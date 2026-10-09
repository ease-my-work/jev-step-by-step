"""Lesson files must stay about JEV and the LLM only. Plumbing belongs in kit/ (see plan section 5)."""

import ast
import re
from pathlib import Path

import pytest

STEPS_DIR = Path(__file__).resolve().parent.parent / "steps"
STEP_DIRS = sorted(p for p in STEPS_DIR.glob("step*") if p.is_dir())
LESSON_FILES = sorted(f for d in STEP_DIRS for f in d.glob("*.py") if f.name != "run.py")

FORBIDDEN_IMPORTS = {"rich", "questionary", "argparse", "time", "threading", "sys", "logging", "prompt_toolkit"}
MAX_LINES = 80  # jev.py / llm_only.py in steps 01–09


def _imports(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _step_number(path: Path) -> int:
    return int(re.match(r"step(\d+)", path.parent.name).group(1))


def test_there_is_at_least_one_step():
    assert STEP_DIRS


@pytest.mark.parametrize("step_dir", STEP_DIRS, ids=lambda p: p.name)
def test_every_step_has_the_standard_files(step_dir):
    for name in ("jev.py", "llm_only.py", "run.py", "README.md"):
        assert (step_dir / name).exists(), f"{step_dir.name} is missing {name}"


@pytest.mark.parametrize("path", LESSON_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_lesson_files_import_no_plumbing(path):
    bad = _imports(ast.parse(path.read_text(encoding="utf-8"))) & FORBIDDEN_IMPORTS
    assert not bad, f"{path.name} imports {bad} — move that into kit/"


@pytest.mark.parametrize("path", LESSON_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_lesson_files_have_no_print_or_try(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Try), f"{path.name}:{node.lineno} has try/except — plumbing belongs in kit/"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "print", f"{path.name}:{node.lineno} prints — the UI lives in kit/"


@pytest.mark.parametrize("path", LESSON_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_lesson_files_start_with_the_three_line_header(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(f"# Step {_step_number(path):02d} — ")
    assert lines[1].startswith("# Compare with:")
    assert "kit/ is plumbing" in lines[2]


@pytest.mark.parametrize(
    "path", [p for p in LESSON_FILES if _step_number(p) <= 9], ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_lesson_files_stay_short(path):
    assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_LINES


@pytest.mark.parametrize("step_dir", STEP_DIRS, ids=lambda p: p.name)
def test_lessons_expose_run_with_one_argument(step_dir):
    for name in ("jev.py", "llm_only.py"):
        tree = ast.parse((step_dir / name).read_text(encoding="utf-8"))
        runs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
        assert runs and len(runs[0].args.args) == 1, f"{step_dir.name}/{name} needs `def run(query):`"


@pytest.mark.parametrize("step_dir", STEP_DIRS, ids=lambda p: p.name)
def test_run_py_is_tiny_and_calls_run_step(step_dir):
    text = (step_dir / "run.py").read_text(encoding="utf-8")
    assert len([line for line in text.splitlines() if line.strip()]) <= 5
    assert "kit.run_step(" in text or "kit.run_benchmark(" in text
    assert f'"{_step_number(step_dir / "run.py"):02d} ' in text
