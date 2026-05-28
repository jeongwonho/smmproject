import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) in sys.path:
    sys.path.remove(str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT))

from server import AppHandler, ROUTER, RouteRequest, cron_authorization_valid
from core import PanelError, derive_order_idempotency_key


class FakeGithubResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class VercelRewriteRoutingTest(unittest.TestCase):
    def test_incoming_request_path_preserves_oauth_query_after_vercel_rewrite(self):
        path = AppHandler._incoming_request_path(
            None,
            "/api/index.py?__path=/api/admin/cafe24/oauth/callback&code=abc123&state=state456",
        )

        self.assertEqual(path, "/api/admin/cafe24/oauth/callback?code=abc123&state=state456")

    def test_incoming_request_path_preserves_regular_api_query_after_vercel_rewrite(self):
        path = AppHandler._incoming_request_path(None, "/api/index.py?__path=/api/products&q=instagram")

        self.assertEqual(path, "/api/products?q=instagram")


class OrderIdempotencyTest(unittest.TestCase):
    def test_derived_order_idempotency_key_is_stable_with_sorted_fields(self):
        first = derive_order_idempotency_key(
            "user_1",
            "product_1",
            {"targetValue": "  instamart  ", "orderedCount": 100},
            now_seconds=120,
        )
        second = derive_order_idempotency_key(
            "user_1",
            "product_1",
            {"orderedCount": "100", "targetValue": "instamart"},
            now_seconds=121,
        )

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("auto:"))

    def test_derived_order_idempotency_key_rotates_by_time_window(self):
        first = derive_order_idempotency_key("user_1", "product_1", {"targetValue": "instamart"}, now_seconds=119)
        second = derive_order_idempotency_key("user_1", "product_1", {"targetValue": "instamart"}, now_seconds=120)

        self.assertNotEqual(first, second)


