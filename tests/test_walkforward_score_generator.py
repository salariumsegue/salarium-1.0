from pathlib import Path


SOURCE = Path(
    "scripts/generate_walkforward_scores.py"
).read_text(encoding="utf-8")


def test_generator_uses_governed_features() -> None:
    assert "CORE_TECHNICAL_FEATURES" in SOURCE
    assert '"return_5d"' not in SOURCE


def test_generator_uses_hardened_model() -> None:
    assert "max_depth=6" in SOURCE
    assert "min_samples_leaf=100" in SOURCE
    assert "max_features=0.70" in SOURCE


def test_generator_scores_full_test_year_once() -> None:
    assert 'scored["score"] = model.predict(' in SOURCE
    assert "for rebalance_date" not in SOURCE


def test_generator_saves_shared_artifact() -> None:
    assert "walkforward_oos_scores.csv" in SOURCE


def test_generator_supports_fast_single_year_check() -> None:
    assert '"--test-year"' in SOURCE
