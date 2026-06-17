import datetime as dt
import unittest

import bootstrap
from backend.errors import PanelError
from backend.integrations.cafe24 import (
    CAFE24_MANUAL_INPUT_REQUIRED_STATUSES,
    CAFE24_REVIEW_REQUIRED_STATUSES,
    CAFE24_STANDARD_STATUSES,
    Cafe24PollWindowError,
    Cafe24DispatchRequestError,
    cafe24_access_token_error,
    cafe24_auto_poll_due,
    cafe24_dispatch_request_context,
    cafe24_enriched_product_payload,
    cafe24_integration_payload_from_row,
    cafe24_item_identity,
    cafe24_next_auto_poll_at,
    cafe24_normalize_datetime_text,
    cafe24_order_has_embedded_items,
    cafe24_order_item_filter_clauses,
    cafe24_order_item_list_options,
    cafe24_order_item_pagination_payload,
    cafe24_order_item_payload_from_row,
    cafe24_order_item_summary_payload,
    cafe24_order_items_from_order,
    cafe24_orders_from_payload,
    cafe24_option_entries,
    cafe24_option_payload,
    cafe24_option_pairs,
    cafe24_payment_gate_status,
    cafe24_payment_snapshot_from_payload,
    cafe24_payment_status_with_source,
    cafe24_poll_datetime_window,
    cafe24_product_options_from_payload,
    cafe24_product_payload,
    cafe24_product_variants_from_payload,
    cafe24_products_from_payload,
    cafe24_processing_error_status,
    cafe24_refresh_error_requires_reconnect,
    cafe24_refresh_token_expired,
    cafe24_variant_payload,
    cafe24_status_in_progress,
    cafe24_status_is_payment_blocked,
    cafe24_status_needs_operator_action,
    cafe24_status_requires_manual_input,
    cafe24_status_requires_review,
    cafe24_supplier_dispatch_outcome,
    cafe24_token_status,
    cafe24_token_status_label,
    cafe24_token_status_message,
    normalize_cafe24_payment_status,
    normalize_cafe24_scopes,
    normalize_cafe24_shop_no,
    normalize_cafe24_status,
)
from backend.integrations.cafe24_mapping_gaps import (
    Cafe24MappingGapDetailBudget,
    annotate_cafe24_mapping_gap_groups,
    cafe24_mapping_gap_item_payload,
    cafe24_mapping_gap_product_filter,
    cafe24_mapping_gap_report_options,
    fetch_cafe24_mapping_gap_product_details,
)
from backend.integrations.cafe24_manual import (
    Cafe24ManualInputError,
    build_cafe24_manual_input_plan_payload,
    build_cafe24_manual_input_cron_response,
    build_cafe24_manual_input_preview_response,
    cafe24_manual_expected_quantity,
    cafe24_manual_input_request,
    cafe24_manual_order_fields,
    cafe24_manual_product_payload,
    cafe24_manual_supplier_mapping,
    cafe24_validate_manual_input_order_item,
    cafe24_validate_manual_input_supplier,
)
from backend.integrations.cafe24_audit import resolve_cafe24_audit_runtime_mode
from backend.integrations.cafe24_panel import (
    cafe24_expected_quantity_from_payload_for_panel,
    cafe24_order_item_id_for_panel,
    cafe24_order_item_selector_for_panel,
    validate_cafe24_direct_fields_for_panel,
)
from backend.integrations.cafe24_preflight import (
    build_cafe24_order_item_preflight,
    build_cafe24_mapping_preview_report,
    cafe24_expected_quantity_from_payload,
    cafe24_order_item_selector_from_payload,
    cafe24_order_item_selector_has_lookup,
    cafe24_preflight_quantity,
)
from backend.integrations.supplier_targets import (
    ACCOUNT_STYLE_PLATFORMS,
    account_preview_url,
    platform_target_error_message,
    platform_target_url_matches,
    preview_platform_hint,
    SupplierTargetError,
    supplier_panel_target_link,
    supplier_supported_hosts,
    validate_supplier_panel_target_link,
)


