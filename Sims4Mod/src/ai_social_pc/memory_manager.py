import os
import re
import json
import threading
import http.client
from typing import Dict, List, Any, Optional, Tuple, Set
from ai_social_pc.logger import log, log_exception
from ai_social_pc.group_manager import get_current_save_id

try:
    import services
except ImportError:
    services = None

# Persistent file path in TS4 user directory
MEMORY_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_social_memories.json")
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765

# In-memory working cache for current save: { pair_key: [memory_dicts...] }
_WORKING_MEMORIES_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None
_ACTIVE_MEMORY_SAVE_ID: Optional[str] = None
_IS_MEMORIES_DIRTY: bool = False
_MEMORIES_LOCK = threading.RLock()



def _get_pair_key(sim_a_id: int, sim_b_id: int = 0) -> str:
    """Returns canonical unique key for a pair of Sims (bidirectional) or personal Sim memory."""
    if not sim_b_id or int(sim_b_id) == 0:
        return f"sim_{int(sim_a_id)}"
    a = int(sim_a_id)
    b = int(sim_b_id)
    return f"{min(a, b)}_{max(a, b)}"


def _read_memories_disk_file() -> Dict[str, Any]:
    """Reads the memories JSON from disk, ensuring the 'saves' dict exists."""
    if os.path.exists(MEMORY_FILE_PATH):
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to load ai_social_memories.json", e)
    return {"saves": {}}


