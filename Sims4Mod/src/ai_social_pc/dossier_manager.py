# -*- coding: utf-8 -*-
"""
Synapse Third-Party Dossier Manager (Experimental Feature)
Analyzes dialogue, messenger chats, and autonomous scenes for mentions of
third-party Sims, names, service roles, occupations, relatives, or neighbors,
and generates an in-depth Dossier / Context Card for inclusion in the AI prompt.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple

from ai_social_pc.logger import log, log_exception

try:
    import services
except ImportError:
    services = None


def is_dossier_enabled() -> bool:
    """Checks if the experimental third-party dossier feature is enabled in config."""
    try:
        from ai_thought_reader.config import get_experimental_flag
        return bool(get_experimental_flag("third_party_dossier"))
    except Exception:
        return False


# Common Russian words/pronouns that could collide with short 2-3 letter names
COMMON_COLLISION_WORDS = {
    "он", "она", "оно", "они", "мы", "вы", "ты", "я",
    "ли", "бы", "же", "да", "не", "ни", "но", "а", "и",
    "том", "мир", "май", "сон", "рой", "лев", "год", "кот", "бот", "дом",
    "готов", "дан", "был", "будет", "стал", "все", "всё", "еще", "ещё", "уже",
}

RU_NAME_ENDINGS = r"(?:[аяеиыуою]|ой|ей|ою|ею|ом|ем|ём|ов|ев|ам|ами|ах|чка|чки|чке|чку|чкой|очка|очки|очке|очку|очкой|ечка|ечки|ечке|ечку|ечкой|енька|еньке|еньку|енькой|ушка|ушке|ушку|ушкой|уля|ули|уле|улю|улей|'s)?"


def _build_name_pattern(name_part: str) -> Optional[str]:
    """Generates a flexible regex pattern matching Russian and English inflections of a name."""
    clean = (name_part or "").strip().lower()
    if not clean or len(clean) < 2:
        return None

    # Strip final vowel or й/ь if word is at least 3 chars long
    if len(clean) >= 3 and clean[-1] in "аяеиыуоюьй":
        stem = clean[:-1]
    else:
        stem = clean

    if len(stem) <= 2:
        return rf"\b{re.escape(stem)}(?:[аяеиыуою]|'s)?\b"

    return rf"\b{re.escape(stem)}{RU_NAME_ENDINGS}\b"


def _extract_participant_ids(participant_sim_infos: List[Any]) -> Set[int]:
    """Extracts valid integer Sim IDs for all active conversation participants."""
    res = set()
    for p in participant_sim_infos:
        if p is None:
            continue
        sid = getattr(p, "sim_id", None) or getattr(p, "id", None)
        if sid:
            try:
                res.add(int(sid))
            except (ValueError, TypeError):
                pass
    return res


def detect_third_party_references(text: str, participant_sim_infos: List[Any]) -> Dict[str, Any]:
    """
    Parses dialogue text and finds mentions of third-party Sims, roles, relatives, or neighbors.
    Excludes all active participants from being identified as third parties.
    """
    result = {
        "matched_sims": [],
        "trigger_neighbors": False,
        "trigger_relatives": False,
        "matched_roles": [],
    }

    if not text or not services:
        return result

    raw_text = text.lower()
    participant_ids = _extract_participant_ids(participant_sim_infos)

    # 1. Collective Triggers: Neighbors
    if re.search(r"\b(?:сосед[а-я]*|по соседству|на нашей улице|neighbor[s]?)\b", raw_text, re.IGNORECASE):
        result["trigger_neighbors"] = True

    # 2. Collective Triggers: Relatives / Family
    if re.search(r"\b(?:родственник[а-я]*|родн[яеию]|семь[яеию]|родич[а-я]*|родны[хеми]|relative[s]?|family|extended family|folks)\b", raw_text, re.IGNORECASE):
        result["trigger_relatives"] = True

    # 3. Relational Triggers (spouse, child, parent, sibling, lover, ex)
    rel_terms = {
        "spouse": r"\b(?:муж[а-я]*|жен[а-я]|супруг[а-я]*|husband|wife|spouse)\b",
        "child": r"\b(?:сын[а-я]*|доч[ьк][а-я]*|дет[я-я]|ребен[ка-я]*|son|daughter|child|children|kid|kids)\b",
        "parent": r"\b(?:мам[а-я]*|пап[а-я]*|мать|матер[а-я]*|отец|отц[а-я]*|родител[а-я]*|mother|father|parents|mom|dad)\b",
        "sibling": r"\b(?:брат[а-я]*|сестр[а-я]*|brother|sister|sibling|brothers|sisters|siblings)\b",
        "lover": r"\b(?:любовник[а-я]*|любовниц[а-я]*|любов[а-я]*|парен[ья-я]*|девушк[а-я]*|lover|mistress|boyfriend|girlfriend)\b",
        "ex": r"\b(?:бывш[а-я]*|ex-husband|ex-wife|ex-boyfriend|ex-girlfriend)\b",
    }

    found_rel_categories = set()
    for cat, pattern in rel_terms.items():
        if re.search(pattern, raw_text, re.IGNORECASE):
            found_rel_categories.add(cat)

    sim_info_mgr = services.sim_info_manager()
    if not sim_info_mgr:
        return result

    candidate_sim_scores: Dict[int, Tuple[Any, float, str]] = {}  # sim_id -> (sim_info, score, reason)

    # Resolve Relational Ties for participants
    if found_rel_categories:
        for p_info in participant_sim_infos:
            if not p_info:
                continue
            p_id = getattr(p_info, "sim_id", 0)
            gen = getattr(p_info, "genealogy", None)
            rel_tracker = getattr(p_info, "relationship_tracker", None)

            # Spouse
            if "spouse" in found_rel_categories:
                sp_id = getattr(p_info, "spouse_sim_id", 0)
                if sp_id and sp_id not in participant_ids:
                    s_info = sim_info_mgr.get(int(sp_id))
                    if s_info:
                        candidate_sim_scores[int(sp_id)] = (s_info, 120.0, "Супруг(а)")

            # Children
            if "child" in found_rel_categories and gen:
                try:
                    for cid in getattr(gen, "get_children_sim_ids", lambda: [])():
                        if int(cid) not in participant_ids:
                            c_info = sim_info_mgr.get(int(cid))
                            if c_info:
                                candidate_sim_scores[int(cid)] = (c_info, 110.0, "Ребенок")
                except Exception:
                    pass

            # Parents
            if "parent" in found_rel_categories and gen:
                try:
                    for pid in getattr(gen, "get_parent_sim_ids", lambda: [])():
                        if int(pid) not in participant_ids:
                            par_info = sim_info_mgr.get(int(pid))
                            if par_info:
                                candidate_sim_scores[int(pid)] = (par_info, 110.0, "Родитель")
                except Exception:
                    pass

            # Siblings
            if "sibling" in found_rel_categories and gen:
                try:
                    for sbid in getattr(gen, "get_siblings_sim_ids", lambda: [])():
                        if int(sbid) not in participant_ids:
                            sb_info = sim_info_mgr.get(int(sbid))
                            if sb_info:
                                candidate_sim_scores[int(sbid)] = (sb_info, 105.0, "Брат/Сестра")
                except Exception:
                    pass

            # Lover / Mistress (> 35 romance, not spouse)
            if "lover" in found_rel_categories and rel_tracker:
                try:
                    from ai_social_pc.chat_manager import _get_romance_track
                    rom_track = _get_romance_track()
                    if rom_track and hasattr(rel_tracker, "get_relationship_score"):
                        for other_info in sim_info_mgr.get_all():
                            oid = getattr(other_info, "sim_id", 0)
                            if oid and int(oid) not in participant_ids and int(oid) != getattr(p_info, "spouse_sim_id", 0):
                                r_val = rel_tracker.get_relationship_score(oid, rom_track)
                                if r_val >= 35.0:
                                    candidate_sim_scores[int(oid)] = (other_info, 115.0 + r_val, "Романтическая связь")
                except Exception:
                    pass

    # 4. Careers, Occupations & NPC Service Roles (Playable and NPC)
    career_and_role_patterns = {
        # --- NPC Service Roles ---
        "maid": (r"\b(?:горничн[а-я]*|уборщиц[а-я]*|клининг[а-я]*|maid|cleaner)\b", "Горничная"),
        "nanny": (r"\b(?:нян[яеию]|няньк[а-я]*|бэбиситтер[а-я]*|nanny|babysitter)\b", "Няня"),
        "butler": (r"\b(?:дворецк[а-я]*|батлер[а-я]*|butler)\b", "Дворецкий"),
        "gardener": (r"\b(?:садовник[а-я]*|садовод[а-я]*|gardener)\b", "Садовник"),
        "repair": (r"\b(?:ремонтник[а-я]*|сантехник[а-я]*|мастер[а-я]*|repairman|technician|plumber)\b", "Мастер-ремонтник"),
        "delivery": (r"\b(?:курьер[а-я]*|доставщик[а-я]*|пиццерий[а-я]*|пицц[а-я]*|delivery|courier)\b", "Доставщик"),
        "mailman": (r"\b(?:почтальон[а-я]*|почт[а-я]*|mailman|postal)\b", "Почтальон"),
        "bartender": (r"\b(?:бармен[а-я]*|барист[а-я]*|bartender|barista)\b", "Бармен"),
        "paparazzi": (r"\b(?:папарацц[иея]*|paparazzi)\b", "Папарацци"),
        "masseuse": (r"\b(?:массажист[а-я]*|массажистк[а-я]*|masseur|masseuse)\b", "Массажист"),
        "firefighter": (r"\b(?:пожарн[а-я]*|firefighter)\b", "Пожарный"),
        "policeman": (r"\b(?:полицейск[а-я]*|коп[а-я]*|милиционер[а-я]*|police|officer|cop)\b", "Полицейский"),
        "grim_reaper": (r"\b(?:смерт[ьи]|жнец[а-я]*|костляв[а-я]*|grim reaper|death)\b", "Смерть"),
        "father_winter": (r"\b(?:дед[а-я]* мороз[а-я]*|санта|клим[а-я]* мороз[а-я]*|father winter|santa)\b", "Дед Мороз"),
        "bonehilda": (r"\b(?:скелехильд[а-я]*|скелет[а-я]*|bonehilda)\b", "Скелехильда"),

        # --- Playable Professions & Careers ---
        "politician": (r"\b(?:политик[а-я]*|мэр[а-я]*|президент[а-я]*|депутат[а-я]*|чиновник[а-я]*|губернатор[а-я]*|politician|mayor|president|official)\b", "Политик"),
        "doctor": (r"\b(?:врач[а-я]*|доктор[а-я]*|хирург[а-я]*|медик[а-я]*|терапевт[а-я]*|медсестр[а-я]*|медбрат[а-я]*|doctor|physician|surgeon|nurse|medic)\b", "Врач"),
        "scientist": (r"\b(?:учен[ыо][а-я]*|учён[ыо][а-я]*|исследовател[а-я]*|лаборант[а-я]*|scientist|researcher)\b", "Ученый"),
        "detective": (r"\b(?:детектив[а-я]*|следовател[а-я]*|сыщик[а-я]*|detective|investigator)\b", "Детектив"),
        "teacher": (r"\b(?:учител[а-я]*|преподавател[а-я]*|профессор[а-я]*|педагог[а-я]*|репетитор[а-я]*|teacher|professor|educator)\b", "Преподаватель"),
        "lawyer": (r"\b(?:юрист[а-я]*|адвокат[а-я]*|судь[яеию][а-я]*|прокурор[а-я]*|lawyer|attorney|judge|prosecutor)\b", "Юрист"),
        "engineer": (r"\b(?:инженер[а-я]*|программист[а-я]*|разработчик[а-я]*|айтишник[а-я]*|engineer|developer|programmer)\b", "Инженер / Программист"),
        "writer": (r"\b(?:писател[а-я]*|журналист[а-я]*|репортер[а-я]*|автор[а-я]*|колумнист[а-я]*|writer|journalist|author)\b", "Писатель / Журналист"),
        "artist": (r"\b(?:художник[а-я]*|живопис[а-я]*|иллюстратор[а-я]*|artist|painter)\b", "Художник"),
        "musician": (r"\b(?:музыкант[а-я]*|певец|певиц[а-я]*|композитор[а-я]*|гитарист[а-я]*|пианист[а-я]*|musician|singer|composer)\b", "Музыкант"),
        "actor": (r"\b(?:актер[а-я]*|актрис[а-я]*|кинозвезд[а-я]*|actor|actress|movie star)\b", "Актёр"),
        "chef": (r"\b(?:повар[а-я]*|шеф[а-я]*|кулинар[а-я]*|кулинари[а-я]*|chef|cook|culinary)\b", "Кулинар / Шеф-повар"),
        "athlete": (r"\b(?:спортсмен[а-я]*|атлет[а-я]*|бодибилдер[а-я]*|тренер[а-я]*|боксер[а-я]*|футболист[а-я]*|athlete|fitness|coach|trainer)\b", "Спортсмен"),
        "astronaut": (r"\b(?:космонавт[а-я]*|астронавт[а-я]*|astronaut|cosmonaut)\b", "Космонавт"),
        "secret_agent": (r"\b(?:тайн[а-я]* агент[а-я]*|шпион[а-я]*|разведчик[а-я]*|secret agent|spy)\b", "Тайный агент"),
        "military": (r"\b(?:военн[а-я]*|солдат[а-я]*|офицер[а-я]*|генерал[а-я]*|сержант[а-я]*|military|soldier)\b", "Военный"),
        "business": (r"\b(?:бизнесмен[а-я]*|предпринимател[а-я]*|финансист[а-я]*|инвестор[а-я]*|businessman|executive)\b", "Бизнесмен"),
        "ecologist": (r"\b(?:эколог[а-я]*|природоохранник[а-я]*|conservationist|ecologist)\b", "Эколог"),
        "boss": (r"\b(?:босс[а-я]*|начальник[а-я]*|шеф[а-я]*|руководител[а-я]*|boss|supervisor)\b", "Начальник"),
        "coworker": (r"\b(?:коллег[а-я]*|сослужив[а-я]*|сослуживиц[а-я]*|coworker|colleague)\b", "Коллега"),
    }

    found_service_roles = []
    for role_key, (pat, label) in career_and_role_patterns.items():
        if re.search(pat, raw_text, re.IGNORECASE):
            found_service_roles.append((role_key, label))
            result["matched_roles"].append(label)

    # If any career or role is mentioned, find Sims matching that role across 3 tiers:
    if found_service_roles:
        try:
            from ai_thought_reader.context import get_sim_career_info
            
            # Helper to check if Sim matches any of the triggered roles
            def _sim_has_matching_role(target_sim):
                c_str = str(get_sim_career_info(target_sim)).lower()
                for r_key, r_lbl in found_service_roles:
                    if r_key in c_str or r_lbl.lower() in c_str:
                        return r_lbl
                return None

            # Tier 1: Instanced sims on the active lot (highest priority)
            for inst in sim_info_mgr.instanced_sims_gen():
                inf = getattr(inst, "sim_info", inst)
                sid = getattr(inf, "sim_id", 0)
                if not sid or int(sid) in participant_ids or getattr(inf, "is_pet", False):
                    continue
                matched_lbl = _sim_has_matching_role(inf)
                if matched_lbl:
                    candidate_sim_scores[int(sid)] = (inf, 160.0, f"На участке: {matched_lbl}")

            # Tier 2: Known contacts of dialogue participants
            for p_info in participant_sim_infos:
                if not p_info:
                    continue
                r_tr = getattr(p_info, "relationship_tracker", None)
                if r_tr and hasattr(r_tr, "get_all_target_sim_ids"):
                    for rel_sid in r_tr.get_all_target_sim_ids():
                        if int(rel_sid) in participant_ids or int(rel_sid) in candidate_sim_scores:
                            continue
                        rel_info = sim_info_mgr.get(int(rel_sid))
                        if rel_info and not getattr(rel_info, "is_pet", False):
                            matched_lbl = _sim_has_matching_role(rel_info)
                            if matched_lbl:
                                candidate_sim_scores[int(rel_sid)] = (rel_info, 140.0, f"Знакомый(ая) {matched_lbl}")

            # Tier 3: All Sims in the save (townies, residents, NPCs) if not enough found yet
            if len(candidate_sim_scores) < 3:
                for any_sim in sim_info_mgr.get_all():
                    any_sid = getattr(any_sim, "sim_id", 0)
                    if not any_sid or int(any_sid) in participant_ids or getattr(any_sim, "is_pet", False):
                        continue
                    if int(any_sid) in candidate_sim_scores:
                        continue
                    matched_lbl = _sim_has_matching_role(any_sim)
                    if matched_lbl:
                        candidate_sim_scores[int(any_sid)] = (any_sim, 110.0, f"Профессия: {matched_lbl}")
                        if len(candidate_sim_scores) >= 3:
                            break
        except Exception as e_srv:
            log_exception("Error resolving career/service roles in dossier", e_srv)

    # 5. Direct Mentions by First Name or Last Name
    try:
        from ai_thought_reader.lore_manager import get_sim_lore
    except Exception:
        get_sim_lore = lambda sid: ""

    try:
        all_sims = list(sim_info_mgr.get_all())
    except Exception:
        all_sims = []

    for s_info in all_sims:
        sid = getattr(s_info, "sim_id", 0)
        if not sid or int(sid) in participant_ids or getattr(s_info, "is_pet", False):
            continue

        fn = getattr(s_info, "first_name", "") or ""
        ln = getattr(s_info, "last_name", "") or ""

        clean_fn = fn.strip().lower()
        clean_ln = ln.strip().lower()

        pat_fn = _build_name_pattern(clean_fn) if clean_fn else None
        pat_ln = _build_name_pattern(clean_ln) if clean_ln else None

        fn_matched = bool(pat_fn and re.search(pat_fn, raw_text, re.IGNORECASE))
        ln_matched = bool(pat_ln and re.search(pat_ln, raw_text, re.IGNORECASE))

        # Check compound surname components if not directly matched (e.g. Spencer-Kim)
        if not ln_matched and clean_ln and ("-" in clean_ln or " " in clean_ln):
            subparts = re.split(r"[- ]+", clean_ln)
            for sp in subparts:
                sp_pat = _build_name_pattern(sp)
                if sp_pat and re.search(sp_pat, raw_text, re.IGNORECASE):
                    ln_matched = True
                    break

        matched_name = False
        matched_reason = ""
        score = 0.0

        # Case 1: Both First Name and Last Name matched in text (100% confidence)
        if fn_matched and ln_matched:
            matched_name = True
            matched_reason = f"Имя и фамилия: {fn} {ln}"
            score = 350.0

        # Case 2: Only First Name matched
        elif fn_matched:
            if clean_fn in COMMON_COLLISION_WORDS or len(clean_fn) <= 3:
                cap_pat = rf"\b{re.escape(fn.strip().capitalize())}{RU_NAME_ENDINGS}\b"
                if re.search(cap_pat, text):
                    matched_name = True
                    matched_reason = f"Имя: {fn}"
                    score = 120.0
            else:
                matched_name = True
                matched_reason = f"Имя: {fn}"
                score = 120.0

        # Case 3: Only Last Name matched
        elif ln_matched:
            if clean_ln in COMMON_COLLISION_WORDS or len(clean_ln) <= 3:
                cap_pat = rf"\b{re.escape(ln.strip().capitalize())}{RU_NAME_ENDINGS}\b"
                has_cap = bool(re.search(cap_pat, text))
                has_family = bool(re.search(rf"(?:\b(?:семья|семье|семью|семьей|дом|мистер|миссис)\s+){re.escape(clean_ln[:3])}", raw_text))
                if has_cap or has_family:
                    matched_name = True
                    matched_reason = f"Фамилия: {ln}"
                    score = 110.0
            else:
                matched_name = True
                matched_reason = f"Фамилия: {ln}"
                score = 110.0

        if matched_name:
            # Prioritize: currently on active lot
            if getattr(s_info, "get_sim_instance", lambda: None)() is not None:
                score += 50.0
            # Prioritize: has relationship with any participant
            for p in participant_sim_infos:
                if p:
                    r_tr = getattr(p, "relationship_tracker", None)
                    if r_tr and hasattr(r_tr, "has_relationship"):
                        if r_tr.has_relationship(sid):
                            score += 40.0
                            break
            # Prioritize: has custom Lore
            if get_sim_lore(sid):
                score += 25.0

            cur_exist = candidate_sim_scores.get(int(sid))
            if not cur_exist or score > cur_exist[1]:
                candidate_sim_scores[int(sid)] = (s_info, score, matched_reason)
                log(f"[DOSSIER] Found candidate: {fn} {ln} (score={score}, reason='{matched_reason}')")

    # Sort candidates by score descending and take top 3
    sorted_candidates = sorted(candidate_sim_scores.values(), key=lambda x: x[1], reverse=True)
    result["matched_sims"] = [c[0] for c in sorted_candidates[:3]]

    return result


def _format_single_sim_dossier(target_info: Any, participant_sim_infos: List[Any], is_en: bool = False) -> str:
    """Renders a rich, multi-tiered dossier card for a single third-party Sim."""
    lines = []
    sid = getattr(target_info, "sim_id", 0)
    fn = getattr(target_info, "first_name", "") or ""
    ln = getattr(target_info, "last_name", "") or ""
    full_name = f"{fn} {ln}".strip() or ("Sim" if is_en else "Персонаж")

    # Age and Gender
    age_str = "Adult" if is_en else "Взрослый"
    try:
        a_val = getattr(target_info, "age", None)
        if a_val:
            a_name = str(getattr(a_val, "name", a_val)).upper()
            age_map = {
                "BABY": ("Baby", "Младенец"),
                "TODDLER": ("Toddler", "Малыш"),
                "CHILD": ("Child", "Ребенок"),
                "TEEN": ("Teen", "Подросток"),
                "YOUNGADULT": ("Young Adult", "Молодой(ая)"),
                "ADULT": ("Adult", "Взрослый(ая)"),
                "ELDER": ("Elder", "Пожилой(ая)"),
            }
            if a_name in age_map:
                age_str = age_map[a_name][0] if is_en else age_map[a_name][1]
    except Exception:
        pass

    # Career / Role
    from ai_thought_reader.context import get_sim_career_info
    career_str = get_sim_career_info(target_info) or ("Unemployed" if is_en else "Без работы")
    if is_en and career_str and career_str != "Unemployed":
        try:
            from ai_thought_reader.context_en import translate_career_en
            career_str = translate_career_en(career_str)
        except Exception:
            pass

    # Household / Residence
    residence_str = "Homeless Townie" if is_en else "Бездомный горожанин"
    try:
        hh = getattr(target_info, "household", None)
        if hh:
            h_name = getattr(hh, "name", "")
            z_id = getattr(hh, "home_zone_id", 0)
            if z_id and z_id > 0:
                residence_str = f"Семья «{h_name}»" if not is_en else f'Household "{h_name}"'
    except Exception:
        pass

    # Occult
    occult_str = "Human" if is_en else "Человек"
    try:
        from ai_thought_reader.lore_manager import get_sim_race
        custom_race = get_sim_race(sid)
        if custom_race:
            occult_str = custom_race
        else:
            occ_tr = getattr(target_info, "occult_tracker", None)
            if occ_tr:
                for occ_name in ("VAMPIRE", "WITCH", "WEREWOLF", "MERMAID", "ALIEN", "ROBOT"):
                    has_occ = getattr(occ_tr, f"has_occult_type", None)
                    if has_occ:
                        # check type
                        pass
    except Exception:
        pass

    header_lbl = f"[ДОСЬЕ: {full_name}]" if not is_en else f"[DOSSIER: {full_name}]"
    lines.append(header_lbl)
    lines.append(f"  • Статус: {age_str}, {career_str}. Проживание: {residence_str}. Раса: {occult_str}." if not is_en else f"  • Status: {age_str}, {career_str}. Living: {residence_str}. Race: {occult_str}.")

    # Relationships of each participant to this Sim
    from ai_thought_reader.context import get_relationship_between_sims
    from ai_social_pc.chat_manager import _get_friendship_track, _get_romance_track
    fr_track = _get_friendship_track()
    rom_track = _get_romance_track()

    rel_lines = []
    for p in participant_sim_infos:
        if not p:
            continue
        p_name = f"{getattr(p, 'first_name', '')}".strip() or ("Sim" if is_en else "Собеседник")
        r_type = get_relationship_between_sims(p, target_info)
        if is_en and r_type:
            try:
                from ai_thought_reader.context_en import translate_relationship_en
                r_type = translate_relationship_en(r_type)
            except Exception:
                pass
        p_tr = getattr(p, "relationship_tracker", None)
        scores = []
        if p_tr and hasattr(p_tr, "get_relationship_score"):
            try:
                if fr_track:
                    fv = int(p_tr.get_relationship_score(sid, fr_track))
                    scores.append(f"Дружба: {fv:+d}" if not is_en else f"Friendship: {fv:+d}")
                if rom_track:
                    rv = int(p_tr.get_relationship_score(sid, rom_track))
                    scores.append(f"Романтика: {rv:+d}" if not is_en else f"Romance: {rv:+d}")
            except Exception:
                pass
        score_part = f" ({', '.join(scores)})" if scores else ""
        rel_lines.append(f"    - У {p_name}: {r_type}{score_part}")

    if rel_lines:
        lines.append("  • Отношения участников к нему/ней:" if not is_en else "  • Participants' relations to this Sim:")
        lines.extend(rel_lines)

    # Family & romantic connections in the world
    gen = getattr(target_info, "genealogy", None)
    family_members = []
    if gen:
        try:
            sim_info_mgr = services.sim_info_manager()
            sp_id = getattr(target_info, "spouse_sim_id", 0)
            if sp_id and sim_info_mgr:
                sp_info = sim_info_mgr.get(int(sp_id))
                if sp_info:
                    sp_name = f"{getattr(sp_info, 'first_name', '')} {getattr(sp_info, 'last_name', '')}".strip()
                    family_members.append(f"Супруг(а): {sp_name}" if not is_en else f"Spouse: {sp_name}")
            for cid in getattr(gen, "get_children_sim_ids", lambda: [])()[:2]:
                if sim_info_mgr:
                    c_info = sim_info_mgr.get(int(cid))
                    if c_info:
                        c_name = f"{getattr(c_info, 'first_name', '')}".strip()
                        family_members.append(f"Ребенок: {c_name}" if not is_en else f"Child: {c_name}")
            for pid in getattr(gen, "get_parent_sim_ids", lambda: [])()[:2]:
                if sim_info_mgr:
                    par_info = sim_info_mgr.get(int(pid))
                    if par_info:
                        p_name = f"{getattr(par_info, 'first_name', '')}".strip()
                        family_members.append(f"Родитель: {p_name}" if not is_en else f"Parent: {p_name}")
        except Exception:
            pass

    if family_members:
        lines.append(f"  • Семья: {', '.join(family_members)}" if not is_en else f"  • Family: {', '.join(family_members)}")

    # CAS Personality Traits
    try:
        from ai_thought_reader.context import get_sim_traits
        tr_list = get_sim_traits(target_info)
        if tr_list:
            t_str = ", ".join(tr_list[:4])
            if is_en and t_str:
                try:
                    from ai_thought_reader.context_en import translate_traits_en
                    t_str = translate_traits_en(t_str)
                except Exception:
                    pass
            lines.append(f"  • Черты характера: {t_str}" if not is_en else f"  • Traits: {t_str}")
    except Exception:
        pass

    # Personal Custom Lore (from lore_manager)
    try:
        from ai_thought_reader.lore_manager import get_sim_lore
        custom_lore = get_sim_lore(sid)
        if custom_lore:
            lore_clean = str(custom_lore).strip()
            if len(lore_clean) > 200:
                lore_clean = lore_clean[:200] + "..."
            lines.append(f'  • Личный лор и биография: «{lore_clean}»' if not is_en else f'  • Lore & Secrets: "{lore_clean}"')
    except Exception:
        pass

    # Context of the Moment: current location, mood, recent events
    moment_facts = []
    inst = getattr(target_info, "get_sim_instance", lambda: None)()
    if inst is not None:
        moment_facts.append("Находится прямо сейчас на этом участке" if not is_en else "Currently on this lot")
    else:
        moment_facts.append("Находится вне участка" if not is_en else "Off-lot")

    try:
        mood_curr = target_info.get_current_mood()
        if mood_curr:
            m_name = getattr(mood_curr, "mood_name", getattr(mood_curr, "__name__", str(mood_curr)))
            if is_en and m_name:
                try:
                    from ai_thought_reader.context_en import translate_mood_en
                    m_name = translate_mood_en(m_name)
                except Exception:
                    pass
            moment_facts.append(f"Настроение: {m_name}" if not is_en else f"Mood: {m_name}")
    except Exception:
        pass

    try:
        from ai_social_pc.event_memory_manager import get_events_for_sim
        evs = get_events_for_sim(sid, max_events=2)
        if evs:
            e_titles = [e.get("title", "") for e in evs if e.get("title")]
            if e_titles:
                moment_facts.append(f"Недавние события: {', '.join(e_titles)}" if not is_en else f"Recent events: {', '.join(e_titles)}")
    except Exception:
        pass

    if moment_facts:
        lines.append(f"  • Контекст момента: {'; '.join(moment_facts)}" if not is_en else f"  • Context: {'; '.join(moment_facts)}")

    return "\n".join(lines)


def _format_neighborhood_dossier(participant_sim_infos: List[Any], is_en: bool = False) -> str:
    """Generates a summary card of all neighbor households living on the current street / neighborhood."""
    if not services:
        return ""

    try:
        cz = services.current_zone()
        if not cz:
            return ""
        nh_id = getattr(cz, "neighborhood_id", None) or getattr(cz, "neighborhood_zone_id", None)
        world_id = getattr(cz, "world_id", 0)

        hh_mgr = services.household_manager()
        if not hh_mgr:
            return ""

        active_hh = services.active_household()
        active_hh_id = getattr(active_hh, "id", 0) if active_hh else 0

        neighbor_entries = []
        for hh in hh_mgr.get_all():
            hh_id = getattr(hh, "id", 0)
            if hh_id == active_hh_id:
                continue
            h_zone = getattr(hh, "home_zone_id", 0)
            if not h_zone or h_zone <= 0:
                continue

            # Check if in same neighborhood
            h_nh = None
            try:
                zs = services.get_zone_situation_manager() if hasattr(services, "get_zone_situation_manager") else None
                # or check persistence
                ps = services.get_persistence_service()
                if ps:
                    z_data = ps.get_zone_proto_buff(h_zone)
                    if z_data:
                        h_nh = getattr(z_data, "neighborhood_id", None)
            except Exception:
                h_nh = None

            if (nh_id and h_nh == nh_id) or len(neighbor_entries) < 3:
                h_name = getattr(hh, "name", "House")
                members = []
                for s_inf in getattr(hh, "sim_infos", []):
                    if not getattr(s_inf, "is_pet", False):
                        members.append(getattr(s_inf, "first_name", ""))
                m_str = f" ({', '.join(members[:3])})" if members else ""
                neighbor_entries.append(f"Семья «{h_name}»{m_str}" if not is_en else f'"{h_name}" Household{m_str}')

            if len(neighbor_entries) >= 4:
                break

        if not neighbor_entries:
            return ""

        lines = [
            "[СВОДКА: Соседи на улице / по соседству]" if not is_en else "[SUMMARY: Neighborhood & Street Neighbors]",
            f"  • Соседние дома: {'; '.join(neighbor_entries)}" if not is_en else f"  • Neighbor homes: {'; '.join(neighbor_entries)}",
            "  • Примечание: Это реальные жители соседних домов на вашей улице." if not is_en else "  • Note: These are the actual living neighbors on your street."
        ]
        return "\n".join(lines)
    except Exception as e_nh:
        log_exception("Error formatting neighborhood dossier", e_nh)
        return ""


def _format_relatives_dossier(participant_sim_infos: List[Any], is_en: bool = False) -> str:
    """Generates a complete family tree breakdown for all conversation participants."""
    if not services:
        return ""

    sim_info_mgr = services.sim_info_manager()
    if not sim_info_mgr:
        return ""

    participant_ids = _extract_participant_ids(participant_sim_infos)
    lines = [
        "[СВОДКА: Семья и родственники собеседников]" if not is_en else "[SUMMARY: Participants' Living Family Members]"
    ]

    has_entries = False
    for p in participant_sim_infos:
        if not p:
            continue
        p_name = f"{getattr(p, 'first_name', '')}".strip() or ("Sim" if is_en else "Собеседник")
        gen = getattr(p, "genealogy", None)
        if not gen:
            continue

        p_family = []
        try:
            # Spouse
            sp_id = getattr(p, "spouse_sim_id", 0)
            if sp_id and sp_id not in participant_ids:
                s_info = sim_info_mgr.get(int(sp_id))
                if s_info:
                    sn = f"{getattr(s_info, 'first_name', '')} {getattr(s_info, 'last_name', '')}".strip()
                    p_family.append(f"Супруг(а): {sn}" if not is_en else f"Spouse: {sn}")

            # Children
            for cid in getattr(gen, "get_children_sim_ids", lambda: [])():
                if int(cid) not in participant_ids:
                    c_info = sim_info_mgr.get(int(cid))
                    if c_info:
                        cn = f"{getattr(c_info, 'first_name', '')}".strip()
                        p_family.append(f"Ребенок: {cn}" if not is_en else f"Child: {cn}")

            # Parents
            for pid in getattr(gen, "get_parent_sim_ids", lambda: [])():
                if int(pid) not in participant_ids:
                    par_info = sim_info_mgr.get(int(pid))
                    if par_info:
                        pn = f"{getattr(par_info, 'first_name', '')}".strip()
                        p_family.append(f"Родитель: {pn}" if not is_en else f"Parent: {pn}")

            # Siblings
            for sbid in getattr(gen, "get_siblings_sim_ids", lambda: [])():
                if int(sbid) not in participant_ids:
                    sb_info = sim_info_mgr.get(int(sbid))
                    if sb_info:
                        sbn = f"{getattr(sb_info, 'first_name', '')}".strip()
                        p_family.append(f"Брат/Сестра: {sbn}" if not is_en else f"Sibling: {sbn}")
        except Exception:
            pass

        if p_family:
            has_entries = True
            lines.append(f"  • Родня у {p_name}: {', '.join(p_family)}" if not is_en else f"  • {p_name}'s Family: {', '.join(p_family)}")

    if not has_entries:
        return ""
    return "\n".join(lines)


def build_third_party_dossier(text: str, participant_sim_infos: List[Any], is_en: bool = False) -> Optional[str]:
    """
    Main entry point: Analyzes dialogue text for third-party mentions.
    Returns a formatted multi-section Dossier block, or None if disabled or nothing detected.
    """
    if not is_dossier_enabled():
        return None

    if not text or not participant_sim_infos:
        return None

    try:
        detection = detect_third_party_references(text, participant_sim_infos)
        matched_sims = detection.get("matched_sims", [])
        trigger_neighbors = detection.get("trigger_neighbors", False)
        trigger_relatives = detection.get("trigger_relatives", False)

        if not matched_sims and not trigger_neighbors and not trigger_relatives:
            return None

        sections = []

        # 1. Individual character dossiers (up to 3)
        for target_info in matched_sims:
            s_dossier = _format_single_sim_dossier(target_info, participant_sim_infos, is_en=is_en)
            if s_dossier:
                sections.append(s_dossier)

        # 2. Neighbors summary (if triggered)
        if trigger_neighbors:
            nh_dossier = _format_neighborhood_dossier(participant_sim_infos, is_en=is_en)
            if nh_dossier:
                sections.append(nh_dossier)

        # 3. Relatives summary (if triggered)
        if trigger_relatives:
            rel_dossier = _format_relatives_dossier(participant_sim_infos, is_en=is_en)
            if rel_dossier:
                sections.append(rel_dossier)

        if not sections:
            return None

        header = "=== СПРАВКА О СТОРОННИХ ПЕРСОНАЖАХ И СВЯЗЯХ ===" if not is_en else "=== THIRD-PARTY CHARACTER DOSSIER & CONTEXT ==="
        footer = "================================================="
        body = "\n\n".join(sections)
        result_text = f"{header}\n{body}\n{footer}"
        log(f"[DOSSIER] Generated dossier for {len(matched_sims)} sim(s), neighbors={trigger_neighbors}, relatives={trigger_relatives}")
        return result_text
    except Exception as ex:
        log_exception("Error in build_third_party_dossier", ex)
        return None
