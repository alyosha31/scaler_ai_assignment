from __future__ import annotations

import json
import hashlib
from pathlib import Path

from scaler_script_pipeline.core.config import Settings, get_settings
from scaler_script_pipeline.core.models import GenerationStatus, ScriptProject
from scaler_script_pipeline.evals.judge import EvalJudge
from scaler_script_pipeline.evals.reporter import create_run_dir, write_report
from scaler_script_pipeline.evals.structural import has_red_line_failures, run_guardrails
from scaler_script_pipeline.evals.types import (
    CaseEvalResult,
    EvalRunResult,
    EvalScenario,
    GeneratedCase,
    LevelAdaptivityPair,
    PairEvalResult,
)
from scaler_script_pipeline.services.claude import ClaudeClient
from scaler_script_pipeline.services.evaluator import EvaluationRunner
from scaler_script_pipeline.services.pipeline import ScriptPipeline
from scaler_script_pipeline.services.validator import BriefValidator
from scaler_script_pipeline.storage.repository import ProjectRepository


def load_scenarios(path: Path, case_filter: str | None, max_cases: int | None) -> list[EvalScenario]:
    scenarios = [EvalScenario.model_validate(item) for item in json.loads(path.read_text())]
    if case_filter:
        scenarios = [scenario for scenario in scenarios if scenario.case_id == case_filter]
    if max_cases is not None:
        scenarios = scenarios[:max_cases]
    return scenarios


def load_pairs(path: Path) -> list[LevelAdaptivityPair]:
    if not path.exists():
        return []
    return [LevelAdaptivityPair.model_validate(item) for item in json.loads(path.read_text())]


def build_pipeline(settings: Settings, database_url: str | None = None) -> ScriptPipeline:
    generation_settings = settings.model_copy(update={"model_judge_enabled": False})
    repo = ProjectRepository(database_url or settings.database_url)
    repo.init_db()
    claude = ClaudeClient(generation_settings)
    return ScriptPipeline(
        repository=repo,
        validator=BriefValidator(),
        claude=claude,
        evaluator=EvaluationRunner(claude, generation_settings),
    )


def run_eval(
    scenarios_path: Path,
    pairs_path: Path,
    output_dir: Path,
    structural_only: bool = False,
    case_filter: str | None = None,
    max_cases: int | None = None,
    database_url: str | None = None,
    from_projects: Path | None = None,
) -> tuple[EvalRunResult, Path]:
    settings = get_settings()
    scenarios = load_scenarios(scenarios_path, case_filter, max_cases)
    pairs = load_pairs(pairs_path)
    if case_filter:
        pairs = [
            pair
            for pair in pairs
            if pair.beginner_case_id == case_filter or pair.advanced_case_id == case_filter
        ]

    run_dir = create_run_dir(output_dir, settings.anthropic_model)
    pipeline = build_pipeline(settings, database_url=database_url)
    judge = None if structural_only else EvalJudge(ClaudeClient(settings))

    generated: dict[str, GeneratedCase] = {}
    case_results: list[CaseEvalResult] = []

    for scenario in scenarios:
        if from_projects:
            project_path_in = from_projects / f"{scenario.case_id}.project.json"
            project = ScriptProject.model_validate_json(project_path_in.read_text())
            markdown = render_markdown_from_project(project)
        else:
            project = pipeline.generate_project(scenario.brief)
            markdown = pipeline.export_markdown(project.id) if project.outline else ""

        project_path = run_dir / "projects" / f"{scenario.case_id}.project.json"
        script_path = run_dir / "scripts" / f"{scenario.case_id}.script.md"
        project_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        script_path.write_text(markdown, encoding="utf-8")

        generated[scenario.case_id] = GeneratedCase(
            scenario=scenario,
            project=project,
            markdown=markdown,
        )
        case_results.append(
            evaluate_case(
                scenario=scenario,
                project=project,
                project_path=project_path,
                script_path=script_path,
                judge=judge,
            )
        )

    pair_results = [
        evaluate_pair(pair, generated, judge)
        for pair in pairs
        if pair.beginner_case_id in generated and pair.advanced_case_id in generated
    ]

    passed_gate = all(case.passed_gate for case in case_results) and all(
        pair.passed_gate for pair in pair_results
    )
    result = EvalRunResult(
        model=settings.anthropic_model,
        judge_enabled=not structural_only,
        prompt_hash=prompt_hash(),
        scenario_count=len(scenarios),
        cases=case_results,
        pairs=pair_results,
        passed_gate=passed_gate,
    )
    report_path = write_report(run_dir, result)
    return result, report_path


