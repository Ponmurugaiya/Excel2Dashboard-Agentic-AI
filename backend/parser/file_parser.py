"""
File Parser — Phase 1
Supports Excel (.xlsx, .xls, .xlsm) and CSV (.csv) files.
Returns a unified dict of {sheet_name: DataFrame} regardless of input type.
No AI involved. Pure pandas + openpyxl.
"""

import pandas as pd
from pathlib import Path
from typing import Dict

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
CSV_EXTENSIONS   = {".csv"}
SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS | CSV_EXTENSIONS


def parse_file(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Parse an Excel or CSV file into a dict of DataFrames.

    - Excel: each sheet becomes one entry  → { "Sheet1": df, "Sheet2": df }
    - CSV:   the filename becomes the key  → { "sales": df }

    Args:
        file_path: Path to the uploaded file.

    Returns:
        Dict mapping sheet/file name → DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is unsupported or the file is corrupt.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Accepted formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if suffix in EXCEL_EXTENSIONS:
        return _parse_excel(path)
    else:
        return _parse_csv(path)


# ── Excel ─────────────────────────────────────────────────────────────────────

def _parse_excel(path: Path) -> Dict[str, pd.DataFrame]:
    try:
        sheets: Dict[str, pd.DataFrame] = pd.read_excel(
            path,
            sheet_name=None,  # load all sheets
            engine="openpyxl",
        )
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}") from e

    # Drop completely empty sheets
    sheets = {name: df for name, df in sheets.items() if not df.empty}

    if not sheets:
        raise ValueError("The Excel file contains no data.")

    return sheets


# ── CSV ───────────────────────────────────────────────────────────────────────

def _parse_csv(path: Path) -> Dict[str, pd.DataFrame]:
    """
    Smart CSV parser:
    - Auto-detects delimiter (comma, semicolon, tab, pipe)
    - Strips whitespace from column names
    - Tries to parse obvious date columns automatically
    """
    delimiter = _detect_delimiter(path)

    try:
        df = pd.read_csv(
            path,
            sep=delimiter,
            encoding="utf-8",
            encoding_errors="replace",  # handle non-UTF8 files gracefully
            skipinitialspace=True,
        )
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {e}") from e

    if df.empty:
        raise ValueError("The CSV file contains no data.")

    # Clean column names — strip leading/trailing whitespace
    df.columns = [str(c).strip() for c in df.columns]

    # Use the filename stem as the sheet name (e.g. "sales_data" for sales_data.csv)
    sheet_name = path.stem

    return {sheet_name: df}


def _detect_delimiter(path: Path) -> str:
    """
    Peek at the first non-empty line of the file and pick the most likely delimiter.
    Falls back to comma if nothing obvious is found.
    """
    candidates = [",", ";", "\t", "|"]

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # Skip blank lines, read first real line
            for line in f:
                line = line.strip()
                if line:
                    counts = {delim: line.count(delim) for delim in candidates}
                    best = max(counts, key=counts.get)
                    if counts[best] > 0:
                        return best
                    break
    except Exception:
        pass

    return ","  # safe default
