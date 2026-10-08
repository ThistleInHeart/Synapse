import os
import time
import json
import re
import http.client
import threading
from typing import Callable, Optional, Dict, List, Tuple, Any, Set
from ai_social_pc.logger import log, log_exception

try:
    import services
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    services = None
    LocalizationHelperTuning = None

# Optional integration with core AIThoughtReader mod
try:
    from ai_thought_reader.context import (
        get_sim_occult_info,
        get_sim_clothing_and_nudity_info,
        get_current_activity,
        get_nearby_sims_info,
        get_sim_family_info,
        get_household_pets_info,
        get_household_roommates_info,
        get_sim_mood_info,
        get_current_location,
        get_sim_home_world_name,
        get_sim_motives_summary,
        get_sim_traits_info,
        get_custom_sim_lore,
        get_sim_pregnancy_info,
        get_sim_fame_and_reputation_info,
        get_sim_career_info,
        get_sim_aspiration_info,
        get_household_funds_info,
        get_relationship_between_sims,
    )
    from ai_thought_reader.config import get_chat_context_flag
    _HAS_THOUGHT_READER = True
except Exception:
    _HAS_THOUGHT_READER = False
    get_chat_context_flag = lambda f: True
    get_sim_occult_info = None
    get_sim_clothing_and_nudity_info = None
    get_current_activity = None
    get_nearby_sims_info = None
    get_sim_family_info = None
    get_household_pets_info = None
    get_household_roommates_info = None
    get_sim_mood_info = None
    get_current_location = None
    get_sim_home_world_name = None
    get_sim_motives_summary = None
    get_sim_traits_info = None
    get_custom_sim_lore = None
    get_sim_pregnancy_info = None
    get_sim_fame_and_reputation_info = None
    get_sim_career_info = None
    get_sim_aspiration_info = None
    get_household_funds_info = None
    get_relationship_between_sims = None

def _is_en() -> bool:
    try:
        from ai_social_pc.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False


BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765

# Track instance IDs for The Sims 4 relationship commodities
FRIENDSHIP_TRACK_ID = 16650
ROMANCE_TRACK_ID = 16651

# ---------------------------------------------------------------------------
# 1-on-1 Direct Chat Sessions & Disk Persistence
# ---------------------------------------------------------------------------
CHATS_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_social_chats.json")

# In-memory working state for active save slot: { (min_id, max_id): [msg_dict, ...] }
_WORKING_CHATS_CACHE: Optional[Dict[Tuple[int, int], List[Dict[str, Any]]]] = None
_ACTIVE_CHATS_SAVE_ID: Optional[str] = None
_IS_CHATS_DIRTY: bool = False
_CHATS_LOCK = threading.RLock()

# Public dictionary for backwards compatibility
_CHAT_SESSIONS: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}


def get_chat_session_key(actor_id: int, target_id: int) -> Tuple[int, int]:
    """
    Returns a canonical symmetric session key between two Sims.
    Regardless of whether Sim A or Sim B is active, key is always (min_id, max_id).
    """
    a, b = int(actor_id), int(target_id)
    return (min(a, b), max(a, b))


def _key_to_str(key: Tuple[int, int]) -> str:
    return f"{key[0]}_{key[1]}"


def _str_to_key(key_str: str) -> Optional[Tuple[int, int]]:
    parts = key_str.split("_")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return (int(parts[0]), int(parts[1]))
    return None


