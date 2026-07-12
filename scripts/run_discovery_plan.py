from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.data_sources.yahoo_discovery import (
    DiscoveryResult,
    YahooDiscoveryDownloader,
)
from src.universe.discovery_plan import (
    verify_discovery_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an immutable U.S. equity discovery "
            "plan in resumable chunks."
        )
    )

    parser.add_argument(
        "--plan",
        required=True,
    )

    parser.add_argument(
        "--manifest",
        required=True,
    )

    parser.add_argument(
        "--start",
        required=True,
    )

    parser.add_argument(
        "--end",
        required=True,
    )

    parser.add_argument(
        "--output-directory",
        default="data/discovery/chunks",
    )

    parser.add_argument(
        "--cache-directory",
        default="data/cache/yahoo_discovery",
    )

    parser.add_argument(
        "--from-chunk",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--to-chunk",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    return parser.parse_args()


def atomic_write_csv(
    frame: pd.DataFrame,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    frame.to_csv(
        temporary_path,
        index=False,
    )

    temporary_path.replace(path)


def atomic_write_json(
    payload: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(path)


def load_report_records(
    path: Path,
) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}

    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
    )

    return {
        str(row["ticker"]): row.to_dict()
        for _, row in frame.iterrows()
    }


def make_record(
    plan_id: str,
    plan_row: Any,
    result: DiscoveryResult,
) -> dict[str, Any]:
    return {
        "plan_id": plan_id,
        "plan_index": int(
            plan_row.plan_index
        ),
        "chunk_id": int(
            plan_row.chunk_id
        ),
        "ticker": result.ticker,
        "yahoo_symbol": result.yahoo_symbol,
        "status": result.status,
        "rows": result.rows,
        "first_date": result.first_date or "",
        "last_date": result.last_date or "",
        "error": result.error or "",
        "cache_path": result.cache_path or "",
    }


def write_records(
    records: dict[str, dict[str, Any]],
    report_path: Path,
) -> None:
    frame = pd.DataFrame(
        records.values()
    )

    if frame.empty:
        return

    frame["plan_index"] = pd.to_numeric(
        frame["plan_index"],
        errors="raise",
    ).astype(int)

    frame["chunk_id"] = pd.to_numeric(
        frame["chunk_id"],
        errors="raise",
    ).astype(int)

    frame = frame.sort_values(
        "plan_index"
    ).reset_index(drop=True)

    atomic_write_csv(
        frame,
        report_path,
    )


def build_progress(
    output_directory: Path,
    *,
    plan_id: str,
    plan_rows: int,
    plan_sha256: str,
) -> dict[str, Any]:
    paths = sorted(
        output_directory.glob(
            "history_*.csv"
        )
    )

    frames = [
        pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
        )
        for path in paths
    ]

    if frames:
        report = pd.concat(
            frames,
            ignore_index=True,
        )

        report = report.drop_duplicates(
            subset=["ticker"],
            keep="last",
        )
    else:
        report = pd.DataFrame(
            columns=["ticker", "status"]
        )

    status_counts = (
        report["status"]
        .value_counts(dropna=False)
        .to_dict()
        if not report.empty
        else {}
    )

    completed = len(report)

    return {
        "plan_id": plan_id,
        "plan_sha256": plan_sha256,
        "updated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "plan_rows": plan_rows,
        "completed_rows": completed,
        "completion_rate": (
            completed / plan_rows
            if plan_rows
            else 0.0
        ),
        "status_counts": status_counts,
        "report_files": len(paths),
    }


def main() -> int:
    args = parse_args()

    plan, manifest = verify_discovery_plan(
        args.plan,
        args.manifest,
    )

    plan_id = str(manifest["plan_id"])
    plan_rows = int(manifest["row_count"])
    plan_sha256 = str(
        manifest["plan_sha256"]
    )

    output_directory = Path(
        args.output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        manifest,
        output_directory
        / "plan_manifest.json",
    )

    downloader = YahooDiscoveryDownloader(
        cache_directory=args.cache_directory,
        retries=3,
        retry_delay_seconds=1.0,
    )

    available_chunks = sorted(
        int(value)
        for value in plan["chunk_id"].unique()
    )

    selected_chunks = [
        chunk_id
        for chunk_id in available_chunks
        if chunk_id >= args.from_chunk
        and (
            args.to_chunk is None
            or chunk_id <= args.to_chunk
        )
    ]

    print("Plan ID:", plan_id)
    print("Plan rows:", plan_rows)
    print("Selected chunks:", selected_chunks)
    print("Output:", output_directory)
    print()

    for chunk_id in selected_chunks:
        chunk = plan[
            plan["chunk_id"].eq(
                chunk_id
            )
        ].copy()

        first_index = int(
            chunk["plan_index"].min()
        )

        report_path = (
            output_directory
            / f"history_{first_index:05d}.csv"
        )

        records = load_report_records(
            report_path
        )

        print(
            f"=== Chunk {chunk_id} "
            f"({len(chunk)} rows) ==="
        )

        for position, plan_row in enumerate(
            chunk.itertuples(index=False),
            start=1,
        ):
            ticker = str(plan_row.ticker)
            yahoo_symbol = str(
                plan_row.yahoo_symbol
            )

            previous = records.get(ticker)
            previous_status = (
                str(
                    previous.get(
                        "status",
                        "",
                    )
                )
                if previous
                else ""
            )

            if (
                previous_status
                in {"success", "empty"}
                and not args.force
            ):
                continue

            if (
                previous_status == "failed"
                and not args.retry_failed
                and not args.force
            ):
                continue

            result = downloader.discover(
                ticker=ticker,
                yahoo_symbol=yahoo_symbol,
                start_date=args.start,
                end_date=args.end,
                force=args.force,
            )

            if (
                result.status == "failed"
                and args.retry_failed
                and not args.force
            ):
                result = downloader.discover(
                    ticker=ticker,
                    yahoo_symbol=yahoo_symbol,
                    start_date=args.start,
                    end_date=args.end,
                    force=True,
                )

            records[ticker] = make_record(
                plan_id,
                plan_row,
                result,
            )

            write_records(
                records,
                report_path,
            )

            progress = build_progress(
                output_directory,
                plan_id=plan_id,
                plan_rows=plan_rows,
                plan_sha256=plan_sha256,
            )

            atomic_write_json(
                progress,
                output_directory
                / "progress.json",
            )

            print(
                f"[{position}/{len(chunk)}] "
                f"{ticker} ({yahoo_symbol}) "
                f"{result.status}: "
                f"{result.rows} rows"
            )

        print()

    final_progress = build_progress(
        output_directory,
        plan_id=plan_id,
        plan_rows=plan_rows,
        plan_sha256=plan_sha256,
    )

    atomic_write_json(
        final_progress,
        output_directory
        / "progress.json",
    )

    print("=== DISCOVERY PROGRESS ===")
    print(
        json.dumps(
            final_progress,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
