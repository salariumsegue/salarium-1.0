from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


DEFAULT_RISK_EXPOSURE = {
    "risk_on": 1.00,
    "neutral": 0.75,
    "risk_off": 0.45,
}


def select_buffered_holdings(
    ranked_tickers: Sequence[str],
    previous_holdings: Sequence[str],
    *,
    top_n: int = 10,
    buffer_rank: int = 15,
) -> list[str]:
    if top_n <= 0:
        raise ValueError("top_n must be positive")

    if buffer_rank < top_n:
        raise ValueError(
            "buffer_rank must be at least top_n"
        )

    ranked = list(dict.fromkeys(ranked_tickers))

    if not ranked:
        return []

    eligible = set(ranked[:buffer_rank])

    selected = [
        ticker
        for ticker in previous_holdings
        if ticker in eligible
    ][:top_n]

    for ticker in ranked:
        if len(selected) == top_n:
            break

        if ticker not in selected:
            selected.append(ticker)

    return selected


def equal_weights(
    tickers: Sequence[str],
    *,
    exposure: float = 1.0,
) -> dict[str, float]:
    names = list(dict.fromkeys(tickers))

    if not 0 <= exposure <= 1:
        raise ValueError(
            "exposure must be between 0 and 1"
        )

    if not names or exposure == 0:
        return {}

    weight = exposure / len(names)

    return {
        ticker: weight
        for ticker in names
    }


def capped_inverse_volatility_weights(
    volatilities: pd.Series,
    *,
    exposure: float = 1.0,
    maximum_weight: float = 0.18,
    minimum_volatility: float = 0.005,
) -> dict[str, float]:
    if not 0 <= exposure <= 1:
        raise ValueError(
            "exposure must be between 0 and 1"
        )

    if not 0 < maximum_weight <= 1:
        raise ValueError(
            "maximum_weight must be between 0 and 1"
        )

    clean = pd.to_numeric(
        volatilities,
        errors="coerce",
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if clean.empty or exposure == 0:
        return {}

    clean = clean.clip(
        lower=minimum_volatility
    )

    if (
        len(clean) * maximum_weight
        + 1e-12
        < exposure
    ):
        raise ValueError(
            "maximum_weight is too small for the "
            "requested exposure"
        )

    inverse_volatility = 1.0 / clean

    remaining = list(
        inverse_volatility.index
    )
    remaining_exposure = float(exposure)
    weights: dict[str, float] = {}

    while remaining:
        denominator = float(
            inverse_volatility.loc[
                remaining
            ].sum()
        )

        proposed = {
            ticker: (
                remaining_exposure
                * float(
                    inverse_volatility.loc[
                        ticker
                    ]
                )
                / denominator
            )
            for ticker in remaining
        }

        capped = [
            ticker
            for ticker, weight
            in proposed.items()
            if weight > maximum_weight
        ]

        if not capped:
            weights.update(proposed)
            break

        for ticker in capped:
            weights[ticker] = maximum_weight
            remaining_exposure -= maximum_weight
            remaining.remove(ticker)

        if remaining_exposure <= 1e-12:
            break

    return {
        ticker: float(weight)
        for ticker, weight
        in weights.items()
        if weight > 1e-12
    }


def calculate_turnover(
    previous_weights: Mapping[str, float],
    target_weights: Mapping[str, float],
) -> float:
    tickers = (
        set(previous_weights)
        | set(target_weights)
    )

    return float(
        sum(
            abs(
                float(
                    target_weights.get(
                        ticker,
                        0.0,
                    )
                )
                - float(
                    previous_weights.get(
                        ticker,
                        0.0,
                    )
                )
            )
            for ticker in tickers
        )
    )


def cap_turnover(
    previous_weights: Mapping[str, float],
    target_weights: Mapping[str, float],
    *,
    maximum_turnover: float,
) -> tuple[dict[str, float], float, float]:
    if maximum_turnover <= 0:
        raise ValueError(
            "maximum_turnover must be positive"
        )

    raw_turnover = calculate_turnover(
        previous_weights,
        target_weights,
    )

    if raw_turnover <= maximum_turnover:
        return (
            dict(target_weights),
            raw_turnover,
            1.0,
        )

    blend = (
        maximum_turnover
        / raw_turnover
    )

    tickers = (
        set(previous_weights)
        | set(target_weights)
    )

    blended_weights = {
        ticker: (
            float(
                previous_weights.get(
                    ticker,
                    0.0,
                )
            )
            + blend
            * (
                float(
                    target_weights.get(
                        ticker,
                        0.0,
                    )
                )
                - float(
                    previous_weights.get(
                        ticker,
                        0.0,
                    )
                )
            )
        )
        for ticker in tickers
    }

    blended_weights = {
        ticker: weight
        for ticker, weight
        in blended_weights.items()
        if abs(weight) > 1e-12
    }

    actual_turnover = calculate_turnover(
        previous_weights,
        blended_weights,
    )

    return (
        blended_weights,
        actual_turnover,
        blend,
    )


def resolve_risk_exposure(
    risk_state: str,
    *,
    regime_is_confident: bool,
) -> float:
    normalized = (
        str(risk_state)
        .strip()
        .lower()
    )

    exposure = DEFAULT_RISK_EXPOSURE.get(
        normalized,
        DEFAULT_RISK_EXPOSURE[
            "neutral"
        ],
    )

    if not regime_is_confident:
        return min(
            exposure,
            DEFAULT_RISK_EXPOSURE[
                "neutral"
            ],
        )

    return float(exposure)


def weight_diagnostics(
    weights: Mapping[str, float],
) -> dict[str, float]:
    if not weights:
        return {
            "gross_exposure": 0.0,
            "maximum_weight": 0.0,
            "herfindahl_index": 0.0,
        }

    values = np.asarray(
        list(weights.values()),
        dtype=float,
    )

    return {
        "gross_exposure": float(
            values.sum()
        ),
        "maximum_weight": float(
            values.max()
        ),
        "herfindahl_index": float(
            np.square(values).sum()
        ),
    }
