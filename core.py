from __future__ import annotations

import base64
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
import time
from html import escape as html_escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
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

try:
    from .backend.errors import PanelError
    from .backend.db import DatabaseConnection, DatabaseCursor, PanelStoreDatabaseMixin, normalize_database_row, rewrite_postgres_placeholders, split_sql_script
    from .backend.auth import (
        assess_public_password_strength,
        generate_email_verification_code,
        hash_password,
        hash_token_value,
        password_contains_repeated_pattern,
        password_contains_sequence,
        verify_password,
    )
    from .backend.orders import (
        ORDER_CHANNEL_CAFE24,
        ORDER_CHANNEL_MANUAL,
        ORDER_CHANNEL_WEB,
        ORDER_CHANNELS,
        ORDER_DISPATCH_ACCEPTED,
        ORDER_DISPATCH_CANCELLED,
        ORDER_DISPATCH_COMPLETED,
        ORDER_DISPATCH_FAILED,
        ORDER_DISPATCH_IN_PROGRESS,
        ORDER_DISPATCH_PARTIAL,
        ORDER_DISPATCH_READY,
        ORDER_DISPATCH_STATUSES,
        ORDER_DISPATCH_SUBMITTED,
        ORDER_DISPATCH_UNMAPPED,
        ORDER_EXTERNAL_REFERENCE_MAX_LENGTH,
        automation_paused as _automation_paused,
        automation_retry_at as _automation_retry_at,
        canonical_order_field_value as _canonical_order_field_value,
        derive_order_idempotency_key,
        generate_public_order_number,
        normalize_order_channel as _normalize_order_channel,
        normalize_order_dispatch_status,
        order_channel_label,
        order_submission_payload,
        parse_iso_datetime as _parse_order_iso_datetime,
        sanitize_external_order_reference,
        sanitize_idempotency_key,
    )
    from .backend.payments import normalize_webhook_signature, verify_payment_webhook_signature
    from .backend.wallet import (
        ChargeOrderRequestError,
        admin_charge_order_payload as _admin_charge_order_payload,
        charge_order_filter_clause,
        charge_order_payload as _charge_order_payload,
        balance_transaction_kind_to_ledger_entry_type,
        charge_amount_breakdown as _charge_amount_breakdown,
        generate_charge_order_code,
        money_label as _money_label,
        normalize_charge_order_request,
        normalize_charge_payment_channel as _normalize_charge_payment_channel,
        payment_method_detail_label as _payment_method_detail_label,
        payment_method_label as _payment_method_label,
        payment_status_label as _payment_status_label,
        receipt_type_label as _receipt_type_label,
        resolve_charge_expiry as _resolve_charge_expiry,
        wallet_balances_payload,
        wallet_ledger_entry_payload,
        wallet_ledger_filter_clause,
    )
    from .backend.integrations.cafe24 import (
        Cafe24ApiClient,
        Cafe24ApiError,
        Cafe24DispatchRequestError,
        Cafe24PollWindowError,
        CAFE24_ORDER_ITEM_DATE_EXPR,
        CAFE24_STANDARD_STATUSES,
        cafe24_access_token_error,
        cafe24_api_base_url,
        cafe24_auto_poll_due as _cafe24_auto_poll_due,
        cafe24_client_id,
        cafe24_client_secret,
        cafe24_default_poll_window as _cafe24_default_poll_window,
        cafe24_dispatch_request_context,
        cafe24_enriched_product_payload,
        cafe24_integration_payload_from_row,
        cafe24_item_identity,
        cafe24_mapping_payload_from_row,
        cafe24_next_auto_poll_at as _cafe24_next_auto_poll_at,
        cafe24_normalize_datetime_text,
        cafe24_oauth_timestamp_from_response,
        cafe24_order_date_from_payload,
        cafe24_order_has_embedded_items,
        cafe24_order_item_filter_clauses,
        cafe24_order_item_list_options,
        cafe24_order_item_pagination_payload,
        cafe24_order_item_payload_from_row,
        cafe24_order_item_summary_payload,
        cafe24_order_items_from_order,
        cafe24_orders_from_payload,
        cafe24_option_entries,
        cafe24_option_pairs,
        cafe24_payload_value,
        cafe24_payment_gate_status,
        cafe24_payment_snapshot_from_payload,
        cafe24_payment_status_from_payload,
        cafe24_payment_status_with_source,
        cafe24_poll_datetime_window as _cafe24_poll_datetime_window,
        cafe24_product_payload,
        cafe24_product_variants_from_payload,
        cafe24_products_from_payload,
        cafe24_supplier_dispatch_outcome,
        cafe24_supplier_dispatch_state,
        cafe24_target_diagnostics,
        cafe24_token_status as _cafe24_token_status,
        cafe24_token_status_label as _cafe24_token_status_label,
        cafe24_token_status_message as _cafe24_token_status_message,
        cafe24_variant_payload,
        cafe24_processing_error_status,
        cafe24_refresh_error_requires_reconnect,
        cafe24_refresh_token_expired,
        cafe24_refresh_token_expiring_soon,
        cafe24_redirect_uri,
        cafe24_status_is_cancelled,
        cafe24_status_is_payment_blocked,
        cafe24_status_is_supply_eligible,
        cafe24_status_needs_operator_action,
        normalize_cafe24_payment_status,
        normalize_cafe24_scopes,
        normalize_cafe24_shop_no,
        normalize_cafe24_status,
    )
    from .backend.integrations.cafe24_audit import build_cafe24_operational_audit
    from .backend.integrations.cafe24_mapping_gaps import (
        annotate_cafe24_mapping_gap_groups,
        cafe24_mapping_gap_item_payload,
        cafe24_mapping_gap_report_options,
        fetch_cafe24_mapping_gap_product_details,
        summarize_cafe24_mapping_gaps,
    )
    from .backend.integrations.cafe24_manual import (
        build_cafe24_manual_input_plan_payload,
        build_cafe24_manual_input_preview_response,
        cafe24_manual_product_payload,
        cafe24_manual_supplier_mapping,
    )
    from .backend.integrations.cafe24_panel import (
        cafe24_expected_quantity_from_payload_for_panel,
        cafe24_manual_expected_quantity_for_panel,
        cafe24_manual_input_request_for_panel,
        cafe24_order_item_id_for_panel,
        cafe24_order_item_selector_for_panel,
        cafe24_validate_manual_input_order_item_for_panel,
        cafe24_validate_manual_input_supplier_for_panel,
        coerce_cafe24_ordered_count_mapping_value_for_panel,
        default_cafe24_ordered_count_for_panel,
        resolve_cafe24_quantity_candidates_for_panel,
        validate_cafe24_direct_fields_for_panel,
    )
    from .backend.integrations.cafe24_preflight import (
        build_cafe24_mapping_preview_report,
        build_cafe24_order_item_preflight,
        cafe24_preflight_quantity,
        redact_cafe24_preview_value,
    )
    from .backend.integrations.cafe24_quantity import (
        cafe24_quantity_candidates_from_options,
    )
    from .backend.integrations.mkt24_settings import (
        Mkt24SettingsError,
        build_mkt24_order_payload_from_setting,
        default_mkt24_field_config,
        default_mkt24_option_config,
        mkt24_detail_data,
        normalize_mkt24_field_config,
        resolve_mkt24_field_value,
        validate_mkt24_option_config as _validate_mkt24_option_config,
    )
    from .backend.integrations.supplier_targets import (
        ACCOUNT_STYLE_PLATFORMS,
        account_preview_url,
        platform_target_error_message,
        platform_target_url_matches,
        preview_platform_hint,
        supplier_panel_target_link,
        supplier_supported_hosts,
        validate_supplier_panel_target_link,
        SupplierTargetError,
    )
    from .backend.integrations.suppliers import (
        FASTTRAFFIC_API_URL,
        SUPPLIER_INTEGRATION_FASTTRAFFIC,
        SupplierApiClient,
        SupplierApiError,
        supplier_auto_dispatch_readiness,
        supplier_auto_dispatch_readiness_payload,
        supplier_error_is_auth_failure,
        normalize_fasttraffic_candidates,
        normalize_mkt24_candidates,
        normalize_supplier_integration_type,
        normalize_supplier_api_candidates,
        normalize_supplier_services_payload,
        normalize_supplier_order_status_payload,
        supplier_service_record,
        supplier_request_timeout_seconds,
        supplier_uses_panel_api,
        supplier_service_sync_due,
        supplier_supports_auto_dispatch,
        supplier_supports_balance_check,
        supplier_sync_interval_minutes,
    )
except ImportError:  # pragma: no cover - top-level script runtime
    from backend.errors import PanelError
    from backend.db import DatabaseConnection, DatabaseCursor, PanelStoreDatabaseMixin, normalize_database_row, rewrite_postgres_placeholders, split_sql_script
    from backend.auth import (
        assess_public_password_strength,
        generate_email_verification_code,
        hash_password,
        hash_token_value,
        password_contains_repeated_pattern,
        password_contains_sequence,
        verify_password,
    )
    from backend.orders import (
        ORDER_CHANNEL_CAFE24,
        ORDER_CHANNEL_MANUAL,
        ORDER_CHANNEL_WEB,
        ORDER_CHANNELS,
        ORDER_DISPATCH_ACCEPTED,
        ORDER_DISPATCH_CANCELLED,
        ORDER_DISPATCH_COMPLETED,
        ORDER_DISPATCH_FAILED,
        ORDER_DISPATCH_IN_PROGRESS,
        ORDER_DISPATCH_PARTIAL,
        ORDER_DISPATCH_READY,
        ORDER_DISPATCH_STATUSES,
        ORDER_DISPATCH_SUBMITTED,
        ORDER_DISPATCH_UNMAPPED,
        ORDER_EXTERNAL_REFERENCE_MAX_LENGTH,
        automation_paused as _automation_paused,
        automation_retry_at as _automation_retry_at,
        canonical_order_field_value as _canonical_order_field_value,
        derive_order_idempotency_key,
        generate_public_order_number,
        normalize_order_channel as _normalize_order_channel,
        normalize_order_dispatch_status,
        order_channel_label,
        order_submission_payload,
        parse_iso_datetime as _parse_order_iso_datetime,
        sanitize_external_order_reference,
        sanitize_idempotency_key,
    )
    from backend.payments import normalize_webhook_signature, verify_payment_webhook_signature
    from backend.wallet import (
        ChargeOrderRequestError,
        admin_charge_order_payload as _admin_charge_order_payload,
        charge_order_filter_clause,
        charge_order_payload as _charge_order_payload,
        balance_transaction_kind_to_ledger_entry_type,
        charge_amount_breakdown as _charge_amount_breakdown,
        generate_charge_order_code,
        money_label as _money_label,
        normalize_charge_order_request,
        normalize_charge_payment_channel as _normalize_charge_payment_channel,
        payment_method_detail_label as _payment_method_detail_label,
        payment_method_label as _payment_method_label,
        payment_status_label as _payment_status_label,
        receipt_type_label as _receipt_type_label,
        resolve_charge_expiry as _resolve_charge_expiry,
        wallet_balances_payload,
        wallet_ledger_entry_payload,
        wallet_ledger_filter_clause,
    )
    from backend.integrations.cafe24 import (
        Cafe24ApiClient,
        Cafe24ApiError,
        Cafe24DispatchRequestError,
        Cafe24PollWindowError,
        CAFE24_ORDER_ITEM_DATE_EXPR,
        CAFE24_STANDARD_STATUSES,
        cafe24_access_token_error,
        cafe24_api_base_url,
        cafe24_auto_poll_due as _cafe24_auto_poll_due,
        cafe24_client_id,
        cafe24_client_secret,
        cafe24_default_poll_window as _cafe24_default_poll_window,
        cafe24_dispatch_request_context,
        cafe24_enriched_product_payload,
        cafe24_integration_payload_from_row,
        cafe24_item_identity,
        cafe24_mapping_payload_from_row,
        cafe24_next_auto_poll_at as _cafe24_next_auto_poll_at,
        cafe24_normalize_datetime_text,
        cafe24_oauth_timestamp_from_response,
        cafe24_order_date_from_payload,
        cafe24_order_has_embedded_items,
        cafe24_order_item_filter_clauses,
        cafe24_order_item_list_options,
        cafe24_order_item_pagination_payload,
        cafe24_order_item_payload_from_row,
        cafe24_order_item_summary_payload,
        cafe24_order_items_from_order,
        cafe24_orders_from_payload,
        cafe24_option_entries,
        cafe24_option_pairs,
        cafe24_payload_value,
        cafe24_payment_gate_status,
        cafe24_payment_snapshot_from_payload,
        cafe24_payment_status_from_payload,
        cafe24_payment_status_with_source,
        cafe24_poll_datetime_window as _cafe24_poll_datetime_window,
        cafe24_product_payload,
        cafe24_product_variants_from_payload,
        cafe24_products_from_payload,
        cafe24_supplier_dispatch_outcome,
        cafe24_supplier_dispatch_state,
        cafe24_target_diagnostics,
        cafe24_token_status as _cafe24_token_status,
        cafe24_token_status_label as _cafe24_token_status_label,
        cafe24_token_status_message as _cafe24_token_status_message,
        cafe24_variant_payload,
        cafe24_processing_error_status,
        cafe24_refresh_error_requires_reconnect,
        cafe24_refresh_token_expired,
        cafe24_refresh_token_expiring_soon,
        cafe24_redirect_uri,
        cafe24_status_is_cancelled,
        cafe24_status_is_payment_blocked,
        cafe24_status_is_supply_eligible,
        cafe24_status_needs_operator_action,
        normalize_cafe24_payment_status,
        normalize_cafe24_scopes,
        normalize_cafe24_shop_no,
        normalize_cafe24_status,
    )
    from backend.integrations.cafe24_audit import build_cafe24_operational_audit
    from backend.integrations.cafe24_mapping_gaps import (
        annotate_cafe24_mapping_gap_groups,
        cafe24_mapping_gap_item_payload,
        cafe24_mapping_gap_report_options,
        fetch_cafe24_mapping_gap_product_details,
        summarize_cafe24_mapping_gaps,
    )
    from backend.integrations.cafe24_manual import (
        build_cafe24_manual_input_plan_payload,
        build_cafe24_manual_input_preview_response,
        cafe24_manual_product_payload,
        cafe24_manual_supplier_mapping,
    )
    from backend.integrations.cafe24_panel import (
        cafe24_expected_quantity_from_payload_for_panel,
        cafe24_manual_expected_quantity_for_panel,
        cafe24_manual_input_request_for_panel,
        cafe24_order_item_id_for_panel,
        cafe24_order_item_selector_for_panel,
        cafe24_validate_manual_input_order_item_for_panel,
        cafe24_validate_manual_input_supplier_for_panel,
        coerce_cafe24_ordered_count_mapping_value_for_panel,
        default_cafe24_ordered_count_for_panel,
        resolve_cafe24_quantity_candidates_for_panel,
        validate_cafe24_direct_fields_for_panel,
    )
    from backend.integrations.cafe24_preflight import (
        build_cafe24_mapping_preview_report,
        build_cafe24_order_item_preflight,
        cafe24_preflight_quantity,
        redact_cafe24_preview_value,
    )
    from backend.integrations.cafe24_quantity import (
        cafe24_quantity_candidates_from_options,
    )
    from backend.integrations.mkt24_settings import (
        Mkt24SettingsError,
        build_mkt24_order_payload_from_setting,
        default_mkt24_field_config,
        default_mkt24_option_config,
        mkt24_detail_data,
        normalize_mkt24_field_config,
        resolve_mkt24_field_value,
        validate_mkt24_option_config as _validate_mkt24_option_config,
    )
    from backend.integrations.supplier_targets import (
        ACCOUNT_STYLE_PLATFORMS,
        account_preview_url,
        platform_target_error_message,
        platform_target_url_matches,
        preview_platform_hint,
        supplier_panel_target_link,
        supplier_supported_hosts,
        validate_supplier_panel_target_link,
        SupplierTargetError,
    )
    from backend.integrations.suppliers import (
        FASTTRAFFIC_API_URL,
        SUPPLIER_INTEGRATION_FASTTRAFFIC,
        SupplierApiClient,
        SupplierApiError,
        supplier_auto_dispatch_readiness,
        supplier_auto_dispatch_readiness_payload,
        supplier_error_is_auth_failure,
        normalize_fasttraffic_candidates,
        normalize_mkt24_candidates,
        normalize_supplier_integration_type,
        normalize_supplier_api_candidates,
        normalize_supplier_services_payload,
        normalize_supplier_order_status_payload,
        supplier_service_record,
        supplier_request_timeout_seconds,
        supplier_uses_panel_api,
        supplier_service_sync_due,
        supplier_supports_auto_dispatch,
        supplier_supports_balance_check,
        supplier_sync_interval_minutes,
    )


APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = APP_ROOT / "data"
DB_PATH = DATA_ROOT / "smm_panel.db"
DEMO_USER_ID = "user_demo"
PREVIEW_TIMEOUT_SECONDS = 6
DEFAULT_SITE_NAME = "인스타마트"
DEFAULT_SITE_DESCRIPTION = "실제 판매형 SNS 마케팅 서비스 쇼핑몰"
LEGACY_DEFAULT_SITE_NAMES = {"Pulse24", "Pulse24 Panel"}
LEGACY_DEFAULT_SITE_DESCRIPTIONS = {"Reference-style SMM Growth Panel"}
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
MKT24_PANEL_API_URL = "https://api.mkt24.co.kr/v3/panel"
SUPPLIER_SERVICE_SYNC_DEFAULT_INTERVAL_MINUTES = 30
SUPPLIER_SERVICE_SYNC_LOCK_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_BASE_MINUTES = 10
SUPPLIER_SERVICE_SYNC_RETRY_MAX_MINUTES = 60
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
LEGAL_DOCUMENT_VERSIONS = {
    "terms": "2026-04-18",
    "privacy": "2026-04-18",
    "marketing": "2026-04-18",
    "age": "2026-04-18",
}
AUTH_VERIFICATION_PURPOSE_SIGNUP = "signup"
AUTH_VERIFICATION_CODE_LENGTH = 6
AUTH_VERIFICATION_TTL_SECONDS = 10 * 60
AUTH_VERIFICATION_COMPLETE_TTL_SECONDS = 30 * 60
AUTH_VERIFICATION_RESEND_INTERVAL_SECONDS = 60
AUTH_VERIFICATION_MAX_ATTEMPTS = 5
PUBLIC_PASSWORD_MIN_LENGTH = 10
PUBLIC_PASSWORD_RECOMMENDED_LENGTH = 12
PUBLIC_PASSWORD_VERY_STRONG_LENGTH = 14
ORDER_IDEMPOTENCY_KEY_MAX_LENGTH = 120
ORDER_AUTO_IDEMPOTENCY_WINDOW_SECONDS = 2 * 60
CAFE24_ORDER_CHANNEL = ORDER_CHANNEL_CAFE24
CAFE24_DEFAULT_SHOP_NO = 1
CAFE24_OAUTH_STATE_TTL_SECONDS = 10 * 60
CAFE24_DEFAULT_SCOPES = ("mall.read_order", "mall.write_order", "mall.read_product")
CAFE24_REFRESH_LOCK_SECONDS = 90
CAFE24_POLL_LOCK_SECONDS = 8 * 60
CAFE24_AUTO_POLL_INTERVAL_MINUTES = 5
AUTOMATION_RETRY_MAX_ATTEMPTS = 3
SUPPLIER_STATUS_CHECK_INTERVAL_MINUTES = 10
CAFE24_COMPLETION_RETRY_INTERVAL_MINUTES = 10
CAFE24_REFRESH_TOKEN_EXPIRY_WARNING_DAYS = 2
CAFE24_TOKEN_STATUS_CONNECTED = "connected"
CAFE24_TOKEN_STATUS_EXPIRING = "token_expiring"
CAFE24_TOKEN_STATUS_REFRESHING = "refreshing"
CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED = "reconnect_required"
CAFE24_TOKEN_STATUS_FAILED = "failed"
CAFE24_ORDER_OVERLAP_MINUTES = 20
CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS = 30
CAFE24_ORDER_PAGE_LIMIT = 1000
CAFE24_ORDER_MAX_PAGES = 30
CAFE24_FLOW_LOOKBACK_MINUTES = 180
CAFE24_FLOW_PAGE_LIMIT = 200
CAFE24_FLOW_MAX_PAGES = 3
CAFE24_FLOW_DETAIL_FETCH_LIMIT = 50
CAFE24_FLOW_DISPATCH_LIMIT = 50
CAFE24_FLOW_STATUS_LIMIT = 75
CAFE24_FLOW_COMPLETION_LIMIT = 50
CAFE24_FLOW_REQUEST_TIMEOUT_SECONDS = 5.0
CAFE24_FLOW_MAX_ATTEMPTS = 1
CAFE24_ORDER_ELIGIBLE_STATUSES = {"N10", "N20", "N21", "N22", "N30", "N40", "N50"}
CAFE24_ORDER_UNPAID_STATUSES = {"N00"}
CAFE24_ORDER_CANCELLED_PREFIXES = ("C", "R", "E")
CAFE24_PAYMENT_PAID_STATUSES = {"paid", "payment_confirmed", "confirmed", "complete", "completed", "done", "y", "true", "p", "a", "t"}
CAFE24_PAYMENT_PENDING_STATUSES = {"unpaid", "awaiting_payment", "pending", "ready", "waiting", "n", "false", "f"}
CAFE24_PAYMENT_CANCELLED_STATUSES = {"canceled", "cancelled", "cancel", "refunded", "refund", "void"}
WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = 5 * 60
SECRET_ENVELOPE_PREFIX = "enc:v1:"
SECRET_ENCRYPTION_KEY_MIN_LENGTH = 24
COMMON_PASSWORD_PATTERNS = {
    "12345678",
    "123456789",
    "1234567890",
    "11111111",
    "00000000",
    "password",
    "password1",
    "qwer1234",
    "qwerty123",
    "abc12345",
    "letmein",
    "welcome123",
    "admin1234",
    "instamart",
    "인스타마트",
}
KEYBOARD_SEQUENCE_PATTERNS = (
    "0123456789",
    "abcdefghijklmnopqrstuvwxyz",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
)


def env_flag(value: Any) -> bool:
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


def payment_provider_name() -> str:
    return str(os.environ.get("SMM_PANEL_PAYMENT_PROVIDER") or "").strip().lower()


def payment_public_key() -> str:
    return str(
        os.environ.get("SMM_PANEL_PAYMENT_PUBLIC_KEY")
        or os.environ.get("SMM_PANEL_PAYMENT_CLIENT_KEY")
        or ""
    ).strip()


def payment_secret_key() -> str:
    return str(os.environ.get("SMM_PANEL_PAYMENT_SECRET_KEY") or "").strip()


def payment_webhook_secret() -> str:
    return str(os.environ.get("SMM_PANEL_PAYMENT_WEBHOOK_SECRET") or "").strip()


def legacy_payment_webhook_secret_allowed() -> bool:
    return (not is_production_runtime()) or env_flag(os.environ.get("SMM_PANEL_ALLOW_LEGACY_WEBHOOK_SECRET"))


def card_payment_configured() -> bool:
    return bool(payment_provider_name() and payment_public_key() and payment_secret_key())


def bank_transfer_config() -> Dict[str, str]:
    config = {
        "bankName": str(os.environ.get("SMM_PANEL_BANK_NAME") or "").strip(),
        "accountNumber": str(os.environ.get("SMM_PANEL_BANK_ACCOUNT") or "").strip(),
        "accountHolder": str(os.environ.get("SMM_PANEL_BANK_ACCOUNT_HOLDER") or "").strip(),
        "depositGuide": str(os.environ.get("SMM_PANEL_BANK_DEPOSIT_GUIDE") or "").strip(),
    }
    if not is_production_runtime() and not (config["bankName"] and config["accountNumber"] and config["accountHolder"]):
        return {
            "bankName": config["bankName"] or "로컬은행",
            "accountNumber": config["accountNumber"] or "123-456-789012",
            "accountHolder": config["accountHolder"] or "인스타마트",
            "depositGuide": config["depositGuide"] or "로컬 확인용 계좌 정보입니다. 운영 환경에서는 실제 입금 계좌를 설정해 주세요.",
        }
    return config


def bank_transfer_configured() -> bool:
    config = bank_transfer_config()
    return bool(config["bankName"] and config["accountNumber"] and config["accountHolder"])


def auth_email_provider_name() -> str:
    return str(
        os.environ.get("SMM_PANEL_AUTH_EMAIL_PROVIDER")
        or os.environ.get("SMM_PANEL_EMAIL_PROVIDER")
        or ""
    ).strip().lower()


def auth_email_from_address() -> str:
    return str(
        os.environ.get("SMM_PANEL_AUTH_EMAIL_FROM")
        or os.environ.get("SMM_PANEL_EMAIL_FROM")
        or ""
    ).strip()


def auth_email_sender_name() -> str:
    return str(
        os.environ.get("SMM_PANEL_AUTH_EMAIL_SENDER_NAME")
        or os.environ.get("SMM_PANEL_EMAIL_SENDER_NAME")
        or DEFAULT_SITE_NAME
    ).strip()


def validate_public_password(password: str, *, email: str = "", name: str = "") -> None:
    assessment = assess_public_password_strength(password, email=email, name=name)
    if assessment["isValid"]:
        return
    if assessment["warnings"]:
        raise PanelError(assessment["warnings"][0])
    raise PanelError("비밀번호가 안전하지 않습니다. 더 길고 예측 어려운 비밀번호를 사용해 주세요.")


def dispatch_signup_verification_email(email: str, code: str, *, site_name: str = DEFAULT_SITE_NAME) -> Dict[str, Any]:
    provider = auth_email_provider_name()
    sender = auth_email_sender_name() or site_name
    from_address = auth_email_from_address()
    if not provider:
        if is_production_runtime():
            raise PanelError("이메일 인증 설정이 완료되지 않았습니다. 운영팀에 문의해 주세요.", status=503)
        print(f"[auth-email:preview] {sender} <{from_address or 'preview@example.com'}> -> {email} code={code}")
        return {"deliveryMode": "preview", "previewCode": code}
    if provider in {"preview", "console", "log"}:
        print(f"[auth-email:{provider}] {sender} <{from_address or 'preview@example.com'}> -> {email} code={code}")
        return {"deliveryMode": provider, "previewCode": code if not is_production_runtime() else ""}
    raise PanelError("현재 이메일 발송 provider 구현이 필요합니다. 운영 설정을 확인해 주세요.", status=503)


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
    avatar_label TEXT NOT NULL DEFAULT 'IM',
    balance INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    account_status TEXT NOT NULL DEFAULT 'active',
    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
    marketing_opt_in_at TEXT NOT NULL DEFAULT '',
    withdrawn_at TEXT NOT NULL DEFAULT '',
    suspended_reason TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    last_login_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
    ON users(email);

CREATE TABLE IF NOT EXISTS user_social_identities (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    provider_email TEXT NOT NULL DEFAULT '',
    linked_at TEXT NOT NULL,
    last_login_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS user_consents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    is_agreed INTEGER NOT NULL DEFAULT 0,
    agreed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, consent_type, consent_version)
);

CREATE TABLE IF NOT EXISTS user_auth_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_type TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(token_type, token_hash)
);

CREATE TABLE IF NOT EXISTS email_verification_challenges (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    purpose TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    verification_token_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    send_count INTEGER NOT NULL DEFAULT 1,
    last_sent_at TEXT NOT NULL DEFAULT '',
    resend_available_at TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL,
    verified_at TEXT NOT NULL DEFAULT '',
    used_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_verification_challenges_email_purpose_created_at
    ON email_verification_challenges(email, purpose, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_verification_challenges_status_expires_at
    ON email_verification_challenges(status, expires_at);

CREATE TABLE IF NOT EXISTS platform_sections (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '●',
    image_url TEXT NOT NULL DEFAULT '',
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
    order_channel TEXT NOT NULL DEFAULT 'web',
    external_order_id TEXT NOT NULL DEFAULT '',
    external_order_item_id TEXT NOT NULL DEFAULT '',
    dispatch_status TEXT NOT NULL DEFAULT 'unmapped',
    dispatch_attempts INTEGER NOT NULL DEFAULT 0,
    supplier_last_error TEXT NOT NULL DEFAULT '',
    external_payload_json TEXT NOT NULL DEFAULT '{}',
    notes_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL DEFAULT '',
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
    amount BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    kind TEXT NOT NULL,
    memo TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payment_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    reference TEXT NOT NULL DEFAULT '',
    failure_reason TEXT NOT NULL DEFAULT '',
    admin_adjustment_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    available_balance BIGINT NOT NULL DEFAULT 0,
    pending_balance BIGINT NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS charge_orders (
    id TEXT PRIMARY KEY,
    order_code TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    vat_amount BIGINT NOT NULL DEFAULT 0,
    total_amount BIGINT NOT NULL,
    payment_channel TEXT NOT NULL,
    payment_method_detail TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'created',
    depositor_name TEXT NOT NULL DEFAULT '',
    receipt_type TEXT NOT NULL DEFAULT 'none',
    receipt_payload_json TEXT NOT NULL DEFAULT '{}',
    reference TEXT NOT NULL DEFAULT '',
    pg_provider TEXT NOT NULL DEFAULT '',
    pg_order_id TEXT NOT NULL DEFAULT '',
    pg_payment_key TEXT NOT NULL DEFAULT '',
    failure_reason TEXT NOT NULL DEFAULT '',
    payment_payload_json TEXT NOT NULL DEFAULT '{}',
    bank_account_snapshot_json TEXT NOT NULL DEFAULT '{}',
    confirmed_at TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL DEFAULT '',
    paid_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_charge_orders_user_created_at
    ON charge_orders(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_charge_orders_status_created_at
    ON charge_orders(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_charge_orders_channel_status_created_at
    ON charge_orders(payment_channel, status, created_at DESC);

CREATE TABLE IF NOT EXISTS wallet_ledger (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL,
    amount BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    related_charge_order_id TEXT REFERENCES charge_orders(id) ON DELETE SET NULL,
    related_order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    memo TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_created_at
    ON wallet_ledger(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entry_type_created_at
    ON wallet_ledger(entry_type, created_at DESC);

CREATE TABLE IF NOT EXISTS payment_webhooks (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_key TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL DEFAULT '',
    charge_order_id TEXT REFERENCES charge_orders(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'received',
    payload_json TEXT NOT NULL DEFAULT '{}',
    processed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_webhooks_charge_order_created_at
    ON payment_webhooks(charge_order_id, created_at DESC);

CREATE TABLE IF NOT EXISTS cash_receipt_requests (
    id TEXT PRIMARY KEY,
    charge_order_id TEXT NOT NULL UNIQUE REFERENCES charge_orders(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL DEFAULT '',
    business_number TEXT NOT NULL DEFAULT '',
    purpose TEXT NOT NULL DEFAULT 'personal',
    status TEXT NOT NULL DEFAULT 'requested',
    requested_at TEXT NOT NULL,
    issued_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cash_receipt_requests_user_created_at
    ON cash_receipt_requests(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tax_invoice_requests (
    id TEXT PRIMARY KEY,
    charge_order_id TEXT NOT NULL UNIQUE REFERENCES charge_orders(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name TEXT NOT NULL DEFAULT '',
    business_number TEXT NOT NULL DEFAULT '',
    recipient_email TEXT NOT NULL DEFAULT '',
    contact_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'requested',
    requested_at TEXT NOT NULL,
    issued_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tax_invoice_requests_user_created_at
    ON tax_invoice_requests(user_id, created_at DESC);

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
    service_sync_status TEXT NOT NULL DEFAULT 'never',
    service_sync_message TEXT NOT NULL DEFAULT '',
    service_sync_started_at TEXT NOT NULL DEFAULT '',
    service_sync_completed_at TEXT NOT NULL DEFAULT '',
    service_sync_lock_until TEXT NOT NULL DEFAULT '',
    service_sync_error_count INTEGER NOT NULL DEFAULT 0,
    service_sync_interval_minutes INTEGER NOT NULL DEFAULT 30,
    health_status TEXT NOT NULL DEFAULT 'unknown',
    health_message TEXT NOT NULL DEFAULT '',
    health_checked_at TEXT NOT NULL DEFAULT '',
    balance_status TEXT NOT NULL DEFAULT 'unknown',
    balance_checked_at TEXT NOT NULL DEFAULT '',
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
    is_active INTEGER NOT NULL DEFAULT 1,
    raw_json TEXT NOT NULL DEFAULT '{}',
    synced_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL DEFAULT '',
    removed_at TEXT NOT NULL DEFAULT '',
    UNIQUE(supplier_id, external_service_id)
);

CREATE INDEX IF NOT EXISTS idx_supplier_services_supplier_active
    ON supplier_services(supplier_id, is_active, category, name);

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

CREATE TABLE IF NOT EXISTS mkt24_product_settings (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'mkt24',
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_service_id TEXT NOT NULL DEFAULT '',
    product_uuid TEXT NOT NULL,
    product_type_name TEXT NOT NULL DEFAULT '',
    full_name TEXT NOT NULL DEFAULT '',
    menu_name TEXT NOT NULL DEFAULT '',
    detail_snapshot_json TEXT NOT NULL DEFAULT '{}',
    field_config_json TEXT NOT NULL DEFAULT '{}',
    option_config_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_synced_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(supplier_id, product_uuid)
);

CREATE INDEX IF NOT EXISTS idx_mkt24_product_settings_supplier_service
    ON mkt24_product_settings(supplier_id, supplier_service_id, is_active);

CREATE TABLE IF NOT EXISTS supplier_orders (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_service_id TEXT NOT NULL DEFAULT '',
    supplier_external_order_id TEXT NOT NULL DEFAULT '',
    request_payload_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    last_status_checked_at TEXT NOT NULL DEFAULT '',
    next_status_check_at TEXT NOT NULL DEFAULT '',
    status_check_attempts INTEGER NOT NULL DEFAULT 0,
    status_check_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cafe24_oauth_states (
    state TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    redirect_uri TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_cafe24_oauth_states_expires_at
    ON cafe24_oauth_states(expires_at);

CREATE TABLE IF NOT EXISTS cafe24_integrations (
    id TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    access_token TEXT NOT NULL DEFAULT '',
    refresh_token TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL DEFAULT '',
    refresh_token_expires_at TEXT NOT NULL DEFAULT '',
    last_poll_at TEXT NOT NULL DEFAULT '',
    poll_cursor TEXT NOT NULL DEFAULT '',
    auto_submit INTEGER NOT NULL DEFAULT 0,
    completion_policy TEXT NOT NULL DEFAULT 'memo_only',
    token_status TEXT NOT NULL DEFAULT 'connected',
    token_last_checked_at TEXT NOT NULL DEFAULT '',
    token_last_refreshed_at TEXT NOT NULL DEFAULT '',
    token_refresh_lock_until TEXT NOT NULL DEFAULT '',
    token_refresh_lock_owner TEXT NOT NULL DEFAULT '',
    reconnect_required_at TEXT NOT NULL DEFAULT '',
    reconnect_reason TEXT NOT NULL DEFAULT '',
    cafe24_poll_lock_until TEXT NOT NULL DEFAULT '',
    cafe24_poll_lock_owner TEXT NOT NULL DEFAULT '',
    last_auto_poll_at TEXT NOT NULL DEFAULT '',
    last_auto_poll_status TEXT NOT NULL DEFAULT 'never',
    last_auto_poll_message TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_sync_status TEXT NOT NULL DEFAULT 'never',
    last_sync_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mall_id, shop_no)
);

CREATE INDEX IF NOT EXISTS idx_cafe24_integrations_active
    ON cafe24_integrations(is_active, updated_at DESC);

CREATE TABLE IF NOT EXISTS cafe24_product_mappings (
    id TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    cafe24_product_no TEXT NOT NULL DEFAULT '',
    cafe24_variant_code TEXT NOT NULL DEFAULT '',
    cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
    internal_product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id TEXT NOT NULL DEFAULT '',
    supplier_product_uuid TEXT NOT NULL DEFAULT '',
    supplier_product_code TEXT NOT NULL DEFAULT '',
    field_mapping_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mall_id, shop_no, cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code)
);

CREATE INDEX IF NOT EXISTS idx_cafe24_product_mappings_product
    ON cafe24_product_mappings(internal_product_id, enabled);

CREATE TABLE IF NOT EXISTS cafe24_supplier_mappings (
    id TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    cafe24_product_no TEXT NOT NULL DEFAULT '',
    cafe24_variant_code TEXT NOT NULL DEFAULT '',
    cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
    internal_product_id TEXT NOT NULL DEFAULT '',
    supplier_id TEXT NOT NULL DEFAULT '',
    supplier_service_id TEXT NOT NULL DEFAULT '',
    supplier_external_service_id TEXT NOT NULL DEFAULT '',
    supplier_product_uuid TEXT NOT NULL DEFAULT '',
    supplier_product_code TEXT NOT NULL DEFAULT '',
    field_mapping_json TEXT NOT NULL DEFAULT '{}',
    auto_dispatch_enabled INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mall_id, shop_no, cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code)
);

CREATE INDEX IF NOT EXISTS idx_cafe24_supplier_mappings_supplier
    ON cafe24_supplier_mappings(supplier_id, supplier_service_id, enabled);

CREATE TABLE IF NOT EXISTS cafe24_order_items (
    id TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    cafe24_order_id TEXT NOT NULL,
    cafe24_order_item_code TEXT NOT NULL DEFAULT '',
    cafe24_product_no TEXT NOT NULL DEFAULT '',
    cafe24_variant_code TEXT NOT NULL DEFAULT '',
    cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
    cafe24_order_date TEXT NOT NULL DEFAULT '',
    buyer_name TEXT NOT NULL DEFAULT '',
    buyer_email TEXT NOT NULL DEFAULT '',
    buyer_phone TEXT NOT NULL DEFAULT '',
    receiver_name TEXT NOT NULL DEFAULT '',
    order_status_code TEXT NOT NULL DEFAULT '',
    payment_status TEXT NOT NULL DEFAULT '',
    payment_status_source TEXT NOT NULL DEFAULT '',
    payment_gate_status TEXT NOT NULL DEFAULT 'unverified',
    payment_method TEXT NOT NULL DEFAULT '',
    payment_amount INTEGER NOT NULL DEFAULT 0,
    payment_paid_at TEXT NOT NULL DEFAULT '',
    payment_reference TEXT NOT NULL DEFAULT '',
    payment_snapshot_json TEXT NOT NULL DEFAULT '{}',
    source_status TEXT NOT NULL DEFAULT '',
    standard_status TEXT NOT NULL DEFAULT 'received',
    internal_order_id TEXT NOT NULL DEFAULT '',
    mapping_id TEXT NOT NULL DEFAULT '',
    product_id TEXT NOT NULL DEFAULT '',
    supplier_id TEXT NOT NULL DEFAULT '',
    supplier_service_id TEXT NOT NULL DEFAULT '',
    supplier_external_service_id TEXT NOT NULL DEFAULT '',
    normalized_fields_json TEXT NOT NULL DEFAULT '{}',
    supplier_payload_json TEXT NOT NULL DEFAULT '{}',
    raw_payload_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT NOT NULL DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT NOT NULL DEFAULT '',
    automation_last_checked_at TEXT NOT NULL DEFAULT '',
    automation_error_code TEXT NOT NULL DEFAULT '',
    auto_dispatch_approved INTEGER NOT NULL DEFAULT 0,
    auto_dispatch_source TEXT NOT NULL DEFAULT '',
    preflight_checked_at TEXT NOT NULL DEFAULT '',
    preflight_blockers_json TEXT NOT NULL DEFAULT '[]',
    supplier_order_id TEXT NOT NULL DEFAULT '',
    supplier_order_uuid TEXT NOT NULL DEFAULT '',
    supplier_response_json TEXT NOT NULL DEFAULT '{}',
    cafe24_completion_status TEXT NOT NULL DEFAULT 'pending',
    cafe24_completion_message TEXT NOT NULL DEFAULT '',
    cafe24_completed_at TEXT NOT NULL DEFAULT '',
    cafe24_completion_attempts INTEGER NOT NULL DEFAULT 0,
    cafe24_next_completion_retry_at TEXT NOT NULL DEFAULT '',
    last_submitted_at TEXT NOT NULL DEFAULT '',
    last_synced_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mall_id, shop_no, cafe24_order_id, cafe24_order_item_code)
);

CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_status_updated_at
    ON cafe24_order_items(standard_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_order_date
    ON cafe24_order_items(mall_id, shop_no, cafe24_order_date DESC);

CREATE INDEX IF NOT EXISTS idx_cafe24_order_items_internal_order
    ON cafe24_order_items(internal_order_id);

CREATE TABLE IF NOT EXISTS cafe24_api_events (
    id TEXT PRIMARY KEY,
    mall_id TEXT NOT NULL,
    shop_no INTEGER NOT NULL DEFAULT 1,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cafe24_api_events_created_at
    ON cafe24_api_events(created_at DESC);

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
    header_logo_url TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL DEFAULT 'admin',
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_created_at
    ON admin_audit_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_entity
    ON admin_audit_logs(entity_type, entity_id, created_at DESC);
"""

RUNTIME_SCHEMA_VERSION = "2026-05-19-01"


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
    return _money_label(value)


def payment_method_label(method: str) -> str:
    return _payment_method_label(method)


def payment_status_label(status: str) -> str:
    return _payment_status_label(status)


def receipt_type_label(receipt_type: str) -> str:
    return _receipt_type_label(receipt_type)


def default_home_popup_record() -> Dict[str, Any]:
    return {
        "id": "popup_home_service_notice",
        "name": "홈 서비스 안내 팝업",
        "badgeText": "신규 서비스 안내",
        "title": "서비스 안내를 확인해 주세요",
        "description": "상품별 제공 범위와 정책을 확인한 뒤 주문해 주세요.",
        "imageUrl": "",
        "route": "/help",
        "theme": "coral",
        "isActive": False,
    }


def default_site_settings_record() -> Dict[str, Any]:
    return {
        "siteName": DEFAULT_SITE_NAME,
        "siteDescription": DEFAULT_SITE_DESCRIPTION,
        "useMailSmsSiteName": False,
        "mailSmsSiteName": "",
        "headerLogoUrl": "",
        "faviconUrl": "",
        "shareImageUrl": "",
    }


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


def secret_encryption_material() -> bytes:
    raw = str(
        os.environ.get("SMM_PANEL_SECRET_ENCRYPTION_KEY")
        or os.environ.get("SMM_PANEL_SESSION_SECRET")
        or ""
    ).strip()
    if len(raw) < SECRET_ENCRYPTION_KEY_MIN_LENGTH:
        return b""
    return hashlib.sha256(raw.encode("utf-8")).digest()


def secret_encryption_available() -> bool:
    return bool(secret_encryption_material())


def secret_is_encrypted(value: Any) -> bool:
    return str(value or "").startswith(SECRET_ENVELOPE_PREFIX)


def _secret_encryption_required() -> bool:
    return is_production_runtime() or env_flag(os.environ.get("SMM_PANEL_REQUIRE_SECRET_ENCRYPTION"))


def _secret_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: List[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        counter += 1
        chunks.append(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
    return b"".join(chunks)[:length]


def encrypt_secret_value(value: Any, *, require_key: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw or secret_is_encrypted(raw):
        return raw
    key = secret_encryption_material()
    if not key:
        if require_key or _secret_encryption_required():
            raise PanelError("민감 키 암호화 키가 설정되지 않았습니다. SMM_PANEL_SECRET_ENCRYPTION_KEY를 설정해 주세요.")
        return raw
    nonce = secrets.token_bytes(16)
    plain = raw.encode("utf-8")
    stream = _secret_keystream(key, nonce, len(plain))
    cipher = bytes(left ^ right for left, right in zip(plain, stream))
    mac = hmac.new(key, b"enc:v1:" + nonce + cipher, hashlib.sha256).digest()
    envelope = base64.urlsafe_b64encode(nonce + mac + cipher).decode("ascii").rstrip("=")
    return f"{SECRET_ENVELOPE_PREFIX}{envelope}"


def decrypt_secret_value(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or not secret_is_encrypted(raw):
        return raw
    key = secret_encryption_material()
    if not key:
        raise PanelError("공급사 비밀키 복호화 키가 설정되지 않았습니다. SMM_PANEL_SECRET_ENCRYPTION_KEY를 확인해 주세요.")
    encoded = raw[len(SECRET_ENVELOPE_PREFIX) :]
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise PanelError("공급사 비밀키 형식이 올바르지 않습니다.") from exc
    if len(decoded) <= 48:
        raise PanelError("공급사 비밀키 형식이 올바르지 않습니다.")
    nonce = decoded[:16]
    mac = decoded[16:48]
    cipher = decoded[48:]
    expected_mac = hmac.new(key, b"enc:v1:" + nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise PanelError("공급사 비밀키 검증에 실패했습니다.")
    stream = _secret_keystream(key, nonce, len(cipher))
    plain = bytes(left ^ right for left, right in zip(cipher, stream))
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PanelError("공급사 비밀키 복호화에 실패했습니다.") from exc


def safe_mask_secret(value: Any, visible_suffix: int = 4) -> str:
    try:
        return mask_secret(decrypt_secret_value(value), visible_suffix)
    except PanelError:
        return "암호화 키 확인 필요"


class RichTextSanitizer(HTMLParser):
    ALLOWED_TAGS = {"p", "strong", "b", "em", "i", "u", "br", "ul", "ol", "li", "a"}
    VOID_TAGS = {"br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style"}:
            self.skip_depth += 1
            return
        if self.skip_depth or normalized not in self.ALLOWED_TAGS:
            return
        if normalized == "a":
            safe_attrs = []
            href = ""
            for name, value in attrs:
                if name.lower() == "href":
                    href = str(value or "").strip()
                    break
            parsed = urlparse(href)
            if href and parsed.scheme.lower() in {"http", "https", "mailto"}:
                safe_attrs.append(f'href="{html_escape(href, quote=True)}"')
                if parsed.scheme.lower() in {"http", "https"}:
                    safe_attrs.append('target="_blank"')
                    safe_attrs.append('rel="noopener noreferrer"')
            self.parts.append(f"<a{' ' + ' '.join(safe_attrs) if safe_attrs else ''}>")
            return
        self.parts.append(f"<{normalized}>")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth or normalized not in self.ALLOWED_TAGS or normalized in self.VOID_TAGS:
            return
        self.parts.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(html_escape(data))

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&{html_escape(name)};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&#{html_escape(name)};")

    def sanitized(self) -> str:
        return "".join(self.parts).strip()


def sanitize_rich_html(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    sanitizer = RichTextSanitizer()
    try:
        sanitizer.feed(raw)
        sanitizer.close()
    except Exception:
        return html_escape(raw)
    return sanitizer.sanitized()


def legal_document_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "key": "terms",
            "title": "이용약관",
            "version": LEGAL_DOCUMENT_VERSIONS["terms"],
            "required": True,
            "summary": "회원가입, 주문, 서비스 이용 조건에 대한 기본 약관입니다.",
            "body": [
                "회원은 정확한 계정·URL·수량 정보를 입력해야 하며, 잘못된 정보 입력으로 발생한 처리 지연은 회원 책임에 해당할 수 있습니다.",
                "서비스 특성상 주문 접수 또는 공급사 처리 단계 진입 이후에는 환불·취소 기준이 제한될 수 있습니다.",
                "허위 정보 입력, 타인 권리 침해, 정책 위반 주문은 제한될 수 있습니다.",
            ],
        },
        {
            "key": "privacy",
            "title": "개인정보처리방침",
            "version": LEGAL_DOCUMENT_VERSIONS["privacy"],
            "required": True,
            "summary": "회원 식별, 주문 처리, 고객 지원에 필요한 최소 정보 처리 방침입니다.",
            "body": [
                "이메일, 이름(또는 닉네임), 로그인 기록, 주문 이력, 잔액 내역 등을 처리할 수 있습니다.",
                "공급사 연동에 필요한 최소 주문 정보만 외부 공급사로 전달합니다.",
                "개인정보는 주문 처리, 고객 지원, 부정 이용 방지, 법령상 의무 이행 목적 범위에서 보관·이용합니다.",
            ],
        },
        {
            "key": "age",
            "title": "연령 확인",
            "version": LEGAL_DOCUMENT_VERSIONS["age"],
            "required": True,
            "summary": "만 14세 이상 또는 법정대리인 동의 필요 여부 확인 문구입니다.",
            "body": [
                "만 14세 미만 이용자는 회원가입 및 서비스 이용이 제한될 수 있습니다.",
                "연령 또는 법정대리인 동의 확인이 필요한 경우 추가 확인을 요청할 수 있습니다.",
            ],
        },
        {
            "key": "marketing",
            "title": "마케팅 정보 수신 동의",
            "version": LEGAL_DOCUMENT_VERSIONS["marketing"],
            "required": False,
            "summary": "이벤트, 상품 안내, 혜택 알림 수신 동의입니다.",
            "body": [
                "선택 동의이며, 동의하지 않아도 서비스 이용에 제한은 없습니다.",
                "회원은 언제든지 마케팅 수신 동의를 철회할 수 있습니다.",
            ],
        },
    ]


def oauth_provider_catalog() -> List[Dict[str, Any]]:
    providers = [
        ("google", "구글 로그인", "GOOGLE"),
        ("kakao", "카카오 로그인", "KAKAO"),
        ("naver", "네이버 로그인", "NAVER"),
    ]
    payload = []
    for provider, label, prefix in providers:
        enabled = all(
            str(os.environ.get(f"SMM_PANEL_{prefix}_{name}", "")).strip()
            for name in ("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")
        )
        payload.append(
            {
                "provider": provider,
                "label": label,
                "enabled": enabled,
                "status": "configured" if enabled else "pending_config",
                "startPath": f"/api/auth/oauth/{provider}/start",
                "requiredEnv": [
                    f"SMM_PANEL_{prefix}_CLIENT_ID",
                    f"SMM_PANEL_{prefix}_CLIENT_SECRET",
                    f"SMM_PANEL_{prefix}_REDIRECT_URI",
                ],
            }
        )
    return payload


def normalize_order_channel(raw: Any) -> str:
    try:
        return _normalize_order_channel(raw)
    except ValueError as exc:
        raise PanelError(str(exc)) from exc


def parse_iso_datetime(value: Any) -> Optional[dt.datetime]:
    return _parse_order_iso_datetime(value)


def automation_paused() -> bool:
    return _automation_paused()


def automation_retry_at(attempts: int) -> str:
    return _automation_retry_at(attempts)


def cafe24_poll_datetime_window(
    *,
    start_raw: str = "",
    end_raw: str = "",
    last_poll_at: str = "",
    use_cursor: bool = False,
    overlap_minutes: int = CAFE24_ORDER_OVERLAP_MINUTES,
) -> Dict[str, str]:
    try:
        return _cafe24_poll_datetime_window(
            start_raw=start_raw,
            end_raw=end_raw,
            last_poll_at=last_poll_at,
            use_cursor=use_cursor,
            overlap_minutes=overlap_minutes,
            default_lookback_days=CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS,
        )
    except Cafe24PollWindowError as exc:
        raise PanelError(str(exc), status=400) from exc


def cafe24_default_poll_window(last_poll_at: str = "", overlap_minutes: int = CAFE24_ORDER_OVERLAP_MINUTES) -> Dict[str, str]:
    try:
        return _cafe24_default_poll_window(last_poll_at=last_poll_at, overlap_minutes=overlap_minutes)
    except Cafe24PollWindowError as exc:
        raise PanelError(str(exc), status=400) from exc


def redact_external_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        sensitive_tokens = ("token", "secret", "password", "authorization", "access_token", "refresh_token")
        for key, item in value.items():
            lower = str(key).lower()
            if any(token in lower for token in sensitive_tokens):
                redacted[key] = mask_secret(str(item), 4)
            elif "email" in lower:
                redacted[key] = mask_email(str(item))
            elif "phone" in lower or "mobile" in lower or "tel" in lower:
                redacted[key] = mask_phone(str(item))
            else:
                redacted[key] = redact_external_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_external_payload(item) for item in value]
    return value


def is_unique_constraint_error(exc: BaseException) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    error_name = exc.__class__.__name__.lower()
    if "unique" in error_name or "integrity" in error_name:
        return True
    return "unique" in str(exc).lower()


def supplier_platform_label(platform_key: str) -> str:
    key = str(platform_key or "").strip().lower()
    if not key:
        return ""
    return SUPPLIER_PLATFORM_LABELS.get(key, key.replace("_", " ").title())


def avatar_label(name: str) -> str:
    cleaned = "".join(part for part in str(name or "").strip().split())
    if not cleaned:
        return "IM"
    return cleaned[:2].upper()


def resolved_avatar_label(stored_label: str, name: str) -> str:
    cleaned = str(stored_label or "").strip()
    if not cleaned or cleaned == "P24":
        return avatar_label(name)
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
        if urlparse(normalized).scheme.lower() != "https":
            raise PanelError(f"{label}는 https 주소만 사용할 수 있습니다.")
        return normalized
    raise PanelError(f"{label} 주소 형식이 올바르지 않습니다.")


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
      <text x="28" y="180" font-size="14" fill="rgba(255,255,255,0.72)">{html_escape(DEFAULT_SITE_NAME)} Link Preview</text>
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
    if urlparse(resolved).scheme.lower() != "https":
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


def validate_mkt24_option_config(option_config: Dict[str, Any], *, supports_order_options: bool) -> Dict[str, Any]:
    try:
        return _validate_mkt24_option_config(option_config, supports_order_options=supports_order_options)
    except Mkt24SettingsError as exc:
        raise PanelError(str(exc)) from exc


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
    panel_like_service = normalized_type == SUPPLIER_INTEGRATION_MKT24 and bool(raw_payload.get("service") or raw_payload.get("id"))
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
    if normalized_type == SUPPLIER_INTEGRATION_MKT24 and panel_like_service:
        notes.append("MKT24 대행사용 /v3/panel 표준 API 기준으로 key + action=add payload를 구성합니다.")
    elif normalized_type == SUPPLIER_INTEGRATION_MKT24:
        notes.append("이 추천은 MKT24 v3 상품 목록 메타데이터 기준 추정값입니다. 실제 발주 API 문서 확인 후 확정하는 것이 안전합니다.")
    elif normalized_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
        notes.append("FastTraffic은 X-Api-Key 헤더와 서비스별 action payload를 사용합니다. API Key는 요청 body에 포함하지 않습니다.")
        notes.append("등록 API는 분당 제한이 있으므로 자동 발주는 서버에서 throttle과 실패 제한 상태를 확인한 뒤 실행합니다.")

    example_payload: Dict[str, Any] = {}
    if normalized_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
        action = str(service.get("externalServiceId") or raw_payload.get("service") or "").strip()
        fasttraffic_meta = raw_payload.get("fasttraffic") if isinstance(raw_payload.get("fasttraffic"), dict) else {}
        example_payload["action"] = action
        example_payload["service"] = action
        target_param = str(fasttraffic_meta.get("targetParam") or "target").strip()
        quantity_param = str(fasttraffic_meta.get("quantityParam") or "count").strip()
        if "url" in target_param:
            example_payload[target_param] = supplier_target_placeholder(platform_key, "url").replace("예: ", "")
        else:
            example_payload[target_param] = "sample_account"
        if action in {"nblog_direct", "nclip_direct_c", "ncafe_auto", "ncafe_direct"}:
            example_payload["title"] = "주문 대상 제목"
        if action == "nblog_keyword":
            example_payload["keyword"] = supplier_example_value("googleKeyword")
        example_payload[quantity_param] = min_amount
        for key, value in (fasttraffic_meta.get("defaults") if isinstance(fasttraffic_meta.get("defaults"), dict) else {}).items():
            example_payload.setdefault(str(key), value)
    elif normalized_type == SUPPLIER_INTEGRATION_CLASSIC or panel_like_service:
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
        "confidence": "high" if normalized_type in {SUPPLIER_INTEGRATION_CLASSIC, SUPPLIER_INTEGRATION_FASTTRAFFIC} or panel_like_service else "medium",
        "notes": notes,
        "formRecommendation": recommendation,
        "callExampleTitle": "공급사 호출 예시" if normalized_type in {SUPPLIER_INTEGRATION_CLASSIC, SUPPLIER_INTEGRATION_FASTTRAFFIC} or panel_like_service else "추천 입력 예시",
        "callExamplePayload": example_payload,
        "callExampleIsEstimated": not (normalized_type in {SUPPLIER_INTEGRATION_CLASSIC, SUPPLIER_INTEGRATION_FASTTRAFFIC} or panel_like_service),
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

    keys = [key for key in template.keys() if key != "requestMemo"]
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


def ensure_request_memo_form_structure(
    form_structure: Dict[str, Any],
    memo_label: str = "요청 메모",
) -> Dict[str, Any]:
    if not isinstance(form_structure, dict):
        return {}
    schema = form_structure.get("schema")
    template = form_structure.get("template")
    if not isinstance(schema, dict) or not isinstance(template, dict):
        return form_structure
    if "requestMemo" in template:
        return form_structure
    _append_form_field(
        schema,
        template,
        {
            "name": "requestMemo",
            "kind": "textarea",
            "label": memo_label,
            "placeholder": "추가 요청사항이 있으면 남겨 주세요.",
            "rows": 4,
            "required": False,
        },
    )
    return form_structure


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

    form_structure = parse_json(form_structure_json, {})
    if not isinstance(form_structure, dict):
        return form_structure_json
    form_structure = ensure_request_memo_form_structure(form_structure, memo_label)
    schema = form_structure.get("schema")
    template = form_structure.get("template")
    if not isinstance(schema, dict) or not isinstance(template, dict):
        return form_structure_json

    if not advanced_field_keys:
        return as_json(form_structure)

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
                                    "숏폼 초기 반응 확인용으로도 적합합니다.",
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
                                    "광고 소재의 초기 반응 확인용으로 활용할 수 있습니다.",
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
                                    "브랜드 키워드 검증이나 블로그 체류 개선에도 활용할 수 있습니다.",
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
            ("cat_press_release", "기사형 보도자료 송출", "브랜드 신뢰도 확보용 기사형 송출 상품", "브랜드명", f"예: {DEFAULT_SITE_NAME}", "송출 수량", 1, 30, 1, "건"),
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
                        "필요 시 추가 요청사항을 함께 남기면 담당자가 참고합니다.",
                    ],
                    [
                        "대상 채널 또는 URL을 입력해 주세요.",
                        "원하는 수량을 설정해 주세요.",
                        "주문 후 진행 상태는 내역 화면에서 확인할 수 있어요.",
                    ],
                    "주문 전 필요한 정보를 한 화면에서 확인할 수 있도록 구성했습니다.",
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


class PanelStore(PanelStoreDatabaseMixin):
    default_db_path = DB_PATH
    demo_user_id = DEMO_USER_ID
    schema_sql = SCHEMA_SQL
    runtime_schema_version = RUNTIME_SCHEMA_VERSION

    def _wallet_runtime_repair_needed(self, conn: DatabaseConnection) -> bool:
        missing_wallet = conn.execute(
            """
            SELECT 1
            FROM users u
            LEFT JOIN wallets w ON w.user_id = u.id
            WHERE w.user_id IS NULL
            LIMIT 1
            """
        ).fetchone()
        if missing_wallet is not None:
            return True
        balance_drift = conn.execute(
            """
            SELECT 1
            FROM users u
            JOIN wallets w ON w.user_id = u.id
            WHERE COALESCE(u.balance, 0) <> COALESCE(w.available_balance, 0)
            LIMIT 1
            """
        ).fetchone()
        if balance_drift is not None:
            return True
        unmigrated_legacy = conn.execute(
            """
            SELECT 1
            FROM balance_transactions bt
            LEFT JOIN wallet_ledger wl ON wl.id = ('legacy_' || bt.id)
            WHERE wl.id IS NULL
            LIMIT 1
            """
        ).fetchone()
        return unmigrated_legacy is not None

    def _ensure_mkt24_product_settings_table(self, conn: DatabaseConnection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS mkt24_product_settings (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL DEFAULT 'mkt24',
                supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
                supplier_service_id TEXT NOT NULL DEFAULT '',
                product_uuid TEXT NOT NULL,
                product_type_name TEXT NOT NULL DEFAULT '',
                full_name TEXT NOT NULL DEFAULT '',
                menu_name TEXT NOT NULL DEFAULT '',
                detail_snapshot_json TEXT NOT NULL DEFAULT '{}',
                field_config_json TEXT NOT NULL DEFAULT '{}',
                option_config_json TEXT NOT NULL DEFAULT '{}',
                is_active INTEGER NOT NULL DEFAULT 1,
                last_synced_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(supplier_id, product_uuid)
            );
            """
        )
        self._ensure_column(conn, "mkt24_product_settings", "supplier_service_id", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mkt24_product_settings_supplier_service
                ON mkt24_product_settings(supplier_id, supplier_service_id, is_active)
            """
        )

    def _migrate_cafe24_supplier_mappings(self, conn: DatabaseConnection) -> None:
        legacy_rows = conn.execute(
            """
            SELECT
                cm.*,
                psm.supplier_id AS fallback_supplier_id,
                psm.supplier_service_id AS fallback_supplier_service_id,
                psm.supplier_external_service_id AS fallback_supplier_external_service_id
            FROM cafe24_product_mappings cm
            LEFT JOIN product_supplier_mappings psm
                ON psm.product_id = cm.internal_product_id
               AND psm.is_active = 1
               AND (
                    cm.supplier_id = ''
                    OR cm.supplier_id = psm.supplier_id
               )
            """
        ).fetchall()
        timestamp = now_iso()
        for row in legacy_rows:
            product_no = str(row["cafe24_product_no"] or "")
            variant_code = str(row["cafe24_variant_code"] or "")
            custom_code = str(row["cafe24_custom_product_code"] or "")
            if not any([product_no, variant_code, custom_code]):
                continue
            supplier_id = str(row["supplier_id"] or row["fallback_supplier_id"] or "").strip()
            supplier_service_id = str(row["fallback_supplier_service_id"] or "").strip()
            supplier_external_service_id = str(
                row["supplier_product_uuid"]
                or row["supplier_product_code"]
                or row["fallback_supplier_external_service_id"]
                or ""
            ).strip()
            if not supplier_id and not supplier_external_service_id:
                continue
            existing = conn.execute(
                """
                SELECT id
                FROM cafe24_supplier_mappings
                WHERE mall_id = ? AND shop_no = ? AND cafe24_product_no = ?
                  AND cafe24_variant_code = ? AND cafe24_custom_product_code = ?
                """,
                (row["mall_id"], row["shop_no"], product_no, variant_code, custom_code),
            ).fetchone()
            if existing is not None:
                continue
            conn.execute(
                """
                INSERT INTO cafe24_supplier_mappings (
                    id, mall_id, shop_no, cafe24_product_no, cafe24_variant_code,
                    cafe24_custom_product_code, internal_product_id, supplier_id,
                    supplier_service_id, supplier_external_service_id,
                    supplier_product_uuid, supplier_product_code, field_mapping_json,
                    auto_dispatch_enabled, enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cafe24_smap_{uuid4().hex[:14]}",
                    row["mall_id"],
                    row["shop_no"],
                    product_no,
                    variant_code,
                    custom_code,
                    row["internal_product_id"] or "",
                    supplier_id,
                    supplier_service_id,
                    supplier_external_service_id,
                    row["supplier_product_uuid"] or "",
                    row["supplier_product_code"] or "",
                    row["field_mapping_json"] or "{}",
                    0,
                    row["enabled"],
                    timestamp,
                    timestamp,
                ),
            )

    def _migrate_supplier_secrets(self, conn: DatabaseConnection) -> None:
        if not secret_encryption_available():
            return
        rows = conn.execute("SELECT id, api_key, bearer_token FROM suppliers").fetchall()
        for row in rows:
            api_key = str(row["api_key"] or "")
            bearer_token = str(row["bearer_token"] or "")
            encrypted_api_key = encrypt_secret_value(api_key)
            encrypted_bearer_token = encrypt_secret_value(bearer_token)
            if encrypted_api_key != api_key or encrypted_bearer_token != bearer_token:
                conn.execute(
                    "UPDATE suppliers SET api_key = ?, bearer_token = ?, updated_at = ? WHERE id = ?",
                    (encrypted_api_key, encrypted_bearer_token, now_iso(), row["id"]),
                )

    def _ensure_charge_support_tables(self, conn: DatabaseConnection) -> None:
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_charge_orders_status_created_at
                ON charge_orders(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_charge_orders_channel_status_created_at
                ON charge_orders(payment_channel, status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_wallet_ledger_entry_type_created_at
                ON wallet_ledger(entry_type, created_at DESC);

            CREATE TABLE IF NOT EXISTS payment_webhooks (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                event_key TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL DEFAULT '',
                charge_order_id TEXT REFERENCES charge_orders(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'received',
                payload_json TEXT NOT NULL DEFAULT '{}',
                processed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_payment_webhooks_charge_order_created_at
                ON payment_webhooks(charge_order_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS cash_receipt_requests (
                id TEXT PRIMARY KEY,
                charge_order_id TEXT NOT NULL UNIQUE REFERENCES charge_orders(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                phone_number TEXT NOT NULL DEFAULT '',
                business_number TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT 'personal',
                status TEXT NOT NULL DEFAULT 'requested',
                requested_at TEXT NOT NULL,
                issued_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cash_receipt_requests_user_created_at
                ON cash_receipt_requests(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS tax_invoice_requests (
                id TEXT PRIMARY KEY,
                charge_order_id TEXT NOT NULL UNIQUE REFERENCES charge_orders(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                business_name TEXT NOT NULL DEFAULT '',
                business_number TEXT NOT NULL DEFAULT '',
                recipient_email TEXT NOT NULL DEFAULT '',
                contact_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'requested',
                requested_at TEXT NOT NULL,
                issued_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tax_invoice_requests_user_created_at
                ON tax_invoice_requests(user_id, created_at DESC);
            """
        )

    def _ensure_cafe24_support_tables(self, conn: DatabaseConnection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cafe24_oauth_states (
                state TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                scopes_json TEXT NOT NULL DEFAULT '[]',
                redirect_uri TEXT NOT NULL DEFAULT '',
                actor TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS cafe24_integrations (
                id TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                scopes_json TEXT NOT NULL DEFAULT '[]',
                access_token TEXT NOT NULL DEFAULT '',
                refresh_token TEXT NOT NULL DEFAULT '',
                expires_at TEXT NOT NULL DEFAULT '',
                refresh_token_expires_at TEXT NOT NULL DEFAULT '',
                last_poll_at TEXT NOT NULL DEFAULT '',
                poll_cursor TEXT NOT NULL DEFAULT '',
                auto_submit INTEGER NOT NULL DEFAULT 0,
                completion_policy TEXT NOT NULL DEFAULT 'memo_only',
                token_status TEXT NOT NULL DEFAULT 'connected',
                token_last_checked_at TEXT NOT NULL DEFAULT '',
                token_last_refreshed_at TEXT NOT NULL DEFAULT '',
                token_refresh_lock_until TEXT NOT NULL DEFAULT '',
                token_refresh_lock_owner TEXT NOT NULL DEFAULT '',
                reconnect_required_at TEXT NOT NULL DEFAULT '',
                reconnect_reason TEXT NOT NULL DEFAULT '',
                cafe24_poll_lock_until TEXT NOT NULL DEFAULT '',
                cafe24_poll_lock_owner TEXT NOT NULL DEFAULT '',
                last_auto_poll_at TEXT NOT NULL DEFAULT '',
                last_auto_poll_status TEXT NOT NULL DEFAULT 'never',
                last_auto_poll_message TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                last_sync_status TEXT NOT NULL DEFAULT 'never',
                last_sync_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(mall_id, shop_no)
            );
            CREATE TABLE IF NOT EXISTS cafe24_product_mappings (
                id TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                cafe24_product_no TEXT NOT NULL DEFAULT '',
                cafe24_variant_code TEXT NOT NULL DEFAULT '',
                cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
                internal_product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                supplier_id TEXT NOT NULL DEFAULT '',
                supplier_product_uuid TEXT NOT NULL DEFAULT '',
                supplier_product_code TEXT NOT NULL DEFAULT '',
                field_mapping_json TEXT NOT NULL DEFAULT '{}',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(mall_id, shop_no, cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code)
            );
            CREATE TABLE IF NOT EXISTS cafe24_supplier_mappings (
                id TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                cafe24_product_no TEXT NOT NULL DEFAULT '',
                cafe24_variant_code TEXT NOT NULL DEFAULT '',
                cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
                internal_product_id TEXT NOT NULL DEFAULT '',
                supplier_id TEXT NOT NULL DEFAULT '',
                supplier_service_id TEXT NOT NULL DEFAULT '',
                supplier_external_service_id TEXT NOT NULL DEFAULT '',
                supplier_product_uuid TEXT NOT NULL DEFAULT '',
                supplier_product_code TEXT NOT NULL DEFAULT '',
                field_mapping_json TEXT NOT NULL DEFAULT '{}',
                auto_dispatch_enabled INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(mall_id, shop_no, cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code)
            );
            CREATE TABLE IF NOT EXISTS cafe24_order_items (
                id TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                cafe24_order_id TEXT NOT NULL,
                cafe24_order_item_code TEXT NOT NULL DEFAULT '',
                cafe24_product_no TEXT NOT NULL DEFAULT '',
                cafe24_variant_code TEXT NOT NULL DEFAULT '',
                cafe24_custom_product_code TEXT NOT NULL DEFAULT '',
                cafe24_order_date TEXT NOT NULL DEFAULT '',
                buyer_name TEXT NOT NULL DEFAULT '',
                buyer_email TEXT NOT NULL DEFAULT '',
                buyer_phone TEXT NOT NULL DEFAULT '',
                receiver_name TEXT NOT NULL DEFAULT '',
                order_status_code TEXT NOT NULL DEFAULT '',
                payment_status TEXT NOT NULL DEFAULT '',
                payment_status_source TEXT NOT NULL DEFAULT '',
                payment_gate_status TEXT NOT NULL DEFAULT 'unverified',
                payment_method TEXT NOT NULL DEFAULT '',
                payment_amount INTEGER NOT NULL DEFAULT 0,
                payment_paid_at TEXT NOT NULL DEFAULT '',
                payment_reference TEXT NOT NULL DEFAULT '',
                payment_snapshot_json TEXT NOT NULL DEFAULT '{}',
                source_status TEXT NOT NULL DEFAULT '',
                standard_status TEXT NOT NULL DEFAULT 'received',
                internal_order_id TEXT NOT NULL DEFAULT '',
                mapping_id TEXT NOT NULL DEFAULT '',
                product_id TEXT NOT NULL DEFAULT '',
                supplier_id TEXT NOT NULL DEFAULT '',
                supplier_service_id TEXT NOT NULL DEFAULT '',
                supplier_external_service_id TEXT NOT NULL DEFAULT '',
                normalized_fields_json TEXT NOT NULL DEFAULT '{}',
                supplier_payload_json TEXT NOT NULL DEFAULT '{}',
                raw_payload_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT '',
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT NOT NULL DEFAULT '',
                automation_last_checked_at TEXT NOT NULL DEFAULT '',
                automation_error_code TEXT NOT NULL DEFAULT '',
                auto_dispatch_approved INTEGER NOT NULL DEFAULT 0,
                auto_dispatch_source TEXT NOT NULL DEFAULT '',
                preflight_checked_at TEXT NOT NULL DEFAULT '',
                preflight_blockers_json TEXT NOT NULL DEFAULT '[]',
                supplier_order_id TEXT NOT NULL DEFAULT '',
                supplier_order_uuid TEXT NOT NULL DEFAULT '',
                supplier_response_json TEXT NOT NULL DEFAULT '{}',
                cafe24_completion_status TEXT NOT NULL DEFAULT 'pending',
                cafe24_completion_message TEXT NOT NULL DEFAULT '',
                cafe24_completed_at TEXT NOT NULL DEFAULT '',
                cafe24_completion_attempts INTEGER NOT NULL DEFAULT 0,
                cafe24_next_completion_retry_at TEXT NOT NULL DEFAULT '',
                last_submitted_at TEXT NOT NULL DEFAULT '',
                last_synced_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(mall_id, shop_no, cafe24_order_id, cafe24_order_item_code)
            );
            CREATE TABLE IF NOT EXISTS cafe24_api_events (
                id TEXT PRIMARY KEY,
                mall_id TEXT NOT NULL,
                shop_no INTEGER NOT NULL DEFAULT 1,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                request_json TEXT NOT NULL DEFAULT '{}',
                response_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )

    def _sync_wallet_state(self, conn: DatabaseConnection) -> None:
        timestamp = now_iso()
        user_rows = conn.execute("SELECT id, balance FROM users").fetchall()
        for user in user_rows:
            wallet = conn.execute(
                "SELECT available_balance, pending_balance FROM wallets WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            if wallet is None:
                conn.execute(
                    """
                    INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
                    VALUES (?, ?, 0, ?, ?)
                    """,
                    (user["id"], int(user["balance"]), timestamp, timestamp),
                )
                continue
            if int(wallet["available_balance"]) != int(user["balance"]):
                conn.execute(
                    "UPDATE users SET balance = ?, updated_at = ? WHERE id = ?",
                    (int(wallet["available_balance"]), timestamp, user["id"]),
                )

        legacy_rows = conn.execute(
            """
            SELECT id, user_id, amount, balance_after, kind, memo, created_at
            FROM balance_transactions
            ORDER BY created_at ASC
            """
        ).fetchall()
        for row in legacy_rows:
            ledger_id = f"legacy_{row['id']}"
            exists = conn.execute("SELECT 1 FROM wallet_ledger WHERE id = ?", (ledger_id,)).fetchone()
            if exists is not None:
                continue
            conn.execute(
                """
                INSERT INTO wallet_ledger (
                    id, user_id, entry_type, amount, balance_after, related_charge_order_id, related_order_id, memo, created_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    ledger_id,
                    row["user_id"],
                    balance_transaction_kind_to_ledger_entry_type(row["kind"]),
                    int(row["amount"]),
                    int(row["balance_after"]),
                    row["memo"],
                    row["created_at"],
                ),
            )

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
                "notes": {"memo": "키워드 유입 확인"},
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

    def _ensure_home_popup(self, conn: DatabaseConnection) -> None:
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

    def _ensure_site_settings(self, conn: DatabaseConnection) -> None:
        exists = conn.execute("SELECT id FROM site_settings LIMIT 1").fetchone()
        if exists is not None:
            return
        settings = default_site_settings_record()
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO site_settings (
                id, site_name, site_description, use_mail_sms_site_name, mail_sms_site_name, header_logo_url,
                favicon_url, share_image_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                settings["siteName"],
                settings["siteDescription"],
                bool_to_int(settings["useMailSmsSiteName"]),
                settings["mailSmsSiteName"],
                settings["headerLogoUrl"],
                settings["faviconUrl"],
                settings["shareImageUrl"],
                timestamp,
                timestamp,
            ),
        )

    def _ensure_analytics_samples(self, conn: DatabaseConnection) -> None:
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

    def _seed(self, conn: DatabaseConnection) -> None:
        created_at = now_iso()
        if demo_seed_enabled():
            conn.execute(
                """
                INSERT INTO users (
                    id, name, email, password_hash, phone, tier, role, avatar_label, balance,
                    is_active, account_status, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEMO_USER_ID,
                    "기본 관리자",
                    "demo@pulse24.local",
                    "",
                    "01024512400",
                    "PRO",
                    "admin",
                    "P24",
                    185000,
                    1,
                    "active",
                    "기본 패널 운영 계정",
                    created_at,
                    created_at,
                ),
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
            ("support_faq", "FAQ", "주문 전 자주 묻는 질문을 빠르게 확인하세요.", "/help#faq", "?", "", 0),
            ("support_notice", "공지사항", "운영 공지와 정책 업데이트를 바로 확인하세요.", "/help#notice", "!", "", 1),
            ("support_consult", "1:1 상담", "맞춤형 상품이 필요하면 상담 흐름으로 연결합니다.", "/products/cat_custom_request", "☏", "", 2),
            ("support_guide", "이용가이드", "처음 쓰는 분도 쉽게 이해할 수 있도록 흐름을 정리했습니다.", "/help#guide", "→", "", 3),
        ]
        conn.executemany(
            "INSERT INTO support_links (id, title, subtitle, route, icon, external_url, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            supports,
        )

        benefits = [
            ("benefit_safe", "안정적인 처리 우선", "급격한 수치 상승보다 안정적인 속도와 채널 안전을 우선합니다.", "🛡", 0),
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
                INSERT INTO platform_sections (id, slug, display_name, description, icon, image_url, accent_color, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    platform["id"],
                    platform["slug"],
                    platform["display_name"],
                    platform["description"],
                    platform["icon"],
                    str(platform.get("image_url") or ""),
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

        if demo_seed_enabled():
            transactions = [
                ("tx_initial", DEMO_USER_ID, 350000, 350000, "charge", "초기 운영 확인 캐시 충전", (now - dt.timedelta(days=10)).isoformat(timespec="seconds")),
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

    def _fetchall(self, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute(query, tuple(params)).fetchall()

    def _fetchone(self, query: str, params: Iterable[Any] = ()) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        if row is None:
            raise PanelError("요청한 데이터를 찾을 수 없습니다.", status=404)
        return row

    def _public_user_row(self, conn: DatabaseConnection, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ? AND is_active = 1 AND account_status = 'active' AND role != 'admin'
            """,
            (user_id,),
        ).fetchone()
        return row

    def _user_summary(self, conn: DatabaseConnection, user_id: str) -> Dict[str, Any]:
        user = self._public_user_row(conn, user_id)
        if user is None:
            raise PanelError("로그인한 사용자를 찾을 수 없습니다.", status=401)
        wallet = self._wallet_balances(conn, user_id)
        return {
            "id": user["id"],
            "name": user["name"],
            "emailMasked": mask_email(user["email"]),
            "phoneMasked": mask_phone(user["phone"]),
            "tier": user["tier"],
            "avatarLabel": resolved_avatar_label(user["avatar_label"], user["name"]),
            "balance": wallet["available"],
            "balanceLabel": money(wallet["available"]),
            "hasPassword": bool(user["password_hash"]),
            "accountStatus": user["account_status"],
            "marketingOptIn": bool(user["marketing_opt_in"]),
        }

    def _wallet_balances(self, conn: DatabaseConnection, user_id: str) -> Dict[str, int]:
        user = self._public_user_row(conn, user_id)
        if user is None:
            raise PanelError("로그인한 사용자를 찾을 수 없습니다.", status=401)
        wallet = conn.execute(
            "SELECT available_balance, pending_balance FROM wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        available_balance = int(wallet["available_balance"]) if wallet is not None else int(user["balance"])
        pending_balance = int(wallet["pending_balance"]) if wallet is not None else 0
        if wallet is None:
            timestamp = now_iso()
            conn.execute(
                """
                INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, available_balance, pending_balance, timestamp, timestamp),
            )
        elif int(user["balance"]) != available_balance:
            conn.execute("UPDATE users SET balance = ?, updated_at = ? WHERE id = ?", (available_balance, now_iso(), user_id))
        return {"available": available_balance, "pending": pending_balance}

    def _set_wallet_balances(
        self,
        conn: DatabaseConnection,
        user_id: str,
        *,
        available_balance: int,
        pending_balance: Optional[int] = None,
    ) -> None:
        wallet = conn.execute(
            "SELECT pending_balance FROM wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        current_pending = int(wallet["pending_balance"]) if wallet is not None else 0
        next_pending = current_pending if pending_balance is None else int(pending_balance)
        timestamp = now_iso()
        if wallet is None:
            conn.execute(
                """
                INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, int(available_balance), next_pending, timestamp, timestamp),
            )
            return
        conn.execute(
            "UPDATE wallets SET available_balance = ?, pending_balance = ?, updated_at = ? WHERE user_id = ?",
            (int(available_balance), next_pending, timestamp, user_id),
        )
        conn.execute("UPDATE users SET balance = ?, updated_at = ? WHERE id = ?", (int(available_balance), timestamp, user_id))

    def _change_wallet_available_balance(
        self,
        conn: DatabaseConnection,
        user_id: str,
        delta: int,
        *,
        require_sufficient: bool = False,
        timestamp: Optional[str] = None,
    ) -> int:
        self._wallet_balances(conn, user_id)
        timestamp = timestamp or now_iso()
        if require_sufficient and int(delta) < 0:
            debit_amount = abs(int(delta))
            cursor = conn.execute(
                """
                UPDATE wallets
                SET available_balance = available_balance - ?, updated_at = ?
                WHERE user_id = ? AND available_balance >= ?
                """,
                (debit_amount, timestamp, user_id, debit_amount),
            )
        else:
            cursor = conn.execute(
                """
                UPDATE wallets
                SET available_balance = available_balance + ?, updated_at = ?
                WHERE user_id = ?
                """,
                (int(delta), timestamp, user_id),
            )
        if cursor.rowcount != 1:
            if require_sufficient and int(delta) < 0:
                raise PanelError("보유 캐시가 부족합니다. 충전 후 다시 시도해 주세요.")
            raise PanelError("지갑 잔액을 갱신할 수 없습니다.", status=409)
        wallet = conn.execute(
            "SELECT available_balance FROM wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if wallet is None:
            raise PanelError("지갑 정보를 찾을 수 없습니다.", status=404)
        balance_after = int(wallet["available_balance"])
        conn.execute("UPDATE users SET balance = ?, updated_at = ? WHERE id = ?", (balance_after, timestamp, user_id))
        return balance_after

    def _refresh_wallet_pending_balance(self, conn: DatabaseConnection, user_id: str) -> int:
        pending_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS pending_amount
            FROM charge_orders
            WHERE user_id = ?
              AND status IN ('created', 'awaiting_payment', 'awaiting_deposit', 'processing')
            """,
            (user_id,),
        ).fetchone()
        pending_balance = int(pending_row["pending_amount"]) if pending_row is not None else 0
        available_balance = self._wallet_balances(conn, user_id)["available"]
        self._set_wallet_balances(
            conn,
            user_id,
            available_balance=available_balance,
            pending_balance=pending_balance,
        )
        return pending_balance

    def _append_wallet_ledger_entry(
        self,
        conn: DatabaseConnection,
        *,
        ledger_id: str,
        user_id: str,
        entry_type: str,
        amount: int,
        balance_after: int,
        memo: str,
        related_charge_order_id: Optional[str] = None,
        related_order_id: Optional[str] = None,
        created_at: str,
    ) -> None:
        exists = conn.execute("SELECT 1 FROM wallet_ledger WHERE id = ?", (ledger_id,)).fetchone()
        if exists is not None:
            return
        conn.execute(
            """
            INSERT INTO wallet_ledger (
                id, user_id, entry_type, amount, balance_after, related_charge_order_id, related_order_id, memo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ledger_id,
                user_id,
                entry_type,
                int(amount),
                int(balance_after),
                related_charge_order_id,
                related_order_id,
                memo,
                created_at,
            ),
        )

    def _charge_order_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return _charge_order_payload(row, created_label=self._relative_date_label(dict(row).get("created_at", "")))

    def _admin_charge_order_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        row_map = dict(row)
        customer_email = str(row_map.get("customer_email") or "")
        return _admin_charge_order_payload(
            row_map,
            created_label=self._relative_date_label(row_map.get("created_at", "")),
            customer_email_masked=mask_email(customer_email),
        )

    def _admin_charge_order_by_id(self, conn: DatabaseConnection, charge_order_id: str) -> Dict[str, Any]:
        row = conn.execute(
            """
            SELECT
                co.*,
                u.name AS customer_name,
                u.email AS customer_email
            FROM charge_orders co
            JOIN users u ON u.id = co.user_id
            WHERE co.id = ?
            """,
            (charge_order_id,),
        ).fetchone()
        if row is None:
            raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)
        return self._admin_charge_order_payload(row)

    def _wallet_payload(self, conn: DatabaseConnection, user_id: str) -> Dict[str, Any]:
        balances = self._wallet_balances(conn, user_id)
        pending_balance = self._refresh_wallet_pending_balance(conn, user_id)
        return wallet_balances_payload(balances["available"], pending_balance)

    def _charge_amount_breakdown(self, amount: int) -> Dict[str, int]:
        return _charge_amount_breakdown(amount)

    def _normalized_charge_payment_channel(self, raw_value: Any) -> str:
        try:
            return _normalize_charge_payment_channel(raw_value)
        except ValueError as exc:
            raise PanelError(str(exc)) from exc

    def _resolve_charge_expiry(self, payment_channel: str) -> str:
        return _resolve_charge_expiry(payment_channel)

    def _payment_method_detail_label(self, payment_channel: str, method_detail: str) -> str:
        return _payment_method_detail_label(payment_channel, method_detail)

    def _bank_transfer_public_payload(self) -> Dict[str, Any]:
        config = bank_transfer_config()
        return {
            "enabled": bank_transfer_configured(),
            "bankName": config["bankName"],
            "accountNumber": config["accountNumber"],
            "accountHolder": config["accountHolder"],
            "depositGuide": config["depositGuide"] or "입금자명을 동일하게 입력하면 확인이 빨라집니다.",
        }

    def _payment_methods_public_payload(self) -> List[Dict[str, Any]]:
        bank_transfer = self._bank_transfer_public_payload()
        return [
            {
                "id": "card",
                "label": "카드/간편결제",
                "description": "결제 승인 후 보유금액으로 즉시 반영됩니다.",
                "enabled": card_payment_configured(),
                "requiresProvider": True,
            },
            {
                "id": "bank_transfer",
                "label": "계좌입금",
                "description": "입금 확인 후 보유금액으로 반영됩니다.",
                "enabled": bank_transfer["enabled"],
                "requiresProvider": False,
            },
        ]

    def charge_config_public_payload(self) -> Dict[str, Any]:
        return {
            "methods": self._payment_methods_public_payload(),
            "bankTransfer": self._bank_transfer_public_payload(),
            "minimumAmount": 5_000,
            "maximumAmount": 5_000_000,
            "vatIncluded": False,
            "policyHighlights": [
                "결제 완료 또는 입금 확인 후에만 보유금액이 적립됩니다.",
                "카드/간편결제는 결제 승인 확인 후에만 보유금액으로 반영됩니다.",
                "환불, 증빙, 취소 기준은 이용약관과 결제 안내를 따릅니다.",
            ],
        }

    def _record_receipt_request(
        self,
        conn: DatabaseConnection,
        *,
        charge_order_id: str,
        user_id: str,
        receipt_type: str,
        receipt_payload: Dict[str, Any],
        timestamp: str,
    ) -> None:
        if receipt_type == "cash_receipt":
            row = conn.execute("SELECT id FROM cash_receipt_requests WHERE charge_order_id = ?", (charge_order_id,)).fetchone()
            values = (
                str(receipt_payload.get("phoneNumber") or "").strip(),
                str(receipt_payload.get("businessNumber") or "").strip(),
                str(receipt_payload.get("purpose") or "personal").strip() or "personal",
            )
            if row is None:
                conn.execute(
                    """
                    INSERT INTO cash_receipt_requests (
                        id, charge_order_id, user_id, phone_number, business_number, purpose,
                        status, requested_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'requested', ?, ?, ?)
                    """,
                    (f"cr_{uuid4().hex[:12]}", charge_order_id, user_id, *values, timestamp, timestamp, timestamp),
                )
            else:
                conn.execute(
                    """
                    UPDATE cash_receipt_requests
                    SET phone_number = ?, business_number = ?, purpose = ?, status = 'requested', updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, timestamp, row["id"]),
                )
            return

        if receipt_type == "tax_invoice":
            row = conn.execute("SELECT id FROM tax_invoice_requests WHERE charge_order_id = ?", (charge_order_id,)).fetchone()
            values = (
                str(receipt_payload.get("businessName") or "").strip(),
                str(receipt_payload.get("businessNumber") or "").strip(),
                str(receipt_payload.get("recipientEmail") or "").strip(),
                str(receipt_payload.get("contactName") or "").strip(),
            )
            if row is None:
                conn.execute(
                    """
                    INSERT INTO tax_invoice_requests (
                        id, charge_order_id, user_id, business_name, business_number, recipient_email,
                        contact_name, status, requested_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'requested', ?, ?, ?)
                    """,
                    (f"ti_{uuid4().hex[:12]}", charge_order_id, user_id, *values, timestamp, timestamp, timestamp),
                )
            else:
                conn.execute(
                    """
                    UPDATE tax_invoice_requests
                    SET business_name = ?, business_number = ?, recipient_email = ?, contact_name = ?, status = 'requested', updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, timestamp, row["id"]),
                )


    def _create_charge_order_record(
        self,
        conn: DatabaseConnection,
        *,
        user_id: str,
        amount: int,
        vat_amount: int,
        total_amount: int,
        payment_channel: str,
        payment_method_detail: str,
        status: str,
        depositor_name: str = "",
        receipt_type: str = "none",
        receipt_payload: Optional[Dict[str, Any]] = None,
        reference: str = "",
        pg_provider: str = "",
        payment_payload: Optional[Dict[str, Any]] = None,
        bank_account_snapshot: Optional[Dict[str, Any]] = None,
        expires_at: str = "",
    ) -> Dict[str, Any]:
        created_at = now_iso()
        charge_order_id = f"chg_{uuid4().hex[:16]}"
        order_code = generate_charge_order_code()
        while conn.execute("SELECT 1 FROM charge_orders WHERE order_code = ?", (order_code,)).fetchone() is not None:
            order_code = generate_charge_order_code()
        conn.execute(
            """
            INSERT INTO charge_orders (
                id, order_code, user_id, amount, vat_amount, total_amount,
                payment_channel, payment_method_detail, status, depositor_name,
                receipt_type, receipt_payload_json, reference,
                pg_provider, pg_order_id, pg_payment_key, failure_reason,
                payment_payload_json, bank_account_snapshot_json, confirmed_at,
                expires_at, paid_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, ?, ?, '', ?, ?)
            """,
            (
                charge_order_id,
                order_code,
                user_id,
                int(amount),
                int(vat_amount),
                int(total_amount),
                payment_channel,
                payment_method_detail,
                status,
                depositor_name,
                receipt_type,
                as_json(receipt_payload or {}),
                reference,
                pg_provider,
                as_json(payment_payload or {}),
                as_json(bank_account_snapshot or {}),
                "",
                expires_at,
                created_at,
                created_at,
            ),
        )
        row = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
        return dict(row) if row is not None else {}

    def _complete_charge_order(
        self,
        conn: DatabaseConnection,
        charge_order_id: str,
        *,
        payment_method: str,
        payment_status: str = "completed",
        reference: str = "",
        payment_payload: Optional[Dict[str, Any]] = None,
        paid_total_amount: Optional[int] = None,
        memo_prefix: str = "캐시 충전",
    ) -> Dict[str, Any]:
        charge_order = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
        if charge_order is None:
            raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)
        if charge_order["status"] == "paid":
            wallet = self._wallet_payload(conn, str(charge_order["user_id"]))
            return {
                "chargeOrder": self._charge_order_payload(dict(charge_order)),
                "wallet": wallet,
                "paymentReference": charge_order["reference"],
                "paymentId": f"payment_{charge_order_id}",
            }
        if charge_order["status"] in {"cancelled", "expired", "failed", "refunded"}:
            raise PanelError("완료할 수 없는 충전 주문 상태입니다.")
        expected_total_amount = int(charge_order["total_amount"])
        if paid_total_amount is not None and int(paid_total_amount) != expected_total_amount:
            raise PanelError("결제 금액 검증에 실패했습니다.")

        timestamp = now_iso()
        payment_reference = reference or charge_order["reference"] or f"PMT-{dt.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        merged_payment_payload = parse_json(charge_order["payment_payload_json"], {})
        merged_payment_payload.update(payment_payload or {})
        transition = conn.execute(
            """
            UPDATE charge_orders
            SET status = 'paid', reference = ?, payment_payload_json = ?, confirmed_at = ?, paid_at = ?, updated_at = ?
            WHERE id = ? AND status NOT IN ('paid', 'cancelled', 'expired', 'failed', 'refunded')
            """,
            (payment_reference, as_json(merged_payment_payload), timestamp, timestamp, timestamp, charge_order_id),
        )
        if transition.rowcount != 1:
            refreshed = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
            if refreshed is not None and refreshed["status"] == "paid":
                wallet = self._wallet_payload(conn, str(refreshed["user_id"]))
                return {
                    "chargeOrder": self._charge_order_payload(dict(refreshed)),
                    "wallet": wallet,
                    "paymentReference": refreshed["reference"],
                    "paymentId": f"payment_{charge_order_id}",
                }
            raise PanelError("완료할 수 없는 충전 주문 상태입니다.", status=409)

        balance_after = self._change_wallet_available_balance(
            conn,
            str(charge_order["user_id"]),
            int(charge_order["amount"]),
            timestamp=timestamp,
        )
        tx_id = f"tx_charge_{charge_order_id}"
        if conn.execute("SELECT 1 FROM balance_transactions WHERE id = ?", (tx_id,)).fetchone() is None:
            conn.execute(
                """
                INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id,
                    charge_order["user_id"],
                    int(charge_order["amount"]),
                    balance_after,
                    "charge",
                    f"{memo_prefix} {money(int(charge_order['amount']))}",
                    timestamp,
                ),
            )
        self._append_wallet_ledger_entry(
            conn,
            ledger_id=f"ledger_charge_{charge_order_id}",
            user_id=str(charge_order["user_id"]),
            entry_type="charge",
            amount=int(charge_order["amount"]),
            balance_after=balance_after,
            memo=f"{memo_prefix} {money(int(charge_order['amount']))}",
            related_charge_order_id=charge_order_id,
            created_at=timestamp,
        )
        payment_id = f"payment_{charge_order_id}"
        if conn.execute("SELECT 1 FROM payment_records WHERE id = ?", (payment_id,)).fetchone() is None:
            conn.execute(
                """
                INSERT INTO payment_records (
                    id, user_id, amount, payment_method, payment_status, reference, failure_reason, admin_adjustment_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, '', '', ?, ?)
                """,
                (
                    payment_id,
                    charge_order["user_id"],
                    int(charge_order["total_amount"]),
                    payment_method,
                    payment_status,
                    payment_reference,
                    timestamp,
                    timestamp,
                ),
            )
        self._refresh_wallet_pending_balance(conn, str(charge_order["user_id"]))
        updated = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
        return {
            "chargeOrder": self._charge_order_payload(dict(updated or charge_order)),
            "wallet": self._wallet_payload(conn, str(charge_order["user_id"])),
            "paymentReference": payment_reference,
            "paymentId": f"payment_{charge_order_id}",
        }

    def _normalize_customer_email(self, email: str) -> str:
        normalized = str(email or "").strip().lower()
        if not normalized or "@" not in normalized or "." not in normalized.split("@", 1)[-1]:
            raise PanelError("유효한 이메일을 입력해 주세요.")
        return normalized

    def _assert_available_customer_email(
        self,
        conn: DatabaseConnection,
        email: str,
        *,
        exclude_user_id: str = "",
    ) -> None:
        params: List[Any] = [email]
        query = "SELECT id FROM users WHERE email = ?"
        if exclude_user_id:
            query += " AND id != ?"
            params.append(exclude_user_id)
        exists = conn.execute(query, params).fetchone()
        if exists is not None:
            raise PanelError("이미 사용 중인 이메일입니다.")

    def _latest_email_verification_challenge(
        self,
        conn: DatabaseConnection,
        email: str,
        purpose: str,
    ) -> Optional[Dict[str, Any]]:
        return conn.execute(
            """
            SELECT *
            FROM email_verification_challenges
            WHERE email = ? AND purpose = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, purpose),
        ).fetchone()

    def start_signup_email_verification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        email = self._normalize_customer_email(payload.get("email") or "")
        now = dt.datetime.now().astimezone()
        timestamp = now.isoformat(timespec="seconds")
        resend_available_at = (now + dt.timedelta(seconds=AUTH_VERIFICATION_RESEND_INTERVAL_SECONDS)).isoformat(timespec="seconds")
        expires_at = (now + dt.timedelta(seconds=AUTH_VERIFICATION_TTL_SECONDS)).isoformat(timespec="seconds")
        code = generate_email_verification_code()
        code_hash = hash_token_value(code)

        with self._connect() as conn:
            self._assert_available_customer_email(conn, email)
            row = self._latest_email_verification_challenge(conn, email, AUTH_VERIFICATION_PURPOSE_SIGNUP)
            if row is not None and not row["used_at"]:
                retry_after = parse_iso_datetime(row["resend_available_at"])
                if row["status"] == "pending" and retry_after and retry_after > now:
                    remaining = max(1, int((retry_after - now).total_seconds()))
                    raise PanelError(f"{remaining}초 후에 인증코드를 다시 보낼 수 있어요.", status=429)

            delivery = dispatch_signup_verification_email(email, code)
            if row is not None and not row["used_at"]:
                conn.execute(
                    """
                    UPDATE email_verification_challenges
                    SET code_hash = ?,
                        verification_token_hash = '',
                        status = 'pending',
                        attempt_count = 0,
                        send_count = COALESCE(send_count, 0) + 1,
                        last_sent_at = ?,
                        resend_available_at = ?,
                        expires_at = ?,
                        verified_at = '',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (code_hash, timestamp, resend_available_at, expires_at, timestamp, row["id"]),
                )
                challenge_id = row["id"]
            else:
                challenge_id = f"evc_{uuid4().hex[:16]}"
                conn.execute(
                    """
                    INSERT INTO email_verification_challenges (
                        id, email, purpose, code_hash, verification_token_hash, status,
                        attempt_count, send_count, last_sent_at, resend_available_at,
                        expires_at, verified_at, used_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, '', 'pending', 0, 1, ?, ?, ?, '', '', ?, ?)
                    """,
                    (
                        challenge_id,
                        email,
                        AUTH_VERIFICATION_PURPOSE_SIGNUP,
                        code_hash,
                        timestamp,
                        resend_available_at,
                        expires_at,
                        timestamp,
                        timestamp,
                    ),
                )
            conn.commit()

        result = {
            "email": email,
            "challengeId": challenge_id,
            "expiresAt": expires_at,
            "resendAvailableAt": resend_available_at,
            "deliveryMode": delivery.get("deliveryMode", ""),
            "sent": True,
        }
        preview_code = str(delivery.get("previewCode") or "").strip()
        if preview_code and not is_production_runtime():
            result["previewCode"] = preview_code
        return result

    def verify_signup_email_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        email = self._normalize_customer_email(payload.get("email") or "")
        code = re.sub(r"\D+", "", str(payload.get("code") or ""))
        if len(code) != AUTH_VERIFICATION_CODE_LENGTH:
            raise PanelError(f"{AUTH_VERIFICATION_CODE_LENGTH}자리 인증코드를 입력해 주세요.")

        now = dt.datetime.now().astimezone()
        timestamp = now.isoformat(timespec="seconds")
        with self._connect() as conn:
            row = self._latest_email_verification_challenge(conn, email, AUTH_VERIFICATION_PURPOSE_SIGNUP)
            if row is None or row["used_at"]:
                raise PanelError("먼저 인증코드를 발송해 주세요.", status=404)
            if row["status"] != "pending":
                raise PanelError("새 인증코드를 다시 요청해 주세요.", status=409)

            expires_at = parse_iso_datetime(row["expires_at"])
            if expires_at is None or expires_at <= now:
                conn.execute(
                    "UPDATE email_verification_challenges SET status = 'expired', updated_at = ? WHERE id = ?",
                    (timestamp, row["id"]),
                )
                conn.commit()
                raise PanelError("인증코드가 만료되었습니다. 다시 요청해 주세요.", status=410)

            attempt_count = int(row["attempt_count"] or 0)
            if attempt_count >= AUTH_VERIFICATION_MAX_ATTEMPTS:
                conn.execute(
                    "UPDATE email_verification_challenges SET status = 'failed', updated_at = ? WHERE id = ?",
                    (timestamp, row["id"]),
                )
                conn.commit()
                raise PanelError("인증 시도 횟수를 초과했습니다. 새 코드를 요청해 주세요.", status=429)

            if not hmac.compare_digest(hash_token_value(code), str(row["code_hash"] or "")):
                attempt_count += 1
                next_status = "failed" if attempt_count >= AUTH_VERIFICATION_MAX_ATTEMPTS else "pending"
                conn.execute(
                    "UPDATE email_verification_challenges SET attempt_count = ?, status = ?, updated_at = ? WHERE id = ?",
                    (attempt_count, next_status, timestamp, row["id"]),
                )
                conn.commit()
                remaining = max(0, AUTH_VERIFICATION_MAX_ATTEMPTS - attempt_count)
                if remaining:
                    raise PanelError(f"인증코드가 올바르지 않습니다. 남은 시도 {remaining}회", status=400)
                raise PanelError("인증 시도 횟수를 초과했습니다. 새 코드를 요청해 주세요.", status=429)

            verification_token = secrets.token_urlsafe(24)
            complete_by = (now + dt.timedelta(seconds=AUTH_VERIFICATION_COMPLETE_TTL_SECONDS)).isoformat(timespec="seconds")
            conn.execute(
                """
                UPDATE email_verification_challenges
                SET status = 'verified',
                    verification_token_hash = ?,
                    verified_at = ?,
                    expires_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (hash_token_value(verification_token), timestamp, complete_by, timestamp, row["id"]),
            )
            conn.commit()
            return {
                "email": email,
                "verified": True,
                "verifiedAt": timestamp,
                "verificationToken": verification_token,
                "completeBy": complete_by,
            }

    def _record_user_consents(
        self,
        conn: DatabaseConnection,
        user_id: str,
        *,
        terms_agreed: bool,
        privacy_agreed: bool,
        age_confirmed: bool,
        marketing_agreed: bool,
        agreed_at: str,
    ) -> None:
        rows = [
            ("terms", LEGAL_DOCUMENT_VERSIONS["terms"], terms_agreed),
            ("privacy", LEGAL_DOCUMENT_VERSIONS["privacy"], privacy_agreed),
            ("age", LEGAL_DOCUMENT_VERSIONS["age"], age_confirmed),
            ("marketing", LEGAL_DOCUMENT_VERSIONS["marketing"], marketing_agreed),
        ]
        for consent_type, version, agreed in rows:
            existing = conn.execute(
                "SELECT id FROM user_consents WHERE user_id = ? AND consent_type = ? AND consent_version = ?",
                (user_id, consent_type, version),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO user_consents (
                        id, user_id, consent_type, consent_version, is_agreed, agreed_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"consent_{uuid4().hex[:12]}", user_id, consent_type, version, bool_to_int(agreed), agreed_at, agreed_at),
                )
            else:
                conn.execute(
                    "UPDATE user_consents SET is_agreed = ?, agreed_at = ? WHERE id = ?",
                    (bool_to_int(agreed), agreed_at, existing["id"]),
                )

    def authenticate_public_user(self, email: str, password: str) -> Dict[str, Any]:
        normalized_email = self._normalize_customer_email(email)
        if not str(password or ""):
            raise PanelError("비밀번호를 입력해 주세요.")

        with self._connect() as conn:
            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE email = ? AND is_active = 1 AND account_status = 'active' AND role != 'admin'
                LIMIT 1
                """,
                (normalized_email,),
            ).fetchone()
            if user is None or not verify_password(password, user["password_hash"]):
                raise PanelError("이메일 또는 비밀번호가 올바르지 않습니다.", status=401)
            timestamp = now_iso()
            conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, user["id"]))
            identity = conn.execute(
                "SELECT id FROM user_social_identities WHERE user_id = ? AND provider = 'email' AND provider_user_id = ?",
                (user["id"], normalized_email),
            ).fetchone()
            if identity is None:
                conn.execute(
                    """
                    INSERT INTO user_social_identities (
                        id, user_id, provider, provider_user_id, provider_email, linked_at, last_login_at, created_at, updated_at
                    ) VALUES (?, ?, 'email', ?, ?, ?, ?, ?, ?)
                    """,
                    (f"identity_{uuid4().hex[:12]}", user["id"], normalized_email, normalized_email, timestamp, timestamp, timestamp, timestamp),
                )
            else:
                conn.execute(
                    "UPDATE user_social_identities SET provider_email = ?, last_login_at = ?, updated_at = ? WHERE id = ?",
                    (normalized_email, timestamp, timestamp, identity["id"]),
                )
            conn.commit()
            return self._user_summary(conn, user["id"])

    def register_public_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        email = self._normalize_customer_email(payload.get("email") or "")
        password = str(payload.get("password") or "")
        password_confirmation = str(payload.get("passwordConfirmation") or "")
        verification_token = str(payload.get("verificationToken") or "").strip()
        name = str(payload.get("name") or payload.get("nickname") or "").strip()
        terms_agreed = bool(payload.get("termsAgreed"))
        privacy_agreed = bool(payload.get("privacyAgreed"))
        marketing_agreed = bool(payload.get("marketingAgreed"))
        age_confirmed = bool(payload.get("ageConfirmed"))

        if not name:
            raise PanelError("이름 또는 닉네임을 입력해 주세요.")
        if not verification_token:
            raise PanelError("이메일 인증을 먼저 완료해 주세요.", status=409)
        validate_public_password(password, email=email, name=name)
        if password != password_confirmation:
            raise PanelError("비밀번호 확인이 일치하지 않습니다.")
        if not terms_agreed:
            raise PanelError("이용약관 동의가 필요합니다.")
        if not privacy_agreed:
            raise PanelError("개인정보처리방침 동의가 필요합니다.")
        if not age_confirmed:
            raise PanelError("연령 확인 문구에 동의해 주세요.")

        timestamp = now_iso()
        user_id = f"user_{uuid4().hex[:12]}"
        with self._connect() as conn:
            self._assert_available_customer_email(conn, email)
            verification_row = self._latest_email_verification_challenge(conn, email, AUTH_VERIFICATION_PURPOSE_SIGNUP)
            if verification_row is None or verification_row["used_at"] or verification_row["status"] != "verified":
                raise PanelError("이메일 인증을 다시 진행해 주세요.", status=409)
            expires_at = parse_iso_datetime(verification_row["expires_at"])
            if expires_at is None or expires_at <= dt.datetime.now().astimezone():
                raise PanelError("이메일 인증이 만료되었습니다. 다시 진행해 주세요.", status=410)
            if not hmac.compare_digest(
                hash_token_value(verification_token),
                str(verification_row["verification_token_hash"] or ""),
            ):
                raise PanelError("이메일 인증 확인 정보가 올바르지 않습니다. 다시 진행해 주세요.", status=409)
            conn.execute(
                """
                INSERT INTO users (
                    id, name, email, password_hash, phone, tier, role, avatar_label, balance, is_active,
                    account_status, marketing_opt_in, marketing_opt_in_at, notes, last_login_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, '', 'STANDARD', 'customer', ?, 0, 1, 'active', ?, ?, '', ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    email,
                    hash_password(password),
                    avatar_label(name),
                    bool_to_int(marketing_agreed),
                    timestamp if marketing_agreed else "",
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            )
            conn.execute(
                """
                INSERT INTO user_social_identities (
                    id, user_id, provider, provider_user_id, provider_email, linked_at, last_login_at, created_at, updated_at
                ) VALUES (?, ?, 'email', ?, ?, ?, ?, ?, ?)
                """,
                (f"identity_{uuid4().hex[:12]}", user_id, email, email, timestamp, timestamp, timestamp, timestamp),
            )
            conn.execute(
                """
                UPDATE email_verification_challenges
                SET used_at = ?, status = 'used', updated_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, verification_row["id"]),
            )
            conn.execute(
                """
                INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
                VALUES (?, 0, 0, ?, ?)
                """,
                (user_id, timestamp, timestamp),
            )
            self._record_user_consents(
                conn,
                user_id,
                terms_agreed=terms_agreed,
                privacy_agreed=privacy_agreed,
                age_confirmed=age_confirmed,
                marketing_agreed=marketing_agreed,
                agreed_at=timestamp,
            )
            conn.commit()
            return self._user_summary(conn, user_id)

    def public_user_for_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = self._public_user_row(conn, user_id)
            if row is None:
                return None
            return self._user_summary(conn, user_id)

    def public_shell(self, user_id: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            user = self._user_summary(conn, user_id) if user_id else None
            popup_row = conn.execute("SELECT * FROM home_popups ORDER BY updated_at DESC LIMIT 1").fetchone()
            site_settings_row = self._site_settings_row(conn)
            site_settings = self._site_settings_public_payload(site_settings_row)
            banners = [
                dict(row)
                for row in conn.execute("SELECT * FROM home_banners WHERE is_active = 1 ORDER BY sort_order")
            ]
            featured = [
                dict(row)
                for row in conn.execute("SELECT * FROM home_spotlights WHERE section_key = 'featured' ORDER BY sort_order LIMIT 6")
            ]
            supports = [
                dict(row)
                for row in conn.execute("SELECT * FROM support_links ORDER BY sort_order LIMIT 4")
            ]
            notices = [
                {
                    **dict(row),
                    "publishedLabel": self._relative_date_label(row["published_at"]),
                }
                for row in conn.execute("SELECT * FROM notices ORDER BY pinned DESC, published_at DESC LIMIT 1")
            ]
            platforms = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, slug, display_name, description, icon, image_url, accent_color
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
            company = {
                "name": site_settings["siteName"],
                "representative": "운영 관리자",
                "contact": str(os.environ.get("SMM_PANEL_SUPPORT_CONTACT") or "").strip(),
                "hours": "평일 10:00 - 19:00",
            }
            return {
                "app": {
                    "name": site_settings["siteName"],
                    "subtitle": "고객 친화형 SMM 서비스 쇼핑몰",
                    "accentColor": "#b96bc6",
                },
                "siteSettings": site_settings,
                "user": user,
                "viewer": {
                    "authenticated": bool(user),
                },
                "topLinks": [
                    {"label": "서비스 소개서", "route": "/products"},
                    {"label": "이용 가이드", "route": "/help"},
                ],
                "popup": self._popup_public_payload(popup_row) if popup_row else None,
                "platforms": [
                    {
                        "id": platform["id"],
                        "slug": platform["slug"],
                        "displayName": platform["display_name"],
                        "description": platform["description"],
                        "icon": platform["icon"],
                        "logoImageUrl": platform["image_url"],
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
                "notices": notices,
                "authConfig": {
                    "signupEnabled": True,
                    "loginRoute": "/auth",
                    "passwordResetEnabled": False,
                    "signupRoute": "/auth/signup",
                    "emailVerificationRequired": True,
                    "verificationCodeLength": AUTH_VERIFICATION_CODE_LENGTH,
                    "verificationExpiresInSeconds": AUTH_VERIFICATION_TTL_SECONDS,
                    "verificationCompleteExpiresInSeconds": AUTH_VERIFICATION_COMPLETE_TTL_SECONDS,
                    "verificationResendIntervalSeconds": AUTH_VERIFICATION_RESEND_INTERVAL_SECONDS,
                    "passwordPolicy": {
                        "minimumLength": PUBLIC_PASSWORD_MIN_LENGTH,
                        "recommendedLength": PUBLIC_PASSWORD_RECOMMENDED_LENGTH,
                        "veryStrongLength": PUBLIC_PASSWORD_VERY_STRONG_LENGTH,
                    },
                    "oauthProviders": oauth_provider_catalog(),
                },
                "company": company,
                "isShell": True,
            }

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
                    SELECT id, slug, display_name, description, icon, image_url, accent_color
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
                "representative": "운영 관리자",
                "contact": str(os.environ.get("SMM_PANEL_SUPPORT_CONTACT") or "").strip(),
                "hours": "평일 10:00 - 19:00",
            }
            legal_documents = legal_document_catalog()
            guides = [
                {
                    "id": "guide_order",
                    "title": "주문 전 확인 가이드",
                    "description": "플랫폼별 입력 형식, 계정 공개 여부, 환불 가능 구간을 먼저 확인하세요.",
                },
                {
                    "id": "guide_payment",
                    "title": "충전 및 결제 안내",
                    "description": "결제수단 확인, 입금/승인 상태, 충전 후 사용 흐름을 안내합니다.",
                },
                {
                    "id": "guide_policy",
                    "title": "환불·리필·정책 요약",
                    "description": "주문 시작 전 취소 가능 구간, 진행 후 처리 기준, 재작업 정책을 정리했습니다.",
                },
            ]

            return {
                "app": {
                    "name": site_settings["siteName"],
                    "subtitle": "고객 친화형 SMM 서비스 쇼핑몰",
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
                    {"label": "이용 가이드", "route": "/help"},
                ],
                "popup": self._popup_public_payload(popup_row) if popup_row else None,
                "platforms": [
                    {
                        "id": platform["id"],
                        "slug": platform["slug"],
                        "displayName": platform["display_name"],
                        "description": platform["description"],
                        "icon": platform["icon"],
                        "logoImageUrl": platform["image_url"],
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
                "guides": guides,
                "legalDocuments": legal_documents,
                "authConfig": {
                    "signupEnabled": True,
                    "loginRoute": "/auth",
                    "passwordResetEnabled": False,
                    "signupRoute": "/auth/signup",
                    "emailVerificationRequired": True,
                    "verificationCodeLength": AUTH_VERIFICATION_CODE_LENGTH,
                    "verificationExpiresInSeconds": AUTH_VERIFICATION_TTL_SECONDS,
                    "verificationCompleteExpiresInSeconds": AUTH_VERIFICATION_COMPLETE_TTL_SECONDS,
                    "verificationResendIntervalSeconds": AUTH_VERIFICATION_RESEND_INTERVAL_SECONDS,
                    "passwordPolicy": {
                        "minimumLength": PUBLIC_PASSWORD_MIN_LENGTH,
                        "recommendedLength": PUBLIC_PASSWORD_RECOMMENDED_LENGTH,
                        "veryStrongLength": PUBLIC_PASSWORD_VERY_STRONG_LENGTH,
                    },
                    "oauthProviders": oauth_provider_catalog(),
                },
                "chargeConfig": self.charge_config_public_payload(),
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
                ps.image_url AS platform_logo_image_url,
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
            GROUP BY
                ps.id,
                ps.slug,
                ps.display_name,
                ps.description,
                ps.icon,
                ps.image_url,
                ps.accent_color,
                ps.sort_order,
                pg.id,
                pg.name,
                pg.description,
                pg.sort_order,
                pc.id,
                pc.name,
                pc.description,
                pc.option_label_name,
                pc.hero_subtitle,
                pc.sort_order
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
                    "logoImageUrl": row["platform_logo_image_url"],
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
                    ps.image_url AS platform_logo_image_url,
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
                form_structure = ensure_request_memo_form_structure(
                    parse_json(row["form_structure_json"], {}),
                    "추가 요청사항",
                )
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
                        "formStructure": form_structure,
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
                "serviceDescriptionHtml": sanitize_rich_html(category["service_description_html"]),
                "caution": parse_json(category["caution_json"], []),
                "refundNotice": parse_json(category["refund_notice_json"], []),
                "platform": {
                    "id": category["platform_id"],
                    "slug": category["platform_slug"],
                    "displayName": category["platform_name"],
                    "icon": category["platform_icon"],
                    "logoImageUrl": category["platform_logo_image_url"],
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
                        "orderChannel": row["order_channel"] or ORDER_CHANNEL_WEB,
                        "orderChannelLabel": order_channel_label(row["order_channel"] or ORDER_CHANNEL_WEB),
                        "dispatchStatus": row["dispatch_status"] or ORDER_DISPATCH_UNMAPPED,
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
        return {"transactions": self.list_wallet_ledger(user_id, limit=50)["entries"]}

    def get_wallet(self, user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        with self._connect() as conn:
            wallet = self._wallet_payload(conn, user_id)
        return {"wallet": wallet}

    def list_wallet_ledger(
        self,
        user_id: str = "",
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        filters = filters or {}
        conditions, params, safe_limit = wallet_ledger_filter_clause(filters, user_id=user_id, limit=limit)
        rows = self._fetchall(
            f"""
            SELECT
                wl.*,
                co.order_code,
                co.payment_channel,
                co.payment_method_detail,
                co.receipt_type,
                co.status AS charge_status,
                co.reference AS charge_reference,
                co.failure_reason AS charge_failure_reason
            FROM wallet_ledger wl
            LEFT JOIN charge_orders co
              ON co.id = wl.related_charge_order_id
            WHERE {' AND '.join(conditions)}
            ORDER BY wl.created_at DESC
            LIMIT ?
            """,
            [*params, safe_limit],
        )
        entries = [
            wallet_ledger_entry_payload(
                row,
                payment_method_detail_label=self._payment_method_detail_label(
                    row["payment_channel"] or "",
                    row["payment_method_detail"] or "",
                ),
                created_label=self._relative_date_label(row["created_at"]),
            )
            for row in rows
        ]
        return {"wallet": self.get_wallet(user_id)["wallet"], "entries": entries}

    def list_charge_orders(
        self,
        user_id: str = "",
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        filters = filters or {}
        conditions, params, safe_limit = charge_order_filter_clause(filters, user_id=user_id, limit=limit)
        rows = self._fetchall(
            f"""
            SELECT *
            FROM charge_orders
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [*params, safe_limit],
        )
        return {
            "wallet": self.get_wallet(user_id)["wallet"],
            "chargeOrders": [self._charge_order_payload(row) for row in rows],
        }

    def get_charge_order(self, charge_order_id: str, user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        row = self._fetchone(
            """
            SELECT *
            FROM charge_orders
            WHERE id = ? AND user_id = ?
            """,
            (charge_order_id, user_id),
        )
        payload = self._charge_order_payload(row)
        with self._connect() as conn:
            cash_receipt = conn.execute(
                "SELECT * FROM cash_receipt_requests WHERE charge_order_id = ?",
                (charge_order_id,),
            ).fetchone()
            tax_invoice = conn.execute(
                "SELECT * FROM tax_invoice_requests WHERE charge_order_id = ?",
                (charge_order_id,),
            ).fetchone()
        return {
            "wallet": self.get_wallet(user_id)["wallet"],
            "chargeOrder": payload,
            "cashReceiptRequest": dict(cash_receipt) if cash_receipt is not None else None,
            "taxInvoiceRequest": dict(tax_invoice) if tax_invoice is not None else None,
        }

    def create_charge_order(self, payload: Dict[str, Any], user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        try:
            charge_request = normalize_charge_order_request(
                payload,
                card_payment_enabled=card_payment_configured(),
                bank_transfer_enabled=bank_transfer_configured(),
            )
        except ChargeOrderRequestError as exc:
            raise PanelError(str(exc), status=exc.status) from exc
        payment_channel = charge_request["paymentChannel"]
        payment_method_detail = charge_request["paymentMethodDetail"]
        depositor_name = charge_request["depositorName"]
        receipt_type = charge_request["receiptType"]
        receipt_payload = charge_request["receiptPayload"]
        breakdown = charge_request["breakdown"]
        status = charge_request["status"]
        expires_at = self._resolve_charge_expiry(payment_channel)
        bank_snapshot = self._bank_transfer_public_payload() if charge_request["requiresBankSnapshot"] else {}

        with self._connect() as conn:
            charge_order = self._create_charge_order_record(
                conn,
                user_id=user_id,
                amount=breakdown["amount"],
                vat_amount=breakdown["vatAmount"],
                total_amount=breakdown["totalAmount"],
                payment_channel=payment_channel,
                payment_method_detail=payment_method_detail,
                status=status,
                depositor_name=depositor_name,
                receipt_type=receipt_type,
                receipt_payload=receipt_payload,
                pg_provider=payment_provider_name(),
                bank_account_snapshot=bank_snapshot,
                expires_at=expires_at,
            )
            if receipt_type != "none":
                self._record_receipt_request(
                    conn,
                    charge_order_id=str(charge_order["id"]),
                    user_id=user_id,
                    receipt_type=receipt_type,
                    receipt_payload=receipt_payload,
                    timestamp=now_iso(),
                )
            wallet = self._wallet_payload(conn, user_id)
            conn.commit()
        return {
            "chargeOrder": self._charge_order_payload(charge_order),
            "wallet": wallet,
            "chargeConfig": self.charge_config_public_payload(),
        }

    def start_charge_order_payment(self, charge_order_id: str, payload: Dict[str, Any], user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        method_detail = str(payload.get("paymentMethodDetail") or "").strip().lower()
        if not card_payment_configured():
            raise PanelError("현재 선택할 수 없는 결제수단입니다. 계좌입금을 선택하거나 고객센터로 문의해 주세요.", status=503)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM charge_orders WHERE id = ? AND user_id = ?",
                (charge_order_id, user_id),
            ).fetchone()
            if row is None:
                raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)
            if row["payment_channel"] not in {"card", "easy_pay"}:
                raise PanelError("카드/간편결제 주문만 결제를 시작할 수 있습니다.")
            if row["status"] == "paid":
                return {"chargeOrder": self._charge_order_payload(dict(row)), "wallet": self._wallet_payload(conn, user_id)}
            timestamp = now_iso()
            payment_payload = parse_json(row["payment_payload_json"], {})
            payment_payload.update(
                {
                    "provider": payment_provider_name(),
                    "publicKey": payment_public_key(),
                    "requestedAt": timestamp,
                    "methodDetail": method_detail or row["payment_method_detail"],
                }
            )
            pg_order_id = row["pg_order_id"] or f"pg_{uuid4().hex[:18]}"
            conn.execute(
                """
                UPDATE charge_orders
                SET payment_method_detail = ?, pg_provider = ?, pg_order_id = ?, payment_payload_json = ?, status = 'awaiting_payment', updated_at = ?
                WHERE id = ?
                """,
                (method_detail or row["payment_method_detail"], payment_provider_name(), pg_order_id, as_json(payment_payload), timestamp, charge_order_id),
            )
            updated = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
            conn.commit()
        return {
            "chargeOrder": self._charge_order_payload(dict(updated or row)),
            "wallet": self.get_wallet(user_id)["wallet"],
            "paymentSession": {
                "provider": payment_provider_name(),
                "providerConfigured": True,
                "publicKey": payment_public_key(),
                "orderId": charge_order_id,
                "orderCode": str((updated or row)["order_code"]),
                "pgOrderId": str((updated or row)["pg_order_id"]),
                "amount": int((updated or row)["amount"]),
                "vatAmount": int((updated or row)["vat_amount"]),
                "totalAmount": int((updated or row)["total_amount"]),
                "methodDetail": method_detail or str((updated or row)["payment_method_detail"] or ""),
            },
        }

    def submit_charge_order_deposit_request(self, charge_order_id: str, payload: Dict[str, Any], user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        depositor_name = str(payload.get("depositorName") or "").strip()
        receipt_type = str(payload.get("receiptType") or "none").strip().lower()
        receipt_payload = payload.get("receiptPayload") if isinstance(payload.get("receiptPayload"), dict) else {}
        if not depositor_name:
            raise PanelError("입금자명을 입력해 주세요.")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM charge_orders WHERE id = ? AND user_id = ?",
                (charge_order_id, user_id),
            ).fetchone()
            if row is None:
                raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)
            if row["payment_channel"] != "bank_transfer":
                raise PanelError("계좌입금 주문만 입금 요청을 접수할 수 있습니다.")
            timestamp = now_iso()
            bank_snapshot = parse_json(row["bank_account_snapshot_json"], {}) or self._bank_transfer_public_payload()
            conn.execute(
                """
                UPDATE charge_orders
                SET depositor_name = ?, receipt_type = ?, receipt_payload_json = ?, bank_account_snapshot_json = ?, status = 'awaiting_deposit', updated_at = ?
                WHERE id = ?
                """,
                (depositor_name, receipt_type, as_json(receipt_payload), as_json(bank_snapshot), timestamp, charge_order_id),
            )
            if receipt_type != "none":
                self._record_receipt_request(
                    conn,
                    charge_order_id=charge_order_id,
                    user_id=user_id,
                    receipt_type=receipt_type,
                    receipt_payload=receipt_payload,
                    timestamp=timestamp,
                )
            updated = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
            wallet = self._wallet_payload(conn, user_id)
            conn.commit()
        return {
            "chargeOrder": self._charge_order_payload(dict(updated or row)),
            "wallet": wallet,
            "bankTransfer": self._bank_transfer_public_payload(),
        }

    def confirm_charge_order(self, charge_order_id: str, payload: Dict[str, Any], user_id: str = "") -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM charge_orders WHERE id = ? AND user_id = ?",
                (charge_order_id, user_id),
            ).fetchone()
            if row is None:
                raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)
            if row["payment_channel"] == "bank_transfer":
                raise PanelError("계좌입금은 입금 확인 후 반영됩니다.", status=409)
            raise PanelError("결제 승인 확인이 완료되지 않았습니다. 잠시 후 다시 시도하거나 고객센터로 문의해 주세요.", status=503)

    def process_payment_webhook(
        self,
        payload: Dict[str, Any],
        *,
        provided_secret: str = "",
        provided_signature: str = "",
        provided_timestamp: str = "",
        raw_body: bytes = b"",
    ) -> Dict[str, Any]:
        expected_secret = payment_webhook_secret()
        if not expected_secret:
            raise PanelError("웹훅 비밀키가 설정되지 않았습니다.", status=503)
        signature_valid = verify_payment_webhook_signature(
            expected_secret,
            raw_body,
            provided_signature,
            provided_timestamp,
        )
        legacy_secret_valid = provided_secret == expected_secret and legacy_payment_webhook_secret_allowed()
        if not signature_valid and not legacy_secret_valid:
            raise PanelError("유효하지 않은 웹훅 요청입니다.", status=401)
        provider = str(payload.get("provider") or payment_provider_name() or "unknown").strip().lower()
        event_key = str(payload.get("eventKey") or payload.get("id") or payload.get("eventId") or "").strip()
        event_type = str(payload.get("eventType") or payload.get("type") or "").strip()
        if not event_key:
            raise PanelError("웹훅 이벤트 키가 필요합니다.")
        charge_order_id = str(payload.get("chargeOrderId") or "").strip()
        order_code = str(payload.get("orderCode") or "").strip()
        status = str(payload.get("status") or "").strip().lower()
        paid_total_amount = int(float(payload.get("totalAmount") or payload.get("amount") or 0) or 0)
        reference = str(payload.get("reference") or payload.get("paymentKey") or payload.get("transactionId") or "").strip()
        timestamp = now_iso()

        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM payment_webhooks WHERE event_key = ?", (event_key,)).fetchone()
            if existing is not None:
                return {
                    "ok": True,
                    "duplicate": True,
                    "webhookId": existing["id"],
                    "status": existing["status"],
                }
            charge_order = None
            if charge_order_id:
                charge_order = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
            elif order_code:
                charge_order = conn.execute("SELECT * FROM charge_orders WHERE order_code = ?", (order_code,)).fetchone()

            webhook_id = f"wh_{uuid4().hex[:16]}"
            insert_cursor = conn.execute(
                """
                INSERT INTO payment_webhooks (
                    id, provider, event_key, event_type, charge_order_id, status, payload_json, processed_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'received', ?, '', ?, ?)
                ON CONFLICT(event_key) DO NOTHING
                """,
                (webhook_id, provider, event_key, event_type, charge_order["id"] if charge_order is not None else None, as_json(payload), timestamp, timestamp),
            )
            if insert_cursor.rowcount != 1:
                existing = conn.execute("SELECT * FROM payment_webhooks WHERE event_key = ?", (event_key,)).fetchone()
                conn.commit()
                return {
                    "ok": True,
                    "duplicate": True,
                    "webhookId": existing["id"] if existing is not None else "",
                    "status": existing["status"] if existing is not None else "duplicate",
                }

            result_payload: Dict[str, Any] = {"ok": True, "webhookId": webhook_id, "status": "received"}
            if charge_order is None:
                conn.execute("UPDATE payment_webhooks SET status = 'ignored', processed_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, webhook_id))
                conn.commit()
                result_payload["status"] = "ignored"
                return result_payload

            if status in {"paid", "succeeded", "success", "completed"}:
                result = self._complete_charge_order(
                    conn,
                    str(charge_order["id"]),
                    payment_method=str(charge_order["payment_channel"]),
                    payment_status="completed",
                    reference=reference,
                    payment_payload=payload,
                    paid_total_amount=paid_total_amount or int(charge_order["total_amount"]),
                    memo_prefix="충전 결제",
                )
                conn.execute(
                    "UPDATE payment_webhooks SET status = 'processed', processed_at = ?, updated_at = ? WHERE id = ?",
                    (timestamp, timestamp, webhook_id),
                )
                conn.commit()
                result_payload.update({"status": "processed", **result})
                return result_payload

            mapped_status = {
                "failed": "failed",
                "cancelled": "cancelled",
                "canceled": "cancelled",
                "expired": "expired",
                "refund_requested": "refund_requested",
                "refunded": "refunded",
            }.get(status, "")
            if mapped_status:
                conn.execute(
                    "UPDATE charge_orders SET status = ?, failure_reason = ?, updated_at = ? WHERE id = ?",
                    (mapped_status, reference or str(payload.get("failureReason") or ""), timestamp, charge_order["id"]),
                )
            conn.execute(
                "UPDATE payment_webhooks SET status = 'processed', processed_at = ?, updated_at = ? WHERE id = ?",
                (timestamp, timestamp, webhook_id),
            )
            conn.commit()
            result_payload["status"] = "processed"
            return result_payload

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

    def _analytics_page_label(self, conn: DatabaseConnection, route: str) -> str:
        normalized = normalize_analytics_route(route)
        if normalized == "/":
            return "홈"
        if normalized == "/products":
            return "상품 목록"
        if normalized == "/help":
            return "도움말 허브"
        if normalized == "/auth":
            return "로그인 / 회원가입"
        if normalized == "/charge":
            return "충전"
        if normalized == "/orders":
            return "주문 내역"
        if normalized == "/my":
            return "마이 페이지"
        if normalized == "/legal/terms":
            return "이용약관"
        if normalized == "/legal/privacy":
            return "개인정보처리방침"
        if normalized == "/legal/marketing":
            return "마케팅 수신 동의"
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

    def _admin_analytics_payload(self, conn: DatabaseConnection) -> Dict[str, Any]:
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
            platform_section_rows = conn.execute(
                """
                SELECT
                    ps.*,
                    COUNT(DISTINCT pg.id) AS group_count,
                    COUNT(DISTINCT pc.id) AS category_count,
                    COUNT(DISTINCT p.id) AS product_count
                FROM platform_sections ps
                LEFT JOIN platform_groups pg ON pg.platform_section_id = ps.id
                LEFT JOIN product_categories pc ON pc.platform_group_id = pg.id
                LEFT JOIN products p ON p.product_category_id = pc.id
                GROUP BY ps.id
                ORDER BY ps.sort_order, ps.display_name
                """
            ).fetchall()
            supplier_rows = conn.execute(
                """
                SELECT
                    s.*,
                    COUNT(DISTINCT CASE WHEN ss.is_active = 1 THEN ss.id END) AS service_count,
                    COUNT(DISTINCT CASE WHEN ss.is_active = 0 THEN ss.id END) AS inactive_service_count,
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
                    "apiKeyMasked": safe_mask_secret(row["api_key"]),
                    "hasBearerToken": bool(row["bearer_token"]),
                    "bearerTokenMasked": safe_mask_secret(row["bearer_token"]),
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
                    "serviceSyncStatus": row["service_sync_status"],
                    "serviceSyncMessage": row["service_sync_message"],
                    "serviceSyncStartedAt": row["service_sync_started_at"],
                    "serviceSyncCompletedAt": row["service_sync_completed_at"],
                    "serviceSyncLockUntil": row["service_sync_lock_until"],
                    "serviceSyncErrorCount": row["service_sync_error_count"],
                    "serviceSyncIntervalMinutes": row["service_sync_interval_minutes"],
                    "healthStatus": row.get("health_status") or "unknown",
                    "healthMessage": row.get("health_message") or "",
                    "healthCheckedAt": row.get("health_checked_at") or "",
                    "balanceStatus": row.get("balance_status") or "unknown",
                    "balanceCheckedAt": row.get("balance_checked_at") or "",
                    "serviceCount": row["service_count"],
                    "inactiveServiceCount": row["inactive_service_count"],
                    "mappingCount": row["mapping_count"],
                    "autoDispatchReadiness": supplier_auto_dispatch_readiness_payload(row),
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
                for row in supplier_rows
            ]

            platform_sections = [
                {
                    "id": row["id"],
                    "slug": row["slug"],
                    "displayName": row["display_name"],
                    "description": row["description"],
                    "icon": row["icon"],
                    "logoImageUrl": row["image_url"],
                    "accentColor": row["accent_color"],
                    "sortOrder": row["sort_order"],
                    "groupCount": row["group_count"],
                    "categoryCount": row["category_count"],
                    "productCount": row["product_count"],
                }
                for row in platform_section_rows
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
                    "avatarLabel": resolved_avatar_label(row["avatar_label"], row["name"]),
                    "balance": row["balance"],
                    "balanceLabel": money(row["balance"]),
                    "isActive": bool(row["is_active"]),
                    "accountStatus": row["account_status"],
                    "marketingOptIn": bool(row["marketing_opt_in"]),
                    "hasPassword": bool(row["password_hash"]),
                    "notes": row["notes"],
                    "lastLoginAt": row["last_login_at"],
                    "orderCount": row["order_count"],
                    "totalSpent": row["total_spent"],
                    "totalSpentLabel": money(row["total_spent"]),
                    "lastOrderAt": row["last_order_at"] or "",
                    "lastOrderLabel": self._relative_date_label(row["last_order_at"]) if row["last_order_at"] else "",
                    "searchText": " ".join(
                        filter(
                            None,
                            [
                                str(row["name"] or ""),
                                str(row["email"] or ""),
                                str(row["phone"] or ""),
                                str(row["tier"] or ""),
                                str(row["role"] or ""),
                                str(row["notes"] or ""),
                            ],
                        )
                    ).lower(),
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
                GROUP BY
                    pc.id,
                    pg.id,
                    pg.name,
                    ps.id,
                    ps.display_name,
                    ps.sort_order,
                    pg.sort_order
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
                    "serviceDescriptionHtml": sanitize_rich_html(row["service_description_html"]),
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
                    so.id AS supplier_order_id,
                    so.status AS supplier_status,
                    so.supplier_external_order_id,
                    so.updated_at AS supplier_updated_at,
                    s.name AS supplier_name
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN platform_sections ps ON ps.id = o.platform_section_id
                LEFT JOIN supplier_orders so ON so.id = (
                    SELECT so2.id
                    FROM supplier_orders so2
                    WHERE so2.order_id = o.id
                    ORDER BY so2.created_at DESC
                    LIMIT 1
                )
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
                    "orderChannel": row["order_channel"] or ORDER_CHANNEL_WEB,
                    "orderChannelLabel": order_channel_label(row["order_channel"] or ORDER_CHANNEL_WEB),
                    "externalOrderId": row["external_order_id"] or "",
                    "externalOrderItemId": row["external_order_item_id"] or "",
                    "dispatchStatus": row["dispatch_status"] or ORDER_DISPATCH_UNMAPPED,
                    "dispatchAttempts": int(row["dispatch_attempts"] or 0),
                    "supplierLastError": row["supplier_last_error"] or "",
                    "notes": parse_json(row["notes_json"], {}),
                    "supplierStatus": row["supplier_status"] or "",
                    "supplierOrderId": row["supplier_order_id"] or "",
                    "supplierName": row["supplier_name"] or "",
                    "supplierExternalOrderId": row["supplier_external_order_id"] or "",
                    "supplierUpdatedAt": row["supplier_updated_at"] or "",
                    "supplierDispatchLabel": (
                        "발주 성공"
                        if row["supplier_external_order_id"]
                        else "발주 실패"
                        if row["supplier_status"] == "failed"
                        else "전송 대기"
                        if row["supplier_name"]
                        else "공급사 미연결"
                    ),
                    "searchText": " ".join(
                        filter(
                            None,
                            [
                                str(row["order_number"] or ""),
                                str(row["customer_name"] or ""),
                                str(row["customer_email"] or ""),
                                str(row["product_name_snapshot"] or ""),
                                str(row["option_name_snapshot"] or ""),
                                str(row["target_value"] or ""),
                                str(row["order_channel"] or ""),
                                str(row["external_order_id"] or ""),
                                str(row["external_order_item_id"] or ""),
                                str(row["dispatch_status"] or ""),
                                str(row["supplier_last_error"] or ""),
                                str((parse_json(row["notes_json"], {}) or {}).get("memo") or ""),
                                str((parse_json(row["notes_json"], {}) or {}).get("adminMemo") or ""),
                                str(row["supplier_name"] or ""),
                                str(row["supplier_status"] or ""),
                                str(row["supplier_external_order_id"] or ""),
                            ],
                        )
                    ).lower(),
                    "createdAt": row["created_at"],
                    "createdLabel": self._relative_date_label(row["created_at"]),
                }
                for row in admin_order_rows
            ]

            admin_charge_rows = conn.execute(
                """
                SELECT
                    co.*,
                    u.name AS customer_name,
                    u.email AS customer_email
                FROM charge_orders co
                JOIN users u ON u.id = co.user_id
                ORDER BY co.created_at DESC
                LIMIT 100
                """
            ).fetchall()
            admin_charge_orders = [self._admin_charge_order_payload(row) for row in admin_charge_rows]
            cafe24_integration_rows = conn.execute(
                "SELECT * FROM cafe24_integrations ORDER BY is_active DESC, mall_id, shop_no"
            ).fetchall()
            cafe24_mapping_rows = conn.execute(
                """
                SELECT
                    cm.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name,
                    s.name AS supplier_name,
                    ss.name AS supplier_service_name,
                    ss.external_service_id AS supplier_service_external_id
                FROM cafe24_supplier_mappings cm
                LEFT JOIN products p ON p.id = cm.internal_product_id
                LEFT JOIN suppliers s ON s.id = cm.supplier_id
                LEFT JOIN supplier_services ss ON ss.id = cm.supplier_service_id
                ORDER BY cm.updated_at DESC
                LIMIT 200
                """
            ).fetchall()
            cafe24_order_rows = conn.execute(
                """
                SELECT
                    coi.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name
                FROM cafe24_order_items coi
                LEFT JOIN products p ON p.id = coi.product_id
                ORDER BY coi.updated_at DESC
                LIMIT 200
                """
            ).fetchall()
            cafe24_integrations = [self._cafe24_integration_payload(row) for row in cafe24_integration_rows]
            cafe24_product_mappings = [self._cafe24_mapping_payload(row) for row in cafe24_mapping_rows]
            cafe24_order_items = [self._cafe24_order_item_payload(row) for row in cafe24_order_rows]
            notice_rows = conn.execute("SELECT * FROM notices ORDER BY pinned DESC, published_at DESC, id").fetchall()
            faq_rows = conn.execute("SELECT * FROM faqs ORDER BY sort_order, id").fetchall()
            audit_rows = conn.execute(
                "SELECT * FROM admin_audit_logs ORDER BY created_at DESC LIMIT 80"
            ).fetchall()
            cafe24_flow_snapshot = parse_json(self._runtime_metadata_value(conn, "cafe24_flow.last_tick"), {})
            cafe24_flow_last_tick_at = self._runtime_metadata_value(conn, "cafe24_flow.last_tick_at")
            cafe24_flow_last_tick_status = self._runtime_metadata_value(conn, "cafe24_flow.last_tick_status")
            automation_snapshot = cafe24_flow_snapshot or parse_json(self._runtime_metadata_value(conn, "automation.last_tick"), {})
            automation_last_tick_at = cafe24_flow_last_tick_at or self._runtime_metadata_value(conn, "automation.last_tick_at")
            automation_last_tick_status = cafe24_flow_last_tick_status or self._runtime_metadata_value(conn, "automation.last_tick_status")
            automation_paused_value = self._runtime_metadata_value(conn, "automation.paused")

            mapped_product_count = sum(1 for item in internal_products if item["mapping"])
            total_service_count = sum(int(item["serviceCount"]) for item in suppliers)
            active_suppliers = sum(1 for item in suppliers if item["isActive"])
            active_customers = sum(1 for item in customers if item["isActive"] and item["role"] == "customer")
            active_products = sum(1 for item in internal_products if item["isActive"])
            analytics_overview = analytics.get("windows", {}).get("30d", {}).get("overview", {})
            pending_charge_count = sum(
                1
                for item in admin_charge_orders
                if item["status"] in {"created", "awaiting_payment", "awaiting_deposit", "refund_requested"}
            )

            return {
                "siteSettings": self._site_settings_admin_payload(site_settings_row),
                "popup": self._popup_admin_payload(popup_row) if popup_row else None,
                "homeBanners": [self._home_banner_payload(row) for row in banner_rows],
                "platformSections": platform_sections,
                "analytics": analytics,
                "suppliers": suppliers,
                "customers": customers,
                "platformGroups": platform_groups,
                "categories": categories,
                "internalProducts": internal_products,
                "adminOrders": admin_orders,
                "adminChargeOrders": admin_charge_orders,
                "cafe24Integrations": cafe24_integrations,
                "cafe24ProductMappings": cafe24_product_mappings,
                "cafe24OrderItems": cafe24_order_items,
                "notices": [self._notice_payload(row) for row in notice_rows],
                "faqs": [self._faq_payload(row) for row in faq_rows],
                "auditLogs": [self._admin_audit_payload(row) for row in audit_rows],
                "automation": {
                    "lastTick": automation_snapshot,
                    "lastTickAt": automation_last_tick_at,
                    "lastTickStatus": automation_last_tick_status or automation_snapshot.get("status") or "never",
                    "paused": automation_paused() or automation_paused_value == "1",
                },
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
                    "chargeOrderCount": len(admin_charge_orders),
                    "pendingChargeCount": pending_charge_count,
                    "cafe24IntegrationCount": len(cafe24_integrations),
                    "cafe24ReconnectRequiredCount": sum(1 for item in cafe24_integrations if item["tokenStatus"] == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED),
                    "cafe24WaitingInputCount": sum(1 for item in cafe24_order_items if item["standardStatus"] == "waiting_input"),
                    "cafe24FailedCount": sum(1 for item in cafe24_order_items if item["standardStatus"] == "failed"),
                    "visitorCount": int(analytics_overview.get("uniqueVisitors") or 0),
                    "salesTotal": int(analytics_overview.get("sales") or 0),
                },
            }

    def _cafe24_integration_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return cafe24_integration_payload_from_row(
            row,
            default_shop_no=CAFE24_DEFAULT_SHOP_NO,
            auto_poll_interval_minutes=CAFE24_AUTO_POLL_INTERVAL_MINUTES,
        )

    def _cafe24_next_auto_poll_at(self, row: Dict[str, Any]) -> str:
        return _cafe24_next_auto_poll_at(
            row,
            interval_minutes=CAFE24_AUTO_POLL_INTERVAL_MINUTES,
        )

    def _cafe24_auto_poll_due(self, row: Dict[str, Any], *, force: bool = False) -> bool:
        return _cafe24_auto_poll_due(
            row,
            force=force,
            interval_minutes=CAFE24_AUTO_POLL_INTERVAL_MINUTES,
        )

    def _cafe24_token_status(self, row: Dict[str, Any]) -> str:
        return _cafe24_token_status(row)

    def _cafe24_token_status_label(self, row: Dict[str, Any]) -> str:
        return _cafe24_token_status_label(row)

    def _cafe24_token_status_message(self, row: Dict[str, Any]) -> str:
        return _cafe24_token_status_message(row)

    def _cafe24_mapping_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return cafe24_mapping_payload_from_row(row, default_shop_no=CAFE24_DEFAULT_SHOP_NO)

    def _cafe24_order_item_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return cafe24_order_item_payload_from_row(row, default_shop_no=CAFE24_DEFAULT_SHOP_NO)

    def cafe24_operational_audit(self) -> Dict[str, Any]:
        with self._connect() as conn:
            return build_cafe24_operational_audit(
                conn,
                db_path=DB_PATH,
                runtime_mode=runtime_mode(),
                production_runtime=is_production_runtime(),
                token_status=self._cafe24_token_status,
                token_status_label=self._cafe24_token_status_label,
                token_status_message=self._cafe24_token_status_message,
            )

    def cafe24_mapping_gap_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            options = cafe24_mapping_gap_report_options(payload)
        except ValueError as exc:
            raise PanelError(str(exc), status=400) from exc
        integration_id = options["integrationId"]
        mall_id = options["mallId"]
        shop_no = options["shopNo"]
        include_product_details = options["includeProductDetails"]
        product_filter = options["productFilter"]
        limit = options["limit"]
        detail_fetch_limit = options["detailFetchLimit"]
        detail_api_timeout_seconds = options["detailApiTimeoutSeconds"]
        detail_api_max_attempts = options["detailApiMaxAttempts"]
        detail_api_budget_seconds = options["detailApiBudgetSeconds"]

        with self._connect() as conn:
            if integration_id:
                integration = self._cafe24_integration_row(conn, integration_id)
            elif mall_id:
                integration = conn.execute(
                    """
                    SELECT *
                    FROM cafe24_integrations
                    WHERE mall_id = ? AND shop_no = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (mall_id, shop_no),
                ).fetchone()
                if integration is None:
                    raise PanelError("Cafe24 연동 정보를 찾을 수 없습니다.", status=404)
            else:
                integration = self._cafe24_integration_row(conn, "")
            mall_id = str(integration["mall_id"])
            shop_no = int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO)

            where = [
                "coi.mall_id = ?",
                "coi.shop_no = ?",
                "coi.payment_gate_status = 'payment_confirmed'",
                "(coi.mapping_id = '' OR coi.mapping_id IS NULL)",
                "(coi.supplier_service_id = '' OR coi.supplier_service_id IS NULL)",
            ]
            params: List[Any] = [mall_id, shop_no]
            if product_filter:
                placeholders = ", ".join("?" for _ in product_filter)
                where.append(f"coi.cafe24_product_no IN ({placeholders})")
                params.extend(sorted(product_filter))
            rows = conn.execute(
                f"""
                SELECT
                    coi.id, coi.mall_id, coi.shop_no, coi.cafe24_order_id,
                    coi.cafe24_order_item_code, coi.cafe24_product_no,
                    coi.cafe24_variant_code, coi.cafe24_custom_product_code,
                    coi.standard_status, coi.payment_gate_status, coi.error_message,
                    coi.raw_payload_json, coi.last_synced_at, coi.updated_at, coi.created_at
                FROM cafe24_order_items coi
                WHERE {" AND ".join(where)}
                ORDER BY COALESCE(NULLIF(coi.last_synced_at, ''), coi.updated_at, coi.created_at) DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()

            items: List[Dict[str, Any]] = []
            product_nos: List[str] = []
            for row in rows:
                raw_payload = parse_json(row["raw_payload_json"], {})
                item = cafe24_mapping_gap_item_payload(row, raw_payload, default_shop_no=CAFE24_DEFAULT_SHOP_NO)
                product_no = item["productNo"]
                if product_no and product_no not in product_nos:
                    product_nos.append(product_no)
                items.append(item)

            product_details: Dict[str, Any] = {}
            warnings: List[str] = []
            detail_product_nos: List[str] = []
            detail_target_product_nos: List[str] = []
            detail_attempted_product_nos: List[str] = []
            if include_product_details and product_nos:
                self._require_cafe24_scope(integration, "mall.read_product", "Cafe24 미매핑 상품 상세 조회")
                def detail_api_call(
                    product_no: str,
                    label: str,
                    api_call: Any,
                    request_timeout_seconds: float,
                    max_attempts: int,
                ) -> Any:
                    return self._cafe24_call_with_token_retry(
                        conn,
                        integration,
                        api_call,
                        request_timeout_seconds=request_timeout_seconds,
                        max_attempts=max_attempts,
                    )

                detail_result = fetch_cafe24_mapping_gap_product_details(
                    product_nos,
                    detail_fetch_limit=detail_fetch_limit,
                    detail_api_timeout_seconds=detail_api_timeout_seconds,
                    detail_api_max_attempts=detail_api_max_attempts,
                    detail_api_budget_seconds=detail_api_budget_seconds,
                    api_call=detail_api_call,
                )
                product_details = detail_result["productDetails"]
                warnings.extend(detail_result["warnings"])
                detail_product_nos = detail_result["detailProductNos"]
                detail_target_product_nos = detail_result["detailTargetProductNos"]
                detail_attempted_product_nos = detail_result["detailAttemptedProductNos"]
                conn.commit()
            integration = self._latest_cafe24_integration_row(conn, integration)

        groups = summarize_cafe24_mapping_gaps(items)
        annotated_groups = annotate_cafe24_mapping_gap_groups(groups, product_details)
        return {
            "integration": {
                "id": integration["id"],
                "mallId": mall_id,
                "shopNo": shop_no,
                "tokenStatus": self._cafe24_token_status(integration),
                "tokenStatusLabel": self._cafe24_token_status_label(integration),
            },
            "summary": {
                "itemCount": len(items),
                "groupCount": len(annotated_groups),
                "manualInputRequiredGroupCount": sum(1 for group in annotated_groups if group.get("diagnostics", {}).get("manualInputRequired")),
                "mappingCandidateGroupCount": sum(1 for group in annotated_groups if group.get("diagnostics", {}).get("mappingCandidate")),
                "productNos": product_nos,
                "detailTargetProductNos": detail_target_product_nos,
                "detailAttemptedProductNos": detail_attempted_product_nos,
                "detailProductNos": detail_product_nos,
                "detailFetchLimit": detail_fetch_limit,
                "detailApiTimeoutSeconds": detail_api_timeout_seconds,
                "detailApiMaxAttempts": detail_api_max_attempts,
                "detailApiBudgetSeconds": detail_api_budget_seconds,
            },
            "groups": annotated_groups,
            "productDetails": product_details,
            "warnings": warnings,
            "checkedAt": now_iso(),
        }

    def _log_cafe24_event(
        self,
        conn: DatabaseConnection,
        *,
        mall_id: str,
        shop_no: int,
        event_type: str,
        status: str,
        request_payload: Any = None,
        response_payload: Any = None,
        error_message: str = "",
    ) -> None:
        conn.execute(
            """
            INSERT INTO cafe24_api_events (
                id, mall_id, shop_no, event_type, status, request_json, response_json, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"cafe24_evt_{uuid4().hex[:16]}",
                mall_id,
                int(shop_no or CAFE24_DEFAULT_SHOP_NO),
                event_type,
                status,
                as_json(redact_external_payload(request_payload or {})),
                as_json(redact_external_payload(response_payload or {})),
                str(error_message or "")[:1000],
                now_iso(),
            ),
        )

    def list_cafe24_order_items(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        options = cafe24_order_item_list_options(payload)
        page = int(options["page"])
        page_size = int(options["pageSize"])
        window = options["window"]
        with self._connect() as conn:
            integration = self._cafe24_integration_row(conn, options["integrationId"]) if options["integrationId"] else None
            clauses = cafe24_order_item_filter_clauses(options, integration=integration)
            total_row = conn.execute(
                f"SELECT COUNT(*) AS total_count FROM cafe24_order_items coi WHERE {clauses['whereSql']}",
                clauses["params"],
            ).fetchone()
            total = int((total_row or {}).get("total_count") or 0)
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""
                SELECT
                    coi.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name
                FROM cafe24_order_items coi
                LEFT JOIN products p ON p.id = coi.product_id
                WHERE {clauses['whereSql']}
                ORDER BY {CAFE24_ORDER_ITEM_DATE_EXPR} DESC, coi.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*clauses["params"], page_size, offset],
            ).fetchall()
            summary_row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN coi.payment_gate_status = 'payment_confirmed' THEN 1 ELSE 0 END) AS payment_confirmed_count,
                    SUM(CASE WHEN coi.payment_gate_status = 'payment_confirmed'
                        AND coi.mapping_id = '' AND coi.supplier_service_id = '' AND coi.product_id = ''
                        THEN 1 ELSE 0 END) AS unmapped_count,
                    SUM(CASE WHEN coi.standard_status IN (
                        'waiting_input', 'mapping_error', 'field_extract_failed', 'missing_required_field',
                        'invalid_quantity', 'invalid_target', 'supplier_range_error', 'needs_manual_review',
                        'payment_review_required'
                    ) THEN 1 ELSE 0 END) AS review_required_count,
                    SUM(CASE WHEN coi.payment_gate_status = 'payment_confirmed'
                        AND coi.supplier_order_uuid = ''
                        AND coi.standard_status IN (
                            'waiting_input', 'mapping_error', 'missing_required_field',
                            'invalid_quantity', 'invalid_target', 'supplier_range_error', 'needs_manual_review'
                        )
                        THEN 1 ELSE 0 END) AS manual_input_required_count,
                    SUM(CASE WHEN coi.standard_status = 'ready_to_submit'
                        AND coi.payment_gate_status = 'payment_confirmed'
                        AND coi.supplier_order_uuid = ''
                        THEN 1 ELSE 0 END) AS ready_to_submit_count,
                    SUM(CASE WHEN coi.standard_status = 'failed' THEN 1 ELSE 0 END) AS failed_count
                FROM cafe24_order_items coi
                WHERE {clauses['summaryWhereSql']}
                """,
                clauses["summaryParams"],
            ).fetchone()
        return {
            "items": [self._cafe24_order_item_payload(row) for row in rows],
            "orderItems": [self._cafe24_order_item_payload(row) for row in rows],
            "summary": cafe24_order_item_summary_payload(summary_row),
            "pagination": cafe24_order_item_pagination_payload(
                page=page,
                page_size=page_size,
                total=total,
                window=window,
            ),
            "filters": {
                "payment": options["paymentFilter"] or "all",
                "mapping": options["mappingFilter"] or "all",
                "status": options["statusFilter"] or "all",
                "search": options["search"],
            },
        }

    def create_cafe24_oauth_authorize_url(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mall_id = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("mallId") or "").strip())
        shop_no = normalize_cafe24_shop_no(payload.get("shopNo"))
        redirect_uri = str(payload.get("redirectUri") or cafe24_redirect_uri()).strip()
        scopes = normalize_cafe24_scopes(payload.get("scopes"))
        actor = self._admin_actor(payload)
        if not mall_id:
            raise PanelError("Cafe24 Mall ID를 입력해 주세요.")
        if not redirect_uri:
            raise PanelError("Cafe24 OAuth redirect URI를 확인할 수 없습니다.")
        client_id = cafe24_client_id()
        if not client_id or not cafe24_client_secret():
            raise PanelError("SMM_PANEL_CAFE24_CLIENT_ID / SMM_PANEL_CAFE24_CLIENT_SECRET 환경변수가 필요합니다.", status=503)
        state = secrets.token_urlsafe(32)
        created_at = now_iso()
        expires_at = (dt.datetime.now().astimezone() + dt.timedelta(seconds=CAFE24_OAUTH_STATE_TTL_SECONDS)).isoformat()
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM cafe24_oauth_states WHERE expires_at < ? OR used_at != ''",
                (created_at,),
            )
            conn.execute(
                """
                INSERT INTO cafe24_oauth_states (
                    state, mall_id, shop_no, scopes_json, redirect_uri, actor, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (state, mall_id, shop_no, as_json(scopes), redirect_uri, actor, created_at, expires_at),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.oauth_start",
                entity_type="cafe24_integration",
                entity_id=f"{mall_id}:{shop_no}",
                message=f"Cafe24 OAuth 승인 시작: {mall_id} / {shop_no}",
                metadata={"scopes": scopes, "redirectUri": redirect_uri},
            )
            conn.commit()
        authorize_params = {
            "response_type": "code",
            "client_id": client_id,
            "state": state,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
        }
        authorize_url = f"{cafe24_api_base_url(mall_id)}/oauth/authorize?{urlencode(authorize_params)}"
        return {
            "authorizeUrl": authorize_url,
            "state": state,
            "expiresAt": expires_at,
            "redirectUri": redirect_uri,
            "scopes": scopes,
        }

    def complete_cafe24_oauth_callback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = str(payload.get("state") or "").strip()
        code = str(payload.get("code") or "").strip()
        if not state or not code:
            raise PanelError("Cafe24 OAuth state/code가 없습니다.", status=400)
        with self._connect() as conn:
            state_row = conn.execute("SELECT * FROM cafe24_oauth_states WHERE state = ?", (state,)).fetchone()
        if state_row is None:
            raise PanelError("Cafe24 OAuth 요청을 찾을 수 없습니다. 관리자에서 다시 연결을 시작해 주세요.", status=400)
        if str(state_row["used_at"] or ""):
            raise PanelError("이미 사용된 Cafe24 OAuth 요청입니다. 관리자에서 다시 연결을 시작해 주세요.", status=400)
        try:
            expires_at = dt.datetime.fromisoformat(str(state_row["expires_at"]))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        except ValueError:
            expires_at = dt.datetime.now().astimezone() - dt.timedelta(seconds=1)
        if expires_at < dt.datetime.now().astimezone():
            raise PanelError("Cafe24 OAuth 승인 시간이 만료되었습니다. 관리자에서 다시 연결을 시작해 주세요.", status=400)

        mall_id = str(state_row["mall_id"] or "").strip()
        shop_no = normalize_cafe24_shop_no(state_row["shop_no"])
        redirect_uri = str(state_row["redirect_uri"] or "").strip()
        actor = str(state_row["actor"] or "admin")
        token_payload = Cafe24ApiClient.exchange_authorization_code(mall_id, code, redirect_uri)
        token_scopes = token_payload.get("scopes") or token_payload.get("scope") or parse_json(state_row["scopes_json"], list(CAFE24_DEFAULT_SCOPES))
        expires_at_value = str(
            token_payload.get("expires_at")
            or token_payload.get("access_token_expires_at")
            or cafe24_oauth_timestamp_from_response(token_payload, "expires_at", "expires_in")
            or ""
        ).strip()
        refresh_expires_at_value = str(
            token_payload.get("refresh_token_expires_at")
            or cafe24_oauth_timestamp_from_response(token_payload, "refresh_token_expires_at", "refresh_token_expires_in")
            or ""
        ).strip()
        result = self.save_cafe24_integration(
            {
                "mallId": mall_id,
                "shopNo": shop_no,
                "accessToken": token_payload.get("access_token"),
                "refreshToken": token_payload.get("refresh_token"),
                "expiresAt": expires_at_value,
                "refreshTokenExpiresAt": refresh_expires_at_value,
                "scopes": token_scopes,
                "autoSubmit": False,
                "isActive": True,
                "_adminActor": actor,
            }
        )
        with self._connect() as conn:
            timestamp = now_iso()
            conn.execute("UPDATE cafe24_oauth_states SET used_at = ? WHERE state = ?", (timestamp, state))
            self._log_cafe24_event(
                conn,
                mall_id=mall_id,
                shop_no=shop_no,
                event_type="oauth_callback",
                status="success",
                request_payload={"state": state, "redirectUri": redirect_uri},
                response_payload=token_payload,
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.oauth_complete",
                entity_type="cafe24_integration",
                entity_id=result["integration"]["id"],
                message=f"Cafe24 OAuth 토큰 저장 완료: {mall_id} / {shop_no}",
            )
            conn.commit()
        return result

    def save_cafe24_integration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        integration_id = str(payload.get("id") or "").strip()
        mall_id = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("mallId") or "").strip())
        shop_no = normalize_cafe24_shop_no(payload.get("shopNo"))
        access_token = str(payload.get("accessToken") or "").strip()
        refresh_token = str(payload.get("refreshToken") or "").strip()
        scopes = normalize_cafe24_scopes(payload.get("scopes"))
        expires_at = str(payload.get("expiresAt") or "").strip()
        refresh_expires_at = str(payload.get("refreshTokenExpiresAt") or "").strip()
        auto_submit = 1 if payload.get("autoSubmit", False) else 0
        completion_policy = str(payload.get("completionPolicy") or "memo_only").strip() or "memo_only"
        is_active = 1 if payload.get("isActive", True) else 0
        actor = self._admin_actor(payload)
        if not mall_id:
            raise PanelError("Cafe24 mall_id를 입력해 주세요.")
        with self._connect() as conn:
            existing = None
            if integration_id:
                existing = conn.execute("SELECT * FROM cafe24_integrations WHERE id = ?", (integration_id,)).fetchone()
                if existing is None:
                    raise PanelError("Cafe24 연동 정보를 찾을 수 없습니다.", status=404)
            else:
                existing = conn.execute(
                    "SELECT * FROM cafe24_integrations WHERE mall_id = ? AND shop_no = ?",
                    (mall_id, shop_no),
                ).fetchone()
            timestamp = now_iso()
            stored_access_token = encrypt_secret_value(
                access_token or (decrypt_secret_value(existing["access_token"]) if existing else ""),
                require_key=_secret_encryption_required(),
            )
            stored_refresh_token = encrypt_secret_value(
                refresh_token or (decrypt_secret_value(existing["refresh_token"]) if existing else ""),
                require_key=_secret_encryption_required(),
            )
            tokens_updated = bool(access_token or refresh_token or not existing)
            tokens_available = bool(stored_access_token and stored_refresh_token)
            next_token_status = (
                CAFE24_TOKEN_STATUS_CONNECTED
                if tokens_available
                else CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED
            )
            next_reconnect_required_at = "" if tokens_available else timestamp
            next_reconnect_reason = "" if tokens_available else "Cafe24 OAuth 토큰을 연결해야 합니다."
            if existing and not tokens_updated:
                next_token_status = str(existing.get("token_status") or next_token_status)
                next_reconnect_required_at = str(existing.get("reconnect_required_at") or "")
                next_reconnect_reason = str(existing.get("reconnect_reason") or "")
            token_last_refreshed_at = (
                timestamp
                if access_token or refresh_token
                else (str(existing.get("token_last_refreshed_at") or "") if existing else "")
            )
            if existing:
                integration_id = existing["id"]
                conn.execute(
                    """
                    UPDATE cafe24_integrations
                    SET mall_id = ?, shop_no = ?, scopes_json = ?, access_token = ?, refresh_token = ?,
                        expires_at = ?, refresh_token_expires_at = ?, auto_submit = ?, completion_policy = ?,
                        token_status = ?, token_last_checked_at = ?, token_last_refreshed_at = ?,
                        token_refresh_lock_until = ?, token_refresh_lock_owner = ?,
                        reconnect_required_at = ?, reconnect_reason = ?, is_active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        mall_id,
                        shop_no,
                        as_json(scopes),
                        stored_access_token,
                        stored_refresh_token,
                        expires_at or existing["expires_at"],
                        refresh_expires_at or existing["refresh_token_expires_at"],
                        auto_submit,
                        completion_policy,
                        next_token_status,
                        timestamp,
                        token_last_refreshed_at,
                        "",
                        "",
                        next_reconnect_required_at,
                        next_reconnect_reason,
                        is_active,
                        timestamp,
                        integration_id,
                    ),
                )
                action = "updated"
            else:
                integration_id = f"cafe24_{uuid4().hex[:14]}"
                conn.execute(
                    """
                    INSERT INTO cafe24_integrations (
                        id, mall_id, shop_no, scopes_json, access_token, refresh_token,
                        expires_at, refresh_token_expires_at, auto_submit, completion_policy,
                        token_status, token_last_checked_at, token_last_refreshed_at,
                        token_refresh_lock_until, token_refresh_lock_owner,
                        reconnect_required_at, reconnect_reason, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        integration_id,
                        mall_id,
                        shop_no,
                        as_json(scopes),
                        stored_access_token,
                        stored_refresh_token,
                        expires_at,
                        refresh_expires_at,
                        auto_submit,
                        completion_policy,
                        next_token_status,
                        timestamp,
                        token_last_refreshed_at,
                        "",
                        "",
                        next_reconnect_required_at,
                        next_reconnect_reason,
                        is_active,
                        timestamp,
                        timestamp,
                    ),
                )
                action = "created"
            self._record_admin_audit(
                conn,
                actor=actor,
                action=f"cafe24.integration_{action}",
                entity_type="cafe24_integration",
                entity_id=integration_id,
                message=f"Cafe24 연동 {action}: {mall_id} / {shop_no}",
            )
            conn.commit()
            row = conn.execute("SELECT * FROM cafe24_integrations WHERE id = ?", (integration_id,)).fetchone()
        return {"integration": self._cafe24_integration_payload(row)}

    def save_cafe24_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mapping_id = str(payload.get("id") or "").strip()
        mall_id = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("mallId") or "").strip())
        shop_no = normalize_cafe24_shop_no(payload.get("shopNo"))
        product_no = sanitize_external_order_reference(payload.get("cafe24ProductNo"))
        variant_code = sanitize_external_order_reference(payload.get("cafe24VariantCode"))
        custom_product_code = sanitize_external_order_reference(payload.get("cafe24CustomProductCode"))
        internal_product_id = str(payload.get("internalProductId") or "").strip()
        supplier_id = str(payload.get("supplierId") or "").strip()
        supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
        supplier_product_uuid = sanitize_external_order_reference(payload.get("supplierProductUuid"))
        supplier_product_code = sanitize_external_order_reference(payload.get("supplierProductCode"))
        field_mapping_raw = payload.get("fieldMappingJson")
        field_mapping = parse_json(str(field_mapping_raw or "{}"), {}) if isinstance(field_mapping_raw, str) else payload.get("fieldMapping") or {}
        auto_dispatch_enabled = 1 if payload.get("autoDispatchEnabled", False) else 0
        enabled = 1 if payload.get("enabled", True) else 0
        actor = self._admin_actor(payload)
        if not mall_id:
            raise PanelError("Cafe24 mall_id를 입력해 주세요.")
        if not any([product_no, variant_code, custom_product_code]):
            raise PanelError("Cafe24 상품번호, 품목코드, 자체상품코드 중 하나 이상이 필요합니다.")
        if not supplier_id:
            raise PanelError("Cafe24 상품에 연결할 공급사를 선택해 주세요.")
        if not supplier_service_id and not supplier_product_uuid and not supplier_product_code:
            raise PanelError("공급사 서비스를 선택하거나 공급사 상품 코드를 입력해 주세요.")
        with self._connect() as conn:
            if internal_product_id:
                product = conn.execute("SELECT id FROM products WHERE id = ?", (internal_product_id,)).fetchone()
                if product is None:
                    raise PanelError("내부 상품을 찾을 수 없습니다.", status=404)
            supplier = conn.execute("SELECT id, is_active FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
            if supplier is None:
                raise PanelError("공급사를 찾을 수 없습니다.", status=404)
            if not bool(supplier["is_active"]):
                raise PanelError("비활성 공급사는 Cafe24 매핑에 사용할 수 없습니다.")
            supplier_service = None
            supplier_external_service_id = supplier_product_uuid or supplier_product_code
            if supplier_service_id:
                supplier_service = conn.execute(
                    "SELECT id, external_service_id FROM supplier_services WHERE id = ? AND supplier_id = ? AND is_active = 1",
                    (supplier_service_id, supplier_id),
                ).fetchone()
                if supplier_service is None:
                    raise PanelError("선택한 공급사 서비스를 찾을 수 없습니다.", status=404)
                supplier_external_service_id = str(supplier_service["external_service_id"] or "")
                supplier_product_uuid = supplier_product_uuid or supplier_external_service_id
            existing = conn.execute("SELECT * FROM cafe24_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone() if mapping_id else None
            if existing is None:
                existing = conn.execute(
                    """
                    SELECT *
                    FROM cafe24_supplier_mappings
                    WHERE mall_id = ? AND shop_no = ? AND cafe24_product_no = ?
                      AND cafe24_variant_code = ? AND cafe24_custom_product_code = ?
                    """,
                    (mall_id, shop_no, product_no, variant_code, custom_product_code),
                ).fetchone()
                if existing is not None:
                    mapping_id = existing["id"]
            timestamp = now_iso()
            if existing:
                conn.execute(
                    """
                    UPDATE cafe24_supplier_mappings
                    SET mall_id = ?, shop_no = ?, cafe24_product_no = ?, cafe24_variant_code = ?,
                        cafe24_custom_product_code = ?, internal_product_id = ?, supplier_id = ?,
                        supplier_service_id = ?, supplier_external_service_id = ?, supplier_product_uuid = ?,
                        supplier_product_code = ?, field_mapping_json = ?, auto_dispatch_enabled = ?,
                        enabled = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        mall_id,
                        shop_no,
                        product_no,
                        variant_code,
                        custom_product_code,
                        internal_product_id,
                        supplier_id,
                        supplier_service_id,
                        supplier_external_service_id,
                        supplier_product_uuid,
                        supplier_product_code,
                        as_json(field_mapping),
                        auto_dispatch_enabled,
                        enabled,
                        timestamp,
                        mapping_id,
                    ),
                )
            else:
                mapping_id = f"cafe24_smap_{uuid4().hex[:14]}"
                conn.execute(
                    """
                    INSERT INTO cafe24_supplier_mappings (
                        id, mall_id, shop_no, cafe24_product_no, cafe24_variant_code,
                        cafe24_custom_product_code, internal_product_id, supplier_id,
                        supplier_service_id, supplier_external_service_id, supplier_product_uuid,
                        supplier_product_code, field_mapping_json, auto_dispatch_enabled,
                        enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mapping_id,
                        mall_id,
                        shop_no,
                        product_no,
                        variant_code,
                        custom_product_code,
                        internal_product_id,
                        supplier_id,
                        supplier_service_id,
                        supplier_external_service_id,
                        supplier_product_uuid,
                        supplier_product_code,
                        as_json(field_mapping),
                        auto_dispatch_enabled,
                        enabled,
                        timestamp,
                        timestamp,
                    ),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.mapping_save",
                entity_type="cafe24_supplier_mapping",
                entity_id=mapping_id,
                message=f"Cafe24 공급사 매핑 저장: {mall_id}/{shop_no}",
                metadata={
                    "productNo": product_no,
                    "variantCode": variant_code,
                    "customProductCode": custom_product_code,
                    "supplierId": supplier_id,
                    "supplierServiceId": supplier_service_id,
                },
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT
                    cm.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name,
                    s.name AS supplier_name,
                    ss.name AS supplier_service_name,
                    ss.external_service_id AS supplier_service_external_id
                FROM cafe24_supplier_mappings cm
                LEFT JOIN products p ON p.id = cm.internal_product_id
                LEFT JOIN suppliers s ON s.id = cm.supplier_id
                LEFT JOIN supplier_services ss ON ss.id = cm.supplier_service_id
                WHERE cm.id = ?
                """,
                (mapping_id,),
            ).fetchone()
        return {"mapping": self._cafe24_mapping_payload(row)}

    def preview_cafe24_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        field_mapping_raw = payload.get("fieldMappingJson")
        field_mapping = parse_json(str(field_mapping_raw or "{}"), {}) if isinstance(field_mapping_raw, str) else payload.get("fieldMapping") or {}
        sample_item_id = str(payload.get("sampleOrderItemId") or payload.get("itemId") or "").strip()
        internal_product_id = str(payload.get("internalProductId") or "").strip()
        supplier_id = str(payload.get("supplierId") or "").strip()
        supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
        supplier_product_uuid = sanitize_external_order_reference(payload.get("supplierProductUuid"))
        supplier_product_code = sanitize_external_order_reference(payload.get("supplierProductCode"))

        errors: List[str] = []
        normalized_fields: Dict[str, Any] = {}
        supplier_payload: Dict[str, Any] = {}
        raw_payload: Dict[str, Any] = {}
        order_payload: Dict[str, Any] = {}
        item_payload: Dict[str, Any] = {}
        buyer: Dict[str, Any] = {}
        receiver: Dict[str, Any] = {}
        product: Optional[Dict[str, Any]] = None
        mapping: Dict[str, Any] = {
            "id": "preview",
            "internal_product_id": internal_product_id,
            "supplier_id": supplier_id,
            "supplier_service_id": supplier_service_id,
            "supplier_external_service_id": supplier_product_uuid or supplier_product_code,
            "supplier_product_uuid": supplier_product_uuid,
            "supplier_product_code": supplier_product_code,
            "field_mapping_json": as_json(field_mapping),
            "supplier_min_amount": 0,
            "supplier_max_amount": 0,
            "supplier_service_raw_json": "{}",
        }

        with self._connect() as conn:
            if sample_item_id:
                sample = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (sample_item_id,)).fetchone()
                if sample is None:
                    raise PanelError("샘플 Cafe24 주문상품을 찾을 수 없습니다.", status=404)
                raw_payload = parse_json(sample["raw_payload_json"], {})
                order_payload = raw_payload.get("order") if isinstance(raw_payload.get("order"), dict) else {}
                item_payload = raw_payload.get("item") if isinstance(raw_payload.get("item"), dict) else {}
                buyer = raw_payload.get("buyer") if isinstance(raw_payload.get("buyer"), dict) else {}
                receiver = raw_payload.get("receiver") if isinstance(raw_payload.get("receiver"), dict) else {}
            else:
                raw_payload = payload.get("rawPayload") if isinstance(payload.get("rawPayload"), dict) else {}
                order_payload = raw_payload.get("order") if isinstance(raw_payload.get("order"), dict) else {}
                item_payload = raw_payload.get("item") if isinstance(raw_payload.get("item"), dict) else {
                    "product_no": payload.get("cafe24ProductNo"),
                    "variant_code": payload.get("cafe24VariantCode"),
                    "custom_product_code": payload.get("cafe24CustomProductCode"),
                }
                buyer = raw_payload.get("buyer") if isinstance(raw_payload.get("buyer"), dict) else {}
                receiver = raw_payload.get("receiver") if isinstance(raw_payload.get("receiver"), dict) else {}

            if supplier_id:
                supplier = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
                if supplier is None:
                    errors.append("공급사를 찾을 수 없습니다.")
                else:
                    mapping.update(
                        {
                            "api_url": supplier["api_url"],
                            "integration_type": supplier["integration_type"],
                            "api_key": supplier["api_key"],
                            "bearer_token": supplier["bearer_token"],
                            "supplier_name": supplier["name"],
                            "supplier_is_active": supplier["is_active"],
                        }
                    )
            if supplier_service_id:
                supplier_service = conn.execute("SELECT * FROM supplier_services WHERE id = ?", (supplier_service_id,)).fetchone()
                if supplier_service is None:
                    errors.append("공급사 서비스를 찾을 수 없습니다.")
                else:
                    mapping.update(
                        {
                            "supplier_service_id": supplier_service["id"],
                            "supplier_external_service_id": supplier_service["external_service_id"],
                            "supplier_product_uuid": supplier_product_uuid or supplier_service["external_service_id"],
                            "supplier_service_name": supplier_service["name"],
                            "supplier_service_raw_json": supplier_service["raw_json"] or "{}",
                            "supplier_min_amount": supplier_service["min_amount"],
                            "supplier_max_amount": supplier_service["max_amount"],
                        }
                    )
            if internal_product_id:
                product_row = conn.execute(
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
                    WHERE p.id = ?
                    """,
                    (internal_product_id,),
                ).fetchone()
                if product_row is None:
                    errors.append("내부 상품을 찾을 수 없습니다.")
                else:
                    product = dict(product_row)

        option_entries = cafe24_option_entries(order_payload, item_payload)
        quantity_candidates = cafe24_quantity_candidates_from_options(option_entries)
        try:
            if product is not None:
                normalized_fields = self._normalize_cafe24_item_fields(
                    product=product,
                    mapping=mapping,
                    order_payload=order_payload,
                    item_payload=item_payload,
                    buyer=buyer,
                    receiver=receiver,
                )
                form_structure = ensure_request_memo_form_structure(parse_json(product["form_structure_json"], {}), "추가 요청사항")
                self._validate_fields(normalized_fields, form_structure.get("schema", {}))
            else:
                normalized_fields = self._normalize_cafe24_direct_item_fields(
                    mapping=mapping,
                    order_payload=order_payload,
                    item_payload=item_payload,
                    buyer=buyer,
                    receiver=receiver,
                )
                self._validate_cafe24_direct_fields(normalized_fields, mapping)
            if supplier_id:
                supplier_payload = self._build_supplier_order_payload(
                    product
                    or {
                        "product_code": "",
                        "platform_slug": "",
                        "price_strategy": "unit",
                    },
                    normalized_fields,
                    mapping,
                )
        except PanelError as exc:
            errors.append(str(exc))

        return {
            "ok": not errors,
            "errors": errors,
            "normalizedFields": normalized_fields,
            "supplierPayload": supplier_payload,
            "optionEntries": option_entries,
            "quantityCandidates": quantity_candidates,
            "fieldMapping": field_mapping,
            "sampleOrderItemId": sample_item_id,
        }

    def preview_single_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        selector = cafe24_order_item_selector_for_panel(payload, default_shop_no=CAFE24_DEFAULT_SHOP_NO)
        expected_quantity = cafe24_expected_quantity_from_payload_for_panel(payload)

        with self._connect() as conn:
            item_id = cafe24_order_item_id_for_panel(conn, selector)
            item_row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if item_row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            mapping_id = str(item_row.get("mapping_id") or "").strip()
            mapping_row = None
            if mapping_id:
                mapping_row = conn.execute("SELECT * FROM cafe24_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone()

        if mapping_row is not None:
            preview = self.preview_cafe24_mapping(
                {
                    "sampleOrderItemId": item_id,
                    "internalProductId": mapping_row.get("internal_product_id") or "",
                    "supplierId": mapping_row.get("supplier_id") or "",
                    "supplierServiceId": mapping_row.get("supplier_service_id") or "",
                    "supplierProductUuid": mapping_row.get("supplier_product_uuid") or "",
                    "supplierProductCode": mapping_row.get("supplier_product_code") or "",
                    "fieldMappingJson": mapping_row.get("field_mapping_json") or "{}",
                }
            )
        else:
            normalized_fields = parse_json(item_row["normalized_fields_json"], {})
            supplier_payload = parse_json(item_row["supplier_payload_json"], {})
            if not supplier_payload:
                raise PanelError("Cafe24 매핑 또는 수동 보정 payload가 없어 preview할 수 없습니다.", status=409)
            preview = {
                "ok": True,
                "errors": [],
                "normalizedFields": normalized_fields,
                "supplierPayload": supplier_payload,
                "optionEntries": [],
                "quantityCandidates": [],
                "fieldMapping": {},
                "sampleOrderItemId": item_id,
            }

        item_payload = self._cafe24_order_item_payload(item_row)
        report = build_cafe24_mapping_preview_report(preview, expected_quantity=expected_quantity)
        return {
            "itemId": item_id,
            "identity": {
                "mallId": item_payload["mallId"],
                "shopNo": item_payload["shopNo"],
                "orderId": item_payload["orderId"],
                "orderItemCode": item_payload["orderItemCode"],
                "productNo": item_payload["productNo"],
                "variantCode": item_payload["variantCode"],
                "customProductCode": item_payload["customProductCode"],
            },
            "mappingId": mapping_id,
            "standardStatus": item_payload["standardStatus"],
            "paymentGateStatus": item_payload["paymentGateStatus"],
            "preview": report,
        }

    def delete_cafe24_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mapping_id = str(payload.get("mappingId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not mapping_id:
            raise PanelError("삭제할 Cafe24 매핑을 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cafe24_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone()
            if row is None:
                raise PanelError("Cafe24 매핑을 찾을 수 없습니다.", status=404)
            conn.execute("UPDATE cafe24_supplier_mappings SET enabled = 0, updated_at = ? WHERE id = ?", (now_iso(), mapping_id))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.mapping_disable",
                entity_type="cafe24_supplier_mapping",
                entity_id=mapping_id,
                message="Cafe24 상품 매핑 비활성화",
            )
            conn.commit()
        return {"ok": True, "mappingId": mapping_id}

    def _cafe24_integration_row(self, conn: DatabaseConnection, integration_id: str = "") -> Dict[str, Any]:
        if integration_id:
            row = conn.execute("SELECT * FROM cafe24_integrations WHERE id = ?", (integration_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM cafe24_integrations WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise PanelError("Cafe24 연동 정보를 찾을 수 없습니다.", status=404)
        return row

    def _require_cafe24_scope(self, row: Dict[str, Any], scope: str, action_label: str) -> None:
        scopes = normalize_cafe24_scopes(parse_json(row["scopes_json"], []))
        if scope not in scopes:
            raise PanelError(
                f"{action_label} 권한이 없습니다. Cafe24 OAuth를 {scope} 권한으로 다시 연결해 주세요.",
                status=403,
            )

    def _cafe24_api_panel_error(self, action_label: str, exc: Exception) -> PanelError:
        message = str(exc or "").strip() or "알 수 없는 Cafe24 API 오류"
        safe_message = message[:500]
        lowered = message.lower()
        if any(keyword in lowered for keyword in ("401", "unauthorized", "invalid token", "access token")):
            return PanelError(f"{action_label} 실패: Cafe24 OAuth 토큰을 다시 연결해 주세요.", status=409)
        if any(keyword in lowered for keyword in ("403", "forbidden", "scope", "permission", "권한")):
            return PanelError(f"{action_label} 실패: Cafe24 상품 읽기 권한을 확인해 주세요. mall.read_product 권한으로 다시 연결이 필요합니다.", status=403)
        return PanelError(f"{action_label} 실패: {safe_message}", status=502)

    def _cafe24_token_expiring(self, expires_at: str) -> bool:
        if not expires_at:
            return False
        try:
            expires = dt.datetime.fromisoformat(str(expires_at))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
            return expires <= dt.datetime.now().astimezone() + dt.timedelta(minutes=3)
        except ValueError:
            return False

    def _mark_cafe24_token_state(
        self,
        conn: DatabaseConnection,
        integration_id: str,
        *,
        status: str,
        message: str = "",
        reconnect_required: bool = False,
        clear_lock: bool = True,
    ) -> None:
        timestamp = now_iso()
        reconnect_at = timestamp if reconnect_required else ""
        lock_until = "" if clear_lock else None
        lock_owner = "" if clear_lock else None
        if clear_lock:
            conn.execute(
                """
                UPDATE cafe24_integrations
                SET token_status = ?, token_last_checked_at = ?, token_refresh_lock_until = ?,
                    token_refresh_lock_owner = ?, reconnect_required_at = ?, reconnect_reason = ?,
                    last_sync_status = CASE WHEN ? = 'failed' THEN 'failed' ELSE last_sync_status END,
                    last_sync_message = CASE WHEN ? != '' THEN ? ELSE last_sync_message END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    timestamp,
                    lock_until,
                    lock_owner,
                    reconnect_at,
                    str(message or "")[:1000],
                    status,
                    str(message or ""),
                    str(message or "")[:1000],
                    timestamp,
                    integration_id,
                ),
            )
            return
        conn.execute(
            """
            UPDATE cafe24_integrations
            SET token_status = ?, token_last_checked_at = ?, reconnect_required_at = ?,
                reconnect_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, timestamp, reconnect_at, str(message or "")[:1000], timestamp, integration_id),
        )

    def _acquire_cafe24_refresh_lock(self, conn: DatabaseConnection, integration_id: str) -> str:
        owner = f"refresh_{uuid4().hex[:16]}"
        timestamp = now_iso()
        lock_until = (dt.datetime.now().astimezone() + dt.timedelta(seconds=CAFE24_REFRESH_LOCK_SECONDS)).isoformat(timespec="seconds")
        cursor = conn.execute(
            """
            UPDATE cafe24_integrations
            SET token_status = ?, token_last_checked_at = ?, token_refresh_lock_owner = ?,
                token_refresh_lock_until = ?, updated_at = ?
            WHERE id = ?
              AND (
                token_refresh_lock_until = ''
                OR token_refresh_lock_until < ?
                OR token_refresh_lock_owner = ?
              )
            """,
            (
                CAFE24_TOKEN_STATUS_REFRESHING,
                timestamp,
                owner,
                lock_until,
                timestamp,
                integration_id,
                timestamp,
                owner,
            ),
        )
        return owner if cursor.rowcount == 1 else ""

    def _acquire_cafe24_poll_lock(self, conn: DatabaseConnection, integration_id: str) -> str:
        owner = f"poll_{uuid4().hex[:16]}"
        timestamp = now_iso()
        lock_until = (dt.datetime.now().astimezone() + dt.timedelta(seconds=CAFE24_POLL_LOCK_SECONDS)).isoformat(timespec="seconds")
        cursor = conn.execute(
            """
            UPDATE cafe24_integrations
            SET cafe24_poll_lock_owner = ?, cafe24_poll_lock_until = ?,
                last_auto_poll_status = ?, last_auto_poll_message = ?, updated_at = ?
            WHERE id = ?
              AND (
                cafe24_poll_lock_until = ''
                OR cafe24_poll_lock_until < ?
                OR cafe24_poll_lock_owner = ?
              )
            """,
            (
                owner,
                lock_until,
                "running",
                "자동 주문 수집 진행 중",
                timestamp,
                integration_id,
                timestamp,
                owner,
            ),
        )
        return owner if cursor.rowcount == 1 else ""

    def _release_cafe24_poll_lock(
        self,
        conn: DatabaseConnection,
        integration_id: str,
        owner: str,
        *,
        status: str,
        message: str,
        completed_at: Optional[str] = None,
    ) -> None:
        timestamp = completed_at or now_iso()
        conn.execute(
            """
            UPDATE cafe24_integrations
            SET cafe24_poll_lock_owner = ?, cafe24_poll_lock_until = ?,
                last_auto_poll_at = ?, last_auto_poll_status = ?,
                last_auto_poll_message = ?, updated_at = ?
            WHERE id = ? AND cafe24_poll_lock_owner = ?
            """,
            ("", "", timestamp, status, str(message or "")[:1000], timestamp, integration_id, owner),
        )

    def _cafe24_client_for_row(
        self,
        conn: DatabaseConnection,
        row: Dict[str, Any],
        *,
        force_refresh: bool = False,
    ) -> Cafe24ApiClient:
        mall_id = str(row["mall_id"])
        access_token = decrypt_secret_value(row["access_token"])
        refresh_token = decrypt_secret_value(row["refresh_token"])
        integration_id = str(row["id"])
        if not access_token or not refresh_token:
            message = "Cafe24 OAuth 토큰이 없습니다. 관리자에서 다시 연결해 주세요."
            self._mark_cafe24_token_state(
                conn,
                integration_id,
                status=CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED,
                message=message,
                reconnect_required=True,
            )
            conn.commit()
            raise PanelError(message, status=409)
        if cafe24_refresh_token_expired(row["refresh_token_expires_at"]):
            message = "Cafe24 refresh token이 만료되었습니다. OAuth 재연결이 필요합니다."
            self._mark_cafe24_token_state(
                conn,
                integration_id,
                status=CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED,
                message=message,
                reconnect_required=True,
            )
            conn.commit()
            raise PanelError(message, status=409)
        if refresh_token and (force_refresh or self._cafe24_token_expiring(str(row["expires_at"] or ""))):
            lock_owner = self._acquire_cafe24_refresh_lock(conn, integration_id)
            if not lock_owner:
                time.sleep(0.8)
                latest = conn.execute("SELECT * FROM cafe24_integrations WHERE id = ?", (integration_id,)).fetchone()
                if latest:
                    latest_access_token = decrypt_secret_value(latest["access_token"])
                    latest_token_is_usable = latest_access_token and not self._cafe24_token_expiring(str(latest["expires_at"] or ""))
                    latest_token_changed = latest_access_token and latest_access_token != access_token
                    if latest_token_is_usable and (not force_refresh or latest_token_changed):
                        return Cafe24ApiClient(
                            mall_id,
                            latest_access_token,
                            shop_no=int(latest["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                        )
                raise PanelError("Cafe24 토큰 갱신이 진행 중입니다. 잠시 후 다시 시도해 주세요.", status=409)
            conn.commit()
            try:
                refreshed = Cafe24ApiClient.refresh_access_token(mall_id, refresh_token)
            except Exception as exc:
                message = str(exc)
                next_status = (
                    CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED
                    if cafe24_refresh_error_requires_reconnect(message)
                    else CAFE24_TOKEN_STATUS_FAILED
                )
                self._mark_cafe24_token_state(
                    conn,
                    integration_id,
                    status=next_status,
                    message=message,
                    reconnect_required=next_status == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED,
                )
                conn.commit()
                raise PanelError(
                    "Cafe24 토큰 갱신에 실패했습니다. OAuth 재연결이 필요합니다."
                    if next_status == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED
                    else f"Cafe24 토큰 갱신에 실패했습니다: {message}",
                    status=409 if next_status == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED else 503,
                ) from exc
            access_token = str(refreshed.get("access_token") or "").strip()
            refresh_token = str(refreshed.get("refresh_token") or refresh_token).strip()
            scopes = normalize_cafe24_scopes(refreshed.get("scopes") or refreshed.get("scope") or parse_json(row["scopes_json"], []))
            refreshed_expires_at = (
                str(refreshed.get("expires_at") or refreshed.get("access_token_expires_at") or "").strip()
                or cafe24_oauth_timestamp_from_response(refreshed, "expires_at", "expires_in")
                or str(row["expires_at"] or "")
            )
            refreshed_refresh_expires_at = (
                str(refreshed.get("refresh_token_expires_at") or "").strip()
                or cafe24_oauth_timestamp_from_response(refreshed, "refresh_token_expires_at", "refresh_token_expires_in")
                or str(row["refresh_token_expires_at"] or "")
            )
            conn.execute(
                """
                UPDATE cafe24_integrations
                SET access_token = ?, refresh_token = ?, expires_at = ?, refresh_token_expires_at = ?,
                    scopes_json = ?, token_status = ?, token_last_checked_at = ?,
                    token_last_refreshed_at = ?, token_refresh_lock_until = ?,
                    token_refresh_lock_owner = ?, reconnect_required_at = ?, reconnect_reason = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    encrypt_secret_value(access_token, require_key=_secret_encryption_required()),
                    encrypt_secret_value(refresh_token, require_key=_secret_encryption_required()),
                    refreshed_expires_at,
                    refreshed_refresh_expires_at,
                    as_json(scopes or []),
                    CAFE24_TOKEN_STATUS_CONNECTED,
                    now_iso(),
                    now_iso(),
                    "",
                    "",
                    "",
                    "",
                    now_iso(),
                    row["id"],
                ),
            )
            conn.commit()
        elif cafe24_refresh_token_expiring_soon(row["refresh_token_expires_at"]):
            self._mark_cafe24_token_state(
                conn,
                integration_id,
                status=CAFE24_TOKEN_STATUS_EXPIRING,
                message="Cafe24 refresh token 만료가 임박했습니다.",
                clear_lock=False,
            )
        else:
            self._mark_cafe24_token_state(
                conn,
                integration_id,
                status=CAFE24_TOKEN_STATUS_CONNECTED,
                message="",
                clear_lock=False,
            )
        return Cafe24ApiClient(mall_id, access_token, shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO))

    def _latest_cafe24_integration_row(
        self,
        conn: DatabaseConnection,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        latest = conn.execute("SELECT * FROM cafe24_integrations WHERE id = ?", (row["id"],)).fetchone()
        return latest if latest is not None else row

    def _cafe24_call_with_token_retry(
        self,
        conn: DatabaseConnection,
        integration: Dict[str, Any],
        api_call: Any,
        *,
        request_timeout_seconds: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ) -> Any:
        def configure(client: Cafe24ApiClient) -> Cafe24ApiClient:
            if request_timeout_seconds is not None:
                client.request_timeout_seconds = request_timeout_seconds
            if max_attempts is not None:
                client.max_attempts = max_attempts
            return client

        client = configure(self._cafe24_client_for_row(conn, self._latest_cafe24_integration_row(conn, integration)))
        try:
            return api_call(client)
        except Cafe24ApiError as exc:
            if not cafe24_access_token_error(exc):
                raise
            retry_integration = self._latest_cafe24_integration_row(conn, integration)
            retry_client = configure(self._cafe24_client_for_row(conn, retry_integration, force_refresh=True))
            return api_call(retry_client)

    def list_cafe24_products(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        integration_id = str(payload.get("integrationId") or "").strip()
        keyword = str(payload.get("q") or payload.get("keyword") or "").strip()
        product_no = str(payload.get("productNo") or payload.get("product_no") or "").strip()
        try:
            limit = min(max(int(payload.get("limit") or 20), 1), 100)
            offset = max(int(payload.get("offset") or 0), 0)
        except (TypeError, ValueError):
            raise PanelError("조회 개수/페이지 값이 올바르지 않습니다.", status=400)
        with self._connect() as conn:
            integration = self._cafe24_integration_row(conn, integration_id)
            self._require_cafe24_scope(integration, "mall.read_product", "Cafe24 상품 조회")
            try:
                response = self._cafe24_call_with_token_retry(
                    conn,
                    integration,
                    lambda client: client.products(keyword=keyword, product_no=product_no, limit=limit, offset=offset),
                )
            except Cafe24ApiError as exc:
                self._log_cafe24_event(
                    conn,
                    mall_id=str(integration["mall_id"]),
                    shop_no=int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                    event_type="products.lookup",
                    status="failed",
                    request_payload={"keyword": keyword, "productNo": product_no, "limit": limit, "offset": offset},
                    error_message=str(exc),
                )
                conn.commit()
                raise self._cafe24_api_panel_error("Cafe24 상품 조회", exc) from exc
            products = [cafe24_product_payload(product) for product in cafe24_products_from_payload(response)]
            self._log_cafe24_event(
                conn,
                mall_id=str(integration["mall_id"]),
                shop_no=int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                event_type="products.lookup",
                status="success",
                request_payload={"keyword": keyword, "productNo": product_no, "limit": limit, "offset": offset},
                response_payload={"count": len(products)},
            )
            conn.commit()
        return {
            "products": products,
            "count": len(products),
            "query": {"keyword": keyword, "productNo": product_no, "limit": limit, "offset": offset},
        }

    def get_cafe24_product_detail(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        integration_id = str(payload.get("integrationId") or "").strip()
        product_no = str(payload.get("productNo") or payload.get("product_no") or "").strip()
        if not product_no:
            raise PanelError("조회할 Cafe24 상품번호가 필요합니다.", status=400)
        warnings: List[str] = []
        with self._connect() as conn:
            integration = self._cafe24_integration_row(conn, integration_id)
            self._require_cafe24_scope(integration, "mall.read_product", "Cafe24 상품 상세 조회")
            try:
                product_response = self._cafe24_call_with_token_retry(
                    conn,
                    integration,
                    lambda client: client.product(product_no),
                )
            except Cafe24ApiError as exc:
                self._log_cafe24_event(
                    conn,
                    mall_id=str(integration["mall_id"]),
                    shop_no=int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                    event_type="products.detail",
                    status="failed",
                    request_payload={"productNo": product_no},
                    error_message=str(exc),
                )
                conn.commit()
                raise self._cafe24_api_panel_error("Cafe24 상품 상세 조회", exc) from exc
            product_rows = cafe24_products_from_payload(product_response)
            if not product_rows:
                raise PanelError("Cafe24 상품을 찾지 못했습니다.", status=404)
            option_response = None
            variant_response = None
            try:
                option_response = self._cafe24_call_with_token_retry(
                    conn,
                    integration,
                    lambda client: client.product_options(product_no),
                )
            except Exception as exc:
                warnings.append(f"옵션 조회 실패: {exc}")
            try:
                variant_response = self._cafe24_call_with_token_retry(
                    conn,
                    integration,
                    lambda client: client.product_variants(product_no),
                )
            except Exception as exc:
                warnings.append(f"품목 조회 실패: {exc}")
            product_payload = cafe24_enriched_product_payload(
                product_rows[0],
                option_response=option_response,
                variant_response=variant_response,
                include_raw=True,
            )
            self._log_cafe24_event(
                conn,
                mall_id=str(integration["mall_id"]),
                shop_no=int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                event_type="products.detail",
                status="success" if not warnings else "partial",
                request_payload={"productNo": product_no},
                response_payload={
                    "optionCount": len(product_payload.get("options") or []),
                    "variantCount": len(product_payload.get("variants") or []),
                    "warnings": warnings,
                },
            )
            conn.commit()
        return {"product": product_payload, "warnings": warnings}

    def _cafe24_variant_option_entries(
        self,
        conn: DatabaseConnection,
        integration: Dict[str, Any],
        identity: Dict[str, str],
    ) -> List[Dict[str, str]]:
        product_no = str(identity.get("productNo") or "").strip()
        variant_code = str(identity.get("variantCode") or "").strip()
        custom_code = str(identity.get("customProductCode") or "").strip()
        if not product_no or not (variant_code or custom_code):
            return []
        try:
            self._require_cafe24_scope(integration, "mall.read_product", "Cafe24 품목 옵션 조회")
            response = self._cafe24_call_with_token_retry(
                conn,
                integration,
                lambda client: client.product_variants(product_no),
            )
        except Exception:
            return []
        for variant in cafe24_product_variants_from_payload(response):
            payload = cafe24_variant_payload(variant)
            payload_variant_code = str(payload.get("variantCode") or "").strip()
            payload_custom_code = str(payload.get("customProductCode") or "").strip()
            if variant_code and payload_variant_code and payload_variant_code != variant_code:
                continue
            if custom_code and payload_custom_code and payload_custom_code != custom_code:
                continue
            entries = cafe24_option_entries(
                {},
                {
                    "option_value": payload.get("optionText") or "",
                    "option_text": payload.get("optionText") or "",
                    "variant_option": payload.get("optionText") or "",
                    "options": variant.get("options") or variant.get("option") or variant.get("option_values") or [],
                },
            )
            if entries:
                return entries
        return []

    def _resolve_cafe24_mapping_source(
        self,
        source: Any,
        *,
        field_key: str = "",
        order_payload: Dict[str, Any],
        item_payload: Dict[str, Any],
        buyer: Dict[str, Any],
        receiver: Dict[str, Any],
        option_pairs: Dict[str, str],
        option_entries: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        option_entries = option_entries if option_entries is not None else cafe24_option_entries(order_payload, item_payload)
        if isinstance(source, dict):
            source_type = str(source.get("source") or source.get("type") or "").strip()
            extract = str(source.get("extract") or "").strip()
            fallback = source.get("fallback")
            value = ""
            if source_type == "fixed":
                value = str(source.get("value") if source.get("value") is not None else source.get("defaultValue") or "").strip()
            elif source_type == "item":
                field = str(source.get("field") or source.get("path") or "").strip()
                value = cafe24_payload_value(item_payload, (field,)) if field else ""
            elif source_type == "order":
                field = str(source.get("field") or source.get("path") or "").strip()
                value = cafe24_payload_value(order_payload, (field,)) if field else ""
            elif source_type == "buyer":
                field = str(source.get("field") or source.get("path") or "").strip()
                value = cafe24_payload_value(buyer, (field,)) if field else ""
            elif source_type == "receiver":
                field = str(source.get("field") or source.get("path") or "").strip()
                value = cafe24_payload_value(receiver, (field,)) if field else ""
            elif source_type == "option":
                label = str(source.get("label") or source.get("optionLabel") or source.get("name") or source.get("contains") or "").strip()
                if extract == "quantity_number":
                    candidates = cafe24_quantity_candidates_from_options(option_entries, label=label)
                    value = resolve_cafe24_quantity_candidates_for_panel(
                        candidates,
                        ambiguity_policy=str(source.get("ambiguityPolicy") or "needs_manual_review"),
                    )
                else:
                    lowered = label.lower()
                    value = next(
                        (
                            str(entry.get("value") or "").strip()
                            for entry in option_entries
                            if not lowered or lowered in str(entry.get("label") or "").lower()
                        ),
                        "",
                    )
            if value:
                return str(value).strip()
            if fallback:
                return self._resolve_cafe24_mapping_source(
                    fallback,
                    field_key=field_key,
                    order_payload=order_payload,
                    item_payload=item_payload,
                    buyer=buyer,
                    receiver=receiver,
                    option_pairs=option_pairs,
                    option_entries=option_entries,
                )
            return ""
        sources = source if isinstance(source, list) else [source]
        for spec in sources:
            text = str(spec or "").strip()
            if not text:
                continue
            if text == "quantity":
                return cafe24_payload_value(item_payload, ("quantity", "qty", "order_quantity"))
            if text.startswith("item."):
                value = cafe24_payload_value(item_payload, (text[5:],))
            elif text.startswith("order."):
                value = cafe24_payload_value(order_payload, (text[6:],))
            elif text.startswith("buyer."):
                value = cafe24_payload_value(buyer, (text[6:],))
            elif text.startswith("receiver."):
                value = cafe24_payload_value(receiver, (text[9:],))
            elif text.startswith("option:"):
                needle = text[7:].strip().lower()
                value = next((value for label, value in option_pairs.items() if needle in label.lower()), "")
            else:
                value = option_pairs.get(text, "")
            if value:
                if field_key == "orderedCount":
                    return coerce_cafe24_ordered_count_mapping_value_for_panel(value, label=text, source=text)
                return str(value).strip()
        return ""

    def _match_cafe24_mapping(
        self,
        conn: DatabaseConnection,
        mall_id: str,
        shop_no: int,
        identity: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT
                cm.*,
                p.form_structure_json,
                p.name AS internal_product_name,
                s.name AS supplier_name,
                s.api_url,
                s.integration_type,
                s.api_key,
                s.bearer_token,
                s.is_active AS supplier_is_active,
                ss.name AS supplier_service_name,
                ss.external_service_id AS supplier_service_external_id,
                ss.raw_json AS supplier_service_raw_json,
                ss.min_amount AS supplier_min_amount,
                ss.max_amount AS supplier_max_amount,
                ss.is_active AS supplier_service_is_active
            FROM cafe24_supplier_mappings cm
            LEFT JOIN products p ON p.id = cm.internal_product_id
            JOIN suppliers s ON s.id = cm.supplier_id
            LEFT JOIN supplier_services ss ON ss.id = cm.supplier_service_id
            WHERE cm.mall_id = ? AND cm.shop_no = ? AND cm.enabled = 1
            """,
            (mall_id, shop_no),
        ).fetchall()
        best: Optional[Dict[str, Any]] = None
        best_score = -1
        for row in rows:
            score = 0
            row_product_no = str(row["cafe24_product_no"] or "")
            row_variant_code = str(row["cafe24_variant_code"] or "")
            row_custom_code = str(row["cafe24_custom_product_code"] or "")
            if not any([row_product_no, row_variant_code, row_custom_code]):
                continue
            if row_product_no:
                if row_product_no != identity["productNo"]:
                    continue
                score += 4
            if row_variant_code:
                if row_variant_code != identity["variantCode"]:
                    continue
                score += 3
            if row_custom_code:
                if row_custom_code != identity["customProductCode"]:
                    continue
                score += 2
            if score > best_score:
                best = row
                best_score = score
        return best

    def _normalize_cafe24_item_fields(
        self,
        *,
        product: Dict[str, Any],
        mapping: Dict[str, Any],
        order_payload: Dict[str, Any],
        item_payload: Dict[str, Any],
        buyer: Dict[str, Any],
        receiver: Dict[str, Any],
        extra_option_entries: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        form_structure = ensure_request_memo_form_structure(parse_json(product["form_structure_json"], {}), "추가 요청사항")
        template = form_structure.get("template", {})
        schema = form_structure.get("schema", {})
        field_mapping = parse_json(mapping["field_mapping_json"], {})
        option_entries = cafe24_option_entries(order_payload, item_payload) + list(extra_option_entries or [])
        option_pairs = cafe24_option_pairs(order_payload, item_payload)
        for entry in extra_option_entries or []:
            option_pairs.setdefault(entry["label"], entry["value"])
        option_blob = " ".join(option_pairs.values())
        first_url_match = re.search(r"https?://[^\s,|]+", option_blob)
        account_candidate = ""
        for label, value in option_pairs.items():
            lowered = label.lower()
            if any(token in lowered for token in ("계정", "아이디", "id", "account", "username")):
                account_candidate = value
                break

        fields: Dict[str, Any] = {}
        for field_key in template.keys() | schema.keys():
            mapped_value = self._resolve_cafe24_mapping_source(
                field_mapping.get(field_key),
                field_key=field_key,
                order_payload=order_payload,
                item_payload=item_payload,
                buyer=buyer,
                receiver=receiver,
                option_pairs=option_pairs,
                option_entries=option_entries,
            )
            if mapped_value:
                fields[field_key] = mapped_value
                continue
            if field_key == "orderedCount":
                fields[field_key] = default_cafe24_ordered_count_for_panel(item_payload, option_entries)
            elif field_key == "targetUrl" and first_url_match:
                fields[field_key] = first_url_match.group(0)
            elif field_key == "targetValue":
                fields[field_key] = first_url_match.group(0) if first_url_match else account_candidate
            elif field_key == "contactPhone":
                fields[field_key] = cafe24_payload_value(receiver, ("cellphone", "phone", "mobile", "phone1")) or cafe24_payload_value(
                    buyer,
                    ("cellphone", "phone", "mobile", "phone1"),
                )
            elif field_key == "requestMemo":
                fields[field_key] = cafe24_payload_value(order_payload, ("memo", "client_memo", "order_memo")) or option_pairs.get("orderMemo", "")

        if "orderedCount" not in fields:
            fields["orderedCount"] = default_cafe24_ordered_count_for_panel(item_payload, option_entries)
        return fields

    def _supplier_mapping_from_cafe24_mapping(
        self,
        mapping: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        supplier_id = str(mapping.get("supplier_id") or "").strip()
        if not supplier_id:
            return None
        supplier_external_service_id = str(
            mapping.get("supplier_service_external_id")
            or mapping.get("supplier_external_service_id")
            or mapping.get("supplier_product_uuid")
            or mapping.get("supplier_product_code")
            or ""
        ).strip()
        if not supplier_external_service_id:
            return None
        return {
            "id": str(mapping.get("id") or ""),
            "product_id": str(mapping.get("internal_product_id") or ""),
            "supplier_id": supplier_id,
            "supplier_service_id": str(mapping.get("supplier_service_id") or supplier_external_service_id),
            "supplier_external_service_id": supplier_external_service_id,
            "api_url": str(mapping.get("api_url") or ""),
            "integration_type": str(mapping.get("integration_type") or SUPPLIER_INTEGRATION_CLASSIC),
            "api_key": mapping.get("api_key") or "",
            "bearer_token": mapping.get("bearer_token") or "",
            "supplier_name": str(mapping.get("supplier_name") or ""),
            "supplier_service_name": str(mapping.get("supplier_service_name") or ""),
            "supplier_is_active": mapping.get("supplier_is_active"),
            "supplier_service_raw_json": mapping.get("supplier_service_raw_json") or "{}",
            "supplier_min_amount": mapping.get("supplier_min_amount"),
            "supplier_max_amount": mapping.get("supplier_max_amount"),
        }

    def _normalize_cafe24_direct_item_fields(
        self,
        *,
        mapping: Dict[str, Any],
        order_payload: Dict[str, Any],
        item_payload: Dict[str, Any],
        buyer: Dict[str, Any],
        receiver: Dict[str, Any],
        extra_option_entries: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        field_mapping = parse_json(mapping.get("field_mapping_json"), {})
        option_entries = cafe24_option_entries(order_payload, item_payload) + list(extra_option_entries or [])
        option_pairs = cafe24_option_pairs(order_payload, item_payload)
        for entry in extra_option_entries or []:
            option_pairs.setdefault(entry["label"], entry["value"])
        option_blob = " ".join(option_pairs.values())
        first_url_match = re.search(r"https?://[^\s,|]+", option_blob)
        account_candidate = ""
        for label, value in option_pairs.items():
            lowered = label.lower()
            if any(token in lowered for token in ("계정", "아이디", "id", "account", "username", "링크", "url")):
                account_candidate = value
                break

        field_keys = set(field_mapping.keys()) | {
            "targetUrl",
            "targetValue",
            "orderedCount",
            "contactPhone",
            "requestMemo",
            "comments",
            "runs",
            "interval",
            "min",
            "max",
            "posts",
            "oldPosts",
            "delay",
            "expiry",
        }
        fields: Dict[str, Any] = {}
        for field_key in field_keys:
            mapped_value = self._resolve_cafe24_mapping_source(
                field_mapping.get(field_key),
                field_key=field_key,
                order_payload=order_payload,
                item_payload=item_payload,
                buyer=buyer,
                receiver=receiver,
                option_pairs=option_pairs,
                option_entries=option_entries,
            )
            if mapped_value:
                fields[field_key] = mapped_value
                continue
            if field_key == "orderedCount":
                fields[field_key] = default_cafe24_ordered_count_for_panel(item_payload, option_entries)
            elif field_key == "targetUrl" and first_url_match:
                fields[field_key] = first_url_match.group(0)
            elif field_key == "targetValue":
                fields[field_key] = first_url_match.group(0) if first_url_match else account_candidate
            elif field_key == "contactPhone":
                fields[field_key] = cafe24_payload_value(receiver, ("cellphone", "phone", "mobile", "phone1")) or cafe24_payload_value(
                    buyer,
                    ("cellphone", "phone", "mobile", "phone1"),
                )
            elif field_key == "requestMemo":
                fields[field_key] = cafe24_payload_value(order_payload, ("memo", "client_memo", "order_memo")) or option_pairs.get("orderMemo", "")

        return {key: value for key, value in fields.items() if value not in ("", None)}

    def _validate_cafe24_direct_fields(self, fields: Dict[str, Any], mapping: Dict[str, Any]) -> None:
        validate_cafe24_direct_fields_for_panel(
            fields,
            mapping,
            looks_like_url=looks_like_url,
            normalize_url=normalize_url,
        )

    def _ensure_cafe24_channel_user(self, conn: DatabaseConnection, mall_id: str, shop_no: int) -> str:
        user_id = f"user_cafe24_{re.sub(r'[^A-Za-z0-9_]', '_', mall_id)}_{int(shop_no)}"
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if existing is not None:
            return user_id
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO users (
                id, name, email, phone, tier, role, avatar_label, balance, is_active,
                account_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                f"Cafe24 {mall_id}",
                f"cafe24-{mall_id}-{shop_no}@external.instamart.local",
                "",
                "EXTERNAL",
                "integration",
                "C24",
                0,
                0,
                "external_channel",
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
            VALUES (?, 0, 0, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, timestamp, timestamp),
        )
        return user_id

    def _active_supplier_mapping_for_product(
        self,
        conn: DatabaseConnection,
        product_id: str,
        cafe24_mapping: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        mapping = None
        cafe24_mapping_dict = dict(cafe24_mapping or {})
        preferred_supplier_id = str(cafe24_mapping_dict.get("supplier_id") or "").strip()
        if preferred_supplier_id:
            mapping = conn.execute(
                """
                SELECT
                    psm.*, s.api_url, s.integration_type, s.api_key, s.bearer_token,
                    s.name AS supplier_name, s.is_active AS supplier_is_active
                FROM product_supplier_mappings psm
                JOIN suppliers s ON s.id = psm.supplier_id
                WHERE psm.product_id = ? AND psm.supplier_id = ? AND psm.is_active = 1
                LIMIT 1
                """,
                (product_id, preferred_supplier_id),
            ).fetchone()
        if mapping is None:
            mapping = conn.execute(
                """
                SELECT
                    psm.*, s.api_url, s.integration_type, s.api_key, s.bearer_token,
                    s.name AS supplier_name, s.is_active AS supplier_is_active
                FROM product_supplier_mappings psm
                JOIN suppliers s ON s.id = psm.supplier_id
                WHERE psm.product_id = ? AND psm.is_primary = 1 AND psm.is_active = 1
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
        if mapping is None and preferred_supplier_id and cafe24_mapping_dict:
            supplier = conn.execute("SELECT * FROM suppliers WHERE id = ?", (preferred_supplier_id,)).fetchone()
            if supplier is not None:
                return {
                    "id": "",
                    "product_id": product_id,
                    "supplier_id": supplier["id"],
                    "supplier_service_id": str(
                        cafe24_mapping_dict.get("supplier_product_uuid") or cafe24_mapping_dict.get("supplier_product_code") or ""
                    ),
                    "supplier_external_service_id": str(
                        cafe24_mapping_dict.get("supplier_product_uuid") or cafe24_mapping_dict.get("supplier_product_code") or ""
                    ),
                    "api_url": supplier["api_url"],
                    "integration_type": supplier["integration_type"],
                    "api_key": supplier["api_key"],
                    "bearer_token": supplier["bearer_token"],
                    "supplier_name": supplier["name"],
                    "supplier_is_active": supplier["is_active"],
                }
        return mapping

    def _create_cafe24_internal_order(
        self,
        conn: DatabaseConnection,
        *,
        integration: Dict[str, Any],
        order_item_id: str,
        identity: Dict[str, str],
        product: Dict[str, Any],
        fields: Dict[str, Any],
        raw_payload: Dict[str, Any],
        supplier_mapping: Optional[Dict[str, Any]],
    ) -> str:
        existing = conn.execute(
            "SELECT internal_order_id FROM cafe24_order_items WHERE id = ?",
            (order_item_id,),
        ).fetchone()
        if existing is not None and str(existing["internal_order_id"] or "").strip():
            return str(existing["internal_order_id"])
        duplicate = conn.execute(
            """
            SELECT id
            FROM orders
            WHERE order_channel = ? AND external_order_id = ? AND external_order_item_id = ?
            """,
            (ORDER_CHANNEL_CAFE24, identity["orderId"], identity["orderItemCode"]),
        ).fetchone()
        if duplicate is not None:
            return str(duplicate["id"])

        user_id = self._ensure_cafe24_channel_user(conn, str(integration["mall_id"]), int(integration["shop_no"]))
        timestamp = now_iso()
        order_number = generate_public_order_number()
        while conn.execute("SELECT 1 FROM orders WHERE order_number = ? LIMIT 1", (order_number,)).fetchone() is not None:
            order_number = generate_public_order_number()
        quantity = self._resolve_quantity(product, fields)
        total_price = int(product["price"]) if product["price_strategy"] == "fixed" else int(product["price"]) * quantity
        target_value = (
            str(fields.get("targetValue") or "")
            or str(fields.get("targetUrl") or "")
            or str(fields.get("targetKeyword") or "")
        ).strip()
        notes = {
            "memo": str(fields.get("requestMemo") or "").strip(),
            "source": "cafe24",
            "mallId": integration["mall_id"],
            "shopNo": int(integration["shop_no"]),
            "cafe24OrderId": identity["orderId"],
            "cafe24OrderItemCode": identity["orderItemCode"],
            "buyerName": cafe24_payload_value(raw_payload.get("buyer") or {}, ("name", "buyer_name")),
        }
        order_id = f"order_{uuid4().hex[:16]}"
        conn.execute(
            """
            INSERT INTO orders (
                id, order_number, user_id, platform_section_id, product_category_id, product_id,
                product_name_snapshot, option_name_snapshot, target_value, contact_phone,
                quantity, unit_price, total_price, status, order_channel, external_order_id,
                external_order_item_id, dispatch_status, external_payload_json, notes_json,
                idempotency_key, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                str(fields.get("contactPhone") or "").strip(),
                quantity,
                int(product["price"]),
                total_price,
                "queued",
                ORDER_CHANNEL_CAFE24,
                identity["orderId"],
                identity["orderItemCode"],
                ORDER_DISPATCH_READY if supplier_mapping else ORDER_DISPATCH_UNMAPPED,
                as_json(redact_external_payload(raw_payload)),
                as_json(notes),
                "",
                timestamp,
                timestamp,
            ),
        )
        template = ensure_request_memo_form_structure(parse_json(product["form_structure_json"], {}), "추가 요청사항").get("template", {})
        for field_index, (field_key, field_value) in enumerate(fields.items()):
            if field_value in ("", None):
                continue
            field_label = self._field_label(template.get(field_key, {}), field_key)
            conn.execute(
                "INSERT INTO order_fields (id, order_id, field_key, field_label, field_value) VALUES (?, ?, ?, ?, ?)",
                (f"{order_id}_field_{field_index}", order_id, field_key, field_label, str(field_value)),
            )
        conn.execute(
            """
            UPDATE cafe24_order_items
            SET internal_order_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (order_id, timestamp, order_item_id),
        )
        return order_id

    def _process_cafe24_item(
        self,
        conn: DatabaseConnection,
        *,
        integration: Dict[str, Any],
        order_payload: Dict[str, Any],
        item_payload: Dict[str, Any],
        index: int,
        submit_ready: bool,
        require_mapping_auto_dispatch: bool = False,
    ) -> Dict[str, Any]:
        mall_id = str(integration["mall_id"])
        shop_no = int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO)
        identity = cafe24_item_identity(order_payload, item_payload, index)
        if not identity["orderId"]:
            raise PanelError("Cafe24 주문번호가 없는 주문 payload입니다.")
        buyer = order_payload.get("buyer") if isinstance(order_payload.get("buyer"), dict) else {}
        receivers = order_payload.get("receivers")
        receiver = receivers[0] if isinstance(receivers, list) and receivers and isinstance(receivers[0], dict) else {}
        source_status = identity["statusCode"]
        payment_status, payment_status_source = cafe24_payment_status_with_source(order_payload, item_payload, source_status)
        payment_gate_status = cafe24_payment_gate_status(source_status, payment_status)
        payment_snapshot = cafe24_payment_snapshot_from_payload(order_payload, item_payload)
        order_date = cafe24_order_date_from_payload(order_payload, item_payload)
        status = normalize_cafe24_status(source_status)
        error_message = ""
        mapping_row = self._match_cafe24_mapping(conn, mall_id, shop_no, identity)
        mapping = dict(mapping_row) if mapping_row is not None else None
        normalized_fields: Dict[str, Any] = {}
        supplier_payload: Dict[str, Any] = {}
        internal_order_id = ""
        supplier_mapping: Optional[Dict[str, Any]] = None
        product: Optional[Dict[str, Any]] = None
        supplier_id = ""
        supplier_service_id = ""
        supplier_external_service_id = ""

        raw_payload = {
            "order": order_payload,
            "item": item_payload,
            "buyer": buyer,
            "receiver": receiver,
        }
        if payment_gate_status == "cancelled":
            status = "cancelled"
            error_message = "Cafe24 취소/반품 계열 상태입니다. 공급 전이면 자동 차단됩니다."
        elif payment_gate_status == "payment_pending":
            status = "payment_pending"
            error_message = "결제 완료 전 주문입니다. 공급하지 않습니다."
        elif payment_gate_status != "payment_confirmed":
            status = "payment_review_required"
            error_message = "Cafe24 결제 완료 상태가 확인되지 않아 검수가 필요합니다."
        elif mapping is None:
            status = "waiting_input"
            error_message = "Cafe24 상품 매핑이 없습니다."
        else:
            supplier_mapping = self._supplier_mapping_from_cafe24_mapping(mapping)
            supplier_id = str(mapping.get("supplier_id") or "")
            supplier_service_id = str(mapping.get("supplier_service_id") or "")
            supplier_external_service_id = str(
                mapping.get("supplier_service_external_id")
                or mapping.get("supplier_external_service_id")
                or mapping.get("supplier_product_uuid")
                or mapping.get("supplier_product_code")
                or ""
            )
            if supplier_mapping is None:
                status = "mapping_error"
                error_message = "Cafe24 상품에 연결된 공급사 서비스가 없습니다."
            elif not bool(mapping.get("supplier_is_active")):
                status = "mapping_error"
                error_message = "Cafe24 상품에 연결된 공급사가 비활성 상태입니다."
            elif mapping.get("supplier_service_id") and not bool(mapping.get("supplier_service_is_active")):
                status = "mapping_error"
                error_message = "Cafe24 상품에 연결된 공급사 서비스가 비활성 상태입니다. 서비스 동기화 또는 매핑 수정이 필요합니다."
            elif mapping.get("internal_product_id"):
                base_option_entries = cafe24_option_entries(order_payload, item_payload)
                extra_option_entries: List[Dict[str, str]] = []
                try:
                    fallback_quantity = int(str(cafe24_payload_value(item_payload, ("quantity", "qty", "order_quantity")) or "0").replace(",", ""))
                except ValueError:
                    fallback_quantity = 0
                supplier_min_amount = int(mapping.get("supplier_min_amount") or 0)
                if (
                    supplier_min_amount
                    and fallback_quantity
                    and fallback_quantity < supplier_min_amount
                    and not cafe24_quantity_candidates_from_options(base_option_entries)
                ):
                    extra_option_entries = self._cafe24_variant_option_entries(conn, integration, identity)
                    if extra_option_entries:
                        raw_payload["variantOptionEntries"] = extra_option_entries
                product_row = conn.execute(
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
                    (mapping["internal_product_id"],),
                ).fetchone()
                if product_row is None:
                    status = "mapping_error"
                    error_message = "매핑된 내부 상품 참조가 비활성 또는 삭제 상태입니다."
                else:
                    product = dict(product_row)
                    try:
                        normalized_fields = self._normalize_cafe24_item_fields(
                            product=product,
                            mapping=mapping,
                            order_payload=order_payload,
                            item_payload=item_payload,
                            buyer=buyer,
                            receiver=receiver,
                            extra_option_entries=extra_option_entries,
                        )
                        form_structure = ensure_request_memo_form_structure(parse_json(product["form_structure_json"], {}), "추가 요청사항")
                        self._validate_fields(normalized_fields, form_structure.get("schema", {}))
                        self._validate_product_target(product, normalized_fields, require_preview=False)
                        supplier_payload = self._build_supplier_order_payload(product, normalized_fields, supplier_mapping)
                        status = "ready_to_submit"
                    except PanelError as exc:
                        status = cafe24_processing_error_status(exc)
                        error_message = str(exc)
            else:
                base_option_entries = cafe24_option_entries(order_payload, item_payload)
                extra_option_entries = []
                try:
                    fallback_quantity = int(str(cafe24_payload_value(item_payload, ("quantity", "qty", "order_quantity")) or "0").replace(",", ""))
                except ValueError:
                    fallback_quantity = 0
                supplier_min_amount = int(mapping.get("supplier_min_amount") or 0)
                if (
                    supplier_min_amount
                    and fallback_quantity
                    and fallback_quantity < supplier_min_amount
                    and not cafe24_quantity_candidates_from_options(base_option_entries)
                ):
                    extra_option_entries = self._cafe24_variant_option_entries(conn, integration, identity)
                    if extra_option_entries:
                        raw_payload["variantOptionEntries"] = extra_option_entries
                try:
                    normalized_fields = self._normalize_cafe24_direct_item_fields(
                        mapping=mapping,
                        order_payload=order_payload,
                        item_payload=item_payload,
                        buyer=buyer,
                        receiver=receiver,
                        extra_option_entries=extra_option_entries,
                    )
                    self._validate_cafe24_direct_fields(normalized_fields, mapping)
                    supplier_payload = self._build_supplier_order_payload(
                        {
                            "product_code": "",
                            "platform_slug": "",
                            "price_strategy": "unit",
                        },
                        normalized_fields,
                        supplier_mapping,
                    )
                    status = "ready_to_submit"
                except PanelError as exc:
                    status = cafe24_processing_error_status(exc)
                    error_message = str(exc)

        timestamp = now_iso()
        row_id = f"cafe24_item_{uuid4().hex[:16]}"
        conn.execute(
            """
            INSERT INTO cafe24_order_items (
                id, mall_id, shop_no, cafe24_order_id, cafe24_order_item_code,
                cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code,
                cafe24_order_date, buyer_name, buyer_email, buyer_phone, receiver_name, order_status_code,
                payment_status, payment_status_source, payment_gate_status, payment_method, payment_amount,
                payment_paid_at, payment_reference, payment_snapshot_json, source_status, standard_status,
                mapping_id, product_id, supplier_id, supplier_service_id, supplier_external_service_id,
                normalized_fields_json, supplier_payload_json, raw_payload_json,
                error_message, last_synced_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mall_id, shop_no, cafe24_order_id, cafe24_order_item_code)
            DO UPDATE SET
                cafe24_product_no = excluded.cafe24_product_no,
                cafe24_variant_code = excluded.cafe24_variant_code,
                cafe24_custom_product_code = excluded.cafe24_custom_product_code,
                cafe24_order_date = excluded.cafe24_order_date,
                buyer_name = excluded.buyer_name,
                buyer_email = excluded.buyer_email,
                buyer_phone = excluded.buyer_phone,
                receiver_name = excluded.receiver_name,
                order_status_code = excluded.order_status_code,
                payment_status = excluded.payment_status,
                payment_status_source = excluded.payment_status_source,
                payment_gate_status = excluded.payment_gate_status,
                payment_method = excluded.payment_method,
                payment_amount = excluded.payment_amount,
                payment_paid_at = excluded.payment_paid_at,
                payment_reference = excluded.payment_reference,
                payment_snapshot_json = excluded.payment_snapshot_json,
                source_status = excluded.source_status,
                standard_status = CASE
                    WHEN cafe24_order_items.standard_status IN ('supplier_submitted', 'supplier_progress', 'completed')
                    THEN cafe24_order_items.standard_status
                    ELSE excluded.standard_status
                END,
                mapping_id = excluded.mapping_id,
                product_id = excluded.product_id,
                supplier_id = excluded.supplier_id,
                supplier_service_id = excluded.supplier_service_id,
                supplier_external_service_id = excluded.supplier_external_service_id,
                normalized_fields_json = excluded.normalized_fields_json,
                supplier_payload_json = excluded.supplier_payload_json,
                raw_payload_json = excluded.raw_payload_json,
                error_message = excluded.error_message,
                last_synced_at = excluded.last_synced_at,
                updated_at = excluded.updated_at
            """,
            (
                row_id,
                mall_id,
                shop_no,
                identity["orderId"],
                identity["orderItemCode"],
                identity["productNo"],
                identity["variantCode"],
                identity["customProductCode"],
                order_date,
                cafe24_payload_value(buyer, ("name", "buyer_name")),
                cafe24_payload_value(buyer, ("email", "buyer_email")),
                cafe24_payload_value(buyer, ("cellphone", "phone", "mobile")),
                cafe24_payload_value(receiver, ("name", "receiver_name")),
                source_status,
                payment_status,
                payment_status_source,
                payment_gate_status,
                payment_snapshot["method"],
                int(payment_snapshot["amount"] or 0),
                payment_snapshot["paidAt"],
                payment_snapshot["reference"],
                as_json(payment_snapshot),
                source_status,
                status,
                mapping["id"] if mapping is not None else "",
                product["id"] if product is not None else "",
                supplier_id,
                supplier_service_id,
                supplier_external_service_id,
                as_json(normalized_fields),
                as_json(supplier_payload),
                as_json(raw_payload),
                error_message,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        current = conn.execute(
            """
            SELECT *
            FROM cafe24_order_items
            WHERE mall_id = ? AND shop_no = ? AND cafe24_order_id = ? AND cafe24_order_item_code = ?
            """,
            (mall_id, shop_no, identity["orderId"], identity["orderItemCode"]),
        ).fetchone()
        current_status = str(current["standard_status"] or status)
        if current_status == "ready_to_submit" and product is not None:
            internal_order_id = self._create_cafe24_internal_order(
                conn,
                integration=integration,
                order_item_id=current["id"],
                identity=identity,
                product=product,
                fields=normalized_fields,
                raw_payload=raw_payload,
                supplier_mapping=supplier_mapping,
            )
        dispatch_allowed = bool(
            submit_ready
            and mapping
            and (not require_mapping_auto_dispatch or mapping.get("auto_dispatch_enabled"))
        )
        if dispatch_allowed and internal_order_id and product is not None and supplier_mapping is not None:
            # Commit the normalized order before the external supplier request.
            conn.commit()
            dispatch = self._dispatch_supplier_order(internal_order_id, product, normalized_fields, supplier_mapping)
            with self._connect() as dispatch_conn:
                next_status = "supplier_submitted" if dispatch["status"] in {"submitted", "accepted"} else "failed"
                dispatch_conn.execute(
                    """
                    UPDATE cafe24_order_items
                    SET standard_status = ?, supplier_order_id = ?, supplier_order_uuid = ?,
                        error_message = ?, last_submitted_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        next_status,
                        dispatch.get("id") or "",
                        dispatch.get("supplierExternalOrderId") or "",
                        "" if next_status == "supplier_submitted" else "공급사 발주 실패",
                        now_iso(),
                        now_iso(),
                        current["id"],
                    ),
                )
                dispatch_conn.commit()
            return {"id": current["id"], "status": next_status, "submitted": True}
        return {"id": current["id"], "status": current_status, "submitted": False}

    def poll_due_cafe24_orders(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        actor = str(payload.get("_adminActor") or payload.get("actor") or "cron").strip() or "cron"
        force = bool(payload.get("force", False))
        use_cursor = env_flag(payload.get("useCursor") or payload.get("use_cursor"))
        try:
            lookback_days = int(payload.get("lookbackDays") or CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS)
        except (TypeError, ValueError):
            lookback_days = CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS
        lookback_days = min(max(lookback_days, 1), 90)
        try:
            lookback_minutes = int(payload.get("lookbackMinutes") or payload.get("lookback_minutes") or 0)
        except (TypeError, ValueError):
            lookback_minutes = 0
        lookback_minutes = min(max(lookback_minutes, 0), 7 * 24 * 60)
        try:
            overlap_minutes = int(payload.get("overlapMinutes") or payload.get("overlap_minutes") or CAFE24_ORDER_OVERLAP_MINUTES)
        except (TypeError, ValueError):
            overlap_minutes = CAFE24_ORDER_OVERLAP_MINUTES
        overlap_minutes = min(max(overlap_minutes, 0), 24 * 60)
        try:
            limit = int(payload.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50
        limit = min(max(limit, 1), 200)
        try:
            page_limit = int(payload.get("pageLimit") or CAFE24_ORDER_PAGE_LIMIT)
        except (TypeError, ValueError):
            page_limit = CAFE24_ORDER_PAGE_LIMIT
        page_limit = min(max(page_limit, 1), CAFE24_ORDER_PAGE_LIMIT)
        try:
            max_pages = int(payload.get("maxPages") or CAFE24_ORDER_MAX_PAGES)
        except (TypeError, ValueError):
            max_pages = CAFE24_ORDER_MAX_PAGES
        max_pages = min(max(max_pages, 1), CAFE24_ORDER_MAX_PAGES)
        try:
            detail_fetch_limit = int(payload.get("detailFetchLimit") if payload.get("detailFetchLimit") is not None else 200)
        except (TypeError, ValueError):
            detail_fetch_limit = 200
        detail_fetch_limit = min(max(detail_fetch_limit, 0), 500)
        try:
            request_timeout_seconds = float(
                payload.get("requestTimeoutSeconds")
                or payload.get("request_timeout_seconds")
                or 0
            )
        except (TypeError, ValueError):
            request_timeout_seconds = 0.0
        if request_timeout_seconds <= 0:
            request_timeout_seconds = None
        else:
            request_timeout_seconds = min(max(request_timeout_seconds, 1.0), 15.0)
        try:
            max_attempts = int(payload.get("maxAttempts") or payload.get("max_attempts") or 0)
        except (TypeError, ValueError):
            max_attempts = 0
        max_attempts = min(max(max_attempts, 0), 3) or None
        now = dt.datetime.now().astimezone()
        start_at = now - (dt.timedelta(minutes=lookback_minutes) if lookback_minutes else dt.timedelta(days=lookback_days))
        start_date = start_at.strftime("%Y-%m-%d %H:%M:%S")
        end_date = now.strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            integration_rows = conn.execute(
                """
                SELECT *
                FROM cafe24_integrations
                WHERE is_active = 1
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        processed_integrations = 0
        skipped_integrations = 0
        locked_integrations = 0
        reconnect_required = 0
        stored_order_items = 0
        response_orders = 0
        for integration_row in integration_rows:
            integration = dict(integration_row)
            integration_id = str(integration["id"])
            mall_id = str(integration["mall_id"])
            shop_no = int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO)
            token_status = self._cafe24_token_status(integration)
            if token_status == CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED:
                reconnect_required += 1
                skipped_integrations += 1
                message = self._cafe24_token_status_message(integration)
                with self._connect() as conn:
                    conn.execute(
                        """
                        UPDATE cafe24_integrations
                        SET last_auto_poll_status = ?, last_auto_poll_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        ("reconnect_required", message[:1000], now_iso(), integration_id),
                    )
                    conn.commit()
                results.append({"integrationId": integration_id, "mallId": mall_id, "shopNo": shop_no, "status": "reconnect_required", "message": message})
                continue
            if not self._cafe24_auto_poll_due(integration, force=force):
                skipped_integrations += 1
                results.append({"integrationId": integration_id, "mallId": mall_id, "shopNo": shop_no, "status": "skipped", "message": "아직 다음 자동 수집 주기가 아닙니다."})
                continue
            with self._connect() as conn:
                owner = self._acquire_cafe24_poll_lock(conn, integration_id)
                conn.commit()
            if not owner:
                locked_integrations += 1
                results.append({"integrationId": integration_id, "mallId": mall_id, "shopNo": shop_no, "status": "locked", "message": "이미 자동 수집이 진행 중입니다."})
                continue

            started = time.perf_counter()
            try:
                result = self.poll_cafe24_orders(
                    {
                        "integrationId": integration_id,
                        "startDate": start_date,
                        "endDate": end_date,
                        "useCursor": use_cursor,
                        "overlapMinutes": overlap_minutes,
                        "pageLimit": page_limit,
                        "maxPages": max_pages,
                        "detailFetchLimit": detail_fetch_limit,
                        "requestTimeoutSeconds": request_timeout_seconds,
                        "maxAttempts": max_attempts,
                        "submitReady": False,
                        "_adminActor": actor,
                    }
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                summary = result.get("summary", {})
                stored_count = int(summary.get("storedOrderItemCount") or result.get("processed") or 0)
                response_count = int(summary.get("responseOrderCount") or 0)
                stored_order_items += stored_count
                response_orders += response_count
                processed_integrations += 1
                message = f"자동 수집 완료 · Cafe24 {response_count}건 · 품주 {stored_count}개 저장 · {duration_ms}ms"
                with self._connect() as conn:
                    self._release_cafe24_poll_lock(conn, integration_id, owner, status="success", message=message)
                    self._log_cafe24_event(
                        conn,
                        mall_id=mall_id,
                        shop_no=shop_no,
                        event_type="orders.auto_poll",
                        status="success",
                        request_payload={
                            "lookbackDays": lookback_days,
                            "lookbackMinutes": lookback_minutes,
                            "useCursor": use_cursor,
                            "overlapMinutes": overlap_minutes,
                            "startDate": start_date,
                            "endDate": end_date,
                            "pageLimit": page_limit,
                            "maxPages": max_pages,
                            "detailFetchLimit": detail_fetch_limit,
                            "requestTimeoutSeconds": request_timeout_seconds,
                            "maxAttempts": max_attempts,
                            "submitReady": False,
                            "autoDispatch": False,
                        },
                        response_payload={"durationMs": duration_ms, **summary},
                    )
                    conn.commit()
                results.append({"integrationId": integration_id, "mallId": mall_id, "shopNo": shop_no, "status": "success", "message": message, "summary": summary})
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                message = str(exc)
                errors.append(f"{mall_id}/{shop_no}: {message}")
                status = (
                    "reconnect_required"
                    if cafe24_refresh_error_requires_reconnect(message) or "재연결" in message or "refresh token" in message.lower()
                    else "failed"
                )
                if status == "reconnect_required":
                    reconnect_required += 1
                with self._connect() as conn:
                    if status == "reconnect_required":
                        self._mark_cafe24_token_state(
                            conn,
                            integration_id,
                            status=CAFE24_TOKEN_STATUS_RECONNECT_REQUIRED,
                            message=message,
                            reconnect_required=True,
                            clear_lock=False,
                        )
                    self._release_cafe24_poll_lock(conn, integration_id, owner, status=status, message=message)
                    self._log_cafe24_event(
                        conn,
                        mall_id=mall_id,
                        shop_no=shop_no,
                        event_type="orders.auto_poll",
                        status="failed",
                        request_payload={
                            "lookbackDays": lookback_days,
                            "lookbackMinutes": lookback_minutes,
                            "useCursor": use_cursor,
                            "overlapMinutes": overlap_minutes,
                            "startDate": start_date,
                            "endDate": end_date,
                            "pageLimit": page_limit,
                            "maxPages": max_pages,
                            "detailFetchLimit": detail_fetch_limit,
                            "requestTimeoutSeconds": request_timeout_seconds,
                            "maxAttempts": max_attempts,
                            "submitReady": False,
                            "autoDispatch": False,
                        },
                        response_payload={"durationMs": duration_ms},
                        error_message=message,
                    )
                    conn.commit()
                results.append({"integrationId": integration_id, "mallId": mall_id, "shopNo": shop_no, "status": status, "message": message})

        return {
            "processedIntegrations": processed_integrations,
            "skippedIntegrations": skipped_integrations,
            "lockedIntegrations": locked_integrations,
            "reconnectRequiredIntegrations": reconnect_required,
            "responseOrderCount": response_orders,
            "storedOrderItemCount": stored_order_items,
            "errors": errors,
            "results": results,
            "summary": {
                "lookbackDays": lookback_days,
                "lookbackMinutes": lookback_minutes,
                "useCursor": use_cursor,
                "overlapMinutes": overlap_minutes,
                "intervalMinutes": CAFE24_AUTO_POLL_INTERVAL_MINUTES,
                "pageLimit": page_limit,
                "maxPages": max_pages,
                "detailFetchLimit": detail_fetch_limit,
                "requestTimeoutSeconds": request_timeout_seconds,
                "maxAttempts": max_attempts,
                "autoDispatch": False,
                "submitReady": False,
            },
        }

    def poll_cafe24_orders(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        integration_id = str(payload.get("integrationId") or "").strip()
        submit_ready = bool(payload.get("submitReady", False))
        actor = self._admin_actor(payload)
        processed = 0
        waiting = 0
        blocked = 0
        submitted = 0
        failed = 0
        errors: List[str] = []
        response_order_count = 0
        requested_windows: List[Dict[str, Any]] = []
        query_pages: List[Dict[str, Any]] = []
        detail_fetch_total = 0
        detail_fetch_error_count = 0
        with self._connect() as conn:
            if integration_id:
                integration_rows = [self._cafe24_integration_row(conn, integration_id)]
            else:
                integration_rows = conn.execute("SELECT * FROM cafe24_integrations WHERE is_active = 1 ORDER BY updated_at DESC").fetchall()
            if not integration_rows:
                raise PanelError("활성 Cafe24 연동 정보가 없습니다.")
            for integration in integration_rows:
                mall_id = str(integration["mall_id"])
                shop_no = int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO)
                try:
                    overlap_minutes = int(payload.get("overlapMinutes") or payload.get("overlap_minutes") or CAFE24_ORDER_OVERLAP_MINUTES)
                except (TypeError, ValueError):
                    overlap_minutes = CAFE24_ORDER_OVERLAP_MINUTES
                overlap_minutes = min(max(overlap_minutes, 0), 24 * 60)
                try:
                    request_timeout_seconds = float(
                        payload.get("requestTimeoutSeconds")
                        or payload.get("request_timeout_seconds")
                        or 0
                    )
                except (TypeError, ValueError):
                    request_timeout_seconds = 0.0
                if request_timeout_seconds <= 0:
                    request_timeout_seconds = None
                else:
                    request_timeout_seconds = min(max(request_timeout_seconds, 1.0), 15.0)
                try:
                    max_attempts = int(payload.get("maxAttempts") or payload.get("max_attempts") or 0)
                except (TypeError, ValueError):
                    max_attempts = 0
                max_attempts = min(max(max_attempts, 0), 3) or None
                window = cafe24_poll_datetime_window(
                    start_raw=str(payload.get("startDate") or ""),
                    end_raw=str(payload.get("endDate") or ""),
                    last_poll_at=str(integration["last_poll_at"] or ""),
                    use_cursor=env_flag(payload.get("useCursor") or payload.get("use_cursor")),
                    overlap_minutes=overlap_minutes,
                )
                requested_statuses = payload.get("statuses")
                if isinstance(requested_statuses, str):
                    status_filter = [status.strip() for status in requested_statuses.split(",") if status.strip()]
                elif isinstance(requested_statuses, list):
                    status_filter = [str(status).strip() for status in requested_statuses if str(status).strip()]
                else:
                    status_filter = None
                start_date = window["start"]
                end_date = window["end"]
                try:
                    page_limit = int(payload.get("pageLimit") or CAFE24_ORDER_PAGE_LIMIT)
                except (TypeError, ValueError):
                    page_limit = CAFE24_ORDER_PAGE_LIMIT
                page_limit = min(max(page_limit, 1), CAFE24_ORDER_PAGE_LIMIT)
                try:
                    max_pages = int(payload.get("maxPages") or CAFE24_ORDER_MAX_PAGES)
                except (TypeError, ValueError):
                    max_pages = CAFE24_ORDER_MAX_PAGES
                max_pages = min(max(max_pages, 1), CAFE24_ORDER_MAX_PAGES)
                try:
                    detail_fetch_limit = int(payload.get("detailFetchLimit") if payload.get("detailFetchLimit") is not None else 200)
                except (TypeError, ValueError):
                    detail_fetch_limit = 200
                detail_fetch_limit = min(max(detail_fetch_limit, 0), 500)
                request_payload = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "orderStatuses": status_filter or "all",
                    "limit": page_limit,
                    "maxPages": max_pages,
                    "detailFetchLimit": detail_fetch_limit,
                    "overlapMinutes": overlap_minutes,
                    "requestTimeoutSeconds": request_timeout_seconds,
                    "maxAttempts": max_attempts,
                }
                requested_windows.append({"mallId": mall_id, "shopNo": shop_no, **request_payload})
                try:
                    orders_by_key: Dict[str, Dict[str, Any]] = {}
                    page_events: List[Dict[str, Any]] = []
                    detail_fetch_count = 0
                    detail_fetch_errors: List[str] = []
                    query_variants = [
                        {"dateType": "order_date", "paymentStatuses": None, "reason": "primary"},
                        {"dateType": "pay_date", "paymentStatuses": ["P", "A", "T"], "reason": "paid-date-fallback"},
                    ]
                    for variant_index, variant in enumerate(query_variants):
                        if variant_index > 0 and orders_by_key:
                            break
                        date_type = str(variant["dateType"])
                        payment_status_filter = variant["paymentStatuses"]
                        for page_index in range(max_pages):
                            offset = page_index * page_limit
                            response = self._cafe24_call_with_token_retry(
                                conn,
                                integration,
                                lambda client, selected_date_type=date_type, selected_payment_status_filter=payment_status_filter, selected_offset=offset: client.orders(
                                    start_date=start_date,
                                    end_date=end_date,
                                    statuses=status_filter,
                                    payment_statuses=selected_payment_status_filter,
                                    limit=page_limit,
                                    offset=selected_offset,
                                    date_type=selected_date_type,
                                ),
                                request_timeout_seconds=request_timeout_seconds,
                                max_attempts=max_attempts,
                            )
                            page_orders = cafe24_orders_from_payload(response)
                            page_events.append(
                                {
                                    "dateType": date_type,
                                    "paymentStatuses": payment_status_filter or "all",
                                    "reason": variant["reason"],
                                    "offset": offset,
                                    "count": len(page_orders),
                                }
                            )
                            for order_payload in page_orders:
                                order_id = cafe24_payload_value(order_payload, ("order_id", "order_no", "id"))
                                if (
                                    order_id
                                    and not cafe24_order_has_embedded_items(order_payload)
                                    and detail_fetch_count < detail_fetch_limit
                                ):
                                    try:
                                        detail_response = self._cafe24_call_with_token_retry(
                                            conn,
                                            integration,
                                            lambda client, selected_order_id=order_id: client.order(selected_order_id),
                                            request_timeout_seconds=request_timeout_seconds,
                                            max_attempts=max_attempts,
                                        )
                                        detail_orders = cafe24_orders_from_payload(detail_response)
                                        if detail_orders:
                                            order_payload = detail_orders[0]
                                            detail_fetch_count += 1
                                    except Exception as detail_exc:
                                        detail_fetch_errors.append(f"{order_id}: {str(detail_exc)[:200]}")
                                order_key = order_id or f"{date_type}:{offset}:{len(orders_by_key)}"
                                existing = orders_by_key.get(order_key)
                                if existing is None or (
                                    cafe24_order_has_embedded_items(order_payload)
                                    and not cafe24_order_has_embedded_items(existing)
                                ):
                                    orders_by_key[order_key] = order_payload
                            if len(page_orders) < page_limit:
                                break
                    orders = list(orders_by_key.values())
                    response_order_count += len(orders)
                    self._log_cafe24_event(
                        conn,
                        mall_id=mall_id,
                        shop_no=shop_no,
                        event_type="orders.poll",
                        status="success",
                        request_payload={**request_payload, "pages": page_events},
                        response_payload={
                            "orderCount": len(orders),
                            "pages": page_events,
                            "detailFetchCount": detail_fetch_count,
                            "detailFetchErrors": detail_fetch_errors,
                        },
                    )
                    query_pages.extend(page_events)
                    detail_fetch_total += detail_fetch_count
                    detail_fetch_error_count += len(detail_fetch_errors)
                    for order_payload in orders:
                        for index, item_payload in enumerate(cafe24_order_items_from_order(order_payload)):
                            result = self._process_cafe24_item(
                                conn,
                                integration=integration,
                                order_payload=order_payload,
                                item_payload=item_payload,
                                index=index,
                                submit_ready=submit_ready and bool(integration["auto_submit"]),
                                require_mapping_auto_dispatch=True,
                            )
                            processed += 1
                            if cafe24_status_needs_operator_action(result["status"]):
                                waiting += 1
                            elif cafe24_status_is_payment_blocked(result["status"]):
                                blocked += 1
                            elif result["status"] == "failed":
                                failed += 1
                            elif result.get("submitted"):
                                submitted += 1
                    conn.execute(
                        """
                        UPDATE cafe24_integrations
                        SET last_poll_at = ?, last_sync_status = ?, last_sync_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            now_iso(),
                            "success",
                            f"요청 {start_date}~{end_date} · Cafe24 {len(orders)}건 · 품주 {processed}개 저장",
                            now_iso(),
                            integration["id"],
                        ),
                    )
                    self._record_admin_audit(
                        conn,
                        actor=actor,
                        action="cafe24.orders_poll",
                        entity_type="cafe24_integration",
                        entity_id=integration["id"],
                        message=f"Cafe24 주문 수집: {mall_id}/{shop_no}",
                        metadata={"processed": processed, "waiting": waiting, "blocked": blocked, "submitted": submitted, "failed": failed},
                    )
                    conn.commit()
                except Exception as exc:
                    message = str(exc)
                    errors.append(f"{mall_id}/{shop_no}: {message}")
                    conn.execute(
                        """
                        UPDATE cafe24_integrations
                        SET last_sync_status = ?, last_sync_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        ("failed", message[:1000], now_iso(), integration["id"]),
                    )
                    self._log_cafe24_event(
                        conn,
                        mall_id=mall_id,
                        shop_no=shop_no,
                        event_type="orders.poll",
                        status="failed",
                        request_payload=request_payload,
                        response_payload={"orderCount": 0},
                        error_message=message,
                    )
                    conn.commit()
        summary = {
            "requestWindows": requested_windows,
            "responseOrderCount": response_order_count,
            "storedOrderItemCount": processed,
            "paymentBlockedCount": blocked,
            "reviewRequiredCount": waiting,
            "submitReadyCount": max(processed - waiting - blocked - failed, 0),
            "submittedCount": submitted,
            "failedCount": failed,
            "queryPages": query_pages,
            "detailFetchCount": detail_fetch_total,
            "detailFetchErrorCount": detail_fetch_error_count,
        }
        return {
            "processed": processed,
            "waitingInput": waiting,
            "blocked": blocked,
            "submitted": submitted,
            "failed": failed,
            "errors": errors,
            "summary": summary,
        }

    def resync_cafe24_order_by_id(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        integration_id = str(payload.get("integrationId") or "").strip()
        order_id = str(payload.get("orderId") or payload.get("cafe24OrderId") or "").strip()
        submit_ready = bool(payload.get("submitReady", False))
        actor = self._admin_actor(payload)
        if not order_id:
            raise PanelError("재수집할 Cafe24 주문번호를 입력해 주세요.", status=400)
        processed = 0
        waiting = 0
        blocked = 0
        submitted = 0
        failed = 0
        errors: List[str] = []
        response_order_count = 0
        with self._connect() as conn:
            integration = self._cafe24_integration_row(conn, integration_id)
            mall_id = str(integration["mall_id"])
            shop_no = int(integration["shop_no"] or CAFE24_DEFAULT_SHOP_NO)
            request_payload = {"orderId": order_id, "embed": "items,buyer,receivers"}
            try:
                response = self._cafe24_call_with_token_retry(
                    conn,
                    integration,
                    lambda client: client.order(order_id),
                )
                orders = cafe24_orders_from_payload(response)
                response_order_count = len(orders)
                self._log_cafe24_event(
                    conn,
                    mall_id=mall_id,
                    shop_no=shop_no,
                    event_type="orders.resync_by_id",
                    status="success",
                    request_payload=request_payload,
                    response_payload={"orderCount": len(orders)},
                )
                for order_payload in orders:
                    for index, item_payload in enumerate(cafe24_order_items_from_order(order_payload)):
                        result = self._process_cafe24_item(
                            conn,
                            integration=integration,
                            order_payload=order_payload,
                            item_payload=item_payload,
                            index=index,
                            submit_ready=submit_ready and bool(integration["auto_submit"]),
                            require_mapping_auto_dispatch=True,
                        )
                        processed += 1
                        if cafe24_status_needs_operator_action(result["status"]):
                            waiting += 1
                        elif cafe24_status_is_payment_blocked(result["status"]):
                            blocked += 1
                        elif result["status"] == "failed":
                            failed += 1
                        elif result.get("submitted"):
                            submitted += 1
                conn.execute(
                    """
                    UPDATE cafe24_integrations
                    SET last_sync_status = ?, last_sync_message = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "success",
                        f"주문번호 {order_id} 재수집 · Cafe24 {len(orders)}건 · 품주 {processed}개 저장",
                        now_iso(),
                        integration["id"],
                    ),
                )
                self._record_admin_audit(
                    conn,
                    actor=actor,
                    action="cafe24.orders_resync_by_id",
                    entity_type="cafe24_integration",
                    entity_id=integration["id"],
                    message=f"Cafe24 주문번호 직접 재수집: {order_id}",
                    metadata={"orderId": order_id, "processed": processed, "waiting": waiting, "blocked": blocked, "submitted": submitted, "failed": failed},
                )
                conn.commit()
            except Exception as exc:
                message = str(exc)
                errors.append(f"{mall_id}/{shop_no}: {message}")
                conn.execute(
                    """
                    UPDATE cafe24_integrations
                    SET last_sync_status = ?, last_sync_message = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    ("failed", message[:1000], now_iso(), integration["id"]),
                )
                self._log_cafe24_event(
                    conn,
                    mall_id=mall_id,
                    shop_no=shop_no,
                    event_type="orders.resync_by_id",
                    status="failed",
                    request_payload=request_payload,
                    response_payload={"orderCount": 0},
                    error_message=message,
                )
                conn.commit()
        return {
            "processed": processed,
            "waitingInput": waiting,
            "blocked": blocked,
            "submitted": submitted,
            "failed": failed,
            "errors": errors,
            "summary": {
                "requestWindows": [{"mallId": mall_id, "shopNo": shop_no, **request_payload}],
                "responseOrderCount": response_order_count,
                "storedOrderItemCount": processed,
                "paymentBlockedCount": blocked,
                "reviewRequiredCount": waiting,
                "submitReadyCount": max(processed - waiting - blocked - failed, 0),
                "submittedCount": submitted,
                "failedCount": failed,
            },
        }

    def retry_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        item_id = str(payload.get("itemId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not item_id:
            raise PanelError("재처리할 Cafe24 주문 품주를 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            integration = conn.execute(
                "SELECT * FROM cafe24_integrations WHERE mall_id = ? AND shop_no = ?",
                (row["mall_id"], row["shop_no"]),
            ).fetchone()
            if integration is None:
                raise PanelError("Cafe24 연동 정보를 찾을 수 없습니다.", status=404)
            raw_payload = parse_json(row["raw_payload_json"], {})
            order_payload = raw_payload.get("order") if isinstance(raw_payload.get("order"), dict) else {}
            item_payload = raw_payload.get("item") if isinstance(raw_payload.get("item"), dict) else {}
            if not order_payload or not item_payload:
                raise PanelError("원본 Cafe24 payload가 없어 재처리할 수 없습니다.")
            conn.execute(
                "UPDATE cafe24_order_items SET retry_count = COALESCE(retry_count, 0) + 1, updated_at = ? WHERE id = ?",
                (now_iso(), item_id),
            )
            result = self._process_cafe24_item(
                conn,
                integration=integration,
                order_payload=order_payload,
                item_payload=item_payload,
                index=0,
                submit_ready=True,
                require_mapping_auto_dispatch=False,
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.order_item_retry",
                entity_type="cafe24_order_item",
                entity_id=item_id,
                message="Cafe24 주문 품주 수동 재처리",
                metadata=result,
            )
            conn.commit()
        return {"result": result}

    def dispatch_single_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        selector = cafe24_order_item_selector_for_panel(payload, default_shop_no=CAFE24_DEFAULT_SHOP_NO)
        expected_quantity = cafe24_expected_quantity_from_payload_for_panel(payload)
        allow_mapping_update = bool(payload.get("allowExpectedQuantityMappingUpdate") or payload.get("allow_expected_quantity_mapping_update"))
        allow_cancelled_redispatch = bool(payload.get("allowCanceledSupplierRedispatch") or payload.get("allow_cancelled_supplier_redispatch"))

        with self._connect() as conn:
            item_id = cafe24_order_item_id_for_panel(conn, selector)

        retry_result = self.retry_cafe24_order_item({"itemId": item_id, "_adminActor": self._admin_actor(payload)})
        mapping_updated = False

        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            normalized_fields = parse_json(row["normalized_fields_json"], {})
            supplier_payload = parse_json(row["supplier_payload_json"], {})
            quantity = cafe24_preflight_quantity(normalized_fields, supplier_payload)
            if expected_quantity and quantity != expected_quantity:
                mapping_id = str(row["mapping_id"] or "").strip()
                if allow_mapping_update and mapping_id:
                    mapping_row = conn.execute("SELECT * FROM cafe24_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone()
                    if mapping_row is not None and (
                        str(mapping_row["cafe24_variant_code"] or "").strip()
                        or str(mapping_row["cafe24_custom_product_code"] or "").strip()
                    ):
                        field_mapping = parse_json(mapping_row["field_mapping_json"], {})
                        field_mapping["orderedCount"] = {"source": "fixed", "value": str(expected_quantity)}
                        conn.execute(
                            "UPDATE cafe24_supplier_mappings SET field_mapping_json = ?, updated_at = ? WHERE id = ?",
                            (as_json(field_mapping), now_iso(), mapping_id),
                        )
                        conn.commit()
                        mapping_updated = True
                    else:
                        raise PanelError(
                            "Cafe24 옵션 수량 자동 보정은 품목코드 또는 자체상품코드 단위 매핑에서만 허용됩니다.",
                            status=409,
                        )
                if mapping_updated:
                    retry_result = self.retry_cafe24_order_item({"itemId": item_id, "_adminActor": self._admin_actor(payload)})
                    row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
                    normalized_fields = parse_json(row["normalized_fields_json"], {}) if row is not None else {}
                    supplier_payload = parse_json(row["supplier_payload_json"], {}) if row is not None else {}
                    quantity = cafe24_preflight_quantity(normalized_fields, supplier_payload)
                if expected_quantity and quantity != expected_quantity:
                    raise PanelError(
                        f"Cafe24 옵션 수량 검증 실패: 예상 {expected_quantity}명, 변환 {quantity}명입니다. 발주를 중단했습니다.",
                        status=409,
                    )
            if allow_cancelled_redispatch and str(row["supplier_order_uuid"] or "").strip():
                current_status = str(row["standard_status"] or "").strip()
                response_json = parse_json(row["supplier_response_json"], {})
                response_text = json.dumps(response_json, ensure_ascii=False).lower() if isinstance(response_json, dict) else str(response_json).lower()
                if current_status not in {"failed", "cancelled"} and "canceled" not in response_text and "cancelled" not in response_text:
                    raise PanelError("취소/실패로 확인된 공급사 주문만 재발주할 수 있습니다.", status=409)
                conn.execute(
                    """
                    UPDATE cafe24_order_items
                    SET supplier_order_id = '', supplier_order_uuid = '', standard_status = 'ready_to_submit',
                        error_message = '', automation_error_code = '', next_retry_at = '', updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso(), item_id),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if str(row["payment_gate_status"] or "") != "payment_confirmed":
                raise PanelError("Cafe24 결제완료가 확인되지 않아 발주할 수 없습니다.")
            if str(row["standard_status"] or "") != "ready_to_submit":
                raise PanelError(
                    f"재검증 후 발주 가능 상태가 아닙니다: {row['standard_status']} · {row['error_message']}",
                    status=409,
                )

        dispatch_result = self.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": self._admin_actor(payload)})
        return {
            "itemId": item_id,
            "retry": retry_result,
            "dispatch": dispatch_result,
            "expectedQuantity": expected_quantity,
            "normalizedQuantity": quantity,
            "mappingUpdated": mapping_updated,
        }

    def preflight_single_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        selector = cafe24_order_item_selector_for_panel(payload, default_shop_no=CAFE24_DEFAULT_SHOP_NO)
        expected_quantity = cafe24_expected_quantity_from_payload_for_panel(payload)

        with self._connect() as conn:
            item_id = cafe24_order_item_id_for_panel(conn, selector)
            row = conn.execute(
                """
                SELECT
                    coi.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name
                FROM cafe24_order_items coi
                LEFT JOIN products p ON p.id = coi.product_id
                WHERE coi.id = ?
                """,
                (item_id,),
            ).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            item = self._cafe24_order_item_payload(row)
            normalized_fields = parse_json(row["normalized_fields_json"], {})
            supplier_payload = parse_json(row["supplier_payload_json"], {})
            readiness = {"ok": False, "code": "supplier_missing", "message": "공급사 매핑이 없습니다."}
            if str(row.get("supplier_id") or "").strip():
                readiness = self._supplier_auto_dispatch_readiness(
                    conn,
                    supplier_id=str(row["supplier_id"]),
                    supplier_service_id=str(row.get("supplier_service_id") or ""),
                )

        return build_cafe24_order_item_preflight(
            item_id=item_id,
            item=item,
            normalized_fields=normalized_fields,
            supplier_payload=supplier_payload,
            readiness=readiness,
            expected_quantity=expected_quantity,
            checked_at=now_iso(),
        )

    def check_single_cafe24_supplier_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        selector = cafe24_order_item_selector_for_panel(
            payload,
            default_shop_no=CAFE24_DEFAULT_SHOP_NO,
            required_message="Cafe24 주문 품주 식별값이 필요합니다.",
        )
        actor = self._admin_actor(payload)

        with self._connect() as conn:
            item_id = cafe24_order_item_id_for_panel(conn, selector)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    coi.*,
                    s.api_url,
                    s.integration_type,
                    s.api_key,
                    s.bearer_token,
                    s.name AS supplier_name
                FROM cafe24_order_items coi
                JOIN suppliers s ON s.id = coi.supplier_id
                WHERE coi.id = ?
                """,
                (item_id,),
            ).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            external_order_id = str(row["supplier_order_uuid"] or "").strip()
            if not external_order_id:
                raise PanelError("공급사 주문번호가 없어 상태 조회가 불가합니다.", status=409)

        timestamp = now_iso()
        try:
            client = SupplierApiClient(
                str(row["api_url"]),
                decrypt_secret_value(row["api_key"]),
                integration_type=str(row["integration_type"]),
                bearer_token=decrypt_secret_value(row["bearer_token"]),
            )
            status_payload = client.status(external_order_id)
            supplier_status = normalize_supplier_order_status_payload(status_payload)
            cafe24_status = self._supplier_status_to_cafe24_status(supplier_status)
            response_json = parse_json(row["supplier_response_json"], {})
            response_json["lastStatusCheck"] = {"checkedAt": timestamp, "payload": status_payload}
            message = ""
            if isinstance(status_payload, dict):
                message = str(status_payload.get("error") or status_payload.get("message") or "").strip()
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE cafe24_order_items
                    SET standard_status = ?, supplier_response_json = ?, error_message = ?,
                        automation_last_checked_at = ?, automation_error_code = '',
                        cafe24_completion_status = CASE
                            WHEN ? = 'completed' AND cafe24_completion_status <> 'done' THEN 'pending'
                            ELSE cafe24_completion_status
                        END,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        cafe24_status,
                        as_json(redact_external_payload(response_json)),
                        message[:1000],
                        timestamp,
                        supplier_status,
                        timestamp,
                        item_id,
                    ),
                )
                self._log_cafe24_event(
                    conn,
                    mall_id=str(row["mall_id"]),
                    shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                    event_type="supplier.status_single",
                    status="success",
                    request_payload={"supplierOrderUuid": external_order_id},
                    response_payload=redact_external_payload(status_payload),
                    error_message=message,
                )
                self._record_admin_audit(
                    conn,
                    actor=actor,
                    action="cafe24.order_item_supplier_status",
                    entity_type="cafe24_order_item",
                    entity_id=item_id,
                    message=f"Cafe24 품주 공급사 상태 조회: {supplier_status}",
                    metadata={"supplierOrderUuid": external_order_id, "supplierStatus": supplier_status},
                )
                conn.commit()
            return {
                "itemId": item_id,
                "supplierOrderUuid": external_order_id,
                "supplierStatus": supplier_status,
                "cafe24Status": cafe24_status,
                "message": message,
                "statusPayload": redact_external_payload(status_payload),
                "checkedAt": timestamp,
            }
        except Exception as exc:
            error_message = str(exc)
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE cafe24_order_items
                    SET automation_last_checked_at = ?, automation_error_code = ?,
                        error_message = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (timestamp, "supplier_status_check_failed", error_message[:1000], timestamp, item_id),
                )
                self._log_cafe24_event(
                    conn,
                    mall_id=str(row["mall_id"]),
                    shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                    event_type="supplier.status_single",
                    status="failed",
                    request_payload={"supplierOrderUuid": external_order_id},
                    response_payload={},
                    error_message=error_message,
                )
                self._record_admin_audit(
                    conn,
                    actor=actor,
                    action="cafe24.order_item_supplier_status_failed",
                    entity_type="cafe24_order_item",
                    entity_id=item_id,
                    message=f"Cafe24 품주 공급사 상태 조회 실패: {error_message[:160]}",
                    metadata={"supplierOrderUuid": external_order_id},
                )
                conn.commit()
            return {
                "itemId": item_id,
                "supplierOrderUuid": external_order_id,
                "supplierStatus": "check_failed",
                "cafe24Status": str(row["standard_status"] or ""),
                "message": error_message,
                "checkedAt": timestamp,
            }

    def dispatch_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        item_id = str(payload.get("itemId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not item_id:
            raise PanelError("발주할 Cafe24 주문 품주를 선택해 주세요.")

        dispatch_id = f"cafe24_sord_{uuid4().hex[:12]}"
        timestamp = now_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    coi.*,
                    s.name AS supplier_name,
                    s.api_url,
                    s.integration_type,
                    s.api_key,
                    s.bearer_token,
                    s.is_active AS supplier_is_active
                FROM cafe24_order_items coi
                LEFT JOIN suppliers s ON s.id = coi.supplier_id
                WHERE coi.id = ?
                """,
                (item_id,),
            ).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            request_payload = parse_json(row["supplier_payload_json"], {})
            try:
                dispatch_context = cafe24_dispatch_request_context(row, request_payload)
            except Cafe24DispatchRequestError as exc:
                raise PanelError(str(exc), status=exc.status) from exc
            if dispatch_context["duplicate"]:
                return dispatch_context["response"]
            request_payload = dispatch_context["requestPayload"]
            cursor = conn.execute(
                """
                UPDATE cafe24_order_items
                SET standard_status = ?, supplier_order_id = ?, error_message = ?,
                    retry_count = COALESCE(retry_count, 0) + 1,
                    automation_last_checked_at = ?, automation_error_code = '', next_retry_at = '',
                    updated_at = ?
                WHERE id = ?
                  AND supplier_order_uuid = ''
                  AND (
                    standard_status IN ('ready_to_submit', 'failed')
                    OR (standard_status = 'needs_manual_review' AND automation_error_code = 'supplier_token_expired')
                  )
                """,
                ("submitting", dispatch_id, "", timestamp, timestamp, item_id),
            )
            if cursor.rowcount != 1:
                raise PanelError("다른 요청에서 이미 발주 처리 중입니다.")
            conn.commit()

        response_payload: Any = {}
        supplier_external_order_id = ""
        next_status = "failed"
        error_message = ""
        try:
            api_key = decrypt_secret_value(row["api_key"])
            bearer_token = decrypt_secret_value(row.get("bearer_token") or "")
            client = SupplierApiClient(
                str(row["api_url"]),
                api_key,
                integration_type=str(row.get("integration_type") or SUPPLIER_INTEGRATION_CLASSIC),
                bearer_token=bearer_token,
            )
            response_payload = client.order(request_payload)
            outcome = cafe24_supplier_dispatch_outcome(response_payload)
            supplier_external_order_id = outcome["supplierExternalOrderId"]
            next_status = outcome["status"]
            error_message = outcome["errorMessage"]
        except Exception as exc:
            response_payload = {"error": str(exc)}
            error_message = str(exc)
            next_status = "failed"

        attempts_after = int(row["retry_count"] or 0) + 1
        next_retry_at = ""
        automation_error_code = ""
        supplier_auth_failed = supplier_error_is_auth_failure(
            error_message,
            integration_type=str(row.get("integration_type") or ""),
        )
        dispatch_state = cafe24_supplier_dispatch_state(
            {"status": next_status, "errorMessage": error_message},
            supplier_auth_failed=supplier_auth_failed,
            attempts_after=attempts_after,
            max_attempts=AUTOMATION_RETRY_MAX_ATTEMPTS,
            retry_at=automation_retry_at(attempts_after),
        )
        next_status = dispatch_state["status"]
        error_message = dispatch_state["errorMessage"]
        automation_error_code = dispatch_state["automationErrorCode"]
        next_retry_at = dispatch_state["nextRetryAt"]

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE cafe24_order_items
                SET standard_status = ?, supplier_order_uuid = ?, supplier_response_json = ?,
                    error_message = ?, automation_error_code = ?, next_retry_at = ?,
                    last_submitted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_status,
                    supplier_external_order_id,
                    as_json(redact_external_payload(response_payload)),
                    error_message,
                    automation_error_code,
                    next_retry_at,
                    now_iso(),
                    now_iso(),
                    item_id,
                ),
            )
            if supplier_auth_failed and str(row.get("supplier_id") or "").strip():
                conn.execute(
                    """
                    UPDATE suppliers
                    SET health_status = ?, health_message = ?, health_checked_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "failed",
                        (error_message or "공급사 인증 토큰이 만료되었습니다.")[:1000],
                        now_iso(),
                        now_iso(),
                        str(row["supplier_id"]),
                    ),
                )
            self._log_cafe24_event(
                conn,
                mall_id=str(row["mall_id"]),
                shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                event_type="supplier.dispatch",
                status="success" if next_status == "supplier_submitted" else "failed",
                request_payload=redact_external_payload(request_payload),
                response_payload=redact_external_payload(response_payload),
                error_message=error_message,
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.order_item_dispatch",
                entity_type="cafe24_order_item",
                entity_id=item_id,
                message=f"Cafe24 주문 품주 공급사 발주: {next_status}",
                metadata={
                    "supplierOrderId": dispatch_id,
                    "supplierOrderUuid": supplier_external_order_id,
                    "status": next_status,
                },
            )
            conn.commit()
        return {
            "id": item_id,
            "status": next_status,
            "submitted": next_status == "supplier_submitted",
            "supplierOrderId": dispatch_id,
            "supplierOrderUuid": supplier_external_order_id,
            "errorMessage": error_message,
        }

    def resync_cafe24_order_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        item_id = str(payload.get("itemId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not item_id:
            raise PanelError("재동기화할 Cafe24 주문 품주를 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            integration = conn.execute(
                "SELECT * FROM cafe24_integrations WHERE mall_id = ? AND shop_no = ?",
                (row["mall_id"], row["shop_no"]),
            ).fetchone()
            if integration is None:
                raise PanelError("Cafe24 연동 정보를 찾을 수 없습니다.", status=404)
            response = self._cafe24_call_with_token_retry(
                conn,
                integration,
                lambda client: client.order(row["cafe24_order_id"]),
            )
            orders = cafe24_orders_from_payload(response)
            if not orders:
                raise PanelError("Cafe24 주문 상세 응답이 비어 있습니다.")
            result = None
            for order_payload in orders:
                for index, item_payload in enumerate(cafe24_order_items_from_order(order_payload)):
                    identity = cafe24_item_identity(order_payload, item_payload, index)
                    if identity["orderItemCode"] != row["cafe24_order_item_code"]:
                        continue
                    result = self._process_cafe24_item(
                        conn,
                        integration=integration,
                        order_payload=order_payload,
                        item_payload=item_payload,
                        index=index,
                        submit_ready=bool(integration["auto_submit"]),
                        require_mapping_auto_dispatch=True,
                    )
                    break
            if result is None:
                raise PanelError("Cafe24 주문 상세에서 해당 품주를 찾지 못했습니다.")
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.order_item_resync",
                entity_type="cafe24_order_item",
                entity_id=item_id,
                message="Cafe24 주문 품주 재동기화",
                metadata=result,
            )
            conn.commit()
        return {"result": result}

    def _cafe24_manual_input_plan(self, conn: DatabaseConnection, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = cafe24_manual_input_request_for_panel(payload, default_shop_no=CAFE24_DEFAULT_SHOP_NO)
        selector = request["selector"]
        item_id = str(request["itemId"])
        supplier_id = str(request["supplierId"])
        supplier_service_id = str(request["supplierServiceId"])
        fields = request["fields"]
        item_id = cafe24_order_item_id_for_panel(conn, selector)
        row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        cafe24_validate_manual_input_order_item_for_panel(row)

        supplier_row = conn.execute(
            "SELECT * FROM suppliers WHERE id = ?",
            (supplier_id,),
        ).fetchone()
        service_row = conn.execute(
            """
            SELECT *
            FROM supplier_services
            WHERE id = ? AND supplier_id = ?
            """,
            (supplier_service_id, supplier_id),
        ).fetchone()
        cafe24_validate_manual_input_supplier_for_panel(supplier_row, service_row)

        product_row = None
        if str(row.get("product_id") or "").strip():
            product_row = conn.execute(
                """
                SELECT p.product_code, p.name, ps.slug AS platform_slug
                FROM products p
                JOIN product_categories pc ON pc.id = p.product_category_id
                JOIN platform_groups pg ON pg.id = pc.platform_group_id
                JOIN platform_sections ps ON ps.id = pg.platform_section_id
                WHERE p.id = ?
                """,
                (row["product_id"],),
            ).fetchone()
        return build_cafe24_manual_input_plan_payload(
            item_id=item_id,
            item_row=row,
            supplier_row=supplier_row,
            service_row=service_row,
            supplier_id=supplier_id,
            supplier_service_id=supplier_service_id,
            fields=fields,
            product_row=product_row,
            validate_direct_fields=self._validate_cafe24_direct_fields,
            build_supplier_order_payload=self._build_supplier_order_payload,
        )

    def preview_cafe24_order_item_manual_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        expected_quantity = cafe24_expected_quantity_from_payload_for_panel(payload)
        expected_quantity = cafe24_manual_expected_quantity_for_panel(payload, expected_quantity)

        with self._connect() as conn:
            plan = self._cafe24_manual_input_plan(conn, payload)
            row = plan["row"]
            item = self._cafe24_order_item_payload(row)
            fields = plan["fields"]
            supplier_payload = plan["supplierPayload"]
            item.update(
                {
                    "standardStatus": "ready_to_submit",
                    "supplierId": plan["supplierId"],
                    "supplierServiceId": plan["supplierServiceId"],
                    "supplierExternalServiceId": plan["supplierExternalServiceId"],
                    "normalizedFields": fields,
                    "supplierPayload": supplier_payload,
                    "errorMessage": "",
                    "automationErrorCode": "",
                    "targetDiagnostics": cafe24_target_diagnostics(
                        fields,
                        supplier_payload,
                        standard_status="ready_to_submit",
                    ),
                }
            )
            readiness = self._supplier_auto_dispatch_readiness(
                conn,
                supplier_id=plan["supplierId"],
                supplier_service_id=plan["supplierServiceId"],
            )

        preflight = build_cafe24_order_item_preflight(
            item_id=plan["itemId"],
            item=item,
            normalized_fields=fields,
            supplier_payload=supplier_payload,
            readiness=readiness,
            expected_quantity=expected_quantity,
            checked_at=now_iso(),
        )
        return build_cafe24_manual_input_preview_response(
            item_id=plan["itemId"],
            preflight=preflight,
            supplier_id=plan["supplierId"],
            supplier_service_id=plan["supplierServiceId"],
            supplier_external_service_id=plan["supplierExternalServiceId"],
            normalized_fields=fields,
            supplier_payload=supplier_payload,
            redactor=redact_cafe24_preview_value,
        )

    def save_cafe24_order_item_manual_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._admin_actor(payload)
        timestamp = now_iso()
        approve_auto_dispatch = env_flag(
            payload.get("approveAutoDispatch")
            or payload.get("approve_auto_dispatch")
            or payload.get("dispatchAfterSave")
            or payload.get("dispatch_after_save")
        )
        auto_dispatch_source = "manual_input" if approve_auto_dispatch else ""
        with self._connect() as conn:
            plan = self._cafe24_manual_input_plan(conn, payload)
            item_id = plan["itemId"]
            supplier_id = plan["supplierId"]
            supplier_service_id = plan["supplierServiceId"]
            fields = plan["fields"]
            supplier_payload = plan["supplierPayload"]

            conn.execute(
                """
                UPDATE cafe24_order_items
                SET supplier_id = ?, supplier_service_id = ?, supplier_external_service_id = ?,
                    normalized_fields_json = ?, supplier_payload_json = ?,
                    standard_status = 'ready_to_submit', error_message = '',
                    automation_error_code = '', next_retry_at = '',
                    auto_dispatch_approved = ?, auto_dispatch_source = ?,
                    preflight_checked_at = '', preflight_blockers_json = '[]',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    supplier_id,
                    supplier_service_id,
                    plan["supplierExternalServiceId"],
                    as_json(fields),
                    as_json(supplier_payload),
                    1 if approve_auto_dispatch else 0,
                    auto_dispatch_source,
                    timestamp,
                    item_id,
                ),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.order_item_manual_input",
                entity_type="cafe24_order_item",
                entity_id=item_id,
                message="Cafe24 주문 품주 수동 보정 저장",
                metadata={
                    "supplierId": supplier_id,
                    "supplierServiceId": supplier_service_id,
                    "payloadKeys": sorted(str(key) for key in supplier_payload.keys()),
                },
            )
            updated = conn.execute(
                """
                SELECT
                    coi.*,
                    p.name AS internal_product_name,
                    p.option_name AS internal_option_name
                FROM cafe24_order_items coi
                LEFT JOIN products p ON p.id = coi.product_id
                WHERE coi.id = ?
                """,
                (item_id,),
            ).fetchone()
            conn.commit()

        return {
            "item": self._cafe24_order_item_payload(updated),
            "normalizedFields": fields,
            "supplierPayload": supplier_payload,
        }

    def update_cafe24_order_item_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        item_id = str(payload.get("itemId") or payload.get("id") or "").strip()
        status = str(payload.get("status") or "").strip()
        memo = str(payload.get("memo") or "").strip()
        actor = self._admin_actor(payload)
        if not item_id:
            raise PanelError("처리할 Cafe24 주문 품주를 선택해 주세요.")
        if status not in CAFE24_STANDARD_STATUSES:
            raise PanelError("지원하지 않는 Cafe24 주문 상태입니다.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise PanelError("Cafe24 주문 품주를 찾을 수 없습니다.", status=404)
            conn.execute(
                "UPDATE cafe24_order_items SET standard_status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status, memo, now_iso(), item_id),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="cafe24.order_item_status",
                entity_type="cafe24_order_item",
                entity_id=item_id,
                message=f"Cafe24 주문 품주 상태 변경: {status}",
                metadata={"memo": memo},
            )
            conn.commit()
        return {"ok": True, "itemId": item_id, "status": status}

    def list_supplier_services(self, supplier_id: str, search: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            supplier = conn.execute("SELECT id, name, integration_type FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
            if supplier is None:
                raise PanelError("공급사를 찾을 수 없습니다.", status=404)

            query = """
                SELECT *
                FROM supplier_services
                WHERE supplier_id = ? AND is_active = 1
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

    def _supplier_service_payload(self, row: Dict[str, Any], integration_type: str) -> Dict[str, Any]:
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
            "isActive": bool(row["is_active"]),
            "syncedAt": row["synced_at"],
            "lastSeenAt": row["last_seen_at"],
            "removedAt": row["removed_at"],
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

    def get_mkt24_product_setting(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("supplierId") or "").strip()
        product_uuid = str(payload.get("productUuid") or "").strip()
        refresh = bool(payload.get("refresh", False))
        if not supplier_id or not product_uuid:
            raise PanelError("MKT24 공급사와 상품을 선택해 주세요.")

        with self._connect() as conn:
            row = self._mkt24_product_setting_row(conn, supplier_id, product_uuid)
            if row is not None and not refresh:
                return {"setting": self._mkt24_product_setting_payload(row)}

        return self.sync_mkt24_product_detail(
            {
                "supplierId": supplier_id,
                "productUuid": product_uuid,
                "_adminActor": payload.get("_adminActor") or "admin",
            }
        )

    def sync_mkt24_product_detail(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("supplierId") or "").strip()
        product_uuid = str(payload.get("productUuid") or "").strip()
        actor = self._admin_actor(payload)
        if not supplier_id or not product_uuid:
            raise PanelError("MKT24 공급사와 상품을 선택해 주세요.")

        supplier = self._supplier_by_id(supplier_id, include_api_key=True)
        if normalize_supplier_integration_type(supplier["integrationType"]) != SUPPLIER_INTEGRATION_MKT24:
            raise PanelError("MKT24 공급사에서만 상품 상세를 조회할 수 있습니다.")

        client = SupplierApiClient(
            supplier["apiUrl"],
            supplier["apiKey"],
            integration_type=supplier["integrationType"],
            bearer_token=supplier.get("bearerToken") or "",
        )
        detail_payload = client.mkt24_product_detail(product_uuid)
        detail = mkt24_detail_data(detail_payload)
        if not detail:
            raise PanelError("MKT24 상품 상세 응답 형식이 올바르지 않습니다.")

        timestamp = now_iso()
        detail_product_uuid = str(detail.get("productUuid") or product_uuid).strip()
        with self._connect() as conn:
            service = conn.execute(
                """
                SELECT id, external_service_id, name, type
                FROM supplier_services
                WHERE supplier_id = ? AND external_service_id = ?
                LIMIT 1
                """,
                (supplier_id, detail_product_uuid),
            ).fetchone()
            row = self._mkt24_product_setting_row(conn, supplier_id, detail_product_uuid)
            existing_field_config = parse_json(row["field_config_json"], {}) if row is not None else {}
            existing_option_config = parse_json(row["option_config_json"], {}) if row is not None else {}
            field_config = default_mkt24_field_config(detail, existing_field_config)
            option_config = default_mkt24_option_config(detail, existing_option_config)
            option_config = validate_mkt24_option_config(
                option_config,
                supports_order_options=bool(detail.get("supportsOrderOptions")),
            )
            values = (
                "mkt24",
                supplier_id,
                service["id"] if service is not None else "",
                detail_product_uuid,
                str(detail.get("productTypeName") or (service["type"] if service else "") or ""),
                str(detail.get("fullName") or detail.get("productName") or (service["name"] if service else "") or ""),
                str(detail.get("menuName") or detail.get("productName") or ""),
                as_json(detail),
                as_json(field_config),
                as_json(option_config),
                1 if row is None else int(row["is_active"]),
                timestamp,
                timestamp,
            )
            if row is None:
                setting_id = f"mkt24_set_{uuid4().hex[:14]}"
                conn.execute(
                    """
                    INSERT INTO mkt24_product_settings (
                        id, provider, supplier_id, supplier_service_id, product_uuid,
                        product_type_name, full_name, menu_name, detail_snapshot_json,
                        field_config_json, option_config_json, is_active, last_synced_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (setting_id, *values, timestamp),
                )
            else:
                setting_id = row["id"]
                conn.execute(
                    """
                    UPDATE mkt24_product_settings
                    SET provider = ?, supplier_id = ?, supplier_service_id = ?, product_uuid = ?,
                        product_type_name = ?, full_name = ?, menu_name = ?, detail_snapshot_json = ?,
                        field_config_json = ?, option_config_json = ?, is_active = ?,
                        last_synced_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, setting_id),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="mkt24.product_detail_sync",
                entity_type="mkt24_product_setting",
                entity_id=setting_id,
                message=f"MKT24 상품 상세 동기화: {detail_product_uuid}",
                metadata={"supplierId": supplier_id, "productUuid": detail_product_uuid},
            )
            conn.commit()
            refreshed = self._mkt24_product_setting_row(conn, supplier_id, detail_product_uuid)
        return {"setting": self._mkt24_product_setting_payload(refreshed)}

    def save_mkt24_product_setting(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("supplierId") or "").strip()
        product_uuid = str(payload.get("productUuid") or "").strip()
        supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
        is_active = bool(payload.get("isActive", True))
        field_config = payload.get("fieldConfig") if isinstance(payload.get("fieldConfig"), dict) else {}
        option_config = payload.get("optionConfig") if isinstance(payload.get("optionConfig"), dict) else {}
        actor = self._admin_actor(payload)
        if not supplier_id or not product_uuid:
            raise PanelError("저장할 MKT24 상품 설정을 선택해 주세요.")

        timestamp = now_iso()
        with self._connect() as conn:
            supplier = conn.execute(
                "SELECT id, integration_type FROM suppliers WHERE id = ?",
                (supplier_id,),
            ).fetchone()
            if supplier is None or normalize_supplier_integration_type(supplier["integration_type"]) != SUPPLIER_INTEGRATION_MKT24:
                raise PanelError("MKT24 공급사를 선택해 주세요.")
            service = conn.execute(
                """
                SELECT id, external_service_id
                FROM supplier_services
                WHERE supplier_id = ? AND id = ? AND is_active = 1
                LIMIT 1
                """,
                (supplier_id, supplier_service_id),
            ).fetchone()
            if service is None:
                raise PanelError("MKT24 공급사 서비스를 선택해 주세요.")
            if str(service["external_service_id"]) != product_uuid:
                raise PanelError("선택한 서비스와 MKT24 상품 UUID가 일치하지 않습니다.")

            row = self._mkt24_product_setting_row(conn, supplier_id, product_uuid)
            if row is None:
                raise PanelError("먼저 MKT24 상품 상세를 불러와 주세요.")
            detail = parse_json(row["detail_snapshot_json"], {})
            if not isinstance(detail, dict) or not detail:
                raise PanelError("MKT24 상품 상세 snapshot이 없습니다. 다시 불러온 뒤 저장해 주세요.")

            normalized_field_config = self._normalize_mkt24_field_config(detail, field_config)
            normalized_option_config = validate_mkt24_option_config(
                option_config,
                supports_order_options=bool(detail.get("supportsOrderOptions")),
            )
            self._build_mkt24_order_payload_from_setting(
                detail,
                normalized_field_config,
                normalized_option_config,
                {},
                for_preview=True,
            )
            conn.execute(
                """
                UPDATE mkt24_product_settings
                SET supplier_service_id = ?, field_config_json = ?, option_config_json = ?,
                    is_active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    supplier_service_id,
                    as_json(normalized_field_config),
                    as_json(normalized_option_config),
                    bool_to_int(is_active),
                    timestamp,
                    row["id"],
                ),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="mkt24.product_setting_update",
                entity_type="mkt24_product_setting",
                entity_id=row["id"],
                message=f"MKT24 주문 옵션 설정 저장: {product_uuid}",
                metadata={"supplierId": supplier_id, "supplierServiceId": supplier_service_id, "isActive": is_active},
            )
            conn.commit()
            saved = self._mkt24_product_setting_row(conn, supplier_id, product_uuid)
        return {"setting": self._mkt24_product_setting_payload(saved)}

    def _mkt24_product_setting_row(
        self,
        conn: DatabaseConnection,
        supplier_id: str,
        product_uuid: str,
    ) -> Optional[Dict[str, Any]]:
        return conn.execute(
            """
            SELECT *
            FROM mkt24_product_settings
            WHERE supplier_id = ? AND product_uuid = ?
            LIMIT 1
            """,
            (supplier_id, product_uuid),
        ).fetchone()

    def _mkt24_product_setting_payload(self, row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if row is None:
            return {}
        detail = parse_json(row["detail_snapshot_json"], {})
        field_config = parse_json(row["field_config_json"], {})
        option_config = parse_json(row["option_config_json"], {})
        preview: Dict[str, Any] = {}
        preview_error = ""
        try:
            preview = self._build_mkt24_order_payload_from_setting(
                detail if isinstance(detail, dict) else {},
                field_config if isinstance(field_config, dict) else {},
                option_config if isinstance(option_config, dict) else {},
                {},
                for_preview=True,
            )
        except Exception as exc:
            preview_error = str(exc)
        return {
            "id": row["id"],
            "provider": row["provider"],
            "supplierId": row["supplier_id"],
            "supplierServiceId": row["supplier_service_id"],
            "productUuid": row["product_uuid"],
            "productTypeName": row["product_type_name"],
            "fullName": row["full_name"],
            "menuName": row["menu_name"],
            "detailSnapshot": detail if isinstance(detail, dict) else {},
            "fieldConfig": field_config if isinstance(field_config, dict) else {},
            "optionConfig": option_config if isinstance(option_config, dict) else {},
            "isActive": bool(row["is_active"]),
            "lastSyncedAt": row["last_synced_at"],
            "updatedAt": row["updated_at"],
            "payloadPreview": preview,
            "payloadPreviewError": preview_error,
        }

    def _normalize_mkt24_field_config(self, detail: Dict[str, Any], field_config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return normalize_mkt24_field_config(detail, field_config)
        except Mkt24SettingsError as exc:
            raise PanelError(str(exc)) from exc

    def _admin_actor(self, payload: Optional[Dict[str, Any]] = None) -> str:
        actor = str((payload or {}).get("_adminActor") or "").strip()
        return actor or "admin"

    def _record_admin_audit(
        self,
        conn: DatabaseConnection,
        *,
        actor: str = "admin",
        action: str,
        entity_type: str = "",
        entity_id: str = "",
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO admin_audit_logs (
                id, actor, action, entity_type, entity_id, message, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit_{uuid4().hex[:16]}",
                actor or "admin",
                action,
                entity_type,
                entity_id,
                message,
                as_json(metadata or {}),
                now_iso(),
            ),
        )

    def _admin_audit_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "actor": row["actor"],
            "action": row["action"],
            "entityType": row["entity_type"],
            "entityId": row["entity_id"],
            "message": row["message"],
            "metadata": parse_json(row["metadata_json"], {}),
            "createdAt": row["created_at"],
            "createdLabel": self._relative_date_label(row["created_at"]),
        }

    def _notice_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "body": row["body"],
            "tag": row["tag"],
            "pinned": bool(row["pinned"]),
            "publishedAt": row["published_at"],
        }

    def _faq_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "question": row["question"],
            "answer": row["answer"],
            "sortOrder": row["sort_order"],
        }

    def save_supplier(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        api_url = str(payload.get("apiUrl") or "").strip()
        integration_type = normalize_supplier_integration_type(payload.get("integrationType"))
        api_key = str(payload.get("apiKey") or "").strip()
        bearer_token = str(payload.get("bearerToken") or "").strip()
        notes = str(payload.get("notes") or "").strip()
        is_active = bool(payload.get("isActive", True))
        actor = self._admin_actor(payload)

        if not name:
            raise PanelError("공급사 이름을 입력해 주세요.")
        if not api_url:
            raise PanelError("API URL을 입력해 주세요.")
        if integration_type == SUPPLIER_INTEGRATION_MKT24:
            candidates = normalize_mkt24_candidates(api_url)
            api_url = candidates[0] if candidates else api_url
        elif integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            candidates = normalize_fasttraffic_candidates(api_url)
            api_url = candidates[0] if candidates else api_url

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
                    api_key = decrypt_secret_value(existing["api_key"])
            if integration_type == SUPPLIER_INTEGRATION_MKT24:
                if not api_key:
                    raise PanelError("MKT24 API Key를 입력해 주세요.")
                bearer_token = ""
            elif integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
                if not api_key:
                    raise PanelError("FastTraffic API Key를 입력해 주세요.")
                bearer_token = ""
            else:
                if not api_key:
                    raise PanelError("API 키를 입력해 주세요.")
                bearer_token = ""

            stored_api_key = encrypt_secret_value(api_key, require_key=_secret_encryption_required())
            stored_bearer_token = encrypt_secret_value(bearer_token, require_key=_secret_encryption_required())

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
                        stored_api_key,
                        stored_bearer_token,
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
                        stored_api_key,
                        stored_bearer_token,
                        bool_to_int(is_active),
                        notes,
                        timestamp,
                        timestamp,
                    ),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="supplier.update" if existing is not None else "supplier.create",
                entity_type="supplier",
                entity_id=supplier_id,
                message=f"공급사 저장: {name}",
                metadata={"integrationType": integration_type, "isActive": is_active},
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
        actor = self._admin_actor(payload)

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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="site.popup_update",
                entity_type="home_popup",
                entity_id=popup_id,
                message=f"홈 팝업 저장: {name}",
                metadata={"isActive": is_active, "route": route},
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
        actor = self._admin_actor(payload)

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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="site.banner_update",
                entity_type="home_banner",
                entity_id=banner_id,
                message=f"홈 배너 저장: {title}",
                metadata={"isActive": is_active, "route": route, "sortOrder": sort_order},
            )
            conn.commit()
        return {"banner": self._home_banner_by_id(banner_id)}

    def save_platform_section(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        platform_id = str(payload.get("id") or "").strip()
        icon = str(payload.get("icon") or "").strip() or "●"
        image_url = normalize_image_asset_source(payload.get("logoImageUrl") or "", "플랫폼 로고 이미지")
        accent_color = str(payload.get("accentColor") or "#4c76ff").strip() or "#4c76ff"
        actor = self._admin_actor(payload)

        if not platform_id:
            raise PanelError("수정할 플랫폼을 선택해 주세요.")
        if len(icon) > 6:
            raise PanelError("대체 아이콘은 6자 이하로 입력해 주세요.")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent_color):
            raise PanelError("강조 색상은 #RRGGBB 형식으로 입력해 주세요.")

        with self._connect() as conn:
            existing = conn.execute("SELECT id FROM platform_sections WHERE id = ?", (platform_id,)).fetchone()
            if existing is None:
                raise PanelError("수정할 플랫폼을 찾을 수 없습니다.", status=404)
            conn.execute(
                """
                UPDATE platform_sections
                SET icon = ?, image_url = ?, accent_color = ?
                WHERE id = ?
                """,
                (
                    icon,
                    image_url,
                    accent_color,
                    platform_id,
                ),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="site.platform_logo_update",
                entity_type="platform_section",
                entity_id=platform_id,
                message="플랫폼 로고/색상 저장",
                metadata={"hasImage": bool(image_url), "accentColor": accent_color},
            )
            conn.commit()
        return {"platformSection": self._platform_section_by_id(platform_id)}

    def save_site_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        site_name = str(payload.get("siteName") or "").strip()
        site_description = str(payload.get("siteDescription") or "").strip()
        use_mail_sms_site_name = bool(payload.get("useMailSmsSiteName", False))
        mail_sms_site_name = str(payload.get("mailSmsSiteName") or "").strip()
        header_logo_url = normalize_image_asset_source(payload.get("headerLogoUrl") or "", "상단 로고 이미지")
        favicon_url = normalize_image_asset_source(payload.get("faviconUrl") or "", "파비콘")
        share_image_url = normalize_image_asset_source(payload.get("shareImageUrl") or "", "대표 이미지")
        actor = self._admin_actor(payload)

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
                    header_logo_url = ?, favicon_url = ?, share_image_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    site_name,
                    site_description,
                    bool_to_int(use_mail_sms_site_name),
                    mail_sms_site_name,
                    header_logo_url,
                    favicon_url,
                    share_image_url,
                    timestamp,
                    existing["id"],
                ),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="site.settings_update",
                entity_type="site_settings",
                entity_id=existing["id"],
                message=f"사이트 기본 설정 저장: {site_name}",
                metadata={
                    "hasHeaderLogo": bool(header_logo_url),
                    "hasFavicon": bool(favicon_url),
                    "hasShareImage": bool(share_image_url),
                },
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
        if integration_type == SUPPLIER_INTEGRATION_MKT24:
            bearer_token = ""
        actor = self._admin_actor(payload)

        if not api_url:
            raise PanelError("API URL을 입력해 주세요.")
        if not api_key:
            label = "MKT24 API Key" if integration_type == SUPPLIER_INTEGRATION_MKT24 else "API 키"
            raise PanelError(f"{label}를 입력해 주세요.")

        result = self._run_supplier_connection_test(
            api_url,
            api_key,
            integration_type=integration_type,
            bearer_token=bearer_token,
        )

        if supplier_id:
            persisted_api_url = result.get("persistedApiUrl") or result["resolvedApiUrl"]
            stored_api_key = encrypt_secret_value(api_key, require_key=_secret_encryption_required())
            stored_bearer_token = encrypt_secret_value(
                "",
                require_key=_secret_encryption_required(),
            )
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
                        stored_api_key,
                        stored_bearer_token,
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
                self._record_admin_audit(
                    conn,
                    actor=actor,
                    action="supplier.connection_test",
                    entity_type="supplier",
                    entity_id=supplier_id,
                    message="공급사 API 연결 확인",
                    metadata={"status": result["status"], "serviceCount": result["serviceCount"]},
                )
                conn.commit()

        return {"result": result}

    def _acquire_supplier_service_sync_lock(self, supplier_id: str, *, force: bool = False) -> Dict[str, Any]:
        started_at = now_iso()
        lock_until = (
            dt.datetime.now().astimezone() + dt.timedelta(minutes=SUPPLIER_SERVICE_SYNC_LOCK_MINUTES)
        ).isoformat(timespec="seconds")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
            if row is None:
                raise PanelError("공급사를 찾을 수 없습니다.", status=404)
            if not bool(row["is_active"]):
                raise PanelError("비활성 공급사는 서비스 동기화를 실행할 수 없습니다.")
            active_lock = parse_iso_datetime(row.get("service_sync_lock_until"))
            if active_lock and active_lock > dt.datetime.now().astimezone():
                raise PanelError("이미 공급사 서비스 동기화가 진행 중입니다. 잠시 후 다시 시도해 주세요.", status=409)
            if not force and not supplier_service_sync_due(row):
                return {"acquired": False, "skipped": True, "supplier": self._supplier_by_id(supplier_id)}
            conn.execute(
                """
                UPDATE suppliers
                SET service_sync_status = 'syncing',
                    service_sync_message = '서비스 동기화 진행 중',
                    service_sync_started_at = ?,
                    service_sync_lock_until = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (started_at, lock_until, started_at, supplier_id),
            )
            conn.commit()
        return {"acquired": True, "skipped": False, "supplier": self._supplier_by_id(supplier_id, include_api_key=True)}

    def _mark_supplier_service_sync_failed(self, supplier_id: str, message: str, *, actor: str = "system") -> None:
        timestamp = now_iso()
        safe_message = str(message or "서비스 동기화에 실패했습니다.").strip()[:800]
        with self._connect() as conn:
            row = conn.execute(
                "SELECT service_sync_error_count FROM suppliers WHERE id = ?",
                (supplier_id,),
            ).fetchone()
            if row is None:
                return
            error_count = int(row["service_sync_error_count"] or 0) + 1
            conn.execute(
                """
                UPDATE suppliers
                SET service_sync_status = 'failed',
                    service_sync_message = ?,
                    service_sync_completed_at = ?,
                    service_sync_lock_until = '',
                    service_sync_error_count = ?,
                    last_test_status = 'failed',
                    last_test_message = ?,
                    last_checked_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (safe_message, timestamp, error_count, safe_message, timestamp, timestamp, supplier_id),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="supplier.services_sync_failed",
                entity_type="supplier",
                entity_id=supplier_id,
                message="공급사 서비스 동기화 실패",
                metadata={"error": safe_message, "errorCount": error_count},
            )
            conn.commit()

    def _sync_supplier_services_internal(
        self,
        supplier_id: str,
        *,
        actor: str = "admin",
        force: bool = True,
        request_timeout_seconds: Any = None,
    ) -> Dict[str, Any]:
        lock = self._acquire_supplier_service_sync_lock(supplier_id, force=force)
        if lock.get("skipped"):
            return {
                "supplier": lock["supplier"],
                "serviceCount": lock["supplier"].get("lastServiceCount", 0),
                "syncedAt": lock["supplier"].get("serviceSyncCompletedAt") or lock["supplier"].get("lastCheckedAt") or "",
                "skipped": True,
                "message": "최근 동기화 상태가 아직 유효합니다.",
            }

        supplier = lock["supplier"]
        try:
            result = self._run_supplier_connection_test(
                supplier["apiUrl"],
                supplier["apiKey"],
                integration_type=supplier["integrationType"],
                bearer_token=supplier.get("bearerToken") or "",
                require_services=True,
                request_timeout_seconds=request_timeout_seconds,
            )
            services_payload = result["servicesPayload"]
            if not isinstance(services_payload, list):
                raise PanelError("공급사 서비스 목록 형식이 올바르지 않습니다.")
        except Exception as exc:
            message = str(exc) if isinstance(exc, (PanelError, SupplierApiError)) else "서비스 동기화 중 오류가 발생했습니다."
            self._mark_supplier_service_sync_failed(supplier_id, message, actor=actor)
            raise

        synced_at = now_iso()
        seen_external_ids: List[str] = []
        unique_seen: set[str] = set()
        update_rows: List[Tuple[Any, ...]] = []
        insert_rows: List[Tuple[Any, ...]] = []

        with self._connect() as conn:
            existing_rows = conn.execute(
                "SELECT id, external_service_id FROM supplier_services WHERE supplier_id = ?",
                (supplier_id,),
            ).fetchall()
            existing_by_external_id = {
                str(row["external_service_id"]): str(row["id"])
                for row in existing_rows
            }
            for item in services_payload:
                if not isinstance(item, dict):
                    continue
                service_record = supplier_service_record(supplier["integrationType"], item)
                if service_record is None:
                    continue
                external_service_id = service_record["externalServiceId"]
                if external_service_id in unique_seen:
                    continue
                unique_seen.add(external_service_id)
                seen_external_ids.append(external_service_id)
                service_id = existing_by_external_id.get(external_service_id) or f"svc_{uuid4().hex[:12]}"
                if external_service_id in existing_by_external_id:
                    update_rows.append(
                        (
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
                            synced_at,
                            service_id,
                        )
                    )
                else:
                    insert_rows.append(
                        (
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
                            synced_at,
                        ),
                    )

            if update_rows:
                conn.executemany(
                    """
                    UPDATE supplier_services
                    SET name = ?, category = ?, type = ?, rate = ?, min_amount = ?, max_amount = ?,
                        dripfeed = ?, refill = ?, cancel = ?, is_active = 1, raw_json = ?,
                        synced_at = ?, last_seen_at = ?, removed_at = ''
                    WHERE id = ?
                    """,
                    update_rows,
                )
            if insert_rows:
                conn.executemany(
                    """
                    INSERT INTO supplier_services (
                        id, supplier_id, external_service_id, name, category, type, rate,
                        min_amount, max_amount, dripfeed, refill, cancel, is_active,
                        raw_json, synced_at, last_seen_at, removed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, '')
                    """,
                    insert_rows,
                )

            if seen_external_ids:
                placeholders = ",".join("?" for _ in seen_external_ids)
                conn.execute(
                    f"""
                    UPDATE supplier_services
                    SET is_active = 0, removed_at = ?, synced_at = ?
                    WHERE supplier_id = ? AND is_active = 1 AND external_service_id NOT IN ({placeholders})
                    """,
                    (synced_at, synced_at, supplier_id, *seen_external_ids),
                )
            else:
                conn.execute(
                    """
                    UPDATE supplier_services
                    SET is_active = 0, removed_at = ?, synced_at = ?
                    WHERE supplier_id = ? AND is_active = 1
                    """,
                    (synced_at, synced_at, supplier_id),
                )

            inactive_count = conn.execute(
                "SELECT COUNT(*) AS count FROM supplier_services WHERE supplier_id = ? AND is_active = 0",
                (supplier_id,),
            ).fetchone()["count"]
            persisted_api_url = result.get("persistedApiUrl") or result["resolvedApiUrl"]
            service_count = len(seen_external_ids)
            conn.execute(
                """
                UPDATE suppliers
                SET api_url = ?, last_test_status = 'success', last_test_message = ?, last_balance = ?, last_currency = ?,
                    last_service_count = ?, last_checked_at = ?,
                    service_sync_status = 'success',
                    service_sync_message = ?,
                    service_sync_completed_at = ?,
                    service_sync_lock_until = '',
                    service_sync_error_count = 0,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    persisted_api_url,
                    "서비스 동기화 완료",
                    result["balance"],
                    result["currency"],
                    service_count,
                    synced_at,
                    "서비스 동기화 완료",
                    synced_at,
                    synced_at,
                    supplier_id,
                ),
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="supplier.services_sync",
                entity_type="supplier",
                entity_id=supplier_id,
                message="공급사 서비스 목록 동기화",
                metadata={"serviceCount": service_count, "inactiveServiceCount": inactive_count},
            )
            conn.commit()

        return {
            "supplier": self._supplier_by_id(supplier_id),
            "serviceCount": service_count,
            "inactiveServiceCount": inactive_count,
            "syncedAt": synced_at,
            "skipped": False,
        }

    def sync_supplier_services(self, supplier_id: str, *, actor: str = "admin") -> Dict[str, Any]:
        return self._sync_supplier_services_internal(supplier_id, actor=actor, force=True)

    def sync_due_supplier_services(
        self,
        *,
        actor: str = "cron",
        limit: int = 10,
        request_timeout_seconds: Any = 6,
    ) -> Dict[str, Any]:
        requested_limit = 10 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "synced": 0, "failed": 0, "skipped": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 25))
        supplier_timeout = supplier_request_timeout_seconds(request_timeout_seconds, 6)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM suppliers
                WHERE is_active = 1
                ORDER BY COALESCE(NULLIF(service_sync_completed_at, ''), NULLIF(last_checked_at, ''), created_at) ASC
                LIMIT 100
                """
            ).fetchall()

        checked = len(rows)
        results: List[Dict[str, Any]] = []
        synced = 0
        failed = 0
        skipped = 0
        for row in rows:
            if len(results) >= max_items:
                break
            if not supplier_service_sync_due(row):
                skipped += 1
                continue
            supplier_id = str(row["id"])
            try:
                result = self._sync_supplier_services_internal(
                    supplier_id,
                    actor=actor,
                    force=False,
                    request_timeout_seconds=supplier_timeout,
                )
                if result.get("skipped"):
                    skipped += 1
                else:
                    synced += 1
                results.append({"supplierId": supplier_id, "ok": True, **result})
            except Exception as exc:
                failed += 1
                results.append({"supplierId": supplier_id, "ok": False, "error": str(exc)})

        return {
            "checked": checked,
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "results": results,
            "requestTimeoutSeconds": supplier_timeout,
            "ranAt": now_iso(),
        }

    def _supplier_auto_dispatch_readiness(
        self,
        conn: DatabaseConnection,
        *,
        supplier_id: str,
        supplier_service_id: str = "",
    ) -> Dict[str, Any]:
        row = conn.execute(
            """
            SELECT
                s.*,
                ss.is_active AS service_is_active,
                ss.external_service_id AS service_external_id,
                (
                    SELECT COUNT(*)
                    FROM supplier_services active_ss
                    WHERE active_ss.supplier_id = s.id AND active_ss.is_active = 1
                ) AS active_service_count
            FROM suppliers s
            LEFT JOIN supplier_services ss ON ss.supplier_id = s.id AND ss.id = ?
            WHERE s.id = ?
            """,
            (supplier_service_id, supplier_id),
        ).fetchone()
        if row is None:
            return {"ok": False, "retryable": False, "code": "supplier_missing", "message": "공급사를 찾을 수 없습니다."}
        return supplier_auto_dispatch_readiness(row, supplier_service_id=supplier_service_id)

    def check_due_supplier_health(self, *, actor: str = "cron", limit: int = 20) -> Dict[str, Any]:
        requested_limit = 20 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "ok": 0, "failed": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 50))
        due_before = (dt.datetime.now().astimezone() - dt.timedelta(minutes=SUPPLIER_STATUS_CHECK_INTERVAL_MINUTES)).isoformat(timespec="seconds")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    (
                        SELECT COUNT(*)
                        FROM supplier_services ss
                        WHERE ss.supplier_id = s.id AND ss.is_active = 1
                    ) AS active_service_count
                FROM suppliers s
                WHERE s.is_active = 1
                  AND (s.health_checked_at = '' OR s.health_checked_at <= ?)
                ORDER BY COALESCE(NULLIF(s.health_checked_at, ''), s.created_at) ASC
                LIMIT ?
                """,
                (due_before, max_items),
            ).fetchall()

        checked = 0
        ok = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        for row in rows:
            checked += 1
            supplier_id = str(row["id"])
            integration_type = normalize_supplier_integration_type(row.get("integration_type"))
            timestamp = now_iso()
            health_status = "ok"
            health_message = "공급사 상태 정상"
            balance_status = "unsupported"
            last_balance = str(row.get("last_balance") or "")
            last_currency = str(row.get("last_currency") or "")
            active_service_count = int(row.get("active_service_count") or 0)
            if not str(row.get("api_key") or "").strip():
                health_status = "failed"
                health_message = "공급사 API key가 없습니다."
            elif active_service_count <= 0:
                health_status = "failed"
                health_message = "활성 공급사 서비스가 없습니다. 서비스 동기화가 필요합니다."
            elif str(row.get("service_sync_status") or "") == "failed":
                health_status = "failed"
                health_message = str(row.get("service_sync_message") or "최근 서비스 동기화가 실패했습니다.")[:1000]

            if health_status == "ok" and integration_type == SUPPLIER_INTEGRATION_MKT24:
                try:
                    client = SupplierApiClient(
                        str(row["api_url"]),
                        decrypt_secret_value(row["api_key"]),
                        integration_type=integration_type,
                        bearer_token=decrypt_secret_value(row.get("bearer_token") or ""),
                    )
                    client.services()
                    health_message = "MKT24 연결 확인 완료"
                    balance_status = "unsupported"
                except Exception as exc:
                    health_status = "failed"
                    health_message = str(exc)[:1000]
            if health_status == "ok" and supplier_supports_balance_check(integration_type):
                try:
                    client = SupplierApiClient(
                        str(row["api_url"]),
                        decrypt_secret_value(row["api_key"]),
                        integration_type=integration_type,
                        bearer_token=decrypt_secret_value(row.get("bearer_token") or ""),
                    )
                    balance = client.balance_summary()
                    last_balance = str(balance.get("balance") or "")
                    last_currency = str(balance.get("currency") or "")
                    balance_status = "ok"
                    health_message = "공급사 연결/잔액 확인 완료"
                except Exception as exc:
                    health_status = "failed"
                    balance_status = "failed"
                    health_message = str(exc)[:1000]

            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE suppliers
                    SET health_status = ?, health_message = ?, health_checked_at = ?,
                        balance_status = ?, balance_checked_at = ?, last_balance = ?, last_currency = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        health_status,
                        health_message,
                        timestamp,
                        balance_status,
                        timestamp,
                        last_balance,
                        last_currency,
                        timestamp,
                        supplier_id,
                    ),
                )
                conn.commit()
            if health_status == "ok":
                ok += 1
            else:
                failed += 1
            results.append({"supplierId": supplier_id, "status": health_status, "message": health_message})

        return {"checked": checked, "ok": ok, "failed": failed, "results": results, "ranAt": now_iso()}

    def _mark_cafe24_retry_state(
        self,
        conn: DatabaseConnection,
        *,
        item_id: str,
        attempts: int,
        code: str,
        message: str,
        retryable: bool = True,
    ) -> None:
        timestamp = now_iso()
        if not retryable or attempts >= AUTOMATION_RETRY_MAX_ATTEMPTS:
            conn.execute(
                """
                UPDATE cafe24_order_items
                SET standard_status = ?, automation_last_checked_at = ?, automation_error_code = ?,
                    next_retry_at = '', error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                ("needs_manual_review", timestamp, code, message[:1000], timestamp, item_id),
            )
            return
        conn.execute(
            """
            UPDATE cafe24_order_items
            SET automation_last_checked_at = ?, automation_error_code = ?,
                next_retry_at = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, code, automation_retry_at(attempts), message[:1000], timestamp, item_id),
        )

    def dispatch_due_cafe24_order_items(self, *, actor: str = "cron", limit: int = 20) -> Dict[str, Any]:
        requested_limit = 20 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "submitted": 0, "blocked": 0, "failed": 0, "duplicates": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 100))
        timestamp = now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    coi.id, coi.supplier_id, coi.supplier_service_id, coi.retry_count,
                    coi.mapping_id, coi.auto_dispatch_approved
                FROM cafe24_order_items coi
                JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
                LEFT JOIN cafe24_supplier_mappings cm ON cm.id = coi.mapping_id
                WHERE ci.is_active = 1
                  AND ci.auto_submit = 1
                  AND coi.payment_gate_status = 'payment_confirmed'
                  AND coi.standard_status IN ('ready_to_submit', 'failed')
                  AND coi.supplier_order_uuid = ''
                  AND coi.supplier_id <> ''
                  AND coi.supplier_external_service_id <> ''
                  AND (
                    (
                      coi.mapping_id <> ''
                      AND cm.id IS NOT NULL
                      AND cm.enabled = 1
                      AND cm.auto_dispatch_enabled = 1
                      AND (
                        cm.cafe24_product_no <> ''
                        OR cm.cafe24_variant_code <> ''
                        OR cm.cafe24_custom_product_code <> ''
                      )
                    )
                    OR coi.auto_dispatch_approved = 1
                  )
                  AND COALESCE(coi.retry_count, 0) < ?
                  AND (coi.next_retry_at = '' OR coi.next_retry_at <= ?)
                ORDER BY coi.updated_at ASC
                LIMIT ?
                """,
                (AUTOMATION_RETRY_MAX_ATTEMPTS, timestamp, max_items),
            ).fetchall()

        submitted = 0
        blocked = 0
        failed = 0
        duplicates = 0
        results: List[Dict[str, Any]] = []
        for row in rows:
            item_id = str(row["id"])
            try:
                preflight = self.preflight_single_cafe24_order_item({"itemId": item_id, "_adminActor": actor})
                blocking_reasons = [str(reason) for reason in preflight.get("blockingReasons") or []]
                with self._connect() as conn:
                    conn.execute(
                        """
                        UPDATE cafe24_order_items
                        SET preflight_checked_at = ?, preflight_blockers_json = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            str(preflight.get("checkedAt") or now_iso()),
                            as_json(blocking_reasons),
                            now_iso(),
                            item_id,
                        ),
                    )
                    conn.commit()
                if not bool(preflight.get("canDispatch")):
                    readiness = preflight.get("supplierReadiness") if isinstance(preflight.get("supplierReadiness"), dict) else {}
                    code = blocking_reasons[0] if blocking_reasons else str(readiness.get("code") or "preflight_blocked")
                    message = str(readiness.get("message") or ", ".join(blocking_reasons) or "Cafe24 preflight 차단")
                    blocked += 1
                    with self._connect() as conn:
                        self._mark_cafe24_retry_state(
                            conn,
                            item_id=item_id,
                            attempts=max(int(row["retry_count"] or 0), 1),
                            code=code,
                            message=message,
                            retryable=bool(readiness.get("retryable")),
                        )
                        conn.commit()
                    results.append({"itemId": item_id, "status": "blocked", "preflight": preflight})
                    continue
                result = self.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": actor})
                if result.get("duplicate"):
                    duplicates += 1
                elif result.get("submitted"):
                    submitted += 1
                elif result.get("status") == "failed":
                    failed += 1
                results.append(result)
            except Exception as exc:
                failed += 1
                with self._connect() as conn:
                    attempts_row = conn.execute("SELECT retry_count FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
                    self._mark_cafe24_retry_state(
                        conn,
                        item_id=item_id,
                        attempts=int((attempts_row or {}).get("retry_count") or 1),
                        code="dispatch_exception",
                        message=str(exc),
                        retryable=True,
                    )
                    conn.commit()
                results.append({"itemId": item_id, "status": "failed", "error": str(exc)})
        return {
            "checked": len(rows),
            "submitted": submitted,
            "blocked": blocked,
            "failed": failed,
            "duplicates": duplicates,
            "results": results,
            "ranAt": now_iso(),
        }

    def dispatch_due_web_orders(self, *, actor: str = "cron", limit: int = 20) -> Dict[str, Any]:
        requested_limit = 20 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "submitted": 0, "blocked": 0, "failed": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, dispatch_attempts
                FROM orders
                WHERE order_channel = ?
                  AND dispatch_status IN (?, ?)
                  AND COALESCE(dispatch_attempts, 0) < ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (ORDER_CHANNEL_WEB, ORDER_DISPATCH_READY, ORDER_DISPATCH_FAILED, AUTOMATION_RETRY_MAX_ATTEMPTS, max_items),
            ).fetchall()

        submitted = 0
        blocked = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        for row in rows:
            order_id = str(row["id"])
            try:
                with self._connect() as conn:
                    context = self._supplier_dispatch_context(conn, order_id)
                    readiness = self._supplier_auto_dispatch_readiness(
                        conn,
                        supplier_id=str(context["mapping"]["supplier_id"]),
                        supplier_service_id=str(context["mapping"]["supplier_service_id"]),
                    )
                    if not readiness["ok"]:
                        blocked += 1
                        conn.execute(
                            "UPDATE orders SET supplier_last_error = ?, updated_at = ? WHERE id = ?",
                            (str(readiness["message"])[:1000], now_iso(), order_id),
                        )
                        conn.commit()
                        results.append({"orderId": order_id, "status": "blocked", **readiness})
                        continue
                dispatch = self._dispatch_supplier_order(order_id, context["product"], context["fields"], context["mapping"])
                if dispatch["status"] in {ORDER_DISPATCH_SUBMITTED, ORDER_DISPATCH_ACCEPTED}:
                    submitted += 1
                elif dispatch["status"] == ORDER_DISPATCH_FAILED:
                    failed += 1
                results.append({"orderId": order_id, **dispatch})
            except Exception as exc:
                failed += 1
                with self._connect() as conn:
                    conn.execute(
                        """
                        UPDATE orders
                        SET dispatch_attempts = COALESCE(dispatch_attempts, 0) + 1,
                            supplier_last_error = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (str(exc)[:1000], now_iso(), order_id),
                    )
                    conn.commit()
                results.append({"orderId": order_id, "status": "failed", "error": str(exc)})
        return {"checked": len(rows), "submitted": submitted, "blocked": blocked, "failed": failed, "results": results, "ranAt": now_iso()}

    def _supplier_status_to_cafe24_status(self, supplier_status: str) -> str:
        if supplier_status == "completed":
            return "completed"
        if supplier_status in {"in_progress", "pending", "submitted", "accepted", "partial"}:
            return "supplier_progress"
        if supplier_status in {"failed", "cancelled"}:
            return "failed"
        return "supplier_progress"

    def _next_supplier_status_check_at(self, supplier_status: str) -> str:
        if supplier_status in {"completed", "failed", "cancelled"}:
            return ""
        return (
            dt.datetime.now().astimezone()
            + dt.timedelta(minutes=SUPPLIER_STATUS_CHECK_INTERVAL_MINUTES)
        ).isoformat(timespec="seconds")

    def refresh_due_supplier_order_statuses(self, *, actor: str = "cron", limit: int = 50) -> Dict[str, Any]:
        requested_limit = 50 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "completed": 0, "failed": 0, "errors": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 150))
        timestamp = now_iso()
        terminal_statuses = {"completed", "failed", "cancelled"}
        checked = 0
        completed = 0
        failed = 0
        errors = 0
        results: List[Dict[str, Any]] = []

        with self._connect() as conn:
            supplier_order_rows = conn.execute(
                """
                SELECT
                    so.*,
                    o.order_channel,
                    o.external_order_id,
                    o.external_order_item_id,
                    s.api_url,
                    s.integration_type,
                    s.api_key,
                    s.bearer_token
                FROM supplier_orders so
                JOIN orders o ON o.id = so.order_id
                JOIN suppliers s ON s.id = so.supplier_id
                WHERE so.supplier_external_order_id <> ''
                  AND so.status NOT IN ('completed', 'failed', 'cancelled')
                  AND (so.next_status_check_at = '' OR so.next_status_check_at <= ?)
                ORDER BY COALESCE(NULLIF(so.next_status_check_at, ''), so.updated_at) ASC
                LIMIT ?
                """,
                (timestamp, max_items),
            ).fetchall()

        for row in supplier_order_rows:
            checked += 1
            try:
                client = SupplierApiClient(
                    str(row["api_url"]),
                    decrypt_secret_value(row["api_key"]),
                    integration_type=str(row["integration_type"]),
                    bearer_token=decrypt_secret_value(row["bearer_token"]),
                )
                status_payload = client.status(str(row["supplier_external_order_id"]))
                supplier_status = normalize_supplier_order_status_payload(status_payload)
                next_check = self._next_supplier_status_check_at(supplier_status)
                response_json = parse_json(row["response_json"], {})
                response_json["lastStatusCheck"] = {"checkedAt": now_iso(), "payload": status_payload}
                message = ""
                if isinstance(status_payload, dict):
                    message = str(status_payload.get("error") or status_payload.get("message") or "").strip()
                with self._connect() as conn:
                    conn.execute(
                        """
                        UPDATE supplier_orders
                        SET status = ?, response_json = ?, last_status_checked_at = ?,
                            next_status_check_at = ?, status_check_attempts = COALESCE(status_check_attempts, 0) + 1,
                            status_check_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            supplier_status,
                            as_json(redact_external_payload(response_json)),
                            now_iso(),
                            next_check,
                            message[:1000],
                            now_iso(),
                            row["id"],
                        ),
                    )
                    conn.execute(
                        "UPDATE orders SET dispatch_status = ?, supplier_last_error = ?, updated_at = ? WHERE id = ?",
                        (
                            normalize_order_dispatch_status(supplier_status),
                            message[:1000] if supplier_status in {"failed", "cancelled"} else "",
                            now_iso(),
                            row["order_id"],
                        ),
                    )
                    if supplier_status in terminal_statuses:
                        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (supplier_status, now_iso(), row["order_id"]))
                    elif supplier_status in {"in_progress", "pending", "submitted", "accepted", "partial"}:
                        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", ("in_progress", now_iso(), row["order_id"]))
                    if row["order_channel"] == ORDER_CHANNEL_CAFE24 and row["external_order_id"]:
                        cafe24_status = self._supplier_status_to_cafe24_status(supplier_status)
                        conn.execute(
                            """
                            UPDATE cafe24_order_items
                            SET standard_status = ?, error_message = ?, automation_last_checked_at = ?,
                                cafe24_completion_status = CASE
                                    WHEN ? = 'completed' AND cafe24_completion_status <> 'done'
                                      AND EXISTS (
                                        SELECT 1
                                        FROM cafe24_integrations ci
                                        WHERE ci.mall_id = cafe24_order_items.mall_id
                                          AND ci.shop_no = cafe24_order_items.shop_no
                                          AND ci.completion_policy = 'purchase_confirm'
                                      ) THEN 'pending'
                                    WHEN ? = 'completed' AND cafe24_completion_status <> 'done' THEN 'skipped'
                                    ELSE cafe24_completion_status
                                END,
                                cafe24_completion_message = CASE
                                    WHEN ? = 'completed'
                                      AND NOT EXISTS (
                                        SELECT 1
                                        FROM cafe24_integrations ci
                                        WHERE ci.mall_id = cafe24_order_items.mall_id
                                          AND ci.shop_no = cafe24_order_items.shop_no
                                          AND ci.completion_policy = 'purchase_confirm'
                                      ) THEN 'completion_policy=memo_only'
                                    ELSE cafe24_completion_message
                                END,
                                updated_at = ?
                            WHERE cafe24_order_id = ? AND cafe24_order_item_code = ?
                            """,
                            (
                                cafe24_status,
                                message[:1000],
                                now_iso(),
                                supplier_status,
                                supplier_status,
                                supplier_status,
                                now_iso(),
                                row["external_order_id"],
                                row["external_order_item_id"],
                            ),
                        )
                    conn.commit()
                if supplier_status == "completed":
                    completed += 1
                elif supplier_status in {"failed", "cancelled"}:
                    failed += 1
                results.append({"supplierOrderId": row["id"], "status": supplier_status})
            except Exception as exc:
                errors += 1
                with self._connect() as conn:
                    conn.execute(
                        """
                        UPDATE supplier_orders
                        SET last_status_checked_at = ?, next_status_check_at = ?,
                            status_check_attempts = COALESCE(status_check_attempts, 0) + 1,
                            status_check_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (now_iso(), automation_retry_at(1), str(exc)[:1000], now_iso(), row["id"]),
                    )
                    conn.commit()
                results.append({"supplierOrderId": row["id"], "status": "failed", "error": str(exc)})

        remaining_limit = max(max_items - checked, 0)
        if remaining_limit:
            cutoff = (dt.datetime.now().astimezone() - dt.timedelta(minutes=SUPPLIER_STATUS_CHECK_INTERVAL_MINUTES)).isoformat(timespec="seconds")
            with self._connect() as conn:
                cafe24_rows = conn.execute(
                    """
                    SELECT
                        coi.*,
                        s.api_url,
                        s.integration_type,
                        s.api_key,
                        s.bearer_token
                    FROM cafe24_order_items coi
                    JOIN suppliers s ON s.id = coi.supplier_id
                    WHERE coi.supplier_order_uuid <> ''
                      AND coi.standard_status IN ('submitting', 'supplier_submitted', 'supplier_progress')
                      AND (coi.automation_last_checked_at = '' OR coi.automation_last_checked_at <= ?)
                    ORDER BY COALESCE(NULLIF(coi.automation_last_checked_at, ''), coi.last_submitted_at, coi.updated_at) ASC
                    LIMIT ?
                    """,
                    (cutoff, remaining_limit),
                ).fetchall()

            for row in cafe24_rows:
                checked += 1
                try:
                    client = SupplierApiClient(
                        str(row["api_url"]),
                        decrypt_secret_value(row["api_key"]),
                        integration_type=str(row["integration_type"]),
                        bearer_token=decrypt_secret_value(row["bearer_token"]),
                    )
                    status_payload = client.status(str(row["supplier_order_uuid"]))
                    supplier_status = normalize_supplier_order_status_payload(status_payload)
                    cafe24_status = self._supplier_status_to_cafe24_status(supplier_status)
                    response_json = parse_json(row["supplier_response_json"], {})
                    response_json["lastStatusCheck"] = {"checkedAt": now_iso(), "payload": status_payload}
                    message = ""
                    if isinstance(status_payload, dict):
                        message = str(status_payload.get("error") or status_payload.get("message") or "").strip()
                    with self._connect() as conn:
                        conn.execute(
                            """
                            UPDATE cafe24_order_items
                            SET standard_status = ?, supplier_response_json = ?, error_message = ?,
                                automation_last_checked_at = ?, cafe24_completion_status = CASE
                                    WHEN ? = 'completed' AND cafe24_completion_status <> 'done'
                                      AND EXISTS (
                                        SELECT 1
                                        FROM cafe24_integrations ci
                                        WHERE ci.mall_id = cafe24_order_items.mall_id
                                          AND ci.shop_no = cafe24_order_items.shop_no
                                          AND ci.completion_policy = 'purchase_confirm'
                                      ) THEN 'pending'
                                    WHEN ? = 'completed' AND cafe24_completion_status <> 'done' THEN 'skipped'
                                    ELSE cafe24_completion_status
                                END,
                                cafe24_completion_message = CASE
                                    WHEN ? = 'completed'
                                      AND NOT EXISTS (
                                        SELECT 1
                                        FROM cafe24_integrations ci
                                        WHERE ci.mall_id = cafe24_order_items.mall_id
                                          AND ci.shop_no = cafe24_order_items.shop_no
                                          AND ci.completion_policy = 'purchase_confirm'
                                      ) THEN 'completion_policy=memo_only'
                                    ELSE cafe24_completion_message
                                END,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                cafe24_status,
                                as_json(redact_external_payload(response_json)),
                                message[:1000],
                                now_iso(),
                                supplier_status,
                                supplier_status,
                                supplier_status,
                                now_iso(),
                                row["id"],
                            ),
                        )
                        conn.commit()
                    if supplier_status == "completed":
                        completed += 1
                    elif supplier_status in {"failed", "cancelled"}:
                        failed += 1
                    results.append({"itemId": row["id"], "status": supplier_status})
                except Exception as exc:
                    errors += 1
                    with self._connect() as conn:
                        conn.execute(
                            """
                            UPDATE cafe24_order_items
                            SET automation_last_checked_at = ?, automation_error_code = ?,
                                error_message = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (now_iso(), "supplier_status_check_failed", str(exc)[:1000], now_iso(), row["id"]),
                        )
                        conn.commit()
                    results.append({"itemId": row["id"], "status": "failed", "error": str(exc)})

        return {"checked": checked, "completed": completed, "failed": failed, "errors": errors, "results": results, "ranAt": now_iso()}

    def complete_due_cafe24_order_items(self, *, actor: str = "cron", limit: int = 20) -> Dict[str, Any]:
        requested_limit = 20 if limit is None else int(limit)
        if requested_limit <= 0:
            return {"checked": 0, "done": 0, "failed": 0, "results": [], "ranAt": now_iso(), "skippedByLimit": True}
        max_items = max(1, min(requested_limit, 100))
        timestamp = now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    coi.*,
                    ci.id AS integration_id,
                    ci.scopes_json,
                    ci.access_token,
                    ci.refresh_token,
                    ci.expires_at,
                    ci.refresh_token_expires_at,
                    ci.token_status,
                    ci.token_refresh_lock_until,
                    ci.reconnect_reason
                FROM cafe24_order_items coi
                JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
                WHERE ci.is_active = 1
                  AND ci.completion_policy = 'purchase_confirm'
                  AND coi.standard_status = 'completed'
                  AND coi.payment_gate_status = 'payment_confirmed'
                  AND coi.cafe24_completion_status IN ('pending', 'failed')
                  AND COALESCE(coi.cafe24_completion_attempts, 0) < ?
                  AND (coi.cafe24_next_completion_retry_at = '' OR coi.cafe24_next_completion_retry_at <= ?)
                ORDER BY coi.updated_at ASC
                LIMIT ?
                """,
                (AUTOMATION_RETRY_MAX_ATTEMPTS, timestamp, max_items),
            ).fetchall()

        done = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        for row in rows:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    UPDATE cafe24_order_items
                    SET cafe24_completion_status = ?, cafe24_completion_attempts = COALESCE(cafe24_completion_attempts, 0) + 1,
                        cafe24_completion_message = '', updated_at = ?
                    WHERE id = ?
                      AND cafe24_completion_status IN ('pending', 'failed')
                      AND cafe24_completed_at = ''
                    """,
                    ("processing", now_iso(), row["id"]),
                )
                conn.commit()
            if cursor.rowcount != 1:
                continue
            try:
                with self._connect() as conn:
                    integration_payload = dict(row)
                    integration_payload["id"] = integration_payload.get("integration_id") or integration_payload.get("id")
                    response = self._cafe24_call_with_token_retry(
                        conn,
                        integration_payload,
                        lambda client: client.confirm_purchase(
                            str(row["cafe24_order_id"]),
                            str(row["cafe24_order_item_code"]),
                        ),
                    )
                    conn.execute(
                        """
                        UPDATE cafe24_order_items
                        SET cafe24_completion_status = ?, cafe24_completion_message = ?,
                            cafe24_completed_at = ?, cafe24_next_completion_retry_at = '', updated_at = ?
                        WHERE id = ?
                        """,
                        ("done", as_json(redact_external_payload(response))[:1000], now_iso(), now_iso(), row["id"]),
                    )
                    self._log_cafe24_event(
                        conn,
                        mall_id=str(row["mall_id"]),
                        shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                        event_type="order_item.purchase_confirm",
                        status="success",
                        request_payload={
                            "orderId": row["cafe24_order_id"],
                            "orderItemCode": row["cafe24_order_item_code"],
                            "purchase_confirmation": "T",
                            "collect_points": "F",
                        },
                        response_payload=response,
                    )
                    conn.commit()
                done += 1
                results.append({"itemId": row["id"], "status": "done"})
            except Exception as exc:
                failed += 1
                with self._connect() as conn:
                    attempts_row = conn.execute(
                        "SELECT cafe24_completion_attempts FROM cafe24_order_items WHERE id = ?",
                        (row["id"],),
                    ).fetchone()
                    attempts = int((attempts_row or {}).get("cafe24_completion_attempts") or 1)
                    next_retry = "" if attempts >= AUTOMATION_RETRY_MAX_ATTEMPTS else automation_retry_at(attempts)
                    conn.execute(
                        """
                        UPDATE cafe24_order_items
                        SET cafe24_completion_status = ?, cafe24_completion_message = ?,
                            cafe24_next_completion_retry_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        ("failed", str(exc)[:1000], next_retry, now_iso(), row["id"]),
                    )
                    self._log_cafe24_event(
                        conn,
                        mall_id=str(row["mall_id"]),
                        shop_no=int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
                        event_type="order_item.purchase_confirm",
                        status="failed",
                        request_payload={"orderId": row["cafe24_order_id"], "orderItemCode": row["cafe24_order_item_code"]},
                        error_message=str(exc),
                    )
                    conn.commit()
                results.append({"itemId": row["id"], "status": "failed", "error": str(exc)})
        return {"checked": len(rows), "done": done, "failed": failed, "results": results, "ranAt": now_iso()}

    def run_cafe24_flow_tick(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        actor = str(payload.get("_adminActor") or payload.get("actor") or "cron").strip() or "cron"
        paused = automation_paused()
        started_at = now_iso()
        started_perf = time.perf_counter()

        def int_option(key: str, default: int, *, minimum: int = 0, maximum: int = 1000) -> int:
            try:
                value = int(payload.get(key) if payload.get(key) is not None else default)
            except (TypeError, ValueError):
                value = default
            return min(max(value, minimum), maximum)

        def float_option(key: str, default: float, *, minimum: float = 1.0, maximum: float = 15.0) -> float:
            try:
                value = float(payload.get(key) if payload.get(key) is not None else default)
            except (TypeError, ValueError):
                value = default
            return min(max(value, minimum), maximum)

        lookback_minutes = int_option("lookbackMinutes", CAFE24_FLOW_LOOKBACK_MINUTES, minimum=5, maximum=7 * 24 * 60)
        overlap_minutes = int_option("overlapMinutes", CAFE24_ORDER_OVERLAP_MINUTES, minimum=0, maximum=24 * 60)
        cafe24_limit = int_option("cafe24Limit", 5, minimum=1, maximum=200)
        page_limit = int_option("pageLimit", CAFE24_FLOW_PAGE_LIMIT, minimum=1, maximum=CAFE24_ORDER_PAGE_LIMIT)
        max_pages = int_option("maxPages", CAFE24_FLOW_MAX_PAGES, minimum=1, maximum=CAFE24_ORDER_MAX_PAGES)
        detail_fetch_limit = int_option("detailFetchLimit", CAFE24_FLOW_DETAIL_FETCH_LIMIT, minimum=0, maximum=500)
        dispatch_limit = int_option("dispatchLimit", CAFE24_FLOW_DISPATCH_LIMIT, minimum=0, maximum=100)
        status_limit = int_option("statusLimit", CAFE24_FLOW_STATUS_LIMIT, minimum=0, maximum=150)
        completion_limit = int_option("completionLimit", CAFE24_FLOW_COMPLETION_LIMIT, minimum=0, maximum=100)
        request_timeout_seconds = float_option(
            "requestTimeoutSeconds",
            CAFE24_FLOW_REQUEST_TIMEOUT_SECONDS,
            minimum=1.0,
            maximum=15.0,
        )
        max_attempts = int_option("maxAttempts", CAFE24_FLOW_MAX_ATTEMPTS, minimum=1, maximum=3)

        result: Dict[str, Any] = {
            "startedAt": started_at,
            "paused": paused,
            "cafe24Poll": {},
            "cafe24Dispatch": {"skipped": paused},
            "supplierStatusRefresh": {"skipped": paused},
            "cafe24Completion": {"skipped": paused},
            "settings": {
                "lookbackMinutes": lookback_minutes,
                "useCursor": True,
                "overlapMinutes": overlap_minutes,
                "pageLimit": page_limit,
                "maxPages": max_pages,
                "detailFetchLimit": detail_fetch_limit,
                "dispatchLimit": dispatch_limit,
                "statusLimit": status_limit,
                "completionLimit": completion_limit,
                "requestTimeoutSeconds": request_timeout_seconds,
                "maxAttempts": max_attempts,
            },
        }
        status = "success"
        message = "Cafe24 flow tick completed"
        try:
            result["cafe24Poll"] = self.poll_due_cafe24_orders(
                {
                    "actor": actor,
                    "force": True,
                    "lookbackMinutes": lookback_minutes,
                    "useCursor": True,
                    "overlapMinutes": overlap_minutes,
                    "limit": cafe24_limit,
                    "pageLimit": page_limit,
                    "maxPages": max_pages,
                    "detailFetchLimit": detail_fetch_limit,
                    "requestTimeoutSeconds": request_timeout_seconds,
                    "maxAttempts": max_attempts,
                }
            )
            if not paused:
                result["cafe24Dispatch"] = self.dispatch_due_cafe24_order_items(actor=actor, limit=dispatch_limit)
                result["supplierStatusRefresh"] = self.refresh_due_supplier_order_statuses(actor=actor, limit=status_limit)
                result["cafe24Completion"] = self.complete_due_cafe24_order_items(actor=actor, limit=completion_limit)
            else:
                message = "Cafe24 flow paused: collection only"
        except Exception as exc:
            status = "failed"
            message = str(exc)
            result["error"] = message
        finally:
            result["finishedAt"] = now_iso()
            result["durationMs"] = int((time.perf_counter() - started_perf) * 1000)
            result["status"] = status
            result["message"] = message
            with self._connect() as conn:
                self._set_runtime_metadata(conn, "cafe24_flow.last_tick", as_json(redact_external_payload(result)))
                self._set_runtime_metadata(conn, "cafe24_flow.last_tick_at", result["finishedAt"])
                self._set_runtime_metadata(conn, "cafe24_flow.last_tick_status", status)
                conn.commit()
        return result

    def run_automation_tick(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        actor = str(payload.get("_adminActor") or payload.get("actor") or "cron").strip() or "cron"
        paused = automation_paused()
        started_at = now_iso()
        started_perf = time.perf_counter()
        lookback_days = int(payload.get("lookbackDays") or CAFE24_ORDER_DEFAULT_LOOKBACK_DAYS)
        supplier_limit = int(payload.get("supplierLimit") or 10)
        supplier_sync_limit = int(payload.get("supplierSyncLimit") if payload.get("supplierSyncLimit") is not None else supplier_limit)
        supplier_health_limit = int(payload.get("supplierHealthLimit") if payload.get("supplierHealthLimit") is not None else supplier_limit)
        cafe24_limit = int(payload.get("cafe24Limit") or 5)
        cafe24_page_limit = int(payload.get("cafe24PageLimit") or CAFE24_ORDER_PAGE_LIMIT)
        cafe24_max_pages = int(payload.get("cafe24MaxPages") or CAFE24_ORDER_MAX_PAGES)
        cafe24_detail_fetch_limit = int(payload.get("cafe24DetailFetchLimit") if payload.get("cafe24DetailFetchLimit") is not None else 200)
        dispatch_limit = int(payload.get("dispatchLimit") or 25)
        status_limit = int(payload.get("statusLimit") or 50)
        completion_limit = int(payload.get("completionLimit") or 25)
        result: Dict[str, Any] = {
            "startedAt": started_at,
            "paused": paused,
            "supplierServiceSync": {},
            "supplierHealth": {},
            "cafe24Poll": {},
            "webDispatch": {"skipped": paused},
            "cafe24Dispatch": {"skipped": paused},
            "supplierStatusRefresh": {"skipped": paused},
            "cafe24Completion": {"skipped": paused},
        }
        status = "success"
        message = "automation tick completed"
        try:
            result["supplierServiceSync"] = self.sync_due_supplier_services(actor=actor, limit=supplier_sync_limit)
            result["supplierHealth"] = self.check_due_supplier_health(actor=actor, limit=supplier_health_limit)
            result["cafe24Poll"] = self.poll_due_cafe24_orders(
                {
                    "actor": actor,
                    "lookbackDays": lookback_days,
                    "limit": cafe24_limit,
                    "pageLimit": cafe24_page_limit,
                    "maxPages": cafe24_max_pages,
                    "detailFetchLimit": cafe24_detail_fetch_limit,
                }
            )
            if not paused:
                result["webDispatch"] = self.dispatch_due_web_orders(actor=actor, limit=dispatch_limit)
                result["cafe24Dispatch"] = self.dispatch_due_cafe24_order_items(actor=actor, limit=dispatch_limit)
                result["supplierStatusRefresh"] = self.refresh_due_supplier_order_statuses(actor=actor, limit=status_limit)
                result["cafe24Completion"] = self.complete_due_cafe24_order_items(actor=actor, limit=completion_limit)
            else:
                message = "automation paused: collection only"
        except Exception as exc:
            status = "failed"
            message = str(exc)
            result["error"] = message
        finally:
            result["finishedAt"] = now_iso()
            result["durationMs"] = int((time.perf_counter() - started_perf) * 1000)
            result["status"] = status
            result["message"] = message
            with self._connect() as conn:
                self._set_runtime_metadata(conn, "automation.last_tick", as_json(redact_external_payload(result)))
                self._set_runtime_metadata(conn, "automation.last_tick_at", result["finishedAt"])
                self._set_runtime_metadata(conn, "automation.last_tick_status", status)
                self._set_runtime_metadata(conn, "automation.paused", "1" if paused else "0")
                conn.commit()
        return result

    def save_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("productId") or "").strip()
        supplier_id = str(payload.get("supplierId") or "").strip()
        supplier_service_id = str(payload.get("supplierServiceId") or "").strip()
        pricing_mode = str(payload.get("pricingMode") or "multiplier").strip() or "multiplier"
        price_multiplier = safe_float(payload.get("priceMultiplier"), 1.0)
        fixed_markup = int(float(payload.get("fixedMarkup") or 0) or 0)
        is_primary = bool(payload.get("isPrimary", True))
        actor = self._admin_actor(payload)

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
                WHERE id = ? AND supplier_id = ? AND is_active = 1
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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="supplier.mapping_update",
                entity_type="product_supplier_mapping",
                entity_id=mapping_id,
                message="상품 공급사 매핑 저장",
                metadata={"productId": product_id, "supplierId": supplier_id, "supplierServiceId": supplier_service_id},
            )
            conn.commit()

        return {"mapping": self._mapping_summary_by_product(product_id)}

    def delete_product_mapping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mapping_id = str(payload.get("mappingId") or "").strip()
        actor = self._admin_actor(payload)
        if not mapping_id:
            raise PanelError("삭제할 매핑 정보를 찾을 수 없습니다.")
        with self._connect() as conn:
            row = conn.execute("SELECT product_id FROM product_supplier_mappings WHERE id = ?", (mapping_id,)).fetchone()
            if row is None:
                raise PanelError("삭제할 매핑을 찾을 수 없습니다.", status=404)
            conn.execute("DELETE FROM product_supplier_mappings WHERE id = ?", (mapping_id,))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="supplier.mapping_delete",
                entity_type="product_supplier_mapping",
                entity_id=mapping_id,
                message="상품 공급사 매핑 삭제",
                metadata={"productId": row["product_id"]},
            )
            conn.commit()
            return {"mapping": self._mapping_summary_by_product(row["product_id"])}

    def save_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        email = self._normalize_customer_email(payload.get("email") or "")
        password = str(payload.get("password") or "")
        phone = str(payload.get("phone") or "").strip()
        tier = str(payload.get("tier") or "STANDARD").strip() or "STANDARD"
        role = str(payload.get("role") or "customer").strip() or "customer"
        notes = str(payload.get("notes") or "").strip()
        is_active = bool(payload.get("isActive", True))
        account_status = "active" if is_active else "suspended"
        actor = self._admin_actor(payload)

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
            self._assert_available_customer_email(conn, email, exclude_user_id=customer_id)
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
                    SET name = ?, email = ?, password_hash = ?, phone = ?, tier = ?, role = ?, avatar_label = ?, is_active = ?, account_status = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (name, email, password_hash, phone, tier, role, avatar_label(name), bool_to_int(is_active), account_status, notes, timestamp, customer_id),
                )
            else:
                customer_id = f"user_{uuid4().hex[:12]}"
                password_hash = "" if role == "admin" else hash_password(password)
                conn.execute(
                    """
                    INSERT INTO users (
                        id, name, email, password_hash, phone, tier, role, avatar_label, balance, is_active,
                        account_status, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                    """,
                    (customer_id, name, email, password_hash, phone, tier, role, avatar_label(name), bool_to_int(is_active), account_status, notes, timestamp, timestamp),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="customer.update" if payload.get("id") else "customer.create",
                entity_type="customer",
                entity_id=customer_id,
                message=f"고객 계정 저장: {name}",
                metadata={"role": role, "isActive": is_active},
            )
            conn.commit()
        return {"customer": self._customer_by_id(customer_id)}

    def get_customer_detail(self, customer_id: str) -> Dict[str, Any]:
        return {"customer": self._customer_by_id(customer_id, include_private=True)}

    def delete_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("customerId") or "").strip()
        actor = self._admin_actor(payload)
        if not customer_id:
            raise PanelError("삭제할 고객을 선택해 주세요.")
        if customer_id == DEMO_USER_ID:
            raise PanelError("기본 운영 계정은 삭제할 수 없습니다.")

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
            self._record_admin_audit(
                conn,
                actor=actor,
                action=f"customer.{action}",
                entity_type="customer",
                entity_id=customer_id,
                message=f"고객 계정 {action}",
            )
            conn.commit()
        return {"ok": True, "action": action, "customerId": customer_id}

    def adjust_customer_balance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(payload.get("customerId") or "").strip()
        amount = int(float(payload.get("amount") or 0) or 0)
        memo = str(payload.get("memo") or "").strip() or "관리자 잔액 조정"
        actor = self._admin_actor(payload)
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
            self._set_wallet_balances(conn, customer_id, available_balance=balance_after)
            conn.execute(
                """
                INSERT INTO balance_transactions (id, user_id, amount, balance_after, kind, memo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"tx_{uuid4().hex[:12]}", customer_id, amount, balance_after, "admin_adjust", memo, timestamp),
            )
            self._append_wallet_ledger_entry(
                conn,
                ledger_id=f"ledger_admin_adjust_{uuid4().hex[:12]}",
                user_id=customer_id,
                entry_type="admin_adjustment",
                amount=amount,
                balance_after=balance_after,
                memo=memo,
                created_at=timestamp,
            )
            self._record_admin_audit(
                conn,
                actor=actor,
                action="customer.balance_adjust",
                entity_type="customer",
                entity_id=customer_id,
                message="고객 보유금액 수동 조정",
                metadata={"amount": amount, "balanceAfter": balance_after, "memo": memo},
            )
            conn.commit()
        return {"customer": self._customer_by_id(customer_id), "balanceAfter": balance_after, "balanceAfterLabel": money(balance_after)}

    def admin_update_charge_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        charge_order_id = str(payload.get("chargeOrderId") or "").strip()
        action = str(payload.get("action") or "").strip()
        reference = str(payload.get("reference") or "").strip()
        admin_memo = str(payload.get("adminMemo") or "").strip()
        actor = self._admin_actor(payload)
        if not charge_order_id:
            raise PanelError("처리할 충전 주문을 선택해 주세요.")
        if action not in {"approve_deposit", "mark_failed", "cancel"}:
            raise PanelError("지원하지 않는 충전 처리 방식입니다.")

        timestamp = now_iso()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM charge_orders WHERE id = ?", (charge_order_id,)).fetchone()
            if row is None:
                raise PanelError("충전 주문을 찾을 수 없습니다.", status=404)

            if action == "approve_deposit":
                if row["payment_channel"] != "bank_transfer":
                    raise PanelError("계좌입금 주문만 입금 확인 처리할 수 있습니다.")
                result = self._complete_charge_order(
                    conn,
                    charge_order_id,
                    payment_method="bank_transfer",
                    payment_status="completed",
                    reference=reference or f"ADMIN-{dt.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}",
                    payment_payload={"approvedBy": "admin", "adminMemo": admin_memo, "approvedAt": timestamp},
                    paid_total_amount=int(row["total_amount"]),
                    memo_prefix="입금 확인 충전",
                )
                self._record_admin_audit(
                    conn,
                    actor=actor,
                    action="charge.approve_deposit",
                    entity_type="charge_order",
                    entity_id=charge_order_id,
                    message="충전 주문 입금 확인 및 보유금액 반영",
                    metadata={"reference": reference, "adminMemo": admin_memo},
                )
                conn.commit()
                return {
                    "chargeOrder": self._admin_charge_order_by_id(conn, charge_order_id),
                    "wallet": result.get("wallet"),
                }

            if row["status"] == "paid":
                raise PanelError("이미 결제 완료된 충전 주문은 실패/취소 처리할 수 없습니다.")
            next_status = "failed" if action == "mark_failed" else "cancelled"
            failure_reason = admin_memo or ("관리자 실패 처리" if action == "mark_failed" else "관리자 취소 처리")
            payment_payload = parse_json(row["payment_payload_json"], {})
            payment_payload.update({"adminMemo": admin_memo, "updatedBy": "admin", "updatedAt": timestamp})
            conn.execute(
                """
                UPDATE charge_orders
                SET status = ?, reference = ?, failure_reason = ?, payment_payload_json = ?, updated_at = ?
                WHERE id = ? AND status != 'paid'
                """,
                (
                    next_status,
                    reference,
                    failure_reason,
                    as_json(payment_payload),
                    timestamp,
                    charge_order_id,
                ),
            )
            self._refresh_wallet_pending_balance(conn, str(row["user_id"]))
            charge_order = self._admin_charge_order_by_id(conn, charge_order_id)
            self._record_admin_audit(
                conn,
                actor=actor,
                action=f"charge.{action}",
                entity_type="charge_order",
                entity_id=charge_order_id,
                message=f"충전 주문 {next_status} 처리",
                metadata={"reference": reference, "adminMemo": admin_memo},
            )
            conn.commit()
        return {"chargeOrder": charge_order}

    def save_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        notice_id = str(payload.get("id") or "").strip()
        title = str(payload.get("title") or "").strip()
        body = str(payload.get("body") or "").strip()
        tag = str(payload.get("tag") or "공지").strip() or "공지"
        pinned = bool(payload.get("pinned", False))
        published_at = str(payload.get("publishedAt") or "").strip() or now_iso()
        actor = self._admin_actor(payload)
        if not title:
            raise PanelError("공지 제목을 입력해 주세요.")
        if not body:
            raise PanelError("공지 내용을 입력해 주세요.")

        with self._connect() as conn:
            action = "notice.update" if notice_id else "notice.create"
            if notice_id:
                exists = conn.execute("SELECT id FROM notices WHERE id = ?", (notice_id,)).fetchone()
                if exists is None:
                    raise PanelError("수정할 공지를 찾을 수 없습니다.", status=404)
                conn.execute(
                    "UPDATE notices SET title = ?, body = ?, tag = ?, pinned = ?, published_at = ? WHERE id = ?",
                    (title, body, tag, bool_to_int(pinned), published_at, notice_id),
                )
            else:
                notice_id = f"notice_{uuid4().hex[:12]}"
                conn.execute(
                    "INSERT INTO notices (id, title, body, tag, pinned, published_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (notice_id, title, body, tag, bool_to_int(pinned), published_at),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action=action,
                entity_type="notice",
                entity_id=notice_id,
                message=f"공지 저장: {title}",
                metadata={"pinned": pinned, "tag": tag},
            )
            conn.commit()
            notice = conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
        return {"notice": self._notice_payload(notice)}

    def delete_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        notice_id = str(payload.get("noticeId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not notice_id:
            raise PanelError("삭제할 공지를 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
            if row is None:
                raise PanelError("삭제할 공지를 찾을 수 없습니다.", status=404)
            conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="notice.delete",
                entity_type="notice",
                entity_id=notice_id,
                message=f"공지 삭제: {row['title']}",
            )
            conn.commit()
        return {"ok": True, "noticeId": notice_id}

    def save_faq(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        faq_id = str(payload.get("id") or "").strip()
        question = str(payload.get("question") or "").strip()
        answer = str(payload.get("answer") or "").strip()
        sort_order = int(float(payload.get("sortOrder") or 0) or 0)
        actor = self._admin_actor(payload)
        if not question:
            raise PanelError("FAQ 질문을 입력해 주세요.")
        if not answer:
            raise PanelError("FAQ 답변을 입력해 주세요.")

        with self._connect() as conn:
            action = "faq.update" if faq_id else "faq.create"
            if faq_id:
                exists = conn.execute("SELECT id FROM faqs WHERE id = ?", (faq_id,)).fetchone()
                if exists is None:
                    raise PanelError("수정할 FAQ를 찾을 수 없습니다.", status=404)
                conn.execute(
                    "UPDATE faqs SET question = ?, answer = ?, sort_order = ? WHERE id = ?",
                    (question, answer, sort_order, faq_id),
                )
            else:
                faq_id = f"faq_{uuid4().hex[:12]}"
                conn.execute(
                    "INSERT INTO faqs (id, question, answer, sort_order) VALUES (?, ?, ?, ?)",
                    (faq_id, question, answer, sort_order),
                )
            self._record_admin_audit(
                conn,
                actor=actor,
                action=action,
                entity_type="faq",
                entity_id=faq_id,
                message=f"FAQ 저장: {question}",
                metadata={"sortOrder": sort_order},
            )
            conn.commit()
            faq = conn.execute("SELECT * FROM faqs WHERE id = ?", (faq_id,)).fetchone()
        return {"faq": self._faq_payload(faq)}

    def delete_faq(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        faq_id = str(payload.get("faqId") or payload.get("id") or "").strip()
        actor = self._admin_actor(payload)
        if not faq_id:
            raise PanelError("삭제할 FAQ를 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM faqs WHERE id = ?", (faq_id,)).fetchone()
            if row is None:
                raise PanelError("삭제할 FAQ를 찾을 수 없습니다.", status=404)
            conn.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="faq.delete",
                entity_type="faq",
                entity_id=faq_id,
                message=f"FAQ 삭제: {row['question']}",
            )
            conn.commit()
        return {"ok": True, "faqId": faq_id}

    def _supplier_dispatch_context(self, conn: DatabaseConnection, order_id: str) -> Dict[str, Any]:
        row = conn.execute(
            """
            SELECT
                o.id AS order_id,
                o.quantity,
                o.target_value,
                p.id AS product_id,
                p.name AS product_name,
                p.product_code,
                p.price_strategy,
                ps.slug AS platform_slug,
                psm.supplier_id,
                psm.supplier_service_id,
                psm.supplier_external_service_id,
                s.api_url,
                s.integration_type,
                s.api_key,
                s.bearer_token,
                s.name AS supplier_name,
                s.is_active AS supplier_is_active
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN product_categories pc ON pc.id = p.product_category_id
            JOIN platform_groups pg ON pg.id = pc.platform_group_id
            JOIN platform_sections ps ON ps.id = pg.platform_section_id
            JOIN product_supplier_mappings psm ON psm.product_id = p.id AND psm.is_primary = 1 AND psm.is_active = 1
            JOIN suppliers s ON s.id = psm.supplier_id
            JOIN supplier_services ss ON ss.id = psm.supplier_service_id AND ss.is_active = 1
            WHERE o.id = ?
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        if row is None:
            raise PanelError("이 주문에 연결된 활성 공급사 매핑이 없습니다.", status=404)
        if not bool(row["supplier_is_active"]):
            raise PanelError("연결된 공급사가 비활성 상태입니다.")
        fields = {
            field["field_key"]: field["field_value"]
            for field in conn.execute("SELECT field_key, field_value FROM order_fields WHERE order_id = ?", (order_id,)).fetchall()
        }
        if not any(fields.get(key) for key in ("targetUrl", "targetValue", "targetKeyword")):
            fields["targetValue"] = row["target_value"]
        if not fields.get("orderedCount"):
            fields["orderedCount"] = str(row["quantity"])
        product = {
            "id": row["product_id"],
            "name": row["product_name"],
            "product_code": row["product_code"],
            "platform_slug": row["platform_slug"],
            "price_strategy": row["price_strategy"],
        }
        mapping = {
            "supplier_id": row["supplier_id"],
            "supplier_service_id": row["supplier_service_id"],
            "supplier_external_service_id": row["supplier_external_service_id"],
            "api_url": row["api_url"],
            "integration_type": row["integration_type"],
            "api_key": row["api_key"],
            "bearer_token": row["bearer_token"],
        }
        return {"product": product, "fields": fields, "mapping": mapping, "supplierName": row["supplier_name"]}

    def retry_supplier_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(payload.get("orderId") or "").strip()
        actor = self._admin_actor(payload)
        if not order_id:
            raise PanelError("재전송할 주문을 선택해 주세요.")
        with self._connect() as conn:
            order_exists = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
            if order_exists is None:
                raise PanelError("주문을 찾을 수 없습니다.", status=404)
            context = self._supplier_dispatch_context(conn, order_id)
        dispatch = self._dispatch_supplier_order(order_id, context["product"], context["fields"], context["mapping"])
        with self._connect() as conn:
            if dispatch["status"] in {"submitted", "accepted"}:
                conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", ("in_progress", now_iso(), order_id))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="order.supplier_retry",
                entity_type="order",
                entity_id=order_id,
                message="공급사 발주 재전송",
                metadata={"supplier": context.get("supplierName"), "dispatchStatus": dispatch["status"]},
            )
            conn.commit()
        return {"dispatch": dispatch}

    def refresh_supplier_order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(payload.get("orderId") or "").strip()
        actor = self._admin_actor(payload)
        if not order_id:
            raise PanelError("상태를 조회할 주문을 선택해 주세요.")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    so.*,
                    s.api_url,
                    s.integration_type,
                    s.api_key,
                    s.bearer_token,
                    s.name AS supplier_name
                FROM supplier_orders so
                JOIN suppliers s ON s.id = so.supplier_id
                WHERE so.order_id = ?
                ORDER BY so.created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ).fetchone()
            if row is None:
                raise PanelError("조회할 공급사 발주 기록이 없습니다.", status=404)
            external_order_id = str(row["supplier_external_order_id"] or "").strip()
            if not external_order_id:
                raise PanelError("공급사 외부 주문번호가 없어 상태 조회가 불가합니다.")

            client = SupplierApiClient(
                str(row["api_url"]),
                decrypt_secret_value(row["api_key"]),
                integration_type=str(row["integration_type"]),
                bearer_token=decrypt_secret_value(row["bearer_token"]),
            )
            status_payload = client.status(external_order_id)
            next_supplier_status = normalize_supplier_order_status_payload(status_payload)
            response_json = parse_json(row["response_json"], {})
            response_json["lastStatusCheck"] = {
                "checkedAt": now_iso(),
                "payload": status_payload,
            }
            timestamp = now_iso()
            conn.execute(
                "UPDATE supplier_orders SET status = ?, response_json = ?, updated_at = ? WHERE id = ?",
                (next_supplier_status, as_json(response_json), timestamp, row["id"]),
            )
            conn.execute(
                "UPDATE orders SET dispatch_status = ?, supplier_last_error = ?, updated_at = ? WHERE id = ?",
                (
                    normalize_order_dispatch_status(next_supplier_status),
                    str(status_payload.get("error") or status_payload.get("message") or "").strip()
                    if isinstance(status_payload, dict) and next_supplier_status in {"failed", "cancelled"}
                    else "",
                    timestamp,
                    order_id,
                ),
            )
            if next_supplier_status == "completed":
                conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", ("completed", timestamp, order_id))
            elif next_supplier_status in {"in_progress", "pending", "submitted", "partial"}:
                conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", ("in_progress", timestamp, order_id))
            elif next_supplier_status in {"failed", "cancelled"}:
                conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (next_supplier_status, timestamp, order_id))
            self._record_admin_audit(
                conn,
                actor=actor,
                action="order.supplier_status_refresh",
                entity_type="order",
                entity_id=order_id,
                message="공급사 주문 상태 조회",
                metadata={"supplierStatus": next_supplier_status, "externalOrderId": external_order_id},
            )
            conn.commit()
        return {"supplierStatus": next_supplier_status, "supplierOrderId": row["id"], "statusPayload": status_payload}

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
        actor = self._admin_actor(payload)

        if not group_id:
            raise PanelError("플랫폼 그룹을 선택해 주세요.")
        if not name:
            raise PanelError("카테고리 이름을 입력해 주세요.")

        caution_items = split_lines(caution_text) or ["비공개 계정 또는 잘못된 URL 입력 시 작업이 지연될 수 있어요."]
        refund_items = split_lines(refund_text) or ["작업이 시작된 이후에는 취소 및 환불이 제한될 수 있어요."]
        if not service_description_html:
            service_description_html = f"<p><strong>{html_escape(name)}</strong></p><p>{html_escape(description or hero_subtitle or '상세 설명을 입력해 주세요.')}</p>"
        service_description_html = sanitize_rich_html(service_description_html)

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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="catalog.category_update" if payload.get("id") else "catalog.category_create",
                entity_type="product_category",
                entity_id=category_id,
                message=f"상품 카테고리 저장: {name}",
                metadata={"groupId": group_id, "isActive": is_active},
            )
            conn.commit()
        return {"category": self._category_by_id(category_id)}

    def delete_category(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        category_id = str(payload.get("categoryId") or "").strip()
        actor = self._admin_actor(payload)
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
            self._record_admin_audit(
                conn,
                actor=actor,
                action=f"catalog.category_{action}",
                entity_type="product_category",
                entity_id=category_id,
                message=f"상품 카테고리 {action}",
                metadata={"orderCount": int(order_count), "productCount": int(product_count)},
            )
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
        actor = self._admin_actor(payload)

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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="catalog.product_update" if payload.get("id") else "catalog.product_create",
                entity_type="product",
                entity_id=product_id,
                message=f"상품 저장: {name}",
                metadata={"categoryId": category_id, "price": price, "isActive": is_active},
            )
            conn.commit()
        return {"product": self._catalog_product_by_id(product_id)}

    def delete_catalog_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("productId") or "").strip()
        actor = self._admin_actor(payload)
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
            self._record_admin_audit(
                conn,
                actor=actor,
                action=f"catalog.product_{action}",
                entity_type="product",
                entity_id=product_id,
                message=f"상품 {action}",
                metadata={"categoryId": product["product_category_id"], "orderCount": int(order_count)},
            )
            conn.commit()
        return {"ok": True, "action": action, "productId": product_id}

    def update_admin_order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(payload.get("orderId") or "").strip()
        status = str(payload.get("status") or "").strip()
        admin_memo = str(payload.get("adminMemo") or "").strip()
        actor = self._admin_actor(payload)
        if not order_id:
            raise PanelError("주문을 선택해 주세요.")
        if status not in {"queued", "in_progress", "completed", "failed", "cancelled"}:
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
            self._record_admin_audit(
                conn,
                actor=actor,
                action="order.status_update",
                entity_type="order",
                entity_id=order_id,
                message=f"주문 상태 변경: {status}",
                metadata={"adminMemo": admin_memo},
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
        request_timeout_seconds: Any = None,
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
                request_timeout_seconds=request_timeout_seconds,
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
                persisted_api_url = (
                    candidate
                    if normalized_type in {SUPPLIER_INTEGRATION_MKT24, SUPPLIER_INTEGRATION_FASTTRAFFIC}
                    else (api_url.strip() or candidate)
                )
                return {
                    "status": "success",
                    "message": success_message,
                    "resolvedApiUrl": candidate,
                    "persistedApiUrl": persisted_api_url,
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
            "apiKeyMasked": safe_mask_secret(row["api_key"]),
            "hasBearerToken": bool(row["bearer_token"]) and integration_type != SUPPLIER_INTEGRATION_MKT24,
            "bearerTokenMasked": "" if integration_type == SUPPLIER_INTEGRATION_MKT24 else safe_mask_secret(row["bearer_token"]),
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
            "serviceSyncStatus": row["service_sync_status"],
            "serviceSyncMessage": row["service_sync_message"],
            "serviceSyncStartedAt": row["service_sync_started_at"],
            "serviceSyncCompletedAt": row["service_sync_completed_at"],
            "serviceSyncLockUntil": row["service_sync_lock_until"],
            "serviceSyncErrorCount": row["service_sync_error_count"],
            "serviceSyncIntervalMinutes": row["service_sync_interval_minutes"],
            "healthStatus": row.get("health_status") or "unknown",
            "healthMessage": row.get("health_message") or "",
            "healthCheckedAt": row.get("health_checked_at") or "",
            "balanceStatus": row.get("balance_status") or "unknown",
            "balanceCheckedAt": row.get("balance_checked_at") or "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if include_api_key:
            payload["apiKey"] = decrypt_secret_value(row["api_key"])
            payload["bearerToken"] = "" if integration_type == SUPPLIER_INTEGRATION_MKT24 else decrypt_secret_value(row["bearer_token"])
        return payload

    def public_site_settings(self) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1")
        return {"siteSettings": self._site_settings_public_payload(row)}

    def admin_site_settings(self) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1")
        return {"siteSettings": self._site_settings_admin_payload(row)}

    def _site_settings_row(self, conn: DatabaseConnection) -> Dict[str, Any]:
        row = conn.execute("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            self._ensure_site_settings(conn)
            row = conn.execute("SELECT * FROM site_settings ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            raise PanelError("사이트 설정을 불러오지 못했습니다.", status=500)
        site_name = str(row["site_name"] or "").strip()
        site_description = str(row["site_description"] or "").strip()
        should_normalize_name = site_name in LEGACY_DEFAULT_SITE_NAMES
        should_normalize_description = (not site_description) or site_description in LEGACY_DEFAULT_SITE_DESCRIPTIONS
        if should_normalize_name or should_normalize_description:
            conn.execute(
                """
                UPDATE site_settings
                SET site_name = ?, site_description = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    DEFAULT_SITE_NAME if should_normalize_name else site_name,
                    DEFAULT_SITE_DESCRIPTION if should_normalize_description else site_description,
                    now_iso(),
                    row["id"],
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM site_settings WHERE id = ?", (row["id"],)).fetchone()
            if row is None:
                raise PanelError("사이트 설정을 불러오지 못했습니다.", status=500)
        return row

    def _site_settings_public_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
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
            "headerLogoUrl": row["header_logo_url"],
            "faviconUrl": row["favicon_url"],
            "shareImageUrl": row["share_image_url"],
        }

    def _site_settings_admin_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._site_settings_public_payload(row)
        payload.update(
            {
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
        )
        return payload

    def _popup_public_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
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

    def _popup_admin_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
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

    def _home_banner_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
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

    def _platform_section_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "slug": row["slug"],
            "displayName": row["display_name"],
            "description": row["description"],
            "icon": row["icon"],
            "logoImageUrl": row["image_url"],
            "accentColor": row["accent_color"],
            "sortOrder": row["sort_order"],
        }

    def _home_popup_by_id(self, popup_id: str) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM home_popups WHERE id = ?", (popup_id,))
        return self._popup_admin_payload(row)

    def _home_banner_by_id(self, banner_id: str) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM home_banners WHERE id = ?", (banner_id,))
        return self._home_banner_payload(row)

    def _platform_section_by_id(self, platform_id: str) -> Dict[str, Any]:
        row = self._fetchone("SELECT * FROM platform_sections WHERE id = ?", (platform_id,))
        return self._platform_section_payload(row)

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
            consent_rows = conn.execute(
                """
                SELECT consent_type, consent_version, is_agreed, agreed_at
                FROM user_consents
                WHERE user_id = ?
                ORDER BY agreed_at DESC
                """,
                (customer_id,),
            ).fetchall()
            social_rows = conn.execute(
                """
                SELECT provider, provider_email, linked_at, last_login_at
                FROM user_social_identities
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (customer_id,),
            ).fetchall()
        if row is None:
            raise PanelError("고객을 찾을 수 없습니다.", status=404)
        payload = {
            "id": row["id"],
            "name": row["name"],
            "emailMasked": mask_email(row["email"]),
            "phoneMasked": mask_phone(row["phone"]),
            "tier": row["tier"],
            "role": row["role"],
            "avatarLabel": resolved_avatar_label(row["avatar_label"], row["name"]),
            "balance": row["balance"],
            "balanceLabel": money(row["balance"]),
            "isActive": bool(row["is_active"]),
            "accountStatus": row["account_status"],
            "marketingOptIn": bool(row["marketing_opt_in"]),
            "marketingOptInAt": row["marketing_opt_in_at"],
            "withdrawnAt": row["withdrawn_at"],
            "suspendedReason": row["suspended_reason"],
            "hasPassword": bool(row["password_hash"]),
            "notes": row["notes"],
            "lastLoginAt": row["last_login_at"],
            "orderCount": row["order_count"],
            "totalSpent": row["total_spent"],
            "totalSpentLabel": money(row["total_spent"]),
            "lastOrderAt": row["last_order_at"] or "",
            "lastOrderLabel": self._relative_date_label(row["last_order_at"]) if row["last_order_at"] else "",
            "consents": [
                {
                    "type": consent["consent_type"],
                    "version": consent["consent_version"],
                    "isAgreed": bool(consent["is_agreed"]),
                    "agreedAt": consent["agreed_at"],
                }
                for consent in consent_rows
            ],
            "socialIdentities": [
                {
                    "provider": social["provider"],
                    "providerEmail": social["provider_email"],
                    "linkedAt": social["linked_at"],
                    "lastLoginAt": social["last_login_at"],
                }
                for social in social_rows
            ],
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
                GROUP BY
                    pc.id,
                    pg.id,
                    pg.name,
                    ps.id,
                    ps.display_name
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
            "serviceDescriptionHtml": sanitize_rich_html(row["service_description_html"]),
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

    def _sync_category_order_options(self, conn: DatabaseConnection, category_id: str) -> None:
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
        raise PanelError(
            "직접 잔액 충전 API는 더 이상 지원되지 않습니다. 새로운 충전 주문 플로우를 사용해 주세요.",
            status=410,
        )

    def _order_submission_payload(
        self,
        conn: DatabaseConnection,
        order_row: Dict[str, Any],
        *,
        duplicate: bool = False,
    ) -> Dict[str, Any]:
        wallet = self._wallet_balances(conn, str(order_row["user_id"]))
        return order_submission_payload(
            order_row,
            available_balance=wallet["available"],
            duplicate=duplicate,
        )

    def _existing_order_by_idempotency(self, user_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? AND idempotency_key = ?",
                (user_id, idempotency_key),
            ).fetchone()
            if row is None:
                return None
            return self._order_submission_payload(conn, dict(row), duplicate=True)

    def _existing_order_by_external_reference(
        self,
        order_channel: str,
        external_order_id: str,
        external_order_item_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not external_order_id:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM orders
                WHERE order_channel = ?
                  AND external_order_id = ?
                  AND external_order_item_id = ?
                """,
                (order_channel, external_order_id, external_order_item_id),
            ).fetchone()
            if row is None:
                return None
            return self._order_submission_payload(conn, dict(row), duplicate=True)

    def create_order(
        self,
        payload: Dict[str, Any],
        user_id: str = "",
        *,
        order_channel: str = ORDER_CHANNEL_WEB,
        external_order_id: str = "",
        external_order_item_id: str = "",
        external_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise PanelError("로그인이 필요합니다.", status=401)
        channel = normalize_order_channel(order_channel)
        external_reference = sanitize_external_order_reference(external_order_id)
        external_item_reference = sanitize_external_order_reference(external_order_item_id)
        if channel == ORDER_CHANNEL_WEB:
            external_reference = ""
            external_item_reference = ""
        elif not external_reference:
            raise PanelError("외부 주문 식별자가 필요합니다.")
        product_id = str(payload.get("productId") or "").strip()
        fields = payload.get("fields") or {}
        if not product_id:
            raise PanelError("주문할 상품이 선택되지 않았습니다.")
        if not isinstance(fields, dict):
            raise PanelError("주문 폼 정보가 올바르지 않습니다.")
        idempotency_key = sanitize_idempotency_key(payload.get("idempotencyKey"))
        if not idempotency_key and channel == ORDER_CHANNEL_WEB:
            idempotency_key = derive_order_idempotency_key(user_id, product_id, fields)
        existing_order = self._existing_order_by_idempotency(user_id, idempotency_key)
        if existing_order is not None:
            return existing_order
        existing_external_order = self._existing_order_by_external_reference(channel, external_reference, external_item_reference)
        if existing_external_order is not None:
            return existing_external_order

        supplier_mapping: Optional[Dict[str, Any]] = None
        product_data: Optional[Dict[str, Any]] = None
        try:
            with self._connect() as conn:
                if idempotency_key:
                    existing_row = conn.execute(
                        "SELECT * FROM orders WHERE user_id = ? AND idempotency_key = ?",
                        (user_id, idempotency_key),
                    ).fetchone()
                    if existing_row is not None:
                        return self._order_submission_payload(conn, dict(existing_row), duplicate=True)
                if external_reference:
                    existing_external_row = conn.execute(
                        """
                        SELECT *
                        FROM orders
                        WHERE order_channel = ?
                          AND external_order_id = ?
                          AND external_order_item_id = ?
                        """,
                        (channel, external_reference, external_item_reference),
                    ).fetchone()
                    if existing_external_row is not None:
                        return self._order_submission_payload(conn, dict(existing_external_row), duplicate=True)
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

                form_structure = ensure_request_memo_form_structure(
                    parse_json(product["form_structure_json"], {}),
                    "추가 요청사항",
                )
                rules = form_structure.get("schema", {})
                self._validate_fields(fields, rules)
                self._validate_product_target(product, fields, require_preview=True)

                quantity = self._resolve_quantity(product, fields)
                total_price = int(product["price"]) if product["price_strategy"] == "fixed" else int(product["price"]) * quantity

                user = conn.execute("SELECT balance, phone FROM users WHERE id = ?", (user_id,)).fetchone()
                if user is None:
                    raise PanelError("사용자를 찾을 수 없습니다.", status=404)
                wallet_balances = self._wallet_balances(conn, user_id)
                if int(wallet_balances["available"]) < total_price:
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
                    JOIN supplier_services ss ON ss.id = psm.supplier_service_id AND ss.is_active = 1
                    WHERE psm.product_id = ? AND psm.is_primary = 1 AND psm.is_active = 1
                    LIMIT 1
                    """,
                    (product_id,),
                ).fetchone()
                if mapping_row is not None and bool(mapping_row["supplier_is_active"]):
                    supplier_mapping = dict(mapping_row)
                product_data = dict(product)
                dispatch_status = ORDER_DISPATCH_READY if supplier_mapping else ORDER_DISPATCH_UNMAPPED

                timestamp = now_iso()
                order_number = generate_public_order_number()
                while conn.execute("SELECT 1 FROM orders WHERE order_number = ? LIMIT 1", (order_number,)).fetchone() is not None:
                    order_number = generate_public_order_number()
                order_id = f"order_{uuid4().hex[:16]}"
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
                request_memo = str(fields.get("requestMemo") or "").strip()
                if request_memo:
                    notes["memo"] = request_memo

                conn.execute(
                    """
                    INSERT INTO orders (
                        id, order_number, user_id, platform_section_id, product_category_id, product_id,
                        product_name_snapshot, option_name_snapshot, target_value, contact_phone,
                        quantity, unit_price, total_price, status, order_channel, external_order_id,
                        external_order_item_id, dispatch_status, external_payload_json, notes_json,
                        idempotency_key, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        channel,
                        external_reference,
                        external_item_reference,
                        dispatch_status,
                        as_json(external_payload or {}),
                        as_json(notes),
                        idempotency_key,
                        timestamp,
                        timestamp,
                    ),
                )

                template = form_structure.get("template", {})
                for field_index, (field_key, field_value) in enumerate(fields.items()):
                    if field_value in ("", None):
                        continue
                    field_label = self._field_label(template.get(field_key, {}), field_key)
                    conn.execute(
                        "INSERT INTO order_fields (id, order_id, field_key, field_label, field_value) VALUES (?, ?, ?, ?, ?)",
                        (f"{order_id}_field_{field_index}", order_id, field_key, field_label, str(field_value)),
                    )

                balance_after = self._change_wallet_available_balance(
                    conn,
                    user_id,
                    -total_price,
                    require_sufficient=True,
                    timestamp=timestamp,
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
                self._append_wallet_ledger_entry(
                    conn,
                    ledger_id=f"ledger_{order_id}",
                    user_id=user_id,
                    entry_type="order_debit",
                    amount=-total_price,
                    balance_after=balance_after,
                    memo=f"{product['name']} 주문",
                    related_order_id=order_id,
                    created_at=timestamp,
                )
                conn.commit()
        except Exception as exc:
            if idempotency_key and is_unique_constraint_error(exc):
                existing_order = self._existing_order_by_idempotency(user_id, idempotency_key)
                if existing_order is not None:
                    return existing_order
            if external_reference and is_unique_constraint_error(exc):
                existing_external_order = self._existing_order_by_external_reference(
                    channel,
                    external_reference,
                    external_item_reference,
                )
                if existing_external_order is not None:
                    return existing_external_order
            raise

        supplier_dispatch = None
        if supplier_mapping and product_data is not None:
            supplier_dispatch = self._dispatch_supplier_order(order_id, product_data, fields, supplier_mapping)

        response_payload = {
            "ok": True,
            "orderId": order_id,
            "orderNumber": order_number,
            "orderChannel": channel,
            "externalOrderId": external_reference,
            "externalOrderItemId": external_item_reference,
            "dispatchStatus": dispatch_status,
            "totalPrice": total_price,
            "totalPriceLabel": money(total_price),
            "balanceAfter": balance_after,
            "balanceAfterLabel": money(balance_after),
        }
        if supplier_dispatch is not None:
            response_payload["supplierDispatchStatus"] = supplier_dispatch["status"]
            response_payload["dispatchStatus"] = supplier_dispatch["status"]
        return response_payload

    def _dispatch_supplier_order(
        self,
        order_id: str,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id, supplier_external_order_id, status
                FROM supplier_orders
                WHERE order_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ).fetchone()
            if existing is not None and (
                str(existing["supplier_external_order_id"] or "").strip()
                or str(existing["status"] or "") in {"submitted", "accepted", "in_progress", "completed"}
            ):
                return {
                    "id": existing["id"],
                    "status": normalize_order_dispatch_status(existing["status"]),
                    "supplierExternalOrderId": existing["supplier_external_order_id"] or "",
                    "duplicate": True,
                }
        supplier_order_id = f"sord_{uuid4().hex[:12]}"
        timestamp = now_iso()
        request_payload = self._build_supplier_order_payload(product, fields, mapping)
        supplier_external_order_id = ""
        status = "pending"
        response_payload: Any = {}
        supplier_last_error = ""

        try:
            api_key = decrypt_secret_value(mapping["api_key"])
            bearer_token = decrypt_secret_value(mapping.get("bearer_token") or "")
            client = SupplierApiClient(
                str(mapping["api_url"]),
                api_key,
                integration_type=str(mapping.get("integration_type") or SUPPLIER_INTEGRATION_CLASSIC),
                bearer_token=bearer_token,
            )
            if client.integration_type == SUPPLIER_INTEGRATION_MKT24 and not client.uses_panel_api:
                for check in self._mkt24_load_input_checks(mapping, request_payload):
                    client.mkt24_sns_lookup(
                        product_uuid=check["productUuid"],
                        sns_value=check["snsValue"],
                    )
                client.mkt24_estimate_sns(request_payload)
            response_payload = client.order(request_payload)
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
            supplier_last_error = str(exc)
        if not supplier_last_error and isinstance(response_payload, dict):
            supplier_last_error = str(response_payload.get("error") or response_payload.get("message") or "").strip()
        supplier_auth_failed = supplier_error_is_auth_failure(
            supplier_last_error,
            integration_type=str(mapping.get("integration_type") or ""),
        )
        dispatch_status = normalize_order_dispatch_status(status)

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
            conn.execute(
                """
                UPDATE orders
                SET dispatch_status = ?,
                    dispatch_attempts = COALESCE(dispatch_attempts, 0) + 1,
                    supplier_last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    dispatch_status,
                    supplier_last_error if dispatch_status == ORDER_DISPATCH_FAILED else "",
                    timestamp,
                    order_id,
                ),
            )
            if supplier_auth_failed and str(mapping.get("supplier_id") or "").strip():
                conn.execute(
                    """
                    UPDATE suppliers
                    SET health_status = ?, health_message = ?, health_checked_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "failed",
                        (supplier_last_error or "공급사 인증 토큰이 만료되었습니다.")[:1000],
                        timestamp,
                        timestamp,
                        str(mapping["supplier_id"]),
                    ),
                )
            conn.commit()

        return {
            "id": supplier_order_id,
            "status": dispatch_status,
            "supplierExternalOrderId": supplier_external_order_id,
        }

    def _build_supplier_order_payload(
        self,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        integration_type = normalize_supplier_integration_type(str(mapping.get("integration_type") or ""))
        if integration_type == SUPPLIER_INTEGRATION_FASTTRAFFIC:
            return self._build_fasttraffic_supplier_order_payload(product, fields, mapping)
        if integration_type == SUPPLIER_INTEGRATION_MKT24 and not supplier_uses_panel_api(integration_type, str(mapping.get("api_url") or "")):
            return self._build_mkt24_supplier_order_payload(product, fields, mapping)

        payload: Dict[str, Any] = {
            "service": str(mapping["supplier_external_service_id"]),
        }

        target_url = str(fields.get("targetUrl") or "").strip()
        target_value = str(fields.get("targetValue") or "").strip()
        target_keyword = str(fields.get("targetKeyword") or "").strip()
        quantity = str(fields.get("orderedCount") or "").strip()
        platform_hint = preview_platform_hint(
            " ".join(
                [
                    str(product.get("product_code") or ""),
                    str(product.get("name") or product.get("product_name") or ""),
                    str(mapping.get("supplier_service_name") or ""),
                    str(mapping.get("supplier_external_service_id") or ""),
                ]
            ),
            " ".join([str(product.get("platform_slug") or ""), str(mapping.get("supplier_name") or "")]),
        )

        if target_url:
            payload["link"] = self._supplier_panel_target_link(target_url, platform_hint)
        elif target_value:
            inferred_link = self._supplier_panel_target_link(target_value, platform_hint)
            if inferred_link:
                payload["link"] = inferred_link
            if not inferred_link and not looks_like_url(target_value):
                payload["username"] = target_value.lstrip("@")

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

        if payload.get("link"):
            self._validate_supplier_panel_target_link(str(payload["link"]), platform_hint)

        return payload

    def _supplier_panel_target_link(self, raw_value: Any, platform_hint: str) -> str:
        return supplier_panel_target_link(
            raw_value,
            platform_hint,
            normalize_url=normalize_url,
            looks_like_url=looks_like_url,
        )

    def _validate_supplier_panel_target_link(self, link: str, platform_hint: str) -> None:
        try:
            validate_supplier_panel_target_link(
                link,
                platform_hint,
                normalize_url=normalize_url,
            )
        except SupplierTargetError as exc:
            raise PanelError(str(exc)) from exc

    def _build_fasttraffic_supplier_order_payload(
        self,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        action = str(mapping.get("supplier_external_service_id") or "").strip()
        if not action:
            raise PanelError("FastTraffic 서비스 action이 없습니다.")

        raw_service = parse_json(str(mapping.get("supplier_service_raw_json") or ""), {})
        if not isinstance(raw_service, dict):
            raw_service = {}
        fasttraffic_meta = raw_service.get("fasttraffic") if isinstance(raw_service, dict) else {}
        if not isinstance(fasttraffic_meta, dict):
            fasttraffic_meta = {}

        payload: Dict[str, Any] = {
            "service": action,
            "action": action,
        }
        defaults = fasttraffic_meta.get("defaults") if isinstance(fasttraffic_meta.get("defaults"), dict) else {}
        payload.update(defaults)

        direct_field_keys = {
            "blog_id",
            "blog_ids",
            "blog_url",
            "cafe_url",
            "clip_url",
            "title",
            "keyword",
            "private_comment",
            "work_cycle",
            "work_speed",
            "start_date",
            "end_date",
            "like_count",
            "comment_count",
            "save_count",
            "scrap_count",
            "stay_count",
            "stay_time",
            "stay_min",
            "stay_max",
            "stay_count_min",
            "stay_count_max",
            "keyword_inflow",
            "friend_count",
            "view_count",
            "view_min",
            "view_max",
            "subscriber_count",
            "keyword_count",
            "direct_comments",
        }
        for key in direct_field_keys:
            value = fields.get(key)
            if value not in (None, ""):
                payload[key] = value

        target_url = self._first_field_value(fields, ("blog_url", "cafe_url", "clip_url", "targetUrl", "link", "url"))
        target_value = self._first_field_value(fields, ("blog_id", "blog_ids", "targetValue", "username", "account", "snsValue"))
        keyword = self._first_field_value(fields, ("keyword", "targetKeyword", "googleKeyword", "google_keyword"))
        request_memo = self._first_field_value(fields, ("requestMemo", "memo", "comments", "direct_comments"))
        quantity = self._coerce_positive_int(self._first_field_value(fields, ("orderedCount", "quantity", "count", "qty")))
        title = self._first_field_value(fields, ("title", "productTitle", "campaignTitle")) or str(
            product.get("name") or product.get("product_name") or "인스타마트 주문"
        ).strip()

        if action == "nblog_auto":
            payload.setdefault("blog_id", target_value.lstrip("@"))
            if quantity:
                payload.setdefault("stay_min", max(1, min(quantity, int(payload.get("stay_min") or quantity))))
                payload["stay_max"] = quantity
        elif action == "nblog_direct":
            payload.setdefault("title", title)
            payload.setdefault("blog_url", normalize_url(target_url) or target_url)
            if quantity:
                payload["stay_count"] = quantity
        elif action == "nblog_daily":
            payload.setdefault("blog_ids", target_value.lstrip("@"))
            payload.setdefault("start_date", (dt.date.today() + dt.timedelta(days=1)).isoformat())
            if quantity:
                payload.setdefault("stay_count_min", max(1, min(quantity, int(payload.get("stay_count_min") or quantity))))
                payload["stay_count_max"] = quantity
        elif action == "nblog_add_friend":
            payload.setdefault("blog_id", target_value.lstrip("@"))
            if quantity:
                payload["friend_count"] = quantity
        elif action == "nblog_keyword":
            payload.setdefault("blog_url", normalize_url(target_url) or target_url)
            payload.setdefault("keyword", keyword or request_memo)
            if quantity:
                payload["keyword_inflow"] = quantity
        elif action == "nclip_direct_c":
            payload.setdefault("title", title)
            payload.setdefault("clip_url", normalize_url(target_url) or target_url)
            if quantity:
                payload["view_count"] = quantity
            if request_memo and "direct_comments" not in payload:
                payload["direct_comments"] = request_memo
        elif action == "ncafe_auto":
            payload.setdefault("title", title)
            payload.setdefault("cafe_url", normalize_url(target_url) or target_url)
            if quantity:
                payload.setdefault("view_min", max(1, min(quantity, int(payload.get("view_min") or quantity))))
                payload["view_max"] = quantity
        elif action == "ncafe_direct":
            payload.setdefault("title", title)
            payload.setdefault("cafe_url", normalize_url(target_url) or target_url)
            if quantity:
                payload["view_count"] = quantity
            if request_memo and "direct_comments" not in payload:
                payload["direct_comments"] = request_memo
        else:
            raise PanelError(f"지원하지 않는 FastTraffic 서비스입니다: {action}")

        required_fields = fasttraffic_meta.get("required") if isinstance(fasttraffic_meta.get("required"), list) else []
        missing_fields = [
            str(key)
            for key in required_fields
            if str(payload.get(str(key)) or "").strip() == ""
        ]
        if missing_fields:
            raise PanelError(f"FastTraffic 필수값 누락: {', '.join(missing_fields)}")

        quantity_param = str(fasttraffic_meta.get("quantityParam") or "").strip()
        if quantity_param and payload.get(quantity_param) not in (None, ""):
            final_quantity = self._coerce_positive_int(payload.get(quantity_param))
            min_amount = self._coerce_positive_int(mapping.get("supplier_min_amount") or raw_service.get("min") or 1) or 1
            max_amount = self._coerce_positive_int(mapping.get("supplier_max_amount") or raw_service.get("max") or final_quantity) or final_quantity
            if final_quantity < min_amount or final_quantity > max_amount:
                raise PanelError(f"FastTraffic 수량은 {min_amount}~{max_amount} 범위여야 합니다.")
            allowed_quantities = fasttraffic_meta.get("allowedQuantities")
            if isinstance(allowed_quantities, list) and allowed_quantities:
                allowed = {self._coerce_positive_int(value) for value in allowed_quantities}
                if final_quantity not in allowed:
                    raise PanelError("FastTraffic 서이추 수량은 50 단위로 50~500 사이에서 선택해야 합니다.")
            payload[quantity_param] = final_quantity

        cleaned: Dict[str, Any] = {}
        for key, value in payload.items():
            if value in (None, ""):
                continue
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _first_field_value(fields: Dict[str, Any], keys: Iterable[str]) -> str:
        for key in keys:
            value = fields.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""

    @staticmethod
    def _coerce_positive_int(value: Any) -> int:
        try:
            parsed = int(float(str(value).replace(",", "").strip()))
        except (TypeError, ValueError):
            return 0
        return parsed if parsed > 0 else 0

    def _build_mkt24_supplier_order_payload(
        self,
        product: Dict[str, Any],
        fields: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        product_uuid = str(mapping.get("supplier_external_service_id") or mapping.get("productUuid") or "").strip()
        if not product_uuid:
            raise PanelError("MKT24 상품 UUID가 없습니다.")

        setting = self._mkt24_setting_for_mapping(mapping)
        if setting:
            detail = setting["detail"]
            field_config = setting["fieldConfig"]
            option_config = setting["optionConfig"]
        else:
            detail = {
                "productUuid": product_uuid,
                "fullName": product.get("name") or "",
                "productName": product.get("name") or "",
                "productTypeName": product.get("product_code") or "",
                "supportsOrderOptions": False,
                "formStructure": {
                    "schema": {"snsValue": ["STRING_REQUIRED"], "orderedCount": ["MIN_MAX"]},
                    "template": {
                        "snsValue": {"variant": "load_input", "templateOptions": {"type": "account", "label": "계정/URL"}},
                        "orderedCount": {"variant": "input", "templateOptions": {"labelProps": {"label": "수량"}}},
                    },
                },
            }
            field_config = default_mkt24_field_config(detail)
            option_config = default_mkt24_option_config(detail)
        return self._build_mkt24_order_payload_from_setting(detail, field_config, option_config, fields)

    def _mkt24_setting_for_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = str(mapping.get("supplier_id") or mapping.get("supplierId") or "").strip()
        product_uuid = str(mapping.get("supplier_external_service_id") or mapping.get("productUuid") or "").strip()
        if not supplier_id or not product_uuid:
            return {}
        with self._connect() as conn:
            row = self._mkt24_product_setting_row(conn, supplier_id, product_uuid)
        if row is None or not bool(row["is_active"]):
            return {}
        detail = parse_json(row["detail_snapshot_json"], {})
        field_config = parse_json(row["field_config_json"], {})
        option_config = parse_json(row["option_config_json"], {})
        return {
            "detail": detail if isinstance(detail, dict) else {},
            "fieldConfig": field_config if isinstance(field_config, dict) else {},
            "optionConfig": option_config if isinstance(option_config, dict) else {},
        }

    def _resolve_mkt24_field_value(self, field_key: str, config: Dict[str, Any], user_fields: Dict[str, Any], *, for_preview: bool) -> Any:
        return resolve_mkt24_field_value(field_key, config, user_fields, for_preview=for_preview)

    def _build_mkt24_order_payload_from_setting(
        self,
        detail: Dict[str, Any],
        field_config: Dict[str, Any],
        option_config: Dict[str, Any],
        user_fields: Dict[str, Any],
        *,
        for_preview: bool = False,
    ) -> Dict[str, Any]:
        try:
            return build_mkt24_order_payload_from_setting(
                detail,
                field_config,
                option_config,
                user_fields,
                for_preview=for_preview,
            )
        except Mkt24SettingsError as exc:
            raise PanelError(str(exc)) from exc

    def _mkt24_load_input_checks(self, mapping: Dict[str, Any], payload: Dict[str, Any]) -> List[Dict[str, str]]:
        setting = self._mkt24_setting_for_mapping(mapping)
        field_config = setting.get("fieldConfig") if setting else {}
        if not isinstance(field_config, dict):
            return []
        product_uuid = str(payload.get("productUuid") or "").strip()
        order_info = payload.get("value", {}).get("orderInfo", {}) if isinstance(payload.get("value"), dict) else {}
        checks: List[Dict[str, str]] = []
        for field_key, config in field_config.items():
            if not isinstance(config, dict) or not bool(config.get("enabled", True)):
                continue
            if str(config.get("variant") or "") != "load_input":
                continue
            value = str(order_info.get(field_key) or "").strip()
            if value:
                checks.append({"fieldKey": str(field_key), "productUuid": product_uuid, "snsValue": value})
        return checks

    def _validate_fields(self, fields: Dict[str, Any], rules: Dict[str, List[str]]) -> None:
        for key, field_rules in rules.items():
            if "STRING_REQUIRED" in field_rules and not str(fields.get(key) or "").strip():
                raise PanelError("필수 입력값이 비어 있습니다.")

    def _validate_product_target(
        self,
        product: Dict[str, Any],
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
            format_valid = bool(url) and platform_target_url_matches(
                platform_hint,
                url,
                normalize_url=normalize_url,
                looks_like_url=looks_like_url,
            )
        elif field_key == "targetValue":
            if looks_like_url(raw_input):
                format_valid = bool(url) and platform_target_url_matches(
                    platform_hint,
                    url,
                    normalize_url=normalize_url,
                    looks_like_url=looks_like_url,
                )
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

    def _resolve_preview_target(self, product: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, str]:
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

    def _resolve_quantity(self, product: Dict[str, Any], fields: Dict[str, Any]) -> int:
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
