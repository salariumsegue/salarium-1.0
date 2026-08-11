import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(
    "scripts/"
    "build_sec_pit_factor_panel.py"
)

SPEC = importlib.util.spec_from_file_location(
    "sec_pit_factor",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)


def test_market_cap_uses_close_not_adjusted_close() -> None:
    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert (
        'result["close"]'
        in source
    )

    assert (
        "adjusted close is not used"
        in source.lower()
    )


def test_asof_merge_blocks_future_information() -> None:
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-10",
                    "2025-01-20",
                ]
            ),
            "ticker": [
                "AAA",
                "AAA",
            ],
            "close": [
                10.0,
                11.0,
            ],
        }
    )

    events = pd.DataFrame(
        {
            "requested_ticker": [
                "AAA"
            ],
            "available_date": (
                pd.to_datetime(
                    ["2025-01-15"]
                )
            ),
            "value": [
                100.0
            ],
            "filed": (
                pd.to_datetime(
                    ["2025-01-14"]
                )
            ),
            "end": (
                pd.to_datetime(
                    ["2024-12-31"]
                )
            ),
            "form": [
                "10-K"
            ],
            "concept": [
                "Assets"
            ],
            "accession_number": [
                "x"
            ],
        }
    )

    merged = MODULE.merge_field_asof(
        panel,
        events,
        "assets",
    )

    first = merged.loc[
        merged["date"]
        == pd.Timestamp(
            "2025-01-10"
        ),
        "assets",
    ].iloc[0]

    second = merged.loc[
        merged["date"]
        == pd.Timestamp(
            "2025-01-20"
        ),
        "assets",
    ].iloc[0]

    assert np.isnan(first)
    assert second == 100.0


def test_annual_duration_filter_rejects_quarter() -> None:
    ledger = pd.DataFrame(
        {
            "canonical_field": [
                "net_income",
                "net_income",
            ],
            "requested_ticker": [
                "AAA",
                "AAA",
            ],
            "available_date": (
                pd.to_datetime(
                    [
                        "2025-02-01",
                        "2025-02-01",
                    ]
                )
            ),
            "value": [
                10.0,
                40.0,
            ],
            "filed": (
                pd.to_datetime(
                    [
                        "2025-01-31",
                        "2025-01-31",
                    ]
                )
            ),
            "start": (
                pd.to_datetime(
                    [
                        "2024-10-01",
                        "2024-01-01",
                    ]
                )
            ),
            "end": (
                pd.to_datetime(
                    [
                        "2024-12-31",
                        "2024-12-31",
                    ]
                )
            ),
            "form": [
                "10-K",
                "10-K",
            ],
            "concept": [
                "NetIncomeLoss",
                "NetIncomeLoss",
            ],
            "accession_number": [
                "x",
                "x",
            ],
            "concept_priority": [
                0,
                0,
            ],
            "period_days": [
                91,
                365,
            ],
        }
    )

    events = (
        MODULE.select_field_events(
            ledger,
            "net_income",
        )
    )

    assert len(events) == 1
    assert events.iloc[0]["value"] == 40.0


def test_sec_ledger_is_registered_as_verified() -> None:
    policy = json.loads(
        Path(
            "configs/"
            "security_metadata_policy.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    source = next(
        row
        for row in policy[
            "verified_point_in_time_sources"
        ]
        if row["path"].endswith(
            "sec_point_in_time_"
            "fundamental_facts.csv"
        )
    )

    assert (
        source[
            "point_in_time_verified"
        ]
        is True
    )


def test_factor_definitions_present() -> None:
    required = {
        "market_cap",
        "log_market_cap",
        "book_to_market",
        "earnings_yield",
        "roa",
        "roe",
        "operating_profitability",
        "gross_profitability",
        "leverage",
    }

    assert required.issubset(
        set(
            MODULE.RAW_FACTORS
        )
    )
