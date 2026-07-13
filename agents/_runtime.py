"""Shared AgentField runtime helpers.

The agents in this package are thin AgentField nodes. Every one of them delegates to the
framework-free logic in `psiog_kendra`, which is what keeps the domain logic unit-testable
without a running control plane.

AgentField owns what AgentField is for: node registration, `@app.skill()` /
`@app.reasoner()`, agent-to-agent calls through the control plane (traced as a DAG), and
the vector-memory fabric. The LLM transport is the local Ollama gateway, because
OpenRouter is not provisioned.
"""

from __future__ import annotations

from agentfield import Agent, AIConfig

from psiog_kendra.config import settings


def make_agent(node_id: str, description: str, tags: list[str]) -> Agent:
    """Build an AgentField node wired to the local model and control plane."""
    cfg = settings()
    return Agent(
        node_id=node_id,
        agentfield_server=cfg.agentfield_server,
        description=description,
        tags=tags,
        # The model AgentField would use for its own `app.ai()` calls. Pointed at the
        # local Ollama server: OpenRouter is not provisioned, so nothing leaves the host.
        ai_config=AIConfig(
            model=f"ollama/{cfg.model_complex}",
            api_base=cfg.ollama_host,
            temperature=cfg.llm_temperature,
        ),
    )
