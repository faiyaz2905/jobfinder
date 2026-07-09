from __future__ import annotations

import json
from pathlib import Path

from .models import Company


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "companies.json"


def load_companies(config_path: Path = DEFAULT_CONFIG_PATH) -> list[Company]:
    if not config_path.exists():
        return []

    data = json.loads(config_path.read_text(encoding="utf-8"))
    companies = data.get("companies", [])
    return [
        Company(
            name=item["name"],
            career_url=item.get("career_url", ""),
            category=item.get("category", ""),
            ats_type=item.get("ats_type", "generic"),
            notes=item.get("notes", ""),
            linkedin_slug=item.get("linkedin_slug", ""),
            facebook_page_url=item.get("facebook_page_url", ""),
        )
        for item in companies
        if item.get("name")
    ]


def save_companies(companies: list[Company], config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "companies": [
            {
                "name": company.name,
                "career_url": company.career_url,
                "category": company.category,
                "ats_type": company.ats_type,
                "notes": company.notes,
                "linkedin_slug": company.linkedin_slug,
                "facebook_page_url": company.facebook_page_url,
            }
            for company in sorted(companies, key=lambda item: item.name.lower())
        ]
    }
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def add_company(company: Company, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    companies = load_companies(config_path)
    kept = [existing for existing in companies if existing.name.lower() != company.name.lower()]
    kept.append(company)
    save_companies(kept, config_path)


def remove_company(name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> bool:
    companies = load_companies(config_path)
    kept = [company for company in companies if company.name.lower() != name.lower()]
    if len(kept) == len(companies):
        return False
    save_companies(kept, config_path)
    return True
