# -*- coding: utf-8 -*-
"""
Synapse Localization Manager (i18n)
Supports dynamic loading of .txt language files from the 'languages' directory.
Provides UI translations, prompt localization, fallback to built-in dictionaries,
and clean data structures for the future web-based translation portal (Bridge & Mod).
"""

import os
import sys
import re
import json

class LocalizationManager:
    _instance = None

    def __init__(self):
        self.languages_dir = self._find_languages_dir()
        self.available_languages = {} # code -> { 'display_name': ..., 'code': ..., 'filepath': ..., 'ui': {}, 'prompts': {}, 'mod': {} }
        self.current_code = "ru"
        self._load_all_languages()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LocalizationManager()
        return cls._instance

    def _find_languages_dir(self):
        candidates = []
        # 1. Next to executable if frozen
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "languages"))
        # 2. PyInstaller MEIPASS bundled directory
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "languages"))
        # 3. Next to this file
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages"))
        # 4. Current working dir
        candidates.append(os.path.join(os.getcwd(), "languages"))
        # 5. Standard Desktop path
        candidates.append(r"C:\Users\zayar\Desktop\Synapse\languages")

        for c in candidates:
            if os.path.isdir(c):
                return c
        # Default to directory next to this file
        target = candidates[1]
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            pass
        return target

    def _load_all_languages(self):
        self.available_languages.clear()
        
        # 1. Scan languages directory for .txt files
        if self.languages_dir and os.path.isdir(self.languages_dir):
            for fname in os.listdir(self.languages_dir):
                if fname.lower().endswith(".txt"):
                    fpath = os.path.join(self.languages_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        data = self.parse_txt_content(content, default_code=os.path.splitext(fname)[0].lower())
                        data["filepath"] = fpath
                        code = data.get("code", "ru").lower()
                        self.available_languages[code] = data
                    except Exception as e:
                        print(f"[WARN] Failed to parse language file {fname}: {e}")

        # 2. Fallbacks if directory is empty or missing RU/EN
        if "ru" not in self.available_languages:
            self.available_languages["ru"] = {
                "display_name": "🌐 Язык: RU",
                "code": "ru",
                "filepath": None,
                "ui": {},
                "prompts": {},
                "mod": {},
            }
        if "en" not in self.available_languages:
            self.available_languages["en"] = {
                "display_name": "🌐 Language: EN",
                "code": "en",
                "filepath": None,
                "ui": {},
                "prompts": {},
                "mod": {},
            }

    @staticmethod
    def parse_txt_content(content: str, default_code: str = "ru") -> dict:
        """
        Parses our human-friendly .txt translation format:
        LANGUAGE = 🌐 Язык: RU
        CODE = ru
        
        [BRIDGE_UI]
        KEY = VALUE
        
        [BRIDGE_PROMPTS]
        [PROMPT_TAG]
        multi-line
        [/PROMPT_TAG]
        
        [MOD_UI]
        MOD_KEY = VALUE
        """
        data = {
            "display_name": "Unknown",
            "code": default_code,
            "ui": {},
            "prompts": {},
            "mod": {},
        }

        # 1. Header meta
        m_lang = re.search(r'^\s*LANGUAGE\s*[:=]\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        m_code = re.search(r'^\s*CODE\s*[:=]\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        if m_lang:
            data["display_name"] = m_lang.group(1).strip()
        if m_code:
            data["code"] = m_code.group(1).strip().lower()

        # If display_name is not set, format from code
        if data["display_name"] == "Unknown":
            data["display_name"] = f"🌐 Language: {data['code'].upper()}"

        # 2. Extract multi-line prompts [TAG] ... [/TAG]
        for m in re.finditer(r'\[([A-Z0-9_]+)\]\s*\n(.*?)\n\s*\[/\1\]', content, re.DOTALL):
            tag = m.group(1)
            val = m.group(2).strip()
            data["prompts"][tag] = val

        # 3. Clean out multi-line blocks to parse single-line key=value pairs
        cleaned = re.sub(r'\[([A-Z0-9_]+)\].*?\[/\1\]', '', content, flags=re.DOTALL)
        current_section = "ui"

        for line in cleaned.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            sec_lower = line.lower()
            if sec_lower in ("[bridge_ui]", "[ui]"):
                current_section = "ui"
                continue
            elif sec_lower in ("[bridge_prompts]", "[prompts]"):
                current_section = "prompts"
                continue
            elif sec_lower in ("[mod_ui]", "[mod_strings]", "[mod]"):
                current_section = "mod"
                continue

            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if "\\n" in v:
                    v = v.replace("\\n", "\n")
                if k.upper() in ("LANGUAGE", "CODE"):
                    continue
                if current_section == "mod" or k.startswith("MOD_"):
                    data["mod"][k] = v
                else:
                    data["ui"][k] = v

        return data

    def get_language_choices(self) -> list:
        """Returns list of display names for dropdown."""
        # Ensure RU is first, then EN, then others alphabetically
        codes = list(self.available_languages.keys())
        def _sort_key(c):
            if c == "ru": return (0, "")
            if c == "en": return (1, "")
            return (2, self.available_languages[c].get("display_name", c))
        codes.sort(key=_sort_key)
        return [self.available_languages[c]["display_name"] for c in codes]

    def set_language_by_display_name(self, name: str) -> str:
        for c, data in self.available_languages.items():
            if data["display_name"] == name:
                self.current_code = c
                return c
        self.current_code = "ru"
        return "ru"

    def set_language_by_code(self, code: str) -> str:
        code_low = (code or "ru").strip().lower()
        if code_low in self.available_languages:
            self.current_code = code_low
        elif code_low in ("ru", "rus", "russian", "русский"):
            self.current_code = "ru"
        elif code_low in ("en", "eng", "english", "английский"):
            self.current_code = "en"
        elif code_low[:2] in self.available_languages:
            self.current_code = code_low[:2]
        else:
            # Check prefix match among available languages (e.g. "español" -> "es")
            matched = False
            for k in self.available_languages:
                if code_low.startswith(k) or k.startswith(code_low[:2]):
                    self.current_code = k
                    matched = True
                    break
            if not matched:
                self.current_code = "ru"
        return self.current_code

    def get_current_display_name(self) -> str:
        curr = self.available_languages.get(self.current_code)
        if curr:
            return curr["display_name"]
        return "🌐 Язык: RU"

    def t(self, key: str, default: str = "") -> str:
        """Translate UI string by key."""
        lang_data = self.available_languages.get(self.current_code, {})
        val = lang_data.get("ui", {}).get(key)
        if val:
            return val
        # Fallback to RU
        ru_data = self.available_languages.get("ru", {})
        val_ru = ru_data.get("ui", {}).get(key)
        if val_ru:
            return val_ru
        return default or key

    def get_ui(self, key: str, default: str = "") -> str:
        """Alias for t(key, default)."""
        return self.t(key, default)

    def get_prompt(self, prompt_tag: str, default: str = None) -> str:
        """Retrieve localized system prompt by tag for current language."""
        lang_data = self.available_languages.get(self.current_code, {})
        p = lang_data.get("prompts", {}).get(prompt_tag)
        if p:
            return p
        # Fallback to RU
        ru_data = self.available_languages.get("ru", {})
        p_ru = ru_data.get("prompts", {}).get(prompt_tag)
        if p_ru:
            return p_ru
        return default

    def get_prompt_for_lang(self, lang_code: str, prompt_tag: str, default: str = None) -> str:
        """Retrieve localized default prompt by tag for a specific language code."""
        code = normalize_lang_code(lang_code)
        lang_data = self.available_languages.get(code, {})
        p = lang_data.get("prompts", {}).get(prompt_tag)
        if p:
            return p
        ru_data = self.available_languages.get("ru", {})
        p_ru = ru_data.get("prompts", {}).get(prompt_tag)
        if p_ru:
            return p_ru
        return default

    def get_lang_prompts(self, cfg: dict, lang_code: str = None) -> dict:
        """
        Retrieves the isolated prompt dictionary for a specific language from cfg['prompts_by_language'].
        Performs safe auto-migration of legacy top-level keys if prompts_by_language is missing.
        """
        if not cfg or not isinstance(cfg, dict):
            return {}
        
        target_lang = normalize_lang_code(lang_code or cfg.get("language") or "ru")
        
        if "prompts_by_language" not in cfg or not isinstance(cfg["prompts_by_language"], dict):
            cfg["prompts_by_language"] = {}

        p_by_lang = cfg["prompts_by_language"]

        # If target language not yet initialized, check if we can migrate legacy top-level prompts
        if target_lang not in p_by_lang:
            legacy_lang = normalize_lang_code(cfg.get("language", "ru"))
            # If target language matches legacy config language, migrate existing keys
            if target_lang == legacy_lang and (cfg.get("system_prompt") or cfg.get("is_custom_system_prompt")):
                p_by_lang[target_lang] = {
                    "system_prompt": cfg.get("system_prompt", ""),
                    "is_custom_system_prompt": bool(cfg.get("is_custom_system_prompt", False)),
                    "chat_system_prompt": cfg.get("chat_system_prompt", ""),
                    "is_custom_chat_system_prompt": bool(cfg.get("is_custom_chat_system_prompt", False)),
                    "group_chat_system_prompt": cfg.get("group_chat_system_prompt", ""),
                    "is_custom_group_chat_system_prompt": bool(cfg.get("is_custom_group_chat_system_prompt", False)),
                    "npc_chat_system_prompt": cfg.get("npc_chat_system_prompt", ""),
                    "is_custom_npc_chat_system_prompt": bool(cfg.get("is_custom_npc_chat_system_prompt", False)),
                    "friend_chat_system_prompt": cfg.get("friend_chat_system_prompt", ""),
                    "is_custom_friend_chat_system_prompt": bool(cfg.get("is_custom_friend_chat_system_prompt", False)),
                    "direct_dialogue_system_prompt": cfg.get("direct_dialogue_system_prompt", ""),
                    "is_custom_direct_dialogue_system_prompt": bool(cfg.get("is_custom_direct_dialogue_system_prompt", False)),
                    "summarize_system_prompt": cfg.get("summarize_system_prompt", ""),
                    "is_custom_summarize_system_prompt": bool(cfg.get("is_custom_summarize_system_prompt", False)),
                    "group_summarize_system_prompt": cfg.get("group_summarize_system_prompt", ""),
                    "is_custom_group_summarize_system_prompt": bool(cfg.get("is_custom_group_summarize_system_prompt", False)),
                    "custom_age_prompts": dict(cfg.get("custom_age_prompts", {})),
                    "custom_special_prompts": dict(cfg.get("custom_special_prompts", {})),
                    "custom_pet_prompts": dict(cfg.get("custom_pet_prompts", {})),
                }
            else:
                p_by_lang[target_lang] = {}

        return p_by_lang[target_lang]

    def save_lang_prompts(self, cfg: dict, lang_code: str, prompts_dict: dict):
        """
        Saves prompts for lang_code into cfg['prompts_by_language'][lang_code].
        If lang_code is the current active language, also mirrors to top-level keys for backward compatibility.
        """
        if not cfg or not isinstance(cfg, dict):
            return
        
        target_lang = normalize_lang_code(lang_code)
        if "prompts_by_language" not in cfg or not isinstance(cfg["prompts_by_language"], dict):
            cfg["prompts_by_language"] = {}
        
        cfg["prompts_by_language"][target_lang] = dict(prompts_dict)

        # Mirror to top-level if active language
        active_lang = normalize_lang_code(cfg.get("language", "ru"))
        if target_lang == active_lang:
            self.sync_top_level_prompts(cfg, target_lang)

    def sync_top_level_prompts(self, cfg: dict, lang_code: str = None):
        """Mirrors active language prompts to legacy top-level keys in cfg."""
        if not cfg or not isinstance(cfg, dict):
            return
        target_lang = normalize_lang_code(lang_code or cfg.get("language", "ru"))
        lang_p = self.get_lang_prompts(cfg, target_lang)

        cfg["system_prompt"] = lang_p.get("system_prompt", "")
        cfg["is_custom_system_prompt"] = bool(lang_p.get("is_custom_system_prompt", False))
        cfg["chat_system_prompt"] = lang_p.get("chat_system_prompt", "")
        cfg["is_custom_chat_system_prompt"] = bool(lang_p.get("is_custom_chat_system_prompt", False))
        cfg["group_chat_system_prompt"] = lang_p.get("group_chat_system_prompt", "")
        cfg["is_custom_group_chat_system_prompt"] = bool(lang_p.get("is_custom_group_chat_system_prompt", False))
        cfg["npc_chat_system_prompt"] = lang_p.get("npc_chat_system_prompt", "")
        cfg["is_custom_npc_chat_system_prompt"] = bool(lang_p.get("is_custom_npc_chat_system_prompt", False))
        cfg["friend_chat_system_prompt"] = lang_p.get("friend_chat_system_prompt", "")
        cfg["is_custom_friend_chat_system_prompt"] = bool(lang_p.get("is_custom_friend_chat_system_prompt", False))
        cfg["direct_dialogue_system_prompt"] = lang_p.get("direct_dialogue_system_prompt", "")
        cfg["is_custom_direct_dialogue_system_prompt"] = bool(lang_p.get("is_custom_direct_dialogue_system_prompt", False))
        cfg["summarize_system_prompt"] = lang_p.get("summarize_system_prompt", "")
        cfg["is_custom_summarize_system_prompt"] = bool(lang_p.get("is_custom_summarize_system_prompt", False))
        cfg["group_summarize_system_prompt"] = lang_p.get("group_summarize_system_prompt", "")
        cfg["is_custom_group_summarize_system_prompt"] = bool(lang_p.get("is_custom_group_summarize_system_prompt", False))
        cfg["custom_age_prompts"] = dict(lang_p.get("custom_age_prompts", {}))
        cfg["custom_special_prompts"] = dict(lang_p.get("custom_special_prompts", {}))
        cfg["custom_pet_prompts"] = dict(lang_p.get("custom_pet_prompts", {}))

    def export_bundle_for_web_tool(self) -> dict:
        """
        Exports a unified dictionary for the future Web/HTML translation tool.
        Separated clearly into Bridge (UI + Prompts) and Mod (Game Strings).
        """
        return {
            "current_code": self.current_code,
            "languages": {
                c: {
                    "display_name": d.get("display_name"),
                    "code": d.get("code"),
                    "bridge_ui": d.get("ui", {}),
                    "bridge_prompts": d.get("prompts", {}),
                    "mod_strings": d.get("mod", {})
                }
                for c, d in self.available_languages.items()
            }
        }


def normalize_lang_code(raw_code: str) -> str:
    """Normalizes any language string ('Russian', 'en', 'es', 'English', etc.) to active code."""
    if not raw_code:
        return "en"
    code_low = str(raw_code).strip().lower()
    if code_low in ("ru", "rus", "russian", "русский"):
        return "ru"
    if code_low in ("en", "eng", "english", "английский"):
        return "en"
    if code_low in ("es", "esp", "spanish", "испанский"):
        return "es"
    if code_low in ("de", "ger", "german", "deutsch", "немецкий"):
        return "de"
    if code_low in ("fr", "fra", "french", "français", "французский"):
        return "fr"
    mgr = LocalizationManager._instance
    if mgr and code_low in mgr.available_languages:
        return code_low
    return code_low[:2] if len(code_low) >= 2 else "en"


def get_i18n() -> LocalizationManager:
    return LocalizationManager.get_instance()


def get_lang_prompts(cfg: dict, lang_code: str = None) -> dict:
    return LocalizationManager.get_instance().get_lang_prompts(cfg, lang_code)


def save_lang_prompts(cfg: dict, lang_code: str, prompts_dict: dict):
    return LocalizationManager.get_instance().save_lang_prompts(cfg, lang_code, prompts_dict)


def sync_top_level_prompts(cfg: dict, lang_code: str = None):
    return LocalizationManager.get_instance().sync_top_level_prompts(cfg, lang_code)


def get_prompt_for_lang(lang_code: str, prompt_tag: str, default: str = "") -> str:
    return LocalizationManager.get_instance().get_prompt_for_lang(lang_code, prompt_tag, default)

