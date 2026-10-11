# Aggregation Grain Contract

Analytical charts need an explicit answer to a basic question:

**What does one source row represent?**

A chart can otherwise survive join fanout, duplicate entity-period rows, or hidden many-to-one
collapse while still looking plausible.

Version 1 separates:

- **source grain**: the fields that uniquely identify one supplied row;
- **output grain**: the visible categorical/temporal dimensions in the chart;
- **aggregation**: the explicit operation used when many valid source rows map to one output key.

## First-party charts

`trend`, `rank`, and `compare` accept:

```python
grain_fields=["account_id", "month"]
```

First-party rendering does **not** aggregate.

If multiple unique source-grain rows map to one displayed key, the chart blocks and rendering
refuses. Aggregate upstream deliberately, then pass one row per displayed grain.

This preserves the repo's no-auto-correction boundary: chart-contract never guesses
`sum` versus `mean`.

## Source-grain uniqueness

Rule: `data.grain.unique`

Declared source-grain fields must:

- exist;
- be non-null;
- be unique across supplied rows.

Duplicate source-grain keys block.

Example:

```text
account_id   month     revenue
A            2026-09   100
A            2026-09   100
B            2026-09   200
```

If the declared grain is `["account_id", "month"]`, the duplicate A/September rows are a
deterministic fanout signal.

The audit does not silently deduplicate or aggregate them.

## Missing grain declaration

Rule: `contract.grain.declared`

If repeated rows share the displayed grain and no source grain is declared, the chart/spec
produces REVIEW.

If no repeated displayed keys exist, missing grain metadata remains acceptable.

This keeps v1 focused on places where row identity materially changes interpretation.

## External aggregate specs

External Vega-Lite specs may declare a closed v1 grain contract:

```json
{
  "usermeta": {
    "grain_contract": {
      "version": 1,
      "source_grain_fields": ["account_id", "month"],
      "output_grain_fields": ["month"],
      "aggregation": {"op": "sum", "field": "revenue"},
      "source_row_count": 4,
      "source_unique_grain_count": 4,
      "output_group_count": 2
    }
  }
}
```

Version 1 supports one encoding-level aggregate metric operation:

- `sum`
- `mean`
- `median`
- `min`
- `max`
- `count`
- `distinct`

The declaration must exactly match the Vega-Lite encoding aggregate.

The aggregate remains independently covered by:

- `transform.inventory`
- `transform.declaration`
- `transform.lineage.receipts`

The grain contract adds the missing semantic layer: what rows are being collapsed into what
displayed unit.

## Receipts

The contract records:

- source row count;
- unique source-grain count;
- output group count.

Those counts are recomputed on spec audit. Stale receipts block.

## What this does not prove

A passing grain contract does not prove:

- the declared entity key is the correct business key;
- upstream joins are complete;
- `sum`, `mean`, or another aggregate is analytically appropriate;
- upstream pre-aggregation was performed correctly when only aggregated rows are supplied;
- duplicate-free data are free from all fanout or entity-resolution errors.

It proves a narrower contract:

**Given the supplied evidence, are rows unique at the declared source grain, and is any
many-to-one collapse into the displayed grain explicit and structurally consistent?**
