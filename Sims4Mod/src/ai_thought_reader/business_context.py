"""
Synapse Home & Small Business Context Resolver
Supports EP 'Businesses & Hobbies' (Любимое дело), Get to Work (Retail),
Dine Out (Restaurant), and Cats & Dogs (Vet Clinic).
"""

from typing import Optional, Dict, Any, Tuple
try:
    import services
except ImportError:
    services = None

try:
    from sims4.localization import LocalizationHelperTuning
except ImportError:
    LocalizationHelperTuning = None

from ai_thought_reader.logger import log, log_exception


def get_clean_business_name(raw_name) -> str:
    """Extracts a clean human-readable name from a string or localized tuning string."""
    if not raw_name:
        return ""
    try:
        if isinstance(raw_name, str):
            clean = raw_name.strip()
            if clean:
                return clean
        if LocalizationHelperTuning is not None:
            raw_text = LocalizationHelperTuning.get_raw_text(raw_name)
            if raw_text:
                return str(raw_text).strip()
    except Exception:
        pass
    try:
        return str(raw_name).strip()
    except Exception:
        return ""


def get_business_type_label(business_type, is_en: bool = False) -> str:
    """Translates BusinessType enum to a clear descriptive label."""
    t_name = getattr(business_type, "name", str(business_type)).upper()
    if "SMALL_BUSINESS" in t_name:
        return "Home / Small Business" if is_en else "Малый / Домашний бизнес"
    elif "RETAIL" in t_name:
        return "Retail Store" if is_en else "Розничный магазин"
    elif "RESTAURANT" in t_name:
        return "Restaurant" if is_en else "Ресторан"
    elif "VET" in t_name:
        return "Vet Clinic" if is_en else "Ветеринарная клиника"
    elif "RENTAL_UNIT" in t_name:
        return "Residential Rental" if is_en else "Аренда жилья"
    return "Business" if is_en else "Бизнес"


def is_business_on_current_zone(bm, curr_zone_id) -> bool:
    """Checks if the business operates on the currently active zone ID."""
    if bm is None or not curr_zone_id:
        return False
    try:
        if getattr(bm, "business_zone_id", None) == curr_zone_id:
            return True
        if hasattr(bm, "is_zone_assigned_allowed") and bm.is_zone_assigned_allowed(curr_zone_id):
            return True
        allowed_zones = getattr(bm, "_allowed_zone_ids", None)
        if allowed_zones and curr_zone_id in allowed_zones:
            return True

        # Check if this business is owned by a household whose home_zone_id is curr_zone_id
        owner_hh_id = getattr(bm, "owner_household_id", None)
        if owner_hh_id and services is not None:
            hh_mgr = getattr(services, "household_manager", lambda: None)()
            if hh_mgr is not None:
                hh = hh_mgr.get(owner_hh_id)
                if hh is not None and getattr(hh, "home_zone_id", None) == curr_zone_id:
                    return True
    except Exception:
        pass
    return False


