"""
Excel Parser — Phase 1
Reads an uploaded Excel file and returns a dict of {sheet_name: DataFrame}.
No AI involved. Pure pandas + openpyxl.
"""

import pandas as pd
from pathlib import Path
from typing import Dict


def parse_excel(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Parse all sheets from an Excel file.

    Args:
        file_path: Absolute or relative path to the .xlsx / .xls file.

    Returns:
        A dict mapping sheet name → DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid Excel file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    try:
        sheets: Dict[str, pd.DataFrame] = pd.read_excel(
            path,
            sheet_name=None,   # Load all sheets
            engine="openpyxl",
        )
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}") from e

    # Drop completely empty sheets
    sheets = {
        name: df
        for name, df in sheets.items()
        if not df.empty
    }

    return sheets
