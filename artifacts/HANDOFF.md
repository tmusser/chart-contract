# HANDOFF

## Resume Packet

- Goal: make additive component decompositions reconcile explicitly to one scalar control total.
- Branch: `agent/control-total-reconciliation`.
- Base: `main` at `269d5fe49ab687484a8aed5354eab1206ceb55f4`.
- Pull request: #29 (`feat: audit control total reconciliation`).
- Current slice: first-party reconciliation API, closed v1 receipts, chart/spec audits, component uniqueness/value checks, residual/share arithmetic, ratio-like rejection, control-total-gap CLI trap, three new profile rules, tests, and docs.
- Read first: `src/chart_contract/reconciliation.py`, `src/chart_contract/reconciliation_audit.py`, `tests/test_reconciliation_contract.py`, and `docs/RECONCILIATION_CONTRACT.md`.

## Current Repo State

- `Chart.rank()` and `Chart.compare()` accept:
  - `control_total`
  - optional `control_total_source`
  - optional `reconciliation_tolerance`
- Reconciliation is opt-in.
- Trend is intentionally excluded in v1 so time rows are not accidentally treated as additive components.
- V1 uses fixed `sum` semantics only.
- First-party specs preserve a closed `usermeta.reconciliation_contract`.
- The contract binds `x` as component field and `y` as additive metric field.
- Components must be non-null/non-blank and unique.
- Metric values must be complete, finite, numeric, and non-boolean.
- Duplicate component labels block rather than being silently summed.
- Percent/rate/ratio metrics are rejected from sum reconciliation.
- Component sum, residual, and represented share are recomputed from supplied evidence.
- Represented share is available only for positive controls with non-negative components.
- First-party rendering refuses a reconciliation outside tolerance.
- External specs may preserve a failing but internally coherent receipt; audit then emits `data.reconciliation.total=FAIL` with the residual/share rather than misclassifying it as malformed schema.
- Stale receipts that remain internally coherent but disagree with supplied evidence block.
- `examples/traps/control_total_gap.*` uses 9.1M components against 11.8M control -> residual 2.7M, 77.1% represented, BLOCK.
- No balancing component is created automatically.
- Reconciliation covers supplied evidence; truncated rank display semantics remain independently covered by comparison-set rules.
- The `audit-v0.2` profile now contains 94 rules.

## Important Decisions

- Control-total reconciliation is source-evidence arithmetic, not business-authority certification.
- One scalar control + one sum decomposition keeps v1 deterministic and inspectable.
- `control_total_source` is optional descriptive provenance, not authentication.
- `reconciliation_tolerance` is an explicit absolute tolerance; no automatic tolerance is inferred from metric magnitude.
- The tiny `math.isclose` relative tolerance exists only for floating-point stability.
- Duplicate components are treated as ambiguous/double-count risk rather than implicitly aggregated.
- A failed reconciliation surfaces the residual and represented share but does not infer the missing category.
- Unknown/Other/balancing rows are never synthesized to make arithmetic pass.
- Ratio-like metrics stay outside generic additive reconciliation.
- Existing grain, rank/comparison-set, unit, metric-definition, population, uncertainty, ratio, comparison, and time-window contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because three new reconciliation rules change profile semantic identity.

## Verification

Initial GitHub Actions CI run #276 (`39152937739`) found one stale-receipt test fixture that changed component total/residual but failed to update represented share; the closed schema correctly rejected that fixture before evidence replay.

The fixture was corrected to remain internally coherent while stale versus supplied evidence.

GitHub Actions CI run #277 (`39153019498`) passed on code-bearing head `9512ebded454e6f510b0ef3e2e974187d5936abf`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `control_total_gap` BLOCK trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- A consistently wrong control total or source label remains undetectable.
- V1 does not authenticate external control totals.
- V1 does not model hierarchical controls, accounting bridges, or nested subtotal reconciliation.
- V1 does not automatically reconcile transformed/filtered display subsets; those remain under transform and comparison-set policies.
- V1 uses float arithmetic rather than exact decimal accounting.
- Multi-row component definitions require upstream aggregation or a future richer reconciliation contract.

## Next Recommended Task

- Confirm final PR #29 CI remains green after VERIFY/HANDOFF.
- Merge if scalar additive reconciliation and explicit residual semantics match the intended v1.
- Keep hierarchical control trees, accounting adjustments, and exact-decimal reconciliation separate future work.
