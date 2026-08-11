from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


STAGE_ORDER = (
    "universe",
    "quantitative",
    "advanced",
    "agentic",
)


@dataclass(frozen=True)
class FeatureSpec:
    column: str
    weight: float
    direction: str = "higher"
    required: bool = True

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "FeatureSpec":
        feature = cls(
            column=str(payload["column"]),
            weight=float(payload["weight"]),
            direction=str(
                payload.get(
                    "direction",
                    "higher",
                )
            ),
            required=bool(
                payload.get(
                    "required",
                    True,
                )
            ),
        )

        if feature.weight <= 0:
            raise ValueError(
                "Feature weights must be positive."
            )

        if feature.direction not in {
            "higher",
            "lower",
        }:
            raise ValueError(
                "Feature direction must be "
                "'higher' or 'lower'."
            )

        return feature


@dataclass(frozen=True)
class FilterSpec:
    column: str
    operator: str
    value: Any
    required: bool = True

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "FilterSpec":
        return cls(
            column=str(payload["column"]),
            operator=str(payload["operator"]),
            value=payload.get("value"),
            required=bool(
                payload.get(
                    "required",
                    True,
                )
            ),
        )


@dataclass(frozen=True)
class SortSpec:
    column: str
    ascending: bool

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "SortSpec":
        return cls(
            column=str(payload["column"]),
            ascending=bool(
                payload.get(
                    "ascending",
                    False,
                )
            ),
        )


@dataclass(frozen=True)
class StageSpec:
    name: str
    target_count: int
    score_column: str
    minimum_feature_coverage: float
    features: tuple[FeatureSpec, ...]
    filters: tuple[FilterSpec, ...]
    tie_breakers: tuple[SortSpec, ...]

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "StageSpec":
        stage = cls(
            name=str(payload["name"]),
            target_count=int(
                payload["target_count"]
            ),
            score_column=str(
                payload.get(
                    "score_column",
                    f"{payload['name']}_score",
                )
            ),
            minimum_feature_coverage=float(
                payload.get(
                    "minimum_feature_coverage",
                    1.0,
                )
            ),
            features=tuple(
                FeatureSpec.from_dict(item)
                for item in payload["features"]
            ),
            filters=tuple(
                FilterSpec.from_dict(item)
                for item in payload.get(
                    "filters",
                    [],
                )
            ),
            tie_breakers=tuple(
                SortSpec.from_dict(item)
                for item in payload.get(
                    "tie_breakers",
                    [],
                )
            ),
        )

        if stage.target_count <= 0:
            raise ValueError(
                "Stage target_count must be positive."
            )

        if not 0 <= stage.minimum_feature_coverage <= 1:
            raise ValueError(
                "minimum_feature_coverage must "
                "be between zero and one."
            )

        if not stage.features:
            raise ValueError(
                "Every stage requires at least "
                "one scoring feature."
            )

        return stage


@dataclass(frozen=True)
class FunnelSpec:
    stages: dict[str, StageSpec]
    final_target: int
    final_minimum: int
    final_maximum: int
    diversification_group_column: str | None
    maximum_per_group: int | None

    @classmethod
    def from_path(
        cls,
        path: Path,
    ) -> "FunnelSpec":
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        stages = {
            item["name"]: StageSpec.from_dict(
                item
            )
            for item in payload["stages"]
        }

        missing = set(STAGE_ORDER) - set(stages)

        if missing:
            raise ValueError(
                "Missing funnel stages: "
                + ", ".join(sorted(missing))
            )

        final = payload["final_selection"]

        spec = cls(
            stages=stages,
            final_target=int(
                final["target_count"]
            ),
            final_minimum=int(
                final["minimum_count"]
            ),
            final_maximum=int(
                final["maximum_count"]
            ),
            diversification_group_column=(
                final.get("group_column")
            ),
            maximum_per_group=(
                int(final["maximum_per_group"])
                if final.get(
                    "maximum_per_group"
                )
                is not None
                else None
            ),
        )

        if not (
            10
            <= spec.final_minimum
            <= spec.final_target
            <= spec.final_maximum
            <= 30
        ):
            raise ValueError(
                "Final funnel bounds must satisfy "
                "10 <= minimum <= target <= "
                "maximum <= 30."
            )

        return spec


