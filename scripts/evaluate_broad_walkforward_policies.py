from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd


def load_evaluator():
    path = Path(
        "scripts/"
        "evaluate_walkforward_policies.py"
    )

    spec = importlib.util.spec_from_file_location(
        "policy_evaluator",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load policy evaluator."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--score-path",
        default=(
            "results/broad_walkforward/"
            "walkforward_oos_scores.csv"
        ),
    )

    parser.add_argument(
        "--output-directory",
        default=(
            "results/"
            "broad_walkforward"
        ),
    )

    args = parser.parse_args()

    evaluator = load_evaluator()

    scored = pd.read_csv(
        args.score_path
    )

    scored["date"] = pd.to_datetime(
        scored["date"],
        errors="raise",
    )

    all_results = []
    summaries = []

    for policy in (
        evaluator
        .approved_research_policies()
    ):
        print(
            "Evaluating broad policy:",
            policy,
        )

        result = (
            evaluator.evaluate_policy(
                scored,
                policy,
            )
        )

        all_results.append(
            result
        )

        summaries.append(
            evaluator.summarize(
                result,
                policy,
                "overall",
            )
        )

        for year, yearly in (
            result.groupby(
                "test_year"
            )
        ):
            summaries.append(
                evaluator.summarize(
                    yearly,
                    policy,
                    str(year),
                )
            )

    results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = pd.DataFrame(
        summaries
    )

    output_directory = Path(
        args.output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        output_directory
        / "approved_policy_results.csv",
        index=False,
    )

    summary.to_csv(
        output_directory
        / "approved_policy_summary.csv",
        index=False,
    )

    print()
    print(
        "BROAD_POLICY_EVALUATION_STATUS=PASS"
    )

    print()
    print(
        summary[
            summary["period"]
            == "overall"
        ].to_string(
            index=False
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
