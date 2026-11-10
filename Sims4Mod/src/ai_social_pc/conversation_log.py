# -*- coding: utf-8 -*-
"""
Recent Conversations & Interactions Log (24 Sim-Hours).
Maintains a rolling 24-hour log of all communications for each Sim across:
1. Live in-person dialogues (Direct Dialogue)
2. Autonomous Director scenes (Autonomous Director / ambient conversation)
3. 1-on-1 Messenger chats (Direct Messages)
4. Group chats (Group Messages)

Persisted per save in:
~/Documents/Electronic Arts/The Sims 4/ai_social_recent_conversations.json
"""

import os
import json
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Set

from ai_social_pc.logger import log, log_exception

try:
    import services
except ImportError:
    services = None

CONVERSATIONS_FILE_PATH = os.path.expanduser(
    r"~\Documents\Electronic Arts\The Sims 4\ai_social_recent_conversations.json"
)

_CONVERSATIONS_LOCK = threading.RLock()
_WORKING_CONVERSATIONS_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None
_ACTIVE_CONV_SAVE_ID: Optional[str] = None
_IS_CONV_DIRTY: bool = False


def _get_current_save_id() -> str:
    try:
        from ai_social_pc.group_manager import get_current_save_id
        return get_current_save_id()
    except Exception:
        return "default"


