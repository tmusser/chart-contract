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
