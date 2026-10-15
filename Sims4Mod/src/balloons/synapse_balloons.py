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

# 16 Curated Signature Designer Badges: (TopHex, BotHex)
# Perceptually balanced, guaranteed contrast with white text (#FFFFFF)
BADGE_PALETTE = [
    (0x569670, 0x3D7252),  # 0: Sage Green
    (0x3598A8, 0x227582),  # 1: Ocean Teal
    (0x4290B8, 0x2D7092),  # 2: Coastal Azure
    (0x4D6BFA, 0x344ECA),  # 3: Royal Cobalt
    (0x6966F0, 0x4D4ABF),  # 4: Deep Indigo
    (0x896BB8, 0x674D91),  # 5: Lavender Violet
    (0xA4559F, 0x7E3A7A),  # 6: Berry Magenta
    (0xD6628A, 0xAB4569),  # 7: Rose Coral
    (0xD45B4F, 0xA83F34),  # 8: Warm Terracotta
    (0xC77934, 0x9B5A1F),  # 9: Honey Amber
    (0xB08B32, 0x86671E),  # 10: Golden Ochre
    (0x789842, 0x59742B),  # 11: Olive Moss
    (0x45A38E, 0x307E6D),  # 12: Eucalyptus Mint
    (0x677882, 0x4B5B64),  # 13: Slate Steel
    (0x94677A, 0x72495B),  # 14: Dusty Mauve
    (0x8B6B54, 0x6B4F3A),  # 15: Warm Espresso
]

def get_sim_color_index(sim_id, avoid_index=None):
    try:
        sid = int(sim_id or 0)
    except Exception:
        sid = 0
    h = (sid ^ (sid >> 16) ^ (sid >> 32)) & 0xFFFFFFFF
    idx = h % len(BADGE_PALETTE)
    if avoid_index is not None and idx == avoid_index:
        shift = ((h >> 8) % (len(BADGE_PALETTE) - 1)) + 1
        idx = (idx + shift) % len(BADGE_PALETTE)
    return idx

def get_sim_badge_colors(sim_id, avoid_sim_id=None):
    avoid_idx = None
    if avoid_sim_id and str(avoid_sim_id) != str(sim_id):
        avoid_idx = get_sim_color_index(avoid_sim_id)
    idx = get_sim_color_index(sim_id, avoid_index=avoid_idx)
    return BADGE_PALETTE[idx]

def _do_client_cheat(sim_id, balloon_type, enc_name, enc_text, duration, cid, color_top=0, color_bot=0):
    cmd = "ui.synapse_balloon {} {} {} {} {} {} {}".format(
        sim_id, balloon_type, enc_name, enc_text, duration, color_top, color_bot
    )
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
        for sim_id, b_type, enc_name, enc_text, duration, old_cid, c_top, c_bot in _PENDING_BALLOONS:
            _do_client_cheat(sim_id, b_type, enc_name, enc_text, duration, cid or old_cid, c_top, c_bot)
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

