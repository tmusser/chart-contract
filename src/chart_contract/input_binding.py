"""Deterministic fingerprints that bind audit reports to their exact inputs."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any

import pandas as pd

from .audit import AuditFinding, AuditReport
from .contracts import resolve_spec_claim
from .profiles import (
    AuditProfileBinding,
    audit_profile_binding_from_dict,
    build_audit_profile_binding,
)

BOUND_REPORT_SCHEMA_VERSION = "0.4"
PACKAGE_VERSION_FALLBACK = "0.2.0"
HASH_ALGORITHM = "sha256"
REPORT_BINDING_CANONICALIZATION = "audit-report-semantics-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class InputBinding:
    """Content-addressed identity for the inputs that produced an audit report."""

    algorithm: str
    subject_kind: str
    subject_sha256: str
    data_sha256: str | None
    claim_sha256: str
    tool_version: str
    bundle_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InputBindingVerification:
    """Component-level comparison between a durable binding and current inputs."""

    binding: InputBinding
    candidate: InputBinding

    @property
    def subject_matches(self) -> bool:
        return self.binding.subject_sha256 == self.candidate.subject_sha256

    @property
    def data_matches(self) -> bool:
        return self.binding.data_sha256 == self.candidate.data_sha256

    @property
    def claim_matches(self) -> bool:
        return self.binding.claim_sha256 == self.candidate.claim_sha256

    @property
    def matches(self) -> bool:
        return (
            self.binding.subject_kind == self.candidate.subject_kind
            and self.subject_matches
            and self.data_matches
            and self.claim_matches
            and self.binding.bundle_sha256 == self.candidate.bundle_sha256
        )


@dataclass(frozen=True, slots=True)
class ReportBinding:
    """Content identity for a saved audit result, its inputs, and audit profile."""

    algorithm: str
    canonicalization: str
    input_bundle_sha256: str
    audit_profile: AuditProfileBinding
    report_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "canonicalization": self.canonicalization,
            "input_bundle_sha256": self.input_bundle_sha256,
            "audit_profile": self.audit_profile.to_dict(),
            "report_sha256": self.report_sha256,
        }


@dataclass(slots=True)
class BoundAuditReport(AuditReport):
    """Audit report bound to deterministic inputs, result semantics, and policy identity."""

    input_binding: InputBinding | None = None
    report_binding: ReportBinding | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = AuditReport.to_dict(self)
        payload["schema_version"] = BOUND_REPORT_SCHEMA_VERSION
        payload["input_binding"] = self.input_binding.to_dict() if self.input_binding else None
        payload["report_binding"] = self.report_binding.to_dict() if self.report_binding else None
        return payload

    def to_markdown(self) -> str:
        base = AuditReport.to_markdown(self)
        if self.input_binding is None:
            return base
        binding = self.input_binding
        lines = [
            base,
            "",
            "## Input Binding",
            "",
            f"- Algorithm: `{binding.algorithm}`",
            f"- Subject kind: `{binding.subject_kind}`",
            f"- Subject SHA-256: `{binding.subject_sha256}`",
            f"- Data SHA-256: `{binding.data_sha256 or 'none'}`",
            f"- Claim SHA-256: `{binding.claim_sha256}`",
            f"- Tool version: `{binding.tool_version}`",
            f"- Bundle SHA-256: `{binding.bundle_sha256}`",
        ]
        if self.report_binding is not None:
            report_binding = self.report_binding
            lines.extend(
                [
                    "",
                    "## Report Binding",
                    "",
                    f"- Canonicalization: `{report_binding.canonicalization}`",
                    f"- Audit profile: `{report_binding.audit_profile.profile}`",
                    (
                        "- Audit profile SHA-256: "
                        f"`{report_binding.audit_profile.profile_manifest_sha256}`"
                    ),
                    f"- Report SHA-256: `{report_binding.report_sha256}`",
                ]
            )
        return "\n".join(lines)

    def matches_inputs(
        self,
        *,
        subject: Any,
        subject_kind: str,
        data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
        claim: str | None,
    ) -> bool:
        if self.input_binding is None or self.report_binding is None:
            return False
        if not report_integrity_matches(self):
            return False
        if self.report_binding.audit_profile != build_audit_profile_binding():
            return False
        return verify_input_binding(
            self.input_binding,
            subject=subject,
            subject_kind=subject_kind,
            data=data,
            claim=claim,
        ).matches

    def matches_spec(
        self,
        *,
        spec: Mapping[str, Any],
        data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
        claim: str | None,
    ) -> bool:
        return self.matches_inputs(
            subject=spec,
            subject_kind="spec",
            data=data,
            claim=resolve_spec_claim(spec, claim),
        )

    def matches_chart(self, chart: Any) -> bool:
        return self.matches_inputs(
            subject=chart,
            subject_kind="chart_contract",
            data=chart.data,
            claim=chart.claim,
        )


def report_binding_from_dict(payload: Mapping[str, Any]) -> ReportBinding:
    """Parse a serialized report binding without treating it as authentication."""

    required = {
        "algorithm",
        "canonicalization",
        "input_bundle_sha256",
        "audit_profile",
        "report_sha256",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Report binding is missing required field(s): {', '.join(missing)}")

    algorithm = payload["algorithm"]
    canonicalization = payload["canonicalization"]
    input_bundle_sha256 = payload["input_bundle_sha256"]
    audit_profile_payload = payload["audit_profile"]
    report_sha256 = payload["report_sha256"]

    if algorithm != HASH_ALGORITHM:
        raise ValueError(f"Unsupported report-binding algorithm: {algorithm!r}")
    if canonicalization != REPORT_BINDING_CANONICALIZATION:
        raise ValueError(f"Unsupported report-binding canonicalization: {canonicalization!r}")
    _require_sha256("input_bundle_sha256", input_bundle_sha256, prefix="Report binding")
    if not isinstance(audit_profile_payload, Mapping):
        raise ValueError("Report binding audit_profile must be an object.")
    audit_profile = audit_profile_binding_from_dict(audit_profile_payload)
    _require_sha256("report_sha256", report_sha256, prefix="Report binding")
    return ReportBinding(
        algorithm=algorithm,
        canonicalization=canonicalization,
        input_bundle_sha256=input_bundle_sha256,
        audit_profile=audit_profile,
        report_sha256=report_sha256,
    )


def bound_report_from_dict(payload: Mapping[str, Any]) -> BoundAuditReport:
    """Parse and self-check a serialized schema-0.4 bound audit report."""

    schema_version = payload.get("schema_version")
    if schema_version != BOUND_REPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Expected bound report schema {BOUND_REPORT_SCHEMA_VERSION}; got {schema_version!r}."
        )

    serialized_input = payload.get("input_binding")
    if not isinstance(serialized_input, Mapping):
        raise ValueError("Bound report is missing input_binding.")
    input_binding = input_binding_from_dict(serialized_input)

    serialized_report = payload.get("report_binding")
    if not isinstance(serialized_report, Mapping):
        raise ValueError("Bound report is missing report_binding.")
    report_binding = report_binding_from_dict(serialized_report)
    if report_binding.input_bundle_sha256 != input_binding.bundle_sha256:
        raise ValueError("Report binding input_bundle_sha256 does not match input_binding.")

    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raise ValueError("Bound report findings must be a list.")
    findings: list[AuditFinding] = []
    for index, raw_finding in enumerate(raw_findings):
        if not isinstance(raw_finding, Mapping):
            raise ValueError(f"Bound report finding {index} must be an object.")
        required = {"rule_id", "severity", "message"}
        missing = sorted(required - set(raw_finding))
        if missing:
            raise ValueError(
                f"Bound report finding {index} is missing required field(s): {', '.join(missing)}"
            )
        rule_id = raw_finding["rule_id"]
        severity = raw_finding["severity"]
        message = raw_finding["message"]
        suggestion = raw_finding.get("suggestion")
        field_name = raw_finding.get("field")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"Bound report finding {index} rule_id must be a non-empty string.")
        if not isinstance(severity, str):
            raise ValueError(f"Bound report finding {index} severity must be a string.")
        if not isinstance(message, str) or not message:
            raise ValueError(f"Bound report finding {index} message must be a non-empty string.")
        if suggestion is not None and not isinstance(suggestion, str):
            raise ValueError(f"Bound report finding {index} suggestion must be a string or null.")
        if field_name is not None and not isinstance(field_name, str):
            raise ValueError(f"Bound report finding {index} field must be a string or null.")
        findings.append(
            AuditFinding(
                rule_id=rule_id,
                severity=severity,
                message=message,
                suggestion=suggestion,
                field=field_name,
            )
        )

    report = BoundAuditReport(
        findings=findings,
        input_binding=input_binding,
        report_binding=report_binding,
    )
    derived = AuditReport.to_dict(report)
    for field_name in (
        "passed",
        "has_failures",
        "has_warnings",
        "verdict",
        "summary",
        "verdict_summary",
    ):
        if payload.get(field_name) != derived[field_name]:
            raise ValueError(
                f"Bound report {field_name} does not match the serialized findings."
            )
    if not report_integrity_matches(report):
        raise ValueError("Bound report report_sha256 does not match its serialized audit result.")
    return report


def input_binding_from_dict(payload: Mapping[str, Any]) -> InputBinding:
    """Parse and self-check a serialized input binding."""

    required = {
        "algorithm",
        "subject_kind",
        "subject_sha256",
        "data_sha256",
        "claim_sha256",
        "tool_version",
        "bundle_sha256",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Input binding is missing required field(s): {', '.join(missing)}")

    algorithm = payload["algorithm"]
    subject_kind = payload["subject_kind"]
    subject_sha256 = payload["subject_sha256"]
    data_sha256 = payload["data_sha256"]
    claim_sha256 = payload["claim_sha256"]
    tool_version = payload["tool_version"]
    bundle_sha256 = payload["bundle_sha256"]

    if algorithm != HASH_ALGORITHM:
        raise ValueError(f"Unsupported input-binding algorithm: {algorithm!r}")
    if not isinstance(subject_kind, str) or not subject_kind:
        raise ValueError("Input binding subject_kind must be a non-empty string.")
    _require_sha256("subject_sha256", subject_sha256)
    if data_sha256 is not None:
        _require_sha256("data_sha256", data_sha256)
    _require_sha256("claim_sha256", claim_sha256)
    if not isinstance(tool_version, str) or not tool_version:
        raise ValueError("Input binding tool_version must be a non-empty string.")
    _require_sha256("bundle_sha256", bundle_sha256)

    binding = InputBinding(
        algorithm=algorithm,
        subject_kind=subject_kind,
        subject_sha256=subject_sha256,
        data_sha256=data_sha256,
        claim_sha256=claim_sha256,
        tool_version=tool_version,
        bundle_sha256=bundle_sha256,
    )
    expected_bundle = _bundle_sha256(binding)
    if expected_bundle != binding.bundle_sha256:
        raise ValueError("Input binding bundle_sha256 does not match its recorded components.")
    return binding


def verify_input_binding(
    binding: InputBinding,
    *,
    subject: Any,
    subject_kind: str,
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    claim: str | None,
) -> InputBindingVerification:
    """Recompute current input fingerprints using the binding's recorded tool version."""

    candidate = build_input_binding(
        subject=subject,
        subject_kind=subject_kind,
        data=data,
        claim=claim,
        tool_version=binding.tool_version,
    )
    return InputBindingVerification(binding=binding, candidate=candidate)


