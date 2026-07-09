from __future__ import annotations

import argparse
from pathlib import Path

from radar.company_config import DEFAULT_CONFIG_PATH, add_company, load_companies, remove_company
from radar.models import Company, Posting
from radar.notify.emailer import build_html_body, load_email_settings, missing_settings, send_new_postings
from radar.scan import scan_company
from radar.scheduler_hooks import local_schedule_hint
from radar.scrapers.career_pages import DEFAULT_KEYWORDS
from radar.scrapers.contacts import scrape_contacts
from radar.scrapers.facebook import discover_facebook_posts
from radar.scrapers.linkedin_search import discover_linkedin_jobs
from radar.storage.db import (
    DEFAULT_DB_PATH,
    VALID_STATUSES,
    connect,
    export_contacts_csv,
    list_contacts,
    list_postings,
    mark_applied,
    set_posting_status,
    upsert_contacts,
    upsert_postings,
)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="radar", description="Internship Radar CLI")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(required=True)

    list_parser = subparsers.add_parser("list-companies", help="Show tracked companies")
    list_parser.set_defaults(func=cmd_list_companies)

    add_parser = subparsers.add_parser("add-company", help="Add or update a tracked company")
    add_parser.add_argument("name")
    add_parser.add_argument("--career-url", required=True)
    add_parser.add_argument("--category", default="")
    add_parser.add_argument("--ats-type", default="generic", choices=["generic", "greenhouse", "lever", "workday"])
    add_parser.add_argument("--notes", default="")
    add_parser.add_argument("--linkedin-slug", default="")
    add_parser.add_argument("--facebook-page-url", default="")
    add_parser.set_defaults(func=cmd_add_company)

    remove_parser = subparsers.add_parser("remove-company", help="Remove a tracked company")
    remove_parser.add_argument("name")
    remove_parser.set_defaults(func=cmd_remove_company)

    scan_parser = subparsers.add_parser("scan", help="Scan career pages and store newly found postings")
    scan_parser.add_argument("--company", help="Scan only companies whose name contains this text")
    scan_parser.add_argument("--keyword", action="append", dest="keywords", help="Extra keyword to match")
    scan_parser.add_argument("--include-linkedin", action="store_true", help="Include SerpAPI-backed LinkedIn discovery")
    scan_parser.add_argument("--include-facebook", action="store_true", help="Include Meta Graph API Facebook discovery")
    scan_parser.add_argument("--notify", action="store_true", help="Email newly found postings")
    scan_parser.add_argument("--timeout", type=int, default=20)
    scan_parser.set_defaults(func=cmd_scan)

    discover_parser = subparsers.add_parser("discover", help="Run lower-confidence LinkedIn/Facebook discovery")
    discover_parser.add_argument("source", choices=["linkedin", "facebook", "all"])
    discover_parser.add_argument("--company", help="Discover only companies whose name contains this text")
    discover_parser.add_argument("--keyword", action="append", dest="keywords", help="Extra keyword to match")
    discover_parser.add_argument("--notify", action="store_true", help="Email newly found discovery results")
    discover_parser.add_argument("--timeout", type=int, default=20)
    discover_parser.set_defaults(func=cmd_discover)

    notify_parser = subparsers.add_parser("notify-test", help="Validate email settings and render a sample alert")
    notify_parser.add_argument("--send", action="store_true", help="Send the sample alert email")
    notify_parser.set_defaults(func=cmd_notify_test)

    history_parser = subparsers.add_parser("history", help="Show stored postings")
    history_parser.add_argument("--limit", type=int, default=50)
    history_parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="Filter by posting status")
    history_parser.add_argument("--company", help="Filter by company name")
    history_parser.set_defaults(func=cmd_history)

    applied_parser = subparsers.add_parser("log-applied", help="Mark a posting as applied")
    applied_parser.add_argument("posting_id")
    applied_parser.add_argument("--note", default="", help="Optional note about the application")
    applied_parser.set_defaults(func=cmd_log_applied)

    status_parser = subparsers.add_parser("set-status", help="Set a posting status")
    status_parser.add_argument("posting_id")
    status_parser.add_argument("status", choices=sorted(VALID_STATUSES))
    status_parser.add_argument("--note", default="", help="Optional note to store with the posting")
    status_parser.set_defaults(func=cmd_set_status)

    contacts_parser = subparsers.add_parser("contacts", help="Manage scraped contact emails")
    contacts_subparsers = contacts_parser.add_subparsers(required=True)

    contacts_update = contacts_subparsers.add_parser("update", help="Refresh contact repository")
    contacts_update.add_argument("--company", help="Update only companies whose name contains this text")
    contacts_update.add_argument("--timeout", type=int, default=20)
    contacts_update.add_argument("--max-pages", type=int, default=8)
    contacts_update.set_defaults(func=cmd_contacts_update)

    contacts_list = contacts_subparsers.add_parser("list", help="Show stored contact emails")
    contacts_list.add_argument("--company", help="Filter by company name")
    contacts_list.add_argument("--type", dest="contact_type", choices=["generic", "hr", "named"], help="Filter by contact type")
    contacts_list.set_defaults(func=cmd_contacts_list)

    contacts_export = contacts_subparsers.add_parser("export", help="Export contact repository to CSV")
    contacts_export.add_argument("--output", type=Path, default=Path("contacts.csv"))
    contacts_export.add_argument("--company", help="Filter by company name")
    contacts_export.add_argument("--type", dest="contact_type", choices=["generic", "hr", "named"], help="Filter by contact type")
    contacts_export.set_defaults(func=cmd_contacts_export)

    schedule_parser = subparsers.add_parser("schedule", help="Create or print scheduling helpers")
    schedule_subparsers = schedule_parser.add_subparsers(required=True)

    local_parser = schedule_subparsers.add_parser("local", help="Print local scheduler commands")
    local_parser.add_argument("--every-hours", type=int, default=12)
    local_parser.add_argument("--include-linkedin", action="store_true", help="Include LinkedIn discovery in scheduled scans")
    local_parser.add_argument("--include-facebook", action="store_true", help="Include Facebook discovery in scheduled scans")
    local_parser.set_defaults(func=cmd_schedule_local)

    return parser


