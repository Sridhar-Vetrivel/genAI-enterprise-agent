"""Shared plumbing for the three REST-backed source clients.

Each client has two paths:
  * live  — an authenticated REST call to the real system;
  * mock  — a realistic synthetic fixture from the configured MOCK_DIR.

USE_MOCK_SOURCES selects between them. No Databricks / GitHub / CRM tenant is
provisioned for the capstone, so the demo runs on the fixtures, and the live path is
exercised in unit tests with a mocked transport.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import httpx

from psiog_kendra.config import settings


class SourceError(RuntimeError):
    """A source system could not be reached or returned an unusable response."""


@lru_cache(maxsize=16)
def load_mock(name: str) -> dict[str, Any]:
    """Load and cache a fixture from <MOCK_DIR>/<name>.json."""
    path = settings().mock_dir / f"{name}.json"
    if not path.exists():
        raise SourceError(f"mock fixture not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SourceError(f"mock fixture is not valid JSON: {path}") from exc


async def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float | None = None,
    client: httpx.AsyncClient | None = None,
) -> Any:
    """GET a JSON document, turning any transport/HTTP failure into SourceError."""
    timeout = settings().source_timeout if timeout is None else timeout
    try:
        if client is not None:
            resp = await client.get(url, headers=headers, params=params)
        else:
            async with httpx.AsyncClient(timeout=timeout) as owned:
                resp = await owned.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise SourceError(f"{url} returned HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise SourceError(f"{url} unreachable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SourceError(f"{url} returned a non-JSON body") from exc
