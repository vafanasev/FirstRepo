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

RSID_PATTERN = re.compile(r"\b(?:rs\d+|i\d+)\b", flags=re.IGNORECASE)


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


def _text(cell) -> str:
    return cell.get_text(" ", strip=True)


def _extract_link(cell) -> str:
    for a_tag in cell.find_all("a", href=True):
        href = a_tag["href"].strip()
        if "snpedia.com" in href:
            return href
    a_tag = cell.find("a", href=True)
    return a_tag["href"].strip() if a_tag else ""


def _extract_headers(table) -> list[str]:
    thead_tr = table.select_one("thead tr")
    if thead_tr:
        header_cells = thead_tr.find_all(["th", "td"])
        return [c.get_text(" ", strip=True).lower() for c in header_cells]

    for tr in table.find_all("tr"):
        th_cells = tr.find_all("th")
        td_cells = tr.find_all("td")
        if th_cells and (not td_cells) and len(th_cells) > 1:
            return [c.get_text(" ", strip=True).lower() for c in th_cells]
        if th_cells and td_cells and len(th_cells) == len(td_cells):
            return [c.get_text(" ", strip=True).lower() for c in th_cells]

    return []


def _find_data_tables(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        headers = _extract_headers(table)
        header_line = " ".join(headers)
        table_text = table.get_text(" ", strip=True).lower()
        if (
            "rsid" in header_line
            or "genotype" in header_line
            or "magnitude" in header_line
            or "snpedia" in table_text
            or RSID_PATTERN.search(table_text)
        ):
            yield table


def _parse_by_header(header: str, value: str, cell, row: dict[str, object]) -> None:
    if "rsid" in header or header == "snp":
        row["rsID"] = value
        row["snpedia_link"] = row["snpedia_link"] or _extract_link(cell)
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


def _cell_signature(cell) -> str:
    classes = " ".join(cell.get("class", []))
    attrs = " ".join(str(cell.get(k, "")) for k in ("data-title", "data-label", "aria-label", "title"))
    return f"{classes} {attrs}".lower()


def _parse_row_heuristics(cells, row: dict[str, object]) -> None:
    joined = " ".join(_text(c) for c in cells)
    joined_lower = joined.lower()

    if not row["rsID"]:
        rs_match = RSID_PATTERN.search(joined)
        if rs_match:
            row["rsID"] = rs_match.group(0)

    if not row["genotype"]:
        gt_match = re.search(r"\(([ACGTDI;/-]{1,10})\)", joined, flags=re.IGNORECASE)
        if gt_match:
            row["genotype"] = gt_match.group(1).replace(";", "/")

    if not row["magnitude"]:
        mag_match = re.search(r"(?:magnitude|mag)\s*[:=]?\s*([-+]?\d*[\.,]?\d+)", joined_lower)
        if mag_match:
            row["magnitude"] = normalize_magnitude(mag_match.group(1))

    if row["repute"] == "unknown":
        rep_match = re.search(r"\b(bad|good|neutral)\b", joined_lower)
        if rep_match:
            row["repute"] = rep_match.group(1)

    if not row["snpedia_link"]:
        for c in cells:
            link = _extract_link(c)
            if link:
                row["snpedia_link"] = link
                break

    if not row["summary"] and cells:
        best = ""
        for c in cells:
            t = _text(c)
            if not t:
                continue
            if RSID_PATTERN.fullmatch(t):
                continue
            if len(t) > len(best):
                best = t
        row["summary"] = best


def _parse_row(cells, headers: list[str]) -> dict[str, object]:
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
        value = _text(cell)
        signature = _cell_signature(cell)

        if idx < len(headers):
            _parse_by_header(headers[idx], value, cell, row)

        if "gene" in signature and not row["genes"]:
            row["genes"] = value
        if "geno" in signature and not row["genotype"]:
            row["genotype"] = value
        if "magnitude" in signature and not row["magnitude"]:
            row["magnitude"] = normalize_magnitude(value)
        if "repute" in signature and row["repute"] == "unknown":
            row["repute"] = value.lower() if value else "unknown"
        if ("summary" in signature or "desc" in signature) and not row["summary"]:
            row["summary"] = value
        if ("source" in signature or "section" in signature) and not row["source"]:
            row["source"] = value
        if ("snp" in signature or "link" in signature) and not row["snpedia_link"]:
            row["snpedia_link"] = _extract_link(cell) or value

        if not row["rsID"]:
            rs_match = RSID_PATTERN.search(value)
            if rs_match:
                row["rsID"] = rs_match.group(0)
                row["snpedia_link"] = row["snpedia_link"] or _extract_link(cell)

    _parse_row_heuristics(cells, row)
    row["repute"] = str(row["repute"] or "unknown").lower()
    row["repute_ru"] = map_repute_to_ru(row["repute"])
    return row


def _new_row() -> dict[str, object]:
    return {
        "rsID": "",
        "genotype": "",
        "magnitude": 0.0,
        "repute": "unknown",
        "summary": "",
        "genes": "",
        "snpedia_link": "",
        "source": "",
        "repute_ru": "Неизвестно",
    }


def _extract_pairs_from_tables(container) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for tr in container.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        left = _text(cells[0]).strip()
        right = _text(cells[1]).strip()
        if not left or not right:
            continue
        left_l = left.lower()
        right_l = right.lower()
        # supports both "Label | Value" and "Value | Label"
        if right_l in {"repute", "magnitude", "frequency", "genes", "gene", "summary", "description", "source"}:
            pairs[right_l] = left
        if left_l in {"repute", "magnitude", "frequency", "genes", "gene", "summary", "description", "source"}:
            pairs[left_l] = right
    return pairs


def _extract_rows_from_detail_blocks(soup: BeautifulSoup) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for container in soup.find_all(["section", "article", "div"]):
        title_tag = container.find(["h1", "h2", "h3", "h4", "a"], string=RSID_PATTERN)
        if title_tag is None:
            continue

        title_text = _text(title_tag)
        rs_match = RSID_PATTERN.search(title_text)
        if rs_match is None:
            continue

        row = _new_row()
        row["rsID"] = rs_match.group(0)

        gt_match = re.search(r"\(([ACGTDI;/-]{1,10})\)", title_text, flags=re.IGNORECASE)
        if gt_match:
            row["genotype"] = gt_match.group(1).replace(";", "/")

        pairs = _extract_pairs_from_tables(container)
        if "magnitude" in pairs:
            row["magnitude"] = normalize_magnitude(pairs["magnitude"])
        if "repute" in pairs:
            row["repute"] = pairs["repute"].lower()
        if "gene" in pairs and not row["genes"]:
            row["genes"] = pairs["gene"]
        if "genes" in pairs and not row["genes"]:
            row["genes"] = pairs["genes"]
        if "summary" in pairs and not row["summary"]:
            row["summary"] = pairs["summary"]
        if "description" in pairs and not row["summary"]:
            row["summary"] = pairs["description"]
        if "source" in pairs:
            row["source"] = pairs["source"]

        if not row["summary"]:
            best_par = ""
            for p in container.find_all(["p", "li"]):
                t = _text(p)
                if len(t) > len(best_par):
                    best_par = t
            row["summary"] = best_par

        row["snpedia_link"] = "https://www.snpedia.com/index.php/" + str(row["rsID"])
        row["repute"] = str(row["repute"] or "unknown").lower()
        row["repute_ru"] = map_repute_to_ru(row["repute"])
        rows.append(row)
    return rows


def _is_low_information(row: pd.Series) -> bool:
    summary = str(row.get("summary", "") or "").strip().lower()
    return (
        normalize_magnitude(row.get("magnitude", 0.0)) == 0.0
        and str(row.get("genotype", "") or "").strip() == ""
        and str(row.get("genes", "") or "").strip() == ""
        and str(row.get("repute", "unknown") or "unknown").strip().lower() == "unknown"
        and summary in {"", "not tested", "not set"}
    )


def parse_promethease_html_bytes(html_bytes: bytes) -> pd.DataFrame:
    soup = BeautifulSoup(BytesIO(html_bytes), "lxml")
    parsed_rows: list[dict[str, object]] = []

    for table in _find_data_tables(soup):
        headers = _extract_headers(table)
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            if tr.find("th") and tr.find("td") is None:
                continue

            row = _parse_row(cells, headers)
            if row["rsID"]:
                parsed_rows.append(row)

    parsed_rows.extend(_extract_rows_from_detail_blocks(soup))

    df = pd.DataFrame(parsed_rows)
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col != "magnitude" else 0.0

    df["magnitude"] = df["magnitude"].apply(normalize_magnitude)
    df["repute"] = df["repute"].astype(str).str.lower()
    df["repute_ru"] = df["repute"].apply(map_repute_to_ru)

    df = df.drop_duplicates(subset=["rsID", "genotype", "summary"], keep="first")

    low_mask = df.apply(_is_low_information, axis=1)
    if (~low_mask).any():
        df = df[~low_mask]

    df = df.sort_values(by="magnitude", ascending=False).reset_index(drop=True)
    return df[REQUIRED_COLUMNS]


def parse_promethease_report(path: str | Path) -> pd.DataFrame:
    html_bytes = load_report_bytes(path)
    return parse_promethease_html_bytes(html_bytes)
