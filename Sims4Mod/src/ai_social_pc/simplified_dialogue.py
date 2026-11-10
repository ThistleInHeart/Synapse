# -*- coding: utf-8 -*-
"""
Synapse Simplified Autonomous Dialogue (Упрощённое автономное общение)
Lightweight alternative mode: generates spontaneous 2-turn or group dialogue during
standard vanilla Sims chatting (pairs and 3+ Sims groups) without pushing interactions
or breaking queues.
Mutually exclusive with the Autonomous Director.
"""

import time
import random
import threading
from typing import Optional, Tuple, List, Dict, Any

try:
    import services
except ImportError:
    services = None

try:
    import sims4
    import sims4.commands
except ImportError:
    sims4 = None

try:
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    LocalizationHelperTuning = None

import json
import urllib.request

def send_request(endpoint: str, payload: dict, timeout: int = 45) -> Optional[dict]:
    """Sends JSON POST request to Synapse Bridge."""
    try:
        from ai_social_pc.chat_manager import BRIDGE_HOST, BRIDGE_PORT
    except Exception:
        BRIDGE_HOST = "127.0.0.1"
        BRIDGE_PORT = 5000

    url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        log_exception(f"Error sending request to Bridge endpoint {endpoint}", e)
        return None

from ai_thought_reader.config import (
    log, log_exception,
    get_simplified_dialogue_enabled,
    get_simplified_dialogue_timers,
    get_simplified_dialogue_balloon,
    get_simplified_dialogue_notification,
    get_director_enabled,
)

_is_dialogue_in_flight: bool = False
_last_dialogue_real_time: float = 0.0
_last_tick_check_real_time: float = 0.0
SIMPLIFIED_TICK_INTERVAL_REAL_SECONDS: float = 4.0


def cheat_print(connection, text: str):
    """Prints message safely to game cheat console and log."""
    log(f"[SIMPLIFIED CONSOLE] {text}")
    try:
        if sims4 is not None and hasattr(sims4, "commands"):
            if hasattr(sims4.commands, "cheat_output"):
                sims4.commands.cheat_output(text, connection)
            elif connection is not None and hasattr(sims4.commands, "output"):
                sims4.commands.output(text, connection)
    except Exception:
        pass


def get_sim_name(sim) -> str:
    """Helper to safely retrieve a readable full name of a Sim or SimInfo."""
    if sim is None:
        return "Сим"
    try:
        inf = getattr(sim, "sim_info", sim)
        fn = getattr(inf, "first_name", "") or getattr(sim, "first_name", "")
        ln = getattr(inf, "last_name", "") or getattr(sim, "last_name", "")
        full = f"{fn} {ln}".strip()
        if full:
            return full
        if hasattr(inf, "full_name") and inf.full_name:
            return str(inf.full_name)
    except Exception:
        pass
    return "Сим"


def is_game_paused() -> bool:
    """Checks if the game clock is currently paused."""
    if services is None:
        return False
    try:
        from clock import ClockSpeedMode
        clock_service = services.game_clock_service()
        if clock_service is not None:
            return clock_service.clock_speed == ClockSpeedMode.PAUSED
    except Exception:
        pass
    return False


def get_unpaused_real_time() -> float:
    """Returns monotonically increasing unpaused real time."""
    try:
        from ai_social_pc.autonomous_director import get_unpaused_real_time as get_dir_time
        return get_dir_time()
    except Exception:
        return time.time()


