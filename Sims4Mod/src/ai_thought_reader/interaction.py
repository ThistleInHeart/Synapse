import time
from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.context import build_sim_prompt
from ai_thought_reader.client import request_ai_thought_async, check_bridge_health
from ai_thought_reader.config import add_recent_thought
from ai_thought_reader.ui_helper import (
    show_notification,
    show_sim_thought_notification,
    show_error_notification,
)

try:
    import services
    from interactions.base.immediate_interaction import ImmediateSuperInteraction
    from sims4.utils import flexmethod
    from event_testing.results import TestResult
    from sims4.localization import LocalizationHelperTuning
    from interactions.base.interaction import Interaction
    from interactions.context import InteractionContext
except ImportError:
    services = None
    ImmediateSuperInteraction = object
    flexmethod = lambda f: f
    TestResult = None
    LocalizationHelperTuning = None
    Interaction = object
    InteractionContext = None


try:
    from ai_thought_reader.localization import _t
except ImportError:
    _t = lambda k, d=None: d or k

_PENDING_REQUEST_SIM_IDS = set()
_LAST_REQUEST_SIM_TIME = {}


def _is_en() -> bool:
    try:
        from ai_thought_reader.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False


class AIReadThoughtsInteraction(ImmediateSuperInteraction):
    """
    Immediate Super Interaction displayed on Sims in the Pie Menu.
    Triggered immediately upon clicking without queuing an animation.
    """
    INSTANCE_SUBCLASSES_ONLY = True
    _tuning_id = 18298976728462081835
    guid64 = 18298976728462081835
    allow_autonomous = False
    allow_user_directed = True
    simless = True
    pie_menu_priority = 10
    category = None

    @classmethod
    def get_name(cls, target=None, context=None, **kwargs):
        name = _t("PIE_READ_THOUGHTS", "Прочитать мысли (AI)")
        if LocalizationHelperTuning is not None:
            return LocalizationHelperTuning.get_raw_text(name)
        return name

    @classmethod
    def _display_name(cls, *args, **kwargs):
        name = _t("PIE_READ_THOUGHTS", "Прочитать мысли (AI)")
        if LocalizationHelperTuning is not None:
            return LocalizationHelperTuning.get_raw_text(name)
        return name

    @flexmethod
    def _test(cls, inst, target=None, context=None, **kwargs):
        try:
            from ai_thought_reader.interaction_hook import _is_sim_in_active_sex
            tgt = target
            if tgt is None and context is not None:
                tgt = getattr(context, "target", None)
            if tgt is None and inst is not None:
                tgt = getattr(inst, "target", None)
            if tgt is None and context is not None:
                tgt = getattr(context, "sim", None)
            if tgt is None and inst is not None:
                tgt = getattr(inst, "sim", None)

            if tgt is not None and _is_sim_in_active_sex(tgt):
                return TestResult.NONE if TestResult else False
        except Exception:
            pass
        return TestResult.TRUE if TestResult else True

    test = _test

    def _run_interaction_gen(self, timeline):
        try:
            self._execute_read_action()
        except Exception as e:
            log_exception("Exception in AIReadThoughtsInteraction._run_interaction_gen", e)
        return True
        yield

    def _run_interaction(self):
        return self._execute_read_action()

    def _execute_read_action(self):
        try:
            target = self.target
            if target is None:
                target = self.sim

            if target is None:
                log("[INTERACTION] Target is None.")
                return False

            sim_info = getattr(target, "sim_info", None)
            if sim_info is None and hasattr(target, "get_sim_info"):
                sim_info = target.get_sim_info()

            if sim_info is None:
                log("[INTERACTION] Could not obtain sim_info from target.")
                return False

            is_pet = getattr(sim_info, "is_pet", False)
            f_name = getattr(sim_info, "first_name", "") or ""
            l_name = getattr(sim_info, "last_name", "") or ""
            is_en_name = _is_en()
            def_name = ("Pet" if is_en_name else "Питомец") if is_pet else ("Sim" if is_en_name else "Персонаж")
            sim_name = f"{f_name} {l_name}".strip() if (f_name or l_name) else def_name
            log(f"[INTERACTION] 'Прочитать мысли' triggered on: {sim_name} (is_pet={is_pet})")


            sim_id = getattr(sim_info, "sim_id", None)
            now = time.time()
            if sim_id and sim_id in _PENDING_REQUEST_SIM_IDS:
                last_req = _LAST_REQUEST_SIM_TIME.get(sim_id, 0.0)
                if (now - last_req) < 20.0:
                    is_en = _is_en()
                    w_title = "Please wait..." if is_en else "Подождите..."
                    w_msg = f"{sim_name}'s thoughts are currently being processed. Please wait for the reply!" if is_en else f"Мысли {sim_name} уже обрабатываются нейросетью. Пожалуйста, подождите ответ!"
                    show_notification(
                        w_title,
                        w_msg,
                        sim_info=sim_info,
                        is_error=False,
                    )
                    return False
                else:
                    _PENDING_REQUEST_SIM_IDS.discard(sim_id)

            bridge_ok, _ = check_bridge_health()
            if not bridge_ok:
                is_en = _is_en()
                msg = "AI Bridge is not running! Please start Synapse." if is_en else "AI Bridge не запущен! Запустите Synapse или файл 'run_bridge.bat'."
                show_error_notification(msg)
                return False

            if sim_id:
                _PENDING_REQUEST_SIM_IDS.add(sim_id)
                _LAST_REQUEST_SIM_TIME[sim_id] = now

            # Instant UI feedback
            is_en = _is_en()
            if is_en:
                notice_title = "Reading Thoughts..."
                notice_msg = f"Connecting to {sim_name}'s thoughts..." if is_pet else f"Connecting to {sim_name}'s inner voice..."
            else:
                notice_title = "Считывание мыслей..."
                notice_msg = f"Связываемся с мыслями питомца {sim_name}..." if is_pet else f"Связываемся с внутренним голосом {sim_name}..."
            show_notification(
                notice_title,
                notice_msg,
                sim_info=sim_info,
                is_error=False,
            )

            # Build prompt
            try:
                prompt = build_sim_prompt(sim_info)
            except Exception as ex_prompt:
                log_exception("Error in build_sim_prompt for AIReadThoughtsInteraction", ex_prompt)
                if sim_id:
                    _PENDING_REQUEST_SIM_IDS.discard(sim_id)
                err_msg = f"Error building thought prompt: {ex_prompt}" if is_en else f"Ошибка составления контекста мыслей: {ex_prompt}"
                show_error_notification(err_msg)
                return False

            # Request thought via Bridge
            def _on_thought_ready(thought, success):
                try:
                    if sim_id:
                        _PENDING_REQUEST_SIM_IDS.discard(sim_id)
                    if success:
                        log(f"[INTERACTION SUCCESS] {sim_name} thinks: '{thought}'")
                        try:
                            add_recent_thought(sim_name, thought)
                        except Exception:
                            pass
                        show_sim_thought_notification(sim_info, thought)
                    else:
                        log(f"[INTERACTION ERROR] {thought}", level="ERROR")
                        show_error_notification(thought)
                except Exception as ex:
                    log_exception("Exception in _on_thought_ready", ex)
                finally:
                    if sim_id:
                        _PENDING_REQUEST_SIM_IDS.discard(sim_id)

            try:
                request_ai_thought_async(prompt, sim_name, _on_thought_ready)
                return True
            except Exception as ex_req:
                log_exception("Error in request_ai_thought_async for AIReadThoughtsInteraction", ex_req)
                if sim_id:
                    _PENDING_REQUEST_SIM_IDS.discard(sim_id)
                show_error_notification(str(ex_req))
                return False

        except Exception as e:
            log_exception("Exception during AIReadThoughtsInteraction execution", e)
            return False


