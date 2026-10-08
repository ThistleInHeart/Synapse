# -*- coding: utf-8 -*-
"""
Synapse In-Game Localization Engine
Provides _t(key, default) for retrieving translated UI strings in-game.
Automatically determines the language from:
1. Custom override in ai_mod_config.json (if user selected it)
2. The Sims 4 active game locale (services.get_current_locale())
3. Default: 'en' for English / all locales, 'ru' for Russian locale

Supports dynamic runtime loading of community translations (.json files)
placed directly in Mods\\Synapse\\languages\\mod_strings\\ without recompiling the mod!
"""

import os
import json

try:
    from ai_thought_reader.mod_strings import MOD_STRINGS
except ImportError:
    try:
        from ai_social_pc.mod_strings import MOD_STRINGS
    except ImportError:
        MOD_STRINGS = {}

_CURRENT_LANG = None

_EXTERNAL_LANG_DIRS = [
    os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\Mods\Synapse\languages\mod_strings"),
    os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\Mods\languages\mod_strings"),
    r"C:\Users\zayar\Desktop\Synapse\Mods\languages\mod_strings",
]
_LOADED_EXTERNAL_LANGS = {}


def _load_external_lang(lang_code: str) -> dict:
    """
    Dynamically loads and caches mod_strings_{lang_code}.json if placed
    in the player's Mods\\Synapse\\languages\\mod_strings\\ folder.
    Automatically reloads if the file has been modified on disk.
    """
    global _LOADED_EXTERNAL_LANGS
    code = (lang_code or "").strip().lower()
    if not code:
        return {}

    target_name = "mod_strings_{}.json".format(code)
    for folder in _EXTERNAL_LANG_DIRS:
        if not os.path.isdir(folder):
            continue
        fpath = os.path.join(folder, target_name)
        if os.path.isfile(fpath):
            try:
                mtime = os.path.getmtime(fpath)
                cached = _LOADED_EXTERNAL_LANGS.get(code)
                if cached and cached.get("mtime") == mtime:
                    return cached.get("data", {})

                with open(fpath, "r", encoding="utf-8") as f:
                    content = json.load(f)
                if isinstance(content, dict):
                    _LOADED_EXTERNAL_LANGS[code] = {"mtime": mtime, "data": content}
                    return content
            except Exception:
                pass

    return _LOADED_EXTERNAL_LANGS.get(code, {}).get("data", {})


def get_available_languages() -> dict:
    """
    Returns a dictionary of language_code -> display_name.
    Combines built-in languages ('en', 'ru') with any external community
    mod_strings_*.json files discovered in the Mods directory.
    """
    langs = {
        "en": "English",
        "ru": "Русский",
    }
    for folder in _EXTERNAL_LANG_DIRS:
        if not os.path.isdir(folder):
            continue
        try:
            for fname in os.listdir(folder):
                if fname.startswith("mod_strings_") and fname.endswith(".json"):
                    code = fname[len("mod_strings_"):-len(".json")].lower()
                    if code not in langs:
                        data = _load_external_lang(code)
                        d_name = data.get("_metadata", {}).get("display_name", code.upper())
                        langs[code] = "{} ({})".format(d_name, code.upper())
        except Exception:
            pass
    return langs


def set_current_language(code: str):
    """Sets active language and synchronizes with config."""
    global _CURRENT_LANG
    _CURRENT_LANG = code.lower().strip() if code else None
    try:
        from ai_thought_reader.config import set_language
        set_language(_CURRENT_LANG)
    except Exception:
        pass


def get_game_language() -> str:
    """
    Returns the active language code ('en', 'ru', etc.).
    Dynamically queries config so changes on disk or from Synapse Launcher
    take immediate effect without requiring a game restart.
    """
    global _CURRENT_LANG
    try:
        from ai_thought_reader.config import get_language
        lang = get_language()
        if lang:
            _CURRENT_LANG = lang
            return lang
    except Exception:
        pass

    try:
        from ai_social_pc.config import get_language
        lang = get_language()
        if lang:
            _CURRENT_LANG = lang
            return lang
    except Exception:
        pass

    if _CURRENT_LANG:
        return _CURRENT_LANG

    # Fallback to game locale
    try:
        import services
        loc = services.get_current_locale()
        if loc:
            loc_str = str(loc).lower()
            if "ru" in loc_str:
                _CURRENT_LANG = "ru"
                return "ru"
            _CURRENT_LANG = "en"
            return "en"
    except Exception:
        pass

    return "en"


def is_english() -> bool:
    """Returns True if the active game/mod language is English."""
    return get_game_language() == "en"


def _t(key: str, default: str = "") -> str:
    """
    Returns localized string for the specified key.
    1. Checks external mod_strings_{lang}.json from Mods/Synapse/languages/mod_strings/
    2. Checks built-in MOD_STRINGS dictionary for active language
    3. Falls back to built-in 'en' (Master)
    4. Falls back to built-in 'ru'
    5. Falls back to default parameter or key
    """
    lang = get_game_language()

    # 1. External override / community translation
    ext_dict = _load_external_lang(lang)
    if ext_dict and key in ext_dict:
        val = ext_dict.get(key)
        if val and not str(val).startswith("[TODO]"):
            return str(val)

    # 2. Built-in compiled dictionary for active language
    lang_dict = MOD_STRINGS.get(lang, {})
    val = lang_dict.get(key)
    if val and not str(val).startswith("[TODO]"):
        return str(val)

    # 3. Fallback to EN (Master)
    en_dict = MOD_STRINGS.get("en", {})
    val_en = en_dict.get(key)
    if val_en and not str(val_en).startswith("[TODO]"):
        return str(val_en)

    # 4. Fallback to RU
    ru_dict = MOD_STRINGS.get("ru", {})
    val_ru = ru_dict.get(key)
    if val_ru and not str(val_ru).startswith("[TODO]"):
        return str(val_ru)

    return default or key
