# HANDOFF

## Resume Packet

- Goal: make numerator, denominator, cohort identity, and denominator-basis consistency auditable for ratio-like analytical metrics.
- Branch: `agent/denominator-cohort-contract`.
- Base: `main` at `f8dc6151453053ad193fa255d4b5d8655b4ccb1d`.
- Pull request: #20 (`feat: add denominator and cohort contracts`).
- Current slice: first-party API fields, closed v1 ratio metadata, chart/spec audits, mixed-denominator CLI trap, two new profile rules, tests, docs, and refreshed proof artifacts.
- Read first: `src/chart_contract/ratio.py`, `src/chart_contract/ratio_audit.py`, `tests/test_ratio_contract.py`, and `docs/RATIO_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept:
  - `numerator`
  - `denominator`
  - optional `cohort`
  - optional `denominator_basis_field`
- Missing denominator semantics on recognized ratio-like units produces `contract.ratio.denominator=WARN`.
- Declared contracts are closed version 1 and bind `metric_field`, numerator, denominator, cohort, and denominator basis field.
- Partial/malformed/extra-field contracts fail.
- Spec contracts must bind to a quantitative field actually shown by the audited spec.
- First-party renderers preserve `usermeta.ratio_contract` only for the supported v1 metric intents.
- A denominator basis field is checked across every supplied row for presence, non-null/non-empty string identity, invariance, and exact agreement with the declared denominator.
- Mixed identities such as `visitors` / `signups` fail `data.ratio.denominator_basis`.
- Different denominator numeric sizes are not a failure; version 1 audits denominator meaning, not magnitude.
- `cohort` is descriptive identity only and is not parsed or validated as row membership.
- `value_representation` remains the independent percent-scaling contract.
- `examples/traps/mixed_denominator_basis.*` demonstrates a renderable comparison that blocks solely because denominator meaning changes across rows.
- The `audit-v0.2` profile now contains 65 rules.

## Important Decisions

- Missing denominator identity is REVIEW; contradictory or malformed declared identity is BLOCK.
- No numerator/denominator identity is inferred from field names, source names, claim text, or value ranges.
- An explicit ratio contract is allowed even when the unit string is nonstandard and not recognized by the heuristic.
- Row-level denominator basis stores semantic labels, not counts.
- The v1 first-party contract is deliberately scoped to `trend`, `rank`, and `compare`; distributions do not emit or require it.
- Ratio metadata does not recompute or validate upstream arithmetic.
- Cohort prose is preserved for inspectability but not treated as machine-verified population membership.
- Existing filters remain the explicit surface for chart filter/window declarations.
- Older schema-0.4 reports become stale-policy artifacts because two new rules change profile semantic identity.

## Verification

Initial CI run #230 failed because five legacy READY fixtures used `conversion rate` / `rate` without declaring what the metric was of.

Those fixtures were corrected to declare actual numerator/denominator identity rather than weakening the new policy.

GitHub Actions CI run #236 (`37475378812`) then passed on code-bearing head `2fb9889dd3c65a25ed1127f02cd8fd2de8746bc9`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all prior CLI trap paths -> PASSED
- `mixed_denominator_basis` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- The v1 contract does not carry numeric numerator/denominator values, so it cannot replay the rate arithmetic.
- A malicious or mistaken upstream producer can label all rows with the same denominator identity even when source construction differs; this contract detects declared semantic inconsistency, not hidden upstream fraud.
- The recognized unit heuristic is intentionally conservative and does not attempt to classify every possible `per ...` unit.
- Cohort identity has no canonical ontology in v1.
- External specs can carry ratio metadata for broader quantitative shapes, but first-party API enforcement remains intentionally narrower.

## Next Recommended Task

- Confirm final PR #20 CI remains green after VERIFY/HANDOFF.
- Merge if the REVIEW-on-missing / BLOCK-on-contradiction policy and closed v1 schema match the intended semantics.
- Keep ratio arithmetic verification, time-varying denominator populations, and cohort equivalence as separate future work.
