from __future__ import annotations

import re
from typing import Any, Dict, List

from .cafe24 import cafe24_payload_value


class Cafe24QuantityAmbiguousError(ValueError):
    pass


def cafe24_quantity_candidates_from_text(text: Any, *, label: str = "", source: str = "") -> List[Dict[str, Any]]:
    raw_text = str(text or "").strip()
    if not raw_text:
        return []
    cleaned = re.sub(r"\([^)]*[+-]?\s*\d[\d,]*(?:\.\d+)?\s*원[^)]*\)", " ", raw_text)
    cleaned = re.sub(r"[+-]\s*\d[\d,]*(?:\.\d+)?\s*원", " ", cleaned)
    candidates: List[Dict[str, Any]] = []

    def add(value: float, raw: str, unit: str) -> None:
        parsed = int(value)
        if parsed > 0:
            candidates.append({"value": parsed, "raw": raw.strip(), "unit": unit, "label": label, "source": source})

    for match in re.finditer(r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*([kK])\b", cleaned):
        add(float(match.group(1)) * 1000, match.group(0), match.group(2))

    quantity_units = "명|개|회|건|뷰|팔로워|팔로워수|조회|조회수|좋아요|구독|구독자|댓글|저장|유입"
    for match in re.finditer(rf"(?<![A-Za-z0-9])(\d[\d,]*(?:\.\d+)?)\s*({quantity_units})", cleaned, re.IGNORECASE):
        add(float(match.group(1).replace(",", "")), match.group(0), match.group(2))

    label_has_quantity_hint = any(
        token in str(label or "").lower()
        for token in ("수량", "팔로워", "조회", "좋아요", "구독", "댓글", "저장", "유입", "quantity", "count")
    )
    if label_has_quantity_hint and not candidates:
        numeric = re.fullmatch(r"\s*(\d[\d,]*(?:\.\d+)?)\s*", cleaned)
        if numeric:
            add(float(numeric.group(1).replace(",", "")), numeric.group(0), "")
    deduped: Dict[int, Dict[str, Any]] = {}
    for candidate in candidates:
        deduped.setdefault(int(candidate["value"]), candidate)
    return list(deduped.values())


def cafe24_quantity_candidates_from_options(
    option_entries: List[Dict[str, str]],
    *,
    label: str = "",
) -> List[Dict[str, Any]]:
    needle = str(label or "").strip().lower()
    matches = [
        entry
        for entry in option_entries
        if not needle or needle in str(entry.get("label") or "").lower()
    ]
    candidates: List[Dict[str, Any]] = []
    for entry in matches:
        candidates.extend(
            cafe24_quantity_candidates_from_text(
                entry.get("value"),
                label=str(entry.get("label") or ""),
                source=str(entry.get("source") or ""),
            )
        )
    if needle and not candidates:
        for entry in option_entries:
            candidates.extend(
                cafe24_quantity_candidates_from_text(
                    entry.get("value"),
                    label=str(entry.get("label") or ""),
                    source=str(entry.get("source") or ""),
                )
            )
    deduped: Dict[int, Dict[str, Any]] = {}
    for candidate in candidates:
        deduped.setdefault(int(candidate["value"]), candidate)
    return list(deduped.values())


def resolve_cafe24_quantity_candidates(
    candidates: List[Dict[str, Any]],
    *,
    ambiguity_policy: str = "needs_manual_review",
) -> str:
    unique = sorted({int(candidate["value"]) for candidate in candidates if int(candidate.get("value") or 0) > 0})
    if not unique:
        return ""
    if len(unique) == 1:
        return str(unique[0])
    policy = str(ambiguity_policy or "needs_manual_review").strip()
    if policy in {"largest", "max"}:
        return str(max(unique))
    if policy in {"first", "first_match"}:
        return str(int(candidates[0]["value"]))
    labels = ", ".join(str(value) for value in unique)
    raise Cafe24QuantityAmbiguousError(f"Cafe24 옵션 수량 후보가 여러 개입니다({labels}). 관리자 검수가 필요합니다.")


def coerce_cafe24_ordered_count_mapping_value(value: Any, *, label: str = "", source: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"\d[\d,]*", text):
        return str(int(text.replace(",", "")))
    candidates = cafe24_quantity_candidates_from_text(text, label=label, source=source)
    if candidates:
        return resolve_cafe24_quantity_candidates(candidates)
    return text


def default_cafe24_ordered_count(item_payload: Dict[str, Any], option_entries: List[Dict[str, str]]) -> str:
    candidates = cafe24_quantity_candidates_from_options(option_entries)
    if candidates:
        try:
            return resolve_cafe24_quantity_candidates(candidates)
        except Cafe24QuantityAmbiguousError as exc:
            raise Cafe24QuantityAmbiguousError(f"{exc} Cafe24 매핑에서 주문 수량 source를 명시해 주세요.") from exc
    return cafe24_payload_value(item_payload, ("quantity", "qty", "order_quantity")) or "1"
