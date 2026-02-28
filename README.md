# Promethease RU (локально)

Локальный MVP для разбора отчётов Promethease (`.html/.htm/.zip`) с интерфейсом на русском.

## Возможности
- Парсинг отчётов Promethease в `pandas.DataFrame`
- Поддержка `.zip` (берётся самый крупный html внутри)
- Streamlit UI: фильтры, поиск, сортировка, Top N
- Экспорт в `Excel (.xlsx)` и `JSON`
- CLI для пакетной обработки
- Опциональный офлайн-перевод EN→RU через `argostranslate` (необязательный)

## Установка
```bash
python -m pip install -r requirements.txt
```

## Запуск Streamlit
```bash
streamlit run app.py
```

## Пример запуска CLI
```bash
python -m promethease_ru parse sample_data/report_fixture_1.html --out out.xlsx --min-mag 2 --repute bad,good
python -m promethease_ru parse sample_data/report_fixture_1.html --out out.json
```

## Тесты
```bash
python -m pytest -q
```

## Локальность и приватность
Приложение не делает сетевых запросов при парсинге/фильтрации/экспорте.