def find_business_manager_for_lot_or_sim(sim_info=None) -> Tuple[Optional[Any], bool]:
    """
    Finds relevant business manager.
    Returns tuple: (business_manager, is_on_current_lot: bool)
    """
    if services is None:
        return None, False

    try:
        biz_svc = getattr(services, "business_service", lambda: None)()
        if biz_svc is None:
            return None, False

        curr_zone_id = getattr(services, "current_zone_id", lambda: None)()

        # 1. Check if current active lot has an assigned business manager
        if curr_zone_id:
            try:
                mgr = biz_svc.get_business_manager_for_zone(curr_zone_id)
                if mgr is not None:
                    return mgr, True
            except Exception:
                pass

            # Check active zone director
            try:
                venue_svc = getattr(services, "venue_service", lambda: None)()
                if venue_svc:
                    zd = venue_svc.get_zone_director()
                    if zd and hasattr(zd, "business_manager") and zd.business_manager:
                        return zd.business_manager, True
            except Exception:
                pass

            # Search trackers for SmallBusiness allowed on this lot
            try:
                if hasattr(biz_svc, "business_trackers_gen"):
                    for tracker in biz_svc.business_trackers_gen():
                        bms = getattr(tracker, "_business_managers", {}) or {}
                        for bm in bms.values():
                            if bm is not None:
                                if is_business_on_current_zone(bm, curr_zone_id):
                                    return bm, True
                                if hasattr(bm, "is_zone_assigned_allowed") and bm.is_zone_assigned_allowed(curr_zone_id):
                                    return bm, True
                                if getattr(bm, "business_zone_id", None) == curr_zone_id:
                                    return bm, True
            except Exception:
                pass

            # Check active lot's owner household directly (Home / Small Business in residential lots)
            try:
                curr_zone = getattr(services, "current_zone", lambda: None)()
                lot = getattr(curr_zone, "lot", None) if curr_zone else None
                lot_hh_id = getattr(lot, "zone_owner_household_id", None) if lot else None
                if not lot_hh_id:
                    active_lot = getattr(services, "active_lot", lambda: None)()
                    lot_hh_id = getattr(active_lot, "zone_owner_household_id", None) if active_lot else None
                if lot_hh_id and hasattr(biz_svc, "get_business_tracker_for_household"):
                    lot_tracker = biz_svc.get_business_tracker_for_household(lot_hh_id)
                    if lot_tracker:
                        bms = getattr(lot_tracker, "_business_managers", {}) or {}
                        for bm in bms.values():
                            if bm is not None:
                                return bm, True
                if lot_hh_id and services is not None:
                    hh_mgr = getattr(services, "household_manager", lambda: None)()
                    if hh_mgr:
                        lot_hh = hh_mgr.get(lot_hh_id)
                        if lot_hh:
                            if hasattr(lot_hh, "business_tracker") and lot_hh.business_tracker:
                                bms = getattr(lot_hh.business_tracker, "_business_managers", {}) or {}
                                for bm in bms.values():
                                    if bm is not None:
                                        return bm, True
                            if hasattr(lot_hh, "sim_info_gen") and hasattr(biz_svc, "get_business_manager_for_sim"):
                                for m in lot_hh.sim_info_gen():
                                    m_mgr = biz_svc.get_business_manager_for_sim(getattr(m, "sim_id", 0))
                                    if m_mgr is not None:
                                        return m_mgr, True
            except Exception:
                pass

        # 2. Check if sim_info owns or works in a business
        if sim_info is not None:
            s_id = getattr(sim_info, "sim_id", None)
            if s_id and hasattr(biz_svc, "get_business_manager_for_sim"):
                try:
                    sim_mgr = biz_svc.get_business_manager_for_sim(s_id)
                    if sim_mgr is not None:
                        is_on_cur = is_business_on_current_zone(sim_mgr, curr_zone_id)
                        return sim_mgr, is_on_cur
                except Exception:
                    pass

            # Check if Sim has SmallBusinessCareer linked to an owner
            try:
                if hasattr(sim_info, "career_tracker") and sim_info.career_tracker is not None:
                    careers = getattr(sim_info.career_tracker, "careers", {})
                    for c in careers.values():
                        levels = getattr(c, "_levels_per_owner", None)
                        if levels and hasattr(biz_svc, "get_business_manager_for_sim"):
                            for o_id in levels.keys():
                                o_mgr = biz_svc.get_business_manager_for_sim(o_id)
                                if o_mgr is not None:
                                    is_on_cur = is_business_on_current_zone(o_mgr, curr_zone_id)
                                    return o_mgr, is_on_cur
            except Exception:
                pass

            # Check if anyone in sim_info's household owns a business
            try:
                hh = getattr(sim_info, "household", None)
                if hh is not None and hasattr(hh, "sim_info_gen") and hasattr(biz_svc, "get_business_manager_for_sim"):
                    for mem in hh.sim_info_gen():
                        m_id = getattr(mem, "sim_id", None)
                        if m_id:
                            m_mgr = biz_svc.get_business_manager_for_sim(m_id)
                            if m_mgr is not None:
                                is_on_cur = is_business_on_current_zone(m_mgr, curr_zone_id)
                                return m_mgr, is_on_cur
            except Exception:
                pass

    except Exception as e:
        log_exception("Error in find_business_manager_for_lot_or_sim", e)

    return None, False


