#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from core import APP_ROOT, PanelError, PanelStore


STATIC_ROOT = APP_ROOT / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8024


def read_json(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def write_json(handler: SimpleHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def send_error_json(handler: SimpleHTTPRequestHandler, exc: Exception) -> None:
    if isinstance(exc, PanelError):
        write_json(handler, exc.status, {"ok": False, "error": str(exc)})
        return
    write_json(handler, 500, {"ok": False, "error": str(exc)})


class PanelHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[SimpleHTTPRequestHandler], store: PanelStore) -> None:
        super().__init__(server_address, handler_cls)
        self.store = store


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_ROOT if directory is None else directory), **kwargs)

    def _server(self) -> PanelHTTPServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                write_json(self, 200, {"ok": True, "service": "Pulse24 Demo Panel"})
                return
            if parsed.path == "/api/bootstrap":
                write_json(self, 200, {"ok": True, **self._server().store.bootstrap()})
                return
            if parsed.path == "/api/admin/bootstrap":
                write_json(self, 200, {"ok": True, **self._server().store.admin_bootstrap()})
                return
            if parsed.path == "/api/products":
                search = parse_qs(parsed.query).get("q", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_catalog(search)})
                return
            if parsed.path.startswith("/api/admin/suppliers/") and parsed.path.endswith("/services"):
                supplier_id = parsed.path.split("/")[4]
                search = parse_qs(parsed.query).get("q", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_supplier_services(supplier_id, search)})
                return
            if parsed.path.startswith("/api/product-categories/"):
                category_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "category": self._server().store.get_product_category(category_id)})
                return
            if parsed.path == "/api/orders":
                status = parse_qs(parsed.query).get("status", [""])[0]
                write_json(self, 200, {"ok": True, **self._server().store.list_orders(status)})
                return
            if parsed.path == "/api/transactions":
                write_json(self, 200, {"ok": True, **self._server().store.list_transactions()})
                return
        except Exception as exc:
            send_error_json(self, exc)
            return

        asset_path = (STATIC_ROOT / parsed.path.lstrip("/")).resolve()
        if parsed.path not in {"", "/"} and asset_path.is_file() and STATIC_ROOT in asset_path.parents:
            self.path = parsed.path
            super().do_GET()
            return

        self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = read_json(self)
            if parsed.path == "/api/orders":
                write_json(self, 200, self._server().store.create_order(payload))
                return
            if parsed.path == "/api/admin/suppliers":
                write_json(self, 200, {"ok": True, **self._server().store.save_supplier(payload)})
                return
            if parsed.path == "/api/admin/customers":
                write_json(self, 200, {"ok": True, **self._server().store.save_customer(payload)})
                return
            if parsed.path == "/api/admin/customers/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_customer(payload)})
                return
            if parsed.path == "/api/admin/customers/balance":
                write_json(self, 200, {"ok": True, **self._server().store.adjust_customer_balance(payload)})
                return
            if parsed.path == "/api/admin/categories":
                write_json(self, 200, {"ok": True, **self._server().store.save_category(payload)})
                return
            if parsed.path == "/api/admin/categories/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_category(payload)})
                return
            if parsed.path == "/api/admin/products":
                write_json(self, 200, {"ok": True, **self._server().store.save_catalog_product(payload)})
                return
            if parsed.path == "/api/admin/products/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_catalog_product(payload)})
                return
            if parsed.path == "/api/admin/orders/status":
                write_json(self, 200, {"ok": True, **self._server().store.update_admin_order_status(payload)})
                return
            if parsed.path == "/api/admin/suppliers/test":
                write_json(self, 200, {"ok": True, **self._server().store.test_supplier_connection(payload)})
                return
            if parsed.path.startswith("/api/admin/suppliers/") and parsed.path.endswith("/sync-services"):
                supplier_id = parsed.path.split("/")[4]
                write_json(self, 200, {"ok": True, **self._server().store.sync_supplier_services(supplier_id)})
                return
            if parsed.path == "/api/admin/mappings":
                write_json(self, 200, {"ok": True, **self._server().store.save_product_mapping(payload)})
                return
            if parsed.path == "/api/admin/mappings/delete":
                write_json(self, 200, {"ok": True, **self._server().store.delete_product_mapping(payload)})
                return
            if parsed.path == "/api/link-preview":
                write_json(self, 200, self._server().store.preview_link(payload))
                return
            if parsed.path == "/api/charge":
                amount = int(payload.get("amount") or 0)
                write_json(self, 200, self._server().store.charge_balance(amount))
                return
            raise PanelError("지원하지 않는 API 경로입니다.", status=404)
        except Exception as exc:
            send_error_json(self, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pulse24 demo SMM panel")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = PanelStore()
    handler = partial(AppHandler, directory=str(STATIC_ROOT))
    httpd = PanelHTTPServer((args.host, args.port), handler, store)
    print(f"Pulse24 demo panel running at http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == "__main__":
    main()
