from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "results" / "signal_aware_covariance" / "signal_aware_covariance_results.csv"
)
BENCHMARK_SOURCE = (
    ROOT / "reports" / "experiments" / "crisis_diversifier_proxy_prices.csv"
)
RELEASE_PATH = ROOT / "web" / "public" / "data" / "release_snapshot.json"
OUTPUT = ROOT / "web" / "public" / "data" / "hypothetical_account_snapshot.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maximum_drawdown(returns: pd.Series) -> float:
    values = (1.0 + pd.to_numeric(returns, errors="raise")).cumprod()
    values = pd.concat([pd.Series([1.0]), values], ignore_index=True)
    return float((values / values.cummax() - 1.0).min())


def aligned_benchmark_returns(
    selected: pd.DataFrame,
    *,
    rebalance_every_days: int,
) -> tuple[pd.Series, list[pd.Timestamp]]:
    proxy = pd.read_csv(BENCHMARK_SOURCE)
    required = {"date", "ticker", "adj_close"}
    if not required.issubset(proxy.columns):
        raise ValueError("Benchmark source is missing required adjusted-close fields")
    proxy["date"] = pd.to_datetime(proxy["date"], errors="raise")
    spy_frame = proxy.loc[proxy["ticker"].eq("SPY"), ["date", "adj_close"]]
    if spy_frame["date"].duplicated().any():
        raise ValueError("Benchmark source contains duplicate SPY dates")
    spy = spy_frame.set_index("date")["adj_close"].sort_index()
    spy = pd.to_numeric(spy, errors="raise")
    if spy.empty:
        raise ValueError("Benchmark source does not contain SPY")

    dates = pd.DatetimeIndex(selected["rebalance_date"])
    returns: list[float] = []
    end_dates: list[pd.Timestamp] = []
    for index, date in enumerate(dates):
        if index + 1 < len(dates):
            end_date = pd.Timestamp(dates[index + 1])
        else:
            eligible = spy.index[spy.index > date]
            if len(eligible) < rebalance_every_days:
                raise ValueError(
                    "SPY history does not cover the final holding interval"
                )
            end_date = pd.Timestamp(eligible[rebalance_every_days - 1])
        start_value = float(spy.loc[:date].iloc[-1])
        end_value = float(spy.loc[:end_date].iloc[-1])
        returns.append(end_value / start_value - 1.0)
        end_dates.append(end_date)
    return pd.Series(returns, dtype=float), end_dates


def main() -> int:
    release: dict[str, Any] = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    core = release["results"]["core_balanced"]
    frame = pd.read_csv(SOURCE)
    selected = frame.loc[
        frame["base_policy"].eq(core["base_policy"])
        & frame["exposure_policy"].eq(core["exposure_policy"])
        & frame["model_horizon_days"].eq(release["architecture"]["model_horizon_days"])
        & frame["rebalance_every_days"].eq(
            release["architecture"]["rebalance_every_days"]
        )
    ].copy()
    selected["rebalance_date"] = pd.to_datetime(
        selected["rebalance_date"], errors="raise"
    )
    selected = selected.sort_values("rebalance_date").reset_index(drop=True)
    if len(selected) != int(core["num_rebalances"]):
        raise ValueError("Detailed return stream does not match the canonical release")
    rebalance_every_days = int(release["architecture"]["rebalance_every_days"])
    benchmark_returns, end_dates = aligned_benchmark_returns(
        selected,
        rebalance_every_days=rebalance_every_days,
    )
    model_values = 100_000.0 * (1.0 + selected["net_return"]).cumprod()
    benchmark_values = 100_000.0 * (1.0 + benchmark_returns).cumprod()
    points = [
        {
            "date": selected["rebalance_date"].iloc[0].date().isoformat(),
            "value": 100_000,
            "benchmark_value": 100_000,
        }
    ]
    points.extend(
        {
            "date": date.date().isoformat(),
            "value": int(round(value)),
            "benchmark_value": int(round(benchmark_value)),
        }
        for date, value, benchmark_value in zip(
            end_dates,
            model_values,
            benchmark_values,
        )
    )
    benchmark_annualized_return = float(
        (1.0 + benchmark_returns).prod()
        ** ((252.0 / rebalance_every_days) / len(benchmark_returns))
        - 1.0
    )
    payload = {
        "schema_version": "1.1",
        "currency": "USD",
        "starting_balance": 100_000,
        "ending_balance": points[-1]["value"],
        "period": {"start": points[0]["date"], "end": points[-1]["date"]},
        "model": {
            "horizon_days": int(release["architecture"]["model_horizon_days"]),
            "rebalance_every_days": rebalance_every_days,
            "base_policy": str(core["base_policy"]),
            "exposure_policy": str(core["exposure_policy"]),
            "risk_anchor": str(core["risk_anchor"]),
            "signal_blend": float(core["signal_blend"]),
        },
        "statistics": {
            "rebalances": int(core["num_rebalances"]),
            "annualized_net_return": float(core["annualized_net_return"]),
            "net_sharpe": float(core["net_sharpe"]),
            "max_drawdown": float(core["max_drawdown"]),
        },
        "benchmark": {
            "ticker": "SPY",
            "label": "S&P 500 (SPY total-return proxy)",
            "data_provider": "Yahoo adjusted-close proxy history",
            "starting_balance": 100_000,
            "ending_balance": points[-1]["benchmark_value"],
            "statistics": {
                "annualized_total_return": benchmark_annualized_return,
                "max_drawdown": maximum_drawdown(benchmark_returns),
            },
            "calculation": "Buy-and-hold SPY adjusted-close total-return proxy over the identical holding intervals.",
        },
        "points": points,
        "governance": {
            "hypothetical": True,
            "live": False,
            "initial_contribution_only": True,
            "modeled_costs_included": True,
            "taxes_and_market_impact_excluded": True,
            "calculation": "Starting balance compounded by each governed net_return observation.",
            "benchmark_is_market_proxy": True,
            "benchmark_fund_expenses_and_distributions_reflected_in_adjusted_close": True,
            "benchmark_initial_trade_cost_excluded": True,
        },
        "provenance": {
            "source_path": str(SOURCE.relative_to(ROOT)),
            "source_sha256": sha256(SOURCE),
            "release_report": str(release["provenance"]["source_report"]),
            "benchmark_source_path": str(BENCHMARK_SOURCE.relative_to(ROOT)),
            "benchmark_source_sha256": sha256(BENCHMARK_SOURCE),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(points)} observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
