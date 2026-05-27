from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


CAFE24_DEFAULT_SHOP_NO = 1
CAFE24_DEFAULT_SCOPES = ("mall.read_order", "mall.write_order", "mall.read_product")
CAFE24_REFRESH_TOKEN_EXPIRY_WARNING_DAYS = 2
CAFE24_AUTO_POLL_INTERVAL_MINUTES = 5
CAFE24_TOKEN_STATUS_CONNECTED = "connected"
CAFE24_TOKEN_STATUS_EXPIRING = "token_expiring"
CAFE24_TOKEN_STATUS_REFRESHING = "refreshing"
CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED = "reconnect_required"
CAFE24_TOKEN_STATUS_FAILED = "failed"
CAFE24_ORDER_OVERLAP_MINUTES = 20
CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS = 30
CAFE24_ORDER_PAGE_LIMIT = 1000
CAFE24_ORDER_ITEM_DATE_EXPR = (
    "COALESCE(NULLIF(coi.cafe24_order_date, ''), NULLIF(coi.payment_paid_at, ''), "
    "NULLIF(coi.last_synced_at, ''), coi.created_at)"
)
CAFE24_ORDER_ELIGIBLE_STATUSES = {"N10", "N20", "N21", "N22", "N30", "N40", "N50"}
CAFE24_ORDER_UNPAID_STATUSES = {"N00"}
CAFE24_ORDER_CANCELLED_PREFIXES = ("C", "R", "E")
CAFE24_PAYMENT_PAID_STATUSES = {"paid", "payment_confirmed", "confirmed", "complete", "completed", "done", "y", "true", "p", "a", "t"}
CAFE24_PAYMENT_PENDING_STATUSES = {"unpaid", "awaiting_payment", "pending", "ready", "waiting", "n", "false", "f"}
CAFE24_PAYMENT_CANCELLED_STATUSES = {"canceled", "cancelled", "cancel", "refunded", "refund", "void"}
CAFE24_MANUAL_INPUT_REQUIRED_STATUSES = {
    "waiting_input",
    "mapping_error",
    "missing_required_field",
    "invalid_quantity",
    "invalid_target",
    "supplier_range_error",
    "needs_manual_review",
}
CAFE24_REVIEW_REQUIRED_STATUSES = CAFE24_MANUAL_INPUT_REQUIRED_STATUSES | {
    "field_extract_failed",
    "payment_review_required",
}
CAFE24_IN_PROGRESS_STATUSES = {"submitting", "supplier_submitted", "supplier_progress"}
CAFE24_OPERATOR_ACTION_STATUSES = CAFE24_MANUAL_INPUT_REQUIRED_STATUSES | {"field_extract_failed"}
CAFE24_PAYMENT_BLOCKED_STATUSES = {"payment_pending", "payment_review_required", "cancelled"}
CAFE24_STANDARD_STATUSES = {
    "received",
    "payment_pending",
    "payment_review_required",
    "validated",
    "field_extract_failed",
    "ready_to_submit",
    "completed",
    "failed",
    "cancelled",
    *CAFE24_MANUAL_INPUT_REQUIRED_STATUSES,
    *CAFE24_IN_PROGRESS_STATUSES,
}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


class Cafe24ApiError(Exception):
    pass


class Cafe24PollWindowError(ValueError):
    pass


class Cafe24DispatchRequestError(ValueError):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def cafe24_client_id() -> str:
    return str(os.environ.get("SMM_PANEL_CAFE24_CLIENT_ID") or "").strip()


def cafe24_client_secret() -> str:
    return str(os.environ.get("SMM_PANEL_CAFE24_CLIENT_SECRET") or "").strip()


def cafe24_redirect_uri() -> str:
    return str(os.environ.get("SMM_PANEL_CAFE24_REDIRECT_URI") or "").strip()


def cafe24_api_base_url(mall_id: str) -> str:
    return f"https://{str(mall_id or '').strip()}.cafe24api.com/api/v2"


def normalize_cafe24_shop_no(raw: Any) -> int:
    try:
        value = int(raw or CAFE24_DEFAULT_SHOP_NO)
    except (TypeError, ValueError):
        value = CAFE24_DEFAULT_SHOP_NO
    return max(value, 1)


