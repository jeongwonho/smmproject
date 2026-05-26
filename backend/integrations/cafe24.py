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
CAFE24_ORDER_PAGE_LIMIT = 1000
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
