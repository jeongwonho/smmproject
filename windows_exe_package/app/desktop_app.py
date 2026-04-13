#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import sys
import textwrap
import webbrowser
from pathlib import Path

from server import ApiError, run_pipeline, save_output


SAMPLE_MANUAL_COMMENTS = """정말 오랜만에 댓글까지 읽게 되는 강연이었어요. 내용이 어렵지 않게 정리돼서 좋았습니다.
위대한 수업은 늘 좋은데 이번 편은 특히 현실적인 예시가 많아서 기억에 남네요.
강연자 설명이 차분해서 집중이 잘 됐고, 중간중간 던지는 질문도 생각할 거리를 줬어요.
댓글 보니 저처럼 다시 보겠다는 분이 많네요. 저도 메모하면서 한 번 더 볼 예정입니다.
단순한 지식 전달이 아니라 삶에 바로 적용할 수 있는 통찰이 있었다는 점이 좋았습니다.
후반부는 조금 더 사례가 있었으면 좋겠다는 아쉬움도 있지만 전체적으로 만족합니다.
EBS 위대한 수업은 이런 깊이 있는 콘텐츠를 꾸준히 해줘서 늘 고맙습니다.
전문적인 이야기인데도 어렵지 않게 풀어줘서 부모님과 함께 보기 좋겠어요."""


def print_block(title: str, body: str = "") -> None:
    line = "=" * 72
    print(f"\n{line}\n{title}\n{line}")
    if body:
        print(body.strip())


