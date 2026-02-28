from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


LLM_COLUMNS = [
    "rsID",
    "genotype",
    "magnitude",
    "repute_ru",
    "summary",
    "genes",
    "snpedia_link",
    "source",
]


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


def export_to_jsonl(df: pd.DataFrame, out_path: str | Path) -> Path:
    """LLM-friendly format: one JSON object per line."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    frame = df.copy()
    for col in LLM_COLUMNS:
        if col not in frame.columns:
            frame[col] = ""

    with out.open("w", encoding="utf-8") as f:
        for record in frame[LLM_COLUMNS].to_dict(orient="records"):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out


def dataframe_to_markdown_summary(df: pd.DataFrame, top_n: int = 30) -> str:
    """Human/LLM-readable compact summary in markdown."""
    if df.empty:
        return "# Отчёт Promethease\n\nДанные не найдены."

    frame = df.copy()
    for col in LLM_COLUMNS:
        if col not in frame.columns:
            frame[col] = ""

    frame = frame.sort_values("magnitude", ascending=False).head(top_n)
    lines = [
        "# Отчёт Promethease (для LLM)",
        "",
        f"Всего записей в выгрузке: {len(df)}",
        f"Показаны top {min(top_n, len(frame))} по magnitude.",
        "",
    ]

    for row in frame[LLM_COLUMNS].to_dict(orient="records"):
        lines.extend(
            [
                f"## {row['rsID']} ({row['genotype']})",
                f"- magnitude: {row['magnitude']}",
                f"- репутация: {row['repute_ru']}",
                f"- гены: {row['genes'] or '—'}",
                f"- summary: {row['summary'] or '—'}",
                f"- snpedia: {row['snpedia_link'] or '—'}",
                f"- source: {row['source'] or '—'}",
                "",
            ]
        )

    return "\n".join(lines)
