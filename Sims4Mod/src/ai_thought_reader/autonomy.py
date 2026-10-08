from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.config import get_autonomy_enabled, get_autonomy_interval

try:
    import services
    import alarms
    from date_and_time import create_time_span
except ImportError:
    services = None
    alarms = None
    create_time_span = None

_autonomy_alarm_handle = None
_last_tick_time = None
_next_trigger_time = None


def get_sim_now():
    """Safely retrieves current in-game sim DateAndTime object."""
    if services is None:
        return None
    try:
        ts = services.time_service() if hasattr(services, "time_service") else None
        if ts is not None and hasattr(ts, "sim_now"):
            return ts.sim_now
        gcs = services.game_clock_service() if hasattr(services, "game_clock_service") else None
        if gcs is not None and hasattr(gcs, "now"):
            return gcs.now()
    except Exception:
        pass
    return None


def format_sim_time(sim_time):
    """Formats in-game DateAndTime object into HH:MM string."""
    if sim_time is None:
        return "Неизвестно"
    try:
        h_val = getattr(sim_time, "hour", 0)
        hour = h_val() if callable(h_val) else int(h_val)
        m_val = getattr(sim_time, "minute", 0)
        minute = m_val() if callable(m_val) else int(m_val)
        return f"{hour:02d}:{minute:02d}"
    except Exception:
        return str(sim_time)


def span_to_minutes(span):
    """Safely converts a TimeSpan object to float sim minutes."""
    if span is None:
        return None
    try:
        if hasattr(span, "in_minutes"):
            val = span.in_minutes
            return float(val() if callable(val) else val)
        if hasattr(span, "in_sim_minutes"):
            val = span.in_sim_minutes
            return float(val() if callable(val) else val)
        if hasattr(span, "in_seconds"):
            val = span.in_seconds
            return float(val() if callable(val) else val) / 60.0
    except Exception:
        pass
    return None


def _on_autonomy_tick(handle=None):
    global _last_tick_time, _next_trigger_time
    try:
        now = get_sim_now()
        _last_tick_time = now
        interval_mins = get_autonomy_interval()
        if now is not None and create_time_span is not None:
            _next_trigger_time = now + create_time_span(minutes=interval_mins)

        if not get_autonomy_enabled():
            return
        if services is None:
            return
        client = services.client_manager().get_first_client()
        if client is None:
            return
        sim_info = getattr(client, "active_sim_info", None)
        if sim_info is None and client.active_sim is not None:
            sim_info = getattr(client.active_sim, "sim_info", None)
        if sim_info is None:
            return

        from ai_thought_reader.commands import execute_read_thoughts
        log(f"[AUTONOMY] Triggering autonomous thought for active Sim: {getattr(sim_info, 'first_name', '')}")
        execute_read_thoughts(sim_info.sim_id)
    except Exception as e:
        log_exception("Error during autonomy thought tick", e)


def trigger_autonomy_now():
    """Manually forces an autonomous thought right now (useful for cheat commands / testing)."""
    _on_autonomy_tick(None)


def update_autonomy_alarm():
    """Starts, updates, or stops the repeating in-game autonomy alarm."""
    global _autonomy_alarm_handle, _next_trigger_time
    if alarms is None or create_time_span is None or services is None:
        return
    try:
        if _autonomy_alarm_handle is not None:
            try:
                alarms.cancel_alarm(_autonomy_alarm_handle)
            except Exception:
                pass
            _autonomy_alarm_handle = None

        if get_autonomy_enabled():
            interval_mins = get_autonomy_interval()
            time_span = create_time_span(minutes=interval_mins)
            now = get_sim_now()
            if now is not None:
                _next_trigger_time = now + time_span

            _autonomy_alarm_handle = alarms.add_alarm(
                update_autonomy_alarm,
                time_span,
                _on_autonomy_tick,
                repeating=True,
            )
            log(f"[AUTONOMY] Repeating alarm active every {interval_mins} sim-minutes.")
        else:
            _next_trigger_time = None
            log("[AUTONOMY] Autonomy is disabled; alarm stopped.")
    except Exception as e:
        log_exception("Failed to update autonomy alarm", e)


