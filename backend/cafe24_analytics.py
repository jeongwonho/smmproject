from __future__ import annotations

import datetime as dt
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen


ANALYTICS_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
DATA_API_BASE_URL = "https://analyticsdata.googleapis.com/v1beta"

RANGE_OPTIONS = {
    "7d": {"label": "최근 7일", "startDate": "7daysAgo"},
    "14d": {"label": "최근 14일", "startDate": "14daysAgo"},
    "30d": {"label": "최근 30일", "startDate": "30daysAgo"},
    "90d": {"label": "최근 90일", "startDate": "90daysAgo"},
}

TRACKED_EVENTS = [
    "page_view",
    "view_item",
    "add_to_cart",
    "begin_checkout",
    "purchase",
    "contact",
    "instamart_marketing_context",
    "instamart_purchase_candidate_missing",
]


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value.strip()
    return ""


def _analytics_config() -> Dict[str, str]:
    return {
        "propertyId": _env_value("SMM_PANEL_GA4_PROPERTY_ID", "GA4_PROPERTY_ID", "GOOGLE_ANALYTICS_PROPERTY_ID"),
        "clientEmail": _env_value("SMM_PANEL_GOOGLE_SERVICE_ACCOUNT_EMAIL", "GOOGLE_SERVICE_ACCOUNT_EMAIL", "GOOGLE_CLIENT_EMAIL", "GA4_CLIENT_EMAIL"),
        "privateKey": _env_value("SMM_PANEL_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", "GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", "GOOGLE_PRIVATE_KEY", "GA4_PRIVATE_KEY").replace("\\n", "\n"),
    }


def _is_configured(config: Dict[str, str]) -> bool:
    return bool(config.get("propertyId") and config.get("clientEmail") and config.get("privateKey"))


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    return int(round(_number(value)))


def _ratio(numerator: Any, denominator: Any) -> float:
    denominator_value = _number(denominator)
    if denominator_value <= 0:
        return 0.0
    return round(_number(numerator) / denominator_value, 6)


def _metric_ratio(numerator: Any, denominator: Any) -> float:
    denominator_value = _number(denominator)
    if denominator_value <= 0:
        return 0.0
    return round(_number(numerator) / denominator_value, 2)


def _manual_ad_spend() -> Dict[str, Dict[str, float]]:
    raw = _env_value("SMM_PANEL_META_AD_SPEND_JSON", "SMM_PANEL_AD_SPEND_JSON")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    entries: Dict[str, Dict[str, float]] = {}

    def put(key: str, value: Any) -> None:
        normalized_key = str(key or "").strip().lower()
        if not normalized_key:
            return
        if isinstance(value, dict):
            spend = _number(value.get("spend") or value.get("adSpend") or value.get("cost"))
            clicks = _number(value.get("clicks") or value.get("adClicks"))
            impressions = _number(value.get("impressions") or value.get("adImpressions"))
        else:
            spend = _number(value)
            clicks = 0.0
            impressions = 0.0
        entries[normalized_key] = {
            "adSpend": spend,
            "adClicks": clicks,
            "adImpressions": impressions,
        }

    if isinstance(parsed, dict):
        for key, value in parsed.items():
            put(key, value)
    elif isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            source_medium = str(item.get("sourceMedium") or item.get("source") or "").strip()
            campaign = str(item.get("campaign") or item.get("campaignName") or "").strip()
            keys = [item.get("key"), campaign]
            if source_medium and campaign:
                keys.insert(0, f"{source_medium}|{campaign}")
            for key in keys:
                put(str(key or ""), item)
    return entries


