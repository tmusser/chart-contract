# Saved Audit-Report Diff (v1)

A chart can be READY yesterday and REVIEW today. The new
`chart-contract audit diff` command compares two **internally valid,
durably bound** saved schema-0.4 JSON reports and explains what changed,
without re-executing either audit or assuming which input caused a finding.

## Basic workflow

```bash
chart-contract audit spec chart.vl.json \
  --data yesterday.csv --format json --out before.json

chart-contract audit spec chart.vl.json \
  --data today.csv --format json --out after.json

chart-contract audit diff before.json after.json
chart-contract audit diff before.json after.json --format json --out diff.json
chart-contract audit diff before.json after.json --fail-on-regression
```

The CLI reports:

- **Verdict transition**, e.g. `READY -> REVIEW`, plus before/after
  PASS/WARN/FAIL counts.
- **Identity drift:** whether the audited subject/spec, explicit audit data,
  exact claim text, recorded tool version, and bound semantic audit profile
  changed. All five are reported **independently**.
- **Added findings** and **resolved findings** with exact rule IDs, optional
  affected fields, severity, and explanation.
- **Changed findings** under the same `(rule_id, field)`, distinguishing
  severity changes from explanation/suggestion changes. Exact duplicate
  findings are counted, not silently collapsed.
- A machine-readable list of changes, deterministic counts, and
  `has_regressions`/`has_improvements` flags.

For deterministic pairing, the command first removes exact matching findings,
then matches same-rule/same-field findings with the same severity, and finally
matches remaining instances by a stable sort order. Changing a finding's
`field` is an addition/resolution, not a guessed rename. A new PASS does not
count as a regression.

```text
Verdict: READY -> REVIEW
Before summary: PASS=... WARN=0 FAIL=0
After summary: PASS=... WARN=1 FAIL=0
Input/policy identities:
  Subject: SAME
  Data: CHANGED
  Claim: SAME
  Tool version: SAME
  Audit policy: SAME
...
```

## Gate semantics

By default, a successful comparison exits **0**, even if the after verdict is
BLOCK. This is a **diff**, not an audit gate. To opt into a small regression
gate, use `--fail-on-regression`: this exits **1** when any newly added
finding has severity WARN/FAIL or when an existing matched finding worsens
(e.g. PASS to WARN). A newly added PASS or message-only change is not a
regression. Existing WARN/FAIL findings that remain unchanged do not trigger.

Malformed JSON, unsupported/legacy schemas, broken report/input bindings,
tampered findings, or comparing different `subject_kind` values are usage
errors (**exit 2**). Outputs use `--format text|json` and optional `--out`.
The JSON diff has `type="chart_contract.audit_report_diff"` and
`schema_version="1.0"`.

## Trust boundaries

**Both reports are independently checked** using the existing
`bound_report_from_dict` parser. This verifies that their saved findings,
derived verdicts, input/report bindings, and historical audit-profile
identities are internally consistent. Unlike `verify report`, the diff
does not compare either report to *current* spec/data/claim or require
its historical profile to equal the installed profile. Historical comparison
needs to remain possible across legitimate audit-policy revisions.

- `profile_changed=true` signals an audit **policy** identity change,
  separately from `tool_version_changed`. Do not interpret a greener
  verdict under a new policy as improved data quality.
- `subject_changed=true` means the bound Vega-Lite spec or first-party
  chart contract changed. If a spec carries inline `data.values`,
  that source evidence is fingerprinted as part of the **subject**, not the
  separate explicit-data digest (`data_sha256` can remain null).
- `data_changed=true` refers **only** to explicit separately supplied
  data. A changed digest is identity evidence, not a causal explanation.
- `claim_changed=true` is an exact text identity comparison.
- If the original reports describe different charts but share subject kind,
  the diff is mechanical; it cannot assert that they belong to the same
  continuing chart. Check the subject identity before interpreting results.
- A matching hash is not a signature or authentic attestation. A malicious
  editor could rewrite findings and recompute bindings. The diff detects
  accidental corruption, not a trustworthy provenance authority.

No statistical test, causal analysis, chart rendering, live re-audit, or
semantic policy compatibility judgment is performed. Labels such as
"regression" and "improvement" refer solely to audit finding *severity*,
not scientific truth or substantive analytical value.

## Runnable synthetic example

```bash
python examples/audit_report_diff_demo.py /tmp/chart-contract-audit-diff
chart-contract audit diff \
  /tmp/chart-contract-audit-diff/before.json \
  /tmp/chart-contract-audit-diff/after.json \
  --format json
```

The generator creates two **genuinely audited bound reports** with identical
spec, claim, and audit-policy identity but different explicit data:
`[4, 5, 6]` versus `[4, 5, 15]` on a documented fixed y-axis range
`[0, 10]`. The new 15-value produces a
`visual.scale.clipped_data` WARN and a READY-to-REVIEW transition.

Use `chart-contract verify report` if the goal is verifying either saved
report against the **current exact** spec, source data and claim prior to
sharing. The diff does not replace that gate.
