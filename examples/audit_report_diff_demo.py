"""Build two reproducible bound audit reports for the audit-diff CLI example.

Usage:
    python examples/audit_report_diff_demo.py /tmp/chart-contract-report-diff
    chart-contract audit diff /tmp/chart-contract-report-diff/before.json \
      /tmp/chart-contract-report-diff/after.json --fail-on-regression
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

from chart_contract import audit_spec


def main(output_dir: str) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    spec = {
        "mark": "line",
        "title": "Recorded weekly sales trend",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {
                "field": "sales", "type": "quantitative",
                "scale": {"domain": [0, 10]},
            },
        },
        "usermeta": {
            "source": "synthetic.report_diff",
            "unit": "sales",
            "claim": "Recorded sales vary across the three weeks.",
            "user_requested_scale_override": True,
        },
    }
    for filename, values in (("before.json", [4, 5, 6]), ("after.json", [4, 5, 15])):
        data = pd.DataFrame({"week": ["W1", "W2", "W3"], "sales": values})
        report = audit_spec(spec, data=data)
        (root / filename).write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {root / 'before.json'} and {root / 'after.json'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/audit_report_diff_demo.py OUTPUT_DIR")
    main(sys.argv[1])
