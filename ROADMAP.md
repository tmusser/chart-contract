# Roadmap

## v0.1 polish

- README hero clarity
- rendered example artifact
- audit output example
- packaging hygiene

## v0.2.0 — Agent Gate

Goal: make `chart-contract` usable as a deterministic CLI gate for chart audits from disk before any code changes spill into v0.3.

Release checklist:

- [x] CLI entrypoint and spec loader: audit a Vega-Lite spec from disk and accept an explicit claim argument.
- [x] Optional data input: support CSV and JSON data files with deterministic parse and file errors.
- [x] Report emitters: produce text, JSON, and Markdown audit reports from the same audit result.
- [x] CI-friendly exit codes: map pass, warn, and fail outcomes to stable process exit codes for agents and CI.
- [x] Runnable trap fixtures: add examples that exercise weak claims, missing provenance, and other audit failures.
- [x] README and docs usage: add copy-paste examples that show the agent gate flow end to end.
- [x] Release prep: bump the package version and add a v0.2.0 changelog entry.

Explicit non-goals:

- Do not add new chart intents.
- Do not add `ChartContract` yet.
- Do not add semantic denominator/grain rules yet.
- Do not add auto-correction.
- Do not build a dashboard or chart generator.

## v0.3 distribution preview

- Chart intents: `Chart.histogram()`, `Chart.boxplot()`, `Chart.violin()`
- Distribution audit rules: numeric metric checks, sample-size thresholds, grouped category thresholds, histogram bins, violin density warnings
- Example artifact: `examples/distribution_charts.py`

## Later

- More visual intents only after the audit contract is strong
- Optional renderer and export improvements
- More annotation primitives
- v0.3 starts only after the gate is stable enough to trust
