import pandas as pd

from scripts.build_us_equity_candidates import (
    build_candidates,
    looks_like_common_equity,
    normalize_yahoo_symbol,
)


def make_directory() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "nasdaq_traded": "Y",
                "symbol": "AAPL",
                "security_name": "Apple Inc. Common Stock",
                "listing_exchange": "Q",
                "etf": "N",
                "test_issue": "N",
                "financial_status": "N",
            },
            {
                "nasdaq_traded": "Y",
                "symbol": "SPY",
                "security_name": "SPDR S&P 500 ETF Trust",
                "listing_exchange": "P",
                "etf": "Y",
                "test_issue": "N",
                "financial_status": "N",
            },
            {
                "nasdaq_traded": "Y",
                "symbol": "TEST",
                "security_name": "Test Security",
                "listing_exchange": "Q",
                "etf": "N",
                "test_issue": "Y",
                "financial_status": "N",
            },
            {
                "nasdaq_traded": "Y",
                "symbol": "ABCW",
                "security_name": "ABC Corporation Warrants",
                "listing_exchange": "N",
                "etf": "N",
                "test_issue": "N",
                "financial_status": "N",
            },
        ]
    )


def test_common_equity_name_filter() -> None:
    assert looks_like_common_equity(
        "Apple Inc. Common Stock"
    )
    assert not looks_like_common_equity(
        "ABC Corporation Warrants"
    )
    assert not looks_like_common_equity(
        "Example Preferred Stock"
    )


def test_yahoo_symbol_normalization() -> None:
    assert normalize_yahoo_symbol("BRK.B") == "BRK-B"
    assert normalize_yahoo_symbol("ABC") == "ABC"


def test_candidate_builder_removes_non_equities() -> None:
    result = build_candidates(make_directory())

    assert list(result["ticker"]) == ["AAPL"]
    assert result.iloc[0]["exchange"] == "NASDAQ"
    assert result.iloc[0]["security_type"] == "COMMON_STOCK"
