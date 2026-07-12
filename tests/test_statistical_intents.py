from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.statistics import (
    ECDF_PROBABILITY_FIELD,
    QQ_REFERENCE_FIELD,
    QQ_SAMPLE_FIELD,
    QQ_THEORETICAL_FIELD,
    ecdf_records,
    qq_records,
)


def _severities(report):
    return {finding.rule_id: finding.severity for finding in report.findings}


def _qq_spec(*, include_reference: bool = True) -> dict:
    layers = [
        {
            "mark": {"type": "point"},
            "encoding": {
                "x": {"field": QQ_THEORETICAL_FIELD, "type": "quantitative"},
                "y": {"field": QQ_SAMPLE_FIELD, "type": "quantitative"},
            },
        }
    ]
    if include_reference:
        layers.append(
            {
                "mark": {"type": "line", "strokeDash": [5, 4]},
                "encoding": {
                    "x": {"field": QQ_THEORETICAL_FIELD, "type": "quantitative"},
                    "y": {"field": QQ_REFERENCE_FIELD, "type": "quantitative"},
                },
            }
        )
    return {
        "title": "Normal QQ diagnostic",
        "usermeta": {
            "source": "synthetic.qq",
            "unit": "standardized value",
            "chart_contract_intent": "qq",
            "qq_reference_distribution": "normal",
        },
        "layer": layers,
    }


def _residual_spec(*, include_zero_rule: bool = True) -> dict:
    layers = [
        {
            "mark": {"type": "point"},
            "encoding": {
                "x": {"field": "fitted", "type": "quantitative"},
                "y": {"field": "residual", "type": "quantitative"},
            },
        }
    ]
    if include_zero_rule:
        layers.append(
            {
                "mark": {"type": "rule", "strokeDash": [5, 4]},
                "encoding": {"y": {"datum": 0, "type": "quantitative"}},
            }
        )
    return {
        "title": "Residual diagnostic",
        "usermeta": {
            "source": "synthetic.model",
            "unit": "dollars",
            "chart_contract_intent": "residual",
        },
        "layer": layers,
    }


def test_qq_chart_renders_points_and_fitted_reference_line() -> None:
    chart = Chart.qq(
        data=pd.DataFrame({"amount": list(range(1, 21))}),
        value="amount",
        claim="Observed quantiles are close to a normal reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="Normal QQ plot",
    )

    spec = chart.to_vega_lite()

    assert chart.intent == "qq"
    assert spec["layer"][0]["mark"]["type"] == "point"
    assert spec["layer"][0]["encoding"]["x"]["field"] == QQ_THEORETICAL_FIELD
    assert spec["layer"][0]["encoding"]["y"]["field"] == QQ_SAMPLE_FIELD
    assert spec["layer"][1]["mark"]["type"] == "line"
    assert spec["layer"][1]["encoding"]["y"]["field"] == QQ_REFERENCE_FIELD


def test_grouped_qq_records_keep_group_identity() -> None:
    frame = pd.DataFrame({"segment": ["A"] * 3 + ["B"] * 3, "amount": [1, 2, 3, 10, 11, 12]})

    points, reference = qq_records(frame, value="amount", group="segment")

    assert {row["segment"] for row in points} == {"A", "B"}
    assert len(reference) == 4


