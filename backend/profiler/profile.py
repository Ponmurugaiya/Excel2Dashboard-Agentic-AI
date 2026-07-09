"""
Data Profiler
Extracts column-level statistics from DataFrames.
Correctly distinguishes:
  - Numeric ID columns (high-cardinality integers used as keys, e.g. CustomerID)
  - Numeric measure columns (revenue, quantity, price)
  - True datetime columns
  - String columns that happen to look date-like (e.g. stock codes)
"""

import re
import pandas as pd
from typing import Any, Dict

# Column name patterns that indicate a numeric ID (not a measure)
_ID_NAME_PATTERNS = re.compile(
    r"(^id$|id$|_id$| id$|no$|_no$| no$|code$|_code$| code$|key$|num$|number$|^invoice$|^order$|^transaction$)",
    re.IGNORECASE,
)

# Column name patterns that are almost certainly NOT dates even if values look like them
_ANTI_DATE_PATTERNS = re.compile(
    r"(stockcode|stock_code|sku|barcode|zipcode|zip_code|postcode|phone|mobile)",
    re.IGNORECASE,
)


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a statistical profile of a single DataFrame.

    Column type rules (in priority order):
    1. bool → "boolean"
    2. Already datetime64 → "datetime"
    3. Numeric dtype:
       a. If column name looks like an ID (ends in id/no/code/key) → "id"
          (stored as type "number" but with is_id=True flag for strategist)
       b. Otherwise → "number"
    4. String/object:
       a. Try coercing to datetime — but ONLY if:
          - column name doesn't match anti-date patterns
          - values don't look like numeric IDs (no pure integers)
          - coercion success rate > 80%
          - successfully parsed dates span at least 30 days
       b. Otherwise → "string"
    """
    profile: Dict[str, Any] = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": {},
    }

    for col in df.columns:
        series = df[col]
        col_norm = col.lower().replace(" ", "").replace("_", "")

        col_profile: Dict[str, Any] = {
            "missing":      int(series.isna().sum()),
            "missing_pct":  round(series.isna().mean() * 100, 2),
            "unique":       int(series.nunique(dropna=True)),
            "sample_values": _safe_sample(series),
            "is_id":        False,
        }

        # ── Boolean ───────────────────────────────────────────────────────────
        if pd.api.types.is_bool_dtype(series):
            col_profile["type"] = "boolean"

        # ── Already a parsed datetime ─────────────────────────────────────────
        elif pd.api.types.is_datetime64_any_dtype(series):
            col_profile["type"] = "datetime"
            dated = series.dropna()
            if len(dated) > 0:
                col_profile["min_date"] = str(dated.min().date())
                col_profile["max_date"] = str(dated.max().date())

        # ── Numeric dtype ─────────────────────────────────────────────────────
        elif pd.api.types.is_numeric_dtype(series):
            col_profile["type"] = "number"
            numeric = series.dropna()
            if len(numeric) > 0:
                col_profile["min"]  = _safe_float(numeric.min())
                col_profile["max"]  = _safe_float(numeric.max())
                col_profile["mean"] = _safe_float(numeric.mean())
                col_profile["std"]  = _safe_float(numeric.std())

            # Flag as ID if column name pattern + all values are integers
            if _ID_NAME_PATTERNS.search(col_norm):
                all_int = (numeric == numeric.astype("int64", errors="ignore")).all()
                if all_int:
                    col_profile["is_id"] = True

        # ── String / object ───────────────────────────────────────────────────
        else:
            # Guard against anti-date columns (stock codes, SKUs etc.)
            is_anti_date = bool(_ANTI_DATE_PATTERNS.search(col_norm))

            # Check if values look numeric (would falsely parse as dates)
            non_null = series.dropna().astype(str).str.strip()
            looks_numeric = non_null.str.match(r"^\d+$").mean() > 0.7

            if not is_anti_date and not looks_numeric:
                coerced = pd.to_datetime(series, errors="coerce")
                hit_rate = coerced.notna().sum() / max(len(series), 1)
                dated = coerced.dropna()

                # Require: >80% parseable AND date range spans >30 days
                date_span = 0
                if len(dated) > 1:
                    date_span = (dated.max() - dated.min()).days

                if hit_rate > 0.8 and date_span > 30:
                    col_profile["type"] = "datetime"
                    col_profile["min_date"] = str(dated.min().date())
                    col_profile["max_date"] = str(dated.max().date())
                else:
                    col_profile["type"] = "string"
            else:
                col_profile["type"] = "string"

        profile["columns"][col] = col_profile

    return profile


def profile_sheets(
    sheets: Dict[str, pd.DataFrame]
) -> Dict[str, Dict[str, Any]]:
    """Profile every sheet in the parsed Excel dict."""
    return {name: profile_dataframe(df) for name, df in sheets.items()}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> Any:
    try:
        v = float(value)
        return None if v != v else round(v, 4)
    except (TypeError, ValueError):
        return None


def _safe_sample(series: pd.Series, n: int = 5) -> list:
    non_null = series.dropna()
    sample = non_null.head(n).tolist()
    result = []
    for v in sample:
        try:
            result.append(v.item())
        except AttributeError:
            result.append(str(v) if hasattr(v, "isoformat") else v)
    return result
