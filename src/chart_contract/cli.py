"""Command-line entry points for chart_contract."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

import pandas as pd

from .audit import BLOCK, READY, REVIEW, AuditReport
from .input_binding import (
    BOUND_REPORT_SCHEMA_VERSION,
    input_binding_from_dict,
    verify_input_binding,
)
from .profile_diff import ProfileDiff, build_profile_diff
from .profiles import DEFAULT_PROFILE, ProfileManifest, get_profile_manifest, load_profile_manifest
from .spec_policy import audit_spec

SUPPORTED_REPORT_FORMATS = ("text", "json", "markdown")
SUPPORTED_VERDICTS = (READY, REVIEW, BLOCK)
VERDICT_RANK = {READY: 0, REVIEW: 1, BLOCK: 2}
PACKAGE_VERSION_FALLBACK = "0.2.0"


class CLIError(ValueError):
    """A deterministic CLI validation error."""


def _package_version() -> str:
    try:
        return package_version("chart-contract")
    except PackageNotFoundError:
        return PACKAGE_VERSION_FALLBACK


def _load_json_object(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CLIError(f"{kind} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CLIError(f"{kind} file is not valid JSON: {path}: {exc.msg}") from exc

    if not isinstance(raw, Mapping):
        raise CLIError(f"{kind} file must contain a JSON object: {path}")
    return dict(raw)


def _load_json_spec(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        raise CLIError(f"Spec file must be JSON (.json): {path}")
    return _load_json_object(path, kind="Spec")


def _load_json_report(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        raise CLIError(f"Report file must be JSON (.json): {path}")
    return _load_json_object(path, kind="Report")


def _load_json_data(path: Path) -> pd.DataFrame:
    try:
        frame = pd.read_json(path)
    except FileNotFoundError as exc:
        raise CLIError(f"Data file not found: {path}") from exc
    except ValueError:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CLIError(f"Data file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CLIError(f"Data file is not valid JSON: {path}: {exc.msg}") from exc

        if isinstance(raw, list):
            return pd.DataFrame(raw)
        if isinstance(raw, Mapping):
            if raw and all(isinstance(value, list) for value in raw.values()):
                return pd.DataFrame(raw)
            if isinstance(raw.get("records"), list):
                return pd.DataFrame(raw["records"])
            normalized = pd.json_normalize(raw)
            if not normalized.empty or not raw:
                return normalized
            return pd.DataFrame([raw])
        raise CLIError(f"JSON data must be an object or array of records: {path}")

    if isinstance(frame, pd.Series):
        return frame.to_frame().T
    return frame


def _load_data(path_text: str | None) -> pd.DataFrame | None:
    if not path_text:
        return None

    path = Path(path_text)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(path)
        except FileNotFoundError as exc:
            raise CLIError(f"Data file not found: {path}") from exc
    if suffix == ".json":
        return _load_json_data(path)
    raise CLIError(f"Unsupported data file extension: {path.suffix or '<none>'}. Use .csv or .json.")


def _format_text_report(report: AuditReport) -> str:
    lines = [
        f"Verdict: {report.verdict}",
        f"Summary: {report.summary()}",
        "Findings:",
    ]
    if not report.findings:
        lines.append("- None")
        return "\n".join(lines)

    for finding in report.findings:
        line = f"- {finding.severity} {finding.rule_id}: {finding.message}"
        if finding.suggestion:
            line += f" Suggestion: {finding.suggestion}"
        lines.append(line)
    return "\n".join(lines)


def _render_report(report: AuditReport, format_name: str) -> str:
    if format_name == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if format_name == "markdown":
        return report.to_markdown()
    return _format_text_report(report)


def _summary_line(report: AuditReport) -> str:
    return f"Verdict: {report.verdict} | Summary: {report.summary()}"


def _write_report(path: Path, content: str) -> None:
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def _should_fail(report_verdict: str, fail_on: str, warnings_as_errors: bool) -> bool:
    threshold = fail_on
    if warnings_as_errors and VERDICT_RANK[threshold] > VERDICT_RANK[REVIEW]:
        threshold = REVIEW
    return VERDICT_RANK[report_verdict] >= VERDICT_RANK[threshold]


def _run_audit_spec(args: argparse.Namespace) -> int:
    spec = _load_json_spec(Path(args.spec_path))
    data = _load_data(args.data_path)
    report = audit_spec(spec=spec, data=data, claim=args.claim)
    selected_output = _render_report(report, args.format)
    if args.out_path:
        _write_report(Path(args.out_path), selected_output)
        print(_summary_line(report))
    else:
        print(selected_output)

    if args.markdown_path:
        _write_report(Path(args.markdown_path), report.to_markdown())

    return 1 if _should_fail(report.verdict, args.fail_on, args.warnings_as_errors) else 0


def _run_verify_report(args: argparse.Namespace) -> int:
    payload = _load_json_report(Path(args.report_path))
    if payload.get("schema_version") != BOUND_REPORT_SCHEMA_VERSION:
        raise CLIError(
            "Report must use bound report schema "
            f"{BOUND_REPORT_SCHEMA_VERSION}; got {payload.get('schema_version')!r}."
        )

    serialized_binding = payload.get("input_binding")
    if not isinstance(serialized_binding, Mapping):
        raise CLIError("Report does not contain a serialized input_binding object.")
    try:
        binding = input_binding_from_dict(serialized_binding)
    except ValueError as exc:
        raise CLIError(f"Invalid report input binding: {exc}") from exc

    if binding.subject_kind != "spec":
        raise CLIError(
            "CLI report verification currently supports saved spec-audit reports only; "
            f"report subject_kind is {binding.subject_kind!r}."
        )

    spec = _load_json_spec(Path(args.spec_path))
    data = _load_data(args.data_path)
    verification = verify_input_binding(
        binding,
        subject=spec,
        subject_kind="spec",
        data=data,
        claim=args.claim,
    )

    status = "MATCH" if verification.matches else "MISMATCH"
    print(f"Binding: {status}")
    print(f"Subject: {'MATCH' if verification.subject_matches else 'MISMATCH'}")
    print(f"Data: {'MATCH' if verification.data_matches else 'MISMATCH'}")
    print(f"Claim: {'MATCH' if verification.claim_matches else 'MISMATCH'}")
    print(f"Bound tool version: {binding.tool_version}")
    return 0 if verification.matches else 1


def _format_profile_text(manifest: ProfileManifest) -> str:
    lines = [
        f"Profile: {manifest.name}",
        f"Rules: {len(manifest.rules)}",
        "Scientific validation: false",
        "Automatic adjudication: false",
        "",
    ]
    for rule in manifest.rules:
        lines.extend(
            [
                f"{rule.rule_id} [{'/'.join(rule.severities)}]",
                f"  Applies to: {', '.join(rule.applies_to)}",
                f"  Trigger: {rule.trigger}",
                f"  Boundary: {rule.known_boundary}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _run_profile_show(args: argparse.Namespace) -> int:
    try:
        manifest = get_profile_manifest(args.profile)
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    if args.format == "json":
        print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_profile_text(manifest))
    return 0


def _format_profile_diff_text(diff: ProfileDiff) -> str:
    lines = [
        f"Profile: {diff.before_profile} -> {diff.after_profile}",
        f"Semantic profile changed: {'true' if diff.semantic_changed else 'false'}",
        f"Tool metadata changed: {'true' if diff.tool_metadata_changed else 'false'}",
        "Compatibility judgment: none",
        "Profile manifest SHA-256:",
        f"  - {diff.before_binding['profile_manifest_sha256']}",
        f"  + {diff.after_binding['profile_manifest_sha256']}",
        "",
    ]
    if diff.profile_changes:
        lines.append("Profile fields:")
        for change in diff.profile_changes:
            lines.append(f"  {change.field}")
            lines.append(f"    - {json.dumps(change.before, sort_keys=True)}")
            lines.append(f"    + {json.dumps(change.after, sort_keys=True)}")
    else:
        lines.append("Profile fields: none")

    if diff.rules_added:
        lines.append("Rules added:")
        for rule in diff.rules_added:
            lines.append(f"  {rule['id']}")
    else:
        lines.append("Rules added: none")

    if diff.rules_removed:
        lines.append("Rules removed:")
        for rule in diff.rules_removed:
            lines.append(f"  {rule['id']}")
    else:
        lines.append("Rules removed: none")

    if diff.rules_changed:
        lines.append("Rules changed:")
        for rule in diff.rules_changed:
            lines.append(f"  {rule.rule_id}")
            for change in rule.changes:
                lines.append(f"    {change.field}")
                lines.append(f"      - {json.dumps(change.before, sort_keys=True)}")
                lines.append(f"      + {json.dumps(change.after, sort_keys=True)}")
    else:
        lines.append("Rules changed: none")

    lines.append(f"Rule order changed: {'true' if diff.rule_order_changed else 'false'}")
    if diff.rule_order_changed:
        lines.append(f"  - {', '.join(diff.before_rule_order)}")
        lines.append(f"  + {', '.join(diff.after_rule_order)}")
    return "\n".join(lines)


def _run_profile_diff(args: argparse.Namespace) -> int:
    try:
        before = load_profile_manifest(args.before)
        after = load_profile_manifest(args.after)
        diff = build_profile_diff(before, after)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        raise CLIError(str(exc)) from exc
    if args.format == "json":
        print(json.dumps(diff.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_profile_diff_text(diff))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chart-contract", description="Audit Vega-Lite specs from disk.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit a chart spec from disk.")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)

    spec_parser = audit_subparsers.add_parser("spec", help="Audit a Vega-Lite spec from disk.")
    spec_parser.add_argument("spec_path", help="Path to the Vega-Lite spec file.")
    spec_parser.add_argument("--data", dest="data_path", help="Optional CSV or JSON data file.")
    spec_parser.add_argument("--claim", help="Claim to audit against the spec.")
    spec_parser.add_argument(
        "--format",
        choices=SUPPORTED_REPORT_FORMATS,
        default="text",
        help="Report format to emit.",
    )
    spec_parser.add_argument("--out", dest="out_path", help="Optional path for the primary report output.")
    spec_parser.add_argument("--markdown", dest="markdown_path", help="Optional path for a Markdown report.")
    spec_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat warnings as failures for exit-code purposes.",
    )
    spec_parser.add_argument(
        "--fail-on",
        choices=SUPPORTED_VERDICTS,
        default=BLOCK,
        help="Fail when the report verdict reaches this threshold.",
    )
    spec_parser.set_defaults(func=_run_audit_spec)

    verify_parser = subparsers.add_parser("verify", help="Verify durable audit artifacts against current inputs.")
    verify_subparsers = verify_parser.add_subparsers(dest="verify_command", required=True)
    report_parser = verify_subparsers.add_parser(
        "report",
        help="Verify a saved JSON audit report against the spec, data, and claim being shared.",
    )
    report_parser.add_argument("report_path", help="Path to a bound JSON audit report.")
    report_parser.add_argument("--spec", dest="spec_path", required=True, help="Current Vega-Lite spec file.")
    report_parser.add_argument("--data", dest="data_path", help="Optional current CSV or JSON data file.")
    report_parser.add_argument("--claim", help="Current exact claim text.")
    report_parser.set_defaults(func=_run_verify_report)

    profile_parser = subparsers.add_parser(
        "profile",
        help="Inspect and compare machine-readable audit profile metadata.",
    )
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)

    profile_show = profile_subparsers.add_parser(
        "show",
        help="Show the machine-readable rule manifest for an audit profile.",
    )
    profile_show.add_argument("profile", nargs="?", default=DEFAULT_PROFILE)
    profile_show_output = profile_show.add_mutually_exclusive_group()
    profile_show_output.add_argument("--format", choices=("text", "json"), dest="format")
    profile_show_output.add_argument("--json", action="store_const", const="json", dest="format")
    profile_show.set_defaults(format="text", func=_run_profile_show)

    profile_diff = profile_subparsers.add_parser(
        "diff",
        help="Compare two saved machine-readable audit profile manifests.",
    )
    profile_diff.add_argument("before", help="Earlier profile-manifest JSON path.")
    profile_diff.add_argument("after", help="Later profile-manifest JSON path.")
    profile_diff_output = profile_diff.add_mutually_exclusive_group()
    profile_diff_output.add_argument("--format", choices=("text", "json"), dest="format")
    profile_diff_output.add_argument("--json", action="store_const", const="json", dest="format")
    profile_diff.set_defaults(format="text", func=_run_profile_diff)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        handler = getattr(args, "func", None)
        if handler is None:
            parser.print_help()
            return 0
        return handler(args)
    except CLIError as exc:
        parser.error(str(exc))
