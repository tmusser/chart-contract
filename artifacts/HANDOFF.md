# HANDOFF

## Resume Packet

- Goal: make source/display measurement units and fixed multiplicative conversions explicit and auditable.
- Branch: `agent/unit-conversion-contract`.
- Base: `main` at `7be4fea88dec1c55d1693e2d61cc00ecf154b558`.
- Pull request: #26 (`feat: audit measurement unit conversions`).
- Current slice: first-party unit-conversion API, closed v1 metadata, chart/spec audits, row-level source-unit checks, fixed-scale recomputation, mixed-unit CLI trap, three new profile rules, tests, and docs.
- Read first: `src/chart_contract/unit_conversion.py`, `src/chart_contract/unit_conversion_audit.py`, `tests/test_unit_conversion_contract.py`, and `docs/UNIT_CONVERSION_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept:
  - `source_unit`
  - `conversion_kind`
  - `conversion_factor`
  - `conversion_basis`
  - `source_value_field`
  - optional `source_unit_basis_field`
- Existing `unit` remains the displayed unit and is preserved separately as `usermeta.unit`.
- Unit-conversion semantics are opt-in.
- First-party specs preserve a closed `usermeta.unit_conversion_contract`.
- `identity` means source/display units are exactly identical with factor 1.0 and no separate conversion evidence.
- `scale` means one fixed multiplicative conversion with preserved original source values and explicit basis text.
- Fixed scale uses `displayed = source * factor`.
- Scale evidence requires jointly present/null source and display values, finite numerics, and at least one complete pair.
- The first-party renderer refuses to stamp a scale contract if arithmetic does not reproduce.
- Optional row-level source-unit evidence must be non-null/non-empty, invariant, and exactly match `source_unit`.
- External contracts must bind to an encoded quantitative metric and exact declared display unit.
- No unit aliases are normalized.
- `examples/traps/mixed_measurement_units.*` demonstrates a USD-labeled chart whose rows actually contain USD and EUR.
- The `audit-v0.2` profile now contains 83 rules.

## Important Decisions

- Unit identity is explicit; it is not inferred from labels, geography, field names, or numeric magnitude.
- Version 1 does not become a conversion engine.
- Callers preserve already-converted displayed values plus the original source-value field when using fixed-scale mode.
- The contract recomputes the fixed factor but never mutates the supplied evidence.
- `identity` and `scale` are the only v1 conversion kinds.
- Scale factors must be finite and positive.
- Time-varying FX, inflation/constant-dollar adjustments, and affine/offset conversions remain out of scope.
- Conversion-basis text is provenance metadata, not proof that the external rate/source is authoritative.
- Existing metric-definition, ratio, comparison, time-window, grain, and comparison-set contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because three new unit rules change profile semantic identity.

## Verification

GitHub Actions CI run #256 (`38755883263`) passed on code-bearing head `bc434f7cd7b08f4cd5e98bc53970b0ae4c2b8215`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `mixed_measurement_units` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- A uniformly wrong source-unit identity cannot be detected from metadata alone.
- Floating-point tolerance is appropriate for v1 but not exact financial-decimal accounting.
- V1 cannot represent per-row or time-varying conversion factors.
- V1 cannot model affine transformations such as Fahrenheit/Celsius.
- V1 does not authenticate the stated conversion basis or fetch independent rate evidence.

## Next Recommended Task

- Confirm final PR #26 CI remains green after VERIFY/HANDOFF.
- Merge if exact source-unit identity and fixed multiplicative conversion semantics match the intended v1.
- Keep time-varying FX, inflation normalization, affine conversions, and canonical unit aliases separate future work.
