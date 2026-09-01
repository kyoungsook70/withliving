#!/usr/bin/env python3
"""Generate and prepare one WITH LIVING story from story/ideas.md.

The script is intentionally dependency-free so it can run on GitHub Actions with
only Python and OPENAI_API_KEY. It updates every discovery file used by the site.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time, timezone, timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "story"
DOMAIN = "https://www.withliving.kr"
AUTHOR = "이경숙 위드리빙 대표"
BRAND = "위드리빙"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
KST = timezone(timedelta(hours=9))


def fail(message: str) -> None:
    raise SystemExit(f"오류: {message}")


def next_topic() -> str:
    text = (STORY / "ideas.md").read_text(encoding="utf-8")
    match = re.search(r"^- \[ \] (.+)$", text, re.MULTILINE)
    if not match:
        fail("story/ideas.md에 남은 미발행 주제가 없습니다.")
    return match.group(1).strip()


def unchecked_topics() -> list[str]:
    text = (STORY / "ideas.md").read_text(encoding="utf-8")
    return [item.strip() for item in re.findall(r"^- \[ \] (.+)$", text, re.MULTILINE)]


def call_openai(payload: dict) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        fail("OPENAI_API_KEY가 설정되지 않았습니다.")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        fail(f"OpenAI API 요청 실패({exc.code}): {detail}")
    except urllib.error.URLError as exc:
        fail(f"OpenAI API 연결 실패: {exc.reason}")

    output_text = "".join(
        part.get("text", "")
        for item in raw.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )
    if not output_text:
        fail(f"모델이 결과를 반환하지 않았습니다. 상태: {raw.get('status')}")
    return json.loads(output_text)


def replenish_topics() -> int:
    remaining = unchecked_topics()
    if len(remaining) >= 5:
        return 0
    brand = (STORY / "brand.md").read_text(encoding="utf-8")
    ideas_text = (STORY / "ideas.md").read_text(encoding="utf-8")
    posts = json.loads((STORY / "posts.json").read_text(encoding="utf-8"))
    published = "\n".join(f"- {post['title']}" for post in posts)
    faq_questions = "\n".join(
        f"- {faq['q']}" for post in posts[:30] for faq in post.get("faq", [])
    )
    prompt = f"""위드리빙 생활용품 고객이 검색창에 입력할 질문형 블로그 글감 10개를 새로 만드세요.

브랜드 기준:
{brand}

기존 ideas.md(중복 금지):
{ideas_text}

이미 발행한 제목(중복 금지):
{published}

기존 FAQ에서 이어질 수 있는 질문:
{faq_questions}

