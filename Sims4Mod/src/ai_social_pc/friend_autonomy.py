"""
friend_autonomy.py
Autonomous Friend Messaging Module for AISocialPC.
Handles spontaneous incoming messages from friends (relationship 'Friends and above')
in direct 1-on-1 chats without prior player prompt.
"""
import os
import json
import random
import threading
import http.client
from typing import Dict, Any, List, Optional, Tuple

try:
    import services
    import alarms
    from date_and_time import create_time_span
except ImportError:
    services = None
    alarms = None
    create_time_span = None

from ai_social_pc.logger import log, log_exception
from ai_social_pc.localization import is_english


def _is_en() -> bool:
    try:
        return is_english()
    except Exception:
        return False

from ai_social_pc.ui_chat import (
    is_sim_online,
    show_chat_notification,
    get_recipient_display_name,
    get_available_contacts,
    is_sim_an_animal,
)
from ai_social_pc.chat_manager import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    add_session_message,
    get_session_history,
    has_player_ever_messaged,
    get_current_sim_absolute_days,
    get_current_sim_time,
    _build_sim_profile_summary,
    get_sim_work_or_school_status,
    get_relative_day_label,
    strip_emojis,
    parse_and_strip_relationship_tags,
)

_friend_autonomy_alarm_handle = None
_is_friend_autonomy_busy = False

# friend_id -> total_sim_minutes when last spontaneous message was sent
_last_friend_autonomy_time: Dict[int, int] = {}
_last_any_friend_time: int = -9999


def is_friend_autonomy_enabled() -> bool:
    """Checks whether friend autonomy is enabled in mod config."""
    try:
        from ai_thought_reader.config import load_config
        cfg = load_config()
        return bool(cfg.get("friend_autonomy_enabled", True))
    except Exception:
        return True


def is_sim_friend_or_above(actor_sim_info, target_sim_info) -> Tuple[bool, str, float]:
    """
    Determines if target_sim_info has a relationship with actor_sim_info of 'Friends and higher'.
    Returns (is_friend_or_above, relationship_title, friendship_score).
    Strictly requires friendship score >= 35 OR verified friend/romance bits, and excludes acquaintances/enemies.
    """
    if actor_sim_info is None or target_sim_info is None:
        return False, "Неизвестно", 0.0

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    target_id = getattr(target_sim_info, "sim_id", 0)
    if not actor_id or not target_id or actor_id == target_id:
        return False, "Сам с собой", 0.0

    if is_sim_an_animal(actor_sim_info) or is_sim_an_animal(target_sim_info):
        return False, "Животное", 0.0

    # 1. Friendship score & bits from relationship tracker
    f_score = 0.0
    rel_tracker = getattr(actor_sim_info, "relationship_tracker", None)
    bits_names = []
    if rel_tracker is not None:
        try:
            f_score = float(rel_tracker.get_relationship_score(target_id))
        except Exception:
            f_score = 0.0
        try:
            bits = rel_tracker.get_all_bits(target_id)
            if bits:
                bits_names = [getattr(b, "__name__", str(b)).lower() for b in bits]
        except Exception:
            pass

    # Exclude enemies, disliked, despised
    for b in bits_names:
        if any(k in b for k in ["nemesis", "enemy", "enemies", "disliked", "despised"]):
            return False, "Враг / Неприязнь", f_score
    if f_score < 0:
        return False, "Враг / Неприязнь", f_score

    # 2. Rich relationship string via context if available
    rel_desc = ""
    try:
        from ai_thought_reader.context import get_relationship_between_sims
        rel_desc = get_relationship_between_sims(target_sim_info, actor_sim_info)
    except Exception:
        pass

    if not rel_desc:
        rel_desc = "Друг" if f_score >= 35.0 else "Знакомый"

    rel_desc_lower = rel_desc.lower()

    # Strangers and pure acquaintances are NEVER "friend and above"
    if "незнаком" in rel_desc_lower:
        return False, rel_desc, f_score
    if ("знаком" in rel_desc_lower) and f_score < 35.0:
        return False, rel_desc, f_score

    # 3. Check for genuine friend bits (do NOT use simple 'friend in bits_str' because
    # 'friend' is a substring of 'relationshipbit_friendship_acquaintance'!)
    has_high_friend_bit = False
    for b in bits_names:
        if any(skip in b for skip in ["acquaintance", "neutral", "stranger", "has_met", "introduced"]):
            continue
        if any(g in b for g in ["best_friend", "bestfriend", "bff", "good_friends", "goodfriends", "good_friend"]):
            has_high_friend_bit = True
            break
        if b in ["friendship_friend", "relationshipbit_friendship_friend"] or b.endswith("_friend"):
            has_high_friend_bit = True
            break

    # Romance / Marriage partner bits
    has_romance_partner_bit = False
    for b in bits_names:
        if any(r in b for r in ["spouse", "husband", "wife", "married", "engaged", "fiance", "sweetheart", "significant_other", "dating", "lovers"]):
            has_romance_partner_bit = True
            break

    # Positive friend/partner titles (excluding 'знакомый')
    positive_keywords = ["друг", "подруг", "лучш", "хорош", "муж", "жена", "возлюблен", "невест", "жених", "парень", "девушка", "любим"]
    title_has_friend_or_above = any(k in rel_desc_lower for k in positive_keywords) and not ("знаком" in rel_desc_lower)

    # STRICT CRITERIA FOR "ДРУГ И ВЫШЕ":
    # 1. Friendship score >= 35 (the official Sims 4 threshold for Friend)
    # 2. OR verified high friend bit (Good Friend, Best Friend)
    # 3. OR romance partner bit with positive friendship (>= 20)
    # 4. OR title has friend/partner and score >= 30
    if f_score >= 35.0:
        return True, rel_desc, f_score

    if has_high_friend_bit and f_score >= 25.0:
        return True, rel_desc, f_score

    if has_romance_partner_bit and f_score >= 20.0:
        return True, rel_desc, f_score

    if title_has_friend_or_above and f_score >= 30.0:
        return True, rel_desc, f_score

    return False, rel_desc, f_score


