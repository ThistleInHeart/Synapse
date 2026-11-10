"""

Direct Dialogue System for Synapse (v0.9).

Allows the active player Sim to engage in direct in-person AI conversations

with any Sim in the world (Infant to Elder, and Pets).



Features:

1. Pie menu interaction on Sims: «Поговорить (ИИ)...» (Tuning ID: 9834006893958795493)

2. UI text input dialog for player speech

3. Context gathering: actor, target, relationship, memories, and nearby witnesses

4. Bridge communication with /direct_dialogue route

5. Dynamic social animations ([Anim=FRIENDLY/ROMANTIC/FUNNY/MEAN])

6. Live relationship changes ([FR=X] [ROM=Y])

7. In-game notification with speaker portrait and memory recording

"""



import time

import json

import threading

import urllib.request

import re

from typing import Optional, List, Dict, Any, Tuple



from ai_social_pc.logger import log, log_exception

from ai_social_pc.chat_manager import (

    apply_chat_relationship_impact,

    _build_sim_profile_summary,

    _build_compact_sim_profile_summary,

    parse_and_strip_relationship_tags,

    strip_emojis,

    get_current_sim_time,

    get_current_sim_absolute_days,

    BRIDGE_HOST,

    BRIDGE_PORT,

)

from ai_social_pc.memory_manager import (

    add_memory,

    format_memories_for_prompt,

)

from ai_social_pc.ui_chat import (

    show_chat_notification,

    get_recipient_display_name,

    _get_loc_text,

    _get_relationship_description,

    is_sim_an_animal,

)



try:

    from ai_thought_reader.config import (

        get_context_flag,

        get_experimental_flag,

        get_intimate_dialogue_flag,

        get_direct_dialogue_flag,

    )

except ImportError:

    get_context_flag = lambda f: True

    get_experimental_flag = lambda f: True

    get_intimate_dialogue_flag = lambda f: True

    get_direct_dialogue_flag = lambda f: True



try:

    import services

    from ui.ui_dialog_generic import UiDialogTextInputOkCancel

    from ui.ui_dialog import UiDialogOk

    from clock import ClockSpeedMode

    from interactions.context import InteractionContext, QueueInsertStrategy

    from interactions.priority import Priority

    from interactions.aop import AffordanceObjectPair

    from sims4.utils import flexmethod

    from event_testing.results import TestResult

except ImportError:

    services = None

    UiDialogTextInputOkCancel = None

    UiDialogOk = None

    ClockSpeedMode = None

    InteractionContext = None

    QueueInsertStrategy = None

    Priority = None

    AffordanceObjectPair = None

    flexmethod = lambda f: f

    TestResult = None



# S4S Tuning ID for «Поговорить (ИИ)...»

SYNAPSE_DIRECT_DIALOGUE_TUNING_ID = 9834006893958795493



# S4S Tuning ID for «Поговорить во время секса (ИИ)...» (WickedWhims Intimacy)

SYNAPSE_DIRECT_DIALOGUE_WW_TUNING_ID = 14829301847263549182



# Base Game Social Super Interaction (conversation container)

AFFORDANCE_CHAT_SUPER = 13998  # sim_Chat / social_Chat



# Base Game Social Mixer Affordance Tuning IDs (sub-interactions inside conversation)

BASE_MIXER_FRIENDLY = 25881  # mixer_social_Chat_targeted_friendly_alwaysOn

BASE_MIXER_ROMANTIC = 26056  # mixer_social_Flirt_targeted_Romance_alwaysOn

BASE_MIXER_FUNNY = 26458     # mixer_social_TellJoke_targeted_Funny_alwaysOn

BASE_MIXER_MEAN = 26442      # mixer_social_Insult_targeted_Mean_alwaysOn



# Custom tuning IDs from AIThoughts.package:

CUSTOM_MIXER_FRIENDLY = 14565810293186056239  # Synapse:mixer_directDialogue_friendly

CUSTOM_MIXER_ROMANTIC = 14456728865103689683  # Synapse:mixer_directDialogue_romantic

CUSTOM_MIXER_FUNNY = 10803519093810832346     # Synapse:mixer_directDialogue_funny

CUSTOM_MIXER_MEAN = 10335430438877297749      # Synapse:mixer_directDialogue_mean


def make_custom_mixers_sub_interactions_only():
    """
    Deprecated / No-op: Custom social mixers are no longer pushed to the queue.
    """
    pass



def _is_en() -> bool:

    try:

        from ai_social_pc.localization import get_game_language

        return (get_game_language() == "en")

    except Exception:

        return False





ANIM_NAME_EN = {

    "FRIENDLY": "Friendly conversation",

    "ROMANTIC": "Flirt / Romance",

    "FUNNY": "Joke / Laugh",

    "MEAN": "Argument / Outrage",

}



ANIM_NAME_RU = {

    "FRIENDLY": "Дружелюбная беседа",

    "ROMANTIC": "Флирт / Романтика",

    "FUNNY": "Шутка / Смех",

    "MEAN": "Спор / Возмущение",

}



_PENDING_DIALOGUE_SIM_IDS = set()



_PREGATHER_LOCK = threading.Lock()

_PREGATHERED_DIALOGUE_CACHE: Dict[Tuple[int, int], Dict[str, Any]] = {}



# In-memory history of in-person dialogue turns

# Key: (min_sim_id, max_sim_id)

# Value: list of dicts: {"sender": str, "text": str, "sim_time_hours": float}

_DIRECT_DIALOGUE_HISTORY: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}



# Delayed summarization timer handles

# Key: (min_sim_id, max_sim_id)

# Value: threading.Timer object

_SUMMARIZE_TIMERS: Dict[Tuple[int, int], threading.Timer] = {}





def _is_sim_in_active_sex(sim_obj) -> bool:

    """Checks if a Sim is currently involved in active sex (WickedWhims or WooHoo)."""

    if sim_obj is None:

        return False

    sim_info = getattr(sim_obj, "sim_info", None) or (sim_obj if hasattr(sim_obj, "first_name") else None)

    if sim_info is None and isinstance(sim_obj, int):

        if services is not None:

            try:

                sim_info = services.sim_info_manager().get(sim_obj)

            except Exception:

                sim_info = None

    if sim_info is None:

        return False

    try:

        from ai_thought_reader.context import get_sim_active_sex_info

        if get_sim_active_sex_info(sim_info) is not None:

            return True

    except Exception:

        pass

    try:

        from wickedwhims.sex.integral.sex_handlers.active_sex.active_sex_handlers import get_active_sex_instances

        active_instances = get_active_sex_instances()

        if active_instances:

            s_id = getattr(sim_info, "sim_id", None)

            for inst in active_instances:

                if inst and hasattr(inst, "is_sim_id_in_instance") and inst.is_sim_id_in_instance(s_id):

                    return True

    except Exception:

        pass

    return False





def hook_direct_dialogue_affordance(dd_aff, is_ww: bool = False):

    """

    Overrides the _test method on the Direct Dialogue affordance class

    (SYNAPSE_DIRECT_DIALOGUE_TUNING_ID or SYNAPSE_DIRECT_DIALOGUE_WW_TUNING_ID).

    """

    if dd_aff is None:

        return

    if getattr(dd_aff, "_synapse_test_hooked", False):

        return



    orig_test = getattr(dd_aff, "_test", None)



    @flexmethod

    def _custom_direct_dialogue_test(cls, inst, target=None, context=None, **kwargs):

        try:

            actor_sim = getattr(context, "sim", None) if context is not None else None

            is_self = False

            if actor_sim is not None and target is not None:

                if target is actor_sim:

                    is_self = True

                actor_id = getattr(actor_sim, "id", None) or getattr(actor_sim, "sim_id", None)

                target_id = getattr(target, "id", None) or getattr(target, "sim_id", None)

                if actor_id and target_id and actor_id == target_id:

                    is_self = True



            if services is not None and target is not None:

                client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None

                if client is not None:

                    active_sim = getattr(client, "active_sim", None)

                    if active_sim is not None:

                        if target is active_sim:

                            is_self = True

                        act_id = getattr(active_sim, "id", None) or getattr(active_sim, "sim_id", None)

                        tgt_id = getattr(target, "id", None) or getattr(target, "sim_id", None)

                        if act_id and tgt_id and act_id == tgt_id:

                            is_self = True



            # In intimate WW dialogue, clicking self is allowed IF active sim is having sex with a partner!

            if is_self:

                if is_ww and _is_sim_in_active_sex(actor_sim or target):

                    pass  # Allow self-click during sex so player can easily talk to sex partner

                else:

                    return TestResult.NONE if TestResult is not None else False



            # 2. Reject Animals

            if target is not None:

                tgt_info = getattr(target, "sim_info", target)

                if is_sim_an_animal(tgt_info):

                    return TestResult.NONE if TestResult is not None else False



            # 3. Reject non-playable babies / infants

            if target is not None:

                tgt_info = getattr(target, "sim_info", target)

                age_enum = getattr(tgt_info, "age", None)

                age_name = getattr(age_enum, "name", "").upper() if age_enum else ""

                if age_name in ("BABY", "INFANT"):

                    return TestResult.NONE if TestResult is not None else False



            # 4. If this is the WW intimacy affordance, ensure active sex is taking place!

            if is_ww:

                in_sex = _is_sim_in_active_sex(target) or _is_sim_in_active_sex(actor_sim)

                if not in_sex:

                    return TestResult.NONE if TestResult is not None else False



        except Exception as ex_test:

            log_exception("Error in direct dialogue custom _test", ex_test)



        if orig_test is not None:

            try:

                if inst is not None:

                    return orig_test(inst, target=target, context=context, **kwargs)

                return orig_test(target=target, context=context, **kwargs)

            except TypeError:

                try:

                    if inst is not None:

                        return orig_test(inst, target, context, **kwargs)

                    return orig_test(target, context, **kwargs)

                except Exception as ex_orig:

                    log_exception("Error calling orig_test", ex_orig)



        return TestResult.TRUE if TestResult is not None else True



    try:

        dd_aff._test = _custom_direct_dialogue_test

        dd_aff._synapse_test_hooked = True

        log(f"[DIRECT DIALOGUE] Successfully installed _test hook on {dd_aff} (is_ww={is_ww})")

    except Exception as e:

        log_exception(f"Failed to hook _test on {dd_aff}", e)





