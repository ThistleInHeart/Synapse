"""
Last Thought Tracker for Synapse.
Records the last generated AI thought for each Sim with in-game Sim timestamps.
Provides contextual formatting for thoughts generated within the last 1 sim-hour (60 sim-minutes).
"""

import time
from typing import Optional, Dict, Any
from ai_thought_reader.logger import log, log_exception

try:
    import services
except ImportError:
    services = None

# In-memory registry: {sim_id: {"thought": str, "sim_minutes": int, "real_time": float}}
_LAST_SIM_THOUGHTS: Dict[int, Dict[str, Any]] = {}


def get_current_sim_absolute_minutes() -> int:
    """Returns absolute in-game minutes elapsed since world start."""
    try:
        if services is not None:
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
                if hasattr(now, "absolute_minutes"):
                    res = now.absolute_minutes()
                    return int(res() if callable(res) else res)

            gc_service = services.game_clock_service()
            if gc_service is not None and hasattr(gc_service, "now"):
                now = gc_service.now()
                if hasattr(now, "absolute_minutes"):
                    res = now.absolute_minutes()
                    return int(res() if callable(res) else res)
    except Exception:
        pass

    # Fallback to real-world minutes
    return int(time.time() / 60)


def record_sim_thought(sim_id: int, thought: str):
    """Records the latest successful AI thought for a Sim."""
    if not sim_id or not thought:
        return
    clean_thought = str(thought).strip()
    if not clean_thought:
        return
    try:
        s_id = int(sim_id)
    except (ValueError, TypeError):
        return

    sim_min = get_current_sim_absolute_minutes()
    _LAST_SIM_THOUGHTS[s_id] = {
        "thought": clean_thought,
        "sim_minutes": sim_min,
        "real_time": time.time(),
    }
    log(f"[LAST THOUGHT TRACKER] Recorded thought for sim_id {s_id} at sim_min {sim_min}: '{clean_thought[:60]}...'")


def get_sim_last_thought_context(sim_info_or_id, is_en: bool = False) -> str:
    """
    Returns formatted context string if the Sim had an AI thought within the last 60 sim-minutes (1 sim-hour).
    Returns "" if no recent thought or older than 60 sim-minutes.
    """
    try:
        from ai_thought_reader.config import get_experimental_flag, get_context_flag
        if not get_experimental_flag("last_thought_context") and not get_context_flag("last_thought"):
            return ""
    except Exception:
        pass

    sim_id = getattr(sim_info_or_id, "sim_id", sim_info_or_id)
    if not sim_id:
        return ""
    try:
        sim_id = int(sim_id)
    except (ValueError, TypeError):
        return ""

    record = _LAST_SIM_THOUGHTS.get(sim_id)
    if not record:
        return ""

    cur_min = get_current_sim_absolute_minutes()
    recorded_min = record.get("sim_minutes", 0)
    elapsed = cur_min - recorded_min

    # If within 0 to 60 sim-minutes (1 in-game hour)
    if 0 <= elapsed <= 60:
        thought_text = record.get("thought", "")
        if not thought_text:
            return ""
        if is_en:
            if elapsed < 2:
                return f"- Last thought (just now): \"{thought_text}\""
            return f"- Last thought ({elapsed} min ago): \"{thought_text}\""
        else:
            if elapsed < 2:
                return f"- Последняя мысль (только что): «{thought_text}»"
            return f"- Последняя мысль ({elapsed} мин. назад): «{thought_text}»"

    return ""
