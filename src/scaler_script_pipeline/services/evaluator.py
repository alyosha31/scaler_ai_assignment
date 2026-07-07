from __future__ import annotations

import logging

from scaler_script_pipeline.core.config import Settings
from scaler_script_pipeline.core.models import (
    EvaluationReport,
    GoldenComparisonPlan,
    ModelJudgeResult,
    ScriptProject,
    StructuralEvalResult,
)
from scaler_script_pipeline.services.claude import ClaudeClient
from scaler_script_pipeline.services.density import project_density_failures
from scaler_script_pipeline.services.prompts import judge_system_prompt, judge_user_prompt

logger = logging.getLogger(__name__)


class EvaluationRunner:
    def __init__(self, claude: ClaudeClient, settings: Settings) -> None:
        self.claude = claude
        self.settings = settings

    def run_structural_checks(self, project: ScriptProject) -> StructuralEvalResult:
        failures: list[str] = []
        brief = project.brief
        outline = project.outline

        if outline is None:
            return StructuralEvalResult(
                all_agenda_items_present=False,
                timing_sums_correctly=False,
                content_code_ratio_within_tolerance=False,
                prior_topics_not_reteaught=False,
                segment_ids_stable=False,
                failures=["No outline exists."],
            )

        outline_agenda = [segment.agenda_item.strip().lower() for segment in outline.segments]
        all_agenda = all(item.strip().lower() in outline_agenda for item in brief.agenda)
        if not all_agenda:
            failures.append("Not every agenda item has a matching outline segment.")

        total_minutes = sum(segment.duration_minutes for segment in outline.segments)
        timing_ok = abs(total_minutes - brief.duration_minutes) <= 1
        if not timing_ok:
            failures.append(
                f"Segment timing sums to {total_minutes}, expected {brief.duration_minutes}."
            )

        content_minutes = sum(segment.content_minutes for segment in outline.segments)
        code_minutes = sum(segment.code_minutes for segment in outline.segments)
        total_ratio_minutes = max(content_minutes + code_minutes, 1)
        actual_code_pct = round((code_minutes / total_ratio_minutes) * 100)
        ratio_ok = abs(actual_code_pct - brief.code_percentage) <= 10
        if not ratio_ok:
            failures.append(
                f"Code ratio is {actual_code_pct}%, expected about {brief.code_percentage}%."
            )

        combined_text = " ".join(draft.instructor_narration.lower() for draft in project.segments)
        prior_reteach_hits = [
            topic
            for topic in brief.topics_already_covered
            if f"what is {topic.lower()}" in combined_text
            or f"define {topic.lower()}" in combined_text
            or f"from scratch {topic.lower()}" in combined_text
        ]
        prior_ok = not prior_reteach_hits
        if not prior_ok:
            failures.append(
                "Potential re-teaching of prior topics: " + ", ".join(prior_reteach_hits)
            )

        outline_ids = {segment.id for segment in outline.segments}
        draft_outline_ids = {draft.outline_id for draft in project.segments}
        stable_ids = draft_outline_ids.issubset(outline_ids) and len(draft_outline_ids) == len(
            project.segments
        )
        if not stable_ids:
            failures.append("One or more segment drafts do not map to stable outline IDs.")

        failures.extend(project_density_failures(project))

        return StructuralEvalResult(
            all_agenda_items_present=all_agenda,
            timing_sums_correctly=timing_ok,
            content_code_ratio_within_tolerance=ratio_ok,
            prior_topics_not_reteaught=prior_ok,
            segment_ids_stable=stable_ids,
            failures=failures,
        )

    def run_model_judge(self, project: ScriptProject) -> ModelJudgeResult | None:
        if not self.settings.model_judge_enabled:
            logger.info("eval.model_judge.skipped project_id=%s", project.id)
            return None
        logger.info("eval.model_judge.start project_id=%s", project.id)
        result = self.claude.generate_model(judge_system_prompt(), judge_user_prompt(project), ModelJudgeResult)
        logger.info(
            "eval.model_judge.done project_id=%s avg_score=%.2f coverage=%.1f level_fit=%.1f pedagogy=%.1f",
            project.id,
            result.average_score,
            result.coverage_score,
            result.level_fit_score,
            result.pedagogy_score,
        )
        return result

    def run_all(self, project: ScriptProject) -> EvaluationReport:
        logger.info("eval.start project_id=%s segments=%s", project.id, len(project.segments))
        structural = self.run_structural_checks(project)
        logger.info(
            "eval.structural.done project_id=%s failures=%s details=%s",
            project.id,
            len(structural.failures),
            " | ".join(structural.failures) if structural.failures else "none",
        )
        model_judge = self.run_model_judge(project)
        model_ok = model_judge is None or model_judge.average_score >= 3.75
        passed = not structural.failures and model_ok
        recommendations = list(structural.failures)
        if model_judge and not model_ok:
            recommendations.append("Model judge average score is below the 3.75 go/no-go threshold.")

        report = EvaluationReport(
            project_id=project.id,
            structural=structural,
            model_judge=model_judge,
            golden_comparison=GoldenComparisonPlan(
                comparison_method="Blind pairwise preference against human-authored instructor scripts.",
                required_dataset="A small set of real Scaler class scripts matched by topic and level.",
                blind_review_protocol=(
                    "Instructors compare anonymized generated and human scripts, then choose which is "
                    "more teach-ready and whether either needs major edits."
                ),
                notes="Documented as production eval path; not run in this take-home without golden scripts.",
            ),
            passed_gate=passed,
            recommendations=recommendations,
        )
        logger.info(
            "eval.done project_id=%s passed=%s recommendations=%s",
            project.id,
            report.passed_gate,
            len(report.recommendations),
        )
        return report
