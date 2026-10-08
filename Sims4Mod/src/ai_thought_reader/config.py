import os
import json
from ai_thought_reader.logger import log, log_exception

CONFIG_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_mod_config.json")

def get_system_default_language():
    """
    Standard default mode is English ('en') for all languages,
    EXCEPT when the game locale is Russian ('ru') -> then Russian ('ru').
    """
    try:
        import services
        loc = services.get_current_locale()
        if loc and "ru" in str(loc).lower():
            return "ru"
    except Exception:
        pass
    return "en"


DEFAULT_CONFIG = {
    "api_key": "",
    "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "reasoning_effort": "auto",
    "language": get_system_default_language(),
    "temperature": 0.75,
    "max_tokens": 1500,
    "autonomy_enabled": False,
    "autonomy_interval": 240,
    "context_flags": {
        "fame": True,         # Слава и репутация
        "pregnancy": True,    # Беременность и родительство
        "family": True,       # Семья и родственники
        "nearby": True,       # Окружающие персонажи
        "social": True,       # Диалоги и стиль общения
        "clothing": True,     # Одежда и уровень раздевания
        "weather": True,      # Погода и время года
        "world_time": True,   # Время в игре и праздники
        "location": True,     # Локация и комната
        "career": True,       # Профессия и карьера
        "aspiration": True,   # Жизненная цель
        "funds": True,        # Бюджет семьи
        "pets": True,         # Домашние питомцы в семье
        "roommates": True,    # Соседи по дому (сожители/друзья)
        "incest": True,       # Теги запретной связи / инцеста
        "memory": True,       # Воспоминания и важные события (эпизодическая память)
    },
    "chat_context_flags": {
        "chat_age_gender": True,    # Возраст и пол
        "chat_occult": True,        # Раса и оккультизм
        "chat_traits": True,        # Черты характера
        "chat_mood": True,          # Текущее настроение
        "chat_location": True,      # Текущая локация
        "chat_lore": True,          # Личная биография / Лор
        "chat_career": True,        # Профессия и карьера
        "chat_aspiration": True,    # Жизненная цель
        "chat_family": True,        # Семья, пара и родственники
        "chat_roommates": True,     # Соседи по дому (сожители/друзья)
        "chat_pets": True,          # Питомцы в семье
        "chat_pregnancy": True,     # Беременность
        "chat_fame": True,          # Слава и репутация
        "chat_funds": True,         # Бюджет семьи
        "chat_relationship": True,  # Отношения между симами
        "chat_incest": True,        # Теги запретной связи / инцеста
        "chat_history": True,       # История переписки
        "chat_memory": True,        # Память о прошлых диалогах (эпизодическая память)
        "summarize_personal": True, # Суммаризация в личных сообщениях
        "summarize_group": True,    # Суммаризация в групповых чатах
        "summarize_direct": True,   # Суммаризация в живых диалогах
    },
    "genealogy_settings": {
        "max_relatives": 100,
        "types": {
            "spouses": True,            # Супруги и постоянная пара (муж, жена, жених, невеста, парень, девушка)
            "children": True,           # Дети (сыновья, дочери, пасынки, падчерицы)
            "parents": True,            # Родители (отец, мать, отчим, мачеха)
            "siblings": True,           # Братья и сестры (родные, сводные)
            "grandparents": True,       # Бабушки и дедушки
            "grandchildren": True,      # Внуки и внучки
            "child_spouses": True,      # Семья детей: Невестка / Зять
            "child_in_laws": True,      # Родственники невестки/зятя (сваты, их братья/сестры)
            "sibling_family": True,     # Семья братьев/сестер (племянники, жены братьев)
            "spouse_in_laws": True,     # Родня со стороны супруга (тесть, тёща, свёкор, свекровь)
            "extended": True,           # Дяди, тети, кузены
            "deceased": True,           # Покойные (умершие) родственники
        }
    },
    "trait_filter_flags": {
        "core": True,             # Основные черты CAS (3 основные черты)
        "aspiration": True,       # Черта за жизненную цель
        "ww_archetypes": True,    # Архетипы личности WickedWhims
        "rewards": True,          # Купленные награды магазина наград
        "ww_traits": True,        # Черты WickedWhims
        "custom_mods": True,      # Черты характера из других модов
    },
    "experimental_flags": {
        "direct_dialogue_pause": True, # Пауза и окно ожидания в живом разговоре
        "alien_male_pregnancy": True, # Определение мужской беременности от инопланетян
        "classic_insane_trait": False, # Классическое безумие для черты «Чудаковатый» (Insane trait behavior)
        "enhanced_world_descriptions": False, # Улучшенное описание городов для нейросети
    },
    "ww_sex_mode": "bed_picker", # Режим интима WickedWhims: bed_picker, nearby_picker, auto_bed, auto_nearby
    "custom_sim_lore": {},
    "autostart_bridge": True,     # Автоматический запуск моста ai_bridge при старте игры
    "bridge_path": "",            # Путь к ai_bridge.exe (если пусто, ищет автоматически)
}

