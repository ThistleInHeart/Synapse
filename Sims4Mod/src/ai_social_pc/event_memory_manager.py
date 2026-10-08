# -*- coding: utf-8 -*-
"""
Automatic In-Game Event Memory Manager for Synapse AI.
Automatically forms episodic memories for Sims based on key live in-game events
(intimacy, WickedWhims, proposal, marriage, breakup, cheating, pregnancy, birth,
death, fights, career changes, fires, and occult transformations) without calling
the LLM — zero latency, zero token cost, 100% reliable.
"""

import time
import services
from typing import Dict, List, Any, Optional, Set, Tuple
from ai_social_pc.logger import log, log_exception
from ai_social_pc.memory_manager import add_memory, add_personal_memory, get_active_memories, remove_memories_by_types

# =========================================================================
# 1. CATALOG OF TEMPLATES, LIFE DURATIONS (DAYS) & TRANSLATIONS
# =========================================================================

EVENT_MEMORY_TEMPLATES = {
    # --- Intimacy & WickedWhims ---
    "intimacy_recent": {
        "days": 3,
        "ru": "У нас с {target} недавно был страстный секс.",
        "en": "{target} and I recently had passionate sex together.",
    },
    "intimacy_solo": {
        "days": 2,
        "ru": "Недавно я провел(а) время наедине с собой и занялся(лась) мастурбацией.",
        "en": "I recently spent some private time alone masturbating.",
    },
    "intimacy_group": {
        "days": 5,
        "ru": "У нас с {target} и другими партнерами был групповой секс.",
        "en": "{target} and I had group sex with other partners.",
    },
    "intimacy_cheating": {
        "days": 7,
        "ru": "У меня был тайный секс с {lover} за спиной у моего партнера ({partner}).",
        "en": "I had secret sex with {lover} behind my partner {partner}'s back.",
    },
    "cheating_caught": {
        "days": 14,
        "ru": "Я застукал(а) {partner} на измене с {lover}! Моё доверие растоптано вдребезги.",
        "en": "I caught {partner} cheating on me with {lover}! My trust has been shattered.",
    },
    "cheating_caught_cheater": {
        "days": 10,
        "ru": "{partner} застукал(а) меня прямо на измене с {lover}! Меня поймали с поличным...",
        "en": "{partner} caught me red-handed in bed with {lover}! My affair has been exposed...",
    },
    "intimacy_offspring_child": {
        "days": 5,
        "ru": "Я случайно увидел(а), как мои родители ({parent1} и {parent2}) занимались интимом... Мои глаза! Мне нужна психологическая помощь, я никогда этого не забуду!",
        "en": "I accidentally walked in on my parents ({parent1} and {parent2}) having intimacy... My eyes! I'm scarred for life, I will never unsee that!",
    },
    "intimacy_offspring_child_solo": {
        "days": 5,
        "ru": "Я случайно увидел(а), как мой родитель ({parent}) был(а) застигнут(а) врасплох за интимом в одиночестве... Мои глаза! Мне нужна психологическая помощь, я никогда этого не забуду!",
        "en": "I accidentally walked in on my parent ({parent}) having solo intimacy... My eyes! I'm scarred for life, I will never unsee that!",
    },
    "intimacy_offspring_parents": {
        "days": 4,
        "ru": "Наш собственный ребенок ({child_name}) застукал нас с {partner} прямо посреди секса! Какой дикий конфуз перед детьми...",
        "en": "Our child ({child_name}) walked in on {partner} and me having sex! What a mortifying embarrassment in front of our kids...",
    },
    "intimacy_offspring_parent_solo": {
        "days": 4,
        "ru": "Мой собственный ребенок ({child_name}) застукал меня прямо во время мастурбации! Какой дикий конфуз и стыд перед ребенком...",
        "en": "My own child ({child_name}) walked in on me masturbating! What a mortifying embarrassment and shame in front of my child...",
    },
    "intimacy_caught_home_actors": {
        "days": 3,
        "ru": "Нас с {target} застукали за сексом прямо у нас дома ({witness} не вовремя вошел(ла) в комнату)!",
        "en": "{target} and I were caught having sex right at our house ({witness} barged into the room)!",
    },
    "intimacy_caught_home_witness": {
        "days": 3,
        "ru": "Я случайно застал(а) {actor} и {target} за сексом у нас дома... Какой неловкий стыд.",
        "en": "I accidentally caught {actor} and {target} having sex at our house... What an awkward embarrassment.",
    },
    "intimacy_solo_caught_home_actor": {
        "days": 3,
        "ru": "Меня застукали за мастурбацией прямо у нас дома ({witness} не вовремя вошел(ла) в комнату)!",
        "en": "I was caught masturbating right at home ({witness} barged into the room at the worst time)!",
    },
    "intimacy_solo_caught_home_witness": {
        "days": 3,
        "ru": "Я случайно застал(а) {actor} за мастурбацией у нас дома... Какой неловкий стыд.",
        "en": "I accidentally caught {actor} masturbating at our house... What an awkward embarrassment.",
    },
    "intimacy_caught_guests_actors": {
        "days": 4,
        "ru": "Нас с {target} застукали за сексом на вечеринке / в чужом доме!",
        "en": "{target} and I were caught having sex at someone else's house / party!",
    },
    "intimacy_caught_guests_witness": {
        "days": 4,
        "ru": "{actor} и {target} нагло устроили секс прямо у меня в доме / на вечеринке!",
        "en": "{actor} and {target} shamelessly had sex right at my place / at the party!",
    },
    "intimacy_solo_caught_guests_actor": {
        "days": 4,
        "ru": "Меня застукали за мастурбацией на вечеринке / в чужом доме!",
        "en": "I was caught masturbating at someone else's house / party!",
    },
    "intimacy_solo_caught_guests_witness": {
        "days": 4,
        "ru": "{actor} нагло занимался(лась) мастурбацией прямо у меня в доме / на вечеринке!",
        "en": "{actor} shamelessly masturbated right at my place / at the party!",
    },
    "intimacy_caught_public_actors": {
        "days": 5,
        "ru": "Нас с {target} поймали за сексом в общественном месте на глазах у посторонних!",
        "en": "{target} and I were caught having sex in public in front of bystanders!",
    },
    "intimacy_caught_public_witness": {
        "days": 3,
        "ru": "Я видел(а), как {actor} и {target} средь бела дня занимались сексом в общественном месте!",
        "en": "I saw {actor} and {target} having sex in public in broad daylight!",
    },
    "intimacy_solo_caught_public_actor": {
        "days": 5,
        "ru": "Меня поймали за мастурбацией в общественном месте на глазах у посторонних!",
        "en": "I was caught masturbating in public in front of bystanders!",
    },
    "intimacy_solo_caught_public_witness": {
        "days": 3,
        "ru": "Я видел(а), как {actor} средь бела дня занимался(лась) мастурбацией в общественном месте!",
        "en": "I saw {actor} masturbating in public in broad daylight!",
    },

    # --- Romance, Proposals & Marriage ---
    "romance_became_couple": {
        "days": 7,
        "ru": "Мы с {target} начали встречаться и признались друг другу в чувствах.",
        "en": "{target} and I started dating and confessed our feelings to each other.",
    },
    "romance_first_kiss": {
        "days": 7,
        "ru": "Мы с {target} впервые поцеловались!",
        "en": "{target} and I shared our first kiss!",
    },
    "romance_cheating_caught": {
        "days": 7,
        "ru": "Я застукал(а), как {partner} флиртует и заигрывает с {lover}! Это предательство.",
        "en": "I caught {partner} flirting and fooling around with {lover}! What a betrayal.",
    },
    "romance_cheating_flirter": {
        "days": 4,
        "ru": "{partner} застал(а) меня за флиртом с {lover}... Кажется, у меня крупные проблемы.",
        "en": "{partner} caught me flirting with {lover}... Looks like I'm in serious trouble.",
    },
    "proposal_accepted_proposer": {
        "days": 14,
        "ru": "Я сделал(а) предложение {target}, и мы теперь обручены!",
        "en": "I proposed to {target}, and we are now engaged!",
    },
    "proposal_accepted_target": {
        "days": 14,
        "ru": "{target} сделал(а) мне предложение руки и сердца, и мы готовимся к свадьбе!",
        "en": "{target} proposed to me, and we are getting ready for our wedding!",
    },
    "proposal_rejected_proposer": {
        "days": 10,
        "ru": "{target} отверг(ла) мое предложение руки и сердца... Мне ужасно больно и стыдно.",
        "en": "{target} rejected my marriage proposal... I feel heartbroken and humiliated.",
    },
    "proposal_rejected_target": {
        "days": 7,
        "ru": "Я отверг(ла) предложение {target}, брак с ним/ней сейчас не входит в мои планы.",
        "en": "I rejected {target}'s proposal; marriage with them is not in my plans right now.",
    },
    "wedding_newlyweds": {
        "days": 14,
        "ru": "Мы с {target} недавно поженились и отпраздновали свадьбу! Мы молодожены.",
        "en": "{target} and I recently got married and tied the knot! We are newlyweds.",
    },
    "breakup_divorce": {
        "days": 14,
        "ru": "Мы с {target} окончательно расстались и разорвали отношения.",
        "en": "{target} and I officially broke up and ended our relationship.",
    },

    # --- Pregnancy, Alien & Childbirth ---
    "pregnancy_mother": {
        "days": 7,
        "ru": "Я узнала, что беременна от {target}! Во мне зарождается ребенок.",
        "en": "I discovered that I am pregnant with {target}'s child! A new life is growing inside me.",
    },
    "pregnancy_father": {
        "days": 7,
        "ru": "{target} сообщила, что ждет от меня ребенка! Я скоро стану родителем.",
        "en": "{target} told me she is expecting my baby! I'm going to be a parent soon.",
    },
    "pregnancy_alien_male": {
        "days": 7,
        "ru": "Меня похитили пришельцы, и теперь я вынашиваю инопланетный плод... Это безумие!",
        "en": "I was abducted by aliens and now I'm carrying an alien offspring... This is crazy!",
    },
    "baby_born": {
        "days": 10,
        "ru": "У нас родился ребенок! Малыш {baby_name} появился на свет.",
        "en": "Our baby was born! Little {baby_name} has arrived into the world.",
    },
    "child_aged_up": {
        "days": 3,
        "ru": "Наш ребенок {target} отпраздновал день рождения и перешел на новый этап жизни.",
        "en": "Our child {target} celebrated their birthday and entered a new stage of life.",
    },

    # --- Death & Grief ---
    "death_loved_one": {
        "days": 14,
        "ru": "{target} трагически погиб(ла)... Тяжелая скорбь и невосполнимая утрата разрывают мне сердце.",
        "en": "{target} passed away tragically... Heavy grief and irreplaceable loss break my heart.",
    },
    "death_enemy": {
        "days": 5,
        "ru": "Мой заклятый враг {target} отправился на тот свет. Туда ему/ей и дорога.",
        "en": "My arch-enemy {target} kicked the bucket. Good riddance.",
    },
    "saved_death_savior": {
        "days": 7,
        "ru": "Мне удалось вымолить жизнь {target} у самой Костлявой Смерти!",
        "en": "I managed to plead for {target}'s life with the Grim Reaper himself!",
    },
    "saved_death_survivor": {
        "days": 10,
        "ru": "{target} спас(ла) меня от когтей Смерти, когда я был(а) на волосок от гибели!",
        "en": "{target} saved me from Death's grasp when I was on the brink of demise!",
    },
    "ghost_relative_met": {
        "days": 4,
        "ru": "Я встретил(а) призрак покойного(ой) {target}... Прошлое словно вернулось из потустороннего мира.",
        "en": "I encountered the ghost of deceased {target}... It felt like the past returned from the beyond.",
    },

    # --- Fights & Conflicts ---
    "fight_won": {
        "days": 5,
        "ru": "Я подрался(лась) с {target} и хорошенько начистил(а) ему/ей лицо!",
        "en": "I got into a fight with {target} and beat them up good!",
    },
    "fight_lost": {
        "days": 5,
        "ru": "{target} избил(а) меня в драке... Это позорное поражение, я этого так не оставлю.",
        "en": "{target} beat me in a fight... It was a humiliating defeat, I won't let this go.",
    },
    "declared_enemies": {
        "days": 14,
        "ru": "Мы с {target} стали заклятыми врагами. Я презираю каждую минуту рядом с ним/ней.",
        "en": "{target} and I have become sworn enemies. I despise every minute near them.",
    },
    "theft_victim": {
        "days": 5,
        "ru": "{target} украл(а) у меня ценную вещь прямо из-под носа!",
        "en": "{target} stole something valuable right from under my nose!",
    },

    # --- Career, Wealth & Incidents ---
    "career_promoted": {
        "days": 5,
        "ru": "Меня повысили на работе, теперь у меня новая должность.",
        "en": "I got promoted at work and transitioned to a new position.",
    },
    "career_fired": {
        "days": 5,
        "ru": "Меня со скандалом уволили с работы... Придется искать новый источник дохода.",
        "en": "I was fired from my job... Now I have to find a new source of income.",
    },
    "lottery_win": {
        "days": 10,
        "ru": "Семья сорвала куш и выиграла миллионы в лотерею! Мы баснословно богаты!",
        "en": "The family hit the jackpot and won millions in the lottery! We are filthy rich!",
    },
    "house_fire": {
        "days": 4,
        "ru": "В доме вспыхнул страшный пожар! Мы чудом спаслись от огня, но страх еще не прошел.",
        "en": "A terrifying fire broke out in the house! We narrowly escaped the flames, the shock hasn't worn off.",
    },
    "college_graduation": {
        "days": 7,
        "ru": "Я успешно закончил(а) университет и получил(а) диплом высшего образования!",
        "en": "I successfully graduated from university and earned my degree!",
    },

    # --- Occult Transformations ---
    "occult_vampire": {
        "days": 10,
        "ru": "{target} обратил(а) меня в вампира. Моя человеческая жизнь закончена, теперь я дитя тьмы.",
        "en": "{target} turned me into a vampire. My human life is over, I am now a child of the night.",
    },
    "occult_werewolf": {
        "days": 7,
        "ru": "Я заразился(лась) проклятием оборотня после схватки с {target}. Зверь внутри рвется наружу!",
        "en": "I contracted lycanthropy after a clash with {target}. The beast within is clawing its way out!",
    },
    "occult_spellcaster": {
        "days": 7,
        "ru": "Мудрец {target} провел(а) обряд вознесения и пробудил(а) во мне магический дар.",
        "en": "Sage {target} performed the Rite of Ascension and awakened my magical gift.",
    },
    "occult_cured": {
        "days": 7,
        "ru": "Я принял(а) лекарство и избавился(лась) от оккультного проклятия. Я снова обычный человек!",
        "en": "I took the cure and broke free from the occult curse. I am a normal human again!",
    },
}

