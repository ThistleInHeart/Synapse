import os
import json
import threading
from typing import Dict, Any, Optional
from ai_thought_reader.logger import log, log_exception

try:
    import services
except ImportError:
    services = None

LORE_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_sim_lore.json")

_WORKING_LORE_CACHE: Optional[Dict[str, str]] = None
_ACTIVE_LORE_SAVE_ID: Optional[str] = None
_IS_LORE_DIRTY: bool = False
_LORE_LOCK = threading.RLock()


def get_current_save_id() -> str:
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
    if os.path.exists(LORE_FILE_PATH):
        try:
            with open(LORE_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_sim_lore.json from disk", e)
    return {"saves": {}}


def load_lore_data() -> Dict[str, str]:
    global _WORKING_LORE_CACHE, _ACTIVE_LORE_SAVE_ID, _IS_LORE_DIRTY
    with _LORE_LOCK:
        current_save = get_current_save_id()

        if _WORKING_LORE_CACHE is not None and _ACTIVE_LORE_SAVE_ID == current_save:
            return _WORKING_LORE_CACHE

        _ACTIVE_LORE_SAVE_ID = current_save
        _IS_LORE_DIRTY = False
        disk_data = _read_disk_file()

        save_entry = disk_data.get("saves", {}).get(current_save, {})
        if isinstance(save_entry, dict):
            _WORKING_LORE_CACHE = {str(k): str(v) for k, v in save_entry.items()}
        else:
            _WORKING_LORE_CACHE = {}

        log(f"[LORE] Initialized in-memory lore for save '{current_save}': {len(_WORKING_LORE_CACHE)} sim(s)")
        return _WORKING_LORE_CACHE


def mark_lore_dirty():
    global _IS_LORE_DIRTY
    _IS_LORE_DIRTY = True


def commit_lore_data_to_disk():
    global _IS_LORE_DIRTY
    with _LORE_LOCK:
        current_save = _ACTIVE_LORE_SAVE_ID or get_current_save_id()
        if _WORKING_LORE_CACHE is None:
            return

        if not _IS_LORE_DIRTY:
            log(f"[LORE] No uncommitted lore changes for save '{current_save}'. Disk commit skipped.")
            return

        try:
            disk_data = _read_disk_file()
            if "saves" not in disk_data or not isinstance(disk_data["saves"], dict):
                disk_data["saves"] = {}

            disk_data["saves"][current_save] = _WORKING_LORE_CACHE

            temp_path = LORE_FILE_PATH + ".tmp"
            os.makedirs(os.path.dirname(LORE_FILE_PATH), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, ensure_ascii=False, indent=2)

            os.replace(temp_path, LORE_FILE_PATH)

            _IS_LORE_DIRTY = False
            log(f"[LORE] Committed lore for {len(_WORKING_LORE_CACHE)} sim(s) in save '{current_save}' to disk successfully.")
        except Exception as e:
            log_exception("Failed to commit ai_sim_lore.json to disk", e)


def reset_working_lore_cache():
    global _WORKING_LORE_CACHE, _ACTIVE_LORE_SAVE_ID, _IS_LORE_DIRTY
    with _LORE_LOCK:
        _WORKING_LORE_CACHE = None
        _ACTIVE_LORE_SAVE_ID = None
        _IS_LORE_DIRTY = False
        log("[LORE] Lore cache reset on zone unload.")


def get_custom_sim_lore(sim_id) -> str:
    if not sim_id:
        return ""
    data = load_lore_data()
    return str(data.get(str(sim_id), "")).strip()


def set_custom_sim_lore(sim_id, lore_text: str) -> bool:
    if not sim_id:
        return False
    data = load_lore_data()
    clean_text = str(lore_text).strip()
    data[str(sim_id)] = clean_text
    mark_lore_dirty()
    commit_lore_data_to_disk()
    log(f"[LORE] Updated lore in memory and committed to disk for Sim {sim_id}: '{clean_text[:40]}...'")
    return True


def delete_custom_sim_lore(sim_id) -> bool:
    if not sim_id:
        return False
    data = load_lore_data()
    s_id = str(sim_id)
    if s_id in data:
        del data[s_id]
        mark_lore_dirty()
        commit_lore_data_to_disk()
        log(f"[LORE] Deleted lore for Sim {sim_id} in memory and committed to disk.")
    return True
