#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import hashlib
import hmac
import json
import math
import os
import secrets
import time
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Dict, Optional, Sequence
from urllib.parse import parse_qs, urlparse

from core import APP_ROOT, PanelError, PanelStore


STATIC_ROOT = APP_ROOT / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8024
ADMIN_SESSION_COOKIE = "smm_panel_admin_session"
ADMIN_SESSION_TTL_SECONDS = 60 * 60 * 12
MAX_JSON_BODY_BYTES = 10 * 1024 * 1024
ADMIN_LOGIN_WINDOW_SECONDS = 15 * 60
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ROBOTS_TXT = "User-agent: *\nDisallow: /admin\nDisallow: /api/admin\n"
INDEX_TEMPLATE_PATH = STATIC_ROOT / "index.html"


def env_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_origin(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def normalize_public_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def parse_origins(raw_value: str) -> tuple[str, ...]:
    origins: list[str] = []
    for candidate in str(raw_value or "").split(","):
        normalized = normalize_origin(candidate)
        if normalized and normalized not in origins:
            origins.append(normalized)
    return tuple(origins)


@dataclass(frozen=True)
class AppConfig:
    public_api_base_url: str = ""
    allowed_origins: tuple[str, ...] = ()
    cookie_domain: str = ""
    admin_cookie_samesite: str = "Strict"
    force_secure_cookies: bool = False

    @property
    def api_origin(self) -> str:
        return normalize_origin(self.public_api_base_url)

    @classmethod
    def from_env(cls) -> "AppConfig":
        public_api_base_url = normalize_public_url(os.environ.get("SMM_PANEL_PUBLIC_API_BASE_URL", ""))
        configured_origins = list(parse_origins(os.environ.get("SMM_PANEL_ALLOWED_ORIGINS", "")))
        public_app_origin = normalize_origin(os.environ.get("SMM_PANEL_PUBLIC_APP_ORIGIN", ""))
        if public_app_origin and public_app_origin not in configured_origins:
            configured_origins.append(public_app_origin)
        cookie_domain = os.environ.get("SMM_PANEL_COOKIE_DOMAIN", "").strip()
        admin_cookie_samesite = (os.environ.get("SMM_PANEL_ADMIN_COOKIE_SAMESITE", "Strict").strip().capitalize() or "Strict")
        if admin_cookie_samesite not in {"Strict", "Lax", "None"}:
            admin_cookie_samesite = "Strict"
        return cls(
            public_api_base_url=public_api_base_url,
            allowed_origins=tuple(configured_origins),
            cookie_domain=cookie_domain,
            admin_cookie_samesite=admin_cookie_samesite,
            force_secure_cookies=env_flag(os.environ.get("SMM_PANEL_FORCE_SECURE_COOKIES", "")),
        )


class RequestRateLimiter:
    def __init__(self, rules: Optional[Dict[str, tuple[int, int]]] = None) -> None:
        self.rules = rules or {
            "orders": (20, 60),
            "link_preview": (30, 60),
            "charge": (12, 60),
            "analytics": (180, 60),
        }
        self.events: Dict[str, list[float]] = {}

    def _key(self, bucket: str, client_key: str) -> str:
        return f"{bucket}:{client_key}"

    def _recent(self, bucket: str, client_key: str) -> list[float]:
        limit, window_seconds = self.rules[bucket]
        now = time.time()
        storage_key = self._key(bucket, client_key)
        attempts = [
            attempt
            for attempt in self.events.get(storage_key, [])
            if attempt > now - window_seconds
        ]
        if attempts:
            self.events[storage_key] = attempts
        else:
            self.events.pop(storage_key, None)
        return attempts

    def retry_after(self, bucket: str, client_key: str) -> int:
        limit, window_seconds = self.rules[bucket]
        attempts = self._recent(bucket, client_key)
        if len(attempts) < limit:
            return 0
        oldest_attempt = min(attempts)
        remaining_seconds = window_seconds - (time.time() - oldest_attempt)
        return max(1, math.ceil(remaining_seconds))

    def record(self, bucket: str, client_key: str) -> None:
        storage_key = self._key(bucket, client_key)
        attempts = self._recent(bucket, client_key)
        attempts.append(time.time())
        self.events[storage_key] = attempts

    def enforce(self, bucket: str, client_key: str, message: str) -> None:
        retry_after = self.retry_after(bucket, client_key)
        if retry_after:
            raise PanelError(message.format(retry_after=retry_after), status=429)
        self.record(bucket, client_key)


class AdminSessionStore:
    def __init__(
        self,
        username: str,
        password: str,
        ttl_seconds: int = ADMIN_SESSION_TTL_SECONDS,
        login_window_seconds: int = ADMIN_LOGIN_WINDOW_SECONDS,
        login_max_attempts: int = ADMIN_LOGIN_MAX_ATTEMPTS,
    ) -> None:
        self.username = username.strip() or "admin"
        self.ttl_seconds = ttl_seconds
        self.login_window_seconds = login_window_seconds
        self.login_max_attempts = login_max_attempts
        self.password_hash = self._hash_value(password) if password else ""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, list[float]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.password_hash)

    def _hash_value(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def session_payload(self, token: str = "") -> Dict[str, Any]:
        session = self.get_session(token)
        return {
            "configured": self.is_configured,
            "authenticated": session is not None,
            "username": session["username"] if session else "",
            "csrfToken": session.get("csrf_token", "") if session else "",
        }

    def verify_credentials(self, username: str, password: str) -> bool:
        if not self.is_configured:
            return False
        if not hmac.compare_digest(username.strip(), self.username):
            return False
        return hmac.compare_digest(self._hash_value(password), self.password_hash)

    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "username": self.username,
            "csrf_token": secrets.token_urlsafe(24),
            "expires_at": time.time() + self.ttl_seconds,
        }
        return token

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        session = self.sessions.get(token)
        if session is None:
            return None
        if float(session.get("expires_at", 0)) <= time.time():
            self.sessions.pop(token, None)
            return None
        session["expires_at"] = time.time() + self.ttl_seconds
        return session

    def destroy_session(self, token: str) -> None:
        if token:
            self.sessions.pop(token, None)

    def _recent_failures(self, client_key: str) -> list[float]:
        now = time.time()
        attempts = [
            attempt
            for attempt in self.failed_attempts.get(client_key, [])
            if attempt > now - self.login_window_seconds
        ]
        if attempts:
            self.failed_attempts[client_key] = attempts
        else:
            self.failed_attempts.pop(client_key, None)
        return attempts

    def login_retry_after(self, client_key: str) -> int:
        attempts = self._recent_failures(client_key)
        if len(attempts) < self.login_max_attempts:
            return 0
        oldest_attempt = min(attempts)
        remaining_seconds = self.login_window_seconds - (time.time() - oldest_attempt)
        return max(1, math.ceil(remaining_seconds))

    def record_failed_login(self, client_key: str) -> None:
        attempts = self._recent_failures(client_key)
        attempts.append(time.time())
        self.failed_attempts[client_key] = attempts

    def clear_failed_logins(self, client_key: str) -> None:
        if client_key:
            self.failed_attempts.pop(client_key, None)