def _get_current_sim_hours() -> float:

    """Returns current absolute in-game time in hours (days * 24 + hour + minute / 60.0)."""

    try:

        if services is not None:

            time_service = services.time_service()

            now = (getattr(time_service, "sim_now", None) if time_service else None) or (

                services.game_clock_service().now() if hasattr(services, "game_clock_service") and services.game_clock_service() else None

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





def _get_and_prune_dialogue_history(actor_id: int, target_id: int, max_turns: int = 15, max_age_hours: float = 24.0) -> List[Dict[str, Any]]:

    """

    Retrieves recent dialogue turns between two Sims, pruning turns older than 24 sim hours

    and capping at max_turns.

    """

    if not actor_id or not target_id:

        return []



    pair_key = (min(actor_id, target_id), max(actor_id, target_id))

    history = _DIRECT_DIALOGUE_HISTORY.get(pair_key, [])

    cur_hours = _get_current_sim_hours()

    eff_age = 999999.0 if (max_age_hours <= 0.0 or max_age_hours >= 999.0) else max_age_hours



    # Prune expired turns

    valid_turns = [turn for turn in history if (cur_hours - turn.get("sim_time_hours", 0.0)) <= eff_age]

    _DIRECT_DIALOGUE_HISTORY[pair_key] = valid_turns



    # Format up to 15 turns for payload

    result = []

    for turn in valid_turns[-max_turns:]:

        result.append({

            "sender": turn.get("sender", ""),

            "text": turn.get("text", ""),

            "time": turn.get("time", ""),

            "sim_time_hours": turn.get("sim_time_hours", 0.0),

        })

    return result





def _record_dialogue_turn(actor_id: int, target_id: int, sender_name: str, text: str):

    """Appends a turn to the in-person dialogue history with the current sim time in hours and HH:MM format."""

    if not actor_id or not target_id or not text:

        return

    pair_key = (min(actor_id, target_id), max(actor_id, target_id))

    if pair_key not in _DIRECT_DIALOGUE_HISTORY:

        _DIRECT_DIALOGUE_HISTORY[pair_key] = []



    cur_hours = _get_current_sim_hours()

    cur_time_str = ""

    try:

        cur_time_str = get_current_sim_time()

    except Exception:

        pass



    _DIRECT_DIALOGUE_HISTORY[pair_key].append({

        "sender": sender_name,

        "text": text,

        "sim_time_hours": cur_hours,

        "time": cur_time_str,

    })

    # Keep buffer capped at 50 raw entries before pruning

    if len(_DIRECT_DIALOGUE_HISTORY[pair_key]) > 50:

        _DIRECT_DIALOGUE_HISTORY[pair_key] = _DIRECT_DIALOGUE_HISTORY[pair_key][-50:]





def _trigger_immediate_summarization(actor_sim_info, target_sim_info):

    """

    Deprecated: Direct dialogue now operates in 100% single-prompt architecture.

    Episodic memories and actions are extracted inline from [SUM=...] and [DO=...] tags

    during the main dialogue response. No secondary background summarization requests are made.

    """

    return





# Backward-compatibility alias

_schedule_delayed_summarization = _trigger_immediate_summarization





def _get_nearby_witness_info(actor_sim, target_sim, max_distance: float = 15.0) -> List[Tuple[Any, float]]:

    """

    Finds other Sims near the conversation who can hear it.

    Returns sorted list of (sim_info, distance) tuples.

    """

    witnesses = []

    if services is None or actor_sim is None:

        return witnesses

    try:

        actor_pos = getattr(actor_sim, "position", None)

        if actor_pos is None:

            return witnesses



        sim_info_mgr = services.sim_info_manager()

        if sim_info_mgr is None:

            return witnesses



        actor_id = getattr(actor_sim, "id", None)

        target_id = getattr(target_sim, "id", None) if target_sim else None



        for inst in sim_info_mgr.instanced_sims_gen():

            inst_id = getattr(inst, "id", None)

            if inst_id in (actor_id, target_id):

                continue

            inst_pos = getattr(inst, "position", None)

            if inst_pos is not None:

                dist = (inst_pos - actor_pos).magnitude()

                if dist <= max_distance:

                    inf = getattr(inst, "sim_info", inst)

                    if inf is not None:

                        witnesses.append((inf, float(dist)))

    except Exception as ex:

        log_exception("Error getting nearby witnesses", ex)

    witnesses.sort(key=lambda x: x[1])

    return witnesses





def _get_nearby_witness_names(actor_sim, target_sim, max_distance: float = 15.0) -> List[str]:

    """Backward compatibility helper returning list of witness names."""

    infos = _get_nearby_witness_info(actor_sim, target_sim, max_distance=max_distance)

    names = []

    for inf, _ in infos:

        n = get_recipient_display_name(inf)

        if n and n not in names:

            names.append(n)

    return names





def _find_social_super_interaction(actor_sim, target_sim):
    """
    Finds the active running SocialSuperInteraction between actor_sim and target_sim.
    Checks cluster service, main groups on both Sims, and si_state on both Sims.
    """
    if services is None or actor_sim is None or target_sim is None:
        return None

    # 1. Check social_group_cluster_service
    try:
        sg_service = services.social_group_cluster_service() if hasattr(services, "social_group_cluster_service") else None
        if sg_service is not None:
            for s in (actor_sim, target_sim):
                grp = sg_service.get_social_group_for_sim(s)
                if grp is not None and actor_sim in grp and target_sim in grp:
                    if hasattr(grp, "get_si_registered_for_sim"):
                        si = grp.get_si_registered_for_sim(actor_sim) or grp.get_si_registered_for_sim(target_sim)
                        if si is not None and not getattr(si, "is_finishing", False):
                            return si
    except Exception:
        pass

    # 2. Check get_main_group() on both Sims
    for s1, s2 in ((actor_sim, target_sim), (target_sim, actor_sim)):
        if hasattr(s1, "get_main_group"):
            try:
                grp = s1.get_main_group()
                if grp is not None and s2 in grp:
                    if hasattr(grp, "get_si_registered_for_sim"):
                        si = grp.get_si_registered_for_sim(s1) or grp.get_si_registered_for_sim(s2)
                        if si is not None and not getattr(si, "is_finishing", False):
                            return si
            except Exception:
                pass

    # 3. Check si_state on both Sims
    for s1, s2 in ((actor_sim, target_sim), (target_sim, actor_sim)):
        if hasattr(s1, "si_state"):
            try:
                for si in s1.si_state:
                    if getattr(si, "is_social", False) and not getattr(si, "is_finishing", False):
                        si_tgt = getattr(si, "target", None)
                        if si_tgt is s2 or si_tgt is s1:
                            return si
                        grp = getattr(si, "social_group", None)
                        if grp is not None and s2 in grp:
                            return si
            except Exception:
                pass

    return None


def _execute_social_mixer(speaker_sim, listener_sim, mixer_affordance_id: int, super_si) -> bool:
    """
    Deprecated / No-op: Custom social mixers are no longer pushed into the queue,
    preventing AssertionError: has no social group and queue duplications.
    """
    return True





def clean_up_direct_dialogue_conversation(actor_sim, target_sim):

    """

    Cleanly cancels and removes the conversation and queue actions for both Sims.

    Leaves the queue empty so the player doesn't have to manually remove stuck actions.

    """

    if services is None or (actor_sim is None and target_sim is None):

        return



    try:
        try:
            from interactions.interaction_finisher import FinishingType
            cancel_reason = getattr(FinishingType, "NATURAL", getattr(FinishingType, "SOURCE_OVER", getattr(FinishingType, "KILLED", None)))
        except Exception:
            cancel_reason = None

        # 1. Cancel running social interactions cleanly without corrupting the social group
        for sim in (actor_sim, target_sim):
            if sim is None or not hasattr(sim, "si_state"):
                continue
            other = target_sim if sim is actor_sim else actor_sim
            try:
                for si in list(sim.si_state):
                    if getattr(si, "is_social", False):
                        si_tgt = getattr(si, "target", None)
                        si_guid = getattr(si, "guid64", 0)
                        if si_tgt is other or si_tgt is None or si_guid == AFFORDANCE_CHAT_SUPER:
                            try:
                                if cancel_reason is not None:
                                    si.cancel(cancel_reason, "Synapse direct dialogue complete")
                                elif hasattr(si, "cancel_user"):
                                    si.cancel_user("Synapse direct dialogue complete")
                            except Exception:
                                pass
            except Exception:
                pass

        # 2. Cancel queued social interactions in queue
        for sim in (actor_sim, target_sim):
            if sim is None or not hasattr(sim, "queue"):
                continue
            other = target_sim if sim is actor_sim else actor_sim
            try:
                for q_item in list(sim.queue):
                    if getattr(q_item, "is_social", False):
                        q_tgt = getattr(q_item, "target", None)
                        q_guid = getattr(q_item, "guid64", 0)
                        if q_tgt is other or q_tgt is None or q_guid == AFFORDANCE_CHAT_SUPER:
                            try:
                                if cancel_reason is not None:
                                    q_item.cancel(cancel_reason, "Synapse direct dialogue complete")
                                elif hasattr(q_item, "cancel_user"):
                                    q_item.cancel_user("Synapse direct dialogue complete")
                            except Exception:
                                pass
            except Exception:
                pass

        log(f"[DIRECT DIALOGUE] Cleanly dismissed conversation for {actor_sim} and {target_sim}")
    except Exception as ex:
        log_exception("Error in clean_up_direct_dialogue_conversation", ex)





def _is_sim_moving(sim_instance) -> bool:
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


def is_sim_already_nearby(actor_sim, target_sim) -> bool:
    """
    Returns True if the two Sims are already close enough in the same space/room
    that no approach walk is necessary (dialogue opens immediately).
    """
    if actor_sim is None or target_sim is None:
        return False
    try:
        pos_a = getattr(actor_sim, "position", None)
        pos_b = getattr(target_sim, "position", None)
        if pos_a is None or pos_b is None:
            return False

        same_floor = abs(pos_a.y - pos_b.y) < 1.8
        if not same_floor:
            return False

        dist = float((pos_a - pos_b).magnitude())
        if dist > 6.0:
            return False

        # Close proximity safeguard: if within 3.0m on same floor, unconditionally nearby
        if dist <= 3.0:
            return True

        # Check room co-presence up to 5.0m
        from ai_thought_reader.context import get_sim_room_and_outdoor
        room_a, outside_a = get_sim_room_and_outdoor(actor_sim)
        room_b, outside_b = get_sim_room_and_outdoor(target_sim)

        # One inside and one outside -> different spaces, need to walk
        if outside_a != outside_b:
            return False

        # Both inside: same room and within 5.0m
        if not outside_a and not outside_b:
            if room_a != 0 and room_b != 0 and room_a == room_b and dist <= 5.0:
                return True
            return False

        # Both outside: within 4.0m
        if outside_a and outside_b:
            return dist <= 4.0

    except Exception as e:
        log_exception("Error in is_sim_already_nearby", e)

    return False


def _route_to_target_and_open_dialog(actor_sim, target_sim, actor_sim_info, target_sim_info):
    """
    Pushes an approach/chat interaction on actor_sim and monitors their movement.
    Only when the Sims physically meet (<= 3.0m, same floor, and not moving)
    does the text input dialogue window open.
    """
    if services is None or actor_sim is None or target_sim is None:
        show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
        return

    aff_mgr = services.affordance_manager()
    if aff_mgr is None:
        show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
        return

    chat_cls = aff_mgr.get(AFFORDANCE_CHAT_SUPER)
    if chat_cls is None:
        show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
        return

    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    ctx = InteractionContext(
        actor_sim,
        InteractionContext.SOURCE_PIE_MENU,
        Priority.High,
        client=client,
    )
    res = actor_sim.push_super_affordance(chat_cls, target_sim, ctx)
    log(f"[DIRECT DIALOGUE] Initiated approach route (sim_Chat) from {actor_sim} to {target_sim}: {res}")

    if not res:
        log("[DIRECT DIALOGUE] Failed to push approach route affordance. Opening dialogue directly.")
        show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
        return

    start_ts = time.time()
    max_duration = 35.0

    from ai_social_pc.main_thread import run_on_main_thread

    def _monitor_tick():
        zone = services.current_zone() if services is not None else None
        if zone is None or getattr(zone, "is_zone_shutting_down", False):
            return

        # 1. Verify actor_sim and target_sim still exist
        curr_actor = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None
        curr_target = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None
        if curr_actor is None or curr_target is None:
            log("[DIRECT DIALOGUE] Sim instance lost during approach. Aborting.")
            return

        # 2. Check distance, floor and movement
        pos_a = getattr(curr_actor, "position", None)
        pos_b = getattr(curr_target, "position", None)
        elapsed = time.time() - start_ts

        if pos_a is not None and pos_b is not None:
            dist = float((pos_a - pos_b).magnitude())
            same_floor = abs(pos_a.y - pos_b.y) < 1.8
            moving = _is_sim_moving(curr_actor)

            # Give at least 0.8s for the pie interaction / approach to register in the UI and game
            if same_floor and elapsed >= 0.8:
                # Arrived: either stopped walking within 3.0m, or reached very close proximity (<= 1.8m)
                if (dist <= 3.0 and not moving) or dist <= 1.8:
                    log(f"[DIRECT DIALOGUE] Approach finished! Sims met ({dist:.1f}m, same_floor={same_floor}, moving={moving}, elapsed={elapsed:.1f}s). Opening dialogue.")
                    show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
                    return

        # 3. Check if actor cancelled the interaction or route failed
        has_social = False
        if hasattr(curr_actor, "queue"):
            for item in curr_actor.queue:
                aff = getattr(item, "affordance", None)
                aff_guid = getattr(aff, "guid64", 0) if aff else 0
                item_guid = getattr(item, "guid64", 0)
                is_soc = getattr(item, "is_social", False) or getattr(aff, "is_social", False)
                if aff_guid == AFFORDANCE_CHAT_SUPER or item_guid == AFFORDANCE_CHAT_SUPER:
                    has_social = True
                    break
                if is_soc:
                    q_tgt = getattr(item, "target", None)
                    if q_tgt is curr_target:
                        has_social = True
                        break

        if not has_social and hasattr(curr_actor, "si_state"):
            for item in curr_actor.si_state:
                aff = getattr(item, "affordance", None)
                aff_guid = getattr(aff, "guid64", 0) if aff else 0
                item_guid = getattr(item, "guid64", 0)
                is_soc = getattr(item, "is_social", False) or getattr(aff, "is_social", False)
                if aff_guid == AFFORDANCE_CHAT_SUPER or item_guid == AFFORDANCE_CHAT_SUPER:
                    has_social = True
                    break
                if is_soc:
                    si_tgt = getattr(item, "target", None)
                    if si_tgt is curr_target or (hasattr(item, "social_group") and item.social_group and curr_target in item.social_group):
                        has_social = True
                        break

        if not has_social and elapsed > 2.5:
            log("[DIRECT DIALOGUE] Approach interaction cancelled by player or route failed. Aborting dialogue.")
            clean_up_direct_dialogue_conversation(curr_actor, curr_target)
            return

        # 4. Check timeout
        if elapsed > max_duration:
            log("[DIRECT DIALOGUE] Approach timed out after 35 seconds. Cleaning up.", level="WARN")
            clean_up_direct_dialogue_conversation(curr_actor, curr_target)
            is_en = _is_en()
            t_name = get_recipient_display_name(target_sim_info)
            show_chat_notification(
                title="Dialogue Cancelled" if is_en else "Диалог отменён",
                text=f"Could not reach {t_name}." if is_en else f"Не удалось подойти к {t_name}.",
                sim_info=actor_sim_info,
                is_error=True,
            )
            return

        # Continue polling every 0.4 seconds
        t = threading.Timer(0.4, lambda: run_on_main_thread(_monitor_tick))
        t.daemon = True
        t.start()

    # Launch first tick after 0.4s
    t = threading.Timer(0.4, lambda: run_on_main_thread(_monitor_tick))
    t.daemon = True
    t.start()


def play_direct_dialogue_animation(actor_sim, target_sim, anim_category: str = "FRIENDLY"):
    """
    Ensures both Sims are engaged in a natural conversation (sim_Chat).
    EA's native conversational engine autonomously drives lifelike talking gestures,
    lipsync, head turns, and eye contact without pushing unstable social mixers into the queue.
    """
    if services is None or actor_sim is None or target_sim is None:
        return

    try:
        actor_info = getattr(actor_sim, "sim_info", None)
        target_info = getattr(target_sim, "sim_info", None)

        is_pet = bool(getattr(target_info, "is_pet", False) or getattr(actor_info, "is_pet", False))
        if is_pet:
            return

        is_baby_or_infant = False
        for s_info in (actor_info, target_info):
            if s_info is not None:
                age_val = getattr(s_info, "age", None)
                age_str = str(age_val).upper() if age_val else ""
                if any(k in age_str for k in ("BABY", "INFANT", "TODDLER")):
                    is_baby_or_infant = True
                    break
        if is_baby_or_infant:
            return

        # 1. Look for existing conversation
        super_si = _find_social_super_interaction(actor_sim, target_sim)
        if super_si is not None and not getattr(super_si, "is_finishing", False):
            log(f"[CONVERSATION] Sims are already in conversation ({super_si}). Continuing natural chat.")
            return

        # 2. If no conversation exists yet, start standard sim_Chat!
        aff_mgr = services.affordance_manager()
        if aff_mgr is not None:
            chat_cls = aff_mgr.get(AFFORDANCE_CHAT_SUPER)
            if chat_cls is not None:
                client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
                ctx = InteractionContext(
                    actor_sim,
                    InteractionContext.SOURCE_SCRIPT,
                    Priority.High,
                    client=client,
                )
                res = actor_sim.push_super_affordance(chat_cls, target_sim, ctx)
                log(f"[CONVERSATION] Initiated standard sim_Chat between {actor_sim} and {target_sim}: {res}")

    except Exception as e:
        log_exception(f"Failed to ensure direct dialogue conversation ({anim_category})", e)





def start_direct_dialogue(target_sim_id: Any, actor_sim_info: Any = None, is_ww_sex: bool = False):

    """

    Main entry point when player clicks «Поговорить (ИИ)...» or «Поговорить во время секса (ИИ)» on a Sim.

    """

    if services is None:

        log("[DIRECT DIALOGUE] services is None", level="ERROR")

        return



    sim_info_mgr = services.sim_info_manager()

    if sim_info_mgr is None:

        return



    if actor_sim_info is None:

        actor_sim_info = services.active_sim_info()



    if actor_sim_info is None:

        log("[DIRECT DIALOGUE] active_sim_info is None", level="ERROR")

        return



    actor_id = getattr(actor_sim_info, "sim_id", 0)



    # 1. Check active sex for actor

    actor_sex_info = None

    try:

        from ai_thought_reader.context import get_sim_active_sex_info

        actor_sex_info = get_sim_active_sex_info(actor_sim_info)

        if actor_sex_info is not None:

            is_ww_sex = True

    except Exception:

        actor_sex_info = None



    target_sim_info = None

    if target_sim_id is not None:

        try:

            t_id = int(target_sim_id)

            target_sim_info = sim_info_mgr.get(t_id)

        except (ValueError, TypeError):

            if hasattr(target_sim_id, "sim_info"):

                target_sim_info = target_sim_id.sim_info

            else:

                target_sim_info = target_sim_id



    # Fallback: if target was not resolved or player clicked self during sex, auto-target intimate partner!

    if target_sim_info is None or (getattr(target_sim_info, "sim_id", 0) == actor_id):

        if is_ww_sex and actor_sex_info:

            actor_ids = actor_sex_info.get("actor_sim_ids", [])

            partner_ids = [sid for sid in actor_ids if sid != actor_id]

            if partner_ids:

                target_sim_info = sim_info_mgr.get(partner_ids[0])

                log(f"[DIRECT DIALOGUE] Resolved self/missing target to intimate partner {partner_ids[0]}")



    if target_sim_info is None:

        log(f"[DIRECT DIALOGUE] Could not resolve target Sim from {target_sim_id}", level="WARN")

        return



    tgt_id = getattr(target_sim_info, "sim_id", 0)



    # Check active sex for target as well

    if not is_ww_sex:

        try:

            from ai_thought_reader.context import get_sim_active_sex_info

            target_sex_info = get_sim_active_sex_info(target_sim_info)

            if target_sex_info is not None:

                is_ww_sex = True

        except Exception:

            pass



    if actor_id == tgt_id:

        log("[DIRECT DIALOGUE] Actor cannot speak to self directly")

        is_en = _is_en()

        show_chat_notification(

            title="Dialogue Unavailable" if is_en else "Диалог невозможен",

            text="You cannot speak to yourself!" if is_en else "Вы не можете разговаривать сами с собой!",

            sim_info=actor_sim_info,

            is_error=True,

        )

        return



    if is_sim_an_animal(target_sim_info):

        log(f"[DIRECT DIALOGUE] Target Sim {tgt_id} is an animal/pet, direct dialogue not allowed")

        target_name = get_recipient_display_name(target_sim_info)

        is_en = _is_en()

        show_chat_notification(

            title="Dialogue Unavailable" if is_en else "Диалог невозможен",

            text=f"{target_name} is a pet / animal. Direct AI conversation is only available with human Sims." if is_en else f"{target_name} — питомец / животное. Общение через ИИ доступно только с персонажами-людьми.",

            sim_info=actor_sim_info,

            is_error=True,

        )

        return



    age_enum = getattr(target_sim_info, "age", None)

    age_name = getattr(age_enum, "name", "").upper() if age_enum else ""

    if age_name in ("BABY", "INFANT"):

        target_name = get_recipient_display_name(target_sim_info)

        is_en = _is_en()

        show_chat_notification(

            title="Dialogue Unavailable" if is_en else "Диалог невозможен",

            text=f"{target_name} is too young for a conversation." if is_en else f"{target_name} слишком мал(а) для осознанного разговора.",

            sim_info=actor_sim_info,

            is_error=True,

        )

        return



    if tgt_id in _PENDING_DIALOGUE_SIM_IDS:

        target_name = get_recipient_display_name(target_sim_info)

        is_en = _is_en()

        show_chat_notification(

            title="Dialogue in progress..." if is_en else "Диалог уже идёт...",

            text=f"{target_name} is currently formulating a response. Please wait!" if is_en else f"{target_name} сейчас обдумывает ответ. Пожалуйста, подождите!",

            sim_info=actor_sim_info,

            is_error=False,

        )

        return



    if is_ww_sex:

        show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=True)

    else:

        approach_first = True

        try:

            from ai_thought_reader.config import get_experimental_flag

            approach_first = bool(get_experimental_flag("direct_dialogue_approach_first"))

        except Exception:

            approach_first = True



        if approach_first:

            actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None
            target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None
            if actor_sim is not None and target_sim is not None:
                if is_sim_already_nearby(actor_sim, target_sim):
                    log("[DIRECT DIALOGUE] Sims are already nearby in the same room/area. Opening dialogue immediately without approach route.")
                    show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)
                else:
                    _route_to_target_and_open_dialog(actor_sim, target_sim, actor_sim_info, target_sim_info)
            else:
                show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)

        else:

            show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, is_ww_sex=False)





