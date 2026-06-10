import pandas as pd

from chart_contract import Chart


def test_missing_claim_fails() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["contract.claim.present"] == "FAIL"


def test_missing_source_warns() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="Conversion improved", unit="rate").audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["contract.source.present"] == "WARN"


def test_missing_unit_warns_for_quantitative_y() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        source="warehouse.funnel_events",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["labels.unit.present"] == "WARN"


def test_causal_language_without_caveat_warns() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="The onboarding launch caused conversion to improve.",
        source="warehouse.funnel_events",
        unit="conversion rate",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["claim.causal_support"] == "WARN"