def _read_chats_disk_file() -> Dict[str, Any]:
    """Reads the chats JSON file from disk."""
    if os.path.exists(CHATS_FILE_PATH):
        try:
            with open(CHATS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_social_chats.json from disk", e)
    return {"saves": {}}


def load_chats_data() -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """
    Loads 1-on-1 chat history for the current save slot.
    Loads from disk if cache is empty or active save changed.
    """
    global _WORKING_CHATS_CACHE, _ACTIVE_CHATS_SAVE_ID, _IS_CHATS_DIRTY, _CHAT_SESSIONS
    with _CHATS_LOCK:
        from ai_social_pc.group_manager import get_current_save_id
        current_save = get_current_save_id()

        if _WORKING_CHATS_CACHE is not None and _ACTIVE_CHATS_SAVE_ID == current_save:
            return _WORKING_CHATS_CACHE

        _ACTIVE_CHATS_SAVE_ID = current_save
        _IS_CHATS_DIRTY = False
        disk_data = _read_chats_disk_file()

        save_entry = disk_data.get("saves", {}).get(current_save, {})
        raw_chats = save_entry.get("chats", {}) if isinstance(save_entry, dict) else {}
        _WORKING_CHATS_CACHE = {}
        for k_str, msgs in raw_chats.items():
            k_tuple = _str_to_key(k_str)
            if k_tuple and isinstance(msgs, list):
                _WORKING_CHATS_CACHE[k_tuple] = list(msgs)

        _CHAT_SESSIONS.clear()
        _CHAT_SESSIONS.update(_WORKING_CHATS_CACHE)

        log(f"[CHATS] Loaded {len(_WORKING_CHATS_CACHE)} active chat session(s) for save '{current_save}'")
        return _WORKING_CHATS_CACHE


def mark_chats_dirty():
    global _IS_CHATS_DIRTY
    _IS_CHATS_DIRTY = True


def commit_chats_to_disk():
    """Commits current in-memory chat histories to disk for active save slot."""
    global _IS_CHATS_DIRTY
    with _CHATS_LOCK:
        from ai_social_pc.group_manager import get_current_save_id
        current_save = _ACTIVE_CHATS_SAVE_ID or get_current_save_id()
        if _WORKING_CHATS_CACHE is None or not _IS_CHATS_DIRTY:
            return

        try:
            disk_data = _read_chats_disk_file()
            if "saves" not in disk_data or not isinstance(disk_data["saves"], dict):
                disk_data["saves"] = {}

            serialized = {_key_to_str(k): v for k, v in _WORKING_CHATS_CACHE.items()}
            if current_save not in disk_data["saves"] or not isinstance(disk_data["saves"][current_save], dict):
                disk_data["saves"][current_save] = {}
            disk_data["saves"][current_save]["chats"] = serialized

            temp_path = CHATS_FILE_PATH + ".tmp"
            os.makedirs(os.path.dirname(CHATS_FILE_PATH), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, ensure_ascii=False, indent=2)

            if os.path.exists(CHATS_FILE_PATH):
                os.replace(temp_path, CHATS_FILE_PATH)
            else:
                os.rename(temp_path, CHATS_FILE_PATH)

            _IS_CHATS_DIRTY = False
            log(f"[CHATS] Committed {len(_WORKING_CHATS_CACHE)} chat session(s) for save '{current_save}' to disk.")
        except Exception as e:
            log_exception("Failed to commit chats to disk", e)


def reset_chats_cache():
    """Clears in-memory working cache upon zone unload/teardown."""
    global _WORKING_CHATS_CACHE, _ACTIVE_CHATS_SAVE_ID, _IS_CHATS_DIRTY, _CHAT_SESSIONS
    with _CHATS_LOCK:
        _WORKING_CHATS_CACHE = None
        _ACTIVE_CHATS_SAVE_ID = None
        _IS_CHATS_DIRTY = False
        _CHAT_SESSIONS.clear()
        log("[CHATS] Working chat cache reset on zone unload.")


def get_session_history(actor_id: int, target_id: int) -> List[Dict[str, Any]]:
    chats = load_chats_data()
    key = get_chat_session_key(actor_id, target_id)
    return chats.get(key, [])


def clear_session_history(actor_id: int, target_id: int):
    chats = load_chats_data()
    key = get_chat_session_key(actor_id, target_id)
    chats.pop(key, None)
    _CHAT_SESSIONS.pop(key, None)
    mark_chats_dirty()
    try:
        from ai_social_pc.delayed_replies import remove_pending_reply
        remove_pending_reply(actor_id, target_id)
        remove_pending_reply(target_id, actor_id)
    except Exception:
        pass
    log(f"Cleared session history for key {key}")


# ---------------------------------------------------------------------------
# Contacted Friends Tracking (Only message if player has messaged them first)
# ---------------------------------------------------------------------------
CONTACTS_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_social_contacts.json")

# In-memory working state for active save slot: { "actor_id_str": [target_id1, target_id2, ...] }
_WORKING_CONTACTS_CACHE: Optional[Dict[str, List[int]]] = None
_ACTIVE_CONTACTS_SAVE_ID: Optional[str] = None
_IS_CONTACTS_DIRTY: bool = False
_CONTACTS_LOCK = threading.RLock()


def _read_contacts_disk_file() -> Dict[str, Any]:
    """Reads the contacts JSON file from disk."""
    if os.path.exists(CONTACTS_FILE_PATH):
        try:
            with open(CONTACTS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_social_contacts.json from disk", e)
    return {"saves": {}}


def load_contacts_data() -> Dict[str, List[int]]:
    """Loads contacted friends data for the current save slot."""
    global _WORKING_CONTACTS_CACHE, _ACTIVE_CONTACTS_SAVE_ID, _IS_CONTACTS_DIRTY
    with _CONTACTS_LOCK:
        from ai_social_pc.group_manager import get_current_save_id
        current_save = get_current_save_id()

        if _WORKING_CONTACTS_CACHE is not None and _ACTIVE_CONTACTS_SAVE_ID == current_save:
            return _WORKING_CONTACTS_CACHE

        _ACTIVE_CONTACTS_SAVE_ID = current_save
        _IS_CONTACTS_DIRTY = False
        disk_data = _read_contacts_disk_file()

        save_entry = disk_data.get("saves", {}).get(current_save, {})
        raw_contacted = save_entry.get("contacted", {}) if isinstance(save_entry, dict) else {}
        _WORKING_CONTACTS_CACHE = {}
        for k, v in raw_contacted.items():
            if isinstance(v, list):
                _WORKING_CONTACTS_CACHE[str(k)] = [int(x) for x in v]

        log(f"[CONTACTS] Loaded contacts cache for save '{current_save}': {len(_WORKING_CONTACTS_CACHE)} player entries")
        return _WORKING_CONTACTS_CACHE


def commit_contacts_to_disk():
    """Commits contacted friends data to disk on game save."""
    global _IS_CONTACTS_DIRTY
    with _CONTACTS_LOCK:
        from ai_social_pc.group_manager import get_current_save_id
        current_save = _ACTIVE_CONTACTS_SAVE_ID or get_current_save_id()
        if _WORKING_CONTACTS_CACHE is None:
            return

        try:
            disk_data = _read_contacts_disk_file()
            disk_data["saves"][current_save] = {
                "contacted": _WORKING_CONTACTS_CACHE,
                "updated_at": int(time.time()),
            }

            temp_path = CONTACTS_FILE_PATH + ".tmp"
            os.makedirs(os.path.dirname(CONTACTS_FILE_PATH), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, ensure_ascii=False, indent=2)

            if os.path.exists(CONTACTS_FILE_PATH):
                os.replace(temp_path, CONTACTS_FILE_PATH)
            else:
                os.rename(temp_path, CONTACTS_FILE_PATH)
            _IS_CONTACTS_DIRTY = False
            log(f"[CONTACTS] Saved ai_social_contacts.json for '{current_save}' successfully.")
        except Exception as e:
            log_exception("Failed to commit ai_social_contacts.json to disk", e)


def reset_contacts_cache():
    """Resets in-memory contacts cache on zone teardown."""
    global _WORKING_CONTACTS_CACHE, _ACTIVE_CONTACTS_SAVE_ID, _IS_CONTACTS_DIRTY
    with _CONTACTS_LOCK:
        _WORKING_CONTACTS_CACHE = None
        _ACTIVE_CONTACTS_SAVE_ID = None
        _IS_CONTACTS_DIRTY = False


def record_player_contacted(actor_id: int, target_id: int):
    """Registers that the player has sent a message to target_id."""
    if not actor_id or not target_id or actor_id == target_id:
        return
    cache = load_contacts_data()
    with _CONTACTS_LOCK:
        global _IS_CONTACTS_DIRTY
        a_key = str(actor_id)
        if a_key not in cache:
            cache[a_key] = []
        t_int = int(target_id)
        if t_int not in cache[a_key]:
            cache[a_key].append(t_int)
            _IS_CONTACTS_DIRTY = True
            log(f"[CONTACTS] Player ID {actor_id} messaged Sim ID {target_id} -> Unlocked incoming friend autonomy!")


def has_player_ever_messaged(actor_id: int, target_id: int) -> bool:
    """Checks whether the player has ever sent a message to target_id."""
    if not actor_id or not target_id or actor_id == target_id:
        return False

    cache = load_contacts_data()
    a_key = str(actor_id)
    t_int = int(target_id)

    # 1. Persistent record
    if a_key in cache and t_int in cache[a_key]:
        return True

    # 2. Check active session history (in case player just typed in this session)
    history = get_session_history(actor_id, target_id)

    for msg in history:
        sender = msg.get("sender", "")
        s_id = msg.get("sender_id", 0)
        s_lower = str(sender).lower()
        if (s_id and s_id == int(actor_id)) or sender in ("Вы", "You") or s_lower in ("вы", "you"):
            record_player_contacted(actor_id, target_id)
            return True

    return False



def get_current_sim_time() -> str:
    """Returns formatted current in-game time (HH:MM)."""
    try:
        if services is not None:
            now = None
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
            elif services.game_clock_service() is not None:
                now = services.game_clock_service().now()

            if now is not None:
                h_val = getattr(now, "hour", 12)
                hour = h_val() if callable(h_val) else int(h_val)
                m_val = getattr(now, "minute", 0)
                minute = m_val() if callable(m_val) else int(m_val)
                return f"{hour:02d}:{minute:02d}"
    except Exception:
        pass
    import time
    return time.strftime("%H:%M")


def get_current_sim_absolute_days() -> int:
    """Returns absolute in-game day counter (0, 1, 2, ...)."""
    try:
        if services is not None:
            now = None
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
            elif services.game_clock_service() is not None:
                now = services.game_clock_service().now()

            if now is not None:
                if hasattr(now, "absolute_days"):
                    res = now.absolute_days()
                    return int(res() if callable(res) else res)
                if hasattr(now, "day"):
                    res = now.day()
                    return int(res() if callable(res) else res)
    except Exception:
        pass
    import time
    return int(time.strftime("%j"))


def get_current_sim_day_of_week() -> str:
    """Returns day of the week: Sun, Mon, etc. in EN, or Вс, Пн, etc. in RU."""
    is_en = False
    try:
        from ai_social_pc.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        is_en = False

    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] if is_en else ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    try:
        if services is not None:
            now = None
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
            elif services.game_clock_service() is not None:
                now = services.game_clock_service().now()

            if now is not None and hasattr(now, "day"):
                res = now.day()
                idx = int(res() if callable(res) else res)
                return day_names[idx % len(day_names)]
    except Exception:
        pass
    import time
    idx = int(time.strftime("%w"))
    return day_names[idx % len(day_names)]


def get_relative_day_label(msg_abs_day: int, cur_abs_day: int, dow: str = "") -> str:
    """Returns relative day label: Today, Yesterday, or Сегодня, Вчера, etc."""
    is_en = False
    try:
        from ai_social_pc.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        is_en = False

    try:
        diff = int(cur_abs_day) - int(msg_abs_day)
    except Exception:
        diff = 0

    if is_en:
        if diff <= 0:
            return "Today"
        elif diff == 1:
            return "Yesterday"
        elif diff == 2:
            return "2 days ago"
        elif dow:
            return f"{dow} ({diff} days ago)"
        else:
            return f"{diff} days ago"
    else:
        if diff <= 0:
            return "Сегодня"
        elif diff == 1:
            return "Вчера"
        elif diff == 2:
            return "Позавчера"
        elif dow:
            return f"{dow} ({diff} дн. назад)"
        else:
            return f"{diff} дн. назад"


def strip_emojis(text: str) -> str:
    """Strips unicode emojis and symbols that cause black rectangles ❚ in The Sims 4 Flash UI."""
    if not text:
        return ""
    # Strip 4-byte UTF-8 emojis, symbol dingbats and surrogate blocks
    clean = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\ufe00-\ufe0f]', '', str(text))
    # Clean out any stray box / illegal characters
    clean = clean.replace("❚", "").replace("■", "").replace("□", "")
    return re.sub(r'\s+', ' ', clean).strip()