def get_all_instanced_sims() -> List[Any]:
    """
    Safely retrieves all currently instanced 3D Sim actors in the active zone.
    Uses multiple fallback sources to guarantee all instanced Sims are detected.
    """
    if services is None:
        return []

    sims_dict = {}

    # 1. Active sim from client manager
    try:
        if hasattr(services, "client_manager"):
            cm = services.client_manager()
            if cm:
                client = cm.get_first_client()
                if client and hasattr(client, "active_sim") and client.active_sim is not None:
                    sims_dict[client.active_sim.id] = client.active_sim
    except Exception as e:
        log_exception("Error in get_all_instanced_sims (client_manager)", e)

    # 2. From sim_info_manager instanced_sims_gen and get_all()
    try:
        if hasattr(services, "sim_info_manager"):
            sim_mgr = services.sim_info_manager()
            if sim_mgr is not None:
                if hasattr(sim_mgr, "instanced_sims_gen"):
                    for inst in sim_mgr.instanced_sims_gen():
                        if inst is not None and getattr(inst, "id", None) is not None:
                            sims_dict[inst.id] = inst
                if hasattr(sim_mgr, "get_all"):
                    for s_info in sim_mgr.get_all():
                        if hasattr(s_info, "get_sim_instance"):
                            inst = s_info.get_sim_instance()
                            if inst is not None and getattr(inst, "id", None) is not None:
                                sims_dict[inst.id] = inst
                if hasattr(sim_mgr, "values"):
                    try:
                        for s_info in sim_mgr.values():
                            if hasattr(s_info, "get_sim_instance"):
                                inst = s_info.get_sim_instance()
                                if inst is not None and getattr(inst, "id", None) is not None:
                                    sims_dict[inst.id] = inst
                    except Exception:
                        pass
    except Exception as e:
        log_exception("Error in get_all_instanced_sims (sim_info_manager)", e)

    # 3. From active household
    try:
        if hasattr(services, "active_household"):
            hh = services.active_household()
            if hh is not None:
                if hasattr(hh, "instanced_sims_gen"):
                    for inst in hh.instanced_sims_gen():
                        if inst is not None and getattr(inst, "id", None) is not None:
                            sims_dict[inst.id] = inst
                if hasattr(hh, "sim_info_gen"):
                    for s_info in hh.sim_info_gen():
                        if hasattr(s_info, "get_sim_instance"):
                            inst = s_info.get_sim_instance()
                            if inst is not None and getattr(inst, "id", None) is not None:
                                sims_dict[inst.id] = inst
    except Exception as e:
        log_exception("Error in get_all_instanced_sims (active_household)", e)

    # 4. From object_manager
    try:
        if hasattr(services, "object_manager"):
            obj_mgr = services.object_manager()
            if obj_mgr and hasattr(obj_mgr, "get_all"):
                for obj in obj_mgr.get_all():
                    if getattr(obj, "is_sim", False) and getattr(obj, "id", None) is not None:
                        sims_dict[obj.id] = obj
    except Exception as e:
        log_exception("Error in get_all_instanced_sims (object_manager)", e)

    return list(sims_dict.values())


def is_sim_in_active_household(sim) -> bool:
    """Checks if a Sim belongs to the currently active household."""
    if sim is None:
        return False
    try:
        if services is None:
            return False

        # Direct check 1: Active sim from client
        if hasattr(services, "client_manager"):
            cm = services.client_manager()
            if cm:
                client = cm.get_first_client()
                if client and hasattr(client, "active_sim") and client.active_sim is not None:
                    if sim is client.active_sim or getattr(sim, "id", -1) == getattr(client.active_sim, "id", -2):
                        return True

        # Direct check 2: selectable / selected flags on sim or sim_info
        sim_info = getattr(sim, "sim_info", sim)
        if getattr(sim_info, "is_selectable", False) or getattr(sim_info, "is_selected", False):
            return True
        if getattr(sim, "is_selected", False) or getattr(sim, "is_selectable", False):
            return True

        # Direct check 3: Active household match
        if hasattr(services, "active_household"):
            active_hh = services.active_household()
            if active_hh is not None:
                sim_id = getattr(sim_info, "sim_id", None) or getattr(sim, "id", None)
                if sim_id:
                    if hasattr(active_hh, "sim_info_gen"):
                        for h_info in active_hh.sim_info_gen():
                            if getattr(h_info, "sim_id", None) == sim_id:
                                return True
                    if hasattr(active_hh, "sim_infos"):
                        for h_info in active_hh.sim_infos:
                            if getattr(h_info, "sim_id", None) == sim_id:
                                return True
                if sim_info in active_hh:
                    return True
    except Exception:
        pass
    return False


def is_sim_available(sim) -> bool:
    """Checks if a Sim is awake, present on lot, and available to speak."""
    if sim is None:
        return False
    try:
        sim_info = getattr(sim, "sim_info", sim)
        if sim_info is None:
            return False
        if getattr(sim_info, "is_pet", False):
            return False
        if getattr(sim_info, "is_dead", False) or getattr(sim, "is_dying", False):
            return False

        # Activity check (sleep/nap)
        act_lower = ""
        try:
            from ai_thought_reader.context import get_current_activity
            act_lower = (get_current_activity(sim_info) or "").lower()
        except Exception:
            pass
        if any(w in act_lower for w in ["сон", "спит", "дремлет", "sleeping", "nap"]):
            return False

        return True
    except Exception:
        return False


