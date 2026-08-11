import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SCRIPT = Path(
    "scripts/"
    "build_current_candidate_funnel.py"
)

SPEC = importlib.util.spec_from_file_location(
    "current_funnel",
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


def test_advanced_model_uses_governed_features() -> None:
    assert (
        "return_5d"
        not in MODULE.CORE_TECHNICAL_FEATURES
    )

    assert (
        "relative_strength"
        in MODULE.CORE_TECHNICAL_FEATURES
    )


def test_drawdown_resilience() -> None:
    prices = pd.Series(
        [
            100.0,
            120.0,
            90.0,
        ]
    )

    result = (
        MODULE.maximum_drawdown_resilience(
            prices
        )
    )

    assert result == 0.75


def test_data_quality_score_is_bounded() -> None:
    frame = pd.DataFrame(
        {
            column: np.ones(252)
            for column in (
                MODULE.LOCAL_TECHNICAL_FEATURES
            )
        }
    )

    score = MODULE.data_quality_score(
        frame,
        expected_history_days=252,
    )

    assert score == 1.0


def test_advanced_contract_has_no_fake_walkforward_fields() -> None:
    import json

    payload = json.loads(
        Path(
            "configs/"
            "candidate_funnel.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    advanced = next(
        stage
        for stage in payload["stages"]
        if stage["name"] == "advanced"
    )

    columns = {
        item["column"]
        for item in advanced["features"]
    }

    assert "walkforward_ic" not in columns

    assert (
        "walkforward_excess_sharpe"
        not in columns
    )

    assert {
        "model_score",
        "model_uncertainty",
        "drawdown_resilience",
        "liquidity_efficiency",
        "data_quality_score",
        "quantitative_score",
    } == columns



def write_minimal_cache(
    tmp_path: Path,
    ticker: str,
) -> Path:
    cache = tmp_path / f"{ticker}.csv"

    pd.DataFrame(
        {
            "date": [
                "2026-07-10",
            ],
            "ticker": [
                ticker,
            ],
            "open": [
                10.0,
            ],
            "high": [
                11.0,
            ],
            "low": [
                9.0,
            ],
            "close": [
                10.5,
            ],
            "volume": [
                1000,
            ],
            "adj_close": [
                10.5,
            ],
        }
    ).to_csv(
        cache,
        index=False,
    )

    return cache


def test_invalid_price_history_is_audited_and_skipped(
    tmp_path: Path,
) -> None:
    class InvalidBuilder:
        @staticmethod
        def build_security_features(
            history: pd.DataFrame,
            ticker: str,
        ) -> pd.DataFrame:
            raise ValueError(
                "Price history contains "
                "invalid OHLCV values."
            )

    cache = write_minimal_cache(
        tmp_path,
        "BAD",
    )

    candidates = pd.DataFrame(
        {
            "ticker": [
                "BAD",
            ],
            "history_days": [
                2141,
            ],
        }
    )

    features, audit = (
        MODULE.build_current_features(
            candidates,
            {
                "BAD": cache,
            },
            InvalidBuilder,
            pd.Timestamp(
                "2026-07-10"
            ),
        )
    )

    assert features.empty

    assert (
        audit.iloc[0]["status"]
        == "rejected_invalid_price_history"
    )

    assert (
        audit.iloc[0]["ticker"]
        == "BAD"
    )


def test_unexpected_builder_error_still_fails(
    tmp_path: Path,
) -> None:
    class BrokenBuilder:
        @staticmethod
        def build_security_features(
            history: pd.DataFrame,
            ticker: str,
        ) -> pd.DataFrame:
            raise RuntimeError(
                "unexpected programming defect"
            )

    cache = write_minimal_cache(
        tmp_path,
        "BUG",
    )

    candidates = pd.DataFrame(
        {
            "ticker": [
                "BUG",
            ],
            "history_days": [
                2141,
            ],
        }
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected programming defect",
    ):
        MODULE.build_current_features(
            candidates,
            {
                "BUG": cache,
            },
            BrokenBuilder,
            pd.Timestamp(
                "2026-07-10"
            ),
        )
