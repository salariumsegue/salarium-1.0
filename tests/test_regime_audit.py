import pandas as pd
import pytest

from src.regime.regime_audit import (
    audit_regime_coverage,
    daily_regime_frame,
)


def test_daily_regime_frame_removes_cross_sectional_duplicates() -> None:
    frame = pd.DataFrame(
        {
            "date": [
                "2025-01-02",
                "2025-01-02",
                "2025-01-03",
                "2025-01-03",
            ],
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "market_regime": [
                "risk_on",
                "risk_on",
                "risk_off",
                "risk_off",
            ],
            "regime_is_confident": [True, True, True, True],
        }
    )

    daily = daily_regime_frame(frame)

    assert len(daily) == 2
    assert list(daily["market_regime"]) == [
        "risk_on",
        "risk_off",
    ]


def test_daily_regime_frame_rejects_same_date_inconsistency() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2025-01-02", "2025-01-02"],
            "market_regime": ["risk_on", "risk_off"],
        }
    )

    with pytest.raises(ValueError, match="same date"):
        daily_regime_frame(frame)


def test_audit_reports_missing_regimes() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2025-01-02", "2025-01-03"],
            "market_regime": ["risk_on", "risk_off"],
            "regime_is_confident": [True, False],
        }
    )

    audit = audit_regime_coverage(frame)

    assert audit["num_dates"] == 2
    assert audit["counts"]["risk_on"] == 1
    assert "expansion" in audit["missing_regimes"]
    assert audit["confident_share"] == pytest.approx(0.5)
