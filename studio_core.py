#!/usr/bin/env python3
from __future__ import annotations

import base64
import html
import ipaddress
import json
import os
import queue
import random
import re
import shutil
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = PROJECT_ROOT / "studio_data"
ASSET_DIR = RUNTIME_DIR / "assets"
EXPORT_DIR = RUNTIME_DIR / "exports"
DB_PATH = RUNTIME_DIR / "brand_grid_studio.db"
SETTINGS_PATH = RUNTIME_DIR / "settings.json"

DEFAULT_PORT = 8010
PRIVATE_CIDRS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

STOPWORDS = {
    "브랜드",
    "프로젝트",
    "서비스",
    "이미지",
    "그리드",
    "인스타그램",
    "스토리",
    "제품",
    "콘텐츠",
    "디자인",
    "운영",
    "내부",
    "기획",
    "광고",
    "프로모션",
    "우리",
    "위한",
    "위해",
    "사용",
    "중심",
    "기반",
    "대한",
    "있는",
    "없는",
    "보다",
    "하고",
    "합니다",
    "입니다",
    "있습니다",
    "추천",
    "필수",
    "금지",
    "타깃",
}

COLOR_NAME_HEX = {
    "white": "#f7f5f1",
    "black": "#141414",
    "gray": "#7a7d82",
    "grey": "#7a7d82",
    "charcoal": "#2e3338",
    "navy": "#31435d",
    "blue": "#4a6d8f",
    "sky": "#8da8c2",
    "green": "#64826e",
    "olive": "#79815a",
    "beige": "#d9c8ae",
    "sand": "#d0bea2",
    "brown": "#8d6a4f",
    "pink": "#d39faa",
    "red": "#bb6159",
    "orange": "#cf8a52",
    "yellow": "#dfc072",
    "gold": "#bda166",
    "purple": "#7f6c9e",
    "violet": "#7f6c9e",
    "teal": "#597f7a",
    "mint": "#8cb6a1",
}

INDUSTRY_PRESETS = {
    "beauty": {
        "match": ["뷰티", "화장품", "스킨", "메이크업", "에스테틱", "미용"],
        "tone_keywords": ["정제된", "클린", "피부결", "모노톤", "소프트 라이트"],
        "triplets": [
            {"label": "브랜드 온보딩", "tone": "미니멀하고 깨끗한 첫인상", "roles": ["후킹", "브랜드 가치", "전환"]},
            {"label": "서비스 디테일", "tone": "텍스처와 디테일 강조", "roles": ["문제 제기", "솔루션", "제품"]},
            {"label": "신뢰 강화", "tone": "리뷰와 결과 중심", "roles": ["후기", "FAQ", "CTA"]},
            {"label": "캠페인 확장", "tone": "시즌성 강조", "roles": ["프로모션", "라이프스타일", "전환"]},
        ],
    },
    "food": {
        "match": ["식음료", "푸드", "레스토랑", "카페", "베이커리", "음식"],
        "tone_keywords": ["따뜻한", "식감 중심", "클로즈업", "웜그레이", "브랜드 스토리"],
        "triplets": [
            {"label": "브랜드 시그니처", "tone": "향과 온기 중심", "roles": ["후킹", "시그니처", "CTA"]},
            {"label": "메뉴/서비스", "tone": "텍스처와 디테일", "roles": ["메뉴 소개", "재료", "혜택"]},
            {"label": "신뢰/리뷰", "tone": "현장감과 후기", "roles": ["후기", "공간", "전환"]},
            {"label": "캠페인 확장", "tone": "이벤트/시즌 테마", "roles": ["이벤트", "교육", "CTA"]},
        ],
    },
    "healthcare": {
        "match": ["의료", "치과", "피부과", "병원", "클리닉", "헬스케어"],
        "tone_keywords": ["신뢰감", "청결함", "차분한 블루그레이", "넓은 여백", "정확성"],
        "triplets": [
            {"label": "신뢰 형성", "tone": "차분하고 전문적인 첫인상", "roles": ["후킹", "전문성", "전환"]},
            {"label": "서비스 설명", "tone": "명료한 정보 전달", "roles": ["문제 제기", "프로세스", "서비스"]},
            {"label": "검증/리뷰", "tone": "증거 기반 스토리", "roles": ["후기", "FAQ", "CTA"]},
            {"label": "캠페인 확장", "tone": "시즌/이벤트 강조", "roles": ["프로모션", "교육", "예약"]},
        ],
    },
    "education": {
        "match": ["교육", "학원", "러닝", "강의", "학교", "코칭"],
        "tone_keywords": ["명료한", "구조적", "신뢰감", "콘트라스트 절제", "에디토리얼"],
        "triplets": [
            {"label": "브랜드 포지션", "tone": "에디토리얼 도입", "roles": ["후킹", "브랜드 소개", "전환"]},
            {"label": "커리큘럼", "tone": "정보와 구조 강조", "roles": ["교육 포인트", "프로세스", "혜택"]},
            {"label": "신뢰/성과", "tone": "사례 중심", "roles": ["후기", "성과", "CTA"]},
            {"label": "캠페인 확장", "tone": "이벤트/시즌 강조", "roles": ["프로모션", "FAQ", "전환"]},
        ],
    },
}

DEFAULT_SETTINGS = {
    "projectBudgetDefault": 30.0,
    "dailyGenerationLimit": 60,
    "internalOnly": True,
    "allowFinalOnlyForSelected": True,
    "routes": {
        "draft": {"label": "Draft", "provider": "mock", "model": "mock-draft", "unitCost": 0.06},
        "final": {"label": "Final", "provider": "mock", "model": "mock-final", "unitCost": 0.24},
        "photo": {"label": "Photo Quality", "provider": "mock", "model": "mock-photo", "unitCost": 0.34},
    },
}

SLOT_ROLE_TEMPLATES = {
    9: [
        "후킹",
        "브랜드 소개",
        "CTA",
        "문제 제기",
        "서비스 설명",
        "혜택",
        "후기",
        "FAQ",
        "전환",
    ],
    12: [
        "후킹",
        "브랜드 소개",
        "CTA",
        "문제 제기",
        "서비스 설명",
        "혜택",
        "후기",
        "FAQ",
        "전환",
        "프로모션",
        "라이프스타일",
        "예약",
    ],
}