def are_sims_actively_conversing(sim_a, sim_b) -> bool:
    """Checks if two Sims are actively chatting in the game."""
    if sim_a is None or sim_b is None:
        return False
    if sim_a is sim_b or getattr(sim_a, "id", -1) == getattr(sim_b, "id", -2):
        return False

    # 1. Social group check via methods
    try:
        for getter in ("get_main_social_group", "get_main_group"):
            if hasattr(sim_a, getter):
                sg_a = getattr(sim_a, getter)()
                if sg_a is not None and hasattr(sg_a, "members"):
                    for m in sg_a.members:
                        if m is sim_b or getattr(m, "id", -1) == getattr(sim_b, "id", -2):
                            return True
            if hasattr(sim_b, getter):
                sg_b = getattr(sim_b, getter)()
                if sg_b is not None and hasattr(sg_b, "members"):
                    for m in sg_b.members:
                        if m is sim_a or getattr(m, "id", -1) == getattr(sim_a, "id", -2):
                            return True
    except Exception:
        pass

    # 2. Social group cluster service
    try:
        if services is not None and hasattr(services, "social_group_cluster_service"):
            sg_service = services.social_group_cluster_service()
            if sg_service is not None:
                grp_a = sg_service.get_social_group_for_sim(sim_a)
                grp_b = sg_service.get_social_group_for_sim(sim_b)
                if grp_a is not None and grp_b is not None and (grp_a is grp_b or getattr(grp_a, "id", 1) == getattr(grp_b, "id", 2)):
                    return True
    except Exception:
        pass

    # 3. Running/queued interactions targeting each other
    try:
        info_a = getattr(sim_a, "sim_info", sim_a)
        info_b = getattr(sim_b, "sim_info", sim_b)
        id_a = getattr(sim_a, "id", None) or getattr(info_a, "sim_id", -1)
        id_b = getattr(sim_b, "id", None) or getattr(info_b, "sim_id", -2)

        for s1, s2, i2, target_id in ((sim_a, sim_b, info_b, id_b), (sim_b, sim_a, info_a, id_a)):
            if hasattr(s1, "get_all_running_and_queued_interactions"):
                for inter in s1.get_all_running_and_queued_interactions():
                    t = getattr(inter, "target", None)
                    if t is None:
                        continue
                    if t is s2 or t is i2:
                        return True
                    t_id = getattr(t, "id", None) or getattr(getattr(t, "sim_info", None), "sim_id", None)
                    if t_id is not None and t_id == target_id:
                        return True
    except Exception:
        pass

    # 4. Fallback to autonomous_director check
    try:
        from ai_social_pc.autonomous_director import are_sims_actively_conversing as dir_are_talking
        return dir_are_talking(sim_a, sim_b)
    except Exception:
        pass

    return False


def find_conversing_groups(require_household: bool = False) -> List[List[Any]]:
    """
    Finds all active chatting groups (pairs or 3+ Sims) on the lot.
    If require_household=True, at least one member must belong to the active household.
    """
    groups = []
    instanced_sims = get_all_instanced_sims()
    if not instanced_sims:
        return groups

    avail_sims = [s for s in instanced_sims if is_sim_available(s)]
    if not avail_sims:
        avail_sims = [s for s in instanced_sims if not getattr(getattr(s, "sim_info", None), "is_pet", False)]

    sims_by_id = {s.id: s for s in avail_sims if getattr(s, "id", None) is not None}

    # 1. Group by SocialGroup
    sg_members_map = {}
    for s in avail_sims:
        s_sg = None
        for getter in ("get_main_social_group", "get_main_group"):
            if hasattr(s, getter):
                try:
                    s_sg = getattr(s, getter)()
                    if s_sg is not None:
                        break
                except Exception:
                    pass

        if s_sg is None and services is not None and hasattr(services, "social_group_cluster_service"):
            try:
                sg_service = services.social_group_cluster_service()
                if sg_service is not None:
                    s_sg = sg_service.get_social_group_for_sim(s)
            except Exception:
                pass

        if s_sg is not None:
            sg_key = getattr(s_sg, "id", None) or id(s_sg)
            if sg_key not in sg_members_map:
                sg_members_map[sg_key] = set()
            sg_members_map[sg_key].add(s.id)

            if hasattr(s_sg, "members"):
                try:
                    for m in s_sg.members:
                        m_inst = getattr(m, "get_sim_instance", lambda: m)() if hasattr(m, "get_sim_instance") else m
                        m_id = getattr(m_inst, "id", None)
                        if m_id and m_id in sims_by_id:
                            sg_members_map[sg_key].add(m_id)
                except Exception:
                    pass

    seen_sim_ids = set()
    for sg_key, member_ids in sg_members_map.items():
        if len(member_ids) >= 2:
            group_sims = [sims_by_id[sid] for sid in member_ids if sid in sims_by_id]
            if len(group_sims) >= 2:
                if not require_household or any(is_sim_in_active_household(m) for m in group_sims):
                    groups.append(group_sims)
                    for m in group_sims:
                        seen_sim_ids.add(m.id)

    # 2. Pairwise interaction / clustering fallback
    for i, sa in enumerate(avail_sims):
        if sa.id in seen_sim_ids:
            continue
        cluster = [sa]
        for sb in avail_sims[i+1:]:
            if sb.id in seen_sim_ids:
                continue
            if are_sims_actively_conversing(sa, sb):
                cluster.append(sb)

        if len(cluster) >= 2:
            if not require_household or any(is_sim_in_active_household(m) for m in cluster):
                groups.append(cluster)
                for m in cluster:
                    seen_sim_ids.add(m.id)

    return groups


