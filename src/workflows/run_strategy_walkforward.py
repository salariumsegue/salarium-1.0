from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.strategy_walkforward_agent import StrategyWalkforwardAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_strategy_walkforward")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "results_dir": "results",
        "training_data_path": "data/processed/training_data_model_safe_with_macro.csv",
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
