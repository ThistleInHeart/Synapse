import time
from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.config import (
    get_api_key,
    set_api_key,
    get_model,
    set_model,
    get_reasoning_effort,
    set_reasoning_effort,
    load_config,
    reload_config,
    get_active_provider_info,
    add_recent_thought,
    set_custom_sim_lore,
    get_custom_sim_lore,
    get_language,
    set_language,
)
from ai_thought_reader.client import (
    request_ai_thought_async,
    send_context_to_bridge_async,
    check_bridge_health,
)
from ai_thought_reader.context import build_sim_prompt
from ai_thought_reader.ui_helper import (
    show_notification,
    show_sim_thought_notification,
    show_error_notification,
)

_PENDING_THOUGHT_SIM_IDS = set()
_LAST_THOUGHT_REQUEST_TIME = {}


def _is_en() -> bool:
    try:
        from ai_thought_reader.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False

try:
    import services
    import sims4.commands
    from sims4.commands import Command, CommandType, output
except ImportError:
    services = None
    sims4 = None
    Command = lambda *a, **kw: lambda f: f
    CommandType = None
    output = lambda msg, c=None: None


def cheat_print(connection, text: str):
    """Outputs text to the cheat console and logs it."""
    log(f"[CONSOLE] {text}")
    try:
        output(text, connection)
    except Exception:
        pass


def execute_set_key(key: str, _connection=None):
    is_en = _is_en()
    if not key or not key.strip():
        cheat_print(_connection, "Usage: ai set_key <your_OpenRouter_key>" if is_en else "Использование: ai set_key <ваш_ключ_OpenRouter>")
        return

    clean_key = key.strip()
    if set_api_key(clean_key):
        masked = clean_key[:7] + "..." + clean_key[-4:] if len(clean_key) > 15 else "***"
        cheat_print(_connection, f"[AI Mod] OpenRouter API key saved ({masked})!" if is_en else f"[AI Mod] API-ключ OpenRouter успешно сохранен ({masked})!")
        show_notification("AI Mind Reader", "OpenRouter API key set and saved." if is_en else "API-ключ OpenRouter успешно установлен и сохранен.")
    else:
        cheat_print(_connection, "[AI Mod] Error saving configuration." if is_en else "[AI Mod] Ошибка при сохранении конфигурации.")


def execute_set_model(model: str, _connection=None):
    is_en = _is_en()
    if not model or not model.strip():
        current_model = get_model()
        cheat_print(_connection, f"Current model: {current_model}" if is_en else f"Текущая модель: {current_model}")
        cheat_print(_connection, "Usage: ai set_model <model_id>" if is_en else "Использование: ai set_model <id_модели>")
        return

    clean_model = model.strip()
    if set_model(clean_model):
        cheat_print(_connection, f"[AI Mod] Model changed to: {clean_model}" if is_en else f"[AI Mod] Модель успешно изменена на: {clean_model}")
        show_notification("AI Mind Reader", f"Selected model: {clean_model}" if is_en else f"Выбрана модель: {clean_model}")
    else:
        cheat_print(_connection, "[AI Mod] Error saving model." if is_en else "[AI Mod] Ошибка при сохранении модели.")


def execute_set_reasoning(level: str, _connection=None):
    is_en = _is_en()
    if not level or not level.strip():
        cur = get_reasoning_effort()
        cheat_print(_connection, f"Current reasoning effort: {cur}" if is_en else f"Текущий уровень рассуждений: {cur}")
        cheat_print(_connection, "Available options: auto, low, medium, high, none" if is_en else "Доступные варианты: auto, low, medium, high, none")
        cheat_print(_connection, "Usage: ai reasoning <auto|low|medium|high|none>" if is_en else "Использование: ai reasoning <auto|low|medium|high|none>")
        return

    clean_level = level.strip().lower()
    if clean_level not in ("auto", "low", "medium", "high", "none"):
        cheat_print(_connection, f"Unknown reasoning level '{level}'. Options: auto, low, medium, high, none." if is_en else f"Неизвестный уровень '{level}'. Выберите: auto, low, medium, high, none.")
        return

    if set_reasoning_effort(clean_level):
        cheat_print(_connection, f"[AI Mod] Reasoning effort changed to: {clean_level}" if is_en else f"[AI Mod] Уровень рассуждений изменен на: {clean_level}")
        show_notification("AI Mind Reader", f"Reasoning effort: {clean_level}" if is_en else f"Уровень рассуждений: {clean_level}")
    else:
        cheat_print(_connection, "[AI Mod] Error saving settings." if is_en else "[AI Mod] Ошибка при сохранении настроек.")


