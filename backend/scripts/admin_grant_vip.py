#!/usr/bin/env python3
"""管理员手动开通 VIP（Phase 1 CLI）。

用法（默认 dry-run，不写库）::

    python scripts/admin_grant_vip.py \\
        --email user@example.com \\
        --plan monthly \\
        --reason "wechat payment" \\
        --admin-email admin@cozyguidehub.com

真实写入需显式 --confirm::

    python scripts/admin_grant_vip.py ... --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import session_scope  # noqa: E402
from app.services.manual_grant_service import ManualGrantError, grant_vip_manual  # noqa: E402


def _print_failed(error_code: str, message: str) -> None:
    print("MANUAL_VIP_GRANT_STATUS=failed")
    print(f"ERROR_CODE={error_code}")
    print(f"MESSAGE={message}")


def _print_dry_run(result) -> None:
    p = result.preview
    print("DRY_RUN=yes")
    print(f"TARGET_USER_EMAIL={p.target_user_email}")
    print(f"PLAN_CODE={p.plan_code}")
    print(f"VIP_BEFORE={p.vip_before.to_display()}")
    print(f"VIP_AFTER_PREVIEW={p.vip_after.to_display()}")
    print(f"WOULD_CREATE_ORDER={p.order_no.replace('DRYRUN', '<timestamp><hex>')}")
    print("WOULD_WRITE_AUDIT=no")
    print("CONFIRM_REQUIRED=yes")
    for w in result.warnings:
        print(f"WARNING={w}")


def _print_success(result) -> None:
    p = result.preview
    print("MANUAL_VIP_GRANT_STATUS=success")
    print(f"ORDER_NO={result.order_no}")
    print(f"TARGET_USER_EMAIL={p.target_user_email}")
    print(f"PLAN_CODE={p.plan_code}")
    print(f"VIP_BEFORE={p.vip_before.to_display()}")
    print(f"VIP_AFTER={p.vip_after.to_display()}")
    print("AUDIT_LOG_WRITTEN=yes")
    print(f"AUDIT_PATH={result.audit_path}")
    for w in result.warnings:
        print(f"WARNING={w}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SaveAny 管理员手动开通 VIP（默认 dry-run，仅 --confirm 写库）",
    )
    parser.add_argument("--email", required=True, help="目标用户注册邮箱")
    parser.add_argument(
        "--plan",
        required=True,
        choices=["monthly", "quarterly", "yearly", "lifetime"],
        help="套餐代码",
    )
    parser.add_argument("--reason", required=True, help="简短原因，如 wechat payment")
    parser.add_argument("--admin-email", required=True, help="操作管理员邮箱（写入审计）")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认写入数据库并追加审计日志（默认不写库）",
    )
    parser.add_argument(
        "--amount-cents-reported",
        type=int,
        default=None,
        help="实际人工收款金额（分），仅写入审计 JSONL",
    )
    parser.add_argument(
        "--request-id",
        default=None,
        help="幂等键；confirm 时若审计中已存在则拒绝",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="终身会员用户发放非终身套餐时必需",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = not args.confirm

    try:
        with session_scope() as db:
            result = grant_vip_manual(
                db,
                email=args.email,
                plan_code=args.plan,
                reason=args.reason,
                admin_email=args.admin_email,
                dry_run=dry_run,
                force=args.force,
                amount_cents_reported=args.amount_cents_reported,
                request_id=args.request_id,
            )
    except ManualGrantError as exc:
        _print_failed(exc.error_code, exc.message)
        return 1

    if dry_run:
        _print_dry_run(result)
    else:
        _print_success(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