def _check_is_employee(bm, sim_info) -> bool:
    """Checks whether the Sim is an employee / assigned worker in the given business."""
    if bm is None or sim_info is None:
        return False
    s_id = getattr(sim_info, "sim_id", 0)

    try:
        if hasattr(bm, "is_employee") and bm.is_employee(sim_info):
            return True
    except Exception:
        pass

    try:
        if hasattr(bm, "get_employee_assignment"):
            assignment = bm.get_employee_assignment(s_id)
            if assignment is not None:
                return True
    except Exception:
        pass

    try:
        emp_mgr = getattr(bm, "_employee_manager", None)
        if emp_mgr is not None:
            if hasattr(emp_mgr, "is_employee") and emp_mgr.is_employee(sim_info):
                return True
            if hasattr(emp_mgr, "get_employee_assignment"):
                if emp_mgr.get_employee_assignment(s_id) is not None:
                    return True
            assignments = getattr(emp_mgr, "_employee_assignments", None)
            if assignments:
                for a in assignments:
                    if getattr(a, "sim_id", None) == s_id:
                        return True
            employees = getattr(emp_mgr, "_employees", None)
            if employees and s_id in employees:
                return True
            emp_ids = getattr(emp_mgr, "_employee_sim_ids", None)
            if emp_ids:
                for v in emp_ids.values():
                    if s_id in v:
                        return True
    except Exception:
        pass

    # Check if Sim has SmallBusinessCareer with an owner_id pointing to this business owner
    try:
        owner_sim_id = getattr(bm, "owner_sim_id", None)
        if hasattr(sim_info, "career_tracker") and sim_info.career_tracker is not None:
            careers = getattr(sim_info.career_tracker, "careers", {})
            for c in careers.values():
                levels = getattr(c, "_levels_per_owner", None)
                if levels is not None and owner_sim_id and (owner_sim_id in levels):
                    if owner_sim_id != s_id:
                        return True
    except Exception:
        pass

    return False


def _is_sim_interacting_as_customer(sim_info) -> bool:
    """Checks if the Sim is currently engaged in customer / shopping / retail interactions."""
    if sim_info is None:
        return False
    try:
        sim = getattr(sim_info, "get_sim_instance", lambda: None)()
        if sim is None:
            return False

        interactions = []
        si_state = getattr(sim, "si_state", None)
        if si_state:
            interactions.extend(list(si_state))
        queue = getattr(sim, "queue", None)
        if queue:
            interactions.extend(list(queue))

        customer_keywords = (
            "retail", "buy", "shop", "purchase", "browse", "ticket",
            "small_business", "customer", "order", "view_art", "evaluate",
            "sales_pitch", "ask_for_recommendation"
        )

        for inter in interactions:
            aff = getattr(inter, "affordance", None)
            aff_name = (getattr(aff, "__name__", "") or str(aff)).lower()
            tgt = getattr(inter, "target", None)
            t_name = (getattr(tgt, "__class__", type(tgt)).__name__ or str(tgt)).lower()
            combined = aff_name + " " + t_name

            for kw in customer_keywords:
                if kw in combined:
                    return True
    except Exception:
        pass
    return False


