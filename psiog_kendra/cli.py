"""Chat interface for the copilot.

kendra "Did yesterday's ETL pipeline run successfully?"    # one question
kendra                                                     # interactive session
"""

from __future__ import annotations

import asyncio
import sys

from psiog_kendra.app import build_copilot
from psiog_kendra.config import settings
from psiog_kendra.coordinator import Coordinator
from psiog_kendra.domains import agent_for
from psiog_kendra.schemas import CopilotResponse


def render(response: CopilotResponse) -> str:
    agents = ", ".join(agent_for(d) for d in response.domains_used) or "none"
    lines = [
        "",
        response.answer,
        "",
        f"  routed to : {agents}",
        f"  why       : {response.routing_reasoning}",
    ]
    if response.citations:
        lines.append("  sources   :")
        lines += [f"    - {c}" for c in response.citations]
    else:
        lines.append("  sources   : NONE (ungrounded - do not trust this answer)")
    lines.append("")
    return "\n".join(lines)


async def ask_once(copilot: Coordinator, query: str) -> None:
    print(render(await copilot.ask(query)))


async def interactive(copilot: Coordinator) -> None:
    cfg = settings()
    print("Psiog Kendra - enterprise copilot")
    print(f"models: {cfg.model_complex} (complex) / {cfg.model_simple} (simple)")
    print("ask a question, or Ctrl-C to quit.\n")
    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if query:
            await ask_once(copilot, query)


def main() -> None:
    copilot = build_copilot()
    query = " ".join(sys.argv[1:]).strip()
    if query:
        asyncio.run(ask_once(copilot, query))
    else:
        asyncio.run(interactive(copilot))


if __name__ == "__main__":
    main()
