"""Trend chart example."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "week": ["2026-05-01", "2026-05-08", "2026-05-15", "2026-05-22"],
            "conversion_rate": [0.12, 0.14, 0.15, 0.16],
        }
    )
    chart = Chart.trend(
        data=df,
        x="week",
        y="conversion_rate",
        claim="Conversion improved after the onboarding launch window.",
        source="synthetic.funnel_events",
        unit="conversion rate",
        event={"x": "2026-05-08", "label": "Onboarding launch"},
        caveat="Observational trend; not causal proof.",
    )
    report = chart.audit()
    spec = chart.to_vega_lite()
    output_path = OUTPUT_DIR / "trend_claim.vl.json"
    output_path.write_text(json.dumps(spec, indent=2))

    print(report.summary())
    for finding in report.findings:
        print(f"- [{finding.severity}] {finding.message}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
