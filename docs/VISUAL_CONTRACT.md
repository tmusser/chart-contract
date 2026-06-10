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

## Examples

### Good Contract

```yaml
claim: Enterprise and startup segments show the highest observed conversion rates.
metric: conversion_rate
grain: customer segment
dimensions: [segment]
source: synthetic.segment_conversion
units: conversion rate
filters:
  quarter: 2026-Q2
time_window: latest synthetic snapshot
caveats:
  - Observational segment summary; not causal proof.
visual_intent: rank
chart_type: bar
```

Why this is strong:

- The claim is specific.
- The metric and grain are explicit.
- The source and units are present.
- The caveat prevents overclaiming causality.
- The visual intent and chart type match a ranked comparison.

### Weak Contract

```yaml
claim: Conversion is better.
metric: conversion_rate
grain:
dimensions: []
source:
units:
filters:
time_window:
caveats: []
visual_intent: show data
chart_type: pie
```

Why this is weak:

- The claim is vague.
- The grain, source, units, and time window are missing.
- The visual intent is not analytical.
- The chart type may not match the task.
- There is no caveat despite a performance claim.

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
