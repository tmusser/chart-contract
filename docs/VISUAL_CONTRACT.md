# Visual Contract

## Contract Fields

A chart should declare:

- claim
- metric
- grain
- dimensions
- source
- units
- filters
- time window if temporal
- caveats if causal, incomplete, or observational
- visual intent
- chart type

## Good Contract

```yaml
claim: "Enterprise win rate is higher than SMB in both regions."
metric: "win_rate"
grain: "segment x region"
dimensions: ["segment", "region"]
source: "warehouse.pipeline_summary"
units: "win rate"
filters:
  quarter: "2026-Q2"
caveat: "Observed pipeline summary; not causal attribution."
visual_intent: "compare"
chart_type: "grouped bar"
```

## Weak Contract

```yaml
claim: "The launch worked."
metric: "conversion"
source: ""
units: ""
filters: {}
caveat: ""
visual_intent: "chart"
chart_type: "pie"
```

## v0.1 Intent Mapping

- `trend` -> line chart
- `rank` -> sorted bar chart
- `compare` -> bar chart, optionally grouped

## Audit Categories

- data contract
- visual form
- claim support
- labels and units
- scale and axis risk
- provenance
- caveats
- accessibility/readability
- Tufte-inspired visual integrity

The contract exists so the claim and the visual form can be judged together before the chart is shared.
