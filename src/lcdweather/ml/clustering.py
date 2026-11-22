"""Question 4 clustering: k-means over city climate profiles, k chosen by silhouette."""

from __future__ import annotations

from collections.abc import Sequence

from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.daily_features import CITY_KEY
from lcdweather.ml.export import ResultTable
from lcdweather.ml.feature_names import FeatureSet
from lcdweather.ml.kmeans_features import PROFILE_COLUMNS, build_city_profiles
from lcdweather.ml.pipelines import FEATURES_COL, feature_stages, usable_feature_set
from lcdweather.ml.settings import RANDOM_SEED

CLUSTER_COL = "cluster"
DEFAULT_K_VALUES = (2, 3, 4, 5, 6)
KMEANS_MAX_ITERATIONS = 100
MIN_CLUSTERS_FOR_SILHOUETTE = 2


def scale_profiles(profiles: DataFrame) -> DataFrame:
    """Impute, assemble and standardize the profile columns into `features`."""
    features = usable_feature_set(profiles, FeatureSet(numeric=PROFILE_COLUMNS))
    stages = feature_stages(features, impute_strategy="mean")
    return Pipeline(stages=stages).fit(profiles).transform(profiles)


def _silhouette(assigned: DataFrame) -> float | None:
    populated = assigned.select(CLUSTER_COL).distinct().count()
    if populated < MIN_CLUSTERS_FOR_SILHOUETTE:
        return None
    evaluator = ClusteringEvaluator(featuresCol=FEATURES_COL, predictionCol=CLUSTER_COL)
    return evaluator.evaluate(assigned)


def fit_k_range(scaled: DataFrame, k_values: Sequence[int]) -> list[dict]:
    """Fit k-means for each feasible k; a silhouette needs k < number of cities."""
    n_cities = scaled.count()
    fits = []
    for k in k_values:
        if k >= n_cities:
            continue
        estimator = KMeans(
            k=k,
            seed=RANDOM_SEED,
            maxIter=KMEANS_MAX_ITERATIONS,
            featuresCol=FEATURES_COL,
            predictionCol=CLUSTER_COL,
        )
        model = estimator.fit(scaled)
        assigned = model.transform(scaled).cache()
        fits.append(
            {
                "k": k,
                "silhouette": _silhouette(assigned),
                "within_cluster_sse": model.summary.trainingCost,
                "assigned": assigned,
            }
        )
    return fits


def select_best_k(fits: list[dict]) -> int:
    """Highest silhouette wins; ties go to the smaller k."""
    scored = [fit for fit in fits if fit["silhouette"] is not None]
    if not scored:
        raise ValueError("No k produced at least two populated clusters")
    return max(scored, key=lambda fit: (fit["silhouette"], -fit["k"]))["k"]


def run_kmeans(
    daily: DataFrame, hourly: DataFrame, k_values: Sequence[int] = DEFAULT_K_VALUES
) -> dict[str, ResultTable]:
    profiles = build_city_profiles(daily, hourly).cache()
    fits = fit_k_range(scale_profiles(profiles).cache(), k_values)
    best_k = select_best_k(fits)
    silhouettes = [
        {
            "k": fit["k"],
            "silhouette": fit["silhouette"],
            "within_cluster_sse": fit["within_cluster_sse"],
            "selected": fit["k"] == best_k,
        }
        for fit in fits
    ]
    assignments = []
    for fit in fits:
        rows = fit["assigned"].select(CITY_KEY, "city", CLUSTER_COL).orderBy(CITY_KEY)
        for row in rows.collect():
            assignments.append({"k": fit["k"], "selected": fit["k"] == best_k, **row.asDict()})
    best = next(fit["assigned"] for fit in fits if fit["k"] == best_k)
    clusters = best.select(CITY_KEY, F.col(CLUSTER_COL))
    return {
        "kmeans_silhouette": silhouettes,
        "kmeans_assignments": assignments,
        "kmeans_city_features": profiles.join(clusters, CITY_KEY).orderBy(CITY_KEY),
    }
