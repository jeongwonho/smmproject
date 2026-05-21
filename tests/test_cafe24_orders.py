import datetime as dt
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import bootstrap
from core import Cafe24ApiError, PanelError, PanelStore, SupplierApiError, now_iso


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


class FakeCafe24VariantQuantityClient(FakeCafe24ProductClient):
    def product_variants(self, product_no):
        return {
            "variants": [
                {
                    "variant_code": "P00000AA000A",
                    "custom_product_code": "IG-FOLLOWER-50",
                    "option_value": "팔로워 수: 50명",
                }
            ]
        }


class FailingCafe24ProductClient:
    def products(self, *, keyword="", product_no="", limit=20, offset=0):
        raise Cafe24ApiError("Cafe24 API 오류 403: scope permission denied")


class FakeCafe24OrderClient:
    def __init__(self, order_payload):
        self.order_payload = order_payload
        self.order_pages = None
        self.orders_calls = []
        self.order_calls = []
        self.confirm_purchase_calls = []

    def orders(
        self,
        *,
        start_date,
        end_date,
        statuses=None,
        payment_statuses=None,
        order_id="",
        limit=100,
        offset=0,
        date_type="order_date",
    ):
        self.orders_calls.append(
            {
                "start_date": start_date,
                "end_date": end_date,
                "statuses": statuses,
                "payment_statuses": payment_statuses,
                "order_id": order_id,
                "limit": limit,
                "offset": offset,
                "date_type": date_type,
            }
        )
        if self.order_pages is not None:
            typed_key = (date_type, offset)
            if typed_key in self.order_pages:
                return {"orders": self.order_pages.get(typed_key, [])}
            return {"orders": self.order_pages.get(offset, [])}
        return {"orders": [self.order_payload]}

    def order(self, order_id):
        self.order_calls.append(order_id)
        return {"order": self.order_payload}

    def confirm_purchase(self, order_id, order_item_code, *, collect_points="F"):
        self.confirm_purchase_calls.append(
            {"order_id": order_id, "order_item_code": order_item_code, "collect_points": collect_points}
        )
        return {"order": {"order_id": order_id, "order_item_code": order_item_code, "purchase_confirmation": "T"}}


