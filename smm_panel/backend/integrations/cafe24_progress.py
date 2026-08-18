from __future__ import annotations

import datetime as dt
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote, urlparse


PUBLIC_PROGRESS_FRESHNESS_MINUTES = 30
PUBLIC_ORDER_LOOKUP_MAX_ITEMS = 100
PUBLIC_ACTIVE_ORDER_LOOKUP_MAX_ITEMS = 200
PUBLIC_ACTIVE_ORDER_LOOKUP_MAX_ORDERS = 50
PUBLIC_ACTIVE_ORDER_CANDIDATE_LIMIT = 500

_COMPLETED_STATUSES = {"completed", "done"}
_ATTENTION_STATUSES = {
    "auto_dispatch_excluded",
    "cancelled",
    "failed",
    "field_extract_failed",
    "invalid_quantity",
    "invalid_target",
    "mapping_error",
    "missing_required_field",
    "needs_manual_review",
    "payment_pending",
    "payment_review_required",
    "supplier_range_error",
    "waiting_input",
}
_SPLIT_ACTIVE_STATUSES = {
    "accepted",
    "in_progress",
    "partial",
    "submitted",
    "supplier_progress",
    "supplier_submitted",
}
_SPLIT_PENDING_STATUSES = {"pending", "queued", "ready", "scheduled", "waiting"}
_REMAINS_KEYS = {
    "remain",
    "remain_count",
    "remaining",
    "remaining_count",
    "remaining_quantity",
    "remains",
}
_QUANTITY_KEYS = (
    "orderedCount",
    "totalQuantity",
    "quantity",
    "count",
    "amount",
)
_TARGET_KEYS = (
    "targetValue",
    "targetUrl",
    "snsValue",
    "instagramId",
    "accountId",
    "username",
    "link",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_text(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value))


def normalize_public_order_number(value: Any) -> str:
    return re.sub(r"\s+", "", _normalized_text(value)).upper()


def normalize_public_buyer_name(value: Any) -> str:
    return re.sub(r"\s+", "", _normalized_text(value)).casefold()


def normalize_public_phone(value: Any) -> str:
    digits = re.sub(r"\D+", "", _normalized_text(value))
    if digits.startswith("0082"):
        digits = digits[4:]
    elif digits.startswith("82"):
        digits = digits[2:]
    if digits.startswith("10"):
        digits = f"0{digits}"
    return digits


def normalize_public_order_lookup(payload: Dict[str, Any]) -> Dict[str, str]:
    order_number = normalize_public_order_number(
        payload.get("orderNumber") or payload.get("order_number")
    )
    buyer_name = normalize_public_buyer_name(
        payload.get("buyerName") or payload.get("buyer_name")
    )
    phone_number = normalize_public_phone(
        payload.get("phoneNumber") or payload.get("phone") or payload.get("buyer_phone")
    )
    if not order_number or not buyer_name or not phone_number:
        raise ValueError("주문번호, 구매자명, 휴대폰번호를 모두 입력해 주세요.")
    if len(order_number) > 64 or len(buyer_name) > 80 or len(phone_number) > 15:
        raise ValueError("입력한 주문 정보를 다시 확인해 주세요.")
    if len(phone_number) < 9:
        raise ValueError("휴대폰번호를 다시 확인해 주세요.")
    return {
        "orderNumber": order_number,
        "buyerName": buyer_name,
        "phoneNumber": phone_number,
    }


def public_order_identity_matches(
    row: Dict[str, Any],
    *,
    buyer_name: str,
    phone_number: str,
) -> bool:
    return (
        normalize_public_buyer_name(row.get("buyer_name")) == buyer_name
        and normalize_public_phone(row.get("buyer_phone")) == phone_number
    )


def _parse_datetime(value: Any) -> Optional[dt.datetime]:
    raw = _text(value)
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        raw = re.sub(r"[,\s]", "", _text(value))
        if not raw:
            return None
        try:
            number = float(raw)
        except ValueError:
            return None
    if not math.isfinite(number):
        return None
    return number


def _positive_int(value: Any) -> int:
    number = _numeric(value)
    if number is None or number <= 0:
        return 0
    return int(round(number))


