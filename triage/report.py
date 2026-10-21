"""Build the shareable compare report (Markdown + tiny HTML)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from triage.complexity import ComplexityReport, measure
from triage.contract import EngineName
from triage.eval import DEFAULT_FIXTURES, EvalReport, run_eval

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MD = REPO_ROOT / "research" / "report.md"
DEFAULT_HTML = REPO_ROOT / "research" / "report.html"

DEFAULT_ENGINES: tuple[EngineName, ...] = ("vega", "llm_schema", "llm_structured")


@dataclass
class CompareResult:
    complexity: dict[str, Any]
    evals: dict[str, dict[str, Any]]
    markdown: str
    html_doc: str
    md_path: Path
    html_path: Path


def _pct(x: float) -> str:
    return f"{100.0 * x:.1f}%"


def _semantic_loc(engine: str, complexity: dict[str, Any]) -> str:
    core = complexity.get("core_triage_by_engine", {})
    fair = complexity.get("fair_deltas", {})
    if engine == "vega":
        return str(core.get("vega", "—"))
    if engine == "llm":
        return str(core.get("llm", 0) + fair.get("parse_repair_code_lines", 0))
    if engine == "llm_structured":
        return str(core.get("llm_structured", "—"))
    if engine == "llm_schema":
        return str(core.get("llm_schema", "—"))
    return "—"


def _fair_delta(engine: str, complexity: dict[str, Any]) -> str:
    fair = complexity.get("fair_deltas", {})
    if engine == "vega":
        return "0"
    if engine == "llm":
        return f"+{fair.get('llm_freeform_semantic_minus_vega', '—')}"
    if engine == "llm_structured":
        return f"+{fair.get('llm_structured_semantic_minus_vega', '—')}"
    if engine == "llm_schema":
        return f"+{fair.get('llm_schema_semantic_minus_vega', '—')}"
    return "—"


def render_markdown(
    *,
    complexity: dict[str, Any],
    evals: dict[str, dict[str, Any]],
    engines: Sequence[str],
    fixtures: str,
    generated_at: str,
) -> str:
    cols = list(engines)
    header = "| Metric | " + " | ".join(cols) + " |"
    sep = "|--------|" + "|".join(["--------"] * len(cols)) + "|"

    def row(label: str, values: list[str]) -> str:
        return "| " + label + " | " + " | ".join(values) + " |"

    metric_rows = [
        row("Semantic LOC (fair)", [_semantic_loc(e, complexity) for e in cols]),
        row("Fair delta vs Vega", [_fair_delta(e, complexity) for e in cols]),
    ]
    keys = [
        ("team_accuracy", "Team accuracy", _pct),
        ("priority_accuracy", "Priority accuracy", _pct),
        ("needs_human_accuracy", "Needs-human accuracy", _pct),
        ("forced_wrong_team_rate", "Forced-wrong team", _pct),
        ("needs_review_rate", "Needs-review rate", _pct),
        ("abstain_rate", "Abstain rate", _pct),
        ("mean_parse_attempts", "Mean parse attempts", lambda x: f"{x:.2f}"),
        ("mean_repair_rounds", "Mean repair rounds", lambda x: f"{x:.2f}"),
    ]
    for key, label, fmt in keys:
        metric_rows.append(
            row(label, [fmt(float(evals[e][key])) for e in cols])
        )

    n_scored = next(iter(evals.values())).get("n_scored", "?")
    n = next(iter(evals.values())).get("n", "?")
    client_note = ""
    for ev in evals.values():
        for case in ev.get("cases") or []:
            c = (case.get("orchestration") or {}).get("client")
            if c:
                client_note = c
                break
        if client_note:
            break

    fair = complexity.get("fair_deltas", {})
    prompts = complexity.get("prompt_chars", {})

    lines = [
        "# gluecut compare report",
        "",
        f"Generated: `{generated_at}`",
        "",
        f"Fixtures: `{fixtures}` (n={n}, n_scored={n_scored})",
        "",
        (
            f"LLM client label (if present): `{client_note or 'n/a'}` "
            "(set `OPENAI_API_KEY` for live models; otherwise simulated)."
        ),
        "",
        "## Head-to-head",
        "",
        header,
        sep,
        *metric_rows,
        "",
        "## Fair complexity notes",
        "",
        "- Semantic LOC excludes `http_client` and `offline_simulator`.",
        f"- Freeform still pays `parse_repair` ({fair.get('parse_repair_code_lines', '—')} LOC).",
        f"- HTTP client called out separately: {fair.get('http_client_code_lines', '—')} LOC "
        "(not in semantic delta).",
        f"- Prompt chars — LLM system: {prompts.get('llm_system_prompt', '—')}; "
        f"Vega criteria: {prompts.get('vega_criteria_and_instructions', '—')}.",
        "",
        "## Reading for LLM engineers",
        "",
        "- **Team accuracy** answers “who got the label right?”",
        "- **Forced-wrong** answers “who auto-routed a wrong team?”",
        "- **Fair delta vs Vega** is the glue claim after removing HTTP inflation.",
        "- JSON mode (`llm_structured`) shrinks freeform glue; it does not remove "
        "prompt + validate + confidence policy.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "uv run python -m triage compare",
        "# or",
        f"uv run python -m triage compare --fixtures {fixtures}",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_html(markdown_table_section: str, *, title: str = "gluecut compare") -> str:
    """Minimal standalone HTML: title + preformatted markdown body is fine;

    Prefer a real HTML table parsed from the compare metrics for sharing.
    """
    # Caller passes full markdown; we also accept building from structured data.
    body = html.escape(markdown_table_section)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f6f4ef;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #d6d3d1;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: linear-gradient(160deg, #e7e5e4 0%, var(--bg) 40%, #ecfdf5 100%);
      color: var(--ink);
      line-height: 1.5;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      padding: 2.5rem 1.25rem 4rem;
    }}
    h1 {{
      font-family: "IBM Plex Serif", Georgia, serif;
      font-weight: 600;
      font-size: 2rem;
      margin: 0 0 0.25rem;
      letter-spacing: -0.02em;
    }}
    .sub {{ color: var(--muted); margin-bottom: 1.75rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,0.72);
      backdrop-filter: blur(6px);
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 0.65rem 0.75rem;
      text-align: left;
      font-variant-numeric: tabular-nums;
    }}
    th {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
    tr:first-child th {{ border-top: 2px solid var(--accent); }}
    td:first-child {{ font-weight: 600; }}
    .notes {{
      margin-top: 1.75rem;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    code {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.9em; }}
  </style>
</head>
<body>
  <main>
    <h1>gluecut</h1>
    <p class="sub">System One vs LLM glue — compare report</p>
    <!-- markdown mirror for copy/paste; table injected below -->
    <div id="report"></div>
    <pre id="md" style="display:none">{body}</pre>
    <script>
      // Render the markdown head-to-head table into HTML.
      const md = document.getElementById('md').textContent;
      const lines = md.split('\\n');
      const start = lines.findIndex(l => l.startsWith('| Metric |'));
      const tableLines = [];
      if (start >= 0) {{
        for (let i = start; i < lines.length; i++) {{
          if (!lines[i].startsWith('|')) break;
          if (lines[i].includes('---')) continue;
          tableLines.push(lines[i]);
        }}
      }}
      function cells(line) {{
        return line.split('|').slice(1, -1).map(s => s.trim());
      }}
      let html = '<table><thead><tr>';
      if (tableLines.length) {{
        cells(tableLines[0]).forEach(c => {{ html += '<th>' + c + '</th>'; }});
        html += '</tr></thead><tbody>';
        tableLines.slice(1).forEach(line => {{
          html += '<tr>';
          cells(line).forEach(c => {{ html += '<td>' + c + '</td>'; }});
          html += '</tr>';
        }});
        html += '</tbody></table>';
      }}
      const gen = (md.match(/Generated: `([^`]+)`/) || [])[1] || '';
      const fix = (md.match(/Fixtures: `([^`]+)`[^\\n]*/ ) || [])[0] || '';
      document.getElementById('report').innerHTML =
        '<p class="sub">' + (gen ? ('Generated ' + gen + '. ') : '') + fix + '</p>' +
        html +
        '<div class="notes"><p>Share <code>research/report.md</code> or this HTML. ' +
        'CLI: <code>uv run python -m triage compare</code></p></div>';
    </script>
  </main>
</body>
</html>
"""


def run_compare(
    *,
    engines: Sequence[EngineName] = DEFAULT_ENGINES,
    fixtures: Path | None = None,
    md_path: Path | None = None,
    html_path: Path | None = None,
) -> CompareResult:
    fixtures = fixtures or DEFAULT_FIXTURES
    md_path = md_path or DEFAULT_MD
    html_path = html_path or DEFAULT_HTML

    complexity_report: ComplexityReport = measure()
    complexity = complexity_report.to_json()

    evals: dict[str, dict[str, Any]] = {}
    for name in engines:
        report: EvalReport = run_eval(name, fixtures)
        payload = report.to_json()
        # Keep cases for client label detection; strip later for smaller md if needed.
        evals[name] = payload

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    markdown = render_markdown(
        complexity=complexity,
        evals=evals,
        engines=engines,
        fixtures=str(fixtures.relative_to(REPO_ROOT) if fixtures.is_relative_to(REPO_ROOT) else fixtures),
        generated_at=generated_at,
    )
    html_doc = render_html(markdown)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown)
    html_path.write_text(html_doc)

    return CompareResult(
        complexity=complexity,
        evals=evals,
        markdown=markdown,
        html_doc=html_doc,
        md_path=md_path,
        html_path=html_path,
    )
