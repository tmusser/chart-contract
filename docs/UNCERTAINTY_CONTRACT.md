# Uncertainty Interval Contract

Error bars are not self-describing.

A visible interval can represent a confidence interval, credible interval, prediction interval,
bootstrap interval, or something else entirely. `chart-contract` makes the interval fields
and semantics explicit without turning interval overlap into a significance test.

## First-party API

Version 1 supports uncertainty intervals on `trend` and `compare`:

```python
chart = Chart.trend(
    data=df,
    x="period",
    y="estimate",
    claim="Observed estimates are shown with a 95% confidence interval.",
    source="warehouse.model_output",
    unit="users",
    interval_lower_field="lower",
    interval_upper_field="upper",
    interval_kind="confidence",
    interval_level=0.95,
    interval_method="wald",
)
```

The estimate field is the chart's existing `y` metric.

Supported interval kinds:

- `confidence`
- `credible`
- `prediction`
- `bootstrap`

The method is an explicit non-empty identity such as `wald`, `posterior_quantiles`, or
`percentile_bootstrap`. chart-contract does not infer method semantics from the bound values.

## Closed version-1 metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "uncertainty_contract": {
      "version": 1,
      "estimate_field": "estimate",
      "lower_field": "lower",
      "upper_field": "upper",
      "interval_kind": "confidence",
      "interval_level": 0.95,
      "interval_method": "wald"
    }
  }
}
```

The estimate, lower, and upper fields must be distinct.

`interval_level` must be finite and strictly between 0 and 1.

## Bound evidence

For every supplied observation:

```text
lower <= estimate <= upper
```

The estimate/lower/upper values must also be:

- jointly complete for every row;
- numeric;
- finite.

A malformed or stale bound blocks.

## Visible binding

First-party trend and compare renderers visibly encode the declared interval using a rule layer.

For external Vega-Lite specs, the audit requires one visible rule layer with either:

```text
y  = lower_field
y2 = upper_field
```

or:

```text
x  = lower_field
x2 = upper_field
```

If the metadata survives but the interval layer is deleted or rewired, the artifact blocks.

## Explicit claim parity

Version 1 parses only narrow explicit phrases:

- `95% confidence interval`
- `95% CI`
- `90% credible interval`
- `80% prediction interval`
- `95% bootstrap interval`

If explicit interval wording appears but no uncertainty contract is present, the artifact
requires `REVIEW`.

If both are present, interval kind and level must exactly match the contract.

General phrases such as "uncertain," "likely," or "error bars" are deliberately not converted
into formal interval semantics.

## What version 1 does not do

A passing uncertainty contract does **not** prove:

- nominal coverage is achieved;
- model assumptions are valid;
- a confidence interval has a Bayesian interpretation;
- a credible interval has frequentist coverage;
- the bootstrap procedure is appropriate;
- prediction intervals are calibrated;
- interval overlap or non-overlap implies statistical significance;
- one interval is more precise or scientifically preferable;
- a null hypothesis should be accepted or rejected.

chart-contract verifies field binding, interval identity, explicit claim parity, and deterministic
bound integrity. Statistical interpretation remains outside the v1 audit boundary.
