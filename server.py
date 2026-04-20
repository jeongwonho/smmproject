#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
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

from core import APP_ROOT, DEFAULT_SITE_NAME, PanelError, PanelStore


STATIC_ROOT = APP_ROOT / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8024
ADMIN_SESSION_COOKIE = "smm_panel_admin_session"
PUBLIC_SESSION_COOKIE = "smm_panel_user_session"
ADMIN_SESSION_TTL_SECONDS = 60 * 60 * 12
PUBLIC_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
MAX_JSON_BODY_BYTES = 10 * 1024 * 1024
ADMIN_LOGIN_WINDOW_SECONDS = 15 * 60
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ROBOTS_TXT = "User-agent: *\nDisallow: /admin\nDisallow: /api/admin\n"
INDEX_TEMPLATE_PATH = STATIC_ROOT / "index.html"
VERCEL_REWRITE_PATH_QUERY_KEY = "__path"


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


def runtime_mode() -> str:
    return str(
        os.environ.get("SMM_PANEL_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("NODE_ENV")
        or ""
    ).strip().lower()


def is_dev_runtime() -> bool:
    mode = runtime_mode()
    if mode in {"dev", "development", "demo", "local", "test"}:
        return True
    if mode in {"prod", "production", "live"}:
        return False
    return not bool(os.environ.get("VERCEL"))


def parse_origins(raw_value: str) -> tuple[str, ...]:
    origins: list[str] = []
    for candidate in str(raw_value or "").split(","):
        normalized = normalize_origin(candidate)
        if normalized and normalized not in origins:
            origins.append(normalized)
    return tuple(origins)


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def resolve_session_secret() -> str:
    direct_secret = str(os.environ.get("SMM_PANEL_SESSION_SECRET", "")).strip()
    if direct_secret:
        return direct_secret
    if not is_dev_runtime():
        raise RuntimeError(
            "SMM_PANEL_SESSION_SECRET is required in production-like environments. "
            "Set a strong random secret before starting the server."
        )
    derived_parts = [
        str(os.environ.get("SMM_PANEL_ADMIN_PASSWORD", "")).strip(),
        str(os.environ.get("SMM_PANEL_DATABASE_URL", "")).strip(),
        str(os.environ.get("SMM_PANEL_SUPABASE_DB_URL", "")).strip(),
    ]
    derived_material = "|".join(part for part in derived_parts if part)
    if derived_material:
        return hashlib.sha256(f"pulse24-session::{derived_material}".encode("utf-8")).hexdigest()
    return hashlib.sha256(f"pulse24-dev::{APP_ROOT}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AppConfig:
    public_api_base_url: str = ""
    allowed_origins: tuple[str, ...] = ()
    cookie_domain: str = ""
    admin_cookie_samesite: str = "Strict"
    public_cookie_samesite: str = "Lax"
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
        public_cookie_samesite = (os.environ.get("SMM_PANEL_PUBLIC_COOKIE_SAMESITE", "Lax").strip().capitalize() or "Lax")
        if public_cookie_samesite not in {"Strict", "Lax", "None"}:
            public_cookie_samesite = "Lax"
        return cls(
            public_api_base_url=public_api_base_url,
            allowed_origins=tuple(configured_origins),
            cookie_domain=cookie_domain,
            admin_cookie_samesite=admin_cookie_samesite,
            public_cookie_samesite=public_cookie_samesite,
            force_secure_cookies=env_flag(os.environ.get("SMM_PANEL_FORCE_SECURE_COOKIES", "")),
        )


class RequestRateLimiter:
    def __init__(self, rules: Optional[Dict[str, tuple[int, int]]] = None) -> None:
        self.rules = rules or {
            "orders": (20, 60),
            "link_preview": (30, 60),
            "charge": (12, 60),
            "analytics": (180, 60),
            "auth": (18, 60),
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


class SignedSessionStore:
    def __init__(self, secret: str, ttl_seconds: int, audience: str) -> None:
        self.secret = secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds
        self.audience = audience

    def _sign(self, payload_segment: str) -> str:
        digest = hmac.new(self.secret, payload_segment.encode("utf-8"), hashlib.sha256).digest()
        return _base64url_encode(digest)

    def create_session(self, payload: Dict[str, Any]) -> str:
        session_payload = {
            **payload,
            "aud": self.audience,
            "csrf_token": secrets.token_urlsafe(24),
            "exp": int(time.time()) + self.ttl_seconds,
        }
        encoded_payload = _base64url_encode(
            json.dumps(session_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        return f"{encoded_payload}.{self._sign(encoded_payload)}"

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        if not token or "." not in token:
            return None
        payload_segment, signature = token.rsplit(".", 1)
        expected_signature = self._sign(payload_segment)
        if not hmac.compare_digest(signature, expected_signature):
            return None
        try:
            payload = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if str(payload.get("aud") or "") != self.audience:
            return None
        if int(payload.get("exp") or 0) <= int(time.time()):
            return None
        return payload

    def destroy_session(self, token: str) -> None:
        return None


class AdminSessionStore:
    def __init__(
        self,
        username: str,
        password: str,
        secret: str,
        ttl_seconds: int = ADMIN_SESSION_TTL_SECONDS,
        login_window_seconds: int = ADMIN_LOGIN_WINDOW_SECONDS,
        login_max_attempts: int = ADMIN_LOGIN_MAX_ATTEMPTS,
    ) -> None:
        self.username = username.strip() or "admin"
        self.ttl_seconds = ttl_seconds
        self.login_window_seconds = login_window_seconds
        self.login_max_attempts = login_max_attempts
        self.password_hash = self._hash_value(password) if password else ""
        self.failed_attempts: Dict[str, list[float]] = {}
        self.signer = SignedSessionStore(secret, ttl_seconds, "admin")

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
        return self.signer.create_session({"username": self.username})

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        session = self.signer.get_session(token)
        if session is None:
            return None
        return session

    def destroy_session(self, token: str) -> None:
        self.signer.destroy_session(token)

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


class UserSessionStore:
    def __init__(self, secret: str, ttl_seconds: int = PUBLIC_SESSION_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self.signer = SignedSessionStore(secret, ttl_seconds, "public")

    def create_session(self, user_id: str) -> str:
        return self.signer.create_session({"user_id": user_id})

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        return self.signer.get_session(token)

    def destroy_session(self, token: str) -> None:
        self.signer.destroy_session(token)


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
    site_name = str(settings.get("siteName") or DEFAULT_SITE_NAME).strip() or DEFAULT_SITE_NAME
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
    document = template.replace(f"<title>{DEFAULT_SITE_NAME}</title>", title_markup)
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
        user_sessions: UserSessionStore,
        config: AppConfig,
        rate_limiter: RequestRateLimiter,
    ) -> None:
        super().__init__(server_address, handler_cls)
        self.store = store
        self.admin_sessions = admin_sessions
        self.user_sessions = user_sessions
        self.config = config
        self.rate_limiter = rate_limiter


@dataclass(frozen=True)
class RuntimeContext:
    store: PanelStore
    admin_sessions: AdminSessionStore
    user_sessions: UserSessionStore
    config: AppConfig
    rate_limiter: RequestRateLimiter


_RUNTIME_CONTEXT: RuntimeContext | None = None


def build_runtime_context() -> RuntimeContext:
    session_secret = resolve_session_secret()
    return RuntimeContext(
        store=PanelStore.from_env(),
        admin_sessions=AdminSessionStore(
            os.environ.get("SMM_PANEL_ADMIN_USERNAME", "admin"),
            os.environ.get("SMM_PANEL_ADMIN_PASSWORD", ""),
            session_secret,
        ),
        user_sessions=UserSessionStore(session_secret),
        config=AppConfig.from_env(),
        rate_limiter=RequestRateLimiter(),
    )


def configure_runtime_context(context: RuntimeContext | None = None) -> RuntimeContext:
    global _RUNTIME_CONTEXT
    _RUNTIME_CONTEXT = context or build_runtime_context()
    return _RUNTIME_CONTEXT


def get_runtime_context() -> RuntimeContext:
    return _RUNTIME_CONTEXT or configure_runtime_context()


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        self._request_path = ""
        super().__init__(*args, directory=str(STATIC_ROOT if directory is None else directory), **kwargs)

    def _server(self) -> PanelHTTPServer | RuntimeContext:
        server = self.server
        if all(hasattr(server, attribute) for attribute in ("store", "admin_sessions", "user_sessions", "config", "rate_limiter")):
            return server  # type: ignore[return-value]
        return get_runtime_context()

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
        server_port = int(getattr(self.server, "server_port", 443))
        return "https" if server_port == 443 else "http"

    def _request_host(self) -> str:
        forwarded_host = self.headers.get("X-Forwarded-Host", "").split(",")[0].strip()
        if forwarded_host:
            return forwarded_host
        host = self.headers.get("Host", "").strip()
        if host:
            return host
        server_name = str(getattr(self.server, "server_name", "localhost"))
        server_port = int(getattr(self.server, "server_port", 443))
        if server_port in {80, 443}:
            return server_name
        return f"{server_name}:{server_port}"

    def _request_origin(self) -> str:
        return normalize_origin(f"{self._request_scheme()}://{self._request_host()}")

    def _static_asset_path(self, request_path: str) -> Path:
        raw_path = str(request_path or "/").split("?", 1)[0].split("#", 1)[0]
        normalized = raw_path.lstrip("/")
        if normalized.startswith("static/"):
            normalized = normalized[len("static/") :]
        return (STATIC_ROOT / normalized).resolve()

    def _static_request_alias(self, request_path: str) -> str:
        raw_path = str(request_path or "/").split("?", 1)[0].split("#", 1)[0]
        normalized = raw_path.lstrip("/")
        if normalized.startswith("static/"):
            normalized = normalized[len("static/") :]
        return f"/{normalized}"

    def _incoming_request_path(self, raw_path: str) -> str:
        parsed = urlparse(raw_path)
        rewritten = parse_qs(parsed.query).get(VERCEL_REWRITE_PATH_QUERY_KEY, [""])[0]
        if rewritten:
            return str(rewritten)
        return parsed.path

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

    def _session_cookie_value(self, cookie_name: str) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(cookie_name)
        return morsel.value if morsel else ""

    def _admin_session_token(self) -> str:
        return self._session_cookie_value(ADMIN_SESSION_COOKIE)

    def _public_session_token(self) -> str:
        return self._session_cookie_value(PUBLIC_SESSION_COOKIE)

    def _admin_session(self) -> Optional[Dict[str, Any]]:
        return self._server().admin_sessions.get_session(self._admin_session_token())

    def _public_session(self) -> Optional[Dict[str, Any]]:
        token = self._public_session_token()
        session = self._server().user_sessions.get_session(token)
        if session is None:
            return None
        user = self._server().store.public_user_for_session(str(session.get("user_id") or ""))
        if user is None:
            self._server().user_sessions.destroy_session(token)
            return None
        return {**session, "user": user}

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

    def _require_public_auth(self) -> Dict[str, Any]:
        session = self._public_session()
        if session is None:
            raise PanelError("로그인이 필요합니다.", status=401)
        return session

    def _require_public_csrf(self, session: Dict[str, Any]) -> None:
        expected = str(session.get("csrf_token") or "")
        provided = self.headers.get("X-SMM-CSRF-Token", "").strip()
        if not expected or not provided or not hmac.compare_digest(provided, expected):
            raise PanelError("로그인 세션 검증에 실패했습니다. 다시 로그인해 주세요.", status=403)

    def _public_session_payload(self) -> Dict[str, Any]:
        session = self._public_session()
        user = session.get("user") if session else None
        return {
            "authenticated": session is not None,
            "csrfToken": session.get("csrf_token", "") if session else "",
            "user": user,
        }

    def _cookie_header(self, cookie_name: str, value: str, max_age: Optional[int], samesite: str) -> str:
        cookie = SimpleCookie()
        cookie[cookie_name] = value
        morsel = cookie[cookie_name]
        morsel["path"] = "/"
        morsel["httponly"] = True
        morsel["samesite"] = samesite
        if max_age is not None:
            morsel["max-age"] = str(max_age)
        if self._config().cookie_domain:
            morsel["domain"] = self._config().cookie_domain
        if (
            self._request_scheme() == "https"
            or self._config().force_secure_cookies
            or samesite == "None"
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
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        try:
            if parsed.path == "/api/health":
                write_json(self, 200, {"ok": True, "service": f"{DEFAULT_SITE_NAME} Panel"})
                return
            if parsed.path == "/robots.txt":
                write_text(self, 200, ROBOTS_TXT)
                return
            if parsed.path == "/api/admin/session":
                write_json(self, 200, {"ok": True, **self._server().admin_sessions.session_payload(self._admin_session_token())})
                return
            if parsed.path == "/api/session":
                write_json(self, 200, {"ok": True, **self._public_session_payload()})
                return
            if parsed.path == "/api/bootstrap":
                session = self._public_session()
                payload = self._server().store.bootstrap(str((session or {}).get("user", {}).get("id") or ""))
                payload["viewer"] = self._public_session_payload()
                write_json(self, 200, {"ok": True, **payload})
                return
            if parsed.path.startswith("/api/auth/oauth/") and parsed.path.endswith("/start"):
                provider = parsed.path.split("/")[4]
                raise PanelError(
                    f"{provider} OAuth는 환경변수 설정 후 활성화됩니다. 현재는 구조만 준비된 상태입니다.",
                    status=503,
                )
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
                session = self._require_public_auth()
                status = parse_qs(parsed.query).get("status", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_orders(status, str(session["user"]["id"]))})
                return
            if parsed.path == "/api/wallet":
                session = self._require_public_auth()
                write_json(self, 200, {"ok": True, **self._server().store.get_wallet(str(session["user"]["id"]))})
                return
            if parsed.path == "/api/wallet/ledger":
                session = self._require_public_auth()
                query = parse_qs(parsed.query)
                limit = query.get("limit", ["50"])[0]
                filters = {
                    "entryType": query.get("entryType", [""])[0],
                    "status": query.get("status", [""])[0],
                    "paymentChannel": query.get("paymentChannel", [""])[0],
                    "createdFrom": query.get("createdFrom", [""])[0],
                    "createdTo": query.get("createdTo", [""])[0],
                }
                write_json(
                    self,
                    200,
                    {"ok": True, **self._server().store.list_wallet_ledger(str(session["user"]["id"]), int(limit or 50), filters)},
                )
                return
            if parsed.path == "/api/charge-orders":
                session = self._require_public_auth()
                query = parse_qs(parsed.query)
                limit = query.get("limit", ["50"])[0]
                filters = {
                    "status": query.get("status", [""])[0],
                    "paymentChannel": query.get("paymentChannel", [""])[0],
                    "createdFrom": query.get("createdFrom", [""])[0],
                    "createdTo": query.get("createdTo", [""])[0],
                }
                write_json(
                    self,
                    200,
                    {"ok": True, **self._server().store.list_charge_orders(str(session["user"]["id"]), int(limit or 50), filters)},
                )
                return
            if parsed.path.startswith("/api/charge-orders/") and len([part for part in parsed.path.split("/") if part]) == 3:
                session = self._require_public_auth()
                charge_order_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, **self._server().store.get_charge_order(charge_order_id, str(session["user"]["id"]))})
                return
            if parsed.path == "/api/transactions":
                session = self._require_public_auth()
                write_json(self, 200, {"ok": True, **self._server().store.list_transactions(str(session["user"]["id"]))})
                return
        except Exception as exc:
            send_error_json(self, exc)
            return

        asset_path = self._static_asset_path(parsed.path)
        if parsed.path not in {"", "/"} and asset_path.is_file() and STATIC_ROOT in asset_path.parents:
            self.path = self._static_request_alias(parsed.path)
            super().do_GET()
            return

        self._serve_index_document()

    def do_HEAD(self) -> None:
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        if parsed.path == "/robots.txt":
            write_text(self, 200, ROBOTS_TXT, write_body=False)
            return

        asset_path = self._static_asset_path(parsed.path)
        if parsed.path not in {"", "/"} and asset_path.is_file() and STATIC_ROOT in asset_path.parents:
            self.path = self._static_request_alias(parsed.path)
            super().do_HEAD()
            return

        self._serve_index_document(write_body=False)

    def do_OPTIONS(self) -> None:
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        try:
            self._require_trusted_origin()
            write_text(self, 204, "", write_body=False)
        except Exception as exc:
            send_error_json(self, exc)

    def do_POST(self) -> None:
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        try:
            if parsed.path == "/api/payments/webhook":
                payload = read_json(self)
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        **self._server().store.process_payment_webhook(
                            payload,
                            provided_secret=self.headers.get("X-SMM-Webhook-Secret", ""),
                        ),
                    },
                )
                return
            self._require_trusted_origin()
            payload = read_json(self)
            if parsed.path == "/api/auth/email/send-code":
                self._enforce_rate_limit("auth", "인증 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, {"ok": True, **self._server().store.start_signup_email_verification(payload)})
                return
            if parsed.path == "/api/auth/email/verify-code":
                self._enforce_rate_limit("auth", "인증 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, {"ok": True, **self._server().store.verify_signup_email_code(payload)})
                return
            if parsed.path == "/api/login":
                self._enforce_rate_limit("auth", "로그인 시도가 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                email = str(payload.get("email") or "").strip()
                password = str(payload.get("password") or "")
                remember_me = bool(payload.get("rememberMe"))
                user = self._server().store.authenticate_public_user(email, password)
                token = self._server().user_sessions.create_session(user["id"])
                session = self._server().user_sessions.get_session(token) or {}
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "authenticated": True,
                        "csrfToken": session.get("csrf_token", ""),
                        "user": user,
                    },
                    extra_headers=[
                        (
                            "Set-Cookie",
                            self._cookie_header(
                                PUBLIC_SESSION_COOKIE,
                                token,
                                PUBLIC_SESSION_TTL_SECONDS if remember_me else None,
                                self._config().public_cookie_samesite,
                            ),
                        )
                    ],
                )
                return
            if parsed.path == "/api/signup":
                self._enforce_rate_limit("auth", "가입 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                user = self._server().store.register_public_user(payload)
                token = self._server().user_sessions.create_session(user["id"])
                session = self._server().user_sessions.get_session(token) or {}
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "authenticated": True,
                        "csrfToken": session.get("csrf_token", ""),
                        "user": user,
                    },
                    extra_headers=[
                        (
                            "Set-Cookie",
                            self._cookie_header(
                                PUBLIC_SESSION_COOKIE,
                                token,
                                PUBLIC_SESSION_TTL_SECONDS,
                                self._config().public_cookie_samesite,
                            ),
                        )
                    ],
                )
                return
            if parsed.path == "/api/orders":
                session = self._require_public_auth()
                self._require_public_csrf(session)
                self._enforce_rate_limit("orders", "주문 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, self._server().store.create_order(payload, str(session["user"]["id"])))
                return
            if parsed.path == "/api/charge-orders":
                session = self._require_public_auth()
                self._require_public_csrf(session)
                self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                write_json(self, 200, {"ok": True, **self._server().store.create_charge_order(payload, str(session["user"]["id"]))})
                return
            if parsed.path.startswith("/api/charge-orders/") and parsed.path.endswith("/start-payment"):
                session = self._require_public_auth()
                self._require_public_csrf(session)
                self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                charge_order_id = parsed.path.split("/")[3]
                write_json(
                    self,
                    200,
                    {"ok": True, **self._server().store.start_charge_order_payment(charge_order_id, payload, str(session["user"]["id"]))},
                )
                return
            if parsed.path.startswith("/api/charge-orders/") and parsed.path.endswith("/confirm"):
                session = self._require_public_auth()
                self._require_public_csrf(session)
                charge_order_id = parsed.path.split("/")[3]
                write_json(
                    self,
                    200,
                    {"ok": True, **self._server().store.confirm_charge_order(charge_order_id, payload, str(session["user"]["id"]))},
                )
                return
            if parsed.path.startswith("/api/charge-orders/") and parsed.path.endswith("/deposit-request"):
                session = self._require_public_auth()
                self._require_public_csrf(session)
                self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
                charge_order_id = parsed.path.split("/")[3]
                write_json(
                    self,
                    200,
                    {"ok": True, **self._server().store.submit_charge_order_deposit_request(charge_order_id, payload, str(session["user"]["id"]))},
                )
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
                    extra_headers=[
                        (
                            "Set-Cookie",
                            self._cookie_header(
                                ADMIN_SESSION_COOKIE,
                                token,
                                ADMIN_SESSION_TTL_SECONDS,
                                self._config().admin_cookie_samesite,
                            ),
                        )
                    ],
                )
                return
            session: Optional[Dict[str, Any]] = None
            if parsed.path.startswith("/api/admin/"):
                session = self._require_admin_auth()
                self._require_admin_csrf(session)
            if parsed.path == "/api/logout":
                session = self._public_session()
                if session is not None:
                    self._require_public_csrf(session)
                self._server().user_sessions.destroy_session(self._public_session_token())
                write_json(
                    self,
                    200,
                    {"ok": True, "authenticated": False},
                    extra_headers=[
                        (
                            "Set-Cookie",
                            self._cookie_header(
                                PUBLIC_SESSION_COOKIE,
                                "",
                                0,
                                self._config().public_cookie_samesite,
                            ),
                        )
                    ],
                )
                return
            if parsed.path == "/api/admin/logout":
                self._server().admin_sessions.destroy_session(self._admin_session_token())
                write_json(
                    self,
                    200,
                    {"ok": True, "authenticated": False},
                    extra_headers=[
                        (
                            "Set-Cookie",
                            self._cookie_header(
                                ADMIN_SESSION_COOKIE,
                                "",
                                0,
                                self._config().admin_cookie_samesite,
                            ),
                        )
                    ],
                )
                return
            if parsed.path == "/api/admin/site-settings":
                write_json(self, 200, {"ok": True, **self._server().store.save_site_settings(payload)})
                return
            if parsed.path == "/api/admin/popup":
                write_json(self, 200, {"ok": True, **self._server().store.save_home_popup(payload)})
                return
            if parsed.path == "/api/admin/home-banners":
                write_json(self, 200, {"ok": True, **self._server().store.save_home_banner(payload)})
                return
            if parsed.path == "/api/admin/platform-sections":
                write_json(self, 200, {"ok": True, **self._server().store.save_platform_section(payload)})
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
                raise PanelError(
                    "직접 잔액 충전 API는 종료되었습니다. /api/charge-orders 기반 충전 플로우를 사용해 주세요.",
                    status=410,
                )
            raise PanelError("지원하지 않는 API 경로입니다.", status=404)
        except Exception as exc:
            send_error_json(self, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{DEFAULT_SITE_NAME} SMM panel")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = configure_runtime_context()
    store = runtime.store
    config = runtime.config
    admin_sessions = runtime.admin_sessions
    user_sessions = runtime.user_sessions
    rate_limiter = runtime.rate_limiter
    handler = partial(AppHandler, directory=str(STATIC_ROOT))
    httpd = PanelHTTPServer((args.host, args.port), handler, store, admin_sessions, user_sessions, config, rate_limiter)
    print(f"{DEFAULT_SITE_NAME} panel running at http://{args.host}:{args.port}")
    print(f"Storage backend: {store.backend}")
    if not admin_sessions.is_configured:
        print("Admin routes are locked. Set SMM_PANEL_ADMIN_PASSWORD to enable /admin.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == "__main__":
    main()
