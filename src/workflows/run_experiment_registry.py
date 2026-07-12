from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.experiment_registry_agent import ExperimentRegistryAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_experiment_registry")

    context = {
        "run_id": run_id,
        "reports_dir": "reports/agent_runs",
        "results_dir": "results",
        "registry_dir": "data/runs",
    }

    agent = ExperimentRegistryAgent()
    result = agent.run(context)

    print(json.dumps(result.to_dict(), indent=2, default=str))

    if result.status == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
