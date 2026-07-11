from __future__ import annotations

import pandas as pd

from chart_contract import Chart, audit_spec
from chart_contract.contracts import find_decorative_terms


def severities(report):
    return {finding.rule_id: finding.severity for finding in report.findings}


def test_spec_missing_encoded_fields_blocks() -> None:
    spec = {
        "mark": "bar",
        "title": "Revenue by segment",
        "encoding": {
            "x": {"field": "revenue", "type": "quantitative"},
            "y": {"field": "segment", "type": "nominal"},
        },
        "usermeta": {"source": "warehouse.revenue", "unit": "dollars"},
    }

    report = audit_spec(spec, data=pd.DataFrame({"other": [1, 2]}), claim="Revenue differs by segment.")

    assert report.verdict == "BLOCK"
    assert severities(report)["data.encoding.fields"] == "FAIL"


def test_spec_quantitative_encoding_requires_numeric_data() -> None:
    spec = {
        "mark": "bar",
        "title": "Revenue by segment",
        "encoding": {"x": "revenue:Q", "y": "segment:N"},
        "usermeta": {"source": "warehouse.revenue", "unit": "dollars"},
    }

    report = audit_spec(
        spec,
        data=pd.DataFrame({"revenue": ["high", "low"], "segment": ["A", "B"]}),
        claim="Revenue differs by segment.",
    )

    assert report.verdict == "BLOCK"
    assert severities(report)["data.encoding.quantitative"] == "FAIL"


def test_shorthand_arc_category_limit_is_enforced() -> None:
    spec = {
        "mark": "arc",
        "title": "Segment share",
        "encoding": {"theta": "value:Q", "color": "segment:N"},
        "usermeta": {"source": "warehouse.share", "unit": "count"},
    }
    frame = pd.DataFrame({"segment": list("ABCDEFG"), "value": [1] * 7})

    report = audit_spec(spec, data=frame, claim="Share differs across segments.")

    assert report.verdict == "BLOCK"
    assert severities(report)["visual.arc.category_count"] == "FAIL"


def test_chart_trend_counts_only_complete_points() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"week": [1, 2], "value": [0.1, None]}),
        x="week",
        y="value",
        claim="Conversion increased.",
        source="warehouse.funnel",
        unit="rate",
        title="Weekly conversion rate",
    )

    report = chart.audit()

    assert report.verdict == "BLOCK"
    assert severities(report)["data.trend.min_points"] == "FAIL"


def test_layered_trend_spec_counts_only_complete_points() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"week": ["2026-01-01", None], "value": [0.1, None]}),
        x="week",
        y="value",
        claim="Conversion changed after launch.",
        source="warehouse.funnel",
        unit="rate",
        title="Weekly conversion rate",
        event={"x": "2026-01-01", "label": "Launch"},
        caveat="Descriptive timing only.",
    )

    report = audit_spec(chart.to_vega_lite(), data=chart.data, claim=chart.claim)

    assert report.verdict == "BLOCK"
    assert severities(report)["data.trend.min_points"] == "FAIL"
    assert severities(report)["contract.source.present"] == "PASS"
    assert severities(report)["labels.unit.present"] == "PASS"


def test_distribution_sample_size_ignores_null_metric_rows() -> None:
    chart = Chart.histogram(
        data=pd.DataFrame({"amount": [1.0] + [None] * 19}),
        value="amount",
        claim="Amounts span the observed range.",
        source="warehouse.amounts",
        unit="dollars",
        title="Amount distribution",
    )

    report = chart.audit()

    assert report.verdict == "BLOCK"
    assert severities(report)["data.distribution.sample_size"] == "FAIL"


def test_unknown_chart_intent_blocks_before_rendering() -> None:
    chart = Chart(
        intent="pie",
        data=pd.DataFrame({"segment": ["A"], "value": [1]}),
        x="segment",
        y="value",
        claim="A is the largest segment.",
        source="warehouse.share",
        unit="count",
        title="Segment share",
    )

    report = chart.audit()

    assert report.verdict == "BLOCK"
    assert severities(report)["visual.intent.match"] == "FAIL"


def test_numeric_trend_x_uses_quantitative_encoding() -> None:
    spec = Chart.trend(
        data=pd.DataFrame({"elapsed_days": [0, 1, 100], "value": [1, 2, 3]}),
        x="elapsed_days",
        y="value",
        claim="Value increases over elapsed time.",
        source="warehouse.metric",
        unit="count",
        title="Value by elapsed day",
    ).to_vega_lite()

    assert spec["encoding"]["x"]["type"] == "quantitative"
    assert spec["encoding"]["tooltip"][0]["type"] == "quantitative"


def test_generated_spec_preserves_audit_metadata() -> None:
    spec = Chart.histogram(
        data=pd.DataFrame({"amount": list(range(20))}),
        value="amount",
        claim="Amounts span the observed range.",
        source="warehouse.amounts",
        unit="dollars",
        title="Amount distribution",
        caveat="Synthetic example.",
        filters={"region": "US"},
    ).to_vega_lite()

    assert spec["usermeta"] == {
        "source": "warehouse.amounts",
        "unit": "dollars",
        "caveat": "Synthetic example.",
        "filters": {"region": "US"},
    }


def test_dataset_hash_and_provenance_do_not_trigger_decorative_warning() -> None:
    payload = {
        "datasets": {"data-abc3def": [{"value": 1}]},
        "usermeta": {"source": "warehouse.image_events", "caveat": "No 3D rendering."},
        "mark": "line",
    }

    assert find_decorative_terms(payload) == []


def test_actual_decorative_metadata_is_still_detected() -> None:
    payload = {
        "config": {
            "backgroundImage": "texture.png",
            "drop-shadow": True,
            "renderMode": "3D",
        }
    }

    assert find_decorative_terms(payload) == ["3d", "background", "image", "shadow", "texture"]
