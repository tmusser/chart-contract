# Logarithmic Axis Source-Visibility Audit

The deterministic `visual.scale.log_domain` rule checks numerical source
observations against explicit Vega-Lite quantitative x/y log scales.

A standard log scale cannot represent zero. Its domain must be entirely
strictly positive **or entirely strictly negative**. Vega-Lite supports
negative-only log domains, so rejecting every negative value would be a
false positive. Crossing from negative to positive is invalid on one
logarithmic axis.

This rule is independent of user-requested zoom authorization:
`scale.type="log"` without any explicit `domain` can still hide evidence.

## Example

```json
{
  "mark": "line",
  "encoding": {
    "x": {"field": "week", "type": "ordinal"},
    "y": {
      "field": "net_return",
      "type": "quantitative",
      "scale": {"type": "log"}
    }
  }
}
```

With source values `[3, 5, -80, 11]`, this chart BLOCKs because one log
domain cannot represent both signs. For data `[-100, -10, -5, -1]`,
a negative-only logarithmic axis can PASS.

## Severity and evidence rules

- **FAIL / BLOCK:** Zero present; both positive and negative source values;
  explicit fixed domain includes/crosses zero; or all source values have the
  opposite sign from a known strictly positive/negative domain.
- **PASS:** All directly plotted source observations are finite, nonzero,
  same-sign and compatible with the declared domain (or inferred domain).
  Negative-only source values are supported.
- **WARN / REVIEW:** Source rows are unavailable/invalid/partially null;
  scope is transformed, aggregated, layered, or unsupported; or dynamic,
  partial, or malformed scale domain cannot be independently verified.
- **No finding:** No explicit `scale.type="log"` on a quantitative x/y
  encoding. Linear, symlog, and implicit scale defaults are unaffected.

For source checks, the audit supports simple untransformed line, point,
circle, bar, and tick marks with directly encoded quantitative x/y source
columns. It considers only rows with a valid companion axis value, then
keeps any excluded/null rows explicit as unverifiable. For mixed-sign,
zero, or contradictory fixed-domain evidence, the rule fails independently
of renderer clipping behavior.

No data are transformed, filled, deleted, or silently split by sign.
The rule does not render Vega-Lite, evaluate arbitrary expressions, or
certify every implicit configuration. Missing evidence cannot produce PASS.
The rule is not a statement about statistical significance.

## CLI trap

```bash
chart-contract audit spec examples/traps/mixed_sign_log_axis.vl.json \
  --data examples/traps/mixed_sign_log_axis.csv \
  --claim "$(cat examples/traps/mixed_sign_log_axis.claim.txt)"
```

Expected: `FAIL visual.scale.log_domain`, overall `BLOCK` and
`PASS scale.override.authorization`. There is no explicit numeric domain
to invoke the older `visual.scale.clipped_data` check.

Vega-Lite reference: https://vega.github.io/vega-lite/docs/scale.html
