import random
from typing import Callable, Optional, Dict, Any, List, Tuple, Set
from ai_social_pc.logger import log, log_exception
from ai_social_pc.chat_manager import (
    get_session_history,
    clear_session_history,
    _get_relationship_description,
    strip_emojis,
    parse_and_strip_relationship_tags,
)

try:
    import services
    from sims4.localization import LocalizationHelperTuning
    from ui.ui_dialog_picker import (
        UiItemPicker,
        BasePickerRow,
        UiSimPicker,
        SimPickerRow,
        SimPickerCellType,
    )
    from ui.ui_dialog_generic import UiDialogTextInputOkCancel
    from ui.ui_dialog import UiDialogOk
    from ui.ui_dialog_notification import UiDialogNotification
    from distributor.shared_messages import IconInfoData
except ImportError:
    services = None
    LocalizationHelperTuning = None
    UiItemPicker = None
    BasePickerRow = None
    UiSimPicker = None
    SimPickerRow = None
    SimPickerCellType = None
    UiDialogTextInputOkCancel = None
    UiDialogOk = None
    UiDialogNotification = None
    IconInfoData = None


if UiSimPicker is not None:
    class ChatSimPicker(UiSimPicker):
        def _validate_row(self, row):
            return True

        @property
        def multi_select(self):
            return False

    class ChatMultiSimPicker(UiSimPicker):
        def _validate_row(self, row):
            return True

        @property
        def multi_select(self):
            return True
else:
    ChatSimPicker = None
    ChatMultiSimPicker = None


if UiItemPicker is not None:
    class ChatActionPicker(UiItemPicker):
        def _validate_row(self, row):
            return True

        @property
        def multi_select(self):
            return False
else:
    ChatActionPicker = None


def _is_en() -> bool:
    try:
        from ai_social_pc.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False


def _get_loc_text(text: str):
    if LocalizationHelperTuning is not None:
        try:
            return LocalizationHelperTuning.get_raw_text(str(text))
        except Exception:
            pass
    return str(text)


def show_chat_notification(title: str, text: str, sim_info=None, is_error: bool = False):
    """Displays a game notification in the upper-right corner with the Sim's portrait."""
    try:
        if services is None or UiDialogNotification is None or LocalizationHelperTuning is None:
            log(f"[UI FALLBACK NOTIF] {title}: {text}")
            return

        client = services.client_manager().get_first_client()
        if client is None:
            return

        active_sim = client.active_sim
        active_sim_info = getattr(client, "active_sim_info", None)
        if active_sim_info is None and active_sim is not None:
            active_sim_info = getattr(active_sim, "sim_info", None)

        owner = sim_info if sim_info is not None and not isinstance(sim_info, dict) else (active_sim_info or active_sim)

        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)

        visual_type = (
            UiDialogNotification.UiDialogNotificationVisualType.SPECIAL_MOMENT
            if not is_error
            else UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
        )

        notification = UiDialogNotification.TunableFactory().default(
            owner,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
            visual_type=visual_type,
        )

        try:
            if sim_info is not None and not isinstance(sim_info, dict) and IconInfoData is not None:
                icon_obj = IconInfoData(obj_instance=sim_info)
                notification.show_dialog(icon_override=icon_obj)
            else:
                notification.show_dialog()
        except Exception:
            notification.show_dialog()

        log(f"[NOTIF] Displayed '{title}': '{text[:50]}...'")
    except Exception as e:
        log_exception("Error showing chat notification", e)


def get_recipient_display_name(recipient) -> str:
    if isinstance(recipient, dict):
        return recipient.get("name", "Interlocutor" if _is_en() else "Собеседник")
    f_name = getattr(recipient, "first_name", "") or ""
    l_name = getattr(recipient, "last_name", "") or ""
    return f"{f_name} {l_name}".strip() or ("Interlocutor" if _is_en() else "Собеседник")


def is_sim_an_animal(sim_info) -> bool:
    """
    Returns True if sim_info is any kind of animal/pet (dog, cat, horse, fox, etc.).
    Returns False for human Sims.
    """
    if sim_info is None:
        return False
    try:
        # Unwrap Sim/GameObject to SimInfo if necessary
        if hasattr(sim_info, "sim_info"):
            sim_info = getattr(sim_info, "sim_info", sim_info)

        # 1. is_pet property/attribute
        if hasattr(sim_info, "is_pet"):
            val = sim_info.is_pet
            if bool(val() if callable(val) else val):
                return True

        # 2. is_human check
        if hasattr(sim_info, "is_human"):
            val = sim_info.is_human
            if not bool(val() if callable(val) else val):
                return True

        # 3. is_animal check
        if hasattr(sim_info, "is_animal"):
            val = sim_info.is_animal
            if bool(val() if callable(val) else val):
                return True

        # 4. species check (enum or int: 1=HUMAN, 2=DOG, 3=CAT, 4=HORSE)
        species = getattr(sim_info, "species", None)
        if species is not None:
            sp_name = str(getattr(species, "name", species)).upper()
            if any(k in sp_name for k in ("DOG", "CAT", "HORSE", "ANIMAL", "PET", "FOX")):
                return True
            if sp_name not in ("HUMAN", "SPECIES.HUMAN", "1", ""):
                try:
                    if int(species) != 1:
                        return True
                except (ValueError, TypeError):
                    pass

        # 5. extended_species check
        ext_species = getattr(sim_info, "extended_species", None)
        if ext_species is not None:
            ext_name = str(getattr(ext_species, "name", ext_species)).upper()
            if any(k in ext_name for k in ("DOG", "CAT", "HORSE", "ANIMAL", "PET", "FOX")):
                return True
            if ext_name not in ("HUMAN", "EXTENDEDSPECIES.HUMAN", "1", ""):
                try:
                    if int(ext_species) != 1:
                        return True
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    return False


def get_current_sim_hour() -> int:
    """Returns current in-game hour (0-23)."""
    try:
        if services is not None:
            now = None
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
            elif services.game_clock_service() is not None:
                now = services.game_clock_service().now()

            if now is not None:
                h_val = getattr(now, "hour", 12)
                return h_val() if callable(h_val) else int(h_val)
    except Exception:
        pass
    import time
    return int(time.strftime("%H"))


def get_current_sim_day() -> int:
    """Returns current in-game day number for deterministic daily seed."""
    try:
        if services is not None:
            now = None
            time_service = services.time_service()
            if time_service is not None and hasattr(time_service, "sim_now"):
                now = time_service.sim_now
            elif services.game_clock_service() is not None:
                now = services.game_clock_service().now()

            if now is not None:
                if hasattr(now, "absolute_days"):
                    res = now.absolute_days()
                    return res() if callable(res) else int(res)
                if hasattr(now, "day"):
                    res = now.day()
                    return res() if callable(res) else int(res)
    except Exception:
        pass
    import time
    return int(time.strftime("%j"))


def _detect_sim_occult(sim_info) -> str:
    """Returns 'werewolf', 'vampire', or 'human'."""
    if sim_info is None:
        return "human"
    try:
        from ai_thought_reader.context import get_sim_occult_info
        info_str = get_sim_occult_info(sim_info).lower()
        if "оборотень" in info_str or "werewolf" in info_str:
            return "werewolf"
        if "вампир" in info_str or "vampire" in info_str:
            return "vampire"
    except Exception:
        pass

    if hasattr(sim_info, "get_traits"):
        try:
            for t in sim_info.get_traits():
                t_name = getattr(t, "__name__", str(t)).lower()
                if "werewolf" in t_name or "оборотень" in t_name:
                    return "werewolf"
                if "vampire" in t_name or "вампир" in t_name:
                    return "vampire"
        except Exception:
            pass

    if hasattr(sim_info, "occult_tracker") and sim_info.occult_tracker is not None:
        try:
            for occult_attr in ["occult_types", "_occult_types"]:
                types = getattr(sim_info.occult_tracker, occult_attr, None)
                if types:
                    for t in types:
                        t_name = getattr(t, "name", str(t)).lower()
                        if "werewolf" in t_name:
                            return "werewolf"
                        if "vampire" in t_name:
                            return "vampire"
        except Exception:
            pass

    return "human"


