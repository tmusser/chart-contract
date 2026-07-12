# SPEC

## Objective

Build `chart-contract`, a lightweight Python harness for claim-first, audited analytical charts that turns analytical claims into inspected `trend`, `rank`, and `compare` charts with Altair/Vega-Lite output and deterministic PASS/WARN/FAIL audit findings.

## Audience

- Analysts and analytics engineers who want auditable chart defaults.
- AI-assisted builders who need a thin contract layer before sharing charts.

## v0.1 Scope

- `Chart.trend()`, `Chart.rank()`, `Chart.compare()`
- `chart.audit()`
- `chart.to_altair()`
- `chart.to_vega_lite()`
- experimental `audit_spec()`
- Altair/Vega-Lite as the only renderer
- deterministic PASS/WARN/FAIL findings
- docs, tests, examples, and build-proof artifacts

## v0.3 Preview

- Distribution intents: `Chart.histogram()`, `Chart.boxplot()`, `Chart.violin()`
- Statistical diagnostic intents: `Chart.qq()`, `Chart.ecdf()`, `Chart.residual()`
- distribution-specific audit rules for numeric value fields, sample size, grouped categories, histogram bins, and violin density warnings
- statistical diagnostic rules for QQ reference support, tie density, fitted-value types, residual sample size, and residual variation
- deterministic normal-reference QQ and ECDF preparation without SciPy or external data fetching
- `examples/distribution_charts.py` and `examples/statistical_diagnostics.py`

## Non-Goals

- UI, dashboards, or Streamlit
- automatic chart correction
- renderers beyond Altair/Vega-Lite
- broad plotting-library coverage beyond the explicitly supported intents
- external data fetching, LLM calls, telemetry, or theme systems

## Acceptance Criteria

- Public API supports the usage shown in the brief.
- Audit layer catches required completeness, data-contract, visual-form, claim-support, provenance, and Tufte-inspired integrity checks.
- `audit_spec()` flags non-zero bar baselines and overcrowded pie/arc charts.
- Examples run on synthetic data and write Vega-Lite JSON into `examples/output/`.
- README leads with the bad-chart to corrected-chart story.
- Artifacts document the `ai-engineering-skills` workflow and verification evidence.

## Constraints

- Python 3.10+
- Minimal dependencies: `pandas`, `altair`, `pytest`
- Keep models simple and inspectable
- Explainable warnings only; no unverifiable claims of compliance or certification

## Verification Commands

- `python -m pip install -e ".[dev]"`
- `pytest`
- `python examples/bad_to_good_chart.py`
- `python examples/trend_claim.py`
- `python examples/rank_claim.py`
- `python examples/compare_claim.py`
- `python examples/statistical_diagnostics.py`
- `git diff --check`

## Smallest Verification Demo

Run `python examples/bad_to_good_chart.py` to show a risky spec audited with failures and a corrected contract-driven chart emitted as Vega-Lite JSON.

## Open Questions

- Event annotations in Altair will be kept simple in v0.1 unless implementation complexity rises.
- Subtitle/provenance handling may rely on chart metadata rather than full visual subtitles.
