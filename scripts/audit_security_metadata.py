from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(
    __file__
).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from src.research.security_metadata_policy import (
    backtest_eligibility,
    classify_temporal_structure,
    detect_metadata_columns,
    has_date_column,
    has_ticker_column,
    load_policy,
)


SCAN_DIRECTORIES = (
    Path("configs/universe_snapshots"),
    Path("data/processed"),
    Path("data/raw"),
)

IMPORTANT_GAPS = (
    "sector",
    "industry",
    "market_cap",
    "shares_outstanding",
    "book_value",
    "book_to_market",
    "price_to_book",
    "price_to_earnings",
    "revenue",
    "operating_income",
    "net_income",
    "return_on_equity",
    "return_on_assets",
    "gross_margin",
    "debt_to_equity",
)


def inspect_csv(
    path: Path,
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    try:
        columns = pd.read_csv(
            path,
            nrows=0,
        ).columns.tolist()
    except Exception as exc:
        return (
            {
                "path": str(path),
                "size_mb": (
                    path.stat().st_size
                    / 1024
                    / 1024
                ),
                "read_status": "error",
                "error": str(exc),
                "column_count": None,
                "has_ticker": None,
                "has_date": None,
                "metadata_field_count": None,
                "temporal_classification": (
                    "unavailable"
                ),
            },
            [],
        )

    detected = detect_metadata_columns(
        columns
    )

    temporal = (
        classify_temporal_structure(
            path,
            columns,
            detected,
        )
    )

    dataset_record = {
        "path": str(path),
        "size_mb": round(
            path.stat().st_size
            / 1024
            / 1024,
            3,
        ),
        "read_status": "ok",
        "error": "",
        "column_count": len(columns),
        "has_ticker": has_ticker_column(
            columns
        ),
        "has_date": has_date_column(
            columns
        ),
        "metadata_field_count": len(
            detected
        ),
        "temporal_classification": (
            temporal
        ),
    }

    fields = []

    for canonical, source_column in (
        detected.items()
    ):
        eligible, reason = (
            backtest_eligibility(
                path,
                canonical,
                policy,
            )
        )

        fields.append(
            {
                "path": str(path),
                "canonical_field": canonical,
                "source_column": (
                    source_column
                ),
                "temporal_classification": (
                    temporal
                ),
                "point_in_time_verified": bool(
                    eligible
                    and reason
                    == "verified_point_in_time_source"
                ),
                "historical_backtest_eligible": (
                    eligible
                ),
                "eligibility_reason": (
                    reason
                ),
            }
        )

    return dataset_record, fields


def discover_csvs() -> list[Path]:
    files: set[Path] = set()

    for directory in SCAN_DIRECTORIES:
        if not directory.exists():
            continue

        for path in directory.rglob(
            "*.csv"
        ):
            if path.is_file():
                files.add(path)

    return sorted(files)


def markdown_table(
    frame: pd.DataFrame,
) -> str:
    if frame.empty:
        return "_No rows detected._"

    columns = list(frame.columns)

    lines = [
        "| "
        + " | ".join(columns)
        + " |",
        "| "
        + " | ".join(
            ["---"] * len(columns)
        )
        + " |",
    ]

    for _, row in frame.iterrows():
        values = []

        for value in row:
            if isinstance(
                value,
                float,
            ):
                values.append(
                    f"{value:.3f}"
                )
            else:
                values.append(
                    str(value)
                )

        lines.append(
            "| "
            + " | ".join(values)
            + " |"
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--policy",
        default=(
            "configs/"
            "security_metadata_policy.json"
        ),
    )
    parser.add_argument(
        "--output-directory",
        default=(
            "reports/experiments"
        ),
    )

    args = parser.parse_args()

    policy_path = Path(
        args.policy
    )

    output_directory = Path(
        args.output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    policy = load_policy(
        policy_path
    )

    csv_paths = discover_csvs()

    dataset_records = []
    field_records = []

    for path in csv_paths:
        dataset, fields = (
            inspect_csv(
                path,
                policy,
            )
        )

        dataset_records.append(
            dataset
        )

        field_records.extend(
            fields
        )

    datasets = pd.DataFrame(
        dataset_records
    )

    fields = pd.DataFrame(
        field_records
    )

    if fields.empty:
        fields = pd.DataFrame(
            columns=[
                "path",
                "canonical_field",
                "source_column",
                "temporal_classification",
                "point_in_time_verified",
                "historical_backtest_eligible",
                "eligibility_reason",
            ]
        )

    available_fields = set(
        fields[
            "canonical_field"
        ].tolist()
    )

    verified_fields = set(
        fields.loc[
            fields[
                "historical_backtest_eligible"
            ]
            == True,
            "canonical_field",
        ].tolist()
    )

    gap_records = []

    for field in IMPORTANT_GAPS:
        available_anywhere = (
            field
            in available_fields
        )

        verified_for_backtest = (
            field
            in verified_fields
        )

        gap_records.append(
            {
                "field": field,
                "available_anywhere": (
                    available_anywhere
                ),
                "point_in_time_verified": (
                    verified_for_backtest
                ),
                "historical_backtest_status": (
                    "approved"
                    if verified_for_backtest
                    else "blocked"
                ),
                "next_action": (
                    "none"
                    if verified_for_backtest
                    else (
                        "verify_source_provenance"
                        if available_anywhere
                        else "source_data"
                    )
                ),
            }
        )

    gaps = pd.DataFrame(
        gap_records
    )

    datasets_path = (
        output_directory
        / "security_metadata_dataset_inventory.csv"
    )

    fields_path = (
        output_directory
        / "security_metadata_field_inventory.csv"
    )

    gaps_path = (
        output_directory
        / "security_metadata_gap_analysis.csv"
    )

    datasets.to_csv(
        datasets_path,
        index=False,
    )

    fields.to_csv(
        fields_path,
        index=False,
    )

    gaps.to_csv(
        gaps_path,
        index=False,
    )

    payload = {
        "schema_version": "1.0",
        "policy_path": str(
            policy_path
        ),
        "csv_files_scanned": len(
            datasets
        ),
        "files_with_metadata": int(
            (
                datasets[
                    "metadata_field_count"
                ]
                .fillna(0)
                > 0
            ).sum()
        )
        if not datasets.empty
        else 0,
        "metadata_fields_detected": sorted(
            available_fields
        ),
        "point_in_time_verified_fields": (
            sorted(
                verified_fields
            )
        ),
        "historical_backtest_blocked_fields": (
            sorted(
                set(IMPORTANT_GAPS)
                - verified_fields
            )
        ),
        "critical_rule": (
            "Current or merely dated metadata is "
            "not approved for historical attribution "
            "until point-in-time provenance is verified."
        ),
        "gap_analysis": gaps.to_dict(
            orient="records"
        ),
    }

    json_path = (
        output_directory
        / "security_metadata_audit.json"
    )

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    metadata_files = datasets[
        datasets[
            "metadata_field_count"
        ].fillna(0)
        > 0
    ].copy()

    report_lines = [
        "# Salarium Security Metadata Audit",
        "",
        "## Governance Rule",
        "",
        (
            "Current or merely dated security metadata "
            "must not be inserted into historical "
            "backtests unless its point-in-time "
            "provenance has been explicitly verified."
        ),
        "",
        "## Scan Summary",
        "",
        (
            f"- CSV files scanned: "
            f"{len(datasets)}"
        ),
        (
            f"- Files containing candidate metadata: "
            f"{len(metadata_files)}"
        ),
        (
            "- Candidate metadata fields detected: "
            + (
                ", ".join(
                    sorted(
                        available_fields
                    )
                )
                if available_fields
                else "none"
            )
        ),
        (
            "- Point-in-time verified fields: "
            + (
                ", ".join(
                    sorted(
                        verified_fields
                    )
                )
                if verified_fields
                else "none"
            )
        ),
        "",
        "## Files Containing Candidate Metadata",
        "",
        markdown_table(
            metadata_files[
                [
                    "path",
                    "size_mb",
                    "has_ticker",
                    "has_date",
                    "metadata_field_count",
                    "temporal_classification",
                ]
            ]
            if not metadata_files.empty
            else metadata_files
        ),
        "",
        "## Detected Metadata Fields",
        "",
        markdown_table(
            fields
        ),
        "",
        "## Historical Research Gap Analysis",
        "",
        markdown_table(
            gaps
        ),
        "",
        "## Interpretation",
        "",
        (
            "- `current_or_dated_snapshot` means the "
            "file can describe the universe at its "
            "snapshot date, but does not establish a "
            "historical point-in-time series."
        ),
        (
            "- `historical_panel_unverified` means a "
            "ticker/date panel exists, but provenance "
            "still must be verified before using it "
            "for historical factor or sector attribution."
        ),
        (
            "- `historical_backtest_status = blocked` "
            "is intentional. Salarium prefers missing "
            "data over look-ahead contamination."
        ),
        "",
    ]

    report_path = (
        output_directory
        / "security_metadata_audit.md"
    )

    report_path.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    print(
        "SECURITY_METADATA_AUDIT_STATUS=PASS"
    )
    print()
    print(
        f"CSV files scanned: {len(datasets)}"
    )
    print(
        "Files with candidate metadata:",
        len(metadata_files),
    )
    print(
        "Metadata fields detected:",
        (
            ", ".join(
                sorted(
                    available_fields
                )
            )
            if available_fields
            else "NONE"
        ),
    )
    print(
        "Point-in-time verified fields:",
        (
            ", ".join(
                sorted(
                    verified_fields
                )
            )
            if verified_fields
            else "NONE"
        ),
    )

    print()
    print(
        "=== HISTORICAL DATA GAPS ==="
    )

    print(
        gaps.to_string(
            index=False
        )
    )

    print()
    print(
        "Report:",
        report_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
