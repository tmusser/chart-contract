"""Command-line entry points for chart_contract."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Sequence

SUPPORTED_REPORT_FORMATS = ("text", "json", "markdown")
SUPPORTED_VERDICTS = ("READY", "REVIEW", "BLOCK")


def _package_version() -> str:
    try:
        return package_version("chart-contract")
    except PackageNotFoundError:
        return "0.1.0"


def _run_audit_spec(args: argparse.Namespace) -> int:
    # Verdict names keep the CLI aligned with AuditReport.verdict and avoid an extra
    # severity-to-verdict translation layer until the real audit execution lands.
    _ = args
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
        default="BLOCK",
        help="Fail when the report verdict reaches this threshold.",
    )
    spec_parser.set_defaults(func=_run_audit_spec)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
