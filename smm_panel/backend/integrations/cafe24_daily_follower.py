from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from .cafe24 import (
    cafe24_enriched_product_payload,
    cafe24_product_variants_from_payload,
    cafe24_products_from_payload,
)


DAILY_FOLLOWER_PRODUCT_NO = "51"
DAILY_FOLLOWER_PRODUCT_CODE = "P00000BZ"
DAILY_FOLLOWER_PRODUCT_NAME = "[데일리] 한국인 팔로워 늘리기"
DAILY_FOLLOWER_DESCRIPTION_MARKER = "INSTAMART_DAILY_FOLLOWER_V1"
DAILY_FOLLOWER_BASE_PRICE = 44_800
DAILY_FOLLOWER_SUPPLIER_SERVICE_ID = "40000"
DAILY_FOLLOWER_ADDITIONAL_OPTION_NAME = "인스타그램 프로필 URL"
DAILY_FOLLOWER_OPTION_MATRIX = {
    "1일 유입수량": ["50명", "100명", "250명", "500명"],
    "반복 횟수": ["5회", "10회"],
}
DAILY_FOLLOWER_DAILY_QUANTITIES = (50, 100, 250, 500)
DAILY_FOLLOWER_VARIANTS = [
    {"variantCode": "P00000BZ00CV", "dailyQuantity": "50명", "repeatCount": "5회", "additionalAmount": 0},
    {"variantCode": "P00000BZ00CW", "dailyQuantity": "50명", "repeatCount": "10회", "additionalAmount": 45_000},
    {"variantCode": "P00000BZ00CX", "dailyQuantity": "100명", "repeatCount": "5회", "additionalAmount": 45_000},
    {"variantCode": "P00000BZ00CY", "dailyQuantity": "100명", "repeatCount": "10회", "additionalAmount": 135_000},
    {"variantCode": "P00000BZ00CZ", "dailyQuantity": "250명", "repeatCount": "5회", "additionalAmount": 180_000},
    {"variantCode": "P00000BZ00DA", "dailyQuantity": "250명", "repeatCount": "10회", "additionalAmount": 405_000},
    {"variantCode": "P00000BZ00DB", "dailyQuantity": "500명", "repeatCount": "5회", "additionalAmount": 405_000},
    {"variantCode": "P00000BZ00DC", "dailyQuantity": "500명", "repeatCount": "10회", "additionalAmount": 855_000},
]


def _daily_follower_description() -> str:
    return f"""<meta charset="UTF-8">
<span style="display:none;">{DAILY_FOLLOWER_DESCRIPTION_MARKER}</span>
<div style="width:100%;max-width:800px;margin:0 auto;background:#fff;color:#172033;font-family:Pretendard,-apple-system,BlinkMacSystemFont,system-ui,sans-serif;line-height:1.65;word-break:keep-all;box-sizing:border-box;">
  <section style="padding:54px 24px 46px;border-top:6px solid #ffd84d;border-bottom:1px solid #dce6f2;background:#f4f8ff;text-align:center;">
    <p style="margin:0 0 12px;color:#1e40af;font-size:13px;font-weight:800;">INSTAMART DAILY FOLLOWER</p>
    <h2 style="margin:0;color:#172033;font-size:30px;line-height:1.35;letter-spacing:0;">[데일리] 한국인 팔로워 늘리기</h2>
    <p style="max-width:620px;margin:16px auto 0;color:#4e5968;font-size:17px;">선택한 수량을 한 번에 몰아서 보내지 않고, 선택한 반복 횟수만큼 하루 단위로 나누어 진행합니다.</p>
  </section>
  <section style="padding:42px 24px;border-bottom:1px solid #e5e9ef;">
    <h3 style="margin:0 0 22px;font-size:23px;text-align:center;">진행 방식</h3>
    <div style="padding:18px 0;border-top:1px solid #dce6f2;">
      <strong style="display:block;color:#1e40af;font-size:16px;">1. 옵션 선택</strong>
      <p style="margin:5px 0 0;color:#5f6673;">1일 유입수량과 반복 횟수를 선택합니다. 총 수량은 1일 유입수량 &times; 반복 횟수입니다.</p>
    </div>
    <div style="padding:18px 0;border-top:1px solid #dce6f2;">
      <strong style="display:block;color:#1e40af;font-size:16px;">2. 프로필 확인</strong>
      <p style="margin:5px 0 0;color:#5f6673;">공개 상태의 인스타그램 프로필 URL을 입력합니다. 비밀번호는 필요하지 않습니다.</p>
    </div>
    <div style="padding:18px 0;border-top:1px solid #dce6f2;border-bottom:1px solid #dce6f2;">
      <strong style="display:block;color:#1e40af;font-size:16px;">3. 하루 단위 분할 진행</strong>
      <p style="margin:5px 0 0;color:#5f6673;">결제 완료 후 자동 검수를 거쳐 첫 회차가 순차 시작되고, 남은 회차는 하루 단위 일정으로 진행됩니다.</p>
    </div>
  </section>
  <section style="padding:34px 24px;border-bottom:1px solid #e5e9ef;background:#fffdf4;text-align:center;">
    <p style="margin:0;color:#6b5a16;font-size:14px;font-weight:700;">수량 계산 예시</p>
    <strong style="display:block;margin-top:8px;color:#172033;font-size:24px;">100명 &times; 10회 = 총 1,000명</strong>
  </section>
  <section style="padding:42px 24px;border-bottom:1px solid #e5e9ef;">
    <img src="https://insta-mart.co.kr/web/upload/NNEditor/20260605/copy-1780646050-instamart-profile-01.png" alt="인스타그램 공개 프로필 입력 예시" style="display:block;width:100%;max-width:520px;height:auto;margin:0 auto;border:1px solid #dce6f2;border-radius:8px;">
    <p style="margin:12px 0 0;color:#7a8798;text-align:center;font-size:13px;">주문할 공개 프로필의 전체 URL을 정확히 입력해 주세요.</p>
  </section>
  <section style="padding:42px 24px;">
    <h3 style="margin:0 0 16px;font-size:22px;">주문 전 확인</h3>
    <ul style="margin:0;padding-left:20px;color:#4e5968;">
      <li style="margin-bottom:8px;">작업 기간에는 계정을 공개 상태로 유지해 주세요.</li>
      <li style="margin-bottom:8px;">진행 중 사용자명이나 프로필 URL을 변경하면 다음 회차가 실패할 수 있습니다.</li>
      <li style="margin-bottom:8px;">다른 팔로워 서비스를 동시에 사용하면 수량 확인과 이력 구분이 어려울 수 있습니다.</li>
      <li style="margin-bottom:8px;">첫 발주가 시작된 뒤에는 자동 작업 특성상 취소나 환불이 제한될 수 있습니다.</li>
      <li>팔로워 수는 플랫폼 이용 및 계정 상태에 따라 자연스럽게 변동할 수 있으며, 별도 이탈 보정은 포함되지 않습니다.</li>
    </ul>
    <p style="margin:22px 0 0;padding:14px 16px;border-left:4px solid #1e40af;background:#f7f9fc;color:#4e5968;font-size:14px;">외부 플랫폼 또는 공급사 상태에 따라 각 회차의 시작 시점은 달라질 수 있습니다.</p>
  </section>
</div>"""


