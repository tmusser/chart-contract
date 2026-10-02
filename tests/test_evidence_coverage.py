from __future__ import annotations

import math

import pandas as pd

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(finding for finding in report.findings if finding.rule_id == rule_id)


def _trend(values: list[float | None]) -> Chart:
    return Chart.trend(
        data=pd.DataFrame(
            {
                "period": list(range(len(values))),
                "value": values,
            }
        ),
        x="period",
        y="value",
        claim="Observed values changed across the measured periods.",
        source="synthetic.coverage",
        unit="count",
        title="Observed value trend",
    )


def test_chart_coverage_passes_at_ninety_percent() -> None:
    chart = _trend([1, 2, 3, 4, 5, 6, 7, 8, 9, None])

    report = chart.audit()
    finding = _finding(report, "data.coverage.usable_rows")

    assert finding.severity == "PASS"
    assert "9 / 10 rows (90.0%)" in finding.message


def test_chart_coverage_warns_below_ninety_percent() -> None:
    chart = _trend([1, 2, 3, 4, 5, 6, 7, 8, None, None])

    report = chart.audit()
    finding = _finding(report, "data.coverage.usable_rows")

    assert finding.severity == "WARN"
    assert report.verdict == "REVIEW"
    assert "8 / 10 rows (80.0%)" in finding.message


def test_chart_coverage_blocks_below_half() -> None:
    chart = _trend([1, 2, 3, 4, None, None, None, None, None, None])

    report = chart.audit()
    finding = _finding(report, "data.coverage.usable_rows")

    assert finding.severity == "FAIL"
    assert report.verdict == "BLOCK"
    assert "4 / 10 rows (40.0%)" in finding.message


def test_chart_coverage_half_is_review_not_block() -> None:
    chart = _trend([1, 2, 3, 4, 5, None, None, None, None, None])

    report = chart.audit()

    assert _finding(report, "data.coverage.usable_rows").severity == "WARN"


def test_group_coverage_warns_on_twenty_point_gap() -> None:
    frame = pd.DataFrame(
        {
            "period": list(range(10)) * 2,
            "segment": ["A"] * 10 + ["B"] * 10,
            "value": list(range(10)) + list(range(8)) + [None, None],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="period",
        y="value",
        group="segment",
        claim="Observed values differ by segment.",
        source="synthetic.coverage",
        unit="count",
        title="Observed values by segment",
    )

    report = chart.audit()
    overall = _finding(report, "data.coverage.usable_rows")
    grouped = _finding(report, "data.coverage.group_balance")

    assert overall.severity == "PASS"
    assert "18 / 20 rows (90.0%)" in overall.message
    assert grouped.severity == "WARN"
    assert "80.0%-100.0%" in grouped.message
    assert "20.0% gap" in grouped.message


def test_group_coverage_passes_when_missingness_is_balanced() -> None:
    frame = pd.DataFrame(
        {
            "period": list(range(10)) * 2,
            "segment": ["A"] * 10 + ["B"] * 10,
            "value": list(range(9)) + [None] + list(range(9)) + [None],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="period",
        y="value",
        group="segment",
        claim="Observed values differ by segment.",
        source="synthetic.coverage",
        unit="count",
        title="Observed values by segment",
    )

    report = chart.audit()

    assert _finding(report, "data.coverage.usable_rows").severity == "PASS"
    assert _finding(report, "data.coverage.group_balance").severity == "PASS"


def test_group_coverage_skips_tiny_groups() -> None:
    frame = pd.DataFrame(
        {
            "period": list(range(4)) + list(range(10)),
            "segment": ["tiny"] * 4 + ["large"] * 10,
            "value": [1, None, None, None] + list(range(10)),
        }
    )
    chart = Chart.compare(
        data=frame,
        x="period",
        y="value",
        group="segment",
        claim="Observed values differ by segment.",
        source="synthetic.coverage",
        unit="count",
        title="Observed values by segment",
    )

    report = chart.audit()

    assert not any(
        finding.rule_id == "data.coverage.group_balance"
        for finding in report.findings
    )


def test_spec_coverage_uses_visible_analytical_fields_not_tooltip_only() -> None:
    spec = {
        "mark": "line",
        "title": "Observed value trend",
        "encoding": {
            "x": {"field": "period", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "tooltip": [
                {"field": "note", "type": "nominal"},
            ],
        },
        "usermeta": {
            "source": "synthetic.coverage",
            "unit": "count",
        },
    }
    frame = pd.DataFrame(
        {
            "period": list(range(10)),
            "value": list(range(8)) + [None, None],
            "note": [None] * 10,
        }
    )

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Observed values changed across the measured periods.",
    )
    finding = _finding(report, "data.coverage.usable_rows")

    assert finding.severity == "WARN"
    assert "8 / 10 rows (80.0%)" in finding.message
    assert finding.field == "period, value"


def test_spec_group_coverage_uses_color_group() -> None:
    spec = {
        "mark": "line",
        "title": "Observed value trend by segment",
        "encoding": {
            "x": {"field": "period", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "segment", "type": "nominal"},
        },
        "usermeta": {
            "source": "synthetic.coverage",
            "unit": "count",
        },
    }
    frame = pd.DataFrame(
        {
            "period": list(range(10)) * 2,
            "segment": ["A"] * 10 + ["B"] * 10,
            "value": list(range(10)) + list(range(8)) + [None, None],
        }
    )

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Observed values differ by segment.",
    )

    assert _finding(report, "data.coverage.usable_rows").severity == "PASS"
    assert _finding(report, "data.coverage.group_balance").severity == "WARN"


def test_spec_coverage_does_not_duplicate_missing_field_failure() -> None:
    spec = {
        "mark": "line",
        "title": "Observed value trend",
        "encoding": {
            "x": {"field": "period", "type": "quantitative"},
            "y": {"field": "derived_value", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.coverage",
            "unit": "count",
        },
    }
    frame = pd.DataFrame({"period": list(range(10)), "value": list(range(10))})

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Observed values changed across the measured periods.",
    )

    assert _finding(report, "data.encoding.fields").severity == "FAIL"
    assert not any(
        finding.rule_id == "data.coverage.usable_rows"
        for finding in report.findings
    )


def test_inf_is_not_treated_as_missing_by_coverage_contract() -> None:
    chart = _trend([1, 2, 3, 4, 5, 6, 7, 8, math.inf, 10])

    report = chart.audit()

    assert _finding(report, "data.coverage.usable_rows").severity == "PASS"
