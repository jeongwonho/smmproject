import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core import PanelError, PanelStore, now_iso


class PublicOrderProgressTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "order_progress.db"
        self.store = PanelStore(db_path=self.db_path)
        self.store.save_cafe24_integration(
            {
                "mallId": "instamart",
                "shopNo": 1,
                "accessToken": "access-token",
                "refreshToken": "refresh-token",
                "scopes": ["mall.read_order"],
                "autoSubmit": False,
            }
        )
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _insert_item(
        self,
        *,
        item_id,
        order_id="20260724-0000087",
        item_code,
        product_name,
        status="supplier_progress",
        quantity=1000,
        supplier_response=None,
        buyer_name="홍길동",
        buyer_phone="+82 10-1234-5678",
        payment_gate_status="payment_confirmed",
        order_date="2026-07-24T10:30:00+09:00",
    ):
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO cafe24_order_items (
                id, mall_id, shop_no, cafe24_order_id, cafe24_order_item_code,
                cafe24_order_date, buyer_name, buyer_phone, payment_gate_status,
                standard_status, normalized_fields_json, supplier_payload_json,
                raw_payload_json, supplier_response_json, automation_last_checked_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                "instamart",
                1,
                order_id,
                item_code,
                order_date,
                buyer_name,
                buyer_phone,
                payment_gate_status,
                status,
                json.dumps(
                    {
                        "targetValue": "https://www.instagram.com/instamart_official/",
                        "orderedCount": quantity,
                    }
                ),
                json.dumps(
                    {
                        "link": "https://www.instagram.com/instamart_official/",
                        "quantity": quantity,
                    }
                ),
                json.dumps({"item": {"product_name": product_name, "quantity": quantity}}),
                json.dumps(supplier_response or {}),
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()

    def _lookup(self, **overrides):
        payload = {
            "orderNumber": "20260724-0000087",
            "buyerName": " 홍 길 동 ",
            "phoneNumber": "010-1234-5678",
        }
        payload.update(overrides)
        return self.store.lookup_public_order_progress(payload)

    def test_lookup_returns_every_item_without_private_supplier_or_buyer_fields(self):
        checked_at = now_iso()
        self._insert_item(
            item_id="item_1",
            item_code="20260724-0000087-01",
            product_name="[데일리] 한국인 팔로워 늘리기",
            supplier_response={
                "lastStatusCheck": {
                    "checkedAt": checked_at,
                    "payload": {"status": "In progress", "remains": 400},
                }
            },
        )
        self._insert_item(
            item_id="item_2",
            item_code="20260724-0000087-02",
            product_name="한국인 좋아요 늘리기",
            status="completed",
            quantity=300,
        )

        result = self._lookup()

        self.assertTrue(result["found"])
        self.assertEqual(result["order"]["orderNumber"], "20260724-0000087")
        self.assertEqual(len(result["order"]["items"]), 2)
        first, second = result["order"]["items"]
        self.assertEqual(first["accountName"], "@instamart_official")
        self.assertEqual(first["progress"]["percent"], 60)
        self.assertEqual(first["statusLabel"], "진행중")
        self.assertEqual(second["statusLabel"], "진행 완료")
        self.assertFalse(second["progress"]["supported"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("010-1234-5678", serialized)
        self.assertNotIn("홍길동", serialized)
        self.assertNotIn("supplierOrder", serialized)
        self.assertNotIn("rawPayload", serialized)

    def test_lookup_uses_one_generic_not_found_result_for_identity_mismatch(self):
        self._insert_item(
            item_id="item_1",
            item_code="20260724-0000087-01",
            product_name="한국인 팔로워 늘리기",
        )

        wrong_name = self._lookup(buyerName="다른사람")
        wrong_phone = self._lookup(phoneNumber="010-9999-9999")
        missing_order = self._lookup(orderNumber="20260724-9999999")

        self.assertEqual(wrong_name, {"found": False})
        self.assertEqual(wrong_phone, {"found": False})
        self.assertEqual(missing_order, {"found": False})

    def test_stale_remains_is_reported_as_unsupported(self):
        stale_checked_at = (
            dt.datetime.now().astimezone() - dt.timedelta(minutes=31)
        ).isoformat(timespec="seconds")
        self._insert_item(
            item_id="item_1",
            item_code="20260724-0000087-01",
            product_name="한국인 팔로워 늘리기",
            supplier_response={
                "lastStatusCheck": {
                    "checkedAt": stale_checked_at,
                    "payload": {"remains": 100},
                }
            },
        )

        result = self._lookup()

        self.assertFalse(result["order"]["items"][0]["progress"]["supported"])
        self.assertIsNone(result["order"]["items"][0]["progress"]["percent"])

    def test_unpaid_and_manual_review_orders_are_not_labeled_in_progress(self):
        self._insert_item(
            item_id="unpaid_item",
            item_code="20260724-0000087-01",
            product_name="한국인 팔로워 늘리기",
            status="payment_pending",
            payment_gate_status="payment_pending",
        )
        self._insert_item(
            item_id="waiting_item",
            item_code="20260724-0000087-02",
            product_name="한국인 좋아요 늘리기",
            status="waiting_input",
        )

        items = self._lookup()["order"]["items"]

        self.assertEqual([item["status"] for item in items], ["attention", "attention"])
        self.assertEqual([item["statusLabel"] for item in items], ["확인 필요", "확인 필요"])

    def test_row_level_cancellation_takes_priority_over_existing_split_job(self):
        self._insert_item(
            item_id="cancelled_daily_item",
            item_code="20260724-0000087-01",
            product_name="[데일리] 한국인 팔로워 늘리기",
            status="cancelled",
            payment_gate_status="cancelled",
            quantity=500,
        )
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO cafe24_split_jobs (
                id, cafe24_order_item_id, mall_id, shop_no, cafe24_order_id,
                cafe24_order_item_code, status, target_value, total_quantity,
                daily_quantity, duration_days, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cancelled_split_job",
                "cancelled_daily_item",
                "instamart",
                1,
                "20260724-0000087",
                "20260724-0000087-01",
                "in_progress",
                "https://www.instagram.com/instamart_official/",
                500,
                100,
                5,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()

        item = self._lookup()["order"]["items"][0]

        self.assertEqual(item["status"], "attention")
        self.assertEqual(item["statusLabel"], "확인 필요")

    def test_daily_split_progress_aggregates_completed_active_and_pending_parts(self):
        self._insert_item(
            item_id="daily_item",
            item_code="20260724-0000087-01",
            product_name="[데일리] 한국인 팔로워 늘리기",
            quantity=500,
        )
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO cafe24_split_jobs (
                id, cafe24_order_item_id, mall_id, shop_no, cafe24_order_id,
                cafe24_order_item_code, status, target_value, total_quantity,
                daily_quantity, duration_days, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "split_job_1",
                "daily_item",
                "instamart",
                1,
                "20260724-0000087",
                "20260724-0000087-01",
                "in_progress",
                "https://www.instagram.com/instamart_official/",
                500,
                100,
                5,
                timestamp,
                timestamp,
            ),
        )
        part_rows = [
            ("part_1", 1, "completed", {}),
            ("part_2", 2, "completed", {}),
            (
                "part_3",
                3,
                "supplier_progress",
                {
                    "lastStatusCheck": {
                        "checkedAt": timestamp,
                        "payload": {"remains": 50},
                    }
                },
            ),
            ("part_4", 4, "pending", {}),
            ("part_5", 5, "pending", {}),
        ]
        for part_id, sequence, status, response in part_rows:
            self.conn.execute(
                """
                INSERT INTO cafe24_split_job_parts (
                    id, split_job_id, cafe24_order_item_id, sequence, quantity,
                    scheduled_at, status, supplier_response_json,
                    last_status_checked_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part_id,
                    "split_job_1",
                    "daily_item",
                    sequence,
                    100,
                    timestamp,
                    status,
                    json.dumps(response),
                    timestamp if status == "supplier_progress" else "",
                    timestamp,
                    timestamp,
                ),
            )
        self.conn.commit()

        item = self._lookup()["order"]["items"][0]

        self.assertEqual(item["dailyQuantity"], 100)
        self.assertEqual(item["totalQuantity"], 500)
        self.assertEqual(item["progress"]["percent"], 50)
        self.assertTrue(item["progress"]["supported"])

    def test_lookup_rejects_incomplete_identity(self):
        with self.assertRaises(PanelError) as raised:
            self.store.lookup_public_order_progress(
                {
                    "orderNumber": "20260724-0000087",
                    "buyerName": "",
                    "phoneNumber": "010-1234-5678",
                }
            )

        self.assertEqual(raised.exception.status, 400)

    def test_active_lookup_requires_reference_order_and_returns_only_matching_progress(self):
        self._insert_item(
            item_id="reference_completed",
            order_id="20260724-0000001",
            item_code="20260724-0000001-01",
            product_name="완료된 기준 주문",
            status="completed",
        )
        self._insert_item(
            item_id="active_item",
            order_id="20260724-0000002",
            item_code="20260724-0000002-01",
            product_name="진행중 주문",
            status="supplier_progress",
            buyer_phone="010-1234-5678",
            order_date="2026-07-24T11:00:00+09:00",
        )
        self._insert_item(
            item_id="completed_item",
            order_id="20260724-0000003",
            item_code="20260724-0000003-01",
            product_name="다른 완료 주문",
            status="completed",
        )
        self._insert_item(
            item_id="attention_item",
            order_id="20260724-0000004",
            item_code="20260724-0000004-01",
            product_name="확인 필요 주문",
            status="waiting_input",
        )
        self._insert_item(
            item_id="other_customer_item",
            order_id="20260724-0000005",
            item_code="20260724-0000005-01",
            product_name="다른 고객 주문",
            status="supplier_progress",
            buyer_phone="010-9999-9999",
        )

        result = self.store.lookup_public_active_order_progress(
            {
                "orderNumber": "20260724-0000001",
                "buyerName": "홍길동",
                "phoneNumber": "01012345678",
            }
        )

        self.assertTrue(result["found"])
        self.assertEqual(result["view"], "active")
        self.assertEqual(result["summary"]["orderCount"], 1)
        self.assertEqual(result["summary"]["itemCount"], 1)
        self.assertEqual(
            [order["orderNumber"] for order in result["orders"]],
            ["20260724-0000002"],
        )
        self.assertEqual(result["orders"][0]["items"][0]["status"], "in_progress")
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("010-1234-5678", serialized)
        self.assertNotIn("홍길동", serialized)
        self.assertNotIn("supplierOrder", serialized)

    def test_active_lookup_groups_multiple_items_and_normalizes_saved_phone_format(self):
        self._insert_item(
            item_id="reference_item",
            order_id="20260724-0000010",
            item_code="20260724-0000010-01",
            product_name="기준 주문",
            status="completed",
            buyer_phone="010-1234-5678",
        )
        for index in range(2):
            self._insert_item(
                item_id=f"active_group_{index}",
                order_id="20260724-0000011",
                item_code=f"20260724-0000011-0{index + 1}",
                product_name=f"진행중 서비스 {index + 1}",
                status="supplier_progress",
                buyer_phone="+82 10 1234 5678",
            )

        result = self.store.lookup_public_active_order_progress(
            {
                "orderNumber": "20260724-0000010",
                "buyerName": " 홍 길 동 ",
                "phoneNumber": "010-1234-5678",
            }
        )

        self.assertTrue(result["found"])
        self.assertEqual(len(result["orders"]), 1)
        self.assertEqual(len(result["orders"][0]["items"]), 2)

    def test_active_lookup_does_not_expand_from_wrong_reference_identity(self):
        self._insert_item(
            item_id="reference_item",
            order_id="20260724-0000020",
            item_code="20260724-0000020-01",
            product_name="기준 주문",
            status="completed",
        )
        self._insert_item(
            item_id="active_item",
            order_id="20260724-0000021",
            item_code="20260724-0000021-01",
            product_name="진행중 주문",
            status="supplier_progress",
        )

        result = self.store.lookup_public_active_order_progress(
            {
                "orderNumber": "20260724-0000020",
                "buyerName": "다른고객",
                "phoneNumber": "010-1234-5678",
            }
        )

        self.assertEqual(result, {"found": False})

    def test_active_lookup_returns_empty_orders_after_valid_completed_reference(self):
        self._insert_item(
            item_id="reference_item",
            order_id="20260724-0000030",
            item_code="20260724-0000030-01",
            product_name="완료된 주문",
            status="completed",
        )

        result = self.store.lookup_public_active_order_progress(
            {
                "orderNumber": "20260724-0000030",
                "buyerName": "홍길동",
                "phoneNumber": "010-1234-5678",
            }
        )

        self.assertTrue(result["found"])
        self.assertEqual(result["orders"], [])
        self.assertEqual(result["summary"]["orderCount"], 0)


if __name__ == "__main__":
    unittest.main()
