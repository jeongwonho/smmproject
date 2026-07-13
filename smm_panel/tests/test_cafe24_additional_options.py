import unittest

import bootstrap
from backend.integrations.cafe24 import cafe24_option_entries, cafe24_option_pairs


class Cafe24AdditionalOptionParsingTest(unittest.TestCase):
    def test_nested_additional_option_extracts_instagram_account(self):
        item_payload = {
            "additional_option_values": [
                {
                    "key": "item_option_add",
                    "type": "text",
                    "name": "additional_options",
                    "value": "인스타그램 아이디=instamart_test",
                }
            ]
        }

        entries = cafe24_option_entries({}, item_payload)
        pairs = cafe24_option_pairs({}, item_payload)

        self.assertIn(
            {
                "label": "인스타그램 아이디",
                "value": "instamart_test",
                "source": "item.additional_option_values",
            },
            entries,
        )
        self.assertEqual(pairs["인스타그램 아이디"], "instamart_test")

    def test_singular_additional_option_preserves_instagram_url(self):
        profile_url = "https://www.instagram.com/instamart_test/?hl=ko"
        item_payload = {
            "additional_option_value": f"인스타그램 프로필 URL={profile_url}",
        }

        pairs = cafe24_option_pairs({}, item_payload)

        self.assertEqual(pairs["인스타그램 프로필 URL"], profile_url)
        self.assertNotIn("https", pairs)

    def test_existing_slash_delimited_option_format_still_parses(self):
        item_payload = {
            "option_value": "계정: instamart_test / 팔로워 수 / 250명 (+35,500원)",
        }

        entries = cafe24_option_entries({}, item_payload)

        self.assertIn(
            {"label": "계정", "value": "instamart_test", "source": "item.option_value"},
            entries,
        )


if __name__ == "__main__":
    unittest.main()
