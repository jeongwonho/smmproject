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
from backend.integrations.cafe24_preflight import build_cafe24_order_item_preflight, cafe24_preflight_quantity


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

    def test_preflight_helper_reports_conditions_without_target_values(self):
        item = {
            "mallId": "growit",
            "shopNo": 1,
            "orderId": "20260506-0000024",
            "orderItemCode": "20260506-0000024-01",
            "productNo": "12",
            "variantCode": "P000000M000D",
            "customProductCode": "P000000M",
            "standardStatus": "ready_to_submit",
            "paymentGateStatus": "payment_confirmed",
            "automationErrorCode": "",
            "errorMessage": "",
            "mappingId": "mapping-1",
            "supplierId": "supplier-1",
            "supplierServiceId": "service-1",
            "supplierExternalServiceId": "40000",
            "supplierOrderUuid": "",
            "targetDiagnostics": {
                "status": "normalized",
                "normalized": True,
                "message": "",
                "supplierStatus": "",
                "supplierReasonCode": "",
                "supplierReasonMessage": "",
            },
        }
        supplier_payload = {
            "service": "40000",
            "link": "https://www.instagram.com/instamart_official/",
            "quantity": "50",
        }

        preflight = build_cafe24_order_item_preflight(
            item_id="item-1",
            item=item,
            normalized_fields={},
            supplier_payload=supplier_payload,
            readiness={"ok": True, "code": "ok", "message": "발주 가능"},
            expected_quantity=50,
            checked_at="2026-05-22T10:00:00+00:00",
        )

        self.assertEqual(cafe24_preflight_quantity({}, supplier_payload), 50)
        self.assertTrue(preflight["canDispatch"])
        self.assertEqual(preflight["supplierPayload"]["keys"], ["link", "quantity", "service"])
        self.assertTrue(preflight["supplierPayload"]["hasTarget"])
        self.assertTrue(preflight["supplierPayload"]["hasQuantity"])
        self.assertNotIn("instamart_official", str(preflight))


if __name__ == "__main__":
    unittest.main()
