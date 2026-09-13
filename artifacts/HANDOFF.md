# HANDOFF

## Resume Packet

- Goal: add claim-contract-style ruleset introspection to `chart-contract` without changing existing chart audit semantics or saved report schema `0.3`.
- Branch: `agent/add-audit-profile-parity`.
- Base: `main` at `08969c5eaa8d8e27fa5a28f8fc1781013ba8cde4`.
- Current slice: machine-readable `audit-v0.2` profile metadata, semantic profile identity, mechanical profile diff, CLI inspection, schemas, tests, and documentation.
- Read first: `src/chart_contract/profiles.py`, `src/chart_contract/profile_diff.py`, `src/chart_contract/cli.py`, `docs/AUDIT_PROFILE.md`, `tests/test_profiles.py`, `tests/test_profile_diff.py`, and `tests/test_cli_profile.py`.

## Current Repo State

- Existing public audit behavior remains unchanged: chart/spec audits still produce `PASS` / `WARN` / `FAIL` findings summarized as `READY` / `REVIEW` / `BLOCK`.
- Existing bound reports remain schema `0.3` and continue to bind the audited subject/spec, explicit data, exact claim, and package version.
- `chart-contract profile show audit-v0.2 --json` exposes the documented audit ruleset as machine-readable metadata rather than requiring agents to scrape Markdown or Python source.
- The profile currently mirrors the 43 stable rule IDs documented in `docs/AUDIT_RULES.md` and records applicable audit surfaces, allowed severities, a concise trigger, and a known boundary for each rule.
- Rules with threshold-dependent behavior record an allowed severity set rather than pretending every rule has one fixed severity.
- `audit-profile-semantics-v1` computes a deterministic semantic SHA-256 identity over profile and rule semantics while intentionally excluding top-level tool/package metadata.
- `chart-contract profile diff before.json after.json` reports profile fields, rule additions/removals, rule-field changes, rule-order drift, semantic identities, and tool metadata drift.
- The profile diff deliberately emits no compatibility judgment.

## Important Decisions

- The machine-readable profile is descriptive metadata, not another audit and not scientific validation.
- A matching profile digest identifies the same declared audit semantics; it does not authenticate execution or prove that an audit implementation is correct.
- Package-version-only drift is separated from semantic ruleset drift.
- This PR does not bind profile identity into saved audit reports. Historical report schema `0.3` keeps its existing meaning.
- A future report-schema revision may add profile identity after this profile contract sees real use; that should be an explicit versioned migration.
- No chart intent, renderer, audit threshold, rule trigger, `READY` / `REVIEW` / `BLOCK` behavior, input binding, or visual-default policy changes in this slice.

## Verification

- New focused tests cover 43-rule parity with `docs/AUDIT_RULES.md`, unique rule IDs, interpretation-boundary fields, semantic binding behavior, allowed severity metadata, mechanical diff behavior, and CLI show/diff behavior.
- Package-version-only manifest changes are expected to keep the same semantic profile identity while setting tool metadata drift in the diff.
- Rule trigger, known-boundary, severity, addition/removal, and order changes are expected to register as semantic drift.
- Full GitHub Actions CI is the authoritative repository verification gate because this environment cannot clone GitHub directly for a local full-suite run.

## Remaining Risks

- The profile registry mirrors the documented audit surface but does not yet force every runtime `report.add(...)` emission through the registry. Drift is test-locked against the human rule reference, not runtime-enforced at every emission site.
- Semantic profile hashes are content identities, not signatures or remote attestation.
- A mechanical rule diff cannot determine whether a change is compatible, safe, breaking, or scientifically better.
- Existing `0.3` audit reports identify their input bundle and tool version, not an exact audit-profile digest.

## Next Recommended Task

- Run the full CI matrix and isolated wheel smoke test on the PR head.
- If green, review the patch for accidental audit-semantic changes and record the final CI evidence in `artifacts/VERIFY.md`.
- Keep report-to-profile binding as a separate future schema migration rather than expanding this PR.
