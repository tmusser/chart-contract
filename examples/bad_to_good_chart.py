"""Hero demo: risky spec -> audit -> corrected contract-driven chart."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart, audit_spec

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise", "Mid-Market", "Public", "Startup", "Partners", "Other"],
            "conversion_rate": [0.09, 0.18, 0.14, 0.12, 0.16, 0.11, 0.08],
        }
    )
    bad_spec = {
        "mark": {"type": "arc", "innerRadius": 40},
        "title": "Chart",
        "encoding": {
            "theta": {"field": "conversion_rate", "type": "quantitative"},
            "color": {"field": "segment", "type": "nominal"},
        },
        "data": {"values": df.to_dict(orient="records")},
    }
    claim = "The onboarding launch caused conversion lift across customer segments."

    print("Bad chart audit:")
    bad_report = audit_spec(spec=bad_spec, data=df, claim=claim)
    for finding in bad_report.findings:
        print(f"- [{finding.severity}] {finding.rule_id}: {finding.message}")

    corrected_chart = Chart.rank(
        data=df.sort_values("conversion_rate", ascending=False),
        x="segment",
        y="conversion_rate",
        claim="Enterprise and startup segments show the highest observed conversion rates.",
        source="synthetic.segment_conversion",
        unit="conversion rate",
        caveat="Observational segment summary; not causal proof for the onboarding launch.",
    )
    corrected_report = corrected_chart.audit()
    corrected_spec = corrected_chart.to_vega_lite()

    output_path = OUTPUT_DIR / "corrected_chart.vl.json"
    output_path.write_text(json.dumps(corrected_spec, indent=2))

    print("\nCorrected chart audit:")
    for finding in corrected_report.findings:
        print(f"- [{finding.severity}] {finding.rule_id}: {finding.message}")
    print(f"\nWrote corrected chart spec to {output_path}")


if __name__ == "__main__":
    main()
