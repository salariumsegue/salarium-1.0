"""Publish four comparable accounts from the governed close; never backfill."""

from __future__ import annotations
import hashlib
import copy
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_forward_paper_snapshot import (
    construct_base_weights,
    load_market_history,
    current_price_map,
)
from src.forward_paper import atomic_json_dump, build_daily_returns, sha256_file
from src.multi_portfolio import advance, validate_prices


def main():
    config_path = ROOT / "configs/paper_portfolios.json"
    config = json.loads(config_path.read_text())
    if (
        config["paper_only"] is not True
        or len(config["portfolios"]) != 4
        or {p["key"] for p in config["portfolios"]}
        != {"core", "defensive", "drawdown", "oil"}
    ):
        raise ValueError("Invalid four-account paper contract")
    source_path = ROOT / "web/public/data/forward_paper_snapshot.json"
    source = json.loads(source_path.read_text())
    state_path = ROOT / "reports/shadow/paper_portfolios_state.json"
    public_path = ROOT / "web/public/data/paper_portfolios.json"
    old = json.loads(state_path.read_text()) if state_path.exists() else None
    date = source["latest_signal_state"]["date"]
    now = datetime.now(timezone.utc).isoformat()
    config_hash = sha256_file(config_path)
    if old and old["config_sha256"] != config_hash:
        raise ValueError("Policy configuration changed")
    if (
        old
        and old["status"] == "awaiting_launch"
        and date <= config["launch_after_signal_date"]
    ):
        return
    if old and old["status"] == "awaiting_launch":
        old = None
    if old and old["signal_date"] >= date:
        return
    if date <= config["launch_after_signal_date"]:
        payload = {
            "policy_config": config,
            "schema_version": "1.0",
            "status": "awaiting_launch",
            "launch_after": config["launch_after_signal_date"],
            "starting_capital": config["starting_capital"],
            "portfolios": [
                {
                    **p,
                    "status": "awaiting_launch",
                    "observations": [],
                    "total_costs": 0,
                    "maximum_drawdown": 0,
                }
                for p in config["portfolios"]
            ],
            "benchmark": [],
            "paper_only": True,
            "generated_at": now,
            "signal_date": None,
            "config_sha256": config_hash,
            "message": "All four accounts begin together at the first governed close after October 5, 2026. No historical outcomes are backfilled.",
        }
        atomic_json_dump(payload, state_path)
        atomic_json_dump(payload, public_path)
        return
    if (
        not source["data_quality"]["passed"]
        or not source["governance"]["paper_only"]
        or source["governance"]["live_capital"]
    ):
        raise ValueError("Source publication gate failed")
    if old and old["config_sha256"] != config_hash:
        raise ValueError("Policy configuration changed")
    rows = source["latest_signal_state"]["rankings"]
    scored = pd.DataFrame(rows)
    held = {a for p in (old or {}).get("portfolios", []) for a in p["positions"]}
    symbols = set(scored.ticker) | held | {"BIL", "USO", "SPY"}
    history = load_market_history(
        provider_name="yahoo",
        csv_path=None,
        cache_directory=ROOT / "data/cache/paper_portfolios",
        symbols=tuple(sorted(symbols)),
        start_date=(pd.Timestamp(date) - timedelta(days=180)).date().isoformat(),
        end_date=(pd.Timestamp(date) + timedelta(days=1)).date().isoformat(),
    )
    history = history.loc[history["date"].le(pd.Timestamp(date))]
    prices = current_price_map(history, signal_date=pd.Timestamp(date))
    validate_prices(prices, symbols)
    returns = build_daily_returns(history)
    sessions = sorted(history.loc[history.ticker.eq("SPY"), "date"].unique())
    base_config = json.loads((ROOT / "configs/forward_paper.json").read_text())
    # All policies share the same selected equity basket and rebalance calendar.
    core_old = next(
        (p for p in (old or {}).get("portfolios", []) if p["key"] == "core"), None
    )
    due = (
        not core_old
        or sum(
            pd.Timestamp(s) > pd.Timestamp(core_old["last_rebalance_date"])
            for s in sessions
        )
        >= config["rebalance_sessions"]
    )
    previous = [
        a for a in (core_old or {}).get("positions", {}) if a not in {"BIL", "USO"}
    ]
    accounts = []
    for policy in config["portfolios"]:
        cfg = copy.deepcopy(base_config)
        cfg["portfolio"]["risk_anchor"] = policy["anchor"]
        cfg["portfolio"]["signal_blend"] = policy["signal_blend"]
        weights = {}
        if due:
            weights, holdings, diagnostics = construct_base_weights(
                scored=scored,
                daily_returns=returns,
                signal_date=pd.Timestamp(date),
                previous_holdings=previous,
                config=cfg,
            )
            if diagnostics["optimizer_fallback"]:
                raise ValueError(f"{policy['name']} covariance gate failed")
        prior = next(
            (p for p in (old or {}).get("portfolios", []) if p["key"] == policy["key"]),
            None,
        )
        account = advance(
            prior,
            policy=policy,
            date=date,
            recorded_at=now,
            prices=prices,
            base_weights=weights,
            source_hash=sha256_file(source_path),
            config_hash=config_hash,
            starting_capital=config["starting_capital"],
            cost_bps=config["transaction_cost_bps"],
            due=due,
        )
        if account["observations"][-1]["rebalance"]:
            account["observations"][-1]["rankings"] = rows
        accounts.append(account)
    benchmark = (old or {}).get("benchmark", [])
    benchmark_units = (old or {}).get(
        "benchmark_units",
        config["starting_capital"]
        / (1 + config["transaction_cost_bps"] / 10000)
        / prices["SPY"],
    )
    benchmark = benchmark + [{"date": date, "nav": benchmark_units * prices["SPY"]}]
    payload = {
        "policy_config": config,
        "schema_version": "1.0",
        "status": "active_paper",
        "launch_date": accounts[0]["launch_date"],
        "signal_date": date,
        "generated_at": now,
        "starting_capital": config["starting_capital"],
        "paper_only": True,
        "config_sha256": config_hash,
        "source_sha256": sha256_file(source_path),
        "market_data_sha256": hashlib.sha256(
            history.sort_values(["ticker", "date"]).to_csv(index=False).encode()
        ).hexdigest(),
        "provider": "yahoo_research_feed",
        "transaction_cost_bps": config["transaction_cost_bps"],
        "portfolios": accounts,
        "benchmark": benchmark,
        "benchmark_units": benchmark_units,
        "message": "Four independent paper accounts. The earlier drawdown account remains a separate legacy record. USO uses ETF adjusted-close prices, not contract-level futures execution.",
    }
    # Compute every account successfully before publishing any change.
    atomic_json_dump(payload, state_path)
    atomic_json_dump(payload, public_path)
    print("Published four portfolios for", date)


if __name__ == "__main__":
    main()
