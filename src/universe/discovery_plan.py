from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_PLAN_COLUMNS: tuple[str, ...] = (
    "ticker",
    "yahoo_symbol",
    "security_type",
    "exchange",
    "is_active",
)


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Cannot hash missing file: {file_path}"
        )

    digest = hashlib.sha256()

    with file_path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _boolean_series(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def build_discovery_plan(
    candidates: pd.DataFrame,
    *,
    chunk_size: int = 250,
) -> pd.DataFrame:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    frame = candidates.copy()

    frame.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in frame.columns
    ]

    missing = [
        column
        for column in REQUIRED_PLAN_COLUMNS
        if column not in frame.columns
    ]

    if missing:
        raise KeyError(
            "Candidate file is missing discovery-plan columns: "
            + ", ".join(missing)
        )

    frame["ticker"] = (
        frame["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame["yahoo_symbol"] = (
        frame["yahoo_symbol"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame["security_type"] = (
        frame["security_type"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame["exchange"] = (
        frame["exchange"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame["is_active"] = _boolean_series(
        frame["is_active"]
    )

    if frame["ticker"].eq("").any():
        raise ValueError(
            "Candidate universe contains an empty ticker."
        )

    if frame["yahoo_symbol"].eq("").any():
        raise ValueError(
            "Candidate universe contains an empty Yahoo symbol."
        )

    if frame["ticker"].duplicated().any():
        duplicates = sorted(
            frame.loc[
                frame["ticker"].duplicated(keep=False),
                "ticker",
            ].unique()
        )

        raise ValueError(
            "Candidate universe contains duplicate tickers: "
            + ", ".join(duplicates)
        )

    plan = frame[
        frame["is_active"]
        & frame["security_type"].eq("COMMON_STOCK")
    ].copy()

    plan = (
        plan.sort_values(
            ["ticker", "yahoo_symbol"],
        )
        .reset_index(drop=True)
    )

    plan.insert(
        0,
        "plan_index",
        range(len(plan)),
    )

    plan.insert(
        1,
        "chunk_id",
        plan["plan_index"] // chunk_size,
    )

    leading_columns = [
        "plan_index",
        "chunk_id",
        "ticker",
        "yahoo_symbol",
        "security_type",
        "exchange",
        "is_active",
    ]

    remaining_columns = [
        column
        for column in plan.columns
        if column not in leading_columns
    ]

    return plan[
        leading_columns + remaining_columns
    ]


def canonical_plan_bytes(
    plan: pd.DataFrame,
) -> bytes:
    return plan.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8")


def write_discovery_plan(
    candidates_path: str | Path,
    output_directory: str | Path,
    *,
    chunk_size: int = 250,
    created_at_utc: datetime | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    source_path = Path(candidates_path)
    output_root = Path(output_directory)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Candidate file does not exist: {source_path}"
        )

    candidates = pd.read_csv(
        source_path,
        dtype=str,
        keep_default_na=False,
    )

    plan = build_discovery_plan(
        candidates,
        chunk_size=chunk_size,
    )

    payload = canonical_plan_bytes(plan)
    plan_sha256 = hashlib.sha256(payload).hexdigest()

    plan_id = (
        f"us_equities_{len(plan)}_"
        f"{plan_sha256[:12]}"
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    plan_path = output_root / f"{plan_id}.csv"
    manifest_path = output_root / f"{plan_id}.json"

    if plan_path.exists():
        if plan_path.read_bytes() != payload:
            raise RuntimeError(
                "Existing immutable plan differs from "
                "the newly generated plan."
            )
    else:
        temporary_path = plan_path.with_suffix(
            ".csv.tmp"
        )
        temporary_path.write_bytes(payload)
        temporary_path.replace(plan_path)

    timestamp = created_at_utc or datetime.now(
        timezone.utc
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "created_at_utc must be timezone-aware"
        )

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "plan_id": plan_id,
        "created_at_utc": (
            timestamp
            .astimezone(timezone.utc)
            .isoformat()
        ),
        "candidate_source": str(source_path),
        "candidate_source_sha256": sha256_file(
            source_path
        ),
        "plan_path": str(plan_path),
        "plan_sha256": plan_sha256,
        "row_count": len(plan),
        "chunk_size": chunk_size,
        "chunk_count": int(
            plan["chunk_id"].nunique()
        ),
        "active_only": True,
        "security_type": "COMMON_STOCK",
    }

    if manifest_path.exists():
        existing = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        if (
            existing.get("plan_sha256")
            != plan_sha256
        ):
            raise RuntimeError(
                "Existing plan manifest has a "
                "different plan hash."
            )

        manifest = existing
    else:
        temporary_manifest = (
            manifest_path.with_suffix(".json.tmp")
        )

        temporary_manifest.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_manifest.replace(
            manifest_path
        )

    return plan_path, manifest_path, manifest


def verify_discovery_plan(
    plan_path: str | Path,
    manifest_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    plan_file = Path(plan_path)
    manifest_file = Path(manifest_path)

    manifest = json.loads(
        manifest_file.read_text(
            encoding="utf-8"
        )
    )

    actual_sha256 = sha256_file(plan_file)
    expected_sha256 = manifest["plan_sha256"]

    if actual_sha256 != expected_sha256:
        raise ValueError(
            "Discovery plan hash does not match "
            "its immutable manifest."
        )

    plan = pd.read_csv(
        plan_file,
        dtype=str,
        keep_default_na=False,
    )

    if len(plan) != int(manifest["row_count"]):
        raise ValueError(
            "Discovery plan row count does not "
            "match its manifest."
        )

    plan["plan_index"] = pd.to_numeric(
        plan["plan_index"],
        errors="raise",
    ).astype(int)

    plan["chunk_id"] = pd.to_numeric(
        plan["chunk_id"],
        errors="raise",
    ).astype(int)

    expected_indices = list(range(len(plan)))

    if plan["plan_index"].tolist() != expected_indices:
        raise ValueError(
            "Discovery plan indices are not contiguous."
        )

    chunk_size = int(manifest["chunk_size"])

    expected_chunks = (
        plan["plan_index"] // chunk_size
    )

    if not expected_chunks.equals(
        plan["chunk_id"]
    ):
        raise ValueError(
            "Discovery plan chunk assignments "
            "do not match its manifest."
        )

    return plan, manifest
