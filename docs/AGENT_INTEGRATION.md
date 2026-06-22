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

Gate behavior:

- `READY`: continue.
- `REVIEW`: summarize warnings, stop, and ask a human whether to proceed.
- `BLOCK`: stop immediately and fix the spec or data contract before sharing.

Policy:

- The agent must stop on `BLOCK`.
- `REVIEW` means summarize the warnings and ask for human review before continuing.

This command prints the selected format to stdout by default.
When `--out` is supplied, the selected output is written to disk and stdout becomes a one-line verdict summary.
When `--markdown` is supplied, Markdown is also written to the requested path.

This is a gate, not a publisher. It is meant to keep the agent inside a bounded audit loop before anything is shared.

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