def execute_status(_connection=None):
    is_en = _is_en()
    reload_config()
    api_key = get_api_key()
    provider_name, model_name, conn_mode = get_active_provider_info()
    reasoning = get_reasoning_effort()

    cfg = load_config()
    if conn_mode == "colab":
        colab_url = cfg.get("colab_url", "").strip()
        key_status = (colab_url[:25] + "...") if len(colab_url) > 25 else (colab_url or ("No URL set" if is_en else "URL не указан"))
        key_header = "URL:"
    elif conn_mode in ("local", "lmstudio", "ollama"):
        key_status = cfg.get("local_url", "http://localhost:1234/v1").strip()
        key_header = "URL:"
    else:
        if api_key:
            key_status = ("Set (" if is_en else "Установлен (") + (api_key[:6] + "..." + api_key[-4:] if len(api_key) > 12 else "***") + ")"
        else:
            key_status = "NOT SET (ai set_key <key>)" if is_en else "НЕ УСТАНОВЛЕН (ai set_key <ключ>)"
        key_header = "API Key:" if is_en else "API-ключ:"

    bridge_ok, bridge_msg = check_bridge_health()
    if is_en:
        bridge_status = "RUNNING (127.0.0.1:8765)" if bridge_ok else "NOT RUNNING (Start Synapse)"
        autonomy_line = "DISABLED (ai timer)"
    else:
        bridge_status = "РАБОТАЕТ (127.0.0.1:8765)" if bridge_ok else "НЕ ЗАПУЩЕН (Запустите Synapse)"
        autonomy_line = "ВЫКЛЮЧЕНЫ (ai timer)"

    try:
        from ai_thought_reader.autonomy import get_autonomy_timer_info
        t_info = get_autonomy_timer_info()
        if t_info.get("enabled"):
            autonomy_line = (f"ENABLED (next: {t_info['next_time_str']}, ~{t_info['mins_left']:.1f} min)" if is_en else f"ВКЛЮЧЕНЫ (след: {t_info['next_time_str']}, ~{t_info['mins_left']:.1f} мин)")
        else:
            autonomy_line = (f"DISABLED (every {t_info['interval_mins']} min)" if is_en else f"ВЫКЛЮЧЕНЫ (каждые {t_info['interval_mins']} мин)")
    except Exception:
        pass

    cheat_print(_connection, "=============================")
    cheat_print(_connection, "          Synapse            ")
    cheat_print(_connection, "=============================")
    cheat_print(_connection, f"AI Bridge:   {bridge_status}")
    cheat_print(_connection, f"{'Provider:' if is_en else 'Провайдер:'}   {provider_name}")
    cheat_print(_connection, f"{'Model:' if is_en else 'Модель:'}      {model_name}")
    cheat_print(_connection, f"{key_header:<13}{key_status}")
    cheat_print(_connection, f"{'Reasoning:' if is_en else 'Рассуждения:'} {reasoning}")
    cheat_print(_connection, f"{'Autonomy:' if is_en else 'Авто-мысли:'}  {autonomy_line}")
    cheat_print(_connection, f"{'Commands:' if is_en else 'Команды:'}     synapse | ai timer | ai status | ai test | ai read | ai help")
    cheat_print(_connection, "=============================")


def execute_test(_connection=None):
    is_en = _is_en()
    api_key = get_api_key()
    model = get_model()

    bridge_ok, _ = check_bridge_health()
    if not bridge_ok:
        msg = "AI Bridge is not running! Please start Synapse." if is_en else "AI Bridge не запущен! Запустите 'Запустить AI Мод (Bridge).bat' на рабочем столе."
        cheat_print(_connection, msg)
        show_error_notification(msg)
        return

    if not api_key:
        msg = "API key not set! Enter: ai set_key <your_key>" if is_en else "API-ключ не установлен! Введите: ai set_key <ваш_ключ>"
        cheat_print(_connection, msg)
        show_error_notification(msg)
        return

    cheat_print(_connection, f"Sending test request to AI ({model})..." if is_en else f"Отправка тестового запроса к AI ({model})...")
    show_notification("AI Mind Reader", f"Testing connection to AI ({model})..." if is_en else f"Тестирование связи с AI ({model})...")

    test_prompt = (
        "This is a test check request from The Sims 4. Reply briefly: 'Connection to The Sims 4 established!'."
        if is_en else
        "Это тестовый проверочный запрос из The Sims 4. Ответь коротко: 'Связь с The Sims 4 установлена!'."
    )

    def on_test_result(text, success):
        if success:
            cheat_print(_connection, f"[Success] AI Response: {text}" if is_en else f"[Успех] Ответ AI: {text}")
            show_notification("AI Mind Reader: Success" if is_en else "AI Mind Reader: Успех", f"{'Response' if is_en else 'Ответ'}: {text}")
        else:
            cheat_print(_connection, f"[Error] {text}" if is_en else f"[Ошибка] {text}")
            show_error_notification(f"{'Verification error' if is_en else 'Ошибка проверки'}: {text}")

    request_ai_thought_async(test_prompt, "Test" if is_en else "Тест", on_test_result)


