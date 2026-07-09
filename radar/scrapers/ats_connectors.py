from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from radar.models import Company, Posting
from radar.scrapers.http import fetch_text


def scrape_ats(company: Company, timeout: int = 20) -> list[Posting]:
    ats_type = company.ats_type.lower().strip()
    if ats_type == "greenhouse":
        return scrape_greenhouse(company, timeout)
    if ats_type == "lever":
        return scrape_lever(company, timeout)
    return []


def scrape_greenhouse(company: Company, timeout: int = 20) -> list[Posting]:
    token = board_token(company.career_url)
    if not token:
        return []

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    data = json.loads(fetch_text(api_url, timeout=timeout))
    postings = []
    for job in data.get("jobs", []):
        title = job.get("title")
        absolute_url = job.get("absolute_url")
        if not title or not absolute_url:
            continue
        postings.append(
            Posting(
                company=company.name,
                role=title,
                url=absolute_url,
                apply_action=absolute_url,
                source="greenhouse",
                source_url=company.career_url,
            )
        )
    return postings


def scrape_lever(company: Company, timeout: int = 20) -> list[Posting]:
    token = lever_token(company.career_url)
    if not token:
        return []

    api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    data = json.loads(fetch_text(api_url, timeout=timeout))
    postings = []
    for job in data:
        title = job.get("text")
        hosted_url = job.get("hostedUrl")
        if not title or not hosted_url:
            continue
        postings.append(
            Posting(
                company=company.name,
                role=title,
                url=hosted_url,
                apply_action=hosted_url,
                source="lever",
                source_url=company.career_url,
            )
        )
    return postings


def board_token(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if "greenhouse.io" not in parsed.netloc and "greenhouse" not in path:
        return ""
    match = re.search(r"(?:boards|embed)/(?:[^/]+/)?([^/?#]+)", path)
    if match:
        return match.group(1)
    return path.split("/")[-1] if path else ""


def lever_token(url: str) -> str:
    parsed = urlparse(url)
    if "lever.co" not in parsed.netloc:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    return parts[0] if parts else ""

