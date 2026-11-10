"""
Trapped and Locked Sim Detector for Synapse.
Identifies whether a Sim is trapped in an enclosed room/space without doors/gates (walled in),
or trapped in a room where all exit doors are locked for them.
"""

from typing import Optional, Tuple
from ai_thought_reader.logger import log, log_exception

try:
    import services
except ImportError:
    services = None

try:
    import build_buy
except ImportError:
    build_buy = None

try:
    import routing
    import sims4.math
except ImportError:
    routing = None
    sims4 = None


def get_sim_trapped_status(sim_info, is_en: bool = False) -> str:
    """
    Returns a status string to append directly after the Sim's name if they are trapped or locked.
    Examples:
      RU: " [ЗАМУРОВАН: помещение без дверей, выхода нет]"
      RU: " [ЗАПЕРТ: комната с закрытой дверью]"
      EN: " [WALLED IN: trapped in a room with no doors or exits]"
      EN: " [LOCKED: trapped behind a locked door]"
      Normal: ""
    """
    try:
        from ai_thought_reader.config import get_experimental_flag, get_context_flag
        if not get_experimental_flag("trapped_sim_detection") and not get_context_flag("trapped_status"):
            return ""
    except Exception:
        pass

    try:
        if services is None or sim_info is None:
            return ""

        sim_instance = sim_info.get_sim_instance() if hasattr(sim_info, "get_sim_instance") else None
        if sim_instance is None:
            return ""

        # Only check instanced Sims on the active lot
        current_zone = services.current_zone()
        if current_zone is None:
            return ""

        zone_id = current_zone.id

        # 1. Obtain Sim's current room ID
        sim_room_id = getattr(sim_instance, "room_id", None)
        sim_level = getattr(sim_instance, "level", 0)
        sim_pos = getattr(sim_instance, "position", None)

        if sim_room_id is None and build_buy is not None and sim_pos is not None:
            try:
                sim_room_id = build_buy.get_room_id(zone_id, sim_pos, sim_level)
            except Exception:
                sim_room_id = 0

        if sim_room_id is None:
            sim_room_id = 0

        # 2. Check room-level doors if Sim is indoors (sim_room_id > 0)
        obj_manager = services.object_manager()
        doors_for_room = []
        if sim_room_id > 0 and obj_manager is not None and build_buy is not None:
            try:
                for obj in obj_manager.values():
                    if getattr(obj, "is_door_portal", False) or hasattr(obj, "get_door_positions"):
                        door_level = getattr(obj, "level", sim_level)
                        if door_level == sim_level:
                            try:
                                front_pos, back_pos = obj.get_door_positions()
                                r_front = build_buy.get_room_id(zone_id, front_pos, door_level) if front_pos else None
                                r_back = build_buy.get_room_id(zone_id, back_pos, door_level) if back_pos else None
                                if r_front == sim_room_id or r_back == sim_room_id:
                                    doors_for_room.append(obj)
                            except Exception:
                                pass
            except Exception as e_doors:
                log_exception("Error inspecting room doors in trapped_detector", e_doors)

            # Case A: Room has strictly ZERO doors leading in or out -> Walled in!
            if len(doors_for_room) == 0:
                log(f"[TRAPPED DETECTOR] Sim {getattr(sim_info, 'full_name', '')} is WALLED IN (room {sim_room_id} has 0 doors)")
                return " [WALLED IN: trapped in a room with no doors or exits]" if is_en else " [ЗАМУРОВАН: помещение без дверей, выхода нет]"

            # Check if every single door of this room is locked for this Sim
            all_room_doors_locked = True
            for door in doors_for_room:
                is_door_locked = False
                try:
                    if hasattr(door, "test_lock"):
                        res = door.test_lock(sim_instance)
                        is_door_locked = bool(getattr(res, "is_locked", res))
                    elif hasattr(door, "get_component"):
                        import objects.components.types
                        cmp_lock = door.get_component(objects.components.types.PORTAL_LOCKING_COMPONENT)
                        if cmp_lock and hasattr(cmp_lock, "test_lock"):
                            res = cmp_lock.test_lock(sim_instance)
                            is_door_locked = bool(getattr(res, "is_locked", res))
                except Exception:
                    is_door_locked = False

                if not is_door_locked:
                    all_room_doors_locked = False
                    break

            if all_room_doors_locked:
                log(f"[TRAPPED DETECTOR] Sim {getattr(sim_info, 'full_name', '')} is LOCKED IN (all {len(doors_for_room)} doors of room {sim_room_id} are locked)")
                return " [LOCKED: trapped behind a locked door]" if is_en else " [ЗАПЕРТ: комната с закрытой дверью]"

        # 3. Pathing connectivity check towards outside arrival / exit point
        if routing is not None and sims4 is not None and hasattr(sim_instance, "routing_location"):
            try:
                arrival_point = None
                if hasattr(current_zone, "active_lot_arrival_spawn_point") and current_zone.active_lot_arrival_spawn_point:
                    arrival_point = current_zone.active_lot_arrival_spawn_point.get_approximate_center()
                elif hasattr(current_zone, "lot") and current_zone.lot and hasattr(current_zone.lot, "corners"):
                    corners = current_zone.lot.corners
                    if corners and len(corners) > 1:
                        arrival_point = corners[1]

                if arrival_point is not None:
                    world_surf = routing.SurfaceIdentifier(zone_id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
                    dest_location = routing.Location(arrival_point, sims4.math.Quaternion.IDENTITY(), world_surf)
                    sim_location = getattr(sim_instance, "routing_location", None)
                    if sim_location is None and sim_pos is not None:
                        sim_location = routing.Location(sim_pos, getattr(sim_instance, "orientation", sims4.math.Quaternion.IDENTITY()), getattr(sim_instance, "routing_surface", world_surf))

                    if sim_location is not None:
                        sim_routing_ctx = getattr(sim_instance, "routing_context", None)
                        if sim_routing_ctx is not None:
                            can_reach_outside = routing.test_connectivity_pt_pt(sim_location, dest_location, sim_routing_ctx)
                            if not can_reach_outside:
                                # Sim cannot reach the exit point. Check if they can reach it WITHOUT locks:
                                generic_ctx = routing.PathPlanContext()
                                can_reach_if_unlocked = routing.test_connectivity_pt_pt(sim_location, dest_location, generic_ctx)
                                if can_reach_if_unlocked:
                                    log(f"[TRAPPED DETECTOR] Sim {getattr(sim_info, 'full_name', '')} path blocked by locked door/gate")
                                    return " [LOCKED: trapped behind a locked door]" if is_en else " [ЗАПЕРТ: комната с закрытой дверью]"
                                else:
                                    log(f"[TRAPPED DETECTOR] Sim {getattr(sim_info, 'full_name', '')} completely walled/fenced in (no path to outside)")
                                    return " [WALLED IN: trapped in a room with no doors or exits]" if is_en else " [ЗАМУРОВАН: помещение без дверей, выхода нет]"
            except Exception as e_routing:
                log_exception("Error in routing connectivity test in trapped_detector", e_routing)

    except Exception as e:
        log_exception("Exception in get_sim_trapped_status", e)

    return ""
