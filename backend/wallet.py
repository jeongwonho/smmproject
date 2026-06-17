from __future__ import annotations

import datetime as dt
import json
import secrets
from typing import Any, Dict, List, Tuple


class ChargeOrderRequestError(ValueError):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def generate_charge_order_code() -> str:
    return f"CHG-{dt.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def charge_amount_breakdown(amount: Any) -> Dict[str, int]:
    normalized_amount = int(amount or 0)
    vat_amount = normalized_amount // 10
    total_amount = normalized_amount + vat_amount
    return {
        "amount": normalized_amount,
        "vatAmount": vat_amount,
        "totalAmount": total_amount,
    }


def resolve_charge_expiry(payment_channel: Any, *, now: dt.datetime | None = None) -> str:
    base_time = now if now is not None and now.tzinfo is not None else (now or dt.datetime.now()).astimezone()
    channel = str(payment_channel or "").strip().lower()
    if channel in {"card", "easy_pay"}:
        return (base_time + dt.timedelta(minutes=15)).isoformat(timespec="seconds")
    return (base_time + dt.timedelta(hours=24)).isoformat(timespec="seconds")


def normalize_charge_payment_channel(raw_value: Any) -> str:
    value = str(raw_value or "").strip().lower()
    aliases = {
        "card_easy_pay": "card",
        "card/easy_pay": "card",
        "simple": "card",
        "wire": "bank_transfer",
        "deposit": "bank_transfer",
    }
    value = aliases.get(value, value)
    if value not in {"card", "easy_pay", "bank_transfer", "virtual_account"}:
        raise ValueError("지원하지 않는 결제 방식입니다.")
    return value


def normalize_charge_order_request(
    payload: Dict[str, Any],
    *,
    card_payment_enabled: bool,
    bank_transfer_enabled: bool,
) -> Dict[str, Any]:
    try:
        amount = int(float(payload.get("amount") or 0) or 0)
    except (TypeError, ValueError) as exc:
        raise ChargeOrderRequestError("충전 금액은 숫자로 입력해 주세요.") from exc
    try:
        payment_channel = normalize_charge_payment_channel(payload.get("paymentChannel") or "")
    except ValueError as exc:
        raise ChargeOrderRequestError(str(exc)) from exc
    payment_method_detail = str(payload.get("paymentMethodDetail") or "").strip().lower()
    depositor_name = str(payload.get("depositorName") or "").strip()
    receipt_type = str(payload.get("receiptType") or "none").strip().lower()
    receipt_payload = payload.get("receiptPayload") if isinstance(payload.get("receiptPayload"), dict) else {}

    if amount < 5_000:
        raise ChargeOrderRequestError("최소 충전 금액은 5,000원입니다.")
    if amount > 5_000_000:
        raise ChargeOrderRequestError("한 번에 충전 가능한 금액은 500만원입니다.")
    if amount % 100 != 0:
        raise ChargeOrderRequestError("충전 금액은 100원 단위로 입력해 주세요.")
    if payment_channel in {"card", "easy_pay"} and not card_payment_enabled:
        raise ChargeOrderRequestError(
            "현재 선택할 수 없는 결제수단입니다. 계좌입금을 선택하거나 고객센터로 문의해 주세요.",
            status=503,
        )
    if payment_channel == "bank_transfer" and not bank_transfer_enabled:
        raise ChargeOrderRequestError("계좌입금 설정이 완료되지 않았습니다. 운영팀에 문의해 주세요.", status=503)
    if receipt_type not in {"none", "cash_receipt", "tax_invoice"}:
        raise ChargeOrderRequestError("지원하지 않는 증빙 신청 유형입니다.")
    if payment_channel == "bank_transfer" and not depositor_name:
        raise ChargeOrderRequestError("입금자명을 입력해 주세요.")
    if receipt_type == "cash_receipt" and not (
        str(receipt_payload.get("phoneNumber") or "").strip() or str(receipt_payload.get("businessNumber") or "").strip()
    ):
        raise ChargeOrderRequestError("현금영수증 신청 정보를 입력해 주세요.")
    if receipt_type == "tax_invoice":
        required_fields = ["businessName", "businessNumber", "recipientEmail"]
        if any(not str(receipt_payload.get(field) or "").strip() for field in required_fields):
            raise ChargeOrderRequestError("세금계산서 신청 정보를 모두 입력해 주세요.")

    payment_status = "awaiting_payment" if payment_channel in {"card", "easy_pay"} else "awaiting_deposit"
    return {
        "amount": amount,
        "breakdown": charge_amount_breakdown(amount),
        "paymentChannel": payment_channel,
        "paymentMethodDetail": payment_method_detail,
        "depositorName": depositor_name,
        "receiptType": receipt_type,
        "receiptPayload": receipt_payload,
        "status": payment_status,
        "requiresBankSnapshot": payment_channel == "bank_transfer",
    }


