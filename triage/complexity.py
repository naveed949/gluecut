"""Measure decision-module complexity with a fair glue breakdown.

Critics often say HTTP clients inflate LOC. This report splits:
- http_client / offline_simulator (transport & test doubles)
- parse_repair (fence scraping, embedded JSON recovery)
- core_triage (prompt loop, validate, confidence → action)
- prompts (character counts in contract, not LOC)
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path

from triage.contract import LLM_REPAIR_PROMPT, LLM_SYSTEM_PROMPT, VEGA_QUESTIONS

ROOT = Path(__file__).resolve().parent
ENGINE_FILES = {
    "vega": ROOT / "engines" / "vega_engine.py",
    "llm": ROOT / "engines" / "llm_engine.py",
    "llm_structured": ROOT / "engines" / "llm_structured_engine.py",
    "llm_client": ROOT / "engines" / "llm_client.py",
    "llm_parse": ROOT / "engines" / "llm_parse.py",
}
SHARED = ROOT / "contract.py"

# Top-level defs → bucket for fair comparison.
_BUCKET_BY_QUALNAME = {
    "triage/engines/llm_client.py::OpenAICompatClient": "http_client",
    "triage/engines/llm_client.py::build_client": "http_client",
    "triage/engines/llm_client.py::SimulatedJsonLlm": "offline_simulator",
    "triage/engines/llm_client.py::ChatClient": "http_client",
    "triage/engines/llm_parse.py::extract_json_object": "parse_repair",
    "triage/engines/llm_engine.py::LlmTriageEngine": "core_triage",
    "triage/engines/llm_structured_engine.py::LlmStructuredTriageEngine": "core_triage",
    "triage/engines/vega_engine.py::VegaTriageEngine": "core_triage",
    "triage/engines/vega_engine.py::_load_model": "core_triage",
}


@dataclass
class FileStats:
    path: str
    total_lines: int
    code_lines: int
    comment_or_blank: int
    functions: int
    classes: int


@dataclass
class ComplexityReport:
    files: dict[str, FileStats]
    buckets: dict[str, int]
    prompt_chars: dict[str, int]
    fair_deltas: dict[str, int]
    note: str
    extras: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "files": {k: asdict(v) for k, v in self.files.items()},
            "buckets": self.buckets,
            "prompt_chars": self.prompt_chars,
            "fair_deltas": self.fair_deltas,
            "note": self.note,
            "delta_code_lines_llm_minus_vega": (
                self.files["llm"].code_lines
                + self.files["llm_client"].code_lines
                + self.files["llm_parse"].code_lines
                - self.files["vega"].code_lines
            ),
            **self.extras,
        }


def _stats(path: Path) -> FileStats:
    text = path.read_text()
    lines = text.splitlines()
    code = 0
    other = 0
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            other += 1
        else:
            code += 1
    tree = ast.parse(text)
    funcs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    return FileStats(
        path=str(path.relative_to(ROOT.parent)),
        total_lines=len(lines),
        code_lines=code,
        comment_or_blank=other,
        functions=funcs,
        classes=classes,
    )


def _code_lines_in_span(lines: list[str], start: int, end: int) -> int:
    """1-based inclusive line span from ast lineno/end_lineno."""
    n = 0
    for i in range(start - 1, min(end, len(lines))):
        s = lines[i].strip()
        if s and not s.startswith("#"):
            n += 1
    return n


def _bucket_loc(path: Path) -> dict[str, int]:
    rel = str(path.relative_to(ROOT.parent))
    text = path.read_text()
    lines = text.splitlines()
    tree = ast.parse(text)
    out: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            key = f"{rel}::{node.name}"
            bucket = _BUCKET_BY_QUALNAME.get(key, "other")
            end = getattr(node, "end_lineno", None) or node.lineno
            out[bucket] = out.get(bucket, 0) + _code_lines_in_span(lines, node.lineno, end)
    return out


def _criteria_chars() -> int:
    n = 0
    for q in VEGA_QUESTIONS.values():
        n += len(q.get("instructions", ""))
        for v in q.get("criteria", {}).values():
            n += len(str(v))
    return n


def measure() -> ComplexityReport:
    files = {name: _stats(path) for name, path in ENGINE_FILES.items()}
    files["shared_contract"] = _stats(SHARED)

    buckets: dict[str, int] = {}
    for path in ENGINE_FILES.values():
        for bucket, n in _bucket_loc(path).items():
            buckets[bucket] = buckets.get(bucket, 0) + n

    # Semantic decision code only (exclude HTTP + offline simulator).
    vega_only = _bucket_loc(ENGINE_FILES["vega"]).get("core_triage", 0)
    llm_freeform_core = _bucket_loc(ENGINE_FILES["llm"]).get("core_triage", 0)
    llm_structured_core = _bucket_loc(ENGINE_FILES["llm_structured"]).get("core_triage", 0)
    parse_repair = buckets.get("parse_repair", 0)
    http_client = buckets.get("http_client", 0)
    offline_sim = buckets.get("offline_simulator", 0)

    prompt_chars = {
        "llm_system_prompt": len(LLM_SYSTEM_PROMPT),
        "llm_repair_prompt": len(LLM_REPAIR_PROMPT),
        "vega_criteria_and_instructions": _criteria_chars(),
    }

    fair_deltas = {
        # Freeform LLM semantic glue vs Vega core (no HTTP, no simulator).
        "llm_freeform_semantic_minus_vega": (
            llm_freeform_core + parse_repair - vega_only
        ),
        # Structured JSON-mode still needs core triage; no parse_repair module.
        "llm_structured_semantic_minus_vega": (llm_structured_core - vega_only),
        # What critics attribute to "just HTTP":
        "http_client_code_lines": http_client,
        "offline_simulator_code_lines": offline_sim,
        "parse_repair_code_lines": parse_repair,
    }

    return ComplexityReport(
        files=files,
        buckets=buckets,
        prompt_chars=prompt_chars,
        fair_deltas=fair_deltas,
        note=(
            "fair_deltas.*_semantic_minus_vega exclude http_client and offline_simulator. "
            "Freeform still pays parse_repair; llm_structured shrinks that but keeps "
            "prompt + json.loads + schema validate + confidence policy."
        ),
        extras={
            "core_triage_by_engine": {
                "vega": vega_only,
                "llm": llm_freeform_core,
                "llm_structured": llm_structured_core,
            },
        },
    )
