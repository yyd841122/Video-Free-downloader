from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    FREE_AI_CHAT_PER_TASK,
    FREE_AI_SUMMARY_PER_DAY,
    FREE_CONCURRENT_DOWNLOAD,
    FREE_MAX_RESOLUTION,
    VIP_AI_CHAT_PER_TASK,
    VIP_AI_SUMMARY_PER_DAY,
    VIP_CONCURRENT_DOWNLOAD,
)
from app.db.models import AiUsage, User
from app.services.ai_task_store import ai_summary_task_store
from app.services.task_meta import retention_seconds_for_user
from app.services.task_store import task_store


@dataclass
class QuotaInfo:
    is_vip: bool
    ai_used_today: int
    ai_daily_limit: int
    ai_remaining: int
    max_resolution: int  # 0 = 不限
    max_concurrent: int
    ai_chat_per_task: int  # 0 = 不限
    file_retention_hours: float
    active_download_tasks: int
    active_ai_tasks: int


def _today_key() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%d")


def _get_today_usage(db: Session, user_id: int) -> AiUsage:
    key = _today_key()
    row = db.execute(select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.date_key == key)).scalar_one_or_none()
    if row is None:
        row = AiUsage(user_id=user_id, date_key=key, count=0)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _ai_chat_limit(user: Optional[User]) -> int:
    if user is not None and user.is_vip:
        return VIP_AI_CHAT_PER_TASK
    return FREE_AI_CHAT_PER_TASK


def get_quota(db: Session, user: Optional[User]) -> QuotaInfo:
    """游客 = 视为未登录 free 用户；返回当前用户的配额画像。"""

    uid = user.id if user else None
    vip = bool(user and user.is_vip)
    retention_sec = retention_seconds_for_user(user)
    if user is None:
        return QuotaInfo(
            is_vip=False,
            ai_used_today=0,
            ai_daily_limit=FREE_AI_SUMMARY_PER_DAY,
            ai_remaining=FREE_AI_SUMMARY_PER_DAY,
            max_resolution=FREE_MAX_RESOLUTION,
            max_concurrent=FREE_CONCURRENT_DOWNLOAD,
            ai_chat_per_task=FREE_AI_CHAT_PER_TASK,
            file_retention_hours=retention_sec / 3600,
            active_download_tasks=task_store.active_count_for_user(uid),
            active_ai_tasks=ai_summary_task_store.active_count_for_user(uid),
        )
    usage = _get_today_usage(db, user.id)
    daily_limit = VIP_AI_SUMMARY_PER_DAY if vip else FREE_AI_SUMMARY_PER_DAY
    return QuotaInfo(
        is_vip=vip,
        ai_used_today=usage.count,
        ai_daily_limit=daily_limit,
        ai_remaining=max(0, daily_limit - usage.count),
        max_resolution=0 if vip else FREE_MAX_RESOLUTION,
        max_concurrent=VIP_CONCURRENT_DOWNLOAD if vip else FREE_CONCURRENT_DOWNLOAD,
        ai_chat_per_task=_ai_chat_limit(user),
        file_retention_hours=retention_sec / 3600,
        active_download_tasks=task_store.active_count_for_user(uid),
        active_ai_tasks=ai_summary_task_store.active_count_for_user(uid),
    )


class QuotaExceededError(Exception):
    pass


def consume_ai_quota(db: Session, user: Optional[User]) -> QuotaInfo:
    """登录用户：扣 1 次 AI 总结。游客：直接拒绝（AI 总结必须登录）。"""

    if user is None:
        raise QuotaExceededError("AI 视频总结需要登录后使用，请先注册或登录")
    info = get_quota(db, user)
    if info.ai_remaining <= 0:
        if info.is_vip:
            raise QuotaExceededError(f"今日 AI 总结配额已用完（{info.ai_daily_limit} 次/天）")
        raise QuotaExceededError(
            f"免费用户每天可使用 {info.ai_daily_limit} 次 AI 总结，今日额度已用完。升级会员可解锁 {VIP_AI_SUMMARY_PER_DAY} 次/天"
        )
    usage = _get_today_usage(db, user.id)
    usage.count += 1
    db.add(usage)
    db.commit()
    return get_quota(db, user)


def check_resolution_allowed(user: Optional[User], height: int) -> None:
    """视频下载分辨率门禁：免费用户限 720p；会员不限。"""

    if not height:
        return
    if user is not None and user.is_vip:
        return
    if height > FREE_MAX_RESOLUTION:
        raise QuotaExceededError(
            f"该清晰度（{height}p）为会员专享，免费用户最高可下载 {FREE_MAX_RESOLUTION}p。升级会员即可解锁高清/4K"
        )


def check_concurrent_download(user: Optional[User]) -> None:
    uid = user.id if user else None
    limit = VIP_CONCURRENT_DOWNLOAD if user and user.is_vip else FREE_CONCURRENT_DOWNLOAD
    active = task_store.active_count_for_user(uid)
    if active >= limit:
        who = "会员" if user and user.is_vip else "免费用户"
        raise QuotaExceededError(f"{who}最多同时进行 {limit} 个下载任务，请等待当前任务完成后再试")


def check_concurrent_ai(user: Optional[User]) -> None:
    uid = user.id if user else None
    limit = VIP_CONCURRENT_DOWNLOAD if user and user.is_vip else FREE_CONCURRENT_DOWNLOAD
    active = ai_summary_task_store.active_count_for_user(uid)
    if active >= limit:
        who = "会员" if user and user.is_vip else "免费用户"
        raise QuotaExceededError(f"{who}最多同时进行 {limit} 个 AI 总结任务，请等待当前任务完成后再试")


def check_and_consume_ai_chat(task, user: User) -> None:
    """每个 AI 总结任务的追问轮次限制（免费 5 轮，会员不限）。"""

    limit = _ai_chat_limit(user)
    if limit <= 0:
        return
    meta = dict(task.metadata or {})
    count = int(meta.get("chat_count", 0))
    if count >= limit:
        raise QuotaExceededError(
            f"本总结已使用 {limit} 轮追问额度。升级会员可无限追问"
        )
    meta["chat_count"] = count + 1
    ai_summary_task_store.update(task.task_id, metadata=meta)