def resolve_sim_business_role(bm, sim_info, is_on_lot: bool = True, is_en: bool = False) -> str:
    """Determines the specific role of the Sim relative to the business."""
    if bm is None or sim_info is None:
        return "Visitor" if is_en else "Посетитель"

    s_id = getattr(sim_info, "sim_id", 0)
    hh_id = getattr(sim_info, "household_id", 0)
    owner_id = getattr(bm, "owner_sim_id", None)
    owner_hh_id = getattr(bm, "owner_household_id", None)

    # 1. Owner
    if owner_id and s_id == owner_id:
        return "Business Owner (Host)" if is_en else "Владелец бизнеса (хозяин заведения)"

    # Check if Sim is an employee/worker in this business
    is_emp = _check_is_employee(bm, sim_info)

    # 2. Member of owner's household living on the same lot
    if owner_hh_id and hh_id == owner_hh_id:
        if is_emp:
            return "Household Member & Employee (Lives here and works in family business)" if is_en else "Член семьи и работник заведения (проживает здесь и помогает вести бизнес)"
        return "Household Member of Owner (Lives in this home)" if is_en else "Член семьи владельца (проживает в этом доме)"

    # 3. Employee (Hired worker from outside)
    if is_emp:
        return "Employee (Staff)" if is_en else "Сотрудник / Работник заведения"

    # 4. Explicit Customer (NPC customer situation or actively shopping)
    is_customer_flag = False
    try:
        if hasattr(bm, "is_sim_a_customer") and bm.is_sim_a_customer(sim_info):
            is_customer_flag = True
    except Exception:
        pass

    if not is_customer_flag and _is_sim_interacting_as_customer(sim_info):
        is_customer_flag = True

    if is_customer_flag:
        return "Customer / Client (Came to buy goods or services)" if is_en else "Клиент / Покупатель (пришёл за покупками или услугами)"

    # 5. Visitor on lot: Hybrid role when business is open vs closed
    is_open = bool(getattr(bm, "is_open", False))
    if is_on_lot:
        if is_open:
            # Business is OPEN: Sim could be shopping or visiting socially. Let AI adapt freely!
            return (
                "Visitor: Customer or Guest (Venue is open: Sim may be here to shop, use services, or visit friends — adapt according to Sim's actions and intentions)"
                if is_en
                else "Посетитель: Покупатель или гость (заведение открыто: персонаж может быть как клиентом за покупками/услугами, так и гостем семьи — ориентируйся по ситуации и намерениям персонажа)"
            )
        else:
            # Business is CLOSED:
            return (
                "Visitor / Guest (Venue is closed: Sim is visiting the family socially or arrived outside business hours)"
                if is_en
                else "Гость семьи / Посетитель (заведение сейчас закрыто: персонаж пришёл в гости к семье, либо застал заведение в нерабочие часы)"
            )

    return "Visitor / Customer" if is_en else "Посетитель / Покупатель"



