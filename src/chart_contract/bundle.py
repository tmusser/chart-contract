"""Cross-chart comparison gates with explicit, bounded identity obligations.

This is a distinct bundle-v1 audit surface. Individual chart rules remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .analysis_scope import parse_analysis_scope_contract
from .audit import BLOCK, FAIL, PASS, READY, REVIEW, WARN, AuditFinding
from .contracts import declared_unit_from_spec, declared_value_representation_from_spec
from .metric_definition import parse_metric_definition_contract
from .spec_policy import audit_spec
from .time_window import parse_time_window_contract

BUNDLE_SCHEMA_VERSION = 1
IDENTITIES = ("analysis_scope", "metric_definition", "unit", "time_window")
_STATUSES = {PASS: 0, WARN: 1, FAIL: 2}

# Identity fields deliberately exclude local column/basis names. They do not
# authenticate upstream definitions; their declared semantic text is exact.
_FIELDS = {
    "analysis_scope": ("scope_id", "scope_version", "scope_definition"),
    "metric_definition": ("metric_id", "metric_version", "metric_definition"),
    "time_window": (
        "window_kind", "window_granularity", "baseline_start", "baseline_end",
        "target_start", "target_end", "baseline_complete", "target_complete",
        "baseline_days", "target_days",
    ),
}


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Bundle {name} must be a non-empty string.")
    return value


def _unique(values: Any, name: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(values, list) or len(values) < minimum:
        raise ValueError(f"Bundle {name} must be an array with at least {minimum} entries.")
    checked = [_text(item, name) for item in values]
    if len(set(checked)) != len(checked):
        raise ValueError(f"Bundle {name} must not contain duplicate values.")
    return checked


def parse_bundle_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on malformed v1 relation declarations; no implicit comparisons."""
    if not isinstance(manifest, Mapping) or set(manifest) != {"version", "artifacts", "relationships"}:
        raise ValueError("Bundle manifest must have exactly version, artifacts, relationships.")
    if type(manifest["version"]) is not int or manifest["version"] != BUNDLE_SCHEMA_VERSION:
        raise ValueError("Bundle manifest version must equal 1.")

    raw_artifacts = manifest["artifacts"]
    if not isinstance(raw_artifacts, list) or len(raw_artifacts) < 2:
        raise ValueError("Bundle needs at least two artifacts.")
    artifacts: list[dict[str, Any]] = []
    for raw in raw_artifacts:
        if not isinstance(raw, Mapping) or not {"id", "spec"} <= set(raw) <= {"id", "spec", "data", "claim"}:
            raise ValueError("Each bundle artifact must have id, spec, and optional data/claim only.")
        item = {"id": _text(raw["id"], "artifact id"), "spec": _text(raw["spec"], "spec path")}
        if "data" in raw:
            item["data"] = _text(raw["data"], "data path")
        if "claim" in raw:
            item["claim"] = _text(raw["claim"], "claim")
        artifacts.append(item)
    artifact_ids = [item["id"] for item in artifacts]
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError("Bundle artifact IDs must be unique.")

    raw_relationships = manifest["relationships"]
    if not isinstance(raw_relationships, list) or not raw_relationships:
        raise ValueError("Bundle must declare at least one relationship.")
    relationships: list[dict[str, Any]] = []
    for raw in raw_relationships:
        if not isinstance(raw, Mapping) or set(raw) != {"id", "artifact_ids", "equal_on"}:
            raise ValueError("Bundle relationship requires exactly id, artifact_ids, equal_on.")
        relation_id = _text(raw["id"], "relationship id")
        members = _unique(raw["artifact_ids"], "relationship artifact_ids", minimum=2)
        dimensions = _unique(raw["equal_on"], "relationship equal_on")
        if not set(members) <= set(artifact_ids):
            raise ValueError(f"Bundle relationship {relation_id!r} references an unknown artifact.")
        if not set(dimensions) <= set(IDENTITIES):
            raise ValueError(f"Bundle relationship {relation_id!r} contains unsupported identity dimensions.")
        relationships.append({"id": relation_id, "artifact_ids": members, "equal_on": dimensions})
    if len({rel["id"] for rel in relationships}) != len(relationships):
        raise ValueError("Bundle relationship IDs must be unique.")
    return {"version": 1, "artifacts": artifacts, "relationships": relationships}


def _identity(spec: Mapping[str, Any], dimension: str) -> dict[str, Any]:
    if dimension == "analysis_scope":
        contract = parse_analysis_scope_contract(spec)
    elif dimension == "metric_definition":
        contract = parse_metric_definition_contract(spec)
    elif dimension == "time_window":
        contract = parse_time_window_contract(spec)
    elif dimension == "unit":
        unit = declared_unit_from_spec(spec)
        if unit is None:
            raise ValueError("Missing declared unit identity.")
        representation = declared_value_representation_from_spec(spec)
        if representation is not None and (
            not isinstance(representation, str) or not representation.strip()
        ):
            raise ValueError("Invalid declared value_representation.")
        return {"unit": unit, "value_representation": representation}
    else:
        raise ValueError(f"Unsupported dimension {dimension!r}.")

    if contract is None:
        raise ValueError(f"Missing declared {dimension} contract.")
    return {key: contract[key] for key in _FIELDS[dimension]}


