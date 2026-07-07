from __future__ import annotations

import json

from scaler_script_pipeline.core.models import ClassOutline, InstructorBrief, ScriptProject, SegmentOutline


def outline_system_prompt() -> str:
    return (
        "You are an expert Scaler class script planner. Create a structured teaching outline "
        "that obeys duration, audience split, content/code ratio, agenda coverage, and prior knowledge. "
        "Be concrete and pedagogically ordered. Do not write the full script yet."
    )


def outline_user_prompt(brief: InstructorBrief, warnings: list[str]) -> str:
    return (
        "Create a class outline for this instructor brief.\n\n"
        f"Brief JSON:\n{brief.model_dump_json(indent=2)}\n\n"
        f"Validation warnings:\n{json.dumps(warnings, indent=2)}\n\n"
        "Rules:\n"
        "- Create one segment per agenda item unless a warning requires an explicit combination rationale.\n"
        "- Segment durations must sum exactly to duration_minutes.\n"
        "- Segment content/code minutes should approximate the requested ratio.\n"
        "- Prior topics should be assumed or called back to, not re-taught.\n"
        "- Beginner-heavy classes should scaffold vocabulary and use more checks.\n"
        "- Advanced-heavy classes should move faster and include tradeoffs/deeper examples.\n"
    )


def segment_system_prompt() -> str:
    return (
        "You are a strong human instructor drafting a teachable live-class script segment. "
        "Write in a practical, instructor-ready voice. Respect the outline exactly."
    )


def segment_user_prompt(brief: InstructorBrief, outline: ClassOutline, segment: SegmentOutline) -> str:
    sibling_summaries = [
        {
            "order": item.order,
            "title": item.title,
            "concepts_introduced": item.concepts_introduced,
            "concepts_assumed": item.concepts_assumed,
        }
        for item in outline.segments
    ]
    return (
        "Generate the script draft for exactly one segment.\n\n"
        f"Brief:\n{brief.model_dump_json(indent=2)}\n\n"
        f"Full outline sibling context:\n{json.dumps(sibling_summaries, indent=2)}\n\n"
        f"Target segment outline:\n{segment.model_dump_json(indent=2)}\n\n"
        "Rules:\n"
        "- Include instructor narration that can be read aloud.\n"
        "- Include live code steps only when code_minutes > 0.\n"
        "- Include at least one comprehension check or activity.\n"
        "- In instructor_narration, place [CODE_STEP] exactly where each live_code_steps item should be taught.\n"
        "- In instructor_narration, place [CHECKPOINT] or [ACTIVITY] exactly where each check/activity should happen.\n"
        "- Do not leave vague placeholders like [CODE SNIPPET]; use the structured markers above.\n"
        "- Include reviewer_rationale explaining depth/example choices.\n"
        "- Do not re-teach topics listed as already covered; use callbacks instead.\n"
    )


def regeneration_user_prompt(
    project: ScriptProject,
    segment: SegmentOutline,
    current_text: str,
    instruction: str,
) -> str:
    previous_segments = [
        {
            "outline_id": draft.outline_id,
            "version": draft.version,
            "status": draft.status,
            "summary": draft.instructor_narration[:500],
        }
        for draft in project.segments
        if draft.outline_id != segment.id
    ]
    return (
        "Regenerate exactly one segment based on instructor feedback.\n\n"
        f"Brief:\n{project.brief.model_dump_json(indent=2)}\n\n"
        f"Target segment outline:\n{segment.model_dump_json(indent=2)}\n\n"
        f"Neighboring/current project context:\n{json.dumps(previous_segments, indent=2)}\n\n"
        f"Current segment narration:\n{current_text}\n\n"
        f"Instructor instruction:\n{instruction}\n\n"
        "Preserve the segment's timing and role in the larger class. In instructor_narration, place "
        "[CODE_STEP], [CHECKPOINT], and [ACTIVITY] markers exactly where the corresponding structured "
        "items should be taught. Return a full replacement SegmentDraft."
    )


def judge_system_prompt() -> str:
    return (
        "You are an exacting evaluator of instructor class scripts. Score conservatively from 0 to 5. "
        "Penalize generic LLM tone, weak pacing, agenda misses, and poor level calibration."
    )


def judge_user_prompt(project: ScriptProject) -> str:
    return (
        "Evaluate this generated class script against the brief.\n\n"
        f"Brief:\n{project.brief.model_dump_json(indent=2)}\n\n"
        f"Outline:\n{project.outline.model_dump_json(indent=2) if project.outline else '{}'}\n\n"
        f"Segments:\n{json.dumps([s.model_dump(mode='json') for s in project.segments], indent=2)}\n\n"
        "Rubric dimensions: coverage, level fit, pedagogical flow, instructor tone, factuality risk, pacing."
    )


def repair_planner_system_prompt() -> str:
    return (
        "You are a repair planner for an AI class-script generation pipeline. "
        "Given a generated project and its evaluation failures, decide which issues can be fixed "
        "by regenerating specific segments and which are global outline/brief issues. "
        "Return precise segment-level repair instructions. Do not rewrite the script yourself."
    )


def repair_planner_user_prompt(project: ScriptProject) -> str:
    eval_json = project.latest_evaluation.model_dump_json(indent=2) if project.latest_evaluation else "{}"
    segment_index = [
        {
            "segment_id": draft.id,
            "outline_id": draft.outline_id,
            "title": next(
                (outline.title for outline in (project.outline.segments if project.outline else []) if outline.id == draft.outline_id),
                "Unknown",
            ),
            "narration_preview": draft.instructor_narration[:700],
        }
        for draft in project.segments
    ]
    return (
        "Create a repair plan for this generated class script.\n\n"
        f"Brief:\n{project.brief.model_dump_json(indent=2)}\n\n"
        f"Outline:\n{project.outline.model_dump_json(indent=2) if project.outline else '{}'}\n\n"
        f"Segment index:\n{json.dumps(segment_index, indent=2)}\n\n"
        f"Evaluation report:\n{eval_json}\n\n"
        "Rules:\n"
        "- Use scope='segment' only when a specific segment can be regenerated to fix the issue.\n"
        "- Use segment_id equal to the SegmentDraft id from the segment index.\n"
        "- Use scope='global' for outline allocation, impossible brief constraints, or multi-segment issues.\n"
        "- Keep repair_instruction concrete enough to pass directly into segment regeneration.\n"
        "- Prefer at most 3 segment repairs.\n"
    )