def _resolve_target_sim_info(target_arg, services):
    if services is None:
        return None
    sim_info_mgr = services.sim_info_manager()
    if sim_info_mgr is None:
        return None

    target_sim_info = None
    if target_arg is not None:
        if hasattr(target_arg, "sim_info"):
            si = getattr(target_arg, "sim_info", None)
            target_sim_info = si() if callable(si) else si
        elif hasattr(target_arg, "get_sim_info"):
            try:
                target_sim_info = target_arg.get_sim_info()
            except Exception:
                pass
        elif hasattr(target_arg, "first_name") and hasattr(target_arg, "sim_id"):
            target_sim_info = target_arg

        if target_sim_info is None:
            raw_str = str(target_arg).strip()
            # 1. Check if argument is a numeric Sim ID (passed by S4S pie menu)
            if raw_str.isdigit() or (raw_str.startswith("-") and raw_str[1:].isdigit()):
                try:
                    sim_id_num = int(raw_str)
                    target_sim_info = sim_info_mgr.get(sim_id_num)
                except Exception:
                    pass

        # 2. Check if argument is a Name query
        if target_sim_info is None and target_arg is not None:
            raw_str = str(target_arg).strip()
            if raw_str:
                query = raw_str.lower()
                for s_info in sim_info_mgr.values():
                    first = getattr(s_info, "first_name", "").lower()
                    last = getattr(s_info, "last_name", "").lower()
                    full = f"{first} {last}".strip()
                    if query in first or query in last or query in full or full in query:
                        target_sim_info = s_info
                        break

    # 3. Fallback to Active Sim
    if target_sim_info is None:
        target_sim_info = services.active_sim_info()

    return target_sim_info


def execute_read_thoughts(target_arg=None, _connection=None):
    """
    Reads thoughts of target Sim.
    target_arg can be:
    - Target Sim ID (int or str of digits from S4S pie menu do_command target_sim_id)
    - Sim Name (str query)
    - None (Active Sim)
    """
    is_en = _is_en()
    if services is None:
        cheat_print(_connection, "Error: game services unavailable." if is_en else "Ошибка: сервисы игры недоступны.")
        return

    bridge_ok, _ = check_bridge_health()
    if not bridge_ok:
        msg = "AI Bridge is not running! Please start Synapse." if is_en else "AI Bridge не запущен! Запустите Synapse или 'Запустить AI Мод (Bridge).bat'."
        cheat_print(_connection, msg)
        show_error_notification(msg)
        return

    target_sim_info = _resolve_target_sim_info(target_arg, services)
    if target_sim_info is None:
        cheat_print(_connection, "Error: Sim not found." if is_en else "Ошибка: персонаж не найден.")
        return

    full_name = f"{target_sim_info.first_name} {target_sim_info.last_name}".strip()
    sim_id = getattr(target_sim_info, "sim_id", None)
    now = time.time()
    if sim_id:
        last_time = _LAST_THOUGHT_REQUEST_TIME.get(sim_id, 0.0)
        if sim_id in _PENDING_THOUGHT_SIM_IDS:
            if (now - last_time) < 20.0:
                log(f"[COMMAND] Thought request already pending for sim_id {sim_id}, skipping duplicate.")
                w_title = "Please wait..." if is_en else "Подождите..."
                w_msg = f"{full_name}'s thoughts are currently being processed. Please wait for the reply!" if is_en else f"Мысли {full_name} уже обрабатываются нейросетью. Пожалуйста, подождите ответ!"
                show_notification(w_title, w_msg, sim_info=target_sim_info, is_error=False)
                return
            else:
                log(f"[COMMAND] Pending thought request for sim_id {sim_id} timed out (>20s), clearing.")
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)

        if (now - last_time) < 2.0:
            log(f"[COMMAND] Debounced duplicate thought request for sim_id {sim_id} within 2.0s, skipping.")
            return
        _PENDING_THOUGHT_SIM_IDS.add(sim_id)
        _LAST_THOUGHT_REQUEST_TIME[sim_id] = now

    is_pet = getattr(target_sim_info, "is_pet", False)
    if is_en:
        notify_text = f"Connecting to {full_name}'s thoughts..." if is_pet else f"Connecting to {full_name}'s inner voice..."
        cheat_msg = f"Reading thoughts: {full_name} (ID: {target_sim_info.sim_id})..."
        notif_title = "Reading Thoughts..."
    else:
        notify_text = f"Связываемся с мыслями питомца {full_name}..." if is_pet else f"Связываемся с внутренним голосом {full_name}..."
        cheat_msg = f"Считывание мыслей: {full_name} (ID: {target_sim_info.sim_id})..."
        notif_title = "Считывание мыслей..."
    cheat_print(_connection, cheat_msg)
    show_notification(notif_title, notify_text, sim_info=target_sim_info)

    try:
        prompt = build_sim_prompt(target_sim_info)
    except Exception as ex_prompt:
        log_exception("Error in build_sim_prompt for execute_read_thoughts", ex_prompt)
        if sim_id:
            _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
        err_msg = f"Error building thought prompt: {ex_prompt}" if is_en else f"Ошибка составления контекста мыслей: {ex_prompt}"
        show_error_notification(err_msg)
        return

    def on_thought_ready(thought, success):
        try:
            if sim_id:
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
            if success:
                cheat_print(_connection, f"[{full_name} thinks]: {thought}" if is_en else f"[{full_name} думает]: {thought}")
                try:
                    add_recent_thought(full_name, thought)
                except Exception:
                    pass
                show_sim_thought_notification(target_sim_info, thought)
            else:
                cheat_print(_connection, f"[Error] {thought}" if is_en else f"[Ошибка] {thought}")
                show_error_notification(thought)
        except Exception as e:
            log_exception("Exception in on_thought_ready", e)
        finally:
            if sim_id:
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)

    try:
        request_ai_thought_async(prompt, full_name, on_thought_ready)
    except Exception as ex_req:
        log_exception("Error calling request_ai_thought_async in execute_read_thoughts", ex_req)
        if sim_id:
            _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
        show_error_notification(str(ex_req))