def cmd_list_companies(args: argparse.Namespace) -> None:
    companies = load_companies(args.config)
    if not companies:
        print("No companies configured.")
        return

    for index, company in enumerate(companies, start=1):
        suffix = f" [{company.category}]" if company.category else ""
        print(f"{index:>2}. {company.name}{suffix}")
        print(f"    {company.career_url}")


def cmd_add_company(args: argparse.Namespace) -> None:
    company = Company(
        name=args.name,
        career_url=args.career_url,
        category=args.category,
        ats_type=args.ats_type,
        notes=args.notes,
        linkedin_slug=args.linkedin_slug,
        facebook_page_url=args.facebook_page_url,
    )
    add_company(company, args.config)
    print(f"Saved {company.name}.")


def cmd_remove_company(args: argparse.Namespace) -> None:
    removed = remove_company(args.name, args.config)
    if removed:
        print(f"Removed {args.name}.")
    else:
        print(f"No company named {args.name} was found.")


def cmd_scan(args: argparse.Namespace) -> None:
    companies = select_companies(args.config, args.company)
    if not companies:
        print("No companies configured.")
        return

    keywords = DEFAULT_KEYWORDS + (args.keywords or [])
    conn = connect(args.db)
    all_new = []

    print(f"Scanning {len(companies)} companies...")
    for company in companies:
        result = scan_company(company, keywords=keywords, timeout=args.timeout)
        if result.error:
            print(f"- {company.name}: error: {result.error}")
        else:
            new_postings = upsert_postings(conn, result.postings)
            all_new.extend(new_postings)
            print(f"- {company.name}: {len(result.postings)} matched, {len(new_postings)} new")

        if args.include_linkedin:
            all_new.extend(run_discovery_source(conn, company, "linkedin", keywords, args.timeout))
        if args.include_facebook:
            all_new.extend(run_discovery_source(conn, company, "facebook", keywords, args.timeout))

    if not all_new:
        print("No new postings found.")
        return

    print("")
    print("New postings:")
    for posting_id, posting in all_new:
        print(f"{posting_id} | {posting.company} | {posting.role}")
        print(f"  {posting.apply_action}")

    if args.notify:
        send_new_postings(all_new)
        print(f"Sent email notification for {len(all_new)} new posting(s).")


def cmd_discover(args: argparse.Namespace) -> None:
    companies = select_companies(args.config, args.company)
    if not companies:
        print("No companies configured.")
        return

    keywords = DEFAULT_KEYWORDS + (args.keywords or [])
    sources = ["linkedin", "facebook"] if args.source == "all" else [args.source]
    conn = connect(args.db)
    all_new = []

    print(f"Running {args.source} discovery for {len(companies)} companies...")
    for company in companies:
        for source in sources:
            all_new.extend(run_discovery_source(conn, company, source, keywords, args.timeout))

    if not all_new:
        print("No new discovery results found.")
        return

    print("")
    print("New discovery results:")
    for posting_id, posting in all_new:
        print(f"{posting_id} | {posting.source} | {posting.company} | {posting.role}")
        print(f"  {posting.apply_action}")

    if args.notify:
        send_new_postings(all_new)
        print(f"Sent email notification for {len(all_new)} new discovery result(s).")


