# HANDOFF

## Resume Packet

- Goal: make uncertainty/error-bar semantics explicit and auditable rather than treating visible intervals as self-describing.
- Branch: `agent/uncertainty-interval-contract`.
- Base: `main` at `9ad28b1ef6d9237a8378903204f38de7355feebb`.
- Pull request: #28 (`feat: audit uncertainty interval semantics`).
- Current slice: first-party interval API/rendering, closed v1 metadata, chart/spec audits, bound containment, visible interval binding, narrow claim parity, comparison-parser collision fix, CLI trap, four new profile rules, tests, and docs.
- Read first: `src/chart_contract/uncertainty.py`, `src/chart_contract/uncertainty_audit.py`, `tests/test_uncertainty_contract.py`, and `docs/UNCERTAINTY_CONTRACT.md`.

## Current Repo State

- `Chart.trend()` and `Chart.compare()` accept:
  - `interval_lower_field`
  - `interval_upper_field`
  - `interval_kind`
  - `interval_level`
  - `interval_method`
- Rank is intentionally excluded from uncertainty v1 because top-N/aggregate-Other interval composition needs a separate design.
- Supported interval kinds: confidence, credible, prediction, bootstrap.
- First-party specs preserve a closed `usermeta.uncertainty_contract`.
- The contract binds one visible estimate field to distinct lower/upper fields.
- `interval_level` must be finite and in `(0,1)`.
- Every estimate/lower/upper triplet must be complete, numeric, finite, and satisfy `lower <= estimate <= upper`.
- First-party rendering refuses malformed bounds and visibly draws intervals as rule layers.
- External specs must keep the declared estimate visible and bind lower/upper fields through `y/y2` or `x/x2`.
- Deleting or rewiring the interval layer blocks even when metadata remains unchanged.
- Narrow explicit claim forms include `95% CI`, confidence, credible, prediction, and bootstrap interval wording.
- Missing uncertainty metadata with such wording produces REVIEW.
- Explicit claim kind/level mismatch produces BLOCK.
- Comparison parsing now excludes recognized interval-level percentages, so `95% CI` no longer triggers a fake percent-change baseline warning.
- `examples/traps/interval_claim_mismatch.*` declares a valid 90% credible interval while the claim says 95% confidence interval.
- The `audit-v0.2` profile now contains 91 rules.

## Important Decisions

- Error bars are semantic contracts, not decoration.
- V1 validates supplied intervals rather than computing them.
- Visible interval binding is required so metadata cannot outlive the actual visual uncertainty encoding.
- Claim parsing stays narrow and deterministic; general words such as uncertain/likely/error bars are not interpreted.
- A passing contract does not certify coverage, calibration, estimator correctness, significance, or hypothesis-test validity.
- Interval overlap/non-overlap is never interpreted as significance.
- Interval method remains explicit descriptive identity rather than executable statistical provenance.
- Existing population, unit, metric-definition, ratio, comparison, time-window, grain, and comparison-set contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because four new uncertainty rules change profile semantic identity.

## Verification

GitHub Actions CI run #273 (`39072662559`) passed on code-bearing head `1fadcb22201c396c5f4bdbc68bcf22b8fd051791`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `interval_claim_mismatch` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- A method label can be internally consistent but statistically wrong.
- V1 does not recompute intervals from standard errors, posterior samples, bootstrap replicates, or model outputs.
- V1 does not validate nominal coverage or calibration.
- V1 does not support simultaneous/multiple-comparison interval semantics.
- Rank/top-N interval composition remains deferred.
- The external visual-binding check intentionally verifies direct rule-field binding, not every semantically equivalent Vega-Lite construction.

## Next Recommended Task

- Confirm final PR #28 CI remains green after VERIFY/HANDOFF.
- Merge if explicit interval semantics, direct visible binding, and narrow claim parity match the desired v1.
- Keep significance/hypothesis testing, simultaneous intervals, calibration, and estimator provenance separate future work.
