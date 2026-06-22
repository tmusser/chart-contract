from chart_contract import AuditFinding, AuditReport


def make_report(*findings: AuditFinding) -> AuditReport:
    return AuditReport(findings=list(findings))


def test_ready_report_serialization() -> None:
    report = make_report()

    assert report.to_dict() == {
        "schema_version": "0.2",
        "passed": True,
        "has_failures": False,
        "has_warnings": False,
        "verdict": "READY",
        "summary": "PASS=0 WARN=0 FAIL=0",
        "verdict_summary": "READY: PASS=0 WARN=0 FAIL=0",
        "findings": [],
    }


def test_review_report_serialization() -> None:
    finding = AuditFinding(
        rule_id="contract.source.present",
        severity="WARN",
        message="Source is missing; provenance should be visible.",
        suggestion="Add a source such as a table, model, or query identifier.",
        field="source",
    )
    report = make_report(finding)

    assert report.to_dict() == {
        "schema_version": "0.2",
        "passed": True,
        "has_failures": False,
        "has_warnings": True,
        "verdict": "REVIEW",
        "summary": "PASS=0 WARN=1 FAIL=0",
        "verdict_summary": "REVIEW: PASS=0 WARN=1 FAIL=0",
        "findings": [finding.to_dict()],
    }


def test_block_report_serialization() -> None:
    finding = AuditFinding(
        rule_id="contract.claim.present",
        severity="FAIL",
        message="Claim is required for an audited chart.",
        suggestion="Add a claim that states what the viewer should believe from the chart.",
        field="claim",
    )
    report = make_report(finding)

    assert report.to_dict() == {
        "schema_version": "0.2",
        "passed": False,
        "has_failures": True,
        "has_warnings": False,
        "verdict": "BLOCK",
        "summary": "PASS=0 WARN=0 FAIL=1",
        "verdict_summary": "BLOCK: PASS=0 WARN=0 FAIL=1",
        "findings": [finding.to_dict()],
    }


def test_markdown_includes_finding_details_and_suggestions() -> None:
    warn_finding = AuditFinding(
        rule_id="contract.source.present",
        severity="WARN",
        message="Source is missing; provenance should be visible.",
        suggestion="Add a source such as a table, model, or query identifier.",
        field="source",
    )
    fail_finding = AuditFinding(
        rule_id="contract.claim.present",
        severity="FAIL",
        message="Claim is required for an audited chart.",
        field="claim",
    )
    markdown = make_report(warn_finding, fail_finding).to_markdown()

    assert "Verdict: `BLOCK`" in markdown
    assert "Summary: `PASS=0 WARN=1 FAIL=1`" in markdown
    assert "**WARN** `contract.source.present`: Source is missing; provenance should be visible." in markdown
    assert "Suggestion: Add a source such as a table, model, or query identifier." in markdown
    assert "**FAIL** `contract.claim.present`: Claim is required for an audited chart." in markdown
    assert "Suggestion: None" not in markdown
