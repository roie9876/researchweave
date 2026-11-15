"""Domain models for ResearchWeave investigations, dynamic agents, and the Company Brain."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


class InvestigationStatus(str, Enum):
    CLARIFYING = "clarifying"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AutonomyMode(str, Enum):
    AUTONOMOUS = "autonomous"
    APPROVAL_REQUIRED = "approval_required"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class VerificationState(str, Enum):
    HYPOTHESIS = "hypothesis"
    OBSERVED = "observed"
    CALCULATED = "calculated"
    REVIEWED_VERIFIED = "reviewed_verified"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class StoppingConditions(BaseModel):
    max_runtime_hours: float | None = Field(
        default=None,
        description="Optional maximum runtime in hours (None = unlimited by default).",
    )
    max_budget_usd: float | None = Field(
        default=None,
        description="Optional best-effort spending cap in USD (None = unlimited by default).",
    )
    stop_on_sufficient_evidence: bool = True
    max_consecutive_failures: int = 5


class ApprovalPolicy(BaseModel):
    require_code_execution_approval: bool = False
    require_compute_provisioning_approval: bool = False
    require_package_install_approval: bool = False
    require_external_write_approval: bool = True


class ObjectiveRevision(BaseModel):
    revision: int
    objective: str
    reason: str
    updated_by: str
    created_at: str = Field(default_factory=utc_now_iso)


class SpecialistAgent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent"))
    investigation_id: str
    name: str
    role_title: str
    description: str
    system_prompt: str
    assigned_model: str
    status: str = "idle"
    created_by: str = "lead-researcher"
    inherited_permissions: list[str] = Field(
        default_factory=lambda: ["public_search", "brain_read", "isolated_sandbox"]
    )
    created_at: str = Field(default_factory=utc_now_iso)


class ResearchTask(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    investigation_id: str
    title: str
    description: str
    kind: str = Field(
        default="literature_analysis",
        description="Task type: literature_analysis, computation, hypothesis_test, independent_review, synthesis",
    )
    assigned_agent_id: str | None = None
    assigned_agent_name: str | None = None
    assigned_model: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)
    result_summary: str | None = None
    code_executed: str | None = None
    code_output: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class SourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("src"))
    investigation_id: str
    title: str
    source_type: str = Field(
        description="uploaded_file, public_url, scientific_paper, dataset, calculation_artifact"
    )
    uri_or_path: str
    blob_container: str | None = None
    blob_name: str | None = None
    content_hash: str
    excerpt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    deleted: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class BrainEntity(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ent"))
    investigation_id: str
    canonical_name: str
    entity_type: str = Field(
        description="concept, material, gene, compound, theorem, method, condition, dataset"
    )
    summary: str = ""
    aliases: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class BrainRelation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rel"))
    investigation_id: str
    source_entity_id: str
    source_entity_name: str
    predicate: str
    target_entity_id: str
    target_entity_name: str
    confidence: float = 0.75
    conditions: str = ""
    verification_state: VerificationState = VerificationState.HYPOTHESIS
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    valid_from: str = Field(default_factory=utc_now_iso)
    invalidated_at: str | None = None


class ClaimRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("clm"))
    investigation_id: str
    statement: str
    category: str = Field(
        default="finding",
        description="hypothesis, observation, calculation, reviewed_finding, limitation",
    )
    verification_state: VerificationState = VerificationState.HYPOTHESIS
    confidence: float = 0.7
    conditions: str = ""
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    reviewer_notes: str | None = None
    checked_by_agent: str | None = None
    objective_revision: int = 1
    created_at: str = Field(default_factory=utc_now_iso)


class ConversationMessage(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    investigation_id: str
    sender: str
    role: str = Field(description="researcher, lead_agent, specialist_agent, reviewer_agent, system")
    content: str
    status: str = Field(
        default="applied",
        description="received, processed, applied, answered_without_goal_change",
    )
    effect_summary: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class TimelineEvent(BaseModel):
    id: int = 0
    investigation_id: str
    event_type: str
    actor: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class CreateInvestigationRequest(BaseModel):
    title: str
    objective: str
    owner: str = "researcher@researchweave.local"
    language: str = "en"
    report_language: str = "en"
    autonomy_mode: AutonomyMode = AutonomyMode.AUTONOMOUS
    approval_policy: ApprovalPolicy = Field(default_factory=ApprovalPolicy)
    stopping_conditions: StoppingConditions = Field(default_factory=StoppingConditions)
    model_pool: list[str] = Field(
        default_factory=lambda: ["gpt-5.4-pro", "gpt-4.1", "o3-deep-research"]
    )
    reference_links: list[str] = Field(default_factory=list)
    reused_investigation_ids: list[str] = Field(default_factory=list)
    collaborators: list[str] = Field(default_factory=list)


class ClarifyConfirmRequest(BaseModel):
    clarification_answers: str = ""
    confirmed_objective: str | None = None
    autonomy_mode: AutonomyMode | None = None
    model_pool: list[str] | None = None
    stopping_conditions: StoppingConditions | None = None


class SteeringMessageRequest(BaseModel):
    sender: str = "researcher@researchweave.local"
    message: str
    update_objective: str | None = None
    new_reference_links: list[str] = Field(default_factory=list)


class UpdateSettingsRequest(BaseModel):
    model_pool: list[str] | None = None
    autonomy_mode: AutonomyMode | None = None
    stopping_conditions: StoppingConditions | None = None
    approval_policy: ApprovalPolicy | None = None
    report_language: str | None = None


class UploadFileRequest(BaseModel):
    filename: str
    content_text: str
    content_type: str = "text/plain"
    uploaded_by: str = "researcher@researchweave.local"