def run_discovery_source(conn, company: Company, source: str, keywords: list[str], timeout: int) -> list[tuple[str, Posting]]:
    try:
        if source == "linkedin":
            postings = discover_linkedin_jobs(company, timeout=timeout)
        elif source == "facebook":
            postings = discover_facebook_posts(company, keywords=keywords, timeout=timeout)
        else:
            raise ValueError(f"Unknown discovery source: {source}")
    except Exception as exc:
        print(f"- {company.name} {source}: error: {exc}")
        return []

    new_postings = upsert_postings(conn, postings)
    print(f"- {company.name} {source}: {len(postings)} matched, {len(new_postings)} new")
    return new_postings


def cmd_history(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    rows = list_postings(conn, limit=args.limit, status=args.status, company=args.company)
    if not rows:
        print("No postings stored yet.")
        return

    for row in rows:
        status = row["status"] or ("applied" if row["applied"] else "new")
        print(f"{row['id']} | {status} | {row['company']} | {row['role']}")
        print(f"  {row['apply_action']}")
        if row["applied_at"]:
            print(f"  applied_at: {row['applied_at']}")
        if row["notes"]:
            print(f"  note: {row['notes']}")


def cmd_log_applied(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    if mark_applied(conn, args.posting_id, note=args.note):
        print(f"Marked {args.posting_id} as applied.")
    else:
        print(f"No posting found with id {args.posting_id}.")


def cmd_set_status(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    if set_posting_status(conn, args.posting_id, args.status, note=args.note):
        print(f"Set {args.posting_id} to {args.status}.")
    else:
        print(f"No posting found with id {args.posting_id}.")


def cmd_contacts_update(args: argparse.Namespace) -> None:
    companies = select_companies(args.config, args.company)
    if not companies:
        print("No companies configured.")
        return

    conn = connect(args.db)
    total_contacts = 0
    total_new = 0

    print(f"Updating contacts for {len(companies)} companies...")
    for company in companies:
        result = scrape_contacts(company, timeout=args.timeout, max_pages=args.max_pages)
        if result.error:
            print(f"- {company.name}: error: {result.error}")
            continue

        new_contacts = upsert_contacts(conn, result.contacts)
        total_contacts += len(result.contacts)
        total_new += len(new_contacts)
        print(f"- {company.name}: {len(result.contacts)} found, {len(new_contacts)} new")

    print(f"Contact update complete: {total_contacts} found, {total_new} new.")


def cmd_contacts_list(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    rows = list_contacts(conn, company=args.company, contact_type=args.contact_type)
    if not rows:
        print("No contacts stored yet.")
        return

    for row in rows:
        print(f"{row['id']} | {row['contact_type']} | {row['company']} | {row['email']}")
        print(f"  {row['source_page']}")


def cmd_contacts_export(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    count = export_contacts_csv(
        conn,
        args.output,
        company=args.company,
        contact_type=args.contact_type,
    )
    print(f"Exported {count} contacts to {args.output}.")


def cmd_schedule_local(args: argparse.Namespace) -> None:
    print(
        local_schedule_hint(
            every_hours=args.every_hours,
            include_linkedin=args.include_linkedin,
            include_facebook=args.include_facebook,
        )
    )


def select_companies(config_path: Path, company_filter: str | None) -> list[Company]:
    companies = load_companies(config_path)
    if company_filter:
        needle = company_filter.lower()
        companies = [company for company in companies if needle in company.name.lower()]
    return companies


def cmd_notify_test(args: argparse.Namespace) -> None:
    settings = load_email_settings()
    missing = missing_settings(settings)

    print(f"SMTP host: {settings.smtp_host}:{settings.smtp_port}")
    print(f"SMTP username: {settings.username or '(missing)'}")
    print(f"Sender: {settings.sender or '(missing)'}")
    print(f"Recipients: {', '.join(settings.recipients) or '(missing)'}")

    sample_company = Company(name="Sample Company", career_url="https://example.com/careers")
    sample_postings = [
        (
            "sample123",
            Posting(
                company=sample_company.name,
                role="Finance Intern",
                url="https://example.com/careers/finance-intern",
                apply_action="https://example.com/careers/finance-intern/apply",
                source="career_page",
                source_url=sample_company.career_url,
            ),
        )
    ]

    if missing:
        print(f"Missing settings: {', '.join(missing)}")
    else:
        print("Email settings look complete.")

    if args.send:
        send_new_postings(sample_postings, settings)
        print("Sent sample notification.")
        return

    print("")
    print("Sample HTML preview:")
    print(build_html_body(sample_postings))
