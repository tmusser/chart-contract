# Dual-axis review (structural Vega-Lite audit)

A dual-axis overlay is not automatically invalid, but it can suggest a
relationship between measures whose relative visual positions depend
on independently chosen y-axis scales.

## What triggers the review

The spec-audit rule `visual.dual_axis.review` emits `WARN` when
both conditions hold **within one layered plot group**:

1. The layer group explicitly declares
   `"resolve": {"scale": {"y": "independent"}}`.
2. Its unit marks encode at least two **distinct quantitative y
   measures**. Source field identity, aggregation, time unit and bin
   definitions distinguish measures.

The rule accounts for shared/inherited encoding fields and nested
layers. It emits one finding per offending layered group with the
precise `resolve.scale.y` path. It does not count `y2` as a second
scale, or conflate independent *x*/*color* scales with independent y.

It does **not** flag two separate plots in an `hconcat`, `vconcat`
or `concat`, a common y scale, or a line-and-points overlay of the
same y measure. Purely categorical or constant reference axes are
not treated as a second quantitative source measure.

## Severity and remediation

This rule produces **REVIEW**, not BLOCK. Dual y axes are a valid,
supported Vega-Lite feature and can be consciously chosen. The audit
does not declare the data correlated/uncorrelated, infer causal effects,
judge the subject matter or silently replace the visual.

When it flags a chart, check labels, domain choices, and the actual
data relationship. Consider small multiples with comparable x axes
if the relationship is a decision-critical claim. If retaining dual
axes, explain that visual alignment can be sensitive to the separate
y scales. Suppressing or changing source observations to make the
warning disappear is inappropriate.

This is a **structural spec check**, not a render simulation, source
verification, statistical correlation test, or universal validation of
Vega-Lite composition semantics. It only audits explicit independent
y resolution on overlaid quantitative layer measures.

## Reproducible trap

```bash
chart-contract audit spec examples/traps/dual_axis_spend_sales.vl.json \
  --data examples/traps/dual_axis_spend_sales.csv \
  --claim "$(cat examples/traps/dual_axis_spend_sales.claim.txt)" \
  --warnings-as-errors
```

The synthetic chart overlays `ad_spend` (USD) and `sales`
(systems sold) across four weeks. It must yield `REVIEW` and
`WARN visual.dual_axis.review`; warnings-as-errors makes the
CLI exit nonzero.

Vega-Lite references:
[scale resolution](https://vega.github.io/vega-lite/docs/resolve)
and [official dual-axis example](https://vega.github.io/vega-lite/examples/layer_dual_axis.html).
