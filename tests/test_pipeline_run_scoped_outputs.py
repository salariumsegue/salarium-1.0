from pathlib import Path


def test_pipeline_captures_run_scoped_outputs() -> None:
    source = Path(
        "scripts/run_research_pipeline.py"
    ).read_text(encoding="utf-8")

    assert (
        'source_root=run_directory / "working_outputs"'
        in source
    )
    assert (
        '["git", "restore", "--", "reports", "results"]'
        not in source
    )


def test_workflows_use_output_context() -> None:
    workflow_paths = list(
        Path("src/workflows").glob("run_*.py")
    )

    required = {
        "run_backtest_reviewer.py",
        "run_data_quality_leakage.py",
        "run_experiment_registry.py",
        "run_final_research_report.py",
        "run_macro_feature_audit.py",
        "run_model_tournament.py",
        "run_risk_portfolio.py",
        "run_strategy_walkforward.py",
    }

    selected = [
        path
        for path in workflow_paths
        if path.name in required
    ]

    assert {path.name for path in selected} == required

    for path in selected:
        source = path.read_text(encoding="utf-8")
        assert "src.core.output_context" in source
        assert '"reports_dir": "reports/agent_runs"' not in source
        assert '"results_dir": "results"' not in source
