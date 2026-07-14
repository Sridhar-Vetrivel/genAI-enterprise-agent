"""Is the fleet actually up?

    python -m agents.health

`make agents` backgrounds five nodes and returns immediately, so a node that dies on
startup is invisible: the shell prints no error and the control plane still lists the node,
because registration happens *before* the server binds its socket. That is exactly how four
of five nodes sat dead behind a healthy-looking fleet.

This asks each node's own port whether anything is listening, and exits non-zero if not.
"""

from __future__ import annotations

import asyncio
import sys

from psiog_kendra.config import settings


async def _listening(host: str, port: int, timeout: float) -> bool:
    """True if something accepts a TCP connection on the port."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, TimeoutError):
        return False
    writer.close()
    return True


async def check(host: str = "127.0.0.1", timeout: float = 2.0) -> dict[str, bool]:
    """Node id -> whether it is serving."""
    ports = settings().node_to_port
    alive = await asyncio.gather(*(_listening(host, p, timeout) for p in ports.values()))
    return dict(zip(ports, alive, strict=True))


def main() -> int:
    health = asyncio.run(check())
    ports = settings().node_to_port
    for node, up in sorted(health.items()):
        mark = "up  " if up else "DOWN"
        print(f"  [{mark}] {node:<14} :{ports[node]}")

    dead = [node for node, up in health.items() if not up]
    if dead:
        print(
            f"\n{len(dead)} of {len(health)} nodes are not serving: {', '.join(sorted(dead))}\n"
            f"Check data/agents/*.log. A node can register with the control plane and still "
            f"be dead -- registration happens before the socket is bound.",
            file=sys.stderr,
        )
        return 1

    print(f"\nall {len(health)} nodes serving")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
