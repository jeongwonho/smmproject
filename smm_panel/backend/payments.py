from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import re
from typing import List


WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = 5 * 60


def normalize_webhook_signature(raw_signature: str) -> List[str]:
    values: List[str] = []
    for part in re.split(r"[,\s]+", str(raw_signature or "").strip()):
        if not part:
            continue
        key, _, value = part.partition("=")
        candidate = value if value else key
        candidate = candidate.strip()
        if candidate:
            values.append(candidate)
    return values


def verify_payment_webhook_signature(
    secret: str,
    raw_body: bytes,
    provided_signature: str,
    provided_timestamp: str = "",
) -> bool:
    if not secret or not raw_body or not provided_signature:
        return False
    timestamp = str(provided_timestamp or "").strip()
    signed_payloads = [raw_body]
    if timestamp:
        try:
            timestamp_value = float(timestamp)
        except ValueError:
            return False
        if abs(dt.datetime.now(dt.timezone.utc).timestamp() - timestamp_value) > WEBHOOK_SIGNATURE_TOLERANCE_SECONDS:
            return False
        signed_payloads.insert(0, f"{timestamp}.".encode("utf-8") + raw_body)
    expected_values = {
        hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        for payload in signed_payloads
    }
    return any(
        hmac.compare_digest(candidate, expected)
        for candidate in normalize_webhook_signature(provided_signature)
        for expected in expected_values
    )
