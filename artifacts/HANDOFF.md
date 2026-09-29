# HANDOFF

## Resume Packet

- Goal: harden durable audit reports against post-audit result edits and audit-policy drift without turning content hashes into authenticity claims.
- Branch: `agent/harden-report-integrity`.
- Base: `main` at `38ac3b701615e01f345733baa0144d621c3a5325`.
- Pull request: #14 (`feat: bind audit reports to result and policy identity`).
- Current slice: bound report schema `0.4`, result-integrity binding, audit-profile binding, saved-report verification, in-memory mutation detection, tests, CI smoke, and provenance docs.
- Read first: `src/chart_contract/input_binding.py`, `src/chart_contract/cli.py`, `tests/test_input_binding.py`, `tests/test_saved_report_verification.py`, and `docs/AUDIT_PROVENANCE.md`.

## Current Repo State

- Public `audit_spec()` and first-party `Chart.audit()` reports now serialize as bound report schema `0.4`.
- Existing `input_binding` still fingerprints the exact audited subject, explicit data, claim, and historical tool version.
- New `report_binding` fingerprints the input bundle plus every serialized finding, derived verdict/summary fields, and the exact `audit-v0.2` semantic profile binding.
- `chart-contract verify report` reports three layers independently: report integrity, audit-profile identity, and current input identity.
- A semantically different installed audit profile returns `Audit profile: MISMATCH` and exit 1 even when the saved report and current inputs are otherwise internally consistent.
- Edited findings or contradictory derived verdict metadata make the saved report malformed and verification exits 2.
- `matches_spec(...)` and `matches_chart(...)` now reject post-audit result mutation as well as input drift.
- Historical schema `0.3` reports remain historical and require re-audit for schema-`0.4` durable verification.

## Important Decisions

- `audit-report-semantics-v1` is deterministic content identity, not cryptographic authentication.
- The report binding includes audit-profile semantic identity but deliberately inherits the profile contract's package-version exclusion, so version-only drift is not policy drift.
- A profile mismatch means the saved ruleset semantics are stale relative to the installed policy; it is not an automatic compatibility, quality, or scientific judgment.
- Do not recompute a report binding after manually editing findings or verdict fields. Re-run the audit and emit a new report.
- Do not synthesize missing result/profile identity for schema `0.3`; those facts were not recorded historically.
- Signing, timestamp authority, remote attestation, and authorship proof remain explicit non-goals.

## Verification

GitHub Actions CI run #202 (`36641570160`) passed on the pre-handoff code head:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- CLI verdict and statistical trap checks -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel installation -> PASSED
- installed CLI schema-`0.4` report shape and verification smoke -> PASSED

The final handoff/verification documentation commits do not change runtime semantics; the final branch CI should still be treated as the merge gate.

## Remaining Risks

- Someone with write access can deliberately recompute hashes after changing an artifact; this feature detects drift, not adversarial forgery.
- Matching profile identity does not prove the Python implementation faithfully implements every declared profile rule.
- A fully matching `READY` artifact is still a deterministic mechanical result, not scientific validation or human approval.
- Consumers that persist schema `0.3` reports must re-audit rather than expecting an in-place upgrade.

## Next Recommended Task

- Confirm final PR #14 CI remains green after the documentation-only handoff commits.
- Review the schema-`0.4` migration boundary and merge if the explicit re-audit requirement for legacy `0.3` artifacts is acceptable.
- Keep any future cryptographic signing/attestation work as a separate layer rather than weakening the present content-identity semantics.
