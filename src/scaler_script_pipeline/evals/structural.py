from __future__ import annotations

from scaler_script_pipeline.core.models import ScriptProject
from scaler_script_pipeline.evals.types import EvalExpectations, GuardrailResult
from scaler_script_pipeline.services.density import project_density_failures, project_density_summary


def run_guardrails(project: ScriptProject, expectations: EvalExpectations) -> list[GuardrailResult]:
    checks: list[GuardrailResult] = []
    outline = project.outline

    if outline is None:
        return [
            GuardrailResult(
                name="outline_exists",
                passed=False,
                detail="Project has no generated outline.",
                red_line="R4_NO_SEGMENT_REGEN_UNIT",
            )
        ]

    agenda_lower = [item.lower() for item in project.brief.agenda]
    outline_agenda = " ".join(segment.agenda_item.lower() for segment in outline.segments)
    missing_agenda = [item for item in agenda_lower if item not in outline_agenda]
    checks.append(
        GuardrailResult(
            name="agenda_coverage",
            passed=not missing_agenda,
            detail="All agenda items are represented." if not missing_agenda else f"Missing: {missing_agenda}",
            red_line=None if not missing_agenda else "R1_AGENDA_MISS",
        )
    )

    total_minutes = sum(segment.duration_minutes for segment in outline.segments)
    timing_ok = abs(total_minutes - project.brief.duration_minutes) <= 1
    checks.append(
        GuardrailResult(
            name="timing_sum",
            passed=timing_ok,
            detail=f"Outline totals {total_minutes} minutes; brief requested {project.brief.duration_minutes}.",
            red_line=None if timing_ok else "R2_TIMING_INVALID",
        )
    )

    code_minutes = sum(segment.code_minutes for segment in outline.segments)
    content_minutes = sum(segment.content_minutes for segment in outline.segments)
    actual_code_pct = round((code_minutes / max(code_minutes + content_minutes, 1)) * 100)
    ratio_ok = abs(actual_code_pct - project.brief.code_percentage) <= 10
    checks.append(
        GuardrailResult(
            name="content_code_ratio",
            passed=ratio_ok,
            detail=f"Actual code ratio {actual_code_pct}%; target {project.brief.code_percentage}%.",
            red_line=None if ratio_ok else "R3_RATIO_INVALID",
        )
    )

    outline_ids = {segment.id for segment in outline.segments}
    draft_ids = {segment.outline_id for segment in project.segments}
    stable = bool(project.segments) and draft_ids.issubset(outline_ids)
    checks.append(
        GuardrailResult(
            name="stable_segment_ids",
            passed=stable,
            detail="Every draft maps to a stable outline segment." if stable else "Draft/outline mapping is broken.",
            red_line=None if stable else "R5_NO_SEGMENT_REGEN_UNIT",
        )
    )

    script_text = _project_text(project)
    missing_terms = [term for term in expectations.must_cover if term.lower() not in script_text]
    checks.append(
        GuardrailResult(
            name="must_cover_terms",
            passed=not missing_terms,
            detail="Expected terms appear in the script." if not missing_terms else f"Missing terms: {missing_terms}",
            red_line=None if not missing_terms else "R1_AGENDA_MISS",
        )
    )

    reteach_hits = [
        topic
        for topic in expectations.must_not_reteach
        if f"what is {topic.lower()}" in script_text
        or f"define {topic.lower()}" in script_text
        or f"from scratch {topic.lower()}" in script_text
    ]
    checks.append(
        GuardrailResult(
            name="prior_topic_not_retaught",
            passed=not reteach_hits,
            detail="Prior topics are not obviously re-taught." if not reteach_hits else f"Potential re-teaching: {reteach_hits}",
            red_line=None if not reteach_hits else "R6_PRIOR_TOPIC_RETAUGHT",
        )
    )

    total_checks = sum(len(segment.checks) + len(segment.activities) for segment in project.segments)
    min_checks = max(1, project.brief.duration_minutes // 30)
    checks_ok = total_checks >= min_checks
    checks.append(
        GuardrailResult(
            name="checkpoint_presence",
            passed=checks_ok,
            detail=f"Found {total_checks} checks/activities; expected at least {min_checks}.",
            red_line=None if checks_ok else "R7_NO_CHECKPOINTS",
        )
    )

    code_required = project.brief.code_percentage >= 30
    live_code_steps = sum(len(segment.live_code_steps) for segment in project.segments)
    code_ok = (not code_required) or live_code_steps > 0
    checks.append(
        GuardrailResult(
            name="live_code_when_required",
            passed=code_ok,
            detail=f"Found {live_code_steps} live-code steps.",
            red_line=None if code_ok else "R3_RATIO_INVALID",
        )
    )

    missing_rationales = [segment.id for segment in project.segments if not segment.reviewer_rationale.strip()]
    checks.append(
        GuardrailResult(
            name="reviewability_rationales",
            passed=not missing_rationales,
            detail="Every segment includes reviewer rationale." if not missing_rationales else f"Missing rationales: {missing_rationales}",
            red_line=None if not missing_rationales else "R4_NO_HUMAN_REVIEW_STRUCTURE",
        )
    )

    density_failures = project_density_failures(project)
    checks.append(
        GuardrailResult(
            name="content_density",
            passed=not density_failures,
            detail=project_density_summary(project) if not density_failures else " | ".join(density_failures),
            red_line="R10_UNTEACHABLE_SCRIPT" if density_failures else None,
        )
    )

    return checks


def has_red_line_failures(guardrails: list[GuardrailResult]) -> bool:
    return any((not check.passed) and check.red_line for check in guardrails)


def _project_text(project: ScriptProject) -> str:
    parts: list[str] = []
    if project.outline:
        parts.append(project.outline.model_dump_json())
    parts.extend(segment.model_dump_json() for segment in project.segments)
    return " ".join(parts).lower()
