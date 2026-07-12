"""Deterministic data preparation for statistical diagnostic plots."""

from __future__ import annotations

from statistics import NormalDist, fmean, stdev
from typing import Any

import pandas as pd

QQ_THEORETICAL_FIELD = "_theoretical_quantile"
QQ_SAMPLE_FIELD = "_sample_quantile"
QQ_REFERENCE_FIELD = "_reference_quantile"
ECDF_VALUE_FIELD = "_ecdf_value"
ECDF_PROBABILITY_FIELD = "_cumulative_probability"


def qq_records(
    data: pd.DataFrame,
    *,
    value: str,
    group: str | None = None,
    distribution: str = "normal",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return QQ points and fitted reference-line records."""
    if distribution != "normal":
        raise ValueError("QQ plots currently support only the normal reference distribution.")
    _require_columns(data, value, group)

    points: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for group_value, frame in _grouped_frames(data, group):
        values = sorted(float(item) for item in frame[value].dropna())
        if not values:
            continue

        probabilities = [(index - 0.5) / len(values) for index in range(1, len(values) + 1)]
        theoretical = [NormalDist().inv_cdf(probability) for probability in probabilities]
        group_payload = _group_payload(group, group_value)
        points.extend(
            {
                QQ_THEORETICAL_FIELD: expected,
                QQ_SAMPLE_FIELD: observed,
                **group_payload,
            }
            for expected, observed in zip(theoretical, values)
        )

        center = fmean(values)
        scale = stdev(values) if len(values) > 1 else 0.0
        for expected in (theoretical[0], theoretical[-1]):
            references.append(
                {
                    QQ_THEORETICAL_FIELD: expected,
                    QQ_REFERENCE_FIELD: center + scale * expected,
                    **group_payload,
                }
            )

    return points, references


def ecdf_records(
    data: pd.DataFrame,
    *,
    value: str,
    group: str | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic empirical-CDF step records."""
    _require_columns(data, value, group)

    records: list[dict[str, Any]] = []
    for group_value, frame in _grouped_frames(data, group):
        values = frame[value].dropna().astype(float)
        if values.empty:
            continue
        counts = values.value_counts(sort=False).sort_index()
        cumulative = counts.cumsum() / counts.sum()
        group_payload = _group_payload(group, group_value)
        first_value = float(counts.index[0])
        records.append(
            {
                ECDF_VALUE_FIELD: first_value,
                ECDF_PROBABILITY_FIELD: 0.0,
                **group_payload,
            }
        )
        records.extend(
            {
                ECDF_VALUE_FIELD: float(observed),
                ECDF_PROBABILITY_FIELD: float(probability),
                **group_payload,
            }
            for observed, probability in cumulative.items()
        )

    return records


def _grouped_frames(data: pd.DataFrame, group: str | None):
    if group is None:
        yield None, data
        return
    for group_value, frame in data.groupby(group, dropna=False, sort=False):
        yield group_value, frame


def _group_payload(group: str | None, value: Any) -> dict[str, Any]:
    if group is None:
        return {}
    return {group: None if pd.isna(value) else value}


def _require_columns(data: pd.DataFrame, value: str, group: str | None) -> None:
    missing = [field for field in (value, group) if field and field not in data.columns]
    if missing:
        raise ValueError(f"Missing required statistical plot column(s): {', '.join(missing)}")
