from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

import pandas as pd
from bs4 import BeautifulSoup

REPUTE_RU_MAP = {
    "bad": "Плохое",
    "good": "Хорошее",
    "neutral": "Нейтральное",
    "unknown": "Неизвестно",
    "": "Неизвестно",
}

REQUIRED_COLUMNS = [
    "rsID",
    "genotype",
    "magnitude",
    "repute",
    "repute_ru",
    "summary",
    "genes",
    "snpedia_link",
    "source",
]


def load_report_bytes(path: str | Path) -> bytes:
    """Load report bytes from .html/.htm or .zip (largest html inside)."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix in {".html", ".htm"}:
        return file_path.read_bytes()

    if suffix == ".zip":
        with zipfile.ZipFile(file_path) as zf:
            html_candidates = [
                info for info in zf.infolist() if info.filename.lower().endswith((".html", ".htm"))
            ]
            if not html_candidates:
                raise ValueError("В ZIP-файле не найдено HTML-отчёта")
            best = max(html_candidates, key=lambda i: i.file_size)
            return zf.read(best)

    raise ValueError("Поддерживаются только .html/.htm/.zip")


def normalize_magnitude(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0.0
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return 0.0
    return float(match.group(0))


def map_repute_to_ru(repute: object) -> str:
    key = str(repute or "").strip().lower()
    return REPUTE_RU_MAP.get(key, "Неизвестно")


def _extract_headers(table) -> list[str]:
    headers = [h.get_text(" ", strip=True).lower() for h in table.find_all("th")]
    return headers


def _find_data_tables(soup: BeautifulSoup):
    tables = soup.find_all("table")
    for table in tables:
        headers = _extract_headers(table)
        header_line = " ".join(headers)
        if "rsid" in header_line or "genotype" in header_line or "magnitude" in header_line:
            yield table


def _extract_link(cell) -> str:
    a_tag = cell.find("a", href=True)
    return a_tag["href"].strip() if a_tag else ""


def _text(cell) -> str:
    return cell.get_text(" ", strip=True)


def _parse_row_by_headers(cells, headers: list[str]) -> dict[str, object]:
    row = {
        "rsID": "",
        "genotype": "",
        "magnitude": 0.0,
        "repute": "unknown",
        "summary": "",
        "genes": "",
        "snpedia_link": "",
        "source": "",
    }

    for idx, cell in enumerate(cells):
        if idx >= len(headers):
            continue
        header = headers[idx]
        value = _text(cell)

        if "rsid" in header or header == "snp":
            row["rsID"] = value
            if not row["snpedia_link"]:
                row["snpedia_link"] = _extract_link(cell)
        elif "genotype" in header:
            row["genotype"] = value
        elif "magnitude" in header:
            row["magnitude"] = normalize_magnitude(value)
        elif "repute" in header:
            row["repute"] = value.lower() if value else "unknown"
        elif "summary" in header or "description" in header:
            row["summary"] = value
        elif "gene" in header:
            row["genes"] = value
        elif "snpedia" in header or "link" in header:
            row["snpedia_link"] = _extract_link(cell) or value
        elif "source" in header or "section" in header:
            row["source"] = value

    if not row["rsID"]:
        for cell in cells:
            txt = _text(cell)
            match = re.search(r"\brs\d+\b", txt, flags=re.IGNORECASE)
            if match:
                row["rsID"] = match.group(0)
                row["snpedia_link"] = row["snpedia_link"] or _extract_link(cell)
                break

    if row["repute"] == "unknown":
        joined = " ".join(_text(c).lower() for c in cells)
        for rep in ("bad", "good", "neutral"):
            if re.search(rf"\b{rep}\b", joined):
                row["repute"] = rep
                break

    if not row["summary"] and len(cells) >= 4:
        row["summary"] = _text(cells[-1])

    return row


def parse_promethease_html_bytes(html_bytes: bytes) -> pd.DataFrame:
    soup = BeautifulSoup(BytesIO(html_bytes), "lxml")
    parsed_rows: list[dict[str, object]] = []

    for table in _find_data_tables(soup):
        headers = _extract_headers(table)
        body_rows = table.find_all("tr")
        for tr in body_rows:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            if tr.find("th") and tr.find("td") is None:
                continue

            row = _parse_row_by_headers(cells, headers)
            if row["rsID"]:
                row["repute"] = str(row["repute"] or "unknown").lower()
                row["repute_ru"] = map_repute_to_ru(row["repute"])
                parsed_rows.append(row)

    df = pd.DataFrame(parsed_rows)
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in {"magnitude"} else 0.0

    df["magnitude"] = df["magnitude"].apply(normalize_magnitude)
    df = df.drop_duplicates(subset=["rsID", "genotype", "summary"], keep="first")
    df = df.sort_values(by="magnitude", ascending=False).reset_index(drop=True)
    return df[REQUIRED_COLUMNS]


def parse_promethease_report(path: str | Path) -> pd.DataFrame:
    html_bytes = load_report_bytes(path)
    return parse_promethease_html_bytes(html_bytes)
