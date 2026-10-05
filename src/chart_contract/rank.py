"""Deterministic rank/top-N contract helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

RANK_CONTRACT_KEY = "rank_contract"
RANK_CONTRACT_VERSION = 1
RANK_ORDER = "descending"
RANK_TIE_POLICY = "include_cutoff_ties"


@dataclass(frozen=True, slots=True)
class RankSummary:
    category_field: str
    metric_field: str
    order: str
    top_n: int | None
    tie_policy: str
    eligible_category_count: int
    displayed_category_count: int
    omitted_category_count: int
    cutoff_tie_expanded: bool

    def to_dict(self) -> dict[str, Any]:
        return {"version": RANK_CONTRACT_VERSION, **asdict(self)}


@dataclass(frozen=True, slots=True)
class RankSelection:
    summary: RankSummary
    displayed_categories: tuple[Any, ...]


def validate_top_n(top_n: Any) -> int | None:
    if top_n is None:
        return None
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
        raise ValueError("Rank top_n must be a positive integer or None.")
    return top_n


def duplicate_rank_categories(frame: pd.DataFrame, category_field: str) -> tuple[Any, ...]:
    if category_field not in frame.columns:
        return ()
    values = frame.loc[frame[category_field].notna(), category_field]
    duplicated = values[values.duplicated(keep=False)]
    if duplicated.empty:
        return ()
    unique = list(dict.fromkeys(duplicated.tolist()))
    return tuple(sorted(unique, key=_category_sort_key))


def build_rank_selection(
    frame: pd.DataFrame,
    *,
    category_field: str,
    metric_field: str,
    top_n: int | None,
) -> RankSelection:
    normalized_top_n = validate_top_n(top_n)
    if category_field not in frame.columns or metric_field not in frame.columns:
        raise ValueError("Rank selection requires category and metric columns.")
    if duplicate_rank_categories(frame, category_field):
        raise ValueError("Rank selection requires one row per non-null category.")

    eligible = frame.loc[
        frame[category_field].notna() & frame[metric_field].notna(),
        [category_field, metric_field],
    ].copy()
    if eligible.empty:
        summary = RankSummary(
            category_field=category_field,
            metric_field=metric_field,
            order=RANK_ORDER,
            top_n=normalized_top_n,
            tie_policy=RANK_TIE_POLICY,
            eligible_category_count=0,
            displayed_category_count=0,
            omitted_category_count=0,
            cutoff_tie_expanded=False,
        )
        return RankSelection(summary=summary, displayed_categories=())

    records = [
        (row[category_field], row[metric_field])
        for _, row in eligible.iterrows()
    ]
    records.sort(key=lambda item: (-float(item[1]), _category_sort_key(item[0])))

    eligible_count = len(records)
    cutoff_tie_expanded = False
    if normalized_top_n is None or normalized_top_n >= eligible_count:
        displayed = records
    else:
        cutoff_value = records[normalized_top_n - 1][1]
        displayed = [item for item in records if item[1] >= cutoff_value]
        cutoff_tie_expanded = len(displayed) > normalized_top_n

    displayed_categories = tuple(item[0] for item in displayed)
    displayed_count = len(displayed_categories)
    summary = RankSummary(
        category_field=category_field,
        metric_field=metric_field,
        order=RANK_ORDER,
        top_n=normalized_top_n,
        tie_policy=RANK_TIE_POLICY,
        eligible_category_count=eligible_count,
        displayed_category_count=displayed_count,
        omitted_category_count=eligible_count - displayed_count,
        cutoff_tie_expanded=cutoff_tie_expanded,
    )
    return RankSelection(summary=summary, displayed_categories=displayed_categories)


def parse_rank_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or RANK_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(RANK_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.rank_contract must be an object.")

    expected_fields = {
        "version",
        "category_field",
        "metric_field",
        "order",
        "top_n",
        "tie_policy",
        "eligible_category_count",
        "displayed_category_count",
        "omitted_category_count",
        "cutoff_tie_expanded",
    }
    if set(contract) != expected_fields:
        missing = sorted(expected_fields - set(contract))
        extra = sorted(set(contract) - expected_fields)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.rank_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != RANK_CONTRACT_VERSION:
        raise ValueError(f"usermeta.rank_contract.version must equal {RANK_CONTRACT_VERSION}.")

    category_field = contract.get("category_field")
    metric_field = contract.get("metric_field")
    if not isinstance(category_field, str) or not category_field:
        raise ValueError("usermeta.rank_contract.category_field must be a non-empty string.")
    if not isinstance(metric_field, str) or not metric_field:
        raise ValueError("usermeta.rank_contract.metric_field must be a non-empty string.")
    if contract.get("order") != RANK_ORDER:
        raise ValueError("usermeta.rank_contract.order must equal 'descending'.")
    if contract.get("tie_policy") != RANK_TIE_POLICY:
        raise ValueError(
            "usermeta.rank_contract.tie_policy must equal 'include_cutoff_ties'."
        )

    top_n = validate_top_n(contract.get("top_n"))
    counts: dict[str, int] = {}
    for field in (
        "eligible_category_count",
        "displayed_category_count",
        "omitted_category_count",
    ):
        value = contract.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"usermeta.rank_contract.{field} must be a non-negative integer.")
        counts[field] = value

    if (
        counts["displayed_category_count"] + counts["omitted_category_count"]
        != counts["eligible_category_count"]
    ):
        raise ValueError(
            "usermeta.rank_contract displayed + omitted category counts must equal eligible count."
        )

    cutoff_tie_expanded = contract.get("cutoff_tie_expanded")
    if not isinstance(cutoff_tie_expanded, bool):
        raise ValueError("usermeta.rank_contract.cutoff_tie_expanded must be boolean.")
    if top_n is None and (
        counts["omitted_category_count"] != 0 or cutoff_tie_expanded
    ):
        raise ValueError(
            "Untruncated rank contracts cannot omit categories or declare cutoff tie expansion."
        )

    return {
        "version": RANK_CONTRACT_VERSION,
        "category_field": category_field,
        "metric_field": metric_field,
        "order": RANK_ORDER,
        "top_n": top_n,
        "tie_policy": RANK_TIE_POLICY,
        **counts,
        "cutoff_tie_expanded": cutoff_tie_expanded,
    }


def rank_filter_categories(spec: Mapping[str, Any], category_field: str) -> tuple[Any, ...] | None:
    """Read the bounded first-party top-N oneOf filter without evaluating expressions."""

    transforms = spec.get("transform")
    if transforms is None:
        return None
    if not isinstance(transforms, list) or len(transforms) != 1:
        return ()
    transform = transforms[0]
    if not isinstance(transform, Mapping) or set(transform) != {"filter"}:
        return ()
    predicate = transform.get("filter")
    if not isinstance(predicate, Mapping):
        return ()
    if set(predicate) != {"field", "oneOf"}:
        return ()
    if predicate.get("field") != category_field:
        return ()
    one_of = predicate.get("oneOf")
    if not isinstance(one_of, list):
        return ()
    return tuple(one_of)


def _category_sort_key(value: Any) -> tuple[str, str]:
    return type(value).__name__, str(value)