class Cafe24AdminManualInputHandlerTest(unittest.TestCase):
    def test_admin_preflight_writes_store_result(self):
        class FakeStore:
            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {"canDispatch": True, "blockingReasons": []}

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

            def _write_store_result(self, method_name, payload):
                return AppHandler._write_store_result(self, method_name, payload)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/admin/cafe24/order-items/preflight",
            parsed=None,
            query={},
            params={},
            payload={"itemId": "cafe24_item_1", "expectedQuantity": "50", "_adminActor": "operator"},
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_admin_cafe24_order_items_preflight(handler, request)

        self.assertEqual(
            handler.store.preflight_payload,
            {"itemId": "cafe24_item_1", "expectedQuantity": "50", "_adminActor": "operator"},
        )
        write_json_mock.assert_called_once()
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["canDispatch"])

    def test_admin_manual_input_runs_preflight_after_save(self):
        class FakeStore:
            def save_cafe24_order_item_manual_input(self, payload):
                self.saved_payload = payload
                return {
                    "item": {"id": "cafe24_item_1", "standardStatus": "ready_to_submit"},
                    "normalizedFields": {"orderedCount": "50"},
                    "supplierPayload": {"link": "https://example.com/target", "quantity": "50", "service": "svc-1"},
                }

            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {"canDispatch": True, "blockingReasons": [], "quantity": {"normalized": 50}}

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/admin/cafe24/order-items/manual-input",
            parsed=None,
            query={},
            params={},
            payload={
                "itemId": "cafe24_item_1",
                "supplierId": "supplier_1",
                "supplierServiceId": "service_1",
                "orderedCount": "50",
                "_adminActor": "operator",
            },
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_admin_cafe24_order_items_manual_input(handler, request)

        self.assertEqual(handler.store.saved_payload["_adminActor"], "operator")
        self.assertEqual(
            handler.store.preflight_payload,
            {"itemId": "cafe24_item_1", "expectedQuantity": "50", "_adminActor": "operator"},
        )
        write_json_mock.assert_called_once()
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["preflight"]["canDispatch"])

    def test_admin_manual_input_preview_writes_store_result(self):
        class FakeStore:
            def preview_cafe24_order_item_manual_input(self, payload):
                self.preview_payload = payload
                return {"dryRun": True, "preflight": {"canDispatch": True}}

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

            def _write_store_result(self, method_name, payload):
                return AppHandler._write_store_result(self, method_name, payload)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/admin/cafe24/order-items/manual-input/preview",
            parsed=None,
            query={},
            params={},
            payload={"itemId": "cafe24_item_1", "orderedCount": "50", "_adminActor": "operator"},
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_admin_cafe24_order_items_manual_input_preview(handler, request)

        self.assertEqual(
            handler.store.preview_payload,
            {"itemId": "cafe24_item_1", "orderedCount": "50", "_adminActor": "operator"},
        )
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["dryRun"])

    def test_cron_manual_input_preview_requires_confirmation(self):
        class FakeHandler:
            def _server(self):
                return SimpleNamespace(store=SimpleNamespace())

        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input/preview",
            parsed=None,
            query={},
            params={},
            payload={"itemId": "cafe24_item_1"},
        )

        with self.assertRaises(PanelError) as context:
            AppHandler._post_cron_cafe24_order_items_manual_input_preview(FakeHandler(), request)

        self.assertEqual(context.exception.status, 400)
        self.assertIn("confirmManualInputPreview=true", str(context.exception))

    def test_cron_manual_input_preview_response_does_not_expose_target_values(self):
        class FakeStore:
            def preview_cafe24_order_item_manual_input(self, payload):
                self.preview_payload = payload
                return {
                    "dryRun": True,
                    "itemId": "cafe24_item_1",
                    "normalizedFields": {"orderedCount": "50", "targetValue": "<redacted>"},
                    "supplierPayload": {"link": "<redacted>", "quantity": "50", "service": "svc-1"},
                    "preflight": {"canDispatch": True, "blockingReasons": []},
                }

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input/preview",
            parsed=None,
            query={},
            params={},
            payload={
                "itemId": "cafe24_item_1",
                "supplierId": "supplier_1",
                "supplierServiceId": "service_1",
                "targetValue": "private_account",
                "orderedCount": "50",
                "confirmManualInputPreview": True,
            },
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_cron_cafe24_order_items_manual_input_preview(handler, request)

        self.assertEqual(handler.store.preview_payload["_adminActor"], "cron")
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["dryRun"])
        rendered = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("private_account", rendered)

    def test_cron_manual_input_requires_confirmation(self):
        class FakeHandler:
            def _server(self):
                return SimpleNamespace(store=SimpleNamespace())

        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input",
            parsed=None,
            query={},
            params={},
            payload={"itemId": "cafe24_item_1"},
        )

        with self.assertRaises(PanelError) as context:
            AppHandler._post_cron_cafe24_order_items_manual_input(FakeHandler(), request)

        self.assertEqual(context.exception.status, 400)
        self.assertIn("confirmManualInput=true", str(context.exception))

    def test_cron_manual_input_response_does_not_expose_target_values(self):
        class FakeStore:
            def save_cafe24_order_item_manual_input(self, payload):
                self.saved_payload = payload
                return {
                    "item": {"id": "cafe24_item_1", "standardStatus": "ready_to_submit"},
                    "normalizedFields": {"orderedCount": "50", "targetValue": "private_account"},
                    "supplierPayload": {
                        "link": "https://instagram.com/private_account",
                        "quantity": "50",
                        "service": "svc-1",
                    },
                }

            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {
                    "canDispatch": True,
                    "blockingReasons": [],
                    "quantity": {"normalized": 50},
                    "supplierPayload": {"keys": ["link", "quantity", "service"], "service": "svc-1", "hasTarget": True, "hasQuantity": True},
                }

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input",
            parsed=None,
            query={},
            params={},
            payload={
                "itemId": "cafe24_item_1",
                "supplierId": "supplier_1",
                "supplierServiceId": "service_1",
                "targetValue": "private_account",
                "orderedCount": "50",
                "confirmManualInput": True,
            },
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_cron_cafe24_order_items_manual_input(handler, request)

        self.assertEqual(handler.store.saved_payload["_adminActor"], "cron")
        self.assertEqual(
            handler.store.preflight_payload,
            {"itemId": "cafe24_item_1", "expectedQuantity": "50", "_adminActor": "cron"},
        )
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        rendered = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("private_account", rendered)
        self.assertNotIn("instagram.com/private_account", rendered)
        self.assertEqual(body["normalizedFields"], {"keys": ["orderedCount", "targetValue"], "orderedCount": "50"})
        self.assertEqual(body["supplierPayload"]["service"], "svc-1")
        self.assertTrue(body["supplierPayload"]["hasTarget"])
        self.assertTrue(body["preflight"]["canDispatch"])

    def test_cron_manual_input_can_dispatch_after_preflight(self):
        class FakeStore:
            def save_cafe24_order_item_manual_input(self, payload):
                self.saved_payload = payload
                return {
                    "item": {"id": "cafe24_item_1", "standardStatus": "ready_to_submit"},
                    "normalizedFields": {"orderedCount": "50", "targetValue": "private_account"},
                    "supplierPayload": {
                        "link": "https://instagram.com/private_account",
                        "quantity": "50",
                        "service": "svc-1",
                    },
                }

            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {
                    "canDispatch": True,
                    "blockingReasons": [],
                    "quantity": {"normalized": 50},
                    "supplierPayload": {"keys": ["link", "quantity", "service"], "service": "svc-1", "hasTarget": True, "hasQuantity": True},
                }

            def dispatch_cafe24_order_item(self, payload):
                self.dispatch_payload = payload
                return {
                    "id": "cafe24_item_1",
                    "status": "supplier_submitted",
                    "submitted": True,
                    "supplierOrderUuid": "supplier-order-1",
                }

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input",
            parsed=None,
            query={},
            params={},
            payload={
                "itemId": "cafe24_item_1",
                "supplierId": "supplier_1",
                "supplierServiceId": "service_1",
                "targetValue": "private_account",
                "orderedCount": "50",
                "confirmManualInput": True,
                "dispatchAfterSave": True,
            },
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_cron_cafe24_order_items_manual_input(handler, request)

        self.assertEqual(handler.store.dispatch_payload, {"itemId": "cafe24_item_1", "_adminActor": "cron"})
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["dispatchAfterSave"])
        self.assertTrue(body["dispatch"]["submitted"])
        rendered = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("private_account", rendered)
        self.assertNotIn("instagram.com/private_account", rendered)


