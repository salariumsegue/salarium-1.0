from pathlib import Path


SOURCE = Path(
    "scripts/evaluate_walkforward_policies.py"
).read_text(encoding="utf-8")


def test_evaluator_reads_score_artifact() -> None:
    assert "walkforward_oos_scores.csv" in SOURCE


def test_evaluator_does_not_train_model() -> None:
    assert "RandomForestRegressor" not in SOURCE
    assert ".fit(" not in SOURCE


def test_evaluator_uses_approved_policies() -> None:
    assert "approved_research_policies" in SOURCE
    assert "ALPHA_BENCHMARK" in SOURCE
    assert "RISK_MANAGED_CANDIDATE" in SOURCE


def test_evaluator_uses_risk_controls() -> None:
    assert "select_buffered_holdings" in SOURCE
    assert "capped_inverse_volatility_weights" in SOURCE
    assert "resolve_risk_exposure" in SOURCE


def test_evaluator_saves_results() -> None:
    assert "approved_policy_results.csv" in SOURCE
    assert "approved_policy_summary.csv" in SOURCE
