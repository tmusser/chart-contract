# VERIFY

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

Remaining risks:
- The CI smoke step exercises a REVIEW trap, not a BLOCK trap; the pytest suite covers the BLOCK path.
- Existing example output files still have unrelated working-tree drift from earlier runs.

Next safest task:
- Push the docs/CI update and then move on to the next planned slice.

2026-06-22 - Add runnable CLI trap fixtures

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m chart_contract audit spec examples/traps/too_many_pie_categories.vl.json --data examples/traps/too_many_pie_categories.csv --claim "$(cat examples/traps/too_many_pie_categories.claim.txt)"` -> PASSED (`BLOCK`, exit 1, `visual.arc.category_count`)
- `./.venv/bin/python -m chart_contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"` -> PASSED (`REVIEW`, exit 0, `claim.causal_support`)
- `./.venv/bin/python -m chart_contract audit spec examples/traps/single_point_trend.vl.json --data examples/traps/single_point_trend.csv --claim "$(cat examples/traps/single_point_trend.claim.txt)"` -> PASSED (`READY`, exit 0)
- `./.venv/bin/python -m pytest tests/test_cli_traps.py` -> PASSED (`2 passed`)
- `./.venv/bin/python -m pytest` -> PASSED (`36 passed`)
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `examples/traps/README.md`
- `examples/traps/too_many_pie_categories.vl.json`
- `examples/traps/too_many_pie_categories.csv`
- `examples/traps/too_many_pie_categories.claim.txt`
- `examples/traps/causal_claim_missing_caveat.vl.json`
- `examples/traps/causal_claim_missing_caveat.csv`
- `examples/traps/causal_claim_missing_caveat.claim.txt`
- `examples/traps/missing_source_or_unit.vl.json`
- `examples/traps/missing_source_or_unit.csv`
- `examples/traps/missing_source_or_unit.claim.txt`
- `examples/traps/single_point_trend.vl.json`
- `examples/traps/single_point_trend.csv`
- `examples/traps/single_point_trend.claim.txt`
- `tests/test_cli_traps.py`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The claim text still has to be passed explicitly on the CLI; the fixtures do not auto-wire claim files.
- The traps are synthetic and only exercise the current gate rules, not new semantics.

Next safest task:
- Add any remaining v0.2 gate documentation or proceed to the next planned slice.

2026-06-22 - CLI audit report outputs and exit codes

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_cli.py` -> PASSED (`11 passed`)
- `./.venv/bin/python -m pytest` -> PASSED (`34 passed`)
- `git diff --check` -> PASSED

Changed files:
- `src/chart_contract/cli.py`
- `tests/test_cli.py`
- `docs/AGENT_INTEGRATION.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The CLI does not auto-create output directories; file writes still require valid parent paths.
- Existing example output JSON/Markdown files still have unrelated working-tree drift from earlier runs.

Next safest task:
- Decide whether to keep this CLI slice focused or add copy-paste README examples for `--out` and `--markdown`.

2026-06-22 - Audit Vega-Lite specs from disk

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_cli.py` -> PASSED (`10 passed`)
- `./.venv/bin/python -m pytest` -> PASSED (`33 passed`)
- `git diff --check` -> PASSED

Changed files:
- `pyproject.toml`
- `src/chart_contract/cli.py`
- `src/chart_contract/__main__.py`
- `tests/test_cli.py`
- `tests/fixtures/cli/ready_chart.vl.json`
- `tests/fixtures/cli/review_chart.vl.json`
- `tests/fixtures/cli/bad_arc_chart.vl.json`
- `tests/fixtures/cli/segments.csv`
- `tests/fixtures/cli/segments.json`
- `docs/AGENT_INTEGRATION.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- `--out` and `--markdown` are still parsed but not wired to file output.
- Existing example output JSON/Markdown files still have unrelated working-tree drift from earlier pytest runs.

Next safest task:
- Wire `--out` and `--markdown` to write reports to disk, keeping stdout text output as the default.

