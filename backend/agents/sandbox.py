"""
Sandboxed Python executor.
Runs agent-generated code safely:
  - Blocks dangerous builtins (os, sys, open, subprocess, requests, etc.)
  - Injects only safe libraries (pandas, numpy, datetime, re, json, math)
  - 30-second timeout via threading
  - Returns result dict or structured error
"""

from __future__ import annotations

import math
import re
import json
import datetime
import threading
from typing import Any

import numpy as np
import pandas as pd


# ── Blocked builtins ──────────────────────────────────────────────────────────

_BLOCKED = {
    "open", "exec", "eval", "__import__",
    "compile", "globals", "locals", "vars",
    "breakpoint", "input",
}

_SAFE_BUILTINS = {
    k: v for k, v in __builtins__.items()
    if k not in _BLOCKED
} if isinstance(__builtins__, dict) else {
    k: getattr(__builtins__, k)
    for k in dir(__builtins__)
    if k not in _BLOCKED and not k.startswith("__")
}


# ── Safe globals injected into generated code ────────────────────────────────

def _make_safe_globals() -> dict:
    return {
        "__builtins__": _SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "json": json,
        "datetime": datetime,
        "re": re,
        "math": math,
    }


# ── Executor ─────────────────────────────────────────────────────────────────

class ExecutionResult:
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = "",
        error_line: int = 0,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_line = error_line

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_line": self.error_line,
        }


def execute(code: str, df: pd.DataFrame, timeout: int = 30) -> ExecutionResult:
    """
    Execute agent-generated code in a sandboxed environment.

    The code must define a function:
        def run(df: pd.DataFrame) -> dict: ...

    Returns ExecutionResult.
    """
    result_holder: list[Any] = [None]
    error_holder: list[str] = [""]
    error_line_holder: list[int] = [0]

    def _run():
        try:
            safe_globals = _make_safe_globals()
            exec(code, safe_globals)  # noqa: S102 — intentional sandboxed exec

            run_fn = safe_globals.get("run")
            if run_fn is None:
                error_holder[0] = "Generated code does not define a `run(df)` function."
                return

            result = run_fn(df.copy())

            # Validate contract: must return a dict
            if not isinstance(result, dict):
                error_holder[0] = f"`run(df)` must return a dict, got {type(result).__name__}"
                return

            # Serialise result — convert pandas/numpy types to plain Python
            result_holder[0] = _serialise(result)

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
            error=f"Execution timed out after {timeout} seconds.",
        )

    if error_holder[0]:
        return ExecutionResult(
            success=False,
            error=error_holder[0],
            error_line=error_line_holder[0],
        )

    return ExecutionResult(success=True, data=result_holder[0])


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
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (f != f) else round(f, 6)  # NaN → None
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Period,)):
        return str(obj)
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(obj)
    return obj
