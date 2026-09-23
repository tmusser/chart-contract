# Roadmap

## Released: v0.2.0

The v0.2.0 release established `chart-contract` as a deterministic agent gate:

- CLI audits for Vega-Lite specs with optional CSV or JSON evidence
- text, JSON, and Markdown reports with stable `READY`, `REVIEW`, and `BLOCK` behavior
- distribution intents: `Chart.histogram()`, `Chart.boxplot()`, and `Chart.violin()`
- statistical diagnostic intents: `Chart.qq()`, `Chart.ecdf()`, and `Chart.residual()`
- runnable trap fixtures and agent-facing claim guidance

## Current main: Unreleased

The current unreleased line adds and hardens:

- `Chart.set_membership()` for audited two-set membership and Venn-style relationships
- row-level universe, binary-membership, unique-member, and reconciled-region checks
- schematic partial-overlap, disjoint, subset, and equal-set layouts with authoritative labels
- deterministic content bindings for audit reports plus CLI re-verification of saved spec-audit reports against current spec/data/claim inputs
- machine-readable `audit-v0.2` profile inspection with stable rule metadata and explicit analytical boundaries
- deterministic `audit-profile-semantics-v1` identities that exclude package-version-only drift
- mechanical saved-profile diffs covering rule additions/removals, field changes, order drift, and tool-metadata drift without an automatic compatibility judgment
- self-contained first-party Vega-Lite claim identity via `usermeta.claim`, with deterministic conflict blocking when an external audit claim disagrees
- CI across Python 3.10-3.13 plus isolated wheel build and install checks
- generated proof artifacts and current-state documentation kept in sync with the implementation

## Next

- decide the release version and release notes for the set-membership, audit-provenance, and profile-inspection slices
- consider binding a future audit-report schema revision to exact audit-profile identity after the profile contract sees real use; do not retroactively change `0.3` report semantics
- keep generated example artifacts deterministic and reviewable
- extend CLI/spec auditing only where evidence can be reconstructed without pretending arbitrary visuals are semantically complete
- add new intents only when their data, claim, and visual contracts can be tested explicitly

## Later

- matrix or UpSet-style membership intent for more than two sets
- additional reference distributions after their semantics and tests are explicit
- optional renderer and export improvements
- more annotation primitives

## Continuing boundaries

- no automatic chart correction
- no dashboard or chart-generator product surface
- no formal statistical certification
- no automatic compatibility or scientific-quality classification from audit-profile drift
- no area-proportional Venn fitting in the two-set intent
- no broad plotting-library coverage without an auditable contract
