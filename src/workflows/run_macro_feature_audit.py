from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.macro_feature_audit_agent import MacroFeatureAuditAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_macro_feature_audit")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "results_dir": "results",
        "macro_comparison_path": "results/macro_model_comparison.csv",
        "feature_importance_path": "results/macro_feature_importance.csv",
        "model_safe_training_path": "data/processed/training_data_model_safe.csv",
        "walkforward_summary_path": "results/walkforward_rank_backtest_summary.csv",
        "model_tournament_path": "results/model_tournament_leaderboard.csv",
    }

    agent = MacroFeatureAuditAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
