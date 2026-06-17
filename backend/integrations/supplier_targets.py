from __future__ import annotations

import re
from typing import Callable, Optional
from urllib.parse import urlparse


class SupplierTargetError(ValueError):
    pass


ACCOUNT_STYLE_PLATFORMS = {"instagram", "threads", "youtube", "tiktok", "facebook"}


def preview_platform_hint(product_code: str, platform_slug: str) -> str:
    lowered = f"{platform_slug} {product_code}".lower()
    for keyword, resolved in (
        ("인스타그램", "instagram"),
        ("인스타", "instagram"),
        ("instagram", "instagram"),
        ("유튜브", "youtube"),
        ("youtube", "youtube"),
        ("틱톡", "tiktok"),
        ("tiktok", "tiktok"),
        ("스레드", "threads"),
        ("threads", "threads"),
        ("페이스북", "facebook"),
        ("facebook", "facebook"),
        ("네이버", "nportal"),
        ("naver", "nportal"),
        ("블로그", "nportal"),
        ("blog", "nportal"),
    ):
        if keyword in lowered:
            return resolved
    return platform_slug


def account_preview_url(account_value: str, platform_hint: str) -> Optional[str]:
    cleaned = str(account_value or "").strip().strip("/")
    if not cleaned:
        return None
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    cleaned = cleaned.replace(" ", "")
    if not re.fullmatch(r"[\w.\-]+", cleaned):
        return None

    builders = {
        "instagram": lambda handle: f"https://www.instagram.com/{handle}/",
        "threads": lambda handle: f"https://www.threads.net/@{handle}",
        "youtube": lambda handle: f"https://www.youtube.com/@{handle}",
        "tiktok": lambda handle: f"https://www.tiktok.com/@{handle}",
        "facebook": lambda handle: f"https://www.facebook.com/{handle}",
    }
    builder = builders.get(platform_hint)
    return builder(cleaned) if builder else None


def supplier_supported_hosts(platform_hint: str) -> set[str]:
    return {
        "instagram": {"instagram.com", "www.instagram.com"},
        "threads": {"threads.net", "www.threads.net", "threads.com", "www.threads.com"},
        "youtube": {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"},
        "tiktok": {"tiktok.com", "www.tiktok.com"},
        "facebook": {"facebook.com", "www.facebook.com", "m.facebook.com"},
    }.get(platform_hint, set())


def platform_target_url_matches(
    platform_hint: str,
    raw_url: str,
    *,
    normalize_url: Callable[[str], Optional[str]],
    looks_like_url: Callable[[str], bool],
) -> bool:
    normalized = normalize_url(raw_url)
    if not normalized:
        return False

    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    path = parsed.path or "/"

    def host_is(domain: str) -> bool:
        return host == domain or host.endswith(f".{domain}")

    if platform_hint == "instagram":
        return host_is("instagram.com") and path.strip("/") != ""
    if platform_hint == "youtube":
        return host == "youtu.be" or host_is("youtube.com")
    if platform_hint == "tiktok":
        return host_is("tiktok.com")
    if platform_hint == "facebook":
        return host_is("facebook.com")
    if platform_hint == "threads":
        return host_is("threads.net")
    if platform_hint == "nportal":
        return host_is("naver.com")
    return looks_like_url(normalized)


def platform_target_error_message(platform_hint: str) -> str:
    labels = {
        "instagram": "인스타그램",
        "youtube": "유튜브",
        "tiktok": "틱톡",
        "facebook": "페이스북",
        "threads": "스레드",
        "nportal": "네이버",
    }
    platform_label = labels.get(platform_hint, "해당 플랫폼")
    return f"{platform_label} 형식에 맞는 링크 또는 계정을 입력해 주세요."


def supplier_panel_target_link(
    raw_value: object,
    platform_hint: str,
    *,
    normalize_url: Callable[[str], Optional[str]],
    looks_like_url: Callable[[str], bool],
) -> str:
    candidate = str(raw_value or "").strip()
    if not candidate:
        return ""
    if candidate.startswith(("http://", "https://")):
        normalized = normalize_url(candidate) or candidate
        if platform_hint in ACCOUNT_STYLE_PLATFORMS:
            parsed = urlparse(normalized)
            host = parsed.netloc.lower()
            has_path_or_query = bool(parsed.path.strip("/")) or bool(parsed.query) or bool(parsed.fragment)
            if host and host not in supplier_supported_hosts(platform_hint) and not has_path_or_query:
                inferred_link = account_preview_url(host, platform_hint)
                if inferred_link:
                    return inferred_link
        return normalized
    if platform_hint in ACCOUNT_STYLE_PLATFORMS:
        inferred_link = account_preview_url(candidate, platform_hint)
        if inferred_link:
            normalized = normalize_url(candidate) if looks_like_url(candidate) else None
            host = urlparse(normalized).netloc.lower() if normalized else ""
            if not host or host not in supplier_supported_hosts(platform_hint):
                return inferred_link
    if looks_like_url(candidate):
        return normalize_url(candidate) or candidate
    return ""


def validate_supplier_panel_target_link(
    link: str,
    platform_hint: str,
    *,
    normalize_url: Callable[[str], Optional[str]],
) -> None:
    if platform_hint not in ACCOUNT_STYLE_PLATFORMS or not link:
        return
    normalized = normalize_url(link) or link
    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    if not host:
        raise SupplierTargetError("공급사 발주 대상 링크를 확인할 수 없습니다. Cafe24 주문 옵션의 계정 ID 또는 URL을 확인해 주세요.")
    supported_hosts = supplier_supported_hosts(platform_hint)
    if supported_hosts and host not in supported_hosts:
        raise SupplierTargetError(
            f"공급사 발주 대상 링크 도메인이 {platform_hint} 서비스와 맞지 않습니다: {host}. "
            "Cafe24 주문 옵션에서 계정 ID 또는 올바른 SNS 링크를 확인해 주세요."
        )
