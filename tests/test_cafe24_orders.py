import datetime as dt
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from smm_panel.core import PanelError, PanelStore, now_iso


class FakeCafe24ProductClient:
    def products(self, *, keyword="", product_no="", limit=20, offset=0):
        return {
            "products": [
                {
                    "product_no": "1001",
                    "product_name": "인스타 팔로워",
                    "custom_product_code": "IG-FOLLOWER",
                    "price": "1000.00",
                    "options": [{"option_name": "SNS 링크", "option_values": ["프로필 URL"]}],
                    "variants": [
                        {
                            "variant_code": "P00000AA000A",
                            "custom_product_code": "IG-FOLLOWER-100",
                            "option_value": "100개",
                        }
                    ],
                }
            ]
        }

    def product(self, product_no):
        return {
            "product": {
                "product_no": str(product_no),
                "product_name": "인스타 팔로워",
                "custom_product_code": "IG-FOLLOWER",
            }
        }

    def product_options(self, product_no):
        return {"options": [{"option_name": "수량", "option_values": ["100개", "500개"]}]}

    def product_variants(self, product_no):
        return {
            "variants": [
                {
                    "variant_code": "P00000AA000A",
                    "custom_product_code": "IG-FOLLOWER-100",
                    "option_value": "100개",
                }
            ]
        }


