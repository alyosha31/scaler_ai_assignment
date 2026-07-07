from scaler_script_pipeline.core.models import (
    BriefValidationResult,
    InstructorBrief,
    ValidationErrorDetail,
    ValidationWarning,
)


class BriefValidator:
    def validate(self, brief: InstructorBrief) -> BriefValidationResult:
        warnings: list[ValidationWarning] = []
        errors: list[ValidationErrorDetail] = []

        if brief.beginner_percentage + brief.advanced_percentage != 100:
            errors.append(
                ValidationErrorDetail(
                    code="AUDIENCE_SPLIT_SUM",
                    message="Beginner and advanced percentages must sum to 100.",
                )
            )

        if brief.content_percentage + brief.code_percentage != 100:
            errors.append(
                ValidationErrorDetail(
                    code="CONTENT_CODE_SUM",
                    message="Content and code percentages must sum to 100.",
                )
            )

        if len(brief.agenda) > brief.duration_minutes / 5:
            warnings.append(
                ValidationWarning(
                    code="DENSE_AGENDA",
                    message="The agenda is dense for the requested duration.",
                    suggested_resolution=(
                        "The outline should treat some agenda items as survey-level coverage "
                        "or combine adjacent items."
                    ),
                )
            )

        if brief.duration_minutes < 45 and brief.code_percentage >= 50:
            warnings.append(
                ValidationWarning(
                    code="SHORT_CODE_HEAVY_SESSION",
                    message="A short, code-heavy session may not leave enough time for setup and checks.",
                    suggested_resolution="Use one focused live-code path and keep conceptual setup concise.",
                )
            )

        if not brief.topics_already_covered:
            warnings.append(
                ValidationWarning(
                    code="NO_PRIOR_TOPICS",
                    message="No prior topics were provided.",
                    suggested_resolution=(
                        "Assume only the background implied by the audience split and avoid callbacks "
                        "to prior sessions."
                    ),
                )
            )

        return BriefValidationResult(
            is_valid=not errors,
            warnings=warnings,
            errors=errors,
            normalized_brief=brief if not errors else None,
        )

