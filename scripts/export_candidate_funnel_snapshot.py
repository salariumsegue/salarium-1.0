from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CANDIDATE_COLUMNS = {
    "portfolio_candidate_rank",
    "ticker",
    "agentic_score",
    "advanced_score",
    "model_score",
    "quantitative_score",
    "agent_fundamental_score",
    "agent_risk_score",
    "agent_catalyst_score",
    "agent_macro_fit_score",
    "agent_evidence_score",
    "agent_confidence",
    "agent_red_flag_count",
    "agent_thesis",
    "agent_risk_summary",
    "agent_catalyst_summary",
    "agent_evidence_ids",
}

EXPECTED_STAGE_COUNTS = {
    "universe": 2000,
    "quantitative": 200,
    "advanced": 50,
    "agentic": 30,
}


def resolve_project_path(
    value: str | Path,
) -> Path:
    path = Path(value).expanduser()

    if not path.is_absolute():
        path = ROOT / path

    return path.resolve()


def portable_path(
    path: Path,
) -> str:
    """Return a repository-relative path when possible.

    External paths remain absolute so the exporter also
    works in isolated tests and temporary environments.
    """
    resolved_path = path.expanduser().resolve()
    resolved_root = ROOT.resolve()

    try:
        return str(
            resolved_path.relative_to(
                resolved_root
            )
        )
    except ValueError:
        return str(resolved_path)


