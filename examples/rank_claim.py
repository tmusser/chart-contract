"""Rank chart example."""

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
            "segment": ["Free", "Starter", "Pro", "Enterprise"],
            "adoption": [120, 210, 185, 260],
        }
    )
    chart = Chart.rank(
        data=df,
        x="segment",
        y="adoption",
        claim="Enterprise leads adoption volume across plans.",
        source="synthetic.plan_adoption",
        unit="accounts",
    )
    report = chart.audit()
    spec = chart.to_vega_lite()
    output_path = OUTPUT_DIR / "rank_claim.vl.json"
    output_path.write_text(json.dumps(spec, indent=2))

    print(report.summary())
    for finding in report.findings:
        print(f"- [{finding.severity}] {finding.message}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
