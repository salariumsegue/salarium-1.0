import subprocess
import sys


def test_discovery_script_can_run_directly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/discover_us_equity_history.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "resumable Yahoo history" in completed.stdout
