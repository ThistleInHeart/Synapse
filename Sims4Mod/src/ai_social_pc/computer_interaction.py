import time
from ai_social_pc.logger import log, log_exception
from ai_social_pc.localization import is_english, _t


def _is_en() -> bool:
    try:
        return is_english()
    except Exception:
        return False

from ai_social_pc.chat_manager import (
    send_chat_message_async,
    send_group_chat_message_async,
    apply_chat_relationship_impact,
    get_session_history,
)
from ai_social_pc.ui_chat import (
    show_contact_picker,
    show_message_input,
    show_chat_conversation_dialog,
    show_chat_notification,
    get_recipient_display_name,
    is_sim_online,
    show_messenger_root_menu,
    show_groups_menu,
    prompt_create_group,
    prompt_edit_groups,
    show_group_message_input,
)
from ai_social_pc.group_manager import (
    get_group_by_id,
    get_group_messages,
    add_group_message,
    clear_group_history,
)

try:
    import services
    import sims4
    from interactions.base.immediate_interaction import ImmediateSuperInteraction
    from interactions.base.super_interaction import SuperInteraction
    from sims4.utils import flexmethod
    from event_testing.results import TestResult
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    services = None
    sims4 = None
    ImmediateSuperInteraction = object
    SuperInteraction = object
    flexmethod = lambda f: f
    TestResult = None
    LocalizationHelperTuning = None

# Tuning ID (s= attribute) of our interaction in AIThoughts.package
# Synapse:test_pc_button s="14101515603163926181"
SYNAPSE_PC_TUNING_ID = 14101515603163926181
SYNAPSE_PHONE_TUNING_ID = 11501066889278280582

ALL_CHAT_AFFORDANCE_IDS = {SYNAPSE_PC_TUNING_ID, SYNAPSE_PHONE_TUNING_ID}

_last_session_open_time = 0.0


