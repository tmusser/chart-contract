"""Altair renderer helpers."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd

from ..contracts import is_datetime_like


def render_chart(chart: Any) -> alt.Chart:
    records = _prepare_records(chart.data)
    subtitle = []
    if chart.source:
        subtitle.append(f"Source: {chart.source}")
    if chart.caveat:
        subtitle.append(f"Caveat: {chart.caveat}")
    if chart.filters:
        subtitle.append(f"Filters: {chart.filters}")

    properties: dict[str, Any] = {
        "width": 640,
        "height": 360,
        "title": {
            "text": chart.title or chart.claim or "Chart",
            "subtitle": subtitle,
        },
    }

    if chart.intent == "trend":
        rendered = _render_trend(chart, records)
    elif chart.intent == "rank":
        rendered = _render_rank(chart, records)
    elif chart.intent == "compare":
        rendered = _render_compare(chart, records)
    elif chart.intent == "histogram":
        rendered = _render_histogram(chart, records)
    elif chart.intent == "boxplot":
        rendered = _render_boxplot(chart, records)
    elif chart.intent == "violin":
        rendered = _render_violin(chart, records)
    else:
        raise ValueError(f"Unsupported chart intent: {chart.intent}")

    return rendered.properties(**properties)


def _render_trend(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    base = alt.Chart(alt.InlineData(values=records))
    x_type = "T" if is_datetime_like(chart.data[chart.x]) else "O"
    line = base.mark_line(point=True).encode(
        x=alt.X(f"{chart.x}:{x_type}", title=chart.x.replace("_", " ").title()),
        y=alt.Y(f"{chart.y}:Q", title=_y_title(chart)),
        tooltip=[
            alt.Tooltip(field=chart.x, type="temporal" if x_type == "T" else "nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
        ],
    )

    if not chart.event:
        return line

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
    return line + rule + text


def _render_rank(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    return alt.Chart(alt.InlineData(values=records)).mark_bar().encode(
        x=alt.X(f"{chart.y}:Q", title=_y_title(chart), scale=alt.Scale(zero=True)),
        y=alt.Y(f"{chart.x}:N", title=chart.x.replace("_", " ").title(), sort="-x"),
        tooltip=[
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
        ],
    )


def _render_compare(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    encoding: dict[str, Any] = {
        "x": alt.X(f"{chart.x}:N", title=chart.x.replace("_", " ").title()),
        "y": alt.Y(f"{chart.y}:Q", title=_y_title(chart), scale=alt.Scale(zero=True)),
        "tooltip": [
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
        ],
    }
    if chart.group:
        encoding["xOffset"] = alt.XOffset(f"{chart.group}:N")
        encoding["color"] = alt.Color(f"{chart.group}:N")
        encoding["tooltip"] = [
            alt.Tooltip(field=chart.x, type="nominal"),
            alt.Tooltip(field=chart.group, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
        ]
    return alt.Chart(alt.InlineData(values=records)).mark_bar().encode(**encoding)


def _render_histogram(chart: Any, records: list[dict[str, Any]]) -> alt.Chart:
    value_field = chart.value or chart.x or chart.y
    if not value_field:
        raise ValueError("Histogram charts require a value field.")

    bin_config: Any = True
    if isinstance(chart.bins, int):
        bin_config = alt.Bin(maxbins=chart.bins)

    encoding: dict[str, Any] = {
        "x": alt.X(f"{value_field}:Q", bin=bin_config, title=_metric_title(value_field, chart.unit)),
        "y": alt.Y("count():Q", title="Count"),
        "tooltip": [
            alt.Tooltip(f"{value_field}:Q", bin=bin_config, title=_metric_title(value_field, chart.unit)),
            alt.Tooltip("count():Q", title="Count"),
        ],
    }
    if chart.group:
        encoding["color"] = alt.Color(f"{chart.group}:N", title=chart.group.replace("_", " ").title())
        encoding["tooltip"] = [
            alt.Tooltip(f"{value_field}:Q", bin=bin_config, title=_metric_title(value_field, chart.unit)),
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
        "y": alt.Y(f"{chart.y}:Q", title=_metric_title(chart.y, chart.unit)),
        "tooltip": [
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
        ],
    }
    if group_field:
        encoding["color"] = alt.Color(f"{group_field}:N", title=group_field.replace("_", " ").title())
        encoding["tooltip"] = [
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(field=group_field, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
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
        y=alt.Y("value:Q", title=_metric_title(chart.y, chart.unit)),
        color=alt.Color(f"{category_field}:N", title=category_field.replace("_", " ").title()),
        tooltip=[
            alt.Tooltip(field=category_field, type="nominal"),
            alt.Tooltip(field=chart.y, type="quantitative"),
            alt.Tooltip("density:Q", title="Density"),
        ],
    )
    return violin


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
