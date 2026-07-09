from __future__ import annotations

import hashlib
import sqlite3
import csv
from datetime import datetime, timezone
from pathlib import Path

from radar.models import Contact, Posting


DEFAULT_DB_PATH = Path.cwd() / ".radar" / "radar.sqlite3"
VALID_STATUSES = {"new", "saved", "applied", "interviewing", "rejected", "offer", "archived"}


def posting_id(posting: Posting) -> str:
    raw = "|".join([posting.company.strip().lower(), posting.role.strip().lower(), posting.url.strip()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def contact_id(contact: Contact) -> str:
    raw = "|".join([contact.company.strip().lower(), contact.email.strip().lower()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS postings (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            apply_action TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            date_found TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            applied INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'new',
            applied_at TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            email TEXT NOT NULL,
            source_page TEXT NOT NULL,
            contact_type TEXT NOT NULL DEFAULT 'generic',
            date_scraped TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
    )
    ensure_column(conn, "postings", "status", "TEXT NOT NULL DEFAULT 'new'")
    ensure_column(conn, "postings", "applied_at", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "postings", "notes", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "contacts", "contact_type", "TEXT NOT NULL DEFAULT 'generic'")
    ensure_column(conn, "contacts", "first_seen", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "contacts", "last_seen", "TEXT NOT NULL DEFAULT ''")
    conn.execute("UPDATE postings SET status = 'applied' WHERE applied = 1 AND status = 'new'")
    conn.execute("UPDATE contacts SET first_seen = date_scraped WHERE first_seen = ''")
    conn.execute("UPDATE contacts SET last_seen = date_scraped WHERE last_seen = ''")
    conn.commit()


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def upsert_postings(conn: sqlite3.Connection, postings: list[Posting]) -> list[tuple[str, Posting]]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_postings: list[tuple[str, Posting]] = []

    for posting in postings:
        pid = posting_id(posting)
        existing = conn.execute("SELECT id FROM postings WHERE id = ?", (pid,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE postings
                SET last_seen = ?, apply_action = ?, source_url = ?
                WHERE id = ?
                """,
                (now, posting.apply_action, posting.source_url, pid),
            )
            continue

        conn.execute(
            """
            INSERT INTO postings (
                id, company, role, apply_action, url, source, source_url,
                date_found, last_seen, applied, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'new')
            """,
            (
                pid,
                posting.company,
                posting.role,
                posting.apply_action,
                posting.url,
                posting.source,
                posting.source_url,
                now,
                now,
            ),
        )
        new_postings.append((pid, posting))

    conn.commit()
    return new_postings


def mark_applied(conn: sqlite3.Connection, posting_id_value: str, note: str = "") -> bool:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = conn.execute(
        """
        UPDATE postings
        SET applied = 1,
            status = 'applied',
            applied_at = ?,
            notes = CASE WHEN ? = '' THEN notes ELSE ? END
        WHERE id = ?
        """,
        (now, note, note, posting_id_value),
    )
    conn.commit()
    return result.rowcount > 0


def set_posting_status(conn: sqlite3.Connection, posting_id_value: str, status: str, note: str = "") -> bool:
    normalized = status.lower().strip()
    if normalized not in VALID_STATUSES:
        valid = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(f"Invalid status '{status}'. Use one of: {valid}")

    applied = 1 if normalized == "applied" else 0
    applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if normalized == "applied" else ""
    result = conn.execute(
        """
        UPDATE postings
        SET applied = ?,
            status = ?,
            applied_at = CASE WHEN ? = '' THEN applied_at ELSE ? END,
            notes = CASE WHEN ? = '' THEN notes ELSE ? END
        WHERE id = ?
        """,
        (applied, normalized, applied_at, applied_at, note, note, posting_id_value),
    )
    conn.commit()
    return result.rowcount > 0


def list_postings(
    conn: sqlite3.Connection,
    limit: int = 50,
    status: str | None = None,
    company: str | None = None,
) -> list[sqlite3.Row]:
    filters = []
    params: list[object] = []

    if status:
        filters.append("status = ?")
        params.append(status.lower().strip())
    if company:
        filters.append("LOWER(company) LIKE ?")
        params.append(f"%{company.lower()}%")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)

    return conn.execute(
        f"""
        SELECT id, company, role, source, apply_action, date_found, last_seen,
               applied, status, applied_at, notes
        FROM postings
        {where_clause}
        ORDER BY date_found DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def upsert_contacts(conn: sqlite3.Connection, contacts: list[Contact]) -> list[tuple[str, Contact]]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_contacts: list[tuple[str, Contact]] = []

    for contact in contacts:
        cid = contact_id(contact)
        existing = conn.execute("SELECT id FROM contacts WHERE id = ?", (cid,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE contacts
                SET source_page = ?,
                    contact_type = ?,
                    date_scraped = ?,
                    last_seen = ?
                WHERE id = ?
                """,
                (contact.source_page, contact.contact_type, now, now, cid),
            )
            continue

        conn.execute(
            """
            INSERT INTO contacts (
                id, company, email, source_page, contact_type,
                date_scraped, first_seen, last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                contact.company,
                contact.email,
                contact.source_page,
                contact.contact_type,
                now,
                now,
                now,
            ),
        )
        new_contacts.append((cid, contact))

    conn.commit()
    return new_contacts


def list_contacts(
    conn: sqlite3.Connection,
    company: str | None = None,
    contact_type: str | None = None,
) -> list[sqlite3.Row]:
    filters = []
    params: list[object] = []

    if company:
        filters.append("LOWER(company) LIKE ?")
        params.append(f"%{company.lower()}%")
    if contact_type:
        filters.append("contact_type = ?")
        params.append(contact_type.lower().strip())

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    return conn.execute(
        f"""
        SELECT id, company, email, source_page, contact_type, date_scraped, first_seen, last_seen
        FROM contacts
        {where_clause}
        ORDER BY company, contact_type, email
        """,
        params,
    ).fetchall()


def export_contacts_csv(
    conn: sqlite3.Connection,
    output_path: Path,
    company: str | None = None,
    contact_type: str | None = None,
) -> int:
    rows = list_contacts(conn, company=company, contact_type=contact_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company", "email", "contact_type", "source_page", "date_scraped", "first_seen", "last_seen"])
        for row in rows:
            writer.writerow(
                [
                    row["company"],
                    row["email"],
                    row["contact_type"],
                    row["source_page"],
                    row["date_scraped"],
                    row["first_seen"],
                    row["last_seen"],
                ]
            )

    return len(rows)
