import pandas as pd
import pytest

from src.backtesting.walkforward_rank_backtest import (
    select_buffered_holdings,
)


def ranked_day(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": tickers,
            "score": list(
                range(len(tickers), 0, -1)
            ),
        }
    )


def test_buffer_retains_existing_holdings() -> None:
    day = ranked_day(
        [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
        ]
    )

    selected = select_buffered_holdings(
        ranked_day=day,
        previous_holdings=["K", "A", "B"],
        top_n=3,
        buffer_rank=12,
    )

    assert selected == ["K", "A", "B"]


def test_buffer_replaces_fallen_holding() -> None:
    day = ranked_day(
        [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
        ]
    )

    selected = select_buffered_holdings(
        ranked_day=day,
        previous_holdings=["Z", "B"],
        top_n=3,
        buffer_rank=4,
    )

    assert selected == ["B", "A", "C"]


def test_empty_ranked_day_returns_empty_list() -> None:
    day = pd.DataFrame(columns=["ticker", "score"])

    assert (
        select_buffered_holdings(
            ranked_day=day,
            previous_holdings=["A"],
            top_n=3,
            buffer_rank=5,
        )
        == []
    )


def test_invalid_buffer_rank_raises() -> None:
    day = ranked_day(["A", "B", "C"])

    with pytest.raises(ValueError):
        select_buffered_holdings(
            ranked_day=day,
            previous_holdings=[],
            top_n=3,
            buffer_rank=2,
        )


def test_invalid_top_n_raises() -> None:
    day = ranked_day(["A", "B", "C"])

    with pytest.raises(ValueError):
        select_buffered_holdings(
            ranked_day=day,
            previous_holdings=[],
            top_n=0,
            buffer_rank=3,
        )
