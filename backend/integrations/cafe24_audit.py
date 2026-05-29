from __future__ import annotations

from collections import Counter
import datetime as dt
import os
from pathlib import Path
from typing import Any, Callable, Dict

from .cafe24 import (
    CAFE24_DEFAULT_SHOP_NO,
    CAFE24_MANUAL_INPUT_REQUIRED_STATUSES,
    cafe24_status_in_progress,
    cafe24_status_requires_manual_input,
    cafe24_status_requires_review,
)
from .suppliers import normalize_supplier_integration_type, supplier_auto_dispatch_readiness_payload


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
    "SMM_PANEL_GITHUB_CRON_REPOSITORY",
    "SMM_PANEL_GITHUB_OIDC_AUDIENCE",
)

TokenStatusFn = Callable[[Dict[str, Any]], str]


def resolve_cafe24_audit_runtime_mode(raw_mode: Any, *, production_runtime: bool) -> Dict[str, str]:
    mode = str(raw_mode or "").strip().lower()
    if mode:
        return {"runtimeMode": mode, "runtimeModeSource": "env"}
    if production_runtime:
        return {"runtimeMode": "production", "runtimeModeSource": "inferred"}
    return {"runtimeMode": "local", "runtimeModeSource": "default"}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _readiness_check(
    key: str,
    label: str,
    *,
    ok: bool,
    severity: str,
    message: str,
    value: Any = "",
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "ok": bool(ok),
        "severity": "ok" if ok else severity,
        "status": "pass" if ok else "blocked" if severity == "critical" else "warning",
        "value": str(value),
        "message": message,
    }


def _cron_auth_payload(env: Dict[str, str]) -> Dict[str, Any]:
    configured_secret_keys = [
        key
        for key in ("CRON_SECRET", "SMM_PANEL_CRON_SECRET")
        if env.get(key) == "set"
    ]
    expected_repository = str(
        os.environ.get("SMM_PANEL_GITHUB_CRON_REPOSITORY") or "jeongwonho/smmproject"
    ).strip()
    oidc_audience = str(os.environ.get("SMM_PANEL_GITHUB_OIDC_AUDIENCE") or "instamart-cron").strip()
    return {
        "status": "ready" if configured_secret_keys else "github_actions_oidc_only",
        "serverSecretConfigured": bool(configured_secret_keys),
        "configuredSecretKeys": configured_secret_keys,
        "githubActionsVerifier": "oidc",
        "expectedRepository": expected_repository,
        "expectedAudience": oidc_audience,
        "acceptedEvents": ["schedule", "workflow_dispatch"],
        "acceptedBearerSources": ["cron_secret", "github_actions_oidc"],
        "requiredGitHubHeaders": ["X-GitHub-Repository", "X-GitHub-Run-Id"],
        "message": (
            "서버 CRON_SECRET 계열 secret과 GitHub Actions OIDC 토큰을 모두 허용합니다."
            if configured_secret_keys
            else "서버 secret은 없지만 GitHub Actions OIDC 토큰 경로는 사용할 수 있습니다."
        ),
    }


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


def _supplier_readiness_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    return supplier_auto_dispatch_readiness_payload(row)


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
            "autoDispatchReadiness": _supplier_readiness_payload(row),
        }
        for row in rows
    ]


