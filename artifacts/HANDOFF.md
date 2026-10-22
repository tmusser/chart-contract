# HANDOFF

## Resume Packet

- Goal: make filtered/cohort analysis-scope identity explicit so stable metrics cannot silently compare different evidence universes.
- Branch: `agent/analysis-scope-contract`.
- Base: `main` at `babf9efd8f008e4b7020c5eacf6328be9048fd16`.
- Pull request: #33 (`feat: audit analysis scope identity`).
- Current slice: first-party scope API, closed v1 metadata, chart/spec audits, row-level scope-basis checks, renderer refusal, mixed-scope CLI trap, two new profile rules, tests, and docs.
- Read first: `src/chart_contract/analysis_scope.py`, `src/chart_contract/analysis_scope_audit.py`, `tests/test_analysis_scope_contract.py`, and `docs/ANALYSIS_SCOPE_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept:
  - `scope_id`
  - `scope_definition`
  - `scope_version`
  - optional `scope_basis_field`
  - optional `scope_basis_value`
- Analysis-scope identity is opt-in.
- If any scope identity metadata is declared, ID/definition/version must all be present and non-empty.
- Basis field/value are optional but must be declared as a pair.
- First-party specs preserve a closed `usermeta.analysis_scope_contract`.
- Metadata-only scope identity is allowed; it does not fabricate row-level evidence.
- When row-level basis evidence is declared, the field must exist and every row must carry one non-empty string identity exactly matching the expected basis value.
- Mixed scopes block, including otherwise clean evidence that shifts from `us_paid_v1` to `all_customers_v1`.
- The first-party renderer refuses to stamp inconsistent row-level scope evidence.
- External specs require reconstructable data when claiming row-level scope evidence.
- Existing free-form `filters` metadata remains separate and non-executable.
- `examples/traps/mixed_analysis_scope.*` demonstrates same metric + same chart + different evidence universe -> BLOCK.
- The `audit-v0.2` profile now contains 102 rules.

## Important Decisions

- Scope identity is separate from metric-definition identity: a metric can remain semantically stable while its cohort/filter universe changes.
- V1 is deliberately identity-based, not a filter execution engine.
- No SQL, dbt, arbitrary Vega expressions, or free-form filter strings are replayed merely to make a scope contract pass.
- `scope_definition` is descriptive metadata and is not parsed for semantic equivalence.
- Optional row-level basis identity provides bounded evidence without pretending it proves upstream membership logic.
- Scope labels are exact strings; chart-contract does not normalize aliases.
- A passing scope contract does not prove the scope is analytically appropriate or that exclusions are justified.
- Existing metric-definition, population, unit, ratio, comparison, uncertainty, reconciliation, directionality, target, grain, and rank contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because two new scope rules change profile semantic identity.

## Verification

GitHub Actions CI run #294 (`39857374077`) passed on code-bearing head `68b5db01cea5336bfc3656df6a55eba6aca2a5ff`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `mixed_analysis_scope` BLOCK trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Scope metadata can be structurally consistent but factually wrong.
- V1 does not execute filter predicates or prove cohort membership.
- V1 does not detect semantic drift hidden behind an unchanged scope version.
- Free-text scope definitions are preserved but not compared for equivalence.
- V1 does not bind the scope contract to upstream SQL/dbt/Python digests.

## Next Recommended Task

- Confirm final PR #33 CI remains green after VERIFY/HANDOFF.
- Merge if exact scope identity and optional row-level scope-basis semantics match the desired v1.
- Keep executable filter lineage, predicate hashing, cohort membership evidence, and cross-version scope migration semantics separate future work.
