import re
from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.config import (
    get_context_flag,
    toggle_context_flag,
    get_chat_context_flag,
    toggle_chat_context_flag,
    get_custom_sim_lore,
    set_custom_sim_lore,
    delete_custom_sim_lore,
    get_recent_thoughts,
    get_autonomy_enabled,
    set_autonomy_enabled,
    get_autonomy_interval,
    set_autonomy_interval,
    get_api_key,
    get_model,
    get_reasoning_effort,
    reload_config,
    get_active_provider_info,
    load_config,
    get_genealogy_settings,
    get_genealogy_max_relatives,
    set_genealogy_max_relatives,
    get_genealogy_type_flag,
    set_genealogy_type_flag,
    toggle_genealogy_type_flag,
    get_trait_filter_flag,
    toggle_trait_filter_flag,
    get_experimental_flag,
    toggle_experimental_flag,
    get_ww_sex_mode,
    set_ww_sex_mode,
    get_language,
    set_language,
)
from ai_thought_reader.client import check_bridge_health
from ai_thought_reader.ui_helper import show_notification, show_error_notification

try:
    import services
except ImportError:
    services = None

try:
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    LocalizationHelperTuning = None

try:
    from ai_thought_reader.localization import _t, set_current_language, is_english
    _is_en = is_english
except ImportError:
    _t = lambda k, d=None: d or k
    set_current_language = lambda c: None
    _is_en = lambda: False

try:
    from ui.ui_dialog_picker import (
        UiItemPicker,
        BasePickerRow,
        UiSimPicker,
        SimPickerRow,
        SimPickerCellType,
    )
    from ui.ui_dialog_generic import UiDialogTextInputOkCancel
    from ui.ui_dialog import UiDialogOk
except ImportError:
    UiItemPicker = None
    BasePickerRow = None
    UiSimPicker = None
    SimPickerRow = None
    SimPickerCellType = None
    UiDialogTextInputOkCancel = None
    UiDialogOk = None


if UiItemPicker is not None:
    class SettingsItemPicker(UiItemPicker):
        """
        Concrete single-select action-picker subclass of UiItemPicker.
        Forces single selection mode: clicking an item dispatches immediately.
        """
        def _validate_row(self, row):
            return True

        @property
        def multi_select(self):
            return False
else:
    SettingsItemPicker = None


if UiSimPicker is not None:
    class LoreSimPicker(UiSimPicker):
        """
        Single-select Sim Picker subclass of UiSimPicker for selecting characters.
        """
        def _validate_row(self, row):
            return True

        @property
        def multi_select(self):
            return False
else:
    LoreSimPicker = None


def is_sim_an_animal(sim_info) -> bool:
    """
    Returns True if sim_info is any kind of animal/pet (dog, cat, horse, fox, etc.).
    Returns False for human Sims.
    """
    if sim_info is None:
        return False
    try:
        if hasattr(sim_info, "sim_info"):
            sim_info = getattr(sim_info, "sim_info", sim_info)

        if hasattr(sim_info, "is_pet"):
            val = sim_info.is_pet
            if bool(val() if callable(val) else val):
                return True

        if hasattr(sim_info, "is_human"):
            val = sim_info.is_human
            if not bool(val() if callable(val) else val):
                return True

        if hasattr(sim_info, "is_animal"):
            val = sim_info.is_animal
            if bool(val() if callable(val) else val):
                return True

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


def _get_localized_string(text: str):
    """Converts a python string to a LocalizedString or fallback."""
    if LocalizationHelperTuning is not None:
        try:
            return LocalizationHelperTuning.get_raw_text(str(text))
        except Exception:
            pass
    return str(text)


def show_picker_dialog(owner_sim_info, title: str, text: str, rows_data: list, on_selected):
    """
    Renders a native Sims 4 ItemPicker dialog configured as an immediate-action menu.
    rows_data: list of tuples (name, description, tag, is_selected)
    on_selected: callback(selected_tag)
    """
    if SettingsItemPicker is None or BasePickerRow is None:
        log("SettingsItemPicker is not available in this environment.", level="ERROR")
        return

    try:
        loc_title = _get_localized_string(title)
        loc_text = _get_localized_string(text)

        factory = SettingsItemPicker.TunableFactory()
        dialog = factory.default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        # Force strict single selection so clicking any row immediately triggers it
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
                name=_get_localized_string(r_name),
                row_description=_get_localized_string(r_desc) if r_desc else None,
                tag=r_tag,
                is_selected=False,  # strictly False so no item is pre-highlighted or locks selection
            )
            dialog.add_row(row)

        def _on_response(dlg):
            try:
                if getattr(dlg, "accepted", False):
                    selected_tag = None

                    # 1. Standard result tags
                    results = dlg.get_result_tags()
                    if results:
                        selected_tag = results[0]

                    # 2. Picked results mapped by option_id
                    if selected_tag is None and hasattr(dlg, "picked_results") and dlg.picked_results:
                        for pid in dlg.picked_results:
                            if pid in tag_by_option_id:
                                selected_tag = tag_by_option_id[pid]
                                break

                    # 3. get_single_result_tag() fallback
                    if selected_tag is None and hasattr(dlg, "get_single_result_tag"):
                        try:
                            selected_tag = dlg.get_single_result_tag()
                        except Exception:
                            pass

                    if selected_tag is not None and callable(on_selected):
                        on_selected(selected_tag)
            except Exception as ex:
                log_exception("Error handling picker dialog response", ex)

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to show picker dialog", e)



def show_text_input_dialog(owner_sim_info, title: str, text: str, initial_text: str, on_submit, on_cancel=None):
    """
    Renders a native Sims 4 TextInput dialog for entering custom lore / biography.
    """
    if UiDialogTextInputOkCancel is None:
        log("UiDialogTextInputOkCancel is not available in this environment.", level="ERROR")
        return

    try:
        loc_title = _get_localized_string(title)
        loc_text = _get_localized_string(text)
        loc_init = _get_localized_string(initial_text or "")

        factory = UiDialogTextInputOkCancel.TunableFactory(
            text_inputs=("lore_input",)
        )
        dialog = factory.default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        # Expand character limit and box height for comfortable typing
        if hasattr(dialog, "text_inputs"):
            lore_tuning = getattr(dialog.text_inputs, "lore_input", None)
            if lore_tuning is not None:
                if hasattr(lore_tuning, "length_restriction") and hasattr(lore_tuning.length_restriction, "max_length"):
                    lore_tuning.length_restriction.max_length = 1000
                if hasattr(lore_tuning, "height"):
                    lore_tuning.height = 120

        text_input_overrides = {
            "lore_input": lambda *_, **__: loc_init
        }

        def _on_response(dlg):
            try:
                if getattr(dlg, "accepted", False):
                    responses = getattr(dlg, "text_input_responses", {})
                    val = responses.get("lore_input", "")
                    if callable(on_submit):
                        on_submit(str(val).strip())
                else:
                    if callable(on_cancel):
                        on_cancel()
            except Exception as ex:
                log_exception("Error handling text input dialog response", ex)

        dialog.show_dialog(on_response=_on_response, text_input_overrides=text_input_overrides)
    except Exception as e:
        log_exception("Failed to show text input dialog", e)


def show_info_dialog(owner_sim_info, title: str, text: str, on_close=None):
    """
    Renders an informative OK dialog.
    """
    if UiDialogOk is None:
        show_notification(title, text, sim_info=owner_sim_info)
        if callable(on_close):
            on_close()
        return

    try:
        loc_title = _get_localized_string(title)
        loc_text = _get_localized_string(text)

        dialog = UiDialogOk.TunableFactory().default(
            owner_sim_info,
            text=lambda *_: loc_text,
            title=lambda *_: loc_title,
        )

        def _on_response(dlg):
            if callable(on_close):
                on_close()

        dialog.show_dialog(on_response=_on_response)
    except Exception as e:
        log_exception("Failed to show info dialog", e)
        show_notification(title, text, sim_info=owner_sim_info)
        if callable(on_close):
            on_close()


# =====================================================================
# MENU CONTROLLERS
# =====================================================================

def open_settings_menu(sim_info=None):
    """
    Entry point for opening the mod settings menu.
    If sim_info is not provided, defaults to active Sim.
    """
    if sim_info is None and services is not None:
        sim_info = services.active_sim_info()

    if sim_info is None:
        log("Cannot open settings menu: active sim_info not found.", level="ERROR")
        return

    show_main_menu(sim_info)


