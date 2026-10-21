"""Altair renderer helpers."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd

from ..contracts import is_datetime_like, is_numeric_series, is_percent_unit
from ..comparison import COMPARISON_INTENTS, build_comparison_summary, changes_match, comparison_declaration
from ..comparison_set import (
    ComparisonSetSummary,
    aggregate_other_transforms,
    build_comparison_set_summary,
    comparison_set_sort,
)
from ..directionality import DIRECTIONALITY_INTENTS, chart_directionality_contract, parse_directionality_contract
from ..grain import GRAIN_INTENTS, build_grain_summary, visible_grain_fields_for_chart
from ..metric_definition import METRIC_DEFINITION_INTENTS, chart_metric_definition_contract
from ..population_sampling import (
    POPULATION_INTENTS,
    chart_population_contract,
    parse_population_contract,
    sample_member_status,
    weight_status,
)
from ..process_tree import process_tree_layout_records, process_tree_summary
from ..rank import RankSelection, build_rank_selection, duplicate_rank_categories, validate_top_n
from ..reconciliation import (
    RECONCILIATION_INTENTS,
    build_reconciliation_summary,
    chart_reconciliation_declaration,
    reconciliation_matches,
)
from ..ratio import RATIO_INTENTS, chart_ratio_contract
from ..set_membership import membership_summary, venn_layout_records
from ..transforms import build_transform_lineage, first_party_transform_declaration
from ..time_window import build_time_window_summary, time_window_declaration
from ..uncertainty import (
    UNCERTAINTY_INTENTS,
    chart_uncertainty_contract,
    interval_bounds_status,
    parse_uncertainty_contract,
)
from ..unit_conversion import (
    UNIT_CONVERSION_INTENTS,
    chart_unit_conversion_contract,
    conversion_arithmetic_status,
    parse_unit_conversion_contract,
    source_unit_basis_status,
)
from ..target import TARGET_INTENTS, build_target_summary, target_declaration
from ..statistics import (
    ECDF_PROBABILITY_FIELD,
    ECDF_VALUE_FIELD,
    QQ_REFERENCE_FIELD,
    QQ_SAMPLE_FIELD,
    QQ_THEORETICAL_FIELD,
    ecdf_records,
    qq_records,
)


def render_chart(chart: Any) -> alt.Chart:
    records = _prepare_records(chart.data)
    subtitle = []
    if chart.source:
        subtitle.append(f"Source: {chart.source}")
    if chart.caveat:
        subtitle.append(f"Caveat: {chart.caveat}")
    if chart.filters:
        subtitle.append(f"Filters: {chart.filters}")

    usermeta = dict(chart.metadata or {})
    rank_selection: RankSelection | None = None
    comparison_set_summary: ComparisonSetSummary | None = None
    if chart.intent == "rank":
        usermeta.setdefault("chart_contract_intent", "rank")
        top_n = validate_top_n(getattr(chart, "top_n", None))
        category_ok = chart.x in chart.data.columns and not duplicate_rank_categories(chart.data, chart.x)
        metric_ok = chart.y in chart.data.columns and is_numeric_series(chart.data[chart.y])
        if top_n is not None and not category_ok:
            raise ValueError("Rank top_n rendering requires exactly one row per non-null category.")
        if top_n is not None and not metric_ok:
            raise ValueError("Rank top_n rendering requires a numeric metric field.")
        if category_ok and metric_ok:
            rank_selection = build_rank_selection(
                chart.data,
                category_field=chart.x,
                metric_field=chart.y,
                top_n=top_n,
            )
            usermeta["rank_contract"] = rank_selection.summary.to_dict()
            if (
                rank_selection.summary.omitted_category_count > 0
                and getattr(chart, "omitted_behavior", None) is not None
            ):
                comparison_set_summary = build_comparison_set_summary(
                    chart.data,
                    selection=rank_selection,
                    omitted_behavior=chart.omitted_behavior,
                    other_label=getattr(chart, "other_label", "Other"),
                    unit=chart.unit,
                )
                usermeta["comparison_set_contract"] = comparison_set_summary.to_dict()
            elif (
                rank_selection.summary.omitted_category_count == 0
                and getattr(chart, "omitted_behavior", None) is not None
            ):
                raise ValueError(
                    "omitted_behavior is only valid when top_n omits eligible categories."
                )

    ratio_contract = (
        chart_ratio_contract(chart)
        if chart.intent in RATIO_INTENTS
        else None
    )
    if ratio_contract is not None:
        usermeta["ratio_contract"] = ratio_contract

    metric_definition_contract = (
        chart_metric_definition_contract(chart)
        if chart.intent in METRIC_DEFINITION_INTENTS
        else None
    )
    if metric_definition_contract is not None:
        usermeta["metric_definition_contract"] = metric_definition_contract

    directionality_raw = (
        chart_directionality_contract(chart)
        if chart.intent in DIRECTIONALITY_INTENTS
        else None
    )
    if directionality_raw is not None:
        usermeta["directionality_contract"] = parse_directionality_contract(
            {"usermeta": {"directionality_contract": directionality_raw}}
        )

    target_raw = (
        target_declaration(chart)
        if chart.intent in TARGET_INTENTS
        else None
    )
    if target_raw is not None:
        target_summary = build_target_summary(chart.data, **target_raw)
        usermeta["target_contract"] = target_summary.to_dict()

    reconciliation_raw = (
        chart_reconciliation_declaration(chart)
        if chart.intent in RECONCILIATION_INTENTS
        else None
    )
    if reconciliation_raw is not None:
        reconciliation_summary = build_reconciliation_summary(
            chart.data,
            **reconciliation_raw,
        )
        if not reconciliation_matches(reconciliation_summary):
            raise ValueError(
                "Component evidence does not reconcile to the declared control total "
                "within the declared tolerance."
            )
        usermeta["reconciliation_contract"] = reconciliation_summary.to_dict()

    population_raw = (
        chart_population_contract(chart)
        if chart.intent in POPULATION_INTENTS
        else None
    )
    if population_raw is not None:
        population_contract = parse_population_contract(
            {"usermeta": {"population_contract": population_raw}}
        )
        if population_contract["sample_member_field"] is not None:
            ok, message = sample_member_status(
                chart.data,
                member_field=population_contract["sample_member_field"],
                sample_size=population_contract["sample_size"],
            )
            if not ok:
                raise ValueError(message)
        if population_contract["weight_field"] is not None:
            ok, message = weight_status(
                chart.data,
                weight_field=population_contract["weight_field"],
            )
            if not ok:
                raise ValueError(message)
        usermeta["population_contract"] = population_contract

    unit_conversion_raw = (
        chart_unit_conversion_contract(chart)
        if chart.intent in UNIT_CONVERSION_INTENTS
        else None
    )
    if unit_conversion_raw is not None:
        unit_contract = parse_unit_conversion_contract(
            {"usermeta": {"unit_conversion_contract": unit_conversion_raw}}
        )
        if unit_contract["source_unit_basis_field"] is not None:
            ok, message = source_unit_basis_status(
                chart.data,
                basis_field=unit_contract["source_unit_basis_field"],
                source_unit=unit_contract["source_unit"],
            )
            if not ok:
                raise ValueError(message)
        if unit_contract["conversion_kind"] == "scale":
            ok, message = conversion_arithmetic_status(
                chart.data,
                metric_field=unit_contract["metric_field"],
                source_value_field=unit_contract["source_value_field"],
                conversion_factor=unit_contract["conversion_factor"],
            )
            if not ok:
                raise ValueError(message)
        usermeta["unit_conversion_contract"] = unit_contract

    uncertainty_raw = (
        chart_uncertainty_contract(chart)
        if chart.intent in UNCERTAINTY_INTENTS
        else None
    )
    if uncertainty_raw is not None:
        uncertainty_contract = parse_uncertainty_contract(
            {"usermeta": {"uncertainty_contract": uncertainty_raw}}
        )
        ok, message = interval_bounds_status(
            chart.data,
            estimate_field=uncertainty_contract["estimate_field"],
            lower_field=uncertainty_contract["lower_field"],
            upper_field=uncertainty_contract["upper_field"],
        )
        if not ok:
            raise ValueError(message)
        usermeta["uncertainty_contract"] = uncertainty_contract

    comparison_raw = (
        comparison_declaration(chart)
        if chart.intent in COMPARISON_INTENTS
        else None
    )
    if comparison_raw is not None:
        comparison_summary = build_comparison_summary(
            chart.data,
            **comparison_raw,
            unit=chart.unit,
            value_representation=chart.value_representation,
        )
        if not changes_match(
            comparison_summary.declared_change,
            comparison_summary.computed_change,
        ):
            raise ValueError(
                "Declared comparison change does not match the selected baseline/target evidence."
            )
        usermeta["comparison_contract"] = comparison_summary.to_dict()

    if chart.intent in GRAIN_INTENTS and getattr(chart, "grain_fields", None) is not None:
        usermeta["grain_contract"] = build_grain_summary(
            chart.data,
            source_grain_fields=chart.grain_fields,
            output_grain_fields=visible_grain_fields_for_chart(chart),
            aggregation=None,
        ).to_dict()

    time_window_raw = time_window_declaration(chart)
    if time_window_raw is not None:
        if comparison_raw is None:
            raise ValueError("Time-window metadata requires an explicit comparison baseline contract.")
        usermeta["time_window_contract"] = build_time_window_summary(
            **time_window_raw,
        ).to_dict()

    declared_transforms = list(first_party_transform_declaration(chart.intent))
    if rank_selection is not None and rank_selection.summary.omitted_category_count > 0:
        if (
            comparison_set_summary is not None
            and comparison_set_summary.omitted_behavior == "aggregate_other"
        ):
            for kind in ("aggregate", "calculate"):
                if kind not in declared_transforms:
                    declared_transforms.append(kind)
        elif "filter" not in declared_transforms:
            declared_transforms.append("filter")
    if declared_transforms:
        usermeta["transform_contract"] = {"declared": sorted(declared_transforms)}
    if chart.intent in {"qq", "ecdf", "residual", "set_membership", "process_tree"}:
        usermeta.setdefault("chart_contract_intent", chart.intent)
    if chart.intent == "qq":
        usermeta.setdefault("qq_reference_distribution", chart.distribution)
    if chart.intent == "set_membership":
        summary = membership_summary(chart.data, set_a=chart.set_a, set_b=chart.set_b)
        usermeta["chart_contract_intent"] = chart.intent
        usermeta["set_membership"] = {
            "member": chart.member,
            "set_a": chart.set_a,
            "set_b": chart.set_b,
            "set_a_label": chart.set_a_label or chart.set_a,
            "set_b_label": chart.set_b_label or chart.set_b,
            "area_semantics": "schematic; labeled region counts are authoritative",
            "region_counts": summary.to_dict(),
        }
    process_summary = None
    if chart.intent == "process_tree":
        process_summary = process_tree_summary(
            chart.data,
            node=chart.node,
            parent=chart.parent,
            label=chart.label,
            branch=chart.branch,
        )
        usermeta["chart_contract_intent"] = chart.intent
        usermeta["process_tree"] = {
            "node": chart.node,
            "parent": chart.parent,
            "label": chart.label,
            "branch": chart.branch,
            "layout": "deterministic top-down rooted tree; sibling order follows input row order",
            **process_summary.to_dict(),
        }
    for key, value in {
        "claim": chart.claim,
        "source": chart.source,
        "unit": chart.unit,
        "value_representation": chart.value_representation,
        "caveat": chart.caveat,
        "filters": chart.filters,
    }.items():
        if value not in (None, ""):
            usermeta[key] = value
    properties: dict[str, Any] = {
        "width": 760 if chart.intent == "process_tree" else 640,
        "height": (
            max(360, 120 * (process_summary.max_depth + 1))
            if process_summary is not None
            else 360
        ),
        "title": {
            "text": chart.title or chart.claim or "Chart",
            "subtitle": subtitle,
        },
        "usermeta": usermeta,
    }

    if chart.intent == "trend":
        rendered = _render_trend(chart, records)
    elif chart.intent == "rank":
        rendered = _render_rank(chart, records, rank_selection, comparison_set_summary)
    elif chart.intent == "compare":
        rendered = _render_compare(chart, records)
    elif chart.intent == "histogram":
        rendered = _render_histogram(chart, records)
    elif chart.intent == "boxplot":
        rendered = _render_boxplot(chart, records)
    elif chart.intent == "violin":
        rendered = _render_violin(chart, records)
    elif chart.intent == "qq":
        rendered = _render_qq(chart)
    elif chart.intent == "ecdf":
        rendered = _render_ecdf(chart)
    elif chart.intent == "residual":
        rendered = _render_residual(chart, records)
    elif chart.intent == "set_membership":
        rendered = _render_set_membership(chart)
    elif chart.intent == "process_tree":
        rendered = _render_process_tree(chart)
    else:
        raise ValueError(f"Unsupported chart intent: {chart.intent}")

    finalized = rendered.properties(**properties)
    lineage = build_transform_lineage(finalized.to_dict())
    if lineage["receipts"]:
        usermeta["transform_lineage"] = lineage
        finalized = finalized.properties(usermeta=usermeta)
    return finalized


def _render_trend(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    base = alt.Chart(alt.InlineData(values=records))
    x_series = chart.data[chart.x]
    if is_datetime_like(x_series):
        x_type = "T"
        tooltip_type = "temporal"
    elif is_numeric_series(x_series):
        x_type = "Q"
        tooltip_type = "quantitative"
    else:
        x_type = "O"
        tooltip_type = "nominal"
    line = base.mark_line(point=True).encode(
        x=alt.X(f"{chart.x}:{x_type}", title=chart.x.replace("_", " ").title()),
        y=alt.Y(f"{chart.y}:Q", title=_y_title(chart), **_metric_axis_kwargs(chart)),
        tooltip=[
            alt.Tooltip(field=chart.x, type=tooltip_type),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ],
    )

    interval = _render_interval_rule(
        chart,
        records,
        x_type=x_type,
        x_tooltip_type=tooltip_type,
    )
    target = _render_target_rule(chart)
    rendered = line
    if interval is not None:
        rendered = rendered + interval
    if target is not None:
        rendered = rendered + target

    if not chart.event:
        return rendered

    event_data = pd.DataFrame(
        [
            {
                chart.x: chart.event.get("x"),
                "label": chart.event.get("label", "Event"),
            }
        ]
    )
    event_records = _prepare_records(event_data)
    rule = alt.Chart(alt.InlineData(values=event_records)).mark_rule(color="#b03a2e", strokeDash=[4, 4]).encode(
        x=alt.X(f"{chart.x}:{x_type}")
    )
    text = (
        alt.Chart(alt.InlineData(values=event_records))
        .mark_text(color="#b03a2e", align="left", dx=6, dy=-6)
        .encode(x=alt.X(f"{chart.x}:{x_type}"), y=alt.value(12), text="label:N")
    )
    return rendered + rule + text


def _render_rank(
    chart: Any,
    records: list[dict[str, Any]],
    selection: RankSelection | None,
    comparison_set: ComparisonSetSummary | None,
) -> alt.Chart:
    base = alt.Chart(alt.InlineData(values=records))
    sort: Any = "-x"
    if selection is not None:
        sort = comparison_set_sort(selection, comparison_set)
        if selection.summary.omitted_category_count > 0:
            if comparison_set is not None and comparison_set.omitted_behavior == "aggregate_other":
                transforms = aggregate_other_transforms(
                    category_field=chart.x,
                    metric_field=chart.y,
                    selected_categories=selection.displayed_categories,
                    other_label=comparison_set.other_label or "Other",
                )
                base = base.transform_calculate(
                    **{chart.x: transforms[0]["calculate"]}
                ).transform_aggregate(
                    **{chart.y: f"sum({chart.y})"},
                    groupby=[chart.x],
                )
            else:
                base = base.transform_filter(
                    alt.FieldOneOfPredicate(
                        field=chart.x,
                        oneOf=list(selection.displayed_categories),
                    )
                )

    return base.mark_bar().encode(
        x=alt.X(
            f"{chart.y}:Q",
            title=_y_title(chart),
            scale=alt.Scale(zero=True),
            **_metric_axis_kwargs(chart),
        ),
        y=alt.Y(
            f"{chart.x}:N",
            title=chart.x.replace("_", " ").title(),
            sort=sort,
        ),
        tooltip=[
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ],
    )


def _render_compare(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    encoding: dict[str, Any] = {
        "x": alt.X(f"{chart.x}:N", title=chart.x.replace("_", " ").title()),
        "y": alt.Y(
            f"{chart.y}:Q",
            title=_y_title(chart),
            scale=alt.Scale(zero=True),
            **_metric_axis_kwargs(chart),
        ),
        "tooltip": [
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ],
    }
    if chart.group:
        encoding["xOffset"] = alt.XOffset(f"{chart.group}:N")
        encoding["color"] = alt.Color(f"{chart.group}:N")
        encoding["tooltip"] = [
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.group, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ]
    bars = alt.Chart(alt.InlineData(values=records)).mark_bar().encode(**encoding)
    interval = _render_interval_rule(
        chart,
        records,
        x_type="N",
        x_tooltip_type="nominal",
    )
    target = _render_target_rule(chart)
    rendered = bars
    if interval is not None:
        rendered = rendered + interval
    if target is not None:
        rendered = rendered + target
    return rendered


def _render_target_rule(chart: Any) -> alt.Chart | None:
    declaration = target_declaration(chart)
    if declaration is None:
        return None
    summary = build_target_summary(chart.data, **declaration)
    field = "__chart_contract_target__"
    values = [{field: summary.target_value}]
    return (
        alt.Chart(alt.InlineData(values=values))
        .mark_rule(strokeDash=[6, 4])
        .encode(y=alt.Y(f"{field}:Q"))
    )


def _render_interval_rule(
    chart: Any,
    records: list[dict[str, Any]],
    *,
    x_type: str,
    x_tooltip_type: str,
) -> alt.Chart | None:
    raw = chart_uncertainty_contract(chart)
    if raw is None:
        return None
    contract = parse_uncertainty_contract(
        {"usermeta": {"uncertainty_contract": raw}}
    )
    lower = contract["lower_field"]
    upper = contract["upper_field"]
    tooltip: list[Any] = [
        alt.Tooltip(field=chart.x, type=x_tooltip_type),
        alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        alt.Tooltip(field=lower, type="quantitative"),
        alt.Tooltip(field=upper, type="quantitative"),
    ]
    encoding: dict[str, Any] = {
        "x": alt.X(f"{chart.x}:{x_type}"),
        "y": alt.Y(f"{lower}:Q"),
        "y2": alt.Y2(f"{upper}:Q"),
        "tooltip": tooltip,
    }
    if chart.group:
        encoding["xOffset"] = alt.XOffset(f"{chart.group}:N")
        encoding["color"] = alt.Color(f"{chart.group}:N")
        tooltip.insert(1, alt.Tooltip(field=chart.group, type="nominal"))
    return alt.Chart(alt.InlineData(values=records)).mark_rule().encode(**encoding)


def _render_histogram(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    value_field = chart.value or chart.x or chart.y
    if not value_field:
        raise ValueError("Histogram charts require a value field.")

    bin_config: Any = True
    if isinstance(chart.bins, int):
        bin_config = alt.Bin(maxbins=chart.bins)

    encoding: dict[str, Any] = {
        "x": alt.X(
            f"{value_field}:Q",
            bin=bin_config,
            title=_metric_title(value_field, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        "y": alt.Y("count():Q", title="Count"),
        "tooltip": [
            alt.Tooltip(
                f"{value_field}:Q",
                bin=bin_config,
                title=_metric_title(value_field, chart.unit),
                **_metric_tooltip_kwargs(chart),
            ),
            alt.Tooltip("count():Q", title="Count"),
        ],
    }
    if chart.group:
        encoding["color"] = alt.Color(f"{chart.group}:N", title=chart.group.replace("_", " ").title())
        encoding["tooltip"] = [
            alt.Tooltip(
                f"{value_field}:Q",
                bin=bin_config,
                title=_metric_title(value_field, chart.unit),
                **_metric_tooltip_kwargs(chart),
            ),
            alt.Tooltip(field=chart.group, type="nominal"),
            alt.Tooltip("count():Q", title="Count"),
        ]
    return alt.Chart(alt.InlineData(values=records)).mark_bar().encode(**encoding)


def _render_boxplot(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    if not chart.y:
        raise ValueError("Boxplot charts require a y field.")

    category_field = chart.category or chart.x or chart.group
    group_field = chart.group if chart.group and chart.group != category_field else None
    working_records = records
    if category_field is None:
        category_field = "_distribution"
        working_records = _add_constant_field(working_records, category_field, "All observations")

    encoding: dict[str, Any] = {
        "x": alt.X(f"{category_field}:N", title=category_field.replace("_", " ").title()),
        "y": alt.Y(
            f"{chart.y}:Q",
            title=_metric_title(chart.y, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        "tooltip": [
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ],
    }
    if group_field:
        encoding["color"] = alt.Color(f"{group_field}:N", title=group_field.replace("_", " ").title())
        encoding["tooltip"] = [
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(field=group_field, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ]
    return alt.Chart(alt.InlineData(values=working_records)).mark_boxplot().encode(**encoding)


def _render_violin(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    if not chart.y:
        raise ValueError("Violin charts require a y field.")

    category_field = chart.category or chart.x or chart.group
    working_records = records
    if category_field is None:
        category_field = "_distribution"
        working_records = _add_constant_field(working_records, category_field, "All observations")

    density_groupby = [category_field]

    base = alt.Chart(alt.InlineData(values=working_records)).transform_density(
        chart.y,
        as_=["value", "density"],
        groupby=density_groupby,
    )
    violin = base.mark_area(orient="horizontal", opacity=0.6).encode(
        x=alt.X("density:Q", title="Density"),
        y=alt.Y(
            "value:Q",
            title=_metric_title(chart.y, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        color=alt.Color(f"{category_field}:N", title=category_field.replace("_", " ").title()),
        tooltip=[
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(
                field="value",
                type="quantitative",
                title=_metric_title(chart.y, chart.unit),
                **_metric_tooltip_kwargs(chart),
            ),
            alt.Tooltip("density:Q", title="Density"),
        ],
    )
    return violin


def _render_qq(chart: Any) -> alt.Chart:
    if not chart.value:
        raise ValueError("QQ charts require a value field.")
    point_records, reference_records = qq_records(
        chart.data,
        value=chart.value,
        group=chart.group,
        distribution=chart.distribution,
    )
    point_encoding: dict[str, Any] = {
        "x": alt.X(f"{QQ_THEORETICAL_FIELD}:Q", title="Theoretical normal quantile"),
        "y": alt.Y(
            f"{QQ_SAMPLE_FIELD}:Q",
            title=_metric_title(chart.value, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        "tooltip": [
            alt.Tooltip(f"{QQ_THEORETICAL_FIELD}:Q", title="Theoretical quantile"),
            alt.Tooltip(
                f"{QQ_SAMPLE_FIELD}:Q",
                title=_metric_title(chart.value, chart.unit),
                **_metric_tooltip_kwargs(chart),
            ),
        ],
    }
    line_encoding: dict[str, Any] = {
        "x": alt.X(f"{QQ_THEORETICAL_FIELD}:Q"),
        "y": alt.Y(f"{QQ_REFERENCE_FIELD}:Q"),
    }
    if chart.group:
        point_encoding["color"] = alt.Color(f"{chart.group}:N", title=chart.group.replace("_", " ").title())
        point_encoding["tooltip"] = [
            alt.Tooltip(field=chart.group, type="nominal"),
            *point_encoding["tooltip"],
        ]
        line_encoding["color"] = alt.Color(f"{chart.group}:N", legend=None)
        line_encoding["detail"] = alt.Detail(f"{chart.group}:N")

    points = alt.Chart(alt.InlineData(values=point_records)).mark_point(filled=True, size=55).encode(**point_encoding)
    reference = (
        alt.Chart(alt.InlineData(values=reference_records))
        .mark_line(strokeDash=[5, 4])
        .encode(**line_encoding)
    )
    return points + reference


def _render_ecdf(chart: Any) -> alt.Chart:
    if not chart.value:
        raise ValueError("ECDF charts require a value field.")
    records = ecdf_records(chart.data, value=chart.value, group=chart.group)
    encoding: dict[str, Any] = {
        "x": alt.X(
            f"{ECDF_VALUE_FIELD}:Q",
            title=_metric_title(chart.value, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        "y": alt.Y(
            f"{ECDF_PROBABILITY_FIELD}:Q",
            title="Cumulative probability",
            scale=alt.Scale(domain=[0, 1]),
            axis=alt.Axis(format=".0%"),
        ),
        "tooltip": [
            alt.Tooltip(
                f"{ECDF_VALUE_FIELD}:Q",
                title=_metric_title(chart.value, chart.unit),
                **_metric_tooltip_kwargs(chart),
            ),
            alt.Tooltip(f"{ECDF_PROBABILITY_FIELD}:Q", title="Cumulative probability", format=".1%"),
        ],
    }
    if chart.group:
        encoding["color"] = alt.Color(f"{chart.group}:N", title=chart.group.replace("_", " ").title())
        encoding["detail"] = alt.Detail(f"{chart.group}:N")
        encoding["tooltip"] = [alt.Tooltip(field=chart.group, type="nominal"), *encoding["tooltip"]]
    return alt.Chart(alt.InlineData(values=records)).mark_line(interpolate="step-after", point=True).encode(**encoding)


def _render_residual(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    if not chart.x or not chart.y:
        raise ValueError("Residual charts require fitted and residual fields.")
    encoding: dict[str, Any] = {
        "x": alt.X(f"{chart.x}:Q", title=chart.x.replace("_", " ").title()),
        "y": alt.Y(
            f"{chart.y}:Q",
            title=_metric_title(chart.y, chart.unit),
            **_metric_axis_kwargs(chart),
        ),
        "tooltip": [
            alt.Tooltip(field=chart.x, type="quantitative"),
            alt.Tooltip(field=chart.y, type="quantitative", **_metric_tooltip_kwargs(chart)),
        ],
    }
    if chart.group:
        encoding["color"] = alt.Color(f"{chart.group}:N", title=chart.group.replace("_", " ").title())
        encoding["tooltip"] = [alt.Tooltip(field=chart.group, type="nominal"), *encoding["tooltip"]]
    points = alt.Chart(alt.InlineData(values=records)).mark_point(filled=True, size=55).encode(**encoding)
    zero = (
        alt.Chart(alt.InlineData(values=[{}]))
        .mark_rule(strokeDash=[5, 4])
        .encode(y=alt.Y(datum=0, type="quantitative"))
    )
    return points + zero


def _render_set_membership(chart: Any) -> alt.Chart:
    if not chart.set_a or not chart.set_b:
        raise ValueError("Set membership charts require set_a and set_b fields.")
    summary = membership_summary(chart.data, set_a=chart.set_a, set_b=chart.set_b)
    set_a_label = chart.set_a_label or chart.set_a.replace("_", " ").title()
    set_b_label = chart.set_b_label or chart.set_b.replace("_", " ").title()
    circle_records, region_records, note_records = venn_layout_records(
        summary,
        set_a_label=set_a_label,
        set_b_label=set_b_label,
    )
    x_encoding = alt.X("x:Q", scale=alt.Scale(domain=[0, 100]), axis=None)
    y_encoding = alt.Y("y:Q", scale=alt.Scale(domain=[0, 100]), axis=None)

    circles = (
        alt.Chart(alt.InlineData(values=circle_records))
        .mark_circle(opacity=0.28, strokeWidth=2)
        .encode(
            x=x_encoding,
            y=y_encoding,
            size=alt.Size("size:Q", scale=None, legend=None),
            color=alt.Color("set_label:N", legend=None),
            tooltip=[
                alt.Tooltip("set_label:N", title="Set"),
                alt.Tooltip("members:Q", title="Members"),
            ],
        )
    )
    regions = (
        alt.Chart(alt.InlineData(values=region_records))
        .mark_text(fontSize=14, fontWeight="bold")
        .encode(x=x_encoding, y=y_encoding, text=alt.Text("label:N"))
    )
    notes = (
        alt.Chart(alt.InlineData(values=note_records))
        .mark_text(fontSize=12)
        .encode(x=x_encoding, y=y_encoding, text=alt.Text("label:N"))
    )
    return circles + regions + notes


def _render_process_tree(chart: Any) -> alt.Chart:
    if not chart.node or not chart.parent or not chart.label:
        raise ValueError("Process-tree charts require node, parent, and label fields.")

    node_records, connector_records, arrow_records, branch_records = process_tree_layout_records(
        chart.data,
        node=chart.node,
        parent=chart.parent,
        label=chart.label,
        branch=chart.branch,
    )
    x_scale = alt.Scale(domain=[0, 100])
    y_scale = alt.Scale(domain=[0, 100], reverse=True)

    connectors = (
        alt.Chart(alt.InlineData(values=connector_records))
        .mark_line(strokeWidth=1.5, color="#6b7280")
        .encode(
            x=alt.X("x:Q", scale=x_scale, axis=None),
            y=alt.Y("y:Q", scale=y_scale, axis=None),
            detail=alt.Detail("edge_id:N"),
            order=alt.Order("order:Q"),
        )
    )
    arrows = (
        alt.Chart(alt.InlineData(values=arrow_records))
        .mark_point(shape="triangle-down", filled=True, size=85, color="#6b7280")
        .encode(
            x=alt.X("x:Q", scale=x_scale, axis=None),
            y=alt.Y("y:Q", scale=y_scale, axis=None),
        )
    )
    boxes = (
        alt.Chart(alt.InlineData(values=node_records))
        .mark_rect(cornerRadius=8, strokeWidth=1.5, fill="#f8fafc", stroke="#475569")
        .encode(
            x=alt.X("x1:Q", scale=x_scale, axis=None),
            x2=alt.X2("x2:Q"),
            y=alt.Y("y1:Q", scale=y_scale, axis=None),
            y2=alt.Y2("y2:Q"),
            tooltip=[
                alt.Tooltip("node_id:N", title="Node"),
                alt.Tooltip("label:N", title="Step"),
            ],
        )
    )
    labels = (
        alt.Chart(alt.InlineData(values=node_records))
        .mark_text(fontSize=13, fontWeight="bold", limit=170, color="#0f172a")
        .encode(
            x=alt.X("x:Q", scale=x_scale, axis=None),
            y=alt.Y("y:Q", scale=y_scale, axis=None),
            text=alt.Text("label:N"),
        )
    )
    rendered = connectors + arrows + boxes + labels

    if branch_records:
        branches = (
            alt.Chart(alt.InlineData(values=branch_records))
            .mark_text(fontSize=11, dy=-7, color="#475569")
            .encode(
                x=alt.X("x:Q", scale=x_scale, axis=None),
                y=alt.Y("y:Q", scale=y_scale, axis=None),
                text=alt.Text("label:N"),
            )
        )
        rendered = rendered + branches
    return rendered


def _metric_axis_kwargs(chart: Any) -> dict[str, Any]:
    representation = (
        chart.value_representation.strip().lower()
        if isinstance(chart.value_representation, str)
        else None
    )
    if is_percent_unit(chart.unit) and representation == "fraction":
        return {"axis": alt.Axis(format=".1%")}
    return {}


def _metric_tooltip_kwargs(chart: Any) -> dict[str, Any]:
    representation = (
        chart.value_representation.strip().lower()
        if isinstance(chart.value_representation, str)
        else None
    )
    if is_percent_unit(chart.unit) and representation == "fraction":
        return {"format": ".1%"}
    return {}


def _metric_title(field_name: str | None, unit: str | None) -> str:
    base = (field_name or "").replace("_", " ").title()
    return f"{base} ({unit})" if unit else base


def _y_title(chart: Any) -> str:
    return _metric_title(chart.y, chart.unit)


def _add_constant_field(records: list[dict[str, Any]], field: str, value: Any) -> list[dict[str, Any]]:
    return [{**record, field: value} for record in records]


def _prepare_records(data: pd.DataFrame) -> list[dict[str, Any]]:
    prepared = data.copy()
    string_columns = prepared.select_dtypes(include=["string"]).columns
    if len(string_columns) > 0:
        prepared = prepared.astype({column: object for column in string_columns})
    return prepared.to_dict(orient="records")
