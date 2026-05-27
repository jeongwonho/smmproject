from __future__ import annotations

from typing import Any, Callable, Dict, Iterable

from .cafe24_preflight import cafe24_order_item_selector_from_payload, cafe24_order_item_selector_has_lookup


class Cafe24ManualInputError(ValueError):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


CAFE24_MANUAL_INPUT_BLOCKED_STATUSES = {
    "submitting",
    "supplier_submitted",
    "supplier_progress",
    "completed",
}
CAFE24_MANUAL_TARGET_KEYS = {"link", "targetUrl", "targetValue", "snsValue", "username", "url"}
CAFE24_MANUAL_QUANTITY_KEYS = {"quantity", "orderedCount", "count", "amount"}


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


def _row_value(row: Any, key: str, default: Any = "") -> Any:
    if row is None:
        return default
    get = getattr(row, "get", None)
    if callable(get):
        return get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


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


def cafe24_manual_expected_quantity(payload: Dict[str, Any], explicit_expected_quantity: Any = 0) -> int:
    try:
        quantity = int(str(explicit_expected_quantity or "0").strip().replace(",", ""))
    except (TypeError, ValueError):
        quantity = 0
    if quantity > 0:
        return quantity
    fields = cafe24_manual_order_fields(payload)
    return int(str(fields.get("orderedCount") or "0").replace(",", ""))


def cafe24_manual_input_request(
    payload: Dict[str, Any],
    *,
    default_shop_no: int = 1,
) -> Dict[str, Any]:
    selector = cafe24_order_item_selector_from_payload(payload, default_shop_no=default_shop_no)
    item_id = str(selector["itemId"])
    supplier_id = str(payload.get("supplierId") or "").strip()
    supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
    if not item_id and not cafe24_order_item_selector_has_lookup(selector):
        raise Cafe24ManualInputError("수동 보정할 Cafe24 주문 품주 id 또는 mall/order/order_item_code를 입력해 주세요.")
    if not supplier_id:
        raise Cafe24ManualInputError("수동 보정에 사용할 공급사를 선택해 주세요.")
    if not supplier_service_id:
        raise Cafe24ManualInputError("수동 보정에 사용할 공급사 서비스를 선택해 주세요.")
    return {
        "selector": selector,
        "itemId": item_id,
        "supplierId": supplier_id,
        "supplierServiceId": supplier_service_id,
        "fields": cafe24_manual_order_fields(payload),
    }


def cafe24_validate_manual_input_order_item(row: Any) -> None:
    if row is None:
        raise Cafe24ManualInputError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
    if str(_row_value(row, "payment_gate_status") or "") != "payment_confirmed":
        raise Cafe24ManualInputError("Cafe24 결제완료가 확인되지 않아 수동 보정할 수 없습니다.")
    standard_status = str(_row_value(row, "standard_status") or "")
    if str(_row_value(row, "supplier_order_uuid") or "").strip() or standard_status in CAFE24_MANUAL_INPUT_BLOCKED_STATUSES:
        raise Cafe24ManualInputError("이미 공급사 발주가 진행된 품주는 수동 보정할 수 없습니다.", status=409)


def cafe24_validate_manual_input_supplier(supplier_row: Any, service_row: Any) -> None:
    if supplier_row is None:
        raise Cafe24ManualInputError("공급사를 찾을 수 없습니다.", status=404)
    if not bool(_row_value(supplier_row, "is_active")):
        raise Cafe24ManualInputError("비활성 공급사는 수동 보정에 사용할 수 없습니다.")
    if service_row is None:
        raise Cafe24ManualInputError("공급사 서비스를 찾을 수 없습니다.", status=404)
    if not bool(_row_value(service_row, "is_active")):
        raise Cafe24ManualInputError("비활성 공급사 서비스는 수동 보정에 사용할 수 없습니다.")


def cafe24_manual_product_payload(product_row: Any = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "product_code": "",
        "name": "",
        "platform_slug": "",
        "price_strategy": "unit",
    }
    if product_row is None:
        return payload
    payload.update(
        {
            "product_code": str(_row_value(product_row, "product_code") or ""),
            "name": str(_row_value(product_row, "name") or ""),
            "platform_slug": str(_row_value(product_row, "platform_slug") or ""),
        }
    )
    return payload


