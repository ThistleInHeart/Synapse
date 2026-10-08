"""
NPC Group Autonomy Module for AISocialPC.
Handles spontaneous autonomous conversations between NPC group members
without direct player intervention.
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

from ai_social_pc.group_manager import (
    get_groups_for_sim,
    add_group_message,
    get_group_messages,
    get_group_topic,
)
from ai_social_pc.ui_chat import (
    is_sim_online,
    show_chat_notification,
    get_recipient_display_name,
    is_sim_an_animal,
)
from ai_social_pc.chat_manager import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    get_current_sim_absolute_days,
    get_current_sim_time,
    get_current_sim_day_of_week,
    _build_sim_profile_summary,
    get_sim_work_or_school_status,
    get_relative_day_label,
    get_chat_context_flag,
    strip_emojis,
    parse_and_strip_relationship_tags,
)

_npc_autonomy_alarm_handle = None
_is_npc_autonomy_busy = False
# group_id -> total_sim_minutes when last autonomous chat occurred
_last_group_autonomy_time = {}


def is_npc_autonomy_enabled() -> bool:
    """Checks whether NPC group autonomy is enabled in mod config."""
    try:
        from ai_thought_reader.config import load_config
        cfg = load_config()
        return bool(cfg.get("npc_group_autonomy_enabled", True))
    except Exception:
        return True


def _on_npc_autonomy_tick(_):
    """
    Called on repeating alarm (approx every 60 sim-minutes).
    Evaluates whether an autonomous chat between NPCs in a group should occur.
    """
    global _is_npc_autonomy_busy
    if _is_npc_autonomy_busy:
        return

    if not is_npc_autonomy_enabled():
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
        groups = get_groups_for_sim(actor_id)
        if not groups:
            return

        sim_mgr = services.sim_info_manager()
        if sim_mgr is None:
            return

        abs_day = get_current_sim_absolute_days()
        time_str = get_current_sim_time()
        try:
            h, m = [int(x) for x in time_str.split(":")]
            cur_minute = abs_day * 1440 + h * 60 + m
        except Exception:
            cur_minute = abs_day * 1440

        # Shuffle groups to give equal opportunity to different chats
        shuffled_groups = list(groups)
        random.shuffle(shuffled_groups)

        for grp in shuffled_groups:
            gid = grp.get("id", "")
            if not gid:
                continue

            # Cooldown per group: at least 180 sim-minutes (3 sim-hours)
            last_t = _last_group_autonomy_time.get(gid, -9999)
            if 0 <= (cur_minute - last_t) < 180:
                continue

            member_ids = grp.get("member_ids", [])
            online_npcs = []

            for mid in member_ids:
                if mid == actor_id:
                    continue
                s_info = sim_mgr.get(mid)
                if s_info is None:
                    continue

                ws_status = get_sim_work_or_school_status(s_info)
                if not is_sim_an_animal(s_info) and is_sim_online(s_info) and not ws_status.get("is_busy", False):
                    online_npcs.append(s_info)

            # Need at least 2 NPCs online to have a conversation between themselves
            if len(online_npcs) < 2:
                continue

            # Roll random chance (e.g. 60% chance to trigger conversation this tick)
            if random.random() > 0.60:
                continue

            _last_group_autonomy_time[gid] = cur_minute
            _is_npc_autonomy_busy = True
            log("[NPC AUTONOMY] Triggering spontaneous conversation in group '{}' with {} online NPCs.".format(grp.get('name'), len(online_npcs)))
            _dispatch_npc_group_chat(actor_sim_info, grp, online_npcs)
            break

    except Exception as e:
        log_exception("Error in _on_npc_autonomy_tick", e)


def _dispatch_npc_group_chat(actor_sim_info, group_data: Dict[str, Any], online_npcs: List[Any]):
    """Dispatches background worker thread for generating NPC dialogue."""
    t = threading.Thread(
        target=_worker_npc_group_chat,
        args=(actor_sim_info, group_data, online_npcs),
        daemon=True,
        name="AISocialPC-NPCAutonomyWorker",
    )
    t.start()


def _worker_npc_group_chat(actor_sim_info, group_data: Dict[str, Any], online_npcs: List[Any]):
    global _is_npc_autonomy_busy
    try:
        group_id = group_data.get("id", "")
        group_name = group_data.get("name", "Групповой чат")
        group_topic = (group_data.get("topic") or "").strip()
        if not group_topic and group_id:
            try:
                group_topic = get_group_topic(group_id)
            except Exception:
                pass

        participants = []
        for s_info in online_npcs:
            name = get_recipient_display_name(s_info)
            info = _build_sim_profile_summary(s_info, is_actor=False)
            mem = ""
            try:
                from ai_social_pc.memory_manager import format_memories_for_prompt
                actor_id = getattr(actor_sim_info, "sim_id", 0)
                s_id = getattr(s_info, "sim_id", 0)
                mem = format_memories_for_prompt(actor_id, s_id)
            except Exception:
                pass

            participants.append({
                "name": name,
                "sim_id": getattr(s_info, "sim_id", 0),
                "is_online": True,
                "info": info,
                "memories": mem,
            })

        # Recent history
        cur_day = get_current_sim_absolute_days()
        raw_history = list(get_group_messages(group_id))
        formatted_messages = []
        for msg in raw_history[-15:]:
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
            "type": "npc_group_chat",
            "group_name": group_name,
            "group_topic": group_topic,
            "participants": participants,
            "messages": formatted_messages,
        }

        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=120)
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }

        conn.request("POST", "/chat", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")

        try:
            resp_json = json.loads(resp_data)
        except Exception:
            resp_json = {}

        if resp.status == 200 and resp_json.get("success"):
            reply_messages = resp_json.get("messages", [])
            if reply_messages:
                from ai_social_pc.main_thread import run_on_main_thread
                run_on_main_thread(_apply_npc_dialogue_results, actor_sim_info, group_data, online_npcs, reply_messages)
            else:
                log("[NPC AUTONOMY] Bridge returned empty dialogue for group '{}'.".format(group_name))
        else:
            log("[NPC AUTONOMY] Failed bridge request (HTTP {}): {}".format(resp.status, resp_data[:200]), level="WARN")

    except Exception as e:
        log_exception("Error in _worker_npc_group_chat", e)
    finally:
        _is_npc_autonomy_busy = False


def _apply_npc_dialogue_results(actor_sim_info, group_data: Dict[str, Any], online_npcs: List[Any], reply_messages: List[Dict[str, Any]]):
    """
    Appends generated NPC messages to group history and displays notification.
    Zero relationship changes are applied to the player.
    """
    try:
        group_id = group_data.get("id", "")
        group_name = group_data.get("name", "Групповой чат")

        first_speaker_sim_info = None
        added_messages = []

        for m in reply_messages:
            raw_sender = m.get("sender", "")
            raw_text = m.get("text", "")
            clean_text, _, _ = parse_and_strip_relationship_tags(strip_emojis(raw_text))
            if not clean_text:
                continue

            # Identify matching SimInfo
            matched_sim = None
            for s_info in online_npcs:
                s_name = get_recipient_display_name(s_info)
                s_first = getattr(s_info, "first_name", "") or ""
                if (raw_sender.lower() in s_name.lower()) or (s_first and s_first.lower() in raw_sender.lower()):
                    matched_sim = s_info
                    break

            sender_name = get_recipient_display_name(matched_sim) if matched_sim else raw_sender
            sender_id = getattr(matched_sim, "sim_id", 0) if matched_sim else 0

            if first_speaker_sim_info is None and matched_sim is not None:
                first_speaker_sim_info = matched_sim

            add_group_message(
                group_id=group_id,
                sender=sender_name,
                text=clean_text,
                sender_id=sender_id,
                sender_name=sender_name,
            )
            added_messages.append("{}: {}".format(sender_name, clean_text))

        if not added_messages:
            return

        log("[NPC AUTONOMY] Appended {} autonomous message(s) to group '{}'.".format(len(added_messages), group_name))

        # Show notification popup
        preview_lines = added_messages[:3]
        if len(added_messages) > 3:
            preview_lines.append("...")

        notify_sim = first_speaker_sim_info or (online_npcs[0] if online_npcs else actor_sim_info)
        is_en = _is_en()
        grp_title = f"Group: {group_name}" if is_en else f"Групповой чат «{group_name}»"
        show_chat_notification(
            title=grp_title,
            text="\n".join(preview_lines),
            sim_info=notify_sim,
            is_error=False,
        )

    except Exception as e:
        log_exception("Error applying NPC dialogue results", e)


def start_npc_group_autonomy_alarm():
    """Initializes repeating in-game alarm for NPC group conversations."""
    global _npc_autonomy_alarm_handle
    if alarms is None or create_time_span is None or services is None:
        return

    try:
        if _npc_autonomy_alarm_handle is not None:
            return

        zone_inst = services.current_zone() if services is not None else None
        if zone_inst is None:
            return

        # Check every 60 sim-minutes
        interval_mins = 60
        time_span = create_time_span(minutes=interval_mins)
        _npc_autonomy_alarm_handle = alarms.add_alarm(
            zone_inst,
            time_span,
            _on_npc_autonomy_tick,
            repeating=True,
            use_sleep_time=True,
            cross_zone=True,
        )
        log("[NPC AUTONOMY] Repeating alarm initialized (checks every {} sim-minutes).".format(interval_mins))
    except Exception as e:
        log_exception("Failed to start NPC group autonomy alarm", e)


def stop_npc_group_autonomy_alarm():
    """Stops the repeating in-game alarm."""
    global _npc_autonomy_alarm_handle
    if alarms is not None and _npc_autonomy_alarm_handle is not None:
        try:
            alarms.cancel_alarm(_npc_autonomy_alarm_handle)
        except Exception:
            pass
        _npc_autonomy_alarm_handle = None


def trigger_npc_group_autonomy(force: bool = True, target_group_filter: str = "") -> Tuple[bool, str]:
    """
    Triggers an NPC group autonomous conversation immediately (useful for testing and cheat commands).
    If force=True, ignores the 3-hour cooldown and the 60% probability check.
    If target_group_filter is provided, targets groups matching that name or ID.
    Returns (success, message).
    """
    global _is_npc_autonomy_busy
    if _is_npc_autonomy_busy:
        return False, "Система уже генерирует диалог с ИИ. Подождите несколько секунд."

    if services is None:
        return False, "Игровые службы недоступны (services is None)."

    is_en = _is_en()
    try:
        client_mgr = services.client_manager()
        if client_mgr is None:
            return False, "Client manager unavailable." if is_en else "Менеджер клиентов недоступен."
        client = client_mgr.get_first_client()
        if client is None:
            return False, "Game client not found." if is_en else "Игровой клиент не найден."
        actor_sim_info = getattr(client, "active_sim_info", None)
        if actor_sim_info is None and client.active_sim is not None:
            actor_sim_info = getattr(client.active_sim, "sim_info", None)
        if actor_sim_info is None:
            return False, "Active Sim is not selected." if is_en else "Активный персонаж не выбран."

        actor_id = getattr(actor_sim_info, "sim_id", 0)
        actor_name = get_recipient_display_name(actor_sim_info)
        groups = get_groups_for_sim(actor_id)
        if not groups:
            return False, f"Sim {actor_name} is not in any groups. Create a group via PC or phone!" if is_en else f"Сим {actor_name} не состоит ни в одной группе. Создайте группу через компьютер или телефон!"

        sim_mgr = services.sim_info_manager()
        if sim_mgr is None:
            return False, "Sim manager unavailable." if is_en else "Менеджер симов недоступен."

        abs_day = get_current_sim_absolute_days()
        time_str = get_current_sim_time()
        try:
            h, m = [int(x) for x in time_str.split(":")]
            cur_minute = abs_day * 1440 + h * 60 + m
        except Exception:
            cur_minute = abs_day * 1440

        filter_str = (target_group_filter or "").strip().lower()
        candidate_groups = []
        for grp in groups:
            g_name = (grp.get("name") or "").lower()
            g_id = (grp.get("id") or "").lower()
            if not filter_str or (filter_str in g_name) or (filter_str in g_id):
                candidate_groups.append(grp)

        if not candidate_groups:
            return False, f"No groups found for query '{target_group_filter}'." if is_en else f"Не найдено групп по запросу «{target_group_filter}»."

        reasons = []
        for grp in candidate_groups:
            gid = grp.get("id", "")
            gname = grp.get("name", "Group Chat" if is_en else "Групповой чат")

            if not force:
                last_t = _last_group_autonomy_time.get(gid, -9999)
                diff = cur_minute - last_t
                if 0 <= diff < 180:
                    reasons.append(f"'{gname}': cooldown for another {180 - diff} sim-min." if is_en else f"«{gname}»: кулдаун ещё {180 - diff} сим-мин.")
                    continue

            member_ids = grp.get("member_ids", [])
            online_npcs = []
            offline_npcs = []

            for mid in member_ids:
                if mid == actor_id:
                    continue
                s_info = sim_mgr.get(mid)
                if s_info is None:
                    continue

                ws_status = get_sim_work_or_school_status(s_info)
                s_name = get_recipient_display_name(s_info)
                if is_sim_online(s_info) and not ws_status.get("is_busy", False):
                    online_npcs.append(s_info)
                else:
                    if is_en:
                        status_desc = "work/school" if ws_status.get("is_busy") else "offline/sleep"
                    else:
                        status_desc = "работа/учеба" if ws_status.get("is_busy") else "оффлайн/сон"
                    offline_npcs.append(f"{s_name} ({status_desc})")

            if len(online_npcs) < 2:
                if is_en:
                    no_m = "no other members"
                    reasons.append(f"'{gname}': only {len(online_npcs)} NPC online (2+ required). Unavailable: {', '.join(offline_npcs) if offline_npcs else no_m}")
                else:
                    no_m = "нет других участников"
                    reasons.append(f"«{gname}»: только {len(online_npcs)} NPC в сети (требуется 2+). Недоступны: {', '.join(offline_npcs) if offline_npcs else no_m}")
                continue

            # Found suitable group
            _last_group_autonomy_time[gid] = cur_minute
            _is_npc_autonomy_busy = True
            online_names = [get_recipient_display_name(s) for s in online_npcs]
            log(f"[NPC AUTONOMY] Manual trigger: starting chat in '{gname}' with {len(online_npcs)} online NPCs: {', '.join(online_names)}")
            _dispatch_npc_group_chat(actor_sim_info, grp, online_npcs)
            if is_en:
                return True, f"Started conversation in group '{gname}'!\nOnline members: {', '.join(online_names)}.\nAwaiting AI response and popup notification..."
            else:
                return True, f"Запущен диалог в группе «{gname}»!\nУчастники в сети: {', '.join(online_names)}.\nОжидайте ответ ИИ и всплывающее уведомление..."

        if is_en:
            return False, "Could not start conversation:\n" + "\n".join(reasons)
        else:
            return False, "Не удалось запустить диалог:\n" + "\n".join(reasons)

    except Exception as e:
        log_exception("Error in trigger_npc_group_autonomy", e)
        return False, f"Error on trigger: {e}" if is_en else f"Ошибка при запуске: {e}"


def get_npc_autonomy_debug_info() -> str:
    """Returns formatted diagnostic text about the NPC autonomy system."""
    is_en = _is_en()
    lines = []
    lines.append("=== NPC GROUP AUTONOMY STATUS ===" if is_en else "=== СТАТУС АВТОНОМНОСТИ NPC В ГРУППАХ ===")
    lines.append(f"• Enabled in config: {'YES' if is_npc_autonomy_enabled() else 'NO'}" if is_en else f"• Включено в настройках: {'ДА' if is_npc_autonomy_enabled() else 'НЕТ'}")
    lines.append(f"• Game timer (Alarm): {'ACTIVE' if _npc_autonomy_alarm_handle is not None else 'NOT RUNNING'}" if is_en else f"• Игровой таймер (Alarm): {'АКТИВЕН' if _npc_autonomy_alarm_handle is not None else 'НЕ ЗАПУЩЕН'}")
    lines.append(f"• Generation currently busy: {'YES' if _is_npc_autonomy_busy else 'NO'}" if is_en else f"• Генерация сейчас занята: {'ДА' if _is_npc_autonomy_busy else 'НЕТ'}")

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

    groups = get_groups_for_sim(actor_id)
    lines.append(f"• Sim groups: {len(groups)}" if is_en else f"• Групп у сима: {len(groups)}")
    sim_mgr = services.sim_info_manager()

    for idx, grp in enumerate(groups, 1):
        gid = grp.get("id", "")
        gname = grp.get("name", "Group" if is_en else "Группа")
        last_t = _last_group_autonomy_time.get(gid, -9999)
        cd_left = max(0, 180 - (cur_minute - last_t)) if last_t > 0 else 0
        if is_en:
            cd_str = f"{cd_left} sim-min." if cd_left > 0 else "Ready"
        else:
            cd_str = f"{cd_left} сим-мин." if cd_left > 0 else "Готова"

        member_ids = grp.get("member_ids", [])
        online_count = 0
        members_desc = []
        for mid in member_ids:
            if mid == actor_id:
                continue
            s_info = sim_mgr.get(mid) if sim_mgr else None
            if not s_info:
                continue
            s_name = get_recipient_display_name(s_info)
            ws = get_sim_work_or_school_status(s_info)
            if is_sim_online(s_info) and not ws.get("is_busy"):
                online_count += 1
                members_desc.append(f"{s_name} [ONLINE]" if is_en else f"{s_name} [ОНЛАЙН]")
            else:
                if is_en:
                    reason = "work/school" if ws.get("is_busy") else "offline/sleep"
                else:
                    reason = "работа/учеба" if ws.get("is_busy") else "оффлайн/сон"
                members_desc.append(f"{s_name} [{reason}]")

        if is_en:
            lines.append(f"  [{idx}] '{gname}' (ID: {gid}):")
            lines.append(f"      Cooldown: {cd_str} | Online NPCs: {online_count} of {max(0, len(member_ids) - 1)}")
            if members_desc:
                lines.append(f"      Members: {', '.join(members_desc)}")
        else:
            lines.append(f"  [{idx}] «{gname}» (ID: {gid}):")
            lines.append(f"      Кулдаун: {cd_str} | Онлайн NPC: {online_count} из {max(0, len(member_ids) - 1)}")
            if members_desc:
                lines.append(f"      Участники: {', '.join(members_desc)}")

    return "\n".join(lines)
