from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart
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
