# HANDOFF

RESUME PACKET

- Goal: Keep `chart-contract` credible as a claim-first audited chart harness while applying small public-facing polish patches without scope expansion.
- Workflow State: polish patch complete, next gate=`verify-contract` satisfied, context risk=low.
- Branch: `main`, Commit: `7689daa`, Dirty: yes
- Next task: commit and push the polish patch, then consider CI compatibility follow-up
- Verification: `python3 -m pip install -e '.[dev]' && python3 examples/bad_to_good_chart.py && python3 -m pytest`
- Read first: `artifacts/HANDOFF.md`, `artifacts/SPEC.md`, `artifacts/PLAN.md`, `artifacts/VERIFY.md`, then `README.md`

## Current Goal

The repository now includes a bounded credibility patch: clearer README positioning, packaging hygiene, MIT licensing, a disciplined roadmap, low-risk `AuditReport` helpers, and minimal GitHub Actions CI.

## Completed Slices

- Package skeleton and packaging -> verified by editable install and import tests
- Audit models and deterministic rules -> verified by focused pytest coverage
- Trend, rank, and compare intents -> verified by chart intent tests and example runs
- Experimental `audit_spec()` -> verified by spec audit tests and hero example
- README, docs, manifests, and workflow case study -> verified by structural checks
- Public-facing polish patch -> verified by editable install, hero example run, full pytest, and `git diff --check`

## Changed Files

- `src/chart_contract/chart.py` -> front-door `Chart` dataclass and intent constructors
- `src/chart_contract/audit.py` -> audit models, chart audits, experimental spec audit, and low-risk report helpers
- `src/chart_contract/contracts.py` -> shared claim/title/filter/spec helper logic
- `src/chart_contract/renderers/altair.py` -> Altair/Vega-Lite rendering helpers
- `tests/` -> deterministic coverage for imports, audit rules, intents, spec auditing, and example execution
- `examples/` -> synthetic-data demos and emitted Vega-Lite specs
- `docs/` -> rationale, visual contract, principles, workflow case study, and stronger contract examples
- `README.md` -> clearer public-facing positioning and audit-output scanability
- `pyproject.toml` / `LICENSE` / `ROADMAP.md` / `.github/workflows/ci.yml` -> packaging hygiene, license, disciplined roadmap, and minimal CI
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
- Defer rendered README screenshots rather than adding heavyweight export dependencies in this patch.

## Open Decisions

- Whether to pin dependency versions or add compatibility shims in CI for future maintenance.
- Whether to add lightweight SVG/PNG export tooling for README visuals in a later release.

## Traps

- Do not expand beyond `trend`, `rank`, and `compare` without updating `artifacts/SPEC.md`.
- Do not convert the repo into a dashboard or chart gallery project.
- Preserve proof artifacts in `artifacts/` after any future changes.

## Next Recommended Task

Commit and push this polish patch, then decide whether the next step should be CI compatibility coverage or lightweight render export tooling.

Verification command:
- `python3 -m pip install -e '.[dev]' && python3 examples/bad_to_good_chart.py && python3 -m pytest`
