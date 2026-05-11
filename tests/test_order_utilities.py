import re
import unittest
from unittest.mock import patch

import bootstrap
from core import derive_order_idempotency_key, generate_public_order_number


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
        with patch("core.secrets.token_hex", return_value="deadbeef"):
            order_number = generate_public_order_number()

        self.assertRegex(order_number, r"^SMM-\d{8}-DEADBEEF$")

    def test_generate_public_order_number_changes_with_token(self):
        with patch("core.secrets.token_hex", side_effect=["00000000", "ffffffff"]):
            first = generate_public_order_number()
            second = generate_public_order_number()

        self.assertNotEqual(first, second)
        self.assertTrue(re.match(r"^SMM-\d{8}-00000000$", first))
        self.assertTrue(re.match(r"^SMM-\d{8}-FFFFFFFF$", second))


if __name__ == "__main__":
    unittest.main()
