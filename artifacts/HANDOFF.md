# HANDOFF

## Resume Packet

- Goal: make sample/census scope, target population, optional member/weight evidence, and population-generalization intent explicit.
- Branch: `agent/population-sampling-contract`.
- Base: `main` at `8709096777f7d4ebceeea69290dd3e52034b0cf4`.
- Pull request: #27 (`feat: audit population sampling scope`).
- Current slice: first-party sampling API, closed v1 metadata, chart/spec audits, sample-member reconstruction, positive-weight checks, bounded generalization review, convenience-sample CLI trap, four new profile rules, tests, and docs.
- Read first: `src/chart_contract/population_sampling.py`, `src/chart_contract/population_sampling_audit.py`, `tests/test_population_sampling_contract.py`, and `docs/POPULATION_SAMPLING_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept:
  - `evidence_scope`
  - `population`
  - `population_size`
  - `sample_size`
  - `sampling_method`
  - optional `sample_member_field`
  - optional `weight_field`
  - `generalizes_to_population`
- Population semantics are opt-in.
- First-party specs preserve a closed `usermeta.population_contract`.
- Sample evidence cannot declare `census` sampling and must be smaller than a declared population.
- Census evidence requires `sampling_method="census"`, population size, and exact sample/population equality.
- DataFrame row count is deliberately not used as sample size.
- Optional sample-member evidence is reconstructable only when supplied rows are one sampled unit each; IDs must be complete, unique, and exactly match declared sample size.
- Optional sampling weights must be complete, numeric, finite, and strictly positive.
- Population generalization is an explicit boolean rather than broad claim-text inference.
- Missing population metadata emits REVIEW only for bounded explicit claim phrases: `sample of`, `sampled from`, `survey respondent(s)`, and `census of`.
- Generalization from convenience/quota/unknown/other sampling emits REVIEW.
- Descriptive nonprobability samples can remain READY.
- Probability-method/census generalization structurally passes but is not described as representativeness proof.
- `examples/traps/convenience_sample_generalized.*` demonstrates a coherent convenience sample that explicitly overreaches to the full population.
- The `audit-v0.2` profile now contains 87 rules.

## Important Decisions

- Sampling scope is provenance, not statistical certification.
- Aggregated analytical rows are not assumed to be sampled units.
- `sample_member_field` is optional so aggregated charts can declare sample size without fabricating row-level proof.
- When member evidence is declared, exact count reconstruction is strict.
- Weight validation is structural only; no calibration or estimator logic is inferred.
- Generalization intent is explicit metadata to avoid open-ended NLP adjudication.
- Nonprobability generalization is REVIEW, not BLOCK: it may be defensible with domain context, but should not silently remain READY.
- Probability-method declarations are not automatic approval of population inference.
- Existing coverage, metric-definition, unit, ratio, comparison, time-window, grain, and comparison-set contracts remain independent and composable.
- Older schema-0.4 reports become stale-policy artifacts because four new population rules change profile semantic identity.

## Verification

GitHub Actions CI run #269 (`38989751879`) passed on code-bearing head `226f55a1a671dbddc196d0381d3103f52dcaf993`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all existing CLI trap paths -> PASSED
- `convenience_sample_generalized` REVIEW trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Population/sampling metadata can be truthfully formatted but factually wrong.
- V1 does not validate the sampling frame, inclusion probabilities, nonresponse, or actual execution of the declared method.
- V1 does not model cluster/strata structure beyond the method label.
- V1 does not validate weighting methodology or use weights to recompute metrics.
- V1 does not estimate uncertainty, design effects, or effective sample size.
- Broad claim-language inference remains intentionally out of scope beyond the four bounded explicit sampling phrases.

## Next Recommended Task

- Confirm final PR #27 CI remains green after VERIFY/HANDOFF.
- Merge if the explicit sample/census scope and nonprobability-generalization REVIEW boundary match the desired v1.
- Keep uncertainty/interval semantics, design effects, and formal sample inference separate future work.