def find_conversing_pairs() -> List[Tuple[Any, Any]]:
    """Backward compatibility helper: returns 2-Sim pairs from active groups."""
    pairs = []
    groups = find_conversing_groups(require_household=False)
    for grp in groups:
        if len(grp) >= 2:
            pairs.append((grp[0], grp[1]))
    return pairs


def find_potential_candidates(max_distance: float = 25.0) -> List[Dict[str, Any]]:
    """
    Finds available Sims on the lot who are NOT currently chatting in an active group,
    paired with active household Sims, sorted by distance.
    """
    candidates = []
    instanced_sims = get_all_instanced_sims()
    if not instanced_sims:
        return candidates

    avail_sims = [s for s in instanced_sims if is_sim_available(s)]
    if not avail_sims:
        avail_sims = [s for s in instanced_sims if not getattr(getattr(s, "sim_info", None), "is_pet", False)]

    active_groups = find_conversing_groups(require_household=False)
    busy_sim_ids = set()
    for grp in active_groups:
        for s in grp:
            busy_sim_ids.add(s.id)

    free_sims = [s for s in avail_sims if s.id not in busy_sim_ids]
    selectable_free = [s for s in free_sims if is_sim_in_active_household(s)]
    target_initiators = selectable_free if selectable_free else free_sims

    seen_pairs = set()

    for sa in target_initiators:
        pos_a = getattr(sa, "position", None)
        loc_a = get_room_and_lot_desc(sa)

        for sb in free_sims:
            if sa is sb or sa.id == sb.id:
                continue
            pair_key = (min(sa.id, sb.id), max(sa.id, sb.id))
            if pair_key in seen_pairs:
                continue

            pos_b = getattr(sb, "position", None)
            loc_b = get_room_and_lot_desc(sb)

            dist = 999.0
            if pos_a is not None and pos_b is not None:
                dx = getattr(pos_a, "x", 0.0) - getattr(pos_b, "x", 0.0)
                dz = getattr(pos_a, "z", 0.0) - getattr(pos_b, "z", 0.0)
                dist = (dx * dx + dz * dz) ** 0.5

            same_room = bool(loc_a and loc_b and loc_a == loc_b and "Комната" not in loc_a)
            is_nearby = (dist <= max_distance) or same_room

            if is_nearby:
                seen_pairs.add(pair_key)
                na = get_sim_name(sa)
                nb = get_sim_name(sb)
                sa_info = getattr(sa, "sim_info", sa)
                sb_info = getattr(sb, "sim_info", sb)
                rel = get_relationship_desc(sa_info, sb_info)

                mood_a = "Нейтральный"
                try:
                    if hasattr(sa, "get_mood") and sa.get_mood():
                        mood_a = getattr(sa.get_mood(), "name", "Нейтральный")
                    elif hasattr(sa_info, "get_mood") and sa_info.get_mood():
                        mood_a = getattr(sa_info.get_mood(), "name", "Нейтральный")
                except Exception:
                    pass

                mood_b = "Нейтральный"
                try:
                    if hasattr(sb, "get_mood") and sb.get_mood():
                        mood_b = getattr(sb.get_mood(), "name", "Нейтральный")
                    elif hasattr(sb_info, "get_mood") and sb_info.get_mood():
                        mood_b = getattr(sb_info.get_mood(), "name", "Нейтральный")
                except Exception:
                    pass

                candidates.append({
                    "sims": [sa, sb],
                    "sim_a": na,
                    "sim_b": nb,
                    "distance": round(dist, 1) if dist < 900 else -1,
                    "location": loc_a,
                    "relationship": rel,
                    "mood_a": mood_a,
                    "mood_b": mood_b,
                })

    candidates.sort(key=lambda c: (c["distance"] if c["distance"] >= 0 else 999))
    return candidates


def get_sim_profile_summary(sim_info, is_actor: bool = False, other_sim_info: Any = None) -> str:
    """Builds a complete, rich profile summary for a Sim matching the full Synapse live dialogue specification."""
    try:
        from ai_social_pc.chat_manager import _build_sim_profile_summary
        return _build_sim_profile_summary(sim_info, is_actor=is_actor, is_direct_dialogue=True, other_sim_info=other_sim_info)
    except Exception as e:
        log_exception("Error in get_sim_profile_summary via _build_sim_profile_summary", e)
    return f"- Имя: {get_sim_name(sim_info)}"