def is_sim_online(sim_info) -> bool:
    """
    Determines whether a Sim is online or offline in the messenger.
    Rules:
    - Werewolves: Always online (24/7).
    - Vampires: Online during evening/night (18:00 - 06:00). During day (06:00 - 18:00), offline (15% chance online).
    - Regular Sims: Online during day (06:00 - 23:00). At night (23:00 - 06:00), offline (15% chance online).
    Uses a deterministic daily seed per Sim to avoid flickering status within the same night.
    """
    if sim_info is None:
        return True

    occult = _detect_sim_occult(sim_info)
    if occult == "werewolf":
        return True

    hour = get_current_sim_hour()
    sim_id = getattr(sim_info, "sim_id", 0) if not isinstance(sim_info, dict) else sim_info.get("id", 0)
    if not sim_id:
        sim_id = abs(hash(str(sim_info)))
    sim_day = get_current_sim_day()

    # Deterministic 15% roll per Sim for this day/night
    is_night_owl = ((sim_id * 37 + sim_day * 13) % 100) < 15

    if occult == "vampire":
        # Vampires are active in evening/night: 18:00 - 06:00
        is_night_time = (hour >= 18 or hour < 6)
        if is_night_time:
            return True
        return is_night_owl

    # Regular Sims: active in daytime 06:00 - 23:00. At night: 15% chance
    is_day_time = (6 <= hour < 23)
    if is_day_time:
        return True
    return is_night_owl


def is_sim_truly_known(actor_sim_info, target_sim_info) -> bool:
    """
    Determines if actor genuinely knows target (friends, family, acquaintances, romance).
    Returns False for unintroduced strangers, service NPCs, or walk-bys who haven't met.
    """
    if actor_sim_info is None or target_sim_info is None:
        return False

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    target_id = getattr(target_sim_info, "sim_id", 0)
    if not actor_id or not target_id or actor_id == target_id:
        return False

    # 1. Household members (family, roommates in the same house) always know each other
    try:
        actor_household = getattr(actor_sim_info, "household", None)
        target_household = getattr(target_sim_info, "household", None)
        if actor_household is not None and target_household is not None and actor_household == target_household:
            return True
    except Exception:
        pass

    # 2. Check relationship description via get_relationship_between_sims
    rel_desc = _get_relationship_description(actor_sim_info, target_sim_info).lower()
    if "незнаком" in rel_desc or "не знаком" in rel_desc or "stranger" in rel_desc or "not acquainted" in rel_desc:
        return False

    # 3. Check relationship tracker bits
    rel_tracker = getattr(actor_sim_info, "relationship_tracker", None)
    if rel_tracker is not None:
        try:
            bits = rel_tracker.get_all_bits(target_id)
            if bits:
                bits_names = [getattr(b, "__name__", str(b)).lower() for b in bits]
                bits_str = " ".join(bits_names)
                known_keywords = [
                    "has_met", "acquaintance", "friend", "love", "romance", "family",
                    "mother", "father", "son", "daughter", "brother", "sister",
                    "spouse", "husband", "wife", "coworker", "introduced", "significant_other",
                    "neighbor", "club", "dating", "sweetheart", "nemesis", "enemy", "disliked",
                    "despised", "rel_bit"
                ]
                if any(k in bits_str for k in known_keywords):
                    return True
                if len(bits) > 0:
                    return True
        except Exception:
            pass

    # 4. Check relationship service directly
    try:
        if services is not None:
            rel_svc = services.relationship_service()
            if rel_svc is not None and hasattr(rel_svc, "has_relationship"):
                if rel_svc.has_relationship(actor_id, target_id):
                    rel = rel_svc.get_relationship(actor_id, target_id)
                    if rel is not None:
                        rel_bits = rel.get_bits(actor_id) if hasattr(rel, "get_bits") else ()
                        if rel_bits:
                            return True
    except Exception:
        pass

    # 5. Positive relationship description match
    positive_keywords = ["друг", "подруг", "муж", "жена", "мать", "отец", "брат", "сестр", "коллег", "знаком", "возлюблен", "парень", "девушка"]
    return any(k in rel_desc for k in positive_keywords)


def get_available_contacts(actor_sim_info, include_strangers: bool = False) -> List[Any]:
    """
    Returns a list of all valid contact Sims in the world:
    By default (include_strangers=False): only returns Sims that the active Sim genuinely knows.
    Skips active Sim, pets, and non-playable age groups (babies, infants, toddlers).
    """
    contacts = []
    if services is None or actor_sim_info is None:
        return contacts

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return contacts

    for tgt in sim_info_manager.get_all():
        tgt_id = getattr(tgt, "sim_id", 0)
        if not tgt_id or tgt_id == actor_id:
            continue
        if is_sim_an_animal(tgt):
            continue
        if getattr(tgt, "is_pet", False):
            continue

        # Skip non-playable age groups (babies, infants, toddlers)
        age_enum = getattr(tgt, "age", None)
        age_name = getattr(age_enum, "name", "").upper() if age_enum else ""
        if age_name in ("BABY", "INFANT", "TODDLER"):
            continue

        if not include_strangers:
            if not is_sim_truly_known(actor_sim_info, tgt):
                continue

        contacts.append(tgt)

    return contacts


def show_lonely_dialog(actor_sim_info):
    """
    Displays a dialog informing the player that their Sim currently has no acquaintances (they are alone).
    """
    is_en = _is_en()
    actor_name = get_recipient_display_name(actor_sim_info)
    title = "AI Messenger" if is_en else "AI Мессенджер"
    if is_en:
        text = (
            f"Character {actor_name} does not know anyone yet.\n\n"
            f"You are lonely...\n\n"
            f"Introduce yourself to other Sims around town or chat with neighbors "
            f"to add them to your messenger contacts list!"
        )
    else:
        text = (
            f"У персонажа {actor_name} пока нет знакомых.\n\n"
            f"Вы одиноки...\n\n"
            f"Познакомьтесь с другими персонажами в городе или пообщайтесь с соседями, "
            f"чтобы добавить их в список контактов мессенджера!"
        )
    if UiDialogOk is not None:
        try:
            loc_title = _get_loc_text(title)
            loc_text = _get_loc_text(text)
            dialog = UiDialogOk.TunableFactory().default(
                actor_sim_info,
                text=lambda *_: loc_text,
                title=lambda *_: loc_title,
            )
            dialog.show_dialog()
            return
        except Exception as e:
            log_exception("Failed to show lonely UiDialogOk", e)

    # Fallback to in-game notification
    show_chat_notification(title, text, sim_info=actor_sim_info, is_error=False)


def show_contact_picker(actor_sim_info, on_contact_selected: Callable[[Any], None]):
    """
    Displays the native Sims 4 Sim Picker dialog (grid with 3D portraits,
    names, relationship bars, and category filter tabs), matching MCCC.
    Only shows Sims that the actor genuinely knows.
    If no known Sims exist, informs the player that they are lonely.
    """
    contacts = get_available_contacts(actor_sim_info, include_strangers=False)
    if not contacts:
        show_lonely_dialog(actor_sim_info)
        return

    if ChatSimPicker is not None and SimPickerRow is not None:
        _render_sim_picker_dialog(actor_sim_info, on_contact_selected, contacts=contacts)
    elif ChatActionPicker is not None and BasePickerRow is not None:
        _render_action_picker_fallback(actor_sim_info, on_contact_selected, contacts=contacts)
    else:
        log("No picker available in this environment.", level="ERROR")


