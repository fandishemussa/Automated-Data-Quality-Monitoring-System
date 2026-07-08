"""Operational dashboard actions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SENSITIVE_TOKENS = (
    "PASSWORD",
    "TOKEN",
    "SECRET",
    "WEBHOOK",
    "API_KEY",
    "AUTH",
)


def sanitize_command_output(output: str, max_lines: int = 40) -> str:
    """Return command output with likely secret-bearing lines removed."""

    safe_lines = []
    for line in str(output or "").splitlines():
        upper_line = line.upper()
        if any(token in upper_line for token in SENSITIVE_TOKENS):
            safe_lines.append("[redacted sensitive output line]")
        else:
            safe_lines.append(line)

    if len(safe_lines) > max_lines:
        omitted = len(safe_lines) - max_lines
        safe_lines = safe_lines[-max_lines:]
        safe_lines.insert(0, f"[showing last {max_lines} lines; omitted {omitted} earlier lines]")

    return "\n".join(safe_lines).strip()


def run_checks_subprocess(
    project_root: str | Path,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Run `python main.py` safely for a dashboard-triggered check run."""

    completed = subprocess.run(
        [sys.executable, "main.py"],
        cwd=Path(project_root),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=_safe_child_environment(),
    )

    return {
        "returncode": completed.returncode,
        "stdout": sanitize_command_output(completed.stdout),
        "stderr": sanitize_command_output(completed.stderr),
        "success": completed.returncode == 0,
    }


def _safe_child_environment() -> dict[str, str]:
    """Return the inherited process environment without adding secrets."""

    return dict(os.environ)
