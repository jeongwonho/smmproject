import tempfile
import unittest
from pathlib import Path

from core import PanelStore


class SharedRateLimitTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "shared_rate_limit_test.db"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_rate_limit_count_is_shared_between_store_instances(self):
        first_store = PanelStore(db_path=self.db_path)
        second_store = PanelStore(db_path=self.db_path)

        self.assertEqual(first_store.shared_rate_limit_retry_after("auth", "203.0.113.10", 2, 60), 0)
        self.assertEqual(second_store.shared_rate_limit_retry_after("auth", "203.0.113.10", 2, 60), 0)
        self.assertGreater(first_store.shared_rate_limit_retry_after("auth", "203.0.113.10", 2, 60), 0)

    def test_rate_limit_does_not_store_raw_client_identity(self):
        store = PanelStore(db_path=self.db_path)
        store.shared_rate_limit_retry_after("orders", "198.51.100.22", 10, 60)

        with store._connect() as conn:
            row = conn.execute("SELECT * FROM security_rate_limits").fetchone()
        self.assertNotEqual(row["client_key_hash"], "198.51.100.22")
        self.assertEqual(len(row["client_key_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