def load_memories() -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns the active in-memory memories cache for the current save slot.
    Loads from disk if cache is empty or active save changed.
    """
    global _WORKING_MEMORIES_CACHE, _ACTIVE_MEMORY_SAVE_ID, _IS_MEMORIES_DIRTY
    with _MEMORIES_LOCK:
        current_save = get_current_save_id()

        if _WORKING_MEMORIES_CACHE is not None and _ACTIVE_MEMORY_SAVE_ID == current_save:
            return _WORKING_MEMORIES_CACHE

        _ACTIVE_MEMORY_SAVE_ID = current_save
        _IS_MEMORIES_DIRTY = False
        disk_data = _read_memories_disk_file()

        save_entry = disk_data.get("saves", {}).get(current_save, {})
        pair_memories = save_entry.get("pair_memories", {}) if isinstance(save_entry, dict) else {}
        _WORKING_MEMORIES_CACHE = {k: list(v) for k, v in pair_memories.items()}

        log(f"[MEMORY] Initialized in-memory memories for save '{current_save}': {len(_WORKING_MEMORIES_CACHE)} pair(s)")
        return _WORKING_MEMORIES_CACHE


def mark_memories_dirty():
    global _IS_MEMORIES_DIRTY
    _IS_MEMORIES_DIRTY = True


def commit_memories_to_disk():
    """
    Persists memories cache to disk safely.
    Called immediately when memories are created/modified, and during game save / zone teardown.
    """
    global _IS_MEMORIES_DIRTY
    with _MEMORIES_LOCK:
        current_save = _ACTIVE_MEMORY_SAVE_ID or get_current_save_id()
        if _WORKING_MEMORIES_CACHE is None:
            return

        if not _IS_MEMORIES_DIRTY:
            return

        try:
            disk_data = _read_memories_disk_file()
            if "saves" not in disk_data or not isinstance(disk_data["saves"], dict):
                disk_data["saves"] = {}

            disk_data["saves"][current_save] = {
                "pair_memories": _WORKING_MEMORIES_CACHE,
            }

            temp_path = MEMORY_FILE_PATH + ".tmp"
            os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, ensure_ascii=False, indent=2)

            if os.path.exists(MEMORY_FILE_PATH):
                os.replace(temp_path, MEMORY_FILE_PATH)
            else:
                os.rename(temp_path, MEMORY_FILE_PATH)

            _IS_MEMORIES_DIRTY = False
            log(f"[MEMORY] Committed {len(_WORKING_MEMORIES_CACHE)} memory pairs for save '{current_save}' to disk successfully.")
        except Exception as e:
            log_exception("Failed to commit ai_social_memories.json to disk", e)


def reset_memories_cache():
    """
    Clears in-memory working cache upon zone unload/teardown.
    Any unsaved modifications are dropped if player exited without saving.
    """
    global _WORKING_MEMORIES_CACHE, _ACTIVE_MEMORY_SAVE_ID, _IS_MEMORIES_DIRTY
    with _MEMORIES_LOCK:
        _WORKING_MEMORIES_CACHE = None
        _ACTIVE_MEMORY_SAVE_ID = None
        _IS_MEMORIES_DIRTY = False
        log("[MEMORY] Memories cache reset on zone unload.")


def save_memories(data: Dict[str, List[Dict[str, Any]]]):
    """Compatibility wrapper that marks working cache dirty."""
    mark_memories_dirty()


def get_active_memories(actor_id: int, recipient_id: int) -> List[Dict[str, Any]]:
    """
    Returns non-expired memories for this pair of Sims.
    Automatically cleans up expired items based on the current in-game day.
    """
    all_memories = load_memories()
    key = _get_pair_key(actor_id, recipient_id)
    pair_memories = all_memories.get(key, [])

    if not pair_memories:
        return []

    from ai_social_pc.chat_manager import get_current_sim_absolute_days
    cur_day = get_current_sim_absolute_days()

    active = []
    changed = False

    for mem in pair_memories:
        dur = mem.get("duration_days", 0)
        expires = mem.get("expires_day")

        # Duration 0 means permanent memory (never expires)
        if dur == 0 or expires is None:
            mem_copy = dict(mem)
            mem_copy["remaining_label"] = "Навсегда"
            mem_copy["days_left"] = 0
            mem_copy["is_permanent"] = True
            active.append(mem_copy)
            continue

        # Temporary memory: check expiration
        days_left = expires - cur_day
        if days_left <= 0:
            changed = True
            log(f"[MEMORY] Memory expired: '{mem.get('summary', '')[:40]}...' (Created: day {mem.get('created_day')}, Expired: day {expires}, Current: day {cur_day})")
            continue

        mem_copy = dict(mem)
        mem_copy["days_left"] = days_left
        mem_copy["is_permanent"] = False
        d_word = "дн." if days_left > 4 or days_left == 0 else ("дня" if days_left > 1 else "день")
        mem_copy["remaining_label"] = f"Осталось {days_left} {d_word}"
        active.append(mem_copy)

    if changed:
        all_memories[key] = [m for m in pair_memories if m.get("duration_days", 0) == 0 or (m.get("expires_day") is not None and m.get("expires_day") > cur_day)]
        mark_memories_dirty()

    # Conflict resolution: A broken up pair cannot simultaneously be engaged, newlyweds, or a dating couple
    has_breakup = any(m.get("event_type") == "breakup_divorce" for m in active)
    if has_breakup:
        conflicting_types = {"wedding_newlyweds", "proposal_accepted_proposer", "proposal_accepted_target", "romance_became_couple"}
        filtered = [m for m in active if m.get("event_type") not in conflicting_types]
        if len(filtered) != len(active):
            active = filtered
            all_memories[key] = [m for m in all_memories[key] if m.get("event_type") not in conflicting_types]
            mark_memories_dirty()

    # Conflict resolution: Sex cheating supersedes flirt cheating (caught having sex > caught flirting)
    has_sex_cheating = any(m.get("event_type") in ("cheating_caught", "cheating_caught_cheater") for m in active)
    if has_sex_cheating:
        flirt_types = {"romance_cheating_caught", "romance_cheating_flirter"}
        filtered = [m for m in active if m.get("event_type") not in flirt_types]
        if len(filtered) != len(active):
            active = filtered
            all_memories[key] = [m for m in all_memories[key] if m.get("event_type") not in flirt_types]
            mark_memories_dirty()

    return active


def add_memory(
    actor_id: int,
    recipient_id: int,
    summary: str,
    duration_days: int,
    summary_en: str = "",
    event_type: str = "",
):
    """
    Adds a new memory to the working cache for current save.
    duration_days: 0 = permanent, >0 = temporary in-game days.
    summary_en: optional English translation for bilingual support.
    event_type: optional event category key to refresh existing memories of the same event.
    """
    clean_summary = str(summary).strip()
    if "<think>" in clean_summary:
        clean_summary = clean_summary.split("</think>")[-1].strip()
    if "<thought>" in clean_summary:
        clean_summary = clean_summary.split("</thought>")[-1].strip()
    clean_summary = clean_summary.strip(' "\'«»\n\r\t')
    if clean_summary.startswith("- ") or clean_summary.startswith("• "):
        clean_summary = clean_summary[2:].strip()

    clean_summary_en = str(summary_en).strip() if summary_en else ""
    if "<think>" in clean_summary_en:
        clean_summary_en = clean_summary_en.split("</think>")[-1].strip()
    if "<thought>" in clean_summary_en:
        clean_summary_en = clean_summary_en.split("</thought>")[-1].strip()
    clean_summary_en = clean_summary_en.strip(' "\'«»\n\r\t')
    if clean_summary_en.startswith("- ") or clean_summary_en.startswith("• "):
        clean_summary_en = clean_summary_en[2:].strip()

    if not clean_summary or clean_summary.upper() == "NONE":
        return

    from ai_social_pc.chat_manager import get_current_sim_absolute_days
    cur_day = get_current_sim_absolute_days()

    expires_day = None if duration_days == 0 else (cur_day + duration_days)

    all_memories = load_memories()
    key = _get_pair_key(actor_id, recipient_id)
    if key not in all_memories:
        all_memories[key] = []

    # Check for duplicate recent memory or same event_type to refresh duration without spamming
    for existing in all_memories[key]:
        match_by_event = bool(event_type and existing.get("event_type") == event_type)
        ex_actor = existing.get("actor_id", 0)
        actor_matches = (ex_actor == 0 or ex_actor == actor_id)
        match_by_summary = (existing.get("summary") == clean_summary)
        if (match_by_event and actor_matches) or match_by_summary:
            existing["summary"] = clean_summary
            if clean_summary_en:
                existing["summary_en"] = clean_summary_en
            if event_type:
                existing["event_type"] = event_type
            if actor_id:
                existing["actor_id"] = int(actor_id)
            if recipient_id:
                existing["recipient_id"] = int(recipient_id)
            existing["created_day"] = cur_day
            existing["duration_days"] = duration_days
            existing["expires_day"] = expires_day
            mark_memories_dirty()
            log(f"[MEMORY] Refreshed existing memory for {key} (type='{event_type}'): '{clean_summary[:40]}...' (Duration: {duration_days} days)")
            return

    new_entry = {
        "actor_id": int(actor_id) if actor_id else 0,
        "recipient_id": int(recipient_id) if recipient_id else 0,
        "summary": clean_summary,
        "summary_en": clean_summary_en,
        "event_type": event_type,
        "created_day": cur_day,
        "duration_days": duration_days,
        "expires_day": expires_day,
    }

    all_memories[key].append(new_entry)

    # Keep at most 10 memories per key
    if len(all_memories[key]) > 10:
        all_memories[key] = all_memories[key][-10:]

    mark_memories_dirty()
    log(f"[MEMORY] Stored new memory in memory cache for {key} (type='{event_type}'): '{clean_summary}' (Duration: {duration_days} days, Expires: day {expires_day})")


def remove_memories_by_types(actor_id: int, recipient_id: int, event_types: List[str]) -> int:
    """Removes memories matching specific event types for this pair of Sims."""
    all_memories = load_memories()
    key = _get_pair_key(actor_id, recipient_id)
    removed_count = 0
    if key in all_memories:
        types_set = set(event_types)
        orig_list = all_memories[key]
        filtered = [m for m in orig_list if m.get("event_type") not in types_set]
        removed_count = len(orig_list) - len(filtered)
        if removed_count > 0:
            all_memories[key] = filtered
            mark_memories_dirty()
            log(f"[MEMORY] Removed {removed_count} conflicting memories of types {event_types} for key {key}")
    return removed_count


def clear_memories_for_sim(sim_id: int) -> int:
    """Removes all memories (personal and pair) involving this Sim."""
    if not sim_id:
        return 0
    s_id = int(sim_id)
    all_memories = load_memories()
    removed = 0
    for key in list(all_memories.keys()):
        if key == f"sim_{s_id}":
            removed += len(all_memories[key])
            del all_memories[key]
        elif "_" in key and not key.startswith("sim_"):
            parts = key.split("_")
            if len(parts) == 2:
                try:
                    if s_id in (int(parts[0]), int(parts[1])):
                        removed += len(all_memories[key])
                        del all_memories[key]
                except ValueError:
                    pass
    if removed > 0:
        mark_memories_dirty()
        log(f"[MEMORY] Cleared {removed} memories for Sim {s_id}")
    return removed


def add_personal_memory(
    sim_id: int,
    summary: str,
    duration_days: int,
    summary_en: str = "",
    event_type: str = "",
):
    """
    Adds a personal episodic memory for an individual Sim (e.g. fire, promotion, Alien pregnancy).
    """
    add_memory(
        actor_id=int(sim_id),
        recipient_id=0,
        summary=summary,
        duration_days=duration_days,
        summary_en=summary_en,
        event_type=event_type,
    )


def get_all_active_memories_for_sim(sim_id: int, is_en: bool = False, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Returns non-expired memories relevant to this Sim (aggregating personal and pair memories).
    Sorted newest first, limited to 'limit' items.
    """
    if not sim_id:
        return []
    s_id = int(sim_id)
    all_memories = load_memories()

    collected: List[Dict[str, Any]] = []
    seen_texts: Set[str] = set()

    # Identify Sim's first name for perspective filtering of legacy memories without actor_id
    sim_first_name = ""
    try:
        import services
        sim_mgr = services.sim_info_manager() if services is not None else None
        if sim_mgr:
            s_inf = sim_mgr.get(s_id)
            if s_inf:
                fn = (getattr(s_inf, "first_name", "") or "").strip().lower()
                if fn and len(fn) > 2:
                    sim_first_name = fn
    except Exception:
        pass

    # 1. Personal memories
    personal_active = get_active_memories(s_id, 0)
    for m in personal_active:
        txt = (m.get("summary_en") if is_en and m.get("summary_en") else m.get("summary", "")).strip()
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            collected.append(m)

    # 2. Pair memories where this Sim is one of the partners
    for key in list(all_memories.keys()):
        if "_" in key and not key.startswith("sim_"):
            parts = key.split("_")
            if len(parts) == 2:
                try:
                    id_a, id_b = int(parts[0]), int(parts[1])
                    if s_id in (id_a, id_b):
                        other_id = id_b if s_id == id_a else id_a
                        pair_active = get_active_memories(s_id, other_id)
                        for m in pair_active:
                            # 1. If memory has actor_id, ensure it belongs to this Sim!
                            mem_actor = m.get("actor_id")
                            txt = (m.get("summary_en") if is_en and m.get("summary_en") else m.get("summary", "")).strip()
                            txt_low = txt.lower()

                            if mem_actor is not None and mem_actor != 0:
                                if mem_actor != s_id:
                                    continue
                            elif sim_first_name and sim_first_name in txt_low:
                                # 2. Legacy perspective filter (only for entries without actor_id):
                                # If the memory explicitly mentions this Sim's first name,
                                # it was written from the perspective of the OTHER partner.
                                continue

                            if txt and txt not in seen_texts:
                                seen_texts.add(txt)
                                collected.append(m)
                except ValueError:
                    continue

    # Sort by created_day descending (newest first)
    collected.sort(key=lambda x: x.get("created_day", 0), reverse=True)
    return collected[:limit]