def prompt_text(label: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    if secret:
        value = getpass.getpass(f"{label}{suffix}: ")
    else:
        value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_choice(label: str, options: list[tuple[str, str]], default: str) -> str:
    print(f"\n{label}")
    for index, (_, title) in enumerate(options, start=1):
        marker = " (기본값)" if options[index - 1][0] == default else ""
        print(f"{index}. {title}{marker}")

    raw = input("번호 선택: ").strip()
    if not raw:
        return default
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(options):
            return options[index][0]
    for code, title in options:
        if raw == code or raw == title:
            return code
    print("유효하지 않은 입력이라 기본값을 사용합니다.")
    return default


def prompt_yes_no(label: str, default: bool = True) -> bool:
    default_label = "Y/n" if default else "y/N"
    raw = input(f"{label} [{default_label}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true", "네", "예"}


def prompt_multiline(label: str, default_text: str = "") -> str:
    print(f"\n{label}")
    print("여러 줄 입력 후 마지막 줄에 END 만 입력하면 종료됩니다.")
    if default_text:
        print("엔터만 입력하면 기본 데모 댓글을 사용합니다.")
    lines: list[str] = []
    first_line = input("> ")
    if not first_line.strip() and default_text:
        return default_text
    if first_line.strip() == "END":
        return "\n".join(lines)
    lines.append(first_line)
    while True:
        line = input("> ")
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def build_interactive_payload() -> dict:
    print_block(
        "댓글 브리프 스튜디오",
        "브라우저 없이 실행되는 로컬 콘솔 버전입니다.\n"
        "기본값만으로도 데모 파이프라인을 바로 실행할 수 있습니다.",
    )

    source_mode = prompt_choice(
        "댓글 소스를 선택하세요.",
        [
            ("demo", "데모 댓글 사용"),
            ("youtube", "유튜브 댓글 수집"),
            ("manual", "수동 댓글 붙여넣기"),
        ],
        "demo",
    )

    source = {
        "mode": source_mode,
        "videoUrl": "",
        "youtubeApiKey": "",
        "commentLimit": 200,
        "commentOrder": "relevance",
        "manualVideoTitle": "[위대한 수업] 인간을 움직이는 선택의 기술",
        "manualComments": SAMPLE_MANUAL_COMMENTS,
    }

    if source_mode == "youtube":
        source["videoUrl"] = prompt_text("유튜브 영상 URL")
        source["youtubeApiKey"] = prompt_text("YouTube Data API Key", secret=True)
        source["commentLimit"] = int(
            prompt_choice(
                "수집 개수를 선택하세요.",
                [("100", "100개"), ("200", "200개"), ("300", "300개"), ("500", "500개")],
                "200",
            )
        )
        source["commentOrder"] = prompt_choice(
            "정렬 기준을 선택하세요.",
            [("relevance", "인기순"), ("time", "최신순")],
            "relevance",
        )
    elif source_mode == "manual":
        source["manualVideoTitle"] = prompt_text("영상 제목", source["manualVideoTitle"])
        source["manualComments"] = prompt_multiline("댓글을 한 줄씩 붙여넣으세요.", SAMPLE_MANUAL_COMMENTS)

    summary_mode = prompt_choice(
        "요약 방식을 선택하세요.",
        [("heuristic", "로컬 휴리스틱 요약"), ("openai", "OpenAI 요약")],
        "heuristic",
    )
    summary = {
        "mode": summary_mode,
        "openaiApiKey": "",
        "openaiModel": "gpt-4.1-mini",
    }
    if summary_mode == "openai":
        summary["openaiApiKey"] = prompt_text("OpenAI API Key", secret=True)
        summary["openaiModel"] = prompt_text("모델명", "gpt-4.1-mini")

    template = {
        "tone": prompt_choice(
            "문체 톤을 선택하세요.",
            [("review", "후기형"), ("info", "정보형"), ("warm", "감성형")],
            "review",
        ),
        "seoFocus": prompt_text("SEO 키워드", "위대한 수업, EBS 강연 후기"),
        "cta": prompt_text("마무리 문장", "한 번쯤 다시 보며 곱씹어볼 만한 강연입니다."),
        "includeQuotes": prompt_yes_no("대표 댓글을 본문에 포함할까요?", True),
    }

    publish = {
        "mode": prompt_choice(
            "결과 처리 방식을 선택하세요.",
            [("save", "파일 저장만"), ("naver-handoff", "네이버 작성 화면용 핸드오프")],
            "save",
        ),
        "naverBlogId": "",
    }
    if publish["mode"] == "naver-handoff":
        publish["naverBlogId"] = prompt_text("네이버 블로그 ID", "sample_blog_id")

    return {
        "source": source,
        "summary": summary,
        "template": template,
        "publish": publish,
    }


def build_demo_payload() -> dict:
    return {
        "source": {"mode": "demo"},
        "summary": {"mode": "heuristic"},
        "template": {
            "tone": "review",
            "seoFocus": "위대한 수업, EBS 강연 후기",
            "cta": "한 번쯤 다시 보며 곱씹어볼 만한 강연입니다.",
            "includeQuotes": True,
        },
        "publish": {
            "mode": "naver-handoff",
            "naverBlogId": "sample_blog_id",
        },
    }


def print_result(result: dict) -> None:
    summary = result["summary"]
    collection = result["collection"]
    draft = result["draft"]

    print_block("실행 결과", result["runSummary"])

    metrics = [
        f"- 원본 댓글: {collection['rawCount']}",
        f"- 정제 댓글: {collection['filteredCount']}",
        f"- 요약 엔진: {summary['engineLabel']}",
        f"- 대표 분위기: {summary['moodLabel']}",
    ]
    print("\n".join(metrics))

    print_block(
        "카테고리",
        "\n".join(f"- {item['label']} · {item['count']}건" for item in summary.get("categories", [])),
    )
    print_block("키워드", ", ".join(summary.get("topKeywords", [])) or "없음")

    quotes = []
    for quote in summary.get("representativeQuotes", []):
        quotes.append(f"[{quote.get('author', '시청자')} · 좋아요 {quote.get('likeCount', 0)}]")
        quotes.append(quote.get("text", ""))
        quotes.append("")
    print_block("대표 댓글", "\n".join(quotes).strip() or "대표 댓글이 없습니다.")

    print_block("생성된 제목", draft.get("title", ""))
    print_block("본문 초안", draft.get("markdownBody", ""))
    print_block("해시태그", " ".join(draft.get("hashtags", [])))

    if result.get("publish", {}).get("writerUrl"):
        print_block("네이버 작성 URL", result["publish"]["writerUrl"])

    if result.get("notices"):
        print_block("운영 메모", "\n".join(f"- {item}" for item in result["notices"]))


def maybe_edit_draft(result: dict, interactive: bool) -> dict:
    draft = result["draft"]
    edited = {
        "title": draft.get("title", ""),
        "markdownBody": draft.get("markdownBody", ""),
        "hashtags": draft.get("hashtags", []),
    }

    if not interactive:
        return edited

    if prompt_yes_no("제목을 수정할까요?", False):
        edited["title"] = prompt_text("새 제목", edited["title"])

    if prompt_yes_no("해시태그를 수정할까요?", False):
        tags = prompt_text("해시태그", " ".join(edited["hashtags"]))
        edited["hashtags"] = [item for item in tags.split() if item]

    if prompt_yes_no("본문을 통째로 다시 입력할까요?", False):
        edited["markdownBody"] = prompt_multiline("새 본문을 입력하세요.", edited["markdownBody"])

    return edited


def perform_save(result: dict, edited_draft: dict) -> dict:
    payload = {
        "result": result,
        "editedDraft": edited_draft,
    }
    return save_output(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="댓글 브리프 스튜디오 로컬 실행형 앱")
    parser.add_argument("--demo", action="store_true", help="질문 없이 데모 파이프라인으로 즉시 실행")
    parser.add_argument("--save", action="store_true", help="실행 후 결과를 바로 저장")
    parser.add_argument("--json", action="store_true", help="결과 전체를 JSON으로 출력")
    parser.add_argument("--open-writer", action="store_true", help="실행 후 네이버 작성 URL을 브라우저로 열기")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        payload = build_demo_payload() if args.demo else build_interactive_payload()
        result = run_pipeline(payload)
    except ApiError as exc:
        print(f"\n오류: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n취소되었습니다.")
        return 130

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_result(result)

    edited_draft = maybe_edit_draft(result, interactive=not args.demo)

    if args.save or (not args.demo and prompt_yes_no("결과 파일을 저장할까요?", True)):
        try:
            saved = perform_save(result, edited_draft)
        except ApiError as exc:
            print(f"\n저장 실패: {exc}", file=sys.stderr)
            return 1
        print_block(
            "저장 완료",
            "\n".join(f"- {item['label']}: {item['path']}" for item in saved.get("paths", [])),
        )

    writer_url = result.get("publish", {}).get("writerUrl", "")
    if writer_url and (args.open_writer or (not args.demo and prompt_yes_no("네이버 작성 화면을 열까요?", False))):
        webbrowser.open(writer_url)
        print("\n기본 브라우저에서 네이버 작성 화면을 열었습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
