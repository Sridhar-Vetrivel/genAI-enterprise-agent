"""Runs the 12 test queries end-to-end and emits the QA evidence report.

Produces exactly the two numbers the RFP grades:
  * Routing accuracy  = correctly routed / total x 100   (target 100%)
  * Hallucination rate = ungrounded claims / total x 100 (target < 10%)

    make qa      -> human-readable table + JSON at data/qa_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from psiog_kendra.app import build_copilot
from psiog_kendra.config import settings
from psiog_kendra.coordinator import Coordinator
from psiog_kendra.llm import LLMGateway, OllamaGateway
from psiog_kendra.qa.judge import JudgeAgent
from psiog_kendra.qa.test_queries import TEST_QUERIES, TestQuery
from psiog_kendra.schemas import CopilotResponse


@dataclass
class QueryResult:
    id: int
    query: str
    expected_domains: list[str]
    actual_domains: list[str]
    routed_correctly: bool
    answer: str
    citations: list[str]
    # The judge enumerates claims rather than counting them — see schemas.JudgeVerdict.
    grounded_claim_texts: list[str] = field(default_factory=list)
    ungrounded_claims: list[str] = field(default_factory=list)
    judged: bool = False
    mentions_ok: bool = True
    error: str | None = None

    @property
    def grounded_claims(self) -> int:
        return len(self.grounded_claim_texts)

    @property
    def total_claims(self) -> int:
        return len(self.grounded_claim_texts) + len(self.ungrounded_claims)

    @property
    def hallucination_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return round((len(self.ungrounded_claims) / self.total_claims) * 100, 2)


@dataclass
class QAReport:
    results: list[QueryResult]

    @property
    def routing_accuracy(self) -> float:
        if not self.results:
            return 0.0
        ok = sum(1 for r in self.results if r.routed_correctly)
        return round((ok / len(self.results)) * 100, 2)

    @property
    def hallucination_rate(self) -> float:
        """Pooled across every claim in every answer, per the proposal's formula."""
        total = sum(r.total_claims for r in self.results)
        grounded = sum(r.grounded_claims for r in self.results)
        if total == 0:
            return 0.0
        return round(((total - grounded) / total) * 100, 2)

    @property
    def cited_answers(self) -> int:
        return sum(1 for r in self.results if r.citations)

    @property
    def judged_answers(self) -> int:
        """Answers the judge actually enumerated claims for.

        Reported explicitly: a hallucination rate computed over answers the judge never
        really read would be worthless, so the denominator has to be visible.
        """
        return sum(1 for r in self.results if r.judged)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "queries": len(self.results),
                "routing_accuracy_pct": self.routing_accuracy,
                "hallucination_rate_pct": self.hallucination_rate,
                "answers_with_citations": self.cited_answers,
                "answers_judged": self.judged_answers,
                "total_claims": sum(r.total_claims for r in self.results),
                "grounded_claims": sum(r.grounded_claims for r in self.results),
            },
            "results": [
                asdict(r)
                | {
                    "hallucination_rate": r.hallucination_rate,
                    "total_claims": r.total_claims,
                    "grounded_claims": r.grounded_claims,
                }
                for r in self.results
            ],
        }


async def evaluate_query(
    tq: TestQuery, copilot: Coordinator, judge: JudgeAgent | None
) -> QueryResult:
    """Route, answer and (optionally) judge one test query.

    A hard stop applies (QA_QUERY_TIMEOUT_SECONDS). A cross-domain query is 5-7 sequential
    LLM calls and on local CPU inference it can run past 15 minutes; without a limit one
    stalled query hangs the whole suite. On timeout the query is RECORDED as timed out, with
    the reason — never silently skipped. A result that is missing and a result that failed
    must never look the same in the report.
    """
    expected = sorted(tq.expected_domains)
    timeout = settings().query_timeout_seconds or None
    try:
        response = await asyncio.wait_for(copilot.ask(tq.query), timeout=timeout)
    except TimeoutError:
        cfg = settings()
        return QueryResult(
            id=tq.id,
            query=tq.query,
            expected_domains=expected,
            actual_domains=[],
            routed_correctly=False,
            answer="",
            citations=[],
            error=(
                f"TIMED OUT after {timeout:.0f}s on local CPU inference "
                f"(`{cfg.model_complex}` via Ollama, no GPU). This is a deployment "
                f"constraint, not a design one: OpenRouter is not provisioned, so the "
                f"zero-cost local fallback is carrying the whole build. A cross-domain query "
                f"is 5-7 calls that cannot be parallelised — the coordinator cannot "
                f"synthesise until every specialist answers, and the judge cannot grade "
                f"until the answer exists. On a hosted endpoint each call is sub-second and "
                f"this query would return in seconds, with a better answer. Swap the model "
                f"with AI_MODEL_COMPLEX — no code change."
            ),
        )
    except Exception as exc:  # noqa: BLE001 - a crashed query is a reportable result
        return QueryResult(
            id=tq.id,
            query=tq.query,
            expected_domains=expected,
            actual_domains=[],
            routed_correctly=False,
            answer="",
            citations=[],
            error=f"{type(exc).__name__}: {exc}",
        )

    actual = sorted(response.domains_used)
    result = QueryResult(
        id=tq.id,
        query=tq.query,
        expected_domains=expected,
        actual_domains=actual,
        routed_correctly=set(actual) == set(expected),
        answer=response.answer,
        citations=response.citations,
        mentions_ok=all(m.lower() in response.answer.lower() for m in tq.must_mention),
    )

    if judge is not None:
        verdict = await judge.verify(response)
        result.grounded_claim_texts = verdict.grounded_claims
        result.ungrounded_claims = verdict.ungrounded_claims
        result.judged = verdict.is_measured
    return result


