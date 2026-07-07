from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row as psycopg_dict_row
except ImportError:  # pragma: no cover - optional runtime dependency
    psycopg = None
    psycopg_dict_row = None


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
        result.append("%s" if char == "?" and not in_single and not in_double else char)
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
    def rowcount(self) -> int:
        return int(getattr(self.raw_cursor, "rowcount", -1) or 0)

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


def env_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def runtime_mode() -> str:
    return str(
        os.environ.get("SMM_PANEL_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("NODE_ENV")
        or ""
    ).strip().lower()


def is_production_runtime() -> bool:
    mode = runtime_mode()
    if mode in {"dev", "development", "demo", "local", "test"}:
        return False
    if mode in {"prod", "production", "live"}:
        return True
    return bool(os.environ.get("VERCEL"))


def demo_seed_enabled() -> bool:
    return env_flag(os.environ.get("SMM_PANEL_ENABLE_DEMO_SEED")) or env_flag(
        os.environ.get("SMM_PANEL_ENABLE_SAMPLE_SEED")
    )


def now_iso() -> str:
    import datetime as dt

    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class PanelStoreDatabaseMixin:
    default_db_path: Path
    schema_sql: str
    runtime_schema_version: str

    def __init__(self, db_path: Optional[Path] = None, database_url: str = "") -> None:
        self.db_path = db_path or self.default_db_path
        self.database_url = str(database_url or "").strip()
        if self.database_url:
            if not self.database_url.startswith(("postgres://", "postgresql://")):
                raise RuntimeError("SMM_PANEL_DATABASE_URL must be a postgres connection string.")
            self.backend = "postgres"
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.backend = "sqlite"
        self._boot()

    @classmethod
    def from_env(cls, db_path: Optional[Path] = None):
        database_url = (
            os.environ.get("SMM_PANEL_DATABASE_URL", "").strip()
            or os.environ.get("SMM_PANEL_SUPABASE_DB_URL", "").strip()
        )
        if not database_url and is_production_runtime():
            raise RuntimeError(
                "SMM_PANEL_DATABASE_URL or SMM_PANEL_SUPABASE_DB_URL is required in production. "
                "Refusing to start with a temporary SQLite database."
            )
        return cls(db_path=db_path or cls.default_db_path, database_url=database_url)

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

    def _boot(self) -> None:
        if self.backend == "postgres" and is_production_runtime():
            try:
                with self._connect() as conn:
                    schema_version = self._runtime_metadata_value_if_available(conn, "schema_version")
                    if schema_version == self.runtime_schema_version and not self._runtime_schema_repair_needed(conn):
                        return
            except Exception:
                pass
        self._initialize()

    def _initialize(self) -> None:
        with self._connect() as conn:
            previous_schema_version = self._runtime_metadata_value_if_available(conn, "schema_version")
            if not previous_schema_version:
                conn.executescript(self.schema_sql)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            schema_version = self._runtime_metadata_value(conn, "schema_version")
            schema_repair_needed = self._runtime_schema_repair_needed(conn)
            if schema_version != self.runtime_schema_version or schema_repair_needed:
                self._apply_migrations(conn)
                self._set_runtime_metadata(conn, "schema_version", self.runtime_schema_version)
            has_categories = conn.execute("SELECT COUNT(*) AS count FROM product_categories").fetchone()["count"]
            if not has_categories:
                self._seed(conn)
            self._ensure_home_popup(conn)
            self._ensure_site_settings(conn)
            self._clear_mkt24_bearer_tokens(conn)
            if demo_seed_enabled():
                self._seed_management_samples(conn)
                self._ensure_management_order_samples(conn)
                self._ensure_analytics_samples(conn)
            if self._wallet_runtime_repair_needed(conn):
                self._sync_wallet_state(conn)
            conn.commit()

    def _runtime_metadata_value(self, conn: DatabaseConnection, key: str) -> str:
        row = conn.execute("SELECT value FROM runtime_metadata WHERE key = ?", (key,)).fetchone()
        if row is None:
            return ""
        return str(row["value"] or "")

    def _runtime_metadata_value_if_available(self, conn: DatabaseConnection, key: str) -> str:
        try:
            return self._runtime_metadata_value(conn, key)
        except Exception:
            return ""

    def _set_runtime_metadata(self, conn: DatabaseConnection, key: str, value: str) -> None:
        conn.execute(
            """
            INSERT INTO runtime_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now_iso()),
        )

    def _runtime_schema_repair_needed(self, conn: DatabaseConnection) -> bool:
        required_tables = ("notification_events", "cafe24_split_jobs", "cafe24_split_job_parts")
        placeholders = ", ".join(["?"] * len(required_tables))
        try:
            if self.backend == "postgres":
                rows = conn.execute(
                    f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name IN ({placeholders})
                    """,
                    required_tables,
                ).fetchall()
                present = {str(row["table_name"] or "") for row in rows}
            else:
                rows = conn.execute(
                    f"""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name IN ({placeholders})
                    """,
                    required_tables,
                ).fetchall()
                present = {str(row["name"] or "") for row in rows}
        except Exception:
            return True
        return any(table not in present for table in required_tables)

    def _apply_migrations(self, conn: DatabaseConnection) -> None:
        self._ensure_column(conn, "users", "password_hash", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'customer'")
        self._ensure_column(conn, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "users", "account_status", "TEXT NOT NULL DEFAULT 'active'")
        self._ensure_column(conn, "users", "marketing_opt_in", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "users", "marketing_opt_in_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "withdrawn_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "suspended_reason", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "notes", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "users", "last_login_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "platform_sections", "image_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "site_settings", "header_logo_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "home_banners", "image_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "home_banners", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "product_categories", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "products", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "suppliers", "integration_type", "TEXT NOT NULL DEFAULT 'classic'")
        self._ensure_column(conn, "suppliers", "bearer_token", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "service_sync_status", "TEXT NOT NULL DEFAULT 'never'")
        self._ensure_column(conn, "suppliers", "service_sync_message", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "service_sync_started_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "service_sync_completed_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "service_sync_lock_until", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "service_sync_error_count", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "suppliers", "service_sync_interval_minutes", "INTEGER NOT NULL DEFAULT 30")
        self._ensure_column(conn, "suppliers", "health_status", "TEXT NOT NULL DEFAULT 'unknown'")
        self._ensure_column(conn, "suppliers", "health_message", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "health_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "suppliers", "balance_status", "TEXT NOT NULL DEFAULT 'unknown'")
        self._ensure_column(conn, "suppliers", "balance_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._migrate_mkt24_panel_endpoint(conn)
        self._clear_mkt24_bearer_tokens(conn)
        self._ensure_column(conn, "supplier_services", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "supplier_services", "last_seen_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "supplier_services", "removed_at", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_supplier_services_supplier_active
                ON supplier_services(supplier_id, is_active, category, name)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_suppliers_service_sync_status
                ON suppliers(is_active, service_sync_status, service_sync_completed_at)
            """
        )
        conn.execute(
            """
            UPDATE supplier_services
            SET last_seen_at = COALESCE(NULLIF(last_seen_at, ''), synced_at)
            WHERE last_seen_at = ''
            """
        )
        self._ensure_column(conn, "home_popups", "image_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "site_visit_events", "exclude_from_stats", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "charge_orders", "payment_payload_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "charge_orders", "bank_account_snapshot_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "charge_orders", "confirmed_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "orders", "idempotency_key", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "orders", "order_channel", "TEXT NOT NULL DEFAULT 'web'")
        self._ensure_column(conn, "orders", "external_order_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "orders", "external_order_item_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "orders", "dispatch_status", "TEXT NOT NULL DEFAULT 'unmapped'")
        self._ensure_column(conn, "orders", "dispatch_attempts", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "orders", "supplier_last_error", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "orders", "external_payload_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "supplier_orders", "last_status_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "supplier_orders", "next_status_check_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "supplier_orders", "status_check_attempts", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "supplier_orders", "status_check_message", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_user_idempotency_key
                ON orders(user_id, idempotency_key)
                WHERE idempotency_key <> ''
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_channel_external_reference
                ON orders(order_channel, external_order_id, external_order_item_id)
                WHERE external_order_id <> ''
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_channel_status_created_at
                ON orders(order_channel, status, created_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_dispatch_status_created_at
                ON orders(dispatch_status, created_at DESC)
            """
        )
        self._ensure_charge_support_tables(conn)
        self._ensure_notification_events_table(conn)
        self._ensure_cafe24_support_tables(conn)
        self._ensure_cafe24_split_support_tables(conn)
        self._ensure_mkt24_product_settings_table(conn)
        self._ensure_column(conn, "cafe24_product_mappings", "supplier_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_product_mappings", "supplier_product_uuid", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_product_mappings", "supplier_product_code", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_product_mappings", "field_mapping_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "cafe24_product_mappings", "enabled", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "cafe24_supplier_mappings", "supplier_service_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_supplier_mappings", "enabled", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(conn, "cafe24_integrations", "token_status", "TEXT NOT NULL DEFAULT 'connected'")
        self._ensure_column(conn, "cafe24_integrations", "token_last_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "token_last_refreshed_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "token_refresh_lock_until", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "token_refresh_lock_owner", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "reconnect_required_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "reconnect_reason", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "cafe24_poll_lock_until", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "cafe24_poll_lock_owner", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "last_auto_poll_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_integrations", "last_auto_poll_status", "TEXT NOT NULL DEFAULT 'never'")
        self._ensure_column(conn, "cafe24_integrations", "last_auto_poll_message", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_order_date", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_status", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_status_source", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_gate_status", "TEXT NOT NULL DEFAULT 'unverified'")
        self._ensure_column(conn, "cafe24_order_items", "payment_method", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_amount", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "cafe24_order_items", "payment_paid_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_reference", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "payment_snapshot_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "cafe24_order_items", "standard_status", "TEXT NOT NULL DEFAULT 'received'")
        self._ensure_column(conn, "cafe24_order_items", "internal_order_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "supplier_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "supplier_service_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "supplier_external_service_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "supplier_response_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column(conn, "cafe24_order_items", "next_retry_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "automation_last_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "automation_error_code", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "auto_dispatch_approved", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "cafe24_order_items", "auto_dispatch_source", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "preflight_checked_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "preflight_blockers_json", "TEXT NOT NULL DEFAULT '[]'")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_completion_status", "TEXT NOT NULL DEFAULT 'pending'")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_completion_message", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_completed_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_completion_attempts", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(conn, "cafe24_order_items", "cafe24_next_completion_retry_at", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_supplier_orders_next_status_check
                ON supplier_orders(status, next_status_check_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_automation_retry
                ON cafe24_order_items(standard_status, next_retry_at, payment_gate_status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_completion_retry
                ON cafe24_order_items(cafe24_completion_status, cafe24_next_completion_retry_at)
            """
        )
        if not is_production_runtime():
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_oauth_states_expires_at
                    ON cafe24_oauth_states(expires_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_integrations_active
                    ON cafe24_integrations(is_active, updated_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_product_mappings_product
                    ON cafe24_product_mappings(internal_product_id, enabled)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_supplier_mappings_supplier
                    ON cafe24_supplier_mappings(supplier_id, supplier_service_id, enabled)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_status_updated_at
                    ON cafe24_order_items(standard_status, updated_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_order_date
                    ON cafe24_order_items(mall_id, shop_no, cafe24_order_date DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_internal_order
                    ON cafe24_order_items(internal_order_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cafe24_api_events_created_at
                    ON cafe24_api_events(created_at DESC)
                """
            )
        conn.execute("UPDATE cafe24_integrations SET auto_submit = 1 WHERE is_active = 1")
        self._migrate_cafe24_supplier_mappings(conn)
        if not is_production_runtime():
            self._ensure_bigint_columns(
                conn,
                {
                    "wallets": ["available_balance", "pending_balance"],
                    "charge_orders": ["amount", "vat_amount", "total_amount"],
                    "wallet_ledger": ["amount", "balance_after"],
                    "payment_records": ["amount"],
                    "balance_transactions": ["amount", "balance_after"],
                },
            )
        conn.execute("UPDATE users SET email = lower(trim(email)) WHERE email != lower(trim(email))")
        conn.execute("UPDATE support_links SET route = '/help#faq' WHERE id = 'support_faq'")
        conn.execute("UPDATE support_links SET route = '/help#notice' WHERE id = 'support_notice'")
        conn.execute("UPDATE support_links SET route = '/help#guide' WHERE id = 'support_guide'")
        conn.execute(
            "UPDATE users SET account_status = CASE WHEN is_active = 1 THEN 'active' ELSE 'suspended' END WHERE COALESCE(account_status, '') = ''"
        )
        demo_user_id = getattr(self, "demo_user_id", "user_demo")
        conn.execute("UPDATE users SET role = 'admin', is_active = 1, account_status = 'active' WHERE id = ?", (demo_user_id,))
        conn.execute("UPDATE users SET role = COALESCE(NULLIF(role, ''), 'customer') WHERE id != ?", (demo_user_id,))
        self._migrate_supplier_secrets(conn)

    def _ensure_notification_events_table(self, conn: DatabaseConnection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_events (
                id TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                event_key TEXT NOT NULL,
                event_type TEXT NOT NULL DEFAULT '',
                entity_type TEXT NOT NULL DEFAULT '',
                entity_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                last_error TEXT NOT NULL DEFAULT '',
                sent_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(channel, event_key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notification_events_status_updated_at
                ON notification_events(channel, status, updated_at DESC)
            """
        )

    def _ensure_cafe24_split_support_tables(self, conn: DatabaseConnection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cafe24_split_jobs (
                id TEXT PRIMARY KEY,
                cafe24_order_item_id TEXT NOT NULL REFERENCES cafe24_order_items(id) ON DELETE CASCADE,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                cafe24_order_id TEXT NOT NULL,
                cafe24_order_item_code TEXT NOT NULL DEFAULT '',
                dispatch_mode TEXT NOT NULL DEFAULT 'daily_split',
                status TEXT NOT NULL DEFAULT 'scheduled',
                target_value TEXT NOT NULL DEFAULT '',
                total_quantity INTEGER NOT NULL DEFAULT 0,
                daily_quantity INTEGER NOT NULL DEFAULT 0,
                duration_days INTEGER NOT NULL DEFAULT 0,
                dispatched_parts INTEGER NOT NULL DEFAULT 0,
                completed_parts INTEGER NOT NULL DEFAULT 0,
                failed_parts INTEGER NOT NULL DEFAULT 0,
                supplier_id TEXT NOT NULL DEFAULT '',
                supplier_service_id TEXT NOT NULL DEFAULT '',
                supplier_external_service_id TEXT NOT NULL DEFAULT '',
                normalized_fields_json TEXT NOT NULL DEFAULT '{}',
                supplier_payload_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT '',
                next_dispatch_at TEXT NOT NULL DEFAULT '',
                last_dispatch_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(cafe24_order_item_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cafe24_split_jobs_status_next
                ON cafe24_split_jobs(status, next_dispatch_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cafe24_split_job_parts (
                id TEXT PRIMARY KEY,
                split_job_id TEXT NOT NULL REFERENCES cafe24_split_jobs(id) ON DELETE CASCADE,
                cafe24_order_item_id TEXT NOT NULL REFERENCES cafe24_order_items(id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                supplier_order_id TEXT NOT NULL DEFAULT '',
                supplier_order_uuid TEXT NOT NULL DEFAULT '',
                supplier_response_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT '',
                dispatch_attempts INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT NOT NULL DEFAULT '',
                dispatched_at TEXT NOT NULL DEFAULT '',
                last_status_checked_at TEXT NOT NULL DEFAULT '',
                next_status_check_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(split_job_id, sequence)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cafe24_split_parts_due
                ON cafe24_split_job_parts(status, scheduled_at, next_retry_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cafe24_split_parts_status_check
                ON cafe24_split_job_parts(status, next_status_check_at)
            """
        )

    def _migrate_mkt24_panel_endpoint(self, conn: DatabaseConnection) -> None:
        rows = conn.execute(
            """
            SELECT id
            FROM suppliers
            WHERE integration_type = 'mkt24'
              AND lower(api_url) LIKE '%api.mkt24.co.kr%'
              AND lower(api_url) NOT LIKE '%/panel'
            """
        ).fetchall()
        supplier_ids = [str(row["id"]) for row in rows]
        if not supplier_ids:
            return
        timestamp = now_iso()
        placeholders = ",".join("?" for _ in supplier_ids)
        conn.execute(
            f"""
            UPDATE suppliers
            SET api_url = ?,
                last_test_status = 'never',
                last_test_message = ?,
                last_service_count = 0,
                service_sync_status = 'never',
                service_sync_message = ?,
                service_sync_started_at = '',
                service_sync_completed_at = '',
                service_sync_lock_until = '',
                service_sync_error_count = 0,
                health_status = 'unknown',
                health_message = '',
                health_checked_at = '',
                balance_status = 'unknown',
                balance_checked_at = '',
                updated_at = ?
            WHERE id IN ({placeholders})
            """,
            (
                "https://api.mkt24.co.kr/v3/panel",
                "MKT24 대행사용 API endpoint가 /v3/panel로 전환되었습니다. 연결 확인과 서비스 동기화를 다시 실행하세요.",
                "MKT24 대행사용 API endpoint가 /v3/panel로 전환되었습니다. 서비스 동기화가 필요합니다.",
                timestamp,
                *supplier_ids,
            ),
        )
        conn.execute(
            f"""
            UPDATE supplier_services
            SET is_active = 0,
                removed_at = ?,
                synced_at = ?
            WHERE supplier_id IN ({placeholders})
              AND is_active = 1
            """,
            (timestamp, timestamp, *supplier_ids),
        )

    def _clear_mkt24_bearer_tokens(self, conn: DatabaseConnection) -> None:
        conn.execute(
            """
            UPDATE suppliers
            SET bearer_token = '',
                updated_at = ?
            WHERE integration_type = 'mkt24'
              AND COALESCE(bearer_token, '') <> ''
            """,
            (now_iso(),),
        )

    def _ensure_bigint_columns(self, conn: DatabaseConnection, table_columns: Dict[str, List[str]]) -> None:
        if self.backend != "postgres":
            return
        for table, columns in table_columns.items():
            for column in columns:
                conn.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE BIGINT")

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