_current_config = None
_last_config_mtime = 0
_recent_thoughts = []


def reload_config() -> dict:
    """Forces reloading the config file from disk."""
    global _current_config, _last_config_mtime
    _current_config = None
    _last_config_mtime = 0
    cfg = load_config(force_reload=True)
    lang_val = cfg.get("language")
    if lang_val:
        try:
            import ai_thought_reader.localization as loc_tr
            loc_tr._CURRENT_LANG = lang_val
        except Exception:
            pass
        try:
            import ai_social_pc.localization as loc_spc
            loc_spc._CURRENT_LANG = lang_val
        except Exception:
            pass
    return cfg


def load_config(force_reload: bool = False) -> dict:
    global _current_config, _last_config_mtime

    file_mtime = 0
    if os.path.isfile(CONFIG_FILE_PATH):
        try:
            file_mtime = os.path.getmtime(CONFIG_FILE_PATH)
        except Exception:
            file_mtime = 0

    if not force_reload and _current_config is not None and file_mtime == _last_config_mtime:
        return _current_config

    config = dict(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
            # Ensure context_flags dictionary has all default keys
            if "context_flags" not in config or not isinstance(config["context_flags"], dict):
                config["context_flags"] = dict(DEFAULT_CONFIG["context_flags"])
            else:
                for k, v in DEFAULT_CONFIG["context_flags"].items():
                    if k not in config["context_flags"]:
                        config["context_flags"][k] = v

            # Ensure chat_context_flags dictionary has all default keys
            if "chat_context_flags" not in config or not isinstance(config["chat_context_flags"], dict):
                config["chat_context_flags"] = dict(DEFAULT_CONFIG["chat_context_flags"])
            else:
                for k, v in DEFAULT_CONFIG["chat_context_flags"].items():
                    if k not in config["chat_context_flags"]:
                        config["chat_context_flags"][k] = v

            # Ensure genealogy_settings dictionary has all default keys
            if "genealogy_settings" not in config or not isinstance(config["genealogy_settings"], dict):
                config["genealogy_settings"] = {
                    "max_relatives": DEFAULT_CONFIG["genealogy_settings"]["max_relatives"],
                    "types": dict(DEFAULT_CONFIG["genealogy_settings"]["types"]),
                }
            else:
                g_cfg = config["genealogy_settings"]
                if "max_relatives" not in g_cfg:
                    g_cfg["max_relatives"] = DEFAULT_CONFIG["genealogy_settings"]["max_relatives"]
                if "types" not in g_cfg or not isinstance(g_cfg["types"], dict):
                    g_cfg["types"] = dict(DEFAULT_CONFIG["genealogy_settings"]["types"])
                else:
                    for tk, tv in DEFAULT_CONFIG["genealogy_settings"]["types"].items():
                        if tk not in g_cfg["types"]:
                            g_cfg["types"][tk] = tv

            # Ensure trait_filter_flags dictionary has all default keys
            if "trait_filter_flags" not in config or not isinstance(config["trait_filter_flags"], dict):
                config["trait_filter_flags"] = dict(DEFAULT_CONFIG["trait_filter_flags"])
            else:
                for k, v in DEFAULT_CONFIG["trait_filter_flags"].items():
                    if k not in config["trait_filter_flags"]:
                        config["trait_filter_flags"][k] = v

            # Ensure experimental_flags dictionary has all default keys
            if "experimental_flags" not in config or not isinstance(config["experimental_flags"], dict):
                config["experimental_flags"] = dict(DEFAULT_CONFIG["experimental_flags"])
            else:
                for k, v in DEFAULT_CONFIG["experimental_flags"].items():
                    if k not in config["experimental_flags"]:
                        config["experimental_flags"][k] = v

            if "custom_sim_lore" not in config or not isinstance(config["custom_sim_lore"], dict):
                config["custom_sim_lore"] = {}

            if "ww_sex_mode" not in config or not config["ww_sex_mode"]:
                config["ww_sex_mode"] = DEFAULT_CONFIG["ww_sex_mode"]
            log("Configuration loaded successfully from disk.")
        except Exception as e:
            log_exception("Failed to load config file", e)
    else:
        save_config(config)

    _last_config_mtime = file_mtime
    _current_config = config
    return _current_config


def save_config(config: dict) -> bool:
    global _current_config, _last_config_mtime
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        _current_config = config
        try:
            _last_config_mtime = os.path.getmtime(CONFIG_FILE_PATH)
        except Exception:
            pass
        log("Configuration saved successfully.")
        return True
    except Exception as e:
        log_exception("Failed to save config file", e)
        return False


def get_active_model() -> str:
    """Returns the currently active AI model depending on the connection mode (Colab, Local, API)."""
    cfg = load_config()
    conn_mode = cfg.get("connection_mode", "api").strip().lower()

    if conn_mode == "colab":
        colab_m = cfg.get("colab_model", "").strip()
        if colab_m:
            return colab_m
    elif conn_mode in ("local", "lmstudio", "ollama"):
        loc_m = cfg.get("local_model", "").strip()
        if loc_m:
            return loc_m
    else:
        api_prov = cfg.get("api_provider", "").strip().lower()
        prov_models = cfg.get("provider_models", {})
        if isinstance(prov_models, dict) and api_prov in prov_models and prov_models[api_prov]:
            return str(prov_models[api_prov]).strip()

    return cfg.get("model", DEFAULT_CONFIG["model"]).strip()


def get_active_provider_info() -> tuple:
    """
    Returns (provider_display_name, active_model_name, connection_mode)
    """
    cfg = load_config()
    conn_mode = cfg.get("connection_mode", "api").strip().lower()

    if conn_mode == "colab":
        model_name = cfg.get("colab_model", "Kobold / Colab").strip()
        return "Kobold AI (Colab)", model_name, "colab"
    elif conn_mode in ("local", "lmstudio", "ollama"):
        loc_eng = cfg.get("local_engine", "Local AI").strip()
        model_name = cfg.get("local_model", "default").strip()
        return f"Локальный ({loc_eng})", model_name, "local"
    else:
        api_prov = cfg.get("api_provider", "api").strip().lower()
        prov_labels = {
            "gemini": "Google AI (Gemini)",
            "openrouter": "OpenRouter",
            "openai": "OpenAI",
            "anthropic": "Anthropic Claude",
            "mistral": "Mistral AI",
        }
        prov_display = prov_labels.get(api_prov, f"API ({api_prov.capitalize()})")
        prov_models = cfg.get("provider_models", {})
        model_name = ""
        if isinstance(prov_models, dict) and api_prov in prov_models:
            model_name = str(prov_models[api_prov]).strip()
        if not model_name:
            model_name = cfg.get("model", DEFAULT_CONFIG["model"]).strip()
        return prov_display, model_name, "api"


def get_api_key() -> str:
    cfg = load_config()
    return cfg.get("api_key", "").strip()


def set_api_key(key: str) -> bool:
    cfg = load_config()
    cfg["api_key"] = key.strip()
    return save_config(cfg)


def get_language() -> str:
    """Returns active language code ('en', 'ru', etc.). Standard default is 'en' unless RU game locale or explicit setting."""
    cfg = load_config()
    lang = cfg.get("language")
    if not lang:
        return get_system_default_language()
    lang_str = str(lang).strip().lower()
    if lang_str in ("ru", "russian", "русский"):
        return "ru"
    if lang_str in ("en", "english", "английский"):
        return "en"
    return lang_str if lang_str else "en"


def set_language(lang: str) -> bool:
    """Saves selected language code to ai_mod_config.json ('en', 'ru', or custom code)."""
    cfg = load_config()
    lang_val = str(lang).strip().lower()
    if lang_val in ("russian", "русский"):
        lang_val = "ru"
    elif lang_val in ("english", "английский"):
        lang_val = "en"
    cfg["language"] = lang_val
    res = save_config(cfg)
    try:
        import ai_thought_reader.localization as loc_tr
        loc_tr._CURRENT_LANG = lang_val
    except Exception:
        pass
    try:
        import ai_social_pc.localization as loc_spc
        loc_spc._CURRENT_LANG = lang_val
    except Exception:
        pass
    return res


def get_model() -> str:
    return get_active_model()


def set_model(model_name: str) -> bool:
    cfg = load_config()
    cfg["model"] = model_name.strip()
    conn_mode = cfg.get("connection_mode", "api").strip().lower()
    if conn_mode == "colab":
        cfg["colab_model"] = model_name.strip()
    elif conn_mode in ("local", "lmstudio", "ollama"):
        cfg["local_model"] = model_name.strip()
    else:
        api_prov = cfg.get("api_provider", "").strip().lower()
        if api_prov:
            if "provider_models" not in cfg or not isinstance(cfg["provider_models"], dict):
                cfg["provider_models"] = {}
            cfg["provider_models"][api_prov] = model_name.strip()
    return save_config(cfg)


def get_reasoning_effort() -> str:
    cfg = load_config()
    return cfg.get("reasoning_effort", "auto").strip().lower()


def set_reasoning_effort(level: str) -> bool:
    cfg = load_config()
    cfg["reasoning_effort"] = level.strip().lower()
    return save_config(cfg)


def get_config_value(key: str, default=None):
    cfg = load_config()
    return cfg.get(key, default)


# Context Flags Management
def get_context_flag(flag_name: str) -> bool:
    cfg = load_config()
    flags = cfg.get("context_flags", {})
    return flags.get(flag_name, DEFAULT_CONFIG["context_flags"].get(flag_name, True))


def set_context_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "context_flags" not in cfg or not isinstance(cfg["context_flags"], dict):
        cfg["context_flags"] = dict(DEFAULT_CONFIG["context_flags"])
    cfg["context_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_context_flag(flag_name: str) -> bool:
    current = get_context_flag(flag_name)
    new_val = not current
    set_context_flag(flag_name, new_val)
    return new_val


def get_all_context_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["context_flags"])
    flags.update(cfg.get("context_flags", {}))
    return flags


# Chat Context Flags Management
def get_chat_context_flag(flag_name: str) -> bool:
    cfg = load_config()
    flags = cfg.get("chat_context_flags", {})
    return flags.get(flag_name, DEFAULT_CONFIG["chat_context_flags"].get(flag_name, True))


def set_chat_context_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "chat_context_flags" not in cfg or not isinstance(cfg["chat_context_flags"], dict):
        cfg["chat_context_flags"] = dict(DEFAULT_CONFIG["chat_context_flags"])
    cfg["chat_context_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_chat_context_flag(flag_name: str) -> bool:
    current = get_chat_context_flag(flag_name)
    new_val = not current
    set_chat_context_flag(flag_name, new_val)
    return new_val


def get_all_chat_context_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["chat_context_flags"])
    flags.update(cfg.get("chat_context_flags", {}))
    return flags


def get_summarize_personal() -> bool:
    return get_chat_context_flag("summarize_personal")


def set_summarize_personal(enabled: bool) -> bool:
    return set_chat_context_flag("summarize_personal", enabled)


def get_summarize_group() -> bool:
    return get_chat_context_flag("summarize_group")


def set_summarize_group(enabled: bool) -> bool:
    return set_chat_context_flag("summarize_group", enabled)


def get_summarize_direct() -> bool:
    return get_chat_context_flag("summarize_direct")


def set_summarize_direct(enabled: bool) -> bool:
    return set_chat_context_flag("summarize_direct", enabled)


# Custom Sim Lore Management (isolated per save file via lore_manager)
def get_custom_sim_lore(sim_id) -> str:
    if not sim_id:
        return ""
    try:
        from ai_thought_reader import lore_manager
        return lore_manager.get_custom_sim_lore(sim_id)
    except Exception as e:
        log_exception("Error in get_custom_sim_lore", e)
        return ""


def set_custom_sim_lore(sim_id, lore_text: str) -> bool:
    if not sim_id:
        return False
    try:
        from ai_thought_reader import lore_manager
        return lore_manager.set_custom_sim_lore(sim_id, lore_text)
    except Exception as e:
        log_exception("Error in set_custom_sim_lore", e)
        return False


def delete_custom_sim_lore(sim_id) -> bool:
    if not sim_id:
        return False
    try:
        from ai_thought_reader import lore_manager
        return lore_manager.delete_custom_sim_lore(sim_id)
    except Exception as e:
        log_exception("Error in delete_custom_sim_lore", e)
        return False


# Recent Thoughts Journal
def add_recent_thought(sim_name: str, thought: str, timestamp_str: str = ""):
    global _recent_thoughts
    import time
    t_str = timestamp_str or time.strftime("%H:%M")
    _recent_thoughts.insert(0, {
        "sim_name": sim_name,
        "thought": thought,
        "time": t_str,
    })
    if len(_recent_thoughts) > 20:
        _recent_thoughts = _recent_thoughts[:20]


def get_recent_thoughts() -> list:
    global _recent_thoughts
    return list(_recent_thoughts)


# Autonomy Settings
def get_autonomy_enabled() -> bool:
    cfg = load_config()
    return bool(cfg.get("autonomy_enabled", False))


def set_autonomy_enabled(enabled: bool) -> bool:
    cfg = load_config()
    cfg["autonomy_enabled"] = bool(enabled)
    return save_config(cfg)


def get_autonomy_interval() -> int:
    cfg = load_config()
    return int(cfg.get("autonomy_interval", 30))


def set_autonomy_interval(minutes: int) -> bool:
    cfg = load_config()
    cfg["autonomy_interval"] = max(5, int(minutes))
    return save_config(cfg)


# =====================================================================
# Genealogy / Family Context Settings
# =====================================================================

def get_genealogy_settings() -> dict:
    cfg = load_config()
    return cfg.get("genealogy_settings", DEFAULT_CONFIG["genealogy_settings"])


def get_genealogy_max_relatives() -> int:
    settings = get_genealogy_settings()
    try:
        val = int(settings.get("max_relatives", 100))
        return max(1, min(500, val))
    except Exception:
        return 100


def set_genealogy_max_relatives(val: int) -> bool:
    try:
        cfg = load_config()
        if "genealogy_settings" not in cfg or not isinstance(cfg["genealogy_settings"], dict):
            cfg["genealogy_settings"] = dict(DEFAULT_CONFIG["genealogy_settings"])
        cfg["genealogy_settings"]["max_relatives"] = max(1, min(500, int(val)))
        return save_config(cfg)
    except Exception as e:
        log_exception("Failed to set genealogy max relatives", e)
        return False


def get_genealogy_type_flag(type_key: str) -> bool:
    settings = get_genealogy_settings()
    types = settings.get("types", {})
    if isinstance(types, dict) and type_key in types:
        return bool(types[type_key])
    return DEFAULT_CONFIG["genealogy_settings"]["types"].get(type_key, True)


def set_genealogy_type_flag(type_key: str, val: bool) -> bool:
    try:
        cfg = load_config()
        if "genealogy_settings" not in cfg or not isinstance(cfg["genealogy_settings"], dict):
            cfg["genealogy_settings"] = dict(DEFAULT_CONFIG["genealogy_settings"])
        if "types" not in cfg["genealogy_settings"] or not isinstance(cfg["genealogy_settings"]["types"], dict):
            cfg["genealogy_settings"]["types"] = dict(DEFAULT_CONFIG["genealogy_settings"]["types"])
        cfg["genealogy_settings"]["types"][type_key] = bool(val)
        return save_config(cfg)
    except Exception as e:
        log_exception(f"Failed to set genealogy type flag {type_key}", e)
        return False


def toggle_genealogy_type_flag(type_key: str) -> bool:
    cur = get_genealogy_type_flag(type_key)
    set_genealogy_type_flag(type_key, not cur)
    return not cur


# =====================================================================
# Trait Filter Settings
# =====================================================================

def get_trait_filter_flag(flag_name: str) -> bool:
    cfg = load_config()
    flags = cfg.get("trait_filter_flags", {})
    return bool(flags.get(flag_name, DEFAULT_CONFIG["trait_filter_flags"].get(flag_name, True)))


def set_trait_filter_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "trait_filter_flags" not in cfg or not isinstance(cfg["trait_filter_flags"], dict):
        cfg["trait_filter_flags"] = dict(DEFAULT_CONFIG["trait_filter_flags"])
    cfg["trait_filter_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_trait_filter_flag(flag_name: str) -> bool:
    current = get_trait_filter_flag(flag_name)
    new_val = not current
    set_trait_filter_flag(flag_name, new_val)
    return new_val


def get_all_trait_filter_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["trait_filter_flags"])
    flags.update(cfg.get("trait_filter_flags", {}))
    return flags


# =====================================================================
# Experimental Settings
# =====================================================================

def get_experimental_flag(flag_name: str) -> bool:
    cfg = load_config()
    flags = cfg.get("experimental_flags", {})
    return bool(flags.get(flag_name, DEFAULT_CONFIG["experimental_flags"].get(flag_name, False)))


def set_experimental_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "experimental_flags" not in cfg or not isinstance(cfg["experimental_flags"], dict):
        cfg["experimental_flags"] = dict(DEFAULT_CONFIG["experimental_flags"])
    cfg["experimental_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_experimental_flag(flag_name: str) -> bool:
    current = get_experimental_flag(flag_name)
    new_val = not current
    set_experimental_flag(flag_name, new_val)
    return new_val


def get_all_experimental_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["experimental_flags"])
    flags.update(cfg.get("experimental_flags", {}))
    return flags


# =====================================================================
# WickedWhims Sex Mode Settings
# =====================================================================

def get_ww_sex_mode() -> str:
    """Returns the current WW sex action mode: 'bed_picker', 'nearby_picker', 'auto_bed', 'auto_nearby'."""
    cfg = load_config()
    return cfg.get("ww_sex_mode", DEFAULT_CONFIG.get("ww_sex_mode", "bed_picker"))


def set_ww_sex_mode(mode: str) -> bool:
    """Sets the WW sex action mode."""
    cfg = load_config()
    cfg["ww_sex_mode"] = str(mode)
    return save_config(cfg)
