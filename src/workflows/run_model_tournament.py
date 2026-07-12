from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.model_tournament_agent import ModelTournamentAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_model_tournament")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "results_dir": "results",
        "walkforward_summary_path": "results/walkforward_rank_backtest_summary.csv",
        "macro_comparison_path": "results/macro_model_comparison.csv",
        "manual_inputs_path": "results/model_tournament_inputs.csv",
    }

    agent = ModelTournamentAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
