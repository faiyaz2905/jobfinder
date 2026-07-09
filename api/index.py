from __future__ import annotations

import json
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from radar.cloud.scan_runner import run_cloud_scan, utc_now
from radar.cloud.supabase import SupabaseClient, SupabaseError, verify_user_token


def allowed_emails() -> set[str]:
    return {
        value.strip().lower()
        for value in os.environ.get("ALLOWED_USER_EMAILS", "").replace(";", ",").split(",")
        if value.strip()
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._security_headers()
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            route = query.pop("route", [""])[0].strip("/")
            if route:
                path = f"/api/{route}"
            if not path.startswith("/api/"):
                return self._serve_dashboard(path)

            if path == "/api/cron/scan":
                if method != "GET":
                    return self._json(405, {"error": "method_not_allowed"})
                self._require_cron()
                return self._json(200, run_cloud_scan("scheduled"))

            user = self._require_user()
            if method in {"POST", "PATCH"}:
                self._require_same_origin()

            if path == "/api/postings" and method == "GET":
                return self._list_postings(query)
            if path.startswith("/api/postings/") and path.endswith("/apply") and method in {"POST", "PATCH"}:
                posting_id = path.removeprefix("/api/postings/").removesuffix("/apply").strip("/")
                return self._mark_applied(posting_id)
            if path == "/api/contacts" and method == "GET":
                return self._list_contacts()
            if path == "/api/companies" and method == "GET":
                return self._list_companies()
            if path == "/api/companies" and method == "POST":
                return self._add_company()
            if path.startswith("/api/companies/") and method == "PATCH":
                return self._update_company(path.rsplit("/", 1)[-1])
            if path == "/api/health" and method == "GET":
                return self._health()
            if path == "/api/scans" and method == "POST":
                cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec="seconds")
                recent = SupabaseClient().select(
                    "scan_runs",
                    filters={"trigger": "eq.manual", "started_at": f"gte.{cutoff}"},
                    limit=1,
                )
                if recent:
                    return self._json(429, {"error": "manual_scan_cooldown"})
                return self._json(200, run_cloud_scan("manual"))
            if path == "/api/session" and method == "GET":
                return self._json(200, {"email": user.get("email", "")})
            return self._json(404, {"error": "not_found"})
        except PermissionError as exc:
            return self._json(401, {"error": str(exc)})
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})
        except SupabaseError:
            return self._json(503, {"error": "database_or_auth_service_unavailable"})
        except Exception:
            return self._json(500, {"error": "internal_server_error"})

    def _require_cron(self) -> None:
        secret = os.environ.get("CRON_SECRET", "")
        supplied = self.headers.get("Authorization", "")
        if not secret or supplied != f"Bearer {secret}":
            raise PermissionError("unauthorized")

    def _require_user(self) -> dict:
        supplied = self.headers.get("Authorization", "")
        if not supplied.startswith("Bearer "):
            raise PermissionError("authentication_required")
        user = verify_user_token(supplied[7:])
        allowlist = allowed_emails()
        if not allowlist or user.get("email", "").lower() not in allowlist:
            raise PermissionError("user_not_allowed")
        return user

    def _require_same_origin(self) -> None:
        expected = os.environ.get("APP_ORIGIN", "").rstrip("/")
        origin = self.headers.get("Origin", "").rstrip("/")
        if expected and origin != expected:
            raise PermissionError("invalid_origin")

    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length", "0")), 16384)
        if length <= 0:
            return {}
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid_json") from exc
        if not isinstance(value, dict):
            raise ValueError("request_body_must_be_an_object")
        return value

    def _list_postings(self, query: dict[str, list[str]]) -> None:
        filters = {}
        status = query.get("status", [""])[0]
        if status:
            filters["status"] = f"eq.{status}"
        rows = SupabaseClient().select("postings", filters=filters, order="first_seen_at.desc", limit=500)
        data = [
            {
                **row,
                "date_found": row.get("first_seen_at"),
                "last_seen": row.get("last_seen_at"),
                "applied": row.get("status") == "applied",
            }
            for row in rows
        ]
        self._json(200, data)

    def _mark_applied(self, posting_id: str) -> None:
        if not posting_id or len(posting_id) > 64:
            raise ValueError("invalid_posting_id")
        rows = SupabaseClient().update(
            "postings",
            {"status": "applied", "applied_at": utc_now()},
            {"id": f"eq.{posting_id}"},
        )
        if not rows:
            return self._json(404, {"error": "posting_not_found"})
        self._json(200, {"ok": True, "posting": rows[0]})

    def _list_contacts(self) -> None:
        rows = SupabaseClient().select("contacts", order="company.asc,email.asc", limit=1000)
        self._json(
            200,
            [{**row, "date_scraped": row.get("last_seen_at")} for row in rows],
        )

    def _list_companies(self) -> None:
        self._json(200, SupabaseClient().select("companies", order="name.asc", limit=500))

    def _add_company(self) -> None:
        body = self._body()
        name = str(body.get("name", "")).strip()
        career_url = str(body.get("career_url", "")).strip()
        if not name or not career_url.startswith("https://"):
            raise ValueError("name_and_https_career_url_are_required")
        allowed = {
            "name",
            "career_url",
            "category",
            "ats_type",
            "ats_identifier",
            "notes",
            "linkedin_slug",
            "facebook_url",
            "enabled",
        }
        row = {key: value for key, value in body.items() if key in allowed}
        rows = SupabaseClient().insert("companies", row)
        self._json(201, rows[0])

    def _update_company(self, company_id: str) -> None:
        body = self._body()
        allowed = {
            "name",
            "career_url",
            "category",
            "ats_type",
            "ats_identifier",
            "notes",
            "linkedin_slug",
            "facebook_url",
            "enabled",
        }
        values = {key: value for key, value in body.items() if key in allowed}
        if not values:
            raise ValueError("no_supported_fields")
        if "career_url" in values and not str(values["career_url"]).startswith("https://"):
            raise ValueError("career_url_must_use_https")
        rows = SupabaseClient().update("companies", values, {"id": f"eq.{company_id}"})
        if not rows:
            return self._json(404, {"error": "company_not_found"})
        self._json(200, rows[0])

    def _health(self) -> None:
        db = SupabaseClient()
        scans = db.select("scan_runs", order="started_at.desc", limit=20)
        latest_success = next(
            (row for row in scans if row.get("status") in {"succeeded", "partial"}),
            None,
        )
        latest_email = next(
            (row for row in scans if row.get("notification_status") == "sent"),
            None,
        )
        latest = scans[0] if scans else None
        self._json(
            200,
            {
                "last_scan_time": latest_success.get("finished_at") if latest_success else None,
                "last_email_sent_time": latest_email.get("finished_at") if latest_email else None,
                "latest_scan": latest,
                "recent_scans": scans,
                "flagged_companies": [
                    error.get("company")
                    for error in (latest or {}).get("error_summary", [])
                    if error.get("company") and not error["company"].startswith("_")
                ],
                "per_company_posting_counts": {},
            },
        )

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_dashboard(self, request_path: str) -> None:
        dist_dir = Path(__file__).resolve().parents[1] / "radar-dashboard" / "dist"
        relative = request_path.lstrip("/")
        candidate = (dist_dir / relative).resolve() if relative else dist_dir / "index.html"
        if not str(candidate).startswith(str(dist_dir.resolve())) or not candidate.is_file():
            candidate = dist_dir / "index.html"
        if not candidate.is_file():
            return self._json(404, {"error": "dashboard_not_built"})

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        body = candidate.read_bytes()
        self.send_response(200)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
