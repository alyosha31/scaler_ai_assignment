from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_tutor.evals.runner import run_eval


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run class-script pipeline evals.")
    parser.add_argument("--structural-only", action="store_true", help="Skip LLM judge calls.")
    parser.add_argument("--case", dest="case_filter", help="Run a single case_id.")
    parser.add_argument("--max-cases", type=int, help="Run only the first N scenarios.")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("eval/scenarios/script-generation-cases.json"),
    )
    parser.add_argument(
        "--pairs",
        type=Path,
        default=Path("eval/scenarios/level-adaptivity-pairs.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("eval/results"))
    parser.add_argument(
        "--database-url",
        default="sqlite:///./data/eval_runs.db",
        help="SQLite URL used by generated eval projects.",
    )
    parser.add_argument(
        "--from-projects",
        type=Path,
        help="Directory containing <case_id>.project.json files to re-evaluate without regenerating.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result, report_path = run_eval(
        scenarios_path=args.scenarios,
        pairs_path=args.pairs,
        output_dir=args.output_dir,
        structural_only=args.structural_only,
        case_filter=args.case_filter,
        max_cases=args.max_cases,
        database_url=args.database_url,
        from_projects=args.from_projects,
    )
    passed = sum(1 for case in result.cases if case.passed_gate)
    print(f"Report: {report_path}")
    print(f"Cases passed: {passed}/{len(result.cases)}")
    print(f"Pairs passed: {sum(1 for pair in result.pairs if pair.passed_gate)}/{len(result.pairs)}")
    print(f"Gate: {'PASS' if result.passed_gate else 'FAIL'}")
    return 0 if result.passed_gate else 1


if __name__ == "__main__":
    sys.exit(main())
