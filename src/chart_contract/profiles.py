"""Machine-readable audit profile metadata and semantic bindings."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

PROFILE_MANIFEST_SCHEMA_VERSION = "1.0"
PROFILE_MANIFEST_TYPE = "chart_contract.audit_profile_manifest"
PROFILE_BINDING_CANONICALIZATION = "audit-profile-semantics-v1"
PROFILE_BINDING_ALGORITHM = "sha256"
DEFAULT_PROFILE = "audit-v0.2"
PACKAGE_VERSION_FALLBACK = "0.2.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SCOPE_NOTICE = (
    "The audit profile describes implemented chart-contract checks. Inspecting or matching "
    "this metadata is not scientific validation and does not prove a chart, claim, data set, "
    "or visual interpretation correct."
)
NOT_EVALUATED = (
    "whether the source data are accurate, representative, complete, or unbiased",
    "whether an analytical or statistical method is scientifically appropriate",
    "whether causal, diagnostic, or substantive interpretations are true",
    "whether declared user intent, provenance, caveats, or evidence metadata are truthful",
    "whether an arbitrary Vega-Lite composition is semantically complete beyond implemented checks",
)


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    applies_to: tuple[str, ...]
    severities: tuple[str, ...]
    trigger: str
    known_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.rule_id,
            "applies_to": list(self.applies_to),
            "severities": list(self.severities),
            "trigger": self.trigger,
            "known_boundary": self.known_boundary,
        }


@dataclass(frozen=True)
class ProfileManifest:
    name: str
    description: str
    rules: tuple[RuleSpec, ...]

    def rule(self, rule_id: str) -> RuleSpec:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        raise KeyError(f"Unknown rule {rule_id!r} for profile {self.name!r}.")

    def to_dict(self) -> dict[str, Any]:
        rules = [rule.to_dict() for rule in self.rules]
        return {
            "schema_version": PROFILE_MANIFEST_SCHEMA_VERSION,
            "type": PROFILE_MANIFEST_TYPE,
            "tool": {
                "name": "chart-contract",
                "version": _package_version(),
            },
            "profile": {
                "name": self.name,
                "description": self.description,
            },
            "scientific_validation": False,
            "automatic_adjudication": False,
            "scope_notice": SCOPE_NOTICE,
            "not_evaluated": list(NOT_EVALUATED),
            "rule_count": len(rules),
            "rules": rules,
        }


@dataclass(frozen=True)
class AuditProfileBinding:
    algorithm: str
    canonicalization: str
    profile: str
    profile_manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _r(
    rule_id: str,
    applies_to: tuple[str, ...],
    severities: tuple[str, ...],
    trigger: str,
    known_boundary: str,
) -> RuleSpec:
    return RuleSpec(rule_id, applies_to, severities, trigger, known_boundary)


AUDIT_V0_2 = ProfileManifest(
    name=DEFAULT_PROFILE,
    description=(
        "Deterministic claim, data, provenance, diagnostic, and visual-integrity checks "
        "implemented by chart-contract 0.2-era chart and Vega-Lite spec audits."
    ),
    rules=(
        _r("contract.claim.present", ("chart", "spec"), ("PASS", "FAIL"), "A chart/spec must declare an analytical claim.", "Claim presence does not establish that the claim is supported or true."),
        _r("contract.source.present", ("chart", "spec"), ("PASS", "WARN"), "Source/provenance metadata should be declared.", "A declared source is not independently verified."),
        _r("data.y.column", ("chart",), ("FAIL",), "The declared y field is missing from chart data.", "Column presence does not establish measurement validity."),
        _r("data.y.numeric", ("chart",), ("PASS", "FAIL"), "The declared y field must be numeric for quantitative chart intents.", "Numeric type does not establish that the metric is meaningful or correctly computed."),
        _r("labels.unit.present", ("chart", "spec"), ("PASS", "WARN"), "Quantitative values should declare a unit.", "A unit label is not checked against source-system semantics."),
        _r("data.required.column", ("chart",), ("FAIL",), "A referenced x/y/group field is missing.", "The rule checks presence only, not semantic appropriateness."),
        _r("data.encoding.fields", ("spec",), ("PASS", "FAIL"), "Encoded Vega-Lite fields must exist in supplied or inline data.", "Only fields reconstructable from the audited spec/data are checked."),
        _r("data.encoding.quantitative", ("spec",), ("PASS", "FAIL"), "Quantitative encodings must map to numeric supplied data.", "Numeric type does not prove the encoding or aggregation is analytically appropriate."),
        _r("data.not_empty", ("chart",), ("PASS", "WARN"), "First-party chart data should contain observations.", "Non-empty data can still be insufficient or biased."),
        _r("data.trend.min_points", ("chart", "spec"), ("PASS", "FAIL"), "Directional trend claims require at least two complete observations.", "Two observations establish only minimum directionality, not trend robustness."),
        _r("data.trend.x.ordered", ("chart",), ("PASS", "WARN"), "Trend x values should be datetime-like or ordered.", "Ordering does not prove temporal comparability or causal interpretation."),
        _r("data.distribution.value.numeric", ("chart", "spec"), ("PASS", "FAIL"), "Distribution/quantile metrics must exist and be numeric.", "Numeric type does not validate distributional interpretation."),
        _r("data.distribution.sample_size", ("chart", "spec"), ("PASS", "WARN", "FAIL"), "Distribution and quantile diagnostics FAIL below 5 usable observations, WARN for 5-19, PASS at 20+.", "Thresholds are deterministic guardrails, not statistical certification."),
        _r("data.distribution.group_sample_size", ("chart", "spec"), ("PASS", "WARN"), "Grouped distributions WARN when any non-null group has fewer than 10 usable rows.", "The threshold does not establish representativeness or equal precision across groups."),
        _r("readability.histogram.bins", ("chart", "spec"), ("PASS", "WARN"), "Integer histogram bin counts outside 5-50 WARN; default or custom-controlled binning passes.", "Readable bin counts do not prove the chosen binning preserves every relevant feature."),
        _r("visual.violin.sample_size", ("chart", "spec"), ("PASS", "WARN"), "Violin views WARN below 30 usable observations.", "The threshold is a readability guardrail, not density-estimation validation."),
        _r("stat.qq.reference_distribution", ("chart", "spec"), ("PASS", "FAIL"), "QQ audits support only the declared normal reference distribution.", "Passing does not prove normality."),
        _r("stat.qq.tie_density", ("chart", "spec"), ("PASS", "WARN"), "QQ audits WARN when fewer than half of 10+ observations are distinct.", "Tie density is only one failure mode for quantile interpretation."),
        _r("claim.qq.normality_support", ("chart", "spec"), ("PASS", "WARN"), "QQ audits WARN when outer-quantile deviation reaches 0.8 sample standard deviations.", "This deterministic visual heuristic is not a formal normality test."),
        _r("visual.qq.reference_line", ("chart", "spec"), ("PASS", "FAIL"), "QQ views require the supported fitted normal reference line.", "A reference line makes departures interpretable but does not certify model fit."),
        _r("data.residual.fitted.numeric", ("chart", "spec"), ("PASS", "FAIL"), "Residual diagnostics require numeric fitted values.", "Numeric fitted values do not establish model adequacy."),
        _r("data.residual.sample_size", ("chart", "spec"), ("PASS", "WARN", "FAIL"), "Residual diagnostics FAIL below 5 complete pairs, WARN for 5-19, PASS at 20+.", "The threshold does not guarantee power to detect all residual structure."),
        _r("data.residual.variation", ("chart", "spec"), ("PASS", "WARN"), "Residual diagnostics WARN when residuals have no variation.", "Variation alone does not imply residual behavior is acceptable."),
        _r("claim.residual.pattern_support", ("chart", "spec"), ("PASS", "WARN"), "Residual absence claims WARN at |correlation| >= 0.5 or ordered-thirds mean shift >= 1 residual SD.", "The heuristic does not exhaust heteroskedasticity, autocorrelation, leverage, or nonlinear structure."),
        _r("visual.residual.zero_reference", ("chart", "spec"), ("PASS", "FAIL"), "Residual views require a zero reference line.", "The line supports interpretation but does not validate residual assumptions."),
        _r("data.set_membership.columns", ("chart",), ("PASS", "FAIL"), "Set-membership audits require member plus two membership columns.", "Column declarations do not prove the universe definition is semantically complete."),
        _r("data.set_membership.member_unique", ("chart",), ("PASS", "FAIL"), "Set-membership member identifiers must be non-null and unique.", "Uniqueness does not prove entity resolution correctness."),
        _r("data.set_membership.binary", ("chart",), ("PASS", "FAIL"), "Membership columns must be booleans or integer 0/1 with no nulls.", "Binary encoding does not prove membership labels are correct."),
        _r("data.set_membership.region_counts", ("chart",), ("PASS", "FAIL"), "A-only, overlap, B-only, and neither counts must reconcile to the universe.", "Reconciliation checks arithmetic consistency, not semantic set validity."),
        _r("visual.set_membership.area_semantics", ("chart",), ("PASS", "FAIL"), "Set-membership rendering must declare schematic geometry and authoritative labels.", "Schematic circles are not area-proportional evidence."),
        _r("readability.rank.category_count", ("chart",), ("PASS", "WARN"), "Rank charts WARN when category count exceeds the implemented readability limit.", "Category-count heuristics do not determine the best presentation for every audience."),
        _r("readability.color.category_count", ("chart", "spec"), ("PASS", "WARN"), "Color encodings WARN above eight observed categories.", "The rule does not certify accessibility or perceptual separability."),
        _r("claim.causal_support", ("chart", "spec"), ("PASS", "WARN"), "Causal language without caveat or declared causal evidence metadata WARNs.", "Metadata is declarative; the audit does not independently establish causal identification."),
        _r("claim.event_without_caveat", ("chart",), ("WARN",), "An event annotation paired with no caveat creates a timing-based causal-inference warning.", "The rule cannot determine whether viewers will infer causality in every context."),
        _r("contract.filters.implied", ("chart",), ("WARN",), "Claims implying a filter/time window WARN when filters metadata is absent.", "Text heuristics cannot reconstruct every implicit analytical scope."),
        _r("labels.title.quality", ("chart", "spec"), ("PASS", "WARN"), "Missing or generic titles WARN; specific titles pass.", "Title specificity does not establish claim correctness."),
        _r("visual.intent.match", ("chart",), ("PASS", "FAIL"), "First-party chart intent must match a supported renderer contract.", "A supported intent does not make the visual analytically optimal."),
        _r("visual.integrity.decoration", ("chart", "spec"), ("PASS", "WARN", "FAIL"), "Decorative/chartjunk-like terms WARN for charts/non-arc specs and FAIL for arc specs.", "Pattern detection cannot identify every distracting or misleading design choice."),
        _r("scale.bar.nonzero_baseline", ("spec",), ("PASS", "FAIL"), "Quantitative bar axes FAIL when scale.zero is false.", "The rule covers explicit Vega-Lite baseline controls, not every preprocessing transform."),
        _r("scale.bar.explicit_domain_zero", ("spec",), ("FAIL",), "Explicit numeric bar domains that exclude zero FAIL.", "Dynamic domain expressions cannot always be proven to preserve zero."),
        _r("scale.override.authorization", ("spec",), ("PASS", "FAIL"), "Quantitative x/y scale overrides require explicit user-request metadata.", "The declaration records intent; it does not prove the user actually requested the override."),
        _r("scale.normalization.authorization", ("spec",), ("PASS", "FAIL"), "Native Vega-Lite normalization requires explicit user-request metadata.", "The rule cannot reconstruct semantic normalization hidden in arbitrary transforms or preprocessed data."),
        _r("visual.arc.category_count", ("spec",), ("PASS", "FAIL"), "Arc specs FAIL above six observed categories.", "A passing category count does not make an arc chart the best comparison form."),
    ),
)

_PROFILE_MANIFESTS = {AUDIT_V0_2.name: AUDIT_V0_2}
_RULE_REGISTRY = {rule.rule_id: rule for rule in AUDIT_V0_2.rules}


def _package_version() -> str:
    try:
        return package_version("chart-contract")
    except PackageNotFoundError:
        return PACKAGE_VERSION_FALLBACK


def supported_profiles() -> tuple[str, ...]:
    return tuple(_PROFILE_MANIFESTS)


def get_profile_manifest(name: str = DEFAULT_PROFILE) -> ProfileManifest:
    try:
        return _PROFILE_MANIFESTS[name]
    except KeyError as exc:
        supported = ", ".join(supported_profiles())
        raise ValueError(f"Unsupported profile {name!r}. Supported profiles: {supported}.") from exc


def validate_rule_emission(rule_id: str, severity: str) -> None:
    try:
        rule = _RULE_REGISTRY[rule_id]
    except KeyError as exc:
        raise ValueError(f"Audit rule {rule_id!r} is not registered in {DEFAULT_PROFILE}.") from exc
    if severity not in rule.severities:
        allowed = ", ".join(rule.severities)
        raise ValueError(
            f"Audit rule {rule_id!r} emitted severity {severity!r}; allowed severities: {allowed}."
        )


def build_audit_profile_binding(
    manifest: ProfileManifest | Mapping[str, Any] | None = None,
) -> AuditProfileBinding:
    if manifest is None:
        payload = get_profile_manifest().to_dict()
    elif isinstance(manifest, ProfileManifest):
        payload = manifest.to_dict()
    else:
        payload = dict(manifest)

    semantic_payload = _semantic_manifest_payload(payload)
    profile = semantic_payload["profile"]
    return AuditProfileBinding(
        algorithm=PROFILE_BINDING_ALGORITHM,
        canonicalization=PROFILE_BINDING_CANONICALIZATION,
        profile=str(profile["name"]),
        profile_manifest_sha256=_sha256_json(semantic_payload),
    )


def audit_profile_binding_from_dict(payload: Mapping[str, Any]) -> AuditProfileBinding:
    required = {"algorithm", "canonicalization", "profile", "profile_manifest_sha256"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Audit profile binding is missing required field(s): {', '.join(missing)}")
    algorithm = payload["algorithm"]
    canonicalization = payload["canonicalization"]
    profile = payload["profile"]
    digest = payload["profile_manifest_sha256"]
    if algorithm != PROFILE_BINDING_ALGORITHM:
        raise ValueError(f"Unsupported audit profile binding algorithm: {algorithm!r}")
    if canonicalization != PROFILE_BINDING_CANONICALIZATION:
        raise ValueError(f"Unsupported audit profile canonicalization: {canonicalization!r}")
    if not isinstance(profile, str) or not profile:
        raise ValueError("Audit profile binding profile must be a non-empty string.")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ValueError("Audit profile binding digest must be a lowercase SHA-256 hex digest.")
    return AuditProfileBinding(
        algorithm=algorithm,
        canonicalization=canonicalization,
        profile=profile,
        profile_manifest_sha256=digest,
    )


def load_profile_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Profile manifest file not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Profile manifest is not valid JSON: {manifest_path}: {exc.msg}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Profile manifest root must be an object/mapping.")
    _semantic_manifest_payload(payload)
    return dict(payload)


def _semantic_manifest_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("type") != PROFILE_MANIFEST_TYPE:
        raise ValueError(
            f"Expected profile manifest type {PROFILE_MANIFEST_TYPE!r}; got {payload.get('type')!r}."
        )
    if payload.get("schema_version") != PROFILE_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported profile manifest schema version: "
            f"{payload.get('schema_version')!r}."
        )
    profile = payload.get("profile")
    rules = payload.get("rules")
    if not isinstance(profile, Mapping) or not isinstance(profile.get("name"), str):
        raise ValueError("Profile manifest must contain profile.name.")
    if not isinstance(rules, list):
        raise ValueError("Profile manifest rules must be a list.")
    if payload.get("rule_count") != len(rules):
        raise ValueError("Profile manifest rule_count does not match rules length.")
    return {
        "profile": dict(profile),
        "scientific_validation": payload.get("scientific_validation"),
        "automatic_adjudication": payload.get("automatic_adjudication"),
        "scope_notice": payload.get("scope_notice"),
        "not_evaluated": payload.get("not_evaluated"),
        "rule_count": payload.get("rule_count"),
        "rules": rules,
    }


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