def start_pc_chat_session(actor_sim_info, computer_obj=None, preselected_contact=None):
    """
    Main entry point for starting an AI chat session from a computer.
    Called when the player completes the computer interaction, or via cheat command.
    """
    global _last_session_open_time
    now = time.time()
    if preselected_contact is None and (now - _last_session_open_time < 1.0):
        log("[PC CHAT] Debounced duplicate start_pc_chat_session call")
        return
    _last_session_open_time = now

    if actor_sim_info is None and services is not None:
        actor_sim_info = services.active_sim_info()

    if actor_sim_info is None:
        log("Cannot start PC chat: active sim_info is None", level="ERROR")
        return

    actor_name = get_recipient_display_name(actor_sim_info)
    log(f"Starting PC Chat session for actor: {actor_name}")

    def _on_contact_picked(chosen_contact):
        recipient_name = get_recipient_display_name(chosen_contact)
        log(f"Actor {actor_name} selected contact {recipient_name}")

        # If any Sim (including this contact) is now online, process delayed replies immediately
        try:
            from ai_social_pc.delayed_replies import check_and_process_pending_replies
            check_and_process_pending_replies(force_all=False)
        except Exception:
            pass

        active_dialog_ref = [None]
        user_closed_manually = [False]
        a_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
        r_id = getattr(chosen_contact, "sim_id", 0) if not isinstance(chosen_contact, dict) else chosen_contact.get("id", -1)

        from ai_social_pc.chat_manager import get_session_history
        initial_history_len = [len(get_session_history(a_id, r_id))]

        def _cancel_active_dialog():
            dlg = active_dialog_ref[0]
            active_dialog_ref[0] = None
            if dlg is not None:
                try:
                    if getattr(dlg, "_is_user_closed", False):
                        log("[UI] Dialog already closed by user, skipping cancel")
                        return
                    import services
                    uds = services.ui_dialog_service() if services is not None else None
                    d_id = getattr(dlg, "dialog_id", None)
                    if uds is not None and d_id is not None:
                        is_active = True
                        if hasattr(uds, "_active_dialogs"):
                            is_active = (d_id in uds._active_dialogs)
                        if is_active:
                            log(f"[UI] Auto-cancelling active typing dialog ID {d_id} to refresh view")
                            uds.dialog_cancel(d_id)
                        else:
                            log(f"[UI] Dialog ID {d_id} already closed, skipping cancel")
                except Exception as e:
                    log_exception("Error auto-cancelling active dialog", e)

        def _open_input_for_contact(is_typing: bool = False):
            if user_closed_manually[0] and not is_typing:
                return

            def _on_cancel():
                log("User closed/canceled the messenger dialog")
                user_closed_manually[0] = True
                active_dialog_ref[0] = None

                # Trigger summarization if new messages were exchanged in this session
                try:
                    from ai_social_pc.chat_manager import get_session_history
                    from ai_social_pc.memory_manager import request_chat_summarization_async
                    cur_history = list(get_session_history(a_id, r_id))
                    if len(cur_history) > initial_history_len[0]:
                        log(f"[MEMORY] Messenger closed. Triggering chat summarization ({len(cur_history)} messages, initial was {initial_history_len[0]}).")
                        request_chat_summarization_async(actor_sim_info, chosen_contact, cur_history)
                        initial_history_len[0] = len(cur_history)
                except Exception as mem_err:
                    log_exception("Failed to trigger chat summarization on close", mem_err)

            def _on_message_submitted(entered_text):
                user_closed_manually[0] = False
                active_dialog_ref[0] = None
                clean_text = entered_text.strip()
                if clean_text.lower() in ("/clear", "/reset", "очистить", "/сброс"):
                    from ai_social_pc.chat_manager import clear_session_history
                    clear_session_history(a_id, r_id)
                    initial_history_len[0] = 0
                    show_chat_notification(
                        title=_t("CHAT_ROOT_TITLE", "AI Messenger"),
                        text=_t("CHAT_CLEAR_CONFIRM", "Chat history with {name} has been cleared.").format(name=recipient_name),
                        sim_info=chosen_contact if not isinstance(chosen_contact, dict) else None,
                        is_error=False,
                    )
                    _open_input_for_contact(is_typing=False)
                    return

                # 1. Immediately append player's message to conversation history
                from ai_social_pc.chat_manager import add_session_message, send_chat_message_async
                a_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
                r_id = getattr(chosen_contact, "sim_id", 0) if not isinstance(chosen_contact, dict) else chosen_contact.get("id", -1)
                a_name = get_recipient_display_name(actor_sim_info)
                add_session_message(a_id, r_id, sender=a_name, text=clean_text, sender_id=a_id)

                # Check if recipient is online: if offline, enqueue for delayed reply when they wake up
                if not is_sim_online(chosen_contact):
                    log(f"[AI Chat] Recipient {recipient_name} is offline. Enqueueing pending reply for when they wake up.")
                    try:
                        from ai_social_pc.delayed_replies import enqueue_pending_reply
                        enqueue_pending_reply(a_id, r_id, clean_text)
                    except Exception as eq_err:
                        log_exception("Failed to enqueue pending reply", eq_err)
                    _open_input_for_contact(is_typing=False)
                    return

                # 2. Immediately re-open window with typing indicator inside the window
                _open_input_for_contact(is_typing=True)

                # 3. Check for work / school status and build extra prompt note
                from ai_social_pc.chat_manager import (
                    get_sim_work_or_school_status,
                    build_work_or_school_prompt_context,
                )
                actor_name = getattr(actor_sim_info, "first_name", "") or "Собеседник"
                work_school_status = get_sim_work_or_school_status(chosen_contact)
                extra_ctx = None
                if work_school_status.get("is_busy"):
                    extra_ctx = build_work_or_school_prompt_context(
                        sender_name=actor_name,
                        recipient_name=recipient_name,
                        status_info=work_school_status,
                    )
                    log(f"[AI Chat] Recipient {recipient_name} is at {work_school_status.get('activity_type')}. Context note: '{extra_ctx[:60]}...'")

                # 4. Send async request to Synapse Bridge
                def _on_reply(reply_text, success):
                    _cancel_active_dialog()
                    time.sleep(0.05)

                    if success:
                        if not user_closed_manually[0]:
                            _open_input_for_contact(is_typing=False)
                        else:
                            show_chat_notification(
                                title=recipient_name,
                                text=reply_text,
                                sim_info=chosen_contact if not isinstance(chosen_contact, dict) else None,
                                is_error=False,
                            )
                    else:
                        show_chat_notification(
                            title=_t("MESSENGER_ERROR_TITLE", "Messenger Error"),
                            text=reply_text,
                            sim_info=actor_sim_info,
                            is_error=True,
                        )
                        if not user_closed_manually[0]:
                            _open_input_for_contact(is_typing=False)

                send_chat_message_async(
                    actor_sim_info,
                    chosen_contact,
                    clean_text,
                    _on_reply,
                    extra_context=extra_ctx,
                )

            _cancel_active_dialog()
            active_dialog_ref[0] = show_message_input(
                actor_sim_info,
                chosen_contact,
                _on_message_submitted,
                is_typing=is_typing,
                on_cancel=_on_cancel,
            )

        # Open text input dialog
        _open_input_for_contact()

    def _open_groups_flow():
        def _on_select_group(group_data):
            open_group_chat_session(actor_sim_info, group_data)

        def _on_create_group():
            def _on_created(new_grp):
                open_group_chat_session(actor_sim_info, new_grp)

            prompt_create_group(
                actor_sim_info,
                on_group_created=_on_created,
                on_cancel=_open_groups_flow,
            )

        def _on_edit_groups():
            prompt_edit_groups(
                actor_sim_info,
                on_done=_open_groups_flow,
                on_cancel=_open_groups_flow,
            )

        def _on_back():
            start_pc_chat_session(actor_sim_info)

        show_groups_menu(
            actor_sim_info,
            on_select_group=_on_select_group,
            on_create_group=_on_create_group,
            on_edit_groups=_on_edit_groups,
            on_back=_on_back,
        )

    if preselected_contact is not None:
        _on_contact_picked(preselected_contact)
    else:
        show_messenger_root_menu(
            actor_sim_info,
            on_direct_chat=lambda: show_contact_picker(actor_sim_info, _on_contact_picked),
            on_groups=_open_groups_flow,
        )


