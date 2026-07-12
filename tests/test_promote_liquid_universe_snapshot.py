import pandas as pd
import pytest

from scripts.promote_liquid_universe_snapshot import (
    PromotionRules,
    validate_promotion,
)


def make_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
    dict,
]:
    metrics = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "last_price": 200.0,
                "median_dollar_volume": 30_000_000.0,
                "history_days": 1_000,
            },
            {
                "ticker": "MSFT",
                "last_price": 400.0,
                "median_dollar_volume": 20_000_000.0,
                "history_days": 1_000,
            },
            {
                "ticker": "TEST",
                "last_price": 20.0,
                "median_dollar_volume": 10_000_000.0,
                "history_days": 1_000,
            },
        ]
    )

    selected = pd.DataFrame(
        [
            {
                "universe_rank": 1,
                "ticker": "AAPL",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "is_active": True,
                "last_price": 200.0,
                "median_dollar_volume": 30_000_000.0,
                "history_days": 1_000,
                "last_date": "2026-07-10",
            },
            {
                "universe_rank": 2,
                "ticker": "MSFT",
                "security_type": "COMMON_STOCK",
                "exchange": "NASDAQ",
                "is_active": True,
                "last_price": 400.0,
                "median_dollar_volume": 20_000_000.0,
                "history_days": 1_000,
                "last_date": "2026-07-10",
            },
        ]
    )

    exclusions = pd.DataFrame(
        {
            "ticker": [
                "AAPL",
                "MSFT",
                "TEST",
            ],
            "eligible": [
                True,
                True,
                True,
            ],
        }
    )

    progress = {
        "plan_id": "plan-1",
        "plan_sha256": "abc123",
        "plan_rows": 3,
        "completed_rows": 3,
        "completion_rate": 1.0,
        "status_counts": {
            "success": 3,
        },
    }

    manifest = {
        "plan_id": "plan-1",
        "plan_sha256": "abc123",
        "row_count": 3,
    }

    return (
        selected,
        metrics,
        exclusions,
        progress,
        manifest,
    )


def test_valid_promotion_passes() -> None:
    (
        selected,
        metrics,
        exclusions,
        progress,
        manifest,
    ) = make_inputs()

    summary = validate_promotion(
        selected,
        metrics,
        exclusions,
        progress,
        manifest,
        PromotionRules(
            maximum_size=2,
        ),
    )

    assert summary["selected_rows"] == 2
    assert summary["eligible_before_cap"] == 3
    assert summary["market_date"] == "2026-07-10"


def test_non_top_selection_is_rejected() -> None:
    (
        selected,
        metrics,
        exclusions,
        progress,
        manifest,
    ) = make_inputs()

    selected.loc[1, "ticker"] = "TEST"
    selected.loc[
        1,
        "median_dollar_volume",
    ] = 10_000_000.0

    with pytest.raises(
        ValueError,
        match="top eligible",
    ):
        validate_promotion(
            selected,
            metrics,
            exclusions,
            progress,
            manifest,
            PromotionRules(
                maximum_size=2,
            ),
        )


def test_stale_selected_security_is_rejected() -> None:
    (
        selected,
        metrics,
        exclusions,
        progress,
        manifest,
    ) = make_inputs()

    selected.loc[
        1,
        "last_date",
    ] = "2026-06-01"

    with pytest.raises(
        ValueError,
        match="stale",
    ):
        validate_promotion(
            selected,
            metrics,
            exclusions,
            progress,
            manifest,
            PromotionRules(
                maximum_size=2,
            ),
        )
