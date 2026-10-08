from ai_thought_reader import __version__
from ai_thought_reader.logger import log, log_exception
from ai_thought_reader.config import load_config, get_api_key, get_model
from ai_thought_reader.injector import inject
from ai_thought_reader.interaction import AIReadThoughtsInteraction, AIReadThoughtsWWInteraction
import ai_thought_reader.commands
from ai_thought_reader.interaction_hook import patch_ai_interactions

from ai_thought_reader.lore_manager import (
    load_lore_data,
    commit_lore_data_to_disk,
    reset_working_lore_cache,
)
from ai_thought_reader.main_thread import process_main_thread_queue

try:
    import services
except ImportError:
    services = None

try:
    from sims.sim import Sim
except ImportError:
    Sim = None

try:
    from objects.definition_manager import DefinitionManager
except ImportError:
    DefinitionManager = object

try:
    import zone
except ImportError:
    zone = None

try:
    from services.persistence_service import PersistenceService
except ImportError:
    PersistenceService = None

OBJECT_SIM = 14965  # Sim Object Definition ID (Human) in The Sims 4
OBJECT_CAT_1 = 120619
OBJECT_CAT_2 = 120620
OBJECT_DOG_1 = 120621
OBJECT_DOG_2 = 174619
OBJECT_CAT_LEGACY = 153073
OBJECT_DOG_LEGACY = 153074
OBJECT_SMALL_DOG_LEGACY = 153075

SIM_DEFINITION_IDS = (
    OBJECT_SIM,
    OBJECT_CAT_1,
    OBJECT_CAT_2,
    OBJECT_DOG_1,
    OBJECT_DOG_2,
    OBJECT_CAT_LEGACY,
    OBJECT_DOG_LEGACY,
    OBJECT_SMALL_DOG_LEGACY,
)

S4S_AFFORDANCE_ID = 18298976728462081835
WW_AFFORDANCE_IDS = (12182240539294674680, 15699576483586314424)
ALL_AFFORDANCE_IDS = (S4S_AFFORDANCE_ID,) + WW_AFFORDANCE_IDS


def whitelist_interactions_in_wickedwhims():
    """
    Ensures WickedWhims doesn't block our thought reading interactions during sex.
    Adds ONLY the WW affordance to SEX_ALLOWED_VANILLA_INTERACTIONS with _AllowedDirectionality.ALLOWED.
    The regular thought interaction is intentionally NOT whitelisted so WW hides it during sex!
    """
    try:
        from wickedwhims.sex.integral.sex_handlers._ts4_interactions_blocking import (
            SEX_ALLOWED_VANILLA_INTERACTIONS,
            _AllowedDirectionality,
        )
        for aff_id in WW_AFFORDANCE_IDS:
            SEX_ALLOWED_VANILLA_INTERACTIONS[aff_id] = _AllowedDirectionality.ALLOWED
            log(f"[WW HOOK] Whitelisted WW affordance {aff_id} in WickedWhims SEX_ALLOWED_VANILLA_INTERACTIONS!")
    except Exception:
        pass


def get_affordances_to_inject():
    """Returns affordances that need to be injected (prefers S4S package tunings)."""
    affs = []
    if services is not None:
        try:
            aff_mgr = services.affordance_manager()
            if aff_mgr is not None:
                for a_id in ALL_AFFORDANCE_IDS:
                    s4s_aff = aff_mgr.get(a_id)
                    if s4s_aff is not None:
                        try:
                            setattr(s4s_aff, "simless", True)
                            setattr(s4s_aff, "allow_user_directed", True)
                            if a_id in WW_AFFORDANCE_IDS:
                                if hasattr(s4s_aff, "test_globals") and s4s_aff.test_globals is not None:
                                    s4s_aff.test_globals = [t for t in s4s_aff.test_globals if "IsNotInSex" not in str(type(t))]
                        except Exception:
                            pass
                        try:
                            from ai_thought_reader.interaction_hook import patch_specific_affordance
                            patch_specific_affordance(s4s_aff)
                        except Exception as ex_p:
                            log_exception(f"Error patching s4s affordance {a_id}", ex_p)
                        if s4s_aff not in affs:
                            affs.append(s4s_aff)
        except Exception as e:
            log_exception("Error fetching S4S affordances", e)

    # Fallback to pure Python classes only if package tunings are not present!
    if not affs:
        affs = [AIReadThoughtsInteraction, AIReadThoughtsWWInteraction]
    return affs


def inject_to_sim_definition():
    """Injects affordances into the Sim and Pet Object Definitions."""
    if services is None:
        return
    try:
        def_manager = services.definition_manager()
        if def_manager is None:
            return
        affordances = get_affordances_to_inject()
        for def_id in SIM_DEFINITION_IDS:
            try:
                obj_def = super(DefinitionManager, def_manager).get(def_id) if DefinitionManager is not object else def_manager.get(def_id)
                if obj_def is not None and hasattr(obj_def, "_super_affordances"):
                    current = list(obj_def._super_affordances)
                    for aff in affordances:
                        if aff not in current:
                            current.append(aff)
                            log(f"[INJECT] Added {getattr(aff, '__name__', aff)} to obj_def {def_id}!")
                    obj_def._super_affordances = tuple(current)
            except Exception as ex_id:
                log(f"[INJECT] Notice: Definition ID {def_id} not loaded or not in pack: {ex_id}")
    except Exception as e:
        log_exception("Failed to inject to Sim/Pet object definitions", e)


