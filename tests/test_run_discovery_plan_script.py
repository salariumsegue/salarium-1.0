import subprocess
import sys


def test_discovery_plan_runner_can_run_directly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_discovery_plan.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert (
        "immutable U.S. equity discovery"
        in completed.stdout
    )
