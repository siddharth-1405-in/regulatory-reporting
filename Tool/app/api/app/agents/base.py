"""Shared agent layer — governed run-record contract + Claude/stub client.

Every agent run is recorded with the mandatory governance fields (evidence_used,
reasoning_summary, confidence, impacted_metrics, proposed_action,
approval_required, prompt_version, model_version). Agents are advisory: they
write only AgentRun / RemediationProposal / Narrative rows and never mutate
calculation inputs or runs. A live Anthropic Claude call is used when an API key
is configured; otherwise a deterministic, fully-grounded fallback is used so the
platform always runs.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import AgentRun


@dataclass
class AgentResult:
    agent_type: str
    reasoning_summary: str = ""
    confidence: float = 0.0
    evidence_used: list = field(default_factory=list)
    impacted_metrics: list = field(default_factory=list)
    proposed_action: str = ""
    approval_required: bool = True
    prompt_version: str = "v1"
    model_version: str = "deterministic-stub"
    output: dict = field(default_factory=dict)

    def to_run(self, instance_id: int) -> AgentRun:
        return AgentRun(
            instance_id=instance_id, agent_type=self.agent_type,
            evidence_used=self.evidence_used, reasoning_summary=self.reasoning_summary,
            confidence=self.confidence, impacted_metrics=self.impacted_metrics,
            proposed_action=self.proposed_action, approval_required=self.approval_required,
            prompt_version=self.prompt_version, model_version=self.model_version,
            status="proposed", output=self.output,
        )


def persist(db: Session, instance_id: int, result: AgentResult) -> AgentRun:
    run = result.to_run(instance_id)
    db.add(run)
    db.flush()
    return run


def call_claude_json(system: str, user: str, *, narrative: bool = False) -> tuple[dict | None, str]:
    """Call Claude expecting a JSON object. Returns (parsed_json | None, model_version).

    Returns (None, 'deterministic-stub') when no API key is configured or the
    call fails, signalling the caller to use its deterministic fallback.
    """
    if not settings.ai_enabled:
        return None, "deterministic-stub"
    model = settings.claude_model_narrative if narrative else settings.claude_model_reasoning
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model=model, max_tokens=1500, system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        start, end = text.find("{"), text.rfind("}")
        parsed = json.loads(text[start:end + 1]) if start >= 0 else None
        return parsed, model
    except Exception:
        return None, "deterministic-stub"
