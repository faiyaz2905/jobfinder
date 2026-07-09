from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from radar.company_config import load_companies
from radar.models import Company, Posting
from radar.notify.emailer import send_new_postings
from radar.scan import scan_company
from radar.storage.db import posting_id

from .supabase import SupabaseClient


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_companies_if_empty(db: SupabaseClient) -> list[dict[str, Any]]:
    rows = db.select("companies", filters={"enabled": "eq.true"}, order="name.asc")
    if rows:
        return rows

    seed_rows = [
        {
            "name": company.name,
            "career_url": company.career_url,
            "category": company.category,
            "ats_type": company.ats_type,
            "notes": company.notes,
            "linkedin_slug": company.linkedin_slug,
            "facebook_url": company.facebook_page_url,
            "enabled": True,
        }
        for company in load_companies()
    ]
    if seed_rows:
        db.insert("companies", seed_rows, upsert=True, on_conflict="name")
    return db.select("companies", filters={"enabled": "eq.true"}, order="name.asc")


def company_from_row(row: dict[str, Any]) -> Company:
    return Company(
        name=row["name"],
        career_url=row.get("career_url", ""),
        category=row.get("category", ""),
        ats_type=row.get("ats_type", "generic"),
        notes=row.get("notes", ""),
        linkedin_slug=row.get("linkedin_slug", ""),
        facebook_page_url=row.get("facebook_url", ""),
    )


def insert_posting(db: SupabaseClient, company_id: str, posting: Posting) -> tuple[str, bool]:
    fingerprint = posting_id(posting)
    now = utc_now()
    inserted = db.insert(
        "postings",
        {
            "id": fingerprint,
            "company_id": company_id,
            "company": posting.company,
            "role": posting.role,
            "apply_action": posting.apply_action,
            "source": posting.source,
            "source_url": posting.source_url,
            "first_seen_at": now,
            "last_seen_at": now,
        },
        upsert=True,
        ignore_duplicates=True,
        on_conflict="id",
    )
    if inserted:
        return fingerprint, True

    db.update(
        "postings",
        {
            "last_seen_at": now,
            "apply_action": posting.apply_action,
            "source_url": posting.source_url,
        },
        {"id": f"eq.{fingerprint}"},
    )
    return fingerprint, False


def run_cloud_scan(trigger: str = "scheduled") -> dict[str, Any]:
    db = SupabaseClient()
    owner = str(uuid.uuid4())
    acquired = bool(
        db.rpc(
            "acquire_scan_lock",
            {"lock_name": "career-scan", "lock_owner": owner, "ttl_seconds": 290},
        )
    )
    if not acquired:
        return {"status": "skipped", "reason": "scan_already_running"}

    run_rows = db.insert("scan_runs", {"trigger": trigger, "status": "running"})
    run_id = run_rows[0]["id"]
    errors: list[dict[str, str]] = []
    postings_seen = 0
    new_postings: list[tuple[str, Posting]] = []
    companies_checked = 0
    notification_status = "not_needed"

    try:
        company_rows = seed_companies_if_empty(db)
        timeout = max(5, min(int(os.environ.get("RADAR_SCAN_TIMEOUT", "12")), 20))

        workers = max(1, min(int(os.environ.get("RADAR_SCAN_WORKERS", "6")), 10))
        futures = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for row in company_rows:
                future = executor.submit(scan_company, company_from_row(row), timeout=timeout)
                futures[future] = row

            completed = [(futures[future], future.result()) for future in as_completed(futures)]

        for row, result in completed:
            companies_checked += 1
            if result.error:
                errors.append({"company": row["name"], "error": result.error[:300]})
                continue

            postings_seen += len(result.postings)
            for posting in result.postings:
                fingerprint, is_new = insert_posting(db, row["id"], posting)
                if is_new:
                    new_postings.append((fingerprint, posting))

        pending_rows = db.select(
            "postings",
            columns="id,company,role,apply_action,source,source_url",
            filters={"notified_at": "is.null"},
            order="first_seen_at.asc",
            limit=200,
        )
        pending_notifications = [
            (
                row["id"],
                Posting(
                    company=row["company"],
                    role=row["role"],
                    url=row["apply_action"],
                    apply_action=row["apply_action"],
                    source=row["source"],
                    source_url=row["source_url"],
                ),
            )
            for row in pending_rows
        ]

        if pending_notifications:
            notification_status = "pending"
            try:
                send_new_postings(pending_notifications)
                for posting_fingerprint, _posting in pending_notifications:
                    db.update(
                        "postings",
                        {"notified_at": utc_now()},
                        {"id": f"eq.{posting_fingerprint}", "notified_at": "is.null"},
                    )
                notification_status = "sent"
            except Exception as exc:
                notification_status = "failed"
                errors.append({"company": "_notification", "error": str(exc)[:300]})

        status = "partial" if errors else "succeeded"
        db.update(
            "scan_runs",
            {
                "status": status,
                "finished_at": utc_now(),
                "companies_checked": companies_checked,
                "postings_seen": postings_seen,
                "new_postings": len(new_postings),
                "notification_status": notification_status,
                "error_summary": errors,
            },
            {"id": f"eq.{run_id}"},
        )
        return {
            "status": status,
            "scan_id": run_id,
            "companies_checked": companies_checked,
            "postings_seen": postings_seen,
            "new_postings": len(new_postings),
            "notification_status": notification_status,
            "errors": len(errors),
        }
    except Exception as exc:
        errors.append({"company": "_scan", "error": str(exc)[:300]})
        db.update(
            "scan_runs",
            {
                "status": "failed",
                "finished_at": utc_now(),
                "companies_checked": companies_checked,
                "postings_seen": postings_seen,
                "new_postings": len(new_postings),
                "notification_status": notification_status,
                "error_summary": errors,
            },
            {"id": f"eq.{run_id}"},
        )
        raise
    finally:
        try:
            db.rpc("release_scan_lock", {"lock_name": "career-scan", "lock_owner": owner})
        except Exception:
            pass
