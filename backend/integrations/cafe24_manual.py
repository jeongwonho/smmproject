from __future__ import annotations

from typing import Any, Dict, Iterable


class Cafe24ManualInputError(ValueError):
    pass


_ADVANCED_FIELD_KEYS = {
    "comments",
    "runs",
    "interval",
    "min",
    "max",
    "posts",
    "oldPosts",
    "delay",
    "expiry",
    "country",
    "device",
    "typeOfTraffic",
    "googleKeyword",
    "answerNumber",
}


def _first_text(payload: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _coerce_positive_quantity(value: Any) -> str:
    text = str(value or "").strip().replace(",", "")
    if not text:
        raise Cafe24ManualInputError("수동 보정 수량을 입력해 주세요.")
    try:
        quantity = int(float(text))
    except (TypeError, ValueError) as exc:
        raise Cafe24ManualInputError("수동 보정 수량은 숫자로 입력해 주세요.") from exc
    if quantity <= 0:
        raise Cafe24ManualInputError("수동 보정 수량은 1 이상이어야 합니다.")
    return str(quantity)


def cafe24_manual_order_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("fields") if isinstance(payload.get("fields"), dict) else payload
    if not isinstance(source, dict):
        raise Cafe24ManualInputError("수동 보정 입력값 형식이 올바르지 않습니다.")

    fields: Dict[str, Any] = {
        "orderedCount": _coerce_positive_quantity(
            _first_text(source, ("orderedCount", "quantity", "count", "qty"))
        )
    }

    target_url = _first_text(source, ("targetUrl", "targetURL", "link", "snsUrl", "url"))
    target_value = _first_text(source, ("targetValue", "snsValue", "username", "account", "target"))
    if target_url:
        fields["targetUrl"] = target_url
    elif target_value:
        fields["targetValue"] = target_value

    contact_phone = _first_text(source, ("contactPhone", "phone", "receiverPhone"))
    if contact_phone:
        fields["contactPhone"] = contact_phone

    request_memo = _first_text(source, ("requestMemo", "memo", "adminMemo"))
    if request_memo:
        fields["requestMemo"] = request_memo

    for key in sorted(_ADVANCED_FIELD_KEYS):
        value = source.get(key)
        if value not in (None, ""):
            fields[key] = value

    if not fields.get("targetUrl") and not fields.get("targetValue") and not fields.get("comments"):
        raise Cafe24ManualInputError("공급사 발주 대상 링크, 계정 또는 댓글 입력값을 입력해 주세요.")
    return fields