# In-memory debounce to prevent spamming duplicate events within short window
_EVENT_DEBOUNCE: Dict[str, float] = {}
_LAST_PERIODIC_CHECK_TIME: float = 0.0

# State tracking dictionaries
_PREGNANCY_STATE: Dict[int, bool] = {}
_DEATH_STATE: Set[int] = set()
_DEATH_INITIALIZED: bool = False
_CAREER_LEVELS: Dict[Any, int] = {}
_OCCULT_STATE: Dict[int, str] = {}
_FIRE_WAS_ACTIVE: bool = False
_ACTIVE_SEX_SESSIONS: Set[str] = set()
_ACTIVE_SEX_WITNESSES: Set[Tuple[str, int]] = set()
_CURRENT_SEX_SIM_IDS: Set[int] = set()


# =========================================================================
# 2. HELPER FUNCTIONS
# =========================================================================

def _get_sim_name(sim_info) -> str:
    if sim_info is None:
        return "Сим"
    f = getattr(sim_info, "first_name", "") or ""
    l = getattr(sim_info, "last_name", "") or ""
    name = f"{f} {l}".strip()
    return name if name else (f or "Сим")


def _is_debounced(key: str, cooldown_seconds: float = 120.0) -> bool:
    now = time.time()
    last = _EVENT_DEBOUNCE.get(key, 0.0)
    if now - last < cooldown_seconds:
        return True
    _EVENT_DEBOUNCE[key] = now
    return False


def record_event_memory(
    template_key: str,
    actor_sim_info,
    target_sim_info=None,
    duration_override: int = None,
    extra_context: Optional[Dict[str, str]] = None
) -> bool:
    """
    Constructs and persists an episodic memory from the catalog.
    Bilingual (RU and EN), with zero LLM queries.
    """
    if template_key not in EVENT_MEMORY_TEMPLATES or actor_sim_info is None:
        return False

    actor_id = getattr(actor_sim_info, "sim_id", 0)
    if not actor_id:
        return False

    target_id = getattr(target_sim_info, "sim_id", 0) if target_sim_info is not None else 0

    tpl = EVENT_MEMORY_TEMPLATES[template_key]
    days = duration_override if duration_override is not None else tpl.get("days", 3)

    actor_name = _get_sim_name(actor_sim_info)
    target_name = _get_sim_name(target_sim_info) if target_sim_info else ""

    ctx_ru = {
        "actor": actor_name,
        "target": target_name or ("партнером" if "intimacy" in template_key else "соперником" if "fight" in template_key else "собеседником"),
        "partner": target_name or "партнером",
        "lover": target_name or "любовником",
        "parent": target_name or "Родитель",
        "witness": "Очевидец",
        "baby_name": "Малыш",
        "parent1": "Родитель 1",
        "parent2": "Родитель 2",
        "child_name": "Ребёнок",
    }
    ctx_en = {
        "actor": actor_name,
        "target": target_name or ("partner" if "intimacy" in template_key else "an opponent" if "fight" in template_key else "another Sim"),
        "partner": target_name or "partner",
        "lover": target_name or "lover",
        "parent": target_name or "Parent",
        "witness": "A bystander",
        "baby_name": "little one",
        "parent1": "Parent 1",
        "parent2": "Parent 2",
        "child_name": "child",
    }
    if extra_context:
        for k, v in extra_context.items():
            if k.endswith("_ru"):
                ctx_ru[k[:-3]] = v
            elif k.endswith("_en"):
                ctx_en[k[:-3]] = v
            else:
                ctx_ru[k] = v
                ctx_en[k] = v

    # Safe formatting
    try:
        ru_text = tpl["ru"].format(**ctx_ru)
    except Exception:
        ru_text = tpl["ru"]

    try:
        en_text = tpl["en"].format(**ctx_en)
    except Exception:
        en_text = tpl["en"]

    debounce_key = f"{template_key}_{actor_id}_{target_id}_{ctx_ru.get('lover', '')}"
    if _is_debounced(debounce_key, cooldown_seconds=60.0):
        return False

    if target_id and target_id != actor_id:
        add_memory(actor_id, target_id, ru_text, days, summary_en=en_text, event_type=template_key)
    else:
        add_personal_memory(actor_id, ru_text, days, summary_en=en_text, event_type=template_key)

    log(f"[EVENT MEMORY] Stored '{template_key}' for Sim {actor_id} ({actor_name}): '{ru_text}' (Duration: {days} days)")
    return True