def read_json(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}
    if length > MAX_JSON_BODY_BYTES:
        raise PanelError("요청 본문이 너무 큽니다.", status=413)
    try:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PanelError("요청 형식이 올바르지 않습니다.", status=400) from exc


def write_json(
    handler: SimpleHTTPRequestHandler,
    status: int,
    payload: Dict[str, Any],
    extra_headers: Sequence[tuple[str, str]] = (),
) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    for header_name, header_value in extra_headers:
        handler.send_header(header_name, header_value)
    handler.end_headers()
    handler.wfile.write(raw)


def write_text(
    handler: SimpleHTTPRequestHandler,
    status: int,
    body: str,
    content_type: str = "text/plain; charset=utf-8",
    extra_headers: Sequence[tuple[str, str]] = (),
    write_body: bool = True,
) -> None:
    raw = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    for header_name, header_value in extra_headers:
        handler.send_header(header_name, header_value)
    handler.end_headers()
    if write_body:
        handler.wfile.write(raw)


def send_error_json(handler: SimpleHTTPRequestHandler, exc: Exception) -> None:
    if isinstance(exc, PanelError):
        write_json(handler, exc.status, {"ok": False, "error": str(exc)})
        return
    print(f"[panel-error] {exc}")
    write_json(handler, 500, {"ok": False, "error": "서버 처리 중 오류가 발생했습니다."})


