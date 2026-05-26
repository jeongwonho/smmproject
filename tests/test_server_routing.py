import json
import os
import sys
import unittest
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
    def test_admin_manual_input_preview_does_not_save(self):
        class FakeStore:
            def preview_cafe24_order_item_manual_input(self, payload):
                self.preview_payload = payload
                return {
                    "itemId": "cafe24_item_1",
                    "dryRun": True,
                    "normalizedFields": {"keys": ["orderedCount", "targetValue"], "orderedCount": "50"},
                    "supplierPayload": {"keys": ["link", "quantity", "service"], "service": "svc-1", "hasTarget": True, "hasQuantity": True},
                    "preflight": {"canDispatch": True, "blockingReasons": []},
                }

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        handler = FakeHandler()
        request = RouteRequest(
            path="/api/admin/cafe24/order-items/manual-input/preview",
            parsed=None,
            query={},
            params={},
            payload={"itemId": "cafe24_item_1", "orderedCount": "50"},
        )

        with patch("server.write_json") as write_json_mock:
            AppHandler._post_admin_cafe24_order_items_manual_input_preview(handler, request)

        self.assertEqual(handler.store.preview_payload["itemId"], "cafe24_item_1")
        _, status, body = write_json_mock.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["dryRun"])
        self.assertTrue(body["preflight"]["canDispatch"])

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
                    "itemId": "cafe24_item_1",
                    "dryRun": True,
                    "normalizedFields": {
                        "keys": ["orderedCount", "targetValue"],
                        "orderedCount": "50",
                        "redacted": {"orderedCount": "50", "targetValue": "<redacted>"},
                    },
                    "supplierPayload": {
                        "keys": ["link", "quantity", "service"],
                        "service": "svc-1",
                        "hasTarget": True,
                        "hasQuantity": True,
                        "redacted": {"link": "<redacted>", "quantity": "50", "service": "svc-1"},
                    },
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
        rendered = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("private_account", rendered)
        self.assertTrue(body["dryRun"])
        self.assertTrue(body["preflight"]["canDispatch"])

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
        self.assertFalse(body["dispatchAfterSave"])
        self.assertNotIn("dispatch", body)

    def test_cron_manual_input_can_dispatch_after_successful_preflight(self):
        class FakeStore:
            def save_cafe24_order_item_manual_input(self, payload):
                self.saved_payload = payload
                return {
                    "item": {"id": "cafe24_item_1", "standardStatus": "ready_to_submit"},
                    "normalizedFields": {"orderedCount": "50"},
                    "supplierPayload": {
                        "link": "https://instagram.com/private_account",
                        "quantity": "50",
                        "service": "svc-1",
                    },
                }

            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {"canDispatch": True, "blockingReasons": [], "quantity": {"normalized": 50}}

            def dispatch_cafe24_order_item(self, payload):
                self.dispatch_payload = payload
                return {
                    "id": "cafe24_item_1",
                    "status": "supplier_submitted",
                    "submitted": True,
                    "supplierOrderUuid": "SUP-1001",
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
                "dispatchAfterSave": True,
                "confirmManualInput": True,
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

    def test_cron_manual_input_blocks_dispatch_when_preflight_fails(self):
        class FakeStore:
            def save_cafe24_order_item_manual_input(self, payload):
                self.saved_payload = payload
                return {
                    "item": {"id": "cafe24_item_1", "standardStatus": "ready_to_submit"},
                    "normalizedFields": {"orderedCount": "50"},
                    "supplierPayload": {"quantity": "50", "service": "svc-1"},
                }

            def preflight_single_cafe24_order_item(self, payload):
                self.preflight_payload = payload
                return {"canDispatch": False, "blockingReasons": ["supplier_missing"]}

            def dispatch_cafe24_order_item(self, payload):  # pragma: no cover - should never be called
                raise AssertionError("dispatch should not run when preflight fails")

        class FakeHandler:
            def __init__(self):
                self.store = FakeStore()

            def _server(self):
                return SimpleNamespace(store=self.store)

        request = RouteRequest(
            path="/api/cron/cafe24/order-items/manual-input",
            parsed=None,
            query={},
            params={},
            payload={
                "itemId": "cafe24_item_1",
                "orderedCount": "50",
                "dispatchAfterSave": True,
                "confirmManualInput": True,
            },
        )

        with self.assertRaises(PanelError) as context:
            AppHandler._post_cron_cafe24_order_items_manual_input(FakeHandler(), request)

        self.assertEqual(context.exception.status, 409)
        self.assertIn("preflight", str(context.exception))


class CronAuthorizationTest(unittest.TestCase):
    def test_cron_authorization_requires_bearer_secret(self):
        with patch.dict(os.environ, {"CRON_SECRET": "cron-secret"}, clear=False):
            self.assertTrue(cron_authorization_valid("Bearer cron-secret"))
            self.assertFalse(cron_authorization_valid("Bearer wrong"))
            self.assertFalse(cron_authorization_valid(""))

    def test_cron_authorization_accepts_verified_github_actions_run(self):
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
        with patch.dict(os.environ, {"CRON_SECRET": "", "SMM_PANEL_CRON_SECRET": ""}, clear=False):
            with patch("server.urllib_request.urlopen", return_value=FakeGithubResponse(payload)) as urlopen:
                self.assertTrue(cron_authorization_valid("Bearer github-token", headers))
                self.assertTrue(urlopen.called)

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


class WorkflowConfigurationTest(unittest.TestCase):
    def test_cafe24_mapping_gaps_workflow_sends_detail_retry_attempts(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-mapping-gaps.yml").read_text()

        self.assertIn("detail_api_max_attempts:", workflow)
        self.assertIn("DETAIL_API_MAX_ATTEMPTS", workflow)
        self.assertIn("detailApiMaxAttempts:$detailApiMaxAttempts", workflow)
        self.assertIn("fail_on_warnings:", workflow)
        self.assertIn("warning_count", workflow)
        self.assertIn("mapping gap detail lookup returned", workflow)

    def test_cafe24_manual_input_workflow_reads_target_from_secret(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-manual-input-one.yml").read_text()

        self.assertIn("target_secret_name:", workflow)
        self.assertIn("dispatch_after_save:", workflow)
        self.assertIn("DISPATCH_AFTER_SAVE", workflow)
        self.assertIn("dispatchAfterSave:$dispatchAfterSave", workflow)
        self.assertIn("supplier dispatch did not submit", workflow)
        self.assertIn("TARGET_VALUE_CAFE24_MANUAL: ${{ secrets.CAFE24_MANUAL_TARGET_VALUE }}", workflow)
        self.assertIn('case "$TARGET_SECRET_NAME" in', workflow)
        self.assertIn("Unsupported target secret", workflow)
        self.assertIn("::add-mask::${TARGET_VALUE}", workflow)
        self.assertNotIn("secrets[inputs.target_secret_name]", workflow)
        self.assertNotIn("target_value:", workflow)
        self.assertNotIn("TARGET_VALUE: ${{ inputs.", workflow)

    def test_cafe24_manual_input_preview_workflow_is_dry_run_and_reads_target_from_secret(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-manual-input-preview-one.yml").read_text()

        self.assertIn("target_secret_name:", workflow)
        self.assertIn("TARGET_VALUE_CAFE24_MANUAL: ${{ secrets.CAFE24_MANUAL_TARGET_VALUE }}", workflow)
        self.assertIn('case "$TARGET_SECRET_NAME" in', workflow)
        self.assertIn("Unsupported target secret", workflow)
        self.assertIn("::add-mask::${TARGET_VALUE}", workflow)
        self.assertNotIn("secrets[inputs.target_secret_name]", workflow)
        self.assertIn("/api/cron/cafe24/order-items/manual-input/preview", workflow)
        self.assertIn("confirmManualInputPreview:true", workflow)
        self.assertNotIn("target_value:", workflow)
        self.assertNotIn("TARGET_VALUE: ${{ inputs.", workflow)

    def test_cafe24_dispatch_workflow_requires_preflight_before_dispatch(self):
        workflow = (APP_ROOT / ".github" / "workflows" / "cafe24-dispatch-one.yml").read_text()

        self.assertIn("/api/cron/cafe24/order-items/preflight", workflow)
        self.assertIn("Preflight summary", workflow)
        self.assertIn(".canDispatch // false", workflow)
        self.assertIn("refusing to call dispatch-one", workflow)
        self.assertIn("/api/cron/cafe24/order-items/dispatch-one", workflow)


if __name__ == "__main__":
    unittest.main()
