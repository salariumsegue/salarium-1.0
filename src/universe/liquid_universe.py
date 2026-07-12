from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


REQUIRED_UNIVERSE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "security_type",
    "exchange",
    "last_price",
    "median_dollar_volume",
    "history_days",
    "is_active",
)


@dataclass(frozen=True)
class UniverseRules:
    minimum_price: float = 5.0
    minimum_median_dollar_volume: float = 5_000_000.0
    minimum_history_days: int = 504
    allowed_exchanges: tuple[str, ...] = (
        "NYSE",
        "NASDAQ",
        "NYSEARCA",
    )
    allowed_security_types: tuple[str, ...] = (
        "COMMON_STOCK",
    )
    maximum_size: int = 500


def normalize_universe_candidates(
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    result = candidates.copy()

    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]

    aliases = {
        "symbol": "ticker",
        "type": "security_type",
        "price": "last_price",
        "median_dollar_volume_20d": "median_dollar_volume",
        "trading_history_days": "history_days",
        "active": "is_active",
    }

    result = result.rename(columns=aliases)

    missing = [
        column
        for column in REQUIRED_UNIVERSE_COLUMNS
        if column not in result.columns
    ]

    if missing:
        raise KeyError(
            "Missing required universe columns: "
            + ", ".join(missing)
        )

    result["ticker"] = (
        result["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["security_type"] = (
        result["security_type"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["exchange"] = (
        result["exchange"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    for column in (
        "last_price",
        "median_dollar_volume",
        "history_days",
    ):
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    result["is_active"] = result["is_active"].map(
        lambda value: (
            value
            if isinstance(value, bool)
            else str(value).strip().lower()
            in {"1", "true", "yes", "y"}
        )
    )

    if result["ticker"].eq("").any():
        raise ValueError("Universe contains an empty ticker.")

    if result["ticker"].duplicated().any():
        duplicates = sorted(
            result.loc[
                result["ticker"].duplicated(keep=False),
                "ticker",
            ].unique()
        )
        raise ValueError(
            "Universe contains duplicate tickers: "
            + ", ".join(duplicates)
        )

    numeric_columns = [
        "last_price",
        "median_dollar_volume",
        "history_days",
    ]

    if result[numeric_columns].isna().any().any():
        raise ValueError(
            "Universe contains invalid numeric values."
        )

    return result.reset_index(drop=True)


def select_liquid_universe(
    candidates: pd.DataFrame,
    rules: UniverseRules | None = None,
) -> pd.DataFrame:
    active_rules = rules or UniverseRules()
    normalized = normalize_universe_candidates(candidates)

    if active_rules.maximum_size <= 0:
        raise ValueError("maximum_size must be positive")

    eligible = normalized[
        normalized["is_active"]
        & normalized["security_type"].isin(
            active_rules.allowed_security_types
        )
        & normalized["exchange"].isin(
            active_rules.allowed_exchanges
        )
        & normalized["last_price"].ge(
            active_rules.minimum_price
        )
        & normalized["median_dollar_volume"].ge(
            active_rules.minimum_median_dollar_volume
        )
        & normalized["history_days"].ge(
            active_rules.minimum_history_days
        )
    ].copy()

    eligible["liquidity_rank"] = (
        eligible["median_dollar_volume"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    eligible = (
        eligible.sort_values(
            [
                "median_dollar_volume",
                "history_days",
                "ticker",
            ],
            ascending=[False, False, True],
        )
        .head(active_rules.maximum_size)
        .reset_index(drop=True)
    )

    eligible["universe_rank"] = range(
        1,
        len(eligible) + 1,
    )

    return eligible


def explain_exclusions(
    candidates: pd.DataFrame,
    rules: UniverseRules | None = None,
) -> pd.DataFrame:
    active_rules = rules or UniverseRules()
    normalized = normalize_universe_candidates(candidates)

    records: list[dict[str, object]] = []

    for row in normalized.to_dict(orient="records"):
        reasons: list[str] = []

        if not row["is_active"]:
            reasons.append("inactive")

        if row["security_type"] not in (
            active_rules.allowed_security_types
        ):
            reasons.append("security_type")

        if row["exchange"] not in active_rules.allowed_exchanges:
            reasons.append("exchange")

        if row["last_price"] < active_rules.minimum_price:
            reasons.append("price")

        if (
            row["median_dollar_volume"]
            < active_rules.minimum_median_dollar_volume
        ):
            reasons.append("liquidity")

        if row["history_days"] < active_rules.minimum_history_days:
            reasons.append("history")

        records.append(
            {
                "ticker": row["ticker"],
                "eligible": not reasons,
                "exclusion_reasons": ",".join(reasons),
            }
        )

    return pd.DataFrame(records)