def test_qq_audit_rejects_unsupported_reference_distribution() -> None:
    report = Chart.qq(
        data=pd.DataFrame({"amount": list(range(20))}),
        value="amount",
        distribution="lognormal",
        claim="Observed quantiles match the chosen reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="QQ plot",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["stat.qq.reference_distribution"] == "FAIL"
    assert _severities(report)["visual.qq.reference_line"] == "FAIL"


def test_qq_audit_has_reference_line_contract() -> None:
    report = Chart.qq(
        data=pd.DataFrame({"amount": list(range(1, 21))}),
        value="amount",
        claim="Observed quantiles broadly track a normal reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="QQ plot",
    ).audit()

    assert _severities(report)["visual.qq.reference_line"] == "PASS"


def test_qq_audit_warns_when_ties_dominate() -> None:
    report = Chart.qq(
        data=pd.DataFrame({"amount": [1] * 12 + [2] * 12}),
        value="amount",
        claim="Observed quantiles are compared with a normal reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="QQ plot",
    ).audit()

    assert _severities(report)["stat.qq.tie_density"] == "WARN"


def test_qq_audit_warns_when_normality_claim_conflicts_with_heavy_tails() -> None:
    values = [-15, -2, -1.8, -1.5, -1.2, -1, -0.8, -0.5, -0.2, 0, 0.2, 0.5, 0.8, 1, 1.2, 1.5, 1.8, 2, 2.2, 15]
    report = Chart.qq(
        data=pd.DataFrame({"amount": values}),
        value="amount",
        claim="The amount data are normally distributed with no meaningful tail departure.",
        source="synthetic.heavy_tails",
        unit="dollars",
        title="Normal QQ diagnostic",
    ).audit()

    assert report.verdict == "REVIEW"
    assert _severities(report)["claim.qq.normality_support"] == "WARN"


def test_qq_audit_accepts_moderate_tail_alignment() -> None:
    report = Chart.qq(
        data=pd.DataFrame({"amount": list(range(1, 21))}),
        value="amount",
        claim="Observed quantiles broadly track a normal reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="Normal QQ diagnostic",
    ).audit()

    assert _severities(report)["claim.qq.normality_support"] == "PASS"


def test_qq_spec_audit_requires_reference_line() -> None:
    frame = pd.DataFrame(
        {
            QQ_THEORETICAL_FIELD: list(range(20)),
            QQ_SAMPLE_FIELD: list(range(20)),
            QQ_REFERENCE_FIELD: list(range(20)),
        }
    )

    report = audit_spec(
        _qq_spec(include_reference=False),
        data=frame,
        claim="Observed quantiles broadly track a normal reference.",
    )

    assert report.verdict == "BLOCK"
    assert _severities(report)["visual.qq.reference_line"] == "FAIL"


def test_qq_spec_audit_warns_on_heavy_tail_claim() -> None:
    sample = [-15, -2, -1.8, -1.5, -1.2, -1, -0.8, -0.5, -0.2, 0, 0.2, 0.5, 0.8, 1, 1.2, 1.5, 1.8, 2, 2.2, 15]
    frame = pd.DataFrame(
        {
            QQ_THEORETICAL_FIELD: list(range(20)),
            QQ_SAMPLE_FIELD: sample,
            QQ_REFERENCE_FIELD: list(range(20)),
        }
    )

    report = audit_spec(
        _qq_spec(),
        data=frame,
        claim="The data are normally distributed with no meaningful tail departure.",
    )

    assert report.verdict == "REVIEW"
    assert _severities(report)["claim.qq.normality_support"] == "WARN"


def test_ecdf_chart_renders_step_line() -> None:
    chart = Chart.ecdf(
        data=pd.DataFrame({"amount": [1, 1, 2, 4, 8, 16]}),
        value="amount",
        claim="Most observations are below eight dollars.",
        source="synthetic.amounts",
        unit="dollars",
        title="Empirical cumulative distribution",
    )

    spec = chart.to_vega_lite()

    assert chart.intent == "ecdf"
    assert spec["mark"]["type"] == "line"
    assert spec["mark"]["interpolate"] == "step-after"
    assert spec["encoding"]["y"]["field"] == ECDF_PROBABILITY_FIELD


def test_ecdf_records_start_at_zero_and_end_at_one() -> None:
    records = ecdf_records(pd.DataFrame({"amount": [1, 1, 2, 4]}), value="amount")

    assert records[0][ECDF_PROBABILITY_FIELD] == 0.0
    assert records[-1][ECDF_PROBABILITY_FIELD] == 1.0
    assert [row[ECDF_PROBABILITY_FIELD] for row in records] == sorted(
        row[ECDF_PROBABILITY_FIELD] for row in records
    )


def test_grouped_ecdf_reaches_one_for_each_group() -> None:
    frame = pd.DataFrame({"segment": ["A", "A", "B", "B"], "amount": [1, 2, 10, 20]})
    records = ecdf_records(frame, value="amount", group="segment")

    terminal = {}
    for row in records:
        terminal[row["segment"]] = row[ECDF_PROBABILITY_FIELD]

    assert terminal == {"A": 1.0, "B": 1.0}


def test_residual_chart_renders_points_and_zero_reference() -> None:
    chart = Chart.residual(
        data=pd.DataFrame({"fitted": [1, 2, 3, 4], "residual": [-0.2, 0.1, 0.3, -0.1]}),
        fitted="fitted",
        residual="residual",
        claim="Residuals remain centered around zero across fitted values.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    )

    spec = chart.to_vega_lite()

    assert chart.intent == "residual"
    assert spec["layer"][0]["mark"]["type"] == "point"
    assert spec["layer"][1]["mark"]["type"] == "rule"
    assert spec["layer"][1]["encoding"]["y"]["datum"] == 0


def test_residual_audit_requires_numeric_fitted_values() -> None:
    report = Chart.residual(
        data=pd.DataFrame({"fitted": ["low", "mid", "high"], "residual": [0.1, -0.2, 0.1]}),
        fitted="fitted",
        residual="residual",
        claim="Residuals are centered around zero.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.residual.fitted.numeric"] == "FAIL"


@pytest.mark.parametrize(
    ("row_count", "expected_severity"),
    [(4, "FAIL"), (10, "WARN"), (20, "PASS")],
)
def test_residual_sample_size_thresholds(row_count: int, expected_severity: str) -> None:
    report = Chart.residual(
        data=pd.DataFrame({"fitted": list(range(row_count)), "residual": [0.1, -0.1] * (row_count // 2)}),
        fitted="fitted",
        residual="residual",
        claim="Residuals are centered around zero.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert _severities(report)["data.residual.sample_size"] == expected_severity


def test_residual_audit_warns_without_variation() -> None:
    report = Chart.residual(
        data=pd.DataFrame({"fitted": list(range(20)), "residual": [0.0] * 20}),
        fitted="fitted",
        residual="residual",
        claim="Residuals are centered around zero.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert _severities(report)["data.residual.variation"] == "WARN"


def test_residual_audit_warns_when_no_pattern_claim_conflicts_with_trend() -> None:
    fitted = list(range(20))
    residual = [value - 9.5 for value in fitted]
    report = Chart.residual(
        data=pd.DataFrame({"fitted": fitted, "residual": residual}),
        fitted="fitted",
        residual="residual",
        claim="Residuals show no pattern and are randomly scattered around zero.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert report.verdict == "REVIEW"
    assert _severities(report)["claim.residual.pattern_support"] == "WARN"


def test_residual_audit_detects_curved_structure() -> None:
    fitted = list(range(21))
    residual = [((value - 10) ** 2) / 20 - 2 for value in fitted]
    report = Chart.residual(
        data=pd.DataFrame({"fitted": fitted, "residual": residual}),
        fitted="fitted",
        residual="residual",
        claim="Residuals show no obvious pattern.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert _severities(report)["claim.residual.pattern_support"] == "WARN"


def test_residual_audit_accepts_low_structure_pattern() -> None:
    report = Chart.residual(
        data=pd.DataFrame({"fitted": list(range(20)), "residual": [0.1, -0.1] * 10}),
        fitted="fitted",
        residual="residual",
        claim="Residuals remain centered around zero with no obvious fitted-value pattern.",
        source="synthetic.model",
        unit="dollars",
        title="Residual diagnostic",
    ).audit()

    assert _severities(report)["claim.residual.pattern_support"] == "PASS"


def test_residual_spec_audit_warns_on_obvious_pattern() -> None:
    frame = pd.DataFrame(
        {
            "fitted": list(range(20)),
            "residual": [value - 9.5 for value in range(20)],
        }
    )

    report = audit_spec(
        _residual_spec(),
        data=frame,
        claim="Residuals show no pattern and are randomly scattered around zero.",
    )

    assert report.verdict == "REVIEW"
    assert _severities(report)["claim.residual.pattern_support"] == "WARN"
    assert _severities(report)["visual.residual.zero_reference"] == "PASS"


def test_residual_spec_audit_blocks_tiny_sample() -> None:
    frame = pd.DataFrame({"fitted": [1, 2, 3, 4], "residual": [0.2, -0.1, 0.1, -0.2]})

    report = audit_spec(
        _residual_spec(),
        data=frame,
        claim="This tiny diagnostic is sufficient to assess residual behavior.",
    )

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.residual.sample_size"] == "FAIL"


def test_residual_spec_audit_requires_zero_reference_line() -> None:
    frame = pd.DataFrame({"fitted": list(range(20)), "residual": [0.1, -0.1] * 10})

    report = audit_spec(
        _residual_spec(include_zero_rule=False),
        data=frame,
        claim="Residuals remain centered around zero with no obvious fitted-value pattern.",
    )

    assert report.verdict == "BLOCK"
    assert _severities(report)["visual.residual.zero_reference"] == "FAIL"
