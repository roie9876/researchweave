"""Isolated code execution sandbox and safety guardrails for ResearchWeave.

Enforces:
- Mandatory safety and legality guardrails on prompts, objectives, and agent actions.
- Isolated subprocess execution with strict timeout, stripped credentials/environment,
  temporary working directory, and forbidden dangerous module/syscall inspection.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ILLEGAL_OR_UNSAFE_PATTERNS = (
    "ransomware",
    "exploit target",
    "ddos",
    "steal credentials",
    "exfiltrate password",
    "bypass authentication",
    "synthesize pathogen",
    "bioweapon",
    "chemical weapon",
    "unauthorized intrusion",
)

FORBIDDEN_PYTHON_IMPORTS = {
    "socket",
    "subprocess",
    "shutil",
    "ctypes",
    "multiprocessing",
    "pty",
    "resource",
}


def check_guardrails(text: str) -> tuple[bool, str]:
    """Validate that an objective, prompt, or instruction does not violate safety/legality guardrails."""
    lowered = text.lower()
    for pat in ILLEGAL_OR_UNSAFE_PATTERNS:
        if pat in lowered:
            return (
                False,
                f"Blocked by ResearchWeave Guardrail: prohibited or unlawful research request matching '{pat}'.",
            )
    return True, "ok"


def validate_python_code_safety(code: str) -> tuple[bool, str]:
    """Statically inspect generated Python analysis code before execution in the isolated workspace."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError in generated code: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in FORBIDDEN_PYTHON_IMPORTS:
                    return False, f"Import of '{root_mod}' is restricted inside the isolated research sandbox."
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_mod = node.module.split(".")[0]
                if root_mod in FORBIDDEN_PYTHON_IMPORTS:
                    return False, f"Import from '{root_mod}' is restricted inside the isolated research sandbox."
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "__import__", "open"}:
                return False, f"Call to '{node.func.id}()' is restricted inside the isolated research sandbox."

    return True, "ok"


def execute_in_isolated_sandbox(
    code: str,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Execute validated scientific/computational Python code in an isolated directory with stripped env."""
    is_safe, reason = validate_python_code_safety(code)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": reason,
            "exit_code": -1,
            "blocked_by_guardrail": True,
        }

    with tempfile.TemporaryDirectory(prefix="rw-sandbox-") as tmpdir:
        script_path = Path(tmpdir) / "analysis_job.py"
        script_path.write_text(code, encoding="utf-8")

        safe_env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": tmpdir,
        }

        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=tmpdir,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "exit_code": proc.returncode,
                "blocked_by_guardrail": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox execution timed out after {timeout_seconds}s.",
                "exit_code": -2,
                "blocked_by_guardrail": False,
            }
