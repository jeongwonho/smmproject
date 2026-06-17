from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request


GITHUB_ACTIONS_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_ACTIONS_OIDC_JWKS_URL = f"{GITHUB_ACTIONS_OIDC_ISSUER}/.well-known/jwks"
GITHUB_ACTIONS_OIDC_DEFAULT_AUDIENCE = "instamart-cron"
GITHUB_ACTIONS_EXPECTED_EVENTS = {"schedule", "workflow_dispatch"}
JWT_RS256_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def env_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def cron_secret() -> str:
    return str(os.environ.get("CRON_SECRET") or os.environ.get("SMM_PANEL_CRON_SECRET") or "").strip()


def expected_github_cron_repository() -> str:
    return str(os.environ.get("SMM_PANEL_GITHUB_CRON_REPOSITORY") or "jeongwonho/smmproject").strip()


def expected_github_oidc_audience() -> str:
    return str(os.environ.get("SMM_PANEL_GITHUB_OIDC_AUDIENCE") or GITHUB_ACTIONS_OIDC_DEFAULT_AUDIENCE).strip()


def legacy_github_run_cron_auth_enabled() -> bool:
    return env_flag(os.environ.get("SMM_PANEL_ALLOW_GITHUB_RUN_CRON_AUTH", ""))


def _jwt_base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _jwt_json_segment(value: str) -> Dict[str, Any]:
    payload = json.loads(_jwt_base64url_decode(value).decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _fetch_github_oidc_jwks() -> Dict[str, Any]:
    request = urllib_request.Request(
        GITHUB_ACTIONS_OIDC_JWKS_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "instamart-cafe24-cron-verifier",
        },
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=5) as response:
        payload = json.load(response)
    return payload if isinstance(payload, dict) else {}


def _verify_rs256_signature(signing_input: bytes, signature: bytes, jwk: Dict[str, Any]) -> bool:
    try:
        modulus = int.from_bytes(_jwt_base64url_decode(str(jwk.get("n") or "")), "big")
        exponent = int.from_bytes(_jwt_base64url_decode(str(jwk.get("e") or "")), "big")
    except (ValueError, TypeError, binascii.Error):
        return False
    if modulus <= 0 or exponent <= 0:
        return False
    key_size = (modulus.bit_length() + 7) // 8
    if len(signature) != key_size:
        return False
    decoded = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes(key_size, "big")
    digest_info = JWT_RS256_SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(signing_input).digest()
    if not decoded.startswith(b"\x00\x01") or not decoded.endswith(digest_info):
        return False
    separator_index = decoded.find(b"\x00", 2)
    if separator_index < 10:
        return False
    return decoded[separator_index + 1 :] == digest_info and all(byte == 0xFF for byte in decoded[2:separator_index])


def github_actions_oidc_claims(token: str) -> Optional[Dict[str, Any]]:
    try:
        header_segment, payload_segment, signature_segment = str(token or "").split(".", 2)
        header = _jwt_json_segment(header_segment)
        payload = _jwt_json_segment(payload_segment)
        signature = _jwt_base64url_decode(signature_segment)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        return None
    if header.get("alg") != "RS256":
        return None
    kid = str(header.get("kid") or "")
    if not kid:
        return None
    try:
        jwks = _fetch_github_oidc_jwks()
    except (urllib_error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    matching_key = next((key for key in jwks.get("keys") or [] if isinstance(key, dict) and str(key.get("kid") or "") == kid), None)
    if not matching_key:
        return None
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    if not _verify_rs256_signature(signing_input, signature, matching_key):
        return None
    return payload


def github_actions_oidc_authorization_valid(headers: Any) -> bool:
    auth_header = str(headers.get("Authorization", "") if headers else "").strip()
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header.removeprefix("Bearer ").strip()
    if token.count(".") != 2:
        return False
    payload = github_actions_oidc_claims(token)
    if not payload:
        return False
    now_seconds = int(time.time())
    try:
        expires_at = int(payload.get("exp") or 0)
        not_before = int(payload.get("nbf") or payload.get("iat") or 0)
    except (TypeError, ValueError):
        return False
    if expires_at < now_seconds or not_before > now_seconds + 60:
        return False
    audience = payload.get("aud")
    expected_audience = expected_github_oidc_audience()
    audience_ok = expected_audience in audience if isinstance(audience, list) else str(audience or "") == expected_audience
    expected_repository = expected_github_cron_repository()
    repository = str(headers.get("X-GitHub-Repository", "") if headers else "").strip()
    run_id = str(headers.get("X-GitHub-Run-Id", "") if headers else "").strip()
    token_run_id = str(payload.get("run_id") or "").strip()
    return (
        str(payload.get("iss") or "") == GITHUB_ACTIONS_OIDC_ISSUER
        and audience_ok
        and str(payload.get("repository") or "") == expected_repository
        and (not repository or repository == expected_repository)
        and str(payload.get("event_name") or "") in GITHUB_ACTIONS_EXPECTED_EVENTS
        and bool(token_run_id)
        and (not run_id or run_id == token_run_id)
    )


def github_actions_run_authorization_valid(headers: Any) -> bool:
    auth_header = str(headers.get("Authorization", "") if headers else "").strip()
    if not auth_header.startswith("Bearer "):
        return False
    repository = str(headers.get("X-GitHub-Repository", "") if headers else "").strip()
    run_id = str(headers.get("X-GitHub-Run-Id", "") if headers else "").strip()
    expected_repository = expected_github_cron_repository()
    if repository != expected_repository or not run_id.isdigit():
        return False

    request = urllib_request.Request(
        f"https://api.github.com/repos/{expected_repository}/actions/runs/{run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": auth_header,
            "User-Agent": "instamart-cafe24-cron-verifier",
        },
        method="GET",
    )
    try:
        with urllib_request.urlopen(request, timeout=5) as response:
            if int(getattr(response, "status", 0) or 0) != 200:
                return False
            payload = json.load(response)
    except (urllib_error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return False

    run_repository = str((payload.get("repository") or {}).get("full_name") or "")
    run_event = str(payload.get("event") or "")
    return (
        str(payload.get("id") or "") == run_id
        and run_repository == expected_repository
        and run_event in {"schedule", "workflow_dispatch"}
    )


def github_actions_cron_authorization_valid(headers: Any) -> bool:
    return github_actions_oidc_authorization_valid(headers) or (
        legacy_github_run_cron_auth_enabled() and github_actions_run_authorization_valid(headers)
    )


def cron_authorization_valid(header_value: str, headers: Any = None) -> bool:
    expected = cron_secret()
    provided = str(header_value or "").strip()
    if expected and provided and hmac.compare_digest(provided, f"Bearer {expected}"):
        return True
    return github_actions_cron_authorization_valid(headers)