def bind_spec_report(
    report: AuditReport,
    *,
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    claim: str | None,
) -> BoundAuditReport:
    input_binding = build_input_binding(
        subject=spec,
        subject_kind="spec",
        data=data,
        claim=claim,
    )
    return _bind_report(report, input_binding)


def bind_chart_report(report: AuditReport, chart: Any) -> BoundAuditReport:
    input_binding = build_input_binding(
        subject=chart,
        subject_kind="chart_contract",
        data=chart.data,
        claim=chart.claim,
    )
    return _bind_report(report, input_binding)


def _bind_report(report: AuditReport, input_binding: InputBinding) -> BoundAuditReport:
    bound = BoundAuditReport(findings=list(report.findings), input_binding=input_binding)
    bound.report_binding = build_report_binding(bound, input_binding)
    return bound


def build_report_binding(
    report: AuditReport,
    input_binding: InputBinding,
    *,
    audit_profile: AuditProfileBinding | None = None,
) -> ReportBinding:
    """Bind a concrete audit result to its input bundle and audit-profile semantics."""

    profile_binding = audit_profile or build_audit_profile_binding()
    semantic_payload = _report_semantic_payload(report, input_binding, profile_binding)
    return ReportBinding(
        algorithm=HASH_ALGORITHM,
        canonicalization=REPORT_BINDING_CANONICALIZATION,
        input_bundle_sha256=input_binding.bundle_sha256,
        audit_profile=profile_binding,
        report_sha256=_sha256_json(semantic_payload),
    )


