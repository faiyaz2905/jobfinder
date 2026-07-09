from __future__ import annotations

import json
import os
from urllib.parse import urlencode

from radar.models import Company, Posting
from radar.scrapers.http import fetch_text


SERPAPI_URL = "https://serpapi.com/search.json"


def discover_linkedin_jobs(company: Company, timeout: int = 20) -> list[Posting]:
    api_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set SERPAPI_API_KEY to enable LinkedIn discovery")

    query = linkedin_query(company)
    url = f"{SERPAPI_URL}?{urlencode({'engine': 'google', 'q': query, 'api_key': api_key})}"
    data = json.loads(fetch_text(url, timeout=timeout))

    postings: list[Posting] = []
    seen_links: set[str] = set()
    for result in data.get("organic_results", []):
        link = result.get("link", "")
        title = result.get("title", "")
        if "linkedin.com/jobs" not in link or link in seen_links:
            continue
        seen_links.add(link)
        postings.append(
            Posting(
                company=company.name,
                role=clean_title(title) or f"{company.name} LinkedIn opportunity",
                url=link,
                apply_action=link,
                source="linkedin",
                source_url=link,
            )
        )

    return postings


def linkedin_query(company: Company) -> str:
    company_term = company.linkedin_slug or company.name
    suffix = os.environ.get("RADAR_LINKEDIN_QUERY_SUFFIX", "intern OR internship Bangladesh")
    return f'site:linkedin.com/jobs "{company_term}" {suffix}'


def clean_title(title: str) -> str:
    for marker in (" | LinkedIn", " - LinkedIn"):
        if marker in title:
            title = title.split(marker, 1)[0]
    return " ".join(title.split())