def _on_friend_autonomy_tick(_):
    """
    Periodic tick (approx every 60 sim-minutes).
    Evaluates whether an eligible friend (friends and above) should send a spontaneous message to the player.
    """
    global _is_friend_autonomy_busy, _last_any_friend_time
    if _is_friend_autonomy_busy:
        return

    if not is_friend_autonomy_enabled():
        return

    if services is None:
        return

    try:
        client_mgr = services.client_manager()
        if client_mgr is None:
            return
        client = client_mgr.get_first_client()
        if client is None:
            return
        actor_sim_info = getattr(client, "active_sim_info", None)
        if actor_sim_info is None and client.active_sim is not None:
            actor_sim_info = getattr(client.active_sim, "sim_info", None)
        if actor_sim_info is None:
            return

        actor_id = getattr(actor_sim_info, "sim_id", 0)
        abs_day = get_current_sim_absolute_days()
        time_str = get_current_sim_time()
        try:
            h, m = [int(x) for x in time_str.split(":")]
            cur_minute = abs_day * 1440 + h * 60 + m
        except Exception:
            cur_minute = abs_day * 1440

        # Global cooldown between any friend spontaneous messages: at least 90 sim-minutes
        if 0 <= (cur_minute - _last_any_friend_time) < 90:
            return

        contacts = get_available_contacts(actor_sim_info, include_strangers=False)
        if not contacts:
            return

        eligible_friends = []
        for tgt in contacts:
            tgt_id = getattr(tgt, "sim_id", 0)

            # Spam prevention: Friend can ONLY write if player has messaged them at least once!
            if not has_player_ever_messaged(actor_id, tgt_id):
                continue

            # Per-friend cooldown: 180 sim-minutes (3 sim-hours)
            last_t = _last_friend_autonomy_time.get(tgt_id, -9999)
            if 0 <= (cur_minute - last_t) < 180:
                continue

            is_f, rel_title, score = is_sim_friend_or_above(actor_sim_info, tgt)
            if not is_f:
                continue

            ws_status = get_sim_work_or_school_status(tgt)
            if is_sim_online(tgt) and not ws_status.get("is_busy", False):
                eligible_friends.append((tgt, rel_title, score))

        if not eligible_friends:
            return

        # Random chance to send message this tick (50%)
        if random.random() > 0.50:
            return

        # Pick random friend
        chosen_sim_info, chosen_rel_title, _ = random.choice(eligible_friends)
        chosen_id = getattr(chosen_sim_info, "sim_id", 0)

        _last_friend_autonomy_time[chosen_id] = cur_minute
        _last_any_friend_time = cur_minute
        _is_friend_autonomy_busy = True

        f_name = get_recipient_display_name(chosen_sim_info)
        log(f"[FRIEND AUTONOMY] Triggering spontaneous incoming message from friend '{f_name}' ({chosen_rel_title}).")
        _dispatch_friend_chat(actor_sim_info, chosen_sim_info, chosen_rel_title)

    except Exception as e:
        log_exception("Error in _on_friend_autonomy_tick", e)