def daily_follower_product_plan() -> Dict[str, Any]:
    description = _daily_follower_description()
    variants = []
    for variant in DAILY_FOLLOWER_VARIANTS:
        total_price = DAILY_FOLLOWER_BASE_PRICE + int(variant["additionalAmount"])
        variants.append({**variant, "totalPrice": total_price})
    return {
        "productNo": DAILY_FOLLOWER_PRODUCT_NO,
        "productCode": DAILY_FOLLOWER_PRODUCT_CODE,
        "productName": DAILY_FOLLOWER_PRODUCT_NAME,
        "basePrice": DAILY_FOLLOWER_BASE_PRICE,
        "description": description,
        "mobileDescription": description,
        "summaryDescription": "선택한 한국인 팔로워 수량을 하루 단위로 나누어 진행하는 분할 상품입니다.",
        "additionalOption": {
            "name": DAILY_FOLLOWER_ADDITIONAL_OPTION_NAME,
            "required": "T",
            "textLength": 100,
        },
        "options": DAILY_FOLLOWER_OPTION_MATRIX,
        "variants": variants,
    }


def daily_follower_product_updates() -> Dict[str, Any]:
    plan = daily_follower_product_plan()
    return {
        "product": {
            "display": "F",
            "selling": "F",
            "product_name": DAILY_FOLLOWER_PRODUCT_NAME,
            "price": f"{DAILY_FOLLOWER_BASE_PRICE:.2f}",
            "buy_unit_type": "O",
            "buy_unit": 1,
            "order_quantity_limit_type": "O",
            "minimum_quantity": 1,
            "maximum_quantity": 1,
            "description": plan["description"],
            "mobile_description": plan["mobileDescription"],
            "summary_description": plan["summaryDescription"],
        },
        "options": {
            "use_additional_option": "T",
            "additional_options": [
                {
                    "additional_option_name": DAILY_FOLLOWER_ADDITIONAL_OPTION_NAME,
                    "additional_option_text_length": 100,
                    "required_additional_option": "T",
                }
            ],
        },
        "variants": [
            {
                "variant_code": variant["variantCode"],
                "display": "T",
                "selling": "T",
                "additional_amount": f"{int(variant['additionalAmount']):.2f}",
            }
            for variant in DAILY_FOLLOWER_VARIANTS
        ],
    }


