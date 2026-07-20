from pathlib import Path


def test_rank_backtest_uses_canonical_liquid500_features() -> None:
    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    expected_features = [
        "return_1d",
        "return_5d",
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
    ]

    legacy_features = [
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
    ]

    for feature in expected_features:
        assert f'"{feature}"' in source

    for feature in legacy_features:
        assert f'"{feature}"' not in source


def test_rank_backtest_has_single_dataset_context_import() -> None:
    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    assert source.count(
        "from src.core.dataset_context import"
    ) == 1
