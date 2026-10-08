"""
delayed_replies.py
Manages queued messages sent to Sims while they are offline (asleep or away).
Periodically checks (via an in-game alarm every 30 sim-minutes) if any recipient Sim
has woken up and come online, triggering a natural delayed reply with morning/evening context.
"""

from typing import Dict, Tuple, Any, List, Optional
import threading
from ai_social_pc.logger import log, log_exception
from ai_social_pc.localization import is_english


def _is_en() -> bool:
    try:
        return is_english()
    except Exception:
        return False


try:
    import alarms
    import services
    from date_and_time import create_time_span
except ImportError:
    alarms = None
    services = None
    create_time_span = None

# Key: (actor_sim_id, recipient_sim_id)
# Value: dict containing sent time, last message, etc.
_PENDING_REPLIES: Dict[Tuple[int, int], Dict[str, Any]] = {}

# Key: group_id (str)
# Value: dict containing group_id, actor_id, sent_sim_time, sent_hour, last_message
_PENDING_GROUP_REPLIES: Dict[str, Dict[str, Any]] = {}
_delayed_alarm_handle = None


def enqueue_pending_reply(actor_id: int, recipient_id: int, message_text: str):
    """
    Enqueues or updates an unreplied message sent to an offline Sim.
    If multiple messages are sent to the same offline Sim, we preserve the original
    sent time (so the Sim knows when the dialogue began) and update the latest message text.
    """
    if not actor_id or not recipient_id:
        return

    from ai_social_pc.chat_manager import get_current_sim_time
    from ai_social_pc.ui_chat import get_current_sim_hour

    key = (actor_id, recipient_id)
    sent_time = get_current_sim_time()
    sent_hour = get_current_sim_hour()

    if key in _PENDING_REPLIES:
        _PENDING_REPLIES[key]["last_message"] = message_text
        log(f"[DELAYED QUEUE] Updated pending message for Sim {recipient_id} from actor {actor_id}")
    else:
        _PENDING_REPLIES[key] = {
            "actor_id": actor_id,
            "recipient_id": recipient_id,
            "sent_sim_time": sent_time,
            "sent_hour": sent_hour,
            "last_message": message_text,
        }
        log(f"[DELAYED QUEUE] Enqueued pending reply from Sim {recipient_id} for actor {actor_id} (sent at {sent_time})")

    # Ensure alarm is running
    start_delayed_replies_alarm()


def enqueue_pending_group_reply(group_id: str, actor_id: int, message_text: str):
    """
    Enqueues or updates an unreplied group message sent while members are offline/asleep.
    """
    if not group_id:
        return

    from ai_social_pc.chat_manager import get_current_sim_time
    from ai_social_pc.ui_chat import get_current_sim_hour

    sent_time = get_current_sim_time()
    sent_hour = get_current_sim_hour()

    if group_id in _PENDING_GROUP_REPLIES:
        _PENDING_GROUP_REPLIES[group_id]["last_message"] = message_text
        log(f"[DELAYED GROUP QUEUE] Updated pending group message for {group_id}")
    else:
        _PENDING_GROUP_REPLIES[group_id] = {
            "group_id": group_id,
            "actor_id": actor_id,
            "sent_sim_time": sent_time,
            "sent_hour": sent_hour,
            "last_message": message_text,
        }
        log(f"[DELAYED GROUP QUEUE] Enqueued pending group reply for {group_id} (sent at {sent_time})")

    start_delayed_replies_alarm()


def remove_pending_reply(actor_id: int, recipient_id: int):
    """Removes a pending reply from queue (e.g. when chat history is wiped)."""
    key = (actor_id, recipient_id)
    if key in _PENDING_REPLIES:
        _PENDING_REPLIES.pop(key, None)
        log(f"[DELAYED QUEUE] Removed pending reply for key {key}")


def remove_pending_group_reply(group_id: str):
    """Removes a pending group reply from queue (e.g. when group history is wiped or group deleted)."""
    if group_id in _PENDING_GROUP_REPLIES:
        _PENDING_GROUP_REPLIES.pop(group_id, None)
        log(f"[DELAYED GROUP QUEUE] Removed pending group reply for {group_id}")


def clear_all_pending_replies() -> int:
    """Clears all pending replies from queue and returns the count of cleared items."""
    count = len(_PENDING_REPLIES)
    _PENDING_REPLIES.clear()
    log(f"[DELAYED QUEUE] Cleared all {count} pending reply item(s).")
    return count


