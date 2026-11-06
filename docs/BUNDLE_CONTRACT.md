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

## Cross-chart additive total reconciliation

A new, typed `sum_reconciliation` relationship compares **two independently
rendered chart artifacts**: a one-row headline total and a categorical
breakdown whose components are explicitly declared exhaustive. It is an
additional version-1 bundle relationship shape; the existing untyped
`artifact_ids` / `equal_on` identity contracts remain unchanged.

```json
{
  "kind": "sum_reconciliation",
  "id": "sales_breakdown_matches_headline",
  "total_artifact_id": "headline",
  "components_artifact_id": "breakdown",
  "total_metric_field": "sales_total",
  "component_field": "channel",
  "component_metric_field": "channel_sales",
  "components_exhaustive": true,
  "tolerance": 0.0
}
```

Place this object in `relationships` with both artifacts listed in
`artifacts`. The two artifact IDs must differ. The metric fields may
have **different source column names**, but the two specs must declare
identical non-empty additive `unit` and value-representation semantics;
percent, rate, and ratio units cannot be summed by this contract.
`components_exhaustive: true` is an explicit obligation—not proof that
upstream component categories were defined correctly.

The headline must be one directly displayed **finite numeric value in
exactly one source row**. The breakdown must show its component categories
on nominal/ordinal x and numeric amounts on y. Both use simple untransformed
bar/point charts, without aggregation, Vega-Lite filters, binning, stacks
or hidden transformations. Every supplied component must have a non-empty,
unique label and a complete finite metric value. No observed rows may be
automatically imputed, filtered, grouped, or replaced with an "Unknown"
balancing category.

The bundle reruns each component's full `audit_spec` gate first.
If either artifact `BLOCK`s, the comparison reports
`bundle.reconciliation.skipped: WARN`, **not a fabricated PASS**.
Otherwise the cross-chart rules are:

- `bundle.reconciliation.evidence: PASS/FAIL`: two charted evidence sets
  are compatible, complete, and reconstructable from source rows, with
  matching additive units.
- `bundle.reconciliation.total: PASS/FAIL`: compare the source headline
  value to the sum of all source components within the declared *absolute*
  tolerance. A mismatch includes the numeric residual and, where meaningful,
  the percentage of the headline represented.
- The bundle `BLOCK`s if either cross-chart rule FAILs, even when both
  individual charts report READY.

Use an independent `equal_on` relationship for `analysis_scope`,
`metric_definition` and/or `time_window` if those identities must also
match. **Arithmetic equality alone does not prove two charts share the same
metric definition, source population, time period, or reporting cut.**

The sum relationship does not use a static, self-declared control total from
the breakdown chart. It derives the control from the *separate headline's*
source evidence, while reusing the existing single-chart component validation.

Reproduce the trap:

```bash
chart-contract audit bundle examples/traps/cross_chart_total_gap.bundle.json
```

The headline source contains 1,000 systems and the three reported channels
contain 500 + 300 + 120 = 920. Both component charts are individually
READY; `bundle.reconciliation.evidence` PASSes while the total comparison
BLOCKs with an 80-system residual.

## Verdict and report

The bundle re-audits all component specs using `audit_spec`, carrying forward
their complete, content-bound reports (input and report bindings plus profile
digests) in JSON output. Historical report files are not trusted as substitutes.
The bundle verdict uses the worst of its component verdicts and relationship
findings:

- `READY`: all component audits READY and all declared identity and additive relationships pass.
- `REVIEW`: at least one component REVIEW; no BLOCK.
- `BLOCK`: a component BLOCK, a required identity or additive-evidence check fails, or a declared cross-chart relationship disagrees.

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

The bundle identity rules are `bundle.identity.analysis_scope`,
`bundle.identity.metric_definition`, `bundle.identity.unit`,
`bundle.identity.time_window`, and `bundle.identity.skipped`.
The separate arithmetic rules are `bundle.reconciliation.evidence`,
`bundle.reconciliation.total`, and `bundle.reconciliation.skipped`.
They belong to the **bundle-only** surface and are not counted in the
120-rule single-chart `audit-v0.2` profile.

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
infer which cross-chart comparisons a user intended. The optional
`sum_reconciliation` relation verifies a narrow additive comparison only;
it cannot authenticate control-source authority, component taxonomies,
upstream completeness or causal comparability.
