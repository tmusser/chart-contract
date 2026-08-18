"""Deterministic fingerprints that bind audit reports to their exact inputs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any

import pandas as pd

from .audit import AuditReport

BOUND_REPORT_SCHEMA_VERSION = "0.3"
PACKAGE_VERSION_FALLBACK = "0.2.0"
HASH_ALGORITHM = "sha256"


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


@dataclass(slots=True)
class BoundAuditReport(AuditReport):
    """Audit report whose verdict is bound to deterministic input fingerprints."""

    input_binding: InputBinding | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["schema_version"] = BOUND_REPORT_SCHEMA_VERSION
        payload["input_binding"] = self.input_binding.to_dict() if self.input_binding else None
        return payload

    def to_markdown(self) -> str:
        base = super().to_markdown()
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
        return "\n".join(lines)

    def matches_inputs(
        self,
        *,
        subject: Any,
        subject_kind: str,
        data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
        claim: str | None,
    ) -> bool:
        if self.input_binding is None:
            return False
        candidate = build_input_binding(
            subject=subject,
            subject_kind=subject_kind,
            data=data,
            claim=claim,
            tool_version=self.input_binding.tool_version,
        )
        return candidate == self.input_binding


def bind_spec_report(
    report: AuditReport,
    *,
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    claim: str | None,
) -> BoundAuditReport:
    return BoundAuditReport(
        findings=list(report.findings),
        input_binding=build_input_binding(
            subject=spec,
            subject_kind="spec",
            data=data,
            claim=claim,
        ),
    )


def bind_chart_report(report: AuditReport, chart: Any) -> BoundAuditReport:
    return BoundAuditReport(
        findings=list(report.findings),
        input_binding=build_input_binding(
            subject=_chart_contract_payload(chart),
            subject_kind="chart_contract",
            data=chart.data,
            claim=chart.claim,
        ),
    )


def build_input_binding(
    *,
    subject: Any,
    subject_kind: str,
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    claim: str | None,
    tool_version: str | None = None,
) -> InputBinding:
    resolved_version = tool_version or _package_version()
    subject_sha256 = _sha256_json(subject)
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


def _package_version() -> str:
    try:
        return package_version("chart-contract")
    except PackageNotFoundError:
        return PACKAGE_VERSION_FALLBACK


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
