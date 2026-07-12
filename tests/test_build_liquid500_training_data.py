from pathlib import Path

import pandas as pd
import pytest

from scripts.build_liquid500_training_data import (
    BASE_MACRO_COLUMNS,
    merge_panel_with_macro,
    normalize_dates,
    prepare_macro_daily,
)


def macro_rows() -> pd.DataFrame:
    base = {
        "macro_signal_score": 0.1,
        "macro_tone_score": 0.2,
        "surprise_num": 1.0,
        "inflation_num": 0.0,
        "growth_num": 1.0,
        "rate_policy_num": 0.0,
        "liquidity_num": 0.0,
        "reaction_quality_num": 0.0,
        "five_day_market_bias_score": 0.1,
        "five_day_bias_num": 1.0,
        "macro_confidence": 0.8,
    }

    return pd.DataFrame(
        [
            {
                "date": "2025-01-02",
                "ticker": "AAPL",
                **base,
            },
            {
                "date": "2025-01-02",
                "ticker": "MSFT",
                **base,
            },
            {
                "date": "2025-01-03",
                "ticker": "AAPL",
                **base,
            },
        ]
    )


def test_normalize_dates_handles_strings() -> None:
    result = normalize_dates(
        pd.Series(
            [
                "2025-01-02",
                "2025-01-03",
            ]
        )
    )

    assert pd.api.types.is_datetime64_any_dtype(
        result
    )

    assert result.iloc[0] == pd.Timestamp(
        "2025-01-02"
    )


def test_macro_daily_deduplicates_global_dates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "macro.csv"
    macro_rows().to_csv(path, index=False)

    daily, macro_columns = (
        prepare_macro_daily(path)
    )

    assert len(daily) == 2

    assert set(BASE_MACRO_COLUMNS).issubset(
        macro_columns
    )

    assert "macro_regime" in daily.columns
    assert "risk_state" in daily.columns


def test_macro_daily_rejects_same_date_inconsistency(
    tmp_path: Path,
) -> None:
    frame = macro_rows()
    frame.loc[1, "growth_num"] = -1.0

    path = tmp_path / "macro.csv"
    frame.to_csv(path, index=False)

    with pytest.raises(
        ValueError,
        match="vary within the same date",
    ):
        prepare_macro_daily(path)


def test_merge_normalizes_datetime_and_string_dates() -> None:
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-02",
                    "2025-01-03",
                    ]
            ),
            "ticker": [
                "AAPL",
                "AAPL",
            ],
            "target_5d_return": [
                0.01,
                0.02,
            ],
        }
    )

    macro = pd.DataFrame(
        {
            "date": [
                "2025-01-02",
                "2025-01-03",
            ],
            "macro_signal_score": [
                0.1,
                0.2,
            ],
        }
    )

    merged, statistics = (
        merge_panel_with_macro(
            panel,
            macro,
        )
    )

    assert len(merged) == 2
    assert statistics[
        "missing_macro_date_count"
    ] == 0

    assert statistics[
        "date_coverage_rate"
    ] == pytest.approx(1.0)
