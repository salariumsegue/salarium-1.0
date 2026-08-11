from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.funnel.agent_research import (
    latest_waiting_run,
    load_contract,
    read_jsonl,
    validate_assessments,
)
from src.funnel.candidate_funnel import (
    sha256_path,
)


ASSESSMENT_COLUMNS = [
    "ticker",
    "agent_fundamental_score",
    "agent_risk_score",
    "agent_catalyst_score",
    "agent_macro_fit_score",
    "agent_confidence",
    "agent_red_flag_count",
    "agent_thesis",
    "agent_risk_summary",
    "agent_catalyst_summary",
    "agent_evidence_ids",
    "reviewer",
    "generated_at_utc",
]


def numeric(
    value: Any,
    default: float = float("nan"),
) -> float:
    try:
        converted = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default

    if not math.isfinite(converted):
        return default

    return converted


def bounded(
    value: float,
) -> float:
    return float(
        np.clip(
            value,
            0.0,
            1.0,
        )
    )


def percentile_rank(
    series: pd.Series,
    *,
    higher_is_better: bool,
) -> pd.Series:
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    ranked_values = (
        values
        if higher_is_better
        else -values
    )

    ranks = ranked_values.rank(
        pct=True,
        method="average",
    )

    return ranks.fillna(
        0.50
    ).clip(
        0.0,
        1.0,
    )


def format_metric(
    value: Any,
    decimals: int = 3,
) -> str:
    number = numeric(value)

    if not math.isfinite(number):
        return "unavailable"

    return f"{number:.{decimals}f}"


def packet_metrics(
    packet: dict[str, Any],
    evidence: dict[
        str,
        dict[str, Any],
    ],
    primary_types: set[str],
) -> dict[str, Any]:
    advanced = packet.get(
        "advanced_evaluation"
    ) or {}

    market = packet.get(
        "market_snapshot"
    ) or {}

    factors = packet.get(
        "point_in_time_factors"
    ) or {}

    macro = packet.get(
        "macro_state"
    ) or {}

    evidence_ids = [
        str(value)
        for value in packet.get(
            "evidence_ids",
            []
        )
    ]

    source_types = {
        str(
            evidence[
                evidence_id
            ][
                "source_type"
            ]
        )
        for evidence_id in evidence_ids
        if evidence_id in evidence
    }

    return {
        "ticker": str(
            packet["ticker"]
        ).upper(),
        "advanced_rank": numeric(
            advanced.get(
                "advanced_rank"
            )
        ),
        "advanced_score": numeric(
            advanced.get(
                "advanced_score"
            )
        ),
        "model_score": numeric(
            advanced.get(
                "model_score"
            )
        ),
        "model_uncertainty": numeric(
            advanced.get(
                "model_uncertainty"
            )
        ),
        "quantitative_score": numeric(
            advanced.get(
                "quantitative_score"
            )
        ),
        "drawdown_resilience": numeric(
            advanced.get(
                "drawdown_resilience"
            )
        ),
        "data_quality_score": numeric(
            advanced.get(
                "data_quality_score"
            )
        ),
        "volatility_20d": numeric(
            market.get(
                "volatility_20d"
            )
        ),
        "momentum_20d": numeric(
            market.get(
                "momentum_20d"
            )
        ),
        "relative_strength": numeric(
            market.get(
                "relative_strength"
            )
        ),
        "quality_composite_z": numeric(
            factors.get(
                "quality_composite_z"
            )
        ),
        "value_composite_z": numeric(
            factors.get(
                "value_composite_z"
            )
        ),
        "roa_z": numeric(
            factors.get(
                "roa_z"
            )
        ),
        "leverage_z": numeric(
            factors.get(
                "leverage_z"
            )
        ),
        "risk_state": str(
            macro.get(
                "risk_state",
                "neutral",
            )
        ).lower(),
        "evidence_ids": evidence_ids,
        "evidence_count": len(
            evidence_ids
        ),
        "source_type_count": len(
            source_types
        ),
        "has_primary": bool(
            source_types
            & primary_types
        ),
    }


