import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from server import AppHandler
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


if __name__ == "__main__":
    unittest.main()