def report_integrity_matches(report: BoundAuditReport) -> bool:
    """Check that a bound report still matches its originally bound result semantics."""

    if report.input_binding is None or report.report_binding is None:
        return False
    if report.report_binding.input_bundle_sha256 != report.input_binding.bundle_sha256:
        return False
    expected = build_report_binding(
        report,
        report.input_binding,
        audit_profile=report.report_binding.audit_profile,
    )
    return expected == report.report_binding


def _report_semantic_payload(
    report: AuditReport,
    input_binding: InputBinding,
    audit_profile: AuditProfileBinding,
) -> dict[str, Any]:
    serialized = AuditReport.to_dict(report)
    return {
        "input_bundle_sha256": input_binding.bundle_sha256,
        "audit_profile": audit_profile.to_dict(),
        "result": {
            "passed": serialized["passed"],
            "has_failures": serialized["has_failures"],
            "has_warnings": serialized["has_warnings"],
            "verdict": serialized["verdict"],
            "summary": serialized["summary"],
            "verdict_summary": serialized["verdict_summary"],
            "findings": serialized["findings"],
        },
    }


def build_input_binding(
    *,
    subject: Any,
    subject_kind: str,
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    claim: str | None,
    tool_version: str | None = None,
) -> InputBinding:
    resolved_version = tool_version or _package_version()
    normalized_subject = _subject_payload(subject, subject_kind)
    subject_sha256 = _sha256_json(normalized_subject)
    data_sha256 = _hash_data(data)
    claim_sha256 = _sha256_json(claim)
    bundle_payload = {
        "algorithm": HASH_ALGORITHM,
        "subject_kind": subject_kind,
        "subject_sha256": subject_sha256,
        "data_sha256": data_sha256,
        "claim_sha256": claim_sha256,
        "tool_version": resolved_version,
    }
    return InputBinding(
        algorithm=HASH_ALGORITHM,
        subject_kind=subject_kind,
        subject_sha256=subject_sha256,
        data_sha256=data_sha256,
        claim_sha256=claim_sha256,
        tool_version=resolved_version,
        bundle_sha256=_sha256_json(bundle_payload),
    )


