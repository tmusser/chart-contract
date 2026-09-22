# HANDOFF

## Resume Packet

- Goal: keep rendered chart artifacts attached to the exact analytical claim they were created to support.
- Branch: `agent/embed-audited-claim`.
- Base: `main` at `e279b87dad8a0a8cb6b62ba2a8085648798134f7`.
- Current slice: embedded claim metadata, deterministic claim-conflict auditing, resolved-claim input binding, saved-report verification, profile parity, tests, and agent documentation.
- Read first: `src/chart_contract/contracts.py`, `src/chart_contract/audit.py`, `src/chart_contract/spec_policy.py`, `src/chart_contract/renderers/altair.py`, `src/chart_contract/input_binding.py`, `tests/test_audit_spec.py`, and `docs/AGENT_INTEGRATION.md`.

## Current Repo State

- First-party `Chart.to_vega_lite()` output preserves the exact analytical claim as `usermeta.claim` even when the display title differs.
- `audit_spec()` accepts the existing explicit claim input and can now recover the claim from `usermeta.claim` when the explicit input is omitted.
- If both claim sources exist and differ after trimming outer whitespace, `contract.claim.consistency` emits `FAIL`, producing `BLOCK`.
- External/legacy specs without `usermeta.claim` preserve their existing findings and explicit-claim workflow; no consistency finding is emitted for absence alone.
- Bound spec reports hash the resolved claim actually audited. `matches_spec(..., claim=None)` and CLI saved-report verification use the embedded claim when present.
- The machine-readable `audit-v0.2` profile now contains 44 documented rules including `contract.claim.consistency`.

## Important Decisions

- Claim identity is provenance, not analytical support.
- The consistency check uses deterministic exact text identity, not semantic similarity or LLM judgment.
- A custom display title may differ from the analytical claim; title and claim are intentionally separate fields.
- Embedded claim metadata is authoritative for first-party chart artifacts, but arbitrary external Vega-Lite specs are not required to carry it.
- Missing embedded metadata does not create a new warning or failure, preserving legacy audit behavior.
- Claim metadata values are excluded from chart-decoration keyword scanning.
- No automatic claim rewriting, chart correction, or publication behavior is added.

## Verification

Focused tests cover:
- exact claim retention through first-party rendering;
- embedded-only audits;
- explicit/embedded conflict blocking;
- resolved-claim durable bindings;
- saved-report verification without a repeated explicit claim;
- legacy explicit-only behavior;
- decoration-scanner isolation;
- machine-readable profile/documentation parity.

The full GitHub Actions Python 3.10-3.13 matrix and isolated wheel smoke remain the authoritative final gate for this slice.

## Remaining Risks

- Exact identity cannot determine whether two differently worded claims are substantively equivalent.
- A matching embedded claim can still be false, unsupported, misleading, or scientifically invalid.
- Historical checked-in Vega-Lite outputs are not bulk-regenerated in this slice because dependency-version rendering drift would add unrelated proof-artifact churn.

## Next Recommended Task

- Open the PR and let the full CI matrix attack the implementation.
- If green, inspect the final branch diff for accidental audit-semantic changes outside claim identity.
- Keep the older percent-unit versus decimal-scale question as a separate follow-up rather than combining it into this back-to-basics slice.
