"""Compare chart example."""

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
            "segment": ["SMB", "SMB", "Enterprise", "Enterprise"],
            "region": ["East", "West", "East", "West"],
            "win_rate": [0.21, 0.24, 0.29, 0.31],
        }
    )
    chart = Chart.compare(
        data=df,
        x="segment",
        y="win_rate",
        group="region",
        claim="Enterprise win rate leads SMB in both regions.",
        source="synthetic.pipeline_summary",
        unit="win rate",
        caveat="Observed pipeline summary; not a causal attribution statement.",
    )
    report = chart.audit()
    spec = chart.to_vega_lite()
    output_path = OUTPUT_DIR / "compare_claim.vl.json"
    output_path.write_text(json.dumps(spec, indent=2))

    print(report.summary())
    for finding in report.findings:
        print(f"- [{finding.severity}] {finding.message}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
