# VERIFY

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
