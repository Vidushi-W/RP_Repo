"""Best-effort client for storing summarized practice results in the API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _request_json(path: str, method: str = "GET", payload: dict | None = None):
    base_url = os.getenv("SLSL_API_URL", "http://127.0.0.1:8000").rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}", data=data,
        headers={"Content-Type": "application/json"}, method=method,
    )
    with urlopen(request, timeout=3.0) as response:
        return json.loads(response.read().decode("utf-8"))


def load_recent_attempts(user_id: str, limit: int = 4) -> tuple[list[dict] | None, str]:
    """Read MongoDB history; ``None`` means API/Atlas was unavailable."""
    try:
        attempts = _request_json(f"/api/users/{quote(user_id, safe='')}/attempts?limit={limit}")
        return attempts, "MongoDB"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None, "SQLite fallback"


def save_practice_result(payload: dict) -> tuple[bool, str]:
    """Post a result without interrupting camera practice if the API is offline."""
    try:
        _request_json("/api/attempts", method="POST", payload=payload)
        return True, "saved to MongoDB"
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("detail", "API rejected the result")
        except (ValueError, AttributeError):
            detail = "API rejected the result"
        return False, str(detail)
    except (URLError, TimeoutError, OSError, ValueError):
        return False, "API unavailable; result was not saved"