제품의 성분·사용법·보관법, 현재 계절, 기존 FAQ의 후속 질문을 고르게 활용하세요.
의학적 진단·치료를 전제로 하거나 효능을 단정하는 질문은 제외하고, 각 항목은 자연스러운 한국어 질문 한 문장으로 작성하세요.
"""
    payload = {
        "model": MODEL,
        "input": prompt,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "withliving_blog_ideas",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ideas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 10,
                            "maxItems": 10,
                        }
                    },
                    "required": ["ideas"],
                    "additionalProperties": False,
                },
            }
        },
    }
    result = call_openai(payload)
    existing_normalized = {
        re.sub(r"\s+", "", line).lower()
        for line in re.findall(r"^- \[[ xX]\] (.+)$", ideas_text, re.MULTILINE)
    }
    new_ideas: list[str] = []
    for idea in result["ideas"]:
        cleaned = re.sub(r"\s+", " ", idea).strip()
        normalized = re.sub(r"\s+", "", cleaned).lower()
        if cleaned and normalized not in existing_normalized and normalized not in {
            re.sub(r"\s+", "", item).lower() for item in new_ideas
        }:
            new_ideas.append(cleaned)
    if len(new_ideas) != 10:
        fail("중복되지 않는 새 글감 10개를 만들지 못했습니다.")
    path = STORY / "ideas.md"
    current = path.read_text(encoding="utf-8").rstrip()
    path.write_text(current + "\n" + "\n".join(f"- [ ] {idea}" for idea in new_ideas) + "\n", encoding="utf-8")
    return len(new_ideas)


def response_schema() -> dict:
    source = {
        "type": "object",
        "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
        "required": ["title", "url"],
        "additionalProperties": False,
    }
    faq = {
        "type": "object",
        "properties": {"q": {"type": "string"}, "a": {"type": "string"}},
        "required": ["q", "a"],
        "additionalProperties": False,
    }
    section = {
        "type": "object",
        "properties": {
            "heading": {"type": "string"},
            "paragraphs": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3},
            "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
        "required": ["heading", "paragraphs", "bullets"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "summary": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
            "intro": {"type": "string"},
            "sections": {"type": "array", "items": section, "minItems": 3, "maxItems": 5},
            "faq": {"type": "array", "items": faq, "minItems": 3, "maxItems": 3},
            "sources": {"type": "array", "items": source, "minItems": 2, "maxItems": 5},
            "cta_text": {"type": "string"},
            "cta_url": {"type": "string"},
        },
        "required": ["slug", "title", "description", "summary", "tags", "intro", "sections", "faq", "sources", "cta_text", "cta_url"],
        "additionalProperties": False,
    }


def generate(topic: str) -> dict:
    brand = (STORY / "brand.md").read_text(encoding="utf-8")
    existing = json.loads((STORY / "posts.json").read_text(encoding="utf-8"))
    existing_titles = "\n".join(f"- {p['title']}" for p in existing[:30])
    products = (ROOT / "products.json").read_text(encoding="utf-8")
    prompt = f"""아래 주제로 위드리빙 공식 블로그 글 한 편을 한국어로 작성하세요.

주제: {topic}

브랜드가 제공한 사실:
{brand}

기존 글 제목(중복 금지):
{existing_titles}

실제 제품 정보와 구매 URL(이 파일에 있는 정보만 사용):
{products}

