from __future__ import annotations

from ai_tutor.core.models import ScriptProject
from ai_tutor.evals.types import AdaptivityJudgeResult, ScriptJudgeResult
from ai_tutor.services.claude import ClaudeClient


SCRIPT_JUDGE_SYSTEM = """You are an expert reviewer of live-class instructor scripts.
Evaluate whether a generated script is close to what a strong human instructor would write.

Score 1-5, where 1 is poor, 3 is acceptable, and 5 is excellent.

Red lines:
- R1_AGENDA_MISS: agenda item missing or only named without teaching substance
- R2_TIMING_INVALID: timing clearly does not fit requested duration
- R3_RATIO_INVALID: content/code split clearly violates the brief
- R6_PRIOR_TOPIC_RETAUGHT: prior topics are re-taught from scratch
- R7_NO_CHECKPOINTS: no meaningful checks/activities
- R8_BEGINNER_ADVANCED_NO_DIFFERENCE: level calibration is generic or absent
- R9_GENERIC_LLM_DUMP: script reads like generic AI prose, not a teachable instructor script
- R10_UNTEACHABLE_SCRIPT: instructor could not realistically teach from this

Return exactly one JSON object matching the requested schema."""


def script_judge_user(project: ScriptProject, expected_level: str) -> str:
    return f"""Evaluate this class script.

Expected level: {expected_level}

Brief:
{project.brief.model_dump_json(indent=2)}

Outline:
{project.outline.model_dump_json(indent=2) if project.outline else "{}"}

Segments:
{[segment.model_dump(mode="json") for segment in project.segments]}

Judge for:
- coverage
- faithfulness to duration/content-code/audience
- level fit
- pedagogical sequence
- teachability as instructor notes
- pacing
- non-generic instructor tone
- live-code quality where relevant
- reviewability and rationale
"""


ADAPTIVITY_SYSTEM = """You are evaluating level adaptivity between two generated scripts.
Both scripts have the same topic, agenda, duration, and content/code ratio.
Only the beginner/advanced split differs.

The pair passes only if the two outputs are meaningfully different in vocabulary, pacing,
assumed background, example depth, live-code complexity, and checkpoint style.

Return exactly one JSON object matching the requested schema."""


def adaptivity_user(beginner: ScriptProject, advanced: ScriptProject) -> str:
    return f"""Compare these two scripts.

Beginner-heavy script:
{beginner.model_dump_json(indent=2)}

Advanced-heavy script:
{advanced.model_dump_json(indent=2)}

Decide whether the differences are meaningful enough to prove level adaptivity.
"""


class EvalJudge:
    def __init__(self, claude: ClaudeClient) -> None:
        self.claude = claude

    def judge_script(self, project: ScriptProject, expected_level: str) -> ScriptJudgeResult:
        return self.claude.generate_model(
            SCRIPT_JUDGE_SYSTEM,
            script_judge_user(project, expected_level),
            ScriptJudgeResult,
            trace_name="offline_script_judge",
            trace_metadata={
                "project_id": project.id,
                "stage": "offline_script_judge",
                "expected_level": expected_level,
            },
        )

    def judge_adaptivity(
        self, beginner: ScriptProject, advanced: ScriptProject
    ) -> AdaptivityJudgeResult:
        return self.claude.generate_model(
            ADAPTIVITY_SYSTEM,
            adaptivity_user(beginner, advanced),
            AdaptivityJudgeResult,
            trace_name="offline_adaptivity_judge",
            trace_metadata={
                "project_id": beginner.id,
                "advanced_project_id": advanced.id,
                "stage": "offline_adaptivity_judge",
            },
        )