def get_relationship_desc(sim_info_a, sim_info_b) -> str:
    """Returns comprehensive relationship description between two Sims matching live dialogue."""
    try:
        from ai_social_pc.chat_manager import _get_relationship_description
        return _get_relationship_description(sim_info_a, sim_info_b)
    except Exception as e:
        log_exception("Error in get_relationship_desc", e)
    return "Знакомые (Дружба: 0, Романтика: 0)"


def get_room_and_lot_desc(sim) -> str:
    """Returns room/location description where the Sim is standing."""
    try:
        from ai_thought_reader.context import get_room_description_for_sim
        room = get_room_description_for_sim(sim)
        if room:
            return room
    except Exception:
        pass
    try:
        zone = services.current_zone() if services else None
        if zone is not None:
            lot = getattr(zone, "lot", None)
            if lot and hasattr(lot, "get_lot_name"):
                lot_name = lot.get_lot_name()
                if lot_name:
                    return lot_name
            return getattr(zone, "name", "На участке")
    except Exception:
        pass
    return "На участке"


def play_simplified_dialogue(sim_a_or_group, dialogue_lines_or_sim_b, third_arg=None):
    """
    Displays the generated dialogue over the Sims' heads using synapse_balloons.
    Supports both 2-turn pairs and 3+ Sims group dialogues sequentially!
    No interactions or queue actions are pushed!
    """
    if third_arg is not None:
        group_sims = [sim_a_or_group, dialogue_lines_or_sim_b]
        dialogue_lines = third_arg
    elif isinstance(sim_a_or_group, (list, tuple)):
        group_sims = list(sim_a_or_group)
        dialogue_lines = dialogue_lines_or_sim_b
    else:
        group_sims = [sim_a_or_group]
        dialogue_lines = dialogue_lines_or_sim_b

    if not dialogue_lines or not group_sims:
        return

    try:
        try:
            import synapse_balloons
        except ImportError:
            from balloons import synapse_balloons

        show_bal = get_simplified_dialogue_balloon()
        show_notif = get_simplified_dialogue_notification()
        log(f"[SIMPLIFIED] Playing dialogue ({len(dialogue_lines)} lines). Flags: balloon={show_bal}, notification={show_notif}")

        all_group_sim_ids = []
        for s in group_sims:
            s_inf = getattr(s, "sim_info", s)
            s_id_val = getattr(s_inf, "sim_id", 0) or getattr(s, "id", 0)
            if s_id_val:
                all_group_sim_ids.append(s_id_val)

        current_delay = 0.0
        for idx, turn in enumerate(dialogue_lines):
            spk_raw = str(turn.get("speaker") or "").strip()
            txt = str(turn.get("text") or "").strip()
            if not txt:
                continue

            # Match speaker to a Sim in the group
            matched_sim = None
            spk_lower = spk_raw.lower()
            for s in group_sims:
                s_name = get_sim_name(s).lower()
                s_inf = getattr(s, "sim_info", s)
                s_fn = getattr(s_inf, "first_name", "").strip().lower()
                if (s_fn and s_fn in spk_lower) or (s_name and (s_name in spk_lower or spk_lower in s_name)):
                    matched_sim = s
                    break

            if matched_sim is None:
                matched_sim = group_sims[idx % len(group_sims)]

            # Record each turn into conversation memory log
            try:
                from ai_social_pc.conversation_log import record_conversation_exchange, record_overheard_exchange
                conv_ch = "group_dialogue" if len(group_sims) > 2 else "direct_dialogue"
                spk_info = getattr(matched_sim, "sim_info", matched_sim)
                spk_id = getattr(spk_info, "sim_id", 0) or getattr(matched_sim, "id", 0)
                spk_name = get_sim_name(matched_sim)

                record_conversation_exchange(
                    participant_sim_ids=all_group_sim_ids,
                    speaker_id=spk_id,
                    speaker_name=spk_name,
                    text=txt,
                    channel=conv_ch,
                )

                try:
                    target_names = [get_sim_name(os) for os in group_sims if os is not matched_sim]
                    t_names_str = ", ".join(target_names) if target_names else ""
                    record_overheard_exchange(
                        center_sim_or_pos=matched_sim,
                        speaker_id=spk_id,
                        speaker_name=spk_name,
                        text=txt,
                        channel="overheard_dialogue",
                        target_name=t_names_str,
                        exclude_sim_ids=set(all_group_sim_ids),
                        max_distance=15.0,
                    )
                except Exception:
                    pass
            except Exception as e_mem_rec:
                log_exception("Error recording simplified dialogue turn to memory log", e_mem_rec)

            # Pick another sim to avoid overlaying balloon
            avoid_id = 0
            for os_cand in group_sims:
                if os_cand is not matched_sim:
                    avoid_id = getattr(os_cand, "id", 0)
                    break

            def _make_show_turn(s_sim, s_txt, s_avoid_id):
                def _show(_alarm_handle=None):
                    s_info = getattr(s_sim, "sim_info", None)
                    if s_info is None:
                        return
                    if show_notif:
                        try:
                            from ai_thought_reader.ui_helper import show_notification
                            fn = getattr(s_info, "first_name", "Сим")
                            show_notification(f"{fn}:", f"«{s_txt}»", sim_info=s_info, is_error=False)
                        except Exception:
                            pass
                    if show_bal and synapse_balloons is not None and hasattr(synapse_balloons, "show_sim_balloon"):
                        try:
                            synapse_balloons.show_sim_balloon(s_info, s_txt, balloon_type="speech", avoid_sim_id=s_avoid_id)
                        except Exception as e_bal:
                            log_exception("Error displaying simplified balloon", e_bal)
                return _show

            show_func = _make_show_turn(matched_sim, txt, avoid_id)

            if idx == 0:
                show_func()
            else:
                try:
                    import alarms
                    import date_and_time
                    time_span = date_and_time.create_time_span(seconds=current_delay)
                    alarms.add_alarm(matched_sim, time_span, show_func)
                except Exception:
                    threading.Timer(current_delay, show_func).start()

            # Dynamic delay for each turn based on reading length
            line_dur = max(3.5, min(7.0, len(txt) * 0.05 + 2.8))
            current_delay += line_dur

    except Exception as e:
        log_exception("Error in play_simplified_dialogue", e)


