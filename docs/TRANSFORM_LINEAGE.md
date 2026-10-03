# Transform Lineage Receipts

Transform-kind declarations answer **what kind of transformation exists**.

Lineage receipts answer a stronger deterministic question:

**Does the metadata still describe the exact transform structure in this spec?**

## Receipt shape

For every auditable transform occurrence, `chart-contract` can build a structural receipt:

```json
{
  "kind": "calculate",
  "location": "transform[1].calculate",
  "operation_sha256": "<64 lowercase hex characters>",
  "input_fields": ["revenue", "users"],
  "output_fields": ["revenue_per_user"]
}
```

Receipts live under:

```json
{
  "usermeta": {
    "transform_lineage": {
      "version": 1,
      "receipts": []
    }
  }
}
```

Use the public helper after the transform structure is final:

```python
from chart_contract import build_transform_lineage

spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
```

## What the digest covers

For explicit transform-array entries, `operation_sha256` hashes the complete canonical JSON
object for that transform entry.

That means changing any structural transform parameter changes the receipt, including examples
such as:

- a filter expression;
- a calculate expression;
- a `groupby` field;
- a window sort;
- an aggregate operation;
- density bounds;
- transform output names.

JSON mapping key order does not affect the digest.

Encoding-level transforms such as `aggregate`, `bin`, `stack`, and `timeUnit` receive
bounded semantic payload receipts containing the transformed field and operator configuration.

## Field lineage

Receipts also expose bounded, structural input/output field lineage where Vega-Lite makes it
recoverable without executing code.

Examples:

- `calculate`: input fields referenced as `datum.field` or `datum["field"]`; output from `as`;
- `aggregate`, `joinaggregate`, `window`: operation fields, grouping fields, and explicit `as` outputs;
- `density`: density field + grouping inputs, explicit `as` outputs;
- `fold` / `flatten`: listed inputs and explicit outputs;
- `regression` / `loess`: response/on/grouping inputs and explicit outputs;
- encoding-level aggregate/bin/time-unit transforms: source field only.

Field lineage is deliberately best-effort and bounded. An empty output list can mean Vega-Lite
does not expose one stable explicit output field in that syntax; it does not mean the
transformation has no output.

## Audit behavior

Rule: `transform.lineage.receipts`

For specs with auditable transforms:

- exact receipt parity -> `PASS`;
- missing lineage metadata -> `FAIL`;
- malformed receipts -> `FAIL`;
- changed operation payload -> `FAIL`;
- missing receipt -> `FAIL`;
- stale receipt -> `FAIL`.

For a spec with no auditable transforms:

- no lineage metadata -> `PASS`;
- exact empty version-1 lineage -> `PASS`;
- stale non-empty receipts -> `FAIL`.

## First-party renderers

First-party renderers stamp lineage after Altair has produced the final Vega-Lite transform
structure.

This matters because the receipt binds what the renderer actually emitted rather than a
hand-written approximation of the intended transform.

Current transformed first-party examples include:

- histograms: encoding-level bin + aggregate receipts;
- violins: density-transform receipt.

## Important boundary

A matching receipt is **not execution evidence**.

It does not prove:

- a calculate expression returns the intended quantity;
- a filter selects the correct population;
- a regression or loess model is scientifically appropriate;
- a lookup source is correct;
- an upstream SQL/dbt/Python transformation produced the supplied data;
- the listed input/output fields are complete semantic lineage for arbitrary expressions.

The receipt proves that the declared structural metadata matches the current Vega-Lite
transform syntax under chart-contract's bounded parser.

## Relationship to other bindings

Three different identities remain intentionally separate:

1. `transform_contract.declared` — unique transform kinds.
2. `transform_lineage` — occurrence-level structural transform identity and bounded field lineage.
3. report/spec input bindings — identity of the full audited artifact and saved audit result.

This separation avoids treating one digest as proof of analytical correctness or upstream
provenance.
