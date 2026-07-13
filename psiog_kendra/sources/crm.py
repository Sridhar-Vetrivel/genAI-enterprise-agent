"""CRM source client — accounts, deals and contact history.

Live path: a HubSpot-style REST API (`/accounts`, `/deals`, `/contacts`).
Mock path: data/mock/crm.json.
"""

from __future__ import annotations

from typing import Any

import httpx

from psiog_kendra.config import settings
from psiog_kendra.sources.base import SourceError, get_json, load_mock

CITATION_PREFIX = "CRM"


def _deal_citation(deal: dict[str, Any]) -> str:
    return f"{CITATION_PREFIX} deal {deal['deal_id']} ({deal['account_name']})"


def _account_citation(account: dict[str, Any]) -> str:
    return f"{CITATION_PREFIX} account {account['account_id']} ({account['name']})"


def _matches(value: str, needle: str) -> bool:
    """Loose account-name match: 'acme' should find 'Acme Corp'."""
    v, n = value.strip().lower(), needle.strip().lower()
    if not n:
        return True
    if n in v or v in n:
        return True
    # Match on any significant word ("techstart" in "TechStart Ltd").
    return any(w in v for w in n.split() if len(w) > 3)


class CRMClient:
    """Reads customer records from the CRM."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._cfg = settings()
        self._http = http

    async def _collection(self, name: str) -> list[dict[str, Any]]:
        cfg = self._cfg
        if cfg.use_mock_sources:
            return list(load_mock("crm")[name])
        if not cfg.crm_api_base or not cfg.crm_api_key:
            raise SourceError("CRM_API_BASE/CRM_API_KEY not set and mocks disabled")
        payload = await get_json(
            f"{cfg.crm_api_base.rstrip('/')}/{name}",
            headers={"Authorization": f"Bearer {cfg.crm_api_key}"},
            client=self._http,
        )
        # A CRM may return either {"deals": [...]} or a bare [...] list.
        if isinstance(payload, list):
            return list(payload)
        if isinstance(payload, dict):
            return list(payload.get(name, []))
        raise SourceError(f"CRM /{name} returned an unusable payload of type {type(payload)}")

    async def find_deals(self, account: str | None = None) -> list[dict[str, Any]]:
        deals = await self._collection("deals")
        if account:
            deals = [d for d in deals if _matches(str(d.get("account_name", "")), account)]
        return deals

    async def find_accounts(self, account: str | None = None) -> list[dict[str, Any]]:
        accounts = await self._collection("accounts")
        if account:
            accounts = [a for a in accounts if _matches(str(a.get("name", "")), account)]
        return accounts

    async def find_contacts(self, account: str | None = None) -> list[dict[str, Any]]:
        contacts = await self._collection("contacts")
        if account:
            contacts = [c for c in contacts if _matches(str(c.get("account_name", "")), account)]
        return contacts

    async def fetch(self, account: str | None = None) -> tuple[dict[str, Any], list[str]]:
        """Return (records, citations) — the grounding payload for the CRM agent.

        Sync status travels with the record so a stale account can never be reported as
        fresh — that is what makes the pipeline-failure/CRM cross-domain query answerable.
        """
        accounts = await self.find_accounts(account)
        deals = await self.find_deals(account)
        contacts = await self.find_contacts(account)
        citations = [_account_citation(a) for a in accounts] + [_deal_citation(d) for d in deals]
        return {"accounts": accounts, "deals": deals, "contacts": contacts}, citations
