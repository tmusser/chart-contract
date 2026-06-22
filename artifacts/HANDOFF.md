# HANDOFF

RESUME PACKET

- Goal: keep `chart-contract` stable at v0.1 while building out the v0.2 agent gate in small, auditable slices.
- Workflow State: the CLI docs now mention `--fail-on READY|REVIEW|BLOCK` in addition to `--warnings-as-errors`, and the wording stays careful about `READY` as an explicit threshold.
- Branch: `main`
- Next task: commit the docs cleanup and push it if the branch looks good.
- Verification: `./.venv/bin/python -m pytest`, `./.venv/bin/chart-contract --version`, and `git diff --check`
- Read first: `README.md`, `docs/AGENT_INTEGRATION.md`, `artifacts/VERIFY.md`

## Current Repo State

- The v0.1 scope in `artifacts/SPEC.md` remains unchanged.
- The v0.2.0 roadmap is now explicit and commit-shaped.
- The package version is bumped to 0.2.0 and the changelog calls out the shipped gate surface.
- Report serialization is hardened for CLI use, and the CLI now loads specs/data from disk, emits multiple report formats, and writes file outputs when requested.
- The v0.2 trap fixtures are file-based and runnable from the CLI, with separate spec, data, and claim files for easy inspection.
- The README now advertises the CLI audit gate, and CI runs a trap smoke check in addition to pytest.
- The trend-spec audit now matches the chart-level trend rule for simple line specs, so the single-point trap is BLOCK again.
- The CI workflow now explicitly checks that BLOCK exits 1 and that `--warnings-as-errors` turns REVIEW into a nonzero exit.
- `report.verdict` is now spelled out in the README as the authoritative gate field, and `report.passed` is documented as a no-FAIL signal.
- The `--fail-on` flag is now briefly documented so users do not have to discover it only through `--help`.

## Working Commands

- `git diff --check`
- `./.venv/bin/python -m pytest tests/test_cli.py`
- `./.venv/bin/python -m pytest`
- `sed -n '1,260p' ROADMAP.md`
- `sed -n '1,220p' docs/AGENT_INTEGRATION.md`

## Important Decisions

- Keep v0.2.0 concrete enough that each slice can become a commit.
- Preserve the v0.1 and later-roadmap context while avoiding v0.3 drift.
- Do not add ChartContract, auto-correction, or extra chart intents in this slice.
- Use `schema_version: "0.2"` in serialization output as the CLI-facing contract anchor.
- Use verdict names for `--fail-on` so the future exit-code mapping stays aligned with `AuditReport.verdict`.
- Keep stdout text as the default surface unless `--out` switches it to a one-line verdict summary.
- Keep trap fixtures tiny and synthetic so they stay inspectable and easy to copy-paste.
- Keep the CI smoke check on a REVIEW fixture so it stays a passing gate while still exercising the CLI front door.
- Keep the release notes aligned with the actual CLI behavior so `0.2.0` stays a truthful cut.
- Mirror chart-level trend completeness checks in spec-audit code whenever line specs are treated as trend-like.
- When adding CI smoke checks, assert the exit code explicitly instead of relying on output alone.
- Keep docs wording version-neutral when the release version has already advanced.
- Keep public CLI flags like `--fail-on` documented in the agent guidance when they are exposed in `--help`.

## Next Recommended Task

Use the roadmap and agent-integration docs as the source of truth for the next implementation slice.
