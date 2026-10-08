from ai_thought_reader.logger import log, log_exception

try:
    import services
    from ui.ui_dialog_notification import UiDialogNotification
    from sims4.localization import LocalizationHelperTuning
    from distributor.shared_messages import IconInfoData
except ImportError:
    services = None
    UiDialogNotification = None
    LocalizationHelperTuning = None
    IconInfoData = None


def show_notification(title: str, text: str, sim_info=None, is_error: bool = False):
    """
    Displays an in-game notification popup in the top right corner.
    Rock-solid implementation with zero NoneType errors.
    """
    try:
        if services is None or UiDialogNotification is None or LocalizationHelperTuning is None:
            log(f"[UI FALLBACK] {title}: {text}")
            return

        client = services.client_manager().get_first_client()
        if client is None:
            log("[UI] No active game client found to display notification.")
            return

        active_sim = client.active_sim
        active_sim_info = getattr(client, "active_sim_info", None)
        if active_sim_info is None and active_sim is not None:
            active_sim_info = getattr(active_sim, "sim_info", None)

        if active_sim is None and active_sim_info is None:
            log("[UI] No active sim found for dialog context.")
            return

        # Target owner for the dialog
        owner = sim_info if sim_info is not None else (active_sim_info if active_sim_info is not None else active_sim)

        loc_title = LocalizationHelperTuning.get_raw_text(title)
        loc_text = LocalizationHelperTuning.get_raw_text(text)

        # Visual type (SPECIAL_MOMENT for thoughts, INFORMATION for errors/tests)
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

        # Show notification with Sim portrait
        try:
            if sim_info is not None and IconInfoData is not None:
                icon_obj = IconInfoData(obj_instance=sim_info)
                notification.show_dialog(icon_override=icon_obj)
            elif active_sim_info is not None and IconInfoData is not None:
                icon_obj = IconInfoData(obj_instance=active_sim_info)
                notification.show_dialog(icon_override=icon_obj)
            else:
                notification.show_dialog()
        except Exception as ie:
            log(f"[UI] icon_override failed ({ie}), falling back to default show_dialog")
            try:
                notification.show_dialog()
            except Exception as ie2:
                log_exception("Default show_dialog failed", ie2)
                return

        log(f"[UI SUCCESS] Notification displayed: '{title}' -> '{text[:60]}...'")

    except Exception as e:
        log_exception("Failed to show UI notification", e)


def show_sim_thought_notification(sim_info, thought: str):
    """Shows the generated thought with the Sim's name and portrait."""
    is_en = False
    try:
        from ai_thought_reader.localization import get_game_language
        is_en = (get_game_language() == "en")
    except Exception:
        is_en = False

    default_name = "Sim" if is_en else "Сим"
    sim_name = f"{sim_info.first_name} {sim_info.last_name}".strip() if sim_info else default_name
    title = f"Thoughts: {sim_name}" if is_en else f"Мысли: {sim_name}"
    formatted_thought = f"\"{thought}\"" if is_en else f"«{thought}»"
    show_notification(title, formatted_thought, sim_info=sim_info, is_error=False)


def show_error_notification(error_msg: str):
    """Shows an error notification."""
    title = "Synapse"
    show_notification(title, error_msg, sim_info=None, is_error=True)
