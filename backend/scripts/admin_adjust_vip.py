#!/usr/bin/env python3
"""管理员手动调整 / 撤销 VIP（Phase 1 CLI）。

用法（默认 dry-run，写操作需 --confirm + --request-id）::

    python scripts/admin_adjust_vip.py --action list-grants --email user@example.com

    python scripts/admin_adjust_vip.py --action rollback-last-manual-grant \\
        --email user@example.com --reason "refund requested" \\
        --admin-email support@cozyguidehub.com --request-id adjust-001

    python scripts/admin_adjust_vip.py ... --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import session_scope  # noqa: E402
from app.services.manual_vip_adjustment_service import (  # noqa: E402
    ManualGrantRecordView,
    ManualVipAdjustmentError,
    VALID_ACTIONS,
    list_manual_grants,
    revoke_vip,
    rollback_last_manual_grant,
)


def _print_failed(error_code: str, message: str) -> None:
    print("MANUAL_VIP_ADJUSTMENT_STATUS=failed")
    print(f"ERROR_CODE={error_code}")
    print(f"MESSAGE={message}")


def _print_grant_row(view: ManualGrantRecordView) -> None:
    print("---")
    print(f"ORDER_NO={view.order_no}")
    print(f"TARGET_USER_EMAIL={view.target_user_email}")
    print(f"PLAN_CODE={view.plan_code}")
    print(f"AMOUNT_CENTS_REPORTED={view.amount_cents_reported}")
    print(f"VIP_BEFORE={view.vip_before_display()}")
    print(f"VIP_AFTER={view.vip_after_display()}")
    print(f"REASON={view.reason}")
    print(f"ADMIN_EMAIL={view.admin_email}")
    print(f"REQUEST_ID={view.request_id or ''}")
    print(f"CREATED_AT={view.created_at}")
    print(f"ROLLED_BACK={'yes' if view.rolled_back else 'no'}")


def _print_list_grants(views: list[ManualGrantRecordView]) -> None:
    print("MANUAL_VIP_ADJUSTMENT_STATUS=success")
    print(f"MANUAL_GRANTS_FOUND={len(views)}")
    for view in views:
        _print_grant_row(view)


def _print_adjustment_dry_run(result) -> None:
    p = result.preview
    print("DRY_RUN=yes")
    print(f"ACTION={p.action}")
    print(f"TARGET_USER_EMAIL={p.target_user_email}")
    print(f"VIP_BEFORE={p.vip_before.to_display()}")
    print(f"VIP_AFTER_PREVIEW={p.vip_after.to_display()}")
    if p.related_order_no:
        print(f"RELATED_ORDER_NO={p.related_order_no}")
    if p.related_manual_grant_id:
        print(f"RELATED_MANUAL_GRANT_ID={p.related_manual_grant_id}")
    if p.order_status_before is not None:
        print(f"ORDER_STATUS_BEFORE={p.order_status_before}")
        print(f"ORDER_STATUS_AFTER_PREVIEW={p.order_status_after}")
    print("WOULD_WRITE_AUDIT=no")
    print("CONFIRM_REQUIRED=yes")
    for w in result.warnings:
        print(f"WARNING={w}")


def _print_adjustment_success(result) -> None:
    p = result.preview
    print("MANUAL_VIP_ADJUSTMENT_STATUS=success")
    print(f"ACTION={p.action}")
    print(f"TARGET_USER_EMAIL={p.target_user_email}")
    print(f"VIP_BEFORE={p.vip_before.to_display()}")
    print(f"VIP_AFTER={p.vip_after.to_display()}")
    if p.related_order_no:
        print(f"RELATED_ORDER_NO={p.related_order_no}")
    if p.order_status_after is not None:
        print(f"ORDER_STATUS_AFTER={p.order_status_after}")
    print("AUDIT_LOG_WRITTEN=yes")
    print(f"AUDIT_PATH={result.adjustment_audit_path}")
    for w in result.warnings:
        print(f"WARNING={w}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SaveAny 管理员手动调整/撤销 VIP（默认 dry-run；写操作需 --confirm）",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=sorted(VALID_ACTIONS),
        help="list-grants | rollback-last-manual-grant | revoke-vip",
    )
    parser.add_argument("--email", help="目标用户注册邮箱")
    parser.add_argument("--reason", help="简短原因（写操作必填）")
    parser.add_argument("--admin-email", help="操作管理员邮箱（写操作必填）")
    parser.add_argument("--request-id", help="幂等键（写操作必填）")
    parser.add_argument("--confirm", action="store_true", help="确认写入数据库与审计日志")
    parser.add_argument("--force", action="store_true", help="终身会员 revoke 时必需")
    parser.add_argument("--order-no", help="指定 MAN 订单号")
    parser.add_argument(
        "--mark-order-refunded",
        action="store_true",
        help="将对应 MAN 订单 status 从 paid 改为 refunded",
    )
    parser.add_argument("--limit", type=int, default=10, help="list-grants 最多返回条数")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = not args.confirm

    try:
        with session_scope() as db:
            if args.action == "list-grants":
                if not args.email:
                    raise ManualVipAdjustmentError("invalid_email", "list-grants 需要 --email")
                views = list_manual_grants(
                    db,
                    email=args.email,
                    limit=args.limit,
                    order_no=args.order_no,
                    request_id=args.request_id,
                )
                _print_list_grants(views)
                return 0

            if not args.email:
                raise ManualVipAdjustmentError("invalid_email", "写操作需要 --email")
            if not args.reason:
                raise ManualVipAdjustmentError("invalid_reason", "写操作需要 --reason")
            if not args.admin_email:
                raise ManualVipAdjustmentError("invalid_admin_email", "写操作需要 --admin-email")
            if not args.request_id:
                raise ManualVipAdjustmentError("invalid_request_id", "写操作需要 --request-id")

            if args.action == "rollback-last-manual-grant":
                result = rollback_last_manual_grant(
                    db,
                    email=args.email,
                    reason=args.reason,
                    admin_email=args.admin_email,
                    request_id=args.request_id,
                    dry_run=dry_run,
                    order_no=args.order_no,
                    mark_order_refunded=args.mark_order_refunded,
                )
            elif args.action == "revoke-vip":
                result = revoke_vip(
                    db,
                    email=args.email,
                    reason=args.reason,
                    admin_email=args.admin_email,
                    request_id=args.request_id,
                    dry_run=dry_run,
                    force=args.force,
                    order_no=args.order_no,
                    mark_order_refunded=args.mark_order_refunded,
                )
            else:
                raise ManualVipAdjustmentError("invalid_action", f"未知 action：{args.action}")

        if dry_run:
            _print_adjustment_dry_run(result)
        else:
            _print_adjustment_success(result)
    except ManualVipAdjustmentError as exc:
        _print_failed(exc.error_code, exc.message)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
