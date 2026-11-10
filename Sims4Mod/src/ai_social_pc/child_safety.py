# -*- coding: utf-8 -*-
from typing import Optional, Any

try:
    from sims.sim_info_types import Age
except Exception:
    Age = None


PROTECTED_AGE_STAGES = [
    "BABY",
    "INFANT",
    "TODDLER",
    "CHILD",
]

BLOCKED_DO_ACTIONS = [
    "wicked_sex",
    "woohoo",
    "sex",
    "ww_sex",
    "have_sex",
    "ask_on_date",
    "date",
    "ask_date",
    "go_on_date",
    "start_date",
]


def is_child_or_minor(sim_info: Any) -> bool:
    if sim_info is None:
        return False
    try:
        raw_age = getattr(sim_info, "age", None)
        if raw_age is not None:
            age_name = getattr(raw_age, "name", str(raw_age)).upper()
            for stage in PROTECTED_AGE_STAGES:
                if stage in age_name:
                    return True

        if hasattr(sim_info, "is_child") and sim_info.is_child:
            return True
        if hasattr(sim_info, "is_toddler") and sim_info.is_toddler:
            return True
        if hasattr(sim_info, "is_baby") and sim_info.is_baby:
            return True
        if hasattr(sim_info, "is_infant") and sim_info.is_infant:
            return True
    except Exception:
        pass
    return False


def can_apply_romance(sim_a: Any, sim_b: Any) -> bool:
    if is_child_or_minor(sim_a) or is_child_or_minor(sim_b):
        return False
    return True


def is_do_action_allowed(actor_info: Any, target_info: Any, action_type: str) -> bool:
    if not action_type:
        return True
    act = str(action_type).strip().lower()
    if is_child_or_minor(actor_info) or is_child_or_minor(target_info):
        for blocked in BLOCKED_DO_ACTIONS:
            if act == blocked or act.startswith(f"{blocked}:"):
                return False
    return True


def should_hide_nudity_level(sim_info: Any) -> bool:
    return is_child_or_minor(sim_info)