def execute_read_thoughts_ww(target_arg=None, _connection=None):
    """
    Reads thoughts of target Sim during WickedWhims intimacy / sex.
    Target can be:
    - Target Sim ID (from S4S WW pie menu)
    - Sim Name
    - None (Active Sim)
    """
    is_en = _is_en()
    if services is None:
        cheat_print(_connection, "Error: game services unavailable." if is_en else "Ошибка: сервисы игры недоступны.")
        return False

    bridge_ok, _ = check_bridge_health()
    if not bridge_ok:
        msg = "AI Bridge is not running! Please start Synapse." if is_en else "AI Bridge не запущен! Запустите Synapse или 'Запустить AI Мод (Bridge).bat'."
        cheat_print(_connection, msg)
        show_error_notification(msg)
        return False

    target_sim_info = _resolve_target_sim_info(target_arg, services)
    if target_sim_info is None:
        cheat_print(_connection, "Error: Sim not found." if is_en else "Ошибка: персонаж не найден.")
        return False

    full_name = f"{target_sim_info.first_name} {target_sim_info.last_name}".strip()
    sim_id = getattr(target_sim_info, "sim_id", None)
    now = time.time()
    if sim_id:
        last_time = _LAST_THOUGHT_REQUEST_TIME.get(sim_id, 0.0)
        if sim_id in _PENDING_THOUGHT_SIM_IDS:
            if (now - last_time) < 20.0:
                log(f"[COMMAND] WW thought request already pending for sim_id {sim_id}, skipping duplicate.")
                w_title = "Please wait..." if is_en else "Подождите..."
                w_msg = f"{full_name}'s intimate thoughts are currently being processed. Please wait for the reply!" if is_en else f"Интимные мысли {full_name} уже обрабатываются нейросетью. Пожалуйста, подождите ответ!"
                show_notification(w_title, w_msg, sim_info=target_sim_info, is_error=False)
                return False
            else:
                log(f"[COMMAND] Pending WW thought request for sim_id {sim_id} timed out (>20s), clearing.")
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)

        if (now - last_time) < 2.0:
            log(f"[COMMAND] Debounced duplicate WW thought request for sim_id {sim_id} within 2.0s, skipping.")
            return False
        _PENDING_THOUGHT_SIM_IDS.add(sim_id)
        _LAST_THOUGHT_REQUEST_TIME[sim_id] = now

    log(f"[WW INTERACTION] 'Прочитать мысли ww' triggered on: {full_name} (ID: {target_sim_info.sim_id})")
    if is_en:
        cheat_msg = f"Reading intimate thoughts (WW): {full_name} (ID: {target_sim_info.sim_id})..."
        notif_title = "Reading Intimate Thoughts..."
        notify_text = f"Connecting to {full_name}'s intimate thoughts..."
    else:
        cheat_msg = f"Считывание мыслей (WW): {full_name} (ID: {target_sim_info.sim_id})..."
        notif_title = "Считывание интимных мыслей..."
        notify_text = f"Связываемся с интимными мыслями {full_name}..."

    cheat_print(_connection, cheat_msg)
    show_notification(notif_title, notify_text, sim_info=target_sim_info)

    try:
        prompt = build_sim_prompt(target_sim_info)
    except Exception as ex_prompt:
        log_exception("Error in build_sim_prompt for execute_read_thoughts_ww", ex_prompt)
        if sim_id:
            _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
        err_msg = f"Error building intimate thought prompt: {ex_prompt}" if is_en else f"Ошибка составления контекста интимных мыслей: {ex_prompt}"
        show_error_notification(err_msg)
        return False

    def on_thought_ready(thought, success):
        try:
            if sim_id:
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
            if success:
                log(f"[WW INTERACTION SUCCESS] {full_name} thinks: '{thought}'")
                cheat_print(_connection, f"[{full_name} thinks]: {thought}" if is_en else f"[{full_name} думает]: {thought}")
                try:
                    add_recent_thought(full_name, thought)
                except Exception:
                    pass
                show_sim_thought_notification(target_sim_info, thought)
            else:
                log(f"[WW INTERACTION ERROR] {thought}", level="ERROR")
                cheat_print(_connection, f"[Error] {thought}" if is_en else f"[Ошибка] {thought}")
                show_error_notification(thought)
        except Exception as e:
            log_exception("Exception in WW on_thought_ready", e)
        finally:
            if sim_id:
                _PENDING_THOUGHT_SIM_IDS.discard(sim_id)

    try:
        request_ai_thought_async(prompt, full_name, on_thought_ready)
        return True
    except Exception as ex_req:
        log_exception("Error calling request_ai_thought_async in execute_read_thoughts_ww", ex_req)
        if sim_id:
            _PENDING_THOUGHT_SIM_IDS.discard(sim_id)
        show_error_notification(str(ex_req))
        return False