def open_group_chat_session(actor_sim_info, group_data):
    """
    Interactive group chat session dialog loop.
    Supports viewing message history, player sending messages,
    NPC group members replying via AI, typing indicators, and /clear.
    """
    if actor_sim_info is None and services is not None:
        actor_sim_info = services.active_sim_info()

    if actor_sim_info is None or not group_data:
        return

    actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
    actor_name = get_recipient_display_name(actor_sim_info)
    group_id = group_data.get("id")

    active_group_dialog_ref = [None]
    user_closed_manually = [False]
    initial_history_len = [len(get_group_messages(group_id))]

    def _cancel_active_group_dialog():
        dlg = active_group_dialog_ref[0]
        active_group_dialog_ref[0] = None
        if dlg is not None:
            try:
                if getattr(dlg, "_is_user_closed", False):
                    return
                import services
                uds = services.ui_dialog_service() if services is not None else None
                d_id = getattr(dlg, "dialog_id", None)
                if uds is not None and d_id is not None:
                    is_active = True
                    if hasattr(uds, "_active_dialogs"):
                        is_active = (d_id in uds._active_dialogs)
                    if is_active:
                        uds.dialog_cancel(d_id)
            except Exception as e:
                log_exception("Error auto-cancelling active group dialog", e)

    def _open_input(is_typing: bool = False, typing_author: str = ""):
        if user_closed_manually[0] and not is_typing:
            return

        cur_group = get_group_by_id(group_id) or group_data
        group_name = cur_group.get("name", "Групповой чат")

        def _on_cancel():
            log(f"User closed group chat dialog for group '{group_name}'")
            user_closed_manually[0] = True
            active_group_dialog_ref[0] = None

            # Trigger group summarization if new messages were exchanged in this session
            try:
                from ai_social_pc.group_manager import get_group_messages
                from ai_social_pc.memory_manager import request_group_summarization_async
                cur_history = list(get_group_messages(group_id))
                if len(cur_history) > initial_history_len[0]:
                    log(f"[MEMORY] Group dialog closed. Triggering group summarization ({len(cur_history)} msgs, initial was {initial_history_len[0]}).")
                    request_group_summarization_async(actor_sim_info, cur_group, cur_history)
                    initial_history_len[0] = len(cur_history)
            except Exception as mem_err:
                log_exception("Failed to trigger group summarization on close", mem_err)

        def _on_message_submitted(entered_text):
            user_closed_manually[0] = False
            active_group_dialog_ref[0] = None
            clean_text = entered_text.strip()
            if not clean_text:
                _open_input(is_typing=False)
                return

            if clean_text.lower() in ("/clear", "/reset", "очистить", "/сброс"):
                clear_group_history(group_id)
                initial_history_len[0] = 0
                is_en = _is_en()
                show_chat_notification(
                    title="Group Chat" if is_en else "Групповой чат",
                    text=f"Chat history for group '{group_name}' has been cleared." if is_en else f"История сообщений группы '{group_name}' очищена.",
                    sim_info=actor_sim_info,
                    is_error=False,
                )
                _open_input(is_typing=False)
                return

            # Append player's message to group history
            add_group_message(group_id, sender=actor_name, text=clean_text, sender_id=actor_id, sender_name=actor_name)

            # Resolve other group members
            sim_mgr = services.sim_info_manager() if services is not None else None
            other_members = []
            for mid in cur_group.get("member_ids", []):
                if mid != actor_id:
                    s_info = sim_mgr.get(mid) if sim_mgr else None
                    if s_info:
                        other_members.append(s_info)

            if not other_members:
                is_en = _is_en()
                show_chat_notification(
                    title=f"Group: {group_name}" if is_en else "Группа",
                    text="There are no other members in this group." if is_en else "В этой группе нет других участников.",
                    sim_info=actor_sim_info,
                    is_error=True,
                )
                _open_input(is_typing=False)
                return

            # Check online status of other members
            from ai_social_pc.chat_manager import get_sim_work_or_school_status
            online_sims = []
            for s in other_members:
                ws = get_sim_work_or_school_status(s)
                if is_sim_online(s) and not ws.get("is_busy", False):
                    online_sims.append(s)

            # Check if player specifically mentioned a member by name
            target_typing_author = ""
            target_sim = None
            clean_lower = clean_text.lower()
            for s in other_members:
                f_name = (getattr(s, "first_name", "") or "").strip()
                l_name = (getattr(s, "last_name", "") or "").strip()
                if f_name and f_name.lower() in clean_lower:
                    target_typing_author = f_name
                    target_sim = s
                    break
                if l_name and l_name.lower() in clean_lower:
                    target_typing_author = f"{f_name} {l_name}".strip()
                    target_sim = s
                    break

            # If addressed to a specific person who is offline, or if ALL members are offline:
            is_target_offline = (target_sim is not None and target_sim not in online_sims)
            is_all_offline = (len(online_sims) == 0)

            if is_target_offline or is_all_offline:
                from ai_social_pc.delayed_replies import enqueue_pending_group_reply
                log(f"[GROUP CHAT] Participants (or targeted '{target_typing_author}') are offline. Enqueueing morning reply.")
                try:
                    enqueue_pending_group_reply(group_id, actor_id, clean_text)
                except Exception as eq_err:
                    log_exception("Failed to enqueue pending group reply", eq_err)

                is_en = _is_en()
                if is_target_offline and target_typing_author:
                    note_text = (
                        f"{target_typing_author} is currently offline (asleep). Message delivered, response will arrive later."
                        if is_en else
                        f"{target_typing_author} сейчас не в сети (спит). Сообщение доставлено, ответ придет позже."
                    )
                else:
                    note_text = (
                        "All group members are currently offline (asleep). Message delivered, they will reply in the morning."
                        if is_en else
                        "Все участники группы сейчас не в сети (спят). Сообщение доставлено, они ответят утром."
                    )

                show_chat_notification(
                    title=f"Group: {group_name}" if is_en else f"Группа: {group_name}",
                    text=note_text,
                    sim_info=actor_sim_info,
                    is_error=False,
                )
                _open_input(is_typing=False)
                return

            # Show typing indicator dialog
            _cancel_active_group_dialog()
            active_group_dialog_ref[0] = show_group_message_input(
                actor_sim_info,
                cur_group,
                _on_message_submitted,
                is_typing=True,
                typing_author=target_typing_author,
                on_cancel=_on_cancel,
            )

            def _on_group_reply(reply_messages, is_success, error_msg=""):
                log(f"[GROUP AI] Reply received (success={is_success}, count={len(reply_messages)})")
                _cancel_active_group_dialog()
                time.sleep(0.05)

                is_en = _is_en()
                if is_success:
                    if reply_messages:
                        for msg in reply_messages:
                            sender_name = msg.get("sender", "Interlocutor" if is_en else "Собеседник")
                            text = msg.get("text", "")
                            d_fr = msg.get("delta_friendship", 0)
                            d_rom = msg.get("delta_romance", 0)

                            # Find matching Sim to record sender_id and apply relationship
                            target_sim_info = None
                            for s in other_members:
                                s_name = get_recipient_display_name(s)
                                s_first = getattr(s, "first_name", "") or ""
                                if (sender_name.lower() in s_name.lower()) or (s_first and s_first.lower() in sender_name.lower()):
                                    target_sim_info = s
                                    break

                            t_sim_id = getattr(target_sim_info, "sim_id", 0) if target_sim_info else 0
                            add_group_message(group_id, sender=sender_name, text=text, sender_id=t_sim_id, sender_name=sender_name)

                            if target_sim_info is not None and (d_fr != 0 or d_rom != 0):
                                apply_chat_relationship_impact(actor_sim_info, target_sim_info, delta_fr=d_fr, delta_rom=d_rom)

                        if not user_closed_manually[0]:
                            _open_input(is_typing=False)
                        else:
                            summary_lines = [f"{m.get('sender')}: {m.get('text')}" for m in reply_messages[:2]]
                            show_chat_notification(
                                title=f"Group: {group_name}" if is_en else group_name,
                                text="\n".join(summary_lines),
                                sim_info=actor_sim_info,
                                is_error=False,
                            )
                    else:
                        # All offline or empty reply
                        show_chat_notification(
                            title=f"Group: {group_name}" if is_en else group_name,
                            text="None of the members are currently online to reply." if is_en else "Сейчас никто из участников не в сети, чтобы ответить.",
                            sim_info=actor_sim_info,
                            is_error=False,
                        )
                        if not user_closed_manually[0]:
                            _open_input(is_typing=False)
                else:
                    err_text = error_msg or ("Failed to receive response in group chat." if is_en else "Не удалось получить ответ в групповом чате.")
                    show_chat_notification(
                        title="Messenger Error" if is_en else "Ошибка мессенджера",
                        text=err_text,
                        sim_info=actor_sim_info,
                        is_error=True,
                    )
                    if not user_closed_manually[0]:
                        _open_input(is_typing=False)

            send_group_chat_message_async(
                actor_sim_info=actor_sim_info,
                group_data=cur_group,
                message_text=clean_text,
                callback=_on_group_reply,
            )

        _cancel_active_group_dialog()
        active_group_dialog_ref[0] = show_group_message_input(
            actor_sim_info,
            cur_group,
            _on_message_submitted,
            is_typing=is_typing,
            typing_author=typing_author,
            on_cancel=_on_cancel,
        )

    _open_input(is_typing=False)