def get_business_info_dict(sim_info=None, is_en: bool = False) -> Optional[Dict[str, Any]]:
    """Returns structured information about active business on lot or for Sim."""
    try:
        from ai_thought_reader.config import get_experimental_flag
        if not get_experimental_flag("home_business_context"):
            return None
    except Exception:
        return None

    bm, is_on_lot = find_business_manager_for_lot_or_sim(sim_info)
    if bm is None:
        return None

    try:
        raw_name = getattr(bm, "name", "") or getattr(bm, "_name", "")
        b_name = get_clean_business_name(raw_name) or ("Small Business" if is_en else "Малый бизнес")

        b_type = getattr(bm, "business_type", None)
        b_type_label = get_business_type_label(b_type, is_en=is_en)

        is_open = bool(getattr(bm, "is_open", False))
        role = resolve_sim_business_role(bm, sim_info, is_on_lot=is_on_lot, is_en=is_en)

        s_id = getattr(sim_info, "sim_id", 0) if sim_info else 0
        hh_id = getattr(sim_info, "household_id", 0) if sim_info else 0
        owner_id = getattr(bm, "owner_sim_id", None)
        owner_hh_id = getattr(bm, "owner_household_id", None)

        is_owner = bool(owner_id and s_id == owner_id)
        is_emp = _check_is_employee(bm, sim_info)
        is_family = bool(owner_hh_id and hh_id == owner_hh_id and not is_owner)
        is_fam_emp = bool(is_family and is_emp)

        cust_count = 0
        cust_mgr = getattr(bm, "_customer_manager", None)
        if cust_mgr and hasattr(cust_mgr, "_customers"):
            cust_count = len(cust_mgr._customers)

        attendance_info = ""
        sale_mode = getattr(bm, "_attendance_sale_mode", None)
        if sale_mode is not None:
            m_str = getattr(sale_mode, "name", str(sale_mode)).upper()
            if "HOURLY_FEE" in m_str:
                attendance_info = "Hourly fee active" if is_en else "Действует почасовая оплата за пребывание"
            elif "ENTRY_FEE" in m_str:
                attendance_info = "Entry fee active" if is_en else "Действует плата за вход"

        return {
            "name": b_name,
            "business_name": b_name,
            "business_type": b_type_label,
            "is_open": is_open,
            "is_on_lot": is_on_lot,
            "role": role,
            "customer_count": cust_count,
            "customers_count": cust_count,
            "is_owner": is_owner,
            "is_family_member": is_family,
            "is_employee": is_emp,
            "is_family_employee": is_fam_emp,
            "attendance_info": attendance_info,
        }
    except Exception as e:
        log_exception("Error compiling business_info_dict", e)
        return None


def get_business_prompt_block(sim_info=None, is_en: bool = False) -> str:
    """Formats a rich prompt block for LLM describing home / lot business.
    
    Only shown when the Sim is physically on the business lot!
    If the Sim is off-lot (at school, in the park, visiting elsewhere), business info
    is omitted because their career/job is already shown in the career section.
    """
    data = get_business_info_dict(sim_info, is_en=is_en)
    if not data:
        return ""

    is_on_lot = data.get("is_on_lot", False)
    if not is_on_lot:
        return ""

    is_open = data.get("is_open", False)
    b_name = data.get("business_name", "")
    b_type = data.get("business_type", "")
    role = data.get("role", "")
    cust_cnt = data.get("customer_count", 0)
    att_info = data.get("attendance_info", "")

    if is_en:
        status_str = "OPEN for customers right now (active business hours)" if is_open else "CLOSED right now (off-hours / no customers)"
        lines = [
            "[HOME / LOT BUSINESS CONTEXT]:",
            f"- Venue: \"{b_name}\" ({b_type})",
            f"- Status: {status_str}",
            f"- Character Role: {role}",
        ]
        if is_open:
            if cust_cnt > 0:
                lines.append(f"- Customers on Lot: {cust_cnt} customer(s) present right now.")
            if att_info:
                lines.append(f"- Fee Policy: {att_info}.")
            lines.append("- Note: The business is actively operating. Visiting Sims may have come specifically to shop/browse as customers, or to visit the household socially — reflect their actual intent based on their actions and desires.")
        return "\n".join(lines) + "\n\n"
    else:
        status_str = "ОТКРЫТ для посетителей прямо сейчас (рабочие часы)" if is_open else "ЗАКРЫТ в данный момент (нерабочее время / клиентов нет)"
        lines = [
            "[ДОМАШНИЙ БИЗНЕС НА УЧАСТКЕ]:",
            f"- Заведение: «{b_name}» ({b_type})",
            f"- Статус: {status_str}",
            f"- Роль персонажа: {role}",
        ]
        if is_open:
            if cust_cnt > 0:
                lines.append(f"- Клиенты на участке: прямо сейчас в заведении {cust_cnt} клиент(ов).")
            if att_info:
                lines.append(f"- Условия входа: {att_info}.")
            lines.append("- Примечание: Заведение активно работает. Посетители могут прийти как клиенты (за покупками, услугами или осмотром товаров), так и в гости к жильцам дома — ориентируйся на текущие действия и желания персонажа.")
        return "\n".join(lines) + "\n\n"

