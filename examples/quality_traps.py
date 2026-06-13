"""Small audit traps for agent-in-the-loop chart review."""

from __future__ import annotations

import pandas as pd

from chart_contract import Chart


def show_example(name: str, report, rule_ids: list[str]) -> None:
    print(name)
    for finding in report.findings:
        if finding.rule_id in rule_ids:
            print(f"- [{finding.severity}] {finding.rule_id}: {finding.message}")
    print()


def missing_unit() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.12, 0.15]})
    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved after the launch.",
        source="warehouse.funnel_events",
    ).audit()
    show_example("Missing unit", report, ["labels.unit.present"])


def missing_source() -> None:
    df = pd.DataFrame({"segment": ["SMB", "Enterprise"], "conversion_rate": [0.09, 0.18]})
    report = Chart.rank(
        data=df,
        x="segment",
        y="conversion_rate",
        claim="Enterprise leads conversion.",
        unit="conversion rate",
    ).audit()
    show_example("Missing source", report, ["contract.source.present"])


def causal_claim_without_support() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.12, 0.15]})
    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="The onboarding launch caused conversion to improve.",
        source="warehouse.funnel_events",
        unit="rate",
    ).audit()
    show_example("Causal claim without support", report, ["claim.causal_support"])


def main() -> None:
    missing_unit()
    missing_source()
    causal_claim_without_support()


if __name__ == "__main__":
    main()
