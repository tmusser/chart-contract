"""Distribution chart demo: histogram, boxplot, and violin."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from chart_contract import Chart

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _audit_and_write(label: str, chart: Chart, output_path: Path) -> None:
    report = chart.audit()
    print(f"{label}: {report.verdict_summary()}")
    _write_json(output_path, chart.to_vega_lite())
    print(f"Wrote {output_path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        {
            "segment": ["SMB"] * 15 + ["Enterprise"] * 15,
            "amount": [
                4,
                5,
                6,
                7,
                5,
                4,
                6,
                7,
                8,
                6,
                5,
                7,
                6,
                4,
                5,
                12,
                13,
                15,
                14,
                13,
                12,
                16,
                14,
                15,
                13,
                12,
                14,
                15,
                13,
                12,
            ],
        }
    )

    histogram = Chart.histogram(
        data=df,
        value="amount",
        claim="The amount values are spread across the observed range.",
        source="synthetic.amounts",
        unit="count",
        title="Amount distribution",
        bins=12,
    )
    _audit_and_write("Histogram", histogram, OUTPUT_DIR / "histogram_chart.vl.json")

    boxplot = Chart.boxplot(
        data=df,
        x="segment",
        y="amount",
        claim="SMB and Enterprise have different amount summaries.",
        source="synthetic.amounts",
        unit="count",
        title="Amount by segment",
    )
    _audit_and_write("Boxplot", boxplot, OUTPUT_DIR / "boxplot_chart.vl.json")

    violin = Chart.violin(
        data=df,
        x="segment",
        y="amount",
        claim="SMB and Enterprise have different amount shapes.",
        source="synthetic.amounts",
        unit="count",
        title="Amount density by segment",
    )
    _audit_and_write("Violin", violin, OUTPUT_DIR / "violin_chart.vl.json")


if __name__ == "__main__":
    main()
