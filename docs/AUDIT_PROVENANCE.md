# Audit Input Provenance

`chart-contract` audit verdicts are content-bound. A report should not be reusable after the audited chart inputs change.

Public spec audits and first-party `Chart.audit()` reports therefore emit a deterministic `input_binding` envelope.

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

## Why no timestamp?

The binding is intended to be reproducible. Wall-clock time is intentionally excluded from the content identity, so the same inputs audited by the same package version produce the same binding.

## Report schema

Bound reports serialize with report schema `0.3` and include:

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
  }
}
```

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
Binding: MATCH
Subject: MATCH
Data: MATCH
Claim: MATCH
Bound tool version: 0.2.0
```

The verifier returns:

- `0` when the saved binding matches the current spec, data, and claim exactly;
- `1` when at least one bound component has drifted;
- `2` for malformed, unbound, unsupported, or unreadable verification inputs.

Component-level output makes drift inspectable. A spec-only mutation reports `Subject: MISMATCH` while unchanged data and claim remain `MATCH`.

The verifier recomputes fingerprints using the tool version recorded in the saved binding. This preserves the identity of the historical audit instead of requiring the currently installed package version to equal the version that produced the report.

Before comparing live inputs, the CLI also checks that the serialized bundle hash is consistent with the component hashes recorded inside the report. This catches accidental or casual edits to one binding field.

The CLI verification surface currently supports saved **spec-audit** JSON reports. First-party `Chart.audit()` bindings remain verifiable through `matches_chart(...)` in Python because reconstructing an arbitrary chart contract from a generic serialized CLI input would create a second contract format.

## Boundary

A fingerprint proves content identity, not analytical truth. A matching `READY` report means the current inputs are the same inputs that produced that mechanical verdict. It does not upgrade `READY` into scientific validation or human approval.

The hashes are also not signatures. Someone who can rewrite the report can deliberately recompute a new internally consistent binding. Saved-report verification is a drift and consistency check, not an authenticity, authorship, or tamper-proofing mechanism.
