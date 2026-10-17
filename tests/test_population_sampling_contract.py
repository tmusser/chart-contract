from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
        }
    )


def _sample_chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "period",
        "y": "active_users",
        "claim": "Observed active users differ across periods.",
        "source": "synthetic.population_sampling",
        "unit": "users",
        "title": "Observed active users",
        "evidence_scope": "sample",
        "population": "All eligible product users",
        "population_size": 1000,
        "sample_size": 250,
        "sampling_method": "simple_random",
        "sample_member_field": None,
        "weight_field": None,
        "generalizes_to_population": True,
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_probability_sample_contract_passes_without_row_level_count_evidence() -> None:
    report = _sample_chart(_frame()).audit()

    assert _finding(report, "contract.population.scope").severity == "PASS"
    assert _finding(report, "claim.population.generalization").severity == "PASS"
    assert not any(
        f.rule_id == "data.population.sample_count" for f in report.findings
    )
    assert report.verdict == "READY"


def test_declared_sample_size_is_not_inferred_from_aggregated_row_count() -> None:
    chart = _sample_chart(_frame(), sample_size=250)

    report = chart.audit()

    assert report.verdict == "READY"
    assert "sample_size=250" in _finding(
        report,
        "contract.population.scope",
    ).message


def test_first_party_spec_preserves_closed_population_contract() -> None:
    spec = _sample_chart(_frame()).to_vega_lite()

    assert spec["usermeta"]["population_contract"] == {
        "version": 1,
        "evidence_scope": "sample",
        "population": "All eligible product users",
        "population_size": 1000,
        "sample_size": 250,
        "sampling_method": "simple_random",
        "sample_member_field": None,
        "weight_field": None,
        "generalizes_to_population": True,
    }


def test_row_level_sample_member_count_reconstructs_exactly() -> None:
    frame = pd.DataFrame(
        {
            "period": ["A", "B", "C"],
            "active_users": [10, 20, 30],
            "user_id": ["u1", "u2", "u3"],
        }
    )
    report = _sample_chart(
        frame,
        population_size=10,
        sample_size=3,
        sample_member_field="user_id",
    ).audit()

    assert _finding(report, "data.population.sample_count").severity == "PASS"
    assert report.verdict == "READY"


def test_duplicate_or_mismatched_sample_member_count_blocks_and_refuses_render() -> None:
    frame = pd.DataFrame(
        {
            "period": ["A", "B", "C"],
            "active_users": [10, 20, 30],
            "user_id": ["u1", "u1", "u2"],
        }
    )
    chart = _sample_chart(
        frame,
        population_size=10,
        sample_size=3,
        sample_member_field="user_id",
    )

    report = chart.audit()

    finding = _finding(report, "data.population.sample_count")
    assert finding.severity == "FAIL"
    assert "duplicate identifiers" in finding.message
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="duplicate identifiers"):
        chart.to_vega_lite()


def test_nonprobability_generalization_requires_review() -> None:
    report = _sample_chart(
        _frame(),
        sampling_method="convenience",
        generalizes_to_population=True,
    ).audit()

    finding = _finding(report, "claim.population.generalization")
    assert finding.severity == "WARN"
    assert "convenience" in finding.message
    assert report.verdict == "REVIEW"


def test_nonprobability_sample_can_stay_descriptive() -> None:
    report = _sample_chart(
        _frame(),
        sampling_method="convenience",
        generalizes_to_population=False,
    ).audit()

    assert _finding(report, "claim.population.generalization").severity == "PASS"
    assert report.verdict == "READY"


