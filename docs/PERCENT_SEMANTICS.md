# Percent Value Semantics

Percent labels are ambiguous unless the raw numeric representation is explicit.

The same displayed value can come from different raw scales:

- `0.42` with `value_representation="fraction"` means 42%.
- `42` with `value_representation="percentage_points"` means 42%.

`chart-contract` does not inspect the observed values and guess which representation the author intended.

## First-party contract

For a percent-valued metric, declare both the unit and the raw representation:

```python
chart = Chart.trend(
    data=df,
    x="week",
    y="conversion_rate",
    claim="Observed conversion increased.",
    source="warehouse.funnel",
    unit="percent",
    value_representation="fraction",
)
```

Supported percent units are `percent`, `percentage`, and `%`.

Supported representations are:

- `fraction`: raw `0.42` represents 42%.
- `percentage_points`: raw `42` represents 42%.

A percent unit with no representation produces `REVIEW` via
`labels.percent.representation`. Unsupported or contradictory representation metadata
produces `BLOCK`.

A `value_representation` declaration without explicit percent unit/presentation semantics
also blocks. The field is deliberately not treated as a generic numeric-scaling switch.

## Rendering behavior

The first-party renderer never rescales the underlying data.

For `fraction` values it applies Vega-Lite percent formatting to the quantitative metric axis
and tooltip, so raw `0.42` is presented as 42%.

For `percentage_points` values it preserves the raw scale and does not apply Vega-Lite's
percent formatter, because that formatter would multiply `42` by 100 for display.

The representation is preserved in `usermeta.value_representation` so downstream spec audits
can recover the same contract.

## External Vega-Lite specs

Spec audits recognize explicit percent presentation when either:

- `usermeta.unit` is `percent`, `percentage`, or `%`; or
- a quantitative axis explicitly uses a Vega-Lite/D3 percent format.

Rules:

- missing `usermeta.value_representation` -> `WARN`;
- unsupported/malformed representation -> `FAIL`;
- `fraction` without an explicit percent axis format -> `WARN`;
- `percentage_points` with a percent formatter -> `FAIL`;
- matching representation/format semantics -> `PASS`.

## Deliberate boundary

This contract is about **representation**, not metric correctness.

It does not infer whether a column named `rate` is a probability, percent, events per unit
time, ratio, index, or some other rate. A generic `unit="rate"` is therefore not silently
treated as percent.

It also does not infer representation from value ranges. Values above 1 can be legitimate
fractional growth rates, and values below 1 can be legitimate percentage-point values. Range
heuristics would create false certainty.

No audit result proves that the upstream numerator, denominator, population, or aggregation is
correct. The rule only keeps raw-number-to-percent presentation semantics explicit and
inspectable.
