"""Create and audit a rooted process-tree flowchart."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart


OUTPUT_DIR = Path(__file__).parent / "output"


def main() -> None:
    frame = pd.DataFrame(
        {
            "step_id": ["start", "review", "approve", "revise", "ship"],
            "parent_id": [None, "start", "review", "review", "approve"],
            "step": [
                "Request received",
                "Review request",
                "Approve",
                "Revise",
                "Ship",
            ],
            "branch": [None, None, "Yes", "No", None],
        }
    )

    chart = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        branch="branch",
        claim="Requests move from intake through review to revision or approval.",
        source="synthetic.request_approval",
        title="Request approval flow",
    )

    report = chart.audit()
    print(report.verdict_summary())
    for finding in report.findings:
        print(f"{finding.severity} {finding.rule_id}: {finding.message}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "process_tree.vl.json"
    output_path.write_text(json.dumps(chart.to_vega_lite(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
