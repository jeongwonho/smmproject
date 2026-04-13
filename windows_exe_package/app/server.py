#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"

SAMPLE_VIDEO = {
    "title": "[위대한 수업] 인간을 움직이는 선택의 기술",
    "channelTitle": "EBS",
    "publishedAt": "2026-03-20T09:00:00Z",
    "videoId": "demo-video",
    "url": "https://www.youtube.com/watch?v=demo-video",
}

SAMPLE_COMMENTS = [
    {
        "author": "시청자 A",
        "text": "정말 오랜만에 댓글까지 읽게 되는 강연이었어요. 내용이 어렵지 않게 정리돼서 좋았습니다.",
        "likeCount": 184,
        "publishedAt": "2026-03-20T10:10:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 B",
        "text": "위대한 수업은 늘 좋은데 이번 편은 특히 현실적인 예시가 많아서 기억에 남네요.",
        "likeCount": 163,
        "publishedAt": "2026-03-20T11:20:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 C",
        "text": "강연자 설명이 차분해서 집중이 잘 됐고, 중간중간 던지는 질문도 생각할 거리를 줬어요.",
        "likeCount": 158,
        "publishedAt": "2026-03-20T12:15:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 D",
        "text": "댓글 보니 저처럼 다시 보겠다는 분이 많네요. 저도 메모하면서 한 번 더 볼 예정입니다.",
        "likeCount": 144,
        "publishedAt": "2026-03-20T12:30:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 E",
        "text": "단순한 지식 전달이 아니라 삶에 바로 적용할 수 있는 통찰이 있었다는 점이 좋았습니다.",
        "likeCount": 132,
        "publishedAt": "2026-03-20T13:40:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 F",
        "text": "후반부는 조금 더 사례가 있었으면 좋겠다는 아쉬움도 있지만 전체적으로 만족합니다.",
        "likeCount": 87,
        "publishedAt": "2026-03-20T14:00:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 G",
        "text": "전문적인 이야기인데도 어렵지 않게 풀어줘서 부모님과 함께 보기 좋겠어요.",
        "likeCount": 79,
        "publishedAt": "2026-03-20T15:10:00Z",
        "isReply": False,
    },
    {
        "author": "시청자 H",
        "text": "EBS 위대한 수업은 이런 깊이 있는 콘텐츠를 꾸준히 해줘서 늘 고맙습니다.",
        "likeCount": 76,
        "publishedAt": "2026-03-20T15:45:00Z",
        "isReply": False,
    },
]

STOPWORDS = {
    "그리고",
    "하지만",
    "이번",
    "정말",
    "너무",
    "그냥",
    "이런",
    "저는",
    "제가",
    "이게",
    "있는",
    "같아요",
    "같습니다",
    "네요",
    "입니다",
    "있는지",
    "영상",
    "강연",
    "위대한",
    "수업",
    "댓글",
    "시청자",
    "정도",
    "에서",
    "으로",
    "하고",
    "하게",
    "때문",
    "하면",
    "하면요",
    "more",
    "with",
    "that",
    "this",
    "좋습니다",
    "좋았어요",
    "좋았습니다",
    "좋겠어요",
    "좋네요",
    "있어요",
    "있습니다",
    "됩니다",
    "였어요",
    "했어요",
    "이었어요",
    "예정입니다",
}

CATEGORY_RULES = {
    "배움 포인트": ["배웠", "깨달", "통찰", "인사이트", "정리", "공부", "지식", "생각"],
    "감동/몰입": ["감동", "울림", "좋았", "좋네요", "최고", "감사", "훌륭", "멋진", "집중"],
    "공감/자기반영": ["공감", "저도", "제 이야기", "저 역시", "와닿", "비슷", "현실적"],
    "비판/추가논의": ["아쉽", "다만", "부족", "반론", "편향", "비판", "논쟁"],
    "재시청/추천": ["다시", "재시청", "추천", "공유", "저장", "한 번 더", "부모님"],
    "질문/확장": ["궁금", "질문", "왜", "어떻게", "더 알고", "후속"],
}

POSITIVE_MARKERS = ["좋", "감동", "최고", "훌륭", "감사", "유익", "도움", "추천", "다시"]
CRITICAL_MARKERS = ["아쉽", "부족", "다만", "편향", "반론", "비판", "논쟁"]

