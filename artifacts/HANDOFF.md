# HANDOFF

RESUME PACKET

- Goal: Deliver `chart-contract` v0.1 as a claim-first audited chart harness with proof artifacts showing the `ai-engineering-skills` workflow.
- Workflow State: build complete, next gate=`verify-contract` satisfied, context risk=low.
- Branch: `main`, Commit: pending initial commit, Dirty: yes
- Next task: add CI coverage for Altair/pandas compatibility without expanding v0.1 scope
- Verification: `python3 -m pytest && python3 examples/bad_to_good_chart.py`
- Read first: `artifacts/HANDOFF.md`, `artifacts/SPEC.md`, `artifacts/PLAN.md`, `artifacts/VERIFY.md`, then `README.md`

## Current Goal

The repository now ships the v0.1 package, examples, docs, tests, and build-proof artifacts requested in the brief.

## Completed Slices

- Package skeleton and packaging -> verified by editable install and import tests
- Audit models and deterministic rules -> verified by focused pytest coverage
- Trend, rank, and compare intents -> verified by chart intent tests and example runs
- Experimental `audit_spec()` -> verified by spec audit tests and hero example
- README, docs, manifests, and workflow case study -> verified by structural checks

## Changed Files

- `src/chart_contract/chart.py` -> front-door `Chart` dataclass and intent constructors
- `src/chart_contract/audit.py` -> audit models, chart audits, experimental spec audit
- `src/chart_contract/contracts.py` -> shared claim/title/filter/spec helper logic
- `src/chart_contract/renderers/altair.py` -> Altair/Vega-Lite rendering helpers
- `tests/` -> deterministic coverage for imports, audit rules, intents, spec auditing, and example execution
- `examples/` -> synthetic-data demos and emitted Vega-Lite specs
- `docs/` -> rationale, visual contract, principles, and workflow case study
- `artifacts/` -> spec, plan, todo, verification log, manifest, invocation log, and handoff state

## Working Commands

- `python3 -m pip install -e '.[dev]'`
- `python3 -m pytest`
- `python3 examples/bad_to_good_chart.py`
- `python3 examples/trend_claim.py`
- `python3 examples/rank_claim.py`
- `python3 examples/compare_claim.py`

## Important Decisions

- Keep Altair/Vega-Lite as the only renderer in v0.1.
- Keep `audit_spec()` experimental and deterministic rather than broad or AI-driven.
- Treat causal-language checks as warnings unless evidence is explicitly declared.
- Inline Vega-Lite data in the renderer to avoid local Altair/pandas dtype compatibility issues.

## Open Decisions

- Whether to pin dependency versions or add compatibility shims in CI for future maintenance.

## Traps

- Do not expand beyond `trend`, `rank`, and `compare` without updating `artifacts/SPEC.md`.
- Do not convert the repo into a dashboard or chart gallery project.
- Preserve proof artifacts in `artifacts/` after any future changes.

## Next Recommended Task

Add CI coverage that validates the current package against pinned Altair/pandas versions and records warning expectations.

Verification command:
- `python3 -m pytest && python3 examples/bad_to_good_chart.py`
