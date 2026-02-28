from __future__ import annotations

from pathlib import Path
import zipfile

import pandas as pd

from promethease_parser import (
    load_report_bytes,
    map_repute_to_ru,
    normalize_magnitude,
    parse_promethease_report,
)


def test_load_html_from_zip_uses_largest_html(tmp_path: Path):
    zip_path = tmp_path / "report.zip"
    small = b"<html><body>small</body></html>"
    large = b"<html><body>" + b"x" * 1000 + b"</body></html>"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("small.html", small)
        zf.writestr("nested/large.htm", large)

    loaded = load_report_bytes(zip_path)
    assert loaded == large


def test_parse_table_has_at_least_5_rows_and_expected_columns():
    df = parse_promethease_report("sample_data/report_fixture_1.html")
    assert len(df) >= 5
    expected = {"rsID", "genotype", "magnitude", "repute", "repute_ru", "summary", "genes", "snpedia_link", "source"}
    assert expected.issubset(set(df.columns))


def test_normalize_magnitude_variants():
    assert normalize_magnitude("2,5") == 2.5
    assert normalize_magnitude("mag=4.1") == 4.1
    assert normalize_magnitude(None) == 0.0
    assert normalize_magnitude("N/A") == 0.0


def test_map_repute_to_ru():
    assert map_repute_to_ru("bad") == "Плохое"
    assert map_repute_to_ru("good") == "Хорошее"
    assert map_repute_to_ru("neutral") == "Нейтральное"
    assert map_repute_to_ru("whatever") == "Неизвестно"


def test_smoke_parser_not_empty_and_columns_present():
    df = parse_promethease_report("sample_data/report_fixture_2.html")
    assert not df.empty
    for col in ["rsID", "genotype", "magnitude", "repute_ru", "summary"]:
        assert col in df.columns


def test_parse_headerless_class_based_table_extracts_key_fields():
    df = parse_promethease_report("sample_data/report_fixture_4.html")
    assert len(df) == 2

    row = df[df["rsID"].str.lower() == "rs8176746"].iloc[0]
    assert row["genotype"] in {"A;G", "A/G"}
    assert row["magnitude"] == 2.8
    assert row["repute"] == "bad"
    assert row["repute_ru"] == "Плохое"
    assert row["genes"] == "ABO"
    assert "blood group" in row["summary"].lower()
