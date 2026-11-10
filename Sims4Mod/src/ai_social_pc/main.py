import time
from ai_social_pc import __version__
from ai_social_pc.logger import log, log_exception
from ai_social_pc.injector import inject
from ai_social_pc.computer_interaction import (
    patch_computer_interactions,
    inject_affordance_into_computers,
    inject_affordance_into_phone,
)
from ai_social_pc.group_manager import (
    load_groups_data,
    commit_groups_data_to_disk,
    reset_working_cache,
    get_current_save_id,
)
from ai_social_pc.memory_manager import (
    load_memories,
    commit_memories_to_disk,
    reset_memories_cache,
)
from ai_social_pc.chat_manager import (
    load_contacts_data,
    commit_contacts_to_disk,
    reset_contacts_cache,
    load_chats_data,
    commit_chats_to_disk,
    reset_chats_cache,
)
from ai_social_pc.main_thread import process_main_thread_queue
from ai_social_pc.delayed_replies import on_zone_update_check
from ai_social_pc.npc_autonomy import stop_npc_group_autonomy_alarm
from ai_social_pc.friend_autonomy import stop_friend_autonomy_alarm
import ai_social_pc.commands

try:
    import services
    import zone
    from services.persistence_service import PersistenceService
    from relationships.relationship_service import RelationshipService
except ImportError:
    services = None
    zone = None
    PersistenceService = None
    RelationshipService = None


def on_game_saved(slot_id=None):
    """Triggered whenever a real game save occurs to commit mod data to disk."""
    try:
        log(f"[SAVE HOOK] Game save event detected (slot_id={slot_id})! Committing groups, chats, memories & contacts to disk...")
        commit_groups_data_to_disk()
        commit_chats_to_disk()
        commit_memories_to_disk()
        commit_contacts_to_disk()
    except Exception as e:
        log_exception("Error committing mod data on game save", e)


def on_zone_load():
    """Triggered on zone load to inject AI PC Messenger into computers and phone, and start delayed replies alarm."""
    try:
        # 1. Warm up caches for the current save slot
        cur_save = get_current_save_id()
        load_groups_data()
        load_chats_data()
        load_memories()
        load_contacts_data()
        log(f"[ZONE] Initialized mod caches for active save slot: {cur_save}")

        # 2. Register manual save callback on persistence service if available
        if services is not None:
            try:
                ps = services.get_persistence_service()
                if ps is not None and hasattr(ps, "add_manual_save_complete_callback"):
                    if not getattr(ps, "_aisocialpc_save_cb_registered", False):
                        ps.add_manual_save_complete_callback(lambda: on_game_saved("manual"))
                        ps._aisocialpc_save_cb_registered = True
                        log("[SAVE HOOK] Registered add_manual_save_complete_callback.")
            except Exception as ex_ps:
                log_exception("Error registering manual save callback", ex_ps)

        # 3. Inject affordances into computers
        log("[ZONE] Injecting AISocialPC affordances into computers...")
        count = inject_affordance_into_computers()
        log(f"[ZONE] Injection complete. {count} computer definition(s) updated.")

        # 4. Inject phone affordance
        log("[ZONE] Injecting phone affordance...")
        phone_ok = inject_affordance_into_phone()
        log(f"[ZONE] Phone injection result: {phone_ok}")

        # 5. Start delayed replies system
        from ai_social_pc.delayed_replies import start_delayed_replies_alarm, check_and_process_pending_replies
        start_delayed_replies_alarm()
        check_and_process_pending_replies(force_all=False)

        # 6. Start NPC group autonomy system
        try:
            from ai_social_pc.npc_autonomy import start_npc_group_autonomy_alarm
            start_npc_group_autonomy_alarm()
        except Exception as e_npc:
            log_exception("Error starting NPC group autonomy alarm", e_npc)

        # 7. Start Friend 1-on-1 autonomy system
        try:
            from ai_social_pc.friend_autonomy import start_friend_autonomy_alarm
            start_friend_autonomy_alarm()
        except Exception as e_fa:
            log_exception("Error starting friend autonomy alarm", e_fa)

        # 8. Verify and hook Direct Dialogue interactions (regular & WickedWhims intimacy)
        try:
            from ai_social_pc.direct_dialogue import (
                SYNAPSE_DIRECT_DIALOGUE_TUNING_ID,
                SYNAPSE_DIRECT_DIALOGUE_WW_TUNING_ID,
                hook_direct_dialogue_affordance,
            make_custom_mixers_sub_interactions_only,
            )
            aff_mgr = services.affordance_manager()
            if aff_mgr is not None:
                dd_aff = aff_mgr.get(SYNAPSE_DIRECT_DIALOGUE_TUNING_ID)
                if dd_aff is not None:
                    hook_direct_dialogue_affordance(dd_aff, is_ww=False)
                    log(f"[ZONE] Found and hooked Direct Dialogue affordance: {dd_aff} ({SYNAPSE_DIRECT_DIALOGUE_TUNING_ID})")
                dd_ww_aff = aff_mgr.get(SYNAPSE_DIRECT_DIALOGUE_WW_TUNING_ID)
                if dd_ww_aff is not None:
                    hook_direct_dialogue_affordance(dd_ww_aff, is_ww=True)
                    log(f"[ZONE] Found and hooked WW Intimate Dialogue affordance: {dd_ww_aff} ({SYNAPSE_DIRECT_DIALOGUE_WW_TUNING_ID})")
                make_custom_mixers_sub_interactions_only()
        except Exception as e_dd:
            log_exception("Error checking direct dialogue affordance", e_dd)

        # 9. Install native travel commands hook (prevents infinite loading screens)
        try:
            from ai_social_pc.action_executor import hook_travel_commands
            hook_travel_commands()
        except Exception as e_th:
            log_exception("Error initializing travel hook", e_th)

        # 10. Hook vanilla social mixer interactions for autonomous living dialogue
        try:
            from ai_social_pc.autonomous_director import hook_vanilla_social_mixer
            hook_vanilla_social_mixer()
        except Exception as e_vsm:
            log_exception("Error initializing vanilla social mixer hook", e_vsm)

        # 11. Notify Autonomous Director about zone load for grace period protection (1 minute real time)
        try:
            from ai_social_pc.autonomous_director import on_director_zone_load
            on_director_zone_load()
        except Exception as e_dzl:
            log_exception("Error initializing director zone load grace period", e_dzl)
    except Exception as e:
        log_exception("Error in on_zone_load", e)