def get_autonomy_timer_info() -> dict:
    """
    Returns diagnostic details about the autonomous thought countdown:
    - enabled: bool
    - alarm_active: bool
    - interval_mins: int
    - current_time_str: str (HH:MM)
    - next_time_str: str (HH:MM)
    - mins_left: float
    - active_sim_name: str
    - formatted_msg: str
    """
    global _autonomy_alarm_handle, _next_trigger_time
    is_en = False
    try:
        from ai_thought_reader.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        pass

    enabled = get_autonomy_enabled()
    interval_mins = get_autonomy_interval()
    now = get_sim_now()
    unknown_str = "Unknown" if is_en else "Неизвестно"
    current_time_str = format_sim_time(now) if now is not None else unknown_str

    active_sim_name = ""
    if services is not None:
        try:
            client = services.client_manager().get_first_client()
            if client is not None:
                s_info = getattr(client, "active_sim_info", None)
                if s_info is None and client.active_sim is not None:
                    s_info = getattr(client.active_sim, "sim_info", None)
                if s_info is not None:
                    active_sim_name = f"{getattr(s_info, 'first_name', '')} {getattr(s_info, 'last_name', '')}".strip()
        except Exception:
            pass

    if not enabled:
        if is_en:
            msg = (
                "=========================================\n"
                "      AUTONOMOUS THOUGHTS TIMER (AI)     \n"
                "=========================================\n"
                "Status:      DISABLED in settings\n"
                f"Interval:    every {interval_mins} sim-minutes (when enabled)\n"
                f"Game Time:   {current_time_str}\n"
                "-----------------------------------------\n"
                "Enable autonomous thoughts via menu 'synapse' / 'ai menu'\n"
                "or trigger immediately for testing: ai timer now\n"
                "========================================="
            )
        else:
            msg = (
                "=========================================\n"
                "       ТАЙМЕР АВТОНОМНЫХ МЫСЛЕЙ          \n"
                "=========================================\n"
                "Статус:      ВЫКЛЮЧЕНЫ в настройках\n"
                f"Интервал:    каждые {interval_mins} сим-минут (при включении)\n"
                f"Время игры:  {current_time_str}\n"
                "-----------------------------------------\n"
                "Включить авто-мысли можно через меню 'synapse' / 'ai menu'\n"
                "или протестировать принудительно: ai timer now\n"
                "========================================="
            )
        return {
            "enabled": False,
            "alarm_active": False,
            "interval_mins": interval_mins,
            "current_time_str": current_time_str,
            "next_time_str": "-",
            "mins_left": 0.0,
            "active_sim_name": active_sim_name,
            "formatted_msg": msg,
        }

    alarm_active = (_autonomy_alarm_handle is not None)
    mins_left = None
    next_time_obj = None

    # 1. Direct query of alarm handle
    if _autonomy_alarm_handle is not None:
        try:
            if hasattr(alarms, "time_until_alarm"):
                span = alarms.time_until_alarm(_autonomy_alarm_handle)
                m = span_to_minutes(span)
                if m is not None and m >= 0:
                    mins_left = m
            if mins_left is None:
                finishing = getattr(_autonomy_alarm_handle, "finishing_time", None) or getattr(_autonomy_alarm_handle, "_finishing_time", None)
                if finishing is not None and now is not None:
                    next_time_obj = finishing
                    span = finishing - now
                    m = span_to_minutes(span)
                    if m is not None:
                        mins_left = max(0.0, m)
        except Exception:
            pass

    # 2. Fallback to tracked _next_trigger_time
    if mins_left is None and _next_trigger_time is not None and now is not None:
        try:
            next_time_obj = _next_trigger_time
            span = _next_trigger_time - now
            m = span_to_minutes(span)
            if m is not None:
                mins_left = max(0.0, m)
        except Exception:
            pass

    # 3. If alarm handle was lost while enabled, re-arm it
    if not alarm_active or mins_left is None:
        update_autonomy_alarm()
        alarm_active = (_autonomy_alarm_handle is not None)
        if _next_trigger_time is not None and now is not None:
            try:
                next_time_obj = _next_trigger_time
                span = _next_trigger_time - now
                m = span_to_minutes(span)
                if m is not None:
                    mins_left = max(0.0, m)
            except Exception:
                pass

    if mins_left is None:
        mins_left = float(interval_mins)

    approx_str = f"~in {int(mins_left)} min" if is_en else f"~через {int(mins_left)} мин"
    if next_time_obj is not None:
        next_time_str = format_sim_time(next_time_obj)
    elif now is not None and create_time_span is not None:
        try:
            calc_next = now + create_time_span(minutes=int(mins_left))
            next_time_str = format_sim_time(calc_next)
        except Exception:
            next_time_str = approx_str
    else:
        next_time_str = approx_str

    if is_en:
        sim_target_info = f"Sim:         {active_sim_name}\n" if active_sim_name else ""
        formatted_msg = (
            "=========================================\n"
            "      AUTONOMOUS THOUGHTS TIMER (AI)     \n"
            "=========================================\n"
            f"Status:      ENABLED (every {interval_mins} sim-minutes)\n"
            f"{sim_target_info}"
            f"Game Time:   {current_time_str}\n"
            f"Next:        at {next_time_str} sim time\n"
            f"Remaining:   ~{mins_left:.1f} sim-minutes\n"
            "-----------------------------------------\n"
            "Command for immediate trigger: ai timer now\n"
            "========================================="
        )
    else:
        sim_target_info = f"Персонаж:    {active_sim_name}\n" if active_sim_name else ""
        formatted_msg = (
            "=========================================\n"
            "       ТАЙМЕР АВТОНОМНЫХ МЫСЛЕЙ (AI)     \n"
            "=========================================\n"
            f"Статус:      ВКЛЮЧЕНЫ (каждые {interval_mins} сим-минут)\n"
            f"{sim_target_info}"
            f"Время игры:  {current_time_str}\n"
            f"Следующая:   в {next_time_str} по игровому времени\n"
            f"Осталось:    ~{mins_left:.1f} сим-минут\n"
            "-----------------------------------------\n"
            "Команда для мгновенного запуска: ai timer now\n"
            "========================================="
        )

    return {
        "enabled": True,
        "alarm_active": alarm_active,
        "interval_mins": interval_mins,
        "current_time_str": current_time_str,
        "next_time_str": next_time_str,
        "mins_left": mins_left,
        "active_sim_name": active_sim_name,
        "formatted_msg": formatted_msg,
    }
