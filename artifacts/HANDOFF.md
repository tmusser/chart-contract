# HANDOFF

## Resume Packet

- Goal: make business metric identity/version explicit so a stable quantitative field name cannot hide definition drift.
- Branch: `agent/metric-definition-identity`.
- Base: `main` at `43f2a814dfdab06837a75e02631b8c2dc1981f46`.
- Pull request: #25 (`feat: audit metric definition identity`).
- Current slice: first-party metric identity API, closed v1 spec metadata, chart/spec audits, row-level version checks, metric-definition-drift CLI trap, two new profile rules, tests, and docs.
- Read first: `src/chart_contract/metric_definition.py`, `src/chart_contract/metric_definition_audit.py`, `tests/test_metric_definition_contract.py`, and `docs/METRIC_DEFINITION_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept:
  - `metric_id`
  - `metric_definition`
  - `metric_version`
  - optional `metric_basis_field`
- Metric-definition identity is opt-in.
- If any identity metadata is supplied, ID/definition/version must all be present and non-empty.
- First-party specs preserve a closed `usermeta.metric_definition_contract`.
- The contract binds to the chart/spec quantitative metric field.
- External specs must bind the same metric field to a visible quantitative encoding.
- `metric_basis_field` provides row-level evidence that every supplied observation uses the same declared metric version.
- Missing, null, blank, mixed, or contract-mismatched basis values block.
- Without a basis field, the contract records catalog identity only and emits no row-level version finding.
- No metric identity is inferred from field names, units, titles, claims, sources, or values.
- `examples/traps/metric_definition_drift.*` demonstrates `active_users` retaining the same field name while row versions change from v1 to v2.
- The `audit-v0.2` profile now contains 80 rules.

## Important Decisions

- Opt-in semantics avoid forcing callers to invent fake metric-catalog identity merely to reach READY.
- Once declared, metric identity is strict and closed-schema.
- Metric version is an exact semantic identity string; no normalization or compatibility inference is performed.
- The optional basis field checks version identity only; it does not replay or validate upstream metric computation.
- Definition text is descriptive metadata and is not interpreted for semantic equivalence.
- A passing contract does not certify that the business definition is sensible or correctly implemented upstream.
- Existing ratio, comparison, time-window, grain, and comparison-set contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because two new metric-definition rules change profile semantic identity.

## Verification

GitHub Actions CI run #253 (`38471520287`) passed on code-bearing head `913b3c72432203342e6874817ff7749e13dad53a`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `metric_definition_drift` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- A stable but incorrect version label remains undetectable.
- V1 does not bind metric identity to executable SQL/dbt/Python definitions.
- V1 does not compare semantic equivalence of free-text definitions.
- Cross-version compatibility remains a human/domain decision rather than an automated judgment.
- A metric may change implementation without changing its declared version upstream.

## Next Recommended Task

- Confirm final PR #25 CI remains green after VERIFY/HANDOFF.
- Merge if strict opt-in metric identity and row-version consistency match the desired v1.
- Keep executable metric provenance, definition digests, and cross-version migration semantics separate future work.