2026-06-22 - Add CLI skeleton

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_cli.py` -> PASSED (`6 passed`)
- `./.venv/bin/python -m pytest` -> PASSED (`29 passed`)
- `git diff --check` -> PASSED

Changed files:
- `pyproject.toml`
- `src/chart_contract/cli.py`
- `src/chart_contract/__main__.py`
- `tests/test_cli.py`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The CLI still stubs out audit execution; it only parses the v0.2 surface for now.
- Example output JSON files still have unrelated pre-existing working-tree drift from earlier runs.

Next safest task:
- Implement the `chart-contract audit spec` execution path in one small slice, starting with disk-based spec loading.

2026-06-22 - Stabilize report serialization

Environment:
- Working directory: repo root

Commands:
- `./.venv/bin/python -m pytest tests/test_audit_report.py tests/test_audit_rules.py tests/test_import.py` -> PASSED (`17 passed`)
- `git diff --check` -> PASSED

Changed files:
- `src/chart_contract/audit.py`
- `tests/test_audit_report.py`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- Example output JSON files still have unrelated pre-existing working-tree drift from earlier runs.
- CLI output and exit-code behavior are still future work for the v0.2 gate slice.

Next safest task:
- Start the v0.2 CLI slice with disk-based spec loading and explicit claim input.

2026-06-22 - Define v0.2.0 agent gate scope

Environment:
- Working directory: repo root

Commands:
- `sed -n '1,260p' ROADMAP.md` -> PASSED
- `sed -n '1,220p' docs/AGENT_INTEGRATION.md` -> PASSED
- `git diff --check` -> PASSED

Changed files:
- `ROADMAP.md`
- `README.md`
- `docs/AGENT_INTEGRATION.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- The v0.2.0 gate is now explicit in docs, but the CLI itself is still future work.
- Exit-code mappings and fixture details remain to be implemented in code.

Next safest task:
- Implement the v0.2.0 CLI in one small slice at a time, starting with disk-based spec loading.

2026-06-19 - Suite reference cleanup for context-to-action-skills

Environment:
- Working directory: repo root

