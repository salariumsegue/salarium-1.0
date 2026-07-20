from __future__ import annotations

import os
from pathlib import Path


def resolve_output_root() -> Path:
    run_directory = os.environ.get("SALARIUM_RUN_DIR", "").strip()

    if run_directory:
        return Path(run_directory).resolve() / "working_outputs"

    return Path.cwd()


def resolve_reports_root() -> Path:
    root = resolve_output_root()

    if os.environ.get("SALARIUM_RUN_DIR", "").strip():
        return root / "reports"

    return Path("reports")


def resolve_agent_reports_dir() -> Path:
    return resolve_reports_root() / "agent_runs"


def resolve_results_dir() -> Path:
    root = resolve_output_root()

    if os.environ.get("SALARIUM_RUN_DIR", "").strip():
        return root / "results"

    return Path("results")


def resolve_report_path(filename: str) -> Path:
    return resolve_reports_root() / filename


def resolve_result_path(filename: str) -> Path:
    return resolve_results_dir() / filename
