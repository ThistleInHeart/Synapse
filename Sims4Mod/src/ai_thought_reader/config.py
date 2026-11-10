import os
import json
from typing import List, Dict, Any, Optional, Tuple, Set
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


DEFAULT_MULTISIM_RULES_RU = {
    "group_chat": "- ЭТО ГРУППОВОЙ ДИАЛОГ! Все перечисленные персонажи общаются вместе в одной компании. Если реплика обращена ко всем («привет девочки», «как вы?», «народ», вопрос к компании) или касается присутствующих — другие участники разговора ОБЯЗАТЕЛЬНО подхватывают беседу через разделитель «///» со своими ответами по очереди! (Формат: Ответ первого собеседника [FR=...] [ROM=...] /// Имя: Ответ второго собеседника [FR=...] [ROM=...]). Если фраза адресована строго одному по имени («Мимси, поцелуй меня») — отвечает только адресат.",
    "bystander": "- Персонаж рядом встревает ИСКЛЮЧИТЕЛЬНО РЕДКО (через «///» или [JOIN=...]) — только если назвали его имя («Эй, Данте!»), задели его лично/семью или прямо обратились к нему. В обычных разговорах между собеседниками персонаж рядом молча занимается своими делами и НЕ встревает!",
    "sex_group": "- ЭТО СОВМЕСТНЫЙ ИНТИМНЫЙ АКТ (ГРУППОВОЙ СЕКС / СЕКС ВТРОЁМ И Т.Д.)! Все перечисленные персонажи находятся в процессе близости вместе с вами. Если реплика обращена ко всем участникам («как вам?», «девочки...», стон или вопрос к участникам) или касается происходящего — другие участники интима ОБЯЗАТЕЛЬНО подхватывают разговор через разделитель «///» со своими реакциями, стонами, репликами и тегами! (Формат: Ответ первого партнера [FR=...] [ROM=...] /// Имя: Ответ второго партнера [FR=...] [ROM=...]). Опционально разрешены [DO=stop_sex] (прервать секс) и [SUM=...|Day=N] (важное воспоминание).",
    "sex_bystander": "- Персонаж находится рядом в комнате как свидетель или наблюдатель. Свидетель встревает ИСКЛЮЧИТЕЛЬНО РЕДКО (через «///») — только если заговорили прямо с ним, назвали его имя или задели его лично. В обычных интимных репликах участников между собой свидетель МОЛЧИТ и не встревает! Если свидетель вступает в разговор и согласен присоединиться, он может использовать [DO=join_sex], а если возмущен — потребовать прекратить [DO=stop_sex].",
}