def dispatch_simplified_dialogue(sim_a_or_group, sim_b=None, on_finish=None):
    """Asynchronously calls Bridge /simplified_dialogue and plays result with FULL live context."""
    global _is_dialogue_in_flight, _last_dialogue_real_time

    if _is_dialogue_in_flight:
        return False

    if isinstance(sim_a_or_group, (list, tuple)):
        group_sims = list(sim_a_or_group)
    else:
        group_sims = [sim_a_or_group, sim_b] if sim_b is not None else [sim_a_or_group]

    if len(group_sims) < 2:
        return False

    _is_dialogue_in_flight = True

    def _worker():
        global _is_dialogue_in_flight, _last_dialogue_real_time
        try:
            participants = []
            first_sim = group_sims[0]
            first_sim_info = getattr(first_sim, "sim_info", first_sim)

            for idx, s in enumerate(group_sims):
                inf = getattr(s, "sim_info", None)
                if inf is None:
                    continue
                name = get_sim_name(s)
                mood = getattr(inf.get_mood(), "name", "Нейтральный") if hasattr(inf, "get_mood") else "Нейтральный"
                other_inf = first_sim_info if idx > 0 else (getattr(group_sims[1], "sim_info", None) if len(group_sims) > 1 else None)
                prof = get_sim_profile_summary(inf, is_actor=(idx == 0), other_sim_info=other_inf)
                rel = get_relationship_desc(first_sim_info, inf) if idx > 0 else "Инициатор"
                is_sel = is_sim_in_active_household(s)
                participants.append({
                    "name": name,
                    "first_name": getattr(inf, "first_name", name),
                    "info": prof,
                    "mood": mood,
                    "relationship": rel,
                    "selectable": is_sel,
                })

            if len(participants) < 2:
                return

            loc_desc = ""
            try:
                from ai_social_pc.chat_manager import _get_direct_dialogue_location
                loc_desc = _get_direct_dialogue_location(first_sim_info, is_en=False)
            except Exception:
                loc_desc = get_room_and_lot_desc(group_sims[0])

            cur_sim_time = ""
            cur_season = ""
            cur_weather = ""
            cur_holiday = ""
            cur_world = ""
            lot_ev = ""
            try:
                from ai_thought_reader.context import (
                    get_world_time_info,
                    get_season_info,
                    get_weather_info,
                    get_holiday_info,
                    get_current_world_name,
                    get_active_social_event_info,
                )
                cur_sim_time = get_world_time_info() or ""
                cur_season = get_season_info() or ""
                cur_weather = get_weather_info() or ""
                cur_holiday = get_holiday_info(first_sim_info) or ""
                cur_world = get_current_world_name() or ""
                lot_ev = get_active_social_event_info(first_sim_info, is_en=False) or ""
            except Exception as ex_env:
                log_exception("Error collecting environment in simplified dialogue", ex_env)

            memories_txt = ""
            try:
                from ai_social_pc.memory_manager import get_recent_memories_text
                id0 = getattr(first_sim_info, "sim_id", 0) or getattr(first_sim_info, "id", 0)
                sec_inf = getattr(group_sims[1], "sim_info", group_sims[1]) if len(group_sims) > 1 else None
                id1 = getattr(sec_inf, "sim_id", 0) or getattr(sec_inf, "id", 0) if sec_inf else 0
                if id0 and id1:
                    memories_txt = get_recent_memories_text(id0, id1, limit=5)
            except Exception as ex_mem:
                log_exception("Error collecting memories in simplified dialogue", ex_mem)

            payload = {
                "type": "simplified_dialogue",
                "actor_name": participants[0]["name"],
                "target_name": participants[1]["name"],
                "actor_info": participants[0]["info"],
                "target_info": participants[1]["info"],
                "relationship": participants[1]["relationship"],
                "participants": participants,
                "location": loc_desc,
                "world": cur_world,
                "current_time": cur_sim_time,
                "season": cur_season,
                "weather": cur_weather,
                "holiday": cur_holiday,
                "event": lot_ev,
                "memories": memories_txt,
            }

            p_names = ", ".join([p["name"] for p in participants])
            log(f"[SIMPLIFIED] Sending full dialogue request for {len(participants)} Sims: {p_names}...")
            resp = send_request("simplified_dialogue", payload)

            if resp and isinstance(resp, dict) and (resp.get("status") == "success" or resp.get("success") is True):
                dialogue = resp.get("dialogue", [])
                if dialogue:
                    log(f"[SIMPLIFIED] Received {len(dialogue)} dialogue lines. Playing speech balloons...")
                    play_simplified_dialogue(group_sims, dialogue)
                    _last_dialogue_real_time = get_unpaused_real_time()
            else:
                log(f"[SIMPLIFIED] Bridge returned non-success or empty dialogue: {resp}")

        except Exception as e:
            log_exception("Error in dispatch_simplified_dialogue worker", e)
        finally:
            _is_dialogue_in_flight = False
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

    th = threading.Thread(target=_worker, name="SynapseSimplifiedDialogueThread", daemon=True)
    th.start()
    return True