def format_memories_for_sim_thoughts(sim_id: int, is_en: bool = False, limit: int = 5) -> Optional[str]:
    """
    Formats active memories into a prompt block for SimMind (inner thoughts).
    """
    try:
        from ai_thought_reader.config import get_context_flag
        if not get_context_flag("memory"):
            return None
    except Exception:
        pass

    active = get_all_active_memories_for_sim(sim_id, is_en=is_en, limit=limit)
    if not active:
        return None

    header = "Recent Significant Events & Memories:" if is_en else "Недавние важные события и воспоминания:"
    lines = [header]
    for m in active:
        s = (m.get("summary_en", "") if is_en and m.get("summary_en") else m.get("summary", "")).strip()
        if not s:
            continue
        if is_en:
            is_perm = m.get("is_permanent", m.get("duration_days", 0) == 0)
            if is_perm:
                lbl = "Permanent"
            else:
                dl = m.get("days_left")
                if dl is None:
                    raw_lbl = str(m.get("remaining_label", ""))
                    m_days = re.search(r'\d+', raw_lbl)
                    dl = int(m_days.group(0)) if m_days else 1
                lbl = f"{dl} day remaining" if dl == 1 else f"{dl} days remaining"
        else:
            lbl = m.get("remaining_label", "Навсегда")
        lines.append(f"• [{lbl}]: {s}")

    return "\n".join(lines)


