import datetime as dt
import os
import re
import unittest
from unittest.mock import patch

import bootstrap
from backend.orders import automation_paused, automation_retry_at, order_submission_payload, parse_iso_datetime
from backend.wallet import (
    admin_charge_order_payload,
    charge_amount_breakdown,
    charge_order_filter_clause,
    charge_order_payload,
    normalize_charge_payment_channel,
    payment_method_detail_label,
    resolve_charge_expiry,
    wallet_balances_payload,
    wallet_ledger_entry_payload,
    wallet_ledger_filter_clause,
)
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

    def test_order_submission_payload_keeps_response_shape(self):
        payload = order_submission_payload(
            {
                "id": "order-1",
                "order_number": "SMM-20260526-ABCDEF",
                "order_channel": "cafe24",
                "external_order_id": "20260506-0000024",
                "external_order_item_id": "20260506-0000024-01",
                "dispatch_status": "ready",
                "total_price": 79000,
            },
            available_balance=121000,
            duplicate=True,
        )

        self.assertEqual(payload["orderId"], "order-1")
        self.assertEqual(payload["orderChannel"], "cafe24")
        self.assertEqual(payload["externalOrderId"], "20260506-0000024")
        self.assertEqual(payload["dispatchStatus"], "ready")
        self.assertEqual(payload["totalPriceLabel"], "79,000원")
        self.assertEqual(payload["balanceAfterLabel"], "121,000원")
        self.assertTrue(payload["duplicate"])

    def test_order_automation_helpers_live_in_order_domain(self):
        base_time = dt.datetime(2026, 5, 27, 10, 0, tzinfo=dt.timezone.utc)

        self.assertEqual(parse_iso_datetime("2026-05-27T10:00:00+00:00"), base_time)
        self.assertIsNone(parse_iso_datetime("not-a-date"))
        self.assertFalse(automation_paused({}))
        self.assertTrue(automation_paused({"SMM_PANEL_AUTOMATION_PAUSED": "yes"}))
        self.assertEqual(automation_retry_at(1, now=base_time), "2026-05-27T10:10:00+00:00")
        self.assertEqual(automation_retry_at(2, now=base_time), "2026-05-27T10:30:00+00:00")
        self.assertEqual(automation_retry_at(99, now=base_time), "2026-05-27T12:00:00+00:00")

    def test_core_automation_helpers_delegate_to_order_domain(self):
        import core

        with patch.dict(os.environ, {"SMM_PANEL_AUTOMATION_PAUSED": "1"}, clear=False):
            self.assertTrue(core.automation_paused())
        self.assertIsNone(core.parse_iso_datetime(""))
        self.assertRegex(core.automation_retry_at(1), r"^\d{4}-\d{2}-\d{2}T")

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

    def test_payment_method_detail_label_uses_wallet_domain_helper(self):
        self.assertEqual(payment_method_detail_label("card", "kakao_pay"), "카카오페이")
        self.assertEqual(payment_method_detail_label("card", "custom_pg"), "custom_pg")
        self.assertEqual(payment_method_detail_label("bank_transfer", ""), "계좌입금")
        self.assertEqual(payment_method_detail_label("virtual_account", ""), "가상계좌")

    def test_resolve_charge_expiry_uses_wallet_domain_helper(self):
        now = dt.datetime(2026, 5, 26, 9, 30, tzinfo=dt.timezone.utc)

        self.assertEqual(resolve_charge_expiry("card", now=now), "2026-05-26T09:45:00+00:00")
        self.assertEqual(resolve_charge_expiry("easy_pay", now=now), "2026-05-26T09:45:00+00:00")
        self.assertEqual(resolve_charge_expiry("bank_transfer", now=now), "2026-05-27T09:30:00+00:00")

    def test_wallet_payload_helpers_keep_public_shapes(self):
        self.assertEqual(
            wallet_balances_payload(1000, 500),
            {
                "availableBalance": 1000,
                "availableBalanceLabel": "1,000원",
                "pendingBalance": 500,
                "pendingBalanceLabel": "500원",
                "totalBalance": 1500,
                "totalBalanceLabel": "1,500원",
            },
        )
        charge_payload = charge_order_payload(
            {
                "id": "charge-1",
                "order_code": "CHG-20260526-ABCDEF",
                "amount": 50000,
                "vat_amount": 5000,
                "total_amount": 55000,
                "payment_channel": "bank_transfer",
                "payment_method_detail": "",
                "status": "awaiting_deposit",
                "depositor_name": "홍길동",
                "receipt_type": "cash_receipt",
                "receipt_payload_json": '{"phoneNumber":"01012345678"}',
                "reference": "REF-1",
                "pg_provider": "",
                "pg_order_id": "",
                "pg_payment_key": "",
                "failure_reason": "",
                "payment_payload_json": "{}",
                "bank_account_snapshot_json": '{"bankName":"국민은행"}',
                "expires_at": "2026-05-27T00:00:00+09:00",
                "confirmed_at": "",
                "paid_at": "",
                "created_at": "2026-05-26T00:00:00+09:00",
                "updated_at": "2026-05-26T00:00:00+09:00",
            },
            created_label="방금 전",
        )

        self.assertEqual(charge_payload["totalAmountLabel"], "55,000원")
        self.assertEqual(charge_payload["paymentChannelLabel"], "계좌입금")
        self.assertEqual(charge_payload["statusLabel"], "입금 대기")
        self.assertEqual(charge_payload["receiptPayload"]["phoneNumber"], "01012345678")
        self.assertEqual(charge_payload["bankAccount"]["bankName"], "국민은행")
        self.assertEqual(charge_payload["createdLabel"], "방금 전")

    def test_admin_charge_order_payload_adds_customer_search_fields(self):
        payload = admin_charge_order_payload(
            {
                "id": "charge-1",
                "user_id": "user-1",
                "customer_name": "홍길동",
                "customer_email": "hong@example.com",
                "order_code": "CHG-20260526-ABCDEF",
                "amount": 50000,
                "vat_amount": 5000,
                "total_amount": 55000,
                "payment_channel": "bank_transfer",
                "payment_method_detail": "",
                "status": "awaiting_deposit",
                "depositor_name": "홍길동",
                "receipt_type": "none",
                "receipt_payload_json": "{}",
                "reference": "REF-1",
                "pg_provider": "",
                "pg_order_id": "",
                "pg_payment_key": "",
                "failure_reason": "",
                "payment_payload_json": "{}",
                "bank_account_snapshot_json": "{}",
                "expires_at": "",
                "confirmed_at": "",
                "paid_at": "",
                "created_at": "2026-05-26T00:00:00+09:00",
                "updated_at": "2026-05-26T00:00:00+09:00",
            },
            created_label="오늘",
            customer_email_masked="h***@example.com",
        )

        self.assertEqual(payload["customerId"], "user-1")
        self.assertEqual(payload["customerName"], "홍길동")
        self.assertEqual(payload["customerEmailMasked"], "h***@example.com")
        self.assertIn("chg-20260526-abcdef", payload["searchText"])
        self.assertIn("hong@example.com", payload["searchText"])
        self.assertIn("계좌입금", payload["searchText"])

    def test_wallet_ledger_helpers_build_filters_and_entries(self):
        conditions, params, safe_limit = wallet_ledger_filter_clause(
            {
                "entryType": "charge",
                "status": "paid",
                "paymentChannel": "card",
                "createdFrom": "2026-05-01",
                "createdTo": "2026-05-31",
            },
            user_id="user-1",
            limit=200,
        )

        self.assertEqual(safe_limit, 100)
        self.assertIn("wl.entry_type = ?", conditions)
        self.assertEqual(params, ["user-1", "charge", "paid", "card", "2026-05-01", "2026-05-31"])

        entry = wallet_ledger_entry_payload(
            {
                "id": "ledger-1",
                "entry_type": "charge",
                "amount": 55000,
                "balance_after": 155000,
                "memo": "충전 완료",
                "related_charge_order_id": "charge-1",
                "related_order_id": "",
                "order_code": "CHG-20260526-ABCDEF",
                "payment_channel": "card",
                "payment_method_detail": "kakao_pay",
                "receipt_type": "none",
                "charge_status": "paid",
                "charge_reference": "REF-1",
                "charge_failure_reason": "",
                "created_at": "2026-05-26T00:00:00+09:00",
            },
            payment_method_detail_label="카카오페이",
            created_label="오늘",
        )

        self.assertEqual(entry["amountLabel"], "+55,000원")
        self.assertEqual(entry["balanceAfterLabel"], "155,000원")
        self.assertEqual(entry["paymentMethodDetailLabel"], "카카오페이")
        self.assertEqual(entry["statusLabel"], "결제 완료")
        self.assertEqual(entry["createdLabel"], "오늘")

    def test_charge_order_filter_clause_matches_list_filters(self):
        conditions, params, safe_limit = charge_order_filter_clause(
            {
                "status": "paid",
                "paymentChannel": "bank_transfer",
                "createdFrom": "2026-05-01",
                "createdTo": "2026-05-31",
            },
            user_id="user-1",
            limit=0,
        )

        self.assertEqual(safe_limit, 50)
        self.assertEqual(
            conditions,
            [
                "user_id = ?",
                "status = ?",
                "payment_channel = ?",
                "created_at >= ?",
                "created_at <= ?",
            ],
        )
        self.assertEqual(params, ["user-1", "paid", "bank_transfer", "2026-05-01", "2026-05-31"])

    def test_charge_order_filter_clause_ignores_all_filters_and_clamps_limit(self):
        conditions, params, safe_limit = charge_order_filter_clause(
            {
                "status": "all",
                "paymentChannel": "all",
            },
            user_id="user-1",
            limit=500,
        )

        self.assertEqual(conditions, ["user_id = ?"])
        self.assertEqual(params, ["user-1"])
        self.assertEqual(safe_limit, 100)


if __name__ == "__main__":
    unittest.main()
