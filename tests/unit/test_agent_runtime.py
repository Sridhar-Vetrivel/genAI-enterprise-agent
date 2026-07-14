"""Every node must serve on a port of its own.

The bug these guard: AgentField's `Agent.run()` defaults every node to port 8001. `make
agents` starts all five on one host, so the first to bind won and the other four exited
with "address already in use" -- but only *after* they had registered with the control
plane. The control plane listed five healthy nodes; four of them were dead, and any
`app.call()` routed to one of them hung. A collision must fail a test, not a demo.
"""

from __future__ import annotations

import pytest

from agents._runtime import serve
from psiog_kendra.config import reset_settings, settings


class TestNodePorts:
    def test_no_two_nodes_share_a_port(self) -> None:
        ports = settings().node_to_port
        assert len(set(ports.values())) == len(ports), (
            f"two nodes share a port -- the loser dies on bind: {ports}"
        )

    def test_every_started_node_has_a_port(self) -> None:
        # The five nodes `make agents` starts. The judge is not served; it is called
        # in-process by the QA harness.
        cfg = settings()
        started = {
            cfg.node_coordinator,
            cfg.node_data,
            cfg.node_devops,
            cfg.node_crm,
            cfg.node_docs,
        }
        assert started <= set(cfg.node_to_port)

    def test_ports_are_env_overridable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT_DATA_AGENT", "9002")
        reset_settings()
        try:
            assert settings().node_to_port[settings().node_data] == 9002
        finally:
            reset_settings()

    def test_renaming_a_node_keeps_its_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The map is keyed by node id, so a renamed node must not lose its port and fall
        # back to someone else's.
        monkeypatch.setenv("NODE_DATA_AGENT", "databricks-agent")
        reset_settings()
        try:
            ports = settings().node_to_port
            assert ports["databricks-agent"] == settings().port_data
            assert len(set(ports.values())) == len(ports)
        finally:
            reset_settings()


class TestCallbackUrl:
    """The other half of the same bug. A node registers the URL the control plane will
    dial to reach it. The control plane runs in Docker, so `localhost` there is the
    *container* -- a node registering http://localhost:8002 points every call at the
    container's own empty port and the call dies on "connection refused"."""

    def test_the_callback_is_not_localhost(self) -> None:
        cfg = settings()
        url = cfg.callback_url(cfg.node_data)
        assert "localhost" not in url and "127.0.0.1" not in url, (
            f"the containerised control plane cannot reach the node at {url}"
        )

    def test_the_callback_port_is_the_port_the_node_serves_on(self) -> None:
        # If these two drift apart, the node is up and the control plane still cannot
        # reach it -- the hardest version of this bug to see.
        cfg = settings()
        for node, port in cfg.node_to_port.items():
            assert cfg.callback_url(node).endswith(f":{port}")

    def test_the_callback_host_is_env_overridable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A control plane running outside Docker needs plain localhost.
        monkeypatch.setenv("AGENT_CALLBACK_HOST", "localhost")
        reset_settings()
        try:
            cfg = settings()
            assert cfg.callback_url(cfg.node_crm) == f"http://localhost:{cfg.port_crm}"
        finally:
            reset_settings()


class _FakeAgent:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.served_on: int | None = None

    def run(self, **kwargs: object) -> None:
        self.served_on = kwargs["port"]  # type: ignore[assignment]


class TestServe:
    def test_serves_the_node_on_its_configured_port(self) -> None:
        app = _FakeAgent(settings().node_docs)
        serve(app)  # type: ignore[arg-type]
        assert app.served_on == settings().port_docs

    def test_an_unknown_node_fails_loudly_rather_than_defaulting(self) -> None:
        # Defaulting an unmapped node to 8001 is what caused the collision. A node with no
        # port must refuse to start, not quietly squat on the coordinator's socket.
        app = _FakeAgent("mystery-agent")
        with pytest.raises(SystemExit, match="no port configured"):
            serve(app)  # type: ignore[arg-type]
        assert app.served_on is None
