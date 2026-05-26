from __future__ import annotations

from typing import Any, Dict, List, Tuple

NON_MAPPING_OPTION_LABELS = {"memo", "order memo", "ordermemo", "requestmemo", "request memo", "메모", "주문메모", "요청사항"}


def cafe24_mapping_gap_key(item: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(item.get("productNo") or "").strip(),
        str(item.get("variantCode") or "").strip(),
        str(item.get("customProductCode") or "").strip(),
    )


def summarize_cafe24_mapping_gaps(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for item in items:
        key = cafe24_mapping_gap_key(item)
        group = groups.setdefault(
            key,
            {
                "productNo": key[0],
                "variantCode": key[1],
                "customProductCode": key[2],
                "count": 0,
                "orderItems": [],
                "optionLabels": [],
                "quantityCandidates": [],
                "errorMessages": [],
                "lastSyncedAt": "",
            },
        )
        group["count"] += 1
        group["orderItems"].append(
            {
                "id": item.get("id") or "",
                "orderId": item.get("orderId") or "",
                "orderItemCode": item.get("orderItemCode") or "",
                "standardStatus": item.get("standardStatus") or "",
                "paymentGateStatus": item.get("paymentGateStatus") or "",
                "lastSyncedAt": item.get("lastSyncedAt") or "",
            }
        )
        if str(item.get("lastSyncedAt") or "") > str(group.get("lastSyncedAt") or ""):
            group["lastSyncedAt"] = item.get("lastSyncedAt") or ""
        for label in item.get("optionLabels") or []:
            if label and label not in group["optionLabels"]:
                group["optionLabels"].append(label)
        for candidate in item.get("quantityCandidates") or []:
            if candidate and candidate not in group["quantityCandidates"]:
                group["quantityCandidates"].append(candidate)
        message = str(item.get("errorMessage") or "").strip()
        if message and message not in group["errorMessages"]:
            group["errorMessages"].append(message)

    return sorted(
        groups.values(),
        key=lambda group: (-int(group["count"] or 0), str(group.get("productNo") or ""), str(group.get("variantCode") or "")),
    )


def cafe24_mapping_gap_diagnostics(
    group: Dict[str, Any],
    product_detail: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    detail = product_detail if isinstance(product_detail, dict) else {}
    option_labels = [label for label in group.get("optionLabels") or [] if str(label or "").strip()]
    mapping_option_labels = [
        label
        for label in option_labels
        if str(label or "").strip().lower() not in NON_MAPPING_OPTION_LABELS
    ]
    quantity_candidates = [candidate for candidate in group.get("quantityCandidates") or [] if int(candidate.get("value") or 0) > 0]
    detail_options = detail.get("options") if isinstance(detail.get("options"), list) else []
    variants = detail.get("variants") if isinstance(detail.get("variants"), list) else []
    has_detail_options = any(
        str(option.get("name") or option.get("value") or "").strip()
        or bool(option.get("values") if isinstance(option.get("values"), list) else [])
        for option in detail_options
        if isinstance(option, dict)
    )
    product_name = str(detail.get("productName") or "").strip()
    personal_payment_like = "개인결제" in product_name
    has_mapping_sources = bool(mapping_option_labels or quantity_candidates or has_detail_options)
    group_variant_code = str(group.get("variantCode") or "").strip()
    group_custom_code = str(group.get("customProductCode") or "").strip()
    matched_variant = {}
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        variant_code = str(variant.get("variantCode") or "").strip()
        custom_code = str(variant.get("customProductCode") or "").strip()
        if (group_variant_code and variant_code == group_variant_code) or (group_custom_code and custom_code == group_custom_code):
            matched_variant = {
                "variantCode": variant_code,
                "customProductCode": custom_code,
                "productCode": str(variant.get("productCode") or "").strip(),
                "optionText": str(variant.get("optionText") or "").strip(),
                "display": str(variant.get("display") or "").strip(),
                "selling": str(variant.get("selling") or "").strip(),
                "price": str(variant.get("price") or "").strip(),
            }
            break

    if not has_mapping_sources:
        return {
            "status": "manual_input_required",
            "manualInputRequired": True,
            "mappingCandidate": False,
            "reason": "no_option_or_quantity_source",
            "nextAction": "옵션/수량 후보가 없어 상품 매핑만으로 발주 payload를 만들 수 없습니다. Cafe24 큐에서 공급사 서비스와 대상/수량을 수동 보정하세요.",
            "productName": product_name,
            "personalPaymentLike": personal_payment_like,
            "hasCafe24Options": False,
            "variantCount": len(variants),
            "hasVariantMatch": bool(matched_variant),
            "matchedVariant": matched_variant,
        }
    if not quantity_candidates:
        return {
            "status": "field_mapping_required",
            "manualInputRequired": False,
            "mappingCandidate": True,
            "reason": "option_labels_without_quantity_candidate",
            "nextAction": "옵션 라벨은 있지만 수량 후보가 없습니다. Cafe24 매핑에서 orderedCount source를 고정값 또는 명시 옵션으로 지정하세요.",
            "productName": product_name,
            "personalPaymentLike": personal_payment_like,
            "hasCafe24Options": has_detail_options,
            "variantCount": len(variants),
            "hasVariantMatch": bool(matched_variant),
            "matchedVariant": matched_variant,
        }
    return {
        "status": "mapping_candidate",
        "manualInputRequired": False,
        "mappingCandidate": True,
        "reason": "quantity_candidate_detected",
        "nextAction": "상품번호/품목코드 기준으로 공급사 서비스를 선택하고 payload preview로 수량과 target을 검증하세요.",
        "productName": product_name,
        "personalPaymentLike": personal_payment_like,
        "hasCafe24Options": has_detail_options,
        "variantCount": len(variants),
        "hasVariantMatch": bool(matched_variant),
        "matchedVariant": matched_variant,
    }


def annotate_cafe24_mapping_gap_groups(
    groups: List[Dict[str, Any]],
    product_details: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    details = product_details if isinstance(product_details, dict) else {}
    annotated: List[Dict[str, Any]] = []
    for group in groups:
        product_no = str(group.get("productNo") or "")
        next_group = dict(group)
        next_group["diagnostics"] = cafe24_mapping_gap_diagnostics(group, details.get(product_no))
        annotated.append(next_group)
    return annotated
