"""Hero demo: risky spec -> audit -> corrected contract-driven chart."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd

from chart_contract import Chart, audit_spec

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def _export_svg(chart: alt.Chart, path: Path) -> bool:
    try:
        chart.save(str(path), format="svg")
        return True
    except Exception as exc:  # pragma: no cover - only hit when export tooling misbehaves
        print(f"SVG export failed for {path.name}: {exc}")
        return False


def _write_export_fallback(
    path: Path,
    bad_spec: dict,
    bad_report: dict,
    corrected_spec: dict,
    corrected_report: dict,
) -> None:
    lines = [
        "# Hero Export Notes",
        "",
        "SVG export was not reliable in this environment, so the proof artifact falls back to",
        "the Vega-Lite specs and audit reports below.",
        "",
        "## Bad Spec",
        "",
        "```json",
        json.dumps(bad_spec, indent=2),
        "```",
        "",
        "## Bad Audit",
        "",
        "```json",
        json.dumps(bad_report, indent=2),
        "```",
        "",
        "## Corrected Spec",
        "",
        "```json",
        json.dumps(corrected_spec, indent=2),
        "```",
        "",
        "## Corrected Audit",
        "",
        "```json",
        json.dumps(corrected_report, indent=2),
        "```",
    ]
    _write_text(path, "\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise", "Mid-Market", "Public", "Startup", "Partners", "Other"],
            "conversion_rate": [0.09, 0.18, 0.14, 0.12, 0.16, 0.11, 0.08],
        }
    )
    chart_df = df.astype({"segment": "object"})
    chart_records = chart_df.to_dict(orient="records")

    bad_chart = (
        alt.Chart(alt.InlineData(values=chart_records))
        .mark_arc(innerRadius=40)
        .encode(
            theta=alt.Theta("conversion_rate:Q"),
            color=alt.Color("segment:N"),
            tooltip=[alt.Tooltip("segment:N"), alt.Tooltip("conversion_rate:Q")],
        )
        .properties(title="Chart", width=320, height=320)
    )
    bad_spec = bad_chart.to_dict()
    claim = "The onboarding launch caused conversion lift across customer segments."

    print("Bad chart audit:")
    bad_report = audit_spec(spec=bad_spec, data=chart_records, claim=claim)
    for finding in bad_report.findings:
        print(f"- [{finding.severity}] {finding.rule_id}: {finding.message}")

    bad_audit_md = OUTPUT_DIR / "bad_chart_audit.md"
    bad_audit_json = OUTPUT_DIR / "bad_chart_audit.json"
    _write_text(bad_audit_md, bad_report.to_markdown())
    _write_json(bad_audit_json, bad_report.to_dict())

    corrected_chart = Chart.rank(
        data=chart_df.sort_values("conversion_rate", ascending=False),
        x="segment",
        y="conversion_rate",
        claim="Enterprise and startup segments show the highest observed conversion rates.",
        source="synthetic.segment_conversion",
        unit="conversion rate",
        caveat="Observational segment summary; not causal proof for the onboarding launch.",
    )
    corrected_report = corrected_chart.audit()
    corrected_spec = corrected_chart.to_vega_lite()
    corrected_altair = corrected_chart.to_altair()

    corrected_spec_path = OUTPUT_DIR / "corrected_chart.vl.json"
    _write_json(corrected_spec_path, corrected_spec)

    print("\nCorrected chart audit:")
    for finding in corrected_report.findings:
        print(f"- [{finding.severity}] {finding.rule_id}: {finding.message}")

    bad_svg = OUTPUT_DIR / "bad_chart.svg"
    corrected_svg = OUTPUT_DIR / "corrected_chart.svg"
    bad_svg_ok = _export_svg(bad_chart, bad_svg)
    corrected_svg_ok = _export_svg(corrected_altair, corrected_svg)

    if not (bad_svg_ok and corrected_svg_ok):
        fallback_note = OUTPUT_DIR / "hero_export_notes.md"
        _write_export_fallback(
            fallback_note,
            bad_spec=bad_spec,
            bad_report=bad_report.to_dict(),
            corrected_spec=corrected_spec,
            corrected_report=corrected_report.to_dict(),
        )
        print(f"\nWrote export fallback notes to {fallback_note}")
    else:
        print(f"\nWrote rendered charts to {bad_svg} and {corrected_svg}")

    print(f"Wrote audit reports to {bad_audit_md} and {bad_audit_json}")
    print(f"Wrote corrected chart spec to {corrected_spec_path}")


if __name__ == "__main__":
    main()
