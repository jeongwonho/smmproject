import re
import unittest
from unittest.mock import patch

import bootstrap
from backend.wallet import charge_amount_breakdown, normalize_charge_payment_channel
from core import (
    derive_order_idempotency_key,
    generate_public_order_number,
    normalize_order_channel,
    normalize_order_dispatch_status,
    order_channel_label,
    sanitize_external_order_reference,
)


class OrderUtilityTest(unittest.TestCase):
    def test_derive_order_idempotency_key_normalizes_nested_fields(self):
        first = derive_order_idempotency_key(
            " user_1 ",
            " product_1 ",
            {
                "target": {"url": " https://example.com/p/1 ", "meta": [" a ", None]},
                "quantity": 100,
            },
            now_seconds=240,
        )
        second = derive_order_idempotency_key(
            "user_1",
            "product_1",
            {
                "quantity": "100",
                "target": {"meta": ["a", ""], "url": "https://example.com/p/1"},
            },
            now_seconds=241,
        )

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("auto:2:"))
        self.assertLessEqual(len(first), 120)

    def test_generate_public_order_number_uses_expected_format(self):
        with patch("backend.orders.secrets.token_hex", return_value="deadbeef"):
            order_number = generate_public_order_number()

        self.assertRegex(order_number, r"^SMM-\d{8}-DEADBEEF$")

    def test_generate_public_order_number_changes_with_token(self):
        with patch("backend.orders.secrets.token_hex", side_effect=["00000000", "ffffffff"]):
            first = generate_public_order_number()
            second = generate_public_order_number()

        self.assertNotEqual(first, second)
        self.assertTrue(re.match(r"^SMM-\d{8}-00000000$", first))
        self.assertTrue(re.match(r"^SMM-\d{8}-FFFFFFFF$", second))

    def test_sanitize_external_order_reference_strips_control_chars_and_limits_length(self):
        raw = f"  cafe24\x00order\nitem{'x' * 200}  "

        sanitized = sanitize_external_order_reference(raw)

        self.assertTrue(sanitized.startswith("cafe24orderitem"))
        self.assertEqual(len(sanitized), 160)
        self.assertNotRegex(sanitized, r"[\x00-\x1f\x7f]")

    def test_normalize_order_dispatch_status_aliases_supplier_states(self):
        self.assertEqual(normalize_order_dispatch_status("pending"), "ready")
        self.assertEqual(normalize_order_dispatch_status("sent"), "submitted")
        self.assertEqual(normalize_order_dispatch_status("processing"), "in_progress")
        self.assertEqual(normalize_order_dispatch_status("partially-completed"), "partial")
        self.assertEqual(normalize_order_dispatch_status("cancel"), "cancelled")
        self.assertEqual(normalize_order_dispatch_status("unexpected"), "failed")

    def test_normalize_order_channel_aliases_sources(self):
        self.assertEqual(normalize_order_channel(""), "web")
        self.assertEqual(normalize_order_channel("public_web"), "web")
        self.assertEqual(normalize_order_channel("cafe-24"), "cafe24")
        self.assertEqual(normalize_order_channel("external-cafe24"), "cafe24")
        self.assertEqual(normalize_order_channel("admin"), "manual")

        with self.assertRaisesRegex(Exception, "지원하지 않는 주문 유입 경로"):
            normalize_order_channel("partner")

    def test_order_channel_label_uses_display_labels(self):
        self.assertEqual(order_channel_label("web"), "자사몰")
        self.assertEqual(order_channel_label("cafe24"), "카페24")
        self.assertEqual(order_channel_label("manual"), "수동등록")
        self.assertEqual(order_channel_label("partner"), "partner")

    def test_charge_amount_breakdown_includes_vat(self):
        self.assertEqual(
            charge_amount_breakdown(50_000),
            {"amount": 50_000, "vatAmount": 5_000, "totalAmount": 55_000},
        )

    def test_normalize_charge_payment_channel_aliases(self):
        self.assertEqual(normalize_charge_payment_channel("wire"), "bank_transfer")
        self.assertEqual(normalize_charge_payment_channel("card/easy_pay"), "card")
        with self.assertRaises(ValueError):
            normalize_charge_payment_channel("cash")


if __name__ == "__main__":
    unittest.main()
