from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    name: str
    career_url: str
    category: str = ""
    ats_type: str = "generic"
    notes: str = ""
    linkedin_slug: str = ""
    facebook_page_url: str = ""


@dataclass(frozen=True)
class Posting:
    company: str
    role: str
    url: str
    apply_action: str
    source: str
    source_url: str


@dataclass(frozen=True)
class Contact:
    company: str
    email: str
    source_page: str
    contact_type: str = "generic"