def on_simplified_dialogue_tick():
    """
    Called periodically from zone update loop.
    Checks whether active Sims are conversing and rolls chance to generate dialogue.
    """
    global _last_tick_check_real_time, _last_dialogue_real_time

    try:
        if not get_simplified_dialogue_enabled():
            return
        if get_director_enabled():
            return
        if _is_dialogue_in_flight:
            return
        if is_game_paused():
            return

        now_rt = get_unpaused_real_time()
        if _last_tick_check_real_time > 0 and (now_rt - _last_tick_check_real_time) < SIMPLIFIED_TICK_INTERVAL_REAL_SECONDS:
            return
        _last_tick_check_real_time = now_rt

        timers = get_simplified_dialogue_timers()
        silence_sec = timers.get("silence_sec", 180)
        chance_pct = timers.get("trigger_chance_pct", 40)

        if _last_dialogue_real_time > 0:
            elapsed = now_rt - _last_dialogue_real_time
            if elapsed < silence_sec:
                return

        # Prioritize conversations involving active household
        groups = find_conversing_groups(require_household=True)
        if not groups:
            return

        roll = random.randint(1, 100)
        if roll > chance_pct:
            _last_dialogue_real_time = now_rt - max(0, silence_sec - 25.0)
            log(f"[SIMPLIFIED TICK] Conversing group found, but chance roll failed ({roll} > {chance_pct}%). Retrying in 25s.")
            return

        chosen_group = random.choice(groups)
        p_names = ", ".join([get_sim_name(s) for s in chosen_group])
        log(f"[SIMPLIFIED TICK] Triggering simplified dialogue for active chatting group ({len(chosen_group)} Sims): {p_names} (roll={roll} <= {chance_pct}%)")
        dispatch_simplified_dialogue(chosen_group)

    except Exception as e:
        log_exception("Error in on_simplified_dialogue_tick", e)


def force_trigger_simplified_dialogue(_connection=None):
    """
    Forces an immediate Simplified Dialogue execution between currently talking Sims
    or nearby active Sims. Triggered via cheat command 'synapse.run_simplified'.
    """
    def _print(msg):
        cheat_print(_connection, msg)

    # Check active conversing groups first
    groups = find_conversing_groups(require_household=True)
    if not groups:
        groups = find_conversing_groups(require_household=False)

    if groups:
        chosen_group = groups[0]
        names = [get_sim_name(s) for s in chosen_group]
        _print(f"Запуск диалога для активно общающихся симов ({len(chosen_group)}): {', '.join(names)}...")
        dispatch_simplified_dialogue(chosen_group)
        return True

    # If no active group is talking, look for potential candidate cluster/pair nearby
    candidates = find_potential_candidates()
    if candidates:
        cand = candidates[0]
        cand_sims = cand.get("sims", [])
        if len(cand_sims) >= 2:
            names = [get_sim_name(s) for s in cand_sims]
            dist_str = f"~{cand.get('distance')}м" if cand.get('distance', -1) > 0 else "в одной комнате"
            _print(f"Активных разговоров нет, но найдены подходящие кандидаты рядом ({len(cand_sims)}): {', '.join(names)} (локация '{cand.get('location')}', {dist_str}). Запуск...")
            dispatch_simplified_dialogue(cand_sims)
            return True

    _print("Ошибка: На участке не найдено ни активно общающихся симов, ни доступных кандидатов рядом.")
    return False