def sha256_path(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def json_safe(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return (
            None
            if np.isnan(value)
            else float(value)
        )

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    return value


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    records: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        payload = json.loads(line)

        if not isinstance(payload, dict):
            raise ValueError(
                f"{path}:{line_number} "
                "must contain a JSON object."
            )

        records.append(payload)

    return records


def split_evidence_ids(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    try:
        if pd.isna(value):
            return []
    except (
        TypeError,
        ValueError,
    ):
        pass

    return list(
        dict.fromkeys(
            item.strip()
            for item in str(value).split("|")
            if item.strip()
        )
    )


def find_latest_complete_run(
    funnel_root: Path,
) -> tuple[
    Path,
    dict[str, Any],
]:
    candidates: list[
        tuple[
            str,
            float,
            Path,
            dict[str, Any],
        ]
    ] = []

    for manifest_path in funnel_root.glob(
        "*/manifest.json"
    ):
        try:
            payload = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

        if payload.get("status") != "complete":
            continue

        run_directory = manifest_path.parent

        if not (
            run_directory
            / "portfolio_candidates.csv"
        ).is_file():
            continue

        candidates.append(
            (
                str(
                    payload.get(
                        "created_at_utc",
                        "",
                    )
                ),
                manifest_path.stat().st_mtime,
                run_directory,
                payload,
            )
        )

    if not candidates:
        raise FileNotFoundError(
            "No complete candidate-funnel "
            "run was found."
        )

    _, _, run_directory, payload = max(
        candidates,
        key=lambda item: (
            item[0],
            item[1],
        ),
    )

    return (
        run_directory,
        payload,
    )


def evidence_metadata(
    *,
    manifest: dict[str, Any],
    contract_path: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    set[str],
    set[str],
    float,
]:
    contract = json.loads(
        contract_path.read_text(
            encoding="utf-8"
        )
    )

    primary_types = set(
        contract.get(
            "primary_source_types",
            [],
        )
    )

    catalyst_types = set(
        contract.get(
            "catalyst_source_types",
            [],
        )
    )

    confidence_cap = float(
        contract.get(
            "confidence_cap_without_primary_source",
            0.65,
        )
    )

    agent_input = (
        manifest.get("agent_input")
        or {}
    )

    path_value = agent_input.get("path")

    if not path_value:
        return (
            {},
            primary_types,
            catalyst_types,
            confidence_cap,
        )

    assessment_path = resolve_project_path(
        path_value
    )

    evidence_path = (
        assessment_path.parent
        / "evidence_registry.jsonl"
    )

    records = read_jsonl(
        evidence_path
    )

    index = {
        str(record["evidence_id"]): record
        for record in records
        if "evidence_id" in record
    }

    return (
        index,
        primary_types,
        catalyst_types,
        confidence_cap,
    )


def numeric_or_none(
    value: Any,
) -> float | None:
    try:
        number = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not np.isfinite(number):
        return None

    return number


def integer_or_none(
    value: Any,
) -> int | None:
    number = numeric_or_none(value)

    if number is None:
        return None

    return int(number)


def text_or_none(
    value: Any,
) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    text = str(value).strip()

    return text or None


def candidate_as_of_date(
    frame: pd.DataFrame,
) -> str | None:
    for column in [
        "date",
        "last_date",
    ]:
        if column not in frame.columns:
            continue

        values = pd.to_datetime(
            frame[column],
            errors="coerce",
        ).dropna()

        if not values.empty:
            return (
                values.max()
                .date()
                .isoformat()
            )

    return None


def validate_run(
    manifest: dict[str, Any],
    candidates: pd.DataFrame,
) -> None:
    stage_counts = manifest.get(
        "stage_counts",
        {},
    )

    for stage, expected in (
        EXPECTED_STAGE_COUNTS.items()
    ):
        actual = stage_counts.get(stage)

        if actual != expected:
            raise ValueError(
                f"{stage} count is {actual}; "
                f"expected {expected}."
            )

    final_count = int(
        stage_counts.get(
            "portfolio_candidates",
            len(candidates),
        )
    )

    if not 10 <= final_count <= 30:
        raise ValueError(
            "Final candidate count must "
            "remain between 10 and 30."
        )

    if len(candidates) != final_count:
        raise ValueError(
            "Portfolio-candidate CSV row count "
            "does not match the manifest."
        )

    missing = (
        REQUIRED_CANDIDATE_COLUMNS
        - set(candidates.columns)
    )

    if missing:
        raise ValueError(
            "Candidate data is missing: "
            + ", ".join(sorted(missing))
        )

    if candidates["ticker"].duplicated().any():
        raise ValueError(
            "Candidate data contains "
            "duplicate tickers."
        )

    expected_ranks = list(
        range(
            1,
            len(candidates) + 1,
        )
    )

    observed_ranks = (
        pd.to_numeric(
            candidates[
                "portfolio_candidate_rank"
            ],
            errors="raise",
        )
        .astype(int)
        .tolist()
    )

    if observed_ranks != expected_ranks:
        raise ValueError(
            "Portfolio candidate ranks are "
            "not contiguous and ordered."
        )


def build_snapshot(
    *,
    run_directory: Path,
    manifest: dict[str, Any],
    contract_path: Path,
) -> dict[str, Any]:
    candidates_path = (
        run_directory
        / "portfolio_candidates.csv"
    )

    candidates = pd.read_csv(
        candidates_path,
        low_memory=False,
    ).sort_values(
        "portfolio_candidate_rank"
    ).reset_index(drop=True)

    candidates["ticker"] = (
        candidates["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    validate_run(
        manifest,
        candidates,
    )

    (
        evidence,
        primary_types,
        catalyst_types,
        confidence_cap,
    ) = evidence_metadata(
        manifest=manifest,
        contract_path=contract_path,
    )

    candidate_records: list[
        dict[str, Any]
    ] = []

    for row in candidates.to_dict(
        orient="records"
    ):
        evidence_ids = split_evidence_ids(
            row.get(
                "agent_evidence_ids"
            )
        )

        source_types = {
            str(
                evidence[evidence_id].get(
                    "source_type",
                    "",
                )
            )
            for evidence_id in evidence_ids
            if evidence_id in evidence
        }

        has_primary = bool(
            source_types
            & primary_types
        )

        has_catalyst = bool(
            source_types
            & catalyst_types
        )

        candidate_records.append(
            {
                "rank": int(
                    row[
                        "portfolio_candidate_rank"
                    ]
                ),
                "ticker": row["ticker"],
                "company_name": text_or_none(
                    row.get(
                        "company_name"
                    )
                ),
                "exchange": text_or_none(
                    row.get(
                        "exchange"
                    )
                ),
                "security_type": text_or_none(
                    row.get(
                        "security_type"
                    )
                ),
                "last_price": numeric_or_none(
                    row.get(
                        "last_price"
                    )
                ),
                "median_dollar_volume": (
                    numeric_or_none(
                        row.get(
                            "median_dollar_volume"
                        )
                    )
                ),
                "scores": {
                    "agentic": numeric_or_none(
                        row.get(
                            "agentic_score"
                        )
                    ),
                    "advanced": numeric_or_none(
                        row.get(
                            "advanced_score"
                        )
                    ),
                    "model": numeric_or_none(
                        row.get(
                            "model_score"
                        )
                    ),
                    "quantitative": (
                        numeric_or_none(
                            row.get(
                                "quantitative_score"
                            )
                        )
                    ),
                    "fundamental": (
                        numeric_or_none(
                            row.get(
                                "agent_fundamental_score"
                            )
                        )
                    ),
                    "risk": numeric_or_none(
                        row.get(
                            "agent_risk_score"
                        )
                    ),
                    "catalyst": numeric_or_none(
                        row.get(
                            "agent_catalyst_score"
                        )
                    ),
                    "macro_fit": numeric_or_none(
                        row.get(
                            "agent_macro_fit_score"
                        )
                    ),
                    "evidence": numeric_or_none(
                        row.get(
                            "agent_evidence_score"
                        )
                    ),
                    "confidence": numeric_or_none(
                        row.get(
                            "agent_confidence"
                        )
                    ),
                },
                "model_uncertainty": (
                    numeric_or_none(
                        row.get(
                            "model_uncertainty"
                        )
                    )
                ),
                "drawdown_resilience": (
                    numeric_or_none(
                        row.get(
                            "drawdown_resilience"
                        )
                    )
                ),
                "data_quality_score": (
                    numeric_or_none(
                        row.get(
                            "data_quality_score"
                        )
                    )
                ),
                "red_flag_count": (
                    integer_or_none(
                        row.get(
                            "agent_red_flag_count"
                        )
                    )
                    or 0
                ),
                "evidence_count": (
                    integer_or_none(
                        row.get(
                            "agent_evidence_count"
                        )
                    )
                    or len(evidence_ids)
                ),
                "source_types": sorted(
                    source_type
                    for source_type in source_types
                    if source_type
                ),
                "primary_evidence_supported": (
                    has_primary
                ),
                "external_catalyst_evidence": (
                    has_catalyst
                ),
                "review_status": (
                    "primary_evidence_supported"
                    if has_primary
                    else "internal_evidence_only"
                ),
                "thesis": text_or_none(
                    row.get(
                        "agent_thesis"
                    )
                ),
                "risk_summary": text_or_none(
                    row.get(
                        "agent_risk_summary"
                    )
                ),
                "catalyst_summary": (
                    text_or_none(
                        row.get(
                            "agent_catalyst_summary"
                        )
                    )
                ),
            }
        )

    stage_counts = {
        key: int(value)
        for key, value
        in manifest[
            "stage_counts"
        ].items()
    }

    input_count = int(
        (
            manifest.get("input")
            or {}
        ).get(
            "rows",
            stage_counts[
                "universe"
            ],
        )
    )

    neutral_lower = 0.45
    neutral_upper = 0.55

    primary_count = sum(
        candidate[
            "primary_evidence_supported"
        ]
        for candidate in candidate_records
    )

    catalyst_count = sum(
        candidate[
            "external_catalyst_evidence"
        ]
        for candidate in candidate_records
    )

    red_flag_free_count = sum(
        candidate[
            "red_flag_count"
        ]
        == 0
        for candidate in candidate_records
    )

    high_confidence_count = sum(
        (
            candidate[
                "scores"
            ][
                "confidence"
            ]
            or 0.0
        )
        > confidence_cap
        for candidate in candidate_records
    )

    neutral_fundamental_count = sum(
        candidate["scores"][
            "fundamental"
        ]
        is not None
        and neutral_lower
        <= candidate["scores"][
            "fundamental"
        ]
        <= neutral_upper
        for candidate in candidate_records
    )

    neutral_catalyst_count = sum(
        candidate["scores"][
            "catalyst"
        ]
        is not None
        and neutral_lower
        <= candidate["scores"][
            "catalyst"
        ]
        <= neutral_upper
        for candidate in candidate_records
    )

    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "system": {
            "name": "Salarium",
            "surface": (
                "Candidate Intelligence Funnel"
            ),
            "status": (
                "complete_internal_evidence_baseline"
            ),
        },
        "provenance": {
            "run_id": manifest.get(
                "run_id"
            ),
            "run_created_at_utc": (
                manifest.get(
                    "created_at_utc"
                )
            ),
            "source_manifest": portable_path(
                run_directory
                / "manifest.json"
            ),
            "git": manifest.get(
                "git",
                {},
            ),
        },
        "as_of_date": candidate_as_of_date(
            candidates
        ),
        "architecture": {
            "stages": [
                {
                    "key": "valid_source",
                    "label": (
                        "Valid Securities"
                    ),
                    "count": input_count,
                    "description": (
                        "Discovery securities with "
                        "valid current feature data."
                    ),
                },
                {
                    "key": "universe",
                    "label": (
                        "Broad Research Universe"
                    ),
                    "count": stage_counts[
                        "universe"
                    ],
                    "description": (
                        "Liquidity and history "
                        "governed universe."
                    ),
                },
                {
                    "key": "quantitative",
                    "label": (
                        "Quantitative Screen"
                    ),
                    "count": stage_counts[
                        "quantitative"
                    ],
                    "description": (
                        "Fast cross-sectional "
                        "technical screening."
                    ),
                },
                {
                    "key": "advanced",
                    "label": (
                        "Advanced Evaluation"
                    ),
                    "count": stage_counts[
                        "advanced"
                    ],
                    "description": (
                        "Hardened model, uncertainty, "
                        "risk and data quality."
                    ),
                },
                {
                    "key": "agentic",
                    "label": (
                        "Agentic Research"
                    ),
                    "count": stage_counts[
                        "agentic"
                    ],
                    "description": (
                        "Evidence-governed "
                        "qualitative assessment."
                    ),
                },
                {
                    "key": (
                        "portfolio_candidates"
                    ),
                    "label": (
                        "Research Candidates"
                    ),
                    "count": stage_counts[
                        "portfolio_candidates"
                    ],
                    "description": (
                        "Final monitored candidates, "
                        "not portfolio weights."
                    ),
                },
            ],
            "stage_counts": stage_counts,
        },
        "evidence_summary": {
            "candidate_count": len(
                candidate_records
            ),
            "primary_evidence_supported": (
                primary_count
            ),
            "internal_evidence_only": (
                len(candidate_records)
                - primary_count
            ),
            "external_catalyst_evidence": (
                catalyst_count
            ),
            "neutral_catalyst_assessments": (
                neutral_catalyst_count
            ),
            "fundamental_neutral_assessments": (
                neutral_fundamental_count
            ),
            "red_flag_free_candidates": (
                red_flag_free_count
            ),
            "high_confidence_candidates": (
                high_confidence_count
            ),
            "confidence_cap_without_primary": (
                confidence_cap
            ),
        },
        "candidates": candidate_records,
        "disclosures": [
            (
                "These are research candidates, "
                "not portfolio weights, trade "
                "instructions, or investment advice."
            ),
            (
                "The current qualitative layer is "
                "an internal-evidence baseline."
            ),
            (
                "Company-specific catalysts were "
                "not asserted without accepted "
                "external catalyst evidence."
            ),
            (
                "Neutral fundamental assessments "
                "indicate insufficient primary "
                "evidence, not a positive or "
                "negative fundamental conclusion."
            ),
            (
                "Historical model research remains "
                "subject to the documented "
                "survivorship-bias limitation."
            ),
        ],
    }


def write_snapshot(
    *,
    snapshot: dict[str, Any],
    output_path: Path,
) -> tuple[
    Path,
    str,
]:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            json_safe(snapshot),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    temporary = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temporary.write_bytes(encoded)
    temporary.replace(output_path)

    digest = hashlib.sha256(
        encoded
    ).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "artifact": output_path.name,
        "sha256": digest,
        "size_bytes": len(encoded),
        "generated_at_utc": snapshot[
            "generated_at_utc"
        ],
        "candidate_run_id": snapshot[
            "provenance"
        ][
            "run_id"
        ],
        "candidate_count": len(
            snapshot["candidates"]
        ),
    }

    manifest_path = (
        output_path.parent
        / (
            output_path.stem
            + "_manifest.json"
        )
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return (
        manifest_path,
        digest,
    )


def main() -> int:
    parser = argparse.ArgumentParser()

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

    parser.add_argument(
        "--output",
        default=(
            "web/public/data/"
            "candidate_funnel_snapshot.json"
        ),
    )

    args = parser.parse_args()

    run_directory, manifest = (
        find_latest_complete_run(
            resolve_project_path(
                args.funnel_root
            )
        )
    )

    snapshot = build_snapshot(
        run_directory=run_directory,
        manifest=manifest,
        contract_path=resolve_project_path(
            args.contract
        ),
    )

    output_path = resolve_project_path(
        args.output
    )

    manifest_path, digest = (
        write_snapshot(
            snapshot=snapshot,
            output_path=output_path,
        )
    )

    print(
        "CANDIDATE_WEBSITE_EXPORT_STATUS=PASS"
    )

    print(
        "Run:",
        snapshot[
            "provenance"
        ][
            "run_id"
        ],
    )

    print(
        "Candidates:",
        len(
            snapshot[
                "candidates"
            ]
        ),
    )

    print(
        "Primary-evidence supported:",
        snapshot[
            "evidence_summary"
        ][
            "primary_evidence_supported"
        ],
    )

    print(
        "Snapshot:",
        output_path,
    )

    print(
        "Manifest:",
        manifest_path,
    )

    print(
        "SHA-256:",
        digest,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