def clear_all_pending_group_replies() -> int:
    """Clears all pending group replies from queue."""
    count = len(_PENDING_GROUP_REPLIES)
    _PENDING_GROUP_REPLIES.clear()
    log(f"[DELAYED GROUP QUEUE] Cleared all {count} pending group reply item(s).")
    return count


def get_pending_replies_count() -> int:
    """Returns number of pending replies currently waiting in queue."""
    return len(_PENDING_REPLIES)


def get_pending_group_replies_count() -> int:
    """Returns number of pending group replies currently waiting in queue."""
    return len(_PENDING_GROUP_REPLIES)


_last_check_sim_minute = -1


def on_zone_update_check():
    """
    Called continuously from Zone.update simulation loop.
    Checks pending offline replies whenever in-game time advances by 3+ sim-minutes.
    100% reliable regardless of game speed (1, 2, 3) or time skipping.
    """
    global _last_check_sim_minute
    if not _PENDING_REPLIES and not _PENDING_GROUP_REPLIES:
        return

    try:
        from ai_social_pc.chat_manager import get_current_sim_absolute_days, get_current_sim_time
        from ai_social_pc.ui_chat import get_current_sim_hour

        abs_day = get_current_sim_absolute_days()
        hour = get_current_sim_hour()
        time_str = get_current_sim_time()
        try:
            minute = int(time_str.split(":")[1])
        except Exception:
            minute = 0

        cur_total_minute = abs_day * 1440 + hour * 60 + minute

        # Check every 3 sim-minutes, or reset if time jumped backwards
        if _last_check_sim_minute != -1 and 0 <= (cur_total_minute - _last_check_sim_minute) < 3:
            return

        _last_check_sim_minute = cur_total_minute
        check_and_process_pending_replies(force_all=False)
    except Exception as e:
        log_exception("Error in on_zone_update_check", e)


def get_all_pending_replies() -> List[Dict[str, Any]]:
    """Returns a copy of all pending reply items."""
    return list(_PENDING_REPLIES.values())


def start_delayed_replies_alarm():
    """
    Starts or ensures the repeating in-game alarm
    to check for Sims who have come online.
    """
    global _delayed_alarm_handle
    if alarms is None or create_time_span is None or services is None:
        return

    try:
        if _delayed_alarm_handle is not None:
            return

        zone_inst = services.current_zone() if services is not None else None
        if zone_inst is None:
            return

        interval_mins = 15
        time_span = create_time_span(minutes=interval_mins)
        _delayed_alarm_handle = alarms.add_alarm(
            zone_inst,
            time_span,
            _on_delayed_replies_tick,
            repeating=True,
            use_sleep_time=True,
            cross_zone=True,
        )
        log(f"[DELAYED REPLIES] Repeating alarm initialized (checks every {interval_mins} sim-minutes).")
    except Exception as e:
        log_exception("Failed to start delayed replies alarm", e)


def stop_delayed_replies_alarm():
    """Stops the repeating in-game alarm."""
    global _delayed_alarm_handle
    if alarms is not None and _delayed_alarm_handle is not None:
        try:
            alarms.cancel_alarm(_delayed_alarm_handle)
        except Exception:
            pass
        _delayed_alarm_handle = None
        log("[DELAYED REPLIES] Alarm cancelled.")


def _on_delayed_replies_tick(alarm_handle=None):
    """Callback fired by TS4 repeating alarm."""
    try:
        check_and_process_pending_replies(force_all=False)
    except Exception as e:
        log_exception("Error during delayed replies tick", e)


