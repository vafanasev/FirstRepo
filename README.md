# Promethease RU (локально)

Локальный MVP для разбора отчётов Promethease (`.html/.htm/.zip`) с интерфейсом на русском.

## Возможности
- Парсинг отчётов Promethease в `pandas.DataFrame`
- Поддержка `.zip` (берётся самый крупный html внутри)
- Streamlit UI: фильтры, поиск, сортировка, Top N
- Экспорт в `Excel (.xlsx)`, `JSON`, `JSONL (LLM)` и `Markdown (LLM)`
- CLI для пакетной обработки
- Опциональный офлайн-перевод EN→RU через `argostranslate` (необязательный)

## Быстрый запуск (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Если Streamlit просит email
Это одноразовый onboarding Streamlit и не обязателен:
- можно просто оставить поле пустым и нажать Enter;
- либо отключить сбор usage stats:

```bash
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml <<'CFG'
[browser]
gatherUsageStats = false
CFG
```

## Запуск Streamlit
```bash
python3 -m streamlit run app.py
```

## Пример запуска CLI
```bash
python3 -m promethease_ru parse sample_data/report_fixture_1.html --out out.xlsx --min-mag 2 --repute bad,good
python3 -m promethease_ru parse sample_data/report_fixture_1.html --out out.json
```

## Форматы для LLM
В Web UI доступны отдельные кнопки:
- `Скачать JSONL (LLM)` — один JSON-объект на строку, удобно для RAG/батч-обработки.
- `Скачать Markdown (LLM)` — краткий структурированный отчёт top SNP по magnitude.

## Тесты
```bash
python3 -m pytest -q
```

## Локальность и приватность
Приложение не делает сетевых запросов при парсинге/фильтрации/экспорте.
