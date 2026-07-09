from __future__ import annotations

from dataclasses import dataclass

from radar.models import Company, Posting
from radar.scrapers.ats_connectors import scrape_ats
from radar.scrapers.career_pages import DEFAULT_KEYWORDS, scrape_generic


@dataclass(frozen=True)
class CompanyScanResult:
    company: Company
    postings: list[Posting]
    error: str = ""


def scan_company(company: Company, keywords: list[str] | None = None, timeout: int = 20) -> CompanyScanResult:
    try:
        postings = scrape_ats(company, timeout=timeout) if company.ats_type != "generic" else []
        if not postings:
            postings = scrape_generic(company, keywords=keywords or DEFAULT_KEYWORDS, timeout=timeout)
        return CompanyScanResult(company=company, postings=postings)
    except Exception as exc:
        return CompanyScanResult(company=company, postings=[], error=str(exc))

