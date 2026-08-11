from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.funnel.candidate_funnel import (
    FunnelSpec,
    run_candidate_funnel,
    score_stage,
    sha256_path,
)
from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
)


LOCAL_TECHNICAL_FEATURES = [
    feature
    for feature in CORE_TECHNICAL_FEATURES
    if feature != "relative_strength"
]


def load_liquid500_builder():
    path = (
        ROOT
        / "scripts"
        / "build_liquid500_training_data.py"
    )

    spec = importlib.util.spec_from_file_location(
        "salarium_liquid500_builder",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load liquid-500 builder."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    required = [
        "build_security_features",
        "add_cross_sectional_relative_strength",
        "load_cache_map",
    ]

    missing = [
        name
        for name in required
        if not hasattr(module, name)
    ]

    if missing:
        raise RuntimeError(
            "Liquid-500 builder is missing: "
            + ", ".join(missing)
        )

    return module


def maximum_drawdown_resilience(
    prices: pd.Series,
) -> float:
    clean = (
        pd.to_numeric(
            prices,
            errors="coerce",
        )
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    if len(clean) < 2:
        return float("nan")

    equity = (
        clean
        / float(clean.iloc[0])
    )

    drawdown = (
        equity
        / equity.cummax()
        - 1.0
    )

    maximum_drawdown = float(
        drawdown.min()
    )

    return float(
        np.clip(
            1.0 + maximum_drawdown,
            0.0,
            1.0,
        )
    )


def data_quality_score(
    feature_frame: pd.DataFrame,
    expected_history_days: int,
) -> float:
    recent = feature_frame.tail(252)

    coverage = float(
        recent[
            LOCAL_TECHNICAL_FEATURES
        ]
        .notna()
        .mean()
        .mean()
    )

    history_score = float(
        np.clip(
            len(feature_frame)
            / max(
                expected_history_days,
                1,
            ),
            0.0,
            1.0,
        )
    )

    return float(
        0.80 * coverage
        + 0.20 * history_score
    )


def load_discovery_candidates() -> pd.DataFrame:
    metrics = pd.read_csv(
        ROOT
        / "data"
        / "discovery"
        / "evaluation"
        / "metrics.csv",
        low_memory=False,
    )

    exclusions = pd.read_csv(
        ROOT
        / "data"
        / "discovery"
        / "evaluation"
        / "exclusions.csv",
        low_memory=False,
    )

    for frame in [
        metrics,
        exclusions,
    ]:
        frame["ticker"] = (
            frame["ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    merged = metrics.merge(
        exclusions[
            [
                "ticker",
                "eligible",
                "exclusion_reasons",
            ]
        ],
        on="ticker",
        how="left",
        validate="one_to_one",
    )

    eligible = merged[
        merged["eligible"]
        .fillna(False)
        .astype(bool)
    ].copy()

    eligible = eligible.sort_values(
        [
            "median_dollar_volume",
            "ticker",
        ],
        ascending=[
            False,
            True,
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    eligible["liquidity_rank"] = np.arange(
        1,
        len(eligible) + 1,
    )

    if len(eligible) < 2000:
        raise RuntimeError(
            "Fewer than 2,000 eligible "
            "discovery securities."
        )

    return eligible


def build_current_features(
    candidates: pd.DataFrame,
    cache_map: dict[str, Path],
    builder: Any,
    as_of_date: pd.Timestamp,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    feature_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    expected_history_days = int(
        candidates[
            "history_days"
        ].max()
    )

    for position, row in enumerate(
        candidates.itertuples(
            index=False
        ),
        start=1,
    ):
        ticker = str(row.ticker)
        cache_path = cache_map[ticker]

        try:
            history = pd.read_csv(
                cache_path,
                low_memory=False,
            )

            history["date"] = pd.to_datetime(
                history["date"],
                errors="coerce",
            )

            features = (
                builder.build_security_features(
                    history,
                    ticker=ticker,
                )
            )

        except ValueError as error:
            message = str(error)
            normalized_message = message.lower()

            recognized_data_errors = (
                "invalid ohlcv values",
                "invalid price or volume values",
                "missing required price",
                "no valid price rows",
                "price history is empty",
            )

            if not any(
                marker in normalized_message
                for marker in recognized_data_errors
            ):
                raise

            audit_rows.append(
                {
                    "ticker": ticker,
                    "status": (
                        "rejected_invalid_price_history"
                    ),
                    "cache_path": str(
                        cache_path
                    ),
                    "feature_date": "",
                    "error_type": type(
                        error
                    ).__name__,
                    "error": message,
                }
            )

            print(
                "Rejected invalid cache:",
                ticker,
                "|",
                message,
            )

            continue

        features["date"] = pd.to_datetime(
            features["date"],
            errors="coerce",
        )

        latest = features[
            features["date"]
            == as_of_date
        ].copy()

        if latest.empty:
            audit_rows.append(
                {
                    "ticker": ticker,
                    "status": (
                        "missing_as_of_feature_row"
                    ),
                    "cache_path": str(cache_path),
                    "feature_date": "",
                }
            )
            continue

        latest_row = (
            latest.sort_values("date")
            .iloc[-1]
            .to_dict()
        )

        price_column = (
            "adj_close"
            if "adj_close" in history.columns
            else "close"
        )

        resilience = (
            maximum_drawdown_resilience(
                history[
                    price_column
                ].tail(252)
            )
        )

        quality = data_quality_score(
            features,
            expected_history_days,
        )

        record = {
            "ticker": ticker,
            "date": as_of_date,
            **{
                feature: latest_row.get(
                    feature
                )
                for feature in (
                    LOCAL_TECHNICAL_FEATURES
                    + [
                        "return_5d",
                    ]
                )
            },
            "drawdown_resilience": (
                resilience
            ),
            "data_quality_score": quality,
        }

        feature_rows.append(record)

        audit_rows.append(
            {
                "ticker": ticker,
                "status": "pass",
                "cache_path": str(cache_path),
                "feature_date": str(
                    as_of_date.date()
                ),
                "data_quality_score": (
                    quality
                ),
                "drawdown_resilience": (
                    resilience
                ),
            }
        )

        if (
            position % 100 == 0
            or position == len(candidates)
        ):
            print(
                "Built current features:",
                position,
                "/",
                len(candidates),
            )

    feature_frame = pd.DataFrame(
        feature_rows
    )

    audit_frame = pd.DataFrame(
        audit_rows
    )

    status_counts = (
        audit_frame["status"]
        .value_counts()
        .sort_index()
        .to_dict()
        if not audit_frame.empty
        else {}
    )

    print()
    print(
        "Feature build status counts:",
        status_counts,
    )

    print(
        "Valid feature rows:",
        len(feature_frame),
    )

    return (
        feature_frame,
        audit_frame,
    )


def fit_hardened_model(
    training_path: Path,
    estimators: int,
) -> tuple[
    RandomForestRegressor,
    pd.Series,
    pd.Series,
]:
    columns = [
        *CORE_TECHNICAL_FEATURES,
        "target_5d_return",
    ]

    training = pd.read_csv(
        training_path,
        usecols=columns,
        low_memory=False,
    )

    for column in columns:
        training[column] = pd.to_numeric(
            training[column],
            errors="coerce",
        )

    training = training.dropna(
        subset=columns
    )

    feature_columns = list(
        CORE_TECHNICAL_FEATURES
    )

    lower_bounds = training[
        feature_columns
    ].quantile(0.005)

    upper_bounds = training[
        feature_columns
    ].quantile(0.995)

    x = training[
        feature_columns
    ].clip(
        lower=lower_bounds,
        upper=upper_bounds,
        axis="columns",
    )

    target = training[
        "target_5d_return"
    ].clip(
        lower=training[
            "target_5d_return"
        ].quantile(0.01),
        upper=training[
            "target_5d_return"
        ].quantile(0.99),
    )

    model = RandomForestRegressor(
        n_estimators=estimators,
        random_state=42,
        n_jobs=-1,
        max_depth=6,
        min_samples_leaf=100,
        max_features=0.70,
        bootstrap=True,
    )

    print(
        "Training hardened advanced model on",
        f"{len(training):,}",
        "rows...",
    )

    model.fit(
        x.to_numpy(
            dtype=float
        ),
        target.to_numpy(
            dtype=float
        ),
    )

    return (
        model,
        lower_bounds,
        upper_bounds,
    )


def add_advanced_evaluation(
    quantitative: pd.DataFrame,
    model: RandomForestRegressor,
    lower_bounds: pd.Series,
    upper_bounds: pd.Series,
) -> pd.DataFrame:
    result = quantitative.copy()

    feature_columns = list(
        CORE_TECHNICAL_FEATURES
    )

    x = result[
        feature_columns
    ].clip(
        lower=lower_bounds,
        upper=upper_bounds,
        axis="columns",
    ).to_numpy(
        dtype=float
    )

    tree_predictions = np.column_stack(
        [
            tree.predict(x)
            for tree in model.estimators_
        ]
    )

    result["model_score"] = (
        tree_predictions.mean(
            axis=1
        )
    )

    result["model_uncertainty"] = (
        tree_predictions.std(
            axis=1,
            ddof=0,
        )
    )

    result["liquidity_efficiency"] = (
        np.log1p(
            pd.to_numeric(
                result[
                    "median_dollar_volume"
                ],
                errors="coerce",
            )
        )
        / (
            1.0
            + 100.0
            * pd.to_numeric(
                result[
                    "volatility_20d"
                ],
                errors="coerce",
            ).clip(
                lower=0.005
            )
        )
    )

    return result


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default=(
            "configs/"
            "candidate_funnel.json"
        ),
    )

    parser.add_argument(
        "--training-data",
        default=(
            "data/processed/"
            "training_data_liquid500_"
            "model_safe_with_global_macro.csv"
        ),
    )

    parser.add_argument(
        "--discovery-reports",
        default=(
            "data/discovery/chunks"
        ),
    )

    parser.add_argument(
        "--input-output",
        default=(
            "data/processed/"
            "current_candidate_funnel_input.csv"
        ),
    )

    parser.add_argument(
        "--input-manifest",
        default=(
            "data/processed/"
            "current_candidate_funnel_"
            "input_manifest.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "results/"
            "candidate_funnel"
        ),
    )

    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    training_path = Path(
        args.training_data
    )
    input_path = Path(
        args.input_output
    )
    manifest_path = Path(
        args.input_manifest
    )

    spec = FunnelSpec.from_path(
        config_path
    )

    candidates = (
        load_discovery_candidates()
    )

    as_of_date = pd.to_datetime(
        candidates["last_date"],
        errors="coerce",
    ).max()

    current = candidates[
        pd.to_datetime(
            candidates["last_date"],
            errors="coerce",
        )
        == as_of_date
    ].copy()

    if len(current) < 2000:
        raise RuntimeError(
            "Fewer than 2,000 eligible "
            "securities share the latest date."
        )

    builder = load_liquid500_builder()

    cache_map, report_paths = (
        builder.load_cache_map(
            args.discovery_reports,
            set(current["ticker"]),
        )
    )

    current_features, audit = (
        build_current_features(
            current,
            cache_map,
            builder,
            as_of_date,
        )
    )

    base = current.merge(
        current_features,
        on="ticker",
        how="inner",
        validate="one_to_one",
    )

    if len(base) < 2000:
        rejection_counts = (
            audit["status"]
            .value_counts()
            .sort_index()
            .to_dict()
        )

        raise RuntimeError(
            "Feature construction left fewer "
            "than 2,000 current securities. "
            f"Valid rows: {len(base)}. "
            f"Audit counts: {rejection_counts}."
        )

    universe = score_stage(
        base,
        spec.stages["universe"],
    )

    universe = (
        builder
        .add_cross_sectional_relative_strength(
            universe
        )
    )

    quantitative = score_stage(
        universe,
        spec.stages[
            "quantitative"
        ],
    )

    model, lower, upper = (
        fit_hardened_model(
            training_path,
            args.estimators,
        )
    )

    advanced_input = (
        add_advanced_evaluation(
            quantitative,
            model,
            lower,
            upper,
        )
    )

    advanced_columns = [
        "ticker",
        "model_score",
        "model_uncertainty",
        "liquidity_efficiency",
    ]

    base = base.merge(
        universe[
            [
                "ticker",
                "relative_strength",
            ]
        ],
        on="ticker",
        how="left",
        validate="one_to_one",
    )

    base = base.merge(
        advanced_input[
            advanced_columns
        ],
        on="ticker",
        how="left",
        validate="one_to_one",
    )

    input_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = input_path.with_suffix(
        input_path.suffix + ".tmp"
    )

    base.to_csv(
        temporary,
        index=False,
    )

    temporary.replace(input_path)

    audit_path = input_path.with_name(
        "current_candidate_funnel_"
        "feature_audit.csv"
    )

    audit.to_csv(
        audit_path,
        index=False,
    )

    input_manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "as_of_date": str(
            as_of_date.date()
        ),
        "eligible_discovery_rows": len(
            candidates
        ),
        "same_date_eligible_rows": len(
            current
        ),
        "feature_rows": len(
            current_features
        ),
        "feature_status_counts": {
            str(status): int(count)
            for status, count
            in audit["status"]
            .value_counts()
            .sort_index()
            .items()
        },
        "rejected_feature_rows": int(
            (
                audit["status"]
                != "pass"
            ).sum()
        ),
        "funnel_input_rows": len(
            base
        ),
        "precomputed_universe_rows": len(
            universe
        ),
        "precomputed_quantitative_rows": len(
            quantitative
        ),
        "advanced_evaluated_rows": len(
            advanced_input
        ),
        "input_path": str(
            input_path
        ),
        "input_sha256": sha256_path(
            input_path
        ),
        "feature_audit_path": str(
            audit_path
        ),
        "feature_audit_sha256": (
            sha256_path(
                audit_path
            )
        ),
        "training_path": str(
            training_path
        ),
        "training_sha256": sha256_path(
            training_path
        ),
        "config_path": str(
            config_path
        ),
        "config_sha256": sha256_path(
            config_path
        ),
        "discovery_report_count": len(
            report_paths
        ),
        "advanced_model": {
            "type": (
                "RandomForestRegressor"
            ),
            "estimators": (
                args.estimators
            ),
            "max_depth": 6,
            "min_samples_leaf": 100,
            "max_features": 0.70,
            "training_universe": (
                "canonical_liquid_500"
            ),
            "scoring_universe": (
                "quantitative_top_200"
            ),
        },
    }

    write_json(
        manifest_path,
        input_manifest,
    )

    funnel_manifest_path = (
        run_candidate_funnel(
            input_path=input_path,
            config_path=config_path,
            output_root=Path(
                args.output_root
            ),
        )
    )

    funnel_manifest = json.loads(
        funnel_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    expected = {
        "universe": 2000,
        "quantitative": 200,
        "advanced": 50,
    }

    for stage, count in expected.items():
        actual = funnel_manifest[
            "stage_counts"
        ].get(stage)

        if actual != count:
            raise RuntimeError(
                f"{stage} count is "
                f"{actual}, expected {count}."
            )

    if (
        funnel_manifest["status"]
        != "awaiting_agent_research"
    ):
        raise RuntimeError(
            "Real funnel should stop at "
            "the agent research queue."
        )

    print()
    print(
        "CURRENT_CANDIDATE_FUNNEL_STATUS=PASS"
    )

    print(
        "As-of date:",
        as_of_date.date(),
    )

    print(
        "Funnel input:",
        len(base),
    )

    print(
        "Universe stage:",
        funnel_manifest[
            "stage_counts"
        ]["universe"],
    )

    print(
        "Quantitative stage:",
        funnel_manifest[
            "stage_counts"
        ]["quantitative"],
    )

    print(
        "Advanced stage:",
        funnel_manifest[
            "stage_counts"
        ]["advanced"],
    )

    print(
        "Agent queue:",
        funnel_manifest_path.parent
        / "agent_research_template.csv",
    )

    print(
        "Advanced candidates:",
        funnel_manifest_path.parent
        / "advanced_candidates.csv",
    )

    print(
        "Manifest:",
        funnel_manifest_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
