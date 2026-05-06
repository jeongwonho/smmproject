#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from studio_core import (
    DEFAULT_PORT,
    PRIVATE_CIDRS,
    PROJECT_ROOT,
    StudioError,
    StudioJobs,
    StudioStore,
    discover_local_ips,
    dump_json,
    is_allowed_client,
    safe_json_loads,
)


def read_json(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length).decode("utf-8") if length else "{}"
    return safe_json_loads(body, {})


def write_json(handler: SimpleHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def send_error_json(handler: SimpleHTTPRequestHandler, exc: Exception) -> None:
    if isinstance(exc, StudioError):
        write_json(handler, exc.status, {"ok": False, "error": str(exc)})
    else:
        write_json(handler, 500, {"ok": False, "error": str(exc)})


def bootstrap_payload(server: "StudioHTTPServer") -> Dict[str, Any]:
    urls = []
    if server.host in {"0.0.0.0", "::"}:
        urls.append(f"http://127.0.0.1:{server.port}")
        for address in discover_local_ips():
            urls.append(f"http://{address}:{server.port}")
    else:
        urls.append(f"http://{server.host}:{server.port}")
    return {
        "ok": True,
        "projects": server.store.list_projects(),
        "settings": server.store.get_settings(),
        "server": {
            "host": server.host,
            "port": server.port,
            "internalOnly": server.internal_only,
            "allowCidrs": [str(item) for item in server.allow_cidrs],
            "accessUrls": urls,
        },
    }


class StudioHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls: type[SimpleHTTPRequestHandler],
        *,
        store: StudioStore,
        jobs: StudioJobs,
        host: str,
        port: int,
        allow_cidrs: List[Any],
        internal_only: bool,
    ) -> None:
        super().__init__(server_address, handler_cls)
        self.store = store
        self.jobs = jobs
        self.host = host
        self.port = port
        self.allow_cidrs = allow_cidrs
        self.internal_only = internal_only


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(PROJECT_ROOT if directory is None else directory), **kwargs)

    def _server(self) -> StudioHTTPServer:
        return self.server  # type: ignore[return-value]

    def _guard_client(self) -> bool:
        server = self._server()
        if not server.internal_only:
            return True
        if is_allowed_client(self.client_address[0], server.allow_cidrs):
            return True
        write_json(
            self,
            403,
            {
                "ok": False,
                "error": "이 서버는 내부 IP 전용으로 설정되어 있습니다.",
            },
        )
        return False

    def do_GET(self) -> None:
        if not self._guard_client():
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "service": "Brand Grid Studio",
                        "internalOnly": self._server().internal_only,
                        "clientIp": self.client_address[0],
                    },
                )
                return
            if parsed.path == "/api/bootstrap":
                write_json(self, 200, bootstrap_payload(self._server()))
                return
            if parsed.path == "/api/projects":
                write_json(self, 200, {"ok": True, "projects": self._server().store.list_projects()})
                return
            if re.fullmatch(r"/api/projects/[^/]+", parsed.path or ""):
                project_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "project": self._server().store.get_project(project_id)})
                return
            if re.fullmatch(r"/api/jobs/[^/]+", parsed.path or ""):
                job_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "job": self._server().store.get_job(job_id)})
                return
            if parsed.path == "/api/settings":
                write_json(self, 200, {"ok": True, "settings": self._server().store.get_settings()})
                return
        except Exception as exc:
            send_error_json(self, exc)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if not self._guard_client():
            return
        parsed = urlparse(self.path)
        try:
            payload = read_json(self)
            server = self._server()
            if parsed.path == "/api/projects":
                write_json(self, 200, {"ok": True, "project": server.store.create_project(payload)})
                return
            if re.fullmatch(r"/api/projects/[^/]+", parsed.path or ""):
                project_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "project": server.store.update_project(project_id, payload)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/brand-pack/analyze", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                project = server.store.get_project(project_id)
                from studio_core import analyze_brand_pack, default_grid_plan

                brand_pack = analyze_brand_pack(project)
                grid_plan = default_grid_plan(project["gridSize"], project["industry"], brand_pack)
                server.store.set_project_blobs(project_id, brand_pack=brand_pack, grid_plan=grid_plan)
                write_json(self, 200, {"ok": True, "project": server.store.get_project(project_id)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/grid-plan/auto", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                project = server.store.get_project(project_id)
                from studio_core import default_grid_plan

                grid_plan = default_grid_plan(project["gridSize"], project["industry"], project["brandPack"])
                server.store.set_project_blobs(project_id, grid_plan=grid_plan)
                write_json(self, 200, {"ok": True, "project": server.store.get_project(project_id)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/grid-plan/save", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                write_json(self, 200, {"ok": True, "project": server.store.save_grid_plan(project_id, payload)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/create-one/generate", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                job = server.store.create_job(project_id, "generate_create_one", payload)
                server.jobs.enqueue(job["id"])
                write_json(self, 202, {"ok": True, "job": job})
                return
            if re.fullmatch(r"/api/projects/[^/]+/grid/generate", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                job = server.store.create_job(project_id, "generate_grid", payload)
                server.jobs.enqueue(job["id"])
                write_json(self, 202, {"ok": True, "job": job})
                return
            if re.fullmatch(r"/api/projects/[^/]+/comments", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                write_json(self, 200, {"ok": True, **server.store.add_comment(project_id, payload)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/export", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                write_json(self, 200, {"ok": True, "export": server.store.export_project(project_id)})
                return
            if re.fullmatch(r"/api/projects/[^/]+/export/obsidian", parsed.path or ""):
                project_id = parsed.path.split("/")[3]
                write_json(self, 200, {"ok": True, "obsidian": server.store.export_project_to_obsidian(project_id)})
                return
            if re.fullmatch(r"/api/variants/[^/]+", parsed.path or ""):
                variant_id = parsed.path.rsplit("/", 1)[-1]
                write_json(self, 200, {"ok": True, "variant": server.store.update_variant(variant_id, payload)})
                return
            if parsed.path == "/api/settings":
                write_json(self, 200, {"ok": True, "settings": server.store.update_settings(payload)})
                return
            raise StudioError("지원하지 않는 API 경로입니다.", status=404)
        except Exception as exc:
            send_error_json(self, exc)

    def guess_type(self, path: str) -> str:
        mime, _ = mimetypes.guess_type(path)
        if mime:
            return mime
        return super().guess_type(path)


def make_server(
    *,
    host: str,
    port: int,
    allow_cidrs: Optional[Iterable[str]] = None,
    internal_only: bool = True,
) -> StudioHTTPServer:
    store = StudioStore()
    jobs = StudioJobs(store)
    networks = list(PRIVATE_CIDRS)
    for item in allow_cidrs or []:
        from ipaddress import ip_network

        networks.append(ip_network(item))
    handler = partial(AppHandler, directory=str(PROJECT_ROOT))
    return StudioHTTPServer(
        (host, port),
        handler,
        store=store,
        jobs=jobs,
        host=host,
        port=port,
        allow_cidrs=networks,
        internal_only=internal_only,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Brand Grid Studio internal server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port number")
    parser.add_argument("--allow-cidr", action="append", default=[], help="Additional CIDR ranges to allow")
    parser.add_argument("--disable-internal-only", action="store_true", help="Disable private IP restriction")
    return parser.parse_args()


def access_urls(host: str, port: int) -> List[str]:
    if host in {"0.0.0.0", "::"}:
        urls = [f"http://127.0.0.1:{port}"]
        urls.extend(f"http://{address}:{port}" for address in discover_local_ips())
        return urls
    return [f"http://{host}:{port}"]


def main() -> None:
    args = parse_args()
    server = make_server(
        host=args.host,
        port=args.port,
        allow_cidrs=args.allow_cidr,
        internal_only=not args.disable_internal_only,
    )
    print("Brand Grid Studio server")
    print("Static root:", PROJECT_ROOT)
    for url in access_urls(args.host, args.port):
        print("Access:", url)
    if server.internal_only:
        print("Internal IP guard: enabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
