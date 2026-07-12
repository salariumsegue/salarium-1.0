import json
import sys
from pathlib import Path

import pytest

from scripts.run_research_pipeline import (
    build_child_environment,
    required_workflow_paths,
    run_command,
    validate_workflows,
)


def test_required_workflow_paths_are_unique() -> None:
    paths = required_workflow_paths()

    assert len(paths) == len(set(paths))
    assert all(path.suffix == ".py" for path in paths)


def test_validate_workflows_passes_in_repository() -> None:
    validate_workflows()


def test_child_environment_contains_shared_run_identity(
    tmp_path: Path,
) -> None:
    run_directory = tmp_path / "runs" / "run-123"
    manifest_path = run_directory / "manifest.json"

    environment = build_child_environment(
        run_id="run-123",
        run_directory=run_directory,
        manifest_path=manifest_path,
    )

    assert environment["SALARIUM_RUN_ID"] == "run-123"
    assert environment["SALARIUM_RUN_DIR"] == str(
        run_directory.resolve()
    )
    assert environment["SALARIUM_MANIFEST_PATH"] == str(
        manifest_path.resolve()
    )


def test_run_command_captures_successful_output(
    tmp_path: Path,
) -> None:
    script = tmp_path / "success.py"
    script.write_text(
        'print("workflow completed")\n',
        encoding="utf-8",
    )

    log_directory = tmp_path / "logs"
    log_directory.mkdir()

    result = run_command(
        name="success",
        script_path=str(script),
        environment={},
        log_directory=log_directory,
    )

    assert result["status"] == "passed"
    assert result["return_code"] == 0

    log_path = Path(result["log_path"])
    assert log_path.is_file()
    assert "workflow completed" in log_path.read_text(
        encoding="utf-8"
    )


def test_run_command_records_failure(
    tmp_path: Path,
) -> None:
    script = tmp_path / "failure.py"
    script.write_text(
        (
            "import sys\n"
            'print("workflow failed")\n'
            "raise SystemExit(7)\n"
        ),
        encoding="utf-8",
    )

    log_directory = tmp_path / "logs"
    log_directory.mkdir()

    result = run_command(
        name="failure",
        script_path=str(script),
        environment={},
        log_directory=log_directory,
    )

    assert result["status"] == "failed"
    assert result["return_code"] == 7
    assert "workflow failed" in Path(
        result["log_path"]
    ).read_text(encoding="utf-8")


def test_pipeline_script_can_be_executed_directly() -> None:
    import subprocess

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_research_pipeline.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "complete Salarium research pipeline" in completed.stdout


def test_default_canonical_universe_can_be_resolved() -> None:
    from pathlib import Path

    from scripts.run_research_pipeline import (
        resolve_canonical_universe,
    )

    snapshot = resolve_canonical_universe(
        Path.cwd()
    )

    assert len(snapshot.frame) == 500
    assert snapshot.frame["ticker"].nunique() == 500
    assert snapshot.universe_id.startswith(
        "current_liquid_500_"
    )


def test_child_environment_exports_universe_identity(
    tmp_path: Path,
) -> None:
    run_directory = tmp_path / "run"
    manifest_path = run_directory / "manifest.json"
    universe_path = tmp_path / "universe.csv"
    universe_manifest = tmp_path / "universe.json"

    environment = build_child_environment(
        run_id="run-123",
        run_directory=run_directory,
        manifest_path=manifest_path,
        universe_id="universe-500",
        universe_path=universe_path,
        universe_manifest_path=universe_manifest,
        universe_market_date="2026-07-10",
    )

    assert environment[
        "SALARIUM_UNIVERSE_ID"
    ] == "universe-500"

    assert environment[
        "SALARIUM_UNIVERSE_PATH"
    ] == str(universe_path.resolve())

    assert environment[
        "SALARIUM_UNIVERSE_MANIFEST_PATH"
    ] == str(universe_manifest.resolve())

    assert environment[
        "SALARIUM_UNIVERSE_MARKET_DATE"
    ] == "2026-07-10"
