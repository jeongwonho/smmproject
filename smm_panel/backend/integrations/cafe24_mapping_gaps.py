from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Set, Tuple

from .cafe24 import (
    cafe24_enriched_product_payload,
    cafe24_option_entries,
    cafe24_products_from_payload,
    normalize_cafe24_shop_no,
)
from .cafe24_quantity import cafe24_quantity_candidates_from_text

NON_MAPPING_OPTION_LABELS = {"memo", "order memo", "ordermemo", "requestmemo", "request memo", "메모", "주문메모", "요청사항"}
Cafe24DetailApiCall = Callable[[str, str, Callable[[Any], Any], float, int], Any]


class Cafe24MappingGapDetailBudget:
    def __init__(self, seconds: float, *, clock: Any = None) -> None:
        self.seconds = max(float(seconds or 0), 0.0)
        self._clock = clock or time.monotonic
        self._started_at = self._clock()

    def remaining(self) -> float:
        return self.seconds - (self._clock() - self._started_at)

    def exhausted(self, *, min_seconds: float = 1.0) -> bool:
        return self.remaining() < min_seconds

    def request_timeout(self, per_call_timeout: float, label: str) -> float:
        remaining = self.remaining()
        if remaining < 1.0:
            raise TimeoutError(f"상품 상세 전체 예산 {self.seconds:.1f}초가 부족해 {label} 조회를 건너뜁니다.")
        return min(float(per_call_timeout or remaining), remaining)


def cafe24_mapping_gap_product_filter(raw_value: Any) -> Set[str]:
    if isinstance(raw_value, list):
        return {str(item or "").strip() for item in raw_value if str(item or "").strip()}
    return {item.strip() for item in re.split(r"[\s,]+", str(raw_value or "")) if item.strip()}


def cafe24_mapping_gap_report_options(payload: Dict[str, Any]) -> Dict[str, Any]:
    include_product_details_raw = payload.get("includeProductDetails", payload.get("include_product_details", True))
    include_product_details = str(include_product_details_raw).strip().lower() not in {"0", "false", "no", "off"}
    try:
        limit = min(max(int(payload.get("limit") or 50), 1), 200)
    except (TypeError, ValueError):
        raise ValueError("조회 개수 값이 올바르지 않습니다.")
    try:
        detail_fetch_limit = min(max(int(payload.get("detailFetchLimit") or payload.get("detail_fetch_limit") or 5), 0), 20)
    except (TypeError, ValueError):
        raise ValueError("상품 상세 조회 개수 값이 올바르지 않습니다.")
    try:
        detail_api_timeout_seconds = min(
            max(float(payload.get("detailApiTimeoutSeconds") or payload.get("detail_api_timeout_seconds") or 4), 1.0),
            10.0,
        )
    except (TypeError, ValueError):
        raise ValueError("상품 상세 API timeout 값이 올바르지 않습니다.")
    try:
        detail_api_max_attempts = min(
            max(int(payload.get("detailApiMaxAttempts") or payload.get("detail_api_max_attempts") or 2), 1),
            3,
        )
    except (TypeError, ValueError):
        raise ValueError("상품 상세 API 재시도 값이 올바르지 않습니다.")
    try:
        detail_api_budget_seconds = min(
            max(float(payload.get("detailApiBudgetSeconds") or payload.get("detail_api_budget_seconds") or 24), 1.0),
            120.0,
        )
    except (TypeError, ValueError):
        raise ValueError("상품 상세 전체 timeout 값이 올바르지 않습니다.")

    return {
        "integrationId": str(payload.get("integrationId") or payload.get("integration_id") or "").strip(),
        "mallId": str(payload.get("mallId") or payload.get("mall_id") or "").strip(),
        "shopNo": normalize_cafe24_shop_no(payload.get("shopNo") or payload.get("shop_no")),
        "includeProductDetails": include_product_details,
        "productFilter": cafe24_mapping_gap_product_filter(payload.get("productNos") or payload.get("product_nos") or ""),
        "limit": limit,
        "detailFetchLimit": detail_fetch_limit,
        "detailApiTimeoutSeconds": detail_api_timeout_seconds,
        "detailApiMaxAttempts": detail_api_max_attempts,
        "detailApiBudgetSeconds": detail_api_budget_seconds,
    }


