from __future__ import annotations

import subprocess
import sys

import pytest

from chart_contract.cli import main


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


def test_audit_spec_parses_full_stub_invocation() -> None:
    exit_code = main(
        [
            "audit",
            "spec",
            "spec.vl.json",
            "--data",
            "data.csv",
            "--claim",
            "The launch improved conversion",
            "--format",
            "markdown",
            "--out",
            "report.txt",
            "--markdown",
            "report.md",
            "--warnings-as-errors",
            "--fail-on",
            "REVIEW",
        ]
    )

    assert exit_code == 0


def test_module_entrypoint_version_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "chart_contract", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("chart-contract ")