# ===================================================================
# MCCC-STYLE INJECTION (backup/fallback injection)
# ===================================================================

def _is_computer_definition(tuned_cls):
    """Detect if a tuned class (object definition) is a computer."""
    try:
        anim_cls = getattr(tuned_cls, '_anim_overrides_cls', None)
        if anim_cls is not None:
            params = getattr(anim_cls, 'params', None)
            if params:
                if 'computerType' in params:
                    return True
                if params.get('carryObject') == 'tablet':
                    return True
    except Exception:
        pass
    return False


def is_computer_object(obj):
    """Accurately determines whether a game object is a computer or laptop."""
    if obj is None:
        return False
    if getattr(obj, "is_computer", False):
        return True
    cls_name = obj.__class__.__name__.lower()
    if "computer" in cls_name or "laptop" in cls_name:
        return True
    name = getattr(obj, "__name__", str(obj)).lower()
    if "computer" in name or "laptop" in name:
        return True
    try:
        import tag
        t = getattr(tag.Tag, "Func_Computer", None)
        if t is not None and hasattr(obj, "has_tag") and obj.has_tag(t):
            return True
    except Exception:
        pass
    defn = getattr(obj, "definition", None)
    if defn is not None:
        d_cls = getattr(defn, "cls", defn)
        if _is_computer_definition(d_cls):
            return True
        d_name = str(defn).lower()
        if "computer" in d_name or "laptop" in d_name:
            return True
    return False


