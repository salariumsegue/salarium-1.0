import pandas as pd
import pytest

from src.backtesting.risk_controls import (
    calculate_turnover,
    cap_turnover,
    capped_inverse_volatility_weights,
    equal_weights,
    resolve_risk_exposure,
    select_buffered_holdings,
    weight_diagnostics,
)


def test_buffer_retains_eligible_names() -> None:
    selected = select_buffered_holdings(
        ["A", "B", "C", "D", "E"],
        ["E", "A"],
        top_n=3,
        buffer_rank=5,
    )

    assert selected == ["E", "A", "B"]


def test_equal_weights_respect_exposure() -> None:
    weights = equal_weights(
        ["A", "B", "C"],
        exposure=0.75,
    )

    assert sum(weights.values()) == pytest.approx(
        0.75
    )
    assert weights["A"] == pytest.approx(
        0.25
    )


def test_inverse_volatility_weights_are_capped() -> None:
    weights = (
        capped_inverse_volatility_weights(
            pd.Series(
                {
                    "A": 0.01,
                    "B": 0.02,
                    "C": 0.03,
                    "D": 0.04,
                    "E": 0.05,
                    "F": 0.06,
                }
            ),
            exposure=0.75,
            maximum_weight=0.18,
        )
    )

    assert sum(
        weights.values()
    ) == pytest.approx(0.75)

    assert max(
        weights.values()
    ) <= 0.18 + 1e-12


def test_turnover_cap_blends_weights() -> None:
    previous = {
        "A": 0.5,
        "B": 0.5,
    }

    target = {
        "C": 0.5,
        "D": 0.5,
    }

    blended, turnover, blend = (
        cap_turnover(
            previous,
            target,
            maximum_turnover=0.6,
        )
    )

    assert turnover == pytest.approx(
        0.6
    )
    assert 0 < blend < 1

    assert calculate_turnover(
        previous,
        blended,
    ) == pytest.approx(0.6)


def test_unconfident_risk_on_is_neutralized() -> None:
    exposure = resolve_risk_exposure(
        "risk_on",
        regime_is_confident=False,
    )

    assert exposure == pytest.approx(
        0.75
    )


def test_confident_risk_off_reduces_exposure() -> None:
    exposure = resolve_risk_exposure(
        "risk_off",
        regime_is_confident=True,
    )

    assert exposure == pytest.approx(
        0.45
    )


def test_weight_diagnostics() -> None:
    diagnostics = weight_diagnostics(
        {
            "A": 0.5,
            "B": 0.25,
        }
    )

    assert diagnostics[
        "gross_exposure"
    ] == pytest.approx(0.75)

    assert diagnostics[
        "maximum_weight"
    ] == pytest.approx(0.5)

    assert diagnostics[
        "herfindahl_index"
    ] == pytest.approx(0.3125)
