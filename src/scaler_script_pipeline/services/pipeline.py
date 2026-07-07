from __future__ import annotations

import logging
import re

from fastapi import HTTPException

from scaler_script_pipeline.core.models import (
    ClassOutline,
    DraftStatus,
    GenerationStatus,
    InstructorBrief,
    RegenerationRequest,
    RepairPlan,
    ReviewEvent,
    ReviewEventType,
    ReviewStatus,
    ScriptProject,
    SegmentDraft,
    SegmentEditRequest,
    SegmentRegenerateRequest,
    SignOff,
    SignOffRequest,
)
from scaler_script_pipeline.services.claude import ClaudeClient
from scaler_script_pipeline.services.evaluator import EvaluationRunner
from scaler_script_pipeline.services.prompts import (
    outline_system_prompt,
    outline_user_prompt,
    repair_planner_system_prompt,
    repair_planner_user_prompt,
    regeneration_user_prompt,
    segment_system_prompt,
    segment_user_prompt,
)
from scaler_script_pipeline.services.validator import BriefValidator
from scaler_script_pipeline.storage.repository import ProjectRepository

logger = logging.getLogger(__name__)


class ScriptPipeline:
    def __init__(
        self,
        repository: ProjectRepository,
        validator: BriefValidator,
        claude: ClaudeClient,
        evaluator: EvaluationRunner,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.claude = claude
        self.evaluator = evaluator

    def generate_project(self, brief: InstructorBrief) -> ScriptProject:
        project = ScriptProject(
            brief=brief,
            generation_status=GenerationStatus.CREATED,
            generation_message="Project created.",
            generation_progress=0,
        )
        self.repository.create(project)
        logger.info(
            "project.generate.start project_id=%s topic=%r agenda_items=%s duration=%s ratio=%s/%s audience=%s/%s",
            project.id,
            brief.topic,
            len(brief.agenda),
            brief.duration_minutes,
            brief.content_percentage,
            brief.code_percentage,
            brief.beginner_percentage,
            brief.advanced_percentage,
        )
        try:
            self._set_generation_state(
                project,
                GenerationStatus.VALIDATING,
                "Validating instructor brief.",
                5,
            )
            self._generate_project_in_place(project)
        except Exception as exc:
            logger.exception("project.generate.failed project_id=%s", project.id)
            project.generation_status = GenerationStatus.FAILED
            project.generation_message = "Generation failed."
            project.generation_error = str(exc)
            project.generation_progress = 100
            self.repository.save(project)
        return self.get_project(project.id)

    def _generate_project_in_place(self, project: ScriptProject) -> None:
        brief = project.brief
        validation = self.validator.validate(brief)
        project.validation = validation
        self.repository.save(project)
        logger.info(
            "project.validation.done project_id=%s valid=%s warnings=%s errors=%s",
            project.id,
            validation.is_valid,
            len(validation.warnings),
            len(validation.errors),
        )

        if not validation.is_valid:
            project.generation_status = GenerationStatus.FAILED
            project.generation_message = "Brief has blocking validation errors."
            project.generation_error = "; ".join(error.message for error in validation.errors)
            project.generation_progress = 100
            self.repository.save(project)
            logger.warning("project.validation.blocked project_id=%s error=%s", project.id, project.generation_error)
            return

        self._set_generation_state(
            project,
            GenerationStatus.GENERATING_OUTLINE,
            "Generating class outline.",
            20,
        )
        warning_messages = [warning.message for warning in validation.warnings]
        outline = self.claude.generate_model(
            outline_system_prompt(),
            outline_user_prompt(brief, warning_messages),
            ClassOutline,
            trace_name="outline_generation",
            trace_metadata={"project_id": project.id, "stage": "outline"},
        )
        outline.warnings = validation.warnings + outline.warnings
        project.outline = outline
        self.repository.save(project)
        logger.info(
            "project.outline.done project_id=%s outline_id=%s segments=%s target_content=%s target_code=%s",
            project.id,
            outline.id,
            len(outline.segments),
            outline.target_content_minutes,
            outline.target_code_minutes,
        )

        self._set_generation_state(
            project,
            GenerationStatus.GENERATING_SEGMENTS,
            "Generating segment drafts.",
            35,
        )
        segments: list[SegmentDraft] = []
        total_segments = len(outline.segments)
        for index, segment_outline in enumerate(outline.segments, start=1):
            logger.info(
                "segment.generate.start project_id=%s outline_id=%s index=%s/%s title=%r minutes=%s content=%s code=%s",
                project.id,
                segment_outline.id,
                index,
                total_segments,
                segment_outline.title,
                segment_outline.duration_minutes,
                segment_outline.content_minutes,
                segment_outline.code_minutes,
            )
            draft = self.claude.generate_model(
                segment_system_prompt(),
                segment_user_prompt(brief, outline, segment_outline),
                SegmentDraft,
                trace_name="segment_generation",
                trace_metadata={
                    "project_id": project.id,
                    "segment_id": segment_outline.id,
                    "segment_order": index,
                    "stage": "segment_generation",
                },
            )
            draft.outline_id = segment_outline.id
            draft.duration_minutes = segment_outline.duration_minutes
            draft.content_minutes = segment_outline.content_minutes
            draft.code_minutes = segment_outline.code_minutes
            failures = self._segment_local_failures(draft)
            if failures:
                logger.warning(
                    "segment.local_guardrail.failed project_id=%s outline_id=%s failures=%s",
                    project.id,
                    segment_outline.id,
                    "; ".join(failures),
                )
                repair_prompt = (
                    "Repair this generated segment. Fix these guardrail failures: "
                    + "; ".join(failures)
                )
                repaired = self.claude.generate_model(
                    segment_system_prompt(),
                    regeneration_user_prompt(project, segment_outline, draft.instructor_narration, repair_prompt),
                    SegmentDraft,
                    trace_name="segment_local_repair",
                    trace_metadata={
                        "project_id": project.id,
                        "segment_id": segment_outline.id,
                        "stage": "segment_local_repair",
                        "failures": failures,
                    },
                )
                repaired.outline_id = segment_outline.id
                repaired.duration_minutes = segment_outline.duration_minutes
                repaired.content_minutes = segment_outline.content_minutes
                repaired.code_minutes = segment_outline.code_minutes
                repaired.status = DraftStatus.REGENERATED
                draft = repaired
                logger.info("segment.local_guardrail.repaired project_id=%s outline_id=%s", project.id, segment_outline.id)
            segments.append(draft)
            project.segments = segments
            project.generation_progress = 35 + int((index / max(total_segments, 1)) * 40)
            project.generation_message = f"Generated segment {index}/{total_segments}."
            self.repository.save(project)
            logger.info(
                "segment.generate.done project_id=%s draft_id=%s index=%s/%s version=%s checks=%s activities=%s code_steps=%s",
                project.id,
                draft.id,
                index,
                total_segments,
                draft.version,
                len(draft.checks),
                len(draft.activities),
                len(draft.live_code_steps),
            )

        self._set_generation_state(
            project,
            GenerationStatus.EVALUATING,
            "Running evaluation checks.",
            85,
        )
        project.latest_evaluation = self.evaluator.run_all(project)
        logger.info(
            "project.eval.done project_id=%s passed=%s failures=%s recommendations=%s",
            project.id,
            project.latest_evaluation.passed_gate,
            len(project.latest_evaluation.structural.failures),
            len(project.latest_evaluation.recommendations),
        )
        if not project.latest_evaluation.passed_gate:
            self._set_generation_state(
                project,
                GenerationStatus.REPAIRING,
                "Eval found issues. Planning targeted repairs.",
                90,
            )
            self._repair_once(project)
            self._set_generation_state(
                project,
                GenerationStatus.EVALUATING,
                "Re-running evaluation after repairs.",
                95,
            )
            project.latest_evaluation = self.evaluator.run_all(project)
            logger.info(
                "project.eval.rerun_done project_id=%s passed=%s failures=%s recommendations=%s",
                project.id,
                project.latest_evaluation.passed_gate,
                len(project.latest_evaluation.structural.failures),
                len(project.latest_evaluation.recommendations),
            )

        project.review_status = ReviewStatus.UNDER_REVIEW
        if project.latest_evaluation.passed_gate:
            project.generation_status = GenerationStatus.READY_FOR_REVIEW
            project.generation_message = "Generation complete and eval gate passed."
        else:
            project.generation_status = GenerationStatus.NEEDS_REVISION
            project.generation_message = "Generation complete, but eval found issues."
        project.generation_progress = 100
        self.repository.save(project)
        logger.info(
            "project.generate.done project_id=%s status=%s review_status=%s passed_gate=%s",
            project.id,
            project.generation_status.value,
            project.review_status.value,
            project.latest_evaluation.passed_gate if project.latest_evaluation else None,
        )

    def _repair_once(self, project: ScriptProject) -> None:
        if project.outline is None or project.latest_evaluation is None:
            return
        plan = self.claude.generate_model(
            repair_planner_system_prompt(),
            repair_planner_user_prompt(project),
            RepairPlan,
            trace_name="repair_plan",
            trace_metadata={"project_id": project.id, "stage": "repair_plan"},
        )
        repairable = [issue for issue in plan.repairs if issue.scope == "segment" and issue.segment_id]
        logger.info(
            "project.repair.plan project_id=%s segment_repairs=%s global_issues=%s rationale=%r",
            project.id,
            len(repairable),
            len(plan.global_issues),
            plan.rationale[:300],
        )
        for issue in repairable[:3]:
            try:
                draft = self._find_segment_draft(project, issue.segment_id or "")
                outline = self._find_segment_outline(project, draft.outline_id)
            except HTTPException:
                logger.warning("project.repair.segment_missing project_id=%s segment_id=%s", project.id, issue.segment_id)
                continue
            logger.info(
                "project.repair.segment.start project_id=%s segment_id=%s severity=%s issue=%r",
                project.id,
                draft.id,
                issue.severity,
                issue.issue,
            )
            regenerated = self.claude.generate_model(
                segment_system_prompt(),
                regeneration_user_prompt(
                    project,
                    outline,
                    draft.instructor_narration,
                    issue.repair_instruction,
                ),
                SegmentDraft,
                trace_name="eval_repair_regeneration",
                trace_metadata={
                    "project_id": project.id,
                    "segment_id": draft.id,
                    "stage": "eval_repair_regeneration",
                    "repair_issue": issue.issue,
                },
            )
            regenerated.id = draft.id
            regenerated.outline_id = outline.id
            regenerated.duration_minutes = outline.duration_minutes
            regenerated.content_minutes = outline.content_minutes
            regenerated.code_minutes = outline.code_minutes
            regenerated.version = draft.version + 1
            regenerated.status = DraftStatus.REGENERATED
            idx = project.segments.index(draft)
            project.segments[idx] = regenerated
            project.review_events.append(
                ReviewEvent(
                    project_id=project.id,
                    segment_id=draft.id,
                    type=ReviewEventType.REGENERATED,
                    instructor_feedback=f"Auto-repair: {issue.issue}",
                    before_text=draft.instructor_narration,
                    after_text=regenerated.instructor_narration,
                    version_before=draft.version,
                    version_after=regenerated.version,
                )
            )
            logger.info(
                "project.repair.segment.done project_id=%s segment_id=%s version=%s",
                project.id,
                regenerated.id,
                regenerated.version,
            )
        if plan.global_issues:
            project.review_events.append(
                ReviewEvent(
                    project_id=project.id,
                    type=ReviewEventType.COMMENT,
                    instructor_feedback=(
                        "Global repair issues: "
                        + "; ".join(f"{issue.severity}: {issue.issue}" for issue in plan.global_issues)
                    ),
                )
            )
        self.repository.save(project)

    def get_project(self, project_id: str) -> ScriptProject:
        project = self.repository.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def list_projects(self) -> list[ScriptProject]:
        return self.repository.list()

    def edit_segment(
        self, project_id: str, segment_id: str, request: SegmentEditRequest
    ) -> ScriptProject:
        project = self.get_project(project_id)
        self._ensure_project_editable(project)
        draft = self._find_segment_draft(project, segment_id)
        logger.info("segment.edit project_id=%s segment_id=%s version_before=%s", project_id, draft.id, draft.version)
        before = draft.instructor_narration
        version_before = draft.version
        draft.instructor_narration = request.instructor_narration
        draft.status = DraftStatus.EDITED
        draft.version += 1
        project.review_status = ReviewStatus.CHANGES_REQUESTED
        project.review_events.append(
            ReviewEvent(
                project_id=project.id,
                segment_id=segment_id,
                type=ReviewEventType.EDIT,
                instructor_feedback=request.instructor_feedback,
                before_text=before,
                after_text=draft.instructor_narration,
                version_before=version_before,
                version_after=draft.version,
            )
        )
        return self.repository.save(project)

    def regenerate_segment(
        self, project_id: str, segment_id: str, request: SegmentRegenerateRequest
    ) -> ScriptProject:
        project = self.get_project(project_id)
        self._ensure_project_editable(project)
        if project.outline is None:
            raise HTTPException(status_code=400, detail="Project has no outline")
        draft = self._find_segment_draft(project, segment_id)
        outline = self._find_segment_outline(project, segment_id)
        logger.info(
            "segment.regenerate.start project_id=%s segment_id=%s version_before=%s instruction_chars=%s",
            project_id,
            draft.id,
            draft.version,
            len(request.instruction),
        )

        regen = RegenerationRequest(
            project_id=project.id,
            segment_id=segment_id,
            instruction=request.instruction,
            reason=request.reason,
            target_version=draft.version + 1,
        )
        project.review_events.append(
            ReviewEvent(
                project_id=project.id,
                segment_id=segment_id,
                type=ReviewEventType.REGENERATE_REQUESTED,
                instructor_feedback=f"{request.reason}\n{request.instruction}".strip(),
                before_text=draft.instructor_narration,
                version_before=draft.version,
            )
        )

        regenerated = self.claude.generate_model(
            segment_system_prompt(),
            regeneration_user_prompt(project, outline, draft.instructor_narration, regen.instruction),
            SegmentDraft,
            trace_name="manual_segment_regeneration",
            trace_metadata={
                "project_id": project.id,
                "segment_id": draft.id,
                "stage": "manual_segment_regeneration",
            },
        )
        regenerated.id = draft.id
        regenerated.outline_id = outline.id
        regenerated.duration_minutes = outline.duration_minutes
        regenerated.content_minutes = outline.content_minutes
        regenerated.code_minutes = outline.code_minutes
        regenerated.version = draft.version + 1
        regenerated.status = DraftStatus.REGENERATED

        idx = project.segments.index(draft)
        project.segments[idx] = regenerated
        project.review_status = ReviewStatus.CHANGES_REQUESTED
        project.review_events.append(
            ReviewEvent(
                project_id=project.id,
                segment_id=segment_id,
                type=ReviewEventType.REGENERATED,
                instructor_feedback=request.instruction,
                before_text=draft.instructor_narration,
                after_text=regenerated.instructor_narration,
                version_before=draft.version,
                version_after=regenerated.version,
            )
        )
        project.latest_evaluation = self.evaluator.run_all(project)
        saved = self.repository.save(project)
        logger.info(
            "segment.regenerate.done project_id=%s segment_id=%s version_after=%s passed_gate=%s",
            project_id,
            regenerated.id,
            regenerated.version,
            project.latest_evaluation.passed_gate if project.latest_evaluation else None,
        )
        return saved

    def evaluate_project(self, project_id: str) -> ScriptProject:
        project = self.get_project(project_id)
        logger.info("project.evaluate.start project_id=%s", project_id)
        project.latest_evaluation = self.evaluator.run_all(project)
        saved = self.repository.save(project)
        logger.info(
            "project.evaluate.done project_id=%s passed_gate=%s failures=%s",
            project_id,
            project.latest_evaluation.passed_gate,
            len(project.latest_evaluation.structural.failures),
        )
        return saved

    def sign_off(self, project_id: str, request: SignOffRequest) -> ScriptProject:
        project = self.get_project(project_id)
        logger.info(
            "project.sign_off project_id=%s approved=%s instructor=%r",
            project_id,
            request.approved,
            request.instructor_name,
        )
        sign_off = SignOff(
            project_id=project.id,
            instructor_name=request.instructor_name,
            approved=request.approved,
            final_notes=request.final_notes,
        )
        project.sign_off = sign_off
        project.review_status = ReviewStatus.APPROVED if request.approved else ReviewStatus.CHANGES_REQUESTED
        for segment in project.segments:
            if request.approved:
                segment.status = DraftStatus.APPROVED
        project.review_events.append(
            ReviewEvent(
                project_id=project.id,
                type=ReviewEventType.APPROVED,
                instructor_feedback=request.final_notes,
                after_text=f"Approved by {request.instructor_name}: {request.approved}",
            )
        )
        return self.repository.save(project)

    def _ensure_project_editable(self, project: ScriptProject) -> None:
        if project.sign_off and project.sign_off.approved:
            raise HTTPException(
                status_code=409,
                detail="Project is signed off and locked. Create a new project or add a reopen-review flow before editing.",
            )

    def export_markdown(self, project_id: str) -> str:
        project = self.get_project(project_id)
        lines = [
            f"# {project.brief.topic}",
            "",
            "## Brief",
            "",
            f"- Duration: {project.brief.duration_minutes} minutes",
            f"- Audience: {project.brief.beginner_percentage}% beginner / {project.brief.advanced_percentage}% advanced",
            f"- Ratio: {project.brief.content_percentage}% content / {project.brief.code_percentage}% code",
            "",
        ]
        if project.outline:
            lines.extend(
                [
                    "## Opening Frame",
                    "",
                    project.outline.audience_calibration,
                    "",
                ]
            )
        for idx, draft in enumerate(project.segments, start=1):
            outline = self._find_segment_outline(project, draft.outline_id)
            lines.extend(
                [
                    f"## {idx}. {outline.title}",
                    "",
                    f"Timing: {draft.duration_minutes} min ({draft.content_minutes} content / {draft.code_minutes} code)",
                    "",
                    f"**Transition in:** {outline.transition_in}",
                    "",
                    "### Instructor Script",
                    "",
                    *self._render_segment_markdown(draft),
                    f"**Transition out:** {outline.transition_out}",
                    "",
                ]
            )
        if project.outline:
            lines.extend(["## Recap", "", project.outline.recap_plan, "", "## Next", "", project.outline.next_steps_plan, ""])
        return "\n".join(lines)

    def _render_segment_markdown(self, draft: SegmentDraft) -> list[str]:
        lines: list[str] = []
        code_steps = list(draft.live_code_steps)
        checks = list(draft.checks)
        activities = list(draft.activities)
        marker_pattern = re.compile(r"(\[(?:CODE_STEP|CODE SNIPPET|CHECKPOINT|ACTIVITY)\])", re.IGNORECASE)

        for part in marker_pattern.split(draft.instructor_narration):
            marker = part.upper()
            if marker in {"[CODE_STEP]", "[CODE SNIPPET]"}:
                if code_steps:
                    step = code_steps.pop(0)
                    lines.extend([f"**Live code {step.order}: {step.instruction}**", "", f"```text\n{step.code}\n```", step.explanation, ""])
                continue
            if marker == "[CHECKPOINT]":
                if checks:
                    check = checks.pop(0)
                    lines.extend([f"**Checkpoint:** {check.question}", "", f"- Expected: {check.expected_answer}", f"- Guidance: {check.instructor_guidance}", ""])
                continue
            if marker == "[ACTIVITY]":
                if activities:
                    activity = activities.pop(0)
                    lines.extend(
                        [
                            f"**{activity.type.value.replace('_', ' ').title()}:** {activity.prompt}",
                            "",
                            f"- Expected: {activity.expected_response}",
                            f"- Facilitation: {activity.facilitation_notes}",
                            "",
                        ]
                    )
                continue
            if part.strip():
                lines.extend([part.strip(), ""])

        for step in code_steps:
            lines.extend([f"**Live code {step.order}: {step.instruction}**", "", f"```text\n{step.code}\n```", step.explanation, ""])
        for example in draft.worked_examples:
            lines.extend(
                [
                    f"**Worked example:** {example.setup}",
                    "",
                    example.walkthrough,
                    "",
                    f"- Takeaway: {example.takeaway}",
                    "",
                ]
            )
        for check in checks:
            lines.extend([f"**Checkpoint:** {check.question}", "", f"- Expected: {check.expected_answer}", f"- Guidance: {check.instructor_guidance}", ""])
        for activity in activities:
            lines.extend(
                [
                    f"**{activity.type.value.replace('_', ' ').title()}:** {activity.prompt}",
                    "",
                    f"- Expected: {activity.expected_response}",
                    f"- Facilitation: {activity.facilitation_notes}",
                    "",
                ]
            )
        return lines

    def _find_segment_draft(self, project: ScriptProject, segment_id: str) -> SegmentDraft:
        for draft in project.segments:
            if draft.id == segment_id or draft.outline_id == segment_id:
                return draft
        raise HTTPException(status_code=404, detail="Segment not found")

    def _find_segment_outline(self, project: ScriptProject, segment_id: str):
        if project.outline is None:
            raise HTTPException(status_code=400, detail="Project has no outline")
        for segment in project.outline.segments:
            if segment.id == segment_id:
                return segment
        for draft in project.segments:
            if draft.id == segment_id:
                for segment in project.outline.segments:
                    if segment.id == draft.outline_id:
                        return segment
        raise HTTPException(status_code=404, detail="Segment outline not found")

    def _set_generation_state(
        self,
        project: ScriptProject,
        status: GenerationStatus,
        message: str,
        progress: int,
    ) -> None:
        project.generation_status = status
        project.generation_message = message
        project.generation_progress = progress
        self.repository.save(project)

    def _segment_local_failures(self, draft: SegmentDraft) -> list[str]:
        failures: list[str] = []
        if not draft.instructor_narration.strip():
            failures.append("missing instructor narration")
        if not draft.reviewer_rationale.strip():
            failures.append("missing reviewer rationale")
        if not draft.checks and not draft.activities:
            failures.append("missing comprehension check or activity")
        if draft.code_minutes > 0 and not draft.live_code_steps:
            failures.append("code minutes allocated but no live-code steps")
        return failures