Commands:
- `grep -R "ai-business-skills\\|business-skills\\|ai business skills\\|context-to-action-skills" -n . --exclude-dir=.git --exclude-dir=__pycache__ --exclude="*.svg" --exclude="*.png" --exclude="*.gif" || true` -> PASSED; identified stale references in README.md, docs/SUITE_MAP.md, artifacts/VERIFY.md, docs/AGENT_WORKFLOW_CASE_STUDY.md, and generated metadata
- `grep -R "Part of the Suite\\|Companion Artifact\\|suite map\\|companion" -n README.md docs artifacts examples .github 2>/dev/null || true` -> PASSED
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `docs/SUITE_MAP.md`
- `docs/AGENT_WORKFLOW_CASE_STUDY.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- Historical verification entries still preserve the former repo name as an audit trail.
- Generated package metadata may still carry the old name until a dedicated build-artifact refresh is warranted.

Next safest task:
- Keep future suite-branding edits paired between the README and suite map so the positioning stays consistent.

2026-06-15 - Add README verdict usage note on main

Environment:
- Working directory: repo root

Commands:
- `grep -n "report.verdict\|READY means\|REVIEW means\|BLOCK means" README.md` -> PASSED
- `git diff -- README.md` -> PASSED
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Remaining risks:
- This is a README-only discoverability patch; no product behavior changed.

Next safest task:
- Keep future verdict-layer documentation updates small and explicit now that the feature is already merged.

2026-06-15 - Relocate verdict-layer planning artifacts

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- `python3 -m pytest` -> PASSED (`19 passed`, `213 warnings`)
- `python3 examples/bad_to_good_chart.py` -> PASSED
- `git diff --check` -> PASSED

Changed files:
- `artifacts/features/verdict-layer/README.md`
- `artifacts/features/verdict-layer/SPEC.md`
- `artifacts/features/verdict-layer/TODO.md`
- `artifacts/features/verdict-layer/VERIFY.md`
- `artifacts/features/verdict-layer/HANDOFF.md`
- `artifacts/features/verdict-layer/command-log.md`
- `artifacts/SPEC.md`
- `artifacts/TODO.md`
- `artifacts/HANDOFF.md`
- `artifacts/VERIFY.md`

Remaining risks:
- The feature artifact trail is now isolated, but the verdict surface is still not advertised in public docs.
- Altair/jsonschema deprecation warnings still appear during pytest, though tests pass.

Next safest task:
- Add one tiny public usage example for `report.verdict` after merge if discoverability matters more than branch cleanliness.

2026-06-10 - README hero image and dogfood note

Commands:
- `git diff --check` -> PASSED
- README relative link/image check -> PASSED

Changed files:
- `README.md`
- `artifacts/VERIFY.md`

Remaining risks:
- None for product behavior; this patch is README-only.

Next safest task:
- Tag v0.1.0 or move future work to v0.2.

2026-06-10 - Single-point trend audit fix

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- `python3 -m pytest` -> PASSED (`16 passed`)
- `python3 examples/bad_to_good_chart.py` -> PASSED
- `git diff --check` -> PASSED
- local-path grep checks -> PASSED with no tracked leaks found
- file-URL grep checks -> PASSED with no tracked leaks found
- one-row trend smoke check -> PASSED (`data.trend.min_points: FAIL`, `passed: False`)

Changed files:
- `src/chart_contract/audit.py`
- `tests/test_audit_rules.py`
- `artifacts/VERIFY.md`
- `artifacts/BUILD_MANIFEST.md`
- `artifacts/build_manifest.json`

Remaining risks:
- Percent-unit vs decimal-scale mismatch remains a v0.2 policy decision.
- `audit_spec()` remains intentionally experimental.

Next safest task:
- Declare v0.1 patched, then move future ergonomics work such as scaffold generation into v0.2.

2026-06-10 - Final v0.1 first-impression polish

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- `python3 -m pip install -e '.[dev]'` -> PASSED
- `python3 examples/bad_to_good_chart.py` -> PASSED; static SVG export succeeded
- `python3 -m pytest` -> PASSED (`14 passed`)
- `git diff --check` -> PASSED
- local-path grep check across public docs/source tree -> PASSED with no matches
- `grep -R file-URL -n README.md docs artifacts src tests examples || true` -> PASSED with no matches
- README link validation -> PASSED

Changed files:
- `README.md`
- `examples/bad_to_good_chart.py`
- `examples/output/bad_chart_audit.md`
- `examples/output/bad_chart_audit.json`
- `examples/output/bad_chart.svg`
- `examples/output/corrected_chart.svg`
- `examples/output/corrected_chart.vl.json`
- `pyproject.toml`
- `artifacts/BUILD_MANIFEST.md`
- `artifacts/build_manifest.json`
- `artifacts/VERIFY.md`

Remaining risks:
- Static SVG export is now committed, but browser-level rendering is still unverified.
- `audit_spec()` remains intentionally experimental.

Next safest task:
- Keep v0.1 scope fixed and only revisit renderer/export compatibility if dependency drift changes the demo outputs.

2026-06-10 - Proof artifact polish

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- `python3 -m pytest` -> PASSED (`14 passed`)
- `git diff --check` -> PASSED
- README/case-study/manifest link check -> PASSED
- Manifest verification count sync check -> PASSED

Changed files:
- `README.md`
- `docs/AGENT_WORKFLOW_CASE_STUDY.md`
- `artifacts/BUILD_MANIFEST.md`
- `artifacts/build_manifest.json`
- `artifacts/VERIFY.md`

Remaining risks:
- Visual verification remains limited to spec generation unless rendered chart export is added later.
- `audit_spec()` remains intentionally experimental.

Next safest task:
- Add the v0.2 CLI only after keeping v0.1 chart intents and renderer scope fixed.

2026-06-10 - Public path cleanup patch

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- local-path leak grep across public docs/source tree -> PASSED with no matches
- `python3 -m pip install -e '.[dev]'` -> PASSED
- `python3 examples/bad_to_good_chart.py` -> PASSED
- `python3 -m pytest` -> PASSED (`14 passed`)
- `git diff --check` -> PASSED

Changed files:
- `README.md`
- `docs/VISUAL_CONTRACT.md`
- `artifacts/VERIFY.md`

Deferred items:
- Rendered README screenshots remain deferred because the patch intentionally avoids heavyweight export dependencies.

Remaining risks:
- The generated editable-install metadata can still be recreated transiently by `pip install -e`, but the tracked docs and source files no longer contain local filesystem paths.

Next safest task:
- Commit and push this cleanup patch if you want it published, then consider whether to keep or remove the earlier public-facing polish patch from the branch history.

2026-06-10 - Public-facing polish patch

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Commands:
- `python3 -m pip install -e '.[dev]'` -> PASSED
- `python3 examples/bad_to_good_chart.py` -> PASSED
- `python3 -m pytest` -> PASSED (`14 passed`)
- `git diff --check` -> PASSED

Changed files:
- `pyproject.toml`
- `LICENSE`
- `ROADMAP.md`
- `README.md`
- `docs/VISUAL_CONTRACT.md`
- `src/chart_contract/audit.py`
- `tests/test_audit_rules.py`
- `.github/workflows/ci.yml`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`

