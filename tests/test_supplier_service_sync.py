import datetime as dt
from io import BytesIO
import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

import bootstrap
from core import (
    PanelError,
    PanelStore,
    SupplierApiClient,
    now_iso,
    supplier_service_sync_due,
)


class SupplierServiceSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "instamart_supplier_sync_test.db"
        self.store = PanelStore(db_path=self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._seed_supplier()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _seed_supplier(self):
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO suppliers (
                id, name, api_url, integration_type, api_key, bearer_token,
                is_active, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_sync",
                "Sync Supplier",
                "https://supplier.example/api/v2",
                "classic",
                "classic-key",
                "",
                1,
                "",
                timestamp,
                timestamp,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO supplier_services (
                id, supplier_id, external_service_id, name, category, type,
                rate, min_amount, max_amount, raw_json, synced_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "svc_removed",
                "supplier_sync",
                "removed-1",
                "Removed Service",
                "Old",
                "Default",
                1.0,
                1,
                100,
                "{}",
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()

    def test_sync_upserts_latest_services_and_marks_missing_inactive(self):
        payload = [
            {
                "service": "svc-100",
                "name": "Active Service",
                "category": "Instagram",
                "type": "Default",
                "rate": "12.5",
                "min": "5",
                "max": "5000",
            }
        ]
        with patch.object(
            PanelStore,
            "_run_supplier_connection_test",
            return_value={
                "status": "success",
                "message": "ok",
                "resolvedApiUrl": "https://supplier.example/api/v2",
                "persistedApiUrl": "https://supplier.example/api/v2",
                "balance": "",
                "currency": "",
                "serviceCount": 1,
                "checkedAt": now_iso(),
                "servicesPayload": payload,
            },
        ):
            result = self.store.sync_supplier_services("supplier_sync", actor="test")

        self.assertEqual(result["serviceCount"], 1)
        active = self.conn.execute(
            "SELECT * FROM supplier_services WHERE supplier_id = ? AND external_service_id = ?",
            ("supplier_sync", "svc-100"),
        ).fetchone()
        removed = self.conn.execute(
            "SELECT * FROM supplier_services WHERE supplier_id = ? AND external_service_id = ?",
            ("supplier_sync", "removed-1"),
        ).fetchone()
        supplier = self.conn.execute("SELECT * FROM suppliers WHERE id = ?", ("supplier_sync",)).fetchone()
        self.assertIsNotNone(active)
        self.assertEqual(active["is_active"], 1)
        self.assertEqual(active["min_amount"], 5)
        self.assertEqual(removed["is_active"], 0)
        self.assertTrue(removed["removed_at"])
        self.assertEqual(supplier["service_sync_status"], "success")
        self.assertEqual(supplier["service_sync_error_count"], 0)

    def test_mkt24_supplier_can_be_saved_with_api_key_only(self):
        result = self.store.save_supplier(
            {
                "name": "MKT24 API Key Only",
                "apiUrl": "https://api.mkt24.co.kr/v3",
                "integrationType": "mkt24",
                "apiKey": "mkt24-api-key",
                "isActive": True,
                "_adminActor": "qa",
            }
        )

        self.assertEqual(result["supplier"]["integrationType"], "mkt24")
        self.assertEqual(result["supplier"]["apiUrl"], "https://api.mkt24.co.kr/v3/panel")
        self.assertTrue(result["supplier"]["hasApiKey"])
        self.assertFalse(result["supplier"]["hasBearerToken"])

    def test_active_lock_blocks_duplicate_sync(self):
        future = (dt.datetime.now().astimezone() + dt.timedelta(minutes=5)).isoformat(timespec="seconds")
        self.conn.execute(
            "UPDATE suppliers SET service_sync_status = 'syncing', service_sync_lock_until = ? WHERE id = ?",
            (future, "supplier_sync"),
        )
        self.conn.commit()

        with self.assertRaises(PanelError):
            self.store.sync_supplier_services("supplier_sync", actor="test")

    def test_due_helper_respects_lock_and_interval(self):
        now = dt.datetime.now().astimezone()
        old_completed = (now - dt.timedelta(minutes=45)).isoformat(timespec="seconds")
        future_lock = (now + dt.timedelta(minutes=5)).isoformat(timespec="seconds")
        self.assertTrue(
            supplier_service_sync_due(
                {
                    "is_active": 1,
                    "service_sync_completed_at": old_completed,
                    "last_checked_at": "",
                    "service_sync_status": "success",
                    "service_sync_lock_until": "",
                    "service_sync_interval_minutes": 30,
                },
                now,
            )
        )
        self.assertFalse(
            supplier_service_sync_due(
                {
                    "is_active": 1,
                    "service_sync_completed_at": old_completed,
                    "last_checked_at": "",
                    "service_sync_status": "success",
                    "service_sync_lock_until": future_lock,
                    "service_sync_interval_minutes": 30,
                },
                now,
            )
        )

    def test_mkt24_services_normalizes_v3_url_to_panel_endpoint(self):
        client = SupplierApiClient(
            "https://api.mkt24.co.kr/v3",
            "api-key",
            integration_type="mkt24",
        )
        captured = {}

        def fake_request_form(payload):
            captured.update(payload)
            return [{"service": "12", "name": "Panel Service", "min": "5", "max": "1000"}]

        with patch.object(client, "_request_form", side_effect=fake_request_form):
            client.services()

        self.assertEqual(client.api_url, "https://api.mkt24.co.kr/v3/panel")
        self.assertEqual(captured, {"key": "api-key", "action": "services"})

    def test_mkt24_panel_endpoint_uses_standard_panel_services_action(self):
        client = SupplierApiClient(
            "https://api.mkt24.co.kr/v3/panel",
            "api-key",
            integration_type="mkt24",
        )
        captured = {}

        def fake_request_form(payload):
            captured.update(payload)
            return [{"service": "12", "name": "Panel Service", "min": "5", "max": "1000"}]

        with patch.object(client, "_request_form", side_effect=fake_request_form):
            payload = client.services()

        self.assertEqual(captured, {"key": "api-key", "action": "services"})
        self.assertEqual(payload[0]["service"], "12")

    def test_mkt24_panel_endpoint_uses_standard_panel_order_and_status_actions(self):
        client = SupplierApiClient(
            "https://api.mkt24.co.kr/v3/panel",
            "api-key",
            integration_type="mkt24",
        )
        calls = []

        def fake_request_form(payload):
            calls.append(dict(payload))
            return {"order": "1001"}

        with patch.object(client, "_request_form", side_effect=fake_request_form):
            order_payload = client.order({"service": "12", "link": "https://example.com/post", "quantity": 10})
            status_payload = client.status("1001")

        self.assertEqual(order_payload["order"], "1001")
        self.assertEqual(status_payload["order"], "1001")
        self.assertEqual(calls[0]["action"], "add")
        self.assertEqual(calls[0]["service"], "12")
        self.assertEqual(calls[1], {"key": "api-key", "action": "status", "order": "1001"})

    def test_mkt24_panel_service_payload_normalizes_like_classic_panel_api(self):
        with patch("core.SupplierApiClient.services", return_value=[{"service": "12", "name": "Panel Service", "min": "5", "max": "1000"}]):
            result = self.store._run_supplier_connection_test(
                "https://api.mkt24.co.kr/v3/panel",
                "api-key",
                integration_type="mkt24",
                require_services=True,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["resolvedApiUrl"], "https://api.mkt24.co.kr/v3/panel")
        self.assertEqual(result["servicesPayload"][0]["service"], "12")

    def test_mkt24_token_expired_error_is_actionable(self):
        client = SupplierApiClient(
            "https://api.mkt24.co.kr/v3",
            "api-key",
            integration_type="mkt24",
            bearer_token="expired-token",
        )
        body = b'{"code":"token_expired","uuid":"019e3ac5-b3e7-753e-8f5e-f425742ba7ca"}'
        error = HTTPError("https://api.mkt24.co.kr/v3/panel", 401, "Unauthorized", {}, BytesIO(body))

        with patch(f"{SupplierApiClient.__module__}.urlopen", side_effect=error):
            with self.assertRaisesRegex(Exception, "Bearer Token.*만료"):
                client.services()


if __name__ == "__main__":
    unittest.main()