@dataclass(slots=True)
class BundleReport:
    """Summary is derived anew from bound component audits and identity findings."""

    manifest_sha256: str
    artifact_reports: dict[str, Any]
    relationships: list[dict[str, Any]]
    findings: list[AuditFinding]

    @property
    def verdict(self) -> str:
        if any(report.verdict == BLOCK for report in self.artifact_reports.values()):
            return BLOCK
        if any(f.severity == FAIL for f in self.findings):
            return BLOCK
        if any(report.verdict == REVIEW for report in self.artifact_reports.values()):
            return REVIEW
        if any(f.severity == WARN for f in self.findings):
            return REVIEW
        return READY

    def summary(self) -> str:
        counts = {value: sum(r.verdict == value for r in self.artifact_reports.values()) for value in (READY, REVIEW, BLOCK)}
        return (
            f"Artifacts: READY={counts[READY]} REVIEW={counts[REVIEW]} BLOCK={counts[BLOCK]} | "
            + "Bundle findings: "
            + " ".join(f"{level}={sum(f.severity == level for f in self.findings)}" for level in (PASS, WARN, FAIL))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "chart_contract.audit_bundle_report",
            "schema_version": "1",
            "manifest_sha256": self.manifest_sha256,
            "verdict": self.verdict,
            "summary": self.summary(),
            "artifacts": [
                {"id": identifier, "verdict": report.verdict, "report": report.to_dict()}
                for identifier, report in self.artifact_reports.items()
            ],
            "relationships": self.relationships,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_text(self) -> str:
        lines = [f"Verdict: {self.verdict}", f"Summary: {self.summary()}", "Artifacts:"]
        lines.extend(f"- {identifier}: {report.verdict}" for identifier, report in self.artifact_reports.items())
        lines.append("Bundle findings:")
        lines.extend(
            f"- {finding.severity} {finding.rule_id}: {finding.message}"
            for finding in self.findings
        )
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = [
            "# Audit Bundle Report", "", f"Verdict: \`{self.verdict}\`",
            "", f"Summary: \`{self.summary()}\`", "",
            "## Component artifacts", "",
        ]
        lines.extend(f"- \`{identifier}\`: **{report.verdict}**" for identifier, report in self.artifact_reports.items())
        lines += ["", "## Cross-artifact findings", ""]
        lines.extend(
            f"- **{finding.severity}** \`{finding.rule_id}\`: {finding.message}"
            for finding in self.findings
        )
        return "\n".join(lines)


def audit_bundle(
    manifest: Mapping[str, Any],
    inputs: Mapping[str, tuple[Mapping[str, Any], pd.DataFrame | None, str | None]],
) -> BundleReport:
    """Reaudit all component specs, then compare only explicitly related identities.

    inputs maps manifest artifact IDs to (spec, data, claim). Nothing is fetched
    implicitly and saved historical READY reports are never trusted.
    """
    normalized = parse_bundle_manifest(manifest)
    ids = {item["id"] for item in normalized["artifacts"]}
    if set(inputs) != ids:
        raise ValueError("Bundle inputs must match declared artifact IDs exactly.")

    reports: dict[str, Any] = {}
    specs: dict[str, Mapping[str, Any]] = {}
    for artifact in normalized["artifacts"]:
        identifier = artifact["id"]
        supplied = inputs[identifier]
        if not isinstance(supplied, tuple) or len(supplied) != 3:
            raise ValueError(f"Bundle input {identifier!r} must be (spec, data, claim).")
        spec, data, claim = supplied
        if not isinstance(spec, Mapping):
            raise ValueError(f"Bundle artifact {identifier!r} requires a spec object.")
        specs[identifier] = spec
        reports[identifier] = audit_spec(spec=spec, data=data, claim=claim)

    findings: list[AuditFinding] = []
    for relation in normalized["relationships"]:
        members = relation["artifact_ids"]
        for dimension in relation["equal_on"]:
            rule = f"bundle.identity.{dimension}"
            if any(reports[identifier].verdict == BLOCK for identifier in members):
                findings.append(AuditFinding(
                    "bundle.identity.skipped", WARN,
                    f"Relationship {relation['id']!r} {dimension} comparison skipped: "
                    "at least one component artifact is BLOCK.",
                ))
                continue
            identities: dict[str, dict[str, Any]] = {}
            errors: list[str] = []
            for identifier in members:
                try:
                    identities[identifier] = _identity(specs[identifier], dimension)
                except (ValueError, TypeError, KeyError) as exc:
                    errors.append(f"{identifier}: {exc}")
            if errors:
                findings.append(AuditFinding(
                    rule, FAIL, f"Relationship {relation['id']!r} has missing or invalid "
                    f"{dimension} identity: {'; '.join(errors)}.",
                ))
                continue
            expected = identities[members[0]]
            if any(identities[identifier] != expected for identifier in members[1:]):
                detail = "; ".join(
                    f"{identifier}={json.dumps(identities[identifier], sort_keys=True)}"
                    for identifier in members
                )
                findings.append(AuditFinding(
                    rule, FAIL, f"Relationship {relation['id']!r} mismatched {dimension}: {detail}.",
                    suggestion="Split the comparison or align the declared evidence universe; do not silently rewrite metadata.",
                ))
            else:
                findings.append(AuditFinding(
                    rule, PASS,
                    f"Relationship {relation['id']!r} has matching declared {dimension} "
                    f"identity across {', '.join(members)}.",
                ))
    canonical = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return BundleReport(
        manifest_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        artifact_reports=reports,
        relationships=normalized["relationships"],
        findings=findings,
    )
