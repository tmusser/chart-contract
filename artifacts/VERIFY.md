# VERIFY

2026-09-13 - Add machine-readable audit profile parity

Environment:
- Branch: `agent/add-audit-profile-parity`
- Base: `main` at `08969c5eaa8d8e27fa5a28f8fc1781013ba8cde4`
- Local GitHub clone: unavailable in this execution environment because direct GitHub DNS resolution is disabled; GitHub Actions is the authoritative full-suite gate.

Changed areas:
- `src/chart_contract/profiles.py`
- `src/chart_contract/profile_diff.py`
- `src/chart_contract/cli.py`
- `src/chart_contract/__init__.py`
- `schemas/audit-profile-v1.schema.json`
- `schemas/audit-profile-diff-v1.schema.json`
- `tests/test_profiles.py`
- `tests/test_profile_diff.py`
- `tests/test_cli_profile.py`
- `docs/AUDIT_PROFILE.md`
- `AGENTS.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `artifacts/SPEC.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Verification gates added:
- profile manifest rule IDs must exactly match the 43 stable IDs documented in `docs/AUDIT_RULES.md`, in order
- profile manifest preserves `scientific_validation: false` and `automatic_adjudication: false`
- package/tool version-only drift must not change `audit-profile-semantics-v1` identity
- rule trigger or allowed-severity changes must change semantic identity
- profile diff must separate semantic drift from tool metadata drift
- profile diff must expose rule additions/removals, per-rule changes, and order drift without a compatibility judgment
- CLI `profile show` and `profile diff` must preserve the interpretation boundary and stable JSON types

Semantic boundaries:
- this slice does not change any existing audit rule implementation, threshold, or verdict
- saved audit report schema remains `0.3`; no profile identity is retroactively attached to historical reports
- a matching profile digest is content identity only, not authentication, proof of execution, or scientific validation
- profile drift is not automatically classified as safe, breaking, compatible, improved, or scientifically preferable

Pending authoritative verification:
- full pytest suite across Python 3.10-3.13
- existing CLI REVIEW/BLOCK/warnings-as-errors smoke gates
- isolated wheel build/install smoke test
- final PR diff review for accidental audit-semantic changes

2026-07-12 - Harden diagnostic claim audits

Environment:
- Branch: `agent/diagnostic-claim-traps`
- Pull request: #5 (`feat: harden diagnostic claim audits`)
- Python: 3.12 on GitHub Actions Ubuntu runner

Commands and gates:
- `python -m pytest` -> PASSED (full repository suite)
- legacy CLI REVIEW smoke check -> PASSED
- legacy CLI BLOCK smoke check -> PASSED
- legacy warnings-as-errors smoke check -> PASSED
- `qq_heavy_tails` -> PASSED (`REVIEW`, `claim.qq.normality_support`)
- `qq_missing_reference_line` -> PASSED (`BLOCK`, `visual.qq.reference_line`)
- `residual_obvious_pattern` -> PASSED (`REVIEW`, `claim.residual.pattern_support`)
- `diagnostic_tiny_sample` -> PASSED (`BLOCK`, `data.residual.sample_size`)
- GitHub Actions CI run #155 -> PASSED

