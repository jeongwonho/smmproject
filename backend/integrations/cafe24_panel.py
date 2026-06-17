from __future__ import annotations

from typing import Any, Callable, Dict, List

from ..errors import PanelError
from .cafe24_manual import (
    Cafe24ManualInputError,
    cafe24_manual_expected_quantity,
    cafe24_manual_input_request,
    cafe24_validate_manual_input_order_item,
    cafe24_validate_manual_input_supplier,
)
from .cafe24_preflight import (
    cafe24_expected_quantity_from_payload,
    cafe24_order_item_selector_from_payload,
    cafe24_order_item_selector_has_lookup,
)
from .cafe24_quantity import (
    Cafe24QuantityAmbiguousError,
    coerce_cafe24_ordered_count_mapping_value,
    default_cafe24_ordered_count,
    resolve_cafe24_quantity_candidates,
)


def resolve_cafe24_quantity_candidates_for_panel(
    candidates: List[Dict[str, Any]],
    *,
    ambiguity_policy: str = "needs_manual_review",
) -> str:
    try:
        return resolve_cafe24_quantity_candidates(candidates, ambiguity_policy=ambiguity_policy)
    except Cafe24QuantityAmbiguousError as exc:
        raise PanelError(str(exc)) from exc


def coerce_cafe24_ordered_count_mapping_value_for_panel(value: Any, *, label: str = "", source: str = "") -> str:
    try:
        return coerce_cafe24_ordered_count_mapping_value(value, label=label, source=source)
    except Cafe24QuantityAmbiguousError as exc:
        raise PanelError(str(exc)) from exc


def default_cafe24_ordered_count_for_panel(item_payload: Dict[str, Any], option_entries: List[Dict[str, str]]) -> str:
    try:
        return default_cafe24_ordered_count(item_payload, option_entries)
    except Cafe24QuantityAmbiguousError as exc:
        raise PanelError(str(exc)) from exc


def cafe24_expected_quantity_from_payload_for_panel(payload: Dict[str, Any]) -> int:
    try:
        return cafe24_expected_quantity_from_payload(payload)
    except ValueError as exc:
        raise PanelError(str(exc), status=400) from exc


def cafe24_order_item_selector_for_panel(
    payload: Dict[str, Any],
    *,
    default_shop_no: int = 1,
    required_message: str = "Cafe24 품주 id 또는 mall/order/order_item_code가 필요합니다.",
) -> Dict[str, Any]:
    selector = cafe24_order_item_selector_from_payload(payload, default_shop_no=default_shop_no)
    if not cafe24_order_item_selector_has_lookup(selector):
        raise PanelError(required_message, status=400)
    return selector


def cafe24_order_item_id_for_panel(
    conn: Any,
    selector: Dict[str, Any],
    *,
    missing_message: str = "지정한 Cafe24 주문 품주를 찾을 수 없습니다.",
) -> str:
    item_id = str(selector.get("itemId") or "").strip()
    if item_id:
        return item_id
    row = conn.execute(
        """
        SELECT id
        FROM cafe24_order_items
        WHERE mall_id = ? AND shop_no = ? AND cafe24_order_id = ? AND cafe24_order_item_code = ?
        """,
        (selector["mallId"], selector["shopNo"], selector["orderId"], selector["orderItemCode"]),
    ).fetchone()
    if row is None:
        raise PanelError(missing_message, status=404)
    return str(row["id"])


def validate_cafe24_direct_fields_for_panel(
    fields: Dict[str, Any],
    mapping: Dict[str, Any],
    *,
    looks_like_url: Callable[[str], bool],
    normalize_url: Callable[[str], str | None],
) -> None:
    raw_quantity = fields.get("orderedCount")
    if raw_quantity in (None, ""):
        raise PanelError("수량을 확인할 수 없습니다.")
    try:
        quantity = int(str(raw_quantity).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise PanelError("수량은 숫자로 입력되어야 합니다.") from exc
    if quantity <= 0:
        raise PanelError("수량은 1 이상이어야 합니다.")
    min_amount = int(mapping.get("supplier_min_amount") or 0)
    max_amount = int(mapping.get("supplier_max_amount") or 0)
    if min_amount and quantity < min_amount:
        raise PanelError(f"공급사 최소 수량({min_amount})보다 작습니다.")
    if max_amount and quantity > max_amount:
        raise PanelError(f"공급사 최대 수량({max_amount})보다 큽니다.")

    target_url = str(fields.get("targetUrl") or "").strip()
    target_value = str(fields.get("targetValue") or "").strip()
    comments = str(fields.get("comments") or "").strip()
    if not target_url and not target_value and not comments:
        raise PanelError("공급사 발주에 필요한 링크 또는 계정 입력값이 없습니다.")
    if target_url and looks_like_url(target_url) and not normalize_url(target_url):
        raise PanelError("대상 URL 형식이 올바르지 않습니다.")
    if target_value and looks_like_url(target_value) and not normalize_url(target_value):
        raise PanelError("대상 URL 형식이 올바르지 않습니다.")


def cafe24_manual_input_request_for_panel(payload: Dict[str, Any], *, default_shop_no: int = 1) -> Dict[str, Any]:
    try:
        return cafe24_manual_input_request(payload, default_shop_no=default_shop_no)
    except Cafe24ManualInputError as exc:
        raise PanelError(str(exc), status=getattr(exc, "status", 400)) from exc


def cafe24_manual_expected_quantity_for_panel(payload: Dict[str, Any], explicit_expected_quantity: Any = 0) -> int:
    try:
        return cafe24_manual_expected_quantity(payload, explicit_expected_quantity)
    except Cafe24ManualInputError as exc:
        raise PanelError(str(exc), status=getattr(exc, "status", 400)) from exc


def cafe24_validate_manual_input_order_item_for_panel(row: Any) -> None:
    try:
        cafe24_validate_manual_input_order_item(row)
    except Cafe24ManualInputError as exc:
        raise PanelError(str(exc), status=getattr(exc, "status", 400)) from exc


def cafe24_validate_manual_input_supplier_for_panel(supplier_row: Any, service_row: Any) -> None:
    try:
        cafe24_validate_manual_input_supplier(supplier_row, service_row)
    except Cafe24ManualInputError as exc:
        raise PanelError(str(exc), status=getattr(exc, "status", 400)) from exc
