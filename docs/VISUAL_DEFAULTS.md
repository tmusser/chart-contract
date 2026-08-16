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

The existing `scale.bar.nonzero_baseline` rule still blocks a quantitative bar axis with
`scale.zero = false`, even if `user_requested_scale_override` is true.

That asymmetry is intentional. A zoomed line or point chart can be a legitimate requested
view because position, not bar length, carries the comparison. Truncated bars change the
visual length baseline itself and remain outside the accepted visual-integrity contract.

## What the policy can and cannot detect

The policy deterministically detects native Vega-Lite scale-domain overrides and native
stack normalization in the supported spec shapes, including nested layers and concatenated
views.

It does not infer semantic normalization hidden inside arbitrary `calculate`, aggregate,
window, or preprocessed data transformations. If values were normalized before reaching the
spec, the audit cannot reconstruct the user's original units from the rendered specification
alone.

The safest agent behavior is therefore simple: preserve the user's original scale and units by
default, and record a transformation request only when the user actually made one.