OFFICIAL_NAVER_EDITOR_GUIDE = "https://help.naver.com/service/5593/category/3128?lang=ko"
OFFICIAL_NAVER_DRAFT_GUIDE = "https://help.naver.com/service/5593/contents/15543?lang=ko&osType=PC"


class ApiError(Exception):
    pass


def read_json(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    payload = handler.rfile.read(length).decode("utf-8") if length else "{}"
    try:
        return json.loads(payload or "{}")
    except json.JSONDecodeError as exc:
        raise ApiError("JSON 본문을 해석할 수 없습니다.") from exc


def write_json(handler: SimpleHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def dedupe_key(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", clean_text(value).lower())


def looks_like_noise(value: str) -> bool:
    text = clean_text(value)
    if len(text) < 8:
        return True
    if re.search(r"https?://|www\.", text):
        return True
    if re.fullmatch(r"[ㅋㅎㅠㅜ!?.~\s]+", text):
        return True
    if len(set(text)) <= 2 and len(text) >= 10:
        return True
    return False


def extract_video_id(url_or_id: str) -> str:
    candidate = clean_text(url_or_id)
    if not candidate:
        return ""
    if re.fullmatch(r"[\w-]{11}", candidate):
        return candidate

    patterns = [
        r"v=([\w-]{11})",
        r"youtu\.be/([\w-]{11})",
        r"/shorts/([\w-]{11})",
        r"/live/([\w-]{11})",
        r"/embed/([\w-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, candidate)
        if match:
            return match.group(1)
    return ""


def http_get_json(url: str, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    request = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ApiError(f"외부 API 호출 실패: HTTP {exc.code} {detail[:240]}") from exc
    except URLError as exc:
        raise ApiError(f"외부 API 호출 실패: {exc.reason}") from exc


def http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=raw, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ApiError(f"외부 API 호출 실패: HTTP {exc.code} {detail[:240]}") from exc
    except URLError as exc:
        raise ApiError(f"외부 API 호출 실패: {exc.reason}") from exc


def fetch_video_metadata(video_id: str, api_key: str) -> Dict[str, Any]:
    params = urlencode(
        {
            "part": "snippet,statistics",
            "id": video_id,
            "key": api_key,
        }
    )
    data = http_get_json(f"https://www.googleapis.com/youtube/v3/videos?{params}")
    items = data.get("items") or []
    if not items:
        raise ApiError("영상 정보를 찾지 못했습니다. URL 또는 API Key를 확인해주세요.")
    snippet = items[0].get("snippet", {})
    return {
        "title": clean_text(snippet.get("title", "")),
        "channelTitle": clean_text(snippet.get("channelTitle", "")),
        "publishedAt": snippet.get("publishedAt", ""),
        "videoId": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def fetch_youtube_comments(video_id: str, api_key: str, limit: int, order: str) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    page_token = ""

    while len(collected) < limit:
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(100, limit),
            "textFormat": "plainText",
            "order": order,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        payload = http_get_json(
            f"https://www.googleapis.com/youtube/v3/commentThreads?{urlencode(params)}"
        )
        items = payload.get("items") or []
        if not items:
            break

        for item in items:
            top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            if top:
                collected.append(
                    {
                        "author": clean_text(top.get("authorDisplayName", "익명")),
                        "text": clean_text(top.get("textOriginal") or top.get("textDisplay") or ""),
                        "likeCount": int(top.get("likeCount", 0) or 0),
                        "publishedAt": top.get("publishedAt", ""),
                        "isReply": False,
                    }
                )

            replies = item.get("replies", {}).get("comments", []) or []
            for reply in replies:
                snippet = reply.get("snippet", {})
                collected.append(
                    {
                        "author": clean_text(snippet.get("authorDisplayName", "익명")),
                        "text": clean_text(snippet.get("textOriginal") or snippet.get("textDisplay") or ""),
                        "likeCount": int(snippet.get("likeCount", 0) or 0),
                        "publishedAt": snippet.get("publishedAt", ""),
                        "isReply": True,
                    }
                )
                if len(collected) >= limit:
                    break

            if len(collected) >= limit:
                break

        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break

    return collected[:limit]


def parse_manual_comments(text: str) -> List[Dict[str, Any]]:
    comments = []
    for index, line in enumerate((text or "").splitlines(), start=1):
        cleaned = clean_text(line)
        if not cleaned:
            continue
        comments.append(
            {
                "author": f"수동입력 {index}",
                "text": cleaned,
                "likeCount": 0,
                "publishedAt": "",
                "isReply": False,
            }
        )
    return comments


def filter_comments(comments: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    unique: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    for comment in comments:
        text = clean_text(comment.get("text", ""))
        if looks_like_noise(text):
            skipped += 1
            continue

        payload = {
            "author": clean_text(comment.get("author", "익명")),
            "text": text,
            "likeCount": int(comment.get("likeCount", 0) or 0),
            "publishedAt": comment.get("publishedAt", ""),
            "isReply": bool(comment.get("isReply", False)),
        }

        key = dedupe_key(text)
        if not key:
            skipped += 1
            continue

        existing = unique.get(key)
        if not existing or (payload["likeCount"], len(payload["text"])) > (
            existing["likeCount"],
            len(existing["text"]),
        ):
            unique[key] = payload

    filtered = sorted(unique.values(), key=lambda item: (item["likeCount"], len(item["text"])), reverse=True)
    return filtered, skipped


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z]{2,}|[가-힣]{2,}", text.lower())
    disallowed_suffixes = ("습니다", "했어요", "이에요", "네요", "겠어요", "였어요")
    return [
        token
        for token in tokens
        if token not in STOPWORDS and not token.endswith(disallowed_suffixes)
    ]


def normalize_title_seed(title: str) -> str:
    cleaned = clean_text(title)
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", cleaned)
    cleaned = cleaned.replace("EBS", "").strip(" -")
    return cleaned or "위대한 수업"


def classify_comment(text: str) -> List[str]:
    labels = []
    for label, markers in CATEGORY_RULES.items():
        if any(marker in text for marker in markers):
            labels.append(label)
    return labels or ["일반 반응"]


def summarize_sentiment(comments: List[Dict[str, Any]]) -> str:
    positive = 0
    critical = 0
    for comment in comments:
        text = comment["text"]
        if any(marker in text for marker in CRITICAL_MARKERS):
            critical += 1
        elif any(marker in text for marker in POSITIVE_MARKERS):
            positive += 1

    if positive > critical * 2:
        return "긍정/공감 중심"
    if critical and critical >= positive:
        return "의견이 갈리는 편"
    return "차분한 관찰형"


def build_local_summary(video: Dict[str, Any], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    keyword_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    joined_text = " ".join(comment["text"] for comment in comments)

    for comment in comments:
        weight = max(1, min(5, comment["likeCount"] // 25 + 1))
        keyword_counter.update({token: weight for token in tokenize(comment["text"])})
        category_counter.update(classify_comment(comment["text"]))

    top_keywords = [word for word, _ in keyword_counter.most_common(8)]
    top_categories = [
        {"label": label, "count": count}
        for label, count in category_counter.most_common(5)
    ]
    mood_label = summarize_sentiment(comments)

    representative_quotes = comments[: min(3, len(comments))]
    title_seed = normalize_title_seed(video.get("title", ""))
    suggested_title = f"[위대한 수업] {title_seed} 댓글 반응 정리와 후기 포인트"

    key_points: List[str] = []
    if top_categories:
        first = top_categories[0]
        key_points.append(
            f"가장 많이 포착된 반응은 '{first['label']}'이며, 전체 분위기를 이끄는 핵심 축으로 보입니다."
        )
    if any(marker in joined_text for marker in ["어렵지", "쉽게", "차분", "정리돼서"]):
        key_points.append("어려운 주제를 차분하고 쉽게 풀어준 전달 방식이 특히 좋았다는 평가가 많았습니다.")
    elif any(marker in joined_text for marker in ["현실적", "사례", "적용"]):
        key_points.append("현실적인 예시와 바로 적용 가능한 통찰이 강연의 장점으로 자주 언급됐습니다.")
    elif top_keywords:
        key_points.append(
            f"반복적으로 언급된 키워드는 {', '.join(top_keywords[:3])} 수준이었고, 핵심 장면에 대한 회고가 이어졌습니다."
        )

    if any(marker in joined_text for marker in ["다시", "메모", "한 번 더", "추천"]):
        key_points.append("메모해두고 다시 보고 싶다는 반응이 이어져 재시청 가치가 높은 강연으로 받아들여졌습니다.")
    elif any(item["label"] == "비판/추가논의" for item in top_categories):
        key_points.append("일부 댓글에서는 보완되었으면 하는 지점도 언급되어 균형 잡힌 후기 구성이 가능합니다.")
    else:
        key_points.append("전체적으로는 강연을 추천하거나 다시 보고 싶다는 반응이 우세했습니다.")

    audience_reactions = []
    if top_categories:
        audience_reactions.append(f"배움과 공감 중심으로 반응이 모였습니다.")
    if representative_quotes:
        audience_reactions.append("강연이 어렵지 않게 정리되었다는 평가가 반복적으로 확인됩니다.")
    if any("부모님" in comment["text"] for comment in comments):
        audience_reactions.append("가족과 함께 보기 좋은 강연이라는 반응도 확인됩니다.")

    seo_keywords = ["위대한 수업", "EBS 강연 후기", "유튜브 댓글 반응"] + top_keywords[:4]

    mood_text = (
        f"댓글 분위기는 '{mood_label}'에 가깝습니다. "
        f"특히 {', '.join(item['label'] for item in top_categories[:3])} 반응이 반복적으로 등장했습니다."
    )

    return {
        "engine": "heuristic",
        "engineLabel": "로컬 휴리스틱",
        "moodLabel": mood_label,
        "moodText": mood_text,
        "categories": top_categories,
        "topKeywords": top_keywords,
        "representativeQuotes": representative_quotes,
        "keyPoints": key_points,
        "audienceReactions": audience_reactions,
        "suggestedTitle": suggested_title,
        "seoKeywords": seo_keywords,
        "closingHook": "댓글 흐름만 봐도 왜 이 강연이 꾸준히 회자되는지 납득되는 편입니다.",
    }


def extract_json_object(content: str) -> Dict[str, Any]:
    text = clean_text(content)
    if not text:
        raise ApiError("OpenAI 응답이 비어 있습니다.")

    fenced = re.search(r"\{.*\}", text, re.DOTALL)
    candidate = fenced.group(0) if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ApiError("OpenAI 응답을 JSON으로 변환하지 못했습니다.") from exc


def build_openai_summary(
    video: Dict[str, Any],
    comments: List[Dict[str, Any]],
    api_key: str,
    model: str,
) -> Dict[str, Any]:
    prompt_comments = comments[: min(60, len(comments))]
    comment_block = "\n".join(
        f"- ({item['likeCount']} likes) {item['text']}" for item in prompt_comments
    )

    system_prompt = (
        "당신은 한국어 콘텐츠 마케터입니다. "
        "유튜브 댓글을 바탕으로 네이버 블로그 후기 초안을 위한 구조화 요약을 JSON으로만 반환하세요."
    )

    user_prompt = f"""
영상 제목: {video.get("title", "")}
채널명: {video.get("channelTitle", "")}
댓글 수: {len(comments)}

반환 형식:
{{
  "moodLabel": "짧은 분위기 라벨",
  "moodText": "전체 분위기를 2문장으로 설명",
  "categories": [{{"label":"카테고리","count":12}}],
  "topKeywords": ["키워드1", "키워드2"],
  "representativeQuotes": [{{"text":"대표 댓글", "author":"익명", "likeCount":0}}],
  "keyPoints": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
  "audienceReactions": ["반응 1", "반응 2", "반응 3"],
  "suggestedTitle": "블로그 제목",
  "seoKeywords": ["SEO 키워드"],
  "closingHook": "마무리 문장"
}}

주의:
- 사실로 확인되지 않은 내용은 만들지 말 것
- 댓글에 근거한 내용만 정리할 것
- 결과는 한국어로 작성할 것
- JSON 외 텍스트를 섞지 말 것

댓글:
{comment_block}
""".strip()

    payload = {
        "model": model or "gpt-4.1-mini",
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = http_post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = extract_json_object(content)
    return {
        "engine": "openai",
        "engineLabel": f"OpenAI ({payload['model']})",
        "moodLabel": clean_text(parsed.get("moodLabel", "")) or "분석 완료",
        "moodText": clean_text(parsed.get("moodText", "")),
        "categories": parsed.get("categories", []) or [],
        "topKeywords": parsed.get("topKeywords", []) or [],
        "representativeQuotes": parsed.get("representativeQuotes", []) or [],
        "keyPoints": parsed.get("keyPoints", []) or [],
        "audienceReactions": parsed.get("audienceReactions", []) or [],
        "suggestedTitle": clean_text(parsed.get("suggestedTitle", "")),
        "seoKeywords": parsed.get("seoKeywords", []) or [],
        "closingHook": clean_text(parsed.get("closingHook", "")),
    }


def tone_label(tone: str) -> str:
    return {
        "review": "후기형",
        "info": "정보형",
        "warm": "감성형",
    }.get(tone, "후기형")


def to_hashtag(value: str) -> str:
    candidate = re.sub(r"[^0-9A-Za-z가-힣]+", "", clean_text(value))
    if not candidate:
        return ""
    return f"#{candidate}"


def derive_topic_hashtag(title: str) -> str:
    words = re.findall(r"[0-9A-Za-z가-힣]+", normalize_title_seed(title))
    words = [word for word in words if len(word) >= 2]
    if not words:
        return ""
    candidate = "".join(words[-2:]) if len(words) >= 2 else words[-1]
    if len(candidate) > 14:
        candidate = words[-1]
    return to_hashtag(candidate)


def build_sections(
    video: Dict[str, Any],
    summary: Dict[str, Any],
    collection: Dict[str, Any],
    template: Dict[str, Any],
) -> List[Tuple[str, List[str]]]:
    video_title = normalize_title_seed(video.get("title", "위대한 수업"))
    tone = template.get("tone", "review")
    seo_focus = clean_text(template.get("seoFocus", ""))
    cta = clean_text(template.get("cta", ""))

    intro = (
        f"EBS <위대한 수업> '{video_title}' 편은 댓글만 훑어봐도 시청자들이 어디에서 멈추고, "
        f"무엇을 오래 곱씹었는지 분명하게 드러납니다. 이번 글에서는 정제된 댓글 "
        f"{collection['filteredCount']}개를 기준으로 반응의 결을 정리해봤습니다."
    )

    if tone == "info":
        intro = (
            f"이번 포스팅은 '{video_title}' 편의 댓글 반응을 바탕으로 핵심 인사이트를 정리한 기록입니다. "
            f"인기 댓글과 반복 표현을 기준으로 어떤 포인트가 주목받았는지 살펴보겠습니다."
        )
    elif tone == "warm":
        intro = (
            f"댓글을 읽다 보면 강연이 끝난 뒤에도 시청자들 마음에 오래 남는 문장이 무엇인지 보입니다. "
            f"'{video_title}' 편 역시 배움과 공감이 오래 이어진 강연이었습니다."
        )

    overview = [
        summary["moodText"],
        f"상위 반응은 {', '.join(item['label'] for item in summary['categories'][:3]) or '일반 반응'} 중심으로 모였습니다.",
    ]

    insights = summary["keyPoints"][:]
    if seo_focus:
        insights.append(f"검색 유입 관점에서는 '{seo_focus}' 키워드와 함께 묶어 소개하기에 적합합니다.")

    reactions = summary["audienceReactions"][:]
    if template.get("includeQuotes", True) and summary["representativeQuotes"]:
        quote = summary["representativeQuotes"][0]
        reactions.append(
            f"대표 댓글로는 \"{quote['text']}\" 같은 반응이 눈에 띄었습니다."
        )

    ending_lines = [
        summary.get("closingHook", "").strip() or "댓글 반응만으로도 이 강연이 왜 회자되는지 확인할 수 있습니다.",
    ]
    if cta:
        ending_lines.append(cta)
    else:
        ending_lines.append("차분히 생각할 거리를 찾는 분이라면 한 번쯤 직접 시청해보길 권합니다.")

    return [
        ("도입", [intro]),
        ("댓글 분위기 한눈에 보기", overview),
        ("많이 언급된 핵심 포인트", insights),
        ("인상 깊은 시청자 반응", reactions),
        ("마무리", ending_lines),
    ]


def build_markdown_body(sections: List[Tuple[str, List[str]]]) -> str:
    blocks = []
    for heading, paragraphs in sections:
        blocks.append(f"## {heading}")
        blocks.append("")
        for paragraph in paragraphs:
            if paragraph:
                blocks.append(paragraph)
                blocks.append("")
    return "\n".join(blocks).strip()


def build_html_body(sections: List[Tuple[str, List[str]]]) -> str:
    parts = []
    for heading, paragraphs in sections:
        parts.append(f"<h2>{html.escape(heading)}</h2>")
        for paragraph in paragraphs:
            parts.append(f"<p>{html.escape(paragraph)}</p>")
    return "\n".join(parts)


def markdownish_to_html(markdown_body: str) -> str:
    blocks = []
    for chunk in re.split(r"\n{2,}", markdown_body.strip()):
        text = chunk.strip()
        if not text:
            continue
        if text.startswith("## "):
            blocks.append(f"<h2>{html.escape(text[3:].strip())}</h2>")
        else:
            blocks.append(f"<p>{html.escape(text).replace(chr(10), '<br />')}</p>")
    return "\n".join(blocks)


def build_draft(
    video: Dict[str, Any],
    collection: Dict[str, Any],
    summary: Dict[str, Any],
    template: Dict[str, Any],
) -> Dict[str, Any]:
    title = summary.get("suggestedTitle") or f"[위대한 수업] {video.get('title', '강연')} 댓글 후기"
    sections = build_sections(video, summary, collection, template)
    markdown_body = build_markdown_body(sections)
    html_body = build_html_body(sections)

    hashtags = ["#위대한수업", "#EBS", "#강연후기", "#유튜브댓글반응"]
    topic_tag = derive_topic_hashtag(video.get("title", ""))
    if topic_tag:
        hashtags.append(topic_tag)

    for keyword in clean_text(template.get("seoFocus", "")).split(","):
        tag = to_hashtag(keyword)
        if tag:
            hashtags.append(tag)

    unique_hashtags = []
    for tag in hashtags:
        if tag not in unique_hashtags:
            unique_hashtags.append(tag)

    return {
        "title": clean_text(title),
        "markdownBody": markdown_body,
        "htmlBody": html_body,
        "hashtags": unique_hashtags[:8],
        "toneLabel": tone_label(template.get("tone", "review")),
    }


def build_publish_info(publish: Dict[str, Any]) -> Dict[str, Any]:
    blog_id = clean_text(publish.get("naverBlogId", ""))
    writer_url = ""
    if blog_id:
        writer_url = (
            "https://blog.naver.com/PostWriteForm.naver?"
            f"blogId={quote(blog_id)}&Redirect=Write&redirect=Write"
        )

    return {
        "mode": publish.get("mode", "save"),
        "writerUrl": writer_url,
        "notes": [
            "네이버는 공개 발행 API가 확인되지 않아, MVP에서는 저장 패키지와 작성 화면 핸드오프를 제공합니다.",
            "공식 에디터 도움말과 임시 저장 안내를 함께 제공합니다.",
        ],
        "helpLinks": [
            OFFICIAL_NAVER_EDITOR_GUIDE,
            OFFICIAL_NAVER_DRAFT_GUIDE,
        ],
    }


def build_run_summary(video: Dict[str, Any], collection: Dict[str, Any], summary: Dict[str, Any]) -> str:
    return (
        f"'{video.get('title', '강연')}' 기준으로 댓글 {collection['filteredCount']}개를 정리했고, "
        f"{summary['engineLabel']} 엔진으로 초안을 생성했습니다."
    )


def collect_source(source: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    mode = source.get("mode", "demo")
    notices: List[str] = []

    if mode == "manual":
        comments = parse_manual_comments(source.get("manualComments", ""))
        if not comments:
            raise ApiError("수동 댓글 입력이 비어 있습니다.")
        video = {
            "title": clean_text(source.get("manualVideoTitle", "")) or "[수동 입력] 위대한 수업 댓글 모음",
            "channelTitle": "수동 입력",
            "publishedAt": "",
            "videoId": "",
            "url": "",
        }
        return video, comments, notices

    if mode == "youtube":
        video_url = clean_text(source.get("videoUrl", ""))
        api_key = clean_text(source.get("youtubeApiKey", ""))
        if not video_url or not api_key:
            raise ApiError("유튜브 댓글 수집을 위해 영상 URL과 YouTube API Key가 모두 필요합니다.")
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ApiError("유튜브 URL에서 videoId를 찾지 못했습니다.")

        video = fetch_video_metadata(video_id, api_key)
        comments = fetch_youtube_comments(
            video_id,
            api_key,
            int(source.get("commentLimit", 200) or 200),
            source.get("commentOrder", "relevance"),
        )
        if not comments:
            notices.append("댓글이 비어 있거나 수집 가능한 댓글이 적었습니다.")
        return video, comments, notices

    notices.append("데모 댓글로 실행되었습니다.")
    return SAMPLE_VIDEO, SAMPLE_COMMENTS[:], notices


def run_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("source", {})
    summary_config = payload.get("summary", {})
    template = payload.get("template", {})
    publish = payload.get("publish", {})

    video, raw_comments, notices = collect_source(source)
    filtered_comments, skipped_count = filter_comments(raw_comments)
    if not filtered_comments:
        raise ApiError("정제 후 남은 댓글이 없습니다. 댓글 입력이나 필터 조건을 확인해주세요.")

    collection = {
        "rawCount": len(raw_comments),
        "filteredCount": len(filtered_comments),
        "skippedCount": skipped_count,
        "video": video,
        "comments": filtered_comments[:20],
    }

    summary_mode = summary_config.get("mode", "heuristic")
    summary: Dict[str, Any]
    if summary_mode == "openai":
        api_key = clean_text(summary_config.get("openaiApiKey", ""))
        if not api_key:
            notices.append("OpenAI API Key가 없어 로컬 휴리스틱 요약으로 대체했습니다.")
            summary = build_local_summary(video, filtered_comments)
        else:
            try:
                summary = build_openai_summary(
                    video,
                    filtered_comments,
                    api_key,
                    clean_text(summary_config.get("openaiModel", "")) or "gpt-4.1-mini",
                )
            except ApiError as exc:
                notices.append(f"OpenAI 요약에 실패해 로컬 휴리스틱 요약으로 대체했습니다. 사유: {exc}")
                summary = build_local_summary(video, filtered_comments)
    else:
        summary = build_local_summary(video, filtered_comments)

    draft = build_draft(video, collection, summary, template)
    publish_info = build_publish_info(publish)
    notices.extend(publish_info["notes"])

    return {
        "runSummary": build_run_summary(video, collection, summary),
        "collection": collection,
        "summary": summary,
        "draft": draft,
        "publish": publish_info,
        "notices": notices,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
    }


def slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "-", clean_text(value))
    normalized = normalized.strip("-")
    return normalized[:48] or "blog-draft"


def save_output(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload.get("result")
    edited = payload.get("editedDraft") or {}
    if not result:
        raise ApiError("저장할 결과 데이터가 없습니다.")

    title = clean_text(edited.get("title", "")) or clean_text(result.get("draft", {}).get("title", "blog-draft"))
    markdown_body = (edited.get("markdownBody", "") or "").strip()
    if not markdown_body:
        markdown_body = result.get("draft", {}).get("markdownBody", "")

    hashtags = edited.get("hashtags") or result.get("draft", {}).get("hashtags", [])
    hashtags_text = " ".join(hashtags)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = OUTPUT_DIR / f"{timestamp}-{slugify(title)}"
    folder.mkdir(parents=True, exist_ok=True)

    markdown = f"# {title}\n\n{markdown_body}\n\n{hashtags_text}\n"
    html_body = markdownish_to_html(markdown_body)
    html_doc = f"""<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)}</title>
  </head>
  <body>
    <h1>{html.escape(title)}</h1>
    {html_body}
    <p>{html.escape(hashtags_text)}</p>
  </body>
</html>
"""
    text_doc = f"{title}\n\n{markdown_body}\n\n{hashtags_text}\n"

    metadata = {
        "savedAt": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "hashtags": hashtags,
        "sourceVideo": result.get("collection", {}).get("video", {}),
        "summaryEngine": result.get("summary", {}).get("engineLabel", ""),
        "writerUrl": result.get("publish", {}).get("writerUrl", ""),
    }

    files = [
        ("Markdown", folder / "post.md", markdown),
        ("HTML", folder / "post.html", html_doc),
        ("Plain text", folder / "post.txt", text_doc),
        ("Metadata", folder / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2)),
        (
            "Representative comments",
            folder / "comments.json",
            json.dumps(result.get("collection", {}).get("comments", []), ensure_ascii=False, indent=2),
        ),
    ]

    for _, path, content in files:
        path.write_text(content, encoding="utf-8")

    return {
        "paths": [{"label": label, "path": str(path)} for label, path, _ in files]
    }


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            write_json(self, 200, {"ok": True, "time": datetime.now().isoformat(timespec="seconds")})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = read_json(self)
            if parsed.path == "/api/pipeline/run":
                write_json(self, 200, run_pipeline(payload))
                return
            if parsed.path == "/api/output/save":
                write_json(self, 200, save_output(payload))
                return
            write_json(self, 404, {"error": "지원하지 않는 API 경로입니다."})
        except ApiError as exc:
            write_json(self, 400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            write_json(self, 500, {"error": f"서버 내부 오류: {exc}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="댓글 기반 블로그 포스팅 자동화 MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Server running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
