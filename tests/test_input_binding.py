from __future__ import annotations

import copy

import pandas as pd

from chart_contract import Chart, audit_spec
from chart_contract.input_binding import BoundAuditReport


def _spec() -> dict:
    return {
        "mark": "line",
        "title": "Conversion trend",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "conversion", "type": "quantitative"},
        },
        "usermeta": {"source": "synthetic.conversion", "unit": "rate"},
    }


def _data() -> pd.DataFrame:
    return pd.DataFrame({"week": ["W1", "W2"], "conversion": [0.41, 0.43]})


def test_spec_report_is_bound_to_exact_inputs() -> None:
    spec = _spec()
    data = _data()
    claim = "Conversion increased from W1 to W2."

    report = audit_spec(spec=spec, data=data, claim=claim)
    payload = report.to_dict()

    assert isinstance(report, BoundAuditReport)
    assert payload["schema_version"] == "0.3"
    assert payload["input_binding"]["algorithm"] == "sha256"
    assert payload["input_binding"]["subject_kind"] == "spec"
    assert len(payload["input_binding"]["subject_sha256"]) == 64
    assert len(payload["input_binding"]["data_sha256"]) == 64
    assert len(payload["input_binding"]["claim_sha256"]) == 64
    assert len(payload["input_binding"]["bundle_sha256"]) == 64
    assert report.matches_spec(spec=spec, data=data, claim=claim)


def test_equivalent_spec_key_order_has_same_fingerprint() -> None:
    spec = _spec()
    reordered = {
        "usermeta": spec["usermeta"],
        "encoding": spec["encoding"],
        "title": spec["title"],
        "mark": spec["mark"],
    }

    first = audit_spec(spec=spec, data=_data(), claim="Observed trend.")
    second = audit_spec(spec=reordered, data=_data(), claim="Observed trend.")

    assert first.input_binding == second.input_binding


def test_mutating_spec_invalidates_existing_report() -> None:
    spec = _spec()
    data = _data()
    claim = "Conversion increased from W1 to W2."
    report = audit_spec(spec=spec, data=data, claim=claim)
    changed = copy.deepcopy(spec)
    changed["title"] = "A different chart title"

    assert not report.matches_spec(spec=changed, data=data, claim=claim)


def test_mutating_data_invalidates_existing_report() -> None:
    spec = _spec()
    data = _data()
    claim = "Conversion increased from W1 to W2."
    report = audit_spec(spec=spec, data=data, claim=claim)
    changed = data.copy()
    changed.loc[1, "conversion"] = 0.99

    assert not report.matches_spec(spec=spec, data=changed, claim=claim)


def test_mutating_claim_invalidates_existing_report() -> None:
    spec = _spec()
    data = _data()
    report = audit_spec(spec=spec, data=data, claim="Conversion increased.")

    assert not report.matches_spec(spec=spec, data=data, claim="Conversion decreased.")


def test_chart_audit_is_bound_to_chart_contract_data_and_claim() -> None:
    chart = Chart.trend(
        data=_data(),
        x="week",
        y="conversion",
        claim="Conversion increased from W1 to W2.",
        source="synthetic.conversion",
        unit="rate",
        title="Conversion trend",
    )

    report = chart.audit()

    assert isinstance(report, BoundAuditReport)
    assert report.input_binding is not None
    assert report.input_binding.subject_kind == "chart_contract"
    assert report.to_dict()["schema_version"] == "0.3"
    assert report.matches_chart(chart)


def test_mutating_first_party_chart_invalidates_existing_report() -> None:
    chart = Chart.trend(
        data=_data(),
        x="week",
        y="conversion",
        claim="Conversion increased from W1 to W2.",
        source="synthetic.conversion",
        unit="rate",
        title="Conversion trend",
    )
    report = chart.audit()

    chart.title = "Changed after audit"

    assert not report.matches_chart(chart)


def test_binding_has_no_wall_clock_field() -> None:
    payload = audit_spec(spec=_spec(), data=_data(), claim="Observed trend.").to_dict()["input_binding"]

    assert "timestamp" not in payload
    assert "created_at" not in payload
    assert "audited_at" not in payload
