# HANDOFF

## Resume Packet

- Goal: bind every public chart audit verdict to the exact inputs that produced it so a stale `READY` report cannot survive post-audit mutation undetected.
- Workflow state: draft PR #9 is open. Deterministic spec/chart/data/claim fingerprints, report schema `0.3`, verification helpers, CLI/package assertions, agent guidance, focused tests, and provenance docs are committed. CI run #188 is validating the latest head.
- Branch: `agent/bind-audit-reports-to-inputs`
- Base: `main` at `494f0a00afc4fbc78291cd000d60d904af08c67c`.
- Next task: inspect CI #188. If green, perform a final diff review and update `artifacts/VERIFY.md` with the final run evidence before marking the PR ready.
- Read first: `src/chart_contract/input_binding.py`, `src/chart_contract/spec_policy.py`, `src/chart_contract/chart.py`, `tests/test_input_binding.py`, `docs/AUDIT_PROVENANCE.md`, and `.github/workflows/ci.yml`.

## Current Repo State

- Public `audit_spec()` reports are wrapped as `BoundAuditReport` after the existing deterministic audit and visual-default policy run.
- First-party `Chart.audit()` reports are also wrapped without changing the underlying descriptive, statistical, or set-membership audit semantics.
- Bound reports serialize as schema `0.3` with SHA-256 fingerprints for the audited subject, explicit data when supplied, exact claim, installed package version, and a bundle fingerprint over those components.
- `report.matches_spec(...)` and `report.matches_chart(...)` provide a direct stale-report check before sharing.
- Spec mappings are canonicalized so mapping key order does not change the subject hash.
- Explicit pandas data fingerprints preserve row order, column order, index values/names, dtype metadata, categorical ordering, and supported scalar semantics.
- Inline Vega-Lite data remain covered by the spec fingerprint when no separate `data=` argument is supplied.

## Important Decisions

- Content identity is deterministic and intentionally excludes wall-clock timestamps.
- The installed package version is part of the binding so future canonicalization/rule interpretations do not silently reuse an older-version bundle identity.
- A matching fingerprint proves that inputs match the audited inputs; it does not prove analytical truth, scientific validity, or human approval.
- This slice adds no signing authority, remote attestation, publisher, automatic chart correction, renderer, or chart intent.
- Agents are instructed to rerun the audit after any audited-input change and verify the binding immediately before sharing.
- Unsupported arbitrary Python objects are not a promoted input surface; the supported contract remains JSON/Vega-Lite plus pandas-shaped evidence.

## Verification

- Initial CI #183 exposed a Python 3.10-3.12 compatibility failure from zero-argument `super()` inside a `@dataclass(slots=True)` subclass; Python 3.13 passed. The implementation now uses explicit `AuditReport.to_dict(self)` / `AuditReport.to_markdown(self)` dispatch.
- CI #185 then passed the complete test/CLI/trap jobs on Python 3.10, 3.11, 3.12, and 3.13.
- CI #185 package build, twine validation, and isolated wheel install all passed; the final wheel smoke assertion failed only because the workflow still expected report schema `0.2`.
- The workflow now expects schema `0.3` and also validates installed-version equality plus all component/bundle hash shapes.
- Latest CI run #188 is the executable validation gate for the final head, including the added first-party chart mutation regression.

## Remaining Risks

- SHA-256 content binding is identity evidence, not a signature; someone able to alter both inputs and report can recompute a new binding.
- The data canonicalizer is designed around the package's pandas/JSON-shaped inputs, not arbitrary opaque Python objects.
- Changes to canonicalization behavior in a future package version will intentionally produce a version-distinct bundle identity.
- `data_sha256` is `null` for inline-only spec data because those values are already part of `subject_sha256`; consumers should compare the bundle rather than interpreting a null explicit-data hash as unaudited data.

## Next Recommended Task

If CI #188 is fully green, record the final run in `artifacts/VERIFY.md`, perform one final PR patch review, and mark PR #9 ready for review. Do not add transform-consent behavior to this PR; keep that as the next separate slice.
