# PLAN

1. Package skeleton
   Result: installable package, requested file tree, public imports.
   Verification: editable install and import test.
2. Audit models
   Result: `AuditFinding`, `AuditReport`, shared helpers, deterministic finding summaries.
   Verification: focused audit model tests.
3. Trend intent end-to-end
   Result: `Chart.trend()`, audit checks, Altair/Vega-Lite rendering, event annotation support.
   Verification: trend tests and example run.
4. Rank and compare intents
   Result: `Chart.rank()` and `Chart.compare()` with readable bar defaults and sorting/grouping.
   Verification: chart intent tests and example runs.
5. `audit_spec()` demo rules
   Result: experimental spec audit for risky Vega-Lite-like specs.
   Verification: `test_audit_spec.py`.
6. Examples
   Result: runnable synthetic-data demos including hero bad-to-good flow.
   Verification: example scripts generate output files.
7. Docs and manifest
   Result: README, docs, agent guidance, human/machine-readable build manifest.
   Verification: structural checks and README content checks.
8. Verification and handoff
   Result: durable evidence in `VERIFY.md` and resumable state in `HANDOFF.md`.
   Verification: command log and remaining-risk summary.