def _find_numeric_key(value: Any, keys: set[str], *, depth: int = 0) -> Optional[float]:
    if depth > 5:
        return None
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).strip().lower() in keys:
                number = _numeric(nested)
                if number is not None:
                    return number
        for nested in value.values():
            found = _find_numeric_key(nested, keys, depth=depth + 1)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value[:25]:
            found = _find_numeric_key(nested, keys, depth=depth + 1)
            if found is not None:
                return found
    return None


def _latest_status_observation(
    response: Dict[str, Any],
    *,
    fallback_checked_at: Any = "",
) -> Dict[str, Any]:
    if not isinstance(response, dict):
        return {"remains": None, "checkedAt": ""}
    last_check = response.get("lastStatusCheck")
    if isinstance(last_check, dict):
        checked_at = _text(last_check.get("checkedAt")) or _text(fallback_checked_at)
        payload = last_check.get("payload")
    else:
        checked_at = _text(fallback_checked_at)
        payload = response
    return {
        "remains": _find_numeric_key(payload, _REMAINS_KEYS),
        "checkedAt": checked_at,
    }


def _observation_is_fresh(
    checked_at: Any,
    *,
    now: Optional[dt.datetime] = None,
    freshness_minutes: int = PUBLIC_PROGRESS_FRESHNESS_MINUTES,
) -> bool:
    parsed = _parse_datetime(checked_at)
    if parsed is None:
        return False
    current = now or dt.datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    age_seconds = (current.astimezone(dt.timezone.utc) - parsed.astimezone(dt.timezone.utc)).total_seconds()
    return -300 <= age_seconds <= max(1, freshness_minutes) * 60


def _progress_payload(
    *,
    total_quantity: int,
    completed_quantity: float,
    checked_at: str,
) -> Dict[str, Any]:
    if total_quantity <= 0:
        return {"supported": False, "percent": None, "checkedAt": ""}
    bounded = max(0.0, min(float(total_quantity), float(completed_quantity)))
    return {
        "supported": True,
        "percent": int(round((bounded / total_quantity) * 100)),
        "checkedAt": checked_at,
    }


def _unsupported_progress() -> Dict[str, Any]:
    return {"supported": False, "percent": None, "checkedAt": ""}


def _direct_progress(
    row: Dict[str, Any],
    *,
    total_quantity: int,
    now: Optional[dt.datetime],
) -> Dict[str, Any]:
    observation = _latest_status_observation(
        row.get("supplier_response") if isinstance(row.get("supplier_response"), dict) else {},
        fallback_checked_at=row.get("automation_last_checked_at"),
    )
    remains = observation["remains"]
    if (
        total_quantity <= 0
        or remains is None
        or not _observation_is_fresh(observation["checkedAt"], now=now)
    ):
        return _unsupported_progress()
    return _progress_payload(
        total_quantity=total_quantity,
        completed_quantity=total_quantity - max(0.0, remains),
        checked_at=observation["checkedAt"],
    )


def _split_progress(
    split_job: Dict[str, Any],
    *,
    now: Optional[dt.datetime],
) -> Dict[str, Any]:
    total_quantity = _positive_int(split_job.get("total_quantity"))
    parts = split_job.get("parts") if isinstance(split_job.get("parts"), list) else []
    if total_quantity <= 0 or not parts:
        return _unsupported_progress()

    completed_quantity = 0.0
    checked_at_values: List[str] = []
    for part in parts:
        if not isinstance(part, dict):
            return _unsupported_progress()
        quantity = _positive_int(part.get("quantity"))
        status = _text(part.get("status")).lower()
        if status in _COMPLETED_STATUSES:
            completed_quantity += quantity
            continue
        if status in _SPLIT_PENDING_STATUSES:
            continue
        if status not in _SPLIT_ACTIVE_STATUSES:
            return _unsupported_progress()
        observation = _latest_status_observation(
            part.get("supplier_response") if isinstance(part.get("supplier_response"), dict) else {},
            fallback_checked_at=part.get("last_status_checked_at"),
        )
        if observation["remains"] is None or not _observation_is_fresh(
            observation["checkedAt"],
            now=now,
        ):
            return _unsupported_progress()
        completed_quantity += quantity - max(0.0, observation["remains"])
        checked_at_values.append(observation["checkedAt"])

    return _progress_payload(
        total_quantity=total_quantity,
        completed_quantity=completed_quantity,
        checked_at=max(checked_at_values) if checked_at_values else _text(split_job.get("updated_at")),
    )


def _first_text_value(sources: Iterable[Dict[str, Any]], keys: Iterable[str]) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = _text(source.get(key))
            if value:
                return value
    return ""


