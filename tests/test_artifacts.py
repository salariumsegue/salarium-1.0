import json
from pathlib import Path

import pytest

from src.core.artifacts import RunArtifacts
from src.core.run_context import RunContext


@pytest.fixture
def context() -> RunContext:
    return RunContext(
        schema_version="1.0",
        run_id="20260712T040000Z_12345678",
        created_at_utc="2026-07-12T04:00:00+00:00",
        git_commit="1234567890abcdef",
        git_branch="phase3-run-manifests-artifacts",
        git_dirty=False,
        python_version="3.14.6",
        platform="test-platform",
        input_hashes={"input.csv": "abc123"},
        parameters={"top_n": 10},
    )


def test_initialize_creates_run_structure(
    tmp_path: Path,
    context: RunContext,
) -> None:
    artifacts = RunArtifacts(
        context=context,
        base_directory=tmp_path / "runs",
    )

    run_directory = artifacts.initialize()

    assert run_directory.exists()
    assert (run_directory / "manifest.json").is_file()

    for directory_name in (
        "inputs",
        "predictions",
        "backtest",
        "portfolio",
        "reports",
        "logs",
    ):
        assert (run_directory / directory_name).is_dir()


def test_initialize_refuses_to_overwrite_existing_run(
    tmp_path: Path,
    context: RunContext,
) -> None:
    artifacts = RunArtifacts(
        context=context,
        base_directory=tmp_path / "runs",
    )

    artifacts.initialize()

    with pytest.raises(FileExistsError):
        artifacts.initialize()


def test_write_json_writes_stable_payload(
    tmp_path: Path,
    context: RunContext,
) -> None:
    artifacts = RunArtifacts(
        context=context,
        base_directory=tmp_path / "runs",
    )
    artifacts.initialize()

    output_path = artifacts.write_json(
        "backtest/summary.json",
        {"sharpe": 0.42, "top_n": 10},
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {"sharpe": 0.42, "top_n": 10}


def test_artifact_path_cannot_escape_run_directory(
    tmp_path: Path,
    context: RunContext,
) -> None:
    artifacts = RunArtifacts(
        context=context,
        base_directory=tmp_path / "runs",
    )
    artifacts.initialize()

    with pytest.raises(ValueError, match="escapes"):
        artifacts.path("../outside.json")
