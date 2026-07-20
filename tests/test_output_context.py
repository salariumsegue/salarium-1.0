from pathlib import Path

from src.core.output_context import (
    resolve_agent_reports_dir,
    resolve_output_root,
    resolve_report_path,
    resolve_reports_root,
    resolve_result_path,
    resolve_results_dir,
)


def test_output_context_defaults_to_repository_paths(
    monkeypatch,
) -> None:
    monkeypatch.delenv("SALARIUM_RUN_DIR", raising=False)

    assert resolve_output_root() == Path.cwd()
    assert resolve_reports_root() == Path("reports")
    assert resolve_agent_reports_dir() == Path("reports/agent_runs")
    assert resolve_results_dir() == Path("results")
    assert resolve_report_path("latest.md") == Path(
        "reports/latest.md"
    )
    assert resolve_result_path("summary.csv") == Path(
        "results/summary.csv"
    )


def test_output_context_uses_run_scoped_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    run_directory = tmp_path / "run-123"
    monkeypatch.setenv(
        "SALARIUM_RUN_DIR",
        str(run_directory),
    )

    working = run_directory.resolve() / "working_outputs"

    assert resolve_output_root() == working
    assert resolve_reports_root() == working / "reports"
    assert resolve_agent_reports_dir() == (
        working / "reports" / "agent_runs"
    )
    assert resolve_results_dir() == working / "results"
    assert resolve_report_path("latest.md") == (
        working / "reports" / "latest.md"
    )
    assert resolve_result_path("summary.csv") == (
        working / "results" / "summary.csv"
    )
