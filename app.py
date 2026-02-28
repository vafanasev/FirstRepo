from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from exporters import export_to_excel, export_to_json
from promethease_parser import parse_promethease_report
from translator import get_offline_translator

st.set_page_config(page_title="Promethease RU", layout="wide")
st.title("Локальный анализатор отчётов Promethease")
st.caption("Данные обрабатываются только локально, без сетевых запросов.")

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

    st.subheader("Фильтры")
    q = st.text_input("Поиск (rsID / гены / описание)")
    repute_options = ["Плохое", "Хорошее", "Нейтральное", "Неизвестно"]
    selected_repute = st.multiselect("Репутация", options=repute_options, default=repute_options)
    min_mag = st.slider("Минимальная magnitude", min_value=0.0, max_value=float(max(1.0, df["magnitude"].max())), value=0.0)
    top_n = st.number_input("Top N по magnitude (0 = все)", min_value=0, value=0, step=10)

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

    st.subheader("Результаты")
    st.dataframe(filtered, use_container_width=True)

    col1, col2 = st.columns(2)

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
else:
    st.info("Загрузите файл отчёта для начала работы.")
