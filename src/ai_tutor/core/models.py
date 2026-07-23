from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"


class GenerationStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    GENERATING_OUTLINE = "GENERATING_OUTLINE"
    GENERATING_SEGMENTS = "GENERATING_SEGMENTS"
    EVALUATING = "EVALUATING"
    REPAIRING = "REPAIRING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_REVISION = "NEEDS_REVISION"
    FAILED = "FAILED"


class DraftStatus(str, Enum):
    GENERATED = "GENERATED"
    EDITED = "EDITED"
    REGENERATED = "REGENERATED"
    APPROVED = "APPROVED"


class ActivityType(str, Enum):
    CHECKPOINT = "CHECKPOINT"
    QUICK_EXERCISE = "QUICK_EXERCISE"
    LIVE_CODE = "LIVE_CODE"
    DISCUSSION = "DISCUSSION"


class ReviewEventType(str, Enum):
    EDIT = "EDIT"
    REGENERATE_REQUESTED = "REGENERATE_REQUESTED"
    REGENERATED = "REGENERATED"
    APPROVED = "APPROVED"
    COMMENT = "COMMENT"


class InstructorBrief(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    agenda: list[str] = Field(..., min_length=1, max_length=20)
    beginner_percentage: int = Field(..., ge=0, le=100)
    advanced_percentage: int = Field(..., ge=0, le=100)
    duration_minutes: int = Field(..., ge=5, le=240)
    content_percentage: int = Field(..., ge=0, le=100)
    code_percentage: int = Field(..., ge=0, le=100)
    topics_already_covered: list[str] = Field(default_factory=list)

    @field_validator("agenda", "topics_already_covered")
    @classmethod
    def strip_items(cls, values: list[str]) -> list[str]:
        return [item.strip() for item in values if item.strip()]

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        return value.strip()


class ValidationWarning(BaseModel):
    code: str
    message: str
    suggested_resolution: str


class ValidationErrorDetail(BaseModel):
    code: str
    message: str


class BriefValidationResult(BaseModel):
    is_valid: bool
    warnings: list[ValidationWarning] = Field(default_factory=list)
    errors: list[ValidationErrorDetail] = Field(default_factory=list)
    normalized_brief: InstructorBrief | None = None


class SegmentOutline(BaseModel):
    id: str = Field(default_factory=lambda: new_id("seg_outline"))
    order: int
    agenda_item: str
    title: str
    duration_minutes: int = Field(..., ge=1)
    content_minutes: int = Field(..., ge=0)
    code_minutes: int = Field(..., ge=0)
    learning_objective: str
    concepts_introduced: list[str] = Field(default_factory=list)
    concepts_assumed: list[str] = Field(default_factory=list)
    concepts_reinforced: list[str] = Field(default_factory=list)
    teaching_strategy: str
    example_plan: str
    activity_plan: list[str] = Field(default_factory=list)
    transition_in: str
    transition_out: str
    rationale: str


class ClassOutline(BaseModel):
    id: str = Field(default_factory=lambda: new_id("outline"))
    topic: str
    total_duration_minutes: int
    audience_calibration: str
    target_content_minutes: int
    target_code_minutes: int
    segments: list[SegmentOutline]
    recap_plan: str
    next_steps_plan: str
    global_assumptions: list[str] = Field(default_factory=list)
    design_rationale: list[str] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)


class LiveCodeStep(BaseModel):
    order: int
    instruction: str
    code: str = ""
    explanation: str
    expected_output: str = ""


class WorkedExample(BaseModel):
    setup: str
    walkthrough: str
    takeaway: str


class ComprehensionCheck(BaseModel):
    question: str
    expected_answer: str
    instructor_guidance: str


class Activity(BaseModel):
    type: ActivityType
    prompt: str
    expected_response: str = ""
    facilitation_notes: str = ""


class SegmentDraft(BaseModel):
    id: str = Field(default_factory=lambda: new_id("seg_draft"))
    outline_id: str
    duration_minutes: int
    content_minutes: int
    code_minutes: int
    instructor_narration: str
    live_code_steps: list[LiveCodeStep] = Field(default_factory=list)
    worked_examples: list[WorkedExample] = Field(default_factory=list)
    checks: list[ComprehensionCheck] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    reviewer_rationale: str
    status: DraftStatus = DraftStatus.GENERATED
    version: int = 1