def _render_sim_picker_dialog(actor_sim_info, on_contact_selected: Callable[[Any], None], contacts: Optional[List[Any]] = None):
    """
    Renders native UiSimPicker (3-column grid with avatars, relationship bars, and filter tabs).
    """
    try:
        is_en = _is_en()
        actor_name = get_recipient_display_name(actor_sim_info)
        title = "AI Messenger: Select Contact" if is_en else "AI Мессенджер: Выбор собеседника"
        text = f"Select a character to message with {actor_name}:" if is_en else f"Выберите персонажа для переписки с {actor_name}:"

        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)

        factory = ChatSimPicker.TunableFactory()
        dialog = factory.default(
            actor_sim_info,
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

        if contacts is None:
            contacts = get_available_contacts(actor_sim_info, include_strangers=False)

        if not contacts:
            show_lonely_dialog(actor_sim_info)
            return

        # Sort contacts: highest relationship first, then alphabetically by name
        def _sim_sort_key(tgt):
            rel_tracker = getattr(actor_sim_info, "relationship_tracker", None)
            score = 0.0
            if rel_tracker is not None:
                try:
                    score = rel_tracker.get_relationship_score(tgt.sim_id)
                except Exception:
                    pass
            first = getattr(tgt, "first_name", "") or ""
            last = getattr(tgt, "last_name", "") or ""
            name = f"{first} {last}".strip()
            return (-score, name)

        contacts.sort(key=_sim_sort_key)

        sim_by_id = {}
        for tgt in contacts:
            tgt_id = getattr(tgt, "sim_id", None)
            if not tgt_id:
                continue
            sim_by_id[tgt_id] = tgt
            row = SimPickerRow(
                sim_id=tgt_id,
                tag=tgt,
                select_default=False,
            )
            dialog.add_row(row)

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
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
                            for r in getattr(dlg, "picker_rows", []):
                                if getattr(r, "option_id", None) == pid:
                                    s_id = getattr(r, "sim_id", None)
                                    if s_id in sim_by_id:
                                        selected_sim = sim_by_id[s_id]
                                        break
                                    elif getattr(r, "tag", None) is not None:
                                        selected_sim = r.tag
                                        break

                    if selected_sim is None and hasattr(dlg, "get_result_rows"):
                        for r in dlg.get_result_rows():
                            s_id = getattr(r, "sim_id", None)
                            if s_id in sim_by_id:
                                selected_sim = sim_by_id[s_id]
                                break
                            elif getattr(r, "tag", None) is not None:
                                selected_sim = r.tag
                                break

                    if selected_sim is not None and callable(on_contact_selected):
                        on_contact_selected(selected_sim)
                else:
                    log("User closed/canceled SimPicker dialog")
            except Exception as e:
                log_exception("Error in SimPicker _on_response", e)

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to render SimPicker dialog", e)


def _render_action_picker_fallback(owner_sim_info, on_selected, contacts: Optional[List[Any]] = None):
    """Fallback text list picker if UiSimPicker is somehow unavailable."""
    try:
        is_en = _is_en()
        actor_name = get_recipient_display_name(owner_sim_info)
        title = "AI Messenger: Select Contact" if is_en else "AI Мессенджер: Выбор собеседника"
        text = f"Select a character to message with {actor_name}:" if is_en else f"Выберите персонажа для переписки с {actor_name}:"

        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)

        factory = ChatActionPicker.TunableFactory()
        dialog = factory.default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        dialog.min_selectable = 1
        dialog.max_selectable = 1
        dialog.force_done_button = False

        if contacts is None:
            contacts = get_available_contacts(owner_sim_info, include_strangers=False)

        if not contacts:
            show_lonely_dialog(owner_sim_info)
            return

        tag_by_option_id = {}

        for idx, tgt in enumerate(contacts):
            option_id = idx + 1
            tgt_name = get_recipient_display_name(tgt)
            rel_desc = _get_relationship_description(owner_sim_info, tgt)
            tag_by_option_id[option_id] = tgt

            rel_label = "Relationship" if _is_en() else "Отношения"
            row = BasePickerRow(
                option_id=option_id,
                name=_get_loc_text(tgt_name),
                row_description=_get_loc_text(f"{rel_label}: {rel_desc}"),
                tag=tgt,
                is_selected=False,
            )
            dialog.add_row(row)

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    selected_tag = None
                    results = dlg.get_result_tags()
                    if results:
                        selected_tag = results[0]

                    if selected_tag is None and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in tag_by_option_id:
                                selected_tag = tag_by_option_id[pid]
                                break

                    if selected_tag is not None and callable(on_selected):
                        on_selected(selected_tag)
            except Exception as ex:
                log_exception("Error in fallback picker response", ex)

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to render fallback picker dialog", e)


def _wrap_message_text(text: str, max_chars: int = 36) -> List[str]:
    """Wraps message text into clean lines without splitting words."""
    words = str(text).split()
    if not words:
        return [""]
    lines = []
    curr_line = []
    curr_len = 0
    for w in words:
        w_len = len(w)
        space_len = 1 if curr_line else 0
        if curr_len + w_len + space_len <= max_chars:
            curr_line.append(w)
            curr_len += w_len + space_len
        else:
            if curr_line:
                lines.append(" ".join(curr_line))
            curr_line = [w]
            curr_len = w_len
    if curr_line:
        lines.append(" ".join(curr_line))
    return lines


def format_incoming_bubble(sender_name: str, text: str, time_str: str) -> str:
    """Formats an incoming message (strictly left-aligned for recipient / собеседник)."""
    time_tag = f" <font color=\"#7F8C8D\">[{time_str}]</font>" if time_str else ""
    clean_text = str(text).strip().replace("\n", "<br>")
    return f"<p align=\"left\"><b>{sender_name}</b>{time_tag}<br>{clean_text}</p>"


def format_outgoing_bubble(text: str, time_str: str) -> str:
    """Formats an outgoing message (strictly right-aligned for player Sim / You / Вы)."""
    time_tag = f"<font color=\"#7F8C8D\">[{time_str}]</font> " if time_str else ""
    clean_text = str(text).strip().replace("\n", "<br>")
    you_label = "You" if _is_en() else "Вы"
    return f"<p align=\"right\">{time_tag}<b>{you_label}</b><br>{clean_text}</p>"


