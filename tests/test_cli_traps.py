from __future__ import annotations

from pathlib import Path

import pytest

from chart_contract.cli import main

TRAPS = Path(__file__).resolve().parent.parent / "examples" / "traps"


def _claim(name: str) -> str:
    return (TRAPS / f"{name}.claim.txt").read_text(encoding="utf-8").strip()


def invoke(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


@pytest.mark.parametrize(
    ("trap_name", "expected_verdict", "expected_rule_id", "expected_exit"),
    [
        ("too_many_pie_categories", "BLOCK", "visual.arc.category_count", 1),
        ("causal_claim_missing_caveat", "REVIEW", "claim.causal_support", 0),
    ],
)
def test_cli_trap_fixtures(
    trap_name: str,
    expected_verdict: str,
    expected_rule_id: str,
    expected_exit: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = invoke(
        [
            "audit",
            "spec",
            str(TRAPS / f"{trap_name}.vl.json"),
            "--data",
            str(TRAPS / f"{trap_name}.csv"),
            "--claim",
            _claim(trap_name),
        ],
        capsys,
    )

    assert exit_code == expected_exit
    assert stderr == ""
    assert f"Verdict: {expected_verdict}" in stdout
    assert expected_rule_id in stdout
