# CREATION_INVOCATIONS

| Step | Invocation | Purpose | Output |
| --- | --- | --- | --- |
| 1 | `$mini-spec` | Define objective, scope, non-goals, acceptance criteria, and verification commands | `artifacts/SPEC.md` |
| 2 | `$thin-plan` | Break the build into vertical slices | `artifacts/PLAN.md`, `artifacts/TODO.md` |
| 3 | `$scope-freeze` | Freeze write scope before each implementation slice | Scope blocks recorded during build and summarized in `artifacts/VERIFY.md` |
| 4 | `$build-one` | Implement one slice at a time | Source, tests, docs, and examples |
| 5 | `$test-mini` | Run focused deterministic checks after each slice | Pytest cases and script runs |
| 6 | `$verify-contract` | Record evidence and remaining risks | `artifacts/VERIFY.md` |
| 7 | `$handoff` | Leave durable resumable state | `artifacts/HANDOFF.md` |
