#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import argparse
from pathlib import Path
from urllib.request import Request, urlopen


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core import PanelStore  # noqa: E402


REMOTE_AUDIT_PATH = "/api/cron/cafe24/operational-audit"
REMOTE_AUDIT_TOKEN_ENV_KEYS = ("SMM_PANEL_AUDIT_BEARER_TOKEN", "CRON_SECRET", "SMM_PANEL_CRON_SECRET")


def _remote_audit_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if not normalized:
        raise RuntimeError("Remote audit requires --base-url or SMM_PANEL_AUDIT_BASE_URL.")
    if normalized.endswith(REMOTE_AUDIT_PATH):
        return normalized
    return f"{normalized}{REMOTE_AUDIT_PATH}"


def _remote_bearer_token(token_env: str = "") -> str:
    env_keys = (str(token_env).strip(),) if str(token_env or "").strip() else REMOTE_AUDIT_TOKEN_ENV_KEYS
    for key in env_keys:
        token = str(os.environ.get(key) or "").strip()
        if token:
            return token
    raise RuntimeError(
        "Remote audit requires a bearer token in one of: "
        + ", ".join(REMOTE_AUDIT_TOKEN_ENV_KEYS)
    )


def _github_actions_headers() -> dict[str, str]:
    headers = {}
    values = {
        "X-GitHub-Repository": os.environ.get("GITHUB_REPOSITORY"),
        "X-GitHub-Run-Id": os.environ.get("GITHUB_RUN_ID"),
        "X-GitHub-Workflow": os.environ.get("GITHUB_WORKFLOW"),
    }
    for key, value in values.items():
        normalized = str(value or "").strip()
        if normalized:
            headers[key] = normalized
    return headers


def fetch_remote_audit(base_url: str, *, token_env: str = "", timeout_seconds: float = 30.0) -> dict:
    url = _remote_audit_url(base_url)
    token = _remote_bearer_token(token_env)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            **_github_actions_headers(),
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Remote audit response must be a JSON object.")
    return payload