def show_main_menu(sim_info):
    """Main Settings Menu."""
    def_name = _t("LABEL_SIM", "Sim")
    first_name = getattr(sim_info, "first_name", def_name) or def_name
    last_name = getattr(sim_info, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip()

    title = _t("MENU_TITLE", "Synapse Settings")
    char_label = _t("LABEL_CHARACTER", "Character")
    text = (
        f"{char_label}: {full_name}\n"
        f"{_t('MENU_DESC', 'Select a category to configure:')}"
    )

    rows = [
        (
            _t("MENU_LORE", "[+] Личная биография / Лор"),
            _t("MENU_LORE_DESC", "Выбрать персонажа и задать факты, тайны или биографию для ИИ"),
            "lore",
            False,
        ),
        (
            _t("MENU_FLAGS", "[+] Компоненты контекста"),
            _t("MENU_FLAGS_DESC", "Включение и отключение частей контекста (слава, беременность, семья, одежда и др.)"),
            "flags",
            False,
        ),
        (
            _t("MENU_CHAT_FLAGS", "[+] Компоненты контекста [чат]"),
            _t("MENU_CHAT_FLAGS_DESC", "Включение и отключение частей контекста для переписки в мессенджере"),
            "chat_flags",
            False,
        ),
        (
            _t("MENU_GENEALOGY", "[+] Настройка генеалогии"),
            _t("MENU_GENEALOGY_DESC", "Лимит длины списка родни и выбор категорий родственников для контекста ИИ"),
            "genealogy",
            False,
        ),
        (
            _t("MENU_SUMMARIZATION", "[+] Настройка суммаризации"),
            _t("MENU_SUMMARIZATION_DESC", "Управление созданием памяти из личных сообщений и групповых чатов"),
            "summarization",
            False,
        ),
        (
            _t("MENU_AUTONOMY", "[+] Автономные мысли"),
            _t("MENU_AUTONOMY_DESC", "Настройка фоновой генерации мыслей персонажей по таймеру"),
            "autonomy",
            False,
        ),
        (
            _t("MENU_JOURNAL", "[+] Журнал недавних мыслей"),
            _t("MENU_JOURNAL_DESC", "Просмотр истории мыслей персонажей за текущую игровую сессию"),
            "journal",
            False,
        ),
        (
            _t("MENU_DIAGNOSTICS", "[+] Статус связи и диагностика"),
            _t("MENU_DIAGNOSTICS_DESC", "Проверка подключения к AI Bridge, активной модели и ключа"),
            "diagnostics",
            False,
        ),
        (
            _t("MENU_TRAITS_FILTER", "[+] Фильтр черт характера"),
            _t("MENU_TRAITS_FILTER_DESC", "Выбор категорий черт для ИИ (основные CAS, жизненная цель, WickedWhims, награды, моды)"),
            "traits_filter",
            False,
        ),
        (
            _t("MENU_EXPERIMENTAL", "[+] Экспериментальные функции"),
            _t("MENU_EXPERIMENTAL_DESC", "Экспериментальные параметры (пауза и окно ожидания генерации живого диалога)"),
            "experimental",
            False,
        ),
        (
            _t("MENU_LANGUAGE", "🌐 Язык интерфейса и контекста / Language"),
            f"{_t('MENU_LANGUAGE_DESC', 'Переключить язык мода и контекста')} [{get_language()}]",
            "language",
            False,
        ),
    ]

    def _on_select(tag):
        if tag == "lore":
            pick_sim_for_custom_lore(sim_info)
        elif tag == "flags":
            show_context_flags_menu(sim_info)
        elif tag == "chat_flags":
            show_chat_context_flags_menu(sim_info)
        elif tag == "traits_filter":
            show_traits_filter_menu(sim_info)
        elif tag == "genealogy":
            show_genealogy_menu(sim_info)
        elif tag == "summarization":
            show_summarization_menu(sim_info)
        elif tag == "autonomy":
            show_autonomy_menu(sim_info)
        elif tag == "journal":
            show_recent_thoughts_menu(sim_info)
        elif tag == "diagnostics":
            show_diagnostics_menu(sim_info)
        elif tag == "experimental":
            show_experimental_menu(sim_info)
        elif tag == "language":
            show_language_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 1. CUSTOM SIM LORE / BIOGRAPHY
# =====================================================================

def pick_sim_for_custom_lore(owner_sim_info):
    """
    Opens a Sim Picker displaying all Sims in the world, allowing the player to select any character
    whose custom lore / biography they want to view or edit.
    """
    if owner_sim_info is None and services is not None:
        owner_sim_info = services.active_sim_info()

    if owner_sim_info is None:
        log("pick_sim_for_custom_lore: owner_sim_info is None", level="ERROR")
        return

    sim_info_mgr = services.sim_info_manager() if services is not None else None
    if sim_info_mgr is None:
        show_custom_lore_menu(owner_sim_info, owner_sim_info=owner_sim_info)
        return

    owner_id = getattr(owner_sim_info, "sim_id", 0)
    owner_household = getattr(owner_sim_info, "household", None)

    all_sims = []
    for s_info in sim_info_mgr.get_all():
        s_id = getattr(s_info, "sim_id", 0)
        if not s_id:
            continue
        if is_sim_an_animal(s_info):
            continue
        age_enum = getattr(s_info, "age", None)
        age_name = getattr(age_enum, "name", "").upper() if age_enum else ""
        if age_name in ("BABY", "INFANT"):
            continue
        all_sims.append(s_info)

    if not all_sims:
        all_sims = [owner_sim_info]

    # Sort priority:
    # 1. Active Sim
    # 2. Household members
    # 3. Sims who already have custom lore configured
    # 4. Alphabetical by first and last name
    def _sort_key(s):
        s_id = getattr(s, "sim_id", 0)
        is_active = 0 if (s_id == owner_id) else 1
        s_hh = getattr(s, "household", None)
        is_hh = 0 if (owner_household is not None and s_hh == owner_household) else 1
        has_lore = 0 if get_custom_sim_lore(s_id) else 1
        f_name = getattr(s, "first_name", "") or ""
        l_name = getattr(s, "last_name", "") or ""
        return (is_active, is_hh, has_lore, f_name.lower(), l_name.lower())

    all_sims.sort(key=_sort_key)

    is_en = _is_en()
    title = "Select Sim: Biography / Lore" if is_en else "Выбор персонажа: Биография / Лор"
    text = "Select a character to configure their personal lore and backstory:" if is_en else "Выберите персонажа, для которого хотите настроить личный лор и биографию:"

    if LoreSimPicker is not None and SimPickerRow is not None:
        try:
            loc_title = _get_localized_string(title)
            loc_text = _get_localized_string(text)

            factory = LoreSimPicker.TunableFactory()
            dialog = factory.default(
                owner_sim_info,
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

                        if selected_sim is not None:
                            show_custom_lore_menu(selected_sim, owner_sim_info=owner_sim_info)
                        else:
                            show_main_menu(owner_sim_info)
                    else:
                        show_main_menu(owner_sim_info)
                except Exception as ex:
                    log_exception("Error in LoreSimPicker _on_response", ex)
                    show_main_menu(owner_sim_info)

            dialog.show_dialog(on_response=_on_response)
            return
        except Exception as e:
            log_exception("Failed to show LoreSimPicker dialog, falling back to ItemPicker", e)

    # Fallback to SettingsItemPicker list
    rows = []
    for s in all_sims:
        s_id = getattr(s, "sim_id", 0)
        f_name = getattr(s, "first_name", "Сим") or "Сим"
        l_name = getattr(s, "last_name", "") or ""
        f_name_full = f"{f_name} {l_name}".strip()
        lore = get_custom_sim_lore(s_id)
        if lore:
            short_lore = lore[:50] + "..." if len(lore) > 50 else lore
            desc = f"[Lore Set] \"{short_lore}\"" if is_en else f"[Задан лор] «{short_lore}»"
        else:
            desc = "No lore set (click to enter)" if is_en else "Лор не задан (нажмите для ввода)"
        rows.append((f_name_full, desc, s, False))

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться назад"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_item_select(tag):
        if tag == "back":
            show_main_menu(owner_sim_info)
        elif tag is not None:
            show_custom_lore_menu(tag, owner_sim_info=owner_sim_info)

    show_picker_dialog(owner_sim_info, title, text, rows, _on_item_select)


def show_custom_lore_menu(sim_info, owner_sim_info=None):
    """Submenu for viewing, editing, or deleting custom lore for the current Sim."""
    if owner_sim_info is None and services is not None:
        owner_sim_info = services.active_sim_info()
    if owner_sim_info is None:
        owner_sim_info = sim_info

    is_en = _is_en()
    sim_id = getattr(sim_info, "sim_id", None)
    def_name = _t("LABEL_SIM", "Sim")
    first_name = getattr(sim_info, "first_name", def_name) or def_name
    last_name = getattr(sim_info, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip()

    current_lore = get_custom_sim_lore(sim_id)

    title = _t("LORE_MENU_TITLE", "Personal Info: {name}").format(name=full_name)
    if current_lore:
        text = _t("LORE_CURRENT_DESC", "Current biography (sent to AI immediately after traits):\n\n\"{lore}\"\n\nSelect an action:").format(lore=current_lore)
    else:
        text = _t("LORE_EMPTY_DESC", "{name} does not have a personal biography yet.\n\nYou can enter important facts, secrets, or backstory. The AI will consider them in every thought generation!\n\nSelect an action:").format(name=full_name)

    rows = [
        (
            _t("LORE_BTN_EDIT", "[+] Enter / Edit Biography"),
            _t("LORE_BTN_EDIT_DESC", "Open text input dialog to edit backstory"),
            "edit",
            False,
        )
    ]
    if current_lore:
        rows.append((
            _t("LORE_BTN_DELETE", "[X] Delete Biography"),
            _t("LORE_BTN_DELETE_DESC", "Erase current biography for this Sim"),
            "delete",
            False,
        ))
    rows.append((
        _t("LORE_BTN_CHANGE_SIM", "<< Select Another Sim"),
        _t("LORE_BTN_CHANGE_SIM_DESC", "Return to Sim selection list"),
        "change_sim",
        False,
    ))
    rows.append((
        _t("BTN_BACK", "<< Back to Main Menu"),
        _t("BTN_BACK_DESC", "Return to previous menu"),
        "back",
        False,
    ))

    def _on_select(tag):
        if tag == "edit":
            show_custom_lore_input(sim_info, current_lore, owner_sim_info=owner_sim_info)
        elif tag == "delete":
            delete_custom_sim_lore(sim_id)
            del_msg = _t("LORE_DELETED_NOTIF", "Biography for {name} has been deleted.").format(name=full_name)
            show_notification(
                "Synapse",
                del_msg,
                sim_info=owner_sim_info,
            )
            show_custom_lore_menu(sim_info, owner_sim_info=owner_sim_info)
        elif tag == "change_sim":
            pick_sim_for_custom_lore(owner_sim_info)
        elif tag == "back":
            show_main_menu(owner_sim_info)

    show_picker_dialog(owner_sim_info, title, text, rows, _on_select)


def show_custom_lore_input(sim_info, current_lore, owner_sim_info=None):
    """Opens text input dialog to type custom lore."""
    if owner_sim_info is None:
        owner_sim_info = sim_info

    def_name = _t("LABEL_SIM", "Sim")
    first_name = getattr(sim_info, "first_name", def_name) or def_name
    last_name = getattr(sim_info, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip()

    title = _t("LORE_INPUT_TITLE", "Enter Biography: {name}").format(name=full_name)
    text = _t("LORE_INPUT_TEXT", "Enter facts, backstory, or secrets for {name}.\nThis text will be provided to the AI directly after character traits:").format(name=full_name)

    def _on_submit(entered_text):
        sim_id = getattr(sim_info, "sim_id", None)
        if sim_id:
            if entered_text:
                set_custom_sim_lore(sim_id, entered_text)
                saved_msg = _t("LORE_SAVED_NOTIF", "Biography for {name} has been saved!").format(name=full_name)
                show_notification(
                    "Synapse",
                    saved_msg,
                    sim_info=owner_sim_info,
                )
            else:
                delete_custom_sim_lore(sim_id)
                clr_msg = _t("LORE_DELETED_NOTIF", "Biography for {name} has been deleted.").format(name=full_name)
                show_notification(
                    "Synapse",
                    clr_msg,
                    sim_info=owner_sim_info,
                )
        show_custom_lore_menu(sim_info, owner_sim_info=owner_sim_info)

    def _on_cancel():
        show_custom_lore_menu(sim_info, owner_sim_info=owner_sim_info)

    show_text_input_dialog(
        owner_sim_info,
        title,
        text,
        current_lore or "",
        _on_submit,
        on_cancel=_on_cancel,
    )


# =====================================================================
# 2. CONTEXT COMPONENT TOGGLES
# =====================================================================

def _is_en() -> bool:
    try:
        from ai_thought_reader.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False


CONTEXT_FLAG_DEFINITIONS_EN = [
    ("fame", "Celebrity Status & Reputation", "Star status, celebrity level, paparazzi, and public reputation"),
    ("pregnancy", "Pregnancy & Parenthood", "Pregnancy trimesters, contractions, and expecting a baby"),
    ("family", "Family, Partner & Relatives", "Parents, children, spouse, boyfriend/girlfriend, lovers, siblings"),
    ("roommates", "Household Roommates", "Non-related Sims living in the same home (roommates/friends)"),
    ("nearby", "Surrounding Sims Nearby", "Who is currently nearby or in the same room"),
    ("social", "Conversation & Interlocutor", "Current conversation partner, dialogue tone and relationship"),
    ("clothing", "Clothing & Undress State", "Current outfit, clothing style, and level of undress/nudity"),
    ("weather", "Weather & Seasons", "Temperature, rain, snow, and current active season"),
    ("world_time", "In-Game Time & Holidays", "Days of the week, in-game time, and active holidays"),
    ("location", "Location & Rooms", "Lot name, world neighborhood, and current room type"),
    ("career", "Career & Profession", "Job title, company, work performance, and career level"),
    ("aspiration", "Sim Aspiration", "Currently active lifetime aspiration"),
    ("funds", "Household Budget", "Total household Simoleons count"),
    ("pets", "Household Pets", "Household dogs, cats, and pets"),
    ("incest", "Forbidden Romance / Taboo Tags", "Marks [TABOO/INCEST] and psychological reactions to romance between relatives"),
]

CHAT_CONTEXT_FLAG_DEFINITIONS_EN = [
    ("chat_age_gender", "Age & Gender", "Age category and gender of characters"),
    ("chat_occult", "Occult & Race", "Human, Vampire, Spellcaster, Werewolf, Mermaid, Alien"),
    ("chat_traits", "Personality Traits", "Personal character traits"),
    ("chat_mood", "Current Mood", "Current mood and moodlet causes"),
    ("chat_location", "Current Location", "Sim's current location (room or world lot)"),
    ("chat_lore", "Personal Biography / Lore", "Custom facts and backstory from character settings"),
    ("chat_career", "Career & Profession", "Job title, work position, and career status"),
    ("chat_aspiration", "Sim Aspiration", "Active lifetime aspiration"),
    ("chat_family", "Family & Relatives", "Parents, children, spouse, partner, siblings"),
    ("chat_roommates", "Household Roommates", "Non-related housemates and roommates"),
    ("chat_pets", "Household Pets", "Family dogs and cats"),
    ("chat_pregnancy", "Pregnancy", "Pregnancy progress and expecting a baby"),
    ("chat_fame", "Fame & Reputation", "Celebrity level and reputation"),
    ("chat_funds", "Household Budget", "Family funds in Simoleons"),
    ("chat_relationship", "Relationship Between Sims", "Who the Sims are to each other (friends, couple, enemies)"),
    ("chat_incest", "Taboo / Incest Tags", "Mark [incest] in romance between relatives"),
    ("chat_history", "Chat History", "Last sent messages of current conversation"),
    ("chat_memory", "Dialogue Memories", "Episodic memory about meaningful moments, plans, and secrets"),
]

TRAIT_FILTER_FLAG_DEFINITIONS_EN = [
    ("core", "3 Core CAS Traits", "Fundamental personality traits from CAS"),
    ("aspiration", "Aspiration Bonus Trait", "Bonus trait tied to chosen aspiration"),
    ("ww_archetypes", "WickedWhims Archetypes", "WW personality archetypes (Caregiver, Rebel, Sage, etc.)"),
    ("rewards", "Purchased Rewards", "Reward store traits and aspiration milestones"),
    ("ww_traits", "WickedWhims Traits", "Special WW traits and preferences"),
    ("custom_mods", "Custom Mod Traits", "Traits from external mods (RPO, etc.)"),
]

GENEALOGY_TYPE_DEFINITIONS_EN = [
    ("spouses", "Spouses & Committed Partners", "Husband, wife, fiancé, fiancée, boyfriend, girlfriend, lovers"),
    ("children", "Children", "Sons, daughters, stepsons, stepdaughters"),
    ("parents", "Parents", "Father, mother, stepfather, stepmother"),
    ("siblings", "Siblings", "Full, half, and step brothers and sisters"),
    ("grandparents", "Grandparents", "Direct ancestors from mother and father"),
    ("grandchildren", "Grandchildren", "Children's offspring"),
    ("child_spouses", "Children's In-Laws (Son/Daughter-in-law)", "Spouses and partners of sons and daughters"),
    ("child_in_laws", "In-law Extended Family", "Parents and siblings of son/daughter-in-law"),
    ("sibling_family", "Siblings' Families", "Brothers' wives, sisters' husbands, nieces and nephews"),
    ("spouse_in_laws", "Spouse's Relatives", "Father-in-law, mother-in-law, brother/sister-in-law"),
    ("extended", "Aunts, Uncles & Cousins", "Parents' siblings and cousins"),
    ("deceased", "Deceased Relatives", "Deceased ancestors and ghosts"),
]

EXPERIMENTAL_FLAG_DEFINITIONS_EN = [
    (
        "direct_dialogue_pause",
        "Pause and Waiting Dialog in Live Speech",
        "Pauses the game and holds a waiting modal dialog while the AI generates a reply so Sims do not walk away",
    ),
]

CONTEXT_FLAG_DEFINITIONS = [
    ("fame", "Слава и репутация", "Статус звезды, уровень славы, папарацци и репутация"),
    ("pregnancy", "Беременность и родительство", "Сроки беременности, схватки, ожидание ребенка"),
    ("family", "Семья, пара и родственники", "Родители, дети, супруги, пара (девушка/парень), любовницы, братья/сестры"),
    ("roommates", "Соседи по дому", "Неродственные персонажи, проживающие в одном доме (сожители/друзья)"),
    ("nearby", "Окружающие персонажи", "Кто находится поблизости или в одной комнате"),
    ("social", "Диалоги и стиль общения", "Текущий собеседник, тон разговора и отношения"),
    ("clothing", "Одежда и уровень раздевания", "Текущий наряд, стиль одежды и степень наготы"),
    ("weather", "Погода и время года", "Температура, дождь, снег, текущий сезон"),
    ("world_time", "Время и праздники", "Дни недели, игровое время и активные праздники"),
    ("location", "Локация и комнаты", "Название участка, район и текущая комната"),
    ("career", "Профессия и карьера", "Работа, должность и карьерный статус"),
    ("aspiration", "Жизненная цель", "Текущая жизненная цель сима"),
    ("funds", "Бюджет семьи", "Количество симолеонов на счете семьи"),
    ("pets", "Питомцы в семье", "Домашние животные (кошки, собаки)"),
    ("incest", "Теги запретной связи / инцеста", "Пометки [ИНЦЕСТ] и психологическая реакция на романтику/интим между родственниками"),
]


def show_context_flags_menu(sim_info):
    """Submenu for toggling individual prompt context sections on or off."""
    is_en = _is_en()
    title = "Context Components" if is_en else "Компоненты контекста"
    text = (
        "Click any item to instantly toggle [ON] / [OFF].\n"
        "Disabled components are excluded from the AI prompt:"
        if is_en else
        "Нажмите на любой пункт для мгновенного переключения [ВКЛ] / [ВЫКЛ].\n"
        "Отключенные разделы исключаются из промпта нейросети:"
    )

    defs = CONTEXT_FLAG_DEFINITIONS_EN if is_en else CONTEXT_FLAG_DEFINITIONS
    rows = []
    for flag_key, flag_name, flag_desc in defs:
        enabled = get_context_flag(flag_key)
        if is_en:
            if enabled:
                row_title = f"[ON] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn OFF)"
            else:
                row_title = f"[OFF] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn ON)"
        else:
            if enabled:
                row_title = f"[ВКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            else:
                row_title = f"[ВЫКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВКЛЮЧИТЬ)"
        rows.append((row_title, row_desc, flag_key, False))

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться в главное меню настроек"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        else:
            toggle_context_flag(tag)
            # Re-render submenu with updated state immediately
            show_context_flags_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 2b. CHAT CONTEXT COMPONENT TOGGLES
# =====================================================================

CHAT_CONTEXT_FLAG_DEFINITIONS = [
    ("chat_age_gender", "Возраст и пол", "Возрастная категория и пол персонажей"),
    ("chat_occult", "Раса и оккультизм", "Человек, вампир, чародей, оборотень, русалка, пришелец"),
    ("chat_traits", "Черты характера", "Личностные черты симов"),
    ("chat_mood", "Текущее настроение", "Настроение и причины мудлетов"),
    ("chat_location", "Текущая локация", "Где находится сим (комната лота или город)"),
    ("chat_lore", "Личная биография / Лор", "Факты и предыстория из настроек сима"),
    ("chat_career", "Профессия и карьера", "Работа, должность и карьерный статус"),
    ("chat_aspiration", "Жизненная цель", "Текущая жизненная цель сима"),
    ("chat_family", "Семья, пара и родственники", "Родители, дети, супруги, пара (девушка/парень), любовницы, братья/сестры"),
    ("chat_roommates", "Соседи по дому", "Неродственные персонажи, проживающие в одном доме (сожители/друзья)"),
    ("chat_pets", "Питомцы в семье", "Домашние животные (кошки, собаки)"),
    ("chat_pregnancy", "Беременность", "Сроки беременности, схватки, ожидание ребенка"),
    ("chat_fame", "Слава и репутация", "Статус звезды, уровень славы и репутация"),
    ("chat_funds", "Бюджет семьи", "Количество симолеонов на счете семьи"),
    ("chat_relationship", "Отношения между симами", "Кем симы приходятся друг другу (друзья, пара, враги)"),
    ("chat_incest", "Теги запретной связи / инцеста", "Пометки [инцест] при романтике между родственниками"),
    ("chat_history", "История переписки", "Передача последних сообщений текущего диалога"),
    ("chat_memory", "Память о прошлых диалогах", "Эпизодическая память симов о значимых событиях, договоренностях и тайнах"),
]


def show_chat_context_flags_menu(sim_info):
    """Submenu for toggling individual chat prompt context sections on or off."""
    is_en = _is_en()
    title = "Context Components [Chat]" if is_en else "Компоненты контекста [чат]"
    text = (
        "Click any item to instantly toggle [ON] / [OFF].\n"
        "Disabled components are excluded from AI Messenger context:"
        if is_en else
        "Нажмите на любой пункт для мгновенного переключения [ВКЛ] / [ВЫКЛ].\n"
        "Отключенные разделы исключаются из контекста переписки в мессенджере:"
    )

    defs = CHAT_CONTEXT_FLAG_DEFINITIONS_EN if is_en else CHAT_CONTEXT_FLAG_DEFINITIONS
    rows = []
    for flag_key, flag_name, flag_desc in defs:
        enabled = get_chat_context_flag(flag_key)
        if is_en:
            if enabled:
                row_title = f"[ON] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn OFF)"
            else:
                row_title = f"[OFF] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn ON)"
        else:
            if enabled:
                row_title = f"[ВКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            else:
                row_title = f"[ВЫКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВКЛЮЧИТЬ)"
        rows.append((row_title, row_desc, flag_key, False))

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться в главное меню настроек"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        else:
            toggle_chat_context_flag(tag)
            # Re-render submenu with updated state immediately
            show_chat_context_flags_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 2c. TRAIT FILTER SETTINGS
# =====================================================================

TRAIT_FILTER_FLAG_DEFINITIONS = [
    ("core", "3 основные черты характера", "Базовые личностные черты из редактора создания персонажа (CAS)"),
    ("aspiration", "Черта за жизненную цель", "Бонусная черта характера, привязанная к выбранной жизненной цели"),
    ("ww_archetypes", "Архетипы WickedWhims", "Психологические архетипы личности WW (Опекун, Мудрец, Бунтарь и др.)"),
    ("rewards", "Купленные награды", "Черты за баллы счастья и выполненные вехи из магазина наград"),
    ("ww_traits", "Черты WickedWhims", "Особые черты характера и предпочтений WickedWhims"),
    ("custom_mods", "Черты из других модов", "Черты характера сторонних модов (Relationship & Pregnancy Overhaul и др.)"),
]


def show_traits_filter_menu(sim_info):
    """Submenu for toggling trait categories in AI context."""
    is_en = _is_en()
    title = "Personality Traits Filter" if is_en else "Фильтр черт характера"
    text = (
        "Click any item to instantly toggle [ON] / [OFF].\n"
        "Disabled trait categories are excluded from AI context (thoughts, dialog, messenger):"
        if is_en else
        "Нажмите на любой пункт для мгновенного переключения [ВКЛ] / [ВЫКЛ].\n"
        "Отключенные категории черт исключаются из контекста ИИ (мысли, диалог, мессенджер):"
    )

    defs = TRAIT_FILTER_FLAG_DEFINITIONS_EN if is_en else TRAIT_FILTER_FLAG_DEFINITIONS
    rows = []
    for flag_key, flag_name, flag_desc in defs:
        enabled = get_trait_filter_flag(flag_key)
        if is_en:
            if enabled:
                row_title = f"[ON] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn OFF)"
            else:
                row_title = f"[OFF] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn ON)"
        else:
            if enabled:
                row_title = f"[ВКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            else:
                row_title = f"[ВЫКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВКЛЮЧИТЬ)"
        rows.append((row_title, row_desc, flag_key, False))

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться в главное меню настроек"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        else:
            toggle_trait_filter_flag(tag)
            show_traits_filter_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 2d. SUMMARIZATION SETTINGS
# =====================================================================

def show_summarization_menu(sim_info):
    """Submenu for configuring dialogue and chat summarization."""
    is_en = _is_en()
    title = "Summarization & Memory Settings" if is_en else "Настройка суммаризации"
    text = (
        "Configure Sim long-term memory formation from chats and live direct dialogues.\n\n"
        "Select an option below to toggle automatic AI summarization:"
        if is_en else
        "Настройка создания долговременной памяти персонажей из переписок и живых диалогов.\n\n"
        "Выберите категорию ниже для включения или отключения авто-суммаризации ИИ:"
    )

    sum_direct = get_chat_context_flag("summarize_direct")
    sum_personal = get_chat_context_flag("summarize_personal")
    sum_group = get_chat_context_flag("summarize_group")

    if is_en:
        d_title = "[ON] Direct Dialogues (In-Person)" if sum_direct else "[OFF] Direct Dialogues (In-Person)"
        d_desc = (
            "Summarize face-to-face spoken conversations 10s after ending (Click to turn OFF)"
            if sum_direct else
            "Direct in-person dialogue summarization disabled (Click to turn ON)"
        )
        p_title = "[ON] Direct Messages (1-on-1 Chat)" if sum_personal else "[OFF] Direct Messages (1-on-1 Chat)"
        p_desc = (
            "Summarize 1-on-1 private chat upon closing messenger (Click to turn OFF)"
            if sum_personal else
            "Direct message summarization disabled (Click to turn ON)"
        )
        g_title = "[ON] Group Chats" if sum_group else "[OFF] Group Chats"
        g_desc = (
            "Summarize group chat discussions upon closing window (Click to turn OFF)"
            if sum_group else
            "Group chat summarization disabled (Click to turn ON)"
        )
    else:
        d_title = "[ВКЛ] Живые диалоги (в игре)" if sum_direct else "[ВЫКЛ] Живые диалоги (в игре)"
        d_desc = (
            "Суммаризация живого общения через 10 сек после диалога (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            if sum_direct else
            "Суммаризация живого общения отключена (Нажмите, чтобы ВКЛЮЧИТЬ)"
        )
        p_title = "[ВКЛ] Личные сообщения (мессенджер)" if sum_personal else "[ВЫКЛ] Личные сообщения (мессенджер)"
        p_desc = (
            "Суммаризация переписки 1-на-1 при закрытии мессенджера (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            if sum_personal else
            "Суммаризация переписки 1-на-1 отключена (Нажмите, чтобы ВКЛЮЧИТЬ)"
        )
        g_title = "[ВКЛ] Групповые чаты" if sum_group else "[ВЫКЛ] Групповые чаты"
        g_desc = (
            "Суммаризация общения в группах при закрытии окна (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            if sum_group else
            "Суммаризация общения в группах отключена (Нажмите, чтобы ВКЛЮЧИТЬ)"
        )

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться в главное меню настроек"

    rows = [
        (
            d_title,
            d_desc,
            "toggle_direct",
            False,
        ),
        (
            p_title,
            p_desc,
            "toggle_personal",
            False,
        ),
        (
            g_title,
            g_desc,
            "toggle_group",
            False,
        ),
        (
            back_lbl,
            back_dsc,
            "back",
            False,
        ),
    ]

    def _on_select(tag):
        if tag == "toggle_direct":
            toggle_chat_context_flag("summarize_direct")
            show_summarization_menu(sim_info)
        elif tag == "toggle_personal":
            toggle_chat_context_flag("summarize_personal")
            show_summarization_menu(sim_info)
        elif tag == "toggle_group":
            toggle_chat_context_flag("summarize_group")
            show_summarization_menu(sim_info)
        elif tag == "back":
            show_main_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 2d. GENEALOGY / FAMILY CONTEXT SETTINGS
# =====================================================================

GENEALOGY_TYPE_DEFINITIONS = [
    ("spouses", "Супруги и постоянная пара", "Муж, жена, жених, невеста, парень, девушка, любовники"),
    ("children", "Дети", "Сыновья, дочери, пасынки, падчерицы"),
    ("parents", "Родители", "Отец, мать, отчим, мачеха"),
    ("siblings", "Братья и сестры", "Родные и сводные братья и сестры"),
    ("grandparents", "Бабушки и дедушки", "Прямые предки со стороны отца и матери"),
    ("grandchildren", "Внуки и внучки", "Потомки детей"),
    ("child_spouses", "Семья детей (Невестка / Зять)", "Супруги и пары сыновей и дочерей"),
    ("child_in_laws", "Родственники невестки / зятя", "Сваты (родители невестки/зятя), их братья и сестры"),
    ("sibling_family", "Семья братьев и сестер", "Жена брата, муж сестры, племянники и племянницы"),
    ("spouse_in_laws", "Родня со стороны супруга", "Свёкор, свекровь, тесть, тёща, шурин, деверь, золовка, свояченица"),
    ("extended", "Дяди, тети, кузены", "Родня родителей и двоюродные братья/сестры"),
    ("deceased", "Покойные родственники", "Отображение умерших предков и призраков"),
]


def show_genealogy_menu(sim_info):
    """Main submenu for Genealogy and Relatives context settings."""
    max_rel = get_genealogy_max_relatives()
    title = _t("GENEALOGY_TITLE", "Genealogy Settings")
    text = (
        f"{_t('GENEALOGY_DESC_TEXT', 'Configure tracking of relatives and ancestors included in AI context.')}\n\n"
        f"{_t('GENEALOGY_ROW_MAX', '[123] Max Relatives in Context: {count}').format(count=max_rel)}"
    )

    r1_t = _t("GENEALOGY_ROW_MAX", "[Limit: {count}] Maximum List Length").format(count=max_rel)
    r1_d = _t("GENEALOGY_ROW_MAX_DESC", "Click to change maximum relatives limit")
    r2_t = _t("GENEALOGY_ROW_TYPES", "[+] Tracked Kinship Types")
    r2_d = _t("GENEALOGY_ROW_TYPES_DESC", "Configure which family relations to include (parents, siblings, etc.)")
    back_lbl = _t("BTN_BACK", "<< Back to Main Menu")
    back_dsc = _t("BTN_BACK_DESC", "Return to previous menu")

    rows = [
        (
            r1_t,
            r1_d,
            "edit_max",
            False,
        ),
        (
            r2_t,
            r2_d,
            "filter_types",
            False,
        ),
        (
            back_lbl,
            back_dsc,
            "back",
            False,
        ),
    ]

    def _on_select(tag):
        if tag == "edit_max":
            show_genealogy_max_relatives_input(sim_info)
        elif tag == "filter_types":
            show_genealogy_types_menu(sim_info)
        elif tag == "back":
            show_main_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


def show_genealogy_max_relatives_input(sim_info):
    """Text input dialog for custom max length of relatives list."""
    current_max = get_genealogy_max_relatives()
    title = _t("GENEALOGY_MAX_TITLE", "Max Relatives Limit")
    text = _t("GENEALOGY_MAX_TEXT", "Enter the maximum number of relatives to include in AI context (1-50):")

    def _on_submit(entered_text):
        if entered_text:
            digits = re.findall(r"\d+", entered_text)
            if digits:
                try:
                    num = int(digits[0])
                    num = max(1, min(500, num))
                    set_genealogy_max_relatives(num)
                    notif_title = _t("GENEALOGY_TITLE", "Genealogy Settings")
                    notif_msg = f"{_t('GENEALOGY_ROW_MAX', '[123] Max Relatives in Context: {count}').format(count=num)}"
                    show_notification(
                        notif_title,
                        notif_msg,
                        sim_info=sim_info
                    )
                except Exception as e:
                    log_exception("Failed to parse genealogy max relatives", e)
        show_genealogy_menu(sim_info)

    def _on_cancel():
        show_genealogy_menu(sim_info)

    show_text_input_dialog(
        sim_info,
        title,
        text,
        str(current_max),
        _on_submit,
        on_cancel=_on_cancel,
    )


def show_genealogy_types_menu(sim_info):
    """Submenu for toggling individual relative types on or off."""
    is_en = _is_en()
    title = "Relative Types" if is_en else "Типы родственников"
    text = (
        "Click any item to instantly toggle [ON] / [OFF].\n"
        "Disabled relative types are excluded from the character context:"
        if is_en else
        "Нажмите на любой пункт для мгновенного переключения [ВКЛ] / [ВЫКЛ].\n"
        "Отключенные типы родни исключаются из контекста персонажа:"
    )

    defs = GENEALOGY_TYPE_DEFINITIONS_EN if is_en else GENEALOGY_TYPE_DEFINITIONS
    rows = []
    for type_key, type_name, type_desc in defs:
        enabled = get_genealogy_type_flag(type_key)
        if is_en:
            if enabled:
                row_title = f"[ON] {type_name}"
                row_desc = f"{type_desc}. (Click to turn OFF)"
            else:
                row_title = f"[OFF] {type_name}"
                row_desc = f"{type_desc}. (Click to turn ON)"
        else:
            if enabled:
                row_title = f"[ВКЛ] {type_name}"
                row_desc = f"{type_desc}. (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            else:
                row_title = f"[ВЫКЛ] {type_name}"
                row_desc = f"{type_desc}. (Нажмите, чтобы ВКЛЮЧИТЬ)"
        rows.append((row_title, row_desc, type_key, False))

    back_lbl = "<< Back" if is_en else "<< Назад"
    back_dsc = "Return to genealogy settings menu" if is_en else "Вернуться в меню настройки генеалогии"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select(tag):
        if tag == "back":
            show_genealogy_menu(sim_info)
        else:
            toggle_genealogy_type_flag(tag)
            show_genealogy_types_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 3. AUTONOMY SETTINGS
# =====================================================================

def show_autonomy_menu(sim_info):
    """Submenu for configuring autonomous thought generation."""
    is_en = _is_en()
    is_enabled = get_autonomy_enabled()
    interval = get_autonomy_interval()

    title = "Autonomous Thoughts" if is_en else "Автономные мысли"
    if is_en:
        status_str = "ENABLED" if is_enabled else "DISABLED"
        if interval >= 60:
            hrs = interval // 60
            if hrs == 24:
                interval_str = "every 24 hours (once daily)"
            elif hrs == 1:
                interval_str = "every hour (60 sim minutes)"
            else:
                interval_str = f"every {hrs} hrs ({interval} sim minutes)"
        else:
            interval_str = f"every {interval} sim minutes"

        text = (
            f"Current status: [{status_str}]\n"
            f"Generation interval: {interval_str}.\n\n"
            f"When enabled, Sims periodically generate thoughts autonomously in the background.\n"
            f"Select an option to apply immediately:"
        )
        toggle_title = "[DISABLE autonomy]" if is_enabled else "[ENABLE autonomy]"
        toggle_desc = f"Click to change autonomy mode (currently: {status_str})"

        def _mark_active(label, is_act):
            return f"[x] {label} (ACTIVE)" if is_act else f"[ ] {label}"

        rows = [
            (
                toggle_title,
                toggle_desc,
                "toggle",
                False,
            ),
            (
                _mark_active("Every hour (60 sim minutes)", interval == 60),
                "Generate thoughts every in-game hour",
                "set_60",
                False,
            ),
            (
                _mark_active("Every 4 hours (240 sim minutes) [Recommended]", interval == 240),
                "Balanced thought frequency",
                "set_240",
                False,
            ),
            (
                _mark_active("Every 8 hours (480 sim minutes)", interval == 480),
                "Generate thoughts 3 times per Sim day",
                "set_480",
                False,
            ),
            (
                _mark_active("Every 16 hours (960 sim minutes)", interval == 960),
                "Infrequent thought generation",
                "set_960",
                False,
            ),
            (
                _mark_active("Every 24 hours (Once daily)", interval == 1440),
                "Generate thoughts once per Sim day",
                "set_1440",
                False,
            ),
            (
                "<< Back to Main Menu",
                "Return to previous menu",
                "back",
                False,
            ),
        ]
    else:
        status_str = "ВКЛЮЧЕНА" if is_enabled else "ВЫКЛЮЧЕНА"
        if interval >= 60:
            hrs = interval // 60
            if hrs == 24:
                interval_str = "каждые 24 часа (раз в сутки)"
            elif hrs == 1:
                interval_str = "каждый час (60 сим-минут)"
            else:
                interval_str = f"каждые {hrs} ч. ({interval} сим-минут)"
        else:
            interval_str = f"каждые {interval} сим-минут"

        text = (
            f"Текущий статус: [{status_str}]\n"
            f"Интервал генерации: {interval_str}.\n\n"
            f"При включенной автономии персонаж периодически генерирует мысли в фоне без клика игрока.\n"
            f"Нажмите на нужный пункт для мгновенного применения:"
        )

        toggle_title = "[ВЫКЛЮЧИТЬ автономию]" if is_enabled else "[ВКЛЮЧИТЬ автономию]"
        toggle_desc = f"Нажмите для изменения режима (сейчас: {status_str})"

        def _mark_active(label, is_act):
            return f"[x] {label} (АКТИВНО)" if is_act else f"[ ] {label}"

        rows = [
            (
                toggle_title,
                toggle_desc,
                "toggle",
                False,
            ),
            (
                _mark_active("Каждый час (60 сим-минут)", interval == 60),
                "Генерация мыслей каждый игровой час",
                "set_60",
                False,
            ),
            (
                _mark_active("Каждые 4 часа (240 сим-минут) [Рекомендуется]", interval == 240),
                "Сбалансированная периодичность мыслей",
                "set_240",
                False,
            ),
            (
                _mark_active("Каждые 8 часов (480 сим-минут)", interval == 480),
                "Генерация мыслей 3 раза в игровые сутки",
                "set_480",
                False,
            ),
            (
                _mark_active("Каждые 16 часов (960 сим-минут)", interval == 960),
                "Редкая генерация мыслей",
                "set_960",
                False,
            ),
            (
                _mark_active("Каждые 24 часа (Раз в сутки)", interval == 1440),
                "Генерация мыслей один раз в игровые сутки",
                "set_1440",
                False,
            ),
            (
                "<< Назад в главное меню",
                "Вернуться в главное меню настроек",
                "back",
                False,
            ),
        ]

    def _on_select(tag):
        from .autonomy import update_autonomy_alarm
        if tag == "toggle":
            set_autonomy_enabled(not is_enabled)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "set_60":
            set_autonomy_interval(60)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "set_240":
            set_autonomy_interval(240)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "set_480":
            set_autonomy_interval(480)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "set_960":
            set_autonomy_interval(960)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "set_1440":
            set_autonomy_interval(1440)
            update_autonomy_alarm()
            show_autonomy_menu(sim_info)
        elif tag == "back":
            show_main_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 4. RECENT THOUGHTS JOURNAL
# =====================================================================

def show_recent_thoughts_menu(sim_info):
    """Submenu displaying the journal of recent thoughts from this game session."""
    is_en = _is_en()
    thoughts = get_recent_thoughts()
    title = _t("JOURNAL_TITLE", "Recent Thoughts Journal")

    back_lbl = _t("BTN_BACK", "<< Back to Main Menu")
    back_dsc = _t("BTN_BACK_DESC", "Return to previous menu")

    if not thoughts:
        text = _t("JOURNAL_EMPTY", "No thoughts have been recorded in this session yet.")
        rows = [
            (
                back_lbl,
                back_dsc,
                "back",
                False,
            )
        ]
    else:
        text = _t("JOURNAL_DESC_TEXT", "Select a Sim to view their recently generated thoughts:")
        rows = []
        def_name = _t("LABEL_CHARACTER", "Character")
        for idx, item in enumerate(thoughts):
            t_name = item.get("sim_name", def_name)
            t_time = item.get("time", "")
            t_thought = item.get("thought", "")

            preview = (t_thought[:65] + "...") if len(t_thought) > 65 else t_thought
            row_title = f"[{t_time}] {t_name}"
            rows.append((row_title, preview, idx, False))

        rows.append((
            back_lbl,
            back_dsc,
            "back",
            False,
        ))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        elif isinstance(tag, int) and 0 <= tag < len(thoughts):
            selected_item = thoughts[tag]
            s_name = selected_item.get("sim_name", _t("LABEL_CHARACTER", "Character"))
            s_time = selected_item.get("time", "")
            s_text = selected_item.get("thought", "")
            dlg_title = f"{_t('NOTIF_THOUGHT_TITLE', 'Sim Thoughts ({name})').format(name=s_name)} [{s_time}]"
            dlg_text = f"\"{s_text}\"" if is_en else f"«{s_text}»"
            show_info_dialog(
                sim_info,
                dlg_title,
                dlg_text,
                on_close=lambda: show_recent_thoughts_menu(sim_info),
            )

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 5. BRIDGE DIAGNOSTICS & STATUS
# =====================================================================

def show_diagnostics_menu(sim_info):
    """Submenu showing status of AI Bridge, active model, provider, and API key/URL."""
    # Force reload config from disk
    reload_config()

    bridge_ok, bridge_msg = check_bridge_health()
    api_key = get_api_key()
    provider_name, model_name, conn_mode = get_active_provider_info()
    effort = get_reasoning_effort()

    cfg = load_config()
    is_en = _is_en()
    if is_en:
        if conn_mode == "colab":
            colab_url = cfg.get("colab_url", "").strip()
            masked_key = (colab_url[:35] + "...") if len(colab_url) > 35 else (colab_url or "URL not specified")
            key_label = "Tunnel URL"
        elif conn_mode in ("local", "lmstudio", "ollama"):
            masked_key = cfg.get("local_url", "http://localhost:1234/v1").strip()
            key_label = "Local URL"
        else:
            key_label = "API Key"
            if api_key:
                masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 15 else "***"
            else:
                masked_key = "NOT SET (ai set_key <key>)"

        bridge_status = "[ONLINE (127.0.0.1:8765)]" if bridge_ok else "[OFFLINE]"
        title = "Connection Status & Diagnostics"
        text = (
            f"• AI Bridge:    {bridge_status}\n"
            f"• Provider:     {provider_name}\n"
            f"• Model:        {model_name}\n"
            f"• {key_label}:     {masked_key}\n"
            f"• Reasoning:    {effort}\n\n"
            f"If bridge is offline, make sure Synapse is running on your PC."
        )
        rows = [
            (
                "[+] Re-check Connection",
                "Reload updated config from Synapse and verify connection",
                "refresh",
                False,
            ),
            (
                "<< Back to Main Menu",
                "Return to previous menu",
                "back",
                False,
            ),
        ]
    else:
        if conn_mode == "colab":
            colab_url = cfg.get("colab_url", "").strip()
            masked_key = (colab_url[:35] + "...") if len(colab_url) > 35 else (colab_url or "URL не указан")
            key_label = "URL туннеля"
        elif conn_mode in ("local", "lmstudio", "ollama"):
            masked_key = cfg.get("local_url", "http://localhost:1234/v1").strip()
            key_label = "Локальный URL"
        else:
            key_label = "API-ключ"
            if api_key:
                masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 15 else "***"
            else:
                masked_key = "НЕ УСТАНОВЛЕН (ai set_key <ключ>)"

        bridge_status = "[РАБОТАЕТ (127.0.0.1:8765)]" if bridge_ok else "[НЕ ЗАПУЩЕН]"
        title = "Статус связи и диагностика"
        text = (
            f"• AI Bridge:    {bridge_status}\n"
            f"• Провайдер:    {provider_name}\n"
            f"• Модель:       {model_name}\n"
            f"• {key_label}:     {masked_key}\n"
            f"• Рассуждения:  {effort}\n\n"
            f"Если мост отключен, запустите Synapse на компьютере."
        )
        rows = [
            (
                "[+] Проверить подключение повторно",
                "Считать обновленный конфиг из Synapse и проверить связь",
                "refresh",
                False,
            ),
            (
                "<< Назад в главное меню",
                "Вернуться в главное меню настроек",
                "back",
                False,
            ),
        ]

    def _on_select(tag):
        if tag == "refresh":
            reload_config()
            b_ok, _ = check_bridge_health()
            p_name, m_name, _ = get_active_provider_info()
            if is_en:
                if b_ok:
                    show_notification(
                        "Synapse",
                        f"Connection active!\n• Provider: {p_name}\n• Model: {m_name}",
                        sim_info=sim_info,
                    )
                else:
                    show_notification(
                        "Synapse",
                        f"Config updated!\n• Provider: {p_name}\n• Model: {m_name}\n\n⚠️ AI Bridge is not running (127.0.0.1:8765).",
                        sim_info=sim_info,
                    )
            else:
                if b_ok:
                    show_notification(
                        "Synapse",
                        f"Подключение активно!\n• Провайдер: {p_name}\n• Модель: {m_name}",
                        sim_info=sim_info,
                    )
                else:
                    show_notification(
                        "Synapse",
                        f"Конфиг обновлен!\n• Провайдер: {p_name}\n• Модель: {m_name}\n\n⚠️ AI Bridge не запущен (127.0.0.1:8765).",
                        sim_info=sim_info,
                    )
            show_diagnostics_menu(sim_info)
        elif tag == "back":
            show_main_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


# =====================================================================
# 5b. EXPERIMENTAL FEATURES
# =====================================================================

EXPERIMENTAL_FLAG_DEFINITIONS = [
    (
        "direct_dialogue_pause",
        "Пауза и окно ожидания в живом разговоре",
        "Ставит игру на паузу и держит окно ожидания, пока ИИ генерирует реплику (собеседник не уйдёт)",
    ),
    (
        "alien_male_pregnancy",
        "Определение мужской беременности от инопланетян",
        "Если мужчина беременный, автоматически считается что это беременность от инопланетян после похищения",
    ),
    (
        "classic_insane_trait",
        "Классическое безумие для черты «Чудаковатый»",
        "Возвращает черте поведение «Безумный»: персонаж думает и общается намного хаотичнее, с паранойей и абсурдом",
    ),
    (
        "enhanced_world_descriptions",
        "Улучшенное описание городов",
        "Добавляет в контекст для ИИ подробное описание атмосферы, архитектуры и климата каждого города (Сулани, Винденбург и др.)",
    ),
]

EXPERIMENTAL_FLAG_DEFINITIONS_EN = [
    (
        "direct_dialogue_pause",
        "Pause & Waiting Dialog in Direct Dialogue",
        "Pauses the game and holds a waiting dialog while AI generates a line (keeps interlocutor from walking away)",
    ),
    (
        "alien_male_pregnancy",
        "Alien Male Pregnancy Detection",
        "If a male Sim is pregnant, automatically treat it as an alien pregnancy resulting from an abduction",
    ),
    (
        "classic_insane_trait",
        "Classic Insane Trait Behavior",
        "Restores classic 'Insane' trait behavior to Erratic Sims: thoughts and speech become much more chaotic, surreal, and paranoid",
    ),
    (
        "enhanced_world_descriptions",
        "Enhanced World Descriptions",
        "Adds rich atmospheric, architectural, and climate descriptions of each Sims 4 world to the AI context",
    ),
]


def show_experimental_menu(sim_info):
    """Submenu for toggling experimental gameplay features."""
    is_en = _is_en()
    title = "Experimental Features" if is_en else "Экспериментальные функции"
    text = (
        "Click any item to toggle [ON] / [OFF].\n"
        "Experimental AI gameplay mechanics:"
        if is_en else
        "Нажмите на пункт для переключения [ВКЛ] / [ВЫКЛ].\n"
        "Экспериментальные механики взаимодействия с ИИ:"
    )

    defs = EXPERIMENTAL_FLAG_DEFINITIONS_EN if is_en else EXPERIMENTAL_FLAG_DEFINITIONS
    rows = []
    for flag_key, flag_name, flag_desc in defs:
        enabled = get_experimental_flag(flag_key)
        if is_en:
            if enabled:
                row_title = f"[ON] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn OFF)"
            else:
                row_title = f"[OFF] {flag_name}"
                row_desc = f"{flag_desc}. (Click to turn ON)"
        else:
            if enabled:
                row_title = f"[ВКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВЫКЛЮЧИТЬ)"
            else:
                row_title = f"[ВЫКЛ] {flag_name}"
                row_desc = f"{flag_desc}. (Нажмите, чтобы ВКЛЮЧИТЬ)"
        rows.append((row_title, row_desc, flag_key, False))

    # WickedWhims Intimacy Mode Row
    cur_sex_mode = get_ww_sex_mode()
    sex_mode_display_ru = {
        "bed_picker": "Кровать (с выбором позы)",
        "nearby_picker": "Ближайший предмет (с выбором позы)",
        "auto_bed": "Кровать (случайная поза)",
        "auto_nearby": "Ближайший предмет (случайная поза)",
    }
    sex_mode_display_en = {
        "bed_picker": "Bed (with pose picker)",
        "nearby_picker": "Nearby object (with pose picker)",
        "auto_bed": "Bed (random pose)",
        "auto_nearby": "Nearby object (random pose)",
    }
    cur_display = sex_mode_display_en.get(cur_sex_mode, cur_sex_mode) if is_en else sex_mode_display_ru.get(cur_sex_mode, cur_sex_mode)
    ww_row_title = f"[WW] Режим интима: {cur_display}" if not is_en else f"[WW] Intimacy Mode: {cur_display}"
    ww_row_desc = "Настройка поведения при согласии на секс [DO=wicked_sex] (кровать/предмет, выбор позы/авто)" if not is_en else "Configure intimacy behavior upon consent [DO=wicked_sex] (bed/nearby, picker/auto)"
    rows.append((ww_row_title, ww_row_desc, "ww_sex_mode", False))

    back_lbl = "<< Back to Main Menu" if is_en else "<< Назад в главное меню"
    back_dsc = "Return to previous menu" if is_en else "Вернуться в главное меню настроек"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        elif tag == "ww_sex_mode":
            show_ww_intimacy_menu(sim_info)
        else:
            toggle_experimental_flag(tag)
            show_experimental_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)


def show_ww_intimacy_menu(sim_info):
    """Submenu for selecting WickedWhims intimacy action behavior."""
    is_en = _is_en()
    cur_mode = get_ww_sex_mode()
    title = "WickedWhims Intimacy Mode" if is_en else "Режим интима WickedWhims"
    text = (
        "Select how the mod executes intimacy when [DO=wicked_sex] is triggered in chat.\n"
        "Choose bed vs nearby object, and pose picker vs instant random pose:"
        if is_en else
        "Выберите поведение мода при согласии на интимную близость [DO=wicked_sex] в диалоге.\n"
        "Выбор кровати или ближайшего предмета, с меню выбора позы или авто-запуском:"
    )

    modes = [
        (
            "bed_picker",
            "Bed (with pose picker)" if is_en else "Кровать (с выбором позы)",
            "Finds a bed and opens WickedWhims pose selector" if is_en else "Ищет свободную кровать на лоте и открывает меню выбора позы WickedWhims",
        ),
        (
            "nearby_picker",
            "Nearby object (with pose picker)" if is_en else "Ближайший предмет (с выбором позы)",
            "Finds nearest object and opens pose selector" if is_en else "Ищет ближайший предмет (кровать, диван, пол и др.) и открывает меню выбора позы",
        ),
        (
            "auto_bed",
            "Bed (random pose / auto-start)" if is_en else "Кровать (случайная поза / авто-старт)",
            "Starts sex on bed immediately with a random animation" if is_en else "Сразу запускает секс на свободной кровати со случайной позой без дополнительных меню",
        ),
        (
            "auto_nearby",
            "Nearby object (random pose / auto-start)" if is_en else "Ближайший предмет (случайная поза / авто-старт)",
            "Starts sex on nearest object immediately with a random animation" if is_en else "Сразу запускает секс на ближайшем объекте со случайной позой без дополнительных меню",
        ),
    ]

    rows = []
    for mode_key, mode_title, mode_desc in modes:
        is_active = (cur_mode == mode_key)
        prefix = "[Active] " if (is_en and is_active) else ("[Активно] " if is_active else "")
        rows.append((f"{prefix}{mode_title}", mode_desc, mode_key, is_active))

    back_lbl = "<< Back to Experimental" if is_en else "<< Назад в Экспериментальное"
    back_dsc = "Return to experimental menu" if is_en else "Вернуться в раздел экспериментальных настроек"
    rows.append((back_lbl, back_dsc, "back", False))

    def _on_select_mode(tag):
        if tag == "back":
            show_experimental_menu(sim_info)
        elif tag in ("bed_picker", "nearby_picker", "auto_bed", "auto_nearby"):
            set_ww_sex_mode(tag)
            notif_title = "Synapse"
            if is_en:
                en_names = {
                    "bed_picker": "Bed (with pose picker)",
                    "nearby_picker": "Nearby object (with pose picker)",
                    "auto_bed": "Bed (random pose / auto-start)",
                    "auto_nearby": "Nearby object (random pose / auto-start)",
                }
                notif_msg = f"WickedWhims intimacy mode set to:\n{en_names.get(tag, tag)}"
            else:
                ru_names = {
                    "bed_picker": "Кровать (с выбором позы)",
                    "nearby_picker": "Ближайший предмет (с выбором позы)",
                    "auto_bed": "Кровать (случайная поза / авто-старт)",
                    "auto_nearby": "Ближайший предмет (случайная поза / авто-старт)",
                }
                notif_msg = f"Режим интима WickedWhims изменён на:\n{ru_names.get(tag, tag)}"
            show_notification(notif_title, notif_msg, sim_info=sim_info)
            show_experimental_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select_mode)


# =====================================================================
# 6. LANGUAGE SELECTION MENU
# =====================================================================

def show_language_menu(sim_info):
    """Submenu for selecting mod and context language."""
    from ai_thought_reader.localization import get_available_languages
    curr_lang = (get_language() or "en").lower().strip()
    is_en = _is_en()
    title = _t("LANG_MENU_TITLE", "Select Language / Выбор языка")
    text = (
        "Select interface and AI context language.\n"
        "Выберите язык интерфейса и контекста для персонажей.\n\n"
        f"Active Language: [{curr_lang.upper()}]"
    )

    avail_langs = get_available_languages()
    rows = []
    for code, d_name in avail_langs.items():
        is_active = (curr_lang == code)
        status_suffix = " (Active)" if (is_en and is_active) else (" (Активен)" if is_active else "")
        if code == "en":
            desc = "Native English context & UI for small and large AI models." if is_en else "Английский интерфейс и контекст для нейросетей."
        elif code == "ru":
            desc = "Russian interface and rich Russian-language context." if is_en else "Русский интерфейс и богатый русскоязычный контекст."
        else:
            desc = f"Custom translation ({code.upper()}) from Mods\\Synapse\\languages\\mod_strings\\"
        rows.append((f"{d_name}{status_suffix}", desc, code, is_active))

    rows.append((
        _t("BTN_BACK", "<< Back to Main Menu"),
        _t("BTN_BACK_DESC", "Return to previous menu"),
        "back",
        False,
    ))

    def _on_select(tag):
        if tag == "back":
            show_main_menu(sim_info)
        elif tag in avail_langs:
            set_language(tag)
            set_current_language(tag)
            d_name = avail_langs.get(tag, tag.upper())
            notif_msg = f"Language set to {d_name}!\nInterface and context updated." if is_en else f"Язык изменен на {d_name}!\nИнтерфейс и контекст обновлены."
            show_notification(
                "Synapse",
                notif_msg,
                sim_info=sim_info,
            )
            show_main_menu(sim_info)

    show_picker_dialog(sim_info, title, text, rows, _on_select)