# =========================================================================
# 3. RELATIONSHIP BITS LISTENER (Marriage, Proposal, Breakup, Enemies)
# =========================================================================

def on_relationship_bit_added(sim_id_a: int, sim_id_b: int, bit_obj):
    """
    Hooked directly onto RelationshipService.add_relationship_bit.
    Fires when a meaningful relationship status bit is assigned in live gameplay.
    """
    try:
        if not sim_id_a or not sim_id_b or not bit_obj:
            return

        sim_mgr = services.sim_info_manager() if services is not None else None
        if not sim_mgr:
            return

        info_a = sim_mgr.get(sim_id_a)
        info_b = sim_mgr.get(sim_id_b)
        if not info_a or not info_b:
            return

        b_name = getattr(bit_obj, "__name__", str(bit_obj)).lower()

        # 1. Breakup / Divorce / Broken Engagement (14 days) - MUST BE CHECKED FIRST!
        # Prevents "romantic-broken_up_engaged" or "broken_engagement" from ever triggering proposal/wedding!
        if any(k in b_name for k in ("broken", "divorce", "ex_spouse", "ex_partner", "breakup", "separated")):
            record_event_memory("breakup_divorce", info_a, target_sim_info=info_b)
            record_event_memory("breakup_divorce", info_b, target_sim_info=info_a)
            # Instantly purge conflicting romantic statuses between the pair
            try:
                from ai_social_pc.memory_manager import remove_memories_by_types
                conflicting = ["wedding_newlyweds", "proposal_accepted_proposer", "proposal_accepted_target", "romance_became_couple"]
                remove_memories_by_types(sim_id_a, sim_id_b, conflicting)
                remove_memories_by_types(sim_id_b, sim_id_a, conflicting)
            except Exception:
                pass

        # 2. Wedding / Marriage (Newlyweds phase - 14 days)
        elif any(k in b_name for k in ("married", "wedding")) and not any(k in b_name for k in ("broken", "divorce", "ex_")):
            record_event_memory("wedding_newlyweds", info_a, target_sim_info=info_b)
            record_event_memory("wedding_newlyweds", info_b, target_sim_info=info_a)

        # 3. Proposal Accepted (Engaged - 14 days)
        elif any(k in b_name for k in ("engaged", "fiance", "proposal")) and not any(k in b_name for k in ("broken", "divorce", "ex_")):
            record_event_memory("proposal_accepted_proposer", info_a, target_sim_info=info_b)
            record_event_memory("proposal_accepted_target", info_b, target_sim_info=info_a)

        # 4. Became Couple / Romantic relationship (7 days)
        elif any(k in b_name for k in ("significant_other", "boyfriend_girlfriend", "sweethearts")) and not any(k in b_name for k in ("broken", "divorce", "ex_")):
            record_event_memory("romance_became_couple", info_a, target_sim_info=info_b)
            record_event_memory("romance_became_couple", info_b, target_sim_info=info_a)

        # 5. First Kiss (7 days)
        elif "firstkiss" in b_name:
            record_event_memory("romance_first_kiss", info_a, target_sim_info=info_b)
            record_event_memory("romance_first_kiss", info_b, target_sim_info=info_a)

        # 6. Enemies / Despised (14 days)
        elif any(k in b_name for k in ("despised", "enemies", "enemy")):
            record_event_memory("declared_enemies", info_a, target_sim_info=info_b)
            record_event_memory("declared_enemies", info_b, target_sim_info=info_a)

        # 7. Cheating / Unfaithful bit (TS4's romantic-HasBeenUnfaithful)
        elif any(k in b_name for k in ("unfaithful", "hasbeenunfaithful", "cheated", "cheating", "infidelity")):
            lover = _find_lover_for_cheating(info_a, info_b)
            if lover:
                _trigger_cheating_caught(info_a, info_b, lover)
            else:
                lover2 = _find_lover_for_cheating(info_b, info_a)
                if lover2:
                    _trigger_cheating_caught(info_b, info_a, lover2)
                else:
                    _trigger_cheating_caught(info_a, info_b, None)

    except Exception as e:
        log_exception("Error in on_relationship_bit_added handler", e)


# =========================================================================
# 4. INTIMACY & WICKEDWHIMS LISTENER (Caught in the Act, Offspring, Infidelity)
# =========================================================================

def _get_partner_info(sim_info):
    """Returns the spouse or steady romantic partner SimInfo if one exists."""
    if not sim_info:
        return None
    try:
        sim_mgr = services.sim_info_manager() if services is not None else None
        if not sim_mgr:
            return None
        sim_id = getattr(sim_info, "sim_id", 0)
        if not sim_id:
            return None

        # 1. Direct spouse_sim_id
        sp_id = getattr(sim_info, "spouse_sim_id", 0)
        if sp_id and sp_id != sim_id:
            sp = sim_mgr.get(sp_id)
            if sp:
                return sp

        # 2. Direct fiance_sim_id
        fc_id = getattr(sim_info, "fiance_sim_id", 0)
        if fc_id and fc_id != sim_id:
            fc = sim_mgr.get(fc_id)
            if fc:
                return fc

        # 3. Genealogy spouse
        gen = getattr(sim_info, "genealogy", None)
        if gen is not None:
            for s_attr in ("get_spouse_sim_info", "get_spouse"):
                if hasattr(gen, s_attr):
                    try:
                        res = getattr(gen, s_attr)()
                        if res and getattr(res, "sim_id", 0) != sim_id:
                            return res
                    except Exception:
                        pass
            for sid_attr in ("_spouse_id", "spouse_id"):
                if hasattr(gen, sid_attr):
                    val = getattr(gen, sid_attr, 0)
                    if val and val != sim_id:
                        cand = sim_mgr.get(val)
                        if cand:
                            return cand

        # 4. Search RelationshipTracker & RelationshipService
        rt = getattr(sim_info, "relationship_tracker", None)
        rel_targets = set()

        if rt is not None:
            if hasattr(rt, "_relationships"):
                for rel in getattr(rt._relationships, "values", lambda: [])():
                    t1 = getattr(rel, "sim_id_a", None)
                    t2 = getattr(rel, "sim_id_b", None)
                    tid = t2 if t1 == sim_id else t1
                    if tid and tid != sim_id:
                        rel_targets.add(tid)
            elif hasattr(rt, "get_all_relationships"):
                for rel in (rt.get_all_relationships() or []):
                    t1 = getattr(rel, "sim_id_a", None)
                    t2 = getattr(rel, "sim_id_b", None)
                    tid = t2 if t1 == sim_id else t1
                    if tid and tid != sim_id:
                        rel_targets.add(tid)

        rel_svc = services.relationship_service() if services is not None else None
        if rel_svc is not None and hasattr(rel_svc, "target_sim_gen"):
            try:
                for tid in rel_svc.target_sim_gen(sim_id):
                    if tid and tid != sim_id:
                        rel_targets.add(tid)
            except Exception:
                pass

        for other in sim_mgr.values():
            if other and getattr(other, "sim_id", 0) != sim_id:
                rel_targets.add(getattr(other, "sim_id", 0))

        PARTNER_BIT_KEYWORDS = (
            "married", "spouse", "husband", "wife", "family_husband_wife",
            "engaged", "fiance",
            "significant_other", "boyfriend_girlfriend", "sweethearts", "lovebirds"
        )

        for tid in rel_targets:
            if not tid or tid == sim_id:
                continue
            bits = []
            if rt is not None and hasattr(rt, "get_all_bits"):
                try:
                    bits = rt.get_all_bits(tid) or []
                except Exception:
                    pass
            elif rel_svc is not None and hasattr(rel_svc, "get_all_bits"):
                try:
                    bits = rel_svc.get_all_bits(sim_id, tid) or []
                except Exception:
                    pass

            for b in bits:
                bn = getattr(b, "__name__", str(b)).lower()
                if any(k in bn for k in ("broken", "divorce", "ex_spouse", "ex_partner", "separated")):
                    continue
                if any(k in bn for k in PARTNER_BIT_KEYWORDS):
                    cand = sim_mgr.get(tid)
                    if cand:
                        return cand

    except Exception as e:
        log_exception("Error in _get_partner_info", e)
    return None


