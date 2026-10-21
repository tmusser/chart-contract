# Metric Target Contract

A metric can have an explicit business target even when its directionality is already known.

"Lower is better" does not tell you whether 195 ms met a 200 ms target.
"Conversion improved" does not tell you whether 81% cleared an 80% threshold.

Version 1 makes target evaluation explicit and reproducible.

## First-party API

```python
Chart.trend(
    data=df,
    x="period",
    y="quality_score",
    claim="Quality score met target.",
    source="warehouse.quality",
    unit="points",
    metric_target=80,
    target_operator="at_least",
    target_selector_field="period",
    target_selector_value="after",
    target_tolerance=0.0,
)
```

Supported operators:

- `at_least`
- `at_most`
- `equal`

The selected observation must resolve to exactly one supplied row.

## Closed version-1 metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "target_contract": {
      "version": 1,
      "metric_field": "quality_score",
      "selector_field": "period",
      "selector_value": "after",
      "target_value": 80.0,
      "operator": "at_least",
      "tolerance": 0.0,
      "observed_value": 81.0,
      "target_gap": 1.0,
      "target_met": true
    }
  }
}
```

The schema is closed.

## Target arithmetic

For observed value `x`, target `t`, and absolute tolerance `e`:

```text
at_least -> x >= t - e
at_most  -> x <= t + e
equal    -> abs(x - t) <= e
```

The durable receipt also records:

```text
target_gap = observed_value - target_value
```

The sign of `target_gap` is descriptive only. Whether a positive or negative gap is favorable depends on the declared target operator and any separate metric-directionality semantics.

## One explicit observation

Version 1 never assumes the latest row, last row, rightmost bar, or maximum date is the observation to test.

The caller declares:

- `target_selector_field`
- `target_selector_value`

That selector must match exactly one row and the selected metric value must be finite numeric evidence.

## Visible target line

First-party trend/compare specs draw the scalar target as a rule.

External specs with `target_contract` must also visibly encode a rule at the exact declared target value.

Target metadata that survives after the line is deleted or moved fails `visual.metric.target`.

The target rule is a declared threshold, not source evidence; first-party rendering uses a datum-backed rule rather than inventing a source-data row.

## Narrow claim parity

Version 1 recognizes only explicit target-status wording such as:

- `met target`
- `meets target`
- `hit target`
- `reached target`
- `target was met`
- `missed target`
- `target was missed`

Explicit met/missed wording without a target contract produces `REVIEW`.

A claim saying the target was met when the contract recomputes `target_met=false`, or vice versa, blocks.

Phrases such as `above target`, `below target`, `on track`, `healthy`, or `acceptable` are intentionally outside v1 rather than being interpreted loosely.

## Relationship to directionality

Directionality and target semantics are independent contracts.

`metric_direction="lower_is_better"` describes how movement is evaluated.

`target_operator="at_most"` declares the threshold condition.

A passing target contract does not prove that the threshold is a valid optimization target, and chart-contract does not infer target operators from metric directionality.

## What version 1 does not prove

A passing target contract does **not** prove:

- the target is authoritative;
- the target was chosen rationally;
- meeting the target is materially important;
- the target is achievable;
- the target should be optimized causally;
- there are no tradeoffs with other metrics;
- an acceptable range or utility curve exists;
- the selected observation is the fairest reporting point;
- target attainment is statistically significant.

It proves only that one explicit observation, one scalar threshold, one operator, one tolerance, the visible rule, and narrow met/missed wording are mutually consistent.
