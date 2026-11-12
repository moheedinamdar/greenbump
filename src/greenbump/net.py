"""Small HTTP helpers on the standard library.

Only https URLs are allowed, plus plain http to the local machine (for a local Ollama).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

USER_AGENT = "greenbump (+https://github.com/moheedinamdar/greenbump)"
MAX_BODY_BYTES = 8_000_000
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class NetworkError(RuntimeError):
    """A request failed: bad URL, connection error, HTTP error or unreadable body."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS:
        return
    raise NetworkError(f"refusing {url!r}: use https, or http only for localhost")


def get_text(url: str, timeout: float = 30.0) -> str:
    return _request(url, None, {"Accept": "text/plain, */*"}, timeout).decode("utf-8", errors="replace")


def get_json(url: str, timeout: float = 30.0) -> Any:
    return _loads(_request(url, None, {"Accept": "application/json"}, timeout), url)


def post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: float = 600.0
) -> Any:
    hdrs = {"Accept": "application/json", "Content-Type": "application/json", **(headers or {})}
    return _loads(_request(url, json.dumps(payload).encode(), hdrs, timeout), url)


def _request(url: str, data: bytes | None, headers: dict[str, str], timeout: float) -> bytes:
    check_url(url)
    req = urllib.request.Request(  # noqa: S310  scheme is validated by check_url
        url,
        data=data,
        headers={"User-Agent": USER_AGENT, **headers},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  scheme validated
            body: bytes = resp.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise NetworkError(f"HTTP {exc.code} from {_host(url)}", status=exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NetworkError(f"cannot reach {_host(url)}: {exc}") from exc
    if len(body) > MAX_BODY_BYTES:
        raise NetworkError(f"response from {_host(url)} is larger than {MAX_BODY_BYTES} bytes")
    return body


def _loads(body: bytes, url: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise NetworkError(f"non-JSON response from {_host(url)}") from exc


def _host(url: str) -> str:
    return urlparse(url).netloc or url
