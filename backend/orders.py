from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, Optional


ORDER_IDEMPOTENCY_KEY_MAX_LENGTH = 120
ORDER_AUTO_IDEMPOTENCY_WINDOW_SECONDS = 2 * 60


def sanitize_idempotency_key(raw: Any) -> str:
    value = re.sub(r"[^A-Za-z0-9._:-]", "", str(raw or "").strip())
    return value[:ORDER_IDEMPOTENCY_KEY_MAX_LENGTH]


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
