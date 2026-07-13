"""Structured output contracts.

Every LLM call in Psiog Kendra returns one of these models. `extra="forbid"` keeps
the model honest and makes responses machine-verifiable for QA.

Domain lists are typed `list[str]` rather than a Literal/Enum on purpose: Ollama
0.23 returns HTTP 500 when a JSON schema contains `enum`, so the vocabulary is
enforced by validator instead of by schema. See psiog_kendra.domains.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from psiog_kendra.domains import normalize_domains

CONFIDENCE = ("high", "medium", "low")


class RoutingDecision(BaseModel):
    """The coordinator's intent classification for one query."""

    model_config = ConfigDict(extra="forbid")

    domains: list[str] = Field(default_factory=list)
    reasoning: str = ""
    is_cross_domain: bool = False

    @field_validator("domains", mode="before")
    @classmethod
    def _coerce_domains(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            return []
        return normalize_domains([str(x) for x in v])

    @field_validator("is_cross_domain", mode="before")
    @classmethod
    def _coerce_bool(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in {"true", "yes", "1"}
        return bool(v)

    def model_post_init(self, __context: object) -> None:
        # The model is allowed to disagree with itself here; the domain list wins.
        object.__setattr__(self, "is_cross_domain", len(self.domains) > 1)


class AgentResponse(BaseModel):
    """What every specialist agent returns. `citations` is what makes it grounded."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[str] = Field(default_factory=list)
    confidence: str = "medium"

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: object) -> str:
        val = str(v).strip().lower()
        return val if val in CONFIDENCE else "medium"

    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_citations(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]


class CopilotResponse(BaseModel):
    """The final answer the user sees, synthesised from one or more specialists."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[str] = Field(default_factory=list)
    domains_used: list[str] = Field(default_factory=list)
    routing_reasoning: str = ""

    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_citations(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [v]
        return list(v) if isinstance(v, list) else []


class SynthesisResult(BaseModel):
    """Intermediate shape for the coordinator's cross-domain synthesis LLM call."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[str] = Field(default_factory=list)


class JudgeVerdict(BaseModel):
    """The Judge Agent's grounding check for one answer.

    The judge must ENUMERATE the claims it found, not just count them. Asking a small
    model for an integer invites it to answer 0, which would score a substantive answer
    as 0% hallucination without checking anything. Listing the claims makes the work
    visible and the count a consequence of it. `is_measured` then distinguishes
    "genuinely no factual claims" from "the judge did not do its job".
    """

    model_config = ConfigDict(extra="forbid")

    grounded_claims: list[str] = Field(default_factory=list)
    ungrounded_claims: list[str] = Field(default_factory=list)

    @field_validator("grounded_claims", "ungrounded_claims", mode="before")
    @classmethod
    def _coerce_claims(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]

    @property
    def total_claims(self) -> int:
        return len(self.grounded_claims) + len(self.ungrounded_claims)

    @property
    def is_measured(self) -> bool:
        """False when the judge enumerated nothing — the answer is UNVERIFIED, not clean."""
        return self.total_claims > 0

    @property
    def hallucination_rate(self) -> float:
        """(ungrounded claims / total claims) x 100."""
        if self.total_claims == 0:
            return 0.0
        return round((len(self.ungrounded_claims) / self.total_claims) * 100, 2)
