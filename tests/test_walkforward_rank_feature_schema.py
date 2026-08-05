from pathlib import Path

from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
)


def test_rank_backtest_uses_governed_liquid500_features() -> None:
    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    expected_features = {
        "return_1d",
        "volume_change_1d",
        "high_low_spread",
        "open_close_spread",
        "momentum_5d",
        "momentum_20d",
        "volatility_20d",
        "price_vs_ma20",
        "price_vs_ma50",
        "rsi_14d",
        "relative_strength",
    }

    legacy_features = {
        "return_10d",
        "close_to_sma_5",
        "close_to_sma_20",
        "close_to_sma_50",
        "volume_ratio_10",
        "volatility_10",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
    }

    assert set(CORE_TECHNICAL_FEATURES) == expected_features
    assert "return_5d" not in CORE_TECHNICAL_FEATURES

    assert (
        "CORE_TECHNICAL_FEATURES"
        in source
    )

    for feature in legacy_features:
        assert feature not in CORE_TECHNICAL_FEATURES
