"""Shared subprocess helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command, printing stderr on failure."""
    result = subprocess.run(
        args, capture_output=True, check=False, text=True, cwd=cwd, timeout=120
    )
    if result.returncode != 0:
        msg = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit code {result.returncode}"
        )
        print(f"error: {args[0]}: {msg}", file=sys.stderr)
        raise SystemExit(result.returncode)
    return result
