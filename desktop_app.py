#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser

from server import access_urls, make_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Brand Grid Studio desktop launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=8010, help="Port number")
    parser.add_argument("--lan", action="store_true", help="Shortcut for --host 0.0.0.0")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    parser.add_argument("--allow-cidr", action="append", default=[], help="Additional CIDR ranges to allow")
    parser.add_argument("--disable-internal-only", action="store_true", help="Disable internal IP guard")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = "0.0.0.0" if args.lan else args.host

    server = make_server(
        host=host,
        port=args.port,
        allow_cidrs=args.allow_cidr,
        internal_only=not args.disable_internal_only,
    )

    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    urls = access_urls(host, args.port)
    print("\nBrand Grid Studio desktop launcher")
    print("Press Ctrl+C to stop.\n")
    for url in urls:
        print("Access:", url)
    print("Internal IP guard:", "enabled" if not args.disable_internal_only else "disabled")

    if not args.no_browser and urls:
        time.sleep(0.4)
        webbrowser.open(urls[0])

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()
        server.server_close()
        return 0
    except Exception as exc:
        print(f"\nLauncher failed: {exc}", file=sys.stderr)
        server.shutdown()
        server.server_close()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
