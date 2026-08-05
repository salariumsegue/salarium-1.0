from pathlib import Path


BACKTEST = Path(
    "src/backtesting/walkforward_rank_backtest.py"
)


def source_text() -> str:
    return BACKTEST.read_text(
        encoding="utf-8"
    )


def test_inverse_volatility_mode_exists() -> None:
    source = source_text()

    assert (
        "turnover_buffer_inverse_volatility"
        in source
    )


def test_risk_scaled_mode_exists() -> None:
    source = source_text()

    assert (
        "turnover_buffer_inverse_volatility_"
        "risk_scaled"
        in source
    )


def test_inverse_volatility_uses_reusable_control() -> None:
    source = source_text()

    assert (
        "capped_inverse_volatility_weights"
        in source
    )
    assert "maximum_weight=0.18" in source


def test_risk_scaled_mode_uses_regime_fields() -> None:
    source = source_text()

    assert "resolve_risk_exposure" in source
    assert '"risk_state"' in source
    assert '"regime_is_confident"' in source


def test_weighted_return_replaces_simple_mean() -> None:
    source = source_text()

    assert (
        "new_weights[ticker]"
        in source
    )
    assert (
        "selected_returns.mean()"
        not in source
    )


def test_portfolio_diagnostics_are_recorded() -> None:
    source = source_text()

    assert '"portfolio_exposure"' in source
    assert '"maximum_weight"' in source
    assert '"herfindahl_index"' in source
