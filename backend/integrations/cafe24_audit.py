from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
from typing import Any, Callable, Dict

from .cafe24 import CAFE24_DEFAULT_SHOP_NO
from .suppliers import normalize_supplier_integration_type


CAFE24_OPERATIONAL_AUDIT_ENV_KEYS = (
    "SMM_PANEL_DATABASE_URL",
    "SMM_PANEL_SUPABASE_DB_URL",
    "SMM_PANEL_ENV",
    "APP_ENV",
    "NODE_ENV",
    "VERCEL",
    "SMM_PANEL_CAFE24_CLIENT_ID",
    "SMM_PANEL_CAFE24_CLIENT_SECRET",
    "SMM_PANEL_CAFE24_REDIRECT_URI",
    "SMM_PANEL_SECRET_ENCRYPTION_KEY",
    "SMM_PANEL_SESSION_SECRET",
    "CRON_SECRET",
    "SMM_PANEL_CRON_SECRET",
)

TokenStatusFn = Callable[[Dict[str, Any]], str]


def _count_rows(conn: Any) -> Dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"] or 0)
        for table in (
            "cafe24_integrations",
            "cafe24_supplier_mappings",
            "cafe24_order_items",
            "suppliers",
            "supplier_services",
            "supplier_orders",
        )
    }


def _integration_payloads(
    rows: list[Dict[str, Any]],
    *,
    token_status: TokenStatusFn,
    token_status_label: TokenStatusFn,
    token_status_message: TokenStatusFn,
) -> list[Dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "mallId": row["mall_id"],
            "shopNo": int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
            "isActive": bool(row["is_active"]),
            "tokenStatus": token_status(row),
            "tokenStatusLabel": token_status_label(row),
            "tokenStatusMessage": token_status_message(row),
            "hasAccessToken": bool(row.get("access_token")),
            "hasRefreshToken": bool(row.get("refresh_token")),
            "expiresAt": row.get("expires_at") or "",
            "refreshTokenExpiresAt": row.get("refresh_token_expires_at") or "",
            "lastPollAt": row.get("last_poll_at") or "",
            "pollCursor": row.get("poll_cursor") or "",
            "autoSubmit": bool(row.get("auto_submit")),
            "completionPolicy": row.get("completion_policy") or "memo_only",
            "lastSyncStatus": row.get("last_sync_status") or "never",
            "lastSyncMessage": row.get("last_sync_message") or "",
            "lastAutoPollAt": row.get("last_auto_poll_at") or "",
            "lastAutoPollStatus": row.get("last_auto_poll_status") or "never",
            "lastAutoPollMessage": row.get("last_auto_poll_message") or "",
            "updatedAt": row.get("updated_at") or "",
        }
        for row in rows
    ]


def _mapping_payloads(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "mallId": row["mall_id"],
            "shopNo": int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
            "cafe24ProductNo": row["cafe24_product_no"] or "",
            "cafe24VariantCode": row["cafe24_variant_code"] or "",
            "cafe24CustomProductCode": row["cafe24_custom_product_code"] or "",
            "supplierId": row["supplier_id"] or "",
            "supplierName": row.get("supplier_name") or "",
            "supplierServiceId": row.get("supplier_service_id") or "",
            "supplierServiceName": row.get("supplier_service_name") or "",
            "supplierExternalServiceId": row.get("supplier_external_service_id") or "",
            "supplierProductUuid": row.get("supplier_product_uuid") or "",
            "autoDispatchEnabled": bool(row.get("auto_dispatch_enabled")),
            "enabled": bool(row.get("enabled")),
            "updatedAt": row.get("updated_at") or "",
        }
        for row in rows
    ]


def _order_item_payloads(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "mallId": row["mall_id"],
            "shopNo": int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO),
            "orderId": row["cafe24_order_id"],
            "orderItemCode": row["cafe24_order_item_code"],
            "productNo": row["cafe24_product_no"],
            "variantCode": row["cafe24_variant_code"],
            "customProductCode": row["cafe24_custom_product_code"],
            "standardStatus": row["standard_status"],
            "paymentGateStatus": row.get("payment_gate_status") or "",
            "paymentStatus": row.get("payment_status") or "",
            "mappingId": row.get("mapping_id") or "",
            "supplierId": row.get("supplier_id") or "",
            "supplierServiceId": row.get("supplier_service_id") or "",
            "supplierExternalServiceId": row.get("supplier_external_service_id") or "",
            "supplierOrderUuid": row.get("supplier_order_uuid") or "",
            "automationErrorCode": row.get("automation_error_code") or "",
            "errorMessage": row.get("error_message") or "",
            "lastSyncedAt": row.get("last_synced_at") or "",
            "lastSubmittedAt": row.get("last_submitted_at") or "",
            "updatedAt": row.get("updated_at") or "",
        }
        for row in rows
    ]