def robust_zscore(
    series: pd.Series,
    clip: float = 4.0,
) -> pd.Series:
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid = values.dropna()

    result = pd.Series(
        np.nan,
        index=series.index,
        dtype=float,
    )

    if valid.empty:
        return result

    median = float(valid.median())
    mad = float(
        (valid - median).abs().median()
    )

    if mad > 1e-12:
        scored = (
            0.6744897501960817
            * (values - median)
            / mad
        )
    else:
        deviation = float(
            valid.std(ddof=1)
        )

        if deviation > 1e-12:
            scored = (
                values - float(valid.mean())
            ) / deviation
        else:
            scored = pd.Series(
                0.0,
                index=series.index,
            ).where(
                values.notna()
            )

    return scored.clip(
        lower=-clip,
        upper=clip,
    )


def _filter_mask(
    series: pd.Series,
    operator: str,
    value: Any,
) -> pd.Series:
    if operator in {
        ">",
        ">=",
        "<",
        "<=",
    }:
        numeric = pd.to_numeric(
            series,
            errors="coerce",
        )

        target = float(value)

        if operator == ">":
            return numeric > target
        if operator == ">=":
            return numeric >= target
        if operator == "<":
            return numeric < target
        return numeric <= target

    if operator == "==":
        return series == value

    if operator == "!=":
        return series != value

    if operator == "in":
        return series.isin(value)

    if operator == "not_in":
        return ~series.isin(value)

    if operator == "is_true":
        return (
            series.astype(str)
            .str.lower()
            .isin(
                {
                    "true",
                    "1",
                    "yes",
                }
            )
        )

    if operator == "is_false":
        return ~(
            series.astype(str)
            .str.lower()
            .isin(
                {
                    "true",
                    "1",
                    "yes",
                }
            )
        )

    raise ValueError(
        f"Unsupported filter operator: {operator}"
    )


def apply_filters(
    frame: pd.DataFrame,
    filters: Iterable[FilterSpec],
) -> pd.DataFrame:
    result = frame.copy()
    mask = pd.Series(
        True,
        index=result.index,
    )

    for filter_spec in filters:
        if filter_spec.column not in result.columns:
            if filter_spec.required:
                raise KeyError(
                    "Missing required filter column: "
                    f"{filter_spec.column}"
                )

            continue

        mask &= _filter_mask(
            result[filter_spec.column],
            filter_spec.operator,
            filter_spec.value,
        ).fillna(False)

    return result.loc[mask].copy()


def score_stage(
    frame: pd.DataFrame,
    stage: StageSpec,
) -> pd.DataFrame:
    filtered = apply_filters(
        frame,
        stage.filters,
    )

    weighted_score = pd.Series(
        0.0,
        index=filtered.index,
    )

    available_weight = pd.Series(
        0.0,
        index=filtered.index,
    )

    total_weight = sum(
        feature.weight
        for feature in stage.features
    )

    for feature in stage.features:
        if feature.column not in filtered.columns:
            if feature.required:
                raise KeyError(
                    "Missing required feature column "
                    f"for {stage.name}: "
                    f"{feature.column}"
                )

            continue

        zscore = robust_zscore(
            filtered[feature.column]
        )

        if feature.direction == "lower":
            zscore = -zscore

        valid = zscore.notna()

        weighted_score.loc[valid] += (
            zscore.loc[valid]
            * feature.weight
        )

        available_weight.loc[valid] += (
            feature.weight
        )

    coverage_column = (
        f"{stage.name}_feature_coverage"
    )

    filtered[coverage_column] = (
        available_weight / total_weight
    )

    filtered[stage.score_column] = (
        weighted_score
        / available_weight.replace(
            0.0,
            np.nan,
        )
    )

    filtered = filtered[
        filtered[coverage_column]
        >= stage.minimum_feature_coverage
    ].copy()

    sort_columns = [
        stage.score_column,
    ]

    ascending = [
        False,
    ]

    for tie_breaker in stage.tie_breakers:
        if (
            tie_breaker.column
            not in filtered.columns
        ):
            raise KeyError(
                "Missing tie-breaker column: "
                f"{tie_breaker.column}"
            )

        if (
            tie_breaker.column
            not in sort_columns
        ):
            sort_columns.append(
                tie_breaker.column
            )
            ascending.append(
                tie_breaker.ascending
            )

    if "ticker" not in sort_columns:
        sort_columns.append("ticker")
        ascending.append(True)

    filtered = (
        filtered.sort_values(
            sort_columns,
            ascending=ascending,
            kind="mergesort",
        )
        .head(
            stage.target_count
        )
        .reset_index(drop=True)
    )

    filtered[
        f"{stage.name}_rank"
    ] = np.arange(
        1,
        len(filtered) + 1,
    )

    return filtered