def execute_dump_context(target_arg=None, _connection=None, is_ww: bool = False):
    """
    Collects full context for target Sim and sends it directly to Synapse console,
    WITHOUT invoking the neural network (zero tokens, no LLM cost).
    """
    is_en = _is_en()
    if services is None:
        cheat_print(_connection, "Error: game services unavailable." if is_en else "Ошибка: сервисы игры недоступны.")
        return

    bridge_ok, _ = check_bridge_health()
    if not bridge_ok:
        msg = "AI Bridge is not running! Please start Synapse." if is_en else "AI Bridge не запущен! Запустите Synapse или 'Запустить AI Мод (Bridge).bat'."
        cheat_print(_connection, msg)
        show_error_notification(msg)
        return

    target_sim_info = _resolve_target_sim_info(target_arg, services)
    if target_sim_info is None:
        cheat_print(_connection, "Error: Sim not found." if is_en else "Ошибка: персонаж не найден.")
        return

    full_name = f"{target_sim_info.first_name} {target_sim_info.last_name}".strip()

    try:
        prompt = build_sim_prompt(target_sim_info)
    except Exception as ex_prompt:
        log_exception("Error in build_sim_prompt for execute_dump_context", ex_prompt)
        err_msg = f"Error building context: {ex_prompt}" if is_en else f"Ошибка составления контекста: {ex_prompt}"
        show_error_notification(err_msg)
        return

    # Log to thought_reader.log as well
    log(f"[CONTEXT DUMP for {full_name} ({len(prompt)} chars)]:\n{prompt}")

    def on_context_sent(msg, success):
        if success:
            cheat_msg = (
                f"[Synapse Context]: Context for {full_name} ({len(prompt)} chars) sent to Synapse window (no AI called)!"
                if is_en
                else f"[Synapse Контекст]: Контекст {full_name} ({len(prompt)} симв.) отправлен в окно Synapse (без запроса к ИИ)!"
            )
            cheat_print(_connection, cheat_msg)
        else:
            cheat_print(_connection, f"[Error] {msg}")

    send_context_to_bridge_async(prompt, full_name, on_context_sent)


def execute_menu(target_sim_id=None, _connection=None):
    """Opens the in-game UI Settings Menu for target_sim_id or active sim."""
    try:
        from ai_thought_reader.ui_dialogs import open_settings_menu
        target_sim_info = None
        if target_sim_id is not None:
            raw_str = str(target_sim_id).strip()
            if raw_str.isdigit() or (raw_str.startswith("-") and raw_str[1:].isdigit()):
                sim_info_mgr = services.sim_info_manager() if services else None
                if sim_info_mgr is not None:
                    target_sim_info = sim_info_mgr.get(int(raw_str))
        open_settings_menu(target_sim_info)
        cheat_print(_connection, "[AI Mod] Settings menu opened." if _is_en() else "[AI Mod] Открыто меню настроек.")
    except Exception as e:
        log_exception("Error opening settings menu", e)
        cheat_print(_connection, f"[AI Mod] Error opening menu: {e}" if _is_en() else f"[AI Mod] Ошибка открытия меню: {e}")


def execute_lore(text_arg: str = None, _connection=None):
    """Sets or displays custom lore for the active Sim via console."""
    is_en = _is_en()
    if services is None:
        cheat_print(_connection, "Error: game services unavailable." if is_en else "Ошибка: сервисы игры недоступны.")
        return
    sim_info = services.active_sim_info()
    if not sim_info:
        cheat_print(_connection, "Error: active sim not found." if is_en else "Ошибка: активный персонаж не найден.")
        return

    sim_id = getattr(sim_info, "sim_id", None)
    full_name = f"{sim_info.first_name} {sim_info.last_name}".strip()

    if not text_arg or not text_arg.strip():
        current = get_custom_sim_lore(sim_id)
        if current:
            cheat_print(_connection, f"Current lore for {full_name}: \"{current}\"" if is_en else f"Текущий лор {full_name}: «{current}»")
        else:
            cheat_print(_connection, f"{full_name} has no custom lore. Enter: ai lore <text>" if is_en else f"У {full_name} нет дополнительного лора. Введите: ai lore <текст>")
        return

    clean_text = text_arg.strip()
    if set_custom_sim_lore(sim_id, clean_text):
        cheat_print(_connection, f"[AI Mod] Lore for {full_name} successfully saved!" if is_en else f"[AI Mod] Лор для {full_name} успешно сохранен!")
        show_notification(
            "AI Mind Reader",
            f"Lore for {full_name} saved:\n\"{clean_text}\"" if is_en else f"Лор для {full_name} сохранен:\n«{clean_text}»",
            sim_info=sim_info
        )
    else:
        cheat_print(_connection, "[AI Mod] Error saving lore." if is_en else "[AI Mod] Ошибка при сохранении лора.")


