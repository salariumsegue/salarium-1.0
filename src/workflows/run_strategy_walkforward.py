from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.core.dataset_context import resolve_training_data_path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.core.output_context import (
    resolve_agent_reports_dir,
    resolve_report_path,
    resolve_result_path,
    resolve_results_dir,
)

from src.agents.strategy_walkforward_agent import StrategyWalkforwardAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_strategy_walkforward")

    context = {
        "run_id": run_id,
        "reports_dir": str(resolve_agent_reports_dir()),
        "results_dir": str(resolve_results_dir()),
        "training_data_path": str(resolve_training_data_path()),
        "top_n": 10,
        "rebalance_step": 5,
        "transaction_cost_per_turnover": 0.001,
    }

    agent = StrategyWalkforwardAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