def check_and_process_pending_replies(force_all: bool = False):
    """
    Checks all pending replies. If a recipient is now online (or force_all=True),
    pops them from the queue and triggers an asynchronous AI reply.
    """
    if not _PENDING_REPLIES and not _PENDING_GROUP_REPLIES:
        return

    if services is None:
        return

    sim_info_mgr = services.sim_info_manager()
    if sim_info_mgr is None:
        return

    from ai_social_pc.ui_chat import is_sim_online, _detect_sim_occult, get_current_sim_hour
    from ai_social_pc.chat_manager import get_sim_work_or_school_status

    keys_to_check = list(_PENDING_REPLIES.keys())
    stagger_delay = 0.0
    hour = get_current_sim_hour()

    for key in keys_to_check:
        if key not in _PENDING_REPLIES:
            continue

        entry = _PENDING_REPLIES[key]
        actor_id, recipient_id = key

        recipient_info = sim_info_mgr.get(recipient_id)
        actor_info = sim_info_mgr.get(actor_id)

        if recipient_info is None or actor_info is None:
            # Sim no longer exists in world
            _PENDING_REPLIES.pop(key, None)
            continue

        ws_recip = get_sim_work_or_school_status(recipient_info)
        online = force_all or (is_sim_online(recipient_info) and not ws_recip.get("is_busy", False))
        occult = _detect_sim_occult(recipient_info)
        r_f = getattr(recipient_info, "first_name", "") or ""
        r_l = getattr(recipient_info, "last_name", "") or ""
        r_name = f"{r_f} {r_l}".strip() or f"Сим {recipient_id}"

        if online:
            log(f"[DELAYED REPLIES] {r_name} ({occult}) is online at {hour:02d}:00! Triggering response (stagger: {stagger_delay:.1f}s)")
            _PENDING_REPLIES.pop(key, None)
            _trigger_delayed_reply(actor_info, recipient_info, entry, delay_seconds=stagger_delay)
            stagger_delay += 2.5
        else:
            log(f"[DELAYED REPLIES] {r_name} ({occult}) is still offline at {hour:02d}:00. Waiting next check.")

    # Check pending group replies
    if _PENDING_GROUP_REPLIES:
        from ai_social_pc.group_manager import get_group_by_id

        gkeys = list(_PENDING_GROUP_REPLIES.keys())
        for gid in gkeys:
            if gid not in _PENDING_GROUP_REPLIES:
                continue

            entry = _PENDING_GROUP_REPLIES[gid]
            actor_id = entry.get("actor_id", 0)
            actor_info = sim_info_mgr.get(actor_id)
            group_data = get_group_by_id(gid)

            if group_data is None or actor_info is None:
                _PENDING_GROUP_REPLIES.pop(gid, None)
                continue

            # Check if at least 1 member (other than actor) has woken up
            any_online = False
            for mid in group_data.get("member_ids", []):
                if mid == actor_id:
                    continue
                s = sim_info_mgr.get(mid)
                if s:
                    ws = get_sim_work_or_school_status(s)
                    if (force_all or is_sim_online(s)) and not ws.get("is_busy", False):
                        any_online = True
                        break

            if any_online:
                g_name = group_data.get("name", "Групповой чат")
                log(f"[DELAYED GROUP] Group '{g_name}' has awakened members at {hour:02d}:00! Triggering morning reply (stagger: {stagger_delay:.1f}s)")
                _PENDING_GROUP_REPLIES.pop(gid, None)
                _trigger_delayed_group_reply(actor_info, group_data, entry, delay_seconds=stagger_delay)
                stagger_delay += 3.0
            else:
                log(f"[DELAYED GROUP] All members of group '{gid}' are still offline at {hour:02d}:00.")


def _trigger_delayed_reply(actor_info, recipient_info, entry: Dict[str, Any], delay_seconds: float = 0.0):
    """Dispatches delayed response generation, optionally staggered by delay_seconds."""
    def _worker():
        try:
            _execute_delayed_reply(actor_info, recipient_info, entry)
        except Exception as e:
            log_exception("Error executing delayed reply", e)

    if delay_seconds > 0.0:
        timer = threading.Timer(delay_seconds, _worker)
        timer.daemon = True
        timer.start()
    else:
        _worker()