def show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, default_text: str = "", is_ww_sex: bool = False):

    """

    Opens UiDialogTextInputOkCancel for the player to type their spoken phrase.

    """

    if UiDialogTextInputOkCancel is None:

        log("[DIRECT DIALOGUE] UiDialogTextInputOkCancel is not available", level="ERROR")

        return



    actor_id = getattr(actor_sim_info, "sim_id", 0)

    tgt_id = getattr(target_sim_info, "sim_id", 0)

    is_en = _is_en()

    target_name = get_recipient_display_name(target_sim_info)

    actor_name = get_recipient_display_name(actor_sim_info)

    rel_desc = _get_relationship_description(actor_sim_info, target_sim_info)



    mood_str = "Fine" if is_en else "Обычное"

    try:

        mood_curr = target_sim_info.get_current_mood()

        if mood_curr is not None:

            mood_str = getattr(mood_curr, "mood_name", getattr(mood_curr, "__name__", str(mood_curr)))

    except Exception:

        pass



    if is_en:

        try:

            from ai_thought_reader.context_en import translate_relationship_en, translate_mood_en

            rel_desc = translate_relationship_en(rel_desc)

            mood_str = translate_mood_en(mood_str)

        except Exception:

            pass



    # Fetch active sex info if intimate dialogue

    active_sex = None

    if is_ww_sex:

        try:

            from ai_thought_reader.context import get_sim_active_sex_info

            active_sex = get_sim_active_sex_info(target_sim_info) or get_sim_active_sex_info(actor_sim_info)

        except Exception:

            active_sex = None



    if is_ww_sex:

        title = f"Intimate Talk with {target_name}" if is_en else f"Интимный разговор с {target_name}"

        pose_line = ""

        if active_sex and active_sex.get("pose"):

            raw_pose = active_sex.get("pose")

            if is_en:

                try:

                    from ai_thought_reader.context_en import translate_activity_en

                    raw_pose = translate_activity_en(raw_pose)

                except Exception:

                    pass

            pose_lbl = "Process / Pose" if is_en else "Процесс / Поза"

            pose_line = f"<br>{pose_lbl}: <i>{raw_pose}</i>"



        if is_en:

            prompt_body = (

                f"<p align=\"center\"><b>Intimate conversation with {target_name}</b></p>\n"

                f"<p align=\"left\">Relationship: <b>{rel_desc}</b><br>"

                f"Mood: <i>{mood_str}</i>{pose_line}</p>\n"

                f"<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>\n"

                f"<p align=\"left\"><font color=\"#555555\">Type what {actor_name} will whisper / say in the heat of passion:<br>"

                f"(OK — Speak  |  Cancel — Close)</font></p>"

            )

        else:

            prompt_body = (

                f"<p align=\"center\"><b>Интимное общение с {target_name}</b></p>\n"

                f"<p align=\"left\">Отношения: <b>{rel_desc}</b><br>"

                f"Настроение собеседника: <i>{mood_str}</i>{pose_line}</p>\n"

                f"<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>\n"

                f"<p align=\"left\"><font color=\"#555555\">Введите фразу или шепот {actor_name} в момент близости:<br>"

                f"(ОК — сказать  |  Отмена — закрыть)</font></p>"

            )

    else:

        title = f"Speak with {target_name}" if is_en else f"Сказать {target_name}"

        if is_en:

            prompt_body = (

                f"<p align=\"center\"><b>Live conversation with {target_name}</b></p>\n"

                f"<p align=\"left\">Relationship: <b>{rel_desc}</b><br>"

                f"Mood: <i>{mood_str}</i></p>\n"

                f"<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>\n"

                f"<p align=\"left\"><font color=\"#555555\">Type what {actor_name} will say out loud:<br>"

                f"(OK — Speak  |  Cancel — Close)</font></p>"

            )

        else:

            prompt_body = (

                f"<p align=\"center\"><b>Живой разговор с {target_name}</b></p>\n"

                f"<p align=\"left\">Отношения: <b>{rel_desc}</b><br>"

                f"Настроение собеседника: <i>{mood_str}</i></p>\n"

                f"<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>\n"

                f"<p align=\"left\"><font color=\"#555555\">Введите фразу, которую {actor_name} скажет вслух:<br>"

                f"(ОК — сказать  |  Отмена — закрыть)</font></p>"

            )



    try:

        loc_title = _get_loc_text(title)

        loc_text = _get_loc_text(prompt_body)

        loc_init = _get_loc_text(default_text or "")



        factory = UiDialogTextInputOkCancel.TunableFactory(

            text_inputs=("direct_dialogue_input",)

        )

        dialog = factory.default(

            actor_sim_info,

            text=lambda *_: loc_text,

            title=lambda *_: loc_title,

        )



        if hasattr(dialog, "text_inputs"):

            tuning = getattr(dialog.text_inputs, "direct_dialogue_input", None)

            if tuning is not None:

                if hasattr(tuning, "length_restriction") and hasattr(tuning.length_restriction, "max_length"):

                    tuning.length_restriction.max_length = 500

                if hasattr(tuning, "initial_value"):

                    tuning.initial_value = lambda *_: loc_init



        def _on_response(dlg):

            try:

                actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None

                target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None



                if getattr(dlg, "accepted", False):

                    text = ""

                    if hasattr(dlg, "get_input_text"):

                        text = dlg.get_input_text() or ""

                    elif hasattr(dlg, "text_input_responses"):

                        resp_dict = getattr(dlg, "text_input_responses", {})

                        text = resp_dict.get("direct_dialogue_input", "") or ""



                    clean_text = str(text).strip()

                    if clean_text:

                        _dispatch_direct_dialogue(actor_sim_info, target_sim_info, clean_text, is_ww_sex=is_ww_sex)

                    else:

                        log("[DIRECT DIALOGUE] Empty text submitted, canceling")

                        clean_up_direct_dialogue_conversation(actor_sim, target_sim)

                else:

                    log("[DIRECT DIALOGUE] Dialog cancelled by user, closing input dialog")

                    _clear_pregathered_context(actor_id, tgt_id)

                    clean_up_direct_dialogue_conversation(actor_sim, target_sim)

            except Exception as e:

                log_exception("Error in direct dialogue dialog response", e)



        try:

            _start_pregathering_direct_dialogue_context(actor_sim_info, target_sim_info, is_ww_sex=is_ww_sex)

        except Exception as ex_pg:

            log_exception("Failed to start background context pregathering", ex_pg)

        dialog.show_dialog(on_response=_on_response)

        log(f"[DIRECT DIALOGUE] Opened input dialog for dialogue with {target_name} (is_ww_sex={is_ww_sex})")



    except Exception as e:

        log_exception("Failed to render direct dialogue input dialog", e)





