import pandas as pd
import pytest

from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
    EXCLUDED_FEATURES,
    MACRO_USAGE_POLICY,
    audit_feature_frame,
)


def test_primary_features_exclude_duplicate_return() -> None:
    assert "return_5d" not in CORE_TECHNICAL_FEATURES
    assert "momentum_5d" in CORE_TECHNICAL_FEATURES
    assert "return_5d" in EXCLUDED_FEATURES


def test_macro_is_not_approved_as_core_ranker() -> None:
    assert (
        MACRO_USAGE_POLICY["direct_ranking_model"]
        == "rejected_by_equivalent_walkforward_test"
    )


def test_feature_audit_detects_exact_duplicate() -> None:
    frame = pd.DataFrame(
        {
            "return_5d": [0.1, 0.2, -0.1],
            "momentum_5d": [0.1, 0.2, -0.1],
            "return_1d": [0.01, -0.02, 0.03],
        }
    )

    audit = audit_feature_frame(
        frame,
        candidate_features=[
            "return_5d",
            "momentum_5d",
            "return_1d",
        ],
    )

    assert {
        "left": "return_5d",
        "right": "momentum_5d",
    } in audit["exact_duplicate_pairs"]


def test_feature_audit_reports_missing_columns() -> None:
    frame = pd.DataFrame(
        {
            "return_1d": [0.01, 0.02],
        }
    )

    audit = audit_feature_frame(
        frame,
        candidate_features=[
            "return_1d",
            "momentum_5d",
        ],
    )

    assert audit["missing_candidate_features"] == [
        "momentum_5d"
    ]


def test_invalid_correlation_threshold_raises() -> None:
    frame = pd.DataFrame(
        {
            "return_1d": [0.01, 0.02],
        }
    )

    with pytest.raises(ValueError):
        audit_feature_frame(
            frame,
            correlation_threshold=1.1,
        )
