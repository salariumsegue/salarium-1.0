from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


REQUIRED_HISTORY_COLUMNS: tuple[str, ...] = (
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


SECURITY_FEATURE_COLUMNS: tuple[str, ...] = (
    "return_1d",
    "return_5d",
    "volume_change_1d",
    "high_low_spread",
    "open_close_spread",
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "ma20",
    "ma50",
    "price_vs_ma20",
    "price_vs_ma50",
    "rsi_14d",
)


MODEL_FEATURE_COLUMNS: tuple[str, ...] = (
    *SECURITY_FEATURE_COLUMNS,
    "relative_strength",
)


def compute_rsi(
    price: pd.Series,
    window: int = 14,
) -> pd.Series:
    if window <= 0:
        raise ValueError("window must be positive")

    delta = price.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(
        window,
        min_periods=window,
    ).mean()

    average_loss = losses.rolling(
        window,
        min_periods=window,
    ).mean()

    relative_strength = (
        average_gain
        / average_loss.replace(0, np.nan)
    )

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    rising_without_losses = (
        average_gain.gt(0)
        & average_loss.eq(0)
    )

    unchanged = (
        average_gain.eq(0)
        & average_loss.eq(0)
    )

    rsi = rsi.mask(
        rising_without_losses,
        100.0,
    )

    rsi = rsi.mask(
        unchanged,
        50.0,
    )

    return rsi


def normalize_price_history(
    frame: pd.DataFrame,
    *,
    ticker: str | None = None,
) -> pd.DataFrame:
    result = frame.copy()

    result.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for column in result.columns
    ]

    result = result.rename(
        columns={
            "datetime": "date",
            "index": "date",
            "symbol": "ticker",
            "adjclose": "adj_close",
            "adjusted_close": "adj_close",
        }
    )

    normalized_ticker = (
        ticker.strip().upper()
        if ticker is not None
        else None
    )

    if "ticker" not in result.columns:
        if normalized_ticker is None:
            raise KeyError(
                "Price history requires a ticker column "
                "or explicit ticker argument."
            )

        result["ticker"] = normalized_ticker

    result["ticker"] = (
        result["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if normalized_ticker is not None:
        observed = set(
            result["ticker"].dropna()
        )

        if observed and observed != {
            normalized_ticker
        }:
            raise ValueError(
                "Price-history ticker does not match "
                "the requested canonical ticker."
            )

        result["ticker"] = normalized_ticker

    missing = [
        column
        for column in REQUIRED_HISTORY_COLUMNS
        if column not in result.columns
    ]

    if missing:
        raise KeyError(
            "Price history is missing columns: "
            + ", ".join(missing)
        )

    parsed_dates = pd.to_datetime(
        result["date"],
        errors="raise",
        utc=True,
    )

    result["date"] = (
        parsed_dates.dt.tz_convert(None)
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    if "adj_close" in result.columns:
        numeric_columns.append(
            "adj_close"
        )

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    if result[numeric_columns].isna().any().any():
        raise ValueError(
            "Price history contains invalid or "
            "missing numeric values."
        )

    if "adj_close" not in result.columns:
        result["adj_close"] = result["close"]

    duplicated = result.duplicated(
        subset=["date", "ticker"],
        keep=False,
    )

    if duplicated.any():
        raise ValueError(
            "Price history contains duplicate "
            "date/ticker rows."
        )

    invalid = (
        result["open"].le(0)
        | result["high"].le(0)
        | result["low"].le(0)
        | result["close"].le(0)
        | result["adj_close"].le(0)
        | result["volume"].lt(0)
        | result["high"].lt(result["low"])
    )

    if invalid.any():
        raise ValueError(
            "Price history contains invalid OHLCV values."
        )

    return (
        result.sort_values(
            ["ticker", "date"]
        )
        .reset_index(drop=True)
    )


def build_security_features(
    history: pd.DataFrame,
    *,
    ticker: str | None = None,
    target_horizon_days: int = 5,
) -> pd.DataFrame:
    if target_horizon_days <= 0:
        raise ValueError(
            "target_horizon_days must be positive"
        )

    result = normalize_price_history(
        history,
        ticker=ticker,
    )

    if result["ticker"].nunique() != 1:
        raise ValueError(
            "build_security_features expects "
            "exactly one ticker."
        )

    adjusted_price = result[
        "adj_close"
    ]

    return_1d = adjusted_price.pct_change(
        fill_method=None
    )

    momentum_5d = adjusted_price.pct_change(
        5,
        fill_method=None,
    )

    momentum_20d = adjusted_price.pct_change(
        20,
        fill_method=None,
    )

    result["return_1d"] = return_1d
    result["return_5d"] = momentum_5d

    result["volume_change_1d"] = (
        result["volume"].pct_change(
            fill_method=None
        )
    )

    result["high_low_spread"] = (
        result["high"] - result["low"]
    ) / result["close"]

    result["open_close_spread"] = (
        result["close"] - result["open"]
    ) / result["open"]

    result["momentum_5d"] = momentum_5d
    result["momentum_20d"] = momentum_20d

    result["volatility_20d"] = (
        return_1d
        .rolling(
            20,
            min_periods=20,
        )
        .std()
    )

    result["ma20"] = (
        adjusted_price
        .rolling(
            20,
            min_periods=20,
        )
        .mean()
    )

    result["ma50"] = (
        adjusted_price
        .rolling(
            50,
            min_periods=50,
        )
        .mean()
    )

    result["price_vs_ma20"] = (
        adjusted_price / result["ma20"] - 1
    )

    result["price_vs_ma50"] = (
        adjusted_price / result["ma50"] - 1
    )

    result["rsi_14d"] = compute_rsi(
        adjusted_price,
        window=14,
    )

    future_adjusted_price = (
        adjusted_price.shift(
            -target_horizon_days
        )
    )

    target_return = (
        future_adjusted_price
        / adjusted_price
        - 1
    )

    result["target_5d_return"] = (
        target_return
    )

    target_label = pd.Series(
        pd.NA,
        index=result.index,
        dtype="Int8",
    )

    valid_target = target_return.notna()

    target_label.loc[valid_target] = (
        target_return.loc[
            valid_target
        ]
        .gt(0)
        .astype("int8")
    )

    result["target_label"] = target_label

    numeric_columns = result.select_dtypes(
        include=["number"]
    ).columns

    result[numeric_columns] = (
        result[numeric_columns]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )

    return result


def calculate_daily_momentum_mean(
    panel: pd.DataFrame,
) -> pd.Series:
    required = {
        "date",
        "momentum_20d",
    }

    missing = sorted(
        required - set(panel.columns)
    )

    if missing:
        raise KeyError(
            "Panel is missing columns: "
            + ", ".join(missing)
        )

    return (
        panel.groupby(
            "date",
            sort=True,
        )["momentum_20d"]
        .mean()
    )


def add_cross_sectional_relative_strength(
    panel: pd.DataFrame,
    *,
    daily_momentum_mean: (
        pd.Series
        | Mapping[pd.Timestamp, float]
        | None
    ) = None,
) -> pd.DataFrame:
    result = panel.copy()

    if daily_momentum_mean is None:
        momentum_mean = (
            calculate_daily_momentum_mean(
                result
            )
        )
    else:
        momentum_mean = pd.Series(
            daily_momentum_mean
        )

    result["relative_strength"] = (
        result["momentum_20d"]
        - result["date"].map(
            momentum_mean
        )
    )

    return result


def filter_model_safe_rows(
    panel: pd.DataFrame,
) -> pd.DataFrame:
    result = panel.copy()

    required_columns = [
        "date",
        "ticker",
        "target_5d_return",
        *MODEL_FEATURE_COLUMNS,
    ]

    missing = [
        column
        for column in required_columns
        if column not in result.columns
    ]

    if missing:
        raise KeyError(
            "Model panel is missing columns: "
            + ", ".join(missing)
        )

    numeric_columns = result.select_dtypes(
        include=["number"]
    ).columns

    result[numeric_columns] = (
        result[numeric_columns]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )

    result = result.dropna(
        subset=required_columns
    )

    return (
        result.sort_values(
            ["ticker", "date"]
        )
        .reset_index(drop=True)
    )
