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


def _port(node_id: str) -> int:
    """The port this node owns.

    `Agent.run()` defaults every node to 8001. `make agents` starts all five on one host,
    so the first to bind won and the other four exited on "address already in use" -- but
    only *after* registering, leaving the control plane listing five nodes of which four
    were dead. The port is derived from the node id, so a node cannot be handed someone
    else's port by a copy-paste, and an unmapped node refuses to start rather than
    silently squatting on 8001.
    """
    ports = settings().node_to_port
    if node_id not in ports:
        raise SystemExit(
            f"no port configured for node '{node_id}'. "
            f"Add one to Settings.node_to_port and deploy/.env.example. "
            f"Known nodes: {', '.join(sorted(ports))}"
        )
    return ports[node_id]


def make_agent(node_id: str, description: str, tags: list[str]) -> Agent:
    """Build an AgentField node wired to the local model and control plane."""
    cfg = settings()
    _port(node_id)  # fail at import, not eight seconds later at serve time
    return Agent(
        node_id=node_id,
        agentfield_server=cfg.agentfield_server,
        description=description,
        tags=tags,
        # Where the control plane dials this node back. It must NOT be localhost: the
        # control plane runs in Docker, so localhost is the container, and the call dies
        # on "connection refused" against the container's own empty port.
        callback_url=cfg.callback_url(node_id),
        # The model AgentField would use for its own `app.ai()` calls. Pointed at the
        # local Ollama server: OpenRouter is not provisioned, so nothing leaves the host.
        ai_config=AIConfig(
            model=f"ollama/{cfg.model_complex}",
            api_base=cfg.ollama_host,
            temperature=cfg.llm_temperature,
        ),
    )


def serve(app: Agent) -> None:
    """Run a node on the same port it registered its callback URL against."""
    app.run(port=_port(app.node_id))
