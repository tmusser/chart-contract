from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from chart_contract.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cli"


def invoke(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


@pytest.mark.parametrize(
    ("argv", "expected_usage"),
    [
        (["--help"], "usage: chart-contract"),
        (["audit", "--help"], "usage: chart-contract audit"),
        (["audit", "spec", "--help"], "usage: chart-contract audit spec"),
    ],
)
def test_help_surfaces_parse(argv: list[str], expected_usage: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(argv)

    assert excinfo.value.code == 0
    assert expected_usage in capsys.readouterr().out


def test_version_surface_parses(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.startswith("chart-contract ")


def test_missing_claim_produces_block(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "ready_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "Verdict: BLOCK" in stdout
    assert "Summary:" in stdout
    assert "- FAIL contract.claim.present:" in stdout


def test_bad_arc_fixture_produces_block(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "bad_arc_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.json"),
            "--claim",
            "The launch improved conversion",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "Verdict: BLOCK" in stdout
    assert "- FAIL visual.arc.category_count:" in stdout


def test_corrected_fixture_is_ready(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "ready_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
            "--claim",
            "Enterprise and SMB segments differ in conversion rate.",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Verdict: READY" in stdout
    assert "- PASS contract.claim.present:" in stdout


def test_warnings_as_errors_promotes_review_to_failure(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "review_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
            "--claim",
            "Enterprise and SMB segments differ in conversion rate.",
            "--warnings-as-errors",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "Verdict: REVIEW" in stdout
    assert "- WARN contract.source.present:" in stdout


def test_unsupported_data_extension_errors(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "audit",
                "spec",
                str(FIXTURES / "ready_chart.vl.json"),
                "--data",
                str(FIXTURES / "segments.txt"),
                "--claim",
                "Enterprise and SMB segments differ in conversion rate.",
            ]
        )

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "Unsupported data file extension: .txt" in captured.err


def test_module_entrypoint_version_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "chart_contract", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("chart-contract ")
