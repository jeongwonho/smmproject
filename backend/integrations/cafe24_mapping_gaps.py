from __future__ import annotations

from typing import Any, Dict, List, Tuple


def cafe24_mapping_gap_key(item: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(item.get("productNo") or "").strip(),
        str(item.get("variantCode") or "").strip(),
        str(item.get("customProductCode") or "").strip(),
    )


def summarize_cafe24_mapping_gaps(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for item in items:
        key = cafe24_mapping_gap_key(item)
        group = groups.setdefault(
            key,
            {
                "productNo": key[0],
                "variantCode": key[1],
                "customProductCode": key[2],
                "count": 0,
                "orderItems": [],
                "optionLabels": [],
                "quantityCandidates": [],
                "errorMessages": [],
                "lastSyncedAt": "",
            },
        )
        group["count"] += 1
        group["orderItems"].append(
            {
                "id": item.get("id") or "",
                "orderId": item.get("orderId") or "",
                "orderItemCode": item.get("orderItemCode") or "",
                "standardStatus": item.get("standardStatus") or "",
                "paymentGateStatus": item.get("paymentGateStatus") or "",
                "lastSyncedAt": item.get("lastSyncedAt") or "",
            }
        )
        if str(item.get("lastSyncedAt") or "") > str(group.get("lastSyncedAt") or ""):
            group["lastSyncedAt"] = item.get("lastSyncedAt") or ""
        for label in item.get("optionLabels") or []:
            if label and label not in group["optionLabels"]:
                group["optionLabels"].append(label)
        for candidate in item.get("quantityCandidates") or []:
            if candidate and candidate not in group["quantityCandidates"]:
                group["quantityCandidates"].append(candidate)
        message = str(item.get("errorMessage") or "").strip()
        if message and message not in group["errorMessages"]:
            group["errorMessages"].append(message)

    return sorted(
        groups.values(),
        key=lambda group: (-int(group["count"] or 0), str(group.get("productNo") or ""), str(group.get("variantCode") or "")),
    )
