# -*- coding: utf-8 -*-
"""
Synapse Autonomous Living Dialogue Director (Режиссёр живого общения V1)
Manages autonomous, contextual, life-driven conversations between active household Sims.
Zero-fourth-wall, 100% deterministic Sims 4 game-state evaluation.
"""

import time
import json
import threading
import re
import urllib.request
import random
from typing import Optional, List, Dict, Tuple, Any

from ai_social_pc.logger import log, log_exception

try:
    import services
    from date_and_time import DateAndTime, create_time_span
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    services = None
    DateAndTime = None
    create_time_span = None
    LocalizationHelperTuning = None

try:
    from crafting.crafting_tunable import CraftingTuning
except Exception:
    CraftingTuning = None

try:
    from objects.components.spoilable_object_mixin import SpoilableObjectMixin
except Exception:
    SpoilableObjectMixin = None

# =========================================================================
# GLOBAL CONSTANTS & TUNINGS
# =========================================================================

# Minimum silence in the household between conversations (in unpaused real seconds)
HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS = 240.0

# Minimum cooldown between dialogues for the exact same pair of Sims (in unpaused real seconds)
PAIR_COOLDOWN_REAL_SECONDS = 450.0

# Interval between Director background checks (in unpaused real seconds)
DIRECTOR_TICK_INTERVAL_REAL_SECONDS = 8.0

# Grace period protection upon entering a lot or loading a save (in unpaused real seconds)
# Prevents the Director from triggering immediately before the game has fully loaded and settled.
ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS = 60.0

# Backward compatibility aliases for cheats & debug displays (in minutes)
HOUSEHOLD_GLOBAL_COOLDOWN_MINUTES = HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS / 60.0
PAIR_COOLDOWN_MINUTES = PAIR_COOLDOWN_REAL_SECONDS / 60.0

# Window for greeting after work/school return (Sim minutes = 1 hour)
WORK_RETURN_WINDOW_MINUTES = 60.0

# Maximum distance for Sims to be considered together outdoors (meters)
MAX_OUTDOOR_PROXIMITY_METERS = 8.5

# Maximum distance for flexible eating / counter / couch proximity (meters)
MAX_EATING_PROXIMITY_METERS = 5.0

# Triggers that bypass the household silence cooldown and pair cooldowns
# because they represent urgent in-the-moment situations or vivid domestic events.
IMMEDIATE_TRIGGERS = {
    # Home immediate
    "burnt_food",
    "broken_object",
    "dirty_dish_trash",
    "late_night_awake",
    "work_return",
    "cooking_together",
    "eating_together",
    "truant_school_work",
    "ww_post_intimacy",
    "ww_accidental_nudity",
    "negative_mood_reaction",
    "witness_death",
    "fire_hazard",
    "sim_in_labor",
    "caught_cheating",
    "witnessed_cheating",
    "walk_in_intimacy",
    "electrocuted_repair",
    "paid_bills",
    # Visiting Friends immediate
    "guest_arrival_greeting",
    "guest_inappropriate_cooking",
    "guest_late_curfew_departure",
    "guest_homework_together",
    # Visiting Relatives immediate
    "relative_warm_welcome",
    "relative_helping_chores",
    "relative_homework_together",
    # NPCs on our Home Lot immediate
    "guest_home_door_greeting",
    "guest_home_after_school",
    "guest_home_fridge_snack",
    "guest_home_farewell_late",
    "service_nanny_chat",
    "service_repairman_done",
    "neighbor_welcome_wagon",
    "neighbor_door_knock",
    "two_kid_guests_playing",
    # Community Lots immediate
    "community_bar_order_chat",
    "community_cafe_barista",
}

# =========================================================================
# DIRECTOR LOT & SCENARIO CONTEXT STATES
# =========================================================================
DIRECTOR_STATE_HOME = "HOME"
DIRECTOR_STATE_VISITING_RELATIVES = "VISITING_RELATIVES"
DIRECTOR_STATE_VISITING_FRIENDS = "VISITING_FRIENDS"
DIRECTOR_STATE_COMMUNITY = "COMMUNITY"
DIRECTOR_STATE_OTHER = "OTHER"

# Triggers strictly bound to the active household's home lot (domestic routines)
HOME_ONLY_TRIGGERS = {
    "work_return",
    "truant_school_work",
    "paid_bills",
    "cooking_together",
    "eating_together",
    "morning_coffee",
    "bedtime_pillow_talk",
    "late_night_awake",
    "pc_siblings_share",
    "homework_not_done",
    "homework_in_progress",
    "homework_done",
    "watching_tv_together",
    "ambient_living_room",
}

# Universal emergency, drama, and leisure triggers ported to residential visiting modes
PORTED_VISITING_TRIGGERS = {
    # Emergencies & Incidents
    "fire_hazard",
    "witness_death",
    "sim_in_labor",
    "negative_mood_reaction",
    "electrocuted_repair",
    "burnt_food",
    "broken_object",
    # Romance, intimacy, drama
    "caught_cheating",
    "witnessed_cheating",
    "walk_in_intimacy",
    "ww_post_intimacy",
    "ww_accidental_nudity",
    # Leisure & Hobbies
    "table_games",
    "music_performance",
    "gardening_together",
    "creative_painting",
    "pet_care",
    "fitness_workout",
}

# Dedicated 11 scenarios for Guests and NPCs visiting the player's home lot
NPC_HOME_TRIGGERS = {
    # Guest / NPC <-> Played Household Sim
    "neighbor_welcome_wagon",
    "service_repairman_done",
    "guest_home_door_greeting",
    "guest_home_after_school",
    "guest_home_farewell_late",
    "service_nanny_chat",
    "neighbor_door_knock",
    "guest_home_fridge_snack",
    "service_maid_cleaning",
    # NPC <-> NPC on our lot
    "two_guests_living_room",
    "two_kid_guests_playing",
}

# Exactly 44 scenarios permitted on the home lot
HOME_TRIGGERS = HOME_ONLY_TRIGGERS | PORTED_VISITING_TRIGGERS | NPC_HOME_TRIGGERS | {"dirty_dish_trash"}

# Dedicated 8 scenarios for visiting friends / acquaintances
DEDICATED_VISITING_FRIENDS_TRIGGERS = {
    "guest_arrival_greeting",
    "guest_inappropriate_cooking",
    "guest_late_curfew_departure",
    "guest_homework_together",
    "guest_gaming_console_tv",
    "guest_eating_drinking",
    "guest_music_dance_chill",
    "guest_ambient_hangout",
}

# All 26 triggers permitted when visiting friends
VISITING_FRIENDS_TRIGGERS = DEDICATED_VISITING_FRIENDS_TRIGGERS | PORTED_VISITING_TRIGGERS

# Dedicated 8 scenarios for visiting relatives
DEDICATED_VISITING_RELATIVES_TRIGGERS = {
    "relative_warm_welcome",
    "relative_helping_chores",
    "relative_homework_together",
    "relative_eating_together",
    "relative_interrogation_life",
    "relative_cousins_hanging",
    "relative_adult_family_gossip",
    "relative_ambient_visit",
}

# All 27 triggers permitted when visiting relatives (includes dirty_dish_trash for relative household chores)
VISITING_RELATIVES_TRIGGERS = DEDICATED_VISITING_RELATIVES_TRIGGERS | PORTED_VISITING_TRIGGERS | {"dirty_dish_trash"}

# Dedicated 7 scenarios for Community Lots
DEDICATED_COMMUNITY_TRIGGERS = {
    "community_bar_order_chat",
    "community_cafe_barista",
    "community_gym_workout_spot",
    "community_restaurant_companion",
    "community_library_whisper",
    "community_player_social",
    "community_ambient_social",
}

# All permitted triggers on community lots (dedicated + emergencies, drama, leisure)
COMMUNITY_TRIGGERS = DEDICATED_COMMUNITY_TRIGGERS | PORTED_VISITING_TRIGGERS

# Triggers explicitly permitted to occur between two NPCs (NPC <-> NPC) without played household members
NPC_NPC_ALLOWED_TRIGGERS = PORTED_VISITING_TRIGGERS | {
    # Visiting Friends
    "guest_homework_together",
    "guest_gaming_console_tv",
    "guest_eating_drinking",
    "guest_music_dance_chill",
    "guest_ambient_hangout",
    # Visiting Relatives
    "relative_homework_together",
    "relative_eating_together",
    "relative_interrogation_life",
    "relative_cousins_hanging",
    "relative_adult_family_gossip",
    "relative_ambient_visit",
    # NPCs on our Home Lot
    "two_guests_living_room",
    "two_kid_guests_playing",
    # Community Lots
    "community_ambient_social",
}

# Per-trigger custom cooldowns in unpaused real seconds.
# When a trigger fires, it cannot fire again for ANY Sims until this duration expires.
TRIGGER_COOLDOWNS_REAL_SECONDS: Dict[str, float] = {
    "cooking_together": 180.0,  # 3 minutes cooldown after cooking dialogue
    "guest_inappropriate_cooking": 240.0,
    "relative_helping_chores": 240.0,
    "community_bar_order_chat": 180.0,
    "community_cafe_barista": 180.0,
    "community_player_social": 180.0,
    "community_ambient_social": 240.0,
}

# Per-trigger debounce cooldown to prevent consecutive immediate re-firing (in Sim minutes)
TRIGGER_DEBOUNCE_COOLDOWN_MINUTES = 20.0

# Global state trackers
_last_scene_sim_time: Optional[Any] = None
_last_scene_real_time: float = 0.0
_last_ambient_scene_sim_time: Optional[Any] = None
_last_ambient_scene_real_time: float = -999999.0
_last_director_check_sim_minute = -1
_last_director_check_real_time: float = 0.0
_last_silence_telemetry_real_time: float = 0.0
_zone_load_system_time: float = time.time()
_zone_load_unpaused_real_time: float = 0.0
_last_grace_telemetry_real_time: float = 0.0
_accumulated_unpaused_real_seconds: float = 0.0
_last_unpaused_system_time: float = time.time()
_is_scene_in_flight: bool = False
_current_scene_trigger_type: str = ""
_last_completed_scene_info: Dict[str, Any] = {}
_pair_last_scene_sim_time: Dict[Tuple[int, int], Any] = {}
_pair_last_scene_real_time: Dict[Tuple[int, int], float] = {}
_trigger_last_scene_sim_time: Dict[str, Any] = {}
_trigger_last_scene_real_time: Dict[str, float] = {}
_daily_triggers_fired: Dict[str, int] = {}  # key -> absolute_sim_day
_weekly_triggers_fired: Dict[str, int] = {}  # weekly_key -> times_fired_in_week
_sim_work_return_tracker: Dict[int, Any] = {}  # sim_id -> return_sim_time
_sim_previous_work_state: Dict[int, bool] = {}  # sim_id -> was_at_work
_sim_post_woohoo_tracker: Dict[int, Any] = {}  # sim_id -> finish_sim_time
_sim_previous_sex_state: Dict[int, bool] = {}  # sim_id -> was_in_sex
_sim_last_sex_data: Dict[int, Any] = {}  # sim_id -> last active sex dict (partners, location)
_sim_bills_paid_tracker: Dict[int, Any] = {}  # sim_id -> paid_sim_time
_sim_recent_romance_tracker: Dict[int, Dict[str, Any]] = {}  # sim_id -> {timestamp, target_info, target_id, affordance_name}
_sim_recent_intimacy_tracker: Dict[int, Dict[str, Any]] = {}  # sim_id -> {timestamp, actor_ids, total_participants, location_and_privacy, scene_scale, is_active}
ROMANCE_CHEATING_WINDOW_MINUTES = 8.0
INTIMACY_WALK_IN_WINDOW_MINUTES = 8.0
POST_WOOHOO_WINDOW_MINUTES = 30.0
BURNT_FOOD_WINDOW_MINUTES = 30.0
_last_silence_telemetry_sim_minute: int = -9999


def send_director_telemetry(event_type: str, title: str, details: Optional[List[str]] = None, level: str = "INFO", data: Optional[Dict[str, Any]] = None):
    """
    Sends real-time telemetry to AI Bridge (/director_log) in a fire-and-forget daemon thread.
    Zero impact on game simulation.
    """
    def _post():
        try:
            from ai_social_pc.chat_manager import BRIDGE_HOST, BRIDGE_PORT
            payload = {
                "type": event_type,
                "title": title,
                "details": details or [],
                "level": level,
                "data": data or {}
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/director_log"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                pass
        except Exception:
            pass

    t = threading.Thread(target=_post, name="SynapseDirectorTelemetryThread", daemon=True)
    t.start()


def get_sim_now() -> Optional[Any]:
    """Safely gets current in-game DateAndTime object."""
    if services is None:
        return None
    try:
        ts = services.time_service()
        if ts is not None and hasattr(ts, "sim_now"):
            return ts.sim_now
        gcs = services.game_clock_service()
        if gcs is not None and hasattr(gcs, "now"):
            return gcs.now()
    except Exception:
        pass
    return None


def get_current_sim_day() -> int:
    """Returns absolute integer day for 1-time-per-day tracking."""
    now = get_sim_now()
    if now is None:
        return 0
    try:
        # absolute_days or day()
        if hasattr(now, "absolute_days"):
            return int(now.absolute_days())
        if hasattr(now, "day"):
            return int(now.day())
    except Exception:
        pass
    return 0


def get_current_sim_week() -> int:
    """Returns absolute integer week (derived from sim day // 7) for weekly limit tracking."""
    return get_current_sim_day() // 7


def get_weekly_key_from_daily(daily_key: str, curr_week: int) -> str:
    """
    Derives a weekly tracking key from a daily key.
    Strips trailing day suffix if present (e.g. '_12') and appends '_w{curr_week}'.
    Preserves exact per-event, per-sim, or per-pair granularity!
    """
    clean_base = re.sub(r'_\d+$', '', str(daily_key))
    return f"{clean_base}_w{curr_week}"


def get_sim_minutes_between(time_a: Any, time_b: Any) -> float:
    """Calculates difference in sim minutes between two DateAndTime objects."""
    if time_a is None or time_b is None:
        return 999999.0
    try:
        span = time_b - time_a
        if hasattr(span, "in_minutes"):
            m = span.in_minutes() if callable(span.in_minutes) else span.in_minutes
            return float(m)
        if hasattr(span, "in_sim_minutes"):
            m = span.in_sim_minutes() if callable(span.in_sim_minutes) else span.in_sim_minutes
            return float(m)
    except Exception:
        pass
    try:
        if hasattr(time_b, "absolute_minutes") and hasattr(time_a, "absolute_minutes"):
            mb = time_b.absolute_minutes() if callable(time_b.absolute_minutes) else time_b.absolute_minutes
            ma = time_a.absolute_minutes() if callable(time_a.absolute_minutes) else time_a.absolute_minutes
            return float(mb - ma)
    except Exception:
        pass
    try:
        if hasattr(time_b, "hour") and hasattr(time_a, "hour"):
            b_h = time_b.hour() if callable(time_b.hour) else int(time_b.hour)
            b_m = time_b.minute() if callable(time_b.minute) else int(time_b.minute)
            a_h = time_a.hour() if callable(time_a.hour) else int(time_a.hour)
            a_m = time_a.minute() if callable(time_a.minute) else int(time_a.minute)
            diff = (b_h * 60 + b_m) - (a_h * 60 + a_m)
            if diff < 0:
                diff += (24 * 60)
            return float(diff)
    except Exception:
        pass
    return 999999.0


def is_game_paused() -> bool:
    """Returns True if the Sims 4 simulation clock is paused (clock_speed == 0)."""
    if services is None:
        return False
    try:
        if hasattr(services, "game_clock_service"):
            gcs = services.game_clock_service()
            if gcs is not None:
                return getattr(gcs, "clock_speed", 1) == 0
    except Exception:
        pass
    return False


def update_unpaused_real_time() -> float:
    """
    Accumulates elapsed real seconds only while the game is NOT paused (clock_speed > 0).
    Freezes completely during pause or long interruptions.
    """
    global _accumulated_unpaused_real_seconds, _last_unpaused_system_time
    now = time.time()
    dt = now - _last_unpaused_system_time
    _last_unpaused_system_time = now

    if is_game_paused():
        return _accumulated_unpaused_real_seconds

    if 0 < dt < 60.0:
        _accumulated_unpaused_real_seconds += dt
    return _accumulated_unpaused_real_seconds


def get_unpaused_real_time() -> float:
    """Returns monotonically increasing unpaused real seconds."""
    return update_unpaused_real_time()


def record_player_action(actor_sim_info=None, target_sim_info=None):
    """
    Call whenever the player sends a message or opens direct dialogue ('Живое общение').
    Sets a moderate household silence cooldown (45s) so the household has quiet time after player interaction.
    """
    global _last_ambient_scene_real_time
    now_rt = get_unpaused_real_time()
    _last_ambient_scene_real_time = now_rt - (HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS - 45.0)
    if actor_sim_info and target_sim_info:
        s_a = getattr(actor_sim_info, "sim_id", 0)
        s_b = getattr(target_sim_info, "sim_id", 0)
        if s_a and s_b:
            pk = (min(s_a, s_b), max(s_a, s_b))
            _pair_last_scene_real_time[pk] = now_rt
    log("[DIRECTOR] Player Direct Dialogue recorded. Household silence cooldown set (45s).")


def reset_all_cooldowns():
    """Resets all cooldowns and daily limits for instant testing."""
    global _last_scene_sim_time, _last_ambient_scene_sim_time, _is_scene_in_flight
    global _last_scene_real_time, _last_ambient_scene_real_time, _last_director_check_real_time, _last_silence_telemetry_real_time
    global _accumulated_unpaused_real_seconds, _last_unpaused_system_time
    global _pair_last_scene_sim_time, _pair_last_scene_real_time, _trigger_last_scene_sim_time, _trigger_last_scene_real_time, _daily_triggers_fired, _weekly_triggers_fired, _sim_work_return_tracker
    global _sim_post_woohoo_tracker, _sim_previous_sex_state
    global _last_director_check_sim_minute, _current_scene_trigger_type, _sim_bills_paid_tracker, _sim_recent_romance_tracker, _sim_recent_intimacy_tracker
    _last_scene_sim_time = None
    _last_scene_real_time = 0.0
    _last_ambient_scene_sim_time = None
    _last_ambient_scene_real_time = -999999.0
    _last_director_check_real_time = 0.0
    _last_silence_telemetry_real_time = 0.0
    global _zone_load_unpaused_real_time, _last_grace_telemetry_real_time
    _zone_load_unpaused_real_time = -999999.0
    _last_grace_telemetry_real_time = 0.0
    _accumulated_unpaused_real_seconds = 0.0
    _last_unpaused_system_time = time.time()
    _is_scene_in_flight = False
    _current_scene_trigger_type = ""
    _last_completed_scene_info.clear()
    _last_director_check_sim_minute = -1
    _pair_last_scene_sim_time.clear()
    _pair_last_scene_real_time.clear()
    _trigger_last_scene_sim_time.clear()
    _trigger_last_scene_real_time.clear()
    _daily_triggers_fired.clear()
    _weekly_triggers_fired.clear()
    _sim_work_return_tracker.clear()
    _sim_post_woohoo_tracker.clear()
    _sim_previous_sex_state.clear()
    _sim_last_sex_data.clear()
    _sim_bills_paid_tracker.clear()
    _sim_recent_romance_tracker.clear()
    _sim_recent_intimacy_tracker.clear()
    log("[DIRECTOR] All cooldowns, daily and weekly limits reset!")
    send_director_telemetry(
        "RESET",
        "[LOOP] Сброс всех кулдаунов Режиссёра",
        ["Таймеры тишины дома, кулдауны пар, поводов, суточные и недельные лимиты успешно обнулены"],
        level="INFO"
    )


def are_sims_related(info_a, info_b) -> bool:
    """Checks if two SimInfos are related in any way (family, genealogy, in-laws)."""
    if info_a is None or info_b is None:
        return False
    a_id = getattr(info_a, "sim_id", 0)
    b_id = getattr(info_b, "sim_id", 0)
    if not a_id or not b_id or a_id == b_id:
        return False

    # 1. Check relationship tracker bits
    rel_tracker = getattr(info_a, "relationship_tracker", None)
    if rel_tracker is not None:
        try:
            family_keywords = (
                "family", "parent", "child", "son", "daughter",
                "brother", "sister", "sibling", "grandparent",
                "grandchild", "aunt", "uncle", "niece", "nephew",
                "cousin", "in_law", "inlaw", "step_"
            )
            for b in rel_tracker.get_all_bits(b_id):
                b_name = (getattr(b, "__name__", "") or str(b)).lower()
                for kw in family_keywords:
                    if kw in b_name:
                        return True
        except Exception:
            pass

    # 2. Check genealogy direct methods
    gen_a = getattr(info_a, "genealogy", None)
    if gen_a is not None:
        try:
            # Parents
            for p_attr in ("get_parent_sim_ids_gen", "get_parents"):
                if hasattr(gen_a, p_attr):
                    val = getattr(gen_a, p_attr)
                    items = val() if callable(val) else val
                    for p in (items or []):
                        p_id = getattr(p, "sim_id", p)
                        if p_id == b_id:
                            return True
            # Children
            for c_attr in ("get_children_sim_ids_gen", "get_children"):
                if hasattr(gen_a, c_attr):
                    val = getattr(gen_a, c_attr)
                    items = val() if callable(val) else val
                    for c in (items or []):
                        c_id = getattr(c, "sim_id", c)
                        if c_id == b_id:
                            return True
            # Siblings
            for s_attr in ("get_siblings_sim_ids_gen", "get_siblings"):
                if hasattr(gen_a, s_attr):
                    val = getattr(gen_a, s_attr)
                    items = val() if callable(val) else val
                    for s in (items or []):
                        s_id = getattr(s, "sim_id", s)
                        if s_id == b_id:
                            return True
            # Grandparents
            for gp_attr in ("get_grandparent_sim_ids_gen", "get_grandparents"):
                if hasattr(gen_a, gp_attr):
                    val = getattr(gen_a, gp_attr)
                    items = val() if callable(val) else val
                    for gp in (items or []):
                        gp_id = getattr(gp, "sim_id", gp)
                        if gp_id == b_id:
                            return True
            # Grandchildren
            for gc_attr in ("get_grandchild_sim_infos", "get_grandchildren"):
                if hasattr(gen_a, gc_attr):
                    val = getattr(gen_a, gc_attr)
                    items = val() if callable(val) else val
                    for gc in (items or []):
                        gc_id = getattr(gc, "sim_id", gc)
                        if gc_id == b_id:
                            return True
            # Family relationship bit from genealogy
            if hasattr(gen_a, "get_family_relationship_bit"):
                f_bit = gen_a.get_family_relationship_bit(b_id)
                if f_bit is not None:
                    return True
        except Exception:
            pass

    return False


def get_director_lot_state() -> str:
    """
    Strictly determines the current Director state:
    - 'HOME': Active household is at their own home lot.
    - 'VISITING_RELATIVES': Active household is on another residential lot, and at least
      one active Sim (or their spouse) is related to someone in the host household.
    - 'VISITING_FRIENDS': Active household is on another residential lot with resident hosts,
      but no relative/family ties exist.
    - 'COMMUNITY': Public/community lot (bar, cafe, gym, restaurant, park, library, etc.).
    - 'OTHER': Workplace, unowned residential, etc.
    """
    if services is None:
        return DIRECTOR_STATE_HOME

    try:
        active_hh = services.active_household()
        if active_hh is None:
            return DIRECTOR_STATE_HOME

        curr_zone_id = services.current_zone_id()
        home_zone_id = getattr(active_hh, "home_zone_id", None)

        # 1. At Home
        if curr_zone_id and home_zone_id and curr_zone_id == home_zone_id:
            return DIRECTOR_STATE_HOME

        # 2. Check active venue type (Community / Public lots)
        venue_service = services.venue_service() if hasattr(services, "venue_service") else None
        active_venue = getattr(venue_service, "active_venue", None) if venue_service else None
        v_name = getattr(active_venue, "__name__", str(active_venue)).lower() if active_venue else ""

        is_residential = ("residential" in v_name or "apartment" in v_name or "penthouse" in v_name)
        if active_venue is not None and not is_residential:
            return DIRECTOR_STATE_COMMUNITY

        # 3. On another lot: Check if it's a residential lot with a resident household
        active_lot = services.active_lot()
        if active_lot is None:
            return DIRECTOR_STATE_OTHER

        owner_hh_id = getattr(active_lot, "owner_household_id", None)
        if not owner_hh_id:
            if not is_residential and v_name:
                return DIRECTOR_STATE_COMMUNITY
            return DIRECTOR_STATE_OTHER

        # If owner is the active household, it's considered HOME
        if owner_hh_id == getattr(active_hh, "id", None):
            return DIRECTOR_STATE_HOME

        # Retrieve the host household living on this lot
        hh_mgr = services.household_manager() if hasattr(services, "household_manager") else None
        if hh_mgr is None:
            return DIRECTOR_STATE_OTHER
        host_hh = hh_mgr.get(owner_hh_id)
        if host_hh is None:
            return DIRECTOR_STATE_OTHER

        # Collect all Sims from active household (and their spouses)
        active_sims = list(active_hh.sim_info_gen())
        sim_mgr = services.sim_info_manager() if hasattr(services, "sim_info_manager") else None
        extended_active_sims = list(active_sims)
        for a_sim in active_sims:
            spouse_id = getattr(a_sim, "spouse_sim_id", None)
            if spouse_id and sim_mgr:
                sp_info = sim_mgr.get(spouse_id)
                if sp_info and sp_info not in extended_active_sims:
                    extended_active_sims.append(sp_info)

        # Collect all Sims from host household
        host_sims = list(host_hh.sim_info_gen())

        # Check for any relative link between ANY active Sim and ANY host Sim
        for a_sim in extended_active_sims:
            for h_sim in host_sims:
                if are_sims_related(a_sim, h_sim):
                    return DIRECTOR_STATE_VISITING_RELATIVES

        # If residential lot has owners but no family links -> Visiting Friends / Acquaintances
        return DIRECTOR_STATE_VISITING_FRIENDS

    except Exception as e:
        log_exception("Error in get_director_lot_state", e)
        return DIRECTOR_STATE_HOME


def is_daily_trigger_fired(trigger_key: str) -> bool:
    """Checks if a trigger was already fired today."""
    curr_day = get_current_sim_day()
    last_day = _daily_triggers_fired.get(trigger_key, -1)
    return (last_day == curr_day)


def can_trigger_fire_today(daily_key: str, trigger_type: str = "", force: bool = False) -> bool:
    """
    Checks if a trigger is allowed to fire today and this week.
    Does NOT mark the trigger as fired!
    Bypassed only when force=True.
    """
    if force:
        return True
    if is_daily_trigger_fired(daily_key):
        return False



    return True


def mark_daily_trigger_fired(trigger_key: str, trigger_type: str = ""):
    """Marks a trigger as used for today and increments weekly counter."""
    _daily_triggers_fired[trigger_key] = get_current_sim_day()

    curr_week = get_current_sim_week()
    w_key = get_weekly_key_from_daily(trigger_key, curr_week)
    _weekly_triggers_fired[w_key] = _weekly_triggers_fired.get(w_key, 0) + 1


def is_scene_in_flight() -> bool:
    """Returns True if an autonomous scene is currently being generated or played."""
    return _is_scene_in_flight


def on_director_zone_load():
    """Triggered on zone load (entering a lot / loading a save / returning from CAS). Starts the 60s grace protection."""
    global _zone_load_system_time, _zone_load_unpaused_real_time, _last_grace_telemetry_real_time
    _zone_load_system_time = time.time()
    _zone_load_unpaused_real_time = get_unpaused_real_time()
    _last_grace_telemetry_real_time = 0.0
    log(f"[DIRECTOR] Zone load detected. {int(ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS)}s grace period protection activated.")
    send_director_telemetry(
        "ZONE_LOAD_GRACE",
        f"Защита при входе на участок: {int(ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS)}с",
        ["Режиссёр ожидает стабилизации игры после загрузки зоны", f"Защита активна {int(ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS)} сек. реального времени"],
        level="INFO"
    )


def get_zone_load_grace_remaining_seconds() -> float:
    """Returns remaining grace period in unpaused real seconds before Director is allowed to trigger any autonomous scenes."""
    global _zone_load_unpaused_real_time
    if _zone_load_unpaused_real_time <= 0.0:
        _zone_load_unpaused_real_time = get_unpaused_real_time()
    now_rt = get_unpaused_real_time()
    passed = now_rt - _zone_load_unpaused_real_time
    if passed < 0.0:
        passed = 0.0
    grace_sec = ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS
    try:
        from ai_thought_reader.config import get_director_timers
        grace_sec = float(get_director_timers().get("grace_period_sec", ZONE_LOAD_GRACE_PERIOD_REAL_SECONDS))
    except Exception:
        pass
    rem = grace_sec - passed
    return max(0.0, rem)


def get_household_silence_remaining_seconds() -> float:
    """Returns remaining cooldown in unpaused real seconds before next AMBIENT autonomous dialogue can fire."""

    if _last_ambient_scene_real_time <= 0:
        return 0.0
    now_rt = get_unpaused_real_time()
    passed = now_rt - _last_ambient_scene_real_time
    silence_sec = HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS
    try:
        from ai_thought_reader.config import get_director_timers
        silence_sec = float(get_director_timers().get("household_silence_sec", HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS))
    except Exception:
        pass
    rem = silence_sec - passed
    return max(0.0, rem)


def get_household_cooldown_remaining_minutes() -> float:
    """Returns remaining cooldown in Sim minutes before next AMBIENT autonomous dialogue can fire."""
    return get_household_silence_remaining_seconds() / 60.0


def get_pair_cooldown_remaining_seconds(sim_id_a: int, sim_id_b: int) -> float:
    """Returns remaining pair cooldown in unpaused real seconds."""

    pair_key = (min(sim_id_a, sim_id_b), max(sim_id_a, sim_id_b))
    last_time = _pair_last_scene_real_time.get(pair_key)
    if last_time is None or last_time <= 0:
        return 0.0
    now_rt = get_unpaused_real_time()
    passed = now_rt - last_time
    pair_sec = PAIR_COOLDOWN_REAL_SECONDS
    try:
        from ai_thought_reader.config import get_director_timers
        pair_sec = float(get_director_timers().get("pair_cooldown_sec", PAIR_COOLDOWN_REAL_SECONDS))
    except Exception:
        pass
    rem = pair_sec - passed
    return max(0.0, rem)


def get_pair_cooldown_remaining_minutes(sim_id_a: int, sim_id_b: int) -> float:
    """Returns remaining pair cooldown in Sim minutes."""
    return get_pair_cooldown_remaining_seconds(sim_id_a, sim_id_b) / 60.0


def get_trigger_cooldown_remaining_seconds(trigger_type: str) -> float:
    """Returns remaining cooldown in unpaused real seconds for a specific trigger type."""

    cd_sec = TRIGGER_COOLDOWNS_REAL_SECONDS.get(trigger_type, 0.0)
    if cd_sec <= 0:
        return 0.0
    last_rt = _trigger_last_scene_real_time.get(trigger_type, 0.0)
    if last_rt <= 0:
        return 0.0
    now_rt = get_unpaused_real_time()
    passed = now_rt - last_rt
    rem = cd_sec - passed
    return max(0.0, rem)


def get_daily_triggers_summary() -> Dict[str, int]:
    """Returns copy of active daily triggers dictionary."""
    return dict(_daily_triggers_fired)


def get_last_completed_scene_info() -> Dict[str, Any]:
    """Returns info about the last completed autonomous scene."""
    return dict(_last_completed_scene_info)


# =========================================================================
# SPATIAL & AVAILABILITY CHECKS
# =========================================================================

def is_sim_on_or_near_active_lot(sim_instance) -> bool:
    """
    Returns True if the Sim is on the active lot or in the immediately adjacent outdoor zone
    (e.g., sidewalk, mailbox, driveway, road curb where Sims arrive from work/school).
    """
    if sim_instance is None:
        return False
    try:
        # 1. Native lot check (on lot boundary grid)
        if getattr(sim_instance, "is_on_active_lot", lambda: False)():
            return True

        # 2. Outdoor zone immediately adjacent to active lot (sidewalk, street, mailbox)
        if services is not None and hasattr(services, "active_lot"):
            lot = services.active_lot()
            if lot is not None and hasattr(sim_instance, "position"):
                sim_pos = sim_instance.position
                lot_pos = getattr(lot, "position", None)
                if sim_pos is not None and lot_pos is not None:
                    dist = float((sim_pos - lot_pos).magnitude())
                    max_lot_radius = 45.0
                    try:
                        corners = getattr(lot, "corners", None)
                        if corners:
                            max_lot_radius = max(float((c - lot_pos).magnitude()) for c in corners)
                    except Exception:
                        pass
                    # Within lot boundary radius + 25 meters (covers sidewalk, curb, spawn portal)
                    if dist <= (max_lot_radius + 25.0):
                        return True
    except Exception as e:
        log_exception("Error in is_sim_on_or_near_active_lot", e)
    return False


def is_sim_currently_at_work(sim_info) -> bool:
    """Checks if a Sim is currently at work, school, or in an away career rabbit hole."""
    if sim_info is None or isinstance(sim_info, dict):
        return False
    try:
        ct = getattr(sim_info, "career_tracker", None)
        if ct is not None:
            if hasattr(ct, "get_at_work_career"):
                c = ct.get_at_work_career()
                if c is not None:
                    return True
            careers = getattr(ct, "_careers", None) or getattr(ct, "careers", {})
            for c in careers.values():
                if getattr(c, "currently_at_work", False):
                    return True
                inst = getattr(sim_info, "get_sim_instance", lambda: None)()
                if inst is not None:
                    on_lot = is_sim_on_or_near_active_lot(inst)
                    if not on_lot and hasattr(c, "is_work_time") and c.is_work_time:
                        if not getattr(c, "taking_day_off", False) and not getattr(c, "on_vacation", False):
                            return True
    except Exception:
        pass
    return False


def is_sim_truant_from_work_or_school(sim_info) -> Tuple[bool, bool, str, str]:
    """
    Checks if a Sim is currently skipping work or school.
    Returns:
        (is_truant: bool, is_school: bool, career_title: str, status_desc: str)
    """
    if sim_info is None or isinstance(sim_info, dict):
        return False, False, "", "Сим не найден"

    try:
        # If the sim is already at work / school, they are not truant
        if is_sim_currently_at_work(sim_info):
            return False, False, "", "Сим сейчас на работе/учёбе"

        ct = getattr(sim_info, "career_tracker", None)
        if ct is None:
            return False, False, "", "Нет данных о карьере"

        careers = getattr(ct, "careers", None) or getattr(ct, "_careers", {})
        if not careers:
            return False, False, "", "Сим не учится и не трудоустроен"

        from ai_thought_reader.context import get_career_status_and_schedule, CAREER_TRANSLATIONS

        for career in careers.values():
            if getattr(career, "currently_at_work", False):
                continue
            if getattr(career, "taking_day_off", False) or getattr(career, "on_vacation", False):
                continue
            if getattr(career, "on_assignment", False):
                continue

            details = get_career_status_and_schedule(career, sim_info)
            status_str = details.get("status", "")
            is_school = details.get("is_school", False)
            status_lower = status_str.lower()

            # Determine career / school name
            cls_obj = getattr(career, "__class__", None)
            cls_name = getattr(cls_obj, "__name__", "") if cls_obj else ""
            raw_name = getattr(career, "__name__", "") or cls_name or str(career)
            if " on " in raw_name:
                raw_name = raw_name.split(" on ")[0]
            raw_name = raw_name.strip("<> ")
            c_name_lower = raw_name.lower()

            if is_school:
                car_title = "Старшая школа" if ("high" in c_name_lower or "старш" in c_name_lower) else ("Начальная школа" if ("grade" in c_name_lower or "начальн" in c_name_lower) else "Школа")
            else:
                car_title = None
                try:
                    if LocalizationHelperTuning is not None:
                        if hasattr(career, "get_career_name"):
                            c_loc = LocalizationHelperTuning.get_raw_text(career.get_career_name())
                            if c_loc and len(c_loc.strip()) > 1:
                                car_title = c_loc.strip()
                        elif hasattr(career, "career_name"):
                            c_loc = LocalizationHelperTuning.get_raw_text(career.career_name)
                            if c_loc and len(c_loc.strip()) > 1:
                                car_title = c_loc.strip()
                except Exception:
                    pass

                if not car_title:
                    for k, v in CAREER_TRANSLATIONS.items():
                        if k in c_name_lower:
                            car_title = v
                            break

                if not car_title:
                    clean_c = c_name_lower.replace("careers_", "").replace("career_", "").replace("adult_", "").replace("teen_", "").replace("child_", "").strip()
                    if clean_c.endswith(" on"):
                        clean_c = clean_c[:-3].strip()
                    car_title = clean_c.capitalize()

            # Check if skipping / truant: must be genuine work hours according to game engine
            is_work_time = bool(getattr(career, "is_work_time", False))
            is_truant_by_status = any(k in status_lower for k in ["прогуливает", "опаздывает"])
            not_excused = not any(k in status_lower for k in ["выходной", "отпуск", "каникулы", "больничн", "из дома"])

            if is_work_time and is_truant_by_status and not_excused:
                return True, is_school, car_title, status_str or ("Прогуливает уроки" if is_school else "Прогуливает работу")

        # If not truant, return the status of the first career for diagnostic info
        first_career = next(iter(careers.values()))
        d_first = get_career_status_and_schedule(first_career, sim_info)
        f_status = d_first.get("status", "Нет активной смены")
        return False, d_first.get("is_school", False), "", f_status

    except Exception as e:
        log_exception("Error in is_sim_truant_from_work_or_school", e)
        return False, False, "", f"Ошибка проверки: {e}"


def get_minutes_since_sim_shift_ended(sim_info, now=None) -> Optional[float]:
    """
    Returns how many sim minutes ago the Sim finished work/school today, if within 60 minutes.
    Returns None if the Sim did not finish work/school recently today.
    """
    if sim_info is None or isinstance(sim_info, dict):
        return None
    try:
        if is_sim_currently_at_work(sim_info):
            return None
        if now is None:
            now = get_sim_now()
        if now is None:
            return None

        ct = getattr(sim_info, "career_tracker", None)
        if ct is None:
            return None

        now_h = now.hour() if callable(getattr(now, "hour", None)) else int(getattr(now, "hour", 12))
        now_m = now.minute() if callable(getattr(now, "minute", None)) else int(getattr(now, "minute", 0))
        now_day = now.day() if callable(getattr(now, "day", None)) else int(getattr(now, "day", 0))
        now_total_mins = now_h * 60 + now_m

        careers = getattr(ct, "_careers", None) or getattr(ct, "careers", {})
        for career in careers.values():
            if getattr(career, "taking_day_off", False) or getattr(career, "on_vacation", False):
                continue

            work_scheduler = getattr(career, "work_scheduler", None)
            entry_days = []
            start_h, start_m, end_h, end_m = None, None, None, None

            if work_scheduler is not None:
                entries = getattr(work_scheduler, "_schedule_entries", None) or []
                if entries:
                    for entry in entries:
                        st = getattr(entry, "start_time", None)
                        et = getattr(entry, "end_time", None)
                        if st is not None:
                            d = st.day() if callable(getattr(st, "day", None)) else int(getattr(st, "day", 0))
                            entry_days.append(d)
                            if start_h is None:
                                start_h = st.hour() if callable(getattr(st, "hour", None)) else int(getattr(st, "hour", 0))
                                start_m = st.minute() if callable(getattr(st, "minute", None)) else int(getattr(st, "minute", 0))
                        if et is not None and end_h is None:
                            end_h = et.hour() if callable(getattr(et, "hour", None)) else int(getattr(et, "hour", 0))
                            end_m = et.minute() if callable(getattr(et, "minute", None)) else int(getattr(et, "minute", 0))

                if not entry_days:
                    tuning_entries = getattr(work_scheduler, "_schedule_entry_tuning", []) or []
                    for entry in tuning_entries:
                        days_avail = getattr(entry, "days_available", {})
                        if hasattr(days_avail, "items"):
                            for d_val, is_avail in days_avail.items():
                                if is_avail:
                                    entry_days.append(int(d_val))
                        st = getattr(entry, "start_time", None)
                        if st is not None and start_h is None:
                            start_h = st.hour() if callable(getattr(st, "hour", None)) else int(getattr(st, "hour", 0))
                            start_m = st.minute() if callable(getattr(st, "minute", None)) else int(getattr(st, "minute", 0))
                            dur = getattr(entry, "duration", 8.0)
                            end_h = int((start_h + dur) % 24)
                            end_m = start_m

            c_name = getattr(career, "__name__", str(career)).lower()
            is_school = any(k in c_name for k in ("school", "grade", "highschool"))
            if is_school and not entry_days:
                entry_days = [1, 2, 3, 4, 5]
                start_h, start_m, end_h, end_m = 8, 0, 15, 0

            is_scheduled_today = (now_day in entry_days) or ((now_day % 7) in entry_days)
            if not is_scheduled_today:
                continue

            if end_h is not None:
                end_total_mins = end_h * 60 + (end_m or 0)
                diff = now_total_mins - end_total_mins
                if 0 <= diff <= 45:
                    return float(diff)
    except Exception as e:
        log_exception("Error in get_minutes_since_sim_shift_ended", e)
    return None


def is_grim_reaper(sim_info) -> bool:
    """Checks if a SimInfo is the Grim Reaper (Костлявая Смерть)."""
    if sim_info is None:
        return False
    try:
        from ai_thought_reader.context import is_grim_reaper_sim
        if is_grim_reaper_sim(sim_info):
            return True
    except Exception:
        pass
    try:
        fn = (getattr(sim_info, "first_name", "") or "").lower().strip()
        ln = (getattr(sim_info, "last_name", "") or "").lower().strip()
        full = f"{fn} {ln}".strip()
        if any(w in full for w in ["костляв", "смерть", "reaper", "grim", "жнец"]):
            return True
        traits = getattr(sim_info, "trait_tracker", None)
        if traits:
            for t in getattr(traits, "equipped_traits", None) or getattr(traits, "personality_traits", None) or traits:
                t_name = getattr(t, "__name__", str(t)).lower()
                if "grimreaper" in t_name or "grim_reaper" in t_name:
                    return True
        if hasattr(sim_info, "get_traits"):
            for t in sim_info.get_traits():
                t_name = getattr(t, "__name__", str(t)).lower()
                if "grimreaper" in t_name or "grim_reaper" in t_name:
                    return True
    except Exception:
        pass
    return False


def get_grim_reaper_instance_on_lot():
    """Returns instanced Grim Reaper on active lot, if present."""
    if services is None or not hasattr(services, "sim_info_manager"):
        return None
    try:
        from ai_thought_reader.context import get_grim_reaper_instance_on_lot as _ctx_reaper
        res = _ctx_reaper()
        if res is not None:
            return res
    except Exception:
        pass
    try:
        sim_mgr = services.sim_info_manager()
        if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
            for inst in sim_mgr.instanced_sims_gen():
                inf = getattr(inst, "sim_info", None)
                if inf and is_grim_reaper(inf):
                    return inst
                for inter in get_sim_interactions_safe(inst):
                    aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                    if any(k in aff_name for k in ["reap", "reaper", "grim", "scythe", "harvest_soul"]):
                        return inst
    except Exception:
        pass
    return None


def get_sim_interactions_safe(sim):
    """Safely retrieves all running and queued interactions from a Sim."""
    if sim is None:
        return []
    if hasattr(sim, "get_all_running_and_queued_interactions"):
        try:
            return list(sim.get_all_running_and_queued_interactions())
        except Exception:
            pass
    if hasattr(sim, "get_running_and_queued_interactions"):
        try:
            return list(sim.get_running_and_queued_interactions())
        except Exception:
            pass
    try:
        from ai_thought_reader.context import get_sim_running_interactions
        return get_sim_running_interactions(sim)
    except Exception:
        pass
    return []


def get_all_active_buff_objects(sim_info, sim_instance=None):
    """Safely extracts all active buff objects across all TS4 versions."""
    buff_list = []
    if sim_info is None and sim_instance is None:
        return buff_list

    if sim_instance is None and sim_info is not None and hasattr(sim_info, "get_sim_instance"):
        try:
            sim_instance = sim_info.get_sim_instance()
        except Exception:
            pass

    # 1. Try importing get_all_sim_buffs from ai_thought_reader.context
    try:
        from ai_thought_reader.context import get_all_sim_buffs
        if sim_info is not None:
            buff_list.extend(get_all_sim_buffs(sim_info, sim_instance))
    except Exception:
        pass

    # 2. Inspect sim_info directly
    if sim_info is not None:
        for b_attr in ("buff_tracker", "_buff_tracker"):
            bt = getattr(sim_info, b_attr, None)
            if bt is not None:
                try:
                    if hasattr(bt, "__iter__"):
                        for b in bt:
                            if b is not None:
                                buff_list.append(b)
                except Exception:
                    pass
                for sub_attr in ("_active_buffs", "active_buffs", "_buffs", "buffs"):
                    if hasattr(bt, sub_attr):
                        try:
                            obj = getattr(bt, sub_attr)
                            if isinstance(obj, dict):
                                buff_list.extend(list(obj.values()))
                            elif hasattr(obj, "__iter__"):
                                buff_list.extend(list(obj))
                        except Exception:
                            pass
        if hasattr(sim_info, "get_buffs"):
            try:
                buff_list.extend(list(sim_info.get_buffs()))
            except Exception:
                pass
        for attr in ("buffs", "_buffs"):
            if hasattr(sim_info, attr):
                try:
                    obj = getattr(sim_info, attr)
                    if isinstance(obj, dict):
                        buff_list.extend(list(obj.values()))
                    elif hasattr(obj, "__iter__"):
                        buff_list.extend(list(obj))
                except Exception:
                    pass
        bc = getattr(sim_info, "buff_component", None) or getattr(sim_info, "BuffComponent", None)
        if bc is not None:
            for attr in ("_active_buffs", "active_buffs", "_buffs", "buffs"):
                if hasattr(bc, attr):
                    try:
                        obj = getattr(bc, attr)
                        if isinstance(obj, dict):
                            buff_list.extend(list(obj.values()))
                        elif hasattr(obj, "__iter__"):
                            buff_list.extend(list(obj))
                    except Exception:
                        pass
        if hasattr(sim_info, "get_all_buffs"):
            try:
                buff_list.extend(list(sim_info.get_all_buffs()))
            except Exception:
                pass

    # 3. Inspect sim_instance directly
    if sim_instance is not None:
        for b_attr in ("buff_tracker", "_buff_tracker"):
            inst_bt = getattr(sim_instance, b_attr, None)
            if inst_bt is not None:
                try:
                    if hasattr(inst_bt, "__iter__"):
                        for b in inst_bt:
                            if b is not None:
                                buff_list.append(b)
                except Exception:
                    pass
                for sub_attr in ("_active_buffs", "active_buffs", "_buffs", "buffs"):
                    if hasattr(inst_bt, sub_attr):
                        try:
                            obj = getattr(inst_bt, sub_attr)
                            if isinstance(obj, dict):
                                buff_list.extend(list(obj.values()))
                            elif hasattr(obj, "__iter__"):
                                buff_list.extend(list(obj))
                        except Exception:
                            pass
        for attr in ("buffs", "_buffs"):
            if hasattr(sim_instance, attr):
                try:
                    obj = getattr(sim_instance, attr)
                    if isinstance(obj, dict):
                        buff_list.extend(list(obj.values()))
                    elif hasattr(obj, "__iter__"):
                        buff_list.extend(list(obj))
                except Exception:
                    pass
        bc = getattr(sim_instance, "buff_component", None) or getattr(sim_instance, "BuffComponent", None)
        if bc is not None:
            for attr in ("_active_buffs", "active_buffs", "_buffs", "buffs"):
                if hasattr(bc, attr):
                    try:
                        obj = getattr(bc, attr)
                        if isinstance(obj, dict):
                            buff_list.extend(list(obj.values()))
                        elif hasattr(obj, "__iter__"):
                            buff_list.extend(list(obj))
                    except Exception:
                        pass
        if hasattr(sim_instance, "get_buffs"):
            try:
                buff_list.extend(list(sim_instance.get_buffs()))
            except Exception:
                pass
        if hasattr(sim_instance, "get_all_buffs"):
            try:
                buff_list.extend(list(sim_instance.get_all_buffs()))
            except Exception:
                pass

    seen = set()
    unique = []
    for b in buff_list:
        if b is not None and id(b) not in seen:
            seen.add(id(b))
            unique.append(b)
    return unique


def get_sim_buff_names_safe(sim_info, sim_instance=None) -> List[str]:
    """Safely retrieves all active buff names on a Sim across all TS4 versions."""
    raw_buffs = get_all_active_buff_objects(sim_info, sim_instance)
    names = []
    for buff in raw_buffs:
        try:
            b_type = getattr(buff, "buff_type", buff)
            t_name = getattr(b_type, "__name__", "") or ""
            cls_name = getattr(getattr(buff, "__class__", type(buff)), "__name__", "") or ""
            guid = str(getattr(b_type, "guid64", "") or getattr(buff, "guid64", "") or "")
            b_str = str(buff)
            t_str = str(b_type)
            loc_name = ""
            for name_attr in ("buff_name", "name", "_name"):
                v = getattr(b_type, name_attr, None) or getattr(buff, name_attr, None)
                if v and isinstance(v, str):
                    loc_name = v
                    break
            combined = f"{t_name} {cls_name} {guid} {b_str} {t_str} {loc_name}".lower()
            names.append(combined)
        except Exception:
            pass
    return names


def is_sim_available(sim_instance) -> bool:
    """Checks if a Sim is awake, present on lot, and available to speak."""
    if sim_instance is None:
        return False
    try:
        sim_info = getattr(sim_instance, "sim_info", None)
        if sim_info is None:
            return False

        # Must not be a pet
        if getattr(sim_info, "is_pet", False):
            return False

        # Grim Reaper is always available if instanced on lot
        if is_grim_reaper(sim_info):
            return True

        # Must be on active lot or adjacent arrival/outdoor zone (sidewalk / mailbox)
        if not is_sim_on_or_near_active_lot(sim_instance):
            return False

        # Must not be at work / rabbit hole
        if is_sim_currently_at_work(sim_info):
            return False

        # Must not be dead or dying
        if getattr(sim_info, "is_dead", False) or getattr(sim_instance, "is_dying", False):
            return False

        # Must not be sleeping or passed out
        act_lower = ""
        try:
            from ai_thought_reader.context import get_current_activity
            act_lower = (get_current_activity(sim_info) or "").lower()
        except Exception:
            pass

        if any(w in act_lower for w in ["спит", "дремлет", "сон", "в постели (спит)", "sleeping", "nap"]):
            return False

        # Must not be in shower / bath / toilet
        if any(w in act_lower for w in ["душ", "ванн", "туалет", "shower", "bath", "toilet"]):
            return False

        return True
    except Exception:
        return False


def is_sim_moving(sim_instance) -> bool:
    """Checks if a Sim is currently walking, running, or routing across the lot."""
    if sim_instance is None:
        return False
    try:
        if getattr(sim_instance, "is_routing", False):
            return True
        rc = getattr(sim_instance, "routing_component", None)
        if rc is not None:
            if getattr(rc, "is_moving", False):
                return True
            if getattr(rc, "current_path", None) is not None:
                return True
    except Exception:
        pass
    return False


def are_sims_co_present(sim_a, sim_b) -> Tuple[bool, str, float]:
    """
    Determines if two Sims share physical space using the mod's proven room and distance engine.
    Returns: (is_co_present, space_description, distance_meters)
    """
    if sim_a is None or sim_b is None:
        return False, "", 999.0

    try:
        pos_a = getattr(sim_a, "position", None)
        pos_b = getattr(sim_b, "position", None)
        if pos_a is None or pos_b is None:
            return False, "", 999.0

        dist = float((pos_a - pos_b).magnitude())

        from ai_thought_reader.context import get_sim_room_and_outdoor
        room_a, outside_a = get_sim_room_and_outdoor(sim_a)
        room_b, outside_b = get_sim_room_and_outdoor(sim_b)

        # 1. Both indoors in the SAME room
        if not outside_a and not outside_b:
            if room_a != 0 and room_a == room_b:
                return True, "В одной комнате", dist
            # Flexible adjoining / open-concept living space on the same floor
            same_floor = abs(pos_a.y - pos_b.y) < 1.8
            if same_floor and dist <= 9.5:
                return True, "В одном помещении (в пределах зоны видимости)", dist
            return False, f"В разных комнатах дома (room_a={room_a}, room_b={room_b}, d={dist:.1f}m)", dist

        # 2. Both outdoors
        if outside_a and outside_b:
            if dist <= MAX_OUTDOOR_PROXIMITY_METERS:
                return True, "На улице во дворе рядом", dist
            return False, "На улице в отдалении", dist

        # 3. One inside, one outside
        same_floor = abs(pos_a.y - pos_b.y) < 1.8
        if same_floor and dist <= 3.5:
            return True, "На пороге дома (у входной двери)", dist
        return False, "Один в доме, другой на улице", dist

    except Exception as e:
        log_exception("Error in are_sims_co_present", e)
        return False, "", 999.0


def find_nearby_joinable_sims(sim_a, sim_b, max_count: int = 6) -> List[Any]:
    """
    Finds up to max_count additional available Sims on the lot who are co-present with sim_a or sim_b
    (sharing the same room indoors, or within 8.5m outdoors).
    Total participants in the scene will not exceed 2 + max_count (up to 8 Sims total).
    Returns list of sim_info objects for the closest eligible nearby Sims.
    """
    if services is None:
        return []

    inst_a = getattr(sim_a, "get_sim_instance", lambda: sim_a)() if hasattr(sim_a, "get_sim_instance") else sim_a
    inst_b = getattr(sim_b, "get_sim_instance", lambda: sim_b)() if hasattr(sim_b, "get_sim_instance") else sim_b

    info_a = getattr(sim_a, "sim_info", sim_a)
    info_b = getattr(sim_b, "sim_info", sim_b)

    excluded_ids = set()
    if info_a is not None:
        excluded_ids.add(getattr(info_a, "sim_id", 0))
    if info_b is not None:
        excluded_ids.add(getattr(info_b, "sim_id", 0))

    candidates = []
    try:
        sim_mgr = services.sim_info_manager()
        if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
            for inst in sim_mgr.instanced_sims_gen():
                if inst is None:
                    continue
                inf = getattr(inst, "sim_info", None)
                if inf is None:
                    continue
                s_id = getattr(inf, "sim_id", 0)
                if s_id in excluded_ids:
                    continue
                if not is_sim_available(inst):
                    continue

                co_a, desc_a, dist_a = (False, "", 999.0)
                co_b, desc_b, dist_b = (False, "", 999.0)
                if inst_a is not None:
                    co_a, desc_a, dist_a = are_sims_co_present(inst_a, inst)
                if inst_b is not None:
                    co_b, desc_b, dist_b = are_sims_co_present(inst_b, inst)

                if co_a or co_b:
                    best_dist = min(dist_a, dist_b)
                    candidates.append((best_dist, inf))
    except Exception as e:
        log_exception("Error in find_nearby_joinable_sims", e)

    candidates.sort(key=lambda item: item[0])
    return [item[1] for item in candidates[:max_count]]


def is_sim_eating(sim_inst, sim_info, act_str: str) -> bool:
    """
    Checks if a Sim is genuinely eating / consuming food.
    Checks active TS4 interaction affordances and strict regex word boundaries.
    Prevents false substring collisions like 'seating_sit' (contains 'eat') or 'death' (contains 'eat').
    """
    act_lower = (act_str or "").lower()
    # Explicitly reject death, dying, mourning, grief, crying
    if any(k in act_lower for k in ("смерт", "погиб", "умира", "оплакива", "траур", "скорб", "плачет", "mourn", "grief", "die")):
        return False

    if sim_inst is not None:
        try:
            for inter in get_sim_interactions_safe(sim_inst):
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                # Skip seating postures, chairs, beds, broadcasters, reactions, death, grief
                if any(skip in aff_name or skip in i_name for skip in ("seating", "seat_", "sit_", "posture", "broadcaster", "reaction", "chair", "sofa", "bed", "death", "mourn", "cry", "weep")):
                    continue
                # Check for authentic eating affordances
                if any(k in aff_name for k in ("_eat", "eat_", "eat_active", "consume", "dine", "meal", "food_eat")) and not any(k in aff_name for k in ("cook", "make", "prepare", "craft", "cheat", "weather", "order", "death", "mourn")):
                    return True
        except Exception:
            pass

    eating_verbs = [
        "кушает", "трапезничает", "завтракает", "обедает",
        "ужинает", "перекусывает", "поедает", "ест еду", "ест блюдо", "ест пищу", "принимает пищу"
    ]
    if any(verb in act_lower for verb in eating_verbs):
        return True

    import re
    if re.search(r'\b(ест|eating|consumes)\b', act_lower):
        return True

    return False


def is_sim_watching_tv(sim_inst, sim_info, act_str: str) -> bool:
    """Checks if Sim is watching TV, avoiding false substring collisions with 'тв' in 'чувство', 'руководство' or 'notvisible'."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_")):
                    continue
                if any(k in aff_name for k in ("tv_watch", "watch_tv", "television", "watch_movie")):
                    return True
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    if any(k in act_lower for k in ("телевизор", "сериал", "фильм", "смотрим тв", "просмотр тв", "смотрит тв")):
        return True
    import re
    if re.search(r'\b(тв|tv|watch_tv)\b', act_lower):
        return True
    return False


def is_sim_using_pc_or_laptop(sim_inst, sim_info, act_str: str) -> bool:
    """
    Accurately determines if a Sim is currently using or playing on a desktop PC or laptop.
    Checks running interaction affordances, interaction targets (is_computer_object), and activity descriptions.
    """
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            from ai_social_pc.computer_interaction import is_computer_object
            for inter in sim_inst.get_all_running_and_queued_interactions():
                tgt = getattr(inter, "target", None)
                if tgt is not None and is_computer_object(tgt):
                    return True
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_")):
                    continue
                if any(k in aff_name for k in (
                    "computer", "laptop", "videogame", "video_game", "gaming", "playgame",
                    "simsforever", "blicblock", "roadrival", "incrediblesports", "mysims", "bustinout", "play_game"
                )):
                    return True
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    pc_keywords = (
        "компьютер", "пк", "ноутбук", "ноут", "laptop", "desktop", "комп",
        "видеоигр", "видеоигры", "гейминг", "геймер", "стрим",
        "the sims forever", "sims forever", "road rival", "blicblock",
        "mysims", "bustin' out", "bustinout", "incrediblesports", "ролевую игру"
    )
    if any(k in act_lower for k in pc_keywords):
        return True

    if "играет в " in act_lower and not any(skip in act_lower for skip in ("скрипк", "гитар", "рояль", "пианино", "кукл", "игрушк", "шахмат", "прятки", "догонялки")):
        return True

    import re
    if re.search(r'\b(пк|pc|комп|ноут|laptop)\b', act_lower):
        return True

    return False


def is_sim_gardening(sim_inst, sim_info, act_str: str) -> Tuple[bool, str]:
    """
    Determines if a Sim is actively gardening (tending, watering, weeding, harvesting, planting).
    Returns (is_gardening, action_detail).
    """
    plant_suffix = ""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_")):
                    continue
                if any(k in aff_name for k in ("harvest", "weed", "water", "tend", "plant", "fertilize", "spray", "prune", "graft", "splicing", "garden")):
                    tgt = getattr(inter, "target", None)
                    if tgt is not None:
                        try:
                            from ai_thought_reader.context import extract_plant_name, get_plant_growth_stage
                            pn = extract_plant_name(tgt, inter)
                            st = get_plant_growth_stage(tgt, inter=inter, is_en=False)
                            has_pn = bool(pn and pn not in ("Растение", "Культура", "Гигантская культура"))
                            if has_pn and st:
                                plant_suffix = f": {pn}, {st}"
                            elif has_pn:
                                plant_suffix = f": {pn}"
                            elif st:
                                plant_suffix = f": {st}"
                        except Exception:
                            pass

                    base_act = "ухаживает за растениями"
                    if "harvest" in aff_name:
                        base_act = "собирает свежий урожай"
                    elif "weed" in aff_name:
                        base_act = "пропалывает сорняки"
                    elif "water" in aff_name:
                        base_act = "поливает грядки и растения"
                    elif "plant" in aff_name:
                        base_act = "высаживает семена"
                    elif "fertilize" in aff_name:
                        base_act = "удобряет почву"
                    elif "spray" in aff_name:
                        base_act = "опрыскивает растения от жуков"
                    elif "prune" in aff_name:
                        base_act = "подрезает ветви растений"
                    return True, f"{base_act}{plant_suffix}"
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    if any(skip in act_lower for skip in ("пьет вод", "посуд", "чай", "кофе", "душ", "ванн")):
        return False, ""

    act_suffix = ""
    if "(" in (act_str or "") and ")" in (act_str or ""):
        s_idx = act_str.rfind("(") + 1
        e_idx = act_str.rfind(")")
        if 0 <= s_idx < e_idx:
            inner = act_str[s_idx:e_idx].strip()
            if inner:
                act_suffix = f": {inner}"

    if any(k in act_lower for k in ("поливает растени", "поливает грядк", "поливает цвет")):
        return True, f"поливает растения{act_suffix}"
    if any(k in act_lower for k in ("собирает урожай", "сбор урожая")):
        return True, f"собирает урожай{act_suffix}"
    if any(k in act_lower for k in ("пропалывает", "сорняк")):
        return True, f"пропалывает сорняки{act_suffix}"
    if any(k in act_lower for k in ("сажает семена", "сажает растени", "посадка семян")):
        return True, f"сажает растения{act_suffix}"
    if any(k in act_lower for k in ("удобряет", "подкормка растений")):
        return True, f"удобряет почву{act_suffix}"
    if any(k in act_lower for k in ("ухаживает за растениями", "садовод", "копается в саду", "работает в саду")):
        return True, f"ухаживает за растениями{act_suffix}"

    return False, ""


PAINTING_GENRE_CATALOG = [
    # Emotional paintings (check first)
    (("flirty", "кокетлив"), "кокетливая картина"),
    (("angry", "сердит", "гневн"), "сердитая картина"),
    (("sad", "грустн", "печальн"), "грустная картина"),
    (("playful", "игрив"), "игривая картина"),
    (("confident", "уверенн"), "уверенная картина"),
    (("focused", "внимательн", "математическ", "diagram"), "внимательная картина"),

    # Specific genres and styles
    (("popart", "pop_art", "поп-арт", "попарт"), "поп-арт"),
    (("surrealism", "surreal", "сюрреализм"), "сюрреализм"),
    (("abstract", "абстракц"), "абстракция"),
    (("realism", "realist", "реализм"), "реализм"),
    (("impressionism", "impressionist", "импрессионизм"), "импрессионизм"),
    (("landscape", "пейзаж"), "пейзаж"),
    (("portrait", "портрет"), "портрет"),
    (("stilllife", "still_life", "натюрморт"), "натюрморт"),
    (("figure", "figurative", "фигуративн"), "фигуративная живопись"),
    (("reference", "paintbyreference", "paint_by_reference", "по образцу"), "рисунок по образцу"),
    (("mural", "streetart", "graffiti", "роспись", "граффити"), "настенная роспись"),
    (("classic", "классик"), "классика"),
]


def extract_painting_genre(inter=None, tgt=None, act_str: str = "", sim_inst=None) -> str:
    """
    Safely resolves painting style / genre from affordance, recipe, interaction name,
    crafting process, or activity string.
    Returns clean genre string like 'кокетливая картина', 'классика', 'пейзаж', etc. or '' if unknown.
    """
    candidates = []

    # 1. From recipe / crafting process on inter, tgt, or any running interaction
    objects_to_probe = [inter, tgt]
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for other_i in sim_inst.get_all_running_and_queued_interactions():
                if other_i not in objects_to_probe:
                    objects_to_probe.append(other_i)
                o_tgt = getattr(other_i, "target", None)
                if o_tgt is not None and o_tgt not in objects_to_probe:
                    objects_to_probe.append(o_tgt)
        except Exception:
            pass

    for obj in objects_to_probe:
        if obj is None:
            continue
        proc = None
        if hasattr(obj, "get_crafting_process") and callable(getattr(obj, "get_crafting_process")):
            try:
                proc = obj.get_crafting_process()
            except Exception:
                pass
        if proc is None and hasattr(obj, "crafting_process"):
            try:
                proc = getattr(obj, "crafting_process", None)
            except Exception:
                pass
        if proc is not None:
            recipe = getattr(proc, "recipe", None)
            if recipe is not None:
                try:
                    from sims4.localization import LocalizationHelperTuning
                    if LocalizationHelperTuning is not None:
                        if hasattr(recipe, "get_display_name"):
                            d = recipe.get_display_name()
                            if d:
                                raw = LocalizationHelperTuning.get_raw_text(d)
                                if raw:
                                    candidates.append(str(raw))
                        if hasattr(recipe, "_display_name"):
                            d = getattr(recipe, "_display_name")
                            if d:
                                raw = LocalizationHelperTuning.get_raw_text(d)
                                if raw:
                                    candidates.append(str(raw))
                except Exception:
                    pass
                rec_name = getattr(recipe, "__name__", "") or str(recipe)
                if rec_name:
                    candidates.append(rec_name)

    # 2. From interaction UI name and affordance
    for obj in objects_to_probe:
        if obj is None:
            continue
        try:
            from ai_thought_reader.context import get_interaction_ui_name
            ui_name = get_interaction_ui_name(obj)
            if ui_name:
                candidates.append(ui_name)
        except Exception:
            pass

        aff = getattr(obj, "affordance", None)
        if aff is not None:
            aff_name = getattr(aff, "__name__", "") or str(aff)
            if aff_name:
                candidates.append(aff_name)
        o_name = getattr(obj, "__name__", "") or str(obj)
        if o_name:
            candidates.append(o_name)

    # 3. From extract_crafting_item_name
    try:
        from ai_thought_reader.context import extract_crafting_item_name
        c_item = extract_crafting_item_name(inter, tgt)
        if c_item:
            candidates.append(c_item)
    except Exception:
        pass

    # 4. From act_str (e.g. 'Пишет картину (Кокетливая картина)')
    if act_str:
        candidates.append(act_str)
        if "(" in act_str and ")" in act_str:
            s_idx = act_str.find("(") + 1
            e_idx = act_str.rfind(")")
            if 0 <= s_idx < e_idx:
                inner = act_str[s_idx:e_idx].strip()
                if inner and not any(bad in inner.lower() for bad in ("пишет картину", "мольберт")):
                    candidates.insert(0, inner)

    # Match all candidates against catalog
    for text in candidates:
        if not text:
            continue
        text_lower = text.lower()
        for keys, genre_label in PAINTING_GENRE_CATALOG:
            if any(k in text_lower for k in keys):
                return genre_label

    return ""


def is_sim_painting(sim_inst, sim_info, act_str: str) -> Tuple[bool, str]:
    """
    Determines if a Sim is actively painting on an easel, canvas, or sketchpad.
    Returns (is_painting, painting_detail).
    Where painting_detail is the genre (e.g. 'кокетливая картина', 'классика', 'пейзаж', 'эскиз на планшете')
    or '' if generic easel painting.
    """
    is_painting = False
    is_sketchpad = False
    found_inter = None
    found_tgt = None

    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_", "view_", "admire_", "scrap_", "sell_")):
                    continue
                if any(k in aff_name for k in ("easel_craft", "paint_canvas", "easel_paint", "sketchpad_draw", "paint_by_reference", "drafting_table", "canvas_paint", "paint_canvas_staged", "easel_staging")):
                    is_painting = True
                    found_inter = inter
                    found_tgt = getattr(inter, "target", None)
                    t_str = str(found_tgt).lower() if found_tgt else ""
                    if "sketchpad" in aff_name or "sketchpad" in t_str:
                        is_sketchpad = True
                    break
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    if any(skip in act_lower for skip in ("смотрит на картин", "любуется картин", "оценивает картин")):
        return False, ""

    if not is_painting:
        if any(k in act_lower for k in ("рисует на мольберте", "пишет картину", "рисует картину", "живопись на холсте", "пишет полотно", "мольберт")):
            is_painting = True
        elif any(k in act_lower for k in ("рисует эскиз", "рисует на планшете", "делает набросок", "sketchpad")):
            is_painting = True
            is_sketchpad = True

    if not is_painting:
        return False, ""

    if is_sketchpad:
        return True, "эскиз на планшете"

    genre = extract_painting_genre(found_inter, found_tgt, act_str, sim_inst=sim_inst)
    return True, genre


def is_sim_playing_instrument(sim_inst, sim_info, act_str: str) -> Tuple[bool, str]:
    """
    Determines if a Sim is actively playing a musical instrument (piano, guitar, violin, organ).
    Returns (is_playing, instrument_name).
    """
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_", "listen_", "dance_")):
                    continue
                if any(k in aff_name for k in ("piano", "guitar", "violin", "pipeorgan", "organ_play", "instrument")):
                    if "piano" in aff_name:
                        return True, "пианино"
                    elif "guitar" in aff_name:
                        return True, "гитаре"
                    elif "violin" in aff_name:
                        return True, "скрипке"
                    elif "organ" in aff_name:
                        return True, "органе"
                    return True, "музыкальном инструменте"
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    if any(skip in act_lower for skip in ("слушает музыку", "слушает радио", "танцует под музыку", "стереосистема")):
        return False, ""

    if any(k in act_lower for k in ("играет на пианино", "играет на рояле", "за фортепиано")):
        return True, "пианино"
    if any(k in act_lower for k in ("играет на гитаре", "тренькает на гитаре", "аккорды на гитаре")):
        return True, "гитаре"
    if any(k in act_lower for k in ("играет на скрипке", "скрипка", "репетирует на скрипке")):
        return True, "скрипке"
    if any(k in act_lower for k in ("играет на органе",)):
        return True, "органе"
    if "репетирует мелодию" in act_lower or "сочиняет песню" in act_lower:
        return True, "музыкальном инструменте"

    return False, ""


def is_sim_working_out(sim_inst, sim_info, act_str: str) -> Tuple[bool, str]:
    """
    Determines if a Sim is actively working out (treadmill, weight machine, pushups, situps, yoga, punching bag).
    Returns (is_working_out, workout_detail).
    """
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("broadcaster", "reaction_", "notvisible", "seating_", "posture_", "watch_", "mentor_")):
                    continue
                if any(k in aff_name for k in ("treadmill", "workoutmachine", "pushups", "situps", "punchingbag", "fitness_workout", "yoga", "stretching", "jumping_jacks")):
                    if "treadmill" in aff_name:
                        return True, "бегает на беговой дорожке"
                    elif "punchingbag" in aff_name:
                        return True, "отрабатывает удары на боксерской груше"
                    elif "workoutmachine" in aff_name:
                        return True, "занимается на силовом тренажере"
                    elif "pushups" in aff_name:
                        return True, "отжимается от пола"
                    elif "situps" in aff_name:
                        return True, "качает пресс на полу"
                    elif "yoga" in aff_name:
                        return True, "занимается йогой и растяжкой"
                    return True, "активно тренируется и делает упражнения"
        except Exception:
            pass

    act_lower = (act_str or "").lower()
    if any(skip in act_lower for skip in ("смотрит тренировк", "тренирует сима")):
        return False, ""

    if any(k in act_lower for k in ("бегает на дорожке", "беговой дорожк")):
        return True, "бегает на беговой дорожке"
    if any(k in act_lower for k in ("качает пресс",)):
        return True, "качает пресс"
    if any(k in act_lower for k in ("отжимается",)):
        return True, "отжимается от пола"
    if any(k in act_lower for k in ("силовой тренажер", "тренируется на тренажере")):
        return True, "тренируется на тренажере"
    if any(k in act_lower for k in ("боксерск", "бьет грушу", "колотит грушу")):
        return True, "отрабатывает удары на груше"
    if any(k in act_lower for k in ("занимается йогой", "йога", "растяжк")):
        return True, "занимается йогой"
    if any(k in act_lower for k in ("тренируется", "делает упражнения", "фитнес")):
        return True, "делает физические упражнения"

    return False, ""


def are_sims_playing_table_game(sim_a, sim_b, act_a: str, act_b: str) -> Tuple[bool, str]:
    """
    Determines if two Sims are playing a tabletop game together (chess, cards, board game).
    Returns (is_playing, game_name).
    """
    game_hint = ""
    for s in (sim_a, sim_b):
        if s is not None and hasattr(s, "get_all_running_and_queued_interactions"):
            try:
                for inter in s.get_all_running_and_queued_interactions():
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                    if any(k in aff_name for k in ("chess", "cardtable", "boardgame", "dontwakellama", "sabacc")):
                        if "chess" in aff_name:
                            game_hint = "шахматы"
                        elif "card" in aff_name:
                            game_hint = "карты"
                        elif "llama" in aff_name:
                            game_hint = "«Не разбуди ламу»"
                        else:
                            game_hint = "настольную игру"
                        break
            except Exception:
                pass
        if game_hint:
            break

    comb = f"{(act_a or '').lower()} {(act_b or '').lower()}"
    is_game = False
    if "шахмат" in comb:
        game_hint = "шахматы"
        is_game = True
    elif "карт" in comb and any(k in comb for k in ("играет в карт", "карточный стол", "партия в карт")):
        game_hint = "карты"
        is_game = True
    elif any(k in comb for k in ("настольн", "настольную игру", "не разбуди ламу")):
        game_hint = game_hint or "настольную игру"
        is_game = True

    if game_hint and is_game:
        return True, game_hint

    return False, ""


def detect_pet_care_in_scene(sim_a, sim_b, act_a: str, act_b: str):
    """
    Detects if one human Sim is interacting with / caring for a household pet (cat/dog/horse)
    while the other human Sim is present in the room.
    Returns (carer_info, other_info, pet_name, care_detail) or None.
    """
    pet_aff_keywords = (
        "laser", "laserpointer", "featherwand", "catwand", "playfetch", "frisbee",
        "catnip", "bellyrub", "pethug", "petcuddle", "walkdog", "dogwalk", "givetreat",
        "brushpet", "groompet", "bathpet", "bathedog", "trainpet", "petplay", "playwithpet",
        "playwithcat", "playwithdog", "pet_bath", "pet_brush", "pet_train", "pet_play",
        "pet_social", "pet_groom", "pet_hug", "pet_petting", "pet_talk", "pet_feed",
        "petbowl", "litterbox", "litter", "fleatreatment", "obstacle", "agility",
        "scratchingpost", "clean_poop", "poop", "rodent", "hamster", "smallpet",
        "horse_clean", "horse_brush", "horse_feed", "horse_hug", "horse_train",
        "mini_goat", "mini_sheep"
    )

    pet_keywords = (
        ("лазер", "играет с питомцем лазерной указкой"),
        ("указк", "играет с питомцем лазерной указкой"),
        ("дразнилк", "играет с кошкой дразнилкой"),
        ("дразнит", "играет и дразнит кошку"),
        ("кошачьей мят", "угощает кошку кошачьей мятой"),
        ("апорт", "играет с собакой в апорт"),
        ("мячик", "играет с собакой в мячик"),
        ("фрисби", "играет с собакой в фрисби"),
        ("чешет пузико", "чешет пузико питомцу"),
        ("пузико", "чешет пузико питомцу"),
        ("купает собак", "купает собаку в ванне"),
        ("купает питомц", "купает питомца в ванне"),
        ("расчесывает", "расчесывает шерсть питомца"),
        ("дрессирует", "дрессирует питомца и учит командам"),
        ("полос", "тренирует собаку на полосе препятствий"),
        ("препятств", "тренирует собаку на полосе препятствий"),
        ("аджилити", "тренирует собаку на полосе препятствий"),
        ("играет с кошк", "играет с кошкой"),
        ("играет с собак", "играет с собакой"),
        ("играет с питомц", "играет с питомцем"),
        ("гладит собак", "гладит собаку"),
        ("гладит кошк", "гладит кошку"),
        ("гладит питомц", "гладит питомца"),
        ("ласкает питомц", "ласкает питомца"),
        ("обнимает", "обнимает питомца"),
        ("прижимает", "прижимает и ласкает питомца"),
        ("дает лакомство", "угощает питомца лакомством"),
        ("угощает", "угощает питомца лакомством"),
        ("насыпает корм", "наполняет миску кормом для питомца"),
        ("миск", "наполняет миску кормом для питомца"),
        ("кормит собак", "кормит собаку"),
        ("кормит кошк", "кормит кошку"),
        ("кормит питомц", "кормит питомца"),
        ("лоток", "чистит кошачий лоток"),
        ("когтеточк", "приучает кошку к когтеточке"),
        ("кучк", "убирает за собакой"),
        ("гуляет с собак", "выгуливает собаку"),
        ("выгуливает", "выгуливает собаку"),
        ("поводок", "выгуливает собаку на поводке"),
        ("блох", "обрабатывает питомца от блох"),
        ("отчитывает", "воспитывает питомца"),
        ("хвалит", "хвалит питомца"),
        ("хомяк", "ухаживает за хомяком"),
        ("грызун", "ухаживает за мелким питомцем"),
        ("копыт", "чистит копыта лошади"),
        ("грив", "расчесывает гриву лошади"),
        ("лошад", "ухаживает за лошадью"),
        ("козочк", "ухаживает за мини-козочкой"),
        ("овечк", "ухаживает за мини-овечкой"),
    )

    for carer_sim, other_sim, c_act, o_act in [(sim_a, sim_b, act_a, act_b), (sim_b, sim_a, act_b, act_a)]:
        if carer_sim is None or other_sim is None:
            continue
        carer_info = getattr(carer_sim, "sim_info", None)
        other_info = getattr(other_sim, "sim_info", None)
        if carer_info is None or other_info is None:
            continue
        if getattr(carer_info, "is_pet", False) or getattr(other_info, "is_pet", False):
            continue

        c_act_lower = (c_act or "").lower()
        if any(w in c_act_lower for w in ["смотрит, как", "смотрит на", "наблюдает за", "наблюдает, как", "следит за"]):
            continue

        care_detail = ""
        pet_name = "питомец"

        # Check interactions on carer_sim
        if hasattr(carer_sim, "get_all_running_and_queued_interactions"):
            try:
                for inter in carer_sim.get_all_running_and_queued_interactions():
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()

                    # Skip spectator / watching affordances
                    if any(skip in aff_name for skip in ("watch", "cheer", "observe", "spectate", "look_at")):
                        continue

                    tgt = getattr(inter, "target", None)
                    tgt_info = getattr(tgt, "sim_info", None) if tgt else None
                    if tgt_info is None and hasattr(tgt, "is_pet"):
                        tgt_info = tgt
                    is_pet_target = bool(tgt_info and (getattr(tgt_info, "is_pet", False) or getattr(getattr(tgt_info, "species", None), "name", "") in ("CAT", "DOG", "HORSE")))

                    if any(k in aff_name for k in pet_aff_keywords) or is_pet_target:
                        if tgt_info and getattr(tgt_info, "first_name", None):
                            pet_name = getattr(tgt_info, "first_name", "питомец")

                        if "laser" in aff_name:
                            care_detail = "играет с питомцем лазерной указкой"
                        elif "feather" in aff_name or "wand" in aff_name:
                            care_detail = "играет с кошкой дразнилкой с перышками"
                        elif "fetch" in aff_name or "frisbee" in aff_name or "ball" in aff_name:
                            care_detail = "играет с собакой в апорт / фрисби"
                        elif "bath" in aff_name:
                            care_detail = "купает питомца в ванне"
                        elif "brush" in aff_name or "groom" in aff_name:
                            care_detail = "расчесывает шерсть питомца"
                        elif "train" in aff_name or "trick" in aff_name:
                            care_detail = "дрессирует питомца и учит командам"
                        elif "obstacle" in aff_name or "agility" in aff_name:
                            care_detail = "тренирует собаку на полосе препятствий"
                        elif "litter" in aff_name:
                            care_detail = "чистит кошачий лоток"
                        elif "bowl" in aff_name or "feedbowl" in aff_name:
                            care_detail = "наполняет миску кормом для питомца"
                        elif "poop" in aff_name:
                            care_detail = "убирает за собакой"
                        elif "scratch" in aff_name:
                            care_detail = "приучает кошку к когтеточке"
                        elif "flea" in aff_name:
                            care_detail = "обрабатывает питомца от блох"
                        elif "rodent" in aff_name or "hamster" in aff_name:
                            care_detail = "ухаживает за хомяком / грызуном"
                        elif "hoof" in aff_name or "hooves" in aff_name:
                            care_detail = "чистит копыта лошади"
                        elif "horse" in aff_name:
                            care_detail = "ухаживает за лошадью"
                        elif "goat" in aff_name or "sheep" in aff_name:
                            care_detail = "ухаживает за мини-козочкой / овечкой"
                        elif "play" in aff_name:
                            care_detail = "играет с питомцем"
                        elif "treat" in aff_name or "feed" in aff_name or "eat" in aff_name:
                            care_detail = "угощает питомца лакомством"
                        elif "hug" in aff_name or "cuddle" in aff_name:
                            care_detail = "обнимает питомца"
                        elif "belly" in aff_name:
                            care_detail = "чешет пузико питомцу"
                        elif "walk" in aff_name or "leash" in aff_name:
                            care_detail = "выгуливает собаку"
                        else:
                            care_detail = "гладит и ласкает питомца"
                        break
            except Exception:
                pass

        if not care_detail:
            for kw, desc in pet_keywords:
                if kw in c_act_lower:
                    care_detail = desc
                    break

        if care_detail:
            # Extract pet name from parentheses in c_act e.g. "Дразнит кошку (Мурка)..."
            if pet_name == "питомец" and "(" in (c_act or "") and ")" in (c_act or ""):
                import re
                m = re.search(r'\(([^)]+)\)', c_act)
                if m:
                    cand = m.group(1).strip()
                    if cand and not any(skip in cand.lower() for skip in ["сидя", "стоя", "лежа", "полностью", "форма"]):
                        pet_name = cand

            # If still generic, try finding a pet in the active household
            if pet_name == "питомец":
                try:
                    import services
                    hh = services.active_household() if hasattr(services, "active_household") else None
                    if hh is not None and hasattr(hh, "sim_infos"):
                        for s_info in hh.sim_infos:
                            if getattr(s_info, "is_pet", False) or getattr(getattr(s_info, "species", None), "name", "") in ("CAT", "DOG", "HORSE"):
                                p_fn = getattr(s_info, "first_name", "")
                                if p_fn:
                                    pet_name = p_fn
                                    break
                except Exception:
                    pass

            return carer_info, other_info, pet_name, care_detail

    return None


# =========================================================================
# UNIVERSAL BROKEN OBJECT & REPAIR ENGINE INTEGRATION
# =========================================================================

REPAIR_ACTIVITY_ACCUSATIVE_MAP = [
    ("плит", "кухонную плиту"),
    ("гриль", "гриль"),
    ("холодильник", "холодильник"),
    ("раковин", "раковину"),
    ("кран", "водопроводный кран"),
    ("унитаз", "унитаз"),
    ("душ", "душевую кабину"),
    ("ванн", "ванну"),
    ("компьютер", "компьютер"),
    ("телевизор", "телевизор"),
    ("стиральн", "стиральную машину"),
    ("посудомоечн", "посудомоечную машину"),
    ("микроволнов", "микроволновку"),
    ("кофеварк", "кофеварку"),
    ("чайник", "чайник"),
    ("стерео", "стереосистему"),
    ("робот", "робота"),
    ("сантехник", "сантехнику"),
]


def is_object_broken(obj) -> bool:
    """
    Checks if a TS4 GameObject is broken, sparking, damaged, or malfunctioning.
    Uses TS4 engine's StateComponent.is_object_usable() as primary ground truth.
    If is_object_usable() is True, the object is working and usable (never broken).
    Falls back to strict regex/state value inspection for CC without BROKEN_STATE_SET tuning.
    """
    if obj is None:
        return False
    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
        return False

    def _state_str(val) -> str:
        if val is None:
            return ""
        return (getattr(val, "__name__", "") or str(val) or "").lower()

    sc = getattr(obj, "state_component", None)
    if sc is not None:
        # 1. Primary: TS4 Native Engine Method
        # StateComponent.is_object_usable() returns False IF AND ONLY IF a state in BROKEN_STATE_SET is active.
        if hasattr(sc, "is_object_usable") and callable(sc.is_object_usable):
            try:
                is_usable = sc.is_object_usable()
                if not is_usable:
                    log(f"[BROKEN OBJ DETECTED] {obj} is unusable (broken state active in BROKEN_STATE_SET)")
                    return True
                # If is_object_usable() is True, object is verified working by Maxis engine!
                return False
            except Exception as e:
                log_exception("Error in sc.is_object_usable()", e)

        # 2. Fallback for custom objects without is_object_usable
        try:
            states_dict = getattr(sc, "_states", None)
            if states_dict and hasattr(states_dict, "items"):
                for s_type, s_val in states_dict.items():
                    t_name = _state_str(s_type)
                    v_name = _state_str(s_val)

                    # Exclude upgrade tuning states (e.g. Upgrade_Generic_LockBrokenness_NotStarted)
                    if any(u in t_name or u in v_name for u in ("upgrade", "lockbroken", "lock_broken", "notstarted", "not_started")):
                        continue

                    # Skip safe/unbroken/clean states
                    if any(safe in v_name for safe in ("unbroken", "notbroken", "not_broken", "neverbreaks", "fix", "repaired", "repairing", "clean", "unclogged", "not_clogged")):
                        continue

                    # Strict check: value must specifically indicate broken/clogged/malfunction/spark
                    import re
                    if re.search(r'(^|_)broken($|_)|(^|_)broke($|_)|clogged|malfunction|sparking|burned', v_name):
                        log(f"[BROKEN OBJ DETECTED] {obj} matched fallback state: type={t_name}, val={v_name}")
                        return True
        except Exception:
            pass

    return False


def get_object_identification_tokens(obj) -> set:
    """
    Extracts all possible identification strings and tokens from a TS4 GameObject.
    Inspects:
    1. Object super_affordances and definition._super_affordances (stove_cook, fridge_clean, etc.)
    2. Direct obj.has_tag checks for official TS4 tag.Tag enum
    3. Localized catalog name (get_object_catalog_name, obj.definition.name)
    4. Definition tuning class (defn.cls) and tuning file name
    5. Active states on the object (StateComponent)
    6. Class name and str(obj)
    7. get_clean_object_tokens fallback
    """
    tokens = set()
    if obj is None:
        return tokens

    # 1. Super affordances tuned on object (e.g. stove_Cook, stove_Clean, stove_Repair)
    try:
        affs = []
        if hasattr(obj, "super_affordances"):
            sas = obj.super_affordances() if callable(obj.super_affordances) else obj.super_affordances
            if sas:
                affs.extend(sas)
        defn = getattr(obj, "definition", None)
        if defn is not None and hasattr(defn, "_super_affordances"):
            affs.extend(defn._super_affordances)
        for a in affs:
            a_str = (getattr(a, "__name__", "") or str(a)).lower()
            tokens.add(a_str)
            for p in re.split(r"[^a-zA-Z0-9]+", a_str):
                if p:
                    tokens.add(p)
    except Exception:
        pass

    # 2. Direct Tag checks via official TS4 tag.Tag
    try:
        import tag
        if hasattr(obj, "has_tag") and hasattr(tag, "Tag"):
            tag_map = [
                ("stove", ("Func_Stove", "Func_Oven", "BuyCatLD_Stove", "BuyCatEE_Stove", "Func_Barbeque", "Func_Grill")),
                ("fridge", ("Func_Fridge", "Func_Refrigerator", "BuyCatLD_Fridge")),
                ("sink", ("Func_Sink", "Func_Sink_Counter", "Func_Sink_Pedestal", "BuyCatLD_Sink")),
                ("toilet", ("Func_Toilet", "BuyCatLD_Toilet")),
                ("shower", ("Func_Shower", "Func_Shower_Tub", "BuyCatLD_Shower")),
                ("bathtub", ("Func_Bathtub", "Func_Tub", "BuyCatLD_Bathtub")),
                ("dishwasher", ("Func_Dishwasher", "BuyCatLD_Dishwasher")),
                ("microwave", ("Func_Microwave", "BuyCatEE_Microwave")),
                ("coffee", ("Func_CoffeeMaker", "Func_TeaMaker", "Func_EspressoMachine")),
                ("tv", ("Func_TV", "Func_Television", "BuyCatEE_TV")),
                ("computer", ("Func_Computer", "Func_Computer_Laptop", "BuyCatEE_Computer")),
                ("stereo", ("Func_Stereo", "Func_Speaker", "BuyCatEE_Stereo")),
                ("washingmachine", ("Func_Washer", "Func_WashingMachine")),
                ("dryer", ("Func_Dryer",)),
                ("robot", ("Func_Robot", "Func_Servo")),
                ("trash", ("Func_TrashCan", "Func_TrashChute")),
            ]
            for kw, tag_names in tag_map:
                for tn in tag_names:
                    t_val = getattr(tag.Tag, tn, None)
                    if t_val is not None:
                        try:
                            if obj.has_tag(t_val):
                                tokens.add(kw)
                                tokens.add(tn.lower())
                                break
                        except Exception:
                            pass
    except Exception:
        pass

    # 3. Localized catalog name
    try:
        from ai_thought_reader.context import get_object_catalog_name
        cat_name = get_object_catalog_name(obj)
        if cat_name:
            cn_lower = str(cat_name).lower()
            tokens.add(cn_lower)
            for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", cn_lower):
                if part:
                    tokens.add(part)
    except Exception:
        pass

    # 4. Target definition & tuning class
    try:
        defn = getattr(obj, "definition", None)
        if defn is not None:
            d_cls = getattr(defn, "cls", None)
            if d_cls is not None:
                cls_name = getattr(d_cls, "__name__", str(d_cls)).lower()
                tokens.add(cls_name)
                for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", cls_name):
                    if part:
                        tokens.add(part)

            t_name = getattr(defn, "tuning_file_name", None) or getattr(defn, "name", None)
            if t_name:
                tn_str = str(t_name).lower()
                tokens.add(tn_str)
                for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", tn_str):
                    if part:
                        tokens.add(part)
    except Exception:
        pass

    # 5. Object tags attribute if present
    try:
        tags = None
        if hasattr(obj, "get_tags"):
            tags = obj.get_tags()
        elif hasattr(obj, "tags"):
            tags = obj.tags
        if tags:
            for t in tags:
                t_name = getattr(t, "name", str(t)).lower()
                tokens.add(t_name)
                for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", t_name):
                    if part:
                        tokens.add(part)
    except Exception:
        pass

    # 6. Active states on the object
    try:
        sc = getattr(obj, "state_component", None)
        if sc is not None:
            states_dict = getattr(sc, "_states", None)
            if states_dict and hasattr(states_dict, "items"):
                for s_type, s_val in states_dict.items():
                    for s_item in (s_type, s_val):
                        s_str = (getattr(s_item, "__name__", "") or str(s_item)).lower()
                        tokens.add(s_str)
                        for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", s_str):
                            if part:
                                tokens.add(part)
    except Exception:
        pass

    # 7. Class name and str(obj)
    try:
        cls_n = obj.__class__.__name__.lower()
        tokens.add(cls_n)
        s_obj = str(obj).lower()
        tokens.add(s_obj)
        for part in re.split(r"[^a-zA-Zа-яА-Я0-9]+", s_obj):
            if part:
                tokens.add(part)
    except Exception:
        pass

    # 8. Fallback
    try:
        from ai_thought_reader.context import get_clean_object_tokens
        tokens.update(get_clean_object_tokens(obj))
    except Exception:
        pass

    return tokens


def get_broken_object_display_name(obj) -> str:
    """Translates broken Sims 4 object or puddle into clear Russian nominative noun."""
    if obj is None:
        return "бытовой прибор"

    tokens = get_object_identification_tokens(obj)

    res = "бытовой прибор"
    if any(k in tokens for k in ["puddle", "лужа"]):
        res = "лужа на полу"
    elif any(k in tokens for k in ["stove", "oven", "range", "grill", "barbeque", "bbq", "cooktop", "burner", "плит", "духовк", "печь", "конфорк"]):
        res = "кухонная плита"
    elif any(k in tokens for k in ["fridge", "refrigerator", "minifridge", "freezer", "холодильник", "морозильн"]):
        res = "холодильник"
    elif any(k in tokens for k in ["sink", "washbasin", "basin", "faucet", "раковин", "умывальник", "кран"]):
        res = "раковина"
    elif any(k in tokens for k in ["toilet", "urinal", "унитаз", "туалет"]):
        res = "унитаз"
    elif any(k in tokens for k in ["shower", "душ"]):
        res = "душ"
    elif any(k in tokens for k in ["bathtub", "tub", "hottub", "jacuzzi", "ванн", "джакузи"]):
        res = "ванна"
    elif any(k in tokens for k in ["dishwasher", "посудомоечн", "посудомойк"]):
        res = "посудомоечная машина"
    elif any(k in tokens for k in ["microwave", "микроволнов", "свч"]):
        res = "микроволновка"
    elif any(k in tokens for k in ["computer", "laptop", "pc", "desktop", "компьютер", "ноутбук", "пк"]):
        res = "компьютер"
    elif any(k in tokens for k in ["tv", "television", "телевизор", "тв"]):
        res = "телевизор"
    elif any(k in tokens for k in ["stereo", "audio", "speaker", "djbooth", "стерео", "колонк", "магнитофон"]):
        res = "стереосистема"
    elif any(k in tokens for k in ["coffee", "espresso", "teamaker", "kettle", "tea", "кофеварк", "чайник", "кофемашин", "эспрессо"]):
        res = "кофеварка"
    elif any(k in tokens for k in ["washingmachine", "washer", "стиральн", "стиралк"]):
        res = "стиральная машина"
    elif any(k in tokens for k in ["dryer", "сушилк"]):
        res = "сушилка для белья"
    elif any(k in tokens for k in ["robot", "servo", "робот", "серво"]):
        res = "робот"
    elif any(k in tokens for k in ["thermostat", "термостат"]):
        res = "термостат"
    elif any(k in tokens for k in ["trash", "nanocan", "trashchute", "мусор"]):
        res = "мусоропровод"
    elif any(k in tokens for k in ["dollhouse", "кукольн"]):
        res = "кукольный домик"
    else:
        try:
            from ai_thought_reader.context import get_object_catalog_name
            cat = get_object_catalog_name(obj)
            if cat and len(cat) <= 30:
                res = cat.lower()
        except Exception:
            pass

    log(f"[BROKEN OBJ DISP] obj={obj}, chosen='{res}', tokens_sample={list(tokens)[:8]}")
    return res


def get_broken_object_accusative_name(obj) -> str:
    """Translates object into Russian accusative case for '{sim} чинит ...'"""
    if obj is None:
        return "сломанный прибор"

    tokens = get_object_identification_tokens(obj)

    if any(k in tokens for k in ["stove", "oven", "range", "grill", "barbeque", "bbq", "cooktop", "burner", "плит", "духовк", "печь", "конфорк"]):
        return "кухонную плиту"
    if any(k in tokens for k in ["fridge", "refrigerator", "minifridge", "freezer", "холодильник", "морозильн"]):
        return "холодильник"
    if any(k in tokens for k in ["sink", "washbasin", "basin", "faucet", "раковин", "умывальник", "кран"]):
        return "раковину"
    if any(k in tokens for k in ["toilet", "urinal", "унитаз", "туалет"]):
        return "унитаз"
    if any(k in tokens for k in ["shower", "душ"]):
        return "душевую кабину"
    if any(k in tokens for k in ["bathtub", "tub", "hottub", "jacuzzi", "ванн", "джакузи"]):
        return "ванну"
    if any(k in tokens for k in ["dishwasher", "посудомоечн", "посудомойк"]):
        return "посудомоечную машину"
    if any(k in tokens for k in ["microwave", "микроволнов", "свч"]):
        return "микроволновку"
    if any(k in tokens for k in ["computer", "laptop", "pc", "desktop", "компьютер", "ноутбук", "пк"]):
        return "компьютер"
    if any(k in tokens for k in ["tv", "television", "телевизор", "тв"]):
        return "телевизор"
    if any(k in tokens for k in ["stereo", "audio", "speaker", "djbooth", "стерео", "колонк", "магнитофон"]):
        return "стереосистему"
    if any(k in tokens for k in ["coffee", "espresso", "teamaker", "kettle", "tea", "кофеварк", "чайник", "кофемашин", "эспрессо"]):
        return "кофеварку"
    if any(k in tokens for k in ["washingmachine", "washer", "стиральн", "стиралк"]):
        return "стиральную машину"
    if any(k in tokens for k in ["dryer", "сушилк"]):
        return "сушилку для белья"
    if any(k in tokens for k in ["robot", "servo", "робот", "серво"]):
        return "робота"
    if any(k in tokens for k in ["thermostat", "термостат"]):
        return "термостат"
    if any(k in tokens for k in ["trash", "nanocan", "trashchute", "мусор"]):
        return "мусоропровод"
    if any(k in tokens for k in ["dollhouse", "кукольн"]):
        return "кукольный домик"

    try:
        from ai_thought_reader.context import get_object_catalog_name
        cat = get_object_catalog_name(obj)
        if cat and len(cat) <= 30:
            return cat.lower()
    except Exception:
        pass

    return "сломанный прибор"


def format_broken_items_list(items: List[str]) -> str:
    """Formats list of broken items into natural Russian text."""
    if not items:
        return "бытовой прибор"
    hardware = [x for x in items if x != "лужа на полу"]
    if hardware:
        if len(hardware) == 1:
            return hardware[0]
        if len(hardware) == 2:
            return f"{hardware[0]} и {hardware[1]}"
        return f"{', '.join(hardware[:-1])} и {hardware[-1]}"
    if "лужа на полу" in items:
        return "лужа на полу"
    return "бытовой прибор"


def detect_broken_objects_in_scene(sim_a, sim_b, act_a: str, act_b: str):
    """
    Scans environment around sim_a and sim_b for broken objects, puddles, or active repair.
    Supports multiple broken objects (мультипредметность).
    Returns (has_broken, broken_names, repairer_name, repair_target, repair_other)
    """
    broken_names = []
    seen_names = set()

    # 1. Check if one of the Sims is actively repairing
    repairer_name = None
    repair_target = None
    repair_other = None

    for sim_inst, act_str, s_name, o_name in [
        (sim_a, act_a, getattr(getattr(sim_a, "sim_info", sim_a), "first_name", "Сим 1"), getattr(getattr(sim_b, "sim_info", sim_b), "first_name", "Сим 2")),
        (sim_b, act_b, getattr(getattr(sim_b, "sim_info", sim_b), "first_name", "Сим 2"), getattr(getattr(sim_a, "sim_info", sim_a), "first_name", "Сим 1"))
    ]:
        if any(w in act_str for w in ["чинит", "ремонт", "repair", "salvage"]):
            target_obj = None
            if hasattr(sim_inst, "get_all_running_and_queued_interactions"):
                try:
                    for inter in sim_inst.get_all_running_and_queued_interactions():
                        t = getattr(inter, "target", None)
                        if t is not None and not hasattr(t, "sim_info"):
                            target_obj = t
                            break
                except Exception:
                    pass
            target_acc = get_broken_object_accusative_name(target_obj) if target_obj else None
            if not target_acc:
                for k, acc in REPAIR_ACTIVITY_ACCUSATIVE_MAP:
                    if k in act_str:
                        target_acc = acc
                        break
            repairer_name = s_name
            repair_other = o_name
            repair_target = target_acc or "сломанный прибор"
            disp = get_broken_object_display_name(target_obj) if target_obj else "бытовой прибор"
            if disp not in seen_names:
                seen_names.add(disp)
                broken_names.append(disp)
            break

    # 2. Scan nearby environment for broken objects and puddles (within 8m)
    if services is not None:
        try:
            obj_mgr = services.object_manager()
            if obj_mgr is not None and hasattr(sim_a, "position"):
                pos_a = sim_a.position
                pos_b = getattr(sim_b, "position", pos_a)

                for obj in obj_mgr.get_all():
                    if obj is None:
                        continue
                    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
                        continue

                    o_pos = getattr(obj, "position", None)
                    if o_pos is None:
                        continue

                    # Skip objects on different floors (vertical delta > 2.5m)
                    if hasattr(pos_a, "y") and hasattr(o_pos, "y"):
                        if abs(pos_a.y - o_pos.y) > 2.5 and abs(pos_b.y - o_pos.y) > 2.5:
                            continue

                    dist_sq_a = (pos_a.x - o_pos.x)**2 + (pos_a.z - o_pos.z)**2
                    dist_sq_b = (pos_b.x - o_pos.x)**2 + (pos_b.z - o_pos.z)**2
                    min_dist_sq = min(dist_sq_a, dist_sq_b)

                    # Up to 8 meters (64.0 sq meters)
                    if min_dist_sq > 64.0:
                        continue

                    cls_n = obj.__class__.__name__.lower()
                    is_puddle = ("puddle" in cls_n or "лужа" in cls_n)
                    is_brk = is_object_broken(obj)

                    if is_brk or is_puddle:
                        d_name = get_broken_object_display_name(obj)
                        log(f"[BROKEN OBJ DETECTED] obj={obj}, is_brk={is_brk}, is_puddle={is_puddle}, name='{d_name}'")
                        if d_name and d_name not in seen_names:
                            seen_names.add(d_name)
                            broken_names.append(d_name)
        except Exception as e:
            log_exception("Error in detect_broken_objects_in_scene scan", e)

    has_broken = bool(broken_names or repairer_name)
    return has_broken, broken_names, repairer_name, repair_target, repair_other


def build_broken_object_premise(name_a: str, name_b: str, broken_names: List[str], repairer_name: Optional[str], repair_target: Optional[str], repair_other: Optional[str]) -> str:
    """Creates a concise, natural, simple premise for broken object(s) or puddles."""
    if repairer_name and repair_target:
        other = repair_other or (name_b if repairer_name == name_a else name_a)
        return f"{repairer_name} чинит {repair_target}, а {other} находится рядом."

    has_puddle = ("лужа на полу" in broken_names)
    hardware = [x for x in broken_names if x != "лужа на полу"]

    if hardware:
        if len(hardware) == 1:
            hw_str = hardware[0]
        elif len(hardware) == 2:
            hw_str = f"{hardware[0]} и {hardware[1]}"
        else:
            hw_str = f"{', '.join(hardware[:-1])} и {hardware[-1]}"

        if has_puddle:
            return f"В доме поломка: не работает {hw_str}, на полу лужа."
        return f"В доме поломка: не работает {hw_str}."

    if has_puddle:
        return "В доме на полу лужа."

    return "В доме поломка: не работает бытовой прибор."


# =========================================================================
# UNIVERSAL DIRTY ENVIRONMENT, DISHES & TRASH ENGINE
# TS4 Dirty & Cleanliness States (DirtyState 15129, Dirty 15128):
# 15130 = DirtyState_Clean
# 15132 = Dirty_Clean (Commodity_Cleanliness 50..100)
# 15134 = Dirty_Neutral (Commodity_Cleanliness 0..50 - default clean state for counters, sinks, tubs)
# 101103 = DirtyState_Neutral
# 255048 = dustLevel_Object_Values_Clean
#
# Dirty / Filthy states:
# 15131 = DirtyState_Dirty
# 15133 = Dirty_Dirty (Commodity_Cleanliness -50..0)
# 15135 = Dirty_VeryDirty (Commodity_Cleanliness -100..-50)
# 120443 = BathState_Dirty
# 255050 = dustLevel_Object_Values_Dirty
# 255051 = dustLevel_Object_Values_Filthy
KNOWN_DIRTY_CLEANLINESS_GUIDS = {
    15131,   # DirtyState_Dirty
    15133,   # Dirty_Dirty
    15135,   # Dirty_VeryDirty
    120443,  # BathState_Dirty
    255050,  # dustLevel_Object_Values_Dirty
    255051,  # dustLevel_Object_Values_Filthy
}
KNOWN_CLEAN_CLEANLINESS_GUIDS = {
    15130,   # DirtyState_Clean
    15132,   # Dirty_Clean
    15134,   # Dirty_Neutral (standard clean counter/appliance state)
    101103,  # DirtyState_Neutral
    255048,  # dustLevel_Object_Values_Clean
}

KNOWN_FRESH_FOOD_GUIDS = {
    15304,   # Freshness_Fresh
    132212,  # Freshness_Untracked_Fresh
    262339,  # Freshness_Preserved
}
KNOWN_SPOILED_FOOD_GUIDS = {
    15305,   # Freshness_Spoiled
    132213,  # Freshness_Untracked_Spoiled
    99427,   # Food_Stink
}


def is_trashcan_object_full(obj) -> bool:
    """Trash can checking has been completely eliminated as per user instruction."""
    return False


def is_food_or_dish_object(obj) -> bool:
    """
    Returns True ONLY if obj is an actual food serving, plate/bowl with food, snack, or drink.
    STRICTLY rejects all appliances (fridge, stove, counter, microwave, sink, toilet, etc.)
    and furniture/electronics so appliances are NEVER mistaken for food!
    """
    if obj is None:
        return False
    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
        return False

    cls_n = obj.__class__.__name__.lower()
    defn = getattr(obj, "definition", None)
    d_name = (str(getattr(defn, "name", "")) or str(defn) or "").lower()

    # 1. HARD REJECT any appliance, plumbing, surface, furniture, electronics, structural object
    appliance_or_surface_tokens = (
        "fridge", "refrigerator", "freezer", "minifridge",
        "stove", "oven", "range", "grill", "cooktop", "burner",
        "microwave", "toaster", "coffeemaker", "teamaker", "kettle",
        "counter", "island", "cabinet", "bar", "table", "desk", "chair", "sofa", "couch", "stool", "bed",
        "sink", "basin", "faucet", "toilet", "urinal", "shower", "bathtub", "tub", "jacuzzi", "dishwasher",
        "trashcan", "trash_can", "dumpster", "nanocan", "wastebasket", "garbagecan", "garbage_can", "chute",
        "computer", "laptop", "tv", "television", "stereo", "speaker", "dryer", "washer", "washingmachine",
        "bookshelf", "bookcase", "door", "window", "floor", "wall", "easel", "mirror", "fireplace"
    )
    if any(k in cls_n or k in d_name for k in appliance_or_surface_tokens):
        return False

    # Check tags for appliances/surfaces
    try:
        import tag
        if hasattr(obj, "has_tag") and hasattr(tag, "Tag"):
            appliance_tags = (
                "Func_Fridge", "Func_Refrigerator", "Func_Stove", "Func_Oven",
                "Func_Microwave", "Func_Counter", "Func_Sink", "Func_Toilet",
                "Func_Shower", "Func_Bathtub", "Func_Dishwasher", "Func_TrashCan",
                "Func_Table", "Func_Desk", "Func_Chair", "Func_Bed", "Func_Computer"
            )
            for at in appliance_tags:
                t_val = getattr(tag.Tag, at, None)
                if t_val is not None and obj.has_tag(t_val):
                    return False
    except Exception:
        pass

    # Quick check: Official Maxis spoilable/crafting
    if SpoilableObjectMixin is not None and hasattr(SpoilableObjectMixin, "object_is_spoiled"):
        try:
            if SpoilableObjectMixin.object_is_spoiled(obj):
                return True
        except Exception:
            pass

    if CraftingTuning is not None and hasattr(CraftingTuning, "SPOILED_STATE_VALUE"):
        try:
            spoil_val = getattr(CraftingTuning, "SPOILED_STATE_VALUE", None)
            if spoil_val is not None:
                spoil_state = getattr(spoil_val, "state", None)
                if spoil_state is not None and hasattr(obj, "has_state") and obj.has_state(spoil_state):
                    if obj.get_state(spoil_state) is spoil_val:
                        return True
        except Exception:
            pass

    # 2. Check for consumable component (standard TS4 food/drink serving component)
    if getattr(obj, "consumable_component", None) is not None:
        return True

    try:
        comps = getattr(obj, "components", ())
        for c in comps:
            c_name = c.__class__.__name__.lower()
            if "consumable" in c_name:
                return True
    except Exception:
        pass

    # 3. Check crafting process (food crafted by sims)
    if hasattr(obj, "get_crafting_process") and callable(getattr(obj, "get_crafting_process")):
        try:
            if obj.get_crafting_process() is not None:
                return True
        except Exception:
            pass
    elif getattr(obj, "crafting_process", None) is not None:
        return True

    # 4. Check recipe attribute
    if getattr(obj, "recipe", None) is not None or getattr(obj, "serving_recipe", None) is not None:
        return True

    # 5. Food / serving / dish tokens in class name or definition name
    food_tokens = (
        "serving", "portion", "snack", "quickmeal", "meal", "food",
        "plate", "bowl", "dish", "mug", "cup", "glass",
        "salad", "peas", "cereal", "oatmeal", "chips", "yogurt", "crackers",
        "sandwich", "pasta", "spaghetti", "macandcheese", "soup", "chili",
        "hamburger", "burger", "hotdog", "pizza", "taco", "steak", "roast",
        "pancake", "waffle", "toast", "burrito", "ramen"
    )
    if any(ft in cls_n or ft in d_name for ft in food_tokens):
        return True

    return False


def is_object_cleanliness_dirty(obj) -> bool:
    """Checks if an object is dirty/grimy according to its cleanliness state."""
    if obj is None:
        return False

    sc = getattr(obj, "state_component", None)
    if sc is not None:
        try:
            states_dict = getattr(sc, "_states", None)
            if states_dict and hasattr(states_dict, "items"):
                for s_type, s_val in states_dict.items():
                    val_guid = getattr(s_val, "guid64", 0) or getattr(s_val, "id", 0)
                    if val_guid in KNOWN_DIRTY_CLEANLINESS_GUIDS:
                        log(f"[DIRTY CHECK] obj={obj} is DIRTY via GUID {val_guid} (s_type={s_type}, s_val={s_val})")
                        return True
                    if val_guid in KNOWN_CLEAN_CLEANLINESS_GUIDS:
                        continue

                    v_str = f"{getattr(s_val, '__name__', '')} {getattr(s_val, 'name', '')} {str(s_val)}".lower()
                    t_str = f"{getattr(s_type, '__name__', '')} {getattr(s_type, 'name', '')} {str(s_type)}".lower()

                    # 1. HARD EXCLUDE non-dirtiness and non-object states:
                    # (lottrait, upgrades, visible contents in slots, food servings, consumables, etc.)
                    if any(u in t_str or u in v_str for u in (
                        "lottrait", "lot_trait", "upgrade", "lockdirt", "lock_dirt", "notstarted", "not_started",
                        "contentsvisible", "consumable", "quality", "servings", "freshness", "recipe", "material_change"
                    )):
                        continue

                    # 2. HARD EXCLUDE negative or clean/neutral states:
                    # (lottrait_filthy_0_no, not_dirty, clean, pristine, neutral, normal)
                    if any(safe in v_str for safe in (
                        "_no", "0_no", "_none", "not_", "notdirty", "not_dirty", "never",
                        "clean", "unsoiled", "sparkling", "pristine", "neutral", "normal"
                    )):
                        continue

                    # 3. Explicit dirty check: State type MUST be dirtiness/cleanliness AND value indicates dirty
                    is_dirt_state_type = any(k in t_str for k in ("dirty", "dirtiness", "cleanliness", "hygiene", "grime"))
                    if is_dirt_state_type and any(d in v_str for d in ("dirty", "filthy", "verydirty", "grimy", "soiled")):
                        log(f"[DIRTY CHECK] obj={obj} is DIRTY via token in v_str='{v_str}' (t_str='{t_str}')")
                        return True
        except Exception:
            pass

    if hasattr(obj, "get_state_values"):
        try:
            for s_val in obj.get_state_values():
                val_guid = getattr(s_val, "guid64", 0) or getattr(s_val, "id", 0)
                if val_guid in KNOWN_DIRTY_CLEANLINESS_GUIDS:
                    log(f"[DIRTY CHECK] obj={obj} is DIRTY via get_state_values GUID {val_guid}")
                    return True
                if val_guid in KNOWN_CLEAN_CLEANLINESS_GUIDS:
                    continue

                v_str = f"{getattr(s_val, '__name__', '')} {getattr(s_val, 'name', '')} {str(s_val)}".lower()
                if any(u in v_str for u in (
                    "lottrait", "lot_trait", "upgrade", "lockdirt", "lock_dirt", "notstarted", "not_started",
                    "contentsvisible", "consumable", "quality", "servings", "freshness", "recipe", "material_change"
                )):
                    continue
                if any(safe in v_str for safe in (
                    "_no", "0_no", "_none", "not_", "notdirty", "not_dirty", "never",
                    "clean", "unsoiled", "sparkling", "pristine", "neutral", "normal"
                )):
                    continue
                if any(d in v_str for d in ("cleanliness_dirty", "cleanliness_filthy", "cleanliness_verydirty", "dirtiness_dirty", "dirty_dirty", "dirty_verydirty", "dirtystate_dirty")):
                    log(f"[DIRTY CHECK] obj={obj} is DIRTY via get_state_values token '{v_str}'")
                    return True
        except Exception:
            pass

    return False


def is_object_food_spoiled(obj) -> bool:
    """
    Checks if a genuine food serving, plate, bowl, or snack has spoiled.
    Returns True if the food has spoiled according to official TS4 states.
    """
    if obj is None:
        return False
    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
        return False

    # Check 1: Official Maxis SpoilableObjectMixin check
    if SpoilableObjectMixin is not None and hasattr(SpoilableObjectMixin, "object_is_spoiled"):
        try:
            if SpoilableObjectMixin.object_is_spoiled(obj):
                log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via SpoilableObjectMixin.object_is_spoiled")
                return True
        except Exception:
            pass

    # Check 2: CraftingTuning.SPOILED_STATE_VALUE direct check
    if CraftingTuning is not None and hasattr(CraftingTuning, "SPOILED_STATE_VALUE"):
        try:
            spoil_val = getattr(CraftingTuning, "SPOILED_STATE_VALUE", None)
            if spoil_val is not None:
                spoil_state = getattr(spoil_val, "state", None)
                if spoil_state is not None and hasattr(obj, "has_state") and obj.has_state(spoil_state):
                    if obj.get_state(spoil_state) is spoil_val:
                        log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via CraftingTuning.SPOILED_STATE_VALUE")
                        return True
        except Exception:
            pass

    # STRICT GUARD: non-food objects cannot be spoiled food
    if not is_food_or_dish_object(obj):
        return False

    # Check 3: StateComponent inspection
    sc = getattr(obj, "state_component", None)
    if sc is not None:
        try:
            states_dict = getattr(sc, "_states", None)
            if states_dict and hasattr(states_dict, "items"):
                for s_type, s_val in states_dict.items():
                    val_guid = getattr(s_val, "guid64", 0) or getattr(s_val, "id", 0)
                    if val_guid in KNOWN_SPOILED_FOOD_GUIDS:
                        log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via KNOWN_SPOILED_FOOD_GUIDS ({val_guid})")
                        return True

                    v_name = f"{getattr(s_val, '__name__', '')} {getattr(s_val, 'name', '')} {str(s_val)}".lower()
                    t_name = f"{getattr(s_type, '__name__', '')} {getattr(s_type, 'name', '')} {str(s_type)}".lower()

                    # Only evaluate freshness / spoil states
                    if any(k in t_name for k in ("freshness", "spoil", "stink", "rotten")):
                        if any(sp in v_name for sp in ("spoiled", "rotten", "foul", "expired", "stink")) and "unspoiled" not in v_name:
                            log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via token '{v_name}' in state '{t_name}'")
                            return True
                    else:
                        if any(sp in v_name for sp in ("_spoiled", "is_spoiled", "state_spoiled", "food_stink")) and "unspoiled" not in v_name:
                            log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via direct token '{v_name}'")
                            return True
        except Exception:
            pass

    # Check 4: get_state_values inspection
    if hasattr(obj, "get_state_values"):
        try:
            for s_val in obj.get_state_values():
                val_guid = getattr(s_val, "guid64", 0) or getattr(s_val, "id", 0)
                if val_guid in KNOWN_SPOILED_FOOD_GUIDS:
                    log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via get_state_values GUID {val_guid}")
                    return True
                v_name = f"{getattr(s_val, '__name__', '')} {getattr(s_val, 'name', '')} {str(s_val)}".lower()
                if any(sp in v_name for sp in ("spoiled", "rotten", "stink")) and "unspoiled" not in v_name:
                    log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via get_state_values token '{v_name}'")
                    return True
        except Exception:
            pass

    # Check 5: Commodity tracker check (Commodity_Freshness GUID 16591)
    try:
        stat_tracker = getattr(obj, "statistic_tracker", None) or getattr(obj, "commodity_tracker", None)
        if stat_tracker is not None:
            stats = getattr(stat_tracker, "_statistics", {})
            if isinstance(stats, dict):
                for stat in stats.values():
                    st_type = getattr(stat, "stat_type", None)
                    s_name = (getattr(st_type, "__name__", "") or str(st_type) or "").lower()
                    s_guid = getattr(st_type, "guid64", 0) or getattr(st_type, "id", 0)
                    if s_guid == 16591 or "freshness" in s_name:
                        val = getattr(stat, "get_value", lambda: 100)()
                        min_val = getattr(stat, "min_value", 0)
                        if val <= min_val or val <= 0:
                            log(f"[SPOILED FOOD DETECTED] obj={obj} is spoiled via freshness commodity value={val}")
                            return True
    except Exception:
        pass

    return False


def is_clean_food_name(s: str) -> bool:
    """Validates that extracted string is a clean human food name and not generic container or hash."""
    if not s or not isinstance(s, str):
        return False
    s_clean = s.strip()
    if not s_clean or s_clean.isdigit():
        return False
    if any(bad in s_clean.lower() for bad in [
        "hash:", "tokens", "text_string", "{", "}", "0x", "<", "0b", "key:",
        "object", "tuning", "component", "interaction", "generic"
    ]):
        return False
    low = s_clean.lower()
    if low in ("миска", "тарелка", "поднос", "блюдо", "чашка", "кружка", "стакан", "порция", "тарелка порционная", "bowl", "plate", "dish", "serving", "cup", "mug", "glass"):
        return False
    return True


FOOD_ITEMS_AND_SNACKS_CATALOG = [
    # Quick Meals from Fridge
    (["peas", "pea", "горошек", "горох"], "Горошек"),
    (["cereal", "хлопья"], "Хлопья с молоком"),
    (["oatmeal", "овсянк"], "Овсяная каша"),
    (["chips", "чипсы", "crisps"], "Чипсы"),
    (["yogurt", "йогурт"], "Йогурт"),
    (["animalcrackers", "animal_crackers", "crackers", "сырные крекеры", "крекер"], "Сырные крекеры"),
    (["applesauce", "apple_sauce", "яблочное пюре"], "Яблочное пюре"),
    (["hamandcheese", "ham_and_cheese", "бутерброд с ветчиной"], "Бутерброд с ветчиной и сыром"),
    (["cheeseandcrackers", "cheese_crackers"], "Сыр с крекерами"),
    (["milk", "молоко"], "Молоко"),
    (["orangejuice", "orange_juice", "juice", "сок"], "Апельсиновый сок"),

    # Microwave Quick Meals
    (["microwavedinner", "microwave_dinner", "tvdinner", "tv_dinner", "готовый обед"], "Готовый обед из микроволновки"),
    (["burrito", "буррито"], "Буррито"),
    (["toasterpastry", "toaster_pastry", "pastry", "выпечка для тостера"], "Выпечка для тостера"),
    (["ramen", "instantramen", "instant_ramen", "лапша быстрого приготовления", "рамен"], "Лапша быстрого приготовления"),
    (["pizzarolls", "pizza_rolls", "пицца-роллы"], "Пицца-роллы"),

    # Cooked & Prepared Meals
    (["gardensalad", "garden_salad", "садовый салат", "садовый_салат", "осенний салат"], "Садовый салат"),
    (["caprese", "капрезе"], "Салат капрезе"),
    (["caesar", "цезарь"], "Салат Цезарь"),
    (["salad", "салат"], "Салат"),
    (["grilledcheese", "grilled_cheese", "жареный сыр"], "Горячий бутерброд с сыром"),
    (["macandcheese", "mac_and_cheese", "macaroni", "макароны с сыром"], "Макароны с сыром"),
    (["spaghetti", "спагетти"], "Спагетти"),
    (["bolognese", "болоньезе"], "Спагетти Болоньезе"),
    (["carbonara", "карбонара"], "Паста Карбонара"),
    (["lasagna", "лазань"], "Лазанья"),
    (["pasta", "паста", "ravioli", "равиоли"], "Паста"),
    (["pancake", "pancakes", "блинчик", "блины"], "Блинчики"),
    (["waffle", "waffles", "вафл"], "Вафли"),
    (["frenchtoast", "french_toast", "французские тосты"], "Французские тосты"),
    (["eggsandtoast", "eggs_and_toast", "яичница с тостами"], "Яичница с тостами"),
    (["scrambledeggs", "scrambled_eggs", "яичница"], "Яичница"),
    (["omelet", "omlet", "омлет"], "Омлет"),
    (["toast", "тост"], "Тосты"),
    (["cheeseburger", "чизбургер"], "Чизбургер"),
    (["hamburger", "burger", "гамбургер", "бургер"], "Бургер"),
    (["hotdog", "frankfurter", "хот-дог", "хотдог"], "Хот-доги"),
    (["sandwich", "panini", "blt", "сэндвич", "бутерброд"], "Сэндвич"),
    (["chili", "чили"], "Чили"),
    (["clamchowder", "chowder", "чаудер"], "Суп из морепродуктов"),
    (["tomatosoup", "tomato_soup", "томатный суп"], "Томатный суп"),
    (["butternutsquash", "тыквенный суп"], "Тыквенный суп"),
    (["chickennoodle", "chicken_noodle", "куриный суп"], "Куриный суп с лапшой"),
    (["minestrone", "минестроне"], "Минестроне"),
    (["soup", "broth", "stew", "суп", "рагу", "похлебк", "борщ"], "Суп"),
    (["steak", "ribeye", "filet", "tritip", "стейк"], "Стейк"),
    (["porkchop", "отбивн", "свинин"], "Свиные отбивные"),
    (["roast", "beef", "жаркое", "говядин"], "Мясное жаркое"),
    (["ribs", "ребрышк"], "Ребрышки барбекю"),
    (["meatloaf", "мясной рулет"], "Мясной рулет"),
    (["chicken", "turkey", "куриц", "индейк"], "Курица / Индейка"),
    (["salmon", "лосось", "семг"], "Лосось"),
    (["fishandchips", "fish_and_chips", "рыба с картошкой"], "Рыба с жареным картофелем"),
    (["pizza", "пицц"], "Пицца"),
    (["taco", "tacos", "тако"], "Тако"),
]


def get_food_object_name(obj) -> str:
    """
    Extracts the specific food or dish name (e.g. 'Горошек', 'Осенний салат', 'Спагетти')
    from a TS4 food object, quick meal (fridge snack), or microwave meal.
    Returns empty string if not determinable or if obj is not actual food.
    """
    if obj is None or not is_food_or_dish_object(obj):
        return ""

    # 1. Custom name if assigned by sim/player
    try:
        if hasattr(obj, "get_custom_name"):
            cn = obj.get_custom_name()
            if is_clean_food_name(str(cn)):
                log(f"[FOOD_NAME] Resolved via get_custom_name: {cn}")
                return str(cn).strip()
    except Exception:
        pass

    # Find recipe tuning from crafting process, object attributes, or components
    proc = None
    if hasattr(obj, "get_crafting_process") and callable(getattr(obj, "get_crafting_process")):
        try:
            proc = obj.get_crafting_process()
        except Exception:
            pass
    elif hasattr(obj, "crafting_process"):
        proc = getattr(obj, "crafting_process", None)

    recipes_to_check = []
    if proc is not None:
        r_proc = getattr(proc, "recipe", None)
        if r_proc is not None:
            recipes_to_check.append(r_proc)

    for attr in ("recipe", "serving_recipe"):
        r_obj = getattr(obj, attr, None)
        if r_obj is not None and r_obj not in recipes_to_check:
            recipes_to_check.append(r_obj)

    cc = getattr(obj, "consumable_component", None)
    if cc is not None:
        r_cc = getattr(cc, "recipe", None)
        if r_cc is not None and r_cc not in recipes_to_check:
            recipes_to_check.append(r_cc)

    # 2. Extract localized string from Recipe
    for rec in recipes_to_check:
        for attr in ("recipe_name", "_recipe_name", "name", "_name"):
            loc_name = getattr(rec, attr, None)
            if loc_name is not None and LocalizationHelperTuning is not None:
                try:
                    raw = LocalizationHelperTuning.get_raw_text(loc_name)
                    if raw and is_clean_food_name(str(raw)):
                        log(f"[FOOD_NAME] Resolved via recipe.{attr}: {raw}")
                        return str(raw).strip()
                except Exception:
                    pass

        # Check get_recipe_name method
        if hasattr(rec, "get_recipe_name") and callable(getattr(rec, "get_recipe_name")):
            for arg in (obj, None):
                try:
                    res = rec.get_recipe_name(arg) if arg else rec.get_recipe_name()
                    if res is not None and LocalizationHelperTuning is not None:
                        raw = LocalizationHelperTuning.get_raw_text(res)
                        if is_clean_food_name(str(raw)):
                            log(f"[FOOD_NAME] Resolved via recipe.get_recipe_name: {raw}")
                            return str(raw).strip()
                except Exception:
                    pass

    # 3. Check UI metadata generators (_ui_metadata_gen on obj and components)
    try:
        sources = [obj]
        comps = getattr(obj, "components", ())
        if comps:
            sources.extend(comps)
        for s in sources:
            if hasattr(s, "_ui_metadata_gen"):
                for k, v in s._ui_metadata_gen():
                    if k in ("recipe_name", "food_name", "name", "serving_name") and v:
                        raw = None
                        if isinstance(v, str):
                            raw = v
                        elif LocalizationHelperTuning is not None:
                            try:
                                raw = LocalizationHelperTuning.get_raw_text(v)
                            except Exception:
                                pass
                        if raw and is_clean_food_name(str(raw)):
                            log(f"[FOOD_NAME] Resolved via _ui_metadata_gen ({k}): {raw}")
                            return str(raw).strip()
    except Exception:
        pass

    # 4. Definition catalog name via create_localized_string
    try:
        from sims4.localization import create_localized_string
        defn = getattr(obj, "definition", None) or getattr(obj, "default_definition", None)
        if defn is not None and hasattr(defn, "name"):
            loc_str = create_localized_string(defn.name)
            if loc_str and LocalizationHelperTuning is not None:
                raw = LocalizationHelperTuning.get_raw_text(loc_str)
                if raw and is_clean_food_name(str(raw)):
                    log(f"[FOOD_NAME] Resolved via definition create_localized_string: {raw}")
                    return str(raw).strip()
    except Exception:
        pass

    # 5. Direct catalog & token matching strictly on food recipe and definition tokens
    # (Never search generic appliance affordances!)
    try:
        tokens_to_search = set()
        for r in recipes_to_check:
            tokens_to_search.add(str(getattr(r, "__name__", "") or r).lower())
            tokens_to_search.add(str(getattr(r, "name", "") or "").lower())
        tokens_to_search.add(str(obj.__class__.__name__).lower())
        tokens_to_search.add(str(obj).lower())
        defn = getattr(obj, "definition", None)
        if defn:
            tokens_to_search.add(str(getattr(defn, "name", "") or defn).lower())
            tn = getattr(defn, "tuning_file_name", None)
            if tn:
                tokens_to_search.add(str(tn).lower())
        joined_search = " ".join(tokens_to_search).replace("_", "").lower()
        log(f"[FOOD_NAME] Tokens to search: {joined_search}")

        for cat_keys, cat_name in FOOD_ITEMS_AND_SNACKS_CATALOG:
            if any(k.replace("_", "").lower() in joined_search for k in cat_keys):
                log(f"[FOOD_NAME] Resolved via FOOD_ITEMS_AND_SNACKS_CATALOG: {cat_name} (tokens: {joined_search[:100]})")
                return cat_name
    except Exception as e:
        log_exception("Error in FOOD_ITEMS_AND_SNACKS_CATALOG matching", e)

    return ""


def get_sim_eating_food_name(sim_inst, sim_info, act_str: str = "") -> str:
    """
    Extracts the human-readable localized name of the food or dish a Sim is currently eating.
    Checks running interactions, target dish/plate, carried objects, plant produce, and activity strings.
    """
    # 1. Check running eating interactions on sim_inst
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                i_name = getattr(inter, "__name__", str(inter)).lower()
                if any(skip in aff_name or skip in i_name for skip in ("seating", "seat_", "sit_", "posture", "broadcaster", "reaction", "chair", "sofa", "bed")):
                    continue
                if any(k in aff_name for k in ("_eat", "eat_", "eat_active", "consume", "dine", "meal", "food_eat")):
                    # Check interaction UI name (e.g., 'Съесть (Макароны с сыром)' or 'Есть: Салат')
                    try:
                        from ai_thought_reader.context import get_interaction_ui_name
                        ui_n = get_interaction_ui_name(inter)
                        if ui_n:
                            cand = ""
                            if "(" in ui_n and ")" in ui_n:
                                s_idx = ui_n.find("(") + 1
                                e_idx = ui_n.rfind(")")
                                if 0 <= s_idx < e_idx:
                                    cand = ui_n[s_idx:e_idx].strip()
                            elif ":" in ui_n:
                                cand = ui_n.split(":", 1)[1].strip()
                            if cand and is_clean_food_name(cand):
                                log(f"[EATING_FOOD_NAME] Found from interaction UI name: {cand}")
                                return cand.capitalize()
                    except Exception:
                        pass

                    # Check interaction targets and carried items
                    candidates = []
                    tgt = getattr(inter, "target", None)
                    if tgt is not None:
                        candidates.append(tgt)
                    if hasattr(inter, "get_target"):
                        try:
                            cand_t = inter.get_target()
                            if cand_t is not None and cand_t not in candidates:
                                candidates.append(cand_t)
                        except Exception:
                            pass
                    if hasattr(inter, "carried_object"):
                        c = getattr(inter, "carried_object", None)
                        if c is not None and c not in candidates:
                            candidates.append(c)

                    for obj in candidates:
                        f_n = get_food_object_name(obj)
                        if f_n:
                            log(f"[EATING_FOOD_NAME] Found from target object {obj}: {f_n}")
                            return f_n
                        try:
                            from ai_thought_reader.context import extract_crafting_item_name, extract_plant_name
                            c_n = extract_crafting_item_name(inter, obj)
                            if c_n and is_clean_food_name(c_n):
                                log(f"[EATING_FOOD_NAME] Found from extract_crafting_item_name: {c_n}")
                                return c_n
                            p_n = extract_plant_name(obj, inter)
                            if p_n and is_clean_food_name(p_n):
                                log(f"[EATING_FOOD_NAME] Found from extract_plant_name: {p_n}")
                                return p_n
                        except Exception:
                            pass
        except Exception as e:
            log_exception("Error inspecting eating interactions for food name", e)

    # 2. Check carried objects or posture targets on sim_inst
    if sim_inst is not None:
        try:
            posture = getattr(sim_inst, "posture", None)
            if posture is not None:
                for attr in ("carried_object", "source_dest_target", "target"):
                    obj = getattr(posture, attr, None)
                    if obj is not None and is_food_or_dish_object(obj):
                        f_n = get_food_object_name(obj)
                        if f_n:
                            log(f"[EATING_FOOD_NAME] Found from posture {attr}: {f_n}")
                            return f_n
        except Exception:
            pass

    # 3. Check act_str / get_current_activity
    if not act_str and sim_info is not None:
        try:
            from ai_thought_reader.context import get_current_activity
            act_str = get_current_activity(sim_info) or ""
        except Exception:
            pass

    if act_str:
        clean_act = act_str.strip()
        # Case 3a: "Ест свежие ягоды (Клубника)" or "Лакомится плодом (Яблоко)"
        if "(" in clean_act and ")" in clean_act:
            s_idx = clean_act.rfind("(") + 1
            e_idx = clean_act.rfind(")")
            if 0 <= s_idx < e_idx:
                inner = clean_act[s_idx:e_idx].strip()
                if inner and is_clean_food_name(inner) and inner.lower() not in ("ест", "кушает", "еда", "пища"):
                    log(f"[EATING_FOOD_NAME] Found from parenthesized activity '{act_str}': {inner}")
                    return inner.capitalize()

        # Case 3b: Strip verb prefix: "Ест макароны с сыром", "Кушает сочный стейк"
        for prefix in ("Кушает ", "кушает ", "Ест ", "ест ", "Лакомится ", "лакомится ", "Поедает ", "поедает ", "Трапезничает ", "трапезничает ", "Хрустит ", "хрустит "):
            if clean_act.startswith(prefix):
                cand = clean_act[len(prefix):].strip()
                if cand and is_clean_food_name(cand) and cand.lower() not in ("пищу", "еду", "пищу (ест)", "(ест)"):
                    log(f"[EATING_FOOD_NAME] Found from activity prefix '{prefix}' -> '{cand}'")
                    return cand.capitalize()

    return ""


def is_object_dirty(obj) -> bool:
    """
    Checks if a TS4 GameObject is dirty: spoiled food,
    trash piles on the floor, or dirty plumbing/appliances/counters.
    Trash cans and generic clean/empty dishes are COMPLETELY EXCLUDED.
    """
    if obj is None:
        return False
    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
        return False

    cls_n = obj.__class__.__name__.lower()
    defn = getattr(obj, "definition", None)
    d_name = (str(getattr(defn, "name", "")) or str(defn) or "").lower()
    tokens = get_object_identification_tokens(obj)

    # 1. COMPLETELY CUT TRASH CANS / DUMPSTERS
    if any(k in tokens or k in cls_n or k in d_name for k in ("trashcan", "trash_can", "dumpster", "nanocan", "wastebasket", "garbagecan", "garbage_can", "chute", "trashchute")):
        return False

    # 2. Food or dishes: ONLY check if food is spoiled!
    if is_object_food_spoiled(obj):
        return True
    if is_food_or_dish_object(obj):
        return False

    # 3. Explicit trash pile on floor
    if any(k in cls_n or k in d_name or k in tokens for k in ("trashpile", "trash_pile", "rubbish_pile", "garbage_pile", "trash_bag", "garbagebag")):
        return True

    # 4. Completely exclude plates, bowls, cups, dishes from general cleanliness so they never register as "грязная посуда"
    if any(k in cls_n or k in d_name or k in tokens for k in ("dish", "plate", "bowl", "mug", "glass", "cup", "serving", "dirtydish", "dirty_dish")):
        return False

    # 5. Dirty plumbing, appliances, counters, stoves, sinks, toilets, etc.
    if is_object_cleanliness_dirty(obj):
        return True

    return False


def get_dirty_object_display_name(obj) -> str:
    """Translates dirty Sims 4 object into a natural Russian noun phrase."""
    if obj is None:
        return "грязь в доме"

    tokens = get_object_identification_tokens(obj)
    cls_n = obj.__class__.__name__.lower()
    defn = getattr(obj, "definition", None)
    d_name = (str(getattr(defn, "name", "")) or str(defn) or "").lower()

    # 1. Spoiled food (ONLY if actual food object AND spoiled)
    if is_object_food_spoiled(obj):
        food_name = get_food_object_name(obj)
        if food_name:
            return f"тарелка с испорченной едой ({food_name})"
        return "тарелка с испорченной едой"

    # 2. Trash pile on floor
    if any(k in cls_n or k in d_name or k in tokens for k in ("trashpile", "trash_pile", "rubbish", "garbage")):
        return "мусор на полу"

    # 3. Plumbing & appliances
    if any(k in tokens for k in ["stove", "oven", "range", "cooktop", "burner", "плит", "духовк", "печь", "конфорк"]):
        return "грязная кухонная плита"
    if any(k in tokens for k in ["sink", "washbasin", "basin", "faucet", "раковин", "умывальник", "кран"]):
        return "грязная раковина"
    if any(k in tokens for k in ["toilet", "urinal", "унитаз", "туалет"]):
        return "грязный унитаз"
    if any(k in tokens for k in ["shower", "душ"]):
        return "грязный душ"
    if any(k in tokens for k in ["bathtub", "tub", "hottub", "ванн", "джакузи"]):
        return "грязная ванна"
    if any(k in tokens for k in ["counter", "island", "тумб", "столешниц"]):
        return "грязные кухонные тумбы"
    if any(k in tokens for k in ["fridge", "refrigerator", "холодильник"]):
        return "грязный холодильник"
    if any(k in tokens for k in ["microwave", "микроволнов"]):
        return "грязная микроволновка"

    return "неубранная грязь"


def detect_dirty_environment_in_scene(sim_a, sim_b, act_a: str, act_b: str):
    """
    Scans environment around sim_a and sim_b for dirty objects, full trash cans, dirty dishes, or active cleaning.
    Supports multiple dirty items (мультипредметность).
    Returns (has_dirty, dirty_names, cleaner_name, clean_target, clean_other)
    """
    dirty_names = []
    seen_names = set()

    # 1. Check if one of the Sims is actively cleaning
    cleaner_name = None
    clean_target = None
    clean_other = None

    for sim_inst, act_str, s_name, o_name in [
        (sim_a, act_a, getattr(getattr(sim_a, "sim_info", sim_a), "first_name", "Сим 1"), getattr(getattr(sim_b, "sim_info", sim_b), "first_name", "Сим 2")),
        (sim_b, act_b, getattr(getattr(sim_b, "sim_info", sim_b), "first_name", "Сим 2"), getattr(getattr(sim_a, "sim_info", sim_a), "first_name", "Сим 1"))
    ]:
        act_lower = (act_str or "").lower()
        # Personal hygiene guard: washing hands, brushing teeth, showering, bathing are NOT house cleaning!
        if any(h in act_lower for h in ["руки", "рук", "зубы", "зуб", "умыва", "душ", "ванн", "моется", "wash_hands", "washhands", "brush_teeth", "take_shower"]):
            continue

        if any(w in act_lower for w in ["уборка", "моет", "чистит", "вытирает", "выносит мусор", "clean", "wash_dishes", "take_out_trash", "throw_away", "mop"]):
            target_obj = None
            if hasattr(sim_inst, "get_all_running_and_queued_interactions"):
                try:
                    for inter in sim_inst.get_all_running_and_queued_interactions():
                        i_name = getattr(inter, "__name__", str(inter)).lower()
                        if any(h in i_name for h in ["washhand", "wash_hand", "brushtooth", "brush_teeth", "shower", "bath", "groom"]):
                            continue
                        t = getattr(inter, "target", None)
                        if t is not None and not hasattr(t, "sim_info"):
                            target_obj = t
                            break
                except Exception:
                    pass

            target_noun = "порядок"
            if target_obj:
                t_tokens = get_object_identification_tokens(target_obj)
                if any(k in t_tokens for k in ["dish", "plate", "bowl", "посуд"]):
                    target_noun = "посуду"
                elif any(k in t_tokens for k in ["trash", "rubbish", "мусор"]):
                    target_noun = "мусор"
                elif any(k in t_tokens for k in ["stove", "oven", "плит"]):
                    target_noun = "плиту"
                elif any(k in t_tokens for k in ["sink", "раковин"]):
                    target_noun = "раковину"
                elif any(k in t_tokens for k in ["toilet", "унитаз"]):
                    target_noun = "унитаз"
                elif any(k in t_tokens for k in ["shower", "душ"]):
                    target_noun = "душевую кабину"
                elif any(k in t_tokens for k in ["bath", "ванн"]):
                    target_noun = "ванну"
                elif any(k in t_tokens for k in ["counter", "тумб"]):
                    target_noun = "кухонные тумбы"
            else:
                if any(w in act_str for w in ["посуд", "dish"]):
                    target_noun = "посуду"
                elif any(w in act_str for w in ["мусор", "trash"]):
                    target_noun = "мусор"
                elif any(w in act_str for w in ["плит", "stove"]):
                    target_noun = "плиту"

            cleaner_name = s_name
            clean_other = o_name
            clean_target = target_noun
            disp = f"уборка ({target_noun})"
            if disp not in seen_names:
                seen_names.add(disp)
                dirty_names.append(disp)
            break

    # 2. Scan nearby environment for dirty objects, full trash cans, dirty dishes (within 8m)
    if services is not None:
        try:
            obj_mgr = services.object_manager()
            if obj_mgr is not None and hasattr(sim_a, "position"):
                pos_a = sim_a.position
                pos_b = getattr(sim_b, "position", pos_a)

                for obj in obj_mgr.get_all():
                    if obj is None:
                        continue
                    if getattr(obj, "is_sim", False) or getattr(obj, "is_terrain", False):
                        continue

                    o_pos = getattr(obj, "position", None)
                    if (o_pos is None or (getattr(o_pos, 'x', 0) == 0 and getattr(o_pos, 'z', 0) == 0)) and getattr(obj, "parent", None) is not None:
                        parent_pos = getattr(obj.parent, "position", None)
                        if parent_pos is not None:
                            o_pos = parent_pos
                    if o_pos is None:
                        continue

                    # Skip objects on different floors (vertical delta > 2.5m)
                    if hasattr(pos_a, "y") and hasattr(o_pos, "y"):
                        if abs(pos_a.y - o_pos.y) > 2.5 and abs(pos_b.y - o_pos.y) > 2.5:
                            continue

                    dist_sq_a = (pos_a.x - o_pos.x)**2 + (pos_a.z - o_pos.z)**2
                    dist_sq_b = (pos_b.x - o_pos.x)**2 + (pos_b.z - o_pos.z)**2
                    min_dist_sq = min(dist_sq_a, dist_sq_b)

                    # Within 8 meters
                    if min_dist_sq > 64.0:
                        continue

                    if is_object_dirty(obj):
                        d_name = get_dirty_object_display_name(obj)
                        log(f"[DIRTY OBJ DETECTED] obj={obj} def={getattr(obj, 'definition', None)} d_name='{d_name}' dist_a={dist_sq_a**0.5:.1f}m dist_b={dist_sq_b**0.5:.1f}m")
                        if d_name and d_name not in seen_names:
                            seen_names.add(d_name)
                            dirty_names.append(d_name)
        except Exception as e:
            log_exception("Error in detect_dirty_environment_in_scene scan", e)

    has_dirty = bool(dirty_names or cleaner_name)
    return has_dirty, dirty_names, cleaner_name, clean_target, clean_other


def build_dirty_environment_premise(name_a: str, name_b: str, dirty_names: List[str], cleaner_name: Optional[str], clean_target: Optional[str], clean_other: Optional[str]) -> str:
    """Creates a concise, natural, simple premise for dirty house, spoiled food, or mess."""
    if cleaner_name and clean_target:
        other = clean_other or (name_b if cleaner_name == name_a else name_a)
        return f"{cleaner_name} наводит порядок (моет {clean_target}), а {other} находится рядом."

    # Filter out active cleaning tag if present
    items = [x for x in dirty_names if not x.startswith("уборка (")]

    if not items:
        return "В доме беспорядок и накопилась грязь."

    if len(items) == 1:
        item = items[0]
        if item.startswith("тарелка с испорченной едой"):
            return f"В комнате стоит {item} с неприятным запахом."
        if item == "мусор на полу":
            return "На полу валяется неубранный мусор."
        if item == "грязные кухонные тумбы":
            return "На кухне испачканы кухонные тумбы и столешница."
        if item == "грязная кухонная плита":
            return "Кухонная плита покрыта жиром и грязью."
        return f"В доме не убрано: {item}."

    if len(items) == 2:
        items_str = f"{items[0]} и {items[1]}"
    else:
        items_str = f"{', '.join(items[:-1])} и {items[-1]}"

    return f"В доме беспорядок: вокруг {items_str}."


def is_sim_genuinely_nude(sim_info) -> bool:
    """
    Returns True if the Sim is genuinely, completely nude (WickedWhims or Vanilla TS4).
    Strictly excludes underwear, swimwear, sleepwear, and regular home clothing.
    """
    if sim_info is None or isinstance(sim_info, dict):
        return False
    try:
        # 1. WickedWhims check via TurboSim
        try:
            from turbolib2.wrappers.sim.sim import TurboSim
            ts = TurboSim(sim_info)
            if hasattr(ts, "is_nude") and ts.is_nude():
                return True
        except Exception:
            pass

        # 2. WickedWhims BodyState check (both top and bottom completely nude)
        try:
            from turbolib2.wrappers.sim.sim import TurboSim
            from wickedwhims.nudity.body.sim_body_state import get_sim_body_state, BodyState
            from turbolib2.services.cas_service import TurboBodyType
            tsim = TurboSim(sim_info)
            top_state = get_sim_body_state(tsim, TurboBodyType.UPPER_BODY)
            bottom_state = get_sim_body_state(tsim, TurboBodyType.LOWER_BODY)
            if top_state == BodyState.NUDE and bottom_state == BodyState.NUDE:
                return True
        except Exception:
            pass

        # 3. Vanilla TS4 Bathing outfit check
        if hasattr(sim_info, "get_current_outfit"):
            outfit = sim_info.get_current_outfit()
            cat = outfit[0] if isinstance(outfit, (tuple, list)) else outfit
            cat_str = str(getattr(cat, "name", cat)).upper()
            if cat_str in ("BATHING", "BATHTIME", "5") or cat == 5:
                return True

        # 4. Vanilla TS4 Naked Buffs
        for b_name in get_sim_buff_names_safe(sim_info):
            if any(k in b_name for k in ["skinnydipping", "streaking", "nude_"]):
                return True
    except Exception:
        pass
    return False


def get_sim_negative_mood_data(sim_info) -> Optional[Dict[str, str]]:
    """
    Checks if a Sim has an active negative mood (Angry, Sad, Tense, Embarrassed, Scared, Dazed, Uncomfortable, Bored).
    Returns dict with mood_key, mood_desc, label_phrase, reaction_phrase or None if mood is neutral/positive.
    """
    if sim_info is None or isinstance(sim_info, dict):
        return None
    try:
        mood_name_raw = ""
        if hasattr(sim_info, "get_mood"):
            m = sim_info.get_mood()
            if m is not None:
                mood_name_raw = getattr(m, "__name__", getattr(m, "name", str(m))).lower()

        # Check full mood string with dominant buff reason
        mood_full_desc = ""
        try:
            from ai_thought_reader.context import get_sim_mood_info
            mood_full_desc = get_sim_mood_info(sim_info, include_reason=True) or ""
        except Exception:
            pass

        # Match negative mood categories
        matched_mood = None
        for key in ["angry", "enraged", "sad", "depressed", "tense", "stressed", "embarrassed", "mortified", "scared", "terrified", "dazed", "uncomfortable", "bored"]:
            if key in mood_name_raw:
                matched_mood = key
                break

        # Fallback check from localized mood description string
        if not matched_mood and mood_full_desc:
            m_low = mood_full_desc.lower()
            if any(k in m_low for k in ["сердит", "злой", "ярост", "гнев", "angry"]):
                matched_mood = "angry"
            elif any(k in m_low for k in ["груст", "печал", "тоск", "подавлен", "sad"]):
                matched_mood = "sad"
            elif any(k in m_low for k in ["напряжен", "стресс", "выгоран", "взводе", "tense"]):
                matched_mood = "tense"
            elif any(k in m_low for k in ["смущен", "стыд", "неловк", "унижен", "embarrass"]):
                matched_mood = "embarrassed"
            elif any(k in m_low for k in ["испуган", "страх", "ужас", "паник", "scared"]):
                matched_mood = "scared"
            elif any(k in m_low for k in ["ошалев", "затормож", "dazed"]):
                matched_mood = "dazed"
            elif any(k in m_low for k in ["дискомфорт", "недомога", "uncomfortable"]):
                matched_mood = "uncomfortable"
            elif any(k in m_low for k in ["скуч", "тоск", "bored"]):
                matched_mood = "bored"

        if not matched_mood:
            return None

        # Normalize key
        norm_key = matched_mood
        if norm_key == "enraged": norm_key = "angry"
        elif norm_key == "depressed": norm_key = "sad"
        elif norm_key == "stressed": norm_key = "tense"
        elif norm_key == "mortified": norm_key = "embarrassed"
        elif norm_key == "terrified": norm_key = "scared"

        desc_to_use = mood_full_desc if mood_full_desc else norm_key.capitalize()

        labels = {
            "angry": ("злится / в ярости", "Что ты такой злой? Кто тебя взбесил?"),
            "sad": ("грустит / в подавленном состоянии", "Что случилось? Ты чего такой грустный?"),
            "tense": ("на взводе от стресса / переутомления", "Ты на взводе, сделай вдох-выдох. Что навалилось?"),
            "embarrassed": ("испытывает сильное смущение и неловкость", "Да ладно тебе, не переживай, со всеми бывает!"),
            "scared": ("сильно напуган / в тревоге", "Тихо, успокойся, я рядом. Чего ты так испугался?"),
            "dazed": ("в ошалевшем / заторможенном состоянии", "Ты в порядке? Сколько пальцев я показываю?"),
            "uncomfortable": ("испытывает сильный дискомфорт / недомогание", "Тебе нехорошо? Может, прилечь или таблетку?"),
            "bored": ("умирает от тоски и скуки", "Скучно до смерти? Давай хоть фильм включим или перекусим?"),
        }

        label_phrase, reaction_phrase = labels.get(norm_key, ("не в духе", "Что стряслось?"))

        return {
            "mood_key": norm_key,
            "mood_desc": desc_to_use,
            "label_phrase": label_phrase,
            "reaction_phrase": reaction_phrase
        }
    except Exception:
        return None


def is_fire_active_on_lot() -> bool:
    """Checks if there is an active fire on the lot via fire_service or fire objects."""
    try:
        from ai_thought_reader.context import get_fire_hazard_context
        f_ctx = get_fire_hazard_context(None)
        if f_ctx is not None:
            return True
    except Exception:
        pass
    if services is not None:
        try:
            fire_service = None
            if hasattr(services, "get_fire_service") and callable(services.get_fire_service):
                fire_service = services.get_fire_service()
            elif hasattr(services, "fire_service") and callable(services.fire_service):
                fire_service = services.fire_service()
            if fire_service:
                raw_fire = getattr(fire_service, "fire_is_active", False)
                if callable(raw_fire):
                    if raw_fire():
                        return True
                elif bool(raw_fire):
                    return True
                f_set = getattr(fire_service, "_fire_objects", None)
                if f_set and len(f_set) > 0:
                    return True
                b_set = getattr(fire_service, "_burning_objects", None)
                if b_set and len(b_set) > 0:
                    return True
                num_fires = getattr(fire_service, "number_of_fires", 0)
                if num_fires and num_fires > 0:
                    return True
        except Exception:
            pass

        try:
            obj_mgr = services.object_manager()
            if obj_mgr is not None:
                for obj in obj_mgr.values():
                    cls_name = getattr(obj, "__class__", type(obj)).__name__.lower()
                    if cls_name == "fire" or "fireobject" in cls_name:
                        return True
        except Exception:
            pass
    return False


def is_sim_reacting_to_fire(sim, sim_info, act_text: str = "") -> bool:
    """Checks if a Sim is panicking about fire, extinguishing fire, or running from fire."""
    if not sim and not sim_info:
        return False
    if any(w in act_text for w in ["пожар", "огонь", "тушит", "горит", "пламя", "огнетушител", "fire", "extinguish"]):
        return True
    try:
        for b_name in get_sim_buff_names_safe(sim_info, sim):
            if any(k in b_name for k in ["fire_panic", "recentfire", "extinguishedfire", "fire_scared"]):
                return True
    except Exception:
        pass
    try:
        if sim and hasattr(sim, "get_running_and_queued_interactions"):
            for inter in sim.get_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or "").lower()
                if any(k in aff_name for k in ["fire_panic", "react_to_fire", "extinguish_fire", "fire_extinguish", "run_away_fire"]):
                    return True
    except Exception:
        pass
    return False


def find_dying_or_dead_sim_info(sim_a=None, sim_b=None) -> Optional[Any]:
    """
    Finds the SimInfo of the Sim who recently died or is actively dying on the lot.
    Checks:
    1. Instanced Sims with is_dying flag.
    2. Interactions of Grim Reaper or participants targeting the deceased or urnstone.
    3. Urnstone / tombstone objects on the active lot.
    4. Household SimInfos with is_dead / is_ghost flag.
    5. Global SimInfoManager for deceased Sims.
    """
    if services is None:
        return None

    try:
        from ai_thought_reader.context import find_dying_or_dead_sim_info as _ctx_find
        res = _ctx_find(sim_a, sim_b)
        if res is not None:
            return res
    except Exception:
        pass

    # 1. Any instanced Sim currently dying or running death interactions
    try:
        sim_mgr = services.sim_info_manager() if hasattr(services, "sim_info_manager") else None
        if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
            for inst in sim_mgr.instanced_sims_gen():
                inf = getattr(inst, "sim_info", None)
                if not inf or is_grim_reaper(inf):
                    continue
                if getattr(inst, "is_dying", False) or getattr(inf, "is_dead", False):
                    return inf
                for inter in get_sim_interactions_safe(inst):
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff) or "").lower()
                    if (aff_name.startswith("death_") or "_death" in aff_name or aff_name.startswith("sim_death")) and not any(k in aff_name for k in ["witness", "react", "mourn", "plead"]):
                        return inf
    except Exception:
        pass

    # 2. Check running interactions of Grim Reaper, sim_a, sim_b
    actors = [sim_a, sim_b]
    reaper = get_grim_reaper_instance_on_lot()
    if reaper and reaper not in actors:
        actors.append(reaper)

    for act_sim in actors:
        if act_sim is None:
            continue
        try:
            for inter in get_sim_interactions_safe(act_sim):
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or "").lower()
                if any(k in aff_name for k in ["death", "mourn", "plead", "reap", "urn", "grave", "kill", "die"]):
                    target = getattr(inter, "target", None)
                    if target is not None:
                        t_info = getattr(target, "sim_info", target)
                        if t_info and hasattr(t_info, "first_name") and not is_grim_reaper(t_info):
                            return t_info
                        if hasattr(target, "get_stored_sim_info"):
                            st = target.get_stored_sim_info()
                            if st:
                                return st
                        for st_attr in ["dead_sim_info", "ghost_sim_info", "_stored_sim_info"]:
                            st = getattr(target, st_attr, None)
                            if st and hasattr(st, "first_name"):
                                return st
        except Exception:
            pass

    # 3. Urnstone / tombstone on active lot
    try:
        obj_mgr = services.object_manager() if hasattr(services, "object_manager") else None
        sim_mgr = services.sim_info_manager() if hasattr(services, "sim_info_manager") else None
        if obj_mgr and hasattr(obj_mgr, "objects"):
            for obj in obj_mgr.objects:
                obj_name = (getattr(obj, "__class__", type(obj)).__name__ or "").lower()
                if "urnstone" in obj_name or "tombstone" in obj_name or "grave" in obj_name or getattr(obj, "is_urnstone", False):
                    if hasattr(obj, "get_stored_sim_info"):
                        st = obj.get_stored_sim_info()
                        if st:
                            return st
                    for st_attr in ["dead_sim_info", "ghost_sim_info", "_stored_sim_info"]:
                        st = getattr(obj, st_attr, None)
                        if st and hasattr(st, "first_name"):
                            return st
                    if hasattr(obj, "get_target_sim_id") and sim_mgr:
                        t_id = obj.get_target_sim_id()
                        if t_id:
                            st = sim_mgr.get(t_id)
                            if st:
                                return st
    except Exception:
        pass

    # 4. Household members with is_dead / is_ghost
    try:
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        hh = getattr(client, "household", None) if client else None
        if hh and hasattr(hh, "sim_info_gen"):
            for h_info in hh.sim_info_gen():
                if (getattr(h_info, "is_dead", False) or getattr(h_info, "is_ghost", False)) and not is_grim_reaper(h_info):
                    return h_info
    except Exception:
        pass

    # 5. Global sim_info_manager deceased Sims
    try:
        sim_mgr = services.sim_info_manager() if hasattr(services, "sim_info_manager") else None
        if sim_mgr and hasattr(sim_mgr, "get_all"):
            for s_info in sim_mgr.get_all():
                if getattr(s_info, "is_dead", False) and not is_grim_reaper(s_info):
                    return s_info
    except Exception:
        pass

    return None


def get_dead_sim_kinship_label(survivor_info, dead_info) -> Optional[str]:
    """
    Returns the Russian kinship label of the dead Sim relative to the survivor Sim
    (e.g. 'мать', 'отец', 'муж', 'жена', 'сын', 'дочь', 'сестра', 'брат').
    If the deceased is NOT a relative (friend, acquaintance, colleague, stranger), returns None.
    """
    if survivor_info is None or dead_info is None:
        return None
    try:
        from ai_thought_reader.context import get_relationship_between_sims
        rel_str = (get_relationship_between_sims(survivor_info, dead_info) or "").strip().lower()
    except Exception:
        rel_str = ""

    if not rel_str:
        return None

    kinship_terms = [
        ("мачех", "мачеха"),
        ("отчим", "отчим"),
        ("падчериц", "падчерица"),
        ("пасынок", "пасынок"),
        ("сводная сестра", "сводная сестра"),
        ("сводный брат", "сводный брат"),
        ("двоюродная сестра", "двоюродная сестра"),
        ("двоюродный брат", "двоюродный брат"),
        ("бабушк", "бабушка"),
        ("дедушк", "дедушка"),
        ("внучк", "внучка"),
        ("внук", "внук"),
        ("тёщ", "тёща"),
        ("тест", "тесть"),
        ("свекров", "свекровь"),
        ("свёкор", "свёкор"),
        ("невестк", "невестка"),
        ("снох", "сноха"),
        ("зят", "зять"),
        ("шурин", "шурин"),
        ("золовк", "золовка"),
        ("девер", "деверь"),
        ("своячениц", "свояченица"),
        ("племянниц", "племянница"),
        ("племянник", "племянник"),
        ("тёт", "тётя"),
        ("тет", "тётя"),
        ("дяд", "дядя"),
        ("мать", "мать"),
        ("мам", "мать"),
        ("отец", "отец"),
        ("пап", "отец"),
        ("жен", "жена"),
        ("супруг", "супруга" if "супруга" in rel_str else "супруг"),
        ("муж", "муж"),
        ("доч", "дочь"),
        ("сын", "сын"),
        ("сестр", "сестра"),
        ("брат", "брат"),
        ("родственниц", "родственница"),
        ("родственник", "родственник"),
    ]

    for stem, label in kinship_terms:
        if stem in rel_str:
            return label

    return None


def build_dead_sim_description(dead_info, witness_a_info, witness_b_info=None) -> str:
    """
    Builds the formatted description of the deceased Sim for the Director premise.
    If the deceased is a relative, appends kinship (e.g. 'Анна (мать)').
    If not a relative, outputs only the name (e.g. 'Анна').
    """
    dead_name = getattr(dead_info, "first_name", "") if dead_info else ""
    if not dead_name:
        return "близкого"

    k_a = get_dead_sim_kinship_label(witness_a_info, dead_info) if witness_a_info else None
    k_b = get_dead_sim_kinship_label(witness_b_info, dead_info) if witness_b_info else None

    # Single witness or witness B is Grim Reaper
    if witness_b_info is None or is_grim_reaper(witness_b_info):
        if k_a:
            return f"{dead_name} ({k_a})"
        return dead_name

    name_a = getattr(witness_a_info, "first_name", "Сим")
    name_b = getattr(witness_b_info, "first_name", "Сим")

    # Both witnesses are relatives with identical kinship
    if k_a and k_b:
        if k_a == k_b:
            return f"{dead_name} ({k_a})"
        return f"{dead_name} ({k_a} для {name_a}, {k_b} для {name_b})"

    # Only witness A is relative
    if k_a:
        return f"{dead_name} ({k_a} для {name_a})"

    # Only witness B is relative
    if k_b:
        return f"{dead_name} ({k_b} для {name_b})"

    # Neither is relative
    return dead_name


def is_sim_actively_dying(sim_or_info) -> bool:
    """
    Returns True if the given Sim is actively dying on the lot.
    """
    if sim_or_info is None or is_grim_reaper(sim_or_info):
        return False
    inf = getattr(sim_or_info, "sim_info", sim_or_info)
    inst = getattr(inf, "get_sim_instance", lambda: None)() if hasattr(inf, "get_sim_instance") else (sim_or_info if hasattr(sim_or_info, "get_all_running_and_queued_interactions") else None)
    if getattr(inf, "is_dying", False) or (inst is not None and getattr(inst, "is_dying", False)):
        return True
    if inst is not None:
        for inter in get_sim_interactions_safe(inst):
            aff = getattr(inter, "affordance", None)
            aff_name = (getattr(aff, "__name__", "") or str(aff) or "").lower()
            if (aff_name.startswith("death_") or "_death" in aff_name or aff_name.startswith("sim_death")) and not any(k in aff_name for k in ["witness", "react", "mourn", "plead", "reap", "reaper", "grim"]):
                return True
    return False


def find_active_dying_sim_and_instance_on_lot() -> Tuple[Optional[Any], Optional[Any]]:
    """
    Finds the instanced Sim on the active lot who is actively dying right now.
    Returns (sim_info, sim_instance) or (None, None).
    """
    if services is None or not hasattr(services, "sim_info_manager"):
        return None, None
    try:
        sim_mgr = services.sim_info_manager()
        if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
            for inst in sim_mgr.instanced_sims_gen():
                inf = getattr(inst, "sim_info", None)
                if not inf or is_grim_reaper(inf):
                    continue
                if is_sim_actively_dying(inst):
                    return inf, inst
    except Exception:
        pass
    return None, None


def find_best_survivor_for_dying_sim(dying_info, dying_inst) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Scans all living instanced Sims on the lot and finds the best emotional partner
    (closest relative, spouse, lover, or best friend) to say their final farewell to the dying Sim.
    Returns (survivor_info, survivor_instance) or (None, None).
    """
    if services is None or not hasattr(services, "sim_info_manager"):
        return None, None

    dying_pos = getattr(dying_inst, "position", None)
    candidates = []

    try:
        sim_mgr = services.sim_info_manager()
        if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
            for inst in sim_mgr.instanced_sims_gen():
                if inst is dying_inst:
                    continue
                inf = getattr(inst, "sim_info", None)
                if not inf or is_grim_reaper(inf) or getattr(inf, "is_pet", False):
                    continue
                if getattr(inst, "is_dying", False) or getattr(inf, "is_dead", False):
                    continue
                if not is_sim_on_or_near_active_lot(inst):
                    continue

                # Distance calculation
                dist = 0.0
                inst_pos = getattr(inst, "position", None)
                if dying_pos is not None and inst_pos is not None:
                    try:
                        dist = (dying_pos - inst_pos).magnitude()
                    except Exception:
                        dist = 10.0

                # Score by relationship closeness
                score = 0
                kinship = get_dead_sim_kinship_label(inf, dying_info)
                if kinship in ("муж", "жена", "супруг", "супруга", "жених", "невеста", "парень", "девушка", "возлюбленный", "возлюбленная"):
                    score += 10000
                elif kinship in ("сын", "дочь", "мать", "отец", "брат", "сестра"):
                    score += 5000
                elif kinship:
                    score += 2500

                # Check relationship score
                rt = getattr(inf, "relationship_tracker", None)
                if rt is not None and hasattr(rt, "get_relationship_score"):
                    try:
                        rel_score = rt.get_relationship_score(getattr(dying_info, "sim_id", 0))
                        score += int(rel_score * 10)
                    except Exception:
                        pass

                # Proximity bonus (closer Sims hear/see better)
                score -= int(dist * 5)
                candidates.append((score, inf, inst))
    except Exception:
        pass

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_inf, best_inst = candidates[0]
    return best_inf, best_inst


def create_dying_farewell_spark(dying_inst, survivor_inst, dying_info, survivor_info, daily_key: str) -> Optional[Dict[str, Any]]:
    """
    Creates the emergency farewell spark between the dying Sim and their closest loved one.
    """
    s_name = getattr(survivor_info, "first_name", "Сим")
    d_name = getattr(dying_info, "first_name", "Сим")
    kinship = get_dead_sim_kinship_label(survivor_info, dying_info)
    kin_desc = f" ({kinship})" if kinship else ""

    premise = (
        f"{d_name}{kin_desc} погибает прямо сейчас на глазах у {s_name}. "
        f"Это их последний диалог перед смертью: {d_name} говорит слабым угасающим голосом (...), "
        f"а реакция и слова {s_name} зависят от их отношений и характеров."
    )

    return {
        "trigger_type": "witness_death",
        "priority": 100,
        "premise": premise,
        "participants": [dying_info, survivor_info],
        "daily_key": daily_key,
        "dying_sim_id": getattr(dying_info, "sim_id", 0),
        "survivor_sim_id": getattr(survivor_info, "sim_id", 0),
    }


def detect_death_or_reaper_in_scene(sim_a, sim_b, info_a, info_b, act_a: str = "", act_b: str = "") -> Optional[Tuple[str, str]]:
    """
    Checks if a death has just occurred, a Sim is dying, an urnstone is present,
    or the Grim Reaper is instantiated on the lot.
    Returns (dead_or_reaper_name, detail_desc) or None.
    """
    # 1. Direct Grim Reaper check on participants
    if is_grim_reaper(info_a) or is_grim_reaper(info_b):
        return ("Костлявая Смерть", "прибытие Костлявой Смерти на участок")

    # 2. Lot-wide Grim Reaper instance
    reaper = get_grim_reaper_instance_on_lot()
    if reaper is not None:
        return ("Костлявая Смерть", "прибытие Костлявой Смерти на участок")

    # 3. Lot-wide dying or deceased Sim
    dead_sim = find_dying_or_dead_sim_info(sim_a, sim_b)
    if dead_sim is not None:
        d_name = getattr(dead_sim, "first_name", "персонаж")
        return (d_name, f"гибель персонажа ({d_name})")

    # 4. Check participants' activities, buffs, and running interactions
    death_keywords = ["смерт", "жнец", "оплакива", "молить о пощаде", "урна", "надгроби", "mourn", "grim", "reaper", "witness_death", "погиб", "умира", "утрата", "скорб"]
    death_buff_keys = ["witnesseddeath", "witness_death", "mourning", "grimreaper", "urnstone", "bereavement", "grief", "sad_death", "loss_of_loved_one"]
    death_aff_keys = ["witness_death", "mourn", "plead_with_death", "death_", "react_to_death", "be_mourned", "die_"]

    for s, inf, act in [(sim_a, info_a, act_a), (sim_b, info_b, act_b)]:
        if act and any(w in act.lower() for w in death_keywords):
            return ("погибший близкий", "трагедию и потерю")
        
        for b_name in get_sim_buff_names_safe(inf):
            if any(k in b_name for k in death_buff_keys):
                return ("погибший близкий", "траур и скорбь")
        
        for inter in get_sim_interactions_safe(s):
            aff = getattr(inter, "affordance", None)
            aff_name = (getattr(aff, "__name__", "") or str(aff) or "").lower()
            if any(k in aff_name for k in death_aff_keys):
                return ("погибший близкий", "трагедию и потерю")

    # 5. Urnstone / tombstone on active lot
    try:
        obj_mgr = services.object_manager() if hasattr(services, "object_manager") else None
        if obj_mgr and hasattr(obj_mgr, "objects"):
            for obj in obj_mgr.objects:
                obj_name = (getattr(obj, "__class__", type(obj)).__name__ or "").lower()
                if "urnstone" in obj_name or "tombstone" in obj_name or "grave" in obj_name or getattr(obj, "is_urnstone", False):
                    return ("погибший персонаж", "скорбь у надгробия")
    except Exception:
        pass

    return None


def is_sim_in_labor(sim, sim_info, act_text: str = "") -> bool:
    """Checks if a Sim is actively in labor / having contractions."""
    if not sim_info and not sim:
        return False

    # 1. Action / interaction text
    if any(w in (act_text or "").lower() for w in ["рожает", "схватки", "роды", "labor", "childbirth"]):
        return True

    # 2. Check via is_sim_in_labor_state or get_sim_pregnancy_info
    try:
        from ai_thought_reader.context import is_sim_in_labor_state, get_sim_pregnancy_info
        if is_sim_in_labor_state(sim_info, sim, act_text):
            return True
        p_text = (get_sim_pregnancy_info(sim_info) or "").lower()
        if any(w in p_text for w in ["схватки", "роды начались", "in labor"]):
            return True
    except Exception:
        pass

    # 3. Comprehensive buff scan via get_sim_buff_names_safe
    try:
        labor_buff_keys = [
            "inlabor", "in_labor", "labor_contractions", "givingbirth",
            "childbirth", "12564", "buff_pregnancy_inlabor",
            "early_labor", "active_labor", "pushing_labor", "transition_labor"
        ]
        for b_name in get_sim_buff_names_safe(sim_info, sim):
            if any(k in b_name for k in labor_buff_keys):
                return True
            if "labor" in b_name and any(k in b_name for k in ["pregnan", "birth", "baby", "delivery", "contractions"]):
                return True
            if "labor" in b_name and getattr(sim_info, "is_pregnant", False):
                return True
    except Exception:
        pass

    # 4. Pregnancy Tracker & Progress
    try:
        p_tracker = getattr(sim_info, "pregnancy_tracker", None)
        if p_tracker is not None:
            for m_name in ("is_in_labor", "in_labor"):
                m = getattr(p_tracker, m_name, None)
                if callable(m):
                    try:
                        if m():
                            return True
                    except Exception:
                        pass
                elif isinstance(m, bool) and m:
                    return True

            is_preg = getattr(sim_info, "is_pregnant", False) or getattr(p_tracker, "is_pregnant", False)
            if is_preg:
                prog = getattr(sim_info, "pregnancy_progress", 0.0)
                if not prog and hasattr(p_tracker, "get_pregnancy_progress"):
                    try:
                        prog = p_tracker.get_pregnancy_progress()
                    except Exception:
                        pass
                if prog is not None and float(prog) >= 0.99:
                    return True
    except Exception:
        pass

    # 5. Running or queued interactions
    try:
        s_inst = sim or (getattr(sim_info, "get_sim_instance", lambda: None)() if sim_info else None)
        if s_inst and hasattr(s_inst, "get_running_and_queued_interactions"):
            for inter in s_inst.get_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff) or "").lower()
                if any(k in aff_name for k in ["give_birth", "labor", "have_baby", "go_to_hospital", "have_baby_at_hospital", "deliver_baby"]):
                    return True
    except Exception:
        pass

    return False


def is_sim_electrocuted(sim, sim_info, act_text: str = "") -> bool:
    """Checks if a Sim has an active electrocuted / singed buff or dazed state from electricity."""
    if not sim_info and not sim:
        return False
    if any(w in (act_text or "").lower() for w in ["удар током", "опален", "electrocute", "ударило током"]):
        return True
    try:
        for b_name in get_sim_buff_names_safe(sim_info, sim):
            if any(k in b_name for k in ["electrocute", "singed", "electric_shock", "shocked_electricity"]):
                return True
        if getattr(sim_info, "is_singed", False) or (sim and getattr(sim, "is_singed", False)):
            return True
    except Exception:
        pass
    return False


def is_sim_in_romantic_relationship(info_1, info_2) -> bool:
    """
    Checks if two Sims are in a committed romantic relationship (Spouse, Fiancé, Steady Boyfriend/Girlfriend).
    STRICTLY EXCLUDES mistresses, casual affairs, and flings!
    """
    if not info_1 or not info_2:
        return False
    s1_id = getattr(info_1, "sim_id", 0)
    s2_id = getattr(info_2, "sim_id", 0)
    if not s1_id or not s2_id or s1_id == s2_id:
        return False

    # 1. Direct spouse_sim_id on SimInfo (Absolute Top Priority!)
    if getattr(info_1, "spouse_sim_id", None) == s2_id or getattr(info_2, "spouse_sim_id", None) == s1_id:
        return True

    # 2. Direct fiance_sim_id on SimInfo
    if getattr(info_1, "fiance_sim_id", None) == s2_id or getattr(info_2, "fiance_sim_id", None) == s1_id:
        return True

    # If either Sim is married to SOMEONE ELSE, they CANNOT be in a legitimate committed relationship with this Sim!
    # (The other person is a mistress/lover, not the committed partner who gets cheated on!)
    sp1 = getattr(info_1, "spouse_sim_id", 0)
    sp2 = getattr(info_2, "spouse_sim_id", 0)
    if (sp1 and sp1 != s2_id) or (sp2 and sp2 != s1_id):
        return False

    # 3. Authoritative context relationship detection
    try:
        from ai_thought_reader.context import get_relationship_between_sims
        rel_str = (get_relationship_between_sims(info_1, info_2) or "").lower()

        # Hard reject mistresses, affairs, side flings!
        if any(bad in rel_str for bad in ["любовниц", "любовник", "интрижк", "измена", "стороне", "affair", "cheating", "fling"]):
            return False

        if any(k in rel_str for k in [
            "муж", "жена", "супруг", "невест", "жених",
            "парень", "девушка", "spouse", "married", "engaged", "fiance", "boyfriend", "girlfriend",
            "partner", "sweetheart"
        ]):
            return True
    except Exception:
        pass

    # 4. Relationship Tracker bits (must be strictly committed bits, not casual/affair)
    try:
        rt = getattr(info_1, "relationship_tracker", None)
        if rt and hasattr(rt, "get_all_bits"):
            bits = rt.get_all_bits(s2_id) or []
            for b in bits:
                b_name = getattr(b, "__name__", str(b)).lower()
                b_cls = getattr(getattr(b, "__class__", None), "__name__", "").lower()
                combined = f"{b_name} {b_cls}"
                # Reject affair/lovers bits
                if any(bad in combined for bad in ["affair", "cheating", "fling"]):
                    return False
                if any(k in combined for k in [
                    "spouse", "married", "engaged", "significantother", "significant_other",
                    "sweethearts", "boyfriend_girlfriend"
                ]):
                    return True
    except Exception:
        pass

    return False


def find_all_committed_partners(sim_info) -> List[Any]:
    """
    Finds all committed romantic partners of sim_info (spouses, fiancés, steady boyfriends/girlfriends).
    Supports polyamory and multiple partners. Strictly excludes divorced exes or casual affairs.
    """
    if sim_info is None or services is None:
        return []
    s_id = getattr(sim_info, "sim_id", 0)
    sim_mgr = getattr(services, "sim_info_manager", lambda: None)()
    if not sim_mgr or not s_id:
        return []

    partners = []
    seen_ids = set()

    # 1. Direct spouse_sim_id
    sp_id = getattr(sim_info, "spouse_sim_id", 0)
    if sp_id and sp_id != s_id:
        sp_inf = sim_mgr.get(sp_id)
        if sp_inf and is_sim_in_romantic_relationship(sim_info, sp_inf):
            partners.append(sp_inf)
            seen_ids.add(sp_id)

    # 2. Direct fiance_sim_id
    fi_id = getattr(sim_info, "fiance_sim_id", 0)
    if fi_id and fi_id != s_id and fi_id not in seen_ids:
        fi_inf = sim_mgr.get(fi_id)
        if fi_inf and is_sim_in_romantic_relationship(sim_info, fi_inf):
            partners.append(fi_inf)
            seen_ids.add(fi_id)

    # 3. Check household and lot Sims
    try:
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        hh = getattr(client, "household", None) if client else None
        if hh:
            for cand in hh.sim_info_gen():
                c_id = getattr(cand, "sim_id", 0)
                if c_id and c_id != s_id and c_id not in seen_ids and is_sim_in_romantic_relationship(sim_info, cand):
                    partners.append(cand)
                    seen_ids.add(c_id)

        for cand in sim_mgr.get_all():
            c_id = getattr(cand, "sim_id", 0)
            if c_id and c_id != s_id and c_id not in seen_ids and is_sim_in_romantic_relationship(sim_info, cand):
                partners.append(cand)
                seen_ids.add(c_id)
    except Exception:
        pass

    return partners


def find_sim_committed_partner(sim_info) -> Optional[Any]:
    """Returns the first committed partner, or None."""
    parts = find_all_committed_partners(sim_info)
    return parts[0] if parts else None


def is_polyamorous_or_exempt_from_cheating(cheater_info, partner_info, lover_info=None) -> bool:
    """
    Returns True if romantic/intimate interaction between cheater_info and lover_info
    is NOT considered cheating against partner_info due to:
    1. lover_info is already a committed partner of cheater_info or partner_info (polyamorous union).
    2. cheater_info or partner_info has polyamorous / non-jealous / player traits (WW, RPO, EA Player trait).
    3. Open relationship boundaries (Lovestruck Romantic Boundaries / relationship bits).
    """
    if not cheater_info or not partner_info:
        return False

    try:
        # 1. Check if lover_info is already a recognized committed partner
        if lover_info is not None:
            l_id = getattr(lover_info, "sim_id", 0)
            if l_id:
                cheater_partner_ids = {getattr(p, "sim_id", 0) for p in find_all_committed_partners(cheater_info)}
                partner_partner_ids = {getattr(p, "sim_id", 0) for p in find_all_committed_partners(partner_info)}
                if l_id in cheater_partner_ids or l_id in partner_partner_ids:
                    return True

        # 2. Check polyamory / non-jealousy traits on either partner or cheater
        POLY_TRAITS = (
            "trait_player", "player", "polyamorous", "polyamory",
            "non_jealous", "no_jealousy", "not_jealous", "unjealous",
            "open_relationship", "free_love", "ww_polyamorous",
            "wicked_polyamorous", "rpo_openrelationship", "rpo_nonmonogamous"
        )
        for inf in (partner_info, cheater_info):
            t_tracker = getattr(inf, "trait_tracker", None)
            if t_tracker:
                traits = getattr(t_tracker, "equipped_traits", None) or getattr(t_tracker, "_equipped_traits", ())
                for tr in traits:
                    tr_name = (getattr(tr, "__name__", "") or str(tr)).lower()
                    if any(pt in tr_name for pt in POLY_TRAITS):
                        return True

        # 3. Check open relationship bits between cheater and partner
        OPEN_BITS = (
            "open_relationship", "polyamorous", "noboundaries", "no_jealousy",
            "boundaries_none", "jealousy_off", "romanticboundaries_open",
            "boundary_physical_open", "boundary_nonphysical_open", "boundary_woohoo_open"
        )
        p_id = getattr(partner_info, "sim_id", 0)
        rel_tracker = getattr(cheater_info, "relationship_tracker", None)
        if rel_tracker and p_id and hasattr(rel_tracker, "get_all_bits"):
            for bit in (rel_tracker.get_all_bits(p_id) or ()):
                b_name = (getattr(bit, "__name__", "") or str(bit)).lower()
                if any(ob in b_name for ob in OPEN_BITS):
                    return True
    except Exception:
        pass

    return False


def get_sim_kinship_or_role_label(sim_info, target_info) -> str:
    """
    Returns the role/kinship of sim_info relative to target_info in Russian
    (e.g. 'дочь', 'сын', 'мать', 'отец', 'сестра', 'брат', 'лучший друг', 'друг', 'знакомый').
    """
    if not sim_info or not target_info:
        return "знакомый"
    try:
        from ai_thought_reader.context import get_relationship_between_sims
        rel_str = (get_relationship_between_sims(sim_info, target_info) or "").strip().lower()
    except Exception:
        rel_str = ""

    if not rel_str:
        return "знакомый"

    # 1. Family / Kinship terms
    kin = get_dead_sim_kinship_label(sim_info, target_info)
    if kin:
        return kin

    is_male = getattr(getattr(sim_info, "gender", None), "name", "MALE") == "MALE"
    # 2. Friends / Social terms
    if "лучш" in rel_str and "друг" in rel_str:
        return "лучший друг" if is_male else "лучшая подруга"
    if "хорош" in rel_str and "друг" in rel_str:
        return "хороший друг" if is_male else "хорошая подруга"
    if "друг" in rel_str or "подруг" in rel_str:
        return "друг" if is_male else "подруга"
    if "приятел" in rel_str:
        return "приятель"
    if "коллег" in rel_str:
        return "коллега"
    if "сосед" in rel_str:
        return "сосед по дому"

    return rel_str


def get_sim_relationship_scores(sim_info, target_info) -> Tuple[int, int]:
    """Returns (friendship_score, romance_score) between sim_info and target_info as integers."""
    if not sim_info or not target_info:
        return 0, 0
    t_id = getattr(target_info, "sim_id", 0)
    if not t_id:
        return 0, 0
    fr, rom = 0, 0
    try:
        rt = getattr(sim_info, "relationship_tracker", None)
        if rt and hasattr(rt, "get_relationship_score"):
            fr = int(rt.get_relationship_score(t_id) or 0)
            rel = rt.get_relationship(t_id) if hasattr(rt, "get_relationship") else None
            if rel and hasattr(rel, "relationship_tracks"):
                for track in rel.relationship_tracks.values():
                    t_name = getattr(getattr(track, "stat_type", None), "__name__", "").lower()
                    if "romance" in t_name:
                        rom = int(track.get_value() or 0)
                        break
    except Exception:
        pass
    return fr, rom


def get_sim_sentiments_summary(sim_info, target_info) -> str:
    """Returns active sentiments (e.g. 'обида', 'обожание', 'гнев', 'близость') from sim_info towards target_info."""
    if not sim_info or not target_info:
        return "нейтральные"
    t_id = getattr(target_info, "sim_id", 0)
    if not t_id:
        return "нейтральные"
    sentiments = []
    try:
        rt = getattr(sim_info, "relationship_tracker", None)
        if rt and hasattr(rt, "get_all_bits"):
            for b in rt.get_all_bits(t_id) or []:
                b_name = getattr(b, "__name__", str(b)).lower()
                b_cls = getattr(getattr(b, "__class__", None), "__name__", "").lower()
                comb = f"{b_name} {b_cls}"
                if "sentiment" in comb:
                    s_label = ""
                    if any(k in comb for k in ["bitter", "hurt", "resentful"]):
                        s_label = "обида / горечь"
                    elif any(k in comb for k in ["furious", "angry"]):
                        s_label = "ярость / гнев"
                    elif any(k in comb for k in ["adoring", "adore"]):
                        s_label = "обожание"
                    elif any(k in comb for k in ["enamored", "infatuated"]):
                        s_label = "влюбленность"
                    elif any(k in comb for k in ["close", "bonding"]):
                        s_label = "душевная близость"
                    elif any(k in comb for k in ["guilty"]):
                        s_label = "чувство вины"
                    elif any(k in comb for k in ["impressed"]):
                        s_label = "восхищение"
                    else:
                        s_label = b_name.replace("sentiment_", "").replace("bit_", "").replace("_", " ")
                    if s_label and s_label not in sentiments:
                        sentiments.append(s_label)
    except Exception:
        pass
    return ", ".join(sentiments[:3]) if sentiments else "нейтральные"


def is_affordance_strictly_romantic(inter, aff) -> bool:
    """
    Ensures interaction is STRICTLY romantic (flirt, kiss, woohoo, etc.)
    and NEVER friendly, familial, funny, or neutral (e.g. friendly hugs, greeting hugs, comfort embraces).
    """
    if not aff and not inter:
        return False
    aff_name = (getattr(aff, "__name__", "") or "").lower()

    # 1. HARD EXCLUSIONS: Any friendly, platonic, family, prank, or neutral tags/keywords
    friendly_blacklist = [
        "friendly", "platonic", "family", "greeting", "farewell",
        "comfort", "consol", "bro_", "buddy", "handshake", "highfive",
        "chat", "talk", "discuss", "joke", "funny", "mischief", "fight",
        "argue", "apologiz", "cheer_up", "calm_down", "deep_conversation",
        "share_ideas", "ask_about", "tell_story", "group_hug", "friendly_hug"
    ]
    if any(fk in aff_name for fk in friendly_blacklist):
        return False

    # 2. Check if interaction itself or affordance reports is_romantic
    try:
        if getattr(inter, "is_romantic", False) or getattr(aff, "is_romantic", False):
            return True
    except Exception:
        pass

    try:
        tags = getattr(aff, "tags", None) or getattr(aff, "interaction_tags", None)
        if tags:
            for t in tags:
                t_str = str(t).lower()
                if "friendly" in t_str or "family" in t_str:
                    return False
                if "romance" in t_str or "romantic" in t_str or "flirt" in t_str:
                    return True
    except Exception:
        pass

    # 3. Explicit strictly romantic keywords in affordance name
    # Notice: For hugs/embraces, we require EXPLICIT romantic qualifiers (e.g. "romantic_hug", "flirty_hug")
    strict_romance_keywords = [
        "romance", "flirt", "kiss", "makeout", "blowkiss",
        "woohoo", "mess_around", "holdhands", "whisper_romantic",
        "confess_feelings", "massageneck", "massageshoulders",
        "smooch", "steamy", "passion", "seduce", "tryforbaby",
        "serenade", "make_move", "pickup_line", "give_rose",
        "romantic_cuddle", "cuddle_romantic", "flirty_cuddle",
        "romantic_hug", "hug_romantic", "flirty_hug",
        "romantic_embrace", "embrace_romantic", "flirty_embrace"
    ]
    if any(rk in aff_name for rk in strict_romance_keywords):
        return True

    # 4. WickedWhims / Intimacy support
    if any(wk in aff_name for wk in ["ww_sex", "ww_tease", "wickedwhims_sex", "wickedwhims_intimacy", "ww_kiss"]):
        return True

    return False


def record_sim_romance_action(sim_id_a: int, sim_id_b: int, affordance_name: str = "romance_action"):
    """
    Directly called when relationship romance score increases or romance interaction occurs.
    Records both sims in _sim_recent_romance_tracker with current Sim time.
    """
    if not sim_id_a or not sim_id_b or sim_id_a == sim_id_b:
        return
    now = get_sim_now()
    if now is None:
        return
    sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
    if not sim_mgr:
        return
    info_a = sim_mgr.get(sim_id_a)
    info_b = sim_mgr.get(sim_id_b)
    if info_a and info_b:
        _sim_recent_romance_tracker[sim_id_a] = {
            "timestamp": now,
            "target_info": info_b,
            "target_id": sim_id_b,
            "affordance_name": affordance_name
        }
        _sim_recent_romance_tracker[sim_id_b] = {
            "timestamp": now,
            "target_info": info_a,
            "target_id": sim_id_a,
            "affordance_name": affordance_name
        }


def get_sim_cheating_action_verb(affordance_name: str = "", cheater_info=None) -> str:
    """
    Returns 'обнял', 'поцеловал', or 'флиртовал' (with gender awareness).
    If the game does not know the exact action, defaults to 'флиртовал' / 'флиртовала'.
    """
    is_fem = False
    if cheater_info:
        gender_attr = getattr(cheater_info, "gender", None)
        g_name = getattr(gender_attr, "name", str(gender_attr)).upper()
        is_fem = (g_name == "FEMALE")

    aff_raw = (affordance_name or "").lower()

    # 1. Поцелуй
    if any(k in aff_raw for k in ["kiss", "makeout", "make_out", "peck", "smooch", "blowkiss", "blow_kiss", "firstkiss"]):
        return "поцеловала" if is_fem else "поцеловал"

    # 2. Объятия
    if any(k in aff_raw for k in ["hug", "embrace", "cuddle", "holdhands", "hold_hands", "caress"]):
        return "обняла" if is_fem else "обнял"

    # 3. Флирт (или если действие неизвестно)
    return "флиртовала" if is_fem else "флиртовал"


def get_sim_romantic_target(sim, sim_info, partner_info=None) -> Tuple[Optional[Any], str]:
    """
    Checks if sim is currently running an active strictly romantic interaction with another Sim,
    OR performed a strictly romantic action within the last 8 Sim minutes (ROMANCE_CHEATING_WINDOW_MINUTES),
    OR partner just reacted with jealousy/boundaries violation buff or event memory.
    Returns (target_info, action_verb) where action_verb is 'обнял', 'поцеловал', or 'флиртовал'.
    If not found, returns (None, 'флиртовал').
    """
    if not sim_info:
        return None, "флиртовал"
    s_id = getattr(sim_info, "sim_id", 0)
    p_id = getattr(partner_info, "sim_id", 0) if partner_info else 0
    now = get_sim_now()

    if not sim and hasattr(sim_info, "get_sim_instance"):
        try:
            sim = sim_info.get_sim_instance()
        except Exception:
            sim = None

    # 1. First check active running interactions (instant detection)
    if sim and hasattr(sim, "get_running_and_queued_interactions"):
        try:
            for inter in sim.get_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                if is_affordance_strictly_romantic(inter, aff):
                    target = getattr(inter, "target", None)
                    t_info = getattr(target, "sim_info", target) if target else None
                    if not t_info and hasattr(inter, "get_participants"):
                        try:
                            from interactions import ParticipantType
                            for p in inter.get_participants(ParticipantType.TargetSim):
                                if p and p != sim:
                                    t_info = getattr(p, "sim_info", p)
                                    break
                        except Exception:
                            pass
                    t_id = getattr(t_info, "sim_id", 0) if t_info else 0
                    if t_info and t_id != s_id and (not p_id or t_id != p_id):
                        if partner_info and is_polyamorous_or_exempt_from_cheating(sim_info, partner_info, t_info):
                            continue
                        act_name = getattr(aff, "__name__", "")
                        verb = get_sim_cheating_action_verb(act_name, sim_info)
                        if now is not None and s_id:
                            _sim_recent_romance_tracker[s_id] = {
                                "timestamp": now,
                                "target_info": t_info,
                                "target_id": t_id,
                                "affordance_name": act_name
                            }
                        return t_info, verb
        except Exception:
            pass

    # 2. Check 8-sim-minute tracker window (direct cheater entry)
    if s_id in _sim_recent_romance_tracker and now is not None:
        data = _sim_recent_romance_tracker[s_id]
        t_stamp = data.get("timestamp")
        t_info = data.get("target_info")
        t_id = data.get("target_id") or getattr(t_info, "sim_id", 0)
        if t_stamp is not None and (not p_id or t_id != p_id):
            mins = get_sim_minutes_between(t_stamp, now)
            if mins is not None and mins <= ROMANCE_CHEATING_WINDOW_MINUTES:
                if not (partner_info and is_polyamorous_or_exempt_from_cheating(sim_info, partner_info, t_info)):
                    act_name = data.get("affordance_name", "")
                    verb = get_sim_cheating_action_verb(act_name, sim_info)
                    return t_info, verb
            else:
                _sim_recent_romance_tracker.pop(s_id, None)

    # 3. Check 8-sim-minute tracker reverse lookup (someone else flirted with cheater)
    if now is not None:
        for other_id, data in list(_sim_recent_romance_tracker.items()):
            if other_id == s_id or other_id == p_id:
                continue
            if data.get("target_id") == s_id:
                t_stamp = data.get("timestamp")
                if t_stamp is not None:
                    mins = get_sim_minutes_between(t_stamp, now)
                    if mins is not None and mins <= ROMANCE_CHEATING_WINDOW_MINUTES:
                        sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
                        lover = sim_mgr.get(other_id) if sim_mgr else data.get("target_info")
                        if partner_info and is_polyamorous_or_exempt_from_cheating(sim_info, partner_info, lover):
                            continue
                        act_name = data.get("affordance_name", "")
                        verb = get_sim_cheating_action_verb(act_name, sim_info)
                        return lover, verb

    # 4. Check active event memories from event_memory_manager
    try:
        from ai_social_pc.event_memory_manager import get_active_memories
        sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
        if p_id and s_id:
            for mem in get_active_memories(p_id, s_id) + get_active_memories(s_id, p_id):
                ev = mem.get("event_type", "")
                if ev in ("romance_cheating_caught", "romance_cheating_flirter", "cheating_caught", "cheating_caught_cheater"):
                    lover_id = mem.get("lover_sim_id") or mem.get("extra_context", {}).get("lover_sim_id")
                    if lover_id and sim_mgr:
                        l_inf = sim_mgr.get(lover_id)
                        if l_inf and not (partner_info and is_polyamorous_or_exempt_from_cheating(sim_info, partner_info, l_inf)):
                            verb = get_sim_cheating_action_verb("flirt", sim_info)
                            return l_inf, verb
    except Exception:
        pass

    # 5. Check partner jealousy / boundaries crossed buff or sentiment
    # In TS4 Lovestruck and base game, when a partner witnesses a boundary breach / cheating,
    # a buff is attached to the partner (e.g. buff_RelationshipBoundaries..., buff_Jealousy..., buff_cheatingwitnessed)
    if partner_info:
        try:
            partner_buffs = get_sim_buff_names_safe(partner_info)
            JEALOUS_TRIGGERS = [
                "boundary", "boundaries", "relationshipboundaries",
                "jealousy", "jealous", "cheatingwitnessed", "witness_cheating",
                "flirtwitnessed", "kisswitnessed", "fear_beingcheatedon", "fear_of_cheating",
                "caughtcheating", "caught_cheating", "infidelity"
            ]
            has_jealous_reaction = any(any(jt in bn for jt in JEALOUS_TRIGGERS) for bn in partner_buffs)

            # Also check sentiments between partner and cheater
            if not has_jealous_reaction and s_id:
                p_rt = getattr(partner_info, "relationship_tracker", None)
                if p_rt and hasattr(p_rt, "get_all_bits"):
                    for b in p_rt.get_all_bits(s_id) or []:
                        b_str = f"{getattr(b, '__name__', '')} {str(b)}".lower()
                        if any(st in b_str for st in ["hurt_cheating", "furious_cheatedon", "guilty_cheated", "bit_cheating"]):
                            has_jealous_reaction = True
                            break

            if has_jealous_reaction:
                from ai_social_pc.event_memory_manager import _find_lover_for_cheating
                lover = _find_lover_for_cheating(sim_info, partner_info, sim)
                if lover and getattr(lover, "sim_id", 0) != p_id and getattr(lover, "sim_id", 0) != s_id:
                    verb = get_sim_cheating_action_verb("flirt", sim_info)
                    if now is not None and s_id:
                        _sim_recent_romance_tracker[s_id] = {
                            "timestamp": now,
                            "target_info": lover,
                            "target_id": getattr(lover, "sim_id", 0),
                            "affordance_name": "jealousy_boundary_witness"
                        }
                    return lover, verb
        except Exception:
            pass

    return None, get_sim_cheating_action_verb("flirt", sim_info)


def update_romance_tracker():
    """
    Scans active Sims on lot to detect ongoing strictly romantic interactions.
    Records the romantic target and timestamp so an 8-Sim-minute cheating detection window is established.
    """
    if services is None:
        return
    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    if client is None:
        return
    now = get_sim_now()
    if now is None:
        return

    # Clean up expired entries (> 8 sim minutes)
    expired_ids = []
    for s_id, data in _sim_recent_romance_tracker.items():
        t_stamp = data.get("timestamp")
        if t_stamp is not None:
            mins = get_sim_minutes_between(t_stamp, now)
            if mins is None or mins > ROMANCE_CHEATING_WINDOW_MINUTES:
                expired_ids.append(s_id)
    for exp_id in expired_ids:
        _sim_recent_romance_tracker.pop(exp_id, None)

    sim_info_manager = getattr(services, "sim_info_manager", lambda: None)()
    if sim_info_manager is None:
        return

    try:
        all_infos = sim_info_manager.get_all() if hasattr(sim_info_manager, "get_all") else []
        for sim_info in all_infos:
            if sim_info is None or getattr(sim_info, "is_pet", False):
                continue
            sim_inst = getattr(sim_info, "get_sim_instance", lambda: None)()
            if not sim_inst or not hasattr(sim_inst, "get_running_and_queued_interactions"):
                continue

            s_id = getattr(sim_info, "sim_id", 0)
            for inter in sim_inst.get_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                if is_affordance_strictly_romantic(inter, aff):
                    target = getattr(inter, "target", None)
                    t_info = getattr(target, "sim_info", target) if target else None
                    t_id = getattr(t_info, "sim_id", 0) if t_info else 0
                    if t_id and t_id != s_id:
                        _sim_recent_romance_tracker[s_id] = {
                            "timestamp": now,
                            "target_info": t_info,
                            "target_id": t_id,
                            "affordance_name": getattr(aff, "__name__", "")
                        }
                        _sim_recent_romance_tracker[t_id] = {
                            "timestamp": now,
                            "target_info": sim_info,
                            "target_id": s_id,
                            "affordance_name": getattr(aff, "__name__", "")
                        }
                        break
    except Exception:
        pass


def update_bills_paid_tracker():
    """
    Scans active household members to detect if any Sim is paying household utility bills.
    Records the sim_time timestamp so a 60-sim-minute window is established.
    """
    if services is None:
        return
    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    if client is None:
        return
    hh = getattr(client, "household", None)
    if hh is None:
        return
    now = get_sim_now()
    if now is None:
        return

    for sim_info in hh.sim_info_gen():
        s_id = getattr(sim_info, "sim_id", 0)
        if not s_id or getattr(sim_info, "is_pet", False):
            continue
        sim_inst = getattr(sim_info, "get_sim_instance", lambda: None)()
        is_paying = False
        if sim_inst and hasattr(sim_inst, "get_running_and_queued_interactions"):
            try:
                for inter in sim_inst.get_running_and_queued_interactions():
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or "").lower()
                    if any(k in aff_name for k in ["paybill", "pay_bill", "pay_bills", "pay_bills_online", "mailbox_paybills", "phone_pay_bills", "computer_pay_bills"]):
                        is_paying = True
                        break
            except Exception:
                pass
        if not is_paying:
            try:
                from ai_thought_reader.context import get_current_activity
                act = (get_current_activity(sim_info) or "").lower()
                if any(k in act for k in ["оплачивает счета", "оплачивает счет", "платит по счетам", "счета за дом"]):
                    is_paying = True
            except Exception:
                pass
        if is_paying:
            _sim_bills_paid_tracker[s_id] = now


# =========================================================================
# VISITING DETECTORS & EVALUATION HELPERS
# =========================================================================

def has_always_welcome_trait(sim_info) -> bool:
    """Checks if a Sim has the 'Always Welcome' trait (Всегда желанный гость, trait_AlwaysWelcome / 26390)."""
    if sim_info is None:
        return False
    try:
        tt = getattr(sim_info, "trait_tracker", None)
        if tt is not None:
            traits = getattr(tt, "traits", ())
            for t in traits:
                t_name = (getattr(t, "__name__", "") or str(t)).lower()
                if "alwayswelcome" in t_name or "always_welcome" in t_name or getattr(t, "guid64", 0) == 26390:
                    return True
    except Exception:
        pass
    return False


def is_sim_host_resident(sim_info) -> bool:
    """Checks if the Sim is a permanent resident of the current active lot's owner household."""
    if sim_info is None or services is None:
        return False
    try:
        active_lot = services.active_lot()
        if not active_lot:
            return False
        owner_hh_id = getattr(active_lot, "owner_household_id", None)
        return bool(owner_hh_id and getattr(sim_info, "household_id", None) == owner_hh_id)
    except Exception:
        return False


def is_sim_active_guest(sim_info) -> bool:
    """Checks if the Sim belongs to the currently played active household or is controlled by the player."""
    if sim_info is None:
        return False
    try:
        # 1. Canonical EA is_npc check: if is_npc is False, the Sim is 100% a player/selectable sim
        if getattr(sim_info, "is_npc", None) is False:
            return True

        # 2. Direct flags
        if getattr(sim_info, "is_selectable", False) or getattr(sim_info, "is_selected", False):
            return True

        target_sim_id = getattr(sim_info, "sim_id", None) or getattr(sim_info, "id", None)
        target_hh_id = getattr(sim_info, "household_id", None)

        if services is not None:
            # 3. Active household ID check
            if hasattr(services, "active_household_id"):
                try:
                    act_hh_id = services.active_household_id()
                    if act_hh_id and target_hh_id and act_hh_id == target_hh_id:
                        return True
                except Exception:
                    pass

            # 4. Client manager & active sim comparison by ID
            if hasattr(services, "client_manager"):
                cm = services.client_manager()
                client = cm.get_first_client() if cm else None
                if client:
                    active_sim = getattr(client, "active_sim", None)
                    if active_sim is not None:
                        act_sim_id = getattr(active_sim, "sim_id", None) or getattr(active_sim, "id", None)
                        act_info = getattr(active_sim, "sim_info", None)
                        if act_sim_id and target_sim_id and act_sim_id == target_sim_id:
                            return True
                        if act_info is not None and getattr(act_info, "sim_id", None) == target_sim_id:
                            return True
                        if active_sim is sim_info or act_info is sim_info:
                            return True

                    # Selectable sims list on client
                    if hasattr(client, "selectable_sims"):
                        try:
                            for sel_info in client.selectable_sims:
                                if getattr(sel_info, "sim_id", None) == target_sim_id:
                                    return True
                        except Exception:
                            pass

            # 5. Active household instance comparison
            if hasattr(services, "active_household"):
                active_hh = services.active_household()
                if active_hh:
                    if target_hh_id and getattr(active_hh, "id", None) == target_hh_id:
                        return True
                    if hasattr(active_hh, "sim_info_gen"):
                        for h_info in active_hh.sim_info_gen():
                            if getattr(h_info, "sim_id", None) == target_sim_id:
                                return True
    except Exception:
        pass
    return False


def is_sim_actively_cooking(sim_inst, act_str: str) -> bool:
    """Checks if a Sim is actively preparing or cooking food."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                for kw in ("cook", "bake", "prepare_food", "stove_fry", "chop_ingredients", "make_gourmet", "grill"):
                    if kw in aff_name:
                        return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    return any(k in act_lower for k in ("готовит", "жарит", "печёт", "печет", "нарезает", "варит"))


def is_sim_drinking(sim_inst, act_str: str) -> bool:
    """Checks if Sim is drinking a beverage (tea, coffee, bar drink, juice)."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                if any(k in aff_name for k in ("drink", "sip", "coffee", "tea", "bar_drink")):
                    return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    return any(k in act_lower for k in ("пьет", "пьёт", "чай", "кофе", "напиток", "сок"))


def is_sim_cleaning_dishes_or_trash(sim_inst, act_str: str) -> bool:
    """Checks if Sim is washing dishes or handling trash."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                if any(k in aff_name for k in ("wash_dish", "clean_dish", "dishwasher", "sink_wash_dish")):
                    return True
                if any(k in aff_name for k in ("trash", "empty_trash", "throw_away")):
                    return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    return any(k in act_lower for k in ("моет посуду", "убирает посуду", "выносит мусор", "выбрасывает мусор"))


def is_sim_doing_homework(sim_inst, sim_info, act_str: str) -> bool:
    """Checks if a child or teen Sim is actively doing homework."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                if "homework" in aff_name:
                    return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    return any(k in act_lower for k in ("домашнее задание", "делает уроки", "домашку", "homework"))


def is_sim_helping_with_homework(sim_inst, sim_info, act_str: str) -> bool:
    """Checks if a parent, older sim, or sibling is actively helping with homework."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                if "homework" in aff_name and any(k in aff_name for k in ("help", "mentor", "supervise", "tutor", "guide")):
                    return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    return any(k in act_lower for k in ("помогает с домашн", "помощь с домашн", "помогать с домашн", "помогает с урок", "учит уроки с", "help with homework", "homework_help"))


def is_sim_homework_completed(sim_info, sim_inst=None) -> bool:
    """
    Deterministically and reliably checks if a Child or Teen Sim has completed their homework today.
    Uses multi-layered detection:
    1. Career Performance Metrics & Statistics (The Sims 4 engine metric check)
    2. Sim Commodity & Statistic Trackers (direct stat progress >= max_value)
    3. Sim Inventory Component (notebook commodity progress >= max_value)
    4. Lot Objects owned by or nearby Sim (notebook placed on desk/table with progress >= max_value)
    5. Buffs / Traits associated with homework completion
    """
    if sim_info is None:
        return False

    # Layer 1: Check School Career Performance Metrics
    try:
        if hasattr(sim_info, "career_tracker") and sim_info.career_tracker is not None:
            for career in getattr(sim_info.career_tracker, "careers", {}).values():
                cls_name = getattr(getattr(career, "__class__", None), "__name__", "")
                c_name = getattr(career, "__name__", str(career)).lower()
                is_school = (
                    getattr(career, "is_school_career", False)
                    or "school" in c_name
                    or "grade" in c_name
                    or "high" in c_name
                    or "school" in cls_name.lower()
                )
                if not is_school:
                    continue

                level_tuning = getattr(career, "current_level_tuning", None)
                metrics = getattr(level_tuning, "performance_metrics", None) if level_tuning else None
                if metrics is not None:
                    all_metrics = list(getattr(metrics, "statistic_metrics", []) or []) + list(getattr(metrics, "commodity_metrics", []) or [])
                    for metric in all_metrics:
                        stat_obj = getattr(metric, "statistic", None)
                        if stat_obj is None:
                            continue
                        val = None
                        try:
                            tracker = sim_info.get_tracker(stat_obj)
                            if tracker is not None:
                                val = tracker.get_value(stat_obj)
                        except Exception:
                            pass
                        if val is None:
                            try:
                                stat_inst = sim_info.get_statistic(stat_obj, add=False)
                                if stat_inst is not None:
                                    val = stat_inst.get_value()
                            except Exception:
                                pass

                        if val is not None:
                            try:
                                lower_th, upper_th = career._get_statistic_progress_thresholds(stat_obj, val)
                                # When upper_threshold is None, the Sim has reached the highest threshold (complete)
                                if upper_th is None and val > 0:
                                    return True
                                if lower_th is not None and getattr(lower_th, "threshold", 0) > 0:
                                    return True
                            except Exception:
                                pass
                            max_v = getattr(stat_obj, "max_value", 100.0)
                            if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                                return True
    except Exception:
        pass

    # Layer 2: Check Sim Info's Commodity & Statistic Trackers directly
    for trk_attr in ("commodity_tracker", "statistic_tracker"):
        try:
            tracker = getattr(sim_info, trk_attr, None)
            if tracker is not None:
                for stat in list(tracker):
                    s_name = f"{getattr(stat, '__name__', '')} {type(stat).__name__} {str(stat)}".lower()
                    if any(k in s_name for k in ("homework", "домашн")):
                        max_v = getattr(stat, "max_value", 100.0)
                        val = getattr(stat, "get_value", lambda: 0)()
                        if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                            return True
        except Exception:
            pass

    # Layer 3: Check Sim Inventory for Homework Book and its commodity
    if sim_inst is None and hasattr(sim_info, "get_sim_instance"):
        try:
            sim_inst = sim_info.get_sim_instance()
        except Exception:
            pass

    if sim_inst is not None and hasattr(sim_inst, "inventory_component"):
        try:
            for item in sim_inst.inventory_component:
                item_desc = f"{str(item)} {type(item).__name__} {getattr(item, 'definition', '')} {getattr(getattr(item, 'definition', None), 'name', '')}".lower()
                if any(k in item_desc for k in ("homework", "домашн", "childhomework", "teenhomework")):
                    # Found homework book in inventory! Check all commodities on it
                    tracker = getattr(item, "commodity_tracker", None) or getattr(item, "statistic_tracker", None)
                    if tracker is not None:
                        for stat in list(tracker):
                            c_name = f"{stat} {type(stat).__name__}".lower()
                            if any(k in c_name for k in ("progress", "homework", "stat")):
                                max_v = getattr(stat, "max_value", 100.0)
                                val = getattr(stat, "get_value", lambda: 0)()
                                if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                                    return True
                    if hasattr(item, "get_all_commodities"):
                        for comm in item.get_all_commodities():
                            c_name = f"{comm} {type(comm).__name__}".lower()
                            if any(k in c_name for k in ("progress", "homework", "stat")):
                                max_v = getattr(comm, "max_value", 100.0)
                                val = getattr(comm, "get_value", lambda: 0)()
                                if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                                    return True
        except Exception:
            pass

    # Layer 4: Check Lot Objects (e.g. homework book left on desk/table in room)
    try:
        import services
        om = services.object_manager() if services is not None and hasattr(services, "object_manager") else None
        if om is not None:
            my_sim_id = getattr(sim_info, "sim_id", 0)
            for obj in om.get_all():
                obj_desc = f"{str(obj)} {type(obj).__name__}".lower()
                if any(k in obj_desc for k in ("childhomework", "teenhomework", "book_homework")):
                    owner = getattr(obj, "owner_sim_info", None)
                    if not owner and hasattr(obj, "get_sim_owner"):
                        owner = obj.get_sim_owner()
                    owner_id = getattr(owner, "sim_id", 0) if owner else 0
                    if owner_id == my_sim_id or owner_id == 0:
                        tracker = getattr(obj, "commodity_tracker", None) or getattr(obj, "statistic_tracker", None)
                        if tracker is not None:
                            for stat in list(tracker):
                                c_name = f"{stat} {type(stat).__name__}".lower()
                                if any(k in c_name for k in ("progress", "homework", "stat")):
                                    max_v = getattr(stat, "max_value", 100.0)
                                    val = getattr(stat, "get_value", lambda: 0)()
                                    if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                                        return True
                        if hasattr(obj, "get_all_commodities"):
                            for comm in obj.get_all_commodities():
                                c_name = f"{comm} {type(comm).__name__}".lower()
                                if any(k in c_name for k in ("progress", "homework", "stat")):
                                    max_v = getattr(comm, "max_value", 100.0)
                                    val = getattr(comm, "get_value", lambda: 0)()
                                    if val >= (max_v - 0.1) or (max_v > 0 and val >= 99.0):
                                        return True
    except Exception:
        pass

    # Layer 5: Buffs indicating homework completion
    try:
        buff_tracker = getattr(sim_info, "buff_tracker", None) or getattr(sim_info, "buffs", None)
        if buff_tracker is not None:
            for b in list(buff_tracker):
                b_name = f"{getattr(b, '__class__', type(b)).__name__} {str(b)}".lower()
                if "homework" in b_name and any(k in b_name for k in ("done", "finish", "complete", "ready")):
                    return True
    except Exception:
        pass

    return False


def is_sim_listening_or_dancing_to_music(sim_inst, sim_info, act_str: str) -> bool:
    """Checks if Sim is dancing or listening to music from stereo / radio."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
                if any(k in aff_name for k in ("blicbloc", "blicblock")):
                    continue
                if any(k in aff_name for k in ("dance", "stereo", "listen_to_music", "radio")):
                    if "cringe" in aff_name:
                        continue
                    return True
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    if "без музыки" in act_lower or "блик-блок" in act_lower or "кринж" in act_lower:
        return False
    return any(k in act_lower for k in ("танцует под", "слушает музыку", "слушает радио", "стереосистема"))


def is_curfew_or_late_departure_time(sim_info, hour: int) -> Tuple[bool, str]:
    """Determines if it is late evening / curfew time to leave."""
    age_name = getattr(getattr(sim_info, "age", None), "name", "ADULT")
    is_young = age_name in ("CHILD", "TEEN")

    if is_young:
        has_curfew_buff = False
        try:
            buff_component = getattr(sim_info, "Buffs", None) or getattr(sim_info, "buff_component", None)
            if buff_component is not None:
                for b in getattr(buff_component, "_active_buffs", {}).values():
                    b_type = getattr(b, "buff_type", b)
                    b_name = (getattr(b_type, "__name__", "") or str(b_type)).lower()
                    if "curfew" in b_name:
                        has_curfew_buff = True
                        break
        except Exception:
            pass
        if has_curfew_buff or (hour >= 22 or hour < 6):
            return True, "поздний час и комендантский час для детей и подростков"
    else:
        if hour >= 0 and hour < 5:
            return True, "глубокая ночь и поздний час"

    return False, ""


def evaluate_visiting_friends_spark(sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b, space_desc, dist, now, hour, pair_key, force, allow_immediate_only, filter_func, allow_fallback: bool = True) -> Optional[Dict[str, Any]]:
    """Evaluates the 8 triggers dedicated to VISITING_FRIENDS mode."""
    a_is_guest = is_sim_active_guest(info_a)
    b_is_guest = is_sim_active_guest(info_b)
    a_is_host = is_sim_host_resident(info_a)
    b_is_host = is_sim_host_resident(info_b)

    curr_zone_id = getattr(services, "current_zone_id", lambda: 0)()
    curr_day = int(get_current_sim_day())

    # 1. guest_arrival_greeting (Priority 100, Immediate)
    # Fires ONCE per visit/day when an active guest and a host resident first see each other!
    if (a_is_guest and b_is_host) or (b_is_guest and a_is_host):
        guest_info = info_a if a_is_guest else info_b
        host_info = info_b if a_is_guest else info_a
        g_name = getattr(guest_info, "first_name", "Гость")
        h_name = getattr(host_info, "first_name", "Хозяин")

        d_key_arr = f"guest_arrival_{curr_zone_id}_{curr_day}"
        if can_trigger_fire_today(d_key_arr, "guest_arrival_greeting", force=force):
            sp = filter_func({
                "trigger_type": "guest_arrival_greeting",
                "priority": 100,
                "premise": f"{h_name} встречает {g_name} на пороге своего дома ({space_desc.lower()}). Тон и реакция зависят от знакомства симов, отношений и цели визита.",
                "participants": [host_info, guest_info],
                "daily_key": d_key_arr,
            })
            if sp is not None:
                return sp

    # 2. guest_inappropriate_cooking (Priority 92, Immediate)
    # Guest started cooking without AlwaysWelcome trait
    for g_inst, g_info, h_info, g_act in [(sim_a, info_a, info_b, act_a), (sim_b, info_b, info_a, act_b)]:
        if is_sim_active_guest(g_info) and is_sim_host_resident(h_info):
            if is_sim_actively_cooking(g_inst, g_act) and not has_always_welcome_trait(g_info):
                d_key_cook = f"inappropriate_cook_{g_info.sim_id}_{curr_day}"
                if can_trigger_fire_today(d_key_cook, "guest_inappropriate_cooking", force=force):
                    g_name = getattr(g_info, "first_name", "Гость")
                    h_name = getattr(h_info, "first_name", "Хозяин")
                    sp = filter_func({
                        "trigger_type": "guest_inappropriate_cooking",
                        "priority": 92,
                        "premise": f"{g_name} начал готовить на чужой кухне без черты «Всегда желанный гость» на глазах у хозяина {h_name} ({space_desc.lower()}). Реакция хозяина зависит от характера и отношений.",
                        "participants": [h_info, g_info],
                        "daily_key": d_key_cook,
                    })
                    if sp is not None:
                        return sp

    # 3. guest_late_curfew_departure (Priority 90, Immediate)
    for g_inst, g_info, o_info in [(sim_a, info_a, info_b), (sim_b, info_b, info_a)]:
        if is_sim_active_guest(g_info):
            is_late, reason_desc = is_curfew_or_late_departure_time(g_info, hour)
            if is_late:
                d_key_late = f"guest_late_{g_info.sim_id}_{curr_day}"
                if can_trigger_fire_today(d_key_late, "guest_late_curfew_departure", force=force):
                    g_name = getattr(g_info, "first_name", "Гость")
                    o_name = getattr(o_info, "first_name", "Собеседник")
                    sp = filter_func({
                        "trigger_type": "guest_late_curfew_departure",
                        "priority": 90,
                        "premise": f"{g_name} замечает, что наступило позднее время ({space_desc.lower()}). Разговор о завершении визита и уходе домой с {o_name} (тон зависит от возраста, характера и отношений).",
                        "participants": [g_info, o_info],
                        "daily_key": d_key_late,
                    })
                    if sp is not None:
                        return sp

    # 4. guest_homework_together (Priority 88, Immediate)
    # Child+Child, Teen+Teen, or Child+Teen doing homework together
    if (age_a in ("CHILD", "TEEN")) and (age_b in ("CHILD", "TEEN")):
        if is_sim_doing_homework(sim_a, info_a, act_a) and is_sim_doing_homework(sim_b, info_b, act_b):
            d_key_hw = f"guest_hw_{pair_key[0]}_{pair_key[1]}_{curr_day}"
            if can_trigger_fire_today(d_key_hw, "guest_homework_together", force=force):
                sp = filter_func({
                    "trigger_type": "guest_homework_together",
                    "priority": 88,
                    "premise": f"{name_a} и {name_b} вместе делают домашнее задание в гостях ({space_desc.lower()}). Общение вокруг уроков и школы (тон зависит от успеваемости, характера и отношений).",
                    "participants": [info_a, info_b],
                    "daily_key": d_key_hw,
                })
                if sp is not None:
                    return sp

    # 5. guest_gaming_console_tv (Priority 65, Ambient)
    is_tv_a = is_sim_watching_tv(sim_a, info_a, act_a)
    is_tv_b = is_sim_watching_tv(sim_b, info_b, act_b)
    is_pc_a = is_sim_using_pc_or_laptop(sim_a, info_a, act_a)
    is_pc_b = is_sim_using_pc_or_laptop(sim_b, info_b, act_b)
    if (is_tv_a and is_tv_b) or (is_pc_a and is_pc_b) or (is_tv_a or is_pc_a or is_tv_b or is_pc_b):
        d_key_game = f"guest_game_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_game, "guest_gaming_console_tv", force=force):
            sp = filter_func({
                "trigger_type": "guest_gaming_console_tv",
                "priority": 65,
                "premise": f"{name_a} и {name_b} вместе играют в видеоигры или смотрят ТВ в гостях ({space_desc.lower()}). Разговор зависит от происходящего на экране, настроения и отношений.",
                "participants": [info_a, info_b],
                "daily_key": d_key_game,
            })
            if sp is not None:
                return sp

    # 6. guest_eating_drinking (Priority 60, Ambient)
    is_eat_a = is_sim_eating(sim_a, info_a, act_a)
    is_eat_b = is_sim_eating(sim_b, info_b, act_b)
    is_drk_a = is_sim_drinking(sim_a, act_a)
    is_drk_b = is_sim_drinking(sim_b, act_b)
    if (is_eat_a or is_drk_a) and (is_eat_b or is_drk_b):
        d_key_eat = f"guest_eat_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_eat, "guest_eating_drinking", force=force):
            sp = filter_func({
                "trigger_type": "guest_eating_drinking",
                "priority": 60,
                "premise": f"{name_a} и {name_b} перекусывают или пьют напитки в гостях ({space_desc.lower()}). Тема беседы зависит от настроения и отношений.",
                "participants": [info_a, info_b],
                "daily_key": d_key_eat,
            })
            if sp is not None:
                return sp

    # 7. guest_music_dance_chill (Priority 55, Ambient)
    if is_sim_listening_or_dancing_to_music(sim_a, info_a, act_a) or is_sim_listening_or_dancing_to_music(sim_b, info_b, act_b):
        d_key_mus = f"guest_music_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_mus, "guest_music_dance_chill", force=force):
            sp = filter_func({
                "trigger_type": "guest_music_dance_chill",
                "priority": 55,
                "premise": f"{name_a} и {name_b} слушают музыку или танцуют под радио в гостях ({space_desc.lower()}). Общение зависит от настроения и характера симов.",
                "participants": [info_a, info_b],
                "daily_key": d_key_mus,
            })
            if sp is not None:
                return sp

    # 8. guest_ambient_hangout (Priority 30, Ambient Baseline Fallback)
    if not allow_fallback:
        return None
    return filter_func({
        "trigger_type": "guest_ambient_hangout",
        "priority": 30,
        "premise": f"{name_a} и {name_b} проводят время в гостях у друзей ({space_desc.lower()}), занимаясь повседневными делами.",
        "participants": [info_a, info_b],
    })


def evaluate_visiting_relatives_spark(sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b, space_desc, dist, now, hour, pair_key, force, allow_immediate_only, filter_func, allow_fallback: bool = True) -> Optional[Dict[str, Any]]:
    """Evaluates the 8 triggers dedicated to VISITING_RELATIVES mode."""
    a_is_guest = is_sim_active_guest(info_a)
    b_is_guest = is_sim_active_guest(info_b)
    a_is_host = is_sim_host_resident(info_a)
    b_is_host = is_sim_host_resident(info_b)

    curr_zone_id = getattr(services, "current_zone_id", lambda: 0)()
    curr_day = int(get_current_sim_day())

    # 1. relative_warm_welcome (Priority 100, Immediate)
    # Fires ONCE per visit/day when an active guest and a relative host resident first see each other!
    if (a_is_guest and b_is_host) or (b_is_guest and a_is_host):
        guest_info = info_a if a_is_guest else info_b
        host_info = info_b if a_is_guest else info_a
        g_name = getattr(guest_info, "first_name", "Гость")
        h_name = getattr(host_info, "first_name", "Хозяин")

        d_key_arr = f"rel_arrival_{curr_zone_id}_{curr_day}"
        if can_trigger_fire_today(d_key_arr, "relative_warm_welcome", force=force):
            sp = filter_func({
                "trigger_type": "relative_warm_welcome",
                "priority": 100,
                "premise": f"{h_name} встречает родственника {g_name} у себя дома ({space_desc.lower()}). Тон встречи и реакция зависят от того, знакомы ли они лично, и от семейных отношений.",
                "participants": [host_info, guest_info],
                "daily_key": d_key_arr,
            })
            if sp is not None:
                return sp

    # 2. relative_helping_chores (Priority 85, Immediate)
    for g_inst, g_info, h_info, g_act in [(sim_a, info_a, info_b, act_a), (sim_b, info_b, info_a, act_b)]:
        if is_sim_active_guest(g_info) and is_sim_cleaning_dishes_or_trash(g_inst, g_act):
            d_key_chore = f"rel_chore_{g_info.sim_id}_{curr_day}"
            if can_trigger_fire_today(d_key_chore, "relative_helping_chores", force=force):
                g_name = getattr(g_info, "first_name", "Гость")
                h_name = getattr(h_info, "first_name", "Хозяин")
                sp = filter_func({
                    "trigger_type": "relative_helping_chores",
                    "priority": 85,
                    "premise": f"{g_name} моет посуду или выносит мусор в доме родственников на глазах у {h_name} ({space_desc.lower()}). Реакция зависит от характера и отношений.",
                    "participants": [h_info, g_info],
                    "daily_key": d_key_chore,
                })
                if sp is not None:
                    return sp

    # 3. relative_homework_together (Priority 88, Immediate)
    # ANY young relatives (Child+Child, Teen+Teen, or Child+Teen) doing homework together
    # (couples, cousins, young uncles/nephews, siblings - any relative link!)
    if (age_a in ("CHILD", "TEEN")) and (age_b in ("CHILD", "TEEN")):
        if is_sim_doing_homework(sim_a, info_a, act_a) and is_sim_doing_homework(sim_b, info_b, act_b):
            d_key_hw = f"rel_hw_{pair_key[0]}_{pair_key[1]}_{curr_day}"
            if can_trigger_fire_today(d_key_hw, "relative_homework_together", force=force):
                sp = filter_func({
                    "trigger_type": "relative_homework_together",
                    "priority": 88,
                    "premise": f"Юные родственники {name_a} и {name_b} вместе делают домашнее задание в гостях ({space_desc.lower()}). Общение вокруг уроков и школы (тон зависит от характера и отношений).",
                    "participants": [info_a, info_b],
                    "daily_key": d_key_hw,
                })
                if sp is not None:
                    return sp

    # 4. relative_eating_together (Priority 80, Ambient)
    # Active Sim is eating food on the relative's lot (either alone or together)
    is_eat_a = is_sim_eating(sim_a, info_a, act_a)
    is_eat_b = is_sim_eating(sim_b, info_b, act_b)
    if is_eat_a or is_eat_b:
        d_key_eat = f"rel_eat_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_eat, "relative_eating_together", force=force):
            sp = filter_func({
                "trigger_type": "relative_eating_together",
                "priority": 80,
                "premise": f"{name_a} и {name_b} едят в гостях у родственников ({space_desc.lower()}). Общение за едой зависит от настроения и отношений.",
                "participants": [info_a, info_b],
                "daily_key": d_key_eat,
            })
            if sp is not None:
                return sp

    # 5. relative_interrogation_life (Priority 75, Ambient)
    # STRICTLY Elder/Adult <-> Child/Teen/YA
    is_older_a = age_a in ("ADULT", "ELDER")
    is_younger_b = age_b in ("CHILD", "TEEN", "YOUNGADULT")
    is_older_b = age_b in ("ADULT", "ELDER")
    is_younger_a = age_a in ("CHILD", "TEEN", "YOUNGADULT")
    if (is_older_a and is_younger_b) or (is_older_b and is_younger_a):
        older_info = info_a if is_older_a else info_b
        younger_info = info_b if is_older_a else info_a
        old_name = getattr(older_info, "first_name", "Старший")
        yng_name = getattr(younger_info, "first_name", "Младший")

        d_key_interrog = f"rel_interrog_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_interrog, "relative_interrogation_life", force=force):
            sp = filter_func({
                "trigger_type": "relative_interrogation_life",
                "priority": 75,
                "premise": f"Старший родственник {old_name} расспрашивает младшего {yng_name} ({space_desc.lower()}). Тема (учёба, работа, семья) и тон зависят от характера и близости симов.",
                "participants": [older_info, younger_info],
                "daily_key": d_key_interrog,
            })
            if sp is not None:
                return sp

    # 6. relative_cousins_hanging (Priority 65, Ambient)
    # ANY relatives of matching age (Child+Child or Teen+Teen) - cousins, young uncles/nephews, etc.
    if (age_a == age_b) and (age_a in ("CHILD", "TEEN")):
        d_key_cous = f"rel_cous_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_cous, "relative_cousins_hanging", force=force):
            sp = filter_func({
                "trigger_type": "relative_cousins_hanging",
                "priority": 65,
                "premise": f"Юные родственники {name_a} и {name_b} проводят время в гостях отдельно от взрослых ({space_desc.lower()}). Разговор зависит от возраста, интересов и отношений.",
                "participants": [info_a, info_b],
                "daily_key": d_key_cous,
            })
            if sp is not None:
                return sp

    # 7. relative_adult_family_gossip (Priority 60, Ambient)
    # STRICTLY Adult/Elder <-> Adult/Elder
    if (age_a in ("ADULT", "ELDER")) and (age_b in ("ADULT", "ELDER")):
        d_key_gossip = f"rel_gossip_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_gossip, "relative_adult_family_gossip", force=force):
            sp = filter_func({
                "trigger_type": "relative_adult_family_gossip",
                "priority": 60,
                "premise": f"Взрослые родственники {name_a} и {name_b} общаются в гостях ({space_desc.lower()}), обсуждая новости семьи, здоровье или бытовые темы.",
                "participants": [info_a, info_b],
                "daily_key": d_key_gossip,
            })
            if sp is not None:
                return sp

    # 8. relative_ambient_visit (Priority 30, Ambient Baseline Fallback)
    if not allow_fallback:
        return None
    return filter_func({
        "trigger_type": "relative_ambient_visit",
        "priority": 30,
        "premise": f"Родственники {name_a} и {name_b} проводят время в гостях ({space_desc.lower()}), занимаясь повседневными делами.",
        "participants": [info_a, info_b],
    })


# =========================================================================
# NPC & GUEST EVALUATION HELPERS (ON ACTIVE HOME LOT)
# =========================================================================

def is_welcome_wagon_active() -> bool:
    """Checks if a Welcome Wagon situation is currently running on the lot."""
    if services is None:
        return False
    try:
        sit_mgr = services.get_zone_situation_manager() if hasattr(services, "get_zone_situation_manager") else None
        if sit_mgr is None and hasattr(services, "current_zone"):
            sit_mgr = getattr(services.current_zone(), "situation_manager", None)
        if sit_mgr is not None and hasattr(sit_mgr, "get_all"):
            for sit in sit_mgr.get_all():
                sit_name = f"{getattr(sit, '__class__', type(sit)).__name__} {str(sit)}".lower()
                if "welcomewagon" in sit_name or "welcome_wagon" in sit_name:
                    return True
    except Exception:
        pass
    return False


def get_sim_service_type(sim_info, sim_inst=None, act_str: str = "") -> Optional[str]:
    """
    Identifies if a Sim is acting as a service NPC on the lot:
    Returns 'maid', 'repair', 'nanny', or None.
    """
    if sim_info is None:
        return None

    # Check traits
    try:
        tt = getattr(sim_info, "trait_tracker", None)
        if tt is not None:
            for t in getattr(tt, "traits", ()):
                t_name = f"{getattr(t, '__name__', '')} {str(t)}".lower()
                if any(k in t_name for k in ("maid", "butler", "servicenpc_maid", "livein_maid", "livein_butler")):
                    return "maid"
                if any(k in t_name for k in ("repair", "handyman", "servicenpc_repair")):
                    return "repair"
                if any(k in t_name for k in ("nanny", "babysitter", "servicenpc_nanny", "livein_nanny")):
                    return "nanny"
                if any(k in t_name for k in ("gardener", "servicenpc_gardener", "livein_gardener")):
                    return "gardener"
    except Exception:
        pass

    # Check active situations
    try:
        sit_mgr = services.get_zone_situation_manager() if hasattr(services, "get_zone_situation_manager") else None
        if sit_mgr is None and hasattr(services, "current_zone"):
            sit_mgr = getattr(services.current_zone(), "situation_manager", None)
        if sit_mgr is not None and sim_inst is not None:
            sim_sits = []
            if hasattr(sit_mgr, "get_situations_sim_is_in"):
                sim_sits = sit_mgr.get_situations_sim_is_in(sim_inst) or []
            elif hasattr(sit_mgr, "get_all"):
                sim_sits = sit_mgr.get_all()
            for sit in sim_sits:
                sit_name = f"{getattr(sit, '__class__', type(sit)).__name__} {str(sit)}".lower()
                if any(k in sit_name for k in ("nanny", "babysitter", "livein_nanny")):
                    return "nanny"
                if any(k in sit_name for k in ("repair", "handyman")):
                    return "repair"
                if any(k in sit_name for k in ("maid", "butler", "cleaner", "livein_maid", "livein_butler")):
                    return "maid"
                if any(k in sit_name for k in ("gardener", "livein_gardener")):
                    return "gardener"
    except Exception:
        pass

    # Check running interactions and affordance names
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if "nanny" in aff_name:
                    return "nanny"
                if any(k in aff_name for k in ("repair", "tinkering", "fix_object", "handiness")):
                    return "repair"
                if any(k in aff_name for k in ("maid", "clean_dish", "wash_dish", "empty_trash", "clean_puddle")):
                    return "maid"
        except Exception:
            pass

    act_l = (act_str or "").lower()
    if any(k in act_l for k in ("няня", "nanny")):
        return "nanny"
    if any(k in act_l for k in ("ремонт", "чинит", "чинка", "repair")):
        return "repair"
    if any(k in act_l for k in ("горничн", "уборщи", "убирает", "maid")):
        return "maid"

    return None


def is_sim_neighbor_uninvited_visitor(sim_info, sim_inst=None, act_str: str = "") -> bool:
    """Checks if Sim is a neighbor dropping in uninvited (doorbell/walkby/neighbor visit)."""
    if sim_info is None:
        return False
    try:
        sit_mgr = services.get_zone_situation_manager() if hasattr(services, "get_zone_situation_manager") else None
        if sit_mgr is None and hasattr(services, "current_zone"):
            sit_mgr = getattr(services.current_zone(), "situation_manager", None)
        if sit_mgr is not None and sim_inst is not None:
            sim_sits = []
            if hasattr(sit_mgr, "get_situations_sim_is_in"):
                sim_sits = sit_mgr.get_situations_sim_is_in(sim_inst) or []
            elif hasattr(sit_mgr, "get_all"):
                sim_sits = sit_mgr.get_all()
            for sit in sim_sits:
                sit_name = f"{getattr(sit, '__class__', type(sit)).__name__} {str(sit)}".lower()
                if any(k in sit_name for k in ("walkbyringdoorbell", "ringdoorbell", "neighbor_visitor", "neighborvisitor")):
                    return True
    except Exception:
        pass

    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("doorbell", "ring_door", "knock_door", "walkby")):
                    return True
        except Exception:
            pass

    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("звонит в дверь", "стучит в дверь", "звонок", "у двери"))


def is_sim_snacking_or_fridge(sim_inst, sim_info, act_str: str = "") -> bool:
    """Checks if Sim is raiding the fridge, grabbing a quick meal, or eating a snack."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("fridge_grab", "quickmeal", "quick_meal", "grab_snack", "eat_food", "food_eat", "eat")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("холодильник", "перекус", "кушает", "ест", "бутерброд", "чипсы", "снек"))


def is_sim_playing_toys_or_games(sim_inst, sim_info, act_str: str = "") -> bool:
    """Checks if Sim is playing video games, toys, dollhouse, or tabletop games."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("videogame", "video_game", "gaming", "console", "dollhouse", "toy", "play_toy", "chess", "arcade", "cards", "activitytable")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("играет", "видеоигр", "приставк", "консоль", "кукольн", "игрушк", "шахмат", "карты"))


def is_sim_at_entrance_or_greeting(sim_inst, sim_info, space_desc: str, act_str: str = "") -> bool:
    """Checks if Sim is at the entrance/porch/front door or engaged in greeting interaction."""
    sp_l = (space_desc or "").lower()
    if any(k in sp_l for k in ("крыльцо", "порог", "вход", "двор", "снаружи", "прихож")):
        return True
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("greet", "door", "invite_in", "ask_to_come_in", "wave", "welcome")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("приветств", "встречает", "у двери", "вход", "порог", "прихожая"))


def is_sim_leaving_or_farewell(sim_inst, sim_info, act_str: str = "") -> bool:
    """Checks if guest is preparing to leave or saying goodbye."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("leave_lot", "goodbye", "farewell", "ask_to_leave", "npc_leave")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("уходит", "прощается", "уходить домой", "прощание"))


def evaluate_npc_home_spark(
    sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
    space_desc, dist, now, hour, pair_key, force, allow_immediate_only, filter_func,
    allow_fallback: bool = True
) -> Optional[Dict[str, Any]]:
    """Evaluates the 11 scenarios dedicated to guests and NPCs on the active household's home lot."""
    is_a_played = is_sim_active_guest(info_a)
    is_b_played = is_sim_active_guest(info_b)

    curr_zone_id = getattr(services, "current_zone_id", lambda: 0)()
    curr_day = int(get_current_sim_day())

    # =========================================================================
    # GROUP B: NPC <-> NPC on our home lot (neither Sim belongs to played household)
    # =========================================================================
    if (not is_a_played) and (not is_b_played):
        # 1. two_kid_guests_playing (Priority 86, Immediate)
        if (age_a in ("CHILD", "TEEN")) and (age_b in ("CHILD", "TEEN")):
            if force or is_sim_playing_toys_or_games(sim_a, info_a, act_a) or is_sim_playing_toys_or_games(sim_b, info_b, act_b):
                d_key_play = f"two_kid_play_{pair_key[0]}_{pair_key[1]}_{curr_day}"
                if can_trigger_fire_today(d_key_play, "two_kid_guests_playing", force=force):
                    sp = filter_func({
                        "trigger_type": "two_kid_guests_playing",
                        "priority": 86,
                        "premise": f"Дети-гости {name_a} и {name_b} играют или проводят время вместе в доме хозяев ({space_desc.lower()}). Разговоры об игре, соперничество или детские споры с учетом их характеров и отношений.",
                        "participants": [info_a, info_b],
                        "daily_key": d_key_play,
                    })
                    if sp is not None:
                        return sp

        # 2. two_guests_living_room (Priority 76, Background)
        if not allow_immediate_only or force:
            d_key_lr = f"two_guests_lr_{pair_key[0]}_{pair_key[1]}_{curr_day}"
            if can_trigger_fire_today(d_key_lr, "two_guests_living_room", force=force):
                sp = filter_func({
                    "trigger_type": "two_guests_living_room",
                    "priority": 76,
                    "premise": f"Двое гостей {name_a} и {name_b} проводят время в доме хозяев ({space_desc.lower()}). Общение между гостями с учетом их отношений (обсуждение обстановки, хозяев дома или личных тем).",
                    "participants": [info_a, info_b],
                    "daily_key": d_key_lr,
                })
                if sp is not None:
                    return sp

        return None

    # =========================================================================
    # GROUP A: Guest / NPC <-> Played Household Sim
    # Exactly one is played household member, and one is visiting NPC/guest
    # =========================================================================
    if is_a_played and not is_b_played:
        host_sim, host_info, host_act, host_age, host_name = sim_a, info_a, act_a, age_a, name_a
        guest_sim, guest_info, guest_act, guest_age, guest_name = sim_b, info_b, act_b, age_b, name_b
    elif is_b_played and not is_a_played:
        host_sim, host_info, host_act, host_age, host_name = sim_b, info_b, act_b, age_b, name_b
        guest_sim, guest_info, guest_act, guest_age, guest_name = sim_a, info_a, act_a, age_a, name_a
    else:
        # Both are played household members: handled by normal domestic triggers!
        return None

    g_id = getattr(guest_info, "sim_id", 0)

    # 1. neighbor_welcome_wagon (Priority 90, Immediate)
    # Welcome Wagon neighbors visiting with fruitcake
    is_ww = is_welcome_wagon_active() or any(k in guest_act for k in ("кекс", "фруктовый", "welcome", "сосед"))
    if is_ww or (force and "welcome" in str(filter_func)):
        d_key_ww = f"welcome_wagon_{curr_zone_id}_{curr_day}"
        if can_trigger_fire_today(d_key_ww, "neighbor_welcome_wagon", force=force):
            sp = filter_func({
                "trigger_type": "neighbor_welcome_wagon",
                "priority": 90,
                "premise": f"Соседи во главе с {guest_name} пришли поприветствовать семью с фруктовым кексом («Добро пожаловать!»). Встреча с {host_name} ({space_desc.lower()}). Знакомство, новости района или обсуждение визита (реакция хозяина зависит от характера, настроения и радушия).",
                "participants": [guest_info, host_info],
                "daily_key": d_key_ww,
            })
            if sp is not None:
                return sp

    # Check service NPC roles (Repairman, Nanny, Maid)
    service_type = get_sim_service_type(guest_info, guest_sim, guest_act)

    # 2. service_repairman_done (Priority 88, Immediate)
    if service_type == "repair" or (force and "repair" in str(filter_func)):
        d_key_rep = f"repair_done_{g_id}_{curr_day}"
        if can_trigger_fire_today(d_key_rep, "service_repairman_done", force=force):
            sp = filter_func({
                "trigger_type": "service_repairman_done",
                "priority": 88,
                "premise": f"Мастер по ремонту {guest_name} сообщает {host_name} об успешной починке техники или сантехники ({space_desc.lower()}). Услуга мастера уже полностью оплачена клиентом при вызове — никаких счетов, требований денег или выдуманных цен! Мастер лишь коротко отчитывается о сделанном, даёт бытовой совет по уходу за приборами или вежливо прощается.",
                "participants": [guest_info, host_info],
                "daily_key": d_key_rep,
            })
            if sp is not None:
                return sp

    # 3. guest_home_door_greeting (Priority 88, Immediate)
    # Universal arrival meeting when any guest (friend, relative, neighbor, stranger) arrives on the home lot
    is_door = is_sim_at_entrance_or_greeting(guest_sim, guest_info, space_desc, guest_act)
    d_key_door = f"guest_home_door_{g_id}_{curr_day}"
    if is_door or can_trigger_fire_today(d_key_door, "guest_home_door_greeting", force=force) or force:
        if can_trigger_fire_today(d_key_door, "guest_home_door_greeting", force=force):
            premise = (
                f"{host_name} встречает пришедшего в дом персонажа {guest_name} ({space_desc.lower()}). "
                f"Первые реплики встречи у порога или при входе. Тон, эмоции и реакция персонажей (радость, теплота, настороженность, неловкость, холодность или неприязнь) "
                f"строго определяются их фактическими отношениями (родные, друзья, чужаки или враги), чертами характера и предысторией."
            )

            sp = filter_func({
                "trigger_type": "guest_home_door_greeting",
                "priority": 88,
                "premise": premise,
                "participants": [host_info, guest_info],
                "daily_key": d_key_door,
            })
            if sp is not None:
                return sp

    # 4. guest_home_after_school (Priority 87, Immediate)
    # Child / Teen brought classmate home after school (15:00-19:00)
    if (host_age in ("CHILD", "TEEN")) and (guest_age in ("CHILD", "TEEN")):
        if (15 <= hour <= 19) or force:
            d_key_school = f"after_school_{g_id}_{curr_day}"
            if can_trigger_fire_today(d_key_school, "guest_home_after_school", force=force):
                sp = filter_func({
                    "trigger_type": "guest_home_after_school",
                    "priority": 87,
                    "premise": f"{host_name} и {guest_name} пришли домой после уроков/занятий ({space_desc.lower()}). Обсуждение школы, оценок или вечерних планов с учетом их отношений и характеров.",
                    "participants": [host_info, guest_info],
                    "daily_key": d_key_school,
                })
                if sp is not None:
                    return sp

    # 5. guest_home_farewell_late (Priority 87, Immediate)
    # Late night / curfew departure
    is_late_time, _ = is_curfew_or_late_departure_time(guest_info, hour)
    is_leaving = is_sim_leaving_or_farewell(guest_sim, guest_info, guest_act)
    if (is_late_time or is_leaving or (hour >= 22 or hour < 6)) or force:
        d_key_farewell = f"farewell_late_{g_id}_{curr_day}"
        if can_trigger_fire_today(d_key_farewell, "guest_home_farewell_late", force=force):
            sp = filter_func({
                "trigger_type": "guest_home_farewell_late",
                "priority": 87,
                "premise": f"Гость {guest_name} собирается уходить домой из-за позднего времени ({space_desc.lower()}). Завершение визита и прощальные реплики (от взаимной признательности до формального прощания или желания поскорее разойтись — строго по отношениям симов).",
                "participants": [guest_info, host_info],
                "daily_key": d_key_farewell,
            })
            if sp is not None:
                return sp

    # 6. service_nanny_chat (Priority 86, Immediate)
    if service_type == "nanny" or (force and "nanny" in str(filter_func)):
        if host_age in ("TEEN", "YOUNGADULT", "ADULT", "ELDER") or force:
            d_key_nanny = f"nanny_chat_{g_id}_{curr_day}"
            if can_trigger_fire_today(d_key_nanny, "service_nanny_chat", force=force):
                sp = filter_func({
                    "trigger_type": "service_nanny_chat",
                    "priority": 86,
                    "premise": f"Няня {guest_name} обсуждает уход за детьми и обстановку в доме с {host_name} ({space_desc.lower()}). Отчёт о поведении детей, кормлении, сне или мелких происшествиях.",
                    "participants": [guest_info, host_info],
                    "daily_key": d_key_nanny,
                })
                if sp is not None:
                    return sp

    # 7. neighbor_door_knock (Priority 85, Immediate)
    # Neighbor arrival / knocking on door (invited neighbor or uninvited walkby neighbor)
    is_neighbor_knock = is_sim_neighbor_uninvited_visitor(guest_info, guest_sim, guest_act) or is_door
    if is_neighbor_knock or force:
        d_key_knock = f"neighbor_knock_{g_id}_{curr_day}"
        if can_trigger_fire_today(d_key_knock, "neighbor_door_knock", force=force):
            sp = filter_func({
                "trigger_type": "neighbor_door_knock",
                "priority": 85,
                "premise": f"Сосед {guest_name} заглянул или постучал в дверь к {host_name} ({space_desc.lower()}). Разговор у входа. Тон и реакция зависят от добрососедских или напряженных отношений между ними.",
                "participants": [guest_info, host_info],
                "daily_key": d_key_knock,
            })
            if sp is not None:
                return sp

    # 8. guest_home_fridge_snack (Priority 85, Immediate)
    is_snack = is_sim_snacking_or_fridge(guest_sim, guest_info, guest_act)
    if is_snack or force:
        d_key_snack = f"guest_snack_{g_id}_{curr_day}"
        if can_trigger_fire_today(d_key_snack, "guest_home_fridge_snack", force=force):
            sp = filter_func({
                "trigger_type": "guest_home_fridge_snack",
                "priority": 85,
                "premise": f"Гость {guest_name} полез в холодильник за перекусом в доме хозяев на глазах у {host_name} ({space_desc.lower()}). Реакция хозяина на перекус гостя и разговор вокруг еды.",
                "participants": [guest_info, host_info],
                "daily_key": d_key_snack,
            })
            if sp is not None:
                return sp

    # 9. service_maid_cleaning (Priority 75, Background)
    if service_type == "maid" or (force and "maid" in str(filter_func)):
        if not allow_immediate_only or force:
            d_key_maid = f"maid_clean_{g_id}_{curr_day}"
            if can_trigger_fire_today(d_key_maid, "service_maid_cleaning", force=force):
                sp = filter_func({
                    "trigger_type": "service_maid_cleaning",
                    "priority": 75,
                    "premise": f"Горничная {guest_name} наводит порядок в доме на глазах у {host_name} ({space_desc.lower()}). Обмен репликами о чистоте, порядке и повседневных домашних делах.",
                    "participants": [guest_info, host_info],
                    "daily_key": d_key_maid,
                })
                if sp is not None:
                    return sp

    return None


# =========================================================================
# COMMUNITY LOT EVALUATION HELPERS
# =========================================================================

def get_distance_between_sims(sim_a, sim_b) -> Optional[float]:
    """Calculates 3D distance in meters/grid units between two Sim instances."""
    if sim_a is None or sim_b is None:
        return None
    try:
        pos_a = getattr(sim_a, "position", None)
        pos_b = getattr(sim_b, "position", None)
        if pos_a is not None and pos_b is not None:
            return float((pos_a - pos_b).magnitude())
    except Exception:
        pass
    return None


def get_current_venue_info() -> Dict[str, Any]:
    """
    Returns information about the current venue:
    {'venue_type': str, 'venue_name': str, 'raw_name': str}
    """
    v_type = "venue"
    v_friendly = "общественное место"
    raw_name = ""
    try:
        if services is not None and hasattr(services, "venue_service"):
            venue_service = services.venue_service()
            active_venue = getattr(venue_service, "active_venue", None) if venue_service else None
            if active_venue is not None:
                raw_name = getattr(active_venue, "__name__", str(active_venue)).lower()
                for key in ("bar", "club", "nightclub", "lounge", "gym", "cafe", "restaurant", "library", "museum", "park", "pool", "beach", "spa", "karaoke"):
                    if key in raw_name:
                        v_type = key
                        break
                from ai_thought_reader.context import VENUE_TRANSLATIONS
                v_friendly = VENUE_TRANSLATIONS.get(v_type, "общественное место")
    except Exception:
        pass
    return {"venue_type": v_type, "venue_name": v_friendly, "raw_name": raw_name}


def is_sim_bartender_active(sim_inst, act_str: str = "") -> bool:
    """Checks if Sim is actively working behind a bar or mixing drinks."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("bar_tend", "bartend", "bar_makedrink", "makedrink", "bar_clean")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("бармен", "смешивает напиток", "за стойкой бара", "готовит напиток"))


def is_sim_ordering_or_at_bar(sim_inst, act_str: str = "") -> bool:
    """Checks if Sim is ordering drinks at a bar counter or sitting at a bar counter."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("order_drink", "orderdrink", "sit_bar", "sitbar", "bar_order", "drink_active", "barstool")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("заказывает напиток", "у стойки бара", "за барной стойкой", "барный стул"))


def is_sim_barista_active(sim_inst, act_str: str = "") -> bool:
    """Checks if Sim is actively working as barista at an espresso bar."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("barista", "espresso_make", "make_espresso", "barista_tend")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("бариста", "готовит эспрессо", "варит кофе"))


def is_sim_ordering_coffee(sim_inst, act_str: str = "") -> bool:
    """Checks if Sim is ordering coffee or pastry at an espresso bar."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("order_coffee", "order_espresso", "espresso_order", "order_pastry", "buy_coffee")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("заказывает кофе", "эспрессо", "покупает выпечку"))


def is_sim_exercising(sim_inst, sim_info=None, act_str: str = "") -> Tuple[bool, str]:
    """Checks if Sim is actively exercising (treadmill, punching bag, weight machine, workout, jog)."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("treadmill", "workout", "exercise", "punchingbag", "weightmachine", "jog", "pushups", "situps", "stretch", "fitness")):
                    if "treadmill" in aff_name:
                        return True, "бегает на беговой дорожке"
                    if "punchingbag" in aff_name:
                        return True, "тренируется на боксёрской груше"
                    if "weightmachine" in aff_name:
                        return True, "занимается на силовом тренажере"
                    if "jog" in aff_name:
                        return True, "на пробежке"
                    return True, "тренируется"
        except Exception:
            pass
    act_lower = (act_str or "").lower()
    for kw, label in [
        ("бегов", "бегает на беговой дорожке"),
        ("груш", "тренируется на груше"),
        ("тренажер", "занимается на тренажере"),
        ("тренажёр", "занимается на тренажере"),
        ("отжима", "отжимается"),
        ("пресс", "качает пресс"),
        ("трениров", "тренируется"),
        ("пробежк", "на пробежке"),
        ("спорт", "занимается спортом"),
    ]:
        if kw in act_lower:
            return True, label
    return False, ""


def is_sim_sitting(sim_inst) -> bool:
    """Checks if Sim posture is sitting."""
    if sim_inst is None:
        return False
    try:
        posture = getattr(sim_inst, "posture", None)
        if posture is not None:
            p_name = getattr(posture, "name", "") or str(type(posture))
            if "sit" in p_name.lower():
                return True
    except Exception:
        pass
    return False


def is_sim_reading_or_studying(sim_inst, sim_info, act_str: str = "") -> bool:
    """Checks if Sim is reading a book, studying, using research computer, or viewing art."""
    if sim_inst is not None and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_inst.get_all_running_and_queued_interactions():
                aff = getattr(inter, "affordance", None)
                aff_name = f"{getattr(aff, '__name__', '')} {str(aff)}".lower()
                if any(k in aff_name for k in ("read_book", "book_read", "read_active", "study", "research_computer", "view_art", "admire_art", "sculpture_view", "painting_view")):
                    return True
        except Exception:
            pass
    act_l = (act_str or "").lower()
    return any(k in act_l for k in ("читает", "книга", "библиотек", "исследует", "рассматривает картину", "любуется искусством"))


def are_sims_actively_conversing(sim_a, sim_b, info_a=None, info_b=None) -> bool:
    """
    Checks if sim_a and sim_b are actively conversing in the game:
    1. Belong to the same SocialGroup (main_social_group).
    2. Or one is targeting the other with an active running social interaction.
    """
    if sim_a is None or sim_b is None:
        return False
    try:
        if hasattr(sim_a, "get_main_social_group"):
            sg_a = sim_a.get_main_social_group()
            if sg_a is not None and hasattr(sg_a, "members"):
                if sim_b in set(sg_a.members):
                    return True
        if hasattr(sim_b, "get_main_social_group"):
            sg_b = sim_b.get_main_social_group()
            if sg_b is not None and hasattr(sg_b, "members"):
                if sim_a in set(sg_b.members):
                    return True
    except Exception:
        pass

    try:
        b_inf = getattr(sim_b, "sim_info", sim_b)
        a_inf = getattr(sim_a, "sim_info", sim_a)
        if hasattr(sim_a, "get_all_running_and_queued_interactions"):
            for inter in sim_a.get_all_running_and_queued_interactions():
                t = getattr(inter, "target", None)
                if t is sim_b or t is b_inf:
                    return True
        if hasattr(sim_b, "get_all_running_and_queued_interactions"):
            for inter in sim_b.get_all_running_and_queued_interactions():
                t = getattr(inter, "target", None)
                if t is sim_a or t is a_inf:
                    return True
    except Exception:
        pass

    return False


def evaluate_community_lot_spark(
    sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
    space_desc, dist, now, hour, pair_key, force, allow_immediate_only, filter_func,
    allow_fallback: bool = True
) -> Optional[Dict[str, Any]]:
    """Evaluates the 6 scenarios dedicated to COMMUNITY lots."""
    v_info = get_current_venue_info()
    v_type = v_info.get("venue_type", "venue")
    v_name = v_info.get("venue_name", "заведение")
    curr_day = int(get_current_sim_day())

    role_str_a = ""
    role_str_b = ""
    try:
        from ai_thought_reader.context import get_sim_active_lot_role
        ra = get_sim_active_lot_role(info_a, sim_a)
        rb = get_sim_active_lot_role(info_b, sim_b)
        role_str_a = str(ra.get("ru", ra) if isinstance(ra, dict) else (ra or "")).lower()
        role_str_b = str(rb.get("ru", rb) if isinstance(rb, dict) else (rb or "")).lower()
    except Exception:
        pass

    # =========================================================================
    # 1. community_bar_order_chat (Priority 85, Immediate)
    # =========================================================================
    is_bar_venue = v_type in ("bar", "club", "nightclub", "lounge", "karaoke") or "бар" in space_desc.lower()
    is_bt_a = ("бармен" in role_str_a) or is_sim_bartender_active(sim_a, act_a)
    is_bt_b = ("бармен" in role_str_b) or is_sim_bartender_active(sim_b, act_b)
    is_ord_a = is_sim_ordering_or_at_bar(sim_a, act_a)
    is_ord_b = is_sim_ordering_or_at_bar(sim_b, act_b)

    if (is_bar_venue or is_bt_a or is_bt_b) and (is_bt_a or is_bt_b or is_ord_a or is_ord_b or (force and "bar" in str(filter_func))):
        if is_bt_a and not is_bt_b:
            bt_inf, cust_inf = info_a, info_b
            bt_name, cust_name = name_a, name_b
        elif is_bt_b and not is_bt_a:
            bt_inf, cust_inf = info_b, info_a
            bt_name, cust_name = name_b, name_a
        else:
            cust_inf, bt_inf = info_a, info_b
            cust_name, bt_name = name_a, name_b

        d_key_bar = f"comm_bar_{getattr(cust_inf, 'sim_id', 0)}_{curr_day}"
        if can_trigger_fire_today(d_key_bar, "community_bar_order_chat", force=force):
            if is_bt_a != is_bt_b:
                premise = f"{cust_name} общается с барменом ({bt_name}) у стойки заведения ({space_desc.lower()}, {v_name}). Если напиток уже получен/в руках — дружеская беседа о заведении, настроении или коктейлях (заказ уже выполнен). Если напитка нет — заказ выпивки у стойки."
                parts = [cust_inf, bt_inf]
            else:
                premise = f"{name_a} и {name_b} находятся у барной стойки заведения ({space_desc.lower()}, {v_name}) с напитками. Напитки уже получены! Обсуждение вкуса напитков, тост, отдых или дружеский разговор (напитки уже на руках, заказывать ничего не нужно)."
                parts = [info_a, info_b]

            sp = filter_func({
                "trigger_type": "community_bar_order_chat",
                "priority": 85,
                "premise": premise,
                "participants": parts,
                "daily_key": d_key_bar,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # 2. community_cafe_barista (Priority 85, Immediate)
    # =========================================================================
    is_cafe_venue = (v_type == "cafe") or "кафе" in space_desc.lower()
    is_barista_a = ("барист" in role_str_a) or is_sim_barista_active(sim_a, act_a)
    is_barista_b = ("барист" in role_str_b) or is_sim_barista_active(sim_b, act_b)
    is_ord_c_a = is_sim_ordering_coffee(sim_a, act_a)
    is_ord_c_b = is_sim_ordering_coffee(sim_b, act_b)

    if (is_cafe_venue or is_barista_a or is_barista_b) and (is_barista_a or is_barista_b or is_ord_c_a or is_ord_c_b or (force and "cafe" in str(filter_func))):
        if is_barista_a and not is_barista_b:
            bar_inf, cust_inf = info_a, info_b
            bar_name, cust_name = name_a, name_b
        elif is_barista_b and not is_barista_a:
            bar_inf, cust_inf = info_b, info_a
            bar_name, cust_name = name_b, name_a
        else:
            cust_inf, bar_inf = info_a, info_b
            cust_name, bar_name = name_a, name_b

        d_key_cafe = f"comm_cafe_{getattr(cust_inf, 'sim_id', 0)}_{curr_day}"
        if can_trigger_fire_today(d_key_cafe, "community_cafe_barista", force=force):
            sp = filter_func({
                "trigger_type": "community_cafe_barista",
                "priority": 85,
                "premise": f"{cust_name} заказывает кофе или выпечку у баристы ({bar_name}) в кафе ({space_desc.lower()}, {v_name}). Обсуждение бодрящего кофе, комплимент напитку или утренний позитивный диалог.",
                "participants": [cust_inf, bar_inf],
                "daily_key": d_key_cafe,
            })
            if sp is not None:
                return sp

    if allow_immediate_only:
        return None

    # =========================================================================
    # 3. community_gym_workout_spot (Priority 75, Ambient)
    # =========================================================================
    is_gym_venue = (v_type == "gym") or "спортзал" in space_desc.lower()
    is_ex_a, ex_det_a = is_sim_exercising(sim_a, info_a, act_a)
    is_ex_b, ex_det_b = is_sim_exercising(sim_b, info_b, act_b)

    if (is_gym_venue or is_ex_a or is_ex_b or (force and "gym" in str(filter_func))) and (is_ex_a or is_ex_b or force):
        if is_ex_a and not is_ex_b:
            ath_inf, spt_inf = info_a, info_b
            ath_name, spt_name = name_a, name_b
            detail = ex_det_a
        elif is_ex_b and not is_ex_a:
            ath_inf, spt_inf = info_b, info_a
            ath_name, spt_name = name_b, name_a
            detail = ex_det_b
        else:
            ath_inf, spt_inf = info_a, info_b
            ath_name, spt_name = name_a, name_b
            detail = ex_det_a or ex_det_b or "тренируется на тренажере"

        d_key_gym = f"comm_gym_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_gym, "community_gym_workout_spot", force=force):
            is_trainer = ("тренер" in role_str_a or "инструктор" in role_str_a) or ("тренер" in role_str_b or "инструктор" in role_str_b)
            role_desc = "тренер" if is_trainer else "напарник по залу"
            sp = filter_func({
                "trigger_type": "community_gym_workout_spot",
                "priority": 75,
                "premise": f"{ath_name} тренируется в спортзале ({detail}), а {spt_name} ({role_desc}) находится рядом ({space_desc.lower()}). Совет по технике, подбадривание или спортивная мотивация.",
                "participants": [ath_inf, spt_inf],
                "daily_key": d_key_gym,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # 4. community_restaurant_companion (Priority 70, Ambient)
    # =========================================================================
    is_dining_venue = v_type in ("restaurant", "cafe", "bar", "lounge") or any(k in space_desc.lower() for k in ("ресторан", "стол", "кафе"))
    is_eat_a = is_sim_eating(sim_a, info_a, act_a)
    is_eat_b = is_sim_eating(sim_b, info_b, act_b)
    is_drk_a = is_sim_drinking(sim_a, act_a)
    is_drk_b = is_sim_drinking(sim_b, act_b)
    is_sit_a = is_sim_sitting(sim_a)
    is_sit_b = is_sim_sitting(sim_b)

    has_food_or_drinks = (is_eat_a or is_eat_b or is_drk_a or is_drk_b)
    if (is_dining_venue or has_food_or_drinks or (force and "restaurant" in str(filter_func))) and (has_food_or_drinks or (is_sit_a and is_sit_b) or force):
        d_key_dine = f"comm_rest_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_dine, "community_restaurant_companion", force=force):
            sp = filter_func({
                "trigger_type": "community_restaurant_companion",
                "priority": 70,
                "premise": f"{name_a} и {name_b} расположились за столиком в заведении ({space_desc.lower()}, {v_name}). Они кушают или выпивают, обсуждая вкус блюд, обстановку или делясь новостями.",
                "participants": [info_a, info_b],
                "daily_key": d_key_dine,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # 5. community_library_whisper (Priority 65, Ambient)
    # =========================================================================
    is_lib_venue = v_type in ("library", "museum") or any(k in space_desc.lower() for k in ("библиотек", "музей", "галере"))
    is_read_a = is_sim_reading_or_studying(sim_a, info_a, act_a)
    is_read_b = is_sim_reading_or_studying(sim_b, info_b, act_b)

    if (is_lib_venue or is_read_a or is_read_b or (force and "library" in str(filter_func))) and (is_read_a or is_read_b or "библиотекар" in role_str_a or "библиотекар" in role_str_b or force):
        d_key_lib = f"comm_lib_{pair_key[0]}_{pair_key[1]}_{curr_day}"
        if can_trigger_fire_today(d_key_lib, "community_library_whisper", force=force):
            sp = filter_func({
                "trigger_type": "community_library_whisper",
                "priority": 65,
                "premise": f"{name_a} и {name_b} находятся в тихом зале заведения ({space_desc.lower()}, {v_name}). Разговор вполголоса: обсуждение прочитанного, экспонатов, поиск нужной книги или замечание о тишине.",
                "participants": [info_a, info_b],
                "daily_key": d_key_lib,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # 6. community_player_social (Priority 80, Ambient - Player Involved)
    # =========================================================================
    is_player_a = is_sim_active_guest(info_a)
    is_player_b = is_sim_active_guest(info_b)
    is_player_involved = is_player_a or is_player_b

    filter_str = str(filter_func)
    wants_player_social = ("community_player_social" in filter_str)
    wants_ambient_social = ("community_ambient_social" in filter_str)

    # Sim is nearby if within 8.5m (~10 grid tiles) or co-present
    is_near = (dist is None or dist <= 8.5)

    if (is_player_involved or wants_player_social) and not wants_ambient_social:
        # Для игрока ОБЯЗАТЕЛЬНО: персонажи должны активно общаться в игре (SocialGroup или социальное действие)
        if force or are_sims_actively_conversing(sim_a, sim_b, info_a, info_b):
            sp = filter_func({
                "trigger_type": "community_player_social",
                "priority": 80,
                "premise": f"{name_a} и {name_b} общаются в заведении ({space_desc.lower()}, {v_name}). Живой диалог: обсуждение атмосферы места, отдыха, напитков/еды или событий вокруг.",
                "participants": [info_a, info_b],
            })
            if sp is not None:
                return sp

    # =========================================================================
    # 7. community_ambient_social (Priority 40, Ambient Baseline Fallback - NPC-NPC)
    # =========================================================================
    if not allow_fallback:
        return None

    if wants_player_social:
        return None

    # STRICT NPC-NPC: If a member of the played household is involved, NEVER trigger community_ambient_social!
    if is_player_involved:
        return None

    # Для NPC-NPC: симы должны быть близко ДРУГ К ДРУГУ (не более 3.5 метров / ~4 клетки)
    # и ни один из них не должен быть на ходу (не идти/бежать через зал)
    is_actively_talking = are_sims_actively_conversing(sim_a, sim_b, info_a, info_b)
    is_close = (dist is not None and dist <= 3.5)

    if not force and not is_actively_talking:
        # Дистанция между говорящими NPC строго <= 3.5м
        if not is_close:
            return None
        # Проверка движения: идущий сим не должен втягиваться в фоновый разговор
        if is_sim_moving(sim_a) or is_sim_moving(sim_b):
            return None

    if force or is_close or is_actively_talking:
        # Distance check for NPC-NPC conversations:
        # Keep NPC-NPC ambient dialogue in the immediate sphere of ANY played household member on the lot.
        if not force:
            try:
                min_dist = None
                active_hh = services.active_household() if hasattr(services, "active_household") else None
                if active_hh is not None:
                    for hh_inst in active_hh.instanced_sims_gen():
                        if hh_inst is not None:
                            d = get_distance_between_sims(sim_a, hh_inst)
                            if d is not None:
                                if min_dist is None or d < min_dist:
                                    min_dist = d
                if min_dist is None:
                    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
                    active_sim = getattr(client, "active_sim", None) if client else None
                    if active_sim is not None:
                        min_dist = get_distance_between_sims(sim_a, active_sim)
                if min_dist is not None and min_dist > 8.5:
                    return None
            except Exception:
                pass

        return filter_func({
            "trigger_type": "community_ambient_social",
            "priority": 40,
            "premise": f"Посетители {name_a} и {name_b} находятся рядом в заведении ({space_desc.lower()}, {v_name}). Разговор двух посетителей: впечатления от места, личные новости или сплетни.",
            "participants": [info_a, info_b],
        })

    return None


def evaluate_scene_spark(sim_a, sim_b, force: bool = False, allow_immediate_only: bool = False) -> Optional[Dict[str, Any]]:
    """
    Evaluates all 100% deterministic game states and returns the highest priority
    Scene Spark dictionary if conditions are met.
    """
    info_a = getattr(sim_a, "sim_info", None)
    info_b = getattr(sim_b, "sim_info", None)
    if info_a is None or info_b is None:
        return None

    now = get_sim_now()
    hour = now.hour() if (now and hasattr(now, "hour")) else 12

    # Get activities from context engine
    from ai_thought_reader.context import get_current_activity
    act_a = (get_current_activity(info_a) or "").lower()
    act_b = (get_current_activity(info_b) or "").lower()

    # Ages
    age_a = getattr(getattr(info_a, "age", None), "name", "ADULT")
    age_b = getattr(getattr(info_b, "age", None), "name", "ADULT")

    # Name helpers
    name_a = getattr(info_a, "first_name", "Сим")
    name_b = getattr(info_b, "first_name", "Сим")

    # Co-presence check: Sims MUST physically share space (in the same room or together outdoors).
    # Even when force=True is used in cheats, Sims cannot talk through walls or between yard and house.
    co_present, space_desc, dist = are_sims_co_present(sim_a, sim_b)
    if not co_present:
        log(f"[DIRECTOR CO-PRESENCE] Pair {name_a} & {name_b} rejected: not co-present ({space_desc})")
        return None

    # Check pair debounce unless forced or in isolated testing mode
    pair_key = (min(info_a.sim_id, info_b.sim_id), max(info_a.sim_id, info_b.sim_id))
    pair_on_cooldown = False
    if not force:
        if get_pair_cooldown_remaining_seconds(info_a.sim_id, info_b.sim_id) > 0:
            pair_on_cooldown = True

    def _base_filter_spark(cand: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if cand is None:
            return None
        trig = cand.get("trigger_type", "")
        if not force:
            try:
                from ai_thought_reader.config import get_director_enabled, is_director_trigger_enabled
                if not get_director_enabled():
                    return None
                lot_state_cur = get_director_lot_state()
                if not is_director_trigger_enabled(lot_state_cur, trig, default=True):
                    log(f"[DIRECTOR FILTER] Trigger '{trig}' is disabled in settings for lot state '{lot_state_cur}'")
                    return None
            except Exception:
                pass


        # 1. Custom per-trigger real-time cooldown check (e.g. 3 minutes for cooking)
        if not force and trig in TRIGGER_COOLDOWNS_REAL_SECONDS:
            if get_trigger_cooldown_remaining_seconds(trig) > 0:
                return None

        # 2. Debounce check: Prevent the exact same trigger from firing back-to-back.
        # Note: Triggers that are strictly per-Sim (truant_school_work, negative_mood_reaction)
        # already have daily limits per Sim and must not block other family members.
        if not force and trig not in TRIGGER_COOLDOWNS_REAL_SECONDS and trig in _trigger_last_scene_sim_time and trig not in ("truant_school_work", "negative_mood_reaction"):
            last_trig_time = _trigger_last_scene_sim_time.get(trig)
            if last_trig_time is not None:
                passed_trig = get_sim_minutes_between(last_trig_time, now)
                if passed_trig < TRIGGER_DEBOUNCE_COOLDOWN_MINUTES:
                    return None

        try:
            from ai_thought_reader.config import is_director_trigger_immediate, get_director_trigger_priority
            is_imm = is_director_trigger_immediate(trig)
            cand["priority"] = get_director_trigger_priority(trig, cand.get("priority", 50))
        except Exception:
            is_imm = trig in IMMEDIATE_TRIGGERS
        # Immediate triggers always pass; routine triggers are suppressed if pair is on cooldown or household is in silence
        if (pair_on_cooldown or allow_immediate_only) and not is_imm:
            log(f"[DIRECTOR FILTER] Trigger '{trig}' suppressed: pair_cooldown={pair_on_cooldown}, imm_only={allow_immediate_only}")
            return None

        # 3. Strict Lot State check:
        lot_state = get_director_lot_state()
        if not force:
            if lot_state == DIRECTOR_STATE_HOME and trig not in HOME_TRIGGERS:
                log(f"[DIRECTOR FILTER] Trigger '{trig}' not allowed in HOME_TRIGGERS")
                return None
            elif lot_state == DIRECTOR_STATE_VISITING_FRIENDS and trig not in VISITING_FRIENDS_TRIGGERS:
                log(f"[DIRECTOR FILTER] Trigger '{trig}' not in VISITING_FRIENDS_TRIGGERS")
                return None
            elif lot_state == DIRECTOR_STATE_VISITING_RELATIVES and trig not in VISITING_RELATIVES_TRIGGERS:
                log(f"[DIRECTOR FILTER] Trigger '{trig}' not in VISITING_RELATIVES_TRIGGERS")
                return None
            elif lot_state == DIRECTOR_STATE_COMMUNITY and trig not in COMMUNITY_TRIGGERS:
                log(f"[DIRECTOR FILTER] Trigger '{trig}' not in COMMUNITY_TRIGGERS")
                return None
            elif lot_state == DIRECTOR_STATE_OTHER:
                log(f"[DIRECTOR FILTER] Trigger '{trig}' rejected for state OTHER")
                return None

        # 4. NPC <-> NPC filter:
        # If neither Sim belongs to the player's active household:
        # On visiting lots: restricted to resident hosts.
        # On player's home lot / community lots: restricted to approved NPC_NPC_ALLOWED_TRIGGERS.
        if not force:
            is_a_played = is_sim_active_guest(info_a)
            is_b_played = is_sim_active_guest(info_b)
            is_npc_npc = (not is_a_played) and (not is_b_played)
            if is_npc_npc:
                if lot_state in (DIRECTOR_STATE_HOME, DIRECTOR_STATE_COMMUNITY):
                    if trig not in NPC_NPC_ALLOWED_TRIGGERS:
                        return None
                else:
                    if not (is_sim_host_resident(info_a) and is_sim_host_resident(info_b)):
                        return None
                    if trig not in NPC_NPC_ALLOWED_TRIGGERS:
                        return None

        return cand

    curr_day = int(get_current_sim_day())
    lot_state = get_director_lot_state()

    # Evaluate mode-specific triggers first (without ambient fallback)
    visiting_spark = None
    if lot_state == DIRECTOR_STATE_VISITING_FRIENDS:
        visiting_spark = evaluate_visiting_friends_spark(
            sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
            space_desc, dist, now, hour, pair_key, force, allow_immediate_only, _base_filter_spark,
            allow_fallback=False
        )
    elif lot_state == DIRECTOR_STATE_VISITING_RELATIVES:
        visiting_spark = evaluate_visiting_relatives_spark(
            sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
            space_desc, dist, now, hour, pair_key, force, allow_immediate_only, _base_filter_spark,
            allow_fallback=False
        )
    elif lot_state == DIRECTOR_STATE_COMMUNITY:
        visiting_spark = evaluate_community_lot_spark(
            sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
            space_desc, dist, now, hour, pair_key, force, allow_immediate_only, _base_filter_spark,
            allow_fallback=False
        )
    elif not force and lot_state != DIRECTOR_STATE_HOME:
        return None

    # Evaluate NPC and Guest scenarios on player's Home lot
    npc_home_spark = None
    if lot_state == DIRECTOR_STATE_HOME or force:
        is_a_played = is_sim_active_guest(info_a)
        is_b_played = is_sim_active_guest(info_b)
        if (not is_a_played) or (not is_b_played) or force:
            npc_home_spark = evaluate_npc_home_spark(
                sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
                space_desc, dist, now, hour, pair_key, force, allow_immediate_only, _base_filter_spark,
                allow_fallback=False
            )

    # Immediate return if visiting trigger or NPC home trigger has max priority >= 90
    if visiting_spark is not None and visiting_spark.get("priority", 0) >= 100:
        return visiting_spark
    if npc_home_spark is not None and npc_home_spark.get("priority", 0) >= 90:
        return npc_home_spark

    def _filter_spark(cand: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        sp = _base_filter_spark(cand)
        if sp is None:
            return None
        best = sp
        if visiting_spark is not None and visiting_spark.get("priority", 0) > best.get("priority", 0):
            best = visiting_spark
        if npc_home_spark is not None and npc_home_spark.get("priority", 0) > best.get("priority", 0):
            best = npc_home_spark
        return best

    # =========================================================================
    # DETECTOR 1: Возвращение со смены (Работа / Школа)
    # Окно: в течение 1 часа после возвращения при первой встрече в комнате.
    # =========================================================================
    for returning_info, other_info in [(info_a, info_b), (info_b, info_a)]:
        ret_id = returning_info.sim_id
        ret_time = _sim_work_return_tracker.get(ret_id)
        mins_since_ret = None
        if ret_time is not None:
            mins_since_ret = get_sim_minutes_between(ret_time, now)
        else:
            mins_since_ret = get_minutes_since_sim_shift_ended(returning_info, now)

        if mins_since_ret is not None and mins_since_ret <= WORK_RETURN_WINDOW_MINUTES:
            d_key = f"work_return_{ret_id}"
            if can_trigger_fire_today(d_key, "work_return", force=force):
                r_name = getattr(returning_info, "first_name", "Сим")
                o_name = getattr(other_info, "first_name", "Сим")
                sp = _filter_spark({
                    "trigger_type": "work_return",
                    "priority": 100,
                    "premise": f"{r_name} вернулся домой со смены (работы или школы) и встречает {o_name} ({space_desc.lower()}).",
                    "participants": [returning_info, other_info],
                    "daily_key": d_key,
                    "consume_work_tracker_sim_id": ret_id,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 0.8: Смерть персонажа / Костлявая Смерть (witness_death) [МГНОВЕННОЕ]
    # Приоритет: 98 (вдвоем) / 99 (один на один со Смертью). Экстренное скорбное событие на участке.
    # Включает имя погибшего и степень родства (если родственник; иначе только имя).
    # =========================================================================
    death_info = detect_death_or_reaper_in_scene(sim_a, sim_b, info_a, info_b, act_a, act_b)
    if death_info is not None:
        d_key_death = f"death_{pair_key[0]}_{pair_key[1]}_{int(get_current_sim_day())}"
        if can_trigger_fire_today(d_key_death, "witness_death", force=force):
            is_reaper_scene = is_grim_reaper(info_a) or is_grim_reaper(info_b)
            is_a_dying = is_sim_actively_dying(sim_a) or getattr(sim_a, "is_dying", False) or getattr(info_a, "is_dead", False)
            is_b_dying = is_sim_actively_dying(sim_b) or getattr(sim_b, "is_dying", False) or getattr(info_b, "is_dead", False)

            if is_reaper_scene:
                survivor_info = info_a if not is_grim_reaper(info_a) else info_b
                reaper_info = info_b if not is_grim_reaper(info_a) else info_a
                s_name = getattr(survivor_info, "first_name", "Сим")
                s_gender = getattr(getattr(survivor_info, "gender", None), "name", "MALE")
                stayed_verb = "осталась" if s_gender == "FEMALE" else "остался"
                him_her = "ей" if s_gender == "FEMALE" else "ему"
                dead_sim = find_dying_or_dead_sim_info(sim_a, sim_b)
                dead_desc = build_dead_sim_description(dead_sim, survivor_info, None)
                premise = f"{s_name} остался(ась) один на один с Костлявой Смертью после гибели {dead_desc} и говорит с ней (реакция зависит от характера и ситуации)."
                prio = 99
                participants = [survivor_info, reaper_info]
                dying_sim_id = 0
                survivor_sim_id = getattr(survivor_info, "sim_id", 0)
            elif is_a_dying != is_b_dying:
                # ONE PARTICIPANT IS DYING, THE OTHER IS THE LIVING SURVIVOR -> FAREWELL DIALOGUE!
                dying_part = info_a if is_a_dying else info_b
                survivor_part = info_b if is_a_dying else info_a
                s_name = getattr(survivor_part, "first_name", "Сим")
                d_name = getattr(dying_part, "first_name", "Сим")
                kinship = get_dead_sim_kinship_label(survivor_part, dying_part)
                kin_desc = f" ({kinship})" if kinship else ""

                premise = (
                    f"{d_name}{kin_desc} погибает прямо сейчас на глазах у {s_name}. "
                    f"Это их последний диалог перед смертью: {d_name} говорит слабым угасающим голосом (...), "
                    f"а реакция и слова {s_name} зависят от их отношений и характеров."
                )
                prio = 100
                participants = [dying_part, survivor_part]
                dying_sim_id = getattr(dying_part, "sim_id", 0)
                survivor_sim_id = getattr(survivor_part, "sim_id", 0)
            else:
                dead_sim = find_dying_or_dead_sim_info(sim_a, sim_b)
                dead_desc = build_dead_sim_description(dead_sim, info_a, info_b)
                premise = f"{name_a} и {name_b} стали свидетелями гибели {dead_desc} и появления Смерти, обсуждая произошедшее."
                prio = 98
                participants = [info_a, info_b]
                dying_sim_id = 0
                survivor_sim_id = 0

            sp = _filter_spark({
                "trigger_type": "witness_death",
                "priority": prio,
                "premise": premise,
                "participants": participants,
                "daily_key": d_key_death,
                "dying_sim_id": dying_sim_id,
                "survivor_sim_id": survivor_sim_id,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 0.9: Пожар на участке (fire_hazard) [МГНОВЕННОЕ]
    # Приоритет: 96. Экстренная опасность возгорания.
    # =========================================================================
    if is_fire_active_on_lot() or is_sim_reacting_to_fire(sim_a, info_a, act_a) or is_sim_reacting_to_fire(sim_b, info_b, act_b):
        d_key_fire = f"fire_{pair_key[0]}_{pair_key[1]}_{int(get_current_sim_day())}"
        if can_trigger_fire_today(d_key_fire, "fire_hazard", force=force):
            fire_summary = "на участке вспыхнул пожар"
            try:
                from ai_thought_reader.context import get_fire_hazard_context
                f_ctx = get_fire_hazard_context(info_a, other_sim_info=info_b, is_en=False)
                if f_ctx and f_ctx.get("summary"):
                    fire_summary = f_ctx["summary"]
            except Exception:
                pass

            premise = (
                f"На участке возник пожар ({fire_summary}). "
                f"Персонажи понимают, что начался пожар, их реакция, слова и поведение зависят от их характеров и отношений."
            )
            sp = _filter_spark({
                "trigger_type": "fire_hazard",
                "priority": 96,
                "premise": premise,
                "participants": [info_a, info_b],
                "daily_key": d_key_fire,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 1.2: Схватки и роды у персонажа (sim_in_labor) [МГНОВЕННОЕ]
    # Приоритет: 97. Чрезвычайная ситуация — активные роды и схватки прямо сейчас!
    # =========================================================================
    for mom_sim, other_sim, mom_inf, other_inf, m_act, o_act in [
        (sim_a, sim_b, info_a, info_b, act_a, act_b),
        (sim_b, sim_a, info_b, info_a, act_b, act_a)
    ]:
        if is_sim_in_labor(mom_sim, mom_inf, m_act):
            d_key_labor = f"labor_{mom_inf.sim_id}_{int(get_current_sim_day())}"
            if can_trigger_fire_today(d_key_labor, "sim_in_labor", force=force):
                m_name = getattr(mom_inf, "first_name", "Сим")
                o_name = getattr(other_inf, "first_name", "Сим")
                m_gender = getattr(getattr(mom_inf, "gender", None), "name", "FEMALE")
                is_male = (m_gender == "MALE")

                is_alien = False
                try:
                    from ai_thought_reader.config import get_experimental_flag
                    if is_male and get_experimental_flag("alien_male_pregnancy"):
                        is_alien = True
                except Exception:
                    pass

                if is_alien:
                    premise = (
                        f"ЧРЕЗВЫЧАЙНАЯ СИТУАЦИЯ: У {m_name} прямо сейчас начались схватки и внеземные роды (мудлет «Пора!»). "
                        f"Инопланетный малыш рождается сию секунду на глазах у {o_name}. "
                        f"Реакция, поведение и слова персонажей зависят исключительно от их характеров, отношений, мотивов и текущей обстановки."
                    )
                else:
                    premise = (
                        f"ЧРЕЗВЫЧАЙНАЯ СИТУАЦИЯ: У {m_name} прямо сейчас начались болезненные схватки и роды (мудлет «Пора!»). "
                        f"Ребенок рождается сию секунду на глазах у {o_name}. "
                        f"Реакция, поведение и слова персонажей зависят исключительно от их характеров, отношений, мотивов и текущей обстановки."
                    )

                sp = _filter_spark({
                    "trigger_type": "sim_in_labor",
                    "priority": 97,
                    "premise": premise,
                    "participants": [mom_inf, other_inf],
                    "daily_key": d_key_labor,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 1.25: Неожиданный вход в приватную / интимную сцену (walk_in_intimacy) [МГНОВЕННОЕ]
    # Приоритет: 94 (если среди участников романтический партнёр вошедшего — измена) / 91 (общий вход).
    # Окно: в процессе ИЛИ в течение 8 сим-минут после завершения (участники ещё в комнате).
    # Универсально масштабируется: одиночное уединение (1), пара (2), группа (3+).
    # =========================================================================
    for intruder_sim, actor_sim, intruder_inf, actor_inf in [
        (sim_a, sim_b, info_a, info_b),
        (sim_b, sim_a, info_b, info_a)
    ]:
        a_id = getattr(actor_inf, "sim_id", 0)
        intruder_id = getattr(intruder_inf, "sim_id", 0)
        if not a_id or not intruder_id or a_id == intruder_id:
            continue

        intimacy_entry = _sim_recent_intimacy_tracker.get(a_id)
        is_active = False
        mins_ago = 0.0

        if intimacy_entry is not None and now is not None:
            t_stamp = intimacy_entry.get("timestamp")
            if t_stamp is not None:
                mins_diff = get_sim_minutes_between(t_stamp, now)
                if mins_diff is not None and mins_diff <= INTIMACY_WALK_IN_WINDOW_MINUTES:
                    is_active = intimacy_entry.get("is_active", False)
                    mins_ago = mins_diff
                else:
                    _sim_recent_intimacy_tracker.pop(a_id, None)
                    intimacy_entry = None
            else:
                intimacy_entry = None

        # Fallback check if actively in sex right now but tracker hadn't ticked yet
        if intimacy_entry is None:
            sex_info = None
            try:
                from ai_thought_reader.context import get_sim_active_sex_info
                sex_info = get_sim_active_sex_info(actor_inf)
            except Exception:
                sex_info = None

            if not sex_info and actor_sim is not None and hasattr(actor_sim, "get_all_running_and_queued_interactions"):
                try:
                    for inter in actor_sim.get_all_running_and_queued_interactions():
                        aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                        if any(k in aff_name for k in ("woohoo", "mess_around", "tryforbaby", "ww_sex")):
                            target = getattr(inter, "target", None)
                            t_info = getattr(target, "sim_info", target) if target else None
                            t_id = getattr(t_info, "sim_id", 0)
                            actor_ids = [a_id]
                            if t_id and t_id != a_id:
                                actor_ids.append(t_id)
                            sex_info = {
                                "actor_sim_ids": actor_ids,
                                "total_participants": len(actor_ids),
                                "location_and_privacy": space_desc,
                                "partners": getattr(t_info, "first_name", "") if t_info else ""
                            }
                            break
                except Exception:
                    pass

            if sex_info:
                actor_ids = sex_info.get("actor_sim_ids", [a_id])
                total_parts = len(actor_ids)
                if total_parts <= 1:
                    scene_scale = "одиночная приватность (уединение / личное пространство)"
                elif total_parts == 2:
                    scene_scale = "парная интимная сцена (вуху / пара)"
                else:
                    scene_scale = f"групповая интимная сцена ({total_parts} участников)"
                loc_phrase = sex_info.get("location_and_privacy") or space_desc
                intimacy_entry = {
                    "timestamp": now,
                    "actor_ids": actor_ids,
                    "total_participants": total_parts,
                    "location_and_privacy": loc_phrase,
                    "scene_scale": scene_scale,
                    "is_active": True,
                }
                is_active = True
                mins_ago = 0.0

        if intimacy_entry is not None:
            actor_ids = intimacy_entry.get("actor_ids", [a_id])
            if intruder_id not in actor_ids:
                total_parts = intimacy_entry.get("total_participants", len(actor_ids))
                scene_scale = intimacy_entry.get("scene_scale", "интимная сцена")
                loc_phrase = intimacy_entry.get("location_and_privacy", space_desc)

                sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
                betrayed_by_sim = None
                if sim_mgr and len(actor_ids) >= 2:
                    for act_id in actor_ids:
                        act_inf = sim_mgr.get(act_id)
                        if act_inf and is_sim_in_romantic_relationship(intruder_inf, act_inf):
                            # Check if at least one other participant is NOT exempt (not polyamorous/open)
                            has_non_exempt_lover = False
                            for other_id in actor_ids:
                                if other_id != act_id:
                                    other_inf = sim_mgr.get(other_id)
                                    if not is_polyamorous_or_exempt_from_cheating(act_inf, intruder_inf, other_inf):
                                        has_non_exempt_lover = True
                                        break
                            if has_non_exempt_lover:
                                betrayed_by_sim = act_inf
                                break

                d_key_walkin = f"walk_in_intimacy_{intruder_id}_{a_id}_{int(get_current_sim_day())}"
                if can_trigger_fire_today(d_key_walkin, "walk_in_intimacy", force=force):
                    i_name = getattr(intruder_inf, "first_name", "Сим")
                    a_name = getattr(actor_inf, "first_name", "Сим")
                    timing_desc = "прямо сейчас в процессе" if is_active else f"только что (буквально {int(mins_ago)} мин назад)"

                    if betrayed_by_sim:
                        b_name = getattr(betrayed_by_sim, "first_name", "Сим")
                        premise = f"{i_name} заходит в комнату и застаёт своего партнёра ({b_name}) во время уединения ({scene_scale})."
                        prio = 94
                    else:
                        premise = f"{i_name} неожиданно заходит и застаёт {a_name} во время уединения ({scene_scale})."
                        prio = 91

                    sp = _filter_spark({
                        "trigger_type": "walk_in_intimacy",
                        "priority": prio,
                        "premise": premise,
                        "participants": [intruder_inf, actor_inf],
                        "daily_key": d_key_walkin,
                        "consume_intimacy_tracker_sim_id": a_id,
                        "total_participants": total_parts,
                        "scene_scale": scene_scale,
                        "loc_phrase": loc_phrase,
                        "betrayed_partner_name": getattr(betrayed_by_sim, "first_name", "") if betrayed_by_sim else "",
                        "is_betrayal": bool(betrayed_by_sim),
                        "intruder_name": i_name,
                        "actor_name": a_name,
                        "is_active": is_active,
                        "mins_ago": int(mins_ago),
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 1.3: Застигнутая измена / Романтика на глазах партнёра (caught_cheating) [МГНОВЕННОЕ]
    # Приоритет: 93. Романтика или флирт одного партнёра с третьим симом на глазах второго.
    # =========================================================================
    for cheater_sim, partner_sim, cheater_inf, partner_inf in [
        (sim_a, sim_b, info_a, info_b),
        (sim_b, sim_a, info_b, info_a)
    ]:
        if is_sim_in_romantic_relationship(partner_inf, cheater_inf):
            # Guarantee the betrayed partner is correctly identified:
            # If cheater_inf has jealousy/boundary buff and partner_inf does not, swap!
            try:
                c_buffs = get_sim_buff_names_safe(cheater_inf)
                p_buffs = get_sim_buff_names_safe(partner_inf)
                JEALOUS_TRIGS = ("boundary", "boundaries", "relationshipboundaries", "jealousy", "jealous", "cheatingwitnessed", "flirtwitnessed")
                if any(any(jt in b for jt in JEALOUS_TRIGS) for b in c_buffs) and not any(any(jt in b for jt in JEALOUS_TRIGS) for b in p_buffs):
                    cheater_sim, partner_sim = partner_sim, cheater_sim
                    cheater_inf, partner_inf = partner_inf, cheater_inf
            except Exception:
                pass

            third_party, act_verb = get_sim_romantic_target(cheater_sim, cheater_inf, partner_info=partner_inf)
            if (
                third_party
                and getattr(third_party, "sim_id", 0) != getattr(partner_inf, "sim_id", 0)
                and getattr(third_party, "sim_id", 0) != getattr(cheater_inf, "sim_id", 0)
                and not is_polyamorous_or_exempt_from_cheating(cheater_inf, partner_inf, third_party)
            ):
                d_key_cheat = f"caught_cheating_{partner_inf.sim_id}_{cheater_inf.sim_id}_{int(get_current_sim_day())}"
                if can_trigger_fire_today(d_key_cheat, "caught_cheating", force=force):
                    c_name = getattr(cheater_inf, "first_name", "Сим")
                    p_name = getattr(partner_inf, "first_name", "Сим")
                    t_name = getattr(third_party, "first_name", "другой персонаж")
                    action_phrase = f"{act_verb} с {t_name}" if "флирт" in act_verb else f"{act_verb} {t_name}"
                    sp = _filter_spark({
                        "trigger_type": "caught_cheating",
                        "priority": 93,
                        "premise": (
                            f"ОСТРАЯ ДРАМА / ПРЕДАТЕЛЬСТВО: {p_name} прямо на своих глазах застает своего романтического партнёра ({c_name}), "
                            f"который только что {action_phrase}."
                        ),
                        "participants": [partner_inf, cheater_inf],
                        "daily_key": d_key_cheat,
                        "consume_romance_tracker_sim_id": getattr(cheater_inf, "sim_id", 0),
                        "cheating_action_verb": act_verb,
                        "third_party_name": t_name,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 1.35: Свидетель застаёт измену (witnessed_cheating) [МГНОВЕННОЕ]
    # Приоритет: 92. Родственник (дочь/сын/родитель/сестра/брат) или друг/знакомый
    # застает романтическое действие персонажа с третьим лицом втайне от партнёра.
    # ВАЖНО: Никаких навязанных эмоций в промпте — чистые факты, метрики отношений,
    # знание тайны и свобода реакции LLM на основе черт и динамики семьи.
    # =========================================================================
    for witness_sim, cheater_sim, witness_inf, cheater_inf in [
        (sim_a, sim_b, info_a, info_b),
        (sim_b, sim_a, info_b, info_a)
    ]:
        committed_partners = find_all_committed_partners(cheater_inf)
        if committed_partners:
            partner_ids = {getattr(p, "sim_id", 0) for p in committed_partners}
            w_id = getattr(witness_inf, "sim_id", 0)
            c_id = getattr(cheater_inf, "sim_id", 0)

            # Witness must NOT be one of the partners (handled by caught_cheating)
            if w_id not in partner_ids:
                third_party, act_verb = get_sim_romantic_target(cheater_sim, cheater_inf, partner_info=None)
                l_id = getattr(third_party, "sim_id", 0) if third_party else 0

                # Filter committed_partners to only those who are ACTUALLY betrayed (not polyamorous/exempt)
                betrayed_partners = [
                    p for p in committed_partners
                    if not is_polyamorous_or_exempt_from_cheating(cheater_inf, p, third_party)
                ] if (third_party and l_id and l_id not in partner_ids and l_id != c_id and l_id != w_id) else []

                if betrayed_partners:
                    partner_inf = betrayed_partners[0]
                    d_key_wit_cheat = f"witnessed_cheating_{w_id}_{c_id}_{int(get_current_sim_day())}"
                    if can_trigger_fire_today(d_key_wit_cheat, "witnessed_cheating", force=force):
                        w_name = getattr(witness_inf, "first_name", "Сим")
                        c_name = getattr(cheater_inf, "first_name", "Сим")
                        p_name = getattr(partner_inf, "first_name", "Сим")
                        l_name = getattr(third_party, "first_name", "другой персонаж")

                        mins_ago = 0
                        if c_id in _sim_recent_romance_tracker and now is not None:
                            t_st = _sim_recent_romance_tracker[c_id].get("timestamp")
                            if t_st is not None:
                                m = get_sim_minutes_between(t_st, now)
                                if m is not None:
                                    mins_ago = int(m)

                        if mins_ago <= 1:
                            timing_desc = "только что"
                            action_phrase = f"{act_verb} с {l_name}" if "флирт" in act_verb else f"{act_verb} {l_name}"
                        else:
                            timing_desc = f"только что ({mins_ago} мин назад)"
                            action_phrase = f"буквально {mins_ago} мин назад {act_verb} с {l_name}" if "флирт" in act_verb else f"буквально {mins_ago} мин назад {act_verb} {l_name}"

                        # Determine witness role & kinship relative to cheater and partner
                        w_role_cheater = get_sim_kinship_or_role_label(witness_inf, cheater_inf)
                        w_role_partner = get_sim_kinship_or_role_label(witness_inf, partner_inf)

                        # Determine if witness is child/relative or friend
                        is_family = any(k in f"{w_role_cheater} {w_role_partner}".lower() for k in [
                            "дочь", "сын", "мать", "отец", "сестра", "брат", "племян", "внук", "кузен", "родствен"
                        ])
                        w_role_desc = f"{w_role_cheater} персонажа {c_name}" if w_role_cheater else "свидетель"
                        if is_family and w_role_partner and w_role_partner != "знакомый":
                            w_role_desc += f" (также {w_role_partner} персонажа {p_name})"

                        # Scores & Sentiments
                        fw_c, rw_c = get_sim_relationship_scores(witness_inf, cheater_inf)
                        fw_p, _ = get_sim_relationship_scores(witness_inf, partner_inf)
                        fw_l, _ = get_sim_relationship_scores(witness_inf, third_party)
                        sent_c = get_sim_sentiments_summary(witness_inf, cheater_inf)
                        sent_p = get_sim_sentiments_summary(witness_inf, partner_inf)

                        # Check if witness already knew
                        witness_already_knows = False
                        try:
                            from ai_social_pc.event_memory_manager import get_active_memories
                            mems = get_active_memories(w_id, c_id) + get_active_memories(w_id, partner_inf.sim_id)
                            for mem in mems:
                                ev = mem.get("event_type", "")
                                if any(k in ev for k in ("cheating", "secret", "affair", "lover")):
                                    witness_already_knows = True
                                    break
                        except Exception:
                            pass

                        partner_names_str = " и ".join(getattr(p, "first_name", "Партнёр") for p in betrayed_partners)
                        partner_word = "своих постоянных партнёров" if len(betrayed_partners) > 1 else "своего партнёра"
                        premise = f"{w_name} ({w_role_desc}) замечает, как {c_name} {action_phrase} втайне от {partner_word} ({partner_names_str})."

                        sp = _filter_spark({
                            "trigger_type": "witnessed_cheating",
                            "priority": 92,
                            "premise": premise,
                            "participants": [witness_inf, cheater_inf],
                            "daily_key": d_key_wit_cheat,
                            "consume_romance_tracker_sim_id": c_id,
                            "cheating_action_verb": act_verb,
                            "cheater_name": c_name,
                            "partner_name": p_name,
                            "lover_name": l_name,
                            "action_phrase": action_phrase,
                            "witness_role_desc": w_role_desc,
                            "witness_already_knows": witness_already_knows,
                            "rel_context": {
                                "fw_c": fw_c,
                                "rw_c": rw_c,
                                "fw_p": fw_p,
                                "fw_l": fw_l,
                                "sent_c": sent_c,
                                "sent_p": sent_p,
                                "role_cheater": w_role_cheater,
                                "role_partner": w_role_partner,
                            }
                        })
                        if sp is not None:
                            return sp

    # =========================================================================
    # DETECTOR 1.5: Прогул школы / смены (Школа / Работа) [МГНОВЕННОЕ]
    # Приоритет: 90. Срабатывает мгновенно, пробивая паузу тишины дома.
    # Суточный лимит: 1 раз в день НА ОДНОГО СИМА (например, жена может
    # отчитать дочь за прогул школы, а затем мужа за прогул работы).
    # =========================================================================
    for truant_info, other_info, t_age, o_age in [(info_a, info_b, age_a, age_b), (info_b, info_a, age_b, age_a)]:
        d_key_truant = f"truant_{truant_info.sim_id}"
        if can_trigger_fire_today(d_key_truant, "truant_school_work", force=force):
            is_truant, is_school, car_title, status_desc = is_sim_truant_from_work_or_school(truant_info)
            if is_truant:
                t_name = getattr(truant_info, "first_name", "Сим")
                o_name = getattr(other_info, "first_name", "Сим")
                if is_school or t_age in ("CHILD", "TEEN"):
                    premise = f"{t_name} прогуливает школу и остался дома в учебное время, а {o_name} застаёт его."
                else:
                    premise = f"{t_name} прогуливает работу и остался дома в рабочее время, а {o_name} застаёт его."
                sp = _filter_spark({
                    "trigger_type": "truant_school_work",
                    "priority": 90,
                    "premise": premise,
                    "participants": [other_info, truant_info],
                    "daily_key": d_key_truant,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 1.6: Удар током при ремонте техники (electrocuted_repair) [МГНОВЕННОЕ]
    # Приоритет: 89. Поражение электрическим током при починке приборов.
    # =========================================================================
    for shocked_sim, other_sim, shocked_inf, other_inf, s_act, o_act in [
        (sim_a, sim_b, info_a, info_b, act_a, act_b),
        (sim_b, sim_a, info_b, info_a, act_b, act_a)
    ]:
        if is_sim_electrocuted(shocked_sim, shocked_inf, s_act):
            d_key_elec = f"electrocuted_{shocked_inf.sim_id}_{int(get_current_sim_day())}"
            if can_trigger_fire_today(d_key_elec, "electrocuted_repair", force=force):
                s_name = getattr(shocked_inf, "first_name", "Сим")
                o_name = getattr(other_inf, "first_name", "Сим")
                sp = _filter_spark({
                    "trigger_type": "electrocuted_repair",
                    "priority": 89,
                    "premise": (
                        f"ПРОИСШЕСТВИЕ: {s_name} только что получил мощный удар электрическим током при починке техники "
                        f"(находится в ошалевшем состоянии, покрыт копотью) прямо на глазах у {o_name}. "
                        f"Слова и реакция персонажей зависят исключительно от их характеров, отношений и текущей обстановки."
                    ),
                    "participants": [other_inf, shocked_inf],
                    "daily_key": d_key_elec,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 2: Совместный обед / ужин (Кухня, барная стойка, диван)
    # ЗОЛОТОЙ МОМЕНТ: Совместная трапеза семьи — крайне редкое событие.
    # Мгновенный триггер с высоким приоритетом (89), пробивает паузу тишины дома!
    # Строгая проверка еды через affordances и regex: исключены ложные 'Стоит на мЕСТе'!
    # =========================================================================
    is_eating_a = is_sim_eating(sim_a, info_a, act_a)
    is_eating_b = is_sim_eating(sim_b, info_b, act_b)

    if is_eating_a and is_eating_b and co_present:
        food_a = get_sim_eating_food_name(sim_a, info_a, act_a)
        food_b = get_sim_eating_food_name(sim_b, info_b, act_b)

        if food_a and food_b:
            if food_a.lower() == food_b.lower():
                premise = f"{name_a} и {name_b} вместе едят «{food_a}»."
            else:
                premise = f"{name_a} и {name_b} вместе едят ({name_a} ест «{food_a}», а {name_b} — «{food_b}»)."
        elif food_a or food_b:
            single_food = food_a or food_b
            premise = f"{name_a} и {name_b} вместе едят (на столе: «{single_food}»)."
        else:
            premise = f"{name_a} и {name_b} вместе едят за одним столом."

        sp = _filter_spark({
            "trigger_type": "eating_together",
            "priority": 89,
            "premise": premise,
            "participants": [info_a, info_b]
        })
        if sp is not None:
            return sp

    # =========================================================================
    # DETECTOR 2.1: После интимной близости (WickedWhims / WooHoo)
    # Окно: в течение 30 минут после завершения (на полу, кровати, диване, в душе и т.д.)
    # Никаких требований к уровню романтики (подходит и для страсти, и для лёгкого секса / FWB).
    # =========================================================================
    if age_a in ("TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for post_info, other_info in [(info_a, info_b), (info_b, info_a)]:
            p_id = post_info.sim_id
            o_id = other_info.sim_id
            post_entry = _sim_post_woohoo_tracker.get(p_id)
            post_time = None
            partner_ids = set()
            where_phrase = ""
            if isinstance(post_entry, (tuple, list)):
                post_time = post_entry[0]
                if len(post_entry) > 1 and isinstance(post_entry[1], (set, list)):
                    partner_ids = set(post_entry[1])
                if len(post_entry) > 2 and isinstance(post_entry[2], str):
                    where_phrase = post_entry[2]
            elif post_entry is not None:
                post_time = post_entry

            # If partner_ids was captured during sex, make sure other_info was actually the sex partner
            if partner_ids and o_id not in partner_ids:
                continue

            is_recent_post = False
            if post_time is not None and get_sim_minutes_between(post_time, now) <= POST_WOOHOO_WINDOW_MINUTES:
                is_recent_post = True
            if not is_recent_post:
                try:
                    for b in getattr(post_info, "buffs", []):
                        b_name = getattr(b, "__class__", type(b)).__name__.lower()
                        if any(k in b_name for k in ["afterglow", "woohoo", "romantic_high"]):
                            is_recent_post = True
                            break
                except Exception:
                    pass

            if is_recent_post:
                d_key_post = f"ww_post_intimacy_{pair_key[0]}_{pair_key[1]}"
                if can_trigger_fire_today(d_key_post, "ww_post_intimacy", force=force):
                    p_name = getattr(post_info, "first_name", "Сим")
                    o_name = getattr(other_info, "first_name", "Сим")
                    loc_suffix = f" ({where_phrase})" if where_phrase else ""
                    premise = f"{p_name} и {o_name} только что завершили интимную близость (секс / вуху){loc_suffix} и находятся рядом, приходя в себя."
                    sp = _filter_spark({
                        "trigger_type": "ww_post_intimacy",
                        "priority": 87,
                        "premise": premise,
                        "participants": [post_info, other_info],
                        "daily_key": d_key_post,
                        "consume_woohoo_tracker_sim_id": p_id,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 2.2: Оплата счетов за дом (paid_bills) [МГНОВЕННОЕ]
    # Приоритет: 86. Окно 1 час после оплаты счетов при встрече с симом от подростка и старше.
    # =========================================================================
    if age_a in ("TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for payer_sim, other_sim, payer_inf, other_inf in [
            (sim_a, sim_b, info_a, info_b),
            (sim_b, sim_a, info_b, info_a)
        ]:
            p_id = payer_inf.sim_id
            paid_time = _sim_bills_paid_tracker.get(p_id)
            if paid_time is not None:
                mins_since_paid = get_sim_minutes_between(paid_time, now)
                if mins_since_paid is not None and mins_since_paid <= 60.0:
                    d_key_bills = f"paid_bills_{p_id}_{int(get_current_sim_day())}"
                    if can_trigger_fire_today(d_key_bills, "paid_bills", force=force):
                        p_name = getattr(payer_inf, "first_name", "Сим")
                        o_name = getattr(other_inf, "first_name", "Сим")
                        sp = _filter_spark({
                            "trigger_type": "paid_bills",
                            "priority": 86,
                            "premise": (
                                f"ФИНАНСЫ И СЧЕТА: {p_name} оплатил счета за дом и поднимает тему бюджета с {o_name}. "
                                f"Тон разговора и реакция персонажей зависят от их благосостояния, черт характера (бережливость, расточительность, эгоизм) и отношений."
                            ),
                            "participants": [payer_inf, other_inf],
                            "daily_key": d_key_bills,
                            "consume_bills_tracker_sim_id": p_id,
                        })
                        if sp is not None:
                            return sp

    # =========================================================================
    # DETECTOR 3: Готовка + Ожидание на кухне
    # Один готовит у плиты, второй рядом в помещении
    # =========================================================================
    is_cooking_a = any(w in act_a for w in ["готовит", "жарит", "варит", "печет", "запекает", "cooking", "bake"])
    is_cooking_b = any(w in act_b for w in ["готовит", "жарит", "варит", "печет", "запекает", "cooking", "bake"])
    if not is_cooking_a and sim_a is not None and hasattr(sim_a, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_a.get_all_running_and_queued_interactions():
                aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                if any(k in aff_name for k in ("cook", "bake", "fry", "prepare_food", "make_recipe", "stove_cook")):
                    is_cooking_a = True
                    break
        except Exception:
            pass
    if not is_cooking_b and sim_b is not None and hasattr(sim_b, "get_all_running_and_queued_interactions"):
        try:
            for inter in sim_b.get_all_running_and_queued_interactions():
                aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                if any(k in aff_name for k in ("cook", "bake", "fry", "prepare_food", "make_recipe", "stove_cook")):
                    is_cooking_b = True
                    break
        except Exception:
            pass

    if is_cooking_a and not is_eating_b:
        d_key_cook = f"cooking_{info_a.sim_id}_{int(get_current_sim_day())}_{hour}"
        if can_trigger_fire_today(d_key_cook, "cooking_together", force=force):
            sp = _filter_spark({
                "trigger_type": "cooking_together",
                "priority": 86,
                "premise": f"{name_a} готовит еду у плиты, а {name_b} находится рядом на кухне.",
                "participants": [info_a, info_b],
                "daily_key": d_key_cook,
            })
            if sp is not None:
                return sp
    elif is_cooking_b and not is_eating_a:
        d_key_cook = f"cooking_{info_b.sim_id}_{int(get_current_sim_day())}_{hour}"
        if can_trigger_fire_today(d_key_cook, "cooking_together", force=force):
            sp = _filter_spark({
                "trigger_type": "cooking_together",
                "priority": 86,
                "premise": f"{name_b} готовит еду у плиты, а {name_a} находится рядом на кухне.",
                "participants": [info_b, info_a],
                "daily_key": d_key_cook,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 3.1: Сгоревшая еда на кухне
    # Повар: Подросток+, Свидетель: Ребенок+, 1 раз за инцидент
    # =========================================================================
    is_burnt_a = any(w in act_a for w in ["пригорев", "burnt", "сгоревш", "гарь", "подгорев"])
    is_burnt_b = any(w in act_b for w in ["пригорев", "burnt", "сгоревш", "гарь", "подгорев"])
    if is_burnt_a or is_burnt_b:
        cook_info = info_a if is_burnt_a else info_b
        wit_info = info_b if is_burnt_a else info_a
        c_name = getattr(cook_info, "first_name", "Сим")
        w_name = getattr(wit_info, "first_name", "Сим")
        d_key_burn = f"burnt_food_{cook_info.sim_id}_{int(get_current_sim_day())}_{hour}"
        if can_trigger_fire_today(d_key_burn, "burnt_food", force=force):
            sp = _filter_spark({
                "trigger_type": "burnt_food",
                "priority": 95,
                "premise": f"{c_name} сжег блюдо у плиты, на кухне стоит запах гари. {w_name} находится рядом.",
                "participants": [cook_info, wit_info],
                "daily_key": d_key_burn,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 3.3: Поломка сантехники / техники
    # Сломанный прибор, кран, унитаз, плита или лужа в помещении. 1 раз в день
    # =========================================================================
    has_broken_env, broken_names, rep_name, rep_target, rep_other = detect_broken_objects_in_scene(sim_a, sim_b, act_a, act_b)
    if has_broken_env:
        d_key_broken = f"broken_obj_{pair_key[0]}_{pair_key[1]}"
        if can_trigger_fire_today(d_key_broken, "broken_object", force=force):
            premise_text = build_broken_object_premise(name_a, name_b, broken_names, rep_name, rep_target, rep_other)
            sp = _filter_spark({
                "trigger_type": "broken_object",
                "priority": 92,
                "premise": premise_text,
                "participants": [info_a, info_b],
                "daily_key": d_key_broken,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 3.4: Грязь и испорченная еда (МГНОВЕННОЕ)
    # Грязная сантехника, плита, тумбы, тарелка с испорченной едой. 1 раз в день
    # =========================================================================
    has_dirty_env, dirty_items, cl_name, cl_target, cl_other = detect_dirty_environment_in_scene(sim_a, sim_b, act_a, act_b)
    if has_dirty_env:
        d_key_dirty = f"dirty_trash_{pair_key[0]}_{pair_key[1]}"
        if can_trigger_fire_today(d_key_dirty, "dirty_dish_trash", force=force):
            premise_text = build_dirty_environment_premise(name_a, name_b, dirty_items, cl_name, cl_target, cl_other)
            sp = _filter_spark({
                "trigger_type": "dirty_dish_trash",
                "priority": 87,
                "premise": premise_text,
                "participants": [info_a, info_b],
                "daily_key": d_key_dirty,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 4: Уроки школьника в доме
    # 1. homework_in_progress (Приоритет: 78):
    #    Школьник прямо сейчас учит уроки (в любое время суток!).
    #    - Родитель помогает (активная помощь / разбор темы)
    #    - Родитель рядом в комнате (надзор / контроль)
    #    - Сиблинги делают домашку вместе за одним столом/в комнате
    #    - Сиблинг рядом в комнате (старший подсказывает / младший отвлекает)
    # 2. homework_done (Приоритет: 76):
    #    Школьник закончил домашку (статус "сделано", прямо сейчас не учит). 06:00 - 23:00
    #    - С родителем: похвала, проверка тетрадей, разговор об оценках
    #    - С сиблингом: уроки сделаны, можно поиграть/отдохнуть
    # 3. homework_not_done (Приоритет: 80):
    #    У школьника еще не сделана домашка (прямо сейчас не учит), родитель рядом. 15:00 - 23:00
    # =========================================================================
    for child_sim, other_sim, child_info, other_info, c_age, o_age, c_act, o_act in [
        (sim_a, sim_b, info_a, info_b, age_a, age_b, act_a, act_b),
        (sim_b, sim_a, info_b, info_a, age_b, age_a, act_b, act_a)
    ]:
        if c_age in ("CHILD", "TEEN"):
            ch_name = getattr(child_info, "first_name", "Школьник")
            o_name = getattr(other_info, "first_name", "Сим")

            # --- 4.1. HOMEWORK_IN_PROGRESS (Школьник учит уроки прямо сейчас) ---
            if is_sim_doing_homework(child_sim, child_info, c_act):
                d_key_hw_prog = f"hw_prog_{child_info.sim_id}_{curr_day}"
                if can_trigger_fire_today(d_key_hw_prog, "homework_in_progress", force=force):
                    # Сценарий с Взрослым (Родитель / опекун / старший член семьи)
                    if o_age in ("YOUNGADULT", "ADULT", "ELDER"):
                        is_helping = is_sim_helping_with_homework(other_sim, other_info, o_act)
                        if is_helping:
                            premise = f"{ch_name} делает домашнее задание, а {o_name} помогает с уроками."
                            parts = [other_info, child_info]
                        else:
                            premise = f"{ch_name} делает домашнее задание, а {o_name} находится рядом в комнате."
                            parts = [child_info, other_info]
                        sp = _filter_spark({
                            "trigger_type": "homework_in_progress",
                            "priority": 78,
                            "premise": premise,
                            "participants": parts,
                            "daily_key": d_key_hw_prog,
                        })
                        if sp is not None:
                            return sp

                    # Сценарий с Сиблингом (второй ребёнок или подросток семьи)
                    elif o_age in ("CHILD", "TEEN"):
                        other_doing_hw = is_sim_doing_homework(other_sim, other_info, o_act)
                        if other_doing_hw:
                            premise = f"Сиблинги {ch_name} и {o_name} вместе делают домашнее задание."
                        else:
                            premise = f"{ch_name} делает домашнее задание, а {o_name} находится рядом в комнате."
                        sp = _filter_spark({
                            "trigger_type": "homework_in_progress",
                            "priority": 78,
                            "premise": premise,
                            "participants": [child_info, other_info],
                            "daily_key": d_key_hw_prog,
                        })
                        if sp is not None:
                            return sp

            # --- 4.2. Уроки НЕ в процессе: проверка сделана / не сделана ---
            else:
                hw_done = is_sim_homework_completed(child_info, child_sim)

                # HOMEWORK_DONE (Домашка сделана — 06:00 - 23:00)
                if hw_done and (6 <= hour <= 23):
                    d_key_done = f"hw_done_{child_info.sim_id}_{curr_day}"
                    if can_trigger_fire_today(d_key_done, "homework_done", force=force):
                        if o_age in ("YOUNGADULT", "ADULT", "ELDER"):
                            premise = f"{ch_name} сделал все школьные домашние задания, а {o_name} находится рядом в комнате."
                        elif o_age in ("CHILD", "TEEN"):
                            premise = f"{ch_name} закончил делать домашнее задание, а {o_name} находится рядом в комнате."
                        else:
                            premise = f"{ch_name} сделал все школьные домашние задания, а {o_name} находится рядом в комнате."

                        sp = _filter_spark({
                            "trigger_type": "homework_done",
                            "priority": 76,
                            "premise": premise,
                            "participants": [child_info, other_info],
                            "daily_key": d_key_done,
                        })
                        if sp is not None:
                            return sp

                # HOMEWORK_NOT_DONE (Домашка не сделана — 15:00 - 23:00)
                elif not hw_done and (15 <= hour <= 23) and o_age in ("YOUNGADULT", "ADULT", "ELDER"):
                    d_key_not_done = f"homework_not_done_{child_info.sim_id}_{curr_day}"
                    if can_trigger_fire_today(d_key_not_done, "homework_not_done", force=force):
                        sp = _filter_spark({
                            "trigger_type": "homework_not_done",
                            "priority": 80,
                            "premise": f"{ch_name} еще не сделал школьное домашнее задание, а {o_name} находится рядом в комнате.",
                            "participants": [other_info, child_info],
                            "daily_key": d_key_not_done,
                        })
                        if sp is not None:
                            return sp

    # =========================================================================
    # DETECTOR 4.3: «Почему не спишь?» ночью (23:00 - 04:00)
    # Взрослый застает ребенка/подростка неспящим. 1 раз в день
    # =========================================================================
    if (hour >= 23 or hour <= 4):
        for adult_info, kid_info, a_age, k_age in [(info_a, info_b, age_a, age_b), (info_b, info_a, age_b, age_a)]:
            if a_age in ("YOUNGADULT", "ADULT", "ELDER") and k_age in ("CHILD", "TEEN"):
                d_key_late = f"late_night_{kid_info.sim_id}"
                if can_trigger_fire_today(d_key_late, "late_night_awake", force=force):
                    a_name = getattr(adult_info, "first_name", "Взрослый")
                    k_name = getattr(kid_info, "first_name", "Школьник")
                    sp = _filter_spark({
                        "trigger_type": "late_night_awake",
                        "priority": 88,
                        "premise": f"{a_name} застает {k_name} бодрствующим глубокой ночью в комнате, когда пора спать.",
                        "participants": [adult_info, kid_info],
                        "daily_key": d_key_late,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 5: ТВ по жанрам (Оба смотрят один телевизор)
    # =========================================================================
    is_tv_a = is_sim_watching_tv(sim_a, info_a, act_a)
    is_tv_b = is_sim_watching_tv(sim_b, info_b, act_b)

    if is_tv_a and is_tv_b and co_present:
        # Determine TV genre if available in text
        genre_hint = "сериал / фильм"
        combined_act = f"{act_a} {act_b}"
        if "боевик" in combined_act or "action" in combined_act:
            genre_hint = "боевик"
        elif "комеди" in combined_act or "ситком" in combined_act:
            genre_hint = "комедию"
        elif "мелодрам" in combined_act or "романтик" in combined_act:
            genre_hint = "мелодраму"
        elif "ужас" in combined_act or "хоррор" in combined_act:
            genre_hint = "фильм ужасов"
        elif "новост" in combined_act or "политик" in combined_act:
            genre_hint = "новости"

        sp = _filter_spark({
            "trigger_type": "watching_tv_together",
            "priority": 70,
            "premise": f"{name_a} и {name_b} сидят рядом и смотрят по телевизору {genre_hint}.",
            "participants": [info_a, info_b]
        })
        if sp is not None:
            return sp

    # =========================================================================
    # DETECTOR 6: ПК сиблингов (Один играет на ПК, второй рядом в комнате)
    # Возраст: Child / Teen, 1 раз в день
    # =========================================================================
    if age_a in ("CHILD", "TEEN") and age_b in ("CHILD", "TEEN"):
        is_pc_a = is_sim_using_pc_or_laptop(sim_a, info_a, act_a)
        is_pc_b = is_sim_using_pc_or_laptop(sim_b, info_b, act_b)
        if is_pc_a != is_pc_b:
            d_key_pc = f"pc_siblings_{pair_key[0]}_{pair_key[1]}"
            if can_trigger_fire_today(d_key_pc, "pc_siblings_share", force=force):
                gamer_info = info_a if is_pc_a else info_b
                other_info = info_b if is_pc_a else info_a
                g_name = getattr(gamer_info, "first_name", "Сим")
                o_name = getattr(other_info, "first_name", "Сим")
                sp = _filter_spark({
                    "trigger_type": "pc_siblings_share",
                    "priority": 68,
                    "premise": f"{g_name} сидит за компьютером или ноутбуком, а {o_name} находится в этой же комнате.",
                    "participants": [gamer_info, other_info],
                    "daily_key": d_key_pc,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 6.1: Садоводство на участке (Уход за садом и растениями)
    # Один ухаживает за растениями в саду/теплице, второй рядом во дворе/комнате.
    # Приоритет: 75. 1 раз в день на садовода.
    # =========================================================================
    if age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for gardener_sim, other_sim, g_inf, o_inf, g_act, o_act in [
            (sim_a, sim_b, info_a, info_b, act_a, act_b),
            (sim_b, sim_a, info_b, info_a, act_b, act_a)
        ]:
            is_gard, gard_detail = is_sim_gardening(gardener_sim, g_inf, g_act)
            if is_gard:
                # Check proximity: either co_present, or both outdoors within 12m
                is_near = co_present
                if not is_near and gardener_sim is not None and other_sim is not None:
                    try:
                        from ai_thought_reader.context import get_sim_room_and_outdoor
                        _, out_g = get_sim_room_and_outdoor(gardener_sim)
                        _, out_o = get_sim_room_and_outdoor(other_sim)
                        if out_g and out_o:
                            pos_g = getattr(gardener_sim, "position", None)
                            pos_o = getattr(other_sim, "position", None)
                            if pos_g is not None and pos_o is not None and float((pos_g - pos_o).magnitude()) <= 12.0:
                                is_near = True
                    except Exception:
                        pass

                if is_near:
                    d_key_gard = f"gardening_{g_inf.sim_id}_{int(get_current_sim_day())}"
                    if can_trigger_fire_today(d_key_gard, "gardening_together", force=force):
                        g_name = getattr(g_inf, "first_name", "Сим")
                        o_name = getattr(o_inf, "first_name", "Сим")
                        sp = _filter_spark({
                            "trigger_type": "gardening_together",
                            "priority": 75,
                            "premise": f"{g_name} ухаживает за растениями ({gard_detail}), а {o_name} находится рядом.",
                            "participants": [g_inf, o_inf],
                            "daily_key": d_key_gard,
                        })
                        if sp is not None:
                            return sp

    # =========================================================================
    # DETECTOR 6.2: Творчество у мольберта / Рисование
    # Один пишет картину на мольберте/планшете, второй рядом в комнате.
    # Приоритет: 74. 1 раз в день на художника.
    # =========================================================================
    if co_present and age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for painter_sim, other_sim, p_inf, o_inf, p_act, o_act in [
            (sim_a, sim_b, info_a, info_b, act_a, act_b),
            (sim_b, sim_a, info_b, info_a, act_b, act_a)
        ]:
            is_paint, paint_detail = is_sim_painting(painter_sim, p_inf, p_act)
            if is_paint:
                d_key_paint = f"painting_{p_inf.sim_id}_{int(get_current_sim_day())}"
                if can_trigger_fire_today(d_key_paint, "creative_painting", force=force):
                    p_name = getattr(p_inf, "first_name", "Сим")
                    o_name = getattr(o_inf, "first_name", "Сим")
                    if paint_detail in ("sketchpad", "эскиз на планшете", "рисует эскиз на цифровом планшете"):
                        premise = f"{p_name} рисует эскиз на цифровом планшете, а {o_name} просто находится рядом в комнате (не позирует и не является объектом рисунка)."
                    elif paint_detail and paint_detail not in ("на мольберте", "пишет картину на мольберте"):
                        premise = f"{p_name} пишет на мольберте картину ({paint_detail}), а {o_name} просто находится рядом в комнате (не позирует и не является объектом картины)."
                    else:
                        premise = f"{p_name} пишет на мольберте картину, а {o_name} просто находится рядом в комнате (не позирует и не является объектом картины)."
                    sp = _filter_spark({
                        "trigger_type": "creative_painting",
                        "priority": 74,
                        "premise": premise,
                        "participants": [p_inf, o_inf],
                        "daily_key": d_key_paint,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 6.3: Музицирование на инструменте (Пианино, гитара, скрипка)
    # Один играет на инструменте, второй находится рядом в комнате и слушает.
    # Приоритет: 75. 1 раз в день на музыканта.
    # =========================================================================
    if co_present and age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for music_sim, other_sim, m_inf, o_inf, m_act, o_act in [
            (sim_a, sim_b, info_a, info_b, act_a, act_b),
            (sim_b, sim_a, info_b, info_a, act_b, act_a)
        ]:
            is_music, inst_name = is_sim_playing_instrument(music_sim, m_inf, m_act)
            if is_music:
                d_key_mus = f"music_{m_inf.sim_id}_{int(get_current_sim_day())}"
                if can_trigger_fire_today(d_key_mus, "music_performance", force=force):
                    m_name = getattr(m_inf, "first_name", "Сим")
                    o_name = getattr(o_inf, "first_name", "Сим")
                    sp = _filter_spark({
                        "trigger_type": "music_performance",
                        "priority": 75,
                        "premise": f"{m_name} играет на музыкальном инструменте ({inst_name}), а {o_name} находится рядом в комнате.",
                        "participants": [m_inf, o_inf],
                        "daily_key": d_key_mus,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 6.4: Домашняя тренировка / Спорт (Беговая дорожка, пресс, йога)
    # Один активно упражняется/бегает, второй рядом в помещении.
    # Приоритет: 73. 1 раз в день на спортсмена.
    # =========================================================================
    if co_present and age_a in ("TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        for fit_sim, other_sim, f_inf, o_inf, f_act, o_act in [
            (sim_a, sim_b, info_a, info_b, act_a, act_b),
            (sim_b, sim_a, info_b, info_a, act_b, act_a)
        ]:
            is_fit, fit_detail = is_sim_working_out(fit_sim, f_inf, f_act)
            if is_fit:
                d_key_fit = f"fitness_{f_inf.sim_id}_{int(get_current_sim_day())}"
                if can_trigger_fire_today(d_key_fit, "fitness_workout", force=force):
                    f_name = getattr(f_inf, "first_name", "Сим")
                    o_name = getattr(o_inf, "first_name", "Сим")
                    sp = _filter_spark({
                        "trigger_type": "fitness_workout",
                        "priority": 73,
                        "premise": f"{f_name} тренируется ({fit_detail}), а {o_name} находится рядом.",
                        "participants": [f_inf, o_inf],
                        "daily_key": d_key_fit,
                    })
                    if sp is not None:
                        return sp

    # =========================================================================
    # DETECTOR 6.5: Настольные игры / Шахматы (Оба играют за одним столом)
    # Приоритет: 76. 1 раз в день на пару игроков.
    # =========================================================================
    if co_present and age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        is_table_g, game_type = are_sims_playing_table_game(sim_a, sim_b, act_a, act_b)
        if is_table_g:
            d_key_tbl = f"table_game_{pair_key[0]}_{pair_key[1]}_{int(get_current_sim_day())}"
            if can_trigger_fire_today(d_key_tbl, "table_games", force=force):
                sp = _filter_spark({
                    "trigger_type": "table_games",
                    "priority": 76,
                    "premise": f"{name_a} и {name_b} играют в {game_type} за одним столом.",
                    "participants": [info_a, info_b],
                    "daily_key": d_key_tbl,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 6.6: Забота о домашнем питомце (Купание, игра, дрессировка)
    # Один ухаживает за кошкой/собакой, второй наблюдает в комнате.
    # Приоритет: 74. 1 раз в день на ухаживающего.
    # =========================================================================
    if co_present and age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        pet_care_res = detect_pet_care_in_scene(sim_a, sim_b, act_a, act_b)
        if pet_care_res is not None:
            carer_inf, other_inf, pet_name, care_detail = pet_care_res
            d_key_pet = f"pet_care_{carer_inf.sim_id}_{int(get_current_sim_day())}"
            if can_trigger_fire_today(d_key_pet, "pet_care", force=force):
                c_name = getattr(carer_inf, "first_name", "Сим")
                o_name = getattr(other_inf, "first_name", "Сим")
                sp = _filter_spark({
                    "trigger_type": "pet_care",
                    "priority": 74,
                    "premise": f"{c_name} ухаживает за питомцем ({pet_name}, {care_detail}), а {o_name} находится рядом в комнате.",
                    "participants": [carer_inf, other_inf],
                    "daily_key": d_key_pet,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 7: Ночной / вечерний разговор перед сном (21:00 - 02:00)
    # Любые симы (пара, семья, соседи, друзья), бодрствующие перед сном.
    # 1 раз в день на пару.
    # =========================================================================
    if (hour >= 21 or hour <= 1) and age_a in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER"):
        d_key_bed = f"bedtime_talk_{pair_key[0]}_{pair_key[1]}"
        if can_trigger_fire_today(d_key_bed, "bedtime_pillow_talk", force=force):
            is_romantic = False
            is_parent_child = False
            try:
                from ai_thought_reader.context import get_relationship_status
                rel_str = (get_relationship_status(info_a, info_b) or "").lower()
                is_romantic = any(k in rel_str for k in ["муж", "жена", "супруг", "возлюблен", "парень", "девушка", "любов"])
                is_parent_child = any(k in rel_str for k in ["отец", "мать", "сын", "дочь", "родител", "ребенок"])
            except Exception:
                pass

            if is_romantic:
                premise = f"{name_a} и {name_b} проводят время вместе поздним вечером перед сном."
            elif is_parent_child:
                premise = f"{name_a} и {name_b} находятся в доме поздним вечером перед сном."
            else:
                premise = f"{name_a} и {name_b} бодрствуют в доме поздним вечером перед сном."

            sp = _filter_spark({
                "trigger_type": "bedtime_pillow_talk",
                "priority": 65,
                "premise": premise,
                "participants": [info_a, info_b],
                "daily_key": d_key_bed,
            })
            if sp is not None:
                return sp


    # =========================================================================
    # DETECTOR 8: Утреннее приветствие / Пробуждение (06:00 - 10:00, 1 раз в день)
    # Любые симы, встретившиеся утром в доме. Без привязки к кофе или душу!
    # =========================================================================
    if 6 <= hour <= 10:
        d_key_morn = f"morning_routine_{pair_key[0]}_{pair_key[1]}"
        if can_trigger_fire_today(d_key_morn, "morning_coffee", force=force):
            sp = _filter_spark({
                "trigger_type": "morning_coffee",
                "priority": 65,
                "premise": f"{name_a} и {name_b} только проснулись и встретились утром в доме.",
                "participants": [info_a, info_b],
                "daily_key": d_key_morn,
            })
            if sp is not None:
                return sp

    # =========================================================================
    # DETECTOR 9: Реакция на тяжёлое / отрицательное настроение (Negative Mood Reaction)
    # Злость, грусть, стресс, смущение, страх, дискомфорт, ошалелость, скука.
    # Суточный лимит: 1 раз в день НА ОДНОГО ПЕРСОНАЖА (отец может утешить сына,
    # а затем в тот же день отреагировать на злость дочери).
    # =========================================================================
    for em_info, other_info in [(info_a, info_b), (info_b, info_a)]:
        m_data = get_sim_negative_mood_data(em_info)
        if m_data is not None:
            # Daily limit is strictly per emotional sim (1 reaction per sim per day)
            d_key_mood = f"neg_mood_{em_info.sim_id}"
            if can_trigger_fire_today(d_key_mood, "negative_mood_reaction", force=force):
                e_name = getattr(em_info, "first_name", "Сим")
                o_name = getattr(other_info, "first_name", "Сим")
                m_desc = m_data["mood_desc"]

                premise = f"{e_name} находится в тяжёлом настроении ({m_desc}), а {o_name} находится рядом."

                sp = _filter_spark({
                    "trigger_type": "negative_mood_reaction",
                    "priority": 84,
                    "premise": premise,
                    "participants": [other_info, em_info],
                    "daily_key": d_key_mood,
                })
                if sp is not None:
                    return sp

    # =========================================================================
    # DETECTOR 10: Моды (WickedWhims случайная нагота / Basemental пиво)
    # =========================================================================
    # A) Accidental Nudity check (WickedWhims / Vanilla TS4)
    # Triggers strictly when one Sim is genuinely nude, and the other is clothed.
    # No age restriction: works for adults, teens, children, toddlers.
    is_nude_a = is_sim_genuinely_nude(info_a)
    is_nude_b = is_sim_genuinely_nude(info_b)

    if (is_nude_a and not is_nude_b) or (is_nude_b and not is_nude_a):
        d_key_nude = f"ww_nudity_{pair_key[0]}_{pair_key[1]}"
        if can_trigger_fire_today(d_key_nude, "ww_accidental_nudity", force=force):
            nude_info = info_a if is_nude_a else info_b
            clothed_info = info_b if is_nude_a else info_a
            nu_name = getattr(nude_info, "first_name", "Сим")
            cl_name = getattr(clothed_info, "first_name", "Сим")
            nu_age = getattr(getattr(nude_info, "age", None), "name", "ADULT")
            cl_age = getattr(getattr(clothed_info, "age", None), "name", "ADULT")

            if nu_age in ("BABY", "INFANT", "TODDLER", "CHILD"):
                premise = f"{nu_name} бегает по дому совершенно голым без одежды, а {cl_name} застает это."
            elif cl_age in ("BABY", "INFANT", "TODDLER", "CHILD"):
                premise = f"{nu_name} находится в комнате без одежды, когда туда неожиданно заходит ребенок {cl_name}."
            else:
                premise = f"{nu_name} находится без одежды в присутствии одетого {cl_name}."

            sp = _filter_spark({
                "trigger_type": "ww_accidental_nudity",
                "priority": 85,
                "premise": premise,
                "participants": [clothed_info, nude_info],
                "daily_key": d_key_nude,
            })
            if sp is not None:
                return sp


    # =========================================================================
    # DETECTOR 11: Фоновый контакт в одной комнате (Fallback)
    # =========================================================================
    if visiting_spark is not None:
        return visiting_spark
    if npc_home_spark is not None:
        return npc_home_spark

    if lot_state == DIRECTOR_STATE_VISITING_FRIENDS:
        return _base_filter_spark({
            "trigger_type": "guest_ambient_hangout",
            "priority": 30,
            "premise": f"{name_a} и {name_b} проводят время в гостях у друзей ({space_desc.lower()}), занимаясь повседневными делами.",
            "participants": [info_a, info_b],
        })
    elif lot_state == DIRECTOR_STATE_VISITING_RELATIVES:
        return _base_filter_spark({
            "trigger_type": "relative_ambient_visit",
            "priority": 30,
            "premise": f"Родственники {name_a} и {name_b} проводят время в гостях ({space_desc.lower()}), занимаясь повседневными делами.",
            "participants": [info_a, info_b],
        })
    elif lot_state == DIRECTOR_STATE_COMMUNITY:
        is_near = (dist is None or dist <= 8.5)
        v_info = get_current_venue_info()
        v_name = v_info.get("venue_name", "заведение")
        is_player_a = is_sim_active_guest(info_a)
        is_player_b = is_sim_active_guest(info_b)
        is_player_involved = is_player_a or is_player_b

        if is_player_involved:
            # Для игрока ОБЯЗАТЕЛЬНО: персонажи должны активно разговаривать в игре!
            if force or are_sims_actively_conversing(sim_a, sim_b, info_a, info_b):
                return _base_filter_spark({
                    "trigger_type": "community_player_social",
                    "priority": 80,
                    "premise": f"{name_a} и {name_b} общаются в заведении ({space_desc.lower()}, {v_name}). Живой диалог: обсуждение атмосферы места, отдыха, напитков/еды или событий вокруг.",
                    "participants": [info_a, info_b],
                })
        else:
            # Для NPC-NPC: строго не более 3.5м между ними и ни один не должен быть на ходу
            is_actively_talking = are_sims_actively_conversing(sim_a, sim_b, info_a, info_b)
            is_close = (dist is not None and dist <= 3.5)
            if not force and not is_actively_talking:
                if not is_close:
                    return None
                if is_sim_moving(sim_a) or is_sim_moving(sim_b):
                    return None

            if force or is_close or is_actively_talking:
                if not force:
                    try:
                        min_d = None
                        active_hh = services.active_household() if hasattr(services, "active_household") else None
                        if active_hh is not None:
                            for hh_inst in active_hh.instanced_sims_gen():
                                if hh_inst is not None:
                                    d = get_distance_between_sims(sim_a, hh_inst)
                                    if d is not None and (min_d is None or d < min_d):
                                        min_d = d
                        if min_d is not None and min_d > 8.5:
                            return None
                    except Exception:
                        pass

                return _base_filter_spark({
                    "trigger_type": "community_ambient_social",
                    "priority": 40,
                    "premise": f"Посетители {name_a} и {name_b} находятся рядом в заведении ({space_desc.lower()}, {v_name}). Разговор двух посетителей: впечатления от места, личные новости или сплетни.",
                    "participants": [info_a, info_b],
                })
        return None
    elif lot_state == DIRECTOR_STATE_HOME or force:
        if (not is_sim_active_guest(info_a)) and (not is_sim_active_guest(info_b)):
            return _base_filter_spark({
                "trigger_type": "two_guests_living_room",
                "priority": 76,
                "premise": f"Двое гостей {name_a} и {name_b} проводят время в доме хозяев ({space_desc.lower()}). Обсуждение обстановки дома, хозяев, общих новостей и планов.",
                "participants": [info_a, info_b],
            })
        return _base_filter_spark({
            "trigger_type": "ambient_living_room",
            "priority": 30,
            "premise": f"{name_a} и {name_b} проводят время в одной комнате ({space_desc}), занимаясь повседневными делами.",
            "participants": [info_a, info_b]
        })
    return None


# =========================================================================
# MONITORING & SCAN ENGINE
# =========================================================================

def update_work_return_tracker():
    """Polls active household Sims to detect moment they return from work/school."""
    if services is None:
        return
    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    if client is None:
        return
    hh = getattr(client, "household", None)
    if hh is None:
        return

    now = get_sim_now()
    if now is None:
        return

    for sim_info in hh.sim_info_gen():
        s_id = getattr(sim_info, "sim_id", None)
        if not s_id or getattr(sim_info, "is_pet", False):
            continue

        is_now_at_work = is_sim_currently_at_work(sim_info)
        was_at_work = _sim_previous_work_state.get(s_id, False)

        # Transition: was at work -> now returned home!
        if was_at_work and not is_now_at_work:
            _sim_work_return_tracker[s_id] = now
            log(f"[DIRECTOR] Detected work/school return for {getattr(sim_info, 'first_name', '')}! Window started.")

        _sim_previous_work_state[s_id] = is_now_at_work


def update_intimacy_tracker():
    """Polls active household Sims to detect active intimacy/woohoo and maintain the 8-Sim-minute walk-in window."""
    if services is None:
        return
    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    if client is None:
        return
    hh = getattr(client, "household", None)
    if hh is None:
        return

    now = get_sim_now()
    if now is None:
        return

    # Clean up expired entries in _sim_recent_intimacy_tracker (> 8 sim minutes)
    expired_ids = []
    for s_id, data in _sim_recent_intimacy_tracker.items():
        t_stamp = data.get("timestamp")
        if t_stamp is not None:
            mins = get_sim_minutes_between(t_stamp, now)
            if mins is None or mins > INTIMACY_WALK_IN_WINDOW_MINUTES:
                expired_ids.append(s_id)
    for exp_id in expired_ids:
        _sim_recent_intimacy_tracker.pop(exp_id, None)

    get_sim_active_sex_info = None
    try:
        from ai_thought_reader.context import get_sim_active_sex_info
    except Exception:
        pass

    for sim_info in hh.sim_info_gen():
        s_id = getattr(sim_info, "sim_id", None)
        if not s_id or getattr(sim_info, "is_pet", False):
            continue

        is_now_in_sex = False
        sex_data = None
        if get_sim_active_sex_info is not None:
            try:
                sex_data = get_sim_active_sex_info(sim_info)
                is_now_in_sex = bool(sex_data)
            except Exception:
                pass

        # Also check active vanilla woohoo affordance if not detected via WW
        if not is_now_in_sex:
            sim_inst = getattr(sim_info, "get_sim_instance", lambda: None)()
            if sim_inst and hasattr(sim_inst, "get_all_running_and_queued_interactions"):
                try:
                    for inter in sim_inst.get_all_running_and_queued_interactions():
                        aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                        if any(k in aff_name for k in ("woohoo", "mess_around", "tryforbaby", "ww_sex")):
                            target = getattr(inter, "target", None)
                            t_info = getattr(target, "sim_info", target) if target else None
                            t_id = getattr(t_info, "sim_id", 0)
                            actor_ids = [s_id]
                            if t_id and t_id != s_id:
                                actor_ids.append(t_id)
                            sex_data = {
                                "actor_sim_ids": actor_ids,
                                "total_participants": len(actor_ids),
                                "location_and_privacy": "В помещении",
                                "partners": getattr(t_info, "first_name", "") if t_info else ""
                            }
                            is_now_in_sex = True
                            break
                except Exception:
                    pass

        if is_now_in_sex and sex_data:
            _sim_last_sex_data[s_id] = sex_data
            actor_ids = sex_data.get("actor_sim_ids") or [s_id]
            total_parts = len(actor_ids)
            if total_parts <= 1:
                scene_scale = "одиночная приватность (уединение / личное пространство)"
            elif total_parts == 2:
                scene_scale = "парная интимная сцена (вуху / пара)"
            else:
                scene_scale = f"групповая интимная сцена ({total_parts} участников)"

            where_raw = sex_data.get("location_and_privacy") or ""
            where_phrase = where_raw.split("[")[0].strip().rstrip(",") or "в помещении"

            # Record in recent intimacy tracker with active flag
            for a_id in actor_ids:
                _sim_recent_intimacy_tracker[a_id] = {
                    "timestamp": now,
                    "actor_ids": list(actor_ids),
                    "total_participants": total_parts,
                    "location_and_privacy": where_phrase,
                    "scene_scale": scene_scale,
                    "is_active": True,
                }

                # If this intimacy is cheating against a committed partner, also register in romance tracker!
                try:
                    sim_mgr = getattr(services, "sim_info_manager", lambda: None)()
                    a_inf = sim_mgr.get(a_id) if sim_mgr else None
                    if a_inf:
                        committed_partners = find_all_committed_partners(a_inf)
                        if committed_partners:
                            cp_ids = {getattr(cp, "sim_id", 0) for cp in committed_partners}
                            for lover_id in actor_ids:
                                if lover_id != a_id and lover_id not in cp_ids:
                                    lover_inf = sim_mgr.get(lover_id)
                                    if lover_inf and any(not is_polyamorous_or_exempt_from_cheating(a_inf, cp, lover_inf) for cp in committed_partners):
                                        _sim_recent_romance_tracker[a_id] = {
                                            "timestamp": now,
                                            "target_info": lover_inf,
                                            "target_id": lover_id,
                                            "affordance_name": "intimacy"
                                        }
                                        break
                except Exception:
                    pass

        was_in_sex = _sim_previous_sex_state.get(s_id, False)
        # Transition: was in sex -> now finished!
        if was_in_sex and not is_now_in_sex:
            last_data = _sim_last_sex_data.pop(s_id, None) or {}
            actor_ids = list(last_data.get("actor_sim_ids") or [s_id])
            partner_ids = set(actor_ids)
            where_raw = last_data.get("location_and_privacy") or ""
            where_phrase = where_raw.split("[")[0].strip().rstrip(",") or "в помещении"
            _sim_post_woohoo_tracker[s_id] = (now, partner_ids, where_phrase)

            total_parts = len(actor_ids)
            if total_parts <= 1:
                scene_scale = "одиночная приватность (уединение / личное пространство)"
            elif total_parts == 2:
                scene_scale = "парная интимная сцена (вуху / пара)"
            else:
                scene_scale = f"групповая интимная сцена ({total_parts} участников)"

            # Keep in recent intimacy tracker with is_active=False for the 8-minute window!
            for a_id in actor_ids:
                _sim_recent_intimacy_tracker[a_id] = {
                    "timestamp": now,
                    "actor_ids": actor_ids,
                    "total_participants": total_parts,
                    "location_and_privacy": where_phrase,
                    "scene_scale": scene_scale,
                    "is_active": False,
                }

            log(f"[DIRECTOR] Detected intimacy finish for {getattr(sim_info, 'first_name', '')}! 8-minute walk-in window and post-woohoo window active.")

        _sim_previous_sex_state[s_id] = is_now_in_sex


def scan_household_for_best_scene(force: bool = False, allow_immediate_only: bool = False) -> Optional[Dict[str, Any]]:
    """
    Scans the active household, pairs up co-present available Sims,
    and returns the best scene candidate with the highest priority spark.
    """
    if services is None:
        return None

    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    if client is None:
        return None
    hh = getattr(client, "household", None)
    if hh is None:
        return None

    # Track returns and intimacy transitions
    update_work_return_tracker()
    update_intimacy_tracker()
    update_bills_paid_tracker()
    update_romance_tracker()

    # =========================================================================
    # EMERGENCY PRIORITY 0: ТРАГЕДИЯ НА УЧАСТКЕ — ПОСЛЕДНЕЕ ПРОЩАНИЕ С УМИРАЮЩИМ
    # =========================================================================
    dying_info, dying_inst = find_active_dying_sim_and_instance_on_lot()
    if dying_info is not None and dying_inst is not None:
        best_survivor_info, best_survivor_inst = find_best_survivor_for_dying_sim(dying_info, dying_inst)
        if best_survivor_info is not None and best_survivor_inst is not None:
            d_key_death = f"death_farewell_{getattr(dying_info, 'sim_id', 0)}_{int(get_current_sim_day())}"
            if can_trigger_fire_today(d_key_death, "witness_death", force=force):
                spark = create_dying_farewell_spark(dying_inst, best_survivor_inst, dying_info, best_survivor_info, d_key_death)
                if spark is not None:
                    return spark

    # Collect available instanced Sims from active household
    available_sims = []
    available_names = []
    for sim_info in hh.sim_info_gen():
        sim_inst = getattr(sim_info, "get_sim_instance", lambda: None)()
        if sim_inst is not None and is_sim_available(sim_inst):
            available_sims.append(sim_inst)
            available_names.append(getattr(sim_info, "first_name", "Сим"))

    # Also include any available Sim on active lot who is actively conversing with a household member (e.g. daughter, relative, guest)
    if services is not None and hasattr(services, "sim_info_manager"):
        try:
            sim_mgr = services.sim_info_manager()
            if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                for inst in sim_mgr.instanced_sims_gen():
                    if inst not in available_sims and is_sim_available(inst):
                        for hh_sim in list(available_sims):
                            is_talking = False
                            if hasattr(hh_sim, "get_main_social_group"):
                                sg = hh_sim.get_main_social_group()
                                if sg and hasattr(sg, "members") and inst in set(sg.members):
                                    is_talking = True
                            if not is_talking and hasattr(hh_sim, "get_all_running_and_queued_interactions"):
                                for inter in hh_sim.get_all_running_and_queued_interactions():
                                    t = getattr(inter, "target", None)
                                    if t is inst or t is getattr(inst, "sim_info", None):
                                        is_talking = True
                                        break
                            if is_talking:
                                available_sims.append(inst)
                                available_names.append(getattr(getattr(inst, "sim_info", None), "first_name", "Сим"))
                                break
        except Exception:
            pass

    # When on home lot: also include visiting guests, service NPCs, or neighbors on active lot
    lot_state = get_director_lot_state()
    if lot_state == DIRECTOR_STATE_HOME:
        if services is not None and hasattr(services, "sim_info_manager"):
            try:
                sim_mgr = services.sim_info_manager()
                if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                    for inst in sim_mgr.instanced_sims_gen():
                        if inst not in available_sims and is_sim_available(inst):
                            s_info = getattr(inst, "sim_info", None)
                            if s_info and not getattr(s_info, "is_pet", False):
                                available_sims.append(inst)
                                available_names.append(f"{getattr(s_info, 'first_name', 'Гость')} (Гость/NPC)")
            except Exception:
                pass
    elif lot_state in (DIRECTOR_STATE_VISITING_FRIENDS, DIRECTOR_STATE_VISITING_RELATIVES):
        try:
            active_lot = services.active_lot() if services else None
            owner_hh_id = getattr(active_lot, "owner_household_id", None) if active_lot else None
            if owner_hh_id and hasattr(services, "household_manager"):
                hh_mgr = services.household_manager()
                host_hh = hh_mgr.get(owner_hh_id) if hh_mgr else None
                if host_hh:
                    for h_info in host_hh.sim_info_gen():
                        h_inst = getattr(h_info, "get_sim_instance", lambda: None)()
                        if h_inst is not None and h_inst not in available_sims and is_sim_available(h_inst):
                            available_sims.append(h_inst)
                            available_names.append(f"{getattr(h_info, 'first_name', 'Хозяин')} (Хозяин дома)")
        except Exception:
            pass
    elif lot_state == DIRECTOR_STATE_COMMUNITY:
        try:
            if services is not None and hasattr(services, "sim_info_manager"):
                sim_mgr = services.sim_info_manager()
                if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                    active_inst_list = [s for s in available_sims if s is not None]
                    for inst in sim_mgr.instanced_sims_gen():
                        if inst not in available_sims and is_sim_available(inst):
                            s_info = getattr(inst, "sim_info", None)
                            if s_info and not getattr(s_info, "is_pet", False):
                                include_sim = False
                                from ai_thought_reader.context import get_sim_active_lot_role
                                role_info = get_sim_active_lot_role(s_info, inst)
                                role_str = role_info.get("ru", str(role_info)) if isinstance(role_info, dict) else str(role_info or "")
                                if role_str:
                                    include_sim = True
                                else:
                                    for ah_inst in active_inst_list:
                                        d = get_distance_between_sims(ah_inst, inst)
                                        if d is not None and d <= 8.5:
                                            include_sim = True
                                            break
                                if include_sim:
                                    available_sims.append(inst)
                                    s_first = getattr(s_info, "first_name", "Сим")
                                    role_label = f" ({role_str})" if role_str else " (Посетитель)"
                                    available_names.append(f"{s_first}{role_label}")
        except Exception as e:
            log_exception("Error collecting community lot sims", e)

    # Variant B for witness_death: if exactly 1 living Sim remains available on the lot,
    # and the Grim Reaper is present, include Death so the lone survivor can plead for mercy.
    reaper_inst = get_grim_reaper_instance_on_lot()
    if reaper_inst is not None and reaper_inst not in available_sims:
        is_talking_to_reaper = False
        for s in available_sims:
            if hasattr(s, "get_main_social_group"):
                sg = s.get_main_social_group()
                if sg and hasattr(sg, "members") and reaper_inst in set(sg.members):
                    is_talking_to_reaper = True
                    break
        if len(available_sims) == 1 or is_talking_to_reaper:
            available_sims.append(reaper_inst)
            available_names.append("Костлявая Смерть")

    if len(available_sims) < 2:
        log(f"[DIRECTOR SCAN] Less than 2 available Sims on lot (found {len(available_sims)}: {', '.join(available_names) or 'none'}).")
        if force:
            send_director_telemetry(
                "SCAN",
                "Сканирование семьи: недостаточно свободных симов",
                [f"Доступно симов: {len(available_sims)} ({', '.join(available_names) if available_names else 'нет'})", "Для диалога требуется минимум 2 бодрствующих сима на участке."],
                level="WARNING"
            )
        return None

    # Prioritize active player sim at the front of available_sims
    try:
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        active_sim = getattr(client, "active_sim", None) if client else None
        if active_sim is not None and active_sim in available_sims:
            available_sims.remove(active_sim)
            available_sims.insert(0, active_sim)
    except Exception:
        pass

    candidates = []
    pair_count = 0
    all_eval_pairs = []
    for i in range(len(available_sims)):
        for j in range(i + 1, len(available_sims)):
            s_a = available_sims[i]
            s_b = available_sims[j]
            d = get_distance_between_sims(s_a, s_b)
            all_eval_pairs.append((s_a, s_b, d if d is not None else 999.0))

    # Prioritize pairs that are physically closest together
    all_eval_pairs.sort(key=lambda item: item[2])

    for sim_a, sim_b, _dist_m in all_eval_pairs:
        pair_count += 1
        spark = evaluate_scene_spark(sim_a, sim_b, force=force, allow_immediate_only=allow_immediate_only)
        if spark is not None:
            candidates.append(spark)

    if not candidates:
        if force:
            lot_state = get_director_lot_state()
            state_desc = {
                DIRECTOR_STATE_HOME: "У себя дома (HOME)",
                DIRECTOR_STATE_VISITING_RELATIVES: "В гостях у родственников (VISITING_RELATIVES)",
                DIRECTOR_STATE_VISITING_FRIENDS: "В гостях у друзей/знакомых (VISITING_FRIENDS)",
                DIRECTOR_STATE_COMMUNITY: "Общественный участок (COMMUNITY)",
                DIRECTOR_STATE_OTHER: "Другой участок (OTHER)",
            }.get(lot_state, lot_state)
            details = [
                f"Режим Режиссёра: {state_desc}",
                f"Проверено пар симов: {pair_count}",
                f"Доступные симы: {', '.join(available_names)}",
            ]
            if lot_state != DIRECTOR_STATE_HOME:
                details.append("Проверены гостевые, универсальные экстренные, драматические и досуговые триггеры.")
            else:
                details.append("Симы не в одной комнате или текущие действия не соответствуют триггерам.")
            send_director_telemetry(
                "SCAN",
                "Сканирование завершено: подходящих поводов не найдено",
                details,
                level="INFO"
            )
        return None

    # Sort by priority score (highest first).
    # If multiple candidates share the exact same top priority score (e.g. ambient in Room 1 vs Room 2),
    # pick fairly and randomly among the top-tied candidates so the same room doesn't always win.
    candidates.sort(key=lambda s: s.get("priority", 0), reverse=True)
    top_priority = candidates[0].get("priority", 0)
    top_candidates = [c for c in candidates if c.get("priority", 0) == top_priority]
    if len(top_candidates) > 1:
        best = random.choice(top_candidates)
    else:
        best = candidates[0]

    parts = best.get("participants", [])
    info_a = getattr(parts[0], "sim_info", parts[0]) if len(parts) > 0 else None
    info_b = getattr(parts[1], "sim_info", parts[1]) if len(parts) > 1 else None
    name_a = getattr(info_a, "first_name", "Сим 1") if info_a else "Сим 1"
    name_b = getattr(info_b, "first_name", "Сим 2") if info_b else "Сим 2"

    if len(parts) >= 2:
        nearby_sims = find_nearby_joinable_sims(parts[0], parts[1], max_count=6)
        best["nearby_sims"] = nearby_sims
        best["all_scene_sims"] = [info_a, info_b] + nearby_sims
    else:
        best["nearby_sims"] = []
        best["all_scene_sims"] = [info_a, info_b] if info_a and info_b else []

    nearby_names = [getattr(s, "first_name", "Сим") for s in best.get("nearby_sims", [])]
    nearby_detail = f"Рядом в пространстве: {', '.join(nearby_names)}" if nearby_names else "Рядом других симов нет"

    send_director_telemetry(
        "DECISION",
        f"[SCENE] ВЫБРАН ПОВОД: [{best.get('trigger_type')}] (Приоритет: {best.get('priority')})",
        [
            f"Инициаторы: {name_a} и {name_b}",
            nearby_detail,
            f"Повод: {best.get('premise')}",
            f"Всего кандидатов обнаружено: {len(candidates)}"
        ],
        level="SUCCESS"
    )
    return best


def record_scene_completed(sim_a: Any, sim_b: Any, trigger_type: str = "ambient", spark: Optional[Dict[str, Any]] = None):
    """
    Updates cooldown timestamps after an autonomous scene successfully executes.
    All scenes (including immediate triggers) reset the household silence cooldown
    (_last_ambient_scene_real_time) and pair cooldowns in unpaused real seconds.
    """
    global _last_scene_sim_time, _last_ambient_scene_sim_time
    global _last_scene_real_time, _last_ambient_scene_real_time
    now = get_sim_now()
    now_rt = get_unpaused_real_time()
    _last_scene_sim_time = now
    _last_scene_real_time = now_rt

    if trigger_type:
        _trigger_last_scene_sim_time[trigger_type] = now
        _trigger_last_scene_real_time[trigger_type] = now_rt

    # Reset household silence cooldown unconditionally (both ambient and immediate triggers)
    _last_ambient_scene_sim_time = now
    _last_ambient_scene_real_time = now_rt

    # Collect all participants in the scene
    participants = []
    if spark:
        raw_parts = spark.get("all_scene_sims") or spark.get("participants", [])
        for p in raw_parts:
            inf = getattr(p, "sim_info", p)
            if inf is not None and inf not in participants:
                participants.append(inf)
    if not participants:
        for s in (sim_a, sim_b):
            inf = getattr(s, "sim_info", s)
            if inf is not None and inf not in participants:
                participants.append(inf)

    # Set pair cooldowns for all participating pairs
    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            inf_i = participants[i]
            inf_j = participants[j]
            s_id_i = getattr(inf_i, "sim_id", 0)
            s_id_j = getattr(inf_j, "sim_id", 0)
            if s_id_i and s_id_j:
                pair_k = (min(s_id_i, s_id_j), max(s_id_i, s_id_j))
                _pair_last_scene_sim_time[pair_k] = now
                _pair_last_scene_real_time[pair_k] = now_rt

    names = [f"{getattr(p, 'first_name', '')}".strip() for p in participants if getattr(p, 'first_name', None)]
    names_str = " & ".join(names) if names else "Участники"

    global _last_completed_scene_info
    _last_completed_scene_info = {
        "trigger_type": trigger_type,
        "participants": [f"{getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}".strip() for p in participants if getattr(p, 'first_name', None)],
        "participant_ids": [getattr(p, "sim_id", 0) for p in participants if getattr(p, "sim_id", 0)],
        "real_time": now_rt,
        "sim_time": now,
    }

    try:
        from ai_thought_reader.config import is_director_trigger_immediate
        is_imm = is_director_trigger_immediate(trigger_type)
    except Exception:
        is_imm = (trigger_type in IMMEDIATE_TRIGGERS)
    if trigger_type in TRIGGER_COOLDOWNS_REAL_SECONDS:
        trig_cd_info = f"Кулдаун повода [{trigger_type}]: {int(TRIGGER_COOLDOWNS_REAL_SECONDS[trigger_type])}с ({TRIGGER_COOLDOWNS_REAL_SECONDS[trigger_type] / 60.0:.1f} мин) реал. времени"
    else:
        trig_cd_info = f"Кулдаун повода [{trigger_type}]: {int(TRIGGER_DEBOUNCE_COOLDOWN_MINUTES)} сим-мин"

    send_director_telemetry(
        "COOLDOWN",
        f"[OK] Сцена завершена [{trigger_type}] для: {names_str}",
        [
            f"Тип: {'[!] Мгновенный' if is_imm else '[COOLDOWN] Фоновый'} (пауза тишины сброшена: {int(HOUSEHOLD_SILENCE_COOLDOWN_REAL_SECONDS)}с реал. времени)",
            f"Кулдаун участников: {int(PAIR_COOLDOWN_REAL_SECONDS)}с ({PAIR_COOLDOWN_REAL_SECONDS / 60.0:.1f} мин)",
            trig_cd_info
        ],
        level="INFO"
    )


def build_autonomous_prompt(spark: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Builds the exact contextual prompt and payload according to user contract:
    [ТЕКСТ РЕЖИССЁРА / СЦЕНА]:
    Повод для разговора: <premise>

    [ПЕРСОНАЖИ В СЦЕНЕ]:
    1. <Name>
    2. <Name>

    --------------------------------------------------------------------------------

    [КОНТЕКСТ: ЖИВОЕ ОБЩЕНИЕ (АВТОНОМИЯ)]
    <Full Direct Dialogue rich profile: actions, furniture, room, clothing/nudity, career/homework, weather, relationship>
    """
    parts = spark.get("participants", [])
    if len(parts) < 2:
        return "", {}

    info_a = getattr(parts[0], "sim_info", parts[0])
    info_b = getattr(parts[1], "sim_info", parts[1])

    name_a = f"{getattr(info_a, 'first_name', '')} {getattr(info_a, 'last_name', '')}".strip() or "Сим"
    name_b = f"{getattr(info_b, 'first_name', '')} {getattr(info_b, 'last_name', '')}".strip() or "Сим"

    premise = spark.get("premise", "")
    trigger_type = spark.get("trigger_type", "ambient")

    try:
        from ai_thought_reader.config import get_director_trigger_custom_prompt
        custom_premise = get_director_trigger_custom_prompt(trigger_type)
        if custom_premise:
            premise = (
                custom_premise
                .replace("{name_a}", name_a)
                .replace("{name_b}", name_b)
                .replace("{actor}", name_a)
                .replace("{target}", name_b)
            )
    except Exception:
        pass

    from ai_social_pc.chat_manager import _build_sim_profile_summary
    from ai_social_pc.ui_chat import _get_relationship_description

    profile_a = _build_sim_profile_summary(info_a, is_direct_dialogue=True, other_sim_info=info_b)
    profile_b = _build_sim_profile_summary(info_b, is_direct_dialogue=True, other_sim_info=info_a)
    rel_desc = _get_relationship_description(info_a, info_b)

    emergency_banner = ""
    if trigger_type == "sim_in_labor":
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — СХВАТКИ И РОДЫ]:\n"
            "Прямо сейчас происходят активные схватки и роды! Младенец рождается сию секунду прямо здесь.\n"
            "Запрещено переходить на отвлеченные, будничные темы.\n"
            "ВАЖНО ДЛЯ РЕЖИССУРЫ: Сценарий полностью универсален и не привязан к конкретному месту или шаблонным ожиданиям. "
            "Слова, физические ощущения, эмоциональные реакции и действия персонажей должны строго определяться их индивидуальными чертами характера, отношениями, текущей локацией и обстоятельствами (от сочувствия, волнения и попыток принять роды на месте до ледяного безразличия, насмешек, ужаса, растерянности или эгоизма).\n\n"
        )
    elif trigger_type == "caught_cheating":
        emergency_banner = (
            f"[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — ЗАСТИГНУТАЯ ИЗМЕНА]:\n"
            f"РОЛИ:\n"
            f"1. {name_a} — ОБМАНУТЫЙ ПОСТОЯННЫЙ ПАРТНЁР / СУПРУГ (ЖЕРТВА ИЗМЕНЫ). {name_a} начинает разговор!\n"
            f"2. {name_b} — ИЗМЕНИВШИЙ ПАРТНЁР (ПОЙМАН С ПОЛИЧНЫМ).\n\n"
        )
    elif trigger_type == "electrocuted_repair":
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — УДАР ТОКОМ ПРИ РЕМОНТЕ]:\n"
            "Персонаж только что получил сильный электрический удар при починке техники, опален и находится в ошалевшем состоянии! "
            "ВАЖНО ДЛЯ РЕЖИССУРЫ: Избегай шаблонного сочувствия. Реакции зависят от личностей: пострадавший может упрямо делать вид, что всё под контролем, жаловаться или пребывать в ступоре; "
            "свидетель может встревожиться, разозлиться на испорченный прибор или язвительно насмехаться над чужой неудачей, если характер вредный или злой.\n\n"
        )
    elif trigger_type == "paid_bills":
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — ОПЛАТА СЧЕТОВ И СЕМЕЙНЫЙ БЮДЖЕТ]:\n"
            "Только что были оплачены счета за жильё, затронут вопрос финансов. "
            "ВАЖНО ДЛЯ РЕЖИССУРЫ: Диалог должен отражать финансовое положение семьи (бедность, долги или беззаботное богатство) и черты характера симов: "
            "тревога за каждую копейку, прижимистость, высокомерие, упрёки в расточительности или безразличие к тратам.\n\n"
        )
    elif trigger_type == "fire_hazard":
        emergency_banner = (
            "[КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ — ПОЖАР НА УЧАСТКЕ]:\n"
            "На участке бушует пожар! Персонажи должны реагировать соответственно: паника, крики, бегство или попытки тушения, а не повседневные разговоры.\n\n"
        )
    elif trigger_type == "witness_death":
        emergency_banner = (
            "[КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ — ТРАГЕДИЯ / СМЕРТЬ]:\n"
            "Происходит гибель персонажа! Диалог должен быть драматичным, эмоциональным, полным горя, страха или прощания.\n\n"
        )
    elif trigger_type == "community_bar_order_chat":
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — У БАРНОЙ СТОЙКИ]:\n"
            "Если персонажи уже находятся у стойки с напитками в руках (или общаются как посетители) — "
            "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО обсуждать выбор или заказ напитков по меню! Заказ УЖЕ выполнен, напитки получены. "
            "Персонажи выпивают, отдыхают, поднимают тост, делятся новостями или впечатлениями от заведения.\n\n"
        )
    elif trigger_type == "community_ambient_social":
        active_hh = services.active_household() if (services is not None and hasattr(services, "active_household")) else None
        hh_first_names = []
        forbidden_names = []
        if active_hh is not None:
            for s_inf in active_hh.sim_info_gen():
                fn = getattr(s_inf, "first_name", "")
                s_id = getattr(s_inf, "sim_id", 0)
                if not fn:
                    continue
                hh_first_names.append(fn)
                knows = False
                for inf in (info_a, info_b):
                    if inf is not None:
                        rt = getattr(inf, "relationship_tracker", None)
                        if rt is not None:
                            try:
                                if hasattr(rt, "has_relationship") and rt.has_relationship(s_id):
                                    knows = True
                                elif hasattr(rt, "get_relationship") and rt.get_relationship(s_id) is not None:
                                    knows = True
                            except Exception:
                                pass
                if not knows:
                    forbidden_names.append(fn)

        names_to_forbid = forbidden_names if forbidden_names else hh_first_names
        hh_names_str = ", ".join(names_to_forbid) if names_to_forbid else "игрока"
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — ФОНОВЫЙ РАЗГОВОР NPC В ЗАВЕДЕНИИ]:\n"
            f"1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО называть или упоминать имена персонажей семьи игрока ({hh_names_str})! "
            "Говорящие NPC не знакомы с ними лично и не знают их имён. Это посторонние для них люди.\n"
            "2. Это приватный разговор двух посетителей заведения между собой. Они обсуждают свои личные дела, напитки, новости или сплетни городка.\n\n"
        )
    elif trigger_type == "community_player_social":
        emergency_banner = (
            "[ОСОБЫЕ УКАЗАНИЯ К СЦЕНЕ — ОБЩЕНИЕ В ЗАВЕДЕНИИ]:\n"
            "Живой разговор в заведении с участием персонажа игрока. Обсуждение атмосферы места, отдыха, музыки, напитков/еды или легкая непринужденная беседа.\n\n"
        )

    nearby_sims = spark.get("nearby_sims")
    if nearby_sims is None and len(parts) >= 2:
        nearby_sims = find_nearby_joinable_sims(parts[0], parts[1], max_count=6)
    if nearby_sims is None:
        nearby_sims = []
    nearby_sims = nearby_sims[:6]

    all_scene_sims = [info_a, info_b] + nearby_sims
    spark["all_scene_sims"] = all_scene_sims

    nearby_lines = []
    nearby_profiles_text = []
    all_participants_payload = [
        {"sim_id": getattr(info_a, "sim_id", 0), "name": name_a},
        {"sim_id": getattr(info_b, "sim_id", 0), "name": name_b},
    ]

    for idx, nb_info in enumerate(nearby_sims, 3):
        nb_name = f"{getattr(nb_info, 'first_name', '')} {getattr(nb_info, 'last_name', '')}".strip() or f"Сим {idx}"
        nb_prof = _build_sim_profile_summary(nb_info, is_direct_dialogue=True, other_sim_info=info_a)
        nearby_lines.append(f"{idx}. {nb_name} (находится рядом в том же пространстве)")
        nearby_profiles_text.append(f"ПРОФИЛЬ: {nb_name} (РЯДОМ В ТОМ ЖЕ ПРОСТРАНСТВЕ)\n{nb_prof}")
        all_participants_payload.append({
            "sim_id": getattr(nb_info, "sim_id", 0),
            "name": nb_name
        })

    nearby_block = ""
    if nearby_lines:
        nearby_list_str = "\n".join(nearby_lines)
        nearby_names_str = ", ".join([getattr(nb, "first_name", "") or "Сим" for nb in nearby_sims])
        nearby_block = (
            f"[ПЕРСОНАЖИ РЯДОМ В ТОМ ЖЕ ПРОСТРАНСТВЕ (МОГУТ ПРИСОЕДИНИТЬСЯ К РАЗГОВОРУ ИЛИ ПРОМОЛЧАТЬ)]:\n"
            f"{nearby_list_str}\n\n"
            f"[ПРАВИЛА УЧАСТИЯ ПЕРСОНАЖЕЙ И ДЛИНЫ ДИАЛОГА]:\n"
            f"- ПРИСУТСТВИЕ НЕ ОБЯЗЫВАЕТ ГОВОРИТЬ: Персонажи рядом ({nearby_names_str}) НЕ обязаны принудительно влезать в разговор! Сим может молча продолжать заниматься своими делами, слушать или игнорировать происходящее. Подключай их реплики ТОЛЬКО по желанию нейросети и если это органично моменту.\n"
            f"- КОЛИЧЕСТВО РЕПЛИК: Базовая длина живого диалога для двоих участников — 1-4 реплики (не затягивай сцену искусственно).\n"
            f"- ПРАВИЛО +1 РЕПЛИКА: За каждого РЕАЛЬНО вступившего в диалог дополнительного персонажа из тех, кто рядом, максимальное рекомендуемое количество реплик увеличивается ровно на +1 (например: говорят двое — 1-4 реплики; подключился третий — до 5 реплик; подключился четвёртый — до 6 реплик).\n\n"
        )

    profiles_all = [
        f"ПРОФИЛЬ: {name_a}\n{profile_a}",
        f"ПРОФИЛЬ: {name_b}\n{profile_b}"
    ] + nearby_profiles_text

    # Collect environment information (World Time, Season, Weather, Holiday)
    env_lines = []
    is_en = False
    try:
        from ai_thought_reader.context import (
            get_world_time_info,
            get_season_info,
            get_weather_info,
            get_holiday_info,
        )
        from ai_social_pc.localization import get_game_language
        is_en = (get_game_language() == "en")

        w_time = get_world_time_info()
        season = get_season_info()
        weather = get_weather_info()
        holiday = get_holiday_info(info_a)
        cur_world = ""
        try:
            from ai_thought_reader.context import get_current_world_name
            cur_world = get_current_world_name() or ""
        except Exception:
            cur_world = ""

        if is_en:
            from ai_thought_reader.context_en import (
                translate_time_en,
                SEASONS_MAP_EN,
                WEATHER_MAP_EN,
                translate_phrase,
                translate_holiday_en,
                WORLD_NAMES_MAP_EN,
            )
            w_time_en = translate_time_en(w_time)
            season_en = SEASONS_MAP_EN.get(season, season)
            weather_en = translate_phrase(weather, WEATHER_MAP_EN)
            holiday_en = translate_holiday_en(holiday) if holiday else ""
            if cur_world:
                cur_world = WORLD_NAMES_MAP_EN.get(cur_world, cur_world)

            from ai_thought_reader.config import get_context_flag
            if get_context_flag("location") and cur_world:
                env_lines.append(f"- World / Location: {cur_world}")
            if get_context_flag("world_time") and w_time_en:
                env_lines.append(f"- In-Game Time: {w_time_en}")
            if get_context_flag("weather"):
                if season_en:
                    env_lines.append(f"- Season: {season_en}")
                if weather_en:
                    env_lines.append(f"- Weather: {weather_en}")
            if get_context_flag("events") and holiday_en:
                env_lines.append(f"- Holiday: {holiday_en}")
        else:
            from ai_thought_reader.config import get_context_flag
            if get_context_flag("location") and cur_world:
                env_lines.append(f"- Мир / Локация: {cur_world}")
            if get_context_flag("world_time") and w_time:
                env_lines.append(f"- Время в игре: {w_time}")
            if get_context_flag("weather"):
                if season:
                    env_lines.append(f"- Время года: {season}")
                if weather:
                    env_lines.append(f"- Погода: {weather}")
            if get_context_flag("events") and holiday:
                env_lines.append(f"- Праздник: {holiday}")
    except Exception as ex_env:
        log_exception("Error collecting environment info for autonomous prompt", ex_env)

    env_block = ""
    if env_lines:
        header = "[ОКРУЖЕНИЕ И ВРЕМЯ]:" if not is_en else "[ENVIRONMENT & TIME]:"
        env_block = f"{header}\n" + "\n".join(env_lines) + "\n\n"

    # Home / Small Business Context (Experimental Flag)
    biz_block = ""
    try:
        from ai_thought_reader.business_context import get_business_prompt_block
        biz_block = get_business_prompt_block(info_a, is_en=is_en)
    except Exception as ex_biz:
        log_exception("Error collecting business info for autonomous prompt", ex_biz)

    # Past Events & Memories between participants
    mem_block = ""
    m_raw = ""
    if get_context_flag("memory"):
        try:
            from ai_social_pc.memory_manager import format_memories_for_prompt
            id_a = getattr(info_a, "sim_id", 0)
            id_b = getattr(info_b, "sim_id", 0)
            if id_a and id_b:
                m_raw = format_memories_for_prompt(id_a, id_b) or ""
                if m_raw:
                    m_hdr = "[ПАМЯТЬ И ПРОШЛЫЕ СОБЫТИЯ МЕЖДУ УЧАСТНИКАМИ]:" if not is_en else "[PAST EVENTS & MEMORIES BETWEEN PARTICIPANTS]:"
                    mem_block = f"{m_hdr}\n{m_raw}\n\n"
        except Exception as ex_mem:
            log_exception("Error collecting memories for autonomous prompt", ex_mem)

    party_guidance_block = ""
    if get_context_flag("events"):
        try:
            from ai_thought_reader.context import get_active_social_event_info, get_party_event_guidance
            ev_a = get_active_social_event_info(info_a)
            ev_b = get_active_social_event_info(info_b)
            chosen_ev = None
            if ev_a and isinstance(ev_a, dict) and ev_a.get("is_participant"):
                chosen_ev = ev_a
            elif ev_b and isinstance(ev_b, dict) and ev_b.get("is_participant"):
                chosen_ev = ev_b
            else:
                chosen_ev = ev_a or ev_b

            if chosen_ev:
                p_guidance = get_party_event_guidance(chosen_ev, is_en=is_en, for_director=True)
                if p_guidance:
                    party_guidance_block = f"\n{p_guidance}\n"
        except Exception as ex_party:
            log_exception("Error collecting party guidance for autonomous director prompt", ex_party)

    if not get_context_flag("emergencies"):
        emergency_banner = ""

    if not get_context_flag("nearby"):
        nearby_block = ""


    prompt = (
        f"[ТЕКСТ РЕЖИССЁРА / СЦЕНА]:\n"
        f"Повод для разговора: {premise}\n"
        f"Важно: Повод описывает лишь внешнее событие/ситуацию. Тон, эмоции, радушие или враждебность персонажей должны СТРОГО опираться на их шкалы отношений, черты характера, чувства и память (если персонажа ненавидят, презирают, обижены или боятся — никакой шаблонной вежливости или беспричинной радости!).\n"
        f"Важно: Не выдумывай названия комнат (кухня, гараж и т.д.), если они прямо не указаны в контексте.\n\n"
        f"{emergency_banner}"
        f"[ПЕРСОНАЖИ В СЦЕНЕ (ГЛАВНЫЕ ИНИЦИАТОРЫ)]:\n"
        f"1. {name_a}\n"
        f"2. {name_b}\n\n"
        f"{nearby_block}"
        f"--------------------------------------------------------------------------------\n\n"
        f"[КОНТЕКСТ: ЖИВОЕ ОБЩЕНИЕ (АВТОНОМИЯ)]\n"
        f"{env_block}"
        f"{biz_block}"
        f"Взаимоотношения между персонажами:\n{rel_desc}\n\n"
        f"{mem_block}"
        + "\n\n".join(profiles_all) + "\n"
        + party_guidance_block
    )

    payload = {
        "type": "autonomous_dialogue",
        "prompt": prompt,
        "premise": premise,
        "trigger_type": trigger_type,
        "participants": all_participants_payload
    }
    if m_raw:
        payload["memories"] = m_raw
    return prompt, payload


def parse_dialogue_fallback(raw_text: str, spark: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fallback parser for dialogue lines if Bridge returned raw string or embedded JSON.
    Handles thinking tags, code blocks, and line-by-line 'Speaker: text' format.
    """
    if not raw_text:
        return []
    clean = str(raw_text).strip()
    if "</think>" in clean:
        clean = clean.split("</think>")[-1].strip()
    if "</thought>" in clean:
        clean = clean.split("</thought>")[-1].strip()

    # 1. Try json block
    try:
        match_json = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean, re.DOTALL)
        cand = match_json.group(1) if match_json else clean
        data = json.loads(cand)
        if isinstance(data, dict) and "dialogue" in data and isinstance(data["dialogue"], list):
            return data["dialogue"]
    except Exception:
        pass

    # 2. Try raw json match
    match_fallback = re.search(r'\{\s*"dialogue"\s*:\s*\[.*?\]\s*\}', clean, re.DOTALL)
    if match_fallback:
        try:
            data = json.loads(match_fallback.group(0))
            if isinstance(data, dict) and "dialogue" in data and isinstance(data["dialogue"], list):
                return data["dialogue"]
        except Exception:
            pass

    # 3. Line by line Speaker: Text
    lines = [ln.strip() for ln in clean.split("\n") if ln.strip()]
    extracted = []
    for ln in lines:
        if ":" in ln:
            parts = ln.split(":", 1)
            spk = parts[0].strip().strip('*-•"«»[]')
            txt = parts[1].strip().strip('"«»')
            if spk and txt and not spk.lower().startswith("повод") and not spk.lower().startswith("сцена"):
                extracted.append({"speaker": spk, "text": txt})
    return extracted


def dispatch_autonomous_scene(spark: Optional[Dict[str, Any]] = None, on_finish_callback=None, force: bool = False) -> bool:
    """
    Dispatches the autonomous scene generation request to the AI Bridge in a background thread.
    Prevents parallel scene overlapping with single-flight lock (_is_scene_in_flight).
    If a scene is already in flight, rejects the request immediately (no delayed queueing).
    """
    global _is_scene_in_flight, _current_scene_trigger_type
    if _is_scene_in_flight:
        log("[DIRECTOR DISPATCH BLOCKED] Another scene is currently in flight. Skipping new scene dispatch.")
        return False

    if spark is None:
        return False
    prompt, payload = build_autonomous_prompt(spark)

    if not prompt or not payload:
        return False

    # Check if trigger is enabled in settings (unless forced via developer command)
    trig_type = spark.get("trigger_type", "")
    if not force:
        try:
            from ai_thought_reader.config import get_director_enabled, is_director_trigger_enabled
            if not get_director_enabled():
                log("[DIRECTOR DISPATCH BLOCKED] Director is globally disabled in settings.")
                return False
            lot_state_cur = get_director_lot_state()
            if trig_type and not is_director_trigger_enabled(lot_state_cur, trig_type, default=True):
                log(f"[DIRECTOR DISPATCH BLOCKED] Trigger '{trig_type}' is disabled in settings for lot state '{lot_state_cur}'. Skipping.")
                return False
        except Exception as ex_cfg:
            log(f"[DIRECTOR DISPATCH] Warning checking config: {ex_cfg}")

    _is_scene_in_flight = True
    _current_scene_trigger_type = trig_type

    # Mark daily trigger as fired now that scene is officially dispatched
    daily_key = spark.get("daily_key")
    if daily_key:
        mark_daily_trigger_fired(daily_key, trigger_type=trig_type)

    ret_id = spark.get("consume_work_tracker_sim_id")
    if ret_id:
        _sim_work_return_tracker.pop(ret_id, None)

    p_id = spark.get("consume_woohoo_tracker_sim_id")
    if p_id:
        _sim_post_woohoo_tracker.pop(p_id, None)

    b_id = spark.get("consume_bills_tracker_sim_id")
    if b_id:
        _sim_bills_paid_tracker.pop(b_id, None)

    r_id = spark.get("consume_romance_tracker_sim_id")
    if r_id:
        _sim_recent_romance_tracker.pop(r_id, None)

    int_id = spark.get("consume_intimacy_tracker_sim_id")
    if int_id:
        _sim_recent_intimacy_tracker.pop(int_id, None)

    parts = spark.get("participants", [])
    sim_a = parts[0] if len(parts) > 0 else None
    sim_b = parts[1] if len(parts) > 1 else None
    trigger_type = spark.get("trigger_type", "ambient")

    log(f"[DIRECTOR DISPATCH] Dispatching scene to Bridge: [{trigger_type}] (daily_key={daily_key or 'none'})")

    send_director_telemetry(
        "DISPATCH",
        f"[AI] Отправка запроса Режиссёра в AI Bridge [{trigger_type}]",
        [
            f"Повод: {spark.get('premise')}",
            "Ожидание генерации диалога нейросетью..."
        ],
        level="INFO"
    )

    try:
        from ai_social_pc.dossier_manager import build_third_party_dossier
        prem = spark.get("premise", "")
        parts = spark.get("participants", [])
        p_infos = [getattr(p, "sim_info", p) for p in parts if p]
        dossier_content = build_third_party_dossier(prem, p_infos)
        if dossier_content and payload is not None:
            payload["third_party_dossier"] = dossier_content
    except Exception:
        pass

    def _worker():
        global _is_scene_in_flight, _current_scene_trigger_type
        try:
            from ai_social_pc.chat_manager import BRIDGE_HOST, BRIDGE_PORT

            url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/autonomous_dialogue"
            data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            dialogue = resp_data.get("dialogue", [])
            if not dialogue:
                raw_txt = resp_data.get("raw_reply") or resp_data.get("thought") or resp_data.get("reply") or ""
                if raw_txt:
                    dialogue = parse_dialogue_fallback(raw_txt, spark)

            log(f"[DIRECTOR] Scene received from Bridge! Trigger: {trigger_type}, lines: {len(dialogue)}")

            if dialogue:
                record_scene_completed(sim_a, sim_b, trigger_type=trigger_type, spark=spark)

                if on_finish_callback is not None:
                    on_finish_callback(dialogue, spark)
                    _is_scene_in_flight = False
                    _current_scene_trigger_type = ""
                else:
                    play_autonomous_scene_balloons(dialogue, spark)
            else:
                _is_scene_in_flight = False
                _current_scene_trigger_type = ""

        except Exception as e:
            log_exception("[DIRECTOR] Failed to dispatch autonomous scene", e)
            send_director_telemetry(
                "ERROR",
                "[X] Ошибка соединения с AI Bridge",
                [f"Детали: {str(e)}", "Убедитесь, что AI Bridge запущен на 127.0.0.1:8765"],
                level="ERROR"
            )
            _is_scene_in_flight = False
            _current_scene_trigger_type = ""

    t = threading.Thread(target=_worker, name="SynapseAutonomousSceneWorker", daemon=True)
    t.start()
    return True


def play_autonomous_scene_balloons(dialogue_lines: List[Dict[str, str]], spark: Dict[str, Any]):
    """
    Sequentially displays 3D speech balloons over each speaking Sim's head.
    Respects comfortable reading speed and reading hold times between turns.
    Supports up to 8 Sims dynamically matching speakers by name.
    Does NOT cancel or interrupt Sims' active animations (eating, TV, cooking, etc.).
    """
    global _is_scene_in_flight, _current_scene_trigger_type
    if not dialogue_lines:
        _is_scene_in_flight = False
        _current_scene_trigger_type = ""
        return

    # Check if game is paused and notify player via telemetry
    try:
        if services is not None and hasattr(services, "game_clock_service"):
            gcs = services.game_clock_service()
            if gcs is not None and getattr(gcs, "clock_speed", 1) == 0:
                log("[AUTONOMOUS BALLOON] Game is PAUSED. Balloons will queue and display as soon as game is unpaused.")
                send_director_telemetry(
                    "PAUSE_NOTICE",
                    "[!] Игра на паузе: диалог ожидает снятия с паузы",
                    ["Снимите игру с паузы (нажмите 1 / Play), чтобы реплики начали появляться над симами."],
                    level="WARNING"
                )
    except Exception:
        pass

    # Collect all participants in the scene
    raw_participants = spark.get("all_scene_sims") or spark.get("participants", [])
    all_participants = []
    for p in raw_participants:
        inf = getattr(p, "sim_info", p)
        if inf is not None and inf not in all_participants:
            all_participants.append(inf)

    if not all_participants:
        _is_scene_in_flight = False
        _current_scene_trigger_type = ""
        return

    participant_lookup = []
    for inf in all_participants:
        first = str(getattr(inf, "first_name", "")).strip().lower()
        last = str(getattr(inf, "last_name", "")).strip().lower()
        full = f"{first} {last}".strip()
        sim_id = getattr(inf, "sim_id", 0)
        participant_lookup.append({
            "info": inf,
            "sim_id": sim_id,
            "first": first,
            "last": last,
            "full": full,
        })

    from ai_social_pc.main_thread import run_on_main_thread

    trigger_type = str(spark.get("trigger_type", "")).strip().lower()
    try:
        from ai_thought_reader.config import get_director_trigger_meta
        trig_meta = get_director_trigger_meta(trigger_type)
        enable_anim = bool(trig_meta.get("enable_animation", True))
        anim_type = str(trig_meta.get("animation_type", "AUTO")).upper()
    except Exception:
        enable_anim = True
        anim_type = "AUTO"

    def _play_scene_turn_animation(s_info, o_id, chosen_anim_type):
        try:
            if not enable_anim or s_info is None:
                return
            speaker_sim = s_info.get_sim_instance() if hasattr(s_info, "get_sim_instance") else None
            if speaker_sim is None:
                return

            other_sim = None
            if o_id and services is not None:
                sim_info_mgr = services.sim_info_manager()
                if sim_info_mgr is not None:
                    o_info = sim_info_mgr.get(o_id)
                    if o_info is not None and hasattr(o_info, "get_sim_instance"):
                        other_sim = o_info.get_sim_instance()

            if other_sim is None and len(all_participants) > 1:
                for p in all_participants:
                    p_id = getattr(p, "sim_id", 0)
                    if p_id != getattr(s_info, "sim_id", 0):
                        if hasattr(p, "get_sim_instance"):
                            other_sim = p.get_sim_instance()
                            if other_sim is not None:
                                break

            if speaker_sim is not None and other_sim is not None:
                from ai_social_pc.direct_dialogue import play_direct_dialogue_animation
                actual_cat = chosen_anim_type
                if actual_cat == "AUTO":
                    if trigger_type in ("cooking_burnt", "dirt_mess", "spoiled_food", "object_broke", "breakup_divorce"):
                        actual_cat = "MEAN"
                    elif trigger_type in ("relative_warm_welcome", "friend_chill", "family_tea", "cooking_masterpiece"):
                        actual_cat = "FRIENDLY"
                    elif trigger_type in ("prank_backfire",):
                        actual_cat = "FUNNY"
                    else:
                        actual_cat = "FRIENDLY"
                play_direct_dialogue_animation(speaker_sim, other_sim, anim_category=actual_cat)
        except Exception as ex_anim:
            log(f"[DIRECTOR ANIMATION] Error triggering turn animation: {ex_anim}")

    def _show_turn(s_info, text_to_show, other_id):
        if enable_anim:
            _play_scene_turn_animation(s_info, other_id, anim_type)
        if services is not None and hasattr(services, "current_zone"):
            try:
                zone = services.current_zone()
                if zone is None or getattr(zone, "is_zone_shutting_down", False):
                    return
            except Exception:
                pass

        try:
            from ai_thought_reader.config import get_display_flag
            show_dtr_bal = get_display_flag("director_balloon", True)
            show_dtr_notif = get_display_flag("director_notification", False)
        except Exception:
            show_dtr_bal = True
            show_dtr_notif = False

        if show_dtr_notif:
            try:
                from ai_thought_reader.ui_helper import show_notification
                first_name = getattr(s_info, "first_name", "Сим")
                show_notification(f"{first_name}:", f"«{text_to_show}»", sim_info=s_info, is_error=False)
            except Exception as ex_notif:
                log(f"[AUTONOMOUS NOTIF] Error displaying notification: {ex_notif}")

        if show_dtr_bal:
            try:
                try:
                    import synapse_balloons
                except ImportError:
                    from balloons import synapse_balloons

                if synapse_balloons is not None and hasattr(synapse_balloons, "show_sim_balloon"):
                    first_name = getattr(s_info, "first_name", None)
                    synapse_balloons.show_sim_balloon(
                        sim_info_or_id=s_info,
                        text=text_to_show,
                        balloon_type="speech",
                        name=first_name,
                        avoid_sim_id=other_id,
                    )
            except Exception as ex_b:
                log(f"[AUTONOMOUS BALLOON] Error displaying balloon: {ex_b}")

    accumulated_delay = 0.0
    prev_speaker_id = 0

    for idx, line in enumerate(dialogue_lines):
        spk_raw = str(line.get("speaker", "")).strip().lower()
        txt = str(line.get("text", "")).strip()
        if not txt:
            continue

        # Smart speaker matching with phonetic normalization (ё/э -> e) and priority scoring
        def _norm_name(s: str) -> str:
            if not s:
                return ""
            return s.strip().lower().replace("ё", "е").replace("э", "е")

        norm_spk = _norm_name(spk_raw)
        matched_entry = None
        best_score = 0

        for entry in participant_lookup:
            f = _norm_name(entry["first"])
            l = _norm_name(entry["last"])
            full = _norm_name(entry["full"])
            score = 0

            # 1. Full name exact match
            if full and full == norm_spk:
                score = 100
            # 2. First name exact word match
            elif f and (f == norm_spk or norm_spk.startswith(f + " ") or f" {f} " in f" {norm_spk} "):
                score = 80
            # 3. First name substring match
            elif f and (f in norm_spk or norm_spk in f):
                score = 60
            # 4. Unique last name match (ONLY if no other participant shares this surname!)
            elif l and (l in norm_spk or norm_spk in l):
                same_surname_count = sum(1 for p in participant_lookup if _norm_name(p["last"]) == l)
                if same_surname_count == 1:
                    score = 30

            if score > best_score:
                best_score = score
                matched_entry = entry

        if matched_entry is None or best_score < 40:
            # Fallback: alternate between participants if previous speaker is known
            if len(participant_lookup) == 2 and prev_speaker_id:
                matched_entry = next((e for e in participant_lookup if e["sim_id"] != prev_speaker_id), participant_lookup[idx % len(participant_lookup)])
            else:
                matched_entry = participant_lookup[idx % len(participant_lookup)]

        speaker_info = matched_entry["info"]
        current_speaker_id = matched_entry["sim_id"]

        # Record into 24-hour conversation log for all scene participants
        try:
            from ai_social_pc.conversation_log import record_conversation_exchange
            all_pids = [p["sim_id"] for p in participant_lookup if p.get("sim_id")]
            spk_disp_name = getattr(speaker_info, "first_name", line.get("speaker", "Sim"))
            record_conversation_exchange(
                participant_sim_ids=all_pids,
                speaker_id=current_speaker_id,
                speaker_name=spk_disp_name,
                text=txt,
                channel="autonomous_scene",
            )
            try:
                from ai_social_pc.conversation_log import record_overheard_exchange
                other_names = [p["first"] for p in participant_lookup if p.get("sim_id") != current_speaker_id and p.get("first")]
                other_tgt = ", ".join(other_names) if other_names else ""
                record_overheard_exchange(
                    center_sim_or_pos=speaker_info or sim_a,
                    speaker_id=current_speaker_id,
                    speaker_name=spk_disp_name,
                    text=txt,
                    channel="overheard_scene",
                    target_name=other_tgt,
                    exclude_sim_ids=set(all_pids),
                    max_distance=15.0,
                )
            except Exception as ex_ov_d:
                pass
        except Exception as ex_rec:
            log_exception("Failed to record autonomous scene turn to conversation log", ex_rec)

        # Avoid previous speaker or another participant
        if prev_speaker_id and prev_speaker_id != current_speaker_id:
            other_id = prev_speaker_id
        elif len(participant_lookup) > 1:
            other_id = next((e["sim_id"] for e in participant_lookup if e["sim_id"] != current_speaker_id), 0)
        else:
            other_id = 0

        prev_speaker_id = current_speaker_id

        # Schedule balloon appearance
        current_delay = accumulated_delay
        spk_disp = getattr(speaker_info, "first_name", "Сим")
        log(f"[AUTONOMOUS BALLOON] Turn {idx + 1}: {spk_disp} -> «{txt}» (t=+{current_delay:.1f}s)")

        if current_delay <= 0.05:
            run_on_main_thread(_show_turn, speaker_info, txt, other_id)
        else:
            t = threading.Timer(
                current_delay,
                lambda s=speaker_info, t=txt, o=other_id: run_on_main_thread(_show_turn, s, t, o)
            )
            t.daemon = True
            t.start()

        # Calculate time for player to read this turn before next speaker starts
        typing_time = len(txt) / 35.0
        reading_hold = 2.0 + (len(txt) * 0.04)
        turn_hold = max(3.8, min(8.5, typing_time + reading_hold))

        send_director_telemetry(
            "BALLOON",
            f"[CHAT] Реплика {idx + 1}/{len(dialogue_lines)} над головой {spk_disp}",
            [
                f"{spk_disp}: «{txt}»",
                f"Появление: +{current_delay:.1f}с | Чтение: {turn_hold:.1f}с (без прерывания анимаций)"
            ],
            level="INFO"
        )
        accumulated_delay += turn_hold

    # When all turns finish, unlock the scene lock after total sequence + 2s buffer
    def _unlock_scene():
        global _is_scene_in_flight, _current_scene_trigger_type
        _is_scene_in_flight = False
        _current_scene_trigger_type = ""
        log("[DIRECTOR] Autonomous dialogue sequence completed. Scene lock released.")

    unlock_timer = threading.Timer(accumulated_delay + 2.0, _unlock_scene)
    unlock_timer.daemon = True
    unlock_timer.start()


# =========================================================================
# GAME SIMULATION TICKER & VANILLA SOCIAL HOOK
# =========================================================================

_vanilla_mixer_hooked: bool = False


def on_director_zone_update_tick():
    """
    Called from Zone.update simulation loop.
    Periodically checks active household Sims for autonomous living dialogue
    opportunities every ~5 real seconds of unpaused play.
    """
    global _last_director_check_real_time, _last_silence_telemetry_real_time
    try:
        if services is None:
            return

        # 1. Quick in-memory check: if another scene is already generating or being displayed, skip tick
        if _is_scene_in_flight:
            return

        # 2. Check if game is paused (clock_speed == 0). Real-time clock freezes during pause.
        if is_game_paused():
            return

        # 3. Throttle check by unpaused real time (every ~5 real seconds) - BEFORE ANY DISK/CONFIG I/O
        now_rt = get_unpaused_real_time()
        if _last_director_check_real_time > 0 and (now_rt - _last_director_check_real_time) < DIRECTOR_TICK_INTERVAL_REAL_SECONDS:
            return

        _last_director_check_real_time = now_rt

        # 4. Check if Autonomous Director is enabled globally in settings
        try:
            from ai_thought_reader.config import get_director_enabled
            if not get_director_enabled():
                return
        except Exception:
            pass

        # 4b. Check zone load grace period protection (at least 60s of real time after entering a lot)
        grace_rem = get_zone_load_grace_remaining_seconds()
        if grace_rem > 0:
            global _last_grace_telemetry_real_time
            if (now_rt - _last_grace_telemetry_real_time) >= 10.0:
                _last_grace_telemetry_real_time = now_rt
                log(f"[DIRECTOR TICK] Zone load grace protection active: {int(grace_rem)}s remaining.")
                send_director_telemetry(
                    "GRACE_PERIOD",
                    f"Защита при входе на участок: {int(grace_rem)}с",
                    ["Режиссёр ожидает стабилизации игры после входа на участок", f"Осталось {int(grace_rem)} сек. реального времени"],
                    level="INFO"
                )
            return

        # 5. Check global household silence cooldown (in unpaused real seconds)
        hh_rem = get_household_silence_remaining_seconds()
        if hh_rem > 0:
            update_work_return_tracker()
            # IMMEDIATE TRIGGERS BREAK THROUGH SILENCE COOLDOWN!
            spark_imm = scan_household_for_best_scene(force=False, allow_immediate_only=True)
            if spark_imm is not None:
                log(f"[DIRECTOR TICK] IMMEDIATE spark broke through silence! Trigger: {spark_imm.get('trigger_type')} (prio={spark_imm.get('priority')})")
                send_director_telemetry(
                    "TICK_SPARK",
                    f"[!] Мгновенный повод пробил паузу тишины: [{spark_imm.get('trigger_type')}]",
                    [f"Повод: {spark_imm.get('premise')}", "Запуск генерации (пауза тишины будет сброшена после завершения сцены)"],
                    level="SUCCESS"
                )
                dispatch_autonomous_scene(spark_imm)
                return



            if (now_rt - _last_silence_telemetry_real_time) >= 5.0:
                _last_silence_telemetry_real_time = now_rt
                st_cur = get_director_lot_state()
                log(f"[DIRECTOR TICK] Silence cooldown active: {int(hh_rem)}s remaining. State: {st_cur}")
                send_director_telemetry(
                    "COOLDOWN",
                    f"Пауза тишины дома: осталось {int(hh_rem)}с (режим {st_cur})",
                    [f"Режиссёр ждёт окончания естественной паузы", f"Осталось: {int(hh_rem)}с реального времени"],
                    level="INFO"
                )
            return

        # 6. Scan active household for the best spark (both immediate and ambient allowed)
        spark = scan_household_for_best_scene(force=False, allow_immediate_only=False)
        if spark is not None:
            _last_silence_telemetry_real_time = now_rt
            trig_name = spark.get('trigger_type', '')
            log(f"[DIRECTOR TICK] Autonomous spark detected! Trigger: {trig_name} (prio={spark.get('priority')})")
            send_director_telemetry(
                "TICK_SPARK",
                f"Сработал автономный повод: [{trig_name}]",
                [f"Повод: {spark.get('premise')}", "Запуск генерации диалога в нейросети..."],
                level="SUCCESS"
            )
            dispatch_autonomous_scene(spark)
        else:
            if (now_rt - _last_silence_telemetry_real_time) >= 5.0:
                _last_silence_telemetry_real_time = now_rt
                st_cur = get_director_lot_state()
                log(f"[DIRECTOR TICK] Scan tick complete. No candidate spark found right now in state '{st_cur}'.")
                send_director_telemetry(
                    "SCAN",
                    f"Сканирование: режим {st_cur} (симы в комнате оцениваются)",
                    [f"Режиссёр активен и проверяет обстановку"],
                    level="INFO"
                )


    except Exception as e:
        log_exception("Error in on_director_zone_update_tick", e)


def on_vanilla_social_mixer_triggered(mixer_interaction):
    """
    Called when any SocialMixerInteraction executes.
    If two active household Sims autonomously talk to each other in-game,
    checks if the Director should attach a contextual living dialogue.
    """
    if mixer_interaction is None or services is None:
        return

    if _is_scene_in_flight:
        return

def on_vanilla_social_mixer_triggered(mixer_interaction):
    """Deprecated: vanilla social interactions are no longer intercepted separately.
    The Director evaluates ambient co-presence strictly via the 22 registered actions."""
    pass


def hook_vanilla_social_mixer():
    """No-op: All dialogues run strictly through the Director's 22 situational actions."""
    pass



