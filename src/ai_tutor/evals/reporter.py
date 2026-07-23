from __future__ import annotations

import json
from pathlib import Path

from ai_tutor.evals.types import EvalRunResult


def write_report(run_dir: Path, result: EvalRunResult) -> Path:
    report_path = run_dir / "report.md"
    passed_cases = sum(1 for case in result.cases if case.passed_gate)
    passed_pairs = sum(1 for pair in result.pairs if pair.passed_gate)

    lines: list[str] = [
        "# Class Script Pipeline Eval Report",
        "",
        f"- **Model**: {result.model}",
        f"- **Judge enabled**: {result.judge_enabled}",
        f"- **Prompt hash**: `{result.prompt_hash}`",
        f"- **Scenario count**: {result.scenario_count}",
        f"- **Cases passed**: {passed_cases}/{len(result.cases)}",
        f"- **Adaptivity pairs passed**: {passed_pairs}/{len(result.pairs)}",
        f"- **Overall gate**: {'PASS' if result.passed_gate else 'FAIL'}",
        "",
        "## Summary",
        "",
        "| # | Case | Category | Structural | Judge | Red lines | Result |",
        "|---|---|---|---|---|---|---|",
    ]

    for index, case in enumerate(result.cases, start=1):
        judge_score = f"{case.judge.overall:.2f}" if case.judge else "skipped"
        red_lines = sorted(
            {
                check.red_line
                for check in case.guardrails
                if check.red_line and not check.passed
            }
            | (set(case.judge.red_lines) if case.judge else set())
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    case.case_id,
                    case.category,
                    "PASS" if case.structural_passed else "FAIL",
                    judge_score,
                    ", ".join(red_lines) if red_lines else "-",
                    "PASS" if case.passed_gate else "FAIL",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Case Details", ""])
    for case in result.cases:
        lines.extend(
            [
                f"### {'PASS' if case.passed_gate else 'FAIL'} {case.case_id}",
                "",
                f"- **Project ID**: `{case.project_id}`",
                f"- **Generation status**: {case.generation_status}",
                f"- **Project JSON**: `{case.project_json_path}`",
                f"- **Script Markdown**: `{case.script_markdown_path}`",
                "",
                "#### Guardrails",
                "",
            ]
        )
        for guardrail in case.guardrails:
            status = "PASS" if guardrail.passed else "FAIL"
            red = f" ({guardrail.red_line})" if guardrail.red_line and not guardrail.passed else ""
            lines.append(f"- **{status}** `{guardrail.name}`{red}: {guardrail.detail}")
        if case.judge:
            lines.extend(
                [
                    "",
                    "#### Model Judge",
                    "",
                    f"- **Overall**: {case.judge.overall:.2f}",
                    f"- **Average score**: {case.judge.scores.average:.2f}",
                    f"- **Red lines**: {', '.join(case.judge.red_lines) if case.judge.red_lines else '-'}",
                    f"- **Rationale**: {case.judge.rationale}",
                ]
            )
        if case.error:
            lines.extend(["", f"- **Error**: {case.error}"])
        lines.append("")

    lines.extend(["## Level Adaptivity", ""])
    for pair in result.pairs:
        lines.extend(
            [
                f"### {'PASS' if pair.passed_gate else 'FAIL'} {pair.pair_id}",
                "",
                f"- **Beginner case**: {pair.beginner_case_id}",
                f"- **Advanced case**: {pair.advanced_case_id}",
            ]
        )
        if pair.judge:
            lines.extend(
                [
                    f"- **Meaningfully different**: {pair.judge.meaningfully_different}",
                    f"- **Too similar risk**: {pair.judge.too_similar_risk}",
                    f"- **Vocabulary**: {pair.judge.vocabulary_difference}",
                    f"- **Pacing**: {pair.judge.pacing_difference}",
                    f"- **Assumed knowledge**: {pair.judge.assumed_knowledge_difference}",
                    f"- **Examples**: {pair.judge.example_depth_difference}",
                    f"- **Code complexity**: {pair.judge.code_complexity_difference}",
                    f"- **Checkpoints**: {pair.judge.checkpoint_difference}",
                ]
            )
        if pair.error:
            lines.append(f"- **Error**: {pair.error}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "results.json").write_text(
        json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return report_path


def create_run_dir(base_dir: Path, model: str) -> Path:
    from datetime import datetime

    safe_model = model.replace(":", "-").replace("/", "-")
    timestamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
    run_dir = base_dir / safe_model / timestamp
    (run_dir / "projects").mkdir(parents=True, exist_ok=True)
    (run_dir / "scripts").mkdir(parents=True, exist_ok=True)
    return run_dir