Changed areas:
- `src/chart_contract/statistical_audit.py`
- `src/chart_contract/audit.py`
- `src/chart_contract/renderers/altair.py`
- `tests/test_statistical_intents.py`
- `examples/traps/qq_heavy_tails.*`
- `examples/traps/qq_missing_reference_line.*`
- `examples/traps/residual_obvious_pattern.*`
- `examples/traps/diagnostic_tiny_sample.*`
- `examples/traps/README.md`
- `docs/DIAGNOSTIC_CLAIMS.md`
- `docs/AUDIT_RULES.md`
- `README.md`
- `.github/workflows/ci.yml`
- `CHANGELOG.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Verified behavior:
- first-party QQ specs require a supported fitted reference line
- severe QQ outer-tail departure warns against overconfident normality wording
- obvious monotonic or broad curved residual structure warns against “no pattern” claims
- fewer than five complete diagnostic observations block interpretation
- nonnumeric fitted values fail without entering residual correlation calculations
- statistical intent metadata is limited to QQ, ECDF, and residual specs, preserving older `usermeta` contracts

Deterministic boundaries:
- QQ tail warning: maximum outer-20% departure at least 0.8 sample standard deviations
- residual warning: absolute fitted/residual correlation at least 0.5 or ordered-thirds mean shift at least 1 residual standard deviation
- diagnostic sample gate: FAIL below 5, WARN for 5-19, PASS at 20+

Remaining risks:
- thresholds catch obvious tail, monotonic, and broad curved structure but do not exhaust heteroskedasticity, autocorrelation, leverage, or every model diagnostic failure
- QQ checks are visual-contract guardrails, not formal normality tests
- first-party statistical spec semantics require `usermeta.chart_contract_intent`

Next safest task:
- Review draft PR #5 and squash-merge if the thresholds and REVIEW-versus-BLOCK split are acceptable.

2026-07-12 - Add statistical diagnostic plots

Environment:
- Working directory: isolated statistical helper reconstruction plus GitHub branch publication
- Python: system Python with pandas and pytest for pure preparation helpers

Commands:
- `PYTHONPATH=src pytest -q tests/test_statistics.py` -> PASSED (`5 passed` in the local helper reconstruction)
- `python -m py_compile src/chart_contract/statistics.py src/chart_contract/statistical_audit.py src/chart_contract/chart.py src/chart_contract/renderers/altair.py` -> PASSED for locally available sources
- GitHub Actions CI -> PASSED (pytest and all three CLI gate smoke checks)

Changed files:
- `src/chart_contract/chart.py`
- `src/chart_contract/statistics.py`
- `src/chart_contract/statistical_audit.py`
- `src/chart_contract/renderers/altair.py`
- `tests/test_statistical_intents.py`
- `examples/statistical_diagnostics.py`
- `README.md`
- `docs/AUDIT_RULES.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `artifacts/SPEC.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Verified locally:
- normal-reference QQ points are ordered and include fitted reference endpoints
- grouped QQ preparation preserves group identity
- ECDF records start at zero and reach one for each group
- unsupported QQ reference distributions fail deterministically

Remaining risks:
- GitHub Actions exercised the Altair rendering paths and full repository suite successfully.
- The slice intentionally supports only a normal QQ reference distribution.

Next safest task:
- Review draft PR #4 and keep the normal-reference-only QQ boundary explicit before merge.

2026-07-11 - Close audit blind spots

Environment:
- Working directory: isolated reconstruction of the current `main` package sources
- Python: system Python with current pandas/Altair and pytest

Commands:
- `PYTHONPATH=src pytest -q tests/test_audit_spec.py tests/test_hidden_regressions.py` -> PASSED (`16 passed`)
- randomized malformed/spec-shape audit probe across 2,000 inputs -> PASSED (no exceptions)
- `python -m py_compile src/chart_contract/*.py src/chart_contract/renderers/*.py` -> PASSED
- GitHub Actions CI -> PASSED (pytest and all three CLI gate smoke checks)

Changed files:
- `src/chart_contract/audit.py`
- `src/chart_contract/contracts.py`
- `src/chart_contract/renderers/altair.py`
- `tests/test_audit_spec.py`
- `tests/test_hidden_regressions.py`
- `docs/AUDIT_RULES.md`
- `CHANGELOG.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Verified fixes:
- missing or non-numeric encoded fields now block spec audits, including shorthand encodings
- trend and distribution sample gates count complete/valid observations rather than raw rows
- the package's own layered trend specs receive trend completeness checks
- generated specs preserve audit metadata in `usermeta`
- numeric trend axes remain quantitatively spaced
- unsupported direct intents block before renderer failure
- data hashes and provenance text do not create false decoration warnings

Remaining risks:
- Layered spec inspection intentionally selects the first supported analytical layer rather than fully evaluating arbitrary multi-view composition.
- Browser-level visual rendering was not inspected in the isolated local reconstruction.

Next safest task:
- Review the draft PR diff and keep the PR in draft until the remaining layered-spec boundary is accepted.

2026-07-03 - Add distribution chart intents

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_distribution_intents.py -q` -> PASSED (`11 passed`)
- `./.venv/bin/python -m pytest tests/test_audit_spec.py -q` -> PASSED (`5 passed`)
- `./.venv/bin/python -m pytest tests/test_chart_intents.py -q` -> PASSED (`4 passed`)
- `./.venv/bin/python -m pytest -q` -> PASSED (`52 passed`)
- `./.venv/bin/python examples/distribution_charts.py` -> PASSED
- `./.venv/bin/python examples/bad_to_good_chart.py` -> PASSED
- `./.venv/bin/chart-contract --help` -> PASSED
- `git diff --check` -> PASSED

Changed files:
- `src/chart_contract/chart.py`
- `src/chart_contract/renderers/altair.py`
- `src/chart_contract/audit.py`
- `tests/test_distribution_intents.py`
- `tests/test_audit_spec.py`
- `tests/test_chart_intents.py`
- `examples/distribution_charts.py`
- `examples/output/histogram_chart.vl.json`
- `examples/output/boxplot_chart.vl.json`
- `examples/output/violin_chart.vl.json`
- `README.md`
- `docs/AUDIT_RULES.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `artifacts/SPEC.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The example scripts rewrite tracked output artifacts, so the working tree will still show those diffs until they are reviewed or intentionally committed.
- The distribution preview is intentionally separate from the v0.1 scope, so any follow-up work should keep that boundary explicit.

Next safest task:
- Review the generated output artifacts and decide whether to commit or keep iterating on the distribution preview.

2026-06-22 - Document `--fail-on` in CLI guidance

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest` -> PASSED (`40 passed`)
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `docs/AGENT_INTEGRATION.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The new `--fail-on` note is documentation-only and intentionally avoids changing gate behavior.
- The working tree still has unrelated example-output drift from earlier runs.

Next safest task:
- Commit the docs cleanup and push it if the branch looks good.

2026-06-22 - Version/docs consistency cleanup

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_cli.py -q` -> PASSED (`12 passed`)
- `./.venv/bin/chart-contract --version` -> PASSED (`chart-contract 0.2.0`)
- `./.venv/bin/python -m pytest` -> PASSED (`40 passed`)
- `git diff --check` -> PASSED

Changed files:
- `src/chart_contract/cli.py`
- `README.md`
- `tests/test_cli.py`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The version fallback now matches the release version, but any future bump should update the shared fallback constant too.
- The working tree still has unrelated example-output drift from earlier runs.

Next safest task:
- Commit the cleanup and push it if the branch looks good.

2026-06-22 - Strengthen GitHub Actions CLI smoke checks

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/chart-contract audit spec examples/traps/too_many_pie_categories.vl.json --data examples/traps/too_many_pie_categories.csv --claim "$(cat examples/traps/too_many_pie_categories.claim.txt)"` wrapped in `set +e` / `test "$exit_code" -eq 1` -> PASSED (`BLOCK`, exit 1)
- `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"` wrapped in `set +e` / `test "$exit_code" -eq 0` -> PASSED (`REVIEW`, exit 0)
- `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)" --warnings-as-errors` wrapped in `set +e` / `test "$exit_code" -ne 0` -> PASSED (`REVIEW`, exit 1)
- `./.venv/bin/python -m pytest` -> PASSED (`39 passed`)
- `git diff --check` -> PASSED

Changed files:
- `.github/workflows/ci.yml`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The workflow smoke checks depend on the trap fixtures remaining in sync with the audit semantics.
- The working tree still has unrelated example-output drift from earlier runs.

Next safest task:
- Commit the CI workflow update and push it if the branch looks good.

2026-06-22 - Fix single-point trend spec audits

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_audit_spec.py tests/test_cli_traps.py -q` -> PASSED (`7 passed`)
- `./.venv/bin/chart-contract audit spec examples/traps/single_point_trend.vl.json --data examples/traps/single_point_trend.csv --claim "$(cat examples/traps/single_point_trend.claim.txt)"` -> PASSED (`BLOCK`, exit 1, `data.trend.min_points`)
- `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"` -> PASSED (`REVIEW`, exit 0, `data.trend.min_points` PASS)
- `./.venv/bin/python -m pytest` -> PASSED (`39 passed`)
- `git diff --check` -> PASSED

Changed files:
- `src/chart_contract/audit.py`
- `tests/test_audit_spec.py`
- `tests/test_cli_traps.py`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The release branch still has unrelated example-output drift in the working tree from earlier runs.
- The trend detection only covers simple line specs with explicit x and y encodings; that is intentional for the v0.2 gate.

Next safest task:
- Commit the trend-spec fix and push it if the branch looks good.

2026-06-22 - Prepare v0.2.0 release

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pip install -e ".[dev]"` -> PASSED (`chart-contract==0.2.0`)
- `./.venv/bin/chart-contract --version` -> PASSED (`chart-contract 0.2.0`)
- `./.venv/bin/python -m pytest` -> PASSED (`36 passed`)
- `./.venv/bin/python examples/bad_to_good_chart.py` -> PASSED
- `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"` -> PASSED (`REVIEW`, exit 0)
- `git diff --check` -> PASSED

Changed files:
- `pyproject.toml`
- `CHANGELOG.md`
- `README.md`
- `ROADMAP.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The example script rewrites tracked output artifacts, so the working tree still contains unrelated example-output drift.
- The release prep does not add any new runtime behavior; it only packages and documents the v0.2.0 gate.

Next safest task:
- Commit the release prep and push it if the branch looks good.

2026-06-22 - Document v0.2 agent gate workflow

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pip install -e ".[dev]"` -> PASSED
- `./.venv/bin/python -m pytest` -> PASSED (`36 passed`)
- `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"` -> PASSED (`REVIEW`, exit 0)
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `docs/AGENT_INTEGRATION.md`
- `ROADMAP.md`
- `.github/workflows/ci.yml`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`
