from __future__ import annotations

import datetime as dt
import secrets


def generate_charge_order_code() -> str:
    return f"CHG-{dt.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def balance_transaction_kind_to_ledger_entry_type(kind: str) -> str:
    labels = {
        "charge": "charge",
        "order": "order_debit",
        "admin_adjust": "admin_adjustment",
    }
    key = str(kind or "").strip().lower()
    return labels.get(key, key or "admin_adjustment")
