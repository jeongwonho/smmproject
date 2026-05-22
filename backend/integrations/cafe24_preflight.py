from __future__ import annotations

from typing import Any, Dict, List


CAFE24_PREFLIGHT_TARGET_KEYS = {"link", "targetUrl", "targetValue", "snsValue", "username", "url"}
CAFE24_PREFLIGHT_QUANTITY_KEYS = {"quantity", "orderedCount", "count", "amount"}
CAFE24_PREVIEW_REDACT_KEYS = {
    "account",
    "comments",
    "contactPhone",
    "link",
    "memo",
    "phone",
    "requestMemo",
    "snsValue",
    "target",
    "targetUrl",
    "targetValue",
    "url",
    "username",
}


def cafe24_preflight_quantity(normalized_fields: Dict[str, Any], supplier_payload: Dict[str, Any]) -> int:
    quantity_value = (
        supplier_payload.get("quantity")
        or supplier_payload.get("orderedCount")
        or normalized_fields.get("orderedCount")
        or normalized_fields.get("quantity")
    )
    try:
        return int(float(str(quantity_value or "0").replace(",", "").strip() or "0"))
    except (TypeError, ValueError):
        return 0


def redact_cafe24_preview_value(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            item_key: redact_cafe24_preview_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_cafe24_preview_value(item, key=key) for item in value]
    normalized_key = str(key or "").strip()
    lower_key = normalized_key.lower()
    if normalized_key in CAFE24_PREVIEW_REDACT_KEYS or any(
        token in lower_key
        for token in ("authorization", "bearer", "email", "link", "memo", "password", "phone", "secret", "target", "token", "url", "username")
    ):
        return "<redacted>"
    return value


def build_cafe24_mapping_preview_report(
    preview: Dict[str, Any],
    *,
    expected_quantity: int = 0,
) -> Dict[str, Any]:
    normalized_fields = preview.get("normalizedFields") if isinstance(preview.get("normalizedFields"), dict) else {}
    supplier_payload = preview.get("supplierPayload") if isinstance(preview.get("supplierPayload"), dict) else {}
    quantity = cafe24_preflight_quantity(normalized_fields, supplier_payload)
    quantity_candidates = []
    for candidate in preview.get("quantityCandidates") or []:
        if not isinstance(candidate, dict):
            continue
        quantity_candidates.append(
            {
                "value": candidate.get("value"),
                "unit": candidate.get("unit") or "",
                "label": candidate.get("label") or "",
                "source": candidate.get("source") or "",
            }
        )
    return {
        "ok": bool(preview.get("ok")),
        "errors": list(preview.get("errors") or []),
        "sampleOrderItemId": str(preview.get("sampleOrderItemId") or ""),
        "normalizedFieldKeys": sorted(str(key) for key in normalized_fields.keys()),
        "supplierPayloadKeys": sorted(str(key) for key in supplier_payload.keys()),
        "normalizedFields": redact_cafe24_preview_value(normalized_fields),
        "supplierPayload": redact_cafe24_preview_value(supplier_payload),
        "supplierPayloadDiagnostics": {
            "service": str(supplier_payload.get("service") or ""),
            "hasTarget": any(
                key in supplier_payload and str(supplier_payload.get(key) or "").strip()
                for key in CAFE24_PREFLIGHT_TARGET_KEYS
            ),
            "hasQuantity": any(
                key in supplier_payload and str(supplier_payload.get(key) or "").strip()
                for key in CAFE24_PREFLIGHT_QUANTITY_KEYS
            ),
        },
        "quantity": {
            "expected": expected_quantity,
            "normalized": quantity,
            "matchesExpected": not expected_quantity or quantity == expected_quantity,
        },
        "optionEntryCount": len(preview.get("optionEntries") or []),
        "quantityCandidates": quantity_candidates,
        "fieldMapping": redact_cafe24_preview_value(preview.get("fieldMapping") or {}),
    }


