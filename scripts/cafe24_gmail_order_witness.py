#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1"
DEFAULT_GMAIL_QUERY = "from:no-reply@cafe24shop.com newer_than:2d"
DEFAULT_WITNESS_URL = "https://smmproject-lime.vercel.app/api/cron/cafe24/email-order-witness"
ORDER_ID_PATTERN = re.compile(r"\b\d{8}-\d{7}\b")


@dataclass
class GmailOrderWitness:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    internal_date: str
    order_ids: List[str]


def env_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def first_env(*names: str) -> str:
    for name in names:
        value = str(os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def json_request(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    form: Optional[Dict[str, str]] = None,
    timeout_seconds: float = 20.0,
) -> Dict[str, Any]:
    data: Optional[bytes] = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    elif form is not None:
        data = urllib_parse.urlencode(form).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request_headers.setdefault("Accept", "application/json")
    request_headers.setdefault("User-Agent", "instamart-cafe24-gmail-witness")
    request = urllib_request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib_error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {raw_error[:1000]}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"HTTP request failed for {method} {url}: {exc}") from exc
    if not raw:
        return {}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from {method} {url}: {raw[:1000]!r}") from exc
    return decoded if isinstance(decoded, dict) else {}


def gmail_access_token(client_id: str, client_secret: str, refresh_token: str, *, timeout_seconds: float) -> str:
    response = json_request(
        GMAIL_TOKEN_URL,
        method="POST",
        form={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout_seconds=timeout_seconds,
    )
    token = str(response.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Gmail OAuth refresh succeeded but no access_token was returned.")
    return token


def gmail_url(user_id: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
    encoded_user = urllib_parse.quote(user_id or "me", safe="")
    query = urllib_parse.urlencode({key: value for key, value in (params or {}).items() if value not in (None, "")})
    base = f"{GMAIL_API_BASE_URL}/users/{encoded_user}/{path.lstrip('/')}"
    return f"{base}?{query}" if query else base


def gmail_message_ids(
    access_token: str,
    *,
    user_id: str,
    query: str,
    max_messages: int,
    timeout_seconds: float,
) -> List[str]:
    message_ids: List[str] = []
    page_token = ""
    headers = {"Authorization": f"Bearer {access_token}"}
    while len(message_ids) < max_messages:
        remaining = max_messages - len(message_ids)
        response = json_request(
            gmail_url(
                user_id,
                "messages",
                {
                    "q": query,
                    "maxResults": min(remaining, 100),
                    "pageToken": page_token,
                },
            ),
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        for message in response.get("messages") or []:
            if isinstance(message, dict):
                message_id = str(message.get("id") or "").strip()
                if message_id:
                    message_ids.append(message_id)
                    if len(message_ids) >= max_messages:
                        break
        page_token = str(response.get("nextPageToken") or "").strip()
        if not page_token:
            break
    return message_ids


def gmail_message(
    access_token: str,
    *,
    user_id: str,
    message_id: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    return json_request(
        gmail_url(user_id, f"messages/{urllib_parse.quote(message_id, safe='')}", {"format": "full"}),
        headers={"Authorization": f"Bearer {access_token}"},
        timeout_seconds=timeout_seconds,
    )


def base64url_text(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode((raw + padding).encode("ascii")).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""


def payload_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for header in payload.get("headers") or []:
        if not isinstance(header, dict):
            continue
        name = str(header.get("name") or "").strip().lower()
        value = str(header.get("value") or "").strip()
        if name and name not in headers:
            headers[name] = value
    return headers


def message_text_parts(payload: Dict[str, Any]) -> Iterable[str]:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
    data = str(body.get("data") or "")
    if data:
        yield base64url_text(data)
    for part in payload.get("parts") or []:
        if isinstance(part, dict):
            yield from message_text_parts(part)


def normalize_message_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", str(value or ""))
    return html.unescape(re.sub(r"\s+", " ", without_tags)).strip()


def extract_order_ids(*texts: str) -> List[str]:
    seen: Dict[str, None] = {}
    for text in texts:
        for match in ORDER_ID_PATTERN.findall(str(text or "")):
            seen.setdefault(match, None)
    return list(seen.keys())


def witness_from_gmail_message(message: Dict[str, Any]) -> GmailOrderWitness:
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    headers = payload_headers(payload)
    body_text = " ".join(normalize_message_text(part) for part in message_text_parts(payload))
    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    snippet = str(message.get("snippet") or "")
    order_ids = extract_order_ids(subject, snippet, body_text)
    return GmailOrderWitness(
        message_id=str(message.get("id") or "").strip(),
        thread_id=str(message.get("threadId") or "").strip(),
        subject=subject,
        sender=sender,
        internal_date=str(message.get("internalDate") or "").strip(),
        order_ids=order_ids,
    )


def witness_payload(witnesses: Iterable[GmailOrderWitness]) -> Dict[str, Any]:
    order_ids: List[str] = []
    message_ids: List[str] = []
    for witness in witnesses:
        if witness.message_id:
            message_ids.append(witness.message_id)
        for order_id in witness.order_ids:
            if order_id not in order_ids:
                order_ids.append(order_id)
    return {
        "source": "gmail_order_witness",
        "orderIds": order_ids,
        "gmailMessageIds": message_ids,
    }


def post_order_witness(
    witness_url: str,
    *,
    cron_token: str,
    payload: Dict[str, Any],
    timeout_seconds: float,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {cron_token}",
        "X-GitHub-Repository": str(os.environ.get("GITHUB_REPOSITORY") or ""),
        "X-GitHub-Run-Id": str(os.environ.get("GITHUB_RUN_ID") or ""),
        "X-GitHub-Workflow": str(os.environ.get("GITHUB_WORKFLOW") or "Cafe24 Gmail Order Witness"),
    }
    return json_request(
        witness_url,
        method="POST",
        headers=headers,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def print_summary(summary: Dict[str, Any]) -> None:
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check recent Cafe24 Gmail order emails and reconcile missing orders.")
    parser.add_argument("--dry-run", action="store_true", help="Read Gmail and print extracted order IDs without calling the panel.")
    parser.add_argument(
        "--allow-missing-credentials",
        action="store_true",
        help="Exit successfully with a skipped summary when Gmail OAuth credentials are not configured.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    timeout_seconds = float(bounded_int(first_env("CAFE24_GMAIL_TIMEOUT_SECONDS", "GMAIL_TIMEOUT_SECONDS") or 20, 20, 2, 60))
    max_messages = bounded_int(first_env("CAFE24_GMAIL_MAX_MESSAGES", "GMAIL_MAX_MESSAGES") or 20, 20, 1, 100)
    user_id = first_env("CAFE24_GMAIL_USER_ID", "GMAIL_USER_ID") or "me"
    query = first_env("CAFE24_GMAIL_QUERY", "GMAIL_QUERY") or DEFAULT_GMAIL_QUERY
    witness_url = first_env("CAFE24_GMAIL_WITNESS_URL", "SMM_PANEL_ORDER_WITNESS_URL") or DEFAULT_WITNESS_URL
    client_id = first_env("CAFE24_GMAIL_CLIENT_ID", "GMAIL_CLIENT_ID")
    client_secret = first_env("CAFE24_GMAIL_CLIENT_SECRET", "GMAIL_CLIENT_SECRET")
    refresh_token = first_env("CAFE24_GMAIL_REFRESH_TOKEN", "GMAIL_REFRESH_TOKEN")
    cron_token = first_env("SMM_PANEL_CRON_TOKEN", "CRON_SECRET", "SMM_PANEL_CRON_SECRET")
    allow_missing = args.allow_missing_credentials or env_flag(first_env("CAFE24_GMAIL_ALLOW_MISSING_CREDENTIALS"))

    missing_credentials = [
        name
        for name, value in {
            "CAFE24_GMAIL_CLIENT_ID": client_id,
            "CAFE24_GMAIL_CLIENT_SECRET": client_secret,
            "CAFE24_GMAIL_REFRESH_TOKEN": refresh_token,
        }.items()
        if not value
    ]
    if missing_credentials:
        summary = {
            "status": "skipped",
            "reason": "missing_gmail_credentials",
            "missing": missing_credentials,
        }
        print_summary(summary)
        return 0 if allow_missing else 2
    if not args.dry_run and not cron_token:
        print_summary({"status": "failed", "reason": "missing_cron_token"})
        return 2

    access_token = gmail_access_token(client_id, client_secret, refresh_token, timeout_seconds=timeout_seconds)
    message_ids = gmail_message_ids(
        access_token,
        user_id=user_id,
        query=query,
        max_messages=max_messages,
        timeout_seconds=timeout_seconds,
    )
    witnesses: List[GmailOrderWitness] = []
    for message_id in message_ids:
        witness = witness_from_gmail_message(
            gmail_message(
                access_token,
                user_id=user_id,
                message_id=message_id,
                timeout_seconds=timeout_seconds,
            )
        )
        if witness.order_ids:
            witnesses.append(witness)

    payload = witness_payload(witnesses)
    order_ids = payload["orderIds"]
    if args.dry_run or not order_ids:
        print_summary(
            {
                "status": "dry_run" if args.dry_run else "ok",
                "query": query,
                "messageCount": len(message_ids),
                "witnessMessageCount": len(witnesses),
                "orderIds": order_ids,
            }
        )
        return 0

    response = post_order_witness(witness_url, cron_token=cron_token, payload=payload, timeout_seconds=timeout_seconds)
    summary = {
        "status": response.get("status") or "ok",
        "query": query,
        "messageCount": len(message_ids),
        "witnessMessageCount": len(witnesses),
        "orderIds": order_ids,
        "panel": response,
    }
    print_summary(summary)
    failed = int(response.get("failed") or 0)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
