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

import os

import time

import sims4.commands

import services

from urllib.parse import quote



try:

    from distributor.system import Distributor

    from distributor.ops import SendUIMessage

    HAS_DISTRIBUTOR = True

except ImportError:

    HAS_DISTRIBUTOR = False



LOG_FILE_PATH = os.path.expanduser(r'~\\Documents\\Electronic Arts\\The Sims 4\\synapse_balloons.log')



def _log(msg):

    try:

        ts = time.strftime('%Y-%m-%d %H:%M:%S')

        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:

            f.write(f'[{ts}] {msg}\n')

    except Exception:

        pass



import sys



_SLOT_BOOTED = False

_UI_READY = False

_PENDING_BALLOONS = []

_PENDING_COMMANDS = []



def _get_shared_mods():

    mods = []

    for mname in ('synapse_balloons', 'balloons.synapse_balloons', __name__):

        m = sys.modules.get(mname)

        if m is not None and m not in mods:

            mods.append(m)

    return mods



def _is_ui_ready():

    for m in _get_shared_mods():

        if getattr(m, '_UI_READY', False):

            return True

    return _UI_READY



def _is_slot_booted():

    for m in _get_shared_mods():

        if getattr(m, '_SLOT_BOOTED', False):

            return True

    return _SLOT_BOOTED



def send_flash_command(cmd, cid=None):

    """Sends a client cheat to Flash immediately, and queues it if Flash UI is not ready yet."""

    global _UI_READY, _PENDING_COMMANDS

    if not _is_slot_booted():

        _ensure_ui_slot(force=False)

    target_cid = cid if cid is not None else _get_client_id()

    try:

        sims4.commands.client_cheat(cmd, target_cid)

        _log(f"[send_flash_command] Dispatched immediately: {cmd} (cid={target_cid}, ready={_is_ui_ready()})")

    except Exception as e:

        _log(f"[send_flash_command] Error dispatching {cmd}: {e}")

    if not _is_ui_ready():

        _PENDING_COMMANDS.append((cmd, target_cid))

        _log(f"[send_flash_command] Also queued pending command: {cmd} (cid={target_cid})")





def reset_balloon_ui():

    global _SLOT_BOOTED, _UI_READY, _PENDING_BALLOONS, _PENDING_COMMANDS

    _log(f'[reset_balloon_ui] Old state: _SLOT_BOOTED={_SLOT_BOOTED}, _UI_READY={_UI_READY}, queue={len(_PENDING_BALLOONS)}')

    _SLOT_BOOTED = False

    _UI_READY = False

    _PENDING_BALLOONS.clear()

    _PENDING_COMMANDS.clear()

    for m in _get_shared_mods():

        m._SLOT_BOOTED = False

        m._UI_READY = False



def _ensure_ui_slot(force=False):

    global _SLOT_BOOTED

    already_booted = _is_slot_booted()

    _log(f'[_ensure_ui_slot] force={force}, _SLOT_BOOTED={already_booted}')

    if already_booted and not force:

        return

    cid = _get_client_id()

    if HAS_DISTRIBUTOR:

        try:

            Distributor.instance().add_op_with_no_owner(SendUIMessage('ShowFacebookDisplay'))

            Distributor.instance().add_op_with_no_owner(SendUIMessage('HideCompleteFacebookDisplay'))

            _SLOT_BOOTED = True

            for m in _get_shared_mods():

                m._SLOT_BOOTED = True

            _log('[_ensure_ui_slot] Dispatched ShowFacebookDisplay + HideCompleteFacebookDisplay')

        except Exception as e:

            _log(f'[_ensure_ui_slot] ShowFacebookDisplay exception: {e}')

    try:

        sims4.commands.client_cheat('ui.synapse_boot', cid)

        _log(f'[_ensure_ui_slot] Dispatched ui.synapse_boot cheat (cid={cid})')

    except Exception as e_boot:

        _log(f'[_ensure_ui_slot] ui.synapse_boot cheat exception: {e_boot}')



