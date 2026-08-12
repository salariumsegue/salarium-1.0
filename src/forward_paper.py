from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

from src.features.liquid500_features import (
    add_cross_sectional_relative_strength,
    build_security_features,
)
from src.research.feature_policy import CORE_TECHNICAL_FEATURES


LEDGER_COLUMNS: tuple[str, ...] = (
    "observation_number",
    "rebalance_date",
    "prior_rebalance_date",
    "source_snapshot_generated_at_utc",
    "source_snapshot_sha256",
    "baseline_equity_exposure",
    "shadow_equity_exposure",
    "cash_weight",
    "paper_nav_before",
    "paper_nav_after",
    "high_water_mark_after",
    "equity_return_contribution",
    "cash_return_contribution",
    "turnover",
    "modeled_cost",
    "net_return",
    "drawdown_after_rebalance",
    "status",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def atomic_json_dump(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def normalize_history(
    history: pd.DataFrame,
    symbol_to_ticker: Mapping[str, str],
) -> pd.DataFrame:
    result = history.copy()
    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]
    if "ticker" not in result.columns or "date" not in result.columns:
        raise KeyError("Forward market data requires ticker and date columns.")
    result["ticker"] = (
        result["ticker"].astype(str).str.upper().str.strip()
    )
    normalized_map = {
        str(symbol).upper().strip(): str(ticker).upper().strip()
        for symbol, ticker in symbol_to_ticker.items()
    }
    result["ticker"] = result["ticker"].map(normalized_map)
    result = result.dropna(subset=["ticker"]).copy()
    result["date"] = pd.to_datetime(
        result["date"], errors="raise", utc=True
    ).dt.tz_localize(None).dt.normalize()
    result = result.sort_values(["ticker", "date"]).reset_index(drop=True)
    if result.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Forward market data contains duplicate date/ticker rows.")
    return result


def resolve_signal_date(
    history: pd.DataFrame,
    *,
    requested_as_of: pd.Timestamp,
    expected_count: int,
    minimum_coverage: float,
    maximum_stale_calendar_days: int,
) -> tuple[pd.Timestamp, int, float]:
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be in (0, 1]")
    if expected_count <= 0:
        raise ValueError("expected_count must be positive")
    if maximum_stale_calendar_days < 0:
        raise ValueError("maximum_stale_calendar_days cannot be negative")

    requested = pd.Timestamp(requested_as_of).normalize()
    eligible = history.loc[history["date"].le(requested)].copy()
    if eligible.empty:
        raise RuntimeError("No market data exists on or before the requested date.")
    coverage_by_date = eligible.groupby("date")["ticker"].nunique().sort_index()
    minimum_names = math.ceil(expected_count * minimum_coverage)
    passing = coverage_by_date.loc[coverage_by_date.ge(minimum_names)]
    if passing.empty:
        best = int(coverage_by_date.max())
        raise RuntimeError(
            "No market date passed the universe coverage gate. "
            f"Best coverage was {best}/{expected_count}; required {minimum_names}."
        )
    signal_date = pd.Timestamp(passing.index[-1]).normalize()
    stale_days = int((requested - signal_date).days)
    if stale_days > maximum_stale_calendar_days:
        raise RuntimeError(
            f"Latest complete market date {signal_date.date()} is {stale_days} calendar "
            f"days stale; maximum is {maximum_stale_calendar_days}."
        )
    count = int(passing.iloc[-1])
    return signal_date, count, count / expected_count


def build_latest_features(
    history: pd.DataFrame,
    *,
    signal_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    price_rows: list[dict[str, Any]] = []
    normalized_date = pd.Timestamp(signal_date).normalize()

    for ticker, ticker_history in history.groupby("ticker", sort=True):
        features = build_security_features(ticker_history, ticker=str(ticker))
        latest = features.loc[features["date"].eq(normalized_date)]
        if latest.empty:
            continue
        row = latest.iloc[-1]
        record = {"date": normalized_date, "ticker": str(ticker)}
        for feature in CORE_TECHNICAL_FEATURES:
            if feature == "relative_strength":
                continue
            record[feature] = row.get(feature)
        frames.append(pd.DataFrame([record]))
        price_rows.append(
            {
                "ticker": str(ticker),
                "price": float(row["adj_close"]),
            }
        )

    if not frames:
        raise RuntimeError("No current feature rows were built.")
    feature_frame = pd.concat(frames, ignore_index=True)
    feature_frame = add_cross_sectional_relative_strength(feature_frame)
    for feature in CORE_TECHNICAL_FEATURES:
        feature_frame[feature] = pd.to_numeric(
            feature_frame[feature], errors="coerce"
        )
    feature_frame = feature_frame.replace([np.inf, -np.inf], np.nan)
    feature_frame = feature_frame.dropna(
        subset=list(CORE_TECHNICAL_FEATURES)
    ).reset_index(drop=True)
    prices = pd.DataFrame(price_rows).drop_duplicates("ticker", keep="last")
    prices = prices.loc[prices["ticker"].isin(feature_frame["ticker"])].copy()
    return feature_frame, prices


def build_daily_returns(history: pd.DataFrame) -> pd.DataFrame:
    price_column = "adj_close" if "adj_close" in history.columns else "close"
    prices = history.pivot(index="date", columns="ticker", values=price_column)
    prices = prices.sort_index().apply(pd.to_numeric, errors="coerce")
    return prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)


def load_verified_model(
    bundle_path: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_hash = sha256_file(bundle_path)
    expected_hash = str(manifest.get("model_sha256", ""))
    if actual_hash != expected_hash:
        raise RuntimeError("Forward model hash does not match its manifest.")
    bundle = joblib.load(bundle_path)
    if bundle.get("schema_version") != "1.0":
        raise RuntimeError("Unsupported forward model bundle schema.")
    if bundle.get("feature_columns") != manifest.get("feature_columns"):
        raise RuntimeError("Forward model feature contract does not match its manifest.")
    if bundle.get("target_horizon_days") != 20:
        raise RuntimeError("Forward model is not the governed 20D model.")
    return bundle, manifest


def score_features(
    features: pd.DataFrame,
    bundle: Mapping[str, Any],
) -> pd.DataFrame:
    columns = list(bundle["feature_columns"])
    if columns != list(CORE_TECHNICAL_FEATURES):
        raise RuntimeError("Forward bundle uses an unexpected feature order.")
    lower = pd.Series(bundle["lower_bounds"], dtype=float).reindex(columns)
    upper = pd.Series(bundle["upper_bounds"], dtype=float).reindex(columns)
    if lower.isna().any() or upper.isna().any():
        raise RuntimeError("Forward model clipping bounds are incomplete.")
    x = features[columns].clip(lower=lower, upper=upper, axis="columns")
    result = features[["date", "ticker", "volatility_20d"]].copy()
    result["score"] = bundle["model"].predict(x)
    result = result.sort_values(
        ["score", "ticker"], ascending=[False, True]
    ).reset_index(drop=True)
    result["rank"] = np.arange(1, len(result) + 1)
    result["score_percentile"] = result["score"].rank(
        method="average", pct=True
    )
    return result


def sessions_after(
    history: pd.DataFrame,
    *,
    prior_date: str | pd.Timestamp,
    current_date: str | pd.Timestamp,
) -> int:
    prior = pd.Timestamp(prior_date).normalize()
    current = pd.Timestamp(current_date).normalize()
    dates = pd.DatetimeIndex(history["date"].drop_duplicates()).sort_values()
    return int(((dates > prior) & (dates <= current)).sum())


def mark_to_market(
    state: Mapping[str, Any],
    current_prices: Mapping[str, float],
) -> dict[str, Any]:
    prior_prices = {
        str(key): float(value)
        for key, value in state["reference_prices"].items()
    }
    weights = {
        str(key): float(value)
        for key, value in state["weights"].items()
    }
    cash_ticker = str(state["cash_proxy"])
    required = set(weights) | {cash_ticker}
    missing = sorted(required.difference(current_prices))
    if missing:
        raise RuntimeError(
            "Current market data is missing held securities: " + ", ".join(missing)
        )

    equity_contribution = 0.0
    current_values: dict[str, float] = {}
    for ticker, weight in weights.items():
        ratio = float(current_prices[ticker]) / prior_prices[ticker]
        current_values[ticker] = weight * ratio
        equity_contribution += weight * (ratio - 1.0)
    cash_weight = float(state["cash_weight"])
    cash_ratio = float(current_prices[cash_ticker]) / prior_prices[cash_ticker]
    cash_contribution = cash_weight * (cash_ratio - 1.0)
    gross_growth = 1.0 + equity_contribution + cash_contribution
    if gross_growth <= 0:
        raise RuntimeError("Forward paper portfolio produced a non-positive NAV.")
    current_cash_value = cash_weight * cash_ratio
    drifted_weights = {
        ticker: value / gross_growth for ticker, value in current_values.items()
    }
    return {
        "equity_return_contribution": equity_contribution,
        "cash_return_contribution": cash_contribution,
        "gross_growth": gross_growth,
        "indicative_nav": float(state["paper_nav_after"]) * gross_growth,
        "drifted_weights": drifted_weights,
        "drifted_cash_weight": current_cash_value / gross_growth,
    }


def load_ledger(path: Path) -> pd.DataFrame:
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    frame = pd.read_csv(path)
    missing = sorted(set(LEDGER_COLUMNS).difference(frame.columns))
    if missing:
        if frame.empty:
            return pd.DataFrame(columns=LEDGER_COLUMNS)
        raise RuntimeError("Shadow ledger is missing columns: " + ", ".join(missing))
    return frame[list(LEDGER_COLUMNS)].copy()


def append_ledger_row(path: Path, row: Mapping[str, Any]) -> None:
    frame = load_ledger(path)
    date = str(row["rebalance_date"])
    if not frame.empty and frame["rebalance_date"].astype(str).eq(date).any():
        raise RuntimeError(f"Shadow ledger already contains {date}.")
    record = {column: row.get(column) for column in LEDGER_COLUMNS}
    result = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    result.to_csv(temporary, index=False)
    os.replace(temporary, path)
