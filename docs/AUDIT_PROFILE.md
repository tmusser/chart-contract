# Audit profile inspection

`chart-contract` exposes its implemented audit rules as a machine-readable profile so agents and reviewers can inspect the gate without scraping Python or relying only on prose documentation.

The initial profile is `audit-v0.2`.

```bash
chart-contract profile show audit-v0.2
chart-contract profile show audit-v0.2 --json
```

A profile manifest records each stable rule ID together with:

- the audit surfaces it can apply to (`chart` and/or `spec`);
- the severities that rule may emit;
- a concise trigger description;
- a known boundary describing what the rule does not establish.

Unlike `claim-contract` rules, some chart-contract rules legitimately emit different severities at different deterministic thresholds. For example, distribution sample size can be `PASS`, `WARN`, or `FAIL`. The manifest therefore records an allowed severity set rather than pretending every rule has one fixed severity.

## What the manifest is not

The profile manifest is descriptive metadata. It is not another audit and it does not execute any rule.

A manifest that parses cleanly does not mean:

- a chart is `READY`;
- the underlying data are correct;
- a causal or diagnostic interpretation is true;
- the chart is scientifically valid;
- the documented rule implementation is bug-free;
- a saved report was authentically produced by the displayed profile.

The manifest preserves these boundaries explicitly with `scientific_validation: false`, `automatic_adjudication: false`, a scope notice, and a `not_evaluated` list.

## Semantic profile identity

`chart-contract` can compute a deterministic SHA-256 identity for the semantic profile under `audit-profile-semantics-v1`.

The semantic identity includes:

- profile name and description;
- interpretation-boundary fields;
- rule count and order;
- every rule ID, applicable surface, allowed severity, trigger, and known boundary.

Top-level tool metadata such as the package version is intentionally excluded. A package-only release should not look like audit-policy drift when the ruleset itself did not change.

The digest is content identity, not authentication. A matching digest does not prove that a report was genuinely executed by that ruleset or that the rules are analytically correct.

## Mechanical profile drift

Save two JSON manifests and compare them mechanically:

```bash
chart-contract profile show audit-v0.2 --json > before-profile.json
# ... inspect another revision or saved manifest ...
chart-contract profile diff before-profile.json after-profile.json
chart-contract profile diff before-profile.json after-profile.json --json
```

The diff reports:

- profile metadata changes;
- rule additions and removals;
- per-rule field changes;
- rule-order drift;
- before/after semantic SHA-256 identities;
- package/tool metadata drift separately.

The diff deliberately emits `compatibility_judgment: null`. It does not label a change safe, breaking, compatible, improved, or scientifically preferable. Those judgments require context outside a mechanical manifest comparison.

## Relationship to saved audit reports

Saved schema-0.4 reports now bind their findings and audit-policy
identity. See [audit-report diff](AUDIT_REPORT_DIFF.md) for a separate
historical comparison command. The command compares historical bound
profiles without assuming the current installed profile is identical.

Schema-0.4 audit reports already fingerprint their exact spec/chart subject, explicit source data, claim, recorded tool version, derived findings/verdict, and semantic audit-profile identity. The historical schema-0.3 format never bound results and profile semantics, so a v0.3 artifact must be **re-audited** to be eligible for durable verification or report diff. This command does not silently migrate or rewrite legacy reports.

Published schemas:

- [`schemas/audit-profile-v1.schema.json`](../schemas/audit-profile-v1.schema.json)
- [`schemas/audit-profile-diff-v1.schema.json`](../schemas/audit-profile-diff-v1.schema.json)