def cafe24_preflight_blocking_reasons(
    *,
    item: Dict[str, Any],
    supplier_payload: Dict[str, Any],
    readiness: Dict[str, Any],
    quantity: int,
    expected_quantity: int,
) -> List[str]:
    blocking_reasons: List[str] = []
    if item["paymentGateStatus"] != "payment_confirmed":
        blocking_reasons.append("payment_not_confirmed")
    if item["standardStatus"] != "ready_to_submit":
        blocking_reasons.append(f"status_{item['standardStatus'] or 'unknown'}")
    if not item["mappingId"]:
        blocking_reasons.append("mapping_missing")
    if not item["supplierId"] or not item["supplierServiceId"]:
        blocking_reasons.append("supplier_mapping_missing")
    if not supplier_payload:
        blocking_reasons.append("supplier_payload_missing")
    if item["supplierOrderUuid"]:
        blocking_reasons.append("supplier_order_already_exists")
    if expected_quantity and quantity != expected_quantity:
        blocking_reasons.append("quantity_mismatch")
    if not readiness.get("ok"):
        blocking_reasons.append(str(readiness.get("code") or "supplier_not_ready"))
    return blocking_reasons


def build_cafe24_order_item_preflight(
    *,
    item_id: str,
    item: Dict[str, Any],
    normalized_fields: Dict[str, Any],
    supplier_payload: Dict[str, Any],
    readiness: Dict[str, Any],
    expected_quantity: int,
    checked_at: str,
) -> Dict[str, Any]:
    quantity = cafe24_preflight_quantity(normalized_fields, supplier_payload)
    blocking_reasons = cafe24_preflight_blocking_reasons(
        item=item,
        supplier_payload=supplier_payload,
        readiness=readiness,
        quantity=quantity,
        expected_quantity=expected_quantity,
    )
    supplier_payload_keys = sorted(str(key) for key in supplier_payload.keys())
    return {
        "itemId": item_id,
        "identity": {
            "mallId": item["mallId"],
            "shopNo": item["shopNo"],
            "orderId": item["orderId"],
            "orderItemCode": item["orderItemCode"],
            "productNo": item["productNo"],
            "variantCode": item["variantCode"],
            "customProductCode": item["customProductCode"],
        },
        "statuses": {
            "standardStatus": item["standardStatus"],
            "paymentGateStatus": item["paymentGateStatus"],
            "automationErrorCode": item["automationErrorCode"],
            "errorMessage": item["errorMessage"],
        },
        "mapping": {
            "mappingId": item["mappingId"],
            "supplierId": item["supplierId"],
            "supplierServiceId": item["supplierServiceId"],
            "supplierExternalServiceId": item["supplierExternalServiceId"],
            "supplierOrderUuid": item["supplierOrderUuid"],
        },
        "quantity": {
            "expected": expected_quantity,
            "normalized": quantity,
            "matchesExpected": not expected_quantity or quantity == expected_quantity,
        },
        "supplierPayload": {
            "keys": supplier_payload_keys,
            "service": str(supplier_payload.get("service") or ""),
            "hasTarget": any(
                key in supplier_payload and str(supplier_payload.get(key) or "").strip()
                for key in CAFE24_PREFLIGHT_TARGET_KEYS
            ),
            "hasQuantity": any(
                key in supplier_payload and str(supplier_payload.get(key) or "").strip()
                for key in CAFE24_PREFLIGHT_QUANTITY_KEYS
            ),
        },
        "targetDiagnostics": {
            "status": item["targetDiagnostics"]["status"],
            "normalized": bool(item["targetDiagnostics"]["normalized"]),
            "message": item["targetDiagnostics"]["message"],
            "supplierStatus": item["targetDiagnostics"]["supplierStatus"],
            "supplierReasonCode": item["targetDiagnostics"]["supplierReasonCode"],
            "supplierReasonMessage": item["targetDiagnostics"]["supplierReasonMessage"],
        },
        "supplierReadiness": readiness,
        "canDispatch": not blocking_reasons,
        "blockingReasons": blocking_reasons,
        "checkedAt": checked_at,
    }