def inject_affordance_into_computers():
    """
    Fallback injection for definition tuned classes.
    """
    if services is None:
        return 0

    try:
        aff_mgr = services.affordance_manager()
        if aff_mgr is None:
            return 0

        our_affordance = aff_mgr.get(SYNAPSE_PC_TUNING_ID)
        if our_affordance is None:
            return 0

        aff_name = getattr(our_affordance, '__name__', str(our_affordance))

        def_mgr = services.definition_manager()
        if def_mgr is None:
            return 0

        count = 0
        for tuned_cls in def_mgr._tuned_classes.values():
            if tuned_cls is None:
                continue
            if not _is_computer_definition(tuned_cls):
                continue
            if not hasattr(tuned_cls, '_super_affordances'):
                continue
            current_affs = tuned_cls._super_affordances
            if our_affordance not in current_affs:
                tuned_cls._super_affordances = (our_affordance,) + current_affs
                count += 1

        if count == 0:
            for tuned_cls in def_mgr._tuned_classes.values():
                if tuned_cls is None:
                    continue
                name = getattr(tuned_cls, '__name__', '').lower()
                if 'computer' not in name and 'laptop' not in name:
                    continue
                if not hasattr(tuned_cls, '_super_affordances'):
                    continue
                current_affs = tuned_cls._super_affordances
                if our_affordance not in current_affs:
                    tuned_cls._super_affordances = (our_affordance,) + current_affs
                    count += 1

        return count

    except Exception as e:
        log_exception("[INJECT] Error in inject_affordance_into_computers", e)
        return 0


