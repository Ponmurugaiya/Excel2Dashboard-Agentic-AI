"""
Data Profiler — Phase 1
Extracts column-level statistics from DataFrames.
No AI involved. Pure pandas.
"""

import pandas as pd
from typing import Any, Dict


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a statistical profile of a single DataFrame.

    Returns a dict shaped like:
    {
        "row_count": int,
        "column_count": int,
        "columns": {
            "col_name": {
                "type": "number" | "string" | "datetime" | "boolean",
                "missing": int,
                "missing_pct": float,
                "unique": int,
                "sample_values": [...],
                # numeric only:
                "min": float, "max": float, "mean": float, "std": float,
                # datetime only:
                "min_date": str, "max_date": str,
            },
            ...
        }
    }
    """
    profile: Dict[str, Any] = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": {},
    }

    for col in df.columns:
        series = df[col]
        col_profile: Dict[str, Any] = {
            "missing": int(series.isna().sum()),
            "missing_pct": round(series.isna().mean() * 100, 2),
            "unique": int(series.nunique(dropna=True)),
            "sample_values": _safe_sample(series),
        }

        # Detect type and compute type-specific stats
        if pd.api.types.is_bool_dtype(series):
            col_profile["type"] = "boolean"

        elif pd.api.types.is_numeric_dtype(series):
            col_profile["type"] = "number"
            numeric = series.dropna()
            if len(numeric) > 0:
                col_profile["min"] = _safe_float(numeric.min())
                col_profile["max"] = _safe_float(numeric.max())
                col_profile["mean"] = _safe_float(numeric.mean())
                col_profile["std"] = _safe_float(numeric.std())

        elif pd.api.types.is_datetime64_any_dtype(series):
            col_profile["type"] = "datetime"
            dated = series.dropna()
            if len(dated) > 0:
                col_profile["min_date"] = str(dated.min().date())
                col_profile["max_date"] = str(dated.max().date())
        else:
            # Try coercing to datetime (common in Excel uploads)
            coerced = pd.to_datetime(series, errors="coerce")
            if coerced.notna().sum() / max(len(series), 1) > 0.7:
                col_profile["type"] = "datetime"
                dated = coerced.dropna()
                if len(dated) > 0:
                    col_profile["min_date"] = str(dated.min().date())
                    col_profile["max_date"] = str(dated.max().date())
            else:
                col_profile["type"] = "string"

        profile["columns"][col] = col_profile

    return profile


def profile_sheets(
    sheets: Dict[str, pd.DataFrame]
) -> Dict[str, Dict[str, Any]]:
    """Profile every sheet in the parsed Excel dict."""
    return {name: profile_dataframe(df) for name, df in sheets.items()}


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> Any:
    """Convert numpy scalar to a plain Python float, handle NaN/Inf."""
    try:
        v = float(value)
        if v != v:  # NaN check
            return None
        return round(v, 4)
    except (TypeError, ValueError):
        return None


def _safe_sample(series: pd.Series, n: int = 5) -> list:
    """Return up to n non-null sample values as plain Python objects."""
    non_null = series.dropna()
    sample = non_null.head(n).tolist()
    # Convert numpy types to plain Python
    result = []
    for v in sample:
        try:
            result.append(v.item())  # numpy scalar → Python
        except AttributeError:
            result.append(str(v) if hasattr(v, "isoformat") else v)
    return result