def _dispatch_friend_chat(actor_sim_info, friend_sim_info, rel_title: str):
    """Spawns background worker thread for LLM generation of friend message."""
    t = threading.Thread(
        target=_worker_friend_chat,
        args=(actor_sim_info, friend_sim_info, rel_title),
        daemon=True,
        name="AISocialPC-FriendAutonomyWorker",
    )
    t.start()


def _worker_friend_chat(actor_sim_info, friend_sim_info, rel_title: str):
    global _is_friend_autonomy_busy
    try:
        actor_id = getattr(actor_sim_info, "sim_id", 0)
        friend_id = getattr(friend_sim_info, "sim_id", 0)

        actor_name = get_recipient_display_name(actor_sim_info)
        friend_name = get_recipient_display_name(friend_sim_info)

        actor_profile = _build_sim_profile_summary(actor_sim_info, is_actor=True)
        friend_profile = _build_sim_profile_summary(friend_sim_info, is_actor=False)

        memories = ""
        try:
            from ai_social_pc.memory_manager import format_memories_for_prompt
            mem = format_memories_for_prompt(actor_id, friend_id)
            memories = mem if mem else ""
        except Exception:
            memories = ""

        cur_day = get_current_sim_absolute_days()
        raw_history = list(get_session_history(actor_id, friend_id))
        formatted_messages = []
        for msg in raw_history[-10:]:
            s = msg.get("sender", "")
            t = msg.get("text", "")
            m_time = msg.get("time", "")
            m_day = msg.get("abs_day", cur_day)
            m_dow = msg.get("dow", "")
            day_lbl = get_relative_day_label(m_day, cur_day, m_dow)
            prefix = "[{} {}] ".format(day_lbl, m_time) if (day_lbl or m_time) else ""
            formatted_messages.append({
                "sender": s,
                "text": t,
                "time": m_time,
                "day": day_lbl,
                "formatted_line": "- {}{}: {}".format(prefix, s, t),
            })

        payload = {
            "type": "friend_chat",
            "friend_name": friend_name,
            "friend_id": friend_id,
            "friend_info": friend_profile,
            "actor_name": actor_name,
            "actor_id": actor_id,
            "actor_info": actor_profile,
            "relationship": rel_title,
            "memories": memories,
            "messages": formatted_messages,
        }

        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=120)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
        }
        conn.request("POST", "/friend_chat", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")
        conn.close()

        if resp.status == 200:
            res_json = json.loads(resp_data)
            reply_text = res_json.get("reply", "") or res_json.get("text", "")
            if reply_text:
                from ai_social_pc.main_thread import run_on_main_thread
                run_on_main_thread(_apply_friend_dialogue_results, actor_sim_info, friend_sim_info, reply_text)
        else:
            log(f"[FRIEND AUTONOMY] Failed bridge request (HTTP {resp.status}): {resp_data[:200]}", level="WARN")
            is_en = _is_en()
            err_title = "Bridge Error" if is_en else "Ошибка моста"
            err_text = f"AI Bridge returned error ({resp.status}). Check bridge console window." if is_en else f"AI Bridge вернул ошибку ({resp.status}). Проверьте окно консоли моста."
            from ai_social_pc.main_thread import run_on_main_thread
            run_on_main_thread(show_chat_notification, title=err_title, text=err_text, sim_info=friend_sim_info, is_error=True)

    except Exception as e:
        log_exception("Error in _worker_friend_chat", e)
    finally:
        _is_friend_autonomy_busy = False


def _apply_friend_dialogue_results(actor_sim_info, friend_sim_info, raw_reply: str):
    """
    Appends generated incoming friend message to direct session history and displays notification.
    """
    try:
        actor_id = getattr(actor_sim_info, "sim_id", 0)
        friend_id = getattr(friend_sim_info, "sim_id", 0)
        friend_name = get_recipient_display_name(friend_sim_info)

        clean_text, _, _ = parse_and_strip_relationship_tags(strip_emojis(raw_reply))
        if not clean_text:
            return

        # Add to direct 1-on-1 session history
        add_session_message(
            actor_id=actor_id,
            target_id=friend_id,
            sender=friend_name,
            text=clean_text,
        )

        log(f"[FRIEND AUTONOMY] Added incoming message from '{friend_name}' to actor {actor_id}: '{clean_text}'")

        # Show notification popup with friend's 3D portrait
        is_en = _is_en()
        title = f"Direct Message: {friend_name}" if is_en else f"Личное сообщение: {friend_name}"
        show_chat_notification(
            title=title,
            text=clean_text,
            sim_info=friend_sim_info,
            is_error=False,
        )

    except Exception as e:
        log_exception("Error applying friend dialogue results", e)


def start_friend_autonomy_alarm():
    """Initializes repeating in-game alarm for friend spontaneous messages."""
    global _friend_autonomy_alarm_handle
    if alarms is None or create_time_span is None or services is None:
        return

    try:
        if _friend_autonomy_alarm_handle is not None:
            return

        zone_inst = services.current_zone() if services is not None else None
        if zone_inst is None:
            return

        interval_mins = 60
        time_span = create_time_span(minutes=interval_mins)
        _friend_autonomy_alarm_handle = alarms.add_alarm(
            zone_inst,
            time_span,
            _on_friend_autonomy_tick,
            repeating=True,
            use_sleep_time=True,
            cross_zone=True,
        )
        log(f"[FRIEND AUTONOMY] Repeating alarm initialized (checks every {interval_mins} sim-minutes).")
    except Exception as e:
        log_exception("Failed to start friend autonomy alarm", e)


def stop_friend_autonomy_alarm():
    """Stops the repeating in-game alarm."""
    global _friend_autonomy_alarm_handle
    if alarms is not None and _friend_autonomy_alarm_handle is not None:
        try:
            alarms.cancel_alarm(_friend_autonomy_alarm_handle)
        except Exception:
            pass
        _friend_autonomy_alarm_handle = None


def trigger_friend_autonomy(force: bool = True, target_friend_filter: str = "") -> Tuple[bool, str]:
    """
    Triggers an immediate spontaneous message from a friend (useful for cheat commands).
    If force=True, ignores the 3-hour cooldown and probability roll.
    If target_friend_filter is provided, matches friend by name.
    Returns (success, message).
    """
    global _is_friend_autonomy_busy, _last_any_friend_time
    is_en = _is_en()
    if _is_friend_autonomy_busy:
        return False, "AI message generation is already in progress. Please wait a few seconds." if is_en else "Система уже генерирует сообщение от ИИ. Подождите пару секунд."

    if services is None:
        return False, "Game services unavailable (services is None)." if is_en else "Игровые службы недоступны (services is None)."

    try:
        client_mgr = services.client_manager()
        if client_mgr is None:
            return False, "Client manager unavailable." if is_en else "Менеджер клиентов недоступен."
        client = client_mgr.get_first_client()
        if client is None:
            return False, "Client not found." if is_en else "Клиент не найден."
        actor_sim_info = getattr(client, "active_sim_info", None)
        if actor_sim_info is None and client.active_sim is not None:
            actor_sim_info = getattr(client.active_sim, "sim_info", None)
        if actor_sim_info is None:
            return False, "Active Sim is not selected." if is_en else "Активный сим не выбран."

        actor_id = getattr(actor_sim_info, "sim_id", 0)
        actor_name = get_recipient_display_name(actor_sim_info)
        contacts = get_available_contacts(actor_sim_info, include_strangers=False)
        if not contacts:
            return False, f"Sim {actor_name} has no contacts. Meet someone in the game first!" if is_en else f"У персонажа {actor_name} нет знакомых. Познакомьтесь с кем-нибудь в игре!"

        abs_day = get_current_sim_absolute_days()
        time_str = get_current_sim_time()
        try:
            h, m = [int(x) for x in time_str.split(":")]
            cur_minute = abs_day * 1440 + h * 60 + m
        except Exception:
            cur_minute = abs_day * 1440

        filter_str = (target_friend_filter or "").strip().lower()
        eligible_candidates = []
        rejection_reasons = []

        for tgt in contacts:
            tgt_name = get_recipient_display_name(tgt)
            tgt_id = getattr(tgt, "sim_id", 0)

            if filter_str and (filter_str not in tgt_name.lower()):
                continue

            is_f, rel_title, score = is_sim_friend_or_above(actor_sim_info, tgt)
            if not is_f:
                if filter_str:
                    if is_en:
                        rejection_reasons.append(f"{tgt_name}: status '{rel_title}' (friendship: {round(score, 1)}). Requires 'Friend' and above (35+ score).")
                    else:
                        rejection_reasons.append(f"{tgt_name}: статус «{rel_title}» (очки дружбы: {round(score, 1)}). Нужен статус «Друг» и выше (очки 35+).")
                continue

            ws_status = get_sim_work_or_school_status(tgt)
            online = is_sim_online(tgt)
            busy = ws_status.get("is_busy", False)

            if not online or busy:
                if is_en:
                    status_desc = "at work/school" if busy else "offline/asleep"
                    rejection_reasons.append(f"{tgt_name} ({rel_title}): {status_desc}.")
                else:
                    status_desc = "на работе/учебе" if busy else "не в сети/спит"
                    rejection_reasons.append(f"{tgt_name} ({rel_title}): {status_desc}.")
                continue

            if not force:
                if not has_player_ever_messaged(actor_id, tgt_id):
                    if is_en:
                        rejection_reasons.append(f"{tgt_name} ({rel_title}): You haven't texted this friend yet (friends text back only after your 1st message).")
                    else:
                        rejection_reasons.append(f"{tgt_name} ({rel_title}): Вы ещё ни разу не писали этому другу в чат (друг может написать только после вашего 1-го сообщения).")
                    continue

                last_t = _last_friend_autonomy_time.get(tgt_id, -9999)
                diff = cur_minute - last_t
                if 0 <= diff < 180:
                    if is_en:
                        rejection_reasons.append(f"{tgt_name}: cooldown for another {180 - diff} sim-min.")
                    else:
                        rejection_reasons.append(f"{tgt_name}: кулдаун ещё {180 - diff} сим-мин.")
                    continue

            eligible_candidates.append((tgt, rel_title, score))

        if not eligible_candidates:
            if is_en:
                msg = "No suitable online friend found to send a message:\n"
                if rejection_reasons:
                    msg += "\n".join(rejection_reasons[:5])
                else:
                    msg += f"Sim {actor_name} has no Sims with status 'Friend or above' among available contacts."
            else:
                msg = "Не найден подходящий друг онлайн для отправки сообщения:\n"
                if rejection_reasons:
                    msg += "\n".join(rejection_reasons[:5])
                else:
                    msg += f"У сима {actor_name} нет симов со статусом «Друзья и выше» среди доступных контактов."
            return False, msg

        # Pick first or random
        chosen_sim_info, chosen_rel_title, score = eligible_candidates[0]
        chosen_id = getattr(chosen_sim_info, "sim_id", 0)
        chosen_name = get_recipient_display_name(chosen_sim_info)

        _last_friend_autonomy_time[chosen_id] = cur_minute
        _last_any_friend_time = cur_minute
        _is_friend_autonomy_busy = True

        log(f"[FRIEND AUTONOMY] Manual trigger: starting message from '{chosen_name}' ({chosen_rel_title}).")
        _dispatch_friend_chat(actor_sim_info, chosen_sim_info, chosen_rel_title)
        if is_en:
            return True, f"Started generating message from friend: {chosen_name} ({chosen_rel_title}, friendship: {round(score, 1)}). Expecting popup message..."
        else:
            return True, f"Запущена генерация сообщения от друга: {chosen_name} ({chosen_rel_title}, дружба: {round(score, 1)}). Ожидайте всплывающего сообщения..."

    except Exception as e:
        log_exception("Error in trigger_friend_autonomy", e)
        return False, f"Error on trigger: {e}" if is_en else f"Ошибка при запуске: {e}"


def get_friend_autonomy_debug_info() -> str:
    """Returns diagnostic text about friend autonomy and eligible friends."""
    is_en = _is_en()
    lines = []
    lines.append("=== FRIEND AUTONOMY STATUS (1-ON-1) ===" if is_en else "=== СТАТУС АВТОНОМНОСТИ ДРУЗЕЙ (1-НА-1) ===")
    lines.append(f"• Enabled in config: {'YES' if is_friend_autonomy_enabled() else 'NO'}" if is_en else f"• Включено в настройках: {'ДА' if is_friend_autonomy_enabled() else 'НЕТ'}")
    lines.append(f"• Game timer (Alarm): {'ACTIVE' if _friend_autonomy_alarm_handle is not None else 'NOT RUNNING'}" if is_en else f"• Игровой таймер (Alarm): {'АКТИВЕН' if _friend_autonomy_alarm_handle is not None else 'НЕ ЗАПУЩЕН'}")
    lines.append(f"• Generation currently busy: {'YES' if _is_friend_autonomy_busy else 'NO'}" if is_en else f"• Генерация сейчас занята: {'ДА' if _is_friend_autonomy_busy else 'НЕТ'}")

    if services is None:
        lines.append("• Game services unavailable." if is_en else "• Игровые службы недоступны.")
        return "\n".join(lines)

    client_mgr = services.client_manager()
    client = client_mgr.get_first_client() if client_mgr else None
    actor_info = getattr(client, "active_sim_info", None) if client else None
    if actor_info is None and client and client.active_sim:
        actor_info = getattr(client.active_sim, "sim_info", None)
    if actor_info is None:
        lines.append("• Active Sim is not selected." if is_en else "• Активный сим не выбран.")
        return "\n".join(lines)

    actor_id = getattr(actor_info, "sim_id", 0)
    actor_name = get_recipient_display_name(actor_info)
    lines.append(f"• Active Sim: {actor_name} (ID: {actor_id})" if is_en else f"• Активный сим: {actor_name} (ID: {actor_id})")

    abs_day = get_current_sim_absolute_days()
    time_str = get_current_sim_time()
    try:
        h, m = [int(x) for x in time_str.split(":")]
        cur_minute = abs_day * 1440 + h * 60 + m
    except Exception:
        cur_minute = abs_day * 1440
    lines.append(f"• Game time: Day {abs_day}, {time_str} (total {cur_minute} sim-min)" if is_en else f"• Игровое время: День {abs_day}, {time_str} (всего {cur_minute} сим-мин)")

    contacts = get_available_contacts(actor_info, include_strangers=False)
    lines.append(f"• Total known contacts: {len(contacts)}" if is_en else f"• Всего знакомых контактов: {len(contacts)}")

    friends_found = 0
    for idx, tgt in enumerate(contacts, 1):
        is_f, rel_title, score = is_sim_friend_or_above(actor_info, tgt)
        if not is_f:
            continue

        friends_found += 1
        tgt_id = getattr(tgt, "sim_id", 0)
        tgt_name = get_recipient_display_name(tgt)

        ws = get_sim_work_or_school_status(tgt)
        online = is_sim_online(tgt)
        busy = ws.get("is_busy", False)

        if is_en:
            if online and not busy:
                status_desc = "ONLINE (READY)"
            elif busy:
                status_desc = "AT WORK/SCHOOL"
            else:
                status_desc = "OFFLINE/ASLEEP"
        else:
            if online and not busy:
                status_desc = "В СЕТИ (ГОТОВ)"
            elif busy:
                status_desc = "НА РАБОТЕ/УЧЕБЕ"
            else:
                status_desc = "ОФФЛАЙН/СОН"

        last_t = _last_friend_autonomy_time.get(tgt_id, -9999)
        cd_left = max(0, 180 - (cur_minute - last_t)) if last_t > 0 else 0
        if is_en:
            cd_str = f"Cooldown: {cd_left} sim-min" if cd_left > 0 else "Ready for message"
            contacted = has_player_ever_messaged(actor_id, tgt_id)
            contact_str = "You messaged: YES (unlocked)" if contacted else "You messaged: NO (locked until 1st message)"
            lines.append(f"  [{friends_found}] {tgt_name} — {rel_title} (Friendship: {round(score, 1)})")
            lines.append(f"      Status: [{status_desc}] | {cd_str} | {contact_str}")
        else:
            cd_str = f"Кулдаун: {cd_left} сим-мин" if cd_left > 0 else "Готов к сообщению"
            contacted = has_player_ever_messaged(actor_id, tgt_id)
            contact_str = "Вы писали: ДА (разблокирован)" if contacted else "Вы писали: НЕТ (заблокирован до 1-го сообщения)"
            lines.append(f"  [{friends_found}] {tgt_name} — {rel_title} (Дружба: {round(score, 1)})")
            lines.append(f"      Статус: [{status_desc}] | {cd_str} | {contact_str}")

    if friends_found == 0:
        lines.append("  (Active Sim has no Sims with status 'Friend' or above yet)" if is_en else "  (У активного персонажа пока нет симов со статусом «Друг» и выше)")

    return "\n".join(lines)
