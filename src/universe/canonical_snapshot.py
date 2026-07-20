from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CanonicalUniverseSnapshot:
    snapshot_path: Path
    manifest_path: Path
    manifest: dict[str, Any]
    frame: pd.DataFrame

    @property
    def universe_id(self) -> str:
        return str(self.manifest["universe_id"])

    @property
    def market_date(self) -> str:
        return str(self.manifest["market_date"])


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


def resolve_snapshot_path(
    manifest_path: str | Path,
    manifest: dict[str, Any],
) -> Path:
    manifest_file = Path(manifest_path)
    declared = Path(str(manifest["snapshot_path"]))

    candidates = [
        declared,
        Path.cwd() / declared,
        manifest_file.parent / declared.name,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not resolve canonical universe snapshot: "
        + str(declared)
    )


def load_canonical_snapshot(
    manifest_path: str | Path,
) -> CanonicalUniverseSnapshot:
    manifest_file = Path(manifest_path).resolve()

    if not manifest_file.is_file():
        raise FileNotFoundError(
            f"Universe manifest does not exist: {manifest_file}"
        )

    manifest = json.loads(
        manifest_file.read_text(encoding="utf-8")
    )

    required_manifest_fields = {
        "universe_id",
        "snapshot_type",
        "market_date",
        "snapshot_path",
        "snapshot_sha256",
    }

    missing_manifest_fields = sorted(
        required_manifest_fields - set(manifest)
    )

    if missing_manifest_fields:
        raise KeyError(
            "Universe manifest is missing fields: "
            + ", ".join(missing_manifest_fields)
        )

    if manifest["snapshot_type"] != "current_liquid_universe":
        raise ValueError(
            "Manifest is not a current liquid-universe snapshot."
        )

    snapshot_path = resolve_snapshot_path(
        manifest_file,
        manifest,
    )

    actual_hash = sha256_file(snapshot_path)
    expected_hash = str(manifest["snapshot_sha256"])

    if actual_hash != expected_hash:
        raise ValueError(
            "Canonical universe snapshot hash does not "
            "match its manifest."
        )

    frame = pd.read_csv(
        snapshot_path,
        dtype={"ticker": str},
        keep_default_na=False,
    )

    required_columns = {
        "universe_id",
        "snapshot_type",
        "snapshot_date",
        "universe_rank",
        "ticker",
        "security_type",
        "exchange",
        "last_price",
        "median_dollar_volume",
        "history_days",
        "last_date",
    }

    missing_columns = sorted(
        required_columns - set(frame.columns)
    )

    if missing_columns:
        raise KeyError(
            "Canonical universe snapshot is missing columns: "
            + ", ".join(missing_columns)
        )

    expected_size = int(
        manifest.get("selection_rules", {}).get(
            "maximum_size",
            manifest.get("validation", {}).get(
                "selected_rows",
                500,
            ),
        )
    )

    if len(frame) != expected_size:
        raise ValueError(
            f"Expected {expected_size} universe rows; "
            f"found {len(frame)}."
        )

    if frame["ticker"].eq("").any():
        raise ValueError(
            "Canonical universe contains an empty ticker."
        )

    if frame["ticker"].duplicated().any():
        raise ValueError(
            "Canonical universe contains duplicate tickers."
        )

    ranks = pd.to_numeric(
        frame["universe_rank"],
        errors="raise",
    ).astype(int)

    if ranks.tolist() != list(range(1, expected_size + 1)):
        raise ValueError(
            "Canonical universe ranks are not contiguous."
        )

    if set(frame["universe_id"]) != {
        str(manifest["universe_id"])
    }:
        raise ValueError(
            "Snapshot universe ID does not match its manifest."
        )

    if set(frame["snapshot_date"]) != {
        str(manifest["market_date"])
    }:
        raise ValueError(
            "Snapshot date does not match its manifest."
        )

    return CanonicalUniverseSnapshot(
        snapshot_path=snapshot_path,
        manifest_path=manifest_file,
        manifest=manifest,
        frame=frame,
    )


def find_latest_canonical_snapshot(
    snapshot_directory: str | Path,
) -> CanonicalUniverseSnapshot | None:
    directory = Path(snapshot_directory)

    if not directory.exists():
        return None

    manifest_paths = sorted(
        directory.glob("*_liquid_500_manifest.json")
    )

    if not manifest_paths:
        return None

    dated_manifests: list[tuple[pd.Timestamp, Path]] = []

    for manifest_path in manifest_paths:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        market_date = pd.Timestamp(
            manifest["market_date"]
        )

        dated_manifests.append(
            (market_date, manifest_path)
        )

    _, latest_manifest = max(
        dated_manifests,
        key=lambda item: (item[0], item[1].name),
    )

    return load_canonical_snapshot(latest_manifest)


def assess_dataset_universe_coverage(
    dataset_path: str | Path,
    canonical_universe: pd.DataFrame,
) -> dict[str, Any]:
    path = Path(dataset_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset does not exist: {path}"
        )

    header = pd.read_csv(path, nrows=0)

    if "ticker" not in header.columns:
        return {
            "status": "unavailable",
            "reason": "dataset_has_no_ticker_column",
            "dataset_path": str(path),
        }

    dataset_tickers = {
        str(ticker).strip().upper()
        for ticker in pd.read_csv(
            path,
            usecols=["ticker"],
            dtype={"ticker": str},
            keep_default_na=False,
        )["ticker"]
        if str(ticker).strip()
    }

    canonical_tickers = {
        str(ticker).strip().upper()
        for ticker in canonical_universe["ticker"]
        if str(ticker).strip()
    }

    overlap = dataset_tickers & canonical_tickers
    missing = canonical_tickers - dataset_tickers
    extra = dataset_tickers - canonical_tickers

    if dataset_tickers == canonical_tickers:
        status = "full"
    elif dataset_tickers and dataset_tickers.issubset(
        canonical_tickers
    ):
        status = "partial"
    else:
        status = "incompatible"

    return {
        "status": status,
        "dataset_path": str(path),
        "dataset_ticker_count": len(dataset_tickers),
        "canonical_ticker_count": len(canonical_tickers),
        "overlap_ticker_count": len(overlap),
        "coverage_rate": (
            len(overlap) / len(canonical_tickers)
            if canonical_tickers
            else 0.0
        ),
        "missing_ticker_count": len(missing),
        "extra_ticker_count": len(extra),
        "missing_tickers": sorted(missing),
        "extra_tickers": sorted(extra),
    }
