# HANDOFF

## Resume Packet

- Goal: make explicit Vega-Lite analytical transforms impossible to hide inside an otherwise plausible chart spec.
- Branch: `agent/audit-vega-transforms`.
- Base: `main` at `8435a29cb09e47275bdad2e5af46eb34f61fc919`.
- Pull request: #16 (`feat: audit Vega-Lite transform contracts`).
- Current slice: recursive transform inventory, exact transform-kind declaration matching, first-party transform metadata, CLI trap, two new audit-profile rules, tests, and docs.
- Read first: `src/chart_contract/transforms.py`, `src/chart_contract/spec_policy.py`, `tests/test_transform_policy.py`, `docs/TRANSFORM_CONTRACT.md`, and `docs/AUDIT_RULES.md`.

## Current Repo State

- External spec audits recursively inventory explicit Vega-Lite transforms and emit one `transform.inventory` finding per occurrence with an exact field path.
- Explicit transform operators covered are `aggregate`, `bin`, `calculate`, `density`, `extent`, `filter`, `flatten`, `fold`, `impute`, `joinaggregate`, `loess`, `lookup`, `pivot`, `quantile`, `regression`, `sample`, `stack`, `timeUnit`, and `window`.
- Encoding-level `aggregate`, `bin`, `stack`, and `timeUnit` are inventoried too, including supported aggregate/bin/time-unit shorthand.
- Malformed transform entries block rather than disappearing from the report.
- Density's optional top-level `extent` parameter is disambiguated from the standalone extent transform.
- `usermeta.transform_contract.declared` is a closed list contract and must exactly equal the detected unique transform-kind set.
- Missing, stale, unsupported, duplicate, malformed, or incomplete declarations block.
- A no-transform spec with no declaration passes the transform policy.
- First-party `Chart.histogram()` output declares `aggregate` and `bin`.
- First-party `Chart.violin()` output declares `density`.
- The checked histogram/violin proof specs now expose that transform metadata.
- `examples/traps/undeclared_filter_transform.*` provides a CLI-level hidden-transform failure case.
- The `audit-v0.2` profile now contains 55 rules, intentionally changing semantic profile identity.

## Important Decisions

- Transform auditing is structural. Do not execute arbitrary Vega-Lite expressions merely to make a spec auditable.
- A matching transform declaration means the spec is transparent about explicit transform kinds. It does not mean the transform is correct, approved, user-requested, scientifically justified, or faithfully reproduced.
- Transform declaration and scale/normalization user-request metadata remain separate contracts.
- Exact-set matching catches both newly hidden transforms and stale declarations after transforms are removed.
- Inventory findings preserve occurrence-level locations even though the declaration is kind-level.
- The detector intentionally fails closed on transform entries that cannot be classified as exactly one supported operator.
- New Vega-Lite transform operators should require an explicit implementation/profile/docs update instead of silent fallback.
- Existing data/evidence rules remain independent; a declared transform does not waive missing-field or reconstructability failures.
- Older schema-0.4 reports correctly become stale-policy artifacts because the two new rules change `audit-profile-semantics-v1`.

## Verification

Initial CI run #208 failed only because an existing exact-`usermeta` regression expected the pre-transform-contract histogram metadata.

After updating that expected contract, GitHub Actions CI run #209 (`36938459089`) passed on code-bearing head `13871a589c60e7f25d2a4156c3bfb603be0ab283`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- CLI verdict + diagnostic traps -> PASSED
- undeclared-filter transform CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- The transform contract does not execute arbitrary expressions or reconstruct transformed result sets.
- The operator inventory is bounded to known explicit Vega-Lite transform structure and must evolve deliberately with Vega-Lite.
- A transform declaration can be truthful about structure while the transform itself is analytically poor or semantically misleading.
- Raw-data encoding checks can still block transformed output fields when deterministic reconstruction is unavailable.
- This PR does not add per-transform expression hashing separate from the existing whole-spec input binding; the exact full spec is already content-bound.

## Next Recommended Task

- Confirm final PR #16 CI remains green after these documentation-only commits.
- Review the public `usermeta.transform_contract.declared` shape and merge if it matches the desired contract.
- Keep transform replay/execution or a richer transformation-lineage receipt as a separate future PR.