def _unavailable_payload(range_id: str = "30d", *, message: str = "", error: str = "") -> Dict[str, Any]:
    selected_range = RANGE_OPTIONS.get(range_id, RANGE_OPTIONS["30d"])
    payload = {
        "source": "unavailable",
        "connected": False,
        "generatedAt": _now_iso(),
        "range": range_id,
        "rangeLabel": selected_range["label"],
        "propertyId": "",
        "message": message or "GA4 연결 정보가 없어 실적 데이터를 표시하지 않습니다.",
        "overview": {
            "sessions": 0,
            "users": 0,
            "events": 0,
            "conversions": 0,
            "revenue": 0,
            "adSpend": 0,
            "roas": 0,
            "costPerPurchase": 0,
            "purchaseCount": 0,
            "averageOrderValue": 0,
        },
        "funnel": [],
        "eventHealth": [],
        "channels": [],
        "pages": [],
        "trend": [],
        "recommendations": [],
        "setupChecklist": _setup_checklist(False, {}, error),
    }
    if error:
        payload["error"] = error
    return payload


def _access_token(config: Dict[str, str]) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except Exception as exc:  # pragma: no cover - exercised only when dependency is missing.
        raise RuntimeError("google-auth와 requests 패키지가 필요합니다.") from exc

    credentials = service_account.Credentials.from_service_account_info(
        {
            "type": "service_account",
            "client_email": config["clientEmail"],
            "private_key": config["privateKey"],
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=[ANALYTICS_SCOPE],
    )
    credentials.refresh(Request())
    return str(credentials.token or "")


def _run_report(
    *,
    property_id: str,
    token: str,
    date_range: Dict[str, str],
    dimensions: Iterable[str] = (),
    metrics: Iterable[str] = (),
    limit: int = 20,
    dimension_filter: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    body = {
        "dateRanges": [{"startDate": date_range["startDate"], "endDate": "today"}],
        "dimensions": [{"name": name} for name in dimensions],
        "metrics": [{"name": name} for name in metrics],
        "limit": limit,
    }
    metric_names = list(metrics)
    if metric_names:
        body["orderBys"] = [{"metric": {"metricName": metric_names[0]}, "desc": True}]
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter

    request = UrlRequest(
        f"{DATA_API_BASE_URL}/properties/{property_id}:runReport",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("error", {}).get("message") or detail
        except json.JSONDecodeError:
            message = detail
        raise RuntimeError(message or "GA4 Data API 요청에 실패했습니다.") from exc
    except URLError as exc:
        raise RuntimeError(f"GA4 Data API 연결에 실패했습니다: {exc.reason}") from exc


def _rows(report: Dict[str, Any], dimensions: List[str], metrics: List[str]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in report.get("rows") or []:
        item: Dict[str, Any] = {}
        for index, name in enumerate(dimensions):
            item[name] = ((row.get("dimensionValues") or [])[index] or {}).get("value", "") if index < len(row.get("dimensionValues") or []) else ""
        for index, name in enumerate(metrics):
            item[name] = _number(((row.get("metricValues") or [])[index] or {}).get("value", 0)) if index < len(row.get("metricValues") or []) else 0
        output.append(item)
    return output


def _event_filter() -> Dict[str, Any]:
    return {
        "filter": {
            "fieldName": "eventName",
            "inListFilter": {"values": TRACKED_EVENTS},
        }
    }


def _recommendations(event_counts: Dict[str, int], overview: Dict[str, Any], channels: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    begin_checkout = event_counts.get("begin_checkout", 0)
    purchases = event_counts.get("purchase", 0)
    purchase_missing = event_counts.get("instamart_purchase_candidate_missing", 0)
    paid_channel = next((item for item in channels if any(token in str(item.get("sourceMedium", "")).lower() for token in ("paid", "cpc", "meta", "facebook", "instagram"))), None)
    recs: List[Dict[str, str]] = []

    if begin_checkout > 0 and purchases == 0:
        recs.append({
            "tone": "bad",
            "title": "결제 시작은 있는데 구매 이벤트가 없습니다.",
            "body": "주문완료 URL에서 transaction_id와 value 파싱이 되는지 먼저 확인해야 합니다. 구매가 안 잡히면 캠페인 최적화가 결제시작에 머뭅니다.",
        })
    elif begin_checkout > 0 and _ratio(purchases, begin_checkout) < 0.12:
        recs.append({
            "tone": "warn",
            "title": "결제 시작 이후 이탈이 큽니다.",
            "body": f"결제 시작 {begin_checkout}건 대비 구매 {purchases}건입니다. 옵션 선택, 비회원 결제, 결제수단 노출, 상품 신뢰 문구를 우선 개선하세요.",
        })

    if purchase_missing > 0:
        recs.append({
            "tone": "warn",
            "title": "구매완료 후보는 감지됐지만 purchase 발화가 막힌 건이 있습니다.",
            "body": "주문번호 또는 결제금액 파싱 실패가 발생한 상태입니다. Cafe24 주문완료 페이지 DOM 기준으로 파서를 보강해야 합니다.",
        })

    if paid_channel and _number(paid_channel.get("conversions")) > 0:
        recs.append({
            "tone": "good",
            "title": "유료 유입에서 구매 신호가 있습니다.",
            "body": f"{paid_channel.get('sourceMedium')} / {paid_channel.get('campaign')}에서 전환이 잡힙니다. 소재별 UTM을 더 촘촘히 나누면 GA 기준 승자 소재를 분리할 수 있습니다.",
        })

    if _number(overview.get("revenue")) <= 0:
        recs.append({
            "tone": "neutral",
            "title": "GA 매출값이 아직 비어 있습니다.",
            "body": "purchase 이벤트에 value, currency, transaction_id가 들어가는지 DebugView에서 실제 주문 1건으로 검증하세요.",
        })

    return recs[:4]


def _setup_checklist(connected: bool, event_counts: Dict[str, int], error: str = "") -> List[Dict[str, str]]:
    return [
        {
            "label": "GA4 Data API 연결",
            "status": "완료" if connected else "대기",
            "detail": "서비스 계정으로 Data API 응답 수신" if connected else (error or "GA4 property id, 서비스 계정 이메일, private key 필요"),
        },
        {
            "label": "Cafe24 Head 브릿지",
            "status": "확인 필요",
            "detail": "UTM 저장, begin_checkout, purchase 후보, contact dataLayer push",
        },
        {
            "label": "결제시작 이벤트",
            "status": "완료" if event_counts.get("begin_checkout", 0) > 0 else "확인 필요",
            "detail": f"{event_counts.get('begin_checkout', 0)}건 수집" if event_counts.get("begin_checkout", 0) > 0 else "orderform.html 진입 테스트 필요",
        },
        {
            "label": "구매 이벤트",
            "status": "완료" if event_counts.get("purchase", 0) > 0 else "확인 필요",
            "detail": f"{event_counts.get('purchase', 0)}건 수집" if event_counts.get("purchase", 0) > 0 else "실제 주문완료 페이지에서 transaction_id/value 확인 필요",
        },
        {
            "label": "광고비/ROAS",
            "status": "확인 필요",
            "detail": "GA4 광고비 metric, Meta API, 또는 SMM_PANEL_META_AD_SPEND_JSON 연결 필요",
        },
    ]


def _build_payload(range_id: str, range_label: str, property_id: str, reports: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    event_rows = _rows(reports["events"], ["eventName"], ["eventCount", "totalUsers", "totalRevenue", "conversions"])
    event_counts = {str(row.get("eventName")): _int(row.get("eventCount")) for row in event_rows}
    overview_row = (_rows(reports["overview"], [], ["sessions", "totalUsers", "eventCount", "conversions", "totalRevenue"]) or [{}])[0]
    purchase_count = event_counts.get("purchase", 0)
    revenue = _int(overview_row.get("totalRevenue"))
    cost_rows = _rows(
        reports.get("channelCosts", {}),
        ["sessionSourceMedium", "sessionCampaignName"],
        ["advertiserAdCost", "advertiserAdClicks", "advertiserAdImpressions"],
    )
    manual_spend = _manual_ad_spend()
    cost_lookup: Dict[tuple[str, str], Dict[str, float]] = {
        (
            str(row.get("sessionSourceMedium") or "(not set)").strip().lower(),
            str(row.get("sessionCampaignName") or "(not set)").strip().lower(),
        ): {
            "adSpend": _number(row.get("advertiserAdCost")),
            "adClicks": _number(row.get("advertiserAdClicks")),
            "adImpressions": _number(row.get("advertiserAdImpressions")),
        }
        for row in cost_rows
    }
    channel_rows = _rows(
        reports["channels"],
        ["sessionSourceMedium", "sessionCampaignName"],
        ["sessions", "totalUsers", "conversions", "totalRevenue", "eventCount"],
    )
    channels: List[Dict[str, Any]] = []
    for row in channel_rows:
        source_medium = row.get("sessionSourceMedium") or "(not set)"
        campaign = row.get("sessionCampaignName") or "(not set)"
        lookup_key = (str(source_medium).strip().lower(), str(campaign).strip().lower())
        spend_data = cost_lookup.get(lookup_key, {})
        manual_data = (
            manual_spend.get(f"{lookup_key[0]}|{lookup_key[1]}")
            or manual_spend.get(lookup_key[1])
            or manual_spend.get(lookup_key[0])
            or {}
        )
        ad_spend = _number(spend_data.get("adSpend")) or _number(manual_data.get("adSpend"))
        conversions = _int(row.get("conversions"))
        channel_revenue = _int(row.get("totalRevenue"))
        channels.append({
            "sourceMedium": source_medium,
            "campaign": campaign,
            "sessions": _int(row.get("sessions")),
            "users": _int(row.get("totalUsers")),
            "conversions": conversions,
            "revenue": channel_revenue,
            "conversionRate": _ratio(row.get("conversions"), row.get("sessions")),
            "adSpend": round(ad_spend),
            "adClicks": _int(spend_data.get("adClicks") or manual_data.get("adClicks")),
            "adImpressions": _int(spend_data.get("adImpressions") or manual_data.get("adImpressions")),
            "roas": _metric_ratio(channel_revenue, ad_spend),
            "cpa": round(ad_spend / conversions) if ad_spend and conversions else 0,
        })
    total_ad_spend = sum(_number(channel.get("adSpend")) for channel in channels)
    overview = {
        "sessions": _int(overview_row.get("sessions")),
        "users": _int(overview_row.get("totalUsers")),
        "events": _int(overview_row.get("eventCount")),
        "conversions": _int(overview_row.get("conversions")),
        "revenue": revenue,
        "adSpend": round(total_ad_spend),
        "roas": _metric_ratio(revenue, total_ad_spend),
        "costPerPurchase": round(total_ad_spend / purchase_count) if total_ad_spend and purchase_count else 0,
        "purchaseCount": purchase_count,
        "averageOrderValue": round(revenue / purchase_count) if purchase_count else 0,
    }
    pages = [
        {
            "path": row.get("pagePath") or "(not set)",
            "views": _int(row.get("screenPageViews")),
            "users": _int(row.get("totalUsers")),
            "conversions": _int(row.get("conversions")),
            "revenue": _int(row.get("totalRevenue")),
        }
        for row in _rows(reports["pages"], ["pagePath"], ["screenPageViews", "totalUsers", "conversions", "totalRevenue"])
    ]
    trend = [
        {
            "date": row.get("date") or "",
            "sessions": _int(row.get("sessions")),
            "users": _int(row.get("totalUsers")),
            "conversions": _int(row.get("conversions")),
            "revenue": _int(row.get("totalRevenue")),
        }
        for row in _rows(reports["trend"], ["date"], ["sessions", "totalUsers", "conversions", "totalRevenue"])
    ]
    trend.sort(key=lambda item: item["date"])

    max_funnel = max(event_counts.get("view_item", 0), event_counts.get("page_view", 0), 1)
    funnel = [
        {"key": "view_item", "label": "상품 조회", "count": event_counts.get("view_item", 0), "rate": _ratio(event_counts.get("view_item", 0), max_funnel)},
        {"key": "add_to_cart", "label": "장바구니", "count": event_counts.get("add_to_cart", 0), "rate": _ratio(event_counts.get("add_to_cart", 0), max_funnel)},
        {"key": "begin_checkout", "label": "결제 시작", "count": event_counts.get("begin_checkout", 0), "rate": _ratio(event_counts.get("begin_checkout", 0), max_funnel)},
        {"key": "purchase", "label": "구매", "count": event_counts.get("purchase", 0), "rate": _ratio(event_counts.get("purchase", 0), max_funnel)},
    ]

    return {
        "source": "ga4",
        "connected": True,
        "generatedAt": _now_iso(),
        "range": range_id,
        "rangeLabel": range_label,
        "propertyId": property_id,
        "overview": overview,
        "funnel": funnel,
        "eventHealth": [
            {
                "eventName": row.get("eventName"),
                "count": _int(row.get("eventCount")),
                "users": _int(row.get("totalUsers")),
                "revenue": _int(row.get("totalRevenue")),
                "conversions": _int(row.get("conversions")),
            }
            for row in event_rows
        ],
        "channels": channels,
        "pages": pages,
        "trend": trend,
        "recommendations": _recommendations(event_counts, overview, channels),
        "setupChecklist": _setup_checklist(True, event_counts),
    }


def get_cafe24_ga4_analytics(range_id: str = "30d") -> Dict[str, Any]:
    range_id = range_id if range_id in RANGE_OPTIONS else "30d"
    selected_range = RANGE_OPTIONS[range_id]
    config = _analytics_config()
    if not _is_configured(config):
        return _unavailable_payload(range_id)

    try:
        token = _access_token(config)
        common = {"property_id": config["propertyId"], "token": token, "date_range": selected_range}
        report_specs = {
            "overview": {"metrics": ["sessions", "totalUsers", "eventCount", "conversions", "totalRevenue"], "limit": 1},
            "events": {"dimensions": ["eventName"], "metrics": ["eventCount", "totalUsers", "totalRevenue", "conversions"], "limit": 30, "dimension_filter": _event_filter()},
            "channels": {"dimensions": ["sessionSourceMedium", "sessionCampaignName"], "metrics": ["sessions", "totalUsers", "conversions", "totalRevenue", "eventCount"], "limit": 12},
            "pages": {"dimensions": ["pagePath"], "metrics": ["screenPageViews", "totalUsers", "conversions", "totalRevenue"], "limit": 12},
            "trend": {"dimensions": ["date"], "metrics": ["sessions", "totalUsers", "conversions", "totalRevenue"], "limit": 120},
            "channelCosts": {"dimensions": ["sessionSourceMedium", "sessionCampaignName"], "metrics": ["advertiserAdCost", "advertiserAdClicks", "advertiserAdImpressions"], "limit": 30},
        }
        with ThreadPoolExecutor(max_workers=len(report_specs)) as executor:
            futures = {
                name: executor.submit(_run_report, **common, **spec)
                for name, spec in report_specs.items()
            }
            reports = {
                name: futures[name].result()
                for name in ("overview", "events", "channels", "pages", "trend")
            }
            try:
                reports["channelCosts"] = futures["channelCosts"].result()
            except Exception:
                reports["channelCosts"] = {}
        if "channelCosts" not in reports:
            reports["channelCosts"] = {}
        return _build_payload(range_id, selected_range["label"], config["propertyId"], reports)
    except Exception as exc:
        return _unavailable_payload(
            range_id,
            message="GA4 API 호출에 실패해 실적 데이터를 표시하지 않습니다.",
            error=str(exc),
        )