def execute_timer(arg: str = None, _connection=None):
    """
    Checks when the next autonomous thought will trigger,
    or triggers it immediately for testing if arg in ('now', 'trigger', 'run', 'test').
    """
    from ai_thought_reader.autonomy import get_autonomy_timer_info, trigger_autonomy_now
    is_en = _is_en()
    if arg and str(arg).strip().lower() in ("now", "trigger", "run", "test", "force"):
        cheat_print(_connection, "[AI Mod] Forcing autonomous thought..." if is_en else "[AI Mod] Принудительный запуск автономной мысли...")
        show_notification(
            "AI Mod: Test" if is_en else "AI Mod: Тест",
            "Forcing autonomous thought for active sim..." if is_en else "Принудительный вызов автоматической мысли активного сима..."
        )
        trigger_autonomy_now()
        return

    info = get_autonomy_timer_info()
    cheat_print(_connection, info["formatted_msg"])

    if info["enabled"]:
        if is_en:
            sub_text = (
                f"Current game time: {info['current_time_str']}\n"
                f"Next thought: at {info['next_time_str']}\n"
                f"Remaining: ~{info['mins_left']:.1f} sim-minutes."
            )
            if info.get("active_sim_name"):
                sub_text += f"\nSim: {info['active_sim_name']}"
            show_notification("Autonomous Thoughts Timer (Test)", sub_text)
        else:
            sub_text = (
                f"Текущее игровое время: {info['current_time_str']}\n"
                f"Следующая мысль: в {info['next_time_str']}\n"
                f"Осталось: ~{info['mins_left']:.1f} сим-минут."
            )
            if info.get("active_sim_name"):
                sub_text += f"\nПерсонаж: {info['active_sim_name']}"
            show_notification("Таймер авто-мыслей (Тест)", sub_text)
    else:
        if is_en:
            show_notification(
                "Autonomous Thoughts Timer",
                f"Autonomous thoughts are DISABLED in settings.\nInterval: every {info['interval_mins']} sim-min.\nEnable in menu: synapse"
            )
        else:
            show_notification(
                "Таймер авто-мыслей",
                f"Автономные мысли ВЫКЛЮЧЕНЫ в настройках.\nИнтервал: каждые {info['interval_mins']} сим-мин.\nВключите в меню: synapse"
            )


def execute_help(_connection=None):
    is_en = _is_en()
    if is_en:
        cheat_print(_connection, "=== Synapse Mod Commands ===")
        cheat_print(_connection, "synapse / ai menu / ai settings  - Open Synapse graphical settings menu")
        cheat_print(_connection, "synapse.lang / ai.lang - Check current interface and AI context language")
        cheat_print(_connection, "synapse.lang <ru|en>   - Switch mod language (English / Russian)")
        cheat_print(_connection, "ai timer               - Check when next autonomous thought triggers")
        cheat_print(_connection, "ai timer now           - Force autonomous thought right now (for testing)")
        cheat_print(_connection, "ai lore <text>         - Set backstory/lore for active Sim")
        cheat_print(_connection, "ai status              - Show mod and bridge status")
        cheat_print(_connection, "ai test                - Test connection to AI")
        cheat_print(_connection, "ai read                - Read thoughts of active Sim right now")
        cheat_print(_connection, "ai read <Name/ID>      - Read thoughts of Sim by Name or SimID")
        cheat_print(_connection, "ai context [Name/ID]   - Send Sim context to Synapse console (without calling AI)")
        cheat_print(_connection, "ai reasoning <level>   - Set reasoning effort (auto, low, medium, high, none)")
        cheat_print(_connection, "ai set_key <KEY>       - Save OpenRouter API key")
        cheat_print(_connection, "ai set_model <MODEL>   - Change AI model")
    else:
        cheat_print(_connection, "=== Команды мода Synapse ===")
        cheat_print(_connection, "synapse / ai menu / ai settings  - Открыть графическое меню настроек Synapse")
        cheat_print(_connection, "synapse.lang / ai.lang - Проверить текущий язык интерфейса и контекста ИИ")
        cheat_print(_connection, "synapse.lang <ru|en>   - Быстро переключить язык мода (English / Русский)")
        cheat_print(_connection, "ai timer               - Узнать, когда будет следующая авто-мысль")
        cheat_print(_connection, "ai timer now           - Принудительно вызвать авто-мысль прямо сейчас (для теста)")
        cheat_print(_connection, "ai lore <текст>        - Задать биографию/лор активного сима")
        cheat_print(_connection, "ai status              - Показать статус мода и моста")
        cheat_print(_connection, "ai test                - Проверить связь с AI")
        cheat_print(_connection, "ai read                - Прочитать мысли активного сима прямо сейчас")
        cheat_print(_connection, "ai read <Имя/ID>       - Прочитать мысли сима по имени или SimID")
        cheat_print(_connection, "ai context [Имя/ID]    - Отправить контекст в окно Synapse без вызова нейросети")
        cheat_print(_connection, "ai reasoning <уровень> - Установить уровень рассуждений (auto, low, medium, high, none)")
        cheat_print(_connection, "ai set_key <КЛЮЧ>      - Сохранить API-ключ OpenRouter")
        cheat_print(_connection, "ai set_model <МОДЕЛЬ>  - Сменить AI модель")


