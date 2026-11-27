"""
AST-Based Static Code Reviewer (`tools/code_review_tool.py`)
- Uses Python `ast` to detect dangerous calls (`eval`, `exec`, `compile`, `__import__`, `getattr`),
  dangerous imports (`os`, `subprocess`, `shutil`, `socket`, `ctypes`, `pickle`, `importlib`),
  and case-insensitive SQL/shell patterns (`DROP TABLE`, `rm -rf`).
- Pair with `bandit` in CI for full SAST coverage.
"""

from __future__ import annotations

import ast
from typing import Any

DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "getattr", "setattr", "delattr"}
DANGEROUS_MODULES = {"os", "subprocess", "shutil", "socket", "ctypes", "pickle", "importlib"}
DANGEROUS_DUNDERS = {
    "__subclasses__", "__bases__", "__globals__",
    "__builtins__", "__class__", "__mro__", "__code__",
}
DANGEROUS_TEXT_PATTERNS = [
    ("drop table", "Database Safety: DROP TABLE detected."),
    ("rm -rf", "System Safety: destructive rm -rf detected."),
]


def _is_open_write_call(node: ast.Call) -> bool:
    is_open = isinstance(node.func, ast.Name) and node.func.id == "open"
    if (
        not is_open
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"builtins", "io"}
    ):
        is_open = True
    if not is_open:
        return False
    mode_arg: ast.expr | None = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "mode":
            mode_arg = kw.value
    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        return any(ch in mode_arg.value for ch in ("w", "a", "x", "+"))
    return False


def code_review(code_text: str) -> dict[str, Any]:
    issues: list[str] = []
    lowered = code_text.lower()
    for pat, msg in DANGEROUS_TEXT_PATTERNS:
        if pat in lowered:
            issues.append(msg)

    try:
        tree = ast.parse(code_text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in DANGEROUS_MODULES:
                        issues.append(f"AST Check: dangerous import '{alias.name}'.")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in DANGEROUS_MODULES:
                    issues.append(f"AST Check: dangerous from-import '{node.module}'.")
            elif isinstance(node, ast.Attribute) and node.attr in DANGEROUS_DUNDERS:
                issues.append(f"AST Check: dangerous dunder attribute '.{node.attr}'.")
            elif isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                    issues.append("AST Check: subscripting '__builtins__' is blocked.")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                    issues.append(f"AST Check: dangerous call '{node.func.id}()'.")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in DANGEROUS_CALLS:
                    issues.append(f"AST Check: dangerous attribute call '.{node.func.attr}()'.")
                elif _is_open_write_call(node):
                    issues.append("AST Check: file write via open() is blocked.")
    except SyntaxError as exc:
        issues.append(f"AST SyntaxError: {exc.msg}")

    return {
        "review_type": "ast_static_and_pattern_check",
        "approved": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }
