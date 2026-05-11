import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from server import AppHandler, ROUTER, cron_authorization_valid
from core import derive_order_idempotency_key


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


class CronAuthorizationTest(unittest.TestCase):
    def test_cron_authorization_requires_bearer_secret(self):
        with patch.dict(os.environ, {"CRON_SECRET": "cron-secret"}, clear=False):
            self.assertTrue(cron_authorization_valid("Bearer cron-secret"))
            self.assertFalse(cron_authorization_valid("Bearer wrong"))
            self.assertFalse(cron_authorization_valid(""))


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

    def test_unknown_api_route_does_not_match(self):
        self.assertIsNone(ROUTER.match("GET", "/api/does-not-exist"))


if __name__ == "__main__":
    unittest.main()
