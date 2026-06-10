# BUILD MANIFEST

- Repo name: `chart-contract`
- Package name: `chart_contract`
- Generated date: `2026-06-10`
- Version scope: `v0.1`
- Built with: `ai-engineering-skills`
- Status: complete

## Front-Door API

- `Chart.trend()`
- `Chart.rank()`
- `Chart.compare()`
- `chart.audit()`
- `chart.to_altair()`
- `chart.to_vega_lite()`
- experimental `audit_spec()`

## Chart Intents

- `trend`
- `rank`
- `compare`

## Renderer

- Altair for chart objects
- Vega-Lite dictionaries via `to_vega_lite()`

## Audit Categories

- data contract
- visual form
- claim support
- labels and units
- scale and axis risk
- provenance
- caveats
- accessibility/readability
- Tufte-inspired visual integrity

## Notable Rules

- `data.trend.min_points` fails single-point trend charts and passes when there are at least two observations.

## Examples

- `examples/bad_to_good_chart.py`
- `examples/trend_claim.py`
- `examples/rank_claim.py`
- `examples/compare_claim.py`
- Generated outputs in `examples/output/`
- `examples/output/bad_chart_audit.md`
- `examples/output/bad_chart_audit.json`
- `examples/output/bad_chart.svg`
- `examples/output/corrected_chart.svg`
- `examples/output/corrected_chart.vl.json`

## Docs

- `README.md`
- `docs/WHY.md`
- `docs/VISUAL_CONTRACT.md`
- `docs/DESIGN_PRINCIPLES.md`
- `docs/AGENT_WORKFLOW_CASE_STUDY.md`
- `AGENTS.md`

## Tests

- `tests/test_import.py`
- `tests/test_audit_rules.py`
- `tests/test_chart_intents.py`
- `tests/test_audit_spec.py`

## Build Workflow Invocations

- `$mini-spec`
- `$thin-plan`
- `$scope-freeze`
- `$build-one`
- `$test-mini`
- `$verify-contract`
- `$handoff`

## Verification Summary

- Editable install passed
- Full pytest suite passed (`16 passed`)
- Hero demo emitted audit Markdown/JSON plus static SVG renders
- `git diff --check` passed
- Structural validation passed
- Local path and file-URL grep checks passed

## Remaining Risks

- `audit_spec()` is experimental and intentionally narrow.
- Visual verification now includes committed static SVGs, but browser rendering remains unverified.
- Percent-unit vs decimal-scale mismatch remains a v0.2 policy decision.
- Current dependency set emits Altair-related deprecation warnings during tests.

## Release Note

Created chart-contract, a lightweight Python harness for claim-first, audited analytical charts. The v0.1 package supports trend, rank, and compare intents, Altair/Vega-Lite output, deterministic audit findings, a bad-chart-to-contract demo, and build artifacts documenting how ai-engineering-skills was used to create the repo. Final v0.1 polish adds committed hero SVGs and audit report artifacts for a stronger first impression.