_last_event_memory_loop_time = 0.0
_last_director_loop_time = 0.0

# Inject into Zone loading screen finished
if zone is not None and hasattr(zone, "Zone"):
    @inject(zone.Zone, "on_loading_screen_animation_finished")
    def _on_zone_load_finished(original, self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            on_zone_load()
        except Exception as e:
            log_exception("Error in on_loading_screen_animation_finished", e)
        return result

    @inject(zone.Zone, "update")
    def _on_zone_update(original, self, *args, **kwargs):
        global _last_event_memory_loop_time, _last_director_loop_time
        result = original(self, *args, **kwargs)
        try:
            process_main_thread_queue()
        except Exception as e_queue:
            log_exception("Error in AISocialPC main thread queue", e_queue)
        try:
            on_zone_update_check()
        except Exception as e:
            log_exception("Error in _on_zone_update", e)

        try:
            now_t = time.time()
            if (now_t - _last_event_memory_loop_time) >= 4.0:
                _last_event_memory_loop_time = now_t
                try:
                    from ai_social_pc.event_memory_manager import process_event_memory_checks
                    process_event_memory_checks()
                except Exception as e_ev:
                    log_exception("Error in process_event_memory_checks", e_ev)

            if (now_t - _last_director_loop_time) >= 4.0:
                _last_director_loop_time = now_t
                try:
                    from ai_social_pc.autonomous_director import on_director_zone_update_tick
                    on_director_zone_update_tick()
                except Exception as e_dir:
                    log_exception("Error in on_director_zone_update_tick", e_dir)

                try:
                    from ai_social_pc.simplified_dialogue import on_simplified_dialogue_tick
                    on_simplified_dialogue_tick()
                except Exception as e_simp:
                    log_exception("Error in on_simplified_dialogue_tick", e_simp)
        except Exception as e_loop:
            log_exception("Error in _on_zone_update periodic loop", e_loop)
        return result

    @inject(zone.Zone, "on_teardown")
    def _on_zone_teardown(original, self, *args, **kwargs):
        try:
            log("[ZONE] Zone teardown detected. Flushing dirty caches to disk before unload...")
            try:
                commit_groups_data_to_disk()
                commit_chats_to_disk()
                commit_memories_to_disk()
                commit_contacts_to_disk()
            except Exception as e_flush:
                log_exception("Error flushing caches on zone teardown", e_flush)

            log("[ZONE] Resetting in-memory working caches...")
            reset_working_cache()
            reset_chats_cache()
            reset_memories_cache()
            reset_contacts_cache()
            try:
                stop_npc_group_autonomy_alarm()
            except Exception:
                pass
            try:
                stop_friend_autonomy_alarm()
            except Exception:
                pass
        except Exception as ex_td:
            log_exception("Error during zone teardown cleanup", ex_td)
        return original(self, *args, **kwargs)





# Universal hook to ensure Romance Track is initialized and never lost ("уходит в молоко")
if RelationshipService is not None:
    @inject(RelationshipService, "add_relationship_score")
    def _injected_add_relationship_score(original, self, sim_id_a, sim_id_b, increment, *args, **kwargs):
        track = kwargs.get("track") if "track" in kwargs else (args[0] if len(args) > 0 else None)
        is_rom = False
        if track is not None:
            try:
                t_name = getattr(track, "__name__", str(track))
                t_id = getattr(track, "guid64", None) or getattr(track, "id", None)
                if t_name == "LTR_Romance_Main" or t_id == 16651 or "romance" in t_name.lower():
                    is_rom = True
                    if not self.has_relationship_track(sim_id_a, sim_id_b, track):
                        self.set_can_add_reltrack(sim_id_a, sim_id_b, True)
                        self.get_relationship_track(sim_id_a, sim_id_b, track=track, add=True)
            except Exception as ex_rom:
                log_exception("Error in romance track auto-add injection", ex_rom)

        result = original(self, sim_id_a, sim_id_b, increment, *args, **kwargs)

        if is_rom:
            try:
                self.send_relationship_info(sim_id_a, target_sim_id=sim_id_b)
                self.send_relationship_info(sim_id_b, target_sim_id=sim_id_a)
            except Exception:
                pass
            try:
                from ai_social_pc.autonomous_director import record_sim_romance_action
                aff_action = ""
                sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
                if sim_mgr:
                    for check_sid in (sim_id_a, sim_id_b):
                        inf = sim_mgr.get(check_sid)
                        inst = getattr(inf, "get_sim_instance", lambda: None)() if inf else None
                        if inst and hasattr(inst, "get_running_and_queued_interactions"):
                            for inter in inst.get_running_and_queued_interactions():
                                aff = getattr(inter, "affordance", None)
                                a_n = (getattr(aff, "__name__", "") or str(aff) or "").lower()
                                if any(rk in a_n for rk in ["kiss", "makeout", "peck", "smooch", "hug", "embrace", "cuddle", "flirt"]):
                                    aff_action = a_n
                                    break
                        if aff_action:
                            break
                record_sim_romance_action(sim_id_a, sim_id_b, aff_action or "flirt")
            except Exception as ex_rec:
                log_exception("Error in romance action tracker injection", ex_rec)
        return result

    @inject(RelationshipService, "add_relationship_bit")
    def _injected_add_relationship_bit(original, self, sim_id_a, sim_id_b, bit_to_add, *args, **kwargs):
        result = original(self, sim_id_a, sim_id_b, bit_to_add, *args, **kwargs)
        try:
            from_load = kwargs.get("from_load", False)
            if not from_load and len(args) >= 2:
                from_load = bool(args[1])
            if not from_load:
                from ai_social_pc.event_memory_manager import on_relationship_bit_added
                on_relationship_bit_added(sim_id_a, sim_id_b, bit_to_add)
                b_name = (getattr(bit_to_add, "__name__", str(bit_to_add)) or "").lower()
                if any(rk in b_name for rk in ["flirt", "kiss", "romance", "lovebirds", "sweethearts", "lovers", "affair"]):
                    from ai_social_pc.autonomous_director import record_sim_romance_action
                    record_sim_romance_action(sim_id_a, sim_id_b, f"bit_{b_name}")
        except Exception as e_bit:
            log_exception("Error in relationship bit event memory hook", e_bit)
        return result


# Initialize on module import
log(f"==================================================")
log(f"  AI Social PC Add-on v{__version__} Initializing")
log(f"==================================================")

try:
    patch_computer_interactions()
    log("AI Social PC interaction hooks loaded and ready.")
    from ai_social_pc.action_executor import hook_travel_commands
    hook_travel_commands()
except Exception as e:
    log_exception("Error during AISocialPC startup", e)