class SupplierCronSyncHandlerTest(unittest.TestCase):
    def test_cron_supplier_sync_passes_bounded_request_timeout(self):
        class FakeStore:
            def sync_due_supplier_services(self, **kwargs):
                self.kwargs = kwargs
                return {"checked": 0, "synced": 0, "failed": 0, "skipped": 0, "results": []}

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/cron/suppliers/sync",
            parsed=None,
            query={},
            params={},
            payload={"limit": 3, "requestTimeoutSeconds": 5},
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_cron_supplier_sync(handler, request)

        self.assertEqual(handler.store.kwargs["actor"], "cron")
        self.assertEqual(handler.store.kwargs["limit"], 3)
        self.assertEqual(handler.store.kwargs["request_timeout_seconds"], 5.0)
        write_json_mock.assert_called_once()


class WorkflowConfigurationTest(unittest.TestCase):
    def test_supplier_catalog_sync_workflow_sends_request_timeout(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "supplier-service-sync.yml").read_text()

        self.assertIn("request_timeout_seconds:", workflow)
        self.assertIn("REQUEST_TIMEOUT_SECONDS", workflow)
        self.assertIn("requestTimeoutSeconds:$requestTimeoutSeconds", workflow)
        self.assertIn("--max-time 120", workflow)

    def test_production_cron_workflows_allow_secret_or_github_oidc_auth(self):
        workflow_names = [
            "cafe24-check-supplier-status.yml",
            "cafe24-dispatch-one.yml",
            "cafe24-manual-input-one.yml",
            "cafe24-manual-input-preview-one.yml",
            "cafe24-mapping-gaps.yml",
            "cafe24-operational-audit.yml",
            "cafe24-order-poll.yml",
            "cafe24-preflight-one.yml",
            "cafe24-preview-one.yml",
            "supplier-service-sync.yml",
        ]
        for workflow_name in workflow_names:
            with self.subTest(workflow=workflow_name):
                workflow = (APP_ROOT / ".github" / "workflows" / workflow_name).read_text()
                self.assertRegex(workflow, r"actions: (read|write)")
                self.assertIn("id-token: write", workflow)
                self.assertIn("ACTIONS_ID_TOKEN_REQUEST_TOKEN", workflow)
                self.assertIn("audience=instamart-cron", workflow)
                self.assertIn('auth_token="${CRON_SECRET:-${oidc_token:-}}"', workflow)
                self.assertIn(
                    "Repository secret CRON_SECRET or GitHub Actions OIDC token is required for production cron auth.",
                    workflow,
                )

    def test_cafe24_mapping_gaps_workflow_sends_detail_retry_attempts(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-mapping-gaps.yml").read_text()

        self.assertIn("detail_api_max_attempts:", workflow)
        self.assertIn("DETAIL_API_MAX_ATTEMPTS", workflow)
        self.assertIn("detailApiMaxAttempts:$detailApiMaxAttempts", workflow)
        self.assertIn("detail_api_budget_seconds:", workflow)
        self.assertIn("DETAIL_API_BUDGET_SECONDS", workflow)
        self.assertIn("detailApiBudgetSeconds:$detailApiBudgetSeconds", workflow)
        self.assertIn("fail_on_warnings:", workflow)
        self.assertIn("warning_count", workflow)
        self.assertIn("mapping gap detail lookup returned", workflow)

    def test_cafe24_order_poll_workflow_runs_flow_tick_every_five_minutes(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-order-poll.yml").read_text()

        self.assertIn('cron: "26,56 * * * *"', workflow)
        self.assertIn("/api/cron/cafe24/flow-tick", workflow)
        self.assertIn("--argjson lookbackMinutes 180", workflow)
        self.assertIn("--argjson useCursor true", workflow)
        self.assertIn("--argjson overlapMinutes 20", workflow)
        self.assertIn("--argjson pageLimit 200", workflow)
        self.assertIn("--argjson maxPages 3", workflow)
        self.assertIn("--argjson requestTimeoutSeconds 5", workflow)
        self.assertIn("--argjson maxAttempts 1", workflow)
        self.assertIn("live_dispatch:", workflow)
        self.assertIn("chain_runs_remaining:", workflow)
        self.assertIn("MANUAL_LIVE_DISPATCH", workflow)
        self.assertIn("CHAIN_RUNS_REMAINING", workflow)
        self.assertIn('SCHEDULE_CHAIN_RUNS: "72"', workflow)
        self.assertIn('if [ "${GITHUB_EVENT_NAME}" = "schedule" ]; then', workflow)
        self.assertIn("active_dispatch_count", workflow)
        self.assertIn("Active Cafe24 flow dispatch chain already exists", workflow)
        self.assertIn("allow_live_dispatch=true", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("timeout-minutes: 8", workflow)
        self.assertIn("dispatch_limit=50", workflow)
        self.assertIn("completion_limit=50", workflow)
        self.assertIn("dispatch_limit=0", workflow)
        self.assertIn("completion_limit=0", workflow)
        self.assertIn("dispatchLimit: $dispatchLimit", workflow)
        self.assertIn("completionLimit: $completionLimit", workflow)
        self.assertIn("chain_runs_remaining=0", workflow)
        self.assertIn("actions/workflows/cafe24-order-poll.yml/dispatches", workflow)
        self.assertIn("Dispatched next Cafe24 flow tick", workflow)
        self.assertNotIn("/api/cron/automation/tick", workflow)

    def test_cafe24_operational_audit_workflow_uses_summary_cli(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-operational-audit.yml").read_text()

        self.assertIn("actions/checkout@v4", workflow)
        self.assertIn("SMM_PANEL_AUDIT_BEARER_TOKEN", workflow)
        self.assertIn("scripts/cafe24_operational_audit.py", workflow)
        self.assertIn("--source remote", workflow)
        self.assertIn("--format summary", workflow)

    def test_cafe24_manual_input_workflow_reads_target_from_secret(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-manual-input-one.yml").read_text()

        self.assertIn("target_secret_name:", workflow)
        self.assertIn("dispatch_after_save:", workflow)
        self.assertIn("TARGET_VALUE_CAFE24_MANUAL: ${{ secrets.CAFE24_MANUAL_TARGET_VALUE }}", workflow)
        self.assertIn('case "$TARGET_SECRET_NAME" in', workflow)
        self.assertIn("Unsupported target secret", workflow)
        self.assertIn("::add-mask::${TARGET_VALUE}", workflow)
        self.assertIn("dispatchAfterSave:($dispatchAfterSave == \"true\")", workflow)
        self.assertIn(".dispatch.submitted // false", workflow)
        self.assertNotIn("secrets[inputs.target_secret_name]", workflow)
        self.assertNotIn("target_value:", workflow)
        self.assertNotIn("TARGET_VALUE: ${{ inputs.", workflow)

    def test_cafe24_manual_input_preview_workflow_is_dry_run_and_secret_backed(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-manual-input-preview-one.yml").read_text()

        self.assertIn("/api/cron/cafe24/order-items/manual-input/preview", workflow)
        self.assertIn("target_secret_name:", workflow)
        self.assertIn("TARGET_VALUE_CAFE24_MANUAL: ${{ secrets.CAFE24_MANUAL_TARGET_VALUE }}", workflow)
        self.assertIn('case "$TARGET_SECRET_NAME" in', workflow)
        self.assertIn("Unsupported target secret", workflow)
        self.assertIn("::add-mask::${TARGET_VALUE}", workflow)
        self.assertIn("confirmManualInputPreview:true", workflow)
        self.assertIn(".preflight.canDispatch // false", workflow)
        self.assertIn("Manual input preview is not dispatchable", workflow)
        self.assertNotIn("secrets[inputs.target_secret_name]", workflow)
        self.assertNotIn("target_value:", workflow)
        self.assertNotIn("confirmManualInput:true", workflow)

    def test_cafe24_dispatch_workflow_requires_preflight_before_dispatch(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-dispatch-one.yml").read_text()

        self.assertIn("/api/cron/cafe24/order-items/preflight", workflow)
        self.assertIn("Preflight summary", workflow)
        self.assertIn(".canDispatch // false", workflow)
        self.assertIn("refusing to call dispatch-one", workflow)
        self.assertIn("/api/cron/cafe24/order-items/dispatch-one", workflow)

    def test_supplier_admin_list_renders_dispatch_contract_summary(self):
        source = (APP_ROOT / "static" / "admin" / "sections.js").read_text()

        self.assertIn("supplierReadinessContractSummary", source)
        self.assertIn("dispatchContract", source)
        self.assertIn("serviceIdRule", source)
        self.assertIn("발주 계약", source)

    def test_cafe24_audit_environment_renders_runtime_and_db_backend(self):
        source = (APP_ROOT / "static" / "admin" / "cafe24-audit-ui.js").read_text()

        self.assertIn("runtimeModeSource", source)
        self.assertIn("databaseBackend", source)
        self.assertIn("Runtime mode", source)
        self.assertIn("Database backend", source)
        self.assertIn("Cron auth", source)
        self.assertIn("Expected Actions repo", source)
        self.assertIn("github_actions_oidc", source)
        self.assertIn("GitHub Actions OIDC", source)
        self.assertIn("supplierReadinessByIntegration", source)
        self.assertIn("MKT24, FastTraffic, classic별", source)

    def test_cafe24_mapping_panel_runs_and_renders_mapping_gaps(self):
        sections_source = (APP_ROOT / "static" / "admin" / "sections.js").read_text()
        workflow_source = (APP_ROOT / "static" / "admin" / "cafe24-workflow-ui.js").read_text()
        actions_source = (APP_ROOT / "static" / "admin" / "cafe24.js").read_text()

        self.assertIn("data-admin-cafe24-mapping-gaps", sections_source)
        self.assertIn("renderCafe24MappingGapReport", sections_source)
        self.assertIn("renderSupplierDispatchReadinessSnapshot", sections_source)
        self.assertIn("adminCafe24SelectedSupplierServiceId", sections_source)
        self.assertIn("미매핑 진단 결과", workflow_source)
        self.assertIn("data-admin-cafe24-use-product", workflow_source)
        self.assertIn("매핑폼 적용", workflow_source)
        self.assertIn("detailApiBudgetSeconds", workflow_source)
        self.assertIn("/api/admin/cafe24/mapping-gaps", actions_source)
        self.assertIn("detailApiBudgetSeconds: 24", actions_source)
        self.assertIn("data-admin-cafe24-service-select", actions_source)
        self.assertIn("adminCafe24SelectedSupplierServiceId", actions_source)

    def test_cafe24_mapping_readiness_snapshot_mentions_supplier_conditions(self):
        source = (APP_ROOT / "static" / "admin" / "supplier-readiness-ui.js").read_text()

        self.assertIn("renderSupplierDispatchReadinessSnapshot", source)
        self.assertIn("선택 공급사 발주 readiness", source)
        self.assertIn("Service sync", source)
        self.assertIn("Health check", source)
        self.assertIn("MKT24", source)
        self.assertIn("FastTraffic", source)
        self.assertIn("classic SMM", source)

    def test_cafe24_scheduler_notice_mentions_github_oidc(self):
        source = (APP_ROOT / "static" / "admin" / "cafe24-queue-ui.js").read_text()

        self.assertIn("OIDC", source)
        self.assertIn("CRON_SECRET", source)
        self.assertIn("Authorization: Bearer", source)

    def test_cafe24_operational_audit_summary_prints_actionable_state(self):
        from scripts.cafe24_operational_audit import _print_summary

        output = StringIO()
        audit = {
            "fetchedAt": "2026-05-27T00:00:00+09:00",
            "operationalReadiness": {"status": "blocked", "message": "blocked", "checks": []},
            "environment": {"runtimeMode": "production", "runtimeModeSource": "env", "databaseBackend": "postgres"},
            "counts": {
                "cafe24_integrations": 1,
                "cafe24_supplier_mappings": 2,
                "cafe24_order_items": 3,
                "suppliers": 4,
                "supplier_services": 5,
            },
            "cafe24DispatchPolicy": {"status": "manual_mapping_mode", "message": "manual"},
            "cafe24ManualWorkflow": {
                "status": "manual_input_required",
                "nextWorkflow": "Cafe24 Manual Input Preview One",
                "nextAction": "preview first",
                "manualInputCandidates": [
                    {
                        "orderId": "20260527-1",
                        "orderItemCode": "item-1",
                        "nextWorkflow": "Cafe24 Manual Input Preview One",
                        "requiredInputs": ["supplier_id"],
                    }
                ],
                "dispatchCandidates": [],
            },
            "cafe24OrderItems": {
                "summary": {
                    "readyToSubmitCount": 1,
                    "manualInputRequiredCount": 2,
                    "reviewRequiredCount": 3,
                    "supplierOrderLinkedCount": 4,
                    "completedCount": 5,
                    "failedCount": 6,
                }
            },
            "cafe24Mappings": {"enabled": 7, "autoDispatchEnabled": 8},
            "cafe24Integrations": [
                {
                    "mallId": "mall",
                    "shopNo": 1,
                    "isActive": True,
                    "tokenStatus": "connected",
                    "autoSubmit": False,
                    "lastPollAt": "2026-05-27",
                    "lastAutoPollStatus": "success",
                }
            ],
            "supplierReadinessByIntegration": [
                {
                    "label": "MKT24",
                    "status": "blocked",
                    "supplierCount": 1,
                    "readySupplierCount": 0,
                    "blockedSupplierCount": 1,
                    "activeServiceCount": 0,
                    "blockedCodes": ["supplier_services_empty"],
                }
            ],
        }

        with redirect_stdout(output):
            _print_summary(audit)

        text = output.getvalue()
        self.assertIn("runtime: production (env)", text)
        self.assertIn("manualWorkflow: manual_input_required / Cafe24 Manual Input Preview One / preview first", text)
        self.assertIn("orderItemSummary: ready=1, manual=2, review=3, linked=4, completed=5, failed=6", text)
        self.assertIn("mappingSummary: enabled=7, autoDispatchEnabled=8", text)
        self.assertIn("mall#1 active token=connected", text)
        self.assertIn("MKT24: blocked", text)
        self.assertIn("workflowCandidates:", text)

    def test_cafe24_operational_audit_remote_url_normalization(self):
        from scripts.cafe24_operational_audit import _remote_audit_url

        self.assertEqual(
            _remote_audit_url("https://smmproject-lime.vercel.app"),
            "https://smmproject-lime.vercel.app/api/cron/cafe24/operational-audit",
        )
        self.assertEqual(
            _remote_audit_url("https://smmproject-lime.vercel.app/api/cron/cafe24/operational-audit"),
            "https://smmproject-lime.vercel.app/api/cron/cafe24/operational-audit",
        )

    def test_cafe24_operational_audit_remote_fetch_uses_bearer_and_github_headers(self):
        from scripts.cafe24_operational_audit import fetch_remote_audit

        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            return FakeGithubResponse(
                {
                    "ok": True,
                    "fetchedAt": "2026-05-27T00:00:00+09:00",
                    "operationalReadiness": {"status": "ready"},
                }
            )

        env = {
            "SMM_PANEL_AUDIT_BEARER_TOKEN": "remote-token",
            "CRON_SECRET": "",
            "SMM_PANEL_CRON_SECRET": "",
            "GITHUB_REPOSITORY": "jeongwonho/smmproject",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_WORKFLOW": "Cafe24 Operational Audit",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("scripts.cafe24_operational_audit.urlopen", side_effect=fake_urlopen):
                audit = fetch_remote_audit("https://smmproject-lime.vercel.app", timeout_seconds=12.5)

        self.assertEqual(audit["operationalReadiness"]["status"], "ready")
        self.assertEqual(captured["url"], "https://smmproject-lime.vercel.app/api/cron/cafe24/operational-audit")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer remote-token")
        self.assertEqual(captured["headers"]["X-github-repository"], "jeongwonho/smmproject")
        self.assertEqual(captured["headers"]["X-github-run-id"], "12345")
        self.assertEqual(captured["timeout"], 12.5)


class CronAuthorizationTest(unittest.TestCase):
    def test_cron_authorization_requires_bearer_secret(self):
        with patch.dict(os.environ, {"CRON_SECRET": "cron-secret"}, clear=False):
            self.assertTrue(cron_authorization_valid("Bearer cron-secret"))
            self.assertFalse(cron_authorization_valid("Bearer wrong"))
            self.assertFalse(cron_authorization_valid(""))

    def test_cron_authorization_rejects_verified_github_actions_run_by_default(self):
        headers = {
            "Authorization": "Bearer github-token",
            "X-GitHub-Repository": "jeongwonho/smmproject",
            "X-GitHub-Run-Id": "12345",
            "X-GitHub-Workflow": "Cafe24 Order Poll",
        }
        payload = {
            "id": 12345,
            "event": "schedule",
            "repository": {"full_name": "jeongwonho/smmproject"},
        }
        with patch.dict(
            os.environ,
            {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": "", "SMM_PANEL_ALLOW_GITHUB_RUN_CRON_AUTH": ""},
            clear=False,
        ):
            with patch("backend.cron_auth.urllib_request.urlopen", return_value=FakeGithubResponse(payload)) as urlopen:
                self.assertFalse(cron_authorization_valid("Bearer github-token", headers))
                self.assertFalse(urlopen.called)

    def test_cron_authorization_accepts_verified_github_actions_run_when_enabled(self):
        headers = {
            "Authorization": "Bearer github-token",
            "X-GitHub-Repository": "jeongwonho/smmproject",
            "X-GitHub-Run-Id": "12345",
            "X-GitHub-Workflow": "Cafe24 Order Poll",
        }
        payload = {
            "id": 12345,
            "event": "schedule",
            "repository": {"full_name": "jeongwonho/smmproject"},
        }
        with patch.dict(
            os.environ,
            {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": "", "SMM_PANEL_ALLOW_GITHUB_RUN_CRON_AUTH": "1"},
            clear=False,
        ):
            with patch("backend.cron_auth.urllib_request.urlopen", return_value=FakeGithubResponse(payload)) as urlopen:
                self.assertTrue(cron_authorization_valid("Bearer github-token", headers))
                self.assertTrue(urlopen.called)

    def test_cron_authorization_accepts_github_actions_oidc_claims(self):
        headers = {
            "Authorization": "Bearer header.payload.signature",
            "X-GitHub-Repository": "jeongwonho/smmproject",
            "X-GitHub-Run-Id": "12345",
        }
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "instamart-cron",
            "repository": "jeongwonho/smmproject",
            "event_name": "schedule",
            "run_id": "12345",
            "nbf": 1,
            "exp": 9999999999,
        }
        with patch.dict(os.environ, {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": ""}, clear=False):
            with patch("backend.cron_auth.github_actions_oidc_claims", return_value=claims):
                self.assertTrue(cron_authorization_valid("Bearer header.payload.signature", headers))

    def test_cron_authorization_rejects_github_actions_oidc_wrong_audience(self):
        headers = {
            "Authorization": "Bearer header.payload.signature",
            "X-GitHub-Run-Id": "12345",
        }
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "wrong-audience",
            "repository": "jeongwonho/smmproject",
            "event_name": "schedule",
            "run_id": "12345",
            "nbf": 1,
            "exp": 9999999999,
        }
        with patch.dict(os.environ, {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": ""}, clear=False):
            with patch("backend.cron_auth.github_actions_oidc_claims", return_value=claims):
                self.assertFalse(cron_authorization_valid("Bearer header.payload.signature", headers))

    def test_cron_authorization_rejects_wrong_github_repository(self):
        headers = {
            "Authorization": "Bearer github-token",
            "X-GitHub-Repository": "someone/else",
            "X-GitHub-Run-Id": "12345",
        }

        with patch.dict(os.environ, {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": ""}, clear=False):
            self.assertFalse(cron_authorization_valid("Bearer github-token", headers))


class RouterRegistryTest(unittest.TestCase):
    def test_dynamic_public_route_declares_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/charge-orders/charge_123/start-payment")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params["charge_order_id"], "charge_123")
        self.assertEqual(route.auth, "public")
        self.assertTrue(route.csrf)

    def test_dynamic_admin_route_declares_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/admin/suppliers/supplier_123/sync-services")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params["supplier_id"], "supplier_123")
        self.assertEqual(route.auth, "admin")
        self.assertTrue(route.csrf)

    def test_cafe24_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/orders/poll")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_flow_tick_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/flow-tick")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_single_dispatch_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/dispatch-one")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_single_preflight_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/preflight")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_single_preflight_admin_route_requires_admin_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/admin/cafe24/order-items/preflight")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "admin")
        self.assertTrue(route.csrf)

    def test_cafe24_single_preview_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/preview")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_manual_input_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/manual-input")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_manual_input_preview_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/manual-input/preview")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_single_supplier_status_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/order-items/check-supplier-status")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_operational_audit_route_requires_admin_auth(self):
        matched = ROUTER.match("GET", "/api/admin/cafe24/operational-audit")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "admin")
        self.assertFalse(route.csrf)

    def test_cafe24_mapping_gaps_admin_route_requires_admin_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/admin/cafe24/mapping-gaps")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "admin")
        self.assertTrue(route.csrf)

    def test_cafe24_mapping_gaps_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("POST", "/api/cron/cafe24/mapping-gaps")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_cafe24_manual_input_admin_route_declares_admin_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/admin/cafe24/order-items/manual-input")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "admin")
        self.assertTrue(route.csrf)

    def test_cafe24_manual_input_preview_admin_route_declares_admin_auth_and_csrf(self):
        matched = ROUTER.match("POST", "/api/admin/cafe24/order-items/manual-input/preview")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "admin")
        self.assertTrue(route.csrf)

    def test_cafe24_operational_audit_cron_route_declares_cron_auth(self):
        matched = ROUTER.match("GET", "/api/cron/cafe24/operational-audit")

        self.assertIsNotNone(matched)
        route, params = matched
        self.assertEqual(params, {})
        self.assertEqual(route.auth, "cron")
        self.assertFalse(route.csrf)

    def test_unknown_api_route_does_not_match(self):
        self.assertIsNone(ROUTER.match("GET", "/api/does-not-exist"))


if __name__ == "__main__":
    unittest.main()
