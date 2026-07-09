from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlparse

from radar.models import Company, Posting
from radar.scrapers.http import fetch_text


DEFAULT_KEYWORDS = [
    "intern",
    "internship",
    "trainee",
    "graduate",
    "management trainee",
    "analyst",
    "associate",
    "entry level",
    "entry-level",
]


@dataclass(frozen=True)
class Link:
    text: str
    href: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[Link] = []
        self._href_stack: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href") or ""
        self._href_stack.append(href)
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href_stack:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href_stack:
            return
        href = self._href_stack.pop()
        text = normalize_text(" ".join(self._text_parts))
        if href and text:
            self.links.append(Link(text=text, href=href))
        self._text_parts = []


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def is_supported_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https", "mailto"}


def keyword_match(value: str, keywords: list[str]) -> bool:
    haystack = value.lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def find_mailto(text: str, subject: str = "") -> str | None:
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    if not match:
        return None
    if not subject:
        return f"mailto:{match.group(0)}"
    return f"mailto:{match.group(0)}?subject={quote(subject)}"


def resolve_apply_action(link: Link, role: str) -> str:
    if link.href.lower().startswith("mailto:"):
        return link.href
    if email_action := find_mailto(link.text, subject=f"Application - {role}"):
        return email_action
    return link.href


def scrape_generic(company: Company, keywords: list[str] | None = None, timeout: int = 20) -> list[Posting]:
    keywords = keywords or DEFAULT_KEYWORDS
    page = fetch_text(company.career_url, timeout=timeout)
    parser = LinkParser()
    parser.feed(page)

    postings: list[Posting] = []
    seen_urls: set[str] = set()
    for link in parser.links:
        absolute_url = urljoin(company.career_url, link.href)
        if not is_supported_url(absolute_url):
            continue

        combined = f"{link.text} {absolute_url}"
        if not keyword_match(combined, keywords):
            continue

        role = link.text
        if role.lower() in {"apply", "apply now", "view", "view details", "learn more"}:
            role = f"{company.name} opportunity"

        apply_action = resolve_apply_action(link, role)
        if not apply_action.lower().startswith("mailto:"):
            apply_action = urljoin(company.career_url, apply_action)

        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)

        postings.append(
            Posting(
                company=company.name,
                role=role,
                url=absolute_url,
                apply_action=apply_action,
                source="career_page",
                source_url=company.career_url,
            )
        )

    return postings
