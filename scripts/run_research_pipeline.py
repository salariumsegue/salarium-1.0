from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.core.artifacts import (
    RunArtifacts,
    capture_generated_outputs,
)
from src.core.run_context import create_run_context
from src.universe.canonical_snapshot import (
    assess_dataset_universe_coverage,
    find_latest_canonical_snapshot,
    load_canonical_snapshot,
)


def resolve_canonical_universe(
    repository_root: Path,
    manifest_override: str = "",
):
    if manifest_override:
        return load_canonical_snapshot(
            Path(manifest_override)
        )

    snapshot = find_latest_canonical_snapshot(
        repository_root
        / "configs"
        / "universe_snapshots"
    )

    if snapshot is None:
        raise FileNotFoundError(
            "No committed canonical liquid-universe "
            "snapshot was found."
        )

    return snapshot


COMMANDS = [
    ("walkforward_rank_backtest", "src/backtesting/walkforward_rank_backtest.py"),
    ("strategy_walkforward", "src/workflows/run_strategy_walkforward.py"),
    ("macro_model_comparison", "src/models/train_macro_comparison.py"),
    ("model_tournament", "src/workflows/run_model_tournament.py"),
    ("data_quality_leakage", "src/workflows/run_data_quality_leakage.py"),
    ("risk_portfolio", "src/workflows/run_risk_portfolio.py"),
    ("macro_feature_audit", "src/workflows/run_macro_feature_audit.py"),
    ("backtest_reviewer", "src/workflows/run_backtest_reviewer.py"),
    ("experiment_registry", "src/workflows/run_experiment_registry.py"),
    ("final_research_report", "src/workflows/run_final_research_report.py"),
]


def required_workflow_paths() -> list[Path]:
    return [Path(script_path) for _, script_path in COMMANDS]


def validate_workflows() -> None:
    missing = [
        str(path)
        for path in required_workflow_paths()
        if not path.is_file()
    ]

    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Missing required workflow files:\n" + formatted
        )


def build_child_environment(
    run_id: str,
    run_directory: Path,
    manifest_path: Path,
    *,
    universe_id: str | None = None,
    universe_path: Path | None = None,
    universe_manifest_path: Path | None = None,
    universe_market_date: str | None = None,
    training_data_path: Path | None = None,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "SALARIUM_RUN_ID": run_id,
            "SALARIUM_RUN_DIR": str(run_directory.resolve()),
            "SALARIUM_MANIFEST_PATH": str(manifest_path.resolve()),
        }
    )
    if universe_id is not None:
        environment["SALARIUM_UNIVERSE_ID"] = universe_id

    if universe_path is not None:
        environment["SALARIUM_UNIVERSE_PATH"] = str(
            universe_path.resolve()
        )

    if universe_manifest_path is not None:
        environment[
            "SALARIUM_UNIVERSE_MANIFEST_PATH"
        ] = str(universe_manifest_path.resolve())

    if universe_market_date is not None:
        environment[
            "SALARIUM_UNIVERSE_MARKET_DATE"
        ] = universe_market_date

    if training_data_path is not None:
        environment[
            "SALARIUM_TRAINING_DATA_PATH"
        ] = str(training_data_path.resolve())

    return environment