def format_memories_for_prompt(actor_id: int, recipient_id: int) -> Optional[str]:
    """
    Formats active memories into prompt block for AI dialogues (PC chat, Direct Dialogue, autonomy).
    """
    from ai_social_pc.chat_manager import get_chat_context_flag
    if not get_chat_context_flag("chat_memory"):
        return None

    memories = get_active_memories(actor_id, recipient_id)
    # Also fetch actor's personal memories (e.g. fire, promotion, newborn)
    personal = get_active_memories(actor_id, 0)
    all_combined = list(memories)
    for pm in personal:
        if pm not in all_combined:
            all_combined.append(pm)

    if not all_combined:
        return None

    is_en = False
    try:
        from ai_social_pc.ui_chat import _is_en
        is_en = _is_en()
    except Exception:
        try:
            from ai_thought_reader.commands import is_english_active
            is_en = is_english_active()
        except Exception:
            is_en = False

    header = "MEMORIES:" if is_en else "ПАМЯТЬ:"
    lines = [header]
    for m in all_combined:
        mem_actor = m.get("actor_id")
        if mem_actor is not None and mem_actor != 0 and mem_actor != actor_id:
            continue
        s = (m.get("summary_en", "") if is_en and m.get("summary_en") else m.get("summary", "")).strip()
        if not s:
            continue
        if is_en:
            is_perm = m.get("is_permanent", m.get("duration_days", 0) == 0)
            if is_perm:
                lbl = "Permanent"
            else:
                dl = m.get("days_left")
                if dl is None:
                    raw_lbl = str(m.get("remaining_label", ""))
                    m_days = re.search(r'\d+', raw_lbl)
                    dl = int(m_days.group(0)) if m_days else 1
                lbl = f"{dl} day remaining" if dl == 1 else f"{dl} days remaining"
        else:
            lbl = m.get("remaining_label", "Навсегда")
        lines.append(f"• [{lbl}]: {s}")

    return "\n".join(lines)


