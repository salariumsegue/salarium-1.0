import json
from pathlib import Path

import pandas as pd
import pytest

from src.universe.discovery_plan import (
    build_discovery_plan,
    verify_discovery_plan,
    write_discovery_plan,
)


def make_candidates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "MSFT",
                "yahoo_symbol": "MSFT",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "is_active": True,
            },
            {
                "ticker": "AAPL",
                "yahoo_symbol": "AAPL",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "is_active": True,
            },
            {
                "ticker": "OLD",
                "yahoo_symbol": "OLD",
                "security_type": "COMMON_STOCK",
                "exchange": "NYSE",
                "is_active": False,
            },
        ]
    )


def test_plan_is_active_sorted_and_contiguous() -> None:
    plan = build_discovery_plan(
        make_candidates(),
        chunk_size=1,
    )

    assert list(plan["ticker"]) == [
        "AAPL",
        "MSFT",
    ]

    assert list(plan["plan_index"]) == [
        0,
        1,
    ]

    assert list(plan["chunk_id"]) == [
        0,
        1,
    ]


def test_plan_rejects_duplicate_tickers() -> None:
    frame = pd.concat(
        [
            make_candidates(),
            make_candidates().iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        build_discovery_plan(frame)


def test_plan_manifest_round_trip(
    tmp_path: Path,
) -> None:
    source_path = (
        tmp_path / "candidates.csv"
    )

    make_candidates().to_csv(
        source_path,
        index=False,
    )

    plan_path, manifest_path, manifest = (
        write_discovery_plan(
            source_path,
            tmp_path / "plans",
            chunk_size=1,
        )
    )

    plan, verified_manifest = (
        verify_discovery_plan(
            plan_path,
            manifest_path,
        )
    )

    assert len(plan) == 2
    assert (
        verified_manifest["plan_id"]
        == manifest["plan_id"]
    )


def test_tampered_plan_is_rejected(
    tmp_path: Path,
) -> None:
    source_path = (
        tmp_path / "candidates.csv"
    )

    make_candidates().to_csv(
        source_path,
        index=False,
    )

    plan_path, manifest_path, _ = (
        write_discovery_plan(
            source_path,
            tmp_path / "plans",
        )
    )

    plan_path.write_text(
        plan_path.read_text(
            encoding="utf-8"
        )
        + "tampered\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="hash",
    ):
        verify_discovery_plan(
            plan_path,
            manifest_path,
        )
