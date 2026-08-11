import json
from pathlib import Path

from src.research.security_metadata_policy import (
    load_provenance_registry,
    provenance_backtest_eligibility,
)


REGISTRY_PATH = Path(
    "configs/"
    "security_metadata_provenance_registry.json"
)


def test_registry_loads() -> None:
    registry = load_provenance_registry(
        REGISTRY_PATH
    )

    assert registry["schema_version"] == "1.0"
    assert len(registry["sources"]) >= 5


def test_legacy_historical_sector_is_explicitly_rejected() -> None:
    registry = load_provenance_registry(
        REGISTRY_PATH
    )

    eligible, reason = (
        provenance_backtest_eligibility(
            Path(
                "data/processed/"
                "salarium_training_with_macro.csv"
            ),
            "sector",
            registry,
        )
    )

    assert eligible is False

    assert reason == (
        "provenance_rejected_"
        "static_metadata_propagated_backward"
    )


def test_demo_sector_is_not_historical_data() -> None:
    registry = load_provenance_registry(
        REGISTRY_PATH
    )

    eligible, reason = (
        provenance_backtest_eligibility(
            Path(
                "data/processed/"
                "demo_stock_training_data.csv"
            ),
            "sector",
            registry,
        )
    )

    assert eligible is False
    assert reason == (
        "provenance_rejected_static_metadata"
    )


def test_yahoo_snapshot_is_current_only() -> None:
    registry = load_provenance_registry(
        REGISTRY_PATH
    )

    eligible, reason = (
        provenance_backtest_eligibility(
            Path(
                "configs/universe_snapshots/"
                "2026-07-08_top125_yahoo.csv"
            ),
            "market_cap",
            registry,
        )
    )

    assert eligible is False
    assert reason == (
        "provenance_rejected_current_snapshot"
    )


def test_registry_contains_evidence() -> None:
    registry = json.loads(
        REGISTRY_PATH.read_text(
            encoding="utf-8"
        )
    )

    target = next(
        row
        for row in registry["sources"]
        if row["path"].endswith(
            "salarium_training_with_macro.csv"
        )
    )

    assert len(target["evidence"]) >= 5

    assert (
        "historical sector attribution"
        in target["prohibited_uses"]
    )