def _decimal(value: Any) -> Optional[Decimal]:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _option_resource(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    resource = payload.get("option")
    if isinstance(resource, dict):
        return resource
    if isinstance(resource, list) and resource and isinstance(resource[0], dict):
        return resource[0]
    return payload


def validate_daily_follower_snapshot(
    product_response: Any,
    option_response: Any,
    variant_response: Any,
    *,
    configured: bool,
    activated: Optional[bool] = None,
) -> Dict[str, Any]:
    blockers: List[str] = []
    product_rows = cafe24_products_from_payload(product_response)
    if not product_rows:
        return {"blockers": ["Cafe24 상품 51을 찾지 못했습니다."], "product": {}, "optionResource": {}}

    raw_product = product_rows[0]
    product = cafe24_enriched_product_payload(
        raw_product,
        option_response=option_response,
        variant_response=variant_response,
        include_raw=False,
    )
    if str(product.get("productNo") or "") != DAILY_FOLLOWER_PRODUCT_NO:
        blockers.append("Cafe24 상품번호가 51이 아닙니다.")
    if str(product.get("productCode") or "") != DAILY_FOLLOWER_PRODUCT_CODE:
        blockers.append("Cafe24 상품코드가 P00000BZ가 아닙니다.")
    if str(product.get("productName") or "") != DAILY_FOLLOWER_PRODUCT_NAME:
        blockers.append("Cafe24 상품명이 데일리 한국인 팔로워 상품과 일치하지 않습니다.")

    observed_options = {
        str(option.get("name") or ""): [str(value) for value in option.get("values") or []]
        for option in product.get("options") or []
    }
    for option_name, expected_values in DAILY_FOLLOWER_OPTION_MATRIX.items():
        if observed_options.get(option_name) != expected_values:
            blockers.append(f"{option_name} 옵션값이 예상 구성과 다릅니다.")

    raw_variants = cafe24_product_variants_from_payload(variant_response)
    observed_variants = {str(variant.get("variant_code") or ""): variant for variant in raw_variants}
    expected_codes = {str(variant["variantCode"]) for variant in DAILY_FOLLOWER_VARIANTS}
    if set(observed_variants) != expected_codes:
        blockers.append("Cafe24 품목 8개의 코드 구성이 예상값과 다릅니다.")
    for expected in DAILY_FOLLOWER_VARIANTS:
        variant_code = str(expected["variantCode"])
        raw_variant = observed_variants.get(variant_code)
        if raw_variant is None:
            continue
        option_pairs = {
            str(item.get("name") or ""): str(item.get("value") or "")
            for item in raw_variant.get("options") or []
            if isinstance(item, dict)
        }
        if option_pairs.get("1일 유입수량") != expected["dailyQuantity"] or option_pairs.get("반복 횟수") != expected["repeatCount"]:
            blockers.append(f"{variant_code} 품목의 옵션 조합이 예상값과 다릅니다.")
        if configured:
            if _decimal(raw_variant.get("additional_amount")) != Decimal(int(expected["additionalAmount"])):
                blockers.append(f"{variant_code} 품목 추가금액이 예상값과 다릅니다.")
            if str(raw_variant.get("display") or "") != "T" or str(raw_variant.get("selling") or "") != "T":
                blockers.append(f"{variant_code} 품목이 진열/판매 가능 상태가 아닙니다.")

    option_resource = _option_resource(option_response)
    if configured:
        if _decimal(raw_product.get("price")) != Decimal(DAILY_FOLLOWER_BASE_PRICE):
            blockers.append("Cafe24 기본 판매가가 44,800원이 아닙니다.")
        if int(raw_product.get("minimum_quantity") or 0) != 1 or int(raw_product.get("maximum_quantity") or 0) != 1:
            blockers.append("Cafe24 주문 수량이 1개로 제한되어 있지 않습니다.")
        if DAILY_FOLLOWER_DESCRIPTION_MARKER not in str(raw_product.get("description") or ""):
            blockers.append("Cafe24 PC 상품 설명이 데일리 팔로워 설명으로 교체되지 않았습니다.")
        if DAILY_FOLLOWER_DESCRIPTION_MARKER not in str(raw_product.get("mobile_description") or ""):
            blockers.append("Cafe24 모바일 상품 설명이 데일리 팔로워 설명으로 교체되지 않았습니다.")
        additional_options = option_resource.get("additional_options") or option_resource.get("additional_option") or []
        expected_additional_option = {
            "additional_option_name": DAILY_FOLLOWER_ADDITIONAL_OPTION_NAME,
            "additional_option_text_length": 100,
            "required_additional_option": "T",
        }
        normalized_additional_options = [
            {
                "additional_option_name": str(item.get("additional_option_name") or ""),
                "additional_option_text_length": int(item.get("additional_option_text_length") or 0),
                "required_additional_option": str(item.get("required_additional_option") or ""),
            }
            for item in additional_options
            if isinstance(item, dict)
        ]
        if str(option_resource.get("use_additional_option") or "") != "T" or normalized_additional_options != [expected_additional_option]:
            blockers.append("필수 입력값 '인스타그램 프로필 URL' 설정이 올바르지 않습니다.")

    if activated is not None:
        expected_status = "T" if activated else "F"
        if str(raw_product.get("display") or "") != expected_status or str(raw_product.get("selling") or "") != expected_status:
            blockers.append("Cafe24 상품 진열/판매 상태가 요청값과 다릅니다.")

    return {"blockers": list(dict.fromkeys(blockers)), "product": product, "optionResource": option_resource}
