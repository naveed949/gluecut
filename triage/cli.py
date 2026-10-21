"""CLI entrypoint for the LLM-vs-System-One triage research."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from triage.complexity import measure
from triage.contract import EngineName, Ticket
from triage.engines import get_engine
from triage.eval import DEFAULT_FIXTURES, run_eval
from triage.report import DEFAULT_ENGINES, DEFAULT_HTML, DEFAULT_MD, run_compare


def _read_body(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file is not None:
        return Path(args.file).read_text()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --text, --file, or pipe the ticket on stdin.")


def cmd_decide(args: argparse.Namespace) -> int:
    body = _read_body(args).strip()
    if not body:
        raise SystemExit("Empty ticket body.")
    engine = get_engine(args.engine)
    decision = engine.triage(Ticket(body=body, subject=args.subject or ""))
    print(json.dumps(decision.to_json(), indent=2, default=str))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    path = Path(args.fixtures) if args.fixtures else DEFAULT_FIXTURES
    report = run_eval(args.engine, path)
    payload = report.to_json()
    if not args.verbose:
        payload.pop("cases", None)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_complexity(_: argparse.Namespace) -> int:
    print(json.dumps(measure().to_json(), indent=2))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    engines: tuple[EngineName, ...]
    if args.engines:
        engines = tuple(args.engines)  # type: ignore[assignment]
    else:
        engines = DEFAULT_ENGINES
    fixtures = Path(args.fixtures) if args.fixtures else DEFAULT_FIXTURES
    md_path = Path(args.out) if args.out else DEFAULT_MD
    html_path = Path(args.html) if args.html else DEFAULT_HTML
    result = run_compare(
        engines=engines,
        fixtures=fixtures,
        md_path=md_path,
        html_path=html_path,
    )
    # Boring CLI: paths only. The report files are the shareable artifact.
    print(result.md_path)
    print(result.html_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="triage",
        description=(
            "Research CLI: compare LLM prompt/parse glue vs Vega System One "
            "for support-ticket triage."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="Triage one ticket")
    d.add_argument(
        "--engine",
        choices=("vega", "llm", "llm_structured"),
        required=True,
    )
    d.add_argument("--text", help="Ticket body")
    d.add_argument("--file", help="Read ticket body from file")
    d.add_argument("--subject", default="", help="Optional subject")
    d.set_defaults(func=cmd_decide)

    e = sub.add_parser("eval", help="Score an engine on fixtures/tickets.jsonl")
    e.add_argument(
        "--engine",
        choices=("vega", "llm", "llm_structured"),
        required=True,
    )
    e.add_argument("--fixtures", help="JSONL path (default: fixtures/tickets.jsonl)")
    e.add_argument("--verbose", action="store_true", help="Include per-case rows")
    e.set_defaults(func=cmd_eval)

    c = sub.add_parser("complexity", help="Print LOC stats for each engine module")
    c.set_defaults(func=cmd_complexity)

    cmp_ = sub.add_parser(
        "compare",
        help="Run complexity + eval; write research/report.md and report.html",
    )
    cmp_.add_argument(
        "--fixtures",
        help="JSONL path (default: fixtures/tickets.jsonl)",
    )
    cmp_.add_argument(
        "--engines",
        nargs="+",
        choices=("vega", "llm", "llm_structured"),
        help="Engines to include (default: vega llm llm_structured)",
    )
    cmp_.add_argument(
        "--out",
        help=f"Markdown output path (default: {DEFAULT_MD})",
    )
    cmp_.add_argument(
        "--html",
        help=f"HTML output path (default: {DEFAULT_HTML})",
    )
    cmp_.set_defaults(func=cmd_compare)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
