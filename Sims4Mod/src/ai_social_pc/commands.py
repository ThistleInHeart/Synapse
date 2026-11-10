from ai_social_pc.logger import log, log_exception
from ai_social_pc.computer_interaction import (
    start_pc_chat_session,
    inject_affordance_into_computers,
    inject_affordance_into_phone,
    find_all_computers,
    SYNAPSE_PC_TUNING_ID,
    SYNAPSE_PHONE_TUNING_ID,
)
from ai_social_pc.chat_manager import _CHAT_SESSIONS

try:
    import services
    import sims4.commands
    from sims4.commands import Command, CommandType, output
    from interactions.context import InteractionContext, QueueInsertStrategy
    from event_testing.results import TestResult
except ImportError:
    services = None
    sims4 = None
    Command = lambda *a, **kw: lambda f: f
    CommandType = None
    output = lambda msg, c=None: None
    InteractionContext = None
    QueueInsertStrategy = None
    TestResult = None


def cheat_print(connection, text: str, notify: bool = False, title: str = "AI Social PC"):
    log(f"[CONSOLE] {text}")
    try:
        if sims4 is not None and hasattr(sims4, "commands"):
            if hasattr(sims4.commands, "cheat_output"):
                sims4.commands.cheat_output(text, connection)
            elif hasattr(sims4.commands, "output"):
                sims4.commands.output(text, connection)
    except Exception:
        pass
    try:
        if output is not None:
            output(text, connection)
    except Exception:
        pass
    if notify:
        try:
            from ai_social_pc.ui_chat import show_chat_notification
            show_chat_notification(title, text, is_error=False)
        except Exception:
            pass


def _is_en() -> bool:
    try:
        from ai_social_pc.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        try:
            from ai_thought_reader.commands import is_english_active
            return is_english_active()
        except Exception:
            return False


def _get_active_sim_and_info():
    if services is None:
        return None, None
    client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
    active_sim = client.active_sim if client else None
    active_sim_info = services.active_sim_info() if hasattr(services, "active_sim_info") else None
    if active_sim is None and active_sim_info is not None and hasattr(active_sim_info, "get_sim_instance"):
        active_sim = active_sim_info.get_sim_instance()
    return active_sim, active_sim_info


def _get_nearest_computer(active_sim=None):
    computers = find_all_computers()
    if not computers:
        return None
    if active_sim is None or not hasattr(active_sim, "position"):
        return computers[0]
    try:
        sim_pos = active_sim.position
        computers.sort(key=lambda c: (c.position - sim_pos).magnitude() if hasattr(c, "position") else 9999)
    except Exception:
        pass
    return computers[0]