필수 기준:
- 제목은 고객이 검색하는 질문형이며 48자 이내입니다(사이트명 포함 title 60자 이내).
- description은 80~150자, 첫 문단은 질문에 2~3문장으로 직접 답합니다.
- H2 3~5개, 각 절에는 독립적으로 인용 가능한 핵심 문장을 포함합니다.
- 생활용품을 의료기기처럼 설명하거나 통증 완화·치료·안전 효과를 약속하지 않습니다.
- 웹 검색으로 확인한 공공기관, 학회, 논문, 제조사 공식 페이지 등 신뢰할 만한 1차 출처만 사용합니다.
- 출처는 sources 배열에만 넣고, intro·sections·FAQ 안에는 URL, 마크다운 링크, 괄호형 인라인 출처를 넣지 않습니다.
- 가격·효능·수치·인증·후기·경험을 만들지 않습니다. 브랜드가 제공한 사실 외의 브랜드 경험도 만들지 않습니다.
- FAQ는 본문과 다른 실용 질문 3개입니다.
- CTA는 products.json의 실제 쿠팡 제품 URL 중 자연스럽게 맞는 것을 사용하고, 맞는 제품이 없으면 products.json의 storeUrl을 사용합니다.
- slug는 날짜 없는 영문 소문자 하이픈 형식입니다.
"""
    payload = {
        "model": MODEL,
        "tools": [{"type": "web_search"}],
        "tool_choice": "required",
        "input": prompt,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "withliving_blog_post",
                "strict": True,
                "schema": response_schema(),
            },
            "verbosity": "medium",
        },
    }
    return call_openai(payload)


def validate(post: dict) -> None:
    if len(post["title"]) > 48:
        fail("생성된 제목이 48자를 초과했습니다. 사이트명까지 포함한 title을 60자 안에 맞춰야 합니다.")
    if not 80 <= len(post["description"]) <= 150:
        fail("description은 80~150자여야 합니다.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", post["slug"]):
        fail("slug 형식이 올바르지 않습니다.")
    if (STORY / f"{post['slug']}.html").exists():
        fail(f"이미 존재하는 slug입니다: {post['slug']}")
    if len(post["faq"]) != 3 or not 3 <= len(post["sections"]) <= 5:
        fail("FAQ 또는 본문 절 개수가 규격과 다릅니다.")
    generated_text = json.dumps({k: v for k, v in post.items() if k not in ("sources", "cta_url")}, ensure_ascii=False)
    forbidden = ("placeholder", "_placeholder", "utm_source=openai", "](", "http://", "https://")
    if any(token.lower() in generated_text.lower() for token in forbidden):
        fail("본문에 임시 문구, URL 또는 인라인 마크다운 출처가 포함되어 있습니다.")
    for section in post["sections"]:
        if any(len(paragraph.strip()) < 30 for paragraph in section["paragraphs"]):
            fail("본문 문단이 지나치게 짧거나 미완성입니다.")
    for source in post["sources"]:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            fail(f"출처 URL은 유효한 HTTPS 주소여야 합니다: {source['url']}")
    parsed_cta = urlparse(post["cta_url"])
    allowed_hosts = {"www.coupang.com", "link.coupang.com", "shop.coupang.com"}
    if parsed_cta.scheme != "https" or parsed_cta.netloc not in allowed_hosts:
        fail("CTA는 products.json에 있는 쿠팡 HTTPS 주소여야 합니다.")
    products = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    allowed_urls = {products["storeUrl"], *(item["url"] for item in products["products"])}
    if post["cta_url"] not in allowed_urls:
        fail("CTA URL이 products.json의 실제 구매 주소와 일치하지 않습니다.")


def body_text(post: dict) -> str:
    parts = [post["intro"]]
    for section in post["sections"]:
        parts.append(f"## {section['heading']}")
        parts.extend(section["paragraphs"])
        parts.extend(f"- {item}" for item in section["bullets"])
    return "\n\n".join(parts)


def body_html(post: dict) -> str:
    chunks = [f"<p>{html.escape(post['intro'])}</p>"]
    for section in post["sections"]:
        chunks.append(f"<h2>{html.escape(section['heading'])}</h2>")
        chunks.extend(f"<p>{html.escape(p)}</p>" for p in section["paragraphs"])
        if section["bullets"]:
            chunks.append("<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in section["bullets"]) + "</ul>")
    return "\n".join(chunks)


def jsonld(post: dict, published: str) -> tuple[str, str, str]:
    url = f"{DOMAIN}/story/{post['slug']}.html"
    blog = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": post["title"], "description": post["description"], "datePublished": published, "dateModified": published, "author": {"@type": "Person", "name": AUTHOR}, "publisher": {"@type": "Organization", "name": BRAND}, "mainEntityOfPage": url, "keywords": ", ".join(post["tags"])}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}} for item in post["faq"]]}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": f"{DOMAIN}/"}, {"@type": "ListItem", "position": 2, "name": "이야기", "item": f"{DOMAIN}/story/"}, {"@type": "ListItem", "position": 3, "name": post["title"], "item": url}]}
    compact = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return compact(blog), compact(faq), compact(breadcrumb)


def render_page(post: dict, published: str, previous: dict | None) -> str:
    title, description, summary = (html.escape(post[k], quote=True) for k in ("title", "description", "summary"))
    url = f"{DOMAIN}/story/{post['slug']}.html"
    blog, faq_ld, breadcrumb = jsonld(post, published)
    faqs = "".join(f"<details><summary>{html.escape(x['q'])}</summary><p>{html.escape(x['a'])}</p></details>" for x in post["faq"])
    sources = "".join(f'<li><a href="{html.escape(x["url"], quote=True)}" target="_blank" rel="noopener">{html.escape(x["title"])}</a></li>' for x in post["sources"])
    related = ""
    if previous:
        prev_url = html.escape(previous["url"], quote=True)
        prev_title = html.escape(previous["title"])
        related = f'<p><a href="{prev_url}">{prev_title}</a>과 <a href="../products.html">위드리빙 제품 페이지</a>도 함께 확인해 보세요.</p>'
    else:
        related = '<p><a href="../products.html">위드리빙 제품 페이지</a>도 함께 확인해 보세요.</p>'
    display_date = published.replace("-", ".")
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{description}"><meta name="author" content="{html.escape(AUTHOR, quote=True)}"><meta name="theme-color" content="#1C1A17">
  <link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{summary}"><meta property="og:url" content="{url}"><meta property="og:image" content="{DOMAIN}/og.png">
  <title>{title}</title><link rel="icon" href="../favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../styles.css">
  <script type="application/ld+json">{blog}</script><script type="application/ld+json">{faq_ld}</script><script type="application/ld+json">{breadcrumb}</script>
</head><body><a class="skip-link" href="#main">본문으로 바로가기</a>
<header class="site-header inner" data-header><a class="wordmark" href="../index.html#home" aria-label="위드리빙 홈">위드리빙<small>WITH LIVING</small></a><button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav"><span></span><span></span><span></span><span class="sr-only">메뉴 열기</span></button><nav id="site-nav" class="site-nav" aria-label="주요 메뉴"><a href="../index.html#home">홈</a><a href="../index.html#about">내 소개</a><a href="../index.html#products">제품</a><a class="active" aria-current="page" href="./">이야기</a><a href="../contact.html">연락하기</a></nav></header>
<main id="main" class="article"><a class="back-link" href="./">← 이야기 목록</a><article>
<header><p>{html.escape(post['tags'][0])} · <time datetime="{published}">{display_date}</time></p><h1>{title}</h1><span>{html.escape(AUTHOR)}</span></header>
<div class="blog-body">{body_html(post)}</div>{related}
<section class="faq"><h2>자주 묻는 질문</h2>{faqs}</section>
<section class="sources"><h2>참고·출처</h2><ol>{sources}</ol></section>
<p>{html.escape(post['cta_text'])}</p><a class="button" href="{html.escape(post['cta_url'], quote=True)}" target="_blank" rel="noopener">쿠팡에서 제품 보기 ↗</a>
</article></main><footer class="site-footer"><div class="footer-brand"><strong>위드리빙</strong><span>WITH LIVING</span></div><div><p>일상에 따뜻함을 더하는 생활용품</p><p>© <span data-year></span> WITH LIVING. ALL RIGHTS RESERVED.</p></div><div class="footer-links"><a href="../index.html#products">제품</a><a aria-current="page" href="./">이야기</a><a href="mailto:withnexgen@gmail.com" target="_blank" rel="noopener noreferrer">이메일</a><a href="https://www.instagram.com/shop0_w2h/" target="_blank" rel="noopener noreferrer">Instagram</a><a href="../contact.html">연락하기</a></div></footer><script src="../script.js" defer></script></body></html>
'''


def update_posts(post: dict, published: str) -> list[dict]:
    path = STORY / "posts.json"
    posts = json.loads(path.read_text(encoding="utf-8"))
    item = {"id": post["slug"], "url": f"{post['slug']}.html", "title": post["title"], "date": published, "description": post["description"], "summary": post["summary"], "tags": post["tags"], "body": body_text(post), "author": AUTHOR, "faq": post["faq"], "sources": post["sources"], "cta": {"label": "쿠팡에서 제품 보기", "url": post["cta_url"]}}
    posts.insert(0, item)
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return posts


def update_ideas(topic: str) -> None:
    path = STORY / "ideas.md"
    text = path.read_text(encoding="utf-8")
    old = f"- [ ] {topic}"
    if text.count(old) != 1:
        fail("선택한 주제를 ideas.md에서 하나로 식별할 수 없습니다.")
    path.write_text(text.replace(old, f"- [x] {topic}", 1), encoding="utf-8")


def update_sitemap(posts: list[dict], published: str) -> None:
    path = ROOT / "sitemap.xml"
    root = ET.parse(path).getroot()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    existing = []
    for node in root.findall(f"{ns}url"):
        loc = node.findtext(f"{ns}loc", "")
        if "/story/" not in loc or loc.rstrip("/") == f"{DOMAIN}/story":
            existing.append((loc, node.findtext(f"{ns}lastmod", published)))
    story_index = f"{DOMAIN}/story/"
    existing = [(loc, published if loc in (f"{DOMAIN}/", story_index) else modified) for loc, modified in existing]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines.extend(f"  <url><loc>{html.escape(loc)}</loc><lastmod>{modified}</lastmod></url>" for loc, modified in existing)
    public_posts = [p for p in posts if p.get("url")]
    lines.extend(f"  <url><loc>{DOMAIN}/story/{html.escape(p['url'])}</loc><lastmod>{p.get('updated', p['date'])}</lastmod></url>" for p in public_posts)
    lines.append("</urlset>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_feed(posts: list[dict]) -> None:
    latest = [p for p in posts if p.get("url")][:20]
    newest = datetime.combine(date.fromisoformat(latest[0]["date"]), time.min, tzinfo=KST)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0">', '  <channel>', '    <title>위드리빙 이야기</title>', f'    <link>{DOMAIN}/story/</link>', '    <description>생활용품을 고르고 관리하는 방법과 위드리빙의 선택 기준</description>', '    <language>ko-KR</language>', f'    <lastBuildDate>{format_datetime(newest)}</lastBuildDate>']
    for post in latest:
        pub = datetime.combine(date.fromisoformat(post["date"]), time.min, tzinfo=KST)
        link = f"{DOMAIN}/story/{post['url']}"
        lines.extend(['    <item>', f"      <title>{html.escape(post['title'])}</title>", f"      <link>{link}</link>", f"      <guid>{link}</guid>", f"      <pubDate>{format_datetime(pub)}</pubDate>", f"      <description>{html.escape(post['summary'])}</description>", '    </item>'])
    lines.extend(['  </channel>', '</rss>'])
    (ROOT / "feed.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_llms(posts: list[dict]) -> None:
    path = ROOT / "llms.txt"
    text = path.read_text(encoding="utf-8")
    start = text.index("## 이야기(블로그)")
    end = text.find("\n## ", start + 3)
    suffix = text[end:] if end != -1 else ""
    public_posts = [p for p in posts if p.get("url")][:30]
    listing = "\n".join(f"- [{p['title']}]({DOMAIN}/story/{p['url']}): {p['summary']}" for p in public_posts)
    path.write_text(text[:start].rstrip() + "\n\n## 이야기(블로그)\n\n" + listing + "\n\n" + suffix.lstrip("\n"), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="발행일 YYYY-MM-DD (기본: 한국 날짜)")
    parser.add_argument("--check", action="store_true", help="API 호출 없이 저장소 기본 조건만 확인")
    args = parser.parse_args()
    if args.check:
        json.loads((STORY / "posts.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "sitemap.xml")
        ET.parse(ROOT / "feed.xml")
        print(f"자동 발행 준비 완료. 다음 주제: {next_topic()}")
        return
    added = replenish_topics()
    topic = next_topic()
    published = args.date or datetime.now(KST).date().isoformat()
    date.fromisoformat(published)
    post = generate(topic)
    validate(post)
    current_posts = json.loads((STORY / "posts.json").read_text(encoding="utf-8"))
    (STORY / f"{post['slug']}.html").write_text(render_page(post, published, current_posts[0] if current_posts else None), encoding="utf-8")
    posts = update_posts(post, published)
    update_ideas(topic)
    update_sitemap(posts, published)
    update_feed(posts)
    update_llms(posts)
    review = {
        "title": post["title"],
        "slug": post["slug"],
        "url": f"{DOMAIN}/story/{post['slug']}.html",
        "fact_check": [
            "본문의 생활용품 사용·관리 설명이 연결된 출처와 일치하는지 확인",
            "브랜드 고유 사실과 제품 연결이 story/brand.md 및 products.json과 일치하는지 확인",
            "제품명·가격·크기·구매 URL이 products.json의 실제 정보와 일치하는지 확인",
        ],
        "remaining_ideas": len(unchecked_topics()),
        "added_ideas": added,
    }
    (ROOT / "daily-review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"발행 준비 완료: {post['title']} ({post['slug']}.html)")


if __name__ == "__main__":
    main()