def show_sim_balloon(sim_info_or_id=None, text="", balloon_type="speech", name=None, duration=None, avoid_sim_id=None, color_override=None):
    """
    Public API to display a speech or thought balloon over any Sim in the world.
    
    :param sim_info_or_id: SimInfo, Sim instance, int/str sim_id, or None (active sim).
    :param text: Text string to display inside the balloon.
    :param balloon_type: 'speech' or 'thought'.
    :param name: Optional author name override for NameBadge. If None, auto-detected from SimInfo.
    :param duration: Optional explicit display time in seconds. If None, calculated smartly.
    :return: True if sent or queued, False on error.
    """
    global _UI_READY, _PENDING_BALLOONS
    if not text:
        return False
        
    _ensure_ui_slot()
    
    # 1. Resolve SimInfo and sim_id
    sim_info = None
    sim_id_str = None
    
    if sim_info_or_id is None:
        if services is not None:
            sim_info = services.active_sim_info()
    elif hasattr(sim_info_or_id, 'sim_info'):
        # Sim instance (e.g. from interaction or actor)
        sim_info = getattr(sim_info_or_id, 'sim_info', None)
    elif hasattr(sim_info_or_id, 'first_name') or hasattr(sim_info_or_id, 'id') or hasattr(sim_info_or_id, 'sim_id'):
        # SimInfo object
        sim_info = sim_info_or_id
    elif isinstance(sim_info_or_id, (int, str)):
        sim_id_str = str(sim_info_or_id)
        if services is not None:
            sim_info_mgr = services.sim_info_manager()
            if sim_info_mgr is not None:
                try:
                    sim_info = sim_info_mgr.get(int(sim_info_or_id))
                except Exception:
                    pass

    if sim_id_str is None:
        if sim_info is not None:
            raw_id = getattr(sim_info, 'id', getattr(sim_info, 'sim_id', None))
            if raw_id is not None:
                sim_id_str = str(raw_id)
                
    if not sim_id_str:
        return False
        
    # 2. Resolve display name
    author_name = "Сим"
    if name is not None and str(name).strip():
        author_name = str(name).strip()
    elif sim_info is not None:
        first = getattr(sim_info, 'first_name', '')
        if first:
            author_name = str(first).strip()
            
    # 3. Clean and normalize text
    clean_text = str(text).strip()
    if balloon_type == "thought":
        # Remove surrounding quotes from thought if present
        clean_text = clean_text.strip('"\'«»')
    elif balloon_type == "speech":
        # Auto-detect thought indicators if speech was requested
        if clean_text.startswith(('*', '(', '«', '[думает]')):
            balloon_type = "thought"
            clean_text = clean_text.strip('"\'«»*()')

    # 4. Smart duration
    if duration is None or duration <= 0:
        duration = calculate_smart_duration(clean_text)

    # 5. Determine unique signature badge colors
    if color_override and isinstance(color_override, (tuple, list)) and len(color_override) >= 2:
        color_top, color_bot = int(color_override[0]), int(color_override[1])
    else:
        color_top, color_bot = get_sim_badge_colors(sim_id_str, avoid_sim_id=avoid_sim_id)
        
    enc_name = quote(author_name)
    enc_text = quote(clean_text)
    cid = _get_client_id()
    
    if _UI_READY:
        _do_client_cheat(sim_id_str, balloon_type, enc_name, enc_text, duration, cid, color_top, color_bot)
    else:
        _PENDING_BALLOONS.append((sim_id_str, balloon_type, enc_name, enc_text, duration, cid, color_top, color_bot))
        
    return True

def _show_balloon_internal(balloon_type, *args, _connection=None):
    global _UI_READY, _PENDING_BALLOONS
    output = sims4.commands.CheatOutput(_connection)
    
    sim_info = services.active_sim_info() if services is not None else None
    if sim_info is None:
        output("Synapse AI Balloons: Нет активного сима на участке!")
        return False
        
    first_name = str(getattr(sim_info, 'first_name', 'Сим'))
    
    if args:
        text = " ".join(str(a) for a in args).strip('"\'')
    else:
        if balloon_type == "thought":
            text = "Хм... о чем бы мне сейчас подумать? Кажется, этот мод на мысли симов работает идеально!"
        else:
            text = "Привет! Это AI Balloons от Synapse с эффектом печатной машинки!"
            
    res = show_sim_balloon(sim_info_or_id=sim_info, text=text, balloon_type=balloon_type, name=first_name)
    
    duration = calculate_smart_duration(text)
    type_label = "Мысль" if balloon_type == "thought" else "Речь"
    if _UI_READY:
        output("Synapse AI Balloons [{}]: Показано над головой {} (длительность: {}с)!".format(type_label, first_name, duration))
    else:
        output("Synapse AI Balloons: Инициализация Flash UI... {} появится над головой {} сразу после загрузки.".format(type_label, first_name))
        
    return res

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
