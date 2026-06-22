# HANDOFF

RESUME PACKET

- Goal: keep `chart-contract` stable at v0.1 while building out the v0.2 agent gate in small, auditable slices.
- Workflow State: the roadmap names `v0.2.0 — Agent Gate`; the package now has a CLI skeleton with `chart-contract`, `python -m chart_contract`, and `audit spec` parsing.
- Branch: `main`
- Next task: implement the `chart-contract audit spec` execution path in the smallest possible slice, starting with spec loading from disk.
- Verification: `./.venv/bin/python -m pytest tests/test_cli.py` and `./.venv/bin/python -m pytest`
- Read first: `ROADMAP.md`, `docs/AGENT_INTEGRATION.md`, `artifacts/VERIFY.md`

## Current Repo State

- The v0.1 scope in `artifacts/SPEC.md` remains unchanged.
- The v0.2.0 roadmap is now explicit and commit-shaped.
- Report serialization is hardened for CLI use, and the CLI shell is wired without audit execution.

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

## Next Recommended Task

Use the roadmap and agent-integration docs as the source of truth for the next implementation slice.
