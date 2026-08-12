from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.evaluate_covariance_portfolio_leverage as covariance_tools  # noqa: E402
import scripts.evaluate_signal_aware_covariance as signal_tools  # noqa: E402
from src.backtesting.drawdown_budget import (  # noqa: E402
    DrawdownBudgetSpec,
    exposure_from_cushion,
)
from src.backtesting.risk_controls import (  # noqa: E402
    calculate_turnover,
    select_buffered_holdings,
)
from src.data_sources.market_data import (  # noqa: E402
    CsvMarketDataProvider,
    MarketDataRequest,
)
from src.data_sources.yahoo_market_data import YahooMarketDataProvider  # noqa: E402
from src.forward_paper import (  # noqa: E402
    append_ledger_row,
    atomic_json_dump,
    build_daily_returns,
    build_latest_features,
    load_ledger,
    load_verified_model,
    mark_to_market,
    normalize_history,
    resolve_signal_date,
    score_features,
    sessions_after,
    sha256_file,
    stable_sha256,
)
from src.universe.canonical_snapshot import load_canonical_snapshot  # noqa: E402


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def market_frame_sha256(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(["date", "ticker"]).reset_index(drop=True)
    row_hashes = pd.util.hash_pandas_object(ordered, index=False).to_numpy()
    digest = hashlib.sha256()
    digest.update("|".join(str(column) for column in ordered.columns).encode())
    digest.update(row_hashes.tobytes())
    return digest.hexdigest()


def load_market_history(
    *,
    provider_name: str,
    csv_path: Path | None,
    cache_directory: Path,
    symbols: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    request = MarketDataRequest.create(symbols, start_date, end_date)
    if provider_name == "csv":
        if csv_path is None:
            raise ValueError("--market-data is required for the CSV provider.")
        provider = CsvMarketDataProvider(csv_path)
    elif provider_name == "yahoo":
        provider = YahooMarketDataProvider(
            cache_directory=cache_directory,
            batch_size=50,
            retries=3,
            retry_delay_seconds=2.0,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
    return provider.fetch(request)


def construct_base_weights(
    *,
    scored: pd.DataFrame,
    daily_returns: pd.DataFrame,
    signal_date: pd.Timestamp,
    previous_holdings: list[str],
    config: dict[str, Any],
) -> tuple[dict[str, float], list[str], dict[str, Any]]:
    portfolio = config["portfolio"]
    top_n = int(portfolio["top_n"])
    holdings = select_buffered_holdings(
        scored["ticker"].tolist(),
        previous_holdings,
        top_n=top_n,
        buffer_rank=int(portfolio["buffer_rank"]),
    )
    indexed = scored.set_index("ticker")
    covariance = None
    sigmas = None
    covariance_observations = 0
    average_correlation = float("nan")
    maximum_correlation = float("nan")
    covariance_reason = "ok"
    try:
        (
            covariance,
            sigmas,
            covariance_observations,
            average_correlation,
            maximum_correlation,
        ) = covariance_tools.covariance_and_stats(
            daily_returns=daily_returns,
            holdings=holdings,
            rebalance_date=signal_date,
            lookback=int(portfolio["covariance_lookback_sessions"]),
            minimum_coverage=float(portfolio["covariance_minimum_coverage"]),
        )
    except RuntimeError as error:
        covariance_reason = str(error)

    risk_weights, optimizer_fallback, optimizer_reason = (
        covariance_tools.optimize_weights(
            constructor=str(portfolio["risk_anchor"]),
            holdings=holdings,
            current_volatility=indexed.loc[holdings, "volatility_20d"],
            covariance=covariance,
            sigmas=sigmas,
            max_weight=float(portfolio["maximum_single_name_weight"]),
        )
    )
    alpha_weights, _ = signal_tools.signal_weights(
        holdings=holdings,
        ranked=scored,
        max_weight=float(portfolio["maximum_single_name_weight"]),
        score_clip=float(portfolio["signal_score_clip"]),
        temperature=float(portfolio["signal_temperature"]),
    )
    weights = signal_tools.blend_weights(
        risk_weights=risk_weights,
        alpha_weights=alpha_weights,
        signal_blend=float(portfolio["signal_blend"]),
        max_weight=float(portfolio["maximum_single_name_weight"]),
    )
    diagnostics = {
        "optimizer_fallback": bool(optimizer_fallback or covariance is None),
        "optimizer_reason": (
            optimizer_reason if optimizer_fallback else covariance_reason
        ),
        "covariance_observations": covariance_observations,
        "average_pairwise_correlation": average_correlation,
        "maximum_pairwise_correlation": maximum_correlation,
    }
    return weights, holdings, diagnostics


def current_price_map(
    history: pd.DataFrame,
    *,
    signal_date: pd.Timestamp,
) -> dict[str, float]:
    latest = history.loc[history["date"].eq(signal_date)].copy()
    price_column = "adj_close" if "adj_close" in latest.columns else "close"
    latest[price_column] = pd.to_numeric(latest[price_column], errors="raise")
    return {
        str(row.ticker): float(getattr(row, price_column))
        for row in latest.itertuples(index=False)
    }


def scaled_weights(
    base_weights: dict[str, float],
    exposure: float,
) -> dict[str, float]:
    return {
        ticker: float(weight) * float(exposure)
        for ticker, weight in base_weights.items()
    }


def make_drawdown_spec(mandate: dict[str, Any]) -> DrawdownBudgetSpec:
    policy = mandate["policy"]
    return DrawdownBudgetSpec(
        key=str(policy["key"]),
        floor_ratio=float(policy["floor_ratio"]),
        cushion_multiplier=float(policy["cushion_multiplier"]),
        max_equity_exposure=float(policy["maximum_equity_exposure"]),
        cash_turnover_bps=float(policy["cash_turnover_bps"]),
        cash_proxy=str(policy["cash_proxy"]),
    )


def initialize_shadow_state(
    *,
    signal_date: pd.Timestamp,
    generated_at: str,
    source_hash: str,
    paper_notional: float,
    baseline_exposure: float,
    base_weights: dict[str, float],
    holdings: list[str],
    prices: dict[str, float],
    drawdown_spec: DrawdownBudgetSpec,
    transaction_cost_bps: float,
    diagnostics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    exposure_cap, floor_value, cushion_ratio = exposure_from_cushion(
        nav=paper_notional,
        high_water_mark=paper_notional,
        spec=drawdown_spec,
    )
    exposure = min(baseline_exposure, exposure_cap)
    weights = scaled_weights(base_weights, exposure)
    turnover = float(sum(weights.values()))
    modeled_cost_rate = turnover * transaction_cost_bps / 10_000.0
    nav_after = paper_notional * (1.0 - modeled_cost_rate)
    cash_weight = 1.0 - exposure
    state = {
        "schema_version": "1.0",
        "status": "active_awaiting_first_completed_interval",
        "last_rebalance_date": signal_date.date().isoformat(),
        "paper_nav_after": nav_after,
        "high_water_mark": paper_notional,
        "baseline_equity_exposure": baseline_exposure,
        "shadow_equity_exposure": exposure,
        "cash_weight": cash_weight,
        "cash_proxy": drawdown_spec.cash_proxy,
        "holdings": holdings,
        "base_weights": base_weights,
        "weights": weights,
        "reference_prices": {
            ticker: prices[ticker] for ticker in [*holdings, drawdown_spec.cash_proxy]
        },
        "last_source_snapshot_sha256": source_hash,
        "last_source_snapshot_generated_at_utc": generated_at,
        "portfolio_diagnostics": diagnostics,
    }
    row = {
        "observation_number": 0,
        "rebalance_date": signal_date.date().isoformat(),
        "prior_rebalance_date": "",
        "source_snapshot_generated_at_utc": generated_at,
        "source_snapshot_sha256": source_hash,
        "baseline_equity_exposure": baseline_exposure,
        "shadow_equity_exposure": exposure,
        "cash_weight": cash_weight,
        "paper_nav_before": paper_notional,
        "paper_nav_after": nav_after,
        "high_water_mark_after": paper_notional,
        "equity_return_contribution": 0.0,
        "cash_return_contribution": 0.0,
        "turnover": turnover,
        "modeled_cost": modeled_cost_rate,
        "net_return": nav_after / paper_notional - 1.0,
        "drawdown_after_rebalance": nav_after / paper_notional - 1.0,
        "status": "initialized_no_market_outcome",
    }
    state["controller"] = {
        "soft_floor_value": floor_value,
        "cushion_ratio": cushion_ratio,
        "exposure_cap": exposure_cap,
    }
    return state, row


def rebalance_shadow_state(
    *,
    prior_state: dict[str, Any],
    ledger: pd.DataFrame,
    signal_date: pd.Timestamp,
    generated_at: str,
    source_hash: str,
    baseline_exposure: float,
    base_weights: dict[str, float],
    holdings: list[str],
    prices: dict[str, float],
    drawdown_spec: DrawdownBudgetSpec,
    transaction_cost_bps: float,
    diagnostics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    marked = mark_to_market(prior_state, prices)
    prior_nav = float(prior_state["paper_nav_after"])
    nav_before_trade = float(marked["indicative_nav"])
    prior_high_water = float(prior_state["high_water_mark"])
    controller_high_water = max(prior_high_water, nav_before_trade)
    exposure_cap, floor_value, cushion_ratio = exposure_from_cushion(
        nav=nav_before_trade,
        high_water_mark=controller_high_water,
        spec=drawdown_spec,
    )
    exposure = min(baseline_exposure, exposure_cap)
    weights = scaled_weights(base_weights, exposure)
    turnover = calculate_turnover(marked["drifted_weights"], weights)
    modeled_cost_rate = turnover * transaction_cost_bps / 10_000.0
    nav_after = nav_before_trade * (1.0 - modeled_cost_rate)
    high_water = max(prior_high_water, nav_after)
    cash_weight = 1.0 - exposure
    completed = int(
        (ledger.get("status", pd.Series(dtype=str)) == "completed_interval").sum()
    )
    state = {
        "schema_version": "1.0",
        "status": "active_forward_paper",
        "last_rebalance_date": signal_date.date().isoformat(),
        "paper_nav_after": nav_after,
        "high_water_mark": high_water,
        "baseline_equity_exposure": baseline_exposure,
        "shadow_equity_exposure": exposure,
        "cash_weight": cash_weight,
        "cash_proxy": drawdown_spec.cash_proxy,
        "holdings": holdings,
        "base_weights": base_weights,
        "weights": weights,
        "reference_prices": {
            ticker: prices[ticker] for ticker in [*holdings, drawdown_spec.cash_proxy]
        },
        "last_source_snapshot_sha256": source_hash,
        "last_source_snapshot_generated_at_utc": generated_at,
        "portfolio_diagnostics": diagnostics,
        "controller": {
            "soft_floor_value": floor_value,
            "cushion_ratio": cushion_ratio,
            "exposure_cap": exposure_cap,
        },
    }
    row = {
        "observation_number": completed + 1,
        "rebalance_date": signal_date.date().isoformat(),
        "prior_rebalance_date": prior_state["last_rebalance_date"],
        "source_snapshot_generated_at_utc": generated_at,
        "source_snapshot_sha256": source_hash,
        "baseline_equity_exposure": baseline_exposure,
        "shadow_equity_exposure": exposure,
        "cash_weight": cash_weight,
        "paper_nav_before": prior_nav,
        "paper_nav_after": nav_after,
        "high_water_mark_after": high_water,
        "equity_return_contribution": marked["equity_return_contribution"],
        "cash_return_contribution": marked["cash_return_contribution"],
        "turnover": turnover,
        "modeled_cost": modeled_cost_rate,
        "net_return": nav_after / prior_nav - 1.0,
        "drawdown_after_rebalance": nav_after / high_water - 1.0,
        "status": "completed_interval",
    }
    return state, row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a governed market-close paper snapshot with no order routing."
    )
    parser.add_argument("--config", default="configs/forward_paper.json")
    parser.add_argument("--provider", choices=["yahoo", "csv"], default="yahoo")
    parser.add_argument("--market-data", default=None)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--force-publish", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = repository_path(args.config)
    config = load_json(config_path)
    universe_manifest_path = repository_path(config["universe"]["manifest"])
    universe_snapshot = load_canonical_snapshot(universe_manifest_path)
    universe = universe_snapshot.frame.copy()
    expected_count = int(config["universe"]["expected_count"])
    if len(universe) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} governed universe rows; found {len(universe)}."
        )

    mandate_path = repository_path(config["shadow"]["mandate"])
    mandate = load_json(mandate_path)
    drawdown_spec = make_drawdown_spec(mandate)
    requested_as_of = pd.Timestamp(args.as_of or datetime.now(timezone.utc).date())
    provider_config = config["provider"]
    start_date = (
        requested_as_of - timedelta(days=int(provider_config["lookback_calendar_days"]))
    ).date().isoformat()
    end_date = (requested_as_of + timedelta(days=1)).date().isoformat()

    symbol_to_ticker = {
        str(row.yahoo_symbol).upper(): str(row.ticker).upper()
        for row in universe.itertuples(index=False)
    }
    symbol_to_ticker.update(
        {str(row.ticker).upper(): str(row.ticker).upper() for row in universe.itertuples(index=False)}
    )
    symbol_to_ticker[drawdown_spec.cash_proxy.upper()] = drawdown_spec.cash_proxy.upper()
    symbols = tuple(
        sorted(
            set(universe["yahoo_symbol"].astype(str).str.upper())
            | {drawdown_spec.cash_proxy.upper()}
        )
    )
    raw_history = load_market_history(
        provider_name=args.provider,
        csv_path=repository_path(args.market_data) if args.market_data else None,
        cache_directory=repository_path(provider_config["cache_directory"]),
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )
    history = normalize_history(raw_history, symbol_to_ticker)
    universe_history = history.loc[
        history["ticker"].ne(drawdown_spec.cash_proxy.upper())
    ].copy()
    signal_date, market_names, market_coverage = resolve_signal_date(
        universe_history,
        requested_as_of=requested_as_of,
        expected_count=expected_count,
        minimum_coverage=float(provider_config["minimum_universe_coverage"]),
        maximum_stale_calendar_days=int(provider_config["maximum_stale_calendar_days"]),
    )
    history = history.loc[history["date"].le(signal_date)].copy()
    universe_history = universe_history.loc[
        universe_history["date"].le(signal_date)
    ].copy()
    features, _ = build_latest_features(
        universe_history,
        signal_date=signal_date,
    )
    feature_coverage = len(features) / expected_count
    if feature_coverage < float(provider_config["minimum_universe_coverage"]):
        raise RuntimeError(
            "Current feature coverage failed the publication gate: "
            f"{len(features)}/{expected_count}."
        )

    bundle_path = repository_path(config["model"]["bundle"])
    model_manifest_path = repository_path(config["model"]["manifest"])
    bundle, model_manifest = load_verified_model(bundle_path, model_manifest_path)
    scored = score_features(features, bundle)
    daily_returns = build_daily_returns(history)
    prices = current_price_map(history, signal_date=signal_date)
    if drawdown_spec.cash_proxy not in prices:
        raise RuntimeError(
            f"Cash proxy {drawdown_spec.cash_proxy} has no price on {signal_date.date()}."
        )

    state_path = repository_path(config["shadow"]["state"])
    ledger_path = repository_path(config["shadow"]["ledger"])
    prior_state = load_json(state_path) if state_path.is_file() else None
    ledger = load_ledger(ledger_path)
    sessions_elapsed = (
        sessions_after(
            universe_history,
            prior_date=prior_state["last_rebalance_date"],
            current_date=signal_date,
        )
        if prior_state
        else int(config["portfolio"]["rebalance_every_sessions"])
    )
    rebalance_due = (
        prior_state is None
        or sessions_elapsed >= int(config["portfolio"]["rebalance_every_sessions"])
    )
    previous_holdings = list(prior_state.get("holdings", [])) if prior_state else []
    generated_at = datetime.now(timezone.utc).isoformat()
    market_hash = market_frame_sha256(history)
    source_hash = stable_sha256(
        {
            "market_data_sha256": market_hash,
            "model_sha256": model_manifest["model_sha256"],
            "universe_sha256": universe_snapshot.manifest["snapshot_sha256"],
            "signal_date": signal_date.date().isoformat(),
        }
    )
    baseline_exposure = float(config["portfolio"]["baseline_exposure"])
    state = prior_state
    if rebalance_due:
        base_weights, holdings, diagnostics = construct_base_weights(
            scored=scored,
            daily_returns=daily_returns,
            signal_date=signal_date,
            previous_holdings=previous_holdings,
            config=config,
        )
        if prior_state is None:
            state, ledger_row = initialize_shadow_state(
                signal_date=signal_date,
                generated_at=generated_at,
                source_hash=source_hash,
                paper_notional=float(config["shadow"]["paper_notional_usd"]),
                baseline_exposure=baseline_exposure,
                base_weights=base_weights,
                holdings=holdings,
                prices=prices,
                drawdown_spec=drawdown_spec,
                transaction_cost_bps=float(config["portfolio"]["transaction_cost_bps"]),
                diagnostics=diagnostics,
            )
        else:
            state, ledger_row = rebalance_shadow_state(
                prior_state=prior_state,
                ledger=ledger,
                signal_date=signal_date,
                generated_at=generated_at,
                source_hash=source_hash,
                baseline_exposure=baseline_exposure,
                base_weights=base_weights,
                holdings=holdings,
                prices=prices,
                drawdown_spec=drawdown_spec,
                transaction_cost_bps=float(config["portfolio"]["transaction_cost_bps"]),
                diagnostics=diagnostics,
            )
        append_ledger_row(ledger_path, ledger_row)
        atomic_json_dump(state, state_path)
        ledger = load_ledger(ledger_path)

    if state is None:
        raise RuntimeError("Forward state was not initialized.")
    marked = mark_to_market(state, prices)
    completed_observations = int(
        (ledger["status"].astype(str) == "completed_interval").sum()
    )
    rebalanced_on_signal_date = (
        str(state["last_rebalance_date"]) == signal_date.date().isoformat()
    )
    name_by_ticker = {
        str(row.ticker): str(row.company_name)
        for row in universe.itertuples(index=False)
    }
    display_count = int(config["publication"]["display_count"])
    ranking_rows: list[dict[str, Any]] = []
    for row in scored.head(display_count).itertuples(index=False):
        ranking_rows.append(
            {
                "rank": int(row.rank),
                "ticker": str(row.ticker),
                "company_name": name_by_ticker.get(str(row.ticker)),
                "score": float(row.score),
                "score_percentile": float(row.score_percentile),
                "volatility_20d": float(row.volatility_20d),
                "risk_state": "neutral",
                "regime_is_confident": False,
                "model_configuration": bundle["model_configuration"],
            }
        )
    portfolio_holdings = [
        {
            "ticker": ticker,
            "company_name": name_by_ticker.get(ticker),
            "rank": int(scored.set_index("ticker").loc[ticker, "rank"]),
            "base_weight": float(state["base_weights"][ticker]),
            "paper_weight": float(state["weights"][ticker]),
            "reference_price": float(state["reference_prices"][ticker]),
        }
        for ticker in state["holdings"]
    ]
    current_drawdown = float(marked["indicative_nav"]) / float(
        state["high_water_mark"]
    ) - 1.0
    payload = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "system": {
            "name": "Salarium",
            "surface": "Forward Paper Snapshot",
            "status": "forward_paper_no_orders",
        },
        "architecture": {
            "universe": "Liquid-500",
            "model_horizon_days": int(config["model"]["horizon_days"]),
            "rebalance_every_days": int(config["portfolio"]["rebalance_every_sessions"]),
            "portfolio_top_n": int(config["portfolio"]["top_n"]),
            "persistence_buffer_rank": int(config["portfolio"]["buffer_rank"]),
        },
        "latest_signal_state": {
            "date": signal_date.date().isoformat(),
            "count": len(ranking_rows),
            "universe_count": int(len(scored)),
            "rankings": ranking_rows,
        },
        "model": {
            "configuration": bundle["model_configuration"],
            "target_horizon_days": int(bundle["target_horizon_days"]),
            "source_rows": int(bundle["training_rows"]),
            "latest_cross_section_rows": int(len(scored)),
            "test_year": int(signal_date.year),
            "frozen_training_end": bundle["training_end"],
            "model_sha256": model_manifest["model_sha256"],
            "daily_retraining": False,
        },
        "data_quality": {
            "provider": str(provider_config["name"]),
            "requested_as_of": requested_as_of.date().isoformat(),
            "signal_date": signal_date.date().isoformat(),
            "market_rows": int(len(history)),
            "market_names_on_signal_date": market_names,
            "market_coverage": market_coverage,
            "feature_rows": int(len(features)),
            "feature_coverage": feature_coverage,
            "maximum_stale_calendar_days": int(provider_config["maximum_stale_calendar_days"]),
            "passed": True,
        },
        "forward_portfolio": {
            "status": str(state["status"]),
            "last_rebalance_date": state["last_rebalance_date"],
            "sessions_since_rebalance": sessions_elapsed,
            "rebalance_performed": rebalanced_on_signal_date,
            "rebalance_due": False,
            "sessions_until_next_rebalance": max(
                int(config["portfolio"]["rebalance_every_sessions"])
                - (0 if rebalanced_on_signal_date else sessions_elapsed),
                0,
            ),
            "holdings": portfolio_holdings,
            "baseline_equity_exposure": float(state["baseline_equity_exposure"]),
            "shadow_equity_exposure": float(state["shadow_equity_exposure"]),
            "cash_weight": float(state["cash_weight"]),
            "cash_proxy": str(state["cash_proxy"]),
            "last_completed_nav": float(state["paper_nav_after"]),
            "indicative_nav": float(marked["indicative_nav"]),
            "high_water_mark": float(state["high_water_mark"]),
            "current_drawdown": current_drawdown,
            "completed_intervals": completed_observations,
            "portfolio_diagnostics": state["portfolio_diagnostics"],
            "controller": state["controller"],
        },
        "disclosures": [
            "This is an append-only forward paper feed, not live investment performance.",
            "The model is frozen between governed validation releases; fresh prices are scored after each eligible market close.",
            "The live macro regime feed is not yet governed, so the baseline exposure fails closed to the configured neutral 75% level.",
            "Yahoo is used as a research data source and is not an exchange-grade production feed.",
            "No brokerage connection, order generation, order submission, or live capital is permitted.",
            "The drawdown floor is soft and cannot prevent losses caused by gaps or missing liquidity.",
        ],
        "governance": {
            "paper_only": True,
            "append_only_ledger": True,
            "historical_backfill": False,
            "live_capital": False,
            "brokerage_connection": False,
            "order_generation": False,
            "order_submission": False,
            "canonical_release_unchanged": True,
            "automatic_model_retraining": False,
        },
        "provenance": {
            "config_path": config_path.relative_to(ROOT).as_posix(),
            "config_sha256": sha256_file(config_path),
            "universe_manifest": universe_manifest_path.relative_to(ROOT).as_posix(),
            "universe_snapshot_sha256": universe_snapshot.manifest["snapshot_sha256"],
            "model_manifest": model_manifest_path.relative_to(ROOT).as_posix(),
            "model_sha256": model_manifest["model_sha256"],
            "market_data_sha256": market_hash,
            "source_snapshot_sha256": source_hash,
            "source_path": str(config["publication"]["snapshot"]),
            "ledger_path": ledger_path.relative_to(ROOT).as_posix(),
            "state_path": state_path.relative_to(ROOT).as_posix(),
            "git_branch": git_value("branch", "--show-current"),
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(git_value("status", "--porcelain")),
        },
    }
    output_path = repository_path(config["publication"]["snapshot"])
    if output_path.is_file() and not args.force_publish and not rebalance_due:
        prior_publication = load_json(output_path)
        if (
            prior_publication.get("provenance", {}).get("source_snapshot_sha256")
            == source_hash
        ):
            print("SALARIUM_FORWARD_PAPER_REFRESH=NO_CHANGE")
            print("Signal date:", signal_date.date().isoformat())
            return 0
    atomic_json_dump(safe(payload), output_path)
    print("SALARIUM_FORWARD_PAPER_REFRESH=PASS")
    print("Signal date:", signal_date.date().isoformat())
    print("Scored names:", len(scored))
    print("Rebalance due:", rebalance_due)
    print("Indicative paper NAV:", f"${marked['indicative_nav']:,.2f}")
    print("Output:", output_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
