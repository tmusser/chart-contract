# HANDOFF

## Resume Packet

- Goal: make scalar business targets explicit, select exactly which supplied observation is evaluated, preserve durable target receipts, keep the threshold visibly bound, and audit narrow met/missed wording.
- Branch: `agent/metric-target-contract`.
- Base: `main` at `c8e58c006a7215d9b89ed7db7c309e49a0ba9848`.
- Pull request: #31 (`feat: audit metric target thresholds`).
- Current slice: first-party target API, closed v1 receipts, chart/spec audits, exact observation selection, visible datum-backed target rules, bounded met/missed claim parsing, target-status mismatch CLI trap, four new profile rules, tests, and docs.
- Read first: `src/chart_contract/target.py`, `src/chart_contract/target_audit.py`, `tests/test_target_contract.py`, and `docs/TARGET_CONTRACT.md`.

## Current Repo State

- `Chart.trend()` and `Chart.compare()` accept:
  - `metric_target`
  - `target_operator`
  - `target_selector_field`
  - `target_selector_value`
  - optional `target_tolerance`
- Target semantics are opt-in.
- V1 operators are `at_least`, `at_most`, and `equal`.
- Tolerance is absolute, finite, non-negative, and defaults to zero.
- The selector must resolve to exactly one supplied row; chart-contract never chooses latest/rightmost/max-date automatically.
- The selected metric value must be finite numeric evidence.
- First-party specs preserve closed `usermeta.target_contract` metadata:
  - metric field
  - selector field/value
  - target value
  - operator
  - tolerance
  - observed value
  - signed target gap
  - target-met boolean
- External audits recompute those receipts from supplied evidence.
- First-party trend/compare output renders the target as a datum-backed rule so the threshold is visible without being invented as source evidence.
- External target metadata requires a visible rule at the exact declared scalar; removed/moved rules block.
- Narrow target-status wording without a target contract produces REVIEW.
- Target-status wording contradictory to recomputed `target_met` blocks.
- Mixed met/missed wording blocks.
- Ordinary claims stay opt-in and do not create target semantics.
- Target and directionality contracts are independent; neither is inferred from the other.
- `examples/traps/target_status_claim_mismatch.*` uses selected value 0.76 versus at-least target 0.80 with correct receipts/rule but claim `Conversion met target.` -> BLOCK.
- The `audit-v0.2` profile now contains 100 rules.

## Important Decisions

- Scalar static thresholds keep v1 deterministic and inspectable.
- Target selection is explicit rather than temporal/order-based.
- `target_gap = observed - target` is stored only as arithmetic receipt; its sign is not utility semantics.
- A datum-backed rule is target metadata made visible, not a synthetic evidence row.
- Target contract validation and selected-observation evidence validation are separate findings.
- `at_least`, `at_most`, and `equal` cover the bounded v1 threshold semantics; acceptable bands/ranges are deferred.
- Met/missed claim parsing is intentionally narrow. Above/below target, on track, healthy, acceptable, and broad goal language are not interpreted.
- A target contract is not target authority/provenance certification.
- A passing target contract does not imply materiality, achievability, statistical significance, or causal benefit.
- Existing directionality, comparison, uncertainty, reconciliation, ratio, population, unit, metric-definition, grain, and rank contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because four new target rules change profile semantic identity.

## Verification

CI run #285 (`39621270743`) exposed a malformed method-signature insertion in the new public API. This was repaired without changing design semantics.

CI run #286 (`39621431123`) exposed target test fixtures that unintentionally triggered existing ratio-contract review and minimum-trend-row blocking. Those fixtures and docs were made scope-neutral; the existing guardrails were preserved.

Corrected GitHub Actions CI run #289 (`39621792558`) passed on head `3820a91296644f38ca874c160c1ebe3a06f38613`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `target_status_claim_mismatch` BLOCK trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Target values and selectors remain user-supplied and can be consistently wrong.
- V1 does not authenticate target ownership/source or effective dates.
- V1 supports one scalar static threshold, not ranges, bands, multiple thresholds, or time-varying targets.
- V1 uses float comparison/tolerance rather than exact decimal semantics.
- A selected row can be mechanically unique but analytically unfair.
- Visible-rule auditing proves structural binding only.
- Broader goal/threshold prose remains intentionally outside the parser.

## Next Recommended Task

- Confirm final PR #31 CI remains green after VERIFY/HANDOFF.
- Merge if explicit scalar thresholds, exact selector semantics, visible target binding, and narrow target-status claim parity match the desired v1.
- Keep target provenance/ownership, acceptable ranges, dynamic targets, materiality, and multi-objective policy separate future work.
