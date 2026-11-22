"""Feature sets and human-readable names for assembled feature vectors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

IMPUTED_SUFFIX = "__imputed"
INDEX_SUFFIX = "__index"
ONEHOT_SUFFIX = "__onehot"


@dataclass(frozen=True)
class FeatureSet:
    numeric: tuple[str, ...]
    categorical: tuple[str, ...] = ()


def clean_feature_name(raw_name: str) -> str:
    """Turn pipeline-internal column names into the original feature names."""
    return raw_name.replace(IMPUTED_SUFFIX, "").replace(f"{ONEHOT_SUFFIX}_", "=")


def feature_names(vector_metadata: Mapping[str, Any], size: int) -> list[str]:
    """Names for each slot of an assembled vector from its ML attribute metadata."""
    names = [f"feature_{index}" for index in range(size)]
    attribute_groups = vector_metadata.get("ml_attr", {}).get("attrs", {})
    for attributes in attribute_groups.values():
        for attribute in attributes:
            index = attribute.get("idx")
            if index is not None and index < size and "name" in attribute:
                names[index] = clean_feature_name(attribute["name"])
    return names
