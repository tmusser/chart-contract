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


def _y_title(chart: Any) -> str:
    base = chart.y.replace("_", " ").title()
    return f"{base} ({chart.unit})" if chart.unit else base


def _prepare_records(data: pd.DataFrame) -> list[dict[str, Any]]:
    prepared = data.copy()
    string_columns = prepared.select_dtypes(include=["string"]).columns
    if len(string_columns) > 0:
        prepared = prepared.astype({column: object for column in string_columns})
    return prepared.to_dict(orient="records")