def balance_transaction_kind_to_ledger_entry_type(kind: str) -> str:
    labels = {
        "charge": "charge",
        "order": "order_debit",
        "admin_adjust": "admin_adjustment",
    }
    key = str(kind or "").strip().lower()
    return labels.get(key, key or "admin_adjustment")


def money_label(value: Any) -> str:
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,}원"


def payment_method_label(method: Any) -> str:
    labels = {
        "charge": "충전",
        "order_debit": "주문 차감",
        "manual_balance": "운영 수동 충전",
        "admin_manual": "운영 수동 충전",
        "bank_transfer": "계좌입금",
        "card": "카드 결제",
        "card_easy_pay": "카드/간편결제",
        "easy_pay": "간편결제",
        "virtual_account": "가상계좌",
        "admin_adjustment": "관리자 조정",
    }
    key = str(method or "").strip().lower()
    return labels.get(key, key or "미정")


def payment_method_detail_label(payment_channel: Any, method_detail: Any) -> str:
    channel = str(payment_channel or "").strip().lower()
    detail = str(method_detail or "").strip()
    if channel == "card" and detail:
        labels = {
            "general_card": "일반 카드",
            "kakao_pay": "카카오페이",
            "naver_pay": "네이버페이",
            "tosspay": "토스페이",
            "payco": "PAYCO",
        }
        return labels.get(detail, detail)
    if channel == "bank_transfer":
        return "계좌입금"
    return payment_method_label(channel)


def payment_status_label(status: Any) -> str:
    labels = {
        "created": "생성됨",
        "awaiting_payment": "결제 대기",
        "awaiting_deposit": "입금 대기",
        "pending": "확인 대기",
        "processing": "처리 중",
        "paid": "결제 완료",
        "completed": "완료",
        "failed": "실패",
        "expired": "만료",
        "cancelled": "취소",
        "refund_requested": "환불 요청",
        "refunded": "환불 완료",
    }
    key = str(status or "").strip().lower()
    return labels.get(key, key or "미정")


def receipt_type_label(receipt_type: Any) -> str:
    labels = {
        "none": "미신청",
        "cash_receipt": "현금영수증",
        "tax_invoice": "세금계산서",
    }
    key = str(receipt_type or "").strip().lower()
    return labels.get(key, key or "미정")


