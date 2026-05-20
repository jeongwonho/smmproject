from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


SUPPLIER_INTEGRATION_CLASSIC = "classic"
SUPPLIER_INTEGRATION_MKT24 = "mkt24"
SUPPLIER_INTEGRATION_FASTTRAFFIC = "fasttraffic"
FASTTRAFFIC_API_URL = "https://fastraffic.co.kr/nblog_api.php"
FASTTRAFFIC_STATUS_ACTIONS = (
    "check_nblog",
    "check_nblog_daily",
    "check_nblog_keyword",
    "check_nclip",
    "check_nclip_direct",
    "check_ncafe",
)
SUPPLIER_SERVICE_SYNC_DEFAULT_INTERVAL_MINUTES = 30
SUPPLIER_SERVICE_SYNC_LOCK_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_BASE_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_MAX_MINUTES = 60
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


FASTTRAFFIC_SERVICE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "service": "nblog_auto",
        "name": "N블로그 자동트래픽",
        "category": "FastTraffic · N블로그",
        "type": "auto",
        "rate": 8,
        "min": 1,
        "max": 5000,
        "fasttraffic": {
            "action": "nblog_auto",
            "statusAction": "check_nblog",
            "targetParam": "blog_id",
            "quantityParam": "stay_max",
            "required": ["blog_id"],
            "defaults": {"private_comment": 0, "work_cycle": "4hr", "stay_time": 60, "stay_min": 1},
            "fieldHints": {"blog_id": "블로그 ID", "stay_max": "체류/조회 목표 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "nblog_direct",
        "name": "N블로그 수동트래픽",
        "category": "FastTraffic · N블로그",
        "type": "direct",
        "rate": 8,
        "min": 1,
        "max": 5000,
        "fasttraffic": {
            "action": "nblog_direct",
            "statusAction": "check_nblog",
            "targetParam": "blog_url",
            "quantityParam": "stay_count",
            "required": ["title", "blog_url"],
            "defaults": {"stay_time": 60},
            "fieldHints": {"blog_url": "블로그 글 URL", "stay_count": "체류/조회 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "nblog_daily",
        "name": "N블로그 일별체류",
        "category": "FastTraffic · N블로그",
        "type": "daily",
        "rate": 8,
        "min": 1,
        "max": 5000,
        "fasttraffic": {
            "action": "nblog_daily",
            "statusAction": "check_nblog_daily",
            "targetParam": "blog_ids",
            "quantityParam": "stay_count_max",
            "required": ["blog_ids"],
            "defaults": {"stay_time": 500},
            "fieldHints": {"blog_ids": "블로그 ID 목록", "stay_count_max": "일별 최대 체류 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "nblog_add_friend",
        "name": "N블로그 서이추",
        "category": "FastTraffic · N블로그",
        "type": "friend",
        "rate": 35,
        "min": 50,
        "max": 500,
        "fasttraffic": {
            "action": "nblog_add_friend",
            "statusAction": "check_nblog",
            "targetParam": "blog_id",
            "quantityParam": "friend_count",
            "required": ["blog_id", "friend_count"],
            "allowedQuantities": [50, 100, 150, 200, 250, 300, 350, 400, 450, 500],
            "fieldHints": {"blog_id": "블로그 ID", "friend_count": "서이추 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "nblog_keyword",
        "name": "N블로그 키워드 유입",
        "category": "FastTraffic · N블로그",
        "type": "keyword",
        "rate": 12,
        "min": 1,
        "max": 1000,
        "fasttraffic": {
            "action": "nblog_keyword",
            "statusAction": "check_nblog_keyword",
            "targetParam": "blog_url",
            "quantityParam": "keyword_inflow",
            "required": ["blog_url", "keyword", "keyword_inflow", "stay_time"],
            "defaults": {"stay_time": 120, "work_speed": "3hr"},
            "fieldHints": {"blog_url": "블로그 글 URL", "keyword": "검색 키워드", "keyword_inflow": "키워드 유입 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "nclip_direct_c",
        "name": "네이버 클립 수동",
        "category": "FastTraffic · N클립",
        "type": "direct",
        "rate": 3,
        "min": 1,
        "max": 10000,
        "fasttraffic": {
            "action": "nclip_direct_c",
            "statusAction": "check_nclip_direct",
            "targetParam": "clip_url",
            "quantityParam": "view_count",
            "required": ["title", "clip_url"],
            "defaults": {"stay_time": 30},
            "fieldHints": {"clip_url": "네이버 클립 URL", "view_count": "조회 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "ncafe_auto",
        "name": "N카페 자동트래픽",
        "category": "FastTraffic · N카페",
        "type": "auto",
        "rate": 4,
        "min": 1,
        "max": 5000,
        "fasttraffic": {
            "action": "ncafe_auto",
            "statusAction": "check_ncafe",
            "targetParam": "cafe_url",
            "quantityParam": "view_max",
            "required": ["title", "cafe_url"],
            "defaults": {"stay_time": 60, "view_min": 1},
            "fieldHints": {"cafe_url": "네이버 카페 글 URL", "view_max": "조회 수"},
            "rateLimitPerMinute": 60,
        },
    },
    {
        "service": "ncafe_direct",
        "name": "N카페 수동트래픽",
        "category": "FastTraffic · N카페",
        "type": "direct",
        "rate": 4,
        "min": 1,
        "max": 5000,
        "fasttraffic": {
            "action": "ncafe_direct",
            "statusAction": "check_ncafe",
            "targetParam": "cafe_url",
            "quantityParam": "view_count",
            "required": ["title", "cafe_url"],
            "defaults": {"stay_time": 60},
            "fieldHints": {"cafe_url": "네이버 카페 글 URL", "view_count": "조회 수"},
            "rateLimitPerMinute": 60,
        },
    },
]


class SupplierApiError(Exception):
    pass


def supplier_http_error_message(status_code: int, payload: Any, fallback: str = "") -> str:
    if isinstance(payload, dict):
        code = str(payload.get("code") or payload.get("error") or "").strip()
        message = str(payload.get("message") or payload.get("error_description") or "").strip()
        trace_uuid = str(payload.get("uuid") or payload.get("traceId") or payload.get("trace_id") or "").strip()
        if code == "token_expired":
            detail = "공급사 인증 정보가 만료되었습니다. 관리자 공급사 설정에서 API 키/권한을 확인한 뒤 연결 확인과 서비스 동기화를 다시 실행해 주세요."
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
    if value == SUPPLIER_INTEGRATION_FASTTRAFFIC:
        return SUPPLIER_INTEGRATION_FASTTRAFFIC
    if value == SUPPLIER_INTEGRATION_MKT24:
        return SUPPLIER_INTEGRATION_MKT24
    return SUPPLIER_INTEGRATION_CLASSIC


def supplier_supports_balance_check(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) in {
        SUPPLIER_INTEGRATION_CLASSIC,
        SUPPLIER_INTEGRATION_FASTTRAFFIC,
    }


def supplier_supports_auto_dispatch(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) in {
        SUPPLIER_INTEGRATION_CLASSIC,
        SUPPLIER_INTEGRATION_MKT24,
        SUPPLIER_INTEGRATION_FASTTRAFFIC,
    }


def supplier_uses_panel_api(integration_type: str, api_url: str) -> bool:
    """Return true for endpoints that follow the standard SMM panel key/action API."""
    normalized_type = normalize_supplier_integration_type(integration_type)
    if normalized_type == SUPPLIER_INTEGRATION_CLASSIC:
        return True
    if normalized_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
        return False
    parsed = urlparse(str(api_url or ""))
    return normalized_type == SUPPLIER_INTEGRATION_MKT24 and parsed.path.rstrip("/").endswith("/panel")


def normalize_fasttraffic_api_url(api_url: str) -> str:
    raw = str(api_url or "").strip()
    if not raw:
        return FASTTRAFFIC_API_URL
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw.rstrip("/"))
    if not parsed.scheme or not parsed.netloc:
        return FASTTRAFFIC_API_URL
    if parsed.netloc.endswith("fastraffic.co.kr"):
        return f"{parsed.scheme}://{parsed.netloc}/nblog_api.php"
    return raw.rstrip("/")


def fasttraffic_service_definitions() -> List[Dict[str, Any]]:
    return [json.loads(json.dumps(item, ensure_ascii=False)) for item in FASTTRAFFIC_SERVICE_DEFINITIONS]


def normalize_mkt24_panel_api_url(api_url: str) -> str:
    raw = str(api_url or "").strip()
    if not raw:
        return raw
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw.rstrip("/"))
    if not parsed.scheme or not parsed.netloc:
        return raw.rstrip("/")
    path = parsed.path.rstrip("/")
    if path.endswith("/panel"):
        return raw.rstrip("/")
    base_path = path
    marker = "/v3"
    if marker in base_path:
        base_path = base_path[: base_path.index(marker) + len(marker)]
    else:
        base_path = "/v3"
    return f"{parsed.scheme}://{parsed.netloc}{base_path}/panel"


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
        self.integration_type = normalize_supplier_integration_type(integration_type)
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            normalized_api_url = normalize_mkt24_panel_api_url(api_url)
        elif self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            normalized_api_url = normalize_fasttraffic_api_url(api_url)
        else:
            normalized_api_url = str(api_url or "").rstrip("/")
        self.api_url = normalized_api_url.rstrip("/")
        self.api_key = api_key.strip()
        self.bearer_token = bearer_token.strip()

    @property
    def uses_panel_api(self) -> bool:
        return supplier_uses_panel_api(self.integration_type, self.api_url)

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
        except (URLError, TimeoutError, ValueError) as exc:
            raise SupplierApiError(str(exc)) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SupplierApiError("공급사 API가 JSON이 아닌 응답을 반환했습니다.") from exc

        if isinstance(parsed, dict) and parsed.get("error"):
            raise SupplierApiError(str(parsed["error"]))
        return parsed

    def _request_fasttraffic_form(self, payload: Dict[str, Any]) -> Any:
        if not self.api_key:
            raise SupplierApiError("FastTraffic API Key가 필요합니다.")
        encoded = urlencode({key: value for key, value in payload.items() if value not in (None, "")}).encode("utf-8")
        request = Request(
            self.api_url or FASTTRAFFIC_API_URL,
            data=encoded,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json,text/plain,*/*",
                "X-Api-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
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
        except (URLError, TimeoutError, ValueError) as exc:
            raise SupplierApiError(str(exc)) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SupplierApiError("FastTraffic API가 JSON이 아닌 응답을 반환했습니다.") from exc

        if isinstance(parsed, dict):
            message = str(parsed.get("message") or parsed.get("error") or "").strip()
            if parsed.get("success") is False:
                code = str(parsed.get("code") or "").strip()
                prefix = f"FastTraffic 오류 {code}: " if code else "FastTraffic 오류: "
                raise SupplierApiError(prefix + (message or "요청이 실패했습니다."))
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
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            return self.fasttraffic_call(action, data)
        payload = {"key": self.api_key, "action": action}
        if data:
            payload.update({key: value for key, value in data.items() if value not in (None, "")})
        return self._request_form(payload)

    def fasttraffic_call(self, action: str, data: Optional[Dict[str, Any]] = None) -> Any:
        action_value = str(action or "").strip()
        if not action_value:
            raise SupplierApiError("FastTraffic action이 필요합니다.")
        payload = {"action": action_value}
        if data:
            payload.update({key: value for key, value in data.items() if value not in (None, "") and key not in {"key", "api_key"}})
        return self._request_fasttraffic_form(payload)

    def services(self) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            return fasttraffic_service_definitions()
        if self.uses_panel_api:
            return self.call("services")
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key:
                raise SupplierApiError("x-api-key가 필요합니다.")
            return self._request_json(
                method="GET",
                url=self._mkt24_v3_url("/products/sns"),
                headers=self._mkt24_headers(),
            )
        return self.call("services")

    def _mkt24_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise SupplierApiError("x-api-key가 필요합니다.")
        headers = {"x-api-key": self.api_key}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

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
            headers=self._mkt24_headers(),
        )

    def mkt24_sns_lookup(self, *, product_uuid: str, sns_value: str) -> Any:
        return self._request_json(
            method="GET",
            url=self._mkt24_v3_url(
                f"/sns?snsValue={quote(str(sns_value), safe='')}&productUuid={quote(str(product_uuid), safe='')}"
            ),
            headers=self._mkt24_headers(),
        )

    def mkt24_estimate_sns(self, payload: Dict[str, Any]) -> Any:
        return self._request_json(
            method="POST",
            url=self._mkt24_v3_url("/order/sns/estimate"),
            headers=self._mkt24_headers(),
            payload=payload,
        )

    def mkt24_order_sns(self, payload: Dict[str, Any]) -> Any:
        return self._request_json(
            method="POST",
            url=self._mkt24_v3_url("/order/sns"),
            headers=self._mkt24_headers(),
            payload=payload,
        )

    def mkt24_order_status(self, order_uuid: str) -> Any:
        return self._request_json(
            method="GET",
            url=self._mkt24_v3_url(f"/order/sns/{quote(str(order_uuid), safe='')}"),
            headers=self._mkt24_headers(),
        )

    def balance(self) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            return self.fasttraffic_call("check_balance")
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24 and not self.uses_panel_api:
            raise SupplierApiError("잔액 API를 지원하지 않는 공급사 타입입니다.")
        return self.call("balance")

    def order(self, data: Dict[str, Any]) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            payload = dict(data)
            action = str(payload.pop("action", "") or payload.pop("service", "") or "").strip()
            return self.fasttraffic_call(action, payload)
        if self.uses_panel_api:
            return self.call("add", data)
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key:
                raise SupplierApiError("MKT24 자동 발주에는 x-api-key가 필요합니다.")
            payload = dict(data)
            product_uuid = str(payload.pop("productUuid", "") or payload.pop("product_uuid", "") or payload.get("service") or "").strip()
            if product_uuid:
                payload["productUuid"] = product_uuid
                payload.pop("service", None)
            return self.mkt24_order_sns(payload)
        return self.call("add", data)

    def status(self, order_id: str) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            target_order_id = str(order_id or "").strip()
            if not target_order_id:
                raise SupplierApiError("FastTraffic 상태 조회에는 wr_id가 필요합니다.")
            for action in FASTTRAFFIC_STATUS_ACTIONS:
                payload = self.fasttraffic_call(action, {"days": 90, "limit": 100, "page": 1})
                rows: List[Any] = []
                if isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, list):
                        rows = data
                    elif isinstance(payload.get("items"), list):
                        rows = payload["items"]
                    elif isinstance(payload.get("list"), list):
                        rows = payload["list"]
                    elif isinstance(payload.get("rows"), list):
                        rows = payload["rows"]
                elif isinstance(payload, list):
                    rows = payload
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    row_id = str(
                        row.get("wr_id")
                        or row.get("id")
                        or row.get("order_id")
                        or row.get("orderId")
                        or ""
                    ).strip()
                    if row_id != target_order_id:
                        continue
                    normalized_row = dict(row)
                    normalized_row.setdefault("order", target_order_id)
                    normalized_row.setdefault("statusAction", action)
                    normalized_row.setdefault("status", self._fasttraffic_status_from_row(row))
                    return normalized_row
            return {
                "order": target_order_id,
                "status": "submitted",
                "message": "FastTraffic 상태 목록에서 아직 주문을 찾지 못했습니다.",
            }
        if self.uses_panel_api:
            return self.call("status", {"order": order_id})
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            if not self.api_key:
                raise SupplierApiError("MKT24 상태 조회에는 x-api-key가 필요합니다.")
            return self.mkt24_order_status(order_id)
        return self.call("status", {"order": order_id})

    def multi_status(self, order_ids: List[str]) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24 and not self.uses_panel_api:
            raise SupplierApiError("이 공급사 타입은 아직 상태 조회 API가 연결되지 않았습니다.")
        return self.call("status", {"orders": ",".join(order_ids)})

    def refill(self, order_id: str) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24 and not self.uses_panel_api:
            raise SupplierApiError("이 공급사 타입은 아직 리필 API가 연결되지 않았습니다.")
        return self.call("refill", {"order": order_id})

    def balance_summary(self) -> Dict[str, str]:
        payload = self.balance()
        if not isinstance(payload, dict):
            raise SupplierApiError("잔액 응답 형식이 올바르지 않습니다.")
        if self.integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            balance_value = payload.get("mb_point")
            if balance_value is None:
                raise SupplierApiError("FastTraffic 포인트 정보를 확인하지 못했습니다.")
            return {
                "balance": str(balance_value),
                "currency": "P",
            }
        if "balance" not in payload:
            raise SupplierApiError("잔액 정보를 확인하지 못했습니다.")
        return {
            "balance": str(payload.get("balance", "")),
            "currency": str(payload.get("currency", "")),
        }

    @staticmethod
    def _fasttraffic_status_from_row(row: Dict[str, Any]) -> str:
        raw_status = str(
            row.get("status")
            or row.get("work_status")
            or row.get("state")
            or row.get("result")
            or row.get("message")
            or ""
        ).lower()
        if any(token in raw_status for token in ("완료", "complete", "success")):
            return "completed"
        if any(token in raw_status for token in ("실패", "오류", "fail", "error", "reject")):
            return "failed"
        if any(token in raw_status for token in ("진행", "처리", "progress", "processing")):
            return "in_progress"
        return "submitted"
