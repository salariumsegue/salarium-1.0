import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.run_context import (
    RunContext,
    hash_inputs,
    make_run_id,
    sha256_file,
)


def test_sha256_file_is_deterministic(tmp_path: Path) -> None:
    file_path = tmp_path / "input.csv"
    file_path.write_text("ticker,price\nAAPL,100\n", encoding="utf-8")

    first = sha256_file(file_path)
    second = sha256_file(file_path)

    assert first == second
    assert len(first) == 64


def test_sha256_changes_when_file_changes(tmp_path: Path) -> None:
    file_path = tmp_path / "input.csv"
    file_path.write_text("AAPL,100\n", encoding="utf-8")
    first = sha256_file(file_path)

    file_path.write_text("AAPL,101\n", encoding="utf-8")
    second = sha256_file(file_path)

    assert first != second


def test_missing_file_cannot_be_hashed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "missing.csv")


def test_hash_inputs_is_sorted_and_complete(tmp_path: Path) -> None:
    second = tmp_path / "b.csv"
    first = tmp_path / "a.csv"

    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")

    hashes = hash_inputs([second, first])

    assert list(hashes) == sorted([str(first), str(second)])
    assert hashes[str(first)] == sha256_file(first)
    assert hashes[str(second)] == sha256_file(second)


def test_make_run_id_uses_utc_time_and_commit_prefix() -> None:
    timestamp = datetime(
        2026,
        7,
        12,
        3,
        30,
        45,
        tzinfo=timezone.utc,
    )

    run_id = make_run_id(
        "1234567890abcdef",
        timestamp,
    )

    assert run_id == "20260712T033045Z_12345678"


def test_make_run_id_rejects_naive_datetime() -> None:
    timestamp = datetime(2026, 7, 12, 3, 30, 45)

    with pytest.raises(ValueError, match="timezone-aware"):
        make_run_id("1234567890abcdef", timestamp)


def test_manifest_is_written_as_stable_json(tmp_path: Path) -> None:
    context = RunContext(
        schema_version="1.0",
        run_id="20260712T033045Z_12345678",
        created_at_utc="2026-07-12T03:30:45+00:00",
        git_commit="1234567890abcdef",
        git_branch="phase3-run-manifests-artifacts",
        git_dirty=False,
        python_version="3.14.6",
        platform="test-platform",
        input_hashes={"input.csv": "abc123"},
        parameters={"top_n": 10},
    )

    manifest_path = context.write_manifest(
        tmp_path / "run" / "manifest.json"
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["run_id"] == context.run_id
    assert payload["git_dirty"] is False
    assert payload["input_hashes"]["input.csv"] == "abc123"
    assert payload["parameters"]["top_n"] == 10
    assert not manifest_path.with_suffix(".json.tmp").exists()