def fetch_cafe24_mapping_gap_product_details(
    product_nos: List[str],
    *,
    detail_fetch_limit: int,
    detail_api_timeout_seconds: float,
    detail_api_max_attempts: int,
    detail_api_budget_seconds: float,
    api_call: Cafe24DetailApiCall,
) -> Dict[str, Any]:
    product_details: Dict[str, Any] = {}
    warnings: List[str] = []
    detail_product_nos: List[str] = []
    detail_target_product_nos = product_nos[:detail_fetch_limit]
    detail_attempted_product_nos: List[str] = []
    if len(product_nos) > detail_fetch_limit:
        warnings.append(f"상품 상세 조회는 {detail_fetch_limit}개로 제한했습니다. 나머지는 productNos를 좁혀 다시 조회하세요.")
    detail_budget = Cafe24MappingGapDetailBudget(detail_api_budget_seconds)

    def detail_call(product_no: str, label: str, client_call: Callable[[Any], Any]) -> Any:
        return api_call(
            product_no,
            label,
            client_call,
            detail_budget.request_timeout(detail_api_timeout_seconds, label),
            detail_api_max_attempts,
        )

    for product_no in detail_target_product_nos:
        if detail_budget.exhausted():
            warnings.append(f"상품 {product_no}: 상세 조회 전체 예산 {detail_api_budget_seconds:.1f}초를 초과해 남은 상품 조회를 중단했습니다.")
            break
        detail_attempted_product_nos.append(product_no)
        try:
            product_response = detail_call(
                product_no,
                "상품",
                lambda client, selected_product_no=product_no: client.product(selected_product_no),
            )
            product_rows = cafe24_products_from_payload(product_response)
            if not product_rows:
                warnings.append(f"상품 {product_no}: Cafe24 상품 응답이 비어 있습니다.")
                continue
            option_response = None
            variant_response = None
            try:
                option_response = detail_call(
                    product_no,
                    "옵션",
                    lambda client, selected_product_no=product_no: client.product_options(selected_product_no),
                )
            except Exception as exc:
                warnings.append(f"상품 {product_no}: 옵션 조회 실패: {exc}")
            try:
                variant_response = detail_call(
                    product_no,
                    "품목",
                    lambda client, selected_product_no=product_no: client.product_variants(selected_product_no),
                )
            except Exception as exc:
                warnings.append(f"상품 {product_no}: 품목 조회 실패: {exc}")
            product_details[product_no] = cafe24_enriched_product_payload(
                product_rows[0],
                option_response=option_response,
                variant_response=variant_response,
            )
            detail_product_nos.append(product_no)
        except Exception as exc:
            warnings.append(f"상품 {product_no}: 상세 조회 실패: {exc}")

    return {
        "productDetails": product_details,
        "warnings": warnings,
        "detailProductNos": detail_product_nos,
        "detailTargetProductNos": detail_target_product_nos,
        "detailAttemptedProductNos": detail_attempted_product_nos,
    }


def cafe24_mapping_gap_item_payload(
    row: Dict[str, Any],
    raw_payload: Dict[str, Any],
    *,
    default_shop_no: int = 1,
) -> Dict[str, Any]:
    order_payload = raw_payload.get("order") if isinstance(raw_payload.get("order"), dict) else {}
    item_payload = raw_payload.get("item") if isinstance(raw_payload.get("item"), dict) else {}
    option_entries = cafe24_option_entries(order_payload, item_payload) if item_payload else []
    quantity_candidates: List[Dict[str, Any]] = []
    for entry in option_entries:
        for candidate in cafe24_quantity_candidates_from_text(
            entry.get("value"),
            label=str(entry.get("label") or ""),
            source=str(entry.get("source") or ""),
        ):
            safe_candidate = {
                "value": int(candidate.get("value") or 0),
                "unit": str(candidate.get("unit") or ""),
                "label": str(candidate.get("label") or ""),
                "source": str(candidate.get("source") or ""),
            }
            if safe_candidate["value"] > 0 and safe_candidate not in quantity_candidates:
                quantity_candidates.append(safe_candidate)

    return {
        "id": row["id"],
        "mallId": row["mall_id"],
        "shopNo": int(row["shop_no"] or default_shop_no),
        "orderId": row["cafe24_order_id"],
        "orderItemCode": row["cafe24_order_item_code"],
        "productNo": str(row["cafe24_product_no"] or "").strip(),
        "variantCode": row["cafe24_variant_code"] or "",
        "customProductCode": row["cafe24_custom_product_code"] or "",
        "standardStatus": row["standard_status"] or "",
        "paymentGateStatus": row["payment_gate_status"] or "",
        "errorMessage": row["error_message"] or "",
        "lastSyncedAt": row["last_synced_at"] or "",
        "optionLabels": sorted({str(entry.get("label") or "") for entry in option_entries if str(entry.get("label") or "")}),
        "quantityCandidates": quantity_candidates,
    }


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
