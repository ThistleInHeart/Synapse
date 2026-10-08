# -*- coding: utf-8 -*-
"""
Synapse English Context Engine
Provides flawless, 100% native English formatting and translation for The Sims 4 AI context.
Ensures smaller models (7B/8B, Ollama, LM Studio) run at peak reasoning intelligence
without language bleed, token waste, or confusion from Cyrillic input.
"""

import re
from typing import List, Dict, Optional, Any


# =========================================================================
# 1. AGE & GENDER
# =========================================================================

AGE_MAP_EN = {
    "BABY": "Newborn",
    "INFANT": "Infant",
    "TODDLER": "Toddler",
    "CHILD": "Child",
    "TEEN": "Teen",
    "YOUNGADULT": "Young Adult",
    "ADULT": "Adult",
    "ELDER": "Elder",
    "Новорожденный": "Newborn",
    "Младенец": "Infant",
    "Малыш": "Toddler",
    "Ребенок": "Child",
    "Подросток": "Teen",
    "Молодой": "Young Adult",
    "Взрослый": "Adult",
    "Пожилой": "Elder",
}

GENDER_MAP_EN = {
    "MALE": "Male",
    "FEMALE": "Female",
    "Мужской": "Male",
    "Женский": "Female",
    "Не указан": "Unspecified",
}

OCCULT_MAP_EN = {
    "Человек": "Human",
    "Вампир": "Vampire",
    "Оборотень": "Werewolf",
    "Русалка": "Mermaid",
    "Чародей / Маг": "Spellcaster / Witch",
    "Чародей": "Spellcaster",
    "Маг": "Witch / Mage",
    "Инопланетянин (Пришелец)": "Alien",
    "Инопланетянин": "Alien",
    "Пришелец": "Alien",
    "Робот (Серво)": "Robot (Servo)",
    "Робот": "Robot (Servo)",
    "Призрак": "Ghost",
    "Ростоман": "PlantSim (human-plant hybrid: photosynthesizes in sunlight, absorbs water instead of regular food, loves nature, wilts without moisture)",
    "Скелет": "Skeleton",
}

OCCULT_FORM_MAP_EN = {
    # Aliens
    "[В маскировке под человека]": "[In Human Disguise]",
    "[Истинный облик (без маскировки)]": "[True Alien Form (Undisguised)]",
    "в маскировке под человека": "in human disguise",
    "истинный облик (без маскировки)": "true alien form (undisguised)",
    # Werewolves
    "[В форме волка (звериный облик)]": "[In Beast / Wolf Form]",
    "[В человеческом облике]": "[In Human Form]",
    "в форме волка (звериный облик)": "in beast / wolf form",
    "в человеческом облике": "in human form",
    # Vampires
    "[В тёмной форме]": "[In Dark Form]",
    "[В обычном облике]": "[In Normal Form]",
    "в тёмной форме": "in dark form",
    "в обычном облике": "in normal form",
}

GHOST_DEATH_MAP_EN = {
    "старость / переутомление": "Old Age / Elder Overexertion",
    "старость": "Old Age",
    "смертельное переутомление": "Elder Overexertion",
    "утопление": "Drowning",
    "сгорание в огне / пожар": "Fire",
    "пожар": "Fire",
    "удар током": "Electrocution",
    "удар молнии": "Lightning Strike",
    "голод / истощение": "Starvation",
    "голод": "Starvation",
    "сердечный приступ от ярости": "Cardiac Arrest (Anger)",
    "взрыв ярости": "Enraged / Cardiac Arrest",
    "смерть от смеха / истерика": "Laughter / Hysteria",
    "смертельное смущение / позор": "Mortification / Embarrassment",
    "съеден проглотис людоедия": "Consumed by Cowplant",
    "перегрев в сауне": "Sauna Steam",
    "отравление рыбой фугу": "Pufferfish Poisoning",
    "солнечный свет (сгорание вампира)": "Sunlight (Vampire)",
    "солнечный свет": "Sunlight",
    "древний смертоносный яд": "Poison",
    "замерзание / переохлаждение": "Freezing",
    "тепловой удар на солнце": "Overheating",
    "магическая перегрузка чародея": "Spellcaster Magical Overload",
    "нападение роя мух": "Swarm of Flies",
    "раздавлен складной кроватью": "Crushed by Murphy Bed",
    "передозировка жучиного сока": "Beetle Juice",
    "падение со скалы при альпинизме": "Rock Climbing Fall",
    "раздавлен торговым автоматом": "Crushed by Vending Machine",
    "нападение злобной курицы": "Killer Chicken Attack",
    "нападение кролика-людоеда": "Killer Rabbit Attack",
    "удар метеорита": "Meteorite Impact",
    "удушье от запаха вонючего жука": "Stink Bug Fumes",
    "поглощен материнским растением": "Consumed by Mother Plant",
    "неудачный спиритический сеанс": "Failed Seance",
    "жертва городской легенды (кровавая мэри)": "Urban Myth",
    "смертельный ужас / страх": "Scared to Death",
    "аромат букета с цветком смерти": "Death Flower Scent",
    "заражение токсичной плесенью": "Toxic Mold",
    "нападение стаи ворон": "Murder of Crows",
    "смертоносная карта таро": "Death by Tarot",
    "стыд и позор": "Died of Shame",
}


def translate_occult_en(race_str: str) -> str:
    """
    Translates Sim species / occult race with live form and death details from Russian to English.
    Handles forms like:
      - 'Инопланетянин (Пришелец) [В маскировке под человека]' -> 'Alien [In Human Disguise]'
      - 'Оборотень [В форме волка (звериный облик)]' -> 'Werewolf [In Beast / Wolf Form]'
      - 'Вампир [В тёмной форме]' -> 'Vampire [In Dark Form]'
      - 'Призрак [Причина смерти: Сгорание в огне / Пожар]' -> 'Ghost [Cause of death: Fire]'
    Also safely passes through already English strings.
    """
    if not race_str:
        return "Human"

    race_str = str(race_str).strip()

    # Pass through already English strings
    if race_str in ("Human", "Alien", "Werewolf", "Vampire", "Ghost", "Mermaid", "Spellcaster", "Spellcaster / Witch", "PlantSim", "Skeleton", "Robot (Servo)"):
        return race_str
    if race_str.startswith(("Alien [", "Werewolf [", "Vampire [", "Ghost [", "Human [", "Spellcaster [", "Robot [", "PlantSim")):
        return race_str

    bracket_detail = ""
    base_part = race_str
    if "[" in race_str and "]" in race_str:
        try:
            start_idx = race_str.find("[")
            end_idx = race_str.rfind("]")
            bracket_detail = race_str[start_idx : end_idx + 1].strip()
            base_part = race_str[:start_idx].strip()
        except Exception:
            pass

    base_en = OCCULT_MAP_EN.get(base_part, "")
    if not base_en:
        base_part_lower = base_part.lower()
        if "инопланетян" in base_part_lower or "пришелец" in base_part_lower:
            base_en = "Alien"
        elif "оборотень" in base_part_lower:
            base_en = "Werewolf"
        elif "вампир" in base_part_lower:
            base_en = "Vampire"
        elif "призрак" in base_part_lower:
            base_en = "Ghost"
        elif "русалк" in base_part_lower:
            base_en = "Mermaid"
        elif "чародей" in base_part_lower or "маг" in base_part_lower:
            base_en = "Spellcaster"
        elif "робот" in base_part_lower or "серво" in base_part_lower:
            base_en = "Robot (Servo)"
        elif "ростоман" in base_part_lower or "plantsim" in base_part_lower:
            base_en = "PlantSim (human-plant hybrid: photosynthesizes in sunlight, absorbs water instead of regular food, loves nature, wilts without moisture)"
        elif "скелет" in base_part_lower:
            base_en = "Skeleton"
        elif "человек" in base_part_lower:
            base_en = "Human"
        else:
            base_en = base_part or "Human"

    if not bracket_detail:
        return base_en

    # Translate bracket detail
    if bracket_detail in OCCULT_FORM_MAP_EN:
        return f"{base_en} {OCCULT_FORM_MAP_EN[bracket_detail]}"

    inner = bracket_detail[1:-1].strip()
    if "причина смерти:" in inner.lower():
        parts = inner.split(":", 1)
        cause_raw = parts[1].strip() if len(parts) > 1 else ""
        cause_en = GHOST_DEATH_MAP_EN.get(cause_raw.lower())
        if not cause_en:
            for k, v in sorted(GHOST_DEATH_MAP_EN.items(), key=lambda x: len(x[0]), reverse=True):
                if k in cause_raw.lower():
                    cause_en = v
                    break
        if not cause_en:
            cause_en = cause_raw
        return f"{base_en} [Cause of death: {cause_en}]"

    # Check lowercase inner form
    inner_lower = inner.lower()
    for k, v in OCCULT_FORM_MAP_EN.items():
        if k.lower() == inner_lower or f"[{k.lower()}]" == bracket_detail.lower():
            return f"{base_en} [{v.strip('[]')}]"

    return f"{base_en} {bracket_detail}"



# =========================================================================
# 2. TIME, SEASONS & WEATHER
# =========================================================================

DAYS_MAP_EN = {
    "Понедельник": "Monday",
    "Вторник": "Tuesday",
    "Среда": "Wednesday",
    "Четверг": "Thursday",
    "Пятница": "Friday",
    "Суббота": "Saturday",
    "Воскресенье": "Sunday",
}

TIME_PERIOD_MAP_EN = {
    "Утро": "Morning",
    "День": "Afternoon",
    "Вечер": "Evening",
    "Ночь": "Night",
}

SEASONS_MAP_EN = {
    "Весна": "Spring",
    "Лето": "Summer",
    "Осень": "Fall (Autumn)",
    "Зима": "Winter",
}

WEATHER_MAP_EN = {
    "Ясно / Солнечно": "Clear / Sunny",
    "Солнечно": "Sunny",
    "Ясно": "Clear",
    "Облачно": "Cloudy",
    "Пасмурно": "Overcast",
    "Дождь": "Rain",
    "Ливень": "Heavy Rain",
    "Гроза": "Thunderstorm",
    "Снег": "Snow",
    "Снегопад": "Heavy Snow",
    "Метель / Буран": "Blizzard",
    "Жара / Зной": "Heatwave",
    "Жара": "Heatwave",
    "Тепло": "Warm",
    "Прохладно": "Cool",
    "Холодно": "Cold",
    "Мороз": "Freezing Cold",
}


# =========================================================================
# 3. CLOTHING & NUDITY
# =========================================================================

CLOTHING_MAP_EN = {
    # Full TS4 Outfit categories
    "Повседневная одежда": "Everyday outfit",
    "Официальный наряд": "Formal attire",
    "Официальный костюм": "Formal attire",
    "Спортивная форма": "Athletic wear",
    "Спортивная одежда": "Athletic wear",
    "Одежда для сна (пижама)": "Sleepwear (pajamas)",
    "Одежда для сна (Пижама)": "Sleepwear (pajamas)",
    "Одежда для сна": "Sleepwear",
    "Праздничный наряд": "Party outfit",
    "Праздничная одежда": "Party outfit",
    "Купальный костюм (купальник / плавки)": "Swimwear",
    "Купальник / Плавки": "Swimwear",
    "Купальник": "Swimwear",
    "Летняя одежда (для жаркой погоды)": "Hot weather outfit",
    "Одежда для жаркой погоды": "Hot weather outfit",
    "Летняя одежда": "Hot weather outfit",
    "Тёплая одежда (для холодной погоды)": "Cold weather outfit",
    "Теплая одежда (для холодной погоды)": "Cold weather outfit",
    "Одежда для холодной погоды": "Cold weather outfit",
    "Тёплая одежда": "Cold weather outfit",
    "Теплая одежда": "Cold weather outfit",
    "Одежда для купания (без одежды / полотенце)": "Bathing (unclothed / wrapped in towel)",
    "Рабочая униформа": "Career / work uniform",
    "Ситуативный наряд": "Situational outfit",
    "Особый наряд / костюм": "Special outfit / costume",
    "Особый наряд": "Special outfit",
    "Наряд с Батуу": "Batuu outfit",
    "Рабочая форма (бизнес)": "Business uniform",
    "Магический наряд": "Magical attire",
    "Нижнее белье": "Underwear",
    "Без одежды (в душе / ванной)": "Undressed (in shower / bath)",
    "Без одежды (полностью раздет)": "Undressed (completely unclothed)",
    # Modifiers
    "(низ снят)": "(bottom off)",
    "(верх снят)": "(top off)",
    "низ снят": "bottom off",
    "верх снят": "top off",
    "Купальный костюм (купальник / плавки) (низ снят)": "Swimwear (bottom off)",
    "Купальный костюм (купальник / плавки) (верх снят)": "Swimwear (top off)",
    "Повседневная одежда (низ снят)": "Everyday outfit (bottom off)",
    "Повседневная одежда (верх снят)": "Everyday outfit (top off)",
    "Официальный наряд (низ снят)": "Formal attire (bottom off)",
    "Официальный наряд (верх снят)": "Formal attire (top off)",
    "Официальный костюм (низ снят)": "Formal attire (bottom off)",
    "Официальный костюм (верх снят)": "Formal attire (top off)",
    "Спортивная форма (низ снят)": "Athletic wear (bottom off)",
    "Спортивная форма (верх снят)": "Athletic wear (top off)",
    "Спортивная одежда (низ снят)": "Athletic wear (bottom off)",
    "Спортивная одежда (верх снят)": "Athletic wear (top off)",
    "Одежда для сна (низ снят)": "Sleepwear (bottom off)",
    "Одежда для сна (верх снят)": "Sleepwear (top off)",
    "Праздничный наряд (низ снят)": "Party outfit (bottom off)",
    "Праздничный наряд (верх снят)": "Party outfit (top off)",
    "Праздничная одежда (низ снят)": "Party outfit (bottom off)",
    "Праздничная одежда (верх снят)": "Party outfit (top off)",
    "Ситуативный наряд (низ снят)": "Situational outfit (bottom off)",
    "Ситуативный наряд (верх снят)": "Situational outfit (top off)",
    "Тёплая одежда (для холодной погоды) (низ снят)": "Cold weather outfit (bottom off)",
    "Тёплая одежда (для холодной погоды) (верх снят)": "Cold weather outfit (top off)",
    "Теплая одежда (для холодной погоды) (низ снят)": "Cold weather outfit (bottom off)",
    "Теплая одежда (для холодной погоды) (верх снят)": "Cold weather outfit (top off)",
}

NUDITY_MAP_EN = {
    "Полностью одет(а)": "Fully clothed",
    "Полностью одет": "Fully clothed",
    "Полностью одета": "Fully clothed",
    "Без верха (топлес, снизу в нижнем белье)": "Topless (bare chest, wearing underwear below)",
    "Без верха (топлес)": "Topless (bare chest)",
    "Без верха": "Topless",
    "Без низа (сверху в нижнем белье)": "Bottomless (wearing underwear top)",
    "Без низа": "Bottomless (no underwear/pants)",
    "В нижнем белье": "In underwear",
    "Нижнее белье": "In underwear",
    "В откровенной / открытой одежде": "In revealing / open clothing",
    "В купальнике / плавках": "In swimwear",
    "В одежде для сна / белье": "In sleepwear / underwear",
    "Полностью обнажен(а) / Нагишом": "Completely nude (naked)",
    "Полностью обнажен(а)": "Completely nude",
    "Полностью обнажен": "Completely nude",
    "Полностью обнажена": "Completely nude",
    "Нагишом": "Naked",
    "Полностью голая": "Completely nude (naked)",
    "Полностью голый": "Completely nude (naked)",
    "Голая": "Nude",
    "Голый": "Nude",
    "Раздета": "Undressed",
    "Раздет": "Undressed",
}


# =========================================================================
# 4. MOODS & INTENSITIES
# =========================================================================

MOOD_MAP_EN = {
    "happy": "Happy",
    "fine": "Fine / Neutral",
    "flirty": "Flirty / Romantic",
    "inspired": "Inspired",
    "focused": "Focused",
    "playful": "Playful",
    "energized": "Energized",
    "confident": "Confident",
    "sad": "Sad",
    "angry": "Angry",
    "uncomfortable": "Uncomfortable",
    "tense": "Tense",
    "embarrassed": "Embarrassed",
    "bored": "Bored",
    "dazed": "Dazed",
    "asleep": "Asleep",
    "scared": "Scared",
    "sex": "Sexually Aroused",
    "aroused": "Sexually Aroused",
    "wickedwhims_mood_sex": "Sexually Aroused",
    "stoned": "Stoned / High",
    "sedated": "Sedated / Down",
    "stimulated": "Stimulated / Wired",
    "drunk": "Drunk / Intoxicated",

    # Basemental Drugs Mood Fallbacks
    "Под кайфом / Накуренное": "Stoned / High",
    "Сильно накуренное / Затуманенное": "Very Stoned / Baked",
    "В полнейшем ауте / Бледный": "Greened Out",
    "Навеселе / Слегка пьяное": "Tipsy",
    "Пьяное / Под алкоголем": "Drunk / Intoxicated",
    "Пьяное": "Drunk",
    "В стельку / В хлам": "Wasted / Smashed",
    "Под стимуляторами / Взвинченное": "Stimulated / Wired",
    "Сильно взвинченное / Бешеный разгон": "Hyper-Stimulated / Wired",
    "На пике стимуляции / Неистовый разгон": "Extreme Stimulation / Overdrive",
    "Под седацией / Расслабленное": "Sedated / Relaxed",
    "Под седацией / Замедленное": "Sedated / Down",
    "Сильно заторможенное / В полудрёме": "Heavy Sedation / Nodding Off",
    "Глубокая седация / Полное отключение": "Deep Sedation / Numb",

    # Russian phrase fallbacks
    "Счастливое": "Happy",
    "Счастлив": "Happy",
    "Счастлива": "Happy",
    "Очень счастливое (В приподнятом настроении)": "Very Happy (Elated)",
    "Безумно счастливое (Эйфория)": "Euphoric (Overjoyed)",
    "Нейтральное / Обычное": "Fine / Neutral",
    "Обычное": "Fine",
    "Нейтральное": "Fine",
    "Кокетливое / Романтичное": "Flirty / Romantic",
    "Кокетливое": "Flirty",
    "Кокетлив": "Flirty",
    "Кокетлива": "Flirty",
    "Очень кокетливое / Страстное": "Very Flirty / Passionate",
    "Пылкая влюбленность и страсть": "Deeply in Love & Passionate",
    "Вдохновленное": "Inspired",
    "Вдохновлен": "Inspired",
    "Вдохновлена": "Inspired",
    "Вдохновение": "Inspired",
    "Очень вдохновленное (Творческий подъем)": "Very Inspired (Creative High)",
    "Наивысшее вдохновение (Творческий экстаз)": "Creative Trance (Deep Inspiration)",
    "Внимательное / Сосредоточенное": "Focused",
    "Внимательное": "Focused",
    "Сосредоточен": "Focused",
    "Сосредоточена": "Focused",
    "Очень внимательное / Глубоко сосредоточенное": "Very Focused (Deep Concentration)",
    "Абсолютная концентрация (Состояние потока)": "In the Zone (Flow State)",
    "Игривое": "Playful",
    "Игрив": "Playful",
    "Игрива": "Playful",
    "Очень игривое / Шаловливое": "Very Playful (Silly)",
    "Истерика / Истерический безудержный хохот (Опасно для жизни!)": "Hysterical (Dangerously Playful!)",
    "Энергичное / Бодрое": "Energized",
    "Энергичное": "Energized",
    "Бодр": "Energized",
    "Бодра": "Energized",
    "Очень энергичное / На взводе (Полон сил)": "Very Energized (Pumped Up)",
    "Бурлящая гиперактивность": "Supercharged / Hyperactive",
    "Уверенное": "Confident",
    "Уверен": "Confident",
    "Уверена": "Confident",
    "Уверенный": "Confident",
    "Уверенная": "Confident",
    "Уверенность": "Confident",
    "Вдохновленный": "Inspired",
    "Вдохновленная": "Inspired",
    "Счастливый": "Happy",
    "Счастливая": "Happy",
    "Сердитый": "Angry",
    "Сердитая": "Angry",
    "Злой": "Angry",
    "Злая": "Angry",
    "Грустный": "Sad",
    "Грустная": "Sad",
    "Игривый": "Playful",
    "Игривая": "Playful",
    "Кокетливый": "Flirty",
    "Кокетливая": "Flirty",
    "Напряженный": "Tense",
    "Напряженная": "Tense",
    "Смущенный": "Embarrassed",
    "Смущенная": "Embarrassed",
    "Скучающий": "Bored",
    "Скучающая": "Bored",
    "Испуганный": "Scared",
    "Испуганная": "Scared",
    "Ошалелый": "Dazed",
    "Ошалелая": "Dazed",
    "Возбужденный": "Sexually Aroused",
    "Возбужденная": "Sexually Aroused",
    "Грустное": "Sad",
    "Очень грустное / Печальное": "Very Sad (Depressed)",
    "Глубокая депрессия / Безутешная скорбь": "Grieving / Severely Depressed",
    "Сердитое / Злое": "Angry",
    "Сердитое": "Angry",
    "Очень сердитое / В ярости": "Very Angry (Furious)",
    "Разъяренное / Неконтролируемая слепая ярость (Опасно для жизни!)": "Enraged (Blind Fury!)",
    "Дискомфорт": "Uncomfortable",
    "Сильный дискомфорт": "Very Uncomfortable",
    "Невыносимый дискомфорт и страдания": "Miserable (Severe Discomfort)",
    "Напряженное": "Tense",
    "Очень напряженное / На грани срыва": "Very Tense (Heavily Stressed)",
    "Сильнейший стресс / Нервный срыв": "Stressed Out (Mental Breakdown)",
    "Смущенное": "Embarrassed",
    "Очень смущенное": "Very Embarrassed (Humiliated)",
    "Сгорает со стыда / Смертельный позор (Опасно для жизни!)": "Mortified (Dying of Embarrassment!)",
    "Скучающее": "Bored",
    "Невыносимая скука / Тоска зеленая": "Utterly Bored",
    "Ошалевшее / Оглушенное": "Dazed",
    "Ошалевшее": "Dazed",
    "Сильное оглушение / Мутное сознание": "Very Dazed (Groggy)",
    "Полная прострация / Потеря ориентации": "Completely Disoriented / Dazed",
    "Сонное / Спит": "Asleep",
    "Сонное": "Sleepy",
    "Спит": "Asleep",
    "Испуганное": "Scared",
    "В ужасе / Сильный панический страх": "Terrified (Panicked)",
    "Панический парализующий ужас": "Paralyzed with Fear",
    "Сексуальное возбуждение / Страстное": "Sexually Aroused / Horny",
    "Сильное сексуальное возбуждение / Пылкая страсть": "Very Aroused / Lustful",
    "Наивысшее возбуждение и экстаз": "Intoxicated with Lust",
}


# =========================================================================
# 5. MOTIVES & NEEDS
# =========================================================================

MOTIVE_MAP_EN = {
    "Потребности в норме": "All needs satisfied",
    "Все потребности удовлетворены": "All needs satisfied",

    # Bladder
    "Критически хочет в туалет (едва сдерживается, острая нужда)": "Desperately needs bathroom (barely holding it, urgent)",
    "Хочет в туалет (нужно сходить в туалет)": "Needs bathroom (needs to pee)",
    "Естественная нужда: В норме": "Bladder: Fine",
    "Естественная нужда: Хочет в туалет": "Bladder: Needs bathroom",
    "Естественная нужда: Нестерпимо хочет в туалет": "Bladder: Desperate to pee",

    # Hunger
    "Умирает от голода (критически пустой желудок, сильное истощение)": "Starving (critically empty stomach, severe exhaustion)",
    "Умирает от голода (критически пустой желудок)": "Starving (critically empty stomach)",
    "Проголодался (хочет есть / перекусить)": "Hungry (wants to eat / snack)",
    "Проголодался (хочет есть)": "Hungry (wants to eat)",
    "Голод: Сыт(а)": "Hunger: Full",
    "Голод: Сыт": "Hunger: Full",
    "Голод: Сыта": "Hunger: Full",
    "Голод: Голоден": "Hunger: Hungry",
    "Голод: Голодна": "Hunger: Hungry",
    "Голод: Умирает от голода": "Hunger: Starving",

    # Energy
    "Валится с ног от усталости (критический недосып, засыпает на ходу)": "Collapsing from exhaustion (severe sleep deprivation, falling asleep on feet)",
    "Валится с ног от усталости (засыпает на ходу)": "Collapsing from exhaustion (falling asleep on feet)",
    "Устал (хочет спать / прилечь отдохнуть)": "Tired (wants to sleep / lie down to rest)",
    "Устал (хочет спать / отдохнуть)": "Tired (wants to sleep / rest)",
    "Энергия: Бодрое": "Energy: Rested",
    "Энергия: Усталость": "Energy: Tired",
    "Энергия: Истощение (валится с ног)": "Energy: Exhausted (collapsing)",

    # Hygiene
    "Ужасно грязен и плохо пахнет (критически необходим душ)": "Filthy and smells terrible (critically needs a shower)",
    "Ужасно грязен и плохо пахнет (срочно нужен душ)": "Filthy and smells terrible (urgently needs a shower)",
    "Не мешало бы помыться / принять душ": "Could use a wash / shower",
    "Не мешало бы принять душ / помыться": "Could use a shower / wash",
    "Гигиена: Чистый": "Hygiene: Clean",
    "Гигиена: Чистая": "Hygiene: Clean",
    "Гигиена: Грязный": "Hygiene: Dirty",
    "Гигиена: Грязная": "Hygiene: Dirty",
    "Гигиена: Ужасный запах": "Hygiene: Filthy / Stinking",

    # Fun
    "Умирает от скуки и тоски (острая нехватка развлечений)": "Dying of boredom (severely lacking entertainment)",
    "Умирает от скуки и тоски": "Dying of boredom",
    "Скучно (хочется развлечься или поиграть)": "Bored (wants some fun or games)",
    "Скучно (хочется развлечься)": "Bored (wants some fun)",
    "Досуг: Весело": "Fun: Having Fun",
    "Досуг: Скучно": "Fun: Bored",
    "Досуг: Невыносимая скука": "Fun: Desperately Bored",

    # Social
    "Крайне одинок (глубокая социальная изоляция, острая нехватка общения)": "Extremely lonely (severe social isolation, desperate for interaction)",
    "Крайне одинок (острая нехватка общения)": "Extremely lonely (desperate for interaction)",
    "Хочется пообщаться / поболтать с кем-нибудь": "Wants to socialize / chat with someone",
    "Хочется пообщаться с кем-нибудь": "Wants to socialize with someone",
    "Общение: Доволен": "Social: Satisfied",
    "Общение: Довольна": "Social: Satisfied",
    "Общение: Одинок": "Social: Lonely",
    "Общение: Одинока": "Social: Lonely",
    "Общение: Отчаянно одинок": "Social: Desperately Lonely",
    "Общение: Отчаянно одинока": "Social: Desperately Lonely",

    # Occult Needs
    "Мучительная вампирская жажда (готов напасть ради свежей крови)": "Agonizing vampire thirst (ready to attack for fresh blood)",
    "Вампирская жажда (нужна свежая кровь или пакет с кровью)": "Vampire thirst (needs fresh blood or blood pack)",
    "Критическое обезвоживание (нужна вода / океан)": "Critically dehydrated (needs water / ocean)",
    "Обезвоживание (нужно увлажнение / душ / плавание)": "Dehydrated (needs hydration / shower / swim)",
    "Критическая засуха и увядание (ростоман вянет без воды)": "Critically parched and wilting (PlantSim is wilting without water)",
    "Обезвоживание ростомана (нужно поглотить воду или полить себя)": "PlantSim dehydrated (needs to absorb water or shower)",
    "Истощение без солнца (ростоману критически необходим солнечный свет)": "Solar exhaustion (PlantSim critically needs sunlight)",
    "Нехватка солнечного света (ростоману нужен свет для фотосинтеза)": "Lacking sunlight (PlantSim needs sunlight for photosynthesis)",
}


# =========================================================================
# 6. TRAITS & ARCHETYPES
# =========================================================================

TRAIT_MAP_EN = {
    # Aspiration Bonus Traits
    "Способный ученик": "Quick Learner",
    "Утонченный вкус": "Muser",
    "Очаровательный": "Alluring",
    "Очаровательная": "Alluring",
    "Коллекционер": "Collector",
    "Негодяй": "Dastardly",
    "Делец": "Business Savvy",
    "Общительный": "Gregarious",
    "Общительная": "Gregarious",
    "Домосед": "Home Turf",
    "Повышенный обмен веществ": "High Metabolism",
    "Связь с животными": "Animal Affinity",
    "Домосед / Семейный": "Domestic",
    "Сущность вкуса": "Essence of Flavor",
    "Долгожитель": "Long Lived",

    # RPO & Family Preference Traits
    "Хочет детей": "Wants Children",
    "Не хочет детей": "Does Not Want Children",
    "Нейтральное отношение к детям": "Indifferent About Children",

    # Reward Store & Milestone Traits
    "Любитель целоваться": "Beguiling",
    "Многодетность": "Fertile",
    "Сова": "Night Owl",
    "Жаворонок": "Early Bird",
    "Трудоголик": "Workaholic",
    "Бережливый": "Frugal",
    "Независимый": "Independent",
    "Беспечный": "Carefree",
    "Предприниматель": "Entrepreneurial",
    "Визуализатор": "Visualizer",
    "Связи": "Connections",
    "Проницательный": "Observant",
    "Быстрый читатель": "Speed Reader",
    "Быстрый уборщик": "Speed Cleaner",
    "Укротитель голода": "Hardly Hungry",
    "Неустающий": "Never Weary",
    "Чистоплотный": "Antiseptic",
    "Стальной мочевой пузырь": "Steel Bladder",
    "Служба спасения": "Always Welcome",
    "Невероятное дружелюбие": "Incredibly Friendly",
    "Гений кулинарии": "Master Chef",
    "Творец": "Creative Visionary",
    "Ученый": "Savvy",

    "Злой": "Evil",
    "Чистюля": "Neat",
    "Азартный / Стремится побеждать": "Competitive",
    "Романтик": "Romantic",
    "Гений": "Genius",
    "Творческий": "Creative",
    "Ленивый": "Lazy",
    "Активный": "Active",
    "Растяпа": "Goofball",
    "Вспыльчивый": "Hot-Headed",
    "Одиночка": "Loner",
    "Общительный": "Outgoing",
    "Перфекционист": "Perfectionist",
    "Амбициозный": "Ambitious",
    "Книжный червь": "Bookworm",
    "Гурман": "Foodie",
    "Сноб": "Snob",
    "Самовлюбленный": "Self-Absorbed",
    "Эксцентричный": "Geek",
    "Любитель искусства": "Art Lover",
    "Меломан": "Music Lover",
    "Брат / Свой в доску": "Bro",
    "Добрый": "Good",
    "Жизнерадостный": "Cheerful",
    "Угрюмый": "Gloomy",
    "Неуклюжий": "Clumsy",
    "Неряха": "Slob",
    "Задира": "Mean",
    "Клептоман": "Kleptomaniac",
    "Вечное дитя": "Childish",
    "Ревнивый": "Jealous",
    "Чудаковатый": "Erratic",
    "Семьянин": "Family-Oriented",
    "Меркантильный": "Materialistic",
    "Недотрога": "Unflirty",
    "Обжора": "Glutton",
    "Уверенный в себе": "Self-Assured",
    "Самоуверенный": "Self-Assured",
    "Самоуверенная": "Self-Assured",
    "Уверенный": "Self-Assured",
    "Уверенная": "Self-Assured",
    "Параноик": "Paranoid",
    "Безумный": "Erratic",
    "Ненавидит детей": "Hates Children",
    "Любит природу": "Loves Outdoors",
    "Вегетарианец": "Vegetarian",
    "Непостоянный": "Noncommittal",
    "Брезгливый": "Squeamish",
    "Привереда": "Squeamish",
    "Танцмашина": "Dance Machine",
    "Свой человек": "Insider",
    "Привередливый": "High Maintenance",
    "Карьерист / Достигатор": "Overachiever",
    "Любопытный": "Nosy",
    "Дитя океана": "Child of the Islands / Ocean",
    "Дитя островов": "Child of the Islands",
    "Мастер на все руки": "Maker",
    "Фриган": "Freegan",
    "Эко-активист": "Recycle Disciple",
    "Щедрый": "Generous",
    "Преданный": "Loyal",
    "Неуклюжий в общении": "Socially Awkward",
    "Любит приключения": "Adventurous",
    "Воспитанный": "Proper",
    "Непереносимость лактозы": "Lactose Intolerant",
    "Любитель животных": "Animal Enthusiast",
    "Любит собак": "Dog Lover",
    "Любит кошек": "Cat Lover",
    "Любит лошадей": "Horse Lover",
    "Хозяин ранчо": "Ranch Hand",
    "Мудрый": "Wise",
    "Скептик": "Skeptical",
    "Кринжовый": "Cringe",
    "Мрачный": "Macabre",
    "Идеалист": "Idealist",
    "Тусовщик": "Party Animal",

    # Feminine forms
    "Добрая": "Good",
    "Злая": "Evil",
    "Активная": "Active",
    "Ленивая": "Lazy",
    "Гениальная": "Genius",
    "Творческая": "Creative",
    "Жизнерадостная": "Cheerful",
    "Угрюмая": "Gloomy",
    "Неуклюжая": "Clumsy",
    "Ревнивая": "Jealous",
    "Семьянинка": "Family-Oriented",
    "Меркантильная": "Materialistic",
    "Общительная": "Outgoing",
    "Уверенная в себе": "Self-Assured",
    "Амбициозная": "Ambitious",
    "Щедрая": "Generous",
    "Преданная": "Loyal",
    "Воспитанная": "Proper",
    "Мудрая": "Wise",

    # Toddler & Infant
    "Прилипчивый": "Clingy",
    "Ангелочек": "Angelic",
    "Капризный": "Fussy",
    "Независимый": "Independent",
    "Любознательный": "Inquisitive",
    "Шутник": "Silly",
    "Обаяшка": "Charmer",
    "Неугомонный": "Wild",
    "Осторожный": "Cautious",
    "Чувствительный": "Sensitive",
    "Спокойный": "Calm",
    "Энергичный": "Intense / Energetic",
    "Непоседа": "Wiggly",

    # Rewards
    "Вечная свежесть (Награда)": "Forever Fresh (Reward)",
    "Независимый (Награда)": "Independent (Reward)",
    "Профессиональный бездельник (Награда)": "Professional Slacker (Reward)",

    # Archetypes
    "Славный малый": "Everyman (Archetype: grounded, loyal, simplicity)",
    "Мудрец": "Sage (Archetype: pursuit of truth, deep reflection)",
    "Опекун": "Caregiver (Archetype: protective, selfless, caring)",
    "Герой": "Hero (Archetype: courageous, overcoming challenges)",
    "Творец": "Creator / Artist (Archetype: imagination, self-expression)",
    "Невинный": "Innocent (Archetype: optimistic, pure, trusting)",
    "Любовник": "Lover (Archetype: romance, passion, intimacy)",
    "Шут": "Jester (Archetype: humor, living in the moment, fun)",
    "Бунтарь": "Rebel (Archetype: rule-breaker, defiant, bold)",

    # WickedWhims
    "Сексуальная привлекательность (WickedWhims)": "Sexually Alluring (WickedWhims)",
    "Сексуальный авантюрист (WickedWhims)": "Sexually Adventurous (WickedWhims)",
    "Воздержание (WickedWhims)": "Sexually Abstinent (WickedWhims)",
    "Щедрый любовник (WickedWhims)": "Generous Lover (WickedWhims)",
    "Эгоистичный любовник (WickedWhims)": "Selfish Lover (WickedWhims)",
    "Любитель спермы (WickedWhims)": "Cumslut (WickedWhims)",
    "Куколд (WickedWhims)": "Cuckold (WickedWhims)",
    "Эксгибиционист (WickedWhims)": "Exhibitionist (WickedWhims)",
    "Любитель наготы (WickedWhims)": "Nudity Enthusiast (WickedWhims)",
    "Прирожденный нудист (WickedWhims)": "Born Nudist (WickedWhims)",
    "Стесняется наготы (WickedWhims)": "Nudity Avoider (WickedWhims)",
    "Любитель подглядывать (WickedWhims)": "Peeping Enthusiast (WickedWhims)",
    "Полиамор (WickedWhims)": "Polyamorous (WickedWhims)",
    "Верный (WickedWhims)": "Faithful (WickedWhims)",
    "Изменник (WickedWhims)": "Sex Cheater (WickedWhims)",
    "Асоциальный (WickedWhims)": "Asocial (WickedWhims)",
    "Чудак (WickedWhims)": "Weirdo (WickedWhims)",
    "Застенчивый (WickedWhims)": "Shy (WickedWhims)",
    "Похотливый (WickedWhims)": "Lustful (WickedWhims)",
    "Инцест (WickedWhims)": "Incest (WickedWhims)",
    "Фарфоровая кукла (WickedWhims)": "Porcelain Doll (WickedWhims)",
    "Повышенная фертильность (WickedWhims)": "High Fertility (WickedWhims)",
    "Проблемы с фертильностью (WickedWhims)": "Fertility Issues (WickedWhims)",
    "Привлекательный (WickedWhims)": "Attractive (WickedWhims)",
    "Впечатлительный (WickedWhims)": "Impressionable (WickedWhims)",
    "Раскрепощенный (WickedWhims)": "Uninhibited (WickedWhims)",
    "Страстный (WickedWhims)": "Passionate (WickedWhims)",
    "Лидер нудистов (WickedWhims)": "Nudist Leader (WickedWhims)",
    "Обычный характер": "Average personality",
}


# =========================================================================
# 7. RELATIONSHIPS & FAMILY LABELS
# =========================================================================

RELATIONSHIP_MAP_EN = {
    # Compounds & Strangers (longest matches first)
    "Незнакомец / Не знаком": "Stranger / Not Acquainted",
    "Незнакомка / Не знакома": "Stranger / Not Acquainted",
    "Незнакомец / Не знакома": "Stranger / Not Acquainted",
    "Незнакомка / Не знаком": "Stranger / Not Acquainted",
    "Незнакомцы / Не знакомы": "Strangers / Not Acquainted",
    "Незнакомец": "Stranger",
    "Незнакомка": "Stranger",
    "Незнакомцы": "Strangers",
    "Не знаком": "Not Acquainted",
    "Не знакома": "Not Acquainted",
    "Не знакомы": "Not Acquainted",

    # In-laws & Extended Family
    "Зять (Муж дочери)": "Son-in-law",
    "Невестка (Жена сына)": "Daughter-in-law",
    "Свёкор / Тесть": "Father-in-law",
    "Свекровь / Тёща": "Mother-in-law",
    "Деверь / Шурин / Зять": "Brother-in-law",
    "Золовка / Свояченица / Невестка": "Sister-in-law",
    "Родственница по браку": "In-law (female)",
    "Родственник по браку": "In-law (male)",
    "Родственница": "Relative (female)",
    "Родственник": "Relative (male)",
    "Родственники": "Relatives",

    # Affairs & Complex Romance
    "Любовница [двойная измена / оба в браке]": "Mistress [mutual affair / both married]",
    "Любовник [двойная измена / оба в браке]": "Lover [mutual affair / both married]",
    "Любовница [роман на стороне при живой жене]": "Mistress [affair on wife]",
    "Любовник [роман на стороне при живом муже]": "Lover [affair on husband]",
    "Любовница [замужняя женщина / измена её мужу]": "Mistress [married woman]",
    "Любовник [женатый мужчина / измена его жене]": "Lover [married man]",
    "Любовница [двойная интрижка / оба в браке]": "Mistress [mutual affair / both married]",
    "Любовник [двойная интрижка / оба в браке]": "Lover [mutual affair / both married]",
    "Любовница (интрижка на стороне при живой жене)": "Mistress (side affair)",
    "Любовник (интрижка на стороне при живом муже)": "Lover (side affair)",
    "Любовница (замужняя интрижка)": "Mistress (married woman)",
    "Любовник (женатый партнер)": "Lover (married man)",
    "Любовница": "Lover / Mistress",
    "Любовник": "Lover",
    "Любовники": "Lovers",
    "Симпатия / Влюбленность": "Crush / Infatuation",
    "Романтический интерес": "Romantic Interest",
    "Возлюбленные": "Lovers / Sweethearts",
    "Возлюбленный": "Sweetheart / Lover",
    "Возлюбленная": "Sweetheart / Lover",

    # Standard Romance & Spouses
    "Муж": "Husband",
    "Жена": "Wife",
    "Жених": "Fiancé",
    "Невеста": "Fiancée",
    "Парень": "Boyfriend",
    "Девушка": "Girlfriend",
    "Супруг(а)": "Spouse",
    "Супруг / Супруга": "Spouse",
    "Супруг": "Spouse",
    "Супруга": "Spouse",
    "Супруги": "Spouses",
    "Парень / Девушка": "Boyfriend / Girlfriend",
    "Парень(девушка)": "Boyfriend / Girlfriend",
    "Жених / Невеста": "Fiancé / Fiancée",
    "Жених(невеста)": "Fiancé / Fiancée",
    "Друг(подруга)": "Friend",
    "Друг (подруга)": "Friend",
    "Друг / Подруга": "Friend",
    "Партнер": "Partner",
    "Партнерша": "Partner",
    "Партнеры": "Partners",
    "Бывший муж": "Ex-Husband",
    "Бывшая жена": "Ex-Wife",
    "Бывший парень": "Ex-Boyfriend",
    "Бывшая девушка": "Ex-Girlfriend",
    "Бывший": "Ex-Partner",
    "Бывшая": "Ex-Partner",

    # Immediate Family
    "Отец": "Father",
    "Папа": "Dad",
    "Мать": "Mother",
    "Мама": "Mom",
    "Сын": "Son",
    "Дочь": "Daughter",
    "Брат": "Brother",
    "Сестра": "Sister",
    "Дедушка": "Grandfather",
    "Бабушка": "Grandmother",
    "Внук": "Grandson",
    "Внучка": "Granddaughter",
    "Дядя": "Uncle",
    "Тетя": "Aunt",
    "Тётя": "Aunt",
    "Двоюродный брат": "Cousin (male)",
    "Двоюродная сестра": "Cousin (female)",
    "Кузен": "Cousin",
    "Кузина": "Cousin",
    "Племянник": "Nephew",
    "Племянница": "Niece",
    "Отчим": "Stepfather",
    "Мачеха": "Stepmother",
    "Пасынок": "Stepson",
    "Падчерица": "Stepdaughter",
    "Сводный брат": "Stepbrother",
    "Сводная сестра": "Stepsister",

    # Social & Friendship
    "Лучшие друзья": "Best Friends",
    "Лучший друг": "Best Friend",
    "Лучшая подруга": "Best Friend",
    "Хорошие друзья": "Good Friends",
    "Хороший друг": "Good Friend",
    "Хорошая подруга": "Good Friend",
    "Друзья": "Friends",
    "Друг": "Friend",
    "Подруга": "Friend",
    "Приятель": "Buddy / Pal",
    "Приятельница": "Buddy / Pal",
    "Приятели": "Buddies / Pals",
    "Знакомый / Знакомая": "Acquaintance",
    "Знакомые": "Acquaintances",
    "Знакомый": "Acquaintance",
    "Знакомая": "Acquaintance",
    "Неприязнь": "Disliked",
    "Враги": "Enemies",
    "Враг": "Enemy",
    "Заклятые враги": "Nemesis",
    "Заклятый враг": "Nemesis",
    "Собеседники": "Chat Partners",
    "Сетевые собеседники": "Online Contacts",
    "Соседка по дому": "Housemate / Roommate",
    "Сосед по дому": "Housemate / Roommate",
    "Сожитель": "Roommate",
    "Сожительница": "Roommate",
    "Сожители": "Roommates",
    "Соседи": "Neighbors / Roommates",
    "Сосед": "Neighbor / Roommate",
    "Соседка": "Neighbor / Roommate",
    "Коллега по работе": "Coworker",
    "Коллега": "Coworker",
    "Коллеги": "Coworkers",
    "Одноклассник": "Classmate",
    "Одноклассница": "Classmate",
    "Одноклассники": "Classmates",
    "Одногруппник": "Classmate / Roommate",
    "Одногруппница": "Classmate / Roommate",

    # Taboo & Incest
    "[инцест-отношения]": "[TABOO/INCEST relationship]",
    "[ИНЦЕСТ-ОТНОШЕНИЯ]": "[TABOO/INCEST relationship]",
    "[инцест]": "[TABOO/INCEST]",
    "[ИНЦЕСТ]": "[TABOO/INCEST]",
}

SOCIAL_STYLE_MAP_EN = {
    "Приятный разговор": "Pleasant conversation",
    "Непринужденный разговор": "Casual conversation",
    "Дружеский разговор": "Friendly conversation",
    "Кокетливый / очаровательный разговор": "Flirty / charming conversation",
    "Намекающий / романтический разговор": "Suggestive / romantic conversation",
    "Интимный / страстный разговор": "Steamy / passionate conversation",
    "Скучный / затянувшийся разговор": "Boring / prolonged conversation",
    "Занудный разговор": "Tedious conversation",
    "Неловкий / натянутый разговор": "Awkward / strained conversation",
    "Оскорбительный разговор": "Offensive conversation",
    "Обидный разговор": "Insulting conversation",
    "Горячий спор / ссора": "Heated argument / quarrel",
    "Очень веселый и смешной разговор": "Hilarious and funny conversation",
    "Игривый разговор": "Playful conversation",
    "Напряженный разговор (ссора, на повышенных тонах)": "Tense conversation (quarrel, raised voices)",
    "Флиртующий": "Flirting",
    "Флирт": "Flirting",
    "Кокетливый": "Flirty",
    "Вспыльчивый": "Hot-headed",
    "Спокойный": "Calm",
    "Дружеский": "Friendly",
    "Дружелюбный": "Friendly",
    "Агрессивный": "Aggressive",
    "Романтичный": "Romantic",
    "Романтический": "Romantic",
    "Веселый": "Playful / Cheerful",
    "Смешной": "Funny",
    "Игривый": "Playful",
    "Напряженный": "Tense",
    "Неловкий": "Awkward",
    "Скучный": "Boring",
    "Сердитый": "Angry",
    "Злой": "Angry",
}


def translate_social_style_en(style_str: str) -> str:
    """Translates conversation style/tone into English."""
    if not style_str:
        return "Casual conversation"
    res = style_str.strip()
    if res in SOCIAL_STYLE_MAP_EN:
        return SOCIAL_STYLE_MAP_EN[res]
    for k in sorted(SOCIAL_STYLE_MAP_EN.keys(), key=len, reverse=True):
        if k.lower() in res.lower():
            return SOCIAL_STYLE_MAP_EN[k]
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


# =========================================================================
# 8. COMMON ACTIVITIES & ROOMS TRANSLATOR
# =========================================================================

ACTIVITY_PATTERNS_EN = [
    (r"(?i)стоит на месте,\s*осматривается", "Standing in place, looking around"),
    (r"(?i)стоит на месте", "Standing in place"),
    (r"(?i)осматривается", "Looking around"),

    # Rocket Science & Space Exploration
    (r"(?i)строит космическую ракету(\s*\(ракетостроение\))?|строительств.*ракет", "Building a space rocket (rocket science)"),
    (r"(?i)продолжает строительство космической ракеты", "Continuing construction of the space rocket"),
    (r"(?i)помогает строить космическую ракету(\s*\(ракетостроение\))?", "Assisting in building a space rocket (rocket science)"),
    (r"(?i)модернизирует.*космическую ракету|улучшает.*ракету", "Upgrading and modifying the space rocket"),
    (r"(?i)защитн.*пушк.*ракет", "Installing ion cannon defense system on the space rocket"),
    (r"(?i)топливн.*бак.*ракет", "Installing auxiliary fuel tanks on the space rocket"),
    (r"(?i)ускорител.*ракет", "Installing additional thruster boosters on the space rocket"),
    (r"(?i)стабилизатор.*ракет", "Installing landing stabilizers on the space rocket"),
    (r"(?i)грузов.*отсек.*ракет", "Expanding the space rocket's cargo bay"),
    (r"(?i)генератор червоточин.*ракет", "Installing a wormhole generator on the space rocket"),
    (r"(?i)летит на.*ракет.*сиксим", "Flying through a wormhole to the alien planet Sixam in a rocket"),
    (r"(?i)летит на космической ракете(\s*\(исследует вселенную\))?|полет.*космос.*ракет", "Flying into outer space in a rocket (exploring the universe)"),
    (r"(?i)космическ.*гонк.*ракет", "Competing in a space race in a rocket"),
    (r"(?i)диверси.*ракет.*", "Sabotaging the space rocket (stuffing exhaust pipe with fruit)"),
    (r"(?i)обломк.*ракет|ремонтирует ракету", "Salvaging crashed rocket debris / repairing the rocket"),
    (r"(?i)вуху в космической ракете(\s*\(в невесомости\))?", "WooHooing in the space rocket (in zero gravity)"),
    (r"(?i)уединяется с (.+?) для страстного вуху в гардеробе", r"Sneaking off with \1 for passionate closet romance"),
    (r"(?i)тайно занимается вуху среди кустов живого лабиринта с (.+)", r"Secretly hooking up in hedge maze with \1"),
    (r"(?i)уединяется в гардеробе для романтического вуху с\s*", "Hooking up in walk-in closet with "),
    (r"(?i)уединяется для романтического вуху в лабиринте кустов с\s*", "Sneaking away for maze romance with "),
    (r"(?i)уединяется с (.+?) для головокружительного вуху на вершине маяка!?", r"Sneaking off with \1 for breathtaking lighthouse romance"),
    (r"(?i)занимается головокружительным вуху на вершине маяка", "Having breathtaking WooHoo at the top of the lighthouse"),
    (r"(?i)уединяется с (.+?) для страстного вуху в куче шуршащих листьев!?", r"Sneaking off with \1 for passionate autumn leaf pile romance"),
    (r"(?i)занимается страстным осенним вуху в куче шуршащих листьев", "Having passionate autumn leaf pile WooHoo"),
    (r"(?i)уединяется с (.+?) для роскошного вуху прямо на куче денег в сейфе!?", r"Sneaking off with \1 for luxurious money vault romance"),
    (r"(?i)занимается роскошным вуху на куче денег в гигантском сейфе", "Having luxurious WooHoo on a pile of money in the vault"),
    (r"(?i)уединяется с (.+?) для страстного романтического вуху под тропическим водопадом!?", r"Sneaking off with \1 for passionate tropical waterfall romance"),
    (r"(?i)занимается страстным романтическим вуху под струями тропического водопада", "Having passionate tropical waterfall WooHoo"),
    (r"(?i)уединяется с (.+?) для экстремального вуху прямо в мусорном контейнере!?", r"Sneaking off with \1 for extreme dumpster romance"),
    (r"(?i)занимается экстремальным вуху прямо в мусорном контейнере", "Having extreme dumpster WooHoo"),
    (r"(?i)уединяется с (.+?) для романтического вуху в уютной горной палатке на склоне комореби!?", r"Sneaking off with \1 for cozy mountain tent romance on Mt. Komorebi"),
    (r"(?i)занимается романтическим вуху в горной палатке на склоне комореби", "Having cozy mountain tent WooHoo on Mt. Komorebi"),
    (r"(?i)уединяется с (.+?) для экстремального вуху в ледяной пещере на вершине комореби!?", r"Sneaking off with \1 for extreme ice cave romance at the peak of Mt. Komorebi"),
    (r"(?i)занимается экстремальным вуху в ледяной пещере на вершине комореби", "Having extreme ice cave WooHoo at the peak of Mt. Komorebi"),
    (r"(?i)уединяется с (.+?) для чувственного вуху в парящих горячих источниках онсэн!?", r"Sneaking off with \1 for sensual onsen hot springs romance"),
    (r"(?i)занимается чувственным вуху в парящих водах горячего источника онсэн", "Having sensual onsen hot springs WooHoo"),
    (r"(?i)весело мчится на санках со снежной горки вместе с (.+?)!?", r"Happily sledding down the snowy hill together with \1"),
    (r"(?i)уединяется с (.+?) для страстного деревенского вуху прямо в курятнике!?", r"Sneaking off with \1 for passionate rustic chicken coop romance"),
    (r"(?i)занимается деревенским вуху в уютном курятнике", "Having rustic chicken coop WooHoo"),
    (r"(?i)уединяется с (.+?) для романтического вуху на самой вершине колеса обозрения!?", r"Sneaking off with \1 for romantic Ferris wheel romance at the top"),
    (r"(?i)занимается романтическим вуху в кабинке колеса обозрения", "Having romantic Ferris wheel WooHoo"),
    (r"(?i)уединяется с (.+?) для щекочущего нервы вуху в жутком доме с привидениями!?", r"Sneaking off with \1 for thrilling haunted house romance"),
    (r"(?i)занимается щекочущим нервы вуху в доме с привидениями", "Having thrilling haunted house WooHoo"),
    (r"(?i)уединяется с (.+?) для нежного вуху в лодочке туннеля любви!?", r"Sneaking off with \1 for sweet tunnel of love romance"),
    (r"(?i)занимается нежным вуху в лодочке аттракциона «туннель любви»", "Having sweet tunnel of love WooHoo in swan boat"),
    (r"(?i)уединяется с (.+?) для тайного страстного вуху за шторкой фотобудки!?", r"Sneaking off with \1 for secret passionate photo booth romance"),
    (r"(?i)занимается тайным страстным вуху в фотобудке", "Having secret passionate photo booth WooHoo"),
    (r"(?i)торжественно делает предложение пойти на выпускной бал для (.+?)(?:!|$)", r"Grandly asking \1 to prom with a creative promposal banner"),
    (r"(?i)кружится в медленном романтическом танце под огнями софитов бала с (.+)", r"Slow dancing under prom spotlight with \1"),
    (r"(?i)тренирует дальние броски и пасы мяча для американского футбола с (.+)", r"Practicing football passes and long throws with \1"),
    (r"(?i)затевает веселый и яростный бой подушками на кровати с (.+?)(?:!|$)", r"Starting a fun and fierce pillow fight on bed with \1!"),
    # EP13 Growing Together (Treehouse WooHoo, Friendship Bracelets, Infants & Bike)
    (r"(?i)уединяется с (.+?) для романтического вуху в уютном домике на дереве!?", r"Sneaking off with \1 for romantic treehouse romance"),
    (r"(?i)занимается романтическим вуху в домике на дереве", "Having romantic treehouse WooHoo"),
    (r"(?i)торжественно повязывает сплетенный вручную браслет дружбы на запястье (.+)", r"Grandly tying a hand-woven friendship bracelet onto \1's wrist"),
    (r"(?i)выкладывает на животик младенца \((.+?)\), тренируя мышцы шеи", r"Placing infant (\1) on tummy for neck muscle practice"),
    (r"(?i)терпеливо учит ползать и координировать движения младенца \((.+?)\)", r"Patiently teaching infant (\1) to crawl and coordinate movements"),
    (r"(?i)учит самостоятельно сидеть и держать равновесие младенца \((.+?)\)", r"Teaching infant (\1) to sit up and balance independently"),
    (r"(?i)радуется первым шагам и попыткам стоять младенца \((.+?)\)!", r"Celebrating first steps and standing attempts of infant (\1)!"),
    (r"(?i)меняет подгузник младенцу \((.+?)\) на пеленальном столике", r"Changing infant (\1)'s diaper on changing table"),
    (r"(?i)кормит младенца \((.+?)\) полезным детским питанием", r"Feeding infant (\1) nutritious baby food in high chair"),
    (r"(?i)носит в удобном слинге-переноске младенца \((.+?)\)", r"Carrying infant (\1) in a comfortable baby carrier sling"),
    (r"(?i)нежно убаюкивает и укладывает в кроватку младенца \((.+?)\)", r"Gently rocking and putting infant (\1) to sleep in crib"),
    (r"(?i)осторожно купает в теплой мыльной воде младенца \((.+?)\)", r"Gently bathing infant (\1) in warm soapy water"),
    (r"(?i)играет в «ку-ку» и смешит забавными звуками младенца \((.+?)\)", r"Playing peek-a-boo and making funny sounds to entertain infant (\1)"),
    (r"(?i)с нежностью заботится и проводит время с младенцем \((.+?)\)", r"Lovingly caring for and spending time with infant (\1)"),
    (r"(?i)учит кататься на двухколесном велосипеде \((.+?)\)", r"Patiently teaching (\1) to ride a two-wheeled bicycle"),
    # EP14 Horse Ranch (Horses, Foals, Mini Pets, Haystack WooHoo, Line Dance, Ranch Hand)
    (r"(?i)уединяется с (.+?) для страстного вуху прямо в мягком ароматном стоге сена!?", r"Sneaking off with \1 for passionate rustic haystack romance"),
    (r"(?i)занимается страстным деревенским вуху в стоге сена", "Having passionate rustic haystack WooHoo"),
    (r"(?i)лихо отплясывает зажигательные кантри-танцы под звуки ранчо-радио вместе с (.+?)(?:!|$)", r"Energetically line dancing to ranch radio music together with \1!"),
    (r"(?i)обсуждает фронт работы по ранчо с разнорабочим (.+)", r"Discussing ranch chores and tasks with ranch hand \1"),
    (r"(?i)умело доит мини-козочку \((.+?)\), собирая свежее домашнее молоко", r"Skillfully milking mini goat (\1) for fresh farm milk"),
    (r"(?i)бережно стрижет шерсть с мини-овечки \((.+?)\), заготавливая руно для пряжи", r"Carefully shearing wool from mini sheep (\1) for yarn"),
    (r"(?i)заботливо кормит из бутылочки крошечного питомца \((.+?)\)", r"Lovingly bottle-feeding tiny mini pet (\1)"),
    (r"(?i)с умилением гладит и ласкает карликового любимца \((.+?)\)", r"Fondly petting and cuddling mini pet (\1)"),
    (r"(?i)заботится и ухаживает за крошечным питомцем \((.+?)\)", r"Caring for and tending to tiny mini pet (\1)"),
    (r"(?i)участвует в престижном конном соревновании каньона честнат-ридж на коне \((.+?)\)!", r"Competing in prestigious Chestnut Ridge equestrian tournament on horse (\1)!"),
    (r"(?i)бережно кормит теплой молочной смесью из бутылочки маленького жеребенка \((.+?)\)", r"Gently bottle-feeding warm milk to little foal (\1)"),
    (r"(?i)весело играет и резвится в загоне с маленьким жеребенком \((.+?)\)", r"Happily playing and romping in paddock with little foal (\1)"),
    (r"(?i)с нежностью обнимает и прижимается к маленькому жеребенку \((.+?)\)", r"Lovingly hugging and snuggling little foal (\1)"),
    (r"(?i)заботливо ухаживает и растит жеребенка \((.+?)\)", r"Lovingly caring for and nurturing foal (\1)"),
    (r"(?i)лихо закладывает виражи вокруг бочек на коне \((.+?)\) на бешеной скорости!?", r"Sharp-turning around barrels at high speed on horse (\1)!"),
    (r"(?i)отрабатывает эффектные прыжки через кавалетти и барьеры на коне \((.+?)\)", r"Practicing jumping over cavaletti and hurdles on horse (\1)"),
    (r"(?i)ловко садится в седло коня \((.+?)\)", r"Deftly mounting the saddle of horse (\1)"),
    (r"(?i)спешивается и гладит по морде коня \((.+?)\)", r"Dismounting and stroking the muzzle of horse (\1)"),
    (r"(?i)уверенно скачет верхом на коне \((.+?)\), наслаждаясь ветром и просторами каньона", r"Riding horse (\1) across canyon trails, enjoying the breeze"),
    (r"(?i)аккуратно расчищает и проверяет копыта коня \((.+?)\) специальным крючком", r"Carefully cleaning and checking hooves of horse (\1) with hoof pick"),
    (r"(?i)заботливо вычесывает и начищает до блеска лоснящуюся шерсть коня \((.+?)\)", r"Lovingly brushing and grooming sleek coat of horse (\1) to a shine"),
    (r"(?i)угощает хрустящим лакомством и ласково треплет по гриве коня \((.+?)\)", r"Offering crunchy treat and patting mane of horse (\1)"),
    (r"(?i)наполняет поилку свежей прохладной водой для коня \((.+?)\)", r"Refilling water trough with fresh cool water for horse (\1)"),
    (r"(?i)нежно прижимается щекой к теплой шее коня \((.+?)\) и шепчет ему на ухо", r"Gently resting cheek against warm neck of horse (\1) and whispering softly"),
    (r"(?i)с любовью заботится и ухаживает за конем \((.+?)\)", r"Lovingly caring for and tending to horse (\1)"),
    # EP15 For Rent (Break-Ins, Snooping, Secrets, Landlord & Tenants, Marbles)
    (r"(?i)взламывает замок чужой квартиры (.+?) отмычкой!?", r"Picking the lock to \1's apartment with a lockpick!"),
    (r"(?i)рыется в чужих вещах и ящиках квартиры (.+?), выискивая компрометирующие тайны", r"Snooping through \1's belongings and drawers searching for juicy secrets"),
    (r"(?i)прикладывает ухо к замочной скважине двери (.+?), жадно подслушивая чужой разговор", r"Pressing ear against \1's keyhole, eagerly eavesdropping on conversation"),
    (r"(?i)шантажирует сочной выведанной тайной (.+?), требуя деньги", r"Blackmailing \1 with an uncovered secret, demanding cash"),
    (r"(?i)оформляет принудительное выселение проблемного арендатора (.+?) за нарушение правил!?", r"Formally evicting troublesome tenant \1 for lease violations!"),
    (r"(?i)собирает арендную плату за жилье с (.+)", r"Collecting residential rent payment from \1"),
    (r"(?i)тщательно осматривает арендуемое жилье жильца (.+?), проверяя состояние квартиры", r"Thoroughly inspecting tenant \1's rental unit and condition"),
    (r"(?i)сосредоточенно выбивает стеклянные шарики-марблс из круга вместе с (.+)", r"Flicking glass marbles out of the ring together with \1"),
    (r"(?i)занимается вопросами аренды жилья вместе с (.+)", r"Handling rental property matters together with \1"),
    # EP16 Lovestruck (Cupid's Corner, Romantic Blanket, Hourly Motel, Seduction, Eggplant Costume, Couples Therapy, Ciudad Enamorada)
    (r"(?i)занимается уморительным и страстным вуху в костюме баклажана вместе с (.+?)(?:!|$)", r"Having hilarious and passionate eggplant costume romance together with \1!"),
    (r"(?i)занимается комичным вуху в нелепом костюме баклажана", "Having funny WooHoo in a ridiculous eggplant costume"),
    (r"(?i)уединяется с (.+?) для страстного вуху прямо на романтическом пледе!?", r"Sneaking off with \1 for passionate romance on the romantic blanket"),
    (r"(?i)занимается романтическим вуху на мягком пледе под открытым небом", "Having romantic WooHoo on a soft blanket under open sky"),
    (r"(?i)лежит в обнимку с (.+?) на романтическом пледе, любуясь звездами", r"Cuddling with \1 on romantic blanket stargazing"),
    (r"(?i)уютно располагается на романтическом пледе вместе с (.+)", r"Cozying up on romantic blanket together with \1"),
    (r"(?i)скрывается от посторонних глаз с (.+?) для пылкого вуху в мотеле на час!?", r"Sneaking off with \1 for passionate hourly motel rendezvous"),
    (r"(?i)занимается тайным страстным вуху в уютном номере мотеля", "Having secret passionate motel room WooHoo"),
    (r"(?i)снимает номер в мотеле для тайного свидания с (.+)", r"Renting a motel room for a secret date with \1"),
    (r"(?i)исполняет соблазнительный приватный танец для (.+)", r"Performing a seductive lap dance for \1"),
    (r"(?i)кружится в чувственном медленном танце с эффектным прогибом вместе с (.+)", r"Slow dancing with a dramatic romantic dip together with \1"),
    (r"(?i)уютно нежится в постели и ведет интимные разговоры на подушках с (.+)", r"Cuddling in bed sharing intimate pillow talk with \1"),
    (r"(?i)чувственно кормит сладкой клубникой в шоколаде с рук (.+)", r"Sensually hand-feeding chocolate-dipped strawberries to \1"),
    (r"(?i)отправляется на романтическое свидание из «уголка купидона» вместе с (.+?)(?:!|$)", r"Going on a romantic Cupid's Corner date together with \1!"),
    (r"(?i)проходит сеанс семейной психотерапии для пар вместе с (.+)", r"Attending a couples relationship counseling session together with \1"),
    (r"(?i)романтично целуется на смотровой площадке сьюдад-энаморады с (.+)", r"Sharing a romantic kiss at Ciudad Enamorada scenic overlook with \1"),
    # EP17 Life & Death (Grim Reaper, Scythe, Funerals, Wills, Coffins, Crypts, Ghosts, Rebirth, Tarot, Ravenwood)
    (r"(?i)занимается потусторонним и пугающе страстным вуху с самим (.+?)(?:!|$)", r"Having otherworldly and hauntingly passionate romance with \1!"),
    (r"(?i)занимается потусторонним и пугающе страстным вуху с самим жнецом смерти!?", "Having otherworldly and hauntingly passionate romance with the Grim Reaper!"),
    (r"(?i)собирает душу сима (.+?) острой косой жнеца смерти", r"Reaping the soul of \1 with the Grim Reaper's sharp scythe"),
    (r"(?i)собирает душу усопшего острой косой жнеца смерти", "Reaping the deceased soul with the Grim Reaper's sharp scythe"),
    (r"(?i)отрабатывает эффектные боевые взмахи косой смерти перед (.+)", r"Practicing dramatic combat scythe swings before \1"),
    (r"(?i)отрабатывает эффектные взмахи и мастерство владения косой смерти", "Practicing dramatic swings and scythe mastery"),
    (r"(?i)бережно полирует лезвие своей могильной косы", "Carefully polishing the blade of the deathly scythe"),
    (r"(?i)калибрует и настраивает сферу душ в департаменте смерти", "Calibrating and tuning the Soul Orb at Netherworld Services"),
    (r"(?i)исследует останки и определяет причину смерти (.+)", r"Examining remains and determining cause of death of \1"),
    (r"(?i)определяет причину смерти и исследует останки усопшего", "Determining cause of death and examining deceased remains"),
    (r"(?i)умоляет жнеца смерти пощадить жизнь (.+)", r"Pleading with the Grim Reaper to spare the life of \1"),
    (r"(?i)умоляет жнеца смерти о пощаде", "Pleading with the Grim Reaper for mercy"),
    (r"(?i)произносит трогательную надгробную речь в память о (.+)", r"Delivering a heartfelt eulogy in memory of \1"),
    (r"(?i)произносит трогательную надгробную речь на похоронах", "Delivering a touching eulogy at the funeral service"),
    (r"(?i)горько скорбит и оплакивает утрату у могилы (.+)", r"Deeply mourning and weeping at \1's grave"),
    (r"(?i)скорбит и оплакивает утрату близкого у надгробия", "Mourning and weeping over the loss of a loved one at the headstone"),
    (r"(?i)зажигает поминальную свечу в память об усопшем", "Lighting a memorial candle in remembrance of the deceased"),
    (r"(?i)бережно подготавливает тело (.+?) к церемонии прощания", r"Gently preparing \1's body for the memorial ceremony"),
    (r"(?i)подготавливает тело усопшего к церемонии прощания и укладывает в гроб", "Preparing the deceased's body for memorial ceremony and placing into casket"),
    (r"(?i)присутствует на церемонии прощания и похоронах (.+)", r"Attending the memorial and funeral service of \1"),
    (r"(?i)присутствует на церемонии похорон и поминальной службе", "Attending the funeral ceremony and memorial service"),
    (r"(?i)внимательно слушает официальное оглашение завещания", "Attentively listening to the official reading of the will"),
    (r"(?i)завещает свое ценное имущество и сбережения (.+)", r"Bequeathing valuable estate and savings to \1"),
    (r"(?i)распределяет ценное имущество и сбережения в завещании", "Distributing valuable estate and savings in the drafted will"),
    (r"(?i)составляет официальное завещание, распределяя наследство и реликвии", "Drafting an official will, distributing inheritance and family heirlooms"),
    (r"(?i)занимается готическим и волнующим вуху прямо внутри гроба вместе с (.+?)(?:!|$)", r"Having gothic and thrilling romance right inside the coffin together with \1!"),
    (r"(?i)занимается готическим вуху прямо внутри гроба", "Having thrilling gothic romance right inside the coffin"),
    (r"(?i)спит в мягко обитом роскошном гробу", "Sleeping comfortably inside a luxurious cushioned coffin"),
    (r"(?i)отдыхает внутри старинного гроба", "Resting inside an ornate antique coffin"),
    (r"(?i)исследует темные глубины старинного склепа и катакомб", "Exploring the eerie dark depths of ancient crypt and catacombs"),
    (r"(?i)высекает трогательную эпитафию на надгробном камне для (.+)", r"Inscribing a heartfelt epitaph onto the headstone for \1"),
    (r"(?i)высекает трогательную эпитафию на надгробном камне", "Inscribing a touching epitaph onto the cemetery headstone"),
    (r"(?i)оставляет свежие цветы и памятное подношение у могилы (.+)", r"Leaving fresh flowers and a memorial offering at \1's grave"),
    (r"(?i)оставляет подношение у могилы усопшего", "Leaving a memorial offering and flowers at the grave"),
    (r"(?i)временно вселяется в тело (.+?), подчиняя его своей призрачной воле!?", r"Temporarily possessing \1's body, bending them to ghostly will!"),
    (r"(?i)временно вселяется в чужое тело, подчиняя сима своей воле", "Temporarily possessing a living Sim's body, bending them to ghostly will"),
    (r"(?i)вселяется в предмет, заставляя его левитировать и дрожать от эктоплазмы", "Possessing an object, making it levitate and tremble with эктоплазмы" if False else "Possessing an object, making it levitate and tremble with ectoplasm"),
    (r"(?i)пугает леденящим кровь призрачным полтергейстом сима (.+?)(?:!|$)", r"Terrorizing \1 with a spine-chilling ghostly poltergeist!"),
    (r"(?i)устраивает шалости полтергейста, поднимая предметы в воздух и пугая окружающих", "Pulling poltergeist antics, floating objects in mid-air and spooking everyone"),
    (r"(?i)оставляет липкий след мерцающей эктоплазмы", "Leaving a slimy trail of glowing ectoplasm"),
    (r"(?i)издает леденящий душу потусторонний вой", "Letting out a bone-chilling otherworldly wail"),
    (r"(?i)развивает призрачное мастерство и связь с миром теней", "Cultivating ghost mastery and communing with the netherworld"),
    (r"(?i)торжественно вычеркивает выполненную мечту из предсмертного списка", "Triumphantly checking off a fulfilled goal from the bucket list"),
    (r"(?i)записывает свои заветные предсмертные желания в список целей души", "Writing cherished aspirations into the soul's bucket list"),
    (r"(?i)погружается в зловещую топь для духовного перерождения и реинкарнации в новую жизнь!?", "Submerging into the Baleful Bog for spiritual rebirth and reincarnation into a new life!"),
    (r"(?i)тянет персональную карту дня из мистической колоды таро", "Drawing a personal card of the day from the mystic Tarot deck"),
    (r"(?i)делает мистический расклад карт таро для (.+?), предсказывая грядущую судьбу", r"Reading mystical Tarot cards for \1, foretelling their destiny"),
    (r"(?i)делает таинственный расклад карт таро, читая знаки судьбы", "Doing a mystic Tarot spread, deciphering omens of fate"),
    (r"(?i)проводит спиритический сеанс вместе с (.+?), призывая духов", r"Conducting a seance together with \1, summoning ancestral spirits"),
    (r"(?i)проводит таинственный спиритический сеанс, призывая духов предков", "Conducting a mystical seance, summoning ancestral spirits"),
    (r"(?i)прогуливается по туманным улочкам таинственного городка вранбург", "Strolling through the misty streets of mysterious town Ravenwood"),
    # EP18 Businesses & Hobbies (Pottery, Tattoos, Small Business, Mentorship, Sweets, Bicycles, Nordhaven)
    (r"(?i)обучает гончарному делу и формовке глины на круге (.+)", r"Teaching pottery and clay shaping on the wheel to \1"),
    (r"(?i)формует глиняное изделие на вращающемся гончарном круге", "Shaping clay artwork on the spinning pottery wheel"),
    (r"(?i)наносит декоративную цветную глазурь на керамическое изделие", "Applying decorative colored glaze onto ceramic pottery"),
    (r"(?i)обжигает глиняные изделия в раскаленной гончарной печи", "Firing clay ceramics inside the high-temperature pottery kiln"),
    (r"(?i)любуется готовой авторской керамикой ручной работы", "Admiring finished handmade ceramic pottery"),
    (r"(?i)аккуратно набивает авторскую татуировку симу (.+?) на тату-кушетке", r"Carefully tattooing custom body art onto \1 at the tattoo chair"),
    (r"(?i)набивает художественную татуировку клиенту на тату-кушетке", "Tattooing custom body art on client at the tattoo chair"),
    (r"(?i)терпеливо делает татуировку у мастера (.+)", r"Patiently getting tattooed by artist \1"),
    (r"(?i)терпит легкую боль, пока мастер наносит татуировку на кожу", "Enduring mild sting while tattoo artist applies ink to skin"),
    (r"(?i)разрабатывает уникальный авторский эскиз для будущей татуировки", "Designing a unique custom sketch for upcoming tattoo"),
    (r"(?i)тщательно стерилизует тату-машинку и дезинфицирует кушетку", "Sanitizing tattoo machine and disinfecting tattoo chair"),
    (r"(?i)продает входной билет в свое заведение для (.+)", r"Selling admission ticket to venue for \1"),
    (r"(?i)настраивает тарифы и продает входные билеты через автомат", "Setting admission rates and vending tickets at ticket machine"),
    (r"(?i)управляет своим малым бизнесом, проверяя доходы и ассортимент товаров", "Managing small business, tracking profits and inventory"),
    (r"(?i)любезно обслуживает и консультирует покупателя (.+)", r"Courteously assisting and consulting customer \1"),
    (r"(?i)приветливо обслуживает покупателей в своей мастерской", "Warmly assisting shoppers and clients in the workshop"),
    (r"(?i)управляет наемным персоналом и распределяет обязанности в заведении", "Managing hired staff and delegating duties in business"),
    (r"(?i)проводит увлекательный мастер-класс по навыку для (.+)", r"Hosting an engaging skill workshop for \1"),
    (r"(?i)увлеченно читает лекцию и рисует схемы на маркерной доске", "Passionately lecturing and sketching diagrams on whiteboard"),
    (r"(?i)внимательно слушает обучающий мастер-класс наставника (.+)", r"Attentively attending skill masterclass taught by mentor \1"),
    (r"(?i)с интересом слушает обучающую лекцию на мастер-классе", "Attending an educational lecture and workshop with keen interest"),
    (r"(?i)угощает свежей воздушной сахарной ватой (.+)", r"Treating \1 to fluffy fresh cotton candy"),
    (r"(?i)готовит пушистую сладкую сахарную вату на кондитерском аппарате", "Spinning fluffy sweet cotton candy on confectionery machine"),
    (r"(?i)варит ароматные желейные конфеты из спелых свежих плодов", "Crafting artisan fruit jelly gummies from fresh produce"),
    (r"(?i)собирает и кастомизирует стильный городской велосипед из редких деталей", "Assembling and customizing stylish city bike from rare parts"),
    (r"(?i)с удовольствием катается на велосипеде вдоль каналов и набережных", "Leisurely cycling along picturesque canals and promenades"),
    (r"(?i)исследует уютные улочки и творческие мастерские нордхавена", "Exploring quaint streets and artisan workshops of Nordhaven"),

    # EP19 Enchanted Nature / Nature's Magic (Fairies, Flight, Spells, Apothecary, Fairy Rings, Woodland Fauna)
    (r"(?i)осыпает искрящейся волшебной пыльцой (.+?), даря вдохновение и радость", r"Showering \1 in sparkling fairy dust, granting inspiration and joy"),
    (r"(?i)собирает переливающуюся пыльцу с волшебных крыльев для сотворения чар", "Harvesting iridescent fairy dust from wings for spellcasting"),
    (r"(?i)кружит в волшебном парящем полете вокруг (.+)", r"Hovering in a magical fluttering flight around \1"),
    (r"(?i)парит в воздухе на мерцающих полупрозрачных крыльях феи", "Hovering in the air on shimmering translucent fairy wings"),
    (r"(?i)обращается в мерцающий лесной огонек, легко скользя среди крон деревьев", "Transforming into a shimmering woodland wisp, gliding through the canopy"),
    (r"(?i)настраивает форму и магическое свечение своих сказочных крыльев", "Customizing shape and mystical glow of fairy wings"),
    (r"(?i)окутывает озорными чарами и усыпляющей пыльцой (.+)", r"Enveloping \1 in playful charms and slumbering fairy dust"),
    (r"(?i)плетет невинные озорные чары и готовит волшебные шалости", "Weaving innocent playful charms and plotting fairy mischief"),
    (r"(?i)исцеляет силой природной магии любимое растение для (.+)", r"Revitalizing favorite plant with nature magic for \1"),
    (r"(?i)сотворяет заклинание цветения, возвращая к жизни увядшие побеги", "Casting a blooming spell, restoring wilted greenery to life"),
    (r"(?i)взывает к силам стихий, призывая благодатный живительный дождь над садом", "Calling upon elements to summon life-giving rain over the garden"),
    (r"(?i)очищает почву от скверны и вредителей волной зеленой природной энергии", "Cleansing soil of corruption and pests with a wave of nature energy"),
    (r"(?i)оплетает цепкими мягкими корнями и цветущими лозами (.+)", r"Entangling \1 in gentle blooming vines and living roots"),
    (r"(?i)управляет гибкими лесными лозами и древесными побегами", "Manipulating flexible forest vines and living shoots"),
    (r"(?i)прислушивается к сокровенному шепоту древнего древа жизни, внимая тайнам природы", "Listening to the sacred whispers of the ancient Tree of Life"),
    (r"(?i)дистиллирует чистейшие растительные эссенции за аптекарским столом", "Distilling pure botanical essences at the apothecary table"),
    (r"(?i)преподносит бодрящий травяной отвар из лесных сборов для (.+)", r"Presenting a revitalizing herbal tonic made of forest herbs to \1"),
    (r"(?i)варит целебный травяной эликсир из свежесобранных лесных сборов", "Brewing a medicinal herbal elixir from freshly gathered forest herbs"),
    (r"(?i)зачаровывает редкие семена и грибы, наполняя их силой природной магии", "Enchanting rare seeds and fungi with the essence of nature magic"),
    (r"(?i)отыскивает редкие светящиеся травы и волшебные коренья в лесной чаще", "Searching for rare bioluminescent herbs and mystical roots in the dense woods"),
    (r"(?i)кружится в мистическом хороводе в круге фей вместе с (.+)", r"Dancing in a mystical fairy circle hand-in-hand with \1"),
    (r"(?i)танцует и медитирует внутри загадочного круга светящихся грибов", "Dancing and meditating inside the mystical ring of glowing mushrooms"),
    (r"(?i)возлагает дары из лесных ягод и цветов на алтарь древних духов природы", "Placing offerings of berries and flowers onto the shrine of ancient nature spirits"),
    (r"(?i)впитывает благословение матери-природы, ощущая прилив гармонии и жизненных сил", "Embracing the blessing of Mother Nature, feeling harmony and surge of vitality"),
    (r"(?i)шагает сквозь зачарованное дупло древнего древа, перемещаясь в волшебную рощу", "Stepping through the enchanted hollow of an ancient tree into a fairy grove"),
    (r"(?i)пересвистывается и напевает трели на языке лесных птиц, наладив чуткий контакт", "Whistling and trilling in bird language, bonding with woodland songbirds"),
    (r"(?i)вместе с (.+?) ласково гладит ручного лесного олененка", r"Affectionately petting gentle forest fawn together with \1"),
    (r"(?i)заботливо угощает орешками и гладит пушистых лесных обитателей", "Tending to and feeding crunchy nuts to gentle woodland critters"),
    (r"(?i)с благодарностью принимает редкий лесной дар от дружелюбных зверят", "Gratefully accepting a rare forest gift from friendly woodland critters"),

    # GP06 Jungle Adventure (Selvadorada, Omiscan Temple, Archeology, Traps, Relics, Skeletons, Waterfalls, Camping)
    (r"(?i)занимается страстным и романтическим вуху под бурлящими струями водопада с (.+)", r"Having passionate romantic WooHoo under rushing waterfall cascades with \1"),
    (r"(?i)предается романтической страсти под струями тропического водопада", "Indulging in romantic passion under tropical waterfall cascades"),
    (r"(?i)нежно и страстно целует под струями водопада (.+)", r"Gently and passionately kissing under waterfall cascades \1"),
    (r"(?i)с упоением целуется под шумящим тропическим водопадом", "Kissing passionately under rushing tropical waterfall"),
    (r"(?i)прорубает тропу через густые лианы джунглей для (.+)", r"Clearing a trail through thick jungle vines for \1"),
    (r"(?i)прорубает дорогу сквозь непроходимые заросли джунглей с помощью мачете", "Clearing a path through impenetrable jungle thickets with a machete"),
    (r"(?i)купается и плещется под тропическим водопадом вместе с (.+)", r"Splashing and bathing under tropical waterfall together with \1"),
    (r"(?i)освежается и смывает дорожную пыль под бурными струями водопада", "Refreshing and washing off travel dust under rushing waterfall cascades"),
    (r"(?i)отбивается от хищных плотоядных лиан, используя специальную приманку", "Fending off carnivorous vines using specialized bait"),
    (r"(?i)отпугивает рой свирепых плазматических летучих мышей защитным спреем", "Scaring off swarm of vicious plasma bats with protective spray"),
    (r"(?i)распыляет защитный спрей от ядовитых пауков джунглей", "Spraying protective repellent against poisonous jungle spiders"),
    (r"(?i)спасается от разрядов электрических светлячков с помощью порошка гузмании", "Shielding from electric fireflies discharges with Guzmania powder"),
    (r"(?i)отбивается от роя хищных насекомых и распыляет защитный спрей в джунглях", "Fending off hostile jungle insects and spraying protective repellent"),
    (r"(?i)мерно покачивается и сладко дремлет в подвесном походном гамаке среди деревьев", "Gently swaying and peacefully napping in hanging travel hammock amongst trees"),
    (r"(?i)отдыхает в полевом экспедиционном лагере посреди диких джунглей", "Resting at expedition campsite in the heart of dense wilderness"),
    (r"(?i)залпом выпивает спасительное сельвадорадское противоядие от смертоносного яда", "Downing saving Selvadoradian antidote against deadly poison"),
    (r"(?i)умоляет продать или дать спасительное противоядие от храмового яда у (.+)", r"Begging \1 for saving temple antidote against deadly poison"),
    (r"(?i)срочно ищет и выменивает спасительный антидот от древнего яда", "Urgently seeking and trading for saving antidote against ancient poison"),
    (r"(?i)внимательно изучает древние механизмы и пытается обезвредить ловушку храма", "Carefully inspecting ancient mechanisms and disarming temple trap"),
    (r"(?i)разгадывает храмовую загадку и распахивает тайные каменные врата святилища", "Solving temple puzzle and opening massive ancient stone gate"),
    (r"(?i)делит легендарные древние сокровища храма вместе с (.+)", r"Sharing legendary ancient temple treasures with \1"),
    (r"(?i)с благоговением отпирает древний сундук с бесценными сокровищами цивилизации омиска", "Reverently unlocking ancient chest filled with treasures of Omiscan civilization"),
    (r"(?i)совершает искреннее пожертвование статуе мадре косеки, моля о благословении", "Making a sincere offering to Madre Cosecha statue, praying for blessing"),
    (r"(?i)ощущает воздействие мистического храмового проклятия, окутавшего тело", "Feeling the lingering effect of mystical temple curse enveloping the body"),
    (r"(?i)размечает колышками и организует новый перспективный участок для совместных раскопок", "Setting boundary stakes and establishing a promising new group excavation site"),
    (r"(?i)изучает и устанавливает подлинность редкого древнего артефакта за археологическим столом", "Examining and authenticating a rare ancient artifact at archaeology table"),
    (r"(?i)вместе с (.+?) раскапывает древний археологический курган", r"Excavating an ancient archaeological dig mound together with \1"),
    (r"(?i)бережно проводит археологические раскопки, просеивая древний грунт кисточкой", "Painstakingly conducting archaeological excavation, brushing ancient soil"),
    (r"(?i)кропотливо реставрирует и склеивает фрагменты древней омисканской реликвии", "Painstakingly restoring and piecing together fragments of ancient Omiscan relic"),
    (r"(?i)тщательно растирает древнюю омисканскую костяную пыль для алхимии и реликвий", "Carefully grinding ancient Omiscan bone dust for alchemy and relics"),
    (r"(?i)соединяет основу реликвии с очищенным кристаллом, активируя древнюю магию", "Combining relic base with refined crystal, awakening ancient magic"),
    (r"(?i)призывает гремящего костями скелета-помощника для ведения хозяйства", "Summoning clattering skeletal assistant to help with household chores"),
    (r"(?i)щеголяет в обличье живого омисканского скелета, задорно постукивая ребрами", "Strutting around in the form of a living Omiscan skeleton, rattling ribs"),
    (r"(?i)зловеще гремит костями и пугает омисканским черепом (.+)", r"Ominously rattling bones and scaring \1 with Omiscan skull"),
    (r"(?i)задорно гремит костями и пугает прохожих своим скелетным видом", "Playfully rattling bones and spooking bystanders with skeletal appearance"),
    (r"(?i)задорно шутит о костях и гремит суставами перед (.+)", r"Playfully joking about bones and rattling joints before \1"),
    (r"(?i)общается и весело шутит с ожившим храмовым скелетом", "Chatting and playfully joking with a living temple skeleton"),
    (r"(?i)кружится в ритмичном и страстном танце румбасим в паре с (.+)", r"Dancing in rhythmic and passionate Rumbasim dance together with \1"),
    (r"(?i)страстно отплясывает зажигательный сельвадорадский танец румбасим", "Passionately dancing the fiery Selvadoradian Rumbasim dance"),
    (r"(?i)вдохновенно играет страстную сельвадорадскую народную серенаду на гитаре для (.+)", r"Passionately playing Selvadoradian folk serenade on guitar for \1"),
    (r"(?i)виртуозно наигрывает колоритные латиноамериканские мотивы на гитаре", "Masterfully strumming vibrant Latin American folk tunes on guitar"),
    (r"(?i)радушно приветствует традиционным сельвадорадским жестом (.+)", r"Warmly greeting \1 with a traditional Selvadoradian gesture"),
    (r"(?i)обменивается колоритным сельвадорадским приветствием", "Exchanging traditional colorful Selvadoradian greeting"),
    (r"(?i)придирчиво выбирает мачете и походное снаряжение у местных торговцев", "Haggling and purchasing expedition gear from local open-air vendors"),
    (r"(?i)с аппетитом пробует пикантные традиционные блюда сельвадорадской кухни", "Savory tasting spicy traditional dishes of Selvadoradian cuisine"),

    # EP20 Through the Ages (Time Machine, Eras, Chivalry, Antiquities, Courtly Etiquette, Chrono-Gadgets)
    (r"(?i)калибрует темпоральный континуум и настраивает хроно-координаты машины времени", "Calibrating temporal continuum and dialing chrono-coordinates on time machine"),
    (r"(?i)совершает захватывающий темпоральный прыжок сквозь века вместе с (.+)", r"Embarking on a thrilling temporal leap through the ages with \1"),
    (r"(?i)шагает в сияющий темпоральный портал, отправляясь в путешествие сквозь века", "Stepping into glowing temporal portal, traveling through the ages"),
    (r"(?i)устраняет опасный временной парадокс, восстанавливая естественный ход истории", "Resolving perilous temporal paradox, restoring natural flow of history"),
    (r"(?i)возвращается из путешествия во времени с подлинными артефактами ушедших веков", "Returning from time journey with genuine artifacts of bygone eras"),
    (r"(?i)скрещивает клинки в благородном рыцарском поединке против (.+)", r"Crossing blades in a noble knightly duel against \1"),
    (r"(?i)отрабатывает искусные фехтовальные приемы с историческим мечом", "Practicing skillful fencing techniques with historical sword"),
    (r"(?i)торжественно посвящает в рыцари и возлагает меч на плечо (.+)", r"Solemnly dubbing \1 into knighthood and laying sword upon shoulder"),
    (r"(?i)принимает посвящение в рыцари, преклонив колено", "Receiving knighthood investiture upon bended knee"),
    (r"(?i)метко пускает оперенную стрелу в мишень из старинного изогнутого лука", "Accurately loosing feathered arrow at target from vintage curved bow"),
    (r"(?i)примеряет и начищает до блеска массивные стальные рыцарские латы", "Fitting and polishing heavy steel knightly plate armor to a shine"),
    (r"(?i)пишет подробную историческую летопись династии гусиным пером за старинным бюро", "Writing detailed dynasty chronicles with quill feather pen at antique bureau"),
    (r"(?i)изучает древнее генеалогическое древо и благородные корни рода вместе с (.+)", r"Tracing ancient genealogical tree and noble lineage together with \1"),
    (r"(?i)кропотливо изучает родословное древо предков, раскрывая семейные тайны веков", "Painstakingly studying ancestral family tree, uncovering secrets of centuries"),
    (r"(?i)бережно реставрирует старинный антиквариат и шестеренки винтажной астролябии", "Delicately restoring antique relics and clockwork cogs of vintage astrolabe"),
    (r"(?i)просматривает голографические хроники грядущих столетий в квантовом архиве", "Reviewing holographic chronicles of upcoming centuries in quantum archives"),
    (r"(?i)кружится в грациозном старинном менуэте на балу в паре с (.+)", r"Twirling in graceful vintage courtly minuet at the ball with \1"),
    (r"(?i)исполняет величавые па старинного придворного менуэта", "Performing majestic steps of vintage courtly minuet"),
    (r"(?i)отвешивает галантный благородный поклон перед (.+)", r"Offering a gallant noble bow before \1"),
    (r"(?i)отрабатывает безупречный придворный реверанс по всем правилам этикета", "Practicing flawless courtly curtsy according to all rules of etiquette"),
    (r"(?i)наслаждается изысканной викторианской чайной церемонией в компании (.+)", r"Enjoying exquisite Victorian tea ceremony in the company of \1"),
    (r"(?i)неспешно вкушает ароматный чай из старинного фарфорового сервиза", "Leisurely savoring aromatic tea poured from vintage porcelain teapot"),
    (r"(?i)настраивает пространственные сенсоры на голографическом дисплее хроноскопа", "Calibrating spatial sensors on holographic display of chronoscope"),
    (r"(?i)заряжает концентрированной энергией хроно-кристаллы темпорального двигателя", "Charging chronocrystals of temporal engine with concentrated energy"),
    (r"(?i)синтезирует старинное средневековое угощение в молекулярном пищевом репликаторе", "Synthesizing vintage medieval delicacy in molecular food replicator"),

    # GP01 Outdoor Retreat (Camping, Granite Falls, Campfire, Herbalism, Insects, Horseshoes, Hermit, Bear)
    (r"(?i)угощает поджаренным над костром зефиром (.+)", r"Treating \1 to golden marshmallows roasted over campfire"),
    (r"(?i)жарит аппетитный зефир на палочке над искрами костра", "Roasting sweet marshmallows on a stick over campfire sparks"),
    (r"(?i)жарит сосиски на палочке над походным костром", "Roasting hot dogs on a stick over the campfire"),
    (r"(?i)жарит свежепойманную рыбу на костре", "Roasting freshly caught fish over open campfire flames"),
    (r"(?i)с упоением травит леденящие кровь страшилки у костра для (.+)", r"Thrillingly telling spine-chilling ghost stories around campfire to \1"),
    (r"(?i)с упоением рассказывает леденящие кровь страшилки у костра", "Thrillingly telling spine-chilling ghost stories around the campfire"),
    (r"(?i)душевно поет походные песни у пылающего костра вместе с (.+)", r"Heartily singing campfire songs around blazing fire with \1"),
    (r"(?i)душевно напевает любимые походные песни у костра", "Heartily humming beloved campfire songs by the fire"),
    (r"(?i)уютно греется у пылающего походного костра", "Cozying up and warming hands by blazing campfire"),
    (r"(?i)азартно соревнуется в метании подков против (.+)", r"Competitively playing horseshoes game against \1"),
    (r"(?i)играет в метание подков, стараясь попасть в колышек", "Playing horseshoes, aiming for a ringer on the stake"),
    (r"(?i)лежит на мягкой траве, любуясь плывущими облаками вместе с (.+)", r"Cloudgazing while lying on soft grass together with \1"),
    (r"(?i)лежит на траве и мечтательно разглядывает облака в небе", "Cloudgazing daydreaming while relaxing on the grass"),
    (r"(?i)беззаботно играет и веселится в палатке вместе с (.+)", r"Playfully hanging out and laughing inside tent with \1"),
    (r"(?i)уютно отдыхает в просторной туристической палатке", "Resting cozily inside spacious camping tent"),
    (r"(?i)осторожно ловит редких насекомых и светлячков в банку", "Carefully catching rare insects and fireflies in a glass jar"),
    (r"(?i)рассматривает пойманных жуков и светлячков в походном садке", "Observing collected beetles and fireflies in a camp terrarium"),
    (r"(?i)растирает дикие травы, распознавая их целебные свойства", "Rubbing wild leaves and identifying herbal properties"),
    (r"(?i)наносит защитную травяную мазь от лесных насекомых для (.+)", r"Applying protective herbal bug ointment onto \1"),
    (r"(?i)варит успокаивающий травяной отвар от укусов насекомых", "Brewing soothing herbal remedy against insect bites"),
    (r"(?i)внезапно выпрыгивает в костюме медведя и пугает (.+)", r"Leaping out in wild bear costume startling \1"),
    (r"(?i)наряжается в костюм дикого медведя и рычит из кустов", "Dressing up in wild bear costume and growling from bushes"),
    (r"(?i)узнает тайный рецепт травяного снадобья у отшельника (.+)", r"Learning secret herbal remedy recipe from hermit \1"),
    (r"(?i)беседует по душам с мудрым лесным отшельником в глуши", "Having a deep heart-to-heart with the wise forest hermit"),

    # GP02 Spa Day (Wellness, Yoga, Meditation, Massage, Mud Bath, Sauna, Manicure, Facial Mask)
    (r"(?i)занимается страстным вуху в горячей и распаренной сауне с (.+)", r"Having passionate WooHoo in the steaming hot sauna with \1"),
    (r"(?i)предается страсти в распаренной горячей сауне", "Enjoying passionate intimacy in the steamy hot sauna"),
    (r"(?i)плещет воду на раскаленные камни в сауне, окутываясь клубами густого пара", "Splashing water onto hot sauna stones, filling the room with billowing steam"),
    (r"(?i)парится в горячей кедровой сауне, глубоко прогревая тело", "Relaxing in hot cedar sauna, warming up in deep steam"),
    (r"(?i)делает расслабляющий классический шведский массаж для (.+)", r"Giving relaxing classic Swedish massage to \1"),
    (r"(?i)делает классический расслабляющий шведский массаж на массажном столе", "Giving classic relaxing Swedish massage on massage table"),
    (r"(?i)наслаждается расслабляющим шведским массажем от (.+)", r"Enjoying relaxing Swedish massage from \1"),
    (r"(?i)расслабляется во время классического шведского массажа", "Relaxing during classic Swedish massage"),
    (r"(?i)делает глубокий массаж мышечных тканей для (.+)", r"Giving deep tissue muscle massage to \1"),
    (r"(?i)массирует глубокие слои мышц, снимая мышечные зажимы", "Massaging deep muscle tissue, releasing muscle tension"),
    (r"(?i)получает глубокий массаж мышечных тканей от (.+)", r"Receiving deep tissue muscle massage from \1"),
    (r"(?i)ощущает облегчение от глубокого массажа зажатых мышц", "Feeling great relief from deep tissue massage"),
    (r"(?i)делает целебный массаж горячими базальтовыми камнями для (.+)", r"Giving healing hot basalt stone massage to \1"),
    (r"(?i)раскладывает горячие базальтовые камни вдоль позвоночника", "Placing hot basalt stones along the spine"),
    (r"(?i)наслаждается прогревающим массажем горячими камнями от (.+)", r"Enjoying soothing hot stone massage from \1"),
    (r"(?i)ощущает приятное тепло массажа горячими базальтовыми камнями", "Feeling soothing warmth of hot basalt stone massage"),
    (r"(?i)делает ароматный сеанс ароматерапевтического массажа с маслами для (.+)", r"Giving fragrant aromatherapy massage with essential oils to \1"),
    (r"(?i)делает ароматерапевтический массаж с эфирными маслами", "Giving aromatherapy massage with essential oils"),
    (r"(?i)вдыхает благовония во время сеанса ароматерапевтического массажа от (.+)", r"Inhaling soothing fragrances during aromatherapy massage from \1"),
    (r"(?i)наслаждается ароматерапевтическим массажем с целебными маслами", "Enjoying aromatherapy massage with healing oils"),
    (r"(?i)разминает натруженные мышцы спортивным массажем для (.+)", r"Loosening strained muscles with sports massage for \1"),
    (r"(?i)проводит спортивный массаж для восстановления тонуса", "Performing sports massage for muscular recovery"),
    (r"(?i)восстанавливает тонус мышц благодаря спортивному массажу от (.+)", r"Rejuvenating muscles thanks to sports massage from \1"),
    (r"(?i)восстанавливает мышцы во время спортивного массажа", "Restoring muscle tone during sports massage session"),
    (r"(?i)делает особый массаж для повышения фертильности для (.+)", r"Giving special fertility massage to \1"),
    (r"(?i)делает гармонизирующий массаж для повышения фертильности", "Giving harmonizing fertility massage"),
    (r"(?i)принимает целебный массаж для повышения фертильности от (.+)", r"Receiving special fertility massage from \1"),
    (r"(?i)принимает гармонизирующий массаж для зачатия", "Receiving harmonizing massage for fertility"),
    (r"(?i)делает восстанавливающий массаж стоп в спа-кресле для (.+)", r"Giving rejuvenating foot massage in spa chair to \1"),
    (r"(?i)массирует уставшие стопы клиента в спа-кресле", "Massaging tired client feet in the spa chair"),
    (r"(?i)блаженствует в кресле, пока (.+) массирует стопы", r"Blissfully resting in chair while \1 massages feet"),
    (r"(?i)блаженно расслабляется в кресле во время массажа стоп", "Blissfully relaxing in chair during foot massage"),
    (r"(?i)разминает кисти и пальцы рук в массажном кресле для (.+)", r"Massaging hands and fingers in massage chair for \1"),
    (r"(?i)делает деликатный массаж кистей рук в массажном кресле", "Giving delicate hand massage in massage chair"),
    (r"(?i)наслаждается расслабляющим массажем кистей рук от (.+)", r"Enjoying relaxing hand massage from \1"),
    (r"(?i)ощущает легкость во время массажа кистей рук", "Feeling hand tension melt away during hand massage"),
    (r"(?i)бережно массирует уставшие плечи и спину (.+) на массажном столе", r"Gently massaging tired shoulders and back of \1 on massage table"),
    (r"(?i)проводит профессиональный сеанс массажа на столе", "Conducting professional massage session on table"),
    (r"(?i)безмятежно лежит на массажном столе, получая заботливый массаж от (.+)", r"Serenely resting on massage table while receiving massage from \1"),
    (r"(?i)безмятежно отдыхает на массажном столе во время сеанса", "Serenely relaxing on massage table during session"),
    (r"(?i)проводит групповое занятие по йоге для (.+)", r"Leading group yoga class for \1"),
    (r"(?i)проводит вдохновляющее групповое занятие по йоге на коврике инструктора", "Leading inspiring group yoga class on instructor mat"),
    (r"(?i)посещает занятие йогой под руководством (.+)", r"Attending yoga class instructed by \1"),
    (r"(?i)посещает занятие йогой в группе единомышленников", "Attending group yoga class with fellow practitioners"),
    (r"(?i)выполняет асану «собака мордой вниз», вытягивая позвоночник", "Practicing downward-facing dog pose, lengthening spine"),
    (r"(?i)балансирует в позе дерева на коврике для йоги", "Balancing steadily in tree pose on yoga mat"),
    (r"(?i)выполняет гармоничный комплекс «приветствие солнца» на рассвете", "Performing harmonious Sun Salutation yoga sequence at dawn"),
    (r"(?i)стоит в уверенной позе воина, укрепляя дух и тело", "Holding confident warrior pose, strengthening body and mind"),
    (r"(?i)выгибается в позе моста, раскрывая грудную клетку", "Arching into bridge pose, opening chest"),
    (r"(?i)тянется в позе треугольника, балансируя на коврике", "Stretching into triangle pose, balancing on mat"),
    (r"(?i)занимается специальной практикой йоги для концентрации ума и прилива энергии", "Practicing specialized yoga flow for mental focus and energy boost"),
    (r"(?i)занимается йогой на коврике, растягивая мышцы и обретая гибкость", "Practicing yoga on the mat, stretching muscles and gaining flexibility"),
    (r"(?i)мгновенно телепортируется силой глубокой медитации и дзена", "Instantly teleporting through focused meditative power and zen"),
    (r"(?i)погружается в глубокий транс и безмятежно левитирует в воздухе", "Drifting into deep meditative trance and levitating serenely in midair"),
    (r"(?i)медитирует на табурете для медитации, очищая разум от лишних мыслей", "Meditating on meditation stool, clearing mind of thoughts"),
    (r"(?i)медитирует, очищая разум от лишних мыслей и обретая внутренний покой", "Meditating, clearing mind of thoughts and finding inner peace"),
    (r"(?i)бережно наносит питательную спа-маску на лицо (.+)", r"Gently applying nourishing spa face mask onto \1's face"),
    (r"(?i)наносит освежающую косметическую маску на лицо для ухода за кожей", "Applying refreshing cosmetic face mask for skin care"),
    (r"(?i)ходит с питательной косметической маской на лице, ухаживая за кожей", "Wearing nourishing cosmetic face mask, caring for skin"),
    (r"(?i)делает стильный маникюр и наносит лак на ногти (.+)", r"Giving stylish manicure and painting nails for \1"),
    (r"(?i)аккуратно наносит модный лак и рисует дизайн на ногтях", "Neatly applying trendy nail polish and painting nail art"),
    (r"(?i)с интересом наблюдает, как (.+) делает великолепный маникюр", r"Watching attentively as \1 creates gorgeous manicure"),
    (r"(?i)сидит в спа-кресле, получая красивый и аккуратный маникюр", "Sitting in spa chair, receiving beautiful neat manicure"),
    (r"(?i)делает спа-педикюр и ухаживает за ноготками (.+)", r"Giving spa pedicure and toe nail care to \1"),
    (r"(?i)делает профессиональный спа-педикюр в кресле", "Giving professional spa pedicure in the chair"),
    (r"(?i)отдыхает в кресле, пока (.+) делает педикюр", r"Relaxing in chair while \1 gives pedicure"),
    (r"(?i)принимает освежающую процедуру спа-педикюра", "Receiving refreshing spa pedicure treatment"),
    (r"(?i)погружается в теплую целебную грязевую ванну, снимая накопившийся стресс", "Soaking in warm therapeutic mud bath, melting away stress"),
    (r"(?i)принимает роскошную расслабляющую ванну с ароматными маслами и солями", "Indulging in luxurious relaxing bath with aromatic oils and salts"),
    (r"(?i)пьет освежающую огуречную воду со льдом из спа-подноса", "Sipping refreshing ice-cold cucumber infused water from spa tray"),
    (r"(?i)практикует техники здорового образа жизни, стремясь к внутреннему покою", "Practicing wellness techniques, seeking inner balance and peace"),

    # GP03 Dine Out (Restaurant Dining, Host, Waiter, Chef Station, Experimental Food, Management)
    (r"(?i)неловко спотыкается и с оглушительным грохотом роняет поднос с посудой", "Clumsily tripping and dropping the dish tray with a loud crash"),
    (r"(?i)приветствует посетителей и с улыбкой провожает за столик (.+)", r"Greeting guests and smilingly escorting \1 to their table"),
    (r"(?i)встречает гостей у входа и распределяет столики в зале", "Greeting arriving guests and seating diners in dining room"),
    (r"(?i)ловко подает горячие ресторанные блюда на подносе для (.+)", r"Skillfully serving hot restaurant dishes on a tray to \1"),
    (r"(?i)несет поднос с аппетитными горячими блюдами к столику", "Carrying tray of mouthwatering hot dishes to the table"),
    (r"(?i)внимательно записывает заказ блюд и пожелания гостей со столика (.+)", r"Attentively noting down dining orders and requests from \1's table"),
    (r"(?i)принимает подробный заказ блюд и напитков у гостей", "Taking detailed food and drink orders from dining guests"),
    (r"(?i)быстро и аккуратно убирает использованную посуду со столика", "Promptly bussing and clearing used dishes from the table"),
    (r"(?i)виртуозно готовит изысканное ресторанное блюдо на профессиональной плите", "Masterfully cooking gourmet restaurant dish at chef station"),
    (r"(?i)тщательно декорирует и доводит до совершенства подачу блюда высокой кухни", "Meticulously garnishing and plating haute cuisine dish to perfection"),
    (r"(?i)внимательно дегустирует блюдо и строчит заметки для ресторанного гида", "Critically tasting the dish and taking notes for restaurant guide"),
    (r"(?i)преподносит изысканный десерт за счет заведения в знак извинения для (.+)", r"Offering complimentary dessert on the house as apology to \1"),
    (r"(?i)угощает гостей комплиментом от шеф-повара за счет заведения", "Treating diners to complimentary chef special on the house"),
    (r"(?i)лично подходит к столику (.+), интересуясь впечатлениями от ужина", r"Personally approaching table of \1 inquiring about dining experience"),
    (r"(?i)обходит обеденный зал, справляясь о комфорте гостей ресторана", "Checking on dining room tables to ensure guest satisfaction"),
    (r"(?i)хвалит и премирует за безупречную работу (.+)", r"Praising and rewarding \1 for impeccable restaurant service"),
    (r"(?i)выражает благодарность персоналу за отличную смену в ресторане", "Expressing gratitude to staff for excellent restaurant shift"),
    (r"(?i)делает строгий выговор за ошибки в обслуживании (.+)", r"Reprimanding \1 for service mistakes and delays"),
    (r"(?i)отчитывает персонал за недочеты и медлительность на смене", "Reprimanding staff for service flaws and slowness on shift"),
    (r"(?i)просит администратора (.+) посадить за свободный столик", r"Asking host \1 to be seated at an available table"),
    (r"(?i)ожидает у стойки администратора приглашения за столик", "Waiting at the host station to be seated"),
    (r"(?i)терпеливо ожидает, пока администратор ресторана подготовит столик", "Patiently waiting while restaurant host prepares table"),
    (r"(?i)заказывает изысканные блюда на весь столик для (.+)", r"Ordering gourmet dining dishes for the whole table for \1"),
    (r"(?i)заказывает разнообразные блюда и напитки на всю компанию за столом", "Ordering varied dishes and drinks for the entire party"),
    (r"(?i)делает заказ изысканных блюд и напитков у официанта (.+)", r"Ordering exquisite meals and drinks from waiter \1"),
    (r"(?i)изучает меню и делает заказ официанту ресторана", "Reviewing the menu and placing order with the waiter"),
    (r"(?i)приятно проводит время в ожидании подачи блюд в компании (.+)", r"Pleasantly chatting while waiting for food with \1"),
    (r"(?i)ожидает подачу свежеприготовленных ресторанных блюд", "Waiting for freshly prepared restaurant dishes to be served"),
    (r"(?i)поднимает бокал и произносит праздничный тост за (.+)", r"Raising glass and making celebratory toast to \1"),
    (r"(?i)торжественно произносит красивый тост за столом ресторана", "Raising glass and delivering elegant toast at dining table"),
    (r"(?i)нежно угощает кусочком изысканного блюда с вилки (.+)", r"Sweetly feeding a bite of gourmet food from fork to \1"),
    (r"(?i)делится кусочком вкусного блюда через столик", "Sharing tasty bite of food across the dining table"),
    (r"(?i)фотографирует подачу экспериментального блюда для симстаграма", "Taking photo of experimental dish presentation for Simstagram"),
    (r"(?i)с восторгом дегустирует шедевр молекулярной экспериментальной кухни", "Enthusiastically savoring masterpiece of molecular experimental gastronomy"),
    (r"(?i)выражает искреннее восхищение кулинарным шедевром шеф-повару (.+)", r"Expressing sincere praise for culinary masterpiece to chef \1"),
    (r"(?i)выражает искренний восторг качеством блюд шеф-повару", "Praising the chef for high quality and culinary excellence"),
    (r"(?i)высказывает претензии по поводу пересоленного или невкусного блюда (.+)", r"Complaining about salty or poor quality dish to \1"),
    (r"(?i)жалуется на качество или температуру поданного блюда", "Complaining about quality or temperature of served dish"),
    (r"(?i)возмущается непозволительно долгим ожиданием заказа перед (.+)", r"Complaining about unacceptable wait time before \1"),
    (r"(?i)возмущается слишком долгой подачей блюд в ресторане", "Frustrated by excessively slow food service at restaurant"),
    (r"(?i)оплачивает ресторанный счет и оставляет щедрые чаевые для (.+)", r"Paying restaurant bill and leaving generous tip for \1"),
    (r"(?i)оплачивает счет за ужин и оставляет хорошие чаевые", "Paying dinner bill and leaving good tip for waiter"),

    # GP04 Vampires (Plasma, Powers, Bat/Mist, Coffins, Sparring, Pipe Organ, Sunlight, Garlic)
    (r"(?i)мучительно шипит и сгорает под смертоносными лучами полуденного солнца", "Painfully sizzling and burning under the deadly rays of noon sun"),
    (r"(?i)метко бросает флакон с лекарством от вампиризма в (.+)", r"Accurately throwing vampire cure flask at \1"),
    (r"(?i)использует древнее лекарство для исцеления от вампиризма", "Using ancient cure to free from the vampiric curse"),
    (r"(?i)готовит редкое абсолютное лекарство от вампиризма за барной стойкой", "Mixing the rare Ultimate Vampire Cure at the bar"),
    (r"(?i)плетет защитную гирлянду из чеснока для защиты дома от кровопийц", "Braiding protective garlic garland to shield home from bloodsuckers"),
    (r"(?i)занимается мистическим и страстным вуху в роскошном гробу с (.+)", r"Having passionate mystical WooHoo in luxurious coffin with \1"),
    (r"(?i)предается страсти в старинном закрытом гробу", "Indulging in dark passion inside an antique closed coffin"),
    (r"(?i)дарует темный дар вечной жизни и обращает в вампира (.+)", r"Granting the dark gift of eternity and turning \1 into a vampire"),
    (r"(?i)совершает таинство обращения смертного в вампира", "Performing dark sacrament of turning a mortal into a vampire"),
    (r"(?i)на коленях умоляет (.+) обратить в вампира и даровать бессмертие", r"Begging \1 on bended knees to turn them into an immortal vampire"),
    (r"(?i)умоляет древнего вампира об обращении в дитя ночи", "Pleading with ancient vampire for the dark gift of the night"),
    (r"(?i)бесшумно крадется во тьме и жадно пьет теплую кровь спящего персонажа (.+)", r"Silently creeping in shadows and feeding on warm blood of sleeping \1"),
    (r"(?i)утоляет мучительную жажду кровью беззащитно спящего сима", "Quenching agonizing thirst with blood of defenceless sleeping sim"),
    (r"(?i)подчиняет волю и жадно выпивает кровь до последней капли у (.+)", r"Compelling will and deeply draining blood to the last drop from \1"),
    (r"(?i)жадно испивает теплую кровь жертвы, утоляя дикий голод", "Ravishingly drinking victim's warm blood, feeding ferocious hunger"),
    (r"(?i)вежливо просит разрешения испить немного теплой крови у (.+)", r"Politely asking permission to drink warm blood from \1"),
    (r"(?i)аккуратно пьет теплую кровь с согласия донора", "Gently drinking warm blood with consent of donor"),
    (r"(?i)пьет донорскую кровь из медицинского пакета, спасаясь от жажды", "Drinking donor blood from a medical pack to stave off thirst"),
    (r"(?i)ест спелый кровавый плод, насыщаясь растительной кровью", "Eating ripe plasma fruit, nourishing on plant blood"),
    (r"(?i)потягивает темный густой коктейль с кровью из хрустального бокала", "Sipping dark rich blood cocktail from crystal glass"),
    (r"(?i)оборачивается летучей мышью и бесшумно рассекает ночной воздух", "Transforming into a bat and swooping silently through night sky"),
    (r"(?i)растворяется в клубах черного тумана и мгновенно переносится в пространстве", "Dissolving into dark mist and teleporting through space"),
    (r"(?i)стремительно несется вперед на сверхъестественной вампирической скорости", "Dashing forward at supernatural vampiric super-speed"),
    (r"(?i)пристально смотрит в глаза и погружает в глубокий гипнотический транс (.+)", r"Staring deeply into eyes and hypnotizing \1 into trance"),
    (r"(?i)погружает смертного в подчиняющий гипнотический транс", "Plunging mortal into commanding hypnotic trance"),
    (r"(?i)внушает чужие мысли и полностью берет под ментальный контроль (.+)", r"Commanding thoughts and taking total mental control of \1"),
    (r"(?i)подчиняет разум смертного своей непреклонной воле", "Bending mortal mind to their unbreakable vampiric will"),
    (r"(?i)вампирической силой искажает и подчиняет эмоциональное состояние (.+)", r"Using vampiric power to alter and control emotional state of \1"),
    (r"(?i)манипулирует аурой и внушает сильные темные эмоции", "Manipulating aura and inducing strong dark emotions"),
    (r"(?i)сходится в яростном вампирическом поединке со сверхсилой против (.+)", r"Engaging in fierce supernatural vampire duel against \1"),
    (r"(?i)тренирует вампирические рефлексы в стремительном поединке", "Training vampiric reflexes in lightning-fast supernatural sparring"),
    (r"(?i)обучается древним таинствам и темным силам под наставничеством (.+)", r"Studying ancient dark arts under the mentorship of master vampire \1"),
    (r"(?i)постигает основы высшего вампирического мастерства", "Learning fundamentals of master vampiric lore and dark powers"),
    (r"(?i)парит в воздухе в темной медитации, черпая энергию из глубин ночи", "Levitating in dark meditation, drawing power from the night"),
    (r"(?i)исполняет зловещую и величественную готическую сонату на духовом органе", "Playing a haunting gothic organ sonata on the pipe organ"),
    (r"(?i)мирно покоится в мягкой обивке богато украшенного гроба", "Resting peacefully in luxurious velvet lining of ornate coffin"),

    # GP05 Parenthood: Parenting, Discipline, School Projects, Curfew, Sack Lunches, Tantrums, Journal, Toys
    (r"(?i)отправляет подумать о своем поведении в тайм-аут (.+)", r"Sending \1 to time out to think about behaviour"),
    (r"(?i)отбывает наказание в тайм-ауте, размышляя о плохом поведении", "Serving time out punishment, reflecting on poor behaviour"),
    (r"(?i)сажает под строгий домашний арест за непослушание (.+)", r"Grounding \1 under strict house arrest for disobedience"),
    (r"(?i)находится под домашним арестом и тоскует взаперти", "Being grounded under house arrest and languishing inside"),
    (r"(?i)прощает проступок и досрочно снимает наказание с (.+)", r"Forgiving misdemeanor and lifting grounding early for \1"),
    (r"(?i)получает долгожданное родительское прощение", "Receiving long-awaited parental forgiveness"),
    (r"(?i)лишает привилегий и временно отбирает гаджеты у (.+)", r"Revoking privileges and taking away gadgets from \1"),
    (r"(?i)лишен любимых привилегий и гаджетов за проступок", "Revoked of favorite privileges and gadgets for misconduct"),
    (r"(?i)в ярости срывается и отчитывает на повышенных тонах (.+)", r"Losing temper and yelling angrily at \1"),
    (r"(?i)выслушивает гневные крики и упреки родителей", "Listening to parents' angry yelling and reproaches"),
    (r"(?i)проводит спокойную, но строгую воспитательную беседу с (.+)", r"Having a calm but firm disciplinary talk with \1"),
    (r"(?i)внимательно слушает нравоучения старших о правилах поведения", "Attentively listening to elders' lectures on rules and behaviour"),
    (r"(?i)с гордостью хвалит за хорошее поведение и послушание (.+)", r"Proudly praising \1 for good behaviour and obedience"),
    (r"(?i)получает заслуженную родительскую похвалу", "Receiving well-deserved parental praise"),
    (r"(?i)крепко сжимает в теплых родительских объятиях (.+)", r"Holding \1 tightly in warm parental bear hug"),
    (r"(?i)наслаждается теплом и поддержкой родительских объятий", "Enjoying the warmth and comfort of parental embrace"),
    (r"(?i)помогает справиться с бурей эмоций и успокоиться (.+)", r"Helping \1 control storm of emotions and calm down"),
    (r"(?i)учится справляться с эмоциями под руководством родителя", "Learning to manage emotions under parent's guidance"),
    (r"(?i)совместно собирает масштабную модель солнечной системы с (.+)", r"Assembling large-scale solar system model project together with \1"),
    (r"(?i)кропотливо конструирует научный проект солнечной системы", "Painstakingly building solar system school science project"),
    (r"(?i)с увлечением строит миниатюрный мост для школьного проекта вместе с (.+)", r"Enthusiastically building miniature bridge school project together with \1"),
    (r"(?i)проверяет грузоподъемность модели моста для школьного проекта", "Testing weight capacity of bridge model for school project"),
    (r"(?i)смешивает шипящие реактивы для макета действующего вулкана вместе с (.+)", r"Mixing fizzing reagents for working volcano school project together with \1"),
    (r"(?i)проводит эффектный химический эксперимент с извержением вулкана", "Performing dramatic chemical volcano eruption experiment"),
    (r"(?i)собирает историческую диораму средневекового замка вместе с (.+)", r"Building historic medieval castle diorama together with \1"),
    (r"(?i)красит и оформляет детали диорамы средневекового замка", "Painting and detailing medieval castle diorama"),
    (r"(?i)склеивает и настраивает детали ученической ракеты вместе с (.+)", r"Gluing and calibrating student rocket project parts together with \1"),
    (r"(?i)собирает миниатюрную ракету для школьного научного проекта", "Building model rocket for school science project"),
    (r"(?i)паяет и соединяет электрические схемы робота для проекта вместе с (.+)", r"Soldering and wiring robot circuits for school project together with \1"),
    (r"(?i)тестирует датчики и микросхемы научного школьного робота", "Testing sensors and circuit boards of science project robot"),
    (r"(?i)с энтузиазмом помогает доделать научный школьный проект для (.+)", r"Enthusiastically helping \1 finish school science project"),
    (r"(?i)сосредоточенно трудится над научным школьным проектом", "Concentrating intensely on school science project"),
    (r"(?i)устанавливает строгий комендантский час на семейной доске объявлений", "Setting strict curfew on family bulletin board"),
    (r"(?i)прикрепляет записку с поручениями и теплыми словами на семейную доску", "Pinning note with chores and warm words to family board"),
    (r"(?i)с гордостью вешает лучший детский рисунок на семейную доску объявлений", "Proudly pinning child's best drawing on family bulletin board"),
    (r"(?i)изучает список домашних обязанностей и поручений на семейной доске", "Checking chore list and household tasks on family board"),
    (r"(?i)красиво сервирует обеденный стол, расставляя приборы и салфетки", "Beautifully setting dining table with silverware and napkins"),
    (r"(?i)заботливо убирает грязную посуду и протирает обеденный стол", "Thoughtfully clearing dirty dishes and wiping dining table"),
    (r"(?i)заботливо упаковывает питательный обед в бумажный пакет для (.+)", r"Lovingly packing nutritious sack lunch brown bag for \1"),
    (r"(?i)собирает вкусный домашний ланч-пакет в школу или на работу", "Packing tasty brown bag sack lunch for school or work"),
    (r"(?i)звонко созывает всех домочадцев к накрытому столу на теплый семейный обед", "Calling all family members to the table for warm family meal"),
    (r"(?i)бродит в плюшевом костюме медведя, переживая необычную фазу взросления", "Wandering in bear costume, going through childhood bear phase"),
    (r"(?i)падает на пол и бьется в безудержной детской истерике", "Throwing wild toddler temper tantrum on the floor"),
    (r"(?i)вдохновенно разливает краски и устраивает хаос на полу", "Inspirately spilling paint and making a creative mess on the floor"),
    (r"(?i)вздыхая, оттирает въевшуюся краску и убирает детский беспорядок с пола", "Sighing while scrubbing paint and cleaning up messy floor"),
    (r"(?i)в ярости хлопает дверью комнаты в порыве бунтарского подросткового гнева", "Angrily slamming bedroom door in teenage rebellion fury"),
    (r"(?i)искренне доверяет свои самые тайные мысли и переживания личному дневнику", "Pensively writing deepest private thoughts and secrets into personal journal"),
    (r"(?i)осторожно прячет личный дневник под матрас от чужих любопытных глаз", "Carefully hiding private journal under mattress from prying eyes"),
    (r"(?i)тайком подглядывает и читает чужие сокровенные секреты в дневнике у (.+)", r"Secretly snooping and reading private journal secrets of \1"),
    (r"(?i)тайком листает чужой секретный дневник, боясь быть застигнутым", "Secretly snooping through someone's diary in fear of being caught"),
    (r"(?i)слушает сердце стетоскопом и лечит любимую плюшевую игрушку у (.+)", r"Listening with stethoscope and treating plush toy together with \1"),
    (r"(?i)увлеченно играет в детского доктора, ставя диагнозы плюшевым пациентам", "Enthusiastically playing with doctor playset, diagnosing teddy bear patients"),
    (r"(?i)строит грандиозную разноцветную башню из строительных кубиков", "Building a magnificent colorful tower out of toy blocks"),

    # GP07 StrangerVille: Military, Secret Lab, Bizarre Plants, Hazmat, Vaccine, Mother Plant
    (r"(?i)четко отдает воинское приветствие по армейскому уставу (.+)", r"Crisply saluting according to military protocol to \1"),
    (r"(?i)щелкает каблуками и четко отдает воинскую честь", "Clicking heels and crisply saluting with military honors"),
    (r"(?i)отрабатывает приемы рукопашного боя в армейском спарринге с (.+)", r"Practicing hand-to-hand combat moves in military sparring with \1"),
    (r"(?i)тренирует приемы самообороны и армейского рукопашного боя", "Practicing self-defense moves and military hand-to-hand combat"),
    (r"(?i)властно отдает приказ упасть и отжаться для (.+)", r"Authoritatively ordering to drop and give push-ups to \1"),
    (r"(?i)командным голосом муштрует подчиненных на плацу", "Drilling subordinates on the parade ground with a commanding voice"),
    (r"(?i)чеканит уверенный строевой шаг в армейском строю", "Marching with confident military drill steps"),
    (r"(?i)упорно отжимается от земли, поддерживая образцовую военную форму", "Powerfully doing push-ups from the ground, maintaining peak military fitness"),
    (r"(?i)ловко и незаметно подбрасывает шпионский жучок в карман (.+)", r"Deftly and stealthily planting a listening bug in pocket of \1"),
    (r"(?i)скрытно устанавливает подслушивающее устройство", "Stealthily planting a covert listening bug"),
    (r"(?i)в наушниках перехватывает секретные переговоры за шпионской станцией прослушки", "Intercepting classified chatter in headphones at covert listening station"),
    (r"(?i)шантажирует компрометирующей аудиозаписью секретных разговоров (.+)", r"Blackmailing \1 with incriminating audio recording of secret conversations"),
    (r"(?i)использует тайный шпионский компромат для шантажа", "Using covert spy wiretap audio for blackmail"),
    (r"(?i)сопоставляет улики, фотографии и схемы за доской расследований, собирая тайное досье", "Connecting evidence, photos and blueprints at mystery board, compiling classified dossier"),
    (r"(?i)скрытно фотографирует пульсирующие аномальные лозы возле секретной лаборатории", "Stealthily photographing pulsating bizarre vines near secret lab"),
    (r"(?i)лихорадочно перерывает засекреченные лабораторные папки в поисках правительственных тайн", "Frantically searching classified lab folders for government secrets"),
    (r"(?i)тщательно сканирует почву переносным сканером, собирая редкие фиолетовые споры", "Carefully scanning ground with handheld scanner, gathering rare purple spores"),
    (r"(?i)прикладывает взломанную ключ-карту и отпирает бронированные гермодвери лаборатории", "Swiping hacked lab keycard and unlocking reinforced blast doors of secret lab"),
    (r"(?i)застегивает герметичный костюм химзащиты с фильтром спор перед спуском в кратер", "Zipping up airtight hazmat suit with spore filter before descending into crater"),
    (r"(?i)синтезирует экспериментальную вакцину от спор на химическом анализаторе", "Synthesizing experimental spore vaccine on chemical analyzer"),
    (r"(?i)вводит дозу экспериментальной вакцины от спор зараженному симу (.+)", r"Administering experimental spore vaccine dose to infected \1"),
    (r"(?i)проводит полевое испытание экспериментальной вакцины от вируса спор", "Conducting field test of experimental spore virus vaccine"),
    (r"(?i)делает укол очищающей вакцины и полностью возвращает рассудок (.+)", r"Giving curative vaccine injection, fully restoring sanity to \1"),
    (r"(?i)вводит спасительную вакцину, побеждая действие токсичных спор", "Administering life-saving vaccine, curing toxic spore affliction"),
    (r"(?i)нелепо дергается и странно бежит с безумной застывшей улыбкой на лице", "Erratic twitching and bizarrely running with a crazed frozen smile on face"),
    (r"(?i)жадно надкусывает пульсирующий странный плод, добровольно отдавая разум матери", "Ravenously biting into pulsating bizarre fruit, willingly surrendering mind to the Mother"),
    (r"(?i)с фанатичной любовью поливает и лелеет чужеродные хищные лозы в саду", "Fanatically watering and nurturing alien predatory vines in the garden"),
    (r"(?i)в трансе произносит бессвязные хвалебные речи великой матери кратера", "Speaking incoherent trance praises to the great Mother of the Crater"),
    (r"(?i)яростно поливает гигантское чудовищное материнское растение струями мега-вакцины", "Furiously hosing monstrous Mother Plant with streams of mega-vaccine"),
    (r"(?i)издает громогласный боевой клич и ведет в яростную атаку союзника (.+)", r"Shouting a thunderous battle cry and leading ally \1 into fierce assault"),
    (r"(?i)издает боевой клич, сплачивая команду защитников города", "Sounding war cry, rallying the town defense squad"),
    (r"(?i)наносит решающий сокрушительный удар и окончательно повергает материнское растение", "Delivering decisive crushing blow and vanquishing the Mother Plant once and for all"),
    (r"(?i)почтительно просит ценных мистических даров и здоровья у возрожденного материнского растения", "Respectfully requesting precious mystical boons and vitality from revived Mother Plant"),
    (r"(?i)изучает конспирологические артефакты и секретные товары в лавке диковинок", "Browsing conspiracy artifacts and classified oddities at curio shop"),
    (r"(?i)надевает самодельную шапочку из фольги для защиты разума от мысленного контроля", "Donning handmade tin foil hat to shield mind from psychic control"),

    # GP08 Realm of Magic: Spells, Sages, Duels, Potions, Familiars, Brooms
    (r"(?i)шагает в сияющий портал, перемещаясь в парящий волшебный мир", "Stepping into glowing portal, travelling to floating Magic Realm"),
    (r"(?i)проводит древний обряд посвящения, наделяя чародейской силой (.+)", r"Performing ancient Rite of Ascension, bestowing magical powers upon \1"),
    (r"(?i)проходит через древний обряд посвящения, пробуждая в себе дар чародея", "Undergoing ancient Rite of Ascension, awakening spellcaster gift within"),
    (r"(?i)собирает парящие фиолетовые магические сферы для ритуала посвящения", "Gathering floating purple magical motes for the Ascension ritual"),
    (r"(?i)тренируется в концентрации магической энергии и оттачивает заклинания", "Practicing magical energy concentration and honing spells"),
    (r"(?i)произносит заклинание «чинио», мгновенно восстанавливая сломанный предмет магией", "Casting Repairio spell, instantly mending broken object with magic"),
    (r"(?i)взмахивает палочкой и читает «чистио», мгновенно очищая всё от грязи", "Waving wand and casting Scruggio, instantly clearing away all dirt"),
    (r"(?i)читает заклинание «лакомио», материализуя из воздуха аппетитное горячее блюдо", "Casting Delicioso spell, materializing delicious hot meal out of thin air"),
    (r"(?i)читает заклинание «травио», наполняя увядающие растения живительной магией", "Casting Floralorial spell, infusing wilting plants with revitalizing magic"),
    (r"(?i)читает «телепортио» и растворяется в воздухе, мгновенно перемещаясь", "Casting Transportalate and vanishing into thin air, teleporting instantly"),
    (r"(?i)читает заклинание «тиражио», создавая точную магическую копию предмета", "Casting Copypasto spell, creating an exact magical duplicate of object"),
    (r"(?i)читает заклинание «садио», взращивая плоды прямо на глазах", "Casting Herbio spell, causing plants to sprout and grow before eyes"),
    (r"(?i)читает заклинание «домойо», мгновенно телепортируясь в родной дом", "Casting Homewardial spell, instantly teleporting back home"),
    (r"(?i)накладывает заклятие «грустио», повергая в пучину отчаяния (.+)", r"Casting Despairio spell, plunging \1 into deep sadness"),
    (r"(?i)накладывает на противника чары всепоглощающей тоски и отчаяния «грустио»", "Casting Despairio spell, afflicting opponent with overwhelming gloom"),
    (r"(?i)читает заклятие «бредио», путая мысли и помрачая рассудок (.+)", r"Casting Deliriano spell, confounding thoughts and befuddling mind of \1"),
    (r"(?i)накладывает заклятие «бредио», вызывая помрачение чужого рассудка", "Casting Deliriano spell, confusing opponent's mental clarity"),
    (r"(?i)накладывает заклятие «яростио», провоцируя вспышку дикой ярости у (.+)", r"Casting Furioso spell, provoking uncontrollable fit of wild fury in \1"),
    (r"(?i)читает заклятие «яростио», разжигая ярость и агрессию", "Casting Furioso spell, inciting fury and raw aggression"),
    (r"(?i)окутывает чарами приворота «влюбио», пробуждая пылкую страсть у (.+)", r"Enchanting with Infatuate charm, stirring fiery passion in \1"),
    (r"(?i)читает приворотное заклинание «влюбио»", "Casting Infatuate love charm"),
    (r"(?i)ловко крадет ценный предмет заклинанием «кладио» у (.+)", r"Deftly pilfering valuable item using Burgliate spell from \1"),
    (r"(?i)с помощью заклинания «кладио» магически похищает ценную вещь", "Using Burgliate spell to magically steal valuables"),
    (r"(?i)превращает в неодушевленный предмет заклинанием «морфио» (.+)", r"Turning \1 into inanimate object using Morphiate spell"),
    (r"(?i)превращает цель в неодушевленную статуэтку заклинанием «морфио»", "Transforming target into an inanimate figurine using Morphiate spell"),
    (r"(?i)обрушивает огненный шар заклинания «инферно» на (.+)", r"Hurling fiery blast of Inferniate spell upon \1"),
    (r"(?i)призывает яростное пламя заклинанием «инферно»", "Summoning raging flames with Inferniate spell"),
    (r"(?i)поражает мощным электрическим разрядом заклинания «вжик-вжик» (.+)", r"Striking \1 with powerful electric lightning blast of Zipzap spell"),
    (r"(?i)выпускает трескучие молнии заклинанием «вжик-вжик»", "Discharging crackling lightning bolts with Zipzap spell"),
    (r"(?i)читает заклинание «некропризыв», призывая призрака из загробного мира", "Casting Necrocall spell, summoning a ghost from the netherworld"),
    (r"(?i)заковывает в монолитную ледяную глыбу заклинанием «обездвижио» (.+)", r"Freezing \1 solid into a block of ice with Chillio spell"),
    (r"(?i)замораживает противника в лед заклинанием «обездвижио»", "Freezing opponent into solid ice with Chillio spell"),
    (r"(?i)подчиняет своей воле и разуму заклинанием «подчинио» (.+)", r"Dominating will and mind of \1 with Minionize spell"),
    (r"(?i)порабощает чужой разум заклинанием ментального подчинения «подчинио»", "Enslaving opponent's mind with Minionize thrall spell"),
    (r"(?i)читает высшее заклинание «оживио», возвращая к жизни призрака (.+)", r"Casting master Dedeathify spell, restoring ghost \1 back to life"),
    (r"(?i)читает великое заклинание «оживио», воскрешая призрака", "Casting grand Dedeathify spell, resurrecting the ghost"),
    (r"(?i)снимает темное проклятие очищающим заклинанием «снимио» с (.+)", r"Cleansing dark curse with Decursify spell from \1"),
    (r"(?i)читает заклинание «снимио», снимая с себя тягостное проклятие", "Casting Decursify spell, purging dark curse from self"),
    (r"(?i)колдует над бурлящим котлом, помешивая волшебное зелье черпаком", "Brewing over bubbling cauldron, stirring magical potion with ladle"),
    (r"(?i)экспериментирует с редкими ингредиентами и магическими травами в огромном котле", "Experimenting with rare ingredients and magical herbs in giant cauldron"),
    (r"(?i)аккуратно разливает дымящееся готовое зелье по стеклянным склянкам", "Carefully bottling steaming finished potion into glass vials"),
    (r"(?i)варит сытную колдовскую похлебку в старинном чугунном котле", "Cooking hearty witch's stew in vintage cast-iron cauldron"),
    (r"(?i)осушает склянку с магическим зельем, ощущая прилив волшебных сил", "Downing a bottle of magical potion, feeling surge of arcane power"),
    (r"(?i)скрещивает магические лучи в дружеской дуэли с чародеем (.+)", r"Crossing magic beams in friendly spell duel with spellcaster \1"),
    (r"(?i)скрещивает магические лучи в дружеской чародейской дуэли", "Crossing magic beams in friendly spellcaster duel"),
    (r"(?i)сражается в ожесточенной магической дуэли не на жизнь, а на смерть с (.+)", r"Fighting in fierce magical duel to the finish with \1"),
    (r"(?i)сражается в ожесточенной и опасной дуэли на заклинаниях", "Fighting in fierce and hazardous spellcaster duel"),
    (r"(?i)ведет магическую дуэль за редкие артефакты и тайные знания с (.+)", r"Dueling for rare artifacts and arcane knowledge with \1"),
    (r"(?i)ведет магическую дуэль за ценные артефакты и заклинания", "Engaging in magic duel for valuable artifacts and spells"),
    (r"(?i)призывает и связывает узами духа нового волшебного фамильяра", "Binding spirit bond with a new magical familiar"),
    (r"(?i)призывает парящего верного фамильяра для защиты от магической гибели", "Summoning floating loyal familiar to guard against magical death"),
    (r"(?i)доверительно беседует со своим верным магическим фамильяром", "Confiding in loyal magical familiar"),
    (r"(?i)отпускает волшебного фамильяра отдыхать в астральный мир", "Dismissing magical familiar to rest in astral realm"),
    (r"(?i)выполняет головокружительные кульбиты и мертвые петли в полете на метле", "Performing thrilling stunts and loop-de-loops flying on magic broom"),
    (r"(?i)взмывает в небеса и стремительно летит верхом на волшебной метле", "Soaring into the skies and swooping swiftly on a magic broom"),
    (r"(?i)корчится от переизбытка магического заряда, рискуя погибнуть от перегрузки", "Writhed in magical charge overload, risking death from magical excess"),
    (r"(?i)страдает от мучительного действия древнего темного проклятия", "Suffering from tormenting affliction of ancient dark curse"),
    (r"(?i)выбирает волшебные палочки, книги заклинаний и ингредиенты на аллее заклинателей", "Browsing magic wands, spellbooks, and ingredients at Caster's Alley"),

    # GP09 Star Wars: Journey to Batuu - Lightsabers, Droids, Starships, Sabacc, First Order, Resistance
    (r"(?i)собирает индивидуальный световой меч из рукояти и кайбер-кристалла в мастерской сави", "Assembling custom lightsaber from hilt and kyber crystal at Savi's Workshop"),
    (r"(?i)оттачивает владение световым мечом, парируя выстрелы летающего тренировочного зонда", "Honing lightsaber prowess, deflecting blasts from hovering training remote"),
    (r"(?i)тренирует джедайские приемы в спарринге на световых мечах с (.+)", r"Practicing Jedi techniques in lightsaber sparring with \1"),
    (r"(?i)тренирует боевые стойки и выпады со световым мечом", "Practicing combat stances and lightsaber strikes"),
    (r"(?i)яростно скрещивает гудящие световые мечи в смертельной дуэли с (.+)", r"Fiercely clashing humming lightsabers in deadly duel with \1"),
    (r"(?i)сражается в динамичной и зрелищной дуэли на световых мечах", "Fighting in dynamic and spectacular lightsaber duel"),
    (r"(?i)конструирует и программирует собственного астромеханика в депо дроидов мьюбо", "Building and programming custom astromech at Mubo's Droid Depot"),
    (r"(?i)приказывает верному дроиду шумно отвлечь патрульных штурмовиков около (.+)", r"Commanding loyal droid to noisily distract patrolling stormtroopers near \1"),
    (r"(?i)приказывает дроиду устроить громкую диверсию и отвлечь патруль", "Commanding droid to create a loud diversion and distract patrol"),
    (r"(?i)отдает команду дроиду поразить электрическим разрядом шокера (.+)", r"Commanding droid to deliver electric shocker zap to \1"),
    (r"(?i)командует дроиду применить защитный электрошокер", "Commanding droid to deploy defensive electric shocker"),
    (r"(?i)подключает дроида к компьютерной панели для скоростного взлома систем безопасности", "Connecting droid to computer panel to slice security systems"),
    (r"(?i)дружелюбно общается с дроидом, слушая его веселое бинарное пищание", "Chatting warmly with droid, listening to its cheerful binary beeps"),
    (r"(?i)забирается в кабину звездного истребителя т-70 «крестокрыл» и вылетает на боевую миссию сопротивления", "Climbing into cockpit of T-70 X-Wing starfighter, embarking on Resistance combat mission"),
    (r"(?i)пилотирует штурмовой шаттл первого ордена «сид-эшелон» в воздушном патруле", "Piloting First Order TIE Echelon assault shuttle on aerial patrol"),
    (r"(?i)занимает место пилота в легендарном «соколе тысячелетия» и отправляется в рискованный контрабандный рейс", "Taking pilot seat of legendary Millennium Falcon, setting off on daring smuggling run"),
    (r"(?i)внимательно проверяет гипердвигатель и орудийные турели космического корабля", "Thoroughly inspecting starship hyperdrive and laser cannon turrets"),
    (r"(?i)ведет азартную карточную игру в сабакк на галактические кредиты с (.+)", r"Playing high-stakes Sabacc card game for galactic credits with \1"),
    (r"(?i)разыгрывает рискованную партию в сабакк, блефуя и надеясь на чистый сабакк", "Playing risky game of Sabacc, bluffing and aiming for pure Sabacc"),
    (r"(?i)смакует экзотический освежающий галактический коктейль в шумной кантине оги", "Savoring exotic refreshing galactic cocktail at bustling Oga's Cantina"),
    (r"(?i)лакомится фирменным ронто-врапом с хрустящими местными специями батуу", "Enjoying signature Ronto Wrap with crispy local Batuu spices"),
    (r"(?i)отрывается под зажигательные инопланетные ритмы дроида-диджея dj r-3x в кантине оги", "Grooving to catchy alien beats of DJ R-3X droid at Oga's Cantina"),
    (r"(?i)внимательно сканирует документы и проверяет на благонадежность (.+)", r"Carefully scanning ID documents and checking loyalty of \1"),
    (r"(?i)сканирует датапад и проводит проверку личности подозрительного прохожего", "Scanning datapad and conducting identity check on suspicious citizen"),
    (r"(?i)помещает под стражу по приказу первого ордена подозрительного смутьяна (.+)", r"Detaining suspicious dissident \1 under First Order command"),
    (r"(?i)берет под арест нарушителя порядка первого ордена", "Placing First Order curfew violator under arrest"),
    (r"(?i)взламывает защищенную контрольную панель аванпоста с помощью даташифратора", "Slicing secure outpost control panel using dataspike tool"),
    (r"(?i)скрытно следит за перемещениями офицеров и передает координаты штабу сопротивления", "Stealthily tracking officer movements and transmitting coordinates to Resistance HQ"),
    (r"(?i)проводит тайную операцию по доставке ценного контрабандного груза в обход патрулей", "Conducting covert operation to deliver valuable contraband cargo past patrols"),
    (r"(?i)отдыхает и восстанавливает силы в жилом отсеке на аванпосте черный шпиль", "Resting and recharging in dwelling quarters at Black Spire Outpost"),
    (r"(?i)применяет джедайское внушение силы, подчиняя мысли (.+)", r"Using Jedi Force mind trick, bending thoughts of \1"),
    (r"(?i)использует внушение силы для обхода бдительности собеседника", "Using Jedi Force mind trick to bypass suspicion"),

    # GP10 Dream Home Decorator: Interior Decorator, Photos, Big Reveal, Modular Furniture
    (r"(?i)делает снимки комнаты «до ремонта» на камеру для профессионального портфолио", "Taking 'Before' photos of the room for professional design portfolio"),
    (r"(?i)фотографирует обновленное стильное пространство «после ремонта» для портфолио", "Photographing stylish renovated room 'After' renovation for design portfolio"),
    (r"(?i)тщательно измеряет стены и дверные проемы рулеткой, оценивая габариты помещения", "Carefully measuring walls and doorways with measuring tape, assessing room dimensions"),
    (r"(?i)внимательно осматривает планировку и естественное освещение комнаты перед переделкой", "Attentively inspecting room layout and natural lighting before makeover"),
    (r"(?i)вежливо провожает клиентов (.+) на прогулку на время ремонтных работ", r"Politely escorting clients \1 out for a walk during renovation work"),
    (r"(?i)провожает хозяев дома на прогулку перед началом масштабного ремонта", "Escorting homeowners out for a walk before major renovation begins"),
    (r"(?i)звонит клиентам и радостно сообщает о завершении грандиозного ремонта", "Calling clients and cheerfully announcing the grand renovation completion"),
    (r"(?i)торжественно ведет клиентов с закрытыми глазами (.+) в обновленную комнату", r"Grandly escorting blindfolded clients \1 into renovated room"),
    (r"(?i)торжественно распахивает двери, начиная грандиозный показ готового интерьера", "Grandly swinging doors open, kicking off the Big Reveal of renovated interior"),
    (r"(?i)с гордостью демонстрирует клиенту стильный элемент обновленного интерьера (.+)", r"Proudly showing off stylish element of renovated interior to \1"),
    (r"(?i)демонстрирует клиентам ключевой обновленный акцент в интерьере", "Showing clients the key renovated interior accent"),
    (r"(?i)всплескивает руками и чуть не плачет от счастья, восхищаясь новым интерьером", "Gasping and tearing up with sheer joy, adoring the new interior"),
    (r"(?i)обескураженно морщится и разочарованно разглядывает неудачные дизайнерские решения", "Cringing in dismay, looking disappointed at poor design choices"),
    (r"(?i)выносит эмоциональный окончательный вердикт дизайнеру интерьера (.+)", r"Delivering emotional final verdict to interior designer \1"),
    (r"(?i)выносит окончательный вердикт и рассчитывается за выполненный ремонт", "Delivering final verdict and paying for completed renovation"),
    (r"(?i)уютно устроился на мягком секционном модульном диване", "Cozying up on a plush modular sectional sofa"),
    (r"(?i)аккуратно раскладывает одежду по полочкам встроенной модульной гардеробной", "Neatly organizing clothing on shelves of built-in modular closet system"),
    (r"(?i)любуется отражением и примеряет наряды у зеркала модульного гардероба", "Admiring reflection and trying on outfits by modular closet mirror"),
    (r"(?i)гармонично расставляет книги, суккуленты и дизайнерский декор на модульных полках", "Harmoniously arranging books, succulents and designer decor on modular shelves"),
    (r"(?i)готовит изысканное блюдо на современной встроенной индукционной варочной панели", "Cooking gourmet dish on sleek built-in induction cooktop"),
    (r"(?i)запекает хрустящие тосты и закуски в компактной настольной духовке", "Baking crispy toasts and treats in compact countertop oven"),
    (r"(?i)увлеченно чертит планировку и собирает цветовой мудборд на графическом планшете", "Enthusiastically sketching room layout and compiling color moodboard on tablet"),
    (r"(?i)пишет экспертную статью о современных трендах в интерьере для журнала архитектуры", "Writing expert interior design trend column for architecture magazine"),

    # GP11 My Wedding Stories: Preparations, Tartosa, Ceremony, Reception, Traditions
    (r"(?i)пробует кусочки праздничных свадебных тортов, выбирая идеальный вкус для банкета", "Tasting slices of festive wedding cakes, choosing perfect flavor for banquet"),
    (r"(?i)выбирает нежный свадебный букет из свежих цветов у флориста в тартозе", "Selecting delicate wedding bouquet from fresh flower florist in Tartosa"),
    (r"(?i)примеряет роскошный свадебный наряд перед зеркалом, готовясь к торжеству", "Trying on exquisite wedding attire in front of mirror, getting ready for celebration"),
    (r"(?i)планирует сценарий свадьбы, дресс-код и список гостей для церемонии", "Planning wedding activities, dress code, and guest list for ceremony"),
    (r"(?i)звонит в старинные свадебные колокола тартозы, возвещая о празднике любви", "Ringing historic Tartosa wedding bells, proclaiming the celebration of love"),
    (r"(?i)торжественно и грациозно идет по свадебному проходу к алтарю к (.+)", r"Solemnly and gracefully walking down the wedding aisle towards \1"),
    (r"(?i)торжественно шествует по свадебному проходу к украшенной цветами арке", "Solemnly walking down the wedding aisle toward flower-decorated arch"),
    (r"(?i)с умилением разбрасывает лепестки роз по дорожке перед молодыми", "Lovingly tossing rose petals along aisle path before newlyweds"),
    (r"(?i)бережно несет бархатную подушечку с обручальными кольцами к арке", "Carefully carrying velvet pillow with wedding rings to arch"),
    (r"(?i)торжественно ведет свадебную церемонию и зачитывает клятвы для (.+)", r"Solemnly presiding over wedding ceremony and reading vows for \1"),
    (r"(?i)ведет торжественную церемонию бракосочетания у свадебной арки", "Presiding over solemn wedding ceremony by wedding arch"),
    (r"(?i)с замиранием сердца произносит искреннюю свадебную клятву в любви и верности для (.+)", r"Heartfeltly reciting emotional wedding vows of love and fidelity to \1"),
    (r"(?i)произносит трогательную свадебную клятву перед лицом гостей", "Reciting touching wedding vows before gathered guests"),
    (r"(?i)нежно надевает сверкающее обручальное кольцо на палец (.+)", r"Gently slipping sparkling wedding ring onto \1's finger"),
    (r"(?i)надевает обручальное кольцо на палец избранника, скрепляя союз", "Putting wedding ring on partner's finger, sealing union"),
    (r"(?i)сливается в страстном первом поцелуе молодоженов под свадебной аркой с (.+)", r"Sharing passionate first kiss as newlyweds under wedding arch with \1"),
    (r"(?i)сливается в трепетном первом поцелуе молодоженов под свадебной аркой", "Sharing tender first kiss as newlyweds under wedding arch"),
    (r"(?i)радостно пускает мыльные пузыри и осыпает молодоженов лепестками", "Joyfully blowing bubbles and showering newlyweds with petals"),
    (r"(?i)рука об руку разрезает великолепный многоярусный свадебный торт вместе с (.+)", r"Cutting magnificent tiered wedding cake hand in hand together with \1"),
    (r"(?i)совместно разрезает праздничный свадебный торт под аплодисменты гостей", "Cutting celebratory wedding cake together to applause of guests"),
    (r"(?i)нежно и игриво кормит кусочком свадебного торта (.+)", r"Playfully and sweetly feeding a bite of wedding cake to \1"),
    (r"(?i)угощает партнера сладким кусочком свадебного торта", "Treating partner to a sweet bite of wedding cake"),
    (r"(?i)поднимает бокал игристого нектара и произносит душевный свадебный тост за (.+)", r"Raising glass of sparkling nectar and delivering heartfelt wedding toast to \1"),
    (r"(?i)поднимает праздничный тост за счастье и долгие годы молодых", "Raising celebratory toast to happiness and long life of newlyweds"),
    (r"(?i)кружится в романтическом первом свадебном танце молодоженов с (.+)", r"Twirling in romantic first wedding dance of newlyweds with \1"),
    (r"(?i)кружится в медленном романтическом первом танце новобрачных", "Twirling in slow romantic first dance of newlyweds"),
    (r"(?i)поворачивается спиной и бросает свадебный букет в толпу незамужних гостей", "Turning around and tossing bridal bouquet into crowd of single guests"),
    (r"(?i)ликует от восторга, поймав заветный букет невесты", "Cheering in triumph after catching the coveted bridal bouquet"),
    (r"(?i)почтительно преподносит чашу свадебного чая в знак уважения и благословения для (.+)", r"Respectfully offering cup of wedding tea as token of honor and blessing for \1"),
    (r"(?i)проводит традиционную свадебную чайную церемонию, отдавая дань уважения предкам", "Conducting traditional wedding tea ceremony, honoring elders and ancestors"),
    (r"(?i)романтично прогуливается под руку вдоль живописного побережья тартозы с (.+)", r"Romantically strolling arm in arm along scenic Tartosa coast with \1"),
    (r"(?i)любуется закатом над водопадами и морем в романтичной тартозе", "Admiring sunset over waterfalls and sea in romantic Tartosa"),

    # GP12 Werewolves: Rampage, Abilities, Greg, Tunnels, Packs
    (r"(?i)в приступе неукротимого волчьего бешенства крушит всё вокруг и свирепо бросается на (.+)", r"In fit of uncontrollable werewolf rampage destroying everything and ferociously lunging at \1"),
    (r"(?i)неистово крушит всё вокруг в приступе неукротимого волчьего бешенства", "Wildly smashing everything around in fit of uncontrollable werewolf rampage"),
    (r"(?i)в муках трансформируется в свирепое звериное обличье под светом луны", "Painfully transforming into ferocious werewolf beast form under moonlight"),
    (r"(?i)издает скорбный вой, пытаясь обуздать кипящую ярость и вернуть человеческое самообладание", "Letting out somber howl, attempting to tame boiling fury and regain human composure"),
    (r"(?i)запрокидывает голову к ночному небу и протяжно воет на сияющую луну", "Tilting head back to night sky and letting out long howl at shining moon"),
    (r"(?i)издает раскатистый стайный вой, призывая волчью стаю объединиться", "Letting out resonant pack howl, summoning wolf pack to unite"),
    (r"(?i)по-звериному метит территорию, обозначая границы своих охотничьих угодий", "Marking territory beast-style, claiming boundaries of hunting grounds"),
    (r"(?i)яростно разрывает землю когтями в поисках древних реликвий и костей", "Ferociously clawing and scavenging ground in search of ancient relics and bones"),
    (r"(?i)с диким аппетитом пожирает сырое мясо и грызет всё, что попадается на пути", "Devouring raw meat with feral appetite and gnawing on anything in path"),
    (r"(?i)тщательно вылизывает и чистит густую волчью шерсть", "Meticulously licking and grooming thick wolf fur"),
    (r"(?i)сворачивается клубком на голой земле и чутко дремлет в зверином обличье", "Curling into a ball on bare ground and napping lightly in beast form"),
    (r"(?i)стремительно крадется по лесной чаще в поисках свежей дичи на ночной охоте", "Swiftly prowling through forest thickets tracking fresh prey on night hunt"),
    (r"(?i)сходится в яростном боевом спарринге оборотней с (.+)", r"Clashing in ferocious werewolf combat sparring match with \1"),
    (r"(?i)сходится в свирепом боевом спарринге оборотней", "Clashing in ferocious werewolf combat sparring match"),
    (r"(?i)бьется не на жизнь, а на смерть за статус вожака альфы против (.+)", r"Battling fiercely for Alpha pack leader rank against \1"),
    (r"(?i)сражается за главенство и лидерский статус вожака альфы в стае", "Fighting for dominance and Alpha pack leader rank in pack"),
    (r"(?i)отчаянно сходится в смертоносной схватке с легендарным свирепым волком грегом", "Desperately clashing in deadly battle with legendary ferocious wolf Greg"),
    (r"(?i)с опаской осматривает предостерегающие знаки у логова опасного отшельника грега", "Apprehensively inspecting warning signs near dangerous hermit Greg's lair"),
    (r"(?i)пробирается сквозь темные лабиринты заброшенных подземных тоннелей мунвуд милл", "Navigating dark labyrinths of abandoned Moonwood Mill underground tunnels"),
    (r"(?i)купается в мистических ледяных водах озера лунвик под лунным сиянием", "Swimming in mystical icy waters of Lake Lunvik under moonlight"),
    (r"(?i)внимательно изучает старинные дневники и расшифровывает древние тайны ликантропии", "Carefully studying ancient diaries and deciphering ancient secrets of lycanthropy"),
    (r"(?i)проводит время в логове стаи, укрепляя братские узы и выполняя поручения вожака", "Spending time at pack hangout, forging pack bonds and fulfilling leader duties"),
    (r"(?i)вносит ценную добычу и ресурсы в общий сундук стаи оборотней", "Contributing valuable loot and resources to shared werewolf pack trunk"),
    (r"(?i)вонзает острые клыки и передает древнее проклятие ликантропии (.+)", r"Sinking sharp fangs and passing ancient curse of lycanthropy to \1"),
    (r"(?i)вонзает клыки, передавая древний дар ликантропии", "Sinking fangs, passing the ancient gift of lycanthropy"),
    (r"(?i)завороженно любуется полной луной, ощущая зов древней первобытной природы", "Mesmerized gazing at full moon, feeling call of ancient primal nature"),

    # SP01 Luxury Party Stuff: Fountain, Buffet Table, Glamour, High Society
    (r"(?i)заполняет фонтан изысканным фруктовым пуншем и освежающими напитками", "Filling fountain with exquisite fruit punch and refreshing beverages"),
    (r"(?i)заполняет праздничный фонтан струящимся теплым шоколадом", "Filling festive fountain with flowing warm chocolate"),
    (r"(?i)заполняет фонтан аппетитным расплавленным сырным фондю", "Filling fountain with mouth-watering melted cheese fondue"),
    (r"(?i)обмакивает сочную спелую клубнику в струящийся шоколадный фонтан", "Dipping juicy ripe strawberry into flowing chocolate fountain"),
    (r"(?i)окунает аппетитные закуски в нежное горячее сырное фондю", "Dipping delicious snacks into tender hot cheese fondue"),
    (r"(?i)наполняет бокал искрящимся напитком из праздничного фонтана", "Filling glass with sparkling beverage from festive fountain"),
    (r"(?i)тайком подмешивает секретный ингредиент в праздничный фонтан с напитками", "Secretly slipping special ingredient into festive drink fountain"),
    (r"(?i)изысканно сервирует банкетный стол деликатесами, канапе и закусками", "Exquisitely serving banquet buffet table with delicacies, canapes and appetizers"),
    (r"(?i)наполняет тарелку изысканными закусками с банкетного стола", "Filling plate with exquisite delicacies from banquet buffet table"),
    (r"(?i)с наслаждением лакомится нежными миндальными пирожными макарон", "Blissfully indulging in delicate almond macaron pastries"),
    (r"(?i)любуется своим блистательным вечерним нарядом перед зеркалом", "Admiring dazzling glamorous evening outfit in the mirror"),
    (r"(?i)элегантно дефилирует в ослепительном наряде, приковывая восхищенные взгляды (.+)", r"Elegantly strutting in dazzling outfit, catching admiring glances of \1"),
    (r"(?i)элегантно дефилирует в ослепительном вечернем наряде, купаясь во внимании гостей", "Elegantly strutting in dazzling evening wear, basking in guests' admiration"),
    (r"(?i)зажигательно и грациозно танцует под ритмы праздничной музыки вместе с (.+)", r"Lively and gracefully dancing to festive party music together with \1"),
    (r"(?i)грациозно танцует под звуки светской музыки среди сияющих огней вечеринки", "Gracefully dancing to high-society party music amidst glittering lights"),

    # SP02 Perfect Patio Stuff: Hot Tubs, Aromatherapy, Grilling, Patio Dining
    (r"(?i)нежно обнимается и целуется в теплой воде джакузи с (.+)", r"Lovingly cuddling and kissing in warm hot tub water with \1"),
    (r"(?i)нежно обнимается и целуется в теплой воде джакузи", "Lovingly cuddling and kissing in warm hot tub water"),
    (r"(?i)беззаботно купается нагишом в теплой гидромассажной ванне под открытым небом", "Carefreely skinny dipping in warm open-air hot tub under the sky"),
    (r"(?i)наслаждается сеансом целебной ароматерапии с эфирными маслами в джакузи", "Enjoying healing aromatherapy session with essential oils in hot tub"),
    (r"(?i)улучшает гидромассажную ванну, монтируя мощные струи и стереосистему", "Upgrading hot tub, installing powerful water jets and stereo system"),
    (r"(?i)подсыпает мыльную пену в джакузи, устраивая забавный пенный переполох", "Slipping soap into hot tub, triggering a hilarious bubbly foam overflow"),
    (r"(?i)нежится в бурлящей гидромассажной ванне с расслабляющими пузырьками вместе с (.+)", r"Soaking in bubbling hot tub with relaxing jets together with \1"),
    (r"(?i)нежится в бурлящей гидромассажной ванне с расслабляющими пузырьками", "Soaking in bubbling hot tub with relaxing jets"),
    (r"(?i)жарит аппетитное сочное барбекю на открытом гриле во внутреннем дворике", "Grilling appetizing juicy barbecue on patio outdoor grill"),
    (r"(?i)обедает свежеприготовленным барбекю за уютным столиком с зонтиком на веранде", "Dining on freshly grilled barbecue at cozy umbrella table on patio"),
    (r"(?i)безмятежно отдыхает и греется на солнце в удобном шезлонге во внутреннем дворике", "Serenely relaxing and sunbathing in comfy patio lounge chair"),

    # SP03 Cool Kitchen Stuff: Ice Cream Maker, Cones, Bowls, Brain Freeze, Kitchen
    (r"(?i)готовит партию нежного домашнего мороженого в мороженице", "Making a batch of creamy homemade ice cream in the ice cream maker"),
    (r"(?i)украшает мороженое сладким сиропом, взбитыми сливками и кондитерской посыпкой", "Garnishing ice cream with sweet syrup, whipped cream and sprinkles"),
    (r"(?i)накладывает аппетитные шарики мороженого в хрустящий вафельный рожок", "Scooping appetizing ice cream scoops into a crispy waffle cone"),
    (r"(?i)раскладывает шарики мороженого в изящную десертную креманку", "Scooping ice cream scoops into an elegant dessert bowl"),
    (r"(?i)хватается за голову от внезапной и пронзительной заморозки мозга", "Clutching head from sudden and intense ice cream brain freeze"),
    (r"(?i)выдыхает клуб горячего пламени после порции драконьего мороженого", "Exhaling a plume of fire after a bite of dragon's breath ice cream"),
    (r"(?i)дрожит от леденящего холода, ощущая призрачный мятный мороз", "Shivering with chills, feeling the ghostly mint freeze"),
    (r"(?i)с удовольствием лакомится тающим мороженым в хрустящем вафельном рожке", "Blissfully enjoying melting ice cream in a crispy waffle cone"),
    (r"(?i)неспешно смакует изысканный холодный десерт ложечкой из креманки", "Leisurely savoring gourmet ice cream with a spoon from a dessert bowl"),
    (r"(?i)с гордостью любуется стильным гарнитуром и сияющими поверхностями кухни", "Proudly admiring sleek modern cabinetry and gleaming kitchen surfaces"),
    (r"(?i)тщательно протирает столешницы и наводит идеальный лоск на современной кухне", "Thoroughly wiping down countertops and polishing modern kitchen surfaces"),

    # SP04 Spooky Stuff: Pumpkin Carving, Candy Bowl, Spooky Treats, Costumes
    (r"(?i)со всей силы яростно растаптывает резную тыкву в оранжевые ошмётки", "Furiously stomping and smashing the carved pumpkin into pieces"),
    (r"(?i)надевает на голову жуткую резную тыкву, пугая всех вокруг", "Wearing a spooky carved pumpkin head, scaring everyone around"),
    (r"(?i)обрабатывает резную тыкву защитным раствором для долгой сохранности", "Treating carved pumpkin with preserving spray to keep it fresh"),
    (r"(?i)зажигает мерцающую свечу внутри резной праздничной тыквы", "Lighting a flickering candle inside the carved festive pumpkin"),
    (r"(?i)мастерски вырезает зловещую светящуюся рожицу на спелой оранжевой тыкве", "Skilfully carving a sinister glowing face on a ripe orange pumpkin"),
    (r"(?i)с визгом отскакивает от вазы со сладостями, испугавшись выскочившей руки скелета", "Screaming and jumping back in terror from the snapping skeleton hand in candy bowl"),
    (r"(?i)осторожно тянется за сладостью в мистическую вазу с конфетами", "Cautiously reaching for a treat in the mystical spooky candy bowl"),
    (r"(?i)готовит жуткие сырные шарики с глазами и хрустящее печенье к празднику", "Cooking eerie eyeball cheese balls and crunchy spooky cookies for the party"),
    (r"(?i)с опаской пробует жуткое хэллоуинское угощение со стола", "Timidly tasting spooky Halloween party treats from the table"),
    (r"(?i)разглядывает жуткие декорации, паутину и светящиеся гирлянды на вечеринке", "Examining spooky party decorations, cobwebs and glowing lanterns"),
    (r"(?i)примеряет маскарадный костюм для жуткой праздничной вечеринки", "Trying on a fancy masquerade costume for the spooky party"),

    # SP05 Movie Hangout Stuff: Popcorn, Movies, Projector, Reactions, Boho Lounge
    (r"(?i)готовит большую миску хрустящего ароматного попкорна в попкорнице", "Making a large bowl of fragrant crunchy popcorn in popcorn popper"),
    (r"(?i)ловко подбрасывает воздушную кукурузу и ловит её ртом", "Skillfully tossing popcorn into the air and catching it in mouth"),
    (r"(?i)хрустит аппетитным теплым попкорном под просмотр кинофильма", "Munching on warm delicious popcorn while watching a movie"),
    (r"(?i)уютно прижимается и обнимается при совместном просмотре романтического фильма вместе с (.+)", r"Snuggling and cuddling during romantic movie with \1"),
    (r"(?i)уютно прижимается и обнимается при совместном просмотре романтического фильма с (.+)", r"Snuggling and cuddling during romantic movie with \1"),
    (r"(?i)уютно прижимается и обнимается при совместном просмотре романтического фильма", "Snuggling and cuddling during romantic movie"),
    (r"(?i)в ужасе закрывает глаза руками от пугающей сцены фильма ужасов", "Covering eyes in terror during scary horror movie scene"),
    (r"(?i)громко хохочет над уморительной комедией на большом экране кинотеатра", "Laughing out loud at hilarious comedy on big movie screen"),
    (r"(?i)утирает слезы от трогательной мелодрамы перед экраном домашнего кинотеатра", "Wiping away tears from touching drama before home theater screen"),
    (r"(?i)с замиранием сердца смотрит захватывающий фильм на гигантском киноэкране", "Watching gripping movie on giant movie screen with bated breath"),
    (r"(?i)расслабляется в уютном богемном кресле среди ярких подушек и гирлянд", "Relaxing in cozy bohemian armchair amidst vibrant cushions and fairy lights"),

    # SP06 Romantic Garden Stuff: Wishing Well, Fountain, Roses, Park Bench
    (r"(?i)в ужасе пятится от злорадного лика колодца желаний, предвещающего беду", "Backing away in terror from sinister face of wishing well foreboding misfortune"),
    (r"(?i)ликует от невероятной щедрости и исполнения мечты у колодца желаний", "Rejoicing over incredible generosity and wish granted by wishing well"),
    (r"(?i)бросает монетку и загадывает заветное желание у шепчущего колодца желаний", "Tossing a coin and making a cherished wish at whispering wishing well"),
    (r"(?i)выливает флакон мыла в фонтан, наполняя сад гигантскими хлопьями пены", "Pouring soap bottle into fountain, filling garden with huge foam bubbles"),
    (r"(?i)весело плещется и брызгается прохладной водой в фонтане вместе с (.+)", r"Joyfully playing and splashing cool fountain water together with \1"),
    (r"(?i)весело плещется и брызгается прохладной водой в фонтане с (.+)", r"Joyfully playing and splashing cool fountain water with \1"),
    (r"(?i)задорно плещется и играет струями воды в прохладном фонтане", "Playfully splashing and frolicking in cool fountain water streams"),
    (r"(?i)бросает блестящую монетку в фонтан и загадывает романтическое желание", "Tossing shiny coin into fountain and making a romantic wish"),
    (r"(?i)умиротворенно сидит на бортике фонтана, слушая мерное журчание воды", "Peacefully sitting on fountain edge, listening to gentle water burble"),
    (r"(?i)нежно обнимается и целуется на уединенной кованой скамейке в саду с (.+)", r"Gently cuddling and kissing on secluded garden bench with \1"),
    (r"(?i)нежно обнимается и целуется на уединенной кованой скамейке в саду", "Gently cuddling and kissing on secluded garden bench"),
    (r"(?i)вдыхает сладкий аромат цветущих роз в романтическом саду", "Breathing in sweet scent of blooming roses in romantic garden"),
    (r"(?i)неспешно прогуливается по благоухающему парку среди увитых плющом арок", "Leisurely strolling through fragrant park among ivy-covered arches"),

    # SP07 Kids Room Stuff: Puppet Theater, Voidcritters, Battle Station, Tween Pop
    (r"(?i)показывает захватывающий кукольный детектив с таинственными уликами в театре", "Putting on a thrilling mystery puppet show with clues at the theater"),
    (r"(?i)разыгрывает фантастическую космическую оперу с кукольными пришельцами в театре", "Performing a fantastic sci-fi space opera puppet show at the theater"),
    (r"(?i)показывает трогательную школьную сказку в детском кукольном театре", "Putting on a touching school drama puppet show at the kids theater"),
    (r"(?i)устраивает уморительное комедийное кукольное представление в детском театре", "Putting on a hilarious comedy puppet show at the kids theater"),
    (r"(?i)показывает захватывающее кукольное представление в кукольном театре", "Putting on an exciting puppet show at the puppet theater"),
    (r"(?i)усердно репетирует кукольный спектакль, отрабатывая голоса и интонации персонажей", "Diligently rehearsing a puppet show, practicing voices and character intonations"),
    (r"(?i)с восторгом смотрит кукольное представление юного таланта (.+)", r"Delightedly watching youth talent puppet show by \1"),
    (r"(?i)с восторгом смотрит яркое представление в детском кукольном театре", "Delightedly watching vibrant puppet show at the kids puppet theater"),
    (r"(?i)азартно разыскивает редкие коллекционные карточки космических монстров", "Eagerly searching for rare collectible Voidcritter cards"),
    (r"(?i)ликует и празднует триумфальную победу своего космического монстра на арене", "Rejoicing and celebrating triumphant victory of Voidcritter in the arena"),
    (r"(?i)огорчается из-за обидного поражения своего космического монстра в битве", "Upset over disappointing defeat of Voidcritter in battle"),
    (r"(?i)тренирует своего космического монстра на электронной арене, повышая его боевой уровень", "Training Voidcritter on electronic battle station, leveling up its power"),
    (r"(?i)с азартом обменивается коллекционными карточками космических монстров с (.+)", r"Eagerly trading collectible Voidcritter cards with \1"),
    (r"(?i)с азартом обменивается коллекционными карточками космических монстров", "Eagerly trading collectible Voidcritter cards"),
    (r"(?i)внимательно изучает характеристики, способности и стихию редкой карточки монстра", "Carefully examining stats, element and powers of rare Voidcritter card"),
    (r"(?i)сражается в напряженной карточной дуэли космических монстров на боевой станции против (.+)", r"Battling in an intense Voidcritter card duel at the battle station against \1"),
    (r"(?i)сражается в напряженной карточной дуэли космических монстров на боевой станции", "Battling in an intense Voidcritter card duel at the battle station"),
    (r"(?i)задорно танцует и подпевает под модные молодежные треки радиостанции «твин-поп»", "Cheerfully dancing and singing along to trendy Tween Pop radio tracks"),
    (r"(?i)с горящими глазами смотрит захватывающий сериал про космических монстров по тв", "Watching thrilling Voidcritters show on TV with wide eyes"),

    # SP08 Backyard Stuff: Lawn Water Slide, Bird Feeder, Wind Chimes, Drink Pitcher, Umbrella Table
    (r"(?i)с визгом проносится по скользкой водной дорожке сквозь облака мыльной пены вместе с (.+)", r"Screaming in joy while sliding through soapy foam bubbles on water slide together with \1"),
    (r"(?i)с визгом проносится по скользкой водной дорожке сквозь облака мыльной пены с (.+)", r"Screaming in joy while sliding through soapy foam bubbles on water slide with \1"),
    (r"(?i)с визгом проносится по водной дорожке сквозь пушистые облака мыльной пены", "Screaming in joy while sliding through fluffy soap foam on the water slide"),
    (r"(?i)задорно выливает бутылку жидкого мыла на водную дорожку для создания скользкой пены", "Cheerfully pouring liquid soap onto water slide to create slippery foam"),
    (r"(?i)исполняет эффектный трюк и кружится волчком при скольжении на водной дорожке", "Performing a flashy trick and spinning like a top while water sliding"),
    (r"(?i)неуклюже плюхается и скользит на животе по водной дорожке, поднимая фонтан брызг", "Clumsily belly-flopping and sliding down water slide with a huge splash"),
    (r"(?i)смеётся и подбадривает лихо катающегося на водной дорожке (.+)", r"Laughing and cheering on water sliding \1"),
    (r"(?i)смеётся и с восторгом наблюдает за катающимися на водной дорожке", "Laughing and delightedly watching Sims slide on the water slide"),
    (r"(?i)с веселым смехом и брызгами съезжает по водной дорожке на заднем дворе вместе с (.+)", r"Laughing joyfully and splashing down backyard water slide together with \1"),
    (r"(?i)с веселым смехом и брызгами съезжает по водной дорожке на заднем дворе с (.+)", r"Laughing joyfully and splashing down backyard water slide with \1"),
    (r"(?i)с веселым смехом и брызгами съезжает по водной дорожке на заднем дворе", "Laughing joyfully and splashing down the backyard lawn water slide"),
    (r"(?i)в панике отмахивается от набросившейся стаи рассерженных птиц у кормушки", "Frantically swatting away a flock of angry dive-bombing birds at feeder"),
    (r"(?i)насыпает отборные семена в подвесную птичью кормушку на заднем дворе", "Pouring birdseed into hanging bird feeder in the backyard"),
    (r"(?i)завороженно наблюдает за прилетевшими к кормушке разноцветными певчими птицами", "Mesmerized watching colorful songbirds flocking to the bird feeder"),
    (r"(?i)тонко настраивает высоту звучания подвесных колокольчиков ветра", "Finely adjusting the pitch of hanging wind chimes"),
    (r"(?i)умиротворенно слушает нежный мелодичный перезвон колокольчиков ветра", "Peacefully listening to gentle melodious chime of wind chimes"),
    (r"(?i)готовит запотевший кувшин освежающего домашнего лимонада со льдом", "Making a frosty pitcher of refreshing homemade iced lemonade"),
    (r"(?i)наливает из кувшина стакан прохладного цитрусового лимонада со льдом", "Pouring a glass of chilled citrus lemonade on ice from the pitcher"),
    (r"(?i)с наслаждением пьет ледяной освежающий напиток из запотевшего стакана", "Delightfully sipping ice-cold refreshing drink from frosted glass"),
    (r"(?i)уютно сидит за столиком с ярким зонтиком на заднем дворе, общаясь с (.+)", r"Cozying up at vibrant patio umbrella table in backyard, chatting with \1"),
    (r"(?i)уютно отдыхает за столиком под ярким зонтиком на свежем воздухе заднего двора", "Cozying up at patio umbrella table in the backyard fresh air"),

    # SP09 Vintage Glamour Stuff: Butler, Vanity Table, Globe Bar, Hollywood Glamour
    (r"(?i)искренне благодарит дворецкого (.+?) за безупречное обслуживание и преданность", r"Genuinely thanking Butler \1 for impeccable service and dedication"),
    (r"(?i)искренне благодарит дворецкого за безупречное обслуживание дома", "Genuinely thanking the butler for impeccable household service"),
    (r"(?i)строго выговаривает дворецкому (.+?) за неподобающее поведение и огрехи в работе", r"Sternly reprimanding Butler \1 for improper behavior and shortcomings"),
    (r"(?i)строго отчитывает дворецкого за огрехи в работе", "Sternly reprimanding the butler for shortcomings at work"),
    (r"(?i)выделяет уютную спальню и указывает личную кровать для дворецкого (.+)", r"Assigning cozy bedroom and personal bed to Butler \1"),
    (r"(?i)выделяет личную спальню и кровать для дворецкого", "Assigning personal bedroom and bed to the butler"),
    (r"(?i)просит дворецкого (.+?) подать изысканное угощение и освежающий напиток", r"Requesting Butler \1 to serve exquisite gourmet meal and refreshing drink"),
    (r"(?i)просит дворецкого подать изысканные напитки и закуски", "Requesting the butler to serve exquisite drinks and appetizers"),
    (r"(?i)отпускает дворецкого на заслуженный отдых до следующего рабочего дня", "Dismissing the butler to enjoy well-deserved rest until next work day"),
    (r"(?i)чинно приветствует гостей у дверей особняка с безупречной выправкой дворецкого", "Statelily greeting guests at mansion doorway with impeccable butler poise"),
    (r"(?i)уморительно балуется с маминой помадой и пудрой перед зеркалом туалетного столика", "Hilariously playing with makeup and powder before vanity mirror"),
    (r"(?i)изящно наносит гламурный винтажный макияж перед зеркалом туалетного столика", "Elegantly applying glamorous vintage makeup before vanity table mirror"),
    (r"(?i)придирчиво поправляет прическу и макияж, оценивая свой безупречный образ в зеркале", "Fastidiously touching up hair and makeup, admiring reflection in vanity mirror"),
    (r"(?i)с нескрываемым самолюбованием красуется перед винтажным туалетным столиком", "Admiring reflection with undisguised vanity before vintage dressing table"),
    (r"(?i)прихорашивается и наводит красоту перед зеркалом туалетного столика", "Freshening up and getting glamorous before vanity table mirror"),
    (r"(?i)с любопытством разглядывает старинные карты и вращает резной глобус-бар", "Curiously studying antique maps and spinning ornate 16th century globe bar"),
    (r"(?i)откидывает крышку старинного глобуса и наливает порцию выдержанного винтажного напитка", "Opening antique globe lid and pouring a serving of vintage aged drink"),
    (r"(?i)неспешно смакует изысканный выдержанный напиток из винтажного хрустального бокала", "Leisurely savoring fine vintage drink from a crystal glassware glass"),
    (r"(?i)томно и расслабленно полулежит на роскошном шезлонге в атмосфере золотого века голливуда", "Languidly lounging on luxurious chaise in Golden Age of Hollywood elegance"),

    # SP10 Bowling Night Stuff: Bowling Lane, Strikes, Spares, Tricks, Moonlight Bowling
    (r"(?i)с грохотом выбивает сокрушительный страйк,\s*сбивая все кегли одним ударом,\s*и ликует!?", "Loudly scoring a crushing strike, knocking down all pins in one roll, and cheering!"),
    (r"(?i)точным добивающим броском закрывает спэа,\s*сбивая оставшиеся кегли на дорожке", "Accurately picking up a spare with a clean finishing roll on the lane"),
    (r"(?i)исполняет виртуозный трюковой бросок с эффектным вращением и подкруткой шара", "Executing a skillful trick shot with an impressive spin on the bowling ball"),
    (r"(?i)неуклюже поскальзывается на полированном паркете дорожки при замахе шаром", "Clumsily slipping on the polished bowling lane floor while swinging the ball"),
    (r"(?i)с досадой наблюдает,\s*как шар для боулинга с глухим стуком скатывается в боковой желоб", "Watching in dismay as the bowling ball thuds into the gutter lane"),
    (r"(?i)азартно состязается на светящейся неоновой дорожке лунного боулинга против (.+)", r"Excitedly competing on glowing neon moonlight bowling lane against \1"),
    (r"(?i)азартно играет в боулинг под неоновыми огнями светомузыки", "Excitedly playing bowling under neon lights and music"),
    (r"(?i)придирчиво выбирает идеальный по весу и цвету шар для боулинга на стойке", "Carefully picking the ideal weight and color bowling ball from the rack"),
    (r"(?i)громко аплодирует и подбадривает готового к броску (.+?) в боулинге", r"Loudly applauding and cheering on \1 for the bowling roll"),
    (r"(?i)с азартом наблюдает за игрой в боулинг,\s*болея за игроков на дорожках", "Enthusiastically watching bowling and cheering for players on the lanes"),
    (r"(?i)пританцовывает под заводные ритмы стиля ню-диско в зале боулинг-клуба", "Grooving to upbeat NuDisco rhythms inside the bowling alley"),
    (r"(?i)отдыхает на ретро-диванчике боулинг-клуба в перерыве между фреймами с (.+)", r"Relaxing on retro lounge sofa between bowling frames with \1"),
    (r"(?i)отдыхает на диванчике боулинг-клуба,\s*обсуждая результаты фреймов", "Relaxing on bowling alley sofa, chatting about frame scores"),
    (r"(?i)делает сосредоточенный разбег и бросает увесистый шар по дорожке боулинга против (.+)", r"Taking focused approach and rolling heavy ball down bowling lane against \1"),
    (r"(?i)делает сосредоточенный разбег и посылает шар по гладкой дорожке боулинга", "Taking focused approach and rolling ball down smooth bowling lane"),

    # SP11 Fitness Stuff: Rock Climbing Wall, Fire Challenge, Earbuds, Workout Videos
    (r"(?i)отважно карабкается по скалодрому,\s*уворачиваясь от вырывающихся струй пламени в испытании огнем!?", "Bravely climbing the wall while dodging bursts of fire jets in the fire challenge!"),
    (r"(?i)теряет хватку на покатом рельефе скалодрома и с глухим стуком срывается на мягкий мат", "Losing grip on the climbing wall incline and falling with a thud onto the safety mat"),
    (r"(?i)изо всех сил преодолевает сложнейший скоростной маршрут на скалодроме против (.+)", r"Pushing limits on the challenging climbing wall speed route against \1"),
    (r"(?i)изо всех сил преодолевает сложнейший скоростной маршрут на бегущем скалодроме", "Pushing limits on the challenging speed route of the treadmill climbing wall"),
    (r"(?i)упорно штурмует вертикальные зацепы механического скалодрома,\s*тренируя выносливость и силу хвата", "Steadfastly conquering handholds on the mechanical climbing wall, building endurance and grip strength"),
    (r"(?i)с замиранием сердца наблюдает за подъемом (.+?) по отвесному скалодрому", r"Watching with bated breath as \1 ascends the steep climbing wall"),
    (r"(?i)с интересом наблюдает за тренировкой скалолаза на механической стене", "Intently watching a climber train on the mechanical wall"),
    (r"(?i)зажигательно пританцовывает на ходу,\s*полностью погрузившись в любимый трек в беспроводных наушниках", "Upbeat dancing on the go, completely immersed in music through wireless earbuds"),
    (r"(?i)слушает бодрящую музыку через компактные спортивные наушники-вкладыши", "Listening to invigorating music through compact sports earbuds"),
    (r"(?i)энергично повторяет ритмичные танцевальные движения за инструктором программы «пламбумба» перед телевизором", "Energetically following rhythmic dance moves of the Plumbumba TV workout video"),
    (r"(?i)выполняет интенсивные силовые упражнения перед экраном телевизора по видео-программе", "Doing intense muscle sculpting exercises before the TV following a fitness video"),
    (r"(?i)обливаясь потом,\s*старательно повторяет упражнения домашней видео-тренировки перед экраном", "Sweating through a home fitness workout video in front of the TV"),

    # SP12 Toddler Stuff: Ball Pit, Slides, Tunnels, Jungle Gym, Pretend Play
    (r"(?i)с восторженным визгом ныряет и барахтается среди разноцветных шариков в сухом бассейне", "Enthusiastically squealing and splashing around in the colorful ball pit"),
    (r"(?i)задорно разбрасывает разноцветные пластиковые шарики из бассейна во все стороны", "Playfully tossing colorful plastic balls from the pit in all directions"),
    (r"(?i)весело копошится и играет в бассейне с пластиковыми шариками", "Happily bustling and playing in the plastic ball pit"),
    (r"(?i)бережно придерживает и страхует малыша (.+?),\s*помогая съехать с горки", r"Gently supporting and guiding toddler \1 down the slide"),
    (r"(?i)бережно помогает малышу съехать с детской горки", "Gently helping the toddler down the slide"),
    (r"(?i)смело забирается наверх и со смехом съезжает вниз по пологой детской горке", "Bravely climbing up and laughing while zooming down the toddler slide"),
    (r"(?i)с любопытством пробирается на четвереньках сквозь извилистый игровой туннель", "Curiously crawling on all fours through the winding play tunnel"),
    (r"(?i)воображает себя отважным космонавтом,\s*управляющим межгалактическим звездолетом на площадке", "Pretending to be a brave astronaut piloting an intergalactic starship on the playground"),
    (r"(?i)фантазирует о дальних плаваниях,\s*играя в грозного пиратского капитана на палубе игрового корабля", "Pretending to sail the high seas as a fierce pirate captain on the play shipwreck"),
    (r"(?i)активно исследует и осваивает игровой комплекс для малышей,\s*лазая по лесенкам и площадкам", "Actively exploring and climbing through the toddler jungle gym"),
    (r"(?i)с умилением и вниманием присматривает за играющим на площадке (.+)", r"Fondly and attentively watching \1 play on the playground"),
    (r"(?i)с теплой улыбкой присматривает за резвящимися на площадке малышами", "Fondly watching the toddlers frolic on the playground"),
    (r"(?i)уютно сидит на мягком пледе для пикника,\s*разделяя вкусный перекус с (.+)", r"Cozying up on soft picnic blanket, sharing tasty snack with \1"),
    (r"(?i)уютно сидит на детском пледе для пикника,\s*лакомясь аппетитными угощениями", "Cozying up on toddler picnic blanket, enjoying delicious snacks"),

    # SP13 Laundry Day Stuff: Washer, Dryer, Wash Tub, Clothesline, Hamper
    (r"(?i)добавляет душистые лепестки цветов и натуральные масла в стиральную машину для аромата", "Adding fragrant flower petals and natural oils into the washing machine for scent"),
    (r"(?i)загружает накопившееся белье в стиральную машину и запускает цикл стирки", "Loading piled-up laundry into the washing machine and starting the wash cycle"),
    (r"(?i)выгружает влажное свежевыстиранное белье из барабана стиральной машины", "Unloading damp freshly washed laundry from the washing machine drum"),
    (r"(?i)тщательно вычищает скопившийся пух и ворс из фильтра сушильной машины для безопасности", "Thoroughly cleaning lint and fuzz from the dryer lint trap for safety"),
    (r"(?i)перекладывает влажные вещи в сушильную машину и включает горячую сушку", "Transferring damp clothes to the dryer and turning on the heat dry cycle"),
    (r"(?i)усердно намыливает и стирает белье вручную в деревянном корыте с пеной", "Diligently scrubbing and hand washing clothes with soapy suds in the rustic wash tub"),
    (r"(?i)с усилием выкручивает и отжимает мокрое белье над тазом перед сушкой", "Tightly wringing out wet laundry over the tub before hanging to dry"),
    (r"(?i)аккуратно развешивает мокрое белье на бельевой веревке на свежем воздухе под солнцем", "Neatly hanging wet laundry on the outdoor clothesline under the fresh sun"),
    (r"(?i)снимает с веревки сухое белье,\s*пахнущее ветром,\s*теплым солнцем и свежестью", "Gathering dry clothes from the line smelling of breeze, warm sun, and freshness"),
    (r"(?i)с глубоким удовольствием вдыхает приятный аромат свежести и тепла от чистого белья", "Deeply savoring the cozy scent of freshness and warmth from clean laundry"),
    (r"(?i)аккуратно складывает теплое постиранное белье в ровные стопки и убирает в комод", "Neatly folding warm washed laundry into tidy stacks and putting it away"),
    (r"(?i)собирает ворох грязной одежды по комнатам и опустошает корзину для стирки", "Gathering piles of dirty laundry from around the house and emptying the hamper"),
    (r"(?i)занимается домашними хлопотами и стиркой скопившейся одежды", "Tending to household chores and washing accumulated laundry"),

    # SP14 My First Pet Stuff: Rodents, Habitats, Pet Outfits, Rabid Rodent Fever
    (r"(?i)выпивает спасительную сыворотку-противоядие от бешенства грызунов", "Drinking the lifesaving antidote serum for Rabid Rodent Fever"),
    (r"(?i)заказывает целебную сыворотку и вакцину от бешенства грызунов через компьютер", "Ordering a curative serum and Rabid Rodent Fever vaccine on the computer"),
    (r"(?i)в панике изучает на компьютере симптомы смертельной болезни «бешенство грызунов»", "Panickedly researching symptoms of the deadly Rabid Rodent Fever on the computer"),
    (r"(?i)вскрикивает от боли и неожиданности,\s*когда капризный грызун больно кусает за палец", "Yelping in pain and surprise as the feisty rodent bites their finger hard"),
    (r"(?i)насыпает свежий питательный корм в кормушку маленького питомца в вольере", "Refilling fresh nutritious food into the small pet's dish in the habitat"),
    (r"(?i)с нежностью угощает маленького грызуна аппетитным лакомством из рук", "Gently offering a tasty treat from their hands to the little rodent"),
    (r"(?i)старательно вычищает и моет клетку грызуна,\s*засыпая свежие опилки", "Diligently cleaning and washing the rodent habitat and adding fresh bedding"),
    (r"(?i)завороженно смотрит,\s*как маленький питомец запускает крошечную ракету из своего вольера", "Mesmerized watching the little pet launch a miniature rocket from its habitat"),
    (r"(?i)с изумлением наблюдает за странными научными экспериментами и секретной жизнью хомяка в вольере", "Astonishedly watching the strange scientific experiments and secret life of the hamster in its habitat"),
    (r"(?i)с улыбкой наблюдает,\s*как маленький питомец усердно наворачивает круги в беговом колесе", "Smilingly watching the little pet enthusiastically spin laps on the exercise wheel"),
    (r"(?i)тихонько сюсюкает и шепчет забавные секретики на ушко своему маленькому питомцу", "Softly baby-talking and whispering amusing secrets into their little pet's ear"),
    (r"(?i)позволяет маленькому питомцу забавно бегать по рукам и плечам", "Letting the little pet playfully scurry along their arms and shoulders"),
    (r"(?i)ласково держит грызуна на ладонях,\s*гладит пушистую спинку и играет с ним", "Gently holding the rodent in their hands, stroking its fluffy back, and playing"),
    (r"(?i)с умилением наряжает своего питомца в забавный карнавальный костюмчик", "Adoringly dressing their pet up in a funny cute costume"),
    (r"(?i)с восхищением любуется своим четвероногим другом в очаровательном наряде", "Admiringly gazing at their four-legged friend looking adorable in their outfit"),
    (r"(?i)в лихорадочном бреду пускает пену изо рта и галлюцинирует,\s*воображая себя гигантским хомяком", "Frothing at the mouth in feverish delirium and hallucinating as a giant hamster"),
    (r"(?i)мучается от сильного жара,\s*яростного чихания и зуда,\s*вызванных бешенством грызунов", "Suffering from high fever, violent sneezing, and severe itching caused by Rabid Rodent Fever"),
    (r"(?i)с нежностью заботится о своем маленьком питомце в вольере", "Tenderly caring for their little pet in the habitat"),

    # SP15 Moschino Stuff: Fashion Photography, Studio Tripod, Backdrop, Poses, Freelancer Career
    (r"(?i)терпеливо ловит удачный кадр,\s*фотографируя четвероногого питомца со штатива", "Patiently catching the perfect shot, photographing the pet from a tripod"),
    (r"(?i)устанавливает таймер на штативе и делает стильный студийный автопортрет", "Setting the tripod timer and snapping a stylish studio self-portrait"),
    (r"(?i)настраивает освещение и меняет декоративный фон в фотостудии для съемки", "Adjusting studio lighting and changing the backdrop for the fashion shoot"),
    (r"(?i)проводит профессиональную модную фотосессию,\s*снимая модель со штатива в студии", "Conducting a professional fashion photoshoot, photographing the model from a tripod in the studio"),
    (r"(?i)принимает эффектную модную позу перед объективом фотокамеры,\s*как с обложки журнала", "Striking a striking high-fashion pose in front of the camera lens like on a magazine cover"),
    (r"(?i)очаровательно кокетничает и принимает чувственную позу для фотографа", "Charmingly flirting and striking a sensual pose for the photographer"),
    (r"(?i)принимает дерзкую и уверенную позу,\s*демонстрируя стиль и харизму на подиуме", "Striking a bold and confident pose, radiating style and runway charisma"),
    (r"(?i)динамично позирует в прыжке и движении для яркого модного кадра", "Dynamically posing in mid-jump and motion for a high-energy fashion shot"),
    (r"(?i)принимает глубокую задумчивую позу с загадочным взглядом вдаль", "Striking a pensive and thoughtful pose with an enigmatic gaze into the distance"),
    (r"(?i)весело дурачится и корчит милые смешные рожицы перед объективом", "Playfully goofing around and making cute funny faces in front of the lens"),
    (r"(?i)позирует перед камерой на студийном маркере для фотографа", "Posing in front of the camera on the studio mark for the photographer"),
    (r"(?i)отправляет лучшие студийные фотографии клиенту на согласование и публикацию", "Submitting the best studio photos to the client for approval and publication"),
    (r"(?i)тщательно обрабатывает снимки на компьютере,\s*выполняя ретушь и цветовую коррекцию", "Carefully editing photos on the computer, retouching and color-grading the shots"),
    (r"(?i)публикует свежие модные кадры с фотосессии в симстаграм для подписчиков", "Posting fresh fashion photoshoot shots to Simstagram for followers"),
    (r"(?i)ищет новые выгодные заказы на модные фотосессии в базе агентства фрилансеров", "Browsing freelance agency listings for new high-paying fashion photoshoot gigs"),

    # SP16 Tiny Living Stuff: Murphy Bed, All-in-One Media Center, Tiny Home
    (r"(?i)занимается страстным вуху в раскладной кровати мёрфи", "Having passionate WooHoo in the fold-down Murphy bed"),
    (r"(?i)с тревогой борется с заклинившим и неподатливым механизмом раскладной кровати", "Anxiously struggling with the jammed and stubborn mechanism of the Murphy bed"),
    (r"(?i)чудом избегает опасности быть захлопнутым и придавленным тяжелой кроватью мёрфи", "Narrowly escaping being crushed and trapped by the heavy Murphy bed"),
    (r"(?i)улучшает кровать мёрфи,\s*устанавливая усиленные пружины против заклинивания", "Upgrading the Murphy bed with reinforced springs to prevent dangerous jamming"),
    (r"(?i)тщательно чинит и смазывает пружинный механизм раскладной кровати мёрфи", "Carefully repairing and lubricating the spring mechanism of the Murphy bed"),
    (r"(?i)с усилием тянет за ручки и опускает раскладную кровать мёрфи из стенного шкафа", "Straining to pull the handles and lower the Murphy bed from the wall cabinet"),
    (r"(?i)поднимает и убирает кровать мёрфи обратно в стенную нишу для освобождения места в комнате", "Lifting and folding the Murphy bed back into the wall to free up floor space"),
    (r"(?i)уютно спит на раскладной кровати мёрфи,\s*наслаждаясь теплом и мягким матрасом", "Sleeping soundly on the Murphy bed, enjoying warmth and comfortable mattress"),
    (r"(?i)дремлет и восстанавливает силы на разложенной кровати мёрфи", "Napping and regaining energy on the unfolded Murphy bed"),
    (r"(?i)устроился на кровати мёрфи и расслабленно отдыхает в компактной комнате", "Lying down on the Murphy bed, relaxing in the compact room"),
    (r"(?i)смотрит увлекательную передачу на универсальной компактной медиасистеме", "Watching an entertaining show on the all-in-one compact media center"),
    (r"(?i)слушает любимую музыку,\s*играющую из встроенных колонок компактного медиацентра", "Listening to favorite tunes from the integrated speakers of the compact media center"),
    (r"(?i)уютно устроился за чтением книги с полки компактного медиа-шкафа", "Cozying up to read a book taken from the compact all-in-one media shelf"),
    (r"(?i)наслаждается идеальным минимализмом,\s*покоем и теплым уютом своего крошечного дома", "Basking in the perfect minimalism, peace, and cozy charm of their tiny home"),

    # SP17 Nifty Knitting Stuff: Knitting, Rocking Chair, Plopsy
    (r"(?i)терпеливо обучает вязанию спицами,\s*показывая правильный хват и набор петель", "Patiently teaching how to knit, demonstrating needle grip and casting on stitches"),
    (r"(?i)с досадой распускает неудачный вязаный проект обратно в моток шерстяных ниток", "Frustratedly frogging and unraveling a failed knitting project back into a ball of yarn"),
    (r"(?i)с благородным сердцем жертвует связанные вручную теплые вещи на благотворительность", "Generously donating hand-knitted warm garments to charity"),
    (r"(?i)с любовью вяжет милую мягкую игрушку из цветных клубков пряжи", "Lovingly knitting an adorable plush toy from colorful yarn balls"),
    (r"(?i)с нежностью вяжет крошечный мягкий комбинезон для малыша", "Tenderly knitting a soft tiny onesie for a baby"),
    (r"(?i)кропотливо вяжет уютный шерстяной свитер со сложным узором", "Painstakingly knitting a cozy wool sweater with an intricate pattern"),
    (r"(?i)сосредоточенно вяжет спицами теплые носки или шапку из мягкой пряжи", "Intently knitting warm socks or a beanie from soft yarn"),
    (r"(?i)вяжет стильный предмет декора для дома,\s*ловко орудуя спицами и пряжей", "Knitting a stylish home decor piece, skillfully working needles and yarn"),
    (r"(?i)мерно покачивается в кресле-качалке,\s*неспешно позвякивая вязальными спицами", "Steadily rocking in the rocking chair, clacking knitting needles softly"),
    (r"(?i)умиротворенно качается в кресле-качалке,\s*предаваясь теплым воспоминаниям о былом", "Peacefully rocking in the rocking chair, reminiscing about good old times"),
    (r"(?i)весело раскачивается в деревянном кресле-качалке,\s*смеясь от забавного скрипа", "Cheerfully rocking back and forth in the wooden rocking chair, giggling at the squeaks"),
    (r"(?i)мягко покачивается в уютном кресле-качалке,\s*наслаждаясь тишиной и покоем", "Gently rocking in the cozy rocking chair, enjoying peaceful silence"),
    (r"(?i)мерно и безмятежно покачивается в деревянном кресле-качалке", "Steadily and serenely rocking in the wooden rocking chair"),
    (r"(?i)фотографирует и выставляет рукодельный шедевр на продажу на интернет-ярмарке «продавито»", "Taking photos and listing handcrafted masterpiece for sale on Plopsy online marketplace"),
    (r"(?i)бережно упаковывает и отправляет через почтовый ящик проданный на «продавито» заказ", "Carefully packaging and shipping out a sold Plopsy order via the mailbox"),
    (r"(?i)увлеченно листает каталог уникальных товаров от мастеров со всего мира на «продавито»", "Enthusiastically browsing catalog of unique handmade creations from crafters worldwide on Plopsy"),
    (r"(?i)увлеченно вяжет спицами,\s*ловко перебирая шерстяную пряжу из корзинки", "Enthusiastically knitting with needles, deftly pulling wool yarn from the basket"),
    (r"(?i)ощущает неловкость и холод в романтических отношениях из-за рокового «проклятия свитера»", "Feeling awkwardness and relationship strain due to the dreaded Sweater Curse"),

    # SP18 Paranormal Stuff: Seance, Haunted House, Guidry, Bonehilda, Investigator
    (r"(?i)с благоговением призывает легендарную горничную-скелета скелехильду", "Reverently summoning the legendary skeleton maid Bonehilda"),
    (r"(?i)проводит священную церемонию очищения дома от злых духов за спиритическим столом", "Performing a sacred house-cleansing ceremony to banish evil spirits at the seance table"),
    (r"(?i)входит в глубокий транс за спиритическим столом,\s*общаясь с душами умерших", "Entering a deep trance at the seance table, communing with departed souls"),
    (r"(?i)медитирует и сканирует духовные вибрации помещения на предмет паранормальной нестабильности", "Meditating and scanning spiritual vibrations of the room for paranormal volatility"),
    (r"(?i)совершает жуткий ритуал на спиритическом столе,\s*временно принимая форму призрака", "Performing a ghastly ritual at the seance table, temporarily turning into a ghost"),
    (r"(?i)изготавливает защитную священную свечу из эктоплазматического воска", "Crafting a protective sacred candle from ectoplasmic wax"),
    (r"(?i)чертит мелом защитный спиритический круг на полу для проведения сеанса", "Chalking a protective seance circle onto the floor to perform spiritual rites"),
    (r"(?i)проводит таинственный спиритический сеанс за круглым столом с хрустальным шаром", "Conducting a mysterious seance around the table with a crystal ball"),
    (r"(?i)идет на отчаянный шаг и жертвует крошечный кусочек своей души загадочному духу", "Taking a desperate gamble and offering a tiny piece of their soul to the mysterious specter"),
    (r"(?i)с осторожностью преподносит ценный подарок или лакомство парящему призрачному духу", "Cautiously offering a valuable gift or treat to the floating specter"),
    (r"(?i)в ярости и панике растаптывает жуткую проклятую куклу,\s*изгоняя темную сущность", "Frantically and angrily stomping a creepy cursed doll to banish its dark essence"),
    (r"(?i)брезгливо вытирает липкую мерцающую эктоплазму с пола в проклятом доме", "Squeamishly mopping up sticky glowing ectoplasm from the floor of the haunted house"),
    (r"(?i)выкорчевывает потусторонние ползучие лозы и жуткие наросты скверны", "Ripping out otherworldly creeping tendrils and eerie cursed growths"),
    (r"(?i)в ужасе спасается бегством от пылающей яростью и злобой призрачной ведьмы темперанции", "Fleeing in terror from the blazing, furious spectral witch Temperance"),
    (r"(?i)увлеченно беседует с призрачным обольстителем и наставником клодом рене гидри", "Engaging in spirited conversation with the charming ghostly mentor Claude Rene Guidry"),
    (r"(?i)смело проводит обряд экзорцизма,\s*изгоняя враждебных потусторонних сущностей", "Bravely performing an exorcism, banishing hostile otherworldly entities"),
    (r"(?i)выполняет опасный заказ по паранормальному расследованию,\s*очищая дом от полтергейста", "Fulfilling a perilous paranormal investigator gig, ridding the client's home of poltergeists"),
    (r"(?i)дрожит от всепоглощающего паранормального страха перед шорохами и мерцанием света в проклятом доме", "Shivering in overwhelming paranormal fear at flickering lights and eerie creaks in the haunted house"),
    (r"(?i)ощущает потустороннюю прохладу и незримое присутствие духов в воздухе дома с привидениями", "Feeling the eerie spectral chill and presence of ghosts in the haunted house air"),

    # SP19 Home Chef Hustle Stuff: Stand Mixer, Waffle Maker, Pizza Oven, Food Stand
    (r"(?i)виртуозно подбрасывает и крутит круг теста для пиццы в воздухе,\s*словно заправский пиццайоло", "Masterfully tossing and spinning pizza dough in the air like a seasoned pizzaiolo"),
    (r"(?i)запекает домашнюю фокаччу или сочный закрытый кальцоне в портативной печи", "Baking artisan focaccia or a juicy calzone in the portable pizza oven"),
    (r"(?i)выпекает ароматную пиццу с хрустящей корочкой и тянущимся сыром в печи для пиццы", "Baking a fragrant pizza with crispy crust and gooey melted cheese in the pizza oven"),
    (r"(?i)выпекает золотистые хрустящие вафли в электрической вафельнице", "Cooking golden crispy waffles in the electric waffle maker"),
    (r"(?i)наслаждается свежеиспеченной хрустящей вафлей с аппетитным топпингом", "Savoring a freshly baked crispy waffle with delicious toppings"),
    (r"(?i)замешивает эластичное тесто с помощью настольного планетарного миксера", "Kneading supple dough with the countertop stand mixer"),
    (r"(?i)взбивает кулинарные смеси и готовит заготовки ингредиентов в настольном миксере", "Whisking culinary mixtures and preparing prepped ingredients in the stand mixer"),
    (r"(?i)громко расхваливает горячие блюда и зазывает голодных прохожих к своему кулинарному прилавку", "Loudly praising hot delicacies and beckoning hungry passersby to their food stand"),
    (r"(?i)открывает кулинарную распродажу и выкладывает аппетитные угощения на витрину торгового прилавка", "Opening a food sale and setting out mouthwatering dishes on the food stand display"),
    (r"(?i)бойко ведет уличную торговлю выпечкой и деликатесами за переносным прилавком", "Briskly tending the portable food stand, selling hot street food and treats"),
    (r"(?i)подсчитывает солидную дневную выручку и наводит порядок на торговом прилавке", "Counting up tidy daily earnings and packing up the food stand"),
    (r"(?i)готовит на кухне с невероятной ловкостью и упоением настоящего шеф-повара", "Cooking in the kitchen with the sublime skill and passion of a master chef"),

    # SP20 Crystal Creations Stuff: Gemology Table, Jewelry Crafting, Crystal Grid, Crystal Tree
    (r"(?i)виртуозно гранит драгоценный камень за геммологическим столом,\s*придавая минералу безупречную форму", "Masterfully cutting a gemstone at the gemology table, shaping the mineral into flawless perfection"),
    (r"(?i)тщательно полирует грани свежеограненного самоцвета,\s*добиваясь ослепительного блеска", "Carefully polishing the facets of a freshly cut gem, achieving a dazzling sparkle"),
    (r"(?i)кропотливо создает авторское ювелирное украшение за геммологическим столом,\s*инкрустируя драгоценный камень", "Painstakingly crafting artisan jewelry at the gemology table, setting a precious gemstone"),
    (r"(?i)внимательно изучает эскизы и выбирает изысканный дизайн для нового ювелирного шедевра", "Carefully reviewing designs and choosing an exquisite setting for a new jewelry masterpiece"),
    (r"(?i)убирает каменную пыль и осколки минералов,\s*наводя идеальный порядок на геммологическом столе", "Sweeping up stone dust and mineral shards, tidying up the gemology table"),
    (r"(?i)увлеченно работает за геммологическим столом над созданием изящных украшений и огранкой камней", "Passionately working at the gemology table crafting fine jewelry and cutting gemstones"),
    (r"(?i)аккуратно раскладывает украшения и кристаллы на решетке для зарядки под лунным светом", "Carefully arranging jewelry and crystals on the grid for moonlight charging"),
    (r"(?i)бережно забирает с решетки заряженное лунным светом ювелирное изделие,\s*светящееся магической силой", "Gently collecting a moonlight-charged piece of jewelry glowing with magical power from the grid"),
    (r"(?i)наблюдает за тем,\s*как кристаллы на решетке впитывают мистическую энергию лунного света", "Watching the crystals on the grid absorb mystical moonlight energy"),
    (r"(?i)бережно собирает диковинные сверкающие самоцветы с ветвей кристального дерева", "Gently harvesting rare sparkling gemstones from the branches of the crystal tree"),
    (r"(?i)с заботой ухаживает за волшебным кристальным деревом,\s*любуясь растущими минералами", "Carefully tending the magical crystal tree, admiring the growing minerals"),
    (r"(?i)с гордостью и восхищением разглядывает надетое на себя сверкающее ювелирное украшение", "Proudly and admiringly inspecting the sparkling handcrafted jewelry they are wearing"),
    (r"(?i)замечает,\s*что любимое ювелирное украшение полностью исчерпало лунный заряд и требует подзарядки", "Noticing that their favorite jewelry has completely depleted its lunar charge and needs recharging"),
    (r"(?i)ощущает мощные защитные вибрации и прилив мистической энергии от надетого заряженного самоцвета", "Feeling powerful protective vibrations and a surge of mystical energy from their charged crystal jewelry"),

    # Base Game Emergencies & Objects: Fire, Cowplant, Voodoo, Future Cube, Clay, Mailbox, Telescope
    (r"(?i)сбивает пламя и тушит горящего сима из огнетушителя", "Beating down flames and extinguishing a burning Sim with a fire extinguisher"),
    (r"(?i)отважно тушит пламя пожара из огнетушителя", "Bravely extinguishing the flames of a fire with a fire extinguisher"),
    (r"(?i)в панике вызывает пожарных по телефону,\s*сообщая о возгорании", "Panickingly calling the fire department to report a fire"),
    (r"(?i)в панике мечется и кричит от ужаса перед разгоревшимся пожаром", "Panicking and screaming in terror at the raging fire"),
    (r"(?i)кормит хищное растение-корову \(проглотис людоедию\) свежим куском мяса", "Feeding the carnivorous Cowplant (Laganaphyllis Simnovorii) a fresh piece of meat"),
    (r"(?i)игриво дразнит и играет с растением-коровой \(проглотис людоедией\)", "Playfully teasing and playing with the Cowplant (Laganaphyllis Simnovorii)"),
    (r"(?i)ласково гладит челюсти и стебель растения-коровы", "Affectionately petting the jaws and stem of the Cowplant"),
    (r"(?i)доит растение-корову,\s*собирая чудодейственную эссенцию жизни", "Milking the Cowplant, collecting the miraculous essence of life"),
    (r"(?i)пытается взять кусок пирога с языка растения-коровы,\s*рискуя быть проглоченным", "Reaching for the cake bait from the Cowplant's tongue, risking being swallowed"),
    (r"(?i)очищает останки и убирает кости вокруг растения-коровы", "Clearing remains and sweeping bones around the Cowplant"),
    (r"(?i)взаимодействует с загадочным хищным растением-коровой \(проглотис людоедией\)", "Interacting with the mysterious carnivorous Cowplant (Laganaphyllis Simnovorii)"),
    (r"(?i)привязывает куклу вуду к симу,\s*проводя тайный ритуал связи", "Binding the voodoo doll to a Sim, performing a secret connection ritual"),
    (r"(?i)колет куклу вуду булавкой,\s*причиняя выбранной жертве острую боль", "Poking the voodoo doll with a needle, inflicting sharp pain on the victim"),
    (r"(?i)щекочет куклу вуду,\s*вызывая приступ неудержимого смеха у жертвы", "Tickling the voodoo doll, causing a fit of uncontrollable laughter in the victim"),
    (r"(?i)нежно обнимает куклу вуду,\s*передавая тепло и симпатию жертве", "Gently cuddling the voodoo doll, sending warmth and affection to the victim"),
    (r"(?i)окунает куклу вуду в воду,\s*насылая сырость и дискомфорт на жертву", "Soaking the voodoo doll in water, inflicting chills and discomfort on the victim"),
    (r"(?i)проводит мистический ритуал с куклой вуду", "Performing a mystical ritual with the voodoo doll"),
    (r"(?i)встряхивает куб будущего и с волнением вопрошает о своей судьбе", "Shaking the Future Cube and anxiously asking about destiny"),
    (r"(?i)увлеченно мнет комок глины в руках,\s*вылепливая забавную фигурку", "Enthusiastically molding a clay blob in their hands, sculpting a figurine"),
    (r"(?i)оплачивает счета за коммунальные услуги через почтовый ящик", "Paying household utility bills through the mailbox"),
    (r"(?i)проверяет почтовый ящик в ожидании свежих писем и посылок", "Checking the mailbox for incoming letters and packages"),
    (r"(?i)опускает в почтовый ящик письмо или посылку для отправки", "Dropping a letter or package into the mailbox for delivery"),
    (r"(?i)тайно подглядывает за соседями через окуляр телескопа", "Secretly spying on neighbors through the telescope eyepiece"),
    (r"(?i)сканирует ночной небосвод в телескоп в поисках внеземной жизни", "Scanning the night sky through the telescope in search of alien life"),

    (r"(?i)идёт строить космическую ракету", "Heading to build a space rocket"),
    (r"(?i)идёт на стартовую площадку для запуска ракеты", "Heading to launch pad for space rocket launch"),
    (r"(?i)идёт к космической ракете", "Heading towards the space rocket"),

    # EP04 Cats & Dogs: Pets, Vet Clinic, Training, Agility, Care, Lighthouse
    # Vet Clinic & Surgery
    (r"(?i)проводит процедуру плановой стерилизации питомца \((.+?)\)", r"Performing routine spay/neuter procedure on pet (\1)"),
    (r"(?i)проводит операцию по отмене стерилизации питомца \((.+?)\)", r"Performing surgery to reverse spay/neuter on pet (\1)"),
    (r"(?i)проводит сложную ветеринарную операцию питомцу \((.+?)\) на хирургическом столе", r"Performing complex veterinary surgery on pet (\1) at surgery station"),
    (r"(?i)измеряет температуру тела питомца \((.+?)\) ветеринарным термометром", r"Taking pet's body temperature (\1) with veterinary thermometer"),
    (r"(?i)слушает сердцебиение и дыхание питомца \((.+?)\) стетоскопом", r"Listening to pet's heartbeat and breathing (\1) with stethoscope"),
    (r"(?i)берет кожный соскоб и осматривает уши питомца \((.+?)\) на паразитов", r"Taking skin swab and inspecting pet's ears (\1) for parasites"),
    (r"(?i)успокаивает напуганного питомца \((.+?)\) ласковыми поглаживаниями на столе", r"Calming frightened pet (\1) with gentle petting on exam table"),
    (r"(?i)ставит точный ветеринарный диагноз четвероногому пациенту \((.+?)\)", r"Making accurate veterinary diagnosis for four-legged patient (\1)"),
    (r"(?i)делает лечебный укол четвероногому пациенту \((.+?)\)", r"Giving medical injection/shot to four-legged patient (\1)"),
    (r"(?i)надевает защитный ветеринарный конус \(воротник\) на шею питомца \((.+?)\)", r"Putting protective cone collar on pet's neck (\1)"),
    (r"(?i)дает назначенное лекарство заболевшему питомцу \((.+?)\)", r"Administering prescribed medicine to sick pet (\1)"),
    (r"(?i)проводит ветеринарный осмотр питомца \((.+?)\) на смотровом столе", r"Performing veterinary checkup on pet (\1) on exam table"),

    # Dog Training & Agility
    (r"(?i)обучает собаку \((.+?)\) полезным командам и закрепляет навык дрессировки", r"Training dog (\1) useful commands and reinforcing obedience skills"),
    (r"(?i)тренирует собаку \((.+?)\) прыгать через барьеры на полосе препятствий", r"Training dog (\1) to jump hurdles on agility obstacle course"),
    (r"(?i)направляет собаку \((.+?)\) в тренировочный туннель на полосе препятствий", r"Guiding dog (\1) through training tunnel on agility course"),
    (r"(?i)тренирует собаку \((.+?)\) огибать слаломные стойки на полосе препятствий", r"Training dog (\1) to navigate slalom weave poles on agility course"),
    (r"(?i)проводит собаку \((.+?)\) по полосе препятствий на лучшее время", r"Running dog (\1) through agility obstacle course for best time"),

    # Care & Walking
    (r"(?i)бегает трусцой на бодрой утренней пробежке вместе с собакой \((.+?)\)", r"Briskly jogging together with dog (\1)"),
    (r"(?i)гуляет с собакой \((.+?)\) на поводке по живописным улочкам", r"Walking dog (\1) on a leash along scenic streets"),
    (r"(?i)обрабатывает шерсть питомца \((.+?)\) специальным шампунем от блох", r"Treating pet's fur (\1) with special flea shampoo"),
    (r"(?i)купает собаку \((.+?)\) в теплой ванне с мыльной пеной", r"Giving dog (\1) a warm bath with soapy suds"),
    (r"(?i)заботливо вычесывает шерсть питомца \((.+?)\) мягкой щеткой", r"Gently brushing pet's coat (\1) with soft brush"),
    (r"(?i)угощает питомца \((.+?)\) аппетитным лакомством", r"Giving delicious treat to pet (\1)"),
    (r"(?i)строго отчитывает питомца \((.+?)\) за непослушание и плохие манеры", r"Firmly scolding pet (\1) for misbehavior and poor manners"),
    (r"(?i)ласково хвалит и поглаживает питомца \((.+?)\) за послушание", r"Affectionately praising and petting pet (\1) for good behavior"),

    # Play & Bonding
    (r"(?i)дразнит кошку \((.+?)\) красной точкой лазерной указки", r"Playing with cat (\1) using red laser pointer dot"),
    (r"(?i)играет с кошкой \((.+?)\) гибкой дразнилкой с перышками", r"Playing with cat (\1) with feather wand teaser"),
    (r"(?i)угощает кошку \((.+?)\) душистой кошачьей мятой", r"Treating cat (\1) with fragrant catnip"),
    (r"(?i)бросает мячик и с азартом играет в апорт с собакой \((.+?)\)", r"Throwing ball playing fetch excitedly with dog (\1)"),
    (r"(?i)запускает летающую тарелку \(фрисби\) в воздух для собаки \((.+?)\)", r"Throwing flying frisbee disc into air for dog (\1)"),
    (r"(?i)умиленно чешет пузико и бока лежащему питомцу \((.+?)\)", r"Lovingly rubbing belly and sides of resting pet (\1)"),
    (r"(?i)с любовью обнимает и прижимает к себе четвероногого друга \((.+?)\)", r"Lovingly hugging and cuddling four-legged friend (\1)"),

    # Lighthouse & Strays
    (r"(?i)официально усыновляет и принимает в семью бездомного питомца \((.+?)\)", r"Officially adopting stray pet (\1) into the family"),

    # Social Dialogues EP04
    (r"(?i)обучает командам и трюкам питомца по кличке\s*", "Training commands and tricks to pet named "),
    (r"(?i)гуляет на поводке с четвероногим другом по кличке\s*", "Walking on leash with four-legged friend named "),
    (r"(?i)заботливо вычесывает щеткой шерсть любимца\s*", "Gently brushing coat of pet "),
    (r"(?i)купает в теплой ванне четвероногого друга по кличке\s*", "Bathing in warm bath four-legged friend named "),
    (r"(?i)угощает аппетитным лакомством любимца по кличке\s*", "Giving delicious treat to pet named "),
    (r"(?i)строго отчитывает за плохое поведение питомца по кличке\s*", "Firmly scolding for misbehavior pet named "),
    (r"(?i)ласково гладит и хвалит за послушание питомца по кличке\s*", "Gently praising for obedience pet named "),
    (r"(?i)дразнит красной точкой лазерной указки любимца\s*", "Playing with red laser pointer with pet "),
    (r"(?i)бросает мяч и играет в апорт с четвероногим другом\s*", "Throwing ball playing fetch with four-legged friend "),
    (r"(?i)проводит профессиональный ветеринарный осмотр питомца\s*", "Performing professional vet examination on pet "),
    (r"(?i)проводит сложную хирургическую операцию четвероногому пациенту\s*", "Performing complex surgery on four-legged patient "),

    # EP05 Seasons: Weather, Holidays, Skating, Bees, Floristry, Scarecrow, Traditions
    # Weather & Climate
    (r"(?i)в шоке и копоти:\s*в сима только что ударила настоящая молния!", "Shocked and covered in soot: Sim was just struck by lightning!"),
    (r"(?i)в панике вздрагивает от раскатов грома и прячется от грозы", "Panicking and cowering from thunder, hiding from thunderstorm"),
    (r"(?i)радостно бегает и плещется в дождевых лужах", "Happily splashing and playing in rain puddles"),
    (r"(?i)весело шлепает по грязным лужам и пачкается в лечебной грязи", "Cheerfully stomping in mud puddles and getting muddy"),
    (r"(?i)идет под раскрытым зонтом, укрываясь от дождя", "Walking under an open umbrella shielding from the rain"),
    (r"(?i)дрожит от пронизывающего ледяного холода и пытается согреться", "Shivering from freezing cold and trying to warm up"),
    (r"(?i)изнывает от невыносимой палящей жары и обливается потом", "Sweating and suffering from intense sweltering heatwave"),
    (r"(?i)загорает на солнышке в шезлонге или на полотенце", "Sunbathing in the sun on a lounge chair or towel"),

    # Winter & Snow
    (r"(?i)лепит снеговика вместе с (.+)", r"Building a snowman together with \1"),
    (r"(?i)лепит снеговика из свежевыпавшего снега", "Building a snowman out of fresh snow"),
    (r"(?i)лежит на сугробе и делает снежного ангела", "Lying on a snowdrift making a snow angel"),
    (r"(?i)азартно играет в снежки против (.+)", r"Playfully having a snowball fight against \1"),
    (r"(?i)азартно играет в снежки и лепит снежные комья", "Playfully having a snowball fight and making snowballs"),
    (r"(?i)счищает лопатой сугробы снега с дорожек вокруг дома", "Shoveling snowdrifts from walkways around the house"),

    # Autumn Leaves & Raking
    (r"(?i)весело прыгает и играет в куче осенних листьев вместе с (.+)", r"Playfully jumping and frolicking in autumn leaf pile together with \1"),
    (r"(?i)весело прыгает и играет в шуршащей куче осенних листьев", "Playfully jumping and frolicking in rustling autumn leaf pile"),
    (r"(?i)сжигает собранную кучу сухих осенних листьев", "Burning a collected pile of dry autumn leaves"),
    (r"(?i)сгребает сухие осенние листья граблями вместе с (.+)", r"Raking dry autumn leaves together with \1"),
    (r"(?i)сгребает сухие осенние листья граблями в аккуратную кучу", "Raking dry autumn leaves into a neat pile"),

    # Seasonal Sports & Cooling Off
    (r"(?i)неловко теряет равновесие и шлепается на ледовом катке", "Awkwardly losing balance and falling on the ice skating rink"),
    (r"(?i)выполняет изящные фигурные вращения и пируэты на катке", "Performing graceful figure skating spins and routines on the rink"),
    (r"(?i)катается на роликах по треку вместе с (.+)", r"Roller skating on the track together with \1"),
    (r"(?i)катается на роликах по треку, отрабатывая скольжение", "Roller skating on the track practicing gliding"),
    (r"(?i)катается на коньках по ледовому катку вместе с (.+)", r"Ice skating on the rink together with \1"),
    (r"(?i)катается на коньках по ледовому катку, нарезая круги", "Ice skating on the rink doing laps"),
    (r"(?i)устраивает задорный бой водяными шариками против (.+)", r"Playfully having a water balloon fight against \1"),
    (r"(?i)задорно бросает шарики с водой и устраивает водяной бой", "Throwing water balloons and having a water balloon fight"),
    (r"(?i)освежается и плещется в надувном детском бассейне", "Cooling off and splashing in inflatable kiddie pool"),
    (r"(?i)с визгом пробегает через разбрызгиватель для газона, спасаясь от жары", "Playfully running through lawn sprinkler cooling off from the heat"),
    (r"(?i)регулирует домашний термостат \(настраивает обогрев / кондиционер\)", "Adjusting home thermostat (setting heating / air conditioning)"),

    # Weather Controller
    (r"(?i)вызывает сокрушительную грозу на пульте управления погодой", "Triggering a devastating thunderstorm using the weather controller"),
    (r"(?i)вызывает снежную бурю с помощью погодного контроллера", "Summoning a blizzard using the weather controller"),
    (r"(?i)вызывает аномальную жару с помощью погодного контроллера", "Summoning a heatwave using the weather controller"),
    (r"(?i)перенастраивает климат с помощью фантастического аппарата управления погодой", "Changing the climate using Dr. June's weather machine"),

    # Floristry, Bees & Scarecrow
    (r"(?i)окуривает и ароматизирует цветочную композицию редким цветочным ароматом", "Scenting floral arrangement with rare floral fragrance"),
    (r"(?i)составляет изысканную цветочную композицию на столике флориста", "Creating an exquisite floral arrangement on the flower table"),
    (r"(?i)собирает свежий душистый мед из пчелиного улья", "Collecting fresh fragrant honey from the bee box"),
    (r"(?i)налаживает гармоничную связь с пчелиной семьей в улье", "Bonding with the bee colony in the bee box"),
    (r"(?i)натравливает рой верных жужжащих пчел на (.+)", r"Sending a swarm of buzzing bees to attack \1"),
    (r"(?i)отправляет рой верных пчел с особым поручением", "Sending a swarm of faithful bees on a special errand"),
    (r"(?i)отмахивается от разгневанного роя пчел и чешет укусы", "Swatting away angry swarm of bees and scratching stings"),
    (r"(?i)бережно ухаживает за пчелиным ульем в защитном костюме пасечника", "Tending bee box in protective beekeeper suit"),
    (r"(?i)проверяет карманы пугала заплатки в поисках редких семян", "Checking Patchy the Scarecrow's pockets for rare seeds"),
    (r"(?i)оживленно беседует и дружит с ожившим пугалом по имени заплатка", "Chatting and befriending Patchy the Straw Man scarecrow"),

    # Holidays, Father Winter & Traditions
    (r"(?i)яростно дерется с (.+?) за мешок с заветными подарками!", r"Furiously fighting with \1 for the bag of holiday presents!"),
    (r"(?i)яростно дерется с дедом морозом за мешок с подарками!", "Furiously fighting with Father Winter for the bag of presents!"),
    (r"(?i)просит праздничный подарок у (.+)", r"Asking \1 for a holiday present"),
    (r"(?i)просит праздничный подарок у деда мороза", "Asking Father Winter for a holiday present"),
    (r"(?i)радушно встречает (.+?) в праздничный вечер", r"Warmly welcoming \1 on holiday evening"),
    (r"(?i)общается с дедом морозом в праздничный вечер", "Socializing with Father Winter on holiday evening"),
    (r"(?i)наряжает праздничную елку гирляндами и игрушками вместе с (.+)", r"Decorating the holiday tree with ornaments together with \1"),
    (r"(?i)наряжает праздничную елку гирляндами и яркими игрушками", "Decorating the holiday tree with garlands and ornaments"),
    (r"(?i)с нетерпением распаковывает праздничный подарок под елкой", "Eagerly unwrapping holiday present under the tree"),
    (r"(?i)торжественно вручает праздничный подарок для (.+)", r"Presenting a holiday gift to \1"),
    (r"(?i)вручает праздничный подарок", "Giving a holiday gift"),
    (r"(?i)достает праздничные гирлянды и украшения из чердачной коробки с декором", "Retrieving holiday decorations from the attic decoration box"),
    (r"(?i)готовит пышное праздничное застолье \(грандиозный ужин\)", "Cooking a grand holiday feast for family and guests"),
    (r"(?i)зажигает праздничные свечи на традиционной меноре / кинаре", "Lighting holiday candles on traditional menorah / kinara"),
    (r"(?i)радостно поет праздничные песни вместе с (.+)", r"Joyfully singing holiday songs together with \1"),
    (r"(?i)радостно поет праздничные гимны и песни", "Joyfully singing holiday carols and songs"),
    (r"(?i)с замиранием сердца смотрит новогодний обратный отсчет до полуночи", "Watching New Year's countdown to midnight on TV"),
    (r"(?i)дает себе твердое новогоднее обещание изменить жизнь к лучшему", "Making a New Year's resolution to improve life"),
    (r"(?i)приветствует сказочного цветочного кролика \((.+?)\)", r"Greeting the magical Flower Bunny (\1)"),
    (r"(?i)приветствует сказочного цветочного кролика и берет цветы", "Greeting the magical Flower Bunny and receiving flowers"),

    # Social Dialogues EP05
    (r"(?i)азартно играет в снежки против\s*", "Playfully having a snowball fight against "),
    (r"(?i)устраивает задорный бой водяными шариками против\s*", "Having a water balloon fight against "),
    (r"(?i)торжественно вручает праздничный подарок для\s*", "Presenting a holiday gift to "),
    (r"(?i)выпрашивает новогодний подарок у\s*", "Asking for a holiday present from "),
    (r"(?i)яростно дерется за мешок с подарками с\s*", "Furiously fighting for present sack with "),
    (r"(?i)оживленно болтает о саде и урожае с пугалом по имени\s*", "Chatting about garden and crops with scarecrow named "),
    (r"(?i)натравливает рой жужжащих пчел на\s*", "Sending a swarm of buzzing bees at "),
    (r"(?i)поет праздничные новогодние песни вместе с\s*", "Singing holiday songs together with "),

    # EP06 Get Famous: Acting, Studio, Media, Music, Drone, Fame, Vault, Paparazzi
    # Acting Career & Studio
    (r"(?i)наносит профессиональный сценический грим актеру \((.+?)\)", r"Applying professional stage makeup to actor (\1)"),
    (r"(?i)работает стилистом-гримером на съемочной площадке", "Working as hair and makeup stylist on movie set"),
    (r"(?i)сидит в кресле стилиста на киностудии:\s*наносит сценический грим и делает прическу", "Sitting in hair and makeup chair on movie set getting styled"),
    (r"(?i)примеряет сценический костюм для съемок на костюмерном подиуме", "Trying on stage costume on wardrobe pedestal"),
    (r"(?i)докладывает режиссеру \((.+?)\) о полной готовности к съемкам сцены", r"Informing director (\1) ready to perform scene on set"),
    (r"(?i)докладывает режиссеру о готовности к съемкам сцены", "Informing director ready to perform scene on set"),
    (r"(?i)играет сцену поединка перед кинокамерой против (.+)", r"Performing duel / combat scene in front of camera against \1"),
    (r"(?i)играет зрелищную сцену поединка перед кинокамерой", "Performing spectacular combat scene in front of movie camera"),
    (r"(?i)играет романтическую сцену с поцелуем перед камерой вместе с (.+)", r"Performing romantic kissing scene on camera together with \1"),
    (r"(?i)играет чувственную романтическую сцену перед кинокамерой", "Performing sensual romantic scene in front of movie camera"),
    (r"(?i)произносит драматический монолог перед кинокамерой на съемочной площадке", "Delivering dramatic monologue in front of movie camera on set"),
    (r"(?i)отыгрывает уморительную комедийную сцену перед кинокамерой", "Delivering hilarious comedy scene in front of movie camera"),
    (r"(?i)исполняет музыкальный номер с пением и танцем перед камерой", "Performing musical number with singing and dancing on camera"),
    (r"(?i)отыгрывает ключевую сцену дубля на съемочной площадке киностудии", "Performing scene take on movie studio set"),
    (r"(?i)усердно репетирует драматическую роль и отрабатывает мимику перед зеркалом", "Practicing dramatic acting role and expressions in the mirror"),
    (r"(?i)снимается в фантастической сцене на фоне зеленого экрана хромакея", "Acting in sci-fi scene in front of green screen"),

    # Media Production, Music & Drone
    (r"(?i)монтирует свежий видеоролик,\s*добавляя динамичные переходы и спецэффекты", "Editing fresh video adding transitions and visual effects"),
    (r"(?i)загружает смонтированный видеоролик на популярную медиаплатформу", "Uploading edited video to popular media platform"),
    (r"(?i)записывает эмоциональное видеопрохождение компьютерной игры для своего влога", "Recording emotional gaming walkthrough video for vlog"),
    (r"(?i)записывает модный видеообзор и советы по красоте для подписчиков", "Recording fashion beauty review video for subscribers"),
    (r"(?i)записывает яркий видеоролик за профессиональным столом медиапроизводства", "Recording video at professional media production station"),
    (r"(?i)записывает готовый музыкальный трек на диск для отправки на лейбл", "Burning finished music track to CD to send to record label"),
    (r"(?i)создает и сводит авторский электронный музыкальный трек в студии", "Producing and mixing original electronic track in music studio"),
    (r"(?i)ведет прямой эфир \(стрим\) в сеть с помощью парящего вокруг дрона", "Livestreaming with flying streaming drone"),
    (r"(?i)записывает видеоматериалы для блога с помощью летающего стримингового дрона", "Recording blog footage with flying streaming drone"),

    # Celebrity Life & Paparazzi
    (r"(?i)азартно фотографирует знаменитость \((.+?)\) под вспышками камер", r"Snapping sensational photos of celebrity (\1) under flashing cameras"),
    (r"(?i)ловит сенсационные кадры знаменитостей под прицелом объектива", "Snapping photos of celebrities under flashing paparazzi cameras"),
    (r"(?i)эффектно позирует папарацци на красной дорожке под вспышки фотокамер", "Striking glamorous poses for paparazzi on the red carpet"),
    (r"(?i)раздает именные автографы восторженным поклонникам \((.+?)\)", r"Signing autographs for excited fans (\1)"),
    (r"(?i)раздает именные автографы восторженным поклонникам", "Signing autographs for excited fans"),
    (r"(?i)с восторгом выпрашивает автограф у знаменитости \((.+?)\)", r"Excitedly asking celebrity (\1) for an autograph"),
    (r"(?i)с восторгом выпрашивает автограф у знаменитости", "Excitedly asking celebrity for an autograph"),
    (r"(?i)делает памятное звездное селфи вместе с (.+)", r"Taking memorable celebrity selfie together with \1"),
    (r"(?i)делает памятное селфи со знаменитостью", "Taking memorable selfie with celebrity"),
    (r"(?i)прячется от назойливых папарацци и фанатов в темных очках и шляпе", "Hiding from paparazzi and fans in celebrity disguise"),
    (r"(?i)падает в восторженный обморок при виде суперзвезды \((.+?)\)!", r"Fainting in awe upon seeing superstar (\1)!"),
    (r"(?i)падает в восторженный обморок от благоговения перед кумиром", "Fainting in awe upon seeing their celebrity idol"),
    (r"(?i)одержимый назойливый фанат:\s*тайно следит за звездой и роется в мусоре кумира", "Obsessed Stan: secretly stalking celebrity and rummaging through trash"),
    (r"(?i)пытается очаровать или подкупить строгого вышибалу \((.+?)\) у входа в vip-зону", r"Trying to charm or bribe strict bouncer (\1) at VIP entrance"),
    (r"(?i)пытается проскользнуть мимо вышибалы в элитную vip-зону клуба", "Trying to sneak past bouncer into elite VIP club area"),
    (r"(?i)непреклонно охраняет vip-вход в клуб и отсеивает недостойных посетителей", "Sternly guarding VIP club entrance turning away commoners"),
    (r"(?i)торжественно закладывает свою именную плитку-звезду на звездной аллее славы", "Placing personalized celebrity tile on Starlight Boulevard Walk of Fame"),

    # Money Vault & Luxury
    (r"(?i)сладко дремлет на огромной горе хрустящих купюр и золота в сейфе", "Sleeping peacefully on huge pile of cash and gold in money vault"),
    (r"(?i)купается в роскоши и подбрасывает золотые монеты в денежном хранилище", "Living in luxury playing with gold coins in money vault"),
    (r"(?i)любуется горами своего богатства в бронированном денежном хранилище", "Admiring enormous wealth inside armored money vault"),
    (r"(?i)показно сорит деньгами и разбрасывает пачки наличных перед толпой", "Flaunting wealth making it rain cash in front of the crowd"),

    # Social Dialogues EP06
    (r"(?i)раздает именные автографы для\s*", "Signing autographs for "),
    (r"(?i)с трепетом выпрашивает автограф у\s*", "Asking for an autograph from "),
    (r"(?i)делает памятное совместное селфи со звездой\s*", "Taking memorable selfie with celebrity "),
    (r"(?i)в экстазе падает в обморок от восторга перед\s*", "Fainting in awe before "),
    (r"(?i)показно сорит деньгами и хвастается богатством перед\s*", "Flaunting wealth and making it rain before "),
    (r"(?i)пытается подкупить или убедить пропустить в vip-зону вышибалу в лице\s*", "Trying to bribe or convince VIP bouncer "),
    (r"(?i)докладывает о готовности к съемке сцены режиссеру в лице\s*", "Reporting ready to perform scene to director "),
    (r"(?i)берет эксклюзивное интервью для сми у знаменитости\s*", "Conducting exclusive media interview with celebrity "),

    # EP07 Island Living: Mermaids, Dolphins, Aqua Zip, Canoe, Scuba, Beach, Volcano, Kava
    # Mermaids & Sirens
    (r"(?i)заманивает (.+?) гипнотической песней сирены на океанскую глубину", r"Luring \1 into the ocean depths with hypnotic Siren's Call"),
    (r"(?i)поет чарующую колыбельную русалки для (.+)", r"Singing Charmer's Lullaby to \1"),
    (r"(?i)поет вдохновляющую русалочью песню для (.+)", r"Singing Inspiring Berceuse to \1"),
    (r"(?i)наводит океанский ужас и тоску реквиемом ночи на (.+)", r"Casting terror with Night's Requiem on \1"),
    (r"(?i)утягивает (.+?) на дно океана русалочьей хваткой!", r"Dragging \1 down to the ocean floor with a mermaid grip!"),
    (r"(?i)дарит волшебный океанский русалочий поцелуй для (.+)", r"Giving a magical mermaid kiss to \1"),

    # Dolphins & Turtles
    (r"(?i)обучает дельфина( по имени .+?)?(\s*\(дельфин-альбинос\))? акробатическим трюкам и сальто", r"Teaching dolphin\1\2 acrobatic tricks and flips"),
    (r"(?i)кормит свежей рыбой из рук дружелюбного дельфина( по имени .+?)?(\s*\(дельфин-альбинос\))?", r"Feeding fresh fish by hand to friendly dolphin\1\2"),
    (r"(?i)ласково гладит дельфина( по имени .+?)?(\s*\(дельфин-альбинос\))? по шелковистой гладкой спине", r"Gently petting dolphin\1\2 on its silky smooth back"),
    (r"(?i)дружелюбно переговаривается и обменивается щелчками с дельфином( по имени .+?)?(\s*\(дельфин-альбинос\))?", r"Chatting and clicking friendly sounds with dolphin\1\2"),
    (r"(?i)весело играет и плещется в теплых волнах с дельфином( по имени .+?)?(\s*\(дельфин-альбинос\))?", r"Playing and splashing in warm waves with dolphin\1\2"),
    (r"(?i)задорно брызгается океанской водой с дельфином( по имени .+?)?(\s*\(дельфин-альбинос\))?", r"Playfully splashing ocean water with dolphin\1\2"),
    (r"(?i)получает мокрый дружеский поцелуй в щеку от дельфина( по имени .+?)?(\s*\(дельфин-альбинос\))?", r"Receiving a wet friendly cheek kiss from dolphin\1\2"),
    (r"(?i)восхищенно общается с дельфином( по имени .+?)?(\s*\(дельфин-альбинос\))? в океане", r"Enthusiastically interacting with dolphin\1\2 in the ocean"),

    # Beach & Sand
    (r"(?i)шутливо закапывает (.+?) по горло в пляжный песок", r"Playfully burying \1 up to the neck in beach sand"),

    # Kava & Culture
    (r"(?i)произносит традиционный островной тост «була!» и пьет каву с (.+)", r"Raising a traditional 'Bula!' toast and drinking kava with \1"),
    (r"(?i)рассказывает древние предания и мифы сулани для (.+)", r"Sharing ancient Sulani island folklore with \1"),

    # Social Dialogues EP07
    (r"(?i)произносит традиционный островной тост с чашей кавы для\s*", "Raising a traditional kava toast for "),
    (r"(?i)приглашает на традиционный островной праздник кавы\s*", "Inviting to a traditional kava party "),
    (r"(?i)дружелюбно щелкает и переговаривается с дельфином по имени\s*", "Clicking and chatting with dolphin named "),
    (r"(?i)кормит свежей рыбой из рук дельфина по имени\s*", "Feeding fresh fish by hand to dolphin named "),
    (r"(?i)нежно гладит по гладкой спине дельфина по имени\s*", "Gently petting on the back dolphin named "),
    (r"(?i)весело играет и плещется в волнах с дельфином по имени\s*", "Splashing and playing in waves with dolphin named "),
    (r"(?i)дарит волшебный океанский русалочий поцелуй для\s*", "Giving a magical mermaid kiss to "),
    (r"(?i)заманивает чарующей песней сирены на глубину океана\s*", "Luring into ocean depths with Siren's Call "),
    (r"(?i)поет чарующую колыбельную русалки для\s*", "Singing Charmer's Lullaby to "),
    (r"(?i)поет вдохновляющую русалочью песню для\s*", "Singing Inspiring Berceuse to "),
    (r"(?i)рассказывает древние предания и мифы сулани для\s*", "Sharing ancient Sulani folklore with "),
    (r"(?i)расспрашивает о традициях и духах архипелага сулани у\s*", "Asking about Sulani traditions and spirits from "),
    (r"(?i)шутливо закапывает в теплый пляжный песок\s*", "Playfully burying in warm beach sand "),

    # EP08 Discover University: Academics, Robotics, Servos, Bicycles, Keg, Ping Pong, Sprites
    # Academics & Debate
    (r"(?i)участвует в жарких академических дебатах на трибуне против (.+)", r"Engaging in heated academic debate at podium against \1"),

    # Robotics & Servos
    (r"(?i)проводит тонкую настройку и улучшение робота серво в лице (.+)", r"Fine-tuning and enhancing Servo robot \1"),
    (r"(?i)ремонтирует поврежденные сервоприводы робота серво в лице (.+)", r"Repairing damaged servomotors of Servo robot \1"),

    # Keg & Games
    (r"(?i)выполняет безумную стойку на руках на бочонке сока \(keg stand\) при поддержке (.+?)!", r"Performing a wild Keg Stand handstand on juice keg supported by \1!"),
    (r"(?i)азартно играет в студенческий сок-понг против (.+)", r"Competitively playing campus juice pong against \1"),
    (r"(?i)сражается в динамичный настольный теннис \(пинг-понг\) против (.+)", r"Playing fast-paced ping pong against \1"),

    # Social Dialogues EP08
    (r"(?i)вступает в жаркий академический спор и дебаты с\s*", "Engaging in heated academic debate with "),
    (r"(?i)убеждает железными логическими аргументами и риторикой\s*", "Convincing with airtight logical rhetoric "),
    (r"(?i)громко скандирует университетскую кричалку вместе с\s*", "Loudly chanting university fight song with "),
    (r"(?i)яростно спорит об итоговой оценке за курс с преподавателем\s*", "Arguing fiercely about final course grade with professor "),
    (r"(?i)поднимает студенческий пластиковый стаканчик с соком за\s*", "Raising a plastic cup juice toast to "),
    (r"(?i)шепотом расспрашивает о тайном студенческом обществе у\s*", "Whispering questions about secret society to "),
    (r"(?i)язвительно высмеивает команду соперничающего университета перед\s*", "Taunting rival university team before "),

    # EP09 Eco Lifestyle: Dumpster, Fabricator, Candle, Fizz, Insects, Meat Wall, Solar, Smog
    # Social Dialogues EP09
    (r"(?i)активно агитирует голосовать за комплекс мер района\s*", "Actively campaigning for Neighborhood Action Plan "),
    (r"(?i)собирает подписи за отмену комплекса мер у\s*", "Gathering signatures to repeal Neighborhood Action Plan from "),
    (r"(?i)с восторгом рассказывает о раздельном сборе мусора и переработке для\s*", "Enthusiastically sharing recycling tips with "),
    (r"(?i)гордо хвастается жизнью без отходов и фриганизмом перед\s*", "Proudly bragging about zero-waste lifestyle and freeganism to "),
    (r"(?i)с негодованием жалуется на удушливый смог и грязь в районе для\s*", "Complaining about industrial smog and pollution to "),
    (r"(?i)угощает искрящейся домашней шипучкой собственного разлива\s*", "Offering homemade fizzy juice to "),
    (r"(?i)делится секретами свечеварения и создания ароматических свечей с\s*", "Sharing candle making secrets with "),

    # EP10 Snowy Escape: Winter Sports, Onsen, Kotatsu, Hiking, Yamachan
    # Social Dialogues EP10
    (r"(?i)с уважением и глубоким почтением кланяется\s*", "Bowing respectfully and deeply to "),
    (r"(?i)с восхищением рассказывает о заснеженных вершинах комореби для\s*", "Admiringly talking about the snowy peaks of Mt. Komorebi to "),
    (r"(?i)приглашает погреться под теплым одеялом котацу и отведать хот-пот\s*", "Inviting to warm up under cozy kotatsu blanket and share hot pot with "),
    (r"(?i)увлеченно обсуждает маршрут горной экспедиции и проверку снаряжения с\s*", "Enthusiastically discussing mountain excursion routes and climbing gear with "),
    (r"(?i)расхваливает целебную расслабляющую силу горячих источников онсэн перед\s*", "Praising healing relaxation of onsen hot springs to "),
    (r"(?i)предостерегает о нападениях лесных шершней и коварных духов на тропе\s*", "Warning about forest hornets and tricky spirits on the trail to "),
    (r"(?i)с возмущением жалуется на застрявшую банку в торговом автомате для\s*", "Indignantly complaining about a stuck can in the vending machine to "),

    # EP11 Cottage Living: Animals, Cows, Llamas, Chickens, Giant Crops, Cross-Stitch, Canning
    # Social Dialogues EP11
    (r"(?i)с восторгом рассказывает о жизни на ферме и сельских заботах для\s*", "Enthusiastically sharing farm life stories and rustic chores with "),
    (r"(?i)делится секретами выращивания гигантских овощей и ухода за огородом с\s*", "Sharing giant vegetable growing secrets and gardening tips with "),
    (r"(?i)гордо хвастается собранными золотыми и обсидиановыми яйцами перед\s*", "Proudly bragging about golden and obsidian eggs to "),
    (r"(?i)предупреждает о коварных лисах, охотящихся на курятники, для\s*", "Warning about crafty foxes stalking hen coops to "),
    (r"(?i)с гордостью демонстрирует вышитую крестиком картину\s*", "Proudly showing off framed cross-stitch needlework to "),
    (r"(?i)обсуждает поручения местных жителей и ярмарку в финчвике с\s*", "Discussing villager errands and Finchwick Fair with "),
    (r"(?i)с обидой жалуется на плевок вредной ламы для\s*", "Resentfully complaining about llama spit to "),

    # EP12 High School Years: Prom, Academics, Pranks, Trendi, Carnival
    # Social Dialogues EP12
    (r"(?i)торжественно вручает самодельный плакат и приглашает на выпускной бал\s*", "Grandly presenting creative promposal banner asking to prom "),
    (r"(?i)шепотом сплетничает о кандидатах в короли и королевы выпускного бала с\s*", "Whispering prom royalty and jester gossip with "),
    (r"(?i)хвастается продажами стильных луков на тренди и подписчиками перед\s*", "Bragging about Trendi fashion sales and followers to "),
    (r"(?i)с возмущением жалуется на несправедливое школьное наказание после уроков для\s*", "Indignantly complaining about detention after school to "),
    (r"(?i)заговорщицким шепотом рассказывает пугающую городскую легенду для\s*", "Conspiratorially whispering spooky urban myths to "),
    (r"(?i)подговаривает устроить дерзкую проделку в школьном коридоре вместе с\s*", "Conspiring to pull off a daring high school corridor prank with "),
    (r"(?i)приглашает поболтать и выпить сладкий бабл-ти в кафе «чай и тренды»\s*", "Inviting to hang out and sip boba tea at ThriftTea with "),

    # EP13 Growing Together: Family, Milestones, Bracelets, Midlife Crisis, Sleepovers
    (r"(?i)с гордостью рассказывает о новых достижениях и вехах развития малыша для\s*", "Proudly sharing infant milestones and achievements with "),
    (r"(?i)с теплотой предается ностальгическим семейным воспоминаниям вместе с\s*", "Warmly reminiscing about nostalgic family memories together with "),
    (r"(?i)торжественно повязывает сплетенный вручную браслет дружбы на запястье\s*", "Grandly tying a hand-woven friendship bracelet onto the wrist of "),
    (r"(?i)делится мудрым родительским опытом и тонкостями воспитания детей с\s*", "Sharing wise parenting experience and child-rearing tips with "),
    (r"(?i)искренне исповедуется в душевных терзаниях и кризисе среднего возраста перед\s*", "Sincerely confessing emotional turmoil and midlife crisis to "),
    (r"(?i)с радостью приглашает пожить в гостях с ночевкой на несколько дней\s*", "Joyfully inviting over for a multi-day sleepover stay with "),
    (r"(?i)со смехом и вздохом жалуется на бесконечную смену грязных подгузников для\s*", "Laughingly complaining about endless messy diaper changes to "),

    # EP14 Horse Ranch: Horses, Derbies, Nectar, Goats, Cowboy Stories
    (r"(?i)с гордостью хвастается победами в конных дерби и навыками верховой езды перед\s*", "Proudly bragging about equestrian derby wins and riding skills to "),
    (r"(?i)делится секретами выездки, конкура и тренировки скакунов с\s*", "Sharing dressage, show jumping, and horse training secrets with "),
    (r"(?i)торжественно поднимает бокал выдержанного нектара и произносит душевный тост за\s*", "Grandly raising a glass of aged nectar and proposing a heartfelt toast to "),
    (r"(?i)с умилением восторгается очаровательными мини-козочками и овечками для\s*", "Gushing fondly about adorable mini goats and sheep to "),
    (r"(?i)увлекательно рассказывает старую ковбойскую байку каньона честнат-ридж для\s*", "Telling a thrilling old Chestnut Ridge cowboy tale to "),
    (r"(?i)ворчливо жалуется на тяжелую чистку стойла от конского навоза для\s*", "Grumpily complaining about mucking out heavy horse manure to "),
    (r"(?i)со знанием дела обсуждает тонкости купажа и выдержки нектара с\s*", "Expertly discussing nectar vintage, blends, and aging with "),

    # EP15 For Rent: Blackmail, Secrets, Landlord, Eviction, Tenant Strike
    (r"(?i)зловеще шантажирует выведанной компрометирующей тайной\s*", "Sinisterly blackmailing with an uncovered secret "),
    (r"(?i)в лицо обвиняет и уличает в скрытой постыдной тайне\s*", "Directly confronting about a shameful hidden secret "),
    (r"(?i)искренне и со стыдом признается в сокровенной тайне перед\s*", "Sincerely and shamefully confessing a secret to "),
    (r"(?i)пытается вручить взятку арендодателю за снижение арендной платы для\s*", "Attempting to bribe landlord for reduced rent to "),
    (r"(?i)в ярости угрожает немедленным выселением из арендованной квартиры для\s*", "Furiously threatening immediate eviction from rental unit to "),
    (r"(?i)возмущенно жалуется на завышенную стоимость аренды и плесень в жилье для\s*", "Indignantly complaining about overpriced rent and mold to "),
    (r"(?i)подбивает соседей объявить бойкот арендодателю и устроить бунт арендаторов вместе с\s*", "Inciting neighbors to boycott landlord and stage tenant strike together with "),

    # EP16 Lovestruck: Attraction, Turn-ons, Couples Therapy, Pillow Talk, Cupid's Corner
    (r"(?i)игриво интересуется романтическими предпочтениями и тем, что возбуждает и привлекает\s*", "Playfully asking about romantic turn-ons, desires, and attraction with "),
    (r"(?i)откровенно обсуждает уровень романтического удовлетворения и страсти в отношениях с\s*", "Openly discussing romantic satisfaction and relationship passion with "),
    (r"(?i)осторожно предлагает вместе посетить сеанс психотерапии для пар для\s*", "Gently proposing attending couples relationship therapy together to "),
    (r"(?i)чувственно кормит сладкой клубникой в шоколаде с рук\s*", "Sensually hand-feeding chocolate-dipped strawberries to "),
    (r"(?i)хвастается кучей лайков и успешных мэтчей в «уголке купидона» перед\s*", "Bragging about likes and successful matches on Cupid's Corner to "),
    (r"(?i)нежно шепчет сокровенные признания во время интимных разговоров на подушках с\s*", "Tenderly whispering intimate confessions during cozy pillow talk with "),
    (r"(?i)с разочарованием жалуется на провальное свидание и неловкую химию для\s*", "Disappointedly complaining about a disastrous date and bad chemistry to "),

    # EP17 Life & Death: Soul's Journey, Bucket List, Mourning, Wills, Reaper, Tarot
    (r"(?i)философски обсуждает путь души, жизнь после смерти и реинкарнацию с\s*", "Philosophically discussing the soul's journey, afterlife, and reincarnation with "),
    (r"(?i)делится своими заветными предсмертными желаниями из списка души с\s*", "Sharing cherished bucket list aspirations and dreams with "),
    (r"(?i)искренне и чутко соболезнует и утешает в глубокой скорби\s*", "Sincerely offering heartfelt condolences and comforting "),
    (r"(?i)хвастается пунктами своего составленного завещания перед\s*", "Boasting about stipulations in drafted will to "),
    (r"(?i)беседует о тайнах загробного мира и работе жнеца смерти с\s*", "Chatting about underworld secrets and the Grim Reaper's work with "),
    (r"(?i)в отчаянии молит пощадить жизнь и не забирать душу перед\s*", "Desperately pleading to spare the life and not take the soul before "),
    (r"(?i)делает таинственный расклад карт таро, предсказывая грядущую судьбу для\s*", "Performing a mysterious Tarot card reading, foretelling future destiny for "),

    # EP18 Businesses & Hobbies: Pottery, Tattoos, Small Business, Mentorship, Craftsmanship
    (r"(?i)с увлечением обсуждает лепку из глины, глазурь и гончарное ремесло с\s*", "Enthusiastically discussing clay modeling, glazes, and pottery with "),
    (r"(?i)с гордостью демонстрирует свежую татуировку и обсуждает эскизы перед\s*", "Proudly showing off fresh tattoo and discussing sketches with "),
    (r"(?i)с энтузиазмом презентует перспективную идею малого бизнеса для\s*", "Enthusiastically pitching a promising small business idea to "),
    (r"(?i)ведет деловые переговоры о совместном коммерческом проекте и партнерстве с\s*", "Conducting business negotiations on a joint commercial venture with "),
    (r"(?i)с досадой жалуется на капризных и придирчивых клиентов малого бизнеса для\s*", "Frustratedly complaining about finicky small business customers to "),
    (r"(?i)рекомендует опытного наставника и курсы повышения мастерства для\s*", "Recommending an experienced mentor and skill masterclasses to "),
    (r"(?i)искренне восхищается безупречным ручным мастерством и талантом\s*", "Sincerely admiring exquisite handmade craftsmanship and talent of "),

    # EP19 Enchanted Nature: Fairies, Nature Magic, Apothecary, Forest Lore
    (r"(?i)с упоением рассказывает предания о лесных феях и скрытых тропах для\s*", "Enthusiastically sharing folklore about woodland fairies and hidden trails with "),
    (r"(?i)увлеченно рассуждает о равновесии стихий и древней магии природы с\s*", "Passionately debating balance of elements and ancient nature magic with "),
    (r"(?i)делится тайными рецептами травяных отваров и эликсиров природы с\s*", "Sharing secret recipes of herbal brews and nature elixirs with "),
    (r"(?i)восхищается изящной формой и волшебным сиянием крыльев перед\s*", "Admiring delicate shape and magical luminescence of fairy wings before "),
    (r"(?i)предостерегает о коварных проделках духов леса и ловушках кругов фей\s*", "Warning about tricky woodland spirit pranks and perilous fairy rings to "),
    (r"(?i)горячо призывает беречь заповедную природу и вековые леса в разговоре с\s*", "Passionately advocating conservation of pristine nature and ancient forests with "),

    # Jungle Adventure / Adventure: Selvadorada, Omiscan Lore, Archaeology
    (r"(?i)с горящими глазами рассказывает об опасностях и скрытых тропах джунглей для\s*", "Eagerly describing hazards and hidden trails of the jungle to "),
    (r"(?i)повествует о величии, храмах и мистических тайнах народа омиска для\s*", "Recounting legends of greatness and mystical secrets of Omiscan civilization to "),
    (r"(?i)с азартом делится смелыми гипотезами об археологических раскопках с\s*", "Enthusiastically sharing bold theories on archaeological discoveries with "),
    (r"(?i)предостерегает о коварных ловушках и ядовитых дротиках древнего храма\s*", "Warning about perilous traps and venomous darts of ancient temple to "),
    (r"(?i)знакомит с колоритными обычаями и традициями сельвадорады в беседе с\s*", "Sharing vibrant customs and folklore of Selvadorada in conversation with "),
    (r"(?i)с гордостью хвастается найденным в руинах бесценным золотым артефактом перед\s*", "Proudly boasting about priceless golden artifact recovered from ruins before "),

    # EP20 Through the Ages: Time Travel, Eras, Chivalry, Antiquities, Courtly Etiquette
    (r"(?i)с восторгом рассказывает об удивительных путешествиях сквозь века и эпохи для\s*", "Enthusiastically describing thrilling journeys through the ages and eras to "),
    (r"(?i)с жаром спорит о парадоксах времени и альтернативных ветвях истории с\s*", "Passionately debating time paradoxes and alternate historical timelines with "),
    (r"(?i)искренне восхищается подлинным старинным антиквариатом и нарядами былых эпох перед\s*", "Sincerely admiring authentic vintage antiquities and historic attire before "),
    (r"(?i)с почтением расспрашивает о тайнах предков и древнем происхождении рода у\s*", "Respectfully inquiring about ancestral secrets and ancient noble lineage of "),
    (r"(?i)предостерегает об угрозе разрушения пространственно-временного континуума для\s*", "Warning about the peril of destabilizing the space-time continuum to "),
    (r"(?i)с изяществом обучает манерам и благородному куртуазному этикету\s*", "Gracefully teaching noble courtly manners and aristocratic etiquette to "),

    # GP01 Outdoor Retreat: Camping Lore, Herbalism, Granite Falls, Survival
    (r"(?i)с упоением рассказывает захватывающие походные байки для\s*", "Enthusiastically sharing thrilling camping lore and outdoor tales with "),
    (r"(?i)обсуждает секреты сбора трав и рецепты целебных мазей с\s*", "Discussing herb foraging secrets and healing balm recipes with "),
    (r"(?i)восхищается первозданной природой и соснами гранит фоллз перед\s*", "Admiring pristine nature and towering pines of Granite Falls before "),
    (r"(?i)дает полезные советы по обустройству палаточного лагеря для\s*", "Giving practical tips on setting up campsite and surviving wilderness to "),
    (r"(?i)задорно шутит о встрече с медведем в диком лесу перед\s*", "Playfully joking about running into wild bears in deep woods before "),
    (r"(?i)с восторгом делится наблюдениями за редкими лесными жуками с\s*", "Eagerly discussing sightings of rare woodland insects and beetles with "),

    # GP02 Spa Day: Wellness, Chakras, Spa, Nails, Meditation, Yoga
    (r"(?i)рассуждает о балансе чакр, духовном равновесии и дзен с\s*", "Discussing chakra balance, spiritual harmony and zen with "),
    (r"(?i)с воодушевлением советует свои любимые спа-процедуры и массаж для\s*", "Enthusiastically recommending favorite spa treatments and massages to "),
    (r"(?i)с гордостью демонстрирует свежий безупречный маникюр перед\s*", "Proudly showing off fresh flawless manicure and nail design before "),
    (r"(?i)делится полезными советами по медитации и снятию стресса с\s*", "Sharing helpful meditation and stress-relief tips with "),
    (r"(?i)увлеченно обсуждает пользу асан йоги и дыхательных практик с\s*", "Eagerly discussing the health benefits of yoga poses and breathwork with "),

    # GP03 Dine Out: Gourmet Food, Molecular Recipes, Service, Recommendations, Ratings
    (r"(?i)с упоением обсуждает тренды высокой кухни и гастрономические изыски с\s*", "Enthusiastically discussing haute cuisine trends and gourmet dining with "),
    (r"(?i)увлеченно делится впечатлениями от экспериментальных блюд и молекулярной кухни с\s*", "Eagerly sharing impressions of experimental molecular gastronomy with "),
    (r"(?i)негодует по поводу медлительного официанта и плохого ресторанного сервиса перед\s*", "Venting about slow restaurant service and inattentive waiters before "),
    (r"(?i)с воодушевлением советует свои любимые рестораны и уютные кафе для\s*", "Enthusiastically recommending favorite fine dining restaurants to "),
    (r"(?i)с гордостью хвастается пятизвездочным рейтингом своего ресторана перед\s*", "Proudly boasting about 5-star restaurant rating and culinary prestige before "),

    # GP04 Vampires: Lore, Dark Gift, Garlic/Sun, Plasma Ethics, Grand Master
    (r"(?i)с таинственным видом обсуждает древние вампирические тайны форготн холлоу с\s*", "Mysteriously discussing ancient vampiric secrets of Forgotten Hollow with "),
    (r"(?i)шепотом рассказывает о даре вечной жизни и тонкостях обращения с\s*", "Whispering about the gift of eternity and intricacies of vampire turning with "),
    (r"(?i)раздраженно жалуется на омерзительный запах чеснока и палящее солнце перед\s*", "Irritatedly complaining about repulsive stench of garlic and scorching sunlight before "),
    (r"(?i)философски спорит об этичности испития свежей крови против пакетов с кровью с\s*", "Philosophically debating ethics of fresh blood vs blood packs with "),
    (r"(?i)с высокомерием кичится своим могущественным титулом великого магистра перед\s*", "Arrogantly flaunting powerful Grand Master vampire title before "),

    # GP05 Parenthood: Parenting, Manners, Praise, Curfew Rebellion, Bear Hug
    (r"(?i)просит мудрого родительского совета по воспитанию непослушных детей у\s*", "Asking for wise parenting advice on raising disobedient kids from "),
    (r"(?i)читает строгую нотацию о хороших манерах и послушании для\s*", "Giving a stern lecture on good manners and obedience to "),
    (r"(?i)искренне хвалит за прилежное поведение, помощь по дому и хорошие манеры\s*", "Warmly praising good behaviour, household help, and manners of "),
    (r"(?i)эмоционально бунтует против строгих домашних правил и комендантского часа перед\s*", "Emotionally rebelling against strict rules and curfew before "),
    (r"(?i)крепко и с любовью обнимает, поддерживая в трудную минуту,\s*", "Tightly and lovingly hugging, comforting in difficult moment, "),

    # GP07 StrangerVille: Interrogation, Conspiracies, Military, Praise Mother, Recruit
    (r"(?i)с пристрастием расспрашивает о странностях, спорах и секретной лаборатории у\s*", "Intensely questioning about bizarre oddities, spores, and secret lab with "),
    (r"(?i)шепотом делится безумными конспирологическими теориями о правительственном заговоре с\s*", "Whispering wild conspiracy theories about government plots to "),
    (r"(?i)командным тоном отдает строгий воинский приказ и требует субординации от\s*", "Giving strict military order in commanding tone and demanding subordination from "),
    (r"(?i)с безумным остекленевшим взглядом бормочет о величии материнского растения перед\s*", "Muttering with crazed glassy stare about the glory of the Mother Plant before "),
    (r"(?i)призывает объединить силы для финального штурма кратера и победы над чудовищем\s*", "Rallying forces for final crater assault and defeating the monstrosity with "),

    # GP08 Realm of Magic: Sages, Spells, Potions, Duels, Ascension, Curses
    (r"(?i)с почтением просит мудреца обучить новому могущественному заклинанию у\s*", "Respectfully asking Sage to teach a powerful new spell to "),
    (r"(?i)просит открыть секретный рецепт древнего алхимического зелья у\s*", "Asking to reveal secret recipe of ancient alchemical potion from "),
    (r"(?i)бросает дерзкий вызов на магическую дуэль для\s*", "Challenging to a daring magical duel "),
    (r"(?i)с увлечением обсуждает тонкости магических искусств и волшебные школы с\s*", "Enthusiastically discussing nuances of magic arts and spell schools with "),
    (r"(?i)самонадеянно хвастается своим чародейским превосходством и силой перед\s*", "Arrogantly boasting of spellcaster prowess and might to "),
    (r"(?i)умоляет провести священный обряд посвящения в чародеи перед\s*", "Pleading to perform sacred Rite of Ascension before "),
    (r"(?i)обеспокоенно жалуется на тяжесть и муки темного проклятия для\s*", "Worryingly lamenting heavy burden and torment of dark curse to "),

    # GP09 Star Wars: Journey to Batuu: ID check, Factions, Sabacc, Duel, Mind trick
    (r"(?i)приказывает предъявить идентификационный чип для проверки личности для\s*", "Ordering to present identification chip for ID check to "),
    (r"(?i)пламенно агитирует вступить в тайные ряды сопротивления перед\s*", "Passionately rallying to join secret ranks of Resistance before "),
    (r"(?i)строго требует присягнуть на верность первому ордену и верховному лидеру перед\s*", "Sternly demanding allegiance to First Order and Supreme Leader before "),
    (r"(?i)шепотом предлагает выгодную контрабандную сделку и депешу для\s*", "Whispering lucrative smuggling deal and dispatch to "),
    (r"(?i)предлагает сыграть рискованную партию в сабакк на галактические кредиты для\s*", "Challenging to high-stakes Sabacc card game for galactic credits with "),
    (r"(?i)с шипением активирует световой меч и вызывает на поединок\s*", "Igniting lightsaber with a hiss and challenging to duel "),
    (r"(?i)плавно ведет рукой и применяет ментальное джедайское внушение силы к\s*", "Waving hand smoothly and applying Jedi mental Force mind trick on "),

    # GP10 Dream Home Decorator: Preferences, Reveal, Objects, Trends, Critique, Verdict
    (r"(?i)деликатно расспрашивает о вкусах, любимых цветах и стилях интерьера у\s*", "Delicately asking about preferences, favorite colors, and decor styles from "),
    (r"(?i)торжественно показывает обновленный интерьер и ждет эмоциональной оценки от\s*", "Grandly revealing renovated interior and awaiting emotional reaction from "),
    (r"(?i)с гордостью демонстрирует стильный элемент обновленного декора для\s*", "Proudly showing off stylish piece of renovated decor to "),
    (r"(?i)увлеченно обсуждает тренды дизайна интерьеров и гармонию колористики с\s*", "Enthusiastically discussing interior design trends and color theory with "),
    (r"(?i)профессионально критикует планировку, освещение и сочетание мебели перед\s*", "Professionally critiquing layout, lighting, and furniture harmony before "),
    (r"(?i)с воодушевлением хвастается снимками успешных дизайнерских проектов из портфолио перед\s*", "Excitedly boasting about successful portfolio project photos to "),
    (r"(?i)с замиранием сердца просит вынести окончательный вердикт о ремонте у\s*", "Anxiously asking to deliver final renovation verdict from "),

    # GP11 My Wedding Stories: Tartosa, Roles, Toasts, Vows
    (r"(?i)с трепетом просит стать почетным свидетелем на свадьбе у\s*", "Anxiously asking to be Sim of Honor at wedding from "),
    (r"(?i)просит стать регистратором свадебной церемонии и скрепить союз у\s*", "Asking to officiate wedding ceremony and seal vows from "),
    (r"(?i)с умилением доверяет почетную роль цветочника на свадьбе для\s*", "Fondly entrusting honorary role of flower pal at wedding to "),
    (r"(?i)доверяет священную роль хранителя обручальных колец для\s*", "Entrusting sacred role of ring bearer to "),
    (r"(?i)поднимает бокал игристого нектара и произносит трогательный свадебный тост за\s*", "Raising glass of sparkling nectar and giving touching wedding toast to "),
    (r"(?i)взволнованно делится предсвадебным мандражом и трепетом с\s*", "Nervously sharing wedding jitters and excitement with "),
    (r"(?i)с теплой улыбкой вспоминает трогательные моменты свадебной церемонии с\s*", "Warmly reminiscing about touching wedding ceremony moments with "),

    # GP12 Werewolves: Moonwood Mill, Packs, Howling, Lycanthropy
    (r"(?i)издает раскатистый стайный вой, приветствуя собратьев по стае перед\s*", "Letting out resonant pack howl, greeting packmates before "),
    (r"(?i)по-звериному ласково трется носом и выказывает волчью преданность перед\s*", "Affectionately nuzzling snout and showing wolfish devotion before "),
    (r"(?i)свирепо рычит, обнажая острые клыки и запугивая\s*", "Ferociously growling, baring sharp fangs and intimidating "),
    (r"(?i)с почтением просит принять в ряды волчьей стаи у\s*", "Respectfully asking to join the ranks of the wolf pack from "),
    (r"(?i)вызывает на дружеский тренировочный спарринг оборотней\s*", "Challenging to friendly werewolf sparring practice "),
    (r"(?i)с замиранием сердца признается в нерушимой связи истинной пары предначертанной судьбой перед\s*", "Heartfeltly confessing unbreakable bond of fated mate before "),
    (r"(?i)умоляет одарить даром ликантропии через укус оборотня у\s*", "Pleading to grant gift of lycanthropy through werewolf bite from "),
    (r"(?i)делится секретами обуздания ярости и волчьего темперамента с\s*", "Sharing secrets of taming fury and wolf temperament with "),
    (r"(?i)с тревогой и любопытством расспрашивает о свирепом волке-отшельнике греге у\s*", "Anxiously and curiously inquiring about fierce hermit wolf Greg from "),

    # SP01 Luxury Party Stuff: Glamour, High Society, Toasts, Gossip
    (r"(?i)делает изысканный светский комплимент роскошному вечернему наряду для\s*", "Paying an exquisite high-society compliment on the glamorous evening outfit to "),
    (r"(?i)с упоением обсуждает пикантные светские сплетни высшего общества с\s*", "Enthusiastically discussing juicy high-society gossip with "),
    (r"(?i)самодовольно хвастается размахом вечеринки и роскошным образом жизни перед\s*", "Smugly boasting about lavish party scale and luxurious lifestyle to "),
    (r"(?i)элегантно поднимает хрустальный бокал и произносит изысканный тост за\s*", "Elegantly raising crystal glass and giving glamorous toast to "),
    (r"(?i)утонченно и чарующе флиртует на светском рауте с\s*", "Sophisticatedly and charmingly flirting at high-society cocktail party with "),

    # SP02 Perfect Patio Stuff: Hot Tub, Aromatherapy, BBQ, Patio
    (r"(?i)приглашает окунуться и расслабиться в теплой гидромассажной ванне\s*", "Inviting to soak and unwind in warm bubbly hot tub "),
    (r"(?i)игриво и весело брызгается теплой водой в джакузи на\s*", "Playfully splashing warm water in hot tub at "),
    (r"(?i)романтично шепчет нежные признания под шелест пузырьков джакузи для\s*", "Romantically whispering tender words amid bubbling hot tub jets to "),
    (r"(?i)увлеченно делится любимыми рецептами барбекю, стейков и маринадов с\s*", "Enthusiastically sharing favorite BBQ recipes, steaks and marinades with "),
    (r"(?i)с восхищением хвалит уют и приятную расслабляющую атмосферу патио перед\s*", "Admiringly praising cozy and relaxing patio atmosphere before "),

    # SP03 Cool Kitchen Stuff: Ice cream, flavors, recipes, kitchen design
    (r"(?i)восхищается нежным вкусом домашнего мороженого перед\s*", "Praising the exquisite flavor of homemade ice cream before "),
    (r"(?i)жарко спорит о лучшем вкусе мороженого и выборе между рожком и креманкой с\s*", "Heatedly debating the best ice cream flavor and cone vs bowl with "),
    (r"(?i)шепотом делится секретным рецептом необычного экзотического мороженого с\s*", "Whispering a secret recipe for unusual exotic ice cream to "),
    (r"(?i)с улыбкой предостерегает от коварной заморозки мозга при поедании мороженого для\s*", "Playfully warning about sneaky brain freeze while eating ice cream to "),
    (r"(?i)делает комплимент безупречному дизайну современной кухни и кулинарному вкусу для\s*", "Complimenting the sleek modern kitchen design and culinary taste of "),

    # SP04 Spooky Stuff: Treats, Scares, Ghost Stories, Costumes
    (r"(?i)выпрашивает жуткие праздничные сладости и угощения у\s*", "Begging for festive spooky party sweets and treats from "),
    (r"(?i)внезапно пугает леденящим «бу!» и зловещим оскалом\s*", "Playfully scaring with a chilling 'Boo!' and sinister grin "),
    (r"(?i)с замиранием сердца рассказывает жуткую историю о призраках и духах для\s*", "Breathlessly telling a spooky ghost story to "),
    (r"(?i)восхищается оригинальным и пугающим маскарадным костюмом\s*", "Admiring the creative and eerie costume of "),
    (r"(?i)хвастается своим зловещим праздничным нарядом и пугает образ перед\s*", "Showing off sinister spooky costume and striking a spooky pose before "),

    # SP05 Movie Hangout Stuff: Movies, endings, shushing, sharing popcorn, genres
    (r"(?i)с горящими глазами обсуждает любимый фильм, сюжетные повороты и актёров с\s*", "Enthusiastically discussing favorite movie, plot twists and actors with "),
    (r"(?i)жарко спорит о неоднозначной концовке и скрытом смысле просмотренного фильма с\s*", "Heatedly debating the ambiguous ending and hidden meaning of the movie with "),
    (r"(?i)шикает и просит не шуметь и не спойлерить во время киносеанса\s*", "Shushing and asking to keep quiet and avoid spoilers during movie for "),
    (r"(?i)дружелюбно угощает хрустящим теплым попкорном из своей миски\s*", "Friendlily offering crispy warm popcorn from personal bowl to "),
    (r"(?i)увлеченно спорит о превосходстве любимого кинематографического жанра с\s*", "Passionately arguing superiority of favorite film genre with "),

    # SP06 Romantic Garden Stuff: Poems, well wishes, splashing, statues, confessions
    (r"(?i)шепчет возвышенные романтические стихи среди цветущих роз для\s*", "Whispering poetic romantic verses amidst blooming roses to "),
    (r"(?i)таинственно приглашает загадать совместное желание у колодца желаний\s*", "Mysteriously inviting to make a joint wish at whispering wishing well with "),
    (r"(?i)игриво и задорно окатывает прохладными брызгами из фонтана\s*", "Playfully splashing cool fountain water at "),
    (r"(?i)с упоением обсуждает изящество античных статуй и ландшафтного дизайна с\s*", "Admiringly discussing elegance of antique statues and landscape with "),
    (r"(?i)с трепетом в сердце признаётся в искренних чувствах среди аромата цветов для\s*", "Heartfeltly confessing genuine feelings amid flower blossoms to "),

    # SP07 Kids Room Stuff: Voidcritters, Battle Station, Puppet Theater
    (r"(?i)гордо хвастается редкой карточкой космического монстра перед\s*", "Proudly bragging about rare Voidcritter card to "),
    (r"(?i)азартно вызывает на эпическую карточную дуэль монстров на боевой арене\s*", "Eagerly challenging to an epic Voidcritter battle station duel against "),
    (r"(?i)с горящими глазами обсуждает любимых космических монстров и их стихии с\s*", "Enthusiastically discussing favorite Voidcritters and elements with "),
    (r"(?i)с предвкушением приглашает занять места в зрительном зале на кукольный спектакль\s*", "Excitedly inviting to the puppet theater show: "),
    (r"(?i)восхищается мастерством управления куклами и артистизмом спектакля юного кукловода\s*", "Praising puppeteering skills and theatrical talent of "),

    # SP08 Backyard Stuff: Water slide, bird feeder, wind chimes, lemonade
    (r"(?i)с восторгом хвастается головокружительными трюками на водной дорожке перед\s*", "Excitedly bragging about dizzying water slide tricks to "),
    (r"(?i)азартно предлагает посоревноваться в скорости скольжения на водной дорожке с\s*", "Eagerly challenging to a water slide speed race with "),
    (r"(?i)увлеченно обсуждает виды прилетевших птиц и их повадки у кормушки с\s*", "Enthusiastically discussing visiting bird species and habits at feeder with "),
    (r"(?i)восхищается мелодичным и умиротворяющим звоном колокольчиков ветра для\s*", "Praising melodious and soothing sound of wind chimes to "),
    (r"(?i)с улыбкой предлагает высокий запотевший стакан домашнего холодного лимонада для\s*", "Warmly offering a tall frosted glass of chilled homemade lemonade to "),

    # SP09 Vintage Glamour Stuff: Butler, Vanity, Globe Bar, Hollywood
    (r"(?i)благодарно хвалит дворецкого за безупречную преданную службу перед\s*", "Gratefully praising butler for loyal and impeccable service to "),
    (r"(?i)строго отчитывает дворецкого за неподобающее поведение и оплошности перед\s*", "Sternly scolding butler for improper conduct and mistakes before "),
    (r"(?i)с аристократическим достоинством просит подать напиток дворецкого\s*", "Aristocratically ordering a drink from butler "),
    (r"(?i)восхищается изысканным гламурным макияжем и голливудским стилем\s*", "Admiring glamorous vintage makeup and Hollywood style of "),
    (r"(?i)предлагает бокал элитного выдержанного напитка из старинного глобус-бара для\s*", "Offering a glass of aged vintage drink from antique globe bar to "),

    # SP10 Bowling Night Stuff: Bowling Strikes, Challenge, Technique, Gutter Ball, Moonlight
    (r"(?i)азартно хвастается серией сокрушительных страйков в боулинге перед\s*", "Excitedly bragging about a streak of crushing strikes to "),
    (r"(?i)спортивно вызывает на решающую партию в боулинг\s*", "Sportingly challenging to a decisive bowling match: "),
    (r"(?i)увлеченно обсуждает технику подкрутки шара и тяжесть шаров для боулинга с\s*", "Enthusiastically discussing ball spin technique and bowling ball weights with "),
    (r"(?i)смеясь подшучивает над неловко укатившимся в боковой желоб шаром\s*", "Laughingly teasing about clumsy gutter ball roll of "),
    (r"(?i)с восторгом восхищается атмосферой ночного неонового лунного боулинга с\s*", "Admiring the vibrant nighttime neon moonlight bowling vibe with "),

    # SP11 Fitness Stuff: Climbing Wall, Fire Challenge, Plumbumba Workout, Sore Muscles, Earbuds
    (r"(?i)с гордостью хвастается покорением сложнейшей трассы на скалодроме перед\s*", "Proudly bragging about conquering hardest climbing wall route to "),
    (r"(?i)с благоговением рассказывает о прохождении экстремального испытания огнем на скалодроме для\s*", "Awe-inspiringly sharing story of conquering extreme climbing wall fire challenge with "),
    (r"(?i)энергично обсуждает домашние фитнес-программы и тренировки «пламбумба» с\s*", "Energetically discussing home fitness routines and Plumbumba workouts with "),
    (r"(?i)с охами и вздохами жалуется на ноющие мышцы и дикую крепатуру после тренировки для\s*", "Groaning and complaining about sore aching muscles after brutal workout to "),
    (r"(?i)с энтузиазмом рекомендует лучший зажигательный плейлист для пробежки в наушниках для\s*", "Enthusiastically recommending best high-energy running playlist for earbuds to "),

    # SP12 Toddler Stuff: Play Dates, Ball Pit, Slide, Tunnels, Parenting
    (r"(?i)с нежностью хвалит малыша за смелость и ловкость на горке перед\s*", "Tenderly praising toddler's courage and dexterity on the slide to "),
    (r"(?i)с теплой улыбкой умиляется забавной возне малыша в сухом бассейне с шариками с\s*", "Warmly adoring toddler's adorable frolicking in the ball pit with "),
    (r"(?i)с энтузиазмом обсуждает организацию веселого праздника и встреч малышей на площадке с\s*", "Enthusiastically discussing organizing toddler play date on the playground with "),
    (r"(?i)доверительно делится родительскими секретами и лайфхаками воспитания малышей с\s*", "Confiding parenting tips and toddler rearing secrets with "),
    (r"(?i)весело зовет играть в отважных исследователей и покорителей пиратского корабля\s*", "Cheerfully inviting to pretend play as brave explorers on pirate ship: "),

    # SP13 Laundry Day Stuff: Washer, Dryer, Wash Tub, Clothesline, Hamper
    (r"(?i)с наслаждением хвастается безупречной чистотой и ароматом свежевыстиранного белья перед\s*", "Delightfully bragging about pristine cleanliness and fresh scent of laundry to "),
    (r"(?i)с тяжким вздохом жалуется на бесконечную гору грязной одежды и рутину стирки для\s*", "Heavily sighing and complaining about never-ending pile of dirty laundry to "),
    (r"(?i)увлеченно обсуждает любимые цветочные добавки и эфирные масла для ароматизации белья с\s*", "Enthusiastically discussing favorite floral additives and essential oils for laundry with "),
    (r"(?i)обеспокоенно предупреждает об опасности пожара из-за забитого ворсового фильтра сушилки для\s*", "Anxiously warning about dryer fire hazards from clogged lint trap to "),
    (r"(?i)с ностальгией восхищается деревенской романтикой ручной стирки в корыте с\s*", "Nostalgically admiring the rustic charm of hand-washing clothes in wash tub with "),

    # SP14 My First Pet Stuff: Rodents, Habitats, Pet Outfits, Rabid Rodent Fever
    (r"(?i)с гордостью хвастается умом,\s*ловкостью и забавными проделками своего маленького грызуна перед\s*", "Proudly bragging about cleverness, agility, and amusing antics of little rodent to "),
    (r"(?i)с ужасом и возмущением жалуется на болезненный укус бешеного грызуна для\s*", "Horrifiedly and indignantly complaining about painful bite from rabid rodent to "),
    (r"(?i)обеспокоенно предупреждает о смертельной угрозе бешенства грызунов и советует вакцину для\s*", "Anxiously warning about deadly threat of Rabid Rodent Fever and advising vaccine to "),
    (r"(?i)с восторгом умиляется забавному и очаровательному костюмчику своего питомца с\s*", "Enthusiastically gushing over funny and adorable costume of their pet with "),
    (r"(?i)с таинственным видом рассказывает о секретных ночных экспериментах и космических планах своего хомяка для\s*", "Mysteriously talking about secret nocturnal experiments and space plans of their hamster to "),

    # SP15 Moschino Stuff: Fashion Photography, Studio Tripod, Backdrop, Poses, Freelancer Career
    (r"(?i)увлеченно обсуждает последние тренды высокой моды и дерзкие коллекции moschino с\s*", "Enthusiastically discussing latest high fashion trends and bold Moschino collections with "),
    (r"(?i)с восхищением хвалит композицию,\s*свет и удачный ракурс на фотографии перед\s*", "Admiringly praising composition, lighting, and perfect camera angle of the photo to "),
    (r"(?i)скептически критикует безвкусный наряд и модные промахи для\s*", "Skeptically criticizing tacky outfit and fashion faux pas to "),
    (r"(?i)с энтузиазмом предлагает устроить профессиональную фэшн-фотосессию в студии для\s*", "Enthusiastically offering to set up a professional fashion photoshoot in the studio for "),
    (r"(?i)с гордостью хвастается публикацией своих снимков на обложке глянцевого журнала перед\s*", "Proudly bragging about having their photos featured on glossy magazine cover to "),

    # SP16 Tiny Living Stuff: Murphy Bed, All-in-One Media Center, Tiny Home
    (r"(?i)с воодушевлением расхваливает эстетику минимализма и уют жизни в микродоме для\s*", "Inspiringly praising minimalism aesthetics and cozy tiny home living to "),
    (r"(?i)с ужасом и содроганием предупреждает о смертельной опасности раскладной кровати мёрфи для\s*", "Horrifiedly and shuddering warning about deadly hazards of Murphy bed to "),
    (r"(?i)с самодовольной улыбкой хвастается копеечными счетами за коммуналку в микродоме перед\s*", "Smugly bragging about dirt-cheap utility bills in tiny home to "),
    (r"(?i)с раздражением жалуется на тесноту и вечную нехватку свободного места в крошечном доме для\s*", "Irritatedly complaining about cramped space and lack of room in tiny home to "),
    (r"(?i)с азартом обсуждает гениальные лайфхаки экономии места и мебель-трансформер с\s*", "Excitedly discussing brilliant space-saving lifehacks and transformable furniture with "),

    # SP17 Nifty Knitting Stuff: Knitting, Rocking Chair, Plopsy
    (r"(?i)с гордостью демонстрирует связанную своими руками вещь перед\s*", "Proudly showing off handcrafted knitted item to "),
    (r"(?i)с увлечением обсуждает сложные схемы петель,\s*узоры и виды мягкой пряжи с\s*", "Enthusiastically discussing complex stitch patterns and soft yarn types with "),
    (r"(?i)с теплотой и любовью дарит связанную своими руками уютную шерстяную вещь для\s*", "Warmly and lovingly gifting a cozy hand-knitted woolen item to "),
    (r"(?i)с энтузиазмом хвастается высокими доходами и успехом своих товаров на «продавито» перед\s*", "Enthusiastically bragging about high earnings and hot sales on Plopsy to "),
    (r"(?i)с досадой жалуется на спущенную петлю и безнадежно запутанный клубок ниток для\s*", "Frustratedly complaining about a dropped stitch and hopelessly tangled ball of yarn to "),
    (r"(?i)с ностальгической улыбкой делится теплыми воспоминаниями о былых временах с\s*", "With a nostalgic smile sharing fond memories of the good old days with "),

    # SP18 Paranormal Stuff: Séance, Haunted House, Guidry, Bonehilda, Investigator
    (r"(?i)с таинственным шепотом рассказывает леденящую кровь историю о привидениях для\s*", "Mysteriously whispering a chilling ghost story to "),
    (r"(?i)с трепетом и надеждой просит совета по общению с духами у призрачного джентльмена гидри", "Reverently asking ghostly gentleman Guidry for advice on dealing with spirits"),
    (r"(?i)ласково обнимает и успокаивает дрожащего от ужаса перед потусторонним собеседника", "Gently hugging and calming their terrified companion who is trembling from paranormal fear"),
    (r"(?i)с гордостью хвастается пережитой жуткой ночью в доме с привидениями перед\s*", "Proudly bragging about surviving a spooky night in the haunted house to "),
    (r"(?i)с волнением обсуждает потусторонние явления,\s*капризы духов и оккультные тайны с\s*", "Excitedly discussing supernatural phenomena, fickle spirits, and occult secrets with "),
    (r"(?i)игриво флиртует и строит глазки очаровательному призрачному созданию", "Playfully flirting and making eyes at the charming spectral being"),

    # SP19 Home Chef Hustle Stuff: Stand Mixer, Waffle Maker, Pizza Oven, Food Stand
    (r"(?i)с лучезарной улыбкой зазывает прохожих попробовать горячие свежеприготовленные деликатесы для\s*", "With a radiant smile beckoning passersby to try hot freshly-made delicacies to "),
    (r"(?i)с энтузиазмом рекомендует попробовать свое фирменное коронное блюдо для\s*", "Enthusiastically recommending their specialty signature dish to "),
    (r"(?i)с гордостью хвастается отличной выручкой и успешными продажами уличной еды перед\s*", "Proudly bragging about great profits and thriving street food sales to "),
    (r"(?i)с азартом делится кулинарными секретами идеального хрустящего теста для пиццы и вафель с\s*", "Passionately sharing culinary secrets of perfect crispy crust and batter with "),
    (r"(?i)с легким вздохом жалуется на привередливых клиентов уличного прилавка и пригоревшую корочку для\s*", "With a light sigh complaining about picky food stand customers and burnt crust to "),
    (r"(?i)с неподдельным восторгом хвалит умопомрачительный аппетитный аромат свежей выпечки перед\s*", "Enthusiastically praising the mouthwatering aroma of freshly baked goods to "),

    # SP20 Crystal Creations Stuff: Gemology Table, Jewelry Crafting, Crystal Grid, Crystal Tree
    (r"(?i)с искренним восхищением любуется изящным авторским ювелирным украшением перед\s*", "Genuinely admiring exquisite handcrafted jewelry to "),
    (r"(?i)с замиранием сердца делает предложение руки и сердца уникальным кольцом с ограненным вручную самоцветом для\s*", "Breathlessly proposing with a unique handcrafted crystal ring to "),
    (r"(?i)с воодушевлением обсуждает магические вибрации,\s*лунную зарядку и целебные свойства кристаллов с\s*", "Enthusiastically discussing magical vibrations, moonlight charging, and healing crystal properties with "),
    (r"(?i)с гордостью хвастается виртуозной огранкой редчайшего драгоценного камня перед\s*", "Proudly bragging about the masterwork cut of a rare gemstone to "),
    (r"(?i)с теплом и заботой дарит заряженный под лунным светом защитный кристальный амулет для\s*", "Warmly and caringly gifting a moonlight-charged protective crystal talisman to "),
    (r"(?i)с беспокойством предупреждает об иссякающей магической энергии заряженного самоцвета для\s*", "Anxiously warning about depleting magical energy of the charged gemstone to "),

    # Intimate & Romance
    (r"(?i)занимается интимной близостью \(вуху\)|занимается вуху|вуху|woohoo", "Having WooHoo / intimate intimacy"),
    (r"(?i)занимается зачатием ребенка", "Trying for a baby"),
    (r"(?i)страстно целует в губы|страстно целует", "Passionately kissing"),
    (r"(?i)чувственно целует в шею", "Sensually kissing neck"),
    (r"(?i)впервые робко целует", "Timidly sharing first kiss"),
    (r"(?i)целует в губы|целует", "Kissing"),
    (r"(?i)флиртует с|кокетничает с|заигрывает с", "Flirting with"),
    (r"(?i)признается в любви|признается в романтических чувствах", "Confessing romantic feelings"),
    (r"(?i)шепчет нежные признания", "Whispering sweet romantic words"),
    (r"(?i)предложение руки и сердца", "Proposing marriage"),

    # Sleep & Rest
    (r"(?i)спит в кровати|спит в постели", "Sleeping soundly in bed"),
    (r"(?i)дремлет на диване", "Napping comfortably on the couch"),
    (r"(?i)лежит в постели|лежит в кровати", "Lying in bed relaxing"),
    (r"(?i)лежит на диване", "Lying on the sofa relaxing"),
    (r"(?i)(?<![а-яА-ЯёЁ])спит(?![а-яА-ЯёЁ])", "Sleeping"),
    (r"(?i)(?<![а-яА-ЯёЁ])дремлет(?![а-яА-ЯёЁ])", "Napping"),

    # Drinks & Food
    (r"(?i)пьет горячий кофе|пьет кофе", "Drinking coffee"),
    (r"(?i)пьет горячий чай|пьет чай", "Drinking tea"),
    (r"(?i)пьет воду", "Drinking a glass of water"),
    (r"(?i)пьет коктейль", "Sipping a cocktail"),
    (r"(?i)пьет напиток", "Drinking a beverage"),
    (r"(?i)готовит еду|готовит блюдо|готовит ужин|готовит завтрак|готовит обед", "Cooking a meal"),
    (r"(?i)(?:ест еду|ест блюдо|(?<![а-яА-ЯёЁ])ест(?![а-яА-ЯёЁ]))", "Eating a meal"),
    (r"(?i)перекусывает", "Having a quick snack"),

    # Tech & Media
    (r"(?i)смотрит телевизор|смотрит тв", "Watching TV"),
    (r"(?i)играет в видеоигры|играет на компьютере", "Playing computer games"),
    (r"(?i)сидит за компьютером", "Sitting at the computer"),
    (r"(?i)просматривает веб-страницы", "Browsing the internet on computer"),
    (r"(?i)пишет на компьютере", "Typing on the computer"),
    (r"(?i)пишет сообщение в телефоне", "Texting on the phone"),
    (r"(?i)разговаривает по телефону", "Talking on the phone"),
    (r"(?i)смотрит в телефон", "Looking at phone screen"),
    (r"(?i)играет в игру на телефоне", "Playing a mobile game on phone"),

    # Books, Music, Arts
    (r"(?i)читает книгу", "Reading a book"),
    (r"(?i)играет на гитаре", "Playing acoustic guitar"),
    (r"(?i)играет на пианино", "Playing the piano"),
    (r"(?i)играет на скрипке", "Playing the violin"),
    (r"(?i)рисует картину на мольберте|рисует на мольберте", "Painting on an easel"),
    (r"(?i)танцует под музыку|танцует", "Dancing to music"),
    (r"(?i)слушает музыку", "Listening to music"),

    # Fitness, Bath & Hygiene
    (r"(?i)принимает грязевую ванну.*", "Taking a mud bath (relaxing spa treatment)"),
    (r"(?i)принимает успокаивающую лавандовую ванну", "Taking a soothing lavender bath"),
    (r"(?i)принимает бодрящую цитрусовую ванну", "Taking an invigorating citrus bath"),
    (r"(?i)принимает молочную ванну с медом.*", "Taking a milk and honey bath for soft skin"),
    (r"(?i)принимает романтическую ванну с лепестками роз", "Taking a romantic bath with rose petals"),
    (r"(?i)принимает расслабляющую ванну с целебными травами", "Taking a relaxing herbal bath"),
    (r"(?i)принимает расслабляющую ароматическую ванну.*", "Taking a relaxing aromatic bath with oils and salts"),
    (r"(?i)принимает расслабляющую ванну с.*пеной", "Taking a relaxing bubble bath with rich foam"),
    (r"(?i)плещется в ванне.*", "Splashing in the bath and playing with a rubber ducky"),
    (r"(?i)купает.*собаку в ванне", "Bathing and washing the dog in the bathtub"),
    (r"(?i)купает малыша в.*ванне", "Bathing the toddler in a warm bath"),
    (r"(?i)принимает горячий парной душ", "Taking a hot steamy shower"),
    (r"(?i)принимает вдохновляющий душ.*", "Taking an inspiring shower and pondering"),
    (r"(?i)принимает бодрящий прохладный душ", "Taking an invigorating cool shower"),
    (r"(?i)принимает быстрый освежающий душ", "Taking a quick refreshing shower"),
    (r"(?i)принимает душ и весело поет.*", "Taking a shower and cheerfully singing out loud"),
    (r"(?i)принимает душ и тихо плачет.*", "Taking a shower and crying quietly in sadness"),
    (r"(?i)принимает душ вместе с партнером", "Taking a shower together with partner"),
    (r"(?i)принимает душ", "Taking a shower"),
    (r"(?i)принимает.*ванну", "Taking a relaxing bath"),

    # PC Web / Internet Mode
    (r"(?i)ищет тайные знания и информацию о вампирах.*", "Researching vampire lore and secrets online"),
    (r"(?i)изучает тайны и предания об оборотнях.*", "Researching werewolf lore and legends online"),
    (r"(?i)изучает магические знания и заклинания.*", "Researching magic lore and spells online"),
    (r"(?i)ищет советы по воспитанию детей.*", "Researching parenting tips online"),
    (r"(?i)изучает советы для садоводов.*", "Researching gardening tips online"),
    (r"(?i)ищет фитнес-программы и советы по тренировкам.*", "Researching workout and fitness routines online"),
    (r"(?i)ищет кулинарные рецепты.*", "Looking up cooking recipes and culinary secrets online"),
    (r"(?i)изучает историю мирового искусства.*", "Researching art history and painting online"),
    (r"(?i)изучает рецепты коктейлей.*", "Researching cocktail recipes and mixology online"),
    (r"(?i)изучает музыкальные уроки и табулатуры.*", "Researching music lessons and tabs online"),
    (r"(?i)смотрит смешные видеоролики с животными.*", "Watching funny animal videos online"),
    (r"(?i)очищает историю браузера.*", "Clearing browser history on the computer"),
    (r"(?i)жертвует деньги на благотворительность.*", "Donating money to charity online"),
    (r"(?i)жалуется и строчит гневные отзывы.*", "Complaining and venting online"),
    (r"(?i)публикует смешной мем.*", "Posting a funny meme online"),
    (r"(?i)читает отзывы о заведениях и ресторанах.*", "Reading restaurant and venue reviews online"),
    (r"(?i)публикует подробный отзыв о заведении.*", "Posting a detailed review of a venue online"),
    (r"(?i)оплачивает коммунальные счета.*", "Paying utility bills online"),
    (r"(?i)оформляет денежный заем / кредит.*", "Taking out a bank loan online"),
    (r"(?i)изучает комплекс мер и правила района.*", "Researching neighborhood action plans and policies online"),
    (r"(?i)подает документы на поступление в университет.*", "Applying to university online"),
    (r"(?i)читает познавательные статьи в интернете", "Reading educational articles online"),
    (r"(?i)ищет информацию и серфит по сайтам в интернете", "Browsing websites and searching the internet"),
    (r"(?i)чистит зубы", "Brushing teeth"),
    (r"(?i)моет руки", "Washing hands"),
    (r"(?i)бегает на беговой дорожке", "Running on the treadmill"),
    (r"(?i)качает пресс", "Doing sit-ups"),
    (r"(?i)отжимается", "Doing push-ups"),
    (r"(?i)занимается йогой", "Practicing yoga"),
    (r"(?i)медитирует", "Meditating"),
    (r"(?i)бегает трусцой|пробежка", "Out for a jog"),

    # House chores
    (r"(?i)моет посуду", "Washing dirty dishes"),
    (r"(?i)убирает мусор|выносит мусор", "Taking out trash"),
    (r"(?i)убирает в доме|прибирается", "Cleaning the house"),
    (r"(?i)поливает растения", "Watering houseplants / garden"),

    # Multitasking & Group Dialogues
    (r"(?i)и параллельно общается с\s*", "while chatting with "),
    (r"(?i)и параллельно ведет беседу", "while having a conversation"),
    (r"(?i)ведет групповую беседу с\s*", "Having a group conversation with "),
    (r"(?i)ведет групповой разговор с\s*", "Having a group conversation with "),
    (r"(?i)ведет групповую беседу", "Having a group conversation"),
    (r"(?i)ведет беседу с\s*", "Talking with "),
    (r"(?i)ведет беседу", "Having a conversation"),
    (r"(?i)общается с\s*", "Talking with "),
    (r"(?i)общение с\s*", "Talking with "),
    (r"(?i)разговаривает с\s*", "Talking with "),

    # Social verbs and states
    (r"(?i)выслушивает крики и гневные претензии от\s*", "Listening to angry shouts and complaints from "),
    (r"(?i)слушает строгий выговор и наставления от\s*", "Listening to a strict lecture and scolding from "),
    (r"(?i)по-детски лепечет и общается с\s*", "Babbling child-like and talking with "),
    (r"(?i)раздраженно огрызается и спорит с\s*", "Snapping irritably and arguing with "),
    (r"(?i)сердито и на взводе отчитывает\s*/\s*спорит с\s*", "Angrily scolding and arguing with "),
    (r"(?i)напряженно слушает сердитые упрёки от\s*", "Tensely listening to angry reproaches from "),
    (r"(?i)напряженно беседует с раздраженным собеседником", "Tensely talking with an irritated interlocutor"),
    (r"(?i)болтает и делится мыслями с\s*", "Chatting and sharing thoughts with "),
    (r"(?i)ласково общается и сюсюкает с\s*", "Affectionately baby-talking with "),
    (r"(?i)непринужденно общается и беседует с\s*", "Casually chatting and talking with "),

    # Granular Social Interactions
    (r"(?i)посылает воздушный поцелуй для\s*", "Blowing a kiss to "),
    (r"(?i)нежно целует в щеку\s*", "Gently kissing cheek of "),
    (r"(?i)галантно целует руку\s*", "Gallantly kissing hand of "),
    (r"(?i)чувственно целует в шею\s*", "Sensually kissing neck of "),
    (r"(?i)романтично целует в губы\s*", "Romantically kissing lips of "),
    (r"(?i)страстно целует\s*", "Passionately kissing "),
    (r"(?i)нежно держит за руку\s*", "Gently holding hands with "),
    (r"(?i)нежно обнимает и прижимает к себе\s*", "Gently embracing and holding close "),
    (r"(?i)шепчет нежные признания на ухо\s*", "Whispering sweet romantic words to "),
    (r"(?i)поет романтическую серенаду для\s*", "Singing a romantic serenade to "),
    (r"(?i)признается в романтических чувствах\s*/\s*любви к\s*", "Confessing romantic feelings of love to "),
    (r"(?i)подкатывает с пикап-фразой к\s*", "Using a pickup line on "),
    (r"(?i)приглашает на романтическое свидание\s*", "Asking on a romantic date "),
    (r"(?i)предлагает начать встречаться и стать парой для\s*", "Asking to be boyfriend/girlfriend to "),
    (r"(?i)интересуется семейным положением у\s*", "Asking if single to "),
    (r"(?i)делает предложение руки и сердца для\s*", "Proposing marriage to "),
    (r"(?i)произносит брачные клятвы перед\s*", "Exchanging marriage vows with "),
    (r"(?i)делает расслабляющий массаж для\s*", "Giving a relaxing massage to "),
    (r"(?i)романтично кормит с рук\s*", "Romantically hand-feeding "),
    (r"(?i)романтично любуется звездами вместе с\s*", "Romantically stargazing with "),
    (r"(?i)делает комплимент привлекательности\s*", "Complimenting appearance of "),
    (r"(?i)нежно принимает ласки и романтические знаки внимания от\s*", "Gently accepting affection from "),
    (r"(?i)нежно проявляет ласку и заботу к\s*", "Gently showing affection and care to "),
    (r"(?i)искренне выражает теплые чувства к\s*", "Warmly expressing affection to "),
    (r"(?i)признаётся в романтической измене перед\s*", "Confessing romantic infidelity to "),
    (r"(?i)разрывает отношения\s*/\s*предлагает остаться друзьями с\s*", "Breaking up / asking to just be friends with "),
    (r"(?i)требует развод у\s*", "Demanding a divorce from "),
    (r"(?i)узнает,\s*как прошел день у\s*", "Asking how the day went of "),
    (r"(?i)расспрашивает о работе и профессии\s*", "Asking about job and career of "),
    (r"(?i)знакомится ближе и узнает получше\s*", "Getting to know better "),
    (r"(?i)ведет глубокий душевный разговор с\s*", "Having a deep heart-to-heart conversation with "),
    (r"(?i)доверяет сокровенный секрет\s*", "Sharing a deep secret with "),
    (r"(?i)изливает душу и делится переживаниями с\s*", "Confiding and venting feelings to "),
    (r"(?i)утешает и искренне поддерживает\s*", "Comforting and cheering up "),
    (r"(?i)делает комплимент стилю и наряду\s*", "Complimenting outfit of "),
    (r"(?i)делает искренний комплимент для\s*", "Giving a sincere compliment to "),
    (r"(?i)с огромным восторгом рассказывает что-то\s*", "Enthusiastically sharing something with "),
    (r"(?i)рассказывает увлекательную историю\s*", "Telling a captivating story to "),
    (r"(?i)сплетничает и обсуждает слухи с\s*", "Gossiping and sharing rumors with "),
    (r"(?i)искренне извиняется и просит прощения у\s*", "Sincerely apologizing to "),
    (r"(?i)дружески обнимает\s*", "Giving a friendly hug to "),
    (r"(?i)дает пять\s*/\s*выражает респект\s*\(«[^»]+»\)\s*для\s*", "Giving a high five to "),
    (r"(?i)пожимает руку\s*", "Shaking hands with "),
    (r"(?i)показывает фотографии на телефоне для\s*", "Showing photos on phone to "),
    (r"(?i)искренне благодарит\s*", "Warmly thanking "),
    (r"(?i)просит денег в долг у\s*", "Asking for a loan from "),
    (r"(?i)обсуждает совместные интересы и планы с\s*", "Discussing interests and plans with "),
    (r"(?i)предлагает съехаться и жить вместе для\s*", "Asking to move in together with "),
    (r"(?i)предлагает стать лучшими друзьями для\s*", "Asking to be best friends with "),
    (r"(?i)выражает искренние соболезнования и поддерживает\s*", "Expressing sincere condolences to "),
    (r"(?i)обсуждает желание завести детей и расширить семью с\s*", "Discussing expanding family with "),
    (r"(?i)жалуется на работу и начальника для\s*", "Complaining about work and boss to "),
    (r"(?i)хвастается своими успехами перед\s*", "Bragging about achievements to "),
    (r"(?i)шутит и рассказывает анекдот для\s*", "Telling jokes to "),
    (r"(?i)травит уморительную историю для\s*", "Telling a hilarious story to "),
    (r"(?i)пародирует и смешно изображает кого-то перед\s*", "Impersonating someone funny in front of "),
    (r"(?i)корчит забавные рожицы перед\s*", "Making silly faces at "),
    (r"(?i)игриво щекочет\s*", "Playfully tickling "),
    (r"(?i)дурачится и веселит\s*", "Goofing around and entertaining "),
    (r"(?i)вступает в ожесточенную драку с\s*", "Engaging in a physical fight with "),
    (r"(?i)отвешивает звонкую пощечину\s*", "Slapping the face of "),
    (r"(?i)грубо толкает и задирает\s*", "Shoving and harassing "),
    (r"(?i)в ярости кричит и срывается на\s*", "Furious and shouting at "),
    (r"(?i)грубо оскорбляет и унижает\s*", "Rudely insulting and belittling "),
    (r"(?i)ожесточенно спорит и ругается с\s*", "Bitterly arguing and bickering with "),
    (r"(?i)в лицо объявляет своим злейшим врагом\s*", "Declaring as sworn enemy "),
    (r"(?i)угрожает расправой и запугивает\s*", "Threatening and intimidating "),
    (r"(?i)яростно обвиняет во всех грехах\s*", "Furiously blaming and accusing "),
    (r"(?i)выплескивает напиток прямо в лицо\s*", "Throwing a drink in the face of "),
    (r"(?i)разговаривает с|беседует с", "Chatting with"),
    (r"(?i)обнимает", "Hugging"),
    (r"(?i)шутит с|рассказывает анекдот", "Telling jokes to"),
    (r"(?i)спорит с|ругается с", "Arguing with"),
    (r"(?i)играет в шахматную партию против\s*", "Playing a chess match against "),
    (r"(?i)обучает\s+(.+?)\s+игре в шахматы и даёт наставления", r"Mentoring \1 in chess and giving guidance"),

    # EP01 Get to Work: Detective, Doctor, Scientist, Alien, Retail
    (r"(?i)ведет допрос (.+?) в роли «доброго полицейского»", r"Interrogating \1 playing good cop"),
    (r"(?i)ведет жесткий допрос (.+?) в роли «злого полицейского»", r"Interrogating \1 playing bad cop"),
    (r"(?i)допрашивает подозреваемого \((.+?)\) в комнате для допросов", r"Interrogating suspect (\1) in interrogation room"),
    (r"(?i)фотографирует задержанного \((.+?)\) для полицейского досье \(магшот\)", r"Taking mugshot of suspect (\1) for police file"),
    (r"(?i)снимает отпечатки пальцев у (.+?) на сканере в участке", r"Taking fingerprints of \1 on police scanner"),
    (r"(?i)обыскивает задержанного \((.+?)\) на наличие улик.*", r"Searching suspect (\1) for evidence"),
    (r"(?i)отводит и запирает (.+?) в тюремную камеру", r"Locking \1 in jail cell"),
    (r"(?i)выпускает (.+?) из тюремной камеры", r"Releasing \1 from jail cell"),
    (r"(?i)арестовывает (.+?) и надевает наручники", r"Arresting \1 and placing handcuffs"),
    (r"(?i)выписывает штраф (.+?) за нарушение.*", r"Issuing citation to \1 for public disorder"),
    (r"(?i)принимает роды у (.+?) в больничной операционной", r"Delivering baby for \1 in operating room"),
    (r"(?i)принимает роды у роженицы \((.+?)\) в больнице", r"Delivering baby for \1 in hospital"),
    (r"(?i)проводит сложную хирургическую операцию (.+)", r"Performing surgery on \1"),
    (r"(?i)делает рентгеновский снимок пациенту \((.+?)\)", r"Taking X-ray scan of patient (\1)"),
    (r"(?i)проводит кардиологический стресс-тест (.+?) на беговой дорожке", r"Conducting cardiac stress test on \1"),
    (r"(?i)измеряет температуру тела (.+?) медицинским градусником", r"Measuring body temperature of \1"),
    (r"(?i)осматривает зрение и уши (.+?) медицинским фонариком", r"Examining eyes and ears of \1"),
    (r"(?i)берет медицинский мазок из горла у (.+)", r"Taking throat swab from \1"),
    (r"(?i)делает лечебный укол пациенту \((.+?)\)", r"Giving medical injection to patient (\1)"),
    (r"(?i)дает назначенную лечебную микстуру (.+)", r"Administering prescribed medicine to \1"),
    (r"(?i)проводит медицинский осмотр (.+?) на смотровой кушетке", r"Examining patient \1 on medical bed"),
    (r"(?i)ставит точный медицинский диагноз пациенту \((.+?)\)", r"Diagnosing illness of patient (\1)"),
    (r"(?i)стреляет из симлуча и замораживает (.+?) в глыбу льда!", r"Firing SimRay and freezing \1 in a block of ice!"),
    (r"(?i)использует ментальный луч симлуча и подчиняет разум (.+)", r"Using SimRay mind control beam on \1"),
    (r"(?i)создает живого генетического клона (.+?) на клонирующей машине", r"Creating genetic clone of \1 on Cloning Machine"),
    (r"(?i)тестирует действие экспериментальной научной сыворотки на (.+)", r"Testing experimental scientific serum on \1"),
    (r"(?i)берет образец днк у (.+?) для генетических исследований", r"Collecting DNA sample from \1 for genetic research"),
    (r"(?i)применяет силу пришельца и полностью стирает память (.+)", r"Using alien power to erase memories of \1"),
    (r"(?i)сканирует разум (.+?) инопланетными биоволнами.*", r"Scanning mind of \1 with alien bio-waves"),
    (r"(?i)считывает эмоции (.+?) через инопланетную эмпатию", r"Sensing emotions of \1 through alien empathy"),
    (r"(?i)пробивает товар на кассовом планшете и рассчитывает покупателя \((.+?)\)", r"Ringing up purchase for \1 on retail tablet"),
    (r"(?i)консультирует покупателя \((.+?)\) и нахваливает товары магазина", r"Pitching products and answering questions for customer (\1)"),
    (r"(?i)обсуждает цену на товар и предлагает скидку покупателю \((.+?)\)", r"Discussing price and offering discount to customer (\1)"),
    (r"(?i)хвалит сотрудника магазина \((.+?)\) за отличную работу.*", r"Praising store employee (\1) for great work"),
    (r"(?i)строго отчитывает сотрудника магазина \((.+?)\) за лень.*", r"Scolding store employee (\1) for slacking off"),
    (r"(?i)фотографирует модель \((.+?)\) в профессиональной фотостудии", r"Taking photos of model (\1) in photo studio"),

    # Social Dialogues EP01
    (r"(?i)ведет допрос подозреваемого в лице\s*", "Interrogating suspect "),
    (r"(?i)арестовывает и надевает наручники на\s*", "Arresting and cuffing "),
    (r"(?i)опрашивает свидетеля о преступлении в лице\s*", "Interviewing crime witness "),
    (r"(?i)проводит медицинский осмотр и лечит пациента в лице\s*", "Examining and treating patient "),
    (r"(?i)просит предоставить образец днк у\s*", "Asking for DNA sample from "),
    (r"(?i)тестирует экспериментальную научную сыворотку на\s*", "Testing experimental serum on "),
    (r"(?i)стирает память инопланетной силой у\s*", "Erasing memory with alien power of "),
    (r"(?i)сканирует личность инопланетным биосканированием у\s*", "Scanning personality with alien bio-scan of "),
    (r"(?i)пробивает покупку на кассовом планшете для\s*", "Ringing up purchase on tablet for "),
    (r"(?i)консультирует и нахваливает товар магазина для\s*", "Pitching retail products to "),

    # EP02 Get Together: Clubs, DJ, Dance, Pub Games, Cafe, Bonfire, Closet, Diving
    (r"(?i)участвует в жарком танцевальном баттле против (.+)", r"Competing in heated dance battle against \1"),
    (r"(?i)демонстрирует тайное клубное рукопожатие (.+)", r"Showing secret club handshake to \1"),
    (r"(?i)пытается свергнуть лидера клуба в лице (.+?)!", r"Attempting to overthrow club leader \1!"),
    (r"(?i)требует от (.+?) немедленно передать лидерство в клубе", r"Demanding club leadership from \1"),
    (r"(?i)начинает клубное собрание для членов клуба «(.+?)»", r"Starting club gathering for members of \"\1\""),
    (r"(?i)завершает клубное собрание членов клуба «(.+?)»", r"Ending club gathering for members of \"\1\""),
    (r"(?i)участвует в клубном собрании «(.+?)»", r"Participating in club gathering \"\1\""),
    (r"(?i)играет партию в настольный футбол \(кикер\) против (.+)", r"Playing foosball match against \1"),
    (r"(?i)соревнуется в меткости в игре в дартс против (.+)", r"Competing in darts match against \1"),

    # Social Dialogues EP02
    (r"(?i)демонстрирует тайное клубное рукопожатие перед\s*", "Performing secret club handshake with "),
    (r"(?i)пытается свергнуть с поста лидера клуба\s*", "Attempting to overthrow club leader "),
    (r"(?i)требует передать бразды правления клубом от\s*", "Demanding club leadership from "),
    (r"(?i)приглашает вступить в свой клуб\s*", "Inviting to join their club "),
    (r"(?i)с позором выгоняет из клуба\s*", "Shamefully kicking out of the club "),
    (r"(?i)восторженно нахваливает свой клуб перед\s*", "Enthusiastically praising their club to "),
    (r"(?i)бросает вызов в танцевальном баттле\s*", "Challenging to a dance battle "),
    (r"(?i)играет в настольный футбол \(кикер\) против\s*", "Playing foosball against "),
    (r"(?i)соревнуется в меткости в игре в дартс против\s*", "Playing darts against "),

    # EP03 City Living: Apartments, Festivals, Basketball, Karaoke, Murals
    (r"(?i)яростно стучит в дверь соседей и жалуется на шум \((.+?)\)", r"Furiously banging on neighbor's door complaining about noise (\1)"),
    (r"(?i)стучит в дверь к соседу \((.+?)\)", r"Knocking on neighbor's door (\1)"),
    (r"(?i)торжественно вручает ключ от своей квартиры (.+)", r"Giving apartment key to \1"),
    (r"(?i)забирает ключ от своей квартиры у (.+)", r"Taking back apartment key from \1"),
    (r"(?i)осыпает романтическими лепестками сакуры (.+)", r"Showering \1 with romantic sakura petals"),
    (r"(?i)играет в уличный баскетбол 1 на 1 против (.+)", r"Playing street basketball 1-on-1 against \1"),
    (r"(?i)поет зажигательный дуэт в микрофон караоке вместе с (.+)", r"Singing karaoke duet with \1"),
    (r"(?i)агитирует внести благотворительное пожертвование в фонд (.+)", r"Canvassing for charitable campaign donations with \1"),

    # Social Dialogues EP03
    (r"(?i)яростно жалуется на шум соседу в лице\s*", "Furiously complaining about apartment noise to "),
    (r"(?i)торжественно вручает ключ от своей квартиры\s*", "Giving apartment key to "),
    (r"(?i)забирает ключ от своей квартиры у\s*", "Taking back apartment key from "),
    (r"(?i)требует срочного ремонта квартиры от арендодателя в лице\s*", "Demanding urgent apartment repairs from landlord "),
    (r"(?i)осыпает романтическими лепестками сакуры\s*", "Showering with romantic sakura petals "),
    (r"(?i)обсуждает остроту фестивального карри с\s*", "Discussing spicy festival curry with "),
    (r"(?i)поет зажигательный дуэт в микрофон караоке вместе с\s*", "Singing karaoke duet with "),
    (r"(?i)играет в уличный баскетбол 1 на 1 против\s*", "Playing street basketball against "),
    (r"(?i)агитирует внести благотворительное пожертвование в фонд\s*", "Canvassing for campaign donation from "),
    (r"(?i)выносит строгую профессиональную оценку блюду\s*", "Delivering critic's evaluation on food to "),

    # Postures & Rooms
    (r"(?i)сидя на кровати", "sitting on bed"),
    (r"(?i)сидя на диване", "sitting on sofa"),
    (r"(?i)сидя на стуле", "sitting on chair"),
    (r"(?i)сидя за столом", "sitting at table"),
    (r"(?i)сидя за барной стойкой", "sitting at bar counter"),
    (r"(?i)сидя на полу", "sitting on the floor"),
    (r"(?i)стоя", "standing"),
    (r"(?i)в спальне", "in the bedroom"),
    (r"(?i)в хозяйской спальне", "in master bedroom"),
    (r"(?i)в гостиной", "in the living room"),
    (r"(?i)на кухне", "in the kitchen"),
    (r"(?i)в столовой", "in the dining room"),
    (r"(?i)в ванной комнате|в ванной", "in the bathroom"),
    (r"(?i)в кабинете", "in the study / home office"),
    (r"(?i)в прихожей|в коридоре", "in the hallway"),
    (r"(?i)на заднем дворе|во дворе", "in the backyard"),
    (r"(?i)на балконе", "on the balcony"),
    (r"(?i)на террасе", "on the terrace"),
    (r"(?i)в саду", "in the garden"),
    (r"(?i)у бассейна|в бассейне", "at the pool"),
    (r"(?i)на улице", "outdoors"),
    (r"(?i)дома", "at home"),
]

LOCATION_PATTERNS_EN = [
    (r"(?i)у себя дома\s*\(([^)]+)\)", r"At Home (\1)"),
    (r"(?i)у себя дома", "At Home"),
    (r"(?i)у себя", "At Home"),
    (r"(?i)возле своего дома\s*/\s*во дворе", "Outside their home / in the yard"),
    (r"(?i)в доме", "At Home / Indoors"),
    (r"(?i)в помещении", "Indoors"),
    (r"(?i)на улице", "Outdoors"),

    (r"(?i)дома\s*\(([^)]+)\)", r"At Home (\1)"),
    (r"(?i)на текущем участке", "On current lot"),
    (r"(?i)находится на другом участке\s*\(г\.\s*([^)]+)\)", r"On another lot (\1)"),
    (r"(?i)находится на другом участке", "On another lot"),
    (r"(?i)в гостиной|гостиная", "in living room"),
    (r"(?i)в спальне|спальня", "in bedroom"),
    (r"(?i)на кухне|кухня", "in kitchen"),
    (r"(?i)в ванной комнате|в ванной|ванная комната|ванная", "in bathroom"),
    (r"(?i)в кабинете|кабинет", "in study / office"),
    (r"(?i)в коридоре|коридор", "in hallway"),
    (r"(?i)в столовой|столовая", "in dining room"),
    (r"(?i)в детской|детская", "in nursery / kids room"),
    (r"(?i)в подвале|подвал", "in basement"),
    (r"(?i)на чердаке|чердак", "in attic"),
    (r"(?i)на балконе|балкон", "on balcony"),
    (r"(?i)на террасе|терраса", "on terrace"),
    (r"(?i)во дворе|двор|задний двор", "in yard / backyard"),
]

PREGNANCY_MAP_EN = {
    "Не беременна": "Not pregnant",
    "Не беремен": "Not pregnant",
    "Не беременен": "Not pregnant",
    "Беременность (1-й триместр)": "Pregnant (1st trimester)",
    "Беременность (2-й триместр)": "Pregnant (2nd trimester)",
    "Беременность (3-й триместр)": "Pregnant (3rd trimester)",
    "Роды / Схватки": "In Labor / Giving Birth",
    "Партнерша беременна": "Partner is pregnant",
}


def translate_pregnancy_en(pregnancy_ru: str) -> str:
    if not pregnancy_ru:
        return "Not pregnant"
    p = pregnancy_ru.strip()
    if p in PREGNANCY_MAP_EN:
        return PREGNANCY_MAP_EN[p]
    p_lower = p.lower()
    if p_lower.startswith("не беремен"):
        if "в семье скоро будет пополнение" in p_lower:
            m = re.search(r':\s*([^)]*?)\s*беременна', p, re.I)
            h_name = m.group(1).strip() if m else "household member"
            return f"Not pregnant (family addition expected soon: {h_name} is pregnant)"
        if "партнер" in p_lower:
            m = re.search(r'партнер(?:ша)?\s+([^,:]+)', p, re.I)
            part_name = m.group(1).strip() if m else "partner"
            return f"Not pregnant (partner {part_name} is expecting a baby)"
        return "Not pregnant"

    is_alien = "инопланет" in p_lower or "похищен" in p_lower
    is_male = p.startswith("Беременен:")

    # Determine term / stage
    if "роды" in p_lower or "схватк" in p_lower:
        stage = "In labor! Giving birth right now!"
    elif "3-й триместр" in p_lower or "3 триместр" in p_lower:
        stage = "3rd trimester"
    elif "2-й триместр" in p_lower or "2 триместр" in p_lower:
        stage = "2nd trimester"
    elif "1-й триместр" in p_lower or "1 триместр" in p_lower:
        stage = "1st trimester"
    else:
        stage = "Pregnant"

    # Offspring count
    babies = "one baby"
    if "двойн" in p_lower:
        babies = "twins"
    elif "тройн" in p_lower:
        babies = "triplets"

    if is_alien and is_male:
        res = f"Pregnant (male): {stage}, pregnant with an alien after abduction; Expecting: {babies}"
        if "опылитель" in p_lower or "второй родитель" in p_lower:
            m = re.search(r'(?:опылитель|второй родитель[^:]*):\s*([^;]+)', p, re.I)
            raw_pol = m.group(1).strip() if m else ""
            if not raw_pol or "инопланет" in raw_pol.lower():
                pollinator = "Alien civilization"
            else:
                pollinator = transliterate_to_latin(raw_pol)
            res += f"; Pollinator: {pollinator}"
        return res
    elif is_male:
        return f"Pregnant (male): {stage}; Expecting: {babies}"

    if "1-й триместр" in p_lower or "1 триместр" in p_lower:
        return f"Pregnant (1st trimester); Expecting: {babies}"
    if "2-й триместр" in p_lower or "2 триместр" in p_lower:
        return f"Pregnant (2nd trimester); Expecting: {babies}"
    if "3-й триместр" in p_lower or "3 триместр" in p_lower:
        return f"Pregnant (3rd trimester); Expecting: {babies}"
    if "роды" in p_lower or "схватк" in p_lower:
        return "In Labor / Giving Birth"
    if "партнерша беременна" in p_lower:
        return "Partner is pregnant"
    return transliterate_to_latin(p)

FAME_MAP_EN = {
    "Безвестность": "Unknown (No fame)",
    "Заметный персонаж": "Notable Sim (1-Star)",
    "Восходящая звезда": "Rising Star (2-Star)",
    "Знаменитость": "B-Lister (3-Star)",
    "Настоящая звезда": "Proper Celebrity (4-Star)",
    "Суперзвезда": "Global Superstar (5-Star)",
    "Безупречная репутация": "Pristine Reputation",
    "Отличная репутация": "Great Reputation",
    "Хорошая репутация": "Good Reputation",
    "Нейтральная репутация": "Neutral Reputation",
    "Плохая репутация": "Bad Reputation",
    "Ужасная репутация": "Terrible Reputation",
    "Отвратительная репутация": "Atrocious Reputation",
}


# =========================================================================
# 9. DYNAMIC AGE-SPECIFIC PROMPT GUIDANCE (ENGLISH)
# =========================================================================

AGE_INSTRUCTION_RULES_EN = {
    "BABY": (
        "AGE CONDITION (Newborn Baby): The character is a newborn infant. "
        "They have no knowledge of words, speech, or complex logic. Thoughts must strictly consist of pure primal physical sensations "
        "(warmth, cold, hunger, milk taste, mother's scent, darkness, sleepiness) or sound reactions (soft whimpers, quiet sniffling, cries). "
        "NEVER use adult coherent logic or complete sentences!\n"
        "Examples: \"Warm... cozy... [soft breathing] sleepy.\" or \"[Whimpering cry] Too cold and wet! Make it stop!\""
    ),
    "INFANT": (
        "AGE CONDITION (Crawling Infant): The character is a crawling infant. "
        "They explore the universe through touch and mouth. Use baby babble (\"goo-goo\", \"ba-ba\"), immediate sensory reactions, and curiosity. "
        "Everything around is massive, bright, and must be tasted or grabbed. No adult thoughts!\n"
        "Examples: \"Shiny red block on the floor! Must put in mouth right now... Ba-ba!\" or \"Loud noise! Scary! Where is mama? Want hugs!\""
    ),
    "TODDLER": (
        "AGE CONDITION (Toddler): The character is a toddler. "
        "They think in short, simple, egocentric sentences. Frequent tantrums (\"Mine!\", \"No want!\"), "
        "playful sound mimicry, fixations on toys, potty, cartoons, and sweet treats. Pure childhood innocence.\n"
        "Examples: \"Vroom vroom goes the toy car! I don't wanna eat green broccoli, I want a cookie!\" or \"Monster under bed won't catch me under blanket. Tummy rumbling...\""
    ),
    "CHILD": (
        "AGE CONDITION (Child, 7-11 years old): The character is a school-age child. "
        "Fascinated by play, games, schoolyard gossip, wild imagination, and avoiding homework. "
        "Childish frustration at adult rules mixed with pure excitement over simple discoveries.\n"
        "Examples: \"Why do adults get to stay up late and I have to go to sleep? Can't wait to finish my LEGO space station tomorrow.\" or \"Math homework again... I'd rather be outside playing pirates with my friends.\""
    ),
    "TEEN": (
        "AGE CONDITION (Teenager): The character is an adolescent teen. "
        "Mind full of drama, identity search, youth maximalism, and light sarcasm. "
        "Obsessed with appearance, peer opinions, secret crushes, and annoyance at parental nagging. Subtle modern teen vibe.\n"
        "Examples: \"A huge pimple right on my forehead before school starts. My social life is officially over.\" or \"If they don't text me back right now I'm gonna scream. And mom is yelling from the kitchen again...\""
    ),
    "YOUNGADULT": (
        "AGE CONDITION (Young Adult): The character is a young adult. "
        "Focus on starting a career, dating, self-discovery, parties, late nights, or coping with adult bills. A mix of ambition, exhaustion, and light irony.\n"
        "Examples: \"If I don't get a hot cup of coffee into my bloodstream right now, this work report will write my obituary.\" or \"I really should go out tonight, but Netflix and my couch are practically holding me hostage...\""
    ),
    "ADULT": (
        "AGE CONDITION (Adult): The character is a mature adult. "
        "Realistic, grounded perspective on life. Balancing career, household chores, family obligations, fatigue, mortgage/bills, and quiet personal goals.\n"
        "Examples: \"Household bills went up again this month. Looks like that vacation to Sulani is postponed until next year.\" or \"Need to get dinner prepped before everyone gets back home and chaos ensues.\""
    ),
    "ELDER": (
        "AGE CONDITION (Elder): The character is an elderly senior. "
        "Fond reflections on the past (\"back in my day...\"), longing for peace and quiet, complaints about aching joints or the weather, and caring for grandchildren.\n"
        "Examples: \"My lower back is definitely forecasting rain tomorrow... Youngsters nowadays can't even say a proper hello.\" or \"Nothing beats a quiet evening by the warm fireplace with a cup of herbal tea.\""
    ),
}


# =========================================================================
# 10. REUSABLE TRANSLATION HELPER FUNCTIONS
# =========================================================================

# Transliteration table for zero-leak guarantee
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

def transliterate_to_latin(text: str) -> str:
    """Safely converts any residual Cyrillic characters into readable Latin."""
    return "".join(CYR_TO_LAT.get(c, c) for c in text)

def translate_phrase(text: str, mapping: dict) -> str:
    """Replaces known phrases from dictionary with Cyrillic-free guarantee."""
    if not text:
        return ""
    res = text.strip()
    # Check exact match first
    if res in mapping:
        return mapping[res]
    # Check key substring match (longer keys first)
    for k in sorted(mapping.keys(), key=len, reverse=True):
        if k and k.lower() in res.lower():
            pattern = re.compile(re.escape(k), re.IGNORECASE)
            res = pattern.sub(mapping[k], res)
    # Transliteration fallback if Cyrillic still remains
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


GENERIC_IDLES_MAP_EN = {
    "Стоит на месте, осматривается": "Standing in place, looking around",
    "Стоит на месте": "Standing in place",
    "Сидит на полу / играет": "Sitting on the floor / playing",
    "Лежит на полу и с любопытством разглядывает всё вокруг": "Lying on the floor, curiously looking all around",
    "Сидит на диване / стуле и отдыхает": "Sitting on sofa/chair, relaxing",
    "Сидит на диване / стуле": "Sitting on sofa/chair",
    "Сидит за столом": "Sitting at table",
    "Лежит в детской кроватке": "Lying in crib",
    "Лежит на животике на полу и смотрит по сторонам": "Lying on tummy on the floor, looking around",
    "Лежит на игровом коврике": "Lying on playmat",
    "Сидит в детском высоком стульчике": "Sitting in high chair",
    "Сидит на полу и разглядывает комнату": "Sitting on the floor, looking around the room",
    "Ползает по полу": "Crawling on the floor",
    "Находится на ручках у взрослого": "Being held in adult's arms",
}

ACTIVITY_MAP_EXACT_EN = {
    # Basemental Drugs & Substances Activities
    "Курит марихуану через бонг": "Smoking marijuana from a bong",
    "Курит блант с марихуаной": "Smoking a weed blunt",
    "Скручивает блант": "Rolling a blunt",
    "Курит травку через трубку": "Smoking weed from a pipe",
    "Ест выпечку с марихуаной (съедобный каннабис)": "Eating cannabis edible (space cake)",
    "Скручивает косяк с марихуаной": "Rolling a weed joint",
    "Делится косяком с марихуаной": "Sharing a weed joint",
    "Курит косяк с марихуаной": "Smoking a weed joint",
    "Курит марихуану (травку)": "Smoking marijuana (weed)",
    "Парит вейп (электронную сигарету)": "Vaping (e-cigarette)",
    "Заправляет вейп": "Refilling a vape",
    "Крутит самокрутку с табаком": "Rolling a tobacco cigarette",
    "Курит сигарету": "Smoking a cigarette",
    "Курит сигару": "Smoking a cigar",
    "Курит кальян": "Smoking hookah",
    "Употребляет снюс / жевательный табак": "Using snus / dipping tobacco",
    "Снюхивает дорожку кокаина с раковины": "Snorting a line of cocaine off the sink",
    "Снюхивает дорожку кокаина": "Snorting a line of cocaine",
    "Снюхивает дорожку амфетамина (спидов)": "Snorting a line of speed (amphetamine)",
    "Снюхивает дорожку кетамина": "Snorting a line of ketamine",
    "Снюхивает измельченный аддералл": "Snorting crushed Adderall",
    "Принимает таблетку аддералла": "Taking an Adderall pill",
    "Принимает таблетку ксанакса": "Taking a Xanax pill",
    "Прессует таблетки на станке": "Pressing pills with a pill press",
    "Принимает таблетку МДМА (экстази)": "Taking an MDMA (ecstasy) pill",
    "Пьет кодеиновый сироп (лин)": "Drinking codeine syrup (lean)",
    "Принимает марку ЛСД (кислоту)": "Dropping an LSD tab (acid)",
    "Употребляет волшебные грибы (псилоцибин)": "Eating magic mushrooms (psilocybin)",
    "Пьет аяуаску на шаманском ритуале": "Drinking Ayahuasca in a shamanic ritual",
    "Употребляет пейот (мескалин)": "Consuming peyote (mescaline)",
    "Пьет алкоголь из бочонка (Keg)": "Drinking from a keg (doing a keg stand)",
    "Пьет пиво (алкоголь)": "Drinking beer (alcohol)",
    "Опрокидывает шот крепкого алкоголя": "Downing a shot of strong liquor",
    "Пьет бокал вина / нектара": "Drinking a glass of wine / nectar",
    "Пьет алкогольный коктейль": "Drinking an alcoholic cocktail",

    # Rocket Science & Space Exploration
    "Строит космическую ракету (ракетостроение)": "Building a space rocket (rocket science)",
    "Продолжает строительство космической ракеты": "Continuing construction of the space rocket",
    "Помогает строить космическую ракету (ракетостроение)": "Assisting in building a space rocket (rocket science)",
    "Модернизирует и улучшает космическую ракету": "Upgrading and modifying the space rocket",
    "Устанавливает защитную пушку на космическую ракету": "Installing ion cannon defense system on the space rocket",
    "Устанавливает дополнительные топливные баки на ракету": "Installing auxiliary fuel tanks on the space rocket",
    "Устанавливает дополнительные ускорители на ракету": "Installing additional thruster boosters on the space rocket",
    "Устанавливает посадочные стабилизаторы на ракету": "Installing landing stabilizers on the space rocket",
    "Расширяет грузовой отсек космической ракеты": "Expanding the space rocket's cargo bay",
    "Устанавливает генератор червоточин на космическую ракету": "Installing a wormhole generator on the space rocket",
    "Летит на космической ракете в открытый космос (исследует вселенную)": "Flying into outer space in a rocket (exploring the universe)",
    "Летит на ракете через червоточину на инопланетную планету Сиксим": "Flying through a wormhole to the alien planet Sixam in a rocket",
    "Участвует в космической гонке на ракете": "Competing in a space race in a rocket",
    "Устраивает диверсию в ракете (засоряет выхлопную трубу фруктом)": "Sabotaging the space rocket (stuffing exhaust pipe with fruit)",
    "Разбирает обломки разбившейся ракеты / ремонтирует ракету": "Salvaging crashed rocket debris / repairing the rocket",
    "Занимается вуху в космической ракете (в невесомости)": "WooHooing in the space rocket (in zero gravity)",
    "С восхищением разглядывает космическую ракету": "Admiring the space rocket in awe",
    "Идёт строить космическую ракету": "Heading to build a space rocket",
    "Идёт на стартовую площадку для запуска ракеты в космос": "Heading to launch pad for space rocket launch",
    "Идёт к космической ракете": "Heading towards the space rocket",

    # Bath & Shower Actions
    "Принимает грязевую ванну (СПА-процедура для релаксации)": "Taking a mud bath (relaxing spa treatment)",
    "Принимает грязевую ванну": "Taking a mud bath",
    "Принимает успокаивающую лавандовую ванну": "Taking a soothing lavender bath",
    "Принимает бодрящую цитрусовую ванну": "Taking an invigorating citrus bath",
    "Принимает молочную ванну с медом для мягкости кожи": "Taking a milk and honey bath for soft skin",
    "Принимает романтическую ванну с лепестками роз": "Taking a romantic bath with rose petals",
    "Принимает расслабляющую ванну с целебными травами": "Taking a relaxing herbal bath",
    "Принимает расслабляющую ароматическую ванну с маслами и солями": "Taking a relaxing aromatic bath with oils and salts",
    "Принимает расслабляющую ванну с пышной пеной": "Taking a relaxing bubble bath with rich foam",
    "Принимает расслабляющую ванну с пеной": "Taking a relaxing bubble bath",
    "Плещется в ванне и играет с резиновой уточкой": "Splashing in the bath and playing with a rubber ducky",
    "Купает и отмывает собаку в ванне": "Bathing and washing the dog in the bathtub",
    "Купает малыша в теплой ванне": "Bathing the toddler in a warm bath",
    "Принимает быстрый освежающий душ": "Taking a quick refreshing shower",
    "Принимает душ и весело поет во весь голос": "Taking a shower and cheerfully singing out loud",
    "Принимает душ и тихо плачет от грусти": "Taking a shower and crying quietly in sadness",
    "Принимает теплую расслабляющую ванну": "Taking a warm relaxing bath",
    "Чинит сантехнику в ванной": "Repairing bathroom plumbing",
    "Модернизирует и улучшает сантехнику в ванной": "Upgrading bathroom plumbing",
    "Идёт принимать грязевую ванну": "Heading to take a mud bath",
    "Идёт принимать ванну с пеной": "Heading to take a bubble bath",

    # PC Web / Internet Mode
    "Ищет тайные знания и информацию о вампирах в интернете": "Researching vampire lore and secrets online",
    "Изучает тайны и предания об оборотнях в сети": "Researching werewolf lore and legends online",
    "Изучает магические знания и заклинания в интернете": "Researching magic lore and spells online",
    "Ищет советы по воспитанию детей в интернете": "Researching parenting tips online",
    "Изучает советы для садоводов и агрономов в сети": "Researching gardening tips online",
    "Ищет фитнес-программы и советы по тренировкам в сети": "Researching workout and fitness routines online",
    "Ищет кулинарные рецепты и секреты шеф-поваров в интернете": "Looking up cooking recipes and culinary secrets online",
    "Изучает историю мирового искусства и живописи в сети": "Researching art history and painting online",
    "Изучает рецепты коктейлей и напитков в интернете": "Researching cocktail recipes and mixology online",
    "Изучает музыкальные уроки и табулатуры в сети": "Researching music lessons and tabs online",
    "Смотрит смешные видеоролики с животными в интернете": "Watching funny animal videos online",
    "Очищает историю браузера на компьютере": "Clearing browser history on the computer",
    "Жертвует деньги на благотворительность через интернет": "Donating money to charity online",
    "Жалуется и строчит гневные отзывы в интернете": "Complaining and venting online",
    "Публикует смешной мем в интернете": "Posting a funny meme online",
    "Читает отзывы о заведениях и ресторанах в интернете": "Reading restaurant and venue reviews online",
    "Публикует подробный отзыв о заведении в сети": "Posting a detailed review of a venue online",
    "Оплачивает коммунальные счета онлайн": "Paying utility bills online",
    "Оформляет денежный заем / кредит в банке онлайн": "Taking out a bank loan online",
    "Изучает комплекс мер и правила района в сети": "Researching neighborhood action plans and policies online",
    "Подает документы на поступление в университет онлайн": "Applying to university online",
    "Читает познавательные статьи в интернете": "Reading educational articles online",
    "Ищет информацию и серфит по сайтам в интернете": "Browsing websites and searching the internet",

    "Аккуратно извлекает окаменелость / кристалл из породы": "Carefully extracting a fossil / crystal from rock matrix",
    "Анализирует фондовый рынок и инвестирует в акции": "Analyzing stock market and investing in shares",
    "Бегает в гору на беговой дорожке": "Running uphill on treadmill",
    "Бегает на выносливость на беговой дорожке": "Endurance running on treadmill",
    "Бегает нагишом на публике (забег голышом / стрикинг)": "Streaking naked in public (streaking / naturism)",
    "Бронирует отпуск / планирует путешествие": "Booking vacation / travel online",
    "Бросает пошлые и соблазнительные взгляды": "Casting suggestive and seductive glances",
    "В восторге и возбуждении наблюдает за чужим сексом": "Excitedly and arousedly watching others have sex",
    "В панике прячется под диваном от ревущего монстра-пылесоса!": "Hiding in panic under sofa from roaring vacuum monster!",
    "В панике убегает от окна (был(а) замечен(а))": "Fleeing in panic from window (got spotted peeping)",
    "В ужасе / отвращении наблюдает за чужим сексом": "Watching others have sex in disgust / horror",
    "В шоке от увиденного: кто-то справляет нужду прямо на пол!": "Shocked: someone is relieving themselves right on the floor!",
    "В шоке от увиденной чужой наготы": "Shocked by seeing someone else's unexpected nudity",
    "В ярости ломает и крушит кукольный домик": "Furiously smashing and stomping the dollhouse",
    "Варит кофе": "Brewing fresh coffee",
    "Варит суп": "Simmering soup",
    "Варит чили": "Cooking chili",
    "Ведет онлайн-переговоры о повышении зарплаты": "Negotiating a pay raise online",
    "Ведет прямую трансляцию (стрим) для подписчиков": "Live-streaming for followers on computer",
    "Ведет раскопки в поисках сокровищ и окаменелостей": "Excavating looking for treasures and fossils",
    "Ведет стрим видеоигры для зрителей": "Live-streaming a video game for viewers",
    "Весело играет в догонялки (салки)": "Cheerfully playing a game of tag",
    "Весело шлепает по лужам и брызгается водой": "Splashing joyfully through rain puddles",
    "Взламывает сервер / базу данных (хакерство)": "Hacking server / database",
    "Возбуждённо заигрывает и наблюдает за чужим сексом": "Flirtatiously watching others have sex and joining in excitement",
    "Выбирает и заказывает подарки в интернет-магазине": "Shopping for gifts online",
    "Выносит / выбрасывает мусор": "Taking out / discarding trash",
    "Выполняет заказ на фрилансе": "Working on a freelance gig",
    "Вытирает личико и моет ручки для": "Wiping face and washing hands of",
    "Вытирает шваброй и убирает устроенный беспорядок на полу": "Mopping up a messy puddle on the floor",
    "Готовит буррито": "Making burritos",
    "Готовит горячий бутерброд с сыром": "Making a grilled cheese sandwich",
    "Готовит горячий бутерброд с сыром (жареный сыр)": "Making a grilled cheese sandwich",
    "Готовит карри": "Cooking curry",
    "Готовит курицу": "Roasting chicken",
    "Готовит лосось / рыбу": "Cooking salmon / fish",
    "Готовит макароны с сыром": "Making mac and cheese",
    "Готовит омлет": "Cooking an omelet",
    "Готовит пасту": "Cooking pasta",
    "Готовит пиццу": "Making pizza",
    "Готовит рыбу": "Cooking fish",
    "Готовит салат": "Preparing a salad",
    "Готовит свежий салат": "Tossing fresh salad",
    "Готовит спагетти / пасту": "Cooking spaghetti / pasta",
    "Готовит тако": "Making tacos",
    "Готовит хот-доги": "Grilling hot dogs",
    "Готовит яичницу / яйца": "Cooking scrambled eggs / sunny side up",
    "Гремит и играет с кастрюлями и сковородками на кухне": "Banging and playing with pots and pans in the kitchen",
    "Громко и довольно мурлычет": "Purring loudly and contentedly",
    "Громко и звонко лает, заявляя о своем присутствии": "Barking loudly, announcing presence",
    "Громко мяукает, требуя внимания к своей персоне": "Meowing loudly, demanding attention",
    "Громко плачет и капризничает": "Crying loudly and throwing a tantrum",
    "Грызет игрушку / пробует предмет на вкус (чешутся режущиеся зубки)": "Teething and chewing on a toy to soothe aching gums",
    "Гулит и лепечет что-то на своем детском языке («агу», «ба-ба»)": "Cooing and babbling baby talk ('goo-goo, ga-ga')",
    "Делает домашнее задание / курсовую работу": "Working on homework / coursework",
    "Делает домашнее задание под присмотром и помощью": "Doing homework under supervision and help of",
    "Делает покупки в интернет-магазине": "Shopping online",
    "Делает растяжку / разминку": "Stretching / warming up",
    "Делает селфи на телефон": "Taking a selfie on the phone",
    "Делает сэндвич / бутерброд": "Making a sandwich",
    "Делает тест на беременность в туалете": "Taking a pregnancy test in the bathroom",
    "Делает тосты": "Making toast",
    "Делает уборку / наводит чистоту": "Tidying up and cleaning around",
    "Делает французские тосты": "Making French toast",
    "Делает школьное домашнее задание": "Doing school homework",
    "Делится новостью / шуткой с подписчиками в соцсети": "Sharing update / joke with followers on social media",
    "Делится переживаниями и учится контролировать эмоции с": "Sharing feelings and learning emotional control with",
    "Демонстрирует интимные части тела на публике (эксгибиционизм)": "Flashing intimate body parts in public (exhibitionism)",
    "День": "Daytime",
    "Достигает оргазма от просмотра порно на компьютере": "Reaching orgasm from watching porn on computer",
    "Ест аппетитный стейк": "Eating a delicious steak",
    "Ест блинчики": "Eating pancakes",
    "Ест бургер": "Eating a burger",
    "Ест горячий сыр (бутерброд с жареным сыром)": "Eating grilled cheese sandwich",
    "Ест карри": "Eating flavorful curry",
    "Ест курицу": "Eating roasted chicken",
    "Ест макароны с сыром": "Eating mac and cheese",
    "Ест мороженое": "Eating ice cream",
    "Ест мясное блюдо": "Eating a savory meat dish",
    "Ест пасту": "Eating pasta",
    "Ест пиццу": "Eating a slice of pizza",
    "Ест попкорн": "Munching on popcorn",
    "Ест рамен / лапшу": "Eating ramen noodles",
    "Ест рыбу / морепродукты": "Eating seafood / fish",
    "Ест салат": "Eating a salad",
    "Ест свежий садовый салат": "Eating garden salad",
    "Ест спагетти": "Eating spaghetti",
    "Ест суп": "Eating a bowl of soup",
    "Ест суши": "Eating sushi",
    "Ест сэндвич": "Eating a sandwich",
    "Ест торт / сладкое": "Enjoying cake / dessert",
    "Ест тост": "Eating toast",
    "Ест хлопья с молоком": "Eating cereal with milk",
    "Ест хот-дог": "Eating a hot dog",
    "Ест яичницу": "Eating eggs",
    "Ест яичницу с тостами": "Eating eggs and toast",
    "Жарит бургеры": "Grilling burgers",
    "Жарит гамбургеры": "Grilling hamburgers",
    "Жарит еду на уличном гриле (барбекю)": "Grilling BBQ food on the outdoor grill",
    "Жарит стейк": "Sizzling a steak",
    "Забавно танцует и виляет попкой под музыку": "Adorably dancing and wiggling to the music",
    "Заваривает чай": "Brewing hot tea",
    "Загружает новые фотографии в соцсеть": "Uploading photos to social media",
    "Заказывает лекарства в онлайн-аптеке": "Ordering medicine from online pharmacy",
    "Заказывает пакеты с кровью в даркнете": "Ordering blood packs on dark web",
    "Заказывает семена для сада в интернет-магазине": "Ordering garden seeds online",
    "Занимается виртуальным романом (киберсексом)": "Engaging in cyber-romance (cyber-woohoo)",
    "Занимается гимнастикой на животике (Tummy Time) вместе с": "Doing tummy time exercises together with",
    "Занимается гимнастикой на животике вместе с": "Doing tummy time exercises together with",
    "Занимается групповым сексом [Оргия — {total_participants} участников]": "Engaging in group sex [Orgy — {total_participants} participants]",
    "Занимается групповым сексом [Тройничок / Секс втроем]": "Engaging in group sex [Threesome]",
    "Занимается групповым сексом [Четверничок / Секс вчетвером]": "Engaging in group sex [Foursome]",
    "Занимается интимной близостью (ВуХу) с": "Having intimate intimacy (WooHoo) with",
    "Занимается интимной гигиеной в туалете (использует прокладку / тампон)": "Managing menstrual hygiene in bathroom (using pad / tampon)",
    "Занимается карьерными делами на компьютере": "Attending to career tasks on computer",
    "Занимается любовью / сексом (Вуху)": "Making love / having sex (WooHoo)",
    "Занимается пробежкой на свежем воздухе": "Jogging outdoors in fresh air",
    "Занимается программированием / разработкой": "Programming and coding software",
    "Занимается самоудовлетворением / соло": "Engaging in solo self-pleasure (masturbation)",
    "Занимается сексом (Зачатие ребенка / Вуху)": "Having sex (Trying for Baby / WooHoo)",
    "Занимается сексом / интимом": "Engaging in sex / intimacy",
    "Занимается сексом / интимом (WickedWhims)": "Engaging in sex / intimacy (WickedWhims)",
    "Занимается спортом / тренируется": "Working out / exercising",
    "Занимается тяжелой тренировкой на силовом тренажере (качает мышцы)": "Heavy workout on weight machine (lifting weights)",
    "Застигнут(а) врасплох за просмотром порно": "Caught red-handed watching porn",
    "Играет в Blicblock (тетрис)": "Playing Blicblock",
    "Играет в Incredible Sports (спортивный симулятор)": "Playing Incredible Sports",
    "Играет в MySims Go": "Playing MySims Go",
    "Играет в Party Game": "Playing Party Game",
    "Играет в RPG / ролевую игру": "Playing an RPG game",
    "Играет в Road Rival (гонки)": "Playing Road Rival",
    "Играет в Sims Bustin' Out": "Playing Sims Bustin' Out",
    "Играет в The Sims Forever": "Playing The Sims Forever",
    "Играет в видеоигру на компьютере": "Playing a video game on the computer",
    "Играет в воображаемые сюжетные игры": "Engaged in imaginative storytelling games",
    "Играет в детские игрушки вместе с": "Playing with toys together with",
    "Играет в прятки «ку-ку» с": "Playing peek-a-boo with",
    # Chess & Table Games
    "Играет в шахматы": "Playing a game of chess",
    "Играет в шахматы за столиком": "Playing chess at the table",
    "Обдумывает следующий ход за шахматным столиком": "Pondering the next move at the chess table",
    "Тренируется и играет в шахматы в одиночку": "Practicing chess solo at the table",
    "Играет в судьбоносную шахматную партию со Смертью": "Playing a fateful game of chess with the Grim Reaper",
    "С интересом наблюдает за шахматной партией": "Watching the chess match with interest",
    "Обучает игре в шахматы и даёт наставления": "Mentoring in chess and giving guidance",
    "Играет в карты за игровым столиком": "Playing cards at the game table",
    "Играет в сабакк за игровым столиком": "Playing Sabacc at the game table",
    "Играет в «Не разбуди ламу»": "Playing Don't Wake the Llama",

    # EP01 Get to Work: Detective, Doctor, Scientist, Alien, Retail
    # Detective
    "Ведет допрос подозреваемого в комнате для допросов": "Interrogating suspect in the interrogation room",
    "Допрашивает подозреваемого в комнате для допросов": "Interrogating suspect in interrogation room",
    "Ведет допрос подозреваемого в роли «доброго полицейского»": "Interrogating suspect playing good cop",
    "Ведет жесткий допрос подозреваемого в роли «злого полицейского»": "Interrogating suspect playing bad cop",
    "Фотографирует задержанного для полицейского досье (магшот)": "Taking mugshot of suspect for police file",
    "Снимает отпечатки пальцев у задержанного на электронном сканере": "Taking suspect's fingerprints on electronic scanner",
    "Снимает отпечатки пальцев на месте преступления с помощью дактилоскопического порошка": "Dusting for fingerprints at crime scene",
    "Обыскивает задержанного на наличие улик и запрещенных предметов": "Searching suspect for evidence and contraband",
    "Отводит и запирает подозреваемого в тюремную камеру": "Locking suspect in jail cell",
    "Выпускает задержанного из тюремной камеры": "Releasing suspect from jail cell",
    "Анализирует зацепки и составляет схему расследования на доске улик": "Analyzing clues and mapping case on crime board",
    "Внимательно ищет зацепки и улики на месте преступления": "Searching for clues and evidence at crime scene",
    "Фотографирует важные улики на месте преступления": "Photographing evidence at crime scene",
    "Осматривает и документирует место преступления": "Inspecting and documenting crime scene",
    "Арестовывает подозреваемого и надевает наручники": "Arresting suspect and placing handcuffs",
    "Патрулирует улицы города и следит за правопорядком": "Patrolling city streets on police duty",
    "Выписывает штраф нарушителю общественного порядка": "Issuing citation for public disorder",
    "Оформляет ориентировку на розыск подозреваемого (APB) на компьютере": "Filing an All Points Bulletin (APB) on computer",
    "Составляет подробный полицейский отчёт по уголовному делу": "Filing detailed police case report on computer",

    # Doctor
    "Проводит сложную хирургическую операцию пациенту на операционном столе": "Performing surgical operation on surgery table",
    "Принимает роды у роженицы в больничной операционной": "Delivering baby in hospital operating room",
    "Принимает роды у роженицы в больнице": "Delivering baby in hospital",
    "Настраивает и калибрует больничный рентгеновский аппарат": "Calibrating hospital X-ray machine",
    "Делает рентгеновский снимок пациенту на аппарате рентгена": "Taking X-ray scan of patient on X-ray machine",
    "Проводит кардиологический стресс-тест пациенту на беговой дорожке": "Conducting cardiac stress test on patient on treadmill",
    "Измеряет температуру тела пациенту медицинским градусником": "Measuring patient's body temperature with thermometer",
    "Осматривает зрение и уши пациента медицинским фонариком": "Examining patient's eyes and ears with medical light",
    "Берет медицинский мазок из горла у пациента": "Taking throat swab from patient for medical analysis",
    "Делает лечебный укол пациенту на кушетке": "Giving medical injection to patient on exam bed",
    "Дает назначенную лечебную микстуру пациенту": "Administering prescribed medicine to patient",
    "Проводит медицинский осмотр пациента на смотровой кушетке": "Examining patient on medical examination bed",
    "Ставит точный медицинский диагноз пациенту": "Diagnosing patient's illness with medical diagnosis",
    "Заправляет и стерилизует больничную койку в палате": "Making and sanitizing hospital bed in ward",
    "Раздает лечебный больничный обед пациентам в палатах": "Serving hospital meals to patients in wards",
    "Выезжает на дом к заболевшему пациенту для срочного осмотра": "Making a house call to examine sick patient at home",

    # Scientist
    "Изобретает новое высокотехнологичное устройство на робототехническом конструкторе": "Inventing new high-tech device on Invention Constructor",
    "Модернизирует научное устройство на робототехническом конструкторе": "Upgrading scientific invention on Invention Constructor",
    "Стреляет из СимЛуча и замораживает сима в глыбу льда!": "Firing SimRay and freezing Sim in a block of ice!",
    "Трансформирует предмет с помощью фантастического луча СимЛуча": "Transforming object using SimRay beam",
    "Использует ментальный луч СимЛуча для контроля чужого разума": "Using SimRay mind control beam to control thoughts",
    "Использует высокотехнологичный научный СимЛуч": "Using high-tech scientific SimRay",
    "Посылает сигнал в глубокий космос и устанавливает контакт с пришельцами через антенну": "Beaming signal to deep space and contacting aliens via Satellite Dish",
    "Активирует защитный барьер спутниковой антенны от похищений пришельцами": "Activating Satellite Dish defense barrier against alien abductions",
    "Транслирует волны спутниковой антенны на весь район (всеобщий танец и счастье)": "Broadcasting satellite waves to neighborhood (hive mind dance & happiness)",
    "Управляет научной спутниковой антенной": "Operating scientific Satellite Dish",
    "Создает живого генетического клона сима на клонирующей машине": "Creating living genetic Sim clone on Cloning Machine",
    "Клонирует ценный предмет и ресурсы на клонирующей машине": "Cloning valuable item and resources on Cloning Machine",
    "Активирует межпространственную червоточину и отправляется на инопланетную планету Сиксим": "Activating interdimensional wormhole and traveling to alien planet Sixam",
    "Настраивает и калибрует генератор межпространственных червоточин": "Calibrating Electroflux Wormhole Generator",
    "Синтезирует экспериментальную научную сыворотку в химической лаборатории": "Synthesizing experimental scientific serum in chemistry lab",
    "Пьет экспериментальную научную сыворотку и ждет мутации эффекта": "Drinking experimental scientific serum and waiting for effects",
    "Тестирует действие экспериментальной научной сыворотки на подопытном": "Testing experimental scientific serum on test subject",
    "Проводит химические опыты с колбами и реагентами в лаборатории": "Conducting chemistry experiments with beakers and reagents in lab",
    "Испытывает мощное научное озарение («Эврика!») и генерирует гениальные идеи": "Experiencing breakthrough Eureka moment and generating brilliant ideas",
    "Берет образец ДНК для научных генетических исследований": "Collecting DNA sample for scientific genetic research",

    # Aliens
    "Похищается пришельцами на летающую тарелку в ослепительный луч света!": "Getting abducted by aliens into flying saucer via tractor beam!",
    "Применяет инопланетную способность стирания памяти": "Using alien memory erase ability",
    "Сканирует разум собеседника инопланетным биосканированием": "Scanning mind with alien bio-scan to analyze personality",
    "Считывает эмоции окружающих через инопланетную эмпатию": "Sensing emotions through alien empathy",
    "Снимает человеческую маскировку и обнажает истинный инопланетный облик": "Removing human disguise to reveal true alien form",
    "Надевает маскировку и принимает облик обычного человека": "Putting on human disguise to blend in as human",
    "Трансмутирует коллекционные кристаллы и металлы инопланетной силой": "Transmuting collectible crystals and metals with alien power",

    # Retail
    "Пробивает покупку на кассовом планшете и рассчитывает покупателя": "Ringing up customer's purchase on retail tablet",
    "Консультирует покупателя и увлеченно нахваливает товары магазина": "Pitching products and answering questions for retail customer",
    "Обсуждает цену на товар и предлагает скидку покупателю": "Discussing item price and offering discount to customer",
    "Пополняет запасы раскупленного товара на магазинных полках и витринах": "Restocking sold out merchandise on retail shelves and displays",
    "Хвалит сотрудника магазина за отличную работу с покупателями": "Praising store employee for excellent retail performance",
    "Строго отчитывает сотрудника магазина за лень и оплошности": "Strictly scolding store employee for slacking off",
    "Открывает свой магазин для покупателей и начинает торговлю": "Opening retail store for customers and starting business day",
    "Закрывает свой магазин для посетителей и подводит итоги продаж": "Closing retail store and reviewing daily sales summary",

    # Baking & Photography
    "Выпекает свежие кондитерские лакомства на фабрике кексов": "Baking fresh confectionery treats at Cupcake Factory",
    "Украшает свежую выпечку кондитерской глазурью и декором": "Decorating fresh pastries with icing and decorative toppings",
    "Занимается изысканной выпечкой (навык выпечки)": "Baking artisan pastries and bread (Baking Skill)",
    "Фотографирует моделей на профессиональном фотооборудовании в студии": "Taking photos of models in professional photo studio",

    # Social Dialogues EP01
    "Ведет допрос подозреваемого в лице": "Interrogating suspect",
    "Арестовывает и надевает наручники на": "Arresting and cuffing",
    "Опрашивает свидетеля о преступлении в лице": "Interviewing crime witness",
    "Проводит медицинский осмотр и лечит пациента в лице": "Examining and treating patient",
    "Просит предоставить образец ДНК у": "Asking for DNA sample from",
    "Тестирует экспериментальную научную сыворотку на": "Testing experimental serum on",
    "Стирает память инопланетной силой у": "Erasing memory with alien power of",
    "Сканирует личность инопланетным биосканированием у": "Scanning personality with alien bio-scan of",
    "Пробивает покупку на кассовом планшете для": "Ringing up purchase on tablet for",
    "Консультирует и нахваливает товар магазина для": "Pitching retail products to",

    # EP02 Get Together: Clubs, DJ, Dance, Pub Games, Cafe, Bonfire, Closet, Diving
    # DJ & Dance
    "Заводит и раскачивает танцующую толпу за диджейским пультом": "Hyping up dancing crowd at DJ booth",
    "Миксует и сводит взрывные клубные треки за диджейским пультом": "Mixing and blending explosive club tracks at DJ booth",
    "Модернизирует диджейский пульт (устанавливает лазеры и дым-машину)": "Upgrading DJ booth with lasers and fog machine",
    "Отрывается и танцует под зажигательный сет диджея": "Partying and dancing to energetic DJ set",
    "Выступает с диджейским сетом за пультом диджея": "Performing DJ set at the DJ booth",
    "Участвует в жарком танцевальном баттле на танцполе": "Competing in a heated dance battle on dance floor",
    "Исполняет синхронный групповой танец вместе с другими симами": "Performing synchronized group dance with other Sims",
    "Демонстрирует виртуозные танцевальные движения и трюки на танцполе": "Showing off impressive dance moves on dance floor",
    "Зажигает на клубном танцполе под ритмичную музыку": "Tearing up the dance floor to rhythmic club music",

    # Clubs
    "Демонстрирует тайное клубное рукопожатие": "Performing secret club handshake",
    "Пытается свергнуть лидера клуба в ходе тайного заговора!": "Attempting to overthrow club leader in a secret plot!",
    "Требует немедленно передать лидерство в клубе": "Demanding immediate transfer of club leadership",
    "Начинает официальное клубное собрание": "Starting an official club gathering",
    "Завершает клубное собрание": "Ending club gathering",
    "Участвует в клубном собрании вместе с соратниками": "Participating in club gathering with fellow members",

    # Pub Games
    "Играет в настольный футбол (кикер), крутя ручки игроков": "Playing foosball table spinning rods",
    "Играет в дартс и прицельно мечет дротики в яблочко мишени": "Playing darts aiming for the bullseye",
    "Играет в ретро-игру на клубном аркадном автомате": "Playing retro games on arcade machine",
    "Аккуратно вытаскивает бруски в настольной игре «Не разбуди ламу»": "Carefully pulling blocks in Don't Wake The Llama",

    # Cafe & Barista
    "Заказывает бодрящий эспрессо и выпечку у бариста в кафе": "Ordering invigorating espresso and pastry from barista",
    "Работает бариста за профессиональной эспрессо-машиной": "Working as barista at commercial espresso machine",
    "Наслаждается чашечкой ароматного эспрессо": "Savoring a cup of aromatic espresso",
    "Пользуется профессиональным эспрессо-баром в кафе": "Using espresso bar at the cafe",

    # Bonfire
    "Увлеченно танцует у пылающего ночного костра": "Dancing around roaring bonfire at night",
    "Разжигает большой костёр сухими поленьями": "Lighting big bonfire with dry firewood",
    "Подбрасывает свежие поленья в пылающий костёр": "Adding fresh logs into roaring bonfire",
    "Греет руки у потрескивающего пламени костра": "Warming hands by crackling bonfire flames",
    "Жарит сладкий зефир (маршмеллоу) на прутике над костром": "Roasting sweet marshmallows on a stick over bonfire",
    "Бросает порошок в костер и меняет цвет пылающего огня": "Throwing powder into bonfire to change flame color",
    "Отдыхает и общается у большого пылающего костра": "Relaxing and socializing around big bonfire",

    # Closet
    "Занимается страстным Вуху в гардеробе": "Having passionate WooHoo in walk-in closet",
    "Примеряет модные наряды в просторном гардеробе": "Trying on stylish outfits in walk-in closet",
    "Прячется в гардеробе и горько плачет в темноте": "Hiding in walk-in closet and crying in the dark",
    "Играет и прячется в гардеробе среди вешалок с одеждой": "Playing and hiding in closet among clothes hangers",
    "Находится в гардеробе для переодевания": "Inside walk-in closet",

    # Diving & Pool
    "С разбега прыгает в воду с вышки «бомбочкой» и поднимает кучу брызг!": "Jumping off diving platform doing a cannonball with a huge splash!",
    "Исполняет элегантный прыжок «ласточкой» с вышки в бассейн": "Performing graceful swan dive from diving platform",
    "Крутит зрелищное сальто назад при прыжке с трамплина": "Doing a spectacular backflip off diving platform",
    "Прыгает в воду с платформы для прыжков (трамплина)": "Jumping into water from diving platform",
    "Купается голышом (скинни-диппинг) в освежающей воде": "Skinny dipping in refreshing water",

    # Ruins & Maze
    "Занимается Вуху в лабиринте из живой изгороди": "Having WooHoo in hedge maze",
    "Бродит по загадочному лабиринту из живой изгороди в саду Шале": "Wandering through hedge maze in Chalet Gardens",
    "Исследует древние развалины города Винденбург": "Exploring ancient ruins of Windenburg",

    # Social Dialogues EP02
    "Демонстрирует тайное клубное рукопожатие перед": "Performing secret club handshake with",
    "Пытается свергнуть с поста лидера клуба": "Attempting to overthrow club leader",
    "Требует передать бразды правления клубом от": "Demanding club leadership from",
    "Приглашает вступить в свой клуб": "Inviting to join club",
    "С позором выгоняет из клуба": "Kicking out of the club",
    "Восторженно нахваливает свой клуб перед": "Enthusiastically praising club to",
    "Бросает вызов в танцевальном баттле": "Challenging to dance battle",
    "Играет в настольный футбол (кикер) против": "Playing foosball against",
    "Соревнуется в меткости в игре в дартс против": "Playing darts against",
    "Уединяется в гардеробе для романтического Вуху с": "Hooking up in walk-in closet with",
    "Уединяется для романтического Вуху в лабиринте кустов с": "Sneaking away for maze WooHoo with",

    # EP03 City Living: Apartments, Festivals, Basketball, Karaoke, Murals
    # Apartments
    "Яростно стучит в дверь соседей и жалуется на невыносимый шум!": "Furiously banging on neighbor's door complaining about unbearable noise!",
    "Стучит в дверь квартиры соседей": "Knocking on apartment neighbors' door",
    "Торжественно вручает ключ от своей квартиры": "Giving apartment key to Sim",
    "Забирает ключ от своей квартиры": "Taking back apartment key from Sim",
    "Вызывает арендодателя квартиры для срочного ремонта труб и проводки": "Calling apartment landlord for urgent repairs of pipes and wiring",
    "Выбрасывает мешок с мусором в домовой мусоропровод высотки": "Throwing trash bag down high-rise trash chute",
    "Изучает расписание фестивалей и правила дома на доске объявлений": "Reading festival schedule and house rules on apartment bulletin board",

    # Festivals
    "Пьет чай из лепестков сакуры на Фестивале романтики": "Drinking sakura petal tea at Romance Festival",
    "Осыпает окружающих лепестками сакуры на фестивале": "Showering crowd with sakura petals at festival",
    "Участвует в испытании огненным карри на Фестивале специй!": "Taking on spicy curry challenge at Spice Festival!",
    "Покупает экзотические специи и пряности в фестивальной палатке": "Buying exotic spices at festival stall",
    "Сражается за победу в хакатоне программистов на фестивале «Умникон»": "Competing in programmers' hackathon at GeekCon",
    "Сражается в киберспортивном турнире на фестивале «Умникон»": "Competing in gaming tournament at GeekCon",
    "Проводит запуск испытательной ракеты на фестивале «Умникон»": "Launching test rocket at GeekCon",
    "Посещает фестиваль технологий и видеоигр «Умникон»": "Visiting GeekCon technology and gaming festival",
    "Выступает за команду шутников на фестивале «Шутки и забавы»": "Representing jokesters at Humor & Hijinks Festival",
    "Выступает за команду проказников на фестивале «Шутки и забавы»": "Representing pranksters at Humor & Hijinks Festival",
    "Веселится на городском фестивале «Шутки и забавы»": "Having fun at Humor & Hijinks Festival",
    "Запускает праздничные фейерверки на фестивале «Шутки и забавы»": "Launching fireworks at Humor & Hijinks Festival",
    "Азартно торгуется с продавцом за винтажные вещи на блошином рынке": "Haggling with vendor for vintage items at Flea Market",
    "Осматривает диковинки и антиквариат на городском блошином рынке": "Browsing antiques and collectibles at Flea Market",

    # Basketball & Karaoke
    "Выполняет эффектный бросок сверху (слэм-данк) в баскетбольное кольцо!": "Performing spectacular slam dunk into basketball hoop!",
    "Тренирует броски и трехочковые попадания в баскетбольное кольцо": "Practicing shooting hoops and three-pointers",
    "Играет в уличный баскетбол на городской площадке": "Playing street basketball on neighborhood court",
    "Играет в баскетбол на уличной спортивной площадке": "Playing basketball on street sports court",
    "Поет зажигательный дуэт у микрофона караоке": "Singing energetic duet at karaoke machine",
    "Выступает на сцене в городском конкурсе караоке": "Performing on stage in city karaoke contest",
    "Эмоционально поет любимый трек в микрофон караоке": "Emotionally singing favorite song into karaoke microphone",

    # Murals & Culture
    "Дерзко закрашивает чужое граффити поверх своим тегом": "Boldly defacing mural tagging graffiti over it",
    "Рисует стрит-арт картину цветными мелками на асфальте": "Creating street art pavement chalk mural",
    "Создает яркое городское граффити баллончиком с краской на стене": "Painting vibrant urban street graffiti on the wall",
    "Расслабленно пускает ароматные мыльные пузыри через кальян": "Relaxingly blowing fragrant bubbles from bubble blower",
    "Учится ловко есть азиатскую уличную еду палочками": "Practicing eating street food with chopsticks",
    "Покупает порцию горячей уличной еды в городском киоске": "Buying hot street food from city food stall",
    "Ведет дружескую беседу с умным говорящим унитазом": "Having friendly chat with smart talking toilet",
    "Пользуется высокотехнологичным биде умного унитаза": "Using high-tech bidet of smart talking toilet",
    "Использует умный говорящий туалет с подсветкой": "Using smart illuminated talking toilet",
    "Выступает на городской улице за чаевые от прохожих": "Busking on city street for tips from pedestrians",
    "Восхищается выступлением уличного артиста и дает чаевые": "Admiring street performer and tipping them",
    "Поджигает фитиль и запускает зрелищный салют-фейерверк в небо!": "Lighting fuse and launching spectacular fireworks into the sky!",

    # City Careers
    "Произносит пламенную политическую речь с городской трибуны": "Delivering passionate political speech from podium",
    "Возглавляет уличный митинг протеста с мегафоном и плакатом": "Leading street protest demonstration with megaphone and sign",
    "Собирает пожертвования на общественную кампанию": "Collecting donations for civic political campaign",
    "Ведет прямую трансляцию в соцсетях для тысяч своих подписчиков": "Livestreaming on social media for thousands of followers",
    "Придирчиво дегустирует блюдо и выносит строгую оценку критика": "Critically tasting dish and delivering food review",
    "Внимательно оценивает произведение искусства профессиональным взглядом критика": "Evaluating artwork with critic's professional eye",

    # Social Dialogues EP03
    "Яростно жалуется на шум соседу в лице": "Furiously complaining about apartment noise to",
    "Торжественно вручает ключ от своей квартиры": "Giving apartment key to",
    "Забирает ключ от своей квартиры у": "Taking back apartment key from",
    "Требует срочного ремонта квартиры от арендодателя в лице": "Demanding urgent apartment repairs from landlord",
    "Осыпает романтическими лепестками сакуры": "Showering with romantic sakura petals",
    "Обсуждает остроту фестивального карри с": "Discussing spicy festival curry with",
    "Поет зажигательный дуэт в микрофон караоке вместе с": "Singing karaoke duet with",
    "Играет в уличный баскетбол 1 на 1 против": "Playing street basketball against",
    "Агитирует внести благотворительное пожертвование в фонд": "Canvassing for campaign donation from",
    "Выносит строгую профессиональную оценку блюду": "Delivering critic's evaluation on food to",

    # EP04 Cats & Dogs: Pets, Vet Clinic, Training, Agility, Care, Lighthouse
    # Vet Clinic & Surgery
    "Проводит плановую процедуру стерилизации питомца": "Performing routine spay/neuter procedure on pet",
    "Проводит операцию по отмене стерилизации питомца": "Performing surgery to reverse spay/neuter on pet",
    "Проводит сложную ветеринарную операцию четвероногому пациенту": "Performing complex veterinary surgery on four-legged patient",
    "Проводит ветеринарный осмотр четвероногого пациента на смотровом столе": "Performing veterinary checkup on four-legged patient on exam table",
    "Измеряет температуру тела питомца ветеринарным термометром": "Taking pet's body temperature with veterinary thermometer",
    "Слушает сердцебиение и дыхание питомца стетоскопом": "Listening to pet's heartbeat and breathing with stethoscope",
    "Берет кожный соскоб и осматривает уши питомца на паразитов": "Taking skin swab and inspecting pet's ears for parasites",
    "Успокаивает напуганного четвероногого пациента": "Calming frightened four-legged patient",
    "Ставит точный ветеринарный диагноз четвероногому пациенту": "Making accurate veterinary diagnosis for four-legged patient",
    "Делает лечебный укол четвероногому пациенту на смотровом столе": "Giving medical injection/shot to four-legged patient on exam table",
    "Надевает защитный ветеринарный конус на шею питомца": "Putting protective cone collar on pet's neck",
    "Дает назначенное лекарство заболевшему питомцу": "Administering prescribed medicine to sick pet",
    "Изготавливает лекарственные препараты и лакомства на ветеринарном лабораторном столе": "Crafting medicines and treats on veterinary laboratory table",
    "Регистрирует заболевшего питомца через электронный терминал ветклиники": "Checking in sick pet at veterinary electronic kiosk",

    # Dog Training & Agility
    "Обучает собаку полезным командам и закрепляет навык дрессировки": "Training dog useful commands and reinforcing obedience skills",
    "Тренирует собаку прыгать через барьеры на полосе препятствий": "Training dog to jump hurdles on agility obstacle course",
    "Направляет собаку в тренировочный туннель на полосе препятствий": "Guiding dog through training tunnel on agility course",
    "Тренирует собаку огибать слаломные стойки на полосе препятствий": "Training dog to navigate slalom weave poles on agility course",
    "Проводит собаку по полосе препятствий на лучшее время": "Running dog through agility obstacle course for best time",

    # Care & Walking
    "Бегает трусцой на бодрой пробежке вместе с собакой": "Briskly jogging together with dog",
    "Гуляет с собакой на поводке по окрестностям": "Walking dog on leash around neighborhood",
    "Обрабатывает шерсть питомца специальным шампунем от блох": "Treating pet's fur with special flea shampoo",
    "Купает собаку в теплой ванне с мыльной пеной": "Giving dog a warm bath with soapy suds",
    "Заботливо вычесывает шерсть питомца мягкой щеткой": "Gently brushing pet's coat with soft brush",
    "Насыпает свежий корм в миску для любимого питомца": "Filling pet food bowl with fresh food",
    "Готовит изысканное домашнее блюдо для любимого питомца": "Cooking gourmet pet food for beloved pet",
    "Угощает питомца аппетитным лакомством": "Giving delicious treat to pet",
    "Строго отчитывает питомца за непослушание и плохие манеры": "Firmly scolding pet for misbehavior and poor manners",
    "Ласково хвалит и гладит питомца за послушание": "Affectionately praising and petting pet for good behavior",

    # Play & Bonding
    "Дразнит кошку красной точкой лазерной указки": "Playing with cat using red laser pointer dot",
    "Играет с кошкой гибкой дразнилкой с перышками": "Playing with cat with feather wand teaser",
    "Угощает кошку душистой кошачьей мятой": "Treating cat with fragrant catnip",
    "Бросает мячик и с азартом играет в апорт с собакой": "Throwing ball playing fetch excitedly with dog",
    "Запускает летающую тарелку (фрисби) в воздух для собаки": "Throwing flying frisbee disc into air for dog",
    "Умиленно чешет пузико четвероногому любимцу": "Lovingly rubbing belly of four-legged pet",
    "С любовью обнимает и прижимает к себе питомца": "Lovingly hugging and cuddling pet",

    # Lighthouse & Strays
    "Занимается головокружительным Вуху на вершине маяка": "Having breathtaking WooHoo at the top of the lighthouse",
    "Любуется панорамой океана со смотровой площадки маяка в Бриндлтон-Бэй": "Admiring ocean panorama from observation deck of Brindleton Bay lighthouse",
    "Официально усыновляет бездомного питомца": "Officially adopting a stray pet",
    "С грустью оплакивает ушедшего четвероногого друга на кладбище питомцев": "Mourning departed four-legged friend at pet cemetery",

    # Social Dialogues EP04
    "Обучает командам и трюкам питомца по кличке": "Training commands and tricks to pet named",
    "Гуляет на поводке с четвероногим другом по кличке": "Walking on leash with four-legged friend named",
    "Заботливо вычесывает щеткой шерсть любимца": "Gently brushing coat of pet",
    "Купает в теплой ванне четвероногого друга по кличке": "Bathing in warm bath four-legged friend named",
    "Угощает аппетитным лакомством любимца по кличке": "Giving delicious treat to pet named",
    "Строго отчитывает за плохое поведение питомца по кличке": "Firmly scolding for misbehavior pet named",
    "Ласково гладит и хвалит за послушание питомца по кличке": "Gently praising for obedience pet named",
    "Дразнит красной точкой лазерной указки любимца": "Playing with red laser pointer with pet",
    "Бросает мяч и играет в апорт с четвероногим другом": "Throwing ball playing fetch with four-legged friend",
    "Проводит профессиональный ветеринарный осмотр питомца": "Performing professional vet examination on pet",
    "Проводит сложную хирургическую операцию четвероногому пациенту": "Performing complex surgery on four-legged patient",

    # EP05 Seasons: Weather, Holidays, Skating, Bees, Floristry, Scarecrow, Traditions
    # Weather & Climate
    "В шоке и копоти: в сима только что ударила настоящая молния!": "Shocked and covered in soot: Sim was just struck by lightning!",
    "В панике вздрагивает от раскатов грома и прячется от грозы": "Panicking and cowering from thunder, hiding from thunderstorm",
    "Радостно бегает и плещется в дождевых лужах": "Happily splashing and playing in rain puddles",
    "Весело шлепает по грязным лужам и пачкается в лечебной грязи": "Cheerfully stomping in mud puddles and getting muddy",
    "Идет под раскрытым зонтом, укрываясь от дождя": "Walking under an open umbrella shielding from the rain",
    "Дрожит от пронизывающего ледяного холода и пытается согреться": "Shivering from freezing cold and trying to warm up",
    "Изнывает от невыносимой палящей жары и обливается потом": "Sweating and suffering from intense sweltering heatwave",
    "Загорает на солнышке в шезлонге или на полотенце": "Sunbathing in the sun on a lounge chair or towel",

    # Winter & Snow
    "Лепит снеговика из свежевыпавшего снега": "Building a snowman out of fresh snow",
    "Лежит на сугробе и делает снежного ангела": "Lying on a snowdrift making a snow angel",
    "Азартно играет в снежки и лепит снежные комья": "Playfully having a snowball fight and making snowballs",
    "Счищает лопатой сугробы снега с дорожек вокруг дома": "Shoveling snowdrifts from walkways around the house",

    # Autumn Leaves & Raking
    "Занимается страстным осенним Вуху в куче шуршащих листьев": "Having passionate autumn leaf pile WooHoo",
    "Весело прыгает и играет в шуршащей куче осенних листьев": "Playfully jumping and frolicking in rustling autumn leaf pile",
    "Сжигает собранную кучу сухих осенних листьев": "Burning a collected pile of dry autumn leaves",
    "Сгребает сухие осенние листья граблями в аккуратную кучу": "Raking dry autumn leaves into a neat pile",

    # Seasonal Sports & Cooling Off
    "Неловко теряет равновесие и шлепается на ледовом катке": "Awkwardly losing balance and falling on the ice skating rink",
    "Выполняет изящные фигурные вращения и пируэты на катке": "Performing graceful figure skating spins and routines on the rink",
    "Катается на роликах по треку, отрабатывая скольжение": "Roller skating on the track practicing gliding",
    "Катается на коньках по ледовому катку, нарезая круги": "Ice skating on the rink doing laps",
    "Задорно бросает шарики с водой и устраивает водяной бой": "Throwing water balloons and having a water balloon fight",
    "Освежается и плещется в надувном детском бассейне": "Cooling off and splashing in inflatable kiddie pool",
    "С визгом пробегает через разбрызгиватель для газона, спасаясь от жары": "Playfully running through lawn sprinkler cooling off from the heat",
    "Регулирует домашний термостат (настраивает обогрев / кондиционер)": "Adjusting home thermostat (setting heating / air conditioning)",

    # Weather Controller
    "Вызывает сокрушительную грозу на пульте управления погодой": "Triggering a devastating thunderstorm using the weather controller",
    "Вызывает снежную бурю с помощью погодного контроллера": "Summoning a blizzard using the weather controller",
    "Вызывает аномальную жару с помощью погодного контроллера": "Summoning a heatwave using the weather controller",
    "Перенастраивает климат с помощью фантастического аппарата управления погодой": "Changing the climate using Dr. June's weather machine",

    # Floristry, Bees & Scarecrow
    "Окуривает и ароматизирует цветочную композицию редким цветочным ароматом": "Scenting floral arrangement with rare floral fragrance",
    "Составляет изысканную цветочную композицию на столике флориста": "Creating an exquisite floral arrangement on the flower table",
    "Собирает свежий душистый мед из пчелиного улья": "Collecting fresh fragrant honey from the bee box",
    "Налаживает гармоничную связь с пчелиной семьей в улье": "Bonding with the bee colony in the bee box",
    "Отправляет рой верных пчел с особым поручением": "Sending a swarm of faithful bees on a special errand",
    "Отмахивается от разгневанного роя пчел и чешет укусы": "Swatting away angry swarm of bees and scratching stings",
    "Бережно ухаживает за пчелиным ульем в защитном костюме пасечника": "Tending bee box in protective beekeeper suit",
    "Проверяет карманы пугала Заплатки в поисках редких семян": "Checking Patchy the Scarecrow's pockets for rare seeds",
    "Оживленно беседует и дружит с ожившим пугалом по имени Заплатка": "Chatting and befriending Patchy the Straw Man scarecrow",

    # Holidays, Father Winter & Traditions
    "Яростно дерется с Дедом Морозом за мешок с подарками!": "Furiously fighting with Father Winter for the bag of presents!",
    "Просит праздничный подарок у Деда Мороза": "Asking Father Winter for a holiday present",
    "Общается с Дедом Морозом в праздничный вечер": "Socializing with Father Winter on holiday evening",
    "Наряжает праздничную елку гирляндами и яркими игрушками": "Decorating the holiday tree with garlands and ornaments",
    "С нетерпением распаковывает праздничный подарок под елкой": "Eagerly unwrapping holiday present under the tree",
    "Вручает праздничный подарок": "Giving a holiday gift",
    "Достает праздничные гирлянды и украшения из чердачной коробки с декором": "Retrieving holiday decorations from the attic decoration box",
    "Готовит пышное праздничное застолье (грандиозный ужин)": "Cooking a grand holiday feast for family and guests",
    "Зажигает праздничные свечи на традиционной меноре / кинаре": "Lighting holiday candles on traditional menorah / kinara",
    "Радостно поет праздничные гимны и песни": "Joyfully singing holiday carols and songs",
    "С замиранием сердца смотрит новогодний обратный отсчет до полуночи": "Watching New Year's countdown to midnight on TV",
    "Дает себе твердое новогоднее обещание изменить жизнь к лучшему": "Making a New Year's resolution to improve life",
    "Приветствует сказочного Цветочного кролика и берет цветы": "Greeting the magical Flower Bunny and receiving flowers",

    # Social Dialogues EP05
    "Азартно играет в снежки против": "Playfully having a snowball fight against",
    "Устраивает задорный бой водяными шариками против": "Having a water balloon fight against",
    "Торжественно вручает праздничный подарок для": "Presenting a holiday gift to",
    "Выпрашивает новогодний подарок у": "Asking for a holiday present from",
    "Яростно дерется за мешок с подарками с": "Furiously fighting for present sack with",
    "Оживленно болтает о саде и урожае с пугалом по имени": "Chatting about garden and crops with scarecrow named",
    "Натравливает рой жужжащих пчел на": "Sending a swarm of buzzing bees at",
    "Поет праздничные новогодние песни вместе с": "Singing holiday songs together with",

    # EP06 Get Famous: Acting, Studio, Media, Music, Drone, Fame, Vault, Paparazzi
    # Acting Career & Studio
    "Работает стилистом-гримером на съемочной площадке": "Working as hair and makeup stylist on movie set",
    "Сидит в кресле стилиста на киностудии: наносит сценический грим и делает прическу": "Sitting in hair and makeup chair on movie set getting styled",
    "Примеряет сценический костюм для съемок на костюмерном подиуме": "Trying on stage costume on wardrobe pedestal",
    "Докладывает режиссеру о готовности к съемкам сцены": "Informing director ready to perform scene on set",
    "Играет зрелищную сцену поединка перед кинокамерой": "Performing spectacular combat scene in front of movie camera",
    "Играет чувственную романтическую сцену перед кинокамерой": "Performing sensual romantic scene in front of movie camera",
    "Произносит драматический монолог перед кинокамерой на съемочной площадке": "Delivering dramatic monologue in front of movie camera on set",
    "Отыгрывает уморительную комедийную сцену перед кинокамерой": "Delivering hilarious comedy scene in front of movie camera",
    "Исполняет музыкальный номер с пением и танцем перед камерой": "Performing musical number with singing and dancing on camera",
    "Отыгрывает ключевую сцену дубля на съемочной площадке киностудии": "Performing scene take on movie studio set",
    "Усердно репетирует драматическую роль и отрабатывает мимику перед зеркалом": "Practicing dramatic acting role and expressions in the mirror",
    "Снимается в фантастической сцене на фоне зеленого экрана хромакея": "Acting in sci-fi scene in front of green screen",

    # Media Production, Music & Drone
    "Монтирует свежий видеоролик, добавляя динамичные переходы и спецэффекты": "Editing fresh video adding transitions and visual effects",
    "Загружает смонтированный видеоролик на популярную медиаплатформу": "Uploading edited video to popular media platform",
    "Записывает эмоциональное видеопрохождение компьютерной игры для своего влога": "Recording emotional gaming walkthrough video for vlog",
    "Записывает модный видеообзор и советы по красоте для подписчиков": "Recording fashion beauty review video for subscribers",
    "Записывает яркий видеоролик за профессиональным столом медиапроизводства": "Recording video at professional media production station",
    "Записывает готовый музыкальный трек на диск для отправки на лейбл": "Burning finished music track to CD to send to record label",
    "Создает и сводит авторский электронный музыкальный трек в студии": "Producing and mixing original electronic track in music studio",
    "Ведет прямой эфир (стрим) в сеть с помощью парящего вокруг дрона": "Livestreaming with flying streaming drone",
    "Записывает видеоматериалы для блога с помощью летающего стримингового дрона": "Recording blog footage with flying streaming drone",

    # Celebrity Life & Paparazzi
    "Ловит сенсационные кадры знаменитостей под прицелом объектива": "Snapping photos of celebrities under flashing paparazzi cameras",
    "Эффектно позирует папарацци на красной дорожке под вспышки фотокамер": "Striking glamorous poses for paparazzi on the red carpet",
    "Раздает именные автографы восторженным поклонникам": "Signing autographs for excited fans",
    "С восторгом выпрашивает автограф у знаменитости": "Excitedly asking celebrity for an autograph",
    "Делает памятное селфи со знаменитостью": "Taking memorable selfie with celebrity",
    "Прячется от назойливых папарацци и фанатов в темных очках и шляпе": "Hiding from paparazzi and fans in celebrity disguise",
    "Падает в восторженный обморок от благоговения перед кумиром": "Fainting in awe upon seeing their celebrity idol",
    "Одержимый назойливый фанат: тайно следит за звездой и роется в мусоре кумира": "Obsessed Stan: secretly stalking celebrity and rummaging through trash",
    "Пытается проскользнуть мимо вышибалы в элитную VIP-зону клуба": "Trying to sneak past bouncer into elite VIP club area",
    "Непреклонно охраняет VIP-вход в клуб и отсеивает недостойных посетителей": "Sternly guarding VIP club entrance turning away commoners",
    "Торжественно закладывает свою именную плитку-звезду на звездной Аллее славы": "Placing personalized celebrity tile on Starlight Boulevard Walk of Fame",

    # Money Vault & Luxury
    "Занимается роскошным Вуху на куче денег в гигантском сейфе": "Having luxurious WooHoo on a pile of money in the vault",
    "Сладко дремлет на огромной горе хрустящих купюр и золота в сейфе": "Sleeping peacefully on huge pile of cash and gold in money vault",
    "Купается в роскоши и подбрасывает золотые монеты в денежном хранилище": "Living in luxury playing with gold coins in money vault",
    "Любуется горами своего богатства в бронированном денежном хранилище": "Admiring enormous wealth inside armored money vault",
    "Показно сорит деньгами и разбрасывает пачки наличных перед толпой": "Flaunting wealth making it rain cash in front of the crowd",

    # Social Dialogues EP06
    "Раздает именные автографы для": "Signing autographs for",
    "С трепетом выпрашивает автограф у": "Asking for an autograph from",
    "Делает памятное совместное селфи со звездой": "Taking memorable selfie with celebrity",
    "В экстазе падает в обморок от восторга перед": "Fainting in awe before",
    "Показно сорит деньгами и хвастается богатством перед": "Flaunting wealth and making it rain before",
    "Пытается подкупить или убедить пропустить в VIP-зону вышибалу в лице": "Trying to bribe or convince VIP bouncer",
    "Докладывает о готовности к съемке сцены режиссеру в лице": "Reporting ready to perform scene to director",
    "Берет эксклюзивное интервью для СМИ у знаменитости": "Conducting exclusive media interview with celebrity",

    # EP07 Island Living (Sulani, Mermaids, Dolphins, Watercraft, Scuba, Beach, Volcano, Kava)
    # Waterfall
    "Принимает освежающий тропический душ в хрустальных струях водопада": "Taking a refreshing tropical shower under the waterfall",
    "Весело резвится и играет в прохладных струях тропического водопада": "Playfully splashing and frolicking under the waterfall",
    "Ищет и ловит редких островных лягушек у подножия водопада": "Searching for rare tropical frogs at the base of the waterfall",
    "Отдыхает и любуется струями живописного тропического водопада": "Relaxing and admiring the scenic tropical waterfall",
    "Занимается страстным романтическим Вуху под струями тропического водопада": "Having passionate tropical waterfall WooHoo",

    # Mermaids & Sirens
    "Трубит в витую морскую раковину, призывая океанских духов и русалок": "Blowing into a conch shell to summon ocean spirits and merfolk",
    "Заманивает чарующей песней сирены на океанскую глубину": "Luring Sims into ocean depths with enchanting Siren's Call",
    "Поет чарующую колыбельную русалки": "Singing mermaid's Charmer's Lullaby",
    "Поет вдохновляющую русалочью песню": "Singing mermaid's Inspiring Berceuse",
    "Поет элегию былых времен (древняя печальная русалочья песнь)": "Singing Aeons' Elegance (ancient mournful mermaid elegy)",
    "Поет леденящий душу реквием ночи русалок": "Singing chilling mermaid Night's Requiem",
    "Использует древнюю русалочью силу для призыва грозы и шторма над океаном": "Using ancient merfolk power to summon an ocean storm",
    "Рассеивает грозовые тучи и призывает ясное солнце над островом": "Dispelling storm clouds to summon clear sunny skies over the island",
    "Утягивает сима на дно океана русалочьей хваткой!": "Dragging a Sim down to the ocean floor with a mermaid grip!",
    "Дарит волшебный океанский русалочий поцелуй": "Giving a magical ocean mermaid kiss",
    "Принимает целебную ванну с ламинарией и океанскими водорослями": "Taking a healing kelp and seaweed bath",
    "Поедает волшебную водоросль-ламинарию для пробуждения русалочьей сущности": "Eating mermadic kelp to awaken inner mermaid nature",
    "Превращается в морское создание, явив великолепный сияющий хвост": "Transforming into a sea creature revealing a magnificent mermaid tail",
    "С грацией скользит в толще океанских волн с русалочьим хвостом": "Swimming gracefully through ocean waves with a mermaid tail",
    "Нежится на прибрежных скалах в лучах солнца в русалочьем обличье": "Basking in the sun on coastal rocks in mermaid form",

    # Dolphins & Turtles
    "Обучает дельфина акробатическим трюкам и сальто": "Teaching dolphin acrobatic tricks and flips",
    "Кормит свежей рыбой из рук дружелюбного дельфина": "Feeding fresh fish by hand to friendly dolphin",
    "Ласково гладит дельфина по шелковистой гладкой спине": "Gently petting dolphin on its silky smooth back",
    "Дружелюбно переговаривается и обменивается щелчками с дельфином": "Chatting and clicking friendly sounds with dolphin",
    "Весело играет и плещется в теплых волнах с дельфином": "Playing and splashing in warm waves with dolphin",
    "Задорно брызгается океанской водой с дельфином": "Playfully splashing ocean water with dolphin",
    "Получает мокрый дружеский поцелуй в щеку от дельфина": "Receiving a wet friendly cheek kiss from dolphin",
    "Восхищенно общается с дельфином в океане": "Enthusiastically interacting with dolphin in the ocean",
    "Бережно сопровождает новорожденных морских черепашат в океан": "Guiding newborn sea turtle hatchlings safely to the ocean",
    "С умилением наблюдает за морскими черепахами в лагуне": "Adoringly watching sea turtles in the lagoon",

    # Watercraft
    "Выполняет рискованные головокружительные трюки на водном мотоцикле (Aqua Zip)": "Performing daring stunts and tricks on an Aqua Zip water scooter",
    "Рассекает лазурные океанские волны на быстроходном водном мотоцикле (Aqua Zip)": "Cruising across azure ocean waves on an Aqua Zip water scooter",
    "Рыбачит в открытом океане с борта традиционного каноэ": "Fishing in the open ocean from an outrigger canoe",
    "Дремлет и покачивается на ласковых волнах в деревянном каноэ": "Napping and drifting peacefully on gentle waves in a canoe",
    "Неспешно скользит по тихим водам лагуны на островном каноэ с веслом": "Paddling smoothly across calm lagoon waters in an island canoe",

    # Scuba & Snorkel
    "Ныряет с аквалангом в поисках затонувших сокровищ и жемчуга на дне рифа": "Scuba diving at reef looking for sunken treasures and pearls",
    "Занимается подводной охотой с гарпуном на океанском рифе": "Spearfishing along the ocean coral reef",
    "Исследует коралловый риф и фотографирует подводную жизнь с аквалангом": "Surveying coral reef and photographing marine life with scuba gear",
    "Занимается спортивным фридайвингом в океанских глубинах на задержке дыхания": "Free diving in deep ocean waters on a single breath",
    "Погружается на морское дно с аквалангом у глубоководного буя": "Deep-sea scuba diving at the buoy",
    "Плавает с маской и трубкой, любуясь разноцветными тропическими рыбками и кораллами": "Snorkeling while admiring colorful tropical fish and coral reefs",

    # Beach, Sand & Sunbathing
    "Строит искусный песчаный замок со рвом и башенками на пляже": "Building an elaborate sandcastle with moats and towers on the beach",
    "Ваяет причудливую скульптуру из влажного пляжного песка": "Sculpting whimsical art out of wet beach sand",
    "Шутливо закапывает друга по горло в пляжный песок": "Playfully burying a friend up to the neck in beach sand",
    "Прочесывает песок на пляже в поисках ракушек, крабов и окаменелостей": "Beachcombing for seashells, crabs, and fossils",
    "Увлеченно играет и возится в мягком теплом песке на берегу океана": "Playing happily in the soft warm sand on the ocean beach",
    "Страдает от саднящего солнечного ожога после долгого дня на пляже": "Suffering from a painful sunburn after a long day on the beach",
    "Загорает нагишом без одежды на уединенном тропическом пляже": "Sunbathing nude on a secluded tropical beach",
    "Беззаботно нежится и загорает на пляжном шезлонге под теплым солнцем Сулани": "Sunbathing comfortably on a beach lounger under the Sulani sun",
    "Лениво покачивается на надувном матрасе на зеркальной глади океана": "Floating peacefully on an inflatable lounger in the calm ocean",

    # Conservation & Ecology
    "Очищает пляж от пластика, мусора и выброшенного штормом сора": "Cleaning plastic, trash, and storm debris off the beach",
    "Очищает океанскую лагуну и риф от ядовитых отходов и плавающего мусора": "Cleaning toxic waste and floating trash from ocean lagoon and reef",
    "Берет пробы океанской воды для экологического анализа состояния рифа": "Taking ocean water samples for environmental reef analysis",
    "Уничтожает инвазивные растения и чужеродные сорняки, спасая экосистему Сулани": "Spraying invasive weeds to preserve Sulani's ecosystem",
    "В благоговении общается с древними духами острова Сулани и получает их благословение": "Communing in awe with ancient Sulani island spirits to receive their blessing",

    # Culture, Kava, Pit Barbecue & Volcano
    "Заваривает традиционный корень кавы в большой резной деревянной чаше": "Brewing traditional kava root in a large carved wooden bowl",
    "Произносит традиционный островной тост «Була!» и выпивает чашу кавы": "Raising a traditional 'Bula!' island toast and drinking kava",
    "Пьет расслабляющий традиционный напиток кава из ореховой чаши": "Drinking relaxing traditional kava from a coconut shell",
    "Разжигает угли и раскаляет камни в традиционной земляной печи (яме для жаркого)": "Heating rocks and tending embers in a traditional pit barbecue earth oven",
    "Достает из раскаленной земляной ямы сочное запеченное жаркое по-сулански": "Serving tender slow-roasted Kalua pork from the pit barbecue",
    "Томит традиционное жаркое калуа из свинины и рыбы в подземной печи под пальмовыми листьями": "Slow-roasting traditional Kalua pork and fish in the earth oven",
    "Виртуозно крутит горящие огненные жезлы в захватывающем островном танце огня": "Performing a thrilling island fire dance with spinning flaming knives",
    "Танцует зажигательный полинезийский танец под ритмичные островные мотивы": "Dancing an energetic Polynesian island dance to upbeat rhythms",
    "Рассказывает древние предания и мифы архипелага Сулани": "Sharing ancient Sulani island folklore and legends",
    "В панике спасается от грохочущего извержения действующего вулкана Сулани!": "Panicking and fleeing the rumbling eruption of Sulani's active volcano!",
    "С тревогой наблюдает за дымящимся жерлом действующего вулкана": "Anxiously watching the smoking caldera of the active volcano",
    "Раскалывает молотом застывшую вулканическую бомбу в поисках ценных минералов": "Cracking open a cooled volcanic bomb to discover valuable minerals and geodes",
    "С опаской трогает остывающий раскаленный кусок вулканической лавы": "Cautiously touching a cooling chunk of molten volcanic lava rock",

    # Social Dialogues EP07
    "Произносит традиционный островной тост с чашей кавы для": "Raising a traditional kava toast for",
    "Приглашает на традиционный островной праздник кавы": "Inviting to a traditional kava party",
    "Дружелюбно щелкает и переговаривается с дельфином по имени": "Clicking and chatting with dolphin named",
    "Кормит свежей рыбой из рук дельфина по имени": "Feeding fresh fish by hand to dolphin named",
    "Нежно гладит по гладкой спине дельфина по имени": "Gently petting on the back dolphin named",
    "Весело играет и плещется в волнах с дельфином по имени": "Splashing and playing in waves with dolphin named",
    "Дарит волшебный океанский русалочий поцелуй для": "Giving a magical mermaid kiss to",
    "Заманивает чарующей песней сирены на глубину океана": "Luring into ocean depths with Siren's Call",
    "Поет чарующую колыбельную русалки для": "Singing Charmer's Lullaby to",
    "Поет вдохновляющую русалочью песню для": "Singing Inspiring Berceuse to",
    "Рассказывает древние предания и мифы Сулани для": "Sharing ancient Sulani folklore with",
    "Расспрашивает о традициях и духах архипелага Сулани у": "Asking about Sulani traditions and spirits from",
    "Шутливо закапывает в теплый пляжный песок": "Playfully burying in warm beach sand",

    # EP08 Discover University (Academics, Debate, Robotics, Servos, Bicycles, Keg, Ping Pong, Sprites)
    # Academics & Studies
    "Сдает готовую курсовую работу профессору через компьютер": "Submitting completed term paper to professor on computer",
    "Вычитывает и редактирует курсовую работу на компьютере": "Proofreading and editing term paper on computer",
    "Пишет и оформляет академическую курсовую работу на компьютере": "Writing and formatting academic term paper on computer",
    "Защищает итоговую презентацию перед академической комиссией": "Presenting final presentation to academic panel",
    "Репетирует защиту итоговой презентации перед доской": "Practicing final presentation defense before the board",
    "Работает над итоговой презентацией (собирает материалы на доске)": "Working on final presentation board compiling materials",
    "Посещает открытую гостевую лекцию профессора в аудитории": "Attending guest professor lecture in lecture hall",
    "Прилежно конспектирует лекцию преподавателя в аудитории": "Diligently taking notes during lecture in hall",
    "Спешит на университетскую лекцию в учебный корпус": "Heading to university class in academic building",
    "Усердно зубрит конспекты и готовится к университетским экзаменам": "Cramming notes and studying for university exams",
    "Читает сложный академический учебник по профильному предмету": "Reading complex academic textbook for course",

    # Research & Debate
    "Записывает академические видеоматериалы и лекции в исследовательском архиве": "Recording academic lectures and videos at research archive machine",
    "Изучает научные материалы и проводит исследования в архивном хранилище": "Researching topics and studying materials at research archive machine",
    "Выступает на трибуне дебатов, оттачивая ораторское мастерство и риторику": "Speaking at debate podium practicing public speaking and rhetoric",
    "Участвует в академических дебатах на трибуне": "Participating in academic debate at podium",

    # Robotics & Servos
    "Получает сильный удар током от искрящего робототехнического станка!": "Receiving a severe electric shock from sparking robotics workstation!",
    "Торжественно активирует новосозданного разумного робота Серво!": "Ceremoniously activating newly crafted sentient Servo robot!",
    "Собирает сложнейшего человекоподобного робота Серво на станке!": "Crafting sophisticated humanoid Servo robot at robotics workstation!",
    "Проводит тонкую настройку и улучшение робота Серво": "Fine-tuning and enhancing Servo robot",
    "Ремонтирует поврежденные сервоприводы робота Серво": "Repairing damaged servomotors of Servo robot",
    "Восполняет заряд аккумулятора на подзарядной станции (режим питания робота)": "Recharging battery at charging station (robot power mode)",
    "Собирает автономного робота-уборщика (Clean-Bot) на робототехническом станке": "Crafting autonomous Clean-Bot at robotics workstation",
    "Конструирует бота-садовника (Gardener-Bot) на робототехническом станке": "Crafting Gardener-Bot at robotics workstation",
    "Собирает бота-ремонтника (Fix-Bot) на робототехническом станке": "Crafting Fix-Bot at robotics workstation",
    "Создает развлекательного пати-бота (Party-Bot) на робототехническом станке": "Crafting entertaining Party-Bot at robotics workstation",
    "Конструирует летающий квадрокоптер на робототехническом станке": "Crafting flying quadcopter drone at robotics workstation",
    "Конструирует электронные схемы и детали на робототехническом станке": "Crafting electronic mechanisms and circuits at robotics workstation",
    "Работает над изобретениями за робототехническим станком": "Working on inventions at robotics workstation",

    # Bicycles
    "Звонит в звонкий звонок велосипеда, распугивая зазевавшихся студентов": "Ringing bicycle bell warning distracted students",
    "Мчится на велосипеде по университетскому кампусу": "Riding bicycle swiftly across university campus",

    # Secret Society & Mascots
    "Оставляет почтительное подношение на алтаре духов природы (Орден Зачарованных)": "Leaving respectful offering at sprite altar (Order of Enchantment)",
    "Посещает таинственное святилище духов природы (Орден Зачарованных)": "Visiting mysterious sprite shrine (Order of Enchantment)",
    "Ощущает присутствие мерцающих духов-спрайтов и купается в их благословении": "Feeling presence of glowing sprites and basking in their blessing",
    "Зажигает в ростовом костюме талисмана университета перед восторженными фанатами": "Hype dancing in university mascot costume before cheering fans",
    "Исполняет боевую кричалку и подбадривает команду университета": "Chanting fight song and cheering on university team",

    # Juice Keg, Pong & Shenanigans
    "Выполняет безумную акробатическую стойку на руках на бочонке сока (Keg Stand)!": "Performing an acrobatic Keg Stand handstand on the juice keg!",
    "Наливает пенный бодрящий сок прямо из студенческого бочонка": "Pouring refreshing juice straight from the campus keg",
    "Тусуется у студенческого бочонка с соком": "Hanging out near the campus juice keg",
    "Азартно забрасывает шарики в стаканчики в студенческом сок-понге": "Tossing ping pong balls into cups playing campus juice pong",
    "Играет в настольный теннис (пинг-понг) на кампусе": "Playing table tennis (ping pong) on campus",
    "Обматывает туалетной бумагой и раскрашивает статую соперничающего университета!": "TP-ing and defacing rival university statue with toilet paper and paint!",
    "Организует шумный студенческий митинг и скандирует лозунги через мегафон": "Organizing noisy student protest and chanting slogans through megaphone",

    # Social Dialogues EP08
    "Вступает в жаркий академический спор и дебаты с": "Engaging in heated academic debate with",
    "Убеждает железными логическими аргументами и риторикой": "Convincing with airtight logical rhetoric",
    "Громко скандирует университетскую кричалку вместе с": "Loudly chanting university fight song with",
    "Яростно спорит об итоговой оценке за курс с преподавателем": "Arguing fiercely about final course grade with professor",
    "Поднимает студенческий пластиковый стаканчик с соком за": "Raising a plastic cup juice toast to",
    "Шепотом расспрашивает о тайном студенческом обществе у": "Whispering questions about secret society to",
    "Язвительно высмеивает команду соперничающего университета перед": "Taunting rival university team before",

    # EP09 Eco Lifestyle (Dumpster, Fabricator, Candle, Fizz, Insects, Meat Wall, Solar, Smog)
    # Dumpster
    "Ныряет в мусорный бак в поисках выброшенных сокровищ и антикварной мебели": "Dumpster diving for discarded treasures and antique furniture",
    "Занимается фриганизмом: выуживает съедобную выброшенную еду из мусорного бака": "Practicing freeganism diving for discarded food in the dumpster",
    "Сладко дремлет внутри мягкого мусорного контейнера": "Napping peacefully inside the dumpster",
    "Ныряет и копается в огромном мусорном контейнере в поисках полезных вещей": "Dumpster diving in search of useful discarded items",
    "Занимается экстремальным Вуху прямо в мусорном контейнере": "Having extreme dumpster WooHoo",

    # Fabricator & Recycler
    "Перерабатывает скопившийся мусор и вещи в полезные эко-детали и биты": "Recycling trash and items into useful bits and pieces",
    "Обливается яркой краской в результате аварии на преобразователе!": "Getting covered in paint from a fabricator mishap!",
    "Изготавливает дизайнерскую эко-мебель на гигантском преобразователе": "Fabricating designer eco-furniture on the fabricator",
    "Создает эко-детали для бытовых улучшений на преобразователе": "Fabricating eco-upgrade parts on the fabricator",
    "Работает за высокотехнологичным преобразователем (3D-печать из вторсырья)": "Operating the high-tech fabricator (3D-printing from recycled bits)",

    # Candle Making
    "Вырезает затейливые узоры на остывающей резной восковой свече": "Carving intricate decorative patterns onto a cooling wax candle",
    "Макает фитили в чан с расплавленным воском, создавая цилиндрические свечи": "Dipping wicks into molten wax to craft dipped candles",
    "Выплавляет ароматные соевые свечи на столе для свечеварения": "Crafting fragrant soy candles at the candle making table",

    # Juice Fizziness & Carbonation
    "Загружает сочные фрукты и сою в бродильный чан аппарата для шипучки": "Loading ingredients into the fizzing station fermenting tank",
    "Запускает процесс карбонизации и выдерживает партию домашней шипучки": "Starting carbonation and brewing a batch of homemade fizzy juice",
    "Разливает искрящуюся шипучку по фирменным бутылкам": "Bottling sparkling fizzy juice into custom bottles",
    "Смакует терпкую шипучку собственного брожения из запотевшего бокала": "Sipping crisp homemade carbonated juice from a chilled glass",
    "Колдует над аппаратом для шипучки, создавая авторские газированные напитки": "Crafting carbonated fizzy beverages at the fizzing station",

    # Insect Farm
    "Подкармливает колонию домашних насекомых свежим компостом и объедками": "Feeding insect farm colony with compost and food scraps",
    "Собирает сверчковую муку и экологичное биотопливо с фермы насекомых": "Harvesting cricket flour and eco-biofuel from insect farm",
    "С нежностью обнимает любимого ручного жучка на ферме насекомых": "Affectionately cuddling a pet beetle from the insect farm",
    "Ухаживает за копошащейся колонией полезных насекомых на эко-ферме": "Tending to the crawling colony of beneficial bugs on the insect farm",

    # Vertical Garden & Meat Wall
    "Срезает сочные куски культивированного био-мяса прямо с вертикальной стены!": "Harvesting cuts of cruelty-free faux meat directly from the vertical meat wall!",
    "Массирует и поливает плантацию искусственного мяса на вертикальной ферме": "Massaging and hydrating the artificial meat wall on the vertical garden",
    "Ухаживает за растениями и зеленью в инновационном вертикальном саду": "Tending to plants and herbs in the innovative vertical garden",

    # Alternative Energy
    "Очищает фотоэлементы и настраивает солнечные панели на крыше": "Cleaning photovoltaic cells and tuning rooftop solar panels",
    "Регулирует и обслуживает ветряной генератор для выработки чистой энергии": "Maintaining wind turbine to generate clean green power",
    "Проверяет конденсационные фильтры автономного сборщика атмосферной росы": "Checking condensation filters of the off-the-grid atmospheric dew collector",

    # Civil Design, Smog & N.A.P.
    "Очищает городской воздух от токсичного смога с помощью ручного смогососа": "Vacuuming toxic smog and industrial emissions with the smog vacuum",
    "Проектирует экологические городские преобразования на чертежном планшете": "Drafting eco-friendly municipal city plans on the drafting tablet",
    "Задыхается и кашляет от едкого промышленного смога на задымленной улице": "Choking and coughing from acrid industrial smog on polluted street",
    "Голосует за утверждение экологического комплекса мер района у доски голосования": "Voting on Neighborhood Action Plans at the voting board",

    # Social Dialogues EP09
    "Активно агитирует голосовать за комплекс мер района": "Actively campaigning for Neighborhood Action Plan",
    "Собирает подписи за отмену комплекса мер у": "Gathering signatures to repeal Neighborhood Action Plan from",
    "С восторгом рассказывает о раздельном сборе мусора и переработке для": "Enthusiastically sharing recycling tips with",
    "Гордо хвастается жизнью без отходов и фриганизмом перед": "Proudly bragging about zero-waste lifestyle and freeganism to",
    "С негодованием жалуется на удушливый смог и грязь в районе для": "Complaining about industrial smog and pollution to",
    "Угощает искрящейся домашней шипучкой собственного разлива": "Offering homemade fizzy juice to",
    "Делится секретами свечеварения и создания ароматических свечей с": "Sharing candle making secrets with",

    # EP10 Snowy Escape (Winter Sports, Onsen, Kotatsu, Hiking, Yamachan, Vending)
    # Winter Sports
    "Стремительно съезжает на лыжах по заснеженному склону горы Комореби": "Skiing rapidly down the snowy slopes of Mt. Komorebi",
    "Выполняет рискованные трюки на лыжах на крутом склоне высокой сложности": "Performing risky ski tricks on the expert slope of Mt. Komorebi",
    "Кубарем катится со снежного склона после падения с лыж!": "Tumbling down the snowy slope after a skiing wipeout!",
    "Мчится вниз по заснеженной трассе на сноуборде": "Snowboarding down the snowy slopes of Mt. Komorebi",
    "Выполняет захватывающие трюки на сноуборде на заснеженном склоне": "Performing thrilling snowboard tricks on the snowy slope",
    "Снимает экстремальный спуск на сноуборде на экшн-камеру": "Recording extreme snowboard run with an action camera",
    "Кубарем летит в сугроб после неудачного приземления на сноуборде!": "Crashing into a snowdrift after a failed snowboard landing!",
    "С восторгом съезжает со снежной горки на санках": "Happily sledding down the snowy bunny slope",
    "Вылетает из санок в пушистый сугроб на вираже!": "Flying out of the sled into a soft snowdrift on a sharp turn!",

    # Onsen Hot Springs
    "Принимает очищающий душ перед погружением в целебный источник онсэн": "Taking a cleansing shower before soaking in the onsen hot springs",
    "Блаженно нежится в горячих минеральных водах источника онсэн": "Blissfully soaking in the healing thermal waters of the onsen",
    "Занимается чувственным Вуху в парящих водах горячего источника онсэн": "Having sensual onsen hot springs WooHoo",
    "Плещется и греется в термальном источнике онсэн": "Splashing and warming up in the steaming onsen hot springs",

    # Rock Climbing & Mountain Excursion
    "Надевает и проверяет альпинистское снаряжение перед штурмом скалы": "Equipping and inspecting rock climbing gear before tackling the wall",
    "Покрывает ладони мелом для надежного хвата на скалодроме": "Chalking hands for secure grip on the rock climbing wall",
    "Карабкается вверх по отвесной обледенелой скале горы Комореби": "Climbing up the sheer icy rock wall of Mt. Komorebi",
    "Срывается со скалы, повисая на страховочной веревке!": "Slipping off the rock wall and dangling on the safety rope!",
    "Внимательно оценивает маршрут подъема по скале": "Carefully planning and breaking down the rock climbing route",
    "Возглавляет горную экспедицию на вершину горы Комореби": "Leading the mountain climb excursion to the peak of Mt. Komorebi",
    "Отдыхает в базовом лагере перед финальным штурмом вершины": "Resting at the mountain base camp before the final ascent",
    "Занимается романтическим Вуху в горной палатке на склоне Комореби": "Having cozy mountain tent WooHoo on Mt. Komorebi",
    "Занимается экстремальным Вуху в ледяной пещере на вершине Комореби": "Having extreme ice cave WooHoo at the peak of Mt. Komorebi",

    # Kotatsu, Hot Pot & Traditions
    "Греет ноги под теплым одеялом традиционного стола котацу": "Warming feet under the cozy blanket of traditional kotatsu table",
    "Наслаждается уютной трапезой за традиционным столом котацу": "Enjoying a cozy meal gathered around traditional kotatsu table",
    "Уютно дремлет, согревая ноги под одеялом стола котацу": "Cozying up and napping under the warm kotatsu blanket",
    "Варит наваристый сукияки в горячем котелке хот-пот": "Cooking rich savory sukiyaki in the steaming hot pot",
    "С аппетитом пробует обжигающие кусочки из кипящего котелка хот-пот": "Savory tasting piping hot morsels from bubbling hot pot",
    "Неуклюже пытается удержать еду бамбуковыми палочками": "Clumsily trying to balance food with bamboo chopsticks",
    "Мастерски орудует традиционными палочками для еды": "Masterfully handling traditional dining chopsticks",
    "Снимает уличную обувь у порога в знак уважения к дому": "Taking off outdoor shoes at the genkan entryway in respect",
    "Переобувается в уютные домашние тапочки": "Slipping into comfortable indoor slippers",

    # Hiking, Forest Spirits & Shrines
    "Совершает медитативное паломничество к горному святилищу": "Taking a meditative hiking pilgrimage to the mountain shrine",
    "Любуется заснеженными кедрами и бамбуковым лесом во время хайкинга": "Admiring snowy cedars and bamboo grove while hiking scenic trails",
    "Отчаянно отбивается от роя злобных лесных шершней на тропе!": "Desperately swatting away a swarm of aggressive forest hornets on the trail!",
    "Загадывает заветное желание при встрече с крошечными лесными духами Кодама": "Making a heartfelt wish upon encountering tiny Kodama forest spirits",
    "С трепетом принимает благословение духов горы Комореби": "Reverently receiving the blessing of the Mt. Komorebi mountain spirits",
    "Кланяется и почтительно загадывает желание у священного алтаря": "Bowing and respectfully wishing at the sacred mountain altar",
    "С восторгом обнимает маскота Ямачана и делает веселое селфи": "Enthusiastically hugging mascot Yamachan and snapping a fun selfie",

    # Vending Machines
    "Покупает горячий суп или коллекционную капсулу в торговом автомате": "Buying hot canned soup or a Simmi capsule from the vending machine",
    "Яростно трясет торговый автомат, пытаясь выбить застрявшую банку!": "Furiously shaking the vending machine to dislodge a stuck can!",
    "Чудом уворачивается от рухнувшего торгового автомата!": "Narrowly dodging the collapsing vending machine!",

    # Social Dialogues EP10
    "С уважением и глубоким почтением кланяется": "Bowing respectfully and deeply to",
    "С восхищением рассказывает о заснеженных вершинах Комореби для": "Admiringly talking about the snowy peaks of Mt. Komorebi to",
    "Приглашает погреться под теплым одеялом котацу и отведать хот-пот": "Inviting to warm up under cozy kotatsu blanket and share hot pot with",
    "Увлеченно обсуждает маршрут горной экспедиции и проверку снаряжения с": "Enthusiastically discussing mountain excursion routes and climbing gear with",
    "Расхваливает целебную расслабляющую силу горячих источников онсэн перед": "Praising healing relaxation of onsen hot springs to",
    "Предостерегает о нападениях лесных шершней и коварных духов на тропе": "Warning about forest hornets and tricky spirits on the trail to",
    "С возмущением жалуется на застрявшую банку в торговом автомате для": "Indignantly complaining about a stuck can in the vending machine to",

    # EP11 Cottage Living (Farm Animals, Cows, Llamas, Chickens, Giant Crops, Cross-Stitch, Canning, Errands)
    # Chickens & Coop
    "Занимается деревенским Вуху в уютном курятнике": "Having rustic chicken coop WooHoo",
    "В ужасе удирает от разъяренного петуха-драчуна!": "Fleeing in terror from an enraged fighting rooster!",
    "Собирает свежие фермерские яйца из теплого курятника": "Collecting fresh farm eggs from the warm chicken coop",
    "Рассыпает отборное зерно во дворе для кур и цыплят": "Scattering grain in the yard for chickens and chicks",
    "Вычищает солому и наводит идеальный порядок в курятнике": "Cleaning out straw and tidying up the chicken coop",
    "Нежно обнимает и гладит любимую пушистую курочку": "Gently hugging and petting a beloved fluffy chicken",
    "Ухаживает за пернатыми обитателями деревенского курятника": "Caring for feathered friends in the rustic chicken coop",

    # Cows & Shed
    "Доит довольную корову в хлеву, наполняя ведро парным молоком": "Milking a contented cow in the animal shed filling a bucket of fresh milk",
    "Заботливо вычесывает и чистит щеткой бока коровы": "Lovingly grooming and brushing the cow's sides in the shed",
    "Угощает корову свежим сеном и аппетитным лакомством": "Treating the cow with fresh hay and a delicious animal treat",
    "С нежностью обнимает ласковую домашнюю корову": "Affectionately hugging the gentle domestic cow",
    "Заботится и ухаживает за пятнистой коровой в хлеву": "Tending to and caring for the spotted cow in the animal shed",

    # Llamas & Wool
    "Утирается после неожиданного и меткого плевка вредной ламы!": "Wiping off face after getting unexpectedly spat on by a sassy llama!",
    "Аккуратно состригает мягкую разноцветную шерсть с пушистой ламы": "Carefully shearing soft colorful wool from the fluffy llama",
    "Тщательно расчесывает густую мягкую шерсть ламы": "Thoroughly brushing the llama's thick soft wool",
    "Балует пушистую ламу полезными лакомствами и хрустящей травой": "Pampering the fluffy llama with healthy treats and crunchy grass",
    "Занимается уходом за грациозной фермерской ламой": "Grooming and caring for the graceful farm llama",

    # Wild Animals (Rabbits, Birds, Foxes)
    "Наряжает очаровательного дикого кролика в крошечный вязаный свитер": "Dressing an adorable wild rabbit in a tiny knitted sweater",
    "В панике отбивается от нападения свирепого кролика-убийцы!": "Panicking and defending against a ferocious killer rabbit attack!",
    "С умилением принимает лесной подарок от дружелюбного кролика": "Touched to receive a sweet forest gift from a friendly wild rabbit",
    "Мило общается и заводит дружбу с диким лесным кроликом": "Socializing and befriending a gentle wild forest rabbit",
    "Заводит душевную песню в унисон с лесными птицами у замшелого пня": "Singing a soulful song together with wild flock of birds by mossy stump",
    "Отбивается от внезапно налетевшей стаи разъяренных птиц!": "Fighting off a sudden attack by a flock of furious wild birds!",
    "Наблюдает за порхающими дикими птицами и слушает их пение": "Watching fluttering wild birds and listening to their melodies",
    "Решительно прогоняет хитрую рыжую лису от курятника": "Resolutely chasing away a sneaky red fox from the chicken coop",
    "Приманивает осторожную дикую лисицу вкусным угощением": "Luring a cautious wild fox with a tasty treat to make friends",
    "Наблюдает за крадущейся по двору дикой лисой": "Watching a wild fox stealthily prowling across the yard",

    # Giant Crops & Finchwick Fair
    "Выставляет выращенных питомцев и гигантские овощи на ярмарке в Финчвике": "Submitting prized farm animals and giant vegetables at the Finchwick Fair",
    "Торжественно срезает грандиозную гигантскую культуру с рекордным весом!": "Triumphantly harvesting a colossal record-weight oversized crop!",
    "Удобряет почву специальными смесями для роста исполинских овощей": "Fertilizing soil with special blends for massive giant vegetable growth",
    "Кропотливо ухаживает за гигантскими культурами на грядке": "Painstakingly tending to giant oversized crops in the garden patch",

    # Crafts, Canning, Errands & Picnics
    "Ойкает, больно уколов палец швейной иглой при вышивании!": "Ouch! Pricking finger with a needle while cross-stitching!",
    "Вышивает затейливые пасторальные узоры крестиком на деревянных пяльцах": "Cross-stitching intricate pastoral patterns on a wooden hoop",
    "Варит ароматный домашний джем и закатывает банки с консервацией": "Cooking fragrant homemade jam and canning preserve jars on stove",
    "Выполняет важные сельские поручения для жителей городка Хэнфорд-он-Бэгли": "Running important village errands for residents of Henford-on-Bagley",
    "Раскладывает плетеную корзину и наслаждается деревенским пикником на траве": "Unpacking a wicker basket and enjoying a rustic picnic on the grass",

    # Social Dialogues EP11
    "С восторгом рассказывает о жизни на ферме и сельских заботах для": "Enthusiastically sharing farm life stories and rustic chores with",
    "Делится секретами выращивания гигантских овощей и ухода за огородом с": "Sharing giant vegetable growing secrets and gardening tips with",
    "Гордо хвастается собранными золотыми и обсидиановыми яйцами перед": "Proudly bragging about golden and obsidian eggs to",
    "Предупреждает о коварных лисах, охотящихся на курятники, для": "Warning about crafty foxes stalking hen coops to",
    "С гордостью демонстрирует вышитую крестиком картину": "Proudly showing off framed cross-stitch needlework to",
    "Обсуждает поручения местных жителей и ярмарку в Финчвике с": "Discussing villager errands and Finchwick Fair with",
    "С обидой жалуется на плевок вредной ламы для": "Resentfully complaining about llama spit to",

    # EP12 High School Years (Pier Carnival, Prom, Academics, Pranks, Cheerleading, Trendi)
    # Pier Rides & Carnival
    "Катается на колесе обозрения, любуясь панорамой озера Коппердейл": "Riding the Ferris wheel enjoying the scenic panorama of Lake Copperdale",
    "Занимается романтическим Вуху в кабинке колеса обозрения": "Having romantic Ferris wheel WooHoo",
    "Визжит от ужаса и восторга внутри зловещего дома с привидениями": "Screaming in spooky delight inside the haunted house attraction",
    "Занимается щекочущим нервы Вуху в доме с привидениями": "Having thrilling haunted house WooHoo",
    "Романтично покачивается в лодочке аттракциона «Туннель любви»": "Gently drifting in a swan boat through the Tunnel of Love",
    "Занимается нежным Вуху в лодочке аттракциона «Туннель любви»": "Having sweet tunnel of love WooHoo in swan boat",
    "Корчит забавные рожицы и делает памятную ленту снимков в фотобудке": "Making goofy faces and snapping photo strips in the photo booth",
    "Занимается тайным страстным Вуху в фотобудке": "Having secret passionate photo booth WooHoo",
    "С разбега ныряет с деревянного пирса в прохладные воды озера": "Diving headfirst off the wooden pier into cool lake waters",

    # Prom & Promposal
    "Торжественно делает предложение пойти на выпускной бал с плакатом": "Grandly asking to prom with a creative promposal banner",
    "Голосует за короля и шута выпускного бала у урны для голосования": "Casting vote for prom royalty and jester at the ballot box",
    "Кружится в медленном романтическом танце на выпускном балу": "Slow dancing romantically at high school prom",
    "Зажигает на праздничном выпускном балу в школьном актовом зале": "Partying and dancing at high school prom in the auditorium",

    # Academics & High School
    "Уныло отбывает наказание в классе после уроков под надзором учителя": "Drearily serving after-school detention under teacher's watchful eye",
    "Нервно списывает со шпаргалки во время сдачи школьного экзамена!": "Nervously peeking at cheat sheets during high school exam!",
    "Сосредоточенно решает сложный вариант выпускного школьного экзамена": "Focusing intently on solving difficult high school final exam",
    "Старательно строчит конспект на лекции в школьном классе": "Diligently taking lecture notes at classroom desk",
    "Сидит за школьной партой и внимательно слушает урок учителя": "Sitting at classroom desk listening attentively to teacher",
    "Украшает дверцу личного школьного шкафчика постерами и гирляндами": "Decorating personal locker with posters and fairy lights",
    "Тайком перекусывает из запасов в своем школьном шкафчике": "Sneaking a quick snack stash from personal locker",
    "Перебирает учебники и тетради у школьного шкафчика": "Sorting textbooks and notebooks at the school locker",
    "Выслушивает строгий выговор в кабинете директора школы": "Listening to a stern reprimand in the principal's office",

    # Pranks & Rebellion
    "Подкладывает зловонную бомбочку в чужой школьный шкафчик!": "Planting a foul stink capsule inside someone's school locker!",
    "Тайно рисует неприличную карикатуру на классной доске перед уроком!": "Secretly drawing a hilarious prank cartoon on classroom whiteboard!",
    "Хулиганит, выкрикивая шутки в школьный микрофон громкой связи!": "Mischievously shouting pranks into the school PA system intercom!",
    "Тайком вылезает через окно по шпалере, сбегая на ночную тусовку!": "Sneaking out bedroom window down trellis ladder to a late-night party!",
    "В страхе призывает Городскую Легенду перед школьным зеркалом в темноте": "Fearfully summoning the Urban Myth before the school bathroom mirror",

    # Extracurriculars
    "Отрабатывает сальто и синхронные связки с помпонами на чирлидинг-мате": "Practicing cheerleading flips and synchronized pom-pom stunts on cheer mat",
    "Тренирует броски и передачи мяча для американского футбола": "Practicing football passes and long throws on the field",

    # Trendi, Boba & Pillow Fight
    "С удовольствием потягивает сладкий чай с шариками тапиоки бабл-ти": "Enjoying sweet boba tea with chewy tapioca pearls",
    "Выставляет собранный модный образ на продажу в приложении Тренди": "Listing curated fashion outfit for sale on Trendi app",
    "Придирчиво выбирает винтажную одежду на рейлах в магазине «Чай и тренды»": "Browsing thrift clothing racks at ThriftTea for vintage gems",
    "Весело кидается подушками в разгаре боя подушками на кровати": "Joyfully throwing pillows during an energetic pillow fight on bed",

    # Social Dialogues EP12
    "Торжественно вручает самодельный плакат и приглашает на выпускной бал": "Grandly presenting creative promposal banner asking to prom",
    "Шепотом сплетничает о кандидатах в короли и королевы выпускного бала с": "Whispering prom royalty and jester gossip with",
    "Хвастается продажами стильных луков на Тренди и подписчиками перед": "Bragging about Trendi fashion sales and followers to",
    "С возмущением жалуется на несправедливое школьное наказание после уроков для": "Indignantly complaining about detention after school to",
    "Заговорщицким шепотом рассказывает пугающую городскую легенду для": "Conspiratorially whispering spooky urban myths to",
    "Подговаривает устроить дерзкую проделку в школьном коридоре вместе с": "Conspiring to pull off a daring high school corridor prank with",
    "Приглашает поболтать и выпить сладкий бабл-ти в кафе «Чай и тренды»": "Inviting to hang out and sip boba tea at ThriftTea with",

    # EP13 Growing Together (Treehouse, Infants, Puzzles, Bracelets, Bike, Splash Pad, Power Walk)
    # Treehouse
    "Занимается романтическим Вуху в домике на дереве": "Having romantic treehouse WooHoo",
    "Совместно строит и сколачивает домик на дереве вместе с семьей": "Building and assembling the treehouse together with family",
    "Украшает домик на дереве флажками и гирляндами": "Decorating the treehouse with flags and fairy lights",
    "Выглядывает в подзорную трубу с наблюдательного поста домика на дереве": "Looking through the spyglass from the treehouse lookout",
    "С веселым гиканьем съезжает по горке из домика на дереве": "Joyfully sliding down the slide from the treehouse",
    "Играет в захватывающие приключения и прячется в домике на дереве": "Playing pretend adventures and hanging out in the treehouse",

    # Infant Milestones & Care
    "Выкладывает на животик младенца, тренируя мышцы спинки и шеи": "Placing infant on tummy to strengthen back and neck muscles",
    "Терпеливо учит ползать и координировать движения младенца": "Patiently teaching infant to crawl and coordinate movements",
    "Учит самостоятельно сидеть и держать равновесие младенца": "Teaching infant to sit up and balance independently",
    "Радуется первым шагам и попыткам стоять младенца!": "Celebrating first steps and standing attempts of infant!",
    "В шоке ликвидирует масштабную аварию с испачканным подгузником младенца!": "In shock cleaning up a catastrophic blowout diaper mishap!",
    "Меняет подгузник младенцу на пеленальном столике": "Changing infant's diaper on changing table",
    "Заботливо кормит младенца из бутылочки": "Lovingly bottle-feeding the infant",
    "Носит в удобном слинге-переноске младенца": "Carrying infant in a comfortable baby carrier sling",
    "Нежно убаюкивает и укладывает в кроватку младенца": "Gently rocking and putting infant to sleep in crib",
    "Осторожно купает в теплой мыльной воде младенца": "Gently bathing infant in warm soapy water",
    "Играет в «ку-ку» и смешит забавными звуками младенца": "Playing peek-a-boo and making funny sounds to entertain infant",
    "С нежностью заботится и проводит время с младенцем": "Lovingly caring for and spending time with infant",

    # Puzzles & Crafts
    "Втихаря прячет недостающий кусочек пазла, подшучивая над семьей!": "Secretly hiding the missing puzzle piece as a playful prank!",
    "Кропотливо подбирает фрагменты и собирает большой семейный пазл": "Meticulously assembling jigsaw pieces of a big family puzzle",
    "Торжественно дарит сплетенный браслет дружбы": "Grandly giving a hand-woven friendship bracelet",
    "Плетет яркий браслет дружбы из разноцветных нитей мулине": "Crafting a colorful friendship bracelet from embroidery floss",
    "Сладко спит в мягком спальном мешке на полу гостиной": "Sleeping cozily in a soft sleeping bag on the living room floor",

    # Bike, Splash Pad, Power Walk
    "Терпеливо учит ребенка держать равновесие на двухколесном велосипеде": "Patiently teaching child to balance on a two-wheeled bicycle",
    "С визгом бегает под освежающими струями фонтанчиков в детском водном парке": "Joyfully squealing and running under splash pad water fountains",
    "Бодро шагает по набережной Сан-Секвойи, занимаясь спортивной ходьбой": "Briskly power walking along the scenic San Sequoia boardwalk",

    # Social Dialogues EP13
    "С гордостью рассказывает о новых достижениях и вехах развития малыша для": "Proudly sharing infant milestones and achievements with",
    "С теплотой предается ностальгическим семейным воспоминаниям вместе с": "Warmly reminiscing about nostalgic family memories together with",
    "Торжественно повязывает сплетенный вручную браслет дружбы на запястье": "Grandly tying a hand-woven friendship bracelet onto the wrist of",
    "Делится мудрым родительским опытом и тонкостями воспитания детей с": "Sharing wise parenting experience and child-rearing tips with",
    "Искренне исповедуется в душевных терзаниях и кризисе среднего возраста перед": "Sincerely confessing emotional turmoil and midlife crisis to",
    "С радостью приглашает пожить в гостях с ночевкой на несколько дней": "Joyfully inviting over for a multi-day sleepover stay",
    "Со смехом и вздохом жалуется на бесконечную смену грязных подгузников для": "Laughingly complaining about endless messy diaper changes to",

    # EP14 Horse Ranch (Horses, Foals, Mini Pets, Haystack, Nectar, Ranch Life)
    # Haystack & Nectar
    "Занимается страстным деревенским Вуху в стоге сена": "Having passionate rustic haystack WooHoo",
    "Сладко дремлет прямо на копне свежего ароматного сена": "Napping cozily on a fragrant heap of fresh hay",
    "Весело кувыркается и дурачится в мягком стоге лугового сена": "Joyfully tumbling and playing in the soft haystack",
    "С упоением давит сочные фрукты босыми ногами в деревянном чане нектарницы!": "Delightfully stomping juicy fruits barefoot in the wooden nectar tub!",
    "Разливает свежевыжатый нектар по стеклянным бутылкам для дальнейшей выдержки": "Bottling freshly pressed nectar into glass bottles for aging",
    "Укладывает бутылки с нектаром на деревянный стеллаж для долгого созревания": "Stacking nectar bottles onto wooden rack for fine aging",
    "Медленно смакует бокал превосходно выдержанного нектара, наслаждаясь букетом вкуса": "Slowly savoring a glass of finely aged nectar, enjoying its bouquet",
    "Занимается производством изысканного домашнего нектара": "Crafting exquisite homemade nectar",

    # Mini Goats & Mini Sheep
    "Умело доит очаровательную карликовую козочку": "Skillfully milking the adorable mini goat",
    "Бережно состригает мягкую шерсть с карликовой овечки": "Carefully shearing soft fleece from mini sheep",
    "Заботливо кормит карликового питомца молоком из бутылочки": "Lovingly bottle-feeding mini pet with milk",
    "С умилением ласкает и обнимает карликовых козочек и овечек": "Fondly cuddling and petting mini goats and sheep",
    "Заботится и проводит время с мини-козочками и овечками": "Caring for and spending time with mini goats and sheep",

    # Ranch Life & Prairie Grass
    "Лихо отбивает каблуками ритм зажигательного ковбойского танца кантри": "Energetically heel-stomping to upbeat country line dancing",
    "Косит сочную дикую луговую траву косой, запасая свежее сено для ранчо": "Harvesting wild prairie grass with a scythe for fresh ranch hay",
    "Дает указания разнорабочему по уборке стойл и уходу за животными": "Giving directions to ranch hand regarding stall chores and animal care",
    "Перебирает струны гитары у костра, душевно напевая старинную ковбойскую балладу": "Strumming acoustic guitar by campfire, softly singing an old cowboy ballad",

    # Competitions & Foals
    "Участвует в престижном соревновании в конноспортивном центре": "Competing in prestigious tournament at Equestrian Center",
    "Бережно кормит жеребенка молоком из бутылочки": "Gently bottle-feeding little foal with milk",
    "Весело играет и резвится с очаровательным жеребенком": "Happily playing and romping with adorable little foal",
    "С нежностью обнимает маленького жеребенка": "Lovingly hugging little foal",
    "Заботливо ухаживает за новорожденным жеребенком": "Lovingly caring for newborn foal",

    # Training & Riding
    "Отрабатывает маневренность и скоростные развороты вокруг бочек на скакуне": "Practicing agility and tight turns around barrels on horseback",
    "Тренирует прыжки через барьеры и кавалетти на тренировочной площадке": "Training jumps over hurdles and cavaletti in the training ring",
    "Садится в седло скакуна": "Mounting the horse saddle",
    "Спешивается после конной прогулки": "Dismounting after a horse trail ride",
    "Едет верхом на лошади, наслаждаясь конной прогулкой": "Riding horse, enjoying a peaceful trail ride",

    # Horse Care & Grooming
    "Вычищает конский навоз вилами и стелет свежую солому в стойле": "Mucking out horse manure with pitchfork and laying fresh stall bedding",
    "Аккуратно расчищает копыта скакуна копытным крючком": "Carefully cleaning horse's hooves with hoof pick",
    "Заботливо вычесывает и чистит шерсть скакуна": "Lovingly brushing and grooming horse's coat",
    "Кормит скакуна свежим душистым сеном из кормушки": "Feeding horse fresh fragrant hay from feeder",
    "Наполняет поилку свежей водой для скакунов": "Refilling water trough with fresh water for horses",
    "С любовью гладит и обнимает своего верного скакуна": "Lovingly petting and hugging faithful horse",
    "Заботливо ухаживает за любимой лошадью": "Lovingly tending to beloved horse",

    # Social Dialogues EP14
    "С гордостью хвастается победами в конных дерби и навыками верховой езды перед": "Proudly bragging about equestrian derby wins and riding skills to",
    "Делится секретами выездки, конкура и тренировки скакунов с": "Sharing dressage, show jumping, and horse training secrets with",
    "Торжественно поднимает бокал выдержанного нектара и произносит душевный тост за": "Grandly raising a glass of aged nectar and proposing a heartfelt toast to",
    "С умилением восторгается очаровательными мини-козочками и овечками для": "Gushing fondly about adorable mini goats and sheep to",
    "Увлекательно рассказывает старую ковбойскую байку каньона Честнат-Ридж для": "Telling a thrilling old Chestnut Ridge cowboy tale to",
    "Ворчливо жалуется на тяжелую чистку стойла от конского навоза для": "Grumpily complaining about mucking out heavy horse manure to",
    "Со знанием дела обсуждает тонкости купажа и выдержки нектара с": "Expertly discussing nectar vintage, blends, and aging with",

    # EP15 For Rent (Mold, Snooping, Rentals, Pressure Cooker, Kettle, Hopscotch, Marbles, Spirit House, Night Market)
    # Mold Remediation
    "Ликвидирует взрыв спор смертоносной черной плесени!": "Cleaning up an explosion of lethal black mold spores!",
    "Обрабатывает очаги ядовитой плесени химическим спреем-фунгицидом": "Treating toxic mold outbreaks with chemical fungicide spray",
    "В защитной маске соскребает и оттирает опасную токсичную плесень со стен!": "Scrubbing dangerous toxic mold off walls while wearing a protective mask!",

    # Snooping, Break-Ins & Blackmail
    "Тайно взламывает дверь чужой квартиры с помощью отмычки!": "Secretly picking the lock of another apartment with a lockpick!",
    "Рыется в чужих вещах в поисках пикантных тайн и компромата": "Snooping through personal belongings searching for juicy secrets and blackmail",
    "Жадно подслушивает чужой разговор через стену": "Eagerly eavesdropping on someone's conversation through the wall",
    "Шантажирует сочной тайной ради личной выгоды": "Blackmailing with a juicy secret for personal gain",

    # Rentals & Property Management
    "Оформляет официальное выселение недобросовестного арендатора": "Filing formal eviction notice for a delinquent tenant",
    "Собирает арендную плату с жильцов многоквартирного дома": "Collecting rent payments from residential tenants",
    "Пытается утихомирить разгневанных жильцов во время бунта арендаторов": "Attempting to calm angry tenants during a tenant revolt strike",
    "Проводит инспекцию состояния арендованного жилья": "Conducting rental unit property inspection",
    "Срочно устраняет коммунальную аварию в арендованном жилье": "Urgently repairing a maintenance emergency in rental unit",
    "Управляет жилым комплексом с арендуемыми квартирами": "Managing residential rental property complex",

    # Kitchen Appliances (Cooker & Kettle)
    "Готовит ароматное традиционное блюдо в мультиварке-скороварке": "Cooking an aromatic traditional meal in the pressure cooker",
    "С наслаждением потягивает свежезаваренный ароматный чай из кружки": "Enjoying a mug of freshly brewed aromatic hot tea",
    "Заваривает согревающий свежий чай в электрическом чайнике": "Brewing comforting hot tea in the electric kettle",

    # Tomarang Games & Culture
    "Ловко прыгает по нарисованным на асфальте классикам": "Deftly hopping along chalk hopscotch court on sidewalk",
    "Метко целится и выбивает стеклянные шарики-марблс на площадке": "Aiming and flicking glass marbles out of the ring on playground",
    "Зажигает благовония и оставляет почтительное подношение в домике духов": "Burning incense and leaving a respectful offering at the Spirit House",
    "С благоговением молится и выражает уважение духам Томаранга": "Reverently praying and paying respects to Tomarang spirits",
    "Гуляет по оживленному ночному рынку Томаранга, разглядывая прилавки и уличную еду": "Strolling through lively Tomarang Night Market, browsing food stalls",

    # Social Dialogues EP15
    "Зловеще шантажирует выведанной компрометирующей тайной": "Sinisterly blackmailing with an uncovered secret",
    "В лицо обвиняет и уличает в скрытой постыдной тайне": "Directly confronting about a shameful hidden secret",
    "Искренне и со стыдом признается в сокровенной тайне перед": "Sincerely and shamefully confessing a secret to",
    "Пытается вручить взятку арендодателю за снижение арендной платы для": "Attempting to bribe landlord for reduced rent to",
    "В ярости угрожает немедленным выселением из арендованной квартиры для": "Furiously threatening immediate eviction from rental unit to",
    "Возмущенно жалуется на завышенную стоимость аренды и плесень в жилье для": "Indignantly complaining about overpriced rent and mold to",
    "Подбивает соседей объявить бойкот арендодателю и устроить бунт арендаторов вместе с": "Inciting neighbors to boycott landlord and stage tenant strike together with",

    # EP16 Lovestruck (Cupid's Corner, Blanket, Motel, Seduction, Eggplant, Therapy, Ciudad Enamorada)
    # Eggplant Costume
    "Занимается комичным Вуху в нелепом костюме баклажана": "Having funny WooHoo in a ridiculous eggplant costume",
    "Вальяжно расхаживает в забавном костюме гигантского баклажана": "Strutting around in a hilarious giant eggplant costume",

    # Romantic Blanket
    "Занимается романтическим Вуху на мягком пледе под открытым небом": "Having romantic WooHoo on a soft blanket under open sky",
    "Отдыхает на романтическом пледе, наслаждаясь теплым вечером": "Relaxing on a romantic blanket enjoying the warm evening",
    "Отдыхает на романтическом пледе на траве": "Relaxing on a romantic picnic blanket on the grass",

    # Hourly Motel
    "Занимается тайным страстным Вуху в уютном номере мотеля": "Having secret passionate motel room WooHoo",
    "Останавливается в мотеле на час для романтического свидания": "Staying at the hourly motel for a secret romantic date",

    # Seduction & Intimacy
    "Двигается в ритме соблазнительного чувственного танца": "Moving to the rhythm of a seductive sensual dance",
    "Танцует романтический медленный танец с глубоким прогибом": "Slow dancing romantically with a dramatic deep dip",
    "Ведет нежные интимные разговоры на подушках после близости": "Sharing tender post-intimacy pillow talk in bed",
    "Кормит партнера спелой клубникой в шоколаде": "Feeding partner sweet chocolate-dipped strawberries",

    # Cupid's Corner
    "Делает кокетливое селфи и обновляет анкету в «Уголке Купидона»": "Taking a flirty selfie and updating Cupid's Corner dating profile",
    "Отправляется на свидание вслепую через «Уголок Купидона»": "Going on a blind date set up via Cupid's Corner",
    "Листает анкеты потенциальных возлюбленных в приложении «Уголок Купидона»": "Browsing potential romantic matches on Cupid's Corner dating app",

    # Therapy & Literature
    "Консультируется с психотерапевтом по вопросам отношений и романтики": "Consulting with a relationship counselor about romance and intimacy",
    "Изучает руководство по романтическим отношениям и искусству обольщения": "Reading a romance guide on relationships and seduction",

    # Ciudad Enamorada
    "Любуется вечерней панорамой романтического города Сьюдад-Энаморада": "Admiring the evening panorama of romantic Ciudad Enamorada",

    # Social Dialogues EP16
    "Игриво интересуется романтическими предпочтениями и тем, что возбуждает и привлекает": "Playfully asking about romantic turn-ons, desires, and attraction with",
    "Откровенно обсуждает уровень романтического удовлетворения и страсти в отношениях с": "Openly discussing romantic satisfaction and relationship passion with",
    "Осторожно предлагает вместе посетить сеанс психотерапии для пар для": "Gently proposing attending couples relationship therapy together to",
    "Чувственно кормит сладкой клубникой в шоколаде с рук": "Sensually hand-feeding chocolate-dipped strawberries to",
    "Хвастается кучей лайков и успешных мэтчей в «Уголке Купидона» перед": "Bragging about likes and successful matches on Cupid's Corner to",
    "Нежно шепчет сокровенные признания во время интимных разговоров на подушках с": "Tenderly whispering intimate confessions during cozy pillow talk with",
    "С разочарованием жалуется на провальное свидание и неловкую химию для": "Disappointedly complaining about a disastrous date and bad chemistry to",

    # EP17 Life & Death
    "Собирает душу усопшего острой косой Жнеца Смерти": "Reaping the deceased soul with the Grim Reaper's sharp scythe",
    "Отрабатывает эффектные взмахи и мастерство владения косой Смерти": "Practicing dramatic swings and scythe mastery",
    "Бережно полирует лезвие своей могильной косы": "Carefully polishing the blade of the deathly scythe",
    "Калибрует и настраивает сферу душ в Департаменте Смерти": "Calibrating and tuning the Soul Orb at Netherworld Services",
    "Определяет причину смерти и исследует останки усопшего": "Determining cause of death and examining deceased remains",
    "Умоляет Жнеца Смерти о пощаде": "Pleading with the Grim Reaper for mercy",
    "Занимается потусторонним и пугающе страстным Вуху с самим Жнецом Смерти!": "Having otherworldly and hauntingly passionate romance with the Grim Reaper!",
    "Произносит трогательную надгробную речь на похоронах": "Delivering a touching eulogy at the funeral service",
    "Скорбит и оплакивает утрату близкого у надгробия": "Mourning and weeping over the loss of a loved one at the headstone",
    "Зажигает поминальную свечу в память об усопшем": "Lighting a memorial candle in remembrance of the deceased",
    "Подготавливает тело усопшего к церемонии прощания и укладывает в гроб": "Preparing the deceased's body for memorial ceremony and placing into casket",
    "Присутствует на церемонии похорон и поминальной службе": "Attending the funeral ceremony and memorial service",
    "Внимательно слушает официальное оглашение завещания": "Attentively listening to the official reading of the will",
    "Распределяет ценное имущество и сбережения в завещании": "Distributing valuable estate and savings in the drafted will",
    "Составляет официальное завещание, распределяя наследство и реликвии": "Drafting an official will, distributing inheritance and family heirlooms",
    "Занимается готическим Вуху прямо внутри гроба": "Having thrilling gothic romance right inside the coffin",
    "Спит в мягко обитом роскошном гробу": "Sleeping comfortably inside a luxurious cushioned coffin",
    "Отдыхает внутри старинного гроба": "Resting inside an ornate antique coffin",
    "Исследует темные глубины старинного склепа и катакомб": "Exploring the eerie dark depths of ancient crypt and catacombs",
    "Высекает трогательную эпитафию на надгробном камне": "Inscribing a touching epitaph onto the cemetery headstone",
    "Оставляет подношение у могилы усопшего": "Leaving a memorial offering and flowers at the grave",
    "Временно вселяется в чужое тело, подчиняя сима своей воле": "Temporarily possessing a living Sim's body, bending them to ghostly will",
    "Вселяется в предмет, заставляя его левитировать и дрожать от эктоплазмы": "Possessing an object, making it levitate and tremble with ectoplasm",
    "Устраивает шалости полтергейста, поднимая предметы в воздух и пугая окружающих": "Pulling poltergeist antics, floating objects in mid-air and spooking everyone",
    "Оставляет липкий след мерцающей эктоплазмы": "Leaving a slimy trail of glowing ectoplasm",
    "Издает леденящий душу потусторонний вой": "Letting out a bone-chilling otherworldly wail",
    "Развивает призрачное мастерство и связь с миром теней": "Cultivating ghost mastery and communing with the netherworld",
    "Торжественно вычеркивает выполненную мечту из предсмертного списка": "Triumphantly checking off a fulfilled goal from the bucket list",
    "Записывает свои заветные предсмертные желания в список целей души": "Writing cherished aspirations into the soul's bucket list",
    "Погружается в Зловещую топь для духовного перерождения и реинкарнации в новую жизнь!": "Submerging into the Baleful Bog for spiritual rebirth and reincarnation into a new life!",
    "Тянет персональную карту дня из мистической колоды Таро": "Drawing a personal card of the day from the mystic Tarot deck",
    "Делает таинственный расклад карт Таро, читая знаки судьбы": "Doing a mystic Tarot spread, deciphering omens of fate",
    "Проводит таинственный спиритический сеанс, призывая духов предков": "Conducting a mystical seance, summoning ancestral spirits",
    "Прогуливается по туманным улочкам таинственного городка Вранбург": "Strolling through the misty streets of mysterious town Ravenwood",
    # Social dialogues exact
    "Философски обсуждает путь души, жизнь после смерти и реинкарнацию с": "Philosophically discussing the soul's journey, afterlife, and reincarnation with",
    "Делится своими заветными предсмертными желаниями из списка души с": "Sharing cherished bucket list aspirations and dreams with",
    "Искренне и чутко соболезнует и утешает в глубокой скорби": "Sincerely offering heartfelt condolences and comforting",
    "Хвастается пунктами своего составленного завещания перед": "Boasting about stipulations in drafted will to",
    "Беседует о тайнах загробного мира и работе Жнеца Смерти с": "Chatting about underworld secrets and the Grim Reaper's work with",
    "В отчаянии молит пощадить жизнь и не забирать душу перед": "Desperately pleading to spare the life and not take the soul before",
    "Делает таинственный расклад карт Таро, предсказывая грядущую судьбу для": "Performing a mysterious Tarot card reading, foretelling future destiny for",

    # EP18 Businesses & Hobbies
    "Формует глиняное изделие на вращающемся гончарном круге": "Shaping clay artwork on the spinning pottery wheel",
    "Наносит декоративную цветную глазурь на керамическое изделие": "Applying decorative colored glaze onto ceramic pottery",
    "Обжигает глиняные изделия в раскаленной гончарной печи": "Firing clay ceramics inside the high-temperature pottery kiln",
    "Любуется готовой авторской керамикой ручной работы": "Admiring finished handmade ceramic pottery",
    "Набивает художественную татуировку клиенту на тату-кушетке": "Tattooing custom body art on client at the tattoo chair",
    "Терпит легкую боль, пока мастер наносит татуировку на кожу": "Enduring mild sting while tattoo artist applies ink to skin",
    "Разрабатывает уникальный авторский эскиз для будущей татуировки": "Designing a unique custom sketch for upcoming tattoo",
    "Тщательно стерилизует тату-машинку и дезинфицирует кушетку": "Sanitizing tattoo machine and disinfecting tattoo chair",
    "Занимается созданием татуировки на тату-кушетке": "Creating custom tattoo art at the tattoo chair",
    "Настраивает тарифы и продает входные билеты через автомат": "Setting admission rates and vending tickets at ticket machine",
    "Управляет своим малым бизнесом, проверяя доходы и ассортимент товаров": "Managing small business, tracking profits and inventory",
    "Приветливо обслуживает покупателей в своей мастерской": "Warmly assisting shoppers and clients in the workshop",
    "Управляет наемным персоналом и распределяет обязанности в заведении": "Managing hired staff and delegating duties in business",
    "Увлеченно читает лекцию и рисует схемы на маркерной доске": "Passionately lecturing and sketching diagrams on whiteboard",
    "С интересом слушает обучающую лекцию на мастер-классе": "Attending an educational lecture and workshop with keen interest",
    "Готовит пушистую сладкую сахарную вату на кондитерском аппарате": "Spinning fluffy sweet cotton candy on confectionery machine",
    "Варит ароматные желейные конфеты из спелых свежих плодов": "Crafting artisan fruit jelly gummies from fresh produce",
    "Собирает и кастомизирует стильный городской велосипед из редких деталей": "Assembling and customizing stylish city bike from rare parts",
    "С удовольствием катается на велосипеде вдоль каналов и набережных": "Leisurely cycling along picturesque canals and promenades",
    "Исследует уютные улочки и творческие мастерские Нордхавена": "Exploring quaint streets and artisan workshops of Nordhaven",
    # Social Dialogues EP18 exact
    "С увлечением обсуждает лепку из глины, глазурь и гончарное ремесло с": "Enthusiastically discussing clay modeling, glazes, and pottery with",
    "С гордостью демонстрирует свежую татуировку и обсуждает эскизы перед": "Proudly showing off fresh tattoo and discussing sketches with",
    "С энтузиазмом презентует перспективную идею малого бизнеса для": "Enthusiastically pitching a promising small business idea to",
    "Ведет деловые переговоры о совместном коммерческом проекте и партнерстве с": "Conducting business negotiations on a joint commercial venture with",
    "С досадой жалуется на капризных и придирчивых клиентов малого бизнеса для": "Frustratedly complaining about finicky small business customers to",
    "Рекомендует опытного наставника и курсы повышения мастерства для": "Recommending an experienced mentor and skill masterclasses to",
    "Искренне восхищается безупречным ручным мастерством и талантом": "Sincerely admiring exquisite handmade craftsmanship and talent of",

    # EP19 Enchanted Nature / Nature's Magic
    "Парит в воздухе на мерцающих полупрозрачных крыльях феи": "Hovering in the air on shimmering translucent fairy wings",
    "Собирает переливающуюся пыльцу с волшебных крыльев для сотворения чар": "Harvesting iridescent fairy dust from wings for spellcasting",
    "Обращается в мерцающий лесной огонек, легко скользя среди крон деревьев": "Transforming into a shimmering woodland wisp, gliding through the canopy",
    "Настраивает форму и магическое свечение своих сказочных крыльев": "Customizing shape and mystical glow of fairy wings",
    "Плетет невинные озорные чары и готовит волшебные шалости": "Weaving innocent playful charms and plotting fairy mischief",
    "Сотворяет заклинание цветения, возвращая к жизни увядшие побеги": "Casting a blooming spell, restoring wilted greenery to life",
    "Взывает к силам стихий, призывая благодатный живительный дождь над садом": "Calling upon elements to summon life-giving rain over the garden",
    "Очищает почву от скверны и вредителей волной зеленой природной энергии": "Cleansing soil of corruption and pests with a wave of nature energy",
    "Управляет гибкими лесными лозами и древесными побегами": "Manipulating flexible forest vines and living shoots",
    "Прислушивается к сокровенному шепоту древнего Древа Жизни, внимая тайнам природы": "Listening to the sacred whispers of the ancient Tree of Life",
    "Дистиллирует чистейшие растительные эссенции за аптекарским столом": "Distilling pure botanical essences at the apothecary table",
    "Варит целебный травяной эликсир из свежесобранных лесных сборов": "Brewing a medicinal herbal elixir from freshly gathered forest herbs",
    "Зачаровывает редкие семена и грибы, наполняя их силой природной магии": "Enchanting rare seeds and fungi with the essence of nature magic",
    "Отыскивает редкие светящиеся травы и волшебные коренья в лесной чаще": "Searching for rare bioluminescent herbs and mystical roots in the dense woods",
    "Танцует и медитирует внутри загадочного круга светящихся грибов": "Dancing and meditating inside the mystical ring of glowing mushrooms",
    "Возлагает дары из лесных ягод и цветов на алтарь древних духов природы": "Placing offerings of berries and flowers onto the shrine of ancient nature spirits",
    "Впитывает благословение Матери-Природы, ощущая прилив гармонии и жизненных сил": "Embracing the blessing of Mother Nature, feeling harmony and surge of vitality",
    "Шагает сквозь зачарованное дупло древнего древа, перемещаясь в волшебную рощу": "Stepping through the enchanted hollow of an ancient tree into a fairy grove",
    "Пересвистывается и напевает трели на языке лесных птиц, наладив чуткий контакт": "Whistling and trilling in bird language, bonding with woodland songbirds",
    "Заботливо угощает орешками и гладит пушистых лесных обитателей": "Tending to and feeding crunchy nuts to gentle woodland critters",
    "С благодарностью принимает редкий лесной дар от дружелюбных зверят": "Gratefully accepting a rare forest gift from friendly woodland critters",
    # Social Dialogues EP19 exact
    "С упоением рассказывает предания о лесных феях и скрытых тропах для": "Enthusiastically sharing folklore about woodland fairies and hidden trails with",
    "Увлеченно рассуждает о равновесии стихий и древней магии природы с": "Passionately debating balance of elements and ancient nature magic with",
    "Делится тайными рецептами травяных отваров и эликсиров природы с": "Sharing secret recipes of herbal brews and nature elixirs with",
    "Восхищается изящной формой и волшебным сиянием крыльев перед": "Admiring delicate shape and magical luminescence of fairy wings before",
    "Предостерегает о коварных проделках духов леса и ловушках кругов фей": "Warning about tricky woodland spirit pranks and perilous fairy rings to",
    "Горячо призывает беречь заповедную природу и вековые леса в разговоре с": "Passionately advocating conservation of pristine nature and ancient forests with",

    # GP06 Jungle Adventure (Selvadorada)
    "Предается романтической страсти под струями тропического водопада": "Indulging in romantic passion under tropical waterfall cascades",
    "С упоением целуется под шумящим тропическим водопадом": "Kissing passionately under rushing tropical waterfall",
    "Прорубает дорогу сквозь непроходимые заросли джунглей с помощью мачете": "Clearing a path through impenetrable jungle thickets with a machete",
    "Отбивается от хищных плотоядных лиан, используя специальную приманку": "Fending off carnivorous vines using specialized bait",
    "Отпугивает рой свирепых плазматических летучих мышей защитным спреем": "Scaring off swarm of vicious plasma bats with protective spray",
    "Распыляет защитный спрей от ядовитых пауков джунглей": "Spraying protective repellent against poisonous jungle spiders",
    "Спасается от разрядов электрических светлячков с помощью порошка Гузмании": "Shielding from electric fireflies discharges with Guzmania powder",
    "Отбивается от роя хищных насекомых и распыляет защитный спрей в джунглях": "Fending off hostile jungle insects and spraying protective repellent",
    "Освежается и смывает дорожную пыль под бурными струями водопада": "Refreshing and washing off travel dust under rushing waterfall cascades",
    "Мерно покачивается и сладко дремлет в подвесном походном гамаке среди деревьев": "Gently swaying and peacefully napping in hanging travel hammock amongst trees",
    "Отдыхает в полевом экспедиционном лагере посреди диких джунглей": "Resting at expedition campsite in the heart of dense wilderness",
    "Залпом выпивает спасительное сельвадорадское противоядие от смертоносного яда": "Downing saving Selvadoradian antidote against deadly poison",
    "Срочно ищет и выменивает спасительный антидот от древнего яда": "Urgently seeking and trading for saving antidote against ancient poison",
    "Внимательно изучает древние механизмы и пытается обезвредить ловушку храма": "Carefully inspecting ancient mechanisms and disarming temple trap",
    "Разгадывает храмовую загадку и распахивает тайные каменные врата святилища": "Solving temple puzzle and opening massive ancient stone gate",
    "С благоговением отпирает древний сундук с бесценными сокровищами цивилизации Омиска": "Reverently unlocking ancient chest filled with treasures of Omiscan civilization",
    "Совершает искреннее пожертвование статуе Мадре Косеки, моля о благословении": "Making a sincere offering to Madre Cosecha statue, praying for blessing",
    "Ощущает воздействие мистического храмового проклятия, окутавшего тело": "Feeling the lingering effect of mystical temple curse enveloping the body",
    "Размечает колышками и организует новый перспективный участок для совместных раскопок": "Setting boundary stakes and establishing a promising new group excavation site",
    "Изучает и устанавливает подлинность редкого древнего артефакта за археологическим столом": "Examining and authenticating a rare ancient artifact at archaeology table",
    "Бережно проводит археологические раскопки, просеивая древний грунт кисточкой": "Painstakingly conducting archaeological excavation, brushing ancient soil",
    "Кропотливо реставрирует и склеивает фрагменты древней омисканской реликвии": "Painstakingly restoring and piecing together fragments of ancient Omiscan relic",
    "Тщательно растирает древнюю омисканскую костяную пыль для алхимии и реликвий": "Carefully grinding ancient Omiscan bone dust for alchemy and relics",
    "Соединяет основу реликвии с очищенным кристаллом, активируя древнюю магию": "Combining relic base with refined crystal, awakening ancient magic",
    "Призывает гремящего костями скелета-помощника для ведения хозяйства": "Summoning clattering skeletal assistant to help with household chores",
    "Щеголяет в обличье живого омисканского скелета, задорно постукивая ребрами": "Strutting around in the form of a living Omiscan skeleton, rattling ribs",
    "Задорно гремит костями и пугает прохожих своим скелетным видом": "Playfully rattling bones and spooking bystanders with skeletal appearance",
    "Общается и весело шутит с ожившим храмовым скелетом": "Chatting and playfully joking with a living temple skeleton",
    "Страстно отплясывает зажигательный сельвадорадский танец Румбасим": "Passionately dancing the fiery Selvadoradian Rumbasim dance",
    "Виртуозно наигрывает колоритные латиноамериканские мотивы на гитаре": "Masterfully strumming vibrant Latin American folk tunes on guitar",
    "Обменивается колоритным сельвадорадским приветствием": "Exchanging traditional colorful Selvadoradian greeting",
    "Придирчиво выбирает мачете и походное снаряжение у местных торговцев": "Haggling and purchasing expedition gear from local open-air vendors",
    "С аппетитом пробует пикантные традиционные блюда сельвадорадской кухни": "Savory tasting spicy traditional dishes of Selvadoradian cuisine",
    # Social Dialogues Jungle Adventure exact
    "С горящими глазами рассказывает об опасностях и скрытых тропах джунглей для": "Eagerly describing hazards and hidden trails of the jungle to",
    "Повествует о величии, храмах и мистических тайнах народа Омиска для": "Recounting legends of greatness and mystical secrets of Omiscan civilization to",
    "С азартом делится смелыми гипотезами об археологических раскопках с": "Enthusiastically sharing bold theories on archaeological discoveries with",
    "Предостерегает о коварных ловушках и ядовитых дротиках древнего храма": "Warning about perilous traps and venomous darts of ancient temple to",
    "Знакомит с колоритными обычаями и традициями Сельвадорады в беседе с": "Sharing vibrant customs and folklore of Selvadorada in conversation with",
    "С гордостью хвастается найденным в руинах бесценным золотым артефактом перед": "Proudly boasting about priceless golden artifact recovered from ruins before",

    # EP20 Through the Ages
    "Калибрует темпоральный континуум и настраивает хроно-координаты машины времени": "Calibrating temporal continuum and dialing chrono-coordinates on time machine",
    "Шагает в сияющий темпоральный портал, отправляясь в путешествие сквозь века": "Stepping into glowing temporal portal, traveling through the ages",
    "Устраняет опасный временной парадокс, восстанавливая естественный ход истории": "Resolving perilous temporal paradox, restoring natural flow of history",
    "Возвращается из путешествия во времени с подлинными артефактами ушедших веков": "Returning from time journey with genuine artifacts of bygone eras",
    "Отрабатывает искусные фехтовальные приемы с историческим мечом": "Practicing skillful fencing techniques with historical sword",
    "Принимает посвящение в рыцари, преклонив колено": "Receiving knighthood investiture upon bended knee",
    "Метко пускает оперенную стрелу в мишень из старинного изогнутого лука": "Accurately loosing feathered arrow at target from vintage curved bow",
    "Примеряет и начищает до блеска массивные стальные рыцарские латы": "Fitting and polishing heavy steel knightly plate armor to a shine",
    "Пишет подробную историческую летопись династии гусиным пером за старинным бюро": "Writing detailed dynasty chronicles with quill feather pen at antique bureau",
    "Кропотливо изучает родословное древо предков, раскрывая семейные тайны веков": "Painstakingly studying ancestral family tree, uncovering secrets of centuries",
    "Бережно реставрирует старинный антиквариат и шестеренки винтажной астролябии": "Delicately restoring antique relics and clockwork cogs of vintage astrolabe",
    "Просматривает голографические хроники грядущих столетий в квантовом архиве": "Reviewing holographic chronicles of upcoming centuries in quantum archives",
    "Исполняет величавые па старинного придворного менуэта": "Performing majestic steps of vintage courtly minuet",
    "Отрабатывает безупречный придворный реверанс по всем правилам этикета": "Practicing flawless courtly curtsy according to all rules of etiquette",
    "Неспешно вкушает ароматный чай из старинного фарфорового сервиза": "Leisurely savoring aromatic tea poured from vintage porcelain teapot",
    "Настраивает пространственные сенсоры на голографическом дисплее хроноскопа": "Calibrating spatial sensors on holographic display of chronoscope",
    "Заряжает концентрированной энергией хроно-кристаллы темпорального двигателя": "Charging chronocrystals of temporal engine with concentrated energy",
    "Синтезирует старинное средневековое угощение в молекулярном пищевом репликаторе": "Synthesizing vintage medieval delicacy in molecular food replicator",
    # Social Dialogues Through the Ages exact
    "С восторгом рассказывает об удивительных путешествиях сквозь века и эпохи для": "Enthusiastically describing thrilling journeys through the ages and eras to",
    "С жаром спорит о парадоксах времени и альтернативных ветвях истории с": "Passionately debating time paradoxes and alternate historical timelines with",
    "Искренне восхищается подлинным старинным антиквариатом и нарядами былых эпох перед": "Sincerely admiring authentic vintage antiquities and historic attire before",
    "С почтением расспрашивает о тайнах предков и древнем происхождении рода у": "Respectfully inquiring about ancestral secrets and ancient noble lineage of",
    "Предостерегает об угрозе разрушения пространственно-временного континуума для": "Warning about the peril of destabilizing the space-time continuum to",
    "С изяществом обучает манерам и благородному куртуазному этикету": "Gracefully teaching noble courtly manners and aristocratic etiquette to",

    # GP01 Outdoor Retreat
    "Жарит аппетитный зефир на палочке над искрами костра": "Roasting sweet marshmallows on a stick over campfire sparks",
    "Жарит сосиски на палочке над походным костром": "Roasting hot dogs on a stick over the campfire",
    "Жарит свежепойманную рыбу на костре": "Roasting freshly caught fish over open campfire flames",
    "С упоением рассказывает леденящие кровь страшилки у костра": "Thrillingly telling spine-chilling ghost stories around the campfire",
    "Душевно напевает любимые походные песни у костра": "Heartily humming beloved campfire songs by the fire",
    "Уютно греется у пылающего походного костра": "Cozying up and warming hands by blazing campfire",
    "Играет в метание подков, стараясь попасть в колышек": "Playing horseshoes, aiming for a ringer on the stake",
    "Лежит на траве и мечтательно разглядывает облака в небе": "Cloudgazing daydreaming while relaxing on the grass",
    "Уютно отдыхает в просторной туристической палатке": "Resting cozily inside spacious camping tent",
    "Осторожно ловит редких насекомых и светлячков в банку": "Carefully catching rare insects and fireflies in a glass jar",
    "Рассматривает пойманных жуков и светлячков в походном садке": "Observing collected beetles and fireflies in a camp terrarium",
    "Растирает дикие травы, распознавая их целебные свойства": "Rubbing wild leaves and identifying herbal properties",
    "Варит успокаивающий травяной отвар от укусов насекомых": "Brewing soothing herbal remedy against insect bites",
    "Наряжается в костюм дикого медведя и рычит из кустов": "Dressing up in wild bear costume and growling from bushes",
    "Беседует по душам с мудрым лесным отшельником в глуши": "Having a deep heart-to-heart with the wise forest hermit",
    # Social Dialogues Outdoor Retreat exact
    "С упоением рассказывает захватывающие походные байки для": "Enthusiastically sharing thrilling camping lore and outdoor tales with",
    "Обсуждает секреты сбора трав и рецепты целебных мазей с": "Discussing herb foraging secrets and healing balm recipes with",
    "Восхищается первозданной природой и соснами Гранит Фоллз перед": "Admiring pristine nature and towering pines of Granite Falls before",
    "Дает полезные советы по обустройству палаточного лагеря для": "Giving practical tips on setting up campsite and surviving wilderness to",
    "Задорно шутит о встрече с медведем в диком лесу перед": "Playfully joking about running into wild bears in deep woods before",
    "С восторгом делится наблюдениями за редкими лесными жуками с": "Eagerly discussing sightings of rare woodland insects and beetles with",

    # GP02 Spa Day
    "Предается страсти в распаренной горячей сауне": "Enjoying passionate intimacy in the steamy hot sauna",
    "Плещет воду на раскаленные камни в сауне, окутываясь клубами густого пара": "Splashing water onto hot sauna stones, filling the room with billowing steam",
    "Парится в горячей кедровой сауне, глубоко прогревая тело": "Relaxing in hot cedar sauna, warming up in deep steam",
    "Делает классический расслабляющий шведский массаж на массажном столе": "Giving classic relaxing Swedish massage on massage table",
    "Расслабляется во время классического шведского массажа": "Relaxing during classic Swedish massage",
    "Массирует глубокие слои мышц, снимая мышечные зажимы": "Massaging deep muscle tissue, releasing muscle tension",
    "Ощущает облегчение от глубокого массажа зажатых мышц": "Feeling great relief from deep tissue massage",
    "Расккладывает горячие базальтовые камни вдоль позвоночника": "Placing hot basalt stones along the spine",
    "Раскладывает горячие базальтовые камни вдоль позвоночника": "Placing hot basalt stones along the spine",
    "Ощущает приятное тепло массажа горячими базальтовыми камнями": "Feeling soothing warmth of hot basalt stone massage",
    "Делает ароматерапевтический массаж с эфирными маслами": "Giving aromatherapy massage with essential oils",
    "Наслаждается ароматерапевтическим массажем с целебными маслами": "Enjoying aromatherapy massage with healing oils",
    "Проводит спортивный массаж для восстановления тонуса": "Performing sports massage for muscular recovery",
    "Восстанавливает мышцы во время спортивного массажа": "Restoring muscle tone during sports massage session",
    "Делает гармонизирующий массаж для повышения фертильности": "Giving harmonizing fertility massage",
    "Принимает гармонизирующий массаж для зачатия": "Receiving harmonizing massage for fertility",
    "Массирует уставшие стопы клиента в спа-кресле": "Massaging tired client feet in the spa chair",
    "Блаженно расслабляется в кресле во время массажа стоп": "Blissfully relaxing in chair during foot massage",
    "Делает деликатный массаж кистей рук в массажном кресле": "Giving delicate hand massage in massage chair",
    "Ощущает легкость во время массажа кистей рук": "Feeling hand tension melt away during hand massage",
    "Проводит профессиональный сеанс массажа на столе": "Conducting professional massage session on table",
    "Безмятежно отдыхает на массажном столе во время сеанса": "Serenely relaxing on massage table during session",
    "Проводит вдохновляющее групповое занятие по йоге на коврике инструктора": "Leading inspiring group yoga class on instructor mat",
    "Посещает занятие йогой в группе единомышленников": "Attending group yoga class with fellow practitioners",
    "Выполняет асану «собака мордой вниз», вытягивая позвоночник": "Practicing downward-facing dog pose, lengthening spine",
    "Балансирует в позе дерева на коврике для йоги": "Balancing steadily in tree pose on yoga mat",
    "Выполняет гармоничный комплекс «Приветствие солнца» на рассвете": "Performing harmonious Sun Salutation yoga sequence at dawn",
    "Стоит в уверенной позе воина, укрепляя дух и тело": "Holding confident warrior pose, strengthening body and mind",
    "Выгибается в позе моста, раскрывая грудную клетку": "Arching into bridge pose, opening chest",
    "Тянется в позе треугольника, балансируя на коврике": "Stretching into triangle pose, balancing on mat",
    "Занимается специальной практикой йоги для концентрации ума и прилива энергии": "Practicing specialized yoga flow for mental focus and energy boost",
    "Занимается йогой на коврике, растягивая мышцы и обретая гибкость": "Practicing yoga on the mat, stretching muscles and gaining flexibility",
    "Мгновенно телепортируется силой глубокой медитации и дзена": "Instantly teleporting through focused meditative power and zen",
    "Погружается в глубокий транс и безмятежно левитирует в воздухе": "Drifting into deep meditative trance and levitating serenely in midair",
    "Медитирует на табурете для медитации, очищая разум от лишних мыслей": "Meditating on meditation stool, clearing mind of thoughts",
    "Медитирует, очищая разум от лишних мыслей и обретая внутренний покой": "Meditating, clearing mind of thoughts and finding inner peace",
    "Наносит освежающую косметическую маску на лицо для ухода за кожей": "Applying refreshing cosmetic face mask for skin care",
    "Ходит с питательной косметической маской на лице, ухаживая за кожей": "Wearing nourishing cosmetic face mask, caring for skin",
    "Аккуратно наносит модный лак и рисует дизайн на ногтях": "Neatly applying trendy nail polish and painting nail art",
    "Сидит в спа-кресле, получая красивый и аккуратный маникюр": "Sitting in spa chair, receiving beautiful neat manicure",
    "Делает профессиональный спа-педикюр в кресле": "Giving professional spa pedicure in the chair",
    "Принимает освежающую процедуру спа-педикюра": "Receiving refreshing spa pedicure treatment",
    "Погружается в теплую целебную грязевую ванну, снимая накопившийся стресс": "Soaking in warm therapeutic mud bath, melting away stress",
    "Принимает роскошную расслабляющую ванну с ароматными маслами и солями": "Indulging in luxurious relaxing bath with aromatic oils and salts",
    "Пьет освежающую огуречную воду со льдом из спа-подноса": "Sipping refreshing ice-cold cucumber infused water from spa tray",
    "Практикует техники здорового образа жизни, стремясь к внутреннему покою": "Practicing wellness techniques, seeking inner balance and peace",
    # Social Dialogues Spa Day exact
    "Рассуждает о балансе чакр, духовном равновесии и дзен с": "Discussing chakra balance, spiritual harmony and zen with",
    "С воодушевлением советует свои любимые спа-процедуры и массаж для": "Enthusiastically recommending favorite spa treatments and massages to",
    "С гордостью демонстрирует свежий безупречный маникюр перед": "Proudly showing off fresh flawless manicure and nail design before",
    "Делится полезными советами по медитации и снятию стресса с": "Sharing helpful meditation and stress-relief tips with",
    "Увлеченно обсуждает пользу асан йоги и дыхательных практик с": "Eagerly discussing the health benefits of yoga poses and breathwork with",

    # GP03 Dine Out
    "Неловко спотыкается и с оглушительным грохотом роняет поднос с посудой": "Clumsily tripping and dropping the dish tray with a loud crash",
    "Встречает гостей у входа и распределяет столики в зале": "Greeting arriving guests and seating diners in dining room",
    "Несет поднос с аппетитными горячими блюдами к столику": "Carrying tray of mouthwatering hot dishes to the table",
    "Принимает подробный заказ блюд и напитков у гостей": "Taking detailed food and drink orders from dining guests",
    "Быстро и аккуратно убирает использованную посуду со столика": "Promptly bussing and clearing used dishes from the table",
    "Виртуозно готовит изысканное ресторанное блюдо на профессиональной плите": "Masterfully cooking gourmet restaurant dish at chef station",
    "Тщательно декорирует и доводит до совершенства подачу блюда высокой кухни": "Meticulously garnishing and plating haute cuisine dish to perfection",
    "Внимательно дегустирует блюдо и строчит заметки для ресторанного гида": "Critically tasting the dish and taking notes for restaurant guide",
    "Угощает гостей комплиментом от шеф-повара за счет заведения": "Treating diners to complimentary chef special on the house",
    "Обходит обеденный зал, справляясь о комфорте гостей ресторана": "Checking on dining room tables to ensure guest satisfaction",
    "Выражает благодарность персоналу за отличную смену в ресторане": "Expressing gratitude to staff for excellent restaurant shift",
    "Отчитывает персонал за недочеты и медлительность на смене": "Reprimanding staff for service flaws and slowness on shift",
    "Ожидает у стойки администратора приглашения за столик": "Waiting at the host station to be seated",
    "Терпеливо ожидает, пока администратор ресторана подготовит столик": "Patiently waiting while restaurant host prepares table",
    "Заказывает разнообразные блюда и напитки на всю компанию за столом": "Ordering varied dishes and drinks for the entire party",
    "Изучает меню и делает заказ официанту ресторана": "Reviewing the menu and placing order with the waiter",
    "Ожидает подачу свежеприготовленных ресторанных блюд": "Waiting for freshly prepared restaurant dishes to be served",
    "Торжественно произносит красивый тост за столом ресторана": "Raising glass and delivering elegant toast at dining table",
    "Делится кусочком вкусного блюда через столик": "Sharing tasty bite of food across the dining table",
    "Фотографирует подачу экспериментального блюда для симстаграма": "Taking photo of experimental dish presentation for Simstagram",
    "С восторгом дегустирует шедевр молекулярной экспериментальной кухни": "Enthusiastically savoring masterpiece of molecular experimental gastronomy",
    "Выражает искренний восторг качеством блюд шеф-повару": "Praising the chef for high quality and culinary excellence",
    "Жалуется на качество или температуру поданного блюда": "Complaining about quality or temperature of served dish",
    "Возмущается слишком долгой подачей блюд в ресторане": "Frustrated by excessively slow food service at restaurant",
    "Оплачивает счет за ужин и оставляет хорошие чаевые": "Paying dinner bill and leaving good tip for waiter",
    # Social Dialogues Dine Out exact
    "С упоением обсуждает тренды высокой кухни и гастрономические изыски с": "Enthusiastically discussing haute cuisine trends and gourmet dining with",
    "Увлеченно делится впечатлениями от экспериментальных блюд и молекулярной кухни с": "Eagerly sharing impressions of experimental molecular gastronomy with",
    "Негодует по поводу медлительного официанта и плохого ресторанного сервиса перед": "Venting about slow restaurant service and inattentive waiters before",
    "С воодушевлением советует свои любимые рестораны и уютные кафе для": "Enthusiastically recommending favorite fine dining restaurants to",
    "С гордостью хвастается пятизвездочным рейтингом своего ресторана перед": "Proudly boasting about 5-star restaurant rating and culinary prestige before",

    # GP04 Vampires
    "Мучительно шипит и сгорает под смертоносными лучами полуденного солнца": "Painfully sizzling and burning under the deadly rays of noon sun",
    "Использует древнее лекарство для исцеления от вампиризма": "Using ancient cure to free from the vampiric curse",
    "Готовит редкое абсолютное лекарство от вампиризма за барной стойкой": "Mixing the rare Ultimate Vampire Cure at the bar",
    "Плетет защитную гирлянду из чеснока для защиты дома от кровопийц": "Braiding protective garlic garland to shield home from bloodsuckers",
    "Предается страсти в старинном закрытом гробу": "Indulging in dark passion inside an antique closed coffin",
    "Совершает таинство обращения смертного в вампира": "Performing dark sacrament of turning a mortal into a vampire",
    "Умоляет древнего вампира об обращении в дитя ночи": "Pleading with ancient vampire for the dark gift of the night",
    "Утоляет мучительную жажду кровью беззащитно спящего сима": "Quenching agonizing thirst with blood of defenceless sleeping sim",
    "Жадно испивает теплую кровь жертвы, утоляя дикий голод": "Ravishingly drinking victim's warm blood, feeding ferocious hunger",
    "Аккуратно пьет теплую кровь с согласия донора": "Gently drinking warm blood with consent of donor",
    "Пьет донорскую кровь из медицинского пакета, спасаясь от жажды": "Drinking donor blood from a medical pack to stave off thirst",
    "Ест спелый кровавый плод, насыщаясь растительной кровью": "Eating ripe plasma fruit, nourishing on plant blood",
    "Потягивает темный густой коктейль с кровью из хрустального бокала": "Sipping dark rich blood cocktail from crystal glass",
    "Оборачивается летучей мышью и бесшумно рассекает ночной воздух": "Transforming into a bat and swooping silently through night sky",
    "Растворяется в клубах черного тумана и мгновенно переносится в пространстве": "Dissolving into dark mist and teleporting through space",
    "Стремительно несется вперед на сверхъестественной вампирической скорости": "Dashing forward at supernatural vampiric super-speed",
    "Погружает смертного в подчиняющий гипнотический транс": "Plunging mortal into commanding hypnotic trance",
    "Подчиняет разум смертного своей непреклонной воле": "Bending mortal mind to their unbreakable vampiric will",
    "Манипулирует аурой и внушает сильные темные эмоции": "Manipulating aura and inducing strong dark emotions",
    "Тренирует вампирические рефлексы в стремительном поединке": "Training vampiric reflexes in lightning-fast supernatural sparring",
    "Постигает основы высшего вампирического мастерства": "Learning fundamentals of master vampiric lore and dark powers",
    "Парит в воздухе в темной медитации, черпая энергию из глубин ночи": "Levitating in dark meditation, drawing power from the night",
    "Исполняет зловещую и величественную готическую сонату на духовом органе": "Playing a haunting gothic organ sonata on the pipe organ",
    "Мирно покоится в мягкой обивке богато украшенного гроба": "Resting peacefully in luxurious velvet lining of ornate coffin",
    # Social Dialogues Vampires exact
    "С таинственным видом обсуждает древние вампирические тайны Форготн Холлоу с": "Mysteriously discussing ancient vampiric secrets of Forgotten Hollow with",
    "Шепотом рассказывает о даре вечной жизни и тонкостях обращения с": "Whispering about the gift of eternity and intricacies of vampire turning with",
    "Раздраженно жалуется на омерзительный запах чеснока и палящее солнце перед": "Irritatedly complaining about repulsive stench of garlic and scorching sunlight before",
    "Философски спорит об этичности испития свежей крови против пакетов с кровью с": "Philosophically debating ethics of fresh blood vs blood packs with",
    "С высокомерием кичится своим могущественным титулом великого магистра перед": "Arrogantly flaunting powerful Grand Master vampire title before",

    # GP05 Parenthood exact
    "Отбывает наказание в тайм-ауте, размышляя о плохом поведении": "Serving time out punishment, reflecting on poor behaviour",
    "Находится под домашним арестом и тоскует взаперти": "Being grounded under house arrest and languishing inside",
    "Получает долгожданное родительское прощение": "Receiving long-awaited parental forgiveness",
    "Лишен любимых привилегий и гаджетов за проступок": "Revoked of favorite privileges and gadgets for misconduct",
    "Выслушивает гневные крики и упреки родителей": "Listening to parents' angry yelling and reproaches",
    "Внимательно слушает нравоучения старших о правилах поведения": "Attentively listening to elders' lectures on rules and behaviour",
    "Получает заслуженную родительскую похвалу": "Receiving well-deserved parental praise",
    "Наслаждается теплом и поддержкой родительских объятий": "Enjoying the warmth and comfort of parental embrace",
    "Учится справляться с эмоциями под руководством родителя": "Learning to manage emotions under parent's guidance",
    "Кропотливо конструирует научный проект Солнечной системы": "Painstakingly building solar system school science project",
    "Проверяет грузоподъемность модели моста для школьного проекта": "Testing weight capacity of bridge model for school project",
    "Проводит эффектный химический эксперимент с извержением вулкана": "Performing dramatic chemical volcano eruption experiment",
    "Красит и оформляет детали диорамы средневекового замка": "Painting and detailing medieval castle diorama",
    "Собирает миниатюрную ракету для школьного научного проекта": "Building model rocket for school science project",
    "Тестирует датчики и микросхемы научного школьного робота": "Testing sensors and circuit boards of science project robot",
    "Сосредоточенно трудится над научным школьным проектом": "Concentrating intensely on school science project",
    "Устанавливает строгий комендантский час на семейной доске объявлений": "Setting strict curfew on family bulletin board",
    "Прикрепляет записку с поручениями и теплыми словами на семейную доску": "Pinning note with chores and warm words to family board",
    "С гордостью вешает лучший детский рисунок на семейную доску объявлений": "Proudly pinning child's best drawing on family bulletin board",
    "Изучает список домашних обязанностей и поручений на семейной доске": "Checking chore list and household tasks on family board",
    "Красиво сервирует обеденный стол, расставляя приборы и салфетки": "Beautifully setting dining table with silverware and napkins",
    "Заботливо убирает грязную посуду и протирает обеденный стол": "Thoughtfully clearing dirty dishes and wiping dining table",
    "Собирает вкусный домашний ланч-пакет в школу или на работу": "Packing tasty brown bag sack lunch for school or work",
    "Звонко созывает всех домочадцев к накрытому столу на теплый семейный обед": "Calling all family members to the table for warm family meal",
    "Бродит в плюшевом костюме медведя, переживая необычную фазу взросления": "Wandering in bear costume, going through childhood bear phase",
    "Падает на пол и бьется в безудержной детской истерике": "Throwing wild toddler temper tantrum on the floor",
    "Вдохновенно разливает краски и устраивает хаос на полу": "Inspirately spilling paint and making a creative mess on the floor",
    "Вздыхая, оттирает въевшуюся краску и убирает детский беспорядок с пола": "Sighing while scrubbing paint and cleaning up messy floor",
    "В ярости хлопает дверью комнаты в порыве бунтарского подросткового гнева": "Angrily slamming bedroom door in teenage rebellion fury",
    "Искренне доверяет свои самые тайные мысли и переживания личному дневнику": "Pensively writing deepest private thoughts and secrets into personal journal",
    "Осторожно прячет личный дневник под матрас от чужих любопытных глаз": "Carefully hiding private journal under mattress from prying eyes",
    "Тайком листает чужой секретный дневник, боясь быть застигнутым": "Secretly snooping through someone's diary in fear of being caught",
    "Увлеченно играет в детского доктора, ставя диагнозы плюшевым пациентам": "Enthusiastically playing with doctor playset, diagnosing teddy bear patients",
    "Строит грандиозную разноцветную башню из строительных кубиков": "Building a magnificent colorful tower out of toy blocks",
    # GP05 Social exact
    "Просит мудрого родительского совета по воспитанию непослушных детей у": "Asking for wise parenting advice on raising disobedient kids from",
    "Читает строгую нотацию о хороших манерах и послушании для": "Giving a stern lecture on good manners and obedience to",
    "Искренне хвалит за прилежное поведение, помощь по дому и хорошие манеры": "Warmly praising good behaviour, household help, and manners of",
    "Эмоционально бунтует против строгих домашних правил и комендантского часа перед": "Emotionally rebelling against strict rules and curfew before",
    "Крепко и с любовью обнимает, поддерживая в трудную минуту,": "Tightly and lovingly hugging, comforting in difficult moment,",

    # GP07 StrangerVille exact
    "Щелкает каблуками и четко отдает воинскую честь": "Clicking heels and crisply saluting with military honors",
    "Тренирует приемы самообороны и армейского рукопашного боя": "Practicing self-defense moves and military hand-to-hand combat",
    "Командным голосом муштрует подчиненных на плацу": "Drilling subordinates on the parade ground with a commanding voice",
    "Чеканит уверенный строевой шаг в армейском строю": "Marching with confident military drill steps",
    "Упорно отжимается от земли, поддерживая образцовую военную форму": "Powerfully doing push-ups from the ground, maintaining peak military fitness",
    "Скрытно устанавливает подслушивающее устройство": "Stealthily planting a covert listening bug",
    "В наушниках перехватывает секретные переговоры за шпионской станцией прослушки": "Intercepting classified chatter in headphones at covert listening station",
    "Использует тайный шпионский компромат для шантажа": "Using covert spy wiretap audio for blackmail",
    "Сопоставляет улики, фотографии и схемы за доской расследований, собирая тайное досье": "Connecting evidence, photos and blueprints at mystery board, compiling classified dossier",
    "Скрытно фотографирует пульсирующие аномальные лозы возле секретной лаборатории": "Stealthily photographing pulsating bizarre vines near secret lab",
    "Лихорадочно перерывает засекреченные лабораторные папки в поисках правительственных тайн": "Frantically searching classified lab folders for government secrets",
    "Тщательно сканирует почву переносным сканером, собирая редкие фиолетовые споры": "Carefully scanning ground with handheld scanner, gathering rare purple spores",
    "Прикладывает взломанную ключ-карту и отпирает бронированные гермодвери лаборатории": "Swiping hacked lab keycard and unlocking reinforced blast doors of secret lab",
    "Застегивает герметичный костюм химзащиты с фильтром спор перед спуском в кратер": "Zipping up airtight hazmat suit with spore filter before descending into crater",
    "Синтезирует экспериментальную вакцину от спор на химическом анализаторе": "Synthesizing experimental spore vaccine on chemical analyzer",
    "Проводит полевое испытание экспериментальной вакцины от вируса спор": "Conducting field test of experimental spore virus vaccine",
    "Вводит спасительную вакцину, побеждая действие токсичных спор": "Administering life-saving vaccine, curing toxic spore affliction",
    "Нелепо дергается и странно бежит с безумной застывшей улыбкой на лице": "Erratic twitching and bizarrely running with a crazed frozen smile on face",
    "Жадно надкусывает пульсирующий странный плод, добровольно отдавая разум Матери": "Ravenously biting into pulsating bizarre fruit, willingly surrendering mind to the Mother",
    "С фанатичной любовью поливает и лелеет чужеродные хищные лозы в саду": "Fanatically watering and nurturing alien predatory vines in the garden",
    "В трансе произносит бессвязные хвалебные речи великой Матери Кратера": "Speaking incoherent trance praises to the great Mother of the Crater",
    "Яростно поливает гигантское чудовищное Материнское растение струями мега-вакцины": "Furiously hosing monstrous Mother Plant with streams of mega-vaccine",
    "Издает боевой клич, сплачивая команду защитников города": "Sounding war cry, rallying the town defense squad",
    "Наносит решающий сокрушительный удар и окончательно повергает Материнское растение": "Delivering decisive crushing blow and vanquishing the Mother Plant once and for all",
    "Почтительно просит ценных мистических даров и здоровья у возрожденного Материнского растения": "Respectfully requesting precious mystical boons and vitality from revived Mother Plant",
    "Изучает конспирологические артефакты и секретные товары в лавке диковинок": "Browsing conspiracy artifacts and classified oddities at curio shop",
    "Надевает самодельную шапочку из фольги для защиты разума от мысленного контроля": "Donning handmade tin foil hat to shield mind from psychic control",
    # GP07 Social exact
    "С пристрастием расспрашивает о странностях, спорах и секретной лаборатории у": "Intensely questioning about bizarre oddities, spores, and secret lab with",
    "Шепотом делится безумными конспирологическими теориями о правительственном заговоре с": "Whispering wild conspiracy theories about government plots to",
    "Командным тоном отдает строгий воинский приказ и требует субординации от": "Giving strict military order in commanding tone and demanding subordination from",
    "С безумным остекленевшим взглядом бормочет о величии Материнского растения перед": "Muttering with crazed glassy stare about the glory of the Mother Plant before",
    "Призывает объединить силы для финального штурма кратера и победы над чудовищем": "Rallying forces for final crater assault and defeating the monstrosity with",

    # GP08 Realm of Magic exact
    "Шагает в сияющий портал, перемещаясь в парящий Волшебный мир": "Stepping into glowing portal, travelling to floating Magic Realm",
    "Проходит через древний Обряд посвящения, пробуждая в себе дар чародея": "Undergoing ancient Rite of Ascension, awakening spellcaster gift within",
    "Собирает парящие фиолетовые магические сферы для ритуала посвящения": "Gathering floating purple magical motes for the Ascension ritual",
    "Тренируется в концентрации магической энергии и оттачивает заклинания": "Practicing magical energy concentration and honing spells",
    "Произносит заклинание «Чинио», мгновенно восстанавливая сломанный предмет магией": "Casting Repairio spell, instantly mending broken object with magic",
    "Взмахивает палочкой и читает «Чистио», мгновенно очищая всё от грязи": "Waving wand and casting Scruggio, instantly clearing away all dirt",
    "Читает заклинание «Лакомио», материализуя из воздуха аппетитное горячее блюдо": "Casting Delicioso spell, materializing delicious hot meal out of thin air",
    "Читает заклинание «Травио», наполняя увядающие растения живительной магией": "Casting Floralorial spell, infusing wilting plants with revitalizing magic",
    "Читает «Телепортио» и растворяется в воздухе, мгновенно перемещаясь": "Casting Transportalate and vanishing into thin air, teleporting instantly",
    "Читает заклинание «Тиражио», создавая точную магическую копию предмета": "Casting Copypasto spell, creating an exact magical duplicate of object",
    "Читает заклинание «Садио», взращивая плоды прямо на глазах": "Casting Herbio spell, causing plants to sprout and grow before eyes",
    "Читает заклинание «Домойо», мгновенно телепортируясь в родной дом": "Casting Homewardial spell, instantly teleporting back home",
    "Накладывает на противника чары всепоглощающей тоски и отчаяния «Грустио»": "Casting Despairio spell, afflicting opponent with overwhelming gloom",
    "Накладывает заклятие «Бредио», вызывая помрачение чужого рассудка": "Casting Deliriano spell, confusing opponent's mental clarity",
    "Читает заклятие «Яростио», разжигая ярость и агрессию": "Casting Furioso spell, inciting fury and raw aggression",
    "Читает приворотное заклинание «Влюбио»": "Casting Infatuate love charm",
    "С помощью заклинания «Кладио» магически похищает ценную вещь": "Using Burgliate spell to magically steal valuables",
    "Превращает цель в неодушевленную статуэтку заклинанием «Морфио»": "Transforming target into an inanimate figurine using Morphiate spell",
    "Призывает яростное пламя заклинанием «Инферно»": "Summoning raging flames with Inferniate spell",
    "Выпускает трескучие молнии заклинанием «Вжик-вжик»": "Discharging crackling lightning bolts with Zipzap spell",
    "Читает заклинание «Некропризыв», призывая призрака из загробного мира": "Casting Necrocall spell, summoning a ghost from the netherworld",
    "Замораживает противника в лед заклинанием «Обездвижио»": "Freezing opponent into solid ice with Chillio spell",
    "Порабощает чужой разум заклинанием ментального подчинения «Подчинио»": "Enslaving opponent's mind with Minionize thrall spell",
    "Читает великое заклинание «Оживио», воскрешая призрака": "Casting grand Dedeathify spell, resurrecting the ghost",
    "Читает заклинание «Снимио», снимая с себя тягостное проклятие": "Casting Decursify spell, purging dark curse from self",
    "Колдует над бурлящим котлом, помешивая волшебное зелье черпаком": "Brewing over bubbling cauldron, stirring magical potion with ladle",
    "Экспериментирует с редкими ингредиентами и магическими травами в огромном котле": "Experimenting with rare ingredients and magical herbs in giant cauldron",
    "Аккуратно разливает дымящееся готовое зелье по стеклянным склянкам": "Carefully bottling steaming finished potion into glass vials",
    "Варит сытную колдовскую похлебку в старинном чугунном котле": "Cooking hearty witch's stew in vintage cast-iron cauldron",
    "Осушает склянку с магическим зельем, ощущая прилив волшебных сил": "Downing a bottle of magical potion, feeling surge of arcane power",
    "Скрещивает магические лучи в дружеской чародейской дуэли": "Crossing magic beams in friendly spellcaster duel",
    "Сражается в ожесточенной и опасной дуэли на заклинаниях": "Fighting in fierce and hazardous spellcaster duel",
    "Ведет магическую дуэль за ценные артефакты и заклинания": "Engaging in magic duel for valuable artifacts and spells",
    "Призывает и связывает узами духа нового волшебного фамильяра": "Binding spirit bond with a new magical familiar",
    "Призывает парящего верного фамильяра для защиты от магической гибели": "Summoning floating loyal familiar to guard against magical death",
    "Доверительно беседует со своим верным магическим фамильяром": "Confiding in loyal magical familiar",
    "Отпускает волшебного фамильяра отдыхать в астральный мир": "Dismissing magical familiar to rest in astral realm",
    "Выполняет головокружительные кульбиты и мертвые петли в полете на метле": "Performing thrilling stunts and loop-de-loops flying on magic broom",
    "Взмывает в небеса и стремительно летит верхом на волшебной метле": "Soaring into the skies and swooping swiftly on a magic broom",
    "Корчится от переизбытка магического заряда, рискуя погибнуть от перегрузки": "Writhed in magical charge overload, risking death from magical excess",
    "Страдает от мучительного действия древнего темного проклятия": "Suffering from tormenting affliction of ancient dark curse",
    "Выбирает волшебные палочки, книги заклинаний и ингредиенты на Аллее Заклинателей": "Browsing magic wands, spellbooks, and ingredients at Caster's Alley",
    # GP08 Social exact
    "С почтением просит мудреца обучить новому могущественному заклинанию у": "Respectfully asking Sage to teach a powerful new spell to",
    "Просит открыть секретный рецепт древнего алхимического зелья у": "Asking to reveal secret recipe of ancient alchemical potion from",
    "Бросает дерзкий вызов на магическую дуэль для": "Challenging to a daring magical duel",
    "С увлечением обсуждает тонкости магических искусств и волшебные школы с": "Enthusiastically discussing nuances of magic arts and spell schools with",
    "Самонадеянно хвастается своим чародейским превосходством и силой перед": "Arrogantly boasting of spellcaster prowess and might to",
    "Умоляет провести священный Обряд посвящения в чародеи перед": "Pleading to perform sacred Rite of Ascension before",
    "Обеспокоенно жалуется на тяжесть и муки темного проклятия для": "Worryingly lamenting heavy burden and torment of dark curse to",

    # GP09 Star Wars: Journey to Batuu exact
    "Собирает индивидуальный световой меч из рукояти и кайбер-кристалла в мастерской Сави": "Assembling custom lightsaber from hilt and kyber crystal at Savi's Workshop",
    "Оттачивает владение световым мечом, парируя выстрелы летающего тренировочного зонда": "Honing lightsaber prowess, deflecting blasts from hovering training remote",
    "Тренирует боевые стойки и выпады со световым мечом": "Practicing combat stances and lightsaber strikes",
    "Сражается в динамичной и зрелищной дуэли на световых мечах": "Fighting in dynamic and spectacular lightsaber duel",
    "Конструирует и программирует собственного астромеханика в Депо дроидов Мьюбо": "Building and programming custom astromech at Mubo's Droid Depot",
    "Приказывает дроиду устроить громкую диверсию и отвлечь патруль": "Commanding droid to create a loud diversion and distract patrol",
    "Командует дроиду применить защитный электрошокер": "Commanding droid to deploy defensive electric shocker",
    "Подключает дроида к компьютерной панели для скоростного взлома систем безопасности": "Connecting droid to computer panel to slice security systems",
    "Дружелюбно общается с дроидом, слушая его веселое бинарное пищание": "Chatting warmly with droid, listening to its cheerful binary beeps",
    "Забирается в кабину звездного истребителя Т-70 «Крестокрыл» и вылетает на боевую миссию Сопротивления": "Climbing into cockpit of T-70 X-Wing starfighter, embarking on Resistance combat mission",
    "Пилотирует штурмовой шаттл Первого Ордена «СИД-эшелон» в воздушном патруле": "Piloting First Order TIE Echelon assault shuttle on aerial patrol",
    "Занимает место пилота в легендарном «Соколе Тысячелетия» и отправляется в рискованный контрабандный рейс": "Taking pilot seat of legendary Millennium Falcon, setting off on daring smuggling run",
    "Внимательно проверяет гипердвигатель и орудийные турели космического корабля": "Thoroughly inspecting starship hyperdrive and laser cannon turrets",
    "Разыгрывает рискованную партию в сабакк, блефуя и надеясь на чистый сабакк": "Playing risky game of Sabacc, bluffing and aiming for pure Sabacc",
    "Смакует экзотический освежающий галактический коктейль в шумной кантине Оги": "Savoring exotic refreshing galactic cocktail at bustling Oga's Cantina",
    "Лакомится фирменным ронто-врапом с хрустящими местными специями Батуу": "Enjoying signature Ronto Wrap with crispy local Batuu spices",
    "Отрывается под зажигательные инопланетные ритмы дроида-диджея DJ R-3X в кантине Оги": "Grooving to catchy alien beats of DJ R-3X droid at Oga's Cantina",
    "Сканирует датапад и проводит проверку личности подозрительного прохожего": "Scanning datapad and conducting identity check on suspicious citizen",
    "Берет под арест нарушителя порядка Первого Ордена": "Placing First Order curfew violator under arrest",
    "Взламывает защищенную контрольную панель аванпоста с помощью даташифратора": "Slicing secure outpost control panel using dataspike tool",
    "Скрытно следит за перемещениями офицеров и передает координаты штабу Сопротивления": "Stealthily tracking officer movements and transmitting coordinates to Resistance HQ",
    "Проводит тайную операцию по доставке ценного контрабандного груза в обход патрулей": "Conducting covert operation to deliver valuable contraband cargo past patrols",
    "Отдыхает и восстанавливает силы в жилом отсеке на аванпосте Черный Шпиль": "Resting and recharging in dwelling quarters at Black Spire Outpost",
    "Использует внушение Силы для обхода бдительности собеседника": "Using Jedi Force mind trick to bypass suspicion",
    # GP09 Social exact
    "Приказывает предъявить идентификационный чип для проверки личности для": "Ordering to present identification chip for ID check to",
    "Пламенно агитирует вступить в тайные ряды Сопротивления перед": "Passionately rallying to join secret ranks of Resistance before",
    "Строго требует присягнуть на верность Первому Ордену и Верховному лидеру перед": "Sternly demanding allegiance to First Order and Supreme Leader before",
    "Шепотом предлагает выгодную контрабандную сделку и депешу для": "Whispering lucrative smuggling deal and dispatch to",
    "Предлагает сыграть рискованную партию в сабакк на галактические кредиты для": "Challenging to high-stakes Sabacc card game for galactic credits with",
    "С шипением активирует световой меч и вызывает на поединок": "Igniting lightsaber with a hiss and challenging to duel",
    "Плавно ведет рукой и применяет ментальное джедайское внушение Силы к": "Waving hand smoothly and applying Jedi mental Force mind trick on",

    # GP10 Dream Home Decorator exact
    "Делает снимки комнаты «До ремонта» на камеру для профессионального портфолио": "Taking 'Before' photos of the room for professional design portfolio",
    "Фотографирует обновленное стильное пространство «После ремонта» для портфолио": "Photographing stylish renovated room 'After' renovation for design portfolio",
    "Тщательно измеряет стены и дверные проемы рулеткой, оценивая габариты помещения": "Carefully measuring walls and doorways with measuring tape, assessing room dimensions",
    "Внимательно осматривает планировку и естественное освещение комнаты перед переделкой": "Attentively inspecting room layout and natural lighting before makeover",
    "Провожает хозяев дома на прогулку перед началом масштабного ремонта": "Escorting homeowners out for a walk before major renovation begins",
    "Звонит клиентам и радостно сообщает о завершении грандиозного ремонта": "Calling clients and cheerfully announcing the grand renovation completion",
    "Торжественно распахивает двери, начиная грандиозный показ готового интерьера": "Grandly swinging doors open, kicking off the Big Reveal of renovated interior",
    "Демонстрирует клиентам ключевой обновленный акцент в интерьере": "Showing clients the key renovated interior accent",
    "Всплескивает руками и чуть не плачет от счастья, восхищаясь новым интерьером": "Gasping and tearing up with sheer joy, adoring the new interior",
    "Обескураженно морщится и разочарованно разглядывает неудачные дизайнерские решения": "Cringing in dismay, looking disappointed at poor design choices",
    "Выносит окончательный вердикт и рассчитывается за выполненный ремонт": "Delivering final verdict and paying for completed renovation",
    "Уютно устроился на мягком секционном модульном диване": "Cozying up on a plush modular sectional sofa",
    "Аккуратно раскладывает одежду по полочкам встроенной модульной гардеробной": "Neatly organizing clothing on shelves of built-in modular closet system",
    "Любуется отражением и примеряет наряды у зеркала модульного гардероба": "Admiring reflection and trying on outfits by modular closet mirror",
    "Гармонично расставляет книги, суккуленты и дизайнерский декор на модульных полках": "Harmoniously arranging books, succulents and designer decor on modular shelves",
    "Готовит изысканное блюдо на современной встроенной индукционной варочной панели": "Cooking gourmet dish on sleek built-in induction cooktop",
    "Запекает хрустящие тосты и закуски в компактной настольной духовке": "Baking crispy toasts and treats in compact countertop oven",
    "Увлеченно чертит планировку и собирает цветовой мудборд на графическом планшете": "Enthusiastically sketching room layout and compiling color moodboard on tablet",
    "Пишет экспертную статью о современных трендах в интерьере для журнала архитектуры": "Writing expert interior design trend column for architecture magazine",
    # GP10 Social exact
    "Деликатно расспрашивает о вкусах, любимых цветах и стилях интерьера у": "Delicately asking about preferences, favorite colors, and decor styles from",
    "Торжественно показывает обновленный интерьер и ждет эмоциональной оценки от": "Grandly revealing renovated interior and awaiting emotional reaction from",
    "С гордостью демонстрирует стильный элемент обновленного декора для": "Proudly showing off stylish piece of renovated decor to",
    "Увлеченно обсуждает тренды дизайна интерьеров и гармонию колористики с": "Enthusiastically discussing interior design trends and color theory with",
    "Профессионально критикует планировку, освещение и сочетание мебели перед": "Professionally critiquing layout, lighting, and furniture harmony before",
    "С воодушевлением хвастается снимками успешных дизайнерских проектов из портфолио перед": "Excitedly boasting about successful portfolio project photos to",
    "С замиранием сердца просит вынести окончательный вердикт о ремонте у": "Anxiously asking to deliver final renovation verdict from",

    # GP11 My Wedding Stories exact
    "Пробует кусочки праздничных свадебных тортов, выбирая идеальный вкус для банкета": "Tasting slices of festive wedding cakes, choosing perfect flavor for banquet",
    "Выбирает нежный свадебный букет из свежих цветов у флориста в Тартозе": "Selecting delicate wedding bouquet from fresh flower florist in Tartosa",
    "Примеряет роскошный свадебный наряд перед зеркалом, готовясь к торжеству": "Trying on exquisite wedding attire in front of mirror, getting ready for celebration",
    "Планирует сценарий свадьбы, дресс-код и список гостей для церемонии": "Planning wedding activities, dress code, and guest list for ceremony",
    "Звонит в старинные свадебные колокола Тартозы, возвещая о празднике любви": "Ringing historic Tartosa wedding bells, proclaiming the celebration of love",
    "Торжественно шествует по свадебному проходу к украшенной цветами арке": "Solemnly walking down the wedding aisle toward flower-decorated arch",
    "С умилением разбрасывает лепестки роз по дорожке перед молодыми": "Lovingly tossing rose petals along aisle path before newlyweds",
    "Бережно несет бархатную подушечку с обручальными кольцами к арке": "Carefully carrying velvet pillow with wedding rings to arch",
    "Ведет торжественную церемонию бракосочетания у свадебной арки": "Presiding over solemn wedding ceremony by wedding arch",
    "Произносит трогательную свадебную клятву перед лицом гостей": "Reciting touching wedding vows before gathered guests",
    "Надевает обручальное кольцо на палец избранника, скрепляя союз": "Putting wedding ring on partner's finger, sealing union",
    "Сливается в трепетном первом поцелуе молодоженов под свадебной аркой": "Sharing tender first kiss as newlyweds under wedding arch",
    "Радостно пускает мыльные пузыри и осыпает молодоженов лепестками": "Joyfully blowing bubbles and showering newlyweds with petals",
    "Совместно разрезает праздничный свадебный торт под аплодисменты гостей": "Cutting celebratory wedding cake together to applause of guests",
    "Угощает партнера сладким кусочком свадебного торта": "Treating partner to a sweet bite of wedding cake",
    "Поднимает праздничный тост за счастье и долгие годы молодых": "Raising celebratory toast to happiness and long life of newlyweds",
    "Кружится в медленном романтическом первом танце новобрачных": "Twirling in slow romantic first dance of newlyweds",
    "Поворачивается спиной и бросает свадебный букет в толпу незамужних гостей": "Turning around and tossing bridal bouquet into crowd of single guests",
    "Ликует от восторга, поймав заветный букет невесты": "Cheering in triumph after catching the coveted bridal bouquet",
    "Проводит традиционную свадебную чайную церемонию, отдавая дань уважения предкам": "Conducting traditional wedding tea ceremony, honoring elders and ancestors",
    "Любуется закатом над водопадами и морем в романтичной Тартозе": "Admiring sunset over waterfalls and sea in romantic Tartosa",
    # GP11 Social exact
    "С трепетом просит стать почетным свидетелем на свадьбе у": "Anxiously asking to be Sim of Honor at wedding from",
    "Просит стать регистратором свадебной церемонии и скрепить союз у": "Asking to officiate wedding ceremony and seal vows from",
    "С умилением доверяет почетную роль цветочника на свадьбе для": "Fondly entrusting honorary role of flower pal at wedding to",
    "Доверяет священную роль хранителя обручальных колец для": "Entrusting sacred role of ring bearer to",
    "Поднимает бокал игристого нектара и произносит трогательный свадебный тост за": "Raising glass of sparkling nectar and giving touching wedding toast to",
    "Взволнованно делится предсвадебным мандражом и трепетом с": "Nervously sharing wedding jitters and excitement with",
    "С теплой улыбкой вспоминает трогательные моменты свадебной церемонии с": "Warmly reminiscing about touching wedding ceremony moments with",

    # GP12 Werewolves exact
    "Неистово крушит всё вокруг в приступе неукротимого волчьего бешенства": "Wildly smashing everything around in fit of uncontrollable werewolf rampage",
    "В муках трансформируется в свирепое звериное обличье под светом луны": "Painfully transforming into ferocious werewolf beast form under moonlight",
    "Издает скорбный вой, пытаясь обуздать кипящую ярость и вернуть человеческое самообладание": "Letting out somber howl, attempting to tame boiling fury and regain human composure",
    "Запрокидывает голову к ночному небу и протяжно воет на сияющую луну": "Tilting head back to night sky and letting out long howl at shining moon",
    "Издает раскатистый стайный вой, призывая волчью стаю объединиться": "Letting out resonant pack howl, summoning wolf pack to unite",
    "По-звериному метит территорию, обозначая границы своих охотничьих угодий": "Marking territory beast-style, claiming boundaries of hunting grounds",
    "Яростно разрывает землю когтями в поисках древних реликвий и костей": "Ferociously clawing and scavenging ground in search of ancient relics and bones",
    "С диким аппетитом пожирает сырое мясо и грызет всё, что попадается на пути": "Devouring raw meat with feral appetite and gnawing on anything in path",
    "Тщательно вылизывает и чистит густую волчью шерсть": "Meticulously licking and grooming thick wolf fur",
    "Сворачивается клубком на голой земле и чутко дремлет в зверином обличье": "Curling into a ball on bare ground and napping lightly in beast form",
    "Стремительно крадется по лесной чаще в поисках свежей дичи на ночной охоте": "Swiftly prowling through forest thickets tracking fresh prey on night hunt",
    "Сходится в свирепом боевом спарринге оборотней": "Clashing in ferocious werewolf combat sparring match",
    "Сражается за главенство и лидерский статус вожака Альфы в стае": "Fighting for dominance and Alpha pack leader rank in pack",
    "Отчаянно сходится в смертоносной схватке с легендарным свирепым волком Грегом": "Desperately clashing in deadly battle with legendary ferocious wolf Greg",
    "С опаской осматривает предостерегающие знаки у логова опасного отшельника Грега": "Apprehensively inspecting warning signs near dangerous hermit Greg's lair",
    "Пробирается сквозь темные лабиринты заброшенных подземных тоннелей Мунвуд Милл": "Navigating dark labyrinths of abandoned Moonwood Mill underground tunnels",
    "Купается в мистических ледяных водах озера Лунвик под лунным сиянием": "Swimming in mystical icy waters of Lake Lunvik under moonlight",
    "Внимательно изучает старинные дневники и расшифровывает древние тайны ликантропии": "Carefully studying ancient diaries and deciphering ancient secrets of lycanthropy",
    "Проводит время в логове стаи, укрепляя братские узы и выполняя поручения вожака": "Spending time at pack hangout, forging pack bonds and fulfilling leader duties",
    "Вносит ценную добычу и ресурсы в общий сундук стаи оборотней": "Contributing valuable loot and resources to shared werewolf pack trunk",
    "Вонзает клыки, передавая древний дар ликантропии": "Sinking fangs, passing the ancient gift of lycanthropy",
    "Завороженно любуется полной луной, ощущая зов древней первобытной природы": "Mesmerized gazing at full moon, feeling call of ancient primal nature",
    # GP12 Social exact
    "Издает раскатистый стайный вой, приветствуя собратьев по стае перед": "Letting out resonant pack howl, greeting packmates before",
    "По-звериному ласково трется носом и выказывает волчью преданность перед": "Affectionately nuzzling snout and showing wolfish devotion before",
    "Свирепо рычит, обнажая острые клыки и запугивая": "Ferociously growling, baring sharp fangs and intimidating",
    "С почтением просит принять в ряды волчьей стаи у": "Respectfully asking to join the ranks of the wolf pack from",
    "Вызывает на дружеский тренировочный спарринг оборотней": "Challenging to friendly werewolf sparring practice",
    "С замиранием сердца признается в нерушимой связи истинной пары предначертанной судьбой перед": "Heartfeltly confessing unbreakable bond of fated mate before",
    "Умоляет одарить даром ликантропии через укус оборотня у": "Pleading to grant gift of lycanthropy through werewolf bite from",
    "Делится секретами обуздания ярости и волчьего темперамента с": "Sharing secrets of taming fury and wolf temperament with",
    "С тревогой и любопытством расспрашивает о свирепом волке-отшельнике Греге у": "Anxiously and curiously inquiring about fierce hermit wolf Greg from",


    # SP01 Luxury Party Stuff exact
    "Заполняет фонтан изысканным фруктовым пуншем и освежающими напитками": "Filling fountain with exquisite fruit punch and refreshing beverages",
    "Заполняет праздничный фонтан струящимся теплым шоколадом": "Filling festive fountain with flowing warm chocolate",
    "Заполняет фонтан аппетитным расплавленным сырным фондю": "Filling fountain with mouth-watering melted cheese fondue",
    "Обмакивает сочную спелую клубнику в струящийся шоколадный фонтан": "Dipping juicy ripe strawberry into flowing chocolate fountain",
    "Окунает аппетитные закуски в нежное горячее сырное фондю": "Dipping delicious snacks into tender hot cheese fondue",
    "Наполняет бокал искрящимся напитком из праздничного фонтана": "Filling glass with sparkling beverage from festive fountain",
    "Тайком подмешивает секретный ингредиент в праздничный фонтан с напитками": "Secretly slipping special ingredient into festive drink fountain",
    "Изысканно сервирует банкетный стол деликатесами, канапе и закусками": "Exquisitely serving banquet buffet table with delicacies, canapes and appetizers",
    "Наполняет тарелку изысканными закусками с банкетного стола": "Filling plate with exquisite delicacies from banquet buffet table",
    "С наслаждением лакомится нежными миндальными пирожными макарон": "Blissfully indulging in delicate almond macaron pastries",
    "Любуется своим блистательным вечерним нарядом перед зеркалом": "Admiring dazzling glamorous evening outfit in the mirror",
    "Элегантно дефилирует в ослепительном вечернем наряде, купаясь во внимании гостей": "Elegantly strutting in dazzling evening wear, basking in guests' admiration",
    "Грациозно танцует под звуки светской музыки среди сияющих огней вечеринки": "Gracefully dancing to high-society party music amidst glittering lights",
    # SP01 Social exact
    "Делает изысканный светский комплимент роскошному вечернему наряду для": "Paying an exquisite high-society compliment on the glamorous evening outfit to",
    "С упоением обсуждает пикантные светские сплетни высшего общества с": "Enthusiastically discussing juicy high-society gossip with",
    "Самодовольно хвастается размахом вечеринки и роскошным образом жизни перед": "Smugly boasting about lavish party scale and luxurious lifestyle to",
    "Элегантно поднимает хрустальный бокал и произносит изысканный тост за": "Elegantly raising crystal glass and giving glamorous toast to",
    "Утонченно и чарующе флиртует на светском рауте с": "Sophisticatedly and charmingly flirting at high-society cocktail party with",


    # SP02 Perfect Patio Stuff exact
    "Нежно обнимается и целуется в теплой воде джакузи": "Lovingly cuddling and kissing in warm hot tub water",
    "Беззаботно купается нагишом в теплой гидромассажной ванне под открытым небом": "Carefreely skinny dipping in warm open-air hot tub under the sky",
    "Наслаждается сеансом целебной ароматерапии с эфирными маслами в джакузи": "Enjoying healing aromatherapy session with essential oils in hot tub",
    "Улучшает гидромассажную ванну, монтируя мощные струи и стереосистему": "Upgrading hot tub, installing powerful water jets and stereo system",
    "Подсыпает мыльную пену в джакузи, устраивая забавный пенный переполох": "Slipping soap into hot tub, triggering a hilarious bubbly foam overflow",
    "Нежится в бурлящей гидромассажной ванне с расслабляющими пузырьками": "Soaking in bubbling hot tub with relaxing jets",
    "Жарит аппетитное сочное барбекю на открытом гриле во внутреннем дворике": "Grilling appetizing juicy barbecue on patio outdoor grill",
    "Обедает свежеприготовленным барбекю за уютным столиком с зонтиком на веранде": "Dining on freshly grilled barbecue at cozy umbrella table on patio",
    "Безмятежно отдыхает и греется на солнце в удобном шезлонге во внутреннем дворике": "Serenely relaxing and sunbathing in comfy patio lounge chair",
    # SP02 Social exact
    "Приглашает окунуться и расслабиться в теплой гидромассажной ванне": "Inviting to soak and unwind in warm bubbly hot tub",
    "Игриво и весело брызгается теплой водой в джакузи на": "Playfully splashing warm water in hot tub at",
    "Романтично шепчет нежные признания под шелест пузырьков джакузи для": "Romantically whispering tender words amid bubbling hot tub jets to",
    "Увлеченно делится любимыми рецептами барбекю, стейков и маринадов с": "Enthusiastically sharing favorite BBQ recipes, steaks and marinades with",
    "С восхищением хвалит уют и приятную расслабляющую атмосферу патио перед": "Admiringly praising cozy and relaxing patio atmosphere before",
    # SP03 Cool Kitchen Stuff exact
    "Готовит партию нежного домашнего мороженого в мороженице": "Making a batch of creamy homemade ice cream in the ice cream maker",
    "Украшает мороженое сладким сиропом, взбитыми сливками и кондитерской посыпкой": "Garnishing ice cream with sweet syrup, whipped cream and sprinkles",
    "Накладывает аппетитные шарики мороженого в хрустящий вафельный рожок": "Scooping appetizing ice cream scoops into a crispy waffle cone",
    "Раскладывает шарики мороженого в изящную десертную креманку": "Scooping ice cream scoops into an elegant dessert bowl",
    "Хватается за голову от внезапной и пронзительной заморозки мозга": "Clutching head from sudden and intense ice cream brain freeze",
    "Выдыхает клуб горячего пламени после порции драконьего мороженого": "Exhaling a plume of fire after a bite of dragon's breath ice cream",
    "Дрожит от леденящего холода, ощущая призрачный мятный мороз": "Shivering with chills, feeling the ghostly mint freeze",
    "С удовольствием лакомится тающим мороженым в хрустящем вафельном рожке": "Blissfully enjoying melting ice cream in a crispy waffle cone",
    "Неспешно смакует изысканный холодный десерт ложечкой из креманки": "Leisurely savoring gourmet ice cream with a spoon from a dessert bowl",
    "С гордостью любуется стильным гарнитуром и сияющими поверхностями кухни": "Proudly admiring sleek modern cabinetry and gleaming kitchen surfaces",
    "Тщательно протирает столешницы и наводит идеальный лоск на современной кухне": "Thoroughly wiping down countertops and polishing modern kitchen surfaces",
    # SP03 Social exact
    "Восхищается нежным вкусом домашнего мороженого перед": "Praising the exquisite flavor of homemade ice cream before",
    "Жарко спорит о лучшем вкусе мороженого и выборе между рожком и креманкой с": "Heatedly debating the best ice cream flavor and cone vs bowl with",
    "Шепотом делится секретным рецептом необычного экзотического мороженого с": "Whispering a secret recipe for unusual exotic ice cream to",
    "С улыбкой предостерегает от коварной заморозки мозга при поедании мороженого для": "Playfully warning about sneaky brain freeze while eating ice cream to",
    "Делает комплимент безупречному дизайну современной кухни и кулинарному вкусу для": "Complimenting the sleek modern kitchen design and culinary taste of",
    # SP04 Spooky Stuff exact
    "Со всей силы яростно растаптывает резную тыкву в оранжевые ошмётки": "Furiously stomping and smashing the carved pumpkin into pieces",
    "Надевает на голову жуткую резную тыкву, пугая всех вокруг": "Wearing a spooky carved pumpkin head, scaring everyone around",
    "Обрабатывает резную тыкву защитным раствором для долгой сохранности": "Treating carved pumpkin with preserving spray to keep it fresh",
    "Зажигает мерцающую свечу внутри резной праздничной тыквы": "Lighting a flickering candle inside the carved festive pumpkin",
    "Мастерски вырезает зловещую светящуюся рожицу на спелой оранжевой тыкве": "Skilfully carving a sinister glowing face on a ripe orange pumpkin",
    "С визгом отскакивает от вазы со сладостями, испугавшись выскочившей руки скелета": "Screaming and jumping back in terror from the snapping skeleton hand in candy bowl",
    "Осторожно тянется за сладостью в мистическую вазу с конфетами": "Cautiously reaching for a treat in the mystical spooky candy bowl",
    "Готовит жуткие сырные шарики с глазами и хрустящее печенье к празднику": "Cooking eerie eyeball cheese balls and crunchy spooky cookies for the party",
    "С опаской пробует жуткое хэллоуинское угощение со стола": "Timidly tasting spooky Halloween party treats from the table",
    "Разглядывает жуткие декорации, паутину и светящиеся гирлянды на вечеринке": "Examining spooky party decorations, cobwebs and glowing lanterns",
    "Примеряет маскарадный костюм для жуткой праздничной вечеринки": "Trying on a fancy masquerade costume for the spooky party",
    # SP04 Social exact
    "Выпрашивает жуткие праздничные сладости и угощения у": "Begging for festive spooky party sweets and treats from",
    "Внезапно пугает леденящим «Бу!» и зловещим оскалом": "Playfully scaring with a chilling 'Boo!' and sinister grin",
    "С замиранием сердца рассказывает жуткую историю о призраках и духах для": "Breathlessly telling a spooky ghost story to",
    "Восхищается оригинальным и пугающим маскарадным костюмом": "Admiring the creative and eerie costume of",
    "Хвастается своим зловещим праздничным нарядом и пугает образ перед": "Showing off sinister spooky costume and striking a spooky pose before",
    # SP05 Movie Hangout Stuff exact
    "Готовит большую миску хрустящего ароматного попкорна в попкорнице": "Making a large bowl of fragrant crunchy popcorn in popcorn popper",
    "Ловко подбрасывает воздушную кукурузу и ловит её ртом": "Skillfully tossing popcorn into the air and catching it in mouth",
    "Хрустит аппетитным теплым попкорном под просмотр кинофильма": "Munching on warm delicious popcorn while watching a movie",
    "Уютно прижимается и обнимается при совместном просмотре романтического фильма": "Snuggling and cuddling during romantic movie",
    "В ужасе закрывает глаза руками от пугающей сцены фильма ужасов": "Covering eyes in terror during scary horror movie scene",
    "Громко хохочет над уморительной комедией на большом экране кинотеатра": "Laughing out loud at hilarious comedy on big movie screen",
    "Утирает слезы от трогательной мелодрамы перед экраном домашнего кинотеатра": "Wiping away tears from touching drama before home theater screen",
    "С замиранием сердца смотрит захватывающий фильм на гигантском киноэкране": "Watching gripping movie on giant movie screen with bated breath",
    "Расслабляется в уютном богемном кресле среди ярких подушек и гирлянд": "Relaxing in cozy bohemian armchair amidst vibrant cushions and fairy lights",
    # SP05 Social exact
    "С горящими глазами обсуждает любимый фильм, сюжетные повороты и актёров с": "Enthusiastically discussing favorite movie, plot twists and actors with",
    "Жарко спорит о неоднозначной концовке и скрытом смысле просмотренного фильма с": "Heatedly debating the ambiguous ending and hidden meaning of the movie with",
    "Шикает и просит не шуметь и не спойлерить во время киносеанса": "Shushing and asking to keep quiet and avoid spoilers during movie for",
    "Дружелюбно угощает хрустящим теплым попкорном из своей миски": "Friendlily offering crispy warm popcorn from personal bowl to",
    "Увлеченно спорит о превосходстве любимого кинематографического жанра с": "Passionately arguing superiority of favorite film genre with",
    # SP06 Romantic Garden Stuff exact
    "В ужасе пятится от злорадного лика колодца желаний, предвещающего беду": "Backing away in terror from sinister face of wishing well foreboding misfortune",
    "Ликует от невероятной щедрости и исполнения мечты у колодца желаний": "Rejoicing over incredible generosity and wish granted by wishing well",
    "Бросает монетку и загадывает заветное желание у шепчущего колодца желаний": "Tossing a coin and making a cherished wish at whispering wishing well",
    "Выливает флакон мыла в фонтан, наполняя сад гигантскими хлопьями пены": "Pouring soap bottle into fountain, filling garden with huge foam bubbles",
    "Задорно плещется и играет струями воды в прохладном фонтане": "Playfully splashing and frolicking in cool fountain water streams",
    "Бросает блестящую монетку в фонтан и загадывает романтическое желание": "Tossing shiny coin into fountain and making a romantic wish",
    "Умиротворенно сидит на бортике фонтана, слушая мерное журчание воды": "Peacefully sitting on fountain edge, listening to gentle water burble",
    "Нежно обнимается и целуется на уединенной кованой скамейке в саду": "Gently cuddling and kissing on secluded garden bench",
    "Вдыхает сладкий аромат цветущих роз в романтическом саду": "Breathing in sweet scent of blooming roses in romantic garden",
    "Неспешно прогуливается по благоухающему парку среди увитых плющом арок": "Leisurely strolling through fragrant park among ivy-covered arches",
    # SP06 Social exact
    "Шепчет возвышенные романтические стихи среди цветущих роз для": "Whispering poetic romantic verses amidst blooming roses to",
    "Таинственно приглашает загадать совместное желание у колодца желаний": "Mysteriously inviting to make a joint wish at whispering wishing well",
    "Игриво и задорно окатывает прохладными брызгами из фонтана": "Playfully splashing cool fountain water at",
    "С упоением обсуждает изящество античных статуй и ландшафтного дизайна с": "Admiringly discussing elegance of antique statues and landscape with",
    "С трепетом в сердце признаётся в искренних чувствах среди аромата цветов для": "Heartfeltly confessing genuine feelings amid flower blossoms to",
    # SP07 Kids Room Stuff exact
    "Показывает захватывающий кукольный детектив с таинственными уликами в театре": "Putting on a thrilling mystery puppet show with clues at the theater",
    "Разыгрывает фантастическую космическую оперу с кукольными пришельцами в театре": "Performing a fantastic sci-fi space opera puppet show at the theater",
    "Показывает трогательную школьную сказку в детском кукольном театре": "Putting on a touching school drama puppet show at the kids theater",
    "Устраивает уморительное комедийное кукольное представление в детском театре": "Putting on a hilarious comedy puppet show at the kids theater",
    "Показывает захватывающее кукольное представление в кукольном театре": "Putting on an exciting puppet show at the puppet theater",
    "Усердно репетирует кукольный спектакль, отрабатывая голоса и интонации персонажей": "Diligently rehearsing a puppet show, practicing voices and character intonations",
    "С восторгом смотрит яркое представление в детском кукольном театре": "Delightedly watching vibrant puppet show at the kids puppet theater",
    "Азартно разыскивает редкие коллекционные карточки космических монстров": "Eagerly searching for rare collectible Voidcritter cards",
    "Ликует и празднует триумфальную победу своего космического монстра на арене": "Rejoicing and celebrating triumphant victory of Voidcritter in the arena",
    "Огорчается из-за обидного поражения своего космического монстра в битве": "Upset over disappointing defeat of Voidcritter in battle",
    "Тренирует своего космического монстра на электронной арене, повышая его боевой уровень": "Training Voidcritter on electronic battle station, leveling up its power",
    "С азартом обменивается коллекционными карточками космических монстров": "Eagerly trading collectible Voidcritter cards",
    "Внимательно изучает характеристики, способности и стихию редкой карточки монстра": "Carefully examining stats, element and powers of rare Voidcritter card",
    "Сражается в напряженной карточной дуэли космических монстров на боевой станции": "Battling in an intense Voidcritter card duel at the battle station",
    "Задорно танцует и подпевает под модные молодежные треки радиостанции «Твин-поп»": "Cheerfully dancing and singing along to trendy Tween Pop radio tracks",
    "С горящими глазами смотрит захватывающий сериал про космических монстров по ТВ": "Watching thrilling Voidcritters show on TV with wide eyes",
    # SP07 Social exact
    "Гордо хвастается редкой карточкой космического монстра перед": "Proudly bragging about rare Voidcritter card to",
    "Азартно вызывает на эпическую карточную дуэль монстров на боевой арене": "Eagerly challenging to an epic Voidcritter battle station duel against",
    "С горящими глазами обсуждает любимых космических монстров и их стихии с": "Enthusiastically discussing favorite Voidcritters and elements with",
    "С предвкушением приглашает занять места в зрительном зале на кукольный спектакль": "Excitedly inviting to the puppet theater show:",
    "Восхищается мастерством управления куклами и артистизмом спектакля юного кукловода": "Praising puppeteering skills and theatrical talent of",
    # SP08 Backyard Stuff exact
    "С визгом проносится по водной дорожке сквозь пушистые облака мыльной пены": "Screaming in joy while sliding through fluffy soap foam on the water slide",
    "Задорно выливает бутылку жидкого мыла на водную дорожку для создания скользкой пены": "Cheerfully pouring liquid soap onto water slide to create slippery foam",
    "Исполняет эффектный трюк и кружится волчком при скольжении на водной дорожке": "Performing a flashy trick and spinning like a top while water sliding",
    "Неуклюже плюхается и скользит на животе по водной дорожке, поднимая фонтан брызг": "Clumsily belly-flopping and sliding down water slide with a huge splash",
    "Смеётся и с восторгом наблюдает за катающимися на водной дорожке": "Laughing and delightedly watching Sims slide on the water slide",
    "С веселым смехом и брызгами съезжает по водной дорожке на заднем дворе": "Laughing joyfully and splashing down the backyard lawn water slide",
    "В панике отмахивается от набросившейся стаи рассерженных птиц у кормушки": "Frantically swatting away a flock of angry dive-bombing birds at feeder",
    "Насыпает отборные семена в подвесную птичью кормушку на заднем дворе": "Pouring birdseed into hanging bird feeder in the backyard",
    "Завороженно наблюдает за прилетевшими к кормушке разноцветными певчими птицами": "Mesmerized watching colorful songbirds flocking to the bird feeder",
    "Тонко настраивает высоту звучания подвесных колокольчиков ветра": "Finely adjusting the pitch of hanging wind chimes",
    "Умиротворенно слушает нежный мелодичный перезвон колокольчиков ветра": "Peacefully listening to gentle melodious chime of wind chimes",
    "Готовит запотевший кувшин освежающего домашнего лимонада со льдом": "Making a frosty pitcher of refreshing homemade iced lemonade",
    "Наливает из кувшина стакан прохладного цитрусового лимонада со льдом": "Pouring a glass of chilled citrus lemonade on ice from the pitcher",
    "С наслаждением пьет ледяной освежающий напиток из запотевшего стакана": "Delightfully sipping ice-cold refreshing drink from frosted glass",
    "Уютно отдыхает за столиком под ярким зонтиком на свежем воздухе заднего двора": "Cozying up at patio umbrella table in the backyard fresh air",
    # SP08 Social exact
    "С восторгом хвастается головокружительными трюками на водной дорожке перед": "Excitedly bragging about dizzying water slide tricks to",
    "Азартно предлагает посоревноваться в скорости скольжения на водной дорожке с": "Eagerly challenging to a water slide speed race with",
    "Увлеченно обсуждает виды прилетевших птиц и их повадки у кормушки с": "Enthusiastically discussing visiting bird species and habits at feeder with",
    "Восхищается мелодичным и умиротворяющим звоном колокольчиков ветра для": "Praising melodious and soothing sound of wind chimes to",
    "С улыбкой предлагает высокий запотевший стакан домашнего холодного лимонада для": "Warmly offering a tall frosted glass of chilled homemade lemonade to",
    # SP09 Vintage Glamour Stuff exact
    "Искренне благодарит дворецкого за безупречное обслуживание дома": "Genuinely thanking the butler for impeccable household service",
    "Строго отчитывает дворецкого за огрехи в работе": "Sternly reprimanding the butler for shortcomings at work",
    "Выделяет личную спальню и кровать для дворецкого": "Assigning personal bedroom and bed to the butler",
    "Просит дворецкого подать изысканные напитки и закуски": "Requesting the butler to serve exquisite drinks and appetizers",
    "Отпускает дворецкого на заслуженный отдых до следующего рабочего дня": "Dismissing the butler to enjoy well-deserved rest until next work day",
    "Чинно приветствует гостей у дверей особняка с безупречной выправкой дворецкого": "Statelily greeting guests at mansion doorway with impeccable butler poise",
    "Уморительно балуется с маминой помадой и пудрой перед зеркалом туалетного столика": "Hilariously playing with makeup and powder before vanity mirror",
    "Изящно наносит гламурный винтажный макияж перед зеркалом туалетного столика": "Elegantly applying glamorous vintage makeup before vanity table mirror",
    "Придирчиво поправляет прическу и макияж, оценивая свой безупречный образ в зеркале": "Fastidiously touching up hair and makeup, admiring reflection in vanity mirror",
    "С нескрываемым самолюбованием красуется перед винтажным туалетным столиком": "Admiring reflection with undisguised vanity before vintage dressing table",
    "Прихорашивается и наводит красоту перед зеркалом туалетного столика": "Freshening up and getting glamorous before vanity table mirror",
    "С любопытством разглядывает старинные карты и вращает резной глобус-бар": "Curiously studying antique maps and spinning ornate 16th century globe bar",
    "Откидывает крышку старинного глобуса и наливает порцию выдержанного винтажного напитка": "Opening antique globe lid and pouring a serving of vintage aged drink",
    "Неспешно смакует изысканный выдержанный напиток из винтажного хрустального бокала": "Leisurely savoring fine vintage drink from a crystal glassware glass",
    "Томно и расслабленно полулежит на роскошном шезлонге в атмосфере золотого века Голливуда": "Languidly lounging on luxurious chaise in Golden Age of Hollywood elegance",
    # SP09 Social exact
    "Благодарно хвалит дворецкого за безупречную преданную службу перед": "Gratefully praising butler for loyal and impeccable service to",
    "Строго отчитывает дворецкого за неподобающее поведение и оплошности перед": "Sternly scolding butler for improper conduct and mistakes before",
    "С аристократическим достоинством просит подать напиток дворецкого": "Aristocratically ordering a drink from butler",
    "Восхищается изысканным гламурным макияжем и голливудским стилем": "Admiring glamorous vintage makeup and Hollywood style of",
    "Предлагает бокал элитного выдержанного напитка из старинного глобус-бара для": "Offering a glass of aged vintage drink from antique globe bar to",
    # SP10 Bowling Night Stuff exact
    "С грохотом выбивает сокрушительный страйк, сбивая все кегли одним ударом, и ликует!": "Loudly scoring a crushing strike, knocking down all pins in one roll, and cheering!",
    "Точным добивающим броском закрывает спэа, сбивая оставшиеся кегли на дорожке": "Accurately picking up a spare with a clean finishing roll on the lane",
    "Исполняет виртуозный трюковой бросок с эффектным вращением и подкруткой шара": "Executing a skillful trick shot with an impressive spin on the bowling ball",
    "Неуклюже поскальзывается на полированном паркете дорожки при замахе шаром": "Clumsily slipping on the polished bowling lane floor while swinging the ball",
    "С досадой наблюдает, как шар для боулинга с глухим стуком скатывается в боковой желоб": "Watching in dismay as the bowling ball thuds into the gutter lane",
    "Азартно играет в боулинг под неоновыми огнями светомузыки": "Excitedly playing bowling under neon lights and music",
    "Придирчиво выбирает идеальный по весу и цвету шар для боулинга на стойке": "Carefully picking the ideal weight and color bowling ball from the rack",
    "С азартом наблюдает за игрой в боулинг, болея за игроков на дорожках": "Enthusiastically watching bowling and cheering for players on the lanes",
    "Пританцовывает под заводные ритмы стиля ню-диско в зале боулинг-клуба": "Grooving to upbeat NuDisco rhythms inside the bowling alley",
    "Отдыхает на диванчике боулинг-клуба, обсуждая результаты фреймов": "Relaxing on bowling alley sofa, chatting about frame scores",
    "Делает сосредоточенный разбег и посылает шар по гладкой дорожке боулинга": "Taking focused approach and rolling ball down smooth bowling lane",
    # SP10 Social exact
    "Азартно хвастается серией сокрушительных страйков в боулинге перед": "Excitedly bragging about a streak of crushing strikes to",
    "Спортивно вызывает на решающую партию в боулинг": "Sportingly challenging to a decisive bowling match",
    "Увлеченно обсуждает технику подкрутки шара и тяжесть шаров для боулинга с": "Enthusiastically discussing ball spin technique and bowling ball weights with",
    "Смеясь подшучивает над неловко укатившимся в боковой желоб шаром": "Laughingly teasing about clumsy gutter ball roll of",
    "С восторгом восхищается атмосферой ночного неонового лунного боулинга с": "Admiring the vibrant nighttime neon moonlight bowling vibe with",
    # SP11 Fitness Stuff exact
    "Отважно карабкается по скалодрому, уворачиваясь от вырывающихся струй пламени в испытании огнем!": "Bravely climbing the wall while dodging bursts of fire jets in the fire challenge!",
    "Теряет хватку на покатом рельефе скалодрома и с глухим стуком срывается на мягкий мат": "Losing grip on the climbing wall incline and falling with a thud onto the safety mat",
    "Изо всех сил преодолевает сложнейший скоростной маршрут на бегущем скалодроме": "Pushing limits on the challenging speed route of the treadmill climbing wall",
    "Упорно штурмует вертикальные зацепы механического скалодрома, тренируя выносливость и силу хвата": "Steadfastly conquering handholds on the mechanical climbing wall, building endurance and grip strength",
    "С интересом наблюдает за тренировкой скалолаза на механической стене": "Intently watching a climber train on the mechanical wall",
    "Зажигательно пританцовывает на ходу, полностью погрузившись в любимый трек в беспроводных наушниках": "Upbeat dancing on the go, completely immersed in music through wireless earbuds",
    "Слушает бодрящую музыку через компактные спортивные наушники-вкладыши": "Listening to invigorating music through compact sports earbuds",
    "Энергично повторяет ритмичные танцевальные движения за инструктором программы «Пламбумба» перед телевизором": "Energetically following rhythmic dance moves of the Plumbumba TV workout video",
    "Выполняет интенсивные силовые упражнения перед экраном телевизора по видео-программе": "Doing intense muscle sculpting exercises before the TV following a fitness video",
    "Обливаясь потом, старательно повторяет упражнения домашней видео-тренировки перед экраном": "Sweating through a home fitness workout video in front of the TV",
    # SP11 Social exact
    "С гордостью хвастается покорением сложнейшей трассы на скалодроме перед": "Proudly bragging about conquering hardest climbing wall route to",
    "С благоговением рассказывает о прохождении экстремального испытания огнем на скалодроме для": "Awe-inspiringly sharing story of conquering extreme climbing wall fire challenge with",
    "Энергично обсуждает домашние фитнес-программы и тренировки «Пламбумба» с": "Energetically discussing home fitness routines and Plumbumba workouts with",
    "С охами и вздохами жалуется на ноющие мышцы и дикую крепатуру после тренировки для": "Groaning and complaining about sore aching muscles after brutal workout to",
    "С энтузиазмом рекомендует лучший зажигательный плейлист для пробежки в наушниках для": "Enthusiastically recommending best high-energy running playlist for earbuds to",
    # SP12 Toddler Stuff exact
    "С восторженным визгом ныряет и барахтается среди разноцветных шариков в сухом бассейне": "Enthusiastically squealing and splashing around in the colorful ball pit",
    "Задорно разбрасывает разноцветные пластиковые шарики из бассейна во все стороны": "Playfully tossing colorful plastic balls from the pit in all directions",
    "Весело копошится и играет в бассейне с пластиковыми шариками": "Happily bustling and playing in the plastic ball pit",
    "Бережно помогает малышу съехать с детской горки": "Gently helping the toddler down the slide",
    "Смело забирается наверх и со смехом съезжает вниз по пологой детской горке": "Bravely climbing up and laughing while zooming down the toddler slide",
    "С любопытством пробирается на четвереньках сквозь извилистый игровой туннель": "Curiously crawling on all fours through the winding play tunnel",
    "Воображает себя отважным космонавтом, управляющим межгалактическим звездолетом на площадке": "Pretending to be a brave astronaut piloting an intergalactic starship on the playground",
    "Фантазирует о дальних плаваниях, играя в грозного пиратского капитана на палубе игрового корабля": "Pretending to sail the high seas as a fierce pirate captain on the play shipwreck",
    "Активно исследует и осваивает игровой комплекс для малышей, лазая по лесенкам и площадкам": "Actively exploring and climbing through the toddler jungle gym",
    "С теплой улыбкой присматривает за резвящимися на площадке малышами": "Fondly watching the toddlers frolic on the playground",
    "Уютно сидит на детском пледе для пикника, лакомясь аппетитными угощениями": "Cozying up on toddler picnic blanket, enjoying delicious snacks",
    # SP12 Social exact
    "С нежностью хвалит малыша за смелость и ловкость на горке перед": "Tenderly praising toddler's courage and dexterity on the slide to",
    "С теплой улыбкой умиляется забавной возне малыша в сухом бассейне с шариками с": "Warmly adoring toddler's adorable frolicking in the ball pit with",
    "С энтузиазмом обсуждает организацию веселого праздника и встреч малышей на площадке с": "Enthusiastically discussing organizing toddler play date on the playground with",
    "Доверительно делится родительскими секретами и лайфхаками воспитания малышей с": "Confiding parenting tips and toddler rearing secrets with",
    "Весело зовет играть в отважных исследователей и покорителей пиратского корабля": "Cheerfully inviting to pretend play as brave explorers on pirate ship",
    # SP13 Laundry Day Stuff exact
    "Добавляет душистые лепестки цветов и натуральные масла в стиральную машину для аромата": "Adding fragrant flower petals and natural oils into the washing machine for scent",
    "Загружает накопившееся белье в стиральную машину и запускает цикл стирки": "Loading piled-up laundry into the washing machine and starting the wash cycle",
    "Выгружает влажное свежевыстиранное белье из барабана стиральной машины": "Unloading damp freshly washed laundry from the washing machine drum",
    "Тщательно вычищает скопившийся пух и ворс из фильтра сушильной машины для безопасности": "Thoroughly cleaning lint and fuzz from the dryer lint trap for safety",
    "Перекладывает влажные вещи в сушильную машину и включает горячую сушку": "Transferring damp clothes to the dryer and turning on the heat dry cycle",
    "Усердно намыливает и стирает белье вручную в деревянном корыте с пеной": "Diligently scrubbing and hand washing clothes with soapy suds in the rustic wash tub",
    "С усилием выкручивает и отжимает мокрое белье над тазом перед сушкой": "Tightly wringing out wet laundry over the tub before hanging to dry",
    "Аккуратно развешивает мокрое белье на бельевой веревке на свежем воздухе под солнцем": "Neatly hanging wet laundry on the outdoor clothesline under the fresh sun",
    "Снимает с веревки сухое белье, пахнущее ветром, теплым солнцем и свежестью": "Gathering dry clothes from the line smelling of breeze, warm sun, and freshness",
    "С глубоким удовольствием вдыхает приятный аромат свежести и тепла от чистого белья": "Deeply savoring the cozy scent of freshness and warmth from clean laundry",
    "Аккуратно складывает теплое постиранное белье в ровные стопки и убирает в комод": "Neatly folding warm washed laundry into tidy stacks and putting it away",
    "Собирает ворох грязной одежды по комнатам и опустошает корзину для стирки": "Gathering piles of dirty laundry from around the house and emptying the hamper",
    "Занимается домашними хлопотами и стиркой скопившейся одежды": "Tending to household chores and washing accumulated laundry",
    # SP13 Social exact
    "С наслаждением хвастается безупречной чистотой и ароматом свежевыстиранного белья перед": "Delightfully bragging about pristine cleanliness and fresh scent of laundry to",
    "С тяжким вздохом жалуется на бесконечную гору грязной одежды и рутину стирки для": "Heavily sighing and complaining about never-ending pile of dirty laundry to",
    "Увлеченно обсуждает любимые цветочные добавки и эфирные масла для ароматизации белья с": "Enthusiastically discussing favorite floral additives and essential oils for laundry with",
    "Обеспокоенно предупреждает об опасности пожара из-за забитого ворсового фильтра сушилки для": "Anxiously warning about dryer fire hazards from clogged lint trap to",
    "С ностальгией восхищается деревенской романтикой ручной стирки в корыте с": "Nostalgically admiring the rustic charm of hand-washing clothes in wash tub with",
    # SP14 My First Pet Stuff exact
    "Выпивает спасительную сыворотку-противоядие от бешенства грызунов": "Drinking the lifesaving antidote serum for Rabid Rodent Fever",
    "Заказывает целебную сыворотку и вакцину от бешенства грызунов через компьютер": "Ordering a curative serum and Rabid Rodent Fever vaccine on the computer",
    "В панике изучает на компьютере симптомы смертельной болезни «Бешенство грызунов»": "Panickedly researching symptoms of the deadly Rabid Rodent Fever on the computer",
    "Вскрикивает от боли и неожиданности, когда капризный грызун больно кусает за палец": "Yelping in pain and surprise as the feisty rodent bites their finger hard",
    "Насыпает свежий питательный корм в кормушку маленького питомца в вольере": "Refilling fresh nutritious food into the small pet's dish in the habitat",
    "С нежностью угощает маленького грызуна аппетитным лакомством из рук": "Gently offering a tasty treat from their hands to the little rodent",
    "Старательно вычищает и моет клетку грызуна, засыпая свежие опилки": "Diligently cleaning and washing the rodent habitat and adding fresh bedding",
    "Завороженно смотрит, как маленький питомец запускает крошечную ракету из своего вольера": "Mesmerized watching the little pet launch a miniature rocket from its habitat",
    "С изумлением наблюдает за странными научными экспериментами и секретной жизнью хомяка в вольере": "Astonishedly watching the strange scientific experiments and secret life of the hamster in its habitat",
    "С улыбкой наблюдает, как маленький питомец усердно наворачивает круги в беговом колесе": "Smilingly watching the little pet enthusiastically spin laps on the exercise wheel",
    "Тихонько сюсюкает и шепчет забавные секретики на ушко своему маленькому питомцу": "Softly baby-talking and whispering amusing secrets into their little pet's ear",
    "Позволяет маленькому питомцу забавно бегать по рукам и плечам": "Letting the little pet playfully scurry along their arms and shoulders",
    "Ласково держит грызуна на ладонях, гладит пушистую спинку и играет с ним": "Gently holding the rodent in their hands, stroking its fluffy back, and playing",
    "С умилением наряжает своего питомца в забавный карнавальный костюмчик": "Adoringly dressing their pet up in a funny cute costume",
    "С восхищением любуется своим четвероногим другом в очаровательном наряде": "Admiringly gazing at their four-legged friend looking adorable in their outfit",
    "В лихорадочном бреду пускает пену изо рта и галлюцинирует, воображая себя гигантским хомяком": "Frothing at the mouth in feverish delirium and hallucinating as a giant hamster",
    "Мучается от сильного жара, яростного чихания и зуда, вызванных бешенством грызунов": "Suffering from high fever, violent sneezing, and severe itching caused by Rabid Rodent Fever",
    "С нежностью заботится о своем маленьком питомце в вольере": "Tenderly caring for their little pet in the habitat",
    # SP14 Social exact
    "С гордостью хвастается умом, ловкостью и забавными проделками своего маленького грызуна перед": "Proudly bragging about cleverness, agility, and amusing antics of little rodent to",
    "С ужасом и возмущением жалуется на болезненный укус бешеного грызуна для": "Horrifiedly and indignantly complaining about painful bite from rabid rodent to",
    "Обеспокоенно предупреждает о смертельной угрозе бешенства грызунов и советует вакцину для": "Anxiously warning about deadly threat of Rabid Rodent Fever and advising vaccine to",
    "С восторгом умиляется забавному и очаровательному костюмчику своего питомца с": "Enthusiastically gushing over funny and adorable costume of their pet with",
    "С таинственным видом рассказывает о секретных ночных экспериментах и космических планах своего хомяка для": "Mysteriously talking about secret nocturnal experiments and space plans of their hamster to",
    # SP15 Moschino Stuff exact
    "Терпеливо ловит удачный кадр, фотографируя четвероногого питомца со штатива": "Patiently catching the perfect shot, photographing the pet from a tripod",
    "Устанавливает таймер на штативе и делает стильный студийный автопортрет": "Setting the tripod timer and snapping a stylish studio self-portrait",
    "Настраивает освещение и меняет декоративный фон в фотостудии для съемки": "Adjusting studio lighting and changing the backdrop for the fashion shoot",
    "Проводит профессиональную модную фотосессию, снимая модель со штатива в студии": "Conducting a professional fashion photoshoot, photographing the model from a tripod in the studio",
    "Принимает эффектную модную позу перед объективом фотокамеры, как с обложки журнала": "Striking a striking high-fashion pose in front of the camera lens like on a magazine cover",
    "Очаровательно кокетничает и принимает чувственную позу для фотографа": "Charmingly flirting and striking a sensual pose for the photographer",
    "Принимает дерзкую и уверенную позу, демонстрируя стиль и харизму на подиуме": "Striking a bold and confident pose, radiating style and runway charisma",
    "Динамично позирует в прыжке и движении для яркого модного кадра": "Dynamically posing in mid-jump and motion for a high-energy fashion shot",
    "Принимает глубокую задумчивую позу с загадочным взглядом вдаль": "Striking a pensive and thoughtful pose with an enigmatic gaze into the distance",
    "Весело дурачится и корчит милые смешные рожицы перед объективом": "Playfully goofing around and making cute funny faces in front of the lens",
    "Позирует перед камерой на студийном маркере для фотографа": "Posing in front of the camera on the studio mark for the photographer",
    "Отправляет лучшие студийные фотографии клиенту на согласование и публикацию": "Submitting the best studio photos to the client for approval and publication",
    "Тщательно обрабатывает снимки на компьютере, выполняя ретушь и цветовую коррекцию": "Carefully editing photos on the computer, retouching and color-grading the shots",
    "Публикует свежие модные кадры с фотосессии в Симстаграм для подписчиков": "Posting fresh fashion photoshoot shots to Simstagram for followers",
    "Ищет новые выгодные заказы на модные фотосессии в базе агентства фрилансеров": "Browsing freelance agency listings for new high-paying fashion photoshoot gigs",
    # SP15 Social exact
    "Увлеченно обсуждает последние тренды высокой моды и дерзкие коллекции Moschino с": "Enthusiastically discussing latest high fashion trends and bold Moschino collections with",
    "С восхищением хвалит композицию, свет и удачный ракурс на фотографии перед": "Admiringly praising composition, lighting, and perfect camera angle of the photo to",
    "Скептически критикует безвкусный наряд и модные промахи для": "Skeptically criticizing tacky outfit and fashion faux pas to",
    "С энтузиазмом предлагает устроить профессиональную фэшн-фотосессию в студии для": "Enthusiastically offering to set up a professional fashion photoshoot in the studio for",
    "С гордостью хвастается публикацией своих снимков на обложке глянцевого журнала перед": "Proudly bragging about having their photos featured on glossy magazine cover to",
    # SP16 Tiny Living Stuff exact
    "Занимается страстным вуху в раскладной кровати Мёрфи": "Having passionate WooHoo in the fold-down Murphy bed",
    "С тревогой борется с заклинившим и неподатливым механизмом раскладной кровати": "Anxiously struggling with the jammed and stubborn mechanism of the Murphy bed",
    "Чудом избегает опасности быть захлопнутым и придавленным тяжелой кроватью Мёрфи": "Narrowly escaping being crushed and trapped by the heavy Murphy bed",
    "Улучшает кровать Мёрфи, устанавливая усиленные пружины против заклинивания": "Upgrading the Murphy bed with reinforced springs to prevent dangerous jamming",
    "Тщательно чинит и смазывает пружинный механизм раскладной кровати Мёрфи": "Carefully repairing and lubricating the spring mechanism of the Murphy bed",
    "С усилием тянет за ручки и опускает раскладную кровать Мёрфи из стенного шкафа": "Straining to pull the handles and lower the Murphy bed from the wall cabinet",
    "Поднимает и убирает кровать Мёрфи обратно в стенную нишу для освобождения места в комнате": "Lifting and folding the Murphy bed back into the wall to free up floor space",
    "Уютно спит на раскладной кровати Мёрфи, наслаждаясь теплом и мягким матрасом": "Sleeping soundly on the Murphy bed, enjoying warmth and comfortable mattress",
    "Дремлет и восстанавливает силы на разложенной кровати Мёрфи": "Napping and regaining energy on the unfolded Murphy bed",
    "Устроился на кровати Мёрфи и расслабленно отдыхает в компактной комнате": "Lying down on the Murphy bed, relaxing in the compact room",
    "Смотрит увлекательную передачу на универсальной компактной медиасистеме": "Watching an entertaining show on the all-in-one compact media center",
    "Слушает любимую музыку, играющую из встроенных колонок компактного медиацентра": "Listening to favorite tunes from the integrated speakers of the compact media center",
    "Уютно устроился за чтением книги с полки компактного медиа-шкафа": "Cozying up to read a book taken from the compact all-in-one media shelf",
    "Наслаждается идеальным минимализмом, покоем и теплым уютом своего крошечного дома": "Basking in the perfect minimalism, peace, and cozy charm of their tiny home",
    # SP16 Social exact
    "С воодушевлением расхваливает эстетику минимализма и уют жизни в микродоме для": "Inspiringly praising minimalism aesthetics and cozy tiny home living to",
    "С ужасом и содроганием предупреждает о смертельной опасности раскладной кровати Мёрфи для": "Horrifiedly and shuddering warning about deadly hazards of Murphy bed to",
    "С самодовольной улыбкой хвастается копеечными счетами за коммуналку в микродоме перед": "Smugly bragging about dirt-cheap utility bills in tiny home to",
    "С раздражением жалуется на тесноту и вечную нехватку свободного места в крошечном доме для": "Irritatedly complaining about cramped space and lack of room in tiny home to",
    "С азартом обсуждает гениальные лайфхаки экономии места и мебель-трансформер с": "Excitedly discussing brilliant space-saving lifehacks and transformable furniture with",
    # SP17 Nifty Knitting Stuff exact
    "Терпеливо обучает вязанию спицами, показывая правильный хват и набор петель": "Patiently teaching how to knit, demonstrating needle grip and casting on stitches",
    "С досадой распускает неудачный вязаный проект обратно в моток шерстяных ниток": "Frustratedly frogging and unraveling a failed knitting project back into a ball of yarn",
    "С благородным сердцем жертвует связанные вручную теплые вещи на благотворительность": "Generously donating hand-knitted warm garments to charity",
    "С любовью вяжет милую мягкую игрушку из цветных клубков пряжи": "Lovingly knitting an adorable plush toy from colorful yarn balls",
    "С нежностью вяжет крошечный мягкий комбинезон для малыша": "Tenderly knitting a soft tiny onesie for a baby",
    "Кропотливо вяжет уютный шерстяной свитер со сложным узором": "Painstakingly knitting a cozy wool sweater with an intricate pattern",
    "Сосредоточенно вяжет спицами теплые носки или шапку из мягкой пряжи": "Intently knitting warm socks or a beanie from soft yarn",
    "Вяжет стильный предмет декора для дома, ловко орудуя спицами и пряжей": "Knitting a stylish home decor piece, skillfully working needles and yarn",
    "Мерно покачивается в кресле-качалке, неспешно позвякивая вязальными спицами": "Steadily rocking in the rocking chair, clacking knitting needles softly",
    "Умиротворенно качается в кресле-качалке, предаваясь теплым воспоминаниям о былом": "Peacefully rocking in the rocking chair, reminiscing about good old times",
    "Весело раскачивается в деревянном кресле-качалке, смеясь от забавного скрипа": "Cheerfully rocking back and forth in the wooden rocking chair, giggling at the squeaks",
    "Мягко покачивается в уютном кресле-качалке, наслаждаясь тишиной и покоем": "Gently rocking in the cozy rocking chair, enjoying peaceful silence",
    "Мерно и безмятежно покачивается в деревянном кресле-качалке": "Steadily and serenely rocking in the wooden rocking chair",
    "Фотографирует и выставляет рукодельный шедевр на продажу на интернет-ярмарке «Продавито»": "Taking photos and listing handcrafted masterpiece for sale on Plopsy online marketplace",
    "Бережно упаковывает и отправляет через почтовый ящик проданный на «Продавито» заказ": "Carefully packaging and shipping out a sold Plopsy order via the mailbox",
    "Увлеченно листает каталог уникальных товаров от мастеров со всего мира на «Продавито»": "Enthusiastically browsing catalog of unique handmade creations from crafters worldwide on Plopsy",
    "Увлеченно вяжет спицами, ловко перебирая шерстяную пряжу из корзинки": "Enthusiastically knitting with needles, deftly pulling wool yarn from the basket",
    "Ощущает неловкость и холод в романтических отношениях из-за рокового «Проклятия свитера»": "Feeling awkwardness and relationship strain due to the dreaded Sweater Curse",
    # SP17 Social exact
    "С гордостью демонстрирует связанную своими руками вещь перед": "Proudly showing off handcrafted knitted item to",
    "С увлечением обсуждает сложные схемы петель, узоры и виды мягкой пряжи с": "Enthusiastically discussing complex stitch patterns and soft yarn types with",
    "С теплотой и любовью дарит связанную своими руками уютную шерстяную вещь для": "Warmly and lovingly gifting a cozy hand-knitted woolen item to",
    "С энтузиазмом хвастается высокими доходами и успехом своих товаров на «Продавито» перед": "Enthusiastically bragging about high earnings and hot sales on Plopsy to",
    "С досадой жалуется на спущенную петлю и безнадежно запутанный клубок ниток для": "Frustratedly complaining about a dropped stitch and hopelessly tangled ball of yarn to",
    "С ностальгической улыбкой делится теплыми воспоминаниями о былых временах с": "With a nostalgic smile sharing fond memories of the good old days with",
    # SP18 Paranormal Stuff exact
    "С благоговением призывает легендарную горничную-скелета Скелехильду": "Reverently summoning the legendary skeleton maid Bonehilda",
    "Проводит священную церемонию очищения дома от злых духов за спиритическим столом": "Performing a sacred house-cleansing ceremony to banish evil spirits at the seance table",
    "Входит в глубокий транс за спиритическим столом, общаясь с душами умерших": "Entering a deep trance at the seance table, communing with departed souls",
    "Медитирует и сканирует духовные вибрации помещения на предмет паранормальной нестабильности": "Meditating and scanning spiritual vibrations of the room for paranormal volatility",
    "Совершает жуткий ритуал на спиритическом столе, временно принимая форму призрака": "Performing a ghastly ritual at the seance table, temporarily turning into a ghost",
    "Изготавливает защитную священную свечу из эктоплазматического воска": "Crafting a protective sacred candle from ectoplasmic wax",
    "Чертит мелом защитный спиритический круг на полу для проведения сеанса": "Chalking a protective seance circle onto the floor to perform spiritual rites",
    "Проводит таинственный спиритический сеанс за круглым столом с хрустальным шаром": "Conducting a mysterious seance around the table with a crystal ball",
    "Идет на отчаянный шаг и жертвует крошечный кусочек своей души загадочному духу": "Taking a desperate gamble and offering a tiny piece of their soul to the mysterious specter",
    "С осторожностью преподносит ценный подарок или лакомство парящему призрачному духу": "Cautiously offering a valuable gift or treat to the floating specter",
    "В ярости и панике растаптывает жуткую проклятую куклу, изгоняя темную сущность": "Frantically and angrily stomping a creepy cursed doll to banish its dark essence",
    "Брезгливо вытирает липкую мерцающую эктоплазму с пола в проклятом доме": "Squeamishly mopping up sticky glowing ectoplasm from the floor of the haunted house",
    "Выкорчевывает потусторонние ползучие лозы и жуткие наросты скверны": "Ripping out otherworldly creeping tendrils and eerie cursed growths",
    "В ужасе спасается бегством от пылающей яростью и злобой призрачной ведьмы Темперанции": "Fleeing in terror from the blazing, furious spectral witch Temperance",
    "Увлеченно беседует с призрачным обольстителем и наставником Клодом Рене Гидри": "Engaging in spirited conversation with the charming ghostly mentor Claude Rene Guidry",
    "Смело проводит обряд экзорцизма, изгоняя враждебных потусторонних сущностей": "Bravely performing an exorcism, banishing hostile otherworldly entities",
    "Выполняет опасный заказ по паранормальному расследованию, очищая дом от полтергейста": "Fulfilling a perilous paranormal investigator gig, ridding the client's home of poltergeists",
    "Дрожит от всепоглощающего паранормального страха перед шорохами и мерцанием света в проклятом доме": "Shivering in overwhelming paranormal fear at flickering lights and eerie creaks in the haunted house",
    "Ощущает потустороннюю прохладу и незримое присутствие духов в воздухе дома с привидениями": "Feeling the eerie spectral chill and presence of ghosts in the haunted house air",
    # SP18 Social exact
    "С таинственным шепотом рассказывает леденящую кровь историю о привидениях для": "Mysteriously whispering a chilling ghost story to",
    "С трепетом и надеждой просит совета по общению с духами у призрачного джентльмена Гидри": "Reverently asking ghostly gentleman Guidry for advice on dealing with spirits",
    "Ласково обнимает и успокаивает дрожащего от ужаса перед потусторонним собеседника": "Gently hugging and calming their terrified companion who is trembling from paranormal fear",
    "С гордостью хвастается пережитой жуткой ночью в доме с привидениями перед": "Proudly bragging about surviving a spooky night in the haunted house to",
    "С волнением обсуждает потусторонние явления, капризы духов и оккультные тайны с": "Excitedly discussing supernatural phenomena, fickle spirits, and occult secrets with",
    "Игриво флиртует и строит глазки очаровательному призрачному созданию": "Playfully flirting and making eyes at the charming spectral being",
    # SP19 Home Chef Hustle Stuff exact
    "Виртуозно подбрасывает и крутит круг теста для пиццы в воздухе, словно заправский пиццайоло": "Masterfully tossing and spinning pizza dough in the air like a seasoned pizzaiolo",
    "Запекает домашнюю фокаччу или сочный закрытый кальцоне в портативной печи": "Baking artisan focaccia or a juicy calzone in the portable pizza oven",
    "Выпекает ароматную пиццу с хрустящей корочкой и тянущимся сыром в печи для пиццы": "Baking a fragrant pizza with crispy crust and gooey melted cheese in the pizza oven",
    "Выпекает золотистые хрустящие вафли в электрической вафельнице": "Cooking golden crispy waffles in the electric waffle maker",
    "Наслаждается свежеиспеченной хрустящей вафлей с аппетитным топпингом": "Savoring a freshly baked crispy waffle with delicious toppings",
    "Замешивает эластичное тесто с помощью настольного планетарного миксера": "Kneading supple dough with the countertop stand mixer",
    "Взбивает кулинарные смеси и готовит заготовки ингредиентов в настольном миксере": "Whisking culinary mixtures and preparing prepped ingredients in the stand mixer",
    "Громко расхваливает горячие блюда и зазывает голодных прохожих к своему кулинарному прилавку": "Loudly praising hot delicacies and beckoning hungry passersby to their food stand",
    "Открывает кулинарную распродажу и выкладывает аппетитные угощения на витрину торгового прилавка": "Opening a food sale and setting out mouthwatering dishes on the food stand display",
    "Бойко ведет уличную торговлю выпечкой и деликатесами за переносным прилавком": "Briskly tending the portable food stand, selling hot street food and treats",
    "Подсчитывает солидную дневную выручку и наводит порядок на торговом прилавке": "Counting up tidy daily earnings and packing up the food stand",
    "Готовит на кухне с невероятной ловкостью и упоением настоящего шеф-повара": "Cooking in the kitchen with the sublime skill and passion of a master chef",
    # SP19 Social exact
    "С лучезарной улыбкой зазывает прохожих попробовать горячие свежеприготовленные деликатесы для": "With a radiant smile beckoning passersby to try hot freshly-made delicacies to",
    "С энтузиазмом рекомендует попробовать свое фирменное коронное блюдо для": "Enthusiastically recommending their specialty signature dish to",
    "С гордостью хвастается отличной выручкой и успешными продажами уличной еды перед": "Proudly bragging about great profits and thriving street food sales to",
    "С азартом делится кулинарными секретами идеального хрустящего теста для пиццы и вафель с": "Passionately sharing culinary secrets of perfect crispy crust and batter with",
    "С легким вздохом жалуется на привередливых клиентов уличного прилавка и пригоревшую корочку для": "With a light sigh complaining about picky food stand customers and burnt crust to",
    "С неподдельным восторгом хвалит умопомрачительный аппетитный аромат свежей выпечки перед": "Enthusiastically praising the mouthwatering aroma of freshly baked goods to",
    # SP20 Crystal Creations Stuff exact
    "Виртуозно гранит драгоценный камень за геммологическим столом, придавая минералу безупречную форму": "Masterfully cutting a gemstone at the gemology table, shaping the mineral into flawless perfection",
    "Тщательно полирует грани свежеограненного самоцвета, добиваясь ослепительного блеска": "Carefully polishing the facets of a freshly cut gem, achieving a dazzling sparkle",
    "Кропотливо создает авторское ювелирное украшение за геммологическим столом, инкрустируя драгоценный камень": "Painstakingly crafting artisan jewelry at the gemology table, setting a precious gemstone",
    "Внимательно изучает эскизы и выбирает изысканный дизайн для нового ювелирного шедевра": "Carefully reviewing designs and choosing an exquisite setting for a new jewelry masterpiece",
    "Убирает каменную пыль и осколки минералов, наводя идеальный порядок на геммологическом столе": "Sweeping up stone dust and mineral shards, tidying up the gemology table",
    "Увлеченно работает за геммологическим столом над созданием изящных украшений и огранкой камней": "Passionately working at the gemology table crafting fine jewelry and cutting gemstones",
    "Аккуратно раскладывает украшения и кристаллы на решетке для зарядки под лунным светом": "Carefully arranging jewelry and crystals on the grid for moonlight charging",
    "Бережно забирает с решетки заряженное лунным светом ювелирное изделие, светящееся магической силой": "Gently collecting a moonlight-charged piece of jewelry glowing with magical power from the grid",
    "Наблюдает за тем, как кристаллы на решетке впитывают мистическую энергию лунного света": "Watching the crystals on the grid absorb mystical moonlight energy",
    "Бережно собирает диковинные сверкающие самоцветы с ветвей кристального дерева": "Gently harvesting rare sparkling gemstones from the branches of the crystal tree",
    "С заботой ухаживает за волшебным кристальным деревом, любуясь растущими минералами": "Carefully tending the magical crystal tree, admiring the growing minerals",
    "С гордостью и восхищением разглядывает надетое на себя сверкающее ювелирное украшение": "Proudly and admiringly inspecting the sparkling handcrafted jewelry they are wearing",
    "Замечает, что любимое ювелирное украшение полностью исчерпало лунный заряд и требует подзарядки": "Noticing that their favorite jewelry has completely depleted its lunar charge and needs recharging",
    "Ощущает мощные защитные вибрации и прилив мистической энергии от надетого заряженного самоцвета": "Feeling powerful protective vibrations and a surge of mystical energy from their charged crystal jewelry",
    # SP20 Social exact
    "С искренним восхищением любуется изящным авторским ювелирным украшением перед": "Genuinely admiring exquisite handcrafted jewelry to",
    "С замиранием сердца делает предложение руки и сердца уникальным кольцом с ограненным вручную самоцветом для": "Breathlessly proposing with a unique handcrafted crystal ring to",
    "С воодушевлением обсуждает магические вибрации, лунную зарядку и целебные свойства кристаллов с": "Enthusiastically discussing magical vibrations, moonlight charging, and healing crystal properties with",
    "С гордостью хвастается виртуозной огранкой редчайшего драгоценного камня перед": "Proudly bragging about the masterwork cut of a rare gemstone to",
    "С теплом и заботой дарит заряженный под лунным светом защитный кристальный амулет для": "Warmly and caringly gifting a moonlight-charged protective crystal talisman to",
    "С беспокойством предупреждает об иссякающей магической энергии заряженного самоцвета для": "Anxiously warning about depleting magical energy of the charged gemstone to",
    # Base Game Emergencies & Objects exact
    "Сбивает пламя и тушит горящего сима из огнетушителя": "Beating down flames and extinguishing a burning Sim with a fire extinguisher",
    "Отважно тушит пламя пожара из огнетушителя": "Bravely extinguishing the flames of a fire with a fire extinguisher",
    "В панике вызывает пожарных по телефону, сообщая о возгорании": "Panickingly calling the fire department to report a fire",
    "В панике мечется и кричит от ужаса перед разгоревшимся пожаром": "Panicking and screaming in terror at the raging fire",
    "Кормит хищное растение-корову (Проглотис Людоедию) свежим куском мяса": "Feeding the carnivorous Cowplant (Laganaphyllis Simnovorii) a fresh piece of meat",
    "Игриво дразнит и играет с растением-коровой (Проглотис Людоедией)": "Playfully teasing and playing with the Cowplant (Laganaphyllis Simnovorii)",
    "Ласково гладит челюсти и стебель растения-коровы": "Affectionately petting the jaws and stem of the Cowplant",
    "Доит растение-корову, собирая чудодейственную эссенцию жизни": "Milking the Cowplant, collecting the miraculous essence of life",
    "Пытается взять кусок пирога с языка растения-коровы, рискуя быть проглоченным": "Reaching for the cake bait from the Cowplant's tongue, risking being swallowed",
    "Очищает останки и убирает кости вокруг растения-коровы": "Clearing remains and sweeping bones around the Cowplant",
    "Взаимодействует с загадочным хищным растением-коровой (Проглотис Людоедией)": "Interacting with the mysterious carnivorous Cowplant (Laganaphyllis Simnovorii)",
    "Привязывает куклу вуду к симу, проводя тайный ритуал связи": "Binding the voodoo doll to a Sim, performing a secret connection ritual",
    "Колет куклу вуду булавкой, причиняя выбранной жертве острую боль": "Poking the voodoo doll with a needle, inflicting sharp pain on the victim",
    "Щекочет куклу вуду, вызывая приступ неудержимого смеха у жертвы": "Tickling the voodoo doll, causing a fit of uncontrollable laughter in the victim",
    "Нежно обнимает куклу вуду, передавая тепло и симпатию жертве": "Gently cuddling the voodoo doll, sending warmth and affection to the victim",
    "Окунает куклу вуду в воду, насылая сырость и дискомфорт на жертву": "Soaking the voodoo doll in water, inflicting chills and discomfort on the victim",
    "Проводит мистический ритуал с куклой вуду": "Performing a mystical ritual with the voodoo doll",
    "Встряхивает куб будущего и с волнением вопрошает о своей судьбе": "Shaking the Future Cube and anxiously asking about destiny",
    "Увлеченно мнет комок глины в руках, вылепливая забавную фигурку": "Enthusiastically molding a clay blob in their hands, sculpting a figurine",
    "Оплачивает счета за коммунальные услуги через почтовый ящик": "Paying household utility bills through the mailbox",
    "Проверяет почтовый ящик в ожидании свежих писем и посылок": "Checking the mailbox for incoming letters and packages",
    "Опускает в почтовый ящик письмо или посылку для отправки": "Dropping a letter or package into the mailbox for delivery",
    "Тайно подглядывает за соседями через окуляр телескопа": "Secretly spying on neighbors through the telescope eyepiece",
    "Сканирует ночной небосвод в телескоп в поисках внеземной жизни": "Scanning the night sky through the telescope in search of alien life",

    # Social Milestones
    "Предлагает начать встречаться и стать парой для": "Asking to be boyfriend/girlfriend to",
    "Интересуется семейным положением у": "Asking if single to",
    "Признаётся в романтической измене перед": "Confessing romantic infidelity to",
    "Предлагает съехаться и жить вместе для": "Asking to move in together with",
    "Предлагает стать лучшими друзьями для": "Asking to be best friends with",
    "Выражает искренние соболезнования и поддерживает": "Expressing sincere condolences to",
    "Обсуждает желание завести детей и расширить семью с": "Discussing expanding family with",
    "Жалуется на работу и начальника для": "Complaining about work and boss to",
    "Хвастается своими успехами перед": "Bragging about achievements to",
    "Играет и проводит время в домике на дереве": "Hanging out and playing inside the treehouse",
    "Играет и учится на детском планшете": "Playing learning games on the kid's tablet",
    "Играет на органе": "Playing the pipe organ",
    "Упражняется в игре на органе": "Practicing the pipe organ",
    "Играет мрачную замогильную музыку на органе": "Playing haunting music on the pipe organ",
    "Играет торжественную органную музыку": "Playing grand music on the pipe organ",
    "Играет драматическую музыку для кино на органе": "Playing dramatic cinema music on the pipe organ",
    "Сочиняет произведение на органе": "Composing music on the pipe organ",
    "Идёт играть на органе": "Heading to play the pipe organ",
    "Идёт работать за микроскопом": "Heading to work at the scientific microscope",

    # Microscope
    "Изучает срез растения под микроскопом": "Examining a plant sample under the microscope",
    "Изучает микроструктуру окаменелости под микроскопом": "Examining a fossil specimen under the microscope",
    "Исследует кристалл и кристаллическую структуру под микроскопом": "Examining a crystal structure under the microscope",
    "Анализирует препарат / образец под микроскопом": "Analyzing a specimen / sample under the microscope",
    "Улучшает и настраивает научный микроскоп": "Upgrading and fine-tuning the scientific microscope",
    "Работает за научным микроскопом (исследует микромир)": "Working at the scientific microscope (exploring the microscopic world)",
    "Работает за научным микроскопом": "Working at the scientific microscope",

    # Radio & Music Stations
    "Слушает альтернативный рок / инди по радио": "Listening to alternative / indie rock on the radio",
    "Слушает хэви-метал / тяжёлый рок по радио": "Listening to heavy metal on the radio",
    "Слушает рок-музыку по радио": "Listening to rock music on the radio",
    "Слушает поп-музыку по радио": "Listening to pop music on the radio",
    "Слушает японский поп (S-Pop) по радио": "Listening to Japanese pop (S-Pop) on the radio",
    "Слушает молодёжный тин-поп по радио": "Listening to teen pop on the radio",
    "Слушает классическую музыку по радио": "Listening to classical music on the radio",
    "Слушает музыку эпохи барокко по радио": "Listening to baroque music on the radio",
    "Слушает блюз по радио": "Listening to blues on the radio",
    "Слушает джаз по радио": "Listening to jazz on the radio",
    "Слушает электронную музыку (EDM) по радио": "Listening to electronic music (EDM) on the radio",
    "Слушает хип-хоп / рэп по радио": "Listening to hip-hop / rap on the radio",
    "Слушает жуткую готическую музыку по радио": "Listening to spooky music on the radio",
    "Слушает латиноамериканскую музыку по радио": "Listening to Latin music on the radio",
    "Слушает островные ритмы / регги по радио": "Listening to island / reggae music on the radio",
    "Слушает кантри-музыку по радио": "Listening to country music on the radio",
    "Слушает карнавальную музыку по радио": "Listening to carnival music on the radio",
    "Слушает музыку для концентрации по радио": "Listening to focus music on the radio",
    "Слушает акустические авторские песни по радио": "Listening to acoustic singer-songwriter songs on the radio",
    "Слушает романтическую музыку по радио": "Listening to romance music on the radio",
    "Слушает ретро-хиты по радио": "Listening to retro hits on the radio",
    "Слушает диско-музыку по радио": "Listening to disco music on the radio",
    "Слушает детские песенки по радио": "Listening to kids songs on the radio",
    "Слушает колыбельную музыку по радио": "Listening to lullabies on the radio",
    "Слушает новогоднюю праздничную музыку по радио": "Listening to holiday music on the radio",
    "Слушает летние дачные мотивы по радио": "Listening to summer backyard music on the radio",
    "Слушает этническую музыку мира по радио": "Listening to world music on the radio",
    "Слушает деревенские народные мотивы по радио": "Listening to cottagecore folk music on the radio",
    "Слушает музыку по радио": "Listening to music on the radio",
    "Слушает музыку по радио / стереосистеме": "Listening to music on the radio / stereo",
    "Слушает музыку в наушниках": "Listening to music on earbuds",
    "Слушает рок-музыку в наушниках": "Listening to rock music on earbuds",
    "Слушает поп-музыку в наушниках": "Listening to pop music on earbuds",
    "Слушает классическую музыку в наушниках": "Listening to classical music on earbuds",
    "Слушает электронную музыку (EDM) в наушниках": "Listening to electronic music (EDM) on earbuds",
    "Слушает хип-хоп / рэп в наушниках": "Listening to hip-hop / rap on earbuds",
    "Слушает музыку для концентрации в наушниках": "Listening to focus music on earbuds",
    "Играет с большой мягкой игрушкой": "Playing with a giant plush toy",
    "Играет с детскими игрушками / погремушкой": "Playing with baby toys / rattle",
    "Идет по улице / прогуливается по району": "Walking down the street / strolling in the neighborhood",
    "Идёт в туалет": "Heading to the toilet",
    "Идёт делать домашнее задание": "Heading to do homework",
    "Идёт делать уборку": "Heading to clean up",
    "Идёт за компьютер": "Heading to the computer",
    "Идёт играть на музыкальном инструменте": "Heading to play an instrument",
    "Идёт к мольберту рисовать картину": "Heading to easel to paint",
    "Идёт мыть ванну": "Heading to clean the bathtub",
    "Идёт мыть душевую кабину": "Heading to clean the shower",
    "Идёт на кухню готовить еду": "Heading to the kitchen to cook",
    "Идёт на тренировку": "Heading to work out",
    "Идёт налить напиток": "Heading to get a drink",
    "Идёт по своим делам": "Heading about their business",
    "Идёт по своим делам / перемещается": "Going about their business / walking somewhere",
    "Идёт поесть / перекусить": "Heading to have a bite to eat",
    "Идёт прилечь и вздремнуть": "Heading to lie down for a nap",
    "Идёт принимать бодрящий душ": "Heading to take an energizing shower",
    "Идёт принимать ванну": "Heading to take a bath",
    "Идёт принимать горячий парной душ": "Heading to take a hot steamy shower",
    "Идёт принимать душ": "Heading to take a shower",
    "Идёт смотреть телевизор": "Heading to watch TV",
    "Идёт спать в кровать": "Heading to bed to sleep",
    "Идёт читать книгу": "Heading to read a book",
    "Изучает воду и рябь у рыбного места": "Examining the water and ripples at a fishing spot",
    "Изучает и рассматривает древнюю окаменелость": "Examining an ancient fossil specimen",
    "Изучает и рассматривает найденный кристалл (минерал)": "Examining a newly discovered mineral crystal",
    "Изучает воспитательные методы на компьютере": "Researching parenting methods on computer",
    "Изучает воспитательные методы": "Researching parenting methods",
    "Изучает советы для садоводов и агрономов в сети": "Researching gardening tips online",
    "Ищет фитнес-программы и советы по тренировкам в сети": "Researching fitness programs and workout tips online",
    "Ищет кулинарные рецепты и секреты шеф-поваров в интернете": "Researching recipes and cooking tips online",
    "Изучает историю мирового искусства и живописи в сети": "Researching art history online",
    "Изучает рецепты коктейлей и напитков в интернете": "Researching cocktail recipes and mixology online",
    "Изучает музыкальные уроки и табулатуры в сети": "Studying music lessons and tabs online",
    "Изучает котировки акций и финансовые новости": "Researching stock prices and financial news",
    "Изучает научные архивы и проводит исследование": "Researching scientific archives online",
    "Изучает ночное звездное небо в телескоп": "Gazing at the night stars through telescope",
    "Изучает обучающие материалы в интернете": "Studying tutorial guides online",
    "Изучает упавший космический метеорит": "Examining a fallen cosmic meteorite",
    "Изучает химический элемент / металл": "Analyzing a chemical element / metal sample",
    "Исследует генеалогическое древо семьи": "Researching family genealogy tree",
    "Ищет друга по переписке в интернете": "Looking for penpals online",
    "Ищет и выманивает лягушек из трухлявого бревна": "Luring and hunting frogs out of a hollow log",
    "Ищет и ловит лягушек на природе (в траве и укрытиях)": "Searching for and catching wild frogs in nature",
    "Ищет и ловит лягушек у водоема": "Searching for and catching frogs near the pond",
    "Ищет пару и флиртует на сайте знакомств": "Browsing and flirting on online dating site",
    "Ищет правду о вселенной в телескоп": "Searching for truth about the universe through telescope",
    "Ищет работу и просматривает вакансии на бирже труда": "Searching job postings on job board",
    "Катается с детской горки": "Sliding down the playground slide",
    "Качается на качелях": "Swinging high on the swings",
    "Качается на силовом тренажере": "Working out on the weight machine",
    "Колотит мягкую игрушку, вымещая злость": "Hitting a stuffed animal, venting out anger",
    "Кормит грудью": "Breastfeeding",
    "Кормит грудью ребенка": "Breastfeeding the baby",
    "Кормит детским пюре в высоком стульчике": "Feeding baby purée in high chair",
    "Кормит из бутылочки": "Bottle-feeding baby",
    "Кормит ребенка из бутылочки": "Bottle-feeding the baby",
    "Крепко обнимает любимую мягкую игрушку": "Tightly hugging favorite stuffed animal",
    "Кувыркается в сухом бассейне с шариками": "Tumbling and diving in a ball pit",
    "Кувыркается и катается на спине по полу от удовольствия": "Rolling on back on the floor in pure joy",
    "Купается в теплой детской ванночке с пенкой и брызгается водой": "Splashing happily in a warm sudsy baby bath",
    "Кушает вкусное угощение от": "Eating a tasty treat from",
    "Кушает грудное молочко у": "Nursing from",
    "Кушает детское питание / пюре": "Eating baby food / purée",
    "Кушает детское пюре с ложечки у": "Eating baby purée fed with a spoon by",
    "Лазает и кувыркается на турниках (рукоходе)": "Climbing and swinging on monkey bars",
    "Лежит в люльке": "Lying quietly in the bassinet",
    "Лежит и отдыхает в кровати": "Lying in bed relaxing",
    "Лежит на животике (упражнение Tummy Time, тренирует шею и мышцы)": "Lying on tummy (doing Tummy Time, strengthening neck and muscles)",
    "Лежит на развивающем игровом коврике и трогает подвесные игрушки": "Lying on playmat batting at dangling toys",
    "Лежит на траве и любуется облаками": "Lying on the grass, daydreaming and cloudgazing",
    "Листает детскую книжку с яркими картинками": "Flipping through a picture book with bright illustrations",
    "Листает ленту новостей в социальной сети": "Scrolling through social media feed",
    "Любуется ночным небом и звездами": "Gazing peacefully at the night sky and stars",
    "Любуется своим обнажённым телом перед зеркалом": "Admiring their nude body in the mirror",
    "Любуется скульптурой": "Admiring an art sculpture",
    "Любуется собой в зеркале": "Admiring self in the mirror",
    "Мастерит на столярном станке": "Crafting woodwork at the woodworking table",
    "Меняет подгузник для": "Changing diaper for",
    "Меняет подгузник ребенку": "Changing baby's diaper",
    "Миксует треки за DJ-пультом": "Mixing music tracks at the DJ booth",
    "Моет ванну": "Scrubbing and cleaning the bathtub",
    "Моет душевую кабину": "Cleaning the shower stall",
    "Моет и чистит раковину": "Cleaning and scrubbing the sink",
    "Моет и чистит унитаз": "Cleaning and scrubbing the toilet",
    "Моет руки с мылом в раковине": "Washing hands with soap at the sink",
    "Наблюдает за сексом / подглядывает за интимной близостью": "Watching / voyeuristically peeping on others having sex",
    "Обновляет статус на странице в соцсети": "Updating social media status",
    "Обтирается губкой у раковины": "Taking a sponge bath at the sink",
    "Общается в онлайн-чате за компьютером": "Chatting in online chatroom on computer",
    "Общается и пишет посты на форуме": "Posting on online forums",
    "Общается с другом по переписке": "Chatting with penpal online",
    "Общается с монстром под кроватью / прячется от монстра": "Talking to / hiding from the scary monster under the bed",
    "Оголяет и демонстрирует грудь (эксгибиционизм)": "Flashing bare breasts (exhibitionism)",
    "Оголяет и демонстрирует интимную зону (вагину)": "Flashing intimate private parts (exhibitionism)",
    "Оголяет и демонстрирует пенис": "Exposing penis (flashing/exhibitionism)",
    "Оголяет и показывает ягодицы / попу (эксгибиционизм)": "Flashing bare buttocks / mooning (exhibitionism)",
    "Отвечает на комментарии подписчиков в соцсетях": "Replying to follower comments on social media",
    "Отдыхает у костра / жарит зефир на огне": "Relaxing by campfire / roasting marshmallows",
    "Отправляет образец в Геологический совет": "Mailing mineral sample to the Geo Council",
    "Отправляет рукопись книги в издательство": "Submitting book manuscript to publisher",
    "Оформляет выход на пенсию онлайн": "Filing for retirement online",
    "Оформляет доставку продуктов на дом": "Ordering grocery delivery online",
    "Оформляет увольнение с работы через интернет": "Filing resignation from job online",
    "Оформляет усыновление питомца онлайн": "Filing online adoption for a pet",
    "Переписывается в онлайн-чате": "Messaging in online chat",
    "Печет блинчики": "Flipping pancakes",
    "Печет вафли": "Baking waffles",
    "Печет печенье": "Baking cookies",
    "Печет торт / выпечку": "Baking a cake / pastry",
    "Пишет биографию / мемуары на компьютере": "Writing biography / memoirs on computer",
    "Пишет детективный роман на компьютере": "Writing a mystery novel on computer",
    "Пишет детскую сказку на компьютере": "Writing a children's story on computer",
    "Пишет журналистскую статью / расследование": "Writing investigative journalism article",
    "Пишет заметку в свой личный блог": "Writing a post for personal blog",
    "Пишет и отправляет электронное письмо (e-mail)": "Writing and sending an email",
    "Пишет книгу / роман на компьютере": "Writing a book / novel on computer",
    "Пишет курсовую работу / диплом на компьютере": "Writing term paper / thesis on computer",
    "Пишет любовное письмо на компьютере": "Writing a love letter on computer",
    "Пишет любовный роман на компьютере": "Writing a romance novel on computer",
    "Пишет научно-популярную книгу": "Writing a non-fiction book on computer",
    "Пишет научно-фантастический роман (Sci-Fi)": "Writing a sci-fi novel on computer",
    "Пишет письмо другу по переписке": "Writing a letter to penpal",
    "Пишет плагин / скрипт для сервиса": "Writing a software plugin / script",
    "Пишет программный код по фриланс-заказу": "Coding a freelance programming gig",
    "Пишет рассказ на компьютере": "Writing a short story on computer",
    "Пишет сокровенные мысли в личный тайный дневник": "Writing private thoughts in personal secret journal",
    "Пишет сценарий для фильма на компьютере": "Writing a screenplay on computer",
    "Пишет театральную пьесу на компьютере": "Writing a theater play on computer",
    "Пишет текст / статью на компьютере": "Writing an article / text on computer",
    "Пишет фэнтези-роман на компьютере": "Writing a fantasy novel on computer",
    "Плачет, уткнувшись в мягкую игрушку": "Crying softly into a stuffed animal for comfort",
    "Подает документы на усыновление ребенка через интернет": "Filing online adoption paperwork for a child",
    "Подбадривает себя перед зеркалом": "Giving self a pep talk in front of mirror",
    "Подглядывает в окно за происходящим в доме (вуайеризм)": "Peeping through the window at occupants inside (voyeurism)",
    "Подглядывает в чужое окно и мастурбирует": "Peeping through someone's window and masturbating",
    "Подделывает объяснительную записку на компьютере": "Forging an excuse note on computer",
    "Подстригает и формирует крону дерева бонсай": "Pruning and trimming a bonsai tree",
    "Покупает детали для улучшения техники": "Purchasing upgrade parts online",
    "Покупает книги в интернет-магазине": "Buying books online",
    "Покупает магические ингредиенты и зелья онлайн": "Purchasing magic ingredients and potions online",
    "Покупает одежду в интернет-магазине": "Shopping for clothes online",
    "Ползает по полу / исследует комнату": "Crawling across the floor, curiously exploring the room",
    "Пользуется подгузником (ходит под себя в подгузник)": "Using diaper (filling diaper)",
    "Практикуется в программировании и написании кода": "Practicing computer programming and coding",
    "Принимает бодрящий прохладный душ": "Taking an invigorating cool shower",
    "Принимает вдохновляющий душ и размышляет": "Taking an inspiring shower and pondering",
    "Принимает горячий парной душ": "Taking a hot steamy shower",
    "Принимает грязевую ванну": "Taking a relaxing mud bath",
    "Принимает душ вместе с партнёром": "Taking a shower together with partner",
    "Принимает пищу (ест)": "Eating a meal",
    "Принимает расслабляющую ванну с пеной": "Taking a soothing bubble bath",
    "Прихорашивается перед зеркалом": "Grooming and freshening up in front of mirror",
    "Проверяет ответы от друзей по переписке": "Checking penpal replies",
    "Проверяет электронную почту": "Checking email inbox",
    "Проводит научные опыты за детским лабораторным столиком": "Conducting fun science experiments at children's chemistry lab table",
    "Программирует собственную видеоигру": "Programming a custom video game",
    "Прогуливается по улице / идёт куда-то": "Strolling down the street / walking somewhere",
    "Прочищает засор в унитазе": "Unclogging / plunging the toilet",
    "Прыгает через скакалку": "Skipping rope enthusiastically",
    "Пытается перевернуться со спинки на животик": "Trying hard to roll over from back to tummy",
    "Пьет воду": "Drinking water",
    "Пьет воду из-под крана": "Drinking water directly from the tap",
    "Пьет горячий кофе": "Drinking hot coffee",
    "Пьет коктейль": "Sipping a cocktail",
    "Пьет напиток": "Enjoying a beverage",
    "Пьет сок": "Drinking juice",
    "Пьет чай": "Drinking warm tea",
    "Работает удаленно из дома за компьютером": "Working remotely from home on computer",
    "Разглядывает фотографию в рамке": "Gazing fondly at a framed photograph",
    "Разговаривает и делится секретами с мягкой игрушкой": "Chatting and confiding secrets to a stuffed toy",
    "Разрабатывает мобильное приложение": "Developing a mobile app",
    "Рассматривает и оценивает картину / предмет искусства": "Critiquing and appreciating an artwork painting",
    "Рассматривает картины и произведения искусства в сети": "Viewing artwork and paintings online",
    "Рассматривает лягушку из коллекции": "Examining a frog specimen from collection",
    "Рассматривает пойманную лягушку в террариуме": "Observing a caught frog in a terrarium",
    "Ремонтирует сломанный предмет": "Repairing a broken object",
    "Репетирует актерскую игру перед зеркалом": "Rehearsing acting in front of the mirror",
    "Репетирует речь перед зеркалом": "Practicing a speech in front of the mirror",
    "Рисует детские рисунки / занимается творчеством за столиком": "Drawing colorful kid drawings at the activity table",
    "Рыбачит / ловит рыбу удочкой у воды": "Fishing with a rod by the water",
    "Рыбачит на морском побережье / в океане": "Fishing along the ocean coastline",
    "Рыбачит с наживкой (пытается поймать редкую рыбу)": "Fishing with bait, trying to catch rare fish",
    "Рыбачит у пруда с удочкой": "Fishing at the pond with a rod",
    "Рыбачит, вылавливая все подряд": "Fishing continuously, casting line into the water",
    "С любопытством изучает незнакомый предмет («Что это?»)": "Curiously examining an unfamiliar object ('What is that?')",
    "С любопытством наблюдает за происходящим вокруг": "Curiously watching everything happening around",
    "С любопытством разглядывает устроенный на полу беспорядок": "Curiously inspecting a messy spill on the floor",
    "С радостным визгом рушит башню из кубиков": "Giggling gleefully while knocking down a block tower",
    "Серфит по сайтам в интернете в поисках интересного": "Surfing the web for interesting content",
    "Сидит в социальной сети (проверяет страницу)": "Browsing social network profile",
    "Сидит на диване / стуле и отдыхает": "Sitting on sofa/chair relaxing",
    "Сидит на ручках у взрослого / в слинге": "Being held in adult's arms / baby carrier",
    "Скрещивает лягушек из своей коллекции": "Breeding frogs from personal collection",
    "Слушает музыку онлайн за компьютером": "Listening to music online on computer",
    "Слушает подкаст за компьютером": "Listening to a podcast on computer",
    "Смотрит боевик по ТВ": "Watching an action movie on TV",
    "Смотрит в телескоп / обсерваторию": "Peering through the telescope / observatory",
    "Смотрит вестерны по ТВ": "Watching westerns on TV",
    "Смотрит детектив / триллер по ТВ": "Watching mystery / thriller on TV",
    "Смотрит детский канал («Детский») по ТВ": "Watching Kids TV Channel",
    "Смотрит детский канал «Игого» по ТВ": "Watching 'Horsing Around' kids channel on TV",
    "Смотрит детский канал «Маленькие гении» по ТВ": "Watching 'Little Geniuses' kids channel on TV",
    "Смотрит забавные видеоролики и мемы в интернете": "Watching funny videos and memes online",
    "Смотрит канал «Гражданская политика» по ТВ": "Watching 'Civic Policy' channel on TV",
    "Смотрит канал «Гражданские права» по ТВ": "Watching 'Civic Policy' channel on TV",
    "Смотрит канал «Классика» по ТВ": "Watching 'Classics' channel on TV",
    "Смотрит канал «Мировая культура» по ТВ": "Watching 'World Culture' channel on TV",
    "Смотрит канал «Планета ужасов» по ТВ": "Watching 'Horror Planet' channel on TV",
    "Смотрит канал «Ситком ТВ»": "Watching 'Sitcom TV' channel",
    "Смотрит комедию / юмористическое шоу по ТВ": "Watching comedy / humorous show on TV",
    "Смотрит кукольный театр по ТВ": "Watching puppet theater on TV",
    "Смотрит кулинарную передачу по ТВ": "Watching a cooking show on TV",
    "Смотрит мультфильмы по ТВ": "Watching cartoons on TV",
    "Смотрит мыльную оперу по ТВ": "Watching a soap opera on TV",
    "Смотрит на крутящийся мобиль над кроваткой и слушает колыбельную": "Watching the spinning crib mobile and listening to lullaby",
    "Смотрит новости по ТВ": "Watching the news on TV",
    "Смотрит передачу «Интерьер мечты» по ТВ": "Watching 'Dream Home Design' show on TV",
    "Смотрит передачу «Сим-политика» по ТВ": "Watching 'Sim Politics' on TV",
    "Смотрит помехи по ТВ": "Watching TV static",
    "Смотрит порно на компьютере": "Watching porn on the computer",
    "Смотрит порно по телевизору": "Watching porn on television",
    "Смотрит порно по телевизору и мастурбирует": "Watching porn on TV and masturbating",
    "Смотрит приватный танец стриптизёрши": "Watching a private lap dance from stripper",
    "Смотрит прогноз погоды по ТВ": "Watching weather forecast on TV",
    "Смотрит реалити-шоу про свидания по ТВ": "Watching a dating reality show on TV",
    "Смотрит романтические программы / мелодраму по ТВ": "Watching romance shows / drama on TV",
    "Смотрит сайты в интернете за компьютером": "Browsing websites on computer",
    "Смотрит спортивный канал по ТВ": "Watching sports channel on TV",
    "Смотрит ток-шоу по ТВ": "Watching a talk show on TV",
    "Смотрит фантастику по ТВ": "Watching sci-fi on TV",
    "Смотрит фильм «Алмазы для симов» по ТВ": "Watching movie 'Diamonds are for Sims' on TV",
    "Смотрит фильм «Буйные пороки» по ТВ": "Watching movie 'Roaring Vices' on TV",
    "Смотрит фильм «Вестерн» по ТВ": "Watching Western movie on TV",
    "Смотрит фильм «Возвращение блудного пса» по ТВ": "Watching movie 'Return of the Lost Dog' on TV",
    "Смотрит фильм «Зловещие симы» по ТВ": "Watching movie 'Evil Sims' on TV",
    "Смотрит фильм «Зубрилы из колледжа» по ТВ": "Watching movie 'College Crammers' on TV",
    "Смотрит фильм «Полуночная резня 3» по ТВ": "Watching movie 'Midnight Massacre 3' on TV",
    "Смотрит фильм «Приключения в симуляторе ракеты» по ТВ": "Watching movie 'Adventures in the Rocket Simulator' on TV",
    "Смотрит фильм «Сестрицы Клямзи» по ТВ": "Watching movie 'The Clumsy Sisters' on TV",
    "Смотрит фильм «Симмануэль» по ТВ": "Watching movie 'Simmanuelle' on TV",
    "Смотрит фильм «Супердетки. Гибель головного мозга» по ТВ": "Watching movie 'Superkids: Cortex Collapse' on TV",
    "Смотрит фильм по ТВ": "Watching a movie on television",
    "Смотрит фитнес-тренировку по ТВ": "Watching a fitness workout on TV",
    "Смотрится в зеркало": "Looking in the mirror",
    "Собирает школьный научный проект (макет вулкана / ракету / робота)": "Building a school science project (volcano / rocket / robot model)",
    "Создает компьютерный вирус": "Creating a computer virus",
    "Создает моды для видеоигры": "Creating game mods",
    "Составляет и заполняет рабочие отчеты": "Filling out work reports",
    "Сочиняет стихотворение на компьютере": "Composing poetry on computer",
    "Сочиняет шутки для стендапа на компьютере": "Composing stand-up comedy jokes on computer",
    "Спит в детской кроватке / люльке": "Sleeping peacefully in crib / bassinet",
    "Справляет нужду (писает) прямо на пол / на землю (натуризм / эксгибиционизм)": "Peeing directly on floor / ground (naturism / exhibitionism)",
    "Справляет нужду в туалете (писает / ходит в туалет)": "Using the toilet (relieving bladder / peeing)",
    "Справляет нужду стоя (писает в унитаз)": "Peeing standing up in toilet",
    "Сражается карточками космических монстров на боевой арене": "Battling Voidcritter monster cards in the battle station",
    "Строит башню / пирамидку из детских кубиков": "Stacking colorful blocks into a tower",
    "Стучит в окно, подглядывая за жильцами": "Tapping on window while peeping at residents",
    "Танцует стриптиз / приватный танец на пилоне": "Dancing a private lap / pole dance",
    "Тренирует рассказ / актерское мастерство перед зеркалом": "Practicing storytelling / acting skills in front of mirror",
    "Тренирует фразы для флирта перед зеркалом": "Practicing flirtatious pickup lines in front of mirror",
    "Троллит пользователей на форумах": "Trolling users on online forums",
    "Убирается / наводит чистоту": "Cleaning up and tidying the house",
    "Увлеченно играет в кукольном домике": "Immersed in imaginative play with the dollhouse",
    "Увлеченно играет с детскими игрушками и фигурками": "Deeply engaged playing with action figures and toys",
    "Умывает лицо прохладной водой": "Splashing face with cool water at the sink",
    "Управляет бизнесом онлайн": "Managing business operations online",
    "Успокаивается перед зеркалом": "Calming down in front of the mirror",
    "Устраивает представление в детском кукольном театре": "Putting on a creative puppet show in puppet theater",
    "Устроил бурную истерику на полу (топает ножками и кричит)": "Throwing a wild tantrum on the floor, stomping and screaming",
    "Учится сидеть на попке на полу": "Learning to sit upright on the floor",
    "Фотографирует через окно жильцов в доме": "Taking illicit photos through window of occupants inside",
    "Хрустит чипсами": "Crunching on chips",
    "Хулиганит: играет в устроенном беспорядке / возится в разлитой краске и муке": "Messing around in spilled paint and flour",
    "Хулиганит: играет с мусором / копается в мусорном ведре": "Rooting through trash / playing in garbage can",
    "Хулиганит: плескается и играет с водой в унитазе": "Splashing mischievously in toilet bowl water",
    "Хулиганит: устраивает беспорядок (разливает краску и пачкает пол)": "Making a mess (splattering paint and staining floor)",
    "Чистит зубы у раковины": "Brushing teeth at the bathroom sink",
    "Читает свежие мировые новости в онлайн-изданиях": "Reading world news online",
    "биографию / мемуары": "biography / memoirs",
    "детективный роман": "mystery novel",
    "детскую сказку / книгу для детей": "children's book / fairy tale",
    "журналистскую статью / расследование": "journalistic article / investigation",
    "короткий рассказ": "short story",
    "любовный роман": "romance novel",
    "мотивирующую книгу по саморазвитию": "self-help motivational book",
    "научно-популярную книгу (нон-фикшн)": "non-fiction book",
    "научно-фантастический роман (Sci-Fi)": "sci-fi novel",
    "практическое руководство / справочник": "practical guide / manual",
    "роман в жанре фэнтези": "fantasy novel",
    "сборник стихов / поэзию": "poetry collection",
    "сценарий для фильма": "movie screenplay",
    "театральную пьесу": "theatrical play",
    "шутки для стендап-выступления": "stand-up comedy routine",
}

DYNAMIC_ACTIVITY_PATTERNS = [
    (r"(?i)Смотрит (?:передачу|канал|программу|шоу)?\s*[«\"]([^»\"]+)[»\"](?:\s*по (?:ТВ|телевизору))?", r"Watching '\1' on TV"),
    (r"(?i)Смотрит фильм\s*[«\"]([^»\"]+)[»\"](?:\s*по (?:ТВ|телевизору))?", r"Watching movie '\1' on TV"),
    (r"(?i)Смотрит\s+(.+?)\s+по (?:ТВ|телевизору)", r"Watching \1 on TV"),
    (r"(?i)Играет в (?:игру|видеоигру)?\s*[«\"]([^»\"]+)[»\"](?:\s*на компьютере)?", r"Playing video game '\1' on computer"),
    (r"(?i)Играет в\s+(.+?)\s+на компьютере", r"Playing \1 on computer"),
    (r"(?i)Играет в\s+(.+)", r"Playing \1"),
    (r"(?i)Играет на\s+(.+)", r"Playing \1"),
    (r"(?i)Играет с\s+(.+)", r"Playing with \1"),
    (r"(?i)Пишет книгу в жанре\s*[«\"]?([^»\"]+)[»\"]?", r"Writing a \1 book"),
    (r"(?i)Пишет книгу\s*[«\"]([^»\"]+)[»\"]", r"Writing book '\1'"),
    (r"(?i)Пишет\s+(.+)", r"Writing \1"),
    (r"(?i)Читает книгу\s*[«\"]([^»\"]+)[»\"]", r"Reading book '\1'"),
    (r"(?i)Читает\s+(.+)", r"Reading \1"),
    (r"(?i)Изучает\s+(.+)", r"Studying \1"),
    (r"(?i)Рассматривает\s+(.+)", r"Examining \1"),
    (r"(?i)Любуется\s+(.+)", r"Admiring \1"),
    (r"(?i)Готовит\s+(.+)", r"Cooking \1"),
    (r"(?i)Жарит\s+(.+)", r"Grilling \1"),
    (r"(?i)Печет\s+(.+)", r"Baking \1"),
    (r"(?i)Варит\s+(.+)", r"Cooking \1"),
    (r"(?i)Заваривает\s+(.+)", r"Brewing \1"),
    (r"(?i)Ест\s+(.+)", r"Eating \1"),
    (r"(?i)Пьет\s+(.+)", r"Drinking \1"),
    (r"(?i)Моет\s+(.+)", r"Washing \1"),
    (r"(?i)Чистит\s+(.+)", r"Cleaning \1"),
    (r"(?i)Убирает\s+(.+)", r"Cleaning up \1"),
    (r"(?i)Ремонтирует\s+(.+)", r"Repairing \1"),
    (r"(?i)Купается в\s+(.+)", r"Bathing in \1"),
    (r"(?i)Плавает в\s+(.+)", r"Swimming in \1"),
    (r"(?i)Идёт (?:в сторону|в|на|к)\s+(.+)", r"Heading to \1"),
    (r"(?i)Идет (?:в сторону|в|на|к)\s+(.+)", r"Heading to \1"),
]

WORD_LEXICON_EN = {
    "спагетти": "spaghetti",
    "пицца": "pizza",
    "пиццу": "pizza",
    "омлет": "omelet",
    "бургер": "burger",
    "салат": "salad",
    "суп": "soup",
    "стейк": "steak",
    "рыба": "fish",
    "рыбу": "fish",
    "кофе": "coffee",
    "чай": "tea",
    "вода": "water",
    "воду": "water",
    "сок": "juice",
    "коктейль": "cocktail",
    "джакузи": "hot tub / jacuzzi",
    "бассейн": "pool",
    "бассейне": "pool",
    "ванна": "bathtub",
    "ванной": "bathtub",
    "душе": "shower",
    "душ": "shower",
    "кровать": "bed",
    "кровати": "bed",
    "диван": "sofa",
    "диване": "sofa",
    "кухня": "kitchen",
    "кухне": "kitchen",
    "комната": "room",
    "комнате": "room",
    "спальня": "bedroom",
    "спальне": "bedroom",
    "гостиная": "living room",
    "гостиной": "living room",
    "сад": "garden",
    "саду": "garden",
    "двор": "yard",
    "дворе": "yard",
    "работа": "work",
    "работе": "work",
    "школа": "school",
    "школе": "school",
    "книга": "book",
    "книгу": "book",
    "компьютер": "computer",
    "компьютере": "computer",
    "телефон": "phone",
    "телефоне": "phone",
    "музыка": "music",
    "музыку": "music",
    "роман": "Romance",
    "фантастика": "Sci-Fi",
    "детектив": "Mystery",
    "триллер": "Thriller",
    "биография": "Biography",
}

def translate_activity_en(activity_str: str) -> str:
    """
    Translates Russian activity descriptions into natural English.
    Multi-layer architecture guarantees 100% English output with zero Russian leaks:
    1. Exact dictionary match (429+ predefined and sub-table activities)
    2. Idle & pose dictionary match
    3. Compound interaction & posture regex rules
    4. Dynamic interaction templates (TV, media, games, cooking, crafts)
    5. Word-level lexicon substitution
    6. Posture and location semantic harmonization
    7. Transliteration safety fallback for custom mod affordances
    """
    if not activity_str:
        return "Idle / Relaxing"
    act = activity_str.strip()

    heading_prefix = False
    if act.startswith("Направляется:"):
        heading_prefix = True
        act = act[len("Направляется:"):].strip()
    elif act.startswith("Направляется"):
        heading_prefix = True
        act = act[len("Направляется"):].strip()

    # Layer 1: Comprehensive Exact Match
    if act in ACTIVITY_MAP_EXACT_EN:
        res = ACTIVITY_MAP_EXACT_EN[act]
        return f"Heading: {res}" if heading_prefix else res

    # Layer 2: Generic Idles Match
    if act in GENERIC_IDLES_MAP_EN:
        res = GENERIC_IDLES_MAP_EN[act]
        return f"Heading: {res}" if heading_prefix else res

    # Layer 2.5: Dynamic Multitasking Music Match: e.g. "Мастерит на столярном станке (параллельно слушает рок-музыку по радио)"
    m_music = re.search(r'^(.*?)\s*\((?:параллельно\s+)?слушает\s+([^)]+)\)$', act, flags=re.IGNORECASE)
    if m_music:
        base_part = m_music.group(1).strip()
        music_part = m_music.group(2).strip()
        base_en = translate_activity_en(base_part)
        music_lookup = f"Слушает {music_part}"
        music_en = ACTIVITY_MAP_EXACT_EN.get(music_lookup, f"Listening to {music_part}")
        if music_en.lower().startswith("listening to "):
            music_en = music_en[13:]
        res = f"{base_en} (listening to {music_en})"
        return f"Heading: {res}" if heading_prefix else res

    m_relax_music = re.search(r'^Отдыхает и слушает\s+(.*)$', act, flags=re.IGNORECASE)
    if m_relax_music:
        music_part = m_relax_music.group(1).strip()
        music_lookup = f"Слушает {music_part}"
        music_en = ACTIVITY_MAP_EXACT_EN.get(music_lookup, f"Listening to {music_part}")
        res = f"Relaxing and {music_en[:1].lower() + music_en[1:]}"
        return f"Heading: {res}" if heading_prefix else res

    # Preserve [ИНЦЕСТ] / [TABOO] tags cleanly
    has_incest = "[инцест" in act.lower() or "[taboo" in act.lower()
    act_clean = re.sub(r'\[инцест[^\]]*\]', '', act, flags=re.IGNORECASE).strip()

    # Layer 3: Base regex patterns
    for pattern, replacement in ACTIVITY_PATTERNS_EN:
        act_clean = re.sub(pattern, replacement, act_clean)

    # Layer 4: Dynamic regex templates (TV channels, video games, books, cooking, chores)
    for pattern, replacement in DYNAMIC_ACTIVITY_PATTERNS:
        if re.search(pattern, act_clean):
            act_clean = re.sub(pattern, replacement, act_clean)
            break

    # Layer 5: Word-level lexicon replacement (with word boundary \b)
    for ru_w, en_w in sorted(WORD_LEXICON_EN.items(), key=lambda x: len(x[0]), reverse=True):
        act_clean = re.sub(r'\b' + re.escape(ru_w) + r'\b', en_w, act_clean, flags=re.IGNORECASE)

    # Layer 6: General posture & room replacements
    act_clean = act_clean.replace("сидя на", "sitting on").replace("сидит на", "sitting on")
    act_clean = act_clean.replace("кровати", "bed").replace("диване", "sofa").replace("стуле", "chair")
    act_clean = act_clean.replace("в спальне", "in bedroom").replace("в гостиной", "in living room")
    act_clean = act_clean.replace("на кухне", "in kitchen").replace("в ванной", "in bathroom")

    # Layer 7: Final transliteration safety net if any Cyrillic remains
    if any('\u0400' <= c <= '\u04FF' for c in act_clean):
        act_clean = transliterate_to_latin(act_clean)

    if has_incest:
        act_clean = f"{act_clean} [TABOO/INCEST]"
    return f"Heading: {act_clean}" if heading_prefix else act_clean



# =========================================================================
# VENUES, LOCATIONS & WORLDS (ENGLISH)
# =========================================================================

VENUE_EXACT_MAP_EN = {
    # Public Venues (indoors)
    "В баре (внутри здания)": "At the bar (indoors)",
    "В ночном клубе (внутри здания)": "At the nightclub (indoors)",
    "В лаундж-баре (внутри здания)": "At the lounge bar (indoors)",
    "В спортзале (внутри здания)": "At the gym (indoors)",
    "В библиотеке (внутри здания)": "At the library (indoors)",
    "В музее (внутри здания)": "At the museum (indoors)",
    "В кафе (внутри здания)": "At the cafe (indoors)",
    "В ресторане (внутри здания)": "At the restaurant (indoors)",
    "В спа-салоне (внутри здания)": "At the spa (indoors)",
    "В магазине / торговом центре (внутри здания)": "At the store / shopping mall (indoors)",
    "В караоке-баре (внутри здания)": "At the karaoke bar (indoors)",
    "В ветеринарной клинике (внутри здания)": "At the vet clinic (indoors)",
    "В общественном месте (внутри здания)": "At a public venue (indoors)",

    # Public Venues (outdoors)
    "В городском парке (на свежем воздухе)": "In the city park (outdoors)",
    "На пляже (на свежем воздухе)": "At the beach (outdoors)",
    "В общественном бассейне (на свежем воздухе)": "At the public pool (outdoors)",
    "В общественном месте (на свежем воздухе)": "At a public venue (outdoors)",
    "В городском парке (внутри здания)": "In the city park (indoors)",
    "На пляже (внутри здания)": "At the beach (indoors)",
    "В общественном бассейне (внутри здания)": "At the public pool (indoors)",

    # Bare Venues
    "В городском парке": "In the city park",
    "На пляже": "At the beach",
    "В общественном бассейне": "At the public pool",
    "В баре": "At the bar",
    "В ночном клубе": "At the nightclub",
    "В лаундж-баре": "At the lounge bar",
    "В спортзале": "At the gym",
    "В библиотеке": "At the library",
    "В музее": "At the museum",
    "В кафе": "At the cafe",
    "В ресторане": "At the restaurant",
    "В спа-салоне": "At the spa",
    "В магазине / торговом центре": "At the store / shopping mall",
    "В караоке-баре": "At the karaoke bar",
    "В ветеринарной клинике": "At the vet clinic",
    "В общественном месте": "At a public venue",

    # Residential & Lot Types
    "У себя дома (в помещении)": "At Home (indoors)",
    "У себя дома": "At Home",
    "Возле своего дома / во дворе": "Outside their home / in the yard",
    "В гостях (внутри чужого дома)": "Visiting someone (indoors)",
    "На улице в жилом районе / гуляет возле дома": "Outdoors in neighborhood / walking near house",
    "Находится на другом участке": "On another lot",

    # Proximity & Indoors
    "В этой же комнате (вплотную)": "In same room (right next to)",
    "Рядом на улице (вплотную)": "Outside nearby (right next to)",
    "Рядом в комнате (в паре шагов)": "Nearby in room (few steps away)",
    "Стоит рядом (в паре шагов)": "Standing nearby (few steps away)",
    "Рядом (в паре шагов)": "Nearby (few steps away)",
    "В этой же комнате": "In the same room",
    "В соседней комнате в доме": "In adjacent room indoors",
    "На улице возле дома": "Outside near the house",
    "Внутри дома": "Indoors",
    "На улице во дворе (в отдалении)": "Outside in yard (distant)",
    "На улице во дворе": "Outside in the yard",
    "В другом конце комнаты": "At the other end of the room",
    "Во дворе на улице (в нескольких метрах)": "In the yard outside (several meters away)",
    "В другой части дома": "In another part of the house",

    # Sex Furniture / Surface
    "На двуспальной кровати": "On double bed",
    "На раскладной кровати": "On murphy bed",
    "На двухместном диване": "On loveseat",
    "На кухонной тумбе": "On kitchen counter",
    "На кухонном островке": "On kitchen island",
    "На кухонной тумбе / столе": "On kitchen counter / table",
    "На обеденном столе": "On dining table",
    "На большом столе": "On large dining table",
    "На круглом столе": "On round table",
    "На столе для пикника": "On picnic table",
    "На журнальном столике": "On coffee table",
    "На письменном столе": "On desk",
    "На барной стойке": "On bar counter",
    "В душевой кабине": "In shower stall",
    "В джакузи": "In hot tub / jacuzzi",
    "В сауне": "In sauna",
    "На массажном столе": "On massage table",
    "На пляжном полотенце": "On beach towel",
    "На пледе": "On blanket",
    "На коврике для йоги": "On yoga mat",
    "Прижавшись к стене": "Pressed against the wall",
    "Прижавшись к окну": "Pressed against the window",
    "Прижавшись к двери": "Pressed against the door",
    "В компьютерном кресле": "In computer chair",
    "На шезлонге": "On lounge chair",
    "На пуфике": "On ottoman",
    "На унитазе": "On toilet",
    "В общественном туалете": "In public restroom",
    "В гробу": "In coffin",
    "На земле / траве": "On ground / grass",
    "На танцполе": "On dance floor",
    "На кровати": "On bed",
    "На диване": "On sofa",
    "В кресле": "In armchair",
    "На полу": "On the floor",
    "В душе": "In shower",
    "В ванной": "In bathtub",
    "На столе": "On table",
    "На стуле": "On chair",

    # Privacy descriptors
    "На глазах у других! (Поблизости находятся другие симы, риск быть застигнутыми / эксгибиционизм)":
        "In plain view of others! (Nearby sims watching, high risk of getting caught / exhibitionism)",
    "На открытом воздухе (на улице / во дворе, могут увидеть прохожие!)":
        "Outdoors in the open (outside / yard, passersby might see!)",
    "В доме есть другие люди (нужно быть тише, риск что кто-то войдет!)":
        "Other people are in the house (must be quiet, risk of someone walking in!)",
    "Полная приватность (в закрытой комнате, одни во всем доме)":
        "Complete privacy (locked room, alone in the entire house)",
}

GENITIVE_VENUE_MAP_EN = {
    "бара": "bar",
    "ночного клуба": "nightclub",
    "лаундж-бара": "lounge bar",
    "спортзала": "gym",
    "парка": "park",
    "библиотеки": "library",
    "музея": "museum",
    "бассейна": "pool",
    "кафе": "cafe",
    "ресторана": "restaurant",
    "спа-салона": "spa",
    "магазина": "store / mall",
    "караоке-бара": "karaoke bar",
    "пляжа": "beach",
    "ветеринарной клиники": "vet clinic",
    "заведения": "venue",
}

WORLD_NAMES_MAP_EN = {
    "Виллоу Крик": "Willow Creek",
    "Оазис Спрингс": "Oasis Springs",
    "Ньюкрест": "Newcrest",
    "Гранит Фоллз": "Granite Falls",
    "Магнолия Променейд": "Magnolia Promenade",
    "Винденбург": "Windenburg",
    "Сан Мишуно": "San Myshuno",
    "Форготн Холлоу": "Forgotten Hollow",
    "Бриндлтон Бэй": "Brindleton Bay",
    "Сельвадорада": "Selvadorada",
    "Дель-Соль-Вэлли": "Del Sol Valley",
    "Стрейнджервиль": "Strangerville",
    "Сулани": "Sulani",
    "Глиммербрук": "Glimmerbrook",
    "Волшебный мир / Глиммербрук": "The Magic Realm / Glimmerbrook",
    "Волшебный мир": "The Magic Realm",
    "Бритчестер": "Britechester",
    "Эвергрин-Харбор": "Evergreen Harbor",
    "Гора Комореби": "Mt. Komorebi",
    "Хэнфорд-он-Бэгли": "Henford-on-Bagley",
    "Тартоза": "Tartosa",
    "Мунвуд Милл": "Moonwood Mill",
    "Коппердейл": "Copperdale",
    "Сан-Секвойя": "San Sequoia",
    "Честнат-Ридж": "Chestnut Ridge",
    "Томаранг": "Tomarang",
    "Сьюдад-Энаморада": "Ciudad Enamorada",
    "Вранбург": "Ravenwood",
    "Батуу": "Batuu",
    "Сиксим": "Sixam",
    "Лесная поляна": "Sylvan Glade",
    "Забытый грот": "Forgotten Grotto",
    "Глухой лес": "Deep Woods",
    "Убежище отшельника / Глухой лес": "Deep Woods",
}

# =========================================================================
# Enhanced World & Town Descriptions (for AI immersion & atmospheric context)
# =========================================================================
WORLD_DESCRIPTIONS_EN = {
    "Willow Creek": "classic American Southern suburb: lush shaded avenues, weeping willows, New Orleans colonial mansions, bayous, and blooming magnolias",
    "Oasis Springs": "sun-drenched desert oasis in Southwestern USA: palm trees, towering cacti, red rock canyons, mid-century modern architecture, and dry arid heat",
    "Newcrest": "spacious tranquil green suburb with tidy manicured lawns, a central park, and distant modern skyline views",
    "Magnolia Promenade": "bustling waterfront shopping district: upscale boutiques, trendy retail shops, brick promenades, and scenic coastal parks",
    "Windenburg": "historic Northern/Central European town: half-timbered Tudor architecture, cobblestone alleys, ancient cliffside ruins, windmills, scenic fjords, and vibrant modern nightlife",
    "San Myshuno": "bustling multicultural metropolis: towering skyscrapers, rooftop penthouses, lively apartments, spice markets, street food stalls, cultural festivals, and colorful murals",
    "Forgotten Hollow": "grim gothic mist-covered valley: perpetual twilight, ancient crypts, decrepit Victorian mansions, gnarly dead trees, and lurking vampires",
    "Brindleton Bay": "charming New England coastal harbor: historic lighthouse, weathered cedar-shingle cottages, sandy beaches, sea mist, and a pet-loving community full of cats and dogs",
    "Selvadorada": "Latin American tropical jungle province: dense rainforest, ancient Omiscan temples and forgotten ruins, roaring waterfalls, and a lively cantina village market",
    "Del Sol Valley": "glamorous Los Angeles & Hollywood counterpart: palm-lined boulevards, Starlight Boulevard walk of fame, film studios, luxurious celebrity mansions in The Pinnacles, and bright California sun",
    "Strangerville": "mysterious retro desert canyon town: secret government laboratory, fallout shelters, paranoid conspiracies, bizarre glowing flora, and Area 51-style anomalies",
    "Sulani": "tropical Polynesian island paradise: crystal-clear turquoise lagoons, coral reefs, an active volcano, stilt beach bungalows, rich island heritage, kava culture, and ocean spirits",
    "Glimmerbrook": "secluded fairytale pine-wooded village: misty evergreens, a rushing waterfall, rocky creeks, rustic chalets, and a hidden ancient portal to the Magic Realm",
    "The Magic Realm / Glimmerbrook": "floating mystical islands drifting in cosmic twilight: purple starry void, Caster's Alley, ancient Academy of Magic, shattered flying rocks, and pure raw arcane energy",
    "The Magic Realm": "floating mystical islands drifting in cosmic twilight: purple starry void, Caster's Alley, ancient Academy of Magic, shattered flying rocks, and pure raw arcane energy",
    "Britechester": "historic British collegiate university town: stately neo-gothic University of Britechester, cutting-edge modern Foxbury Institute, scenic canals, cozy pubs, and academic student life",
    "Evergreen Harbor": "industrial Pacific Northwest harbor: repurposed shipping container homes, converted factories, community green initiatives, smokestacks, and eco-conscious urban revival",
    "Mt. Komorebi": "picturesque Japanese mountain resort: snow-covered ski slopes, natural hot springs (onsens), tranquil bamboo groves, Shinto shrines, and blooming cherry blossoms",
    "Henford-on-Bagley": "idyllic English pastoral countryside: thatched-roof stone cottages, rolling green meadows, pastures of cows and llamas, woodland foxes, rabbits, and a charming village market",
    "Tartosa": "romantic Mediterranean coastal haven: breathtaking waterfalls, olive and citrus groves, turquoise sea coves, Italian-style terra-cotta villas, and dream wedding locales",
    "Moonwood Mill": "grungy abandoned logging mill hidden in deep pine forests: rusted machinery, industrial ruins, full moons reflecting off Lake Lunvik, underground tunnels, and territorial werewolf packs",
    "Copperdale": "scenic lakeside former mining town in the American Northwest: iconic high school, carnival pier with a Ferris wheel, thrift & boba tea hangout, and quintessential teen drama",
    "San Sequoia": "breezy California coastal bay styled after San Francisco: majestic suspension bridge, scenic piers, suburban family homes, waterfront parklands, and community recreation centers",
    "Chestnut Ridge": "sweeping American Wild West frontier: vast red rock canyons, sprawling horse ranches, equestrian training parks, nectar-making cellars, and rustic cowboy heritage",
    "Tomarang": "vibrant Southeast Asian tropical valley: lively night market with rich spices, multi-unit residential apartment complexes, lush botanical sanctuary, and revered ancient temples",
    "Ciudad Enamorada": "passionate Latin American city of romance inspired by Mexico City: grand romantic parks, rendezvous motels, rooftop cocktail lounges, and Wall of Love lovers' promenades",
    "Ravenwood": "mystical Victorian netherworld-adjacent realm: ancient cemeteries, weeping willows, crypts, roaming spirits, crows, mourning bells, and ghostly afterlife intrigue",
    "Batuu": "remote outpost on the edge of the Star Wars galaxy: towering petrified spires of Black Spire Outpost, droids, Oga's Cantina, Millennium Falcon, First Order, and Resistance bases",
    "Granite Falls": "deep pine-covered national park wilderness: towering pines, rugged cliffs, campgrounds, campfires, wild herbalism, and the secret secluded cabin of the Hermit",
    "Sixam": "alien extraterrestrial world: bioluminescent floating crystals, otherworldly strange flora, glowing craters, and low-gravity alien wonders",
    "Sylvan Glade": "secret enchanted woodland clearing: massive magical tree, mystical pink-and-blue mist, shimmering waterfalls, glowing fireflies, and rare flora",
    "Forgotten Grotto": "hidden deep canyon cavern: stalactites, glowing cave moss, shimmering crystal geodes, still subterranean pools, and ancient fossils",
    "Deep Woods": "untamed deep secluded woods of Granite Falls: ancient towering canopy, overgrown hidden paths, wilderness wildlife, and the Hermit's rustic wooden cabin",
}

PET_SPECIES_MAP_EN = {
    "Кошка": "Cat",
    "Кот": "Cat",
    "Котёнок": "Kitten",
    "Котенок": "Kitten",
    "Собака": "Dog",
    "Пёс": "Dog",
    "Пес": "Dog",
    "Щенок": "Puppy",
    "Лошадь": "Horse",
    "Конь": "Horse",
    "Жеребёнок": "Foal",
    "Жеребенок": "Foal",
    "Питомец": "Pet",
}

def translate_pet_en(pet_str: str) -> str:
    """Translates pet string like 'Кошка: Барсик' -> 'Cat: Barsik'."""
    if not pet_str:
        return ""
    res = pet_str
    for ru_sp, en_sp in sorted(PET_SPECIES_MAP_EN.items(), key=lambda x: len(x[0]), reverse=True):
        if ru_sp in res:
            res = res.replace(ru_sp, en_sp)
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


def translate_location_en(loc_str: str) -> str:
    """
    Translates Sim spatial location string into English.
    Handles all public venues, outdoors/indoors modifiers, cities, rooms and privacy.
    Guarantees 100% English output with zero Cyrillic leakage.
    """
    if not loc_str:
        return "At home"
    res = loc_str.strip()

    # Exact match first
    if res in VENUE_EXACT_MAP_EN:
        return VENUE_EXACT_MAP_EN[res]

    # City/world handling "(г. Название)" or "(г. Название — описание)"
    def _rep_city(m):
        raw_inside = m.group(1).strip()
        from ai_thought_reader.config import get_experimental_flag
        enhanced = get_experimental_flag("enhanced_world_descriptions")
        if "—" in raw_inside:
            parts = raw_inside.split("—", 1)
            raw_city = parts[0].strip()
        elif " - " in raw_inside:
            parts = raw_inside.split(" - ", 1)
            raw_city = parts[0].strip()
        else:
            raw_city = raw_inside
        tr_city = WORLD_NAMES_MAP_EN.get(raw_city, raw_city)
        if enhanced:
            desc_en = WORLD_DESCRIPTIONS_EN.get(tr_city, "")
            if desc_en:
                return f"({tr_city} — {desc_en})"
        return f"({tr_city})"
    res = re.sub(r'\(г\.\s*([^)]+)\)', _rep_city, res)

    # Privacy handling "[Приватность: ...]"
    def _rep_priv(m):
        raw_priv = m.group(1).strip()
        tr_priv = VENUE_EXACT_MAP_EN.get(raw_priv, raw_priv)
        return f"[Privacy: {tr_priv}]"
    res = re.sub(r'\[Приватность:\s*([^\]]+)\]', _rep_priv, res)

    # Street near venue: "На улице возле ... / в районе"
    def _rep_street(m):
        v_gen = m.group(1).strip()
        v_en = GENITIVE_VENUE_MAP_EN.get(v_gen, v_gen)
        return f"Outdoors near the {v_en} / in the area"
    res = re.sub(r'(?i)На улице возле\s+([^/]+?)\s*/\s*в районе', _rep_street, res)

    # Replace known phrases from VENUE_EXACT_MAP_EN
    for k in sorted(VENUE_EXACT_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, VENUE_EXACT_MAP_EN[k])

    # Replace known world names if still present
    for k in sorted(WORLD_NAMES_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, WORLD_NAMES_MAP_EN[k])

    # Modifiers and rooms
    modifiers = [
        (r"(?i)\(на свежем воздухе\)", "(outdoors)"),
        (r"(?i)\(в помещении\)", "(indoors)"),
        (r"(?i)\(внутри здания\)", "(indoors)"),
        (r"(?i)\(внутри чужого дома\)", "(indoors at someone's house)"),
        (r"(?i)в гостиной|гостиная", "in living room"),
        (r"(?i)в спальне|спальня", "in bedroom"),
        (r"(?i)на кухне|кухня", "in kitchen"),
        (r"(?i)в ванной комнате|в ванной|ванная комната|ванная", "in bathroom"),
        (r"(?i)в кабинете|кабинет", "in study / office"),
        (r"(?i)в коридоре|коридор", "in hallway"),
        (r"(?i)в столовой|столовая", "in dining room"),
        (r"(?i)в детской|детская", "in nursery / kids room"),
        (r"(?i)в подвале|подвал", "in basement"),
        (r"(?i)на чердаке|чердак", "in attic"),
        (r"(?i)на балконе|балкон", "on balcony"),
        (r"(?i)на террасе|терраса", "on terrace"),
        (r"(?i)во дворе|двор|задний двор", "in yard / backyard"),
        (r"(?i)у себя дома", "At Home"),
        (r"(?i)на текущем участке", "On current lot"),
        (r"(?i)находится на другом участке", "On another lot"),
    ]
    for pattern, repl in modifiers:
        res = re.sub(pattern, repl, res)

    try:
        from ai_thought_reader.config import get_experimental_flag
        if get_experimental_flag("enhanced_world_descriptions"):
            for en_world, en_desc in WORLD_DESCRIPTIONS_EN.items():
                bare_tag = f"({en_world})"
                if bare_tag in res and f"({en_world} —" not in res:
                    res = res.replace(bare_tag, f"({en_world} — {en_desc})")
    except Exception:
        pass

    # Transliteration fallback
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)

    return res


def translate_holiday_en(holiday_str: str) -> str:
    """Translates in-game calendar holidays into English."""
    if not holiday_str:
        return ""
    h = holiday_str.strip()
    if "обычный день" in h.lower() or "нет праздника" in h.lower():
        return "Regular day (no holiday)"
    if "день рождения" in h.lower():
        h = re.sub(r'(?i)день рождения у ([^(]+)', r'Birthday for \1', h)
        h = re.sub(r'(?i)день рождения', 'Birthday', h)
        h = re.sub(r'(?i)сегодня празднует день рождения и взрослеет!?', 'is celebrating their birthday and aging up today!', h)
        h = re.sub(r'(?i)сегодня праздник взросления в семье!?', 'birthday celebration in the household today!', h)
        return h

    HOLIDAY_MAP_EN = {
        "новый год": "New Year's Eve",
        "день любви": "Love Day",
        "праздник урожая": "Harvestfest",
        "зимний праздник": "Winterfest",
        "канун нового года": "New Year's Eve",
        "день шуток": "Prank Day",
        "день пирата": "Talk Like a Pirate Day",
        "день лотереи": "Lottery Day",
        "ночь в городе": "Night on the Town",
        "день навыков": "Skill Day",
        "сезонная скидка": "Rebate Day",
        "телевизионная премьера": "TV Season Premiere",
        "день признательности соседям": "Neighborhood Brawl",
    }
    for k, v in HOLIDAY_MAP_EN.items():
        if k in h.lower():
            return v
    if any('\u0400' <= c <= '\u04FF' for c in h):
        h = transliterate_to_latin(h)
    return h


def translate_funds_en(funds_str: str) -> str:
    """Translates household funds status like '(Скромный достаток)' into English."""
    if not funds_str:
        return ""
    f = funds_str.strip()
    FUNDS_STATUS_MAP_EN = {
        "Мало денег / Бедность": "Low funds / Poor",
        "Бедная семья": "Poor household",
        "Скромный достаток": "Modest income / Working class",
        "Хороший достаток": "Comfortable / Well-off",
        "Богатая семья": "Wealthy household",
        "Богатство": "Wealthy / Affluent",
        "Богатая": "Wealthy",
        "Неизвестно": "Unknown",
    }
    for k in sorted(FUNDS_STATUS_MAP_EN.keys(), key=len, reverse=True):
        if k in f:
            f = f.replace(k, FUNDS_STATUS_MAP_EN[k])
    if any('\u0400' <= c <= '\u04FF' for c in f):
        f = transliterate_to_latin(f)
    return f


def translate_fame_en(fame_str: str) -> str:
    """Translates Get Famous fame ranks and reputation into English."""
    if not fame_str:
        return ""
    f = fame_str.strip()
    if f in FAME_MAP_EN:
        return FAME_MAP_EN[f]
    combined_fame = dict(FAME_MAP_EN)
    combined_fame.update({
        "Слава: 0 звёзд (Обычный житель / Не знаменит). Репутация: Нейтральная (обычная городская репутация)":
            "Fame: 0 Stars (Regular Citizen / Not Famous). Reputation: Neutral (Average town reputation)",
        "0 звёзд (Обычный житель / Не знаменит)": "0 Stars (Regular Citizen / Not Famous)",
        "⭐ 1 звезда — Заметный новичок (первое внимание публики)": "⭐ 1 Star — Notable Newcomer (initial public attention)",
        "⭐⭐ 2 звезды — Восходящая звезда (вспышки камер, первые фанаты)": "⭐⭐ 2 Stars — Rising Star (camera flashes, early fans)",
        "⭐⭐⭐ 3 звезды — Настоящая знаменитость (толпы поклонников, известность)": "⭐⭐⭐ 3 Stars — B-Lister (crowds of admirers, widespread recognition)",
        "⭐⭐⭐⭐ 4 звезды — Звезда мирового масштаба (огромная слава, папарацци)": "⭐⭐⭐⭐ 4 Stars — Proper Celebrity (massive fame, swarming paparazzi)",
        "⭐⭐⭐⭐⭐ 5 звёзд — Всемирная суперзвезда (культовая легенда, золотая аура славы)": "⭐⭐⭐⭐⭐ 5 Stars — Global Superstar (living legend, golden aura of fame)",
        "Ужасная (Отъявленный злодей, общественный враг)": "Atrocious (Notorious villain, public enemy)",
        "Очень плохая (Омерзительные слухи, всеобщее недоверие)": "Terrible (Nasty rumors, universal distrust)",
        "Плохая (Дурная слава)": "Bad (Poor standing)",
        "Нейтральная (Обычная городская репутация)": "Neutral (Average town reputation)",
        "Нейтральная (обычная городская репутация)": "Neutral (Average town reputation)",
        "Хорошая (Вежливый и надежный горожанин)": "Good (Polite and dependable citizen)",
        "Отличная (Всеобщее уважение и симпатия)": "Great (Widely respected and liked)",
        "Безупречная (Святой образец для подражания, кумир общества)": "Pristine (Saintly role model, beloved idol)",
        "(Отказ от славы: сим скрывается от публичности)": "(Fame disabled: sim avoids public spotlight)",
        "Слава:": "Fame:",
        "Репутация:": "Reputation:",
        "Ранг": "Rank",
        "звёзд": "Stars",
        "звезда": "Star",
        "звезды": "Stars",
        "Не прикасаться! (брезгует физическим контактом с обычными симами)": "No Touching! (disdains physical contact with ordinary sims)",
        "Изысканный вкус (требует только великолепную ресторанную еду)": "Refined Palate (demands only excellent gourmet food)",
        "Общедоступный номер (телефон разрывается от звонков фанатов)": "Public Number (phone blown up by fans)",
        "Любимец папарацци (обожает позировать перед камерами)": "Paparazzi Darling (loves posing for cameras)",
        "Одержимый фанат (рядом постоянно бродит навязчивый сталкер)": "Obsessed Stan (constantly stalked by an obsessive fan)",
        "Телефонный фанатик (постоянно уткнут в соцсети)": "Phone Fanatic (glued to social media)",
        "Тщеславие (не может оторваться от зеркала)": "Vain Street (cannot stay away from the mirror)",
        "Общение со сливками общества (общается только со знаменитостями)": "A-Lister (only socializes with fellow celebrities)",
        "Любитель сока (постоянная тяга к выпивке и бару)": "Juice Enthusiast (frequent craving for drinks and bars)",
        "Эмоциональная бомба (склонен к драматическим срывам на публике)": "Emotion Bomb (prone to dramatic public meltdowns)",
    })
    for k in sorted(combined_fame.keys(), key=len, reverse=True):
        if k in f:
            f = f.replace(k, combined_fame[k])
    if any('\u0400' <= c <= '\u04FF' for c in f):
        f = transliterate_to_latin(f)
    return f

def translate_traits_en(traits_str: str) -> str:
    """Translates comma-separated traits into clean English."""
    if not traits_str:
        return "Average personality"
    items = [t.strip() for t in traits_str.split(",") if t.strip()]
    translated = []
    for item in items:
        # Check exact trait mapping first
        if item in TRAIT_MAP_EN:
            translated.append(TRAIT_MAP_EN[item])
            continue

        # Check archetype suffix
        if "(Архетип личности" in item:
            arch_base = item.split("(Архетип личности")[0].strip()
            if arch_base in TRAIT_MAP_EN:
                translated.append(TRAIT_MAP_EN[arch_base])
                continue

        # Check suffix removal & translation
        suffix_en = ""
        base_item = item
        for sfx_ru, sfx_replacement in [
            (" (Бонус жизненной цели)", " (Aspiration Bonus)"),
            ("(Бонус жизненной цели)", " (Aspiration Bonus)"),
            (" (Награда за баллы счастья)", " (Reward Trait)"),
            ("(Награда за баллы счастья)", " (Reward Trait)"),
            (" (Черта этапа взросления)", " (Milestone Trait)"),
            ("(Черта этапа взросления)", " (Milestone Trait)"),
            (" (Черта характера)", ""),
            ("(Черта характера)", ""),
        ]:
            if base_item.endswith(sfx_ru):
                base_item = base_item[:-len(sfx_ru)].strip()
                suffix_en = sfx_replacement
                break

        if base_item in TRAIT_MAP_EN:
            translated.append(f"{TRAIT_MAP_EN[base_item]}{suffix_en}")
            continue

        # Check case-insensitive base match
        matched = False
        for k_ru, v_en in TRAIT_MAP_EN.items():
            if k_ru.lower() == base_item.lower():
                translated.append(f"{v_en}{suffix_en}")
                matched = True
                break
        if matched:
            continue

        # Substring fallback
        t_sub = translate_phrase(base_item, TRAIT_MAP_EN)
        translated.append(f"{t_sub}{suffix_en}" if suffix_en else t_sub)

    return ", ".join(translated) if translated else traits_str


def translate_motives_en(motives_str: str) -> str:
    """Translates motives string into English with zero Cyrillic leakage."""
    if not motives_str:
        return "All needs are satisfied"

    # Detect enraged werewolf tag
    is_enraged_tag = False
    clean_motives = motives_str.strip()
    if "(оборотень в ярости)" in clean_motives.lower() or "[оборотень в ярости]" in clean_motives.lower():
        is_enraged_tag = True
        clean_motives = re.sub(r'[\(\[]оборотень в ярости[\)\]]', '', clean_motives, flags=re.IGNORECASE).strip()

    if not clean_motives or clean_motives in ("Потребности в норме", "Все потребности удовлетворены"):
        res = "All needs are satisfied"
    elif clean_motives in MOTIVE_MAP_EN:
        res = MOTIVE_MAP_EN[clean_motives]
    else:
        res = clean_motives
        for k in sorted(MOTIVE_MAP_EN.keys(), key=len, reverse=True):
            if k in res:
                res = res.replace(k, MOTIVE_MAP_EN[k])
    for ru_m, en_m in [
        ("Естественная нужда", "Bladder"),
        ("Нужда", "Bladder"),
        ("Энергия", "Energy"),
        ("Голод", "Hunger"),
        ("Гигиена", "Hygiene"),
        ("Общение", "Social"),
        ("Досуг", "Fun"),
        ("Бодрое", "Rested"),
        ("Усталость", "Tired"),
        ("Сыт(а)", "Full"),
        ("Сыт", "Full"),
        ("Сыта", "Full"),
        ("Голоден", "Hungry"),
        ("Голодна", "Hungry"),
        ("Чистый", "Clean"),
        ("Чистая", "Clean"),
        ("Грязный", "Dirty"),
        ("Грязная", "Dirty"),
        ("Доволен", "Satisfied"),
        ("Довольна", "Satisfied"),
        ("Одинок", "Lonely"),
        ("Одинока", "Lonely"),
        ("Весело", "Having Fun"),
        ("Скучно", "Bored"),
        ("В норме", "Fine"),
    ]:
        res = re.sub(r'\b' + re.escape(ru_m) + r'\b', en_m, res, flags=re.IGNORECASE)
    if is_enraged_tag:
        res = f"{res} (Werewolf in rage)"
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


def translate_relationship_en(rel_str: str) -> str:
    """Translates relationship labels into English."""
    if not rel_str:
        return "Acquaintance"
    res = rel_str
    for k in sorted(RELATIONSHIP_MAP_EN.keys(), key=len, reverse=True):
        v = RELATIONSHIP_MAP_EN[k]
        if k in res:
            res = res.replace(k, v)
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


FAMILY_DETAIL_MAP_EN = {
    "Живут вместе в одном доме": "Lives together in the same household",
    "Живут вместе": "Lives together",
    "Живет отдельно": "Lives separately",
    "Живёт отдельно": "Lives separately",
    "Очень близкие и теплые отношения": "Very close and warm relationship",
    "Хорошие отношения": "Good relationship",
    "Враждебные отношения / Сильная неприязнь": "Hostile / strong dislike",
    "Напряженные отношения": "Tense / strained relationship",
    "Обычные / Нейтральные отношения": "Casual / neutral relationship",
    "Лично ещё не знакомы": "Haven't met in person yet",
    "Женский": "Female",
    "Мужской": "Male",
    "Женщина": "Female",
    "Мужчина": "Male",
    "Теплые дружеские отношения": "Warm friendly relationship",
    "Вражда / Сильная неприязнь": "Enmity / Strong dislike",
    "Соседка по дому": "Roommate (female)",
    "Сосед по дому": "Roommate (male)",
    "Новорожденный": "Newborn",
    "Младенец": "Infant",
    "Малыш": "Toddler",
    "Ребенок": "Child",
    "Подросток": "Teen",
    "Молодой": "Young Adult",
    "Взрослый": "Adult",
    "Пожилой": "Elder",
}


def translate_family_member_en(f_mem: str) -> str:
    """Translates family member entries like 'Муж: Мортимер Гот (Живут вместе в одном доме, Хорошие отношения)' -> 'Husband: Mortimer Goth (Lives together in the same household, Good relationship)'."""
    if not f_mem:
        return ""
    res = f_mem
    res = res.replace("Дружба:", "Friendship:").replace("Романтика:", "Romance:")
    res = res.replace("Дружба", "Friendship").replace("Романтика", "Romance")
    for k in sorted(FAMILY_DETAIL_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, FAMILY_DETAIL_MAP_EN[k])
    for k in sorted(RELATIONSHIP_MAP_EN.keys(), key=len, reverse=True):
        v = RELATIONSHIP_MAP_EN[k]
        if k in res:
            res = res.replace(k, v)
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


def translate_nearby_sim_en(n_sim: str) -> str:
    """Translates nearby Sim entries and roommates into natural English."""
    if not n_sim:
        return ""
    res = n_sim.strip()

    # 1. Structured tag parsing for rich nearby format:
    # "Name (Rel, Настроение: Mood, Действие: Act, Локация: Loc)"
    first_paren = res.find("(")
    if first_paren > 0 and res.endswith(")"):
        inside = res[first_paren + 1 : -1].strip()
        p_mood = inside.find(", Настроение:")
        p_act = inside.find(", Действие:")
        p_loc = inside.find(", Локация:")

        if 0 < p_mood < p_act < p_loc:
            name = res[:first_paren].strip()
            rel = inside[:p_mood].strip()
            mood = inside[p_mood + len(", Настроение:") : p_act].strip()
            act = inside[p_act + len(", Действие:") : p_loc].strip()
            loc = inside[p_loc + len(", Локация:") :].strip()

            rel_en = translate_relationship_en(rel)
            mood_en = translate_mood_en(mood)
            act_en = translate_activity_en(act)
            loc_en = translate_location_en(loc)
            return f"{name} ({rel_en}, Mood: {mood_en}, Action: {act_en}, Location: {loc_en})"

    # Enraged werewolf warnings in nearby/roommate string
    res = re.sub(r'\[ВНИМАНИЕ:\s*(?:Оборотень|Werewolf)\s*в\s*ярости!\]', '[WARNING: Werewolf in rage!]', res, flags=re.IGNORECASE)
    res = re.sub(r'\[ОПАСНОСТЬ:\s*(?:Оборотень|Werewolf)\s*в\s*ярости!\]', '[WARNING: Werewolf in rage!]', res, flags=re.IGNORECASE)
    res = re.sub(r'\[(?:Оборотень|Werewolf)\s*в\s*ярости!\]', '[Werewolf in rage!]', res, flags=re.IGNORECASE)

    # 2. General replacement fallback for other nearby/roommate formats
    res = res.replace("Отношения:", "Relationship:")
    res = res.replace("Дружба:", "Friendship:").replace("Романтика:", "Romance:")
    res = res.replace("Дружба", "Friendship").replace("Романтика", "Romance")
    res = res.replace("Настроение:", "Mood:")
    res = res.replace("Действие:", "Action:")
    res = res.replace("Локация:", "Location:")
    res = res.replace("Направляется:", "Heading:")

    # Gender translation first to prevent substring collisions like 'Муж' in 'Мужской'
    for k in ["Мужской", "Женский", "Мужчина", "Женщина"]:
        if k in res:
            res = res.replace(k, GENDER_MAP_EN.get(k, k))

    for k in sorted(FAMILY_DETAIL_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, FAMILY_DETAIL_MAP_EN[k])

    for k in sorted(RELATIONSHIP_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, RELATIONSHIP_MAP_EN[k])
    for k, v in AGE_MAP_EN.items():
        if k in res:
            res = res.replace(k, v)
    for k, v in sorted(OCCULT_FORM_MAP_EN.items(), key=lambda x: len(x[0]), reverse=True):
        if k in res:
            res = res.replace(k, v)
    if "причина смерти:" in res.lower():
        res = res.replace("Причина смерти:", "Cause of death:").replace("причина смерти:", "cause of death:")
        for k, v in sorted(GHOST_DEATH_MAP_EN.items(), key=lambda x: len(x[0]), reverse=True):
            if k in res.lower():
                idx = res.lower().find(k)
                res = res[:idx] + v + res[idx + len(k):]
    for k, v in sorted(OCCULT_MAP_EN.items(), key=lambda x: len(x[0]), reverse=True):
        if k in res:
            res = res.replace(k, v)
    for k in sorted(MOOD_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, MOOD_MAP_EN[k])

    res = translate_activity_en(res)
    res = translate_location_en(res)
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


BUFF_REASON_MAP_EN = {
    "Отличная еда": "Great food",
    "Вкусная еда": "Delicious food",
    "Отличный кофе": "Great coffee",
    "Хороший кофе": "Good coffee",
    "Чашка чая": "Cup of tea",
    "Уютная обстановка": "Cozy environment",
    "Красивый декор": "Beautiful decor",
    "Грязное окружение": "Dirty surroundings",
    "Неприятный запах": "Bad odor",
    "Одиночество": "Loneliness",
    "Усталость": "Fatigue",
    "Недосып": "Lack of sleep",
    "Скучный разговор": "Boring conversation",
    "Флирт": "Flirting",
    "Влюбленность": "Being in love",
    "Первый поцелуй": "First kiss",
    "ВуХу": "WooHoo",
    "Успех на работе": "Work success",
    "Повышение": "Promotion",
    "Поражение в споре": "Lost an argument",
    "Стыдный момент": "Embarrassing moment",
    "Отличная тренировка": "Great workout",
    "Приятная музыка": "Pleasant music",
}


def translate_mood_en(mood_str: str) -> str:
    """Translates mood including buff reason into English."""
    if not mood_str:
        return "Fine / Neutral"
    res = mood_str
    # Replace '(Причина: ...)' with '(Reason: ...)' and translate common reasons
    def _rep_reason(m):
        raw_reason = m.group(1).strip()
        tr_reason = BUFF_REASON_MAP_EN.get(raw_reason, raw_reason)
        return f"(Reason: {tr_reason})"

    res = re.sub(r'\(Причина:\s*([^)]+)\)', _rep_reason, res)
    for k in sorted(MOOD_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, MOOD_MAP_EN[k])
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


def translate_time_en(time_str: str) -> str:
    """Translates world time e.g. 'Понедельник, 14:30 (День)' -> 'Monday, 14:30 (Afternoon)'."""
    if not time_str:
        return ""
    res = time_str
    for k, v in DAYS_MAP_EN.items():
        if k in res:
            res = res.replace(k, v)
    for k, v in TIME_PERIOD_MAP_EN.items():
        if k in res:
            res = res.replace(k, v)
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


CAREER_MAP_EN = {
    "Преступник / Криминал": "Criminal",
    "Преступник": "Criminal",
    "Криминал": "Criminal",
    "Космонавт": "Astronaut",
    "Спортсмен / Атлет": "Athlete",
    "Спортсмен": "Athlete",
    "Атлет": "Athlete",
    "Athletic": "Athlete",
    "Athletic on": "Athlete",
    "athletic": "Athlete",
    "athlete": "Athlete",
    "Бизнесмен": "Business",
    "Бизнес": "Business",
    "Кулинар / Шеф-повар": "Culinary",
    "Кулинар": "Culinary",
    "Шеф-повар": "Master Chef",
    "Бармен": "Bartender",
    "Исполнитель / Комик / Музыкант": "Entertainer",
    "Исполнитель": "Entertainer",
    "Музыкант": "Musician",
    "Комик": "Comedian",
    "Художник": "Painter",
    "Тайный агент": "Secret Agent",
    "Секретный агент": "Secret Agent",
    "Агент разведки": "Diamond Agent / Intelligence",
    "Агент": "Agent",
    "IT-специалист / Программист": "Tech Guru",
    "IT-специалист": "Tech Guru",
    "Программист": "Programmer",
    "Технический специалист": "Tech Guru",
    "Писатель / Журналист": "Writer",
    "Писатель": "Writer",
    "Журналист": "Journalist",
    "Детектив": "Detective",
    "Врач": "Doctor",
    "Доктор": "Doctor",
    "Ученый": "Scientist",
    "Актер": "Actor",
    "Актриса": "Actress",
    "Военный": "Military",
    "Военнослужащий": "Military",
    "Преподаватель": "Educator",
    "Инженер": "Engineer",
    "Юрист / Адвокат": "Lawyer",
    "Юрист": "Lawyer",
    "Адвокат": "Attorney / Lawyer",
    "Эколог": "Conservationist",
    "Дизайнер интерьеров": "Interior Decorator",
    "Садовод": "Gardener",
    "Ученик (Младшая школа)": "Grade School Student",
    "Ученик (Старшая школа)": "High School Student",
    "Старшая школа": "High School Student",
    "Младшая школа": "Grade School Student",
    "Скаут": "Scout",
    "Театральный кружок": "Drama Club",
    "Няня": "Babysitter",
    "Бариста": "Barista",
    "Работник фастфуда": "Fast Food Employee",
    "Разнорабочий": "Manual Laborer",
    "Спасатель": "Lifeguard",
    "Законодатель стиля / Стилист": "Style Influencer",
    "Законодатель стиля": "Style Influencer",
    "Стилист": "Stylist",
    "Критик": "Critic",
    "Социальные сети / Блогер": "Social Media / Blogger",
    "Социальные сети": "Social Media",
    "Блогер": "Blogger",
    "Политик / Общественный деятель": "Politician",
    "Политик": "Politician",
    "Общественный деятель": "Public Figure",
    "Служащий сарариман (Офисный клерк)": "Salaryman (Office Clerk)",
    "Служащий сарариман": "Salaryman",
    "Офисный клерк": "Office Clerk",
    "Строительный инженер / Урбанист": "Civil Designer",
    "Строительный инженер": "Civil Designer",
    "Урбанист": "Urban Planner",
    "Фрилансер": "Freelancer",
    "Паранормальный сыщик": "Paranormal Investigator",
    "Рыболов": "Fisherman",
    "Водолаз": "Diver",
    "Безработный": "Unemployed",
    "Безработная": "Unemployed",
    "На пенсии": "Retired",
    "Пенсионер": "Retired",
    "Пенсионерка": "Retired",
}

ASPIRATION_MAP_EN = {
    # Wealth
    "Сказочное богатство": "Fabulously Wealthy",
    "Барон": "Mansion Baron",
    # Love
    "Родственная душа": "Soulmate",
    "Серийный романтик": "Serial Romantic",
    "Подлый партнер": "Villainous Valentine",
    "Исследователь любви": "Explorer of Love",
    # Nature
    "Куратор": "The Curator",
    "Независимый ботаник": "Freelance Botanist",
    "Рыбак-ас": "Angling Ace",
    "Сельский смотритель": "Country Caretaker",
    "Повелитель зелий": "Purveyor of Potions",
    "Любитель свежего воздуха": "Outdoor Enthusiast",
    "Куратор археологии": "Archaeology Scholar",
    "Исследователь джунглей": "Jungle Explorer",
    # Knowledge
    "Человек эпохи Возрождения": "Renaissance Sim",
    "Мозговитый чудак": "Nerd Brain",
    "Компьютерный гений": "Computer Whiz",
    "Академик": "Academic",
    "Мастер чародейства": "Spellcraft & Sorcery",
    "Чародейство": "Spellcraft & Sorcery",
    "Любознательность": "Inquisitive",
    # Creativity
    "Исключительный живописец": "Painter Extraordinaire",
    "Музыкальный талант": "Musical Genius",
    "Популярный автор": "Bestselling Author",
    "Мастер актерского мастерства": "Master Actor",
    "Искусный мастер": "Master Maker",
    # Deviance
    "Враг народа": "Public Enemy",
    "Большой бедокур": "Chief of Mischief",
    # Family
    "Большая семья": "Big Happy Family",
    "Успешная династия": "Successful Lineage",
    "Супер-родитель": "Super Parent",
    "Семья вампиров": "Vampire Family",
    # Food
    "Шеф-повар": "Master Chef",
    "Лучший бармен": "Master Mixologist",
    "Любитель жареного сыра": "Grilled Cheese",
    # Athletic
    "Культурист": "Bodybuilder",
    "Любитель экстрима": "Extreme Sports Enthusiast",
    "Чемпион по верховой езде": "Championship Rider",
    # Popularity
    "Шутник": "Joke Star",
    "Мировой друг": "Friend of the World",
    "Главарь вечеринок": "Party Animal",
    "Лидер стаи": "Leader of the Pack",
    "Хороший вампир": "Good Vampire",
    "Повелитель вампиров": "Master Vampire",
    "Местный авторитет": "Neighborhood Confidante",
    "Источник сплетен": "Neighborhood Confidante",
    "Друг животных": "Friend of the Animals",
    "Коренной горожанин": "City Native",
    "Мировая знаменитость": "World-Famous Celebrity",
    # For Rent (EP15)
    "Взыскательный жилец": "Discerning Dweller",
    "Пятизвездочный владелец": "Five-Star Property Owner",
    "Искатель тайн": "Seeker of Secrets",
    # Packs
    "Эко-новатор": "Eco Innovator",
    "Пляжная жизнь": "Beach Life",
    "Мастер нектара": "Master Nectar Maker",
    "Специалист по уходу за собой": "Self-Care Specialist",
    "Внутреннее умиротворение": "Inner Peace",
    "Дзен-гуру": "Zen Guru",
    "Тайна Стрейнджервиля": "StrangerVille Mystery",
    "Жизнь на максимум": "Live Fast",
    "Королева драмы": "Drama Llama",
    "Целеустремленность": "Goal Oriented",
    "Своя компания": "Admired Icon",
    "Душа компании": "Relatable",
    "Экскурсовод по горе Комореби": "Mount Komorebi Sightseer",
    "Посвящение в оборотни": "Werewolf Initiation",
    "Одинокий волк": "Lone Wolf",
    "Посланник оборотней": "Emissary of the Collective",
    "Хищник": "Apex Predator",
    "Исцеление от оборотничества": "Cure for Lycanthropy",
    "Не выбрана": "None selected",
    # Tuning string fallbacks (case-insensitive keys)
    "discerningdweller": "Discerning Dweller",
    "discerning dweller": "Discerning Dweller",
    "multiunit discerningdweller": "Discerning Dweller",
    "popularity multiunit discerningdweller": "Discerning Dweller",
    "propertymanager": "Five-Star Property Owner",
    "property manager": "Five-Star Property Owner",
    "multiunit propertymanager": "Five-Star Property Owner",
    "fivesecrets": "Seeker of Secrets",
    "five secrets": "Seeker of Secrets",
    "multiunit fivesecrets": "Seeker of Secrets",
    "neighborhoodconfidante": "Neighborhood Confidante",
    "neighborhood confidante": "Neighborhood Confidante",
}


def translate_single_career_entry_en(entry: str) -> str:
    """Translates a single career entry e.g. 'Военный — Должность: «Капрал» (Уровень 3: младший командир)'."""
    if not entry or not entry.strip():
        return ""
    ent = entry.strip()

    try:
        from ai_thought_reader.career_data_en import CAREER_MAP_EN as C_MAP, CAREER_JOB_MAP_EN, CAREER_DESC_MAP_EN
    except Exception:
        C_MAP = CAREER_MAP_EN
        CAREER_JOB_MAP_EN = {}
        CAREER_DESC_MAP_EN = {}

    m = re.match(
        r'^(.*?)\s*[\u2014\u2013-]\s*Должность:\s*[«"“\'](.*?)[»"”\']\s*\(Уровень\s*(\d+)(?::\s*([^)]*))?\)',
        ent,
        flags=re.IGNORECASE
    )
    if m:
        c_title = re.sub(r'(?i)\s+on$', '', m.group(1)).strip()
        j_title = m.group(2).strip()
        c_lvl = m.group(3).strip()
        j_desc = (m.group(4) or "").strip()

        c_title_en = C_MAP.get(c_title, c_title)
        j_title_en = CAREER_JOB_MAP_EN.get(j_title, j_title)
        j_desc_en = CAREER_DESC_MAP_EN.get(j_desc, j_desc) if j_desc else ""

        if j_desc_en:
            res = f'{c_title_en} — Position: "{j_title_en}" (Level {c_lvl}: {j_desc_en})'
        else:
            res = f'{c_title_en} — Position: "{j_title_en}" (Level {c_lvl})'
        if any('\u0400' <= c <= '\u04FF' for c in res):
            res = transliterate_to_latin(res)
        return res

    m_simple = re.match(r'^(.*?)\s*\(Уровень\s*(\d+)\)', ent, flags=re.IGNORECASE)
    if m_simple:
        c_title = re.sub(r'(?i)\s+on$', '', m_simple.group(1)).strip()
        c_lvl = m_simple.group(2).strip()
        c_title_en = C_MAP.get(c_title, c_title)
        res = f"{c_title_en} (Level {c_lvl})"
        if any('\u0400' <= c <= '\u04FF' for c in res):
            res = transliterate_to_latin(res)
        return res

    res = ent
    res = re.sub(r'(?i)должность:\s*', 'Position: ', res)
    res = re.sub(r'(?i)уровень\s*(\d+)', r'Level \1', res)
    for k in sorted(CAREER_JOB_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, CAREER_JOB_MAP_EN[k])
    for k in sorted(CAREER_DESC_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, CAREER_DESC_MAP_EN[k])
    for k in sorted(C_MAP.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, C_MAP[k])
    for k in sorted(CAREER_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, CAREER_MAP_EN[k])
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res


def translate_career_en(career_str: str) -> str:
    """Translates career title, job position and level into English with zero Cyrillic leakage."""
    if not career_str or career_str.strip() in ("Безработный", "Безработная"):
        return "Unemployed"
    parts = [p.strip() for p in career_str.split(";") if p.strip()]
    if not parts:
        return "Unemployed"
    translated_parts = [translate_single_career_entry_en(p) for p in parts]
    return "; ".join(translated_parts)


def translate_aspiration_en(asp_str: str) -> str:
    """Translates aspiration name into English."""
    if not asp_str:
        return ""
    res = asp_str
    for k in sorted(ASPIRATION_MAP_EN.keys(), key=len, reverse=True):
        if k in res:
            res = res.replace(k, ASPIRATION_MAP_EN[k])
            return res
    clean_lower = res.strip().lower()
    for k in sorted(ASPIRATION_MAP_EN.keys(), key=len, reverse=True):
        if k.lower() in clean_lower:
            return ASPIRATION_MAP_EN[k]
    if any('\u0400' <= c <= '\u04FF' for c in res):
        res = transliterate_to_latin(res)
    return res



# =========================================================================
# 11. FULL PROMPT BUILDERS (ENGLISH)
# =========================================================================

def build_sim_prompt_en(
    full_name: str,
    age_raw: str,
    gender_raw: str,
    sim_race_ru: str,
    world_time_ru: str,
    season_ru: str,
    weather_ru: str,
    holiday_ru: str,
    clothing_info_ru: str,
    nudity_state_ru: str,
    activity_ru: str,
    mood_ru: str,
    location_ru: str,
    motives_str_ru: str,
    traits_str_ru: str,
    career_ru: str,
    aspiration_ru: str,
    funds_ru: str,
    pregnancy_ru: str,
    fame_info_ru: str,
    custom_lore: str,
    family_members_ru: List[str],
    nearby_sims_ru: List[str],
    roommates_ru: List[str],
    household_pets_ru: List[str],
    sex_info: Optional[dict] = None,
    social_info: Optional[dict] = None,
    is_active_intimate_incest: bool = False,
    flags_func=None,
    sim_id: Optional[int] = None,
) -> str:
    """
    Constructs 100% native, error-free English context prompt.
    Follows strictly the exact ordering and semantic structure required by the mod.
    """
    get_flag = flags_func if flags_func else (lambda f: True)

    age_en = AGE_MAP_EN.get(age_raw, "Adult")
    gender_en = GENDER_MAP_EN.get(gender_raw, "Unspecified")
    race_en = translate_occult_en(sim_race_ru)

    world_time_en = translate_time_en(world_time_ru)
    season_en = SEASONS_MAP_EN.get(season_ru, season_ru)
    weather_en = translate_phrase(weather_ru, WEATHER_MAP_EN)
    clothing_en = translate_phrase(clothing_info_ru, CLOTHING_MAP_EN)
    nudity_en = translate_phrase(nudity_state_ru, NUDITY_MAP_EN)

    activity_en = translate_activity_en(activity_ru)
    mood_en = translate_mood_en(mood_ru)
    location_en = translate_location_en(location_ru)
    motives_en = translate_motives_en(motives_str_ru)
    traits_en = translate_traits_en(traits_str_ru)

    pregnancy_en = translate_pregnancy_en(pregnancy_ru)
    fame_en = translate_phrase(fame_info_ru, FAME_MAP_EN)

    lines = [
        "Character Information:",
        f"- Name: {full_name}",
        f"- Age & Gender: {age_en}, {gender_en}",
        f"- Race: {race_en}",
    ]

    if get_flag("world_time") and world_time_en:
        lines.append(f"- In-Game Time: {world_time_en}")
    if get_flag("weather"):
        if season_en:
            lines.append(f"- Season: {season_en}")
        if weather_en:
            lines.append(f"- Weather: {weather_en}")
    if get_flag("world_time") and holiday_ru:
        lines.append(f"- Holiday: {translate_holiday_en(holiday_ru)}")

    if get_flag("clothing"):
        lines.append(f"- Outfit: {clothing_en}")
        if nudity_en:
            lines.append(f"- Degree of Nudity: {nudity_en}")

    if sex_info:
        action_en = translate_activity_en(sex_info.get("action", ""))
        lines.append(f"- Current Action: {action_en}")
        partner_label = "Partner"
        partners_en = translate_relationship_en(str(sex_info.get("partners", "")))
        lines.append(f"- {partner_label}: {partners_en}")
        if sex_info.get("group_type"):
            lines.append(f"- Intimacy Format: {sex_info['group_type']}")
        if sex_info.get("pose"):
            lines.append(f"- Intimacy Pose / Type: {translate_activity_en(str(sex_info['pose']))}")
        if sex_info.get("location_and_privacy"):
            lines.append(f"- Location & Privacy: {translate_location_en(str(sex_info['location_and_privacy']))}")
    else:
        lines.append(f"- Current Action: {activity_en}")

    # Social Dialog block
    if social_info and get_flag("social"):
        targets = social_info.get("targets", [])
        if not social_info.get("is_group", False) and targets:
            tgt = targets[0]
            tgt_age_gender = translate_nearby_sim_en(str(tgt.get("age_gender", "")))
            tgt_race = translate_occult_en(tgt.get("race", ""))
            tgt_mood = translate_mood_en(str(tgt.get("mood", "")))
            tgt_rel = translate_relationship_en(str(tgt.get("relationships", "")))
            lines.append(f"- Conversation Partner: {tgt['name']} ({tgt_age_gender}, {tgt_race})")
            lines.append(f"- Partner's Mood: {tgt_mood}")
            if tgt.get("career"):
                lines.append(f"- Partner's Career: {translate_career_en(str(tgt['career']))}")
            if social_info.get("style"):
                lines.append(f"- Conversation Style / Tone: {translate_social_style_en(str(social_info['style']))}")
            lines.append(f"- Relationship with Partner: {tgt_rel}")
        elif social_info.get("is_group", False) and targets:
            if social_info.get("style"):
                lines.append(f"- Conversation Style / Tone: {translate_social_style_en(str(social_info['style']))}")
            lines.append("- Conversation Partners (Group Chat Members):")
            for tgt in targets:
                t_ag = translate_nearby_sim_en(str(tgt.get("age_gender", "")))
                t_rc = translate_occult_en(tgt.get("race", ""))
                t_md = translate_mood_en(str(tgt.get("mood", "")))
                t_cr = translate_career_en(str(tgt.get("career", ""))) if tgt.get("career") else ""
                t_cr_str = f", Career: {t_cr}" if t_cr else ""
                t_rl = translate_relationship_en(str(tgt.get("relationships", "")))
                lines.append(f"  • {tgt['name']} ({t_ag}, {t_rc}, Mood: {t_md}{t_cr_str}, Relationship: {t_rl})")

    # Nearby Sims block
    if get_flag("nearby"):
        if nearby_sims_ru:
            lines.append("- Nearby Sims:")
            if any("оборотень в ярости" in str(ns).lower() or "werewolf in rage" in str(ns).lower() for ns in nearby_sims_ru):
                lines.append("  ⚠️ WARNING: An enraged / rampaging werewolf is nearby!")
            for n_sim in nearby_sims_ru:
                lines.append(f"  • {translate_nearby_sim_en(n_sim)}")
        else:
            lines.append("- Nearby Sims: Nobody nearby (currently alone)")

    # Family & Relatives block
    if get_flag("family"):
        if family_members_ru:
            lines.append("- Family, Partner & Relatives:")
            for f_mem in family_members_ru:
                lines.append(f"  • {translate_family_member_en(f_mem)}")
        else:
            lines.append("- Family & Personal Life: Single (no partner or known relatives)")

    # Household Roommates block
    if get_flag("roommates"):
        if roommates_ru:
            lines.append("- Household Roommates (living together, non-relatives):")
            for rm in roommates_ru:
                lines.append(f"  • {translate_nearby_sim_en(rm)}")
        else:
            lines.append("- Household Roommates: No roommates (lives alone or only with family)")

    # Household Pets block
    if get_flag("pets"):
        if household_pets_ru:
            p_cnt = len(household_pets_ru)
            p_word = "pet" if p_cnt == 1 else "pets"
            tr_pets = [translate_pet_en(p) for p in household_pets_ru]
            lines.append(f"- Household Pets: {p_cnt} {p_word} — " + ", ".join(tr_pets))
        else:
            lines.append("- Household Pets: No pets in household")

    lines.append(f"- Current Mood: {mood_en}")

    if get_flag("location"):
        lines.append(f"- Current Location: {location_en}")

    lines.append(f"- Needs & Motives: {motives_en}")
    lines.append(f"- Personality Traits: {traits_en}")

    if custom_lore:
        lines.append(f"- Additional Lore (Personal Backstory): {custom_lore}")

    if get_flag("pregnancy") and pregnancy_en:
        lines.append(f"- Pregnancy: {pregnancy_en}")

    if get_flag("fame") and fame_info_ru:
        lines.append(f"- Fame & Reputation: {translate_fame_en(fame_info_ru)}")

    if get_flag("career") and career_ru:
        lines.append(f"- Career & Profession: {translate_career_en(career_ru)}")

    if get_flag("aspiration") and aspiration_ru:
        lines.append(f"- Aspiration & Life Goal: {translate_aspiration_en(aspiration_ru)}")

    if get_flag("funds") and funds_ru:
        lines.append(f"- Household Budget: {translate_funds_en(funds_ru)}")

    if get_flag("memory") and sim_id:
        try:
            from ai_social_pc.memory_manager import format_memories_for_sim_thoughts
            mem_text = format_memories_for_sim_thoughts(sim_id, is_en=True)
            if mem_text:
                lines.append(f"- {mem_text}")
        except Exception:
            pass

    lines.append("")

    # Dynamic Pregnancy Guidance
    if get_flag("pregnancy"):
        is_preg_active = any(k in pregnancy_ru.lower() for k in ["беременн", "триместр", "схватк", "роды"]) and "не беремен" not in pregnancy_ru.lower()
        if is_preg_active:
            if "инопланет" in pregnancy_ru.lower() or "похищен" in pregnancy_ru.lower() or "alien" in pregnancy_en.lower():
                lines.append(
                    "IMPORTANT (Alien Pregnancy): The character is carrying an alien baby after being abducted by UFO! Reflect this extraordinary, eerie, or shocking state in their thoughts — strange sensations in the abdomen, fear and awe of the unknown extraterrestrial lifeform within, memories of the abduction."
                )
            else:
                lines.append(
                    "IMPORTANT (Pregnancy / Expecting a Child): Reflect the pregnancy state in the character's thoughts — physical sensations (baby kicks, heaviness, nausea, contractions), emotional anticipation, joy, anxiety, or preparing for parenthood."
                )
            lines.append("")

    # Dynamic Fame Guidance
    if get_flag("fame"):
        if any(s in fame_info_ru for s in ["⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]):
            lines.append(
                "IMPORTANT (Celebrity Status & Stardom): The character is a well-known celebrity. Reflect the weight of popularity, paparazzi, public attention, stardom quirks, or fatigue from the limelight."
            )
            lines.append("")

    # Dynamic Age-Specific Rule
    age_rule_en = AGE_INSTRUCTION_RULES_EN.get(age_raw, "")
    if age_rule_en:
        lines.append(age_rule_en)
        lines.append("")

    # Dynamic Classic Insane Trait Guidance (Experimental Flag)
    try:
        from ai_thought_reader.config import get_experimental_flag
        has_classic_insane = get_experimental_flag("classic_insane_trait")
    except Exception:
        has_classic_insane = False

    if has_classic_insane and (any(k in traits_en.lower() for k in ["erratic", "insane"]) or any(k in traits_str_ru.lower() for k in ["чудаковатый", "безумный", "erratic", "insane"])):
        lines.append(
            "IMPORTANT (Classic Insane Trait Behavior): The character's 'Erratic' trait operates in classic 'Insane' mode (from TS3 and early TS4). "
            "Their thoughts should be genuinely chaotic, eccentric, and unhinged: paranoid suspicions, talking to inanimate objects (furniture, appliances, walls), bizarre conspiracy theories, sudden erratic leaps of logic, wild emotional swings, and absurd stream of consciousness. Make their internal monologue unpredictably chaotic and surreal!"
        )
        lines.append("")

    # Incest / Taboo dynamic guidance
    if is_active_intimate_incest and get_flag("incest"):
        lines.append(
            "IMPORTANT (Forbidden Romance / Taboo Bond): The character is currently in a romantic or intimate interaction with their blood/close relative (marked [TABOO/INCEST]). "
            "Reflect the psychological complexity of a forbidden connection: awareness of the taboo, secret attraction, guilt, awkwardness, thrill, or overwhelming passion from the forbidden nature of the moment."
        )
        lines.append("")

    # Dynamic Intoxication / Substance Guidance (Basemental Drugs Moods & Highs)
    mood_lower_en = mood_en.lower()
    if any(k in mood_lower_en for k in ["stoned", "high", "baked", "greened out"]):
        lines.append(
            "IMPORTANT (Cannabis High / Stoned): The character is under the influence of cannabis. "
            "Their thoughts should be mellow, slightly hazy, reflecting munchies, spaced-out philosophy, humor, or relaxed sluggishness."
        )
        lines.append("")
    elif any(k in mood_lower_en for k in ["drunk", "tipsy", "wasted", "smashed", "intoxicated"]):
        lines.append(
            "IMPORTANT (Alcohol Intoxication): The character is drunk. "
            "Their thoughts should be uninhibited, impulsive, overly emotional, loud, or careless, reflecting lowered social filters and drunken bravado."
        )
        lines.append("")
    elif any(k in mood_lower_en for k in ["stimulated", "wired", "hyper-stimulated"]):
        lines.append(
            "IMPORTANT (Stimulant State): The character is on stimulants. "
            "Their thoughts are racing at breakneck speed, filled with hyper-confidence, restless adrenaline, hyperactivity, and intense urgency."
        )
        lines.append("")
    elif any(k in mood_lower_en for k in ["sedated", "down", "nodding off", "numb"]):
        lines.append(
            "IMPORTANT (Sedated State): The character is under the effect of sedatives or downers. "
            "Their thoughts are slow, heavy, detached, and hazy, struggling to focus or drifting toward sleep."
        )
        lines.append("")

    lines.append(
        f"Formulate a short (1-2 sentences) spontaneous internal monologue for {full_name} at this exact second. Remember: the thought must sound direct, vivid, without introductory cliches like 'I am thinking about...'!"
    )

    # Global Latin Sanity Guarantee: ensure 0 Cyrillic characters leak anywhere in system context
    clean_lines = []
    for line in lines:
        if line.startswith("- Additional Lore (Personal Backstory):"):
            clean_lines.append(line)
        elif any('\u0400' <= c <= '\u04FF' for c in line):
            clean_lines.append(transliterate_to_latin(line))
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines)


def build_pet_prompt_en(
    first_name: str,
    species_name_ru: str,
    age_gender_ru: str,
    activity_ru: str,
    mood_ru: str,
    motives_ru: str,
    traits_ru: str,
    location_ru: str,
    owners_ru: List[str],
    other_pets_ru: List[str],
    nearby_ru: List[str],
    world_time_ru: str,
    season_ru: str,
    weather_ru: str,
    custom_lore: str = "",
    flags_func=None,
) -> str:
    """Builds English pet prompt for Dogs and Cats."""
    get_flag = flags_func if flags_func else (lambda f: True)

    species_en = "Dog" if "собак" in species_name_ru.lower() or "пес" in species_name_ru.lower() else ("Cat" if "кош" in species_name_ru.lower() or "кот" in species_name_ru.lower() else "Pet")
    age_gender_en = translate_nearby_sim_en(age_gender_ru)
    activity_en = translate_activity_en(activity_ru)
    mood_en = translate_mood_en(mood_ru)
    location_en = translate_location_en(location_ru)
    world_time_en = translate_time_en(world_time_ru)
    season_en = SEASONS_MAP_EN.get(season_ru, season_ru)
    weather_en = translate_phrase(weather_ru, WEATHER_MAP_EN)

    lines = [
        f"Pet Information ({species_en}):",
        f"- Name: {first_name}",
        f"- Species: {species_en}",
        f"- Age & Gender: {age_gender_en}",
    ]
    if get_flag("world_time") and world_time_en:
        lines.append(f"- In-Game Time: {world_time_en}")
    if get_flag("weather"):
        if season_en:
            lines.append(f"- Season: {season_en}")
        if weather_en:
            lines.append(f"- Weather: {weather_en}")
    lines.append(f"- Current Action: {activity_en}")
    lines.append(f"- Current Mood: {mood_en}")
    if motives_ru:
        lines.append(f"- Needs & Motives: {translate_motives_en(motives_ru)}")
    if traits_ru:
        lines.append(f"- Habits & Traits: {traits_ru}")

    if custom_lore:
        lines.append(f"- Additional Pet Lore: {custom_lore}")

    if get_flag("location"):
        lines.append(f"- Current Location: {location_en}")

    if get_flag("pets"):
        if owners_ru:
            tr_owners = [o.replace(" (Хозяин)", " (Owner)").replace("(Хозяин)", "(Owner)") for o in owners_ru]
            tr_owners = [transliterate_to_latin(o) if any('\u0400' <= c <= '\u04FF' for c in o) else o for o in tr_owners]
            lines.append("- Owners (family members): " + ", ".join(tr_owners))
        else:
            lines.append("- Owners: Stray / No permanent owner")
        if other_pets_ru:
            tr_other_pets = [translate_pet_en(p) for p in other_pets_ru]
            lines.append("- Other Pets in Household: " + ", ".join(tr_other_pets))

    if get_flag("nearby"):
        if nearby_ru:
            lines.append("- Nearby Sims:")
            for n in nearby_ru:
                lines.append(f"  • {translate_nearby_sim_en(n)}")
        else:
            lines.append("- Nearby Sims: Nobody nearby")

    lines.append("")
    lines.append(
        f"Formulate a short (1-2 sentences) spontaneous thought of the pet {first_name} ({species_en}) at this exact second in the first person (\"I\"). Reflect its current action, animal sounds, behavioral habits, and sincere emotions!"
    )
    # Global Latin Sanity Guarantee
    clean_lines = []
    for line in lines:
        if line.startswith("- Additional Pet Lore:"):
            clean_lines.append(line)
        elif any('\u0400' <= c <= '\u04FF' for c in line):
            clean_lines.append(transliterate_to_latin(line))
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines)
