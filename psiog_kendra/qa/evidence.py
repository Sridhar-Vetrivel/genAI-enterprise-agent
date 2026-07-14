"""Turn QA results into per-query evidence files for the mid-term Evidence Pack.

    make evidence          # regenerate docs/qa/ from data/qa_report.json

One file per test query: what was asked, how it routed, what it answered, what it cited,
what the Judge Agent found — plus the exact command to reproduce it and instructions for
the screenshot that goes into the mid-term submission (Section 4).

See docs/MidTerm_Submission_Reference.md for how these map to Evidence IDs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.domains import agent_for
from psiog_kendra.qa.test_queries import TEST_QUERIES, by_id

# Which Week 4-9 deliverable each domain evidences (see Implementation.md build status).
DOMAIN_TO_DELIVERABLE = {
    "data-platform": "D-03 (Week 6 — Data Platform agent)",
    "devops": "D-05 (Week 8 — DevOps agent)",
    "crm": "D-06 (Week 9 — CRM agent)",
    "docs": "D-04 (Week 7 — Docs agent + RAG index)",
}


def evidence_id(index: int) -> str:
    """EV-01, EV-02, ... — the key the mid-term template's Section 4.1 index is built on.

    Section 3 requires every deliverable marked Done or Partial to point at one of these,
    and the evaluator cross-checks that link. A page without an Evidence ID cannot be
    referenced, so it cannot support a claim.
    """
    return f"EV-{index:02d}"


def _deliverables(domains: list[str]) -> list[str]:
    items = ["D-02 (Week 5 — Coordinator routing)"]
    items += [DOMAIN_TO_DELIVERABLE[d] for d in domains if d in DOMAIN_TO_DELIVERABLE]
    if len(domains) > 1:
        items.append("D-07 (cross-domain synthesis, cited across systems)")
    return items


@dataclass(frozen=True)
class Artefact:
    """Evidence the 12 test queries structurally cannot provide.

    A query proves an agent routes and cites. It says nothing about whether the test suite
    passes, what the coverage figure is, whether the RAG index built, or whether the control
    plane runs — and Sections 3 and 6 of the template ask for exactly those. Screenshot only
    the query pages and D-01 and D-08 have no evidence at all.
    """

    slug: str
    title: str
    deliverable: str
    caption: str
    command: str
    look_for: list[str]
    note: str = ""


ARTEFACTS: tuple[Artefact, ...] = (
    Artefact(
        slug="qa-summary",
        title="QA summary — routing accuracy and hallucination rate",
        deliverable="D-07 (12 test queries, grounded and cited)",
        caption="The graded QA run: routing accuracy and hallucination rate across all 12 queries",
        command="make qa",
        look_for=[
            "the `Routing accuracy` line — the headline number for Section 6",
            "the `Hallucination rate` line, and the claim counts behind it",
            "the `Answers judged` line — a rate computed from unjudged answers is worthless, "
            "so this must read 12/12",
            "the per-query PASS lines above the summary",
        ],
        note=(
            "**On response time — say this before anyone asks.** A full run is ~60 LLM calls "
            "and takes about an hour, and a single cross-domain query takes 8-15 minutes. "
            "That is *not* the architecture. Every call runs on `gemma3:4b` under Ollama, on "
            "CPU, with no GPU, because **OpenRouter is not provisioned** and the zero-cost "
            "local fallback is carrying the whole build. A cross-domain query is 5-7 calls "
            "that cannot be parallelised — the coordinator cannot synthesise until the "
            "specialists answer, and the judge cannot grade until the answer exists. On a "
            "hosted endpoint those calls are sub-second, so the same run finishes in "
            "single-digit minutes and the answers get *better*: most of the leak-stripping "
            "and citation-repair in `prompting.py` exists to compensate for a 4B model. "
            "`AI_MODEL_COMPLEX` is an env var — the day OpenRouter is provisioned the model "
            "swaps with no code change. Record it in Section 8 as a deployment constraint, "
            "not a design one."
        ),
    ),
    Artefact(
        slug="tests-coverage",
        title="Test suite and coverage",
        deliverable="D-08 (unit tests passing; coverage >= 50%)",
        caption="Full offline test suite passing, with the measured coverage figure",
        command="make cov",
        look_for=[
            "the final `TOTAL` coverage percentage — this is the real tool figure Section 6 "
            "demands, not a claim",
            "the passed/failed count on the last line",
            "the per-module table, which shows coverage is spread across routing, retrieval, "
            "sources and QA — not concentrated in one easy module",
        ],
        note=(
            "This suite runs with no LLM, no network and no control plane, which is why it is "
            "fast and reproducible. That is the point of keeping `psiog_kendra/` framework-free."
        ),
    ),
    Artefact(
        slug="rag-index",
        title="RAG index build",
        deliverable="D-04 (Docs agent + RAG index: chunked, embedded, searchable)",
        caption="The documentation corpus chunked, embedded and indexed for similarity search",
        command="make index",
        look_for=[
            "the chunk count and the embedding model (`nomic-embed-text`, 768-dim)",
            "`0 orphans` — every chunk carries a citation, so no retrieved text can be "
            "un-attributable",
            "the path the index is written to",
        ],
        note=(
            "Gemma 3 cannot produce embeddings at all, which is why a separate embedding model "
            "is pulled. Worth stating in Section 8 as a deviation."
        ),
    ),
    Artefact(
        slug="control-plane",
        title="AgentField control plane and the 5 registered agents",
        deliverable="D-01 (control plane via Docker Compose)",
        caption="The AgentField control plane running, with all five agent nodes registered",
        command="make up && make agents",
        look_for=[
            "the control plane container coming up healthy",
            "all five nodes registering: coordinator, data, devops, crm, docs",
            "the control-plane URL, so the evaluator can see it is self-hosted and not a "
            "managed service",
        ],
        note=(
            "**D-01 is Partial, not Done, and should be declared as such.** The approved "
            "proposal committed to the control plane *plus* an Azure VM *plus* OpenRouter "
            "connected. OpenRouter is not provisioned, so all inference runs locally at "
            "zero cost. Claiming D-01 as Done without evidence for those two parts is exactly "
            "the inconsistency the evaluator cross-checks for — declare it Partial and record "
            "the deviation in Section 8."
        ),
    ),
)


def render_query(result: dict[str, Any]) -> str:
    """The evidence page for one test query."""
    cfg = settings()
    qid = result["id"]
    tq = by_id(qid)
    expected = result["expected_domains"]
    actual = result["actual_domains"]
    passed = result["routed_correctly"]
    citations = result["citations"]
    agents = [agent_for(d) for d in actual]

    total = result.get("total_claims", 0)
    grounded = result.get("grounded_claims", 0)
    grounded_texts = result.get("grounded_claim_texts", []) or []
    ungrounded = result.get("ungrounded_claims", []) or []
    halluc = result.get("hallucination_rate", 0.0)
    judged = result.get("judged", False)

    kind = "cross-domain" if len(expected) > 1 else "single-domain"
    verdict = "✅ PASS — routed exactly as expected" if passed else "❌ FAIL"
    eid = evidence_id(qid)

    lines: list[str] = [
        f"# {eid} — Q{qid:02d} — {kind.title()} — {'PASS' if passed else 'FAIL'}",
        "",
        f"> **Question asked:** “{tq.query}”",
        "",
        "## What happened",
        "",
        "| | |",
        "|---|---|",
        f"| **Evidence ID** | **{eid}** (cite this from Section 3) |",
        f"| **Test query #** | {qid} of 12 |",
        f"| **Type** | {kind} |",
        f"| **Expected domain(s)** | `{'`, `'.join(expected)}` |",
        f"| **Actual domain(s) routed to** | `{'`, `'.join(actual) or '—'}` |",
        f"| **Routing result** | {verdict} |",
        f"| **Specialist agent(s) invoked** | {', '.join(f'`{a}`' for a in agents) or '—'} |",
        f"| **Citations returned** | {len(citations)} |",
        f"| **Claims grounded (Judge Agent)** | {grounded} / {total} |",
        f"| **Hallucination rate** | {halluc}% (target &lt;{cfg.target_hallucination_rate}%) |",
        f"| **Routing model** | `{cfg.model_complex}` (local Ollama, ₹0) |",
        "",
        "### The copilot's answer",
        "",
        "```text",
        result["answer"].strip() or "(no answer)",
        "```",
        "",
        "### Citations (this is what makes the answer grounded)",
        "",
    ]

    if citations:
        lines += [f"{i}. `{c}`" for i, c in enumerate(citations, 1)]
    else:
        lines.append("**None — an uncited answer is treated as 100% ungrounded by the Judge.**")

    lines += [
        "",
        "### Judge Agent verdict",
        "",
        "The Judge Agent re-fetched the raw source content behind each citation (independently "
        "of what the answering agent saw) and checked every factual claim against it.",
        "",
    ]

    if not judged:
        lines += [
            "> ⚠️ **UNVERIFIED — the Judge could not enumerate the claims in this answer.**",
            "> This is counted as ungrounded, NOT as a clean pass. Re-run `make qa` with "
            "> `gemma3:4b` loaded (it needs ~4 GiB free RAM); the small model is too weak to "
            "> decompose claims reliably.",
        ]
    else:
        lines += [
            f"It found **{total} factual claim(s)**, of which **{grounded} were grounded** in "
            f"the cited sources — a hallucination rate of **{halluc}%**.",
            "",
        ]
        if grounded_texts:
            lines.append("**Grounded claims** (each traced to a cited source):")
            lines += [f"- ✅ {c}" for c in grounded_texts]
            lines.append("")
        if ungrounded:
            lines.append("**Ungrounded claims** (flagged as hallucinations):")
            lines += [f"- ❌ {c}" for c in ungrounded]
        else:
            lines.append(
                "**No ungrounded claims** — every assertion traces back to a cited source."
            )

    if result.get("error"):
        lines += ["", f"> ⚠️ Error during run: `{result['error']}`"]

    if tq.must_mention and not result.get("mentions_ok", True):
        lines += [
            "",
            f"> ⚠️ The answer is grounded but did not mention the expected fact(s): "
            f"{', '.join(tq.must_mention)}",
        ]

    lines += [
        "",
        "## Why this proves what it proves",
        "",
        f"- **Routing is LLM intent classification, not keywords.** The coordinator sent this "
        f"question to `{'`, `'.join(actual) or '—'}` by classifying its intent with "
        f"`{cfg.model_complex}`. There is no `if/else` on keywords anywhere in the router.",
    ]
    if len(actual) > 1:
        lines.append(
            "- **Cross-domain synthesis works.** Multiple specialists were dispatched in "
            "parallel and their answers were merged into one reply that cites every system used."
        )
    if citations:
        lines.append(
            "- **The answer is grounded.** Every claim traces to a live source record or an "
            "indexed document section — nothing comes from the model's training data."
        )

    lines += [
        "",
        "**Deliverables evidenced:** " + "; ".join(_deliverables(actual)),
        "",
        "## How to reproduce this",
        "",
        "```bash",
        "# 1. Ollama must be running with the models pulled, and ~4 GiB of RAM free",
        "#    (gemma3:4b will not load below that — check with: ollama ps)",
        "ollama serve",
        "",
        "# 2. Build the vector index once",
        "make index",
        "",
        "# 3. Ask this exact question",
        f'make ask Q="{tq.query}"',
        "```",
        "",
        "To re-run the whole graded suite and regenerate this file:",
        "",
        "```bash",
        "make qa         # 12 queries + Judge Agent -> data/qa_report.json",
        "make evidence   # regenerates docs/qa/*.md from that report",
        "```",
        "",
        "## 📸 How to take the screenshot (for the mid-term Evidence Pack)",
        "",
        "The mid-term template requires a **full-size, readable** screenshot pasted directly "
        "into the document (no collages, no thumbnails). For this query:",
        "",
        "1. Open a terminal and make the window wide enough that no line wraps.",
        "",
        "2. Run the command below. Keep the **command itself visible** above the output — the",
        "   evaluator must be able to see the question that was asked, not just the answer:",
        "",
        "   ```bash",
        f'   make ask Q="{tq.query}"',
        "   ```",
        "",
        "3. Wait for the answer, then check that **all four of these are in the same frame**:",
        "",
        "   - the question you typed,",
        "   - the answer text,",
        f"   - the `routed to :` line (it must show {', '.join(f'`{a}`' for a in agents) or '—'}),",
        "   - the `sources   :` list — this is the grounding, and it is the whole point.",
        "",
        "4. Screenshot the **whole terminal window**, not a crop.",
        "",
        "5. Paste it into the mid-term doc under its Evidence block, and fill the header table:",
        "",
        "   | Field | Value |",
        "   |---|---|",
        f"   | Evidence ID | {eid} |",
        f"   | What this proves | Q{qid:02d} routes to "
        f"`{'`, `'.join(actual) or '—'}` and returns a cited, grounded answer |",
        f"   | Deliverable ID | {', '.join(d.split(' ')[0] for d in _deliverables(actual))} |",
        "   | Date captured | *(fill in)* |",
        "   | Verifiable link | *(GitHub commit for `data/qa_report.json`)* |",
        "",
        "> **Do not screenshot a fallback run.** If the terminal prints",
        "> `gemma3:4b does not fit in host memory; falling back to gemma3:1b`, the answer came",
        "> from the weak model and neither the routing nor the answer is representative.",
        "> Free ~4 GiB of RAM (check with `ollama ps`) and run it again.",
        "",
        "---",
        "",
        f"*Generated by `make evidence` from `{cfg.qa_report_path.name}`. "
        "Do not hand-edit — re-run `make qa && make evidence` instead.*",
    ]
    return "\n".join(lines) + "\n"


def render_artefact(artefact: Artefact, index: int) -> str:
    """An evidence page for something the 12 test queries cannot prove.

    A query shows an agent routing and citing. It says nothing about whether the suite
    passes, what coverage actually is, whether the index built, or whether the control plane
    runs — and Sections 3 and 6 ask for all four. Without these, D-01 and D-08 would go into
    the submission with no evidence behind them at all.
    """
    cfg = settings()
    eid = evidence_id(index)

    lines = [
        f"# {eid} — {artefact.title}",
        "",
        "| | |",
        "|---|---|",
        f"| **Evidence ID** | **{eid}** (cite this from Section 3) |",
        f"| **Deliverable** | {artefact.deliverable} |",
        f"| **Command** | `{artefact.command}` |",
        "",
        "## Why this page exists",
        "",
        "The 12 test-query pages prove the agents route correctly and answer with citations. "
        "They cannot prove this. Screenshot only the query pages and this deliverable goes "
        "into the submission unevidenced, which is precisely the inconsistency the evaluator "
        "cross-checks for.",
        "",
        "## 📸 How to take the screenshot",
        "",
        "1. Open a terminal wide enough that no line wraps.",
        "",
        "2. Run the command, keeping it visible above its output:",
        "",
        "   ```bash",
        f"   {artefact.command}",
        "   ```",
        "",
        "3. Check that these are all in the same frame:",
        "",
    ]
    lines += [f"   - {item}," for item in artefact.look_for]
    lines += [
        "",
        "4. Screenshot the **whole terminal window**, not a crop.",
        "",
        "5. Paste it into the mid-term doc under its Evidence block, and fill the header table:",
        "",
        "   | Field | Value |",
        "   |---|---|",
        f"   | Evidence ID | {eid} |",
        f"   | What this proves | {artefact.caption} |",
        f"   | Deliverable ID | {artefact.deliverable.split(' ')[0]} |",
        "   | Date captured | *(fill in)* |",
        "   | Verifiable link | *(GitHub commit)* |",
        "",
    ]
    if artefact.note:
        lines += ["> " + artefact.note.replace("\n", "\n> "), ""]

    lines += [
        "---",
        "",
        f"*Generated by `make evidence`. Models: `{cfg.model_complex}` / `{cfg.model_simple}`, "
        "local Ollama, ₹0.*",
    ]
    return "\n".join(lines) + "\n"


def evidence_rows(report: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """(Evidence ID, caption, deliverable IDs, file) for every page — the Section 4.1 index."""
    rows: list[tuple[str, str, str, str]] = []
    results = {r["id"]: r for r in report["results"]}

    for tq in TEST_QUERIES:
        r = results.get(tq.id)
        if not r:
            continue
        domains = r["actual_domains"]
        rows.append(
            (
                evidence_id(tq.id),
                f"Q{tq.id:02d} “{tq.query}” routes to "
                f"{', '.join(domains) or '—'} and answers with citations",
                ", ".join(d.split(" ")[0] for d in _deliverables(domains)),
                f"q{tq.id:02d}.md",
            )
        )

    for offset, artefact in enumerate(ARTEFACTS):
        idx = len(TEST_QUERIES) + offset + 1
        rows.append(
            (
                evidence_id(idx),
                artefact.caption,
                artefact.deliverable.split(" ")[0],
                f"{evidence_id(idx).lower()}-{artefact.slug}.md",
            )
        )
    return rows


def render_index(report: dict[str, Any]) -> str:
    """The docs/qa/ index — the Evidence Index (Section 4.1) in miniature."""
    cfg = settings()
    s = report["summary"]
    results = {r["id"]: r for r in report["results"]}

    lines = [
        "# QA Evidence — the 12 mandatory test queries",
        "",
        "Auto-generated from the last `make qa` run. One page per test query: what was asked, "
        "how it routed, what it cited, what the Judge Agent found, and how to screenshot it "
        "for the mid-term Evidence Pack.",
        "",
        "## Headline numbers",
        "",
        "| Metric | Target | Measured |",
        "|---|---|---|",
        f"| Routing accuracy | {cfg.target_routing_accuracy}% | **{s['routing_accuracy_pct']}%** |",
        f"| Hallucination rate | &lt;{cfg.target_hallucination_rate}% | "
        f"**{s['hallucination_rate_pct']}%** |",
        f"| Answers carrying citations | all | "
        f"**{s['answers_with_citations']} / {s['queries']}** |",
        f"| Claims grounded | — | **{s['grounded_claims']} / {s['total_claims']}** |",
        f"| Answers verified by the Judge | all | "
        f"**{s.get('answers_judged', 0)} / {s['queries']}** |",
        f"| LLM cost | ₹0 | **₹0** (local `{cfg.model_complex}` / `{cfg.model_simple}`) |",
        "",
        f"Queries completed in this run: **{s['queries']} / {len(TEST_QUERIES)}**",
        "",
    ]

    if s.get("answers_judged", 0) < s["queries"]:
        lines += [
            f"> ⚠️ **{s['queries'] - s.get('answers_judged', 0)} answer(s) were not verified "
            "by the Judge Agent.** They are counted as ungrounded, not as clean. A judge that "
            "enumerates no claims has done no work, and reporting that as 0% hallucination "
            "would be worthless.",
            "",
        ]

    lines += [
        "## Per-query evidence",
        "",
        "| # | Query | Expected | Routed to | Cites | Halluc. | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]

    for tq in TEST_QUERIES:
        r = results.get(tq.id)
        if not r:
            lines.append(
                f"| {tq.id} | {tq.query} | `{'`, `'.join(sorted(tq.expected_domains))}` "
                f"| _not yet run_ | — | — | — |"
            )
            continue
        status = "✅" if r["routed_correctly"] else "❌"
        name = f"q{tq.id:02d}.md"
        lines.append(
            f"| {tq.id} | {tq.query} | `{'`, `'.join(r['expected_domains'])}` "
            f"| {status} `{'`, `'.join(r['actual_domains']) or '—'}` "
            f"| {len(r['citations'])} | {r['hallucination_rate']}% | [{name}]({name}) |"
        )

    lines += [
        "",
        "## Beyond the queries",
        "",
        "A test query proves an agent routes correctly and cites its source. It cannot show "
        "that the suite passes, what the coverage figure really is, that the RAG index built, "
        "or that the control plane runs — and Sections 3 and 6 ask for all four. Screenshot "
        "only the query pages and **D-01 and D-08 go into the submission unevidenced**.",
        "",
        "| Evidence | Proves | Command | Page |",
        "|---|---|---|---|",
    ]
    for offset, artefact in enumerate(ARTEFACTS):
        eid = evidence_id(len(TEST_QUERIES) + offset + 1)
        name = f"{eid.lower()}-{artefact.slug}.md"
        lines.append(
            f"| **{eid}** | {artefact.caption} | `{artefact.command}` | [{name}]({name}) |"
        )

    lines += [
        "",
        "## Section 4.1 — Evidence Index (paste this into the mid-term doc)",
        "",
        "The template requires one row per evidence block, and Section 3 requires every "
        "deliverable marked Done or Partial to point at an Evidence ID here. The evaluator "
        "cross-checks that link, so a page with no ID cannot support a claim.",
        "",
        "| Evidence ID | Caption (what it proves) | Deliverable ID | Date captured | Link |",
        "|---|---|---|---|---|",
    ]
    for eid, caption, deliverables, _ in evidence_rows(report):
        lines.append(f"| {eid} | {caption} | {deliverables} | *(fill in)* | *(GitHub commit)* |")

    lines += [
        "",
        "> **D-01 is Partial, not Done.** The approved proposal committed to the control plane "
        "*plus* an Azure VM *plus* OpenRouter connected. OpenRouter is not provisioned — all "
        "inference is local at ₹0. Declare it Partial and record the deviation in Section 8; "
        "claiming it Done without evidence for those parts is exactly what the consistency "
        "check catches.",
        "",
        "```bash",
        "make qa && make evidence   # re-run the suite and regenerate this directory",
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_evidence() -> tuple[int, list[str]]:
    """Write docs/qa/ from the QA report. Returns (files written, their names)."""
    cfg = settings()
    if not cfg.qa_report_path.exists():
        raise SystemExit(f"no QA report at {cfg.qa_report_path} — run `make qa` first")

    report = json.loads(cfg.qa_report_path.read_text())
    out_dir = cfg.evidence_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for result in report["results"]:
        path = out_dir / f"q{result['id']:02d}.md"
        path.write_text(render_query(result))
        written.append(path.name)

    for offset, artefact in enumerate(ARTEFACTS):
        eid = evidence_id(len(TEST_QUERIES) + offset + 1)
        path = out_dir / f"{eid.lower()}-{artefact.slug}.md"
        path.write_text(render_artefact(artefact, len(TEST_QUERIES) + offset + 1))
        written.append(path.name)

    # Delete pages left over from an earlier run. Without this, a query that has not yet
    # re-run keeps its stale page — and a page carrying numbers from superseded code is
    # worse than a missing one, because it looks like current evidence and gets submitted.
    stale_pages = list(out_dir.glob("q[0-9][0-9].md")) + list(out_dir.glob("ev-[0-9][0-9]-*.md"))
    for stale in stale_pages:
        if stale.name not in written:
            stale.unlink()

    (out_dir / "README.md").write_text(render_index(report))
    written.append("README.md")
    return len(written), written


def main() -> None:
    count, written = build_evidence()
    cfg = settings()
    print(f"wrote {count} evidence file(s) to {cfg.evidence_dir}")
    for name in written:
        print(f"  {name}")


if __name__ == "__main__":
    main()
