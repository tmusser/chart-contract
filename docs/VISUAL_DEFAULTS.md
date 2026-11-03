# Visual default policy

`chart-contract` treats the viewer's frame of reference as part of the analytical contract.
A chart generator should not silently change that frame by cutting a quantitative scale or
normalizing values that the user supplied in their original units.

This policy applies to external Vega-Lite specs audited through `audit_spec()` or the CLI.
It does not turn `chart-contract` into a prompt recorder or prove what a user actually asked
for. It creates a deterministic declaration boundary that agents and other generators can
preserve and audit.

## Default behavior

When the user has not explicitly requested a scale or normalization transformation:

- leave quantitative scale domains at their ordinary renderer defaults;
- do not set `scale.zero = false`;
- do not inject `scale.domain`, `domainMin`, `domainMax`, or `domainRaw`;
- do not use Vega-Lite `stack: "normalize"`;
- do not use a stack transform with `offset: "normalize"`.

The corresponding audit findings are:

- `scale.override.authorization`
- `scale.normalization.authorization`

A detected transformation without the matching user-request declaration is a `FAIL`, which
makes the report `BLOCK`.

## Explicit user requests

If the user actually asks for a zoomed/cropped quantitative scale, record:

```json
{
  "usermeta": {
    "user_requested_scale_override": true
  }
}
```

If the user actually asks for normalized shares or a 100% stacked view, record:

```json
{
  "usermeta": {
    "user_requested_normalization": true
  }
}
```

These fields are declarations of user intent. They are not evidence that the request really
occurred, and an agent must not add them merely to make an audit pass.

## Bar-chart exception

A quantitative bar baseline must still include zero even when
`user_requested_scale_override` is true.

Two rules enforce that boundary:

- `scale.bar.nonzero_baseline` blocks an explicit `scale.zero = false`;
- `scale.bar.explicit_domain_zero` blocks a numeric `domain`, `domainMin`, or `domainMax`
  that explicitly excludes zero.

That asymmetry is intentional. A zoomed line or point chart can be a legitimate requested
view because position, not bar length, carries the comparison. Truncated bars change the
visual length baseline itself and remain outside the accepted visual-integrity contract.

## Hidden observations under an authorized scale

Authorizing an axis override answers **whether the zoom was requested**;
it does not answer **whether source observations fall outside the axis**.

The additional rule `visual.scale.clipped_data` checks an explicitly
numeric quantitative x/y scale's bounds against supplied directly plotted
source values. It runs independently of `scale.override.authorization`.
It supports finite numeric `domain: [min, max]`, numeric `domainMin`, and
numeric `domainMax`; boundary values are included. The rule only asserts
coverage for a simple, untransformed line, point, circle, bar or tick view
with reconstructable source records and direct encodings.

- **PASS:** All plotted numeric values are inside checkable explicit bounds.
- **WARN / REVIEW:** At least one source observation is outside the declared
  numeric axis limits. If the mark sets `clip: true`, the mark may hide those
  observations; without it, values may render off-plot depending on the
  renderer. This is a disclosure/review signal, not an automatic error.
- **WARN / REVIEW:** Dynamic `domainRaw`, unsupported domains, layered or
  transformed views, aggregate/bin/time-unit/stack encodings, or missing or
  invalid evidence prevent reliable source coverage verification.
- **No finding:** No explicit numeric quantitative domain bounds were
  declared. `scale.zero=false` alone is a separate authorization/baseline
  concern, not proof that observations were excluded.

One rule finding is emitted per affected x/y channel. The audit never
rewrites a zoom, drops an outlier, executes arbitrary transforms, or pretends
to render a visual. Bar zero-baseline rules still apply independently.

Example with a clipped negative return:

```json
{
  "mark": {"type": "line", "clip": true},
  "encoding": {
    "x": {"field": "week", "type": "ordinal"},
    "y": {"field": "returns", "type": "quantitative",
          "scale": {"domain": [0, 15]}}
  },
  "usermeta": {"user_requested_scale_override": true}
}
```

A row with `returns=-80` is outside the requested y-axis domain. The
override is authorized, but the new clipping rule produces `REVIEW`.
See [the CLI trap](../examples/traps/hidden_outlier_axis.vl.json).

## What the policy can and cannot detect

The policy deterministically detects native Vega-Lite scale-domain overrides and native
stack normalization in the supported spec shapes, including nested layers and concatenated
views.

The explicit bar-domain rule covers numeric domains and obvious numeric `domainMin` /
`domainMax` exclusions. It does not attempt to prove the zero behavior of every dynamic
`domainRaw` expression.

The policy also does not infer semantic normalization hidden inside arbitrary `calculate`,
aggregate, window, or preprocessed data transformations. If values were normalized before
reaching the spec, the audit cannot reconstruct the user's original units from the rendered
specification alone.

The safest agent behavior is therefore simple: preserve the user's original scale and units by
default, and record a transformation request only when the user actually made one.