def validate_unique_tickers(
    frame: pd.DataFrame,
    label: str,
) -> None:
    if "ticker" not in frame.columns:
        raise KeyError(
            f"{label} has no ticker column."
        )

    if frame["ticker"].isna().any():
        raise ValueError(
            f"{label} contains missing tickers."
        )

    duplicates = int(
        frame["ticker"].duplicated().sum()
    )

    if duplicates:
        raise ValueError(
            f"{label} contains {duplicates} "
            "duplicate tickers."
        )


def merge_agent_research(
    advanced: pd.DataFrame,
    agent_input: pd.DataFrame,
) -> pd.DataFrame:
    validate_unique_tickers(
        agent_input,
        "Agent research input",
    )

    collisions = (
        set(advanced.columns)
        & set(agent_input.columns)
        - {"ticker"}
    )

    if collisions:
        raise ValueError(
            "Agent research columns collide with "
            "existing funnel columns: "
            + ", ".join(sorted(collisions))
        )

    return advanced.merge(
        agent_input,
        on="ticker",
        how="left",
        validate="one_to_one",
    )


def select_final_candidates(
    agentic: pd.DataFrame,
    spec: FunnelSpec,
) -> pd.DataFrame:
    if len(agentic) < spec.final_minimum:
        raise RuntimeError(
            "Agentic stage produced fewer than "
            f"{spec.final_minimum} eligible names."
        )

    group_column = (
        spec.diversification_group_column
    )

    cap = spec.maximum_per_group

    if (
        group_column is None
        or cap is None
    ):
        selected = agentic.head(
            spec.final_target
        ).copy()
    else:
        if group_column not in agentic.columns:
            raise KeyError(
                "Configured diversification column "
                f"is missing: {group_column}"
            )

        selected_indices: list[int] = []
        group_counts: dict[str, int] = {}

        for index, row in agentic.iterrows():
            group = str(
                row[group_column]
            )

            count = group_counts.get(
                group,
                0,
            )

            if count >= cap:
                continue

            selected_indices.append(index)
            group_counts[group] = count + 1

            if (
                len(selected_indices)
                == spec.final_target
            ):
                break

        selected = agentic.loc[
            selected_indices
        ].copy()

    if len(selected) < spec.final_minimum:
        raise RuntimeError(
            "Diversification rules leave fewer "
            "than the required minimum candidates."
        )

    selected = selected.head(
        spec.final_maximum
    ).reset_index(drop=True)

    selected[
        "portfolio_candidate_rank"
    ] = np.arange(
        1,
        len(selected) + 1,
    )

    return selected


