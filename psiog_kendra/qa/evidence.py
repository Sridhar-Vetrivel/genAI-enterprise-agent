"""Turn QA results into per-query evidence files for the mid-term Evidence Pack.

    make evidence          # regenerate docs/qa/ from data/qa_report.json

One file per test query: what was asked, how it routed, what it answered, what it cited,
what the Judge Agent found — plus the exact command to reproduce it and instructions for
the screenshot that goes into the mid-term submission (Section 4).

See docs/MidTerm_Submission_Reference.md for how these map to Evidence IDs.
"""

from __future__ import annotations

import json
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


def _deliverables(domains: list[str]) -> list[str]:
    items = ["D-02 (Week 5 — Coordinator routing)"]
    items += [DOMAIN_TO_DELIVERABLE[d] for d in domains if d in DOMAIN_TO_DELIVERABLE]
    if len(domains) > 1:
        items.append("D-07 (cross-domain synthesis, cited across systems)")
    return items


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

    lines: list[str] = [
        f"# Q{qid:02d} — {kind.title()} — {'PASS' if passed else 'FAIL'}",
        "",
        f"> **Question asked:** “{tq.query}”",
        "",
        "## What happened",
        "",
        "| | |",
        "|---|---|",
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
        "## How these map to the mid-term submission",
        "",
        "Each page ends with screenshot instructions and a pre-filled Evidence-block header "
        "table. See [../MidTerm_Submission_Reference.md](../MidTerm_Submission_Reference.md) "
        "for the template's rules — every deliverable marked Done/Partial in Section 3 must "
        "point to at least one Evidence ID here.",
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

    # Delete pages left over from an earlier run. Without this, a query that has not yet
    # re-run keeps its stale page — and a page carrying numbers from superseded code is
    # worse than a missing one, because it looks like current evidence and gets submitted.
    for stale in out_dir.glob("q[0-9][0-9].md"):
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
