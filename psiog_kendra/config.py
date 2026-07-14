"""Environment-driven configuration. The single source of truth for every setting.

Nothing in this codebase hardcodes a URL, endpoint path, model name, agent node id,
file path, limit or threshold. It all lands here, is read from the environment, and is
documented in deploy/.env.example. Copy that file to .env (gitignored) to override.

OpenRouter is not provisioned, so every LLM call goes to the local Ollama server at zero
cost. Switching to OpenRouter later is an env change, not a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]


def _env(key: str, default: str) -> str:
    return os.getenv(key, default).strip()


def _int(key: str, default: int) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


def _flag(key: str, default: bool) -> bool:
    return _env(key, "true" if default else "false").lower() in {"1", "true", "yes", "on"}


def _path(key: str, default: str) -> Path:
    """Resolve a path setting; relative values are anchored at the repo root."""
    raw = Path(_env(key, default))
    return raw if raw.is_absolute() else ROOT / raw


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Read via `settings()`."""

    # ---------------- LLM: local Ollama, zero cost ----------------
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    ollama_chat_path: str = field(default_factory=lambda: _env("OLLAMA_CHAT_PATH", "/api/chat"))
    ollama_embed_path: str = field(default_factory=lambda: _env("OLLAMA_EMBED_PATH", "/api/embed"))
    # Hard cases: routing, cross-domain synthesis, grounding judgement.
    model_complex: str = field(default_factory=lambda: _env("AI_MODEL_COMPLEX", "gemma3:4b"))
    # Simple cases: phrasing a single already-retrieved record.
    model_simple: str = field(default_factory=lambda: _env("AI_MODEL_SIMPLE", "gemma3:1b"))
    embed_model: str = field(default_factory=lambda: _env("AI_EMBED_MODEL", "nomic-embed-text"))
    llm_temperature: float = field(default_factory=lambda: _float("AI_TEMPERATURE", 0.0))
    llm_timeout: float = field(default_factory=lambda: _float("AI_TIMEOUT_SECONDS", 180.0))
    llm_retries: int = field(default_factory=lambda: _int("AI_RETRIES", 2))
    # Context window. Smaller = less KV cache = less RAM to load the model.
    llm_num_ctx: int = field(default_factory=lambda: _int("AI_NUM_CTX", 4096))
    # If the complex model will not fit in host RAM, degrade to the simple model rather
    # than failing the query. The downgrade is logged, never silent.
    fallback_on_oom: bool = field(default_factory=lambda: _flag("AI_FALLBACK_ON_OOM", True))

    # ---------------- AgentField control plane ----------------
    agentfield_server: str = field(
        default_factory=lambda: _env("AGENTFIELD_SERVER", "http://localhost:8080")
    )
    agentfield_execute_path: str = field(
        default_factory=lambda: _env("AGENTFIELD_EXECUTE_PATH", "/api/v1/execute")
    )

    # ---------------- Agent node ids ----------------
    node_coordinator: str = field(default_factory=lambda: _env("NODE_COORDINATOR", "coordinator"))
    node_data: str = field(default_factory=lambda: _env("NODE_DATA_AGENT", "data-agent"))
    node_devops: str = field(default_factory=lambda: _env("NODE_DEVOPS_AGENT", "devops-agent"))
    node_crm: str = field(default_factory=lambda: _env("NODE_CRM_AGENT", "crm-agent"))
    node_docs: str = field(default_factory=lambda: _env("NODE_DOCS_AGENT", "docs-agent"))
    node_judge: str = field(default_factory=lambda: _env("NODE_JUDGE_AGENT", "judge-agent"))

    # ---------------- Agent node ports ----------------
    # Each node serves its own FastAPI app, and AgentField defaults every one of them to
    # 8001. Started together on one host, the first node wins the socket and the other
    # four die on "address already in use" -- *after* they have registered with the
    # control plane. The fleet then looks healthy (5 nodes listed) while 4 of them are
    # dead, and every `app.call()` to them hangs. One port per node, explicitly.
    port_coordinator: int = field(default_factory=lambda: _int("PORT_COORDINATOR", 8001))
    port_data: int = field(default_factory=lambda: _int("PORT_DATA_AGENT", 8002))
    port_devops: int = field(default_factory=lambda: _int("PORT_DEVOPS_AGENT", 8003))
    port_crm: int = field(default_factory=lambda: _int("PORT_CRM_AGENT", 8004))
    port_docs: int = field(default_factory=lambda: _int("PORT_DOCS_AGENT", 8005))

    # The host the CONTROL PLANE uses to call a node back. The nodes run on the host; the
    # control plane runs in Docker, where "localhost" is the container itself -- so a node
    # that registers `http://localhost:8002` tells the control plane to dial its own empty
    # port, and every call dies on "connection refused". Set to `localhost` when the
    # control plane is not containerised.
    agent_callback_host: str = field(
        default_factory=lambda: _env("AGENT_CALLBACK_HOST", "host.docker.internal")
    )

    # ---------------- Data sources ----------------
    # No Databricks/GitHub/CRM tenant is provisioned, so the specialists read realistic
    # synthetic fixtures. Set USE_MOCK_SOURCES=false and supply credentials to go live.
    use_mock_sources: bool = field(default_factory=lambda: _flag("USE_MOCK_SOURCES", True))

    databricks_host: str = field(default_factory=lambda: _env("DATABRICKS_HOST", ""))
    databricks_token: str = field(default_factory=lambda: _env("DATABRICKS_TOKEN", ""))
    databricks_runs_path: str = field(
        default_factory=lambda: _env("DATABRICKS_RUNS_PATH", "/api/2.1/jobs/runs/list")
    )
    databricks_page_size: int = field(default_factory=lambda: _int("DATABRICKS_PAGE_SIZE", 25))

    github_api: str = field(default_factory=lambda: _env("GITHUB_API", "https://api.github.com"))
    github_repo: str = field(default_factory=lambda: _env("GITHUB_REPO", "psiog/platform"))
    github_token: str = field(default_factory=lambda: _env("GITHUB_TOKEN", ""))
    github_runs_path: str = field(
        default_factory=lambda: _env("GITHUB_RUNS_PATH", "/repos/{repo}/actions/runs")
    )
    github_page_size: int = field(default_factory=lambda: _int("GITHUB_PAGE_SIZE", 25))

    crm_api_base: str = field(default_factory=lambda: _env("CRM_API_BASE", ""))
    crm_api_key: str = field(default_factory=lambda: _env("CRM_API_KEY", ""))

    source_timeout: float = field(default_factory=lambda: _float("SOURCE_TIMEOUT_SECONDS", 30.0))
    # How many source records a specialist puts in front of the LLM.
    max_records_in_prompt: int = field(default_factory=lambda: _int("MAX_RECORDS_IN_PROMPT", 5))

    # ---------------- RAG ----------------
    rag_top_k: int = field(default_factory=lambda: _int("RAG_TOP_K", 5))
    rag_chunk_chars: int = field(default_factory=lambda: _int("RAG_CHUNK_CHARS", 900))
    rag_chunk_overlap: int = field(default_factory=lambda: _int("RAG_CHUNK_OVERLAP", 150))
    rag_min_score: float = field(default_factory=lambda: _float("RAG_MIN_SCORE", 0.25))

    # ---------------- QA ----------------
    target_routing_accuracy: float = field(
        default_factory=lambda: _float("QA_TARGET_ROUTING_ACCURACY", 100.0)
    )
    target_hallucination_rate: float = field(
        default_factory=lambda: _float("QA_TARGET_HALLUCINATION_RATE", 10.0)
    )
    # The single biggest cost driver in a QA run — the judge re-reads raw sources per answer.
    judge_source_char_limit: int = field(
        default_factory=lambda: _int("QA_JUDGE_SOURCE_CHAR_LIMIT", 5000)
    )
    # How much of a "claim" must overlap the answer's own words before we accept that the
    # answer really made it. The judge tends to enumerate source fields the answer never
    # mentioned ("The actor is priya.n"), which pad the denominator with free passes and
    # flatter the hallucination rate. Raise it to be stricter about what counts as a claim.
    judge_claim_overlap: float = field(
        default_factory=lambda: _float("QA_JUDGE_CLAIM_OVERLAP", 0.5)
    )
    # Hard stop per query. A cross-domain query is 5-7 sequential LLM calls and on local CPU
    # inference it can run 15 minutes or more; a stalled one would otherwise hang the suite
    # indefinitely. On timeout the query is RECORDED as timed out, never silently skipped —
    # a missing result and a failed result must not look the same. 0 disables the limit.
    query_timeout_seconds: float = field(
        default_factory=lambda: _float("QA_QUERY_TIMEOUT_SECONDS", 900.0)
    )

    # ---------------- Paths ----------------
    docs_dir: Path = field(default_factory=lambda: _path("DOCS_DIR", "data/docs"))
    mock_dir: Path = field(default_factory=lambda: _path("MOCK_DIR", "data/mock"))
    index_path: Path = field(default_factory=lambda: _path("INDEX_PATH", "data/index/vectors.json"))
    qa_report_path: Path = field(
        default_factory=lambda: _path("QA_REPORT_PATH", "data/qa_report.json")
    )
    # Per-query evidence pages for the mid-term Evidence Pack (`make evidence`).
    evidence_dir: Path = field(default_factory=lambda: _path("EVIDENCE_DIR", "docs/qa"))

    @property
    def databricks_runs_url(self) -> str:
        return f"{self.databricks_host.rstrip('/')}{self.databricks_runs_path}"

    @property
    def github_runs_url(self) -> str:
        path = self.github_runs_path.format(repo=self.github_repo)
        return f"{self.github_api.rstrip('/')}{path}"

    @property
    def domain_to_agent(self) -> dict[str, str]:
        """Domain label -> specialist node id. Both sides are env-configurable."""
        from psiog_kendra.domains import CRM, DATA_PLATFORM, DEVOPS, DOCS

        return {
            DATA_PLATFORM: self.node_data,
            DEVOPS: self.node_devops,
            CRM: self.node_crm,
            DOCS: self.node_docs,
        }

    @property
    def node_to_port(self) -> dict[str, int]:
        """Node id -> the port that node serves on. Both sides are env-configurable."""
        return {
            self.node_coordinator: self.port_coordinator,
            self.node_data: self.port_data,
            self.node_devops: self.port_devops,
            self.node_crm: self.port_crm,
            self.node_docs: self.port_docs,
        }

    def callback_url(self, node_id: str) -> str:
        """The URL the control plane should dial to reach this node."""
        return f"http://{self.agent_callback_host}:{self.node_to_port[node_id]}"


_cached: Settings | None = None


def settings() -> Settings:
    """Process-wide settings singleton."""
    global _cached
    if _cached is None:
        _cached = Settings()
    return _cached


def reset_settings() -> None:
    """Drop the cache so tests can re-read a patched environment."""
    global _cached
    _cached = None
