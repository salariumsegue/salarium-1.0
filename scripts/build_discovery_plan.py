from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.universe.discovery_plan import (
    write_discovery_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze the current active equity candidates "
            "into an immutable Yahoo discovery plan."
        )
    )

    parser.add_argument(
        "--candidates",
        default="configs/us_equity_candidates.csv",
    )

    parser.add_argument(
        "--output-directory",
        default="configs/discovery_plans",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=250,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    plan_path, manifest_path, manifest = (
        write_discovery_plan(
            candidates_path=args.candidates,
            output_directory=(
                args.output_directory
            ),
            chunk_size=args.chunk_size,
        )
    )

    print(
        "PLAN_PATH=" + str(plan_path)
    )
    print(
        "MANIFEST_PATH=" + str(
            manifest_path
        )
    )
    print(
        "PLAN_ID=" + str(
            manifest["plan_id"]
        )
    )
    print(
        "ROWS=" + str(
            manifest["row_count"]
        )
    )
    print(
        "CHUNKS=" + str(
            manifest["chunk_count"]
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
