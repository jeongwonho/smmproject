import datetime as dt
import unittest

import bootstrap
from backend.integrations.cafe24 import (
    cafe24_normalize_datetime_text,
    cafe24_payment_gate_status,
    cafe24_payment_snapshot_from_payload,
    cafe24_payment_status_with_source,
    cafe24_refresh_error_requires_reconnect,
    cafe24_refresh_token_expired,
    normalize_cafe24_payment_status,
    normalize_cafe24_scopes,
    normalize_cafe24_shop_no,
    normalize_cafe24_status,
)


class Cafe24IntegrationHelperTest(unittest.TestCase):
    def test_normalizes_shop_scopes_and_statuses(self):
        self.assertEqual(normalize_cafe24_shop_no("0"), 1)
        self.assertEqual(normalize_cafe24_shop_no("2"), 2)
        self.assertEqual(normalize_cafe24_scopes("mall.read_order mall.write_order,mall.read_order"), ["mall.read_order", "mall.write_order"])
        self.assertEqual(normalize_cafe24_status("N20"), "validated")
        self.assertEqual(normalize_cafe24_status("C10"), "cancelled")
        self.assertEqual(normalize_cafe24_payment_status("P"), "paid")
        self.assertEqual(normalize_cafe24_payment_status(False), "unpaid")

    def test_payment_snapshot_and_gate_status(self):
        order_payload = {
            "order_status": "N20",
            "payment": {
                "payment_method_name": "card",
                "paid_amount": "12,300",
                "paid_at": "2026-05-22T01:02:03+09:00",
                "transaction_id": "tid-1",
            },
        }
        item_payload = {"payment_status": "complete"}

        self.assertEqual(cafe24_payment_status_with_source(order_payload, item_payload, "N20"), ("paid", "payload"))
        self.assertEqual(cafe24_payment_gate_status("N20", "paid"), "payment_confirmed")
        self.assertEqual(cafe24_payment_gate_status("N00", "unpaid"), "payment_pending")
        self.assertEqual(cafe24_payment_gate_status("C10", "paid"), "cancelled")
        self.assertEqual(
            cafe24_payment_snapshot_from_payload(order_payload, item_payload),
            {
                "method": "card",
                "amount": 12300,
                "paidAt": "2026-05-22T01:02:03+09:00",
                "reference": "tid-1",
            },
        )
        self.assertEqual(cafe24_normalize_datetime_text("2026-05-22 01:02:03"), "2026-05-22 01:02:03")

    def test_refresh_token_reconnect_helpers(self):
        expired_at = (dt.datetime.now().astimezone() - dt.timedelta(minutes=1)).isoformat()
        self.assertTrue(cafe24_refresh_token_expired(expired_at))
        self.assertTrue(cafe24_refresh_error_requires_reconnect("invalid_grant: expired refresh token"))
        self.assertFalse(cafe24_refresh_error_requires_reconnect("temporary upstream timeout"))


if __name__ == "__main__":
    unittest.main()
