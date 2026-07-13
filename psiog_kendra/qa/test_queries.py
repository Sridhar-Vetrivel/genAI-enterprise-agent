"""The 12 mandatory test queries from the approved proposal (solution-proposal.md § 5).

`expected_domains` is the routing ground truth. The routing suite asserts the
coordinator's RoutingDecision.domains equals this set. Target: 100%.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psiog_kendra.domains import CRM, DATA_PLATFORM, DEVOPS, DOCS


@dataclass(frozen=True)
class TestQuery:
    id: int
    query: str
    expected_domains: frozenset[str]
    # Substrings that must appear in a correct answer. Used by the QA report to catch an
    # answer that is grounded but wrong.
    must_mention: tuple[str, ...] = field(default=())

    @property
    def is_cross_domain(self) -> bool:
        return len(self.expected_domains) > 1


TEST_QUERIES: tuple[TestQuery, ...] = (
    TestQuery(
        1,
        "Did yesterday's ETL pipeline for the sales data run successfully?",
        frozenset({DATA_PLATFORM}),
        ("sales_etl",),
    ),
    TestQuery(
        2,
        "What was the error in the last failed Databricks job?",
        frozenset({DATA_PLATFORM}),
        ("schema",),
    ),
    TestQuery(
        3,
        "Did the latest deployment of the payments service pass all quality gates?",
        frozenset({DEVOPS}),
        ("payments",),
    ),
    TestQuery(
        4,
        "What was the last deployment date for the auth service?",
        frozenset({DEVOPS}),
        ("auth",),
    ),
    TestQuery(
        5,
        "What is the current deal status for Acme Corp?",
        frozenset({CRM}),
        ("Negotiation",),
    ),
    TestQuery(
        6,
        "Who is the account owner for TechStart Ltd?",
        frozenset({CRM}),
        ("Karthik",),
    ),
    TestQuery(
        7,
        "What is the runbook for when the ingestion pipeline throws a schema mismatch error?",
        frozenset({DOCS}),
        ("quarantine",),
    ),
    TestQuery(
        8,
        "What does the architecture doc say about the ingestion pipeline?",
        frozenset({DOCS}),
        ("bronze",),
    ),
    TestQuery(
        9,
        "Did last night's pipeline failure affect any CRM customer sync?",
        frozenset({DATA_PLATFORM, CRM}),
        (),
    ),
    TestQuery(
        10,
        "The ingestion job failed - is there a fix in the runbooks?",
        frozenset({DATA_PLATFORM, DOCS}),
        (),
    ),
    TestQuery(
        11,
        "What's the status of the latest deployment and are there any known issues?",
        frozenset({DEVOPS, DOCS}),
        (),
    ),
    TestQuery(
        12,
        "Give me a full status update - pipeline, deployments, and any open incidents",
        frozenset({DATA_PLATFORM, DEVOPS, CRM, DOCS}),
        (),
    ),
)


def by_id(qid: int) -> TestQuery:
    for q in TEST_QUERIES:
        if q.id == qid:
            return q
    raise KeyError(f"no test query {qid}")


def routing_accuracy(results: dict[int, set[str]]) -> float:
    """(correctly routed / total) x 100 against the ground truth above."""
    if not results:
        return 0.0
    correct = sum(1 for qid, got in results.items() if got == set(by_id(qid).expected_domains))
    return round((correct / len(results)) * 100, 2)
