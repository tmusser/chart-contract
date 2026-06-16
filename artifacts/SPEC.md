# SPEC

## Objective

Add a deterministic pre-share verdict layer to `chart-contract` so analysts and AI agents can tell whether a chart is ready to share without interpreting raw findings first.

## User / Use Case

- Analysts reviewing a draft chart before sharing it in a doc, deck, or Slack thread.
- AI agents generating a draft chart that must stop, warn, or proceed based on audit output.

## Acceptance Criteria

- A report with any `FAIL` finding yields a `BLOCK` verdict.
- A report with no `FAIL` findings and at least one `WARN` finding yields a `REVIEW` verdict.
- A report with only `PASS` findings yields a `READY` verdict.
- The verdict output includes a short human-readable summary plus PASS/WARN/FAIL counts.
- The underlying audit findings remain fully inspectable; the verdict is a thin layer, not a replacement.
- The behavior is deterministic and covered by focused tests.

## Non-Goals

- No new chart intents beyond `trend`, `rank`, and `compare`.
- No UI, dashboard, CLI, or publishing workflow.
- No LLM calls, auto-fix loops, or automatic chart correction.
- No changes to renderer behavior beyond existing Altair/Vega-Lite output.
- No replacement for human review on nuanced or domain-specific claims.

## Constraints

- Preserve the v0.1 scope of `chart-contract` as a claim-first audit harness.
- Keep warnings explainable and rule-driven.
- Do not change `audit_spec()` semantics unless needed for consistency.
- Do not fetch or mutate external data.
- Prefer the smallest public surface that solves the pre-share decision problem.

## Run / Test / Verification Commands

- `python3 -m pytest`
- `python3 examples/bad_to_good_chart.py`
- `git diff --check`

## Project Structure Sketch

- `src/chart_contract/audit.py`
  Add the verdict mapping close to `AuditReport` and finding summaries.
- `tests/test_audit_rules.py`
  Add deterministic verdict coverage for PASS-only, WARN-only, and FAIL cases.
- `README.md` or `docs/`
  Optional follow-up only if the new surface needs one short usage example.

## Smallest Verification Demo

Show three reports:

1. a clean chart audit that returns `READY`
2. a warning-only chart audit that returns `REVIEW`
3. a failing chart audit that returns `BLOCK`

The demo is successful if the verdict and counts match the findings exactly.

## Open Questions

- Should the verdict live as an `AuditReport` property or a small helper method on the report model?
- Should `audit_spec()` reports get the same verdict surface immediately, or should v0.1 keep the first slice focused on chart audits?
- What is the smallest wording that feels operational without sounding like compliance language?