def _hook_zone_load():

    try:

        from zone import Zone

        orig_load = getattr(Zone, 'load_zone', None)

        if orig_load is not None and not getattr(orig_load, '_synapse_balloon_load_hooked', False):

            def _wrapped_load(self, *args, **kwargs):

                _log('[ZONE HOOK] Zone.load_zone started')

                try:

                    reset_balloon_ui()

                except Exception:

                    pass

                res = orig_load(self, *args, **kwargs)

                return res

            _wrapped_load._synapse_balloon_load_hooked = True

            Zone.load_zone = _wrapped_load



        orig_teardown = getattr(Zone, 'on_teardown', None)

        if orig_teardown is not None and not getattr(orig_teardown, '_synapse_balloon_teardown_hooked', False):

            def _wrapped_teardown(self, *args, **kwargs):

                _log('[ZONE HOOK] Zone.on_teardown detected')

                try:

                    reset_balloon_ui()

                except Exception:

                    pass

                return orig_teardown(self, *args, **kwargs)

            _wrapped_teardown._synapse_balloon_teardown_hooked = True

            Zone.on_teardown = _wrapped_teardown



        orig_finished = getattr(Zone, 'on_loading_screen_animation_finished', None)

        if orig_finished is not None and not getattr(orig_finished, '_synapse_balloon_finished_hooked', False):

            def _wrapped_finished(self, *args, **kwargs):

                res = orig_finished(self, *args, **kwargs)

                _log('[ZONE HOOK] Zone.on_loading_screen_animation_finished detected -> booting slot')

                try:

                    _ensure_ui_slot(force=True)

                except Exception as e_fin:

                    _log(f'[ZONE HOOK] Error in loading screen finished boot: {e_fin}')

                return res

            _wrapped_finished._synapse_balloon_finished_hooked = True

            Zone.on_loading_screen_animation_finished = _wrapped_finished

    except Exception as e_h:

        _log(f'[ZONE HOOK] Failed setting up zone hooks: {e_h}')



_hook_zone_load()



try:

    if services is not None:

        cur_zone = getattr(services, 'current_zone', lambda: None)()

        if cur_zone is not None and getattr(cur_zone, 'is_zone_running', False):

            _ensure_ui_slot()