def find_phone_social_category(active_sim=None, use_bunny=False):
    """
    Finds the in-game PieMenuCategory object for 'Social' (Общение) on the phone.
    By default (use_bunny=False), targets the classic Base Game 'Общение' (зелёные губы).
    If use_bunny=True, targets 'Кролик общения' (Social Bunny).
    """
    if services is None:
        return None
    try:
        if active_sim is None:
            client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
            active_sim = client.active_sim if client else None

        if active_sim is None or not hasattr(active_sim, "_phone_affordances"):
            return None

        # Option A: User specifically wants Social Bunny
        if use_bunny:
            for aff in active_sim._phone_affordances:
                cat = getattr(aff, "category", None)
                if cat is not None:
                    c_name = getattr(cat, "__name__", str(cat)).lower()
                    if "social_media" in c_name or "bunny" in c_name:
                        log(f"[PHONE CAT] Found Social Bunny category: {getattr(cat, '__name__', str(cat))}")
                        return cat

        # Option B: BASE GAME Social app (зелёные губы)
        # Priority 1: Check category from standard phone chat/text affordances
        for aff in active_sim._phone_affordances:
            aff_name = getattr(aff, "__name__", "").lower()
            if "phone" in aff_name and any(k in aff_name for k in ("chat", "send_text", "sendtext", "text_picker")):
                cat = getattr(aff, "category", None)
                if cat is not None:
                    c_name = getattr(cat, "__name__", str(cat)).lower()
                    if not any(bad in c_name for bad in ("media", "bunny", "work", "career", "travel", "house", "entertain")):
                        log(f"[PHONE CAT] Found Base Game Social category from affordance {aff_name}: {getattr(cat, '__name__', str(cat))}")
                        return cat

        # Priority 2: Check any affordance with phone_social or phone_call (excluding non-social categories)
        for aff in active_sim._phone_affordances:
            aff_name = getattr(aff, "__name__", "").lower()
            if "phone" in aff_name and ("social" in aff_name or "call" in aff_name):
                cat = getattr(aff, "category", None)
                if cat is not None:
                    c_name = getattr(cat, "__name__", str(cat)).lower()
                    if not any(bad in c_name for bad in ("media", "bunny", "work", "career", "travel", "house", "entertain")):
                        log(f"[PHONE CAT] Found Base Game Social category from affordance {aff_name}: {getattr(cat, '__name__', str(cat))}")
                        return cat

        # Priority 3: Search for category with 'social', excluding media/bunny
        for aff in active_sim._phone_affordances:
            cat = getattr(aff, "category", None)
            if cat is not None:
                c_name = getattr(cat, "__name__", str(cat)).lower()
                if "social" in c_name and "media" not in c_name and "bunny" not in c_name:
                    log(f"[PHONE CAT] Found Base Game Social category by name: {getattr(cat, '__name__', str(cat))}")
                    return cat

        # Priority 4: Fallback from pie_menu_category manager directly
        pie_mgr = services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY) if hasattr(sims4, "resources") else None
        if pie_mgr is not None:
            for cat in pie_mgr.types.values():
                c_name = getattr(cat, "__name__", str(cat)).lower()
                if "phone" in c_name and "social" in c_name and "media" not in c_name and "bunny" not in c_name:
                    log(f"[PHONE CAT] Found Base Game Social category from pie_mgr: {getattr(cat, '__name__', str(cat))}")
                    return cat

    except Exception as e:
        log_exception("Error in find_phone_social_category", e)
    return None


