import datetime as dt
import unittest

import bootstrap
from backend.integrations.cafe24 import (
    CAFE24_MANUAL_INPUT_REQUIRED_STATUSES,
    CAFE24_REVIEW_REQUIRED_STATUSES,
    CAFE24_STANDARD_STATUSES,
    cafe24_access_token_error,
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
from backend.integrations.cafe24_mapping_gaps import annotate_cafe24_mapping_gap_groups
from backend.integrations.cafe24_manual import build_cafe24_manual_input_cron_response
from backend.integrations.cafe24_preflight import (
    build_cafe24_order_item_preflight,
    build_cafe24_mapping_preview_report,
    cafe24_expected_quantity_from_payload,
    cafe24_order_item_selector_from_payload,
    cafe24_order_item_selector_has_lookup,
    cafe24_preflight_quantity,
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

    def test_cafe24_status_groups_are_exposed_from_domain_module(self):
        self.assertIn("ready_to_submit", CAFE24_STANDARD_STATUSES)
        self.assertIn("waiting_input", CAFE24_STANDARD_STATUSES)
        self.assertIn("waiting_input", CAFE24_MANUAL_INPUT_REQUIRED_STATUSES)
        self.assertIn("payment_review_required", CAFE24_REVIEW_REQUIRED_STATUSES)
        self.assertNotIn("payment_review_required", CAFE24_MANUAL_INPUT_REQUIRED_STATUSES)

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
        self.assertTrue(
            cafe24_access_token_error(
                'Cafe24 API 오류 401: {"error":{"code":401,"message":"access_token time expired. (invalid_token)"}}'
            )
        )
        self.assertTrue(cafe24_access_token_error("401 Unauthorized: invalid token"))
        self.assertFalse(cafe24_access_token_error("403 scope permission denied"))

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

    def test_manual_input_cron_response_redacts_target_values(self):
        response = build_cafe24_manual_input_cron_response(
            item_id="item-1",
            result={
                "normalizedFields": {"orderedCount": "50", "targetValue": "private_account"},
                "supplierPayload": {
                    "service": "40000",
                    "link": "https://www.instagram.com/private_account/",
                    "quantity": "50",
                },
            },
            preflight={
                "canDispatch": True,
                "blockingReasons": [],
                "quantity": {"normalized": 50},
            },
            dispatch_after_save=True,
            dispatch={"submitted": True, "supplierOrderUuid": "SUP-1001"},
        )

        self.assertTrue(response["dispatchAfterSave"])
        self.assertEqual(response["normalizedFields"], {"keys": ["orderedCount", "targetValue"], "orderedCount": "50"})
        self.assertEqual(response["supplierPayload"]["service"], "40000")
        self.assertTrue(response["supplierPayload"]["hasTarget"])
        self.assertTrue(response["supplierPayload"]["hasQuantity"])
        self.assertTrue(response["dispatch"]["submitted"])
        rendered = str(response)
        self.assertNotIn("private_account", rendered)
        self.assertNotIn("instagram.com/private_account", rendered)

    def test_order_item_selector_supports_item_id_or_cafe24_identity(self):
        item_selector = cafe24_order_item_selector_from_payload({"itemId": " item-1 "}, default_shop_no=1)
        lookup_selector = cafe24_order_item_selector_from_payload(
            {
                "mall_id": "growit",
                "shop_no": "2",
                "order_id": "20260506-0000024",
                "order_item_code": "20260506-0000024-01",
            },
            default_shop_no=1,
        )
        missing_selector = cafe24_order_item_selector_from_payload({"mallId": "growit"}, default_shop_no=1)

        self.assertEqual(item_selector["itemId"], "item-1")
        self.assertTrue(cafe24_order_item_selector_has_lookup(item_selector))
        self.assertEqual(lookup_selector["shopNo"], 2)
        self.assertEqual(lookup_selector["orderItemCode"], "20260506-0000024-01")
        self.assertTrue(cafe24_order_item_selector_has_lookup(lookup_selector))
        self.assertFalse(cafe24_order_item_selector_has_lookup(missing_selector))

    def test_expected_quantity_parser_accepts_commas_and_rejects_invalid_values(self):
        self.assertEqual(cafe24_expected_quantity_from_payload({"expectedQuantity": "1,500"}), 1500)
        self.assertEqual(cafe24_expected_quantity_from_payload({"expected_quantity": ""}), 0)
        with self.assertRaises(ValueError):
            cafe24_expected_quantity_from_payload({"expectedQuantity": "many"})
        with self.assertRaises(ValueError):
            cafe24_expected_quantity_from_payload({"expectedQuantity": "-1"})

    def test_mapping_preview_report_redacts_target_values_but_keeps_payload_shape(self):
        report = build_cafe24_mapping_preview_report(
            {
                "ok": True,
                "errors": [],
                "sampleOrderItemId": "item-1",
                "normalizedFields": {"targetValue": "instamart_official", "orderedCount": "50"},
                "supplierPayload": {"service": "40000", "link": "https://instagram.com/instamart_official", "quantity": "50"},
                "optionEntries": [{"name": "수량", "value": "50명"}],
                "quantityCandidates": [{"value": 50, "raw": "50명", "label": "수량", "source": "option"}],
                "fieldMapping": {"targetValue": {"source": "option", "optionName": "계정"}},
            },
            expected_quantity=50,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["supplierPayloadKeys"], ["link", "quantity", "service"])
        self.assertEqual(report["supplierPayload"]["service"], "40000")
        self.assertEqual(report["supplierPayload"]["quantity"], "50")
        self.assertEqual(report["supplierPayload"]["link"], "<redacted>")
        self.assertEqual(report["normalizedFields"]["targetValue"], "<redacted>")
        self.assertEqual(report["quantity"]["normalized"], 50)
        self.assertTrue(report["supplierPayloadDiagnostics"]["hasTarget"])
        self.assertTrue(report["supplierPayloadDiagnostics"]["hasQuantity"])
        self.assertNotIn("instamart_official", str(report))

    def test_mapping_gap_diagnostics_marks_personal_payment_as_manual_input_required(self):
        groups = [
            {
                "productNo": "32",
                "variantCode": "P00000BG000A",
                "customProductCode": "P00000BG",
                "count": 2,
                "optionLabels": [],
                "quantityCandidates": [],
            }
        ]
        details = {
            "32": {
                "productName": "개인결제",
                "options": [{"name": "", "value": "", "values": []}],
                "variants": [{"variantCode": "P00000BG000A"}],
            }
        }

        annotated = annotate_cafe24_mapping_gap_groups(groups, details)

        self.assertEqual(annotated[0]["diagnostics"]["status"], "manual_input_required")
        self.assertTrue(annotated[0]["diagnostics"]["manualInputRequired"])
        self.assertFalse(annotated[0]["diagnostics"]["mappingCandidate"])
        self.assertTrue(annotated[0]["diagnostics"]["personalPaymentLike"])
        self.assertTrue(annotated[0]["diagnostics"]["hasVariantMatch"])
        self.assertEqual(annotated[0]["diagnostics"]["matchedVariant"]["variantCode"], "P00000BG000A")
        self.assertIn("수동 보정", annotated[0]["diagnostics"]["nextAction"])


if __name__ == "__main__":
    unittest.main()
