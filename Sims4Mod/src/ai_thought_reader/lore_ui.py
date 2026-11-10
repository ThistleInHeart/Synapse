def _dispatch_ui_cmd(cmd_str: str, cid=None):
    """Sends command to Flash via balloons send_flash_command or fallback."""
    try:
        from balloons.synapse_balloons import send_flash_command
        send_flash_command(cmd_str, cid)
        return
    except Exception:
        pass
    try:
        if sims4 is not None:
            sims4.commands.client_cheat(cmd_str, cid)
    except Exception as e:
        log_exception(f"Error executing client_cheat {cmd_str}", e)

import binascii
from typing import Optional, Tuple
from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.lore_manager import (
    get_custom_sim_lore,
    set_custom_sim_lore,
    delete_custom_sim_lore,
    commit_lore_data_to_disk,
    get_custom_sim_race,
    set_custom_sim_race,
    delete_custom_sim_race,
    commit_race_data_to_disk,
)

try:
    import services
    import sims4.commands
except ImportError:
    services = None
    sims4 = None


from urllib.parse import quote, unquote

def encode_hex(text: str) -> str:
    """URL-encodes unicode string safely for ActionScript decodeURIComponent."""
    if not text:
        return "00"
    try:
        return quote(str(text), safe="")
    except Exception:
        return "00"


def decode_hex(enc_str: str) -> str:
    """Decodes URL-encoded or hex string back to unicode."""
    if not enc_str or enc_str == "00":
        return ""
    try:
        return unquote(str(enc_str))
    except Exception:
        return ""


def get_client_id(_connection=None) -> int:
    try:
        if _connection:
            return int(_connection)
        if services is not None:
            client = services.client_manager().get_first_client()
            if client:
                return int(client.id)
    except Exception:
        pass
    return 0


def get_sim_lore_info(sim_id=None) -> Tuple[Optional[object], str, str, str]:
    """Resolves sim_info, full name, current custom lore text, and custom race."""
    if services is None:
        return None, "Персонаж", "", ""

    sim_info_mgr = services.sim_info_manager()
    sim_info = None

    if sim_id:
        try:
            sid_num = int(sim_id)
            if sim_info_mgr:
                sim_info = sim_info_mgr.get(sid_num)
        except Exception:
            sim_info = None

    if sim_info is None:
        sim_info = services.active_sim_info()

    if sim_info is None:
        return None, "Персонаж", "", ""

    first = getattr(sim_info, "first_name", "") or ""
    last = getattr(sim_info, "last_name", "") or ""
    full_name = f"{first} {last}".strip() or "Персонаж"
    s_id = getattr(sim_info, "sim_id", 0)

    lore_text = get_custom_sim_lore(s_id) or ""
    race_text = get_custom_sim_race(s_id) or ""
    return sim_info, full_name, lore_text, race_text


def _get_common_ui_payload(target_sim_id=None):
    sim_info, full_name, lore_text, race_text = get_sim_lore_info(target_sim_id)
    s_id = str(getattr(sim_info, "sim_id", 0)) if sim_info else "0"
    enc_name = encode_hex(full_name)
    enc_lore = encode_hex(lore_text)
    enc_race = encode_hex(race_text)
    try:
        from ai_thought_reader.config import (
            get_packed_context_state_str,
            get_autonomy_enabled,
            get_autonomy_interval,
            get_packed_genealogy_state_str,
            get_packed_memory_state_str,
            get_packed_mods_state_str,
            get_packed_display_state_str,
            get_packed_experimental_state_str,
            get_packed_director_state_str,
        )
        packed_ctx = get_packed_context_state_str()
        auto_on = "1" if get_autonomy_enabled() else "0"
        auto_int = str(get_autonomy_interval())
        packed_gene = get_packed_genealogy_state_str()
        packed_mem = get_packed_memory_state_str()
        packed_mods = get_packed_mods_state_str()
        packed_disp = get_packed_display_state_str()
        packed_exp = get_packed_experimental_state_str()
        packed_director = get_packed_director_state_str()
    except Exception:
        packed_ctx = "00"
        auto_on = "1"
        auto_int = "240"
        packed_gene = "depth:10;max_relatives:100"
        packed_mem = "ev_mem:1;diag_hours:24;sum_pers:1;sum_grp:1"
        packed_mods = "ww_mode:bed_picker"
        packed_disp = "th_bal:1;th_notif:1;dir_bal:1;dir_notif:1;dtr_bal:1;dtr_notif:0"
        packed_exp = "dyn_act:0;biz:0;pause:1;alien:1;insane:0"
        packed_director = "en:0|dis:none"
    try:
        from ai_thought_reader.world_lore_manager import get_packed_world_lore_payload
        packed_world = get_packed_world_lore_payload()
    except Exception:
        packed_world = "00|0"
    return sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director