def _pause_game_clock() -> Optional[int]:

    """Pauses the game clock and returns the previous speed mode."""

    if services is None:

        return None

    try:

        gcs = services.game_clock_service()

        if gcs is not None and hasattr(gcs, "set_clock_speed"):

            prev = getattr(gcs, "clock_speed", None)

            if callable(prev):

                prev = prev()

            pause_val = getattr(ClockSpeedMode, "PAUSED", 0) if ClockSpeedMode is not None else 0

            gcs.set_clock_speed(pause_val)

            log(f"[DIRECT DIALOGUE] Game clock paused (prev_speed={prev})")

            return prev

    except Exception as e:

        log_exception("Failed to pause game clock", e)

    return None





def _restore_game_clock(prev_speed: Optional[int]):

    """Restores the game clock speed after dialogue response."""

    if services is None:

        return

    try:

        gcs = services.game_clock_service()

        if gcs is not None and hasattr(gcs, "set_clock_speed"):

            normal_val = getattr(ClockSpeedMode, "NORMAL", 1) if ClockSpeedMode is not None else 1

            target = prev_speed if prev_speed is not None else normal_val

            gcs.set_clock_speed(target)

            log(f"[DIRECT DIALOGUE] Game clock restored to {target}")

    except Exception as e:

        log_exception("Failed to restore game clock", e)





def _show_waiting_dialog(actor_sim_info, target_name: str, spoken_text: str, is_ww_sex: bool = False) -> Optional[Any]:

    """Displays a modal waiting dialog informing player that reply is generating."""

    if UiDialogOk is None:

        return None

    try:

        is_en = _is_en()

        if is_ww_sex:

            title = f"Intimate conversation with {target_name}" if is_en else f"Интимный разговор с {target_name}"

            if is_en:

                text = (

                    f"You whispered:\n«{spoken_text}»\n\n"

                    f"<font color=\"#E67E22\"><b>Please wait...</b></font>\n"

                    f"{target_name} is reacting in the intimate scene. Game is temporarily paused.\n\n"

                    f"<font color=\"#7F8C8D\">(Window will close automatically when reply arrives)</font>"

                )

            else:

                text = (

                    f"Вы сказали:\n«{spoken_text}»\n\n"

                    f"<font color=\"#E67E22\"><b>Пожалуйста, подождите...</b></font>\n"

                    f"Собеседник реагирует в процессе близости. Игра временно на паузе.\n\n"

                    f"<font color=\"#7F8C8D\">(Окно закроется автоматически при получении ответа)</font>"

                )

        else:

            title = f"Conversation with {target_name}" if is_en else f"Разговор с {target_name}"

            if is_en:

                text = (

                    f"You said:\n«{spoken_text}»\n\n"

                    f"<font color=\"#E67E22\"><b>Please wait...</b></font>\n"

                    f"{target_name} is formulating a response. Game is temporarily paused.\n\n"

                    f"<font color=\"#7F8C8D\">(Window will close automatically when reply arrives)</font>"

                )

            else:

                text = (

                    f"Вы сказали:\n«{spoken_text}»\n\n"

                    f"<font color=\"#E67E22\"><b>Пожалуйста, подождите...</b></font>\n"

                    f"Собеседник обдумывает ответ. Игра временно на паузе.\n\n"

                    f"<font color=\"#7F8C8D\">(Окно закроется автоматически при получении ответа)</font>"

                )

        loc_title = _get_loc_text(title)

        loc_text = _get_loc_text(text)



        factory = UiDialogOk.TunableFactory()

        dialog = factory.default(

            actor_sim_info,

            text=lambda *_: loc_text,

            title=lambda *_: loc_title,

        )

        try:

            dialog.responses = ()

        except Exception:

            pass



        dialog.show_dialog()

        log(f"[DIRECT DIALOGUE] Opened waiting modal dialog (ID {getattr(dialog, 'dialog_id', None)})")

        return dialog

    except Exception as e:

        log_exception("Failed to show direct dialogue waiting dialog", e)

        return None





