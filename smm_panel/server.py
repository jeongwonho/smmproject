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
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlparse

from backend.auth import hash_password, verify_password
from backend.cron_auth import cron_authorization_valid, cron_secret
from backend.errors import PanelError
from backend.cafe24_analytics import get_cafe24_ga4_analytics
from backend.integrations.cafe24_manual import build_cafe24_manual_input_cron_response
from core import APP_ROOT, DEFAULT_SITE_NAME, PanelStore


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
ROBOTS_TXT = "User-agent: *\nDisallow: /admin\nDisallow: /admin/\nDisallow: /api/\nAllow: /\n"
INDEX_TEMPLATE_PATH = STATIC_ROOT / "index.html"
VERCEL_REWRITE_PATH_QUERY_KEY = "__path"
PUBLIC_SHELL_CACHE_SECONDS = 60
PUBLIC_BOOTSTRAP_CACHE_SECONDS = 60
PUBLIC_CATALOG_CACHE_SECONDS = 60
PUBLIC_SHELL_CACHE_CONTROL = "public, max-age=60, s-maxage=300, stale-while-revalidate=1800"
PUBLIC_BOOTSTRAP_CACHE_CONTROL = "public, max-age=60, s-maxage=300, stale-while-revalidate=1800"
PUBLIC_CATALOG_CACHE_CONTROL = "public, max-age=60, s-maxage=300, stale-while-revalidate=1800"
PUBLIC_CACHE_INVALIDATING_METHODS = {
    "save_site_settings",
    "save_home_popup",
    "save_home_banner",
    "save_platform_section",
    "save_category",
    "delete_category",
    "save_catalog_product",
    "delete_catalog_product",
    "save_notice",
    "delete_notice",
    "save_faq",
    "delete_faq",
}


def env_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def bounded_timeout_seconds(value: Any, default_seconds: float = 6.0) -> float:
    try:
        timeout = float(value or 0)
    except (TypeError, ValueError):
        timeout = 0.0
    if timeout <= 0:
        timeout = default_seconds
    return max(2.0, min(timeout, 30.0))


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
    def __init__(
        self,
        rules: Optional[Dict[str, tuple[int, int]]] = None,
        persistent_enforcer: Optional[Callable[[str, str, int, int], int]] = None,
    ) -> None:
        self.rules = rules or {
            "orders": (20, 60),
            "link_preview": (30, 60),
            "charge": (12, 60),
            "analytics": (180, 60),
            "auth": (18, 60),
            "admin_login": (8, 15 * 60),
        }
        self.persistent_enforcer = persistent_enforcer
        self.events: Dict[str, list[float]] = {}
        self.lock = threading.Lock()
        self.max_keys = 2000

    def _key(self, bucket: str, client_key: str) -> str:
        return f"{bucket}:{client_key}"

    def _trim_storage_if_needed(self) -> None:
        if len(self.events) <= self.max_keys:
            return
        now = time.time()
        for storage_key in list(self.events.keys()):
            bucket = storage_key.split(":", 1)[0]
            window_seconds = self.rules.get(bucket, (0, 60))[1]
            recent = [attempt for attempt in self.events.get(storage_key, []) if attempt > now - window_seconds]
            if recent:
                self.events[storage_key] = recent
            else:
                self.events.pop(storage_key, None)
            if len(self.events) <= self.max_keys:
                return
        for storage_key in sorted(self.events, key=lambda key: min(self.events.get(key, [0])))[: max(0, len(self.events) - self.max_keys)]:
            self.events.pop(storage_key, None)

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
        if self.persistent_enforcer is not None:
            try:
                limit, window_seconds = self.rules[bucket]
                retry_after = int(self.persistent_enforcer(bucket, client_key, limit, window_seconds) or 0)
            except Exception as exc:
                print(f"[rate-limit-fallback] {bucket}: {exc}")
            else:
                if retry_after:
                    raise PanelError(message.format(retry_after=retry_after), status=429)
                return
        with self.lock:
            self._trim_storage_if_needed()
            retry_after = self.retry_after(bucket, client_key)
            if retry_after:
                raise PanelError(message.format(retry_after=retry_after), status=429)
            self.record(bucket, client_key)


class TTLResponseCache:
    def __init__(self, max_items: int = 128) -> None:
        self.max_items = max_items
        self.items: Dict[str, tuple[float, bytes]] = {}
        self.lock = threading.Lock()

    def _prune(self, now: float) -> None:
        for key, (expires_at, _) in list(self.items.items()):
            if expires_at <= now:
                self.items.pop(key, None)
        if len(self.items) <= self.max_items:
            return
        for key in sorted(self.items, key=lambda item_key: self.items[item_key][0])[: len(self.items) - self.max_items]:
            self.items.pop(key, None)

    def get_or_set(self, key: str, ttl_seconds: int, factory: Any) -> Dict[str, Any]:
        now = time.time()
        with self.lock:
            self._prune(now)
            cached = self.items.get(key)
            if cached is not None and cached[0] > now:
                return json.loads(cached[1].decode("utf-8"))
        payload = factory()
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with self.lock:
            self.items[key] = (now + max(1, ttl_seconds), raw)
            self._prune(now)
        return json.loads(raw.decode("utf-8"))

    def clear(self) -> None:
        with self.lock:
            self.items.clear()


