# Control-Total Reconciliation Contract

A component chart can be mechanically clean while omitting or double-counting part of the business.

`chart-contract` can bind an additive rank/compare decomposition to one explicit scalar control total and recompute how much of that total the displayed component evidence accounts for.

## First-party API

```python
chart = Chart.rank(
    data=df,
    x="region",
    y="revenue",
    claim="Regional revenue components are shown.",
    source="warehouse.region_revenue",
    unit="USD",
    control_total=11_800_000,
    control_total_source="finance.company_revenue",
    reconciliation_tolerance=1.0,
)
```

Version 1 is intentionally limited to `rank` and `compare` component decompositions.

It does not treat trend/time rows as additive components.

## Closed version-1 metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "reconciliation_contract": {
      "version": 1,
      "component_field": "region",
      "metric_field": "revenue",
      "reconciliation": "sum",
      "control_total": 11800000.0,
      "control_total_source": "finance.company_revenue",
      "tolerance": 1.0,
      "component_count": 4,
      "component_total": 11800000.0,
      "residual": 0.0,
      "represented_share": 1.0
    }
  }
}
```

The schema is closed.

## Component evidence

Version 1 requires:

- one visible component field;
- one visible additive quantitative metric;
- non-null, non-blank component labels;
- exactly one supplied row per component;
- complete finite numeric metric values.

Duplicate component labels block rather than being silently summed.

If a decomposition legitimately needs multiple rows per component, aggregate it upstream or use a future explicit aggregation contract rather than relying on hidden summation.

## Control-total arithmetic

For supplied component metric values `x_i`:

```text
component_total = sum(x_i)
residual = control_total - component_total
```

The reconciliation passes when:

```text
component_total ~= control_total
```

using the declared non-negative absolute `reconciliation_tolerance` plus only a tiny floating-point comparison tolerance.

When all component values are non-negative and the control total is positive:

```text
represented_share = component_total / control_total
```

This receipt makes a failure easy to interpret.

Example:

```text
component total = 9.1M
control total   = 11.8M
residual        = 2.7M
represented     = 77.1%
```

## No automatic Unknown bucket

A failed reconciliation is evidence that the decomposition needs investigation.

`chart-contract` does not repair the chart by creating an `Unknown`, `Other`, or balancing component automatically.

The residual may represent:

- omitted categories;
- duplicate/double-counted categories;
- different source scopes;
- stale control totals;
- upstream joins or filters;
- legitimate accounting adjustments not represented by the component taxonomy.

The audit cannot determine which explanation is correct.

## Additive boundary

Version 1 uses fixed `sum` semantics only.

Percent/rate/ratio metrics are rejected because summing them is not a generic valid reconciliation operation.

A passing sum contract proves arithmetic consistency against the declared control total. It does not prove the metric is substantively additive in every business context.

## Control-total provenance

`control_total_source` is optional descriptive metadata.

It can record that the scalar control came from a different authoritative system or table than the component evidence.

A non-empty source label does not authenticate that system or prove the control total is correct.

## What version 1 does not prove

A passing reconciliation contract does **not** prove:

- the control total is authoritative or correct;
- the component taxonomy is conceptually complete;
- components are mutually exclusive upstream;
- the metric should be additive beyond the declared use;
- joins, filters, or source ingestion are correct;
- the residual identifies a specific missing category;
- accounting adjustments have been modeled correctly.

It proves only that the supplied unique component rows, durable receipts, and declared scalar control total are arithmetically consistent within the declared tolerance.
