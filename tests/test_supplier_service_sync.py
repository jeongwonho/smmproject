import datetime as dt
from io import BytesIO
import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import patch

import bootstrap
from backend.integrations.suppliers import (
    FASTTRAFFIC_API_URL,
    SupplierApiError,
    normalize_supplier_api_candidates,
    normalize_supplier_services_payload,
    supplier_auto_dispatch_readiness,
    supplier_auto_dispatch_readiness_payload,
    supplier_service_record,
)
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

    def _ready_supplier_row(self, **overrides):
        row = {
            "is_active": 1,
            "api_key": "supplier-api-key",
            "service_is_active": 1,
            "service_external_id": "40000",
            "integration_type": "classic",
            "api_url": "https://supplier.example/api/v2",
            "active_service_count": 1,
            "service_sync_status": "success",
            "service_sync_message": "",
            "health_status": "ok",
            "health_message": "",
            "balance_status": "ok",
        }
        row.update(overrides)
        return row

    def test_supplier_api_candidate_helpers_live_in_supplier_domain(self):
        self.assertEqual(
            normalize_supplier_api_candidates("classic", "supplier.example"),
            [
                "https://supplier.example/api/v2",
                "https://supplier.example/api",
                "https://supplier.example",
            ],
        )
        self.assertEqual(
            normalize_supplier_api_candidates("mkt24", "https://api.mkt24.co.kr/v3"),
            ["https://api.mkt24.co.kr/v3/panel"],
        )
        self.assertEqual(normalize_supplier_api_candidates("fasttraffic", ""), [FASTTRAFFIC_API_URL])

    def test_supplier_service_payload_helpers_live_in_supplier_domain(self):
        services = normalize_supplier_services_payload(
            "mkt24",
            {
                "data": {
                    "instagram": [
                        {
                            "productUuid": "01811868-0f05-4000-8000-000000000018",
                            "fullName": "인스타그램 팔로워",
                            "productTypeName": "팔로워",
                            "normalPrice": "120",
                        }
                    ]
                }
            },
        )

        self.assertEqual(services[0]["_platformKey"], "instagram")
        record = supplier_service_record("mkt24", services[0])
        self.assertEqual(record["externalServiceId"], "01811868-0f05-4000-8000-000000000018")
        self.assertEqual(record["category"], "인스타그램")
        self.assertEqual(record["rate"], 120.0)
        self.assertIn("인스타그램 팔로워", record["rawJson"])

        panel_record = supplier_service_record(
            "mkt24",
            {"service": "40000", "name": "Panel Service", "rate": "1.5", "min": "1", "max": "5000"},
        )
        self.assertEqual(panel_record["externalServiceId"], "40000")
        self.assertEqual(panel_record["maxAmount"], 5000)

        with self.assertRaises(SupplierApiError):
            normalize_supplier_services_payload("classic", {"services": []})

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

    def test_mkt24_supplier_save_clears_legacy_bearer_token(self):
        created_at = now_iso()
        self.conn.execute(
            """
            INSERT INTO suppliers (
                id, name, api_url, integration_type, api_key, bearer_token,
                is_active, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_mkt24_legacy",
                "MKT24 Legacy",
                "https://api.mkt24.co.kr/v3/panel",
                "mkt24",
                "old-key",
                "legacy-bearer",
                1,
                "",
                created_at,
                created_at,
            ),
        )
        self.conn.commit()

        result = self.store.save_supplier(
            {
                "id": "supplier_mkt24_legacy",
                "name": "MKT24 Legacy",
                "apiUrl": "https://api.mkt24.co.kr/v3/panel",
                "integrationType": "mkt24",
                "apiKey": "new-key",
                "bearerToken": "should-be-ignored",
                "isActive": True,
                "_adminActor": "qa",
            }
        )

        row = self.conn.execute("SELECT bearer_token FROM suppliers WHERE id = ?", ("supplier_mkt24_legacy",)).fetchone()
        self.assertEqual(row["bearer_token"], "")
        self.assertFalse(result["supplier"]["hasBearerToken"])

    def test_boot_clears_mkt24_legacy_bearer_tokens(self):
        created_at = now_iso()
        self.conn.execute(
            """
            INSERT INTO suppliers (
                id, name, api_url, integration_type, api_key, bearer_token,
                is_active, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "supplier_mkt24_boot_cleanup",
                "MKT24 Boot Cleanup",
                "https://api.mkt24.co.kr/v3/panel",
                "mkt24",
                "api-key",
                "legacy-bearer",
                1,
                "",
                created_at,
                created_at,
            ),
        )
        self.conn.commit()

        PanelStore(db_path=self.db_path)

        row = self.conn.execute("SELECT bearer_token FROM suppliers WHERE id = ?", ("supplier_mkt24_boot_cleanup",)).fetchone()
        self.assertEqual(row["bearer_token"], "")

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

    def test_due_supplier_sync_uses_short_cron_timeout_and_returns_failure_result(self):
        captured = {}

        def fake_connection_test(_store, api_url, api_key, **kwargs):
            captured["apiUrl"] = api_url
            captured["requestTimeoutSeconds"] = kwargs.get("request_timeout_seconds")
            raise PanelError("공급사 API 응답 시간이 초과되었습니다.")

        with patch.object(PanelStore, "_run_supplier_connection_test", fake_connection_test):
            result = self.store.sync_due_supplier_services(
                actor="cron",
                limit=1,
                request_timeout_seconds=4,
            )

        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["requestTimeoutSeconds"], 4.0)
        self.assertEqual(captured["requestTimeoutSeconds"], 4.0)
        self.assertIn("응답 시간이 초과", result["results"][0]["error"])
        supplier = self.conn.execute("SELECT * FROM suppliers WHERE id = ?", ("supplier_sync",)).fetchone()
        self.assertEqual(supplier["service_sync_status"], "failed")
        self.assertIn("응답 시간이 초과", supplier["service_sync_message"])

    def test_supplier_auto_dispatch_readiness_covers_operational_blockers(self):
        cases = [
            (
                self._ready_supplier_row(is_active=0),
                "supplier_inactive",
                False,
            ),
            (
                self._ready_supplier_row(service_is_active=0),
                "supplier_service_inactive",
                False,
            ),
            (
                self._ready_supplier_row(service_external_id=""),
                "supplier_service_external_id_missing",
                False,
            ),
            (
                self._ready_supplier_row(api_key=""),
                "supplier_api_key_missing",
                False,
            ),
            (
                self._ready_supplier_row(active_service_count=0),
                "supplier_services_empty",
                True,
            ),
            (
                self._ready_supplier_row(service_sync_status="failed", service_sync_message="sync failed"),
                "supplier_sync_failed",
                True,
            ),
            (
                self._ready_supplier_row(health_status="failed", health_message="health failed"),
                "supplier_health_not_ok",
                True,
            ),
            (
                self._ready_supplier_row(balance_status="failed"),
                "supplier_balance_failed",
                True,
            ),
        ]
        for row, expected_code, expected_retryable in cases:
            with self.subTest(expected_code=expected_code):
                readiness = supplier_auto_dispatch_readiness(row, supplier_service_id="svc_1")
                self.assertFalse(readiness["ok"])
                self.assertEqual(readiness["code"], expected_code)
                self.assertEqual(readiness["retryable"], expected_retryable)

    def test_supplier_auto_dispatch_readiness_requires_numeric_mkt24_panel_service_id(self):
        for external_service_id in ("019e3ac5-b3e7-753e-8f5e-f425742ba7ca", "mkt24-product-uuid"):
            with self.subTest(external_service_id=external_service_id):
                readiness = supplier_auto_dispatch_readiness(
                    self._ready_supplier_row(
                        integration_type="mkt24",
                        api_url="https://api.mkt24.co.kr/v3/panel",
                        service_external_id=external_service_id,
                        balance_status="unsupported",
                    ),
                    supplier_service_id="svc_mkt24",
                )

                self.assertFalse(readiness["ok"])
                self.assertEqual(readiness["code"], "mkt24_panel_service_id_invalid")
                self.assertIn("숫자형 panel 서비스 ID", readiness["message"])
                self.assertIn("숫자형 panel service ID", readiness["nextAction"])
                self.assertEqual(readiness["dispatchContract"]["integrationType"], "mkt24")
                self.assertEqual(readiness["dispatchContract"]["endpointMode"], "/v3/panel")
                self.assertEqual(readiness["dispatchContract"]["authMode"], "api_key_form")
                self.assertEqual(readiness["dispatchContract"]["serviceIdRule"], "numeric_panel_service_id")
                self.assertEqual(readiness["dispatchContract"]["serviceIdValue"], external_service_id)
                requirements = {item["key"]: item for item in readiness["requirements"]}
                self.assertEqual(requirements["api_auth"]["status"], "pass")
                self.assertTrue(requirements["balance_check"]["ok"])
                self.assertFalse(requirements["balance_check"]["blocking"])
                self.assertEqual(requirements["mkt24_dispatch_contract"]["status"], "blocked")
                self.assertIn("숫자형 panel 서비스 ID", requirements["mkt24_dispatch_contract"]["message"])

    def test_supplier_auto_dispatch_readiness_allows_supported_supplier_types(self):
        cases = [
            self._ready_supplier_row(integration_type="classic", balance_status="ok"),
            self._ready_supplier_row(integration_type="fasttraffic", balance_status="ok"),
            self._ready_supplier_row(
                integration_type="mkt24",
                api_url="https://api.mkt24.co.kr/v3/panel",
                service_external_id="730000",
                balance_status="unsupported",
            ),
        ]
        for row in cases:
            with self.subTest(integration=row["integration_type"]):
                readiness = supplier_auto_dispatch_readiness(row, supplier_service_id="svc_1")
                self.assertTrue(readiness["ok"])
                self.assertEqual(readiness["code"], "ok")
                self.assertIn("발주", readiness["nextAction"])
                self.assertFalse(readiness["reviewRequired"])
                self.assertEqual(readiness["reviewCodes"], [])
                self.assertEqual(readiness["dispatchContract"]["integrationType"], row["integration_type"])
                self.assertEqual(readiness["dispatchContract"]["serviceIdValue"], row["service_external_id"])

    def test_supplier_auto_dispatch_readiness_payload_accepts_admin_count_alias(self):
        row = self._ready_supplier_row(service_count=3)
        row.pop("active_service_count")
        payload = supplier_auto_dispatch_readiness_payload(row, supplier_service_id="svc_1")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["code"], "ok")
        self.assertIn("발주", payload["nextAction"])
        self.assertEqual(payload["reviewCodes"], [])
        self.assertEqual(payload["dispatchContract"]["integrationType"], "classic")
        self.assertEqual(payload["dispatchContract"]["serviceIdRule"], "numeric_or_panel_service_id")
        requirement_map = {item["key"]: item for item in payload["requirements"]}
        self.assertEqual(requirement_map["service_catalog"]["value"], "3개")

    def test_admin_bootstrap_exposes_supplier_auto_dispatch_readiness(self):
        supplier = next(
            item for item in self.store.admin_bootstrap()["suppliers"] if item["id"] == "supplier_sync"
        )

        self.assertFalse(supplier["autoDispatchReadiness"]["ok"])
        self.assertEqual(supplier["autoDispatchReadiness"]["code"], "supplier_health_not_ok")
        requirement_keys = [item["key"] for item in supplier["autoDispatchReadiness"]["requirements"]]
        self.assertIn("service_sync", requirement_keys)
        self.assertIn("api_auth", requirement_keys)
        self.assertIn("health_check", requirement_keys)
        self.assertIn("classic_dispatch_contract", requirement_keys)

        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE suppliers
            SET service_sync_status = 'success',
                service_sync_completed_at = ?,
                health_status = 'ok',
                health_message = 'ok',
                health_checked_at = ?,
                balance_status = 'ok',
                balance_checked_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, timestamp, "supplier_sync"),
        )
        self.conn.commit()

        supplier = next(
            item for item in self.store.admin_bootstrap()["suppliers"] if item["id"] == "supplier_sync"
        )

        self.assertTrue(supplier["autoDispatchReadiness"]["ok"])
        self.assertEqual(supplier["autoDispatchReadiness"]["code"], "ok")

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
            with self.assertRaisesRegex(Exception, "인증 정보.*만료"):
                client.services()

    def test_supplier_api_client_uses_configured_request_timeout(self):
        client = SupplierApiClient(
            "https://supplier.example/api/v2",
            "api-key",
            request_timeout_seconds=4,
        )
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"[]"

        def fake_urlopen(request: Request, timeout=12):
            captured["timeout"] = timeout
            return FakeResponse()

        with patch(f"{SupplierApiClient.__module__}.urlopen", side_effect=fake_urlopen):
            client.services()

        self.assertEqual(captured["timeout"], 4.0)

    def test_fasttraffic_balance_uses_x_api_key_header(self):
        api_key = "a" * 64
        client = SupplierApiClient(
            "https://fastraffic.co.kr/bbs/board.php?bo_table=fast_api_manger",
            api_key,
            integration_type="fasttraffic",
        )
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"success": true, "mb_point": 12500}'

        def fake_urlopen(request: Request, timeout=15):
            captured["url"] = request.full_url
            captured["headers"] = {key.lower(): value for key, value in request.header_items()}
            captured["body"] = (request.data or b"").decode("utf-8")
            captured["timeout"] = timeout
            return FakeResponse()

        with patch(f"{SupplierApiClient.__module__}.urlopen", side_effect=fake_urlopen):
            payload = client.balance()

        self.assertEqual(captured["url"], "https://fastraffic.co.kr/nblog_api.php")
        self.assertEqual(captured["headers"].get("x-api-key"), api_key)
        self.assertIn("action=check_balance", captured["body"])
        self.assertNotIn("api_key", captured["body"])
        self.assertEqual(payload["mb_point"], 12500)

    def test_fasttraffic_static_services_syncs_catalog(self):
        with patch.object(
            SupplierApiClient,
            "_request_fasttraffic_form",
            return_value={"success": True, "mb_point": 50000},
        ):
            created = self.store.save_supplier(
                {
                    "name": "FastTraffic",
                    "apiUrl": "https://fastraffic.co.kr",
                    "integrationType": "fasttraffic",
                    "apiKey": "b" * 64,
                    "isActive": True,
                    "_adminActor": "qa",
                }
            )
            result = self.store.sync_supplier_services(created["supplier"]["id"], actor="qa")

        self.assertEqual(created["supplier"]["apiUrl"], "https://fastraffic.co.kr/nblog_api.php")
        self.assertEqual(result["serviceCount"], 8)
        row = self.conn.execute(
            """
            SELECT *
            FROM supplier_services
            WHERE supplier_id = ? AND external_service_id = ?
            """,
            (created["supplier"]["id"], "nblog_direct"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_active"], 1)
        self.assertIn("FastTraffic", row["category"])

    def test_fasttraffic_nblog_direct_payload_transform(self):
        payload = self.store._build_supplier_order_payload(
            {"name": "블로그 체류 상품", "price_strategy": "unit"},
            {
                "targetUrl": "blog.naver.com/test/123",
                "orderedCount": "30",
                "requestMemo": "댓글 샘플",
            },
            {
                "integration_type": "fasttraffic",
                "supplier_external_service_id": "nblog_direct",
                "supplier_service_raw_json": '{"min":1,"max":5000,"fasttraffic":{"required":["title","blog_url"],"quantityParam":"stay_count","defaults":{"stay_time":60}}}',
            },
        )

        self.assertEqual(payload["action"], "nblog_direct")
        self.assertEqual(payload["blog_url"], "https://blog.naver.com/test/123")
        self.assertEqual(payload["stay_count"], 30)
        self.assertEqual(payload["stay_time"], 60)
        self.assertEqual(payload["title"], "블로그 체류 상품")

    def test_fasttraffic_missing_required_target_blocks_payload(self):
        with self.assertRaisesRegex(PanelError, "필수값 누락"):
            self.store._build_supplier_order_payload(
                {"name": "클립 상품", "price_strategy": "unit"},
                {"orderedCount": "20"},
                {
                    "integration_type": "fasttraffic",
                    "supplier_external_service_id": "nclip_direct_c",
                    "supplier_service_raw_json": '{"min":1,"max":10000,"fasttraffic":{"required":["title","clip_url"],"quantityParam":"view_count"}}',
                },
            )


if __name__ == "__main__":
    unittest.main()