def parse_and_strip_relationship_tags(text: str) -> Tuple[str, int, int]:
    """
    Extracts [FR=...] and [ROM=...] tags, clamps them (-30..+15), and removes them from text.
    Returns tuple: (cleaned_text, delta_friendship, delta_romance)
    """
    if not text:
        return "", 0, 0

    delta_fr = 0
    delta_rom = 0

    fr_m = re.search(r'\[FR\s*=\s*([+-]?\d+)\]', text, re.IGNORECASE)
    if fr_m:
        try:
            delta_fr = int(fr_m.group(1))
        except Exception:
            delta_fr = 0

    rom_m = re.search(r'\[ROM\s*=\s*([+-]?\d+)\]', text, re.IGNORECASE)
    if rom_m:
        try:
            delta_rom = int(rom_m.group(1))
        except Exception:
            delta_rom = 0

    delta_fr = max(-30, min(15, delta_fr))
    delta_rom = max(-30, min(15, delta_rom))

    clean = re.sub(r'\[FR\s*=\s*[+-]?\d+\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'\[ROM\s*=\s*[+-]?\d+\]', '', clean, flags=re.IGNORECASE)
    return clean.strip(), delta_fr, delta_rom


def add_session_message(
    actor_id: int,
    target_id: int,
    sender: str,
    text: str,
    sender_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Appends a sanitized message to active session history with timestamp, in-game day, and sender ID."""
    chats = load_chats_data()
    key = get_chat_session_key(actor_id, target_id)
    if key not in chats:
        chats[key] = []
    cur_time = get_current_sim_time()
    cur_day = get_current_sim_absolute_days()
    dow = get_current_sim_day_of_week()
    clean_t = strip_emojis(text)

    # Determine real sender_id
    real_sender_id = 0
    if sender_id is not None and int(sender_id) != 0:
        real_sender_id = int(sender_id)
    elif sender in ("Вы", "You") or str(sender).lower() in ("вы", "you"):
        real_sender_id = int(actor_id)
    else:
        real_sender_id = int(target_id)

    msg_obj = {
        "sender": sender,
        "sender_id": real_sender_id,
        "text": clean_t,
        "time": cur_time,
        "abs_day": cur_day,
        "dow": dow,
    }
    chats[key].append(msg_obj)
    # Strictly maintain rolling window of max 15 messages
    if len(chats[key]) > 15:
        chats[key] = chats[key][-15:]

    mark_chats_dirty()
    _CHAT_SESSIONS[key] = chats[key]

    # If the player sent this message, unlock spontaneous friend autonomy for this target
    s_is_player = (sender in ("Вы", "You") or str(sender).lower() in ("вы", "you") or real_sender_id == int(actor_id))
    if s_is_player:
        record_player_contacted(actor_id, target_id)

    return msg_obj


def _build_sim_profile_summary(sim_info, is_actor: bool = False) -> str:
    """Builds a complete, rich profile of a Sim for chat roleplay matching the full AI Read specification."""
    try:
        from ai_social_pc.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        is_en = False

    if sim_info is None:
        return "Unknown Sim" if is_en else "Неизвестный персонаж"

    if isinstance(sim_info, dict):
        return sim_info.get("summary", "Virtual Contact" if is_en else "Виртуальный собеседник")

    f_name = getattr(sim_info, "first_name", "") or ""
    l_name = getattr(sim_info, "last_name", "") or ""
    full_name = f"{f_name} {l_name}".strip() or ("Sim" if is_en else "Сим")

    gender_raw = getattr(getattr(sim_info, "gender", None), "name", "").upper()
    age_raw = getattr(getattr(sim_info, "age", None), "name", "").upper()

    if is_en:
        lines = [f"- Name: {full_name}"]
        gender_map_en = {"MALE": "Male", "FEMALE": "Female"}
        age_map_en = {
            "BABY": "Newborn",
            "INFANT": "Infant",
            "TODDLER": "Toddler",
            "CHILD": "Child",
            "TEEN": "Teen",
            "YOUNGADULT": "Young Adult",
            "ADULT": "Adult",
            "ELDER": "Elder",
        }
        g_str = gender_map_en.get(gender_raw, gender_raw)
        a_str = age_map_en.get(age_raw, age_raw)
        if get_chat_context_flag("chat_age_gender"):
            if g_str and a_str:
                lines.append(f"- Age & Gender: {a_str}, {g_str}")
            elif g_str:
                lines.append(f"- Gender: {g_str}")
            elif a_str:
                lines.append(f"- Age: {a_str}")

        if get_chat_context_flag("chat_occult") and _HAS_THOUGHT_READER and get_sim_occult_info:
            try:
                race = get_sim_occult_info(sim_info, is_en=True)
                if race:
                    try:
                        from ai_thought_reader.context_en import translate_occult_en
                        race = translate_occult_en(race)
                    except Exception:
                        pass
                    lines.append(f"- Race: {race}")
            except Exception:
                pass

        sim_instance = getattr(sim_info, "get_sim_instance", lambda: None)()
        is_on_active_lot = False
        if sim_instance is not None:
            if hasattr(sim_instance, "is_on_active_lot"):
                try:
                    is_on_active_lot = sim_instance.is_on_active_lot()
                except Exception:
                    is_on_active_lot = True
            else:
                is_on_active_lot = True

        if get_chat_context_flag("chat_family") and _HAS_THOUGHT_READER and get_sim_family_info:
            try:
                family_members = get_sim_family_info(sim_info)
                if family_members:
                    lines.append("- Family, Partner & Relatives:")
                    for f_mem in family_members:
                        try:
                            from ai_thought_reader.context_en import translate_family_member_en
                            lines.append(f"  • {translate_family_member_en(f_mem)}")
                        except Exception:
                            lines.append(f"  • {f_mem}")
                else:
                    lines.append("- Family & Personal Life: Single (no partner or known relatives)")
            except Exception:
                pass

        if get_chat_context_flag("chat_roommates") and _HAS_THOUGHT_READER and get_household_roommates_info:
            try:
                roommates = get_household_roommates_info(sim_info)
                if roommates:
                    lines.append("- Household Roommates (living together, non-relatives):")
                    for rm in roommates:
                        try:
                            from ai_thought_reader.context_en import translate_nearby_sim_en
                            lines.append(f"  • {translate_nearby_sim_en(rm)}")
                        except Exception:
                            lines.append(f"  • {rm}")
                else:
                    lines.append("- Household Roommates: No roommates (lives alone or only with family)")
            except Exception:
                pass

        if get_chat_context_flag("chat_pets") and _HAS_THOUGHT_READER and get_household_pets_info:
            try:
                pets = get_household_pets_info(sim_info)
                if pets:
                    p_cnt = len(pets)
                    p_word = "pet" if p_cnt == 1 else "pets"
                    lines.append(f"- Household Pets: {p_cnt} {p_word} — " + ", ".join(pets))
                else:
                    lines.append("- Household Pets: No pets in household")
            except Exception:
                pass

        if get_chat_context_flag("chat_mood"):
            if _HAS_THOUGHT_READER and get_sim_mood_info:
                try:
                    mood_str = get_sim_mood_info(sim_info, include_reason=is_on_active_lot)
                    if mood_str:
                        try:
                            from ai_thought_reader.context_en import translate_mood_en
                            mood_str = translate_mood_en(mood_str)
                        except Exception:
                            pass
                        lines.append(f"- Current Mood: {mood_str}")
                except Exception:
                    pass
            else:
                try:
                    if hasattr(sim_info, "get_mood"):
                        m = sim_info.get_mood()
                        if m:
                            lines.append(f"- Current Mood: {getattr(m, 'name', str(m))}")
                except Exception:
                    pass

        if get_chat_context_flag("chat_location"):
            if is_on_active_lot:
                if _HAS_THOUGHT_READER and get_current_location:
                    try:
                        loc = get_current_location(sim_info)
                        try:
                            from ai_thought_reader.context_en import translate_location_en
                            loc = translate_location_en(loc)
                        except Exception:
                            pass
                        lines.append(f"- Current Location: {loc}")
                    except Exception:
                        lines.append("- Current Location: On current lot")
                else:
                    lines.append("- Current Location: On current lot")
            else:
                loc = "On another lot"
                if _HAS_THOUGHT_READER and get_sim_home_world_name:
                    try:
                        hw = get_sim_home_world_name(sim_info)
                        if hw:
                            from ai_thought_reader.context_en import WORLD_NAMES_MAP_EN, WORLD_DESCRIPTIONS_EN
                            from ai_thought_reader.config import get_experimental_flag
                            hw_en = WORLD_NAMES_MAP_EN.get(hw, hw)
                            if get_experimental_flag("enhanced_world_descriptions"):
                                desc_en = WORLD_DESCRIPTIONS_EN.get(hw_en, "")
                                if desc_en:
                                    loc = f"On another lot in {hw_en} ({desc_en})"
                                else:
                                    loc = f"On another lot in {hw_en}"
                            else:
                                loc = f"On another lot in {hw_en}"
                    except Exception:
                        pass
                lines.append(f"- Current Location: {loc}")

        if get_chat_context_flag("chat_traits"):
            if _HAS_THOUGHT_READER and get_sim_traits_info:
                try:
                    traits = get_sim_traits_info(sim_info)
                    if traits:
                        t_str = ", ".join(traits)
                        try:
                            from ai_thought_reader.context_en import translate_traits_en
                            t_str = translate_traits_en(t_str)
                        except Exception:
                            pass
                        lines.append(f"- Character Traits: {t_str}")
                except Exception:
                    pass
            else:
                try:
                    trait_tracker = getattr(sim_info, "trait_tracker", None)
                    if trait_tracker is not None:
                        t_names = [getattr(t, "__name__", str(t)) for t in trait_tracker.personality_traits]
                        if t_names:
                            lines.append(f"- Character Traits: {', '.join(t_names)}")
                except Exception:
                    pass

            # Classic Insane Trait Guidance (Chat / Dialogue - EN)
            try:
                from ai_thought_reader.config import get_experimental_flag
                if get_experimental_flag("classic_insane_trait"):
                    is_insane = False
                    if _HAS_THOUGHT_READER and get_sim_traits_info:
                        tr_list = get_sim_traits_info(sim_info) or []
                        if any(k in str(tr_list).lower() for k in ["чудаковатый", "безумный", "erratic", "insane"]):
                            is_insane = True
                    if not is_insane:
                        trait_tracker = getattr(sim_info, "trait_tracker", None)
                        if trait_tracker is not None:
                            t_names = [getattr(t, "__name__", str(t)).lower() for t in getattr(trait_tracker, "personality_traits", ())]
                            if any(k in " ".join(t_names) for k in ["insane", "erratic"]):
                                is_insane = True
                    if is_insane:
                        lines.append(
                            "- Personality Note (Classic Insane Trait): The character's 'Erratic' trait operates in classic 'Insane' mode. "
                            "In conversation, they speak chaotically, unpredictably, with surreal logic, paranoia, talking to objects, or sudden weird conspiracy theories."
                        )
            except Exception:
                pass

        if get_chat_context_flag("chat_lore"):
            sim_id = getattr(sim_info, "sim_id", None)
            if sim_id and _HAS_THOUGHT_READER and get_custom_sim_lore:
                try:
                    lore = get_custom_sim_lore(sim_id)
                    if lore:
                        lines.append(f"- Additional Lore (Personal Backstory): {lore}")
                except Exception:
                    pass

        if get_chat_context_flag("chat_pregnancy") and _HAS_THOUGHT_READER and get_sim_pregnancy_info:
            try:
                preg = get_sim_pregnancy_info(sim_info)
                if preg:
                    try:
                        from ai_thought_reader.context_en import translate_pregnancy_en
                        preg = translate_pregnancy_en(preg)
                    except Exception:
                        pass
                    lines.append(f"- Pregnancy: {preg}")
            except Exception:
                pass

        if get_chat_context_flag("chat_fame") and _HAS_THOUGHT_READER and get_sim_fame_and_reputation_info:
            try:
                fame = get_sim_fame_and_reputation_info(sim_info)
                if fame:
                    try:
                        from ai_thought_reader.context_en import translate_fame_en
                        fame = translate_fame_en(fame)
                    except Exception:
                        pass
                    lines.append(f"- Fame & Reputation: {fame}")
            except Exception:
                pass

        if get_chat_context_flag("chat_career") and _HAS_THOUGHT_READER and get_sim_career_info:
            try:
                career = get_sim_career_info(sim_info)
                if career:
                    try:
                        from ai_thought_reader.context_en import translate_career_en
                        career = translate_career_en(career)
                    except Exception:
                        pass
                    lines.append(f"- Career & Profession: {career}")
            except Exception:
                pass

        if get_chat_context_flag("chat_aspiration") and _HAS_THOUGHT_READER and get_sim_aspiration_info:
            try:
                aspiration = get_sim_aspiration_info(sim_info)
                if aspiration:
                    try:
                        from ai_thought_reader.context_en import translate_aspiration_en
                        aspiration = translate_aspiration_en(aspiration)
                    except Exception:
                        pass
                    lines.append(f"- Aspiration & Life Goal: {aspiration}")
            except Exception:
                pass

        if get_chat_context_flag("chat_funds") and _HAS_THOUGHT_READER and get_household_funds_info:
            try:
                funds = get_household_funds_info(sim_info)
                if funds:
                    try:
                        from ai_thought_reader.context_en import translate_funds_en
                        funds = translate_funds_en(funds)
                    except Exception:
                        pass
                    lines.append(f"- Household Budget: {funds}")
            except Exception:
                pass

        clean_lines = []
        for line in lines:
            if line.startswith("- Additional Lore (Personal Backstory):"):
                clean_lines.append(line)
            elif any('\u0400' <= c <= '\u04FF' for c in line):
                try:
                    from ai_thought_reader.context_en import transliterate_to_latin
                    clean_lines.append(transliterate_to_latin(line))
                except Exception:
                    clean_lines.append(line)
            else:
                clean_lines.append(line)
        return "\n".join(clean_lines)

    lines = []
    lines.append(f"- Имя: {full_name}")
    gender_map = {"MALE": "Мужской", "FEMALE": "Женский"}
    age_map = {
        "BABY": "Новорожденный",
        "INFANT": "Младенец",
        "TODDLER": "Малыш",
        "CHILD": "Ребенок",
        "TEEN": "Подросток",
        "YOUNGADULT": "Молодой(ая)",
        "ADULT": "Взрослый(ая)",
        "ELDER": "Пожилой(ая)",
    }
    g_str = gender_map.get(gender_raw, gender_raw)
    a_str = age_map.get(age_raw, age_raw)
    if get_chat_context_flag("chat_age_gender"):
        if g_str and a_str:
            lines.append(f"- Возраст и пол: {a_str}, {g_str}")
        elif g_str:
            lines.append(f"- Пол: {g_str}")
        elif a_str:
            lines.append(f"- Возраст: {a_str}")

    # Race / Occult Type
    if get_chat_context_flag("chat_occult") and _HAS_THOUGHT_READER and get_sim_occult_info:
        try:
            race = get_sim_occult_info(sim_info, is_en=False)
            if race:
                lines.append(f"- Раса: {race}")
        except Exception:
            pass


    # Determine whether the Sim is physically spawned on the active lot
    sim_instance = getattr(sim_info, "get_sim_instance", lambda: None)()
    is_on_active_lot = False
    if sim_instance is not None:
        if hasattr(sim_instance, "is_on_active_lot"):
            try:
                is_on_active_lot = sim_instance.is_on_active_lot()
            except Exception:
                is_on_active_lot = True
        else:
            is_on_active_lot = True


    # Family & Relatives
    if get_chat_context_flag("chat_family") and _HAS_THOUGHT_READER and get_sim_family_info:
        try:
            family_members = get_sim_family_info(sim_info)
            if family_members:
                lines.append("- Семья, пара и родственники:")
                for f_mem in family_members:
                    lines.append(f"  • {f_mem}")
            else:
                lines.append("- Семья и личная жизнь: Одинок (нет пары и известных родственников)")
        except Exception:
            pass

    # Household Roommates
    if get_chat_context_flag("chat_roommates") and _HAS_THOUGHT_READER and get_household_roommates_info:
        try:
            roommates = get_household_roommates_info(sim_info)
            if roommates:
                lines.append("- Соседи по дому (живут вместе, не родственники):")
                for rm in roommates:
                    lines.append(f"  • {rm}")
            else:
                lines.append("- Соседи по дому: Нет соседей (проживает только с семьёй или один)")
        except Exception:
            pass

    # Household Pets
    if get_chat_context_flag("chat_pets") and _HAS_THOUGHT_READER and get_household_pets_info:
        try:
            pets = get_household_pets_info(sim_info)
            if pets:
                p_cnt = len(pets)
                p_word = "питомец" if p_cnt == 1 else ("питомца" if p_cnt < 5 else "питомцев")
                lines.append(f"- Домашние питомцы в семье: {p_cnt} {p_word} — " + ", ".join(pets))
            else:
                lines.append("- Домашние питомцы в семье: Нет домашних животных")
        except Exception:
            pass

    # Mood:
    # Crucial user requirement:
    # If on active lot -> full mood with dominant buff reason (e.g. "Счастливое (Причина: Отличная еда)")
    # If on another lot -> basic mood WITHOUT buff reason (e.g. "Счастливое")
    if get_chat_context_flag("chat_mood"):
        if _HAS_THOUGHT_READER and get_sim_mood_info:
            try:
                mood_str = get_sim_mood_info(sim_info, include_reason=is_on_active_lot)
                if mood_str:
                    lines.append(f"- Текущее настроение: {mood_str}")
            except Exception:
                pass
        else:
            try:
                if hasattr(sim_info, "get_mood"):
                    m = sim_info.get_mood()
                    if m:
                        lines.append(f"- Текущее настроение: {getattr(m, 'name', str(m))}")
            except Exception:
                pass

    # Location:
    # Crucial user requirement:
    # If on active lot -> full location with inside/outside/world
    # If on another lot -> "Находится на другом участке" (without inside/outside and without claiming they are on the player's active lot)
    if get_chat_context_flag("chat_location"):
        if is_on_active_lot:
            if _HAS_THOUGHT_READER and get_current_location:
                try:
                    loc = get_current_location(sim_info)
                    lines.append(f"- Текущая локация: {loc}")
                except Exception:
                    lines.append("- Текущая локация: На текущем участке")
            else:
                lines.append("- Текущая локация: На текущем участке")
        else:
            loc = "Находится на другом участке"
            if _HAS_THOUGHT_READER and get_sim_home_world_name:
                try:
                    hw = get_sim_home_world_name(sim_info)
                    if hw:
                        from ai_thought_reader.config import get_experimental_flag
                        if get_experimental_flag("enhanced_world_descriptions"):
                            from ai_thought_reader.context import WORLD_DESCRIPTIONS_RU
                            desc = WORLD_DESCRIPTIONS_RU.get(hw, "")
                            if desc:
                                loc = f"Находится на другом участке (г. {hw} — {desc})"
                            else:
                                loc = f"Находится на другом участке (г. {hw})"
                        else:
                            loc = f"Находится на другом участке (г. {hw})"
                except Exception:
                    pass
            lines.append(f"- Текущая локация: {loc}")


    # Traits
    if get_chat_context_flag("chat_traits"):
        if _HAS_THOUGHT_READER and get_sim_traits_info:
            try:
                traits = get_sim_traits_info(sim_info)
                if traits:
                    lines.append(f"- Черты характера: {', '.join(traits)}")
            except Exception:
                pass
        else:
            try:
                trait_tracker = getattr(sim_info, "trait_tracker", None)
                if trait_tracker is not None:
                    t_names = [getattr(t, "__name__", str(t)) for t in trait_tracker.personality_traits]
                    if t_names:
                        lines.append(f"- Черты характера: {', '.join(t_names)}")
            except Exception:
                pass

        # Classic Insane Trait Guidance (Chat / Dialogue - RU)
        try:
            from ai_thought_reader.config import get_experimental_flag
            if get_experimental_flag("classic_insane_trait"):
                is_insane = False
                if _HAS_THOUGHT_READER and get_sim_traits_info:
                    tr_list = get_sim_traits_info(sim_info) or []
                    if any(k in str(tr_list).lower() for k in ["чудаковатый", "безумный", "erratic", "insane"]):
                        is_insane = True
                if not is_insane:
                    trait_tracker = getattr(sim_info, "trait_tracker", None)
                    if trait_tracker is not None:
                        t_names = [getattr(t, "__name__", str(t)).lower() for t in getattr(trait_tracker, "personality_traits", ())]
                        if any(k in " ".join(t_names) for k in ["insane", "erratic"]):
                            is_insane = True
                if is_insane:
                    lines.append(
                        "- Особенность характера (Черта «Безумный» / Классическое безумие): Черта «Чудаковатый» действует в классическом режиме «Безумный» (Insane из TS3 и раннего TS4). "
                        "В разговоре персонаж общается сумбурно, непредсказуемо, с сюрреалистичной логикой, бредовыми теориями заговора, паранойей, разговорами с неодушевленными предметами или внезапными причудами."
                    )
        except Exception:
            pass

    # Custom Sim Lore / Biography
    if get_chat_context_flag("chat_lore"):
        sim_id = getattr(sim_info, "sim_id", None)
        if sim_id and _HAS_THOUGHT_READER and get_custom_sim_lore:
            try:
                lore = get_custom_sim_lore(sim_id)
                if lore:
                    lines.append(f"- Дополнительные сведения о персонаже (личная биография): {lore}")
            except Exception:
                pass

    # Pregnancy
    if get_chat_context_flag("chat_pregnancy") and _HAS_THOUGHT_READER and get_sim_pregnancy_info:
        try:
            preg = get_sim_pregnancy_info(sim_info)
            if preg:
                lines.append(f"- Беременность: {preg}")
        except Exception:
            pass

    # Fame & Reputation
    if get_chat_context_flag("chat_fame") and _HAS_THOUGHT_READER and get_sim_fame_and_reputation_info:
        try:
            fame = get_sim_fame_and_reputation_info(sim_info)
            if fame:
                lines.append(f"- Слава и репутация: {fame}")
        except Exception:
            pass

    # Career
    if get_chat_context_flag("chat_career") and _HAS_THOUGHT_READER and get_sim_career_info:
        try:
            career = get_sim_career_info(sim_info)
            if career:
                lines.append(f"- Профессия и должность: {career}")
        except Exception:
            pass

    # Aspiration
    if get_chat_context_flag("chat_aspiration") and _HAS_THOUGHT_READER and get_sim_aspiration_info:
        try:
            aspiration = get_sim_aspiration_info(sim_info)
            if aspiration:
                lines.append(f"- Жизненная цель: {aspiration}")
        except Exception:
            pass

    # Household Funds
    if get_chat_context_flag("chat_funds") and _HAS_THOUGHT_READER and get_household_funds_info:
        try:
            funds = get_household_funds_info(sim_info)
            if funds:
                lines.append(f"- Бюджет семьи: {funds}")
        except Exception:
            pass

    return "\n".join(lines)


def _get_relationship_description(actor_info, recipient_info) -> str:
    """
    Gets relationship string describing who actor_info (sender) is to recipient_info (responder).
    E.g. If actor is brother, returns 'Знакомый, Брат' or 'Жена, Сестра [инцест]'.
    """
    is_en = False
    try:
        from ai_social_pc.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        pass

    if not get_chat_context_flag("chat_relationship"):
        return "Chat Partners" if is_en else "Собеседники"

    if isinstance(recipient_info, dict):
        rel = recipient_info.get("relationship", "Online Contacts" if is_en else "Сетевые собеседники")
        if is_en:
            try:
                from ai_thought_reader.context_en import translate_relationship_en
                return translate_relationship_en(rel)
            except Exception:
                return rel
        return rel

    rel = "Знакомые"
    if _HAS_THOUGHT_READER and get_relationship_between_sims:
        try:
            # Target is actor_info (sender), source is recipient_info
            r = get_relationship_between_sims(recipient_info, actor_info)
            if r:
                rel = r
        except Exception:
            pass

    if not get_chat_context_flag("chat_incest"):
        rel = re.sub(r'\s*\[инцест.*?\]', '', rel, flags=re.IGNORECASE).strip()

    try:
        from ai_social_pc.localization import get_game_language
        if get_game_language() == "en":
            try:
                from ai_thought_reader.context_en import translate_relationship_en
                rel = translate_relationship_en(rel)
            except Exception:
                pass
    except Exception:
        pass

    return rel


def get_sim_work_or_school_status(sim_info) -> Dict[str, Any]:
    """
    Determines if a Sim is currently attending work or school/university.
    Returns:
      {
        "is_busy": bool,
        "activity_type": "work" | "school" | None,
        "career_name": str,
        "detail_text": str,
      }
    """
    default_res = {
        "is_busy": False,
        "activity_type": None,
        "career_name": "",
        "detail_text": "",
    }
    if sim_info is None or isinstance(sim_info, dict):
        return default_res

    try:
        career_tracker = getattr(sim_info, "career_tracker", None)
        if career_tracker is None:
            return default_res

        # 1. Primary check: at-work career object from tracker
        active_career = None
        if hasattr(career_tracker, "get_at_work_career"):
            active_career = career_tracker.get_at_work_career()

        # Check if sim is physically spawned on the active lot
        sim_instance = getattr(sim_info, "get_sim_instance", lambda: None)()
        is_on_lot = False
        if sim_instance is not None:
            if hasattr(sim_instance, "is_on_active_lot"):
                try:
                    is_on_lot = sim_instance.is_on_active_lot()
                except Exception:
                    is_on_lot = True
            else:
                is_on_lot = True

        # 2. Secondary check: iterate all careers
        if active_career is None:
            careers_dict = getattr(career_tracker, "_careers", None) or getattr(career_tracker, "careers", {})
            for c in careers_dict.values():
                if getattr(c, "currently_at_work", False):
                    active_career = c
                    break
                # If sim is not on the active lot, check scheduled work/school time
                if not is_on_lot and hasattr(c, "is_work_time") and c.is_work_time:
                    # Exclude days off or vacation
                    if not getattr(c, "taking_day_off", False) and not getattr(c, "on_vacation", False):
                        active_career = c
                        break

        if active_career is None:
            return default_res

        c_name = getattr(active_career, "__name__", str(active_career)).lower()
        cat_val = getattr(active_career, "career_category", None)
        cat_int = int(cat_val) if cat_val is not None else -1

        # CareerCategory: 2 = School, 6 = UniversityCourse
        is_school = (cat_int in (2, 6)) or any(k in c_name for k in ("school", "grade", "highschool", "university", "college", "degree", "education_student"))

        # Find human-readable translated name if available
        matched_title = ""
        if _HAS_THOUGHT_READER:
            try:
                from ai_thought_reader.context import CAREER_TRANSLATIONS
                for k, v in CAREER_TRANSLATIONS.items():
                    if k in c_name:
                        matched_title = v
                        break
            except Exception:
                pass

        if not matched_title:
            matched_title = c_name.replace("career_", "").replace("adult_", "").replace("teen_", "").replace("child_", "").capitalize()

        if is_school:
            if any(u in c_name for u in ("university", "college", "degree")) or cat_int == 6:
                detail = "в университете на парах/лекциях"
            elif "grade" in c_name:
                detail = "в младшей школе на уроках"
            elif "high" in c_name:
                detail = "в старшей школе на уроках"
            else:
                detail = "на учёбе (на уроках/занятиях)"

            return {
                "is_busy": True,
                "activity_type": "school",
                "career_name": matched_title or "Школа/Учёба",
                "detail_text": detail,
            }
        else:
            return {
                "is_busy": True,
                "activity_type": "work",
                "career_name": matched_title,
                "detail_text": f"на работе ({matched_title})" if matched_title else "на работе",
            }

    except Exception as e:
        log_exception("Error in get_sim_work_or_school_status", e)
        return default_res


def build_work_or_school_prompt_context(sender_name: str, recipient_name: str, status_info: Dict[str, Any]) -> Optional[str]:
    """
    Builds the situational prompt note when recipient Sim is currently at work or school.
    """
    if not status_info or not status_info.get("is_busy"):
        return None

    act_type = status_info.get("activity_type")
    detail = status_info.get("detail_text", "")

    if act_type == "school":
        return (
            f"ВАЖНОЕ ОБСТОЯТЕЛЬСТВО: Вы ({recipient_name}) прямо сейчас находитесь НА УЧЁБЕ ({detail}). "
            f"Собеседник {sender_name} написал вам прямо во время учебного процесса. "
            f"Вы прямо сейчас заглянули в телефон/мессенджер, чтобы ответить ему. "
            f"ВАЖНО: {sender_name} не на вашей учёбе — на уроках/парах находитесь именно ВЫ ({recipient_name}). "
            f"Ответьте естественно от первого лица с учётом того, что вы сейчас на учёбе (можете упомянуть урок, пару, учительницу/преподавателя, перемену или школьную обстановку)."
        )
    elif act_type == "work":
        return (
            f"ВАЖНОЕ ОБСТОЯТЕЛЬСТВО: Вы ({recipient_name}) прямо сейчас находитесь НА РАБОТЕ ({detail}). "
            f"Собеседник {sender_name} написал вам прямо в разгар рабочего дня. "
            f"Вы прямо сейчас заглянули в телефон/мессенджер, чтобы ответить ему. "
            f"ВАЖНО: {sender_name} не на вашей работе — на смене находитесь именно ВЫ ({recipient_name}). "
            f"Ответьте естественно от первого лица с учётом того, что вы сейчас на работе (можете упомянуть рабочие дела, клиентов/задачи, усталость, начальника или рабочую обстановку)."
        )

    return None


_FRIENDSHIP_TRACK = None
_ROMANCE_TRACK = None


def _get_friendship_track():
    global _FRIENDSHIP_TRACK
    if _FRIENDSHIP_TRACK is not None:
        return _FRIENDSHIP_TRACK
    try:
        from relationships.global_relationship_tuning import RelationshipGlobalTuning
        if hasattr(RelationshipGlobalTuning, "REL_INSPECTOR_TRACK") and RelationshipGlobalTuning.REL_INSPECTOR_TRACK is not None:
            _FRIENDSHIP_TRACK = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
            return _FRIENDSHIP_TRACK
    except Exception:
        pass

    if services is not None:
        try:
            import sims4.resources
            stat_mgr = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            if stat_mgr is not None:
                cand = stat_mgr.get(FRIENDSHIP_TRACK_ID)
                if cand is not None:
                    _FRIENDSHIP_TRACK = cand
                    return _FRIENDSHIP_TRACK
                for cls in stat_mgr.types.values():
                    if getattr(cls, "__name__", "") == "LTR_Friendship_Main":
                        _FRIENDSHIP_TRACK = cls
                        return _FRIENDSHIP_TRACK
        except Exception:
            pass
    return None


def _get_romance_track():
    global _ROMANCE_TRACK
    if _ROMANCE_TRACK is not None:
        return _ROMANCE_TRACK

    if services is not None:
        try:
            from server_commands.argument_helpers import get_tunable_instance
            import sims4.resources
            cand = get_tunable_instance(sims4.resources.Types.STATISTIC, "LTR_Romance_Main", exact_match=True)
            if cand is not None:
                _ROMANCE_TRACK = cand
                return _ROMANCE_TRACK
        except Exception:
            pass

        try:
            import sims4.resources
            stat_mgr = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            if stat_mgr is not None:
                cand = stat_mgr.get(ROMANCE_TRACK_ID)
                if cand is not None:
                    _ROMANCE_TRACK = cand
                    return _ROMANCE_TRACK
                for cls in stat_mgr.types.values():
                    if getattr(cls, "__name__", "") == "LTR_Romance_Main":
                        _ROMANCE_TRACK = cls
                        return _ROMANCE_TRACK
        except Exception:
            pass
    return None


def apply_chat_relationship_impact(actor_sim_info, recipient_sim_info, delta_fr: int = 0, delta_rom: int = 0):
    """
    Applies dynamic relationship score delta (friendship & romance) between the two Sims.
    Logs previous score -> delta -> new score for transparency and verification.
    """
    if actor_sim_info is None or recipient_sim_info is None or isinstance(recipient_sim_info, dict):
        return

    if delta_fr == 0 and delta_rom == 0:
        return

    try:
        actor_id = getattr(actor_sim_info, "sim_id", None)
        target_id = getattr(recipient_sim_info, "sim_id", None)
        if not actor_id or not target_id or actor_id == target_id:
            return

        rel_tracker = getattr(actor_sim_info, "relationship_tracker", None)
        if rel_tracker is None:
            return

        actor_name = f"{getattr(actor_sim_info, 'first_name', '')} {getattr(actor_sim_info, 'last_name', '')}".strip() or str(actor_id)
        target_name = f"{getattr(recipient_sim_info, 'first_name', '')} {getattr(recipient_sim_info, 'last_name', '')}".strip() or str(target_id)

        rel_service = services.relationship_service() if services is not None else None

        if delta_fr != 0 and hasattr(rel_tracker, "add_relationship_score"):
            fr_track = _get_friendship_track()
            old_fr = None
            if hasattr(rel_tracker, "get_relationship_score"):
                try:
                    old_fr = rel_tracker.get_relationship_score(target_id, fr_track) if fr_track else rel_tracker.get_relationship_score(target_id)
                except Exception:
                    pass

            if fr_track is not None:
                rel_tracker.add_relationship_score(target_id, float(delta_fr), fr_track)
            else:
                rel_tracker.add_relationship_score(target_id, float(delta_fr))

            new_fr = None
            if hasattr(rel_tracker, "get_relationship_score"):
                try:
                    new_fr = rel_tracker.get_relationship_score(target_id, fr_track) if fr_track else rel_tracker.get_relationship_score(target_id)
                except Exception:
                    pass

            old_s = f"{old_fr:.1f}" if old_fr is not None else "?"
            new_s = f"{new_fr:.1f}" if new_fr is not None else "?"
            log(f"[RELATIONSHIP] Friendship between {actor_name} and {target_name}: {old_s} -> {new_s} (delta: {delta_fr:+d})")

        if delta_rom != 0 and hasattr(rel_tracker, "add_relationship_score"):
            rom_track = _get_romance_track()
            if rom_track is not None:
                # Ensure romance track is instantiated in relationship tracker if not present yet
                if rel_service is not None:
                    try:
                        if not rel_service.has_relationship_track(actor_id, target_id, rom_track):
                            rel_service.set_can_add_reltrack(actor_id, target_id, True)
                            rel_service.get_relationship_track(actor_id, target_id, track=rom_track, add=True)
                    except Exception as e_rt:
                        log_exception("Error ensuring romance track exists in chat_manager", e_rt)

                old_rom = None
                if hasattr(rel_tracker, "get_relationship_score"):
                    try:
                        old_rom = rel_tracker.get_relationship_score(target_id, rom_track)
                    except Exception:
                        pass

                rel_tracker.add_relationship_score(target_id, float(delta_rom), rom_track)

                new_rom = None
                if hasattr(rel_tracker, "get_relationship_score"):
                    try:
                        new_rom = rel_tracker.get_relationship_score(target_id, rom_track)
                    except Exception:
                        pass

                # Update relationship info on client UI immediately
                if rel_service is not None:
                    try:
                        rel_service.send_relationship_info(actor_id, target_sim_id=target_id)
                        rel_service.send_relationship_info(target_id, target_sim_id=actor_id)
                    except Exception:
                        pass

                old_s = f"{old_rom:.1f}" if old_rom is not None else "?"
                new_s = f"{new_rom:.1f}" if new_rom is not None else "?"
                log(f"[RELATIONSHIP] Romance between {actor_name} and {target_name}: {old_s} -> {new_s} (delta: {delta_rom:+d})")
            else:
                log(f"[RELATIONSHIP] Romance track not found, skipping romance delta {delta_rom:+d}", level="WARNING")

    except Exception as e:
        log_exception("Could not update relationship score", e)


def send_chat_message_async(
    actor_sim_info,
    recipient_sim_info,
    message_text: str,
    callback: Callable[[str, bool], None],
    extra_context: Optional[str] = None,
    history_override: Optional[List[Dict[str, Any]]] = None,
):
    """
    Sends chat request to Synapse local AI Bridge on 127.0.0.1:8765.
    Executes in a separate thread and calls callback(reply_or_error, is_success).
    """
    thread = threading.Thread(
        target=_worker_chat_request,
        args=(actor_sim_info, recipient_sim_info, message_text, callback, extra_context, history_override),
        daemon=True,
        name="AISocialPC-Worker",
    )
    thread.start()


def _safe_dispatch(func, *args, **kwargs):
    if not callable(func):
        return
    try:
        from ai_social_pc.main_thread import run_on_main_thread
        run_on_main_thread(func, *args, **kwargs)
    except Exception:
        try:
            func(*args, **kwargs)
        except Exception:
            pass


def _worker_chat_request(
    actor_sim_info,
    recipient_sim_info,
    message_text: str,
    callback: Callable[[str, bool], None],
    extra_context: Optional[str] = None,
    history_override: Optional[List[Dict[str, Any]]] = None,
):
    actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
    recipient_id = getattr(recipient_sim_info, "sim_id", 0) if not isinstance(recipient_sim_info, dict) else recipient_sim_info.get("id", -1)

    # Determine names
    if isinstance(actor_sim_info, dict):
        sender_name = actor_sim_info.get("name", "Игрок")
    else:
        s_f = getattr(actor_sim_info, "first_name", "") or ""
        s_l = getattr(actor_sim_info, "last_name", "") or ""
        sender_name = f"{s_f} {s_l}".strip() or "Персонаж"

    if isinstance(recipient_sim_info, dict):
        recipient_name = recipient_sim_info.get("name", "Собеседник")
    else:
        r_f = getattr(recipient_sim_info, "first_name", "") or ""
        r_l = getattr(recipient_sim_info, "last_name", "") or ""
        recipient_name = f"{r_f} {r_l}".strip() or "Собеседник"

    log(f"Chat request: {sender_name} -> {recipient_name}: '{message_text}'")

    # Get conversation history
    cur_day = get_current_sim_absolute_days()
    formatted_messages = []
    if get_chat_context_flag("chat_history"):
        if history_override is not None:
            raw_history = list(history_override)
        else:
            raw_history = list(get_session_history(actor_id, recipient_id))
        for msg in raw_history[-15:]:
            s = msg.get("sender", "")
            s_id = msg.get("sender_id", 0)
            if s_id and actor_id and s_id == actor_id:
                sim_display = sender_name
            elif s_id and recipient_id and s_id == recipient_id:
                sim_display = recipient_name
            elif s in ("Вы", "You") or s == sender_name:
                sim_display = sender_name
            elif history_override is not None:
                sim_display = s
            else:
                sim_display = recipient_name

            m_time = msg.get("time", "")
            m_day = msg.get("abs_day", cur_day)
            m_dow = msg.get("dow", "")
            day_lbl = get_relative_day_label(m_day, cur_day, m_dow)

            prefix = f"[{day_lbl} {m_time}] " if (day_lbl or m_time) else ""
            line_str = f"- {prefix}{sim_display}: {msg.get('text', '')}"

            formatted_messages.append({
                "sender": sim_display,
                "text": msg.get("text", ""),
                "time": m_time,
                "day": day_lbl,
                "formatted_line": line_str,
            })
    else:
        formatted_messages = []

    sender_info = _build_sim_profile_summary(actor_sim_info, is_actor=True)
    recipient_info = _build_sim_profile_summary(recipient_sim_info, is_actor=False)
    relationship_desc = _get_relationship_description(actor_sim_info, recipient_sim_info)

    payload = {
        "type": "chat",
        "sender_name": sender_name,
        "recipient_name": recipient_name,
        "sender_info": sender_info,
        "recipient_info": recipient_info,
        "relationship": relationship_desc,
        "message": message_text,
        "messages": formatted_messages,
    }
    try:
        from ai_social_pc.memory_manager import format_memories_for_prompt
        mem_text = format_memories_for_prompt(actor_id, recipient_id)
        if mem_text:
            payload["memories"] = mem_text
    except Exception as _mem_e:
        log_exception("Failed to attach memories to payload", _mem_e)

    if extra_context:
        payload["extra_context"] = str(extra_context)

    try:
        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=120)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }

        conn.request("POST", "/chat", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")

        try:
            resp_json = json.loads(resp_data)
        except json.JSONDecodeError:
            resp_json = {"reply": resp_data, "success": resp.status == 200}

        if resp.status == 200 and resp_json.get("success", True):
            raw_reply = resp_json.get("reply", "") or resp_json.get("thought", "")
            clean_reply, local_fr, local_rom = parse_and_strip_relationship_tags(strip_emojis(raw_reply))

            # Allow server to optionally override deltas via explicit JSON fields
            delta_fr = resp_json.get("delta_friendship")
            delta_fr = int(delta_fr) if delta_fr is not None else local_fr

            delta_rom = resp_json.get("delta_romance")
            delta_rom = int(delta_rom) if delta_rom is not None else local_rom

            log(f"Received reply from {recipient_name}: '{clean_reply}' (FR={delta_fr:+d}, ROM={delta_rom:+d})")

            # Dispatch state mutation, relationship changes and UI reopen strictly to the main thread
            def _finish_chat_turn():
                add_session_message(actor_id, recipient_id, sender=recipient_name, text=clean_reply, sender_id=recipient_id)
                apply_chat_relationship_impact(actor_sim_info, recipient_sim_info, delta_fr=delta_fr, delta_rom=delta_rom)
                callback(clean_reply, True)

            _safe_dispatch(_finish_chat_turn)
        else:
            err = resp_json.get("error") or resp_json.get("reply") or f"Ошибка связи (HTTP {resp.status})"
            log(f"Bridge error in chat: {err}", level="ERROR")
            _safe_dispatch(callback, err, False)

        conn.close()

    except ConnectionRefusedError:
        err_msg = "⏳ AI Bridge запускается в консоли... Пожалуйста, повторите действие через несколько секунд."
        log("Connection refused to AI Bridge. Triggering console autostart...", level="WARNING")
        try:
            from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
            ensure_bridge_running_async()
        except Exception:
            pass
        _safe_dispatch(callback, err_msg, False)
    except TimeoutError:
        err_msg = "Время ожидания ответа от нейросети истекло (таймаут 2 мин)."
        log("Timeout in chat request", level="WARNING")
        _safe_dispatch(callback, err_msg, False)
    except OSError as e:
        win_err = getattr(e, "winerror", None) or getattr(e, "errno", None)
        if win_err == 10061:
            err_msg = "⏳ AI Bridge запускается в консоли... Пожалуйста, повторите действие через несколько секунд."
            try:
                from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
                ensure_bridge_running_async()
            except Exception:
                pass
        elif win_err == 10054:
            err_msg = "Соединение с AI Bridge прервано."
        else:
            err_msg = f"Сетевая ошибка: {e}"
        log(f"Socket error: {e}", level="WARNING")
        _safe_dispatch(callback, err_msg, False)
    except Exception as e:
        log_exception("Unexpected error in chat worker", e)
        _safe_dispatch(callback, f"Ошибка чата: {e}", False)


def send_group_chat_message_async(
    actor_sim_info,
    group_data: Dict[str, Any],
    message_text: str,
    callback: Callable[[List[Dict[str, Any]], bool, str], None],
    extra_context: Optional[str] = None,
    force_all_online: bool = False,
):
    """
    Sends group chat message to Synapse local AI Bridge on 127.0.0.1:8765.
    Executes in a background thread and calls callback(reply_messages, is_success, error_msg).
    reply_messages is a list of dicts:
      [{"sender": str, "text": str, "delta_friendship": int, "delta_romance": int}, ...]
    """
    thread = threading.Thread(
        target=_worker_group_chat_request,
        args=(actor_sim_info, group_data, message_text, callback, extra_context, force_all_online),
        daemon=True,
        name="AISocialPC-GroupWorker",
    )
    thread.start()


def _worker_group_chat_request(
    actor_sim_info,
    group_data: Dict[str, Any],
    message_text: str,
    callback: Callable[[List[Dict[str, Any]], bool, str], None],
    extra_context: Optional[str] = None,
    force_all_online: bool = False,
):
    try:
        actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
        default_you = "You" if _is_en() else "Вы"
        if isinstance(actor_sim_info, dict):
            sender_name = actor_sim_info.get("name", default_you)
        else:
            s_f = getattr(actor_sim_info, "first_name", "") or ""
            s_l = getattr(actor_sim_info, "last_name", "") or ""
            sender_name = f"{s_f} {s_l}".strip() or default_you

        group_id = group_data.get("id", "")
        def_grp_name = "Group Chat" if _is_en() else "Групповой чат"
        group_name = group_data.get("name", def_grp_name)
        group_topic = (group_data.get("topic") or "").strip()
        if not group_topic and group_id:
            try:
                from ai_social_pc.group_manager import get_group_topic
                group_topic = get_group_topic(group_id)
            except Exception:
                pass
        member_ids = group_data.get("member_ids", [])

        # Gather participants (excluding actor)
        from ai_social_pc.ui_chat import is_sim_online
        sim_mgr = services.sim_info_manager() if services is not None else None
        participants = []

        for mid in member_ids:
            if mid == actor_id:
                continue
            s_info = sim_mgr.get(mid) if sim_mgr else None
            if s_info is None:
                continue

            m_f = getattr(s_info, "first_name", "") or ""
            m_l = getattr(s_info, "last_name", "") or ""
            m_name = f"{m_f} {m_l}".strip() or f"Сим_{mid}"

            if force_all_online:
                is_on = True
            else:
                ws_status = get_sim_work_or_school_status(s_info)
                # Strictly online if is_sim_online and not busy with work/school
                is_on = is_sim_online(s_info) and not ws_status.get("is_busy", False)

            info = _build_sim_profile_summary(s_info, is_actor=False)
            rel = _get_relationship_description(actor_sim_info, s_info)
            mem = ""
            try:
                from ai_social_pc.memory_manager import format_memories_for_prompt
                mem = format_memories_for_prompt(actor_id, mid)
            except Exception:
                pass

            participants.append({
                "name": m_name,
                "sim_id": mid,
                "is_online": is_on,
                "info": info,
                "relationship": rel,
                "memories": mem,
            })

        # Format rolling history (last 15 messages)
        from ai_social_pc.group_manager import get_group_messages
        cur_day = get_current_sim_absolute_days()
        formatted_messages = []
        if get_chat_context_flag("chat_history"):
            raw_history = list(get_group_messages(group_id))
            for msg in raw_history[-15:]:
                s = msg.get("sender", "")
                t = msg.get("text", "")
                m_time = msg.get("time", "")
                m_day = msg.get("abs_day", cur_day)
                m_dow = msg.get("dow", "")
                day_lbl = get_relative_day_label(m_day, cur_day, m_dow)
                prefix = f"[{day_lbl} {m_time}] " if (day_lbl or m_time) else ""
                formatted_messages.append({
                    "sender": s,
                    "text": t,
                    "time": m_time,
                    "day": day_lbl,
                    "formatted_line": f"- {prefix}{s}: {t}",
                })

        payload = {
            "type": "group_chat",
            "sender_name": sender_name,
            "group_name": group_name,
            "group_topic": group_topic,
            "message": message_text,
            "participants": participants,
            "messages": formatted_messages,
        }
        if extra_context:
            payload["extra_context"] = str(extra_context)

        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=120)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }

        conn.request("POST", "/chat", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")

        try:
            resp_json = json.loads(resp_data)
        except Exception:
            resp_json = {}

        if resp.status == 200 and resp_json.get("success"):
            raw_msgs = resp_json.get("messages", [])
            sanitized_msgs = []
            for m in raw_msgs:
                s_name = m.get("sender", "Собеседник")
                raw_t = m.get("text", "")
                # Ensure no emojis and clean tags
                clean_t, local_fr, local_rom = parse_and_strip_relationship_tags(strip_emojis(raw_t))
                d_fr = m.get("delta_friendship")
                d_fr = int(d_fr) if d_fr is not None else local_fr
                d_rom = m.get("delta_romance")
                d_rom = int(d_rom) if d_rom is not None else local_rom

                if clean_t:
                    sanitized_msgs.append({
                        "sender": s_name,
                        "text": clean_t,
                        "delta_friendship": d_fr,
                        "delta_romance": d_rom,
                    })

            log(f"[GROUP AI] Successfully received {len(sanitized_msgs)} group messages from Bridge.")
            _safe_dispatch(callback, sanitized_msgs, True, "")
        else:
            err = resp_json.get("error") or f"Ошибка связи (HTTP {resp.status})"
            log(f"Bridge error in group chat: {err}", level="ERROR")
            _safe_dispatch(callback, [], False, err)

        conn.close()

    except ConnectionRefusedError:
        err_msg = "⏳ AI Bridge запускается в консоли... Пожалуйста, повторите действие через несколько секунд."
        log("Connection refused to AI Bridge in group chat. Triggering console autostart...", level="WARNING")
        try:
            from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
            ensure_bridge_running_async()
        except Exception:
            pass
        _safe_dispatch(callback, [], False, err_msg)
    except TimeoutError:
        err_msg = "Время ожидания ответа группы истекло (таймаут 2 мин)."
        log("Timeout in group chat request", level="WARNING")
        _safe_dispatch(callback, [], False, err_msg)
    except OSError as e:
        win_err = getattr(e, "winerror", None) or getattr(e, "errno", None)
        if win_err == 10061:
            err_msg = "⏳ AI Bridge запускается в консоли... Пожалуйста, повторите действие через несколько секунд."
            try:
                from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
                ensure_bridge_running_async()
            except Exception:
                pass
        elif win_err == 10054:
            err_msg = "Соединение с AI Bridge прервано."
        else:
            err_msg = f"Сетевая ошибка: {e}"
        log(f"Socket error in group chat: {e}", level="WARNING")
        _safe_dispatch(callback, [], False, err_msg)
    except Exception as e:
        log_exception("Unexpected error in group chat worker", e)
        _safe_dispatch(callback, [], False, f"Ошибка группы: {e}")

