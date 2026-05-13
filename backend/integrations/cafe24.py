from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


CAFE24_DEFAULT_SHOP_NO = 1
CAFE24_ORDER_PAGE_LIMIT = 1000
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


class Cafe24ApiClient:
    def __init__(self, mall_id: str, access_token: str, *, shop_no: int = CAFE24_DEFAULT_SHOP_NO) -> None:
        self.mall_id = str(mall_id or "").strip()
        self.access_token = str(access_token or "").strip()
        self.shop_no = int(shop_no or CAFE24_DEFAULT_SHOP_NO)
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
        for attempt in range(3):
            request = Request(url, data=data, headers=headers, method=method.upper())
            try:
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                break
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    retry_after = str(exc.headers.get("Retry-After") or "").strip() if exc.headers else ""
                    try:
                        delay = min(max(float(retry_after), 0.5), 3.0) if retry_after else 0.5 * (attempt + 1)
                    except ValueError:
                        delay = 0.5 * (attempt + 1)
                    time.sleep(delay)
                    continue
                raise Cafe24ApiError(f"Cafe24 API 오류 {exc.code}: {body or exc.reason}") from exc
            except (URLError, TimeoutError, ValueError) as exc:
                if attempt < 2:
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
