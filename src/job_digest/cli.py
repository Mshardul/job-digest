"""Command-line interface for Job Digest."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from job_digest.config.profile import validate_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-digest", description="Job Digest")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the full daily pipeline")
    subparsers.add_parser(
        "dry-run",
        help="Run everything except sending; prints the email with scores",
    )
    subparsers.add_parser("validate-profile", help="Check the profile for errors")
    return parser


def _cmd_validate_profile() -> int:
    errors, warnings = validate_profile()
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    for error in errors:
        print(f"Error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Profile is valid.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate-profile":
        return _cmd_validate_profile()
    return 0
