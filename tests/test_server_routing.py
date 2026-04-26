import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from server import AppHandler


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


if __name__ == "__main__":
    unittest.main()