class StudioError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def slugify(value: str) -> str:
    lowered = clean_text(value).lower()
    lowered = re.sub(r"[^0-9a-z가-힣]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "project"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]
    if isinstance(value, str):
        parts = re.split(r"[\n,]+", value)
        return [clean_text(item) for item in parts if clean_text(item)]
    return []


def safe_json_loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def default_brief() -> Dict[str, Any]:
    return {
        "projectName": "",
        "client": "",
        "brandName": "",
        "industry": "",
        "owner": "",
        "goal": "",
        "serviceSummary": "",
        "targetAudience": "",
        "homepageUrl": "",
        "instagramUrl": "",
        "requiredKeywords": [],
        "bannedKeywords": [],
        "requiredColors": [],
        "bannedColors": [],
        "references": [],
    }


def default_brand_pack() -> Dict[str, Any]:
    return {
        "overview": "브랜드 입력을 저장한 뒤 자동 분석을 실행하세요.",
        "toneKeywords": [],
        "palette": [],
        "coreVisuals": [],
        "requiredKeywords": [],
        "bannedKeywords": [],
        "locks": {
            "subjectLock": "",
            "styleLock": "",
            "compositionLock": "",
            "negativeLock": "",
        },
        "urlSummaries": [],
        "referenceSummary": [],
        "tripletSuggestions": [],
        "masterTone": "",
        "warnings": ["브랜드 분석이 아직 실행되지 않았습니다."],
        "updatedAt": now_iso(),
    }


def build_triplet_defaults(grid_size: int, industry: str, brand_pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    preset = pick_industry_preset(industry)
    source = preset.get("triplets") if preset else []
    if not source:
        source = [
            {"label": "브랜드 온보딩", "tone": "차분한 첫인상과 브랜드 소개", "roles": ["후킹", "브랜드 소개", "전환"]},
            {"label": "서비스 디테일", "tone": "기능과 혜택 중심", "roles": ["문제 제기", "서비스 설명", "혜택"]},
            {"label": "신뢰 강화", "tone": "리뷰와 FAQ 중심", "roles": ["후기", "FAQ", "CTA"]},
            {"label": "캠페인 확장", "tone": "프로모션과 시즌 메시지", "roles": ["프로모션", "라이프스타일", "전환"]},
        ]

    triplet_count = max(1, grid_size // 3)
    master_tone = clean_text(brand_pack.get("masterTone", ""))
    items = []
    for index in range(triplet_count):
        template = source[index % len(source)]
        items.append(
            {
                "id": f"triplet-{index + 1}",
                "label": template["label"],
                "tone": template["tone"],
                "roles": list(template["roles"]),
                "masterTone": master_tone,
            }
        )
    return items


def default_grid_plan(grid_size: int, industry: str, brand_pack: Dict[str, Any]) -> Dict[str, Any]:
    triplets = build_triplet_defaults(grid_size, industry, brand_pack)
    roles = SLOT_ROLE_TEMPLATES[12 if grid_size == 12 else 9]
    slots = []
    for index in range(grid_size):
        triplet = triplets[index // 3]
        slots.append(
            {
                "id": f"slot-{index + 1}",
                "index": index + 1,
                "tripletId": triplet["id"],
                "role": roles[index],
                "tone": triplet["tone"],
                "locked": False,
                "status": "Draft",
                "selectedVariantId": "",
                "notes": "",
            }
        )
    return {
        "gridSize": grid_size,
        "groupingMode": "row",
        "masterTone": clean_text(brand_pack.get("masterTone", "")),
        "triplets": triplets,
        "slots": slots,
        "warnings": [],
        "updatedAt": now_iso(),
    }


def default_create_one_state() -> Dict[str, Any]:
    return {
        "lastPreset": "Hero",
        "lastRoute": "draft",
        "lastCount": 4,
        "lastDirection": "",
    }


def default_review_state() -> Dict[str, Any]:
    return {
        "projectStatus": "Draft",
        "checklist": [
            {"id": "brand", "label": "Brand Pack 확정", "done": False},
            {"id": "tone", "label": "Triplet tone 확인", "done": False},
            {"id": "similarity", "label": "유사도 경고 해소", "done": False},
            {"id": "approval", "label": "승인 슬롯 잠금", "done": False},
            {"id": "export", "label": "내보내기 전 확인", "done": False},
        ],
    }


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(char * 2 for char in cleaned)
    if len(cleaned) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", cleaned):
        return (104, 119, 137)
    return tuple(int(cleaned[index : index + 2], 16) for index in range(0, 6, 2))


def blend(color: str, amount: float, towards: str = "#ffffff") -> str:
    base = hex_to_rgb(color)
    target = hex_to_rgb(towards)
    mixed = tuple(int(base[index] + (target[index] - base[index]) * amount) for index in range(3))
    return rgb_to_hex(mixed)


def color_brightness(color: str) -> float:
    red, green, blue = hex_to_rgb(color)
    return (red * 299 + green * 587 + blue * 114) / 1000


def pick_industry_preset(industry: str) -> Dict[str, Any]:
    cleaned = clean_text(industry)
    for preset in INDUSTRY_PRESETS.values():
        if any(token in cleaned for token in preset["match"]):
            return preset
    return {}


def normalize_palette(raw_colors: Iterable[str]) -> List[str]:
    palette: List[str] = []
    seen = set()
    for item in raw_colors:
        value = clean_text(item).lower()
        if not value:
            continue
        if value in COLOR_NAME_HEX:
            value = COLOR_NAME_HEX[value]
        if not value.startswith("#"):
            continue
        rgb = rgb_to_hex(hex_to_rgb(value))
        if rgb not in seen:
            seen.add(rgb)
            palette.append(rgb)
    return palette[:6]


def tokenize(value: str) -> List[str]:
    words = re.findall(r"[A-Za-z]{2,}|[가-힣]{2,}", clean_text(value).lower())
    return [word for word in words if word not in STOPWORDS]


def collect_keywords(*chunks: str) -> List[str]:
    counter: Counter[str] = Counter()
    for chunk in chunks:
        counter.update(tokenize(chunk))
    return [word for word, _ in counter.most_common(8)]


def safe_ip(value: str) -> ipaddress._BaseAddress:
    candidate = value
    if value.startswith("::ffff:"):
        candidate = value.split("::ffff:", 1)[1]
    return ipaddress.ip_address(candidate)


def is_allowed_client(
    ip_value: str, extra_cidrs: Optional[Iterable[ipaddress._BaseNetwork]] = None
) -> bool:
    try:
        address = safe_ip(ip_value)
    except ValueError:
        return False
    if address.is_loopback or address.is_private or address.is_link_local:
        return True
    for network in PRIVATE_CIDRS:
        if address in network:
            return True
    if extra_cidrs:
        return any(address in network for network in extra_cidrs)
    return False


def discover_local_ips() -> List[str]:
    results: List[str] = []
    try:
        hostname = socket.gethostname()
        infos = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        for info in infos:
            address = info[4][0]
            try:
                parsed = safe_ip(address)
            except ValueError:
                continue
            if parsed.is_private and address not in results:
                results.append(address)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            if address not in results:
                results.insert(0, address)
    except OSError:
        pass
    return results[:4]


def infer_color_mode(palette: List[str]) -> str:
    if not palette:
        return "모노톤"
    bright = sum(1 for color in palette if color_brightness(color) >= 180)
    cool = sum(1 for color in palette if hex_to_rgb(color)[2] >= hex_to_rgb(color)[0])
    if bright >= max(1, len(palette) // 2):
        return "밝고 여백감 있는 톤"
    if cool >= max(1, len(palette) // 2):
        return "차분한 블루그레이 톤"
    return "따뜻한 뉴트럴 톤"


def fetch_url_summary(url: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(220_000).decode(charset, errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return {"url": url, "status": "unavailable", "title": "", "description": "", "keywords": []}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    meta_match = re.search(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']',
        body,
        re.IGNORECASE | re.DOTALL,
    )
    heading_matches = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", body, re.IGNORECASE | re.DOTALL)
    text_blob = " ".join(re.sub(r"<[^>]+>", " ", chunk) for chunk in heading_matches[:5])
    description = clean_text(meta_match.group(1) if meta_match else text_blob)
    title = clean_text(title_match.group(1) if title_match else url)
    keywords = collect_keywords(title, description)
    return {
        "url": url,
        "status": "ok",
        "title": title,
        "description": description[:220],
        "keywords": keywords,
    }


def infer_reference_kind(name: str, explicit_kind: str = "") -> str:
    value = clean_text(explicit_kind or name).lower()
    pairs = {
        "logo": ["logo", "로고"],
        "product": ["product", "상품", "제품"],
        "person": ["person", "model", "인물", "사람"],
        "space": ["space", "interior", "공간", "실내"],
        "feed": ["feed", "instagram", "grid", "피드"],
    }
    for label, tokens in pairs.items():
        if any(token in value for token in tokens):
            return label
    return "reference"


def merge_settings(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(base))
    for key, value in updates.items():
        if key == "routes" and isinstance(value, dict):
            for route_name, route_value in value.items():
                if route_name not in merged["routes"] or not isinstance(route_value, dict):
                    continue
                for sub_key in ["label", "provider", "model", "unitCost"]:
                    if sub_key in route_value:
                        merged["routes"][route_name][sub_key] = route_value[sub_key]
        elif key in {"projectBudgetDefault", "dailyGenerationLimit", "internalOnly", "allowFinalOnlyForSelected"}:
            merged[key] = value
    return merged


def decode_data_url(data_url: str) -> Tuple[str, bytes]:
    match = re.match(r"data:([^;]+);base64,(.+)$", data_url or "", re.DOTALL)
    if not match:
        raise StudioError("업로드 이미지 형식이 올바르지 않습니다.")
    mime = match.group(1)
    try:
        raw = base64.b64decode(match.group(2))
    except ValueError as exc:
        raise StudioError("업로드 이미지 디코딩에 실패했습니다.") from exc
    return mime, raw


def extension_for_mime(mime: str) -> str:
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }
    return mapping.get(mime, ".bin")


def xml_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_mock_svg(
    *,
    brand_name: str,
    headline: str,
    subline: str,
    role: str,
    route_label: str,
    palette: List[str],
    seed: int,
) -> str:
    colors = palette[:4] or ["#f4f1ec", "#d0d5db", "#7b8794", "#31435d"]
    while len(colors) < 4:
        colors.append(blend(colors[-1], 0.2))

    rng = random.Random(seed)
    accent = colors[2]
    surface = blend(colors[0], 0.12)
    ink = "#101418" if color_brightness(colors[0]) >= 145 else "#f5f4f0"

    circle_x = rng.randint(720, 980)
    circle_y = rng.randint(120, 320)
    circle_r = rng.randint(130, 210)
    rect_x = rng.randint(80, 220)
    rect_y = rng.randint(680, 820)
    rect_w = rng.randint(520, 720)
    rect_h = rng.randint(280, 360)
    line_y = rng.randint(430, 520)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{colors[0]}"/>
      <stop offset="55%" stop-color="{colors[1]}"/>
      <stop offset="100%" stop-color="{colors[3]}"/>
    </linearGradient>
  </defs>
  <rect width="1080" height="1350" fill="url(#bg)"/>
  <circle cx="{circle_x}" cy="{circle_y}" r="{circle_r}" fill="{blend(colors[2], 0.18)}" opacity="0.82"/>
  <rect x="{rect_x}" y="{rect_y}" rx="42" ry="42" width="{rect_w}" height="{rect_h}" fill="{surface}" opacity="0.88"/>
  <rect x="78" y="{line_y}" width="924" height="2" fill="{blend(accent, 0.42)}" opacity="0.9"/>
  <rect x="78" y="72" rx="999" ry="999" width="188" height="44" fill="{blend(colors[0], 0.18)}"/>
  <text x="116" y="101" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="20" fill="{ink}" letter-spacing="2.4">BRAND GRID</text>
  <text x="84" y="215" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="22" fill="{blend(ink, 0.34, '#ffffff' if ink == '#101418' else '#101418')}" letter-spacing="1.8">{xml_escape(brand_name[:36] or 'Internal Studio')}</text>
  <text x="84" y="358" font-family="Pretendard, Noto Sans KR, sans-serif" font-weight="600" font-size="88" fill="{ink}">
    <tspan x="84" dy="0">{xml_escape(headline[:18])}</tspan>
    <tspan x="84" dy="102">{xml_escape(headline[18:36])}</tspan>
  </text>
  <text x="84" y="588" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="28" fill="{blend(ink, 0.22, '#ffffff' if ink == '#101418' else '#101418')}">{xml_escape(subline[:52])}</text>
  <text x="120" y="{rect_y + 112}" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="26" fill="{ink}" letter-spacing="1.4">{xml_escape(role)}</text>
  <text x="120" y="{rect_y + 180}" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="56" font-weight="600" fill="{ink}">{xml_escape(route_label)}</text>
  <text x="120" y="{rect_y + 244}" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="24" fill="{blend(ink, 0.26, '#ffffff' if ink == '#101418' else '#101418')}">{xml_escape('Mock preview for workflow validation')}</text>
  <rect x="84" y="1204" rx="18" ry="18" width="912" height="92" fill="{blend(colors[3], 0.18)}" opacity="0.9"/>
  <text x="116" y="1261" font-family="Pretendard, Noto Sans KR, sans-serif" font-size="24" fill="{ink}">{xml_escape('Tone: ' + subline[:70])}</text>
</svg>
"""


def write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def route_settings(settings: Dict[str, Any], route: str) -> Dict[str, Any]:
    routes = settings.get("routes", {})
    if route not in routes:
        raise StudioError("지원하지 않는 생성 라우트입니다.")
    value = routes[route]
    return {
        "route": route,
        "label": clean_text(value.get("label", route.title())),
        "provider": clean_text(value.get("provider", "mock")).lower() or "mock",
        "model": clean_text(value.get("model", f"mock-{route}")) or f"mock-{route}",
        "unitCost": float(value.get("unitCost", 0) or 0),
    }


def make_prompt_block(
    project: Dict[str, Any],
    brand_pack: Dict[str, Any],
    scope_type: str,
    scope_key: str,
    role: str,
    route: str,
    direction: str,
) -> Dict[str, Any]:
    brief = project["brief"]
    positive = [
        *brand_pack.get("toneKeywords", [])[:5],
        role,
        infer_color_mode(brand_pack.get("palette", [])),
    ]
    negative = ensure_list(brief.get("bannedKeywords"))
    overview = clean_text(brand_pack.get("overview", ""))
    references = [item.get("name", "") for item in brief.get("references", [])[:4]]
    return {
        "headline": clean_text(role),
        "scopeType": scope_type,
        "scopeKey": scope_key,
        "route": route,
        "direction": clean_text(direction),
        "overview": overview,
        "positivePrompt": positive,
        "negativePrompt": negative,
        "references": references,
        "styleLock": brand_pack.get("locks", {}).get("styleLock", ""),
        "compositionLock": brand_pack.get("locks", {}).get("compositionLock", ""),
    }


def save_mock_asset(project_id: str, variant_id: str, svg: str) -> str:
    relative = Path("studio_data") / "assets" / project_id / "variants" / f"{variant_id}.svg"
    write_text(PROJECT_ROOT / relative, svg)
    return "/" + str(relative).replace(os.sep, "/")


def load_reference_parts(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    parts = []
    for item in project["brief"].get("references", [])[:4]:
        asset_url = clean_text(item.get("assetUrl"))
        if not asset_url:
            continue
        path = PROJECT_ROOT / asset_url.lstrip("/")
        if not path.exists():
            continue
        mime = clean_text(item.get("mimeType")) or "image/jpeg"
        raw = path.read_bytes()
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime,
                    "data": base64.b64encode(raw).decode("ascii"),
                }
            }
        )
    return parts


def call_gemini_image(
    *,
    api_key: str,
    model: str,
    prompt: Dict[str, Any],
    reference_parts: List[Dict[str, Any]],
) -> Tuple[bytes, str, Dict[str, Any]]:
    text = (
        f"Brand overview: {prompt['overview']}\n"
        f"Primary role: {prompt['headline']}\n"
        f"Style lock: {prompt['styleLock']}\n"
        f"Composition lock: {prompt['compositionLock']}\n"
        f"Positive cues: {', '.join(prompt['positivePrompt'])}\n"
        f"Negative cues: {', '.join(prompt['negativePrompt'])}\n"
        f"Direction: {prompt['direction']}\n"
        "Return a clean, brand-consistent vertical Instagram visual."
    ).strip()

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": text}, *reference_parts],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={"Content-Type": "application/json; charset=utf-8"},
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=80) as response:
            raw_response = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise StudioError(f"Gemini 이미지 생성 실패: HTTP {exc.code} {detail[:240]}", status=502) from exc
    except urllib.error.URLError as exc:
        raise StudioError(f"Gemini 이미지 생성 실패: {exc.reason}", status=502) from exc

    candidates = raw_response.get("candidates") or []
    for candidate in candidates:
        parts = ((candidate.get("content") or {}).get("parts") or [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = clean_text(inline.get("mimeType") or inline.get("mime_type") or "image/png")
                return base64.b64decode(inline["data"]), mime, raw_response
    raise StudioError("Gemini 응답에서 이미지 데이터를 찾지 못했습니다.", status=502)


def extract_palette_from_references(references: List[Dict[str, Any]], required_colors: List[str]) -> List[str]:
    palette: List[str] = []
    for item in references:
        palette.extend(ensure_list(item.get("palette", [])))
    palette.extend(required_colors)
    normalized = normalize_palette(palette)
    if normalized:
        return normalized[:5]
    return ["#f1ede6", "#c8d0d8", "#72808e", "#31435d"]


def analyze_brand_pack(project: Dict[str, Any]) -> Dict[str, Any]:
    brief = project["brief"]
    references = brief.get("references", [])
    required_keywords = ensure_list(brief.get("requiredKeywords"))
    banned_keywords = ensure_list(brief.get("bannedKeywords"))
    required_colors = ensure_list(brief.get("requiredColors"))
    banned_colors = ensure_list(brief.get("bannedColors"))
    urls = [clean_text(brief.get("homepageUrl")), clean_text(brief.get("instagramUrl"))]
    url_summaries = [fetch_url_summary(url) for url in urls if url]

    preset = pick_industry_preset(brief.get("industry", ""))
    palette = extract_palette_from_references(references, required_colors)
    color_mode = infer_color_mode(palette)
    reference_summary = []
    for item in references:
        reference_summary.append(
            {
                "name": clean_text(item.get("name")),
                "kind": infer_reference_kind(item.get("name", ""), item.get("kind", "")),
                "palette": normalize_palette(ensure_list(item.get("palette", []))),
                "notes": clean_text(item.get("notes")),
            }
        )

    keyword_pool = collect_keywords(
        brief.get("projectName", ""),
        brief.get("brandName", ""),
        brief.get("goal", ""),
        brief.get("serviceSummary", ""),
        brief.get("targetAudience", ""),
        " ".join(required_keywords),
        " ".join(summary.get("title", "") + " " + summary.get("description", "") for summary in url_summaries),
    )
    tone_keywords = []
    tone_keywords.extend(preset.get("tone_keywords", []))
    tone_keywords.extend(required_keywords[:3])
    tone_keywords.extend(keyword_pool[:4])
    tone_keywords.append(color_mode)
    deduped_tones = []
    for item in tone_keywords:
        cleaned = clean_text(item)
        if cleaned and cleaned not in deduped_tones:
            deduped_tones.append(cleaned)

    core_visuals = []
    kinds = Counter(item["kind"] for item in reference_summary)
    if kinds:
        for kind, _ in kinds.most_common(3):
            label_map = {
                "product": "제품 반복 노출",
                "person": "인물/모델 일관성",
                "space": "공간 톤 유지",
                "logo": "로고 노출 관리",
                "feed": "피드 일관성 유지",
                "reference": "브랜드 레퍼런스 구조화",
            }
            core_visuals.append(label_map.get(kind, kind))
    if not core_visuals:
        core_visuals = ["브랜드 컬러 일관성", "여백 중심 구성", "텍스트 영역 확보"]

    warnings = []
    if not references:
        warnings.append("참조 이미지가 없어 Subject / Style Lock 정확도가 낮을 수 있습니다.")
    if not any(summary.get("status") == "ok" for summary in url_summaries) and any(urls):
        warnings.append("일부 URL 요약을 가져오지 못했습니다. 내부망 환경에서는 수동 요약 입력을 함께 권장합니다.")
    overlap = sorted(set(required_keywords) & set(banned_keywords))
    if overlap:
        warnings.append(f"필수/금지 키워드가 겹칩니다: {', '.join(overlap)}")
    if not brief.get("goal"):
        warnings.append("프로젝트 목표가 비어 있어 Slot Role 추천 정확도가 낮아질 수 있습니다.")

    brand_name = clean_text(brief.get("brandName") or brief.get("projectName") or brief.get("client") or "브랜드")
    industry = clean_text(brief.get("industry"))
    audience = clean_text(brief.get("targetAudience"))
    service = clean_text(brief.get("serviceSummary"))
    keyword_sentence = ", ".join(deduped_tones[:5])
    overview = (
        f"{brand_name}는 {industry or '일반'} 업종에서 "
        f"{audience or '브랜드 적합 고객층'}을 겨냥하며, "
        f"{service or '핵심 서비스 가치'}를 {keyword_sentence or '정제된 톤'}으로 전달해야 합니다."
    )

    master_tone = f"{brand_name} / {color_mode} / {' · '.join(deduped_tones[:3])}"
    triplets = build_triplet_defaults(int(project.get("gridSize", 9)), industry, {"masterTone": master_tone})
    reference_kinds = ", ".join(sorted(set(item["kind"] for item in reference_summary))) or "reference"

    return {
        "overview": overview,
        "toneKeywords": deduped_tones[:8],
        "palette": palette,
        "coreVisuals": core_visuals,
        "requiredKeywords": required_keywords,
        "bannedKeywords": banned_keywords,
        "locks": {
            "subjectLock": f"{reference_kinds} 기반 반복 요소를 유지하고 브랜드 핵심 피사체를 우선 고정합니다.",
            "styleLock": f"{color_mode}과 {' · '.join(deduped_tones[:4])}을 유지합니다.",
            "compositionLock": "넓은 여백, 중심 피사체, 텍스트가 들어갈 안전 영역을 확보합니다.",
            "negativeLock": f"금지 키워드 {', '.join(banned_keywords[:5]) or '없음'} 및 금지 색 {', '.join(banned_colors[:5]) or '없음'}은 배제합니다.",
        },
        "urlSummaries": url_summaries,
        "referenceSummary": reference_summary,
        "tripletSuggestions": triplets,
        "masterTone": master_tone,
        "warnings": warnings,
        "updatedAt": now_iso(),
    }


class StudioStore:
    def __init__(self, runtime_dir: Path = RUNTIME_DIR) -> None:
        self.runtime_dir = runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        self._ensure_settings()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    client TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    budget_limit REAL NOT NULL,
                    grid_size INTEGER NOT NULL,
                    grouping_mode TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    brand_pack_json TEXT NOT NULL,
                    grid_plan_json TEXT NOT NULL,
                    create_one_json TEXT NOT NULL,
                    review_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS variants (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    version_no INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    route TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    is_selected INTEGER NOT NULL DEFAULT 0,
                    is_locked INTEGER NOT NULL DEFAULT 0,
                    score REAL NOT NULL DEFAULT 0,
                    cost_estimate REAL NOT NULL DEFAULT 0,
                    cost_actual REAL NOT NULL DEFAULT 0,
                    asset_url TEXT NOT NULL,
                    prompt_json TEXT NOT NULL,
                    meta_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    pin_x REAL NOT NULL DEFAULT 50,
                    pin_y REAL NOT NULL DEFAULT 50,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_variants_project_scope
                    ON variants(project_id, scope_type, scope_key, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_project
                    ON comments(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_project
                    ON jobs(project_id, created_at DESC);
                """
            )

    def _ensure_settings(self) -> None:
        if SETTINGS_PATH.exists():
            return
        write_text(SETTINGS_PATH, json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2))

    def get_settings(self) -> Dict[str, Any]:
        current = safe_json_loads(SETTINGS_PATH.read_text(encoding="utf-8"), DEFAULT_SETTINGS)
        merged = merge_settings(DEFAULT_SETTINGS, current)
        merged["hasGoogleApiKey"] = bool(os.environ.get("GOOGLE_API_KEY"))
        return merged

    def update_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        settings = merge_settings(self.get_settings(), payload)
        cleaned = dict(settings)
        cleaned.pop("hasGoogleApiKey", None)
        write_text(SETTINGS_PATH, json.dumps(cleaned, ensure_ascii=False, indent=2))
        return self.get_settings()

    def _save_references(self, project_id: str, incoming: List[Dict[str, Any]], existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        existing_map = {item.get("assetId"): item for item in existing if item.get("assetId")}
        saved: List[Dict[str, Any]] = []
        for item in incoming:
            asset_id = clean_text(item.get("assetId"))
            if item.get("dataUrl"):
                mime, raw = decode_data_url(item["dataUrl"])
                asset_id = asset_id or make_id("ref")
                relative = Path("studio_data") / "assets" / project_id / "references" / f"{asset_id}{extension_for_mime(mime)}"
                write_bytes(PROJECT_ROOT / relative, raw)
                saved.append(
                    {
                        "assetId": asset_id,
                        "name": clean_text(item.get("name") or "reference"),
                        "kind": infer_reference_kind(item.get("name", ""), item.get("kind", "")),
                        "mimeType": mime,
                        "assetUrl": "/" + str(relative).replace(os.sep, "/"),
                        "palette": normalize_palette(ensure_list(item.get("palette", []))),
                        "notes": clean_text(item.get("notes")),
                    }
                )
            elif asset_id and asset_id in existing_map:
                retained = dict(existing_map[asset_id])
                retained["name"] = clean_text(item.get("name") or retained.get("name"))
                retained["kind"] = infer_reference_kind(retained.get("name", ""), item.get("kind", retained.get("kind", "")))
                retained["notes"] = clean_text(item.get("notes") or retained.get("notes"))
                if item.get("palette"):
                    retained["palette"] = normalize_palette(ensure_list(item.get("palette")))
                saved.append(retained)
        return saved

    def create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        brief_payload = payload.get("brief") or {}
        brief = default_brief()
        for key in brief:
            if key == "references":
                continue
            brief[key] = brief_payload.get(key, brief[key])
        brief["requiredKeywords"] = ensure_list(brief_payload.get("requiredKeywords"))
        brief["bannedKeywords"] = ensure_list(brief_payload.get("bannedKeywords"))
        brief["requiredColors"] = ensure_list(brief_payload.get("requiredColors"))
        brief["bannedColors"] = ensure_list(brief_payload.get("bannedColors"))
        if not clean_text(brief.get("projectName") or brief.get("brandName")):
            raise StudioError("프로젝트명 또는 브랜드명을 입력해주세요.")

        project_id = make_id("project")
        settings = self.get_settings()
        grid_size = 12 if int(payload.get("gridSize", 9) or 9) == 12 else 9
        brief["references"] = self._save_references(project_id, brief_payload.get("references", []), [])
        brand_pack = default_brand_pack()
        grid_plan = default_grid_plan(grid_size, brief.get("industry", ""), brand_pack)
        create_one = default_create_one_state()
        review = default_review_state()
        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, project_name, client, brand_name, industry, owner, goal, status, budget_limit,
                    grid_size, grouping_mode, brief_json, brand_pack_json, grid_plan_json, create_one_json,
                    review_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    clean_text(brief.get("projectName") or brief.get("brandName")),
                    clean_text(brief.get("client")),
                    clean_text(brief.get("brandName") or brief.get("projectName")),
                    clean_text(brief.get("industry")),
                    clean_text(brief.get("owner")),
                    clean_text(brief.get("goal")),
                    "Draft",
                    float(payload.get("budgetLimit") or settings["projectBudgetDefault"]),
                    grid_size,
                    "row",
                    dump_json(brief),
                    dump_json(brand_pack),
                    dump_json(grid_plan),
                    dump_json(create_one),
                    dump_json(review),
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_project(project_id)

    def update_project(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_project(project_id)
        brief = current["brief"]
        incoming = payload.get("brief") or {}
        for key in [
            "projectName",
            "client",
            "brandName",
            "industry",
            "owner",
            "goal",
            "serviceSummary",
            "targetAudience",
            "homepageUrl",
            "instagramUrl",
        ]:
            if key in incoming:
                brief[key] = incoming[key]
        for key in ["requiredKeywords", "bannedKeywords", "requiredColors", "bannedColors"]:
            if key in incoming:
                brief[key] = ensure_list(incoming.get(key))
        if "references" in incoming:
            brief["references"] = self._save_references(project_id, incoming.get("references", []), brief.get("references", []))

        grid_size = current["gridSize"]
        if payload.get("gridSize"):
            grid_size = 12 if int(payload.get("gridSize")) == 12 else 9
        grouping_mode = clean_text(payload.get("groupingMode") or current.get("groupingMode") or "row") or "row"
        grid_plan = current["gridPlan"]
        if grid_size != current["gridSize"]:
            grid_plan = default_grid_plan(grid_size, brief.get("industry", ""), current["brandPack"])
        else:
            grid_plan["gridSize"] = grid_size
            grid_plan["groupingMode"] = grouping_mode
            grid_plan["updatedAt"] = now_iso()

        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET project_name=?, client=?, brand_name=?, industry=?, owner=?, goal=?, budget_limit=?,
                    grid_size=?, grouping_mode=?, brief_json=?, grid_plan_json=?, updated_at=?
                WHERE id=?
                """,
                (
                    clean_text(brief.get("projectName") or brief.get("brandName")),
                    clean_text(brief.get("client")),
                    clean_text(brief.get("brandName") or brief.get("projectName")),
                    clean_text(brief.get("industry")),
                    clean_text(brief.get("owner")),
                    clean_text(brief.get("goal")),
                    float(payload.get("budgetLimit") or current["budgetLimit"]),
                    grid_size,
                    grouping_mode,
                    dump_json(brief),
                    dump_json(grid_plan),
                    timestamp,
                    project_id,
                ),
            )
        return self.get_project(project_id)

    def set_project_blobs(
        self,
        project_id: str,
        *,
        brand_pack: Optional[Dict[str, Any]] = None,
        grid_plan: Optional[Dict[str, Any]] = None,
        create_one: Optional[Dict[str, Any]] = None,
        review: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> None:
        current = self.get_project(project_id)
        payloads = {
            "brand_pack_json": dump_json(brand_pack or current["brandPack"]),
            "grid_plan_json": dump_json(grid_plan or current["gridPlan"]),
            "create_one_json": dump_json(create_one or current["createOne"]),
            "review_json": dump_json(review or current["review"]),
            "status": clean_text(status or current["status"]) or current["status"],
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET brand_pack_json=?, grid_plan_json=?, create_one_json=?, review_json=?, status=?, updated_at=?
                WHERE id=?
                """,
                (
                    payloads["brand_pack_json"],
                    payloads["grid_plan_json"],
                    payloads["create_one_json"],
                    payloads["review_json"],
                    payloads["status"],
                    now_iso(),
                    project_id,
                ),
            )

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.*,
                    COALESCE(SUM(v.cost_actual), 0) AS spent_cost,
                    COUNT(v.id) AS variant_count
                FROM projects p
                LEFT JOIN variants v ON v.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        projects = []
        for row in rows:
            projects.append(
                {
                    "id": row["id"],
                    "projectName": row["project_name"],
                    "client": row["client"],
                    "brandName": row["brand_name"],
                    "industry": row["industry"],
                    "owner": row["owner"],
                    "goal": row["goal"],
                    "status": row["status"],
                    "budgetLimit": row["budget_limit"],
                    "spentCost": round(float(row["spent_cost"] or 0), 2),
                    "variantCount": int(row["variant_count"] or 0),
                    "gridSize": row["grid_size"],
                    "updatedAt": row["updated_at"],
                }
            )
        return projects

    def _project_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "projectName": row["project_name"],
            "client": row["client"],
            "brandName": row["brand_name"],
            "industry": row["industry"],
            "owner": row["owner"],
            "goal": row["goal"],
            "status": row["status"],
            "budgetLimit": float(row["budget_limit"]),
            "gridSize": int(row["grid_size"]),
            "groupingMode": row["grouping_mode"],
            "brief": safe_json_loads(row["brief_json"], default_brief()),
            "brandPack": safe_json_loads(row["brand_pack_json"], default_brand_pack()),
            "gridPlan": safe_json_loads(row["grid_plan_json"], default_grid_plan(int(row["grid_size"]), row["industry"], default_brand_pack())),
            "createOne": safe_json_loads(row["create_one_json"], default_create_one_state()),
            "review": safe_json_loads(row["review_json"], default_review_state()),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_variants(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM variants
                WHERE project_id=?
                ORDER BY scope_type, scope_key, version_no DESC, created_at DESC
                """,
                (project_id,),
            ).fetchall()
        variants = []
        for row in rows:
            variants.append(
                {
                    "id": row["id"],
                    "projectId": row["project_id"],
                    "scopeType": row["scope_type"],
                    "scopeKey": row["scope_key"],
                    "version": row["version_no"],
                    "role": row["role"],
                    "route": row["route"],
                    "provider": row["provider"],
                    "model": row["model"],
                    "status": row["status"],
                    "selected": bool(row["is_selected"]),
                    "locked": bool(row["is_locked"]),
                    "score": float(row["score"]),
                    "costEstimate": float(row["cost_estimate"]),
                    "costActual": float(row["cost_actual"]),
                    "assetUrl": row["asset_url"],
                    "prompt": safe_json_loads(row["prompt_json"], {}),
                    "meta": safe_json_loads(row["meta_json"], {}),
                    "createdAt": row["created_at"],
                }
            )
        return variants

    def list_comments(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "projectId": row["project_id"],
                "scopeType": row["scope_type"],
                "scopeKey": row["scope_key"],
                "author": row["author"],
                "body": row["body"],
                "pinX": float(row["pin_x"]),
                "pinY": float(row["pin_y"]),
                "status": row["status"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def get_project(self, project_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise StudioError("프로젝트를 찾을 수 없습니다.", status=404)
        project = self._project_row_to_dict(row)
        project["variants"] = self.list_variants(project_id)
        project["comments"] = self.list_comments(project_id)
        project["spentCost"] = round(sum(item["costActual"] for item in project["variants"]), 2)
        project["estimatedCost"] = round(sum(item["costEstimate"] for item in project["variants"]), 2)
        project["gridPlan"]["warnings"] = build_similarity_warnings(project["gridPlan"], project["variants"])
        project["review"]["projectStatus"] = infer_project_status(project)
        return project

    def create_job(self, project_id: str, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.get_project(project_id)
        job_id = make_id("job")
        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, project_id, job_type, status, progress, payload_json, result_json, error_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, project_id, job_type, "queued", 0, dump_json(payload), "", "", timestamp, timestamp),
            )
        return self.get_job(job_id)

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        progress: int,
        result: Optional[Dict[str, Any]] = None,
        error_message: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status=?, progress=?, result_json=?, error_message=?, updated_at=?
                WHERE id=?
                """,
                (status, progress, dump_json(result or {}), clean_text(error_message), now_iso(), job_id),
            )

    def get_job(self, job_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise StudioError("작업 상태를 찾을 수 없습니다.", status=404)
        return {
            "id": row["id"],
            "projectId": row["project_id"],
            "jobType": row["job_type"],
            "status": row["status"],
            "progress": int(row["progress"]),
            "payload": safe_json_loads(row["payload_json"], {}),
            "result": safe_json_loads(row["result_json"], {}),
            "errorMessage": row["error_message"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _next_version(self, project_id: str, scope_type: str, scope_key: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version_no), 0) AS current_max FROM variants WHERE project_id=? AND scope_type=? AND scope_key=?",
                (project_id, scope_type, scope_key),
            ).fetchone()
        return int(row["current_max"]) + 1

    def insert_variant(
        self,
        *,
        project_id: str,
        scope_type: str,
        scope_key: str,
        role: str,
        route_info: Dict[str, Any],
        prompt: Dict[str, Any],
        asset_url: str,
        meta: Dict[str, Any],
        selected: bool,
        locked: bool,
        cost_actual: float,
    ) -> Dict[str, Any]:
        version = self._next_version(project_id, scope_type, scope_key)
        variant_id = make_id("variant")
        timestamp = now_iso()
        if selected:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE variants SET is_selected=0 WHERE project_id=? AND scope_type=? AND scope_key=?",
                    (project_id, scope_type, scope_key),
                )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO variants (
                    id, project_id, scope_type, scope_key, version_no, role, route, provider, model,
                    status, is_selected, is_locked, score, cost_estimate, cost_actual, asset_url,
                    prompt_json, meta_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    variant_id,
                    project_id,
                    scope_type,
                    scope_key,
                    version,
                    clean_text(role),
                    route_info["route"],
                    route_info["provider"],
                    route_info["model"],
                    "Draft" if route_info["route"] == "draft" else "Review",
                    1 if selected else 0,
                    1 if locked else 0,
                    float(meta.get("score", 0)),
                    float(route_info["unitCost"]),
                    float(cost_actual),
                    asset_url,
                    dump_json(prompt),
                    dump_json(meta),
                    timestamp,
                ),
            )
        return self.get_variant(variant_id)

    def get_variant(self, variant_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM variants WHERE id=?", (variant_id,)).fetchone()
        if not row:
            raise StudioError("버전을 찾을 수 없습니다.", status=404)
        return {
            "id": row["id"],
            "projectId": row["project_id"],
            "scopeType": row["scope_type"],
            "scopeKey": row["scope_key"],
            "version": row["version_no"],
            "role": row["role"],
            "route": row["route"],
            "provider": row["provider"],
            "model": row["model"],
            "status": row["status"],
            "selected": bool(row["is_selected"]),
            "locked": bool(row["is_locked"]),
            "score": float(row["score"]),
            "costEstimate": float(row["cost_estimate"]),
            "costActual": float(row["cost_actual"]),
            "assetUrl": row["asset_url"],
            "prompt": safe_json_loads(row["prompt_json"], {}),
            "meta": safe_json_loads(row["meta_json"], {}),
            "createdAt": row["created_at"],
        }

    def update_variant(self, variant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        variant = self.get_variant(variant_id)
        selected = payload.get("selected")
        locked = payload.get("locked")
        status = payload.get("status")

        with self._connect() as conn:
            if selected is True:
                conn.execute(
                    "UPDATE variants SET is_selected=0 WHERE project_id=? AND scope_type=? AND scope_key=?",
                    (variant["projectId"], variant["scopeType"], variant["scopeKey"]),
                )
            if selected is not None:
                conn.execute("UPDATE variants SET is_selected=? WHERE id=?", (1 if selected else 0, variant_id))
            if locked is not None:
                conn.execute("UPDATE variants SET is_locked=? WHERE id=?", (1 if locked else 0, variant_id))
            if status:
                conn.execute("UPDATE variants SET status=? WHERE id=?", (clean_text(status), variant_id))

        if variant["scopeType"] == "slot":
            project = self.get_project(variant["projectId"])
            grid_plan = project["gridPlan"]
            for slot in grid_plan.get("slots", []):
                if slot["id"] == variant["scopeKey"]:
                    if selected is True:
                        slot["selectedVariantId"] = variant_id
                    if locked is not None:
                        slot["locked"] = bool(locked)
                    if status:
                        slot["status"] = clean_text(status)
                    break
            self.set_project_blobs(variant["projectId"], grid_plan=grid_plan)
        return self.get_variant(variant_id)

    def save_grid_plan(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        project = self.get_project(project_id)
        grid_plan = payload.get("gridPlan")
        if not isinstance(grid_plan, dict):
            raise StudioError("저장할 그리드 정보가 올바르지 않습니다.")
        sanitized = default_grid_plan(int(grid_plan.get("gridSize", project["gridSize"])), project["industry"], project["brandPack"])
        sanitized["gridSize"] = 12 if int(grid_plan.get("gridSize", sanitized["gridSize"])) == 12 else 9
        sanitized["groupingMode"] = clean_text(grid_plan.get("groupingMode", sanitized["groupingMode"])) or "row"
        sanitized["masterTone"] = clean_text(grid_plan.get("masterTone", project["brandPack"].get("masterTone", "")))
        incoming_triplets = grid_plan.get("triplets") or []
        incoming_slots = grid_plan.get("slots") or []
        sanitized["triplets"] = []
        for index, triplet in enumerate(incoming_triplets[: sanitized["gridSize"] // 3], start=1):
            sanitized["triplets"].append(
                {
                    "id": clean_text(triplet.get("id") or f"triplet-{index}"),
                    "label": clean_text(triplet.get("label") or f"Triplet {index}"),
                    "tone": clean_text(triplet.get("tone") or sanitized["masterTone"]),
                    "roles": ensure_list(triplet.get("roles"))[:3] or ["후킹", "설명", "전환"],
                    "masterTone": sanitized["masterTone"],
                }
            )
        while len(sanitized["triplets"]) < sanitized["gridSize"] // 3:
            triplet_index = len(sanitized["triplets"]) + 1
            sanitized["triplets"].append(
                {
                    "id": f"triplet-{triplet_index}",
                    "label": f"Triplet {triplet_index}",
                    "tone": sanitized["masterTone"],
                    "roles": ["후킹", "설명", "전환"],
                    "masterTone": sanitized["masterTone"],
                }
            )

        sanitized["slots"] = []
        for index in range(sanitized["gridSize"]):
            incoming = incoming_slots[index] if index < len(incoming_slots) else {}
            triplet_id = sanitized["triplets"][index // 3]["id"]
            sanitized["slots"].append(
                {
                    "id": clean_text(incoming.get("id") or f"slot-{index + 1}"),
                    "index": index + 1,
                    "tripletId": triplet_id,
                    "role": clean_text(incoming.get("role") or SLOT_ROLE_TEMPLATES[sanitized["gridSize"]][index]),
                    "tone": clean_text(incoming.get("tone") or sanitized["triplets"][index // 3]["tone"]),
                    "locked": bool(incoming.get("locked", False)),
                    "status": clean_text(incoming.get("status") or "Draft"),
                    "selectedVariantId": clean_text(incoming.get("selectedVariantId")),
                    "notes": clean_text(incoming.get("notes")),
                }
            )
        sanitized["updatedAt"] = now_iso()
        self.set_project_blobs(project_id, grid_plan=sanitized)
        return self.get_project(project_id)

    def add_comment(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.get_project(project_id)
        author = clean_text(payload.get("author") or "내부 리뷰어")
        body = clean_text(payload.get("body"))
        if not body:
            raise StudioError("코멘트 내용을 입력해주세요.")
        comment_id = make_id("comment")
        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comments (id, project_id, scope_type, scope_key, author, body, pin_x, pin_y, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comment_id,
                    project_id,
                    clean_text(payload.get("scopeType") or "project"),
                    clean_text(payload.get("scopeKey") or project_id),
                    author,
                    body,
                    float(payload.get("pinX") or 50),
                    float(payload.get("pinY") or 50),
                    clean_text(payload.get("status") or "Open"),
                    timestamp,
                ),
            )
        return {"comment": self.list_comments(project_id)[0]}

    def export_project(self, project_id: str) -> Dict[str, Any]:
        project = self.get_project(project_id)
        export_id = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{slugify(project['projectName'])}"
        export_root = EXPORT_DIR / export_id
        export_root.mkdir(parents=True, exist_ok=True)
        assets_root = export_root / "assets"
        assets_root.mkdir(parents=True, exist_ok=True)

        selected_variants = []
        for variant in project["variants"]:
            if variant["selected"] or variant["scopeType"] == "one":
                selected_variants.append(variant)
                source = PROJECT_ROOT / variant["assetUrl"].lstrip("/")
                if source.exists():
                    shutil.copy2(source, assets_root / source.name)

        summary = {
            "project": {
                "id": project["id"],
                "projectName": project["projectName"],
                "client": project["client"],
                "brandName": project["brandName"],
                "industry": project["industry"],
                "status": project["status"],
            },
            "brandPack": project["brandPack"],
            "gridPlan": project["gridPlan"],
            "selectedVariants": selected_variants,
            "comments": project["comments"],
            "cost": {
                "estimated": project["estimatedCost"],
                "actual": project["spentCost"],
                "budgetLimit": project["budgetLimit"],
            },
        }
        write_text(export_root / "project_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

        html_items = []
        for variant in selected_variants:
            file_name = Path(variant["assetUrl"]).name
            html_items.append(
                f"""
                <article class="tile">
                  <img src="./assets/{file_name}" alt="{xml_escape(variant['role'])}" />
                  <div class="meta">
                    <strong>{xml_escape(variant['role'])}</strong>
                    <span>{xml_escape(variant['route'])} · {xml_escape(variant['status'])}</span>
                  </div>
                </article>
                """
            )
        write_text(
            export_root / "contact_sheet.html",
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>{xml_escape(project['projectName'])} contact sheet</title>
  <style>
    body {{ font-family: Pretendard, Arial, sans-serif; margin: 32px; background: #f5f3ef; color: #1f2429; }}
    h1 {{ margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
    .tile {{ background: #fff; border: 1px solid #d9dde2; border-radius: 22px; overflow: hidden; box-shadow: 0 14px 30px rgba(17,24,39,.08); }}
    img {{ width: 100%; display: block; aspect-ratio: 4 / 5; object-fit: cover; background: #ece8df; }}
    .meta {{ padding: 14px 16px 18px; display: grid; gap: 4px; }}
    span {{ color: #67737e; font-size: 14px; }}
  </style>
</head>
<body>
  <h1>{xml_escape(project['projectName'])}</h1>
  <div class="grid">
    {''.join(html_items)}
  </div>
</body>
</html>
""",
        )

        zip_path = EXPORT_DIR / f"{export_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in export_root.rglob("*"):
                archive.write(file_path, arcname=str(file_path.relative_to(export_root)))

        return {
            "exportId": export_id,
            "folderUrl": "/" + str(export_root.relative_to(PROJECT_ROOT)).replace(os.sep, "/"),
            "zipUrl": "/" + str(zip_path.relative_to(PROJECT_ROOT)).replace(os.sep, "/"),
            "selectedCount": len(selected_variants),
        }


def infer_project_status(project: Dict[str, Any]) -> str:
    selected_grid = [variant for variant in project["variants"] if variant["scopeType"] == "slot" and variant["selected"]]
    approved = [variant for variant in selected_grid if variant["status"].lower() == "approved"]
    if selected_grid and len(approved) == len(selected_grid):
        return "Approved"
    if project["comments"]:
        return "Review"
    if project["variants"]:
        return "Draft"
    return "Brief"


def build_similarity_warnings(grid_plan: Dict[str, Any], variants: List[Dict[str, Any]]) -> List[str]:
    selected_map = {variant["scopeKey"]: variant for variant in variants if variant["scopeType"] == "slot" and variant["selected"]}
    warnings = []
    last_role = ""
    last_palette_label = ""
    repeat_count = 0
    for slot in grid_plan.get("slots", []):
        variant = selected_map.get(slot["id"])
        role = clean_text(slot.get("role"))
        palette_label = clean_text(((variant or {}).get("meta") or {}).get("paletteLabel"))
        if role == last_role and role:
            repeat_count += 1
        else:
            repeat_count = 1
        if repeat_count >= 3:
            warnings.append(f"{role} 역할이 3칸 이상 연속됩니다. 밸런스를 다시 확인하세요.")
            repeat_count = 0
        if palette_label and palette_label == last_palette_label:
            warnings.append(f"{slot['id']}와 이전 슬롯의 팔레트 방향이 유사합니다.")
        last_role = role
        last_palette_label = palette_label
    deduped = []
    for warning in warnings:
        if warning not in deduped:
            deduped.append(warning)
    return deduped[:6]


class StudioJobs:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker = threading.Thread(target=self._run, daemon=True, name="studio-jobs")
        self._worker.start()

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def _run(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._process(job_id)
            except Exception as exc:  # pragma: no cover - defensive worker guard
                self.store.update_job(job_id, status="failed", progress=100, error_message=str(exc))
            finally:
                self._queue.task_done()

    def _process(self, job_id: str) -> None:
        job = self.store.get_job(job_id)
        project = self.store.get_project(job["projectId"])
        settings = self.store.get_settings()
        self.store.update_job(job_id, status="running", progress=10)
        if job["jobType"] == "generate_create_one":
            result = self._generate_create_one(project, settings, job["payload"], job_id)
        elif job["jobType"] == "generate_grid":
            result = self._generate_grid(project, settings, job["payload"], job_id)
        else:
            raise StudioError("지원하지 않는 백그라운드 작업입니다.")
        self.store.update_job(job_id, status="succeeded", progress=100, result=result)

    def _generate_variant_asset(
        self,
        *,
        project: Dict[str, Any],
        route_info: Dict[str, Any],
        prompt_block: Dict[str, Any],
        role: str,
        seed: int,
    ) -> Tuple[str, Dict[str, Any], float]:
        brand_pack = project["brandPack"]
        brand_name = clean_text(project["brandName"] or project["projectName"])
        palette = brand_pack.get("palette", [])
        score = max(0.72, min(0.96, 0.72 + ((seed % 19) / 100)))
        palette_label = infer_color_mode(palette)
        provider_notice = ""

        if route_info["provider"] == "gemini" and os.environ.get("GOOGLE_API_KEY"):
            try:
                raw, mime, response = call_gemini_image(
                    api_key=os.environ["GOOGLE_API_KEY"],
                    model=route_info["model"],
                    prompt=prompt_block,
                    reference_parts=load_reference_parts(project),
                )
                ext = extension_for_mime(mime)
                variant_id = make_id("variantfile")
                relative = Path("studio_data") / "assets" / project["id"] / "variants" / f"{variant_id}{ext}"
                write_bytes(PROJECT_ROOT / relative, raw)
                return (
                    "/" + str(relative).replace(os.sep, "/"),
                    {
                        "score": round(score, 2),
                        "paletteLabel": palette_label,
                        "providerNotice": "Gemini 이미지 생성 성공",
                        "responseDigest": {
                            "candidateCount": len(response.get("candidates") or []),
                        },
                    },
                    route_info["unitCost"],
                )
            except StudioError as exc:
                provider_notice = f"{exc}. Mock 렌더러로 자동 대체했습니다."

        svg = render_mock_svg(
            brand_name=brand_name,
            headline=prompt_block["headline"],
            subline=" · ".join(prompt_block["positivePrompt"][:3]),
            role=role,
            route_label=route_info["label"],
            palette=palette,
            seed=seed,
        )
        variant_id = make_id("variantfile")
        asset_url = save_mock_asset(project["id"], variant_id, svg)
        return (
            asset_url,
            {
                "score": round(score, 2),
                "paletteLabel": palette_label,
                "providerNotice": provider_notice or "Mock 렌더러로 생성됨",
            },
            0.0,
        )

    def _generate_create_one(
        self,
        project: Dict[str, Any],
        settings: Dict[str, Any],
        payload: Dict[str, Any],
        job_id: str,
    ) -> Dict[str, Any]:
        route_info = route_settings(settings, payload.get("route", "draft"))
        count = max(1, min(8, int(payload.get("count", 4) or 4)))
        preset = clean_text(payload.get("preset") or "Hero")
        direction = clean_text(payload.get("direction"))
        created = []

        for index in range(count):
            self.store.update_job(job_id, status="running", progress=15 + int(((index + 1) / count) * 75))
            role = f"{preset} {index + 1}"
            prompt_block = make_prompt_block(project, project["brandPack"], "one", preset.lower(), role, route_info["route"], direction)
            asset_url, meta, cost_actual = self._generate_variant_asset(
                project=project,
                route_info=route_info,
                prompt_block=prompt_block,
                role=role,
                seed=index + int(time.time()),
            )
            created.append(
                self.store.insert_variant(
                    project_id=project["id"],
                    scope_type="one",
                    scope_key=preset.lower(),
                    role=role,
                    route_info=route_info,
                    prompt=prompt_block,
                    asset_url=asset_url,
                    meta=meta,
                    selected=index == 0,
                    locked=False,
                    cost_actual=cost_actual,
                )
            )

        create_one = dict(project["createOne"])
        create_one["lastPreset"] = preset
        create_one["lastRoute"] = route_info["route"]
        create_one["lastCount"] = count
        create_one["lastDirection"] = direction
        self.store.set_project_blobs(project["id"], create_one=create_one, status="Draft")
        return {"variants": created, "project": self.store.get_project(project["id"])}

    def _generate_grid(
        self,
        project: Dict[str, Any],
        settings: Dict[str, Any],
        payload: Dict[str, Any],
        job_id: str,
    ) -> Dict[str, Any]:
        route_info = route_settings(settings, payload.get("route", "draft"))
        target_slot_ids = ensure_list(payload.get("slotIds"))
        grid_plan = project["gridPlan"]
        slots = []
        for slot in grid_plan.get("slots", []):
            if slot.get("locked") and not target_slot_ids:
                continue
            if target_slot_ids and slot["id"] not in target_slot_ids:
                continue
            slots.append(slot)
        if not slots:
            slots = [slot for slot in grid_plan.get("slots", []) if not slot.get("locked")]
        if not slots:
            raise StudioError("재생성할 슬롯이 없습니다.")

        created = []
        total = len(slots)
        for index, slot in enumerate(slots, start=1):
            self.store.update_job(job_id, status="running", progress=15 + int((index / total) * 75))
            direction = clean_text(payload.get("direction") or slot.get("notes"))
            prompt_block = make_prompt_block(
                project,
                project["brandPack"],
                "slot",
                slot["id"],
                slot["role"],
                route_info["route"],
                direction,
            )
            asset_url, meta, cost_actual = self._generate_variant_asset(
                project=project,
                route_info=route_info,
                prompt_block=prompt_block,
                role=slot["role"],
                seed=index * 97 + int(time.time()),
            )
            variant = self.store.insert_variant(
                project_id=project["id"],
                scope_type="slot",
                scope_key=slot["id"],
                role=slot["role"],
                route_info=route_info,
                prompt=prompt_block,
                asset_url=asset_url,
                meta=meta,
                selected=True,
                locked=bool(slot.get("locked")),
                cost_actual=cost_actual,
            )
            created.append(variant)
            slot["selectedVariantId"] = variant["id"]

        self.store.set_project_blobs(project["id"], grid_plan=grid_plan, status="Review" if route_info["route"] != "draft" else "Draft")
        return {"variants": created, "project": self.store.get_project(project["id"])}
