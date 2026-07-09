from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SupabaseError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, url: str | None = None, service_key: str | None = None) -> None:
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.service_key = service_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.url or not self.service_key:
            raise SupabaseError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: Any = None,
        prefer: str = "",
    ) -> Any:
        suffix = f"?{urlencode(query, safe='(),.*:')}" if query else ""
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer

        request = Request(
            f"{self.url}/rest/v1/{path.lstrip('/')}{suffix}",
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise SupabaseError(f"Supabase HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise SupabaseError(f"Could not reach Supabase: {exc.reason}") from exc

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: dict[str, str] | None = None,
        order: str = "",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        query = {"select": columns, **(filters or {})}
        if order:
            query["order"] = order
        if limit is not None:
            query["limit"] = str(limit)
        return self.request("GET", table, query=query) or []

    def insert(
        self,
        table: str,
        rows: dict[str, Any] | list[dict[str, Any]],
        *,
        upsert: bool = False,
        ignore_duplicates: bool = False,
        on_conflict: str = "",
    ) -> list[dict[str, Any]]:
        query = {"on_conflict": on_conflict} if on_conflict else None
        resolution = "ignore-duplicates" if ignore_duplicates else "merge-duplicates"
        prefer = f"return=representation,resolution={resolution}" if upsert else "return=representation"
        return self.request("POST", table, query=query, body=rows, prefer=prefer) or []

    def update(self, table: str, values: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        return self.request(
            "PATCH",
            table,
            query=filters,
            body=values,
            prefer="return=representation",
        ) or []

    def rpc(self, function_name: str, arguments: dict[str, Any]) -> Any:
        return self.request("POST", f"rpc/{function_name}", body=arguments)


def verify_user_token(token: str) -> dict[str, Any]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not anon_key or not token:
        raise SupabaseError("Authentication is not configured")

    request = Request(
        f"{url}/auth/v1/user",
        headers={"apikey": anon_key, "Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise SupabaseError("Invalid or expired user session") from exc

