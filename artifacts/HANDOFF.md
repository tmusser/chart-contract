# HANDOFF

RESUME PACKET

- Goal: add first-class distribution intents without breaking the existing trend/rank/compare contract or CLI behavior.
- Workflow State: `Chart.histogram()`, `Chart.boxplot()`, `Chart.violin()`, distribution renderers, distribution audit rules, tests, docs, and `examples/distribution_charts.py` are all in place.
- Branch: `codex/distribution-chart-intents`
- Next task: review the diff, then stage/commit or keep iterating if a follow-up is needed.
- Verification: `./.venv/bin/python -m pytest -q`, `./.venv/bin/python examples/distribution_charts.py`, `./.venv/bin/python examples/bad_to_good_chart.py`, `./.venv/bin/chart-contract --help`, and `git diff --check`
- Read first: `README.md`, `ROADMAP.md`, `docs/AUDIT_RULES.md`, `artifacts/VERIFY.md`

## Current Repo State

- The v0.1 scope in `artifacts/SPEC.md` remains intact, and the new distribution intents live in a separate v0.3 preview section.
- The v0.2.0 agent gate is still intact: CLI loading, report serialization, trap fixtures, and CI smoke checks remain in place.
- Distribution intents now exist as `Chart.histogram()`, `Chart.boxplot()`, and `Chart.violin()` with matching Altair renderers.
- `audit_chart()` and `audit_spec()` now enforce distribution-specific checks for numeric metrics, sample sizes, grouped categories, histogram bins, and violin density warnings.
- `examples/distribution_charts.py` writes histogram, boxplot, and violin Vega-Lite specs into `examples/output/`.
- README, `docs/AUDIT_RULES.md`, `ROADMAP.md`, and `artifacts/SPEC.md` now describe the distribution preview and keep the claim-first framing explicit.
- The repo still has tracked example-output drift whenever the example scripts are run, so those artifacts need review before any commit.

## Working Commands

- `git diff --check`
- `./.venv/bin/python -m pytest tests/test_distribution_intents.py -q`
- `./.venv/bin/python -m pytest tests/test_audit_spec.py -q`
- `./.venv/bin/python -m pytest tests/test_chart_intents.py -q`
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python examples/distribution_charts.py`
- `./.venv/bin/python examples/bad_to_good_chart.py`
- `./.venv/bin/chart-contract --help`
- `sed -n '1,260p' ROADMAP.md`
- `sed -n '1,220p' docs/AUDIT_RULES.md`

## Important Decisions

- Keep the distribution slice claim-first and deterministic; avoid turning the package into a full visualization library.
- Keep v0.1 scope in `artifacts/SPEC.md` stable while using a separate preview section for new intents.
- Keep the existing trend/rank/compare API and CLI behavior unchanged.
- Keep the distribution audits focused on numeric metrics, sample size, grouping, bins, and violin density warnings.
- Keep example outputs synthetic and inspectable so they stay easy to review.

## Next Recommended Task

Use the roadmap, SPEC, and audit-rules docs as the source of truth for any follow-up slice.
