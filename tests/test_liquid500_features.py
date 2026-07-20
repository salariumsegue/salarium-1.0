import numpy as np
import pandas as pd
import pytest

from src.features.liquid500_features import (
    MODEL_FEATURE_COLUMNS,
    SECURITY_FEATURE_COLUMNS,
    add_cross_sectional_relative_strength,
    build_security_features,
    filter_model_safe_rows,
    normalize_price_history,
)


def make_history(
    ticker: str = "AAPL",
    *,
    periods: int = 90,
    slope: float = 0.5,
) -> pd.DataFrame:
    dates = pd.bdate_range(
        "2025-01-02",
        periods=periods,
    )

    adjusted_close = (
        100.0
        + np.arange(periods) * slope
    )

    return pd.DataFrame(
        {
            "Date": dates,
            "Ticker": ticker.lower(),
            "Open": adjusted_close * 0.995,
            "High": adjusted_close * 1.01,
            "Low": adjusted_close * 0.99,
            "Close": adjusted_close,
            "Adj Close": adjusted_close,
            "Volume": (
                1_000_000
                + np.arange(periods) * 1_000
            ),
        }
    )


def test_history_normalization_is_canonical() -> None:
    result = normalize_price_history(
        make_history()
    )

    assert result["ticker"].unique().tolist() == [
        "AAPL"
    ]

    assert pd.api.types.is_datetime64_any_dtype(
        result["date"]
    )

    assert "adj_close" in result.columns


def test_target_uses_five_day_forward_adjusted_return() -> None:
    history = make_history()
    result = build_security_features(
        history
    )

    row = 50

    expected = (
        result.loc[
            row + 5,
            "adj_close",
        ]
        / result.loc[row, "adj_close"]
        - 1
    )

    assert result.loc[
        row,
        "target_5d_return",
    ] == pytest.approx(expected)


def test_last_five_rows_have_no_target() -> None:
    result = build_security_features(
        make_history()
    )

    assert (
        result["target_5d_return"]
        .tail(5)
        .isna()
        .all()
    )

    assert (
        result["target_label"]
        .tail(5)
        .isna()
        .all()
    )


def test_future_changes_do_not_modify_current_features() -> None:
    history = make_history()
    altered = history.copy()

    cutoff = 60

    for column in (
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
    ):
        altered.loc[
            cutoff + 1 :,
            column,
        ] *= 3.0

    original_features = (
        build_security_features(
            history
        )
    )

    altered_features = (
        build_security_features(
            altered
        )
    )

    pd.testing.assert_series_equal(
        original_features.loc[
            cutoff,
            list(SECURITY_FEATURE_COLUMNS),
        ],
        altered_features.loc[
            cutoff,
            list(SECURITY_FEATURE_COLUMNS),
        ],
        check_names=False,
    )

    assert (
        original_features.loc[
            cutoff,
            "target_5d_return",
        ]
        != altered_features.loc[
            cutoff,
            "target_5d_return",
        ]
    )


def test_relative_strength_is_cross_sectionally_centered() -> None:
    aapl = build_security_features(
        make_history(
            "AAPL",
            slope=0.5,
        )
    )

    msft = build_security_features(
        make_history(
            "MSFT",
            slope=1.0,
        )
    )

    panel = pd.concat(
        [aapl, msft],
        ignore_index=True,
    )

    result = (
        add_cross_sectional_relative_strength(
            panel
        )
    )

    daily_means = (
        result.dropna(
            subset=["relative_strength"]
        )
        .groupby("date")[
            "relative_strength"
        ]
        .mean()
    )

    assert np.allclose(
        daily_means.to_numpy(),
        0.0,
        atol=1e-12,
    )


def test_model_safe_filter_removes_warmup_and_tail() -> None:
    aapl = build_security_features(
        make_history("AAPL")
    )

    msft = build_security_features(
        make_history(
            "MSFT",
            slope=0.8,
        )
    )

    panel = pd.concat(
        [aapl, msft],
        ignore_index=True,
    )

    panel = (
        add_cross_sectional_relative_strength(
            panel
        )
    )

    result = filter_model_safe_rows(
        panel
    )

    assert not result.empty

    assert not result[
        list(MODEL_FEATURE_COLUMNS)
        + ["target_5d_return"]
    ].isna().any().any()

    assert result["ticker"].nunique() == 2