def render_markdown_from_project(project: ScriptProject) -> str:
    lines = [f"# {project.brief.topic}", ""]
    if project.outline:
        lines.extend(["## Outline", "", project.outline.audience_calibration, ""])
    for index, segment in enumerate(project.segments, start=1):
        lines.extend([f"## {index}. Segment", "", segment.instructor_narration, ""])
    return "\n".join(lines)


def evaluate_case(
    scenario: EvalScenario,
    project: ScriptProject,
    project_path: Path,
    script_path: Path,
    judge: EvalJudge | None,
) -> CaseEvalResult:
    guardrails = run_guardrails(project, scenario.expectations)
    structural_passed = not has_red_line_failures(guardrails) and all(
        check.passed for check in guardrails
    )

    judge_result = None
    error = None
    if judge and project.generation_status == GenerationStatus.READY_FOR_REVIEW:
        try:
            judge_result = judge.judge_script(project, scenario.expectations.expected_level)
        except Exception as exc:  # keep eval report complete even on provider failure
            error = str(exc)

    judge_passed = True
    if judge_result:
        judge_passed = (
            judge_result.overall >= scenario.expectations.min_model_score
            and judge_result.scores.average >= scenario.expectations.min_model_score
            and not judge_result.red_lines
        )
    elif judge:
        judge_passed = False

    generation_ok = project.generation_status == GenerationStatus.READY_FOR_REVIEW
    passed_gate = generation_ok and structural_passed and judge_passed
    return CaseEvalResult(
        case_id=scenario.case_id,
        category=scenario.category,
        project_id=project.id,
        generation_status=project.generation_status.value,
        structural_passed=structural_passed,
        guardrails=guardrails,
        judge=judge_result,
        passed_gate=passed_gate,
        project_json_path=str(project_path),
        script_markdown_path=str(script_path),
        error=error or project.generation_error,
    )


def evaluate_pair(
    pair: LevelAdaptivityPair,
    generated: dict[str, GeneratedCase],
    judge: EvalJudge | None,
) -> PairEvalResult:
    if judge is None:
        return PairEvalResult(
            pair_id=pair.pair_id,
            beginner_case_id=pair.beginner_case_id,
            advanced_case_id=pair.advanced_case_id,
            judge=None,
            passed_gate=True,
        )

    try:
        result = judge.judge_adaptivity(
            generated[pair.beginner_case_id].project,
            generated[pair.advanced_case_id].project,
        )
        return PairEvalResult(
            pair_id=pair.pair_id,
            beginner_case_id=pair.beginner_case_id,
            advanced_case_id=pair.advanced_case_id,
            judge=result,
            passed_gate=result.pass_ and result.meaningfully_different,
        )
    except Exception as exc:
        return PairEvalResult(
            pair_id=pair.pair_id,
            beginner_case_id=pair.beginner_case_id,
            advanced_case_id=pair.advanced_case_id,
            passed_gate=False,
            error=str(exc),
        )


def prompt_hash() -> str:
    prompt_file = Path("src/scaler_script_pipeline/services/prompts.py")
    if not prompt_file.exists():
        return "unknown"
    return hashlib.sha256(prompt_file.read_bytes()).hexdigest()[:12]
