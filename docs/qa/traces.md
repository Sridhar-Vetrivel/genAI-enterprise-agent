# Control-Plane Traces — one execution per test query

Each of the 12 test queries was run through `coordinator.ask` on the AgentField
control plane. The coordinator classifies intent with the LLM, dispatches to the
specialist agents with `app.call()` (recorded as a DAG), and synthesises one cited
answer — so a single trace evidences routing, the multi-agent architecture, and
grounding together.

Open **<http://localhost:8080/ui/>** and find the execution by its ID.

Traced: **0 of 12 succeeded**.

## 📸 How to take the screenshot

1. Open <http://localhost:8080/ui/> and select the execution ID for the query you want.
2. Stay on the **Inputs & Outputs** tab: the input query on the left, the
   `answer` / `citations` / `confidence` on the right. The citation is the proof
   the answer is grounded — make sure it is readable.
3. Capture the **whole browser window**, including the reasoner name, the
   `data-agent`/`coordinator` node badge, the green **Succeeded** status and the
   duration. Full-size, no crop, no collage.
4. For the cross-domain queries (Q9–Q12) also capture the **Debug**/DAG view: it
   shows the coordinator calling more than one specialist, which is the single
   clearest picture of the multi-agent design.

## Executions

| Q | Query | Routed to | Status | Time | Execution ID |
|---|---|---|---|---|---|
| Q01 | Did yesterday's ETL pipeline for the sales data run successfully? | `—` | ❌ unknown | 90.5s | `—` |

## Answers as traced

### Q01 — Did yesterday's ETL pipeline for the sales data run successfully?

> **unknown** — execution timeout after 1m30s