def _print_summary(audit: dict) -> None:
    readiness = audit.get("operationalReadiness") or {}
    environment = audit.get("environment") or {}
    counts = audit.get("counts") or {}
    dispatch_policy = audit.get("cafe24DispatchPolicy") or {}
    manual_workflow = audit.get("cafe24ManualWorkflow") or {}
    order_items = audit.get("cafe24OrderItems") or {}
    order_item_summary = order_items.get("summary") or {}
    mappings = audit.get("cafe24Mappings") or {}
    integrations = audit.get("cafe24Integrations") or []
    supplier_groups = audit.get("supplierReadinessByIntegration") or []
    print(f"fetchedAt: {audit.get('fetchedAt') or '-'}")
    print(f"status: {readiness.get('status') or 'unknown'}")
    print(f"message: {readiness.get('message') or ''}")
    print(f"runtime: {environment.get('runtimeMode') or 'unknown'} ({environment.get('runtimeModeSource') or 'unknown'})")
    print(f"database: {environment.get('databaseBackend') or 'unknown'}")
    if environment.get("sqlitePath"):
        print(f"sqlitePath: {environment.get('sqlitePath')}")
    print(
        "counts: "
        f"integrations={counts.get('cafe24_integrations', 0)}, "
        f"mappings={counts.get('cafe24_supplier_mappings', 0)}, "
        f"orderItems={counts.get('cafe24_order_items', 0)}, "
        f"suppliers={counts.get('suppliers', 0)}, "
        f"services={counts.get('supplier_services', 0)}"
    )
    print(f"dispatchPolicy: {dispatch_policy.get('status') or 'unknown'}")
    print(f"dispatchMessage: {dispatch_policy.get('message') or ''}")
    print(
        "manualWorkflow: "
        f"{manual_workflow.get('status') or 'unknown'} / "
        f"{manual_workflow.get('nextWorkflow') or '-'} / "
        f"{manual_workflow.get('nextAction') or ''}"
    )
    print(
        "orderItemSummary: "
        f"ready={order_item_summary.get('readyToSubmitCount', 0)}, "
        f"manual={order_item_summary.get('manualInputRequiredCount', 0)}, "
        f"review={order_item_summary.get('reviewRequiredCount', 0)}, "
        f"linked={order_item_summary.get('supplierOrderLinkedCount', 0)}, "
        f"completed={order_item_summary.get('completedCount', 0)}, "
        f"failed={order_item_summary.get('failedCount', 0)}"
    )
    print(
        "mappingSummary: "
        f"enabled={mappings.get('enabled', 0)}, "
        f"autoDispatchEnabled={mappings.get('autoDispatchEnabled', 0)}"
    )
    print("integrations:")
    if integrations:
        for integration in integrations:
            active_label = "active" if integration.get("isActive") else "inactive"
            print(
                "- "
                f"{integration.get('mallId') or '-'}#{integration.get('shopNo') or '-'} "
                f"{active_label} "
                f"token={integration.get('tokenStatus') or '-'} "
                f"autoSubmit={bool(integration.get('autoSubmit'))} "
                f"lastPoll={integration.get('lastPollAt') or '-'} "
                f"lastAutoPoll={integration.get('lastAutoPollStatus') or '-'}"
            )
    else:
        print("- none")
    print("supplierReadinessByIntegration:")
    for group in supplier_groups:
        print(
            "- "
            f"{group.get('label') or group.get('integrationType') or 'unknown'}: "
            f"{group.get('status') or 'unknown'}, "
            f"suppliers={group.get('supplierCount', 0)}, "
            f"ready={group.get('readySupplierCount', 0)}, "
            f"blocked={group.get('blockedSupplierCount', 0)}, "
            f"services={group.get('activeServiceCount', 0)}, "
            f"blockedCodes={','.join(group.get('blockedCodes') or []) or '-'}"
        )
    if manual_workflow.get("manualInputCandidates") or manual_workflow.get("dispatchCandidates"):
        print("workflowCandidates:")
        for candidate in manual_workflow.get("manualInputCandidates") or []:
            print(
                "- manual "
                f"{candidate.get('orderId') or '-'} / {candidate.get('orderItemCode') or '-'} "
                f"next={candidate.get('nextWorkflow') or '-'} "
                f"required={','.join(candidate.get('requiredInputs') or []) or '-'}"
            )
        for candidate in manual_workflow.get("dispatchCandidates") or []:
            print(
                "- dispatch "
                f"{candidate.get('orderId') or '-'} / {candidate.get('orderItemCode') or '-'} "
                f"next={candidate.get('nextWorkflow') or '-'} "
                f"required={','.join(candidate.get('requiredInputs') or []) or '-'}"
            )
    print("checks:")
    for check in readiness.get("checks") or []:
        print(
            f"- [{check.get('status') or 'unknown'}] "
            f"{check.get('key') or 'check'}: {check.get('message') or ''} "
            f"({check.get('value') or '-'})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a redacted Cafe24 operational audit.")
    parser.add_argument("--source", choices=("local", "remote"), default=os.environ.get("SMM_PANEL_AUDIT_SOURCE") or "local")
    parser.add_argument("--base-url", default=os.environ.get("SMM_PANEL_AUDIT_BASE_URL") or "")
    parser.add_argument("--token-env", default=os.environ.get("SMM_PANEL_AUDIT_TOKEN_ENV") or "")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--format", choices=("json", "summary"), default="json")
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    audit = (
        fetch_remote_audit(args.base_url, token_env=args.token_env, timeout_seconds=args.timeout)
        if args.source == "remote"
        else PanelStore().cafe24_operational_audit()
    )
    if args.format == "summary":
        _print_summary(audit)
    else:
        print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
    if args.fail_on_blocked and (audit.get("operationalReadiness") or {}).get("status") == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