def execute_language(lang_arg: str = None, _connection=None, _output_fn=None):
    """
    Checks or sets active Synapse language.
    Usage:
      synapse.lang / ai.lang -> outputs full language status & diagnostics
      synapse.lang ru / synapse.lang en -> switches language
      synapse.lang reset -> resets to auto-detection (RU for RU game, EN for others)
    """
    from ai_thought_reader.config import get_language, set_language, load_config
    from ai_thought_reader.localization import set_current_language

    def _out(msg: str):
        cheat_print(_connection, msg)
        if _output_fn and callable(_output_fn):
            try:
                _output_fn(msg, _connection)
            except Exception:
                pass

    if lang_arg and str(lang_arg).strip():
        target = str(lang_arg).strip().lower()
        if target in ("ru", "rus", "russian", "русский", "1"):
            code = "ru"
            name = "Русский (ru)"
        elif target in ("en", "eng", "english", "английский", "2"):
            code = "en"
            name = "English (en)"
        elif target in ("reset", "auto", "default", "0"):
            from ai_thought_reader.config import get_system_default_language
            code = get_system_default_language()
            name = f"Auto-detected [{code.upper()}]"
        else:
            code = target
            name = f"Custom [{target}]"

        set_language(code)
        set_current_language(code)
        _out(f"[Synapse] Switched mod & context language to: {name}")
        show_notification("Synapse Language", f"Language updated to: {name}\nInterface and Sim context are now in {name}.")
        return

    active_code = get_language()
    cfg = load_config()
    cfg_lang = cfg.get("language", "None (auto-detected)")

    detected_locale = "unknown"
    if services:
        try:
            detected_locale = str(services.get_current_locale())
        except Exception:
            detected_locale = "error"

    is_ru = (active_code == "ru")
    lang_name = "Русский (Russian)" if is_ru else "English"
    ctx_name = "Русскоязычный контекст персонажей" if is_ru else "Native English Sim Context"
    def_mode = "Russian (RU game locale detected)" if "ru" in detected_locale.lower() else "English (Standard universal default)"

    sep = "=" * 54
    _out(sep)
    _out("  SYNAPSE LANGUAGE DIAGNOSTICS / СТАТУС ЯЗЫКА")
    _out(sep)
    _out(f"  • Active Language:    [{active_code.upper()}] - {lang_name}")
    _out(f"  • Context Engine:     {ctx_name}")
    _out(f"  • Game Locale:        {detected_locale}")
    _out(f"  • Config Override:    {cfg_lang}")
    _out(f"  • Rule Mode:          {def_mode}")
    _out(sep)
    _out("  Available commands:")
    _out("    synapse.lang en   (or ai.lang en, synapse.lang 2) -> Switch to English")
    _out("    synapse.lang ru   (or ai.lang ru, synapse.lang 1) -> Switch to Russian")
    _out("    synapse.lang auto (or synapse.lang reset)         -> Reset to default")
    _out(sep)

    notif_msg = (
        f"Active: [{active_code.upper()}] {lang_name}\n"
        f"Game Locale: {detected_locale}\n"
        f"Context: {ctx_name}\n"
        f"Config: {cfg_lang}\n\n"
        f"Switch: 'synapse.lang en' or 'synapse.lang ru'"
    )
    show_notification("Synapse Language Status", notif_msg)