def inject_affordance_into_phone(use_bunny=False):
    """
    Guarantees that Synapse:phone_social_messenger (11501066889278280582)
    is injected into Sim definition and active Sim._phone_affordances,
    and ensures its category is properly set to the Base Game Social category.
    """
    if services is None:
        return False
    try:
        aff_mgr = services.affordance_manager()
        if aff_mgr is None:
            return False
        phone_aff = aff_mgr.get(SYNAPSE_PHONE_TUNING_ID)
        if phone_aff is None:
            log(f"[PHONE INJECT] Affordance {SYNAPSE_PHONE_TUNING_ID} not found in affordance_manager", level="WARN")
            return False

        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        active_sim = client.active_sim if client else None

        # Resolve the desired Social category (Base Game or Bunny)
        social_cat = find_phone_social_category(active_sim, use_bunny=use_bunny)
        if social_cat is not None:
            phone_aff.category = social_cat
            log(f"[PHONE INJECT] Successfully assigned Category {getattr(social_cat, '__name__', str(social_cat))} to phone affordance!")

        injected = False
        def_mgr = services.definition_manager()
        if def_mgr is not None:
            sim_def = def_mgr.get(14965)
            if sim_def is not None and hasattr(sim_def, "_phone_affordances"):
                if phone_aff not in sim_def._phone_affordances:
                    sim_def._phone_affordances = (phone_aff,) + sim_def._phone_affordances
                    log("[PHONE INJECT] Injected phone affordance into Sim definition (14965)")
                    injected = True

        if active_sim is not None and hasattr(active_sim, "_phone_affordances"):
            if phone_aff not in active_sim._phone_affordances:
                active_sim._phone_affordances = (phone_aff,) + active_sim._phone_affordances
                log("[PHONE INJECT] Injected phone affordance into active Sim instance")
                injected = True

        return injected or (phone_aff in getattr(active_sim, "_phone_affordances", ()))
    except Exception as e:
        log_exception("Error in inject_affordance_into_phone", e)
        return False