def sha256_path(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def atomic_write_csv(
    frame: pd.DataFrame,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    frame.to_csv(
        temporary,
        index=False,
    )

    temporary.replace(path)


def git_metadata() -> dict[str, Any]:
    def command(
        *args: str,
    ) -> str:
        completed = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )

        return completed.stdout.strip()

    status = command(
        "status",
        "--porcelain",
    )

    return {
        "branch": command(
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ),
        "commit": command(
            "rev-parse",
            "HEAD",
        ),
        "dirty": bool(status),
    }


def run_candidate_funnel(
    *,
    input_path: Path,
    config_path: Path,
    output_root: Path,
    agent_input_path: Path | None = None,
) -> Path:
    spec = FunnelSpec.from_path(
        config_path
    )

    source = pd.read_csv(
        input_path
    )

    source["ticker"] = (
        source["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    validate_unique_tickers(
        source,
        "Funnel input",
    )

    run_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    run_directory = (
        output_root
        / run_id
    )

    run_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    artifacts: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    current = source

    for stage_name in (
        "universe",
        "quantitative",
        "advanced",
    ):
        stage = spec.stages[
            stage_name
        ]

        current = score_stage(
            current,
            stage,
        )

        path = (
            run_directory
            / f"{stage_name}_candidates.csv"
        )

        atomic_write_csv(
            current,
            path,
        )

        counts[stage_name] = len(
            current
        )

        artifacts.append(
            {
                "name": stage_name,
                "path": path.name,
                "rows": len(current),
                "sha256": sha256_path(path),
            }
        )

    agent_features = [
        feature.column
        for feature in spec.stages[
            "agentic"
        ].features
        if feature.column
        not in current.columns
    ]

    template = current[
        [
            "ticker",
            "advanced_rank",
            "advanced_score",
        ]
    ].copy()

    for column in agent_features:
        template[column] = np.nan

    template_path = (
        run_directory
        / "agent_research_template.csv"
    )

    atomic_write_csv(
        template,
        template_path,
    )

    artifacts.append(
        {
            "name": "agent_research_template",
            "path": template_path.name,
            "rows": len(template),
            "sha256": sha256_path(
                template_path
            ),
        }
    )

    final_path: Path | None = None

    if agent_input_path is None:
        status = (
            "awaiting_agent_research"
        )
    else:
        agent_input = pd.read_csv(
            agent_input_path
        )

        agent_input["ticker"] = (
            agent_input["ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        merged = merge_agent_research(
            current,
            agent_input,
        )

        agentic = score_stage(
            merged,
            spec.stages["agentic"],
        )

        agentic_path = (
            run_directory
            / "agentic_candidates.csv"
        )

        atomic_write_csv(
            agentic,
            agentic_path,
        )

        counts["agentic"] = len(
            agentic
        )

        artifacts.append(
            {
                "name": "agentic",
                "path": agentic_path.name,
                "rows": len(agentic),
                "sha256": sha256_path(
                    agentic_path
                ),
            }
        )

        final = select_final_candidates(
            agentic,
            spec,
        )

        final_path = (
            run_directory
            / "portfolio_candidates.csv"
        )

        atomic_write_csv(
            final,
            final_path,
        )

        counts["portfolio_candidates"] = (
            len(final)
        )

        artifacts.append(
            {
                "name": "portfolio_candidates",
                "path": final_path.name,
                "rows": len(final),
                "sha256": sha256_path(
                    final_path
                ),
            }
        )

        status = "complete"

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": status,
        "architecture": {
            "broad_universe_target": 2000,
            "quantitative_target": 200,
            "advanced_target": 50,
            "agentic_target": (
                spec.stages[
                    "agentic"
                ].target_count
            ),
            "portfolio_candidate_bounds": [
                spec.final_minimum,
                spec.final_maximum,
            ],
        },
        "input": {
            "path": str(input_path),
            "sha256": sha256_path(
                input_path
            ),
            "rows": len(source),
        },
        "config": {
            "path": str(config_path),
            "sha256": sha256_path(
                config_path
            ),
        },
        "agent_input": (
            {
                "path": str(
                    agent_input_path
                ),
                "sha256": sha256_path(
                    agent_input_path
                ),
            }
            if agent_input_path
            is not None
            else None
        ),
        "required_agent_columns": (
            agent_features
        ),
        "stage_counts": counts,
        "artifacts": artifacts,
        "git": git_metadata(),
        "final_artifact": (
            final_path.name
            if final_path
            is not None
            else None
        ),
    }

    manifest_path = (
        run_directory
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    latest_path = (
        output_root
        / "latest_manifest.json"
    )

    latest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest_path
