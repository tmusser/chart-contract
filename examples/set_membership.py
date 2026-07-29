"""Create and audit a two-set membership chart."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart


OUTPUT_DIR = Path(__file__).parent / "output"


def main() -> None:
    data = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"],
            "email": [1, 1, 1, 1, 0, 0, 0, 0],
            "paid_search": [0, 1, 1, 0, 1, 1, 0, 0],
        }
    )
    chart = Chart.set_membership(
        data=data,
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        set_a_label="Email",
        set_b_label="Paid search",
        claim="Email and paid search each reach four customers, with two customers in both sets.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
        caveat="Schematic geometry; labeled region counts are authoritative.",
    )

    report = chart.audit()
    print(report.verdict_summary())
    for finding in report.findings:
        print(f"{finding.severity} {finding.rule_id}: {finding.message}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "set_membership_chart.vl.json"
    output_path.write_text(json.dumps(chart.to_vega_lite(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
