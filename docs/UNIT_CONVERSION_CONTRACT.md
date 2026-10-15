# Unit Conversion Contract

A chart can display one unit while the supplied evidence was measured in another.

Common failure modes include:

- USD and EUR values shown under one currency label;
- seconds and milliseconds mixed in one series;
- raw dollars presented as thousands of dollars without a reproducible scale factor;
- a fixed conversion factor changing without the artifact metadata changing.

`chart-contract` makes source/display measurement semantics explicit without silently converting data.

## First-party API

Identity semantics can record the source unit directly:

```python
Chart.compare(
    ...,
    unit="USD",
    source_unit="USD",
    conversion_kind="identity",
    conversion_factor=1.0,
    source_unit_basis_field="source_unit",
)
```

A fixed multiplicative conversion can preserve both original and displayed values:

```python
Chart.trend(
    ...,
    y="revenue_kusd",
    unit="thousand USD",
    source_unit="USD",
    conversion_kind="scale",
    conversion_factor=0.001,
    conversion_basis="1 thousand USD = 1000 USD",
    source_value_field="revenue_usd",
    source_unit_basis_field="source_unit",
)
```

The renderer does not mutate the supplied data.

## Closed version-1 metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "unit": "thousand USD",
    "unit_conversion_contract": {
      "version": 1,
      "metric_field": "revenue_kusd",
      "source_unit": "USD",
      "display_unit": "thousand USD",
      "conversion_kind": "scale",
      "conversion_factor": 0.001,
      "conversion_basis": "1 thousand USD = 1000 USD",
      "source_value_field": "revenue_usd",
      "source_unit_basis_field": "source_unit"
    }
  }
}
```

The schema is closed.

## Identity conversion

`conversion_kind="identity"` requires:

- `source_unit == display_unit`;
- `conversion_factor == 1.0`;
- `conversion_basis == null`;
- `source_value_field == null`.

The optional source-unit basis field can still prove that all supplied rows identify the same unit.

## Fixed scale conversion

`conversion_kind="scale"` requires:

- different non-empty source and display units;
- one finite positive conversion factor;
- one non-empty conversion basis;
- one source-value field distinct from the displayed metric field.

For every complete row:

```text
displayed value = source value × conversion factor
```

Both source and displayed values must be jointly present or jointly null, finite, and numeric.

The first-party renderer refuses to stamp a scale contract whose supplied values do not reproduce.

## Row-level unit identity

Rule: `data.unit.source_basis`

When `source_unit_basis_field` is declared:

- the field must exist;
- values must be non-null, non-empty strings;
- all rows must declare one source-unit identity;
- that identity must exactly match `source_unit`.

The audit does not treat `USD`, `dollars`, or `US dollars` as aliases. Unit normalization is explicit, not inferred.

## What version 1 does not do

Version 1 deliberately does not:

- fetch FX rates;
- choose a conversion factor;
- mutate or rescale source data;
- support row-varying conversion factors;
- perform inflation or constant-dollar adjustment;
- support affine/offset conversions such as Celsius to Fahrenheit;
- infer units from geography, field names, labels, or value ranges;
- validate the external authority behind a declared conversion basis.

A passing fixed-scale contract proves the declared source/display identities are structurally consistent and the supplied values reproduce under one declared multiplicative factor. It does not prove that factor is economically, scientifically, or historically appropriate.