def _close_waiting_dialog(dialog):

    """Closes the waiting dialog using ui_dialog_service."""

    if dialog is None or services is None:

        return

    try:

        uds = services.ui_dialog_service()

        d_id = getattr(dialog, "dialog_id", None)

        if uds is not None and d_id is not None:

            is_active = True

            if hasattr(uds, "_active_dialogs"):

                is_active = (d_id in uds._active_dialogs)

            if is_active:

                log(f"[DIRECT DIALOGUE] Closing waiting dialog ID {d_id}")

                uds.dialog_cancel(d_id)

    except Exception as e:

        log_exception("Failed to close waiting dialog", e)





def _dispatch_direct_dialogue(actor_sim_info, target_sim_info, spoken_text: str, is_ww_sex: bool = False):

    """

    Spawns a background thread to call the Synapse AI Bridge at /direct_dialogue.

    Pauses game and opens waiting modal dialog to prevent Sims from walking away.

    """

    tgt_id = getattr(target_sim_info, "sim_id", 0)

    _PENDING_DIALOGUE_SIM_IDS.add(tgt_id)



    try:

        from ai_social_pc.autonomous_director import record_player_action

        record_player_action(actor_sim_info, target_sim_info)

    except Exception:

        pass



    target_name = get_recipient_display_name(target_sim_info)

    actor_name = get_recipient_display_name(actor_sim_info)



    # 1. Check experimental setting for game pause & waiting modal

    use_pause_and_modal = True

    try:

        from ai_thought_reader.config import get_experimental_flag, get_all_multisim_rules

        use_pause_and_modal = get_experimental_flag("direct_dialogue_pause")

    except Exception:

        use_pause_and_modal = True



    prev_speed = _pause_game_clock() if use_pause_and_modal else None

    waiting_dialog = _show_waiting_dialog(actor_sim_info, target_name, spoken_text, is_ww_sex=is_ww_sex) if use_pause_and_modal else None



    # 2. Notification backup

    is_en_bk = _is_en()

    if is_ww_sex:

        wait_title = f"Intimate conversation with {target_name}" if is_en_bk else f"Интимный разговор с {target_name}"

        wait_text = (

            f"You whispered: «{spoken_text}»\n\n{target_name} is reacting in the intimate scene..."

            if is_en_bk else

            f"Вы сказали: «{spoken_text}»\n\n{target_name} реагирует в процессе близости..."

        )

    else:

        wait_title = f"Conversation with {target_name}" if is_en_bk else f"Разговор с {target_name}"

        wait_text = (

            f"You said: «{spoken_text}»\n\n{target_name} is thinking..."

            if is_en_bk else

            f"Вы сказали: «{spoken_text}»\n\n{target_name} обдумывает ответ..."

        )

    show_chat_notification(

        title=wait_title,

        text=wait_text,

        sim_info=actor_sim_info,

        is_error=False,

    )



    t = threading.Thread(

        target=_worker_direct_dialogue,

        args=(actor_sim_info, target_sim_info, spoken_text, waiting_dialog, prev_speed, is_ww_sex),

        name=f"SynapseDirectDialogue_{tgt_id}",

        daemon=True,

    )

    t.start()