def _supplier_payloads(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "integrationType": normalize_supplier_integration_type(row.get("integration_type")),
            "isActive": bool(row.get("is_active")),
            "lastTestStatus": row.get("last_test_status") or "never",
            "serviceSyncStatus": row.get("service_sync_status") or "never",
            "serviceSyncMessage": row.get("service_sync_message") or "",
            "healthStatus": row.get("health_status") or "unknown",
            "healthMessage": row.get("health_message") or "",
            "balanceStatus": row.get("balance_status") or "unknown",
            "activeServiceCount": int(row.get("active_service_count") or 0),
            "inactiveServiceCount": int(row.get("inactive_service_count") or 0),
        }
        for row in rows
    ]


def build_cafe24_operational_audit(
    conn: Any,
    *,
    db_path: Path,
    runtime_mode: str,
    production_runtime: bool,
    token_status: TokenStatusFn,
    token_status_label: TokenStatusFn,
    token_status_message: TokenStatusFn,
) -> Dict[str, Any]:
    integration_rows = conn.execute("SELECT * FROM cafe24_integrations ORDER BY updated_at DESC").fetchall()
    mapping_rows = conn.execute(
        """
        SELECT
            cm.id, cm.mall_id, cm.shop_no, cm.cafe24_product_no, cm.cafe24_variant_code,
            cm.cafe24_custom_product_code, cm.supplier_id, s.name AS supplier_name,
            cm.supplier_service_id, ss.name AS supplier_service_name,
            cm.supplier_external_service_id, cm.supplier_product_uuid,
            cm.auto_dispatch_enabled, cm.enabled, cm.updated_at
        FROM cafe24_supplier_mappings cm
        LEFT JOIN suppliers s ON s.id = cm.supplier_id
        LEFT JOIN supplier_services ss ON ss.id = cm.supplier_service_id
        ORDER BY cm.updated_at DESC
        LIMIT 50
        """
    ).fetchall()
    order_item_rows = conn.execute(
        """
        SELECT
            id, mall_id, shop_no, cafe24_order_id, cafe24_order_item_code,
            cafe24_product_no, cafe24_variant_code, cafe24_custom_product_code,
            standard_status, payment_gate_status, payment_status,
            mapping_id, supplier_id, supplier_service_id, supplier_external_service_id,
            supplier_order_uuid, automation_error_code, error_message,
            last_synced_at, last_submitted_at, updated_at
        FROM cafe24_order_items
        ORDER BY COALESCE(NULLIF(last_synced_at, ''), updated_at, created_at) DESC
        LIMIT 50
        """
    ).fetchall()
    supplier_rows = conn.execute(
        """
        SELECT
            s.id, s.name, s.integration_type, s.is_active,
            s.last_test_status, s.service_sync_status, s.service_sync_message,
            s.health_status, s.health_message, s.balance_status,
            COUNT(CASE WHEN ss.is_active = 1 THEN ss.id END) AS active_service_count,
            COUNT(CASE WHEN ss.is_active = 0 THEN ss.id END) AS inactive_service_count
        FROM suppliers s
        LEFT JOIN supplier_services ss ON ss.supplier_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        """
    ).fetchall()
    counts = _count_rows(conn)

    integration_payloads = _integration_payloads(
        integration_rows,
        token_status=token_status,
        token_status_label=token_status_label,
        token_status_message=token_status_message,
    )
    mapping_payloads = _mapping_payloads(mapping_rows)
    order_item_payloads = _order_item_payloads(order_item_rows)
    supplier_payloads = _supplier_payloads(supplier_rows)
    database_backend = str(
        getattr(conn, "backend", "")
        or (
            "postgres"
            if os.environ.get("SMM_PANEL_DATABASE_URL") or os.environ.get("SMM_PANEL_SUPABASE_DB_URL")
            else "sqlite"
        )
    )

    return {
        "environment": {
            "runtimeMode": runtime_mode or "local",
            "productionRuntime": production_runtime,
            "databaseBackend": database_backend,
            "sqlitePath": str(db_path) if database_backend == "sqlite" else "",
            "env": {
                key: "set" if os.environ.get(key) else "unset"
                for key in CAFE24_OPERATIONAL_AUDIT_ENV_KEYS
            },
        },
        "counts": counts,
        "cafe24Integrations": integration_payloads,
        "cafe24Mappings": {
            "enabled": sum(1 for row in mapping_payloads if row["enabled"]),
            "autoDispatchEnabled": sum(1 for row in mapping_payloads if row["autoDispatchEnabled"]),
            "recent": mapping_payloads,
        },
        "cafe24OrderItems": {
            "standardStatusCounts": dict(
                Counter(row["standardStatus"] or "unknown" for row in order_item_payloads)
            ),
            "paymentGateStatusCounts": dict(
                Counter(row["paymentGateStatus"] or "unknown" for row in order_item_payloads)
            ),
            "recent": order_item_payloads,
        },
        "suppliers": supplier_payloads,
    }
