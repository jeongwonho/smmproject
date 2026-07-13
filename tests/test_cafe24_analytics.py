import threading
import unittest
from unittest.mock import patch

from backend.cafe24_analytics import get_cafe24_ga4_analytics


class Cafe24AnalyticsTest(unittest.TestCase):
    def test_missing_configuration_returns_empty_unavailable_payload(self):
        with patch(
            "backend.cafe24_analytics._analytics_config",
            return_value={"propertyId": "", "clientEmail": "", "privateKey": ""},
        ):
            payload = get_cafe24_ga4_analytics("30d")

        self.assertEqual(payload["source"], "unavailable")
        self.assertFalse(payload["connected"])
        self.assertEqual(payload["overview"]["sessions"], 0)
        self.assertEqual(payload["overview"]["revenue"], 0)
        self.assertEqual(payload["channels"], [])
        self.assertEqual(payload["trend"], [])

    def test_ga4_reports_are_requested_in_parallel(self):
        barrier = threading.Barrier(6)
        calls = []

        def fake_report(**kwargs):
            calls.append(kwargs)
            barrier.wait(timeout=2)
            return {"rows": []}

        with patch(
            "backend.cafe24_analytics._analytics_config",
            return_value={"propertyId": "123", "clientEmail": "analytics@example.com", "privateKey": "key"},
        ), patch("backend.cafe24_analytics._access_token", return_value="token"), patch(
            "backend.cafe24_analytics._run_report",
            side_effect=fake_report,
        ):
            payload = get_cafe24_ga4_analytics("7d")

        self.assertEqual(len(calls), 6)
        self.assertTrue(payload["connected"])
        self.assertEqual(payload["source"], "ga4")

    def test_ga4_failure_never_falls_back_to_invented_metrics(self):
        with patch(
            "backend.cafe24_analytics._analytics_config",
            return_value={"propertyId": "123", "clientEmail": "analytics@example.com", "privateKey": "key"},
        ), patch("backend.cafe24_analytics._access_token", side_effect=RuntimeError("token unavailable")):
            payload = get_cafe24_ga4_analytics("14d")

        self.assertEqual(payload["source"], "unavailable")
        self.assertEqual(payload["overview"]["purchaseCount"], 0)
        self.assertEqual(payload["recommendations"], [])
        self.assertIn("token unavailable", payload["error"])


if __name__ == "__main__":
    unittest.main()
