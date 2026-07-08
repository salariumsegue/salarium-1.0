from __future__ import annotations

import subprocess
import sys
from pathlib import Path


COMMANDS = [
    ["python", "src/workflows/run_strategy_walkforward.py"],
    ["python", "src/workflows/run_model_tournament.py"],
    ["python", "src/workflows/run_data_quality_leakage.py"],
    ["python", "src/workflows/run_risk_portfolio.py"],
    ["python", "src/workflows/run_macro_feature_audit.py"],
    ["python", "src/workflows/run_backtest_reviewer.py"],
    ["python", "src/workflows/run_experiment_registry.py"],
    ["python", "src/workflows/run_final_research_report.py"],
]


def run_command(command: list[str]) -> None:
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)

    completed = subprocess.run(command)

    if completed.returncode != 0:
        raise SystemExit(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def main() -> int:
    root = Path.cwd()

    required = [
        Path("src/workflows/run_strategy_walkforward.py"),
        Path("src/workflows/run_model_tournament.py"),
        Path("src/workflows/run_data_quality_leakage.py"),
        Path("src/workflows/run_risk_portfolio.py"),
        Path("src/workflows/run_macro_feature_audit.py"),
        Path("src/workflows/run_backtest_reviewer.py"),
        Path("src/workflows/run_experiment_registry.py"),
        Path("src/workflows/run_final_research_report.py"),
    ]

    missing = [str(path) for path in required if not path.exists()]

    if missing:
        print("Missing required workflow files:")
        for path in missing:
            print("-", path)
        return 1

    print(f"Salarium research pipeline root: {root}")

    for command in COMMANDS:
        run_command(command)

    print("")
    print("Research pipeline complete.")
    print("Open dashboard with:")
    print("python -m streamlit run app/streamlit_app.py")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