DEFAULT_MULTISIM_RULES_EN = {
    "group_chat": "- THIS IS AN ACTIVE GROUP CHAT! All listed Sims are in this circle together. If addressed to everyone ('hello girls', 'how are you guys?') or relevant to the group, other participants ALWAYS chime in via '///' separator with their replies in order (Format: Primary reply [FR=...] [ROM=...] /// Name: Second reply [FR=...] [ROM=...]).",
    "bystander": "- A bystander chimes in ONLY OCCASIONALLY via '///' or [JOIN=...] if directly addressed by name, provoked, or personally affected. Otherwise they quietly continue their own business and DO NOT chime in.",
    "sex_group": "- THIS IS A SHARED INTIMATE SCENE (GROUP SEX / THREESOME)! All listed Sims are actively involved together in intimacy. If words are directed to everyone or describe what's happening, other partners ALWAYS chime in via '///' separator with their reactions, moans, and tags (Format: Primary reply [FR=...] [ROM=...] /// Name: Second reply [FR=...]).",
    "sex_bystander": "- Bystander is in the room observing. Bystander speaks EXCEPTIONALLY RARELY (via '///') — only if addressed directly by name or provoked. In normal talk between intimate partners, bystander stays SILENT and does not interrupt! May use [DO=join_sex] if joining or [DO=stop_sex] if outraged.",
}

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
        "name": True,
        "age_gender": True,
        "occult": True,
        "traits": True,
        "lore": True,
        "aspiration": True,
        "mood": True,
        "needs": True,
        "activity": True,
        "clothing": True,
        "nudity": True,
        "pregnancy": True,
        "world_time": True,
        "weather": True,
        "events": True,
        "location": True,
        "emergencies": True,
        "nearby": True,
        "family": True,
        "roommates": True,
        "livein_staff": True,
        "pets": True,
        "social": True,
        "incest": True,
        "recent_dialogs": True,
        "memory": True,
        "career": True,
        "education": True,
        "funds": True,
        "fame": True,
        "clubs": True,
        "trapped_status": False,
        "last_thought": False,
    },
    "direct_dialogue_flags": {
        "dd_witnesses": True,
        "dd_location": True,
        "dd_weather_time": True,
        "dd_events": True,
        "dd_profiles": True,
        "dd_traits": True,
        "dd_mood": True,
        "dd_lore": True,
        "dd_activity": True,
        "dd_clothing": True,
        "dd_relationship": True,
        "dd_family": True,
        "dd_memories": True,
        "dd_business": True,
        "dd_taboo": True,
    },
    "intimate_dialogue_flags": {
        "id_pose": True,
        "id_partners": True,
        "id_privacy": True,
        "id_observers": True,
        "id_attire": True,
        "id_relationship": True,
        "id_traits": True,
        "id_tone": True,
        "id_taboo": True,
        "id_pregnancy": True,
        "id_venue": True,
        "id_memories": True,
    },
    "chat_context_flags": {
        "chat_age_gender": True,
        "chat_occult": True,
        "chat_traits": True,
        "chat_mood": True,
        "chat_location": True,
        "chat_lore": True,
        "chat_career": True,
        "chat_aspiration": True,
        "chat_family": True,
        "chat_roommates": True,
        "chat_livein_staff": True,
        "chat_pets": True,
        "chat_pregnancy": True,
        "chat_fame": True,
        "chat_funds": True,
        "chat_relationship": True,
        "chat_incest": True,
        "chat_history": True,
        "chat_memory": True,
        "chat_clubs": True,
        "chat_clothing": True,
        "chat_nearby": True,
        "chat_activity": True,
        "summarize_personal": True,
        "summarize_group": True,
        "summarize_direct": True,
        "recent_dialogs": True,
        "emergencies": True,
        "needs": True,
    },
    "genealogy_settings": {
        "max_relatives": 100,
        "max_depth": 10,
        "types": {
            "spouses": True,            # Супруги и постоянная пара (муж, жена, жених, невеста, парень, девушка)
            "ex_partners": True,        # Бывшие партнеры (бывший муж, бывшая жена, бывший жених/невеста, бывший парень/девушка, вдовство)
            "ex_in_laws": True,         # Родственники бывших партнеров (родители, братья/сестры, дети, новые супруги)
            "children": True,           # Дети (сыновья, дочери, пасынки, падчерицы)
            "parents": True,            # Родители (отец, мать, отчим, мачеха)
            "siblings": True,           # Братья и сестры (родные, сводные)
            "grandparents": True,       # Бабушки и дедушки
            "grandchildren": True,      # Внуки и внучки
            "ancestors_extended": True, # Прадедушки, прабабушки и предки 3+ поколений
            "descendants_extended": True,# Правнуки, правнучки и потомки 3+ поколений
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
        "direct_dialogue_pause": True,
        "direct_dialogue_multisim_join": True,
        "direct_dialogue_approach_first": True, # Пауза и окно ожидания в живом разговоре
        "alien_male_pregnancy": True, # Определение мужской беременности от инопланетян
        "classic_insane_trait": False, # Классическое безумие для черты «Чудаковатый» (Insane trait behavior)
        "enhanced_world_descriptions": True, # Улучшенное описание городов для нейросети
        "home_business_context": False, # Контекст домашнего и малого бизнеса («Любимое дело» / Get to Work)
        "dynamic_interaction_ui_fallback": False,
        "overheard_conversations": False,
        "third_party_dossier": False,
        "trapped_sim_detection": False,
        "last_thought_context": False,
    },
    "multisim_rules": {},
    "simplified_dialogue_settings": {
        "enabled": False,
        "silence_sec": 180,
        "trigger_chance_pct": 40,
        "balloon": True,
        "notification": False,
    },
    "director_settings": {
        "enabled": False,
        "disabled_triggers": [],
        "timers": {
            "household_silence_sec": 240,
            "pair_cooldown_sec": 450,
            "grace_period_sec": 60,
        },
        "trigger_overrides": {},
    },
    "display_settings": {
        "thought_balloon": True,
        "thought_notification": True,
        "direct_balloon": True,
        "direct_notification": True,
        "director_balloon": True,
        "director_notification": False,
    },
    "balloon_style": {
        "scale_pct": 100,
        "max_width": 260,
        "font_size": 15,
        "leading": 4,
        "show_name": True,
        "name_font_size": 11,
        "pad_x": 16,
        "pad_y": 13,
        "radius": 15,
        "offset_y": 32,
        "offset_x": 0,
        "camera_scale": True,
        "min_scale_pct": 35,
        "bg_alpha_pct": 98,
        "theme": "light",
        "type_speed": 35,
        "duration_pct": 100,
    },

    "ww_sex_mode": "bed_picker", # Режим интима WickedWhims: bed_picker, nearby_picker, auto_bed, auto_nearby
    "event_memory_enabled": True,       # Автоматическая память событий (Вуху, измены, свадьбы, драки и т.д.)
    "dialogue_memory_hours": 24,        # Срок памяти недавних диалогов в часах (24..999, 0 = без ограничений)
    "custom_sim_lore": {},
    "age_instructions_enabled": False,
    "special_situations_enabled": False,
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

            for dict_key in ("direct_dialogue_flags", "intimate_dialogue_flags"):
                if dict_key not in config or not isinstance(config[dict_key], dict):
                    config[dict_key] = dict(DEFAULT_CONFIG[dict_key])
                else:
                    for k, v in DEFAULT_CONFIG[dict_key].items():
                        if k not in config[dict_key]:
                            config[dict_key][k] = v

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

            if "multisim_rules" not in config or not isinstance(config["multisim_rules"], dict):
                config["multisim_rules"] = {}

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
    return flags.get(flag_name, DEFAULT_CONFIG["context_flags"].get(flag_name, False if flag_name in ("trapped_status", "last_thought") else True))


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


# Unified Legacy Mapping (routes legacy chat_* flags to the single unified context_flags)

LEGACY_DD_TO_UNIFIED_MAP = {
    "dd_witnesses": "nearby",
    "dd_weather_time": "weather",
    "dd_location": "location",
    "dd_memories": "memory",
    "dd_events": "events",
    "dd_business": "business",
    "dd_relationship": "social",
    "id_pose": "activity",
    "id_partners": "activity",
    "id_privacy": "activity",
    "id_observers": "nearby",
}

LEGACY_CHAT_TO_UNIFIED_MAP = {
    "chat_age_gender": "age_gender",
    "chat_occult": "occult",
    "chat_traits": "traits",
    "chat_mood": "mood",
    "chat_location": "location",
    "chat_lore": "lore",
    "chat_career": "career",
    "chat_aspiration": "aspiration",
    "chat_family": "family",
    "chat_roommates": "roommates",
    "chat_livein_staff": "livein_staff",
    "chat_pets": "pets",
    "chat_pregnancy": "pregnancy",
    "chat_fame": "fame",
    "chat_funds": "funds",
    "chat_relationship": "social",
    "chat_incest": "incest",
    "chat_history": "recent_dialogs",
    "chat_memory": "memory",
    "chat_clubs": "clubs",
    "chat_clothing": "clothing",
    "chat_nearby": "nearby",
    "chat_activity": "activity",
}


# Chat Context Flags Management (delegates to unified context_flags except summarization keys)
def get_chat_context_flag(flag_name: str) -> bool:
    if flag_name in LEGACY_CHAT_TO_UNIFIED_MAP:
        return get_context_flag(LEGACY_CHAT_TO_UNIFIED_MAP[flag_name])
    if flag_name in DEFAULT_CONFIG["context_flags"] and flag_name not in DEFAULT_CONFIG["chat_context_flags"]:
        # Unified flag used directly (needs, emergencies, memory, recent_dialogs, ...)
        return get_context_flag(flag_name)
    cfg = load_config()
    flags = cfg.get("chat_context_flags", {})
    return flags.get(flag_name, DEFAULT_CONFIG["chat_context_flags"].get(flag_name, True))


def set_chat_context_flag(flag_name: str, enabled: bool) -> bool:
    if flag_name in LEGACY_CHAT_TO_UNIFIED_MAP:
        set_context_flag(LEGACY_CHAT_TO_UNIFIED_MAP[flag_name], enabled)
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


def get_direct_dialogue_flag(flag_name: str) -> bool:
    unified_key = LEGACY_DD_TO_UNIFIED_MAP.get(flag_name, flag_name)
    return get_context_flag(unified_key)


def set_direct_dialogue_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "direct_dialogue_flags" not in cfg or not isinstance(cfg["direct_dialogue_flags"], dict):
        cfg["direct_dialogue_flags"] = dict(DEFAULT_CONFIG["direct_dialogue_flags"])
    cfg["direct_dialogue_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_direct_dialogue_flag(flag_name: str) -> bool:
    current = get_direct_dialogue_flag(flag_name)
    new_val = not current
    set_direct_dialogue_flag(flag_name, new_val)
    return new_val


def get_all_direct_dialogue_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["direct_dialogue_flags"])
    flags.update(cfg.get("direct_dialogue_flags", {}))
    return flags


def get_intimate_dialogue_flag(flag_name: str) -> bool:
    unified_key = LEGACY_DD_TO_UNIFIED_MAP.get(flag_name, flag_name)
    return get_context_flag(unified_key)


def set_intimate_dialogue_flag(flag_name: str, enabled: bool) -> bool:
    cfg = load_config()
    if "intimate_dialogue_flags" not in cfg or not isinstance(cfg["intimate_dialogue_flags"], dict):
        cfg["intimate_dialogue_flags"] = dict(DEFAULT_CONFIG["intimate_dialogue_flags"])
    cfg["intimate_dialogue_flags"][flag_name] = bool(enabled)
    return save_config(cfg)


def toggle_intimate_dialogue_flag(flag_name: str) -> bool:
    current = get_intimate_dialogue_flag(flag_name)
    new_val = not current
    set_intimate_dialogue_flag(flag_name, new_val)
    return new_val


def get_all_intimate_dialogue_flags() -> dict:
    cfg = load_config()
    flags = dict(DEFAULT_CONFIG["intimate_dialogue_flags"])
    flags.update(cfg.get("intimate_dialogue_flags", {}))
    return flags


MODE_TO_CONFIG_KEY = {
    "thought": "context_flags",
    "messenger": "chat_context_flags",
    "direct": "direct_dialogue_flags",
    "intimate": "intimate_dialogue_flags",
}


def set_mode_context_flag(mode: str, flag_name: str, enabled: bool) -> bool:
    mode_str = str(mode).strip().lower()
    if mode_str == "messenger":
        return set_chat_context_flag(flag_name, enabled)
    elif mode_str == "direct":
        return set_direct_dialogue_flag(flag_name, enabled)
    elif mode_str == "intimate":
        return set_intimate_dialogue_flag(flag_name, enabled)
    else:
        return set_context_flag(flag_name, enabled)


def set_bulk_mode_context_flags(mode: str, action: str) -> bool:
    mode_str = str(mode).strip().lower()
    sec = MODE_TO_CONFIG_KEY.get(mode_str, "context_flags")
    cfg = load_config()
    defaults = DEFAULT_CONFIG.get(sec, {})
    if action in ("all_on", "enable_all"):
        cfg[sec] = {k: True for k in defaults}
    elif action in ("all_off", "disable_all"):
        cfg[sec] = {k: False for k in defaults}
    else:
        cfg[sec] = dict(defaults)
    return save_config(cfg)


def get_packed_context_state_str() -> str:
    cfg = load_config()
    all_flags = {}
    for sec in ("context_flags", "chat_context_flags", "direct_dialogue_flags", "intimate_dialogue_flags"):
        d = dict(DEFAULT_CONFIG.get(sec, {}))
        d.update(cfg.get(sec, {}))
        all_flags.update(d)
    parts = [f"{k}:{'1' if v else '0'}" for k, v in all_flags.items()]
    return ";".join(parts)



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


def get_genealogy_max_depth() -> int:
    settings = get_genealogy_settings()
    try:
        val = int(settings.get("max_depth", 10))
        if val == 0 or val >= 99:
            return 999
        return max(2, min(50, val))
    except Exception:
        return 10


def set_genealogy_max_depth(val: int) -> bool:
    try:
        cfg = load_config()
        if "genealogy_settings" not in cfg or not isinstance(cfg["genealogy_settings"], dict):
            cfg["genealogy_settings"] = dict(DEFAULT_CONFIG["genealogy_settings"])
        v = int(val)
        if v == 0 or v >= 99:
            cfg["genealogy_settings"]["max_depth"] = 0
        else:
            cfg["genealogy_settings"]["max_depth"] = max(2, min(50, v))
        return save_config(cfg)
    except Exception as e:
        log_exception("Failed to set genealogy max depth", e)
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


def get_all_genealogy_type_flags() -> dict:
    settings = get_genealogy_settings()
    types = dict(DEFAULT_CONFIG["genealogy_settings"]["types"])
    if isinstance(settings.get("types"), dict):
        types.update(settings["types"])
    return types


def set_bulk_genealogy_flags(action: str) -> bool:
    try:
        cfg = load_config()
        if "genealogy_settings" not in cfg or not isinstance(cfg["genealogy_settings"], dict):
            cfg["genealogy_settings"] = dict(DEFAULT_CONFIG["genealogy_settings"])
        defaults = DEFAULT_CONFIG["genealogy_settings"]["types"]
        act = str(action).strip().lower()
        if act in ("all_on", "enable_all"):
            cfg["genealogy_settings"]["types"] = {k: True for k in defaults}
        elif act in ("all_off", "disable_all"):
            cfg["genealogy_settings"]["types"] = {k: False for k in defaults}
        else: # default / reset
            cfg["genealogy_settings"]["types"] = dict(defaults)
            cfg["genealogy_settings"]["max_depth"] = DEFAULT_CONFIG["genealogy_settings"]["max_depth"]
            cfg["genealogy_settings"]["max_relatives"] = DEFAULT_CONFIG["genealogy_settings"]["max_relatives"]
        return save_config(cfg)
    except Exception as e:
        log_exception(f"Failed to bulk update genealogy flags {action}", e)
        return False


def get_packed_genealogy_state_str() -> str:
    try:
        types = get_all_genealogy_type_flags()
        depth = get_genealogy_max_depth()
        max_rel = get_genealogy_max_relatives()
        parts = [f"depth:{depth}", f"max_relatives:{max_rel}"]
        for k, v in types.items():
            parts.append(f"{k}:{'1' if v else '0'}")
        return ";".join(parts)
    except Exception as e:
        log_exception("Failed to get packed genealogy state string", e)
        return "depth:10;max_relatives:100"


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
# =====================================================================
# Direct Dialogue Multisim Rules (Customizable Prompts)
# =====================================================================

def get_default_multisim_rule(rule_key: str, is_en: bool = False) -> str:
    rules = DEFAULT_MULTISIM_RULES_EN if is_en else DEFAULT_MULTISIM_RULES_RU
    return rules.get(rule_key, "")


def get_multisim_rule(rule_key: str, is_en: bool = False) -> str:
    if not rule_key:
        return ""
    try:
        cfg = load_config()
        custom_rules = cfg.get("multisim_rules", {})
        if isinstance(custom_rules, dict) and rule_key in custom_rules:
            val = custom_rules[rule_key]
            if val and str(val).strip():
                return str(val).strip()
    except Exception as e:
        log_exception(f"Error reading multisim rule {rule_key}", e)
    return get_default_multisim_rule(rule_key, is_en)


def set_multisim_rule(rule_key: str, text: str) -> bool:
    if not rule_key:
        return False
    try:
        cfg = load_config()
        if "multisim_rules" not in cfg or not isinstance(cfg["multisim_rules"], dict):
            cfg["multisim_rules"] = {}
        cfg["multisim_rules"][str(rule_key).strip()] = str(text).strip()
        return save_config(cfg)
    except Exception as e:
        log_exception(f"Error saving multisim rule {rule_key}", e)
        return False


def reset_multisim_rules(rule_key: Optional[str] = None) -> bool:
    try:
        cfg = load_config()
        if "multisim_rules" not in cfg or not isinstance(cfg["multisim_rules"], dict):
            return True
        if rule_key:
            rk = str(rule_key).strip()
            if rk in cfg["multisim_rules"]:
                del cfg["multisim_rules"][rk]
                return save_config(cfg)
            return True
        else:
            cfg["multisim_rules"] = {}
            return save_config(cfg)
    except Exception as e:
        log_exception(f"Error resetting multisim rules", e)
        return False


def get_all_multisim_rules(is_en: bool = False) -> Dict[str, str]:
    keys = ["group_chat", "bystander", "sex_group", "sex_bystander"]
    return {k: get_multisim_rule(k, is_en) for k in keys}


# Experimental Settings
# =====================================================================

def get_experimental_flag(flag_name: str) -> bool:
    if str(flag_name).strip() == "enhanced_world_descriptions":
        return True
    cfg = load_config()
    flags = cfg.get("experimental_flags", {})
    return bool(flags.get(flag_name, DEFAULT_CONFIG["experimental_flags"].get(flag_name, False)))


def get_packed_experimental_state_str() -> str:
    """Returns packed string for experimental feature flags."""
    dyn_act = 1 if get_experimental_flag("dynamic_interaction_ui_fallback") else 0
    biz = 1 if get_experimental_flag("home_business_context") else 0
    pause = 1 if get_experimental_flag("direct_dialogue_pause") else 0
    alien = 1 if get_experimental_flag("alien_male_pregnancy") else 0
    insane = 1 if get_experimental_flag("classic_insane_trait") else 0
    overheard = 1 if get_experimental_flag("overheard_conversations") else 0
    dossier = 1 if get_experimental_flag("third_party_dossier") else 0
    trapped = 1 if get_experimental_flag("trapped_sim_detection") else 0
    last_th = 1 if get_experimental_flag("last_thought_context") else 0
    multisim = 1 if get_experimental_flag("direct_dialogue_multisim_join") else 0
    appr = 1 if get_experimental_flag("direct_dialogue_approach_first") else 0
    return f"dyn_act:{dyn_act};biz:{biz};pause:{pause};alien:{alien};insane:{insane};overheard:{overheard};dossier:{dossier};trapped:{trapped};last_th:{last_th};multisim:{multisim};appr:{appr}"


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


def get_packed_mods_state_str() -> str:
    """Returns packed string for third-party mod integrations."""
    mode = get_ww_sex_mode()
    return f"ww_mode:{mode}"


# =====================================================================
# Display & Notification Settings (Balloons & Notifications)
# =====================================================================

def get_display_flag(flag_name: str, default: bool = True) -> bool:
    """Returns whether a specific balloon or notification is enabled."""
    cfg = load_config()
    disp = cfg.get("display_settings")
    if isinstance(disp, dict) and flag_name in disp:
        return bool(disp[flag_name])
    def_disp = DEFAULT_CONFIG.get("display_settings", {})
    return bool(def_disp.get(flag_name, default))


def set_display_flag(flag_name: str, enabled: bool) -> bool:
    """Sets a specific balloon or notification flag."""
    cfg = load_config()
    if "display_settings" not in cfg or not isinstance(cfg["display_settings"], dict):
        cfg["display_settings"] = dict(DEFAULT_CONFIG.get("display_settings", {}))
    cfg["display_settings"][str(flag_name).strip()] = bool(enabled)
    return save_config(cfg)


def get_packed_display_state_str() -> str:
    """Returns packed string for display and notification settings."""
    th_b = 1 if get_display_flag("thought_balloon", True) else 0
    th_n = 1 if get_display_flag("thought_notification", True) else 0
    dir_b = 1 if get_display_flag("direct_balloon", True) else 0
    dir_n = 1 if get_display_flag("direct_notification", True) else 0
    dtr_b = 1 if get_display_flag("director_balloon", True) else 0
    dtr_n = 1 if get_display_flag("director_notification", False) else 0
    return f"th_bal:{th_b};th_notif:{th_n};dir_bal:{dir_b};dir_notif:{dir_n};dtr_bal:{dtr_b};dtr_notif:{dtr_n}"


# =====================================================================
# Balloon Style & Studio Settings
# =====================================================================

def get_balloon_style() -> dict:
    """Returns the custom balloon visual appearance and animation parameters."""
    cfg = load_config()
    bs = cfg.get("balloon_style")
    def_bs = dict(DEFAULT_CONFIG.get("balloon_style", {}))
    if isinstance(bs, dict):
        def_bs.update(bs)
    return def_bs


def set_balloon_style(style_dict: dict) -> bool:
    """Updates balloon style settings in config."""
    cfg = load_config()
    cur = get_balloon_style()
    if isinstance(style_dict, dict):
        cur.update(style_dict)
    cfg["balloon_style"] = cur
    return save_config(cfg)


def reset_balloon_style() -> bool:
    """Resets balloon style settings to defaults."""
    cfg = load_config()
    cfg["balloon_style"] = dict(DEFAULT_CONFIG.get("balloon_style", {}))
    return save_config(cfg)


def get_packed_balloon_style_str() -> str:
    """Returns packed string of balloon style parameters for Flash UI."""
    bs = get_balloon_style()
    keys = (
        "scale_pct", "max_width", "font_size", "leading", "show_name",
        "name_font_size", "pad_x", "pad_y", "radius", "offset_y",
        "offset_x", "camera_scale", "min_scale_pct", "bg_alpha_pct",
        "theme", "type_speed", "duration_pct"
    )
    parts = []
    for k in keys:
        v = bs.get(k, DEFAULT_CONFIG["balloon_style"].get(k, 0))
        if isinstance(v, bool):
            parts.append(f"{k}:{1 if v else 0}")
        else:
            parts.append(f"{k}:{v}")
    return ";".join(parts)


# =====================================================================
# Memory Settings (Event Memory & Dialogue Memory Retention)
# =====================================================================

def get_event_memory_enabled() -> bool:
    cfg = load_config()
    return bool(cfg.get("event_memory_enabled", DEFAULT_CONFIG.get("event_memory_enabled", True)))


def set_event_memory_enabled(val: bool) -> bool:
    try:
        cfg = load_config()
        cfg["event_memory_enabled"] = bool(val)
        return save_config(cfg)
    except Exception as e:
        log_exception("Failed to set event_memory_enabled", e)
        return False


def get_dialogue_memory_hours() -> int:
    cfg = load_config()
    try:
        val = int(cfg.get("dialogue_memory_hours", DEFAULT_CONFIG.get("dialogue_memory_hours", 24)))
        if val == 0 or val >= 999:
            return 999
        return max(1, val)
    except Exception:
        return 24


def set_dialogue_memory_hours(val: int) -> bool:
    try:
        cfg = load_config()
        v = int(val)
        if v == 0 or v >= 999:
            cfg["dialogue_memory_hours"] = 0
        else:
            cfg["dialogue_memory_hours"] = max(1, v)
        return save_config(cfg)
    except Exception as e:
        log_exception("Failed to set dialogue_memory_hours", e)
        return False


def get_packed_memory_state_str() -> str:
    cfg = load_config()
    ev_mem = 1 if get_event_memory_enabled() else 0
    raw_hours = int(cfg.get("dialogue_memory_hours", 24))
    diag_hours = raw_hours
    sum_pers = 1 if get_chat_context_flag("summarize_personal") else 0
    sum_grp = 1 if get_chat_context_flag("summarize_group") else 0
    return f"ev_mem:{ev_mem};diag_hours:{diag_hours};sum_pers:{sum_pers};sum_grp:{sum_grp}"


# =====================================================================
# Director Settings & Per-Location Scenario Flags
# =====================================================================

def get_director_enabled() -> bool:
    """Returns whether the Autonomous Director is enabled globally."""
    cfg = load_config()
    dtr = cfg.get("director_settings")
    if isinstance(dtr, dict) and "enabled" in dtr:
        return bool(dtr["enabled"])
    return bool(DEFAULT_CONFIG.get("director_settings", {}).get("enabled", False))


def set_director_enabled(enabled: bool) -> bool:
    """Sets whether the Autonomous Director is enabled globally."""
    if enabled and get_simplified_dialogue_enabled():
        log("[MUTUAL_EXCLUSIVE] Cannot enable Director: Simplified Autonomous Dialogue is already active!")
        return False
    cfg = load_config()
    if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
        cfg["director_settings"] = dict(DEFAULT_CONFIG.get("director_settings", {}))
    cfg["director_settings"]["enabled"] = bool(enabled)
    return save_config(cfg)


def get_director_disabled_triggers() -> list:
    """Returns list of disabled scenario trigger keys, e.g. ['community_fire_hazard']."""
    cfg = load_config()
    dtr = cfg.get("director_settings")
    if isinstance(dtr, dict) and "disabled_triggers" in dtr:
        dis = dtr["disabled_triggers"]
        if isinstance(dis, (list, tuple, set)):
            return [str(k) for k in dis]
    return []


DIRECTOR_TRIGGER_ALIASES = {
    "burnt_food": ["cooking_burnt", "burnt_food"],
    "cooking_burnt": ["cooking_burnt", "burnt_food"],
    "cooking_masterpiece": ["cooking_masterpiece", "eating_together", "cooking_together"],
    "eating_together": ["cooking_masterpiece", "hunger_starving", "eating_together"],
    "cooking_together": ["cooking_masterpiece", "cooking_together"],
    "broken_object": ["object_broke", "broken_object"],
    "object_broke": ["object_broke", "broken_object"],
    "repair_success": ["repair_success", "service_repairman_done"],
    "service_repairman_done": ["repair_success", "repairman_arrival", "service_repairman_done"],
    "electrocuted_repair": ["object_broke", "repair_success", "electrocuted_repair"],
    "dirty_dish_trash": ["dirt_mess", "dirty_dish_trash"],
    "dirt_mess": ["dirt_mess", "dirty_dish_trash"],
    "clean_house": ["clean_house", "maid_arrival", "service_maid_cleaning"],
    "service_maid_cleaning": ["clean_house", "maid_arrival", "service_maid_cleaning"],
    "morning_wake": ["morning_wake", "morning_coffee"],
    "morning_coffee": ["morning_wake", "morning_coffee"],
    "night_sleep": ["night_sleep", "bedtime_pillow_talk", "late_night_awake"],
    "bedtime_pillow_talk": ["night_sleep", "bedtime_pillow_talk"],
    "late_night_awake": ["night_sleep", "late_night_awake"],
    "relaxing_bath": ["relaxing_bath"],
    "bill_arrived": ["bill_arrived", "paid_bills"],
    "paid_bills": ["paid_bills", "bill_arrived"],
    "low_energy": ["low_energy", "night_sleep", "bedtime_pillow_talk"],
    "hunger_starving": ["hunger_starving", "eating_together"],
    "garden_harvest": ["garden_harvest", "gardening_together"],
    "gardening_together": ["garden_harvest", "gardening_together"],
    "spoiled_food": ["spoiled_food", "dirt_mess"],
    "guest_knock": ["guest_knock", "guest_arrival_greeting", "guest_home_door_greeting", "neighbor_door_knock", "neighbor_welcome_wagon"],
    "welcomed_guest": ["welcomed_guest", "guest_arrival_greeting", "relative_warm_welcome"],
    "guest_arrival_greeting": ["guest_knock", "welcomed_guest", "guest_arrival_greeting"],
    "guest_home_door_greeting": ["guest_knock", "welcomed_guest", "guest_home_door_greeting"],
    "neighbor_door_knock": ["guest_knock", "neighbor_door_knock"],
    "neighbor_welcome_wagon": ["guest_knock", "neighbor_welcome_wagon"],
    "maid_arrival": ["maid_arrival", "service_maid_cleaning"],
    "repairman_arrival": ["repairman_arrival", "service_repairman_done"],
    "nanny_arrival": ["nanny_arrival", "service_nanny_chat"],
    "service_nanny_chat": ["nanny_arrival", "service_nanny_chat"],
    "gardener_arrival": ["gardener_arrival"],
    "delivery_food": ["delivery_food"],
    "fire_hazard": ["fire_hazard"],
    "burglar_theft": ["burglar_theft"],
    "grim_reaper_death": ["grim_reaper_death", "witness_death"],
    "witness_death": ["grim_reaper_death", "witness_death"],
    "cheating_caught": ["cheating_caught", "caught_cheating", "witnessed_cheating", "walk_in_intimacy"],
    "caught_cheating": ["cheating_caught", "caught_cheating"],
    "witnessed_cheating": ["cheating_caught", "witnessed_cheating"],
    "walk_in_intimacy": ["cheating_caught", "walk_in_intimacy"],
    "breakup_divorce": ["breakup_divorce"],
    "sudden_fight": ["sudden_fight"],
    "fight_lost": ["fight_lost"],
    "fight_won": ["fight_won"],
    "prank_backfire": ["prank_backfire"],
    "bladder_emergency": ["bladder_emergency"],
    "hygiene_emergency": ["hygiene_emergency"],
    "embarrassed_mood": ["embarrassed_mood", "negative_mood_reaction"],
    "negative_mood_reaction": ["embarrassed_mood", "negative_mood_reaction"],
    "relative_greetings": ["relative_greetings", "relative_warm_welcome"],
    "relative_warm_welcome": ["relative_greetings", "welcomed_guest", "relative_warm_welcome"],
    "family_tea": ["family_tea", "relative_eating_together"],
    "relative_eating_together": ["family_tea", "relative_eating_together"],
    "reminisce_past": ["reminisce_past", "relative_ambient_visit"],
    "relative_ambient_visit": ["reminisce_past", "relative_ambient_visit"],
    "family_gossip": ["family_gossip", "relative_adult_family_gossip"],
    "relative_adult_family_gossip": ["family_gossip", "relative_adult_family_gossip"],
    "friend_chill": ["friend_chill", "guest_ambient_hangout", "two_guests_living_room"],
    "guest_ambient_hangout": ["friend_chill", "guest_ambient_hangout"],
    "two_guests_living_room": ["friend_chill", "two_guests_living_room"],
    "board_games": ["board_games", "table_games"],
    "table_games": ["board_games", "table_games"],
    "tv_movie": ["tv_movie", "watching_tv_together", "guest_gaming_console_tv"],
    "watching_tv_together": ["tv_movie", "watching_tv_together"],
    "guest_gaming_console_tv": ["tv_movie", "console_coop", "guest_gaming_console_tv"],
    "painting_art": ["painting_art", "creative_painting"],
    "creative_painting": ["painting_art", "creative_painting"],
    "instrument_play": ["instrument_play", "music_performance", "guest_music_dance_chill"],
    "music_performance": ["instrument_play", "music_performance"],
    "guest_music_dance_chill": ["instrument_play", "party_music", "guest_music_dance_chill"],
    "gaming_session": ["gaming_session", "console_coop"],
    "console_coop": ["console_coop", "gaming_session"],
    "fitness_training": ["fitness_training", "fitness_workout", "gym_workout", "community_gym_workout_spot"],
    "fitness_workout": ["fitness_training", "fitness_workout"],
    "bartender_order": ["bartender_order", "community_bar_order_chat", "bar_cheers"],
    "community_bar_order_chat": ["bartender_order", "community_bar_order_chat"],
    "bar_cheers": ["bar_cheers", "community_bar_order_chat", "bartender_order"],
    "cafe_coffee": ["cafe_coffee", "community_cafe_barista"],
    "community_cafe_barista": ["cafe_coffee", "community_cafe_barista"],
    "gym_workout": ["gym_workout", "fitness_training", "community_gym_workout_spot"],
    "community_gym_workout_spot": ["gym_workout", "fitness_training", "community_gym_workout_spot"],
    "library_quiet": ["library_quiet", "book_reading", "community_library_whisper"],
    "community_library_whisper": ["library_quiet", "book_reading", "community_library_whisper"],
    "book_reading": ["book_reading", "library_quiet"],
    "park_walk": ["park_walk", "community_ambient_social"],
    "community_ambient_social": ["park_walk", "community_ambient_social"],
    "ambient_living_room": ["ambient_living_room", "friend_chill", "clean_house"],
}


def is_director_trigger_enabled(state: str, trigger_name: str, default: bool = True) -> bool:
    """
    Checks if a trigger is enabled for a given director lot state.
    Key format: f"{state.lower()}_{trigger_name}".
    Checks direct trigger name and its aliases. If ANY alias is disabled for this state, returns False.
    """
    if not state or not trigger_name:
        return default
    st_clean = str(state).strip().lower()
    trig_clean = str(trigger_name).strip().lower()

    disabled_list = get_director_disabled_triggers()
    if not disabled_list:
        return True
    disabled = set(disabled_list)

    # 1. Direct check
    if f"{st_clean}_{trig_clean}" in disabled:
        return False

    # 2. Alias check
    aliases = DIRECTOR_TRIGGER_ALIASES.get(trig_clean, [])
    for al in aliases:
        if f"{st_clean}_{al.lower()}" in disabled:
            return False

    return True


def set_director_trigger_flag(state: str, trigger_name: str, enabled: bool) -> bool:
    """Enables or disables a specific trigger for a specific lot state."""
    if not state or not trigger_name:
        return False
    st_clean = str(state).strip().lower()
    trig_clean = str(trigger_name).strip().lower()
    full_key = f"{st_clean}_{trig_clean}"

    cfg = load_config()
    if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
        cfg["director_settings"] = dict(DEFAULT_CONFIG.get("director_settings", {}))

    cur_disabled = list(cfg["director_settings"].get("disabled_triggers", []))
    if not enabled:
        if full_key not in cur_disabled:
            cur_disabled.append(full_key)
    else:
        cur_disabled = [k for k in cur_disabled if k != full_key]

    cfg["director_settings"]["disabled_triggers"] = cur_disabled
    if action in ("reset_defaults", "default", "reset"):
        # Reset overrides for triggers in this state
        overrides = cfg["director_settings"].get("trigger_overrides", {})
        if isinstance(overrides, dict) and all_triggers_for_state:
            for t in all_triggers_for_state:
                overrides.pop(str(t).lower(), None)
            cfg["director_settings"]["trigger_overrides"] = overrides
    return save_config(cfg)


def bulk_set_director_triggers(state: str, action: str, all_triggers_for_state=None) -> bool:
    """
    Bulk updates all triggers for a state:
    action: 'enable_all', 'disable_all', 'reset_defaults'
    """
    if not state:
        return False
    st_clean = str(state).strip().lower()
    prefix = f"{st_clean}_"

    cfg = load_config()
    if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
        cfg["director_settings"] = dict(DEFAULT_CONFIG.get("director_settings", {}))

    cur_disabled = [k for k in cfg["director_settings"].get("disabled_triggers", []) if not str(k).startswith(prefix)]

    if action == "disable_all" and all_triggers_for_state:
        for t in all_triggers_for_state:
            k = f"{st_clean}_{str(t).lower()}"
            if k not in cur_disabled:
                cur_disabled.append(k)

    cfg["director_settings"]["disabled_triggers"] = cur_disabled
    return save_config(cfg)


DEFAULT_DIRECTOR_TIMERS = {
    "household_silence_sec": 240,
    "pair_cooldown_sec": 450,
    "grace_period_sec": 60,
}

# Default trigger metadata: (is_immediate, default_priority)
# Aliases and exact detector keys are both supported.
# Triggers where social communication animation is DISABLED by default (emergencies, intimacy, solo baths, seated games)
DIRECTOR_TRIGGER_NO_ANIMATION = {
    "fire_hazard",
    "grim_reaper_death",
    "witness_death",
    "burglar_theft",
    "cheating_caught",
    "caught_cheating",
    "witnessed_cheating",
    "sudden_fight",
    "fight_lost",
    "fight_won",
    "bladder_emergency",
    "hygiene_emergency",
    "embarrassed_mood",
    "relaxing_bath",
    "board_games",
    "gaming_session",
    "console_coop",
    "table_games",
    "walk_in_intimacy",
    "ww_post_intimacy",
    "ww_accidental_nudity",
    "electrocuted_repair",
    "sim_in_labor",
}

DEFAULT_DIRECTOR_TRIGGER_META = {
    # Emergencies / Urgent (Immediate = True)
    "cooking_burnt": {"immediate": True, "priority": 90},
    "burnt_food": {"immediate": True, "priority": 90},
    "object_broke": {"immediate": True, "priority": 90},
    "broken_object": {"immediate": True, "priority": 90},
    "dirt_mess": {"immediate": True, "priority": 80},
    "dirty_dish_trash": {"immediate": True, "priority": 80},
    "fire_hazard": {"immediate": True, "priority": 96},
    "burglar_theft": {"immediate": True, "priority": 96},
    "grim_reaper_death": {"immediate": True, "priority": 98},
    "witness_death": {"immediate": True, "priority": 98},
    "cheating_caught": {"immediate": True, "priority": 95},
    "caught_cheating": {"immediate": True, "priority": 95},
    "witnessed_cheating": {"immediate": True, "priority": 92},
    "walk_in_intimacy": {"immediate": True, "priority": 90},
    "breakup_divorce": {"immediate": True, "priority": 94},
    "sudden_fight": {"immediate": True, "priority": 95},
    "fight_lost": {"immediate": True, "priority": 88},
    "fight_won": {"immediate": True, "priority": 88},
    "prank_backfire": {"immediate": True, "priority": 86},
    "bladder_emergency": {"immediate": True, "priority": 88},
    "intruder_spotted": {"immediate": True, "priority": 92},
    "work_return": {"immediate": True, "priority": 100},
    "truant_school_work": {"immediate": True, "priority": 95},
    "sim_in_labor": {"immediate": True, "priority": 97},
    "electrocuted_repair": {"immediate": True, "priority": 94},
    "paid_bills": {"immediate": True, "priority": 88},
    "ww_post_intimacy": {"immediate": True, "priority": 90},
    "ww_accidental_nudity": {"immediate": True, "priority": 85},
    "negative_mood_reaction": {"immediate": True, "priority": 84},
    "relative_warm_welcome": {"immediate": True, "priority": 92},
    "relative_helping_chores": {"immediate": True, "priority": 86},
    "guest_arrival_greeting": {"immediate": True, "priority": 92},
    "guest_inappropriate_cooking": {"immediate": True, "priority": 91},
    "guest_late_curfew_departure": {"immediate": True, "priority": 89},
    "guest_home_door_greeting": {"immediate": True, "priority": 92},
    "guest_home_after_school": {"immediate": True, "priority": 88},
    "guest_home_fridge_snack": {"immediate": True, "priority": 85},
    "guest_home_farewell_late": {"immediate": True, "priority": 89},
    "service_nanny_chat": {"immediate": True, "priority": 88},
    "service_repairman_done": {"immediate": True, "priority": 88},
    "neighbor_welcome_wagon": {"immediate": True, "priority": 94},
    "neighbor_door_knock": {"immediate": True, "priority": 91},
    "bartender_order": {"immediate": True, "priority": 85},
    "community_bar_order_chat": {"immediate": True, "priority": 85},
    "cafe_coffee": {"immediate": True, "priority": 85},
    "community_cafe_barista": {"immediate": True, "priority": 85},

    # Domestic & Routine (Immediate = False)
    "clean_house": {"immediate": False, "priority": 70},
    "service_maid_cleaning": {"immediate": False, "priority": 70},
    "cooking_masterpiece": {"immediate": False, "priority": 80},
    "eating_together": {"immediate": False, "priority": 82},
    "cooking_together": {"immediate": False, "priority": 85},
    "repair_success": {"immediate": False, "priority": 78},
    "morning_wake": {"immediate": False, "priority": 65},
    "morning_coffee": {"immediate": False, "priority": 65},
    "night_sleep": {"immediate": False, "priority": 65},
    "bedtime_pillow_talk": {"immediate": False, "priority": 65},
    "late_night_awake": {"immediate": False, "priority": 85},
    "relaxing_bath": {"immediate": False, "priority": 60},
    "bill_arrived": {"immediate": False, "priority": 75},
    "low_energy": {"immediate": False, "priority": 65},
    "hunger_starving": {"immediate": False, "priority": 70},
    "garden_harvest": {"immediate": False, "priority": 72},
    "gardening_together": {"immediate": False, "priority": 72},
    "spoiled_food": {"immediate": False, "priority": 74},
    "guest_knock": {"immediate": False, "priority": 85},
    "welcomed_guest": {"immediate": False, "priority": 85},
    "maid_arrival": {"immediate": False, "priority": 82},
    "repairman_arrival": {"immediate": False, "priority": 82},
    "nanny_arrival": {"immediate": False, "priority": 82},
    "gardener_arrival": {"immediate": False, "priority": 75},
    "delivery_food": {"immediate": False, "priority": 84},
    "ring_doorbell": {"immediate": False, "priority": 85},
    "borrow_sugar": {"immediate": False, "priority": 78},
    "saying_goodbye": {"immediate": False, "priority": 85},
    "hygiene_emergency": {"immediate": False, "priority": 80},
    "embarrassed_mood": {"immediate": False, "priority": 84},
    "painting_art": {"immediate": False, "priority": 72},
    "creative_painting": {"immediate": False, "priority": 72},
    "instrument_play": {"immediate": False, "priority": 72},
    "music_performance": {"immediate": False, "priority": 72},
    "gaming_session": {"immediate": False, "priority": 75},
    "console_coop": {"immediate": False, "priority": 75},
    "tv_movie": {"immediate": False, "priority": 75},
    "watching_tv_together": {"immediate": False, "priority": 75},
    "book_reading": {"immediate": False, "priority": 68},
    "fitness_training": {"immediate": False, "priority": 73},
    "fitness_workout": {"immediate": False, "priority": 73},
    "table_games": {"immediate": False, "priority": 76},
    "pet_care": {"immediate": False, "priority": 74},

    # Relatives visiting (Immediate = False)
    "relative_greetings": {"immediate": False, "priority": 90},
    "family_tea": {"immediate": False, "priority": 78},
    "relative_eating_together": {"immediate": False, "priority": 78},
    "reminisce_past": {"immediate": False, "priority": 70},
    "relative_ambient_visit": {"immediate": False, "priority": 70},
    "advice_critique": {"immediate": False, "priority": 76},
    "family_gossip": {"immediate": False, "priority": 75},
    "relative_adult_family_gossip": {"immediate": False, "priority": 75},
    "gift_exchange": {"immediate": False, "priority": 82},
    "kid_compliments": {"immediate": False, "priority": 75},
    "ask_money_loan": {"immediate": False, "priority": 80},
    "heirloom_talk": {"immediate": False, "priority": 74},
    "relative_homework_together": {"immediate": False, "priority": 80},

    # Friends visiting (Immediate = False)
    "friend_chill": {"immediate": False, "priority": 70},
    "guest_ambient_hangout": {"immediate": False, "priority": 70},
    "two_guests_living_room": {"immediate": False, "priority": 76},
    "two_kid_guests_playing": {"immediate": False, "priority": 80},
    "share_secrets": {"immediate": False, "priority": 78},
    "party_music": {"immediate": False, "priority": 80},
    "guest_music_dance_chill": {"immediate": False, "priority": 80},
    "drinks_chat": {"immediate": False, "priority": 76},
    "dating_advice": {"immediate": False, "priority": 76},
    "borrow_item": {"immediate": False, "priority": 74},
    "board_games": {"immediate": False, "priority": 76},
    "guest_homework_together": {"immediate": False, "priority": 80},
    "guest_gaming_console_tv": {"immediate": False, "priority": 75},
    "guest_eating_drinking": {"immediate": False, "priority": 78},

    # Community (Immediate = False)
    "bar_cheers": {"immediate": False, "priority": 75},
    "gym_workout": {"immediate": False, "priority": 73},
    "community_gym_workout_spot": {"immediate": False, "priority": 73},
    "park_walk": {"immediate": False, "priority": 68},
    "library_quiet": {"immediate": False, "priority": 70},
    "community_library_whisper": {"immediate": False, "priority": 70},
    "nightclub_dance": {"immediate": False, "priority": 78},
    "community_player_social": {"immediate": False, "priority": 80},
    "community_ambient_social": {"immediate": False, "priority": 40},
    "ambient_living_room": {"immediate": False, "priority": 30},
}


def get_director_timers() -> dict:
    """Returns the director cooldown timer settings in unpaused real seconds."""
    cfg = load_config()
    dtr = cfg.get("director_settings", {})
    timers = dict(DEFAULT_DIRECTOR_TIMERS)
    if isinstance(dtr, dict) and "timers" in dtr and isinstance(dtr["timers"], dict):
        timers.update(dtr["timers"])
    return timers


def set_director_timers(silence_sec: int, pair_sec: int, grace_sec: int) -> bool:
    """Sets the director cooldown timers in unpaused real seconds."""
    try:
        cfg = load_config()
        if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
            cfg["director_settings"] = dict(DEFAULT_CONFIG.get("director_settings", {}))
        if "timers" not in cfg["director_settings"] or not isinstance(cfg["director_settings"]["timers"], dict):
            cfg["director_settings"]["timers"] = dict(DEFAULT_DIRECTOR_TIMERS)

        s_sec = max(10, min(3600, int(silence_sec)))
        p_sec = max(10, min(3600, int(pair_sec)))
        g_sec = max(0, min(600, int(grace_sec)))

        cfg["director_settings"]["timers"]["household_silence_sec"] = s_sec
        cfg["director_settings"]["timers"]["pair_cooldown_sec"] = p_sec
        cfg["director_settings"]["timers"]["grace_period_sec"] = g_sec
        return save_config(cfg)
    except Exception as e:
        log_exception("Error setting director timers", e)
        return False


def get_director_trigger_overrides() -> dict:
    """Returns dictionary of custom trigger overrides: key -> {immediate: bool, priority: int}."""
    cfg = load_config()
    dtr = cfg.get("director_settings", {})
    if isinstance(dtr, dict) and "trigger_overrides" in dtr and isinstance(dtr["trigger_overrides"], dict):
        return dict(dtr["trigger_overrides"])
    return {}


def get_director_trigger_meta(trigger_name: str) -> dict:
    """Returns effective metadata for a trigger, checking custom player overrides first."""
    if not trigger_name:
        return {"immediate": False, "priority": 50, "enable_animation": True, "animation_type": "AUTO", "is_custom": False}
    trig_clean = str(trigger_name).strip().lower()
    overrides = get_director_trigger_overrides()

    def_anim = (trig_clean not in DIRECTOR_TRIGGER_NO_ANIMATION)
    aliases = DIRECTOR_TRIGGER_ALIASES.get(trig_clean, [])
    for al in aliases:
        if al.lower() in DIRECTOR_TRIGGER_NO_ANIMATION:
            def_anim = False
            break

    # 1. Direct override check
    if trig_clean in overrides:
        ov = overrides[trig_clean]
        return {
            "immediate": bool(ov.get("immediate", False)),
            "priority": int(ov.get("priority", 50)),
            "custom_prompt": ov.get("custom_prompt", None),
            "enable_animation": bool(ov.get("enable_animation", def_anim)),
            "animation_type": str(ov.get("animation_type", "AUTO")).upper(),
            "def_enable_animation": def_anim,
            "is_custom": True,
        }

    # 2. Alias override check
    for al in aliases:
        al_clean = al.lower()
        if al_clean in overrides:
            ov = overrides[al_clean]
            return {
                "immediate": bool(ov.get("immediate", False)),
                "priority": int(ov.get("priority", 50)),
                "custom_prompt": ov.get("custom_prompt", None),
                "enable_animation": bool(ov.get("enable_animation", def_anim)),
                "animation_type": str(ov.get("animation_type", "AUTO")).upper(),
                "def_enable_animation": def_anim,
                "is_custom": True,
            }

    # 3. Default meta check
    if trig_clean in DEFAULT_DIRECTOR_TRIGGER_META:
        dm = DEFAULT_DIRECTOR_TRIGGER_META[trig_clean]
        return {
            "immediate": bool(dm.get("immediate", False)),
            "priority": int(dm.get("priority", 50)),
            "enable_animation": def_anim,
            "animation_type": "AUTO",
            "def_enable_animation": def_anim,
            "is_custom": False,
        }

    for al in aliases:
        al_clean = al.lower()
        if al_clean in DEFAULT_DIRECTOR_TRIGGER_META:
            dm = DEFAULT_DIRECTOR_TRIGGER_META[al_clean]
            return {
                "immediate": bool(dm.get("immediate", False)),
                "priority": int(dm.get("priority", 50)),
                "enable_animation": def_anim,
                "animation_type": "AUTO",
                "def_enable_animation": def_anim,
                "is_custom": False,
            }

    return {"immediate": False, "priority": 50, "enable_animation": def_anim, "animation_type": "AUTO", "def_enable_animation": def_anim, "is_custom": False}


def get_director_trigger_custom_prompt(trigger_name: str) -> Optional[str]:
    """Returns the customized scenario prompt / premise if one was saved by the player."""
    meta = get_director_trigger_meta(trigger_name)
    cp = meta.get("custom_prompt")
    if cp and str(cp).strip():
        return str(cp).strip()
    return None


def is_director_trigger_immediate(trigger_name: str) -> bool:
    """Returns True if the trigger executes immediately, bypassing silence and pair cooldowns."""
    meta = get_director_trigger_meta(trigger_name)
    return bool(meta.get("immediate", False))


def get_director_trigger_priority(trigger_name: str, default_prio: int = 50) -> int:
    """Returns effective priority score for the trigger."""
    meta = get_director_trigger_meta(trigger_name)
    if meta.get("is_custom"):
        return int(meta.get("priority", default_prio))
    return int(meta.get("priority", default_prio))


def set_director_trigger_override(trigger_name: str, immediate: bool, priority: int, custom_prompt: Optional[str] = None, enable_animation: Optional[bool] = None, animation_type: Optional[str] = None) -> bool:
    """Saves custom override for a trigger, including optional custom scenario prompt and animation settings."""
    if not trigger_name:
        return False
    trig_clean = str(trigger_name).strip().lower()
    try:
        cfg = load_config()
        if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
            cfg["director_settings"] = dict(DEFAULT_CONFIG.get("director_settings", {}))
        if "trigger_overrides" not in cfg["director_settings"] or not isinstance(cfg["director_settings"]["trigger_overrides"], dict):
            cfg["director_settings"]["trigger_overrides"] = {}

        prio_val = max(1, min(999, int(priority)))
        existing = cfg["director_settings"]["trigger_overrides"].get(trig_clean, {}) if isinstance(cfg["director_settings"]["trigger_overrides"].get(trig_clean), dict) else {}

        ov_data = {
            "immediate": bool(immediate),
            "priority": prio_val,
        }
        if custom_prompt is not None and str(custom_prompt).strip():
            ov_data["custom_prompt"] = str(custom_prompt).strip()
        elif "custom_prompt" in existing:
            ov_data["custom_prompt"] = existing["custom_prompt"]

        if enable_animation is not None:
            ov_data["enable_animation"] = bool(enable_animation)
        elif "enable_animation" in existing:
            ov_data["enable_animation"] = existing["enable_animation"]

        if animation_type is not None and str(animation_type).strip():
            ov_data["animation_type"] = str(animation_type).strip().upper()
        elif "animation_type" in existing:
            ov_data["animation_type"] = existing["animation_type"]

        cfg["director_settings"]["trigger_overrides"][trig_clean] = ov_data
        return save_config(cfg)
    except Exception as e:
        log_exception(f"Error setting trigger override for {trigger_name}", e)
        return False


def reset_director_trigger_override(trigger_name: str) -> bool:
    """Removes custom override for a trigger and its aliases, returning to default."""
    if not trigger_name:
        return False
    trig_clean = str(trigger_name).strip().lower()
    try:
        cfg = load_config()
        if "director_settings" not in cfg or not isinstance(cfg["director_settings"], dict):
            return True
        overrides = cfg["director_settings"].get("trigger_overrides", {})
        if not isinstance(overrides, dict):
            return True

        changed = False
        if trig_clean in overrides:
            del overrides[trig_clean]
            changed = True

        for al in DIRECTOR_TRIGGER_ALIASES.get(trig_clean, []):
            al_clean = al.lower()
            if al_clean in overrides:
                del overrides[al_clean]
                changed = True

        if changed:
            cfg["director_settings"]["trigger_overrides"] = overrides
            return save_config(cfg)
        return True
    except Exception as e:
        log_exception(f"Error resetting trigger override for {trigger_name}", e)
        return False


def get_packed_director_state_str() -> str:
    """
    Returns packed string for Flash UI:
    format: 'en:1|dis:home_fire_hazard,community_fire_hazard|tm:240,450,60|ovr:cooking_burnt:1:90,morning_wake:0:80'
    """
    en = 1 if get_director_enabled() else 0
    dis_list = get_director_disabled_triggers()
    dis_str = ",".join(dis_list) if dis_list else "none"

    timers = get_director_timers()
    tm_str = f"{timers.get('household_silence_sec', 240)},{timers.get('pair_cooldown_sec', 450)},{timers.get('grace_period_sec', 60)}"

    overrides = get_director_trigger_overrides()
    if overrides:
        ovr_parts = []
        from urllib.parse import quote
        for k, v in overrides.items():
            if isinstance(v, dict):
                imm_flag = "1" if v.get("immediate") else "0"
                prio_val = str(v.get("priority", 50))
                cp = v.get("custom_prompt")
                cp_enc = quote(str(cp).strip()) if (cp and str(cp).strip()) else "00"
                anim_flag = "1" if v.get("enable_animation", True) else "0"
                anim_t = str(v.get("animation_type", "AUTO")).upper()
                ovr_parts.append(f"{k}:{imm_flag}:{prio_val}:{cp_enc}:{anim_flag}:{anim_t}")
        ovr_str = ",".join(ovr_parts) if ovr_parts else "none"
    else:
        ovr_str = "none"

        simp_en = 1 if get_simplified_dialogue_enabled() else 0
    simp_timers = get_simplified_dialogue_timers()
    simp_sil = simp_timers.get("silence_sec", 180)
    simp_chance = simp_timers.get("trigger_chance_pct", 40)
    simp_bal = 1 if get_simplified_dialogue_balloon() else 0
    simp_notif = 1 if get_simplified_dialogue_notification() else 0
    simp_str = f"{simp_en},{simp_sil},{simp_chance},{simp_bal},{simp_notif}"

    return f"en:{en}|dis:{dis_str}|tm:{tm_str}|ovr:{ovr_str}|simp:{simp_str}"


def get_simplified_dialogue_enabled() -> bool:
    """Returns whether Simplified Autonomous Dialogue is enabled."""
    cfg = load_config()
    s = cfg.get("simplified_dialogue_settings")
    if isinstance(s, dict) and "enabled" in s:
        return bool(s["enabled"])
    return bool(DEFAULT_CONFIG.get("simplified_dialogue_settings", {}).get("enabled", False))


def set_simplified_dialogue_enabled(enabled: bool) -> bool:
    """Sets whether Simplified Autonomous Dialogue is enabled."""
    if enabled and get_director_enabled():
        log("[MUTUAL_EXCLUSIVE] Cannot enable Simplified Dialogue: Director is already active!")
        return False
    cfg = load_config()
    if "simplified_dialogue_settings" not in cfg or not isinstance(cfg["simplified_dialogue_settings"], dict):
        cfg["simplified_dialogue_settings"] = dict(DEFAULT_CONFIG.get("simplified_dialogue_settings", {}))
    cfg["simplified_dialogue_settings"]["enabled"] = bool(enabled)
    return save_config(cfg)


def get_simplified_dialogue_timers() -> dict:
    """Returns silence cooldown seconds and trigger chance pct."""
    cfg = load_config()
    s = cfg.get("simplified_dialogue_settings", {})
    if not isinstance(s, dict):
        s = DEFAULT_CONFIG.get("simplified_dialogue_settings", {})
    return {
        "silence_sec": int(s.get("silence_sec", 180)),
        "trigger_chance_pct": int(s.get("trigger_chance_pct", 40)),
    }


def set_simplified_dialogue_timers(silence_sec: int, chance_pct: int) -> bool:
    """Sets silence cooldown seconds and trigger chance pct."""
    cfg = load_config()
    if "simplified_dialogue_settings" not in cfg or not isinstance(cfg["simplified_dialogue_settings"], dict):
        cfg["simplified_dialogue_settings"] = dict(DEFAULT_CONFIG.get("simplified_dialogue_settings", {}))
    cfg["simplified_dialogue_settings"]["silence_sec"] = max(30, min(3600, int(silence_sec)))
    cfg["simplified_dialogue_settings"]["trigger_chance_pct"] = max(5, min(100, int(chance_pct)))
    return save_config(cfg)


def get_simplified_dialogue_balloon() -> bool:
    cfg = load_config()
    s = cfg.get("simplified_dialogue_settings", {})
    if isinstance(s, dict) and "balloon" in s:
        return bool(s["balloon"])
    return True


def get_simplified_dialogue_notification() -> bool:
    cfg = load_config()
    s = cfg.get("simplified_dialogue_settings", {})
    if isinstance(s, dict) and "notification" in s:
        return bool(s["notification"])
    return False


def set_simplified_dialogue_display(balloon: bool, notification: bool) -> bool:
    cfg = load_config()
    if "simplified_dialogue_settings" not in cfg or not isinstance(cfg["simplified_dialogue_settings"], dict):
        cfg["simplified_dialogue_settings"] = dict(DEFAULT_CONFIG.get("simplified_dialogue_settings", {}))
    cfg["simplified_dialogue_settings"]["balloon"] = bool(balloon)
    cfg["simplified_dialogue_settings"]["notification"] = bool(notification)
    return save_config(cfg)

def get_age_instructions_enabled() -> bool:
    """Returns True if age-specific instruction rules should be included in prompts."""
    try:
        cfg = load_config()
        return bool(cfg.get("age_instructions_enabled", False))
    except Exception:
        return False


def set_age_instructions_enabled(enabled: bool):
    """Sets whether age-specific instruction rules should be included in prompts."""
    try:
        cfg = load_config()
        cfg["age_instructions_enabled"] = bool(enabled)
        save_config(cfg)
    except Exception as e:
        log_exception("Error setting age_instructions_enabled", e)


def get_special_situations_enabled() -> bool:
    """Returns True if special situations prompt rules should be included in prompts."""
    try:
        cfg = load_config()
        return bool(cfg.get("special_situations_enabled", False))
    except Exception:
        return False


def set_special_situations_enabled(enabled: bool):
    """Sets whether special situations prompt rules should be included in prompts."""
    try:
        cfg = load_config()
        cfg["special_situations_enabled"] = bool(enabled)
        save_config(cfg)
    except Exception as e:
        log_exception("Error setting special_situations_enabled", e)
