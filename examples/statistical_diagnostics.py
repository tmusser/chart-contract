"""Statistical diagnostic demo: QQ, ECDF, and residual plots."""

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

    distribution = pd.DataFrame(
        {
            "segment": ["SMB"] * 15 + ["Enterprise"] * 15,
            "amount": [
                4,
                5,
                5,
                6,
                6,
                6,
                7,
                7,
                8,
                8,
                9,
                10,
                10,
                11,
                12,
                11,
                12,
                12,
                13,
                13,
                14,
                14,
                15,
                15,
                16,
                17,
                18,
                19,
                20,
                22,
            ],
        }
    )

    qq = Chart.qq(
        data=distribution,
        value="amount",
        claim="Observed amount quantiles are broadly aligned with a normal reference.",
        source="synthetic.amounts",
        unit="dollars",
        title="Normal QQ plot for amount",
    )
    _audit_and_write("QQ", qq, OUTPUT_DIR / "qq_chart.vl.json")

    ecdf = Chart.ecdf(
        data=distribution,
        value="amount",
        group="segment",
        claim="Enterprise amounts are shifted above SMB amounts across most cumulative probabilities.",
        source="synthetic.amounts",
        unit="dollars",
        title="Empirical cumulative amount by segment",
    )
    _audit_and_write("ECDF", ecdf, OUTPUT_DIR / "ecdf_chart.vl.json")

    residual_frame = pd.DataFrame(
        {
            "fitted": [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48],
            "residual": [0.8, -0.4, 0.3, -0.7, 0.5, -0.2, 0.1, -0.3, 0.6, -0.5, 0.2, -0.1, 0.4, -0.6, 0.3, -0.2, 0.1, -0.4, 0.5, -0.3],
        }
    )
    residual = Chart.residual(
        data=residual_frame,
        fitted="fitted",
        residual="residual",
        claim="Residuals remain centered around zero across the fitted range.",
        source="synthetic.model_predictions",
        unit="dollars",
        title="Residuals versus fitted values",
    )
    _audit_and_write("Residual", residual, OUTPUT_DIR / "residual_chart.vl.json")


if __name__ == "__main__":
    main()
