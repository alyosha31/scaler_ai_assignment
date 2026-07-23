from __future__ import annotations

from pydantic import BaseModel, Field

from ai_tutor.core.models import InstructorBrief, ScriptProject


class EvalExpectations(BaseModel):
    must_cover: list[str] = Field(default_factory=list)
    must_not_reteach: list[str] = Field(default_factory=list)
    expected_level: str
    min_model_score: float = 3.75


class EvalScenario(BaseModel):
    case_id: str
    category: str
    brief: InstructorBrief
    expectations: EvalExpectations


class LevelAdaptivityPair(BaseModel):
    pair_id: str
    beginner_case_id: str
    advanced_case_id: str


class GuardrailResult(BaseModel):
    name: str
    passed: bool
    detail: str
    red_line: str | None = None


class ScriptJudgeScores(BaseModel):
    coverage: float = Field(..., ge=1, le=5)
    faithfulness: float = Field(..., ge=1, le=5)
    level_fit: float = Field(..., ge=1, le=5)
    pedagogy: float = Field(..., ge=1, le=5)
    teachability: float = Field(..., ge=1, le=5)
    pacing: float = Field(..., ge=1, le=5)
    tone: float = Field(..., ge=1, le=5)
    code_quality: float = Field(..., ge=1, le=5)
    reviewability: float = Field(..., ge=1, le=5)

    @property
    def average(self) -> float:
        return (
            self.coverage
            + self.faithfulness
            + self.level_fit
            + self.pedagogy
            + self.teachability
            + self.pacing
            + self.tone
            + self.code_quality
            + self.reviewability
        ) / 9


class ScriptJudgeResult(BaseModel):
    scores: ScriptJudgeScores
    red_lines: list[str] = Field(default_factory=list)
    overall: float = Field(..., ge=1, le=5)
    rationale: str


class AdaptivityJudgeResult(BaseModel):
    meaningfully_different: bool
    vocabulary_difference: str
    pacing_difference: str
    assumed_knowledge_difference: str
    example_depth_difference: str
    code_complexity_difference: str
    checkpoint_difference: str
    too_similar_risk: str
    pass_: bool = Field(alias="pass")


class CaseEvalResult(BaseModel):
    case_id: str
    category: str
    project_id: str
    generation_status: str
    structural_passed: bool
    guardrails: list[GuardrailResult]
    judge: ScriptJudgeResult | None = None
    passed_gate: bool
    project_json_path: str
    script_markdown_path: str
    error: str | None = None


class PairEvalResult(BaseModel):
    pair_id: str
    beginner_case_id: str
    advanced_case_id: str
    judge: AdaptivityJudgeResult | None = None
    passed_gate: bool
    error: str | None = None


class EvalRunResult(BaseModel):
    model: str
    judge_enabled: bool
    prompt_hash: str
    scenario_count: int
    cases: list[CaseEvalResult]
    pairs: list[PairEvalResult]
    passed_gate: bool


class GeneratedCase(BaseModel):
    scenario: EvalScenario
    project: ScriptProject
    markdown: str
