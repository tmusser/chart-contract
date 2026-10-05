"""Rank/top-N audit semantics for chart-contract specs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import (
    FAIL,
    PASS,
    WARN,
    AuditReport,
    _encoding_field,
    _encoding_type,
    _mark_type,
)
from .contracts import is_numeric_series
from .rank import (
    RANK_CONTRACT_KEY,
    build_rank_selection,
    duplicate_rank_categories,
    parse_rank_contract,
    rank_filter_categories,
)


def audit_rank_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    analytical_spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or usermeta.get("chart_contract_intent") != "rank":
        return

    mark = _mark_type(analytical_spec)
    encoding = analytical_spec.get("encoding")
    if not isinstance(encoding, Mapping):
        report.add(
            "visual.rank.sort_order",
            FAIL,
            "Rank spec is missing encodings required to verify descending order.",
            field="encoding",
        )
        return

    x_encoding = encoding.get("x")
    y_encoding = encoding.get("y")
    category_field = _encoding_field(y_encoding)
    metric_field = _encoding_field(x_encoding)

    if (
        mark != "bar"
        or _encoding_type(x_encoding) != "quantitative"
        or _encoding_type(y_encoding) not in {"nominal", "ordinal"}
        or not category_field
        or not metric_field
    ):
        report.add(
            "visual.rank.sort_order",
            FAIL,
            "Rank specs require horizontal bars with quantitative x and nominal/ordinal y encodings.",
            suggestion="Use a quantitative metric on x and ranked category on y.",
            field="encoding",
        )
        return

    try:
        contract = parse_rank_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.rank.truncation",
            FAIL,
            str(exc),
            suggestion="Regenerate rank metadata from the final first-party rank contract.",
            field=f"usermeta.{RANK_CONTRACT_KEY}",
        )
        return

    if contract is None:
        report.add(
            "contract.rank.truncation",
            FAIL,
            "Rank spec is missing usermeta.rank_contract.",
            suggestion="Declare the rank order, top_n, tie policy, and eligible/displayed/omitted counts.",
            field=f"usermeta.{RANK_CONTRACT_KEY}",
        )
        return

    report.add(
        "contract.rank.top_n",
        PASS,
        (
            "Rank spec declares the full eligible category set."
            if contract["top_n"] is None
            else f"Rank spec explicitly declares top_n={contract['top_n']} with cutoff ties included."
        ),
        field=f"usermeta.{RANK_CONTRACT_KEY}.top_n",
    )

    if contract["category_field"] != category_field or contract["metric_field"] != metric_field:
        report.add(
            "contract.rank.truncation",
            FAIL,
            "Rank contract category/metric fields do not match the visual encodings.",
            suggestion="Regenerate rank metadata from the final rank spec.",
            field=f"usermeta.{RANK_CONTRACT_KEY}",
        )
        return

    if frame is None or category_field not in frame.columns or metric_field not in frame.columns:
        report.add(
            "contract.rank.truncation",
            FAIL,
            "Rank truncation cannot be verified without reconstructable category and metric evidence.",
            suggestion="Provide the full source evidence used to build the ranked view.",
            field=f"usermeta.{RANK_CONTRACT_KEY}",
        )
        return

    duplicates = duplicate_rank_categories(frame, category_field)
    if duplicates:
        report.add(
            "data.rank.category_unique",
            FAIL,
            f"Rank spec evidence contains duplicate categories in '{category_field}'.",
            suggestion="Provide exactly one source row per ranked category; do not silently aggregate duplicates.",
            field=category_field,
        )
        return
    report.add(
        "data.rank.category_unique",
        PASS,
        "Rank spec evidence has at most one row per non-null category.",
    )

    if not is_numeric_series(frame[metric_field]):
        return

    selection = build_rank_selection(
        frame,
        category_field=category_field,
        metric_field=metric_field,
        top_n=contract["top_n"],
    )
    expected_contract = selection.summary.to_dict()
    if contract != expected_contract:
        report.add(
            "contract.rank.truncation",
            FAIL,
            "Rank contract counts or tie-expansion metadata do not match the supplied evidence.",
            suggestion="Regenerate the rank contract from the full source evidence.",
            field=f"usermeta.{RANK_CONTRACT_KEY}",
        )
    else:
        report.add(
            "contract.rank.truncation",
            PASS,
            (
                f"Rank truncation is reproducible: {selection.summary.displayed_category_count} displayed of "
                f"{selection.summary.eligible_category_count} eligible categories; "
                f"{selection.summary.omitted_category_count} omitted."
            ),
        )

    expected_categories = list(selection.displayed_categories)
    sort_value = y_encoding.get("sort") if isinstance(y_encoding, Mapping) else None
    if sort_value == expected_categories:
        report.add(
            "visual.rank.sort_order",
            PASS,
            "Rank category order exactly matches descending metric order with deterministic display order for ties.",
            field="encoding.y.sort",
        )
    else:
        report.add(
            "visual.rank.sort_order",
            FAIL,
            "Rank category sort does not match the descending metric order declared by the rank contract.",
            suggestion="Use the deterministic category order emitted by the first-party rank renderer.",
            field="encoding.y.sort",
        )

    filtered_categories = rank_filter_categories(analytical_spec, category_field)
    should_filter = selection.summary.omitted_category_count > 0
    if should_filter:
        if filtered_categories is None:
            report.add(
                "contract.rank.truncation",
                FAIL,
                "Rank contract declares omitted categories but the spec has no explicit bounded top-N filter.",
                suggestion="Preserve full source rows and filter the displayed rank categories explicitly.",
                field="transform",
            )
        elif not filtered_categories:
            report.add(
                "contract.rank.truncation",
                FAIL,
                "Rank truncation filter is not the supported category oneOf predicate.",
                suggestion="Use one bounded category oneOf filter for first-party top-N truncation.",
                field="transform",
            )
        elif _normalized_categories(filtered_categories) != _normalized_categories(expected_categories):
            report.add(
                "contract.rank.truncation",
                FAIL,
                "Rank truncation filter does not select the reproducible top-N category set.",
                suggestion="Regenerate the selected categories from the full rank evidence.",
                field="transform[0].filter",
            )
        else:
            report.add(
                "contract.rank.truncation",
                PASS,
                "Rank top-N filter exactly matches the reproducible displayed category set.",
                field="transform[0].filter",
            )
    elif filtered_categories is not None:
        report.add(
            "contract.rank.truncation",
            FAIL,
            "Rank spec carries a truncation filter even though the rank contract omits no eligible categories.",
            suggestion="Remove the stale filter or regenerate the rank contract.",
            field="transform",
        )

    if selection.summary.cutoff_tie_expanded:
        report.add(
            "data.rank.cutoff_tie",
            WARN,
            (
                f"top_n={selection.summary.top_n} expands to "
                f"{selection.summary.displayed_category_count} categories because the cutoff metric is tied."
            ),
            suggestion="Keep the tie-inclusive result or choose a cutoff that does not split equal metric values.",
            field=metric_field,
        )
    else:
        report.add(
            "data.rank.cutoff_tie",
            PASS,
            "Rank cutoff does not split equal metric values.",
        )

    displayed_count = selection.summary.displayed_category_count
    if displayed_count > 12:
        report.add(
            "readability.rank.category_count",
            WARN,
            f"Rank spec displays {displayed_count} categories, which may be hard to read.",
            suggestion="Use an explicit top_n or another long-tail summary before sharing.",
            field=category_field,
        )
    else:
        report.add(
            "readability.rank.category_count",
            PASS,
            f"Rank spec displays {displayed_count} categories, within the readability limit.",
        )


def _normalized_categories(values: tuple[Any, ...] | list[Any]) -> list[tuple[str, str]]:
    return sorted(
        ((type(value).__name__, str(value)) for value in values),
        key=lambda item: item,
    )
