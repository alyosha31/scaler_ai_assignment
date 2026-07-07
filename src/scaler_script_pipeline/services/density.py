from __future__ import annotations

import re

from scaler_script_pipeline.core.models import ScriptProject, SegmentDraft

MAX_WORDS_PER_CONTENT_MINUTE = 160
MAX_CODE_STEPS_PER_CODE_MINUTE = 1.25
MAX_CONCEPTS_PER_SEGMENT_MINUTE = 1.0


def project_density_failures(project: ScriptProject) -> list[str]:
    failures: list[str] = []
    outline_by_id = {
        segment.id: segment for segment in project.outline.segments
    } if project.outline else {}

    for draft in project.segments:
        words_per_content_minute = _words_per_content_minute(draft)
        if words_per_content_minute > MAX_WORDS_PER_CONTENT_MINUTE:
            failures.append(
                f"Segment {draft.id} has {words_per_content_minute:.0f} narration words/content-minute; "
                f"expected <= {MAX_WORDS_PER_CONTENT_MINUTE}."
            )

        code_steps_per_minute = _code_steps_per_code_minute(draft)
        if code_steps_per_minute > MAX_CODE_STEPS_PER_CODE_MINUTE:
            failures.append(
                f"Segment {draft.id} has {code_steps_per_minute:.2f} live-code steps/code-minute; "
                f"expected <= {MAX_CODE_STEPS_PER_CODE_MINUTE}."
            )

        outline = outline_by_id.get(draft.outline_id)
        if outline:
            concept_count = len(set(outline.concepts_introduced + outline.concepts_reinforced))
            concepts_per_minute = concept_count / max(draft.duration_minutes, 1)
            if concepts_per_minute > MAX_CONCEPTS_PER_SEGMENT_MINUTE:
                failures.append(
                    f"Segment {draft.id} introduces/reinforces {concepts_per_minute:.2f} concepts/minute; "
                    f"expected <= {MAX_CONCEPTS_PER_SEGMENT_MINUTE}."
                )

    return failures


def project_density_summary(project: ScriptProject) -> str:
    if not project.segments:
        return "No segments generated."
    max_words = max(_words_per_content_minute(segment) for segment in project.segments)
    max_code_steps = max(_code_steps_per_code_minute(segment) for segment in project.segments)
    return (
        f"Max narration density {max_words:.0f} words/content-minute; "
        f"max live-code density {max_code_steps:.2f} steps/code-minute."
    )


def _words_per_content_minute(segment: SegmentDraft) -> float:
    words = len(re.findall(r"\b\w+\b", segment.instructor_narration))
    return words / max(segment.content_minutes, 1)


def _code_steps_per_code_minute(segment: SegmentDraft) -> float:
    if not segment.live_code_steps:
        return 0
    return len(segment.live_code_steps) / max(segment.code_minutes, 1)
