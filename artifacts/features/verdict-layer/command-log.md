# Command Log

## Skill / Prompt Trail

| Step | Invocation | Purpose | Output |
| --- | --- | --- | --- |
| 1 | `$wedge-before-build` | Identify the next v0.1-safe feature wedge | Recommendation: deterministic pre-share verdict layer |
| 2 | `$mini-spec` | Turn the wedge into a compact spec | `artifacts/features/verdict-layer/SPEC.md` |
| 3 | `$build-one` | Implement exactly one slice | `src/chart_contract/audit.py`, `tests/test_audit_rules.py` |
| 4 | `$verify-contract` | Record evidence and remaining risks | `artifacts/features/verdict-layer/VERIFY.md` |
| 5 | follow-up artifact cleanup request | Move feature artifacts out of repo-wide files | `artifacts/features/verdict-layer/README.md`, `HANDOFF.md`, `TODO.md`, `command-log.md` |

## Shell Command Trail

Commands run during implementation and cleanup:

- `python3 -m pytest`
- `python3 examples/bad_to_good_chart.py`
- `git diff --check`
- `git checkout -b codex/pre-share-verdict-layer`
- `git commit -m "Add pre-share verdict layer"`
- `git push -u origin codex/pre-share-verdict-layer`
- `git restore --source=origin/main artifacts/SPEC.md artifacts/TODO.md artifacts/HANDOFF.md artifacts/VERIFY.md`

## Notes

- The repo-wide artifact files remain the durable top-level project record.
- This folder keeps the feature-specific planning trail together so future feature work can follow the same pattern without clobbering root artifacts.