def register_affordance_globally():
    """Adds affordances to Sim class tuple (applies to all Sims, Cats, Dogs, Horses)."""
    if Sim is not None:
        try:
            if hasattr(Sim, "_super_affordances"):
                current_affordances = list(Sim._super_affordances)
                for aff in get_affordances_to_inject():
                    if aff not in current_affordances:
                        current_affordances.append(aff)
                        log(f"[INIT] Added {getattr(aff, '__name__', aff)} to Sim._super_affordances!")
                Sim._super_affordances = tuple(current_affordances)
        except Exception as e:
            log_exception("Failed to inject to Sim._super_affordances", e)


def attach_interaction_to_sim(sim_instance):
    """Safely adds AI interactions to a Sim or Pet's interaction set."""
    if sim_instance is None:
        return
    try:
        if hasattr(sim_instance, "add_super_interaction"):
            for aff in get_affordances_to_inject():
                sim_instance.add_super_interaction(aff)
    except Exception as e:
        log_exception("Failed to attach interaction to Sim instance", e)


def attach_to_all_spawned_sims():
    """Iterates through all currently spawned Sims in the active zone and attaches the interaction."""
    if services is None:
        return
    try:
        inject_to_sim_definition()
        register_affordance_globally()
        patch_ai_interactions()
        whitelist_interactions_in_wickedwhims()

        sim_info_manager = services.sim_info_manager()
        if sim_info_manager is not None:
            count = 0
            for sim_info in sim_info_manager.values():
                sim_instance = sim_info.get_sim_instance()
                if sim_instance is not None:
                    attach_interaction_to_sim(sim_instance)
                    count += 1
            log(f"[ZONE] Attached AI interaction to {count} active Sim(s).")
    except Exception as e:
        log_exception("Failed attaching to all spawned sims", e)


# Class-level affordance registration
register_affordance_globally()
patch_ai_interactions()
whitelist_interactions_in_wickedwhims()



def on_game_saved(slot_id=None):
    """Triggered whenever a real game save occurs to commit lore to disk."""
    try:
        log(f"[SAVE HOOK] Game save event detected (slot_id={slot_id})! Committing lore to disk...")
        commit_lore_data_to_disk()
    except Exception as e:
        log_exception("Error committing lore data on game save", e)


# Inject into Zone load & teardown
if zone is not None and hasattr(zone, "Zone"):
    if hasattr(zone.Zone, "load_zone"):
        @inject(zone.Zone, "load_zone")
        def _on_zone_load(original, self, *args, **kwargs):
            try:
                patch_ai_interactions()
            except Exception:
                pass
            return original(self, *args, **kwargs)

    @inject(zone.Zone, "on_loading_screen_animation_finished")
    def _on_zone_load_finished(original, self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            log("[ZONE] Loading screen finished. Injecting to definitions and Sims...")
            attach_to_all_spawned_sims()

            # Warm up lore cache for the active save slot
            try:
                load_lore_data()
            except Exception as e_lore:
                log_exception("Error initializing lore data on zone load", e_lore)

            # Register manual save callback on persistence service if available
            if services is not None:
                try:
                    ps = services.get_persistence_service()
                    if ps is not None and hasattr(ps, "add_manual_save_complete_callback"):
                        if not getattr(ps, "_aithoughtreader_save_cb_registered", False):
                            ps.add_manual_save_complete_callback(lambda: on_game_saved("manual"))
                            ps._aithoughtreader_save_cb_registered = True
                            log("[SAVE HOOK] Registered add_manual_save_complete_callback for lore.")
                except Exception as ex_ps:
                    log_exception("Error registering manual save callback for lore", ex_ps)

            try:
                from ai_thought_reader.autonomy import update_autonomy_alarm
                update_autonomy_alarm()
            except Exception as e_auto:
                log_exception("Error initializing autonomy alarm on zone load", e_auto)

            # Ensure AI Bridge is alive when loading into a lot
            try:
                from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
                ensure_bridge_running_async()
            except Exception:
                pass
        except Exception as e:
            log_exception("Error in on_loading_screen_animation_finished", e)
        return result

    @inject(zone.Zone, "update")
    def _on_zone_update(original, self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            process_main_thread_queue()
        except Exception as e:
            log_exception("Error in AIThoughtReader Zone.update", e)
        return result

    @inject(zone.Zone, "on_teardown")
    def _on_zone_teardown(original, self, *args, **kwargs):
        try:
            log("[ZONE] Zone teardown detected. Flushing dirty lore cache to disk before unload...")
            try:
                commit_lore_data_to_disk()
            except Exception as e_flush:
                log_exception("Error flushing lore cache on zone teardown", e_flush)

            reset_working_lore_cache()
        except Exception as ex_td:
            log_exception("Error during zone teardown cleanup in AIThoughtReader", ex_td)
        return original(self, *args, **kwargs)





try:
    from interactions.interaction_instance_manager import InteractionInstanceManager
    if InteractionInstanceManager is not None and hasattr(InteractionInstanceManager, "on_start"):
        @inject(InteractionInstanceManager, "on_start")
        def _on_interaction_manager_start(original, self, *args, **kwargs):
            res = original(self, *args, **kwargs)
            try:
                patch_ai_interactions()
                whitelist_interactions_in_wickedwhims()
            except Exception as e_im:
                log_exception("Error in InteractionInstanceManager.on_start hook", e_im)
            return res
except Exception:
    pass


def init_mod():
    log(f"================================================")
    log(f" AI Mind Reader v{__version__} loaded! (Direct UI Notification)")
    cfg = load_config()
    key = get_api_key()
    model = get_model()
    log(f" Active Model: {model}")
    log(f" API Key Status: {'Configured' if key else 'NOT CONFIGURED'}")
    patch_ai_interactions()

    # Automatically check and launch the Synapse AI Bridge console if offline
    try:
        from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
        ensure_bridge_running_async()
    except Exception as e_auto:
        log_exception("Failed to launch bridge autostart from init_mod", e_auto)

    log(f"================================================")


init_mod()