def build_assessments(
    *,
    packets: list[dict[str, Any]],
    evidence_records: list[
        dict[str, Any]
    ],
    contract: dict[str, Any],
    generated_at_utc: str,
) -> pd.DataFrame:
    evidence = {
        str(
            record["evidence_id"]
        ): record
        for record in evidence_records
    }

    primary_types = set(
        contract[
            "primary_source_types"
        ]
    )

    metrics = pd.DataFrame(
        [
            packet_metrics(
                packet,
                evidence,
                primary_types,
            )
            for packet in packets
        ]
    )

    if metrics["ticker"].duplicated().any():
        raise ValueError(
            "Research packets contain "
            "duplicate tickers."
        )

    rank_definitions = {
        "model_rank": (
            "model_score",
            True,
        ),
        "quantitative_rank": (
            "quantitative_score",
            True,
        ),
        "uncertainty_rank": (
            "model_uncertainty",
            False,
        ),
        "drawdown_rank": (
            "drawdown_resilience",
            True,
        ),
        "quality_data_rank": (
            "data_quality_score",
            True,
        ),
        "volatility_rank": (
            "volatility_20d",
            False,
        ),
        "momentum_rank": (
            "momentum_20d",
            True,
        ),
        "relative_strength_rank": (
            "relative_strength",
            True,
        ),
        "fundamental_quality_rank": (
            "quality_composite_z",
            True,
        ),
        "fundamental_value_rank": (
            "value_composite_z",
            True,
        ),
        "roa_rank": (
            "roa_z",
            True,
        ),
        "leverage_safety_rank": (
            "leverage_z",
            False,
        ),
    }

    for output, (
        source,
        direction,
    ) in rank_definitions.items():
        metrics[output] = percentile_rank(
            metrics[source],
            higher_is_better=direction,
        )

    rows: list[dict[str, Any]] = []

    for metric in metrics.itertuples(
        index=False,
    ):
        fundamental_score = bounded(
            0.35
            * metric.fundamental_quality_rank
            + 0.30
            * metric.fundamental_value_rank
            + 0.20
            * metric.roa_rank
            + 0.15
            * metric.leverage_safety_rank
        )

        if not metric.has_primary:
            fundamental_score = 0.50

        risk_score = bounded(
            0.35
            * metric.drawdown_rank
            + 0.25
            * metric.volatility_rank
            + 0.20
            * metric.uncertainty_rank
            + 0.10
            * metric.quality_data_rank
            + 0.10
            * metric.leverage_safety_rank
        )

        risk_state = metric.risk_state

        if "risk_off" in risk_state:
            macro_fit_score = bounded(
                0.50
                * risk_score
                + 0.25
                * metric.volatility_rank
                + 0.15
                * metric.drawdown_rank
                + 0.10
                * metric.model_rank
            )

        elif "risk_on" in risk_state:
            macro_fit_score = bounded(
                0.40
                * metric.model_rank
                + 0.25
                * metric.quantitative_rank
                + 0.20
                * metric.momentum_rank
                + 0.15
                * metric.relative_strength_rank
            )

        else:
            macro_fit_score = bounded(
                0.40
                * metric.model_rank
                + 0.30
                * metric.quantitative_rank
                + 0.30
                * risk_score
            )

        catalyst_score = 0.50

        if metric.has_primary:
            confidence = bounded(
                0.68
                + 0.025
                * min(
                    metric.evidence_count,
                    5,
                )
                + 0.025
                * min(
                    metric.source_type_count,
                    4,
                )
            )
        else:
            confidence = 0.62

        severe_risk = any(
            [
                numeric(
                    metric.data_quality_score,
                    1.0,
                )
                < 0.85,
                numeric(
                    metric.drawdown_resilience,
                    1.0,
                )
                < 0.40,
                metric.uncertainty_rank
                < 0.08,
                metric.volatility_rank
                < 0.08,
            ]
        )

        coverage_gap = (
            not metric.has_primary
        )

        red_flag_count = int(
            severe_risk
            or coverage_gap
        )

        thesis = (
            f"{metric.ticker} ranks "
            f"{int(metric.advanced_rank)}/50 "
            "in the advanced queue. "
            f"The hardened model score is "
            f"{format_metric(metric.model_score, 5)} "
            "and the quantitative score is "
            f"{format_metric(metric.quantitative_score)}. "
            f"The evidence-grounded fundamental "
            f"assessment is {fundamental_score:.2f}; "
            "no missing fundamental value was "
            "replaced with current or future data."
        )

        risk_summary = (
            f"The risk assessment is "
            f"{risk_score:.2f}, based on "
            f"20-day volatility "
            f"{format_metric(metric.volatility_20d)}, "
            f"drawdown resilience "
            f"{format_metric(metric.drawdown_resilience)}, "
            f"model uncertainty "
            f"{format_metric(metric.model_uncertainty, 5)}, "
            "data coverage, and available "
            "point-in-time leverage evidence. "
            f"Red-flag count is {red_flag_count}."
        )

        catalyst_summary = (
            "No accepted company-specific catalyst "
            "source is present in the governed "
            "research packet. The catalyst score "
            "therefore remains neutral at 0.50 and "
            "is not inferred from price momentum, "
            "model rank, or market behavior."
        )

        rows.append(
            {
                "ticker": metric.ticker,
                "agent_fundamental_score": (
                    fundamental_score
                ),
                "agent_risk_score": (
                    risk_score
                ),
                "agent_catalyst_score": (
                    catalyst_score
                ),
                "agent_macro_fit_score": (
                    macro_fit_score
                ),
                "agent_confidence": (
                    confidence
                ),
                "agent_red_flag_count": (
                    red_flag_count
                ),
                "agent_thesis": thesis,
                "agent_risk_summary": (
                    risk_summary
                ),
                "agent_catalyst_summary": (
                    catalyst_summary
                ),
                "agent_evidence_ids": "|".join(
                    metric.evidence_ids
                ),
                "reviewer": (
                    "salarium_internal_"
                    "evidence_agent_v1"
                ),
                "generated_at_utc": (
                    generated_at_utc
                ),
            }
        )

    return pd.DataFrame(
        rows
    )[
        ASSESSMENT_COLUMNS
    ]


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        default=None,
    )

    parser.add_argument(
        "--funnel-root",
        default=(
            "results/"
            "candidate_funnel"
        ),
    )

    parser.add_argument(
        "--contract",
        default=(
            "configs/"
            "agent_research_contract.json"
        ),
    )

    args = parser.parse_args()

    run_directory = (
        Path(
            args.run_dir
        )
        if args.run_dir
        else latest_waiting_run(
            Path(
                args.funnel_root
            )
        )
    )

    research_directory = (
        run_directory
        / "agent_research"
    )

    packet_directory = (
        research_directory
        / "packets"
    )

    packet_paths = sorted(
        packet_directory.glob(
            "*.json"
        )
    )

    if len(packet_paths) != 50:
        raise RuntimeError(
            "Exactly 50 research packets "
            "are required."
        )

    packets = [
        json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        for path in packet_paths
    ]

    evidence_path = (
        research_directory
        / "evidence_registry.jsonl"
    )

    evidence_records = read_jsonl(
        evidence_path
    )

    contract = load_contract(
        Path(
            args.contract
        )
    )

    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    assessments = build_assessments(
        packets=packets,
        evidence_records=evidence_records,
        contract=contract,
        generated_at_utc=generated_at,
    )

    validated = validate_assessments(
        assessments=assessments,
        expected_tickers=[
            packet["ticker"]
            for packet in packets
        ],
        evidence_records=evidence_records,
        contract=contract,
    )

    output_path = (
        research_directory
        / "internal_evidence_assessments.csv"
    )

    assessments.to_csv(
        output_path,
        index=False,
    )

    preview_path = (
        research_directory
        / (
            "internal_evidence_"
            "assessments_validated_preview.csv"
        )
    )

    validated.to_csv(
        preview_path,
        index=False,
    )

    primary_tickers = 0

    evidence_by_id = {
        str(
            record["evidence_id"]
        ): record
        for record in evidence_records
    }

    primary_types = set(
        contract[
            "primary_source_types"
        ]
    )

    for packet in packets:
        source_types = {
            str(
                evidence_by_id[
                    evidence_id
                ][
                    "source_type"
                ]
            )
            for evidence_id in packet[
                "evidence_ids"
            ]
            if evidence_id
            in evidence_by_id
        }

        primary_tickers += int(
            bool(
                source_types
                & primary_types
            )
        )

    summary = {
        "schema_version": "1.0",
        "created_at_utc": generated_at,
        "run_directory": str(
            run_directory
        ),
        "assessment_path": str(
            output_path
        ),
        "assessment_sha256": (
            sha256_path(
                output_path
            )
        ),
        "validated_preview_path": str(
            preview_path
        ),
        "validated_preview_sha256": (
            sha256_path(
                preview_path
            )
        ),
        "ticker_count": len(
            assessments
        ),
        "primary_evidence_tickers": (
            primary_tickers
        ),
        "fundamental_neutral_tickers": (
            len(
                assessments
            )
            - primary_tickers
        ),
        "catalyst_policy": (
            "neutral_without_external_"
            "catalyst_evidence"
        ),
        "reviewer": (
            "salarium_internal_"
            "evidence_agent_v1"
        ),
    }

    summary_path = (
        research_directory
        / (
            "internal_evidence_"
            "assessment_manifest.json"
        )
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "INTERNAL_EVIDENCE_ASSESSMENT_STATUS=PASS"
    )

    print(
        "Assessments:",
        len(
            assessments
        ),
    )

    print(
        "Primary-evidence tickers:",
        primary_tickers,
    )

    print(
        "Fundamental-neutral tickers:",
        (
            len(
                assessments
            )
            - primary_tickers
        ),
    )

    print(
        "Catalyst scores:",
        "neutral at 0.50",
    )

    print(
        "ASSESSMENT_PATH=",
        output_path,
        sep="",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
