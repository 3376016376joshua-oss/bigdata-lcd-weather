"""MLlib Pipeline assembly: impute, encode, assemble, scale, then the estimator."""

from __future__ import annotations

import logging

from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import (
    Imputer,
    OneHotEncoder,
    StandardScaler,
    StringIndexer,
    VectorAssembler,
)
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.feature_names import (
    IMPUTED_SUFFIX,
    INDEX_SUFFIX,
    ONEHOT_SUFFIX,
    FeatureSet,
    feature_names,
)

FEATURES_COL = "features"
RAW_FEATURES_COL = "features_raw"

logger = logging.getLogger(__name__)


def usable_feature_set(train: DataFrame, features: FeatureSet) -> FeatureSet:
    """Drop numeric features with no training values, which cannot be imputed."""
    counts = train.agg(*[F.count(F.col(name)).alias(name) for name in features.numeric])
    non_null = counts.first().asDict()
    kept = tuple(name for name in features.numeric if non_null[name] > 0)
    dropped = sorted(set(features.numeric) - set(kept))
    if dropped:
        logger.warning("Dropping features with no training values: %s", dropped)
    if not kept:
        raise ValueError("No numeric feature has any non-null training value")
    return FeatureSet(numeric=kept, categorical=features.categorical)


def feature_stages(features: FeatureSet, impute_strategy: str = "median") -> list:
    """Stages turning raw columns into a scaled `features` vector."""
    imputed = [f"{name}{IMPUTED_SUFFIX}" for name in features.numeric]
    stages: list = [
        Imputer(
            strategy=impute_strategy,
            inputCols=list(features.numeric),
            outputCols=imputed,
        )
    ]
    encoded: list[str] = []
    if features.categorical:
        indexed = [f"{name}{INDEX_SUFFIX}" for name in features.categorical]
        encoded = [f"{name}{ONEHOT_SUFFIX}" for name in features.categorical]
        stages.append(
            StringIndexer(
                inputCols=list(features.categorical),
                outputCols=indexed,
                handleInvalid="keep",
            )
        )
        stages.append(OneHotEncoder(inputCols=indexed, outputCols=encoded))
    stages.append(VectorAssembler(inputCols=imputed + encoded, outputCol=RAW_FEATURES_COL))
    stages.append(
        StandardScaler(
            inputCol=RAW_FEATURES_COL,
            outputCol=FEATURES_COL,
            withMean=True,
            withStd=True,
        )
    )
    return stages


def build_pipeline(estimator, features: FeatureSet) -> Pipeline:
    return Pipeline(stages=feature_stages(features) + [estimator])


def fitted_feature_names(model: PipelineModel, sample: DataFrame, size: int) -> list[str]:
    """Names of the assembled vector slots, read from the transformed schema."""
    schema = model.transform(sample.limit(1)).schema
    return feature_names(schema[RAW_FEATURES_COL].metadata, size)


def feature_weights(model: PipelineModel, sample: DataFrame, model_name: str) -> list[dict]:
    """Per-feature importance (trees) or standardized coefficient (linear models)."""
    fitted = model.stages[-1]
    if hasattr(fitted, "featureImportances"):
        signed = fitted.featureImportances.toArray().tolist()
    else:
        signed = fitted.coefficients.toArray().tolist()
    names = fitted_feature_names(model, sample, len(signed))
    rows = [
        {
            "model": model_name,
            "feature": name,
            "importance": abs(value),
            "signed_value": value,
        }
        for name, value in zip(names, signed)
    ]
    return sorted(rows, key=lambda row: row["importance"], reverse=True)