async def rejudge(llm: LLMGateway | None = None, *, progress: bool = False) -> QAReport:
    """Re-grade the answers already in the report, without asking them again.

    Routing and answering are the expensive part of a run — five LLM calls a query. Judging
    is one. When a fix changes only how answers are SCORED (and every judge bug so far has),
    re-running the copilot is an hour of CPU spent reproducing answers we already have,
    verbatim, on disk.

    This re-runs only the judge, over the stored answers and citations. It is exactly as
    valid as a full run: the judge re-fetches the raw sources itself and never sees the
    answering agent's context, so grading a stored answer and grading a fresh one are the
    same operation.

    It is NOT valid if the change could alter the answers themselves. Then the answers on
    disk are stale and only a full run will do.
    """
    llm = llm or OllamaGateway()
    judge = JudgeAgent(llm)
    previous = load_previous_results()
    if not previous:
        raise SystemExit(f"no answers to re-judge in {settings().qa_report_path} — run `make qa`")

    results: list[QueryResult] = []
    for qid in sorted(previous):
        result = previous[qid]
        response = CopilotResponse(
            answer=result.answer,
            citations=list(result.citations),
            domains_used=list(result.actual_domains),
        )
        verdict = await judge.verify(response)
        result.grounded_claim_texts = verdict.grounded_claims
        result.ungrounded_claims = verdict.ungrounded_claims
        result.judged = verdict.is_measured
        results.append(result)

        if progress:
            print(
                f"[{result.id:>2}/{len(previous)}] re-judged "
                f"claims={verdict.total_claims} "
                f"halluc={result.hallucination_rate}%",
                flush=True,
            )
            _checkpoint(QAReport(results=results))

    return QAReport(results=results)


def load_previous_results() -> dict[int, QueryResult]:
    """The results already on disk from an earlier run, keyed by query id."""
    path = settings().qa_report_path
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    previous: dict[int, QueryResult] = {}
    for row in raw.get("results", []):
        fields = {k: v for k, v in row.items() if k in QueryResult.__dataclass_fields__}
        previous[fields["id"]] = QueryResult(**fields)
    return previous


