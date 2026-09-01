#!/usr/bin/env python3
"""Audit the static WITH LIVING site against the 13 runday-seo checks."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://www.withliving.kr"
KST = timezone(timedelta(hours=9))
PUBLIC_EXCLUDES = {
    Path("story/admin.html"),
    Path("story/post.html"),
    Path("google069b9b51e6c6d70c.html"),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.in_title = False
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.head_links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.headings: list[int] = []
        self.jsonld: list[str] = []
        self.in_jsonld = False
        self.jsonld_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.metas.append(data)
        elif tag == "a":
            self.links.append(data)
        elif tag == "link":
            self.head_links.append(data)
        elif tag == "img":
            self.images.append(data)
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        elif tag == "script" and data.get("type") == "application/ld+json":
            self.in_jsonld = True
            self.jsonld_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_jsonld:
            self.jsonld.append("".join(self.jsonld_buffer).strip())
            self.in_jsonld = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
        if self.in_jsonld:
            self.jsonld_buffer.append(data)


def public_html_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.html")
        if path.relative_to(ROOT) not in PUBLIC_EXCLUDES and ".git" not in path.parts
    )


def parse_pages() -> dict[Path, PageParser]:
    result: dict[Path, PageParser] = {}
    for path in public_html_files():
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        result[path] = parser
    return result


def meta(parser: PageParser, key: str, value: str) -> str:
    for item in parser.metas:
        if item.get(key) == value:
            return item.get("content", "").strip()
    return ""


def canonical(parser: PageParser) -> str:
    for item in parser.head_links:
        if "canonical" in item.get("rel", "").split():
            return item.get("href", "").strip()
    return ""


def jsonld_types(parser: PageParser) -> tuple[set[str], list[str]]:
    types: set[str] = set()
    errors: list[str] = []
    for raw in parser.jsonld:
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue
        def visit(value: object) -> None:
            if isinstance(value, dict):
                kind = value.get("@type")
                if isinstance(kind, str):
                    types.add(kind)
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(item)
    return types, errors


def fix_external_rel(pages: dict[Path, PageParser]) -> int:
    changed = 0
    pattern = re.compile(r'<a\b(?P<attrs>[^>]*\btarget=["\']_blank["\'][^>]*)>', re.I)
    for path in pages:
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            attrs = match.group("attrs")
            if re.search(r'\brel=["\'][^"\']*\bnoopener\b', attrs, re.I):
                return match.group(0)
            changed += 1
            return f'<a{attrs} rel="noopener">'

        updated = pattern.sub(replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return changed


def audit(pages: dict[Path, PageParser]) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    rel = lambda path: str(path.relative_to(ROOT))

    titles: dict[str, list[str]] = {}
    failures = []
    for path, page in pages.items():
        title = page.title.strip()
        titles.setdefault(title, []).append(rel(path))
        description = meta(page, "name", "description")
        if not title or len(title) > 60 or not description:
            failures.append(rel(path))
    failures.extend(name for name, paths in titles.items() if not name or len(paths) > 1 for name in paths)
    results.append(("1", "통과" if not failures else "실패", "제목·설명 이상: " + ", ".join(sorted(set(failures))) if failures else "고유 title과 description 확인"))

    bad = [rel(path) for path, page in pages.items() if not canonical(page).startswith(DOMAIN)]
    results.append(("2", "통과" if not bad else "실패", "canonical 이상: " + ", ".join(bad) if bad else "배포 도메인 canonical 확인"))

    bad = []
    for path, page in pages.items():
        values = [meta(page, "property", key) for key in ("og:title", "og:description", "og:url")]
        image = meta(page, "property", "og:image")
        if not all(values) or (image and not image.startswith("https://")):
            bad.append(rel(path))
    results.append(("3", "통과" if not bad else "실패", "OG 이상: " + ", ".join(bad) if bad else "OG 필수값 확인"))

    bad = []
    for path, page in pages.items():
        skip = any(b - a > 1 for a, b in zip(page.headings, page.headings[1:]))
        if page.headings.count(1) != 1 or skip:
            bad.append(rel(path))
    results.append(("4", "통과" if not bad else "실패", "제목 구조 이상: " + ", ".join(bad) if bad else "H1 1개와 제목 순서 확인"))

    bad = [f"{rel(path)}:{img.get('src', '')}" for path, page in pages.items() for img in page.images if "alt" not in img]
    results.append(("5", "통과" if not bad else "실패", "alt 누락: " + ", ".join(bad) if bad else "이미지 alt 누락 없음"))

    bad = []
    for path, page in pages.items():
        types, errors = jsonld_types(page)
        expected: set[str] = set()
        relative = path.relative_to(ROOT)
        if relative == Path("index.html"):
            expected = {"Organization", "WebSite"}
        elif relative == Path("products.html"):
            expected = {"Product"}
        elif relative.parent == Path("story") and relative.name not in {"index.html"}:
            expected = {"BlogPosting", "BreadcrumbList"}
        if errors or not expected.issubset(types):
            bad.append(f"{rel(path)}({','.join(sorted(expected - types)) or 'JSON 오류'})")
    results.append(("6", "통과" if not bad else "실패", "JSON-LD 이상: " + ", ".join(bad) if bad else "필수 구조화 데이터 확인"))

    posts = json.loads((ROOT / "story/posts.json").read_text(encoding="utf-8"))
    public_urls = {f"{DOMAIN}/story/{post['url']}" for post in posts if post.get("url")}
    tree = ET.parse(ROOT / "sitemap.xml")
    sitemap_urls = {node.text or "" for node in tree.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    bad_urls = sorted(public_urls - sitemap_urls)
    forbidden = sorted(url for url in sitemap_urls if "admin.html" in url or "?id=" in url)
    results.append(("7", "통과" if not bad_urls and not forbidden else "실패", f"누락 {len(bad_urls)}개, 금지 URL {len(forbidden)}개"))

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    blocked_ai = any(re.search(rf"User-agent:\s*{bot}[\s\S]*?Disallow:\s*/", robots, re.I) for bot in ("GPTBot", "ClaudeBot", "PerplexityBot"))
    robots_ok = f"Sitemap: {DOMAIN}/sitemap.xml" in robots and "Disallow: /story/admin.html" in robots and not blocked_ai
    results.append(("8", "통과" if robots_ok else "실패", "sitemap·admin·AI 크롤러 규칙 확인"))

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    llms_ok = "## 이야기(블로그)" in llms and DOMAIN in llms and "위드리빙" in llms
    results.append(("9", "통과" if llms_ok else "실패", "브랜드·페이지·블로그 절 확인"))

    broken: list[str] = []
    unsafe: list[str] = []
    for path, page in pages.items():
        for link in page.links:
            href = link.get("href", "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            parsed = urlparse(href)
            if parsed.scheme in {"http", "https"}:
                if link.get("target") == "_blank" and "noopener" not in link.get("rel", "").split():
                    unsafe.append(f"{rel(path)}:{href}")
                continue
            target = (path.parent / parsed.path).resolve()
            if parsed.path and not target.exists():
                broken.append(f"{rel(path)}:{href}")
    results.append(("10", "통과" if not broken and not unsafe else "실패", f"깨진 링크 {len(broken)}개, noopener 누락 {len(unsafe)}개"))

    mismatches = []
    for post in posts:
        if not post.get("url"):
            continue
        target = ROOT / "story" / post["url"]
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        if not target.exists() or not post.get("author") or not post.get("date") or post["date"] not in text:
            mismatches.append(post.get("url", post.get("id", "알 수 없음")))
    results.append(("11", "통과" if not mismatches else "실패", "글 메타·정적 파일 이상: " + ", ".join(mismatches) if mismatches else "작성자·날짜·정적 URL 일치"))

    forbidden_claims = ("국내 1위", "업계 1위", "세계 최고", "100% 치료", "완치")
    claims = [f"{rel(path)}:{word}" for path in pages for word in forbidden_claims if word in path.read_text(encoding="utf-8")]
    results.append(("12", "통과" if not claims else "실패", "금지 표현: " + ", ".join(claims) if claims else "자동 탐지 금지 표현 없음(사람의 사실 확인 필요)"))

    bad = []
    for path, page in pages.items():
        viewport = meta(page, "name", "viewport")
        text = path.read_text(encoding="utf-8")
        if "width=device-width" not in viewport or re.search(r"width:\s*[4-9]\d{2,}px", text):
            bad.append(rel(path))
    results.append(("13", "통과" if not bad else "실패", "모바일 정적 검사 이상: " + ", ".join(bad) if bad else "viewport·고정폭 정적 검사 통과(375px 시각 확인 별도)"))
    return results


def write_report(results: list[tuple[str, str, str]], fixed: int) -> Path:
    path = ROOT / "reports/seo-audit.md"
    path.parent.mkdir(exist_ok=True)
    timestamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [
        "# 위드리빙 SEO·AEO·GEO 주간 점검",
        "",
        f"점검 시각: {timestamp}",
        "",
        "| 번호 | 판정 | 결과 |",
        "|---:|:---:|---|",
        *[f"| {number} | {status} | {detail.replace('|', '/')} |" for number, status, detail in results],
        "",
        f"자동 수정: 외부 새 창 링크의 `rel=\"noopener\"` 누락 {fixed}건",
        "",
        "## 사람이 직접 확인할 것",
        "",
        "- 생활용품 사용·관리·제품 관련 문장이 출처 및 실제 제품 정보와 일치하는지 확인",
        "- 실제 휴대전화 375px 화면에서 가로 스크롤·겹침·이미지 로딩 확인",
        "- Google Rich Results에서 FAQ·Breadcrumb 감지 확인",
        "- Google Search Console에서 새 글 색인 요청 및 소유권 확인",
        "- ChatGPT 또는 Perplexity에서 새 글 URL의 제목·FAQ 요약 확인",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="사실을 바꾸지 않는 안전한 문제만 수정")
    parser.add_argument("--strict", action="store_true", help="실패 항목이 있으면 종료 코드 1")
    args = parser.parse_args()
    pages = parse_pages()
    fixed = fix_external_rel(pages) if args.fix else 0
    if fixed:
        pages = parse_pages()
    results = audit(pages)
    report = write_report(results, fixed)
    print(report.relative_to(ROOT))
    for number, status, detail in results:
        print(f"{number:>2}. {status} — {detail}")
    if args.strict and any(status == "실패" for _, status, _ in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
