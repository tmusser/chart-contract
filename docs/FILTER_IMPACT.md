# Filter-impact evidence receipts (opt-in v1)

Vega-Lite transform declarations and structural lineage receipts can
prove that an operation exists, and that its syntax has not changed.
Neither says **how many original source rows were excluded** by that
operation. `filter_impact_contract` adds a deterministic, source-bound
row-retention calculation for a carefully restricted subset of
`transform.filter` predicates.

## Supported v1 scope

For a *single root-level view*, `chart-contract` supports **1–20
sequential filters** and at most 100,000 original input rows. Each
transform entry must contain exactly one `filter` key, whose value
is a structured Vega-Lite field predicate with one operator:

- `{"field": "segment", "equal": "Paid"}`
- `{"field": "segment", "oneOf": ["Paid", "Organic"]}`
- `{"field": "score", "gt": 10}` (also `gte`, `lt`, `lte`)

Comparisons are type-strict and evaluated only on **finite, non-null**
values. Equality supports strings, finite numbers, and booleans.
Ordering supports numeric values only. A oneOf list must contain
homogeneous scalars. Subsequent filters consume only the rows retained
by the preceding stage.

Vega-Lite expression strings, logical compositions, `range`, date
predicates, null handling, computed/aggregated fields, non-filter
transform stages, nested/layered data flows, and external data fetches
are **not** executed. If source data are not supplied or values are
unverifiable, the rule emits REVIEW rather than a false receipt PASS.
The source evidence must be the **original unfiltered rows**, not a
post-filter extract. The tool does not independently authenticate it.

## Build and verify

```python
from chart_contract import build_filter_impact_contract, build_transform_lineage

spec = {
    "mark": "point",
    "encoding": {
        "x": {"field": "segment", "type": "nominal"},
        "y": {"field": "systems", "type": "quantitative"},
    },
    "transform": [{"filter": {"field": "segment", "equal": "Core"}}],
    "usermeta": {
        "source": "warehouse.systems",
        "unit": "systems",
        "claim": "Recorded systems in the Core customer segment.",
        "transform_contract": {"declared": ["filter"]},
    },
}
spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
spec["usermeta"]["filter_impact_contract"] = build_filter_impact_contract(
    spec, original_df, minimum_retention_pct=75
)
```

The closed `usermeta.filter_impact_contract` has exactly:

```json
{
  "version": 1,
  "minimum_retention_pct": 75.0,
  "receipts": [
    {
      "location": "transform[0].filter",
      "operation_sha256": "<canonical operation hash>",
      "input_count": 8,
      "retained_count": 5,
      "excluded_count": 3,
      "retained_pct": 62.5
    }
  ]
}
```

Each receipt records **its stage's denominator**. Thus, when two
filters are chained, the second stage starts from the first stage's
retained rows. The threshold applies to *final rows divided by
original input rows*, not the latest stage's denominator. Percentages
are stored to 6 decimal places, but threshold comparison uses the
unrounded full-source ratio.

`data.filter.receipts` independently recomputes all recorded counts
and operation hashes from the supplied source rows on every spec
audit. It **FAILs/BLOCKs** malformed, inconsistent, stale or forged
claims. It **WARNs/REVIEWs** when the predicate/evidence is outside
the supported subset; this is not a verified source count.

`data.filter.retention` emits the verified overall retention share.
It **WARNs/REVIEWs** below a declared minimum or when a declared
minimum cannot be evaluated. Otherwise, it **PASSes** with a
descriptive message and the original row counts. With no minimum,
the rule does not invent a universal allowable exclusion percentage.

**Both rules are opt-in.** Existing specs without
`filter_impact_contract` remain governed by the existing transform
inventory, declaration and structural lineage rules.

## Deterministic trap

```bash
chart-contract audit spec examples/traps/high_filter_exclusion.vl.json \
  --data examples/traps/high_filter_exclusion.csv \
  --claim "$(cat examples/traps/high_filter_exclusion.claim.txt)" \
  --warnings-as-errors
```

Expected: source receipt PASS; retention WARN for 5/8 (62.5%)
against a declared 75% minimum. With `--warnings-as-errors`,
the overall REVIEW becomes a nonzero CI exit.

## Trust boundary

This is a **row-retention audit, not a coverage-validity test**.
It does not decide whether omitted segments were legitimate, verify
upstream extraction, run arbitrary filters, or prove representativeness.
Changing the filter or minimum to force a passing result would
misrepresent the operator's analytical intent. Spec and report
bindings capture the declared contract and recomputed findings, but
do not authenticate the original data source.
