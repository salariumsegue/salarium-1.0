from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.risk_portfolio_agent import RiskPortfolioAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_risk_portfolio")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "results_dir": "results",
        "walkforward_summary_path": "results/walkforward_rank_backtest_summary.csv",
        "walkforward_detail_path": "results/walkforward_rank_backtest_results.csv",
        "model_tournament_path": "results/model_tournament_leaderboard.csv",
        "strategy_summary_path": "results/strategy_walkforward_tournament_summary.csv",
    }

    agent = RiskPortfolioAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