def build_messenger_chat_body(
    actor_name: str,
    recipient_name: str,
    history: List[Dict[str, Any]],
    max_msgs: int = 8,
    is_typing: bool = False,
    is_online: bool = True,
    work_school_status: Optional[Dict[str, Any]] = None,
    actor_id: int = 0,
) -> str:
    """Constructs a complete messenger thread with responsive left/right alignment, day dividers and timeline."""
    is_en = _is_en()
    if work_school_status and work_school_status.get("is_busy"):
        act_type = work_school_status.get("activity_type")
        c_name = work_school_status.get("career_name", "")
        if act_type == "school":
            status_tag = '<font color="#3498DB"><b>At School</b></font>' if is_en else '<font color="#3498DB"><b>На учёбе</b></font>'
            status_note = (f"currently at school ({c_name})" if c_name else "currently at school") if is_en else (f"сейчас на учёбе ({c_name})" if c_name else "сейчас на учёбе")
        else:
            status_tag = '<font color="#F39C12"><b>At Work</b></font>' if is_en else '<font color="#F39C12"><b>На работе</b></font>'
            status_note = (f"currently at work ({c_name})" if c_name else "currently at work") if is_en else (f"сейчас на работе ({c_name})" if c_name else "сейчас на работе")
    elif is_online:
        status_tag = '<font color="#27AE60"><b>Online</b></font>' if is_en else '<font color="#27AE60"><b>В сети</b></font>'
        status_note = "currently online" if is_en else "сейчас в сети"
    else:
        status_tag = '<font color="#7F8C8D"><b>Offline</b></font>' if is_en else '<font color="#7F8C8D"><b>Не в сети</b></font>'
        status_note = "currently offline" if is_en else "сейчас не в сети"

    header = f"<p align=\"center\"><b>{recipient_name}</b>, {status_tag}</p>"

    if not history and not is_typing:
        today_lbl = "——— Today ———" if is_en else "——— Сегодня ———"
        empty_msg = (
            f"Chat with {recipient_name} is open ({status_note}).<br>Send your first message to start the conversation!"
            if is_en else
            f"Чат с {recipient_name} открыт ({status_note}).<br>Напишите первое сообщение, чтобы начать диалог!"
        )
        empty_box = (
            f"<p align=\"center\"><font color=\"#7F8C8D\">{today_lbl}</font><br>"
            f"<font color=\"#7F8C8D\">{empty_msg}</font></p>"
        )
        return f"{header}\n{empty_box}\n<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>"

    from ai_social_pc.chat_manager import get_current_sim_absolute_days, get_relative_day_label
    cur_day = get_current_sim_absolute_days()

    bubbles = []
    last_day_label = None

    for msg in history[-max_msgs:]:
        s = msg.get("sender", "")
        s_id = msg.get("sender_id", 0)
        t = msg.get("text", "")
        m_time = msg.get("time", "")
        m_day = msg.get("abs_day", cur_day)
        m_dow = msg.get("dow", "")
        day_lbl = get_relative_day_label(m_day, cur_day, m_dow)

        if day_lbl != last_day_label:
            bubbles.append(f"<p align=\"center\"><font color=\"#7F8C8D\">——— {day_lbl} ———</font></p>")
            last_day_label = day_lbl

        is_outgoing = False
        if s_id and actor_id and s_id == actor_id:
            is_outgoing = True
        elif s == actor_name:
            is_outgoing = True
        elif s in ("Вы", "You") and not s_id:
            is_outgoing = True

        if is_outgoing:
            bubbles.append(format_outgoing_bubble(t, m_time))
        else:
            bubbles.append(format_incoming_bubble(s or recipient_name, t, m_time))

    if is_typing:
        typing_msg = f"{recipient_name} is typing . . ." if is_en else f"{recipient_name} печатает сообщение . . ."
        typing_bubble = f"<p align=\"left\"><font color=\"#7F8C8D\"><i>{typing_msg}</i></font></p>"
        bubbles.append(typing_bubble)

    chat_body = "\n".join(bubbles)
    divider = "<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>"
    return f"{header}\n{chat_body}\n{divider}"


def show_message_input(
    actor_sim_info,
    recipient_info,
    on_submit: Callable[[str], None],
    default_text: str = "",
    is_typing: bool = False,
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Renders text input dialog styled like a real messenger:
    Incoming messages on the left, outgoing messages on the right.
    Returns the dialog instance so it can be canceled/refreshed automatically.
    """
    if UiDialogTextInputOkCancel is None:
        log("UiDialogTextInputOkCancel is not available.", level="ERROR")
        return None

    recipient_name = get_recipient_display_name(recipient_info)
    actor_name = get_recipient_display_name(actor_sim_info)
    actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
    recipient_id = getattr(recipient_info, "sim_id", 0) if not isinstance(recipient_info, dict) else recipient_info.get("id", -1)

    is_en = _is_en()
    title = "AI Messenger" if is_en else "Мессенджер"
    is_online = is_sim_online(recipient_info)

    from ai_social_pc.chat_manager import get_sim_work_or_school_status
    work_school_status = get_sim_work_or_school_status(recipient_info)

    history = get_session_history(actor_id, recipient_id)
    chat_body = build_messenger_chat_body(
        actor_name,
        recipient_name,
        history,
        max_msgs=6,
        is_typing=is_typing,
        is_online=is_online,
        work_school_status=work_school_status,
        actor_id=actor_id,
    )

    if is_typing:
        prompt_line = (
            "<p align=\"left\"><font color=\"#7F8C8D\"><i>Waiting for reply... (dialog will update automatically)</i></font></p>"
            if is_en else
            "<p align=\"left\"><font color=\"#7F8C8D\"><i>Ожидание ответа... (диалог обновится автоматически)</i></font></p>"
        )
    elif not is_online:
        prompt_line = (
            "<p align=\"left\"><font color=\"#7F8C8D\">Your reply (Sim is asleep / offline  |  OK — send  |  Cancel — close):</font></p>"
            if is_en else
            "<p align=\"left\"><font color=\"#7F8C8D\">Ваш ответ (Собеседник спит / не в сети  |  ОК — отправить  |  Отмена — закрыть):</font></p>"
        )
    else:
        prompt_line = (
            "<p align=\"left\"><font color=\"#555555\">Your reply (OK — send  |  Cancel — close):</font></p>"
            if is_en else
            "<p align=\"left\"><font color=\"#555555\">Ваш ответ (ОК — отправить  |  Отмена — закрыть):</font></p>"
        )

    text = f"{chat_body}\n{prompt_line}"

    try:
        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)
        loc_init = _get_loc_text(default_text or "")

        factory = UiDialogTextInputOkCancel.TunableFactory(
            text_inputs=("chat_msg_input",)
        )
        dialog = factory.default(
            actor_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        if hasattr(dialog, "text_inputs"):
            tuning = getattr(dialog.text_inputs, "chat_msg_input", None)
            if tuning is not None:
                if hasattr(tuning, "length_restriction") and hasattr(tuning.length_restriction, "max_length"):
                    tuning.length_restriction.max_length = 500
                if hasattr(tuning, "height"):
                    tuning.height = 65

        text_input_overrides = {
            "chat_msg_input": lambda *_, **__: loc_init
        }

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    responses = getattr(dlg, "text_input_responses", {})
                    entered = str(responses.get("chat_msg_input", "")).strip()
                    if entered and callable(on_submit):
                        on_submit(entered)
                    elif not entered:
                        # User clicked OK or pressed Enter with empty text:
                        # Keep the messenger window open (do nothing / do not close)
                        if callable(on_submit):
                            on_submit("")
                        else:
                            show_message_input(
                                actor_sim_info,
                                recipient_info,
                                on_submit=on_submit,
                                default_text="",
                                is_typing=is_typing,
                                on_cancel=on_cancel,
                            )
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as ex:
                log_exception("Error in message input response", ex)

        dialog.show_dialog(on_response=_on_response, text_input_overrides=text_input_overrides)
        return dialog
    except Exception as e:
        log_exception("Failed to render message input dialog", e)
        return None


def show_chat_conversation_dialog(
    actor_sim_info,
    recipient_info,
    latest_reply: str,
    on_reply_callback: Callable[[], None],
):
    """
    Displays the conversation thread dialog styled like a real messenger
    with instant 'Reply' button.
    """
    recipient_name = get_recipient_display_name(recipient_info)
    actor_name = get_recipient_display_name(actor_sim_info)
    actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
    recipient_id = getattr(recipient_info, "sim_id", 0) if not isinstance(recipient_info, dict) else recipient_info.get("id", -1)

    # 1. Show notification popup with recipient portrait
    show_chat_notification(
        title=f"{recipient_name}",
        text=f"«{latest_reply}»",
        sim_info=recipient_info if not isinstance(recipient_info, dict) else None,
        is_error=False,
    )

    # 2. Format conversation thread cleanly
    from ai_social_pc.chat_manager import get_sim_work_or_school_status
    work_school_status = get_sim_work_or_school_status(recipient_info)
    is_online = is_sim_online(recipient_info)
    history = get_session_history(actor_id, recipient_id)
    chat_body = build_messenger_chat_body(
        actor_name,
        recipient_name,
        history,
        max_msgs=8,
        is_online=is_online,
        work_school_status=work_school_status,
        actor_id=actor_id,
    )

    is_en = _is_en()
    title = "AI Messenger" if is_en else "Мессенджер"
    sel_action = "Select an action:" if is_en else "Выберите действие:"
    text = (
        f"{chat_body}\n"
        f"<p align=\"left\"><font color=\"#555555\">{sel_action}</font></p>"
    )

    if is_en:
        rows = [
            (
                "[+] Reply...",
                f"Send another message to {recipient_name}",
                "reply",
            ),
            (
                "[X] Clear Chat History",
                "Erase message history and start with a clean slate",
                "clear",
            ),
            (
                "[<<] Close Chat",
                "Close messenger and step away from the computer",
                "close",
            ),
        ]
    else:
        rows = [
            (
                "[+] Написать ответ...",
                f"Отправить следующее сообщение для {recipient_name}",
                "reply",
            ),
            (
                "[X] Очистить историю диалога",
                "Стереть историю переписки и начать с чистого листа",
                "clear",
            ),
            (
                "[<<] Завершить переписку",
                "Закрыть мессенджер и отойти от компьютера",
                "close",
            ),
        ]

    def _on_select(action):
        if action == "reply":
            if callable(on_reply_callback):
                on_reply_callback()
        elif action == "clear":
            clear_session_history(actor_id, recipient_id)
            clr_title = "AI Messenger" if is_en else "AI Мессенджер"
            clr_msg = f"Chat history with {recipient_name} cleared." if is_en else f"История диалога с {recipient_name} очищена."
            show_chat_notification(
                clr_title,
                clr_msg,
                sim_info=actor_sim_info,
            )
        elif action == "close":
            log(f"Chat closed between {actor_name} and {recipient_name}")

    show_action_menu(actor_sim_info, title, text, rows, _on_select)


# =====================================================================
# GROUP CHAT AND MENU SYSTEM (DRY PLAIN TEXT, NO EMOJIS)
# =====================================================================

def show_action_menu(
    owner_sim_info,
    title: str,
    text: str,
    rows_data: List[Tuple[str, str, Any]],
    on_selected: Callable[[Any], None],
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Displays an immediate-choice action menu using ChatActionPicker (UiItemPicker).
    rows_data: list of (name, description, tag)
    on_selected: callback(selected_tag)
    """
    if ChatActionPicker is None or BasePickerRow is None:
        log("ChatActionPicker is not available.", level="ERROR")
        return

    try:
        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)

        factory = ChatActionPicker.TunableFactory()
        dialog = factory.default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        dialog.min_selectable = 1
        dialog.max_selectable = 1
        dialog.force_done_button = False

        tag_by_option_id = {}
        for idx, item in enumerate(rows_data):
            option_id = idx + 1
            r_name = item[0]
            r_desc = item[1] if len(item) > 1 else ""
            r_tag = item[2] if len(item) > 2 else None
            tag_by_option_id[option_id] = r_tag

            row = BasePickerRow(
                option_id=option_id,
                name=_get_loc_text(r_name),
                row_description=_get_loc_text(r_desc) if r_desc else None,
                tag=r_tag,
                is_selected=False,
            )
            dialog.add_row(row)

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    selected_tag = None
                    results = dlg.get_result_tags()
                    if results:
                        selected_tag = results[0]

                    if selected_tag is None and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in tag_by_option_id:
                                selected_tag = tag_by_option_id[pid]
                                break

                    if selected_tag is not None and callable(on_selected):
                        on_selected(selected_tag)
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as e:
                log_exception("Error in show_action_menu _on_response", e)

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to render action menu", e)


