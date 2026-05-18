from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


SUPPLIER_INTEGRATION_CLASSIC = "classic"
SUPPLIER_INTEGRATION_MKT24 = "mkt24"
SUPPLIER_SERVICE_SYNC_DEFAULT_INTERVAL_MINUTES = 30
SUPPLIER_SERVICE_SYNC_LOCK_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_BASE_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_MAX_MINUTES = 60
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


class SupplierApiError(Exception):
    pass


def supplier_http_error_message(status_code: int, payload: Any, fallback: str = "") -> str:
    if isinstance(payload, dict):
        code = str(payload.get("code") or payload.get("error") or "").strip()
        message = str(payload.get("message") or payload.get("error_description") or "").strip()
        trace_uuid = str(payload.get("uuid") or payload.get("traceId") or payload.get("trace_id") or "").strip()
        if code == "token_expired":
            detail = "공급사 Bearer Token이 만료되었습니다. 관리자 공급사 설정에서 새 Bearer Token을 저장한 뒤 연결 확인과 서비스 동기화를 다시 실행해 주세요."
            return f"{detail} 추적 UUID: {trace_uuid}" if trace_uuid else detail
        if message:
            return message
        if code:
            return f"공급사 API 오류 코드 {code}" + (f" · 추적 UUID: {trace_uuid}" if trace_uuid else "")
        redacted = _redact_external_payload(payload)
        return str(redacted)
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return fallback or f"공급사 API 요청이 실패했습니다. HTTP {status_code}"


def parse_iso_datetime(value: Any) -> Optional[dt.datetime]:
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


def normalize_supplier_integration_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value == SUPPLIER_INTEGRATION_MKT24:
        return SUPPLIER_INTEGRATION_MKT24
    return SUPPLIER_INTEGRATION_CLASSIC


def supplier_supports_balance_check(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) == SUPPLIER_INTEGRATION_CLASSIC


def supplier_supports_auto_dispatch(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) == SUPPLIER_INTEGRATION_CLASSIC


def supplier_error_is_auth_failure(error: Any, *, integration_type: str = "") -> bool:
    text = str(error or "").lower()
    normalized_type = normalize_supplier_integration_type(integration_type)
    if "token_expired" in text:
        return True
    if normalized_type == SUPPLIER_INTEGRATION_MKT24 and "http 401" in text:
        return True
    if normalized_type == SUPPLIER_INTEGRATION_MKT24 and "bearer token" in text and "만료" in text:
        return True
    return False


def normalize_supplier_order_status_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        raw_status = str(
            payload.get("status")
            or payload.get("Status")
            or payload.get("state")
            or payload.get("order_status")
            or payload.get("orderStatus")
            or payload.get("order_status_name")
            or payload.get("orderStatusName")
            or ""
        ).strip()
    else:
        raw_status = str(payload or "").strip()
    normalized = raw_status.lower().replace("_", " ").replace("-", " ")
    if not normalized:
        return "submitted"
    if any(token in normalized for token in ("complete", "completed", "완료")):
        return "completed"
    if any(token in normalized for token in ("progress", "processing", "in progress", "진행")):
        return "in_progress"
    if any(token in normalized for token in ("partial", "부분")):
        return "partial"
    if any(token in normalized for token in ("cancel", "canceled", "cancelled", "취소")):
        return "cancelled"
    if any(token in normalized for token in ("fail", "failed", "error", "reject", "실패", "오류")):
        return "failed"
    if any(token in normalized for token in ("pending", "queue", "wait", "대기")):
        return "pending"
    return "submitted"


def supplier_sync_interval_minutes(value: Any) -> int:
    try:
        interval = int(value or 0)
    except (TypeError, ValueError):
        interval = 0
    if interval <= 0:
        return SUPPLIER_SERVICE_SYNC_DEFAULT_INTERVAL_MINUTES
    return max(5, min(interval, 24 * 60))


def supplier_service_sync_due(row: Dict[str, Any], now: Optional[dt.datetime] = None) -> bool:
    if not bool(row.get("is_active", True)):
        return False
    current = now or dt.datetime.now().astimezone()
    lock_until = parse_iso_datetime(row.get("service_sync_lock_until"))
    if lock_until and lock_until > current:
        return False

    status = str(row.get("service_sync_status") or "never")
    completed_at = (
        parse_iso_datetime(row.get("service_sync_completed_at"))
        or parse_iso_datetime(row.get("last_checked_at"))
    )
    if completed_at is None:
        return True

    if status == "failed":
        try:
            error_count = max(int(row.get("service_sync_error_count") or 0), 1)
        except (TypeError, ValueError):
            error_count = 1
        retry_minutes = min(
            SUPPLIER_SERVICE_SYNC_RETRY_BASE_MINUTES * error_count,
            SUPPLIER_SERVICE_SYNC_RETRY_MAX_MINUTES,
        )
        return completed_at <= current - dt.timedelta(minutes=retry_minutes)

    interval_minutes = supplier_sync_interval_minutes(row.get("service_sync_interval_minutes"))
    return completed_at <= current - dt.timedelta(minutes=interval_minutes)


def _redact_external_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        sensitive_tokens = ("token", "secret", "password", "authorization", "access_token", "refresh_token", "key")
        for key, item in value.items():
            lower = str(key).lower()
            redacted[key] = "***" if any(token in lower for token in sensitive_tokens) else _redact_external_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_external_payload(item) for item in value]
    return value


class SupplierApiClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        integration_type: str = SUPPLIER_INTEGRATION_CLASSIC,
        bearer_token: str = "",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key.strip()
        self.integration_type = normalize_supplier_integration_type(integration_type)
        self.bearer_token = bearer_token.strip()

    def _request_form(self, payload: Dict[str, Any]) -> Any:
        encoded = urlencode(payload).encode("utf-8")
        request = Request(
            self.api_url,
            data=encoded,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json,text/plain,*/*",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=12) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, ValueError) as exc:
            raise SupplierApiError(str(exc)) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SupplierApiError("공급사 API가 JSON이 아닌 응답을 반환했습니다.") from exc

        if isinstance(parsed, dict) and parsed.get("error"):
            raise SupplierApiError(str(parsed["error"]))
        return parsed

    def _request_json(
        self,
        *,
        method: str,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        request_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        }
        if headers:
            request_headers.update(headers)
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        request = Request(url or self.api_url, data=data, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=12) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw_error = ""
            try:
                raw_error = exc.read().decode("utf-8", errors="replace")
            except Exception:
                raw_error = ""
            detail = raw_error[:800].strip()
            if detail:
                try:
                    parsed_error = json.loads(detail)
                    detail = supplier_http_error_message(exc.code, parsed_error, detail)
                except json.JSONDecodeError:
                    pass
            raise SupplierApiError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise SupplierApiError(str(exc)) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SupplierApiError("공급사 API가 JSON이 아닌 응답을 반환했습니다.") from exc

        if isinstance(parsed, dict):
            error_message = parsed.get("error") or parsed.get("message")
            if parsed.get("success") is False and error_message:
                raise SupplierApiError(str(error_message))
        return parsed

    def call(self, action: str, data: Optional[Dict[str, Any]] = None) -> Any:
        payload = {"key": self.api_key, "action": action}
        if data:
            payload.update({key: value for key, value in data.items() if value not in (None, "")})
        return self._request_form(payload)

    def services(self) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key:
                raise SupplierApiError("x-api-key가 필요합니다.")
            if not self.bearer_token:
                raise SupplierApiError("Bearer Token이 필요합니다.")
            return self._request_json(
                method="GET",
                url=self._mkt24_v3_url("/products/sns"),
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "x-api-key": self.api_key,
                },
            )
        return self.call("services")

    def _mkt24_v3_url(self, path: str) -> str:
        parsed = urlparse(self.api_url)
        if not parsed.scheme or not parsed.netloc:
            raise SupplierApiError("MKT24 API URL 형식이 올바르지 않습니다.")
        base_path = parsed.path.rstrip("/")
        marker = "/v3"
        if marker in base_path:
            base_path = base_path[: base_path.index(marker) + len(marker)]
        else:
            base_path = "/v3"
        return f"{parsed.scheme}://{parsed.netloc}{base_path}/{path.lstrip('/')}"

    def mkt24_product_detail(self, product_uuid: str) -> Any:
        return self._request_json(
            method="GET",
            url=self._mkt24_v3_url(f"/products/{quote(str(product_uuid), safe='')}"),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "x-api-key": self.api_key,
            },
        )

    def mkt24_sns_lookup(self, *, product_uuid: str, sns_value: str) -> Any:
        return self._request_json(
            method="GET",
            url=self._mkt24_v3_url(
                f"/sns?snsValue={quote(str(sns_value), safe='')}&productUuid={quote(str(product_uuid), safe='')}"
            ),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "x-api-key": self.api_key,
            },
        )

    def mkt24_estimate_sns(self, payload: Dict[str, Any]) -> Any:
        return self._request_json(
            method="POST",
            url=self._mkt24_v3_url("/order/sns/estimate"),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "x-api-key": self.api_key,
            },
            payload=payload,
        )

    def mkt24_order_sns(self, payload: Dict[str, Any]) -> Any:
        return self._request_json(
            method="POST",
            url=self._mkt24_v3_url("/order/sns"),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "x-api-key": self.api_key,
            },
            payload=payload,
        )

    def mkt24_order_status(self, order_uuid: str) -> Any:
        return self._request_json(
            method="GET",
            url=self._mkt24_v3_url(f"/order/sns/{quote(str(order_uuid), safe='')}"),
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "x-api-key": self.api_key,
            },
        )

    def balance(self) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("잔액 API를 지원하지 않는 공급사 타입입니다.")
        return self.call("balance")

    def order(self, data: Dict[str, Any]) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key or not self.bearer_token:
                raise SupplierApiError("MKT24 자동 발주에는 x-api-key와 Bearer Token이 필요합니다.")
            payload = dict(data)
            product_uuid = str(payload.pop("productUuid", "") or payload.pop("product_uuid", "") or payload.get("service") or "").strip()
            if product_uuid:
                payload["productUuid"] = product_uuid
                payload.pop("service", None)
            return self.mkt24_order_sns(payload)
        return self.call("add", data)

    def status(self, order_id: str) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key or not self.bearer_token:
                raise SupplierApiError("MKT24 상태 조회에는 x-api-key와 Bearer Token이 필요합니다.")
            return self.mkt24_order_status(order_id)
        return self.call("status", {"order": order_id})

    def multi_status(self, order_ids: List[str]) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("이 공급사 타입은 아직 상태 조회 API가 연결되지 않았습니다.")
        return self.call("status", {"orders": ",".join(order_ids)})

    def refill(self, order_id: str) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("이 공급사 타입은 아직 리필 API가 연결되지 않았습니다.")
        return self.call("refill", {"order": order_id})

    def balance_summary(self) -> Dict[str, str]:
        payload = self.balance()
        if not isinstance(payload, dict):
            raise SupplierApiError("잔액 응답 형식이 올바르지 않습니다.")
        if "balance" not in payload:
            raise SupplierApiError("잔액 정보를 확인하지 못했습니다.")
        return {
            "balance": str(payload.get("balance", "")),
            "currency": str(payload.get("currency", "")),
        }
