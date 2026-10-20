# Metric Directionality Contract

A numeric increase is not automatically an improvement.

For some metrics, higher values are better. For others, lower values are better. Some metrics are
descriptive only and should not be given a better/worse interpretation by chart-contract.

Version 1 makes that semantic explicit for trend and comparison artifacts.

## First-party API

```python
Chart.trend(
    data=df,
    x="period",
    y="latency_ms",
    claim="Latency worsened after launch.",
    source="warehouse.latency",
    unit="milliseconds",
    metric_direction="lower_is_better",
    baseline_field="period",
    baseline_value="before",
    target_value="after",
    change_type="absolute",
    declared_change=50,
)
```

Supported directions:

- `higher_is_better`
- `lower_is_better`
- `neutral`

## Closed version-1 metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "directionality_contract": {
      "version": 1,
      "metric_field": "latency_ms",
      "direction": "lower_is_better"
    }
  }
}
```

The schema is closed and the metric field must remain visibly quantitative.

## Evaluative claim semantics

Version 1 deliberately recognizes only narrow evaluative wording:

Improvement-like:

- improve / improved / improvement / improving
- better

Worsening-like:

- worse / worsened / worsening
- deteriorate / deteriorated / deterioration / deteriorating

Plain directional wording such as `increased`, `decreased`, `rose`, or `fell` is not
treated as a better/worse judgment.

When evaluative wording appears:

1. metric directionality must be declared;
2. an explicit comparison baseline must be available;
3. the baseline and target metric values must imply the same evaluative direction as the claim.

Example:

```text
metric: latency_ms
direction: lower_is_better
baseline: 200
target:   250
claim:    "Latency improved."
```

The arithmetic change is valid, but under lower-is-better semantics 200 -> 250 is worsening.
The claim therefore blocks.

## Neutral metrics

`direction="neutral"` means chart-contract has no declared basis for calling movement better
or worse.

An evaluative claim against a neutral metric blocks. Descriptive increase/decrease wording is
still allowed.

## Missing metadata

An evaluative claim without a directionality contract produces REVIEW.

An evaluative claim with directionality but without an explicit comparison baseline also
produces REVIEW because the better/worse statement cannot be reproduced against selected
baseline and target observations.

## What version 1 does not do

A passing directionality contract does not prove:

- the metric is a valid optimization objective;
- maximizing/minimizing it is causally beneficial;
- there are no tradeoffs with other metrics;
- the business utility is monotonic over all values;
- a target threshold exists or is appropriate;
- movement is materially important;
- the observed comparison is statistically significant;
- the selected baseline is analytically fair.

Version 1 does not infer targets, acceptable ranges, utility curves, or business thresholds.
It only binds narrow evaluative language to one declared monotonic direction and one explicit
baseline comparison.
