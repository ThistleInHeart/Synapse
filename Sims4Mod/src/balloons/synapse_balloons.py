# -*- coding: utf-8 -*-
"""
Synapse AI Balloons Prototype
Clean-room implementation of 3D speech/thought balloons over Sims' heads.
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
    """Ensure the FacebookDisplay Scaleform slot is shown so our GFx movie is loaded."""
    global _SLOT_BOOTED
    if HAS_DISTRIBUTOR:
        try:
            Distributor.instance().add_op_with_no_owner(SendUIMessage("ShowFacebookDisplay"))
            _SLOT_BOOTED = True
        except Exception:
            pass

def _hook_zone_load():
    try:
        from zone import Zone
        orig = getattr(Zone, 'on_loading_screen_animation_finished', None)
        if orig is not None and not getattr(orig, '_synapse_balloon_hooked', False):
            def _wrapped(self, *args, **kwargs):
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

def _do_client_cheat(sim_id, enc_name, enc_text, duration, cid):
    cmd = "ui.synapse_balloon {} {} {} {}".format(sim_id, enc_name, enc_text, duration)
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
        for sim_id, enc_name, enc_text, duration, old_cid in _PENDING_BALLOONS:
            _do_client_cheat(sim_id, enc_name, enc_text, duration, cid or old_cid)
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

@sims4.commands.Command('synapse.balloon', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_cmd(*args, _connection=None):
    """
    Shows an AI Balloon over the active Sim's head.
    Usage in console (Ctrl+Shift+C):
        synapse.balloon
        synapse.balloon Привет! Это AI Balloons!
    """
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
        text = "Привет! Это AI Balloons от Synapse! Работает в 3D без всяких DLL."
        
    enc_name = quote(first_name)
    enc_text = quote(text)
    duration = 6.5
    cid = _get_client_id(_connection)
    
    if _UI_READY:
        # UI is ready, send cheat immediately
        _do_client_cheat(sim_id, enc_name, enc_text, duration, cid)
        output("Synapse AI Balloons: Показано над головой {} (ID: {})!".format(first_name, sim_id))
    else:
        # Queue command until Flash UI fires synapse.ui_ready
        _PENDING_BALLOONS.append((sim_id, enc_name, enc_text, duration, cid))
        output("Synapse AI Balloons: Инициализация Flash UI... Баллон появится над головой {} сразу после загрузки.".format(first_name))
        
    return True

@sims4.commands.Command('synapse.balloon_clear', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_clear_cmd(_connection=None):
    """
    Clears all active AI Balloons on screen.
    """
    output = sims4.commands.CheatOutput(_connection)
    cid = _get_client_id(_connection)
    sims4.commands.client_cheat("ui.synapse_balloon_clear", cid)
    output("Synapse AI Balloons: Все баллоны очищены.")
    return True