class SignedSessionStore:
    def __init__(self, secret: str, ttl_seconds: int, audience: str) -> None:
        self.secret = secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds
        self.audience = audience
        self.revoked_tokens: Dict[str, int] = {}

    def _sign(self, payload_segment: str) -> str:
        digest = hmac.new(self.secret, payload_segment.encode("utf-8"), hashlib.sha256).digest()
        return _base64url_encode(digest)

    def _token_fingerprint(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _prune_revoked_tokens(self) -> None:
        now = int(time.time())
        expired = [fingerprint for fingerprint, expires_at in self.revoked_tokens.items() if expires_at <= now]
        for fingerprint in expired:
            self.revoked_tokens.pop(fingerprint, None)

    def _is_revoked(self, token: str) -> bool:
        self._prune_revoked_tokens()
        return self._token_fingerprint(token) in self.revoked_tokens

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
        if self._is_revoked(token):
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
        if not token or "." not in token:
            return
        payload_segment, signature = token.rsplit(".", 1)
        expected_signature = self._sign(payload_segment)
        if not hmac.compare_digest(signature, expected_signature):
            return
        try:
            payload = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        if str(payload.get("aud") or "") != self.audience:
            return
        expires_at = int(payload.get("exp") or 0)
        if expires_at <= int(time.time()):
            return
        self._prune_revoked_tokens()
        self.revoked_tokens[self._token_fingerprint(token)] = expires_at


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
        raw = str(value or "")
        if raw.startswith("pbkdf2_sha256$"):
            return raw
        return hash_password(raw)

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
        return verify_password(password, self.password_hash)

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
    payload, _ = read_json_with_raw_body(handler)
    return payload


def read_json_with_raw_body(handler: SimpleHTTPRequestHandler) -> tuple[Dict[str, Any], bytes]:
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}, b""
    if length > MAX_JSON_BODY_BYTES:
        raise PanelError("요청 본문이 너무 큽니다.", status=413)
    raw_body = handler.rfile.read(length)
    try:
        return json.loads(raw_body.decode("utf-8")), raw_body
    except json.JSONDecodeError as exc:
        raise PanelError("요청 형식이 올바르지 않습니다.", status=400) from exc


def write_json(
    handler: SimpleHTTPRequestHandler,
    status: int,
    payload: Dict[str, Any],
    cache_control: str = "no-store",
    extra_headers: Sequence[tuple[str, str]] = (),
) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", cache_control)
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
    if is_admin:
        document = document.replace('data-route-surface="public"', 'data-route-surface="admin"')
        document = document.replace(
            '<link rel="stylesheet" href="/static/styles/public.css" data-surface-style="public" />',
            '<link rel="stylesheet" href="/static/styles/admin.css" data-surface-style="admin" />',
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
        public_cache: TTLResponseCache,
    ) -> None:
        super().__init__(server_address, handler_cls)
        self.store = store
        self.admin_sessions = admin_sessions
        self.user_sessions = user_sessions
        self.config = config
        self.rate_limiter = rate_limiter
        self.public_cache = public_cache


@dataclass(frozen=True)
class RuntimeContext:
    store: PanelStore
    admin_sessions: AdminSessionStore
    user_sessions: UserSessionStore
    config: AppConfig
    rate_limiter: RequestRateLimiter
    public_cache: TTLResponseCache


_RUNTIME_CONTEXT: RuntimeContext | None = None


@dataclass(frozen=True)
class RouteRequest:
    path: str
    parsed: Any
    query: Dict[str, list[str]]
    params: Dict[str, str]
    payload: Dict[str, Any] = field(default_factory=dict)
    raw_body: bytes = b""
    admin_session: Optional[Dict[str, Any]] = None
    public_session: Optional[Dict[str, Any]] = None


RouteHandler = Callable[[Any, RouteRequest], None]


def _compile_route_pattern(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    cursor = 0
    for match in re.finditer(r"<([a-zA-Z_][a-zA-Z0-9_]*)>", pattern):
        parts.append(re.escape(pattern[cursor : match.start()]))
        parts.append(f"(?P<{match.group(1)}>[^/]+)")
        cursor = match.end()
    parts.append(re.escape(pattern[cursor:]))
    return re.compile(f"^{''.join(parts)}$")


@dataclass(frozen=True)
class RouteEntry:
    method: str
    pattern: str
    handler: RouteHandler
    auth: str = "none"
    csrf: bool = False
    trusted_origin: bool = False
    read_json_body: bool = False
    read_raw_json_body: bool = False
    regex: re.Pattern[str] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "regex", _compile_route_pattern(self.pattern))

    def match(self, path: str) -> Optional[Dict[str, str]]:
        matched = self.regex.match(path)
        if matched is None:
            return None
        return {key: unquote(value) for key, value in matched.groupdict().items()}


class RouterRegistry:
    def __init__(self) -> None:
        self.routes: Dict[str, list[RouteEntry]] = {"GET": [], "POST": []}

    def add(self, entry: RouteEntry) -> None:
        self.routes.setdefault(entry.method.upper(), []).append(entry)

    def match(self, method: str, path: str) -> tuple[RouteEntry, Dict[str, str]] | None:
        for entry in self.routes.get(method.upper(), []):
            params = entry.match(path)
            if params is not None:
                return entry, params
        return None


ROUTER = RouterRegistry()


def route(
    method: str,
    pattern: str,
    *,
    auth: str = "none",
    csrf: bool = False,
    trusted_origin: bool = False,
    read_json_body: bool = False,
    read_raw_json_body: bool = False,
) -> Callable[[RouteHandler], RouteHandler]:
    def decorator(handler: RouteHandler) -> RouteHandler:
        ROUTER.add(
            RouteEntry(
                method=method.upper(),
                pattern=pattern,
                handler=handler,
                auth=auth,
                csrf=csrf,
                trusted_origin=trusted_origin,
                read_json_body=read_json_body,
                read_raw_json_body=read_raw_json_body,
            )
        )
        return handler

    return decorator


