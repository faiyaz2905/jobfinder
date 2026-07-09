from __future__ import annotations

import json
import os
from urllib.parse import quote, urlparse

from radar.models import Company, Posting
from radar.scrapers.career_pages import DEFAULT_KEYWORDS, keyword_match
from radar.scrapers.http import fetch_text


GRAPH_VERSION = os.environ.get("RADAR_FACEBOOK_GRAPH_VERSION", "v20.0")


def discover_facebook_posts(
    company: Company,
    keywords: list[str] | None = None,
    timeout: int = 20,
) -> list[Posting]:
    if not company.facebook_page_url:
        return []

    token = os.environ.get("META_GRAPH_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set META_GRAPH_ACCESS_TOKEN to enable Facebook discovery")

    page_id = facebook_page_id(company.facebook_page_url)
    if not page_id:
        return []

    keywords = keywords or DEFAULT_KEYWORDS
    fields = "message,permalink_url,created_time"
    url = (
        f"https://graph.facebook.com/{GRAPH_VERSION}/{quote(page_id)}/posts"
        f"?fields={quote(fields)}&access_token={quote(token)}"
    )
    data = json.loads(fetch_text(url, timeout=timeout))

    postings: list[Posting] = []
    for item in data.get("data", []):
        message = item.get("message", "")
        permalink = item.get("permalink_url", "")
        if not message or not permalink or not keyword_match(message, keywords):
            continue

        postings.append(
            Posting(
                company=company.name,
                role=facebook_role(message, company.name),
                url=permalink,
                apply_action=permalink,
                source="facebook",
                source_url=company.facebook_page_url,
            )
        )

    return postings


def facebook_page_id(page_url: str) -> str:
    parsed = urlparse(page_url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else ""


def facebook_role(message: str, company_name: str) -> str:
    first_line = next((line.strip() for line in message.splitlines() if line.strip()), "")
    if not first_line:
        return f"{company_name} Facebook circular"
    return first_line[:120]

