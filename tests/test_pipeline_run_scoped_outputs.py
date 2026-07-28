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


def test_macro_comparison_precedes_model_tournament() -> None:
    source = Path(
        "scripts/run_research_pipeline.py"
    ).read_text(encoding="utf-8")

    macro_position = source.index(
        '("macro_model_comparison", '
        '"src/models/train_macro_comparison.py")'
    )
    tournament_position = source.index(
        '("model_tournament", '
        '"src/workflows/run_model_tournament.py")'
    )

    assert macro_position < tournament_position


def test_macro_comparison_uses_canonical_context() -> None:
    source = Path(
        "src/models/train_macro_comparison.py"
    ).read_text(encoding="utf-8")

    assert "resolve_training_data_path()" in source
    assert (
        'resolve_result_path("macro_model_comparison.csv")'
        in source
    )
    assert (
        'resolve_result_path("macro_feature_importance.csv")'
        in source
    )
    assert (
        'Path("results/macro_model_comparison.csv")'
        not in source
    )


def test_agents_do_not_write_global_latest_reports() -> None:
    agent_paths = [
        Path("src/agents/data_quality_leakage_agent.py"),
        Path("src/agents/macro_feature_audit_agent.py"),
        Path("src/agents/risk_portfolio_agent.py"),
        Path("src/agents/model_tournament_agent.py"),
        Path("src/agents/backtest_reviewer_agent.py"),
        Path("src/agents/strategy_walkforward_agent.py"),
    ]

    for path in agent_paths:
        source = path.read_text(encoding="utf-8")
        assert 'Path("reports/' not in source
        assert "resolve_report_path(" in source
