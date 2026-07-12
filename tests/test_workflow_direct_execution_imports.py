import runpy


WORKFLOW_PATHS = [
    "src/workflows/run_strategy_walkforward.py",
    "src/workflows/run_data_quality_leakage.py",
    "src/workflows/run_macro_feature_audit.py",
]


def test_workflows_resolve_src_imports_when_loaded_directly() -> None:
    for path in WORKFLOW_PATHS:
        namespace = runpy.run_path(
            path,
            run_name="salarium_import_check",
        )

        assert namespace
