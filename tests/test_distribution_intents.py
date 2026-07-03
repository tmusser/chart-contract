from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart


def test_histogram_chart_preserves_distribution_fields() -> None:
    df = pd.DataFrame({"amount": [1, 2, 2, 3, 4, 5, 5, 5], "segment": ["A", "A", "B", "B", "B", "C", "C", "C"]})

    chart = Chart.histogram(
        data=df,
        value="amount",
        claim="The amounts are spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
        bins=12,
        group="segment",
    )
    spec = chart.to_vega_lite()

    assert chart.intent == "histogram"
    assert chart.value == "amount"
    assert chart.bins == 12
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["field"] == "amount"
    assert spec["encoding"]["x"]["bin"]["maxbins"] == 12
    assert spec["encoding"]["y"]["aggregate"] == "count"


def test_boxplot_chart_renders_boxplot_mark() -> None:
    df = pd.DataFrame(
        {
            "segment": ["SMB", "SMB", "Enterprise", "Enterprise"],
            "amount": [5, 7, 12, 14],
        }
    )

    spec = Chart.boxplot(
        data=df,
        x="segment",
        y="amount",
        claim="Enterprise spends more than SMB.",
        source="synthetic.amounts",
        unit="count",
    ).to_vega_lite()

    assert spec["mark"]["type"] == "boxplot"
    assert spec["encoding"]["x"]["field"] == "segment"
    assert spec["encoding"]["y"]["field"] == "amount"


def test_violin_chart_renders_density_area() -> None:
    df = pd.DataFrame(
        {
            "segment": ["SMB", "SMB", "Enterprise", "Enterprise", "Enterprise", "SMB"],
            "amount": [5, 7, 12, 14, 15, 6],
        }
    )

    spec = Chart.violin(
        data=df,
        x="segment",
        y="amount",
        claim="The two segments have different shapes.",
        source="synthetic.amounts",
        unit="count",
    ).to_vega_lite()

    assert spec["mark"]["type"] == "area"
    assert spec["transform"][0]["density"] == "amount"
    assert spec["encoding"]["color"]["field"] == "segment"


def test_histogram_audit_fails_when_value_column_is_missing() -> None:
    df = pd.DataFrame({"segment": ["A", "B", "C"]})

    report = Chart.histogram(
        data=df,
        value="amount",
        claim="The amounts are spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.distribution.value.numeric"] == "FAIL"
    assert report.verdict == "BLOCK"


def test_distribution_audit_fails_when_value_column_is_not_numeric() -> None:
    df = pd.DataFrame({"segment": ["A", "B", "C"], "amount": ["low", "mid", "high"]})

    report = Chart.boxplot(
        data=df,
        x="segment",
        y="amount",
        claim="The segments differ in amount.",
        source="synthetic.amounts",
        unit="count",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.distribution.value.numeric"] == "FAIL"
    assert report.verdict == "BLOCK"


@pytest.mark.parametrize(
    ("row_count", "expected_severity"),
    [
        (4, "FAIL"),
        (10, "WARN"),
        (20, "PASS"),
    ],
)
def test_distribution_sample_size_thresholds(row_count: int, expected_severity: str) -> None:
    df = pd.DataFrame({"amount": list(range(row_count))})

    report = Chart.histogram(
        data=df,
        value="amount",
        claim="The amounts are spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.distribution.sample_size"] == expected_severity


def test_histogram_bins_outside_readable_range_warn() -> None:
    df = pd.DataFrame({"amount": list(range(50))})

    report = Chart.histogram(
        data=df,
        value="amount",
        claim="The amounts are spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
        bins=3,
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["readability.histogram.bins"] == "WARN"


def test_violin_low_sample_size_warns() -> None:
    df = pd.DataFrame({"segment": ["A"] * 12, "amount": list(range(12))})

    report = Chart.violin(
        data=df,
        x="segment",
        y="amount",
        claim="The segment distribution is shaped this way.",
        source="synthetic.amounts",
        unit="count",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["visual.violin.sample_size"] == "WARN"


def test_distribution_group_sample_size_warns_for_small_groups() -> None:
    df = pd.DataFrame(
        {
            "segment": ["A"] * 4 + ["B"] * 12,
            "amount": list(range(16)),
        }
    )

    report = Chart.boxplot(
        data=df,
        x="segment",
        y="amount",
        claim="The segments differ in amount.",
        source="synthetic.amounts",
        unit="count",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.distribution.group_sample_size"] == "WARN"
