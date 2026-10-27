# Cross-Chart Audit Bundles (v1)

Two individually READY charts can jointly support an invalid comparison. For
example, one chart shows growth among US paid customers and another shows churn
among all customers. Both are internally consistent, but describing their rates
as if they refer to the same universe is misleading.

Bundles make **the intended cross-chart relationship explicit**, then rerun
each component spec audit and compare only the declared semantic identities.

## CLI

```bash
chart-contract audit bundle report.bundle.json
chart-contract audit bundle report.bundle.json --format json --out bundle-audit.json
chart-contract audit bundle report.bundle.json --warnings-as-errors
```

A closed version-1 manifest:

```json
{
  "version": 1,
  "artifacts": [
    {"id": "growth", "spec": "growth.vl.json", "data": "growth.csv"},
    {"id": "churn", "spec": "churn.vl.json", "data": "churn.csv"}
  ],
  "relationships": [
    {
      "id": "executive_same_population",
      "artifact_ids": ["growth", "churn"],
      "equal_on": ["analysis_scope"]
    }
  ]
}
```

Every artifact requires a unique `id` and `spec`. An optional `data` path
(CSV/JSON) and exact `claim` may be supplied. Otherwise, the spec may provide
inline evidence and embedded `usermeta.claim`; the normal component audit
still enforces evidence and claim requirements. The manifest needs at least two
artifacts and one relationship between at least two declared artifact IDs.
Relationship IDs, members, and identity dimensions must be unique. Unknown fields
and unsupported dimensions are rejected rather than ignored.

Paths are relative to the manifest directory. Absolute paths and parent
directory escape are refused; symlinks cannot escape the manifest directory.
This version does not make HTTP requests or execute SQL.

## Supported comparison dimensions

Explicit `equal_on` entries are:

| Dimension | Required evidence | What must be equal |
| --- | --- | --- |
| `analysis_scope` | Closed `usermeta.analysis_scope_contract` | Scope ID, version, and definition |
| `metric_definition` | Closed `usermeta.metric_definition_contract` | Metric ID, version, and definition |
| `unit` | Declared `usermeta.unit` | Unit plus raw value representation |
| `time_window` | Closed `usermeta.time_window_contract` | Kind, granularity, dates, completeness, and durations |

Source column and basis-field names do not need to be identical across charts.
Shared `analysis_scope` does **not** imply shared metric meaning or compatible
time windows; a bundle does not infer either obligation. A report containing
growth and churn can legitimately enforce `analysis_scope` without asserting
those are the same metric.

Every declared dimension needs valid metadata for **every** related artifact.
A missing identity `BLOCK`s rather than silently excluding a component.
Declared identity differences also `BLOCK`; this is a gate against an explicitly
inconsistent comparison, not a claim that the charts cannot coexist.

## Verdict and report

The bundle re-audits all component specs using `audit_spec`, carrying forward
their complete, content-bound reports (input and report bindings plus profile
digests) in JSON output. Historical report files are not trusted as substitutes.
The bundle verdict uses the worst of its component verdicts and relationship
findings:

- `READY`: all component audits READY and all declared identities match.
- `REVIEW`: at least one component REVIEW; no BLOCK.
- `BLOCK`: a component BLOCK, a required identity missing/malformed, or a
  declared relationship disagrees across charts.

A relationship involving an already BLOCKed component is reported as skipped,
not incorrectly described as verified. Other valid relationships remain auditable.
The command supports `text`, `json`, `markdown`, `--out`, `--markdown`,
`--fail-on` and `--warnings-as-errors`, following `audit spec` exit behavior.

The deterministic v1 bundle JSON has
`type="chart_contract.audit_bundle_report"`,
`schema_version="1"`, canonical manifest SHA-256, nested bound component
reports, the relationship declarations, and cross-artifact findings. The
bundle hash identifies the normalized manifest, **not a signed or authenticated
aggregate report**. To check a bundle after any inputs change, rerun the command.
`verify report` remains specific to individual saved spec reports.

The v1 rule IDs are `bundle.identity.analysis_scope`,
`bundle.identity.metric_definition`, `bundle.identity.unit`,
`bundle.identity.time_window`, and `bundle.identity.skipped`. They form a
distinct bundle surface and are **not** silently added to the existing
109-rule single-chart `audit-v0.2` profile.

## Reproduction

```bash
chart-contract audit bundle examples/traps/cross_chart_scope_mismatch.bundle.json
```

The two independent component audits should be READY; the explicit common
scope relationship BLOCKs on `bundle.identity.analysis_scope`.
See the [CLI fixtures](../examples/traps/README.md).

## Non-goals and known boundaries

Matching declarations are **not** cryptographic authentication, upstream
lineage proof, evidence-population reconstruction, or scientific certification.
A consistently mislabeled scope can pass. This does not execute arbitrary
Vega-Lite transforms, resolve SQL predicates, perform causal attribution, or
infer which cross-chart comparisons a user intended. It does not reconcile
quantitative totals across charts or establish causal comparability; those
need distinct future contracts with their own evidence.
