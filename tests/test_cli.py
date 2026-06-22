from __future__ import annotations

import json
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


def test_json_output_is_valid(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "ready_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
            "--claim",
            "Enterprise and SMB segments differ in conversion rate.",
            "--format",
            "json",
        ],
        capsys,
    )

    payload = json.loads(stdout)

    assert exit_code == 0
    assert stderr == ""
    assert payload["schema_version"] == "0.2"
    assert payload["verdict"] == "READY"
    assert isinstance(payload["findings"], list)
    assert "contract.claim.present" in {finding["rule_id"] for finding in payload["findings"]}


def test_out_and_markdown_write_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"

    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "ready_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
            "--claim",
            "Enterprise and SMB segments differ in conversion rate.",
            "--format",
            "json",
            "--out",
            str(out_path),
            "--markdown",
            str(markdown_path),
        ],
        capsys,
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert stderr == ""
    assert stdout.startswith("Verdict: READY | Summary:")
    assert payload["schema_version"] == "0.2"
    assert payload["verdict"] == "READY"
    assert markdown.startswith("# Audit Report")
    assert "Verdict: `READY`" in markdown


def test_block_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_review_exits_zero_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(FIXTURES / "review_chart.vl.json"),
            "--data",
            str(FIXTURES / "segments.csv"),
            "--claim",
            "Enterprise and SMB segments differ in conversion rate.",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Verdict: REVIEW" in stdout
    assert "- WARN contract.source.present:" in stdout


def test_review_exits_nonzero_with_warnings_as_errors(capsys: pytest.CaptureFixture[str]) -> None:
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
