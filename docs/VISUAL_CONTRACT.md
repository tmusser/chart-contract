# Visual Contract

## Contract Fields

A chart should declare:

- claim
- metric or membership evidence
- grain or universe member
- dimensions or set columns
- source
- units when quantitative
- filters
- time window if temporal
- caveats if causal, incomplete, observational, or visually schematic
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
filters: none
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

### Good Set Membership Contract

```yaml
claim: Email and paid search overlap for two of six customers.
member: customer_id
sets: [email, paid_search]
universe: one row per customer
source: synthetic.channel_reach
filters: none
caveats:
  - Schematic geometry; labeled region counts are authoritative.
visual_intent: set_membership
chart_type: venn_style
```

Why this is strong:

- The universe member is explicit and unique.
- The two membership columns preserve row-level evidence.
- The claim can be checked against A-only, overlap, B-only, and neither counts.
- The caveat prevents readers from treating circle area as quantitative.
- The intent is limited to two sets rather than pretending many-set circles stay readable.

### Weak Contract

```yaml
claim: Conversion is better.
metric: conversion_rate
grain: ""
dimensions: []
source: ""
units: ""
filters: ""
time_window: ""
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

## Intent Mapping

- `trend` -> line chart
- `rank` -> sorted bar chart
- `compare` -> bar chart, optionally grouped
- `histogram` -> binned bar chart
- `boxplot` -> boxplot
- `violin` -> density area
- `qq` -> quantile points plus fitted reference line
- `ecdf` -> step line
- `residual` -> points plus zero reference line
- `set_membership` -> labeled, schematic two-set Venn-style view

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
