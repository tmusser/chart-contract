# Perch semantic regression pilot

Perch ([source](https://github.com/lakeday-org/perch)) evaluates a
plain-English invariant in `perch.yaml`:

- `movement_semantics` must return `"neutral"` for increasing **and**
  decreasing movement when `direction="neutral"`.
- Unchanged values return `"unchanged"` regardless of direction.

This is a **supplementary, model-evaluated check**, not a replacement for
deterministic tests in `tests/test_movement_semantics.py` and
`tests/test_directionality_contract.py`. No production logic changes are
required for the pilot. The `scan_types: [lint]` setting intentionally
limits Perch to custom lint rules rather than enabling general AI code review.

## Enable the GitHub Actions check

1. Obtain a key for the [System One](https://api.typesafe.ai/v1/systemone)
   endpoint documented by Perch. A `perch login` session by itself does not
   supply a GitHub Actions secret.
2. In this repository's **Settings > Secrets and variables > Actions**, add
   a repository secret named `PERCH_API_KEY`.
3. In the same settings, add a repository variable named `PERCH_ENABLED`
   with value `true`.

Until `PERCH_ENABLED=true`, the job is **skipped** (it is not a successful
Perch scan). If enabled without an API key, the job fails with a setup error.

The workflow runs when a pull request changes `directionality.py`, the
Perch rule, or the workflow itself. It runs on same-repository pull requests;
fork PRs are skipped because their workflows cannot access repository secrets.
A reported rule violation fails the job. See
[Perch CI docs](https://github.com/lakeday-org/perch/blob/main/docs/ci.md).

## Test locally

Install the CLI and configure credentials as described in
[Perch's README](https://github.com/lakeday-org/perch#readme), then run:

```bash
perch check src/chart_contract/directionality.py --rules neutral-movement-semantics
python -m pytest tests/test_movement_semantics.py
```

Perch may produce false positives or miss a regression. Validate its usefulness
by temporarily introducing a known neutral-direction violation on a throwaway
branch and confirming the rule flags it, then restore the production behavior.
