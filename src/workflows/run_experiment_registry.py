from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.core.output_context import (
    resolve_agent_reports_dir,
    resolve_report_path,
    resolve_result_path,
    resolve_results_dir,
)

from src.agents.experiment_registry_agent import ExperimentRegistryAgent


def main() -> int:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S_experiment_registry")

    context = {
        "run_id": run_id,
        "reports_dir": str(resolve_agent_reports_dir()),
        "results_dir": str(resolve_results_dir()),
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