def run_command(
    name: str,
    script_path: str,
    environment: dict[str, str],
    log_directory: Path,
) -> dict[str, Any]:
    command = [sys.executable, script_path]
    log_path = log_directory / f"{name}.log"

    print()
    print("=" * 80)
    print("Running:", " ".join(command))
    print("Log:", log_path)
    print("=" * 80)

    completed = subprocess.run(
        command,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = (
        completed.stdout
        + ("\n" if completed.stdout and completed.stderr else "")
        + completed.stderr
    )
    log_path.write_text(combined_output, encoding="utf-8")

    if completed.stdout:
        print(completed.stdout, end="")

    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    return {
        "name": name,
        "script": script_path,
        "command": command,
        "return_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "log_path": str(log_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete Salarium research pipeline."
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help=(
            "Input file to hash into the run manifest. "
            "May be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--universe-manifest",
        default="",
        help=(
            "Optional canonical universe manifest override. "
            "Defaults to the latest committed liquid-500 snapshot."
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a non-canonical run from a dirty working tree.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running later workflows after a workflow fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository_root = REPOSITORY_ROOT

    validate_workflows()

    canonical_universe = resolve_canonical_universe(
        repository_root=repository_root,
        manifest_override=args.universe_manifest,
    )

    input_paths = [Path(path) for path in args.input]

    input_paths.extend(
        [
            canonical_universe.snapshot_path,
            canonical_universe.manifest_path,
        ]
    )

    input_paths = list(
        dict.fromkeys(input_paths)
    )

    missing_inputs = [
        str(path)
        for path in input_paths
        if not path.is_file()
    ]

    if missing_inputs:
        formatted = "\n".join(f"- {path}" for path in missing_inputs)
        raise FileNotFoundError(
            "Requested manifest inputs do not exist:\n" + formatted
        )

    if args.input:
        universe_coverage = (
            assess_dataset_universe_coverage(
                Path(args.input[0]),
                canonical_universe.frame,
            )
        )
    else:
        universe_coverage = {
            "status": "not_evaluated",
            "reason": "no_training_input_supplied",
        }

    parameters = {
        "pipeline": "research_pipeline",
        "workflow_count": len(COMMANDS),
        "continue_on_error": args.continue_on_error,
        "allow_dirty": args.allow_dirty,
        "universe_id": canonical_universe.universe_id,
        "universe_market_date": (
            canonical_universe.market_date
        ),
        "universe_snapshot_path": str(
            canonical_universe.snapshot_path
        ),
        "universe_coverage_status": (
            universe_coverage["status"]
        ),
    }

    context = create_run_context(
        input_paths=input_paths,
        parameters=parameters,
        repository_root=repository_root,
        allow_dirty=args.allow_dirty,
    )

    artifacts = RunArtifacts(
        context=context,
        base_directory=repository_root / "data" / "runs",
    )
    run_directory = artifacts.initialize()
    manifest_path = run_directory / "manifest.json"
    log_directory = run_directory / "logs"

    artifacts.write_json(
        "inputs/universe_context.json",
        {
            "universe_id": (
                canonical_universe.universe_id
            ),
            "market_date": (
                canonical_universe.market_date
            ),
            "snapshot_path": str(
                canonical_universe.snapshot_path
            ),
            "manifest_path": str(
                canonical_universe.manifest_path
            ),
            "snapshot_sha256": (
                canonical_universe.manifest[
                    "snapshot_sha256"
                ]
            ),
            "snapshot_rows": len(
                canonical_universe.frame
            ),
            "dataset_coverage": universe_coverage,
        },
    )

    environment = build_child_environment(
        run_id=context.run_id,
        run_directory=run_directory,
        manifest_path=manifest_path,
        universe_id=canonical_universe.universe_id,
        universe_path=canonical_universe.snapshot_path,
        universe_manifest_path=(
            canonical_universe.manifest_path
        ),
        universe_market_date=(
            canonical_universe.market_date
        ),
        training_data_path=(
            Path(args.input[0])
            if args.input
            else None
        ),
    )

    print(f"Salarium research pipeline root: {repository_root}")
    print(f"Run ID: {context.run_id}")
    print(f"Run directory: {run_directory}")
    print(f"Manifest: {manifest_path}")
    print(
        "Canonical universe:",
        canonical_universe.universe_id,
    )
    print(
        "Universe market date:",
        canonical_universe.market_date,
    )
    print(
        "Dataset universe coverage:",
        universe_coverage["status"],
    )

    workflow_results: list[dict[str, Any]] = []

    for name, script_path in COMMANDS:
        result = run_command(
            name=name,
            script_path=script_path,
            environment=environment,
            log_directory=log_directory,
        )
        workflow_results.append(result)

        artifacts.write_json(
            "pipeline_status.json",
            {
                "run_id": context.run_id,
                "status": (
                    "running"
                    if result["return_code"] == 0
                    else "failed"
                ),
                "workflows": workflow_results,
            },
        )

        if result["return_code"] != 0 and not args.continue_on_error:
            print()
            print(f"Pipeline stopped after failure in {name}.")
            return result["return_code"]

    final_status = (
        "passed"
        if all(
            result["return_code"] == 0
            for result in workflow_results
        )
        else "failed"
    )

    artifacts.write_json(
        "pipeline_status.json",
        {
            "run_id": context.run_id,
            "status": final_status,
            "workflows": workflow_results,
        },
    )

    captured_outputs = capture_generated_outputs(
        run_directory=run_directory,
        repository_root=repository_root,
        source_root=run_directory / "working_outputs",
    )

    final_payload = {
        "run_id": context.run_id,
        "status": final_status,
        "workflows": workflow_results,
        "captured_output_count": captured_outputs[
            "captured_file_count"
        ],
        "output_source": str(
            run_directory / "working_outputs"
        ),
    }

    artifacts.write_json(
        "pipeline_status.json",
        final_payload,
    )

    print()
    print(f"Research pipeline complete with status: {final_status}")
    print(
        "Captured outputs:",
        captured_outputs["captured_file_count"],
    )
    print(f"Run directory: {run_directory}")
    print("Open dashboard with:")
    print(f"{sys.executable} -m streamlit run app/streamlit_app.py")

    return 0 if final_status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
