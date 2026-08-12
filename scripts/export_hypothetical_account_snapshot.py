from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "signal_aware_covariance" / "signal_aware_covariance_results.csv"
RELEASE_PATH = ROOT / "web" / "public" / "data" / "release_snapshot.json"
OUTPUT = ROOT / "web" / "public" / "data" / "hypothetical_account_snapshot.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    release: dict[str, Any] = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    core = release["results"]["core_balanced"]
    frame = pd.read_csv(SOURCE)
    selected = frame.loc[
        frame["base_policy"].eq(core["base_policy"])
        & frame["exposure_policy"].eq(core["exposure_policy"])
        & frame["model_horizon_days"].eq(release["architecture"]["model_horizon_days"])
        & frame["rebalance_every_days"].eq(release["architecture"]["rebalance_every_days"])
    ].copy()
    selected["rebalance_date"] = pd.to_datetime(selected["rebalance_date"], errors="raise")
    selected = selected.sort_values("rebalance_date").reset_index(drop=True)
    if len(selected) != int(core["num_rebalances"]):
        raise ValueError("Detailed return stream does not match the canonical release")
    values = 100_000.0 * (1.0 + selected["net_return"]).cumprod()
    points = [
        {"date": date.date().isoformat(), "value": int(round(value))}
        for date, value in zip(selected["rebalance_date"], values)
    ]
    payload = {
        "schema_version": "1.0",
        "currency": "USD",
        "starting_balance": 100_000,
        "ending_balance": points[-1]["value"],
        "period": {"start": points[0]["date"], "end": points[-1]["date"]},
        "model": {
            "horizon_days": int(release["architecture"]["model_horizon_days"]),
            "rebalance_every_days": int(release["architecture"]["rebalance_every_days"]),
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
        "points": points,
        "governance": {
            "hypothetical": True,
            "live": False,
            "initial_contribution_only": True,
            "modeled_costs_included": True,
            "taxes_and_market_impact_excluded": True,
            "calculation": "Starting balance compounded by each governed net_return observation.",
        },
        "provenance": {
            "source_path": str(SOURCE.relative_to(ROOT)),
            "source_sha256": sha256(SOURCE),
            "release_report": str(release["provenance"]["source_report"]),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(points)} observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
