# Changelog

## [0.2.0] - 2026-06-22

### Added

- CLI audit gate for Vega-Lite specs from disk via `chart-contract audit spec`.
- Optional CSV and JSON data input for CLI audits.
- Text, JSON, and Markdown report output from the same audit result.
- CI-friendly exit behavior for `READY`, `REVIEW`, and `BLOCK`.
- Runnable trap fixtures under `examples/traps/` for weak claims, missing provenance, and pie/arc failures.

### Changed

- README now leads with the CLI audit gate as the front door for agent-gated workflows.
- `docs/AGENT_INTEGRATION.md` now tells agents to stop on `BLOCK` and summarize `REVIEW` findings for human review.
- `ROADMAP.md` now treats v0.2.0 as a checked-off release checklist.
- CI now runs a CLI trap smoke check in addition to pytest.

### Notes

- The release stays deterministic and does not add new chart intents, auto-correction, or v0.3 semantic rules.
- Existing v0.1 examples and audit rules remain in place.