@Command("ai_pc_chat", "ai.pc_chat", "chat_pc", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_chat(*args, _connection=None, **kwargs):
    """
    Cheat command to trigger AI Computer Messenger directly.
    Can be invoked from cheat console or directly from S4S do_command interaction.
    """
    is_en = _is_en()
    cheat_print(_connection, "[AI Social PC] Starting AI Messenger..." if is_en else "[AI Social PC] Запуск AI Мессенджера...")
    try:
        _, active_info = _get_active_sim_and_info()
        target_obj = None
        if args:
            try:
                obj_id = int(args[0])
                if services is not None:
                    target_obj = services.object_manager().get(obj_id)
            except Exception:
                pass
        start_pc_chat_session(active_info, computer_obj=target_obj)
    except Exception as e:
        log_exception("Error running ai_pc_chat command", e)
        cheat_print(_connection, f"[AI Social PC] Error: {e}" if is_en else f"[AI Social PC] Ошибка: {e}")


@Command("ai_pc_debug", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_debug(_connection=None):
    """
    Full diagnostics for AI Social PC:
    - Checks Synapse:test_pc_button affordance in affordance_manager
    - Scans all computers in the zone
    - Checks if our interaction is injected into computers
    """
    is_en = _is_en()
    cheat_print(_connection, "==================================================")
    cheat_print(_connection, "         AI SOCIAL PC: DIAGNOSTICS                ")
    cheat_print(_connection, "==================================================")

    if services is None:
        cheat_print(_connection, "[ERROR] Services not available.")
        return

    # 1. Check Affordance Manager for our interaction
    aff_mgr = services.affordance_manager()
    cheat_print(_connection, f"1. Affordance Manager: {'OK' if aff_mgr else 'NONE'}")
    our_aff = None
    if aff_mgr:
        our_aff = aff_mgr.get(SYNAPSE_PC_TUNING_ID)
        if our_aff:
            s_name = getattr(our_aff, "__name__", str(our_aff))
            cat = getattr(our_aff, "category", None)
            prio = getattr(our_aff, "pie_menu_priority", None)
            simless = getattr(our_aff, "simless", None)
            f_str = "FOUND" if is_en else "НАЙДЕН"
            cheat_print(_connection, f"   ✅ Synapse:test_pc_button (ID {SYNAPSE_PC_TUNING_ID}): {f_str} ({s_name})")
            cheat_print(_connection, f"     - category: {cat}")
            cheat_print(_connection, f"     - pie_menu_priority: {prio}")
            cheat_print(_connection, f"     - simless: {simless}")
        else:
            nf_str = "NOT FOUND!" if is_en else "НЕ НАЙДЕН!"
            tip_str = f"Check that AIThoughts.package contains resource with s=\"{SYNAPSE_PC_TUNING_ID}\"" if is_en else f"Проверьте что AIThoughts.package содержит ресурс с s=\"{SYNAPSE_PC_TUNING_ID}\""
            cheat_print(_connection, f"   ❌ Synapse:test_pc_button (ID {SYNAPSE_PC_TUNING_ID}): {nf_str}")
            cheat_print(_connection, f"      {tip_str}")

    # 2. Find computers
    computers = find_all_computers()
    c_found_str = f"2. Computers found on lot: {len(computers)}" if is_en else f"2. Компьютеров на лоте найдено: {len(computers)}"
    cheat_print(_connection, c_found_str)

    # 3. Check injection status
    for idx, comp in enumerate(computers, 1):
        c_id = getattr(comp, "id", "Unknown")
        c_name = getattr(comp, "__name__", str(comp))
        comp_hdr = f"--- Computer #{idx} [ID: {c_id}] ({c_name}) ---" if is_en else f"--- Компьютер #{idx} [ID: {c_id}] ({c_name}) ---"
        cheat_print(_connection, comp_hdr)

        cur_sas = getattr(comp, "_super_affordances", ())
        tot_str = f"Total super_affordances: {len(cur_sas)}" if is_en else f"Всего super_affordances: {len(cur_sas)}"
        cheat_print(_connection, f"   {tot_str}")

        if our_aff is not None:
            in_sa = our_aff in cur_sas
            val_str = ("✅ YES" if is_en else "✅ ДА") if in_sa else ("❌ NO" if is_en else "❌ НЕТ")
            cheat_print(_connection, f"   Synapse:test_pc_button in _super_affordances: {val_str}")

        # Check definition class too
        defn = getattr(comp, "definition", None)
        if defn is not None:
            def_sas = getattr(defn, "_super_affordances", ())
            if our_aff is not None:
                in_def = our_aff in def_sas
                val_str2 = ("✅ YES" if is_en else "✅ ДА") if in_def else ("❌ NO" if is_en else "❌ НЕТ")
                def_msg = f"In definition._super_affordances: {val_str2}" if is_en else f"В definition._super_affordances: {val_str2}"
                cheat_print(_connection, f"   {def_msg}")

    cheat_print(_connection, "==================================================")


@Command("ai_phone_debug", command_type=CommandType.Live if CommandType else 0)
def command_ai_phone_debug(_connection=None):
    """
    Full diagnostics for AI Social Phone:
    - Checks Synapse:phone_social_messenger affordance in affordance_manager
    - Checks if our interaction is in the active Sim's _phone_affordances
    - Tests visibility test for active Sim
    """
    is_en = _is_en()
    cheat_print(_connection, "==================================================")
    cheat_print(_connection, "         AI SOCIAL PHONE: DIAGNOSTICS             ")
    cheat_print(_connection, "==================================================")

    if services is None:
        cheat_print(_connection, "[ERROR] Services not available.")
        return

    aff_mgr = services.affordance_manager()
    phone_aff = aff_mgr.get(SYNAPSE_PHONE_TUNING_ID) if aff_mgr else None
    if phone_aff:
        s_name = getattr(phone_aff, "__name__", str(phone_aff))
        cat = getattr(phone_aff, "category", None)
        cat_id = getattr(cat, "guid64", cat) if cat else "None"
        found_txt = f"1. Interaction (ID {SYNAPSE_PHONE_TUNING_ID}): ✅ FOUND ({s_name})" if is_en else f"1. Действие (ID {SYNAPSE_PHONE_TUNING_ID}): ✅ НАЙДЕНО ({s_name})"
        cheat_print(_connection, found_txt)
        cheat_print(_connection, f"   - category: {cat_id}")
    else:
        nf_txt = f"1. Interaction (ID {SYNAPSE_PHONE_TUNING_ID}): ❌ NOT FOUND in game!" if is_en else f"1. Действие (ID {SYNAPSE_PHONE_TUNING_ID}): ❌ НЕ НАЙДЕНО в игре!"
        tip_txt = "   Verify that AIThoughts.package is loaded by game" if is_en else "   Проверьте что AIThoughts.package загружен игрой"
        cheat_print(_connection, nf_txt)
        cheat_print(_connection, tip_txt)

    active_sim, active_info = _get_active_sim_and_info()
    if active_sim is not None:
        phone_sas = getattr(active_sim, "_phone_affordances", ())
        in_phone = phone_aff in phone_sas if phone_aff else False
        status_in = ("✅ YES" if is_en else "✅ ДА") if in_phone else ("❌ NO" if is_en else "❌ НЕТ")
        in_phone_msg = f"2. In Sim's _phone_affordances: {status_in} (total in phone: {len(phone_sas)})" if is_en else f"2. В _phone_affordances сима: {status_in} (всего в телефоне: {len(phone_sas)})"
        cheat_print(_connection, in_phone_msg)

        # Auto-ensure category is assigned if missing
        if phone_aff is not None and getattr(phone_aff, "category", None) is None:
            inject_affordance_into_phone()
            cat = getattr(phone_aff, "category", None)
            cat_id = getattr(cat, "guid64", getattr(cat, "__name__", str(cat))) if cat else "None"
            upd_cat_msg = f"   - updated category: {cat_id}" if is_en else f"   - обновленная category: {cat_id}"
            cheat_print(_connection, upd_cat_msg)

        if phone_aff is not None:
            try:
                client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
                if client is not None and hasattr(client, "create_interaction_context"):
                    ctx = client.create_interaction_context(active_sim)
                else:
                    from interactions.context import InteractionContext
                    ctx = InteractionContext(active_sim, InteractionContext.SOURCE_PIE_MENU, 3)
                res = phone_aff.test(target=active_sim, context=ctx)
                passed = bool(res)
                reason = getattr(res, "reason", "OK")
                if is_en:
                    test_res_str = "✅ PASSED (visible)" if passed else "❌ BLOCKED"
                    cheat_print(_connection, f"3. Availability test: {test_res_str} (reason: {reason})")
                else:
                    test_res_str = "✅ ПРОЙДЕН (видимо)" if passed else "❌ ЗАБЛОКИРОВАН"
                    cheat_print(_connection, f"3. Тест доступности: {test_res_str} (причина: {reason})")
            except Exception as e:
                err_test_msg = f"3. Error in availability test: {e}" if is_en else f"3. Ошибка при тесте доступности: {e}"
                cheat_print(_connection, err_test_msg)
    else:
        cheat_print(_connection, "2. Active sim not found in world." if is_en else "2. Активный сим не найден в мире.")

    cheat_print(_connection, "==================================================")


@Command("ai_phone_inject", command_type=CommandType.Live if CommandType else 0)
def command_ai_phone_inject(_connection=None):
    """
    Forces injection of AI Social Phone affordance into active Sim right now.
    Usage in console: ai_phone_inject
    """
    is_en = _is_en()
    cheat_print(_connection, "[AI Social Phone] Forced injection into phone..." if is_en else "[AI Social Phone] Принудительная инъекция в телефон...")
    try:
        ok = inject_affordance_into_phone()
        status_str = ("✅ SUCCESS" if ok else "❌ FAILED") if is_en else ("✅ УСПЕШНО" if ok else "❌ НЕ УДАЛОСЬ")
        msg = f"[AI Social Phone] Injection result: {status_str}" if is_en else f"[AI Social Phone] Результат инъекции: {status_str}"
        cheat_print(_connection, msg, notify=True, title="AI Phone Inject")
    except Exception as e:
        cheat_print(_connection, f"[AI Social Phone] {'Error' if is_en else 'Ошибка'}: {e}", notify=True, title="AI Phone Error" if is_en else "AI Phone Ошибка")


@Command("ai_phone_cats", command_type=CommandType.Live if CommandType else 0)
def command_ai_phone_cats(_connection=None):
    """Lists all distinct phone categories found on the active Sim."""
    is_en = _is_en()
    active_sim, _ = _get_active_sim_and_info()
    if active_sim is None or not hasattr(active_sim, "_phone_affordances"):
        cheat_print(_connection, "Active sim not found." if is_en else "Активный сим не найден.")
        return
    cats = {}
    for aff in active_sim._phone_affordances:
        cat = getattr(aff, "category", None)
        if cat is not None:
            c_name = getattr(cat, "__name__", str(cat))
            c_id = getattr(cat, "guid64", 0)
            a_name = getattr(aff, "__name__", str(aff))
            if c_id not in cats:
                cats[c_id] = (c_name, a_name)
    cheat_print(_connection, f"=== {'Found categories in phone' if is_en else 'Найдено категорий в телефоне'}: {len(cats)} ===")
    for c_id, (c_name, a_name) in cats.items():
        cheat_print(_connection, f"ID {c_id}: {c_name} ({'example' if is_en else 'пример'}: {a_name})")


@Command("ai_phone_category", command_type=CommandType.Live if CommandType else 0)
def command_ai_phone_category(target: str = "social", _connection=None):
    """
    Switches phone category between Base Game 'social' (зелёные губы) and 'bunny' (Кролик общения).
    Usage in console:
      ai_phone_category social
      ai_phone_category bunny
    """
    is_en = _is_en()
    is_bunny = (str(target).strip().lower() in ("bunny", "rabbit", "кролик", "media"))
    ok = inject_affordance_into_phone(use_bunny=is_bunny)
    if is_en:
        target_name = "Social Bunny" if is_bunny else "Base Game: Social (green lips)"
    else:
        target_name = "Кролик общения (Social Bunny)" if is_bunny else "Базовая игра: Общение (зелёные губы)"
    if ok:
        msg = f"[AI Social Phone] Category switched to: {target_name}" if is_en else f"[AI Social Phone] Категория переключена на: {target_name}"
        cheat_print(_connection, msg, notify=True, title="AI Phone Category")
    else:
        msg = f"[AI Social Phone] Failed to assign category: {target_name}" if is_en else f"[AI Social Phone] Не удалось назначить категорию: {target_name}"
        cheat_print(_connection, msg, notify=True, title="AI Phone Error" if is_en else "AI Phone Ошибка")


@Command("ai_pc_inject", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_inject(_connection=None):
    """
    Forces injection of AI Social PC affordances into all computers right now.
    Usage in console: ai_pc_inject
    """
    is_en = _is_en()
    cheat_print(_connection, "[AI Social PC] Forcing injection into all computers..." if is_en else "[AI Social PC] Принудительный запуск инъекции во все компьютеры...")
    try:
        count = inject_affordance_into_computers()
        computers = find_all_computers()
        if is_en:
            msg = f"Success! Updated computers: {count} of {len(computers)} found."
        else:
            msg = f"Успешно! Обновлено компьютеров: {count} из {len(computers)} найденных."
        cheat_print(_connection, f"[AI Social PC] {msg}", notify=True, title="AI Social PC: Inject")
    except Exception as e:
        log_exception("Error in ai_pc_inject command", e)
        cheat_print(_connection, f"[AI Social PC] {'Injection error' if is_en else 'Ошибка при инъекции'}: {e}", notify=True, title="AI Social PC: Error" if is_en else "AI Social PC: Ошибка")


@Command("ai_pc_list", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_list(_connection=None):
    """
    Lists all super affordances on the nearest computer.
    Usage in console: ai_pc_list
    """
    is_en = _is_en()
    active_sim, _ = _get_active_sim_and_info()
    comp = _get_nearest_computer(active_sim)
    if comp is None:
        cheat_print(_connection, "[AI Social PC] No computers found on lot." if is_en else "[AI Social PC] Компьютеры на лоте не найдены.", notify=True, title="AI Social PC")
        return

    c_id = getattr(comp, "id", "Unknown")
    cheat_print(_connection, f"=== {'Actions list on computer ID' if is_en else 'Список действий на компьютере ID'}: {c_id} ===")
    sas = getattr(comp, "_super_affordances", ())
    cheat_print(_connection, f"{'Total actions' if is_en else 'Всего действий'}: {len(sas)}")
    top_items = []
    for i, sa in enumerate(sas[:35]):
        sa_name = getattr(sa, "__name__", str(sa))
        sa_guid = getattr(sa, "guid64", 0)
        marker = (" <=== OUR ACTION!" if is_en else " <=== НАШЕ ДЕЙСТВИЕ!") if (sa_guid == SYNAPSE_PC_TUNING_ID or "synapse" in sa_name.lower()) else ""
        line = f" {i+1:2d}. {sa_name} (ID: {sa_guid}){marker}"
        cheat_print(_connection, line)
        if marker:
            top_items.append(line)
    if len(sas) > 35:
        cheat_print(_connection, f" ... {'and' if is_en else 'и ещё'} {len(sas) - 35} {'more actions.' if is_en else 'действий.'}")
    if top_items:
        title = "AI Social PC: List" if is_en else "AI Social PC: Список"
        header = f"Found our actions in list: {len(top_items)}\n" if is_en else f"Найдено наших действий в списке: {len(top_items)}\n"
        cheat_print(_connection, header + "\n".join(top_items), notify=True, title=title)
    else:
        title = "AI Social PC: List" if is_en else "AI Social PC: Список"
        msg = f"Total actions: {len(sas)}. Our actions not in list!" if is_en else f"Всего действий: {len(sas)}. Наших действий в списке нет!"
        cheat_print(_connection, msg, notify=True, title=title)


@Command("ai_pc_test", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_test(_connection=None):
    """
    Tests visibility and passes of AI Chat interaction on nearest computer.
    Usage in console: ai_pc_test
    """
    is_en = _is_en()
    active_sim, active_info = _get_active_sim_and_info()
    if active_sim is None:
        cheat_print(_connection, "[AI Social PC] Error: no active sim in world." if is_en else "[AI Social PC] Ошибка: нет активного сима в мире.", notify=True, title="AI Social PC")
        return
    comp = _get_nearest_computer(active_sim)
    if comp is None:
        cheat_print(_connection, "[AI Social PC] Error: computer not found on lot." if is_en else "[AI Social PC] Ошибка: компьютер не найден на лоте.", notify=True, title="AI Social PC")
        return

    sim_name = f"{getattr(active_info, 'first_name', '')} {getattr(active_info, 'last_name', '')}".strip() or ("Sim" if is_en else "Сим")
    comp_name = getattr(comp, "__name__", str(comp))
    cheat_print(_connection, f"=== {'Interaction test' if is_en else 'Тест взаимодействия'}: {sim_name} -> {comp_name} ===")

    strategy = QueueInsertStrategy.LAST if QueueInsertStrategy else None
    context = InteractionContext(
        active_sim,
        InteractionContext.SOURCE_PIE_MENU,
        InteractionContext.Priority.High,
        insert_strategy=strategy,
    )

    test_lines = []
    aff_mgr = services.affordance_manager() if services else None
    our_aff = aff_mgr.get(SYNAPSE_PC_TUNING_ID) if aff_mgr else None
    if our_aff is None:
        cheat_print(_connection, f"[AI Social PC] {'Error: interaction' if is_en else 'Ошибка: взаимодействие'} {SYNAPSE_PC_TUNING_ID} {'not found.' if is_en else 'не найдено.'}")
        return

    affordances_to_test = [our_aff]
    for aff in affordances_to_test:
        a_name = getattr(aff, "__name__", str(aff))
        try:
            res = aff.test(target=comp, context=context)
            passed = bool(res)
            reason = getattr(res, "reason", "OK")
            if is_en:
                status = "AVAILABLE IN MENU" if passed else f"BLOCKED ({reason})"
            else:
                status = "ДОСТУПНО В МЕНЮ" if passed else f"ЗАБЛОКИРОВАНО ({reason})"
            cheat_print(_connection, f"• {a_name}: {status}")
            test_lines.append(f"{a_name}: {status}")
        except Exception as e:
            err_lbl = "Test error" if is_en else "Ошибка теста"
            cheat_print(_connection, f"• {a_name}: {err_lbl}: {e}")
            test_lines.append(f"{a_name}: {err_lbl}: {e}")

    if test_lines:
        t_title = f"Test: {sim_name}" if is_en else f"Тест: {sim_name}"
        cheat_print(_connection, "\n".join(test_lines), notify=True, title=t_title)


@Command("ai_pc_push", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_push(_connection=None):
    """
    Pushes the AI Chat interaction directly into the active Sim's interaction queue.
    Usage in console: ai_pc_push
    """
    is_en = _is_en()
    active_sim, active_info = _get_active_sim_and_info()
    if active_sim is None:
        cheat_print(_connection, "[AI Social PC] Error: no active sim." if is_en else "[AI Social PC] Ошибка: нет активного сима.")
        return
    comp = _get_nearest_computer(active_sim)
    if comp is None:
        cheat_print(_connection, "[AI Social PC] Error: computer not found." if is_en else "[AI Social PC] Ошибка: компьютер не найден.")
        return

    cheat_print(_connection, "[AI Social PC] Pushing interaction to sim queue..." if is_en else "[AI Social PC] Отправка действия в очередь сима...")
    try:
        start_pc_chat_session(active_info, computer_obj=comp)
        cheat_print(_connection, "[AI Social PC] Interlocutor picker opened!" if is_en else "[AI Social PC] Окно выбора собеседника открыто!")
    except Exception as e:
        cheat_print(_connection, f"[AI Social PC] {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_pc_clear", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_clear(_connection=None):
    """
    Clears all active PC chat session histories.
    """
    is_en = _is_en()
    count = len(_CHAT_SESSIONS)
    _CHAT_SESSIONS.clear()
    cheat_print(_connection, f"[AI Social PC] {'Cleared active chat sessions' if is_en else 'Очищено активных сессий переписки'}: {count}")


@Command("ai_pc_status", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_status(_connection=None):
    """
    Displays current PC chat sessions status.
    """
    is_en = _is_en()
    from ai_social_pc.delayed_replies import get_pending_replies_count
    pending_cnt = get_pending_replies_count()
    if is_en:
        cheat_print(_connection, f"[AI Social PC] Active chat pairs: {len(_CHAT_SESSIONS)}, Awaiting wake (in queue): {pending_cnt}")
    else:
        cheat_print(_connection, f"[AI Social PC] Активных пар переписки: {len(_CHAT_SESSIONS)}, Ожидают пробуждения (в очереди): {pending_cnt}")


@Command("ai_pc_queue", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_queue(_connection=None):
    """
    Displays pending offline replies queue.
    """
    is_en = _is_en()
    from ai_social_pc.delayed_replies import get_all_pending_replies
    queue = get_all_pending_replies()
    if not queue:
        cheat_print(_connection, "[AI Social PC] Offline replies queue is empty." if is_en else "[AI Social PC] Очередь отложенных ответов пуста.")
        return
    cheat_print(_connection, f"[AI Social PC] {'Awaiting reply in queue' if is_en else 'В очереди ожидают ответа'}: {len(queue)} {'sim(s)' if is_en else 'собеседник(ов)'}:")
    for item in queue:
        msg_preview = item.get('last_message', '')[:40]
        if is_en:
            cheat_print(_connection, f"  • Sim ID {item.get('recipient_id')} (message sent at {item.get('sent_sim_time')}): \"{msg_preview}...\"")
        else:
            cheat_print(_connection, f"  • Сим ID {item.get('recipient_id')} (сообщение отправлено в {item.get('sent_sim_time')}): «{msg_preview}...»")


@Command("ai_pc_force_wake", command_type=CommandType.Live if CommandType else 0)
def command_ai_pc_force_wake(_connection=None):
    """
    Forces immediate processing and delivery of all pending offline replies.
    """
    is_en = _is_en()
    from ai_social_pc.delayed_replies import check_and_process_pending_replies, get_pending_replies_count
    cnt = get_pending_replies_count()
    if cnt == 0:
        cheat_print(_connection, "[AI Social PC] No pending messages in queue to wake." if is_en else "[AI Social PC] Нет отложенных сообщений в очереди для пробуждения.")
        return
    if is_en:
        cheat_print(_connection, f"[AI Social PC] Forcing wake and reply generation for {cnt} sims...")
    else:
        cheat_print(_connection, f"[AI Social PC] Принудительно будим и запускаем генерацию ответов для {cnt} собеседников...")
    check_and_process_pending_replies(force_all=True)


@Command("ai_rel", "ai_chat_rel", command_type=CommandType.Live if CommandType else 0)
def command_ai_rel(_connection=None):
    """
    Prints friendship and romance scores with known Sims to the game cheat console.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_rel
    """
    is_en = _is_en()
    try:
        if services is None:
            cheat_print(_connection, "[AI Social PC] Services not available.")
            return
        active_sim = services.active_sim_info()
        if active_sim is None:
            cheat_print(_connection, "[AI Social PC] No active sim." if is_en else "[AI Social PC] Нет активного сима.")
            return

        tracker = getattr(active_sim, "relationship_tracker", None)
        if tracker is None:
            cheat_print(_connection, "[AI Social PC] Sim has no relationship_tracker." if is_en else "[AI Social PC] У сима нет relationship_tracker.")
            return

        from ai_social_pc.chat_manager import _get_friendship_track, _get_romance_track
        fr_track = _get_friendship_track()
        rom_track = _get_romance_track()

        first_name = getattr(active_sim, "first_name", "") or ""
        last_name = getattr(active_sim, "last_name", "") or ""
        sim_name = f"{first_name} {last_name}".strip() or ("Active Sim" if is_en else "Активный сим")

        cheat_print(_connection, f"=== {'Relationships for' if is_en else 'Отношения для'}: {sim_name} ===")
        sim_info_mgr = services.sim_info_manager()

        rel_service = services.relationship_service()
        found = 0
        if rel_service is not None and hasattr(rel_service, "target_sim_gen"):
            for target_id in rel_service.target_sim_gen(active_sim.sim_id):
                target_info = sim_info_mgr.get(target_id) if sim_info_mgr else None
                if target_info is None:
                    continue
                t_first = getattr(target_info, "first_name", "") or ""
                t_last = getattr(target_info, "last_name", "") or ""
                t_name = f"{t_first} {t_last}".strip() or f"Sim {target_id}"

                fr = tracker.get_relationship_score(target_id, fr_track) if fr_track else tracker.get_relationship_score(target_id)
                rom = tracker.get_relationship_score(target_id, rom_track) if rom_track else 0.0
                if is_en:
                    cheat_print(_connection, f"• {t_name}: Friendship = {fr:+.1f} | Romance = {rom:+.1f}")
                else:
                    cheat_print(_connection, f"• {t_name}: Дружба = {fr:+.1f} | Романтика = {rom:+.1f}")
                found += 1

        if found == 0:
            cheat_print(_connection, "No known sims or relationships." if is_en else "Нет известных симов или отношений.")
    except Exception as e:
        log_exception("Error running ai_rel command", e)
        cheat_print(_connection, f"[AI Social PC] {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_memory", "ai_memories", command_type=CommandType.Live if CommandType else 0)
def command_ai_memory(_connection=None):
    """
    Prints active episodic memories to the cheat console.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_memory
    """
    is_en = _is_en()
    try:
        from ai_social_pc.memory_manager import load_memories, get_active_memories
        all_memories = load_memories()
        if not all_memories:
            cheat_print(_connection, "[SIM MEMORIES] No memory records yet." if is_en else "[ПАМЯТЬ СИМОВ] Записей памяти пока нет.")
            return

        cheat_print(_connection, "=== SIM EPISODIC MEMORIES ===" if is_en else "=== ЭПИЗОДИЧЕСКАЯ ПАМЯТЬ СИМОВ ===")
        sim_info_mgr = services.sim_info_manager() if services is not None else None

        count = 0
        for pair_key, mem_list in all_memories.items():
            if pair_key.startswith("sim_"):
                try:
                    s_id = int(pair_key.split("_")[1])
                except (ValueError, IndexError):
                    continue
                name = f"Sim_{s_id}"
                if sim_info_mgr:
                    info = sim_info_mgr.get(s_id)
                    if info:
                        name = f"{getattr(info, 'first_name', '')} {getattr(info, 'last_name', '')}".strip() or name
                active = get_active_memories(s_id, 0)
                for m in active:
                    lbl = m.get("remaining_label", "Forever" if is_en else "Навсегда")
                    s = (m.get("summary_en") if is_en and m.get("summary_en") else m.get("summary", ""))
                    cheat_print(_connection, f"• [{lbl}] ({name}): {s}")
                    count += 1
            else:
                ids = pair_key.split("_")
                if len(ids) == 2:
                    try:
                        id_a, id_b = int(ids[0]), int(ids[1])
                    except ValueError:
                        continue
                    name_a, name_b = f"Sim_{id_a}", f"Sim_{id_b}"
                    if sim_info_mgr:
                        info_a = sim_info_mgr.get(id_a)
                        info_b = sim_info_mgr.get(id_b)
                        if info_a:
                            name_a = f"{getattr(info_a, 'first_name', '')} {getattr(info_a, 'last_name', '')}".strip() or name_a
                        if info_b:
                            name_b = f"{getattr(info_b, 'first_name', '')} {getattr(info_b, 'last_name', '')}".strip() or name_b

                    active = get_active_memories(id_a, id_b)
                    for m in active:
                        lbl = m.get("remaining_label", "Forever" if is_en else "Навсегда")
                        s = (m.get("summary_en") if is_en and m.get("summary_en") else m.get("summary", ""))
                        act_id = m.get("actor_id")
                        if act_id == id_a:
                            disp_name = f"{name_a} -> {name_b}"
                        elif act_id == id_b:
                            disp_name = f"{name_b} -> {name_a}"
                        else:
                            disp_name = f"{name_a} <-> {name_b}"
                        cheat_print(_connection, f"• [{lbl}] ({disp_name}): {s}")
                        count += 1

        if count == 0:
            cheat_print(_connection, "[SIM MEMORIES] No active memories (may have all expired)." if is_en else "[ПАМЯТЬ СИМОВ] Нет активных воспоминаний (возможно, срок всех истёк).")
        else:
            cheat_print(_connection, f"{'Total active memories' if is_en else 'Всего активных воспоминаний'}: {count}")
    except Exception as e:
        log_exception("Error in command_ai_memory", e)
        cheat_print(_connection, f"[AI Social PC] {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_test_memory", "ai_memory_test", command_type=CommandType.Live if CommandType else 0)
def command_ai_test_memory(event_name: str = "", _connection=None):
    """
    Test triggers an episodic memory on the currently active Sim.
    Usage:
    ai_test_memory intimacy
    ai_test_memory offspring
    ai_test_memory wedding
    ai_test_memory cheating
    ai_test_memory fire
    ai_test_memory promo
    ai_test_memory pregnancy
    """
    is_en = _is_en()
    try:
        from ai_social_pc.event_memory_manager import record_event_memory, EVENT_MEMORY_TEMPLATES
        active_sim = services.get_active_sim() if services is not None else None
        if not active_sim:
            cheat_print(_connection, "No active Sim selected!" if is_en else "Активный сим не выбран!")
            return

        actor_info = getattr(active_sim, "sim_info", active_sim)
        target_info = None
        hh = getattr(actor_info, "household", None)
        if hh:
            for s in getattr(hh, "sim_infos", []):
                if s and getattr(s, "sim_id", 0) != getattr(actor_info, "sim_id", 0):
                    target_info = s
                    break

        ev = event_name.lower().strip()
        if not ev:
            cheat_print(
                _connection,
                "Usage: ai_test_memory <event_name>\nAvailable: intimacy, group_sex, offspring, cheating, flirt, flirter, wedding, proposal, breakup, pregnancy, fire, promo, death, vampire, werewolf"
                if is_en else
                "Использование: ai_test_memory <событие>\nДоступно: intimacy, group_sex, offspring, cheating, flirt, flirter, wedding, proposal, breakup, pregnancy, fire, promo, death, vampire, werewolf"
            )
            return

        ev_map = {
            "intimacy": "intimacy_recent",
            "sex": "intimacy_recent",
            "solo": "intimacy_solo",
            "masturbation": "intimacy_solo",
            "group": "intimacy_group",
            "group_sex": "intimacy_group",
            "offspring": "intimacy_offspring_child",
            "kid": "intimacy_offspring_child",
            "offspring_solo": "intimacy_offspring_child_solo",
            "kid_solo": "intimacy_offspring_child_solo",
            "offspring_parents": "intimacy_offspring_parents",
            "offspring_parent_solo": "intimacy_offspring_parent_solo",
            "cheating": "intimacy_cheating",
            "cheated": "cheating_caught",
            "flirt": "romance_cheating_caught",
            "flirting": "romance_cheating_caught",
            "flirt_caught": "romance_cheating_caught",
            "flirter": "romance_cheating_flirter",
            "wedding": "wedding_newlyweds",
            "marriage": "wedding_newlyweds",
            "proposal": "proposal_accepted_proposer",
            "breakup": "breakup_divorce",
            "pregnancy": "pregnancy_mother",
            "baby": "baby_born",
            "birth": "baby_born",
            "fire": "house_fire",
            "promotion": "career_promoted",
            "promo": "career_promoted",
            "fired": "career_fired",
            "death": "death_loved_one",
            "vampire": "occult_vampire",
            "werewolf": "occult_werewolf",
        }

        tpl_key = ev_map.get(ev, ev)
        if tpl_key not in EVENT_MEMORY_TEMPLATES:
            cheat_print(_connection, f"Unknown event '{ev}'." if is_en else f"Неизвестное событие '{ev}'.")
            return

        record_event_memory(tpl_key, actor_info, target_sim_info=target_info)
        tpl = EVENT_MEMORY_TEMPLATES[tpl_key]
        days = tpl.get("days", 3)
        text = tpl.get("en" if is_en else "ru", "")
        cheat_print(_connection, f"[AI MEMORY TEST] Recorded '{tpl_key}' ({days} days): {text}" if is_en else f"[ТЕСТ ПАМЯТИ] Записано событие '{tpl_key}' ({days} дн.): {text}")
    except Exception as e:
        log_exception("Error in command_ai_test_memory", e)
        cheat_print(_connection, f"Error: {e}")


@Command("ai_memory_clear", "ai_mem_clear", command_type=CommandType.Live if CommandType else 0)
def command_ai_memory_clear(_connection=None):
    """
    Clears all stored episodic memories for all Sims.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_memory_clear
    """
    is_en = _is_en()
    try:
        from ai_social_pc.memory_manager import clear_all_memories
        cleared_count = clear_all_memories()
        msg = f"[SIM MEMORIES] Cleared memory records: {cleared_count}" if is_en else f"[ПАМЯТЬ СИМОВ] Очищено записей памяти: {cleared_count}"
        title = "Memories Cleared" if is_en else "Память очищена"
        cheat_print(_connection, msg, notify=True, title=title)
    except Exception as e:
        log_exception("Error in command_ai_memory_clear", e)
        cheat_print(_connection, f"[AI Social PC] {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_memory_clear_active", "ai_clear_active_memory", command_type=CommandType.Live if CommandType else 0)
def command_ai_memory_clear_active(_connection=None):
    """
    Clears all episodic memories for the currently active Sim.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_memory_clear_active
    """
    is_en = _is_en()
    try:
        active_sim = services.get_active_sim() if services is not None else None
        if not active_sim:
            cheat_print(_connection, "No active Sim selected!" if is_en else "Активный сим не выбран!")
            return
        sim_id = getattr(active_sim, "sim_id", 0)
        from ai_social_pc.memory_manager import clear_memories_for_sim
        cleared_count = clear_memories_for_sim(sim_id)
        msg = f"[SIM MEMORIES] Cleared {cleared_count} memories for active Sim." if is_en else f"[ПАМЯТЬ СИМОВ] Очищено {cleared_count} воспоминаний активного сима."
        title = "Memories Cleared" if is_en else "Память очищена"
        cheat_print(_connection, msg, notify=True, title=title)
    except Exception as e:
        log_exception("Error in command_ai_memory_clear_active", e)
        cheat_print(_connection, f"[AI Social PC] {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_npc_chat", "ai.npc_chat", "ai_npc_autonomy", "ai_npc_group", "npc_chat", command_type=CommandType.Live if CommandType else 0)
def command_ai_npc_chat(*args, _connection=None, **kwargs):
    """
    Forces an immediate autonomous conversation between NPCs in a group.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_npc_chat             - picks any group with 2+ online NPCs
    ai_npc_chat Friends     - triggers in group whose name contains 'Friends'
    """
    is_en = _is_en()
    tag = "[NPC AUTONOMY]" if is_en else "[NPC АВТОНОМИЯ]"
    title = "NPC Autonomy" if is_en else "Автономия NPC"
    try:
        from ai_social_pc.npc_autonomy import trigger_npc_group_autonomy
        filter_str = " ".join([str(a) for a in args]).strip() if args else ""
        if is_en:
            start_msg = f"{tag} Triggering forced NPC conversation{' (filter: ' + filter_str + ')' if filter_str else ''}..."
        else:
            start_msg = f"{tag} Запуск принудительного диалога NPC{' (фильтр: ' + filter_str + ')' if filter_str else ''}..."
        cheat_print(_connection, start_msg)
        ok, msg = trigger_npc_group_autonomy(force=True, target_group_filter=filter_str)
        cheat_print(_connection, f"{tag} {msg}", notify=ok, title=title)
    except Exception as e:
        log_exception("Error in command_ai_npc_chat", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_npc_status", "ai.npc_status", "ai_npc_debug", command_type=CommandType.Live if CommandType else 0)
def command_ai_npc_status(_connection=None):
    """
    Prints diagnostic information about groups, online status of NPCs, and autonomy alarm.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_npc_status
    """
    is_en = _is_en()
    tag = "[NPC AUTONOMY]" if is_en else "[NPC АВТОНОМИЯ]"
    try:
        from ai_social_pc.npc_autonomy import get_npc_autonomy_debug_info
        info_text = get_npc_autonomy_debug_info()
        for line in info_text.splitlines():
            cheat_print(_connection, line)
    except Exception as e:
        log_exception("Error in command_ai_npc_status", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_npc_alarm", "ai.npc_alarm", command_type=CommandType.Live if CommandType else 0)
def command_ai_npc_alarm(_connection=None):
    """
    Restarts or checks the background periodic alarm for NPC autonomy.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_npc_alarm
    """
    is_en = _is_en()
    tag = "[NPC AUTONOMY]" if is_en else "[NPC АВТОНОМИЯ]"
    title = "NPC Autonomy" if is_en else "Автономия NPC"
    try:
        from ai_social_pc.npc_autonomy import stop_npc_group_autonomy_alarm, start_npc_group_autonomy_alarm
        stop_npc_group_autonomy_alarm()
        start_npc_group_autonomy_alarm()
        if is_en:
            msg = f"{tag} Game alarm restarted (checking every 60 sim-minutes)."
        else:
            msg = f"{tag} Игровой таймер перезапущен (проверка каждые 60 сим-минут)."
        cheat_print(_connection, msg, notify=True, title=title)
    except Exception as e:
        log_exception("Error in command_ai_npc_alarm", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_friend_chat", "ai.friend_chat", "ai_friend_msg", "friend_chat", command_type=CommandType.Live if CommandType else 0)
def command_ai_friend_chat(*args, _connection=None, **kwargs):
    """
    Forces an immediate spontaneous incoming message from a friend (Friends and above) in direct chat.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_friend_chat          - picks any eligible friend online
    ai_friend_chat Bella    - triggers from friend whose name matches 'Bella'
    """
    is_en = _is_en()
    tag = "[FRIEND CHAT]" if is_en else "[ДРУЖЕСКИЙ ЧАТ]"
    title = "Friend Message" if is_en else "Сообщение от друга"
    try:
        from ai_social_pc.friend_autonomy import trigger_friend_autonomy
        filter_str = " ".join([str(a) for a in args]).strip() if args else ""
        if is_en:
            start_msg = f"{tag} Triggering spontaneous message from friend{' (filter: ' + filter_str + ')' if filter_str else ''}..."
        else:
            start_msg = f"{tag} Запуск спонтанного сообщения от друга{' (фильтр: ' + filter_str + ')' if filter_str else ''}..."
        cheat_print(_connection, start_msg)
        ok, msg = trigger_friend_autonomy(force=True, target_friend_filter=filter_str)
        cheat_print(_connection, f"{tag} {msg}", notify=ok, title=title)
    except Exception as e:
        log_exception("Error in command_ai_friend_chat", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_friend_status", "ai.friend_status", "ai_friend_debug", command_type=CommandType.Live if CommandType else 0)
def command_ai_friend_status(_connection=None):
    """
    Prints diagnostic information about friends, their relationship levels, online/work status, and cooldowns.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_friend_status
    """
    is_en = _is_en()
    tag = "[FRIEND CHAT]" if is_en else "[ДРУЖЕСКИЙ ЧАТ]"
    try:
        from ai_social_pc.friend_autonomy import get_friend_autonomy_debug_info
        info_text = get_friend_autonomy_debug_info()
        for line in info_text.splitlines():
            cheat_print(_connection, line)
    except Exception as e:
        log_exception("Error in command_ai_friend_status", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_friend_alarm", "ai.friend_alarm", command_type=CommandType.Live if CommandType else 0)
def command_ai_friend_alarm(_connection=None):
    """
    Restarts or checks the background periodic alarm for friend autonomy.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_friend_alarm
    """
    is_en = _is_en()
    tag = "[FRIEND CHAT]" if is_en else "[ДРУЖЕСКИЙ ЧАТ]"
    title = "Friend Messages" if is_en else "Сообщения друзей"
    try:
        from ai_social_pc.friend_autonomy import stop_friend_autonomy_alarm, start_friend_autonomy_alarm
        stop_friend_autonomy_alarm()
        start_friend_autonomy_alarm()
        if is_en:
            msg = f"{tag} Friend autonomy game alarm restarted (checking every 60 sim-minutes)."
        else:
            msg = f"{tag} Игровой таймер друзей перезапущен (проверка каждые 60 сим-минут)."
        cheat_print(_connection, msg, notify=True, title=title)
    except Exception as e:
        log_exception("Error in command_ai_friend_alarm", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_direct_talk", "ai.direct_talk", "direct_talk", command_type=CommandType.Live if CommandType else 0)
def command_ai_direct_talk(*args, _connection=None, **kwargs):
    """
    Called by the pie-menu interaction «Talk (AI)...» or via console.
    Usage:
    ai_direct_talk <target_sim_id>
    """
    is_en = _is_en()
    tag = "[DIRECT DIALOGUE]" if is_en else "[ЖИВОЙ ДИАЛОГ]"
    try:
        from ai_social_pc.direct_dialogue import start_direct_dialogue
        target = args[0] if args else None
        start_direct_dialogue(target)
    except Exception as e:
        log_exception("Error in command_ai_direct_talk", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_direct_talk_ww", "ai.direct_talk_ww", "direct_talk_ww", command_type=CommandType.Live if CommandType else 0)
def command_ai_direct_talk_ww(*args, _connection=None, **kwargs):
    """
    Called by the pie-menu interaction «Talk during sex (AI)...» or via console.
    Usage:
    ai_direct_talk_ww <target_sim_id>
    """
    is_en = _is_en()
    tag = "[INTIMATE DIALOGUE]" if is_en else "[ИНТИМНЫЙ ДИАЛОГ]"
    try:
        from ai_social_pc.direct_dialogue import start_direct_dialogue
        target = args[0] if args else None
        start_direct_dialogue(target, is_ww_sex=True)
    except Exception as e:
        log_exception("Error in command_ai_direct_talk_ww", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_talk", "ai.talk", "ai_talk_test", command_type=CommandType.Live if CommandType else 0)
def command_ai_talk(*args, _connection=None, **kwargs):
    """
    Test direct dialogue with a Sim by name or target Sim ID from cheat console.
    Usage:
    ai_talk <Sim_Name>
    """
    is_en = _is_en()
    tag = "[DIRECT DIALOGUE]" if is_en else "[ЖИВОЙ ДИАЛОГ]"
    try:
        from ai_social_pc.direct_dialogue import start_direct_dialogue
        if not args:
            cheat_print(_connection, "Usage: ai_talk <Sim_Name>" if is_en else "Использование: ai_talk <Имя_Сима>")
            return

        filter_name = " ".join([str(a) for a in args]).strip().lower()
        if services is not None:
            sim_info_mgr = services.sim_info_manager()
            found_sim_info = None
            for s_info in sim_info_mgr.get_all():
                f_name = (getattr(s_info, "first_name", "") or "").lower()
                l_name = (getattr(s_info, "last_name", "") or "").lower()
                full_name = f"{f_name} {l_name}".strip()
                if filter_name in full_name or filter_name in f_name or filter_name in l_name:
                    found_sim_info = s_info
                    break

            if found_sim_info is not None:
                full_n = f"{getattr(found_sim_info, 'first_name', '')} {getattr(found_sim_info, 'last_name', '')}".strip()
                msg = f"{tag} Opening dialogue with: {full_n}..." if is_en else f"{tag} Открываем диалог с: {full_n}..."
                cheat_print(_connection, msg)
                start_direct_dialogue(found_sim_info)
            else:
                msg = f"{tag} Sim matching '{filter_name}' not found." if is_en else f"{tag} Персонаж по запросу '{filter_name}' не найден."
                cheat_print(_connection, msg)
    except Exception as e:
        log_exception("Error in command_ai_talk", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_visit", "ai.visit", "ai_invite", command_type=CommandType.Live if CommandType else 0)
def command_ai_visit(*args, _connection=None, **kwargs):
    """
    Test command to immediately trigger the visit_lot post-dialogue action for a Sim.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_visit <Sim_Name>
    """
    is_en = _is_en()
    tag = "[ACTION DO]" if is_en else "[ДЕЙСТВИЕ DO]"
    if not args:
        cheat_print(_connection, "Usage: ai_visit <Sim_Name>" if is_en else "Использование: ai_visit <Имя_Сима>")
        return
    sim_target = " ".join([str(a) for a in args]).strip()
    active_sim, active_info = _get_active_sim_and_info()
    if active_info is None:
        cheat_print(_connection, f"{tag} Error: active sim not found." if is_en else f"{tag} Ошибка: активный сим не найден.")
        return
    cheat_print(_connection, f"{tag} Testing arrival for: {sim_target}..." if is_en else f"{tag} Тестирование прихода сима: {sim_target}...")
    try:
        from ai_social_pc.action_executor import execute_post_chat_action
        def _console_feedback(text):
            cheat_print(_connection, f"{text}")
        execute_post_chat_action(sim_target, "visit_lot", active_info, None, feedback_fn=_console_feedback)
    except Exception as e:
        log_exception("Error in command_ai_visit", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_sex", "ai.sex", command_type=CommandType.Live if CommandType else 0)
def command_ai_sex(*args, _connection=None, **kwargs):
    """
    Test command to immediately trigger the WickedWhims intimacy post-dialogue action with a Sim.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_sex <Sim_Name>
    """
    is_en = _is_en()
    tag = "[ACTION DO]" if is_en else "[ДЕЙСТВИЕ DO]"
    if not args:
        cheat_print(_connection, "Usage: ai_sex <Sim_Name>" if is_en else "Использование: ai_sex <Имя_Сима>")
        return
    sim_target = " ".join([str(a) for a in args]).strip()
    active_sim, active_info = _get_active_sim_and_info()
    if active_info is None:
        cheat_print(_connection, f"{tag} Error: active sim not found." if is_en else f"{tag} Ошибка: активный сим не найден.")
        return
    cheat_print(_connection, f"{tag} Testing intimacy with: {sim_target}..." if is_en else f"{tag} Запуск интима с: {sim_target}...")
    try:
        from ai_social_pc.action_executor import execute_post_chat_action
        def _console_feedback(text):
            cheat_print(_connection, f"{text}")
        execute_post_chat_action(sim_target, "wicked_sex", active_info, None, feedback_fn=_console_feedback)
    except Exception as e:
        log_exception("Error in command_ai_sex", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_travel", "ai.travel", command_type=CommandType.Live if CommandType else 0)
def command_ai_travel(*args, _connection=None, **kwargs):
    """
    Test command to immediately trigger the travel_together post-dialogue action with one or more Sims.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_travel <Sim_Name>
    ai_travel Sim1, Sim2
    """
    is_en = _is_en()
    tag = "[ACTION DO]" if is_en else "[ДЕЙСТВИЕ DO]"
    if not args:
        cheat_print(_connection, "Usage: ai_travel <Sim_Name(s)>" if is_en else "Использование: ai_travel <Имя_Сима_или_несколько>")
        return
    sim_target = " ".join([str(a) for a in args]).strip()
    active_sim, active_info = _get_active_sim_and_info()
    if active_info is None:
        cheat_print(_connection, f"{tag} Error: active sim not found." if is_en else f"{tag} Ошибка: активный сим не найден.")
        return
    cheat_print(_connection, f"{tag} Testing travel together with: {sim_target}..." if is_en else f"{tag} Запуск совместной прогулки с: {sim_target}...")
    try:
        from ai_social_pc.action_executor import execute_post_chat_action
        def _console_feedback(text):
            cheat_print(_connection, f"{text}")
        execute_post_chat_action(sim_target, "travel_together", active_info, None, feedback_fn=_console_feedback)
    except Exception as e:
        log_exception("Error in command_ai_travel", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_date", "ai.date", command_type=CommandType.Live if CommandType else 0)
def command_ai_date(*args, _connection=None, **kwargs):
    """
    Test command to immediately trigger standard Base Game Date with a Sim.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_date <Sim_Name>
    """
    is_en = _is_en()
    tag = "[ACTION DO]" if is_en else "[ДЕЙСТВИЕ DO]"
    if not args:
        cheat_print(_connection, "Usage: ai_date <Sim_Name>" if is_en else "Использование: ai_date <Имя_Сима>")
        return
    sim_target = " ".join([str(a) for a in args]).strip()
    active_sim, active_info = _get_active_sim_and_info()
    if active_info is None:
        cheat_print(_connection, f"{tag} Error: active sim not found." if is_en else f"{tag} Ошибка: активный сим не найден.")
        return
    cheat_print(_connection, f"{tag} Testing Base Game date with: {sim_target}..." if is_en else f"{tag} Запуск базового свидания с: {sim_target}...")
    try:
        from ai_social_pc.action_executor import execute_post_chat_action
        def _console_feedback(text):
            cheat_print(_connection, f"{text}")
        execute_post_chat_action(sim_target, "ask_on_date", active_info, None, feedback_fn=_console_feedback)
    except Exception as e:
        log_exception("Error in command_ai_date", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


@Command("ai_money", "ai.money", command_type=CommandType.Live if CommandType else 0)
def command_ai_money(*args, _connection=None, **kwargs):
    """
    Test command to test money transfer / loans.
    Usage in Sims 4 console (Ctrl+Shift+C):
    ai_money 500             -> NPC sends you 500§
    ai_money -500            -> You send NPC 500§
    ai_money Gail 1000       -> Gail sends you 1000§
    ai_money Gail -1000      -> You send Gail 1000§
    """
    is_en = _is_en()
    tag = "[ACTION DO]" if is_en else "[ДЕЙСТВИЕ DO]"
    if not args:
        cheat_print(_connection, "Usage: ai_money [Sim_Name] [Amount]" if is_en else "Использование: ai_money [Имя_Сима] [Сумма]")
        return
    active_sim, active_info = _get_active_sim_and_info()
    if active_info is None:
        cheat_print(_connection, f"{tag} Error: active sim not found." if is_en else f"{tag} Ошибка: активный сим не найден.")
        return

    target_sim = ""
    amount = 500
    is_send = False

    parts = list(args)
    last_p = str(parts[-1]).strip()
    try:
        val = int(last_p)
        if val < 0:
            is_send = True
            amount = abs(val)
        else:
            amount = val
        parts = parts[:-1]
    except Exception:
        amount = 500

    if parts:
        target_sim = " ".join([str(p) for p in parts]).strip()

    action = f"send_money:{amount}" if is_send else f"receive_money:{amount}"
    cheat_print(_connection, f"{tag} Testing money: {action} with {target_sim or 'interlocutor'}..." if is_en else f"{tag} Тестирование денег: {action} с {target_sim or 'собеседником'}...")
    try:
        from ai_social_pc.action_executor import execute_post_chat_action
        def _console_feedback(text):
            cheat_print(_connection, f"{text}")
        execute_post_chat_action(target_sim, action, active_info, None, feedback_fn=_console_feedback)
    except Exception as e:
        log_exception("Error in command_ai_money", e)
        cheat_print(_connection, f"{tag} {'Error' if is_en else 'Ошибка'}: {e}")


# =========================================================================
# SYNAPSE SIMPLIFIED AUTONOMOUS DIALOGUE COMMANDS (CONSOLES & TESTING)
# =========================================================================

@Command("synapse.simplified_scan", "synapse.simp_scan", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_scan(*args, _connection=None, **kwargs):
    """Scans and outputs active chatting groups and nearby candidate Sims."""
    try:
        from ai_social_pc.simplified_dialogue import scan_conversing_details
        data = scan_conversing_details()
        active_groups = data.get("active_groups", [])
        candidates = data.get("potential_candidates", [])
        all_sims = data.get("all_sims", [])

        cheat_print(_connection, "=== [СКАНИРОВАНИЕ УПРОЩЁННОГО ОБЩЕНИЯ] ===")
        cheat_print(_connection, f"Всего симов на участке: {len(all_sims)}")

        cheat_print(_connection, "[АКТИВНЫЕ РАЗГОВОРЫ В ИГРЕ]:")
        if not active_groups:
            cheat_print(_connection, "  (Нет активных разговоров. Симы сейчас не общаются)")
        else:
            for i, g in enumerate(active_groups, 1):
                g_type = "Пара (2 сима)" if g["type"] == "pair" else f"Группа ({g['count']} симов)"
                members_str = ", ".join([f"{m['name']} [{m['mood']}{', Семья' if m['selectable'] else ''}]" for m in g['members']])
                cheat_print(_connection, f"  #{i} {g_type} в '{g['location']}':")
                cheat_print(_connection, f"     Участники: {members_str}")

        cheat_print(_connection, "")
        cheat_print(_connection, f"[ПОТЕНЦИАЛЬНЫЕ КАНДИДАТЫ РЯДОМ] (найдено: {len(candidates)}):")
        if not candidates:
            cheat_print(_connection, "  (Свободных кандидатов рядом не найдено)")
            if all_sims:
                cheat_print(_connection, "  [Обнаруженные симы на участке]:")
                for s in all_sims:
                    hh_str = "Активная семья" if s["household"] else "Гость/Горожанин"
                    av_str = "Доступен" if s["available"] else "Занят/Спит"
                    cheat_print(_connection, f"    • {s['name']} ({hh_str}, {s['mood']}, {av_str}, комната: '{s['location']}')")
        else:
            for j, c in enumerate(candidates[:6], 1):
                dist_str = f"~{c['distance']}м" if c.get('distance', -1) > 0 else "в одной комнате"
                cheat_print(_connection, f"  #{j} {c['sim_a']} + {c['sim_b']} [{dist_str}, '{c['location']}']")
                cheat_print(_connection, f"     Отношения: {c['relationship']} | Настроения: {c['mood_a']} / {c['mood_b']}")

        cheat_print(_connection, "")
        cheat_print(_connection, "Подсказка: введите 'synapse.run_simplified' для запуска диалога.")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_scan", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.simplified_candidates", "synapse.simp_candidates", "synapse.simp_groups", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_candidates(*args, _connection=None, **kwargs):
    """Outputs candidate pairs/groups for simplified dialogue."""
    try:
        from ai_social_pc.simplified_dialogue import find_potential_candidates, find_conversing_groups
        active_groups = find_conversing_groups()
        candidates = find_potential_candidates()

        cheat_print(_connection, "=== [КАНДИДАТЫ ДЛЯ ОБЩЕНИЯ НА УЧАСТКЕ] ===")
        cheat_print(_connection, f"• Активных групп/пар сейчас разговаривают: {len(active_groups)}")
        cheat_print(_connection, f"• Найдено потенциальных кандидатов рядом: {len(candidates)}")
        if not candidates:
            cheat_print(_connection, "  Кандидатов не найдено. Симы должны быть доступны и находиться в одной комнате или поблизости.")
        else:
            for i, c in enumerate(candidates, 1):
                dist_str = f"~{c['distance']}м" if c.get('distance', -1) > 0 else "в одной комнате"
                cheat_print(_connection, f"  Кандидат #{i}: {c['sim_a']} & {c['sim_b']}")
                cheat_print(_connection, f"     Локация: {c['location']} ({dist_str}) | {c['relationship']}")
                cheat_print(_connection, f"     Настроения: {c['sim_a']} ({c['mood_a']}), {c['sim_b']} ({c['mood_b']})")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_candidates", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.simplified_status", "synapse.simp_status", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_status(*args, _connection=None, **kwargs):
    """Displays operational status of simplified dialogue mode."""
    try:
        from ai_social_pc.simplified_dialogue import get_simplified_status
        st = get_simplified_status()
        cheat_print(_connection, "=== [СТАТУС: УПРОЩЁННОЕ ОБЩЕНИЕ] ===")
        cheat_print(_connection, f"• Включено в настройках: {'ДА' if st['enabled'] else 'НЕТ'}")
        if st['director_conflict']:
            cheat_print(_connection, "• [!] ВНИМАНИЕ: Режиссёр общения включен! Упрощённое общение заблокировано взаимным исключением.")
        cheat_print(_connection, f"• Пауза тишины: {st['silence_sec']} сек. (Осталось: {st['remaining_sec']} сек.)")
        cheat_print(_connection, f"• Шанс генерации: {st['chance_pct']}%")
        cheat_print(_connection, f"• Игра на паузе: {'ДА' if st['is_paused'] else 'НЕТ'}")
        cheat_print(_connection, f"• Запрос в процессе (in_flight): {'ДА' if st['in_flight'] else 'НЕТ'}")
        cheat_print(_connection, f"• 3D Облачка: {'ВКЛ' if st['balloon'] else 'ВЫКЛ'} | Уведомления: {'ВКЛ' if st['notification'] else 'ВЫКЛ'}")
        cheat_print(_connection, f"• Активных групп общения: {st.get('active_groups_count', 0)} (пар: {st.get('pairs_count', 0)}, групп 3+: {st.get('groups_3plus_count', 0)})")
        for g in st.get('conversing_groups', []):
            cheat_print(_connection, f"    -> {g}")
        cheat_print(_connection, f"• Потенциальных кандидатов рядом: {st.get('candidates_count', 0)}")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_status", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.run_simplified", "synapse.run_simp", "synapse.simplified_run", "synapse.simp_run", command_type=CommandType.Live if CommandType else 0)
def command_synapse_run_simplified(*args, _connection=None, **kwargs):
    """Forces an immediate simplified dialogue execution."""
    try:
        from ai_social_pc.simplified_dialogue import force_trigger_simplified_dialogue
        force_trigger_simplified_dialogue(_connection=_connection)
    except Exception as e:
        log_exception("Error in command_synapse_run_simplified", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.simplified_reset", "synapse.simp_reset", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_reset(*args, _connection=None, **kwargs):
    """Resets silence timer for simplified dialogue."""
    try:
        from ai_social_pc.simplified_dialogue import reset_simplified_silence
        reset_simplified_silence()
        cheat_print(_connection, "[УСПЕХ] Пауза тишины сброшена в 0! Следующий диалог сгенерируется при первой возможности.")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_reset", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.simplified_chance", "synapse.simp_chance", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_chance(pct_str: str = "100", _connection=None, **kwargs):
    """Sets trigger chance % for simplified dialogue."""
    try:
        from ai_thought_reader.config import get_simplified_dialogue_timers, set_simplified_dialogue_timers
        curr = get_simplified_dialogue_timers()
        val = max(1, min(100, int(pct_str)))
        set_simplified_dialogue_timers(curr.get("silence_sec", 180), val)
        cheat_print(_connection, f"[УСПЕХ] Шанс упрощённого общения установлен на {val}%")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_chance", e)
        cheat_print(_connection, f"Error: {e}")


@Command("synapse.simplified_silence", "synapse.simp_silence", command_type=CommandType.Live if CommandType else 0)
def command_synapse_simplified_silence(sec_str: str = "30", _connection=None, **kwargs):
    """Sets silence cooldown in seconds for simplified dialogue."""
    try:
        from ai_thought_reader.config import get_simplified_dialogue_timers, set_simplified_dialogue_timers
        curr = get_simplified_dialogue_timers()
        val = max(5, int(sec_str))
        set_simplified_dialogue_timers(val, curr.get("trigger_chance_pct", 40))
        cheat_print(_connection, f"[УСПЕХ] Пауза тишины упрощённого общения установлена на {val} сек.")
    except Exception as e:
        log_exception("Error in command_synapse_simplified_silence", e)
        cheat_print(_connection, f"Error: {e}")


# =========================================================================
# SYNAPSE DIRECTOR TESTING & SCENE COMMANDS
# =========================================================================

@Command('synapse.scan', 'synapse.scan_all', command_type=CommandType.Live if CommandType else 0)
def command_synapse_scan(_connection=None):
    """
    [РЕЖИССЁР] Сканер всех возможных действий Режиссёра на лоте прямо сейчас.
    Выводит полный список действий в формате: [ДА] / [НЕТ] (причина).
    """
    is_en = _is_en()
    cheat_print(_connection, '=== [SYNAPSE DIRECTOR: GLOBAL SCANNER] ===' if is_en else '=== [РЕЖИССЁР: СКАНЕР ВСЕХ ДЕЙСТВИЙ] ===')
    try:
        from ai_social_pc.director_testing import scan_all_triggers_report
        report = scan_all_triggers_report()
        yes_count = 0
        for item in report:
            tid = item['id']
            name = item['name']
            is_met = item['is_met']
            details = item['details']
            if is_met:
                yes_count += 1
                cheat_print(_connection, f' [ДА]  {name} ({tid}) -> {details}')
            else:
                cheat_print(_connection, f' [НЕТ] {name} ({tid}) -> {details}')

        summary = f'\nИТОГ: Готово к срабатыванию {yes_count} из {len(report)} действий.' if not is_en else f'\nSUMMARY: {yes_count} of {len(report)} actions ready.'
        cheat_print(_connection, summary)
    except Exception as e:
        log_exception('Error in command_synapse_scan', e)
        cheat_print(_connection, f'Error in scan: {e}')


@Command('synapse.test', command_type=CommandType.Live if CommandType else 0)
def command_synapse_test(trigger_id: str = '', _connection=None):
    """
    [РЕЖИССЁР] Точечная проверка условий для конкретного действия.
    Использование: synapse.test cooking_together
    """
    is_en = _is_en()
    if not trigger_id:
        cheat_print(_connection, 'Укажите ID действия! Пример: synapse.test cooking_together' if not is_en else 'Specify action ID! Example: synapse.test cooking_together')
        cheat_print(_connection, 'Используйте synapse.scan, чтобы увидеть список ID.' if not is_en else 'Use synapse.scan to see all action IDs.')
        return

    tid = str(trigger_id).strip().lower()
    cheat_print(_connection, f'=== [ПРОВЕРКА УСЛОВИЯ: {tid}] ===' if not is_en else f'=== [TEST CONDITION: {tid}] ===')
    try:
        from ai_social_pc.director_testing import evaluate_trigger_conditions, TRIGGER_MAP
        meta = TRIGGER_MAP.get(tid, {})
        name = meta.get('name_ru' if not is_en else 'name_en', tid)
        is_met, details, _ = evaluate_trigger_conditions(tid)

        if is_met:
            cheat_print(_connection, f'[ИТОГ: ВЫПОЛНЕНО] {name} ({tid})')
            cheat_print(_connection, f'Детали: {details}')
        else:
            cheat_print(_connection, f'[ИТОГ: НЕ ВЫПОЛНЕНО] {name} ({tid})')
            cheat_print(_connection, f'Причина: {details}')
    except Exception as e:
        log_exception('Error in command_synapse_test', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.run', command_type=CommandType.Live if CommandType else 0)
def command_synapse_run(trigger_id: str = '', force_flag: str = '', _connection=None):
    """
    [РЕЖИССЁР] Запуск действия Режиссёра.
    Использование:
      synapse.run cooking_together        - запуск при наличии условий
      synapse.run cooking_together force  - принудительный запуск без условий
    """
    is_en = _is_en()
    if not trigger_id:
        cheat_print(_connection, 'Укажите ID действия! Пример: synapse.run cooking_together' if not is_en else 'Specify action ID! Example: synapse.run cooking_together')
        return

    tid = str(trigger_id).strip().lower()
    force = str(force_flag).strip().lower() in ('force', 'true', '1')

    force_lbl = ' (FORCE)' if force else ''
    cheat_print(_connection, f'=== [ЗАПУСК ДЕЙСТВИЯ: {tid}{force_lbl}] ===' if not is_en else f'=== [RUN ACTION: {tid}{force_lbl}] ===')
    try:
        from ai_social_pc.director_testing import evaluate_trigger_conditions, generate_forced_trigger_spark, TRIGGER_MAP
        from ai_social_pc.autonomous_director import dispatch_autonomous_scene, is_scene_in_flight

        meta = TRIGGER_MAP.get(tid, {})
        name = meta.get('name_ru' if not is_en else 'name_en', tid)

        if force:
            spark = generate_forced_trigger_spark(tid)
            if not spark:
                cheat_print(_connection, f'[ОТКАЗ] Не удалось создать принудительную сцену для {name} ({tid}). На лоте недостаточно симов.')
                return
            details = 'Принудительный запуск (FORCE)'
        else:
            is_met, details, spark = evaluate_trigger_conditions(tid)
            if not is_met or not spark:
                cheat_print(_connection, f'[ОТКАЗ: УСЛОВИЯ НЕТ] Действие \'{name}\' ({tid}) отклонено!')
                cheat_print(_connection, f'Причина: {details}')
                cheat_print(_connection, f'Подсказка: Для принудительного теста используйте:\nsynapse.run {tid} force')
                return

        if is_scene_in_flight():
            cheat_print(_connection, 'Внимание: В данный момент сцена уже воспроизводится! Подождите пару секунд.')
            return

        cheat_print(_connection, f'[УСЛОВИЕ ЕСТЬ!] {name} ({tid})')
        cheat_print(_connection, f'Детали: {details}')
        cheat_print(_connection, 'Отправка запроса в Synapse AI Bridge...')

        dispatched = dispatch_autonomous_scene(spark, force=force)
        if dispatched:
            cheat_print(_connection, 'Успех! Сцена поставлена в очередь и скоро воспроизведется над симами.')
        else:
            cheat_print(_connection, 'Ошибка: Сцена не была запущена диспетчером.')
    except Exception as e:
        log_exception('Error in command_synapse_run', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.force', command_type=CommandType.Live if CommandType else 0)
def command_synapse_force(trigger_id: str = '', _connection=None):
    """
    [РЕЖИССЁР] Принудительный запуск любого сценария Режиссёра.
    Использование: synapse.force cooking_together
    """
    command_synapse_run(trigger_id, 'force', _connection=_connection)


@Command('synapse.reset_auto', 'synapse.director_reset', command_type=CommandType.Live if CommandType else 0)
def command_synapse_reset_auto(_connection=None):
    """Сбрасывает все кулдауны и лимиты Режиссёра для мгновенного тестирования."""
    try:
        from ai_social_pc.autonomous_director import reset_all_cooldowns
        reset_all_cooldowns()
        cheat_print(_connection, '[СБРОС] Все кулдауны и счетчики Автономного Режиссёра обнулены!', notify=True, title='Synapse Director')
    except Exception as e:
        log_exception('Error in command_synapse_reset_auto', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.check_scene', 'synapse.auto_debug', command_type=CommandType.Live if CommandType else 0)
def command_synapse_check_scene(_connection=None):
    """Диагностика Автономного Режиссёра: проверяет текущую готовность сцены на участке."""
    try:
        from ai_social_pc.autonomous_director import scan_household_for_best_scene, get_director_lot_state
        lot_st = get_director_lot_state()
        cheat_print(_connection, f'=== [ДИАГНОСТИКА РЕЖИССЁРА (Режим участка: {lot_st})] ===')
        spark = scan_household_for_best_scene(force=False)
        if spark:
            cheat_print(_connection, f'[ГОТОВО] Найдена подходящая сцена: {spark.get("trigger_type")} (Приоритет: {spark.get("priority")})')
            cheat_print(_connection, f'Повод: {spark.get("premise", "-")}')
        else:
            cheat_print(_connection, '[ОЖИДАНИЕ] Естественная сцена сейчас не готова (кулдаун или нет условий).')
            cheat_print(_connection, 'Для принудительного запуска используйте: synapse.force_auto или synapse.run <id> force')
    except Exception as e:
        log_exception('Error in command_synapse_check_scene', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.force_auto', 'synapse.auto_chat', command_type=CommandType.Live if CommandType else 0)
def command_synapse_force_auto(_connection=None):
    """Принудительно запускает лучшее автономное событие Режиссёра прямо сейчас."""
    try:
        from ai_social_pc.autonomous_director import scan_household_for_best_scene, dispatch_autonomous_scene
        spark = scan_household_for_best_scene(force=True)
        if spark:
            cheat_print(_connection, f'[РЕЖИССЁР] Принудительный запуск сцены: {spark.get("trigger_type")}')
            dispatch_autonomous_scene(spark, force=True)
        else:
            cheat_print(_connection, '[РЕЖИССЁР] Не удалось подобрать пару симов для принудительной сцены.')
    except Exception as e:
        log_exception('Error in command_synapse_force_auto', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.director_state', command_type=CommandType.Live if CommandType else 0)
def command_synapse_director_state(_connection=None):
    """Выводит текущее состояние режима Режиссёра (HOME, VISITING_FRIENDS, VISITING_RELATIVES, COMMUNITY)."""
    try:
        from ai_social_pc.autonomous_director import (
            get_director_lot_state,
            DIRECTOR_STATE_HOME,
            DIRECTOR_STATE_VISITING_FRIENDS,
            DIRECTOR_STATE_VISITING_RELATIVES,
            DIRECTOR_STATE_COMMUNITY,
            DIRECTOR_STATE_OTHER,
        )
        st = get_director_lot_state()
        labels = {
            DIRECTOR_STATE_HOME: 'ДОМ (Активная семья)',
            DIRECTOR_STATE_VISITING_FRIENDS: 'В ГОСТЯХ У ДРУЗЕЙ',
            DIRECTOR_STATE_VISITING_RELATIVES: 'В ГОСТЯХ У РОДСТВЕННИКОВ',
            DIRECTOR_STATE_COMMUNITY: 'ОБЩЕСТВЕННЫЙ УЧАСТОК',
            DIRECTOR_STATE_OTHER: 'ДРУГОЙ УЧАСТОК',
        }
        cheat_print(_connection, f'[РЕЖИССЁР] Текущий режим участка: {labels.get(st, st)} ({st})', notify=True, title='Synapse Director')
    except Exception as e:
        log_exception('Error in command_synapse_director_state', e)
        cheat_print(_connection, f'Error: {e}')


@Command('synapse.test_npc_npc', 'synapse.run_npc_npc', command_type=CommandType.Live if CommandType else 0)
def command_synapse_test_npc_npc(_connection=None):
    """
    Тестирует диалог между двумя NPC/симами без участия активного игрока.
    Работает:
    - На общественных участках (между 2 свободными NPC на лоте);
    - В гостях (между двумя хозяевами дома);
    - На домашнем участке (между двумя гостями).
    """
    try:
        from ai_social_pc.autonomous_director import (
            get_director_lot_state,
            is_sim_host_resident,
            is_sim_active_guest,
            is_sim_available,
            evaluate_scene_spark,
            dispatch_autonomous_scene,
            get_distance_between_sims,
            DIRECTOR_STATE_HOME,
            DIRECTOR_STATE_COMMUNITY,
            DIRECTOR_STATE_VISITING_FRIENDS,
            DIRECTOR_STATE_VISITING_RELATIVES,
        )

        state = get_director_lot_state()
        sim_mgr = services.sim_info_manager() if hasattr(services, 'sim_info_manager') else None
        if not sim_mgr:
            cheat_print(_connection, 'Ошибка: sim_info_manager недоступен.')
            return

        candidates = []
        for inst in sim_mgr.instanced_sims_gen():
            inf = getattr(inst, 'sim_info', None)
            if not inf or not is_sim_available(inst):
                continue
            if state in (DIRECTOR_STATE_VISITING_FRIENDS, DIRECTOR_STATE_VISITING_RELATIVES):
                if is_sim_host_resident(inf):
                    candidates.append(inst)
            elif state == DIRECTOR_STATE_COMMUNITY:
                if not is_sim_active_guest(inf) and getattr(inf, 'is_npc', True):
                    candidates.append(inst)
            elif state == DIRECTOR_STATE_HOME:
                if not is_sim_active_guest(inf) and getattr(inf, 'is_npc', True):
                    candidates.append(inst)
            else:
                if not is_sim_active_guest(inf) and getattr(inf, 'is_npc', True):
                    candidates.append(inst)

        if len(candidates) < 2:
            cheat_print(_connection, f'[ОШИБКА] На участке недостаточно свободных NPC ({len(candidates)}). Требуется минимум 2 свободных NPC для диалога.', notify=True, title='Synapse NPC-NPC')
            return

        # Перебираем пары кандидатов, сортируя их по физической близости (ближайшие пары проверяются первыми)
        all_pairs = []
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                c1 = candidates[i]
                c2 = candidates[j]
                d = get_distance_between_sims(c1, c2)
                all_pairs.append((c1, c2, d if d is not None else 999.0))

        all_pairs.sort(key=lambda item: item[2])

        selected_spark = None
        tried_pairs_info = []

        for c1, c2, dist_m in all_pairs:
            inf1 = getattr(c1, 'sim_info', None)
            inf2 = getattr(c2, 'sim_info', None)
            name1 = getattr(inf1, 'first_name', 'NPC 1')
            name2 = getattr(inf2, 'first_name', 'NPC 2')
            tried_pairs_info.append(f"{name1} и {name2} ({dist_m:.1f}м)")

            spark = evaluate_scene_spark(c1, c2, force=True)
            if spark is not None:
                selected_spark = spark
                cheat_print(_connection, f'[ТЕСТ NPC <-> NPC] Найдена подходящая пара: {name1} и {name2} (Дистанция: {dist_m:.1f}м, Режим лота: {state})...')
                break

        if selected_spark is None:
            pairs_str = ", ".join(tried_pairs_info[:4])
            cheat_print(_connection, f'[ОШИБКА] Ни для одной из проверенных пар не удалось создать повод (проверено: {pairs_str}). Убедитесь, что симы находятся рядом или в одной зоне лота.', notify=True, title='Synapse NPC-NPC')
            return

        trig = selected_spark.get('trigger_type', 'ambient')
        prio = selected_spark.get('priority', 0)
        premise = selected_spark.get('premise', '')
        cheat_print(_connection, f'[УСПЕХ] Выбран повод: [{trig}] (Приоритет: {prio})\nПовод: {premise}\nЗапуск диалога...', notify=True, title='Synapse NPC-NPC')

        dispatch_autonomous_scene(selected_spark, force=True)

    except Exception as e:
        log_exception('Error in command_synapse_test_npc_npc', e)
        cheat_print(_connection, f'Error: {e}')
