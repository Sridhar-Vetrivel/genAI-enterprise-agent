"""Is the fleet actually usable?

    python -m agents.health      (or: make agents-status)

A node is only usable if BOTH halves hold, and each half has failed on its own here:

* **Serving** -- something is listening on the node's port. `make agents` backgrounds five
  nodes and returns immediately, so a node that dies on startup is otherwise invisible. Four
  of five once sat dead behind a control plane that cheerfully listed all five, because
  AgentField registers *before* it binds the socket.

* **Routable** -- the control plane still lists the node. `data-agent` was evicted from the
  registry after an 82-second inference (its heartbeat stopped and never resumed) while its
  process stayed alive and its port kept answering. Port-only health called it "up"; the
  control plane would not route a single call to it.

Checking one half and trusting the other is how both bugs hid. This checks both.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

import httpx

from psiog_kendra.config import settings


@dataclass(frozen=True)
class NodeHealth:
    """What the two independent checks say about one node."""

    node_id: str
    port: int
    serving: bool  # something is listening on the port
    routable: bool  # the control plane will route to it

    @property
    def ok(self) -> bool:
        return self.serving and self.routable

    @property
    def status(self) -> str:
        if self.ok:
            return "up"
        if self.serving and not self.routable:
            # The dangerous one: looks alive from the outside, gets no traffic.
            return "UNREGISTERED"
        if self.routable and not self.serving:
            # The other dangerous one: listed by the control plane, but dead.
            return "DEAD"
        return "DOWN"


async def _serving(host: str, port: int, timeout: float) -> bool:
    """True if something accepts a TCP connection on the port."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, TimeoutError):
        return False
    writer.close()
    return True


async def _registered(timeout: float) -> set[str]:
    """The node ids the control plane will actually route to.

    Asks the discovery endpoint, not `/api/v1/nodes`. `/nodes` lists only nodes whose
    health_status is "active", and a node that registered while its port was still binding
    is stuck at "unknown" -- while the control plane routes to it quite happily. Judging by
    /nodes marked four working agents as broken.

    An unreachable control plane returns an empty set, so every node reads UNREGISTERED --
    which is the truth: nothing can be routed anywhere.
    """
    cfg = settings()
    url = f"{cfg.agentfield_server.rstrip('/')}{cfg.agentfield_discovery_path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            found = resp.json().get("capabilities") or []
    except (httpx.HTTPError, ValueError):
        return set()
    return {c["agent_id"] for c in found if "agent_id" in c}


async def check(host: str = "127.0.0.1", timeout: float = 5.0) -> list[NodeHealth]:
    """Both halves, for every node, concurrently."""
    ports = settings().node_to_port
    serving, registered = await asyncio.gather(
        asyncio.gather(*(_serving(host, p, timeout) for p in ports.values())),
        _registered(timeout),
    )
    return [
        NodeHealth(node_id=node, port=port, serving=is_serving, routable=node in registered)
        for (node, port), is_serving in zip(ports.items(), serving, strict=True)
    ]


_REMEDY = {
    "UNREGISTERED": (
        "serving, but the control plane will not route to it. Its heartbeat stopped (this "
        "has happened after a long inference) or the control plane restarted under it. "
        "Restart the node, and check `make up` is running."
    ),
    "DEAD": (
        "listed by the control plane but nothing is on its port -- it registered and then "
        "died. Check data/agents/*.log."
    ),
    "DOWN": "not running at all. Start it with `make agents`; check data/agents/*.log.",
}


def main() -> int:
    fleet = asyncio.run(check())
    for node in sorted(fleet, key=lambda n: n.node_id):
        print(f"  [{node.status:^12}] {node.node_id:<14} :{node.port}")

    broken = [n for n in fleet if not n.ok]
    if broken:
        print(f"\n{len(broken)} of {len(fleet)} nodes are not usable:", file=sys.stderr)
        for node in sorted(broken, key=lambda n: n.node_id):
            print(f"  {node.node_id}: {_REMEDY[node.status]}", file=sys.stderr)
        return 1

    print(f"\nall {len(fleet)} nodes serving and routable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