def cafe24_manual_supplier_mapping(
    item_row: Any,
    supplier_row: Any,
    service_row: Any,
    *,
    supplier_id: str,
    supplier_service_id: str,
) -> Dict[str, Any]:
    return {
        "id": str(_row_value(item_row, "mapping_id") or "manual"),
        "product_id": str(_row_value(item_row, "product_id") or ""),
        "supplier_id": supplier_id,
        "supplier_service_id": supplier_service_id,
        "supplier_external_service_id": str(_row_value(service_row, "external_service_id") or ""),
        "api_url": str(_row_value(supplier_row, "api_url") or ""),
        "integration_type": str(_row_value(supplier_row, "integration_type") or "classic"),
        "api_key": _row_value(supplier_row, "api_key"),
        "bearer_token": _row_value(supplier_row, "bearer_token") or "",
        "supplier_name": str(_row_value(supplier_row, "name") or ""),
        "supplier_service_name": str(_row_value(service_row, "name") or ""),
        "supplier_service_raw_json": _row_value(service_row, "raw_json") or "{}",
        "supplier_min_amount": _row_value(service_row, "min_amount"),
        "supplier_max_amount": _row_value(service_row, "max_amount"),
    }


def build_cafe24_manual_input_plan_payload(
    *,
    item_id: str,
    item_row: Any,
    supplier_row: Any,
    service_row: Any,
    supplier_id: str,
    supplier_service_id: str,
    fields: Dict[str, Any],
    product_row: Any = None,
    validate_direct_fields: Callable[[Dict[str, Any], Dict[str, Any]], None],
    build_supplier_order_payload: Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    product_payload = cafe24_manual_product_payload(product_row)
    supplier_mapping = cafe24_manual_supplier_mapping(
        item_row,
        supplier_row,
        service_row,
        supplier_id=supplier_id,
        supplier_service_id=supplier_service_id,
    )
    supplier_external_service_id = str(supplier_mapping["supplier_external_service_id"] or "")
    validate_direct_fields(fields, supplier_mapping)
    supplier_payload = build_supplier_order_payload(product_payload, fields, supplier_mapping)
    return {
        "itemId": str(item_id),
        "row": item_row,
        "supplierId": supplier_id,
        "supplierServiceId": supplier_service_id,
        "supplierExternalServiceId": supplier_external_service_id,
        "fields": fields,
        "supplierPayload": supplier_payload,
    }


def build_cafe24_manual_input_preview_response(
    *,
    item_id: str,
    preflight: Dict[str, Any],
    supplier_id: str,
    supplier_service_id: str,
    supplier_external_service_id: str,
    normalized_fields: Dict[str, Any],
    supplier_payload: Dict[str, Any],
    redactor: Callable[[Any], Any],
) -> Dict[str, Any]:
    return {
        "dryRun": True,
        "itemId": item_id,
        "identity": preflight.get("identity", {}),
        "wouldUpdate": {
            "standardStatus": "ready_to_submit",
            "supplierId": supplier_id,
            "supplierServiceId": supplier_service_id,
            "supplierExternalServiceId": supplier_external_service_id,
            "normalizedFieldKeys": sorted(str(key) for key in normalized_fields.keys()),
            "supplierPayloadKeys": sorted(str(key) for key in supplier_payload.keys()),
        },
        "normalizedFields": redactor(normalized_fields),
        "supplierPayload": redactor(supplier_payload),
        "preflight": preflight,
    }


def build_cafe24_manual_input_cron_response(
    *,
    item_id: str,
    result: Dict[str, Any],
    preflight: Dict[str, Any],
    dispatch_after_save: bool = False,
    dispatch: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    supplier_payload = result.get("supplierPayload") if isinstance(result.get("supplierPayload"), dict) else {}
    normalized_fields = result.get("normalizedFields") if isinstance(result.get("normalizedFields"), dict) else {}
    response: Dict[str, Any] = {
        "ok": True,
        "itemId": item_id,
        "identity": preflight.get("identity", {}),
        "statuses": preflight.get("statuses", {}),
        "mapping": preflight.get("mapping", {}),
        "quantity": preflight.get("quantity", {}),
        "normalizedFields": {
            "keys": sorted(str(key) for key in normalized_fields.keys()),
            "orderedCount": str(normalized_fields.get("orderedCount") or ""),
        },
        "supplierPayload": {
            "keys": sorted(str(key) for key in supplier_payload.keys()),
            "service": str(supplier_payload.get("service") or ""),
            "hasTarget": any(str(supplier_payload.get(key) or "").strip() for key in CAFE24_MANUAL_TARGET_KEYS),
            "hasQuantity": any(str(supplier_payload.get(key) or "").strip() for key in CAFE24_MANUAL_QUANTITY_KEYS),
        },
        "preflight": preflight,
        "dispatchAfterSave": bool(dispatch_after_save),
    }
    if dispatch is not None:
        response["dispatch"] = dispatch
    return response