def build_runtime_context() -> RuntimeContext:
    session_secret = resolve_session_secret()
    store = PanelStore.from_env()
    return RuntimeContext(
        store=store,
        admin_sessions=AdminSessionStore(
            os.environ.get("SMM_PANEL_ADMIN_USERNAME", "admin"),
            os.environ.get("SMM_PANEL_ADMIN_PASSWORD", ""),
            session_secret,
        ),
        user_sessions=UserSessionStore(session_secret),
        config=AppConfig.from_env(),
        rate_limiter=RequestRateLimiter(persistent_enforcer=store.shared_rate_limit_retry_after),
        public_cache=TTLResponseCache(),
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

    def _cafe24_oauth_redirect_uri(self) -> str:
        configured = os.environ.get("SMM_PANEL_CAFE24_REDIRECT_URI", "").strip()
        parsed = urlparse(configured)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            # OAuth redirect_uri matching is exact. Do not strip a trailing slash
            # or otherwise normalize the path after the operator configured it.
            return configured
        return f"{self._request_origin()}/api/admin/cafe24/oauth/callback"

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
        rewritten = ""
        preserved_query_items: list[tuple[str, str]] = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key == VERCEL_REWRITE_PATH_QUERY_KEY and not rewritten:
                rewritten = value
                continue
            preserved_query_items.append((key, value))
        if rewritten:
            query = urlencode(preserved_query_items)
            return f"{rewritten}?{query}" if query else str(rewritten)
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
            "img-src 'self' data: https:; "
            "style-src 'self'; "
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
            self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        if self._disable_static_cache():
            self.send_header("Cache-Control", "no-store")
        if self._robots_blocked_path():
            self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet, noimageindex")
        allowed_origin = self._allowed_cors_origin()
        if allowed_origin and self._request_path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-SMM-CSRF-Token")
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

    def _require_cron_auth(self) -> None:
        if cron_authorization_valid(self.headers.get("Authorization", ""), self.headers):
            return
        if not cron_secret():
            raise PanelError("CRON_SECRET 또는 GitHub Actions Cron 검증이 필요합니다.", status=503)
        raise PanelError("Cron 요청 인증에 실패했습니다.", status=401)

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

    def _public_cached_payload(self, cache_key: str, ttl_seconds: int, factory: Any) -> Dict[str, Any]:
        return self._server().public_cache.get_or_set(cache_key, ttl_seconds, factory)

    def _server_timing_header(self, name: str, started_at: float) -> tuple[str, str]:
        metric = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-") or "app"
        elapsed_ms = max(0.0, (time.perf_counter() - started_at) * 1000.0)
        return ("Server-Timing", f"{metric};dur={elapsed_ms:.1f}")

    def _query_value(self, request: RouteRequest, key: str, default: str = "") -> str:
        return request.query.get(key, [default])[0]

    def _dispatch_route(self, method: str, parsed: Any) -> bool:
        matched = ROUTER.match(method, parsed.path)
        if matched is None:
            return False

        entry, params = matched
        if entry.trusted_origin:
            self._require_trusted_origin()

        admin_session: Optional[Dict[str, Any]] = None
        public_session: Optional[Dict[str, Any]] = None
        if entry.auth == "admin":
            admin_session = self._require_admin_auth()
            if entry.csrf:
                self._require_admin_csrf(admin_session)
        elif entry.auth == "public":
            public_session = self._require_public_auth()
            if entry.csrf:
                self._require_public_csrf(public_session)
        elif entry.auth == "cron":
            self._require_cron_auth()
        elif entry.auth != "none":
            raise PanelError("라우트 인증 설정이 올바르지 않습니다.", status=500)

        payload: Dict[str, Any] = {}
        raw_body = b""
        if entry.read_raw_json_body:
            payload, raw_body = read_json_with_raw_body(self)
        elif entry.read_json_body:
            payload = read_json(self)
        if admin_session is not None and (entry.read_json_body or entry.read_raw_json_body):
            payload["_adminActor"] = str(admin_session.get("username") or "admin")

        request = RouteRequest(
            path=parsed.path,
            parsed=parsed,
            query=parse_qs(parsed.query),
            params=params,
            payload=payload,
            raw_body=raw_body,
            admin_session=admin_session,
            public_session=public_session,
        )
        entry.handler(self, request)
        return True

    def _write_store_result(self, method_name: str, payload: Dict[str, Any]) -> None:
        result = getattr(self._server().store, method_name)(payload)
        if method_name in PUBLIC_CACHE_INVALIDATING_METHODS:
            self._server().public_cache.clear()
        write_json(self, 200, {"ok": True, **result})

    @route("GET", "/api/health")
    def _get_health(self, request: RouteRequest) -> None:
        started_at = time.perf_counter()
        write_json(
            self,
            200,
            {"ok": True, "service": f"{DEFAULT_SITE_NAME} Panel"},
            extra_headers=[self._server_timing_header("health", started_at)],
        )

    @route("GET", "/api/cron/suppliers/sync", auth="cron")
    def _get_cron_supplier_sync(self, request: RouteRequest) -> None:
        limit = int(self._query_value(request, "limit", "10") or 10)
        request_timeout_seconds = bounded_timeout_seconds(self._query_value(request, "requestTimeoutSeconds", "6"))
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.sync_due_supplier_services(
                    actor="cron",
                    limit=limit,
                    request_timeout_seconds=request_timeout_seconds,
                ),
            },
        )

    @route("GET", "/robots.txt")
    def _get_robots(self, request: RouteRequest) -> None:
        write_text(self, 200, ROBOTS_TXT)

    @route("GET", "/api/admin/session")
    def _get_admin_session(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._server().admin_sessions.session_payload(self._admin_session_token())})

    @route("GET", "/api/session")
    def _get_public_session(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._public_session_payload()})

    @route("GET", "/api/public-shell")
    def _get_public_shell(self, request: RouteRequest) -> None:
        started_at = time.perf_counter()
        session = self._public_session()
        user_id = str((session or {}).get("user", {}).get("id") or "")
        payload = (
            self._server().store.public_shell(user_id)
            if user_id
            else self._public_cached_payload(
                "public-shell:v1",
                PUBLIC_SHELL_CACHE_SECONDS,
                lambda: self._server().store.public_shell(""),
            )
        )
        payload["viewer"] = self._public_session_payload()
        write_json(
            self,
            200,
            {"ok": True, **payload},
            cache_control="no-store" if session else PUBLIC_SHELL_CACHE_CONTROL,
            extra_headers=[self._server_timing_header("public-shell", started_at)],
        )

    @route("GET", "/api/bootstrap")
    def _get_bootstrap(self, request: RouteRequest) -> None:
        started_at = time.perf_counter()
        session = self._public_session()
        user_id = str((session or {}).get("user", {}).get("id") or "")
        payload = (
            self._server().store.bootstrap(user_id)
            if user_id
            else self._public_cached_payload(
                "bootstrap:v1",
                PUBLIC_BOOTSTRAP_CACHE_SECONDS,
                lambda: self._server().store.bootstrap(""),
            )
        )
        payload["viewer"] = self._public_session_payload()
        write_json(
            self,
            200,
            {"ok": True, **payload},
            cache_control="no-store" if session else PUBLIC_BOOTSTRAP_CACHE_CONTROL,
            extra_headers=[self._server_timing_header("bootstrap", started_at)],
        )

    @route("GET", "/api/auth/oauth/<provider>/start")
    def _get_oauth_start(self, request: RouteRequest) -> None:
        provider = request.params.get("provider", "")
        raise PanelError(f"{provider} OAuth는 환경변수 설정 후 활성화됩니다. 현재는 구조만 준비된 상태입니다.", status=503)

    @route("GET", "/api/admin/cafe24/oauth/callback")
    def _get_cafe24_oauth_callback(self, request: RouteRequest) -> None:
        error = self._query_value(request, "error")
        if error:
            self._redirect(
                "/admin/cafe24?"
                + urlencode(
                    {
                        "cafe24OAuth": "error",
                        "message": self._query_value(request, "error_description", error),
                    }
                )
            )
            return
        try:
            self._server().store.complete_cafe24_oauth_callback(
                {
                    "state": self._query_value(request, "state"),
                    "code": self._query_value(request, "code"),
                }
            )
            self._redirect("/admin/cafe24?cafe24OAuth=success")
        except Exception as exc:
            message = str(exc) if isinstance(exc, PanelError) else "Cafe24 OAuth 토큰 저장에 실패했습니다."
            self._redirect("/admin/cafe24?" + urlencode({"cafe24OAuth": "error", "message": message}))

    @route("GET", "/api/admin/bootstrap", auth="admin")
    def _get_admin_bootstrap(self, request: RouteRequest) -> None:
        payload = self._server().store.admin_bootstrap()
        payload["cafe24OAuthRedirectUri"] = self._cafe24_oauth_redirect_uri()
        write_json(self, 200, {"ok": True, **payload})

    @route("GET", "/api/admin/cafe24/order-items", auth="admin")
    def _get_admin_cafe24_order_items(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.list_cafe24_order_items(
                    {
                        "integrationId": self._query_value(request, "integrationId"),
                        "from": self._query_value(request, "from"),
                        "to": self._query_value(request, "to"),
                        "page": self._query_value(request, "page", "1"),
                        "pageSize": self._query_value(request, "pageSize", "5"),
                        "payment": self._query_value(request, "payment", "all"),
                        "mapping": self._query_value(request, "mapping", "all"),
                        "status": self._query_value(request, "status", "all"),
                        "search": self._query_value(request, "q", self._query_value(request, "search")),
                    }
                ),
            },
        )

    @route("GET", "/api/admin/cafe24/operational-audit", auth="admin")
    def _get_admin_cafe24_operational_audit(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._server().store.cafe24_operational_audit()})

    @route("GET", "/api/admin/cafe24-analytics", auth="admin")
    def _get_admin_cafe24_analytics(self, request: RouteRequest) -> None:
        range_id = self._query_value(request, "range", "30d")
        write_json(self, 200, {"ok": True, **get_cafe24_ga4_analytics(range_id)})

    @route("GET", "/api/cron/cafe24/operational-audit", auth="cron")
    def _get_cron_cafe24_operational_audit(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._server().store.cafe24_operational_audit()})

    @route("POST", "/api/admin/cafe24/mapping-gaps", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_mapping_gaps(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._server().store.cafe24_mapping_gap_report(request.payload)})

    @route("POST", "/api/cron/cafe24/mapping-gaps", auth="cron", read_json_body=True)
    def _post_cron_cafe24_mapping_gaps(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        write_json(self, 200, {"ok": True, **self._server().store.cafe24_mapping_gap_report(payload)})

    @route("GET", "/api/admin/customers/<customer_id>", auth="admin")
    def _get_admin_customer_detail(self, request: RouteRequest) -> None:
        write_json(self, 200, {"ok": True, **self._server().store.get_customer_detail(request.params["customer_id"])})

    @route("GET", "/api/admin/cafe24/products", auth="admin")
    def _get_admin_cafe24_products(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.list_cafe24_products(
                    {
                        "integrationId": self._query_value(request, "integrationId"),
                        "q": self._query_value(request, "q"),
                        "productNo": self._query_value(request, "productNo"),
                        "limit": self._query_value(request, "limit", "20"),
                        "offset": self._query_value(request, "offset", "0"),
                    }
                ),
            },
        )

    @route("GET", "/api/admin/cafe24/products/<product_no>", auth="admin")
    def _get_admin_cafe24_product_detail(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.get_cafe24_product_detail(
                    {
                        "integrationId": self._query_value(request, "integrationId"),
                        "productNo": request.params["product_no"],
                    }
                ),
            },
        )

    @route(
        "POST",
        "/api/admin/cafe24/products/<product_no>/configure-daily-follower",
        auth="admin",
        csrf=True,
        trusted_origin=True,
        read_json_body=True,
    )
    def _post_admin_cafe24_configure_daily_follower(self, request: RouteRequest) -> None:
        request.payload["productNo"] = request.params["product_no"]
        self._write_store_result("configure_cafe24_daily_follower_product", request.payload)

    @route("GET", "/api/products")
    def _get_products(self, request: RouteRequest) -> None:
        started_at = time.perf_counter()
        search_query = self._query_value(request, "q")
        cache_key = f"products:v1:{search_query.strip().lower()[:160]}"
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._public_cached_payload(
                    cache_key,
                    PUBLIC_CATALOG_CACHE_SECONDS,
                    lambda: self._server().store.list_catalog(search_query),
                ),
            },
            cache_control=PUBLIC_CATALOG_CACHE_CONTROL,
            extra_headers=[self._server_timing_header("products", started_at)],
        )

    @route("GET", "/api/admin/suppliers/<supplier_id>/services", auth="admin")
    def _get_admin_supplier_services(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {"ok": True, **self._server().store.list_supplier_services(request.params["supplier_id"], self._query_value(request, "q"))},
        )

    @route("GET", "/api/admin/suppliers/<supplier_id>/mkt24-product-settings/<product_uuid>", auth="admin")
    def _get_admin_mkt24_product_setting(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.get_mkt24_product_setting(
                    {
                        "supplierId": request.params["supplier_id"],
                        "productUuid": request.params["product_uuid"],
                        "refresh": self._query_value(request, "refresh", "0") in {"1", "true", "yes"},
                    }
                ),
            },
        )

    @route("GET", "/api/product-categories/<category_id>")
    def _get_product_category(self, request: RouteRequest) -> None:
        started_at = time.perf_counter()
        category_id = request.params["category_id"]
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._public_cached_payload(
                    f"product-category:v1:{category_id}",
                    PUBLIC_CATALOG_CACHE_SECONDS,
                    lambda: {"category": self._server().store.get_product_category(category_id)},
                ),
            },
            cache_control=PUBLIC_CATALOG_CACHE_CONTROL,
            extra_headers=[self._server_timing_header("product-category", started_at)],
        )

    @route("GET", "/api/orders", auth="public")
    def _get_orders(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, {"ok": True, **self._server().store.list_orders(self._query_value(request, "status"), user_id)})

    @route("GET", "/api/wallet", auth="public")
    def _get_wallet(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, {"ok": True, **self._server().store.get_wallet(user_id)})

    @route("GET", "/api/wallet/ledger", auth="public")
    def _get_wallet_ledger(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        filters = {
            "entryType": self._query_value(request, "entryType"),
            "status": self._query_value(request, "status"),
            "paymentChannel": self._query_value(request, "paymentChannel"),
            "createdFrom": self._query_value(request, "createdFrom"),
            "createdTo": self._query_value(request, "createdTo"),
        }
        write_json(
            self,
            200,
            {"ok": True, **self._server().store.list_wallet_ledger(user_id, int(self._query_value(request, "limit", "50") or 50), filters)},
        )

    @route("GET", "/api/charge-orders", auth="public")
    def _get_charge_orders(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        filters = {
            "status": self._query_value(request, "status"),
            "paymentChannel": self._query_value(request, "paymentChannel"),
            "createdFrom": self._query_value(request, "createdFrom"),
            "createdTo": self._query_value(request, "createdTo"),
        }
        write_json(
            self,
            200,
            {"ok": True, **self._server().store.list_charge_orders(user_id, int(self._query_value(request, "limit", "50") or 50), filters)},
        )

    @route("GET", "/api/charge-orders/<charge_order_id>", auth="public")
    def _get_charge_order(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, {"ok": True, **self._server().store.get_charge_order(request.params["charge_order_id"], user_id)})

    @route("GET", "/api/transactions", auth="public")
    def _get_transactions(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, {"ok": True, **self._server().store.list_transactions(user_id)})

    def do_GET(self) -> None:
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        try:
            if self._dispatch_route("GET", parsed):
                return
            if parsed.path.startswith("/api/"):
                raise PanelError("지원하지 않는 API 경로입니다.", status=404)
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

    @route("POST", "/api/payments/webhook", read_raw_json_body=True)
    def _post_payment_webhook(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.process_payment_webhook(
                    request.payload,
                    provided_secret=self.headers.get("X-SMM-Webhook-Secret", ""),
                    provided_signature=self.headers.get("X-SMM-Webhook-Signature", "")
                    or self.headers.get("X-Payment-Signature", ""),
                    provided_timestamp=self.headers.get("X-SMM-Webhook-Timestamp", "")
                    or self.headers.get("X-Payment-Timestamp", ""),
                    raw_body=request.raw_body,
                ),
            },
        )

    @route("POST", "/api/cafe24/webhooks/orders", read_raw_json_body=True)
    def _post_cafe24_order_webhook(self, request: RouteRequest) -> None:
        result = self._server().store.process_cafe24_order_webhook(
            request.payload,
            provided_api_key=self.headers.get("X-API-Key", ""),
            trace_id=self.headers.get("X-Trace-ID", "")
            or self.headers.get("X-Trace-Id", "")
            or self.headers.get("X-Trace ID", ""),
        )
        write_json(self, 200, {"ok": result.get("status") in {"processed", "ignored"}, **result})

    @route("POST", "/api/cron/suppliers/sync", auth="cron", read_json_body=True)
    def _post_cron_supplier_sync(self, request: RouteRequest) -> None:
        request_timeout_seconds = bounded_timeout_seconds(
            request.payload.get("requestTimeoutSeconds")
            or request.payload.get("request_timeout_seconds")
            or 6
        )
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.sync_due_supplier_services(
                    actor="cron",
                    limit=int(request.payload.get("limit") or 10),
                    request_timeout_seconds=request_timeout_seconds,
                ),
            },
        )

    @route("POST", "/api/cron/cafe24/orders/poll", auth="cron", read_json_body=True)
    def _post_cron_cafe24_orders_poll(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.poll_due_cafe24_orders(payload),
            },
        )

    @route("POST", "/api/cron/automation/tick", auth="cron", read_json_body=True)
    def _post_cron_automation_tick(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.run_automation_tick(payload)
        write_json(
            self,
            500 if result.get("status") == "failed" else 200,
            {
                "ok": result.get("status") != "failed",
                **result,
            },
        )

    @route("POST", "/api/cron/cafe24/flow-tick", auth="cron", read_json_body=True)
    def _post_cron_cafe24_flow_tick(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.run_cafe24_flow_tick(payload)
        flow_ok = result.get("status") in {"success", "locked"}
        write_json(
            self,
            500 if result.get("status") == "failed" else 200,
            {
                "ok": flow_ok,
                **result,
            },
        )

    @route("POST", "/api/cron/cafe24/email-order-witness", auth="cron", read_json_body=True)
    def _post_cron_cafe24_email_order_witness(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.reconcile_cafe24_email_order_witness(payload)
        write_json(self, 200, {"ok": True, **result})

    @route("POST", "/api/cron/cafe24/order-items/dispatch-one", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_dispatch_one(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.dispatch_single_cafe24_order_item(payload)
        write_json(self, 200, {"ok": True, **result})

    @route("POST", "/api/cron/cafe24/order-items/preflight", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_preflight(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.preflight_single_cafe24_order_item(payload)
        write_json(self, 200, {"ok": True, **result})

    @route("POST", "/api/cron/cafe24/order-items/preview", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_preview(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.preview_single_cafe24_order_item(payload)
        write_json(self, 200, {"ok": True, **result})

    @route("POST", "/api/cron/cafe24/order-items/manual-input/preview", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_manual_input_preview(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        if not env_flag(payload.get("confirmManualInputPreview")):
            raise PanelError("Cron 수동 보정 미리보기는 confirmManualInputPreview=true가 필요합니다.", status=400)
        payload["_adminActor"] = "cron"
        result = self._server().store.preview_cafe24_order_item_manual_input(payload)
        write_json(self, 200, {"ok": True, **result})

    @route("POST", "/api/cron/cafe24/order-items/manual-input", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_manual_input(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        if not env_flag(payload.get("confirmManualInput")):
            raise PanelError("Cron 수동 보정은 confirmManualInput=true가 필요합니다.", status=400)
        payload["_adminActor"] = "cron"
        result = self._server().store.save_cafe24_order_item_manual_input(payload)
        item = result.get("item") or {}
        item_id = str(item.get("id") or payload.get("itemId") or payload.get("id") or "")
        expected_quantity = payload.get("expectedQuantity") or payload.get("expected_quantity") or payload.get("orderedCount")
        preflight = self._server().store.preflight_single_cafe24_order_item(
            {"itemId": item_id, "expectedQuantity": expected_quantity, "_adminActor": "cron"}
        )
        dispatch_after_save = env_flag(payload.get("dispatchAfterSave") or payload.get("dispatch_after_save"))
        dispatch_result = None
        if dispatch_after_save:
            if not bool(preflight.get("canDispatch")):
                raise PanelError("수동 보정 preflight가 발주 가능 상태가 아니므로 단건 발주를 실행하지 않았습니다.", status=409)
            dispatch_result = self._server().store.dispatch_cafe24_order_item(
                {"itemId": item_id, "_adminActor": "cron"}
            )
        write_json(
            self,
            200,
            build_cafe24_manual_input_cron_response(
                item_id=item_id,
                result=result,
                preflight=preflight,
                dispatch_after_save=dispatch_after_save,
                dispatch=dispatch_result,
            ),
        )

    @route("POST", "/api/cron/cafe24/order-items/check-supplier-status", auth="cron", read_json_body=True)
    def _post_cron_cafe24_order_items_check_supplier_status(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        payload["_adminActor"] = "cron"
        result = self._server().store.check_single_cafe24_supplier_status(payload)
        write_json(self, 200, {"ok": result.get("supplierStatus") != "check_failed", **result})

    @route("POST", "/api/auth/email/send-code", trusted_origin=True, read_json_body=True)
    def _post_auth_email_send_code(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("auth", "인증 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        write_json(self, 200, {"ok": True, **self._server().store.start_signup_email_verification(request.payload)})

    @route("POST", "/api/auth/email/verify-code", trusted_origin=True, read_json_body=True)
    def _post_auth_email_verify_code(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("auth", "인증 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        write_json(self, 200, {"ok": True, **self._server().store.verify_signup_email_code(request.payload)})

    @route("POST", "/api/login", trusted_origin=True, read_json_body=True)
    def _post_login(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("auth", "로그인 시도가 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        email = str(request.payload.get("email") or "").strip()
        password = str(request.payload.get("password") or "")
        remember_me = bool(request.payload.get("rememberMe"))
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

    @route("POST", "/api/signup", trusted_origin=True, read_json_body=True)
    def _post_signup(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("auth", "가입 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        user = self._server().store.register_public_user(request.payload)
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

    @route("POST", "/api/orders", auth="public", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_orders(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("orders", "주문 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, self._server().store.create_order(request.payload, user_id))

    @route("POST", "/api/charge-orders", auth="public", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_charge_orders(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(self, 200, {"ok": True, **self._server().store.create_charge_order(request.payload, user_id)})

    @route("POST", "/api/charge-orders/<charge_order_id>/start-payment", auth="public", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_charge_order_start_payment(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.start_charge_order_payment(request.params["charge_order_id"], request.payload, user_id),
            },
        )

    @route("POST", "/api/charge-orders/<charge_order_id>/confirm", auth="public", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_charge_order_confirm(self, request: RouteRequest) -> None:
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(
            self,
            200,
            {"ok": True, **self._server().store.confirm_charge_order(request.params["charge_order_id"], request.payload, user_id)},
        )

    @route("POST", "/api/charge-orders/<charge_order_id>/deposit-request", auth="public", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_charge_order_deposit_request(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("charge", "충전 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        user_id = str(request.public_session["user"]["id"]) if request.public_session else ""
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.submit_charge_order_deposit_request(
                    request.params["charge_order_id"],
                    request.payload,
                    user_id,
                ),
            },
        )

    @route("POST", "/api/analytics/track", trusted_origin=True, read_json_body=True)
    def _post_analytics_track(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("analytics", "방문 수집 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.record_site_visit(
                    request.payload,
                    user_agent=self.headers.get("User-Agent", ""),
                    request_host=self.headers.get("Host", ""),
                ),
            },
        )

    @route("POST", "/api/admin/login", trusted_origin=True, read_json_body=True)
    def _post_admin_login(self, request: RouteRequest) -> None:
        username = str(request.payload.get("username") or "").strip()
        password = str(request.payload.get("password") or "")
        admin_sessions = self._server().admin_sessions
        client_identity = self._client_identity()
        self._enforce_rate_limit("admin_login", "로그인 시도가 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        if not admin_sessions.is_configured:
            raise PanelError(
                "관리자 보안 설정이 없습니다. SMM_PANEL_ADMIN_PASSWORD 환경변수를 설정한 뒤 서버를 다시 실행해 주세요.",
                status=503,
            )
        retry_after = admin_sessions.login_retry_after(client_identity)
        if retry_after:
            raise PanelError(f"로그인 시도가 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.", status=429)
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

    @route("POST", "/api/logout", trusted_origin=True, read_json_body=True)
    def _post_logout(self, request: RouteRequest) -> None:
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
                    self._cookie_header(PUBLIC_SESSION_COOKIE, "", 0, self._config().public_cookie_samesite),
                )
            ],
        )

    @route("POST", "/api/admin/logout", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_logout(self, request: RouteRequest) -> None:
        self._server().admin_sessions.destroy_session(self._admin_session_token())
        write_json(
            self,
            200,
            {"ok": True, "authenticated": False},
            extra_headers=[
                (
                    "Set-Cookie",
                    self._cookie_header(ADMIN_SESSION_COOKIE, "", 0, self._config().admin_cookie_samesite),
                )
            ],
        )

    @route("POST", "/api/admin/site-settings", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_site_settings(self, request: RouteRequest) -> None:
        self._write_store_result("save_site_settings", request.payload)

    @route("POST", "/api/admin/popup", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_popup(self, request: RouteRequest) -> None:
        self._write_store_result("save_home_popup", request.payload)

    @route("POST", "/api/admin/home-banners", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_home_banners(self, request: RouteRequest) -> None:
        self._write_store_result("save_home_banner", request.payload)

    @route("POST", "/api/admin/platform-sections", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_platform_sections(self, request: RouteRequest) -> None:
        self._write_store_result("save_platform_section", request.payload)

    @route("POST", "/api/admin/suppliers", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_suppliers(self, request: RouteRequest) -> None:
        self._write_store_result("save_supplier", request.payload)

    @route("POST", "/api/admin/mkt24-product-settings", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_mkt24_product_settings(self, request: RouteRequest) -> None:
        self._write_store_result("save_mkt24_product_setting", request.payload)

    @route("POST", "/api/admin/mkt24-product-settings/sync", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_mkt24_product_settings_sync(self, request: RouteRequest) -> None:
        self._write_store_result("sync_mkt24_product_detail", request.payload)

    @route("POST", "/api/admin/cafe24/oauth/start", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_oauth_start(self, request: RouteRequest) -> None:
        request.payload["redirectUri"] = request.payload.get("redirectUri") or self._cafe24_oauth_redirect_uri()
        self._write_store_result("create_cafe24_oauth_authorize_url", request.payload)

    @route("POST", "/api/admin/cafe24/integrations", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_integrations(self, request: RouteRequest) -> None:
        self._write_store_result("save_cafe24_integration", request.payload)

    @route("POST", "/api/admin/cafe24/mappings", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_mappings(self, request: RouteRequest) -> None:
        self._write_store_result("save_cafe24_product_mapping", request.payload)

    @route("POST", "/api/admin/cafe24/mappings/preview", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_mappings_preview(self, request: RouteRequest) -> None:
        self._write_store_result("preview_cafe24_mapping", request.payload)

    @route("POST", "/api/admin/cafe24/mappings/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_mappings_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_cafe24_product_mapping", request.payload)

    @route("POST", "/api/admin/cafe24/poll", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_poll(self, request: RouteRequest) -> None:
        self._write_store_result("poll_cafe24_orders", request.payload)

    @route("POST", "/api/admin/cafe24/orders/resync-by-id", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_orders_resync_by_id(self, request: RouteRequest) -> None:
        self._write_store_result("resync_cafe24_order_by_id", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/retry", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_retry(self, request: RouteRequest) -> None:
        self._write_store_result("retry_cafe24_order_item", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/preflight", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_preflight(self, request: RouteRequest) -> None:
        self._write_store_result("preflight_single_cafe24_order_item", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/dispatch", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_dispatch(self, request: RouteRequest) -> None:
        self._write_store_result("dispatch_cafe24_order_item", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/resync", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_resync(self, request: RouteRequest) -> None:
        self._write_store_result("resync_cafe24_order_item", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/manual-input/preview", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_manual_input_preview(self, request: RouteRequest) -> None:
        self._write_store_result("preview_cafe24_order_item_manual_input", request.payload)

    @route("POST", "/api/admin/cafe24/order-items/manual-input", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_manual_input(self, request: RouteRequest) -> None:
        payload = dict(request.payload or {})
        result = self._server().store.save_cafe24_order_item_manual_input(payload)
        item = result.get("item") or {}
        item_id = str(item.get("id") or payload.get("itemId") or payload.get("id") or "")
        expected_quantity = payload.get("expectedQuantity") or payload.get("expected_quantity") or payload.get("orderedCount")
        preflight = self._server().store.preflight_single_cafe24_order_item(
            {
                "itemId": item_id,
                "expectedQuantity": expected_quantity,
                "_adminActor": payload.get("_adminActor") or "admin",
            }
        )
        write_json(self, 200, {"ok": True, **result, "preflight": preflight})

    @route("POST", "/api/admin/cafe24/order-items/status", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_cafe24_order_items_status(self, request: RouteRequest) -> None:
        self._write_store_result("update_cafe24_order_item_status", request.payload)

    @route("POST", "/api/admin/customers", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_customers(self, request: RouteRequest) -> None:
        self._write_store_result("save_customer", request.payload)

    @route("POST", "/api/admin/customers/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_customers_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_customer", request.payload)

    @route("POST", "/api/admin/customers/balance", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_customers_balance(self, request: RouteRequest) -> None:
        self._write_store_result("adjust_customer_balance", request.payload)

    @route("POST", "/api/admin/charge-orders/action", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_charge_orders_action(self, request: RouteRequest) -> None:
        self._write_store_result("admin_update_charge_order", request.payload)

    @route("POST", "/api/admin/categories", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_categories(self, request: RouteRequest) -> None:
        self._write_store_result("save_category", request.payload)

    @route("POST", "/api/admin/categories/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_categories_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_category", request.payload)

    @route("POST", "/api/admin/products", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_products(self, request: RouteRequest) -> None:
        self._write_store_result("save_catalog_product", request.payload)

    @route("POST", "/api/admin/products/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_products_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_catalog_product", request.payload)

    @route("POST", "/api/admin/orders/status", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_orders_status(self, request: RouteRequest) -> None:
        self._write_store_result("update_admin_order_status", request.payload)

    @route("POST", "/api/admin/orders/retry-supplier", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_orders_retry_supplier(self, request: RouteRequest) -> None:
        self._write_store_result("retry_supplier_order", request.payload)

    @route("POST", "/api/admin/orders/supplier-status", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_orders_supplier_status(self, request: RouteRequest) -> None:
        self._write_store_result("refresh_supplier_order_status", request.payload)

    @route("POST", "/api/admin/notices", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_notices(self, request: RouteRequest) -> None:
        self._write_store_result("save_notice", request.payload)

    @route("POST", "/api/admin/notices/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_notices_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_notice", request.payload)

    @route("POST", "/api/admin/faqs", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_faqs(self, request: RouteRequest) -> None:
        self._write_store_result("save_faq", request.payload)

    @route("POST", "/api/admin/faqs/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_faqs_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_faq", request.payload)

    @route("POST", "/api/admin/suppliers/test", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_suppliers_test(self, request: RouteRequest) -> None:
        self._write_store_result("test_supplier_connection", request.payload)

    @route("POST", "/api/admin/suppliers/<supplier_id>/sync-services", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_supplier_sync_services(self, request: RouteRequest) -> None:
        write_json(
            self,
            200,
            {
                "ok": True,
                **self._server().store.sync_supplier_services(
                    request.params["supplier_id"],
                    actor=str(request.payload.get("_adminActor") or "admin"),
                ),
            },
        )

    @route("POST", "/api/admin/mappings", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_mappings(self, request: RouteRequest) -> None:
        self._write_store_result("save_product_mapping", request.payload)

    @route("POST", "/api/admin/mappings/delete", auth="admin", csrf=True, trusted_origin=True, read_json_body=True)
    def _post_admin_mappings_delete(self, request: RouteRequest) -> None:
        self._write_store_result("delete_product_mapping", request.payload)

    @route("POST", "/api/link-preview", trusted_origin=True, read_json_body=True)
    def _post_link_preview(self, request: RouteRequest) -> None:
        self._enforce_rate_limit("link_preview", "링크 확인 요청이 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.")
        write_json(self, 200, self._server().store.preview_link(request.payload))

    @route("POST", "/api/charge", trusted_origin=True, read_json_body=True)
    def _post_legacy_charge(self, request: RouteRequest) -> None:
        raise PanelError("직접 잔액 충전 API는 종료되었습니다. /api/charge-orders 기반 충전 플로우를 사용해 주세요.", status=410)

    def do_POST(self) -> None:
        request_path = self._incoming_request_path(self.path)
        parsed = urlparse(request_path)
        self._request_path = parsed.path
        try:
            if self._dispatch_route("POST", parsed):
                return
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
    httpd = PanelHTTPServer(
        (args.host, args.port),
        handler,
        store,
        admin_sessions,
        user_sessions,
        config,
        rate_limiter,
        runtime.public_cache,
    )
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
