# SPEC

## Objective

Build `chart-contract`, a lightweight Python harness for claim-first analytical charts that makes the claim, evidence shape, visual intent, provenance, and known limitations inspectable before a chart is shared.

The package should emit Altair/Vega-Lite output and deterministic `PASS`/`WARN`/`FAIL` findings summarized as `READY`, `REVIEW`, or `BLOCK`.

## Audience

- Analysts and analytics engineers who want auditable chart defaults.
- AI-assisted builders who need a thin contract layer before sharing charts.
- Agent workflows that need a deterministic CLI gate and durable audit report.

## Current Scope

- descriptive intents: `Chart.trend()`, `Chart.rank()`, and `Chart.compare()`
- distribution intents: `Chart.histogram()`, `Chart.boxplot()`, and `Chart.violin()`
- statistical diagnostic intents: `Chart.qq()`, `Chart.ecdf()`, and `Chart.residual()`
- two-set membership intent: `Chart.set_membership()`
- `chart.audit()` for first-party chart contracts
- experimental `audit_spec()` for supported Vega-Lite evidence shapes
- `chart.to_altair()` and `chart.to_vega_lite()`
- `chart-contract audit spec` with text, JSON, and Markdown reports
- Altair/Vega-Lite as the only renderer
- deterministic, explainable audit findings and stable CLI exit behavior
- docs, tests, traps, examples, and generated proof artifacts

## Evidence Boundaries

- Trend, rank, compare, distribution, diagnostic, and membership claims require explicit fields and usable observations.
- QQ and residual charts provide visual diagnostic guardrails, not formal normality or model-adequacy certification.
- Set membership requires one row per unique universe member and exactly two explicit boolean or integer `0`/`1` membership columns.
- Venn-style circle geometry is schematic; labeled region counts are authoritative.
- Arbitrary external Vega-Lite specs are audited only where the required evidence can be reconstructed deterministically.

## Non-Goals

- UI, dashboards, or Streamlit
- automatic chart correction
- renderers beyond Altair/Vega-Lite
- broad plotting-library coverage beyond explicitly supported intents
- external data fetching, LLM calls, telemetry, or theme systems
- three-or-more-set Venn diagrams or area-proportional Venn fitting
- unverifiable claims of statistical, accessibility, or design certification

## Acceptance Criteria

- Public API supports every intent listed in Current Scope.
- Audit findings cover contract completeness, usable data, visual form, claim support, provenance, and explainable visual-integrity checks.
- The CLI returns stable reports and exit codes for `READY`, `REVIEW`, and `BLOCK`.
- First-party generated specs preserve intent and evidence metadata required for downstream auditing.
- Examples run on synthetic data and write inspectable Vega-Lite JSON into `examples/output/`.
- CI tests the supported Python range and validates an isolated built wheel.
- README, roadmap, changelog, and workflow artifacts describe current behavior without overstating guarantees.

## Constraints

- Python 3.10+
- Runtime dependencies limited to `pandas` and `altair`
- Simple, inspectable models and deterministic thresholds
- Explainable warnings only
- New intents require explicit data, claim, visual, test, and documentation contracts

## Verification Commands

- `python -m pip install -e ".[dev]"`
- `python -m pytest`
- `python examples/bad_to_good_chart.py`
- `python examples/distribution_charts.py`
- `python examples/statistical_diagnostics.py`
- `python examples/set_membership.py`
- `chart-contract --version`
- `git diff --check`

## Smallest Verification Demo

Run `python examples/bad_to_good_chart.py` to compare a risky chart that still renders with a corrected contract-driven chart and inspect the emitted audit evidence.

For set membership, run `python examples/set_membership.py` and verify that A-only, overlap, B-only, neither, and universe counts reconcile in the generated spec metadata.

## Open Questions

- What release version should carry the set-membership intent?
- Should a future many-set intent use an UpSet-style matrix rather than circles?
- Which additional external-spec shapes can be audited without inventing missing semantic evidence?