def show_multi_contact_picker(
    actor_sim_info,
    title: str,
    text: str,
    on_selected: Callable[[List[Any]], None],
    preselected_sim_ids: Optional[List[int]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Renders native UiSimPicker with multi-select enabled.
    Allows selecting multiple known Sims.
    """
    if ChatMultiSimPicker is None or SimPickerRow is None:
        log("ChatMultiSimPicker is not available.", level="ERROR")
        return

    try:
        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)

        factory = ChatMultiSimPicker.TunableFactory()
        dialog = factory.default(
            actor_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        dialog.min_selectable = 1
        dialog.max_selectable = 15
        dialog.column_count = 3
        dialog.should_show_names = True
        dialog.display_filter = True
        if SimPickerCellType is not None:
            dialog.cell_type = SimPickerCellType.DEFAULT

        contacts = get_available_contacts(actor_sim_info, include_strangers=False)
        if not contacts:
            show_lonely_dialog(actor_sim_info)
            if callable(on_cancel):
                on_cancel()
            return

        preselected_set = set(preselected_sim_ids or [])

        sim_by_id = {}
        for tgt in contacts:
            tgt_id = getattr(tgt, "sim_id", None)
            if not tgt_id:
                continue
            sim_by_id[tgt_id] = tgt
            is_pre = (tgt_id in preselected_set)
            row = SimPickerRow(
                sim_id=tgt_id,
                tag=tgt,
                select_default=is_pre,
            )
            dialog.add_row(row)

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    selected_sims = []
                    results = dlg.get_result_tags()
                    if results:
                        selected_sims = [r for r in results if r is not None]

                    if not selected_sims and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in sim_by_id:
                                selected_sims.append(sim_by_id[pid])

                    if not selected_sims and hasattr(dlg, "get_result_rows"):
                        for r in dlg.get_result_rows():
                            s_id = getattr(r, "sim_id", None)
                            if s_id in sim_by_id:
                                selected_sims.append(sim_by_id[s_id])
                            elif getattr(r, "tag", None) is not None:
                                selected_sims.append(r.tag)

                    if selected_sims and callable(on_selected):
                        on_selected(selected_sims)
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as e:
                log_exception("Error in show_multi_contact_picker _on_response", e)

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to render multi contact picker", e)


def show_simple_text_input(
    owner_sim_info,
    title: str,
    text: str,
    initial_value: str = "",
    on_submit: Optional[Callable[[str], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
    allow_empty: bool = False,
    max_length: int = 60,
):
    """
    Prompts player for a single line of text (e.g. group name, group topic).
    """
    if UiDialogTextInputOkCancel is None:
        log("UiDialogTextInputOkCancel is not available.", level="ERROR")
        return None

    try:
        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)
        loc_init = _get_loc_text(initial_value or "")

        factory = UiDialogTextInputOkCancel.TunableFactory(
            text_inputs=("simple_text_input",)
        )
        dialog = factory.default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        if hasattr(dialog, "text_inputs"):
            tuning = getattr(dialog.text_inputs, "simple_text_input", None)
            if tuning is not None:
                if hasattr(tuning, "length_restriction") and hasattr(tuning.length_restriction, "max_length"):
                    tuning.length_restriction.max_length = max_length
                if hasattr(tuning, "height"):
                    tuning.height = 35

        text_input_overrides = {
            "simple_text_input": lambda *_, **__: loc_init
        }

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    responses = getattr(dlg, "text_input_responses", {})
                    entered = str(responses.get("simple_text_input", "")).strip()
                    if (entered or allow_empty) and callable(on_submit):
                        on_submit(entered)
                    elif callable(on_cancel):
                        on_cancel()
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as ex:
                log_exception("Error in simple text input response", ex)

        dialog.show_dialog(on_response=_on_response, text_input_overrides=text_input_overrides)
        return dialog
    except Exception as e:
        log_exception("Failed to render simple text input dialog", e)
        return None


def show_messenger_root_menu(
    actor_sim_info,
    on_direct_chat: Callable[[], None],
    on_groups: Callable[[], None],
):
    """
    Renders the root launcher menu with two plain choices (no emojis):
    1. Личные сообщения
    2. Группы
    """
    is_en = _is_en()
    if is_en:
        rows = [
            ("Direct Messages", "Private one-on-one conversation with a selected Sim", "direct"),
            ("Group Chats", "Group conversations with multiple participants", "groups"),
        ]
        title = "AI Messenger"
        text = "Select a category:"
    else:
        rows = [
            ("Личные сообщения", "Переписка один на один с выбранным персонажем", "direct"),
            ("Группы", "Общие чаты и беседы с несколькими участниками", "groups"),
        ]
        title = "Мессенджер"
        text = "Выберите раздел:"

    def _on_pick(tag):
        if tag == "direct" and callable(on_direct_chat):
            on_direct_chat()
        elif tag == "groups" and callable(on_groups):
            on_groups()

    show_action_menu(
        owner_sim_info=actor_sim_info,
        title=title,
        text=text,
        rows_data=rows,
        on_selected=_on_pick,
    )


def show_groups_menu(
    actor_sim_info,
    on_select_group: Callable[[Dict[str, Any]], None],
    on_create_group: Callable[[], None],
    on_edit_groups: Callable[[], None],
    on_back: Callable[[], None],
):
    """
    Renders group chat menu (plain text, no emojis):
    1. Создать группу
    2. Изменить существующую
    3+. [Created groups]
    Last. Назад в главное меню
    """
    from ai_social_pc.group_manager import get_groups_for_sim
    actor_id = getattr(actor_sim_info, "sim_id", 0)
    groups = get_groups_for_sim(actor_id)

    sim_mgr = services.sim_info_manager() if services is not None else None

    is_en = _is_en()
    if is_en:
        rows = [
            ("Create New Group", "Create a new group chat and invite members", "create"),
            ("Edit Existing Group", "Rename, change members, or delete a group", "edit"),
        ]
    else:
        rows = [
            ("Создать группу", "Создать новый групповой чат и пригласить участников", "create"),
            ("Изменить существующую", "Переименовать, изменить состав или удалить группу", "edit"),
        ]

    for grp in groups:
        def_grp_name = "Group" if is_en else "Группа"
        g_name = grp.get("name", def_grp_name)
        topic = (grp.get("topic") or "").strip()
        m_ids = grp.get("member_ids", [])
        m_names = []
        for mid in m_ids:
            if mid == actor_id:
                continue
            if sim_mgr:
                s_info = sim_mgr.get(mid)
                if s_info:
                    m_names.append(get_recipient_display_name(s_info))
                    continue
            m_names.append(f"Sim_{mid}" if is_en else f"Сим_{mid}")

        preview = ", ".join(m_names[:3])
        if len(m_names) > 3:
            extra = f" and {len(m_names) - 3} more" if is_en else f" и ещё {len(m_names) - 3}"
            preview += extra

        desc_parts = []
        if topic:
            desc_parts.append(f"Topic: «{topic}»" if is_en else f"Смысл: «{topic}»")
        if preview:
            desc_parts.append(f"Members: {preview}" if is_en else f"Участники: {preview}")
        else:
            desc_parts.append(f"{len(m_ids)} members" if is_en else f"{len(m_ids)} участников")
        desc = " • ".join(desc_parts)

        mem_abbr = "mbrs." if is_en else "уч."
        rows.append((f"{g_name} ({len(m_ids)} {mem_abbr})", desc, ("open", grp)))

    back_lbl = "<< Back to Main Menu" if is_en else "Назад в главное меню"
    back_dsc = "Return to messenger section selection" if is_en else "Вернуться к выбору раздела мессенджера"
    rows.append((back_lbl, back_dsc, "back"))

    def _on_pick(tag):
        if tag == "create" and callable(on_create_group):
            on_create_group()
        elif tag == "edit" and callable(on_edit_groups):
            on_edit_groups()
        elif tag == "back" and callable(on_back):
            on_back()
        elif isinstance(tag, tuple) and tag[0] == "open" and callable(on_select_group):
            on_select_group(tag[1])

    title = "Group Chats" if is_en else "Групповые чаты"
    text = "Select an action or a group to open:" if is_en else "Выберите действие или группу для общения:"
    show_action_menu(
        owner_sim_info=actor_sim_info,
        title=title,
        text=text,
        rows_data=rows,
        on_selected=_on_pick,
    )


def prompt_create_group(
    actor_sim_info,
    on_group_created: Callable[[Dict[str, Any]], None],
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Three-step group creation flow:
    Step 1: Enter group name.
    Step 2: Enter group topic/meaning (optional).
    Step 3: Pick members from known contacts.
    """
    def _on_name_entered(entered_name):
        clean_name = entered_name.strip()
        if not clean_name:
            if callable(on_cancel):
                on_cancel()
            return

        def _on_topic_entered(entered_topic):
            clean_topic = (entered_topic or "").strip()

            def _on_members_picked(selected_sims):
                m_ids = [getattr(s, "sim_id", 0) for s in selected_sims if getattr(s, "sim_id", 0)]
                actor_id = getattr(actor_sim_info, "sim_id", 0)
                if actor_id and actor_id not in m_ids:
                    m_ids.append(actor_id)

                from ai_social_pc.group_manager import create_group
                new_grp = create_group(clean_name, actor_id, m_ids, topic=clean_topic)
                is_en = _is_en()
                c_title = "Group Created" if is_en else "Группа создана"
                c_msg = f"Group '{clean_name}' created ({len(new_grp['member_ids'])} members)." if is_en else f"Группа '{clean_name}' создана ({len(new_grp['member_ids'])} участников)."
                show_chat_notification(
                    title=c_title,
                    text=c_msg,
                    sim_info=actor_sim_info,
                )
                if callable(on_group_created):
                    on_group_created(new_grp)

            is_en_members = _is_en()
            m_title = "Select Members" if is_en_members else "Выбор участников"
            m_text = f"Select participants for group '{clean_name}':" if is_en_members else f"Выберите участников для группы '{clean_name}':"
            show_multi_contact_picker(
                actor_sim_info=actor_sim_info,
                title=m_title,
                text=m_text,
                on_selected=_on_members_picked,
                on_cancel=on_cancel,
            )

        is_en_top = _is_en()
        t_title = "Group Topic (Optional)" if is_en_top else "Смысл группы (необязательно)"
        t_text = f"Describe the topic or purpose of group '{clean_name}' (optional, can be left blank):" if is_en_top else f"Опишите тему или цель группы '{clean_name}' (необязательно, можно оставить пустым):"
        show_simple_text_input(
            owner_sim_info=actor_sim_info,
            title=t_title,
            text=t_text,
            initial_value="",
            allow_empty=True,
            max_length=200,
            on_submit=_on_topic_entered,
            on_cancel=lambda: _on_topic_entered(""),
        )

    is_en_main = _is_en()
    main_title = "Create Group" if is_en_main else "Создание группы"
    main_text = "Enter a name for the new group:" if is_en_main else "Введите название для новой группы:"
    show_simple_text_input(
        owner_sim_info=actor_sim_info,
        title=main_title,
        text=main_text,
        initial_value="",
        on_submit=_on_name_entered,
        on_cancel=on_cancel,
    )


def prompt_edit_groups(
    actor_sim_info,
    on_done: Callable[[], None],
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Group modification flow:
    1. Select which group to edit.
    2. Choose action: Rename, Update Topic, Update Members, Clear History, Delete.
    """
    from ai_social_pc.group_manager import (
        get_groups_for_sim,
        update_group_name,
        update_group_topic,
        get_group_topic,
        update_group_members,
        clear_group_history,
        delete_group,
    )

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    groups = get_groups_for_sim(actor_id)

    is_en_eg = _is_en()
    if not groups:
        show_chat_notification(
            title="Groups" if is_en_eg else "Группы",
            text="You don't have any groups to edit yet." if is_en_eg else "У вас пока нет созданных групп для изменения.",
            sim_info=actor_sim_info,
        )
        if callable(on_done):
            on_done()
        return

    sim_mgr = services.sim_info_manager() if services is not None else None

    # Step 1: Select group to edit
    rows = []
    for grp in groups:
        g_name = grp.get("name", "Group" if is_en_eg else "Группа")
        topic = (grp.get("topic") or "").strip()
        m_ids = grp.get("member_ids", [])
        m_count_str = f"{len(m_ids)} mbrs." if is_en_eg else f"{len(m_ids)} уч."
        desc = m_count_str
        if topic:
            topic_prefix = " • Topic: «{}»" if is_en_eg else " • Смысл: «{}»"
            desc += topic_prefix.format(topic)
        rows.append((f"{g_name} ({m_count_str})", desc, grp))

    back_lbl = "<< Back to Groups List" if is_en_eg else "Назад к списку групп"
    back_dsc = "Return to previous list" if is_en_eg else "Вернуться назад"
    rows.append((back_lbl, back_dsc, "back"))

    def _on_group_picked(picked_item):
        if picked_item == "back":
            if callable(on_done):
                on_done()
            return

        is_en = _is_en()
        grp = picked_item
        g_id = grp.get("id")
        def_grp = "Group" if is_en else "Группа"
        g_name = grp.get("name", def_grp)
        g_topic = (grp.get("topic") or "").strip() or get_group_topic(g_id)

        # Step 2: Select action for this group
        if is_en:
            topic_desc = f"Current topic: «{g_topic}»" if g_topic else "Set topic/description for AI"
            action_rows = [
                ("Rename Group", "Set a new name for this group", "rename"),
                ("Change Group Topic", topic_desc, "topic"),
                ("Change Members", "Add or remove members from this group", "members"),
                ("Clear Message History", "Erase all messages in this group", "clear"),
                ("Delete Group", "Permanently delete this group", "delete"),
                ("<< Back to Group List", "Return to group list", "back"),
            ]
        else:
            topic_desc = f"Текущий смысл: «{g_topic}»" if g_topic else "Задать смысл/описание группы для ИИ"
            action_rows = [
                ("Переименовать группу", "Задать новое название для этой группы", "rename"),
                ("Изменить смысл группы", topic_desc, "topic"),
                ("Изменить состав участников", "Добавить или удалить участников группы", "members"),
                ("Очистить историю сообщений", "Стереть все сообщения в этой группе", "clear"),
                ("Удалить группу", "Полностью удалить эту группу", "delete"),
                ("Назад к выбору группы", "Вернуться к списку групп", "back"),
            ]

        def _on_action_picked(action_tag):
            if action_tag == "back":
                prompt_edit_groups(actor_sim_info, on_done, on_cancel)
            elif action_tag == "rename":
                def _on_new_name(new_name):
                    update_group_name(g_id, new_name)
                    r_title = "Group Updated" if is_en else "Группа обновлена"
                    r_msg = f"Group renamed to '{new_name}'." if is_en else f"Группа переименована в '{new_name}'."
                    show_chat_notification(
                        title=r_title,
                        text=r_msg,
                        sim_info=actor_sim_info,
                    )
                    if callable(on_done):
                        on_done()

                rn_title = "Rename Group" if is_en else "Переименование"
                rn_text = f"Enter a new name for group '{g_name}':" if is_en else f"Введите новое название для группы '{g_name}':"
                show_simple_text_input(
                    owner_sim_info=actor_sim_info,
                    title=rn_title,
                    text=rn_text,
                    initial_value=g_name,
                    on_submit=_on_new_name,
                    on_cancel=lambda: prompt_edit_groups(actor_sim_info, on_done, on_cancel),
                )
            elif action_tag == "topic":
                def _on_new_topic(new_topic):
                    clean_t = (new_topic or "").strip()
                    update_group_topic(g_id, clean_t)
                    t_title = "Group Topic Updated" if is_en else "Смысл группы обновлен"
                    if is_en:
                        t_msg = f"Topic for group '{g_name}' updated." if clean_t else f"Topic for group '{g_name}' cleared."
                    else:
                        t_msg = f"Смысл группы '{g_name}' изменен." if clean_t else f"Смысл группы '{g_name}' очищен."
                    show_chat_notification(
                        title=t_title,
                        text=t_msg,
                        sim_info=actor_sim_info,
                    )
                    if callable(on_done):
                        on_done()

                top_title = "Group Topic" if is_en else "Смысл группы"
                top_text = (
                    f"Enter a topic or description for group '{g_name}' (clear text and click OK to remove):"
                    if is_en else
                    f"Введите смысл или описание для группы '{g_name}' (для удаления сотрите текст и нажмите ОК):"
                )
                show_simple_text_input(
                    owner_sim_info=actor_sim_info,
                    title=top_title,
                    text=top_text,
                    initial_value=g_topic,
                    allow_empty=True,
                    max_length=200,
                    on_submit=_on_new_topic,
                    on_cancel=lambda: prompt_edit_groups(actor_sim_info, on_done, on_cancel),
                )
            elif action_tag == "members":
                def _on_new_members(selected_sims):
                    m_ids = [getattr(s, "sim_id", 0) for s in selected_sims if getattr(s, "sim_id", 0)]
                    if actor_id and actor_id not in m_ids:
                        m_ids.append(actor_id)
                    update_group_members(g_id, m_ids)
                    m_title = "Members Updated" if is_en else "Состав обновлен"
                    m_msg = f"Group '{g_name}' now has {len(m_ids)} members." if is_en else f"В группе '{g_name}' теперь {len(m_ids)} участников."
                    show_chat_notification(
                        title=m_title,
                        text=m_msg,
                        sim_info=actor_sim_info,
                    )
                    if callable(on_done):
                        on_done()

                mem_title = "Group Members" if is_en else "Участники группы"
                mem_text = f"Change member list for group '{g_name}':" if is_en else f"Измените состав участников группы '{g_name}':"
                show_multi_contact_picker(
                    actor_sim_info=actor_sim_info,
                    title=mem_title,
                    text=mem_text,
                    on_selected=_on_new_members,
                    preselected_sim_ids=grp.get("member_ids", []),
                    on_cancel=lambda: prompt_edit_groups(actor_sim_info, on_done, on_cancel),
                )
            elif action_tag == "clear":
                clear_group_history(g_id)
                c_title = "History Cleared" if is_en else "История очищена"
                c_msg = f"Message history for group '{g_name}' cleared." if is_en else f"История сообщений группы '{g_name}' очищена."
                show_chat_notification(
                    title=c_title,
                    text=c_msg,
                    sim_info=actor_sim_info,
                )
                if callable(on_done):
                    on_done()
            elif action_tag == "delete":
                delete_group(g_id)
                d_title = "Group Deleted" if is_en else "Группа удалена"
                d_msg = f"Group '{g_name}' was deleted." if is_en else f"Группа '{g_name}' была удалена."
                show_chat_notification(
                    title=d_title,
                    text=d_msg,
                    sim_info=actor_sim_info,
                )
                if callable(on_done):
                    on_done()

        group_act_title = f"Group: {g_name}" if is_en else f"Группа: {g_name}"
        group_act_text = "Select an action for this group:" if is_en else "Выберите действие для этой группы:"
        show_action_menu(
            owner_sim_info=actor_sim_info,
            title=group_act_title,
            text=group_act_text,
            rows_data=action_rows,
            on_selected=_on_action_picked,
            on_cancel=on_cancel,
        )

    edit_main_title = "Edit Groups" if is_en_eg else "Изменение группы"
    edit_main_text = "Select a group to edit:" if is_en_eg else "Выберите группу, которую хотите изменить:"
    show_action_menu(
        owner_sim_info=actor_sim_info,
        title=edit_main_title,
        text=edit_main_text,
        rows_data=rows,
        on_selected=_on_group_picked,
        on_cancel=on_cancel,
    )


def build_group_chat_body(
    actor_name: str,
    group_name: str,
    member_statuses: List[Any],
    history: List[Dict[str, Any]],
    group_topic: str = "",
    max_msgs: int = 6,
    is_typing: bool = False,
    typing_author: str = "",
    total_count: Optional[int] = None,
    actor_id: int = 0,
) -> str:
    """
    Renders group conversation body without emojis.
    Participants show dry online status: (в сети) or (не в сети).
    Incoming messages show author name: [Имя]: текст
    """
    is_en = _is_en()
    count = total_count if total_count is not None else len(member_statuses)
    count_str = f"{count} members" if is_en else f"{count} участников"

    formatted_members = []
    for item in member_statuses:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            m_name, is_on = item[0], bool(item[1])
            if is_en:
                status_tag = '<font color="#27AE60">online</font>' if is_on else '<font color="#7F8C8D">offline</font>'
            else:
                status_tag = '<font color="#27AE60">в сети</font>' if is_on else '<font color="#7F8C8D">не в сети</font>'
            formatted_members.append(f"{m_name} ({status_tag})")
        else:
            formatted_members.append(str(item))

    members_preview = ", ".join(formatted_members[:3])
    if len(formatted_members) > 3:
        extra = f" and {len(formatted_members) - 3} more" if is_en else f" и ещё {len(formatted_members) - 3}"
        members_preview += extra

    top_label = "Topic" if is_en else "Смысл"
    topic_line = f"<br><font color=\"#4A69BD\"><i>{top_label}: {group_topic}</i></font>" if group_topic else ""
    header = f"<p align=\"center\"><b>{group_name}</b> ({count_str}){topic_line}<br><font color=\"#7F8C8D\">{members_preview}</font></p>"

    if not history and not is_typing:
        today_lbl = "——— Today ———" if is_en else "——— Сегодня ———"
        empty_msg = (
            "Group chat is open.<br>Send your first message to start the conversation!"
            if is_en else
            "Групповой чат открыт.<br>Напишите первое сообщение, чтобы начать общение!"
        )
        empty_box = (
            f"<p align=\"center\"><font color=\"#7F8C8D\">{today_lbl}</font><br>"
            f"<font color=\"#7F8C8D\">{empty_msg}</font></p>"
        )
        return f"{header}\n{empty_box}\n<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>"

    from ai_social_pc.chat_manager import get_current_sim_absolute_days, get_relative_day_label
    cur_day = get_current_sim_absolute_days()

    bubbles = []
    last_day_label = None

    for msg in history[-max_msgs:]:
        s = msg.get("sender", "")
        s_id = msg.get("sender_id", 0)
        t = msg.get("text", "")
        m_time = msg.get("time", "")
        m_day = msg.get("abs_day", cur_day)
        m_dow = msg.get("dow", "")
        day_lbl = get_relative_day_label(m_day, cur_day, m_dow)

        if day_lbl != last_day_label:
            bubbles.append(f"<p align=\"center\"><font color=\"#7F8C8D\">——— {day_lbl} ———</font></p>")
            last_day_label = day_lbl

        is_outgoing = False
        if s_id and actor_id and s_id == actor_id:
            is_outgoing = True
        elif s == actor_name:
            is_outgoing = True
        elif s in ("Вы", "You") and not s_id:
            is_outgoing = True

        if is_outgoing:
            bubbles.append(format_outgoing_bubble(t, m_time))
        else:
            # Group incoming message shows author name clearly
            author_header = f"<b>{s}</b>: " if s else ""
            bubbles.append(format_incoming_bubble(s, f"{author_header}{t}", m_time))

    if is_typing:
        if typing_author:
            who = f"{typing_author} is typing . . ." if is_en else f"{typing_author} печатает сообщение . . ."
        else:
            who = "Several people are typing . . ." if is_en else "Печатает несколько людей . . ."
        typing_bubble = f"<p align=\"left\"><font color=\"#7F8C8D\"><i>{who}</i></font></p>"
        bubbles.append(typing_bubble)

    chat_body = "\n".join(bubbles)
    divider = "<p align=\"center\"><font color=\"#7F8C8D\">————————————————————————</font></p>"
    return f"{header}\n{chat_body}\n{divider}"


def show_group_message_input(
    actor_sim_info,
    group_data: Dict[str, Any],
    on_submit: Callable[[str], None],
    default_text: str = "",
    is_typing: bool = False,
    typing_author: str = "",
    on_cancel: Optional[Callable[[], None]] = None,
):
    """
    Renders group chat input dialog.
    """
    if UiDialogTextInputOkCancel is None:
        log("UiDialogTextInputOkCancel is not available.", level="ERROR")
        return None

    is_en = _is_en()
    actor_name = get_recipient_display_name(actor_sim_info)
    actor_id = getattr(actor_sim_info, "sim_id", 0) if not isinstance(actor_sim_info, dict) else 0
    def_grp_title = "Group Chat" if is_en else "Групповой чат"
    group_name = group_data.get("name", def_grp_title)
    group_id = group_data.get("id", "")
    all_member_ids = group_data.get("member_ids", [])
    group_topic = (group_data.get("topic") or "").strip()
    if not group_topic and group_id:
        from ai_social_pc.group_manager import get_group_topic
        group_topic = get_group_topic(group_id)

    # Resolve member statuses (online/offline)
    from ai_social_pc.group_manager import get_group_messages
    from ai_social_pc.chat_manager import get_sim_work_or_school_status
    sim_mgr = services.sim_info_manager() if services is not None else None
    member_statuses = []

    for mid in all_member_ids:
        if mid == actor_id:
            continue
        if sim_mgr:
            s_info = sim_mgr.get(mid)
            if s_info:
                s_name = get_recipient_display_name(s_info)
                ws = get_sim_work_or_school_status(s_info)
                is_on = is_sim_online(s_info) and not ws.get("is_busy", False)
                member_statuses.append((s_name, is_on))
                continue
        member_statuses.append((f"Sim_{mid}" if is_en else f"Сим_{mid}", False))

    history = get_group_messages(group_id)
    chat_body = build_group_chat_body(
        actor_name=actor_name,
        group_name=group_name,
        member_statuses=member_statuses,
        history=history,
        group_topic=group_topic,
        max_msgs=6,
        is_typing=is_typing,
        typing_author=typing_author,
        total_count=len(all_member_ids),
        actor_id=actor_id,
    )

    title = f"Group: {group_name}" if is_en else f"Группа: {group_name}"
    if is_typing:
        prompt_line = (
            "<p align=\"left\"><font color=\"#7F8C8D\"><i>Waiting for reply... (dialog will update automatically)</i></font></p>"
            if is_en else
            "<p align=\"left\"><font color=\"#7F8C8D\"><i>Ожидание ответа... (диалог обновится автоматически)</i></font></p>"
        )
    else:
        prompt_line = (
            "<p align=\"left\"><font color=\"#555555\">Your message to group (OK — send  |  Cancel — close):</font></p>"
            if is_en else
            "<p align=\"left\"><font color=\"#555555\">Ваше сообщение в группу (ОК — отправить  |  Отмена — закрыть):</font></p>"
        )

    text = f"{chat_body}\n{prompt_line}"

    try:
        loc_title = _get_loc_text(title)
        loc_text = _get_loc_text(text)
        loc_init = _get_loc_text(default_text or "")

        factory = UiDialogTextInputOkCancel.TunableFactory(
            text_inputs=("group_msg_input",)
        )
        dialog = factory.default(
            actor_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        if hasattr(dialog, "text_inputs"):
            tuning = getattr(dialog.text_inputs, "group_msg_input", None)
            if tuning is not None:
                if hasattr(tuning, "length_restriction") and hasattr(tuning.length_restriction, "max_length"):
                    tuning.length_restriction.max_length = 500
                if hasattr(tuning, "height"):
                    tuning.height = 65

        text_input_overrides = {
            "group_msg_input": lambda *_, **__: loc_init
        }

        def _on_response(dlg):
            try:
                setattr(dlg, "_is_user_closed", True)
                if getattr(dlg, "accepted", False):
                    responses = getattr(dlg, "text_input_responses", {})
                    entered = str(responses.get("group_msg_input", "")).strip()
                    if entered and callable(on_submit):
                        on_submit(entered)
                    elif not entered:
                        # User clicked OK or pressed Enter with empty text:
                        # Keep the group messenger window open (do nothing / do not close)
                        if callable(on_submit):
                            on_submit("")
                        else:
                            show_group_message_input(
                                actor_sim_info,
                                group_data,
                                on_submit=on_submit,
                                default_text="",
                                is_typing=is_typing,
                                typing_author=typing_author,
                                on_cancel=on_cancel,
                            )
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as ex:
                log_exception("Error in group message input response", ex)

        dialog.show_dialog(on_response=_on_response, text_input_overrides=text_input_overrides)
        return dialog
    except Exception as e:
        log_exception("Failed to render group message input dialog", e)
        return None

