import os
import json
import time
import threading
from typing import Dict, List, Any, Optional
from ai_social_pc.logger import log, log_exception
from ai_social_pc.chat_manager import (
    get_current_sim_time,
    get_current_sim_absolute_days,
    get_current_sim_day_of_week,
    strip_emojis,
)

try:
    import services
except ImportError:
    services = None

GROUPS_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_social_groups.json")

# In-memory working state for the active save slot:
_WORKING_GROUPS_CACHE: Optional[Dict[str, Any]] = None
_ACTIVE_SAVE_ID: Optional[str] = None
_IS_DIRTY: bool = False
_GROUPS_LOCK = threading.RLock()


def get_current_save_id() -> str:
    """
    Returns the persistent unique identifier for the currently loaded save slot.
    Format:
    - 'guid_<guid>' if save_slot_proto_guid is available (64-bit int)
    - 'slot_<slot_id>' if slot_id is available
    - 'slot_default' as fallback
    """
    if services is not None:
        try:
            ps = services.get_persistence_service()
            if ps is not None:
                guid = ps.get_save_slot_proto_guid()
                if guid:
                    return f"guid_{guid}"
        except Exception:
            pass

        try:
            cur_zone = services.current_zone()
            if cur_zone is not None:
                slot_id = getattr(cur_zone, "save_slot_data_id", None)
                if slot_id:
                    return f"slot_{slot_id}"
        except Exception:
            pass

    return "slot_default"


