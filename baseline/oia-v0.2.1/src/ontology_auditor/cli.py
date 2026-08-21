"""Command-line interface for ontology-intervention-auditor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .io import audit_payload, load_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ontology-auditor",
        description=(
            "Audit whether finite executable ontology candidates can be separated "
            "by permitted interventions and whether the distinction affects decisions."
        ),
    )
    parser.add_argument("input", type=Path, help="JSON audit instance")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write JSON report to this path instead of stdout",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_payload(load_payload(args.input))
    except Exception as exc:  # CLI boundary: render validation failures cleanly.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=args.indent, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
