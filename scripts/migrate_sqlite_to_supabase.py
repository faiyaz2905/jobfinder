from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.cloud.scan_runner import seed_companies_if_empty
from radar.cloud.supabase import SupabaseClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local Internship Radar data to Supabase")
    parser.add_argument("--db", type=Path, default=Path(".radar/radar.sqlite3"))
    parser.add_argument("--apply", action="store_true", help="Write data; without this flag, only print counts")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"SQLite database not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    postings = conn.execute("select * from postings").fetchall()
    contacts = conn.execute("select * from contacts").fetchall()
    print(f"Found {len(postings)} postings and {len(contacts)} contacts.")
    if not args.apply:
        print("Dry run only. Add --apply after configuring Supabase environment variables.")
        return

    cloud = SupabaseClient()
    companies = seed_companies_if_empty(cloud)
    company_ids = {row["name"].lower(): row["id"] for row in companies}

    posting_rows = [
        {
            "id": row["id"],
            "company_id": company_ids.get(row["company"].lower()),
            "company": row["company"],
            "role": row["role"],
            "apply_action": row["apply_action"],
            "source": row["source"],
            "source_url": row["source_url"],
            "first_seen_at": row["date_found"],
            "last_seen_at": row["last_seen"],
            "status": row["status"],
            "applied_at": row["applied_at"] or None,
            "notified_at": row["date_found"],
            "notes": row["notes"],
        }
        for row in postings
    ]
    contact_rows = [
        {
            "id": row["id"],
            "company_id": company_ids.get(row["company"].lower()),
            "company": row["company"],
            "email": row["email"].lower(),
            "source_page": row["source_page"],
            "contact_type": row["contact_type"],
            "first_seen_at": row["first_seen"],
            "last_seen_at": row["last_seen"],
        }
        for row in contacts
    ]

    for start in range(0, len(posting_rows), 100):
        cloud.insert("postings", posting_rows[start : start + 100], upsert=True, on_conflict="id")
    for start in range(0, len(contact_rows), 100):
        cloud.insert("contacts", contact_rows[start : start + 100], upsert=True, on_conflict="id")
    print("Migration complete.")


if __name__ == "__main__":
    main()