def _collect_direct_dialogue_context(actor_sim_info, target_sim_info, is_ww_sex: bool = False) -> dict:

    """Collects all heavy contextual information, profiles, witnesses, and state."""

    tgt_id = getattr(target_sim_info, "sim_id", 0)

    actor_id = getattr(actor_sim_info, "sim_id", 0)

    target_name = get_recipient_display_name(target_sim_info)

    actor_name = get_recipient_display_name(actor_sim_info)



    actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None

    target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None



    is_en = _is_en()

    actor_info_summary = _build_sim_profile_summary(actor_sim_info, is_direct_dialogue=True, other_sim_info=target_sim_info)

    target_info_summary = _build_sim_profile_summary(target_sim_info, is_direct_dialogue=True, other_sim_info=actor_sim_info)



    rel_desc = _get_relationship_description(actor_sim_info, target_sim_info)

    if is_en:

        try:

            from ai_thought_reader.context_en import translate_relationship_en

            rel_desc = translate_relationship_en(rel_desc)

        except Exception:

            pass



    memories = ""



    multisim_join_enabled = True

    try:

        from ai_thought_reader.config import get_experimental_flag, get_all_multisim_rules

        multisim_join_enabled = bool(get_experimental_flag("direct_dialogue_multisim_join"))

    except Exception:

        multisim_join_enabled = True



    # Detect Group Conversation (3+ Sims talking together or in joint sex) or Nearby Bystanders

    is_group_conv = False

    other_sim_infos = []



    if multisim_join_enabled and is_ww_sex:

        try:

            from ai_thought_reader.context import get_sim_active_sex_info

            target_sex_info = get_sim_active_sex_info(target_sim_info)

            actor_sex_info = get_sim_active_sex_info(actor_sim_info)

            raw_sex_info = target_sex_info or actor_sex_info or {}

            if raw_sex_info:

                actor_ids = raw_sex_info.get("actor_sim_ids", [])

                sim_mgr = services.sim_info_manager() if services else None

                if sim_mgr:

                    for s_id in actor_ids:

                        if s_id not in (actor_id, tgt_id):

                            p_inf = sim_mgr.get(s_id)

                            if p_inf and p_inf not in other_sim_infos:

                                other_sim_infos.append(p_inf)

                if len(actor_ids) >= 3 or (len(actor_ids) >= 2 and (actor_id not in actor_ids or tgt_id not in actor_ids)):

                    is_group_conv = True

        except Exception as ex_ww_grp:

            log_exception("Error detecting WW sex participants", ex_ww_grp)

    elif multisim_join_enabled:

        try:

            for s_check in (actor_sim, target_sim):

                if s_check is None:

                    continue

                for grp_attr in ["get_main_social_group", "get_main_group"]:

                    if hasattr(s_check, grp_attr):

                        sg = getattr(s_check, grp_attr)()

                        if sg is not None:

                            sg_members = []

                            try:

                                for member in sg:

                                    m_inf = getattr(member, "sim_info", member)

                                    if m_inf is not None and m_inf not in sg_members:

                                        sg_members.append(m_inf)

                            except Exception:

                                pass

                            if not sg_members and hasattr(sg, "sims_gen"):

                                for member in sg.sims_gen():

                                    m_inf = getattr(member, "sim_info", member)

                                    if m_inf is not None and m_inf not in sg_members:

                                        sg_members.append(m_inf)



                            if len(sg_members) >= 3:

                                is_group_conv = True

                                for m in sg_members:

                                    m_id = getattr(m, "sim_id", 0)

                                    if m_id not in (actor_id, tgt_id) and m not in other_sim_infos:

                                        other_sim_infos.append(m)

                                break

                if is_group_conv:

                    break



            if not is_group_conv:

                try:

                    from ai_thought_reader.context import get_social_dialog_info

                    for s_inf in (actor_sim_info, target_sim_info):

                        s_info_data = get_social_dialog_info(s_inf)

                        if s_info_data and s_info_data.get("is_group"):

                            is_group_conv = True

                            sim_mgr = services.sim_info_manager() if services else None

                            if sim_mgr:

                                for t_entry in s_info_data.get("targets", []):

                                    t_name = t_entry.get("name", "")

                                    for inst in sim_mgr.instanced_sims_gen():

                                        inf_c = getattr(inst, "sim_info", inst)

                                        if inf_c is not None:

                                            fn = get_recipient_display_name(inf_c)

                                            if fn == t_name and getattr(inf_c, "sim_id", 0) not in (actor_id, tgt_id):

                                                if inf_c not in other_sim_infos:

                                                    other_sim_infos.append(inf_c)

                            break

                except Exception as ex_ctx_s:

                    log_exception("Error inspecting get_social_dialog_info in direct dialogue", ex_ctx_s)

        except Exception as ex_sg:

            log_exception("Error detecting social group members in direct dialogue", ex_sg)



    # 2. Collect witnesses and separate group members vs nearby bystanders

    witness_tuple_list = _get_nearby_witness_info(actor_sim, target_sim, max_distance=15.0) if multisim_join_enabled else []

    other_sim_ids_set = {getattr(inf, "sim_id", getattr(inf, "id", None)) for inf in other_sim_infos}

    if is_ww_sex and 'raw_sex_info' in locals() and raw_sex_info:

        other_sim_ids_set.update(raw_sex_info.get("actor_sim_ids", []))

    witness_names = [

        get_recipient_display_name(inf)

        for inf, _ in witness_tuple_list

        if get_recipient_display_name(inf) and inf not in other_sim_infos and getattr(inf, "sim_id", getattr(inf, "id", None)) not in other_sim_ids_set

    ]

    witnesses_str = ", ".join(witness_names) if witness_names else ""



    bystander_sim_infos = []

    try:

        for inf, dist in witness_tuple_list:

            if dist <= 9.0 and inf not in other_sim_infos:

                inst = inf.get_sim_instance() if hasattr(inf, "get_sim_instance") else None

                if inst is not None:

                    try:

                        if getattr(inf, "is_dead", False) or getattr(inst, "is_dying", False):

                            continue

                        from ai_thought_reader.context import get_current_activity

                        act_l = (get_current_activity(inf) or "").lower()

                        if any(w in act_l for w in ["сон", "спит", "дремлет", "sleeping", "nap"]):

                            continue

                        if any(w in act_l for w in ["душ", "ванна", "туалет", "shower", "bath", "toilet"]):

                            continue

                    except Exception:

                        pass

                bystander_sim_infos.append(inf)

                if len(bystander_sim_infos) >= 2:

                    break

    except Exception as ex_byst:

        log_exception("Error collecting nearby bystanders in direct dialogue", ex_byst)



    # Build payload for group members (all Sims in the group chat)

    group_members_payload = []

    for g_inf in other_sim_infos:

        g_id = getattr(g_inf, "sim_id", 0)

        g_name = get_recipient_display_name(g_inf)

        g_prof = _build_sim_profile_summary(g_inf, is_direct_dialogue=True, other_sim_info=actor_sim_info)

        g_rel = _get_relationship_description(actor_sim_info, g_inf)

        if is_en:

            try:

                from ai_thought_reader.context_en import translate_relationship_en

                g_rel = translate_relationship_en(g_rel)

            except Exception:

                pass

        group_members_payload.append({

            "sim_id": g_id,

            "name": g_name,

            "profile": g_prof,

            "relationship_with_actor": g_rel,

        })



    # Build payload for bystanders (Sims nearby, not in group) - FAST COMPACT PROFILE

    bystanders_payload = []

    for b_inf in bystander_sim_infos:

        b_id = getattr(b_inf, "sim_id", 0)

        b_name = get_recipient_display_name(b_inf)

        b_prof = _build_compact_sim_profile_summary(b_inf, is_en=is_en, other_sim_info=actor_sim_info)

        b_rel = _get_relationship_description(actor_sim_info, b_inf)

        if is_en:

            try:

                from ai_thought_reader.context_en import translate_relationship_en

                b_rel = translate_relationship_en(b_rel)

            except Exception:

                pass

        bystanders_payload.append({

            "sim_id": b_id,

            "name": b_name,

            "profile": b_prof,

            "relationship_with_actor": b_rel,

        })



    other_sims_payload = group_members_payload if is_group_conv else bystanders_payload



    target_age = str(getattr(target_sim_info, "age", "ADULT")).upper()

    is_pet = bool(getattr(target_sim_info, "is_pet", False))



    if get_context_flag("recent_dialogs"):

        try:

            from ai_thought_reader.config import get_dialogue_memory_hours

            hist_hours = float(get_dialogue_memory_hours())

        except Exception:

            hist_hours = 24.0

        history_msgs = _get_and_prune_dialogue_history(actor_id, tgt_id, max_turns=15, max_age_hours=hist_hours)

    else:

        history_msgs = []



    cur_sim_time = ""

    cur_season = ""

    cur_weather = ""

    cur_holiday = ""

    cur_world = ""

    actor_ev = None

    target_ev = None

    lot_ev = None

    try:

        from ai_thought_reader.context import get_world_time_info, get_season_info, get_weather_info, get_holiday_info, get_current_world_name, get_active_social_event_info

        cur_sim_time = get_world_time_info() or get_current_sim_time()

        cur_season = get_season_info()

        cur_weather = get_weather_info()

        cur_holiday = get_holiday_info(actor_sim_info)

        cur_world = get_current_world_name() or ""

        actor_ev = get_active_social_event_info(actor_sim_info, is_en=is_en)

        target_ev = get_active_social_event_info(target_sim_info, is_en=is_en)

        lot_ev = actor_ev or target_ev or get_active_social_event_info(None, is_en=is_en)

    except Exception:

        try:

            cur_sim_time = get_current_sim_time()

        except Exception:

            pass



    if is_en:

        try:

            from ai_thought_reader.context_en import translate_time_en, SEASONS_MAP_EN, WEATHER_MAP_EN, translate_phrase, translate_holiday_en, WORLD_NAMES_MAP_EN

            cur_sim_time = translate_time_en(cur_sim_time)

            cur_season = SEASONS_MAP_EN.get(cur_season, cur_season)

            cur_weather = translate_phrase(cur_weather, WEATHER_MAP_EN)

            if cur_holiday:

                cur_holiday = translate_holiday_en(cur_holiday)

            if cur_world:

                cur_world = WORLD_NAMES_MAP_EN.get(cur_world, cur_world)

        except Exception:

            pass



    sex_info = None

    scene_participants = []

    is_group_sex_dialogue = False

    if is_ww_sex:

        try:

            from ai_thought_reader.context import get_sim_active_sex_info

            target_sex_info = get_sim_active_sex_info(target_sim_info)

            actor_sex_info = get_sim_active_sex_info(actor_sim_info)

            raw_sex_info = target_sex_info or actor_sex_info or {}

            if raw_sex_info:

                actor_ids = raw_sex_info.get("actor_sim_ids", [])

                if actor_id in actor_ids and tgt_id in actor_ids:

                    scene_role = "partners"

                elif tgt_id in actor_ids:

                    scene_role = "bystander_to_participant"

                elif actor_id in actor_ids:

                    scene_role = "participant_to_bystander"

                else:

                    scene_role = "partners"



                sim_mgr = services.sim_info_manager() if services else None

                if sim_mgr:

                    for s_id in actor_ids:

                        if s_id not in (actor_id, tgt_id):

                            p_inf = sim_mgr.get(s_id)

                            if p_inf:

                                p_fn = f"{getattr(p_inf, 'first_name', '')} {getattr(p_inf, 'last_name', '')}".strip()

                                # Reuse profile if already built in group_members_payload

                                p_prof = None

                                for gm in group_members_payload:

                                    if gm.get("sim_id") == s_id:

                                        p_prof = gm.get("profile")

                                        break

                                if not p_prof:

                                    p_prof = _build_sim_profile_summary(p_inf, is_direct_dialogue=True, other_sim_info=actor_sim_info)

                                p_rel = _get_relationship_description(actor_sim_info, p_inf)

                                scene_participants.append({

                                    "name": p_fn,

                                    "sim_id": s_id,

                                    "role": "participant",

                                    "info": p_prof,

                                    "relationship": p_rel,

                                })



                is_group_sex_dialogue = (len(actor_ids) >= 3 or (len(actor_ids) >= 2 and scene_role != "partners"))



                sex_info = {

                    "action": raw_sex_info.get("action", ""),

                    "partners": raw_sex_info.get("partners", ""),

                    "pose": raw_sex_info.get("pose", ""),

                    "location_and_privacy": raw_sex_info.get("location_and_privacy", ""),

                    "group_type": raw_sex_info.get("group_type", ""),

                    "scene_role": scene_role,

                    "num_partners": raw_sex_info.get("num_partners", 1),

                }

        except Exception as ex_sex:

            log_exception("Error compiling sex_info for direct dialogue payload", ex_sex)



    biz_info = None

    try:

        from ai_thought_reader.business_context import get_business_info_dict

        biz_info = get_business_info_dict(actor_sim_info, is_en=is_en)

    except Exception:

        biz_info = None



    event_info = None

    if lot_ev:

        ev_name_key = "event_name_en" if is_en else "event_name"

        role_key = "role_en" if is_en else "role"

        event_info = {

            "event_name": lot_ev.get(ev_name_key) or lot_ev.get("event_name", ""),

            "actor_role": actor_ev.get(role_key) if actor_ev else None,

            "actor_is_participant": actor_ev.get("is_participant", False) if actor_ev else False,

            "target_role": target_ev.get(role_key) if target_ev else None,

            "target_is_participant": target_ev.get("is_participant", False) if target_ev else False,

        }



    try:

        if not get_context_flag("nearby"):

            witnesses_str = ""

        if not get_context_flag("world_time"):

            cur_sim_time = ""

            cur_holiday = ""

        if not get_context_flag("events"):

            event_info = None

        if not get_context_flag("weather"):

            cur_season = ""

            cur_weather = ""

        if not get_context_flag("location"):

            cur_world = ""

        if not get_context_flag("memory"):

            memories = ""

        if not get_context_flag("career"):

            biz_info = None

        if not get_context_flag("social"):

            rel_desc = ""

        if is_ww_sex and sex_info:

            if not get_intimate_dialogue_flag("id_pose"):

                sex_info["pose"] = ""

            if not get_intimate_dialogue_flag("id_partners"):

                sex_info["partners"] = ""

            if not get_intimate_dialogue_flag("id_privacy"):

                sex_info["location_and_privacy"] = ""

            if not get_intimate_dialogue_flag("id_observers"):

                scene_participants = []

                is_group_sex_dialogue = False

    except Exception:

        pass



    payload = {

        "type": "direct_dialogue",

        "actor_name": actor_name,

        "target_name": target_name,

        "message": "",

        "spoken_text": "",

        "world": cur_world,

        "current_time": cur_sim_time,

        "season": cur_season,

        "weather": cur_weather,

        "holiday": cur_holiday,

        "messages": history_msgs,

        "actor_info": actor_info_summary,

        "target_info": target_info_summary,

        "relationship": rel_desc,

        "memories": memories,

        "witnesses": witnesses_str,

        "target_age": target_age,

        "is_pet": is_pet,

        "is_group_conversation": is_group_conv,

        "group_members": group_members_payload,

        "bystanders": bystanders_payload,

        "other_sims": other_sims_payload,

        "multisim_join_enabled": multisim_join_enabled,

        "multisim_rules": get_all_multisim_rules(is_en=is_en),

    }



    if event_info:

        payload["event_info"] = event_info

    if biz_info:

        payload["business_info"] = biz_info

    if is_ww_sex:

        payload["is_ww_sex"] = True

        if sex_info:

            payload["sex_info"] = sex_info

        if scene_participants:

            payload["scene_participants"] = scene_participants

        if is_group_sex_dialogue:

            payload["is_group_sex_dialogue"] = True



    return {

        "base_payload": payload,

        "group_members_payload": group_members_payload,

        "bystanders_payload": bystanders_payload,

        "other_sim_infos": other_sim_infos,

        "bystander_sim_infos": bystander_sim_infos,

        "is_group_conv": is_group_conv,

        "is_group_sex_dialogue": is_group_sex_dialogue,

        "scene_participants": scene_participants,

        "actor_sim": actor_sim,

        "target_sim": target_sim,

        "actor_name": actor_name,

        "target_name": target_name,

        "is_en": is_en,

    }





def _start_pregathering_direct_dialogue_context(actor_sim_info, target_sim_info, is_ww_sex: bool = False):

    """Spawns an asynchronous worker to pre-compile dialogue context while the player is typing their phrase."""

    if actor_sim_info is None or target_sim_info is None:

        return

    actor_id = getattr(actor_sim_info, "sim_id", 0)

    tgt_id = getattr(target_sim_info, "sim_id", 0)

    if not actor_id or not tgt_id:

        return



    key = (actor_id, tgt_id)

    ready_event = threading.Event()

    holder = {}



    def _pregather_worker():

        try:

            t0 = time.time()

            log(f"[PREGATHER] Starting background context pre-gathering for ({actor_id} -> {tgt_id}, is_ww={is_ww_sex})...")

            ctx = _collect_direct_dialogue_context(actor_sim_info, target_sim_info, is_ww_sex=is_ww_sex)

            holder["data"] = ctx

            holder["time"] = time.time()

            elapsed = time.time() - t0

            log(f"[PREGATHER] Background context pre-gathering finished in {elapsed:.2f}s!")

        except Exception as ex_pg:

            log_exception("Error in background pregathering context", ex_pg)

        finally:

            ready_event.set()



    with _PREGATHER_LOCK:

        _PREGATHERED_DIALOGUE_CACHE[key] = {

            "event": ready_event,

            "holder": holder,

            "time": time.time(),

            "is_ww_sex": is_ww_sex,

        }



    t = threading.Thread(

        target=_pregather_worker,

        name=f"SynapsePregather_{actor_id}_{tgt_id}",

        daemon=True,

    )

    t.start()





def _clear_pregathered_context(actor_id: int, tgt_id: int):

    """Removes pregathered context from cache when a dialogue window is cancelled."""

    with _PREGATHER_LOCK:

        _PREGATHERED_DIALOGUE_CACHE.pop((actor_id, tgt_id), None)