def _is_child_of(child_info, parent_info) -> bool:
    """
    Bulletproof check to determine if child_info is an offspring/child of parent_info.
    Checks parent SimInfos, child SimInfos, genealogy trackers, and relationship bits.
    """
    if not child_info or not parent_info:
        return False
    try:
        c_id = getattr(child_info, "sim_id", 0)
        p_id = getattr(parent_info, "sim_id", 0)
        if not c_id or not p_id or c_id == p_id:
            return False

        # 1. Direct parent SimInfos from child
        for direct_attr in ("get_parent_sim_infos", "get_parents"):
            if hasattr(child_info, direct_attr):
                try:
                    res = getattr(child_info, direct_attr)()
                    if res:
                        for p in res:
                            if getattr(p, "sim_id", 0) == p_id:
                                return True
                except Exception:
                    pass

        # 2. Genealogy tracker from child
        gen = getattr(child_info, "genealogy_tracker", None)
        if gen:
            try:
                if hasattr(gen, "get_parent_sim_ids"):
                    if p_id in (gen.get_parent_sim_ids() or []):
                        return True
                for p_attr in ("_parent_ids", "parent_ids"):
                    if hasattr(gen, p_attr):
                        if p_id in (getattr(gen, p_attr) or []):
                            return True
            except Exception:
                pass

        # 3. Direct children SimInfos from parent
        for child_attr in ("get_child_sim_infos", "get_children"):
            if hasattr(parent_info, child_attr):
                try:
                    res = getattr(parent_info, child_attr)()
                    if res:
                        for c in res:
                            if getattr(c, "sim_id", 0) == c_id:
                                return True
                except Exception:
                    pass

        # 4. Genealogy tracker from parent
        gen_p = getattr(parent_info, "genealogy_tracker", None)
        if gen_p:
            try:
                if hasattr(gen_p, "get_child_sim_ids"):
                    if c_id in (gen_p.get_child_sim_ids() or []):
                        return True
                for c_attr in ("_child_ids", "child_ids"):
                    if hasattr(gen_p, c_attr):
                        if c_id in (getattr(gen_p, c_attr) or []):
                            return True
            except Exception:
                pass

        # 5. Relationship tracker on child towards parent
        rt_c = getattr(child_info, "relationship_tracker", None)
        if rt_c and hasattr(rt_c, "get_all_bits"):
            try:
                for b in (rt_c.get_all_bits(p_id) or []):
                    b_str = getattr(b, "__name__", str(b)).lower()
                    if any(k in b_str for k in ("parent", "mother", "father", "stepparent", "step_parent")):
                        return True
            except Exception:
                pass

        # 6. Relationship tracker on parent towards child
        rt_p = getattr(parent_info, "relationship_tracker", None)
        if rt_p and hasattr(rt_p, "get_all_bits"):
            try:
                for b in (rt_p.get_all_bits(c_id) or []):
                    b_str = getattr(b, "__name__", str(b)).lower()
                    if any(k in b_str for k in ("child", "son", "daughter", "stepchild", "step_child", "stepson", "stepdaughter")):
                        return True
            except Exception:
                pass

    except Exception as e:
        log_exception("Error in _is_child_of", e)
    return False


def _check_and_process_intimacy_events():
    """
    Monitors active WickedWhims sex instances or standard WooHoo.
    Detects sex sessions, catches in the act (offspring, cheating, guests, public),
    and records 3-day intimacy memories.
    """
    global _ACTIVE_SEX_SESSIONS, _ACTIVE_SEX_WITNESSES, _CURRENT_SEX_SIM_IDS
    try:
        active_instances = []
        try:
            from wickedwhims.sex.integral.sex_handlers.active_sex.active_sex_handlers import get_active_sex_instances
            active_instances = get_active_sex_instances() or []
        except Exception:
            active_instances = []

        current_session_keys = set()
        current_sex_sims = set()
        sim_mgr = services.sim_info_manager() if services is not None else None
        if not sim_mgr:
            return

        for inst in active_instances:
            if not inst or not hasattr(inst, "get_actors_as_sim_id"):
                continue

            raw_actor_ids = list(inst.get_actors_as_sim_id() or [])
            if not raw_actor_ids:
                continue

            for s_id in raw_actor_ids:
                current_sex_sims.add(int(s_id))

            session_key = "_".join(sorted(str(i) for i in raw_actor_ids))
            current_session_keys.add(session_key)

            participants = [sim_mgr.get(s_id) for s_id in raw_actor_ids if sim_mgr.get(s_id)]
            if not participants:
                continue

            p1 = participants[0]
            p2 = participants[1] if len(participants) > 1 else None
            p1_name = _get_sim_name(p1)
            p2_name = _get_sim_name(p2) if p2 else ""

            # Record participant intimacy memories ONCE per sex session
            if session_key not in _ACTIVE_SEX_SESSIONS:
                _ACTIVE_SEX_SESSIONS.add(session_key)

                if len(participants) == 1:
                    # Base solo masturbation memory for participant (2 days)
                    record_event_memory("intimacy_solo", p1)
                elif len(participants) == 2:
                    # 1. Base Intimacy Memory for Participants (3 days for pair, 5 days for group)
                    record_event_memory("intimacy_recent", p1, target_sim_info=p2)
                    record_event_memory("intimacy_recent", p2, target_sim_info=p1)
                else:
                    for part in participants:
                        other_names = [_get_sim_name(o) for o in participants if o != part]
                        record_event_memory("intimacy_group", part, extra_context={"target": ", ".join(other_names)})

                # 2. Check Infidelity for each participant (pair or group only)
                if len(participants) >= 2:
                    for part in participants:
                        partner = _get_partner_info(part)
                        if partner and partner not in participants:
                            partner_name = _get_sim_name(partner)
                            lovers = [_get_sim_name(o) for o in participants if o != part]
                            lover_str = ", ".join(lovers)
                            # Cheater's memory (neutral fact: had secret intimacy behind partner's back)
                            record_event_memory(
                                "intimacy_cheating",
                                part,
                                extra_context={"partner": partner_name, "lover": lover_str}
                            )

            # 3. Check for Walk-ins / Witnesses in the SAME ROOM
            # (Allows catching them if someone enters the room mid-session, while recording each witness only once)
            _check_sex_witnesses(participants, p1, p2, p1_name, p2_name, session_key, sex_instance=inst)

        # Also check standard EA WooHoo interactions
        for info in sim_mgr.values():
            if info is None or getattr(info, "is_pet", False):
                continue
            sim_inst = info.get_sim_instance() if hasattr(info, "get_sim_instance") else None
            if not sim_inst:
                continue
            try:
                si_state = getattr(sim_inst, "si_state", None)
                running_sis = getattr(si_state, "_sis", set()) if si_state else []
                for inter in running_sis:
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff)).lower() if aff else ""
                    if "woohoo" in aff_name:
                        current_sex_sims.add(getattr(info, "sim_id", 0))
                        tgt = getattr(inter, "target", None)
                        if tgt and hasattr(tgt, "sim_info"):
                            current_sex_sims.add(getattr(tgt.sim_info, "sim_id", 0))
            except Exception:
                pass

        _CURRENT_SEX_SIM_IDS = current_sex_sims

        # Cleanup finished sex sessions and witness keys
        _ACTIVE_SEX_SESSIONS.intersection_update(current_session_keys)
        _ACTIVE_SEX_WITNESSES = {w for w in _ACTIVE_SEX_WITNESSES if w[0] in current_session_keys}

    except Exception as e:
        log_exception("Error processing intimacy events", e)


def _has_sex_line_of_sight(viewer_inst, p1_instance, sex_instance=None) -> bool:
    """
    Checks if viewer_inst has an unblocked line of sight to the sex participants / location.
    Uses WickedWhims TurboLineOfSight (raycast/convex polygon) and EA LineOfSightComponent.
    """
    if not viewer_inst or not p1_instance:
        return False
    try:
        # Determine target sex position
        target_pos = None
        if sex_instance and hasattr(sex_instance, "get_los_position"):
            try:
                target_pos = sex_instance.get_los_position()
            except Exception:
                target_pos = None
        if target_pos is None:
            target_pos = getattr(p1_instance, "position", None)
        if target_pos is None:
            return False

        # 1. WickedWhims TurboLineOfSight (native raycast/convex polygon)
        try:
            from turbolib2.wrappers.line_of_sight import TurboLineOfSight
            routing_surface = getattr(viewer_inst, "routing_surface", None)
            los = TurboLineOfSight(viewer_inst.position, routing_surface, radius=15.0)
            if los.has_line_of_sight(target_pos):
                return True
        except Exception:
            pass

        # 2. EA LineOfSightComponent constraint geometry
        try:
            los_comp = getattr(viewer_inst, "lineofsight_component", None)
            if los_comp:
                convex = los_comp.constraint_convex
                if convex and hasattr(convex, "geometry") and convex.geometry:
                    if hasattr(convex.geometry, "contains_point"):
                        if convex.geometry.contains_point(target_pos):
                            return True
        except Exception:
            pass
    except Exception:
        pass
    return False


