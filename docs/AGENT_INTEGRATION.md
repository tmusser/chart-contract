# Agent Integration

Use `chart-contract` as a gate before a chart is shared.

## v0.2.0 — Agent Gate

Current copy-paste CLI shape:

```bash
chart-contract audit spec path/to/spec.vl.json \
  --data path/to/data.csv \
  --claim "The launch improved conversion"
```

Supported inputs:

- `--data path/to/data.csv` for CSV input.
- `--data path/to/data.json` for JSON input.
- `--claim "..."` for the chart claim being audited.
- `--format text|json|markdown` for the desired report shape.
- `--out path/to/report.txt` to write the selected output to disk.
- `--markdown path/to/report.md` to write Markdown output alongside the selected format.
- `--warnings-as-errors` to make REVIEW exit nonzero.
- `--fail-on READY|REVIEW|BLOCK` to set an explicit threshold; `READY` is mechanically valid but effectively means "always fail."

Gate behavior:

- `READY`: continue only while the bound inputs still match the chart being shared.
- `REVIEW`: summarize warnings, stop, and ask a human whether to proceed.
- `BLOCK`: stop immediately and fix the spec or data contract before sharing.

Policy:

- The agent must stop on `BLOCK`.
- `REVIEW` means summarize the warnings and ask for human review before continuing.
- A durable audit report is valid only for its recorded `input_binding`; if the spec, explicit data, or claim changes, rerun the audit before sharing.
- `--fail-on` is available when you want an explicit threshold, but `BLOCK` is usually the practical gate.

This command prints the selected format to stdout by default.
When `--out` is supplied, the selected output is written to disk and stdout becomes a one-line verdict summary.
When `--markdown` is supplied, Markdown is also written to the requested path.

JSON and Markdown reports include a deterministic input binding over the audited subject, explicit data, claim, and package version. This lets downstream code detect a stale report after post-audit mutation; it does not make the verdict scientifically valid or human-approved.

This is a gate, not a publisher. It is meant to keep the agent inside a bounded audit loop before anything is shared.

The working pattern is:

1. The agent proposes a chart.
2. `chart-contract` audits the spec and data contract and records the input binding.
3. The agent fixes the chart or stops.
4. If any audited input changes, the agent reruns the audit rather than reusing the old report.
5. Immediately before sharing, the agent verifies that the report still corresponds to the current inputs.
6. A human reviews the result before sharing.

Python callers can perform the final identity check directly:

```python
report = audit_spec(spec=spec, data=df, claim=claim)
if not report.matches_spec(spec=spec, data=df, claim=claim):
    raise RuntimeError("audit report is stale; rerun chart-contract")
```

For first-party charts, use `report.matches_chart(chart)`.

Copy/paste instruction for agents:

> Generate a chart only if chart-contract audit passes. If there are WARN findings, summarize them and ask whether to proceed. If there are FAIL findings, do not render for sharing; fix the spec or explain why it failed. Do not reuse an audit report after changing the spec, data, or claim; rerun the audit and verify the input binding immediately before sharing.

Allowed:

- Generate a draft chart spec.
- Run audit.
- Verify the input binding before sharing.
- Explain warnings.
- Propose fixes.

Not allowed:

- Ignore FAIL findings.
- Reuse a stale `READY` report after changing audited inputs.
- Claim causality without evidence.
- Hide missing source/unit.
- Auto-publish.

`chart-contract` is a review gate, not an autonomous chart publisher. It helps an agent surface evidence, caveats, visual-risk issues, and stale-audit drift before a human decides whether the chart should go out.
