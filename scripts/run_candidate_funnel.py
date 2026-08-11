from __future__ import annotations

import argparse
from pathlib import Path

from src.funnel.candidate_funnel import (
    run_candidate_funnel,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Salarium multi-stage "
            "candidate research funnel."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--agent-input",
        default=None,
    )

    parser.add_argument(
        "--config",
        default=(
            "configs/"
            "candidate_funnel.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "results/"
            "candidate_funnel"
        ),
    )

    args = parser.parse_args()

    manifest = run_candidate_funnel(
        input_path=Path(args.input),
        agent_input_path=(
            Path(args.agent_input)
            if args.agent_input
            else None
        ),
        config_path=Path(args.config),
        output_root=Path(
            args.output_root
        ),
    )

    print(
        "CANDIDATE_FUNNEL_STATUS=PASS"
    )

    print(
        "Manifest:",
        manifest,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
