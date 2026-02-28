from __future__ import annotations


def get_offline_translator(from_lang: str = "en", to_lang: str = "ru"):
    """Return callable(text)->translated_text if argostranslate is available."""
    try:
        from argostranslate import package, translate  # type: ignore
    except Exception:
        return None

    try:
        installed_languages = translate.get_installed_languages()
        from_language = next((lang for lang in installed_languages if lang.code == from_lang), None)
        to_language = next((lang for lang in installed_languages if lang.code == to_lang), None)

        if from_language is None or to_language is None:
            return None

        translator = from_language.get_translation(to_language)
        if translator is None:
            return None
        return translator.translate
    except Exception:
        return None