def clear_all_memories() -> int:
    """Clears all stored memories from working cache."""
    all_mem = load_memories()
    count = sum(len(v) for v in all_mem.values())
    all_mem.clear()
    mark_memories_dirty()
    log(f"[MEMORY] Cleared all {count} stored memories from memory cache.")
    return count


def request_chat_summarization_async(actor_sim_info, recipient_sim_info, messages: List[Dict[str, Any]], is_direct_dialogue: bool = False):
    """
    Sends chat dialogue to Synapse Bridge for summarization in background thread.
    Executes when dialogue window is closed by player or scheduled by direct dialogue.
    """
    if not messages or len(messages) < 2:
        return

    from ai_social_pc.chat_manager import get_chat_context_flag
    if not get_chat_context_flag("chat_memory"):
        log("[MEMORY] Summarization skipped because 'chat_memory' is disabled in config.")
        return

    if is_direct_dialogue and not get_chat_context_flag("summarize_direct"):
        log("[MEMORY] Direct dialogue summarization skipped because 'summarize_direct' is disabled in config.")
        return

    if not is_direct_dialogue and not get_chat_context_flag("summarize_personal"):
        log("[MEMORY] Personal chat summarization skipped because 'summarize_personal' is disabled in config.")
        return

    thread = threading.Thread(
        target=_worker_summarize_chat,
        args=(actor_sim_info, recipient_sim_info, messages),
        daemon=True,
        name="AISocialPC-Summarizer",
    )
    thread.start()


