import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart, audit_spec

TRAPS = Path(__file__).resolve().parent.parent / "examples" / "traps"


def test_bar_chart_nonzero_baseline_fails() -> None:
    spec = {
        "mark": "bar",
        "title": "Revenue by segment",
        "encoding": {
            "x": {"field": "revenue", "type": "quantitative", "scale": {"zero": False}},
            "y": {"field": "segment", "type": "nominal"},
        },
        "usermeta": {"source": "warehouse.revenue", "unit": "dollars"},
    }

    report = audit_spec(spec=spec, claim="Revenue increased after repricing.")

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["scale.bar.nonzero_baseline"] == "FAIL"


def test_pie_chart_with_too_many_categories_fails() -> None:
    df = pd.DataFrame(
        {
            "segment": ["A", "B", "C", "D", "E", "F", "G"],
            "value": [10, 9, 8, 7, 6, 5, 4],
        }
    )
    spec = {
        "mark": {"type": "arc"},
        "title": "Chart",
        "encoding": {
            "theta": {"field": "value", "type": "quantitative"},
            "color": {"field": "segment", "type": "nominal"},
        },
    }

    report = audit_spec(
        spec=spec,
        data=df,
        claim="The launch caused a lift across customer segments.",
    )

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["visual.arc.category_count"] == "FAIL"


def test_single_point_line_trend_fails() -> None:
    spec = json.loads((TRAPS / "single_point_trend.vl.json").read_text(encoding="utf-8"))
    data = pd.read_csv(TRAPS / "single_point_trend.csv")

    report = audit_spec(
        spec=spec,
        data=data,
        claim=(TRAPS / "single_point_trend.claim.txt").read_text(encoding="utf-8").strip(),
    )

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert report.verdict == "BLOCK"
    assert severities["data.trend.min_points"] == "FAIL"


def test_two_point_line_trend_passes_min_points() -> None:
    spec = json.loads((TRAPS / "causal_claim_missing_caveat.vl.json").read_text(encoding="utf-8"))
    data = pd.read_csv(TRAPS / "causal_claim_missing_caveat.csv")

    report = audit_spec(
        spec=spec,
        data=data,
        claim=(TRAPS / "causal_claim_missing_caveat.claim.txt").read_text(encoding="utf-8").strip(),
    )

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.trend.min_points"] == "PASS"


def test_histogram_spec_audit_preserves_distribution_contract() -> None:
    df = pd.DataFrame(
        {
            "amount": list(range(20)),
            "segment": ["A"] * 10 + ["B"] * 10,
        }
    )

    spec = Chart.histogram(
        data=df,
        value="amount",
        claim="The amount distribution is spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
        title="Amount distribution by segment",
        bins=12,
        group="segment",
    ).to_vega_lite()

    report = audit_spec(
        spec=spec,
        data=df,
        claim="The amount distribution is spread across the observed range.",
    )

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert report.verdict == "READY"
    assert severities["contract.source.present"] == "PASS"
    assert severities["labels.unit.present"] == "PASS"
    assert severities["data.encoding.fields"] == "PASS"
    assert severities["data.encoding.quantitative"] == "PASS"
    assert severities["data.distribution.value.numeric"] == "PASS"
    assert severities["data.distribution.sample_size"] == "PASS"
    assert severities["data.distribution.group_sample_size"] == "PASS"
    assert severities["readability.histogram.bins"] == "PASS"
