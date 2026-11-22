"""Hyper-parameter search on the validation split and refit before testing."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable

from pyspark.ml import PipelineModel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.feature_names import FeatureSet
from lcdweather.ml.pipelines import build_pipeline
from lcdweather.ml.splits import Splits


@dataclass(frozen=True)
class ModelSpec:
    name: str
    make_estimator: Callable[..., Any]
    param_grid: Sequence[dict[str, Any]]


@dataclass(frozen=True)
class TunedModel:
    spec: ModelSpec
    best_params: dict[str, Any]
    # Fitted on train only: its validation predictions are honest.
    validation_model: PipelineModel
    # Refit on train + validation with the chosen parameters for the test split.
    final_model: PipelineModel
    trials: list[dict]


def tune_model(
    spec: ModelSpec,
    features: FeatureSet,
    splits: Splits,
    score_validation: Callable[[DataFrame], float],
    metric_name: str,
    higher_is_better: bool,
) -> TunedModel:
    """Fit every grid point on train, keep the best validation score, then refit."""
    if not spec.param_grid:
        raise ValueError(f"Empty parameter grid for model {spec.name}")
    candidates = []
    for params in spec.param_grid:
        model = build_pipeline(spec.make_estimator(**params), features).fit(splits.train)
        score = score_validation(model.transform(splits.validation))
        candidates.append((score, params, model))
    pick = max if higher_is_better else min
    best_score, best_params, best_model = pick(candidates, key=lambda item: item[0])
    trials = [
        {
            "model": spec.name,
            "params": json.dumps(params, sort_keys=True),
            "metric": metric_name,
            "validation_score": score,
            "selected": params is best_params,
        }
        for score, params, _ in candidates
    ]
    refit_data = splits.train.unionByName(splits.validation)
    final_model = build_pipeline(spec.make_estimator(**best_params), features).fit(refit_data)
    return TunedModel(spec, best_params, best_model, final_model, trials)


def append_model_output(scored: DataFrame, model: PipelineModel, output, alias: str) -> DataFrame:
    """Add one model's output column, discarding the pipeline's working columns."""
    kept = [F.col(name) for name in scored.columns]
    return model.transform(scored).select(*kept, output.alias(alias))