def _worker_summarize_chat(actor_sim_info, recipient_sim_info, messages: List[Dict[str, Any]]):
    try:
        actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
        recipient_id = getattr(recipient_sim_info, "sim_id", 0) if not isinstance(recipient_sim_info, dict) else recipient_sim_info.get("id", -1)

        s_f = getattr(actor_sim_info, "first_name", "") or ""
        s_l = getattr(actor_sim_info, "last_name", "") or ""
        sender_name = f"{s_f} {s_l}".strip() or "Игрок"

        r_f = getattr(recipient_sim_info, "first_name", "") or ""
        r_l = getattr(recipient_sim_info, "last_name", "") or ""
        recipient_name = f"{r_f} {r_l}".strip() or "Собеседник"

        from ai_social_pc.chat_manager import _get_relationship_description
        rel = _get_relationship_description(actor_sim_info, recipient_sim_info)

        payload = {
            "type": "summarize",
            "sender_name": sender_name,
            "recipient_name": recipient_name,
            "relationship": rel,
            "messages": messages,
        }

        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=60)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }
        conn.request("POST", "/summarize", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8", errors="ignore")
        conn.close()

        if resp.status == 200:
            res_json = json.loads(resp_data)
            has_memory = bool(res_json.get("has_memory", False))
            summary = res_json.get("summary", "").strip() if has_memory else ""
            duration = int(res_json.get("duration_days", 3)) if has_memory else 0
            actions_list = res_json.get("actions")
            action_actor = res_json.get("action_actor")
            action_type = res_json.get("action_type")

            from ai_social_pc.main_thread import run_on_main_thread
            def _apply_chat_summary():
                if has_memory and summary:
                    add_memory(actor_id, recipient_id, summary, duration)
                else:
                    log(f"[MEMORY] Dialogue between {sender_name} and {recipient_name} was trivial; no memory recorded.")

                if actions_list or action_type:
                    try:
                        from ai_social_pc.action_executor import execute_post_chat_action, execute_post_chat_actions
                        if actions_list:
                            execute_post_chat_actions(actions_list, actor_sim_info, recipient_sim_info)
                        else:
                            execute_post_chat_action(action_actor, action_type, actor_sim_info, recipient_sim_info)
                    except Exception as ex_act:
                        log_exception("Failed executing post-chat action", ex_act)

            run_on_main_thread(_apply_chat_summary)
        else:
            log(f"[MEMORY] Bridge returned HTTP {resp.status} during summarization: {resp_data[:100]}", level="WARN")

    except Exception as e:
        log_exception("Error in _worker_summarize_chat", e)


def request_group_summarization_async(actor_sim_info, group_data: Dict[str, Any], messages: List[Dict[str, Any]]):
    """
    Sends group chat dialogue to Synapse Bridge for summarization in a background thread.
    Executes when the group chat dialog window is closed by player.
    """
    if not messages or len(messages) < 2:
        return

    from ai_social_pc.chat_manager import get_chat_context_flag
    if not get_chat_context_flag("chat_memory"):
        log("[MEMORY] Group summarization skipped because 'chat_memory' is disabled in config.")
        return

    if not get_chat_context_flag("summarize_group"):
        log("[MEMORY] Group summarization skipped because 'summarize_group' is disabled in config.")
        return

    thread = threading.Thread(
        target=_worker_summarize_group_chat,
        args=(actor_sim_info, group_data, messages),
        daemon=True,
        name="AISocialPC-GroupSummarizer",
    )
    thread.start()


def _worker_summarize_group_chat(actor_sim_info, group_data: Dict[str, Any], messages: List[Dict[str, Any]]):
    try:
        actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
        s_f = getattr(actor_sim_info, "first_name", "") or ""
        s_l = getattr(actor_sim_info, "last_name", "") or ""
        sender_name = f"{s_f} {s_l}".strip() or "Игрок"

        group_name = group_data.get("name", "Групповой чат")
        group_topic = group_data.get("topic", "").strip()
        member_ids = group_data.get("member_ids", [])

        sim_mgr = services.sim_info_manager() if services is not None else None
        from ai_social_pc.ui_chat import get_recipient_display_name

        participants = []
        member_map = {}  # name_lower -> sim_id

        for mid in member_ids:
            if mid == actor_id:
                continue
            s = sim_mgr.get(mid) if sim_mgr else None
            if s:
                m_name = get_recipient_display_name(s)
                m_first = getattr(s, "first_name", "") or ""
                m_last = getattr(s, "last_name", "") or ""
                participants.append({"name": m_name, "id": mid})
                member_map[m_name.lower()] = mid
                if m_first:
                    member_map[m_first.lower()] = mid
                if m_last:
                    member_map[m_last.lower()] = mid

        if not participants:
            return

        payload = {
            "type": "group_summarize",
            "sender_name": sender_name,
            "group_name": group_name,
            "group_topic": group_topic,
            "participants": participants,
            "messages": messages[-15:],
        }

        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=60)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }
        conn.request("POST", "/group_summarize", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8", errors="ignore")
        conn.close()

        if resp.status == 200:
            res_json = json.loads(resp_data)
            has_memory = bool(res_json.get("has_memory", False))
            memories = res_json.get("memories", [])
            actions_list = res_json.get("actions")
            action_actor = res_json.get("action_actor")
            action_type = res_json.get("action_type")

            from ai_social_pc.main_thread import run_on_main_thread
            def _apply_group_summary():
                if has_memory and memories:
                    saved_count = 0
                    for mem in memories:
                        target_name = mem.get("target_name", "")
                        summary = mem.get("summary", "").strip()
                        duration = int(mem.get("duration_days", 3))

                        # Find matching sim_id
                        matched_sim_id = None
                        t_low = target_name.lower().strip()
                        for k, sid in member_map.items():
                            if k == t_low:
                                matched_sim_id = sid
                                break
                        if not matched_sim_id:
                            for k, sid in member_map.items():
                                if k in t_low or t_low in k:
                                    matched_sim_id = sid
                                    break

                        if matched_sim_id and summary:
                            add_memory(actor_id, matched_sim_id, summary, duration)
                            saved_count += 1
                            log(f"[GROUP MEMORY] Saved episodic memory for Sim {matched_sim_id} ({target_name}): '{summary}' ([Day={duration}])")
                else:
                    log(f"[GROUP MEMORY] Dialogue in group '{group_name}' was trivial; no memory recorded.")

                if actions_list or action_type:
                    try:
                        from ai_social_pc.action_executor import execute_post_chat_action, execute_post_chat_actions
                        if actions_list:
                            execute_post_chat_actions(actions_list, actor_sim_info)
                        else:
                            execute_post_chat_action(action_actor, action_type, actor_sim_info, None)
                    except Exception as ex_act:
                        log_exception("Failed executing group post-chat action", ex_act)

            run_on_main_thread(_apply_group_summary)
        else:
            log(f"[GROUP MEMORY] Bridge returned HTTP {resp.status} during group summarization: {resp_data[:100]}", level="WARN")

    except Exception as e:
        log_exception("Error in _worker_summarize_group_chat", e)

