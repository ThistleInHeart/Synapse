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

def _ensure_ui_slot():
    """Ensure the FacebookDisplay Scaleform slot is shown so our GFx movie is loaded."""
    if HAS_DISTRIBUTOR:
        try:
            Distributor.instance().add_op_with_no_owner(SendUIMessage("ShowFacebookDisplay"))
        except Exception:
            pass

def _get_client_id(_connection):
    client = services.client_manager().get(_connection)
    if client is not None:
        return client.id
    client = services.client_manager().get_first_client()
    if client is not None:
        return client.id
    return 0

@sims4.commands.Command('synapse.balloon', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_cmd(*args, _connection=None):
    """
    Shows an AI Balloon over the active Sim's head.
    Usage in console (Ctrl+Shift+C):
        synapse.balloon
        synapse.balloon Привет! Это AI Balloons!
        synapse.balloon "Любой текст на русском или английском"
    """
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
    cmd = "synapse_balloon {} {} {} {}".format(sim_id, enc_name, enc_text, duration)
    sims4.commands.client_cheat(cmd, cid)
    
    output("Synapse AI Balloons: Показано над головой {} (ID: {})!".format(first_name, sim_id))
    return True

@sims4.commands.Command('synapse.balloon_clear', command_type=sims4.commands.CommandType.Live)
def synapse_balloon_clear_cmd(_connection=None):
    """
    Clears all active AI Balloons on screen.
    Usage: synapse.balloon_clear
    """
    output = sims4.commands.CheatOutput(_connection)
    cid = _get_client_id(_connection)
    sims4.commands.client_cheat("synapse_balloon_clear", cid)
    output("Synapse AI Balloons: Все баллоны очищены.")
    return True

# Auto-boot slot when lot finishes loading
try:
    from zone import Zone
    _orig_loading_screen = Zone.on_loading_screen_animation_finished
    def _synapse_lot_ready(self, *a, **kw):
        res = _orig_loading_screen(self, *a, **kw)
        try:
            _ensure_ui_slot()
        except Exception:
            pass
        return res
    Zone.on_loading_screen_animation_finished = _synapse_lot_ready
except Exception:
    pass