class AIReadThoughtsWWInteraction(ImmediateSuperInteraction):
    """
    Immediate Super Interaction displayed on Sims during intimacy/sex (WickedWhims / WooHoo).
    In-game display name is identical to the normal interaction ("Прочитать мысли (AI)"),
    while in code and categorization it is dedicated to WickedWhims intimacy ("прочитать мысли ww").
    """
    INSTANCE_SUBCLASSES_ONLY = True
    _tuning_id = 15699576483586314424
    guid64 = 15699576483586314424
    allow_autonomous = False
    allow_user_directed = True
    simless = True
    pie_menu_priority = 20
    category = 16004868385894589359  # TURBODRIVER:WickedWhims_Wicked_Parent

    @classmethod
    def get_name(cls, target=None, context=None, **kwargs):
        name = _t("PIE_READ_THOUGHTS", "Прочитать мысли (AI)")
        if LocalizationHelperTuning is not None:
            return LocalizationHelperTuning.get_raw_text(name)
        return name

    @classmethod
    def _display_name(cls, *args, **kwargs):
        name = _t("PIE_READ_THOUGHTS", "Прочитать мысли (AI)")
        if LocalizationHelperTuning is not None:
            return LocalizationHelperTuning.get_raw_text(name)
        return name

    @flexmethod
    def _test(cls, inst, target=None, context=None, **kwargs):
        try:
            from ai_thought_reader.interaction_hook import _is_sim_in_active_sex
            tgt = target
            if tgt is None and context is not None:
                tgt = getattr(context, "target", None)
            if tgt is None and inst is not None:
                tgt = getattr(inst, "target", None)
            if tgt is None and context is not None:
                tgt = getattr(context, "sim", None)
            if tgt is None and inst is not None:
                tgt = getattr(inst, "sim", None)

            if tgt is not None and _is_sim_in_active_sex(tgt):
                return TestResult.TRUE if TestResult else True
        except Exception:
            pass
        return TestResult.NONE if TestResult else False

    test = _test

    def _run_interaction_gen(self, timeline):
        try:
            self._execute_read_action_ww()
        except Exception as e:
            log_exception("Exception in AIReadThoughtsWWInteraction._run_interaction_gen", e)
        return True
        yield

    def _run_interaction(self):
        return self._execute_read_action_ww()

    def _execute_read_action_ww(self):
        try:
            target = self.target
            if target is None:
                target = self.sim

            if target is None:
                log("[INTERACTION WW] Target is None.")
                return False

            sim_info = getattr(target, "sim_info", None)
            if sim_info is None and hasattr(target, "get_sim_info"):
                sim_info = target.get_sim_info()

            if sim_info is None:
                log("[INTERACTION WW] Could not obtain sim_info from target.")
                return False

            from ai_thought_reader.commands import execute_read_thoughts_ww
            return execute_read_thoughts_ww(sim_info)
        except Exception as e:
            log_exception("Exception during AIReadThoughtsWWInteraction execution", e)
            return False


