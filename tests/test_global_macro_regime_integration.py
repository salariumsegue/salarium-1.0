from pathlib import Path


def test_global_macro_builder_adds_regime_annotations() -> None:
    source = Path(
        "scripts/build_global_macro_model_safe_training_data.py"
    ).read_text(encoding="utf-8")

    assert "add_regime_annotations" in source
    assert '"market_regime"' in source
    assert "regime_is_confident" in source
    assert "confidence_threshold=0.80" in source
