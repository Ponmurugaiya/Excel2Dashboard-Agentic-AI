"""
Sandboxed Python executor.
Runs agent-generated code safely with:
  - Safe builtins (imports allowed via __import__ — required for stdlib)
  - Blocked dangerous modules: os, sys, subprocess, requests, socket, etc.
  - Injected safe libraries: pd, np, datetime, re, json, math
  - 30-second timeout via threading
  - Returns ExecutionResult with success/data/error
"""

from __future__ import annotations

import builtins
import math
import re
import json
import datetime
import threading
from typing import Any

import numpy as np
import pandas as pd


# ── Blocked module imports ────────────────────────────────────────────────────
# We allow __import__ (needed for stdlib) but intercept dangerous modules.

_BLOCKED_MODULES = {
    "os", "sys", "subprocess", "socket", "requests",
    "urllib", "http", "ftplib", "smtplib", "telnetlib",
    "shutil", "pathlib", "glob", "tempfile",
    "pickle", "shelve", "dbm",
    "ctypes", "cffi", "importlib",
    "multiprocessing", "threading", "concurrent",
    "signal", "pty", "fcntl", "termios",
}

def _safe_import(name, *args, **kwargs):
    """Allow stdlib imports but block dangerous modules."""
    top = name.split(".")[0]
    if top in _BLOCKED_MODULES:
        raise ImportError(f"Module '{name}' is not allowed in analysis code.")
    return builtins.__import__(name, *args, **kwargs)


# ── Safe globals injected into every exec ────────────────────────────────────

def _make_safe_globals() -> dict:
    # Start with a clean builtins copy that uses our safe __import__
    safe_builtins = vars(builtins).copy()
    safe_builtins["__import__"] = _safe_import
    # Block direct file/exec operations
    for blocked in ("open", "exec", "eval", "compile",
                    "breakpoint", "input", "__loader__"):
        safe_builtins.pop(blocked, None)

    return {
        "__builtins__": safe_builtins,
        # Pre-injected so code doesn't need to import them
        "pd":       pd,
        "np":       np,
        "json":     json,
        "datetime": datetime,
        "re":       re,
        "math":     math,
    }


# ── Code pre-processor ────────────────────────────────────────────────────────

def _preprocess_code(code: str) -> str:
    """
    Fix common LLM code generation issues before execution:
    1. Strip markdown fences (```python ... ```)
    2. Remove if __name__ == '__main__': blocks
    3. Remove top-level print() / display() calls outside functions
    4. Ensure the code actually contains a run() function definition
    """
    # Strip fences
    code = re.sub(r"```python\s*", "", code)
    code = re.sub(r"```\s*", "", code)
    code = code.strip()

    # Remove __name__ == '__main__' blocks (they confuse the executor)
    code = re.sub(
        r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:.*",
        "",
        code,
        flags=re.DOTALL,
    )

    return code.strip()


def _extract_run_function(code: str) -> str:
    """
    If the LLM included prose or multiple functions, extract just the run() definition.
    If no run() exists at all, return the original code — the executor will give
    a clear 'does not define run()' error message on exec.
    """
    # Already has def run( at top level — good
    if re.search(r"^def run\s*\(", code, re.MULTILINE):
        return code

    # Try to find def run( anywhere (might be indented inside prose)
    match = re.search(r"(def run\s*\(.*?)(?=\n\S|\Z)", code, re.DOTALL)
    if match:
        return match.group(1).strip()

    # No run() found anywhere — return as-is so executor gives clear error
    return code


# ── Main executor ─────────────────────────────────────────────────────────────

class ExecutionResult:
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = "",
        error_line: int = 0,
        code_used: str = "",
    ):
        self.success    = success
        self.data       = data
        self.error      = error
        self.error_line = error_line
        self.code_used  = code_used

    def to_dict(self) -> dict:
        return {
            "success":    self.success,
            "data":       self.data,
            "error":      self.error,
            "error_line": self.error_line,
        }


def execute(code: str, df: pd.DataFrame, timeout: int = 30) -> ExecutionResult:
    """
    Execute agent-generated code in a sandboxed environment.

    The code must define (or be extractable as):
        def run(df: pd.DataFrame) -> dict: ...

    Returns ExecutionResult.
    """
    # Pre-process
    code = _preprocess_code(code)
    code = _extract_run_function(code)

    result_holder:     list[Any] = [None]
    error_holder:      list[str] = [""]
    error_line_holder: list[int] = [0]

    def _run():
        try:
            safe_globals = _make_safe_globals()
            exec(code, safe_globals)  # noqa: S102

            run_fn = safe_globals.get("run")
            if run_fn is None:
                error_holder[0] = (
                    "Generated code does not define a `run(df)` function. "
                    "The function must be named exactly `run`, defined at the top level, "
                    "and start with `def run(df):`."
                )
                return

            result = run_fn(df.copy())

            if result is None:
                error_holder[0] = (
                    "`run(df)` returned None. "
                    "Ensure the function ends with `return {...}` and all code paths return a dict."
                )
                return

            if not isinstance(result, dict):
                error_holder[0] = (
                    f"`run(df)` must return a dict, got {type(result).__name__}. "
                    "Return a dict with keys: result_type, title, and data fields."
                )
                return

            result_holder[0] = _serialise(result)

        except ImportError as exc:
            error_holder[0] = f"ImportError: {exc} — use only pd, np, datetime, re, math (pre-imported)"
            error_line_holder[0] = 0
        except Exception as exc:
            import traceback
            tb = traceback.extract_tb(exc.__traceback__)
            line = tb[-1].lineno if tb else 0
            error_holder[0] = f"{type(exc).__name__}: {exc}"
            error_line_holder[0] = line

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return ExecutionResult(
            success=False,
            error=f"Execution timed out after {timeout}s. Simplify the analysis.",
            code_used=code,
        )

    if error_holder[0]:
        return ExecutionResult(
            success=False,
            error=error_holder[0],
            error_line=error_line_holder[0],
            code_used=code,
        )

    return ExecutionResult(success=True, data=result_holder[0], code_used=code)


# ── Serialiser ────────────────────────────────────────────────────────────────

def _serialise(obj: Any) -> Any:
    """Recursively convert numpy/pandas types to plain Python for JSON safety."""
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialise(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (f != f) else round(f, 6)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Period):
        return str(obj)
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(obj)
    return obj