Deferred items:
- Rendered README chart artifact export was not added because lightweight SVG/PNG export tooling is not currently installed, and this patch intentionally avoids heavy new dependencies.

Remaining risks:
- CI currently exercises one Python version (`3.11`) rather than a broader compatibility matrix.
- Altair-related deprecation warnings still appear in local pytest output.

Next safest task:
- Decide whether to commit and push this polish patch, then consider a small CI compatibility follow-up.

2026-06-10 - Build `chart-contract` v0.1

Environment:
- Working directory: repo root
- Python: `Python 3.12.4`

Scope freezes used:
- Slice 1: repo skeleton and planning artifacts
- Slice 2: core models, audit rules, and renderer
- Slice 3: examples, README, docs, and example execution coverage

Commands:
- `python3 -m pip install -e '.[dev]'` -> PASSED
  Note: pip reported an existing environment conflict warning for `spyder`/`ipython`, but the editable install completed successfully.
- `python3 -m pytest tests/test_import.py tests/test_audit_rules.py tests/test_chart_intents.py tests/test_audit_spec.py` -> PASSED (`10 passed`)
- `python3 -m pytest` -> PASSED (`11 passed`)
- `python3 examples/bad_to_good_chart.py` -> PASSED
- `python3 examples/trend_claim.py` -> PASSED
- `python3 examples/rank_claim.py` -> PASSED
- `python3 examples/compare_claim.py` -> PASSED
- `git diff --check` -> PASSED
- Structural validation inline Python check -> PASSED
  Checks: expected files exist, package imports, build manifests exist, README mentions `ai-engineering-skills`, README mentions `ai-business-skills`, README front-door intents remain `trend` / `rank` / `compare`

Changed files:
- `README.md`
- `AGENTS.md`
- `pyproject.toml`
- `src/chart_contract/__init__.py`
- `src/chart_contract/chart.py`
- `src/chart_contract/audit.py`
- `src/chart_contract/contracts.py`
- `src/chart_contract/renderers/__init__.py`
- `src/chart_contract/renderers/altair.py`
- `tests/test_import.py`
- `tests/test_audit_rules.py`
- `tests/test_chart_intents.py`
- `tests/test_audit_spec.py`
- `examples/bad_to_good_chart.py`
- `examples/trend_claim.py`
- `examples/rank_claim.py`
- `examples/compare_claim.py`
- `examples/output/corrected_chart.vl.json`
- `examples/output/trend_claim.vl.json`
- `examples/output/rank_claim.vl.json`
- `examples/output/compare_claim.vl.json`
- `docs/WHY.md`
- `docs/VISUAL_CONTRACT.md`
- `docs/DESIGN_PRINCIPLES.md`
- `docs/AGENT_WORKFLOW_CASE_STUDY.md`
- `artifacts/SPEC.md`
- `artifacts/PLAN.md`
- `artifacts/TODO.md`
- `artifacts/VERIFY.md`
- `artifacts/HANDOFF.md`
- `artifacts/CREATION_INVOCATIONS.md`
- `artifacts/BUILD_MANIFEST.md`
- `artifacts/build_manifest.json`

Not tested:
- Visual rendering in a browser beyond Vega-Lite/Altair spec generation
- CI matrix behavior across multiple Altair and pandas versions

Remaining risks:
- `audit_spec()` is intentionally experimental and limited to deterministic Vega-Lite-like checks.
- Altair emits deprecation warnings through current dependencies during tests, though all specs generated successfully.

Next safest task:
- Add CI coverage that pins and validates Altair/pandas compatibility while keeping the v0.1 scope fixed.
