from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_to_json(df: pd.DataFrame, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(out, orient="records", force_ascii=False, indent=2)
    return out


def export_to_excel(df: pd.DataFrame, out_path: str | Path, sheet_name: str = "Все") -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return out