def _wallet_parse_json(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return fallback


def wallet_balances_payload(available_balance: Any, pending_balance: Any) -> Dict[str, Any]:
    available = int(available_balance or 0)
    pending = int(pending_balance or 0)
    total = available + pending
    return {
        "availableBalance": available,
        "availableBalanceLabel": money_label(available),
        "pendingBalance": pending,
        "pendingBalanceLabel": money_label(pending),
        "totalBalance": total,
        "totalBalanceLabel": money_label(total),
    }


def charge_order_payload(row: Dict[str, Any], *, created_label: str = "") -> Dict[str, Any]:
    row_map = dict(row)
    amount = int(row_map.get("amount") or 0)
    vat_amount = int(row_map.get("vat_amount") or 0)
    total_amount = int(row_map.get("total_amount") or 0)
    payment_channel = row_map.get("payment_channel") or ""
    status = row_map.get("status") or ""
    receipt_type = row_map.get("receipt_type") or "none"
    return {
        "id": row_map["id"],
        "orderCode": row_map["order_code"],
        "amount": amount,
        "amountLabel": money_label(amount),
        "vatAmount": vat_amount,
        "vatAmountLabel": money_label(vat_amount),
        "totalAmount": total_amount,
        "totalAmountLabel": money_label(total_amount),
        "paymentChannel": payment_channel,
        "paymentChannelLabel": payment_method_label(payment_channel),
        "paymentMethodDetail": row_map.get("payment_method_detail") or "",
        "status": status,
        "statusLabel": payment_status_label(status),
        "depositorName": row_map.get("depositor_name") or "",
        "receiptType": receipt_type,
        "receiptTypeLabel": receipt_type_label(receipt_type),
        "receiptPayload": _wallet_parse_json(row_map.get("receipt_payload_json"), {}),
        "reference": row_map.get("reference") or "",
        "pgProvider": row_map.get("pg_provider") or "",
        "pgOrderId": row_map.get("pg_order_id", ""),
        "pgPaymentKey": row_map.get("pg_payment_key", ""),
        "failureReason": row_map.get("failure_reason") or "",
        "paymentPayload": _wallet_parse_json(row_map.get("payment_payload_json"), {}),
        "bankAccount": _wallet_parse_json(row_map.get("bank_account_snapshot_json"), {}),
        "expiresAt": row_map.get("expires_at") or "",
        "confirmedAt": row_map.get("confirmed_at", ""),
        "paidAt": row_map.get("paid_at") or "",
        "createdAt": row_map.get("created_at") or "",
        "updatedAt": row_map.get("updated_at") or "",
        "createdLabel": created_label,
    }


def admin_charge_order_payload(
    row: Dict[str, Any],
    *,
    created_label: str = "",
    customer_email_masked: str = "",
) -> Dict[str, Any]:
    row_map = dict(row)
    payload = charge_order_payload(row_map, created_label=created_label)
    customer_name = str(row_map.get("customer_name") or "")
    customer_email = str(row_map.get("customer_email") or "")
    payload.update(
        {
            "customerId": row_map.get("user_id", ""),
            "customerName": customer_name,
            "customerEmailMasked": customer_email_masked,
            "searchText": " ".join(
                filter(
                    None,
                    [
                        str(payload.get("orderCode") or ""),
                        customer_name,
                        customer_email,
                        str(payload.get("depositorName") or ""),
                        str(payload.get("reference") or ""),
                        str(payload.get("status") or ""),
                        str(payload.get("paymentChannelLabel") or ""),
                    ],
                )
            ).lower(),
        }
    )
    return payload


def charge_order_filter_clause(
    filters: Dict[str, Any],
    *,
    user_id: str,
    limit: Any = 50,
) -> Tuple[List[str], List[Any], int]:
    safe_limit = min(max(int(limit or 50), 1), 100)
    params: List[Any] = [user_id]
    conditions = ["user_id = ?"]
    status = str(filters.get("status") or "").strip().lower()
    if status and status != "all":
        conditions.append("status = ?")
        params.append(status)
    payment_channel = str(filters.get("paymentChannel") or "").strip().lower()
    if payment_channel and payment_channel != "all":
        conditions.append("payment_channel = ?")
        params.append(payment_channel)
    created_from = str(filters.get("createdFrom") or "").strip()
    if created_from:
        conditions.append("created_at >= ?")
        params.append(created_from)
    created_to = str(filters.get("createdTo") or "").strip()
    if created_to:
        conditions.append("created_at <= ?")
        params.append(created_to)
    return conditions, params, safe_limit


def wallet_ledger_filter_clause(
    filters: Dict[str, Any],
    *,
    user_id: str,
    limit: Any = 50,
) -> Tuple[List[str], List[Any], int]:
    safe_limit = min(max(int(limit or 50), 1), 100)
    params: List[Any] = [user_id]
    conditions = ["wl.user_id = ?"]
    entry_type = str(filters.get("entryType") or "").strip().lower()
    if entry_type and entry_type != "all":
        conditions.append("wl.entry_type = ?")
        params.append(entry_type)
    status = str(filters.get("status") or "").strip().lower()
    if status and status != "all":
        conditions.append("COALESCE(co.status, 'completed') = ?")
        params.append(status)
    payment_channel = str(filters.get("paymentChannel") or "").strip().lower()
    if payment_channel and payment_channel != "all":
        conditions.append("COALESCE(co.payment_channel, '') = ?")
        params.append(payment_channel)
    created_from = str(filters.get("createdFrom") or "").strip()
    if created_from:
        conditions.append("wl.created_at >= ?")
        params.append(created_from)
    created_to = str(filters.get("createdTo") or "").strip()
    if created_to:
        conditions.append("wl.created_at <= ?")
        params.append(created_to)
    return conditions, params, safe_limit


def wallet_ledger_entry_payload(
    row: Dict[str, Any],
    *,
    payment_method_detail_label: str = "",
    created_label: str = "",
) -> Dict[str, Any]:
    amount = int(row["amount"])
    balance_after = int(row["balance_after"])
    payment_channel = row["payment_channel"] or ""
    entry_type = row["entry_type"]
    receipt_type = row["receipt_type"] or "none"
    charge_status = row["charge_status"] or "completed"
    return {
        "id": row["id"],
        "entryType": entry_type,
        "entryTypeLabel": payment_method_label(entry_type),
        "amount": amount,
        "amountLabel": ("+" if amount > 0 else "") + money_label(amount),
        "balanceAfter": balance_after,
        "balanceAfterLabel": money_label(balance_after),
        "memo": row["memo"],
        "relatedChargeOrderId": row["related_charge_order_id"] or "",
        "relatedOrderId": row["related_order_id"] or "",
        "chargeOrderCode": row["order_code"] or "",
        "paymentChannel": payment_channel,
        "paymentChannelLabel": payment_method_label(payment_channel or entry_type),
        "paymentMethodDetail": row["payment_method_detail"] or "",
        "paymentMethodDetailLabel": payment_method_detail_label or payment_method_label(payment_channel),
        "receiptType": receipt_type,
        "receiptTypeLabel": receipt_type_label(receipt_type),
        "status": charge_status,
        "statusLabel": payment_status_label(charge_status),
        "reference": row["charge_reference"] or "",
        "failureReason": row["charge_failure_reason"] or "",
        "createdAt": row["created_at"],
        "createdLabel": created_label,
    }
