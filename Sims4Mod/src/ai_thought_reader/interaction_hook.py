try:
    import services
    import sims4.commands
except ImportError:
    services = None
    sims4 = None

from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.commands import execute_read_thoughts, execute_read_thoughts_ww

REGULAR_THOUGHT_AFFORDANCE_ID = 18298976728462081835
WW_THOUGHT_AFFORDANCE_IDS = {12182240539294674680, 15699576483586314424}
THOUGHT_AFFORDANCE_IDS = {REGULAR_THOUGHT_AFFORDANCE_ID} | WW_THOUGHT_AFFORDANCE_IDS


def _is_sim_in_active_sex(sim_obj):
    if sim_obj is None:
        return False
    if isinstance(sim_obj, int):
        if services is not None:
            try:
                sim_info = services.sim_info_manager().get(sim_obj)
            except Exception:
                sim_info = None
        else:
            sim_info = None
    else:
        sim_info = getattr(sim_obj, "sim_info", None) or (sim_obj if hasattr(sim_obj, "first_name") else None)
    if sim_info is None:
        return False
    try:
        from ai_thought_reader.context import get_sim_active_sex_info
        if get_sim_active_sex_info(sim_info) is not None:
            return True
    except Exception:
        pass
    sim_id = getattr(sim_info, "sim_id", None)
    try:
        from wickedwhims.sex.integral.sex_handlers.active_sex.active_sex_handlers import get_active_sex_instances
        active_instances = get_active_sex_instances()
        if active_instances:
            for inst in active_instances:
                if inst and hasattr(inst, "is_sim_id_in_instance") and inst.is_sim_id_in_instance(sim_id):
                    return True
    except Exception:
        pass
    try:
        from turbolib2.wrappers.sim.sim import TurboSim
        ts = TurboSim(sim_info)
        if ts and ts.get_temp_value("active_sex_instance", default=None) is not None:
            return True
    except Exception:
        pass
    return False


def _handle_capture(interaction_instance):
    """
    Extracts the target Sim and immediately triggers execute_read_thoughts or execute_read_thoughts_ww.
    """
    try:
        name = getattr(interaction_instance, "__name__", str(interaction_instance.__class__.__name__))
        guid64 = getattr(interaction_instance, "guid64", 0)
        log(f"[INTERACTION HOOK] Captured thought reading affordance execution: {name} (GUID: {guid64})")

        target = getattr(interaction_instance, "target", None)
        if target is None:
            target = getattr(interaction_instance, "sim", None)

        target_id = getattr(target, "sim_id", None) if target else None
        if target_id is None and hasattr(target, "id"):
            target_id = getattr(target, "id", None)

        if guid64 in WW_THOUGHT_AFFORDANCE_IDS or "ww" in name.lower():
            execute_read_thoughts_ww(target_id or target)
        else:
            execute_read_thoughts(target_id or target)
    except Exception as ex:
        log_exception("Error in thought interaction capture handler", ex)


def patch_specific_affordance(aff_cls):
    """
    Hooks visibility test directly on the specific affordance class (18298976728462081835 / 15699576483586314424).
    IMPORTANT: Execution is handled cleanly by the tuning's basic_extras (do_command ai_read / ai_read_ww).
    We do NOT override _run_interaction_gen to prevent duplicate executions!
    """
    if aff_cls is None:
        return
    if getattr(aff_cls, "_synapse_aff_hooked", False):
        return

    try:
        guid64 = getattr(aff_cls, "guid64", 0)
        is_ww = guid64 in WW_THOUGHT_AFFORDANCE_IDS or "ww" in getattr(aff_cls, "__name__", "").lower()

        try:
            from sims4.utils import flexmethod
            from event_testing.results import TestResult
        except ImportError:
            flexmethod = lambda f: f
            TestResult = None

        if is_ww:
            @flexmethod
            def _ww_aff_test(cls, inst, target=None, context=None, **kwargs):
                try:
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

            aff_cls.test = _ww_aff_test
            aff_cls._test = _ww_aff_test
        else:
            @flexmethod
            def _regular_aff_test(cls, inst, target=None, context=None, **kwargs):
                try:
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

            aff_cls.test = _regular_aff_test
            aff_cls._test = _regular_aff_test

        aff_cls._synapse_aff_hooked = True
        log(f"[INTERACTION HOOK] Successfully hooked custom generator and test on affordance {getattr(aff_cls, '__name__', aff_cls)} (ID: {guid64}, is_ww={is_ww})!")
    except Exception as e:
        log_exception("Failed to hook affordance methods", e)


def patch_ai_interactions():
    """
    Finds our tuned affordances in the affordance manager and patches them individually.
    Zero touch on base game classes!
    """
    if services is None:
        return False
    try:
        aff_mgr = services.affordance_manager()
        if aff_mgr is None:
            return False

        patched_count = 0
        for aff_id in THOUGHT_AFFORDANCE_IDS:
            aff_cls = aff_mgr.get(aff_id)
            if aff_cls is not None:
                patch_specific_affordance(aff_cls)
                patched_count += 1
        if patched_count > 0:
            log(f"[INTERACTION HOOK] Patched {patched_count} affordances in affordance_manager.")
        return patched_count > 0
    except Exception as e:
        log_exception("Error in patch_ai_interactions", e)
        return False