class StructuralEvalResult(BaseModel):
    all_agenda_items_present: bool
    timing_sums_correctly: bool
    content_code_ratio_within_tolerance: bool
    prior_topics_not_reteaught: bool
    segment_ids_stable: bool
    failures: list[str] = Field(default_factory=list)


class ModelJudgeResult(BaseModel):
    coverage_score: float = Field(..., ge=0, le=5)
    level_fit_score: float = Field(..., ge=0, le=5)
    pedagogy_score: float = Field(..., ge=0, le=5)
    tone_score: float = Field(..., ge=0, le=5)
    factuality_score: float = Field(..., ge=0, le=5)
    pacing_score: float = Field(..., ge=0, le=5)
    judge_rationale: str

    @property
    def average_score(self) -> float:
        return (
            self.coverage_score
            + self.level_fit_score
            + self.pedagogy_score
            + self.tone_score
            + self.factuality_score
            + self.pacing_score
        ) / 6


class GoldenComparisonPlan(BaseModel):
    comparison_method: str
    required_dataset: str
    blind_review_protocol: str
    notes: str


class EvaluationReport(BaseModel):
    id: str = Field(default_factory=lambda: new_id("eval"))
    project_id: str
    structural: StructuralEvalResult
    model_judge: ModelJudgeResult | None = None
    golden_comparison: GoldenComparisonPlan
    passed_gate: bool
    recommendations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class RepairIssue(BaseModel):
    scope: str = Field(..., description="'segment' or 'global'")
    segment_id: str | None = None
    severity: str = Field(..., description="'low', 'medium', or 'high'")
    issue: str
    repair_instruction: str


class RepairPlan(BaseModel):
    repairs: list[RepairIssue] = Field(default_factory=list)
    global_issues: list[RepairIssue] = Field(default_factory=list)
    rationale: str


class ReviewEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    project_id: str
    segment_id: str | None = None
    type: ReviewEventType
    instructor_feedback: str = ""
    before_text: str = ""
    after_text: str = ""
    version_before: int | None = None
    version_after: int | None = None
    created_at: datetime = Field(default_factory=utcnow)


class RegenerationRequest(BaseModel):
    id: str = Field(default_factory=lambda: new_id("regen"))
    project_id: str
    segment_id: str
    instruction: str = Field(..., min_length=3)
    reason: str = ""
    target_version: int


class SignOff(BaseModel):
    id: str = Field(default_factory=lambda: new_id("signoff"))
    project_id: str
    instructor_name: str = Field(..., min_length=1)
    approved: bool
    final_notes: str = ""
    approved_at: datetime = Field(default_factory=utcnow)


class ScriptProject(BaseModel):
    id: str = Field(default_factory=lambda: new_id("project"))
    brief: InstructorBrief
    validation: BriefValidationResult | None = None
    outline: ClassOutline | None = None
    segments: list[SegmentDraft] = Field(default_factory=list)
    latest_evaluation: EvaluationReport | None = None
    review_events: list[ReviewEvent] = Field(default_factory=list)
    sign_off: SignOff | None = None
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generation_status: GenerationStatus = GenerationStatus.CREATED
    generation_message: str = "Project created."
    generation_progress: int = Field(default=0, ge=0, le=100)
    generation_error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()


class SegmentEditRequest(BaseModel):
    instructor_feedback: str = ""
    instructor_narration: str = Field(..., min_length=1)


class SegmentRegenerateRequest(BaseModel):
    instruction: str = Field(..., min_length=3)
    reason: str = ""


class SignOffRequest(BaseModel):
    instructor_name: str = Field(..., min_length=1)
    approved: bool = True
    final_notes: str = ""


class ClaudeJsonRequest(BaseModel):
    system: str
    user: str
    schema_name: str


JsonDict = dict[str, Any]


class ClaudeError(RuntimeError):
    pass