def _has_sex_witness_reaction(inst_sim, is_jealous_partner: bool = False) -> bool:
    """Checks if the Sim is currently executing a jealousy or sex reaction interaction."""
    if not inst_sim:
        return False
    try:
        si_state = getattr(inst_sim, "si_state", None)
        running_sis = getattr(si_state, "_sis", set()) if si_state else []
        for inter in running_sis:
            aff = getattr(inter, "affordance", None)
            aff_name = (getattr(aff, "__name__", "") or str(aff)).lower() if aff else ""
            inter_name = (getattr(inter, "__name__", "") or str(inter)).lower()
            comb = f"{aff_name} {inter_name}"
            if "jealous" in comb or "reaction_jealousy" in comb:
                return True
            if not is_jealous_partner:
                if any(k in comb for k in ("watch_sex", "react_to_sex", "embarrass", "gasp", "shocked", "disgusted", "inappropriate", "go_away")):
                    return True
    except Exception:
        pass
    return False


def _has_sex_witness_buff(sim_info, is_jealous_partner: bool = False) -> bool:
    """Checks if the Sim has an active jealousy or witness moodlet/buff."""
    if not sim_info:
        return False
    JEALOUSY_BUFF_KEYWORDS = (
        "cheatingwitnessed", "witness_cheating", "witnessed_cheating",
        "flirtwitnessed", "flirt_witnessed", "kisswitnessed", "kiss_witnessed",
        "woohoowitnessed", "woohoo_witnessed", "caught_cheating", "caughtcheating",
        "fear_beingcheatedon", "fear_of_cheating", "jealousy", "ww_jealousy",
        "caught_sex_cheating"
    )
    GENERAL_WITNESS_BUFF_KEYWORDS = (
        "witnessed_sex", "caught_in_the_act", "walked_in_on_sex", "inappropriate_sex"
    )
    try:
        buff_tracker = getattr(sim_info, "buff_component", None) or getattr(sim_info, "BuffComponent", None)
        if buff_tracker and hasattr(buff_tracker, "_active_buffs"):
            for b in getattr(buff_tracker, "_active_buffs", {}).values():
                b_type = getattr(b, "buff_type", None)
                b_name = (getattr(b_type, "__name__", "") or str(b_type)).lower()
                if "trait" in b_name or "insecure" in b_name or "anxious" in b_name:
                    continue
                if any(k in b_name for k in JEALOUSY_BUFF_KEYWORDS):
                    return True
                if not is_jealous_partner and any(k in b_name for k in GENERAL_WITNESS_BUFF_KEYWORDS):
                    return True
    except Exception:
        pass
    return False


def _check_sex_witnesses(participants, p1, p2, p1_name, p2_name, session_key: str, sex_instance=None):
    """
    Detects if offspring, cheated partner, or other Sims caught them in the act.
    Strictly verifies line of sight and reaction: Sims CANNOT see through closed walls/doors,
    around blind corners, or while facing away without a game reaction!
    """
    global _ACTIVE_SEX_WITNESSES
    try:
        current_zone = services.current_zone() if services is not None else None
        if not current_zone:
            return

        active_lot_id = getattr(current_zone, "lot_id", 0)
        p1_instance = p1.get_sim_instance() if hasattr(p1, "get_sim_instance") else None
        if not p1_instance:
            return

        # Find instantiated Sims on current lot who are NOT participating in the sex
        from sims.sim_info_lod import SimInfoLODLevel
        sim_info_mgr = services.sim_info_manager() if services is not None else None
        if not sim_info_mgr:
            return

        part_ids = {getattr(p, "sim_id", 0) for p in participants}
        p1_room = getattr(p1_instance, "room_id", 0)

        for info in sim_info_mgr.values():
            if info is None:
                continue

            witness_id = getattr(info, "sim_id", 0)
            if not witness_id or witness_id in part_ids:
                continue

            # Don't process the same witness twice in the same sex session
            if (session_key, witness_id) in _ACTIVE_SEX_WITNESSES:
                continue

            # Exclude pets (dogs, cats, horses)
            if getattr(info, "is_pet", False):
                continue

            # Exclude babies, infants, and toddlers (cannot comprehend or be traumatized)
            age_name = getattr(getattr(info, "age", None), "name", "")
            if age_name in ("BABY", "INFANT", "TODDLER"):
                continue

            inst_sim = info.get_sim_instance() if hasattr(info, "get_sim_instance") else None
            if not inst_sim:
                continue

            # Room & Line-of-sight check:
            # Sims CANNOT see or witness intimacy through closed walls and doors!
            inst_room = getattr(inst_sim, "room_id", 0)

            # Distance check
            dist = 999.0
            try:
                dist = (inst_sim.position - p1_instance.position).magnitude()
            except Exception:
                pass

            if p1_room != 0:
                # Sex is INDOORS:
                # Witness MUST be in the exact same room! Never through walls from another room!
                if inst_room != p1_room:
                    continue
                # Inside the same room, maximum distance of 10.0 meters
                if dist > 10.0:
                    continue
            else:
                # Sex is OUTDOORS:
                # Witness must also be outdoors (not inside looking through exterior walls)
                if inst_room != 0:
                    continue
                # Outdoor line of sight: 6.0 meters
                if dist > 6.0:
                    continue

            # Check unblocked line of sight (not behind walls/corners)
            has_los = _has_sex_line_of_sight(inst_sim, p1_instance, sex_instance)

            # A. CASE 1: Offspring catches parents having intimacy!
            is_child_p1 = _is_child_of(info, p1)
            is_child_p2 = _is_child_of(info, p2) if p2 else False

            if is_child_p1 or is_child_p2:
                has_child_reaction = _has_sex_witness_reaction(inst_sim, is_jealous_partner=False)
                has_child_buff = _has_sex_witness_buff(info, is_jealous_partner=False)
                if not (has_child_reaction or has_child_buff or (has_los and dist <= 6.0)):
                    continue

                _ACTIVE_SEX_WITNESSES.add((session_key, witness_id))
                witness_name = _get_sim_name(info)

                if len(participants) == 1 or not p2:
                    # SOLO INTIMACY: Offspring catches single parent!
                    record_event_memory(
                        "intimacy_offspring_child_solo",
                        info,
                        target_sim_info=p1,
                        extra_context={"parent": p1_name}
                    )
                    record_event_memory(
                        "intimacy_offspring_parent_solo",
                        p1,
                        target_sim_info=info,
                        extra_context={"child_name": witness_name}
                    )
                else:
                    # PAIR INTIMACY: Offspring catches parents together!
                    record_event_memory(
                        "intimacy_offspring_child",
                        info,
                        extra_context={"parent1": p1_name, "parent2": p2_name}
                    )
                    record_event_memory(
                        "intimacy_offspring_parents",
                        p1,
                        target_sim_info=p2,
                        extra_context={"child_name": witness_name, "partner": p2_name}
                    )
                    record_event_memory(
                        "intimacy_offspring_parents",
                        p2,
                        target_sim_info=p1,
                        extra_context={"child_name": witness_name, "partner": p1_name}
                    )
                continue

            # B. CASE 2: Cheated Partner catches them in the act!
            caught_cheating = False
            if len(participants) >= 2:
                for part in participants:
                    ptnr = _get_partner_info(part)
                    if ptnr and getattr(ptnr, "sim_id", 0) == getattr(info, "sim_id", 0):
                        # info is the spouse/partner who walked in!
                        has_jealous_reaction = _has_sex_witness_reaction(inst_sim, is_jealous_partner=True)
                        has_jealous_buff = _has_sex_witness_buff(info, is_jealous_partner=True)

                        if not (has_jealous_reaction or has_jealous_buff or (has_los and dist <= 6.0)):
                            continue

                        _ACTIVE_SEX_WITNESSES.add((session_key, witness_id))
                        other_lovers = [_get_sim_name(o) for o in participants if o != part]
                        partner_name = _get_sim_name(info)
                        cheater_name = _get_sim_name(part)
                        lover_str = ", ".join(other_lovers)

                        # Memory for the betrayed partner
                        record_event_memory(
                            "cheating_caught",
                            info,
                            target_sim_info=part,
                            extra_context={"partner": cheater_name, "lover": lover_str}
                        )
                        # Memory for the cheating partner caught in bed
                        record_event_memory(
                            "cheating_caught_cheater",
                            part,
                            target_sim_info=info,
                            extra_context={"partner": partner_name, "lover": lover_str}
                        )
                        # Purge any weaker romantic flirting memories between this couple
                        part_id = getattr(part, "sim_id", 0)
                        info_id = getattr(info, "sim_id", 0)
                        remove_memories_by_types(
                            info_id,
                            part_id,
                            ["romance_cheating_caught", "romance_cheating_flirter"]
                        )
                        # Purge secret cheating memory from the cheater since it is now exposed
                        remove_memories_by_types(part_id, 0, ["intimacy_cheating"])
                        caught_cheating = True

            if caught_cheating:
                continue

            # C. CASE 3: General "Caught in the Act" (At home, In guests, In public)
            # Exclude children from adult caught-in-the-act memories for safety!
            age_name = getattr(getattr(info, "age", None), "name", "")
            if age_name == "CHILD":
                continue

            has_gen_reaction = _has_sex_witness_reaction(inst_sim, is_jealous_partner=False)
            has_gen_buff = _has_sex_witness_buff(info, is_jealous_partner=False)
            if not (has_gen_reaction or has_gen_buff or (has_los and dist <= 6.0)):
                continue

            _ACTIVE_SEX_WITNESSES.add((session_key, witness_id))
            witness_name = _get_sim_name(info)

            # Check lot type
            venue_service = services.venue_service() if services is not None else None
            active_venue = venue_service.active_venue if venue_service else None
            v_name = getattr(active_venue, "__name__", str(active_venue)).lower() if active_venue else ""

            is_residential = ("residential" in v_name or "apartment" in v_name or not v_name)
            household = getattr(p1, "household", None)
            home_zone_id = getattr(household, "home_zone_id", 0) if household else 0
            cur_zone_id = getattr(current_zone, "id", 0)
            is_home_lot = (home_zone_id != 0 and cur_zone_id == home_zone_id)

            if len(participants) == 1 or not p2:
                # SOLO INTIMACY caught by housemate / bystander:
                if is_home_lot:
                    record_event_memory(
                        "intimacy_solo_caught_home_actor",
                        p1,
                        target_sim_info=info,
                        extra_context={"witness": witness_name}
                    )
                    record_event_memory(
                        "intimacy_solo_caught_home_witness",
                        info,
                        target_sim_info=p1,
                        extra_context={"actor": p1_name}
                    )
                elif is_residential:
                    record_event_memory(
                        "intimacy_solo_caught_guests_actor",
                        p1,
                        target_sim_info=info,
                        extra_context={"witness": witness_name}
                    )
                    record_event_memory(
                        "intimacy_solo_caught_guests_witness",
                        info,
                        target_sim_info=p1,
                        extra_context={"actor": p1_name}
                    )
                else:
                    record_event_memory("intimacy_solo_caught_public_actor", p1, target_sim_info=info)
                    record_event_memory(
                        "intimacy_solo_caught_public_witness",
                        info,
                        target_sim_info=p1,
                        extra_context={"actor": p1_name}
                    )
            else:
                # PAIR / GROUP INTIMACY caught by bystander:
                if is_home_lot:
                    # Caught at home
                    record_event_memory(
                        "intimacy_caught_home_actors",
                        p1,
                        target_sim_info=p2,
                        extra_context={"witness": witness_name}
                    )
                    record_event_memory(
                        "intimacy_caught_home_actors",
                        p2,
                        target_sim_info=p1,
                        extra_context={"witness": witness_name}
                    )
                    record_event_memory(
                        "intimacy_caught_home_witness",
                        info,
                        extra_context={"actor": p1_name, "target": p2_name}
                    )
                elif is_residential:
                    # Caught at someone else's house / party
                    record_event_memory("intimacy_caught_guests_actors", p1, target_sim_info=p2)
                    record_event_memory("intimacy_caught_guests_actors", p2, target_sim_info=p1)
                    record_event_memory(
                        "intimacy_caught_guests_witness",
                        info,
                        extra_context={"actor": p1_name, "target": p2_name}
                    )
                else:
                    # Caught in public venue
                    record_event_memory("intimacy_caught_public_actors", p1, target_sim_info=p2)
                    record_event_memory("intimacy_caught_public_actors", p2, target_sim_info=p1)
                    record_event_memory(
                        "intimacy_caught_public_witness",
                        info,
                        extra_context={"actor": p1_name, "target": p2_name}
                    )

    except Exception as e:
        log_exception("Error in _check_sex_witnesses", e)