def normalize_cafe24_scopes(raw: Any) -> List[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[\s,]+", str(raw or "").strip())
    scopes = []
    for value in values:
        scope = str(value or "").strip()
        if scope and scope not in scopes:
            scopes.append(scope)
    return scopes or list(CAFE24_DEFAULT_SCOPES)


def cafe24_oauth_timestamp_from_response(payload: Dict[str, Any], absolute_key: str, seconds_key: str) -> str:
    absolute_value = str(payload.get(absolute_key) or "").strip()
    if absolute_value:
        return absolute_value
    try:
        seconds = int(payload.get(seconds_key) or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds <= 0:
        return ""
    return (dt.datetime.now().astimezone() + dt.timedelta(seconds=seconds)).isoformat()


def _parse_iso_datetime(value: Any) -> Optional[dt.datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed


def cafe24_refresh_token_expired(expires_at: Any) -> bool:
    parsed = _parse_iso_datetime(expires_at)
    return bool(parsed and parsed <= dt.datetime.now().astimezone())


def cafe24_refresh_token_expiring_soon(expires_at: Any) -> bool:
    parsed = _parse_iso_datetime(expires_at)
    if not parsed:
        return False
    threshold = dt.datetime.now().astimezone() + dt.timedelta(days=CAFE24_REFRESH_TOKEN_EXPIRY_WARNING_DAYS)
    return parsed <= threshold


def cafe24_next_auto_poll_at(
    row: Dict[str, Any],
    *,
    interval_minutes: int = CAFE24_AUTO_POLL_INTERVAL_MINUTES,
) -> str:
    last_auto_poll_at = _parse_iso_datetime((row or {}).get("last_auto_poll_at"))
    if not last_auto_poll_at:
        return ""
    return (last_auto_poll_at + dt.timedelta(minutes=interval_minutes)).isoformat(timespec="seconds")


def cafe24_auto_poll_due(
    row: Dict[str, Any],
    *,
    force: bool = False,
    interval_minutes: int = CAFE24_AUTO_POLL_INTERVAL_MINUTES,
) -> bool:
    if force:
        return True
    last_auto_poll_at = _parse_iso_datetime((row or {}).get("last_auto_poll_at"))
    if not last_auto_poll_at:
        return True
    return last_auto_poll_at <= dt.datetime.now().astimezone() - dt.timedelta(minutes=interval_minutes)


def cafe24_token_status(row: Dict[str, Any]) -> str:
    row_map = row or {}
    stored = str(row_map.get("token_status") or CAFE24_TOKEN_STATUS_CONNECTED).strip() or CAFE24_TOKEN_STATUS_CONNECTED
    if stored == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED:
        return stored
    if not row_map.get("refresh_token"):
        return CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED
    if cafe24_refresh_token_expired(row_map.get("refresh_token_expires_at")):
        return CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED
    if stored == CAFE24_TOKEN_STATUS_REFRESHING:
        lock_until = _parse_iso_datetime(row_map.get("token_refresh_lock_until"))
        if lock_until and lock_until > dt.datetime.now().astimezone():
            return stored
    if cafe24_refresh_token_expiring_soon(row_map.get("refresh_token_expires_at")):
        return CAFE24_TOKEN_STATUS_EXPIRING
    if stored in {CAFE24_TOKEN_STATUS_CONNECTED, CAFE24_TOKEN_STATUS_FAILED}:
        return stored
    return CAFE24_TOKEN_STATUS_CONNECTED


def cafe24_token_status_label(row: Dict[str, Any]) -> str:
    return {
        CAFE24_TOKEN_STATUS_CONNECTED: "정상",
        CAFE24_TOKEN_STATUS_EXPIRING: "재연결 권장",
        CAFE24_TOKEN_STATUS_REFRESHING: "갱신 중",
        CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED: "재연결 필요",
        CAFE24_TOKEN_STATUS_FAILED: "확인 실패",
    }.get(cafe24_token_status(row), "미확인")


def cafe24_token_status_message(row: Dict[str, Any]) -> str:
    row_map = row or {}
    status = cafe24_token_status(row_map)
    if status == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED:
        return row_map.get("reconnect_reason") or "Refresh token이 없거나 만료되었습니다. OAuth 재연결이 필요합니다."
    if status == CAFE24_TOKEN_STATUS_EXPIRING:
        return "Refresh token 만료가 임박했습니다. 운영 중단을 막으려면 OAuth를 다시 연결하세요."
    if status == CAFE24_TOKEN_STATUS_REFRESHING:
        return "다른 요청에서 Cafe24 토큰을 갱신 중입니다."
    if status == CAFE24_TOKEN_STATUS_FAILED:
        return row_map.get("reconnect_reason") or row_map.get("last_sync_message") or "최근 토큰 확인에 실패했습니다."
    return "주문 수집 전 access token 만료 여부를 확인하고 필요 시 자동 갱신합니다."


def cafe24_refresh_error_requires_reconnect(error_message: Any) -> bool:
    message = str(error_message or "").lower()
    return any(
        token in message
        for token in (
            "invalid_grant",
            "invalid refresh",
            "expired",
            "unauthorized",
            "401",
            "400",
            "access_denied",
            "invalid token",
        )
    )


def cafe24_access_token_error(error: Any) -> bool:
    message = str(error or "").strip().lower()
    if not message:
        return False
    token_markers = ("invalid_token", "invalid token", "access_token", "access token", "unauthorized")
    return "401" in message and any(marker in message for marker in token_markers)


def cafe24_poll_datetime_window(
    *,
    start_raw: str = "",
    end_raw: str = "",
    last_poll_at: str = "",
    use_cursor: bool = False,
    overlap_minutes: int = CAFE24_ORDER_OVERLAP_MINUTES,
    default_lookback_days: int = CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS,
) -> Dict[str, str]:
    now = dt.datetime.now().astimezone()
    default_start = (now - dt.timedelta(days=default_lookback_days)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    def parse_bound(value: str, *, is_end: bool) -> Optional[dt.datetime]:
        raw = str(value or "").strip()
        if not raw:
            return None
        normalized = raw.replace("T", " ")
        try:
            if len(normalized) <= 10:
                parsed_date = dt.date.fromisoformat(normalized[:10])
                parsed = dt.datetime.combine(
                    parsed_date,
                    dt.time(23, 59, 59) if is_end else dt.time(0, 0, 0),
                    tzinfo=now.tzinfo,
                )
            else:
                parsed = dt.datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=now.tzinfo)
            return parsed.astimezone(now.tzinfo)
        except ValueError as exc:
            raise Cafe24PollWindowError(
                "Cafe24 주문 조회 기간 형식이 올바르지 않습니다. YYYY-MM-DD 또는 YYYY-MM-DD HH:mm:ss 형식을 사용해 주세요."
            ) from exc

    start = parse_bound(start_raw, is_end=False)
    end = parse_bound(end_raw, is_end=True)
    if start is None:
        start = default_start
    if use_cursor and last_poll_at:
        try:
            parsed = dt.datetime.fromisoformat(str(last_poll_at))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=now.tzinfo)
            start = parsed.astimezone(now.tzinfo) - dt.timedelta(minutes=max(int(overlap_minutes or 0), 0))
        except ValueError:
            pass
    if end is None:
        end = now
    if start > end:
        raise Cafe24PollWindowError("Cafe24 주문 수집 시작일은 종료일보다 늦을 수 없습니다.")
    return {
        "start": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end": end.strftime("%Y-%m-%d %H:%M:%S"),
    }


def cafe24_default_poll_window(last_poll_at: str = "", overlap_minutes: int = CAFE24_ORDER_OVERLAP_MINUTES) -> Dict[str, str]:
    return cafe24_poll_datetime_window(last_poll_at=last_poll_at, use_cursor=False, overlap_minutes=overlap_minutes)


def cafe24_order_item_list_options(payload: Dict[str, Any]) -> Dict[str, Any]:
    page = max(int(str(payload.get("page") or "1") or 1), 1)
    page_size = min(max(int(str(payload.get("pageSize") or "5") or 5), 1), 50)
    window = cafe24_poll_datetime_window(
        start_raw=str(payload.get("from") or payload.get("startDate") or ""),
        end_raw=str(payload.get("to") or payload.get("endDate") or ""),
        use_cursor=False,
    )
    return {
        "page": page,
        "pageSize": page_size,
        "window": window,
        "paymentFilter": str(payload.get("payment") or "").strip(),
        "mappingFilter": str(payload.get("mapping") or "").strip(),
        "statusFilter": str(payload.get("status") or "").strip(),
        "search": str(payload.get("q") or payload.get("search") or "").strip().lower(),
        "integrationId": str(payload.get("integrationId") or "").strip(),
    }


def cafe24_order_item_filter_clauses(
    options: Dict[str, Any],
    *,
    integration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    window = options.get("window") if isinstance(options.get("window"), dict) else {}
    where: List[str] = [f"{CAFE24_ORDER_ITEM_DATE_EXPR} >= ?", f"{CAFE24_ORDER_ITEM_DATE_EXPR} <= ?"]
    params: List[Any] = [window.get("start") or "", window.get("end") or ""]
    summary_where: List[str] = list(where)
    summary_params: List[Any] = list(params)

    if integration:
        mall_id = str(integration.get("mall_id") or "")
        shop_no = int(integration.get("shop_no") or CAFE24_DEFAULT_SHOP_NO)
        where.extend(["coi.mall_id = ?", "coi.shop_no = ?"])
        params.extend([mall_id, shop_no])
        summary_where.extend(["coi.mall_id = ?", "coi.shop_no = ?"])
        summary_params.extend([mall_id, shop_no])

    payment_filter = str(options.get("paymentFilter") or "").strip()
    status_filter = str(options.get("statusFilter") or "").strip()
    mapping_filter = str(options.get("mappingFilter") or "").strip()
    search = str(options.get("search") or "").strip().lower()

    if payment_filter and payment_filter != "all":
        where.append("coi.payment_gate_status = ?")
        params.append(payment_filter)
    if status_filter and status_filter != "all":
        where.append("coi.standard_status = ?")
        params.append(status_filter)
    if mapping_filter == "mapped":
        where.append("(coi.mapping_id <> '' OR coi.supplier_service_id <> '' OR coi.product_id <> '')")
    elif mapping_filter == "unmapped":
        where.append("(coi.mapping_id = '' AND coi.supplier_service_id = '' AND coi.product_id = '')")
    if search:
        searchable = (
            "LOWER(coi.mall_id || ' ' || coi.cafe24_order_id || ' ' || coi.cafe24_order_item_code || ' ' || "
            "coi.cafe24_product_no || ' ' || coi.cafe24_variant_code || ' ' || coi.cafe24_custom_product_code || ' ' || "
            "coi.buyer_name || ' ' || coi.payment_status || ' ' || coi.payment_gate_status || ' ' || "
            "coi.payment_method || ' ' || coi.payment_reference || ' ' || coi.standard_status || ' ' || coi.error_message)"
        )
        where.append(f"{searchable} LIKE ?")
        params.append(f"%{search}%")

    return {
        "whereSql": " AND ".join(where),
        "params": params,
        "summaryWhereSql": " AND ".join(summary_where),
        "summaryParams": summary_params,
    }


def cafe24_order_item_summary_payload(row: Dict[str, Any] | None) -> Dict[str, int]:
    row_map = row or {}
    return {
        "totalCount": int(row_map.get("total_count") or 0),
        "paymentConfirmedCount": int(row_map.get("payment_confirmed_count") or 0),
        "unmappedCount": int(row_map.get("unmapped_count") or 0),
        "reviewRequiredCount": int(row_map.get("review_required_count") or 0),
        "manualInputRequiredCount": int(row_map.get("manual_input_required_count") or 0),
        "readyToSubmitCount": int(row_map.get("ready_to_submit_count") or 0),
        "failedCount": int(row_map.get("failed_count") or 0),
    }


def cafe24_order_item_pagination_payload(
    *,
    page: int,
    page_size: int,
    total: int,
    window: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max((total + page_size - 1) // page_size, 1),
        "from": window["start"],
        "to": window["end"],
    }


def cafe24_processing_error_status(error: Any) -> str:
    message = str(error or "")
    if "후보" in message or "검수" in message:
        return "needs_manual_review"
    if "수량" in message and "범위" not in message and "최소" not in message and "최대" not in message:
        return "invalid_quantity"
    if "최소" in message or "최대" in message or "범위" in message:
        return "supplier_range_error"
    if "URL" in message or "링크" in message or "계정" in message:
        return "invalid_target"
    if "필수" in message or "필요한" in message:
        return "missing_required_field"
    return "needs_manual_review"


def cafe24_status_requires_manual_input(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_MANUAL_INPUT_REQUIRED_STATUSES


def cafe24_status_requires_review(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_REVIEW_REQUIRED_STATUSES


def cafe24_status_in_progress(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_IN_PROGRESS_STATUSES


def cafe24_status_needs_operator_action(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_OPERATOR_ACTION_STATUSES


def cafe24_status_is_payment_blocked(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_PAYMENT_BLOCKED_STATUSES


def normalize_cafe24_status(raw: Any) -> str:
    value = str(raw or "").strip()
    if not value:
        return "received"
    if value in CAFE24_ORDER_UNPAID_STATUSES:
        return "received"
    if value.startswith(CAFE24_ORDER_CANCELLED_PREFIXES):
        return "cancelled"
    if value in CAFE24_ORDER_ELIGIBLE_STATUSES:
        return "validated"
    return "received"


def normalize_cafe24_payment_status(raw: Any) -> str:
    if isinstance(raw, bool):
        return "paid" if raw else "unpaid"
    value = str(raw or "").strip().lower()
    if value in CAFE24_PAYMENT_PAID_STATUSES:
        return "paid"
    if value in CAFE24_PAYMENT_CANCELLED_STATUSES:
        return "canceled"
    if value in CAFE24_PAYMENT_PENDING_STATUSES:
        return "unpaid"
    return value


def cafe24_payload_value(payload: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def cafe24_payload_collection(payload: Any, keys: Iterable[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = cafe24_payload_collection(value, keys)
                return nested or [value]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def cafe24_product_options_from_payload(payload: Any) -> List[Dict[str, Any]]:
    return cafe24_payload_collection(payload, ("options", "option", "option_values", "optionValues", "values"))


def cafe24_product_variants_from_payload(payload: Any) -> List[Dict[str, Any]]:
    return cafe24_payload_collection(payload, ("variants", "variant", "items", "item"))


def cafe24_option_payload(option: Dict[str, Any]) -> Dict[str, Any]:
    value_candidates = (
        option.get("option_values")
        or option.get("optionValues")
        or option.get("values")
        or option.get("value")
        or option.get("option_value")
        or ""
    )
    if isinstance(value_candidates, list):
        values = [
            str(value.get("option_text") or value.get("text") or value.get("value") or value.get("name") or value).strip()
            if isinstance(value, dict)
            else str(value).strip()
            for value in value_candidates
        ]
    else:
        values = [text.strip() for text in re.split(r"[,/|]", str(value_candidates or "")) if text.strip()]
    return {
        "name": cafe24_payload_value(option, ("option_name", "name", "label", "key")),
        "value": cafe24_payload_value(option, ("option_value", "value", "text", "option_text")),
        "values": values,
        "raw": option,
    }


def cafe24_variant_payload(variant: Dict[str, Any]) -> Dict[str, Any]:
    option_text = cafe24_payload_value(
        variant,
        ("options", "option_value", "option_values", "variant_option", "option_text", "option_name"),
    )
    return {
        "variantCode": cafe24_payload_value(variant, ("variant_code", "option_code", "item_code", "product_code")),
        "customProductCode": cafe24_payload_value(variant, ("custom_product_code", "custom_variant_code", "custom_item_code")),
        "productCode": cafe24_payload_value(variant, ("product_code", "item_code")),
        "optionText": option_text,
        "display": cafe24_payload_value(variant, ("display", "display_status", "use_display")),
        "selling": cafe24_payload_value(variant, ("selling", "selling_status", "use_selling")),
        "price": cafe24_payload_value(variant, ("price", "additional_amount", "option_price")),
        "stockQuantity": cafe24_payload_value(variant, ("quantity", "stock_quantity", "stock")),
        "raw": variant,
    }


def cafe24_product_payload(product: Dict[str, Any], *, include_raw: bool = False) -> Dict[str, Any]:
    raw_options = cafe24_product_options_from_payload(product.get("options") or product.get("option") or [])
    raw_variants = cafe24_product_variants_from_payload(product.get("variants") or product.get("variant") or [])
    payload = {
        "productNo": cafe24_payload_value(product, ("product_no", "product_id", "id")),
        "productName": cafe24_payload_value(product, ("product_name", "name", "display_product_name")),
        "productCode": cafe24_payload_value(product, ("product_code", "code")),
        "customProductCode": cafe24_payload_value(product, ("custom_product_code", "custom_code")),
        "price": cafe24_payload_value(product, ("price", "retail_price", "selling_price")),
        "display": cafe24_payload_value(product, ("display", "display_status", "use_display")),
        "selling": cafe24_payload_value(product, ("selling", "selling_status", "use_selling")),
        "options": [cafe24_option_payload(option) for option in raw_options],
        "variants": [cafe24_variant_payload(variant) for variant in raw_variants],
    }
    if include_raw:
        payload["raw"] = product
    return payload


def cafe24_enriched_product_payload(
    product: Dict[str, Any],
    *,
    option_response: Any = None,
    variant_response: Any = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    payload = cafe24_product_payload(product, include_raw=include_raw)
    if option_response is not None:
        options = [
            cafe24_option_payload(option)
            for option in cafe24_product_options_from_payload(option_response)
        ]
        if options:
            payload["options"] = options
    if variant_response is not None:
        variants = [
            cafe24_variant_payload(variant)
            for variant in cafe24_product_variants_from_payload(variant_response)
        ]
        if variants:
            payload["variants"] = variants
    return payload


def cafe24_supplier_dispatch_outcome(response_payload: Any) -> Dict[str, str]:
    supplier_external_order_id = ""
    next_status = "failed"
    error_message = ""
    if isinstance(response_payload, dict):
        supplier_external_order_id = str(
            response_payload.get("order")
            or response_payload.get("wr_id")
            or response_payload.get("id")
            or response_payload.get("orderUuid")
            or response_payload.get("order_uuid")
            or response_payload.get("uuid")
            or ""
        ).strip()
        if supplier_external_order_id:
            next_status = "supplier_submitted"
        elif response_payload:
            next_status = "needs_manual_review"
            error_message = "공급사 응답에 주문 ID가 없어 중복 여부 확인이 필요합니다."
        else:
            error_message = "공급사 응답이 비어 있습니다."
    elif response_payload not in (None, False, "", []):
        next_status = "needs_manual_review"
        error_message = "공급사 주문 ID를 확인할 수 없어 수동 확인이 필요합니다."
    else:
        error_message = "공급사 응답이 비어 있습니다."
    return {
        "status": next_status,
        "supplierExternalOrderId": supplier_external_order_id,
        "errorMessage": error_message,
    }


def cafe24_supplier_dispatch_state(
    outcome: Dict[str, str],
    *,
    supplier_auth_failed: bool = False,
    attempts_after: int = 1,
    max_attempts: int = 3,
    retry_at: str = "",
) -> Dict[str, str]:
    next_status = str(outcome.get("status") or "failed")
    error_message = str(outcome.get("errorMessage") or "")
    automation_error_code = ""
    next_retry_at = ""

    if supplier_auth_failed:
        next_status = "needs_manual_review"
        automation_error_code = "supplier_token_expired"
        error_message = error_message or "공급사 인증 토큰이 만료되었습니다. 공급사 설정에서 토큰을 갱신한 뒤 재발주하세요."

    if next_status == "failed":
        automation_error_code = "supplier_dispatch_failed"
        if int(attempts_after or 0) >= int(max_attempts or 0):
            next_status = "needs_manual_review"
            error_message = (error_message or "공급사 발주 실패") + " · 자동 재시도 한도를 초과해 수동 확인이 필요합니다."
        else:
            next_retry_at = retry_at
    elif next_status == "needs_manual_review" and not automation_error_code:
        automation_error_code = "supplier_response_ambiguous"

    return {
        "status": next_status,
        "errorMessage": error_message,
        "automationErrorCode": automation_error_code,
        "nextRetryAt": next_retry_at,
    }


def cafe24_dispatch_duplicate_response(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row_map = dict(row or {})
    standard_status = str(row_map.get("standard_status") or "")
    supplier_order_uuid = str(row_map.get("supplier_order_uuid") or "").strip()
    if supplier_order_uuid or standard_status in {"supplier_submitted", "supplier_progress", "completed"}:
        return {
            "id": row_map.get("id") or "",
            "status": standard_status,
            "submitted": False,
            "duplicate": True,
            "supplierOrderUuid": supplier_order_uuid,
        }
    return None


def cafe24_dispatch_request_context(row: Dict[str, Any], request_payload: Any) -> Dict[str, Any]:
    row_map = dict(row or {})
    duplicate_response = cafe24_dispatch_duplicate_response(row_map)
    if duplicate_response is not None:
        return {
            "duplicate": True,
            "response": duplicate_response,
            "requestPayload": request_payload if isinstance(request_payload, dict) else {},
            "retryingTokenExpired": False,
        }
    if str(row_map.get("payment_gate_status") or "") != "payment_confirmed":
        raise Cafe24DispatchRequestError("Cafe24 결제완료가 확인되지 않아 발주할 수 없습니다.")
    current_standard_status = str(row_map.get("standard_status") or "")
    retrying_token_expired = (
        current_standard_status == "needs_manual_review"
        and str(row_map.get("automation_error_code") or "") == "supplier_token_expired"
    )
    if current_standard_status not in {"ready_to_submit", "failed"} and not retrying_token_expired:
        raise Cafe24DispatchRequestError("발주 가능한 상태가 아닙니다. 먼저 재검증을 실행해 주세요.")
    if not bool(row_map.get("supplier_is_active")):
        raise Cafe24DispatchRequestError("연결된 공급사가 비활성 상태입니다.")
    if not isinstance(request_payload, dict) or not request_payload:
        raise Cafe24DispatchRequestError("공급사 발주 payload가 없습니다. 먼저 재검증을 실행해 주세요.")
    if not str(row_map.get("supplier_id") or "").strip() or not str(row_map.get("supplier_external_service_id") or "").strip():
        raise Cafe24DispatchRequestError("공급사 서비스 매핑이 없습니다.")
    return {
        "duplicate": False,
        "response": None,
        "requestPayload": request_payload,
        "retryingTokenExpired": retrying_token_expired,
    }


def cafe24_products_from_payload(payload: Any) -> List[Dict[str, Any]]:
    return cafe24_payload_collection(payload, ("products", "product"))


def cafe24_orders_from_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("orders", "order"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return [value]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def cafe24_order_items_from_order(order_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("items", "item", "order_items", "orderItems"):
        value = order_payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    return [order_payload]


def cafe24_order_has_embedded_items(order_payload: Dict[str, Any]) -> bool:
    return any(
        isinstance(order_payload.get(key), (list, dict))
        for key in ("items", "item", "order_items", "orderItems")
    )


def _cafe24_row_value(row: Dict[str, Any], key: str, default: Any = "") -> Any:
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _cafe24_parse_json(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return fallback


def _cafe24_money(value: Any) -> str:
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,}원"


def _cafe24_mask_email(email: Any) -> str:
    raw = str(email or "").strip()
    if not raw or "@" not in raw:
        return ""
    local, domain = raw.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(2, len(local) - 2)
    return f"{masked_local}@{domain}"


def _cafe24_mask_phone(phone: Any) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 7:
        return ""
    if len(digits) >= 11:
        return f"{digits[:3]}-****-{digits[-4:]}"
    return f"{digits[:3]}-***-{digits[-4:]}"


def _cafe24_mask_secret(secret: Any, visible_suffix: int = 4) -> str:
    raw = str(secret or "").strip()
    if not raw:
        return ""
    suffix = raw[-visible_suffix:] if len(raw) > visible_suffix else raw
    return "*" * max(4, len(raw) - len(suffix)) + suffix


def cafe24_redact_external_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        sensitive_tokens = ("token", "secret", "password", "authorization", "access_token", "refresh_token")
        for key, item in value.items():
            lower = str(key).lower()
            if any(token in lower for token in sensitive_tokens):
                redacted[key] = _cafe24_mask_secret(item, 4)
            elif "email" in lower:
                redacted[key] = _cafe24_mask_email(item)
            elif "phone" in lower or "mobile" in lower or "tel" in lower:
                redacted[key] = _cafe24_mask_phone(item)
            else:
                redacted[key] = cafe24_redact_external_payload(item)
        return redacted
    if isinstance(value, list):
        return [cafe24_redact_external_payload(item) for item in value]
    return value


def cafe24_integration_payload_from_row(
    row: Dict[str, Any],
    *,
    default_shop_no: int = CAFE24_DEFAULT_SHOP_NO,
    auto_poll_interval_minutes: int = CAFE24_AUTO_POLL_INTERVAL_MINUTES,
) -> Dict[str, Any]:
    return {
        "id": _cafe24_row_value(row, "id"),
        "mallId": _cafe24_row_value(row, "mall_id"),
        "shopNo": int(_cafe24_row_value(row, "shop_no", default_shop_no) or default_shop_no),
        "scopes": _cafe24_parse_json(_cafe24_row_value(row, "scopes_json"), []),
        "hasAccessToken": bool(_cafe24_row_value(row, "access_token")),
        "hasRefreshToken": bool(_cafe24_row_value(row, "refresh_token")),
        "accessTokenMasked": _cafe24_mask_secret(_cafe24_row_value(row, "access_token")),
        "refreshTokenMasked": _cafe24_mask_secret(_cafe24_row_value(row, "refresh_token")),
        "expiresAt": _cafe24_row_value(row, "expires_at"),
        "refreshTokenExpiresAt": _cafe24_row_value(row, "refresh_token_expires_at"),
        "lastPollAt": _cafe24_row_value(row, "last_poll_at"),
        "pollCursor": _cafe24_row_value(row, "poll_cursor"),
        "autoSubmit": bool(_cafe24_row_value(row, "auto_submit")),
        "completionPolicy": _cafe24_row_value(row, "completion_policy", "memo_only") or "memo_only",
        "tokenStatus": cafe24_token_status(row),
        "tokenStatusLabel": cafe24_token_status_label(row),
        "tokenStatusMessage": cafe24_token_status_message(row),
        "tokenLastCheckedAt": _cafe24_row_value(row, "token_last_checked_at"),
        "tokenLastRefreshedAt": _cafe24_row_value(row, "token_last_refreshed_at"),
        "tokenRefreshLockUntil": _cafe24_row_value(row, "token_refresh_lock_until"),
        "reconnectRequiredAt": _cafe24_row_value(row, "reconnect_required_at"),
        "reconnectReason": _cafe24_row_value(row, "reconnect_reason"),
        "cafe24PollLockUntil": _cafe24_row_value(row, "cafe24_poll_lock_until"),
        "lastAutoPollAt": _cafe24_row_value(row, "last_auto_poll_at"),
        "lastAutoPollStatus": _cafe24_row_value(row, "last_auto_poll_status", "never") or "never",
        "lastAutoPollMessage": _cafe24_row_value(row, "last_auto_poll_message"),
        "nextAutoPollAt": cafe24_next_auto_poll_at(row, interval_minutes=auto_poll_interval_minutes),
        "autoPollIntervalMinutes": auto_poll_interval_minutes,
        "isActive": bool(_cafe24_row_value(row, "is_active")),
        "lastSyncStatus": _cafe24_row_value(row, "last_sync_status", "never") or "never",
        "lastSyncMessage": _cafe24_row_value(row, "last_sync_message"),
        "createdAt": _cafe24_row_value(row, "created_at"),
        "updatedAt": _cafe24_row_value(row, "updated_at"),
    }


def cafe24_mapping_payload_from_row(
    row: Dict[str, Any],
    *,
    default_shop_no: int = CAFE24_DEFAULT_SHOP_NO,
) -> Dict[str, Any]:
    return {
        "id": _cafe24_row_value(row, "id"),
        "mallId": _cafe24_row_value(row, "mall_id"),
        "shopNo": int(_cafe24_row_value(row, "shop_no", default_shop_no) or default_shop_no),
        "cafe24ProductNo": _cafe24_row_value(row, "cafe24_product_no"),
        "cafe24VariantCode": _cafe24_row_value(row, "cafe24_variant_code"),
        "cafe24CustomProductCode": _cafe24_row_value(row, "cafe24_custom_product_code"),
        "internalProductId": _cafe24_row_value(row, "internal_product_id"),
        "internalProductName": _cafe24_row_value(row, "internal_product_name"),
        "internalOptionName": _cafe24_row_value(row, "internal_option_name"),
        "supplierId": _cafe24_row_value(row, "supplier_id"),
        "supplierName": _cafe24_row_value(row, "supplier_name"),
        "supplierServiceId": _cafe24_row_value(row, "supplier_service_id"),
        "supplierServiceName": _cafe24_row_value(row, "supplier_service_name"),
        "supplierServiceExternalId": _cafe24_row_value(
            row,
            "supplier_service_external_id",
            _cafe24_row_value(row, "supplier_external_service_id"),
        ),
        "supplierExternalServiceId": _cafe24_row_value(row, "supplier_external_service_id"),
        "supplierProductUuid": _cafe24_row_value(row, "supplier_product_uuid"),
        "supplierProductCode": _cafe24_row_value(row, "supplier_product_code"),
        "fieldMapping": _cafe24_parse_json(_cafe24_row_value(row, "field_mapping_json"), {}),
        "fieldMappingJson": _cafe24_row_value(row, "field_mapping_json", "{}") or "{}",
        "autoDispatchEnabled": bool(_cafe24_row_value(row, "auto_dispatch_enabled")),
        "enabled": bool(_cafe24_row_value(row, "enabled")),
        "createdAt": _cafe24_row_value(row, "created_at"),
        "updatedAt": _cafe24_row_value(row, "updated_at"),
    }


def cafe24_target_diagnostics(
    normalized_fields: Dict[str, Any],
    supplier_payload: Dict[str, Any],
    *,
    supplier_response: Dict[str, Any] | None = None,
    error_message: Any = "",
    standard_status: Any = "",
) -> Dict[str, Any]:
    supplier_response = supplier_response if isinstance(supplier_response, dict) else {}
    target_input = (
        str(normalized_fields.get("targetUrl") or "")
        or str(normalized_fields.get("targetValue") or "")
        or str(normalized_fields.get("snsValue") or "")
        or str(normalized_fields.get("link") or "")
    ).strip()
    supplier_link = (
        str(supplier_payload.get("link") or "")
        or str(supplier_payload.get("snsValue") or "")
        or str(supplier_payload.get("targetUrl") or "")
    ).strip()
    response_reason = supplier_response.get("reason") if isinstance(supplier_response, dict) else {}
    if not isinstance(response_reason, dict):
        response_reason = {}
    target_message = str(error_message or "").strip()
    response_status = str(supplier_response.get("status") or supplier_response.get("Status") or "").strip()
    reason_code = str(response_reason.get("code") or "").strip()
    reason_message = str(response_reason.get("message") or response_reason.get("detail") or "").strip()
    if not target_message and (reason_code or reason_message):
        target_message = " / ".join(filter(None, [reason_code, reason_message]))
    status_value = str(standard_status or "")
    target_status = "ok"
    if status_value == "invalid_target":
        target_status = "invalid"
    elif response_status.lower() in {"canceled", "cancelled"} or reason_code:
        target_status = "supplier_rejected"
    elif target_input and supplier_link and target_input != supplier_link:
        target_status = "normalized"
    elif target_input and not supplier_link and status_value in {"ready_to_submit", "missing_required_field"}:
        target_status = "missing"
    return {
        "input": target_input,
        "supplierLink": supplier_link,
        "status": target_status,
        "message": target_message,
        "supplierStatus": response_status,
        "supplierReasonCode": reason_code,
        "supplierReasonMessage": reason_message,
        "normalized": bool(target_input and supplier_link and target_input != supplier_link),
    }


def cafe24_order_item_payload_from_row(
    row: Dict[str, Any],
    *,
    default_shop_no: int = CAFE24_DEFAULT_SHOP_NO,
) -> Dict[str, Any]:
    raw_payload = _cafe24_parse_json(_cafe24_row_value(row, "raw_payload_json"), {})
    normalized_fields = _cafe24_parse_json(_cafe24_row_value(row, "normalized_fields_json"), {})
    supplier_payload = _cafe24_parse_json(_cafe24_row_value(row, "supplier_payload_json"), {})
    supplier_response = _cafe24_parse_json(_cafe24_row_value(row, "supplier_response_json"), {})
    if not isinstance(normalized_fields, dict):
        normalized_fields = {}
    if not isinstance(supplier_payload, dict):
        supplier_payload = {}
    if not isinstance(supplier_response, dict):
        supplier_response = {}
    standard_status = str(_cafe24_row_value(row, "standard_status") or "")
    target_diagnostics = cafe24_target_diagnostics(
        normalized_fields,
        supplier_payload,
        supplier_response=supplier_response,
        error_message=_cafe24_row_value(row, "error_message"),
        standard_status=standard_status,
    )
    payment_amount = int(_cafe24_row_value(row, "payment_amount", 0) or 0)
    shop_no = normalize_cafe24_shop_no(_cafe24_row_value(row, "shop_no", default_shop_no))
    payload = {
        "id": _cafe24_row_value(row, "id"),
        "mallId": _cafe24_row_value(row, "mall_id"),
        "shopNo": shop_no,
        "orderId": _cafe24_row_value(row, "cafe24_order_id"),
        "orderItemCode": _cafe24_row_value(row, "cafe24_order_item_code"),
        "productNo": _cafe24_row_value(row, "cafe24_product_no"),
        "variantCode": _cafe24_row_value(row, "cafe24_variant_code"),
        "customProductCode": _cafe24_row_value(row, "cafe24_custom_product_code"),
        "orderDate": _cafe24_row_value(row, "cafe24_order_date"),
        "buyerName": _cafe24_row_value(row, "buyer_name"),
        "buyerEmailMasked": _cafe24_mask_email(_cafe24_row_value(row, "buyer_email")),
        "buyerPhoneMasked": _cafe24_mask_phone(_cafe24_row_value(row, "buyer_phone")),
        "receiverName": _cafe24_row_value(row, "receiver_name"),
        "orderStatusCode": _cafe24_row_value(row, "order_status_code"),
        "paymentStatus": _cafe24_row_value(row, "payment_status"),
        "paymentStatusSource": _cafe24_row_value(row, "payment_status_source"),
        "paymentGateStatus": _cafe24_row_value(row, "payment_gate_status"),
        "paymentMethod": _cafe24_row_value(row, "payment_method"),
        "paymentAmount": payment_amount,
        "paymentAmountLabel": _cafe24_money(payment_amount),
        "paymentPaidAt": _cafe24_row_value(row, "payment_paid_at"),
        "paymentReference": _cafe24_row_value(row, "payment_reference"),
        "paymentSnapshot": _cafe24_parse_json(_cafe24_row_value(row, "payment_snapshot_json"), {}),
        "sourceStatus": _cafe24_row_value(row, "source_status"),
        "standardStatus": standard_status,
        "internalOrderId": _cafe24_row_value(row, "internal_order_id"),
        "mappingId": _cafe24_row_value(row, "mapping_id"),
        "productId": _cafe24_row_value(row, "product_id"),
        "supplierId": _cafe24_row_value(row, "supplier_id"),
        "supplierServiceId": _cafe24_row_value(row, "supplier_service_id"),
        "supplierExternalServiceId": _cafe24_row_value(row, "supplier_external_service_id"),
        "internalProductName": _cafe24_row_value(row, "internal_product_name"),
        "internalOptionName": _cafe24_row_value(row, "internal_option_name"),
        "normalizedFields": normalized_fields,
        "supplierPayload": supplier_payload,
        "supplierResponse": supplier_response,
        "targetDiagnostics": target_diagnostics,
        "rawPayloadPreview": cafe24_redact_external_payload(raw_payload),
        "errorMessage": _cafe24_row_value(row, "error_message"),
        "retryCount": int(_cafe24_row_value(row, "retry_count", 0) or 0),
        "nextRetryAt": _cafe24_row_value(row, "next_retry_at"),
        "automationLastCheckedAt": _cafe24_row_value(row, "automation_last_checked_at"),
        "automationErrorCode": _cafe24_row_value(row, "automation_error_code"),
        "autoDispatchApproved": bool(_cafe24_row_value(row, "auto_dispatch_approved", 0)),
        "autoDispatchSource": _cafe24_row_value(row, "auto_dispatch_source"),
        "preflightCheckedAt": _cafe24_row_value(row, "preflight_checked_at"),
        "preflightBlockers": _cafe24_parse_json(_cafe24_row_value(row, "preflight_blockers_json"), []),
        "supplierOrderId": _cafe24_row_value(row, "supplier_order_id"),
        "supplierOrderUuid": _cafe24_row_value(row, "supplier_order_uuid"),
        "lastSubmittedAt": _cafe24_row_value(row, "last_submitted_at"),
        "cafe24CompletionStatus": _cafe24_row_value(row, "cafe24_completion_status") or "pending",
        "cafe24CompletionMessage": _cafe24_row_value(row, "cafe24_completion_message"),
        "cafe24CompletedAt": _cafe24_row_value(row, "cafe24_completed_at"),
        "cafe24CompletionAttempts": int(_cafe24_row_value(row, "cafe24_completion_attempts", 0) or 0),
        "cafe24NextCompletionRetryAt": _cafe24_row_value(row, "cafe24_next_completion_retry_at"),
        "lastSyncedAt": _cafe24_row_value(row, "last_synced_at"),
        "createdAt": _cafe24_row_value(row, "created_at"),
        "updatedAt": _cafe24_row_value(row, "updated_at"),
    }
    payload["searchText"] = " ".join(
        filter(
            None,
            [
                str(payload["mallId"] or ""),
                str(payload["shopNo"] or ""),
                str(payload["orderId"] or ""),
                str(payload["orderItemCode"] or ""),
                str(payload["productNo"] or ""),
                str(payload["variantCode"] or ""),
                str(payload["customProductCode"] or ""),
                str(payload["orderDate"] or ""),
                str(payload["buyerName"] or ""),
                str(payload["internalProductName"] or ""),
                str(payload["standardStatus"] or ""),
                str(payload["paymentStatus"] or ""),
                str(payload["paymentGateStatus"] or ""),
                str(payload["paymentMethod"] or ""),
                str(payload["paymentReference"] or ""),
                str(payload["errorMessage"] or ""),
            ],
        )
    ).lower()
    return payload


def cafe24_item_code(order_payload: Dict[str, Any], item_payload: Dict[str, Any], index: int) -> str:
    code = cafe24_payload_value(
        item_payload,
        ("order_item_code", "order_item_id", "item_code", "variant_code", "product_code"),
    )
    if code:
        return code
    return f"{cafe24_payload_value(order_payload, ('order_id', 'order_no', 'id'))}_{index}"


def cafe24_item_identity(order_payload: Dict[str, Any], item_payload: Dict[str, Any], index: int) -> Dict[str, str]:
    return {
        "orderId": cafe24_payload_value(order_payload, ("order_id", "order_no", "id")),
        "orderItemCode": cafe24_item_code(order_payload, item_payload, index),
        "productNo": cafe24_payload_value(item_payload, ("product_no", "product_id")),
        "variantCode": cafe24_payload_value(item_payload, ("variant_code", "option_code", "variant_id")),
        "customProductCode": cafe24_payload_value(
            item_payload,
            ("custom_product_code", "custom_product_code_display", "product_code", "item_code"),
        ),
        "statusCode": cafe24_payload_value(item_payload, ("order_status", "status", "order_status_code"))
        or cafe24_payload_value(order_payload, ("order_status", "status", "order_status_code")),
    }


def cafe24_option_entries(order_payload: Dict[str, Any], item_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []

    def add_entry(label: Any, value: Any, source: str) -> None:
        key = str(label or "").strip()
        text = str(value or "").strip()
        if key and text:
            entries.append({"label": key, "value": text, "source": source})

    def consume(value: Any, prefix: str = "", source: str = "") -> None:
        if isinstance(value, dict):
            label = value.get("name") or value.get("option_name") or value.get("label") or value.get("key")
            text = value.get("value") or value.get("option_value") or value.get("text") or value.get("input_value")
            if label or text:
                add_entry(label or prefix or "option", text, source or prefix or "option")
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, (dict, list)):
                    consume(nested_value, str(nested_key), f"{source}.{nested_key}" if source else str(nested_key))
        elif isinstance(value, list):
            for item in value:
                consume(item, prefix, source or prefix)
        elif isinstance(value, str):
            for part in re.split(r"[\n\r,|/]+", value):
                cleaned = part.strip()
                if not cleaned:
                    continue
                if ":" in cleaned:
                    left, right = cleaned.split(":", 1)
                    add_entry(left, right, source or prefix or "option")
                elif "=" in cleaned:
                    left, right = cleaned.split("=", 1)
                    add_entry(left, right, source or prefix or "option")
                else:
                    add_entry(prefix or "option", cleaned, source or prefix or "option")

    for key in (
        "options",
        "option",
        "option_value",
        "option_value_default",
        "option_text",
        "selected_options",
        "variant_option",
        "variant_options",
        "additional_option_values",
        "additional_options",
        "input_options",
        "custom_options",
    ):
        consume(item_payload.get(key), key, f"item.{key}")
    consume(order_payload.get("memo"), "orderMemo", "order.memo")
    return entries


def cafe24_option_pairs(order_payload: Dict[str, Any], item_payload: Dict[str, Any]) -> Dict[str, str]:
    pairs: Dict[str, str] = {}
    for entry in cafe24_option_entries(order_payload, item_payload):
        pairs[entry["label"]] = entry["value"]
    return pairs


def cafe24_payment_status_from_payload(order_payload: Dict[str, Any], item_payload: Dict[str, Any]) -> str:
    for payload in (item_payload, order_payload):
        if not isinstance(payload, dict):
            continue
        direct = cafe24_payload_value(
            payload,
            ("payment_status", "paymentStatus", "payment_state", "paymentState", "paid_status", "paidStatus"),
        )
        if direct:
            return normalize_cafe24_payment_status(direct)
        paid_value = payload.get("paid")
        if isinstance(paid_value, bool):
            return normalize_cafe24_payment_status(paid_value)
        payment = payload.get("payment")
        if isinstance(payment, dict):
            nested = cafe24_payload_value(payment, ("status", "payment_status", "state", "paid_status"))
            if nested:
                return normalize_cafe24_payment_status(nested)
            nested_paid = payment.get("paid")
            if isinstance(nested_paid, bool):
                return normalize_cafe24_payment_status(nested_paid)
    return ""


def cafe24_payment_amount_value(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def cafe24_payment_snapshot_from_payload(order_payload: Dict[str, Any], item_payload: Dict[str, Any]) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for payload in (item_payload, order_payload):
        if not isinstance(payload, dict):
            continue
        candidates.append(payload)
        for nested_key in ("payment", "payment_info", "paymentInfo", "payment_detail", "paymentDetail"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                candidates.append(nested)
            elif isinstance(nested, list):
                candidates.extend(item for item in nested if isinstance(item, dict))
    method = ""
    amount = 0
    paid_at = ""
    reference = ""
    for candidate in candidates:
        if not method:
            method = str(
                cafe24_payload_value(
                    candidate,
                    (
                        "payment_method",
                        "paymentMethod",
                        "payment_method_name",
                        "paymentMethodName",
                        "pay_method",
                        "payMethod",
                        "paymethod",
                        "payment_gateway",
                        "paymentGateway",
                    ),
                )
                or ""
            ).strip()
        if not amount:
            amount = cafe24_payment_amount_value(
                cafe24_payload_value(
                    candidate,
                    (
                        "payment_amount",
                        "paymentAmount",
                        "paid_amount",
                        "paidAmount",
                        "actual_payment_amount",
                        "actualPaymentAmount",
                        "order_price_amount",
                        "orderPriceAmount",
                        "total_amount",
                        "totalAmount",
                        "amount",
                    ),
                )
            )
        if not paid_at:
            paid_at = str(
                cafe24_payload_value(
                    candidate,
                    (
                        "paid_at",
                        "paidAt",
                        "payment_date",
                        "paymentDate",
                        "payment_complete_date",
                        "paymentCompleteDate",
                        "payment_confirmed_at",
                        "paymentConfirmedAt",
                        "paid_date",
                        "paidDate",
                    ),
                )
                or ""
            ).strip()
        if not reference:
            reference = str(
                cafe24_payload_value(
                    candidate,
                    (
                        "pg_tid",
                        "pgTid",
                        "transaction_id",
                        "transactionId",
                        "payment_id",
                        "paymentId",
                        "approval_no",
                        "approvalNo",
                        "receipt_id",
                        "receiptId",
                    ),
                )
                or ""
            ).strip()
    return {
        "method": method,
        "amount": amount,
        "paidAt": paid_at,
        "reference": reference,
    }


def cafe24_normalize_datetime_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("T", " ")
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
            return f"{raw} 00:00:00"
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", normalized):
            return normalized[:19]
    return raw[:19]


def cafe24_order_date_from_payload(order_payload: Dict[str, Any], item_payload: Dict[str, Any]) -> str:
    candidates: List[Dict[str, Any]] = []
    for payload in (item_payload, order_payload):
        if isinstance(payload, dict):
            candidates.append(payload)
    keys = (
        "order_date",
        "orderDate",
        "ordered_date",
        "orderedDate",
        "created_date",
        "createdDate",
        "created_at",
        "createdAt",
        "order_datetime",
        "orderDatetime",
        "date",
    )
    for candidate in candidates:
        value = cafe24_payload_value(candidate, keys)
        if value:
            return cafe24_normalize_datetime_text(value)
    payment_snapshot = cafe24_payment_snapshot_from_payload(order_payload, item_payload)
    return cafe24_normalize_datetime_text(payment_snapshot.get("paidAt"))


def cafe24_status_is_supply_eligible(raw: Any) -> bool:
    return str(raw or "").strip() in CAFE24_ORDER_ELIGIBLE_STATUSES


def cafe24_status_is_cancelled(raw: Any) -> bool:
    value = str(raw or "").strip()
    return bool(value) and value.startswith(CAFE24_ORDER_CANCELLED_PREFIXES)


def cafe24_payment_gate_status(order_status: Any, payment_status: Any) -> str:
    order_value = str(order_status or "").strip()
    normalized_payment = normalize_cafe24_payment_status(payment_status)
    if cafe24_status_is_cancelled(order_value) or normalized_payment == "canceled":
        return "cancelled"
    if order_value in CAFE24_ORDER_UNPAID_STATUSES or normalized_payment == "unpaid":
        return "payment_pending"
    if order_value in CAFE24_ORDER_ELIGIBLE_STATUSES and normalized_payment == "paid":
        return "payment_confirmed"
    return "payment_review_required"


def cafe24_payment_status_with_source(order_payload: Dict[str, Any], item_payload: Dict[str, Any], order_status: Any) -> Tuple[str, str]:
    payment_status = cafe24_payment_status_from_payload(order_payload, item_payload)
    if payment_status:
        return payment_status, "payload"
    if cafe24_status_is_supply_eligible(order_status):
        return "paid", "order_status"
    return "", "missing"


class Cafe24ApiClient:
    def __init__(
        self,
        mall_id: str,
        access_token: str,
        *,
        shop_no: int = CAFE24_DEFAULT_SHOP_NO,
        request_timeout_seconds: float = 15,
        max_attempts: int = 3,
    ) -> None:
        self.mall_id = str(mall_id or "").strip()
        self.access_token = str(access_token or "").strip()
        self.shop_no = int(shop_no or CAFE24_DEFAULT_SHOP_NO)
        self.request_timeout_seconds = max(float(request_timeout_seconds or 15), 1.0)
        self.max_attempts = max(int(max_attempts or 3), 1)
        if not self.mall_id:
            raise Cafe24ApiError("Cafe24 mall_id가 필요합니다.")
        if not self.access_token:
            raise Cafe24ApiError("Cafe24 access token이 필요합니다.")
        self.base_url = cafe24_api_base_url(self.mall_id)

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        normalized_path = "/" + path.lstrip("/")
        url = f"{self.base_url}{normalized_path}"
        params = dict(query or {})
        params.setdefault("shop_no", self.shop_no)
        if params:
            url = f"{url}?{urlencode({key: value for key, value in params.items() if value not in (None, '')}, doseq=True)}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        raw = ""
        for attempt in range(self.max_attempts):
            request = Request(url, data=data, headers=headers, method=method.upper())
            try:
                with urlopen(request, timeout=self.request_timeout_seconds) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                break
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_attempts - 1:
                    retry_after = str(exc.headers.get("Retry-After") or "").strip() if exc.headers else ""
                    try:
                        delay = min(max(float(retry_after), 0.5), 3.0) if retry_after else 0.5 * (attempt + 1)
                    except ValueError:
                        delay = 0.5 * (attempt + 1)
                    time.sleep(delay)
                    continue
                raise Cafe24ApiError(f"Cafe24 API 오류 {exc.code}: {body or exc.reason}") from exc
            except (URLError, TimeoutError, ValueError) as exc:
                if attempt < self.max_attempts - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise Cafe24ApiError(str(exc)) from exc
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise Cafe24ApiError("Cafe24 API가 JSON이 아닌 응답을 반환했습니다.") from exc
        if isinstance(parsed, dict) and parsed.get("error"):
            error = parsed.get("error")
            if isinstance(error, dict):
                raise Cafe24ApiError(str(error.get("message") or error.get("description") or error))
            raise Cafe24ApiError(str(error))
        return parsed

    @staticmethod
    def exchange_authorization_code(mall_id: str, code: str, redirect_uri: str) -> Dict[str, Any]:
        client_id = cafe24_client_id()
        client_secret = cafe24_client_secret()
        if not client_id or not client_secret:
            raise Cafe24ApiError("SMM_PANEL_CAFE24_CLIENT_ID / SMM_PANEL_CAFE24_CLIENT_SECRET 설정이 필요합니다.")
        if not str(code or "").strip():
            raise Cafe24ApiError("Cafe24 인증 code가 없습니다.")
        if not str(redirect_uri or "").strip():
            raise Cafe24ApiError("Cafe24 redirect_uri가 없습니다.")
        token_url = f"{cafe24_api_base_url(mall_id)}/oauth/token"
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        data = urlencode(
            {
                "grant_type": "authorization_code",
                "code": str(code).strip(),
                "redirect_uri": str(redirect_uri).strip(),
            }
        ).encode("utf-8")
        request = Request(
            token_url,
            data=data,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise Cafe24ApiError(f"Cafe24 토큰 발급 실패 {exc.code}: {body or exc.reason}") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise Cafe24ApiError(str(exc)) from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise Cafe24ApiError("Cafe24 토큰 응답 형식이 올바르지 않습니다.") from exc
        if not isinstance(parsed, dict) or not parsed.get("access_token"):
            raise Cafe24ApiError("Cafe24 access token을 발급하지 못했습니다.")
        return parsed

    @staticmethod
    def refresh_access_token(mall_id: str, refresh_token: str) -> Dict[str, Any]:
        client_id = cafe24_client_id()
        client_secret = cafe24_client_secret()
        if not client_id or not client_secret:
            raise Cafe24ApiError("SMM_PANEL_CAFE24_CLIENT_ID / SMM_PANEL_CAFE24_CLIENT_SECRET 설정이 필요합니다.")
        token_url = f"{cafe24_api_base_url(mall_id)}/oauth/token"
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        data = urlencode({"grant_type": "refresh_token", "refresh_token": refresh_token}).encode("utf-8")
        request = Request(
            token_url,
            data=data,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise Cafe24ApiError(f"Cafe24 토큰 갱신 실패 {exc.code}: {body or exc.reason}") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise Cafe24ApiError(str(exc)) from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise Cafe24ApiError("Cafe24 토큰 응답 형식이 올바르지 않습니다.") from exc
        if not isinstance(parsed, dict) or not parsed.get("access_token"):
            raise Cafe24ApiError("Cafe24 access token을 갱신하지 못했습니다.")
        return parsed

    def orders(
        self,
        *,
        start_date: str,
        end_date: str,
        statuses: Optional[List[str]] = None,
        payment_statuses: Optional[List[str]] = None,
        order_id: str = "",
        limit: int = CAFE24_ORDER_PAGE_LIMIT,
        offset: int = 0,
        date_type: str = "order_date",
    ) -> Any:
        query: Dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "date_type": str(date_type or "order_date").strip() or "order_date",
            "limit": min(max(int(limit or CAFE24_ORDER_PAGE_LIMIT), 1), CAFE24_ORDER_PAGE_LIMIT),
            "offset": max(int(offset or 0), 0),
            "embed": "items,buyer,receivers",
        }
        if statuses:
            query["order_status"] = ",".join(statuses)
        if payment_statuses:
            query["payment_status"] = ",".join(payment_statuses)
        normalized_order_id = str(order_id or "").strip()
        if normalized_order_id:
            query["order_id"] = normalized_order_id
        return self._request("GET", "/admin/orders", query=query)

    def order(self, order_id: str) -> Any:
        return self._request(
            "GET",
            f"/admin/orders/{quote(str(order_id), safe='')}",
            query={"embed": "items,buyer,receivers"},
        )

    def order_count(
        self,
        *,
        start_date: str,
        end_date: str,
        statuses: Optional[List[str]] = None,
        payment_statuses: Optional[List[str]] = None,
        date_type: str = "order_date",
    ) -> Any:
        query: Dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "date_type": str(date_type or "order_date").strip() or "order_date",
        }
        if statuses:
            query["order_status"] = ",".join(statuses)
        if payment_statuses:
            query["payment_status"] = ",".join(payment_statuses)
        return self._request("GET", "/admin/orders/count", query=query)

    def update_order(self, order_id: str, payload: Dict[str, Any]) -> Any:
        return self._request("PUT", f"/admin/orders/{quote(str(order_id), safe='')}", payload=payload)

    def confirm_purchase(self, order_id: str, order_item_code: str, *, collect_points: str = "F") -> Any:
        return self.update_order(
            order_id,
            {
                "order": {
                    "order_item_code": str(order_item_code or "").strip(),
                    "purchase_confirmation": "T",
                    "collect_points": str(collect_points or "F").strip() or "F",
                }
            },
        )

    def products(self, *, keyword: str = "", product_no: str = "", limit: int = 20, offset: int = 0) -> Any:
        query: Dict[str, Any] = {
            "limit": min(max(int(limit or 20), 1), 100),
            "offset": max(int(offset or 0), 0),
        }
        normalized_product_no = str(product_no or "").strip()
        normalized_keyword = str(keyword or "").strip()
        if normalized_product_no:
            query["product_no"] = normalized_product_no
        elif normalized_keyword:
            if normalized_keyword.isdigit():
                query["product_no"] = normalized_keyword
            else:
                query["product_name"] = normalized_keyword
        return self._request("GET", "/admin/products", query=query)

    def product(self, product_no: str) -> Any:
        return self._request("GET", f"/admin/products/{quote(str(product_no), safe='')}")

    def product_options(self, product_no: str) -> Any:
        return self._request("GET", f"/admin/products/{quote(str(product_no), safe='')}/options")

    def product_variants(self, product_no: str) -> Any:
        return self._request("GET", f"/admin/products/{quote(str(product_no), safe='')}/variants")
