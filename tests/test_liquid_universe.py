import pandas as pd
import pytest

from src.universe.liquid_universe import (
    UniverseRules,
    explain_exclusions,
    normalize_universe_candidates,
    select_liquid_universe,
)


def make_candidates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "last_price": 200.0,
                "median_dollar_volume": 1_000_000_000,
                "history_days": 3000,
                "is_active": True,
            },
            {
                "ticker": "MSFT",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "last_price": 400.0,
                "median_dollar_volume": 900_000_000,
                "history_days": 3000,
                "is_active": True,
            },
            {
                "ticker": "PENNY",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "last_price": 1.50,
                "median_dollar_volume": 10_000_000,
                "history_days": 1000,
                "is_active": True,
            },
            {
                "ticker": "ILLIQ",
                "security_type": "COMMON_STOCK",
                "exchange": "NYSE",
                "last_price": 20.0,
                "median_dollar_volume": 100_000,
                "history_days": 1000,
                "is_active": True,
            },
            {
                "ticker": "SPY",
                "security_type": "ETF",
                "exchange": "NYSEARCA",
                "last_price": 500.0,
                "median_dollar_volume": 5_000_000_000,
                "history_days": 3000,
                "is_active": True,
            },
        ]
    )


def test_normalization_standardizes_text_fields() -> None:
    frame = make_candidates()
    frame.loc[0, "ticker"] = " aapl "
    frame.loc[0, "security_type"] = "common_stock"
    frame.loc[0, "exchange"] = "nasdaq"

    result = normalize_universe_candidates(frame)

    assert result.loc[0, "ticker"] == "AAPL"
    assert result.loc[0, "security_type"] == "COMMON_STOCK"
    assert result.loc[0, "exchange"] == "NASDAQ"


def test_duplicate_tickers_are_rejected() -> None:
    frame = pd.concat(
        [make_candidates(), make_candidates().iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate"):
        normalize_universe_candidates(frame)


def test_liquid_universe_filters_ineligible_assets() -> None:
    result = select_liquid_universe(make_candidates())

    assert list(result["ticker"]) == ["AAPL", "MSFT"]
    assert list(result["universe_rank"]) == [1, 2]


def test_universe_is_sorted_by_liquidity() -> None:
    result = select_liquid_universe(make_candidates())

    assert result.iloc[0]["median_dollar_volume"] >= (
        result.iloc[1]["median_dollar_volume"]
    )


def test_maximum_size_is_enforced() -> None:
    result = select_liquid_universe(
        make_candidates(),
        UniverseRules(maximum_size=1),
    )

    assert len(result) == 1
    assert result.iloc[0]["ticker"] == "AAPL"


def test_exclusion_reasons_are_explained() -> None:
    result = explain_exclusions(make_candidates())
    result = result.set_index("ticker")

    assert result.loc["AAPL", "eligible"]
    assert "price" in result.loc[
        "PENNY",
        "exclusion_reasons",
    ]
    assert "liquidity" in result.loc[
        "ILLIQ",
        "exclusion_reasons",
    ]
    assert "security_type" in result.loc[
        "SPY",
        "exclusion_reasons",
    ]


def test_invalid_maximum_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        select_liquid_universe(
            make_candidates(),
            UniverseRules(maximum_size=0),
        )
