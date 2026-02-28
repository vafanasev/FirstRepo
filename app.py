from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from promethease_parser import parse_promethease_report
from translator import get_offline_translator

st.set_page_config(page_title="Promethease RU", page_icon="🧬", layout="wide")

st.markdown(
    """
    <style>
    .main-title {font-size: 2rem; font-weight: 700; margin-bottom: 0.2rem;}
    .subtitle {color: #8b949e; margin-bottom: 1rem;}
    .metric-card {
        border: 1px solid #2f343f;
        border-radius: 10px;
        padding: 12px;
        background: linear-gradient(180deg, #11151c 0%, #0e1117 100%);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">🧬 Локальный анализатор отчётов Promethease</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Данные обрабатываются только локально, без сетевых запросов.</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Загрузите отчёт (.html/.htm/.zip)", type=["html", "htm", "zip"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)

    try:
        df = parse_promethease_report(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if df.empty:
        st.warning("Не удалось извлечь SNP-таблицу из отчёта.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric-card">Всего SNP<br><b>%s</b></div>' % len(df), unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card">Макс. magnitude<br><b>%.2f</b></div>' % float(df["magnitude"].max()), unsafe_allow_html=True)
    with c3:
        bad_n = int((df["repute"] == "bad").sum())
        st.markdown('<div class="metric-card">Потенциально рискованных<br><b>%s</b></div>' % bad_n, unsafe_allow_html=True)

    st.subheader("Фильтры")
    q = st.text_input("Поиск (rsID / гены / описание)")
    repute_options = ["Плохое", "Хорошее", "Нейтральное", "Неизвестно"]
    selected_repute = st.multiselect("Репутация", options=repute_options, default=repute_options)
    min_mag = st.slider("Минимальная magnitude", min_value=0.0, max_value=float(max(1.0, df["magnitude"].max())), value=0.0)
    top_n = st.number_input("Top N по magnitude (0 = все)", min_value=0, value=100, step=10)

    filtered = df.copy()
    if q:
        mask = (
            filtered["rsID"].str.contains(q, case=False, na=False)
            | filtered["genes"].str.contains(q, case=False, na=False)
            | filtered["summary"].str.contains(q, case=False, na=False)
        )
        filtered = filtered[mask]

    filtered = filtered[filtered["repute_ru"].isin(selected_repute)]
    filtered = filtered[filtered["magnitude"] >= float(min_mag)]
    filtered = filtered.sort_values(by="magnitude", ascending=False)
    if top_n and top_n > 0:
        filtered = filtered.head(int(top_n))

    use_translation = st.checkbox("Перевести описание EN→RU (офлайн, если установлен argostranslate)")
    if use_translation:
        translator = get_offline_translator("en", "ru")
        if translator is None:
            st.info("argostranslate не установлен или нет языкового пакета en→ru.")
        else:
            filtered = filtered.copy()
            filtered["summary"] = filtered["summary"].astype(str).map(translator)

    ru_columns = {
        "rsID": "rsID",
        "genotype": "Генотип",
        "magnitude": "Magnitude",
        "repute_ru": "Репутация",
        "summary": "Описание",
        "genes": "Гены",
        "snpedia_link": "SNPedia",
        "source": "Источник",
    }

    st.subheader("Результаты")
    st.dataframe(filtered[list(ru_columns.keys())].rename(columns=ru_columns), use_container_width=True)

    # LLM-friendly exports built in-place to avoid extra files
    llm_columns = ["rsID", "genotype", "magnitude", "repute_ru", "summary", "genes", "snpedia_link", "source"]
    llm_frame = filtered[llm_columns].copy()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            filtered.to_excel(writer, index=False, sheet_name="Все")
        st.download_button(
            "Скачать Excel",
            data=excel_buffer.getvalue(),
            file_name="promethease_ru.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col2:
        json_data = filtered.to_json(orient="records", force_ascii=False, indent=2)
        st.download_button(
            "Скачать JSON",
            data=json_data.encode("utf-8"),
            file_name="promethease_ru.json",
            mime="application/json",
        )

    with col3:
        jsonl_data = "\n".join(
            json.dumps(item, ensure_ascii=False)
            for item in llm_frame.to_dict(orient="records")
        )
        st.download_button(
            "Скачать JSONL (LLM)",
            data=(jsonl_data + "\n").encode("utf-8"),
            file_name="promethease_ru_llm.jsonl",
            mime="application/x-ndjson",
        )

    with col4:
        md_lines = [
            "# Отчёт Promethease (для LLM)",
            f"\nВсего записей: {len(filtered)}\n",
        ]
        for item in llm_frame.head(30).to_dict(orient="records"):
            md_lines.extend(
                [
                    f"## {item['rsID']} ({item['genotype']})",
                    f"- magnitude: {item['magnitude']}",
                    f"- репутация: {item['repute_ru']}",
                    f"- гены: {item['genes'] or '—'}",
                    f"- описание: {item['summary'] or '—'}",
                    f"- SNPedia: {item['snpedia_link'] or '—'}",
                    f"- источник: {item['source'] or '—'}\n",
                ]
            )
        st.download_button(
            "Скачать Markdown (LLM)",
            data="\n".join(md_lines).encode("utf-8"),
            file_name="promethease_ru_llm.md",
            mime="text/markdown",
        )
else:
    st.info("Загрузите файл отчёта для начала работы.")
