# HANDOFF

RESUME PACKET

- Goal: keep `chart-contract` stable at v0.1 while building out the v0.2 agent gate in small, auditable slices.
- Workflow State: the roadmap names `v0.2.0 — Agent Gate`; the CLI now supports text, JSON, and Markdown report output, `--out`, `--markdown`, verdict-based exit codes, runnable CLI trap fixtures under `examples/traps/`, and the README/CI now point at the CLI gate as the front door.
- Branch: `main`
- Next task: push the docs/CI update or move on to the next planned slice.
- Verification: `./.venv/bin/python -m pip install -e ".[dev]"`, `./.venv/bin/chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json --data examples/traps/causal_claim_missing_caveat.csv --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"`, and `./.venv/bin/python -m pytest`
- Read first: `ROADMAP.md`, `README.md`, `docs/AGENT_INTEGRATION.md`, `artifacts/VERIFY.md`

## Current Repo State

- The v0.1 scope in `artifacts/SPEC.md` remains unchanged.
- The v0.2.0 roadmap is now explicit and commit-shaped.
- Report serialization is hardened for CLI use, and the CLI now loads specs/data from disk, emits multiple report formats, and writes file outputs when requested.
- The v0.2 trap fixtures are file-based and runnable from the CLI, with separate spec, data, and claim files for easy inspection.
- The README now advertises the CLI audit gate, and CI runs a trap smoke check in addition to pytest.

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

## Next Recommended Task

Use the roadmap and agent-integration docs as the source of truth for the next implementation slice.
