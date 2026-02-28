from __future__ import annotations

from pathlib import Path
import zipfile

import openpyxl
import pandas as pd

from exporters import export_to_excel, export_to_json
from promethease_parser import parse_promethease_report


def test_export_json_valid(tmp_path: Path):
    df = parse_promethease_report("sample_data/report_fixture_1.html")
    out = tmp_path / "out.json"
    export_to_json(df, out)

    assert out.exists()
    loaded = pd.read_json(out)
    assert not loaded.empty


def test_export_excel_has_sheet_all(tmp_path: Path):
    df = parse_promethease_report("sample_data/report_fixture_1.html")
    out = tmp_path / "out.xlsx"
    export_to_excel(df, out)

    assert out.exists()
    assert out.stat().st_size > 0

    wb = openpyxl.load_workbook(out)
    assert "Все" in wb.sheetnames
