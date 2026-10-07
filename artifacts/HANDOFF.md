# HANDOFF

## Resume Packet

- Goal: make baseline identity and comparison arithmetic explicit for trend/compare claims.
- Branch: `agent/comparison-baseline-contract`.
- Base: `main` at `bffef92074de321e286a346f57e59f44e4559360`.
- Pull request: #21 (`feat: add comparison baseline contracts`).
- Current slice: first-party comparison API fields, closed v1 comparison receipts, chart/spec audits, narrow claim-language parity, percent-vs-percentage-points CLI trap, four new profile rules, tests, and docs.
- Read first: `src/chart_contract/comparison.py`, `src/chart_contract/comparison_audit.py`, `tests/test_comparison_contract.py`, and `docs/COMPARISON_CONTRACT.md`.

## Current Repo State

- `Chart.trend()` and `Chart.compare()` accept:
  - `baseline_field`
  - `baseline_value`
  - `target_value`
  - `change_type`
  - `declared_change`
- Supported change types:
  - `absolute`
  - `percentage_points`
  - `percent_change`
  - `ratio`
- First-party v1 baseline fields must be visible `x` or `group` dimensions.
- Each baseline/target selector must resolve to exactly one finite numeric metric observation.
- Percent change computes `((target - baseline) / baseline) * 100`.
- Ratio computes `target / baseline`.
- Both block on zero baseline.
- Percentage-point arithmetic respects existing percent `value_representation`.
- First-party specs stamp baseline/target metric values and recomputed change into `usermeta.comparison_contract`.
- Spec audits recompute those receipts from supplied evidence and block stale or inconsistent metadata.
- Renderer refuses internally inconsistent declared changes instead of emitting stale receipts.
- Narrow claim parsing recognizes explicit numeric percent, percentage-point, and x/times phrases and requires them to match the contract.
- Missing baseline metadata for such explicit numeric wording produces REVIEW.
- Selector identity is typed and exact; v1 does not silently coerce CSV-inferred numbers to strings or vice versa.
- `examples/traps/percent_vs_percentage_points.*` demonstrates correct arithmetic with false claim semantics.
- The `audit-v0.2` profile now contains 69 rules.

## Important Decisions

- No hidden “previous row” or visual-order baseline.
- No automatic baseline choice.
- One visible selector field only in v1; composite-key selection is deferred.
- Stored comparison values are reproducible receipts, not approval of baseline choice.
- Percentage points and percent change remain distinct even when both involve percent-valued data.
- Claim parsing is intentionally narrow; open-ended language interpretation remains out of scope.
- Exact explicit claim values must match the contract; no implicit rounding tolerance beyond floating-point equality tolerance.
- General analytical comparability (seasonality, cohort drift, confounding) is outside this arithmetic contract.
- Older schema-0.4 reports become stale-policy artifacts because four new comparison rules change profile semantic identity.

## Verification

Initial CI run #239 failed only in the new CLI trap because CSV evidence parsed the period selector as integer while the fixture metadata used strings.

The fixture was corrected to numeric selectors, preserving strict typed identity.

GitHub Actions CI run #240 (`37664376592`) then passed on code-bearing head `ff899ed89d4a57c5e31ca893552a1bffcd83fae2`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all prior CLI trap paths -> PASSED
- `percent_vs_percentage_points` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Composite selectors and grouped multi-row comparisons are not represented in v1.
- Exact explicit claim values do not include a separate display-rounding contract.
- Selector identity may require users to align JSON metadata types with CSV/JSON evidence types.
- Float arithmetic is sufficient for deterministic chart comparisons but not exact financial accounting semantics.
- The contract cannot determine whether a baseline is substantively fair or scientifically valid.

## Next Recommended Task

- Confirm final PR #21 CI remains green after VERIFY/HANDOFF.
- Merge if strict typed selectors and exact claim-number parity match the desired v1 contract.
- Keep composite selectors, explicit rounding, and broader time-window comparability separate rather than broadening this slice.