def patch_computer_interactions():
    """
    Hooks into interaction execution to intercept:
    1. Our Synapse:test_pc_button interaction -> opens AI messenger
    2. Our Synapse:phone_social_messenger interaction -> opens AI messenger
    3. Vanilla Computer Chat actions -> also redirects to AI messenger
    """
    try:
        from interactions.base.immediate_interaction import ImmediateSuperInteraction
        from interactions.base.super_interaction import SuperInteraction

        def _is_our_interaction(obj):
            if obj is None:
                return False
            guid64 = getattr(obj, "guid64", 0)
            if guid64 in ALL_CHAT_AFFORDANCE_IDS:
                return True
            aff = getattr(obj, "affordance", None)
            if aff is not None:
                aff_guid = getattr(aff, "guid64", 0)
                if aff_guid in ALL_CHAT_AFFORDANCE_IDS:
                    return True
                aff_name = getattr(aff, "__name__", "").lower()
                if any(k in aff_name for k in ("synapse", "aisocialpc", "aichatpc")):
                    return True
                if "computer_chat" in aff_name and "autonomous" not in aff_name:
                    return True
            name = getattr(obj, "__name__", str(obj.__class__.__name__)).lower()
            if any(k in name for k in ("synapse", "aisocialpc", "aichatpc")):
                return True
            if "computer_chat" in name and "autonomous" not in name:
                return True
            return False

        # Patch our specific affordances directly if loaded in affordance manager
        if services is not None:
            aff_mgr = services.affordance_manager()
            if aff_mgr is not None:
                for aff_id in ALL_CHAT_AFFORDANCE_IDS:
                    aff_cls = aff_mgr.get(aff_id)
                    if aff_cls is not None and not getattr(aff_cls, "_aisocialpc_aff_hooked", False):
                        def _make_aff_run(orig_m):
                            def _aff_run(self, *args, **kwargs):
                                try:
                                    actor = getattr(self, "sim", None)
                                    actor_info = getattr(actor, "sim_info", None) if actor else None
                                    target_obj = getattr(self, "target", None)
                                    start_pc_chat_session(actor_info, computer_obj=target_obj)
                                except Exception as e:
                                    log_exception("Error in specific affordance run", e)
                                if orig_m:
                                    return orig_m(self, *args, **kwargs)
                                return True
                            return _aff_run

                        orig_run = getattr(aff_cls, "_run_interaction", None)
                        aff_cls._run_interaction = _make_aff_run(orig_run)
                        aff_cls._aisocialpc_aff_hooked = True
                        log(f"[HOOK] Hooked specific affordance: {getattr(aff_cls, '__name__', aff_cls)} ({aff_id})")

                try:
                    from ai_social_pc.direct_dialogue import SYNAPSE_DIRECT_DIALOGUE_TUNING_ID, hook_direct_dialogue_affordance
                    dd_cls = aff_mgr.get(SYNAPSE_DIRECT_DIALOGUE_TUNING_ID)
                    if dd_cls is not None:
                        hook_direct_dialogue_affordance(dd_cls)
                except Exception:
                    pass

        # Hook SuperInteraction._run_interaction
        orig_si = getattr(SuperInteraction, "_run_interaction", None)
        if orig_si and not getattr(SuperInteraction, "_aisocialpc_si_hooked", False):
            def custom_si_run(self, *args, **kwargs):
                try:
                    if _is_our_interaction(self):
                        is_user = getattr(self, "is_user_directed", True)
                        if is_user:
                            name = getattr(self, "__name__", str(self.__class__.__name__))
                            log(f"[HOOK] Intercepted Super interaction: {name}")
                            actor = getattr(self, "sim", None)
                            actor_info = getattr(actor, "sim_info", None) if actor else None
                            target_obj = getattr(self, "target", None)
                            start_pc_chat_session(actor_info, computer_obj=target_obj)
                except Exception as e:
                    log_exception("Error in Super PC hook", e)

                if orig_si:
                    return orig_si(self, *args, **kwargs)
                return True

            SuperInteraction._run_interaction = custom_si_run
            SuperInteraction._aisocialpc_si_hooked = True
            log("[HOOK] Hooked SuperInteraction._run_interaction")

        # Hook SimPickerInteraction
        try:
            from interactions.base.picker_interaction import SimPickerInteraction
            orig_picker = getattr(SimPickerInteraction, "_show_picker_dialog", None)
            if orig_picker and not getattr(SimPickerInteraction, "_aisocialpc_picker_hooked", False):
                def custom_picker(self, *args, **kwargs):
                    try:
                        if _is_our_interaction(self):
                            is_user = getattr(self, "is_user_directed", True)
                            if is_user:
                                name = getattr(self, "__name__", str(self.__class__.__name__))
                                log(f"[HOOK] Intercepted SimPicker: {name}")
                                actor = getattr(self, "sim", None)
                                actor_info = getattr(actor, "sim_info", None) if actor else None
                                target_obj = getattr(self, "target", None)
                                start_pc_chat_session(actor_info, computer_obj=target_obj)
                                return True
                    except Exception as e:
                        log_exception("Error in SimPicker hook", e)
                    return orig_picker(self, *args, **kwargs)

                SimPickerInteraction._show_picker_dialog = custom_picker
                SimPickerInteraction._aisocialpc_picker_hooked = True
                log("[HOOK] Hooked SimPickerInteraction._show_picker_dialog")
        except Exception as e:
            log_exception("Error hooking SimPicker", e)

    except Exception as e:
        log_exception("Error in patch_computer_interactions", e)


def find_all_computers():
    """Returns a list of all computer and laptop objects in the active zone."""
    computers = []
    if services is None:
        return computers
    obj_mgr = services.object_manager()
    if obj_mgr is None:
        return computers
    for obj in obj_mgr.values():
        if is_computer_object(obj):
            computers.append(obj)
    return computers
