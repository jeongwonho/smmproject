import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap
from backend.integrations.mkt24_settings import (
    Mkt24SettingsError,
    build_mkt24_order_payload_from_setting,
    default_mkt24_field_config,
    default_mkt24_option_config,
    mkt24_detail_data,
    validate_mkt24_option_config,
)
from core import PanelError, PanelStore, now_iso


MKT24_DETAIL = {
    "data": {
        "productUuid": "01811868-0f05-4000-8000-000000000018",
        "formStructure": {
            "schema": {
                "snsValue": ["STRING_REQUIRED"],
                "orderedCount": ["MIN_MAX"],
            },
            "template": {
                "snsValue": {
                    "variant": "load_input",
                    "templateOptions": {
                        "type": "account",
                        "label": "계정(ID)",
                        "placeholder": "ID 입력",
                    },
                },
                "orderedCount": {
                    "variant": "input",
                    "templateOptions": {
                        "labelProps": {"label": "팔로워 수"},
                        "formProps": {
                            "name": "orderedCount",
                            "unit": "개",
                            "validationVariant": "onlyNumber",
                        },
                    },
                },
            },
        },
        "minAmount": 5,
        "maxAmount": 40000,
        "stepAmount": 5,
        "optionPriceRate": 50,
        "price": 120,
        "productCode": "instagram-follower-premium",
        "productName": "인스타그램 한국인 프리미엄 팔로워",
        "fullName": "인스타그램 한국인 프리미엄 팔로워",
        "productTypeName": "인스타그램 - 팔로워(프리미엄)",
        "menuName": "인스타그램 한국인 프리미엄 팔로워",
        "supportsOrderOptions": True,
        "productKind": "normal",
        "isEtc": False,
    }
}