def reset_simplified_silence():
    """Resets the silence timer so dialogue can trigger immediately."""
    global _last_dialogue_real_time
    _last_dialogue_real_time = 0.0
    log("[SIMPLIFIED] Silence timer reset.")


def get_simplified_status() -> Dict[str, Any]:
    """Returns high-level status dictionary for debug commands."""
    timers = get_simplified_dialogue_timers()
    silence_sec = timers.get("silence_sec", 180)
    chance_pct = timers.get("trigger_chance_pct", 40)
    now_rt = get_unpaused_real_time()

    elapsed = (now_rt - _last_dialogue_real_time) if _last_dialogue_real_time > 0 else 999999.0
    remaining = max(0.0, silence_sec - elapsed) if _last_dialogue_real_time > 0 else 0.0

    groups = find_conversing_groups(require_household=False)
    group_descs = []
    pairs_count = 0
    groups_3plus_count = 0
    for grp in groups:
        names = [get_sim_name(s) for s in grp]
        if len(grp) == 2:
            pairs_count += 1
            group_descs.append(f"Пара: {' + '.join(names)}")
        else:
            groups_3plus_count += 1
            group_descs.append(f"Группа ({len(grp)} симов): {', '.join(names)}")

    candidates = find_potential_candidates()

    return {
        "enabled": get_simplified_dialogue_enabled(),
        "director_conflict": get_director_enabled(),
        "in_flight": _is_dialogue_in_flight,
        "is_paused": is_game_paused(),
        "silence_sec": silence_sec,
        "remaining_sec": int(remaining),
        "chance_pct": chance_pct,
        "balloon": get_simplified_dialogue_balloon(),
        "notification": get_simplified_dialogue_notification(),
        "active_groups_count": len(groups),
        "pairs_count": pairs_count,
        "groups_3plus_count": groups_3plus_count,
        "conversing_groups": group_descs,
        "candidates_count": len(candidates),
    }


def scan_conversing_details() -> Dict[str, Any]:
    """
    Returns detailed scan results on:
    1) Active conversing groups/pairs on the lot.
    2) Potential candidate groups/pairs nearby that could talk.
    3) All instanced Sims detected on the lot.
    """
    active_details = []
    candidate_details = []
    all_sims_summary = []

    try:
        instanced = get_all_instanced_sims()
        for s in instanced:
            inf = getattr(s, "sim_info", s)
            name = get_sim_name(s)
            
            mood = "Нейтральный"
            try:
                if hasattr(s, "get_mood") and s.get_mood():
                    mood = getattr(s.get_mood(), "name", "Нейтральный")
                elif hasattr(inf, "get_mood") and inf.get_mood():
                    mood = getattr(inf.get_mood(), "name", "Нейтральный")
            except Exception:
                pass

            is_sel = is_sim_in_active_household(s)
            avail = is_sim_available(s)
            loc = get_room_and_lot_desc(s)
            all_sims_summary.append({
                "name": name,
                "mood": mood,
                "household": is_sel,
                "available": avail,
                "location": loc
            })

        # 1. Active groups
        groups = find_conversing_groups(require_household=False)
        for grp in groups:
            members_info = []
            for s in grp:
                inf = getattr(s, "sim_info", s)
                full_n = get_sim_name(s)
                fn = getattr(inf, "first_name", "") or full_n
                mood = "Нейтральный"
                try:
                    if hasattr(s, "get_mood") and s.get_mood():
                        mood = getattr(s.get_mood(), "name", "Нейтральный")
                    elif hasattr(inf, "get_mood") and inf.get_mood():
                        mood = getattr(inf.get_mood(), "name", "Нейтральный")
                except Exception:
                    pass
                is_sel = is_sim_in_active_household(s)
                members_info.append({
                    "name": full_n,
                    "first_name": fn,
                    "mood": mood,
                    "selectable": is_sel,
                })
            loc = get_room_and_lot_desc(grp[0]) if grp else "Неизвестно"
            active_details.append({
                "type": "pair" if len(grp) == 2 else "group",
                "count": len(grp),
                "members": members_info,
                "location": loc,
            })

        # 2. Potential candidates
        candidate_details = find_potential_candidates()

    except Exception as e:
        log_exception("Error in scan_conversing_details", e)

    return {
        "active_groups": active_details,
        "potential_candidates": candidate_details,
        "all_sims": all_sims_summary,
    }