class Cafe24OrderIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(tempfile.gettempdir()) / "instamart_cafe24_orders_test.db"
        self.db_path.unlink(missing_ok=True)
        self.store = PanelStore(db_path=self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._seed_supplier_mapping()
        self.integration = self.store.save_cafe24_integration(
            {
                "mallId": "instamart",
                "shopNo": 1,
                "accessToken": "access-token",
                "refreshToken": "refresh-token",
                "scopes": ["mall.read_order", "mall.write_order", "mall.read_product"],
                "autoSubmit": False,
            }
        )["integration"]
        self.store.save_cafe24_product_mapping(
            {
                "mallId": "instamart",
                "shopNo": 1,
                "cafe24ProductNo": "1001",
                "cafe24VariantCode": "P00000AA000A",
                "supplierId": "supplier_test",
                "supplierServiceId": "supplier_service_test",
                "fieldMapping": {
                    "targetValue": "option:계정",
                    "contactPhone": "receiver.cellphone",
                    "requestMemo": "order.memo",
                },
            }
        )

    def tearDown(self):
        self.conn.close()
        self.db_path.unlink(missing_ok=True)

    def _seed_supplier_mapping(self):
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO suppliers (
                id, name, api_url, integration_type, api_key, bearer_token,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_test",
                "Test Supplier",
                "https://supplier.example/api/v2",
                "classic",
                "api-key",
                "",
                1,
                timestamp,
                timestamp,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO supplier_services (
                id, supplier_id, external_service_id, name, category, type,
                raw_json, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_service_test",
                "supplier_test",
                "svc-1001",
                "Instagram Branding",
                "Instagram",
                "Default",
                "{}",
                timestamp,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO product_supplier_mappings (
                id, product_id, supplier_id, supplier_service_id,
                supplier_external_service_id, is_primary, is_active, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "product_supplier_mapping_test",
                "prd_branding_standard_30",
                "supplier_test",
                "supplier_service_test",
                "svc-1001",
                1,
                1,
                timestamp,
            ),
        )
        self.conn.commit()

    def _order_payload(self):
        return {
            "order_id": "20260426-000001",
            "order_status": "N20",
            "payment_status": "paid",
            "memo": "오전 처리 희망",
            "buyer": {
                "name": "홍길동",
                "email": "buyer@example.com",
                "cellphone": "010-1111-2222",
            },
            "receivers": [
                {
                    "name": "홍길동",
                    "cellphone": "010-3333-4444",
                }
            ],
            "items": [
                {
                    "order_item_code": "20260426-000001-01",
                    "product_no": "1001",
                    "variant_code": "P00000AA000A",
                    "quantity": 1,
                    "options": [{"name": "계정", "value": "instamart_official"}],
                }
            ],
        }

    def _integration_row(self):
        return self.conn.execute("SELECT * FROM cafe24_integrations WHERE mall_id = ?", ("instamart",)).fetchone()

    def _set_integration_token_expiry(self, *, access_delta_seconds=7200, refresh_delta_days=14):
        now = dt.datetime.now().astimezone()
        self.conn.execute(
            """
            UPDATE cafe24_integrations
            SET expires_at = ?, refresh_token_expires_at = ?
            WHERE mall_id = ?
            """,
            (
                (now + dt.timedelta(seconds=access_delta_seconds)).isoformat(timespec="seconds"),
                (now + dt.timedelta(days=refresh_delta_days)).isoformat(timespec="seconds"),
                "instamart",
            ),
        )
        self.conn.commit()

    def test_cafe24_item_normalizes_to_supplier_payload_without_internal_product(self):
        order_payload = self._order_payload()
        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "ready_to_submit")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_status"], "paid")
        self.assertEqual(item["payment_gate_status"], "payment_confirmed")
        self.assertEqual(item["supplier_id"], "supplier_test")
        self.assertEqual(item["supplier_service_id"], "supplier_service_test")
        supplier_payload = json.loads(item["supplier_payload_json"])
        self.assertEqual(supplier_payload["service"], "svc-1001")
        self.assertEqual(supplier_payload["username"], "instamart_official")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM balance_transactions").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wallet_ledger").fetchone()[0], 0)

    def test_ready_cafe24_item_can_be_manually_dispatched_once(self):
        order_payload = self._order_payload()
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]

        with patch("smm_panel.core.SupplierApiClient.order", return_value={"order": "SUP-1001"}) as order_call:
            result = self.store.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": "qa"})
            duplicate = self.store.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": "qa"})

        self.assertEqual(result["status"], "supplier_submitted")
        self.assertEqual(result["supplierOrderUuid"], "SUP-1001")
        self.assertTrue(duplicate["duplicate"])
        order_call.assert_called_once()
        supplier_payload = order_call.call_args.args[0]
        self.assertEqual(supplier_payload["service"], "svc-1001")
        item = self.conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        self.assertEqual(item["standard_status"], "supplier_submitted")
        self.assertEqual(item["supplier_order_uuid"], "SUP-1001")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wallet_ledger").fetchone()[0], 0)

    def test_payment_pending_cafe24_item_cannot_be_dispatched(self):
        order_payload = self._order_payload()
        order_payload["payment_status"] = "unpaid"
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]

        with patch("smm_panel.core.SupplierApiClient.order") as order_call:
            with self.assertRaises(PanelError):
                self.store.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": "qa"})

        order_call.assert_not_called()

    def test_duplicate_cafe24_item_is_idempotent(self):
        order_payload = self._order_payload()
        for _ in range(2):
            self.store._process_cafe24_item(
                self.conn,
                integration=self._integration_row(),
                order_payload=order_payload,
                item_payload=order_payload["items"][0],
                index=0,
                submit_ready=False,
            )
        self.conn.commit()

        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)

    def test_unmapped_cafe24_item_waits_for_operator_input(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["product_no"] = "9999"
        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "waiting_input")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)

    def test_unpaid_cafe24_item_is_blocked_before_mapping_or_dispatch(self):
        order_payload = self._order_payload()
        order_payload["payment_status"] = "unpaid"
        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=True,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "payment_pending")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_gate_status"], "payment_pending")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)

    def test_missing_payment_status_requires_manual_review(self):
        order_payload = self._order_payload()
        order_payload.pop("payment_status", None)
        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=True,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "payment_review_required")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_gate_status"], "payment_review_required")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)

    def test_cafe24_mapping_can_be_saved_without_internal_product(self):
        row = self.conn.execute("SELECT * FROM cafe24_supplier_mappings WHERE mall_id = ?", ("instamart",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["internal_product_id"], "")
        self.assertEqual(row["supplier_id"], "supplier_test")
        self.assertEqual(row["supplier_service_id"], "supplier_service_test")

    def test_cafe24_oauth_start_persists_state(self):
        with patch.dict(
            os.environ,
            {
                "SMM_PANEL_CAFE24_CLIENT_ID": "client-id",
                "SMM_PANEL_CAFE24_CLIENT_SECRET": "client-secret",
            },
            clear=False,
        ):
            result = self.store.create_cafe24_oauth_authorize_url(
                {
                    "mallId": "instamart",
                    "shopNo": 1,
                    "scopes": "mall.read_order mall.write_order mall.read_product",
                    "redirectUri": "https://example.com/api/admin/cafe24/oauth/callback",
                    "_adminActor": "admin",
                }
            )

        parsed = urlparse(result["authorizeUrl"])
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "instamart.cafe24api.com")
        self.assertEqual(query["client_id"][0], "client-id")
        self.assertEqual(query["redirect_uri"][0], "https://example.com/api/admin/cafe24/oauth/callback")
        self.assertIn("mall.read_order", query["scope"][0])
        self.assertTrue(self.conn.execute("SELECT state FROM cafe24_oauth_states WHERE state = ?", (result["state"],)).fetchone())

    def test_cafe24_oauth_callback_exchanges_and_saves_token(self):
        with patch.dict(
            os.environ,
            {
                "SMM_PANEL_CAFE24_CLIENT_ID": "client-id",
                "SMM_PANEL_CAFE24_CLIENT_SECRET": "client-secret",
            },
            clear=False,
        ):
            state_result = self.store.create_cafe24_oauth_authorize_url(
                {
                    "mallId": "oauthmall",
                    "shopNo": 2,
                    "scopes": ["mall.read_order", "mall.write_order"],
                    "redirectUri": "https://example.com/api/admin/cafe24/oauth/callback",
                }
            )
            with patch(
                "smm_panel.core.Cafe24ApiClient.exchange_authorization_code",
                return_value={
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "expires_in": 7200,
                    "refresh_token_expires_in": 1209600,
                    "scope": "mall.read_order,mall.write_order",
                },
            ) as exchange:
                result = self.store.complete_cafe24_oauth_callback({"state": state_result["state"], "code": "auth-code"})

        exchange.assert_called_once_with("oauthmall", "auth-code", "https://example.com/api/admin/cafe24/oauth/callback")
        self.assertEqual(result["integration"]["mallId"], "oauthmall")
        self.assertEqual(result["integration"]["shopNo"], 2)
        self.assertTrue(result["integration"]["hasAccessToken"])
        self.assertTrue(result["integration"]["hasRefreshToken"])
        used_at = self.conn.execute(
            "SELECT used_at FROM cafe24_oauth_states WHERE state = ?",
            (state_result["state"],),
        ).fetchone()["used_at"]
        self.assertTrue(used_at)

    def test_expired_access_token_refreshes_once_and_rotates_refresh_token(self):
        self._set_integration_token_expiry(access_delta_seconds=-30, refresh_delta_days=10)
        with patch(
            "smm_panel.core.Cafe24ApiClient.refresh_access_token",
            return_value={
                "access_token": "rotated-access-token",
                "refresh_token": "rotated-refresh-token",
                "expires_in": 7200,
                "refresh_token_expires_in": 1209600,
                "scope": "mall.read_order,mall.write_order,mall.read_product",
            },
        ) as refresh:
            client = self.store._cafe24_client_for_row(self.conn, self._integration_row())

        refresh.assert_called_once()
        self.assertEqual(client.access_token, "rotated-access-token")
        row = self._integration_row()
        self.assertEqual(row["token_status"], "connected")
        self.assertTrue(row["token_last_refreshed_at"])
        self.assertFalse(row["token_refresh_lock_owner"])
        self.assertFalse(row["reconnect_required_at"])

    def test_expired_refresh_token_blocks_collection_and_requires_reconnect(self):
        self._set_integration_token_expiry(access_delta_seconds=-30, refresh_delta_days=-1)

        with self.assertRaises(PanelError):
            self.store._cafe24_client_for_row(self.conn, self._integration_row())

        row = self._integration_row()
        self.assertEqual(row["token_status"], "reconnect_required")
        self.assertTrue(row["reconnect_required_at"])
        self.assertIn("만료", row["reconnect_reason"])

    def test_cafe24_product_lookup_normalizes_products_before_mapping(self):
        with patch.object(self.store, "_cafe24_client_for_row", return_value=FakeCafe24ProductClient()):
            result = self.store.list_cafe24_products(
                {"integrationId": self.integration["id"], "q": "인스타", "limit": 20, "offset": 0}
            )

        self.assertEqual(result["count"], 1)
        product = result["products"][0]
        self.assertEqual(product["productNo"], "1001")
        self.assertEqual(product["customProductCode"], "IG-FOLLOWER")
        self.assertEqual(product["variants"][0]["variantCode"], "P00000AA000A")

    def test_cafe24_product_detail_includes_options_and_variants_for_mapping(self):
        with patch.object(self.store, "_cafe24_client_for_row", return_value=FakeCafe24ProductClient()):
            result = self.store.get_cafe24_product_detail(
                {"integrationId": self.integration["id"], "productNo": "1001"}
            )

        product = result["product"]
        self.assertEqual(product["productNo"], "1001")
        self.assertEqual(product["options"][0]["name"], "수량")
        self.assertEqual(product["variants"][0]["customProductCode"], "IG-FOLLOWER-100")


if __name__ == "__main__":
    unittest.main()
