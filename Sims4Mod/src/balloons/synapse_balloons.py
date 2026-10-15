# -*- coding: utf-8 -*-
"""
Synapse AI Balloons (Phase 2)
Clean-room implementation of 3D speech and thought balloons over Sims' heads.
Features:
- SpeechBalloon (dialogue card with pointer tail)
- ThoughtBalloon (cloud body with 3 descending bubbles)
- Typewriter effect (35 characters per second)
- Smart dynamic display duration
"""
import sims4.commands
import services
from urllib.parse import quote

try:
    from distributor.system import Distributor
    from distributor.ops import SendUIMessage
    HAS_DISTRIBUTOR = True
except ImportError:
    HAS_DISTRIBUTOR = False

_SLOT_BOOTED = False
_UI_READY = False
_PENDING_BALLOONS = []

def _ensure_ui_slot():
    """Ensure the FacebookDisplay Scaleform slot is shown only once."""
    global _SLOT_BOOTED
    if not _SLOT_BOOTED and HAS_DISTRIBUTOR:
        try:
            Distributor.instance().add_op_with_no_owner(SendUIMessage("ShowFacebookDisplay"))
            _SLOT_BOOTED = True
        except Exception:
            pass

def _hook_zone_load():
    """Silently pre-boot the UI slot at the end of every zone loading screen."""
    try:
        from zone import Zone
        orig = getattr(Zone, 'on_loading_screen_animation_finished', None)
        if orig is not None and not getattr(orig, '_synapse_balloon_hooked', False):
            def _wrapped(self, *args, **kwargs):
                global _SLOT_BOOTED, _UI_READY
                _SLOT_BOOTED = False
                _UI_READY = False
                res = orig(self, *args, **kwargs)
                try:
                    _ensure_ui_slot()
                except Exception:
                    pass
                return res
            _wrapped._synapse_balloon_hooked = True
            Zone.on_loading_screen_animation_finished = _wrapped
    except Exception:
        pass

_hook_zone_load()

def _get_client_id(_connection=None):
    if _connection is not None:
        client = services.client_manager().get(_connection)
        if client is not None:
            return client.id
    client = services.client_manager().get_first_client()
    if client is not None:
        return client.id
    return 0

def calculate_smart_duration(text):
    """
    Computes a comfortable display time based on text length:
    - Typing time at 35 characters per second
    - Base hold time 2.5s + 0.045s per character
    - Clamped between 4.2s and 14.0s
    """
    chars = len(text)
    typing_time = chars / 35.0
    hold_time = 2.5 + (chars * 0.045)
    total = typing_time + hold_time
    return max(4.2, min(14.0, round(total, 1)))

def _do_client_cheat(sim_id, balloon_type, enc_name, enc_text, duration, cid):
    cmd = "ui.synapse_balloon {} {} {} {} {}".format(sim_id, balloon_type, enc_name, enc_text, duration)
    sims4.commands.client_cheat(cmd, cid)

@sims4.commands.Command('synapse.ui_ready', command_type=sims4.commands.CommandType.Live)
def synapse_ui_ready_cmd(_connection=None):
    """Callback from ActionScript when Flash UI is added to stage and ready."""
    global _UI_READY, _PENDING_BALLOONS
    _UI_READY = True
    cid = _get_client_id(_connection)
    output = sims4.commands.CheatOutput(cid)
    output("Synapse AI Balloons: Flash UI подключен и готов к работе!")
    
    # Flush any pending balloons
    if _PENDING_BALLOONS:
        for sim_id, b_type, enc_name, enc_text, duration, old_cid in _PENDING_BALLOONS:
            _do_client_cheat(sim_id, b_type, enc_name, enc_text, duration, cid or old_cid)
        _PENDING_BALLOONS.clear()
        output("Synapse AI Balloons: Отложенные сообщения успешно отображены!")
    return True

@sims4.commands.Command('synapse.balloon_boot', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_boot_cmd(_connection=None):
    """Manually boot the UI slot."""
    output = sims4.commands.CheatOutput(_connection)
    _ensure_ui_slot()
    output("Synapse AI Balloons: UI-слот запущен.")
    return True

def _show_balloon_internal(balloon_type, *args, _connection=None):
    global _UI_READY, _PENDING_BALLOONS
    output = sims4.commands.CheatOutput(_connection)
    
    _ensure_ui_slot()
    
    sim_info = services.active_sim_info()
    if sim_info is None:
        output("Synapse AI Balloons: Нет активного сима на участке!")
        return False
        
    sim_id = str(sim_info.id)
    first_name = str(getattr(sim_info, 'first_name', 'Сим'))
    
    if args:
        text = " ".join(str(a) for a in args).strip('"\'')
    else:
        if balloon_type == "thought":
            text = "Хм... о чем бы мне сейчас подумать? Кажется, этот мод на мысли симов работает идеально!"
        else:
            text = "Привет! Это AI Balloons от Synapse с эффектом печатной машинки!"
            
    # Auto-detect thought if starting with * or (
    if balloon_type == "speech":
        if text.startswith(('*', '(', '«', '[думает]')):
            balloon_type = "thought"
            
    duration = calculate_smart_duration(text)
    enc_name = quote(first_name)
    enc_text = quote(text)
    cid = _get_client_id(_connection)
    
    type_label = "Мысль" if balloon_type == "thought" else "Речь"
    
    if _UI_READY:
        _do_client_cheat(sim_id, balloon_type, enc_name, enc_text, duration, cid)
        output("Synapse AI Balloons [{}]: Показано над головой {} (длительность: {}с)!".format(type_label, first_name, duration))
    else:
        _PENDING_BALLOONS.append((sim_id, balloon_type, enc_name, enc_text, duration, cid))
        output("Synapse AI Balloons: Инициализация Flash UI... {} появится над головой {} сразу после загрузки.".format(type_label, first_name))
        
    return True

@sims4.commands.Command('synapse.balloon', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_cmd(*args, _connection=None):
    """
    Shows a balloon over active Sim (auto-detects thought or speech).
    Usage:
        synapse.balloon Привет всем!
        synapse.balloon (Интересно, что на обед?)
    """
    return _show_balloon_internal("speech", *args, _connection=_connection)

@sims4.commands.Command('synapse.speech', command_type=sims4.commands.CommandType.Live)
def synapse_speech_cmd(*args, _connection=None):
    """
    Explicitly shows a Speech Balloon with a pointer tail.
    Usage:
        synapse.speech Привет! Я разговариваю вслух!
    """
    return _show_balloon_internal("speech", *args, _connection=_connection)

@sims4.commands.Command('synapse.thought', command_type=sims4.commands.CommandType.Live)
def synapse_thought_cmd(*args, _connection=None):
    """
    Explicitly shows a Thought Balloon (cloud with descending circular bubbles).
    Usage:
        synapse.thought Хм, о чем бы мне сейчас подумать...
    """
    return _show_balloon_internal("thought", *args, _connection=_connection)

@sims4.commands.Command('synapse.balloon_clear', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_clear_cmd(_connection=None):
    """Clears all active AI Balloons on screen."""
    output = sims4.commands.CheatOutput(_connection)
    cid = _get_client_id(_connection)
    sims4.commands.client_cheat("ui.synapse_balloon_clear", cid)
    output("Synapse AI Balloons: Все баллоны очищены.")
    return True
