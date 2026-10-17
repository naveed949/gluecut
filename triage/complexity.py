"""Measure decision-module complexity (LOC) for the research write-up."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE_FILES = {
    "vega": ROOT / "engines" / "vega_engine.py",
    "llm": ROOT / "engines" / "llm_engine.py",
}
SHARED = ROOT / "contract.py"


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
    note: str

    def to_json(self) -> dict:
        return {
            "files": {k: asdict(v) for k, v in self.files.items()},
            "note": self.note,
            "delta_code_lines_llm_minus_vega": (
                self.files["llm"].code_lines - self.files["vega"].code_lines
            ),
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


def measure() -> ComplexityReport:
    files = {name: _stats(path) for name, path in ENGINE_FILES.items()}
    files["shared_contract"] = _stats(SHARED)
    return ComplexityReport(
        files=files,
        note=(
            "Compare engines/*/ code_lines: LLM glue (prompt, extract, validate, repair) "
            "vs Vega typed decide(). Shared contract is deterministic shell for both."
        ),
    )