def render_index_html(store: PanelStore, request_path: str, config: AppConfig) -> str:
    template = INDEX_TEMPLATE_PATH.read_text(encoding="utf-8")
    settings = store.public_site_settings()["siteSettings"]
    site_name = str(settings.get("siteName") or "Pulse24").strip() or "Pulse24"
    site_description = str(settings.get("siteDescription") or "").strip()
    favicon_url = str(settings.get("faviconUrl") or "").strip()
    share_image_url = str(settings.get("shareImageUrl") or "").strip()
    is_admin = request_path == "/admin" or request_path.startswith("/admin/")
    title = f"{site_name} Admin Console" if is_admin else site_name

    head_parts = ['<meta name="theme-color" content="#4c76ff" />']
    if is_admin:
        head_parts.append('<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />')
        head_parts.append('<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />')
    else:
        if site_description:
            escaped_description = html.escape(site_description, quote=True)
            head_parts.extend(
                [
                    f'<meta name="description" content="{escaped_description}" />',
                    f'<meta property="og:title" content="{html.escape(site_name, quote=True)}" />',
                    f'<meta property="og:description" content="{escaped_description}" />',
                    f'<meta name="twitter:title" content="{html.escape(site_name, quote=True)}" />',
                    f'<meta name="twitter:description" content="{escaped_description}" />',
                ]
            )
        if share_image_url:
            escaped_share_image = html.escape(share_image_url, quote=True)
            head_parts.extend(
                [
                    '<meta property="og:type" content="website" />',
                    f'<meta property="og:image" content="{escaped_share_image}" />',
                    '<meta name="twitter:card" content="summary_large_image" />',
                    f'<meta name="twitter:image" content="{escaped_share_image}" />',
                ]
            )
        else:
            head_parts.append('<meta name="twitter:card" content="summary" />')
    if favicon_url:
        escaped_favicon = html.escape(favicon_url, quote=True)
        head_parts.extend(
            [
                f'<link rel="icon" href="{escaped_favicon}" data-managed-head="site-favicon" />',
                f'<link rel="shortcut icon" href="{escaped_favicon}" data-managed-head="site-shortcut-icon" />',
                f'<link rel="apple-touch-icon" href="{escaped_favicon}" data-managed-head="site-apple-touch-icon" />',
            ]
        )

    head_markup = "\n    ".join(head_parts)
    title_markup = f"<title>{html.escape(title)}</title>"
    document = template.replace("<title>Pulse24 Demo Panel</title>", title_markup)
    document = document.replace(
        '<meta name="smm-api-base-url" content="" data-managed-runtime="api-base" />',
        f'<meta name="smm-api-base-url" content="{html.escape(config.public_api_base_url, quote=True)}" data-managed-runtime="api-base" />',
    )
    return document.replace("<!-- SMM_MANAGED_HEAD -->", head_markup)


class PanelHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls: type[SimpleHTTPRequestHandler],
        store: PanelStore,
        admin_sessions: AdminSessionStore,
        config: AppConfig,
        rate_limiter: RequestRateLimiter,
    ) -> None:
        super().__init__(server_address, handler_cls)
        self.store = store
        self.admin_sessions = admin_sessions
        self.config = config
        self.rate_limiter = rate_limiter


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        self._request_path = ""
        super().__init__(*args, directory=str(STATIC_ROOT if directory is None else directory), **kwargs)

    def _server(self) -> PanelHTTPServer:
        return self.server  # type: ignore[return-value]

    def _robots_blocked_path(self) -> bool:
        request_path = self._request_path or "/"
        return request_path == "/admin" or request_path.startswith("/admin/") or request_path.startswith("/api/admin/")

    def _disable_static_cache(self) -> bool:
        request_path = self._request_path or "/"
        return request_path in {"", "/", "/admin"} or request_path.startswith("/admin/") or request_path.endswith((".html", ".css", ".js"))

    def _config(self) -> AppConfig:
        return self._server().config

    def _request_scheme(self) -> str:
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
        if forwarded_proto in {"http", "https"}:
            return forwarded_proto
        return "https" if self.server.server_port == 443 else "http"

    def _request_host(self) -> str:
        forwarded_host = self.headers.get("X-Forwarded-Host", "").split(",")[0].strip()
        if forwarded_host:
            return forwarded_host
        return self.headers.get("Host", "").strip() or f"{self.server.server_name}:{self.server.server_port}"

    def _request_origin(self) -> str:
        return normalize_origin(f"{self._request_scheme()}://{self._request_host()}")

    def _allowed_cors_origin(self) -> str:
        origin = normalize_origin(self.headers.get("Origin", ""))
        if not origin:
            return ""
        if origin == self._request_origin():
            return origin
        if origin in self._config().allowed_origins:
            return origin
        return ""

    def _require_trusted_origin(self) -> None:
        origin = normalize_origin(self.headers.get("Origin", ""))
        if not origin:
            return
        if self._allowed_cors_origin():
            return
        raise PanelError("허용되지 않은 요청 출처입니다.", status=403)

    def _content_security_policy(self) -> str:
        connect_sources = ["'self'"]
        api_origin = self._config().api_origin
        if api_origin and api_origin not in connect_sources:
            connect_sources.append(api_origin)
        return (
            "default-src 'self'; "
            "img-src 'self' data: https: http:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            f"connect-src {' '.join(connect_sources)}; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if self._request_scheme() == "https" or self._config().force_secure_cookies:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if self._disable_static_cache():
            self.send_header("Cache-Control", "no-store")
        if self._robots_blocked_path():
            self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet, noimageindex")
        allowed_origin = self._allowed_cors_origin()
        if allowed_origin and self._request_path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type, X-SMM-CSRF-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Vary", "Origin")
        self.send_header("Content-Security-Policy", self._content_security_policy())
        super().end_headers()

    def _admin_session_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(ADMIN_SESSION_COOKIE)
        return morsel.value if morsel else ""

    def _admin_session(self) -> Optional[Dict[str, Any]]:
        return self._server().admin_sessions.get_session(self._admin_session_token())

    def _client_identity(self) -> str:
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return self.client_address[0]

    def _require_admin_auth(self) -> Dict[str, Any]:
        admin_sessions = self._server().admin_sessions
        if not admin_sessions.is_configured:
            raise PanelError(
                "관리자 보안 설정이 없습니다. SMM_PANEL_ADMIN_PASSWORD 환경변수를 설정한 뒤 서버를 다시 실행해 주세요.",
                status=503,
            )
        session = self._admin_session()
        if session is None:
            raise PanelError("관리자 로그인이 필요합니다.", status=401)
        return session

    def _require_admin_csrf(self, session: Dict[str, Any]) -> None:
        expected = str(session.get("csrf_token") or "")
        provided = self.headers.get("X-SMM-CSRF-Token", "").strip()
        if not expected or not provided or not hmac.compare_digest(provided, expected):
            raise PanelError("관리자 요청 검증에 실패했습니다. 다시 로그인해 주세요.", status=403)

    def _cookie_header(self, value: str, max_age: int) -> str:
        cookie = SimpleCookie()
        cookie[ADMIN_SESSION_COOKIE] = value
        morsel = cookie[ADMIN_SESSION_COOKIE]
        morsel["path"] = "/"
        morsel["httponly"] = True
        morsel["samesite"] = self._config().admin_cookie_samesite
        morsel["max-age"] = str(max_age)
        if self._config().cookie_domain:
            morsel["domain"] = self._config().cookie_domain
        if (
            self._request_scheme() == "https"
            or self._config().force_secure_cookies
            or self._config().admin_cookie_samesite == "None"
        ):
            morsel["secure"] = True
        return cookie.output(header="").strip()

    def _serve_index_document(self, *, write_body: bool = True) -> None:
        document = render_index_html(self._server().store, self._request_path or "/", self._config())
        write_text(self, 200, document, content_type="text/html; charset=utf-8", write_body=write_body)

    def _enforce_rate_limit(self, bucket: str, message: str) -> None:
        client_key = self._client_identity()
        self._server().rate_limiter.enforce(bucket, client_key, message)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        self._request_path = parsed.path
        try:
            if parsed.path == "/api/health":
                write_json(self, 200, {"ok": True, "service": "Pulse24 Demo Panel"})
                return
            if parsed.path == "/robots.txt":
                write_text(self, 200, ROBOTS_TXT)
                return
            if parsed.path == "/api/admin/session":
                write_json(self, 200, {"ok": True, **self._server().admin_sessions.session_payload(self._admin_session_token())})
                return
            if parsed.path == "/api/bootstrap":
                write_json(self, 200, {"ok": True, **self._server().store.bootstrap()})
                return
            if parsed.path.startswith("/api/admin/"):
                self._require_admin_auth()
            if parsed.path == "/api/admin/bootstrap":
                write_json(self, 200, {"ok": True, **self._server().store.admin_bootstrap()})
                return
            if parsed.path.startswith("/api/admin/customers/"):
                customer_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, **self._server().store.get_customer_detail(customer_id)})
                return
            if parsed.path == "/api/products":
                search = parse_qs(parsed.query).get("q", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_catalog(search)})
                return
            if parsed.path.startswith("/api/admin/suppliers/") and parsed.path.endswith("/services"):
                supplier_id = parsed.path.split("/")[4]
                search = parse_qs(parsed.query).get("q", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_supplier_services(supplier_id, search)})
                return
            if parsed.path.startswith("/api/product-categories/"):
                category_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "category": self._server().store.get_product_category(category_id)})
                return
            if parsed.path == "/api/orders":
                status = parse_qs(parsed.query).get("status", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_orders(status)})
                return
            if parsed.path == "/api/transactions":
                write_json(self, 200, {"ok": True, **self._server().store.list_transactions()})
                return
        except Exception as exc:
            send_error_json(self, exc)
            return

        asset_path = (STATIC_ROOT / parsed.path.lstrip("/")).resolve()
        if parsed.path not in {"", "/"} and asset_path.is_file() and STATIC_ROOT in asset_path.parents:
            self.path = parsed.path
            super().do_GET()
            return

        self._serve_index_document()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        self._request_path = parsed.path
        if parsed.path == "/robots.txt":
            write_text(self, 200, ROBOTS_TXT, write_body=False)
            return

        asset_path = (STATIC_ROOT / parsed.path.lstrip("/")).resolve()
        if parsed.path not in {"", "/"} and asset_path.is_file() and STATIC_ROOT in asset_path.parents:
            self.path = parsed.path
            super().do_HEAD()
            return

        self._serve_index_document(write_body=False)

    def do_OPTIONS(self) -> None:
        parsed = urlparse(self.path)
        self._request_path = parsed.path
        try:
            self._require_trusted_origin()
            write_text(self, 204, "", write_body=False)
        except Exception as exc:
            send_error_json(self, exc)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._request_path = parsed.path
        try:
            self._require_trusted_origin()
            payload = read_json(self)
            if parsed.path == "/api/orders":
                self._enforce_rate_limit("orders", "주문 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, self._server().store.create_order(payload))
                return
            if parsed.path == "/api/analytics/track":
                self._enforce_rate_limit("analytics", "방문 수집 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        **self._server().store.record_site_visit(
                            payload,
                            user_agent=self.headers.get("User-Agent", ""),
                            request_host=self.headers.get("Host", ""),
                        ),
                    },
                )
                return
            if parsed.path == "/api/admin/login":
                username = str(payload.get("username") or "").strip()
                password = str(payload.get("password") or "")
                admin_sessions = self._server().admin_sessions
                client_identity = self._client_identity()
                if not admin_sessions.is_configured:
                    raise PanelError(
                        "관리자 보안 설정이 없습니다. SMM_PANEL_ADMIN_PASSWORD 환경변수를 설정한 뒤 서버를 다시 실행해 주세요.",
                        status=503,
                    )
                retry_after = admin_sessions.login_retry_after(client_identity)
                if retry_after:
                    raise PanelError(
                        f"로그인 시도가 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.",
                        status=429,
                    )
                if not admin_sessions.verify_credentials(username, password):
                    admin_sessions.record_failed_login(client_identity)
                    raise PanelError("관리자 계정 또는 비밀번호가 올바르지 않습니다.", status=401)
                admin_sessions.clear_failed_logins(client_identity)
                token = admin_sessions.create_session()
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "authenticated": True,
                        "username": admin_sessions.username,
                        "csrfToken": admin_sessions.session_payload(token).get("csrfToken", ""),
                    },
                    extra_headers=[("Set-Cookie", self._cookie_header(token, ADMIN_SESSION_TTL_SECONDS))],
                )
                return
            session: Optional[Dict[str, Any]] = None
            if parsed.path.startswith("/api/admin/"):
                session = self._require_admin_auth()
                self._require_admin_csrf(session)
            if parsed.path == "/api/admin/logout":
                self._server().admin_sessions.destroy_session(self._admin_session_token())
                write_json(
                    self,
                    200,
                    {"ok": True, "authenticated": False},
                    extra_headers=[("Set-Cookie", self._cookie_header("", 0))],
                )
                return
            if parsed.path == "/api/admin/site-settings":
                write_json(self, 200, {"ok": True, **self._server().store.save_site_settings(payload)})
                return
            if parsed.path == "/api/admin/popup":
                write_json(self, 200, {"ok": True, **self._server().store.save_home_popup(payload)})
                return
            if parsed.path == "/api/admin/suppliers":
                write_json(self, 200, {"ok": True, **self._server().store.save_supplier(payload)})
                return
            if parsed.path == "/api/admin/customers":
                write_json(self, 200, {"ok": True, **self._server().store.save_customer(payload)})
                return
            if parsed.path == "/api/admin/customers/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_customer(payload)})
                return
            if parsed.path == "/api/admin/customers/balance":
                write_json(self, 200, {"ok": True, **self._server().store.adjust_customer_balance(payload)})
                return
            if parsed.path == "/api/admin/categories":
                write_json(self, 200, {"ok": True, **self._server().store.save_category(payload)})
                return
            if parsed.path == "/api/admin/categories/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_category(payload)})
                return
            if parsed.path == "/api/admin/products":
                write_json(self, 200, {"ok": True, **self._server().store.save_catalog_product(payload)})
                return
            if parsed.path == "/api/admin/products/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_catalog_product(payload)})
                return
            if parsed.path == "/api/admin/orders/status":
                write_json(self, 200, {"ok": True, **self._server().store.update_admin_order_status(payload)})
                return
            if parsed.path == "/api/admin/suppliers/test":
                write_json(self, 200, {"ok": True, **self._server().store.test_supplier_connection(payload)})
                return
            if parsed.path.startswith("/api/admin/suppliers/") and parsed.path.endswith("/sync-services"):
                supplier_id = parsed.path.split("/")[4]
                write_json(self, 200, {"ok": True, **self._server().store.sync_supplier_services(supplier_id)})
                return
            if parsed.path == "/api/admin/mappings":
                write_json(self, 200, {"ok": True, **self._server().store.save_product_mapping(payload)})
                return
            if parsed.path == "/api/admin/mappings/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_product_mapping(payload)})
                return
            if parsed.path == "/api/link-preview":
                self._enforce_rate_limit("link_preview", "링크 확인 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, self._server().store.preview_link(payload))
                return
            if parsed.path == "/api/charge":
                self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                amount = int(payload.get("amount") or 0)
                write_json(self, 200, self._server().store.charge_balance(amount))
                return
            raise PanelError("지원하지 않는 API 경로입니다.", status=404)
        except Exception as exc:
            send_error_json(self, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pulse24 demo SMM panel")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = PanelStore()
    config = AppConfig.from_env()
    admin_sessions = AdminSessionStore(
        os.environ.get("SMM_PANEL_ADMIN_USERNAME", "admin"),
        os.environ.get("SMM_PANEL_ADMIN_PASSWORD", ""),
    )
    rate_limiter = RequestRateLimiter()
    handler = partial(AppHandler, directory=str(STATIC_ROOT))
    httpd = PanelHTTPServer((args.host, args.port), handler, store, admin_sessions, config, rate_limiter)
    print(f"Pulse24 demo panel running at http://{args.host}:{args.port}")
    if not admin_sessions.is_configured:
        print("Admin routes are locked. Set SMM_PANEL_ADMIN_PASSWORD to enable /admin.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == "__main__":
    main()