class Mkt24OrderOptionTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "instamart_mkt24_options_test.db"
        self.store = PanelStore(db_path=self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._seed_mkt24_supplier()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _seed_mkt24_supplier(self):
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO suppliers (
                id, name, api_url, integration_type, api_key, bearer_token,
                is_active, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_mkt24",
                "MKT24",
                "https://api.mkt24.co.kr/v3",
                "mkt24",
                "test-api-key",
                "test-bearer-token",
                1,
                "",
                timestamp,
                timestamp,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO supplier_services (
                id, supplier_id, external_service_id, name, category, type,
                rate, min_amount, max_amount, raw_json, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_service_mkt24",
                "supplier_mkt24",
                "01811868-0f05-4000-8000-000000000018",
                "인스타그램 한국인 프리미엄 팔로워",
                "인스타그램",
                "팔로워",
                120.0,
                5,
                40000,
                "{}",
                timestamp,
            ),
        )
        self.conn.commit()

    def _sync_default_setting(self):
        with patch("core.SupplierApiClient.mkt24_product_detail", return_value=MKT24_DETAIL):
            return self.store.sync_mkt24_product_detail(
                {
                    "supplierId": "supplier_mkt24",
                    "productUuid": "01811868-0f05-4000-8000-000000000018",
                }
            )["setting"]

    def _mapping(self):
        return {
            "supplier_id": "supplier_mkt24",
            "supplier_service_id": "supplier_service_mkt24",
            "supplier_external_service_id": "01811868-0f05-4000-8000-000000000018",
            "integration_type": "mkt24",
            "api_url": "https://api.mkt24.co.kr/v3",
            "api_key": "test-api-key",
            "bearer_token": "test-bearer-token",
        }

    def test_mkt24_setting_helpers_live_in_backend_domain(self):
        detail = mkt24_detail_data(MKT24_DETAIL)
        existing_fields = {
            "orderedCount": {
                "enabled": False,
                "inputMode": "admin_default",
                "defaultValue": "25",
                "min": 10,
                "max": 1000,
                "step": 10,
            }
        }

        field_config = default_mkt24_field_config(detail, existing_fields)
        option_config = default_mkt24_option_config(
            detail,
            {"enabled": True, "defaults": {"followerOption": {"value": {"radio": "none"}}}},
        )

        self.assertEqual(field_config["snsValue"]["label"], "계정(ID)")
        self.assertTrue(field_config["snsValue"]["required"])
        self.assertFalse(field_config["orderedCount"]["enabled"])
        self.assertEqual(field_config["orderedCount"]["inputMode"], "admin_default")
        self.assertEqual(field_config["orderedCount"]["min"], 10)
        self.assertTrue(option_config["supportsOrderOptions"])
        self.assertEqual(option_config["defaults"]["followerOption"]["value"]["radio"], "none")

        payload_field_config = default_mkt24_field_config(
            detail,
            {"orderedCount": {"inputMode": "admin_default", "defaultValue": "25"}},
        )
        payload = build_mkt24_order_payload_from_setting(
            detail,
            payload_field_config,
            option_config,
            {"snsValue": "instamart_official"},
        )

        self.assertEqual(payload["productUuid"], "01811868-0f05-4000-8000-000000000018")
        self.assertEqual(payload["value"]["orderedCount"], 25)
        self.assertEqual(payload["value"]["orderInfo"]["snsValue"], "instamart_official")
        self.assertIn("optionInfo", payload["value"])

        with self.assertRaisesRegex(Mkt24SettingsError, "JSON 객체"):
            validate_mkt24_option_config({"enabled": True, "defaults": ["invalid"]}, supports_order_options=True)

    def test_product_detail_sync_and_setting_save(self):
        setting = self._sync_default_setting()

        self.assertEqual(setting["productUuid"], "01811868-0f05-4000-8000-000000000018")
        self.assertEqual(setting["fieldConfig"]["orderedCount"]["min"], 5)
        self.assertTrue(setting["optionConfig"]["enabled"])

        saved = self.store.save_mkt24_product_setting(
            {
                "supplierId": "supplier_mkt24",
                "supplierServiceId": "supplier_service_mkt24",
                "productUuid": "01811868-0f05-4000-8000-000000000018",
                "isActive": True,
                "fieldConfig": {
                    "snsValue": {"enabled": True, "required": True, "inputMode": "user_input"},
                    "orderedCount": {"enabled": True, "required": True, "inputMode": "user_input", "min": 10, "max": 1000, "step": 10},
                },
                "optionConfig": {
                    "enabled": True,
                    "defaults": {"splitOrderOption": {"value": {"radio": "none", "input": 0, "every": 0}}},
                },
            }
        )["setting"]

        self.assertEqual(saved["fieldConfig"]["orderedCount"]["min"], 10)
        self.assertIn("splitOrderOption", saved["optionConfig"]["defaults"])
        self.assertEqual(saved["payloadPreview"]["productUuid"], "01811868-0f05-4000-8000-000000000018")

    def test_runtime_payload_merge_uses_saved_options(self):
        self._sync_default_setting()
        self.store.save_mkt24_product_setting(
            {
                "supplierId": "supplier_mkt24",
                "supplierServiceId": "supplier_service_mkt24",
                "productUuid": "01811868-0f05-4000-8000-000000000018",
                "fieldConfig": {
                    "snsValue": {"enabled": True, "required": True, "inputMode": "user_input"},
                    "orderedCount": {"enabled": True, "required": True, "inputMode": "user_input", "min": 5, "max": 100, "step": 5},
                },
                "optionConfig": {
                    "enabled": True,
                    "defaults": {"followerOption": {"value": {"radio": "none"}}},
                },
            }
        )

        payload = self.store._build_supplier_order_payload(
            {"name": "인스타 팔로워", "product_code": "ig-followers"},
            {"targetValue": "instamart_official", "orderedCount": "25"},
            self._mapping(),
        )

        self.assertEqual(payload["productUuid"], "01811868-0f05-4000-8000-000000000018")
        self.assertEqual(payload["value"]["orderedCount"], 25)
        self.assertEqual(payload["value"]["orderInfo"]["snsValue"], "instamart_official")
        self.assertEqual(payload["value"]["optionInfo"]["followerOption"]["value"]["radio"], "none")

    def test_mkt24_panel_endpoint_uses_standard_panel_order_payload(self):
        payload = self.store._build_supplier_order_payload(
            {"name": "인스타 팔로워", "product_code": "ig-followers", "platform_slug": "instagram", "price_strategy": "unit"},
            {"targetValue": "instamart_official", "orderedCount": "25"},
            {
                **self._mapping(),
                "api_url": "https://api.mkt24.co.kr/v3/panel",
                "bearer_token": "",
                "supplier_external_service_id": "12",
            },
        )

        self.assertEqual(payload["service"], "12")
        self.assertEqual(payload["quantity"], "25")
        self.assertEqual(payload["link"], "https://www.instagram.com/instamart_official/")
        self.assertNotIn("username", payload)
        self.assertNotIn("productUuid", payload)
        self.assertNotIn("value", payload)

    def test_supports_order_options_false_omits_option_info(self):
        detail = {"data": {**MKT24_DETAIL["data"], "supportsOrderOptions": False}}
        with patch("core.SupplierApiClient.mkt24_product_detail", return_value=detail):
            self.store.sync_mkt24_product_detail(
                {
                    "supplierId": "supplier_mkt24",
                    "productUuid": "01811868-0f05-4000-8000-000000000018",
                }
            )

        payload = self.store._build_supplier_order_payload(
            {"name": "인스타 팔로워", "product_code": "ig-followers"},
            {"targetValue": "instamart_official", "orderedCount": "25"},
            self._mapping(),
        )

        self.assertNotIn("optionInfo", payload["value"])

    def test_ordered_count_min_max_step_validation(self):
        self._sync_default_setting()

        with self.assertRaises(PanelError):
            self.store._build_supplier_order_payload(
                {"name": "인스타 팔로워", "product_code": "ig-followers"},
                {"targetValue": "instamart_official", "orderedCount": "7"},
                self._mapping(),
            )

        with self.assertRaises(PanelError):
            self.store._build_supplier_order_payload(
                {"name": "인스타 팔로워", "product_code": "ig-followers"},
                {"targetValue": "instamart_official", "orderedCount": "40005"},
                self._mapping(),
            )

    def test_invalid_option_info_defaults_rejected(self):
        self._sync_default_setting()

        with self.assertRaises(PanelError):
            self.store.save_mkt24_product_setting(
                {
                    "supplierId": "supplier_mkt24",
                    "supplierServiceId": "supplier_service_mkt24",
                    "productUuid": "01811868-0f05-4000-8000-000000000018",
                    "fieldConfig": {},
                    "optionConfig": {"enabled": True, "defaults": ["invalid"]},
                }
            )


if __name__ == "__main__":
    unittest.main()
