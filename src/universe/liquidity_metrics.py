from __future__ import annotations

import pandas as pd


REQUIRED_HISTORY_COLUMNS: tuple[str, ...] = (
    "date",
    "ticker",
    "close",
    "volume",
)


def calculate_liquidity_metrics(
    market_data: pd.DataFrame,
    *,
    median_window: int = 60,
) -> pd.DataFrame:
    if median_window <= 0:
        raise ValueError("median_window must be positive")

    missing = [
        column
        for column in REQUIRED_HISTORY_COLUMNS
        if column not in market_data.columns
    ]

    if missing:
        raise KeyError(
            "Missing required history columns: "
            + ", ".join(missing)
        )

    frame = market_data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["ticker"] = (
        frame["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    frame["close"] = pd.to_numeric(
        frame["close"],
        errors="coerce",
    )
    frame["volume"] = pd.to_numeric(
        frame["volume"],
        errors="coerce",
    )

    if frame[["close", "volume"]].isna().any().any():
        raise ValueError(
            "Market history contains invalid close or volume values."
        )

    if (
        (frame["close"] <= 0)
        | (frame["volume"] < 0)
    ).any():
        raise ValueError(
            "Market history contains non-positive prices "
            "or negative volume."
        )

    duplicated = frame.duplicated(
        subset=["date", "ticker"],
        keep=False,
    )

    if duplicated.any():
        raise ValueError(
            "Market history contains duplicate date/ticker rows."
        )

    frame = frame.sort_values(["ticker", "date"])
    frame["dollar_volume"] = frame["close"] * frame["volume"]

    records: list[dict[str, object]] = []

    for ticker, ticker_frame in frame.groupby(
        "ticker",
        sort=True,
    ):
        ticker_frame = ticker_frame.sort_values("date")
        recent = ticker_frame.tail(median_window)

        records.append(
            {
                "ticker": ticker,
                "last_date": ticker_frame["date"].iloc[-1],
                "last_price": float(
                    ticker_frame["close"].iloc[-1]
                ),
                "median_dollar_volume": float(
                    recent["dollar_volume"].median()
                ),
                "history_days": int(
                    ticker_frame["date"].nunique()
                ),
                "first_date": ticker_frame["date"].iloc[0],
            }
        )

    return pd.DataFrame(records).sort_values(
        "ticker"
    ).reset_index(drop=True)


def attach_liquidity_metrics(
    candidates: pd.DataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    if "ticker" not in candidates.columns:
        raise KeyError("Candidate data requires a ticker column")

    if "ticker" not in metrics.columns:
        raise KeyError("Metrics data requires a ticker column")

    candidate_frame = candidates.copy()
    metric_frame = metrics.copy()

    candidate_frame["ticker"] = (
        candidate_frame["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    metric_frame["ticker"] = (
        metric_frame["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if candidate_frame["ticker"].duplicated().any():
        raise ValueError(
            "Candidate data contains duplicate tickers."
        )

    if metric_frame["ticker"].duplicated().any():
        raise ValueError(
            "Liquidity metrics contain duplicate tickers."
        )

    return candidate_frame.merge(
        metric_frame,
        on="ticker",
        how="left",
        validate="one_to_one",
    )