class Cafe24OrderIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "instamart_cafe24_orders_test.db"
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
        self.tmpdir.cleanup()

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
            "payment": {
                "payment_method": "card",
                "paid_amount": "15000",
                "payment_date": "2026-04-27T10:11:00+09:00",
                "pg_tid": "TID-123",
            },
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

    def _enable_auto_submit_and_supplier_ready(self):
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE cafe24_integrations
            SET auto_submit = 1
            WHERE id = ?
            """,
            (self.integration["id"],),
        )
        self.conn.execute(
            """
            UPDATE suppliers
            SET health_status = 'ok', health_message = 'ok', health_checked_at = ?,
                balance_status = 'ok', balance_checked_at = ?,
                service_sync_status = 'success', service_sync_completed_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, timestamp, "supplier_test"),
        )
        self.conn.commit()

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
        self.assertEqual(item["payment_method"], "card")
        self.assertEqual(item["payment_amount"], 15000)
        self.assertEqual(item["payment_paid_at"], "2026-04-27T10:11:00+09:00")
        self.assertEqual(item["payment_reference"], "TID-123")
        self.assertEqual(item["supplier_id"], "supplier_test")
        self.assertEqual(item["supplier_service_id"], "supplier_service_test")
        supplier_payload = json.loads(item["supplier_payload_json"])
        self.assertEqual(supplier_payload["service"], "svc-1001")
        self.assertEqual(supplier_payload["username"], "instamart_official")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM balance_transactions").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wallet_ledger").fetchone()[0], 0)

    def test_cafe24_quantity_option_text_extracts_ordered_count(self):
        samples = {
            "50명": 50,
            "250명 (+35,500원)": 250,
            "1,000명": 1000,
            "10000명(10k) (+1,641,000원)": 10000,
            "10k": 10000,
        }
        for text, expected in samples.items():
            candidates = self.store._cafe24_quantity_candidates_from_text(text, label="팔로워 수")
            self.assertEqual(candidates[0]["value"], expected)

    def test_cafe24_quantity_option_split_text_extracts_ordered_count(self):
        item_payload = {
            "option_value": "계정: instamart_official / 팔로워 수 / 250명 (+35,500원)",
        }
        entries = self.store._cafe24_option_entries({}, item_payload)
        candidates = self.store._cafe24_quantity_candidates_from_options(entries, label="팔로워 수")
        self.assertEqual(candidates[0]["value"], 250)

    def test_cafe24_ordered_count_auto_detects_unique_option_without_mapping(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "250명 (+35,500원)"},
        ]

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
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        normalized_fields = json.loads(item["normalized_fields_json"])
        supplier_payload = json.loads(item["supplier_payload_json"])
        self.assertEqual(normalized_fields["orderedCount"], "250")
        self.assertEqual(supplier_payload["quantity"], "250")

    def test_cafe24_variant_option_lookup_supplies_ordered_count_when_item_quantity_is_one(self):
        self.conn.execute(
            "UPDATE supplier_services SET min_amount = 5 WHERE id = ?",
            ("supplier_service_test",),
        )
        self.conn.commit()
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [{"name": "계정", "value": "instamart_official"}]

        with patch.object(self.store, "_cafe24_client_for_row", return_value=FakeCafe24VariantQuantityClient()):
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
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        normalized_fields = json.loads(item["normalized_fields_json"])
        supplier_payload = json.loads(item["supplier_payload_json"])
        raw_payload = json.loads(item["raw_payload_json"])
        self.assertEqual(normalized_fields["orderedCount"], "50")
        self.assertEqual(supplier_payload["quantity"], "50")
        self.assertEqual(raw_payload["variantOptionEntries"][0]["value"], "50명")

    def test_cafe24_ambiguous_option_quantity_without_mapping_requires_review(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "250명 (+35,500원)"},
            {"name": "1일 유입수량", "value": "50명"},
        ]

        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "needs_manual_review")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertIn("수량 후보", item["error_message"])
        self.assertFalse(json.loads(item["supplier_payload_json"]))

    def test_cafe24_ordered_count_can_be_extracted_from_selected_option(self):
        self.conn.execute(
            """
            UPDATE cafe24_supplier_mappings
            SET field_mapping_json = ?
            WHERE mall_id = ?
            """,
            (
                json.dumps(
                    {
                        "targetValue": "option:계정",
                        "orderedCount": {
                            "source": "option",
                            "label": "팔로워 수",
                            "extract": "quantity_number",
                            "fallback": "item.quantity",
                            "ambiguityPolicy": "needs_manual_review",
                        },
                    }
                ),
                "instamart",
            ),
        )
        self.conn.commit()
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "250명 (+35,500원)"},
        ]

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
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        normalized_fields = json.loads(item["normalized_fields_json"])
        supplier_payload = json.loads(item["supplier_payload_json"])
        self.assertEqual(normalized_fields["orderedCount"], "250")
        self.assertEqual(supplier_payload["quantity"], "250")

    def test_cafe24_duplicate_quantity_options_require_manual_review(self):
        self.conn.execute(
            """
            UPDATE cafe24_supplier_mappings
            SET field_mapping_json = ?
            WHERE mall_id = ?
            """,
            (
                json.dumps(
                    {
                        "targetValue": "option:계정",
                        "orderedCount": {
                            "source": "option",
                            "label": "팔로워 수",
                            "extract": "quantity_number",
                            "fallback": "item.quantity",
                            "ambiguityPolicy": "needs_manual_review",
                        },
                    }
                ),
                "instamart",
            ),
        )
        self.conn.commit()
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "250명 (+35,500원)"},
            {"name": "팔로워 수", "value": "500명 (+79,000원)"},
        ]

        result = self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.commit()

        self.assertEqual(result["status"], "needs_manual_review")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertIn("수량 후보", item["error_message"])
        self.assertFalse(json.loads(item["supplier_payload_json"]))

    def test_cafe24_mapping_preview_uses_sample_order_without_dispatch(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "500명 (+79,000원)"},
        ]
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

        preview = self.store.preview_cafe24_mapping(
            {
                "sampleOrderItemId": item_id,
                "supplierId": "supplier_test",
                "supplierServiceId": "supplier_service_test",
                "fieldMappingJson": json.dumps(
                    {
                        "targetValue": "option:계정",
                        "orderedCount": {
                            "source": "option",
                            "label": "팔로워 수",
                            "extract": "quantity_number",
                            "fallback": "item.quantity",
                            "ambiguityPolicy": "needs_manual_review",
                        },
                    }
                ),
            }
        )

        self.assertTrue(preview["ok"])
        self.assertEqual(preview["normalizedFields"]["orderedCount"], "500")
        self.assertEqual(preview["supplierPayload"]["quantity"], "500")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM supplier_orders").fetchone()[0], 0)

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

        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-1001"}) as order_call:
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

    def test_instagram_panel_payload_converts_bare_dotted_account_to_profile_url(self):
        payload = self.store._build_supplier_order_payload(
            {"product_code": "instagram-follower", "platform_slug": "instagram", "price_strategy": "unit"},
            {"targetValue": "parkk.co.kr", "orderedCount": "50"},
            {
                "supplier_external_service_id": "40000",
                "integration_type": "mkt24",
                "api_url": "https://api.mkt24.co.kr/v3/panel",
            },
        )

        self.assertEqual(payload["link"], "https://www.instagram.com/parkk.co.kr/")
        self.assertEqual(payload["quantity"], "50")

    def test_single_cafe24_supplier_status_check_updates_item(self):
        order_payload = self._order_payload()
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]
        self.conn.execute(
            """
            UPDATE cafe24_order_items
            SET standard_status = 'supplier_submitted',
                supplier_order_uuid = 'SUP-STATUS-1001'
            WHERE id = ?
            """,
            (item_id,),
        )
        self.conn.commit()

        with patch("core.SupplierApiClient.status", return_value={"status": "Completed"}) as status_call:
            result = self.store.check_single_cafe24_supplier_status(
                {
                    "mallId": "instamart",
                    "shopNo": 1,
                    "orderId": "20260426-000001",
                    "orderItemCode": "20260426-000001-01",
                    "_adminActor": "cron",
                }
            )

        status_call.assert_called_once_with("SUP-STATUS-1001")
        self.assertEqual(result["supplierStatus"], "completed")
        self.assertEqual(result["cafe24Status"], "completed")
        item = self.conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        self.assertEqual(item["standard_status"], "completed")
        self.assertEqual(item["cafe24_completion_status"], "pending")

    def test_single_cafe24_dispatch_allows_cancelled_supplier_redispatch(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "parkk.co.kr"},
            {"name": "팔로워 수", "value": "50명"},
        ]
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]
        self.conn.execute(
            """
            UPDATE cafe24_order_items
            SET standard_status = 'failed',
                supplier_order_uuid = 'SUP-CANCELED',
                supplier_response_json = ?,
                error_message = 'bad_request_on_url'
            WHERE id = ?
            """,
            (json.dumps({"lastStatusCheck": {"payload": {"status": "Canceled"}}}), item_id),
        )
        self.conn.commit()

        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-REDISPATCH"}) as order_call:
            result = self.store.dispatch_single_cafe24_order_item(
                {
                    "itemId": item_id,
                    "expectedQuantity": 50,
                    "allowCanceledSupplierRedispatch": True,
                    "_adminActor": "cron",
                }
            )

        self.assertEqual(result["dispatch"]["status"], "supplier_submitted")
        self.assertEqual(result["dispatch"]["supplierOrderUuid"], "SUP-REDISPATCH")
        supplier_payload = order_call.call_args.args[0]
        self.assertEqual(supplier_payload["link"], "https://www.instagram.com/parkk.co.kr/")
        item = self.conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        self.assertEqual(item["supplier_order_uuid"], "SUP-REDISPATCH")

    def test_single_cafe24_dispatch_revalidates_quantity_before_supplier_order(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "50명"},
        ]
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]
        self.conn.execute(
            """
            UPDATE cafe24_order_items
            SET standard_status = 'supplier_range_error',
                supplier_payload_json = '{}',
                error_message = '공급사 최소 수량(5)보다 작습니다.'
            WHERE id = ?
            """,
            (item_id,),
        )
        self.conn.commit()

        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-50"}) as order_call:
            result = self.store.dispatch_single_cafe24_order_item(
                {
                    "mallId": "instamart",
                    "shopNo": 1,
                    "orderId": "20260426-000001",
                    "orderItemCode": "20260426-000001-01",
                    "expectedQuantity": 50,
                    "_adminActor": "cron",
                }
            )

        self.assertEqual(result["normalizedQuantity"], 50)
        self.assertEqual(result["dispatch"]["status"], "supplier_submitted")
        supplier_payload = order_call.call_args.args[0]
        self.assertEqual(supplier_payload["quantity"], "50")

    def test_single_cafe24_dispatch_blocks_expected_quantity_mismatch(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [
            {"name": "계정", "value": "instamart_official"},
            {"name": "팔로워 수", "value": "250명"},
        ]
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]

        with patch("core.SupplierApiClient.order") as order_call:
            with self.assertRaises(PanelError):
                self.store.dispatch_single_cafe24_order_item(
                    {"itemId": item_id, "expectedQuantity": 50, "_adminActor": "cron"}
                )

        order_call.assert_not_called()

    def test_single_cafe24_dispatch_can_persist_fixed_quantity_for_variant_mapping(self):
        order_payload = self._order_payload()
        order_payload["items"][0]["options"] = [{"name": "계정", "value": "instamart_official"}]
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]
        self.conn.execute(
            "UPDATE supplier_services SET min_amount = 5 WHERE id = ?",
            ("supplier_service_test",),
        )
        self.conn.execute(
            """
            UPDATE cafe24_order_items
            SET standard_status = 'supplier_range_error',
                supplier_payload_json = '{}',
                error_message = '공급사 최소 수량(5)보다 작습니다.'
            WHERE id = ?
            """,
            (item_id,),
        )
        self.conn.commit()

        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-FIXED-50"}) as order_call:
            result = self.store.dispatch_single_cafe24_order_item(
                {
                    "itemId": item_id,
                    "expectedQuantity": 50,
                    "allowExpectedQuantityMappingUpdate": True,
                    "_adminActor": "cron",
                }
            )

        self.assertTrue(result["mappingUpdated"])
        self.assertEqual(result["normalizedQuantity"], 50)
        supplier_payload = order_call.call_args.args[0]
        self.assertEqual(supplier_payload["quantity"], "50")
        mapping = self.conn.execute("SELECT field_mapping_json FROM cafe24_supplier_mappings").fetchone()
        self.assertEqual(json.loads(mapping["field_mapping_json"])["orderedCount"]["value"], "50")

    def test_mkt24_token_expired_dispatch_requires_manual_token_refresh(self):
        order_payload = self._order_payload()
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE suppliers
            SET integration_type = 'mkt24',
                api_url = 'https://api.mkt24.co.kr/v3',
                bearer_token = 'expired-token',
                health_status = 'ok',
                health_message = 'ok',
                health_checked_at = ?,
                service_sync_status = 'success',
                service_sync_completed_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, "supplier_test"),
        )
        self.conn.commit()
        item_id = self.conn.execute("SELECT id FROM cafe24_order_items").fetchone()["id"]

        with patch(
            "core.SupplierApiClient.order",
            side_effect=SupplierApiError(
                "HTTP 401: 공급사 Bearer Token이 만료되었습니다. 관리자 공급사 설정에서 새 Bearer Token을 저장해 주세요. code=token_expired"
            ),
        ) as order_call:
            result = self.store.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": "qa"})

        order_call.assert_called_once()
        self.assertEqual(result["status"], "needs_manual_review")
        self.assertFalse(result["submitted"])
        item = self.conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        self.assertEqual(item["standard_status"], "needs_manual_review")
        self.assertEqual(item["automation_error_code"], "supplier_token_expired")
        self.assertEqual(item["next_retry_at"], "")
        self.assertIn("Bearer Token", item["error_message"])
        supplier = self.conn.execute("SELECT * FROM suppliers WHERE id = ?", ("supplier_test",)).fetchone()
        self.assertEqual(supplier["health_status"], "failed")
        self.assertIn("Bearer Token", supplier["health_message"])

    def test_automation_dispatches_ready_cafe24_item_once(self):
        self._enable_auto_submit_and_supplier_ready()
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

        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-AUTO"}) as order_call:
            first = self.store.dispatch_due_cafe24_order_items(actor="cron", limit=10)
            second = self.store.dispatch_due_cafe24_order_items(actor="cron", limit=10)

        self.assertEqual(first["submitted"], 1)
        self.assertEqual(second["checked"], 0)
        order_call.assert_called_once()
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["standard_status"], "supplier_submitted")
        self.assertEqual(item["supplier_order_uuid"], "SUP-AUTO")

    def test_automation_blocks_cafe24_dispatch_when_supplier_health_failed(self):
        self._enable_auto_submit_and_supplier_ready()
        self.conn.execute(
            "UPDATE suppliers SET health_status = 'failed', health_message = 'balance unavailable' WHERE id = ?",
            ("supplier_test",),
        )
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

        with patch("core.SupplierApiClient.order") as order_call:
            result = self.store.dispatch_due_cafe24_order_items(actor="cron", limit=10)

        self.assertEqual(result["blocked"], 1)
        order_call.assert_not_called()
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["automation_error_code"], "supplier_health_not_ok")
        self.assertTrue(item["next_retry_at"])

    def test_automation_blocks_mkt24_panel_dispatch_when_mapping_uses_legacy_uuid(self):
        self._enable_auto_submit_and_supplier_ready()
        legacy_uuid = "01811868-0f05-4000-8000-000000000018"
        self.conn.execute(
            """
            UPDATE suppliers
            SET integration_type = 'mkt24', api_url = 'https://api.mkt24.co.kr/v3/panel'
            WHERE id = ?
            """,
            ("supplier_test",),
        )
        self.conn.execute(
            """
            UPDATE supplier_services
            SET external_service_id = ?
            WHERE id = ?
            """,
            (legacy_uuid, "supplier_service_test"),
        )
        self.conn.execute(
            """
            UPDATE cafe24_supplier_mappings
            SET supplier_external_service_id = ?
            WHERE supplier_id = ?
            """,
            (legacy_uuid, "supplier_test"),
        )
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

        with patch("core.SupplierApiClient.order") as order_call:
            result = self.store.dispatch_due_cafe24_order_items(actor="cron", limit=10)

        self.assertEqual(result["blocked"], 1)
        order_call.assert_not_called()
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["standard_status"], "needs_manual_review")
        self.assertEqual(item["automation_error_code"], "mkt24_panel_service_id_invalid")
        self.assertEqual(item["next_retry_at"], "")

    def test_supplier_completed_status_marks_cafe24_item_ready_for_completion(self):
        self._enable_auto_submit_and_supplier_ready()
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
        with patch("core.SupplierApiClient.order", return_value={"order": "SUP-COMPLETE"}):
            self.store.dispatch_cafe24_order_item({"itemId": item_id, "_adminActor": "qa"})
        old_check = (dt.datetime.now().astimezone() - dt.timedelta(minutes=20)).isoformat(timespec="seconds")
        self.conn.execute(
            "UPDATE cafe24_order_items SET automation_last_checked_at = ? WHERE id = ?",
            (old_check, item_id),
        )
        self.conn.commit()

        with patch("core.SupplierApiClient.status", return_value={"status": "completed"}):
            result = self.store.refresh_due_supplier_order_statuses(actor="cron", limit=10)

        self.assertEqual(result["completed"], 1)
        item = self.conn.execute("SELECT * FROM cafe24_order_items WHERE id = ?", (item_id,)).fetchone()
        self.assertEqual(item["standard_status"], "completed")
        self.assertEqual(item["cafe24_completion_status"], "pending")

    def test_cafe24_completion_confirms_purchase_once_supplier_completed(self):
        self._enable_auto_submit_and_supplier_ready()
        order_payload = self._order_payload()
        self.store._process_cafe24_item(
            self.conn,
            integration=self._integration_row(),
            order_payload=order_payload,
            item_payload=order_payload["items"][0],
            index=0,
            submit_ready=False,
        )
        self.conn.execute(
            """
            UPDATE cafe24_order_items
            SET standard_status = 'completed', cafe24_completion_status = 'pending'
            """
        )
        self.conn.commit()
        fake_client = FakeCafe24OrderClient(order_payload)

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.complete_due_cafe24_order_items(actor="cron", limit=10)

        self.assertEqual(result["done"], 1)
        self.assertEqual(fake_client.confirm_purchase_calls[0]["order_id"], "20260426-000001")
        self.assertEqual(fake_client.confirm_purchase_calls[0]["order_item_code"], "20260426-000001-01")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["cafe24_completion_status"], "done")
        self.assertTrue(item["cafe24_completed_at"])

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

        with patch("core.SupplierApiClient.order") as order_call:
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

    def test_missing_payment_status_uses_order_status_payment_confirmation(self):
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

        self.assertEqual(result["status"], "ready_to_submit")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_status"], "paid")
        self.assertEqual(item["payment_status_source"], "order_status")
        self.assertEqual(item["payment_gate_status"], "payment_confirmed")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orders WHERE order_channel = 'cafe24'").fetchone()[0], 0)

    def test_n50_order_is_collected_and_marked_payment_confirmed(self):
        order_payload = self._order_payload()
        order_payload["order_status"] = "N50"
        order_payload.pop("payment_status", None)
        fake_client = FakeCafe24OrderClient(order_payload)

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_cafe24_orders({"integrationId": self.integration["id"]})

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["summary"]["responseOrderCount"], 1)
        self.assertEqual(fake_client.orders_calls[0]["statuses"], None)
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["order_status_code"], "N50")
        self.assertEqual(item["payment_status"], "paid")
        self.assertEqual(item["payment_status_source"], "order_status")
        self.assertEqual(item["payment_gate_status"], "payment_confirmed")

    def test_poll_collects_all_offset_pages(self):
        first_page = []
        for index in range(1000):
            payload = json.loads(json.dumps(self._order_payload()))
            payload["order_id"] = f"20260427-{index:06d}"
            payload["items"][0]["order_item_code"] = f"20260427-{index:06d}-01"
            first_page.append(payload)
        second_payload = json.loads(json.dumps(self._order_payload()))
        second_payload["order_id"] = "20260428-999999"
        second_payload["items"][0]["order_item_code"] = "20260428-999999-01"
        fake_client = FakeCafe24OrderClient(self._order_payload())
        fake_client.order_pages = {0: first_page, 1000: [second_payload]}

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_cafe24_orders({"integrationId": self.integration["id"]})

        self.assertEqual(len(fake_client.orders_calls), 2)
        self.assertEqual(fake_client.orders_calls[0]["offset"], 0)
        self.assertEqual(fake_client.orders_calls[1]["offset"], 1000)
        self.assertEqual(result["summary"]["responseOrderCount"], 1001)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1001)

    def test_cafe24_payment_status_codes_pat_are_paid(self):
        for status in ("P", "A", "T"):
            self.conn.execute("DELETE FROM cafe24_order_items")
            self.conn.commit()
            order_payload = self._order_payload()
            order_payload["payment_status"] = status
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
            item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
            self.assertEqual(item["payment_status"], "paid")
            self.assertEqual(item["payment_status_source"], "payload")
            self.assertEqual(item["payment_gate_status"], "payment_confirmed")

    def test_n00_order_is_saved_but_blocked_from_dispatch(self):
        order_payload = self._order_payload()
        order_payload["order_status"] = "N00"
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

        self.assertEqual(result["status"], "payment_pending")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_status_source"], "missing")
        self.assertEqual(item["payment_gate_status"], "payment_pending")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1)

    def test_cancelled_order_is_saved_but_blocked_from_dispatch(self):
        order_payload = self._order_payload()
        order_payload["order_status"] = "C10"
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

        self.assertEqual(result["status"], "cancelled")
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["payment_gate_status"], "cancelled")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1)

    def test_manual_poll_uses_month_window_even_when_last_poll_is_recent(self):
        recent = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        self.conn.execute(
            "UPDATE cafe24_integrations SET last_poll_at = ? WHERE id = ?",
            (recent, self.integration["id"]),
        )
        self.conn.commit()
        fake_client = FakeCafe24OrderClient(self._order_payload())

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            self.store.poll_cafe24_orders({"integrationId": self.integration["id"]})

        self.assertEqual(len(fake_client.orders_calls), 1)
        call = fake_client.orders_calls[0]
        expected_start = (dt.datetime.now().astimezone() - dt.timedelta(days=30)).strftime("%Y-%m-%d")
        expected_end = dt.datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertEqual(call["start_date"], f"{expected_start} 00:00:00")
        self.assertRegex(call["end_date"], rf"^{expected_end} \d{{2}}:\d{{2}}:\d{{2}}$")
        self.assertIsNone(call["statuses"])
        self.assertEqual(call["limit"], 1000)
        self.assertEqual(call["offset"], 0)
        self.assertEqual(call["date_type"], "order_date")

    def test_poll_falls_back_to_paid_date_when_order_date_returns_zero(self):
        fake_client = FakeCafe24OrderClient(self._order_payload())
        fake_client.order_pages = {
            ("order_date", 0): [],
            ("pay_date", 0): [self._order_payload()],
        }

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_cafe24_orders({"integrationId": self.integration["id"]})

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["summary"]["responseOrderCount"], 1)
        self.assertEqual(len(fake_client.orders_calls), 2)
        self.assertEqual(fake_client.orders_calls[0]["date_type"], "order_date")
        self.assertIsNone(fake_client.orders_calls[0]["payment_statuses"])
        self.assertEqual(fake_client.orders_calls[1]["date_type"], "pay_date")
        self.assertEqual(fake_client.orders_calls[1]["payment_statuses"], ["P", "A", "T"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1)

    def test_poll_fetches_order_detail_when_list_response_has_no_items(self):
        list_order = self._order_payload()
        list_order.pop("items")
        fake_client = FakeCafe24OrderClient(self._order_payload())
        fake_client.order_pages = {("order_date", 0): [list_order]}

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_cafe24_orders({"integrationId": self.integration["id"]})

        self.assertEqual(result["processed"], 1)
        self.assertEqual(fake_client.order_calls, ["20260426-000001"])
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["cafe24_order_item_code"], "20260426-000001-01")

    def test_cron_poll_collects_active_integration_without_auto_dispatch(self):
        fake_client = FakeCafe24OrderClient(self._order_payload())

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client), patch("core.SupplierApiClient.order") as order_call:
            result = self.store.poll_due_cafe24_orders({"actor": "cron", "lookbackDays": 30})

        self.assertEqual(result["processedIntegrations"], 1)
        self.assertEqual(result["storedOrderItemCount"], 1)
        self.assertFalse(result["summary"]["autoDispatch"])
        order_call.assert_not_called()
        row = self._integration_row()
        self.assertEqual(row["last_auto_poll_status"], "success")
        self.assertTrue(row["last_auto_poll_at"])
        self.assertFalse(row["cafe24_poll_lock_owner"])
        item = self.conn.execute("SELECT * FROM cafe24_order_items").fetchone()
        self.assertEqual(item["standard_status"], "ready_to_submit")

    def test_cron_poll_skips_recent_success_until_interval_passes(self):
        timestamp = now_iso()
        self.conn.execute(
            "UPDATE cafe24_integrations SET last_auto_poll_at = ?, last_auto_poll_status = ? WHERE id = ?",
            (timestamp, "success", self.integration["id"]),
        )
        self.conn.commit()
        fake_client = FakeCafe24OrderClient(self._order_payload())

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_due_cafe24_orders({"actor": "cron"})

        self.assertEqual(result["processedIntegrations"], 0)
        self.assertEqual(result["skippedIntegrations"], 1)
        self.assertEqual(fake_client.orders_calls, [])

    def test_cron_poll_lock_blocks_duplicate_collection(self):
        future = (dt.datetime.now().astimezone() + dt.timedelta(minutes=5)).isoformat(timespec="seconds")
        self.conn.execute(
            "UPDATE cafe24_integrations SET cafe24_poll_lock_until = ?, cafe24_poll_lock_owner = ? WHERE id = ?",
            (future, "poll_existing", self.integration["id"]),
        )
        self.conn.commit()
        fake_client = FakeCafe24OrderClient(self._order_payload())

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_due_cafe24_orders({"actor": "cron", "force": True})

        self.assertEqual(result["processedIntegrations"], 0)
        self.assertEqual(result["lockedIntegrations"], 1)
        self.assertEqual(fake_client.orders_calls, [])

    def test_cron_poll_reconnect_required_is_reported_without_collection(self):
        self.conn.execute(
            """
            UPDATE cafe24_integrations
            SET token_status = ?, reconnect_reason = ?
            WHERE id = ?
            """,
            ("reconnect_required", "refresh token expired", self.integration["id"]),
        )
        self.conn.commit()
        fake_client = FakeCafe24OrderClient(self._order_payload())

        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            result = self.store.poll_due_cafe24_orders({"actor": "cron", "force": True})

        self.assertEqual(result["processedIntegrations"], 0)
        self.assertEqual(result["reconnectRequiredIntegrations"], 1)
        self.assertEqual(fake_client.orders_calls, [])
        row = self._integration_row()
        self.assertEqual(row["last_auto_poll_status"], "reconnect_required")

    def test_cafe24_order_items_list_defaults_to_five_per_page_for_month_window(self):
        for index in range(6):
            payload = json.loads(json.dumps(self._order_payload()))
            payload["order_id"] = f"20260429-{index:06d}"
            payload["items"][0]["order_item_code"] = f"20260429-{index:06d}-01"
            payload["buyer"]["name"] = f"구매자{index}"
            self.store._process_cafe24_item(
                self.conn,
                integration=self._integration_row(),
                order_payload=payload,
                item_payload=payload["items"][0],
                index=0,
                submit_ready=False,
            )
        self.conn.commit()

        first_page = self.store.list_cafe24_order_items({"page": "1"})
        second_page = self.store.list_cafe24_order_items({"page": "2"})
        searched = self.store.list_cafe24_order_items({"q": "20260429-000005"})

        self.assertEqual(first_page["pagination"]["pageSize"], 5)
        self.assertEqual(first_page["pagination"]["total"], 6)
        self.assertEqual(first_page["pagination"]["totalPages"], 2)
        self.assertEqual(len(first_page["items"]), 5)
        self.assertEqual(len(second_page["items"]), 1)
        self.assertEqual(searched["pagination"]["total"], 1)

    def test_order_id_resync_is_idempotent(self):
        fake_client = FakeCafe24OrderClient(self._order_payload())
        with patch.object(self.store, "_cafe24_client_for_row", return_value=fake_client):
            first = self.store.resync_cafe24_order_by_id(
                {"integrationId": self.integration["id"], "orderId": "20260426-000001"}
            )
            second = self.store.resync_cafe24_order_by_id(
                {"integrationId": self.integration["id"], "orderId": "20260426-000001"}
            )

        self.assertEqual(first["processed"], 1)
        self.assertEqual(second["processed"], 1)
        self.assertEqual(fake_client.order_calls, ["20260426-000001", "20260426-000001"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cafe24_order_items").fetchone()[0], 1)

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
                "core.Cafe24ApiClient.exchange_authorization_code",
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
            "core.Cafe24ApiClient.refresh_access_token",
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

    def test_cafe24_product_lookup_requires_product_scope(self):
        self.conn.execute(
            "UPDATE cafe24_integrations SET scopes_json = ? WHERE id = ?",
            (json.dumps(["mall.read_order", "mall.write_order"], ensure_ascii=False), self.integration["id"]),
        )
        self.conn.commit()

        with self.assertRaises(PanelError) as context:
            self.store.list_cafe24_products({"integrationId": self.integration["id"], "q": "인스타"})

        self.assertEqual(context.exception.status, 403)
        self.assertIn("mall.read_product", str(context.exception))

    def test_cafe24_product_lookup_exposes_api_error_without_generic_500(self):
        with patch.object(self.store, "_cafe24_client_for_row", return_value=FailingCafe24ProductClient()):
            with self.assertRaises(PanelError) as context:
                self.store.list_cafe24_products({"integrationId": self.integration["id"], "q": "인스타"})

        self.assertEqual(context.exception.status, 403)
        self.assertIn("상품 읽기 권한", str(context.exception))

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