def _raw_item(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    item = raw_payload.get("item") if isinstance(raw_payload, dict) else {}
    return item if isinstance(item, dict) else {}


def _service_name(row: Dict[str, Any]) -> str:
    raw_item = _raw_item(row.get("raw_payload") if isinstance(row.get("raw_payload"), dict) else {})
    raw_product = raw_item.get("product") if isinstance(raw_item.get("product"), dict) else {}
    return (
        _first_text_value(
            (raw_item, raw_product),
            (
                "product_name",
                "productName",
                "product_name_default",
                "item_product_name",
                "name",
            ),
        )
        or _text(row.get("internal_product_name"))
        or "서비스"
    )


def _quantity_from_sources(sources: Iterable[Dict[str, Any]]) -> int:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in _QUANTITY_KEYS:
            quantity = _positive_int(source.get(key))
            if quantity:
                return quantity
    return 0


def _account_name_from_value(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else "")
    if parsed.netloc:
        host = parsed.netloc.lower().split(":", 1)[0]
        path_parts = [unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
        if host.endswith("instagram.com") and path_parts:
            candidate = path_parts[0].lstrip("@")
            if candidate.lower() not in {"explore", "p", "reel", "reels", "stories", "tv"}:
                return f"@{candidate}"
        return ""
    candidate = raw.lstrip("@").strip()
    if re.fullmatch(r"[A-Za-z0-9._]{1,64}", candidate):
        return f"@{candidate}"
    return ""


def _account_name(row: Dict[str, Any], split_job: Optional[Dict[str, Any]]) -> str:
    if split_job:
        account = _account_name_from_value(split_job.get("target_value"))
        if account:
            return account
    normalized_fields = row.get("normalized_fields") if isinstance(row.get("normalized_fields"), dict) else {}
    supplier_payload = row.get("supplier_payload") if isinstance(row.get("supplier_payload"), dict) else {}
    for source in (normalized_fields, supplier_payload):
        for key in _TARGET_KEYS:
            account = _account_name_from_value(source.get(key))
            if account:
                return account
    return "미지원"


def _unit_label(service_name: str) -> str:
    normalized = _normalized_text(service_name).lower()
    if any(token in normalized for token in ("팔로워", "구독자", "친구", "회원")):
        return "명"
    return "개"


def _customer_status(row: Dict[str, Any], split_job: Optional[Dict[str, Any]]) -> Dict[str, str]:
    payment_status = _text(row.get("payment_gate_status")).lower()
    standard_status = _text(row.get("standard_status")).lower()
    if payment_status != "payment_confirmed" or standard_status in _ATTENTION_STATUSES:
        return {"status": "attention", "statusLabel": "확인 필요"}
    status = _text(split_job.get("status") if split_job else standard_status).lower()
    if status in _COMPLETED_STATUSES:
        return {"status": "completed", "statusLabel": "진행 완료"}
    if status in _ATTENTION_STATUSES:
        return {"status": "attention", "statusLabel": "확인 필요"}
    return {"status": "in_progress", "statusLabel": "진행중"}


def build_public_order_progress_item(
    row: Dict[str, Any],
    *,
    split_job: Optional[Dict[str, Any]] = None,
    now: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    split_job = split_job if isinstance(split_job, dict) else None
    normalized_fields = row.get("normalized_fields") if isinstance(row.get("normalized_fields"), dict) else {}
    supplier_payload = row.get("supplier_payload") if isinstance(row.get("supplier_payload"), dict) else {}
    raw_item = _raw_item(row.get("raw_payload") if isinstance(row.get("raw_payload"), dict) else {})
    total_quantity = (
        _positive_int(split_job.get("total_quantity"))
        if split_job
        else _quantity_from_sources((normalized_fields, supplier_payload, raw_item))
    )
    daily_quantity = _positive_int(split_job.get("daily_quantity")) if split_job else 0
    service_name = _service_name(row)
    progress = (
        _split_progress(split_job, now=now)
        if split_job
        else _direct_progress(row, total_quantity=total_quantity, now=now)
    )
    return {
        "serviceName": service_name,
        "accountName": _account_name(row, split_job),
        "dailyQuantity": daily_quantity or None,
        "totalQuantity": total_quantity or None,
        "unit": _unit_label(service_name),
        **_customer_status(row, split_job),
        "progress": progress,
    }
