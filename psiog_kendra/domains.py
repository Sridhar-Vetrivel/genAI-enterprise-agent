"""The fixed domain vocabulary every routing decision must resolve to.

Kept in one place so the coordinator, the specialists, the test suite and the QA
judge all agree on the same four labels.
"""

from __future__ import annotations

DATA_PLATFORM = "data-platform"
DEVOPS = "devops"
CRM = "crm"
DOCS = "docs"

ALL_DOMAINS: tuple[str, ...] = (DATA_PLATFORM, DEVOPS, CRM, DOCS)

DOMAIN_DESCRIPTIONS: dict[str, str] = {
    DATA_PLATFORM: "Databricks data platform: ETL/ingestion pipelines, jobs, job runs, failures.",
    DEVOPS: "CI/CD: builds, deployments, quality gates, release history.",
    CRM: "Customer data: accounts, deals, deal stages, owners, contact history.",
    DOCS: "Internal knowledge: runbooks, architecture docs, incident records, SOPs.",
}


def domain_to_agent() -> dict[str, str]:
    """Domain label -> specialist node id, resolved from the environment.

    Imported lazily: config imports this module for the domain constants.
    """
    from psiog_kendra.config import settings

    return settings().domain_to_agent


def agent_for(domain: str) -> str:
    """The node id of the specialist that owns `domain`."""
    return domain_to_agent().get(domain, domain)


# Labels a small local model plausibly emits instead of the canonical ones. The
# routing schema cannot use a JSON-schema `enum` (Ollama 0.23 rejects it), so the
# model is free-form and we normalise here instead.
_ALIASES: dict[str, str] = {
    "data": DATA_PLATFORM,
    "data platform": DATA_PLATFORM,
    "dataplatform": DATA_PLATFORM,
    "databricks": DATA_PLATFORM,
    "pipeline": DATA_PLATFORM,
    "etl": DATA_PLATFORM,
    "data-agent": DATA_PLATFORM,
    "dev-ops": DEVOPS,
    "dev ops": DEVOPS,
    "ci/cd": DEVOPS,
    "cicd": DEVOPS,
    "deployment": DEVOPS,
    "deployments": DEVOPS,
    "github": DEVOPS,
    "devops-agent": DEVOPS,
    "customer": CRM,
    "customers": CRM,
    "sales": CRM,
    "hubspot": CRM,
    "crm-agent": CRM,
    "doc": DOCS,
    "documentation": DOCS,
    "runbook": DOCS,
    "runbooks": DOCS,
    "knowledge": DOCS,
    "docs-agent": DOCS,
}


def normalize_domain(raw: str) -> str | None:
    """Map a model-emitted domain label onto the canonical vocabulary.

    Returns None when the label cannot be resolved, so the caller can drop it
    rather than route to an agent that does not exist.
    """
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower().replace("_", "-")
    if key in ALL_DOMAINS:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    # "data-platform agent", "the docs domain", ...
    for canonical in ALL_DOMAINS:
        if canonical in key:
            return canonical
    for alias, canonical in _ALIASES.items():
        if alias in key.split():
            return canonical
    return None


def normalize_domains(raw: list[str]) -> list[str]:
    """Normalise a list of labels, dropping unknowns and de-duplicating.

    Order follows ALL_DOMAINS so routing assertions are order-independent.
    """
    resolved = {d for d in (normalize_domain(r) for r in raw) if d is not None}
    return [d for d in ALL_DOMAINS if d in resolved]


def domain_catalog() -> str:
    """The domain menu injected into the routing prompt."""
    return "\n".join(f"- {name}: {desc}" for name, desc in DOMAIN_DESCRIPTIONS.items())