def _is_eligible_lover(cand_info, cheater_info, partner_info) -> bool:
    """Returns True if cand_info is a valid adult third party (not cheater, not partner, not child, not pet)."""
    if not cand_info or not cheater_info or not partner_info:
        return False
    c_id = getattr(cand_info, "sim_id", 0)
    ch_id = getattr(cheater_info, "sim_id", 0)
    p_id = getattr(partner_info, "sim_id", 0)
    if not c_id or c_id == ch_id or c_id == p_id:
        return False
    if getattr(cand_info, "is_pet", False):
        return False
    age = getattr(getattr(cand_info, "age", None), "name", "")
    if age in ("BABY", "INFANT", "TODDLER", "CHILD"):
        return False
    try:
        if _is_child_of(cand_info, cheater_info) or _is_child_of(cheater_info, cand_info):
            return False
        if _is_child_of(cand_info, partner_info) or _is_child_of(partner_info, cand_info):
            return False
    except Exception:
        pass
    return True


def _has_romance_with(sim_a, sim_b) -> bool:
    """Checks if sim_a has romantic bits or positive romance score towards sim_b."""
    if not sim_a or not sim_b:
        return False
    try:
        b_id = getattr(sim_b, "sim_id", 0)
        rel_tracker = getattr(sim_a, "relationship_tracker", None)
        if rel_tracker:
            for b in (rel_tracker.get_all_bits(b_id) or []):
                bn = getattr(b, "__name__", str(b)).lower()
                if any(k in bn for k in ("romantic", "romance", "flirt", "kiss", "lovers", "affair", "casanova", "desire", "sweethearts", "crush")):
                    return True
            try:
                from ai_social_pc.chat_manager import _get_romance_track
                r_track = _get_romance_track()
                if r_track and hasattr(rel_tracker, "get_relationship_score"):
                    score = rel_tracker.get_relationship_score(b_id, r_track)
                    if score and score > 0:
                        return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _find_lover_for_cheating(cheater_info, partner_info, cheater_inst=None):
    """
    Identifies the third-party Sim (the lover) involved in the cheating incident.
    Prioritizes:
    1. Active interaction target on cheater (if adult third party)
    2. Other adult Sims in the same room with romantic bits / score > 0
    3. Other adult Sims in the same room / vicinity
    4. Any adult Sim on the lot with positive romance score
    """
    if not cheater_info or not partner_info:
        return None

    sim_mgr = services.sim_info_manager() if services is not None else None
    if not sim_mgr:
        return None

    cheater_id = getattr(cheater_info, "sim_id", 0)
    partner_id = getattr(partner_info, "sim_id", 0)
    if not cheater_id or not partner_id:
        return None

    if cheater_inst is None and hasattr(cheater_info, "get_sim_instance"):
        cheater_inst = cheater_info.get_sim_instance()

    # 1. Direct check: running interaction target on cheater
    if cheater_inst:
        try:
            si_state = getattr(cheater_inst, "si_state", None)
            running_sis = getattr(si_state, "_sis", set()) if si_state else []
            for inter in running_sis:
                tgt = getattr(inter, "target", None)
                if tgt and hasattr(tgt, "sim_info"):
                    tgt_info = tgt.sim_info
                    if _is_eligible_lover(tgt_info, cheater_info, partner_info):
                        return tgt_info
        except Exception:
            pass

    # 2. Check candidate Sims in the same room or nearby on lot
    cheater_room = getattr(cheater_inst, "room_id", 0) if cheater_inst else 0
    cheater_pos = getattr(cheater_inst, "position", None) if cheater_inst else None

    rom_track = None
    try:
        from ai_social_pc.chat_manager import _get_romance_track
        rom_track = _get_romance_track()
    except Exception:
        pass

    rel_tracker = getattr(cheater_info, "relationship_tracker", None)

    candidates = []
    for cand_info in sim_mgr.values():
        if not _is_eligible_lover(cand_info, cheater_info, partner_info):
            continue

        cand_inst = cand_info.get_sim_instance() if hasattr(cand_info, "get_sim_instance") else None
        cand_id = getattr(cand_info, "sim_id", 0)

        in_room = False
        dist = 999.0
        if cheater_inst and cand_inst and cheater_pos:
            try:
                cand_room = getattr(cand_inst, "room_id", 0)
                dist = (cand_inst.position - cheater_pos).magnitude()
                if cheater_room != 0:
                    if cand_room == cheater_room and dist <= 15.0:
                        in_room = True
                else:
                    if cand_room == 0 and dist <= 12.0:
                        in_room = True
            except Exception:
                pass
        elif cand_inst:
            dist = 20.0

        # Relationship check
        has_rom_bits = False
        rom_score = 0.0
        if rel_tracker:
            try:
                bits = rel_tracker.get_all_bits(cand_id)
                for b in (bits or []):
                    bn = getattr(b, "__name__", str(b)).lower()
                    if any(k in bn for k in ("romantic", "romance", "flirt", "kiss", "lovers", "affair", "casanova", "desire", "sweethearts", "crush")):
                        has_rom_bits = True
                        break
            except Exception:
                pass
            if rom_track and hasattr(rel_tracker, "get_relationship_score"):
                try:
                    rom_score = float(rel_tracker.get_relationship_score(cand_id, rom_track) or 0.0)
                except Exception:
                    pass

        # Candidate MUST have romantic ties, positive romance score, or be actively engaged in sex!
        is_in_sex = cand_id in _CURRENT_SEX_SIM_IDS
        if not (has_rom_bits or rom_score > 0 or is_in_sex):
            continue

        candidates.append({
            "info": cand_info,
            "in_room": in_room,
            "has_rom_bits": has_rom_bits,
            "rom_score": rom_score,
            "dist": dist
        })

    if not candidates:
        return None

    # Sort candidates: in_room first, romance bits first, highest romance score, shortest distance
    candidates.sort(
        key=lambda c: (
            1 if c["in_room"] else 0,
            1 if c["has_rom_bits"] else 0,
            c["rom_score"],
            -c["dist"]
        ),
        reverse=True
    )

    return candidates[0]["info"]