def _worker_direct_dialogue(actor_sim_info, target_sim_info, spoken_text: str, waiting_dialog=None, prev_speed=None, is_ww_sex: bool = False):

    """Worker thread: gathers context, calls bridge, and applies response."""

    tgt_id = getattr(target_sim_info, "sim_id", 0)

    actor_id = getattr(actor_sim_info, "sim_id", 0)

    target_name = get_recipient_display_name(target_sim_info)

    actor_name = get_recipient_display_name(actor_sim_info)



    try:

        key = (actor_id, tgt_id)

        cached_entry = None

        with _PREGATHER_LOCK:

            cached_entry = _PREGATHERED_DIALOGUE_CACHE.pop(key, None)



        pregathered = None

        if cached_entry:

            cached_entry["event"].wait(timeout=3.5)

            holder = cached_entry.get("holder", {})

            data = holder.get("data")

            if data and (time.time() - cached_entry.get("time", 0.0) < 1800.0) and cached_entry.get("is_ww_sex") == is_ww_sex:

                pregathered = data

                log(f"[DIRECT DIALOGUE] Reusing pre-gathered context! Instant fast-path active.")



        if not pregathered:

            log(f"[DIRECT DIALOGUE] Pre-gathered context not available or timed out, gathering synchronously...")

            pregathered = _collect_direct_dialogue_context(actor_sim_info, target_sim_info, is_ww_sex=is_ww_sex)



        payload = dict(pregathered["base_payload"])

        payload["message"] = spoken_text

        payload["spoken_text"] = spoken_text



        group_members_payload = pregathered.get("group_members_payload", [])

        bystanders_payload = pregathered.get("bystanders_payload", [])

        other_sim_infos = pregathered.get("other_sim_infos", [])

        bystander_sim_infos = pregathered.get("bystander_sim_infos", [])

        is_group_conv = pregathered.get("is_group_conv", False)

        is_group_sex_dialogue = pregathered.get("is_group_sex_dialogue", False)

        scene_participants = pregathered.get("scene_participants", [])

        is_en = pregathered.get("is_en", _is_en())

        actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else pregathered.get("actor_sim")

        target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else pregathered.get("target_sim")



        try:

            from ai_social_pc.dossier_manager import build_third_party_dossier

            dossier_content = build_third_party_dossier(spoken_text or "", [actor_sim_info, target_sim_info], is_en=is_en)

            if dossier_content:

                payload["third_party_dossier"] = dossier_content

        except Exception as e_dos:

            log_exception("Error attaching dossier in direct dialogue", e_dos)



        url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/direct_dialogue"

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(

            url,

            data=data,

            headers={"Content-Type": "application/json; charset=utf-8"},

            method="POST",

        )

        with urllib.request.urlopen(req, timeout=120) as resp:

            resp_data = json.loads(resp.read().decode("utf-8"))



        clean_text = resp_data.get("text") or resp_data.get("reply") or "..."

        anim_category = str(resp_data.get("animation") or "FRIENDLY").upper().strip()

        delta_fr = int(resp_data.get("delta_friendship", 0))

        delta_rom = int(resp_data.get("delta_romance", 0))

        try:

            from ai_social_pc.child_safety import can_apply_romance

            if not can_apply_romance(actor_sim_info, target_sim_info):

                delta_rom = 0

        except Exception:

            pass

        # Safeguard: map relationship deltas to appropriate animation if omitted or neutral

        if anim_category in ("FRIENDLY", "DEFAULT", "CONVERSATION", ""):

            if delta_rom >= 2:

                anim_category = "ROMANTIC"

            elif delta_fr <= -5 or delta_rom <= -5:

                anim_category = "MEAN"

            else:

                anim_category = "FRIENDLY"



        # Inline memory and action tags extracted directly from the single-prompt dialogue

        memory_summary = str(resp_data.get("memory_summary") or "").strip()

        memory_days = int(resp_data.get("memory_days", 3) or 3)

        action_type = resp_data.get("action_type")

        action_actor = resp_data.get("action_actor")



        log(f"[DIRECT DIALOGUE] Reply received from {target_name}: '{clean_text}' | Anim: {anim_category} | FR: {delta_fr:+d}, ROM: {delta_rom:+d}")

        if memory_summary:

            log(f"[DIRECT DIALOGUE] Single-prompt memory detected: '{memory_summary}' ({memory_days} days)")

        if action_type:

            log(f"[DIRECT DIALOGUE] Single-prompt action detected: [WHODO={action_actor}] [DO={action_type}]")



        wd_ref = waiting_dialog

        waiting_dialog = None

        ps_ref = prev_speed

        prev_speed = None



        from ai_social_pc.main_thread import run_on_main_thread

        def _main_finish():

            _close_waiting_dialog(wd_ref)

            _restore_game_clock(ps_ref)

            # Build list of all conversation participants

            all_group_sim_ids = [actor_id, tgt_id]

            for g_item in group_members_payload:

                g_sid = g_item.get("sim_id")

                if g_sid and g_sid not in all_group_sim_ids:

                    all_group_sim_ids.append(g_sid)



            # Determine channel

            if is_ww_sex:

                conv_channel = "intimate_group_dialogue" if is_group_conv else "intimate_dialogue"

            else:

                conv_channel = "group_dialogue" if is_group_conv else "direct_dialogue"



            # Sync pairwise dialogue history for all participants

            if len(all_group_sim_ids) > 2:

                for idx_a in range(len(all_group_sim_ids)):

                    for idx_b in range(idx_a + 1, len(all_group_sim_ids)):

                        p_a = all_group_sim_ids[idx_a]

                        p_b = all_group_sim_ids[idx_b]

                        _record_dialogue_turn(p_a, p_b, actor_name, spoken_text)

                        _record_dialogue_turn(p_a, p_b, target_name, clean_text)

            else:

                _record_dialogue_turn(actor_id, tgt_id, actor_name, spoken_text)

                _record_dialogue_turn(actor_id, tgt_id, target_name, clean_text)



            try:

                from ai_social_pc.conversation_log import record_conversation_exchange, record_overheard_exchange

                record_conversation_exchange(all_group_sim_ids, actor_id, actor_name, spoken_text, channel=conv_channel)

                record_conversation_exchange(all_group_sim_ids, tgt_id, target_name, clean_text, channel=conv_channel)

                try:

                    record_overheard_exchange(

                        center_sim_or_pos=actor_sim,

                        speaker_id=actor_id,

                        speaker_name=actor_name,

                        text=spoken_text,

                        channel="overheard_dialogue",

                        target_name=target_name,

                        exclude_sim_ids=set(all_group_sim_ids),

                        max_distance=15.0,

                    )

                    record_overheard_exchange(

                        center_sim_or_pos=target_sim or actor_sim,

                        speaker_id=tgt_id,

                        speaker_name=target_name,

                        text=clean_text,

                        channel="overheard_dialogue",

                        target_name=actor_name,

                        exclude_sim_ids=set(all_group_sim_ids),

                        max_distance=15.0,

                    )

                except Exception as ex_ov_dd:

                    pass

            except Exception as ex_clog:

                log_exception("Failed to record direct dialogue in conversation log", ex_clog)



            # Extract joined replies from other Sims if any

            replies_list = resp_data.get("replies") or []

            joined_replies = []

            if len(replies_list) > 1:

                joined_replies = replies_list[1:]



            # Record conversation exchange for joined participants

            if joined_replies:

                try:

                    for jr in joined_replies:

                        jr_name = jr.get("sender") or "Сим"

                        jr_txt = jr.get("text") or ""

                        jr_id = jr.get("sim_id", 0)

                        if jr_txt:

                            if len(all_group_sim_ids) > 2:

                                for idx_a in range(len(all_group_sim_ids)):

                                    for idx_b in range(idx_a + 1, len(all_group_sim_ids)):

                                        _record_dialogue_turn(all_group_sim_ids[idx_a], all_group_sim_ids[idx_b], jr_name, jr_txt)

                            else:

                                _record_dialogue_turn(actor_id, tgt_id, jr_name, jr_txt)

                            try:

                                from ai_social_pc.conversation_log import record_conversation_exchange

                                record_conversation_exchange(all_group_sim_ids, jr_id or tgt_id, jr_name, jr_txt, channel=conv_channel)

                            except Exception:

                                pass

                except Exception as ex_jr_rec:

                    log_exception("Error recording joined replies in conversation history", ex_jr_rec)



            _apply_direct_dialogue_results(

                actor_sim_info,

                target_sim_info,

                spoken_text,

                clean_text,

                anim_category,

                delta_fr,

                delta_rom,

                memory_summary=memory_summary,

                memory_days=memory_days,

                action_type=action_type,

                action_actor=action_actor,

                is_ww_sex=is_ww_sex,

                joined_replies=joined_replies,

            )



        run_on_main_thread(_main_finish)



    except Exception as e:

        log_exception(f"Error in direct dialogue with {target_name}", e)

        wd_ref = waiting_dialog

        waiting_dialog = None

        ps_ref = prev_speed

        prev_speed = None



        from ai_social_pc.main_thread import run_on_main_thread

        def _main_err():

            _close_waiting_dialog(wd_ref)

            _restore_game_clock(ps_ref)

            is_en = _is_en()

            show_chat_notification(

                title="Dialogue Error" if is_en else "Ошибка диалога",

                text=f"Failed to receive response from {target_name}. Ensure Synapse is running!" if is_en else f"Не удалось получить ответ от {target_name}. Убедитесь, что Synapse запущен!",

                sim_info=actor_sim_info,

                is_error=True,

            )

            act_s = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None

            tgt_s = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None

            clean_up_direct_dialogue_conversation(act_s, tgt_s)

        run_on_main_thread(_main_err)

    finally:

        if waiting_dialog is not None:

            _close_waiting_dialog(waiting_dialog)

        if prev_speed is not None:

            _restore_game_clock(prev_speed)

        _PENDING_DIALOGUE_SIM_IDS.discard(tgt_id)





