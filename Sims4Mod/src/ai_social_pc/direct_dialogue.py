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

# In-memory history of in-person dialogue turns
# Key: (min_sim_id, max_sim_id)
# Value: list of dicts: {"sender": str, "text": str, "sim_time_hours": float}
_DIRECT_DIALOGUE_HISTORY: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

# Delayed summarization timer handles
# Key: (min_sim_id, max_sim_id)
# Value: threading.Timer object
_SUMMARIZE_TIMERS: Dict[Tuple[int, int], threading.Timer] = {}


def hook_direct_dialogue_affordance(dd_aff):
    """
    Overrides the _test method on the Direct Dialogue affordance class (SYNAPSE_DIRECT_DIALOGUE_TUNING_ID)
    to ensure that «Поговорить... (ИИ)»:
    1. NEVER appears on the active player Sim (cannot speak to self).
    2. NEVER appears on any animal (dogs, cats, horses, foxes).
    3. NEVER appears on babies or infants.
    """
    if dd_aff is None:
        return
    if getattr(dd_aff, "_synapse_test_hooked", False):
        return

    orig_test = getattr(dd_aff, "_test", None)

    @flexmethod
    def _custom_direct_dialogue_test(cls, inst, target=None, context=None, **kwargs):
        try:
            # 1. Reject Self
            actor_sim = getattr(context, "sim", None) if context is not None else None
            if actor_sim is not None and target is not None:
                if target is actor_sim:
                    return TestResult.NONE if TestResult is not None else False
                actor_id = getattr(actor_sim, "id", None) or getattr(actor_sim, "sim_id", None)
                target_id = getattr(target, "id", None) or getattr(target, "sim_id", None)
                if actor_id and target_id and actor_id == target_id:
                    return TestResult.NONE if TestResult is not None else False

            # Also check if target is client's active sim
            if services is not None and target is not None:
                client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
                if client is not None:
                    active_sim = getattr(client, "active_sim", None)
                    if active_sim is not None:
                        if target is active_sim:
                            return TestResult.NONE if TestResult is not None else False
                        act_id = getattr(active_sim, "id", None) or getattr(active_sim, "sim_id", None)
                        tgt_id = getattr(target, "id", None) or getattr(target, "sim_id", None)
                        if act_id and tgt_id and act_id == tgt_id:
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
        log(f"[DIRECT DIALOGUE] Successfully installed _test hook on {dd_aff} ({SYNAPSE_DIRECT_DIALOGUE_TUNING_ID})")
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

    # Prune turns older than 24 sim-hours
    valid_turns = [turn for turn in history if (cur_hours - turn.get("sim_time_hours", 0.0)) <= max_age_hours]
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
    Triggers chat summarization immediately after a direct dialogue turn without any delay,
    so post-chat actions (visiting lots, traveling together, romantic dates, money transfers, intimacy)
    execute right away.
    """
    actor_id = getattr(actor_sim_info, "sim_id", 0)
    target_id = getattr(target_sim_info, "sim_id", 0)
    if not actor_id or not target_id:
        return

    try:
        from ai_thought_reader.config import get_chat_context_flag
        if not get_chat_context_flag("chat_memory") or not get_chat_context_flag("summarize_direct"):
            log("[DIRECT DIALOGUE] Summarization skipped because 'summarize_direct' or 'chat_memory' is disabled.")
            return
    except Exception:
        pass

    pair_key = (min(actor_id, target_id), max(actor_id, target_id))

    # Cancel any leftover timer if exists
    existing_timer = _SUMMARIZE_TIMERS.pop(pair_key, None)
    if existing_timer is not None:
        try:
            existing_timer.cancel()
        except Exception:
            pass

    try:
        history = _get_and_prune_dialogue_history(actor_id, target_id, max_turns=15, max_age_hours=24.0)
        if history and len(history) >= 2:
            from ai_social_pc.memory_manager import request_chat_summarization_async
            log(f"[DIRECT DIALOGUE] Triggering immediate summarization for {pair_key} ({len(history)} turns)")
            request_chat_summarization_async(actor_sim_info, target_sim_info, history, is_direct_dialogue=True)
    except Exception as e:
        log_exception("Error executing direct dialogue summarization", e)


# Backward-compatibility alias
_schedule_delayed_summarization = _trigger_immediate_summarization


def _get_nearby_witness_names(actor_sim, target_sim, max_distance: float = 15.0) -> List[str]:
    """Finds names of other Sims near the conversation who can hear it."""
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
                    name = get_recipient_display_name(getattr(inst, "sim_info", inst))
                    if name and name not in witnesses:
                        witnesses.append(name)
    except Exception as ex:
        log_exception("Error getting nearby witnesses", ex)
    return witnesses


def _find_social_super_interaction(actor_sim, target_sim):
    """
    Finds the active running SocialSuperInteraction between actor_sim and target_sim.
    """
    if actor_sim is None or target_sim is None:
        return None

    # 1. Check actor's main social group
    if hasattr(actor_sim, "get_main_group"):
        try:
            grp = actor_sim.get_main_group()
            if grp is not None:
                in_grp = False
                try:
                    in_grp = (target_sim in grp)
                except Exception:
                    pass
                if in_grp and hasattr(grp, "get_si_registered_for_sim"):
                    si = grp.get_si_registered_for_sim(actor_sim)
                    if si is not None and not getattr(si, "is_finishing", False):
                        return si
        except Exception:
            pass

    # 2. Check actor's si_state
    if hasattr(actor_sim, "si_state"):
        try:
            for si in actor_sim.si_state:
                if getattr(si, "is_social", False) and not getattr(si, "is_finishing", False):
                    si_target = getattr(si, "target", None)
                    if si_target is target_sim:
                        return si
                    grp = getattr(si, "social_group", None)
                    if grp is not None:
                        try:
                            if target_sim in grp:
                                return si
                        except Exception:
                            pass
        except Exception:
            pass

    # 3. Check target's main social group (as fallback)
    if hasattr(target_sim, "get_main_group"):
        try:
            grp = target_sim.get_main_group()
            if grp is not None:
                in_grp = False
                try:
                    in_grp = (actor_sim in grp)
                except Exception:
                    pass
                if in_grp and hasattr(grp, "get_si_registered_for_sim"):
                    si = grp.get_si_registered_for_sim(actor_sim) or grp.get_si_registered_for_sim(target_sim)
                    if si is not None and not getattr(si, "is_finishing", False):
                        return si
        except Exception:
            pass

    return None


def _execute_social_mixer(speaker_sim, listener_sim, mixer_affordance_id: int, super_si) -> bool:
    """
    Executes a SocialMixerInteraction attached to super_si.
    This produces the in-conversation speech bubble and plays the corresponding talk animation.
    """
    if services is None or speaker_sim is None or listener_sim is None or super_si is None:
        return False

    aff_mgr = services.affordance_manager()
    if aff_mgr is None:
        return False

    mixer_cls = aff_mgr.get(mixer_affordance_id)
    if mixer_cls is None:
        log(f"[ANIMATION] Mixer affordance {mixer_affordance_id} not found in manager", level="WARN")
        return False

    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    sa = getattr(super_si, "affordance", super_si)

    context = InteractionContext(
        speaker_sim,
        InteractionContext.SOURCE_PIE_MENU,
        Priority.High,
        client=client,
        insert_strategy=QueueInsertStrategy.NEXT if QueueInsertStrategy is not None else None,
    )

    if AffordanceObjectPair is not None:
        try:
            aop = AffordanceObjectPair(
                mixer_cls,
                listener_sim,
                sa,
                super_si,
                skip_safe_tests=True,
                skip_test_on_execute=True,
            )
            res = aop.test_and_execute(context)
            if res:
                log(f"[ANIMATION] AOP test_and_execute succeeded for {mixer_affordance_id} ({speaker_sim} -> {listener_sim}): {res}")
                return True
            res = aop.execute(context)
            if res:
                log(f"[ANIMATION] AOP execute succeeded for {mixer_affordance_id} ({speaker_sim} -> {listener_sim}): {res}")
                return True
        except Exception as e:
            log_exception(f"Error executing social mixer {mixer_affordance_id}", e)

    return False


def play_direct_dialogue_animation(actor_sim, target_sim, anim_category: str):
    """
    Triggers a social mixer animation within the active conversation.
    Displays as an attached speech bubble on the dialogue portrait (sub-interaction)
    and plays the corresponding gesture/talk animation.
    """
    if services is None or actor_sim is None or target_sim is None:
        return

    try:
        actor_info = getattr(actor_sim, "sim_info", None)
        target_info = getattr(target_sim, "sim_info", None)

        is_pet = bool(getattr(target_info, "is_pet", False) or getattr(actor_info, "is_pet", False))
        is_baby_or_infant = False
        for s_info in (actor_info, target_info):
            if s_info is not None:
                age_val = getattr(s_info, "age", None)
                age_str = str(age_val).upper() if age_val else ""
                if any(k in age_str for k in ("BABY", "INFANT", "TODDLER")):
                    is_baby_or_infant = True
                    break

        aff_mgr = services.affordance_manager()
        if aff_mgr is None:
            return

        cat = str(anim_category or "FRIENDLY").upper().strip()

        # Select custom or base-game mixer
        mixer_id = BASE_MIXER_FRIENDLY
        if not is_pet and not is_baby_or_infant:
            if cat == "ROMANTIC":
                mixer_id = CUSTOM_MIXER_ROMANTIC if (CUSTOM_MIXER_ROMANTIC and aff_mgr.get(CUSTOM_MIXER_ROMANTIC)) else BASE_MIXER_ROMANTIC
            elif cat == "FUNNY":
                mixer_id = CUSTOM_MIXER_FUNNY if (CUSTOM_MIXER_FUNNY and aff_mgr.get(CUSTOM_MIXER_FUNNY)) else BASE_MIXER_FUNNY
            elif cat == "MEAN":
                mixer_id = CUSTOM_MIXER_MEAN if (CUSTOM_MIXER_MEAN and aff_mgr.get(CUSTOM_MIXER_MEAN)) else BASE_MIXER_MEAN
            else:
                mixer_id = CUSTOM_MIXER_FRIENDLY if (CUSTOM_MIXER_FRIENDLY and aff_mgr.get(CUSTOM_MIXER_FRIENDLY)) else BASE_MIXER_FRIENDLY

        # 1. Look for existing conversation
        super_si = _find_social_super_interaction(actor_sim, target_sim)

        # 2. If no conversation exists yet, start one!
        if super_si is None:
            log(f"[ANIMATION] Sims are not in conversation yet. Initiating sim_Chat ({AFFORDANCE_CHAT_SUPER})...")
            client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
            chat_cls = aff_mgr.get(AFFORDANCE_CHAT_SUPER)
            if chat_cls is not None:
                ctx = InteractionContext(
                    actor_sim,
                    InteractionContext.SOURCE_PIE_MENU,
                    Priority.High,
                    client=client,
                )
                res = actor_sim.push_super_affordance(chat_cls, target_sim, ctx)
                if res and hasattr(res, "interaction") and res.interaction is not None:
                    super_si = res.interaction

        if super_si is not None and not is_pet and not is_baby_or_infant:
            # The player's Sim is the SPEAKER (talking / flirting / joking / arguing)
            # The NPC is the LISTENER (hearing the player's line and reacting)
            executed = _execute_social_mixer(speaker_sim=actor_sim, listener_sim=target_sim, mixer_affordance_id=mixer_id, super_si=super_si)
            if not executed:
                # Fallback: if actor cannot execute, let target execute
                executed = _execute_social_mixer(speaker_sim=target_sim, listener_sim=actor_sim, mixer_affordance_id=mixer_id, super_si=super_si)
            log(f"[ANIMATION] Executed {cat} mixer ({mixer_id}) (Speaker: {actor_sim} -> Listener: {target_sim}): {executed}")
        else:
            log(f"[ANIMATION] Skipping social mixer (is_pet={is_pet}, is_baby={is_baby_or_infant}, super_si={super_si})")

    except Exception as e:
        log_exception(f"Failed to play direct dialogue animation ({anim_category})", e)


def start_direct_dialogue(target_sim_id: Any, actor_sim_info: Any = None):
    """
    Main entry point when player clicks «Поговорить (ИИ)...» on a Sim.
    """
    if services is None:
        log("[DIRECT DIALOGUE] services is None", level="ERROR")
        return

    sim_info_mgr = services.sim_info_manager()
    if sim_info_mgr is None:
        return

    target_sim_info = None
    try:
        t_id = int(target_sim_id)
        target_sim_info = sim_info_mgr.get(t_id)
    except (ValueError, TypeError):
        if hasattr(target_sim_id, "sim_info"):
            target_sim_info = target_sim_id.sim_info
        else:
            target_sim_info = target_sim_id

    if target_sim_info is None:
        log(f"[DIRECT DIALOGUE] Could not resolve target Sim from {target_sim_id}", level="WARN")
        return

    if actor_sim_info is None:
        actor_sim_info = services.active_sim_info()

    if actor_sim_info is None:
        log("[DIRECT DIALOGUE] active_sim_info is None", level="ERROR")
        return

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    tgt_id = getattr(target_sim_info, "sim_id", 0)

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

    show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info)


def show_direct_dialogue_input_dialog(actor_sim_info, target_sim_info, default_text: str = ""):
    """
    Opens UiDialogTextInputOkCancel for the player to type their spoken phrase.
    """
    if UiDialogTextInputOkCancel is None:
        log("[DIRECT DIALOGUE] UiDialogTextInputOkCancel is not available", level="ERROR")
        return

    is_en = _is_en()
    target_name = get_recipient_display_name(target_sim_info)
    actor_name = get_recipient_display_name(actor_sim_info)
    rel_desc = _get_relationship_description(actor_sim_info, target_sim_info)

    title = f"Speak with {target_name}" if is_en else f"Сказать {target_name}"

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
                if getattr(dlg, "accepted", False):
                    text = ""
                    if hasattr(dlg, "get_input_text"):
                        text = dlg.get_input_text() or ""
                    elif hasattr(dlg, "text_input_responses"):
                        resp_dict = getattr(dlg, "text_input_responses", {})
                        text = resp_dict.get("direct_dialogue_input", "") or ""

                    clean_text = str(text).strip()
                    if clean_text:
                        _dispatch_direct_dialogue(actor_sim_info, target_sim_info, clean_text)
                    else:
                        log("[DIRECT DIALOGUE] Empty text submitted, canceling")
            except Exception as e:
                log_exception("Error in direct dialogue dialog response", e)

        dialog.show_dialog(on_response=_on_response)
        log(f"[DIRECT DIALOGUE] Opened input dialog for dialogue with {target_name}")

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


def _show_waiting_dialog(actor_sim_info, target_name: str, spoken_text: str) -> Optional[Any]:
    """Displays a modal waiting dialog informing player that reply is generating."""
    if UiDialogOk is None:
        return None
    try:
        is_en = _is_en()
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


def _dispatch_direct_dialogue(actor_sim_info, target_sim_info, spoken_text: str):
    """
    Spawns a background thread to call the Synapse AI Bridge at /direct_dialogue.
    Pauses game and opens waiting modal dialog to prevent Sims from walking away.
    """
    tgt_id = getattr(target_sim_info, "sim_id", 0)
    _PENDING_DIALOGUE_SIM_IDS.add(tgt_id)

    target_name = get_recipient_display_name(target_sim_info)
    actor_name = get_recipient_display_name(actor_sim_info)

    # 1. Check experimental setting for game pause & waiting modal
    use_pause_and_modal = True
    try:
        from ai_thought_reader.config import get_experimental_flag
        use_pause_and_modal = get_experimental_flag("direct_dialogue_pause")
    except Exception:
        use_pause_and_modal = True

    prev_speed = _pause_game_clock() if use_pause_and_modal else None
    waiting_dialog = _show_waiting_dialog(actor_sim_info, target_name, spoken_text) if use_pause_and_modal else None

    # 2. Notification backup
    is_en_bk = _is_en()
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
        args=(actor_sim_info, target_sim_info, spoken_text, waiting_dialog, prev_speed),
        name=f"SynapseDirectDialogue_{tgt_id}",
        daemon=True,
    )
    t.start()


def _worker_direct_dialogue(actor_sim_info, target_sim_info, spoken_text: str, waiting_dialog=None, prev_speed=None):
    """Worker thread: gathers context, calls bridge, and applies response."""
    tgt_id = getattr(target_sim_info, "sim_id", 0)
    actor_id = getattr(actor_sim_info, "sim_id", 0)
    target_name = get_recipient_display_name(target_sim_info)
    actor_name = get_recipient_display_name(actor_sim_info)

    try:
        actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None
        target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None

        actor_info_summary = _build_sim_profile_summary(actor_sim_info)
        target_info_summary = _build_sim_profile_summary(target_sim_info)

        rel_desc = _get_relationship_description(actor_sim_info, target_sim_info)
        if _is_en():
            try:
                from ai_thought_reader.context_en import translate_relationship_en
                rel_desc = translate_relationship_en(rel_desc)
            except Exception:
                pass
        memories = format_memories_for_prompt(actor_id, tgt_id) or ""

        witness_names = _get_nearby_witness_names(actor_sim, target_sim)
        witnesses_str = ", ".join(witness_names) if witness_names else ""

        target_age = str(getattr(target_sim_info, "age", "ADULT")).upper()
        is_pet = bool(getattr(target_sim_info, "is_pet", False))

        # Get recent dialogue history (up to 15 turns within last 24 sim hours)
        history_msgs = _get_and_prune_dialogue_history(actor_id, tgt_id, max_turns=15, max_age_hours=24.0)

        cur_sim_time = ""
        try:
            cur_sim_time = get_current_sim_time()
        except Exception:
            pass

        payload = {
            "type": "direct_dialogue",
            "actor_name": actor_name,
            "target_name": target_name,
            "message": spoken_text,
            "spoken_text": spoken_text,
            "current_time": cur_sim_time,
            "messages": history_msgs,
            "actor_info": actor_info_summary,
            "target_info": target_info_summary,
            "relationship": rel_desc,
            "memories": memories,
            "witnesses": witnesses_str,
            "target_age": target_age,
            "is_pet": is_pet,
        }

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
        # Safeguard: map relationship deltas to appropriate animation if omitted or neutral
        if anim_category in ("FRIENDLY", "DEFAULT", "CONVERSATION", ""):
            if delta_rom >= 2:
                anim_category = "ROMANTIC"
            elif delta_fr <= -5 or delta_rom <= -5:
                anim_category = "MEAN"
            else:
                anim_category = "FRIENDLY"

        log(f"[DIRECT DIALOGUE] Reply received from {target_name}: '{clean_text}' | Anim: {anim_category} | FR: {delta_fr:+d}, ROM: {delta_rom:+d}")

        wd_ref = waiting_dialog
        waiting_dialog = None
        ps_ref = prev_speed
        prev_speed = None

        from ai_social_pc.main_thread import run_on_main_thread
        def _main_finish():
            _close_waiting_dialog(wd_ref)
            _restore_game_clock(ps_ref)
            _record_dialogue_turn(actor_id, tgt_id, actor_name, spoken_text)
            _record_dialogue_turn(actor_id, tgt_id, target_name, clean_text)
            _apply_direct_dialogue_results(
                actor_sim_info,
                target_sim_info,
                spoken_text,
                clean_text,
                anim_category,
                delta_fr,
                delta_rom,
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

    # 1. Apply relationship change
    if delta_fr != 0 or delta_rom != 0:
        apply_chat_relationship_impact(actor_sim_info, target_sim_info, delta_fr=delta_fr, delta_rom=delta_rom)

    # 2. Trigger social animation
    try:
        actor_sim = actor_sim_info.get_sim_instance() if hasattr(actor_sim_info, "get_sim_instance") else None
        target_sim = target_sim_info.get_sim_instance() if hasattr(target_sim_info, "get_sim_instance") else None
        if actor_sim is not None and target_sim is not None:
            play_direct_dialogue_animation(actor_sim, target_sim, anim_category)
    except Exception as ex_anim:
        log_exception("Error playing animation", ex_anim)

    # 3. Format clean notification
    is_en = _is_en()
    if is_en:
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

    show_chat_notification(
        title=f"{target_name}:",
        text=notif_body,
        sim_info=target_sim_info,
        is_error=False,
    )

    # 4. Immediate summarization after conversation turn (actions execute right away)
    _trigger_immediate_summarization(actor_sim_info, target_sim_info)
