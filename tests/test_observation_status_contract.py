"""Missing, suppressed, and structural-zero audit regressions."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def finding(report, rule):
    return next(item for item in report.findings if item.rule_id == rule)


def example_frame():
    return pd.DataFrame({
        "period": ["Jan", "Feb", "Mar"],
        "sales": [5.0, 0.0, 3.0],
        "observation_state": ["observed", "structural_zero", "observed"],
    })


def chart(data=None, **kwargs):
    return Chart.trend(
        data=example_frame() if data is None else data,
        x="period", y="sales",
        claim="Reported sales vary across these periods.",
        source="synthetic.observation_status",
        unit="orders",
        title="Reported sales by period",
        observation_status_field="observation_state",
        **kwargs,
    )


def external():
    spec = {
        "mark": "line",
        "title": "Reported sales by period",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "sales", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.observation_status",
            "unit": "orders",
            "observation_status_contract": {
                "version": 1,
                "metric_field": "sales",
                "status_field": "observation_state",
                "counts": {
                    "observed": 2, "structural_zero": 1,
                    "missing": 0, "suppressed": 0,
                },
            },
        },
    }
    return spec, example_frame()


def test_observed_and_structural_zero_can_be_ready():
    report = chart().audit()
    assert finding(report, "contract.observation.status").severity == "PASS"
    assert finding(report, "data.observation.values").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_stamps_exact_count_receipts():
    spec = chart().to_vega_lite()
    assert spec["usermeta"]["observation_status_contract"] == external()[0]["usermeta"]["observation_status_contract"]


def test_first_party_round_trip():
    spec = chart().to_vega_lite()
    report = audit_spec(spec, claim="Reported sales vary across these periods.")
    assert finding(report, "data.observation.receipts").severity == "PASS"


@pytest.mark.parametrize("state,value", [
    ("missing", 0.0), ("suppressed", 0.0),
    ("observed", None), ("structural_zero", 7.0),
    ("weird", 0.0), (None, 0.0),
    ("observed", float("inf")), ("observed", True),
])
def test_contradictory_state_blocks_and_renderer_refuses(state, value):
    frame = example_frame()
    frame.at[1, "observation_state"] = state
    frame.at[1, "sales"] = value
    target = chart(frame)
    report = target.audit()
    assert finding(report, "data.observation.values").severity == "FAIL"
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError):
        target.to_vega_lite()


def test_external_status_and_receipts_pass():
    spec, frame = external()
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert finding(report, "contract.observation.status").severity == "PASS"
    assert finding(report, "data.observation.values").severity == "PASS"
    assert finding(report, "data.observation.receipts").severity == "PASS"
    assert report.verdict == "READY"


def test_stale_counts_fail():
    spec, frame = external()
    spec["usermeta"]["observation_status_contract"]["counts"]["observed"] = 3
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert finding(report, "data.observation.receipts").severity == "FAIL"


def test_hidden_metric_binding_fails():
    spec, frame = external()
    spec["usermeta"]["observation_status_contract"]["metric_field"] = "unplotted"
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert finding(report, "contract.observation.status").severity == "FAIL"


def test_closed_schema_fails_on_extra_field():
    spec, frame = external()
    spec["usermeta"]["observation_status_contract"]["impute_zero"] = True
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert finding(report, "contract.observation.status").severity == "FAIL"


def test_missing_evidence_fails_closed():
    spec, _ = external()
    report = audit_spec(spec, data=None, claim="Reported sales vary across these periods.")
    assert finding(report, "data.observation.values").severity == "FAIL"


def test_null_metric_allowed_only_when_missing_or_suppressed():
    frame = example_frame()
    frame.at[1, "sales"] = None
    frame.at[1, "observation_state"] = "suppressed"
    spec, _ = external()
    spec["usermeta"]["observation_status_contract"]["counts"] = {
        "observed": 2, "structural_zero": 0, "missing": 0, "suppressed": 1
    }
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert finding(report, "data.observation.values").severity == "PASS"
    assert finding(report, "data.observation.receipts").severity == "PASS"


def test_absent_contract_does_not_guess_status():
    spec, frame = external()
    del spec["usermeta"]["observation_status_contract"]
    report = audit_spec(spec, data=frame, claim="Reported sales vary across these periods.")
    assert not any(f.rule_id.startswith(("contract.observation", "data.observation")) for f in report.findings)


def test_rank_constructor_accepts_status_contract():
    rank = Chart.rank(
        data=pd.DataFrame({"segment": ["a","b"],"revenue":[3,0],"status":["observed","structural_zero"]}),
        x="segment",y="revenue",claim="Observed revenue by segment.",
        source="synthetic.revenue",unit="dollars",
        observation_status_field="status",
    )
    assert finding(rank.audit(), "data.observation.values").severity == "PASS"


def test_compare_constructor_accepts_status_contract():
    compared = Chart.compare(
        data=pd.DataFrame({"segment": ["a","b"],"revenue":[3,0],"status":["observed","structural_zero"]}),
        x="segment",y="revenue",claim="Observed revenue by segment.",
        source="synthetic.revenue",unit="dollars",
        observation_status_field="status",
    )
    assert finding(compared.audit(), "data.observation.values").severity == "PASS"