def test_census_requires_exact_population_count_and_census_method() -> None:
    valid = _sample_chart(
        _frame(),
        evidence_scope="census",
        population_size=250,
        sample_size=250,
        sampling_method="census",
        generalizes_to_population=True,
    ).audit()
    invalid_count = _sample_chart(
        _frame(),
        evidence_scope="census",
        population_size=251,
        sample_size=250,
        sampling_method="census",
    ).audit()
    invalid_method = _sample_chart(
        _frame(),
        evidence_scope="census",
        population_size=250,
        sample_size=250,
        sampling_method="simple_random",
    ).audit()

    assert valid.verdict == "READY"
    assert _finding(invalid_count, "contract.population.scope").severity == "FAIL"
    assert _finding(invalid_method, "contract.population.scope").severity == "FAIL"


def test_sample_cannot_equal_or_exceed_declared_population() -> None:
    report = _sample_chart(
        _frame(),
        population_size=250,
        sample_size=250,
    ).audit()

    assert _finding(report, "contract.population.scope").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_positive_finite_weights_pass() -> None:
    frame = pd.DataFrame(
        {
            "period": ["A", "B"],
            "active_users": [100, 120],
            "weight": [1.25, 0.75],
        }
    )

    report = _sample_chart(frame, weight_field="weight").audit()

    assert _finding(report, "data.population.weights").severity == "PASS"
    assert report.verdict == "READY"


@pytest.mark.parametrize("bad_weight", [0, -1, None, float("inf"), "heavy", True])
def test_invalid_weights_block(bad_weight) -> None:
    frame = pd.DataFrame(
        {
            "period": ["A", "B"],
            "active_users": [100, 120],
            "weight": [1.0, bad_weight],
        }
    )

    report = _sample_chart(frame, weight_field="weight").audit()

    assert _finding(report, "data.population.weights").severity == "FAIL"
    assert report.verdict == "BLOCK"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = pd.DataFrame(
        {
            "period": ["A", "B", "C"],
            "active_users": [10, 20, 30],
            "user_id": ["u1", "u2", "u3"],
            "weight": [1.0, 1.2, 0.8],
        }
    )
    spec = {
        "mark": "line",
        "title": "Observed active users",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "active_users", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.population_sampling",
            "unit": "users",
            "population_contract": {
                "version": 1,
                "evidence_scope": "sample",
                "population": "All eligible product users",
                "population_size": 10,
                "sample_size": 3,
                "sampling_method": "stratified",
                "sample_member_field": "user_id",
                "weight_field": "weight",
                "generalizes_to_population": True,
            },
        },
    }
    return spec, frame


def test_external_population_contract_passes_with_reconstructable_evidence() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "contract.population.scope").severity == "PASS"
    assert _finding(report, "data.population.sample_count").severity == "PASS"
    assert _finding(report, "data.population.weights").severity == "PASS"
    assert _finding(report, "claim.population.generalization").severity == "PASS"
    assert report.verdict == "READY"


def test_external_reconstructable_fields_require_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(
        spec,
        data=None,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "data.population.sample_count").severity == "FAIL"
    assert _finding(report, "data.population.weights").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_closed_population_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["population_contract"]["response_rate"] = 0.5

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "contract.population.scope").severity == "FAIL"


def test_explicit_sample_claim_without_contract_requires_review() -> None:
    chart = Chart.trend(
        data=_frame(),
        x="period",
        y="active_users",
        claim="A sample of eligible users shows higher observed activity after launch.",
        source="synthetic.population_sampling",
        unit="users",
        title="Observed active users",
    )

    report = chart.audit()

    finding = _finding(report, "contract.population.scope")
    assert finding.severity == "WARN"
    assert report.verdict == "REVIEW"


def test_external_explicit_sample_claim_without_contract_requires_review() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["population_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Survey respondents show higher observed activity after launch.",
    )

    finding = _finding(report, "contract.population.scope")
    assert finding.severity == "WARN"
    assert report.verdict == "REVIEW"


def test_absent_population_contract_does_not_invent_sampling_semantics() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["population_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert not any(
        f.rule_id
        in {
            "contract.population.scope",
            "data.population.sample_count",
            "data.population.weights",
            "claim.population.generalization",
        }
        for f in report.findings
    )