def _trigger_cheating_caught(cheater, partner, lover):
    """Records event memories for both partner (caught spouse) and cheater (got caught)."""
    if not cheater or not partner:
        return
    partner_name = _get_sim_name(partner)
    cheater_name = _get_sim_name(cheater)
    lover_name = _get_sim_name(lover) if lover else "тайным возлюбленным"
    lover_name_en = _get_sim_name(lover) if lover else "a secret lover"
    record_event_memory(
        "romance_cheating_caught",
        partner,
        target_sim_info=cheater,
        extra_context={
            "partner": cheater_name,
            "lover": lover_name,
            "lover_ru": lover_name,
            "lover_en": lover_name_en,
        }
    )
    record_event_memory(
        "romance_cheating_flirter",
        cheater,
        target_sim_info=partner,
        extra_context={
            "partner": partner_name,
            "lover": lover_name,
            "lover_ru": lover_name,
            "lover_en": lover_name_en,
        }
    )


def _check_and_process_romantic_cheating():
    """
    Detects if a Sim is caught flirting, kissing, or being romantic with someone else
    in front of their spouse or steady romantic partner.
    Supports 3 robust detection methods:
    1. Active romantic interaction witnessed in same room/vicinity.
    2. Active jealousy reaction interaction (e.g. reaction_jealousy_kiss_lovedone) running on either partner or cheater.
    3. Active jealousy/fear moodlet (e.g. cheatingwitnessed, fear_beingcheatedon) on partner.
    """
    sim_mgr = services.sim_info_manager() if services is not None else None
    if not sim_mgr:
        return

    ROMANTIC_KEYWORDS = (
        "flirt", "kiss", "make_out", "makeout", "blow_kiss", "hold_hands",
        "embrace", "cuddle", "caress", "serenade", "whisper_nothings",
        "romance", "romantic"
    )

    JEALOUSY_BUFF_KEYWORDS = (
        "cheatingwitnessed", "witness_cheating", "witnessed_cheating",
        "flirtwitnessed", "flirt_witnessed", "kisswitnessed", "kiss_witnessed",
        "woohoowitnessed", "woohoo_witnessed", "caught_cheating", "caughtcheating",
        "fear_beingcheatedon", "fear_of_cheating"
    )

    for info in sim_mgr.values():
        if info is None or getattr(info, "is_pet", False):
            continue

        actor_age = getattr(getattr(info, "age", None), "name", "")
        if actor_age in ("BABY", "INFANT", "TODDLER", "CHILD"):
            continue

        partner_info = _get_partner_info(info)
        if not partner_info or getattr(partner_info, "is_pet", False):
            continue

        actor_id = getattr(info, "sim_id", 0)
        partner_id = getattr(partner_info, "sim_id", 0)

        # 1. Skip if either Sim is actively engaged in sex / woohoo.
        # Intimacy monitoring handles caught in the act of sex!
        if actor_id in _CURRENT_SEX_SIM_IDS or partner_id in _CURRENT_SEX_SIM_IDS:
            continue

        # 2. Skip if sex cheating is already active between this couple.
        # Sex cheating supersedes flirt cheating.
        pair_mems = get_active_memories(actor_id, partner_id)
        if any(m.get("event_type") in ("cheating_caught", "cheating_caught_cheater") for m in pair_mems):
            continue

        actor_inst = info.get_sim_instance() if hasattr(info, "get_sim_instance") else None
        partner_inst = partner_info.get_sim_instance() if hasattr(partner_info, "get_sim_instance") else None

        # -----------------------------------------------------------------
        # TRIGGER 1: Sim (info) is running an active romantic interaction with a 3rd party
        # and partner is witnessing it in the same room / outdoors nearby.
        # -----------------------------------------------------------------
        if actor_inst and partner_inst:
            lover_info = None
            try:
                si_state = getattr(actor_inst, "si_state", None)
                running_sis = getattr(si_state, "_sis", set()) if si_state else []
                for inter in running_sis:
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff)).lower() if aff else ""
                    inter_name = (getattr(inter, "__name__", "") or str(inter)).lower()
                    combined = f"{aff_name} {inter_name}"
                    if "jealous" in combined:
                        continue
                    if any(k in combined for k in ROMANTIC_KEYWORDS):
                        tgt = getattr(inter, "target", None)
                        if tgt and hasattr(tgt, "sim_info"):
                            tgt_info = tgt.sim_info
                            if _is_eligible_lover(tgt_info, info, partner_info):
                                lover_info = tgt_info
                                break
            except Exception:
                lover_info = None

            if lover_info:
                witnessed = False
                try:
                    actor_room = getattr(actor_inst, "room_id", 0)
                    partner_room = getattr(partner_inst, "room_id", 0)
                    dist = (partner_inst.position - actor_inst.position).magnitude()
                    if actor_room != 0:
                        if partner_room == actor_room and dist <= 15.0:
                            witnessed = True
                    else:
                        if partner_room == 0 and dist <= 10.0:
                            witnessed = True
                except Exception:
                    pass

                if witnessed:
                    _trigger_cheating_caught(info, partner_info, lover_info)
                    continue

        # -----------------------------------------------------------------
        # TRIGGER 2: Jealousy reaction interaction running on either Sim
        # (e.g. reaction_jealousy_kiss_lovedone, reaction_jealousy_flirt_lovedone)
        # In TS4, these reaction animations have target = None and run for ~10-15s!
        # In TS4, jealousy reactions are pushed on the BETRAYED partner (witness).
        # Therefore info is ALWAYS the betrayed partner, and partner_info is ALWAYS the cheater!
        # -----------------------------------------------------------------
        if actor_inst:
            has_jealousy_reaction = False
            try:
                si_state = getattr(actor_inst, "si_state", None)
                running_sis = getattr(si_state, "_sis", set()) if si_state else []
                for inter in running_sis:
                    aff = getattr(inter, "affordance", None)
                    aff_name = (getattr(aff, "__name__", "") or str(aff)).lower() if aff else ""
                    inter_name = (getattr(inter, "__name__", "") or str(inter)).lower()
                    combined = f"{aff_name} {inter_name}"
                    if "jealousy" in combined or "reaction_jealousy" in combined:
                        has_jealousy_reaction = True
                        break
            except Exception:
                pass

            if has_jealousy_reaction:
                # info is the betrayed partner; partner_info is the cheater
                lover = _find_lover_for_cheating(partner_info, info, partner_inst)
                if lover or (partner_inst and _has_romance_with(partner_info, lover)):
                    _trigger_cheating_caught(partner_info, info, lover)
                    continue
                elif partner_inst:
                    # Fallback if lover left the room: cheater is partner_info, betrayed is info
                    _trigger_cheating_caught(partner_info, info, None)
                    continue

        # -----------------------------------------------------------------
        # TRIGGER 3: Jealousy or Fear of Cheating buff on partner
        # Strictly ignore trait buffs (e.g. buff_Trait_Jealous_Insecure)
        # -----------------------------------------------------------------
        try:
            buff_tracker = getattr(info, "buff_component", None) or getattr(info, "BuffComponent", None)
            if buff_tracker and hasattr(buff_tracker, "_active_buffs"):
                has_cheating_buff = False
                for b in getattr(buff_tracker, "_active_buffs", {}).values():
                    b_type = getattr(b, "buff_type", None)
                    b_name = (getattr(b_type, "__name__", "") or str(b_type)).lower()
                    if "trait" in b_name or "insecure" in b_name or "anxious" in b_name:
                        continue
                    if any(k in b_name for k in JEALOUSY_BUFF_KEYWORDS):
                        has_cheating_buff = True
                        break

                if has_cheating_buff:
                    # info is the betrayed partner with the buff; partner_info is the cheater
                    lover = _find_lover_for_cheating(partner_info, info, partner_inst)
                    _trigger_cheating_caught(partner_info, info, lover)
                    continue
        except Exception:
            pass


# =========================================================================
# 5. PERIODIC GAME EVENTS (Pregnancy, Death, Career, Fire, Fights, Occult)
# =========================================================================