except Exception:

    pass



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

    Computes display time based on text length and custom user balloon_style:

    - Typing speed (chars/sec)

    - Base hold time + hold per char

    - Duration multiplier

    """

    chars = len(text)

    try:

        from ai_thought_reader.config import get_balloon_style

        bs = get_balloon_style()

    except Exception:

        bs = {}

    type_speed = bs.get("type_speed", 35)

    speed = float(type_speed) if type_speed and type_speed > 0 else 1000.0

    dur_mult = max(0.5, min(2.5, bs.get("duration_pct", 100) / 100.0))

    typing_time = (chars / speed) if speed < 1000.0 else 0.4

    hold_time = 2.5 + (chars * 0.045)

    total = (typing_time + hold_time) * dur_mult

    return max(3.5, min(25.0, round(total, 1)))



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



def sync_balloon_style_to_flash(cid=None):

    """Dispatches current balloon style configuration to Flash."""

    try:

        from ai_thought_reader.config import get_packed_balloon_style_str

        packed = get_packed_balloon_style_str()

        send_flash_command(f"ui.synapse_settings balloon_style {packed}", cid=cid)

        _log(f"[sync_balloon_style_to_flash] Dispatched: {packed}")

    except Exception as e:

        _log(f"[sync_balloon_style_to_flash] Error: {e}")



@sims4.commands.Command('synapse.ui_ready', command_type=sims4.commands.CommandType.Live)

def synapse_ui_ready_cmd(_connection=None):

    """Callback from ActionScript when Flash UI is added to stage and ready."""

    global _UI_READY, _SLOT_BOOTED, _PENDING_BALLOONS, _PENDING_COMMANDS

    was_ready = _is_ui_ready()

    _UI_READY = True

    _SLOT_BOOTED = True

    for m in _get_shared_mods():

        m._UI_READY = True

        m._SLOT_BOOTED = True

    cid = _get_client_id(_connection)

    _log(f"[synapse.ui_ready] Received callback from ActionScript! cid={cid}, was_ready={was_ready}")

    output = sims4.commands.CheatOutput(cid)

    if not was_ready:

        output("Synapse AI Balloons: Flash UI подключен и готов к работе!")

    sync_balloon_style_to_flash(cid)

    

    # Flush any pending UI commands across all module aliases

    for m in _get_shared_mods():

        p_cmds = getattr(m, '_PENDING_COMMANDS', None)

        if p_cmds:

            _log(f"[synapse.ui_ready] Flushing {len(p_cmds)} pending commands from {m.__name__}")

            for p_cmd, p_cid in list(p_cmds):

                try:

                    sims4.commands.client_cheat(p_cmd, p_cid or cid)

                    _log(f"[synapse.ui_ready] Flushed command: {p_cmd}")

                except Exception as e_cmd:

                    _log(f"[synapse.ui_ready] Error flushing {p_cmd}: {e_cmd}")

            p_cmds.clear()



    # Flush any pending balloons

    if _PENDING_BALLOONS:

        _log(f"[synapse.ui_ready] Flushing {len(_PENDING_BALLOONS)} pending balloons...")

        for sim_id, b_type, enc_name, enc_text, duration, old_cid, c_top, c_bot in _PENDING_BALLOONS:

            _do_client_cheat(sim_id, b_type, enc_name, enc_text, duration, cid or old_cid, c_top, c_bot)

        _PENDING_BALLOONS.clear()

        output("Synapse AI Balloons: Отложенные сообщения успешно отображены!")

    return True



@sims4.commands.Command('synapse.ui_log', command_type=sims4.commands.CommandType.Live)

def synapse_ui_log_cmd(enc_msg="", _connection=None):

    """Diagnostic logger receiving events from ActionScript."""

    from urllib.parse import unquote

    try:

        msg = unquote(str(enc_msg))

    except Exception:

        msg = str(enc_msg)

    _log(f"[FLASH] {msg}")

    return True



@sims4.commands.Command('synapse.balloon_boot', command_type=sims4.commands.CommandType.Live)

def synapse_balloon_boot_cmd(_connection=None):

    """Manually boot the UI slot."""

    output = sims4.commands.CheatOutput(_connection)

    reset_balloon_ui()

    _ensure_ui_slot(force=True)

    output("Synapse AI Balloons: UI-слот сброшен и принудительно запущен заново.")

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

        

    if not _SLOT_BOOTED:

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

    

    _log(f"[show_sim_balloon] author={author_name}, sim_id={sim_id_str}, type={balloon_type}, _UI_READY={_UI_READY}")

    

    # Always attempt direct client cheat dispatch immediately

    _do_client_cheat(sim_id_str, balloon_type, enc_name, enc_text, duration, cid, color_top, color_bot)

    _log(f"[show_sim_balloon] Dispatched ui.synapse_balloon directly")

    

    if not _UI_READY:

        _PENDING_BALLOONS.append((sim_id_str, balloon_type, enc_name, enc_text, duration, cid, color_top, color_bot))

        _log(f"[show_sim_balloon] Also queued in _PENDING_BALLOONS (total: {len(_PENDING_BALLOONS)})")

        if not _SLOT_BOOTED:

            _ensure_ui_slot()

        

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

    output("Synapse AI Balloons [{}]: Отправлено над головой {} (длительность: {}с)!".format(type_label, first_name, duration))

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



@sims4.commands.Command('synapse.custom_ui', 'synapse.test_ui', 'synapse.ui_test', command_type=sims4.commands.CommandType.Live)

def synapse_custom_ui_cmd(*args, _connection=None):

    """

    Test and diagnostic command for Synapse Custom UI and Flash balloons.

    Usage in cheat console:

        synapse.custom_ui        - reports UI status and sends a test balloon

        synapse.custom_ui boot   - re-boots the Flash UI slot

        synapse.custom_ui menu   - opens the main in-game settings dialog

    """

    output = sims4.commands.CheatOutput(_connection)

    subcmd = " ".join(str(a) for a in args).strip().lower()



    if subcmd == "menu":

        try:

            from ai_thought_reader.commands import execute_menu

            execute_menu(target_sim_id=None, _connection=_connection)

            output("Synapse UI: Открыто главное меню настроек.")

            return True

        except Exception as e:

            output("Synapse UI: Ошибка открытия меню: {}".format(e))

            return False



    if subcmd == "boot":

        reset_balloon_ui()

        _ensure_ui_slot(force=True)

        output("Synapse UI: UI-слот сброшен и принудительно перезапущен.")

        return True



    output("==================================================")

    output("       SYNAPSE AI CUSTOM UI / BALLOONS STATUS     ")

    output("==================================================")

    output(" - UI Slot Booted: {}".format(_SLOT_BOOTED))

    output(" - Flash UI Ready: {}".format(_UI_READY))

    output(" - Pending Balloons Queue: {}".format(len(_PENDING_BALLOONS)))



    sim_info = services.active_sim_info() if services is not None else None

    if sim_info is not None:

        first_name = str(getattr(sim_info, 'first_name', 'Сим'))

        output(" - Active Sim: {} (ID: {})".format(first_name, getattr(sim_info, 'id', '0')))

    else:

        output(" - Active Sim: Нет активного сима на участке")



    output("Отправка тестового AI-баллона...")

    show_sim_balloon(sim_info_or_id=sim_info, text="Тест Custom UI: Flash-баллон работает корректно!", balloon_type="speech")

    output("==================================================")

    return True



# =====================================================================

# Synapse Balloon Studio & Interactive Preview Commands

# =====================================================================



_studio_prev_clock_speed = None

_studio_target_sim_id = None



@sims4.commands.Command('synapse.balloon_studio_start', command_type=sims4.commands.CommandType.Live)

def synapse_balloon_studio_start_cmd(_connection=None):

    """Starts Balloon Studio: pauses game, finds active or available sim, notifies Flash."""

    global _studio_prev_clock_speed, _studio_target_sim_id

    cid = _get_client_id(_connection)

    

    # 1. Pause game simulation

    try:

        from clock import ClockSpeedMode

    except ImportError:

        ClockSpeedMode = None

    try:

        gcs = services.game_clock_service()

        if gcs is not None and hasattr(gcs, "set_clock_speed"):

            cs = getattr(gcs, "clock_speed", None)

            if callable(cs):

                try:

                    cs = cs()

                except Exception:

                    pass

            _studio_prev_clock_speed = cs

            pause_val = getattr(ClockSpeedMode, "PAUSED", 0) if ClockSpeedMode is not None else 0

            gcs.set_clock_speed(pause_val)

            _log(f"[studio_start] Game paused. Previous speed: {_studio_prev_clock_speed}")

    except Exception as e:

        _log(f"[studio_start] Pause error: {e}")



    # 2. Find target sim on lot

    target_sim = None

    try:

        client = services.client_manager().get_first_client()

        if client is not None:

            target_sim = client.active_sim

        if target_sim is None or not getattr(target_sim, "is_instantiated", lambda: True)():

            for sim in services.sim_info_manager().instantiated_sims():

                if getattr(sim, "is_sim", True) and not getattr(sim, "is_pet", False):

                    target_sim = sim

                    break

    except Exception as e_sim:

        _log(f"[studio_start] Sim lookup error: {e_sim}")



    sim_id_str = str(getattr(target_sim, "id", 0)) if target_sim is not None else "0"

    sim_name_str = "Сим"

    if target_sim is not None:

        try:

            first = getattr(target_sim, "first_name", "") or ""

            last = getattr(target_sim, "last_name", "") or ""

            full = f"{first} {last}".strip()

            if full:

                sim_name_str = full

        except Exception:

            pass

    _studio_target_sim_id = sim_id_str



    # 3. Synchronize current balloon style to Flash

    sync_balloon_style_to_flash(cid)



    # 4. Notify Flash to open the Studio panel and attach preview balloon over sim's head

    enc_name = quote(sim_name_str)

    send_flash_command(f"ui.synapse_settings studio_start {sim_id_str} {enc_name}", cid=cid)

    _log(f"[studio_start] Studio started for sim {sim_id_str} ({sim_name_str})")

    return True





@sims4.commands.Command('synapse.balloon_studio_stop', command_type=sims4.commands.CommandType.Live)

def synapse_balloon_studio_stop_cmd(_connection=None):

    """Stops Balloon Studio: restores previous game clock speed."""

    global _studio_prev_clock_speed

    cid = _get_client_id(_connection)

    try:

        from clock import ClockSpeedMode

        normal_val = getattr(ClockSpeedMode, "NORMAL", 1) if ClockSpeedMode is not None else 1

    except ImportError:

        normal_val = 1

    try:

        gcs = services.game_clock_service()

        if gcs is not None and hasattr(gcs, "set_clock_speed"):

            target_speed = _studio_prev_clock_speed if _studio_prev_clock_speed is not None else normal_val

            gcs.set_clock_speed(target_speed)

            _log(f"[studio_stop] Restored game clock speed to: {target_speed}")

    except Exception as e:

        _log(f"[studio_stop] Restore clock error: {e}")

    return True





@sims4.commands.Command('synapse.balloon_studio_focus', command_type=sims4.commands.CommandType.Live)

def synapse_balloon_studio_focus_cmd(sim_id_arg="", _connection=None):

    """Button click in Studio HUD to focus camera on the target sim."""

    global _studio_target_sim_id

    target_id = sim_id_arg or _studio_target_sim_id

    cid = _get_client_id(_connection)

    if target_id and str(target_id) != "0":

        try:

            sims4.commands.client_cheat(f"camera.focus_on_sim {target_id}", cid)

            _log(f"[studio_focus] Camera focused on sim: {target_id}")

        except Exception as e:

            _log(f"[studio_focus] Error focusing camera: {e}")

    return True





@sims4.commands.Command('synapse.set_balloon_style', command_type=sims4.commands.CommandType.Live)

def synapse_set_balloon_style_cmd(*args, _connection=None):

    """Persists balloon style dictionary from Flash UI."""

    if not args:

        return False

    packed = str(args[0])

    style_dict = {}

    for item in packed.split(";"):

        if ":" in item:

            k, v = item.split(":", 1)

            k = k.strip()

            v = v.strip()

            if k in ("show_name", "camera_scale"):

                style_dict[k] = (v == "1")

            elif k == "theme":

                style_dict[k] = str(v)

            else:

                try:

                    style_dict[k] = int(v)

                except ValueError:

                    pass

    try:

        from ai_thought_reader.config import set_balloon_style

        set_balloon_style(style_dict)

        _log(f"[set_balloon_style] Successfully saved {len(style_dict)} style properties.")

    except Exception as e:

        _log(f"[set_balloon_style] Error saving style: {e}")

    return True





@sims4.commands.Command('synapse.reset_balloon_style', command_type=sims4.commands.CommandType.Live)

def synapse_reset_balloon_style_cmd(_connection=None):

    """Resets balloon style to defaults and synchronizes back to Flash."""

    cid = _get_client_id(_connection)

    try:

        from ai_thought_reader.config import reset_balloon_style

        reset_balloon_style()

        sync_balloon_style_to_flash(cid)

        _log("[reset_balloon_style] Balloon style reset to defaults.")

    except Exception as e:

        _log(f"[reset_balloon_style] Error: {e}")

    return True



