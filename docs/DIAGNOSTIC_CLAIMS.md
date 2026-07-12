# Diagnostic Claim Guidance

Diagnostic charts answer a different kind of question from ordinary descriptive charts.

A trend chart often supports a positive statement such as “conversion increased.” A diagnostic chart often supports a narrower absence claim such as “no large fitted-value pattern is visible.” Absence claims are easier to overstate because a quiet-looking chart is not proof that the model or distribution is correct.

## General pattern

Prefer this structure:

1. Name the diagnostic and reference being inspected.
2. Describe the observed alignment or departure.
3. Limit the claim to the observed sample and plotted range.
4. State what the chart does not prove.

Strong diagnostic claims sound like observations, not certifications.

## QQ claims

### Weak

> The data are normal.

This converts a visual comparison into a distributional conclusion and ignores possible center, tail, tie, and sample-size limitations.

### Stronger

> Observed quantiles broadly follow the fitted normal reference through the center, while both outer tails depart from the line.

### Stronger when alignment is close

> Observed quantiles remain close to the fitted normal reference across most of the sample; this visual check does not establish normality.

Good QQ claims:

- say “broadly consistent with” or “track the reference” rather than “are normal”;
- name tail departures explicitly;
- mention heavy ties or rounded values when present;
- do not omit the fitted reference line;
- avoid strong conclusions from fewer than 20 observations.

## Residual claims

### Weak

> There is no pattern in the residuals.

“No pattern” is an absence claim. It should be limited to the structures and fitted-value range the diagnostic can actually reveal.

### Stronger

> Residuals remain centered near zero across the observed fitted-value range, with no large monotonic or curved structure at the audit thresholds.

### Stronger when structure is visible

> Residuals increase with fitted values, indicating remaining fitted-value structure that the model does not capture.

Good residual claims:

- distinguish centering from absence of structure;
- name monotonic, curved, funnel-shaped, grouped, or outlier patterns when visible;
- avoid “random” or “well behaved” unless the evidence supports those words;
- keep the zero reference line visible;
- treat small samples as insufficient rather than reassuring.

## ECDF claims

ECDF claims should describe cumulative thresholds or relative shifts without implying a density model.

### Weak

> Segment A has a better distribution.

### Stronger

> Across most observed thresholds, a larger share of Segment A falls below the same amount than Segment B.

Good ECDF claims:

- name the threshold or cumulative comparison;
- avoid “stochastically dominates” unless the curves and domain support that technical claim;
- acknowledge crossings rather than compressing them into one winner.

## Agent checklist

Before emitting a diagnostic claim, an agent should ask:

- Is the claim positive evidence or absence of detected problems?
- Does the chart include its required reference line?
- Is the sample large enough for the wording?
- Do tails, fitted-value trends, curvature, ties, or crossings contradict the claim?
- Can the wording be narrowed from “is” to “appears,” “broadly tracks,” or “within the observed range”?

The runnable fixtures in `examples/traps/` show these distinctions as explicit `REVIEW` and `BLOCK` outcomes.

The audit rules provide deterministic guardrails. They do not replace model diagnostics, hypothesis tests, or domain review.
