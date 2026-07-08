from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.backtest_reviewer_agent import BacktestReviewerAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_backtest_review")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "walkforward_summary_path": "results/walkforward_rank_backtest_summary.csv",
        "macro_comparison_path": "results/macro_model_comparison.csv",
        "feature_importance_path": "results/macro_feature_importance.csv",
    }

    agent = BacktestReviewerAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
