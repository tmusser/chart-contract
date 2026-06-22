import json
from pathlib import Path

import pandas as pd

from chart_contract import audit_spec

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