class Cafe24IntegrationHelperTest(unittest.TestCase):
    def test_audit_runtime_mode_does_not_label_vercel_production_as_local(self):
        self.assertEqual(
            resolve_cafe24_audit_runtime_mode("", production_runtime=True),
            {"runtimeMode": "production", "runtimeModeSource": "inferred"},
        )
        self.assertEqual(
            resolve_cafe24_audit_runtime_mode("", production_runtime=False),
            {"runtimeMode": "local", "runtimeModeSource": "default"},
        )
        self.assertEqual(
            resolve_cafe24_audit_runtime_mode("Production", production_runtime=True),
            {"runtimeMode": "production", "runtimeModeSource": "env"},
        )

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
        self.assertTrue(cafe24_status_requires_manual_input("waiting_input"))
        self.assertFalse(cafe24_status_requires_manual_input("field_extract_failed"))
        self.assertTrue(cafe24_status_requires_review("field_extract_failed"))
        self.assertTrue(cafe24_status_in_progress("supplier_progress"))
        self.assertTrue(cafe24_status_needs_operator_action("field_extract_failed"))
        self.assertFalse(cafe24_status_needs_operator_action("payment_review_required"))
        self.assertTrue(cafe24_status_is_payment_blocked("payment_review_required"))

    def test_manual_input_cron_response_redacts_target_values(self):
        response = build_cafe24_manual_input_cron_response(
            item_id="cafe24_item_1",
            result={
                "normalizedFields": {"orderedCount": "50", "targetValue": "private_account"},
                "supplierPayload": {
                    "link": "https://instagram.com/private_account",
                    "quantity": "50",
                    "service": "40000",
                },
            },
            preflight={"canDispatch": True, "blockingReasons": []},
            dispatch_after_save=True,
            dispatch={
                "id": "cafe24_item_1",
                "status": "supplier_submitted",
                "submitted": True,
                "supplierOrderUuid": "order-uuid-1",
            },
        )

        rendered = str(response)
        self.assertNotIn("private_account", rendered)
        self.assertNotIn("instagram.com/private_account", rendered)
        self.assertEqual(response["normalizedFields"], {"keys": ["orderedCount", "targetValue"], "orderedCount": "50"})
        self.assertEqual(response["supplierPayload"]["service"], "40000")
        self.assertTrue(response["supplierPayload"]["hasTarget"])
        self.assertTrue(response["supplierPayload"]["hasQuantity"])
        self.assertTrue(response["dispatchAfterSave"])
        self.assertTrue(response["dispatch"]["submitted"])

    def test_manual_input_preview_response_uses_redactor_and_update_summary(self):
        response = build_cafe24_manual_input_preview_response(
            item_id="cafe24_item_1",
            preflight={"canDispatch": True, "identity": {"orderId": "20260512-0000017"}},
            supplier_id="supplier_1",
            supplier_service_id="service_1",
            supplier_external_service_id="40000",
            normalized_fields={"orderedCount": "50", "targetValue": "private_account"},
            supplier_payload={"service": "40000", "link": "https://instagram.com/private_account", "quantity": "50"},
            redactor=lambda value: "<redacted>" if isinstance(value, dict) and "targetValue" in value else value,
        )

        self.assertTrue(response["dryRun"])
        self.assertEqual(response["itemId"], "cafe24_item_1")
        self.assertEqual(response["identity"], {"orderId": "20260512-0000017"})
        self.assertEqual(response["wouldUpdate"]["standardStatus"], "ready_to_submit")
        self.assertEqual(response["wouldUpdate"]["supplierExternalServiceId"], "40000")
        self.assertEqual(response["wouldUpdate"]["normalizedFieldKeys"], ["orderedCount", "targetValue"])
        self.assertEqual(response["wouldUpdate"]["supplierPayloadKeys"], ["link", "quantity", "service"])
        self.assertEqual(response["normalizedFields"], "<redacted>")
        self.assertEqual(response["supplierPayload"]["service"], "40000")
        self.assertTrue(response["preflight"]["canDispatch"])

    def test_cafe24_processing_error_status_is_domain_helper(self):
        self.assertEqual(cafe24_processing_error_status("수량은 숫자로 입력되어야 합니다."), "invalid_quantity")
        self.assertEqual(cafe24_processing_error_status("공급사 최소 수량(100)보다 작습니다."), "supplier_range_error")
        self.assertEqual(cafe24_processing_error_status("대상 URL 형식이 올바르지 않습니다."), "invalid_target")
        self.assertEqual(cafe24_processing_error_status("필수 입력값이 없습니다."), "missing_required_field")
        self.assertEqual(cafe24_processing_error_status("수량 후보가 여러 개라 검수가 필요합니다."), "needs_manual_review")

    def test_cafe24_product_payload_helpers_are_domain_helpers(self):
        response = {
            "products": [
                {
                    "product_no": "1001",
                    "product_name": "인스타 팔로워",
                    "custom_product_code": "IG-FOLLOWER",
                    "price": "1000.00",
                    "options": [{"option_name": "수량", "option_values": ["100개", "500개"]}],
                    "variants": [
                        {
                            "variant_code": "P00000AA000A",
                            "custom_product_code": "IG-FOLLOWER-100",
                            "option_value": "100개",
                            "stock_quantity": "999",
                        }
                    ],
                }
            ]
        }

        product_rows = cafe24_products_from_payload(response)
        product = cafe24_product_payload(product_rows[0], include_raw=True)
        options = cafe24_product_options_from_payload(response["products"][0]["options"])
        variants = cafe24_product_variants_from_payload(response["products"][0]["variants"])

        self.assertEqual(product["productNo"], "1001")
        self.assertEqual(product["customProductCode"], "IG-FOLLOWER")
        self.assertIs(product["raw"], response["products"][0])
        self.assertEqual(cafe24_option_payload(options[0])["values"], ["100개", "500개"])
        self.assertEqual(cafe24_variant_payload(variants[0])["variantCode"], "P00000AA000A")
        self.assertEqual(product["variants"][0]["stockQuantity"], "999")

        enriched = cafe24_enriched_product_payload(
            {"product_no": "1002", "product_name": "릴스 조회수"},
            option_response={"options": [{"option_name": "수량", "option_values": ["1000회"]}]},
            variant_response={"variants": [{"variant_code": "P00000AB000A", "stock_quantity": "50"}]},
        )
        self.assertEqual(enriched["productNo"], "1002")
        self.assertEqual(enriched["options"][0]["values"], ["1000회"])
        self.assertEqual(enriched["variants"][0]["variantCode"], "P00000AB000A")

        fallback = cafe24_enriched_product_payload(
            {
                "product_no": "1003",
                "product_name": "좋아요",
                "options": [{"option_name": "수량", "option_values": ["50개"]}],
            },
            option_response={"options": []},
        )
        self.assertEqual(fallback["options"][0]["values"], ["50개"])

    def test_cafe24_order_payload_helpers_are_domain_helpers(self):
        embedded_order = {
            "order_id": "20260426-000001",
            "items": [
                {"order_item_code": "20260426-000001-01"},
                "ignored",
            ],
        }
        single_order = {"order": embedded_order}
        order_list = {"orders": [embedded_order, "ignored"]}
        flat_item_order = {"order_id": "20260426-000002", "order_item_code": "20260426-000002-01"}

        self.assertEqual(cafe24_orders_from_payload(single_order), [embedded_order])
        self.assertEqual(cafe24_orders_from_payload(order_list), [embedded_order])
        self.assertEqual(cafe24_orders_from_payload([embedded_order, "ignored"]), [embedded_order])
        self.assertEqual(cafe24_order_items_from_order(embedded_order), [{"order_item_code": "20260426-000001-01"}])
        self.assertEqual(cafe24_order_items_from_order(flat_item_order), [flat_item_order])
        self.assertTrue(cafe24_order_has_embedded_items(embedded_order))
        self.assertFalse(cafe24_order_has_embedded_items(flat_item_order))

    def test_cafe24_supplier_dispatch_outcome_extracts_order_ids(self):
        self.assertEqual(
            cafe24_supplier_dispatch_outcome({"order": "SUP-1"}),
            {"status": "supplier_submitted", "supplierExternalOrderId": "SUP-1", "errorMessage": ""},
        )
        self.assertEqual(
            cafe24_supplier_dispatch_outcome({"orderUuid": "SUP-UUID-1"})["supplierExternalOrderId"],
            "SUP-UUID-1",
        )
        ambiguous = cafe24_supplier_dispatch_outcome({"message": "accepted"})
        self.assertEqual(ambiguous["status"], "needs_manual_review")
        self.assertIn("주문 ID", ambiguous["errorMessage"])
        empty = cafe24_supplier_dispatch_outcome({})
        self.assertEqual(empty["status"], "failed")
        self.assertIn("비어", empty["errorMessage"])

    def test_cafe24_dispatch_request_context_validates_preconditions(self):
        ready_row = {
            "id": "cafe24_item_1",
            "payment_gate_status": "payment_confirmed",
            "standard_status": "ready_to_submit",
            "automation_error_code": "",
            "supplier_is_active": 1,
            "supplier_id": "supplier_1",
            "supplier_external_service_id": "svc-1",
            "supplier_order_uuid": "",
        }

        context = cafe24_dispatch_request_context(ready_row, {"service": "svc-1", "quantity": "50"})

        self.assertFalse(context["duplicate"])
        self.assertEqual(context["requestPayload"]["service"], "svc-1")
        self.assertFalse(context["retryingTokenExpired"])

        duplicate = cafe24_dispatch_request_context(
            {**ready_row, "standard_status": "supplier_submitted", "supplier_order_uuid": "SUP-1"},
            {"service": "svc-1"},
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["response"]["supplierOrderUuid"], "SUP-1")

    def test_cafe24_dispatch_request_context_allows_token_expired_retry(self):
        context = cafe24_dispatch_request_context(
            {
                "id": "cafe24_item_1",
                "payment_gate_status": "payment_confirmed",
                "standard_status": "needs_manual_review",
                "automation_error_code": "supplier_token_expired",
                "supplier_is_active": 1,
                "supplier_id": "supplier_1",
                "supplier_external_service_id": "svc-1",
                "supplier_order_uuid": "",
            },
            {"service": "svc-1", "quantity": "50"},
        )

        self.assertFalse(context["duplicate"])
        self.assertTrue(context["retryingTokenExpired"])

    def test_cafe24_dispatch_request_context_blocks_incomplete_rows(self):
        base_row = {
            "id": "cafe24_item_1",
            "payment_gate_status": "payment_confirmed",
            "standard_status": "ready_to_submit",
            "automation_error_code": "",
            "supplier_is_active": 1,
            "supplier_id": "supplier_1",
            "supplier_external_service_id": "svc-1",
            "supplier_order_uuid": "",
        }

        with self.assertRaisesRegex(Cafe24DispatchRequestError, "결제완료"):
            cafe24_dispatch_request_context({**base_row, "payment_gate_status": "unpaid"}, {"service": "svc-1"})
        with self.assertRaisesRegex(Cafe24DispatchRequestError, "비활성"):
            cafe24_dispatch_request_context({**base_row, "supplier_is_active": 0}, {"service": "svc-1"})
        with self.assertRaisesRegex(Cafe24DispatchRequestError, "payload"):
            cafe24_dispatch_request_context(base_row, {})
        with self.assertRaisesRegex(Cafe24DispatchRequestError, "서비스 매핑"):
            cafe24_dispatch_request_context({**base_row, "supplier_external_service_id": ""}, {"service": "svc-1"})

    def test_cafe24_item_identity_and_option_helpers_are_domain_helpers(self):
        order_payload = {
            "order_id": "20260426-000001",
            "order_status": "N20",
            "memo": "관리자 메모",
        }
        item_payload = {
            "product_no": "1001",
            "variant_code": "P00000AA000A",
            "custom_product_code": "IG-FOLLOWER-100",
            "option_value": "계정: instamart_official / 팔로워 수 / 250명 (+35,500원)",
            "options": [{"name": "요청사항", "value": "천천히"}],
        }

        identity = cafe24_item_identity(order_payload, item_payload, 0)
        entries = cafe24_option_entries(order_payload, item_payload)
        pairs = cafe24_option_pairs(order_payload, item_payload)

        self.assertEqual(identity["orderId"], "20260426-000001")
        self.assertEqual(identity["orderItemCode"], "P00000AA000A")
        self.assertEqual(identity["productNo"], "1001")
        self.assertEqual(identity["customProductCode"], "IG-FOLLOWER-100")
        self.assertEqual(identity["statusCode"], "N20")
        self.assertIn({"label": "계정", "value": "instamart_official", "source": "item.option_value"}, entries)
        self.assertIn({"label": "option_value", "value": "팔로워 수", "source": "item.option_value"}, entries)
        self.assertEqual(pairs["요청사항"], "천천히")
        self.assertEqual(pairs["orderMemo"], "관리자 메모")

    def test_cafe24_mapping_gap_report_options_normalize_inputs(self):
        options = cafe24_mapping_gap_report_options(
            {
                "integrationId": " cafe24_1 ",
                "mallId": " growit ",
                "shopNo": "0",
                "includeProductDetails": "false",
                "productNos": "32, 33\n34",
                "limit": "999",
                "detailFetchLimit": "99",
                "detailApiTimeoutSeconds": "0.1",
                "detailApiMaxAttempts": "9",
                "detailApiBudgetSeconds": "999",
            }
        )

        self.assertEqual(options["integrationId"], "cafe24_1")
        self.assertEqual(options["mallId"], "growit")
        self.assertEqual(options["shopNo"], 1)
        self.assertFalse(options["includeProductDetails"])
        self.assertEqual(options["productFilter"], {"32", "33", "34"})
        self.assertEqual(options["limit"], 200)
        self.assertEqual(options["detailFetchLimit"], 20)
        self.assertEqual(options["detailApiTimeoutSeconds"], 1.0)
        self.assertEqual(options["detailApiMaxAttempts"], 3)
        self.assertEqual(options["detailApiBudgetSeconds"], 120.0)

        self.assertEqual(cafe24_mapping_gap_product_filter(["32", "", " 33 "]), {"32", "33"})
        self.assertEqual(cafe24_mapping_gap_report_options({})["detailApiMaxAttempts"], 2)
        self.assertEqual(cafe24_mapping_gap_report_options({})["detailApiBudgetSeconds"], 24.0)

        with self.assertRaisesRegex(ValueError, "조회 개수"):
            cafe24_mapping_gap_report_options({"limit": "many"})

    def test_cafe24_mapping_gap_detail_budget_caps_call_timeout(self):
        ticks = iter([10, 12, 18, 21])
        budget = Cafe24MappingGapDetailBudget(10, clock=lambda: next(ticks))

        self.assertFalse(budget.exhausted())
        self.assertEqual(budget.request_timeout(4, "상품"), 2)
        with self.assertRaisesRegex(TimeoutError, "상품 상세 전체 예산"):
            budget.request_timeout(4, "옵션")

    def test_fetch_cafe24_mapping_gap_product_details_enriches_product_payloads(self):
        class FakeClient:
            def product(self, product_no):
                return {"product": {"product_no": product_no, "product_name": f"상품 {product_no}"}}

            def product_options(self, product_no):
                return {"options": [{"option_name": "수량", "option_values": ["100명"]}]}

            def product_variants(self, product_no):
                return {"variants": [{"variant_code": "P00000BG000A", "option_value": "수량: 100명"}]}

        calls = []

        def api_call(product_no, label, client_call, request_timeout_seconds, max_attempts):
            calls.append(
                {
                    "productNo": product_no,
                    "label": label,
                    "requestTimeoutSeconds": request_timeout_seconds,
                    "maxAttempts": max_attempts,
                }
            )
            return client_call(FakeClient())

        result = fetch_cafe24_mapping_gap_product_details(
            ["32"],
            detail_fetch_limit=1,
            detail_api_timeout_seconds=4,
            detail_api_max_attempts=2,
            detail_api_budget_seconds=24,
            api_call=api_call,
        )

        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["detailTargetProductNos"], ["32"])
        self.assertEqual(result["detailAttemptedProductNos"], ["32"])
        self.assertEqual(result["detailProductNos"], ["32"])
        self.assertEqual(result["productDetails"]["32"]["productName"], "상품 32")
        self.assertEqual(result["productDetails"]["32"]["options"][0]["name"], "수량")
        self.assertEqual(result["productDetails"]["32"]["variants"][0]["variantCode"], "P00000BG000A")
        self.assertEqual([call["label"] for call in calls], ["상품", "옵션", "품목"])
        self.assertTrue(all(call["requestTimeoutSeconds"] <= 4 for call in calls))
        self.assertTrue(all(call["maxAttempts"] == 2 for call in calls))

    def test_cafe24_mapping_gap_item_payload_extracts_safe_mapping_clues(self):
        row = {
            "id": "item-1",
            "mall_id": "growit",
            "shop_no": 1,
            "cafe24_order_id": "20260512-0000017",
            "cafe24_order_item_code": "20260512-0000017-01",
            "cafe24_product_no": "32",
            "cafe24_variant_code": "P00000BG000A",
            "cafe24_custom_product_code": "P00000BG",
            "standard_status": "waiting_input",
            "payment_gate_status": "payment_confirmed",
            "error_message": "Cafe24 상품 매핑이 없습니다.",
            "last_synced_at": "2026-05-25T23:19:12+00:00",
        }
        raw_payload = {
            "order": {"order_id": "20260512-0000017", "memo": "운영 메모"},
            "item": {
                "options": [
                    {"name": "계정", "value": "instamart_official"},
                    {"name": "팔로워 수", "value": "100명 (+12,000원)"},
                ]
            },
        }

        item = cafe24_mapping_gap_item_payload(row, raw_payload)

        self.assertEqual(item["productNo"], "32")
        self.assertEqual(item["variantCode"], "P00000BG000A")
        self.assertIn("계정", item["optionLabels"])
        self.assertIn("팔로워 수", item["optionLabels"])
        self.assertEqual(item["quantityCandidates"][0]["value"], 100)
        self.assertEqual(item["quantityCandidates"][0]["label"], "팔로워 수")

    def test_cafe24_order_item_row_payload_masks_and_diagnoses_target(self):
        row = {
            "id": "item-1",
            "mall_id": "growit",
            "shop_no": 1,
            "cafe24_order_id": "20260506-0000024",
            "cafe24_order_item_code": "20260506-0000024-01",
            "cafe24_product_no": "12",
            "cafe24_variant_code": "P000000M000D",
            "cafe24_custom_product_code": "P000000M",
            "cafe24_order_date": "2026-05-06",
            "buyer_name": "Buyer",
            "buyer_email": "buyer@example.com",
            "buyer_phone": "01012345678",
            "receiver_name": "Receiver",
            "order_status_code": "N20",
            "payment_status": "paid",
            "payment_status_source": "payload",
            "payment_gate_status": "payment_confirmed",
            "payment_method": "card",
            "payment_amount": 12300,
            "payment_paid_at": "2026-05-06T12:00:00+09:00",
            "payment_reference": "tid-1",
            "payment_snapshot_json": '{"method":"card"}',
            "source_status": "validated",
            "standard_status": "ready_to_submit",
            "internal_order_id": "",
            "mapping_id": "mapping-1",
            "product_id": "product-1",
            "supplier_id": "supplier-1",
            "supplier_service_id": "service-1",
            "supplier_external_service_id": "40000",
            "internal_product_name": "인스타그램 팔로워",
            "internal_option_name": "50명",
            "normalized_fields_json": '{"targetValue":"instamart_official","orderedCount":"50"}',
            "supplier_payload_json": '{"service":"40000","link":"https://instagram.com/instamart_official","quantity":"50"}',
            "supplier_response_json": "{}",
            "raw_payload_json": '{"buyer_email":"buyer@example.com","access_token":"secret-token"}',
            "error_message": "",
            "retry_count": 0,
            "next_retry_at": "",
            "automation_last_checked_at": "",
            "automation_error_code": "",
            "supplier_order_id": "",
            "supplier_order_uuid": "",
            "last_submitted_at": "",
            "cafe24_completion_status": "pending",
            "cafe24_completion_message": "",
            "cafe24_completed_at": "",
            "cafe24_completion_attempts": 0,
            "cafe24_next_completion_retry_at": "",
            "last_synced_at": "2026-05-26T00:00:00+00:00",
            "created_at": "2026-05-26T00:00:00+00:00",
            "updated_at": "2026-05-26T00:00:00+00:00",
        }

        payload = cafe24_order_item_payload_from_row(row)

        self.assertEqual(payload["buyerEmailMasked"], "bu***@example.com")
        self.assertEqual(payload["buyerPhoneMasked"], "010-****-5678")
        self.assertEqual(payload["paymentAmountLabel"], "12,300원")
        self.assertEqual(payload["targetDiagnostics"]["status"], "normalized")
        self.assertTrue(payload["targetDiagnostics"]["normalized"])
        self.assertEqual(payload["rawPayloadPreview"]["buyer_email"], "bu***@example.com")
        self.assertNotEqual(payload["rawPayloadPreview"]["access_token"], "secret-token")
        self.assertIn("20260506-0000024", payload["searchText"])

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

    def test_order_item_list_helpers_build_filters_summary_and_pagination(self):
        options = cafe24_order_item_list_options(
            {
                "page": "0",
                "pageSize": "99",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "payment": "payment_confirmed",
                "mapping": "mapped",
                "status": "ready_to_submit",
                "q": "  ORDER-1  ",
                "integrationId": "cafe24_1",
            }
        )

        self.assertEqual(options["page"], 1)
        self.assertEqual(options["pageSize"], 50)
        self.assertEqual(options["window"], {"start": "2026-05-01 00:00:00", "end": "2026-05-31 23:59:59"})
        self.assertEqual(options["search"], "order-1")

        clauses = cafe24_order_item_filter_clauses(
            options,
            integration={"mall_id": "growit", "shop_no": 1},
        )

        self.assertIn("coi.payment_gate_status = ?", clauses["whereSql"])
        self.assertIn("coi.standard_status = ?", clauses["whereSql"])
        self.assertIn("coi.mapping_id <> ''", clauses["whereSql"])
        self.assertIn("LIKE ?", clauses["whereSql"])
        self.assertEqual(
            clauses["params"],
            [
                "2026-05-01 00:00:00",
                "2026-05-31 23:59:59",
                "growit",
                1,
                "payment_confirmed",
                "ready_to_submit",
                "%order-1%",
            ],
        )
        self.assertNotIn("payment_gate_status = ?", clauses["summaryWhereSql"])
        self.assertEqual(clauses["summaryParams"], ["2026-05-01 00:00:00", "2026-05-31 23:59:59", "growit", 1])

        self.assertEqual(
            cafe24_order_item_summary_payload(
                {
                    "total_count": 9,
                    "payment_confirmed_count": 8,
                    "unmapped_count": 7,
                    "review_required_count": 6,
                    "manual_input_required_count": 5,
                    "ready_to_submit_count": 4,
                    "failed_count": 3,
                }
            ),
            {
                "totalCount": 9,
                "paymentConfirmedCount": 8,
                "unmappedCount": 7,
                "autoDispatchExcludedCount": 0,
                "reviewRequiredCount": 6,
                "manualInputRequiredCount": 5,
                "readyToSubmitCount": 4,
                "failedCount": 3,
            },
        )
        self.assertEqual(
            cafe24_order_item_pagination_payload(page=2, page_size=5, total=6, window=options["window"]),
            {
                "page": 2,
                "pageSize": 5,
                "total": 6,
                "totalPages": 2,
                "from": "2026-05-01 00:00:00",
                "to": "2026-05-31 23:59:59",
            },
        )

    def test_refresh_token_reconnect_helpers(self):
        expired_at = (dt.datetime.now().astimezone() - dt.timedelta(minutes=1)).isoformat()
        self.assertTrue(cafe24_refresh_token_expired(expired_at))
        self.assertTrue(cafe24_refresh_error_requires_reconnect("invalid_grant: expired refresh token"))
        self.assertFalse(cafe24_refresh_error_requires_reconnect("temporary upstream timeout"))

    def test_token_and_auto_poll_helpers_are_domain_helpers(self):
        now = dt.datetime.now().astimezone()
        base_row = {
            "refresh_token": "refresh-token",
            "refresh_token_expires_at": (now + dt.timedelta(days=10)).isoformat(),
            "token_status": "connected",
            "token_refresh_lock_until": "",
            "last_sync_message": "",
            "reconnect_reason": "",
        }

        self.assertEqual(cafe24_token_status(base_row), "connected")
        self.assertEqual(cafe24_token_status_label(base_row), "정상")
        self.assertIn("자동 갱신", cafe24_token_status_message(base_row))
        self.assertEqual(
            cafe24_token_status({**base_row, "refresh_token_expires_at": (now + dt.timedelta(days=1)).isoformat()}),
            "token_expiring",
        )
        self.assertEqual(
            cafe24_token_status({**base_row, "token_status": "refreshing", "token_refresh_lock_until": (now + dt.timedelta(minutes=2)).isoformat()}),
            "refreshing",
        )
        self.assertEqual(
            cafe24_token_status({**base_row, "token_status": "failed", "last_sync_message": "last failure"}),
            "failed",
        )
        self.assertEqual(cafe24_token_status({**base_row, "refresh_token": ""}), "reconnect_required")

        self.assertEqual(
            cafe24_next_auto_poll_at({"last_auto_poll_at": "2026-05-26T08:00:00+00:00"}, interval_minutes=10),
            "2026-05-26T08:10:00+00:00",
        )
        self.assertTrue(cafe24_auto_poll_due({"last_auto_poll_at": ""}))
        self.assertTrue(cafe24_auto_poll_due({"last_auto_poll_at": now.isoformat()}, force=True))
        self.assertTrue(cafe24_auto_poll_due({"last_auto_poll_at": (now - dt.timedelta(minutes=20)).isoformat()}, interval_minutes=10))
        self.assertFalse(cafe24_auto_poll_due({"last_auto_poll_at": (now - dt.timedelta(minutes=1)).isoformat()}, interval_minutes=10))

    def test_integration_row_payload_keeps_admin_token_shape(self):
        row = {
            "id": "cafe24_1",
            "mall_id": "growit",
            "shop_no": 1,
            "scopes_json": '["mall.read_order"]',
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "expires_at": "2026-05-26T09:00:00+00:00",
            "refresh_token_expires_at": (dt.datetime.now().astimezone() + dt.timedelta(days=10)).isoformat(),
            "last_poll_at": "2026-05-26T08:00:00+00:00",
            "poll_cursor": "",
            "auto_submit": 1,
            "completion_policy": "memo_only",
            "token_status": "connected",
            "token_last_checked_at": "2026-05-26T08:01:00+00:00",
            "token_last_refreshed_at": "2026-05-26T08:02:00+00:00",
            "token_refresh_lock_until": "",
            "reconnect_required_at": "",
            "reconnect_reason": "",
            "cafe24_poll_lock_until": "",
            "last_auto_poll_at": "2026-05-26T08:00:00+00:00",
            "last_auto_poll_status": "success",
            "last_auto_poll_message": "ok",
            "is_active": 1,
            "last_sync_status": "success",
            "last_sync_message": "ok",
            "created_at": "2026-05-26T07:00:00+00:00",
            "updated_at": "2026-05-26T08:03:00+00:00",
        }

        payload = cafe24_integration_payload_from_row(row, auto_poll_interval_minutes=5)
        self.assertEqual(payload["mallId"], "growit")
        self.assertEqual(payload["scopes"], ["mall.read_order"])
        self.assertEqual(payload["tokenStatus"], "connected")
        self.assertEqual(payload["tokenStatusLabel"], "정상")
        self.assertTrue(payload["autoSubmit"])
        self.assertEqual(payload["nextAutoPollAt"], "2026-05-26T08:05:00+00:00")
        self.assertTrue(payload["accessTokenMasked"].endswith("cret"))
        self.assertTrue(payload["refreshTokenMasked"].endswith("cret"))

    def test_access_token_error_detects_server_expired_access_token(self):
        self.assertTrue(
            cafe24_access_token_error(
                'Cafe24 API 오류 401: {"error":{"code":401,"message":"access_token time expired. (invalid_token)"}}'
            )
        )
        self.assertTrue(cafe24_access_token_error("401 Unauthorized: invalid token"))
        self.assertFalse(cafe24_access_token_error("403 scope permission denied"))
        self.assertFalse(cafe24_access_token_error("temporary upstream timeout"))

    def test_poll_datetime_window_parses_bounds_and_cursor_overlap(self):
        explicit = cafe24_poll_datetime_window(start_raw="2026-05-01", end_raw="2026-05-02")
        cursor = cafe24_poll_datetime_window(
            end_raw="2026-05-03 10:00:00",
            last_poll_at="2026-05-03T09:30:00+09:00",
            use_cursor=True,
            overlap_minutes=20,
        )

        self.assertEqual(explicit["start"], "2026-05-01 00:00:00")
        self.assertEqual(explicit["end"], "2026-05-02 23:59:59")
        self.assertEqual(cursor["start"], "2026-05-03 09:10:00")
        self.assertEqual(cursor["end"], "2026-05-03 10:00:00")
        with self.assertRaises(Cafe24PollWindowError):
            cafe24_poll_datetime_window(start_raw="not-a-date")
        with self.assertRaises(Cafe24PollWindowError):
            cafe24_poll_datetime_window(start_raw="2026-05-03", end_raw="2026-05-02")

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

    def test_panel_wrappers_raise_panel_errors_for_cron_and_admin_handlers(self):
        selector = cafe24_order_item_selector_for_panel(
            {"mallId": "growit", "shopNo": "1", "orderId": "20260506-0000024", "orderItemCode": "20260506-0000024-01"},
            default_shop_no=1,
        )

        self.assertEqual(selector["mallId"], "growit")
        self.assertEqual(selector["orderItemCode"], "20260506-0000024-01")
        self.assertEqual(cafe24_expected_quantity_from_payload_for_panel({"expectedQuantity": "50"}), 50)
        with self.assertRaises(PanelError) as selector_error:
            cafe24_order_item_selector_for_panel({"mallId": "growit"}, required_message="식별값 필요")
        self.assertEqual(selector_error.exception.status, 400)
        self.assertIn("식별값 필요", str(selector_error.exception))
        with self.assertRaises(PanelError) as quantity_error:
            cafe24_expected_quantity_from_payload_for_panel({"expectedQuantity": "many"})
        self.assertEqual(quantity_error.exception.status, 400)

    def test_panel_order_item_id_helper_resolves_identity_or_preserves_item_id(self):
        class FakeResult:
            def __init__(self, row):
                self.row = row

            def fetchone(self):
                return self.row

        class FakeConn:
            def __init__(self, row):
                self.row = row
                self.calls = []

            def execute(self, query, params=()):
                self.calls.append((query, params))
                return FakeResult(self.row)

        direct_conn = FakeConn({"id": "should-not-read"})
        self.assertEqual(cafe24_order_item_id_for_panel(direct_conn, {"itemId": "item-direct"}), "item-direct")
        self.assertEqual(direct_conn.calls, [])

        lookup_conn = FakeConn({"id": "item-lookup"})
        selector = {
            "itemId": "",
            "mallId": "growit",
            "shopNo": 1,
            "orderId": "20260512-0000017",
            "orderItemCode": "20260512-0000017-01",
        }
        self.assertEqual(cafe24_order_item_id_for_panel(lookup_conn, selector), "item-lookup")
        self.assertEqual(lookup_conn.calls[0][1], ("growit", 1, "20260512-0000017", "20260512-0000017-01"))
        with self.assertRaises(PanelError) as missing_error:
            cafe24_order_item_id_for_panel(FakeConn(None), selector)
        self.assertEqual(missing_error.exception.status, 404)

    def test_panel_direct_field_validation_checks_quantity_target_and_bounds(self):
        def looks_like_url(value):
            return str(value).startswith("https://") or str(value).startswith("bad.")

        def normalize_url(value):
            return str(value) if str(value).startswith("https://") else None

        mapping = {"supplier_min_amount": 10, "supplier_max_amount": 100}
        validate_cafe24_direct_fields_for_panel(
            {"orderedCount": "50", "targetValue": "instamart_official"},
            mapping,
            looks_like_url=looks_like_url,
            normalize_url=normalize_url,
        )
        validate_cafe24_direct_fields_for_panel(
            {"orderedCount": "10", "comments": "one\\ntwo"},
            mapping,
            looks_like_url=looks_like_url,
            normalize_url=normalize_url,
        )
        with self.assertRaisesRegex(PanelError, "수량을 확인"):
            validate_cafe24_direct_fields_for_panel({}, mapping, looks_like_url=looks_like_url, normalize_url=normalize_url)
        with self.assertRaisesRegex(PanelError, "최소 수량"):
            validate_cafe24_direct_fields_for_panel(
                {"orderedCount": "9", "targetValue": "instamart"},
                mapping,
                looks_like_url=looks_like_url,
                normalize_url=normalize_url,
            )
        with self.assertRaisesRegex(PanelError, "필요한 링크"):
            validate_cafe24_direct_fields_for_panel(
                {"orderedCount": "50"},
                mapping,
                looks_like_url=looks_like_url,
                normalize_url=normalize_url,
            )
        with self.assertRaisesRegex(PanelError, "URL 형식"):
            validate_cafe24_direct_fields_for_panel(
                {"orderedCount": "50", "targetUrl": "bad.example"},
                mapping,
                looks_like_url=looks_like_url,
                normalize_url=normalize_url,
            )

    def test_supplier_target_helpers_build_account_urls_and_supported_hosts(self):
        self.assertIn("instagram", ACCOUNT_STYLE_PLATFORMS)
        self.assertEqual(preview_platform_hint("인스타그램 팔로워", ""), "instagram")
        self.assertEqual(preview_platform_hint("creator", "youtube"), "youtube")
        self.assertEqual(preview_platform_hint("블로그 유입", "nportal"), "nportal")
        self.assertEqual(preview_platform_hint("custom", "unknown-platform"), "unknown-platform")
        self.assertEqual(account_preview_url("@instamart.official", "instagram"), "https://www.instagram.com/instamart.official/")
        self.assertEqual(account_preview_url("codex preview", "instagram"), "https://www.instagram.com/codexpreview/")
        self.assertEqual(account_preview_url("creator", "youtube"), "https://www.youtube.com/@creator")
        self.assertIsNone(account_preview_url("bad/path", "instagram"))
        self.assertIn("www.instagram.com", supplier_supported_hosts("instagram"))
        self.assertIn("youtu.be", supplier_supported_hosts("youtube"))
        self.assertEqual(supplier_supported_hosts("unknown"), set())

    def test_supplier_target_helpers_match_platform_urls_and_messages(self):
        def normalize(value):
            text = str(value or "").strip()
            if not text:
                return None
            return text if text.startswith(("http://", "https://")) else f"https://{text}"

        def looks_like(value):
            return "." in str(value or "")

        self.assertTrue(
            platform_target_url_matches(
                "instagram",
                "https://www.instagram.com/instamart.official/",
                normalize_url=normalize,
                looks_like_url=looks_like,
            )
        )
        self.assertFalse(
            platform_target_url_matches(
                "instagram",
                "https://www.instagram.com/",
                normalize_url=normalize,
                looks_like_url=looks_like,
            )
        )
        self.assertTrue(
            platform_target_url_matches(
                "youtube",
                "https://youtu.be/video-id",
                normalize_url=normalize,
                looks_like_url=looks_like,
            )
        )
        self.assertTrue(
            platform_target_url_matches(
                "nportal",
                "https://blog.naver.com/instamart",
                normalize_url=normalize,
                looks_like_url=looks_like,
            )
        )
        self.assertIn("인스타그램", platform_target_error_message("instagram"))
        self.assertIn("해당 플랫폼", platform_target_error_message("unknown"))

    def test_supplier_panel_target_helpers_normalize_and_validate_links(self):
        def normalize(value):
            text = str(value or "").strip()
            if not text:
                return None
            return text if text.startswith(("http://", "https://")) else f"https://{text}"

        def looks_like(value):
            return "." in str(value or "")

        self.assertEqual(
            supplier_panel_target_link(
                "instamart.official",
                "instagram",
                normalize_url=normalize,
                looks_like_url=looks_like,
            ),
            "https://www.instagram.com/instamart.official/",
        )
        self.assertEqual(
            supplier_panel_target_link(
                "https://instagram.com/instamart.official/",
                "instagram",
                normalize_url=normalize,
                looks_like_url=looks_like,
            ),
            "https://instagram.com/instamart.official/",
        )
        self.assertEqual(
            supplier_panel_target_link(
                "https://not-instagram.example",
                "instagram",
                normalize_url=normalize,
                looks_like_url=looks_like,
            ),
            "https://www.instagram.com/not-instagram.example/",
        )
        self.assertEqual(
            supplier_panel_target_link(
                "custom.example/path",
                "unknown",
                normalize_url=normalize,
                looks_like_url=looks_like,
            ),
            "https://custom.example/path",
        )
        validate_supplier_panel_target_link(
            "https://www.instagram.com/instamart.official/",
            "instagram",
            normalize_url=normalize,
        )
        with self.assertRaises(SupplierTargetError):
            validate_supplier_panel_target_link(
                "https://example.com/instamart.official",
                "instagram",
                normalize_url=normalize,
            )

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

    def test_manual_input_helper_validates_fields_and_operational_guards(self):
        fields = cafe24_manual_order_fields(
            {
                "targetValue": "instamart_official",
                "orderedCount": "1,500",
                "requestMemo": "manual fix",
            }
        )

        self.assertEqual(fields["orderedCount"], "1500")
        self.assertEqual(fields["targetValue"], "instamart_official")
        self.assertEqual(fields["requestMemo"], "manual fix")
        self.assertEqual(cafe24_manual_expected_quantity({"targetValue": "instamart_official", "orderedCount": "1,500"}), 1500)
        self.assertEqual(cafe24_manual_expected_quantity({"targetValue": "instamart_official", "orderedCount": "1,500"}, 50), 50)

        cafe24_validate_manual_input_order_item(
            {"payment_gate_status": "payment_confirmed", "standard_status": "waiting_input", "supplier_order_uuid": ""}
        )
        with self.assertRaises(Cafe24ManualInputError) as unpaid_error:
            cafe24_validate_manual_input_order_item(
                {"payment_gate_status": "payment_pending", "standard_status": "waiting_input", "supplier_order_uuid": ""}
            )
        self.assertEqual(unpaid_error.exception.status, 400)
        with self.assertRaises(Cafe24ManualInputError) as progress_error:
            cafe24_validate_manual_input_order_item(
                {"payment_gate_status": "payment_confirmed", "standard_status": "supplier_progress", "supplier_order_uuid": "734"}
            )
        self.assertEqual(progress_error.exception.status, 409)

        cafe24_validate_manual_input_supplier({"is_active": 1}, {"is_active": 1})
        with self.assertRaises(Cafe24ManualInputError) as supplier_error:
            cafe24_validate_manual_input_supplier({"is_active": 0}, {"is_active": 1})
        self.assertEqual(supplier_error.exception.status, 400)

    def test_manual_input_request_normalizes_selector_supplier_and_fields(self):
        request = cafe24_manual_input_request(
            {
                "mallId": "growit",
                "shopNo": "1",
                "orderId": "20260512-0000017",
                "orderItemCode": "20260512-0000017-01",
                "supplierId": "sup_1",
                "supplierServiceId": "svc_1",
                "targetValue": "instamart_official",
                "orderedCount": "50",
            }
        )

        self.assertEqual(request["selector"]["mallId"], "growit")
        self.assertEqual(request["selector"]["shopNo"], 1)
        self.assertEqual(request["selector"]["orderId"], "20260512-0000017")
        self.assertEqual(request["selector"]["orderItemCode"], "20260512-0000017-01")
        self.assertEqual(request["supplierId"], "sup_1")
        self.assertEqual(request["supplierServiceId"], "svc_1")
        self.assertEqual(request["fields"]["orderedCount"], "50")
        self.assertEqual(request["fields"]["targetValue"], "instamart_official")

        with self.assertRaisesRegex(Cafe24ManualInputError, "공급사 서비스를 선택"):
            cafe24_manual_input_request(
                {
                    "itemId": "cafe24_item_1",
                    "supplierId": "sup_1",
                    "targetValue": "instamart_official",
                    "orderedCount": "50",
                }
            )

    def test_manual_input_helper_builds_product_and_supplier_mapping_payloads(self):
        product_payload = cafe24_manual_product_payload(
            {"product_code": "IG-FOLLOW", "name": "인스타 팔로워", "platform_slug": "instagram"}
        )
        supplier_mapping = cafe24_manual_supplier_mapping(
            {"mapping_id": "", "product_id": "product_1"},
            {
                "name": "mkt24",
                "api_url": "https://api.mkt24.co.kr/v3/panel",
                "integration_type": "mkt24",
                "api_key": "encrypted-key",
                "bearer_token": "",
            },
            {
                "external_service_id": "40000",
                "name": "인스타그램 실제 한국인 팔로워",
                "raw_json": '{"service":"40000"}',
                "min_amount": 10,
                "max_amount": 1000,
            },
            supplier_id="supplier_1",
            supplier_service_id="service_1",
        )

        self.assertEqual(product_payload["product_code"], "IG-FOLLOW")
        self.assertEqual(product_payload["platform_slug"], "instagram")
        self.assertEqual(product_payload["price_strategy"], "unit")
        self.assertEqual(supplier_mapping["id"], "manual")
        self.assertEqual(supplier_mapping["supplier_id"], "supplier_1")
        self.assertEqual(supplier_mapping["supplier_service_id"], "service_1")
        self.assertEqual(supplier_mapping["supplier_external_service_id"], "40000")
        self.assertEqual(supplier_mapping["integration_type"], "mkt24")
        self.assertEqual(supplier_mapping["supplier_min_amount"], 10)
        self.assertEqual(supplier_mapping["supplier_max_amount"], 1000)

    def test_manual_input_plan_payload_delegates_validation_and_supplier_payload_build(self):
        calls = []

        def validate_direct_fields(fields, mapping):
            calls.append(("validate", dict(fields), dict(mapping)))

        def build_supplier_order_payload(product, fields, mapping):
            calls.append(("build", dict(product), dict(fields), dict(mapping)))
            return {
                "service": mapping["supplier_external_service_id"],
                "link": fields["targetValue"],
                "quantity": fields["orderedCount"],
            }

        plan = build_cafe24_manual_input_plan_payload(
            item_id="cafe24_item_1",
            item_row={"mapping_id": "", "product_id": "product_1"},
            supplier_row={
                "name": "mkt24",
                "api_url": "https://api.mkt24.co.kr/v3/panel",
                "integration_type": "mkt24",
                "api_key": "encrypted-key",
                "bearer_token": "",
            },
            service_row={
                "external_service_id": "40000",
                "name": "인스타그램 실제 한국인 팔로워",
                "raw_json": '{"service":"40000"}',
                "min_amount": 10,
                "max_amount": 1000,
            },
            supplier_id="supplier_1",
            supplier_service_id="service_1",
            fields={"targetValue": "instamart_official", "orderedCount": "50"},
            product_row={"product_code": "IG-FOLLOW", "name": "인스타 팔로워", "platform_slug": "instagram"},
            validate_direct_fields=validate_direct_fields,
            build_supplier_order_payload=build_supplier_order_payload,
        )

        self.assertEqual(plan["itemId"], "cafe24_item_1")
        self.assertEqual(plan["supplierExternalServiceId"], "40000")
        self.assertEqual(plan["supplierPayload"]["service"], "40000")
        self.assertEqual(plan["supplierPayload"]["quantity"], "50")
        self.assertEqual([call[0] for call in calls], ["validate", "build"])
        self.assertEqual(calls[0][2]["supplier_service_id"], "service_1")
        self.assertEqual(calls[1][1]["product_code"], "IG-FOLLOW")


if __name__ == "__main__":
    unittest.main()
