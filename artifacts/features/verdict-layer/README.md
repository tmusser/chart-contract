# Verdict Layer

This is a feature-level README artifact for the pre-share verdict layer.

## Problem

`chart-contract` findings are inspectable, but a reviewer or AI agent still has to translate raw `PASS` / `WARN` / `FAIL` output into a share decision.

## Proposed Wedge

Add a deterministic verdict on top of existing findings:

- `BLOCK` when any finding is `FAIL`
- `REVIEW` when there are warnings and no failures
- `READY` when all findings are `PASS`

## Why It Fits v0.1

- No new chart intents
- No auto-fix behavior
- No UI or publishing workflow
- No changes to the underlying audit rules

## Smallest Useful Surface

- `report.verdict`
- `report.verdict_summary()`
- serialized verdict fields in `report.to_dict()`
- verdict shown in markdown audit output

## Proof

- Code: `src/chart_contract/audit.py`
- Tests: `tests/test_audit_rules.py`
- Example artifact: `examples/output/bad_chart_audit.md`

## Feature Audit Trail

- `SPEC.md`
- `TODO.md`
- `VERIFY.md`
- `HANDOFF.md`
- `command-log.md`
