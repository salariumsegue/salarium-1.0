import numpy as np
import pandas as pd
import pytest

from src.features.build_stock_training_data import build_features_for_ticker


FEATURE_COLUMNS = [
    "return_1d",
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "rsi_14d",
    "relative_strength",
    "ma_20",
    "ma_50",
    "price_vs_ma20",
    "price_vs_ma50",
]


def make_price_series(
    periods: int = 90,
) -> tuple[pd.Series, pd.Series]:
    dates = pd.bdate_range("2025-01-02", periods=periods)

    stock_close = pd.Series(
        np.linspace(100.0, 145.0, periods),
        index=dates,
        name="AAPL",
    )

    spy_close = pd.Series(
        np.linspace(400.0, 440.0, periods),
        index=dates,
        name="SPY",
    )

    return stock_close, spy_close


def test_five_day_target_matches_future_close_return() -> None:
    stock_close, spy_close = make_price_series()

    result = build_features_for_ticker(
        ticker="AAPL",
        sector="Technology",
        close=stock_close,
        spy_close=spy_close,
    )

    row = 50
    expected = stock_close.iloc[row + 5] / stock_close.iloc[row] - 1

    assert result.loc[row, "target_5d_return"] == pytest.approx(expected)


def test_last_five_rows_have_no_forward_return_target() -> None:
    stock_close, spy_close = make_price_series()

    result = build_features_for_ticker(
        ticker="AAPL",
        sector="Technology",
        close=stock_close,
        spy_close=spy_close,
    )

    assert result["target_5d_return"].tail(5).isna().all()


def test_future_price_changes_do_not_modify_current_features() -> None:
    stock_close, spy_close = make_price_series()

    cutoff_position = 60
    altered_close = stock_close.copy()

    altered_close.iloc[cutoff_position + 1 :] *= 3.0

    original = build_features_for_ticker(
        ticker="AAPL",
        sector="Technology",
        close=stock_close,
        spy_close=spy_close,
    )

    altered = build_features_for_ticker(
        ticker="AAPL",
        sector="Technology",
        close=altered_close,
        spy_close=spy_close,
    )

    pd.testing.assert_series_equal(
        original.loc[cutoff_position, FEATURE_COLUMNS],
        altered.loc[cutoff_position, FEATURE_COLUMNS],
        check_names=False,
    )

    assert (
        original.loc[cutoff_position, "target_5d_return"]
        != altered.loc[cutoff_position, "target_5d_return"]
    )


def test_target_label_matches_forward_return_sign() -> None:
    stock_close, spy_close = make_price_series()

    stock_close.iloc[45:51] = [
        130.0,
        129.0,
        128.0,
        127.0,
        126.0,
        100.0,
    ]

    result = build_features_for_ticker(
        ticker="AAPL",
        sector="Technology",
        close=stock_close,
        spy_close=spy_close,
    )

    row = 45

    assert result.loc[row, "target_5d_return"] < 0
    assert result.loc[row, "target_label"] == 0
