from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import time
from typing import Any, Dict, Optional


ORDER_IDEMPOTENCY_KEY_MAX_LENGTH = 120
ORDER_AUTO_IDEMPOTENCY_WINDOW_SECONDS = 2 * 60
ORDER_EXTERNAL_REFERENCE_MAX_LENGTH = 160
ORDER_AUTOMATION_RETRY_BACKOFF_MINUTES = (10, 30, 120)
ORDER_CHANNEL_WEB = "web"
ORDER_CHANNEL_CAFE24 = "cafe24"
ORDER_CHANNEL_MANUAL = "manual"
ORDER_CHANNELS = {ORDER_CHANNEL_WEB, ORDER_CHANNEL_CAFE24, ORDER_CHANNEL_MANUAL}
ORDER_DISPATCH_UNMAPPED = "unmapped"
ORDER_DISPATCH_READY = "ready"
ORDER_DISPATCH_SUBMITTED = "submitted"
ORDER_DISPATCH_ACCEPTED = "accepted"
ORDER_DISPATCH_IN_PROGRESS = "in_progress"
ORDER_DISPATCH_COMPLETED = "completed"
ORDER_DISPATCH_PARTIAL = "partial"
ORDER_DISPATCH_CANCELLED = "cancelled"
ORDER_DISPATCH_FAILED = "failed"
ORDER_DISPATCH_STATUSES = {
    ORDER_DISPATCH_UNMAPPED,
    ORDER_DISPATCH_READY,
    ORDER_DISPATCH_SUBMITTED,
    ORDER_DISPATCH_ACCEPTED,
    ORDER_DISPATCH_IN_PROGRESS,
    ORDER_DISPATCH_COMPLETED,
    ORDER_DISPATCH_PARTIAL,
    ORDER_DISPATCH_CANCELLED,
    ORDER_DISPATCH_FAILED,
}


def generate_public_order_number() -> str:
    return f"SMM-{dt.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def parse_iso_datetime(value: Any) -> Optional[dt.datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed


def automation_paused(env: Optional[Dict[str, Any]] = None) -> bool:
    source = env if env is not None else os.environ
    return str(source.get("SMM_PANEL_AUTOMATION_PAUSED") or "").strip().lower() in {"1", "true", "yes", "on"}


def automation_retry_at(
    attempts: int,
    *,
    now: Optional[dt.datetime] = None,
    backoff_minutes: tuple[int, ...] = ORDER_AUTOMATION_RETRY_BACKOFF_MINUTES,
) -> str:
    safe_attempts = max(int(attempts or 1), 1)
    index = min(safe_attempts - 1, len(backoff_minutes) - 1)
    base_time = now if now is not None else dt.datetime.now().astimezone()
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return (base_time + dt.timedelta(minutes=backoff_minutes[index])).isoformat(timespec="seconds")


def sanitize_idempotency_key(raw: Any) -> str:
    value = re.sub(r"[^A-Za-z0-9._:-]", "", str(raw or "").strip())
    return value[:ORDER_IDEMPOTENCY_KEY_MAX_LENGTH]


def sanitize_external_order_reference(raw: Any) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]", "", str(raw or "").strip())
    return value[:ORDER_EXTERNAL_REFERENCE_MAX_LENGTH]


def normalize_order_channel(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace("_", "-")
    aliases = {
        "": ORDER_CHANNEL_WEB,
        "public": ORDER_CHANNEL_WEB,
        "public-web": ORDER_CHANNEL_WEB,
        "storefront": ORDER_CHANNEL_WEB,
        "instamart": ORDER_CHANNEL_WEB,
        "cafe-24": ORDER_CHANNEL_CAFE24,
        "cafe24": ORDER_CHANNEL_CAFE24,
        "external-cafe24": ORDER_CHANNEL_CAFE24,
        "admin": ORDER_CHANNEL_MANUAL,
        "manual": ORDER_CHANNEL_MANUAL,
    }
    normalized = aliases.get(value, value)
    if normalized not in ORDER_CHANNELS:
        raise ValueError("지원하지 않는 주문 유입 경로입니다.")
    return normalized


def order_channel_label(raw: Any) -> str:
    try:
        channel = normalize_order_channel(raw)
    except ValueError:
        channel = str(raw or "").strip() or ORDER_CHANNEL_WEB
    return {
        ORDER_CHANNEL_WEB: "자사몰",
        ORDER_CHANNEL_CAFE24: "카페24",
        ORDER_CHANNEL_MANUAL: "수동등록",
    }.get(channel, channel)


def order_money_label(value: Any) -> str:
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,}원"


def order_submission_payload(
    order_row: Dict[str, Any],
    *,
    available_balance: Any,
    duplicate: bool = False,
) -> Dict[str, Any]:
    total_price = int(order_row["total_price"])
    balance_after = int(available_balance or 0)
    payload = {
        "ok": True,
        "orderId": order_row["id"],
        "orderNumber": order_row["order_number"],
        "orderChannel": order_row.get("order_channel") or ORDER_CHANNEL_WEB,
        "externalOrderId": order_row.get("external_order_id") or "",
        "externalOrderItemId": order_row.get("external_order_item_id") or "",
        "dispatchStatus": order_row.get("dispatch_status") or ORDER_DISPATCH_UNMAPPED,
        "totalPrice": total_price,
        "totalPriceLabel": order_money_label(total_price),
        "balanceAfter": balance_after,
        "balanceAfterLabel": order_money_label(balance_after),
    }
    if duplicate:
        payload["duplicate"] = True
    return payload


def normalize_order_dispatch_status(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace("-", "_")
    if value in {"", "none", "not_required", "not_required_yet", "unmapped"}:
        return ORDER_DISPATCH_UNMAPPED
    if value in {"ready", "pending", "queued"}:
        return ORDER_DISPATCH_READY
    if value in {"submitted", "success", "sent"}:
        return ORDER_DISPATCH_SUBMITTED
    if value in {"accepted"}:
        return ORDER_DISPATCH_ACCEPTED
    if value in {"in_progress", "processing", "progress", "running"}:
        return ORDER_DISPATCH_IN_PROGRESS
    if value in {"completed", "complete", "done"}:
        return ORDER_DISPATCH_COMPLETED
    if value in {"partial", "partially_completed"}:
        return ORDER_DISPATCH_PARTIAL
    if value in {"cancelled", "canceled", "cancel"}:
        return ORDER_DISPATCH_CANCELLED
    if value in {"failed", "fail", "error", "blocked"}:
        return ORDER_DISPATCH_FAILED
    return ORDER_DISPATCH_FAILED


def canonical_order_field_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): canonical_order_field_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonical_order_field_value(item) for item in value]
    if value is None:
        return ""
    return str(value).strip()


def derive_order_idempotency_key(
    user_id: str,
    product_id: str,
    fields: Dict[str, Any],
    *,
    now_seconds: Optional[int] = None,
) -> str:
    bucket = int((now_seconds if now_seconds is not None else time.time()) // ORDER_AUTO_IDEMPOTENCY_WINDOW_SECONDS)
    fingerprint_payload = {
        "bucket": bucket,
        "userId": str(user_id or "").strip(),
        "productId": str(product_id or "").strip(),
        "fields": canonical_order_field_value(fields),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]
    return sanitize_idempotency_key(f"auto:{bucket}:{fingerprint}")
