from __future__ import annotations

from pathlib import Path
import json

import openpyxl
import pandas as pd

from exporters import dataframe_to_markdown_summary, export_to_excel, export_to_json, export_to_jsonl
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


def test_export_jsonl_valid_lines(tmp_path: Path):
    df = parse_promethease_report("sample_data/report_fixture_1.html")
    out = tmp_path / "out.jsonl"
    export_to_jsonl(df, out)

    assert out.exists()
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) > 0

    first = json.loads(lines[0])
    assert "rsID" in first
    assert "summary" in first


def test_markdown_summary_has_title_and_rsid():
    df = parse_promethease_report("sample_data/report_fixture_1.html")
    md = dataframe_to_markdown_summary(df, top_n=3)
    assert "# Отчёт Promethease (для LLM)" in md
    assert "## rs" in md.lower()