def _supplier_readiness_by_integration(supplier_payloads: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    labels = {
        "mkt24": "MKT24",
        "fasttraffic": "FastTraffic",
        "classic": "classic SMM",
    }
    groups: Dict[str, Dict[str, Any]] = {
        integration_type: {
            "integrationType": integration_type,
            "label": label,
            "supplierCount": 0,
            "activeSupplierCount": 0,
            "readySupplierCount": 0,
            "blockedSupplierCount": 0,
            "retryableSupplierCount": 0,
            "activeServiceCount": 0,
            "inactiveServiceCount": 0,
            "serviceSyncStatuses": [],
            "healthStatuses": [],
            "balanceStatuses": [],
            "blockedCodes": [],
            "reviewCodes": [],
            "nextActions": [],
            "dispatchContract": {},
        }
        for integration_type, label in labels.items()
    }

    def append_unique(values: list[str], value: Any) -> None:
        normalized = str(value or "").strip()
        if normalized and normalized not in values:
            values.append(normalized)

    for supplier in supplier_payloads:
        integration_type = normalize_supplier_integration_type(supplier.get("integrationType"))
        group = groups.setdefault(
            integration_type,
            {
                "integrationType": integration_type,
                "label": labels.get(integration_type, integration_type or "unknown"),
                "supplierCount": 0,
                "activeSupplierCount": 0,
                "readySupplierCount": 0,
                "blockedSupplierCount": 0,
                "retryableSupplierCount": 0,
                "activeServiceCount": 0,
                "inactiveServiceCount": 0,
                "serviceSyncStatuses": [],
                "healthStatuses": [],
                "balanceStatuses": [],
                "blockedCodes": [],
                "reviewCodes": [],
                "nextActions": [],
                "dispatchContract": {},
            },
        )
        readiness = supplier.get("autoDispatchReadiness") or {}
        requirements = readiness.get("requirements") if isinstance(readiness.get("requirements"), list) else []
        group["supplierCount"] += 1
        group["activeSupplierCount"] += 1 if supplier.get("isActive") else 0
        group["readySupplierCount"] += 1 if readiness.get("ok") is True else 0
        group["blockedSupplierCount"] += 1 if readiness.get("ok") is not True else 0
        group["retryableSupplierCount"] += 1 if readiness.get("retryable") else 0
        group["activeServiceCount"] += int(supplier.get("activeServiceCount") or 0)
        group["inactiveServiceCount"] += int(supplier.get("inactiveServiceCount") or 0)
        append_unique(group["serviceSyncStatuses"], supplier.get("serviceSyncStatus") or "never")
        append_unique(group["healthStatuses"], supplier.get("healthStatus") or "unknown")
        append_unique(group["balanceStatuses"], supplier.get("balanceStatus") or "unknown")
        if not group["dispatchContract"] and isinstance(readiness.get("dispatchContract"), dict):
            group["dispatchContract"] = readiness.get("dispatchContract") or {}
        for requirement in requirements:
            if not isinstance(requirement, dict) or requirement.get("ok") is True:
                continue
            target_codes = group["blockedCodes"] if requirement.get("blocking") else group["reviewCodes"]
            append_unique(target_codes, requirement.get("code") or requirement.get("key"))
        for code in readiness.get("reviewCodes") or []:
            append_unique(group["reviewCodes"], code)
        append_unique(group["nextActions"], readiness.get("nextAction") or readiness.get("message"))

    summaries: list[Dict[str, Any]] = []
    for integration_type in ("mkt24", "fasttraffic", "classic"):
        group = groups[integration_type]
        supplier_count = int(group["supplierCount"] or 0)
        blocked_count = int(group["blockedSupplierCount"] or 0)
        if supplier_count <= 0:
            status = "not_configured"
            message = f"{group['label']} 공급사가 아직 없습니다."
        elif blocked_count > 0:
            status = "blocked"
            message = f"{group['label']} 공급사 {blocked_count}곳이 발주 조건을 통과하지 못했습니다."
        elif group["reviewCodes"]:
            status = "review"
            message = f"{group['label']} 공급사는 발주 가능하지만 확인 항목이 남아 있습니다."
        else:
            status = "ready"
            message = f"{group['label']} 공급사 발주 조건이 준비되었습니다."
        summaries.append({**group, "status": status, "message": message})
    return summaries


def _scalar_count(row: Any) -> int:
    if row is None:
        return 0
    return int(row["count"] or 0)


def _order_item_summary(order_items: list[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "readyToSubmitCount": sum(
            1
            for item in order_items
            if item["standardStatus"] == "ready_to_submit"
            and item["paymentGateStatus"] == "payment_confirmed"
            and not item["supplierOrderUuid"]
        ),
        "readyWithSupplierOrderCount": sum(
            1
            for item in order_items
            if item["standardStatus"] == "ready_to_submit"
            and item["paymentGateStatus"] == "payment_confirmed"
            and item["supplierOrderUuid"]
        ),
        "supplierOrderLinkedCount": sum(1 for item in order_items if item["supplierOrderUuid"]),
        "manualInputRequiredCount": sum(
            1
            for item in order_items
            if item["paymentGateStatus"] == "payment_confirmed"
            and not item["supplierOrderUuid"]
            and cafe24_status_requires_manual_input(item["standardStatus"])
        ),
        "reviewRequiredCount": sum(1 for item in order_items if cafe24_status_requires_review(item["standardStatus"])),
        "inProgressCount": sum(
            1
            for item in order_items
            if cafe24_status_in_progress(item["standardStatus"])
        ),
        "completedCount": sum(1 for item in order_items if item["standardStatus"] == "completed"),
        "failedCount": sum(1 for item in order_items if item["standardStatus"] == "failed"),
    }


def _manual_input_candidate_payloads(
    conn: Any,
    *,
    manual_statuses: list[str],
    limit: int = 8,
) -> list[Dict[str, Any]]:
    safe_limit = min(max(int(limit or 8), 1), 20)
    placeholders = ", ".join("?" for _ in manual_statuses)
    rows = conn.execute(
        f"""
        SELECT
            coi.id, coi.mall_id, coi.shop_no, coi.cafe24_order_id, coi.cafe24_order_item_code,
            coi.cafe24_product_no, coi.cafe24_variant_code, coi.cafe24_custom_product_code,
            coi.standard_status, coi.payment_gate_status, coi.supplier_id, coi.supplier_service_id,
            coi.supplier_external_service_id, coi.automation_error_code, coi.error_message,
            coi.last_synced_at, coi.updated_at
        FROM cafe24_order_items coi
        JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
        WHERE ci.is_active = 1
          AND coi.payment_gate_status = 'payment_confirmed'
          AND COALESCE(coi.supplier_order_uuid, '') = ''
          AND coi.standard_status IN ({placeholders})
        ORDER BY COALESCE(NULLIF(coi.last_synced_at, ''), coi.updated_at, coi.created_at) DESC
        LIMIT {safe_limit}
        """,
        manual_statuses,
    ).fetchall()
    return [_workflow_candidate_payload(row, manual=True) for row in rows]


def _dispatch_candidate_payloads(conn: Any, *, limit: int = 8) -> list[Dict[str, Any]]:
    safe_limit = min(max(int(limit or 8), 1), 20)
    rows = conn.execute(
        f"""
        SELECT
            coi.id, coi.mall_id, coi.shop_no, coi.cafe24_order_id, coi.cafe24_order_item_code,
            coi.cafe24_product_no, coi.cafe24_variant_code, coi.cafe24_custom_product_code,
            coi.standard_status, coi.payment_gate_status, coi.supplier_id, coi.supplier_service_id,
            coi.supplier_external_service_id, coi.automation_error_code, coi.error_message,
            coi.last_synced_at, coi.updated_at
        FROM cafe24_order_items coi
        JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
        WHERE ci.is_active = 1
          AND coi.payment_gate_status = 'payment_confirmed'
          AND coi.standard_status IN ('ready_to_submit', 'failed')
          AND COALESCE(coi.supplier_order_uuid, '') = ''
          AND COALESCE(coi.supplier_id, '') <> ''
          AND COALESCE(coi.supplier_external_service_id, '') <> ''
        ORDER BY COALESCE(NULLIF(coi.last_synced_at, ''), coi.updated_at, coi.created_at) DESC
        LIMIT {safe_limit}
        """
    ).fetchall()
    return [_workflow_candidate_payload(row, manual=False) for row in rows]


def _workflow_candidate_payload(row: Dict[str, Any], *, manual: bool) -> Dict[str, Any]:
    mall_id = row["mall_id"]
    shop_no = int(row["shop_no"] or CAFE24_DEFAULT_SHOP_NO)
    order_id = row["cafe24_order_id"]
    order_item_code = row["cafe24_order_item_code"]
    base_inputs = {
        "mall_id": mall_id,
        "shop_no": str(shop_no),
        "order_id": order_id,
        "order_item_code": order_item_code,
    }
    if manual:
        workflow_inputs = {
            **base_inputs,
            "supplier_id": row.get("supplier_id") or "<select supplier>",
            "supplier_service_id": row.get("supplier_service_id") or "<select supplier service>",
            "target_secret_name": "CAFE24_MANUAL_TARGET_VALUE",
            "ordered_count": "<confirm quantity>",
            "expected_quantity": "<same as ordered_count>",
            "dispatch_after_save": "false",
        }
        next_workflow = "Cafe24 Manual Input Preview One"
        required_inputs = [
            key
            for key, value in workflow_inputs.items()
            if str(value or "").startswith("<")
        ]
    else:
        workflow_inputs = {
            **base_inputs,
            "expected_quantity": "<confirm quantity>",
        }
        next_workflow = "Cafe24 Preflight One"
        required_inputs = ["expected_quantity"]
    return {
        "id": row["id"],
        "mallId": mall_id,
        "shopNo": shop_no,
        "orderId": order_id,
        "orderItemCode": order_item_code,
        "productNo": row["cafe24_product_no"],
        "variantCode": row["cafe24_variant_code"] or "",
        "customProductCode": row["cafe24_custom_product_code"] or "",
        "standardStatus": row["standard_status"] or "",
        "paymentGateStatus": row["payment_gate_status"] or "",
        "supplierId": row.get("supplier_id") or "",
        "supplierServiceId": row.get("supplier_service_id") or "",
        "supplierExternalServiceId": row.get("supplier_external_service_id") or "",
        "automationErrorCode": row.get("automation_error_code") or "",
        "errorMessage": row.get("error_message") or "",
        "lastSyncedAt": row.get("last_synced_at") or row.get("updated_at") or "",
        "nextWorkflow": next_workflow,
        "workflowInputs": workflow_inputs,
        "requiredInputs": required_inputs,
    }


def _dispatch_policy_payload(
    conn: Any,
    *,
    integration_payloads: list[Dict[str, Any]],
) -> Dict[str, Any]:
    active_integrations = [item for item in integration_payloads if item["isActive"]]
    auto_submit_integrations = [item for item in active_integrations if item["autoSubmit"]]
    auto_dispatch_mapping_count = _scalar_count(
        conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM cafe24_supplier_mappings
            WHERE enabled = 1 AND auto_dispatch_enabled = 1
            """
        ).fetchone()
    )
    ready_filter = """
        FROM cafe24_order_items coi
        JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
        WHERE ci.is_active = 1
          AND coi.payment_gate_status = 'payment_confirmed'
          AND coi.standard_status IN ('ready_to_submit', 'failed')
          AND coi.supplier_order_uuid = ''
          AND coi.supplier_id <> ''
          AND coi.supplier_external_service_id <> ''
    """
    ready_item_count = _scalar_count(conn.execute(f"SELECT COUNT(*) AS count {ready_filter}").fetchone())
    auto_submit_ready_item_count = _scalar_count(
        conn.execute(f"SELECT COUNT(*) AS count {ready_filter} AND ci.auto_submit = 1").fetchone()
    )
    manual_ready_item_count = _scalar_count(
        conn.execute(f"SELECT COUNT(*) AS count {ready_filter} AND ci.auto_submit <> 1").fetchone()
    )

    if not active_integrations:
        status = "no_active_integration"
        message = "활성 Cafe24 연동이 없어 자동 발주가 실행되지 않습니다."
    elif auto_submit_integrations:
        status = "auto_submit_enabled"
        message = "활성 Cafe24 연동의 autoSubmit이 켜져 있어 준비된 품주는 자동 발주 대상입니다."
    elif auto_dispatch_mapping_count:
        status = "manual_approval_mode"
        message = "매핑은 자동 발주 허용 상태지만 Cafe24 연동 autoSubmit이 꺼져 있어 품주는 수동 승인/단건 발주로 처리됩니다."
    else:
        status = "manual_mapping_mode"
        message = "Cafe24 연동 autoSubmit과 매핑 자동 발주가 모두 꺼져 있어 운영자가 수동으로 발주해야 합니다."

    return {
        "status": status,
        "message": message,
        "activeIntegrationCount": len(active_integrations),
        "autoSubmitIntegrationCount": len(auto_submit_integrations),
        "autoDispatchMappingCount": auto_dispatch_mapping_count,
        "readyItemCount": ready_item_count,
        "autoSubmitReadyItemCount": auto_submit_ready_item_count,
        "manualReadyItemCount": manual_ready_item_count,
        "canAutoDispatchNow": bool(auto_submit_integrations),
    }


def _manual_workflow_payload(
    conn: Any,
    *,
    integration_payloads: list[Dict[str, Any]],
    supplier_payloads: list[Dict[str, Any]],
    dispatch_policy: Dict[str, Any],
) -> Dict[str, Any]:
    active_integrations = [item for item in integration_payloads if item.get("isActive")]
    connected_integrations = [
        item
        for item in active_integrations
        if item.get("tokenStatus") in {"connected", "token_expiring"}
    ]
    supplier_ready_count = sum(
        1
        for item in supplier_payloads
        if bool((item.get("autoDispatchReadiness") or {}).get("ok"))
    )
    manual_statuses = sorted(CAFE24_MANUAL_INPUT_REQUIRED_STATUSES)
    manual_placeholders = ", ".join("?" for _ in manual_statuses)
    active_item_join = """
        FROM cafe24_order_items coi
        JOIN cafe24_integrations ci ON ci.mall_id = coi.mall_id AND ci.shop_no = coi.shop_no
        WHERE ci.is_active = 1
    """
    manual_input_required_count = _scalar_count(
        conn.execute(
            f"""
            SELECT COUNT(*) AS count
            {active_item_join}
              AND coi.payment_gate_status = 'payment_confirmed'
              AND coi.supplier_order_uuid = ''
              AND coi.standard_status IN ({manual_placeholders})
            """,
            manual_statuses,
        ).fetchone()
    )
    mapping_required_count = _scalar_count(
        conn.execute(
            f"""
            SELECT COUNT(*) AS count
            {active_item_join}
              AND coi.payment_gate_status = 'payment_confirmed'
              AND coi.supplier_order_uuid = ''
              AND (coi.mapping_id = '' OR coi.mapping_id IS NULL)
              AND (coi.supplier_service_id = '' OR coi.supplier_service_id IS NULL)
            """
        ).fetchone()
    )
    manual_input_candidates = _manual_input_candidate_payloads(
        conn,
        manual_statuses=manual_statuses,
    )
    dispatch_candidates = _dispatch_candidate_payloads(conn)
    ready_with_supplier_order_count = _scalar_count(
        conn.execute(
            f"""
            SELECT COUNT(*) AS count
            {active_item_join}
              AND coi.payment_gate_status = 'payment_confirmed'
              AND coi.standard_status = 'ready_to_submit'
              AND coi.supplier_order_uuid <> ''
            """
        ).fetchone()
    )
    dispatch_ready_count = int(dispatch_policy.get("readyItemCount") or 0)
    if not active_integrations:
        status = "blocked"
        next_workflow = "Cafe24 OAuth"
        next_action = "Cafe24 활성 연동을 먼저 연결하세요."
    elif not connected_integrations:
        status = "blocked"
        next_workflow = "Cafe24 OAuth"
        next_action = "Cafe24 token 재연결 후 상품 조회와 주문 수집을 다시 확인하세요."
    elif dispatch_ready_count > 0 and supplier_ready_count > 0:
        status = "dispatch_ready"
        next_workflow = "Cafe24 Dispatch One"
        next_action = "preflight 통과 품주를 단건 발주 workflow 또는 관리자 버튼으로 처리할 수 있습니다."
    elif dispatch_ready_count > 0 or manual_input_required_count > 0 and supplier_ready_count <= 0:
        status = "supplier_readiness_required"
        next_workflow = "Supplier Service Sync"
        next_action = "발주 후보는 있지만 발주 가능한 공급사 readiness가 부족합니다. service sync와 health check를 먼저 실행하세요."
    elif manual_input_required_count > 0:
        status = "manual_input_required"
        next_workflow = "Cafe24 Manual Input Preview One"
        next_action = "고객 대상값은 workflow secret에 넣고 preview 통과 후 manual input 저장/단건 발주를 진행하세요."
    elif mapping_required_count > 0:
        status = "mapping_required"
        next_workflow = "Cafe24 Mapping Gaps"
        next_action = "상품/품목코드와 공급사 서비스를 매핑한 뒤 payload preview를 실행하세요."
    elif ready_with_supplier_order_count > 0:
        status = "supplier_status_required"
        next_workflow = "Cafe24 Check Supplier Status"
        next_action = "공급사 주문번호가 있는 품주는 중복 발주하지 말고 상태 조회와 완료 처리만 확인하세요."
    else:
        status = "waiting_for_orders"
        next_workflow = "Cafe24 Order Poll"
        next_action = "현재 즉시 처리할 Cafe24 품주가 없습니다. 주문 수집과 mapping gaps 결과를 주기적으로 확인하세요."

    return {
        "status": status,
        "nextWorkflow": next_workflow,
        "nextAction": next_action,
        "dispatchReadyCount": dispatch_ready_count,
        "manualInputRequiredCount": manual_input_required_count,
        "mappingRequiredCount": mapping_required_count,
        "readyWithSupplierOrderCount": ready_with_supplier_order_count,
        "supplierReadyCount": supplier_ready_count,
        "activeIntegrationCount": len(active_integrations),
        "connectedIntegrationCount": len(connected_integrations),
        "canDispatchWithoutManualInput": dispatch_ready_count > 0 and supplier_ready_count > 0,
        "canRunManualInputToDispatch": manual_input_required_count > 0 and supplier_ready_count > 0,
        "candidateLimit": 8,
        "manualInputCandidates": manual_input_candidates,
        "dispatchCandidates": dispatch_candidates,
        "secretVisibility": "repository_secrets_not_visible_from_app_runtime",
        "requiredSecretNames": [
            "CAFE24_MANUAL_TARGET_VALUE",
            "CAFE24_MANUAL_TARGET_VALUE_2",
            "CAFE24_MANUAL_TARGET_VALUE_3",
        ],
        "safeInputRule": "고객 대상 URL/계정은 workflow input이 아니라 allow-list된 repository secret으로만 전달합니다.",
    }


def _integration_has_recent_api_failure(item: Dict[str, Any]) -> bool:
    auto_poll_status = str(item.get("lastAutoPollStatus") or "").strip()
    if auto_poll_status == "failed":
        return True
    if auto_poll_status in {"success", "running", "in_progress", "processing"}:
        return False
    return str(item.get("lastSyncStatus") or "").strip() == "failed"


def _operational_readiness_payload(
    *,
    environment: Dict[str, Any],
    counts: Dict[str, int],
    integration_payloads: list[Dict[str, Any]],
    mapping_payloads: list[Dict[str, Any]],
    order_item_payloads: list[Dict[str, Any]],
    order_item_summary: Dict[str, int],
    supplier_payloads: list[Dict[str, Any]],
    dispatch_policy: Dict[str, Any],
) -> Dict[str, Any]:
    env = environment.get("env") or {}
    active_integrations = [item for item in integration_payloads if item.get("isActive")]
    connected_integrations = [
        item
        for item in active_integrations
        if item.get("tokenStatus") in {"connected", "token_expiring"}
    ]
    reconnect_integrations = [
        item
        for item in active_integrations
        if item.get("tokenStatus") in {"reconnect_required", "failed"}
    ]
    sync_failed_integrations = [
        item
        for item in active_integrations
        if _integration_has_recent_api_failure(item)
    ]
    cafe24_env_keys = (
        "SMM_PANEL_CAFE24_CLIENT_ID",
        "SMM_PANEL_CAFE24_CLIENT_SECRET",
        "SMM_PANEL_CAFE24_REDIRECT_URI",
    )
    missing_cafe24_env = [key for key in cafe24_env_keys if env.get(key) != "set"]
    enabled_mapping_count = sum(1 for item in mapping_payloads if item.get("enabled"))
    mapped_order_item_count = sum(1 for item in order_item_payloads if item.get("mappingId"))
    ready_count = int(order_item_summary.get("readyToSubmitCount") or 0)
    manual_count = int(order_item_summary.get("manualInputRequiredCount") or 0)
    review_count = int(order_item_summary.get("reviewRequiredCount") or 0)
    failed_count = int(order_item_summary.get("failedCount") or 0)
    supplier_blocked = [
        item
        for item in supplier_payloads
        if not bool((item.get("autoDispatchReadiness") or {}).get("ok"))
    ]
    supplier_retryable = [
        item
        for item in supplier_blocked
        if bool((item.get("autoDispatchReadiness") or {}).get("retryable"))
    ]
    checks = [
        _readiness_check(
            "database_backend",
            "운영 DB 연결",
            ok=environment.get("databaseBackend") != "sqlite" or not environment.get("productionRuntime"),
            severity="critical",
            value=environment.get("databaseBackend") or "unknown",
            message=(
                "운영 런타임에서 SQLite를 사용 중입니다. 운영 DB 연결 환경변수를 확인하세요."
                if environment.get("databaseBackend") == "sqlite" and environment.get("productionRuntime")
                else "현재 audit이 DB backend를 확인했습니다."
            ),
        ),
        _readiness_check(
            "cafe24_oauth_env",
            "Cafe24 OAuth 환경변수",
            ok=not missing_cafe24_env,
            severity="critical",
            value=", ".join(missing_cafe24_env),
            message=(
                "Cafe24 OAuth 필수 환경변수가 빠져 토큰 재연결/갱신이 막힐 수 있습니다."
                if missing_cafe24_env
                else "Cafe24 OAuth 필수 환경변수가 설정되어 있습니다."
            ),
        ),
        _readiness_check(
            "active_integration",
            "활성 Cafe24 연동",
            ok=bool(active_integrations),
            severity="critical",
            value=len(active_integrations),
            message=(
                "활성 Cafe24 연동이 없어 주문 수집과 발주 자동화가 실행되지 않습니다."
                if not active_integrations
                else "활성 Cafe24 연동이 있습니다."
            ),
        ),
        _readiness_check(
            "token_status",
            "Cafe24 token status",
            ok=bool(connected_integrations) and not reconnect_integrations,
            severity="critical",
            value=f"connected={len(connected_integrations)}, reconnect={len(reconnect_integrations)}",
            message=(
                "재연결이 필요한 Cafe24 token이 있습니다."
                if reconnect_integrations
                else "사용 가능한 Cafe24 token이 없습니다."
                if not connected_integrations
                else "Cafe24 token이 주문 수집 가능한 상태입니다."
            ),
        ),
        _readiness_check(
            "cafe24_api_health",
            "최근 Cafe24 API 상태",
            ok=not sync_failed_integrations,
            severity="warning",
            value=len(sync_failed_integrations),
            message=(
                "최근 Cafe24 API 호출 실패가 있습니다. lastSyncMessage/lastAutoPollMessage와 mapping-gaps 경고를 확인하세요."
                if sync_failed_integrations
                else "최근 Cafe24 API 상태에 실패 기록이 없습니다."
            ),
        ),
        _readiness_check(
            "product_mapping",
            "Cafe24 상품 매핑",
            ok=enabled_mapping_count > 0,
            severity="warning",
            value=enabled_mapping_count,
            message=(
                "활성 Cafe24 상품 매핑이 없어 수집된 품주가 발주 후보로 전환되지 않습니다."
                if enabled_mapping_count <= 0
                else "활성 Cafe24 상품 매핑이 있습니다."
            ),
        ),
        _readiness_check(
            "order_collection",
            "최근 주문 품주",
            ok=counts.get("cafe24_order_items", 0) > 0,
            severity="warning",
            value=counts.get("cafe24_order_items", 0),
            message=(
                "저장된 Cafe24 주문 품주가 없어 실제 수집 상태를 판단할 수 없습니다."
                if counts.get("cafe24_order_items", 0) <= 0
                else "Cafe24 주문 품주가 저장되어 있습니다."
            ),
        ),
        _readiness_check(
            "mapped_order_items",
            "최근 품주 매핑",
            ok=mapped_order_item_count > 0 or counts.get("cafe24_order_items", 0) == 0,
            severity="warning",
            value=mapped_order_item_count,
            message=(
                "최근 품주에 매핑된 항목이 없어 mapping gap을 먼저 확인해야 합니다."
                if mapped_order_item_count <= 0 and counts.get("cafe24_order_items", 0) > 0
                else "최근 품주의 매핑 상태가 확인되었습니다."
            ),
        ),
        _readiness_check(
            "dispatch_policy",
            "발주 정책",
            ok=bool(dispatch_policy.get("canAutoDispatchNow")) or dispatch_policy.get("status") in {"manual_approval_mode", "manual_mapping_mode"},
            severity="warning",
            value=dispatch_policy.get("status") or "unknown",
            message=dispatch_policy.get("message") or "Cafe24 발주 정책을 확인해야 합니다.",
        ),
        _readiness_check(
            "ready_queue",
            "발주 대기 큐",
            ok=ready_count > 0,
            severity="warning",
            value=ready_count,
            message=(
                "현재 발주 대기 품주가 없습니다. 수집/매핑이 정상이어도 즉시 발주 검증할 대상은 없습니다."
                if ready_count <= 0
                else "발주 대기 품주가 있습니다."
            ),
        ),
        _readiness_check(
            "operator_actions",
            "운영자 조치 품주",
            ok=manual_count == 0 and review_count == 0 and failed_count == 0,
            severity="warning",
            value=f"manual={manual_count}, review={review_count}, failed={failed_count}",
            message=(
                "수동 입력/검토/실패 품주가 있어 큐 정리가 필요합니다."
                if manual_count or review_count or failed_count
                else "수동 조치가 필요한 최근 품주가 없습니다."
            ),
        ),
        _readiness_check(
            "supplier_readiness",
            "공급사 readiness",
            ok=not supplier_blocked,
            severity="warning",
            value=f"blocked={len(supplier_blocked)}, retryable={len(supplier_retryable)}",
            message=(
                "발주 차단 상태의 공급사가 있습니다. service sync/health/API key를 확인하세요."
                if supplier_blocked
                else "공급사 readiness 차단 항목이 없습니다."
            ),
        ),
    ]
    blocked = [item for item in checks if item["status"] == "blocked"]
    warnings = [item for item in checks if item["status"] == "warning"]
    if blocked:
        status = "blocked"
        message = f"운영 필수 조건 {len(blocked)}개가 막혀 있습니다."
    elif warnings:
        status = "review"
        message = f"운영 확인 항목 {len(warnings)}개가 남아 있습니다."
    else:
        status = "ready"
        message = "Cafe24 운영 상태가 발주 검증 가능한 상태입니다."
    return {
        "status": status,
        "message": message,
        "blockedCount": len(blocked),
        "warningCount": len(warnings),
        "checks": checks,
    }


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
            s.id, s.name, s.integration_type, s.api_url, s.is_active,
            s.api_key,
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
    supplier_readiness_by_integration = _supplier_readiness_by_integration(supplier_payloads)
    dispatch_policy = _dispatch_policy_payload(conn, integration_payloads=integration_payloads)
    manual_workflow = _manual_workflow_payload(
        conn,
        integration_payloads=integration_payloads,
        supplier_payloads=supplier_payloads,
        dispatch_policy=dispatch_policy,
    )
    order_item_summary = _order_item_summary(order_item_payloads)
    database_backend = str(
        getattr(conn, "backend", "")
        or (
            "postgres"
            if os.environ.get("SMM_PANEL_DATABASE_URL") or os.environ.get("SMM_PANEL_SUPABASE_DB_URL")
            else "sqlite"
        )
    )
    runtime_payload = resolve_cafe24_audit_runtime_mode(runtime_mode, production_runtime=production_runtime)
    env_statuses = {
        key: "set" if os.environ.get(key) else "unset"
        for key in CAFE24_OPERATIONAL_AUDIT_ENV_KEYS
    }
    environment = {
        **runtime_payload,
        "productionRuntime": production_runtime,
        "databaseBackend": database_backend,
        "sqlitePath": str(db_path) if database_backend == "sqlite" else "",
        "cronAuth": _cron_auth_payload(env_statuses),
        "env": env_statuses,
    }
    operational_readiness = _operational_readiness_payload(
        environment=environment,
        counts=counts,
        integration_payloads=integration_payloads,
        mapping_payloads=mapping_payloads,
        order_item_payloads=order_item_payloads,
        order_item_summary=order_item_summary,
        supplier_payloads=supplier_payloads,
        dispatch_policy=dispatch_policy,
    )

    return {
        "fetchedAt": _now_iso(),
        "environment": environment,
        "operationalReadiness": operational_readiness,
        "counts": counts,
        "cafe24Integrations": integration_payloads,
        "cafe24Mappings": {
            "enabled": sum(1 for row in mapping_payloads if row["enabled"]),
            "autoDispatchEnabled": sum(1 for row in mapping_payloads if row["autoDispatchEnabled"]),
            "recent": mapping_payloads,
        },
        "cafe24DispatchPolicy": dispatch_policy,
        "cafe24ManualWorkflow": manual_workflow,
        "cafe24OrderItems": {
            "summary": order_item_summary,
            "standardStatusCounts": dict(
                Counter(row["standardStatus"] or "unknown" for row in order_item_payloads)
            ),
            "paymentGateStatusCounts": dict(
                Counter(row["paymentGateStatus"] or "unknown" for row in order_item_payloads)
            ),
            "recent": order_item_payloads,
        },
        "supplierReadinessByIntegration": supplier_readiness_by_integration,
        "suppliers": supplier_payloads,
    }
