# Agent Integration

Use `chart-contract` as a gate before a chart is shared.

The working pattern is:

1. The agent proposes a chart.
2. `chart-contract` audits the spec and data contract.
3. The agent fixes the chart or stops.
4. A human reviews the result before sharing.

Copy/paste instruction for agents:

> Generate a chart only if chart-contract audit passes. If there are WARN findings, summarize them and ask whether to proceed. If there are FAIL findings, do not render for sharing; fix the spec or explain why it failed.

Allowed:

- Generate a draft chart spec.
- Run audit.
- Explain warnings.
- Propose fixes.

Not allowed:

- Ignore FAIL findings.
- Claim causality without evidence.
- Hide missing source/unit.
- Auto-publish.

`chart-contract` is a review gate, not an autonomous chart publisher. It helps an agent surface evidence, caveats, and visual-risk issues before a human decides whether the chart should go out.
