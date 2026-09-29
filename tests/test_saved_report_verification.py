from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import audit_spec
from chart_contract.cli import main
from chart_contract.input_binding import (
    build_input_binding,
    build_report_binding,
    input_binding_from_dict,
    verify_input_binding,
)
from chart_contract.profiles import build_audit_profile_binding, get_profile_manifest


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


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, str]:
    spec_path = tmp_path / "chart.vl.json"
    data_path = tmp_path / "chart.csv"
    claim = "Conversion increased from W1 to W2."
    spec_path.write_text(json.dumps(_spec()), encoding="utf-8")
    pd.DataFrame(
        {"week": ["W1", "W2"], "conversion": [0.41, 0.43]}
    ).to_csv(data_path, index=False)
    return spec_path, data_path, claim


def _write_report(tmp_path: Path, spec_path: Path, data_path: Path, claim: str) -> Path:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    data = pd.read_csv(data_path)
    report = audit_spec(spec=spec, data=data, claim=claim)
    report_path = tmp_path / "audit.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report_path


def test_cli_verifies_saved_report_against_exact_inputs(tmp_path: Path, capsys) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)

    code = main(
        [
            "verify",
            "report",
            str(report_path),
            "--spec",
            str(spec_path),
            "--data",
            str(data_path),
            "--claim",
            claim,
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Report integrity: MATCH" in output
    assert "Audit profile: MATCH" in output
    assert "Binding: MATCH" in output
    assert "Subject: MATCH" in output
    assert "Data: MATCH" in output
    assert "Claim: MATCH" in output


def test_cli_verifies_embedded_claim_report_without_claim_flag(
    tmp_path: Path,
    capsys,
) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec.setdefault("usermeta", {})["claim"] = claim
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    data = pd.read_csv(data_path)
    report = audit_spec(spec=spec, data=data)
    report_path = tmp_path / "embedded-claim-audit.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    code = main(
        [
            "verify",
            "report",
            str(report_path),
            "--spec",
            str(spec_path),
            "--data",
            str(data_path),
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Binding: MATCH" in output
    assert "Claim: MATCH" in output


def test_cli_reports_spec_drift_without_blurring_other_components(
    tmp_path: Path, capsys
) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)

    changed = json.loads(spec_path.read_text(encoding="utf-8"))
    changed["title"] = "Changed after audit"
    spec_path.write_text(json.dumps(changed), encoding="utf-8")

    code = main(
        [
            "verify",
            "report",
            str(report_path),
            "--spec",
            str(spec_path),
            "--data",
            str(data_path),
            "--claim",
            claim,
        ]
    )

    assert code == 1
    output = capsys.readouterr().out
    assert "Binding: MISMATCH" in output
    assert "Subject: MISMATCH" in output
    assert "Data: MATCH" in output
    assert "Claim: MATCH" in output


def test_cli_reports_data_and_claim_drift_independently(tmp_path: Path, capsys) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)

    pd.DataFrame(
        {"week": ["W1", "W2"], "conversion": [0.41, 0.99]}
    ).to_csv(data_path, index=False)

    code = main(
        [
            "verify",
            "report",
            str(report_path),
            "--spec",
            str(spec_path),
            "--data",
            str(data_path),
            "--claim",
            "Conversion decreased from W1 to W2.",
        ]
    )

    assert code == 1
    output = capsys.readouterr().out
    assert "Subject: MATCH" in output
    assert "Data: MISMATCH" in output
    assert "Claim: MISMATCH" in output


def test_cli_rejects_internally_corrupted_binding(tmp_path: Path) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["input_binding"]["claim_sha256"] = "0" * 64
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "verify",
                "report",
                str(report_path),
                "--spec",
                str(spec_path),
                "--data",
                str(data_path),
                "--claim",
                claim,
            ]
        )

    assert exc_info.value.code == 2


def test_verification_uses_recorded_tool_version_identity() -> None:
    spec = _spec()
    data = pd.DataFrame({"week": ["W1", "W2"], "conversion": [0.41, 0.43]})
    claim = "Observed conversion trend."
    historical = build_input_binding(
        subject=spec,
        subject_kind="spec",
        data=data,
        claim=claim,
        tool_version="0.1.7",
    )

    parsed = input_binding_from_dict(historical.to_dict())
    verification = verify_input_binding(
        parsed,
        subject=spec,
        subject_kind="spec",
        data=data,
        claim=claim,
    )

    assert parsed.tool_version == "0.1.7"
    assert verification.matches is True


def test_cli_rejects_edited_report_finding(tmp_path: Path) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["findings"][0]["message"] = "Edited after the audit completed."
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "verify",
                "report",
                str(report_path),
                "--spec",
                str(spec_path),
                "--data",
                str(data_path),
                "--claim",
                claim,
            ]
        )

    assert exc_info.value.code == 2


def test_cli_rejects_edited_derived_verdict(tmp_path: Path) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["verdict"] = "BLOCK"
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "verify",
                "report",
                str(report_path),
                "--spec",
                str(spec_path),
                "--data",
                str(data_path),
                "--claim",
                claim,
            ]
        )

    assert exc_info.value.code == 2


def test_cli_reports_audit_profile_drift_as_mismatch(
    tmp_path: Path,
    capsys,
) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    data = pd.read_csv(data_path)
    report = audit_spec(spec=spec, data=data, claim=claim)
    assert report.input_binding is not None

    historical_manifest = deepcopy(get_profile_manifest().to_dict())
    historical_manifest["rules"][0]["trigger"] = "Historical trigger semantics."
    historical_profile = build_audit_profile_binding(historical_manifest)
    report.report_binding = build_report_binding(
        report,
        report.input_binding,
        audit_profile=historical_profile,
    )
    report_path = tmp_path / "historical-profile-audit.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    code = main(
        [
            "verify",
            "report",
            str(report_path),
            "--spec",
            str(spec_path),
            "--data",
            str(data_path),
            "--claim",
            claim,
        ]
    )

    assert code == 1
    output = capsys.readouterr().out
    assert "Report integrity: MATCH" in output
    assert "Audit profile: MISMATCH" in output
    assert "Binding: MATCH" in output


def test_cli_requires_reaudit_for_legacy_schema_0_3(tmp_path: Path) -> None:
    spec_path, data_path, claim = _write_inputs(tmp_path)
    report_path = _write_report(tmp_path, spec_path, data_path, claim)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "0.3"
    payload.pop("report_binding")
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "verify",
                "report",
                str(report_path),
                "--spec",
                str(spec_path),
                "--data",
                str(data_path),
                "--claim",
                claim,
            ]
        )

    assert exc_info.value.code == 2
