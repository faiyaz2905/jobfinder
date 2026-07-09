from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "InternshipRadar/0.1 (+personal career tracker)"


def fetch_text(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"Could not fetch {url}: {reason}") from exc

