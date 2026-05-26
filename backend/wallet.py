from __future__ import annotations

import datetime as dt
import secrets
from typing import Any, Dict


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


def balance_transaction_kind_to_ledger_entry_type(kind: str) -> str:
    labels = {
        "charge": "charge",
        "order": "order_debit",
        "admin_adjust": "admin_adjustment",
    }
    key = str(kind or "").strip().lower()
    return labels.get(key, key or "admin_adjustment")
