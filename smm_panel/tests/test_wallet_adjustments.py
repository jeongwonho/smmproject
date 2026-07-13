import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.errors import PanelError
from core import PanelStore, now_iso


class WalletAdjustmentTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "wallet_adjustment_test.db"
        self.store = PanelStore(db_path=self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO users (id, name, email, phone, balance, created_at, updated_at)
            VALUES ('user_wallet_test', 'Wallet Test', 'wallet@example.com', '010-0000-0000', 10000, ?, ?)
            """,
            (timestamp, timestamp),
        )
        self.conn.execute(
            """
            INSERT INTO wallets (user_id, available_balance, pending_balance, created_at, updated_at)
            VALUES ('user_wallet_test', 12000, 0, ?, ?)
            """,
            (timestamp, timestamp),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_admin_adjustment_applies_delta_to_wallet_balance(self):
        result = self.store.adjust_customer_balance(
            {
                "customerId": "user_wallet_test",
                "amount": 3000,
                "memo": "manual correction",
                "_adminActor": "admin",
            }
        )

        self.assertEqual(result["balanceAfter"], 15000)
        wallet = self.conn.execute("SELECT available_balance FROM wallets WHERE user_id = 'user_wallet_test'").fetchone()
        user = self.conn.execute("SELECT balance FROM users WHERE id = 'user_wallet_test'").fetchone()
        transaction = self.conn.execute("SELECT * FROM balance_transactions WHERE user_id = 'user_wallet_test'").fetchone()
        ledger = self.conn.execute("SELECT * FROM wallet_ledger WHERE user_id = 'user_wallet_test'").fetchone()
        audit = self.conn.execute("SELECT * FROM admin_audit_logs WHERE entity_id = 'user_wallet_test'").fetchone()
        self.assertEqual(wallet["available_balance"], 15000)
        self.assertEqual(user["balance"], 15000)
        self.assertEqual(transaction["balance_after"], 15000)
        self.assertEqual(ledger["balance_after"], 15000)
        self.assertIn('"balanceBefore": 12000', audit["metadata_json"])

    def test_admin_adjustment_rejects_negative_balance_without_ledger_mutation(self):
        with self.assertRaises(PanelError):
            self.store.adjust_customer_balance(
                {
                    "customerId": "user_wallet_test",
                    "amount": -13000,
                    "memo": "invalid debit",
                    "_adminActor": "admin",
                }
            )

        wallet = self.conn.execute("SELECT available_balance FROM wallets WHERE user_id = 'user_wallet_test'").fetchone()
        self.assertEqual(wallet["available_balance"], 12000)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM balance_transactions").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wallet_ledger").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
