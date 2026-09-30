from __future__ import annotations

import pandas as pd

from chart_contract import Chart, audit_spec


def _severity(report, rule_id: str) -> str:
    return next(finding.severity for finding in report.findings if finding.rule_id == rule_id)


def _trend(*, representation: str | None) -> Chart:
    return Chart.trend(
        data=pd.DataFrame(
            {
                "week": ["W1", "W2"],
                "conversion": [0.42, 0.47],
            }
        ),
        x="week",
        y="conversion",
        claim="Observed conversion increased across the two measurements.",
        source="synthetic.funnel",
        unit="percent",
        value_representation=representation,
        title="Observed conversion comparison",
    )


def test_fractional_percent_contract_is_ready() -> None:
    report = _trend(representation="fraction").audit()

    assert _severity(report, "labels.percent.representation") == "PASS"
    assert report.verdict == "READY"


def test_missing_percent_representation_requires_review() -> None:
    report = _trend(representation=None).audit()

    assert _severity(report, "labels.percent.representation") == "WARN"
    assert report.verdict == "REVIEW"


def test_invalid_percent_representation_blocks() -> None:
    report = _trend(representation="auto").audit()

    assert _severity(report, "labels.percent.representation") == "FAIL"
    assert report.verdict == "BLOCK"


def test_representation_without_percent_unit_blocks() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"week": ["W1", "W2"], "rate": [0.42, 0.47]}),
        x="week",
        y="rate",
        claim="Observed rate increased across the two measurements.",
        source="synthetic.funnel",
        unit="rate",
        value_representation="fraction",
        title="Observed rate comparison",
    )

    report = chart.audit()

    assert _severity(report, "labels.percent.representation") == "FAIL"


def test_first_party_fraction_rendering_formats_percent_without_rescaling_data() -> None:
    chart = _trend(representation="fraction")
    before = chart.data.copy(deep=True)

    spec = chart.to_vega_lite()

    pd.testing.assert_frame_equal(chart.data, before)
    assert spec["usermeta"]["unit"] == "percent"
    assert spec["usermeta"]["value_representation"] == "fraction"
    assert spec["encoding"]["y"]["axis"]["format"] == ".1%"
    assert spec["encoding"]["tooltip"][1]["format"] == ".1%"


def test_first_party_percentage_points_preserve_raw_scale() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"week": ["W1", "W2"], "conversion": [42.0, 47.0]}),
        x="week",
        y="conversion",
        claim="Observed conversion increased across the two measurements.",
        source="synthetic.funnel",
        unit="percent",
        value_representation="percentage_points",
        title="Observed conversion comparison",
    )

    spec = chart.to_vega_lite()

    assert spec["usermeta"]["value_representation"] == "percentage_points"
    assert "axis" not in spec["encoding"]["y"] or "format" not in spec["encoding"]["y"]["axis"]


def test_external_fraction_spec_without_percent_format_warns() -> None:
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "conversion", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.funnel",
            "unit": "percent",
            "value_representation": "fraction",
        },
    }
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [0.42, 0.47]})

    report = audit_spec(spec=spec, data=data, claim="Observed conversion increased.")

    assert _severity(report, "labels.percent.representation") == "PASS"
    assert _severity(report, "labels.percent.format") == "WARN"


def test_external_percentage_points_with_fraction_scaling_formatter_blocks() -> None:
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {
                "field": "conversion",
                "type": "quantitative",
                "axis": {"format": ".1%"},
            },
        },
        "usermeta": {
            "source": "synthetic.funnel",
            "unit": "percent",
            "value_representation": "percentage_points",
        },
    }
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [42.0, 47.0]})

    report = audit_spec(spec=spec, data=data, claim="Observed conversion increased.")

    assert _severity(report, "labels.percent.representation") == "PASS"
    assert _severity(report, "labels.percent.format") == "FAIL"
    assert report.verdict == "BLOCK"


def test_percent_formatted_external_spec_without_representation_warns() -> None:
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {
                "field": "conversion",
                "type": "quantitative",
                "axis": {"format": ".0%"},
            },
        },
        "usermeta": {"source": "synthetic.funnel"},
    }
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [0.42, 0.47]})

    report = audit_spec(spec=spec, data=data, claim="Observed conversion increased.")

    assert _severity(report, "labels.percent.representation") == "WARN"


def test_malformed_external_representation_blocks() -> None:
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "conversion", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.funnel",
            "unit": "percent",
            "value_representation": 100,
        },
    }
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [0.42, 0.47]})

    report = audit_spec(spec=spec, data=data, claim="Observed conversion increased.")

    assert _severity(report, "labels.percent.representation") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_percentage_points_without_fraction_formatter_passes_format_rule() -> None:
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "conversion", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.funnel",
            "unit": "percent",
            "value_representation": "percentage_points",
        },
    }
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [42.0, 47.0]})

    report = audit_spec(spec=spec, data=data, claim="Observed conversion increased.")

    assert _severity(report, "labels.percent.representation") == "PASS"
    assert _severity(report, "labels.percent.format") == "PASS"