def _check_and_process_periodic_game_events():
    """Lightweight periodic checks running every ~5 sim seconds on Zone update."""
    global _PREGNANCY_STATE, _DEATH_STATE, _DEATH_INITIALIZED, _CAREER_LEVELS, _OCCULT_STATE, _FIRE_WAS_ACTIVE

    sim_mgr = services.sim_info_manager() if services is not None else None
    if not sim_mgr:
        return

    # 0. SAFE DEATH INITIALIZATION & MONITORING
    if not _DEATH_INITIALIZED:
        # Pre-seed dead state on first tick so pre-existing ghosts never trigger false death events
        for d_info in sim_mgr.values():
            if d_info and getattr(d_info, "is_dead", False):
                _DEATH_STATE.add(getattr(d_info, "sim_id", 0))
        _DEATH_INITIALIZED = True
    else:
        for d_info in sim_mgr.values():
            if d_info is None or getattr(d_info, "is_pet", False):
                continue
            d_id = getattr(d_info, "sim_id", 0)
            if not d_id or d_id in _DEATH_STATE:
                continue
            if getattr(d_info, "is_dead", False):
                _DEATH_STATE.add(d_id)
                dead_name = _get_sim_name(d_info)
                hh = getattr(d_info, "household", None)
                hh_sims = getattr(hh, "sim_infos", []) if hh else []
                for survivor in hh_sims:
                    if survivor and getattr(survivor, "sim_id", 0) != d_id and not getattr(survivor, "is_pet", False):
                        record_event_memory("death_loved_one", survivor, extra_context={"target": dead_name})

    # A. PREGNANCY & BIRTH MONITORING
    for info in sim_mgr.values():
        if info is None or getattr(info, "is_pet", False):
            continue
        s_id = getattr(info, "sim_id", 0)
        if not s_id:
            continue

        p_tracker = getattr(info, "pregnancy_tracker", None)
        is_preg = getattr(p_tracker, "is_pregnant", False) if p_tracker else False
        was_preg = _PREGNANCY_STATE.get(s_id, False)

        if not was_preg and is_preg:
            # Pregnancy discovered!
            _PREGNANCY_STATE[s_id] = True
            gender_raw = getattr(getattr(info, "gender", None), "name", "")
            is_male = (gender_raw == "MALE")
            if is_male:
                record_event_memory("pregnancy_alien_male", info)
            else:
                ptnr = getattr(p_tracker, "get_partner", lambda: None)() if hasattr(p_tracker, "get_partner") else None
                if not ptnr:
                    ptnr = _get_partner_info(info)
                ptnr_name = _get_sim_name(ptnr) if ptnr else "любимого"
                record_event_memory("pregnancy_mother", info, extra_context={"target": ptnr_name})
                if ptnr:
                    record_event_memory("pregnancy_father", ptnr, extra_context={"target": _get_sim_name(info)})

        elif was_preg and not is_preg:
            # Baby delivered!
            _PREGNANCY_STATE[s_id] = False
            # Find newborn in household
            hh = getattr(info, "household", None)
            hh_sims = getattr(hh, "sim_infos", []) if hh else []
            baby_name = "малыш"
            for b in hh_sims:
                if b and getattr(getattr(b, "age", None), "name", "") in ("BABY", "INFANT"):
                    baby_name = _get_sim_name(b)
                    break
            record_event_memory("baby_born", info, extra_context={"baby_name": baby_name})
            ptnr = _get_partner_info(info)
            if ptnr:
                record_event_memory("baby_born", ptnr, extra_context={"baby_name": baby_name})

        # B. CAREER PROMOTIONS (keyed by (sim_id, career_id) to prevent multi-career conflicts)
        c_tracker = getattr(info, "career_tracker", None)
        if c_tracker and hasattr(c_tracker, "careers"):
            careers = getattr(c_tracker, "careers", {})
            if careers:
                for c in careers.values():
                    lvl = getattr(c, "user_level", 1)
                    c_uid = getattr(c, "guid64", getattr(c, "id", str(c)))
                    c_key = (s_id, c_uid)
                    old_lvl = _CAREER_LEVELS.get(c_key, 0)
                    if old_lvl != 0 and lvl > old_lvl:
                        record_event_memory("career_promoted", info)
                    _CAREER_LEVELS[c_key] = lvl

        # C. FIGHT BUFFS (Won / Lost)
        buff_tracker = getattr(info, "buff_component", None) or getattr(info, "BuffComponent", None)
        if buff_tracker and hasattr(buff_tracker, "has_buff"):
            for b in getattr(buff_tracker, "_active_buffs", {}).values():
                b_name = getattr(getattr(b, "buff_type", None), "__name__", "").lower()
                if "fight_won" in b_name or "wonfight" in b_name:
                    opponent = None
                    for other in sim_mgr.values():
                        if other and getattr(other, "sim_id", 0) != s_id and not getattr(other, "is_pet", False):
                            o_bt = getattr(other, "buff_component", None) or getattr(other, "BuffComponent", None)
                            if o_bt and hasattr(o_bt, "_active_buffs"):
                                for ob in getattr(o_bt, "_active_buffs", {}).values():
                                    ob_name = getattr(getattr(ob, "buff_type", None), "__name__", "").lower()
                                    if "fight_lost" in ob_name or "lostfight" in ob_name:
                                        opponent = other
                                        break
                            if opponent:
                                break
                    opp_name = _get_sim_name(opponent) if opponent else "противником"
                    record_event_memory("fight_won", info, target_sim_info=opponent, extra_context={"target": opp_name})
                elif "fight_lost" in b_name or "lostfight" in b_name:
                    opponent = None
                    for other in sim_mgr.values():
                        if other and getattr(other, "sim_id", 0) != s_id and not getattr(other, "is_pet", False):
                            o_bt = getattr(other, "buff_component", None) or getattr(other, "BuffComponent", None)
                            if o_bt and hasattr(o_bt, "_active_buffs"):
                                for ob in getattr(o_bt, "_active_buffs", {}).values():
                                    ob_name = getattr(getattr(ob, "buff_type", None), "__name__", "").lower()
                                    if "fight_won" in ob_name or "wonfight" in ob_name:
                                        opponent = other
                                        break
                            if opponent:
                                break
                    opp_name = _get_sim_name(opponent) if opponent else "противником"
                    record_event_memory("fight_lost", info, target_sim_info=opponent, extra_context={"target": opp_name})

        # D. OCCULT TRANSITIONS
        occult_tracker = getattr(info, "occult_tracker", None)
        if occult_tracker and hasattr(occult_tracker, "has_occult_type"):
            from sims.occult.occult_enums import OccultType
            cur_occ = "human"
            if occult_tracker.has_occult_type(OccultType.VAMPIRE):
                cur_occ = "vampire"
            elif occult_tracker.has_occult_type(OccultType.WEREWOLF):
                cur_occ = "werewolf"
            elif occult_tracker.has_occult_type(OccultType.WITCH):
                cur_occ = "witch"

            old_occ = _OCCULT_STATE.get(s_id)
            if old_occ is not None and old_occ != cur_occ:
                if cur_occ == "vampire":
                    record_event_memory("occult_vampire", info)
                elif cur_occ == "werewolf":
                    record_event_memory("occult_werewolf", info)
                elif cur_occ == "witch":
                    record_event_memory("occult_spellcaster", info)
                elif cur_occ == "human" and old_occ in ("vampire", "werewolf", "witch"):
                    record_event_memory("occult_cured", info)

            _OCCULT_STATE[s_id] = cur_occ

    # E. HOUSE FIRE MONITORING
    fire_service = None
    if services is not None:
        if hasattr(services, "get_fire_service") and callable(services.get_fire_service):
            try:
                fire_service = services.get_fire_service()
            except Exception:
                pass
        elif hasattr(services, "fire_service") and callable(services.fire_service):
            try:
                fire_service = services.fire_service()
            except Exception:
                pass
    if fire_service:
        raw_fire = getattr(fire_service, "fire_is_active", False)
        is_fire = raw_fire() if callable(raw_fire) else bool(raw_fire)
        if is_fire:
            _FIRE_WAS_ACTIVE = True
        elif _FIRE_WAS_ACTIVE and not is_fire:
            # Fire extinguished!
            _FIRE_WAS_ACTIVE = False
            active_sim = services.get_active_sim() if services is not None else None
            hh = getattr(active_sim, "household", None) if active_sim else None
            if hh:
                for h_sim in getattr(hh, "sim_infos", []):
                    if h_sim:
                        record_event_memory("house_fire", h_sim)


# =========================================================================
# 6. MAIN TICK ENTRYPOINT (Hooked into Zone.update)
# =========================================================================

def process_event_memory_checks():
    """
    Called periodically from Zone.update.
    Throttled to run at most once every 5 seconds.
    """
    global _LAST_PERIODIC_CHECK_TIME
    now = time.time()
    if now - _LAST_PERIODIC_CHECK_TIME < 5.0:
        return

    _LAST_PERIODIC_CHECK_TIME = now

    try:
        # Check active sex, walk-ins, and intimacy
        _check_and_process_intimacy_events()
    except Exception as e_sex:
        log_exception("Error in process_event_memory_checks intimacy", e_sex)

    try:
        # Check active romantic cheating (flirting/kissing witnessed by partner)
        _check_and_process_romantic_cheating()
    except Exception as e_rom:
        log_exception("Error in process_event_memory_checks romance cheating", e_rom)

    try:
        # Check periodic transitions (pregnancy, death, career, fire, occult)
        _check_and_process_periodic_game_events()
    except Exception as e_game:
        log_exception("Error in process_event_memory_checks game events", e_game)
