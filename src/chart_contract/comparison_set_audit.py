"""Audit truncated-rank comparison-set completeness."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .contracts import declared_unit_from_spec, is_numeric_series
from .comparison_set import (
    COMPARISON_SET_CONTRACT_KEY,
    OMITTED_MASS_WARN_SHARE,
    aggregate_other_transforms,
    build_comparison_set_summary,
    metric_mass_severity,
    parse_comparison_set_contract,
    validate_omitted_behavior,
)
from .rank import build_rank_selection, duplicate_rank_categories, parse_rank_contract, validate_top_n


def audit_comparison_set_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) != "rank":
        return
    category_field = getattr(chart, "x", None)
    metric_field = getattr(chart, "y", None)
    if (
        not category_field
        or not metric_field
        or category_field not in chart.data.columns
        or metric_field not in chart.data.columns
        or duplicate_rank_categories(chart.data, category_field)
        or not is_numeric_series(chart.data[metric_field])
    ):
        return
    try:
        top_n = validate_top_n(getattr(chart, "top_n", None))
    except ValueError:
        return
    selection = build_rank_selection(
        chart.data,
        category_field=category_field,
        metric_field=metric_field,
        top_n=top_n,
    )
    behavior_raw = getattr(chart, "omitted_behavior", None)
    if selection.summary.omitted_category_count == 0:
        if behavior_raw is not None:
            report.add(
                "contract.rank.comparison_set",
                FAIL,
                "omitted_behavior is declared even though the rank omits no eligible categories.",
                suggestion="Remove omitted_behavior or choose a top_n that actually truncates the comparison set.",
                field="omitted_behavior",
            )
        return

    try:
        behavior = validate_omitted_behavior(behavior_raw)
    except ValueError as exc:
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            str(exc),
            field="omitted_behavior",
        )
        return
    if behavior is None:
        report.add(
            "contract.rank.comparison_set",
            WARN,
            (
                f"Rank omits {selection.summary.omitted_category_count} eligible categories but "
                "does not declare whether they are excluded or summarized as Other."
            ),
            suggestion="Set omitted_behavior='exclude' or 'aggregate_other'.",
            field="omitted_behavior",
        )
        return

    try:
        summary = build_comparison_set_summary(
            chart.data,
            selection=selection,
            omitted_behavior=behavior,
            other_label=getattr(chart, "other_label", "Other"),
            unit=getattr(chart, "unit", None),
        )
    except ValueError as exc:
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            str(exc),
            suggestion="Use explicit exclusion or a valid additive Other bucket.",
            field="omitted_behavior",
        )
        return

    report.add(
        "contract.rank.comparison_set",
        PASS,
        (
            f"Truncated comparison set explicitly uses omitted_behavior={summary.omitted_behavior!r}; "
            f"{summary.omitted_category_count} categories are omitted from the ranked set."
        ),
    )
    _add_metric_mass_finding(report, summary)

    if summary.omitted_behavior == "aggregate_other":
        report.add(
            "visual.rank.other_bucket",
            PASS,
            (
                f"First-party rendering will sum omitted categories into {summary.other_label!r} "
                f"with metric value {summary.other_metric_value:g} and pin that summary bucket last."
            ),
        )


def audit_comparison_set_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    analytical_spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or usermeta.get("chart_contract_intent") != "rank":
        return

    try:
        rank_contract = parse_rank_contract(spec)
    except ValueError:
        return
    if rank_contract is None or rank_contract["omitted_category_count"] <= 0:
        if isinstance(usermeta, Mapping) and COMPARISON_SET_CONTRACT_KEY in usermeta:
            report.add(
                "contract.rank.comparison_set",
                FAIL,
                "comparison_set_contract is present even though rank_contract omits no categories.",
                field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
            )
        return

    try:
        contract = parse_comparison_set_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            str(exc),
            suggestion="Regenerate comparison_set_contract from the final rank evidence.",
            field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
        )
        return
    if contract is None:
        report.add(
            "contract.rank.comparison_set",
            WARN,
            (
                f"Rank spec omits {rank_contract['omitted_category_count']} categories without "
                "declaring exclude versus aggregate_other completeness behavior."
            ),
            suggestion="Add a closed version-1 comparison_set_contract.",
            field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
        )
        return
    if frame is None:
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            "comparison_set_contract cannot be verified without full source evidence.",
            suggestion="Supply the full pre-truncation category/metric evidence.",
            field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
        )
        return

    category_field = rank_contract["category_field"]
    metric_field = rank_contract["metric_field"]
    if (
        category_field not in frame.columns
        or metric_field not in frame.columns
        or duplicate_rank_categories(frame, category_field)
        or not is_numeric_series(frame[metric_field])
    ):
        return

    selection = build_rank_selection(
        frame,
        category_field=category_field,
        metric_field=metric_field,
        top_n=rank_contract["top_n"],
    )
    try:
        expected = build_comparison_set_summary(
            frame,
            selection=selection,
            omitted_behavior=contract["omitted_behavior"],
            other_label=contract["other_label"] or "Other",
            unit=declared_unit_from_spec(spec),
        )
    except ValueError as exc:
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            str(exc),
            suggestion="Regenerate comparison-set semantics from the full source evidence.",
            field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
        )
        return

    if contract != expected.to_dict():
        report.add(
            "contract.rank.comparison_set",
            FAIL,
            "Comparison-set counts, metric totals, shares, or Other receipt do not match supplied evidence.",
            suggestion="Regenerate comparison_set_contract from the full source evidence.",
            field=f"usermeta.{COMPARISON_SET_CONTRACT_KEY}",
        )
        return

    report.add(
        "contract.rank.comparison_set",
        PASS,
        (
            f"Comparison-set completeness is reproducible: {expected.selected_category_count} selected, "
            f"{expected.omitted_category_count} omitted, behavior={expected.omitted_behavior!r}."
        ),
    )
    _add_metric_mass_finding(report, expected)

    if expected.omitted_behavior != "aggregate_other":
        return

    expected_transforms = aggregate_other_transforms(
        category_field=category_field,
        metric_field=metric_field,
        selected_categories=selection.displayed_categories,
        other_label=expected.other_label or "Other",
    )
    actual_transforms = analytical_spec.get("transform")
    if actual_transforms != expected_transforms:
        report.add(
            "visual.rank.other_bucket",
            FAIL,
            "Other-bucket transforms do not exactly match the reproducible omitted-category sum.",
            suggestion="Regenerate the aggregate_other rank spec from full source evidence.",
            field="transform",
        )
    else:
        report.add(
            "visual.rank.other_bucket",
            PASS,
            (
                f"Other bucket exactly collapses omitted categories with sum({metric_field})="
                f"{expected.other_metric_value:g}."
            ),
            field="transform",
        )


def _add_metric_mass_finding(report: AuditReport, summary: Any) -> None:
    severity = metric_mass_severity(summary)
    if summary.omitted_metric_share is None:
        report.add(
            "data.rank.omitted_metric_mass",
            WARN,
            (
                f"Omitted metric total is {summary.omitted_metric_total:g}, but a share is not "
                "defined because eligible metric values include negatives or total to a non-positive value."
            ),
            suggestion="Review omission materiality directly from the metric totals.",
        )
        return

    omitted_pct = summary.omitted_metric_share * 100.0
    selected_pct = summary.selected_metric_share * 100.0
    if severity == WARN:
        report.add(
            "data.rank.omitted_metric_mass",
            WARN,
            (
                f"Excluded categories contain {omitted_pct:.1f}% of eligible metric mass; "
                f"the selected ranked categories show only {selected_pct:.1f}%."
            ),
            suggestion=(
                "Consider aggregate_other or explicitly disclose that most metric mass is outside "
                "the displayed ranked categories."
            ),
        )
    else:
        report.add(
            "data.rank.omitted_metric_mass",
            PASS,
            (
                f"Comparison-set receipts account for all metric mass: selected {selected_pct:.1f}%, "
                f"omitted {omitted_pct:.1f}%."
            ),
        )
