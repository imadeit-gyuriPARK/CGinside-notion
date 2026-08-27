"""
노션 회의 DB의 페이지 제목을 정해진 규칙대로 덮어쓰는 스크립트.

- LLM/AI 안 씀. 노션 속성 값을 규칙대로 문자열로 조립할 뿐이라 API 키도 비용도 없음.
- 기본은 dry-run(미리보기). 실제로 바꾸려면 --apply 를 붙임.

사용 예:
    python rename.py --show-props        # DB 속성 구조/값 확인 (규칙 설계용)
    python rename.py                     # 미리보기: "지금 제목 -> 바뀔 제목"
    python rename.py --apply             # 실제로 제목 덮어쓰기
    python rename.py --apply --limit 5   # 앞 5개만
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "").strip()


# ---------------------------------------------------------------------------
# 노션 속성 값 -> 파이썬 값 으로 뽑아내는 헬퍼
# ---------------------------------------------------------------------------
def plain_value(prop: dict):
    """노션 property 객체 하나에서 사람이 읽을 값을 최대한 뽑아낸다."""
    t = prop.get("type")
    v = prop.get(t)

    if t in ("title", "rich_text"):
        return "".join(part.get("plain_text", "") for part in v) if v else ""
    if t == "select":
        return v.get("name", "") if v else ""
    if t == "status":
        return v.get("name", "") if v else ""
    if t == "multi_select":
        return [o.get("name", "") for o in v] if v else []
    if t == "date":
        if not v:
            return ""
        return v.get("start", "") if not v.get("end") else f'{v["start"]}~{v["end"]}'
    if t == "people":
        return [p.get("name", "") for p in v] if v else []
    if t == "checkbox":
        return bool(v)
    if t == "number":
        return v
    if t == "url" or t == "email" or t == "phone_number":
        return v or ""
    if t == "formula":
        return v.get(v.get("type"), "") if v else ""
    if t == "rollup":
        inner = v.get("array") or v.get(v.get("type"))
        return inner
    if t == "created_time":
        return v
    if t == "unique_id":
        num = v.get("number") if v else None
        pre = v.get("prefix") if v else None
        return f"{pre}-{num}" if pre else str(num)
    return v


def page_props(page: dict) -> dict:
    """페이지의 모든 속성을 {이름: 값} 평평한 dict 로."""
    return {name: plain_value(p) for name, p in page.get("properties", {}).items()}


def current_title(page: dict) -> tuple[str, str]:
    """(title 속성 이름, 현재 제목 문자열) 반환."""
    for name, p in page.get("properties", {}).items():
        if p.get("type") == "title":
            return name, plain_value(p)
    raise RuntimeError("이 DB에서 title 타입 속성을 찾지 못했습니다.")


# ---------------------------------------------------------------------------
#  ↓↓↓  제목 규칙  ↓↓↓   (아직 미정 — 사용자가 규칙 주면 여기만 채우면 됨)
# ---------------------------------------------------------------------------
def build_title(props: dict) -> str:
    """
    props: {속성이름: 값} dict.  예) props["프로젝트"], props["날짜"], props["종류"]
    반환값: 이 페이지에 들어갈 새 제목 문자열.

    TODO: 실제 규칙으로 교체.
    예시)
        date = props.get("날짜", "")
        kind = props.get("종류", "")
        proj = props.get("프로젝트", "")
        return f"[{proj}] {date} {kind}".strip()
    """
    raise NotImplementedError(
        "제목 규칙이 아직 안 정해졌습니다. rename.py 의 build_title() 을 채워주세요.\n"
        "먼저 `python rename.py --show-props` 로 속성 이름과 값을 확인하세요."
    )


# ---------------------------------------------------------------------------
# 실행 로직
# ---------------------------------------------------------------------------
def iter_pages(notion: Client, database_id: str):
    cursor = None
    while True:
        resp = notion.databases.query(
            database_id=database_id,
            start_cursor=cursor,
            page_size=100,
        )
        yield from resp["results"]
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]


def cmd_show_props(notion: Client) -> int:
    pages = list(iter_pages(notion, NOTION_DATABASE_ID))
    if not pages:
        print("DB에 페이지가 없습니다.")
        return 0
    print(f"총 {len(pages)}개 페이지. 앞 3개의 속성 값:\n")
    for page in pages[:3]:
        tname, title = current_title(page)
        print(f"── 제목({tname}): {title!r}")
        for k, v in page_props(page).items():
            print(f"     {k!r}: {v!r}")
        print()
    return 0


def run(apply: bool, limit: int | None) -> int:
    notion = Client(auth=NOTION_TOKEN)
    pages = list(iter_pages(notion, NOTION_DATABASE_ID))
    if limit:
        pages = pages[:limit]

    changed = skipped = 0
    for page in pages:
        tname, old = current_title(page)
        new = build_title(page_props(page))
        if new == old:
            skipped += 1
            continue
        changed += 1
        print(f"  {old!r}\n    -> {new!r}")
        if apply:
            notion.pages.update(
                page_id=page["id"],
                properties={tname: {"title": [{"text": {"content": new}}]}},
            )

    mode = "적용됨" if apply else "미리보기 (실제 변경 없음 — --apply 붙이면 적용)"
    print(f"\n[{mode}] 바꿀 것 {changed}개, 이미 맞아서 건너뜀 {skipped}개")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="실제로 제목을 덮어쓴다 (기본은 미리보기)")
    ap.add_argument("--limit", type=int, default=None, help="앞 N개만 처리 (테스트용)")
    ap.add_argument("--show-props", action="store_true", help="DB 속성 이름/값만 출력하고 종료")
    args = ap.parse_args()

    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("NOTION_TOKEN / NOTION_DATABASE_ID 가 비어 있습니다. .env 를 확인하세요.", file=sys.stderr)
        return 1

    notion = Client(auth=NOTION_TOKEN)
    if args.show_props:
        return cmd_show_props(notion)
    return run(apply=args.apply, limit=args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
