import pandas as pd
import pytest

from src.backtesting.walkforward_rank_backtest import split_train_test_by_year


def make_panel() -> pd.DataFrame:
    dates = pd.bdate_range("2024-12-16", "2025-01-15")
    rows = []

    for date in dates:
        for ticker in ("AAPL", "MSFT"):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "target_5d_return": 0.01,
                }
            )

    return pd.DataFrame(rows)


def test_split_purges_last_five_training_sessions() -> None:
    df = make_panel()

    train_df, test_df = split_train_test_by_year(
        df,
        test_year=2025,
        purge_sessions=5,
    )

    all_training_dates = (
        df.loc[df["date"].dt.year < 2025, "date"]
        .drop_duplicates()
        .sort_values()
    )

    expected_last_safe_date = all_training_dates.iloc[-6]

    assert train_df["date"].max() == expected_last_safe_date
    assert test_df["date"].min() == pd.Timestamp("2025-01-01")
    assert train_df["date"].dt.year.max() == 2024
    assert test_df["date"].dt.year.min() == 2025


def test_split_removes_exactly_five_unique_sessions() -> None:
    df = make_panel()

    unpurged_train, _ = split_train_test_by_year(
        df,
        test_year=2025,
        purge_sessions=0,
    )

    purged_train, _ = split_train_test_by_year(
        df,
        test_year=2025,
        purge_sessions=5,
    )

    removed_dates = set(unpurged_train["date"]) - set(purged_train["date"])

    assert len(removed_dates) == 5


def test_split_preserves_all_cross_sectional_rows_on_safe_dates() -> None:
    df = make_panel()

    train_df, _ = split_train_test_by_year(
        df,
        test_year=2025,
        purge_sessions=5,
    )

    rows_per_date = train_df.groupby("date")["ticker"].nunique()

    assert (rows_per_date == 2).all()


def test_negative_purge_is_rejected() -> None:
    df = make_panel()

    with pytest.raises(ValueError, match="non-negative"):
        split_train_test_by_year(
            df,
            test_year=2025,
            purge_sessions=-1,
        )


def test_insufficient_history_returns_empty_training_set() -> None:
    df = make_panel()
    training_sessions = df.loc[
        df["date"].dt.year < 2025,
        "date",
    ].nunique()

    train_df, test_df = split_train_test_by_year(
        df,
        test_year=2025,
        purge_sessions=training_sessions,
    )

    assert train_df.empty
    assert not test_df.empty
