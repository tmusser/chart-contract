# Audit Provenance and Report Integrity

`chart-contract` audit verdicts are content-bound. A report should not be reusable after the audited chart inputs, saved findings, derived verdict, or audit-policy semantics change.

Public spec audits and first-party `Chart.audit()` reports therefore emit two deterministic envelopes:

- `input_binding` identifies the exact subject, explicit data, claim, and historical tool version;
- `report_binding` identifies the saved audit result plus the semantic audit-profile digest that produced it.

These bindings are reproducible drift detectors, not signatures or remote attestation.

## Bound components

Spec audits bind:

- the canonicalized Vega-Lite spec;
- explicit audit data, when supplied;
- the exact claim text;
- the installed `chart-contract` package version.

First-party chart audits bind:

- the chart contract fields other than data and claim;
- the chart data;
- the exact chart claim;
- the installed `chart-contract` package version.

Each component uses SHA-256. The report also carries a bundle SHA-256 over the component hashes, subject kind, hash algorithm, and tool version.

The report binding then covers:

- the input bundle SHA-256;
- the exact `audit-v0.2` semantic profile binding;
- every serialized finding, including message, suggestion, and field metadata;
- the derived `passed`, warning/failure flags, verdict, summary, and verdict summary.

The profile digest excludes package-version-only drift, so a tool release with unchanged audit semantics does not invalidate the policy identity.

## Why no timestamp?

The binding is intended to be reproducible. Wall-clock time is intentionally excluded from the content identity, so the same inputs audited by the same package version produce the same binding.

## Report schema

Bound reports serialize with report schema `0.4` and include:

```json
{
  "input_binding": {
    "algorithm": "sha256",
    "subject_kind": "spec",
    "subject_sha256": "...",
    "data_sha256": "...",
    "claim_sha256": "...",
    "tool_version": "0.2.0",
    "bundle_sha256": "..."
  },
  "report_binding": {
    "algorithm": "sha256",
    "canonicalization": "audit-report-semantics-v1",
    "input_bundle_sha256": "...",
    "audit_profile": {
      "algorithm": "sha256",
      "canonicalization": "audit-profile-semantics-v1",
      "profile": "audit-v0.2",
      "profile_manifest_sha256": "..."
    },
    "report_sha256": "..."
  }
}
```

Schema `0.3` remains historical. It cannot be upgraded in place because it never recorded the result/profile binding. Durable verification of a legacy `0.3` artifact therefore requires re-auditing to produce a new `0.4` report.

When a spec uses only inline data and no explicit `data=` argument is supplied, `data_sha256` is `null`; the inline values remain covered by the spec hash.

## Verification

Python callers can verify an in-memory report against the inputs they are about to share:

```python
report = audit_spec(spec=spec, data=df, claim=claim)
assert report.matches_spec(spec=spec, data=df, claim=claim)
```

For first-party charts:

```python
report = chart.audit()
assert report.matches_chart(chart)
```

Any change to the audited subject, explicit data, or claim invalidates the match.

### Verify a saved JSON report

A report written by the CLI can be checked later without reconstructing the original Python object:

```bash
chart-contract audit spec chart.vl.json \
  --data chart.csv \
  --claim "Observed conversion increased." \
  --format json \
  --out audit.json

chart-contract verify report audit.json \
  --spec chart.vl.json \
  --data chart.csv \
  --claim "Observed conversion increased."
```

Representative success output:

```text
Report integrity: MATCH
Audit profile: MATCH
Binding: MATCH
Subject: MATCH
Data: MATCH
Claim: MATCH
Bound profile: audit-v0.2
Bound profile SHA-256: ...
Bound tool version: 0.2.0
```

The verifier returns:

- `0` when the saved report is internally consistent, the saved audit-profile semantics still match the installed profile, and the current spec/data/claim match exactly;
- `1` when live inputs or audit-profile semantics have drifted;
- `2` for malformed, internally inconsistent, legacy `0.3`, unbound, unsupported, or unreadable verification inputs.

Component-level output makes drift inspectable. A spec-only mutation reports `Subject: MISMATCH` while unchanged data and claim remain `MATCH`.

The verifier recomputes fingerprints using the tool version recorded in the saved binding. This preserves the identity of the historical audit instead of requiring the currently installed package version to equal the version that produced the report.

Before comparing live inputs, the CLI checks both durable envelopes. It rejects an inconsistent input bundle, a report binding attached to a different input bundle, derived verdict/summary fields that disagree with the serialized findings, and a `report_sha256` that no longer matches the saved audit result.

An audit-profile digest mismatch is different: the historical report can still be internally consistent, but the installed audit policy is no longer semantically identical. The verifier reports `Audit profile: MISMATCH` and exits `1`, making re-audit the safe default rather than silently treating an old green result as current.

The CLI verification surface currently supports saved **spec-audit** JSON reports. First-party `Chart.audit()` bindings remain verifiable through `matches_chart(...)` in Python because reconstructing an arbitrary chart contract from a generic serialized CLI input would create a second contract format.

## Boundary

A fingerprint proves content identity, not analytical truth. A fully matching `READY` report means the current inputs, saved audit result, and audit-profile semantics are the same identities carried by that mechanical artifact. It does not upgrade `READY` into scientific validation or human approval.

The hashes are also not signatures. Someone who can rewrite the report can deliberately recompute new internally consistent bindings. Saved-report verification catches accidental or casual artifact drift and stale-policy reuse; it is not authenticity, authorship, cryptographic tamper-proofing, timestamp authority, or remote attestation.