def _execute_delayed_reply(actor_sim_info, recipient_sim_info, entry: Dict[str, Any]):
    """
    Builds context, invokes Synapse AI Bridge for the delayed message,
    and displays the in-game notification upon completion or failure.
    """
    from ai_social_pc.chat_manager import (
        get_current_sim_time,
        send_chat_message_async,
    )
    from ai_social_pc.ui_chat import (
        get_recipient_display_name,
        show_chat_notification,
        _detect_sim_occult,
    )

    is_en = _is_en()
    if is_en:
        sent_time_default = "earlier"
    else:
        sent_time_default = "ранее"
    sent_time = entry.get("sent_sim_time", sent_time_default)
    last_message = entry.get("last_message", "")
    current_time = get_current_sim_time()
    recipient_name = get_recipient_display_name(recipient_sim_info)
    sender_name = get_recipient_display_name(actor_sim_info)
    occult = _detect_sim_occult(recipient_sim_info)

    if is_en:
        if occult == "vampire":
            extra_context = (
                f"Interlocutor {sender_name} sent you messages during the day (at {sent_time}) while you were asleep and hiding from the sun. "
                f"Now it is evening/night ({current_time}), you came online, just saw the message from {sender_name} and are replying. "
                f"IMPORTANT: {sender_name} was awake — YOU ({recipient_name}) were asleep. Reply naturally in the first person having just woken up."
            )
        else:
            extra_context = (
                f"Interlocutor {sender_name} sent you messages at night (at {sent_time}) while you were asleep. "
                f"Now it is morning ({current_time}), you woke up, came online, just saw the message from {sender_name} and are replying. "
                f"IMPORTANT: {sender_name} was awake — YOU ({recipient_name}) were asleep. Reply naturally in the first person having just woken up."
            )
    else:
        if occult == "vampire":
            extra_context = (
                f"Собеседник {sender_name} отправил вам входящие сообщения днем (в {sent_time}), пока вы спали и скрывались от солнца. "
                f"Сейчас вечер/ночь ({current_time}), вы зашли в сеть, только что увидели сообщение от {sender_name} и отвечаете ему. "
                f"ВАЖНО: {sender_name} не спал — спали ВЫ ({recipient_name}). Ответьте естественно от первого лица с учетом пробуждения."
            )
        else:
            extra_context = (
                f"Собеседник {sender_name} отправил вам входящие сообщения ночью (в {sent_time}), когда вы спали. "
                f"Сейчас утро ({current_time}), вы проснулись, зашли в сеть, только что увидели сообщение от {sender_name} и отвечаете ему. "
                f"ВАЖНО: {sender_name} не спал — спали ВЫ ({recipient_name}). Ответьте естественно от первого лица с учетом утреннего пробуждения."
            )

    from ai_social_pc.chat_manager import get_sim_work_or_school_status
    ws_status = get_sim_work_or_school_status(recipient_sim_info)
    if ws_status and ws_status.get("is_busy"):
        if is_en:
            extra_context += f"\nAdditionally, right now you are {ws_status['detail_text']} and replying from there."
        else:
            extra_context += f"\nКроме того, прямо сейчас вы находитесь {ws_status['detail_text']} и отвечаете оттуда."

    log(f"[DELAYED REPLY] Sending AI request for {recipient_name} with extra context: '{extra_context[:60]}...'")

    def _on_reply(reply_text, success):
        if success:
            log(f"[DELAYED REPLY] Delivered reply from {recipient_name}: '{reply_text}'")
            # Show notification popup in upper right corner with Sim's portrait
            show_chat_notification(
                title=recipient_name,
                text=reply_text,
                sim_info=recipient_sim_info,
                is_error=False,
            )
        else:
            log(f"[DELAYED REPLY] Failed reply from {recipient_name}: {reply_text}", level="ERROR")
            err_title = "Messenger Error" if is_en else "Ошибка мессенджера"
            err_text = (
                f"A problem occurred: message from {recipient_name} could not be sent due to connection failure."
                if is_en else
                f"Произошел баг: сообщение от {recipient_name} не было отправлено из-за сбоя связи."
            )
            show_chat_notification(
                title=err_title,
                text=err_text,
                sim_info=recipient_sim_info,
                is_error=True,
            )

    send_chat_message_async(
        actor_sim_info,
        recipient_sim_info,
        last_message,
        _on_reply,
        extra_context=extra_context,
    )


def _trigger_delayed_group_reply(actor_info, group_data: Dict[str, Any], entry: Dict[str, Any], delay_seconds: float = 0.0):
    """Dispatches delayed group response generation, optionally staggered by delay_seconds."""
    def _worker():
        try:
            _execute_delayed_group_reply(actor_info, group_data, entry)
        except Exception as e:
            log_exception("Error executing delayed group reply", e)

    if delay_seconds > 0.0:
        timer = threading.Timer(delay_seconds, _worker)
        timer.daemon = True
        timer.start()
    else:
        _worker()


