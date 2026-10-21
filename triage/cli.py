"""CLI entrypoint for the LLM-vs-System-One research harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from triage.bench import DEFAULT_BENCH_MD, DEFAULT_FIXTURES as BENCH_FIXTURES
from triage.bench import rows_to_json, run_bench, write_bench
from triage.complexity import measure
from triage.contract import EngineName, Ticket
from triage.engines import get_engine
from triage.eval import DEFAULT_FIXTURES, run_eval
from triage.payments import eval_payments
from triage.report import DEFAULT_ENGINES, DEFAULT_HTML, DEFAULT_MD, run_compare
from triage.shadow import DEFAULT_SHADOW_MD, run_shadow, write_shadow

ENGINE_CHOICES = ("vega", "llm", "llm_structured", "llm_schema")


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
    print(result.md_path)
    print(result.html_path)
    return 0


def cmd_shadow(args: argparse.Namespace) -> int:
    engines = tuple(args.engines or ("vega", "llm_schema"))
    fixtures = Path(args.fixtures) if args.fixtures else DEFAULT_FIXTURES
    out = Path(args.out) if args.out else DEFAULT_SHADOW_MD
    report = run_shadow(
        engines=engines,  # type: ignore[arg-type]
        fixtures_path=fixtures,
        limit=args.limit,
    )
    path = write_shadow(report, out)
    print(path)
    print(json.dumps({k: report.per_engine[k] for k in report.engines}, indent=2))
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    engines = tuple(args.engines or ("vega", "llm_schema"))
    fixtures = Path(args.fixtures) if args.fixtures else BENCH_FIXTURES
    rows = run_bench(
        engines=engines,  # type: ignore[arg-type]
        fixtures_path=fixtures,
        limit=args.limit,
        target_qps=args.qps,
    )
    out = Path(args.out) if args.out else DEFAULT_BENCH_MD
    write_bench(rows, out)
    print(out)
    print(json.dumps(rows_to_json(rows), indent=2))
    return 0


def cmd_payments_eval(args: argparse.Namespace) -> int:
    path = Path(args.fixtures) if args.fixtures else None
    print(json.dumps(eval_payments(args.engine, path), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="triage",
        description=(
            "Research CLI: System One vs LLM glue — triage + payments domains."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="Triage one ticket")
    d.add_argument("--engine", choices=ENGINE_CHOICES, required=True)
    d.add_argument("--text", help="Ticket body")
    d.add_argument("--file", help="Read ticket body from file")
    d.add_argument("--subject", default="", help="Optional subject")
    d.set_defaults(func=cmd_decide)

    e = sub.add_parser("eval", help="Score triage fixtures")
    e.add_argument("--engine", choices=ENGINE_CHOICES, required=True)
    e.add_argument("--fixtures", help="JSONL path (default: held_out)")
    e.add_argument("--verbose", action="store_true")
    e.set_defaults(func=cmd_eval)

    c = sub.add_parser("complexity", help="LOC / fair glue breakdown")
    c.set_defaults(func=cmd_complexity)

    cmp_ = sub.add_parser("compare", help="Write research/report.md (+ html)")
    cmp_.add_argument("--fixtures")
    cmp_.add_argument("--engines", nargs="+", choices=ENGINE_CHOICES)
    cmp_.add_argument("--out")
    cmp_.add_argument("--html")
    cmp_.set_defaults(func=cmd_compare)

    sh = sub.add_parser(
        "shadow",
        help="Same fixtures through engines → disagreements.md + $ summary",
    )
    sh.add_argument("--fixtures")
    sh.add_argument("--engines", nargs="+", choices=ENGINE_CHOICES)
    sh.add_argument("--limit", type=int, help="Optional cap for smoke runs")
    sh.add_argument("--out", help=f"default {DEFAULT_SHADOW_MD}")
    sh.set_defaults(func=cmd_shadow)

    b = sub.add_parser("bench", help="Paced QPS cost/latency table → bench.md")
    b.add_argument("--fixtures")
    b.add_argument("--engines", nargs="+", choices=ENGINE_CHOICES)
    b.add_argument("--limit", type=int, default=30)
    b.add_argument("--qps", type=float, default=1.0)
    b.add_argument("--out", help=f"default {DEFAULT_BENCH_MD}")
    b.set_defaults(func=cmd_bench)

    pe = sub.add_parser("payments-eval", help="Second domain: payment failure → reason")
    pe.add_argument("--engine", choices=("vega", "llm_schema"), required=True)
    pe.add_argument("--fixtures")
    pe.set_defaults(func=cmd_payments_eval)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
