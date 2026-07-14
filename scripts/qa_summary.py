"""Print the graded QA report as a screenshot-ready summary. Read-only — grades nothing.

    python -m scripts.qa_summary     (or: make qa-summary)

This is EV-13. `make qa` produces the numbers over ~60 local LLM calls and writes them to
`data/qa_report.json`; this renders that file. Separating the two matters: the evidence
screenshot must never require an hour-long re-run, and re-running to take a screenshot would
produce *different* numbers from the ones already in the submission.
"""

from __future__ import annotations

import json
import sys

from psiog_kendra.config import settings
from psiog_kendra.qa.test_queries import TEST_QUERIES

BAR = "=" * 64


def main() -> int:
    path = settings().qa_report_path
    try:
        with open(path) as fh:
            report = json.load(fh)
    except (OSError, ValueError):
        print(f"no QA report at {path} -- run `make qa` first", file=sys.stderr)
        return 1

    summary = report["summary"]
    results = sorted(report["results"], key=lambda r: r["id"])

    print(BAR)
    print("  PSIOG KENDRA — QA REPORT")
    print(f"  {path}")
    print(BAR)
    for r in results:
        routing = "PASS" if r["routed_correctly"] else "FAIL"
        ungrounded = len(r["ungrounded_claims"])
        print(
            f"  Q{r['id']:02d}  routing {routing}  ->  {','.join(r['actual_domains']):<30}"
            f"  {len(r['citations'])} citation(s)   {ungrounded} ungrounded"
        )

    graded = summary["queries"]
    ungrounded = summary["total_claims"] - summary["grounded_claims"]
    rate = summary["hallucination_rate_pct"]
    routing_pct = summary["routing_accuracy_pct"]

    print("-" * 64)
    print(f"  Queries graded          : {graded} of {len(TEST_QUERIES)}")
    print(
        f"  Routing accuracy        : {routing_pct}%"
        f"{'  ✅ PASS' if routing_pct >= 100 else '  ❌'}   (target 100%)"
    )
    print(f"  Answers with citations  : {summary['answers_with_citations']}/{graded}")
    print(f"  Total claims            : {summary['total_claims']}")
    print(f"  Grounded claims         : {summary['grounded_claims']}")
    print(f"  Ungrounded claims       : {ungrounded}")
    print(
        f"  HALLUCINATION RATE      : {rate}%"
        f"{'  ✅ PASS' if rate < 10 else '  ❌ FAIL'}   (target <10%)"
    )
    print(f"    = ({ungrounded} ungrounded / {summary['total_claims']} claims) x 100")
    print(BAR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
