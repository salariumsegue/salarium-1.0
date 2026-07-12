import pandas as pd
import pytest

from src.universe.liquidity_metrics import (
    attach_liquidity_metrics,
    calculate_liquidity_metrics,
)


def make_history() -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=4)

    rows = []

    for ticker, base_price, volume in (
        ("AAPL", 100.0, 1_000),
        ("MSFT", 200.0, 2_000),
    ):
        for offset, current_date in enumerate(dates):
            rows.append(
                {
                    "date": current_date,
                    "ticker": ticker,
                    "close": base_price + offset,
                    "volume": volume,
                }
            )

    return pd.DataFrame(rows)


def test_calculate_liquidity_metrics_returns_one_row_per_ticker() -> None:
    result = calculate_liquidity_metrics(
        make_history(),
        median_window=3,
    )

    assert list(result["ticker"]) == ["AAPL", "MSFT"]
    assert len(result) == 2
    assert set(result["history_days"]) == {4}


def test_last_price_uses_latest_available_date() -> None:
    result = calculate_liquidity_metrics(
        make_history(),
        median_window=3,
    ).set_index("ticker")

    assert result.loc["AAPL", "last_price"] == pytest.approx(
        103.0
    )
    assert result.loc["MSFT", "last_price"] == pytest.approx(
        203.0
    )


def test_median_dollar_volume_uses_recent_window() -> None:
    result = calculate_liquidity_metrics(
        make_history(),
        median_window=3,
    ).set_index("ticker")

    assert result.loc[
        "AAPL",
        "median_dollar_volume",
    ] == pytest.approx(102_000.0)


def test_invalid_median_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        calculate_liquidity_metrics(
            make_history(),
            median_window=0,
        )


def test_duplicate_history_rows_are_rejected() -> None:
    frame = make_history()
    frame = pd.concat(
        [frame, frame.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate"):
        calculate_liquidity_metrics(frame)


def test_attach_metrics_preserves_candidate_metadata() -> None:
    candidates = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "security_type": [
                "COMMON_STOCK",
                "COMMON_STOCK",
            ],
            "exchange": ["NASDAQ", "NASDAQ"],
            "is_active": [True, True],
        }
    )

    metrics = calculate_liquidity_metrics(
        make_history()
    )

    result = attach_liquidity_metrics(
        candidates,
        metrics,
    )

    assert "security_type" in result.columns
    assert "median_dollar_volume" in result.columns
    assert len(result) == 2