def _apply_direct_dialogue_results(

    actor_sim_info,

    target_sim_info,

    spoken_text: str,

    reply_text: str,

    anim_category: str,

    delta_fr: int,

    delta_rom: int,

    memory_summary: str = "",

    memory_days: int = 3,

    action_type: Optional[str] = None,

    action_actor: Optional[str] = None,

    is_ww_sex: bool = False,

    joined_replies: Optional[List[Dict[str, Any]]] = None,

):

    if services is not None and hasattr(services, "current_zone"):

        try:

            zone = services.current_zone()

            if zone is None or getattr(zone, "is_zone_shutting_down", False):

                log("[DIRECT DIALOGUE] Zone is shutting down or None; aborting visual results.")

                return

        except Exception:

            pass



    target_name = get_recipient_display_name(target_sim_info)

    actor_name = get_recipient_display_name(actor_sim_info)

    actor_id = getattr(actor_sim_info, "sim_id", 0)

    tgt_id = getattr(target_sim_info, "sim_id", 0)



    from ai_social_pc.main_thread import run_on_main_thread



    # =========================================================================

    # Phase 1: Player Sim speaks first (sequential dialogue playback)

    # =========================================================================

    try:

        try:

            import synapse_balloons

        except ImportError:

            from balloons import synapse_balloons

        if synapse_balloons is not None and hasattr(synapse_balloons, "show_sim_balloon"):

            synapse_balloons.show_sim_balloon(

                sim_info_or_id=actor_sim_info,

                text=spoken_text,

                balloon_type="speech",

                name=getattr(actor_sim_info, "first_name", None),

                avoid_sim_id=tgt_id,

            )

    except Exception as ex_b:

        log(f"[BALLOON] Could not display player speech balloon: {ex_b}")



    # Calculate reading and typing delay for player's speech before NPC responds

    # (35 characters per second typing speed + comfortable reading hold)

    typing_time = len(spoken_text) / 35.0

    player_delay = max(2.5, min(6.0, typing_time + 1.6))



    # =========================================================================

    # Phase 2: NPC Sim replies after player finishes speaking

    # =========================================================================

    def _execute_npc_reply():

        if services is not None and hasattr(services, "current_zone"):

            try:

                zone = services.current_zone()

                if zone is None or getattr(zone, "is_zone_shutting_down", False):

                    return

            except Exception:

                pass



        # 1. Apply relationship impact

        if delta_fr != 0 or delta_rom != 0:

            apply_chat_relationship_impact(actor_sim_info, target_sim_info, delta_fr=delta_fr, delta_rom=delta_rom)



        # 2. Trigger social animation

        try:

            actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None

            target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None

            if not is_ww_sex and actor_sim is not None and target_sim is not None:

                play_direct_dialogue_animation(actor_sim, target_sim, anim_category)

            elif is_ww_sex:

                log("[DIRECT DIALOGUE] Skipping standard conversation animations during sex to preserve intimate animations.")

        except Exception as ex_anim:

            log_exception("Error playing animation", ex_anim)



        # 3. Notification of reply with relationship deltas

        is_en = _is_en()

        if is_ww_sex:

            anim_title = "Intimate conversation" if is_en else "Интимный разговор"

        elif is_en:

            anim_title = ANIM_NAME_EN.get(anim_category.upper(), "Conversation")

        else:

            anim_title = ANIM_NAME_RU.get(anim_category.upper(), "Разговор")

        anim_ru = anim_title

        stats_parts = []

        if delta_fr != 0:

            fr_lbl = "Friendship" if is_en else "Дружба"

            stats_parts.append(f"{fr_lbl}: {delta_fr:+d}")

        if delta_rom != 0:

            rom_lbl = "Romance" if is_en else "Романтика"

            stats_parts.append(f"{rom_lbl}: {delta_rom:+d}")

        stats_tag = f" | {', '.join(stats_parts)}" if stats_parts else ""



        notif_body = f"«{reply_text}»\n\n[{anim_ru}{stats_tag}]"



        try:

            from ai_thought_reader.config import get_display_flag

            show_direct_notif = get_display_flag("direct_notification", True)

            show_direct_bal = get_display_flag("direct_balloon", True)

        except Exception:

            show_direct_notif = True

            show_direct_bal = True



        if show_direct_notif:

            show_chat_notification(

                title=f"{target_name}:",

                text=notif_body,

                sim_info=target_sim_info,

                is_error=False,

            )



        # 4. Synapse AI Balloon (Phase 3.2: AI Reply Speech Balloon over target Sim)

        if show_direct_bal:

            try:

                try:

                    import synapse_balloons

                except ImportError:

                    from balloons import synapse_balloons

                if synapse_balloons is not None and hasattr(synapse_balloons, "show_sim_balloon"):

                    synapse_balloons.show_sim_balloon(

                        sim_info_or_id=target_sim_info,

                        text=reply_text,

                        balloon_type="speech",

                        name=getattr(target_sim_info, "first_name", None),

                        avoid_sim_id=actor_id,

                    )

            except Exception as ex_b:

                log(f"[BALLOON] Could not display AI reply speech balloon: {ex_b}")



        # 5. Inline memory and action execution (100% single-prompt architecture)

        if memory_summary:

            try:

                from ai_social_pc.memory_manager import add_memory

                add_memory(actor_id, tgt_id, memory_summary, memory_days)

                log(f"[DIRECT DIALOGUE] Inline episodic memory recorded: '{memory_summary}' ({memory_days} days)")

            except Exception as ex_m:

                log_exception("Failed recording inline memory from direct dialogue", ex_m)



        if action_type:

            try:

                from ai_social_pc.action_executor import execute_post_chat_action

                execute_post_chat_action(action_actor or target_name, action_type, actor_sim_info, target_sim_info)

                log(f"[DIRECT DIALOGUE] Inline post-dialogue action executed: [WHODO={action_actor}] [DO={action_type}]")

            except Exception as ex_act:

                log_exception("Failed executing inline post-dialogue action", ex_act)



        try:

            from ai_social_pc.autonomous_director import record_player_action

            record_player_action(actor_sim_info, target_sim_info)

        except Exception:

            pass



        # Calculate reading hold time for target Sim's reply

        reply_hold_time = max(3.5, min(7.5, len(reply_text) / 28.0 + 2.0))



        # Schedule joined replies from other Sims (Phase 3: Joined Sims)

        accum_joined_delay = reply_hold_time

        if joined_replies:

            for j_idx, jr in enumerate(joined_replies):

                jr_name = jr.get("sender") or "Сим"

                jr_text = jr.get("text") or ""

                jr_anim = jr.get("animation") or "FRIENDLY"

                jr_fr = int(jr.get("delta_friendship", 0))

                jr_rom = int(jr.get("delta_romance", 0))

                jr_sim_id = int(jr.get("sim_id", 0))



                # Lookup sim_info for the joined Sim

                jr_sim_info = None

                if jr_sim_id and services is not None:

                    sim_mgr = services.sim_info_manager()

                    if sim_mgr is not None:

                        jr_sim_info = sim_mgr.get(jr_sim_id)

                if jr_sim_info is None and services is not None:

                    sim_mgr = services.sim_info_manager()

                    if sim_mgr is not None:

                        for inst in sim_mgr.instanced_sims_gen():

                            inf = getattr(inst, "sim_info", inst)

                            if inf is not None:

                                fn = get_recipient_display_name(inf)

                                if fn and (fn.lower() in jr_name.lower() or jr_name.lower() in fn.lower()):

                                    jr_sim_info = inf

                                    break



                def _show_joined_turn(s_info, s_name, t_body, a_cat, d_fr, d_rom, s_act=None, s_mem="", s_days=3):

                    if services is not None and hasattr(services, "current_zone"):

                        try:

                            zone = services.current_zone()

                            if zone is None or getattr(zone, "is_zone_shutting_down", False):

                                return

                        except Exception:

                            pass



                    # 1. Apply relationship delta between Player and joined Sim

                    if s_info is not None and (d_fr != 0 or d_rom != 0):

                        try:

                            apply_chat_relationship_impact(actor_sim_info, s_info, delta_fr=d_fr, delta_rom=d_rom)

                        except Exception as ex_rel_j:

                            log_exception("Error applying joined relationship impact", ex_rel_j)



                    # 2. Notification

                    is_en = _is_en()

                    a_title = ANIM_NAME_EN.get(a_cat.upper(), "Conversation") if is_en else ANIM_NAME_RU.get(a_cat.upper(), "Разговор")

                    parts = []

                    if d_fr != 0:

                        parts.append(f"{('Friendship' if is_en else 'Дружба')}: {d_fr:+d}")

                    if d_rom != 0:

                        parts.append(f"{('Romance' if is_en else 'Романтика')}: {d_rom:+d}")

                    st_tag = f" | {', '.join(parts)}" if parts else ""

                    notif_txt = f"«{t_body}»\n\n[{a_title}{st_tag}]"



                    try:

                        from ai_thought_reader.config import get_display_flag

                        sh_notif = get_display_flag("direct_notification", True)

                        sh_bal = get_display_flag("direct_balloon", True)

                    except Exception:

                        sh_notif = True

                        sh_bal = True



                    if sh_notif and s_info is not None:

                        show_chat_notification(

                            title=f"{s_name}:",

                            text=notif_txt,

                            sim_info=s_info,

                            is_error=False,

                        )



                    # 3. Speech Balloon over joined Sim

                    if sh_bal and s_info is not None:

                        try:

                            try:

                                import synapse_balloons

                            except ImportError:

                                from balloons import synapse_balloons

                            if synapse_balloons is not None and hasattr(synapse_balloons, "show_sim_balloon"):

                                synapse_balloons.show_sim_balloon(

                                    sim_info_or_id=s_info,

                                    text=t_body,

                                    balloon_type="speech",

                                    name=getattr(s_info, "first_name", None),

                                    avoid_sim_id=actor_id,

                                )

                        except Exception as ex_jb:

                            log(f"[BALLOON] Could not display joined speech balloon: {ex_jb}")



                    # 4. Action execution from joined Sim (e.g. stop_sex, join_sex, etc.)

                    if s_act:

                        try:

                            from ai_social_pc.action_executor import execute_post_chat_action

                            execute_post_chat_action(s_name, s_act, actor_sim_info, s_info or target_sim_info)

                            log(f"[DIRECT DIALOGUE] Joined Sim action executed: [WHODO={s_name}] [DO={s_act}]")

                        except Exception as ex_j_act:

                            log_exception("Failed executing joined action", ex_j_act)



                    # 5. Episodic memory from joined Sim

                    if s_mem and s_info is not None:

                        try:

                            from ai_social_pc.memory_manager import add_memory

                            add_memory(actor_id, getattr(s_info, "sim_id", 0), s_mem, s_days)

                            log(f"[DIRECT DIALOGUE] Joined Sim memory recorded: '{s_mem}' ({s_days} days)")

                        except Exception as ex_j_mem:

                            log_exception("Failed recording joined memory", ex_j_mem)



                jr_act = jr.get("action_type")

                jr_mem = str(jr.get("memory_summary") or "").strip()

                jr_days = int(jr.get("memory_days", 3) or 3)



                j_delay = accum_joined_delay

                jt = threading.Timer(

                    j_delay,

                    lambda si=jr_sim_info, sn=jr_name, tb=jr_text, ac=jr_anim, df=jr_fr, dr=jr_rom, sa=jr_act, sm=jr_mem, sd=jr_days: run_on_main_thread(

                        _show_joined_turn, si, sn, tb, ac, df, dr, sa, sm, sd

                    )

                )

                jt.daemon = True

                jt.start()



                # Add reading hold time for this joined turn

                turn_hold = max(3.5, min(7.5, len(jr_text) / 28.0 + 2.0))

                accum_joined_delay += turn_hold



        # In EA's native social system, Sims naturally remain in sim_Chat after an exchange.
        # The mixer sub-interactions (speaking/reacting) finish automatically.
        # We do not forcibly kill sim_Chat with a timer, preventing stuck [X] icons in the queue.



    reply_timer = threading.Timer(player_delay, lambda: run_on_main_thread(_execute_npc_reply))

    reply_timer.daemon = True

    reply_timer.start()

