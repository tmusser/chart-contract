# Vega-Lite Transform Contract

Explicit Vega-Lite transformations can change the analytical evidence presented by a chart even when the source rows and chart encodings look ordinary.

`chart-contract` therefore treats transform structure as part of the auditable artifact.

## What is inventoried

The transform inventory records explicit Vega-Lite transform kinds and their exact spec locations.

Supported explicit transform operators are:

- `aggregate`
- `bin`
- `calculate`
- `density`
- `extent`
- `filter`
- `flatten`
- `fold`
- `impute`
- `joinaggregate`
- `loess`
- `lookup`
- `pivot`
- `quantile`
- `regression`
- `sample`
- `stack`
- `timeUnit`
- `window`

The inventory also recognizes encoding-level `aggregate`, `bin`, `stack`, and
`timeUnit` operations, including supported shorthand forms such as
`mean(revenue):Q`.

Each detected occurrence becomes a `transform.inventory` finding with its exact location,
for example:

```text
PASS transform.inventory: Detected explicit Vega-Lite transform kind 'filter'.
field=layer[0].transform[0].filter
```

A malformed transform entry that cannot be classified as exactly one supported operator
blocks via `transform.inventory`.

## Declaration contract

Any spec with detected transforms must carry an exact transform-kind declaration:

```json
{
  "usermeta": {
    "transform_contract": {
      "declared": ["aggregate", "filter"]
    }
  }
}
```

The declaration is a unique list of transform-kind names.

The audit compares the declaration with the unique kinds detected from the spec:

- exact match -> `PASS`
- detected transform omitted from metadata -> `FAIL`
- stale declared transform no longer present -> `FAIL`
- malformed declaration -> `FAIL`
- transforms present with no declaration -> `FAIL`
- no transforms and no declaration -> `PASS`

Ordering does not matter; semantic set equality does.

## First-party renderers

First-party renderers declare the transforms they emit.

Current examples:

- `Chart.histogram()` declares `aggregate` and `bin`.
- `Chart.violin()` declares `density`.

The declaration is preserved in Vega-Lite `usermeta` so a later spec audit can compare the
artifact with its declared transform kinds.

## Important boundary: inventory is not execution

`chart-contract` does **not** execute arbitrary Vega-Lite transforms as part of this policy.

That means a matching declaration does not prove:

- a `calculate` expression is correct;
- a `filter` preserves the intended population;
- a `window` computation is appropriate;
- a lookup source is accurate;
- a regression/loess transform is scientifically justified;
- a transformed output field can be reconstructed from the supplied raw data.

The existing data-contract rules still apply independently. If an encoded field is not
present in the supplied evidence and chart-contract cannot deterministically reconstruct it,
the audit may still block even when the transform declaration itself matches.

This separation is deliberate: **declared transform structure is inspectable provenance, not
a claim that chart-contract reproduced or validated the transformation.**

## User intent and authorization

The transform declaration is not a user-consent flag.

Existing policies such as `user_requested_scale_override` and
`user_requested_normalization` remain separate because they represent different questions.

A spec can therefore have an exact transform declaration and still fail another policy rule.

## Durable reports

The spec itself is already covered by chart-contract input binding, and the audit findings are
covered by schema-0.4 report binding.

Therefore:

- adding/removing/changing a transform changes the bound spec identity;
- a fresh audit exposes the new transform inventory;
- stale transform declarations fail;
- changing transform-policy rules changes the audit-profile semantic identity.

This is deterministic drift detection, not cryptographic attestation or analytical
certification.