def _read_disk_file() -> Dict[str, Any]:
    if os.path.exists(CONVERSATIONS_FILE_PATH):
        try:
            with open(CONVERSATIONS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_social_recent_conversations.json", e)
    return {"saves": {}}


def _write_disk_file(data: Dict[str, Any]):
    try:
        temp_path = CONVERSATIONS_FILE_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(CONVERSATIONS_FILE_PATH):
            os.replace(temp_path, CONVERSATIONS_FILE_PATH)
        else:
            os.rename(temp_path, CONVERSATIONS_FILE_PATH)
    except Exception as e:
        log_exception("Failed to write ai_social_recent_conversations.json", e)


def load_conversations_data() -> Dict[str, List[Dict[str, Any]]]:
    """Loads rolling conversation cache for the current save."""
    global _WORKING_CONVERSATIONS_CACHE, _ACTIVE_CONV_SAVE_ID, _IS_CONV_DIRTY
    with _CONVERSATIONS_LOCK:
        current_save = _get_current_save_id()
        if _WORKING_CONVERSATIONS_CACHE is not None and _ACTIVE_CONV_SAVE_ID == current_save:
            return _WORKING_CONVERSATIONS_CACHE

        disk_data = _read_disk_file()
        saves_dict = disk_data.get("saves", {})
        save_data = saves_dict.get(current_save, {})
        if not isinstance(save_data, dict):
            save_data = {}

        _WORKING_CONVERSATIONS_CACHE = save_data
        _ACTIVE_CONV_SAVE_ID = current_save
        _IS_CONV_DIRTY = False
        return _WORKING_CONVERSATIONS_CACHE


def commit_conversations_to_disk():
    """Flushes dirty conversation entries to disk."""
    global _IS_CONV_DIRTY
    with _CONVERSATIONS_LOCK:
        if not _IS_CONV_DIRTY or _WORKING_CONVERSATIONS_CACHE is None:
            return
        current_save = _ACTIVE_CONV_SAVE_ID or _get_current_save_id()
        disk_data = _read_disk_file()
        disk_data["saves"][current_save] = _WORKING_CONVERSATIONS_CACHE
        _write_disk_file(disk_data)
        _IS_CONV_DIRTY = False
        log("[CONVERSATION LOG] Saved recent conversations to disk.")


def get_current_sim_hours() -> float:
    """Returns current absolute in-game time in hours (days * 24 + hour + minute / 60.0)."""
    try:
        if services is not None:
            time_service = services.time_service()
            now = (getattr(time_service, "sim_now", None) if time_service else None) or (
                services.game_clock_service().now()
                if hasattr(services, "game_clock_service") and services.game_clock_service()
                else None
            )
            if now is not None:
                days = 0
                if hasattr(now, "absolute_days"):
                    d_val = now.absolute_days()
                    days = int(d_val() if callable(d_val) else d_val)
                elif hasattr(now, "day"):
                    d_val = now.day()
                    days = int(d_val() if callable(d_val) else d_val)
                h_val = getattr(now, "hour", 0)
                hour = float(h_val() if callable(h_val) else h_val)
                m_val = getattr(now, "minute", 0)
                minute = float(m_val() if callable(m_val) else m_val)
                return days * 24.0 + hour + (minute / 60.0)
    except Exception:
        pass
    return time.time() / 3600.0


def _prune_sim_entries(entries: List[Dict[str, Any]], current_hours: float, max_age_hours: float = None) -> List[Dict[str, Any]]:
    if max_age_hours is None:
        try:
            from ai_thought_reader.config import get_dialogue_memory_hours
            v = float(get_dialogue_memory_hours())
            max_age_hours = 999999.0 if (v <= 0.0 or v >= 999.0) else v
        except Exception:
            max_age_hours = 24.0
    elif max_age_hours <= 0.0 or max_age_hours >= 999.0:
        max_age_hours = 999999.0
    valid = []
    for e in entries:
        h = float(e.get("sim_time_hours", 0.0))
        if (current_hours - h) <= max_age_hours and (current_hours - h) >= -1.0:
            valid.append(e)
    # Keep up to 50 latest entries per Sim
    return valid[-100:]


def record_conversation_entry(
    sim_id: Any,
    speaker_id: Any,
    speaker_name: str,
    text: str,
    channel: str = "direct_dialogue",
    group_name: Optional[str] = None,
    location: Optional[str] = None,
):
    """
    Records a conversation turn into sim_id's rolling 24-hour log.
    Channels: 'direct_dialogue', 'autonomous_scene', 'direct_message', 'group_chat'
    """
    if not sim_id or not text:
        return
    clean_text = str(text).strip()
    if not clean_text:
        return

    s_key = str(int(sim_id))
    cur_hours = get_current_sim_hours()

    try:
        from ai_social_pc.chat_manager import get_current_sim_time
        time_str = get_current_sim_time()
    except Exception:
        time_str = ""

    new_entry = {
        "channel": str(channel),
        "speaker_id": int(speaker_id) if speaker_id else 0,
        "speaker_name": str(speaker_name or "Sim").strip(),
        "text": clean_text,
        "sim_time_hours": cur_hours,
        "time": time_str,
    }
    if group_name:
        new_entry["group_name"] = str(group_name).strip()
    if location:
        new_entry["location"] = str(location).strip()

    global _IS_CONV_DIRTY
    with _CONVERSATIONS_LOCK:
        data = load_conversations_data()
        if s_key not in data or not isinstance(data[s_key], list):
            data[s_key] = []

        existing = data[s_key]
        if existing and existing[-1].get("text") == clean_text and abs(existing[-1].get("sim_time_hours", 0) - cur_hours) < 0.05:
            return
        data[s_key].append(new_entry)
        data[s_key] = _prune_sim_entries(data[s_key], cur_hours)
        _IS_CONV_DIRTY = True

    # Async debounce commit to disk
    def _delayed_commit():
        commit_conversations_to_disk()

    t = threading.Timer(4.0, _delayed_commit)
    t.daemon = True
    t.start()


def record_conversation_exchange(
    participant_sim_ids: List[Any],
    speaker_id: Any,
    speaker_name: str,
    text: str,
    channel: str = "direct_dialogue",
    group_name: Optional[str] = None,
    location: Optional[str] = None,
):
    """Convenience helper to record a single turn for all participants in a conversation or scene."""
    if not participant_sim_ids or not text:
        return
    for p_id in participant_sim_ids:
        if p_id is not None:
            try:
                sid_val = getattr(p_id, "sim_id", p_id)
                record_conversation_entry(
                    sim_id=sid_val,
                    speaker_id=speaker_id,
                    speaker_name=speaker_name,
                    text=text,
                    channel=channel,
                    group_name=group_name,
                    location=location,
                )
            except Exception as ex:
                log_exception("Error in record_conversation_exchange", ex)




def get_nearby_sim_ids(center_sim_or_pos, exclude_ids: Optional[Set[int]] = None, max_distance: float = 15.0) -> List[int]:
    """Finds IDs of all active instanced Sims within max_distance meters on the lot, ignoring walls."""
    nearby_ids = []
    if services is None or center_sim_or_pos is None:
        return nearby_ids
    try:
        center_pos = None
        if hasattr(center_sim_or_pos, "position"):
            center_pos = center_sim_or_pos.position
        elif hasattr(center_sim_or_pos, "get_sim_instance"):
            inst = center_sim_or_pos.get_sim_instance()
            if inst and hasattr(inst, "position"):
                center_pos = inst.position
        elif hasattr(center_sim_or_pos, "x") and hasattr(center_sim_or_pos, "z"):
            center_pos = center_sim_or_pos

        if center_pos is None:
            return nearby_ids

        sim_info_mgr = services.sim_info_manager()
        if sim_info_mgr is None:
            return nearby_ids

        ex_set = set(int(x) for x in exclude_ids) if exclude_ids else set()

        for inst in sim_info_mgr.instanced_sims_gen():
            sid = getattr(inst, "sim_id", None) or getattr(inst, "id", None)
            if not sid:
                inf = getattr(inst, "sim_info", None)
                sid = getattr(inf, "sim_id", None)
            if not sid:
                continue
            sid_int = int(sid)
            if sid_int in ex_set:
                continue
            if getattr(inst, "is_pet", False):
                continue
            inst_pos = getattr(inst, "position", None)
            if inst_pos is not None:
                dist = (inst_pos - center_pos).magnitude()
                if dist <= max_distance:
                    nearby_ids.append(sid_int)
    except Exception as ex:
        log_exception("Error in get_nearby_sim_ids", ex)
    return nearby_ids


def record_overheard_exchange(
    center_sim_or_pos: Any,
    speaker_id: Any,
    speaker_name: str,
    text: str,
    channel: str = "overheard_dialogue",
    target_name: Optional[str] = None,
    pc_user_name: Optional[str] = None,
    group_name: Optional[str] = None,
    exclude_sim_ids: Optional[Set[int]] = None,
    max_distance: float = 15.0,
) -> List[int]:
    """
    Experimental: Records spoken or on-screen dialogue into the rolling memory of all Sims
    who are physically nearby (ignoring walls, based on direct distance).
    Channels: 'overheard_dialogue', 'overheard_scene', 'overheard_pc_direct', 'overheard_pc_group'
    Returns list of sim IDs who recorded this overheard exchange.
    """
    try:
        from ai_thought_reader.config import get_experimental_flag
        if not get_experimental_flag("overheard_conversations"):
            return []
    except Exception:
        return []

    clean_text = str(text).strip()
    if not clean_text:
        return []

    nearby_sids = get_nearby_sim_ids(center_sim_or_pos, exclude_ids=exclude_sim_ids, max_distance=max_distance)
    if not nearby_sids:
        return []

    cur_hours = get_current_sim_hours()
    try:
        from ai_social_pc.chat_manager import get_current_sim_time
        time_str = get_current_sim_time()
    except Exception:
        time_str = ""

    new_entry = {
        "channel": str(channel),
        "speaker_id": int(speaker_id) if speaker_id else 0,
        "speaker_name": str(speaker_name or "Sim").strip(),
        "text": clean_text,
        "sim_time_hours": cur_hours,
        "time": time_str,
        "is_overheard": True,
    }
    if target_name:
        new_entry["target_name"] = str(target_name).strip()
    if pc_user_name:
        new_entry["pc_user_name"] = str(pc_user_name).strip()
    if group_name:
        new_entry["group_name"] = str(group_name).strip()

    global _IS_CONV_DIRTY
    with _CONVERSATIONS_LOCK:
        data = load_conversations_data()
        for sid in nearby_sids:
            s_key = str(sid)
            if s_key not in data or not isinstance(data[s_key], list):
                data[s_key] = []
            # Deduplicate if exact same entry text was recorded at the same hour
            existing = data[s_key]
            if existing and existing[-1].get("text") == clean_text and abs(existing[-1].get("sim_time_hours", 0) - cur_hours) < 0.05:
                continue
            data[s_key].append(new_entry)
            data[s_key] = _prune_sim_entries(data[s_key], cur_hours)
        _IS_CONV_DIRTY = True

    # Async debounce commit to disk
    def _delayed_commit():
        commit_conversations_to_disk()

    t = threading.Timer(4.0, _delayed_commit)
    t.daemon = True
    t.start()
    return nearby_sids


def format_relative_time(entry_hours: float, current_hours: float, is_en: bool = False) -> str:
    """Converts difference between current sim hours and entry sim hours into a human-readable relative label."""
    diff_h = current_hours - entry_hours
    if diff_h < 0.0:
        diff_h = 0.0
    diff_m = diff_h * 60.0

    if diff_m < 5.0:
        return "Just now" if is_en else "Только что"
    if diff_m < 60.0:
        mins = max(5, int(round(diff_m / 5.0) * 5))
        return f"{mins} min ago" if is_en else f"{mins} мин. назад"
    
    hours_int = int(round(diff_h))
    if hours_int <= 1:
        return "1 hour ago" if is_en else "1 ч. назад"
    if is_en:
        return f"{hours_int} hours ago"
    
    # Russian pluralization (2-4 часа, 5-20 часов, 21 час, 22-24 часа)
    if hours_int in (2, 3, 4, 22, 23, 24):
        return f"{hours_int} часа назад"
    if hours_int == 21:
        return f"{hours_int} час назад"
    return f"{hours_int} часов назад"


def get_recent_conversation_entries(sim_id: Any, max_age_hours: float = None, max_entries: int = 100) -> List[Dict[str, Any]]:
    if max_age_hours is None:
        try:
            from ai_thought_reader.config import get_dialogue_memory_hours
            v = float(get_dialogue_memory_hours())
            max_age_hours = 999999.0 if (v <= 0.0 or v >= 999.0) else v
        except Exception:
            max_age_hours = 24.0
    elif max_age_hours <= 0.0 or max_age_hours >= 999.0:
        max_age_hours = 999999.0
    """Retrieves pruned, sorted recent conversation entries for a Sim."""
    if not sim_id:
        return []
    s_key = str(int(sim_id))
    cur_hours = get_current_sim_hours()

    with _CONVERSATIONS_LOCK:
        data = load_conversations_data()
        raw_list = data.get(s_key, [])
        valid = _prune_sim_entries(raw_list, cur_hours, max_age_hours=max_age_hours)
        data[s_key] = valid
        return valid[-max_entries:]


def format_recent_conversations_for_prompt(sim_info_or_id: Any, max_entries: int = 100, is_en: bool = False) -> Optional[str]:
    """
    Renders the Sim's recent conversations, messages, and overheard dialogues for inclusion at the end of the context prompt.
    Returns None if no entries exist.
    """
    if sim_info_or_id is None:
        return None
    sid = getattr(sim_info_or_id, "sim_id", sim_info_or_id)
    try:
        sid_int = int(sid)
    except (ValueError, TypeError):
        return None

    try:
        from ai_thought_reader.config import get_dialogue_memory_hours
        cfg_hours = float(get_dialogue_memory_hours())
    except Exception:
        cfg_hours = 24.0
    entries = get_recent_conversation_entries(sid_int, max_age_hours=cfg_hours, max_entries=max_entries)
    if not entries:
        return None

    cur_hours = get_current_sim_hours()
    if cfg_hours >= 999:
        header = (
            "- Recent Conversations & Messages (All Time):"
            if is_en
            else "- Недавние разговоры и сообщения (за всё время):"
        )
    else:
        header = (
            f"- Recent Conversations & Messages (Last {int(cfg_hours)} Sim-Hours):"
            if is_en
            else f"- Недавние разговоры и сообщения (за последние {int(cfg_hours)} ч.):"
        )

    lines = [header]
    for e in entries:
        speaker = e.get("speaker_name", "Sim")
        raw_t = e.get("text", "")
        # Shorten very long lines if needed
        clean_t = raw_t[:160] + "..." if len(raw_t) > 160 else raw_t
        h_val = float(e.get("sim_time_hours", cur_hours))
        rel_time = format_relative_time(h_val, cur_hours, is_en=is_en)
        ch = e.get("channel", "direct_dialogue")
        grp = e.get("group_name", None)
        tgt = e.get("target_name", None)
        user_name = e.get("pc_user_name", None)
        is_ov = bool(e.get("is_overheard", False) or ch.startswith("overheard_"))

        if is_ov:
            if ch in ("overheard_pc_direct", "overheard_messenger_direct"):
                # Seen on someone else's screen (direct message / messenger)
                if user_name:
                    badge = f"Seen on {user_name}'s screen, {rel_time}" if is_en else f"Увидено на экране у {user_name}, {rel_time}"
                else:
                    badge = f"Seen on screen nearby, {rel_time}" if is_en else f"Увидено на экране рядом, {rel_time}"

                if user_name and speaker.lower() == user_name.lower():
                    context_hint = f"(sent to {tgt})" if is_en else (f"(отправил(а) {tgt})" if tgt else "")
                elif tgt:
                    context_hint = f"(messaged {tgt})" if is_en else f"(написал(а) {tgt})"
                elif user_name:
                    context_hint = f"(messaged {user_name})" if is_en else f"(написал(а) {user_name})"
                else:
                    context_hint = ""

                speaker_part = f"{speaker} {context_hint}".strip() if context_hint else f"{speaker}"
            elif ch in ("overheard_pc_group", "overheard_group"):
                # Seen on someone else's screen (group chat)
                if user_name and grp:
                    badge = f'Seen on {user_name}\'s screen: Group "{grp}", {rel_time}' if is_en else f'Увидено на экране у {user_name}: Группа «{grp}», {rel_time}'
                elif user_name:
                    badge = f"Seen on {user_name}\'s screen: Group Chat, {rel_time}" if is_en else f"Увидено на экране у {user_name}: Групповой чат, {rel_time}"
                elif grp:
                    badge = f'Seen on screen nearby: Group "{grp}", {rel_time}' if is_en else f'Увидено на экране рядом: Группа «{grp}», {rel_time}'
                else:
                    badge = f"Seen on screen nearby: Group Chat, {rel_time}" if is_en else f"Увидено на экране рядом: Групповой чат, {rel_time}"

                speaker_part = f"{speaker}"
            else:
                # Live face-to-face or autonomous scene overheard nearby
                badge = f"Overheard Nearby, {rel_time}" if is_en else f"Услышано рядом, {rel_time}"
                if tgt:
                    context_hint = f"(talking to {tgt})" if is_en else f"(в разговоре с {tgt})"
                    speaker_part = f"{speaker} {context_hint}"
                else:
                    speaker_part = f"{speaker}"
        else:
            # Standard own direct message, group chat, or dialogue
            if ch == "direct_message":
                badge = f"Direct Message, {rel_time}" if is_en else f"Личное сообщение, {rel_time}"
            elif ch == "group_chat":
                if grp:
                    badge = f'Group Chat "{grp}", {rel_time}' if is_en else f'Групповой чат «{grp}», {rel_time}'
                else:
                    badge = f"Group Chat, {rel_time}" if is_en else f"Групповой чат, {rel_time}"
            elif ch == "group_dialogue":
                badge = f"Group Conversation, {rel_time}" if is_en else f"Групповой разговор, {rel_time}"
            elif ch in ("intimate_group_dialogue", "group_intimate"):
                badge = f"Group Intimate Scene, {rel_time}" if is_en else f"Групповой интимный разговор, {rel_time}"
            elif ch in ("intimate_dialogue", "intimate_direct"):
                badge = f"Intimate Conversation, {rel_time}" if is_en else f"Интимный разговор, {rel_time}"
            elif ch == "autonomous_scene":
                badge = f"In-Person Scene, {rel_time}" if is_en else f"Живая сцена, {rel_time}"
            else:
                badge = f"In-Person, {rel_time}" if is_en else f"Личный разговор, {rel_time}"

            speaker_part = f"{speaker}"

        if is_en:
            lines.append(f'  • [{badge}] {speaker_part}: "{clean_t}"')
        else:
            lines.append(f'  • [{badge}] {speaker_part}: «{clean_t}»')

    return "\n".join(lines)


def clear_conversation_logs(sim_id: Optional[int] = None) -> int:
    """
    Clears recorded dialogue turns from the rolling conversation log.
    If sim_id is provided, clears only for that Sim. Otherwise clears all.
    """
    global _CONVERSATION_LOG_DATA
    _ensure_loaded()
    with _LOG_LOCK:
        if sim_id:
            s_key = str(int(sim_id))
            if s_key in _CONVERSATION_LOG_DATA:
                cnt = len(_CONVERSATION_LOG_DATA[s_key])
                del _CONVERSATION_LOG_DATA[s_key]
                _mark_dirty()
                log(f"[CONVERSATION_LOG] Cleared {cnt} log entries for Sim {sim_id}.")
                return cnt
            return 0
        cnt = sum(len(v) for v in _CONVERSATION_LOG_DATA.values())
        _CONVERSATION_LOG_DATA.clear()
        _mark_dirty()
        log(f"[CONVERSATION_LOG] Cleared all {cnt} conversation log entries across all Sims.")
        return cnt
