from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_forward_paper_snapshot import initialize_shadow_state
from src.backtesting.drawdown_budget import DrawdownBudgetSpec
from src.forward_paper import (
    LEDGER_COLUMNS,
    append_ledger_row,
    build_latest_features,
    load_ledger,
    mark_to_market,
    normalize_history,
    resolve_signal_date,
    score_features,
)
from src.research.feature_policy import CORE_TECHNICAL_FEATURES


ROOT = Path(__file__).resolve().parents[1]


class MeanModel:
    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return frame.mean(axis=1).to_numpy(dtype=float)


def synthetic_history(tickers: tuple[str, ...] = ("AAA", "BBB")) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-02", periods=70)
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(tickers):
        for position, date in enumerate(dates):
            price = 50.0 + ticker_index * 5.0 + position * (0.12 + 0.01 * ticker_index)
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": price * 0.998,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "adj_close": price,
                    "volume": 1_000_000 + position * 1_000 + ticker_index,
                }
            )
    return pd.DataFrame(rows)


def test_signal_date_requires_fresh_cross_sectional_coverage() -> None:
    history = synthetic_history()
    signal_date, count, coverage = resolve_signal_date(
        history,
        requested_as_of=history["date"].max(),
        expected_count=2,
        minimum_coverage=1.0,
        maximum_stale_calendar_days=0,
    )
    assert signal_date == history["date"].max()
    assert count == 2
    assert coverage == 1.0

    with pytest.raises(RuntimeError, match="stale"):
        resolve_signal_date(
            history,
            requested_as_of=history["date"].max() + pd.Timedelta(days=5),
            expected_count=2,
            minimum_coverage=1.0,
            maximum_stale_calendar_days=2,
        )


def test_current_features_and_scores_use_only_the_signal_date() -> None:
    raw = synthetic_history()
    history = normalize_history(raw, {"AAA": "AAA", "BBB": "BBB"})
    signal_date = history["date"].max()
    features, prices = build_latest_features(history, signal_date=signal_date)
    assert len(features) == 2
    assert set(features["date"]) == {signal_date}
    assert set(prices["ticker"]) == {"AAA", "BBB"}
    assert features[list(CORE_TECHNICAL_FEATURES)].notna().all().all()

    bundle = {
        "feature_columns": list(CORE_TECHNICAL_FEATURES),
        "lower_bounds": {feature: -1000.0 for feature in CORE_TECHNICAL_FEATURES},
        "upper_bounds": {feature: 1000.0 for feature in CORE_TECHNICAL_FEATURES},
        "model": MeanModel(),
    }
    scored = score_features(features, bundle)
    assert scored["rank"].tolist() == [1, 2]
    assert scored["score"].tolist() == sorted(scored["score"], reverse=True)


def test_initial_shadow_snapshot_uses_cushion_cap_and_no_market_backfill() -> None:
    spec = DrawdownBudgetSpec(
        key="drawdown_budget_78_m3",
        floor_ratio=0.78,
        cushion_multiplier=3.0,
        cash_proxy="BIL",
    )
    state, row = initialize_shadow_state(
        signal_date=pd.Timestamp("2026-08-12"),
        generated_at="2026-08-12T22:30:00+00:00",
        source_hash="a" * 64,
        paper_notional=100_000.0,
        baseline_exposure=0.75,
        base_weights={"AAA": 0.5, "BBB": 0.5},
        holdings=["AAA", "BBB"],
        prices={"AAA": 100.0, "BBB": 50.0, "BIL": 91.0},
        drawdown_spec=spec,
        transaction_cost_bps=10.0,
        diagnostics={"optimizer_fallback": False},
    )
    assert state["shadow_equity_exposure"] == pytest.approx(0.66)
    assert state["cash_weight"] == pytest.approx(0.34)
    assert sum(state["weights"].values()) == pytest.approx(0.66)
    assert row["observation_number"] == 0
    assert row["status"] == "initialized_no_market_outcome"
    assert row["equity_return_contribution"] == 0.0
    assert state["paper_nav_after"] < 100_000.0


def test_mark_to_market_and_ledger_are_append_only(tmp_path: Path) -> None:
    state = {
        "reference_prices": {"AAA": 100.0, "BIL": 90.0},
        "weights": {"AAA": 0.60},
        "cash_proxy": "BIL",
        "cash_weight": 0.40,
        "paper_nav_after": 100_000.0,
    }
    marked = mark_to_market(state, {"AAA": 110.0, "BIL": 90.9})
    assert marked["equity_return_contribution"] == pytest.approx(0.06)
    assert marked["cash_return_contribution"] == pytest.approx(0.004)
    assert marked["indicative_nav"] == pytest.approx(106_400.0)

    ledger_path = tmp_path / "ledger.csv"
    empty_header = ",".join(LEDGER_COLUMNS) + "\n"
    ledger_path.write_text(empty_header, encoding="utf-8")
    row = {column: 0 for column in LEDGER_COLUMNS}
    row.update({"rebalance_date": "2026-08-12", "status": "initialized_no_market_outcome"})
    append_ledger_row(ledger_path, row)
    assert len(load_ledger(ledger_path)) == 1
    with pytest.raises(RuntimeError, match="already contains"):
        append_ledger_row(ledger_path, row)


def test_committed_forward_configuration_is_strictly_paper_only() -> None:
    config = json.loads((ROOT / "configs" / "forward_paper.json").read_text())
    mandate = json.loads(
        (ROOT / "configs" / "drawdown_budget_shadow_mandate.json").read_text()
    )
    assert config["mode"] == "forward_paper_only"
    assert config["model"]["retraining_policy"].startswith("frozen")
    assert config["portfolio"]["baseline_exposure"] == 0.75
    assert mandate["execution"]["live_capital"] is False
    assert mandate["execution"]["brokerage_connection"] is False
    assert mandate["execution"]["order_generation"] is False
    assert mandate["execution"]["order_submission"] is False
