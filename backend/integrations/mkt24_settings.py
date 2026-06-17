from __future__ import annotations

from typing import Any, Dict, Optional


class Mkt24SettingsError(ValueError):
    pass


def mkt24_detail_data(payload: Any) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else payload
    return data if isinstance(data, dict) else {}


def mkt24_template_label(entry: Dict[str, Any], fallback: str) -> str:
    options = entry.get("templateOptions", {}) if isinstance(entry, dict) else {}
    if isinstance(options, dict):
        if options.get("label"):
            return str(options.get("label"))
        label_props = options.get("labelProps")
        if isinstance(label_props, dict) and label_props.get("label"):
            return str(label_props.get("label"))
        form_props = options.get("formProps")
        if isinstance(form_props, dict) and form_props.get("label"):
            return str(form_props.get("label"))
    return fallback


def default_mkt24_field_config(detail: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    existing = existing if isinstance(existing, dict) else {}
    form_structure = detail.get("formStructure") if isinstance(detail.get("formStructure"), dict) else {}
    template = form_structure.get("template") if isinstance(form_structure.get("template"), dict) else {}
    schema = form_structure.get("schema") if isinstance(form_structure.get("schema"), dict) else {}
    config: Dict[str, Any] = {}
    for field_key, template_entry in template.items():
        if not isinstance(template_entry, dict):
            continue
        prior = existing.get(field_key) if isinstance(existing.get(field_key), dict) else {}
        rules = schema.get(field_key) if isinstance(schema.get(field_key), list) else []
        field_config = {
            "enabled": bool(prior.get("enabled", True)),
            "required": bool(prior.get("required", "STRING_REQUIRED" in rules or field_key == "orderedCount")),
            "defaultValue": prior.get("defaultValue", ""),
            "inputMode": str(prior.get("inputMode") or "user_input"),
            "label": mkt24_template_label(template_entry, str(field_key)),
            "variant": str(template_entry.get("variant") or "input"),
            "templateOptions": template_entry.get("templateOptions") if isinstance(template_entry.get("templateOptions"), dict) else {},
            "rules": rules,
        }
        if field_key == "orderedCount":
            field_config.update(
                {
                    "min": int(prior.get("min") or detail.get("minAmount") or 1),
                    "max": int(prior.get("max") or detail.get("maxAmount") or detail.get("minAmount") or 1),
                    "step": int(prior.get("step") or detail.get("stepAmount") or 1),
                }
            )
        config[str(field_key)] = field_config
    return config


def default_mkt24_option_config(detail: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    existing = existing if isinstance(existing, dict) else {}
    supports = bool(detail.get("supportsOrderOptions"))
    defaults = existing.get("defaults") if isinstance(existing.get("defaults"), dict) else {}
    return {
        "enabled": bool(existing.get("enabled", supports)),
        "supportsOrderOptions": supports,
        "defaults": defaults,
    }


def validate_mkt24_option_config(option_config: Dict[str, Any], *, supports_order_options: bool) -> Dict[str, Any]:
    if not isinstance(option_config, dict):
        raise Mkt24SettingsError("MKT24 optionInfo 설정 형식이 올바르지 않습니다.")
    defaults = option_config.get("defaults")
    if defaults in (None, ""):
        defaults = {}
    if not isinstance(defaults, dict):
        raise Mkt24SettingsError("optionInfo 기본값은 JSON 객체여야 합니다.")
    enabled = bool(option_config.get("enabled", supports_order_options))
    if enabled and not supports_order_options:
        enabled = False
    return {
        "enabled": enabled,
        "supportsOrderOptions": bool(supports_order_options),
        "defaults": defaults,
    }


def normalize_mkt24_field_config(detail: Dict[str, Any], field_config: Dict[str, Any]) -> Dict[str, Any]:
    defaults = default_mkt24_field_config(detail, field_config)
    normalized: Dict[str, Any] = {}
    for field_key, config in defaults.items():
        incoming = field_config.get(field_key) if isinstance(field_config.get(field_key), dict) else {}
        merged = {**config, **incoming}
        merged["enabled"] = bool(merged.get("enabled", True))
        merged["required"] = bool(merged.get("required", False))
        merged["inputMode"] = str(merged.get("inputMode") or "user_input")
        if merged["inputMode"] not in {"user_input", "admin_default"}:
            merged["inputMode"] = "user_input"
        if field_key == "orderedCount":
            merged["min"] = int(float(merged.get("min") or detail.get("minAmount") or 1))
            merged["max"] = int(float(merged.get("max") or detail.get("maxAmount") or merged["min"]))
            merged["step"] = max(int(float(merged.get("step") or detail.get("stepAmount") or 1)), 1)
            if merged["min"] > merged["max"]:
                raise Mkt24SettingsError("MKT24 수량 최소값은 최대값보다 클 수 없습니다.")
        normalized[field_key] = merged
    return normalized


def resolve_mkt24_field_value(field_key: str, config: Dict[str, Any], user_fields: Dict[str, Any], *, for_preview: bool) -> Any:
    value = None
    if str(config.get("inputMode") or "user_input") == "user_input":
        value = user_fields.get(field_key)
        if value in (None, "") and field_key == "snsValue":
            value = user_fields.get("snsValue") or user_fields.get("targetValue") or user_fields.get("targetUrl") or user_fields.get("targetKeyword")
        if value in (None, "") and field_key == "orderedCount":
            value = user_fields.get("orderedCount")
    if value in (None, ""):
        value = config.get("defaultValue")
    if value in (None, "") and for_preview:
        if field_key == "snsValue":
            return "sample_account"
        if field_key == "orderedCount":
            return config.get("min") or 1
        return f"sample_{field_key}"
    return value


def build_mkt24_order_payload_from_setting(
    detail: Dict[str, Any],
    field_config: Dict[str, Any],
    option_config: Dict[str, Any],
    user_fields: Dict[str, Any],
    *,
    for_preview: bool = False,
) -> Dict[str, Any]:
    if not isinstance(detail, dict):
        raise Mkt24SettingsError("MKT24 상품 상세 정보가 없습니다.")
    product_uuid = str(detail.get("productUuid") or "").strip()
    if not product_uuid:
        raise Mkt24SettingsError("MKT24 상품 UUID가 없습니다.")
    normalized_fields = normalize_mkt24_field_config(detail, field_config)
    normalized_options = validate_mkt24_option_config(
        option_config if isinstance(option_config, dict) else {},
        supports_order_options=bool(detail.get("supportsOrderOptions")),
    )

    order_info: Dict[str, Any] = {}
    ordered_count = None
    for field_key, config in normalized_fields.items():
        if not bool(config.get("enabled", True)):
            continue
        value = resolve_mkt24_field_value(field_key, config, user_fields, for_preview=for_preview)
        if bool(config.get("required")) and value in (None, ""):
            raise Mkt24SettingsError(f"MKT24 필수 입력값이 비어 있습니다: {config.get('label') or field_key}")
        if value in (None, ""):
            continue
        if field_key == "orderedCount":
            try:
                ordered_count = int(value)
            except (TypeError, ValueError) as exc:
                raise Mkt24SettingsError("MKT24 주문 수량은 숫자로 입력해 주세요.") from exc
            min_amount = int(config.get("min") or detail.get("minAmount") or 1)
            max_amount = int(config.get("max") or detail.get("maxAmount") or min_amount)
            step_amount = max(int(config.get("step") or detail.get("stepAmount") or 1), 1)
            if ordered_count < min_amount or ordered_count > max_amount:
                raise Mkt24SettingsError(f"MKT24 주문 수량은 {min_amount}~{max_amount} 범위여야 합니다.")
            if step_amount > 1 and (ordered_count - min_amount) % step_amount != 0:
                raise Mkt24SettingsError(f"MKT24 주문 수량은 {step_amount} 단위로 입력해 주세요.")
            order_info[field_key] = ordered_count
            continue
        order_info[field_key] = value

    if ordered_count is None and "orderedCount" not in normalized_fields:
        fallback_count = user_fields.get("orderedCount")
        if fallback_count not in (None, ""):
            try:
                ordered_count = int(fallback_count)
                order_info["orderedCount"] = ordered_count
            except (TypeError, ValueError) as exc:
                raise Mkt24SettingsError("MKT24 주문 수량은 숫자로 입력해 주세요.") from exc

    value_payload: Dict[str, Any] = {
        "orderInfo": order_info,
        "fullName": str(detail.get("fullName") or detail.get("productName") or detail.get("menuName") or ""),
        "productTypeName": str(detail.get("productTypeName") or ""),
        "isAuto": bool(detail.get("isAuto", False)),
    }
    if ordered_count is not None:
        value_payload["orderedCount"] = ordered_count
        order_info.setdefault("orderedCountRange", [0, 0])
    if normalized_options["enabled"] and normalized_options["defaults"]:
        value_payload["optionInfo"] = normalized_options["defaults"]

    return {
        "productUuid": product_uuid,
        "value": value_payload,
    }