def _execute_delayed_group_reply(actor_sim_info, group_data: Dict[str, Any], entry: Dict[str, Any]):
    """
    Builds morning awakening context for the group, invokes Synapse AI Bridge,
    appends replies to group history, applies discrete relationship changes,
    and displays in-game notification in The Sims 4.
    """
    from ai_social_pc.chat_manager import (
        get_current_sim_time,
        send_group_chat_message_async,
        apply_chat_relationship_impact,
    )
    from ai_social_pc.ui_chat import (
        get_recipient_display_name,
        show_chat_notification,
    )
    from ai_social_pc.group_manager import add_group_message

    is_en = _is_en()
    group_id = group_data.get("id", "")
    group_name = group_data.get("name", "Group" if is_en else "Групповой чат")
    sent_time = entry.get("sent_sim_time", "at night" if is_en else "ночью")
    last_message = entry.get("last_message", "")
    current_time = get_current_sim_time()
    sender_name = get_recipient_display_name(actor_sim_info)

    if is_en:
        extra_context = (
            f"MEMBERS WOKE UP IN THE MORNING: Interlocutor {sender_name} sent a message to this group during the night (at {sent_time}), when members were asleep. "
            f"Now it is morning ({current_time}), members woke up, opened the group chat, saw the message from {sender_name} and are replying to it. "
            f"IMPORTANT: Reply naturally in the first person having just woken up."
        )
    else:
        extra_context = (
            f"УЧАСТНИКИ ПРОСНУЛИСЬ УТРОМ: Собеседник {sender_name} отправил сообщение в эту группу ночью (в {sent_time}), когда участники спали. "
            f"Сейчас утро ({current_time}), участники проснулись, зашли в чат группы, увидели ночное сообщение от {sender_name} и отвечают на него. "
            f"ВАЖНО: Ответьте естественно от первого лица с учётом утреннего пробуждения."
        )

    log(f"[DELAYED GROUP] Sending AI request for group '{group_name}' with morning context: '{extra_context[:60]}...'")

    def _on_group_reply(reply_messages: List[Dict[str, Any]], is_success: bool, error_msg: str):
        if is_success and reply_messages:
            sim_mgr = services.sim_info_manager() if services is not None else None
            actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0

            for msg in reply_messages:
                m_sender = msg.get("sender", "Interlocutor" if is_en else "Собеседник")
                m_text = msg.get("text", "")
                d_fr = msg.get("delta_friendship", 0)
                d_rom = msg.get("delta_romance", 0)

                # Find Sim to record sender_id and apply relationship
                target_sim_info = None
                for mid in group_data.get("member_ids", []):
                    if mid == actor_id:
                        continue
                    s = sim_mgr.get(mid) if sim_mgr else None
                    if s:
                        s_name = get_recipient_display_name(s)
                        s_first = getattr(s, "first_name", "") or ""
                        if (m_sender.lower() in s_name.lower()) or (s_first and s_first.lower() in m_sender.lower()):
                            target_sim_info = s
                            break

                t_sim_id = getattr(target_sim_info, "sim_id", 0) if target_sim_info else 0
                add_group_message(group_id, sender=m_sender, text=m_text, sender_id=t_sim_id, sender_name=m_sender)

                if target_sim_info is not None and (d_fr != 0 or d_rom != 0):
                    apply_chat_relationship_impact(actor_sim_info, target_sim_info, delta_fr=d_fr, delta_rom=d_rom)

            log(f"[DELAYED GROUP] Delivered {len(reply_messages)} reply messages to group '{group_name}'.")

            summary_lines = [f"{m.get('sender')}: {m.get('text')}" for m in reply_messages[:2]]
            grp_title = f"Group: {group_name}" if is_en else f"Группа: {group_name}"
            show_chat_notification(
                title=grp_title,
                text="\n".join(summary_lines),
                sim_info=actor_sim_info,
                is_error=False,
            )
        else:
            log(f"[DELAYED GROUP] Failed morning reply for group '{group_name}': {error_msg}", level="ERROR")
            err_title = "Messenger Error" if is_en else "Ошибка мессенджера"
            err_text = (
                f"An error occurred: failed to deliver morning reply to group '{group_name}'."
                if is_en else
                f"Произошел сбой: не удалось доставить утренний ответ в группу '{group_name}'."
            )
            show_chat_notification(
                title=err_title,
                text=err_text,
                sim_info=actor_sim_info,
                is_error=True,
            )

    send_group_chat_message_async(
        actor_sim_info=actor_sim_info,
        group_data=group_data,
        message_text=last_message,
        callback=_on_group_reply,
        extra_context=extra_context,
        force_all_online=True,
    )

