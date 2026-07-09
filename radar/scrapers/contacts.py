from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from radar.models import Company, Contact
from radar.scrapers.career_pages import LinkParser
from radar.scrapers.http import fetch_text


EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
CONTACT_LINK_KEYWORDS = ("contact", "about", "career", "job", "join", "team", "people")
GENERIC_LOCAL_PARTS = {
    "admin",
    "career",
    "careers",
    "contact",
    "cv",
    "hello",
    "hr",
    "info",
    "jobs",
    "recruitment",
    "recruiter",
    "talent",
}


@dataclass(frozen=True)
class ContactScanResult:
    company: Company
    contacts: list[Contact]
    error: str = ""


def scrape_contacts(company: Company, timeout: int = 20, max_pages: int = 8) -> ContactScanResult:
    try:
        contacts = scrape_company_contacts(company, timeout=timeout, max_pages=max_pages)
        return ContactScanResult(company=company, contacts=contacts)
    except Exception as exc:
        return ContactScanResult(company=company, contacts=[], error=str(exc))


def scrape_company_contacts(company: Company, timeout: int = 20, max_pages: int = 8) -> list[Contact]:
    pages = candidate_pages(company.career_url)
    contacts_by_email: dict[str, Contact] = {}
    fetched_pages = 0

    while pages and fetched_pages < max_pages:
        page_url = pages.pop(0)
        fetched_pages += 1
        try:
            text = fetch_text(page_url, timeout=timeout)
        except RuntimeError:
            continue

        for email in extract_emails(text):
            key = email.lower()
            contacts_by_email.setdefault(
                key,
                Contact(
                    company=company.name,
                    email=email,
                    source_page=page_url,
                    contact_type=classify_email(email),
                ),
            )

        for discovered_url in discover_contact_links(company.career_url, page_url, text):
            if discovered_url not in pages and fetched_pages + len(pages) < max_pages:
                pages.append(discovered_url)

    return sorted(contacts_by_email.values(), key=lambda contact: contact.email.lower())


def candidate_pages(career_url: str) -> list[str]:
    parsed = urlparse(career_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        career_url,
        urljoin(base, "/contact"),
        urljoin(base, "/contact-us"),
        urljoin(base, "/about"),
        urljoin(base, "/about-us"),
        urljoin(base, "/careers"),
        urljoin(base, "/career"),
    ]
    return dedupe_urls(candidates)


def discover_contact_links(career_url: str, current_url: str, page_text: str) -> list[str]:
    parser = LinkParser()
    parser.feed(page_text)
    base_host = urlparse(career_url).netloc.lower()
    discovered = []

    for link in parser.links:
        absolute_url = urljoin(current_url, link.href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.lower() != base_host:
            continue
        if any(keyword in f"{link.text} {parsed.path}".lower() for keyword in CONTACT_LINK_KEYWORDS):
            discovered.append(absolute_url)

    return dedupe_urls(discovered)


def extract_emails(text: str) -> list[str]:
    emails = []
    for match in EMAIL_RE.finditer(text):
        email = match.group(0).strip(".,;:()[]{}<>\"'")
        if is_probable_real_email(email):
            emails.append(email)
    return sorted(set(emails), key=str.lower)


def is_probable_real_email(email: str) -> bool:
    lowered = email.lower()
    blocked_suffixes = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
    if lowered.endswith(blocked_suffixes):
        return False
    if "example.com" in lowered:
        return False
    return True


def classify_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    compact = re.sub(r"[^a-z]", "", local)
    if compact in GENERIC_LOCAL_PARTS:
        return "generic"
    if any(word in compact for word in ("hr", "career", "job", "recruit", "talent")):
        return "hr"
    if "." in local or "_" in local:
        return "named"
    return "generic"


def dedupe_urls(urls: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for url in urls:
        clean = url.split("#", 1)[0].rstrip("/")
        if clean and clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return deduped
