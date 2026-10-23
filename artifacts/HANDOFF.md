# HANDOFF

## Resume Packet

- Goal: distinguish observed numeric zero, structural zero, missing, and suppressed metric evidence so null values cannot silently masquerade as zeros.
- Branch: `agent/observation-status-contract`.
- Base: `main` at `d943f57e6a01021c4de746a05f8f032cb7580603`.
- Pull request: #34 (`feat: audit missing versus zero observation semantics`).
- Main implementation: `src/chart_contract/observation_status.py`, `src/chart_contract/observation_status_audit.py`, `tests/test_observation_status_contract.py`, and `docs/OBSERVATION_STATUS_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept `observation_status_field`.
- Status identity is opt-in. Unsupported or missing declarations are not guessed from raw values.
- Version 1 closed states: `observed`, `structural_zero`, `missing`, `suppressed`.
- `observed` requires finite numeric values; exact numeric zero is valid.
- `structural_zero` requires numeric zero.
- `missing` and `suppressed` require a null metric value. A zero-filled missing observation blocks.
- The first-party renderer refuses contradictory evidence and stamps `usermeta.observation_status_contract` with four state counts.
- External audits independently bind the declared metric to a visible quantitative encoding, validate original evidence, and recompute count receipts.
- Contracts with malformed schema, detached metric fields, stale counts, or unavailable evidence block.
- No imputation, value mutation, suppression-policy approval, missingness classification, or guarantee about visible Vega-Lite gap glyphs.
- Three new rules: `contract.observation.status`, `data.observation.values`, `data.observation.receipts`.
- Audit profile advances from 102 to 105 rules.
- Trap `examples/traps/missing_zero_filled.*` shows February orders set to 0 while status says missing -> BLOCK.

## Verification

- Initial CI #298 showed two unrelated test assumptions, then tests were tightened without weakening production enforcement.
- Corrected code-bearing CI #299 (`40002430312`) passed on head `000b604729e155ec3812eb232bd41dc0488ec56f`:
  - Python 3.10, 3.11, 3.12, 3.13 -> PASSED
  - all old and new CLI traps -> PASSED
  - build and isolated installed wheel -> PASSED
- `artifacts/VERIFY.md` records exact proof.
- Final VERIFY/HANDOFF edits are documentation-only. Confirm exact final-head CI before merge.

## Risks and Decisions

- Status consistency is not upstream ETL correctness.
- Legitimate recorded zeros remain valid; suppressing rows as null does not evade independent coverage checks.
- A false upstream status label may remain undetectable.
- The audit does not transform missing or suppressed values into plotted substitutes.
- V1 does not attest missingness mechanism, censored detection limits, or visual gap readability.
- New rules change the audit policy digest and require re-auditing older bound reports.

## Next Recommended Task

- Check CI on final PR head, review and optionally merge #34.
- Keep richer missingness state taxonomies, censoring, and visible-gap guarantees in separate future contracts.