def open_lore_window(target_sim_id=None, _connection=None) -> bool:
    """
    Opens the Maxis-style Lore Settings window for target_sim_id or the active sim.
    Dispatches ui.synapse_settings and ui.synapse_settings_lore to Flash.
    """
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if not sim_info:
            return False

        # 1. UI slot & command dispatch handled by _dispatch_ui_cmd

        # 2. Open window with full sim, lore & context payload
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings lore {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log(f"[LORE_UI] Opened Lore UI for Sim {s_id}, lore length: {len(decode_hex(enc_lore))}")
            return True

    except Exception as e:
        log_exception("Failed to open Lore window", e)
    return False


def pick_sim_for_lore_window(_connection=None):
    """
    Opens native portrait SimPicker (UiSimPicker).
    When player picks a sim, sends updated sim details & lore payload to the Flash window.
    """
    try:
        active_sim = services.active_sim_info() if services else None
        if not active_sim:
            return

        sim_info_mgr = services.sim_info_manager() if services else None
        if not sim_info_mgr:
            return

        try:
            from ai_thought_reader.ui_dialogs import LoreSimPicker, SimPickerRow, SimPickerCellType, _get_localized_string
        except ImportError:
            from ui_dialogs import LoreSimPicker, SimPickerRow, SimPickerCellType, _get_localized_string
        if LoreSimPicker is None or SimPickerRow is None:
            return

        all_sims = []
        for s in sim_info_mgr.get_all():
            s_id = getattr(s, "sim_id", 0)
            if not s_id or getattr(s, "is_pet", False):
                continue
            age = getattr(getattr(s, "age", None), "name", "").upper()
            if age in ("BABY", "INFANT"):
                continue
            all_sims.append(s)

        if not all_sims:
            all_sims = [active_sim]

        owner_id = getattr(active_sim, "sim_id", 0)
        owner_hh = getattr(active_sim, "household", None)

        def _sort_key(s):
            sid = getattr(s, "sim_id", 0)
            is_active = 0 if (sid == owner_id) else 1
            is_hh = 0 if (owner_hh is not None and getattr(s, "household", None) == owner_hh) else 1
            has_l = 0 if get_custom_sim_lore(sid) else 1
            fn = getattr(s, "first_name", "") or ""
            ln = getattr(s, "last_name", "") or ""
            return (is_active, is_hh, has_l, fn.lower(), ln.lower())

        all_sims.sort(key=_sort_key)

        loc_title = _get_localized_string("Настройки: Выбор персонажа")
        loc_text = _get_localized_string("Выберите персонажа, чью биографию и лор хотите настроить:")

        factory = LoreSimPicker.TunableFactory()
        dialog = factory.default(
            active_sim,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )
        dialog.min_selectable = 1
        dialog.max_selectable = 1
        dialog.column_count = 3
        dialog.should_show_names = True
        dialog.display_filter = True
        if SimPickerCellType is not None:
            dialog.cell_type = SimPickerCellType.DEFAULT

        sim_by_id = {}
        for tgt in all_sims:
            tgt_id = getattr(tgt, "sim_id", 0)
            sim_by_id[tgt_id] = tgt
            row = SimPickerRow(
                sim_id=tgt_id,
                tag=tgt,
                select_default=(tgt_id == owner_id),
            )
            dialog.add_row(row)

        cid = get_client_id(_connection)

        def _on_response(dlg):
            try:
                if getattr(dlg, "accepted", False):
                    selected_sim = None
                    results = dlg.get_result_tags()
                    if results:
                        selected_sim = results[0]
                    if selected_sim is None and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in sim_by_id:
                                selected_sim = sim_by_id[pid]
                                break

                    if selected_sim is not None:
                        sel_id = str(getattr(selected_sim, "sim_id", 0))
                        first = getattr(selected_sim, "first_name", "") or ""
                        last = getattr(selected_sim, "last_name", "") or ""
                        full_name = f"{first} {last}".strip() or "Персонаж"
                        lore_text = get_custom_sim_lore(sel_id) or ""
                        race_text = get_custom_sim_race(sel_id) or ""

                        enc_name = encode_hex(full_name)
                        enc_lore = encode_hex(lore_text)
                        enc_race = encode_hex(race_text)

                        if sims4 is not None:
                            _dispatch_ui_cmd(f"ui.synapse_settings lore_sim {sel_id} {enc_name} {enc_lore} {enc_race}", cid)
                            log(f"[LORE_UI] SimPicker selected {sel_id} ({full_name}), updated Flash window.")
                else:
                    if sims4 is not None:
                        _dispatch_ui_cmd("ui.synapse_settings", cid)
            except Exception as e:
                log_exception("Error handling LoreSimPicker response", e)

        dialog.add_listener(_on_response)
        dialog.show_dialog()

    except Exception as e:
        log_exception("Error in pick_sim_for_lore_window", e)


def save_sim_lore_from_ui(sim_id_str: str, hex_lore: str, hex_race: str = "", _connection=None):
    """Saves custom lore text and custom race sent from Flash UI and notifies Flash."""
    try:
        cid = get_client_id(_connection)
        sim_id = int(sim_id_str)
        lore_text = decode_hex(hex_lore)
        race_text = decode_hex(hex_race)

        if lore_text.strip():
            set_custom_sim_lore(sim_id, lore_text.strip())
        else:
            delete_custom_sim_lore(sim_id)

        if race_text.strip():
            set_custom_sim_race(sim_id, race_text.strip())
        else:
            delete_custom_sim_race(sim_id)

        commit_lore_data_to_disk()
        commit_race_data_to_disk()
        log(f"[LORE_UI] Saved lore for Sim ID {sim_id}: {len(lore_text)} chars, race: '{race_text}'")

        if sims4 is not None:
            _dispatch_ui_cmd("ui.synapse_settings saved", cid)

    except Exception as e:
        log_exception(f"Error saving lore for {sim_id_str}", e)
        cid = get_client_id(_connection)
        if sims4 is not None:
            _dispatch_ui_cmd("ui.synapse_settings saved", cid)


def clear_sim_lore_from_ui(sim_id_str: str, _connection=None):
    """Clears custom lore and custom race for sim_id and updates Flash."""
    try:
        cid = get_client_id(_connection)
        sim_id = int(sim_id_str)
        delete_custom_sim_lore(sim_id)
        delete_custom_sim_race(sim_id)
        commit_lore_data_to_disk()
        commit_race_data_to_disk()
        log(f"[LORE_UI] Cleared lore and race for Sim ID {sim_id}")

        if sims4 is not None:
            _dispatch_ui_cmd("ui.synapse_settings cleared", cid)

    except Exception as e:
        log_exception(f"Error clearing lore for {sim_id_str}", e)


def open_context_window(_connection=None) -> bool:
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp = _get_common_ui_payload(None)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings context {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[CONTEXT_UI] Opened Context Settings UI")
            return True
    except Exception as e:
        log_exception("Failed to open Context window", e)
    return False


def update_context_flag_from_ui(mode: str, flag_name: str, val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_mode_context_flag
        enabled = str(val_str).strip() in ("1", "true", "True", "yes")
        set_mode_context_flag(str(mode).strip(), str(flag_name).strip(), enabled)
        log(f"[CONTEXT_UI] Updated flag {mode}.{flag_name} = {enabled}")
    except Exception as e:
        log_exception(f"Error updating context flag {mode}.{flag_name}", e)


def bulk_update_context_flags_from_ui(mode: str, action: str, _connection=None):
    try:
        cid = get_client_id(_connection)
        from ai_thought_reader.config import set_bulk_mode_context_flags, get_packed_context_state_str
        set_bulk_mode_context_flags(str(mode).strip(), str(action).strip())
        packed_ctx = get_packed_context_state_str()
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings ctx_sync {packed_ctx}", cid)
        log(f"[CONTEXT_UI] Bulk updated mode={mode} with action={action}")
    except Exception as e:
        log_exception(f"Error bulk updating context flags for {mode}", e)


def open_autonomy_window(_connection=None) -> bool:
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp = _get_common_ui_payload(None)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings autonomy {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[AUTONOMY_UI] Opened Autonomy Settings UI")
            return True
    except Exception as e:
        log_exception("Failed to open Autonomy window", e)
    return False


def open_genealogy_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Родство и связи' / Genealogy tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings genealogy {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[GENEALOGY_UI] Opened Genealogy Settings UI")
            return True
    except Exception as e:
        log_exception("Failed to open Genealogy window", e)
    return False


def update_genealogy_flag_from_ui(flag_key: str, val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_genealogy_type_flag
        enabled = str(val_str).strip().lower() in ("1", "true", "yes", "on")
        set_genealogy_type_flag(str(flag_key).strip(), enabled)
        log(f"[GENEALOGY_UI] Updated flag {flag_key} = {enabled}")
    except Exception as e:
        log_exception(f"Error updating genealogy flag {flag_key}", e)


def set_genealogy_depth_from_ui(depth_val: str, _connection=None):
    try:
        from ai_thought_reader.config import set_genealogy_max_depth
        d_val = int(str(depth_val).strip())
        if d_val >= 0:
            set_genealogy_max_depth(d_val)
            log(f"[GENEALOGY_UI] Updated max_depth = {d_val}")
    except Exception as e:
        log_exception(f"Error updating genealogy max_depth {depth_val}", e)


def bulk_update_genealogy_flags_from_ui(action: str, _connection=None):
    try:
        cid = get_client_id(_connection)
        from ai_thought_reader.config import set_bulk_genealogy_flags, get_packed_genealogy_state_str
        set_bulk_genealogy_flags(str(action).strip())
        packed_gene = get_packed_genealogy_state_str()
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings gene_sync {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director}", cid)
        log(f"[GENEALOGY_UI] Bulk updated genealogy flags with action={action}")
    except Exception as e:
        log_exception(f"Error bulk updating genealogy flags for {action}", e)


def open_memory_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Память и общение' / Memory tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings memory {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
        return True
    except Exception as e:
        log_exception("Failed to open memory window", e)
        return False


def open_mods_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Интеграция с модами' tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings mods {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[MODS_UI] Opened Mods Integration UI")
        return True
    except Exception as e:
        log_exception("Failed to open Mods window", e)
        return False


def set_ww_sex_mode_from_ui(mode_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_ww_sex_mode
        m = str(mode_str).strip()
        set_ww_sex_mode(m)
        log(f"[MODS_UI] Updated ww_sex_mode = {m}")
    except Exception as e:
        log_exception(f"Error updating ww_sex_mode {mode_str}", e)


def open_display_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Уведомления и баблы' tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings display {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[DISPLAY_UI] Opened Display Settings UI")
        return True
    except Exception as e:
        log_exception("Failed to open Display window", e)
        return False


def set_display_flag_from_ui(flag_key: str, val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_display_flag
        enabled = str(val_str).strip().lower() in ("1", "true", "yes", "on")
        set_display_flag(str(flag_key).strip(), enabled)
        log(f"[DISPLAY_UI] Updated display flag {flag_key} = {enabled}")
    except Exception as e:
        log_exception(f"Error updating display flag {flag_key}", e)


def open_experimental_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Экспериментальное' tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings experimental {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[EXPERIMENTAL_UI] Opened Experimental Settings UI")
        return True
    except Exception as e:
        log_exception("Failed to open Experimental window", e)
        return False


def set_experimental_flag_from_ui(flag_key: str, val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_experimental_flag
        enabled = str(val_str).strip().lower() in ("1", "true", "yes", "on")
        set_experimental_flag(str(flag_key).strip(), enabled)
        log(f"[EXPERIMENTAL_UI] Updated experimental flag {flag_key} = {enabled}")
    except Exception as e:
        log_exception(f"Error updating experimental flag {flag_key}", e)


def set_event_memory_from_ui(val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_event_memory_enabled
        enabled = str(val_str).strip().lower() in ("1", "true", "yes", "on")
        set_event_memory_enabled(enabled)
        log(f"[MEMORY_UI] Updated event_memory_enabled = {enabled}")
    except Exception as e:
        log_exception(f"Error updating event_memory_enabled {val_str}", e)


def set_dialogue_memory_hours_from_ui(val_str: str, _connection=None):
    try:
        from ai_thought_reader.config import set_dialogue_memory_hours
        v = int(str(val_str).strip())
        set_dialogue_memory_hours(v)
        log(f"[MEMORY_UI] Updated dialogue_memory_hours = {v}")
    except Exception as e:
        log_exception(f"Error updating dialogue_memory_hours {val_str}", e)


def clear_dialogue_log_from_ui(_connection=None):
    try:
        from ai_social_pc.conversation_log import clear_conversation_logs
        cnt = clear_conversation_logs()
        log(f"[MEMORY_UI] Cleared {cnt} dialogue log entries from UI.")
        from ai_thought_reader.localization import is_russian
        from ai_thought_reader.ui_dialogs import show_notification
        is_ru = is_russian()
        msg = f"Очищено записей диалогов: {cnt}." if is_ru else f"Cleared {cnt} recent conversation log entries."
        title = "Память диалогов" if is_ru else "Dialogue Memory"
        show_notification(title, msg)
    except Exception as e:
        log_exception("Error clearing dialogue log from UI", e)


def clear_longterm_memory_from_ui(_connection=None):
    try:
        from ai_social_pc.memory_manager import clear_all_memories
        cnt = clear_all_memories()
        log(f"[MEMORY_UI] Cleared {cnt} long-term memories from UI.")
        from ai_thought_reader.localization import is_russian
        from ai_thought_reader.ui_dialogs import show_notification
        is_ru = is_russian()
        msg = f"Очищено долгосрочных воспоминаний: {cnt}." if is_ru else f"Cleared {cnt} long-term memories."
        title = "Долгосрочная память" if is_ru else "Long-Term Memory"
        show_notification(title, msg)
    except Exception as e:
        log_exception("Error clearing long-term memory from UI", e)


def open_director_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Режиссёр общения' / Director tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings director {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[DIRECTOR_UI] Opened Director Settings UI")
        return True
    except Exception as e:
        log_exception("Failed to open Director window", e)
        return False


def open_worlds_window(target_sim_id=None, _connection=None) -> bool:
    """Opens the Settings window navigated directly to the 'Описания городов' / Worlds tab."""
    try:
        cid = get_client_id(_connection)
        sim_info, s_id, enc_name, enc_lore, enc_race, packed_ctx, auto_on, auto_int, packed_gene, packed_mem, packed_mods, packed_disp, packed_world, packed_exp, packed_director = _get_common_ui_payload(target_sim_id)
        if sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings worlds {s_id} {enc_name} {enc_lore} {packed_ctx} {auto_on} {auto_int} {packed_gene} {packed_mem} {packed_mods} {packed_disp} {packed_world} {packed_exp} {packed_director} {enc_race}", cid)
            log("[WORLDS_UI] Opened Worlds Settings UI")
        return True
    except Exception as e:
        log_exception("Failed to open Worlds window", e)
        return False


def set_world_lore_from_ui(world_key_enc: str, name_enc: str = "00", desc_enc: str = "00", _connection=None) -> bool:
    try:
        from ai_thought_reader import world_lore_manager
        world_key = decode_hex(world_key_enc)
        custom_name = decode_hex(name_enc)
        custom_desc = decode_hex(desc_enc)
        success = world_lore_manager.set_custom_world_data(world_key, custom_desc, custom_name)
        cid = get_client_id(_connection)
        if success and sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings world_saved {world_key_enc}", cid)
        log(f"[WORLDS_UI] Set custom world lore for '{world_key}': success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_world_lore_from_ui", e)
        return False


def delete_world_lore_from_ui(world_key_enc: str, _connection=None) -> bool:
    try:
        from ai_thought_reader import world_lore_manager
        world_key = decode_hex(world_key_enc)
        success = world_lore_manager.delete_custom_world_data(world_key)
        cid = get_client_id(_connection)
        if success and sims4 is not None:
            _dispatch_ui_cmd(f"ui.synapse_settings world_cleared {world_key_enc}", cid)
        log(f"[WORLDS_UI] Cleared custom world lore for '{world_key}': success={success}")
        return success
    except Exception as e:
        log_exception("Error in delete_world_lore_from_ui", e)
        return False


# =====================================================================
# Director UI Handlers & Commands
# =====================================================================

def set_director_master_from_ui(val_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_director_enabled
        enabled = (str(val_str).lower() in ("1", "true", "yes", "on"))
        success = set_director_enabled(enabled)
        log(f"[DIRECTOR_UI] Master director set to {enabled}: success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_director_master_from_ui", e)
        return False


def set_director_trigger_from_ui(state_str: str, trigger_str: str, val_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_director_trigger_flag
        enabled = (str(val_str).lower() in ("1", "true", "yes", "on"))
        success = set_director_trigger_flag(state_str, trigger_str, enabled)
        log(f"[DIRECTOR_UI] Set trigger '{state_str}_{trigger_str}' to {enabled}: success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_director_trigger_from_ui", e)
        return False


def set_director_timers_from_ui(silence_sec_str: str, pair_sec_str: str, grace_sec_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_director_timers
        s = int(str(silence_sec_str).strip())
        p = int(str(pair_sec_str).strip())
        g = int(str(grace_sec_str).strip())
        success = set_director_timers(s, p, g)
        log(f"[DIRECTOR_UI] Set director timers (silence={s}s, pair={p}s, grace={g}s): success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_director_timers_from_ui", e)
        return False


def set_director_trigger_meta_from_ui(trigger_str: str, is_immediate_str: str, prio_str: str, custom_prompt_enc: str = "00", enable_anim_str: str = "1", anim_type_str: str = "AUTO", _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_director_trigger_override
        imm = (str(is_immediate_str).lower() in ("1", "true", "yes", "on"))
        prio = int(str(prio_str).strip())
        custom_prompt = decode_hex(custom_prompt_enc) if custom_prompt_enc and custom_prompt_enc != "00" else None
        enable_anim = (str(enable_anim_str).lower() in ("1", "true", "yes", "on"))
        anim_type = str(anim_type_str).strip().upper() if anim_type_str else "AUTO"
        success = set_director_trigger_override(trigger_str, imm, prio, custom_prompt, enable_animation=enable_anim, animation_type=anim_type)
        log(f"[DIRECTOR_UI] Set trigger meta '{trigger_str}' (immediate={imm}, priority={prio}, custom_prompt={bool(custom_prompt)}, enable_anim={enable_anim}, anim_type={anim_type}): success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_director_trigger_meta_from_ui", e)
        return False


def reset_director_trigger_meta_from_ui(trigger_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import reset_director_trigger_override
        success = reset_director_trigger_override(trigger_str)
        log(f"[DIRECTOR_UI] Reset trigger meta '{trigger_str}': success={success}")
        return success
    except Exception as e:
        log_exception("Error in reset_director_trigger_meta_from_ui", e)
        return False


def bulk_director_state_from_ui(state_str: str, action_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import bulk_set_director_triggers
        all_triggers = None
        if action_str == "disable_all":
            try:
                from ai_social_pc import autonomous_director as ad
                st_clean = str(state_str).upper()
                if st_clean == "HOME":
                    all_triggers = list(ad.HOME_TRIGGERS)
                elif st_clean in ("VISITING_RELATIVES", "RELATIVES"):
                    all_triggers = list(ad.VISITING_RELATIVES_TRIGGERS)
                elif st_clean in ("VISITING_FRIENDS", "FRIENDS"):
                    all_triggers = list(ad.VISITING_FRIENDS_TRIGGERS)
                elif st_clean == "COMMUNITY":
                    all_triggers = list(ad.COMMUNITY_TRIGGERS)
            except Exception:
                pass
        success = bulk_set_director_triggers(state_str, action_str, all_triggers)
        log(f"[DIRECTOR_UI] Bulk action '{action_str}' on state '{state_str}': success={success}")
        return success
    except Exception as e:
        log_exception("Error in bulk_director_state_from_ui", e)
        return False


def pick_sim_for_memory_window(_connection=None):
    """
    Opens native portrait SimPicker (UiSimPicker) for picking a Sim for Section 5 (Memory Creation).
    When player picks a sim, sends updated sim details to Flash via 'ui.synapse_settings memory_sim'.
    """
    try:
        active_sim = services.active_sim_info() if services else None
        if not active_sim:
            return

        sim_info_mgr = services.sim_info_manager() if services else None
        if not sim_info_mgr:
            return

        try:
            from ai_thought_reader.ui_dialogs import LoreSimPicker, SimPickerRow, SimPickerCellType, _get_localized_string
        except ImportError:
            from ui_dialogs import LoreSimPicker, SimPickerRow, SimPickerCellType, _get_localized_string
        if LoreSimPicker is None or SimPickerRow is None:
            return

        all_sims = []
        for s in sim_info_mgr.get_all():
            s_id = getattr(s, "sim_id", 0)
            if not s_id or getattr(s, "is_pet", False):
                continue
            age = getattr(getattr(s, "age", None), "name", "").upper()
            if age in ("BABY", "INFANT"):
                continue
            all_sims.append(s)

        if not all_sims:
            all_sims = [active_sim]

        owner_id = getattr(active_sim, "sim_id", 0)
        owner_hh = getattr(active_sim, "household", None)

        def _sort_key(s):
            sid = getattr(s, "sim_id", 0)
            is_active = 0 if (sid == owner_id) else 1
            is_hh = 0 if (owner_hh is not None and getattr(s, "household", None) == owner_hh) else 1
            fn = getattr(s, "first_name", "") or ""
            ln = getattr(s, "last_name", "") or ""
            return (is_active, is_hh, fn.lower(), ln.lower())

        all_sims.sort(key=_sort_key)

        loc_title = _get_localized_string("Память: Выбор персонажа")
        loc_text = _get_localized_string("Выберите персонажа для создания воспоминания:")

        factory = LoreSimPicker.TunableFactory()
        dialog = factory.default(
            active_sim,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )
        dialog.min_selectable = 1
        dialog.max_selectable = 1
        dialog.column_count = 3
        dialog.should_show_names = True
        dialog.display_filter = True
        if SimPickerCellType is not None:
            dialog.cell_type = SimPickerCellType.DEFAULT

        sim_by_id = {}
        for tgt in all_sims:
            tgt_id = getattr(tgt, "sim_id", 0)
            sim_by_id[tgt_id] = tgt
            row = SimPickerRow(
                sim_id=tgt_id,
                tag=tgt,
                select_default=(tgt_id == owner_id),
            )
            dialog.add_row(row)

        cid = get_client_id(_connection)

        def _on_response(dlg):
            try:
                if getattr(dlg, "accepted", False):
                    selected_sim = None
                    results = dlg.get_result_tags()
                    if results:
                        selected_sim = results[0]
                    if selected_sim is None and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in sim_by_id:
                                selected_sim = sim_by_id[pid]
                                break

                    if selected_sim is not None:
                        sel_id = str(getattr(selected_sim, "sim_id", 0))
                        first = getattr(selected_sim, "first_name", "") or ""
                        last = getattr(selected_sim, "last_name", "") or ""
                        full_name = f"{first} {last}".strip() or "Персонаж"
                        enc_name = encode_hex(full_name)

                        if sims4 is not None:
                            _dispatch_ui_cmd(f"ui.synapse_settings memory_sim {sel_id} {enc_name}", cid)
                            log(f"[MEMORY_UI] SimPicker selected {sel_id} ({full_name}) for memory creation.")
                else:
                    if sims4 is not None:
                        _dispatch_ui_cmd("ui.synapse_settings", cid)
            except Exception as e:
                log_exception("Error handling Memory SimPicker response", e)

        dialog.add_listener(_on_response)
        dialog.show_dialog()

    except Exception as e:
        log_exception("Error in pick_sim_for_memory_window", e)


def set_multisim_rule_from_ui(rule_key_enc: str, text_enc: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_multisim_rule
        rule_key = decode_hex(rule_key_enc) if "%" in rule_key_enc else str(rule_key_enc).strip()
        rule_text = decode_hex(text_enc)
        success = set_multisim_rule(rule_key, rule_text)
        log(f"[MULTISIM_UI] Set multisim rule '{rule_key}': success={success}")
        return success
    except Exception as e:
        log_exception(f"Error in set_multisim_rule_from_ui '{rule_key_enc}'", e)
        return False


def reset_multisim_rules_from_ui(rule_key_enc: str = None, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import reset_multisim_rules
        rule_key = None
        if rule_key_enc and rule_key_enc != "00":
            rule_key = decode_hex(rule_key_enc) if "%" in rule_key_enc else str(rule_key_enc).strip()
        success = reset_multisim_rules(rule_key)
        log(f"[MULTISIM_UI] Reset multisim rules (key={rule_key}): success={success}")
        return success
    except Exception as e:
        log_exception("Error in reset_multisim_rules_from_ui", e)
        return False


def sync_multisim_rules_to_ui(_connection=None):
    try:
        cid = get_client_id(_connection)
        from ai_thought_reader.config import get_all_multisim_rules
        rules = get_all_multisim_rules()
        for rk, rval in rules.items():
            _dispatch_ui_cmd(f"ui.synapse_settings multisim_rule {rk} {encode_hex(rval)}", cid)
        log("[MULTISIM_UI] Synced multisim rules to UI.")
    except Exception as e:
        log_exception("Error syncing multisim rules to UI", e)


def set_simplified_master_from_ui(val_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_simplified_dialogue_enabled
        enabled = (str(val_str).lower() in ("1", "true", "yes", "on"))
        success = set_simplified_dialogue_enabled(enabled)
        log(f"[SIMPLIFIED_UI] Master simplified dialogue set to {enabled}: success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_simplified_master_from_ui", e)
        return False


def set_simplified_timers_from_ui(silence_sec_str: str, chance_pct_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_simplified_dialogue_timers
        sil = int(str(silence_sec_str).strip())
        ch = int(str(chance_pct_str).strip())
        success = set_simplified_dialogue_timers(sil, ch)
        log(f"[SIMPLIFIED_UI] Set timers (silence={sil}s, chance={ch}%): success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_simplified_timers_from_ui", e)
        return False


def set_simplified_display_from_ui(balloon_str: str, notif_str: str, _connection=None) -> bool:
    try:
        from ai_thought_reader.config import set_simplified_dialogue_display
        bal = (str(balloon_str).lower() in ("1", "true", "yes", "on"))
        notif = (str(notif_str).lower() in ("1", "true", "yes", "on"))
        success = set_simplified_dialogue_display(bal, notif)
        log(f"[SIMPLIFIED_UI] Set display (balloon={bal}, notif={notif}): success={success}")
        return success
    except Exception as e:
        log_exception("Error in set_simplified_display_from_ui", e)
        return False
