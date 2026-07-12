import subprocess
import sys


def test_liquid_universe_builder_can_run_directly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_liquid_universe.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "liquid U.S. equity universe" in completed.stdout
