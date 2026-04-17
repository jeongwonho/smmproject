from __future__ import annotations

from collections import Counter, defaultdict
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import sqlite3
from html import escape as html_escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row as psycopg_dict_row
except ImportError:  # pragma: no cover - optional runtime dependency
    psycopg = None
    psycopg_dict_row = None


APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = APP_ROOT / "data"
DB_PATH = DATA_ROOT / "smm_panel.db"
DEMO_USER_ID = "user_demo"
PREVIEW_TIMEOUT_SECONDS = 6
PREVIEW_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
ANALYTICS_LOOKBACK_DAYS = 90
SEARCH_REFERRER_LABELS = {
    "google.": ("search", "Google"),
    "naver.com": ("search", "Naver"),
    "bing.com": ("search", "Bing"),
    "daum.net": ("search", "Daum"),
    "yahoo.com": ("search", "Yahoo"),
}
SOCIAL_REFERRER_LABELS = {
    "instagram.com": ("social", "Instagram"),
    "facebook.com": ("social", "Facebook"),
    "threads.net": ("social", "Threads"),
    "tiktok.com": ("social", "TikTok"),
    "youtube.com": ("social", "YouTube"),
    "x.com": ("social", "X"),
    "twitter.com": ("social", "X"),
}
SUPPLIER_INTEGRATION_CLASSIC = "classic"
SUPPLIER_INTEGRATION_MKT24 = "mkt24"
SUPPLIER_PLATFORM_LABELS = {
    "instagram": "인스타그램",
    "youtube": "유튜브",
    "facebook": "페이스북",
    "threads": "스레드",
    "naver": "N포털",
    "tiktok": "틱톡",
    "x": "X",
    "twitter": "X",
}
PREVIEW_BLOCKED_HOSTNAMES = {"localhost"}
PREVIEW_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'STANDARD',
    role TEXT NOT NULL DEFAULT 'customer',
    avatar_label TEXT NOT NULL DEFAULT 'P24',
    balance INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    last_login_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_sections (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '●',
    accent_color TEXT NOT NULL DEFAULT '#4c76ff',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS platform_groups (
    id TEXT PRIMARY KEY,
    platform_section_id TEXT NOT NULL REFERENCES platform_sections(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS product_categories (
    id TEXT PRIMARY KEY,
    platform_group_id TEXT NOT NULL REFERENCES platform_groups(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    option_label_name TEXT DEFAULT '',
    category_kind TEXT NOT NULL DEFAULT 'normal',
    hero_title TEXT NOT NULL DEFAULT '',
    hero_subtitle TEXT NOT NULL DEFAULT '',
    service_description_html TEXT NOT NULL DEFAULT '',
    caution_json TEXT NOT NULL DEFAULT '[]',
    refund_notice_json TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    product_category_id TEXT NOT NULL REFERENCES product_categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    menu_name TEXT NOT NULL,
    option_name TEXT NOT NULL DEFAULT '',
    product_code TEXT NOT NULL,
    price INTEGER NOT NULL,
    min_amount INTEGER NOT NULL DEFAULT 1,
    max_amount INTEGER NOT NULL DEFAULT 1,
    step_amount INTEGER NOT NULL DEFAULT 1,
    option_price_rate INTEGER NOT NULL DEFAULT 100,
    price_strategy TEXT NOT NULL DEFAULT 'unit',
    unit_label TEXT NOT NULL DEFAULT '개',
    supports_order_options INTEGER NOT NULL DEFAULT 1,
    is_discounted INTEGER NOT NULL DEFAULT 0,
    product_kind TEXT NOT NULL DEFAULT 'normal',
    is_custom INTEGER NOT NULL DEFAULT 0,
    estimated_turnaround TEXT NOT NULL DEFAULT '',
    badge TEXT NOT NULL DEFAULT '',
    form_structure_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS home_banners (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    cta_label TEXT NOT NULL,
    route TEXT NOT NULL,
    image_url TEXT NOT NULL DEFAULT '',
    theme TEXT NOT NULL DEFAULT 'blue',
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS home_interest_tags (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    route TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS home_spotlights (
    id TEXT PRIMARY KEY,
    section_key TEXT NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    route TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '★',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS support_links (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    route TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '◎',
    external_url TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS benefits (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notices (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tag TEXT NOT NULL DEFAULT '공지',
    pinned INTEGER NOT NULL DEFAULT 0,
    published_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faqs (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_number TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform_section_id TEXT NOT NULL REFERENCES platform_sections(id),
    product_category_id TEXT NOT NULL REFERENCES product_categories(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    product_name_snapshot TEXT NOT NULL,
    option_name_snapshot TEXT NOT NULL DEFAULT '',
    target_value TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price INTEGER NOT NULL,
    total_price INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    notes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_fields (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    field_key TEXT NOT NULL,
    field_label TEXT NOT NULL,
    field_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS balance_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    kind TEXT NOT NULL,
    memo TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_url TEXT NOT NULL,
    integration_type TEXT NOT NULL DEFAULT 'classic',
    api_key TEXT NOT NULL,
    bearer_token TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    last_test_status TEXT NOT NULL DEFAULT 'never',
    last_test_message TEXT NOT NULL DEFAULT '',
    last_balance TEXT NOT NULL DEFAULT '',
    last_currency TEXT NOT NULL DEFAULT '',
    last_service_count INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_services (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    external_service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT '',
    rate REAL NOT NULL DEFAULT 0,
    min_amount INTEGER NOT NULL DEFAULT 0,
    max_amount INTEGER NOT NULL DEFAULT 0,
    dripfeed INTEGER NOT NULL DEFAULT 0,
    refill INTEGER NOT NULL DEFAULT 0,
    cancel INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL DEFAULT '{}',
    synced_at TEXT NOT NULL,
    UNIQUE(supplier_id, external_service_id)
);

CREATE TABLE IF NOT EXISTS product_supplier_mappings (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_service_id TEXT NOT NULL REFERENCES supplier_services(id) ON DELETE CASCADE,
    supplier_external_service_id TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    pricing_mode TEXT NOT NULL DEFAULT 'multiplier',
    price_multiplier REAL NOT NULL DEFAULT 1.0,
    fixed_markup INTEGER NOT NULL DEFAULT 0,
    last_synced_at TEXT NOT NULL,
    UNIQUE(product_id, supplier_id, supplier_service_id)
);

CREATE TABLE IF NOT EXISTS supplier_orders (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_service_id TEXT NOT NULL DEFAULT '',
    supplier_external_order_id TEXT NOT NULL DEFAULT '',
    request_payload_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS home_popups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    badge_text TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',
    route TEXT NOT NULL DEFAULT '/',
    theme TEXT NOT NULL DEFAULT 'coral',
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    site_name TEXT NOT NULL,
    site_description TEXT NOT NULL DEFAULT '',
    use_mail_sms_site_name INTEGER NOT NULL DEFAULT 0,
    mail_sms_site_name TEXT NOT NULL DEFAULT '',
    favicon_url TEXT NOT NULL DEFAULT '',
    share_image_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_visit_events (
    id TEXT PRIMARY KEY,
    visitor_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    route TEXT NOT NULL,
    page_label TEXT NOT NULL DEFAULT '',
    referrer_url TEXT NOT NULL DEFAULT '',
    referrer_domain TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'direct',
    source_label TEXT NOT NULL DEFAULT '직접 방문',
    search_keyword TEXT NOT NULL DEFAULT '',
    previous_route TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    device_type TEXT NOT NULL DEFAULT 'desktop',
    exclude_from_stats INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_site_visit_events_created_at
    ON site_visit_events(created_at);

CREATE INDEX IF NOT EXISTS idx_site_visit_events_route
    ON site_visit_events(route);

CREATE INDEX IF NOT EXISTS idx_site_visit_events_session
    ON site_visit_events(session_id);
"""


class PanelError(Exception):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def split_sql_script(script: str) -> List[str]:
    statements: List[str] = []
    buffer: List[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []
    if buffer:
        statement = "\n".join(buffer).strip().rstrip(";").strip()
        if statement:
            statements.append(statement)
    return statements


def rewrite_postgres_placeholders(query: str) -> str:
    if "?" not in query:
        return query
    result: List[str] = []
    in_single = False
    in_double = False
    index = 0
    while index < len(query):
        char = query[index]
        if char == "'" and not in_double:
            result.append(char)
            if in_single and index + 1 < len(query) and query[index + 1] == "'":
                result.append("'")
                index += 2
                continue
            in_single = not in_single
            index += 1
            continue
        if char == '"' and not in_single:
            result.append(char)
            in_double = not in_double
            index += 1
            continue
        if char == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(char)
        index += 1
    return "".join(result)


def normalize_database_row(row: Any, description: Any = None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return dict(row)
    if isinstance(row, (tuple, list)) and description:
        columns: List[str] = []
        for column in description:
            if isinstance(column, (tuple, list)) and column:
                columns.append(str(column[0]))
            else:
                columns.append(str(getattr(column, "name", "")))
        return {column: value for column, value in zip(columns, row)}
    return dict(row)


class DatabaseCursor:
    def __init__(self, raw_cursor: Any) -> None:
        self.raw_cursor = raw_cursor

    @property
    def description(self) -> Any:
        return getattr(self.raw_cursor, "description", None)

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return normalize_database_row(self.raw_cursor.fetchone(), self.description)

    def fetchall(self) -> List[Dict[str, Any]]:
        return [
            normalized
            for row in self.raw_cursor.fetchall()
            if (normalized := normalize_database_row(row, self.description)) is not None
        ]

    def __iter__(self):
        for row in self.raw_cursor:
            normalized = normalize_database_row(row, self.description)
            if normalized is not None:
                yield normalized


class DatabaseConnection:
    def __init__(self, backend: str, raw_connection: Any) -> None:
        self.backend = backend
        self.raw_connection = raw_connection

    def _prepare_query(self, query: str) -> str:
        if self.backend == "postgres":
            return rewrite_postgres_placeholders(query)
        return query

    def execute(self, query: str, params: Iterable[Any] = ()) -> DatabaseCursor:
        prepared_query = self._prepare_query(query)
        if params:
            raw_cursor = self.raw_connection.execute(prepared_query, tuple(params))
        else:
            raw_cursor = self.raw_connection.execute(prepared_query)
        return DatabaseCursor(raw_cursor)

    def executemany(self, query: str, rows: Iterable[Iterable[Any]]) -> DatabaseCursor:
        prepared_query = self._prepare_query(query)
        payload = [tuple(row) for row in rows]
        if self.backend == "postgres":
            raw_cursor = self.raw_connection.cursor()
            raw_cursor.executemany(prepared_query, payload)
            return DatabaseCursor(raw_cursor)
        raw_cursor = self.raw_connection.executemany(prepared_query, payload)
        return DatabaseCursor(raw_cursor)

    def executescript(self, script: str) -> None:
        if self.backend == "sqlite":
            self.raw_connection.executescript(script)
            return
        for statement in split_sql_script(script):
            if statement.upper().startswith("PRAGMA "):
                continue
            self.raw_connection.execute(statement)

    def commit(self) -> None:
        self.raw_connection.commit()

    def rollback(self) -> None:
        self.raw_connection.rollback()

    def close(self) -> None:
        self.raw_connection.close()

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


class PreviewHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: Dict[str, str] = {}
        self.icons: List[str] = []
        self._title_parts: List[str] = []
        self._in_title = False

    @property
    def title(self) -> str:
        return "".join(self._title_parts).strip()

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta":
            meta_key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content", "").strip()
            if meta_key and content and meta_key not in self.meta:
                self.meta[meta_key] = content
            return

        if tag.lower() == "link":
            rel = attr_map.get("rel", "").lower()
            href = attr_map.get("href", "").strip()
            if href and any(token in rel for token in ("icon", "apple-touch-icon")):
                self.icons.append(href)
            return

        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


PASSWORD_HASH_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    raw = str(password or "")
    if not raw:
        return ""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${derived.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    raw_password = str(password or "")
    stored = str(encoded_hash or "").strip()
    if not raw_password or not stored:
        return False
    parts = stored.split("$", 3)
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    _, iteration_text, salt, digest = parts
    try:
        iterations = int(iteration_text)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(candidate.hex(), digest)


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_json(raw: str, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def money(value: int) -> str:
    return f"{value:,}원"


def default_home_popup_record() -> Dict[str, Any]:
    return {
        "id": "popup_home_youtube_rank",
        "name": "홈 유튜브 상위노출 팝업",
        "badgeText": "상단(1~5위) 노출 보장!",
        "title": "유튜브 상위노출\n서비스 출시!",
        "description": "신규 런칭 기념으로 빠르게 확인할 수 있는 홈 프로모션 팝업입니다.",
        "imageUrl": "",
        "route": "/products/cat_youtube_views",
        "theme": "coral",
        "isActive": True,
    }


def default_site_settings_record() -> Dict[str, Any]:
    return {
        "siteName": "Pulse24",
        "siteDescription": "Reference-style SMM Growth Panel",
        "useMailSmsSiteName": False,
        "mailSmsSiteName": "",
        "faviconUrl": "",
        "shareImageUrl": "",
    }


def parse_iso_datetime(raw: str) -> Optional[dt.datetime]:
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed


def normalize_analytics_route(raw: Any) -> str:
    candidate = str(raw or "").strip()
    if not candidate:
        return ""
    if re.match(r"^https?://", candidate, re.IGNORECASE):
        parsed = urlparse(candidate)
        candidate = parsed.path or "/"
    if not candidate.startswith("/"):
        candidate = f"/{candidate.lstrip('/')}"
    candidate = "/" + candidate.lstrip("/")
    if candidate.startswith(("/admin", "/api")):
        return ""
    return candidate


def date_key(value: dt.date) -> str:
    return value.isoformat()


def canonical_domain(hostname: str) -> str:
    host = str(hostname or "").strip().lower()
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m.") and host.endswith((".facebook.com", ".instagram.com", ".youtube.com")):
        host = host[2:]
    if host.startswith("l.facebook.com"):
        return "facebook.com"
    return host


def looks_like_test_identity(*values: Any) -> bool:
    combined = " ".join(str(value or "").lower() for value in values)
    return any(token in combined for token in ("test", "demo", "example", "pulse24.local"))


def mask_email(email: str) -> str:
    raw = str(email or "").strip()
    if not raw or "@" not in raw:
        return ""
    local, domain = raw.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(2, len(local) - 2)
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 7:
        return ""
    if len(digits) >= 11:
        return f"{digits[:3]}-****-{digits[-4:]}"
    return f"{digits[:3]}-***-{digits[-4:]}"


def mask_secret(secret: str, visible_suffix: int = 4) -> str:
    raw = str(secret or "").strip()
    if not raw:
        return ""
    if len(raw) <= visible_suffix:
        return "*" * len(raw)
    return f"{'*' * max(6, len(raw) - visible_suffix)}{raw[-visible_suffix:]}"


def normalize_supplier_integration_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value == SUPPLIER_INTEGRATION_MKT24:
        return SUPPLIER_INTEGRATION_MKT24
    return SUPPLIER_INTEGRATION_CLASSIC


def supplier_supports_balance_check(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) == SUPPLIER_INTEGRATION_CLASSIC


def supplier_supports_auto_dispatch(integration_type: str) -> bool:
    return normalize_supplier_integration_type(integration_type) == SUPPLIER_INTEGRATION_CLASSIC


def supplier_platform_label(platform_key: str) -> str:
    key = str(platform_key or "").strip().lower()
    if not key:
        return ""
    return SUPPLIER_PLATFORM_LABELS.get(key, key.replace("_", " ").title())


def avatar_label(name: str) -> str:
    cleaned = "".join(part for part in str(name or "").strip().split())
    if not cleaned:
        return "P24"
    return cleaned[:2].upper()


def looks_like_url(raw: str) -> bool:
    candidate = raw.strip()
    if not candidate:
        return False
    if candidate.startswith(("http://", "https://")):
        return True
    return bool(re.match(r"^(www\.)?[\w.-]+\.[a-z]{2,}([/:?#].*)?$", candidate, re.IGNORECASE))


def normalize_url(raw: str) -> Optional[str]:
    candidate = raw.strip()
    if not candidate:
        return None
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None
    return candidate


def normalize_navigation_target(raw: str, default: str = "/") -> str:
    candidate = str(raw or "").strip()
    if not candidate:
        return default
    if re.match(r"^https?://", candidate, re.IGNORECASE):
        return candidate
    candidate = candidate.replace("\\", "/")
    candidate = re.sub(r"^\.+", "", candidate).strip()
    if not candidate.startswith("/"):
        candidate = f"/{candidate.lstrip('/')}"
    return candidate or default


def normalize_popup_image_source(raw: Any) -> str:
    return normalize_image_asset_source(raw, "팝업 이미지")


def normalize_image_asset_source(raw: Any, label: str = "이미지") -> str:
    candidate = str(raw or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("data:image/"):
        return candidate
    if candidate.startswith("/"):
        return candidate
    normalized = normalize_url(candidate)
    if normalized:
        return normalized
    raise PanelError(f"{label} 주소 형식이 올바르지 않습니다.")


def preview_platform_hint(product_code: str, platform_slug: str) -> str:
    lowered = f"{platform_slug} {product_code}".lower()
    for keyword, resolved in (
        ("instagram", "instagram"),
        ("youtube", "youtube"),
        ("tiktok", "tiktok"),
        ("threads", "threads"),
        ("facebook", "facebook"),
        ("naver", "nportal"),
        ("blog", "nportal"),
    ):
        if keyword in lowered:
            return resolved
    return platform_slug


def account_preview_url(account_value: str, platform_hint: str) -> Optional[str]:
    cleaned = account_value.strip().strip("/")
    if not cleaned:
        return None
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    cleaned = cleaned.replace(" ", "")
    if not re.fullmatch(r"[\w.\-]+", cleaned):
        return None

    builders = {
        "instagram": lambda handle: f"https://www.instagram.com/{handle}/",
        "threads": lambda handle: f"https://www.threads.net/@{handle}",
        "youtube": lambda handle: f"https://www.youtube.com/@{handle}",
        "tiktok": lambda handle: f"https://www.tiktok.com/@{handle}",
        "facebook": lambda handle: f"https://www.facebook.com/{handle}",
    }
    builder = builders.get(platform_hint)
    return builder(cleaned) if builder else None


ACCOUNT_STYLE_PLATFORMS = {"instagram", "threads", "youtube", "tiktok", "facebook"}


def platform_target_url_matches(platform_hint: str, raw_url: str) -> bool:
    normalized = normalize_url(raw_url)
    if not normalized:
        return False

    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    path = parsed.path or "/"

    def host_is(domain: str) -> bool:
        return host == domain or host.endswith(f".{domain}")

    if platform_hint == "instagram":
        return host_is("instagram.com") and path.strip("/") != ""
    if platform_hint == "youtube":
        return host == "youtu.be" or host_is("youtube.com")
    if platform_hint == "tiktok":
        return host_is("tiktok.com")
    if platform_hint == "facebook":
        return host_is("facebook.com")
    if platform_hint == "threads":
        return host_is("threads.net")
    if platform_hint == "nportal":
        return host_is("naver.com")
    return looks_like_url(normalized)


def platform_target_error_message(platform_hint: str) -> str:
    labels = {
        "instagram": "인스타그램",
        "youtube": "유튜브",
        "tiktok": "틱톡",
        "facebook": "페이스북",
        "threads": "스레드",
        "nportal": "네이버",
    }
    platform_label = labels.get(platform_hint, "해당 플랫폼")
    return f"{platform_label} 형식에 맞는 링크 또는 계정을 입력해 주세요."


def placeholder_thumbnail(label: str, accent_color: str) -> str:
    safe_label = (label or "LINK")[:28]
    initials = "".join(part[:1] for part in re.findall(r"[A-Za-z0-9가-힣]+", safe_label)[:2]).upper() or "PK"
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="220" viewBox="0 0 320 220" fill="none">
      <defs>
        <linearGradient id="g" x1="32" y1="26" x2="286" y2="204" gradientUnits="userSpaceOnUse">
          <stop stop-color="{html_escape(accent_color)}"/>
          <stop offset="1" stop-color="#1F2937"/>
        </linearGradient>
      </defs>
      <rect width="320" height="220" rx="28" fill="url(#g)"/>
      <circle cx="72" cy="74" r="34" fill="rgba(255,255,255,0.18)"/>
      <text x="72" y="85" text-anchor="middle" font-size="28" font-weight="700" fill="#FFFFFF">{html_escape(initials)}</text>
      <text x="28" y="150" font-size="22" font-weight="700" fill="#FFFFFF">{html_escape(safe_label[:20])}</text>
      <text x="28" y="180" font-size="14" fill="rgba(255,255,255,0.72)">Pulse24 Link Preview</text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


def is_public_network_address(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_preview_target(target_url: str) -> None:
    parsed = urlparse(str(target_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid preview target")
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("invalid preview target")
    if hostname in PREVIEW_BLOCKED_HOSTNAMES or hostname.endswith(PREVIEW_BLOCKED_SUFFIXES):
        raise ValueError("blocked preview target")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        if not is_public_network_address(hostname):
            raise ValueError("blocked preview target")
        return
    except ValueError:
        pass

    try:
        resolved = {
            sockaddr[0]
            for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            if sockaddr and sockaddr[0]
        }
    except socket.gaierror as exc:
        raise ValueError("unresolved preview target") from exc
    if not resolved:
        raise ValueError("unresolved preview target")
    for address in resolved:
        if not is_public_network_address(address):
            raise ValueError("blocked preview target")


def safe_preview_image_url(source_url: str, candidate_url: str, title: str, accent_color: str) -> str:
    if not candidate_url:
        return placeholder_thumbnail(title, accent_color)
    resolved = urljoin(source_url, candidate_url)
    try:
        validate_preview_target(resolved)
    except ValueError:
        return placeholder_thumbnail(title, accent_color)
    return resolved


class PreviewRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        validate_preview_target(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


PREVIEW_OPENER = build_opener(PreviewRedirectHandler)


def extract_preview_metadata(target_url: str, accent_color: str) -> Dict[str, Any]:
    try:
        validate_preview_target(target_url)
    except ValueError:
        return {
            "found": False,
            "title": "",
            "imageUrl": "",
            "resolvedUrl": target_url,
            "sourceType": "unresolved",
            "message": "링크가 확인되지 않습니다.",
        }

    request = Request(target_url, headers=PREVIEW_HEADERS)
    final_url = target_url
    try:
        with PREVIEW_OPENER.open(request, timeout=PREVIEW_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            validate_preview_target(final_url)
            content_type = response.headers.get_content_type()
            if content_type.startswith("image/"):
                hostname = urlparse(final_url).netloc or "링크 미리보기"
                return {
                    "found": True,
                    "title": hostname,
                    "imageUrl": final_url,
                    "resolvedUrl": final_url,
                    "sourceType": "image",
                    "message": "입력한 링크를 확인했습니다.",
                }

            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(512_000)
    except (HTTPError, URLError, TimeoutError, ValueError, socket.gaierror):
        return {
            "found": False,
            "title": "",
            "imageUrl": "",
            "resolvedUrl": target_url,
            "sourceType": "unresolved",
            "message": "링크가 확인되지 않습니다.",
        }

    html = raw.decode(charset, errors="replace")
    parser = PreviewHTMLParser()
    parser.feed(html)
    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or parser.title
        or urlparse(target_url).netloc
        or "링크 미리보기"
    ).strip()
    image = (
        parser.meta.get("og:image")
        or parser.meta.get("twitter:image")
        or parser.meta.get("twitter:image:src")
        or (parser.icons[0] if parser.icons else "")
    )
    resolved_image = safe_preview_image_url(final_url or target_url, image, title, accent_color)

    return {
        "found": True,
        "title": title,
        "imageUrl": resolved_image,
        "resolvedUrl": final_url,
        "sourceType": "html",
        "message": "입력한 링크를 확인했습니다.",
    }


def bool_to_int(value: Any) -> int:
    return 1 if bool(value) else 0


def safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def normalize_api_candidates(raw_api_url: str) -> List[str]:
    candidate = raw_api_url.strip()
    if not candidate:
        return []
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    candidate = candidate.rstrip("/")
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return []

    candidates: List[str] = []
    path = parsed.path.rstrip("/")
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if path.endswith("/api/v2"):
        candidates.append(candidate)
    elif path.endswith("/api"):
        candidates.extend([f"{candidate}/v2", candidate])
    elif not path or path == "/":
        candidates.extend([f"{origin}/api/v2", f"{origin}/api", candidate])
    else:
        candidates.extend([candidate, f"{candidate}/v2"])

    deduped: List[str] = []
    for item in candidates:
        normalized = item.rstrip("/")
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def normalize_mkt24_candidates(raw_api_url: str) -> List[str]:
    candidate = raw_api_url.strip()
    if not candidate:
        return []
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    candidate = candidate.rstrip("/")
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return []

    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")
    candidates: List[str] = []

    if path.endswith("/products/sns"):
        candidates.append(candidate)
    elif path.endswith("/products"):
        candidates.append(f"{candidate}/sns")
    elif path.endswith("/v3"):
        candidates.append(f"{candidate}/products/sns")
    elif not path or path == "/":
        candidates.extend([f"{origin}/v3/products/sns", f"{origin}/products/sns"])
    else:
        candidates.extend([candidate, f"{candidate}/products/sns", f"{origin}/v3/products/sns"])

    deduped: List[str] = []
    for item in candidates:
        normalized = item.rstrip("/")
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def normalize_supplier_api_candidates(integration_type: str, raw_api_url: str) -> List[str]:
    normalized_type = normalize_supplier_integration_type(integration_type)
    if normalized_type == SUPPLIER_INTEGRATION_MKT24:
        return normalize_mkt24_candidates(raw_api_url)
    return normalize_api_candidates(raw_api_url)


def normalize_supplier_services_payload(integration_type: str, payload: Any) -> List[Dict[str, Any]]:
    normalized_type = normalize_supplier_integration_type(integration_type)
    if normalized_type == SUPPLIER_INTEGRATION_MKT24:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise SupplierApiError("서비스 목록 형식이 올바르지 않습니다.")
        services: List[Dict[str, Any]] = []
        for platform_key, items in data.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                normalized_item = dict(item)
                normalized_item["_platformKey"] = str(platform_key or "").strip().lower()
                services.append(normalized_item)
        return services

    if not isinstance(payload, list):
        raise SupplierApiError("서비스 목록 형식이 올바르지 않습니다.")
    return [item for item in payload if isinstance(item, dict)]


def supplier_service_record(integration_type: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalized_type = normalize_supplier_integration_type(integration_type)
    if normalized_type == SUPPLIER_INTEGRATION_MKT24:
        external_service_id = str(item.get("productUuid") or "").strip()
        if not external_service_id:
            return None
        platform_key = str(item.get("_platformKey") or "").strip().lower()
        return {
            "externalServiceId": external_service_id,
            "name": str(item.get("fullName") or item.get("menuName") or item.get("cardName") or external_service_id).strip(),
            "category": supplier_platform_label(platform_key),
            "type": str(item.get("productTypeName") or item.get("menuName") or "").strip(),
            "rate": safe_float(item.get("normalPrice"), 0.0),
            "minAmount": 0,
            "maxAmount": 0,
            "dripfeed": False,
            "refill": False,
            "cancel": False,
            "rawJson": as_json(item),
        }

    external_service_id = str(item.get("service") or item.get("id") or "").strip()
    if not external_service_id:
        return None
    return {
        "externalServiceId": external_service_id,
        "name": str(item.get("name") or f"서비스 {external_service_id}").strip(),
        "category": str(item.get("category") or "").strip(),
        "type": str(item.get("type") or "").strip(),
        "rate": safe_float(item.get("rate"), 0.0),
        "minAmount": int(float(item.get("min") or 0) or 0),
        "maxAmount": int(float(item.get("max") or 0) or 0),
        "dripfeed": bool(item.get("dripfeed")),
        "refill": bool(item.get("refill")),
        "cancel": bool(item.get("cancel")),
        "rawJson": as_json(item),
    }


def supplier_target_placeholder(platform_key: str, target_kind: str) -> str:
    platform = str(platform_key or "").strip().lower()
    if target_kind == "account":
        placeholders = {
            "instagram": "예: instamart_official",
            "youtube": "예: @instamart 또는 채널 URL",
            "facebook": "예: facebook 페이지 URL 또는 page id",
            "threads": "예: instamart",
            "naver": "예: blog.naver.com/yourid 또는 플레이스 링크",
            "tiktok": "예: @instamart",
        }
        return placeholders.get(platform, "예: account_id 또는 채널 주소")
    placeholders = {
        "instagram": "https://www.instagram.com/p/...",
        "youtube": "https://www.youtube.com/watch?v=...",
        "facebook": "https://www.facebook.com/...",
        "threads": "https://www.threads.net/@...",
        "naver": "https://blog.naver.com/... 또는 플레이스 링크",
        "tiktok": "https://www.tiktok.com/@.../video/...",
    }
    return placeholders.get(platform, "https://example.com/post/...")


def supplier_target_label(platform_key: str, target_kind: str) -> str:
    platform_label = supplier_platform_label(platform_key)
    if target_kind == "account":
        return f"{platform_label} 계정/채널" if platform_label else "계정/채널"
    if target_kind == "keyword_url":
        return "랜딩 URL"
    return f"{platform_label} 링크" if platform_label else "링크"


def infer_supplier_platform_key(category: str, raw_payload: Dict[str, Any]) -> str:
    raw_key = str(raw_payload.get("_platformKey") or "").strip().lower()
    if raw_key:
        return raw_key
    lowered = str(category or "").strip().lower()
    for key in SUPPLIER_PLATFORM_LABELS:
        if key in lowered:
            return key
    if "인스타" in category:
        return "instagram"
    if "유튜브" in category:
        return "youtube"
    if "페이스북" in category:
        return "facebook"
    if "스레드" in category:
        return "threads"
    if "네이버" in category or "n포털" in category:
        return "naver"
    return ""


def infer_supplier_target_kind(service_name: str, service_type: str, category: str) -> str:
    text = " ".join(part for part in (service_name, service_type, category) if part).lower()
    if any(keyword in text for keyword in ("seo", "traffic", "트래픽", "유입", "검색", "키워드")):
        return "keyword_url"
    if any(keyword in text for keyword in ("팔로워", "구독자", "이웃", "계정관리", "프로필", "page like", "페이지 좋아요", "팬가입", "즐겨찾기")):
        return "account"
    return "url"


def infer_supplier_package_like(service_name: str, service_type: str) -> bool:
    text = " ".join(part for part in (service_name, service_type) if part).lower()
    return any(keyword in text for keyword in ("package", "패키지", "계정관리", "주간", "월간", "30일", "60일", "90일", "유지"))


def infer_supplier_advanced_fields(service: Dict[str, Any], target_kind: str) -> List[str]:
    text = " ".join(
        part for part in (str(service.get("name") or ""), str(service.get("type") or ""), str(service.get("category") or "")) if part
    ).lower()
    advanced: List[str] = []

    if bool(service.get("dripfeed")):
        advanced.extend(["runs", "interval"])
    if "subscription" in text or "구독형" in text:
        advanced.extend(["min", "max", "delay", "expiry"])
    if any(keyword in text for keyword in ("custom comment", "custom comments", "커스텀 댓글", "이모지 댓글")):
        advanced.append("comments")
    if any(keyword in text for keyword in ("poll", "투표")):
        advanced.append("answerNumber")
    if target_kind == "keyword_url":
        advanced.extend(["country", "device", "typeOfTraffic"])

    normalized: List[str] = []
    for key in advanced:
        if key in ADVANCED_ORDER_FIELD_SPECS and key not in normalized:
            normalized.append(key)
    return normalized


def supplier_example_value(field_key: str) -> Any:
    examples = {
        "runs": 3,
        "interval": 30,
        "delay": 30,
        "expiry": "12/31/2026",
        "min": 100,
        "max": 110,
        "posts": 0,
        "oldPosts": 5,
        "comments": "첫 번째 댓글\n두 번째 댓글",
        "answerNumber": 1,
        "country": "KR",
        "device": "Mobile",
        "typeOfTraffic": "search",
        "googleKeyword": "강남 필라테스",
    }
    return examples.get(field_key, "")


def supplier_service_request_guide(integration_type: str, service: Dict[str, Any], raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized_type = normalize_supplier_integration_type(integration_type)
    platform_key = infer_supplier_platform_key(str(service.get("category") or ""), raw_payload)
    target_kind = infer_supplier_target_kind(str(service.get("name") or ""), str(service.get("type") or ""), str(service.get("category") or ""))
    package_like = infer_supplier_package_like(str(service.get("name") or ""), str(service.get("type") or ""))
    advanced_field_keys = infer_supplier_advanced_fields(service, target_kind)
    min_amount = int(service.get("minAmount") or 0) or 1
    max_amount = int(service.get("maxAmount") or 0) or max(min_amount, 1000)
    step_amount = 1
    quantity_label = "수량"
    unit_label = "개"

    if target_kind == "keyword_url":
        form_preset = "keyword_url"
        target_label = "랜딩 URL"
    elif package_like and target_kind == "account":
        form_preset = "package"
        target_label = supplier_target_label(platform_key, "account")
    elif package_like and target_kind == "url":
        form_preset = "url_package"
        target_label = supplier_target_label(platform_key, "url")
    elif target_kind == "account":
        form_preset = "account_quantity"
        target_label = supplier_target_label(platform_key, "account")
    else:
        form_preset = "url_quantity"
        target_label = supplier_target_label(platform_key, "url")

    if "조회수" in str(service.get("name") or "") or "조회수" in str(service.get("type") or ""):
        unit_label = "회"
    if target_kind == "keyword_url":
        quantity_label = "유입 수"
        unit_label = "회"

    recommendation = {
        "formPreset": form_preset,
        "targetLabel": target_label,
        "targetPlaceholder": supplier_target_placeholder(platform_key, target_kind if target_kind != "keyword_url" else "url"),
        "quantityLabel": quantity_label,
        "unitLabel": unit_label,
        "priceStrategy": "fixed" if form_preset in {"package", "url_package"} else "unit",
        "minAmount": min_amount,
        "maxAmount": max_amount,
        "stepAmount": step_amount,
        "advancedFieldKeys": advanced_field_keys,
        "advancedFieldLabels": [ADVANCED_ORDER_FIELD_SPECS[key]["label"] for key in advanced_field_keys],
    }

    notes: List[str] = []
    if bool(service.get("dripfeed")):
        notes.append("드립피드형으로 표시되어 반복 횟수와 실행 간격 옵션을 함께 받는 것을 권장합니다.")
    if package_like:
        notes.append("기간형 또는 패키지형으로 보이므로 내부 상품 가격 방식은 고정가를 권장합니다.")
    if "delay" in advanced_field_keys:
        notes.append("지연 시간 옵션이 필요한 구독/예약형 서비스로 추정되어 시작 간격 입력 칸을 함께 두는 것이 좋습니다.")
    if "comments" in advanced_field_keys:
        notes.append("커스텀 댓글형으로 보여 한 줄씩 입력하는 댓글 목록 필드를 함께 받는 것을 권장합니다.")
    if "answerNumber" in advanced_field_keys:
        notes.append("투표형 서비스로 보여 응답 번호 선택 필드를 함께 두는 것이 안전합니다.")
    if any(key in advanced_field_keys for key in ("country", "device", "typeOfTraffic", "googleKeyword")):
        notes.append("트래픽/검색형 서비스로 추정되어 국가, 디바이스, 유입 유형, 키워드 옵션까지 설계하는 편이 좋습니다.")
    if normalized_type == SUPPLIER_INTEGRATION_MKT24:
        notes.append("이 추천은 MKT24 상품 목록 메타데이터 기준 추정값입니다. 실제 발주 API 문서 확인 후 확정하는 것이 안전합니다.")

    example_payload: Dict[str, Any] = {}
    if normalized_type == SUPPLIER_INTEGRATION_CLASSIC:
        example_payload["service"] = str(service.get("externalServiceId") or "")
        if target_kind == "keyword_url":
            example_payload["link"] = supplier_target_placeholder(platform_key, "url").replace("예: ", "")
            example_payload["google_keyword"] = supplier_example_value("googleKeyword")
        elif target_kind == "account":
            example_payload["username"] = "sample_account"
        else:
            example_payload["link"] = supplier_target_placeholder(platform_key, "url")
        if recommendation["priceStrategy"] != "fixed":
            example_payload["quantity"] = min_amount
        for field_key in advanced_field_keys:
            payload_key = {
                "typeOfTraffic": "type_of_traffic",
                "answerNumber": "answer_number",
                "oldPosts": "old_posts",
                "googleKeyword": "google_keyword",
            }.get(field_key, field_key)
            example_payload[payload_key] = supplier_example_value(field_key)
    else:
        if target_kind == "keyword_url":
            example_payload["targetKeyword"] = supplier_example_value("googleKeyword")
            example_payload["targetUrl"] = supplier_target_placeholder(platform_key, "url").replace("예: ", "")
        elif target_kind == "account":
            example_payload["targetValue"] = "sample_account"
        else:
            example_payload["targetUrl"] = supplier_target_placeholder(platform_key, "url")
        if recommendation["priceStrategy"] != "fixed":
            example_payload["orderedCount"] = min_amount
        for field_key in advanced_field_keys:
            example_payload[field_key] = supplier_example_value(field_key)

    return {
        "confidence": "high" if normalized_type == SUPPLIER_INTEGRATION_CLASSIC else "medium",
        "notes": notes,
        "formRecommendation": recommendation,
        "callExampleTitle": "공급사 호출 예시" if normalized_type == SUPPLIER_INTEGRATION_CLASSIC else "추천 입력 예시",
        "callExamplePayload": example_payload,
        "callExampleIsEstimated": normalized_type != SUPPLIER_INTEGRATION_CLASSIC,
    }


class SupplierApiError(Exception):
    pass


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
        self.ssl_context = ssl._create_unverified_context()

    def _request_form(self, payload: Dict[str, Any]) -> Any:
        encoded = urlencode(payload).encode("utf-8")
        request = Request(
            self.api_url,
            data=encoded,
            headers={
                "User-Agent": PREVIEW_HEADERS["User-Agent"],
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json,text/plain,*/*",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=12, context=self.ssl_context) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
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
            "User-Agent": PREVIEW_HEADERS["User-Agent"],
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
            with urlopen(request, timeout=12, context=self.ssl_context) as response:
                raw = response.read().decode("utf-8", errors="replace")
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
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "x-api-key": self.api_key,
                },
            )
        return self.call("services")

    def balance(self) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("잔액 API를 지원하지 않는 공급사 타입입니다.")
        return self.call("balance")

    def order(self, data: Dict[str, Any]) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("이 공급사 타입은 아직 자동 발주 API가 연결되지 않았습니다.")
        return self.call("add", data)

    def status(self, order_id: str) -> Any:
        if self.integration_type == SUPPLIER_INTEGRATION_MKT24:
            raise SupplierApiError("이 공급사 타입은 아직 상태 조회 API가 연결되지 않았습니다.")
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


def service_html(title: str, lead: str, points: List[str], steps: List[str], note: str) -> str:
    parts = [
        f"<p><strong>{title}</strong></p>",
        f"<p>{lead}</p>",
        "<p><strong>추천 포인트</strong></p>",
    ]
    parts.extend(f"<p>• {point}</p>" for point in points)
    parts.append("<p><strong>주문 방법</strong></p>")
    parts.extend(f"<p>{index}. {step}</p>" for index, step in enumerate(steps, start=1))
    parts.append("<p><strong>운영 메모</strong></p>")
    parts.append(f"<p>{note}</p>")
    return "".join(parts)


def build_form_structure(fields: List[Dict[str, Any]]) -> str:
    schema: Dict[str, List[str]] = {}
    template: Dict[str, Dict[str, Any]] = {}

    for field in fields:
        _append_form_field(schema, template, field)

    return as_json({"schema": schema, "template": template})


def _append_form_field(schema: Dict[str, List[str]], template: Dict[str, Dict[str, Any]], field: Dict[str, Any]) -> None:
    name = field["name"]
    kind = field["kind"]
    required = field.get("required", True)

    if kind == "number":
        rules = ["MIN_MAX"] if required else []
        template[name] = {
            "variant": "input",
            "templateOptions": {
                "labelProps": {"label": field["label"]},
                "formProps": {
                    "name": name,
                    "inputType": "number",
                    "placeholder": field.get("placeholder", "0"),
                    "unit": field.get("unit", ""),
                    "validationVariant": "onlyNumber",
                    "min": field.get("min", 1),
                    "max": field.get("max", 100000),
                    "step": field.get("step", 1),
                },
            },
        }
    elif kind == "textarea":
        rules = ["STRING_REQUIRED"] if required else []
        template[name] = {
            "variant": "textarea",
            "templateOptions": {
                "labelProps": {"label": field["label"]},
                "formProps": {
                    "name": name,
                    "placeholder": field.get("placeholder", ""),
                    "rows": field.get("rows", 4),
                },
            },
        }
    elif kind == "select":
        rules = ["STRING_REQUIRED"] if required else []
        template[name] = {
            "variant": "select",
            "templateOptions": {
                "labelProps": {"label": field["label"]},
                "formProps": {
                    "name": name,
                    "options": field.get("options", []),
                },
            },
        }
    else:
        rules = ["STRING_REQUIRED"] if required else []
        template[name] = {
            "variant": "load_input",
            "templateOptions": {
                "type": field.get("inputType", kind),
                "label": field["label"],
                "placeholder": field.get("placeholder", ""),
            },
        }

    schema[name] = rules


def account_quantity_form(target_label: str, target_placeholder: str, quantity_label: str, min_amount: int, max_amount: int, step_amount: int, unit_label: str = "개") -> str:
    return build_form_structure(
        [
            {
                "name": "targetValue",
                "kind": "account",
                "label": target_label,
                "placeholder": target_placeholder,
                "inputType": "account",
            },
            {
                "name": "orderedCount",
                "kind": "number",
                "label": quantity_label,
                "placeholder": "0",
                "unit": unit_label,
                "min": min_amount,
                "max": max_amount,
                "step": step_amount,
            },
            {
                "name": "contactPhone",
                "kind": "phone",
                "label": "연락처",
                "placeholder": "01012345678",
                "required": False,
                "inputType": "tel",
            },
        ]
    )


def url_quantity_form(target_label: str, target_placeholder: str, quantity_label: str, min_amount: int, max_amount: int, step_amount: int, unit_label: str = "개") -> str:
    return build_form_structure(
        [
            {
                "name": "targetUrl",
                "kind": "url",
                "label": target_label,
                "placeholder": target_placeholder,
                "inputType": "url",
            },
            {
                "name": "orderedCount",
                "kind": "number",
                "label": quantity_label,
                "placeholder": "0",
                "unit": unit_label,
                "min": min_amount,
                "max": max_amount,
                "step": step_amount,
            },
            {
                "name": "contactPhone",
                "kind": "phone",
                "label": "연락처",
                "placeholder": "01012345678",
                "required": False,
                "inputType": "tel",
            },
        ]
    )


def keyword_url_form(min_amount: int, max_amount: int, step_amount: int) -> str:
    return build_form_structure(
        [
            {
                "name": "targetKeyword",
                "kind": "text",
                "label": "키워드",
                "placeholder": "예: 강남 필라테스",
            },
            {
                "name": "targetUrl",
                "kind": "url",
                "label": "랜딩 URL",
                "placeholder": "https://example.com",
                "inputType": "url",
            },
            {
                "name": "orderedCount",
                "kind": "number",
                "label": "유입 수",
                "placeholder": "0",
                "unit": "회",
                "min": min_amount,
                "max": max_amount,
                "step": step_amount,
            },
        ]
    )


def package_form(label: str, placeholder: str) -> str:
    return build_form_structure(
        [
            {
                "name": "targetValue",
                "kind": "account",
                "label": label,
                "placeholder": placeholder,
                "inputType": "account",
            },
            {
                "name": "contactPhone",
                "kind": "phone",
                "label": "담당 연락처",
                "placeholder": "01012345678",
                "inputType": "tel",
            },
        ]
    )


def url_package_form(label: str, placeholder: str) -> str:
    return build_form_structure(
        [
            {
                "name": "targetUrl",
                "kind": "url",
                "label": label,
                "placeholder": placeholder,
                "inputType": "url",
            },
            {
                "name": "contactPhone",
                "kind": "phone",
                "label": "담당 연락처",
                "placeholder": "01012345678",
                "inputType": "tel",
            },
        ]
    )


def custom_form() -> str:
    return build_form_structure(
        [
            {
                "name": "targetValue",
                "kind": "text",
                "label": "희망 채널",
                "placeholder": "예: 스레드, 당근마켓, 웹툰/웹소설",
            },
            {
                "name": "contactPhone",
                "kind": "phone",
                "label": "연락처",
                "placeholder": "01012345678",
                "inputType": "tel",
            },
        ]
    )


FORM_PRESETS = {
    "account_quantity": "계정 ID + 수량",
    "url_quantity": "URL + 수량",
    "keyword_url": "키워드 + URL + 수량",
    "package": "계정 ID + 연락처",
    "url_package": "URL + 연락처",
    "custom": "맞춤 문의형",
}
ADVANCED_ORDER_FIELD_SPECS = {
    "runs": {"name": "runs", "kind": "number", "label": "반복 횟수", "placeholder": "2", "min": 1, "max": 100, "step": 1, "unit": "회", "required": False},
    "interval": {"name": "interval", "kind": "number", "label": "실행 간격", "placeholder": "30", "min": 1, "max": 1440, "step": 1, "unit": "분", "required": False},
    "delay": {"name": "delay", "kind": "number", "label": "지연 시간", "placeholder": "30", "min": 0, "max": 43200, "step": 1, "unit": "분", "required": False},
    "expiry": {"name": "expiry", "kind": "text", "label": "종료일", "placeholder": "MM/DD/YYYY", "required": False},
    "min": {"name": "min", "kind": "number", "label": "최소 수량", "placeholder": "100", "min": 1, "max": 1000000, "step": 1, "unit": "개", "required": False},
    "max": {"name": "max", "kind": "number", "label": "최대 수량", "placeholder": "110", "min": 1, "max": 1000000, "step": 1, "unit": "개", "required": False},
    "posts": {"name": "posts", "kind": "number", "label": "게시물 수", "placeholder": "0", "min": 0, "max": 1000, "step": 1, "unit": "개", "required": False},
    "oldPosts": {"name": "oldPosts", "kind": "number", "label": "기존 게시물 수", "placeholder": "5", "min": 0, "max": 1000, "step": 1, "unit": "개", "required": False},
    "comments": {"name": "comments", "kind": "textarea", "label": "댓글 목록", "placeholder": "한 줄에 한 개씩 입력해 주세요.", "rows": 5, "required": False},
    "answerNumber": {"name": "answerNumber", "kind": "number", "label": "투표 답변 번호", "placeholder": "1", "min": 1, "max": 50, "step": 1, "required": False},
    "country": {"name": "country", "kind": "text", "label": "국가 코드", "placeholder": "예: KR, US", "required": False},
    "device": {"name": "device", "kind": "text", "label": "디바이스", "placeholder": "예: Mobile, Desktop", "required": False},
    "typeOfTraffic": {"name": "typeOfTraffic", "kind": "text", "label": "트래픽 타입", "placeholder": "예: 검색 / 광고 / 일반", "required": False},
    "googleKeyword": {"name": "googleKeyword", "kind": "text", "label": "검색 키워드", "placeholder": "예: 강남 필라테스", "required": False},
}
ADVANCED_ORDER_FIELD_ALIASES = {
    "old_posts": "oldPosts",
    "answer_number": "answerNumber",
    "type_of_traffic": "typeOfTraffic",
    "google_keyword": "googleKeyword",
}


def split_lines(raw: str) -> List[str]:
    return [line.strip() for line in str(raw or "").splitlines() if line.strip()]


def field_template_options(form_structure: Dict[str, Any], field_key: str) -> Dict[str, Any]:
    template = form_structure.get("template", {})
    if not isinstance(template, dict):
        return {}
    entry = template.get(field_key, {})
    if not isinstance(entry, dict):
        return {}
    options = entry.get("templateOptions", {})
    return options if isinstance(options, dict) else {}


def normalize_advanced_field_keys(raw: Any) -> List[str]:
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[\s,]+", str(raw or "").strip()) if str(raw or "").strip() else []
    normalized: List[str] = []
    for item in items:
        key = ADVANCED_ORDER_FIELD_ALIASES.get(str(item or "").strip(), str(item or "").strip())
        if key in ADVANCED_ORDER_FIELD_SPECS and key not in normalized:
            normalized.append(key)
    return normalized


def form_advanced_field_keys(form_structure: Dict[str, Any]) -> List[str]:
    template = form_structure.get("template", {})
    if not isinstance(template, dict):
        return []
    return normalize_advanced_field_keys(list(template.keys()))


def infer_form_preset(form_structure: Dict[str, Any]) -> str:
    template = form_structure.get("template", {})
    if not isinstance(template, dict):
        return "package"

    keys = list(template.keys())
    if keys == ["targetKeyword", "targetUrl", "orderedCount"]:
        return "keyword_url"
    if keys == ["targetUrl", "orderedCount", "contactPhone"]:
        return "url_quantity"
    if keys == ["targetUrl", "contactPhone"]:
        return "url_package"
    if keys == ["targetValue", "orderedCount", "contactPhone"]:
        return "account_quantity"
    if keys == ["targetValue", "contactPhone", "requestMemo"] or keys == ["targetValue", "contactPhone"]:
        target_label = str(field_template_options(form_structure, "targetValue").get("label") or "")
        return "custom" if "희망" in target_label else "package"
    if "targetUrl" in keys and "contactPhone" in keys and "orderedCount" not in keys and "targetKeyword" not in keys:
        return "url_package"
    if "targetValue" in keys and "contactPhone" in keys and "orderedCount" not in keys and "targetUrl" not in keys and "targetKeyword" not in keys:
        target_label = str(field_template_options(form_structure, "targetValue").get("label") or "")
        return "custom" if "희망" in target_label else "package"
    if "targetUrl" in keys and "orderedCount" in keys:
        return "url_quantity"
    if "targetValue" in keys and "orderedCount" in keys:
        return "account_quantity"
    return "package"


def admin_form_config(form_structure: Dict[str, Any]) -> Dict[str, Any]:
    preset = infer_form_preset(form_structure)
    target_value_options = field_template_options(form_structure, "targetValue")
    target_url_options = field_template_options(form_structure, "targetUrl")
    ordered_count_options = field_template_options(form_structure, "orderedCount")
    request_memo_options = field_template_options(form_structure, "requestMemo")
    advanced_field_keys = form_advanced_field_keys(form_structure)

    config = {
        "preset": preset,
        "targetLabel": str(target_value_options.get("label") or target_url_options.get("label") or "계정(ID)"),
        "targetPlaceholder": str(target_value_options.get("placeholder") or target_url_options.get("placeholder") or ""),
        "quantityLabel": str(
            ordered_count_options.get("labelProps", {}).get("label")
            or ordered_count_options.get("label")
            or "수량"
        ),
        "unitLabel": str(ordered_count_options.get("formProps", {}).get("unit") or "개"),
        "memoLabel": str(request_memo_options.get("labelProps", {}).get("label") or request_memo_options.get("label") or "운영 메모"),
        "advancedFieldKeys": advanced_field_keys,
        "advancedFieldLabels": [ADVANCED_ORDER_FIELD_SPECS[key]["label"] for key in advanced_field_keys if key in ADVANCED_ORDER_FIELD_SPECS],
    }
    return config


def build_admin_form_structure(payload: Dict[str, Any], existing_form_structure_json: str = "") -> str:
    preset = str(payload.get("formPreset") or "").strip() or "account_quantity"
    target_label = str(payload.get("targetLabel") or "계정(ID)").strip() or "계정(ID)"
    target_placeholder = str(payload.get("targetPlaceholder") or "").strip()
    quantity_label = str(payload.get("quantityLabel") or "수량").strip() or "수량"
    unit_label = str(payload.get("unitLabel") or "개").strip() or "개"
    memo_label = str(payload.get("memoLabel") or "운영 메모").strip() or "운영 메모"
    min_amount = int(float(payload.get("minAmount") or 1) or 1)
    max_amount = int(float(payload.get("maxAmount") or max(min_amount, 1)) or max(min_amount, 1))
    step_amount = int(float(payload.get("stepAmount") or 1) or 1)
    advanced_field_keys = normalize_advanced_field_keys(payload.get("advancedFieldKeys"))

    if preset == "account_quantity":
        form_structure_json = account_quantity_form(target_label, target_placeholder or "예: account_id", quantity_label, min_amount, max_amount, step_amount, unit_label)
    elif preset == "url_quantity":
        form_structure_json = url_quantity_form(target_label, target_placeholder or "https://example.com/post/...", quantity_label, min_amount, max_amount, step_amount, unit_label)
    elif preset == "keyword_url":
        form_structure_json = keyword_url_form(min_amount, max_amount, step_amount)
    elif preset == "package":
        form_structure_json = build_form_structure(
            [
                {
                    "name": "targetValue",
                    "kind": "account",
                    "label": target_label,
                    "placeholder": target_placeholder or "예: pulse24_official",
                    "inputType": "account",
                },
                {
                    "name": "contactPhone",
                    "kind": "phone",
                    "label": "담당 연락처",
                    "placeholder": "01012345678",
                    "inputType": "tel",
                },
            ]
        )
    elif preset == "url_package":
        form_structure_json = url_package_form(target_label, target_placeholder or "https://example.com/post/...")
    elif preset == "custom":
        form_structure_json = custom_form()
    else:
        form_structure_json = existing_form_structure_json or package_form(target_label, target_placeholder or "예: pulse24_official")

    if not advanced_field_keys:
        return form_structure_json

    form_structure = parse_json(form_structure_json, {})
    if not isinstance(form_structure, dict):
        return form_structure_json
    schema = form_structure.get("schema")
    template = form_structure.get("template")
    if not isinstance(schema, dict) or not isinstance(template, dict):
        return form_structure_json

    for field_key in advanced_field_keys:
        field_spec = ADVANCED_ORDER_FIELD_SPECS.get(field_key)
        if field_spec and field_key not in template:
            _append_form_field(schema, template, field_spec)
    return as_json(form_structure)


def make_option(
    *,
    option_id: str,
    category_id: str,
    name: str,
    option_name: str,
    product_code: str,
    price: int,
    min_amount: int,
    max_amount: int,
    step_amount: int,
    form_structure_json: str,
    price_strategy: str = "unit",
    unit_label: str = "개",
    badge: str = "",
    is_discounted: bool = False,
    estimated_turnaround: str = "5분~2시간",
    sort_order: int = 0,
) -> Dict[str, Any]:
    return {
        "id": option_id,
        "category_id": category_id,
        "name": name,
        "menu_name": name,
        "option_name": option_name,
        "product_code": product_code,
        "price": price,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "step_amount": step_amount,
        "option_price_rate": 100 if not is_discounted else 88,
        "price_strategy": price_strategy,
        "unit_label": unit_label,
        "supports_order_options": 1,
        "is_discounted": 1 if is_discounted else 0,
        "product_kind": "normal",
        "is_custom": 0,
        "estimated_turnaround": estimated_turnaround,
        "badge": badge,
        "form_structure_json": form_structure_json,
        "sort_order": sort_order,
    }


def make_category(
    *,
    category_id: str,
    name: str,
    description: str,
    hero_subtitle: str,
    option_label_name: str,
    service_description_html: str,
    products: List[Dict[str, Any]],
    caution: Optional[List[str]] = None,
    refund_notice: Optional[List[str]] = None,
    sort_order: int = 0,
) -> Dict[str, Any]:
    return {
        "id": category_id,
        "name": name,
        "description": description,
        "option_label_name": option_label_name,
        "category_kind": "normal",
        "hero_title": name,
        "hero_subtitle": hero_subtitle,
        "service_description_html": service_description_html,
        "caution_json": as_json(caution or ["비공개 계정 또는 잘못된 URL 입력 시 작업이 지연될 수 있어요."]),
        "refund_notice_json": as_json(refund_notice or ["작업이 시작된 이후에는 취소 및 환불이 제한될 수 있어요."]),
        "sort_order": sort_order,
        "products": products,
    }


def catalog_blueprints() -> List[Dict[str, Any]]:
    default_caution = [
        "비공개 전환, 삭제, URL 변경이 발생하면 진행이 지연될 수 있어요.",
        "서비스별 특성에 따라 작업 시작 시간이 조금 달라질 수 있어요.",
    ]
    default_refund = [
        "작업이 시작된 이후에는 주문 취소가 제한될 수 있어요.",
        "입력 정보 오류로 인한 실패는 일부 환불 또는 재진행으로 안내드려요.",
    ]

    platforms: List[Dict[str, Any]] = [
        {
            "id": "pf_popular",
            "slug": "popular",
            "display_name": "인기 패키지",
            "description": "처음 시작할 때 가장 많이 선택하는 추천 조합",
            "icon": "★",
            "accent_color": "#ffb84d",
            "groups": [
                {
                    "id": "grp_popular_bundle",
                    "name": "브랜딩 패키지",
                    "description": "단기 성과와 계정 정리를 한 번에 잡는 패키지",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_branding_standard",
                            name="인스타 브랜딩 패키지 - 스탠다드",
                            description="신규 계정이 첫 성과를 만들기 좋은 실속형 패키지",
                            hero_subtitle="계정 세팅, 반응 확보, 첫 유입을 한 번에 진행합니다.",
                            option_label_name="운영 기간",
                            service_description_html=service_html(
                                "인스타 브랜딩 패키지 - 스탠다드",
                                "초기 계정에 필요한 핵심 작업만 모아 빠르게 첫 성과를 만드는 패키지입니다.",
                                [
                                    "프로필 정리와 첫 게시물 반응 확보를 함께 진행해요.",
                                    "브랜드 계정이 너무 인위적으로 보이지 않도록 완만한 속도로 운영해요.",
                                    "운영 기간을 늘릴수록 유입 유지력이 좋아져요.",
                                ],
                                [
                                    "운영할 계정 ID를 입력해 주세요.",
                                    "원하시는 운영 기간을 선택해 주세요.",
                                    "필요하면 메모에 업종과 톤을 함께 적어 주세요.",
                                ],
                                "브랜딩이 필요한 초기 계정, 신규 제품 런칭, 리뉴얼 계정에 적합합니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_branding_standard_30",
                                    category_id="cat_branding_standard",
                                    name="인스타 브랜딩 패키지 - 스탠다드",
                                    option_name="30일",
                                    product_code="instagram-branding-standard",
                                    price=89000,
                                    min_amount=1,
                                    max_amount=1,
                                    step_amount=1,
                                    price_strategy="fixed",
                                    unit_label="패키지",
                                    badge="추천",
                                    form_structure_json=package_form("운영 계정(ID)", "예: pulse24_official"),
                                    estimated_turnaround="담당자 확인 후 당일 시작",
                                ),
                                make_option(
                                    option_id="prd_branding_standard_60",
                                    category_id="cat_branding_standard",
                                    name="인스타 브랜딩 패키지 - 스탠다드",
                                    option_name="60일",
                                    product_code="instagram-branding-standard",
                                    price=159000,
                                    min_amount=1,
                                    max_amount=1,
                                    step_amount=1,
                                    price_strategy="fixed",
                                    unit_label="패키지",
                                    badge="할인",
                                    is_discounted=True,
                                    form_structure_json=package_form("운영 계정(ID)", "예: pulse24_official"),
                                    estimated_turnaround="담당자 확인 후 당일 시작",
                                    sort_order=1,
                                ),
                                make_option(
                                    option_id="prd_branding_standard_90",
                                    category_id="cat_branding_standard",
                                    name="인스타 브랜딩 패키지 - 스탠다드",
                                    option_name="90일",
                                    product_code="instagram-branding-standard",
                                    price=219000,
                                    min_amount=1,
                                    max_amount=1,
                                    step_amount=1,
                                    price_strategy="fixed",
                                    unit_label="패키지",
                                    badge="베스트",
                                    is_discounted=True,
                                    form_structure_json=package_form("운영 계정(ID)", "예: pulse24_official"),
                                    estimated_turnaround="담당자 확인 후 당일 시작",
                                    sort_order=2,
                                ),
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        ),
                        make_category(
                            category_id="cat_shortform_launch",
                            name="숏폼 런칭 패키지",
                            description="릴스와 쇼츠 공개 직후 체감 성과를 빠르게 만듭니다.",
                            hero_subtitle="콘텐츠 공개 초반 반응을 집중 강화해 다음 노출로 이어지게 합니다.",
                            option_label_name="패키지 옵션",
                            service_description_html=service_html(
                                "숏폼 런칭 패키지",
                                "신규 릴스·쇼츠가 업로드된 직후 필요한 조회, 좋아요, 저장 흐름을 빠르게 만드는 조합형 패키지입니다.",
                                [
                                    "영상 공개 초반 노출 가속 구간을 활용하기 좋습니다.",
                                    "조회수와 반응을 균형 있게 구성해 과도한 왜곡을 줄였습니다.",
                                    "숏폼 퍼포먼스 테스트용으로도 적합합니다.",
                                ],
                                [
                                    "영상 URL을 입력해 주세요.",
                                    "원하시는 패키지 강도를 선택해 주세요.",
                                    "같이 확인할 목표 지표가 있으면 메모에 적어 주세요.",
                                ],
                                "광고용 숏폼, 브랜드 쇼츠, 이벤트 티저 운영에 잘 맞습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_shortform_launch_start",
                                    category_id="cat_shortform_launch",
                                    name="숏폼 런칭 패키지",
                                    option_name="스타터",
                                    product_code="shortform-launch",
                                    price=49000,
                                    min_amount=1,
                                    max_amount=1,
                                    step_amount=1,
                                    price_strategy="fixed",
                                    unit_label="패키지",
                                    badge="입문",
                                    form_structure_json=build_form_structure(
                                        [
                                            {
                                                "name": "targetUrl",
                                                "kind": "url",
                                                "label": "영상 URL",
                                                "placeholder": "https://instagram.com/reel/...",
                                                "inputType": "url",
                                            },
                                            {
                                                "name": "requestMemo",
                                                "kind": "textarea",
                                                "label": "운영 메모",
                                                "placeholder": "예: 출시일 전날 18시에 집중 노출 원함",
                                                "rows": 4,
                                                "required": False,
                                            },
                                        ]
                                    ),
                                    estimated_turnaround="10분 이내 시작",
                                ),
                                make_option(
                                    option_id="prd_shortform_launch_boost",
                                    category_id="cat_shortform_launch",
                                    name="숏폼 런칭 패키지",
                                    option_name="부스트",
                                    product_code="shortform-launch",
                                    price=79000,
                                    min_amount=1,
                                    max_amount=1,
                                    step_amount=1,
                                    price_strategy="fixed",
                                    unit_label="패키지",
                                    badge="인기",
                                    is_discounted=True,
                                    form_structure_json=build_form_structure(
                                        [
                                            {
                                                "name": "targetUrl",
                                                "kind": "url",
                                                "label": "영상 URL",
                                                "placeholder": "https://youtube.com/shorts/...",
                                                "inputType": "url",
                                            },
                                            {
                                                "name": "contactPhone",
                                                "kind": "phone",
                                                "label": "알림 연락처",
                                                "placeholder": "01012345678",
                                                "required": False,
                                                "inputType": "tel",
                                            },
                                        ]
                                    ),
                                    estimated_turnaround="10분 이내 시작",
                                    sort_order=1,
                                ),
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                            sort_order=1,
                        ),
                    ],
                }
            ],
        },
        {
            "id": "pf_shortform",
            "slug": "shortform",
            "display_name": "숏폼 마케팅",
            "description": "릴스, 쇼츠, 클립 중심 콘텐츠 노출 강화",
            "icon": "▶",
            "accent_color": "#ff6b6b",
            "groups": [
                {
                    "id": "grp_shortform_views",
                    "name": "릴스/쇼츠 부스팅",
                    "description": "조회와 반응을 동시에 끌어올리는 숏폼 성장군",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_reels_views",
                            name="릴스 조회수 부스팅",
                            description="릴스 초반 도달량을 빠르게 확보하는 조회수 상품",
                            hero_subtitle="공개 직후 도달 구간을 밀어 올려 추가 노출 가능성을 만듭니다.",
                            option_label_name="노출 속도",
                            service_description_html=service_html(
                                "릴스 조회수 부스팅",
                                "브랜드 릴스, 이벤트 릴스, 제품 소개 영상에 가장 많이 사용되는 대표 숏폼 노출 상품입니다.",
                                [
                                    "업로드 직후 성과를 만들고 싶을 때 적합합니다.",
                                    "광고 소재 테스트 시 초기 반응 체크용으로 활용할 수 있습니다.",
                                    "속도 옵션을 선택해 노출 페이스를 조절할 수 있습니다.",
                                ],
                                [
                                    "릴스 URL을 입력해 주세요.",
                                    "원하시는 속도 옵션을 선택해 주세요.",
                                    "수량을 입력하면 총 금액이 자동 계산됩니다.",
                                ],
                                "공개 직후 3시간 내 유입이 중요한 콘텐츠에 특히 잘 맞습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_reels_views_standard",
                                    category_id="cat_reels_views",
                                    name="릴스 조회수 부스팅",
                                    option_name="스탠다드",
                                    product_code="reels-views",
                                    price=12,
                                    min_amount=1000,
                                    max_amount=300000,
                                    step_amount=100,
                                    unit_label="회",
                                    badge="실시간",
                                    form_structure_json=url_quantity_form(
                                        "릴스 URL",
                                        "https://instagram.com/reel/...",
                                        "조회 수량",
                                        1000,
                                        300000,
                                        100,
                                        "회",
                                    ),
                                    estimated_turnaround="3분 이내 시작",
                                ),
                                make_option(
                                    option_id="prd_reels_views_fast",
                                    category_id="cat_reels_views",
                                    name="릴스 조회수 부스팅",
                                    option_name="급상승형",
                                    product_code="reels-views",
                                    price=18,
                                    min_amount=1000,
                                    max_amount=300000,
                                    step_amount=100,
                                    unit_label="회",
                                    badge="빠른 시작",
                                    is_discounted=True,
                                    form_structure_json=url_quantity_form(
                                        "릴스 URL",
                                        "https://instagram.com/reel/...",
                                        "조회 수량",
                                        1000,
                                        300000,
                                        100,
                                        "회",
                                    ),
                                    estimated_turnaround="즉시 시작",
                                    sort_order=1,
                                ),
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        ),
                        make_category(
                            category_id="cat_shorts_shares",
                            name="쇼츠 공유 반응",
                            description="공유와 저장 반응으로 영상 확산을 돕는 상품",
                            hero_subtitle="공유 기반 반응을 활용해 영상의 체감 흥미도를 높입니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "쇼츠 공유 반응",
                                "저장·공유 위주 반응을 구성해 영상의 확산 흐름을 보강하는 상품입니다.",
                                [
                                    "브랜드 콘텐츠의 체감 참여도를 올리기에 적합합니다.",
                                    "영상 광고를 유기적으로 보강할 때 사용하기 좋습니다.",
                                    "댓글 없이도 자연스러운 참여 신호를 만들 수 있습니다.",
                                ],
                                [
                                    "쇼츠 URL을 입력해 주세요.",
                                    "수량을 선택한 뒤 주문을 진행해 주세요.",
                                    "필요하면 메모에 캠페인 기간을 적어 주세요.",
                                ],
                                "광고 영상, 제품 설명, 후기형 숏폼에 안정적으로 활용할 수 있습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_shorts_shares_basic",
                                    category_id="cat_shorts_shares",
                                    name="쇼츠 공유 반응",
                                    option_name="기본",
                                    product_code="shorts-share",
                                    price=95,
                                    min_amount=50,
                                    max_amount=20000,
                                    step_amount=10,
                                    unit_label="건",
                                    badge="확산",
                                    form_structure_json=url_quantity_form(
                                        "쇼츠 URL",
                                        "https://youtube.com/shorts/...",
                                        "공유 수량",
                                        50,
                                        20000,
                                        10,
                                        "건",
                                    ),
                                    estimated_turnaround="15분 이내 시작",
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                            sort_order=1,
                        ),
                    ],
                }
            ],
        },
        {
            "id": "pf_instagram",
            "slug": "instagram",
            "display_name": "인스타그램",
            "description": "팔로워, 좋아요, 프로필 방문, 도달 패키지",
            "icon": "IG",
            "accent_color": "#ff4dc4",
            "groups": [
                {
                    "id": "grp_instagram_growth",
                    "name": "계정 성장",
                    "description": "가장 많이 주문하는 인스타 기본 상품군",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_instagram_korean_followers",
                            name="인스타그램 한국인 팔로워",
                            description="실제 활동 패턴을 고려한 한국인 기반 팔로워 증대",
                            hero_subtitle="브랜드 계정의 신뢰도를 높일 때 많이 선택하는 대표 상품입니다.",
                            option_label_name="진행 옵션",
                            service_description_html=service_html(
                                "인스타그램 한국인 팔로워",
                                "브랜드 계정, 로컬 비즈니스, 크리에이터 계정이 가장 많이 선택하는 기본 성장 상품입니다.",
                                [
                                    "과도한 급증보다 안정적인 성장 흐름을 우선합니다.",
                                    "계정 공개 상태를 유지하면 더욱 안정적으로 진행됩니다.",
                                    "신규 런칭 계정의 사회적 신뢰도를 만드는 데 효과적입니다.",
                                ],
                                [
                                    "인스타 계정 ID를 입력해 주세요.",
                                    "옵션과 수량을 선택해 주세요.",
                                    "주문 후에는 계정명을 변경하지 않는 것을 권장합니다.",
                                ],
                                "브랜드 계정 초반 세팅, 운영 계정 신뢰도 보강, 광고용 계정 정리에 적합합니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_instagram_korean_followers_standard",
                                    category_id="cat_instagram_korean_followers",
                                    name="인스타그램 한국인 팔로워",
                                    option_name="스탠다드",
                                    product_code="instagram-korean-follower",
                                    price=120,
                                    min_amount=10,
                                    max_amount=50000,
                                    step_amount=1,
                                    badge="대표",
                                    form_structure_json=account_quantity_form("계정(ID)", "예: pulse24_official", "팔로워 수", 10, 50000, 1),
                                ),
                                make_option(
                                    option_id="prd_instagram_korean_followers_safe",
                                    category_id="cat_instagram_korean_followers",
                                    name="인스타그램 한국인 팔로워",
                                    option_name="안정형",
                                    product_code="instagram-korean-follower",
                                    price=150,
                                    min_amount=10,
                                    max_amount=30000,
                                    step_amount=1,
                                    badge="안전 운영",
                                    is_discounted=True,
                                    form_structure_json=account_quantity_form("계정(ID)", "예: pulse24_official", "팔로워 수", 10, 30000, 1),
                                    estimated_turnaround="30분 이내 시작",
                                    sort_order=1,
                                ),
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        ),
                        make_category(
                            category_id="cat_instagram_korean_likes",
                            name="인스타그램 한국인 좋아요",
                            description="피드와 릴스의 체감 반응을 높이는 좋아요 상품",
                            hero_subtitle="브랜드 게시물 신뢰도를 높이고 게시물 첫인상을 개선합니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "인스타그램 한국인 좋아요",
                                "게시물·릴스 모두 사용 가능한 좋아요 상품으로 반응 수치를 안정적으로 보강합니다.",
                                [
                                    "광고 집행 전후 게시물 보강용으로 자주 쓰입니다.",
                                    "브랜드 캠페인의 첫 공개 게시물에 적합합니다.",
                                    "릴스와 피드 모두 URL만 있으면 주문할 수 있습니다.",
                                ],
                                [
                                    "게시물 또는 릴스 URL을 입력해 주세요.",
                                    "좋아요 수량을 설정해 주세요.",
                                    "필요하면 메모에 목표 업로드 시간을 남겨 주세요.",
                                ],
                                "초기 게시물 체감 반응을 빠르게 만들고 싶을 때 유용합니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_instagram_korean_likes_basic",
                                    category_id="cat_instagram_korean_likes",
                                    name="인스타그램 한국인 좋아요",
                                    option_name="기본",
                                    product_code="instagram-korean-like",
                                    price=35,
                                    min_amount=50,
                                    max_amount=100000,
                                    step_amount=10,
                                    unit_label="개",
                                    badge="인기",
                                    form_structure_json=url_quantity_form(
                                        "게시물 URL",
                                        "https://instagram.com/p/...",
                                        "좋아요 수량",
                                        50,
                                        100000,
                                        10,
                                    ),
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                            sort_order=1,
                        ),
                        make_category(
                            category_id="cat_instagram_profile_visit",
                            name="인스타그램 프로필 방문",
                            description="프로필 유입을 늘려 계정 탐색과 전환을 돕는 상품",
                            hero_subtitle="링크 클릭, DM, 팔로우 전환을 기대하는 계정에 적합합니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "인스타그램 프로필 방문",
                                "브랜드 계정, 쇼핑몰 계정, 예약형 계정에 많이 사용되는 프로필 유입 상품입니다.",
                                [
                                    "프로필 링크 클릭과 소개 영역 확인 유도를 돕습니다.",
                                    "광고 이후 프로필 전환율 체감 개선에 활용됩니다.",
                                    "이벤트 페이지, 예약 페이지, 링크인바이오 계정에 적합합니다.",
                                ],
                                [
                                    "인스타 계정 ID를 입력해 주세요.",
                                    "원하는 방문 수량을 선택해 주세요.",
                                    "랜딩 목적이 있으면 메모로 남겨 주세요.",
                                ],
                                "프로필 유입이 중요한 예약/상담형 계정에 특히 잘 맞습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_instagram_profile_visit_basic",
                                    category_id="cat_instagram_profile_visit",
                                    name="인스타그램 프로필 방문",
                                    option_name="기본",
                                    product_code="instagram-profile-visit",
                                    price=42,
                                    min_amount=100,
                                    max_amount=100000,
                                    step_amount=10,
                                    unit_label="회",
                                    badge="전환형",
                                    form_structure_json=account_quantity_form("계정(ID)", "예: pulse24_official", "방문 수량", 100, 100000, 10, "회"),
                                    estimated_turnaround="5분 이내 시작",
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                            sort_order=2,
                        ),
                    ],
                }
            ],
        },
        {
            "id": "pf_youtube",
            "slug": "youtube",
            "display_name": "유튜브",
            "description": "조회수, 구독자, 좋아요, 댓글로 채널 성장 보강",
            "icon": "YT",
            "accent_color": "#ff4646",
            "groups": [
                {
                    "id": "grp_youtube_growth",
                    "name": "영상 성장",
                    "description": "영상 퍼포먼스와 채널 신뢰도를 동시에 강화",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_youtube_views",
                            name="유튜브 조회수",
                            description="영상 노출 체감을 빠르게 만드는 기본 조회수 상품",
                            hero_subtitle="브랜드 필름, 인터뷰, 후기 영상 공개 직후 활용도가 높습니다.",
                            option_label_name="속도 옵션",
                            service_description_html=service_html(
                                "유튜브 조회수",
                                "유튜브 검색·추천 노출 체감을 높이기 위해 가장 많이 선택하는 대표 상품입니다.",
                                [
                                    "영상 공개 초반 성과 지표 확보에 유리합니다.",
                                    "광고 집행 전후의 체감 수치를 맞추는 데에도 자주 사용됩니다.",
                                    "채널 성장 실험용으로도 활용도가 높습니다.",
                                ],
                                [
                                    "유튜브 영상 URL을 입력해 주세요.",
                                    "옵션과 조회 수량을 선택해 주세요.",
                                    "콘텐츠 일정이 있으면 메모에 적어 주세요.",
                                ],
                                "브랜드 영상, 숏폼 티저, 캠페인 영상에 폭넓게 활용할 수 있습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_youtube_views_standard",
                                    category_id="cat_youtube_views",
                                    name="유튜브 조회수",
                                    option_name="스탠다드",
                                    product_code="youtube-views",
                                    price=9,
                                    min_amount=1000,
                                    max_amount=500000,
                                    step_amount=100,
                                    unit_label="회",
                                    badge="실속",
                                    form_structure_json=url_quantity_form(
                                        "영상 URL",
                                        "https://youtube.com/watch?v=...",
                                        "조회 수량",
                                        1000,
                                        500000,
                                        100,
                                        "회",
                                    ),
                                    estimated_turnaround="즉시 시작",
                                ),
                                make_option(
                                    option_id="prd_youtube_views_search",
                                    category_id="cat_youtube_views",
                                    name="유튜브 조회수",
                                    option_name="검색 유입형",
                                    product_code="youtube-views",
                                    price=15,
                                    min_amount=1000,
                                    max_amount=300000,
                                    step_amount=100,
                                    unit_label="회",
                                    badge="추천",
                                    is_discounted=True,
                                    form_structure_json=url_quantity_form(
                                        "영상 URL",
                                        "https://youtube.com/watch?v=...",
                                        "조회 수량",
                                        1000,
                                        300000,
                                        100,
                                        "회",
                                    ),
                                    estimated_turnaround="30분 이내 시작",
                                    sort_order=1,
                                ),
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        ),
                        make_category(
                            category_id="cat_youtube_subscribers",
                            name="유튜브 구독자",
                            description="채널 신뢰도와 구독 기반을 함께 보강하는 성장 상품",
                            hero_subtitle="채널 개설 초기, 캠페인 시작 시점에 가장 많이 사용됩니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "유튜브 구독자",
                                "채널 신뢰도 형성에 필요한 구독 기반을 만들어 주는 대표 상품입니다.",
                                [
                                    "신규 채널의 첫 인상을 안정적으로 정리할 수 있습니다.",
                                    "브랜드 채널, 병원/학원 채널, 쇼핑몰 채널에 적합합니다.",
                                    "너무 빠른 급증을 피하고 싶은 경우 안정형 옵션을 추천합니다.",
                                ],
                                [
                                    "유튜브 채널 URL 또는 채널 핸들을 입력해 주세요.",
                                    "원하시는 수량을 입력해 주세요.",
                                    "비공개 설정은 해제한 상태로 유지해 주세요.",
                                ],
                                "브랜드 채널 개설 초반 신뢰도 보강에 활용도가 높습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_youtube_subscribers_basic",
                                    category_id="cat_youtube_subscribers",
                                    name="유튜브 구독자",
                                    option_name="기본",
                                    product_code="youtube-subscribers",
                                    price=185,
                                    min_amount=50,
                                    max_amount=50000,
                                    step_amount=1,
                                    unit_label="명",
                                    badge="채널 성장",
                                    form_structure_json=account_quantity_form("채널 주소", "예: youtube.com/@pulse24", "구독자 수", 50, 50000, 1, "명"),
                                    estimated_turnaround="20분 이내 시작",
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                            sort_order=1,
                        ),
                    ],
                }
            ],
        },
        {
            "id": "pf_nportal",
            "slug": "nportal",
            "display_name": "N포털",
            "description": "블로그, 플레이스, 지식인 노출 중심 포털 성장",
            "icon": "N",
            "accent_color": "#03c75a",
            "groups": [
                {
                    "id": "grp_nportal_search",
                    "name": "포털 노출",
                    "description": "검색 기반 유입과 리뷰 신뢰도를 동시에 보강",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_blog_inflow",
                            name="블로그 키워드 유입",
                            description="포털 검색 유입과 체류 흐름을 함께 고려한 트래픽 상품",
                            hero_subtitle="키워드 검색 기반 랜딩 유입을 늘리고 싶을 때 적합합니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "블로그 키워드 유입",
                                "검색 키워드와 타깃 랜딩을 함께 설정해 유입 흐름을 관리하는 검색형 트래픽 상품입니다.",
                                [
                                    "검색 키워드 기반 유입이 필요한 블로그·홈페이지에 적합합니다.",
                                    "광고 클릭 이후 체감 체류를 보강할 때도 자주 사용됩니다.",
                                    "브랜드 키워드 테스트나 블로그 체류 실험에도 활용할 수 있습니다.",
                                ],
                                [
                                    "목표 키워드를 입력해 주세요.",
                                    "랜딩 URL을 입력해 주세요.",
                                    "원하는 유입 수량을 선택해 주세요.",
                                ],
                                "검색형 트래픽이 필요한 블로그 홍보와 검색 광고 보강에 적합합니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_blog_inflow_basic",
                                    category_id="cat_blog_inflow",
                                    name="블로그 키워드 유입",
                                    option_name="기본",
                                    product_code="blog-keyword-inflow",
                                    price=55,
                                    min_amount=100,
                                    max_amount=50000,
                                    step_amount=10,
                                    unit_label="회",
                                    badge="검색형",
                                    form_structure_json=keyword_url_form(100, 50000, 10),
                                    estimated_turnaround="30분 이내 시작",
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        ),
                        make_category(
                            category_id="cat_place_reviews",
                            name="플레이스 리뷰 부스팅",
                            description="매장 플레이스 리뷰와 저장 반응을 함께 강화",
                            hero_subtitle="오프라인 매장과 지역 기반 서비스에 가장 많이 쓰입니다.",
                            option_label_name="상품 옵션",
                            service_description_html=service_html(
                                "플레이스 리뷰 부스팅",
                                "플레이스 신뢰도와 저장/방문 체감을 함께 개선하고 싶을 때 사용하는 로컬 비즈니스 대표 상품입니다.",
                                [
                                    "병원, 카페, 미용, 필라테스, 맛집 매장 운영에 적합합니다.",
                                    "저장·리뷰 흐름을 함께 고려해 매장 관심도를 높입니다.",
                                    "매장 소개 페이지, 지도 검색 유입 보강에 좋습니다.",
                                ],
                                [
                                    "플레이스 URL을 입력해 주세요.",
                                    "수량을 설정해 주세요.",
                                    "운영 메모에 매장 업종을 남겨 주시면 참고합니다.",
                                ],
                                "로컬 키워드 경쟁이 치열한 업종에서 특히 활용도가 높습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_place_reviews_basic",
                                    category_id="cat_place_reviews",
                                    name="플레이스 리뷰 부스팅",
                                    option_name="기본",
                                    product_code="place-review",
                                    price=6900,
                                    min_amount=1,
                                    max_amount=300,
                                    step_amount=1,
                                    unit_label="건",
                                    badge="로컬",
                                    form_structure_json=build_form_structure(
                                        [
                                            {
                                                "name": "targetUrl",
                                                "kind": "url",
                                                "label": "플레이스 URL",
                                                "placeholder": "https://map.naver.com/...",
                                                "inputType": "url",
                                            },
                                            {
                                                "name": "orderedCount",
                                                "kind": "number",
                                                "label": "수량",
                                                "placeholder": "0",
                                                "unit": "건",
                                                "min": 1,
                                                "max": 300,
                                                "step": 1,
                                            },
                                            {
                                                "name": "requestMemo",
                                                "kind": "textarea",
                                                "label": "요청 메모",
                                                "placeholder": "업종, 매장 포인트, 집중 지역 등을 적어 주세요.",
                                                "rows": 4,
                                                "required": False,
                                            },
                                        ]
                                    ),
                                    estimated_turnaround="담당자 확인 후 순차 진행",
                                )
                            ],
                            caution=["상담형 상품으로 진행 방식 확인 후 순차 작업됩니다."],
                            refund_notice=["작업이 시작된 이후에는 환불이 제한될 수 있어요."],
                            sort_order=1,
                        ),
                    ],
                }
            ],
        },
        {
            "id": "pf_tiktok",
            "slug": "tiktok",
            "display_name": "틱톡",
            "description": "틱톡 조회수, 좋아요, 팔로워 기반 성장",
            "icon": "TT",
            "accent_color": "#00d7ff",
            "groups": [
                {
                    "id": "grp_tiktok_growth",
                    "name": "TikTok Growth",
                    "description": "영상 공개 직후 성과를 만들기 좋은 틱톡 기본 라인업",
                    "sort_order": 0,
                    "categories": [
                        make_category(
                            category_id="cat_tiktok_views",
                            name="틱톡 조회수",
                            description="틱톡 영상 도달량을 빠르게 끌어올리는 기본 상품",
                            hero_subtitle="캠페인 영상, 바이럴 시도 콘텐츠, 제품 소개 숏폼에 잘 맞습니다.",
                            option_label_name="진행 옵션",
                            service_description_html=service_html(
                                "틱톡 조회수",
                                "틱톡 영상 공개 초반 지표를 정리하고 싶은 분들이 가장 많이 선택하는 기본 상품입니다.",
                                [
                                    "공개 직후 지표 확보가 필요한 영상에 적합합니다.",
                                    "브랜드 숏폼, 챌린지, 후기형 콘텐츠에도 활용할 수 있습니다.",
                                    "광고 집행과 함께 사용할 경우 체감 퍼포먼스를 보강할 수 있습니다.",
                                ],
                                [
                                    "틱톡 영상 URL을 입력해 주세요.",
                                    "옵션과 수량을 선택해 주세요.",
                                    "업로드 일정이 있으면 메모에 남겨 주세요.",
                                ],
                                "빠른 도달 체감이 필요한 숏폼 운영에 안정적으로 사용할 수 있습니다.",
                            ),
                            products=[
                                make_option(
                                    option_id="prd_tiktok_views_basic",
                                    category_id="cat_tiktok_views",
                                    name="틱톡 조회수",
                                    option_name="기본",
                                    product_code="tiktok-views",
                                    price=8,
                                    min_amount=1000,
                                    max_amount=500000,
                                    step_amount=100,
                                    unit_label="회",
                                    badge="즉시",
                                    form_structure_json=url_quantity_form(
                                        "틱톡 영상 URL",
                                        "https://tiktok.com/@id/video/...",
                                        "조회 수량",
                                        1000,
                                        500000,
                                        100,
                                        "회",
                                    ),
                                )
                            ],
                            caution=default_caution,
                            refund_notice=default_refund,
                        )
                    ],
                }
            ],
        },
    ]

    generic_blueprints = [
        ("facebook", "페이스북", "FB", "#3b82f6", "페이지/게시물 성장", "페이지 참여도와 도달량을 보강하는 상품군", [
            ("cat_facebook_reactions", "페이스북 게시물 반응", "게시물 좋아요와 참여도를 빠르게 만드는 상품", "페이스북 게시물 URL", "https://facebook.com/...", "반응 수량", 50, 50000, 10, "개"),
            ("cat_facebook_page_followers", "페이스북 페이지 팔로워", "페이지 기본 신뢰도를 만드는 팔로워 상품", "페이지 URL", "https://facebook.com/...", "팔로워 수", 50, 30000, 1, "명"),
        ]),
        ("threads", "스레드", "TH", "#111111", "스레드 가속", "실시간 스레드 반응을 빠르게 보강하는 상품군", [
            ("cat_threads_followers", "스레드 팔로워", "스레드 계정 기본 지표를 만드는 팔로워 상품", "스레드 계정", "예: @pulse24", "팔로워 수", 30, 20000, 1, "명"),
            ("cat_threads_likes", "스레드 좋아요", "스레드 게시물 체감 반응을 높이는 상품", "게시물 URL", "https://threads.net/...", "좋아요 수량", 30, 50000, 10, "개"),
        ]),
        ("etc-sns", "기타 SNS", "◎", "#7c3aed", "기타 채널 운영", "다양한 SNS 채널의 기본 성장을 돕는 상품군", [
            ("cat_other_sns_growth", "기타 SNS 성장 패키지", "채널 특성에 맞춰 반응과 유입을 맞춤 보강합니다.", "채널 주소", "예: x.com/pulse24", "수량", 50, 50000, 10, "건"),
        ]),
        ("map", "지도 마케팅", "MAP", "#10b981", "로컬 매장 활성화", "지도 검색과 저장·리뷰 흐름을 강화하는 상품군", [
            ("cat_map_store_saves", "지도 저장/찜", "매장 저장과 찜 반응을 강화하는 상품", "매장 URL", "https://map.kakao.com/...", "저장 수량", 20, 10000, 1, "건"),
        ]),
        ("seo", "SEO트래픽", "SEO", "#0f766e", "검색 유입", "검색 기반 유입과 체류를 설계하는 상품군", [
            ("cat_seo_traffic", "검색형 웹사이트 유입", "키워드 기반 웹사이트 유입을 설계하는 상품", "랜딩 URL", "https://example.com", "유입 수량", 100, 100000, 10, "회"),
        ]),
        ("press", "언론보도", "PR", "#f97316", "브랜드 신뢰도", "기사형 콘텐츠와 보도자료 송출 중심 상품군", [
            ("cat_press_release", "기사형 보도자료 송출", "브랜드 신뢰도 확보용 기사형 송출 상품", "브랜드명", "예: Pulse24", "송출 수량", 1, 30, 1, "건"),
        ]),
        ("design", "디자인 서비스", "DS", "#ec4899", "디자인 제작", "썸네일과 배너, 상세페이지 제작 보조 상품군", [
            ("cat_design_thumbnail", "썸네일/배너 디자인", "콘텐츠 클릭률 개선을 위한 디자인 상품", "요청 채널", "예: 유튜브/상세페이지", "수량", 1, 50, 1, "건"),
        ]),
        ("market", "오픈마켓", "OM", "#f59e0b", "상품 전환 보조", "찜, 리뷰, 상품 유입을 강화하는 상품군", [
            ("cat_market_favorites", "오픈마켓 관심상품/찜", "상품 관심도 신호를 만드는 상품", "상품 URL", "https://smartstore.naver.com/...", "찜 수량", 20, 50000, 1, "건"),
        ]),
        ("carrot", "당근마켓", "DG", "#fb923c", "로컬 거래 활성화", "당근마켓 노출과 관심 반응 보강 상품군", [
            ("cat_carrot_interest", "당근마켓 관심/조회", "상품 노출과 관심 반응을 강화하는 상품", "상품 URL", "https://www.daangn.com/...", "수량", 20, 20000, 1, "건"),
        ]),
        ("shopping-live", "쇼핑라이브", "SL", "#ef4444", "라이브 전환 보조", "라이브 시청자와 채팅 반응을 돕는 상품군", [
            ("cat_shopping_live_viewers", "쇼핑라이브 시청자 반응", "라이브 시작 초반 분위기를 만드는 상품", "방송 URL", "https://shoppinglive.naver.com/...", "수량", 50, 30000, 10, "명"),
        ]),
        ("apps", "어플마케팅", "APP", "#14b8a6", "앱 성장", "앱 설치와 리뷰 보강 중심 상품군", [
            ("cat_app_installs", "앱 설치/리뷰 부스팅", "앱 스토어 전환 보강용 상품", "앱 링크", "https://play.google.com/...", "수량", 50, 50000, 10, "건"),
        ]),
        ("messenger", "메신저앱", "MSG", "#22c55e", "채널 운영", "채널 친구와 메시지 반응을 보강하는 상품군", [
            ("cat_messenger_channel", "메신저 채널 친구", "채널 운영 초기 신뢰도를 만드는 상품", "채널 URL", "https://pf.kakao.com/...", "친구 수", 20, 30000, 1, "명"),
        ]),
        ("hospitality", "숙박/문화/골프", "HG", "#2563eb", "예약/문의 활성화", "리뷰와 문의 중심 상품군", [
            ("cat_hospitality_reviews", "예약/리뷰 문의 보강", "지역 서비스 예약형 업종 전용 상품", "서비스 URL", "https://example.com/reservation", "수량", 1, 500, 1, "건"),
        ]),
        ("community", "커뮤니티", "CM", "#64748b", "커뮤니티 반응", "조회와 추천, 댓글 흐름을 보강하는 상품군", [
            ("cat_community_upvotes", "커뮤니티 조회/추천", "커뮤니티 게시물 기본 반응을 강화하는 상품", "게시물 URL", "https://example.com/post/1", "수량", 20, 100000, 10, "건"),
        ]),
        ("crowdfunding", "크라우드 펀딩", "CF", "#8b5cf6", "프로젝트 유입", "오픈 전 관심도와 프로젝트 유입 보조 상품군", [
            ("cat_crowdfunding_alerts", "펀딩 알림/유입", "펀딩 프로젝트 알림 신청과 유입을 보강하는 상품", "프로젝트 URL", "https://wadiz.kr/...", "수량", 20, 30000, 1, "건"),
        ]),
        ("music", "음원 플랫폼", "MP", "#db2777", "스트리밍 강화", "스트리밍, 좋아요, 플레이리스트 반응 상품군", [
            ("cat_music_streams", "음원 스트리밍/좋아요", "신곡 공개 초반 반응을 만드는 상품", "음원 URL", "https://music.youtube.com/...", "수량", 100, 100000, 10, "회"),
        ]),
        ("tv", "TV채널", "TV", "#4f46e5", "방송 채널 반응", "클립 조회와 구독자 반응을 보강하는 상품군", [
            ("cat_tv_channel_growth", "TV채널 클립 반응", "방송 클립·채널 반응을 강화하는 상품", "클립 URL", "https://example.com/clip/1", "수량", 100, 50000, 10, "회"),
        ]),
        ("webtoon", "웹툰/웹소설", "WT", "#dc2626", "작품 반응 강화", "조회와 댓글로 작품 신뢰도를 보강하는 상품군", [
            ("cat_webtoon_views", "웹툰/웹소설 조회수", "작품 첫 회차 반응과 체감 노출을 보강하는 상품", "작품 URL", "https://series.naver.com/...", "조회 수량", 100, 100000, 10, "회"),
            ("cat_webtoon_comments", "웹툰/웹소설 댓글(의견)", "작품 참여 분위기를 만드는 댓글 상품", "작품 URL", "https://series.naver.com/...", "댓글 수량", 1, 500, 1, "건"),
        ]),
        ("custom", "맞춤 서비스", "CS", "#111827", "고객 맞춤 서비스", "원하는 채널과 목표에 맞춰 전담 마케터가 설계", [
            ("cat_custom_request", "원하시는 모든 서비스 진행 가능합니다", "원하는 채널과 목표에 맞춰 맞춤형으로 설계합니다.", "희망 채널", "예: 쇼핑몰/앱/커뮤니티/바이럴", "상담 건수", 1, 1, 1, "건"),
        ]),
    ]

    for index, (slug, display_name, icon, accent_color, group_name, group_desc, categories) in enumerate(generic_blueprints, start=len(platforms)):
        group_categories: List[Dict[str, Any]] = []
        for cat_index, category_def in enumerate(categories):
            category_id, name, description, target_label, placeholder, quantity_label, min_amount, max_amount, step_amount, unit_label = category_def
            is_custom = category_id == "cat_custom_request"
            if slug == "seo":
                form_json = keyword_url_form(min_amount, max_amount, step_amount)
                product_code = f"{slug}-traffic"
            elif is_custom:
                form_json = custom_form()
                product_code = f"{slug}-custom"
            elif step_amount == 1 and min_amount == max_amount == 1:
                form_json = custom_form()
                product_code = f"{slug}-package"
            elif target_label.endswith("URL"):
                form_json = url_quantity_form(target_label, placeholder, quantity_label, min_amount, max_amount, step_amount, unit_label)
                product_code = f"{slug}-url"
            else:
                form_json = account_quantity_form(target_label, placeholder, quantity_label, min_amount, max_amount, step_amount, unit_label)
                product_code = f"{slug}-account"

            price_strategy = "fixed" if is_custom else "unit"
            price = 59000 if is_custom else max(12, 85 if unit_label == "명" else 35)
            option_name = "맞춤 상담" if is_custom else "기본"
            product = make_option(
                option_id=f"prd_{category_id}_base",
                category_id=category_id,
                name=name,
                option_name=option_name,
                product_code=product_code,
                price=price,
                min_amount=1 if is_custom else min_amount,
                max_amount=1 if is_custom else max_amount,
                step_amount=1 if is_custom else step_amount,
                unit_label="패키지" if is_custom else unit_label,
                badge="상담형" if is_custom else "운영중",
                price_strategy=price_strategy,
                form_structure_json=form_json,
                estimated_turnaround="담당자 확인 후 진행" if is_custom else "10분~1시간",
            )
            category = make_category(
                category_id=category_id,
                name=name,
                description=description,
                hero_subtitle=f"{display_name} 채널 특성에 맞춘 {name} 상품입니다.",
                option_label_name="상품 옵션",
                service_description_html=service_html(
                    name,
                    f"{display_name} 채널 운영에 필요한 핵심 지표를 빠르게 보강하는 상품입니다.",
                    [
                        f"{display_name} 채널에 맞춰 주문 흐름을 단순화했습니다.",
                        "작업 시작 전 입력한 정보를 다시 한 번 검수해 주세요.",
                        "필요 시 운영 메모를 함께 남기면 담당자가 참고합니다.",
                    ],
                    [
                        "대상 채널 또는 URL을 입력해 주세요.",
                        "원하는 수량을 설정해 주세요.",
                        "주문 후 진행 상태는 내역 화면에서 확인할 수 있어요.",
                    ],
                    "레퍼런스 패널 구조를 따르되, 실제 운영에 맞게 입력 흐름을 단순화했습니다.",
                ),
                products=[product],
                caution=default_caution,
                refund_notice=default_refund,
                sort_order=cat_index,
            )
            group_categories.append(category)

        platforms.append(
            {
                "id": f"pf_{slug}",
                "slug": slug,
                "display_name": display_name,
                "description": group_desc,
                "icon": icon,
                "accent_color": accent_color,
                "groups": [
                    {
                        "id": f"grp_{slug}",
                        "name": group_name,
                        "description": group_desc,
                        "sort_order": 0,
                        "categories": group_categories,
                    }
                ],
            }
        )

    return platforms


class PanelStore:
    def __init__(self, db_path: Path = DB_PATH, database_url: str = "") -> None:
        self.db_path = db_path
        self.database_url = str(database_url or "").strip()
        if self.database_url:
            if not self.database_url.startswith(("postgres://", "postgresql://")):
                raise RuntimeError("SMM_PANEL_DATABASE_URL must be a postgres connection string.")
            self.backend = "postgres"
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.backend = "sqlite"
        self._initialize()

    @classmethod
    def from_env(cls, db_path: Path = DB_PATH) -> "PanelStore":
        database_url = (
            os.environ.get("SMM_PANEL_DATABASE_URL", "").strip()
            or os.environ.get("SMM_PANEL_SUPABASE_DB_URL", "").strip()
        )
        effective_db_path = db_path
        if not database_url and os.environ.get("VERCEL"):
            effective_db_path = Path(os.environ.get("SMM_PANEL_SQLITE_TMP_PATH", "/tmp/smm_panel.db"))
        return cls(db_path=effective_db_path, database_url=database_url)

    def _connect(self) -> DatabaseConnection:
        if self.backend == "postgres":
            if psycopg is None or psycopg_dict_row is None:
                raise RuntimeError(
                    "Supabase/Postgres support requires psycopg. Install dependencies from requirements.txt first."
                )
            conn = psycopg.connect(
                self.database_url,
                autocommit=False,
                prepare_threshold=None,
                row_factory=psycopg_dict_row,
            )
            return DatabaseConnection(self.backend, conn)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return DatabaseConnection(self.backend, conn)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._apply_migrations(conn)
            has_user = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            if not has_user:
                self._seed(conn)
            self._seed_management_samples(conn)
            self._ensure_management_order_samples(conn)
            self._ensure_home_popup(conn)
            self._ensure_site_settings(conn)
            self._ensure_analytics_samples(conn)
            conn.commit()

    def _apply_migrations(self, conn: DatabaseConnection) -> None:
        self._ensure_column(conn, "users", "password_hash", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'customer'")
        self._ensure_column(conn, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "users", "notes", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "last_login_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "home_banners", "image_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "home_banners", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "product_categories", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "products", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "suppliers", "integration_type", "TEXT NOT NULL DEFAULT 'classic'")
        self._ensure_column(conn, "suppliers", "bearer_token", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "home_popups", "image_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "site_visit_events", "exclude_from_stats", "INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE users SET role = 'admin', is_active = 1 WHERE id = ?", (DEMO_USER_ID,))
        conn.execute("UPDATE users SET role = COALESCE(NULLIF(role, ''), 'customer') WHERE id != ?", (DEMO_USER_ID,))

    def _ensure_column(self, conn: DatabaseConnection, table: str, column: str, definition: str) -> None:
        if self.backend == "postgres":
            columns = {
                row["column_name"]
                for row in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
                    """,
                    (table, column),
                ).fetchall()
            }
        else:
            columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column in columns:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _seed_management_samples(self, conn: DatabaseConnection) -> None:
        now = now_iso()
        customers = [
            ("user_brandlab", "브랜드랩", "hello@brandlab.kr", hash_password("brandlab123!"), "01011112222", "STANDARD", "BL", 120000, "customer", 1, "인스타 브랜딩 고객", now, now),
            ("user_cafeflow", "카페플로우", "team@cafeflow.kr", hash_password("cafeflow123!"), "01033334444", "BUSINESS", "CF", 284000, "customer", 1, "플레이스 리뷰 중심 운영", now, now),
            ("user_localmart", "로컬마트", "owner@localmart.kr", hash_password("localmart123!"), "01055556666", "STANDARD", "LM", 76000, "customer", 1, "쇼츠/지도 병행 고객", now, now),
        ]
        for user in customers:
            exists = conn.execute("SELECT 1 FROM users WHERE id = ?", (user[0],)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE users SET password_hash = COALESCE(NULLIF(password_hash, ''), ?) WHERE id = ?",
                    (user[3], user[0]),
                )
                continue
            conn.execute(
                """
                INSERT INTO users (
                    id, name, email, password_hash, phone, tier, avatar_label, balance, role, is_active, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                user,
            )

    def _ensure_management_order_samples(self, conn: DatabaseConnection) -> None:
        existing = conn.execute("SELECT 1 FROM orders WHERE user_id != ? LIMIT 1", (DEMO_USER_ID,)).fetchone()
        if existing is not None:
            return

        now = dt.datetime.now().astimezone()
        sample_orders = [
            {
                "id": "order_mgmt_1",
                "order_number": "P24M101",
                "user_id": "user_brandlab",
                "platform_section_id": "pf_instagram",
                "product_category_id": "cat_instagram_korean_followers",
                "product_id": "prd_instagram_korean_followers_standard",
                "product_name": "인스타그램 한국인 팔로워",
                "option_name": "스탠다드",
                "target_value": "brandlab.official",
                "contact_phone": "01011112222",
                "quantity": 300,
                "unit_price": 120,
                "total_price": 36000,
                "status": "completed",
                "notes": {"memo": "브랜드 런칭 초반 신뢰도 확보"},
                "created_at": (now - dt.timedelta(days=16)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=15, hours=18)).isoformat(timespec="seconds"),
                "fields": [("targetValue", "계정(ID)", "brandlab.official"), ("orderedCount", "수량", "300")],
            },
            {
                "id": "order_mgmt_2",
                "order_number": "P24M102",
                "user_id": "user_brandlab",
                "platform_section_id": "pf_popular",
                "product_category_id": "cat_reels_views",
                "product_id": "prd_reels_views_standard",
                "product_name": "릴스 조회수",
                "option_name": "스탠다드",
                "target_value": "https://instagram.com/reel/brandlab-campaign",
                "contact_phone": "01011112222",
                "quantity": 4000,
                "unit_price": 8,
                "total_price": 32000,
                "status": "completed",
                "notes": {"memo": "신규 캠페인 릴스 도달 보강"},
                "created_at": (now - dt.timedelta(days=11)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=10, hours=20)).isoformat(timespec="seconds"),
                "fields": [("targetUrl", "릴스 URL", "https://instagram.com/reel/brandlab-campaign"), ("orderedCount", "수량", "4000")],
            },
            {
                "id": "order_mgmt_3",
                "order_number": "P24M103",
                "user_id": "user_cafeflow",
                "platform_section_id": "pf_nportal",
                "product_category_id": "cat_place_reviews",
                "product_id": "prd_place_reviews_basic",
                "product_name": "플레이스 리뷰",
                "option_name": "기본",
                "target_value": "카페플로우 성수점",
                "contact_phone": "01033334444",
                "quantity": 15,
                "unit_price": 3500,
                "total_price": 52500,
                "status": "in_progress",
                "notes": {"memo": "신규 지점 오픈 주간 리뷰 보강"},
                "created_at": (now - dt.timedelta(days=9)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=8, hours=22)).isoformat(timespec="seconds"),
                "fields": [("targetValue", "매장명", "카페플로우 성수점"), ("orderedCount", "수량", "15")],
            },
            {
                "id": "order_mgmt_4",
                "order_number": "P24M104",
                "user_id": "user_cafeflow",
                "platform_section_id": "pf_nportal",
                "product_category_id": "cat_blog_inflow",
                "product_id": "prd_blog_inflow_basic",
                "product_name": "블로그 유입",
                "option_name": "기본",
                "target_value": "성수 카페 추천",
                "contact_phone": "01033334444",
                "quantity": 1200,
                "unit_price": 18,
                "total_price": 21600,
                "status": "queued",
                "notes": {"memo": "키워드 유입 테스트"},
                "created_at": (now - dt.timedelta(days=4)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=4)).isoformat(timespec="seconds"),
                "fields": [("targetKeyword", "키워드", "성수 카페 추천"), ("orderedCount", "수량", "1200")],
            },
            {
                "id": "order_mgmt_5",
                "order_number": "P24M105",
                "user_id": "user_localmart",
                "platform_section_id": "pf_youtube",
                "product_category_id": "cat_youtube_views",
                "product_id": "prd_youtube_views_standard",
                "product_name": "유튜브 조회수",
                "option_name": "스탠다드",
                "target_value": "https://youtube.com/watch?v=localmart-demo",
                "contact_phone": "01055556666",
                "quantity": 2500,
                "unit_price": 10,
                "total_price": 25000,
                "status": "completed",
                "notes": {"memo": "지역 행사 쇼츠 연계 조회수 강화"},
                "created_at": (now - dt.timedelta(days=2)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=1, hours=19)).isoformat(timespec="seconds"),
                "fields": [("targetUrl", "영상 URL", "https://youtube.com/watch?v=localmart-demo"), ("orderedCount", "수량", "2500")],
            },
        ]

        for order in sample_orders:
            conn.execute(
                """
                INSERT INTO orders (
                    id, order_number, user_id, platform_section_id, product_category_id, product_id,
                    product_name_snapshot, option_name_snapshot, target_value, contact_phone, quantity,
                    unit_price, total_price, status, notes_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order["id"],
                    order["order_number"],
                    order["user_id"],
                    order["platform_section_id"],
                    order["product_category_id"],
                    order["product_id"],
                    order["product_name"],
                    order["option_name"],
                    order["target_value"],
                    order["contact_phone"],
                    order["quantity"],
                    order["unit_price"],
                    order["total_price"],
                    order["status"],
                    as_json(order["notes"]),
                    order["created_at"],
                    order["updated_at"],
                ),
            )
            for index, (field_key, field_label, field_value) in enumerate(order["fields"]):
                conn.execute(
                    "INSERT INTO order_fields (id, order_id, field_key, field_label, field_value) VALUES (?, ?, ?, ?, ?)",
                    (f"{order['id']}_field_{index}", order["id"], field_key, field_label, field_value),
                )

    def _ensure_home_popup(self, conn: sqlite3.Connection) -> None:
        exists = conn.execute("SELECT id FROM home_popups LIMIT 1").fetchone()
        if exists is not None:
            return
        popup = default_home_popup_record()
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO home_popups (
                id, name, badge_text, title, description, image_url, route, theme, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                popup["id"],
                popup["name"],
                popup["badgeText"],
                popup["title"],
                popup["description"],
                popup["imageUrl"],
                popup["route"],
                popup["theme"],
                bool_to_int(popup["isActive"]),
                timestamp,
                timestamp,
            ),
        )

    def _ensure_site_settings(self, conn: sqlite3.Connection) -> None:
        exists = conn.execute("SELECT id FROM site_settings LIMIT 1").fetchone()
        if exists is not None:
            return
        settings = default_site_settings_record()
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO site_settings (
                id, site_name, site_description, use_mail_sms_site_name, mail_sms_site_name,
                favicon_url, share_image_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                settings["siteName"],
                settings["siteDescription"],
                bool_to_int(settings["useMailSmsSiteName"]),
                settings["mailSmsSiteName"],
                settings["faviconUrl"],
                settings["shareImageUrl"],
                timestamp,
                timestamp,
            ),
        )

    def _ensure_analytics_samples(self, conn: sqlite3.Connection) -> None:
        exists = conn.execute("SELECT COUNT(*) AS count FROM site_visit_events").fetchone()["count"]
        if exists:
            return

        visitors = [f"visitor_seed_{index:02d}" for index in range(1, 19)]
        detail_routes = [
            "/products/cat_instagram_korean_followers",
            "/products/cat_youtube_views",
            "/products/cat_place_reviews",
            "/products/cat_reels_views",
            "/products/cat_blog_inflow",
        ]
        entry_referrers = [
            "https://www.google.com/search?q=인스타그램+팔로워+늘리기",
            "https://search.naver.com/search.naver?query=유튜브+조회수+늘리기",
            "https://www.instagram.com/",
            "https://l.facebook.com/",
            "https://m.youtube.com/",
            "",
        ]
        user_agents = {
            "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "tablet": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "desktop": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }
        now = dt.datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
        event_rows: List[tuple[Any, ...]] = []

        for day_offset in range(44, -1, -1):
            base = now - dt.timedelta(days=day_offset)
            session_total = 4 + ((44 - day_offset) % 5)
            for session_index in range(session_total):
                visitor_id = visitors[(day_offset * 2 + session_index) % len(visitors)]
                session_id = f"session_seed_{44 - day_offset:02d}_{session_index:02d}"
                entry_referrer = entry_referrers[(day_offset + session_index) % len(entry_referrers)]
                device_type = ("mobile", "tablet", "desktop")[session_index % 3]
                analytics_source = self._classify_visit_source(entry_referrer, "", "pulse24.local")
                detail_route = detail_routes[(day_offset + session_index) % len(detail_routes)]
                route_sequence = ["/", "/products", detail_route]
                if session_index % 2 == 0:
                    route_sequence.append("/orders")
                if session_index % 3 == 0:
                    route_sequence.append("/my")

                previous_route = ""
                for step_index, route in enumerate(route_sequence):
                    created_at = (base + dt.timedelta(hours=9 + session_index, minutes=step_index * 7)).isoformat(timespec="seconds")
                    source_meta = analytics_source if step_index == 0 else {
                        "referrerUrl": "",
                        "referrerDomain": "",
                        "sourceType": "internal",
                        "sourceLabel": "내부 이동",
                        "searchKeyword": "",
                    }
                    event_rows.append(
                        (
                            f"visit_seed_{day_offset:02d}_{session_index:02d}_{step_index:02d}",
                            visitor_id,
                            session_id,
                            route,
                            self._analytics_page_label(conn, route),
                            source_meta["referrerUrl"],
                            source_meta["referrerDomain"],
                            source_meta["sourceType"],
                            source_meta["sourceLabel"],
                            source_meta["searchKeyword"],
                            previous_route,
                            user_agents[device_type],
                            device_type,
                            0,
                            created_at,
                        )
                    )
                    previous_route = route

        conn.executemany(
            """
            INSERT INTO site_visit_events (
                id, visitor_id, session_id, route, page_label, referrer_url, referrer_domain,
                source_type, source_label, search_keyword, previous_route, user_agent, device_type, exclude_from_stats, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            event_rows,
        )

    def _seed(self, conn: sqlite3.Connection) -> None:
        created_at = now_iso()
        conn.execute(
            """
            INSERT INTO users (id, name, email, password_hash, phone, tier, role, avatar_label, balance, is_active, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (DEMO_USER_ID, "데모 관리자", "demo@pulse24.local", "", "01024512400", "PRO", "admin", "P24", 185000, 1, "현재 데모 패널 운영 계정", created_at, created_at),
        )

        banners = [
            ("banner_launch", "첫 캠페인을 더 빨리 띄우세요", "신규 계정과 런칭 숏폼에 맞춘 추천 패키지를 한 번에 비교할 수 있어요.", "추천 패키지 보기", "/products/cat_branding_standard", "", "blue", 1, 0),
            ("banner_safe", "안전한 속도로 지표를 설계합니다", "급격한 변화보다 지속 가능한 흐름을 우선하는 패널 UI/UX로 구성했습니다.", "인스타 성장 보기", "/products/cat_instagram_korean_followers", "", "mint", 1, 1),
            ("banner_consult", "찾는 상품이 없다면 맞춤 상담으로 연결", "웹툰, 커뮤니티, 앱, 오픈마켓까지 맞춤 구조로 이어서 설계할 수 있습니다.", "맞춤 서비스 보기", "/products/cat_custom_request", "", "dark", 1, 2),
        ]
        conn.executemany(
            "INSERT INTO home_banners (id, title, subtitle, cta_label, route, image_url, theme, is_active, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            banners,
        )

        interest_tags = [
            ("interest_instagram_followers", "인스타 팔로워", "/products/cat_instagram_korean_followers", 0),
            ("interest_reels_views", "릴스 조회수", "/products/cat_reels_views", 1),
            ("interest_youtube_views", "유튜브 조회수", "/products/cat_youtube_views", 2),
            ("interest_blog_inflow", "블로그 유입", "/products/cat_blog_inflow", 3),
            ("interest_place", "플레이스 리뷰", "/products/cat_place_reviews", 4),
            ("interest_custom", "맞춤 상담", "/products/cat_custom_request", 5),
        ]
        conn.executemany(
            "INSERT INTO home_interest_tags (id, title, route, sort_order) VALUES (?, ?, ?, ?)",
            interest_tags,
        )

        spotlights = [
            ("spotlight_featured_1", "featured", "인스타그램 프로필 방문", "프로필 유입과 링크 전환을 빠르게 만들고 싶을 때", "/products/cat_instagram_profile_visit", "↗", 0),
            ("spotlight_featured_2", "featured", "릴스 조회수 부스팅", "공개 직후 숏폼 도달을 빠르게 끌어올리는 대표 상품", "/products/cat_reels_views", "▶", 1),
            ("spotlight_featured_3", "featured", "유튜브 구독자", "채널 첫 인상을 정리할 때 가장 많이 쓰는 성장 옵션", "/products/cat_youtube_subscribers", "◎", 2),
            ("spotlight_featured_4", "featured", "플레이스 리뷰 부스팅", "오프라인 매장 신뢰도와 저장 흐름을 함께 보강", "/products/cat_place_reviews", "⌂", 3),
        ]
        conn.executemany(
            "INSERT INTO home_spotlights (id, section_key, title, subtitle, route, icon, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            spotlights,
        )

        supports = [
            ("support_faq", "FAQ", "주문 전 자주 묻는 질문을 빠르게 확인하세요.", "/my", "?", "", 0),
            ("support_notice", "공지사항", "운영 공지와 정책 업데이트를 바로 확인하세요.", "/my", "!", "", 1),
            ("support_consult", "1:1 상담", "맞춤형 상품이 필요하면 상담 흐름으로 연결합니다.", "/products/cat_custom_request", "☏", "", 2),
            ("support_guide", "이용가이드", "처음 쓰는 분도 쉽게 이해할 수 있도록 흐름을 정리했습니다.", "/my", "→", "", 3),
        ]
        conn.executemany(
            "INSERT INTO support_links (id, title, subtitle, route, icon, external_url, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            supports,
        )

        benefits = [
            ("benefit_safe", "100% 운영 안정성 우선", "급격한 수치 상승보다 안정적인 속도와 채널 안전을 우선합니다.", "🛡", 0),
            ("benefit_fast", "빠른 주문 흐름", "모바일 우선 주문 구조로 원하는 상품을 빠르게 찾을 수 있어요.", "⚡", 1),
            ("benefit_flexible", "플랫폼별 맞춤 폼 구조", "URL형, 계정형, 키워드형 주문 폼을 상품 특성에 맞게 구성했습니다.", "🧩", 2),
            ("benefit_support", "상담형 상품 확장", "원하는 상품이 없으면 맞춤 서비스로 자연스럽게 이어지도록 설계했습니다.", "🤝", 3),
        ]
        conn.executemany(
            "INSERT INTO benefits (id, title, description, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
            benefits,
        )

        now = dt.datetime.now().astimezone()
        notices = [
            ("notice_1", "운영 속도 정책이 안정형 기준으로 조정되었습니다.", "급격한 주문 몰림 구간에서 계정 안전을 우선하도록 기본 속도 정책을 조정했습니다.", "업데이트", 1, (now - dt.timedelta(days=1)).isoformat(timespec="seconds")),
            ("notice_2", "신규 플랫폼 탭이 추가되었습니다.", "커뮤니티, 웹툰/웹소설, 쇼핑라이브 탭을 새롭게 구성했습니다.", "신규", 0, (now - dt.timedelta(days=4)).isoformat(timespec="seconds")),
            ("notice_3", "맞춤 서비스 접수 폼이 개선되었습니다.", "희망 채널, 연락처, 상세 요청을 한 화면에서 접수할 수 있도록 수정했습니다.", "안내", 0, (now - dt.timedelta(days=8)).isoformat(timespec="seconds")),
        ]
        conn.executemany(
            "INSERT INTO notices (id, title, body, tag, pinned, published_at) VALUES (?, ?, ?, ?, ?, ?)",
            notices,
        )

        faqs = [
            ("faq_1", "주문 후 바로 시작되나요?", "즉시형 상품은 수분 내 시작되며, 상담형 상품은 담당자 확인 후 순차 진행됩니다.", 0),
            ("faq_2", "비공개 계정도 주문 가능한가요?", "비공개 계정이나 삭제된 게시물은 정상 진행이 어렵기 때문에 공개 상태를 권장합니다.", 1),
            ("faq_3", "환불 기준은 어떻게 되나요?", "작업 전 단계는 취소가 가능하지만, 진행이 시작된 이후에는 부분 환불 또는 재진행 기준이 적용됩니다.", 2),
            ("faq_4", "맞춤형 상품도 만들 수 있나요?", "가능합니다. 맞춤 서비스 상품으로 접수하면 요청 범위와 예산에 맞춰 설계해 드립니다.", 3),
        ]
        conn.executemany(
            "INSERT INTO faqs (id, question, answer, sort_order) VALUES (?, ?, ?, ?)",
            faqs,
        )

        for platform_index, platform in enumerate(catalog_blueprints()):
            conn.execute(
                """
                INSERT INTO platform_sections (id, slug, display_name, description, icon, accent_color, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    platform["id"],
                    platform["slug"],
                    platform["display_name"],
                    platform["description"],
                    platform["icon"],
                    platform["accent_color"],
                    platform_index,
                ),
            )
            for group_index, group in enumerate(platform["groups"]):
                conn.execute(
                    """
                    INSERT INTO platform_groups (id, platform_section_id, name, description, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (group["id"], platform["id"], group["name"], group["description"], group_index),
                )
                for category in group["categories"]:
                    conn.execute(
                        """
                        INSERT INTO product_categories (
                            id, platform_group_id, name, description, option_label_name, category_kind,
                            hero_title, hero_subtitle, service_description_html, caution_json, refund_notice_json, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            category["id"],
                            group["id"],
                            category["name"],
                            category["description"],
                            category["option_label_name"],
                            category["category_kind"],
                            category["hero_title"],
                            category["hero_subtitle"],
                            category["service_description_html"],
                            category["caution_json"],
                            category["refund_notice_json"],
                            category["sort_order"],
                        ),
                    )
                    has_multiple = 1 if len(category["products"]) > 1 else 0
                    for product_index, product in enumerate(category["products"]):
                        conn.execute(
                            """
                            INSERT INTO products (
                                id, product_category_id, name, menu_name, option_name, product_code, price,
                                min_amount, max_amount, step_amount, option_price_rate, price_strategy, unit_label,
                                supports_order_options, is_discounted, product_kind, is_custom,
                                estimated_turnaround, badge, form_structure_json, sort_order
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                product["id"],
                                category["id"],
                                product["name"],
                                product["menu_name"],
                                product["option_name"],
                                product["product_code"],
                                product["price"],
                                product["min_amount"],
                                product["max_amount"],
                                product["step_amount"],
                                product["option_price_rate"],
                                product["price_strategy"],
                                product["unit_label"],
                                has_multiple,
                                product["is_discounted"],
                                product["product_kind"],
                                product["is_custom"],
                                product["estimated_turnaround"],
                                product["badge"],
                                product["form_structure_json"],
                                product_index,
                            ),
                        )

        transactions = [
            ("tx_initial", DEMO_USER_ID, 350000, 350000, "charge", "초기 데모 캐시 충전", (now - dt.timedelta(days=10)).isoformat(timespec="seconds")),
            ("tx_order_1", DEMO_USER_ID, -50000, 300000, "order", "유튜브 조회수 주문", (now - dt.timedelta(days=9)).isoformat(timespec="seconds")),
            ("tx_order_2", DEMO_USER_ID, -36000, 264000, "order", "인스타그램 프로필 방문 주문", (now - dt.timedelta(days=6)).isoformat(timespec="seconds")),
            ("tx_order_3", DEMO_USER_ID, -79000, 185000, "order", "숏폼 런칭 패키지 주문", (now - dt.timedelta(days=2)).isoformat(timespec="seconds")),
        ]
        conn.executemany(
            "INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            transactions,
        )

        orders = [
            {
                "id": "order_seed_1",
                "order_number": "P240001",
                "platform_section_id": "pf_youtube",
                "product_category_id": "cat_youtube_views",
                "product_id": "prd_youtube_views_standard",
                "product_name": "유튜브 조회수",
                "option_name": "스탠다드",
                "target_value": "https://youtube.com/watch?v=pulse-demo-1",
                "contact_phone": "01024512400",
                "quantity": 5000,
                "unit_price": 10,
                "total_price": 50000,
                "status": "completed",
                "notes": {"memo": "런칭 첫날 저녁 시간 집중"},
                "created_at": (now - dt.timedelta(days=9)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=8, hours=20)).isoformat(timespec="seconds"),
                "fields": [
                    ("targetUrl", "영상 URL", "https://youtube.com/watch?v=pulse-demo-1"),
                    ("orderedCount", "조회 수량", "5000"),
                ],
            },
            {
                "id": "order_seed_2",
                "order_number": "P240002",
                "platform_section_id": "pf_instagram",
                "product_category_id": "cat_instagram_profile_visit",
                "product_id": "prd_instagram_profile_visit_basic",
                "product_name": "인스타그램 프로필 방문",
                "option_name": "기본",
                "target_value": "pulse24_official",
                "contact_phone": "01024512400",
                "quantity": 850,
                "unit_price": 42,
                "total_price": 35700,
                "status": "in_progress",
                "notes": {"memo": "이벤트 공지 게시물 이후 프로필 유입 보강"},
                "created_at": (now - dt.timedelta(days=6)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=6, hours=-2)).isoformat(timespec="seconds"),
                "fields": [
                    ("targetValue", "계정(ID)", "pulse24_official"),
                    ("orderedCount", "방문 수량", "850"),
                ],
            },
            {
                "id": "order_seed_3",
                "order_number": "P240003",
                "platform_section_id": "pf_popular",
                "product_category_id": "cat_shortform_launch",
                "product_id": "prd_shortform_launch_boost",
                "product_name": "숏폼 런칭 패키지",
                "option_name": "부스트",
                "target_value": "https://instagram.com/reel/pulse24-launch",
                "contact_phone": "01024512400",
                "quantity": 1,
                "unit_price": 79000,
                "total_price": 79000,
                "status": "queued",
                "notes": {"memo": "브랜드 신제품 공개 주간 집중 운영"},
                "created_at": (now - dt.timedelta(days=2)).isoformat(timespec="seconds"),
                "updated_at": (now - dt.timedelta(days=2)).isoformat(timespec="seconds"),
                "fields": [
                    ("targetUrl", "영상 URL", "https://instagram.com/reel/pulse24-launch"),
                ],
            },
        ]

        for order in orders:
            conn.execute(
                """
                INSERT INTO orders (
                    id, order_number, user_id, platform_section_id, product_category_id, product_id,
                    product_name_snapshot, option_name_snapshot, target_value, contact_phone, quantity,
                    unit_price, total_price, status, notes_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order["id"],
                    order["order_number"],
                    DEMO_USER_ID,
                    order["platform_section_id"],
                    order["product_category_id"],
                    order["product_id"],
                    order["product_name"],
                    order["option_name"],
                    order["target_value"],
                    order["contact_phone"],
                    order["quantity"],
                    order["unit_price"],
                    order["total_price"],
                    order["status"],
                    as_json(order["notes"]),
                    order["created_at"],
                    order["updated_at"],
                ),
            )
            for index, (field_key, field_label, field_value) in enumerate(order["fields"]):
                conn.execute(
                    "INSERT INTO order_fields (id, order_id, field_key, field_label, field_value) VALUES (?, ?, ?, ?, ?)",
                    (f"{order['id']}_field_{index}", order["id"], field_key, field_label, field_value),
                )

    def _fetchall(self, query: str, params: Iterable[Any] = ()) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(query, tuple(params)).fetchall()

    def _fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row:
        with self._connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        if row is None:
            raise PanelError("요청한 데이터를 찾을 수 없습니다.", status=404)
        return row

    def _public_user_row(self, conn: sqlite3.Connection, user_id: str) -> Optional[sqlite3.Row]:
        if not user_id:
            return None
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ? AND is_active = 1 AND role != 'admin'
            """,
            (user_id,),
        ).fetchone()
        return row

    def _user_summary(self, conn: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
        user = self._public_user_row(conn, user_id)
        if user is None:
            raise PanelError("로그인한 사용자를 찾을 수 없습니다.", status=401)
        return {
            "id": user["id"],
            "name": user["name"],
            "emailMasked": mask_email(user["email"]),
            "phoneMasked": mask_phone(user["phone"]),
            "tier": user["tier"],
            "avatarLabel": user["avatar_label"],
            "balance": user["balance"],
            "balanceLabel": money(user["balance"]),
            "hasPassword": bool(user["password_hash"]),
        }

    def authenticate_public_user(self, email: str, password: str) -> Dict[str, Any]:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            raise PanelError("이메일을 입력해 주세요.")
        if not str(password or ""):
            raise PanelError("비밀번호를 입력해 주세요.")

        with self._connect() as conn:
            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE lower(email) = ? AND is_active = 1 AND role != 'admin'
                LIMIT 1
                """,
                (normalized_email,),
            ).fetchone()
            if user is None or not verify_password(password, user["password_hash"]):
                raise PanelError("이메일 또는 비밀번호가 올바르지 않습니다.", status=401)
            timestamp = now_iso()
            conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, user["id"]))
            conn.commit()
            return self._user_summary(conn, user["id"])

    def public_user_for_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = self._public_user_row(conn, user_id)
            if row is None:
                return None
            return self._user_summary(conn, user_id)

    def bootstrap(self, user_id: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            user = self._user_summary(conn, user_id) if user_id else None
            popup_row = conn.execute("SELECT * FROM home_popups ORDER BY updated_at DESC LIMIT 1").fetchone()
            site_settings_row = self._site_settings_row(conn)
            site_settings = self._site_settings_public_payload(site_settings_row)
            banners = [
                dict(row)
                for row in conn.execute("SELECT * FROM home_banners ORDER BY sort_order")
            ]
            interest_tags = [
                dict(row)
                for row in conn.execute("SELECT * FROM home_interest_tags ORDER BY sort_order")
            ]
            featured = [
                dict(row)
                for row in conn.execute("SELECT * FROM home_spotlights WHERE section_key = 'featured' ORDER BY sort_order")
            ]
            supports = [
                dict(row)
                for row in conn.execute("SELECT * FROM support_links ORDER BY sort_order")
            ]
            benefits = [
                dict(row)
                for row in conn.execute("SELECT * FROM benefits ORDER BY sort_order")
            ]
            notices = [
                {
                    **dict(row),
                    "publishedLabel": self._relative_date_label(row["published_at"]),
                }
                for row in conn.execute("SELECT * FROM notices ORDER BY pinned DESC, published_at DESC LIMIT 5")
            ]
            faqs = [dict(row) for row in conn.execute("SELECT * FROM faqs ORDER BY sort_order")]
            platforms = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, slug, display_name, description, icon, accent_color
                    FROM platform_sections
                    WHERE EXISTS (
                        SELECT 1
                        FROM platform_groups pg
                        JOIN product_categories pc ON pc.platform_group_id = pg.id AND pc.is_active = 1
                        JOIN products p ON p.product_category_id = pc.id AND p.is_active = 1
                        WHERE pg.platform_section_id = platform_sections.id
                    )
                    ORDER BY sort_order
                    """
                )
            ]

            product_count = conn.execute("SELECT COUNT(*) AS count FROM products WHERE is_active = 1").fetchone()["count"]
            order_count = 0
            active_count = 0
            balance_label = "0원"
            if user:
                order_count = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE user_id = ?", (user["id"],)).fetchone()["count"]
                active_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM orders WHERE user_id = ? AND status IN ('queued', 'in_progress')",
                    (user["id"],),
                ).fetchone()["count"]
                balance_label = user["balanceLabel"]

            company = {
                "name": site_settings["siteName"],
                "representative": "Demo Operator",
                "contact": "support@pulse24.local",
                "hours": "평일 10:00 - 19:00",
            }

            return {
                "app": {
                    "name": site_settings["siteName"],
                    "subtitle": "Reference-style SMM Growth Panel",
                    "accentColor": "#4c76ff",
                },
                "siteSettings": site_settings,
                "user": user,
                "viewer": {
                    "authenticated": bool(user),
                },
                "heroStats": [
                    {"label": "보유 캐시", "value": balance_label},
                    {"label": "등록 상품", "value": f"{product_count:,}개"},
                    {"label": "진행 중 주문", "value": f"{active_count:,}건"},
                    {"label": "누적 주문", "value": f"{order_count:,}건"},
                ],
                "topLinks": [
                    {"label": "서비스 소개서", "route": "/products"},
                    {"label": "이용 가이드", "route": "/my"},
                ],
                "popup": self._popup_public_payload(popup_row) if popup_row else None,
                "platforms": [
                    {
                        "id": platform["id"],
                        "slug": platform["slug"],
                        "displayName": platform["display_name"],
                        "description": platform["description"],
                        "icon": platform["icon"],
                        "accentColor": platform["accent_color"],
                    }
                    for platform in platforms
                ],
                "banners": [
                    {
                        "id": banner["id"],
                        "title": banner["title"],
                        "subtitle": banner["subtitle"],
                        "ctaLabel": banner["cta_label"],
                        "route": banner["route"],
                        "imageUrl": banner["image_url"],
                        "theme": banner["theme"],
                        "isActive": bool(banner["is_active"]),
                    }
                    for banner in banners
                    if bool(banner["is_active"])
                ],
                "interestTags": [
                    {
                        "id": tag["id"],
                        "title": tag["title"],
                        "route": tag["route"],
                    }
                    for tag in interest_tags
                ],
                "featuredServices": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "subtitle": item["subtitle"],
                        "route": item["route"],
                        "icon": item["icon"],
                    }
                    for item in featured
                ],
                "supportLinks": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "subtitle": item["subtitle"],
                        "route": item["route"],
                        "icon": item["icon"],
                        "externalUrl": item["external_url"],
                    }
                    for item in supports
                ],
                "benefits": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "description": item["description"],
                        "icon": item["icon"],
                    }
                    for item in benefits
                ],
                "notices": notices,
                "faqs": faqs,
                "company": company,
            }

    def list_catalog(self, search: str = "") -> Dict[str, Any]:
        search_value = search.strip().lower()
        category_rows = self._fetchall(
            """
            SELECT
                ps.id AS platform_id,
                ps.slug AS platform_slug,
                ps.display_name AS platform_name,
                ps.description AS platform_description,
                ps.icon AS platform_icon,
                ps.accent_color AS platform_accent_color,
                pg.id AS group_id,
                pg.name AS group_name,
                pg.description AS group_description,
                pc.id AS category_id,
                pc.name AS category_name,
                pc.description AS category_description,
                pc.option_label_name,
                pc.hero_subtitle,
                MIN(p.price) AS starting_price,
                COUNT(p.id) AS option_count,
                MAX(CASE WHEN p.badge != '' THEN p.badge ELSE '' END) AS badge
            FROM product_categories pc
            JOIN platform_groups pg ON pg.id = pc.platform_group_id
            JOIN platform_sections ps ON ps.id = pg.platform_section_id
            JOIN products p ON p.product_category_id = pc.id AND p.is_active = 1
            WHERE pc.is_active = 1
            GROUP BY pc.id
            ORDER BY ps.sort_order, pg.sort_order, pc.sort_order
            """
        )

        products_by_category: Dict[str, List[str]] = {}
        for row in self._fetchall("SELECT product_category_id, name, option_name FROM products WHERE is_active = 1"):
            products_by_category.setdefault(row["product_category_id"], []).append(f"{row['name']} {row['option_name']}".strip().lower())

        platforms: Dict[str, Dict[str, Any]] = {}
        for row in category_rows:
            haystack = " ".join(
                [
                    row["platform_name"],
                    row["group_name"],
                    row["category_name"],
                    row["category_description"],
                    " ".join(products_by_category.get(row["category_id"], [])),
                ]
            ).lower()
            if search_value and search_value not in haystack:
                continue

            platform = platforms.setdefault(
                row["platform_id"],
                {
                    "id": row["platform_id"],
                    "slug": row["platform_slug"],
                    "displayName": row["platform_name"],
                    "description": row["platform_description"],
                    "icon": row["platform_icon"],
                    "accentColor": row["platform_accent_color"],
                    "groups": {},
                },
            )
            group = platform["groups"].setdefault(
                row["group_id"],
                {
                    "id": row["group_id"],
                    "name": row["group_name"],
                    "description": row["group_description"],
                    "productCategories": [],
                },
            )
            group["productCategories"].append(
                {
                    "id": row["category_id"],
                    "name": row["category_name"],
                    "description": row["category_description"],
                    "optionLabelName": row["option_label_name"],
                    "heroSubtitle": row["hero_subtitle"],
                    "startingPrice": row["starting_price"],
                    "startingPriceLabel": money(int(row["starting_price"])),
                    "optionCount": row["option_count"],
                    "badge": row["badge"],
                }
            )

        nested = []
        for platform in platforms.values():
            nested.append(
                {
                    **{key: value for key, value in platform.items() if key != "groups"},
                    "groups": list(platform["groups"].values()),
                }
            )

        return {"platforms": nested, "search": search}

    def get_product_category(self, category_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            category = conn.execute(
                """
                SELECT
                    pc.*,
                    pg.id AS group_id,
                    pg.name AS group_name,
                    pg.description AS group_description,
                    ps.id AS platform_id,
                    ps.slug AS platform_slug,
                    ps.display_name AS platform_name,
                    ps.icon AS platform_icon,
                    ps.accent_color AS platform_accent_color
                FROM product_categories pc
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                WHERE pc.id = ? AND pc.is_active = 1
                """,
                (category_id,),
            ).fetchone()
            if category is None:
                raise PanelError("상품 카테고리를 찾을 수 없습니다.", status=404)

            products = []
            for row in conn.execute(
                "SELECT * FROM products WHERE product_category_id = ? AND is_active = 1 ORDER BY sort_order, option_name, name",
                (category_id,),
            ).fetchall():
                products.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "menuName": row["menu_name"],
                        "optionName": row["option_name"],
                        "productCode": row["product_code"],
                        "price": row["price"],
                        "priceLabel": money(row["price"]),
                        "minAmount": row["min_amount"],
                        "maxAmount": row["max_amount"],
                        "stepAmount": row["step_amount"],
                        "optionPriceRate": row["option_price_rate"],
                        "priceStrategy": row["price_strategy"],
                        "unitLabel": row["unit_label"],
                        "supportsOrderOptions": bool(row["supports_order_options"]),
                        "isDiscounted": bool(row["is_discounted"]),
                        "productKind": row["product_kind"],
                        "isCustom": bool(row["is_custom"]),
                        "estimatedTurnaround": row["estimated_turnaround"],
                        "badge": row["badge"],
                        "formStructure": parse_json(row["form_structure_json"], {}),
                    }
                )

            related_rows = conn.execute(
                """
                SELECT pc.id, pc.name, pc.description
                FROM product_categories pc
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                WHERE pg.id = ? AND pc.id != ?
                ORDER BY pc.sort_order
                LIMIT 3
                """,
                (category["group_id"], category_id),
            ).fetchall()

            return {
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "optionLabelName": category["option_label_name"],
                "heroTitle": category["hero_title"],
                "heroSubtitle": category["hero_subtitle"],
                "categoryKind": category["category_kind"],
                "serviceDescriptionHtml": category["service_description_html"],
                "caution": parse_json(category["caution_json"], []),
                "refundNotice": parse_json(category["refund_notice_json"], []),
                "platform": {
                    "id": category["platform_id"],
                    "slug": category["platform_slug"],
                    "displayName": category["platform_name"],
                    "icon": category["platform_icon"],
                    "accentColor": category["platform_accent_color"],
                },
                "group": {
                    "id": category["group_id"],
                    "name": category["group_name"],
                    "description": category["group_description"],
                },
                "products": products,
                "relatedCategories": [
                    {"id": row["id"], "name": row["name"], "description": row["description"]}
                    for row in related_rows
                ],
            }

    def list_orders(self, status: str = "", user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        with self._connect() as conn:
            query = """
                SELECT
                    o.*,
                    ps.display_name AS platform_name,
                    ps.icon AS platform_icon
                FROM orders o
                JOIN platform_sections ps ON ps.id = o.platform_section_id
                WHERE o.user_id = ?
            """
            params: List[Any] = [user_id]
            if status:
                query += " AND o.status = ?"
                params.append(status)
            query += " ORDER BY o.created_at DESC"

            orders = []
            for row in conn.execute(query, params).fetchall():
                fields = conn.execute(
                    "SELECT field_key, field_label, field_value FROM order_fields WHERE order_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
                notes = parse_json(row["notes_json"], {})
                orders.append(
                    {
                        "id": row["id"],
                        "orderNumber": row["order_number"],
                        "platformName": row["platform_name"],
                        "platformIcon": row["platform_icon"],
                        "productName": row["product_name_snapshot"],
                        "optionName": row["option_name_snapshot"],
                        "targetValue": row["target_value"],
                        "contactPhoneMasked": mask_phone(row["contact_phone"]),
                        "quantity": row["quantity"],
                        "unitPrice": row["unit_price"],
                        "unitPriceLabel": money(row["unit_price"]),
                        "totalPrice": row["total_price"],
                        "totalPriceLabel": money(row["total_price"]),
                        "status": row["status"],
                        "notes": {key: value for key, value in notes.items() if key != "adminMemo"},
                        "createdAt": row["created_at"],
                        "createdLabel": self._relative_date_label(row["created_at"]),
                        "fields": [
                            {
                                "key": field["field_key"],
                                "label": field["field_label"],
                                "value": mask_phone(field["field_value"]) if field["field_key"] == "contactPhone" else field["field_value"],
                            }
                            for field in fields
                        ],
                    }
                )

            counts = {
                "all": len(orders),
                "queued": sum(1 for order in orders if order["status"] == "queued"),
                "in_progress": sum(1 for order in orders if order["status"] == "in_progress"),
                "completed": sum(1 for order in orders if order["status"] == "completed"),
            }
            return {"orders": orders, "counts": counts}

    def list_transactions(self, user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        rows = self._fetchall(
            """
            SELECT * FROM balance_transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        transactions = [
            {
                "id": row["id"],
                "amount": row["amount"],
                "amountLabel": ("+" if row["amount"] > 0 else "") + money(row["amount"]),
                "balanceAfter": row["balance_after"],
                "balanceAfterLabel": money(row["balance_after"]),
                "kind": row["kind"],
                "memo": row["memo"],
                "createdAt": row["created_at"],
                "createdLabel": self._relative_date_label(row["created_at"]),
            }
            for row in rows
        ]
        return {"transactions": transactions}

    def record_site_visit(
        self,
        payload: Dict[str, Any],
        *,
        user_agent: str = "",
        request_host: str = "",
    ) -> Dict[str, Any]:
        visitor_id = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("visitorId") or ""))[:80]
        session_id = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("sessionId") or ""))[:80]
        route = normalize_analytics_route(payload.get("route"))
        previous_route = normalize_analytics_route(payload.get("previousRoute"))
        referrer_url = str(payload.get("referrerUrl") or "").strip()[:1000]
        page_label = str(payload.get("pageLabel") or "").strip()[:120]
        exclude_from_stats = bool(payload.get("excludeFromStats"))
        if not visitor_id or not session_id or not route:
            return {"tracked": False}

        timestamp = now_iso()
        request_host = str(request_host or "").split(":", 1)[0].strip().lower()
        with self._connect() as conn:
            latest = conn.execute(
                """
                SELECT route, previous_route, created_at
                FROM site_visit_events
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            latest_at = parse_iso_datetime(latest["created_at"]) if latest else None
            if latest and latest["route"] == route and (latest["previous_route"] or "") == previous_route and latest_at:
                if abs((parse_iso_datetime(timestamp) - latest_at).total_seconds()) < 5:
                    return {"tracked": False}

            source_meta = self._classify_visit_source(referrer_url, previous_route, request_host)
            referrer_path = normalize_analytics_route(urlparse(referrer_url).path if referrer_url else "")
            if referrer_path.startswith("/admin") or looks_like_test_identity(visitor_id, session_id):
                exclude_from_stats = True
            conn.execute(
                """
                INSERT INTO site_visit_events (
                    id, visitor_id, session_id, route, page_label, referrer_url, referrer_domain,
                    source_type, source_label, search_keyword, previous_route, user_agent, device_type, exclude_from_stats, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"visit_{uuid4().hex}",
                    visitor_id,
                    session_id,
                    route,
                    page_label or self._analytics_page_label(conn, route),
                    source_meta["referrerUrl"],
                    source_meta["referrerDomain"],
                    source_meta["sourceType"],
                    source_meta["sourceLabel"],
                    source_meta["searchKeyword"],
                    previous_route,
                    user_agent[:500],
                    self._device_type(user_agent),
                    bool_to_int(exclude_from_stats),
                    timestamp,
                ),
            )
            conn.commit()
        return {"tracked": True}

    def _analytics_page_label(self, conn: sqlite3.Connection, route: str) -> str:
        normalized = normalize_analytics_route(route)
        if normalized == "/":
            return "홈"
        if normalized == "/products":
            return "상품 목록"
        if normalized == "/charge":
            return "충전"
        if normalized == "/orders":
            return "주문 내역"
        if normalized == "/my":
            return "마이 페이지"
        if normalized.startswith("/products/"):
            category_id = normalized.split("/", 2)[2]
            row = conn.execute("SELECT name FROM product_categories WHERE id = ?", (category_id,)).fetchone()
            if row is not None:
                return str(row["name"])
            return "상품 상세"
        return normalized

    def _extract_search_keyword(self, referrer_url: str) -> str:
        if not referrer_url:
            return ""
        parsed = urlparse(referrer_url if re.match(r"^https?://", referrer_url, re.IGNORECASE) else f"https://{referrer_url}")
        query = parse_qs(parsed.query)
        for key in ("q", "query", "p", "keyword", "search_query"):
            values = query.get(key)
            if values:
                return str(values[0]).strip()[:120]
        return ""

    def _classify_visit_source(self, referrer_url: str, previous_route: str, request_host: str) -> Dict[str, str]:
        normalized_previous = normalize_analytics_route(previous_route)
        if normalized_previous:
            return {
                "referrerUrl": "",
                "referrerDomain": "",
                "sourceType": "internal",
                "sourceLabel": "내부 이동",
                "searchKeyword": "",
            }

        raw_referrer = str(referrer_url or "").strip()
        if not raw_referrer:
            return {
                "referrerUrl": "",
                "referrerDomain": "",
                "sourceType": "direct",
                "sourceLabel": "직접 방문",
                "searchKeyword": "",
            }

        parsed = urlparse(raw_referrer if re.match(r"^https?://", raw_referrer, re.IGNORECASE) else f"https://{raw_referrer}")
        domain = canonical_domain(parsed.hostname or "")
        local_host = canonical_domain(request_host)
        if local_host and domain == local_host:
            return {
                "referrerUrl": raw_referrer,
                "referrerDomain": domain,
                "sourceType": "internal",
                "sourceLabel": "내부 이동",
                "searchKeyword": "",
            }

        for pattern, (source_type, label) in SEARCH_REFERRER_LABELS.items():
            if pattern in domain:
                return {
                    "referrerUrl": raw_referrer,
                    "referrerDomain": domain,
                    "sourceType": source_type,
                    "sourceLabel": label,
                    "searchKeyword": self._extract_search_keyword(raw_referrer),
                }

        for pattern, (source_type, label) in SOCIAL_REFERRER_LABELS.items():
            if pattern in domain:
                return {
                    "referrerUrl": raw_referrer,
                    "referrerDomain": domain,
                    "sourceType": source_type,
                    "sourceLabel": label,
                    "searchKeyword": "",
                }

        return {
            "referrerUrl": raw_referrer,
            "referrerDomain": domain,
            "sourceType": "referral",
            "sourceLabel": domain or "외부 추천",
            "searchKeyword": "",
        }

    def _device_type(self, user_agent: str) -> str:
        ua = str(user_agent or "").lower()
        if not ua:
            return "desktop"
        if "ipad" in ua or "tablet" in ua:
            return "tablet"
        if any(keyword in ua for keyword in ("iphone", "android", "mobile", "samsungbrowser")):
            return "mobile"
        return "desktop"

    def _should_exclude_analytics_visit(self, row: Dict[str, Any]) -> bool:
        if bool(row.get("exclude_from_stats")):
            return True
        return looks_like_test_identity(row.get("visitor_id"), row.get("session_id"))

    def _should_exclude_analytics_order(self, row: Dict[str, Any]) -> bool:
        if str(row.get("user_id") or "") == DEMO_USER_ID:
            return True
        if str(row.get("customer_role") or "") != "customer":
            return True
        return looks_like_test_identity(row.get("customer_email"), row.get("customer_name"))

    def _analytics_window_payload(
        self,
        day_count: int,
        cutoff_date: dt.date,
        visits: List[Dict[str, Any]],
        orders: List[Dict[str, Any]],
        visitor_first_dates: Dict[str, dt.date],
    ) -> Dict[str, Any]:
        label_map = {
            "search": "검색",
            "social": "SNS",
            "direct": "직접",
            "referral": "추천",
            "internal": "내부 이동",
        }
        window_visits = [row for row in visits if row["_date"] >= cutoff_date]
        window_orders = [row for row in orders if row["_date"] >= cutoff_date]
        unique_visitors = {row["visitor_id"] for row in window_visits if row["visitor_id"]}
        unique_sessions = {row["session_id"] for row in window_visits if row["session_id"]}
        new_visitors = {
            visitor_id
            for visitor_id in unique_visitors
            if visitor_first_dates.get(visitor_id) and visitor_first_dates[visitor_id] >= cutoff_date
        }
        returning_visitors = unique_visitors - new_visitors

        customer_orders: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        page_buckets: Dict[str, Dict[str, Any]] = {}
        source_buckets: Dict[str, Dict[str, Any]] = {}
        source_type_counter: Counter[str] = Counter()
        keyword_counter: Counter[str] = Counter()
        entry_page_buckets: Dict[str, Dict[str, Any]] = {}
        transition_counter: Dict[tuple[str, str], Dict[str, Any]] = {}
        device_counter: Counter[str] = Counter()
        platform_buckets: Dict[str, Dict[str, Any]] = {}
        product_buckets: Dict[str, Dict[str, Any]] = {}

        for row in window_visits:
            page_key = row["route"] or "/"
            bucket = page_buckets.setdefault(
                page_key,
                {"route": page_key, "pageLabel": row["page_label"] or page_key, "views": 0, "visitors": set()},
            )
            bucket["views"] += 1
            if row["visitor_id"]:
                bucket["visitors"].add(row["visitor_id"])

            source_type = str(row["source_type"] or "direct")
            source_type_counter[source_type] += 1
            device_counter[str(row["device_type"] or "desktop")] += 1

            if source_type != "internal":
                source_key = str(row["referrer_domain"] or source_type)
                source_bucket = source_buckets.setdefault(
                    source_key,
                    {
                        "domain": source_key,
                        "label": row["source_label"] or source_key or "직접 방문",
                        "sourceType": source_type,
                        "visits": 0,
                        "visitors": set(),
                        "sessions": set(),
                    },
                )
                source_bucket["visits"] += 1
                if row["visitor_id"]:
                    source_bucket["visitors"].add(row["visitor_id"])
                if row["session_id"]:
                    source_bucket["sessions"].add(row["session_id"])

            if row["search_keyword"]:
                keyword_counter[str(row["search_keyword"])] += 1

            if row["session_id"]:
                current_entry = entry_page_buckets.get(row["session_id"])
                if current_entry is None or row["_dt"] < current_entry["_dt"]:
                    entry_page_buckets[row["session_id"]] = {
                        "_dt": row["_dt"],
                        "route": row["route"] or "/",
                        "pageLabel": row["page_label"] or row["route"] or "/",
                    }

            if row["previous_route"]:
                key = (row["previous_route"], row["route"])
                transition_bucket = transition_counter.setdefault(
                    key,
                    {
                        "fromRoute": row["previous_route"],
                        "fromLabel": row["previous_route"],
                        "toRoute": row["route"],
                        "toLabel": row["page_label"] or row["route"],
                        "hits": 0,
                    },
                )
                transition_bucket["hits"] += 1

        for row in window_orders:
            customer_orders[str(row["user_id"])].append(row)
            platform_bucket = platform_buckets.setdefault(
                str(row["platform_name"] or "기타"),
                {"name": str(row["platform_name"] or "기타"), "orders": 0, "sales": 0, "customers": set()},
            )
            platform_bucket["orders"] += 1
            platform_bucket["sales"] += int(row["total_price"] or 0)
            if row["user_id"]:
                platform_bucket["customers"].add(row["user_id"])

            product_key = str(row["product_id"] or row["product_name_snapshot"] or "")
            product_bucket = product_buckets.setdefault(
                product_key,
                {
                    "productId": str(row["product_id"] or ""),
                    "productName": str(row["product_name_snapshot"] or "상품"),
                    "orders": 0,
                    "sales": 0,
                    "customers": set(),
                },
            )
            product_bucket["orders"] += 1
            product_bucket["sales"] += int(row["total_price"] or 0)
            if row["user_id"]:
                product_bucket["customers"].add(row["user_id"])

        customer_profiles = []
        gap_samples: List[float] = []
        repeat_customers = set()
        for customer_id, items in customer_orders.items():
            sorted_items = sorted(items, key=lambda item: item["_dt"])
            order_count = len(sorted_items)
            total_sales = sum(int(item["total_price"] or 0) for item in sorted_items)
            if order_count >= 2:
                repeat_customers.add(customer_id)
            customer_gap_days: List[int] = []
            for index in range(1, order_count):
                gap = (sorted_items[index]["_date"] - sorted_items[index - 1]["_date"]).days
                customer_gap_days.append(gap)
                gap_samples.append(gap)
            customer_profiles.append(
                {
                    "customerId": customer_id,
                    "customerName": sorted_items[0]["customer_name"],
                    "customerRole": sorted_items[0]["customer_role"],
                    "orders": order_count,
                    "sales": total_sales,
                    "avgOrderValue": round(total_sales / order_count) if order_count else 0,
                    "avgGapDays": round(sum(customer_gap_days) / len(customer_gap_days), 1) if customer_gap_days else 0,
                    "firstOrderAt": sorted_items[0]["created_at"],
                    "lastOrderAt": sorted_items[-1]["created_at"],
                    "isRepeat": order_count >= 2,
                }
            )

        repurchase_bands = [
            {"label": "1회 구매", "customers": 0},
            {"label": "2회 구매", "customers": 0},
            {"label": "3회 구매", "customers": 0},
            {"label": "4회 이상", "customers": 0},
        ]
        for item in customer_profiles:
            if item["orders"] >= 4:
                repurchase_bands[3]["customers"] += 1
            else:
                repurchase_bands[item["orders"] - 1]["customers"] += 1

        repeat_product_buckets: Dict[str, Dict[str, Any]] = {}
        for row in window_orders:
            if str(row["user_id"]) not in repeat_customers:
                continue
            product_key = str(row["product_id"] or row["product_name_snapshot"] or "")
            product_bucket = repeat_product_buckets.setdefault(
                product_key,
                {
                    "productId": str(row["product_id"] or ""),
                    "productName": str(row["product_name_snapshot"] or "상품"),
                    "repeatOrders": 0,
                    "repeatCustomers": set(),
                    "sales": 0,
                },
            )
            product_bucket["repeatOrders"] += 1
            product_bucket["sales"] += int(row["total_price"] or 0)
            product_bucket["repeatCustomers"].add(row["user_id"])

        unique_customers = {row["user_id"] for row in window_orders if row["user_id"]}
        total_sales = sum(int(row["total_price"] or 0) for row in window_orders)
        total_orders = len(window_orders)

        entry_page_counts: Dict[str, Dict[str, Any]] = {}
        for candidate in entry_page_buckets.values():
            bucket = entry_page_counts.setdefault(
                candidate["route"],
                {"route": candidate["route"], "pageLabel": candidate["pageLabel"], "sessions": 0},
            )
            bucket["sessions"] += 1

        return {
            "rangeDays": day_count,
            "overview": {
                "pageViews": len(window_visits),
                "uniqueVisitors": len(unique_visitors),
                "sessions": len(unique_sessions),
                "newVisitors": len(new_visitors),
                "returningVisitors": len(returning_visitors),
                "orders": total_orders,
                "sales": total_sales,
                "avgOrderValue": round(total_sales / total_orders) if total_orders else 0,
                "uniqueCustomers": len(unique_customers),
                "conversionRate": round((total_orders / len(unique_visitors)) * 100, 2) if unique_visitors else 0,
                "repeatRate": round((len(repeat_customers) / len(unique_customers)) * 100, 2) if unique_customers else 0,
                "returningVisitorRate": round((len(returning_visitors) / len(unique_visitors)) * 100, 2) if unique_visitors else 0,
                "avgOrdersPerCustomer": round(total_orders / len(unique_customers), 2) if unique_customers else 0,
                "avgGapDays": round(sum(gap_samples) / len(gap_samples), 1) if gap_samples else 0,
            },
            "topPages": [
                {
                    "route": item["route"],
                    "pageLabel": item["pageLabel"],
                    "views": item["views"],
                    "visitors": len(item["visitors"]),
                }
                for item in sorted(page_buckets.values(), key=lambda item: (-item["views"], item["pageLabel"]))[:8]
            ],
            "sourceDomains": [
                {
                    "domain": item["domain"] or "direct",
                    "label": item["label"],
                    "sourceType": item["sourceType"],
                    "visits": item["visits"],
                    "visitors": len(item["visitors"]),
                    "sessions": len(item["sessions"]),
                }
                for item in sorted(source_buckets.values(), key=lambda item: (-item["visits"], item["label"]))[:10]
            ],
            "sourceTypes": [
                {"type": key, "label": label_map.get(key, key), "visits": value}
                for key, value in source_type_counter.most_common()
            ],
            "searchKeywords": [
                {"keyword": keyword, "visits": visits}
                for keyword, visits in keyword_counter.most_common(10)
            ],
            "entryPages": sorted(entry_page_counts.values(), key=lambda item: (-item["sessions"], item["pageLabel"]))[:10],
            "pathTransitions": sorted(transition_counter.values(), key=lambda item: (-item["hits"], item["fromRoute"]))[:10],
            "deviceBreakdown": [
                {
                    "device": key,
                    "label": {"desktop": "데스크톱", "mobile": "모바일", "tablet": "태블릿"}.get(key, key),
                    "visits": value,
                    "sharePercent": round((value / len(window_visits)) * 100, 2) if window_visits else 0,
                }
                for key, value in device_counter.most_common()
            ],
            "salesByPlatform": [
                {
                    "name": item["name"],
                    "orders": item["orders"],
                    "sales": item["sales"],
                    "customers": len(item["customers"]),
                }
                for item in sorted(platform_buckets.values(), key=lambda item: (-item["sales"], item["name"]))[:8]
            ],
            "salesByProduct": [
                {
                    "productId": item["productId"],
                    "productName": item["productName"],
                    "orders": item["orders"],
                    "sales": item["sales"],
                    "customers": len(item["customers"]),
                }
                for item in sorted(product_buckets.values(), key=lambda item: (-item["sales"], item["productName"]))[:10]
            ],
            "repurchaseSummary": {
                "customersWithOrders": len(unique_customers),
                "repeatCustomers": len(repeat_customers),
                "repeatRate": round((len(repeat_customers) / len(unique_customers)) * 100, 2) if unique_customers else 0,
                "avgOrdersPerCustomer": round(total_orders / len(unique_customers), 2) if unique_customers else 0,
                "avgGapDays": round(sum(gap_samples) / len(gap_samples), 1) if gap_samples else 0,
            },
            "repurchaseCustomers": sorted(
                customer_profiles,
                key=lambda item: (-int(item["isRepeat"]), -item["orders"], -item["sales"], item["customerName"]),
            )[:12],
            "repurchaseBands": repurchase_bands,
            "repurchaseProducts": [
                {
                    "productId": item["productId"],
                    "productName": item["productName"],
                    "repeatOrders": item["repeatOrders"],
                    "repeatCustomers": len(item["repeatCustomers"]),
                    "sales": item["sales"],
                }
                for item in sorted(repeat_product_buckets.values(), key=lambda item: (-item["repeatOrders"], -item["sales"]))[:10]
            ],
        }

    def _admin_analytics_payload(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        today = dt.datetime.now().astimezone().date()
        dates = [today - dt.timedelta(days=offset) for offset in range(ANALYTICS_LOOKBACK_DAYS - 1, -1, -1)]
        visits = []
        visitor_first_dates: Dict[str, dt.date] = {}
        for row in conn.execute("SELECT * FROM site_visit_events ORDER BY created_at ASC").fetchall():
            parsed = parse_iso_datetime(row["created_at"])
            if parsed is None:
                continue
            item = dict(row)
            if self._should_exclude_analytics_visit(item):
                continue
            item["_dt"] = parsed
            item["_date"] = parsed.astimezone().date() if parsed.tzinfo else parsed.date()
            visitor_id = str(item.get("visitor_id") or "")
            if visitor_id and visitor_id not in visitor_first_dates:
                visitor_first_dates[visitor_id] = item["_date"]
            visits.append(item)

        orders = []
        for row in conn.execute(
            """
            SELECT
                o.*,
                u.name AS customer_name,
                u.email AS customer_email,
                u.role AS customer_role,
                ps.display_name AS platform_name
            FROM orders o
            JOIN users u ON u.id = o.user_id
            JOIN platform_sections ps ON ps.id = o.platform_section_id
            ORDER BY o.created_at ASC
            """
        ).fetchall():
            parsed = parse_iso_datetime(row["created_at"])
            if parsed is None:
                continue
            item = dict(row)
            if self._should_exclude_analytics_order(item):
                continue
            item["_dt"] = parsed
            item["_date"] = parsed.astimezone().date() if parsed.tzinfo else parsed.date()
            orders.append(item)

        traffic_buckets: Dict[str, Dict[str, Any]] = {
            date_key(current): {
                "date": date_key(current),
                "label": current.strftime("%m.%d"),
                "pageViews": 0,
                "visitors": set(),
                "sessions": set(),
                "newVisitors": set(),
                "returningVisitors": set(),
            }
            for current in dates
        }
        sales_buckets: Dict[str, Dict[str, Any]] = {
            date_key(current): {
                "orders": 0,
                "customers": set(),
                "sales": 0,
                "quantity": 0,
            }
            for current in dates
        }

        for row in visits:
            bucket = traffic_buckets.get(date_key(row["_date"]))
            if bucket is None:
                continue
            bucket["pageViews"] += 1
            if row["visitor_id"]:
                bucket["visitors"].add(row["visitor_id"])
                if visitor_first_dates.get(row["visitor_id"]) == row["_date"]:
                    bucket["newVisitors"].add(row["visitor_id"])
                else:
                    bucket["returningVisitors"].add(row["visitor_id"])
            if row["session_id"]:
                bucket["sessions"].add(row["session_id"])

        for row in orders:
            bucket = sales_buckets.get(date_key(row["_date"]))
            if bucket is None:
                continue
            bucket["orders"] += 1
            bucket["sales"] += int(row["total_price"] or 0)
            bucket["quantity"] += int(row["quantity"] or 0)
            if row["user_id"]:
                bucket["customers"].add(row["user_id"])

        daily_overview = []
        for current in dates:
            bucket_key = date_key(current)
            traffic_bucket = traffic_buckets[bucket_key]
            sales_bucket = sales_buckets[bucket_key]
            visitor_count = len(traffic_bucket["visitors"])
            order_count = int(sales_bucket["orders"])
            sales_total = int(sales_bucket["sales"])
            daily_overview.append(
                {
                    "date": bucket_key,
                    "label": traffic_bucket["label"],
                    "pageViews": int(traffic_bucket["pageViews"]),
                    "visitors": visitor_count,
                    "sessions": len(traffic_bucket["sessions"]),
                    "newVisitors": len(traffic_bucket["newVisitors"]),
                    "returningVisitors": len(traffic_bucket["returningVisitors"]),
                    "orders": order_count,
                    "customers": len(sales_bucket["customers"]),
                    "sales": sales_total,
                    "quantity": int(sales_bucket["quantity"]),
                    "avgOrderValue": round(sales_total / order_count) if order_count else 0,
                    "conversionRate": round((order_count / visitor_count) * 100, 2) if visitor_count else 0,
                }
            )

        windows = {}
        for day_count in (7, 30, 90):
            cutoff_date = today - dt.timedelta(days=day_count - 1)
            windows[f"{day_count}d"] = self._analytics_window_payload(
                day_count,
                cutoff_date,
                visits,
                orders,
                visitor_first_dates,
            )

        return {
            "generatedAt": now_iso(),
            "dailyOverview": daily_overview,
            "windows": windows,
        }

    def admin_bootstrap(self) -> Dict[str, Any]:
        with self._connect() as conn:
            popup_row = conn.execute("SELECT * FROM home_popups ORDER BY updated_at DESC LIMIT 1").fetchone()
            banner_rows = conn.execute("SELECT * FROM home_banners ORDER BY sort_order, id").fetchall()
            site_settings_row = self._site_settings_row(conn)
            analytics = self._admin_analytics_payload(conn)
            supplier_rows = conn.execute(
                """
                SELECT
                    s.*,
                    COUNT(DISTINCT ss.id) AS service_count,
                    COUNT(DISTINCT psm.id) AS mapping_count
                FROM suppliers s
                LEFT JOIN supplier_services ss ON ss.supplier_id = s.id
                LEFT JOIN product_supplier_mappings psm ON psm.supplier_id = s.id
                GROUP BY s.id
                ORDER BY s.created_at DESC
                """
            ).fetchall()

            suppliers = [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "apiUrl": row["api_url"],
                    "integrationType": normalize_supplier_integration_type(row["integration_type"]),
                    "hasApiKey": bool(row["api_key"]),
                    "apiKeyMasked": mask_secret(row["api_key"]),
                    "hasBearerToken": bool(row["bearer_token"]),
                    "bearerTokenMasked": mask_secret(row["bearer_token"]),
                    "supportsBalanceCheck": supplier_supports_balance_check(row["integration_type"]),
                    "supportsAutoDispatch": supplier_supports_auto_dispatch(row["integration_type"]),
                    "isActive": bool(row["is_active"]),
                    "notes": row["notes"],
                    "lastTestStatus": row["last_test_status"],
                    "lastTestMessage": row["last_test_message"],
                    "lastBalance": row["last_balance"],
                    "lastCurrency": row["last_currency"],
                    "lastServiceCount": row["last_service_count"],
                    "lastCheckedAt": row["last_checked_at"],
                    "serviceCount": row["service_count"],
                    "mappingCount": row["mapping_count"],
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
                for row in supplier_rows
            ]

            customer_rows = conn.execute(
                """
                SELECT
                    u.*,
                    COUNT(o.id) AS order_count,
                    COALESCE(SUM(o.total_price), 0) AS total_spent,
                    MAX(o.created_at) AS last_order_at
                FROM users u
                LEFT JOIN orders o ON o.user_id = u.id
                GROUP BY u.id
                ORDER BY CASE WHEN u.role = 'admin' THEN 0 ELSE 1 END, u.created_at DESC
                """
            ).fetchall()

            customers = [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "emailMasked": mask_email(row["email"]),
                    "phoneMasked": mask_phone(row["phone"]),
                    "tier": row["tier"],
                    "role": row["role"],
                    "avatarLabel": row["avatar_label"],
                    "balance": row["balance"],
                    "balanceLabel": money(row["balance"]),
                    "isActive": bool(row["is_active"]),
                    "hasPassword": bool(row["password_hash"]),
                    "notes": row["notes"],
                    "lastLoginAt": row["last_login_at"],
                    "orderCount": row["order_count"],
                    "totalSpent": row["total_spent"],
                    "totalSpentLabel": money(row["total_spent"]),
                    "lastOrderAt": row["last_order_at"] or "",
                    "lastOrderLabel": self._relative_date_label(row["last_order_at"]) if row["last_order_at"] else "",
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
                for row in customer_rows
            ]

            group_rows = conn.execute(
                """
                SELECT
                    pg.id,
                    pg.name,
                    pg.description,
                    ps.id AS platform_id,
                    ps.display_name AS platform_name
                FROM platform_groups pg
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                ORDER BY ps.sort_order, pg.sort_order
                """
            ).fetchall()

            platform_groups = [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "platformId": row["platform_id"],
                    "platformName": row["platform_name"],
                }
                for row in group_rows
            ]

            category_rows = conn.execute(
                """
                SELECT
                    pc.*,
                    pg.name AS group_name,
                    pg.id AS group_id,
                    ps.id AS platform_id,
                    ps.display_name AS platform_name,
                    COUNT(p.id) AS product_count,
                    SUM(CASE WHEN p.is_active = 1 THEN 1 ELSE 0 END) AS active_product_count
                FROM product_categories pc
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                LEFT JOIN products p ON p.product_category_id = pc.id
                GROUP BY pc.id
                ORDER BY ps.sort_order, pg.sort_order, pc.sort_order
                """
            ).fetchall()

            categories = [
                {
                    "id": row["id"],
                    "groupId": row["group_id"],
                    "groupName": row["group_name"],
                    "platformId": row["platform_id"],
                    "platformName": row["platform_name"],
                    "name": row["name"],
                    "description": row["description"],
                    "optionLabelName": row["option_label_name"],
                    "heroTitle": row["hero_title"],
                    "heroSubtitle": row["hero_subtitle"],
                    "serviceDescriptionHtml": row["service_description_html"],
                    "cautionText": "\n".join(parse_json(row["caution_json"], [])),
                    "refundText": "\n".join(parse_json(row["refund_notice_json"], [])),
                    "isActive": bool(row["is_active"]),
                    "productCount": row["product_count"],
                    "activeProductCount": row["active_product_count"] or 0,
                    "sortOrder": row["sort_order"],
                }
                for row in category_rows
            ]

            product_rows = conn.execute(
                """
                SELECT
                    p.id AS product_id,
                    p.name AS product_name,
                    p.menu_name,
                    p.option_name,
                    p.product_code,
                    p.price,
                    p.min_amount,
                    p.max_amount,
                    p.step_amount,
                    p.price_strategy,
                    p.unit_label,
                    p.is_discounted,
                    p.estimated_turnaround,
                    p.badge,
                    p.form_structure_json,
                    p.is_active AS product_is_active,
                    p.sort_order,
                    pc.id AS category_id,
                    pc.name AS category_name,
                    pc.is_active AS category_is_active,
                    pg.id AS group_id,
                    pg.name AS group_name,
                    ps.display_name AS platform_name,
                    psm.id AS mapping_id,
                    psm.supplier_id,
                    psm.supplier_service_id,
                    psm.supplier_external_service_id,
                    psm.pricing_mode,
                    psm.price_multiplier,
                    psm.fixed_markup,
                    s.name AS supplier_name,
                    ss.name AS supplier_service_name
                FROM products p
                JOIN product_categories pc ON pc.id = p.product_category_id
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                LEFT JOIN product_supplier_mappings psm ON psm.product_id = p.id AND psm.is_primary = 1
                LEFT JOIN suppliers s ON s.id = psm.supplier_id
                LEFT JOIN supplier_services ss ON ss.id = psm.supplier_service_id
                ORDER BY ps.sort_order, pc.sort_order, p.sort_order
                """
            ).fetchall()

            internal_products = [
                {
                    "id": row["product_id"],
                    "name": row["product_name"],
                    "menuName": row["menu_name"],
                    "optionName": row["option_name"],
                    "productCode": row["product_code"],
                    "price": row["price"],
                    "priceLabel": money(row["price"]),
                    "minAmount": row["min_amount"],
                    "maxAmount": row["max_amount"],
                    "stepAmount": row["step_amount"],
                    "priceStrategy": row["price_strategy"],
                    "unitLabel": row["unit_label"],
                    "isDiscounted": bool(row["is_discounted"]),
                    "estimatedTurnaround": row["estimated_turnaround"],
                    "badge": row["badge"],
                    "sortOrder": row["sort_order"],
                    "categoryId": row["category_id"],
                    "categoryName": row["category_name"],
                    "groupId": row["group_id"],
                    "groupName": row["group_name"],
                    "platformName": row["platform_name"],
                    "isActive": bool(row["product_is_active"]) and bool(row["category_is_active"]),
                    "formConfig": admin_form_config(parse_json(row["form_structure_json"], {})),
                    "mapping": {
                        "id": row["mapping_id"],
                        "supplierId": row["supplier_id"],
                        "supplierServiceId": row["supplier_service_id"],
                        "supplierExternalServiceId": row["supplier_external_service_id"],
                        "supplierName": row["supplier_name"],
                        "supplierServiceName": row["supplier_service_name"],
                        "pricingMode": row["pricing_mode"],
                        "priceMultiplier": row["price_multiplier"],
                        "fixedMarkup": row["fixed_markup"],
                    }
                    if row["mapping_id"]
                    else None,
                }
                for row in product_rows
            ]

            admin_order_rows = conn.execute(
                """
                SELECT
                    o.*,
                    u.name AS customer_name,
                    u.email AS customer_email,
                    u.role AS customer_role,
                    ps.display_name AS platform_name,
                    ps.icon AS platform_icon,
                    so.status AS supplier_status,
                    so.supplier_external_order_id,
                    s.name AS supplier_name
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN platform_sections ps ON ps.id = o.platform_section_id
                LEFT JOIN supplier_orders so ON so.order_id = o.id
                LEFT JOIN suppliers s ON s.id = so.supplier_id
                ORDER BY o.created_at DESC
                LIMIT 60
                """
            ).fetchall()

            admin_orders = [
                {
                    "id": row["id"],
                    "orderNumber": row["order_number"],
                    "customerId": row["user_id"],
                    "customerName": row["customer_name"],
                    "customerEmailMasked": mask_email(row["customer_email"]),
                    "customerRole": row["customer_role"],
                    "platformName": row["platform_name"],
                    "platformIcon": row["platform_icon"],
                    "productName": row["product_name_snapshot"],
                    "optionName": row["option_name_snapshot"],
                    "targetValue": row["target_value"],
                    "quantity": row["quantity"],
                    "totalPrice": row["total_price"],
                    "totalPriceLabel": money(row["total_price"]),
                    "status": row["status"],
                    "notes": parse_json(row["notes_json"], {}),
                    "supplierStatus": row["supplier_status"] or "",
                    "supplierName": row["supplier_name"] or "",
                    "supplierExternalOrderId": row["supplier_external_order_id"] or "",
                    "createdAt": row["created_at"],
                    "createdLabel": self._relative_date_label(row["created_at"]),
                }
                for row in admin_order_rows
            ]

            mapped_product_count = sum(1 for item in internal_products if item["mapping"])
            total_service_count = sum(int(item["serviceCount"]) for item in suppliers)
            active_suppliers = sum(1 for item in suppliers if item["isActive"])
            active_customers = sum(1 for item in customers if item["isActive"] and item["role"] == "customer")
            active_products = sum(1 for item in internal_products if item["isActive"])
            analytics_overview = analytics.get("windows", {}).get("30d", {}).get("overview", {})

            return {
                "siteSettings": self._site_settings_admin_payload(site_settings_row),
                "popup": self._popup_admin_payload(popup_row) if popup_row else None,
                "homeBanners": [self._home_banner_payload(row) for row in banner_rows],
                "analytics": analytics,
                "suppliers": suppliers,
                "customers": customers,
                "platformGroups": platform_groups,
                "categories": categories,
                "internalProducts": internal_products,
                "adminOrders": admin_orders,
                "stats": {
                    "supplierCount": len(suppliers),
                    "activeSupplierCount": active_suppliers,
                    "syncedServiceCount": total_service_count,
                    "mappedProductCount": mapped_product_count,
                    "customerCount": sum(1 for item in customers if item["role"] == "customer"),
                    "activeCustomerCount": active_customers,
                    "productCount": len(internal_products),
                    "activeProductCount": active_products,
                    "orderCount": len(admin_orders),
                    "visitorCount": int(analytics_overview.get("uniqueVisitors") or 0),
                    "salesTotal": int(analytics_overview.get("sales") or 0),
                },
            }

    def list_supplier_services(self, supplier_id: str, search: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            supplier = conn.execute("SELECT id, name, integration_type FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
            if supplier is None:
                raise PanelError("공급사를 찾을 수 없습니다.", status=404)

            query = """
                SELECT *
                FROM supplier_services
                WHERE supplier_id = ?
            """
            params: List[Any] = [supplier_id]
            if search.strip():
                query += " AND LOWER(name || ' ' || category || ' ' || external_service_id) LIKE ?"
                params.append(f"%{search.strip().lower()}%")
            query += " ORDER BY category, name"

            services = [
                self._supplier_service_payload(row, supplier["integration_type"])
                for row in conn.execute(query, params).fetchall()
            ]

        return {
            "supplier": {"id": supplier["id"], "name": supplier["name"]},
            "services": services,
            "search": search,
        }

    def _supplier_service_payload(self, row: sqlite3.Row, integration_type: str) -> Dict[str, Any]:
        raw_payload = parse_json(row["raw_json"], {})
        payload = {
            "id": row["id"],
            "externalServiceId": row["external_service_id"],
            "name": row["name"],
            "category": row["category"],
            "type": row["type"],
            "rate": row["rate"],
            "rateLabel": f"{row['rate']}",
            "minAmount": row["min_amount"],
            "maxAmount": row["max_amount"],
            "dripfeed": bool(row["dripfeed"]),
            "refill": bool(row["refill"]),
            "cancel": bool(row["cancel"]),
            "syncedAt": row["synced_at"],
            "requestGuide": supplier_service_request_guide(
                integration_type,
                {
                    "externalServiceId": row["external_service_id"],
                    "name": row["name"],
                    "category": row["category"],
                    "type": row["type"],
                    "minAmount": row["min_amount"],
                    "maxAmount": row["max_amount"],
                    "dripfeed": bool(row["dripfeed"]),
                    "refill": bool(row["refill"]),
                    "cancel": bool(row["cancel"]),
                },
                raw_payload if isinstance(raw_payload, dict) else {},
            ),
        }
        return payload

    def save_supplier(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        api_url = str(payload.get("apiUrl") or "").strip()
        integration_type = normalize_supplier_integration_type(payload.get("integrationType"))
        api_key = str(payload.get("apiKey") or "").strip()
        bearer_token = str(payload.get("bearerToken") or "").strip()
        notes = str(payload.get("notes") or "").strip()
        is_active = bool(payload.get("isActive", True))

        if not name:
            raise PanelError("공급사 이름을 입력해 주세요.")
        if not api_url:
            raise PanelError("API URL을 입력해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            existing = None
            integration_changed = False
            if supplier_id:
                existing = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
                if existing is None:
                    raise PanelError("수정할 공급사를 찾을 수 없습니다.", status=404)
                existing_type = normalize_supplier_integration_type(existing["integration_type"])
                integration_changed = existing_type != integration_type
                if not api_key and not integration_changed:
                    api_key = existing["api_key"]
                if integration_type == SUPPLIER_INTEGRATION_MKT24 and not bearer_token and not integration_changed:
                    bearer_token = existing["bearer_token"]
            if integration_type == SUPPLIER_INTEGRATION_MKT24:
                if not api_key:
                    raise PanelError("x-api-key를 입력해 주세요.")
                if not bearer_token:
                    raise PanelError("Bearer Token을 입력해 주세요.")
            else:
                if not api_key:
                    raise PanelError("API 키를 입력해 주세요.")
                bearer_token = ""

            if supplier_id and existing is not None:
                conn.execute(
                    """
                    UPDATE suppliers
                    SET name = ?, api_url = ?, integration_type = ?, api_key = ?, bearer_token = ?, is_active = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        api_url,
                        integration_type,
                        api_key,
                        bearer_token,
                        bool_to_int(is_active),
                        notes,
                        timestamp,
                        supplier_id,
                    ),
                )
            else:
                supplier_id = f"sup_{uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO suppliers (
                        id, name, api_url, integration_type, api_key, bearer_token, is_active, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        supplier_id,
                        name,
                        api_url,
                        integration_type,
                        api_key,
                        bearer_token,
                        bool_to_int(is_active),
                        notes,
                        timestamp,
                        timestamp,
                    ),
                )
            conn.commit()

        return {"supplier": self._supplier_by_id(supplier_id)}

    def save_home_popup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        popup_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip() or "홈 프로모션 팝업"
        badge_text = str(payload.get("badgeText") or "").strip()
        title = str(payload.get("title") or "").strip()
        description = str(payload.get("description") or "").strip()
        image_url = normalize_popup_image_source(payload.get("imageUrl") or "")
        route = normalize_navigation_target(payload.get("route") or "/")
        theme = str(payload.get("theme") or "coral").strip().lower() or "coral"
        is_active = bool(payload.get("isActive", False))

        if not title:
            raise PanelError("팝업 제목을 입력해 주세요.")
        if theme not in {"coral", "midnight", "blue"}:
            theme = "coral"

        timestamp = now_iso()
        with self._connect() as conn:
            existing = None
            if popup_id:
                existing = conn.execute("SELECT id, created_at FROM home_popups WHERE id = ?", (popup_id,)).fetchone()
            if existing is None:
                existing = conn.execute("SELECT id, created_at FROM home_popups ORDER BY updated_at DESC LIMIT 1").fetchone()
                if existing is not None:
                    popup_id = existing["id"]
            if existing is None:
                popup_id = popup_id or default_home_popup_record()["id"]
                conn.execute(
                    """
                    INSERT INTO home_popups (
                        id, name, badge_text, title, description, image_url, route, theme, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        popup_id,
                        name,
                        badge_text,
                        title,
                        description,
                        image_url,
                        route,
                        theme,
                        bool_to_int(is_active),
                        timestamp,
                        timestamp,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE home_popups
                    SET name = ?, badge_text = ?, title = ?, description = ?, image_url = ?, route = ?, theme = ?, is_active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        badge_text,
                        title,
                        description,
                        image_url,
                        route,
                        theme,
                        bool_to_int(is_active),
                        timestamp,
                        popup_id,
                    ),
                )
            conn.commit()
        return {"popup": self._home_popup_by_id(popup_id)}

    def save_home_banner(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        banner_id = str(payload.get("id") or "").strip()
        title = str(payload.get("title") or "").strip()
        subtitle = str(payload.get("subtitle") or "").strip()
        cta_label = str(payload.get("ctaLabel") or "").strip() or "바로 보기"
        route = normalize_navigation_target(payload.get("route") or "/")
        image_url = normalize_image_asset_source(payload.get("imageUrl") or "", "홈 배너 이미지")
        theme = str(payload.get("theme") or "blue").strip().lower() or "blue"
        is_active = bool(payload.get("isActive", True))
        sort_order = int(payload.get("sortOrder") or 0)

        if not banner_id:
            raise PanelError("수정할 홈 배너를 선택해 주세요.")
        if not title:
            raise PanelError("배너 제목을 입력해 주세요.")
        if theme not in {"blue", "mint", "dark"}:
            theme = "blue"

        timestamp = now_iso()
        with self._connect() as conn:
            existing = conn.execute("SELECT id FROM home_banners WHERE id = ?", (banner_id,)).fetchone()
            if existing is None:
                raise PanelError("수정할 홈 배너를 찾을 수 없습니다.", status=404)
            conn.execute(
                """
                UPDATE home_banners
                SET title = ?, subtitle = ?, cta_label = ?, route = ?, image_url = ?, theme = ?, is_active = ?, sort_order = ?
                WHERE id = ?
                """,
                (
                    title,
                    subtitle,
                    cta_label,
                    route,
                    image_url,
                    theme,
                    bool_to_int(is_active),
                    sort_order,
                    banner_id,
                ),
            )
            conn.commit()
        return {"banner": self._home_banner_by_id(banner_id)}

    def save_site_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        site_name = str(payload.get("siteName") or "").strip()
        site_description = str(payload.get("siteDescription") or "").strip()
        use_mail_sms_site_name = bool(payload.get("useMailSmsSiteName", False))
        mail_sms_site_name = str(payload.get("mailSmsSiteName") or "").strip()
        favicon_url = normalize_image_asset_source(payload.get("faviconUrl") or "", "파비콘")
        share_image_url = normalize_image_asset_source(payload.get("shareImageUrl") or "", "대표 이미지")

        if not site_name:
            raise PanelError("사이트 이름을 입력해 주세요.")
        if not site_description:
            raise PanelError("사이트 설명을 입력해 주세요.")
        if len(site_name) > 80:
            raise PanelError("사이트 이름은 80자 이하로 입력해 주세요.")
        if len(site_description) > 240:
            raise PanelError("사이트 설명은 240자 이하로 입력해 주세요.")
        if len(mail_sms_site_name) > 60:
            raise PanelError("메일/SMS 전용 사이트 이름은 60자 이하로 입력해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            existing = self._site_settings_row(conn)
            conn.execute(
                """
                UPDATE site_settings
                SET site_name = ?, site_description = ?, use_mail_sms_site_name = ?, mail_sms_site_name = ?,
                    favicon_url = ?, share_image_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    site_name,
                    site_description,
                    bool_to_int(use_mail_sms_site_name),
                    mail_sms_site_name,
                    favicon_url,
                    share_image_url,
                    timestamp,
                    existing["id"],
                ),
            )
            conn.commit()
        return {"siteSettings": self.admin_site_settings()["siteSettings"]}

    def test_supplier_connection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("id") or "").strip()
        supplier = self._supplier_by_id(supplier_id, include_api_key=True) if supplier_id else None

        integration_type = normalize_supplier_integration_type(payload.get("integrationType") or (supplier["integrationType"] if supplier else ""))
        api_url = str(payload.get("apiUrl") or (supplier["apiUrl"] if supplier else "")).strip()
        api_key = str(payload.get("apiKey") or (supplier["apiKey"] if supplier else "")).strip()
        bearer_token = str(payload.get("bearerToken") or (supplier["bearerToken"] if supplier else "")).strip()

        if not api_url:
            raise PanelError("API URL을 입력해 주세요.")
        if not api_key:
            label = "x-api-key" if integration_type == SUPPLIER_INTEGRATION_MKT24 else "API 키"
            raise PanelError(f"{label}를 입력해 주세요.")
        if integration_type == SUPPLIER_INTEGRATION_MKT24 and not bearer_token:
            raise PanelError("Bearer Token을 입력해 주세요.")

        result = self._run_supplier_connection_test(
            api_url,
            api_key,
            integration_type=integration_type,
            bearer_token=bearer_token,
        )

        if supplier_id:
            persisted_api_url = result.get("persistedApiUrl") or result["resolvedApiUrl"]
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE suppliers
                    SET api_url = ?, integration_type = ?, api_key = ?, bearer_token = ?, last_test_status = ?, last_test_message = ?, last_balance = ?,
                        last_currency = ?, last_service_count = ?, last_checked_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        persisted_api_url,
                        integration_type,
                        api_key,
                        bearer_token if integration_type == SUPPLIER_INTEGRATION_MKT24 else "",
                        result["status"],
                        result["message"],
                        result["balance"],
                        result["currency"],
                        result["serviceCount"],
                        result["checkedAt"],
                        result["checkedAt"],
                        supplier_id,
                    ),
                )
                conn.commit()

        return {"result": result}

    def sync_supplier_services(self, supplier_id: str) -> Dict[str, Any]:
        supplier = self._supplier_by_id(supplier_id, include_api_key=True)
        result = self._run_supplier_connection_test(
            supplier["apiUrl"],
            supplier["apiKey"],
            integration_type=supplier["integrationType"],
            bearer_token=supplier.get("bearerToken") or "",
            require_services=True,
        )
        services_payload = result["servicesPayload"]
        synced_at = now_iso()

        if not isinstance(services_payload, list):
            raise PanelError("공급사 서비스 목록 형식이 올바르지 않습니다.")

        with self._connect() as conn:
            for item in services_payload:
                if not isinstance(item, dict):
                    continue
                service_record = supplier_service_record(supplier["integrationType"], item)
                if service_record is None:
                    continue
                external_service_id = service_record["externalServiceId"]
                row_id = conn.execute(
                    "SELECT id FROM supplier_services WHERE supplier_id = ? AND external_service_id = ?",
                    (supplier_id, external_service_id),
                ).fetchone()
                service_id = row_id["id"] if row_id else f"svc_{uuid4().hex[:12]}"
                values = (
                    service_id,
                    supplier_id,
                    external_service_id,
                    service_record["name"],
                    service_record["category"],
                    service_record["type"],
                    service_record["rate"],
                    service_record["minAmount"],
                    service_record["maxAmount"],
                    bool_to_int(service_record["dripfeed"]),
                    bool_to_int(service_record["refill"]),
                    bool_to_int(service_record["cancel"]),
                    service_record["rawJson"],
                    synced_at,
                )
                if row_id:
                    conn.execute(
                        """
                        UPDATE supplier_services
                        SET name = ?, category = ?, type = ?, rate = ?, min_amount = ?, max_amount = ?,
                            dripfeed = ?, refill = ?, cancel = ?, raw_json = ?, synced_at = ?
                        WHERE id = ?
                        """,
                        (
                            values[3],
                            values[4],
                            values[5],
                            values[6],
                            values[7],
                            values[8],
                            values[9],
                            values[10],
                            values[11],
                            values[12],
                            values[13],
                            service_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO supplier_services (
                            id, supplier_id, external_service_id, name, category, type, rate,
                            min_amount, max_amount, dripfeed, refill, cancel, raw_json, synced_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )

            persisted_api_url = result.get("persistedApiUrl") or result["resolvedApiUrl"]
            conn.execute(
                """
                UPDATE suppliers
                SET api_url = ?, last_test_status = 'success', last_test_message = ?, last_balance = ?, last_currency = ?,
                    last_service_count = ?, last_checked_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    persisted_api_url,
                    "서비스 동기화 완료",
                    result["balance"],
                    result["currency"],
                    result["serviceCount"],
                    synced_at,
                    synced_at,
                    supplier_id,
                ),
            )
            conn.commit()

        return {
            "supplier": self._supplier_by_id(supplier_id),
            "serviceCount": result["serviceCount"],
            "syncedAt": synced_at,
        }

    def save_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("productId") or "").strip()
        supplier_id = str(payload.get("supplierId") or "").strip()
        supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
        pricing_mode = str(payload.get("pricingMode") or "multiplier").strip() or "multiplier"
        price_multiplier = safe_float(payload.get("priceMultiplier"), 1.0)
        fixed_markup = int(float(payload.get("fixedMarkup") or 0) or 0)
        is_primary = bool(payload.get("isPrimary", True))

        if not product_id:
            raise PanelError("내부 상품을 선택해 주세요.")
        if not supplier_id or not supplier_service_id:
            raise PanelError("공급사와 공급사 서비스를 선택해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
            if product is None:
                raise PanelError("매핑할 내부 상품을 찾을 수 없습니다.", status=404)

            supplier_service = conn.execute(
                """
                SELECT id, external_service_id, supplier_id
                FROM supplier_services
                WHERE id = ? AND supplier_id = ?
                """,
                (supplier_service_id, supplier_id),
            ).fetchone()
            if supplier_service is None:
                raise PanelError("선택한 공급사 서비스 정보를 찾을 수 없습니다.", status=404)

            if is_primary:
                conn.execute("UPDATE product_supplier_mappings SET is_primary = 0 WHERE product_id = ?", (product_id,))

            existing = conn.execute(
                """
                SELECT id FROM product_supplier_mappings
                WHERE product_id = ? AND supplier_id = ? AND supplier_service_id = ?
                """,
                (product_id, supplier_id, supplier_service_id),
            ).fetchone()

            if existing:
                mapping_id = existing["id"]
                conn.execute(
                    """
                    UPDATE product_supplier_mappings
                    SET supplier_external_service_id = ?, is_primary = ?, is_active = 1, pricing_mode = ?,
                        price_multiplier = ?, fixed_markup = ?, last_synced_at = ?
                    WHERE id = ?
                    """,
                    (
                        supplier_service["external_service_id"],
                        bool_to_int(is_primary),
                        pricing_mode,
                        price_multiplier,
                        fixed_markup,
                        timestamp,
                        mapping_id,
                    ),
                )
            else:
                mapping_id = f"map_{uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO product_supplier_mappings (
                        id, product_id, supplier_id, supplier_service_id, supplier_external_service_id,
                        is_primary, is_active, pricing_mode, price_multiplier, fixed_markup, last_synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                    """,
                    (
                        mapping_id,
                        product_id,
                        supplier_id,
                        supplier_service_id,
                        supplier_service["external_service_id"],
                        bool_to_int(is_primary),
                        pricing_mode,
                        price_multiplier,
                        fixed_markup,
                        timestamp,
                    ),
                )
            conn.commit()

        return {"mapping": self._mapping_summary_by_product(product_id)}

    def delete_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mapping_id = str(payload.get("mappingId") or "").strip()
        if not mapping_id:
            raise PanelError("삭제할 매핑 정보를 찾을 수 없습니다.")
        with self._connect() as conn:
            row = conn.execute("SELECT product_id FROM product_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone()
            if row is None:
                raise PanelError("삭제할 매핑을 찾을 수 없습니다.", status=404)
            conn.execute("DELETE FROM product_supplier_mappings WHERE id = ?", (mapping_id,))
            conn.commit()
            return {"mapping": self._mapping_summary_by_product(row["product_id"])}

    def save_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        email = str(payload.get("email") or "").strip()
        password = str(payload.get("password") or "")
        phone = str(payload.get("phone") or "").strip()
        tier = str(payload.get("tier") or "STANDARD").strip() or "STANDARD"
        role = str(payload.get("role") or "customer").strip() or "customer"
        notes = str(payload.get("notes") or "").strip()
        is_active = bool(payload.get("isActive", True))

        if not name:
            raise PanelError("고객 이름을 입력해 주세요.")
        if not email:
            raise PanelError("이메일을 입력해 주세요.")
        if not phone:
            raise PanelError("연락처를 입력해 주세요.")
        if not customer_id and role != "admin" and len(password) < 8:
            raise PanelError("새 고객 계정에는 8자 이상 비밀번호를 입력해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            if customer_id:
                row = conn.execute("SELECT * FROM users WHERE id = ?", (customer_id,)).fetchone()
                if row is None:
                    raise PanelError("수정할 고객을 찾을 수 없습니다.", status=404)
                password_hash = row["password_hash"]
                if role != "admin" and password:
                    if len(password) < 8:
                        raise PanelError("비밀번호는 8자 이상으로 입력해 주세요.")
                    password_hash = hash_password(password)
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, email = ?, password_hash = ?, phone = ?, tier = ?, role = ?, avatar_label = ?, is_active = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (name, email, password_hash, phone, tier, role, avatar_label(name), bool_to_int(is_active), notes, timestamp, customer_id),
                )
            else:
                customer_id = f"user_{uuid4().hex[:12]}"
                password_hash = "" if role == "admin" else hash_password(password)
                conn.execute(
                    """
                    INSERT INTO users (
                        id, name, email, password_hash, phone, tier, role, avatar_label, balance, is_active, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (customer_id, name, email, password_hash, phone, tier, role, avatar_label(name), bool_to_int(is_active), notes, timestamp, timestamp),
                )
            conn.commit()
        return {"customer": self._customer_by_id(customer_id)}

    def get_customer_detail(self, customer_id: str) -> Dict[str, Any]:
        return {"customer": self._customer_by_id(customer_id, include_private=True)}

    def delete_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("customerId") or "").strip()
        if not customer_id:
            raise PanelError("삭제할 고객을 선택해 주세요.")
        if customer_id == DEMO_USER_ID:
            raise PanelError("현재 데모 운영 계정은 삭제할 수 없습니다.")

        with self._connect() as conn:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (customer_id,)).fetchone()
            if user is None:
                raise PanelError("삭제할 고객을 찾을 수 없습니다.", status=404)
            order_count = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE user_id = ?", (customer_id,)).fetchone()["count"]
            if order_count:
                conn.execute("UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?", (now_iso(), customer_id))
                action = "deactivated"
            else:
                conn.execute("DELETE FROM users WHERE id = ?", (customer_id,))
                action = "deleted"
            conn.commit()
        return {"ok": True, "action": action, "customerId": customer_id}

    def adjust_customer_balance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("customerId") or "").strip()
        amount = int(float(payload.get("amount") or 0) or 0)
        memo = str(payload.get("memo") or "").strip() or "관리자 잔액 조정"
        if not customer_id:
            raise PanelError("고객을 선택해 주세요.")
        if amount == 0:
            raise PanelError("조정 금액을 입력해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            user = conn.execute("SELECT balance FROM users WHERE id = ?", (customer_id,)).fetchone()
            if user is None:
                raise PanelError("고객을 찾을 수 없습니다.", status=404)
            balance_after = int(user["balance"]) + amount
            if balance_after < 0:
                raise PanelError("잔액이 0원보다 작아질 수 없습니다.")
            conn.execute("UPDATE users SET balance = ?, updated_at = ? WHERE id = ?", (balance_after, timestamp, customer_id))
            conn.execute(
                """
                INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"tx_{uuid4().hex[:12]}", customer_id, amount, balance_after, "admin_adjust", memo, timestamp),
            )
            conn.commit()
        return {"customer": self._customer_by_id(customer_id), "balanceAfter": balance_after, "balanceAfterLabel": money(balance_after)}

    def save_category(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        category_id = str(payload.get("id") or "").strip()
        group_id = str(payload.get("groupId") or "").strip()
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip()
        option_label_name = str(payload.get("optionLabelName") or "").strip()
        hero_title = str(payload.get("heroTitle") or name).strip() or name
        hero_subtitle = str(payload.get("heroSubtitle") or description).strip()
        service_description_html = str(payload.get("serviceDescriptionHtml") or "").strip()
        caution_text = str(payload.get("cautionText") or "").strip()
        refund_text = str(payload.get("refundText") or "").strip()
        is_active = bool(payload.get("isActive", True))
        sort_order = int(float(payload.get("sortOrder") or 0) or 0)

        if not group_id:
            raise PanelError("플랫폼 그룹을 선택해 주세요.")
        if not name:
            raise PanelError("카테고리 이름을 입력해 주세요.")

        caution_items = split_lines(caution_text) or ["비공개 계정 또는 잘못된 URL 입력 시 작업이 지연될 수 있어요."]
        refund_items = split_lines(refund_text) or ["작업이 시작된 이후에는 취소 및 환불이 제한될 수 있어요."]
        if not service_description_html:
            service_description_html = f"<p><strong>{html_escape(name)}</strong></p><p>{html_escape(description or hero_subtitle or '상세 설명을 입력해 주세요.')}</p>"

        timestamp = now_iso()
        with self._connect() as conn:
            group_row = conn.execute("SELECT id FROM platform_groups WHERE id = ?", (group_id,)).fetchone()
            if group_row is None:
                raise PanelError("선택한 플랫폼 그룹을 찾을 수 없습니다.", status=404)
            if category_id:
                existing = conn.execute("SELECT id FROM product_categories WHERE id = ?", (category_id,)).fetchone()
                if existing is None:
                    raise PanelError("수정할 카테고리를 찾을 수 없습니다.", status=404)
                conn.execute(
                    """
                    UPDATE product_categories
                    SET platform_group_id = ?, name = ?, description = ?, option_label_name = ?, hero_title = ?,
                        hero_subtitle = ?, service_description_html = ?, caution_json = ?, refund_notice_json = ?,
                        is_active = ?, sort_order = ?
                    WHERE id = ?
                    """,
                    (
                        group_id,
                        name,
                        description,
                        option_label_name,
                        hero_title,
                        hero_subtitle,
                        service_description_html,
                        as_json(caution_items),
                        as_json(refund_items),
                        bool_to_int(is_active),
                        sort_order,
                        category_id,
                    ),
                )
            else:
                category_id = f"cat_{uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO product_categories (
                        id, platform_group_id, name, description, option_label_name, category_kind,
                        hero_title, hero_subtitle, service_description_html, caution_json, refund_notice_json, is_active, sort_order
                    ) VALUES (?, ?, ?, ?, ?, 'normal', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        category_id,
                        group_id,
                        name,
                        description,
                        option_label_name,
                        hero_title,
                        hero_subtitle,
                        service_description_html,
                        as_json(caution_items),
                        as_json(refund_items),
                        bool_to_int(is_active),
                        sort_order,
                    ),
                )
            conn.commit()
        return {"category": self._category_by_id(category_id)}

    def delete_category(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        category_id = str(payload.get("categoryId") or "").strip()
        if not category_id:
            raise PanelError("삭제할 카테고리를 선택해 주세요.")
        with self._connect() as conn:
            category = conn.execute("SELECT id FROM product_categories WHERE id = ?", (category_id,)).fetchone()
            if category is None:
                raise PanelError("삭제할 카테고리를 찾을 수 없습니다.", status=404)
            order_count = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE product_category_id = ?", (category_id,)).fetchone()["count"]
            product_count = conn.execute("SELECT COUNT(*) AS count FROM products WHERE product_category_id = ?", (category_id,)).fetchone()["count"]
            if order_count or product_count:
                conn.execute("UPDATE product_categories SET is_active = 0 WHERE id = ?", (category_id,))
                conn.execute("UPDATE products SET is_active = 0 WHERE product_category_id = ?", (category_id,))
                action = "deactivated"
            else:
                conn.execute("DELETE FROM product_categories WHERE id = ?", (category_id,))
                action = "deleted"
            conn.commit()
        return {"ok": True, "action": action, "categoryId": category_id}

    def save_catalog_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("id") or "").strip()
        category_id = str(payload.get("categoryId") or "").strip()
        name = str(payload.get("name") or "").strip()
        menu_name = str(payload.get("menuName") or name).strip() or name
        option_name = str(payload.get("optionName") or "").strip()
        product_code = str(payload.get("productCode") or "").strip()
        price = int(float(payload.get("price") or 0) or 0)
        min_amount = int(float(payload.get("minAmount") or 1) or 1)
        max_amount = int(float(payload.get("maxAmount") or min_amount) or min_amount)
        step_amount = int(float(payload.get("stepAmount") or 1) or 1)
        price_strategy = str(payload.get("priceStrategy") or "unit").strip() or "unit"
        unit_label = str(payload.get("unitLabel") or "개").strip() or "개"
        badge = str(payload.get("badge") or "").strip()
        estimated_turnaround = str(payload.get("estimatedTurnaround") or "").strip()
        is_discounted = bool(payload.get("isDiscounted", False))
        is_active = bool(payload.get("isActive", True))
        sort_order = int(float(payload.get("sortOrder") or 0) or 0)

        if not category_id:
            raise PanelError("상품 카테고리를 선택해 주세요.")
        if not name:
            raise PanelError("상품 이름을 입력해 주세요.")
        if not product_code:
            raise PanelError("상품 코드(product code)를 입력해 주세요.")
        if price <= 0:
            raise PanelError("상품 가격을 입력해 주세요.")
        if min_amount <= 0 or max_amount <= 0 or step_amount <= 0:
            raise PanelError("최소/최대/증가 단위는 1 이상이어야 합니다.")
        if min_amount > max_amount:
            raise PanelError("최대 수량은 최소 수량보다 크거나 같아야 합니다.")
        if price_strategy == "fixed":
            min_amount = max_amount = step_amount = 1

        timestamp = now_iso()
        with self._connect() as conn:
            category = conn.execute("SELECT id FROM product_categories WHERE id = ?", (category_id,)).fetchone()
            if category is None:
                raise PanelError("선택한 카테고리를 찾을 수 없습니다.", status=404)

            existing_form_structure_json = ""
            previous_category_id = category_id
            if product_id:
                existing = conn.execute("SELECT form_structure_json, product_category_id FROM products WHERE id = ?", (product_id,)).fetchone()
                if existing is None:
                    raise PanelError("수정할 상품을 찾을 수 없습니다.", status=404)
                existing_form_structure_json = str(existing["form_structure_json"] or "")
                previous_category_id = str(existing["product_category_id"] or category_id)

            form_structure_json = build_admin_form_structure(payload, existing_form_structure_json)

            if product_id:
                conn.execute(
                    """
                    UPDATE products
                    SET product_category_id = ?, name = ?, menu_name = ?, option_name = ?, product_code = ?, price = ?,
                        min_amount = ?, max_amount = ?, step_amount = ?, option_price_rate = ?, price_strategy = ?, unit_label = ?,
                        is_discounted = ?, estimated_turnaround = ?, badge = ?, form_structure_json = ?, is_active = ?, sort_order = ?
                    WHERE id = ?
                    """,
                    (
                        category_id,
                        name,
                        menu_name,
                        option_name,
                        product_code,
                        price,
                        min_amount,
                        max_amount,
                        step_amount,
                        88 if is_discounted else 100,
                        price_strategy,
                        unit_label,
                        bool_to_int(is_discounted),
                        estimated_turnaround,
                        badge,
                        form_structure_json,
                        bool_to_int(is_active),
                        sort_order,
                        product_id,
                    ),
                )
            else:
                product_id = f"prd_{uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO products (
                        id, product_category_id, name, menu_name, option_name, product_code, price,
                        min_amount, max_amount, step_amount, option_price_rate, price_strategy, unit_label,
                        supports_order_options, is_discounted, product_kind, is_custom,
                        estimated_turnaround, badge, form_structure_json, is_active, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'normal', 0, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id,
                        category_id,
                        name,
                        menu_name,
                        option_name,
                        product_code,
                        price,
                        min_amount,
                        max_amount,
                        step_amount,
                        88 if is_discounted else 100,
                        price_strategy,
                        unit_label,
                        bool_to_int(is_discounted),
                        estimated_turnaround,
                        badge,
                        form_structure_json,
                        bool_to_int(is_active),
                        sort_order,
                    ),
                )

            self._sync_category_order_options(conn, category_id)
            if previous_category_id != category_id:
                self._sync_category_order_options(conn, previous_category_id)
            conn.commit()
        return {"product": self._catalog_product_by_id(product_id)}

    def delete_catalog_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("productId") or "").strip()
        if not product_id:
            raise PanelError("삭제할 상품을 선택해 주세요.")
        with self._connect() as conn:
            product = conn.execute("SELECT id, product_category_id FROM products WHERE id = ?", (product_id,)).fetchone()
            if product is None:
                raise PanelError("삭제할 상품을 찾을 수 없습니다.", status=404)
            order_count = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE product_id = ?", (product_id,)).fetchone()["count"]
            if order_count:
                conn.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
                action = "deactivated"
            else:
                conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
                action = "deleted"
            self._sync_category_order_options(conn, product["product_category_id"])
            conn.commit()
        return {"ok": True, "action": action, "productId": product_id}

    def update_admin_order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(payload.get("orderId") or "").strip()
        status = str(payload.get("status") or "").strip()
        admin_memo = str(payload.get("adminMemo") or "").strip()
        if not order_id:
            raise PanelError("주문을 선택해 주세요.")
        if status not in {"queued", "in_progress", "completed"}:
            raise PanelError("지원하지 않는 주문 상태입니다.")

        with self._connect() as conn:
            row = conn.execute("SELECT notes_json FROM orders WHERE id = ?", (order_id,)).fetchone()
            if row is None:
                raise PanelError("주문을 찾을 수 없습니다.", status=404)
            notes = parse_json(row["notes_json"], {})
            if admin_memo:
                notes["adminMemo"] = admin_memo
            conn.execute(
                "UPDATE orders SET status = ?, notes_json = ?, updated_at = ? WHERE id = ?",
                (status, as_json(notes), now_iso(), order_id),
            )
            conn.commit()
        return {"ok": True, "orderId": order_id, "status": status}

    def _run_supplier_connection_test(
        self,
        api_url: str,
        api_key: str,
        *,
        integration_type: str = SUPPLIER_INTEGRATION_CLASSIC,
        bearer_token: str = "",
        require_services: bool = False,
    ) -> Dict[str, Any]:
        normalized_type = normalize_supplier_integration_type(integration_type)
        candidates = normalize_supplier_api_candidates(normalized_type, api_url)
        if not candidates:
            raise PanelError("API URL 형식이 올바르지 않습니다.")

        last_error = "연결 실패"
        for candidate in candidates:
            client = SupplierApiClient(
                candidate,
                api_key,
                integration_type=normalized_type,
                bearer_token=bearer_token,
            )
            try:
                if supplier_supports_balance_check(normalized_type):
                    balance_payload = client.balance_summary()
                    success_message = "API 연결이 확인되었습니다."
                else:
                    balance_payload = {"balance": "", "currency": ""}
                    success_message = "서비스 목록 조회가 확인되었습니다. 잔액 API는 제공되지 않습니다."
                raw_services_payload = client.services()
                services_payload = normalize_supplier_services_payload(normalized_type, raw_services_payload)
                return {
                    "status": "success",
                    "message": success_message,
                    "resolvedApiUrl": candidate,
                    "persistedApiUrl": api_url.strip() or candidate,
                    "balance": balance_payload["balance"],
                    "currency": balance_payload["currency"],
                    "serviceCount": len(services_payload),
                    "checkedAt": now_iso(),
                    "servicesPayload": services_payload if require_services else None,
                }
            except SupplierApiError as exc:
                last_error = str(exc)

        raise PanelError(f"API 연결을 확인하지 못했습니다. {last_error}")

    def _supplier_by_id(self, supplier_id: str, *, include_api_key: bool = False) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        integration_type = normalize_supplier_integration_type(row["integration_type"])
        payload = {
            "id": row["id"],
            "name": row["name"],
            "apiUrl": row["api_url"],
            "integrationType": integration_type,
            "hasApiKey": bool(row["api_key"]),
            "apiKeyMasked": mask_secret(row["api_key"]),
            "hasBearerToken": bool(row["bearer_token"]),
            "bearerTokenMasked": mask_secret(row["bearer_token"]),
            "supportsBalanceCheck": supplier_supports_balance_check(integration_type),
            "supportsAutoDispatch": supplier_supports_auto_dispatch(integration_type),
            "isActive": bool(row["is_active"]),
            "notes": row["notes"],
            "lastTestStatus": row["last_test_status"],
            "lastTestMessage": row["last_test_message"],
            "lastBalance": row["last_balance"],
            "lastCurrency": row["last_currency"],
            "lastServiceCount": row["last_service_count"],
            "lastCheckedAt": row["last_checked_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if include_api_key:
            payload["apiKey"] = row["api_key"]
            payload["bearerToken"] = row["bearer_token"]
        return payload

    def public_site_settings(self) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1")
        return {"siteSettings": self._site_settings_public_payload(row)}

    def admin_site_settings(self) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1")
        return {"siteSettings": self._site_settings_admin_payload(row)}

    def _site_settings_row(self, conn: sqlite3.Connection) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            self._ensure_site_settings(conn)
            row = conn.execute("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            raise PanelError("사이트 설정을 불러오지 못했습니다.", status=500)
        return row

    def _site_settings_public_payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        effective_mail_sms_site_name = (
            row["mail_sms_site_name"].strip()
            if bool(row["use_mail_sms_site_name"]) and row["mail_sms_site_name"].strip()
            else row["site_name"]
        )
        return {
            "siteName": row["site_name"],
            "siteDescription": row["site_description"],
            "useMailSmsSiteName": bool(row["use_mail_sms_site_name"]),
            "mailSmsSiteName": row["mail_sms_site_name"],
            "effectiveMailSmsSiteName": effective_mail_sms_site_name,
            "faviconUrl": row["favicon_url"],
            "shareImageUrl": row["share_image_url"],
        }

    def _site_settings_admin_payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        payload = self._site_settings_public_payload(row)
        payload.update(
            {
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
        )
        return payload

    def _popup_public_payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "badgeText": row["badge_text"],
            "title": row["title"],
            "description": row["description"],
            "imageUrl": row["image_url"],
            "route": row["route"],
            "theme": row["theme"],
            "isActive": bool(row["is_active"]),
            "updatedAt": row["updated_at"],
        }

    def _popup_admin_payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "badgeText": row["badge_text"],
            "title": row["title"],
            "description": row["description"],
            "imageUrl": row["image_url"],
            "route": row["route"],
            "theme": row["theme"],
            "isActive": bool(row["is_active"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _home_banner_payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "subtitle": row["subtitle"],
            "ctaLabel": row["cta_label"],
            "route": row["route"],
            "imageUrl": row["image_url"],
            "theme": row["theme"],
            "isActive": bool(row["is_active"]),
            "sortOrder": row["sort_order"],
        }

    def _home_popup_by_id(self, popup_id: str) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM home_popups WHERE id = ?", (popup_id,))
        return self._popup_admin_payload(row)

    def _home_banner_by_id(self, banner_id: str) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM home_banners WHERE id = ?", (banner_id,))
        return self._home_banner_payload(row)

    def _customer_by_id(self, customer_id: str, *, include_private: bool = True) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    u.*,
                    COUNT(o.id) AS order_count,
                    COALESCE(SUM(o.total_price), 0) AS total_spent,
                    MAX(o.created_at) AS last_order_at
                FROM users u
                LEFT JOIN orders o ON o.user_id = u.id
                WHERE u.id = ?
                GROUP BY u.id
                """,
                (customer_id,),
            ).fetchone()
        if row is None:
            raise PanelError("고객을 찾을 수 없습니다.", status=404)
        payload = {
            "id": row["id"],
            "name": row["name"],
            "emailMasked": mask_email(row["email"]),
            "phoneMasked": mask_phone(row["phone"]),
            "tier": row["tier"],
            "role": row["role"],
            "avatarLabel": row["avatar_label"],
            "balance": row["balance"],
            "balanceLabel": money(row["balance"]),
            "isActive": bool(row["is_active"]),
            "hasPassword": bool(row["password_hash"]),
            "notes": row["notes"],
            "lastLoginAt": row["last_login_at"],
            "orderCount": row["order_count"],
            "totalSpent": row["total_spent"],
            "totalSpentLabel": money(row["total_spent"]),
            "lastOrderAt": row["last_order_at"] or "",
            "lastOrderLabel": self._relative_date_label(row["last_order_at"]) if row["last_order_at"] else "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if include_private:
            payload["email"] = row["email"]
            payload["phone"] = row["phone"]
        return payload

    def _category_by_id(self, category_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    pc.*,
                    pg.name AS group_name,
                    pg.id AS group_id,
                    ps.id AS platform_id,
                    ps.display_name AS platform_name,
                    COUNT(p.id) AS product_count,
                    SUM(CASE WHEN p.is_active = 1 THEN 1 ELSE 0 END) AS active_product_count
                FROM product_categories pc
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                LEFT JOIN products p ON p.product_category_id = pc.id
                WHERE pc.id = ?
                GROUP BY pc.id
                """,
                (category_id,),
            ).fetchone()
        if row is None:
            raise PanelError("카테고리를 찾을 수 없습니다.", status=404)
        return {
            "id": row["id"],
            "groupId": row["group_id"],
            "groupName": row["group_name"],
            "platformId": row["platform_id"],
            "platformName": row["platform_name"],
            "name": row["name"],
            "description": row["description"],
            "optionLabelName": row["option_label_name"],
            "heroTitle": row["hero_title"],
            "heroSubtitle": row["hero_subtitle"],
            "serviceDescriptionHtml": row["service_description_html"],
            "cautionText": "\n".join(parse_json(row["caution_json"], [])),
            "refundText": "\n".join(parse_json(row["refund_notice_json"], [])),
            "isActive": bool(row["is_active"]),
            "productCount": row["product_count"],
            "activeProductCount": row["active_product_count"] or 0,
            "sortOrder": row["sort_order"],
        }

    def _catalog_product_by_id(self, product_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    p.*,
                    pc.id AS category_id,
                    pc.name AS category_name,
                    pc.is_active AS category_is_active,
                    pg.id AS group_id,
                    pg.name AS group_name,
                    ps.display_name AS platform_name,
                    psm.id AS mapping_id,
                    psm.supplier_id,
                    psm.supplier_service_id,
                    psm.supplier_external_service_id,
                    psm.pricing_mode,
                    psm.price_multiplier,
                    psm.fixed_markup,
                    s.name AS supplier_name,
                    ss.name AS supplier_service_name
                FROM products p
                JOIN product_categories pc ON pc.id = p.product_category_id
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                LEFT JOIN product_supplier_mappings psm ON psm.product_id = p.id AND psm.is_primary = 1
                LEFT JOIN suppliers s ON s.id = psm.supplier_id
                LEFT JOIN supplier_services ss ON ss.id = psm.supplier_service_id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
        if row is None:
            raise PanelError("상품을 찾을 수 없습니다.", status=404)
        return {
            "id": row["id"],
            "name": row["name"],
            "menuName": row["menu_name"],
            "optionName": row["option_name"],
            "productCode": row["product_code"],
            "price": row["price"],
            "priceLabel": money(row["price"]),
            "minAmount": row["min_amount"],
            "maxAmount": row["max_amount"],
            "stepAmount": row["step_amount"],
            "priceStrategy": row["price_strategy"],
            "unitLabel": row["unit_label"],
            "isDiscounted": bool(row["is_discounted"]),
            "estimatedTurnaround": row["estimated_turnaround"],
            "badge": row["badge"],
            "sortOrder": row["sort_order"],
            "categoryId": row["category_id"],
            "categoryName": row["category_name"],
            "groupId": row["group_id"],
            "groupName": row["group_name"],
            "platformName": row["platform_name"],
            "isActive": bool(row["is_active"]) and bool(row["category_is_active"]),
            "formConfig": admin_form_config(parse_json(row["form_structure_json"], {})),
            "mapping": {
                "id": row["mapping_id"],
                "supplierId": row["supplier_id"],
                "supplierServiceId": row["supplier_service_id"],
                "supplierExternalServiceId": row["supplier_external_service_id"],
                "supplierName": row["supplier_name"],
                "supplierServiceName": row["supplier_service_name"],
                "pricingMode": row["pricing_mode"],
                "priceMultiplier": row["price_multiplier"],
                "fixedMarkup": row["fixed_markup"],
            }
            if row["mapping_id"]
            else None,
        }

    def _sync_category_order_options(self, conn: sqlite3.Connection, category_id: str) -> None:
        active_count = conn.execute(
            "SELECT COUNT(*) AS count FROM products WHERE product_category_id = ? AND is_active = 1",
            (category_id,),
        ).fetchone()["count"]
        supports = 1 if active_count > 1 else 0
        conn.execute("UPDATE products SET supports_order_options = ? WHERE product_category_id = ?", (supports, category_id))

    def _mapping_summary_by_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    psm.id,
                    psm.product_id,
                    psm.supplier_id,
                    psm.supplier_service_id,
                    psm.supplier_external_service_id,
                    psm.pricing_mode,
                    psm.price_multiplier,
                    psm.fixed_markup,
                    s.name AS supplier_name,
                    ss.name AS supplier_service_name
                FROM product_supplier_mappings psm
                JOIN suppliers s ON s.id = psm.supplier_id
                JOIN supplier_services ss ON ss.id = psm.supplier_service_id
                WHERE psm.product_id = ? AND psm.is_primary = 1
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "productId": row["product_id"],
            "supplierId": row["supplier_id"],
            "supplierServiceId": row["supplier_service_id"],
            "supplierExternalServiceId": row["supplier_external_service_id"],
            "supplierName": row["supplier_name"],
            "supplierServiceName": row["supplier_service_name"],
            "pricingMode": row["pricing_mode"],
            "priceMultiplier": row["price_multiplier"],
            "fixedMarkup": row["fixed_markup"],
        }

    def preview_link(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("productId") or "").strip()
        fields = payload.get("fields") or {}
        if not product_id:
            raise PanelError("미리보기를 확인할 상품 정보가 없습니다.")
        if not isinstance(fields, dict):
            raise PanelError("미리보기 입력값 형식이 올바르지 않습니다.")

        with self._connect() as conn:
            product = conn.execute(
                """
                SELECT
                    p.id,
                    p.product_code,
                    p.form_structure_json,
                    pc.name AS category_name,
                    ps.slug AS platform_slug,
                    ps.accent_color
                FROM products p
                JOIN product_categories pc ON pc.id = p.product_category_id
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                WHERE p.id = ? AND p.is_active = 1 AND pc.is_active = 1
                """,
                (product_id,),
            ).fetchone()
            if product is None:
                raise PanelError("미리보기를 확인할 상품을 찾을 수 없습니다.", status=404)

        validation = self._validate_product_target(product, fields, require_preview=False)
        if not validation["rawInput"]:
            return {
                "preview": {
                    "found": False,
                    "title": "",
                    "imageUrl": "",
                    "resolvedUrl": "",
                    "message": "링크나 계정 ID를 입력하면 미리보기가 표시됩니다.",
                    "displayInput": "",
                    "sourceLabel": validation["sourceLabel"],
                    "state": "idle",
                }
            }

        if validation["requiresPreview"]:
            preview = extract_preview_metadata(validation["url"], product["accent_color"] or "#4c76ff")
            preview["displayInput"] = validation["rawInput"]
            preview["sourceLabel"] = validation["sourceLabel"]
            preview["state"] = "found" if preview["found"] else "missing"
            if not preview["found"]:
                preview["message"] = "링크가 확인되지 않습니다."
            return {"preview": preview}

        if not validation["url"]:
            return {
                "preview": {
                    "found": False,
                    "title": "",
                    "imageUrl": "",
                    "resolvedUrl": "",
                    "message": "링크가 확인되지 않습니다.",
                    "displayInput": validation["rawInput"],
                    "sourceLabel": validation["sourceLabel"],
                    "state": "missing",
                }
            }

        return {
            "preview": {
                "found": True,
                "title": "",
                "imageUrl": placeholder_thumbnail(validation["rawInput"], product["accent_color"] or "#4c76ff"),
                "resolvedUrl": validation["url"],
                "message": "링크 형식을 확인했습니다.",
                "displayInput": validation["rawInput"],
                "sourceLabel": validation["sourceLabel"],
                "state": "found",
            }
        }

    def charge_balance(self, amount: int, user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        if amount <= 0:
            raise PanelError("충전 금액은 0보다 커야 합니다.")
        if amount > 5_000_000:
            raise PanelError("한 번에 충전 가능한 금액을 초과했습니다.")

        with self._connect() as conn:
            user = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
            if user is None:
                raise PanelError("사용자를 찾을 수 없습니다.", status=404)
            balance_after = int(user["balance"]) + amount
            timestamp = now_iso()
            tx_id = f"tx_{int(dt.datetime.now().timestamp() * 1000)}"
            conn.execute("UPDATE users SET balance = ?, updated_at = ? WHERE id = ?", (balance_after, timestamp, user_id))
            conn.execute(
                "INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tx_id, user_id, amount, balance_after, "charge", f"캐시 충전 {money(amount)}", timestamp),
            )
            conn.commit()
            return {
                "ok": True,
                "balance": balance_after,
                "balanceLabel": money(balance_after),
            }

    def create_order(self, payload: Dict[str, Any], user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        product_id = str(payload.get("productId") or "").strip()
        fields = payload.get("fields") or {}
        if not product_id:
            raise PanelError("주문할 상품이 선택되지 않았습니다.")
        if not isinstance(fields, dict):
            raise PanelError("주문 폼 정보가 올바르지 않습니다.")

        supplier_mapping: Optional[Dict[str, Any]] = None
        product_data: Optional[Dict[str, Any]] = None
        with self._connect() as conn:
            product = conn.execute(
                """
                SELECT
                    p.*,
                    pc.id AS category_id,
                    pc.name AS category_name,
                    pg.platform_section_id,
                    ps.slug AS platform_slug,
                    ps.accent_color AS accent_color
                FROM products p
                JOIN product_categories pc ON pc.id = p.product_category_id
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                WHERE p.id = ? AND p.is_active = 1 AND pc.is_active = 1
                """,
                (product_id,),
            ).fetchone()
            if product is None:
                raise PanelError("주문할 상품을 찾을 수 없습니다.", status=404)

            rules = parse_json(product["form_structure_json"], {}).get("schema", {})
            self._validate_fields(fields, rules)
            self._validate_product_target(product, fields, require_preview=True)

            quantity = self._resolve_quantity(product, fields)
            total_price = int(product["price"]) if product["price_strategy"] == "fixed" else int(product["price"]) * quantity

            user = conn.execute("SELECT balance, phone FROM users WHERE id = ?", (user_id,)).fetchone()
            if user is None:
                raise PanelError("사용자를 찾을 수 없습니다.", status=404)
            if int(user["balance"]) < total_price:
                raise PanelError("보유 캐시가 부족합니다. 충전 후 다시 시도해 주세요.")

            mapping_row = conn.execute(
                """
                SELECT
                    psm.*,
                    s.api_url,
                    s.integration_type,
                    s.api_key,
                    s.bearer_token,
                    s.name AS supplier_name,
                    s.is_active AS supplier_is_active,
                    ss.name AS supplier_service_name,
                    ss.raw_json AS supplier_service_raw_json
                FROM product_supplier_mappings psm
                JOIN suppliers s ON s.id = psm.supplier_id
                JOIN supplier_services ss ON ss.id = psm.supplier_service_id
                WHERE psm.product_id = ? AND psm.is_primary = 1 AND psm.is_active = 1
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            if mapping_row is not None and bool(mapping_row["supplier_is_active"]):
                supplier_mapping = dict(mapping_row)
            product_data = dict(product)

            timestamp = now_iso()
            order_index = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"] + 1
            order_number = f"P24{order_index:04d}"
            order_id = f"order_{int(dt.datetime.now().timestamp() * 1000)}"
            target_value = (
                str(fields.get("targetValue") or "")
                or str(fields.get("targetUrl") or "")
                or str(fields.get("targetKeyword") or "")
            ).strip()
            contact_phone = str(fields.get("contactPhone") or user["phone"] or "").strip()
            notes = {
                key: value
                for key, value in fields.items()
                if key not in {"targetValue", "targetUrl", "targetKeyword", "orderedCount", "contactPhone"}
            }

            balance_after = int(user["balance"]) - total_price
            conn.execute(
                """
                INSERT INTO orders (
                    id, order_number, user_id, platform_section_id, product_category_id, product_id,
                    product_name_snapshot, option_name_snapshot, target_value, contact_phone,
                    quantity, unit_price, total_price, status, notes_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    order_number,
                    user_id,
                    product["platform_section_id"],
                    product["category_id"],
                    product["id"],
                    product["name"],
                    product["option_name"],
                    target_value,
                    contact_phone,
                    quantity,
                    product["price"],
                    total_price,
                    "queued",
                    as_json(notes),
                    timestamp,
                    timestamp,
                ),
            )

            template = parse_json(product["form_structure_json"], {}).get("template", {})
            for field_index, (field_key, field_value) in enumerate(fields.items()):
                if field_value in ("", None):
                    continue
                field_label = self._field_label(template.get(field_key, {}), field_key)
                conn.execute(
                    "INSERT INTO order_fields (id, order_id, field_key, field_label, field_value) VALUES (?, ?, ?, ?, ?)",
                    (f"{order_id}_field_{field_index}", order_id, field_key, field_label, str(field_value)),
                )

            conn.execute(
                "UPDATE users SET balance = ?, updated_at = ? WHERE id = ?",
                (balance_after, timestamp, user_id),
            )
            conn.execute(
                "INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"tx_{order_id}",
                    user_id,
                    -total_price,
                    balance_after,
                    "order",
                    f"{product['name']} 주문",
                    timestamp,
                ),
            )
            conn.commit()

        supplier_dispatch = None
        if supplier_mapping and product_data is not None:
            supplier_dispatch = self._dispatch_supplier_order(order_id, product_data, fields, supplier_mapping)

        response_payload = {
            "ok": True,
            "orderId": order_id,
            "orderNumber": order_number,
            "totalPrice": total_price,
            "totalPriceLabel": money(total_price),
            "balanceAfter": balance_after,
            "balanceAfterLabel": money(balance_after),
        }
        if supplier_dispatch is not None:
            response_payload["supplierDispatchStatus"] = supplier_dispatch["status"]
        return response_payload

    def _dispatch_supplier_order(
        self,
        order_id: str,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        supplier_order_id = f"sord_{uuid4().hex[:12]}"
        timestamp = now_iso()
        request_payload = self._build_supplier_order_payload(product, fields, mapping)
        supplier_external_order_id = ""
        status = "pending"
        response_payload: Any = {}

        try:
            client = SupplierApiClient(
                str(mapping["api_url"]),
                str(mapping["api_key"]),
                integration_type=str(mapping.get("integration_type") or SUPPLIER_INTEGRATION_CLASSIC),
                bearer_token=str(mapping.get("bearer_token") or ""),
            )
            response_payload = client.order(request_payload)
            if isinstance(response_payload, dict):
                supplier_external_order_id = str(response_payload.get("order") or response_payload.get("id") or "").strip()
                if supplier_external_order_id:
                    status = "submitted"
                elif response_payload:
                    status = "accepted"
                else:
                    status = "failed"
            elif response_payload not in (None, False, "", []):
                status = "accepted"
            else:
                status = "failed"
        except Exception as exc:
            response_payload = {"error": str(exc)}
            status = "failed"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO supplier_orders (
                    id, order_id, supplier_id, supplier_service_id, supplier_external_order_id,
                    request_payload_json, response_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    supplier_order_id,
                    order_id,
                    str(mapping["supplier_id"]),
                    str(mapping["supplier_service_id"]),
                    supplier_external_order_id,
                    as_json(request_payload),
                    as_json(response_payload),
                    status,
                    timestamp,
                    timestamp,
                ),
            )
            conn.commit()

        return {
            "id": supplier_order_id,
            "status": status,
            "supplierExternalOrderId": supplier_external_order_id,
        }

    def _build_supplier_order_payload(
        self,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "service": str(mapping["supplier_external_service_id"]),
        }

        target_url = str(fields.get("targetUrl") or "").strip()
        target_value = str(fields.get("targetValue") or "").strip()
        target_keyword = str(fields.get("targetKeyword") or "").strip()
        quantity = str(fields.get("orderedCount") or "").strip()

        if target_url:
            payload["link"] = normalize_url(target_url) or target_url
        elif target_value:
            if looks_like_url(target_value):
                payload["link"] = normalize_url(target_value) or target_value
            else:
                payload["username"] = target_value.lstrip("@")
                inferred_link = account_preview_url(
                    target_value,
                    preview_platform_hint(str(product.get("product_code") or ""), str(product.get("platform_slug") or "")),
                )
                if inferred_link:
                    payload["link"] = inferred_link

        if quantity and str(product.get("price_strategy") or "") != "fixed":
            payload["quantity"] = quantity

        if target_keyword:
            payload["google_keyword"] = target_keyword

        passthrough_map = {
            "runs": "runs",
            "interval": "interval",
            "country": "country",
            "device": "device",
            "typeOfTraffic": "type_of_traffic",
            "type_of_traffic": "type_of_traffic",
            "googleKeyword": "google_keyword",
            "google_keyword": "google_keyword",
            "answerNumber": "answer_number",
            "answer_number": "answer_number",
            "min": "min",
            "max": "max",
            "posts": "posts",
            "oldPosts": "old_posts",
            "old_posts": "old_posts",
            "delay": "delay",
            "expiry": "expiry",
            "comments": "comments",
        }
        for source_key, target_key in passthrough_map.items():
            value = fields.get(source_key)
            if value not in (None, ""):
                payload[target_key] = value

        request_memo = str(fields.get("requestMemo") or "").strip()
        if request_memo and "comments" not in payload:
            payload["comments"] = request_memo

        return payload

    def _validate_fields(self, fields: Dict[str, Any], rules: Dict[str, List[str]]) -> None:
        for key, field_rules in rules.items():
            if "STRING_REQUIRED" in field_rules and not str(fields.get(key) or "").strip():
                raise PanelError("필수 입력값이 비어 있습니다.")

    def _validate_product_target(
        self,
        product: sqlite3.Row,
        fields: Dict[str, Any],
        require_preview: bool = False,
    ) -> Dict[str, Any]:
        resolved = self._resolve_preview_target(product, fields)
        raw_input = resolved["rawInput"]
        if not raw_input:
            return {
                "rawInput": "",
                "url": "",
                "sourceLabel": resolved["sourceLabel"],
                "platformHint": resolved["platformHint"],
                "fieldKey": resolved["fieldKey"],
                "requiresPreview": False,
            }

        platform_hint = resolved["platformHint"]
        field_key = resolved["fieldKey"]
        url = resolved["url"]
        format_valid = True

        if field_key == "targetUrl":
            format_valid = bool(url) and platform_target_url_matches(platform_hint, url)
        elif field_key == "targetValue":
            if looks_like_url(raw_input):
                format_valid = bool(url) and platform_target_url_matches(platform_hint, url)
            elif platform_hint in ACCOUNT_STYLE_PLATFORMS:
                format_valid = bool(url)

        if not format_valid:
            raise PanelError(platform_target_error_message(platform_hint))

        requires_preview = platform_hint == "instagram" and bool(url)
        if require_preview and requires_preview:
            preview = extract_preview_metadata(url, product["accent_color"] or "#4c76ff")
            if not preview.get("found"):
                raise PanelError("인스타그램 링크가 확인되지 않아 주문할 수 없습니다.")

        return {
            "rawInput": raw_input,
            "url": url,
            "sourceLabel": resolved["sourceLabel"],
            "platformHint": platform_hint,
            "fieldKey": field_key,
            "requiresPreview": requires_preview,
        }

    def _resolve_preview_target(self, product: sqlite3.Row, fields: Dict[str, Any]) -> Dict[str, str]:
        form_structure = parse_json(product["form_structure_json"], {})
        template = form_structure.get("template", {})
        platform_hint = preview_platform_hint(product["product_code"], product["platform_slug"])

        for field_key in ("targetUrl", "targetValue"):
            raw_value = str(fields.get(field_key) or "").strip()
            if not raw_value:
                continue

            template_entry = template.get(field_key, {})
            template_options = template_entry.get("templateOptions", {})
            source_label = self._field_label(template_entry, field_key)

            if looks_like_url(raw_value):
                return {
                    "rawInput": raw_value,
                    "url": normalize_url(raw_value) or "",
                    "sourceLabel": source_label,
                    "fieldKey": field_key,
                    "platformHint": platform_hint,
                }

            if field_key == "targetValue":
                inferred = account_preview_url(raw_value, platform_hint)
                return {
                    "rawInput": raw_value,
                    "url": inferred or "",
                    "sourceLabel": source_label or template_options.get("label", "계정 ID"),
                    "fieldKey": field_key,
                    "platformHint": platform_hint,
                }

            return {
                "rawInput": raw_value,
                "url": "",
                "sourceLabel": source_label,
                "fieldKey": field_key,
                "platformHint": platform_hint,
            }

        return {
            "rawInput": "",
            "url": "",
            "sourceLabel": "",
            "fieldKey": "",
            "platformHint": platform_hint,
        }

    def _resolve_quantity(self, product: sqlite3.Row, fields: Dict[str, Any]) -> int:
        if product["price_strategy"] == "fixed":
            return 1
        raw = fields.get("orderedCount")
        if raw in (None, ""):
            raise PanelError("수량을 입력해 주세요.")
        try:
            quantity = int(raw)
        except (TypeError, ValueError):
            raise PanelError("수량은 숫자로 입력해 주세요.")
        if quantity < int(product["min_amount"]) or quantity > int(product["max_amount"]):
            raise PanelError("수량이 허용 범위를 벗어났습니다.")
        step = int(product["step_amount"])
        if step > 1 and quantity % step != 0:
            raise PanelError(f"수량은 {step} 단위로 입력해 주세요.")
        return quantity

    def _field_label(self, template_entry: Dict[str, Any], fallback: str) -> str:
        options = template_entry.get("templateOptions", {})
        if "label" in options:
            return str(options.get("label"))
        if "labelProps" in options:
            return str(options["labelProps"].get("label", fallback))
        return fallback

    def _relative_date_label(self, raw: str) -> str:
        try:
            target = dt.datetime.fromisoformat(raw)
        except ValueError:
            return raw
        now = dt.datetime.now(target.tzinfo or dt.timezone.utc)
        delta = now - target
        if delta.days >= 1:
            return f"{delta.days}일 전"
        hours = max(int(delta.total_seconds() // 3600), 0)
        if hours >= 1:
            return f"{hours}시간 전"
        minutes = max(int(delta.total_seconds() // 60), 0)
        return f"{max(minutes, 1)}분 전"