def _read_disk_file() -> Dict[str, Any]:
    """Reads the JSON file from disk, ensuring the 'saves' dictionary exists."""
    if os.path.exists(GROUPS_FILE_PATH):
        try:
            with open(GROUPS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_social_groups.json from disk", e)
    return {"saves": {}}


def load_groups_data() -> Dict[str, Any]:
    """
    Returns the active in-memory groups cache for the current save slot.
    Loads from disk if cache is empty or if the active save changed.
    """
    global _WORKING_GROUPS_CACHE, _ACTIVE_SAVE_ID, _IS_DIRTY
    with _GROUPS_LOCK:
        current_save = get_current_save_id()

        if _WORKING_GROUPS_CACHE is not None and _ACTIVE_SAVE_ID == current_save:
            return _WORKING_GROUPS_CACHE

        _ACTIVE_SAVE_ID = current_save
        _IS_DIRTY = False
        disk_data = _read_disk_file()

        save_entry = disk_data.get("saves", {}).get(current_save)
        if save_entry and isinstance(save_entry, dict):
            groups = dict(save_entry.get("groups", {}))
            messages = {k: list(v) for k, v in save_entry.get("messages", {}).items()}
            _WORKING_GROUPS_CACHE = {"groups": groups, "messages": messages}
        else:
            _WORKING_GROUPS_CACHE = {"groups": {}, "messages": {}}

        log(f"[GROUP] Initialized in-memory groups for save '{current_save}': {len(_WORKING_GROUPS_CACHE['groups'])} group(s)")
        return _WORKING_GROUPS_CACHE


def mark_groups_dirty():
    global _IS_DIRTY
    _IS_DIRTY = True


def commit_groups_data_to_disk():
    """
    Commits current in-memory groups and messages to disk for the active save slot.
    Called immediately on changes and during game save / zone teardown.
    """
    global _IS_DIRTY
    with _GROUPS_LOCK:
        current_save = _ACTIVE_SAVE_ID or get_current_save_id()
        if _WORKING_GROUPS_CACHE is None:
            return

        if not _IS_DIRTY:
            return

        try:
            disk_data = _read_disk_file()
            if "saves" not in disk_data or not isinstance(disk_data["saves"], dict):
                disk_data["saves"] = {}

            disk_data["saves"][current_save] = {
                "groups": _WORKING_GROUPS_CACHE.get("groups", {}),
                "messages": _WORKING_GROUPS_CACHE.get("messages", {}),
            }

            temp_path = GROUPS_FILE_PATH + ".tmp"
            os.makedirs(os.path.dirname(GROUPS_FILE_PATH), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, ensure_ascii=False, indent=2)

            if os.path.exists(GROUPS_FILE_PATH):
                os.replace(temp_path, GROUPS_FILE_PATH)
            else:
                os.rename(temp_path, GROUPS_FILE_PATH)

            _IS_DIRTY = False
            log(f"[GROUP] Committed {len(_WORKING_GROUPS_CACHE['groups'])} group(s) for save '{current_save}' to disk successfully.")
        except Exception as e:
            log_exception("Failed to commit groups data to disk", e)


def reset_working_cache():
    """
    Clears in-memory working cache upon zone unload/teardown.
    Any unsaved modifications are safely dropped if the player exited without saving.
    """
    global _WORKING_GROUPS_CACHE, _ACTIVE_SAVE_ID, _IS_DIRTY
    with _GROUPS_LOCK:
        _WORKING_GROUPS_CACHE = None
        _ACTIVE_SAVE_ID = None
        _IS_DIRTY = False
        log("[GROUP] Working cache reset on zone unload.")


def create_group(name: str, owner_id: int, member_ids: List[int], topic: str = "") -> Dict[str, Any]:
    """Creates a new group in memory cache."""
    clean_name = strip_emojis(name).strip() or "Новая группа"
    clean_topic = strip_emojis(topic).strip() if topic else ""
    data = load_groups_data()

    # Ensure owner is in member_ids and IDs are ints
    m_set = {int(owner_id)}
    for m in member_ids:
        try:
            m_set.add(int(m))
        except Exception:
            pass

    grp_id = f"grp_{int(time.time())}_{abs(hash(clean_name)) % 10000}"
    cur_day = get_current_sim_absolute_days()

    group_obj = {
        "id": grp_id,
        "name": clean_name,
        "topic": clean_topic,
        "owner_id": int(owner_id),
        "member_ids": sorted(list(m_set)),
        "created_day": cur_day,
    }

    data["groups"][grp_id] = group_obj
    data["messages"][grp_id] = []
    mark_groups_dirty()
    topic_info = f", topic: '{clean_topic}'" if clean_topic else ""
    log(f"[GROUP] Created group '{clean_name}' (ID: {grp_id}{topic_info}) with {len(m_set)} members in memory cache.")
    return group_obj


def update_group_name(group_id: str, new_name: str) -> bool:
    """Updates group name in memory cache."""
    clean_name = strip_emojis(new_name).strip()
    if not clean_name:
        return False
    data = load_groups_data()
    if group_id in data.get("groups", {}):
        data["groups"][group_id]["name"] = clean_name
        mark_groups_dirty()
        log(f"[GROUP] Renamed group {group_id} to '{clean_name}'")
        return True
    return False


def update_group_topic(group_id: str, new_topic: str) -> bool:
    """Updates group meaning/topic in memory cache."""
    clean_topic = strip_emojis(new_topic).strip() if new_topic else ""
    data = load_groups_data()
    if group_id in data.get("groups", {}):
        data["groups"][group_id]["topic"] = clean_topic
        mark_groups_dirty()
        log(f"[GROUP] Updated topic for group {group_id} to '{clean_topic}'")
        return True
    return False


def get_group_topic(group_id: str) -> str:
    """Returns group meaning/topic if set, otherwise empty string."""
    data = load_groups_data()
    return data.get("groups", {}).get(str(group_id), {}).get("topic", "") or ""


def update_group_members(group_id: str, new_member_ids: List[int]) -> bool:
    """Updates list of members for a group in memory cache."""
    data = load_groups_data()
    if group_id in data.get("groups", {}):
        grp = data["groups"][group_id]
        owner_id = grp.get("owner_id", 0)
        m_set = {owner_id} if owner_id else set()
        for m in new_member_ids:
            try:
                m_set.add(int(m))
            except Exception:
                pass
        grp["member_ids"] = sorted(list(m_set))
        mark_groups_dirty()
        log(f"[GROUP] Updated members for group {group_id}: {len(m_set)} members")
        return True
    return False


def delete_group(group_id: str) -> bool:
    """Deletes group and its message history from memory cache."""
    data = load_groups_data()
    removed = False
    if group_id in data.get("groups", {}):
        data["groups"].pop(group_id, None)
        data["messages"].pop(group_id, None)
        mark_groups_dirty()
        log(f"[GROUP] Deleted group {group_id} from memory cache")
        removed = True
    try:
        from ai_social_pc.delayed_replies import remove_pending_group_reply
        remove_pending_group_reply(group_id)
    except Exception:
        pass
    return removed


def get_groups_for_sim(sim_id: int) -> List[Dict[str, Any]]:
    """Returns all groups where sim_id is a member."""
    data = load_groups_data()
    s_id = int(sim_id)
    res = []
    for grp in data.get("groups", {}).values():
        if s_id in grp.get("member_ids", []):
            res.append(grp)
    return res


def get_group_by_id(group_id: str) -> Optional[Dict[str, Any]]:
    """Returns group object by ID."""
    data = load_groups_data()
    return data.get("groups", {}).get(str(group_id))


def get_group_messages(group_id: str) -> List[Dict[str, Any]]:
    """Returns message history for a group (at most 15 messages)."""
    data = load_groups_data()
    return data.get("messages", {}).get(str(group_id), [])


def add_group_message(
    group_id: str,
    sender: str = "",
    text: str = "",
    sender_id: int = 0,
    sender_name: str = "",
) -> Dict[str, Any]:
    """Appends a message to group history with rolling window of max 15 messages."""
    data = load_groups_data()
    gid = str(group_id)
    if gid not in data["messages"]:
        data["messages"][gid] = []

    final_sender = sender or sender_name or "Участник"
    cur_time = get_current_sim_time()
    cur_day = get_current_sim_absolute_days()
    dow = get_current_sim_day_of_week()
    clean_t = strip_emojis(text)

    msg_obj = {
        "sender": final_sender,
        "sender_id": int(sender_id),
        "text": clean_t,
        "time": cur_time,
        "abs_day": cur_day,
        "dow": dow,
    }

    data["messages"][gid].append(msg_obj)
    # Strictly maintain rolling window of max 15 messages
    if len(data["messages"][gid]) > 15:
        data["messages"][gid] = data["messages"][gid][-15:]

    mark_groups_dirty()
    log(f"[GROUP MSG] {sender_name} in {gid}: '{clean_t[:40]}'")
    return msg_obj


def clear_group_history(group_id: str):
    """Clears message history for a group."""
    data = load_groups_data()
    gid = str(group_id)
    if gid in data.get("messages", {}):
        data["messages"][gid] = []
        mark_groups_dirty()
        log(f"[GROUP] Cleared message history for group {gid}")
    try:
        from ai_social_pc.delayed_replies import remove_pending_group_reply
        remove_pending_group_reply(gid)
    except Exception:
        pass