if sims4 is not None and hasattr(sims4, "commands"):

    # S4S direct pie menu command: ai_read <target_sim_id>
    @Command("ai_read", command_type=CommandType.Live)
    def _cmd_ai_read_s4s(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else kwargs.get("target_sim_id", None)
        execute_read_thoughts(target_arg, _connection)

    # S4S direct pie menu command for WW intimate thoughts: ai_read_ww <target_sim_id>
    @Command("ai_read_ww", "ai.read_ww", "ai.readww", command_type=CommandType.Live)
    def _cmd_ai_read_ww_s4s(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else kwargs.get("target_sim_id", None)
        execute_read_thoughts_ww(target_arg, _connection)

    # S4S direct pie menu command for settings/lore menu: ai_menu <target_sim_id>
    @Command("ai_menu", command_type=CommandType.Live)
    def _cmd_ai_menu_s4s(*args, _connection=None, **kwargs):
        target_arg = args[0] if args else kwargs.get("target_sim_id", None)
        execute_menu(target_arg, _connection=_connection)

    # S4S direct pie menu command for computer messenger: ai_pc_chat
    @Command("ai_pc_chat", "ai.pc_chat", "chat_pc", command_type=CommandType.Live)
    def _cmd_ai_pc_chat(*args, _connection=None, **kwargs):
        try:
            from ai_social_pc.computer_interaction import start_pc_chat_session
            start_pc_chat_session(None)
        except Exception as e:
            log_exception("Error in ai_pc_chat command", e)

    # In-game settings menu commands
    @Command("ai.menu", command_type=CommandType.Live)
    def _cmd_dot_menu(*args, _connection=None, **kwargs):
        target_arg = args[0] if args else kwargs.get("target_sim_id", None)
        execute_menu(target_arg, _connection=_connection)

    @Command("ai.settings", command_type=CommandType.Live)
    def _cmd_dot_settings(*args, _connection=None, **kwargs):
        execute_menu(target_sim_id=None, _connection=_connection)

    @Command("synapse.menu", command_type=CommandType.Live)
    def _cmd_synapse_dot_menu(*args, _connection=None, **kwargs):
        execute_menu(target_sim_id=None, _connection=_connection)

    @Command("synapse.settings", command_type=CommandType.Live)
    def _cmd_synapse_dot_settings(*args, _connection=None, **kwargs):
        execute_menu(target_sim_id=None, _connection=_connection)

    @Command("ai.lore", command_type=CommandType.Live)
    def _cmd_dot_lore(*args, _connection=None, **kwargs):
        lore_text = " ".join(str(a) for a in args).strip() if args else ""
        execute_lore(lore_text, _connection)

    @Command("ai.set_key", command_type=CommandType.Live)
    def _cmd_dot_set_key(*args, _connection=None, **kwargs):
        key = args[0] if args else ""
        execute_set_key(key, _connection)

    @Command("ai.set_model", command_type=CommandType.Live)
    def _cmd_dot_set_model(*args, _connection=None, **kwargs):
        model = args[0] if args else ""
        execute_set_model(model, _connection)

    @Command("ai.reasoning", command_type=CommandType.Live)
    def _cmd_dot_reasoning(*args, _connection=None, **kwargs):
        level = args[0] if args else ""
        execute_set_reasoning(level, _connection)

    @Command("ai.set_reasoning", command_type=CommandType.Live)
    def _cmd_dot_set_reasoning(*args, _connection=None, **kwargs):
        level = args[0] if args else ""
        execute_set_reasoning(level, _connection)

    @Command("ai.status", command_type=CommandType.Live)
    def _cmd_dot_status(_connection=None):
        execute_status(_connection)

    @Command("ai.test", command_type=CommandType.Live)
    def _cmd_dot_test(_connection=None):
        execute_test(_connection)

    @Command("ai.read", command_type=CommandType.Live)
    def _cmd_dot_read(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else None
        execute_read_thoughts(target_arg, _connection)

    @Command("ai.read_thoughts", command_type=CommandType.Live)
    def _cmd_dot_read_thoughts(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else None
        execute_read_thoughts(target_arg, _connection)

    # Inspection commands to send context directly to Synapse without invoking AI
    @Command("ai.context", "ai_context", "ai.dump_context", "ai.read_context", "ai.test_context", "synapse.context", command_type=CommandType.Live)
    def _cmd_dot_context(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else kwargs.get("target_sim_id", None)
        execute_dump_context(target_arg, _connection=_connection, is_ww=False)

    @Command("ai.context_ww", "ai_context_ww", "synapse.context_ww", command_type=CommandType.Live)
    def _cmd_dot_context_ww(*args, _connection=None, **kwargs):
        target_arg = " ".join(str(a) for a in args).strip() if args else kwargs.get("target_sim_id", None)
        execute_dump_context(target_arg, _connection=_connection, is_ww=True)

    @Command("ai.timer", "ai.autonomy", "ai_timer", "synapse.timer", command_type=CommandType.Live)
    def _cmd_dot_timer(*args, _connection=None, **kwargs):
        arg1 = args[0] if args else None
        execute_timer(arg1, _connection)

    @Command("ai.lang", "ai.language", "synapse.lang", "synapse.language", "ai_lang", "synapse_lang", command_type=CommandType.Live)
    def _cmd_dot_language(*args, _connection=None, **kwargs):
        lang_arg = args[0] if args else None
        execute_language(lang_arg, _connection)

    @Command("ai.help", command_type=CommandType.Live)
    def _cmd_dot_help(_connection=None):
        execute_help(_connection)

    # Universal space-separated router command: "ai menu", "ai timer", "ai status", "ai test", "ai read", "ai reasoning"
    @Command("ai", command_type=CommandType.Live)
    def _cmd_space_router(subcmd: str = "menu", *args, _connection=None, **kwargs):
        sub = str(subcmd).strip().lower() if subcmd else "menu"
        arg1 = " ".join(str(a) for a in args).strip() if args else None
        if sub in ("menu", "settings", "options", "config", "gui"):
            execute_menu(target_sim_id=None, _connection=_connection)
        elif sub in ("lang", "language", "locale"):
            execute_language(arg1, _connection)
        elif sub in ("timer", "next", "next_thought", "autonomy", "alarm", "time"):
            execute_timer(arg1, _connection)
        elif sub in ("lore", "bio", "backstory"):
            execute_lore(arg1, _connection)
        elif sub in ("status", "info", "stat"):
            execute_status(_connection)
        elif sub in ("test", "ping"):
            execute_test(_connection)
        elif sub in ("set_key", "key", "setkey"):
            execute_set_key(arg1, _connection)
        elif sub in ("set_model", "model", "setmodel"):
            execute_set_model(arg1, _connection)
        elif sub in ("reasoning", "reason", "effort", "set_reasoning"):
            execute_set_reasoning(arg1, _connection)
        elif sub in ("read", "read_thoughts", "thoughts"):
            execute_read_thoughts(arg1, _connection)
        elif sub in ("read_ww", "readww", "ww"):
            execute_read_thoughts_ww(arg1, _connection)
        elif sub in ("context", "dump_context", "read_context", "prompt", "debug_context"):
            execute_dump_context(arg1, _connection=_connection, is_ww=False)
        elif sub in ("context_ww", "dump_ww", "ww_context"):
            execute_dump_context(arg1, _connection=_connection, is_ww=True)
        elif sub in ("help", "?"):
            execute_help(_connection)
        else:
            is_en = _is_en()
            cheat_print(_connection, f"Unknown subcommand: '{subcmd}'. Type 'ai help' or 'synapse'." if is_en else f"Неизвестная подкоманда: '{subcmd}'. Введите 'ai help' или 'synapse'.")

    # Synapse root command: "synapse", "synapse menu", etc.
    @Command("synapse", command_type=CommandType.Live)
    def _cmd_synapse_router(subcmd: str = "menu", *args, _connection=None, **kwargs):
        _cmd_space_router(subcmd, *args, _connection=_connection, **kwargs)