def _bundle_sha256(binding: InputBinding) -> str:
    return _sha256_json(
        {
            "algorithm": binding.algorithm,
            "subject_kind": binding.subject_kind,
            "subject_sha256": binding.subject_sha256,
            "data_sha256": binding.data_sha256,
            "claim_sha256": binding.claim_sha256,
            "tool_version": binding.tool_version,
        }
    )


def _require_sha256(field_name: str, value: Any, *, prefix: str = "Input binding") -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{prefix} {field_name} must be a lowercase SHA-256 hex digest.")


def _package_version() -> str:
    try:
        return package_version("chart-contract")
    except PackageNotFoundError:
        return PACKAGE_VERSION_FALLBACK


def _subject_payload(subject: Any, subject_kind: str) -> Any:
    if subject_kind == "chart_contract" and is_dataclass(subject):
        return _chart_contract_payload(subject)
    return subject


def _chart_contract_payload(chart: Any) -> dict[str, Any]:
    if not is_dataclass(chart):
        raise TypeError("chart input binding requires a dataclass chart contract")
    return {
        field.name: getattr(chart, field.name)
        for field in fields(chart)
        if field.name not in {"data", "claim"}
    }


def _hash_data(data: pd.DataFrame | Sequence[Mapping[str, Any]] | None) -> str | None:
    if data is None:
        return None
    if isinstance(data, pd.DataFrame):
        frame = data
    else:
        frame = pd.DataFrame([dict(item) for item in data])

    payload = {
        "columns": [_normalize_scalar(value) for value in frame.columns.tolist()],
        "index": [_normalize_scalar(value) for value in frame.index.tolist()],
        "index_names": [_normalize_scalar(value) for value in frame.index.names],
        "dtypes": [_dtype_payload(dtype) for dtype in frame.dtypes],
        "rows": [
            [_normalize_scalar(value) for value in row]
            for row in frame.itertuples(index=False, name=None)
        ],
    }
    return _sha256_json(payload)


def _dtype_payload(dtype: Any) -> Any:
    if isinstance(dtype, pd.CategoricalDtype):
        return {
            "name": "category",
            "categories": [_normalize_scalar(value) for value in dtype.categories.tolist()],
            "ordered": bool(dtype.ordered),
        }
    return str(dtype)


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        _normalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_json(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    return _normalize_scalar(value)


def _normalize_scalar(value: Any) -> Any:
    if value is None or value is pd.NA or value is pd.NaT:
        return {"__missing__": True}
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"__missing__": True}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, (pd.Timestamp, datetime, date, time)):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, (pd.Timedelta, timedelta)):
        return {"__timedelta__": str(value)}

    item = getattr(value, "item", None)
    if callable(item):
        try:
            converted = item()
        except (TypeError, ValueError):
            converted = value
        if converted is not value:
            return _normalize_scalar(converted)

    if isinstance(value, str):
        return value
    return {"__repr__": repr(value), "__type__": type(value).__qualname__}