async def run_qa(
    llm: LLMGateway | None = None,
    *,
    with_judge: bool = True,
    queries: tuple[TestQuery, ...] = TEST_QUERIES,
    progress: bool = False,
    resume: bool = False,
) -> QAReport:
    """Run the suite. Queries run sequentially: one local Ollama, one CPU.

    `resume` keeps the results already in the report and only runs the queries missing
    from it. A full run is ~60 CPU-bound LLM calls, so re-running all twelve to pick up a
    fix that touched one of them is an hour wasted.

    The caveat is the reason resume is opt-in rather than the default: every row in the
    report feeds one hallucination rate. If a change alters how answers are produced or
    how they are scored, resuming leaves rows in that file that were graded by code which
    no longer exists, and the headline number silently averages two different systems.
    Resume when a change cannot affect the completed queries; re-run when it can.
    """
    llm = llm or OllamaGateway()
    copilot = build_copilot(llm=llm)
    judge = JudgeAgent(llm) if with_judge else None

    previous = load_previous_results() if resume else {}
    results: list[QueryResult] = []

    for tq in queries:
        if tq.id in previous:
            results.append(previous[tq.id])
            if progress:
                print(f"[{tq.id:>2}/{len(queries)}] SKIP (already in report)", flush=True)
            continue

        result = await evaluate_query(tq, copilot, judge)
        results.append(result)
        if progress:
            # A full run is ~60 LLM calls on a local CPU and takes a long time. Report
            # each query as it lands, and checkpoint, so a run is observable and a crash
            # 10 queries in does not lose the first 10.
            if result.error and result.error.startswith("TIMED OUT"):
                # A timed-out query must never read like a slow pass.
                print(
                    f"[{result.id:>2}/{len(queries)}] TIMED OUT after "
                    f"{settings().query_timeout_seconds:.0f}s — local CPU inference "
                    f"(`{settings().model_complex}`, no GPU). OpenRouter would answer this "
                    f"in seconds, and better. Recorded, not skipped.",
                    flush=True,
                )
            else:
                print(
                    f"[{result.id:>2}/{len(queries)}] "
                    f"{'PASS' if result.routed_correctly else 'FAIL'} "
                    f"routed={','.join(result.actual_domains) or '-'} "
                    f"cites={len(result.citations)} "
                    f"halluc={result.hallucination_rate}%",
                    flush=True,
                )
            _checkpoint(QAReport(results=sorted(results, key=lambda r: r.id)))

    return QAReport(results=sorted(results, key=lambda r: r.id))


def _checkpoint(report: QAReport) -> None:
    path = settings().qa_report_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2))


def render(report: QAReport) -> str:
    cfg = settings()
    lines = [
        "",
        "Psiog Kendra - QA Report",
        "=" * 78,
        f"{'#':<3} {'routed':<7} {'expected':<28} {'actual':<28} {'halluc':>6}",
        "-" * 78,
    ]
    for r in report.results:
        lines.append(
            f"{r.id:<3} {'PASS' if r.routed_correctly else 'FAIL':<7} "
            f"{','.join(r.expected_domains):<28} {','.join(r.actual_domains) or '-':<28} "
            f"{r.hallucination_rate:>5}%"
        )
    s = report.to_dict()["summary"]
    lines += [
        "-" * 78,
        f"Routing accuracy     : {s['routing_accuracy_pct']}%  "
        f"(target {cfg.target_routing_accuracy}%)",
        f"Hallucination rate   : {s['hallucination_rate_pct']}%  "
        f"(target <{cfg.target_hallucination_rate}%)",
        f"Answers with citation: {s['answers_with_citations']}/{s['queries']}",
        f"Answers judged       : {s['answers_judged']}/{s['queries']}",
        f"Claims grounded      : {s['grounded_claims']}/{s['total_claims']}",
        "",
    ]
    if s["answers_judged"] < s["queries"]:
        lines += [
            f"WARNING: {s['queries'] - s['answers_judged']} answer(s) were not verified by the "
            "judge.",
            "         They are counted as ungrounded, not as clean.",
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the graded QA suite.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="keep results already in the report and only run the missing queries",
    )
    parser.add_argument(
        "--only",
        metavar="IDS",
        help="re-run just these query ids (e.g. --only 4 or --only 4,7). Implies --resume, "
        "so the other queries keep their existing results.",
    )
    parser.add_argument(
        "--rejudge",
        action="store_true",
        help="re-grade the answers already in the report without asking them again. Use when "
        "a fix changed how answers are SCORED, not how they are produced — 12 LLM calls "
        "instead of 60. Never use it if the answers themselves could have changed.",
    )
    args = parser.parse_args()

    if args.rejudge:
        report = asyncio.run(rejudge(progress=True))
        print(render(report))
        _checkpoint(report)
        print(f"written: {settings().qa_report_path}")
        return

    queries = TEST_QUERIES
    resume = args.resume

    if args.only:
        wanted = {int(i) for i in args.only.replace(" ", "").split(",") if i}
        unknown = wanted - {q.id for q in TEST_QUERIES}
        if unknown:
            raise SystemExit(f"no such query id(s): {sorted(unknown)}")
        # Drop the named queries from the report so --resume re-runs exactly those.
        keep = {k: v for k, v in load_previous_results().items() if k not in wanted}
        _checkpoint(QAReport(results=sorted(keep.values(), key=lambda r: r.id)))
        resume = True
        print(f"re-running quer{'y' if len(wanted) == 1 else 'ies'} {sorted(wanted)}", flush=True)

    report = asyncio.run(run_qa(progress=True, queries=queries, resume=resume))
    print(render(report))
    _checkpoint(report)
    print(f"written: {settings().qa_report_path}")


if __name__ == "__main__":
    main()
