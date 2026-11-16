"""Command-line interface for Job Digest."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
