# -*- coding: utf-8 -*-
"""
Synapse Director Testing & Diagnostic Suite (Лаборатория тестов Режиссёра)
Dedicated testing module: independent trigger evaluation, simulation scanning,
and manual execution for autonomous living dialogues.
"""

from typing import Dict, List, Tuple, Any, Optional

try:
    import services
    from date_and_time import DateAndTime
except ImportError:
    services = None
    DateAndTime = None

from ai_social_pc.logger import log, log_exception


# =========================================================================
# TRIGGER DEFINITIONS REGISTRY
# =========================================================================

DIRECTOR_TRIGGERS = [
    {
        "id": "cooking_together",
        "name_ru": "Готовка на кухне",
        "name_en": "Cooking Together",
        "category": "МГНОВЕННОЕ",
        "prio": 86,
        "requirements_ru": "Один сим готовит на кухне, второй рядом (в пределах 6м/комнаты)."
    },
    {
        "id": "burnt_food",
        "name_ru": "Сгоревшая еда",
        "name_en": "Burnt Food",
        "category": "МГНОВЕННОЕ",
        "prio": 95,
        "requirements_ru": "На лоте сгоревшая/испорченная еда или дым, два сима рядом."
    },
    {
        "id": "broken_object",
        "name_ru": "Поломка сантехники / техники",
        "name_en": "Broken Object / Plumbing",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "requirements_ru": "Сломанный прибор, сантехника или лужа рядом (до 8м), два сима рядом."
    },
    {
        "id": "dirty_dish_trash",
        "name_ru": "Грязь и испорченная еда",
        "name_en": "Dirty Objects / Spoiled Food",
        "category": "МГНОВЕННОЕ",
        "prio": 87,
        "requirements_ru": "Грязная сантехника/плита/тумбы, тарелка с испорченной едой или мусор на полу рядом (до 8м)."
    },
    {
        "id": "late_night_awake",
        "name_ru": "Ребёнок не спит ночью (23:00-05:00)",
        "name_en": "Child Awake Late Night",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "requirements_ru": "Ночь (23:00-05:00), родитель и ребёнок (младенец/тоддлер/ребёнок/подросток) бодрствуют в одной комнате."
    },
    {
        "id": "work_return",
        "name_ru": "Возвращение со смены / школы",
        "name_en": "Work / School Return",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "requirements_ru": "Сим вернулся с работы/школы (окно 60 мин), встречает домашнего в комнате или на улице/у дома (до 8.5м)."
    },
    {
        "id": "ww_post_intimacy",
        "name_ru": "После секса / вуху (WickedWhims & WooHoo)",
        "name_en": "Post-WooHoo / Intimacy",
        "category": "МГНОВЕННОЕ",
        "prio": 87,
        "requirements_ru": "Прошло <30 сим-минут после секса/вуху (на любом предмете, на полу или в кровати). Любой уровень отношений."
    },
    {
        "id": "ww_accidental_nudity",
        "name_ru": "Случайная нагота (голый сим)",
        "name_en": "Accidental Nudity",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "requirements_ru": "Один сим полностью голый (WickedWhims или ваниль), второй одет, находятся в одной комнате. Любой возраст."
    },
    {
        "id": "negative_mood_reaction",
        "name_ru": "Реакция на плохое настроение (Гнев, Грусть, Стресс, Стыд и др.)",
        "name_en": "Negative Mood Reaction",
        "category": "МГНОВЕННОЕ",
        "prio": 84,
        "requirements_ru": "У одного из симов негативное настроение (Грусть, Злость, Стресс, Смущение, Страх, Дискомфорт, Ошалелость). 1 раз в день на сима."
    },
    {
        "id": "eating_together",
        "name_ru": "Совместный обед / ужин",
        "name_en": "Eating Together",
        "category": "МГНОВЕННОЕ",
        "prio": 89,
        "requirements_ru": "Оба сима одновременно кушают в одной комнате (Золотой момент семьи)."
    },
    {
        "id": "watching_tv_together",
        "name_ru": "Просмотр ТВ на диване",
        "name_en": "Watching TV Together",
        "category": "ФОНОВОЕ",
        "prio": 78,
        "requirements_ru": "Оба сима одновременно смотрят телевизор в одной комнате."
    },
    {
        "id": "pc_siblings_share",
        "name_ru": "Очередь за ПК (Сиблинги)",
        "name_en": "PC Sharing (Siblings)",
        "category": "ФОНОВОЕ",
        "prio": 79,
        "requirements_ru": "Братья/сёстры (дети/подростки), один сидит за ПК, второй в комнате."
    },
    {
        "id": "homework_not_done",
        "name_ru": "Не сделана домашка",
        "name_en": "Homework Not Done",
        "category": "ФОНОВОЕ",
        "prio": 77,
        "requirements_ru": "Вечер (16:00-21:30), у школьника не сделана домашка, родитель рядом."
    },
    {
        "id": "homework_in_progress",
        "name_ru": "Домашка в процессе",
        "name_en": "Homework in Progress",
        "category": "ФОНОВОЕ",
        "prio": 78,
        "mode": "HOME",
        "requirements_ru": "Школьник делает уроки; родитель помогает/рядом или сиблинг делает вместе/рядом. 1 раз в день.",
    },
    {
        "id": "homework_done",
        "name_ru": "Домашка сделана (готова)",
        "name_en": "Homework Done",
        "category": "ФОНОВОЕ",
        "prio": 76,
        "mode": "HOME",
        "requirements_ru": "Школьник закончил домашку; родитель или сиблинг рядом. 1 раз в день.",
    },
    {
        "id": "bedtime_pillow_talk",
        "name_ru": "Ночной разговор перед сном (21:00-02:00)",
        "name_en": "Bedtime / Late Night Talk",
        "category": "ФОНОВОЕ",
        "prio": 65,
        "requirements_ru": "Поздний вечер/ночь (21:00-02:00). Любые два сима бодрствуют в одной комнате перед сном. 1 раз в день на пару."
    },
    {
        "id": "morning_coffee",
        "name_ru": "Утреннее приветствие / пробуждение (06:00-10:00)",
        "name_en": "Morning Greeting / Wake-up",
        "category": "ФОНОВОЕ",
        "prio": 65,
        "requirements_ru": "Утро (06:00-10:00). Любые два сима бодрствуют и встретились утром в доме. 1 раз в день на пару."
    },
    {
        "id": "truant_school_work",
        "name_ru": "Прогул школы / смены (Школа / Работа)",
        "name_en": "Truancy (School/Work)",
        "category": "МГНОВЕННОЕ",
        "prio": 90,
        "requirements_ru": "Школьник или работник прогуливает текущую смену/уроки и остался дома в присутствии другого сима. 1 раз в день на каждого сима."
    },
    {
        "id": "witness_death",
        "name_ru": "Смерть персонажа / Костлявая Смерть",
        "name_en": "Witness Death / Grim Reaper",
        "category": "МГНОВЕННОЕ",
        "prio": 98,
        "requirements_ru": "На участке смерть: если осталось 2+ сима — скорбят вместе (прио 98); если 1 сим — диалог со Смертью о пощаде (прио 99). Указывает родство погибшего (если родственник). 1 раз в день."
    },
    {
        "id": "fire_hazard",
        "name_ru": "Пожар на участке",
        "name_en": "Fire Hazard",
        "category": "МГНОВЕННОЕ",
        "prio": 96,
        "requirements_ru": "На участке вспыхнул огонь, симы паникуют или тушат пожар. 1 раз в день."
    },
    {
        "id": "sim_in_labor",
        "name_ru": "Схватки и роды (Чрезвычайная ситуация)",
        "name_en": "Childbirth / Labor",
        "category": "МГНОВЕННОЕ",
        "prio": 97,
        "requirements_ru": "У беременного персонажа (симки или сима) начались схватки и роды (мудлет «Пора!»), второй сим рядом. 1 раз в день."
    },
    {
        "id": "caught_cheating",
        "name_ru": "Застигнутая измена",
        "name_en": "Caught Cheating",
        "category": "МГНОВЕННОЕ",
        "prio": 93,
        "requirements_ru": "Один сим флиртовал, поцеловал или обнял другого персонажа на глазах постоянного партнёра (окно 8 сим-минут). 1 раз в день."
    },
    {
        "id": "witnessed_cheating",
        "name_ru": "Свидетель застаёт измену",
        "name_en": "Witnessed Cheating",
        "category": "МГНОВЕННОЕ",
        "prio": 92,
        "requirements_ru": "Свидетель (ребёнок, родственник или друг) застает персонажа в романтике (поцелуй, объятие, флирт) с третьим лицом втайне от партнёра. 1 раз в день."
    },
    {
        "id": "walk_in_intimacy",
        "name_ru": "Неожиданный вход в интимную сцену",
        "name_en": "Walk-in On Intimacy",
        "category": "МГНОВЕННОЕ",
        "prio": 94,
        "requirements_ru": "Сим неожиданно застает приватную или интимную сцену (вуху, уединение, соло, пара или группа 3+). 1 раз в день."
    },
    {
        "id": "electrocuted_repair",
        "name_ru": "Удар током при ремонте техники",
        "name_en": "Electrocuted Repair",
        "category": "МГНОВЕННОЕ",
        "prio": 89,
        "requirements_ru": "Сим получил разряд тока при починке техники (ошалелый/опаленный), второй сим рядом. 1 раз в день."
    },
    {
        "id": "paid_bills",
        "name_ru": "Оплата счетов за дом",
        "name_en": "Household Bills Paid",
        "category": "МГНОВЕННОЕ",
        "prio": 86,
        "requirements_ru": "Сим оплатил счета за дом (окно 60 мин) и встретил члена семьи от подростка и старше. 1 раз в день."
    },
    {
        "id": "gardening_together",
        "name_ru": "Садоводство и растения",
        "name_en": "Gardening & Plants",
        "category": "ФОНОВОЕ",
        "prio": 75,
        "requirements_ru": "Один сим ухаживает за растениями (полив, сбор урожая, прополка), второй находится рядом (до 12м). 1 раз в день."
    },
    {
        "id": "creative_painting",
        "name_ru": "Творчество у мольберта",
        "name_en": "Easel Painting",
        "category": "ФОНОВОЕ",
        "prio": 74,
        "requirements_ru": "Один сим пишет картину на мольберте/планшете, второй находится рядом в комнате. 1 раз в день."
    },
    {
        "id": "music_performance",
        "name_ru": "Музицирование (Пианино / Гитара / Скрипка)",
        "name_en": "Music Performance",
        "category": "ФОНОВОЕ",
        "prio": 75,
        "requirements_ru": "Один сим играет на музыкальном инструменте (пианино, гитара, скрипка, орган), второй слушает в комнате. 1 раз в день."
    },
    {
        "id": "fitness_workout",
        "name_ru": "Домашняя тренировка / Спорт",
        "name_en": "Fitness Workout",
        "category": "ФОНОВОЕ",
        "prio": 73,
        "requirements_ru": "Один сим активно тренируется (беговая дорожка, пресс, отжимания, тренажер, йога), второй рядом в комнате. 1 раз в день."
    },
    {
        "id": "table_games",
        "name_ru": "Настольные игры / Шахматы",
        "name_en": "Table Games & Chess",
        "category": "ФОНОВОЕ",
        "prio": 76,
        "requirements_ru": "Два сима играют в шахматы, карты или настольную игру за одним столом. 1 раз в день на пару."
    },
    {
        "id": "pet_care",
        "name_ru": "Забота о домашнем питомце",
        "name_en": "Pet Care & Play",
        "category": "ФОНОВОЕ",
        "prio": 74,
        "requirements_ru": "Один сим ухаживает за кошкой/собакой (купает, расчесывает, дрессирует, играет), второй находится рядом в комнате. 1 раз в день."
    },
    {
        "id": "ambient_living_room",
        "name_ru": "Фоновая беседа в комнате",
        "name_en": "Ambient Co-Presence",
        "category": "ФОНОВОЕ",
        "prio": 70,
        "requirements_ru": "Два сима в одной комнате занимаются своими делами или общаются (базовый контакт)."
    },

    # =========================================================================
    # VISITING FRIENDS (В ГОСТЯХ У ДРУЗЕЙ) - 8 ТРИГГЕРОВ
    # =========================================================================
    {
        "id": "guest_arrival_greeting",
        "name_ru": "Встреча на пороге (Приветствие)",
        "name_en": "Guest Arrival Greeting",
        "category": "МГНОВЕННОЕ",
        "prio": 100,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "1 раз за визит: хозяин дома впервые замечает активного гостя на пороге или в доме."
    },
    {
        "id": "guest_inappropriate_cooking",
        "name_ru": "Наглая готовка на чужой кухне",
        "name_en": "Inappropriate Cooking as Guest",
        "category": "МГНОВЕННОЕ",
        "prio": 92,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Гость начал готовить еду без черты «Всегда желанный гость», хозяин дома рядом."
    },
    {
        "id": "guest_late_curfew_departure",
        "name_ru": "Позднее время / Комендантский час (Пора домой)",
        "name_en": "Late Curfew / Late Departure",
        "category": "МГНОВЕННОЕ",
        "prio": 90,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Поздний вечер или ночь (дети/подростки 21:00-06:00, взрослые 23:30-05:00): гостю пора уходить домой."
    },
    {
        "id": "guest_homework_together",
        "name_ru": "Совместная домашка в гостях (Дети/Подростки)",
        "name_en": "Doing Homework Together",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Школьники или подростки вместе делают домашнюю работу в гостях."
    },
    {
        "id": "guest_gaming_console_tv",
        "name_ru": "Видеоигры / Совместный просмотр ТВ",
        "name_en": "Gaming / Watching TV as Guests",
        "category": "ФОНОВОЕ",
        "prio": 65,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Гость и хозяин играют в консоль/ПК или смотрят телевизор в комнате."
    },
    {
        "id": "guest_eating_drinking",
        "name_ru": "Совместный перекус / Напитки",
        "name_en": "Eating and Drinking with Friends",
        "category": "ФОНОВОЕ",
        "prio": 60,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Симы вместе едят приготовленные закуски или пьют напитки в гостях."
    },
    {
        "id": "guest_music_dance_chill",
        "name_ru": "Танцы и музыка под радио",
        "name_en": "Music & Dancing Chill",
        "category": "ФОНОВОЕ",
        "prio": 55,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Симы слушают музыку по стереосистеме или танцуют вместе в гостях."
    },
    {
        "id": "guest_ambient_hangout",
        "name_ru": "Фоновые посиделки в гостях",
        "name_en": "Ambient Hangout as Guests",
        "category": "ФОНОВОЕ",
        "prio": 30,
        "mode": "VISITING_FRIENDS",
        "requirements_ru": "Базовое общение и посиделки в гостях у друзей/знакомых в одной комнате (минимальный приоритет)."
    },

    # =========================================================================
    # VISITING RELATIVES (В ГОСТЯХ У РОДСТВЕННИКОВ) - 8 ТРИГГЕРОВ
    # =========================================================================
    {
        "id": "relative_warm_welcome",
        "name_ru": "Тёплая встреча родни на пороге",
        "name_en": "Warm Welcome from Relatives",
        "category": "МГНОВЕННОЕ",
        "prio": 100,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "1 раз за визит: родственник-хозяин встречает активного сима на пороге дома."
    },
    {
        "id": "relative_helping_chores",
        "name_ru": "Помощь родне по дому (Посуда / Мусор)",
        "name_en": "Helping Relatives with Chores",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Гость-родственник моет посуду или выносит мусор в доме хозяев, хозяин рядом."
    },
    {
        "id": "relative_homework_together",
        "name_ru": "Совместная домашка у родни (Дети/Подростки)",
        "name_en": "Doing Homework with Relatives",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Школьники или подростки родственники любого родства (кузены, племянники/дяди-ровесники) вместе делают домашку."
    },
    {
        "id": "relative_eating_together",
        "name_ru": "Семейное застолье / Домашнее угощение",
        "name_en": "Family Meal at Relatives",
        "category": "ФОНОВОЕ",
        "prio": 80,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Активный сим кушает домашнюю еду в гостях у родственников (один или за общим столом)."
    },
    {
        "id": "relative_interrogation_life",
        "name_ru": "Семейный допрос о жизни (Старший к младшему)",
        "name_en": "Family Life Interrogation",
        "category": "ФОНОВОЕ",
        "prio": 75,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Старший родственник (взрослый/пожилой) расспрашивает младшего про учёбу или личную жизнь и работу."
    },
    {
        "id": "relative_cousins_hanging",
        "name_ru": "Младшие родственники (Дети / Подростки отдельно)",
        "name_en": "Young Relatives Hangout",
        "category": "ФОНОВОЕ",
        "prio": 65,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Дети или подростки родственники любого родства (кузены, племянники/дяди-ровесники) проводят время отдельно от старших."
    },
    {
        "id": "relative_adult_family_gossip",
        "name_ru": "Разговоры взрослых о родне и быте",
        "name_en": "Adult Family Gossip & Life Talk",
        "category": "ФОНОВОЕ",
        "prio": 60,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Взрослые родственники (взрослый/пожилой) обсуждают новости семьи, здоровье и заботы."
    },
    {
        "id": "relative_ambient_visit",
        "name_ru": "Семейный уют в гостях",
        "name_en": "Ambient Family Visit",
        "category": "ФОНОВОЕ",
        "prio": 30,
        "mode": "VISITING_RELATIVES",
        "requirements_ru": "Базовое нахождение и общение в гостях у родственников в одной комнате (минимальный приоритет)."
    },
    # =========================================================================
    # REZHIM: NPC & GUESTS ON ACTIVE LOT (11 SCENARIOS)
    # =========================================================================
    {
        "id": "neighbor_welcome_wagon",
        "name_ru": "Визит соседей с кексом («Добро пожаловать!»)",
        "name_en": "Welcome Wagon Neighbors with Fruitcake",
        "category": "МГНОВЕННОЕ",
        "prio": 90,
        "mode": "NPC_HOME",
        "requirements_ru": "Соседи пришли приветствовать новосёлов с фруктовым кексом (активна ситуация Welcome Wagon)."
    },
    {
        "id": "service_repairman_done",
        "name_ru": "Отчёт мастера о починке техники",
        "name_en": "Repairman Reporting Finished Fix",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "mode": "NPC_HOME",
        "requirements_ru": "Мастер по ремонту находится на участке рядом с хозяином дома (починка завершена, услуга уже оплачена клиентом)."
    },
    {
        "id": "guest_home_door_greeting",
        "name_ru": "Встреча прибывшего гостя (друг / родня / сосед / незнакомец)",
        "name_en": "Arrival Greeting (Friend, Relative, Neighbor, Stranger)",
        "category": "МГНОВЕННОЕ",
        "prio": 88,
        "mode": "NPC_HOME",
        "requirements_ru": "Любой приглашённый или прибывший персонаж впервые встречается с хозяином дома на участке."
    },
    {
        "id": "guest_home_after_school",
        "name_ru": "Одноклассник в гостях после школы (15:00-19:00)",
        "name_en": "Schoolmate Home After School",
        "category": "МГНОВЕННОЕ",
        "prio": 87,
        "mode": "NPC_HOME",
        "requirements_ru": "Школьник или подросток привёл друга домой после школы (дети/подростки в период с 15 до 19 часов)."
    },
    {
        "id": "guest_home_farewell_late",
        "name_ru": "Прощание гостя поздно вечером / ночью",
        "name_en": "Guest Late Evening Farewell",
        "category": "МГНОВЕННОЕ",
        "prio": 87,
        "mode": "NPC_HOME",
        "requirements_ru": "Гость собирается уходить домой из-за позднего времени (после 22:00, комендантский час или действие ухода)."
    },
    {
        "id": "two_kid_guests_playing",
        "name_ru": "Дети-гости играют вместе (NPC-NPC дома)",
        "name_en": "Two Kid Guests Playing Together",
        "category": "МГНОВЕННОЕ",
        "prio": 86,
        "mode": "NPC_HOME",
        "requirements_ru": "Двое детей или подростков гостей играют в видеоигры, кукольный домик или игрушки в доме хозяев."
    },
    {
        "id": "service_nanny_chat",
        "name_ru": "Разговор с няней о детях",
        "name_en": "Nanny Report to Household Member",
        "category": "МГНОВЕННОЕ",
        "prio": 86,
        "mode": "NPC_HOME",
        "requirements_ru": "Нанятая няня на участке общается со старшим членом семьи о детях, кормлении и порядке."
    },
    {
        "id": "neighbor_door_knock",
        "name_ru": "Визит соседа у входа / порога",
        "name_en": "Neighbor Visit / Door Knock",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "mode": "NPC_HOME",
        "requirements_ru": "Сосед заглянул в гости (по приглашению или без) и общается у входа/крыльца с хозяином."
    },
    {
        "id": "guest_home_fridge_snack",
        "name_ru": "Гость полез в холодильник за перекусом",
        "name_en": "Guest Raiding Fridge for Snack",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "mode": "NPC_HOME",
        "requirements_ru": "Гость берет еду из холодильника или перекусывает на глазах у хозяина дома."
    },
    {
        "id": "two_guests_living_room",
        "name_ru": "Двое гостей в гостиной (NPC-NPC дома)",
        "name_en": "Two Guests in Living Room",
        "category": "ФОНОВОЕ",
        "prio": 76,
        "mode": "NPC_HOME",
        "requirements_ru": "Двое гостей (не члены семьи) сидят на диване или общаются в гостиной дома хозяев."
    },
    {
        "id": "service_maid_cleaning",
        "name_ru": "Горничная за уборкой в доме",
        "name_en": "Maid Cleaning in Household",
        "category": "ФОНОВОЕ",
        "prio": 75,
        "mode": "NPC_HOME",
        "requirements_ru": "Горничная или дворецкий моет посуду, выносит мусор или убирает лужи на глазах у члена семьи."
    },
    # =========================================================================
    # REZHIM: COMMUNITY LOTS (6 SCENARIOS)
    # =========================================================================
    {
        "id": "community_bar_order_chat",
        "name_ru": "Заказ у бармена / Разговор у стойки",
        "name_en": "Bar Order & Bartender Chat",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "mode": "COMMUNITY",
        "requirements_ru": "Бар, клуб, лаундж: сим заказывает напиток у стойки или общается с барменом (или двое у стойки с напитками)."
    },
    {
        "id": "community_cafe_barista",
        "name_ru": "Заказ кофе у баристы",
        "name_en": "Cafe Barista Order",
        "category": "МГНОВЕННОЕ",
        "prio": 85,
        "mode": "COMMUNITY",
        "requirements_ru": "Кафе: сим заказывает бодрящий кофе или выпечку у стойки баристы."
    },
    {
        "id": "community_gym_workout_spot",
        "name_ru": "Тренировка в спортзале (Тренер / Напарник)",
        "name_en": "Gym Workout & Spotting",
        "category": "ФОНОВОЕ",
        "prio": 75,
        "mode": "COMMUNITY",
        "requirements_ru": "Спортзал: один сим тренируется (дорожка, тренажер, груша), второй (тренер или напарник) находится рядом."
    },
    {
        "id": "community_restaurant_companion",
        "name_ru": "За столиком в заведении (Ресторан / Кафе)",
        "name_en": "Dining Table Companion",
        "category": "ФОНОВОЕ",
        "prio": 70,
        "mode": "COMMUNITY",
        "requirements_ru": "Ресторан, кафе: двое симов сидят за столиком с едой или напитками, обсуждая блюда или новости."
    },
    {
        "id": "community_library_whisper",
        "name_ru": "Тишина в зале (Библиотека / Музей)",
        "name_en": "Library & Museum Whisper",
        "category": "ФОНОВОЕ",
        "prio": 65,
        "mode": "COMMUNITY",
        "requirements_ru": "Библиотека, музей: симы читают, исследуют компьютер или выставку; разговор вполголоса."
    },
    {
        "id": "community_player_social",
        "name_ru": "Разговор с посетителем (Игрок + Сим)",
        "name_en": "Community Lot Player Conversation",
        "category": "ФОНОВОЕ",
        "prio": 80,
        "mode": "COMMUNITY",
        "requirements_ru": "Любой общественный участок: управляемый сим игрока ОБЯЗАТЕЛЬНО уже общается с кем-то в заведении (активный игровой разговор)."
    },
    {
        "id": "community_ambient_social",
        "name_ru": "Фоновая беседа посетителей (NPC + NPC)",
        "name_en": "Community Lot Ambient NPC Conversation",
        "category": "ФОНОВОЕ",
        "prio": 40,
        "mode": "COMMUNITY",
        "requirements_ru": "Любой общественный участок: двое NPC находятся рядом (до 8.5м) около семьи игрока. Разговаривать не обязательно (симы просто рядом). Имена семьи не называются."
    },
]

MODE_HOME = "HOME"
MODE_NPC_HOME = "NPC_HOME"
MODE_VISITING_FRIENDS = "VISITING_FRIENDS"
MODE_VISITING_RELATIVES = "VISITING_RELATIVES"
MODE_COMMUNITY = "COMMUNITY"

for _t in DIRECTOR_TRIGGERS:
    _t.setdefault("mode", MODE_HOME)
    _t.setdefault("weekly_limit", 0)

TRIGGER_MAP: Dict[str, Dict[str, Any]] = {t["id"]: t for t in DIRECTOR_TRIGGERS}

# All actions default to ENABLED (True).
TRIGGER_TOGGLES: Dict[str, bool] = {t["id"]: True for t in DIRECTOR_TRIGGERS}

# Configurable weekly limits for Director triggers (0 = disabled / unlimited by default)
TRIGGER_WEEKLY_LIMITS: Dict[str, int] = {t["id"]: t.get("weekly_limit", 0) for t in DIRECTOR_TRIGGERS}


def get_trigger_weekly_limit(trigger_id: str) -> int:
    """Returns the weekly limit for a trigger (0 means disabled / unlimited)."""
    return TRIGGER_WEEKLY_LIMITS.get(trigger_id, 0)


def set_trigger_weekly_limit(trigger_id: str, limit: int):
    """Sets the weekly limit for a trigger (0 = disabled / unlimited)."""
    if trigger_id in TRIGGER_MAP:
        val = max(0, int(limit))
        TRIGGER_WEEKLY_LIMITS[trigger_id] = val
        TRIGGER_MAP[trigger_id]["weekly_limit"] = val


def is_trigger_enabled(trigger_id: str) -> bool:
    """Deprecated test check - always returns True so testing does not block real director."""
    return True


def is_trigger_testing_active(trigger_id: str = "") -> bool:
    """Deprecated test check - isolated testing mode is completely disabled."""
    return False


def set_trigger_enabled(trigger_id: str, enabled: bool):
    """Sets enabled state for a specific trigger."""
    if trigger_id in TRIGGER_TOGGLES:
        TRIGGER_TOGGLES[trigger_id] = bool(enabled)
        if enabled:
            try:
                from ai_social_pc.autonomous_director import reset_all_cooldowns
                reset_all_cooldowns()
            except Exception:
                pass


def toggle_trigger(trigger_id: str) -> bool:
    """Toggles trigger state and returns the new value."""
    new_val = not TRIGGER_TOGGLES.get(trigger_id, False)
    TRIGGER_TOGGLES[trigger_id] = new_val
    if new_val:
        try:
            from ai_social_pc.autonomous_director import reset_all_cooldowns
            reset_all_cooldowns()
        except Exception:
            pass
    return new_val


def enable_all_triggers(enabled: bool = True):
    """Enables or disables all triggers at once."""
    for tid in TRIGGER_TOGGLES:
        TRIGGER_TOGGLES[tid] = bool(enabled)
    try:
        from ai_social_pc.autonomous_director import reset_all_cooldowns
        reset_all_cooldowns()
    except Exception:
        pass


def enable_triggers_by_mode(mode: str, enabled: bool = True):
    """Enables or disables all triggers belonging to a specific mode."""
    for t in DIRECTOR_TRIGGERS:
        if t.get("mode", MODE_HOME) == mode:
            TRIGGER_TOGGLES[t["id"]] = bool(enabled)
    try:
        from ai_social_pc.autonomous_director import reset_all_cooldowns
        reset_all_cooldowns()
    except Exception:
        pass


# =========================================================================
# HELPER: GET ACTIVE HOUSEHOLD SIMS
# =========================================================================

def get_household_sim_instances() -> List[Any]:
    if services is None:
        return []
    try:
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        hh = getattr(client, "household", None) if client else None
        if hh is None:
            return []
        sims = []
        for info in hh.sim_info_gen():
            inst = getattr(info, "get_sim_instance", lambda: None)()
            if inst is not None:
                sims.append(inst)

        # When visiting another residential lot, include resident hosts living on this lot
        active_lot = services.active_lot() if hasattr(services, "active_lot") else None
        owner_hh_id = getattr(active_lot, "owner_household_id", None) if active_lot else None
        if owner_hh_id and owner_hh_id != getattr(hh, "id", None) and hasattr(services, "household_manager"):
            hh_mgr = services.household_manager()
            host_hh = hh_mgr.get(owner_hh_id) if hh_mgr else None
            if host_hh:
                for h_info in host_hh.sim_info_gen():
                    h_inst = getattr(h_info, "get_sim_instance", lambda: None)()
                    if h_inst is not None and h_inst not in sims:
                        sims.append(h_inst)

        # On home lot, also include any visiting guests, service NPCs, or neighbors currently on the lot
        sim_info_mgr = services.sim_info_manager() if hasattr(services, "sim_info_manager") else None
        if sim_info_mgr is not None and hasattr(sim_info_mgr, "instanced_sims_gen"):
            for inst_sim in sim_info_mgr.instanced_sims_gen():
                if inst_sim is not None and inst_sim not in sims:
                    s_info = getattr(inst_sim, "sim_info", None)
                    if s_info and not getattr(s_info, "is_pet", False):
                        sims.append(inst_sim)

        active_sim = getattr(client, "active_sim", None) if client else None
        if active_sim is not None and active_sim in sims:
            sims.remove(active_sim)
            sims.insert(0, active_sim)
        return sims
    except Exception:
        return []


def get_sim_age_category(sim_info) -> str:
    """Returns upper-case age category string like 'CHILD', 'TEEN', 'ADULT', etc."""
    if sim_info is None:
        return "ADULT"
    try:
        age_enum = getattr(sim_info, "age", None)
        if age_enum is not None:
            return getattr(age_enum, "name", str(age_enum)).upper()
    except Exception:
        pass
    return "ADULT"


def are_sims_siblings(info_a, info_b) -> bool:
    """Checks if two Sims are siblings or household peers."""
    if info_a is None or info_b is None:
        return False
    try:
        if hasattr(info_a, "genealogy") and info_a.genealogy is not None:
            gen = info_a.genealogy
            other_id = getattr(info_b, "sim_id", None)
            if hasattr(gen, "get_siblings_sim_ids_gen"):
                if other_id in list(gen.get_siblings_sim_ids_gen()):
                    return True
        if hasattr(info_a, "relationship_tracker") and info_a.relationship_tracker is not None:
            rel = info_a.relationship_tracker.get_relationship(getattr(info_b, "sim_id", 0))
            if rel is not None:
                bits = getattr(rel, "bits", None) or getattr(rel, "_bits", None) or ()
                for bit in bits:
                    b_name = getattr(bit, "__name__", str(bit)).lower()
                    if any(k in b_name for k in ("sibling", "brother", "sister", "family")):
                        return True
    except Exception:
        pass
    hh_a = getattr(info_a, "household_id", 1)
    hh_b = getattr(info_b, "household_id", 2)
    return (hh_a == hh_b)


# =========================================================================
# TRIGGER EVALUATOR: CHECK CONDITIONS FOR SPECIFIC TRIGGER
# =========================================================================

def evaluate_trigger_conditions(trigger_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Evaluates whether conditions for trigger_id are strictly met right now.
    Returns: (is_met, reason_or_details, candidate_spark)
    """
    from ai_social_pc.autonomous_director import (
        are_sims_co_present, is_sim_available, is_sim_eating,
        is_sim_using_pc_or_laptop,
        get_sim_minutes_between, _sim_post_woohoo_tracker,
        _sim_work_return_tracker, WORK_RETURN_WINDOW_MINUTES,
        POST_WOOHOO_WINDOW_MINUTES, get_sim_now,
        get_minutes_since_sim_shift_ended, is_sim_genuinely_nude,
        get_sim_negative_mood_data, get_sim_eating_food_name,
        is_sim_truant_from_work_or_school,
        is_sim_gardening, is_sim_painting, is_sim_playing_instrument,
        is_sim_working_out, are_sims_playing_table_game, detect_pet_care_in_scene
    )
    from ai_thought_reader.context import get_current_activity

    sims = get_household_sim_instances()
    from ai_social_pc.autonomous_director import DEDICATED_COMMUNITY_TRIGGERS, NPC_HOME_TRIGGERS, is_sim_available
    if trigger_id in DEDICATED_COMMUNITY_TRIGGERS or trigger_id in NPC_HOME_TRIGGERS:
        try:
            if services is not None and hasattr(services, "sim_info_manager"):
                sim_mgr = services.sim_info_manager()
                if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                    for inst in sim_mgr.instanced_sims_gen():
                        if inst not in sims and is_sim_available(inst):
                            s_inf = getattr(inst, "sim_info", None)
                            if s_inf and not getattr(s_inf, "is_pet", False):
                                sims.append(inst)
        except Exception:
            pass

    if trigger_id == "witness_death":
        from ai_social_pc.autonomous_director import get_grim_reaper_instance_on_lot
        reaper = get_grim_reaper_instance_on_lot()
        if reaper is not None and reaper not in sims:
            sims.append(reaper)
    if len(sims) < 2:
        return False, "На участке меньше двух доступных персонажей", None

    # Get sim time
    now = get_sim_now()
    hour = 12
    try:
        from ai_social_pc.ui_chat import get_current_sim_hour
        hour = get_current_sim_hour()
    except Exception:
        if now is not None:
            h_val = getattr(now, "hour", 12)
            hour = h_val() if callable(h_val) else int(h_val)

    active_sim = None
    try:
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        active_sim = getattr(client, "active_sim", None) if client else None
    except Exception:
        pass

    all_pairs = []
    for i in range(len(sims)):
        for j in range(len(sims)):
            if i != j:
                all_pairs.append((sims[i], sims[j]))

    def pair_sort_key(p):
        s_a, s_b = p
        inf_a, inf_b = getattr(s_a, "sim_info", None), getattr(s_b, "sim_info", None)
        from ai_social_pc.autonomous_director import is_sim_active_guest
        is_player_pair = is_sim_active_guest(inf_a) or is_sim_active_guest(inf_b)
        if trigger_id == "community_ambient_social":
            act_score = 10 if is_player_pair else 0
        elif trigger_id == "community_player_social":
            act_score = 0 if is_player_pair else 10
        else:
            act_score = 0 if s_a == active_sim else (1 if s_b == active_sim else 2)
        co, _, dist = are_sims_co_present(s_a, s_b)
        co_score = 0 if co else (1000 + dist)
        return (act_score, co_score)

    all_pairs.sort(key=pair_sort_key)

    active_sim_fail_reason = None
    last_fail_reason = None

    # Check each pair
    for pair_idx in range(len(all_pairs)):
        for _pair_pass in (1,):
            sim_a, sim_b = all_pairs[pair_idx]
            info_a, info_b = sim_a.sim_info, sim_b.sim_info
            name_a = getattr(info_a, "first_name", "Сим 1")
            name_b = getattr(info_b, "first_name", "Сим 2")

            co_present, space_type, dist = are_sims_co_present(sim_a, sim_b)
            act_a = (get_current_activity(info_a) or "").lower()
            act_b = (get_current_activity(info_b) or "").lower()
            age_a = get_sim_age_category(info_a)
            age_b = get_sim_age_category(info_b)

            # VISITING TRIGGERS (Friends & Relatives & NPC Home & Community Lots)
            from ai_social_pc.autonomous_director import (
                DEDICATED_VISITING_FRIENDS_TRIGGERS, DEDICATED_VISITING_RELATIVES_TRIGGERS,
                NPC_HOME_TRIGGERS, DEDICATED_COMMUNITY_TRIGGERS,
                evaluate_visiting_friends_spark, evaluate_visiting_relatives_spark,
                evaluate_npc_home_spark, evaluate_community_lot_spark
            )
            if trigger_id in DEDICATED_VISITING_FRIENDS_TRIGGERS:
                if co_present:
                    pair_key = (min(info_a.sim_id, info_b.sim_id), max(info_a.sim_id, info_b.sim_id))
                    sp = evaluate_visiting_friends_spark(sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b, space_type, dist, now, hour, pair_key, True, False, lambda cand: cand if (cand and cand.get("trigger_type") == trigger_id) else None)
                    if sp is not None and sp.get("trigger_type") == trigger_id:
                        return True, f"Условия выполнены: {sp.get('premise', '')}", sp
                else:
                    if trigger_id == "guest_homework_together":
                        from ai_social_pc.autonomous_director import is_sim_doing_homework
                        if is_sim_doing_homework(sim_a, info_a, act_a) and is_sim_doing_homework(sim_b, info_b, act_b):
                            last_fail_reason = f"Оба сима ({name_a} и {name_b}) делают уроки, но находятся слишком далеко друг от друга (расстояние {dist:.1f}м, {space_type}). Посадите их за один стол или в одну комнату."
                            continue
                    last_fail_reason = f"Симы {name_a} и {name_b} не находятся рядом (дистанция {dist:.1f}м)"

            if trigger_id in DEDICATED_VISITING_RELATIVES_TRIGGERS:
                if co_present:
                    pair_key = (min(info_a.sim_id, info_b.sim_id), max(info_a.sim_id, info_b.sim_id))
                    sp = evaluate_visiting_relatives_spark(sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b, space_type, dist, now, hour, pair_key, True, False, lambda cand: cand if (cand and cand.get("trigger_type") == trigger_id) else None)
                    if sp is not None and sp.get("trigger_type") == trigger_id:
                        return True, f"Условия выполнены: {sp.get('premise', '')}", sp
                else:
                    if trigger_id == "relative_homework_together":
                        from ai_social_pc.autonomous_director import is_sim_doing_homework
                        if is_sim_doing_homework(sim_a, info_a, act_a) and is_sim_doing_homework(sim_b, info_b, act_b):
                            last_fail_reason = f"Оба сима ({name_a} и {name_b}) делают уроки, но находятся слишком далеко друг от друга (расстояние {dist:.1f}м, {space_type}). Посадите их за один стол или в одну комнату."
                            continue
                    last_fail_reason = f"Симы {name_a} и {name_b} не находятся рядом (дистанция {dist:.1f}м)"

            if trigger_id in NPC_HOME_TRIGGERS:
                if co_present:
                    pair_key = (min(info_a.sim_id, info_b.sim_id), max(info_a.sim_id, info_b.sim_id))
                    sp = evaluate_npc_home_spark(sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b, space_type, dist, now, hour, pair_key, True, False, lambda cand: cand if (cand and cand.get("trigger_type") == trigger_id) else None)
                    if sp is not None and sp.get("trigger_type") == trigger_id:
                        return True, f"Условия выполнены: {sp.get('premise', '')}", sp
                else:
                    last_fail_reason = f"Симы {name_a} и {name_b} не находятся рядом (дистанция {dist:.1f}м)"

            if trigger_id in DEDICATED_COMMUNITY_TRIGGERS:
                from ai_social_pc.autonomous_director import is_sim_active_guest, are_sims_actively_conversing
                is_p_a = is_sim_active_guest(info_a)
                is_p_b = is_sim_active_guest(info_b)
                if trigger_id == "community_ambient_social" and (is_p_a or is_p_b):
                    continue
                if trigger_id == "community_player_social" and not (is_p_a or is_p_b):
                    continue

                if trigger_id == "community_player_social":
                    if not are_sims_actively_conversing(sim_a, sim_b, info_a, info_b):
                        last_fail_reason = f"Сим игрока ({name_a if is_p_a else name_b}) не общается с {name_b if is_p_a else name_a}. Для общения игрока обязательно требуется активный разговор в игре."
                        continue

                if trigger_id == "community_ambient_social":
                    from ai_social_pc.autonomous_director import is_sim_moving
                    is_actively_talking = are_sims_actively_conversing(sim_a, sim_b, info_a, info_b)
                    if not is_actively_talking:
                        if dist is None or dist > 3.5:
                            last_fail_reason = f"NPC {name_a} и {name_b} находятся слишком далеко друг от друга (дистанция {dist:.1f}м > 3.5м). Они должны быть рядом (за одним столом/диваном или у стойки)."
                            continue
                        if is_sim_moving(sim_a) or is_sim_moving(sim_b):
                            last_fail_reason = f"Один из NPC ({name_a} или {name_b}) идёт/бежит по участку. Для разговора оба сима должны стоять или сидеть."
                            continue

                if co_present or dist <= 8.5:
                    pair_key = (min(info_a.sim_id, info_b.sim_id), max(info_a.sim_id, info_b.sim_id))
                    sp = evaluate_community_lot_spark(
                        sim_a, sim_b, info_a, info_b, act_a, act_b, age_a, age_b, name_a, name_b,
                        space_type, dist, now, hour, pair_key, False, False,
                        lambda cand: cand if (cand and cand.get("trigger_type") == trigger_id) else None
                    )
                    if sp is not None and sp.get("trigger_type") == trigger_id:
                        return True, f"Условия выполнены: {sp.get('premise', '')}", sp
                else:
                    last_fail_reason = f"Симы {name_a} и {name_b} не находятся рядом (дистанция {dist:.1f}м)"

            # 1. COOKING_TOGETHER
            if trigger_id == "cooking_together":
                if not co_present:
                    continue
                is_cook_a = any(w in act_a for w in ["готовит", "жарит", "варит", "печет", "cook", "bake"])
                is_cook_b = any(w in act_b for w in ["готовит", "жарит", "варит", "печет", "cook", "bake"])
                if is_cook_a and not is_sim_eating(sim_b, info_b, act_b):
                    spark = {
                        "trigger_type": "cooking_together",
                        "priority": 86,
                        "premise": f"{name_a} готовит еду у плиты, а {name_b} находится рядом на кухне.",
                        "participants": [info_a, info_b]
                    }
                    return True, f"{name_a} готовит у плиты, {name_b} рядом на кухне ({space_type})", spark
                if is_cook_b and not is_sim_eating(sim_a, info_a, act_a):
                    spark = {
                        "trigger_type": "cooking_together",
                        "priority": 86,
                        "premise": f"{name_b} готовит еду у плиты, а {name_a} находится рядом на кухне.",
                        "participants": [info_b, info_a]
                    }
                    return True, f"{name_b} готовит у плиты, {name_a} рядом на кухне ({space_type})", spark

            # 2. BURNT_FOOD
            elif trigger_id == "burnt_food":
                if not co_present:
                    continue
                is_burnt_a = any(w in act_a for w in ["пригорев", "burnt", "сгоревш", "гарь", "подгорев"])
                is_burnt_b = any(w in act_b for w in ["пригорев", "burnt", "сгоревш", "гарь", "подгорев"])
                if is_burnt_a or is_burnt_b:
                    cook = info_a if is_burnt_a else info_b
                    wit = info_b if is_burnt_a else info_a
                    c_n = getattr(cook, "first_name", "Повар")
                    w_n = getattr(wit, "first_name", "Свидетель")
                    spark = {
                        "trigger_type": "burnt_food",
                        "priority": 95,
                        "premise": f"{c_n} сжег блюдо у плиты, на кухне стоит запах гари. {w_n} находится рядом.",
                        "participants": [cook, wit]
                    }
                    return True, f"{c_n} сжёг еду, {w_n} чувствует гарь", spark

            # 3. BROKEN_OBJECT
            elif trigger_id == "broken_object":
                if not co_present:
                    last_fail_reason = f"Симы не рядом ({space_type}, {dist:.1f}м)"
                    continue
                from ai_social_pc.autonomous_director import detect_broken_objects_in_scene, build_broken_object_premise
                has_broken, broken_names, rep_name, rep_target, rep_other = detect_broken_objects_in_scene(sim_a, sim_b, act_a, act_b)
                if has_broken:
                    premise_text = build_broken_object_premise(name_a, name_b, broken_names, rep_name, rep_target, rep_other)
                    spark = {
                        "trigger_type": "broken_object",
                        "priority": 88,
                        "premise": premise_text,
                        "participants": [info_a, info_b]
                    }
                    items_desc = ", ".join(broken_names) if broken_names else (rep_target or "поломка")
                    return True, f"Обнаружена поломка ({items_desc}) рядом с {name_a} и {name_b}", spark
                else:
                    last_fail_reason = f"Симы рядом ({space_type}, {dist:.1f}м), но рядом в радиусе 8м нет сломанных приборов или луж"

            # 3.1. DIRTY_DISH_TRASH
            elif trigger_id == "dirty_dish_trash":
                if not co_present:
                    last_fail_reason = f"Симы не рядом ({space_type}, {dist:.1f}м)"
                    continue
                from ai_social_pc.autonomous_director import detect_dirty_environment_in_scene, build_dirty_environment_premise
                has_dirty, dirty_names, cl_name, cl_target, cl_other = detect_dirty_environment_in_scene(sim_a, sim_b, act_a, act_b)
                if has_dirty:
                    premise_text = build_dirty_environment_premise(name_a, name_b, dirty_names, cl_name, cl_target, cl_other)
                    spark = {
                        "trigger_type": "dirty_dish_trash",
                        "priority": 87,
                        "premise": premise_text,
                        "participants": [info_a, info_b]
                    }
                    items_desc = ", ".join(dirty_names) if dirty_names else (f"уборка ({cl_target})" if cl_target else "грязь")
                    return True, f"Обнаружена грязь/испорченная еда ({items_desc}) рядом с {name_a} и {name_b}", spark
                else:
                    last_fail_reason = f"Симы рядом ({space_type}, {dist:.1f}м), но рядом в радиусе 8м нет грязных предметов, кухонных тумб, мусора на полу или тарелки с испорченной едой"

            # 4. LATE_NIGHT_AWAKE
            elif trigger_id == "late_night_awake":
                if not (hour >= 23 or hour < 5):
                    last_fail_reason = f"Сейчас не ночное время (в игре {hour:02d}:00, нужно с 23:00 до 05:00)"
                    continue
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                is_p_a = age_a in ("ADULT", "ELDER", "YOUNGADULT")
                is_c_b = age_b in ("BABY", "INFANT", "TODDLER", "CHILD", "TEEN")
                is_p_b = age_b in ("ADULT", "ELDER", "YOUNGADULT")
                is_c_a = age_a in ("BABY", "INFANT", "TODDLER", "CHILD", "TEEN")
                if (is_p_a and is_c_b) or (is_p_b and is_c_a):
                    p_info = info_a if is_p_a else info_b
                    c_info = info_b if is_p_a else info_a
                    p_n = getattr(p_info, "first_name", "Родитель")
                    c_n = getattr(c_info, "first_name", "Ребёнок")
                    spark = {
                        "trigger_type": "late_night_awake",
                        "priority": 88,
                        "premise": f"{p_n} застает {c_n} бодрствующим глубокой ночью в комнате, когда пора спать.",
                        "participants": [p_info, c_info]
                    }
                    return True, f"Ночь ({hour:02d}:00): родитель {p_n} застал {c_n}", spark
                else:
                    last_fail_reason = f"Нет подходящей пары родитель+ребёнок ({name_a}: {age_a}, {name_b}: {age_b})"

            # 5. EATING_TOGETHER
            elif trigger_id == "eating_together":
                if co_present and is_sim_eating(sim_a, info_a, act_a) and is_sim_eating(sim_b, info_b, act_b):
                    food_a = get_sim_eating_food_name(sim_a, info_a, act_a)
                    food_b = get_sim_eating_food_name(sim_b, info_b, act_b)

                    if food_a and food_b:
                        if food_a.lower() == food_b.lower():
                            premise = f"{name_a} и {name_b} вместе едят «{food_a}»."
                            status_txt = f"{name_a} и {name_b} едят «{food_a}» ({space_type})"
                        else:
                            premise = f"{name_a} и {name_b} вместе едят ({name_a} ест «{food_a}», а {name_b} — «{food_b}»)."
                            status_txt = f"{name_a} ест «{food_a}», {name_b} — «{food_b}» ({space_type})"
                    elif food_a or food_b:
                        single_food = food_a or food_b
                        premise = f"{name_a} и {name_b} вместе едят (на столе: «{single_food}»)."
                        status_txt = f"{name_a} и {name_b} кушают («{single_food}») ({space_type})"
                    else:
                        premise = f"{name_a} и {name_b} вместе едят за одним столом."
                        status_txt = f"{name_a} и {name_b} оба едят ({space_type})"

                    spark = {
                        "trigger_type": "eating_together",
                        "priority": 89,
                        "premise": premise,
                        "participants": [info_a, info_b]
                    }
                    return True, status_txt, spark

            # 6. WATCHING_TV_TOGETHER
            elif trigger_id == "watching_tv_together":
                if not co_present:
                    continue
                tv_a = any(w in act_a for w in ["тв", "телевизор", "сериал", "фильм", "tv", "movie", "watch"])
                tv_b = any(w in act_b for w in ["тв", "телевизор", "сериал", "фильм", "tv", "movie", "watch"])
                if tv_a and tv_b:
                    spark = {
                        "trigger_type": "watching_tv_together",
                        "priority": 78,
                        "premise": f"{name_a} и {name_b} сидят рядом и смотрят телевизор.",
                        "participants": [info_a, info_b]
                    }
                    return True, f"{name_a} и {name_b} вместе смотрят ТВ", spark

            # 7. PC_SIBLINGS_SHARE
            elif trigger_id == "pc_siblings_share":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                pc_a = is_sim_using_pc_or_laptop(sim_a, info_a, act_a)
                pc_b = is_sim_using_pc_or_laptop(sim_b, info_b, act_b)
                if not (pc_a or pc_b):
                    last_fail_reason = f"Никто из симов не сидит за ПК/ноутбуком ({name_a}: {act_a}, {name_b}: {act_b})"
                    continue
                if pc_a and pc_b:
                    last_fail_reason = f"Оба сима уже заняты за ПК/ноутбуком"
                    continue
                if not (age_a in ("CHILD", "TEEN") and age_b in ("CHILD", "TEEN")):
                    last_fail_reason = f"Оба сима должны быть детьми/подростками ({name_a}: {age_a}, {name_b}: {age_b})"
                    continue
                if not are_sims_siblings(info_a, info_b):
                    last_fail_reason = f"Симы {name_a} и {name_b} не являются сиблингами/семьей"
                    continue

                gamer = info_a if pc_a else info_b
                other = info_b if pc_a else info_a
                g_n = getattr(gamer, "first_name", "Сим")
                o_n = getattr(other, "first_name", "Сим")
                spark = {
                    "trigger_type": "pc_siblings_share",
                    "priority": 79,
                    "premise": f"{g_n} сидит за компьютером или ноутбуком, а {o_n} находится в этой же комнате.",
                    "participants": [other, gamer]
                }
                return True, f"Сиблинги у ПК/ноутбука: {g_n} играет, {o_n} рядом", spark

            # 7.1. HOMEWORK_NOT_DONE
            elif trigger_id == "homework_not_done":
                if not (15 <= hour <= 23):
                    last_fail_reason = f"Сейчас не время для проверки уроков (в игре {hour:02d}:00, требуется 15:00-23:00)"
                    continue
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                from ai_social_pc.autonomous_director import is_sim_doing_homework, is_sim_homework_completed
                for p_inf, c_inf, p_ag, c_ag, c_sim, c_act in [
                    (info_a, info_b, age_a, age_b, sim_b, act_b),
                    (info_b, info_a, age_b, age_a, sim_a, act_a)
                ]:
                    if p_ag in ("YOUNGADULT", "ADULT", "ELDER") and c_ag in ("CHILD", "TEEN"):
                        hw_done = is_sim_homework_completed(c_inf, c_sim)
                        is_doing = is_sim_doing_homework(c_sim, c_inf, c_act)
                        if not hw_done and not is_doing:
                            p_n = getattr(p_inf, "first_name", "Родитель")
                            c_n = getattr(c_inf, "first_name", "Школьник")
                            spark = {
                                "trigger_type": "homework_not_done",
                                "priority": 80,
                                "premise": f"{c_n} еще не сделал школьное домашнее задание, а {p_n} находится рядом в комнате.",
                                "participants": [p_inf, c_inf]
                            }
                            return True, f"У школьника {c_n} не сделана домашка, {p_n} рядом ({space_type})", spark
                        elif hw_done:
                            last_fail_reason = f"У {getattr(c_inf, 'first_name', 'школьника')} домашнее задание уже сделано"
                        else:
                            last_fail_reason = f"{getattr(c_inf, 'first_name', 'Школьник')} прямо сейчас делает домашнее задание"
                    else:
                        if not last_fail_reason:
                            last_fail_reason = f"Требуется пара Взрослый + Школьник ({name_a}: {age_a}, {name_b}: {age_b})"

            # 7.2. HOMEWORK_IN_PROGRESS (В любое время, когда школьник учит уроки)
            elif trigger_id == "homework_in_progress":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for c_inf, o_inf, c_ag, o_ag, c_sim, o_sim, c_act, o_act in [
                    (info_a, info_b, age_a, age_b, sim_a, sim_b, act_a, act_b),
                    (info_b, info_a, age_b, age_a, sim_b, sim_a, act_b, act_a)
                ]:
                    if c_ag in ("CHILD", "TEEN"):
                        from ai_social_pc.autonomous_director import is_sim_doing_homework, is_sim_helping_with_homework
                        if is_sim_doing_homework(c_sim, c_inf, c_act):
                            c_n = getattr(c_inf, "first_name", "Школьник")
                            o_n = getattr(o_inf, "first_name", "Собеседник")
                            if o_ag in ("YOUNGADULT", "ADULT", "ELDER"):
                                is_help = is_sim_helping_with_homework(o_sim, o_inf, o_act)
                                if is_help:
                                    premise = f"{c_n} делает домашнее задание, а {o_n} помогает с уроками."
                                    status_txt = f"{c_n} учит уроки, {o_n} помогает ({space_type})"
                                    parts = [o_inf, c_inf]
                                else:
                                    premise = f"{c_n} делает домашнее задание, а {o_n} находится рядом в комнате."
                                    status_txt = f"{c_n} учит уроки, {o_n} рядом ({space_type})"
                                    parts = [c_inf, o_inf]
                                spark = {
                                    "trigger_type": "homework_in_progress",
                                    "priority": 78,
                                    "premise": premise,
                                    "participants": parts
                                }
                                return True, status_txt, spark
                            elif o_ag in ("CHILD", "TEEN"):
                                o_doing = is_sim_doing_homework(o_sim, o_inf, o_act)
                                if o_doing:
                                    premise = f"Сиблинги {c_n} и {o_n} вместе делают домашнее задание."
                                    status_txt = f"{c_n} и {o_n} оба делают домашнее задание ({space_type})"
                                else:
                                    premise = f"{c_n} делает домашнее задание, а {o_n} находится рядом в комнате."
                                    status_txt = f"{c_n} учит уроки, сиблинг {o_n} рядом ({space_type})"
                                spark = {
                                    "trigger_type": "homework_in_progress",
                                    "priority": 78,
                                    "premise": premise,
                                    "participants": [c_inf, o_inf]
                                }
                                return True, status_txt, spark
                        else:
                            last_fail_reason = f"Школьник {getattr(c_inf, 'first_name', 'ребёнок')} прямо сейчас НЕ делает домашнее задание"
                    else:
                        if not last_fail_reason:
                            last_fail_reason = f"Требуется школьник (ребёнок или подросток) в паре ({name_a}: {age_a}, {name_b}: {age_b})"

            # 7.3. HOMEWORK_DONE
            elif trigger_id == "homework_done":
                if not (6 <= hour <= 23):
                    last_fail_reason = f"Сейчас глубокая ночь (в игре {hour:02d}:00, требуется 06:00-23:00)"
                    continue
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                from ai_social_pc.autonomous_director import is_sim_doing_homework, is_sim_homework_completed
                for c_inf, o_inf, c_ag, o_ag, c_sim, o_sim, c_act in [
                    (info_a, info_b, age_a, age_b, sim_a, sim_b, act_a),
                    (info_b, info_a, age_b, age_a, sim_b, sim_a, act_b)
                ]:
                    if c_ag in ("CHILD", "TEEN"):
                        if is_sim_doing_homework(c_sim, c_inf, c_act):
                            last_fail_reason = f"Школьник {getattr(c_inf, 'first_name', 'ребёнок')} всё ещё в процессе уроков (используйте триггер homework_in_progress)"
                            continue
                        hw_done = is_sim_homework_completed(c_inf, c_sim)
                        if hw_done:
                            c_n = getattr(c_inf, "first_name", "Школьник")
                            o_n = getattr(o_inf, "first_name", "Сим")
                            if o_ag in ("YOUNGADULT", "ADULT", "ELDER"):
                                premise = f"{c_n} сделал все школьные домашние задания, а {o_n} находится рядом в комнате."
                            elif o_ag in ("CHILD", "TEEN"):
                                premise = f"{c_n} закончил делать домашнее задание, а {o_n} находится рядом в комнате."
                            else:
                                premise = f"{c_n} сделал все школьные домашние задания, а {o_n} находится рядом в комнате."
                            spark = {
                                "trigger_type": "homework_done",
                                "priority": 76,
                                "premise": premise,
                                "participants": [c_inf, o_inf]
                            }
                            return True, f"У школьника {c_n} сделана домашка, {o_n} рядом ({space_type})", spark
                        else:
                            last_fail_reason = f"У школьника {getattr(c_inf, 'first_name', 'ребёнка')} домашнее задание ещё НЕ сделано"
                    else:
                        if not last_fail_reason:
                            last_fail_reason = f"Требуется школьник (ребёнок или подросток) в паре ({name_a}: {age_a}, {name_b}: {age_b})"

            # 8. WW_POST_INTIMACY
            elif trigger_id == "ww_post_intimacy":
                if co_present:
                    for p_inf, o_inf in [(info_a, info_b), (info_b, info_a)]:
                        post_entry = _sim_post_woohoo_tracker.get(p_inf.sim_id)
                        post_t = post_entry[0] if isinstance(post_entry, (tuple, list)) else post_entry
                        partner_ids = set(post_entry[1]) if isinstance(post_entry, (tuple, list)) and len(post_entry) > 1 and isinstance(post_entry[1], (set, list)) else set()
                        if partner_ids and o_inf.sim_id not in partner_ids:
                            continue
                        if post_t and now and get_sim_minutes_between(post_t, now) <= POST_WOOHOO_WINDOW_MINUTES:
                            p_n = getattr(p_inf, "first_name", "Сим")
                            o_n = getattr(o_inf, "first_name", "Сим")
                            where_p = post_entry[2] if isinstance(post_entry, (tuple, list)) and len(post_entry) > 2 and isinstance(post_entry[2], str) else ""
                            loc_s = f" ({where_p})" if where_p else ""
                            spark = {
                                "trigger_type": "ww_post_intimacy",
                                "priority": 87,
                                "premise": f"{p_n} и {o_n} после интимной близости (секса / вуху){loc_s} находятся рядом, приходя в себя.",
                                "participants": [p_inf, o_inf]
                            }
                            return True, f"{p_n} и {o_n} после секса / вуху", spark

            # 8.5 WW_ACCIDENTAL_NUDITY
            elif trigger_id == "ww_accidental_nudity":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                is_nu_a = is_sim_genuinely_nude(info_a)
                is_nu_b = is_sim_genuinely_nude(info_b)
                if (is_nu_a and not is_nu_b) or (is_nu_b and not is_nu_a):
                    nu_inf = info_a if is_nu_a else info_b
                    cl_inf = info_b if is_nu_a else info_a
                    nu_n = getattr(nu_inf, "first_name", "Сим")
                    cl_n = getattr(cl_inf, "first_name", "Сим")
                    spark = {
                        "trigger_type": "ww_accidental_nudity",
                        "priority": 85,
                        "premise": f"{nu_n} находится без одежды в присутствии одетого {cl_n}.",
                        "participants": [cl_inf, nu_inf]
                    }
                    return True, f"{nu_n} голый, {cl_n} одет (в одной комнате)", spark
                else:
                    if is_nu_a and is_nu_b:
                        last_fail_reason = "Оба сима голые (требуется один голый и один одетый)"
                    else:
                        last_fail_reason = "Ни один из симов не является полностью голым"

            # 9. WORK_RETURN
            elif trigger_id == "work_return":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for r_inf, w_inf in [(info_a, info_b), (info_b, info_a)]:
                    ret_t = _sim_work_return_tracker.get(r_inf.sim_id)
                    mins_diff = None
                    if ret_t and now:
                        mins_diff = get_sim_minutes_between(ret_t, now)
                    if mins_diff is None:
                        mins_diff = get_minutes_since_sim_shift_ended(r_inf, now)

                    if mins_diff is not None and mins_diff <= WORK_RETURN_WINDOW_MINUTES:
                        r_n = getattr(r_inf, "first_name", "Сим")
                        w_n = getattr(w_inf, "first_name", "Сим")
                        spark = {
                            "trigger_type": "work_return",
                            "priority": 85,
                            "premise": f"{r_n} вернулся домой со смены (работы или школы) и встречает {w_n}.",
                            "participants": [w_inf, r_inf]
                        }
                        return True, f"{r_n} вернулся с работы/школы {int(mins_diff)} мин. назад (встречает {w_n})", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов не возвращался с работы или школы в последние 40 минут"

            # 10. NEGATIVE MOOD REACTION (Гнев, Грусть, Стресс, Смущение, Страх, Дискомфорт, Ошалелость, Скука)
            elif trigger_id == "negative_mood_reaction":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for em_inf, oth_inf in [(info_a, info_b), (info_b, info_a)]:
                    m_data = get_sim_negative_mood_data(em_inf)
                    if m_data is not None:
                        e_n = getattr(em_inf, "first_name", "Сим")
                        o_n = getattr(oth_inf, "first_name", "Сим")
                        spark = {
                            "trigger_type": "negative_mood_reaction",
                            "priority": 84,
                            "premise": f"{e_n} находится в тяжёлом настроении ({m_data['mood_desc']}), а {o_n} находится рядом.",
                            "participants": [oth_inf, em_inf]
                        }
                        return True, f"{e_n} {m_data['label_phrase']} ({m_data['mood_desc']})", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни у одного из симов нет отрицательного настроения (Грусть, Гнев, Стресс, Смущение, Страх, Дискомфорт и др.)"

            # 11. BEDTIME_PILLOW_TALK
            elif trigger_id == "bedtime_pillow_talk":
                if (hour >= 21 or hour <= 1) and co_present:
                    is_romantic = False
                    is_parent_child = False
                    try:
                        from ai_thought_reader.context import get_relationship_status
                        rel_str = (get_relationship_status(info_a, info_b) or "").lower()
                        is_romantic = any(k in rel_str for k in ["муж", "жена", "супруг", "возлюблен", "парень", "девушка", "любов"])
                        is_parent_child = any(k in rel_str for k in ["отец", "мать", "сын", "дочь", "родител", "ребенок"])
                    except Exception:
                        pass

                    if is_romantic:
                        premise = f"{name_a} и {name_b} проводят время вместе поздним вечером перед сном."
                    elif is_parent_child:
                        premise = f"{name_a} и {name_b} находятся в доме поздним вечером перед сном."
                    else:
                        premise = f"{name_a} и {name_b} бодрствуют в доме поздним вечером перед сном."

                    spark = {
                        "trigger_type": "bedtime_pillow_talk",
                        "priority": 65,
                        "premise": premise,
                        "participants": [info_a, info_b]
                    }
                    return True, f"{name_a} и {name_b} бодрствуют ночью ({hour:02d}:00, {space_type})", spark
                else:
                    if not (hour >= 21 or hour <= 1):
                        last_fail_reason = f"Сейчас не ночное время (сейчас {hour:02d}:00, требуется 21:00-02:00)"
                    elif not co_present:
                        last_fail_reason = f"Симы не в одной комнате ({space_type}, {dist:.1f}м)"

            # 12. MORNING_COFFEE (Утреннее приветствие)
            elif trigger_id == "morning_coffee":
                if (6 <= hour <= 10) and co_present:
                    premise = f"{name_a} и {name_b} только проснулись и встретились утром в доме."
                    spark = {
                        "trigger_type": "morning_coffee",
                        "priority": 65,
                        "premise": premise,
                        "participants": [info_a, info_b]
                    }
                    return True, f"Утро ({hour:02d}:00): {name_a} и {name_b} встретились ({space_type})", spark
                else:
                    if not (6 <= hour <= 10):
                        last_fail_reason = f"Сейчас не утро (текущее время {hour:02d}:00, требуется 06:00-10:00)"
                    elif not co_present:
                        last_fail_reason = f"Симы не в одной комнате ({space_type}, {dist:.1f}м)"


            # 13.1. TRUANT_SCHOOL_WORK (Прогул школы / смены)
            elif trigger_id == "truant_school_work":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue

                for t_inf, o_inf, t_ag, o_ag in [(info_a, info_b, age_a, age_b), (info_b, info_a, age_b, age_a)]:
                    is_tr, is_sch, car_tit, stat_d = is_sim_truant_from_work_or_school(t_inf)
                    if is_tr:
                        t_n = getattr(t_inf, "first_name", "Сим")
                        o_n = getattr(o_inf, "first_name", "Сим")
                        if is_sch or t_ag in ("CHILD", "TEEN"):
                            premise = f"{t_n} прогуливает школу и остался дома в учебное время, а {o_n} застаёт его."
                        else:
                            premise = f"{t_n} прогуливает работу и остался дома в рабочее время, а {o_n} застаёт его."
                        spark = {
                            "trigger_type": "truant_school_work",
                            "priority": 90,
                            "premise": premise,
                            "participants": [o_inf, t_inf]
                        }
                        status_msg = f"{t_n} прогуливает ({stat_d or car_tit}), дома вместе с {o_n} ({space_type})"
                        return True, status_msg, spark

                if not last_fail_reason:
                    _, _, _, st_a = is_sim_truant_from_work_or_school(info_a)
                    _, _, _, st_b = is_sim_truant_from_work_or_school(info_b)
                    desc_a = f"{name_a}: {st_a}" if st_a else f"{name_a}: нет смены"
                    desc_b = f"{name_b}: {st_b}" if st_b else f"{name_b}: нет смены"
                    last_fail_reason = f"Ни один из симов сейчас не прогуливает смену/уроки ({desc_a}; {desc_b})"


            # 13.2. GARDENING_TOGETHER
            elif trigger_id == "gardening_together":
                for g_sim, o_sim, g_inf, o_inf, g_act, o_act in [(sim_a, sim_b, info_a, info_b, act_a, act_b), (sim_b, sim_a, info_b, info_a, act_b, act_a)]:
                    is_gard, gard_detail = is_sim_gardening(g_sim, g_inf, g_act)
                    if is_gard:
                        is_near = co_present
                        if not is_near and g_sim is not None and o_sim is not None:
                            try:
                                from ai_thought_reader.context import get_sim_room_and_outdoor
                                _, out_g = get_sim_room_and_outdoor(g_sim)
                                _, out_o = get_sim_room_and_outdoor(o_sim)
                                if out_g and out_o:
                                    pos_g = getattr(g_sim, "position", None)
                                    pos_o = getattr(o_sim, "position", None)
                                    if pos_g is not None and pos_o is not None and float((pos_g - pos_o).magnitude()) <= 12.0:
                                        is_near = True
                            except Exception:
                                pass
                        if is_near:
                            g_n = getattr(g_inf, "first_name", "Сим")
                            o_n = getattr(o_inf, "first_name", "Сим")
                            spark = {
                                "trigger_type": "gardening_together",
                                "priority": 75,
                                "premise": f"{g_n} ухаживает за растениями ({gard_detail}), а {o_n} находится рядом.",
                                "participants": [g_inf, o_inf],
                            }
                            return True, f"{g_n} ухаживает за растениями ({gard_detail}), {o_n} рядом", spark
                        else:
                            last_fail_reason = f"Сим {getattr(g_inf, 'first_name', 'Садовод')} занимается садом, но второй сим слишком далеко"
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов прямо сейчас не занимается садоводством (полив, сбор урожая, прополка)"

            # 13.3. CREATIVE_PAINTING
            elif trigger_id == "creative_painting":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for p_sim, o_sim, p_inf, o_inf, p_act, o_act in [(sim_a, sim_b, info_a, info_b, act_a, act_b), (sim_b, sim_a, info_b, info_a, act_b, act_a)]:
                    is_paint, paint_detail = is_sim_painting(p_sim, p_inf, p_act)
                    if is_paint:
                        p_n = getattr(p_inf, "first_name", "Сим")
                        o_n = getattr(o_inf, "first_name", "Сим")
                        if paint_detail in ("sketchpad", "эскиз на планшете", "рисует эскиз на цифровом планшете"):
                            premise = f"{p_n} рисует эскиз на цифровом планшете, а {o_n} просто находится рядом в комнате (не позирует и не является объектом рисунка)."
                            status_msg = f"{p_n} рисует эскиз на планшете, {o_n} в комнате"
                        elif paint_detail and paint_detail not in ("на мольберте", "пишет картину на мольберте"):
                            premise = f"{p_n} пишет на мольберте картину ({paint_detail}), а {o_n} просто находится рядом в комнате (не позирует и не является объектом картины)."
                            status_msg = f"{p_n} пишет картину ({paint_detail}), {o_n} в комнате"
                        else:
                            premise = f"{p_n} пишет на мольберте картину, а {o_n} просто находится рядом в комнате (не позирует и не является объектом картины)."
                            status_msg = f"{p_n} пишет картину на мольберте, {o_n} в комнате"
                        spark = {
                            "trigger_type": "creative_painting",
                            "priority": 74,
                            "premise": premise,
                            "participants": [p_inf, o_inf],
                        }
                        return True, status_msg, spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов прямо сейчас не пишет картину на мольберте или цифровом планшете"

            # 13.4. MUSIC_PERFORMANCE
            elif trigger_id == "music_performance":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for m_sim, o_sim, m_inf, o_inf, m_act, o_act in [(sim_a, sim_b, info_a, info_b, act_a, act_b), (sim_b, sim_a, info_b, info_a, act_b, act_a)]:
                    is_mus, inst_name = is_sim_playing_instrument(m_sim, m_inf, m_act)
                    if is_mus:
                        m_n = getattr(m_inf, "first_name", "Сим")
                        o_n = getattr(o_inf, "first_name", "Сим")
                        spark = {
                            "trigger_type": "music_performance",
                            "priority": 75,
                            "premise": f"{m_n} играет на музыкальном инструменте ({inst_name}), а {o_n} находится рядом в комнате.",
                            "participants": [m_inf, o_inf],
                        }
                        return True, f"{m_n} играет на {inst_name}, {o_n} слушает рядом", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов прямо сейчас не играет на музыкальном инструменте (пианино, гитара, скрипка, орган)"

            # 13.5. FITNESS_WORKOUT
            elif trigger_id == "fitness_workout":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                for f_sim, o_sim, f_inf, o_inf, f_act, o_act in [(sim_a, sim_b, info_a, info_b, act_a, act_b), (sim_b, sim_a, info_b, info_a, act_b, act_a)]:
                    is_fit, fit_detail = is_sim_working_out(f_sim, f_inf, f_act)
                    if is_fit:
                        f_n = getattr(f_inf, "first_name", "Сим")
                        o_n = getattr(o_inf, "first_name", "Сим")
                        spark = {
                            "trigger_type": "fitness_workout",
                            "priority": 73,
                            "premise": f"{f_n} тренируется ({fit_detail}), а {o_n} находится рядом.",
                            "participants": [f_inf, o_inf],
                        }
                        return True, f"{f_n} тренируется ({fit_detail}), {o_n} рядом", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов прямо сейчас не тренируется (беговая дорожка, тренажер, пресс, отжимания, йога)"

            # 13.6. TABLE_GAMES
            elif trigger_id == "table_games":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                is_tbl, game_type = are_sims_playing_table_game(sim_a, sim_b, act_a, act_b)
                if is_tbl:
                    spark = {
                        "trigger_type": "table_games",
                        "priority": 76,
                        "premise": f"{name_a} и {name_b} играют в {game_type} за одним столом.",
                        "participants": [info_a, info_b],
                    }
                    return True, f"{name_a} и {name_b} играют в {game_type} за одним столом", spark
                else:
                    if not last_fail_reason:
                        last_fail_reason = "Симы не играют вместе за игровым/шахматным столом"

            # 13.7. PET_CARE
            elif trigger_id == "pet_care":
                if not co_present:
                    last_fail_reason = f"Симы не в одной комнате/рядом ({space_type}, {dist:.1f}м)"
                    continue
                pet_res = detect_pet_care_in_scene(sim_a, sim_b, act_a, act_b)
                if pet_res is not None:
                    carer_inf, other_inf, pet_n, care_det = pet_res
                    c_n = getattr(carer_inf, "first_name", "Сим")
                    o_n = getattr(other_inf, "first_name", "Сим")
                    spark = {
                        "trigger_type": "pet_care",
                        "priority": 74,
                        "premise": f"{c_n} ухаживает за питомцем ({pet_n}, {care_det}), а {o_n} находится рядом в комнате.",
                        "participants": [carer_inf, other_inf],
                    }
                    return True, f"{c_n} ухаживает за питомцем {pet_n} ({care_det}), {o_n} рядом", spark
                else:
                    if not last_fail_reason:
                        last_fail_reason = "Ни один из симов не ухаживает за домашним питомцем прямо сейчас"

            # 13.8. WITNESS_DEATH
            elif trigger_id == "witness_death":
                from ai_social_pc.autonomous_director import (
                    detect_death_or_reaper_in_scene, is_grim_reaper,
                    find_dying_or_dead_sim_info, build_dead_sim_description
                )
                death_info = detect_death_or_reaper_in_scene(sim_a, sim_b, info_a, info_b, act_a, act_b)
                if death_info is not None:
                    dead_sim = find_dying_or_dead_sim_info(sim_a, sim_b)
                    is_reaper_scene = is_grim_reaper(info_a) or is_grim_reaper(info_b)
                    if is_reaper_scene:
                        survivor_info = info_a if not is_grim_reaper(info_a) else info_b
                        reaper_info = info_b if not is_grim_reaper(info_a) else info_a
                        s_name = getattr(survivor_info, "first_name", "Сим")
                        s_gender = getattr(getattr(survivor_info, "gender", None), "name", "MALE")
                        stayed_verb = "осталась" if s_gender == "FEMALE" else "остался"
                        him_her = "ей" if s_gender == "FEMALE" else "ему"
                        dead_desc = build_dead_sim_description(dead_sim, survivor_info, None)
                        premise = f"{s_name} в слезах и отчаянии {stayed_verb} один на один со Смертью после гибели {dead_desc}. {s_name} умоляет Костлявую Смерть о пощаде, а Смерть холодно отвечает {him_her}."
                        spark = {
                            "trigger_type": "witness_death",
                            "priority": 99,
                            "premise": premise,
                            "participants": [survivor_info, reaper_info],
                        }
                        return True, f"Один на один со Смертью: {s_name} умоляет о пощаде ({dead_desc})", spark
                    else:
                        dead_desc = build_dead_sim_description(dead_sim, info_a, info_b)
                        premise = f"{name_a} и {name_b} в слезах и шоке наблюдают гибель {dead_desc} и появление Смерти, пытаясь утешить друг друга."
                        spark = {
                            "trigger_type": "witness_death",
                            "priority": 98,
                            "premise": premise,
                            "participants": [info_a, info_b],
                        }
                        return True, f"Трагическое событие: гибель {dead_desc} рядом с {name_a} и {name_b}", spark
                else:
                    if not last_fail_reason:
                        last_fail_reason = "На участке нет погибающих персонажей, Костлявой Смерти или оплакиваемых надгробий"

            # 13.9. FIRE_HAZARD
            elif trigger_id == "fire_hazard":
                from ai_social_pc.autonomous_director import is_fire_active_on_lot, is_sim_reacting_to_fire
                if is_fire_active_on_lot() or is_sim_reacting_to_fire(sim_a, info_a, act_a) or is_sim_reacting_to_fire(sim_b, info_b, act_b):
                    fire_summary = "на участке пожар"
                    try:
                        from ai_thought_reader.context import get_fire_hazard_context
                        f_ctx = get_fire_hazard_context(info_a, other_sim_info=info_b, is_en=False)
                        if f_ctx and f_ctx.get("summary"):
                            fire_summary = f_ctx["summary"]
                    except Exception:
                        pass
                    premise = (
                        f"На участке возник пожар ({fire_summary}). "
                        f"Персонажи понимают, что начался пожар, их реакция, слова и поведение зависят от их характеров и отношений."
                    )
                    spark = {
                        "trigger_type": "fire_hazard",
                        "priority": 96,
                        "premise": premise,
                        "participants": [info_a, info_b],
                    }
                    return True, f"На участке активен пожар ({fire_summary})", spark
                else:
                    if not last_fail_reason:
                        last_fail_reason = "На участке нет активного пожара или паники от огня"

            # 13.10. SIM_IN_LABOR
            elif trigger_id == "sim_in_labor":
                from ai_social_pc.autonomous_director import is_sim_in_labor
                preg_details = []
                for mom_sim, other_sim, mom_inf, other_inf, m_act, o_act in [
                    (sim_a, sim_b, info_a, info_b, act_a, act_b),
                    (sim_b, sim_a, info_b, info_a, act_b, act_a)
                ]:
                    if is_sim_in_labor(mom_sim, mom_inf, m_act):
                        m_n = getattr(mom_inf, "first_name", "Сим")
                        o_n = getattr(other_inf, "first_name", "Сим")
                        m_gender = getattr(getattr(mom_inf, "gender", None), "name", "FEMALE")
                        is_male = (m_gender == "MALE")

                        is_alien = False
                        try:
                            from ai_thought_reader.config import get_experimental_flag
                            if is_male and get_experimental_flag("alien_male_pregnancy"):
                                is_alien = True
                        except Exception:
                            pass

                        if is_alien:
                            premise = (
                                f"ЧРЕЗВЫЧАЙНАЯ СИТУАЦИЯ: У {m_n} прямо сейчас начались схватки и внеземные роды (мудлет «Пора!»). "
                                f"Инопланетный малыш рождается сию секунду на глазах у {o_n}. "
                                f"Реакция, поведение и слова персонажей зависят исключительно от их характеров, отношений, мотивов и текущей обстановки."
                            )
                        else:
                            premise = (
                                f"ЧРЕЗВЫЧАЙНАЯ СИТУАЦИЯ: У {m_n} прямо сейчас начались болезненные схватки и роды (мудлет «Пора!»). "
                                f"Ребенок рождается сию секунду на глазах у {o_n}. "
                                f"Реакция, поведение и слова персонажей зависят исключительно от их характеров, отношений, мотивов и текущей обстановки."
                            )

                        spark = {
                            "trigger_type": "sim_in_labor",
                            "priority": 97,
                            "premise": premise,
                            "participants": [mom_inf, other_inf],
                        }
                        return True, f"У {m_n} начались роды/схватки (мудлет «Пора!»), {o_n} рядом", spark

                    try:
                        p_trk = getattr(mom_inf, "pregnancy_tracker", None)
                        is_preg = getattr(mom_inf, "is_pregnant", False) or (p_trk and getattr(p_trk, "is_pregnant", False))
                        if is_preg:
                            m_n = getattr(mom_inf, "first_name", "Сим")
                            from ai_thought_reader.context import get_sim_pregnancy_info
                            p_info = get_sim_pregnancy_info(mom_inf) or "беременен"
                            preg_details.append(f"{m_n} ({p_info})")
                    except Exception:
                        pass

                if not last_fail_reason:
                    if preg_details:
                        last_fail_reason = f"Персонаж беременен, но схватки/роды ещё не начались: {'; '.join(preg_details)}"
                    else:
                        last_fail_reason = "Ни один персонаж в паре не находится в состоянии схваток / родов (мудлет «Пора!»)"

            # 13.11. CAUGHT_CHEATING
            elif trigger_id == "caught_cheating":
                from ai_social_pc.autonomous_director import (
                    is_sim_in_romantic_relationship, get_sim_romantic_target,
                    update_romance_tracker, is_polyamorous_or_exempt_from_cheating
                )
                try:
                    update_romance_tracker()
                except Exception:
                    pass
                found_committed_pair = False
                for cheater_sim, partner_sim, cheater_inf, partner_inf in [
                    (sim_a, sim_b, info_a, info_b),
                    (sim_b, sim_a, info_b, info_a)
                ]:
                    if is_sim_in_romantic_relationship(partner_inf, cheater_inf):
                        found_committed_pair = True
                        try:
                            from ai_social_pc.autonomous_director import get_sim_buff_names_safe
                            c_buffs = get_sim_buff_names_safe(cheater_inf)
                            p_buffs = get_sim_buff_names_safe(partner_inf)
                            JEALOUS_TRIGS = ("boundary", "boundaries", "relationshipboundaries", "jealousy", "jealous", "cheatingwitnessed", "flirtwitnessed")
                            if any(any(jt in b for jt in JEALOUS_TRIGS) for b in c_buffs) and not any(any(jt in b for jt in JEALOUS_TRIGS) for b in p_buffs):
                                cheater_sim, partner_sim = partner_sim, cheater_sim
                                cheater_inf, partner_inf = partner_inf, cheater_inf
                        except Exception:
                            pass

                        third_party, act_verb = get_sim_romantic_target(cheater_sim, cheater_inf, partner_info=partner_inf)
                        if (
                            third_party
                            and getattr(third_party, "sim_id", 0) != getattr(partner_inf, "sim_id", 0)
                            and getattr(third_party, "sim_id", 0) != getattr(cheater_inf, "sim_id", 0)
                            and not is_polyamorous_or_exempt_from_cheating(cheater_inf, partner_inf, third_party)
                        ):
                            c_n = getattr(cheater_inf, "first_name", "Сим")
                            p_n = getattr(partner_inf, "first_name", "Сим")
                            t_n = getattr(third_party, "first_name", "другой персонаж")
                            action_phrase = f"{act_verb} с {t_n}" if "флирт" in act_verb else f"{act_verb} {t_n}"
                            spark = {
                                "trigger_type": "caught_cheating",
                                "priority": 93,
                                "premise": (
                                    f"ОСТРАЯ ДРАМА / ПРЕДАТЕЛЬСТВО: {p_n} прямо на своих глазах застает своего романтического партнёра ({c_n}), "
                                    f"который только что {action_phrase}."
                                ),
                                "participants": [partner_inf, cheater_inf],
                                "consume_romance_tracker_sim_id": getattr(cheater_inf, "sim_id", 0),
                                "cheating_action_verb": act_verb,
                                "third_party_name": t_n,
                            }
                            return True, f"{p_n} застает {c_n}: {action_phrase} (окно 8 мин)", spark
                if found_committed_pair:
                    last_fail_reason = "Пара состоит в отношениях (брак/романтика), но за последние 8 сим-минут не зафиксировано действие с третьим персонажем вне полиамории/открытых границ"
                elif not last_fail_reason:
                    last_fail_reason = "Симы не состоят в романтических отношениях (брак, помолвка, пара)"

            # 13.11b. WITNESSED_CHEATING
            elif trigger_id == "witnessed_cheating":
                from ai_social_pc.autonomous_director import (
                    find_all_committed_partners, find_sim_committed_partner, get_sim_romantic_target, update_romance_tracker,
                    get_sim_kinship_or_role_label, get_sim_relationship_scores, get_sim_sentiments_summary,
                    is_polyamorous_or_exempt_from_cheating
                )
                try:
                    update_romance_tracker()
                except Exception:
                    pass
                for witness_sim, cheater_sim, witness_inf, cheater_inf in [
                    (sim_a, sim_b, info_a, info_b),
                    (sim_b, sim_a, info_b, info_a)
                ]:
                    committed_partners = find_all_committed_partners(cheater_inf)
                    if committed_partners:
                        partner_ids = {getattr(p, "sim_id", 0) for p in committed_partners}
                        w_id = getattr(witness_inf, "sim_id", 0)
                        c_id = getattr(cheater_inf, "sim_id", 0)
                        if w_id not in partner_ids:
                            third_party, act_verb = get_sim_romantic_target(cheater_sim, cheater_inf, partner_info=None)
                            l_id = getattr(third_party, "sim_id", 0) if third_party else 0
                            betrayed_partners = [
                                p for p in committed_partners
                                if not is_polyamorous_or_exempt_from_cheating(cheater_inf, p, third_party)
                            ] if (third_party and l_id and l_id not in partner_ids and l_id != c_id and l_id != w_id) else []
                            if betrayed_partners:
                                partner_inf = betrayed_partners[0]
                                w_n = getattr(witness_inf, "first_name", "Сим")
                                c_n = getattr(cheater_inf, "first_name", "Сим")
                                p_n = getattr(partner_inf, "first_name", "Сим")
                                l_n = getattr(third_party, "first_name", "другой персонаж")

                                from ai_social_pc.autonomous_director import _sim_recent_romance_tracker, get_sim_now, get_sim_minutes_between
                                cur_now = get_sim_now()
                                mins_ago = 0
                                if c_id in _sim_recent_romance_tracker and cur_now is not None:
                                    t_st = _sim_recent_romance_tracker[c_id].get("timestamp")
                                    if t_st is not None:
                                        m = get_sim_minutes_between(t_st, cur_now)
                                        if m is not None:
                                            mins_ago = int(m)

                                if mins_ago <= 1:
                                    action_phrase = f"{act_verb} с {l_n}" if "флирт" in act_verb else f"{act_verb} {l_n}"
                                else:
                                    action_phrase = f"буквально {mins_ago} мин назад {act_verb} с {l_n}" if "флирт" in act_verb else f"буквально {mins_ago} мин назад {act_verb} {l_n}"
                                w_role_cheater = get_sim_kinship_or_role_label(witness_inf, cheater_inf)
                                w_role_partner = get_sim_kinship_or_role_label(witness_inf, partner_inf)
                                is_family = any(k in f"{w_role_cheater} {w_role_partner}".lower() for k in [
                                    "дочь", "сын", "мать", "отец", "сестра", "брат", "племян", "внук", "кузен", "родствен"
                                ])
                                w_role_desc = f"{w_role_cheater} персонажа {c_n}" if w_role_cheater else "свидетель"
                                if is_family and w_role_partner and w_role_partner != "знакомый":
                                    w_role_desc += f" (также {w_role_partner} персонажа {p_n})"

                                fw_c, rw_c = get_sim_relationship_scores(witness_inf, cheater_inf)
                                fw_p, _ = get_sim_relationship_scores(witness_inf, partner_inf)
                                fw_l, _ = get_sim_relationship_scores(witness_inf, third_party)
                                sent_c = get_sim_sentiments_summary(witness_inf, cheater_inf)
                                sent_p = get_sim_sentiments_summary(witness_inf, partner_inf)

                                partner_names_str = " и ".join(getattr(p, "first_name", "Партнёр") for p in betrayed_partners)
                                partner_word = "своих постоянных партнёров" if len(betrayed_partners) > 1 else "своего партнёра"
                                spark = {
                                    "trigger_type": "witnessed_cheating",
                                    "priority": 92,
                                    "premise": f"{w_n} ({w_role_desc}) замечает, как {c_n} {action_phrase} втайне от {partner_word} ({partner_names_str}).",
                                    "participants": [witness_inf, cheater_inf],
                                    "consume_romance_tracker_sim_id": c_id,
                                    "cheating_action_verb": act_verb,
                                    "cheater_name": c_n,
                                    "partner_name": p_n,
                                    "lover_name": l_n,
                                    "action_phrase": action_phrase,
                                    "witness_role_desc": w_role_desc,
                                    "witness_already_knows": False,
                                    "rel_context": {
                                        "fw_c": fw_c,
                                        "rw_c": rw_c,
                                        "fw_p": fw_p,
                                        "fw_l": fw_l,
                                        "sent_c": sent_c,
                                        "sent_p": sent_p,
                                        "role_cheater": w_role_cheater,
                                        "role_partner": w_role_partner,
                                    }
                                }
                                return True, f"{w_n} ({w_role_desc}) застает измену {c_n} с {l_n}", spark
                if not last_fail_reason:
                    last_fail_reason = "Свидетель не обнаружил факта недавней романтики персонажа с третьим лицом втайне от постоянного партнёра"

            # 13.11c. WALK_IN_INTIMACY
            elif trigger_id == "walk_in_intimacy":
                from ai_social_pc.autonomous_director import (
                    is_sim_in_romantic_relationship, _sim_recent_intimacy_tracker,
                    INTIMACY_WALK_IN_WINDOW_MINUTES, get_sim_now, get_sim_minutes_between,
                    is_polyamorous_or_exempt_from_cheating
                )
                cur_now = get_sim_now()
                for intruder_sim, actor_sim, intruder_inf, actor_inf in [
                    (sim_a, sim_b, info_a, info_b),
                    (sim_b, sim_a, info_b, info_a)
                ]:
                    a_id = getattr(actor_inf, "sim_id", 0)
                    intruder_id = getattr(intruder_inf, "sim_id", 0)
                    if not a_id or not intruder_id or a_id == intruder_id:
                        continue

                    intimacy_entry = _sim_recent_intimacy_tracker.get(a_id)
                    is_active = False
                    mins_ago = 0.0

                    if intimacy_entry is not None and cur_now is not None:
                        t_stamp = intimacy_entry.get("timestamp")
                        if t_stamp is not None:
                            mins_diff = get_sim_minutes_between(t_stamp, cur_now)
                            if mins_diff is not None and mins_diff <= INTIMACY_WALK_IN_WINDOW_MINUTES:
                                is_active = intimacy_entry.get("is_active", False)
                                mins_ago = mins_diff
                            else:
                                intimacy_entry = None
                        else:
                            intimacy_entry = None

                    if intimacy_entry is None:
                        sex_info = None
                        try:
                            from ai_thought_reader.context import get_sim_active_sex_info
                            sex_info = get_sim_active_sex_info(actor_inf)
                        except Exception:
                            sex_info = None

                        if not sex_info and actor_sim is not None and hasattr(actor_sim, "get_all_running_and_queued_interactions"):
                            try:
                                for inter in actor_sim.get_all_running_and_queued_interactions():
                                    aff_name = (getattr(getattr(inter, "affordance", None), "__name__", "") or "").lower()
                                    if any(k in aff_name for k in ("woohoo", "mess_around", "tryforbaby", "ww_sex")):
                                        target = getattr(inter, "target", None)
                                        t_info = getattr(target, "sim_info", target) if target else None
                                        t_id = getattr(t_info, "sim_id", 0)
                                        actor_ids = [a_id]
                                        if t_id and t_id != a_id:
                                            actor_ids.append(t_id)
                                        sex_info = {
                                            "actor_sim_ids": actor_ids,
                                            "total_participants": len(actor_ids),
                                            "location_and_privacy": space_type,
                                            "partners": getattr(t_info, "first_name", "") if t_info else ""
                                        }
                                        break
                            except Exception:
                                pass

                        if sex_info:
                            actor_ids = sex_info.get("actor_sim_ids", [a_id])
                            total_parts = len(actor_ids)
                            if total_parts <= 1:
                                scene_scale = "одиночная приватность (уединение / личное пространство)"
                            elif total_parts == 2:
                                scene_scale = "парная интимная сцена (вуху / пара)"
                            else:
                                scene_scale = f"групповая интимная сцена ({total_parts} участников)"
                            loc_phrase = sex_info.get("location_and_privacy") or space_type
                            intimacy_entry = {
                                "timestamp": cur_now,
                                "actor_ids": actor_ids,
                                "total_participants": total_parts,
                                "location_and_privacy": loc_phrase,
                                "scene_scale": scene_scale,
                                "is_active": True,
                            }
                            is_active = True
                            mins_ago = 0.0

                    if intimacy_entry is not None:
                        actor_ids = intimacy_entry.get("actor_ids", [a_id])
                        if intruder_id not in actor_ids:
                            total_parts = intimacy_entry.get("total_participants", len(actor_ids))
                            scene_scale = intimacy_entry.get("scene_scale", "интимная сцена")
                            loc_phrase = intimacy_entry.get("location_and_privacy", space_type)

                            sim_mgr = getattr(services, "sim_info_manager", lambda: None)() if services is not None else None
                            betrayed_by_sim = None
                            if sim_mgr and len(actor_ids) >= 2:
                                for act_id in actor_ids:
                                    act_inf = sim_mgr.get(act_id)
                                    if act_inf and is_sim_in_romantic_relationship(intruder_inf, act_inf):
                                        has_non_exempt_lover = False
                                        for other_id in actor_ids:
                                            if other_id != act_id:
                                                other_inf = sim_mgr.get(other_id)
                                                if not is_polyamorous_or_exempt_from_cheating(act_inf, intruder_inf, other_inf):
                                                    has_non_exempt_lover = True
                                                    break
                                        if has_non_exempt_lover:
                                            betrayed_by_sim = act_inf
                                            break

                            i_n = getattr(intruder_inf, "first_name", "Сим")
                            a_n = getattr(actor_inf, "first_name", "Сим")
                            timing_desc = "прямо сейчас в процессе" if is_active else f"только что (буквально {int(mins_ago)} мин назад)"

                            if betrayed_by_sim:
                                b_n = getattr(betrayed_by_sim, "first_name", "Сим")
                                premise = f"{i_n} заходит в комнату и застаёт своего партнёра ({b_n}) во время уединения ({scene_scale})."
                                prio = 94
                            else:
                                premise = f"{i_n} неожиданно заходит и застаёт {a_n} во время уединения ({scene_scale})."
                                prio = 91

                            spark = {
                                "trigger_type": "walk_in_intimacy",
                                "priority": prio,
                                "premise": premise,
                                "participants": [intruder_inf, actor_inf],
                                "consume_intimacy_tracker_sim_id": a_id,
                                "total_participants": total_parts,
                                "scene_scale": scene_scale,
                                "loc_phrase": loc_phrase,
                                "betrayed_partner_name": getattr(betrayed_by_sim, "first_name", "") if betrayed_by_sim else "",
                                "is_betrayal": bool(betrayed_by_sim),
                                "intruder_name": i_n,
                                "actor_name": a_n,
                                "is_active": is_active,
                                "mins_ago": int(mins_ago),
                            }
                            return True, f"{i_n} застает {a_n} ({scene_scale}, {timing_desc})", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один сим не находится в активной интимной/приватной сцене и не завершал её в последние 8 сим-минут"

            # 13.12. ELECTROCUTED_REPAIR
            elif trigger_id == "electrocuted_repair":
                from ai_social_pc.autonomous_director import is_sim_electrocuted
                for shocked_sim, other_sim, shocked_inf, other_inf, s_act, o_act in [
                    (sim_a, sim_b, info_a, info_b, act_a, act_b),
                    (sim_b, sim_a, info_b, info_a, act_b, act_a)
                ]:
                    if is_sim_electrocuted(shocked_sim, shocked_inf, s_act):
                        s_n = getattr(shocked_inf, "first_name", "Сим")
                        o_n = getattr(other_inf, "first_name", "Сим")
                        spark = {
                            "trigger_type": "electrocuted_repair",
                            "priority": 89,
                            "premise": (
                                f"ПРОИСШЕСТВИЕ: {s_n} только что получил мощный удар электрическим током при починке техники "
                                f"(находится в ошалевшем состоянии, покрыт копотью) прямо на глазах у {o_n}. "
                                f"Слова и реакция персонажей зависят исключительно от их характеров, отношений и текущей обстановки."
                            ),
                            "participants": [other_inf, shocked_inf],
                        }
                        return True, f"{s_n} получил удар током при ремонте, {o_n} осматривает", spark
                if not last_fail_reason:
                    last_fail_reason = "Ни один из симов не получил удар током (нет опаленности или мудлета ошалелости от тока)"

            # 13.13. PAID_BILLS
            elif trigger_id == "paid_bills":
                from ai_social_pc.autonomous_director import _sim_bills_paid_tracker, get_sim_minutes_between, get_sim_now
                if age_a in ("TEEN", "YOUNGADULT", "ADULT", "ELDER") and age_b in ("TEEN", "YOUNGADULT", "ADULT", "ELDER"):
                    cur_now = get_sim_now()
                    for payer_sim, other_sim, payer_inf, other_inf, p_act, o_act in [
                        (sim_a, sim_b, info_a, info_b, act_a, act_b),
                        (sim_b, sim_a, info_b, info_a, act_b, act_a)
                    ]:
                        p_id = payer_inf.sim_id
                        paid_time = _sim_bills_paid_tracker.get(p_id)
                        is_paying_now = any(k in p_act for k in ["оплачивает счета", "оплачивает счет", "платит по счетам", "счета за дом"])
                        mins_since = get_sim_minutes_between(paid_time, cur_now) if (paid_time and cur_now) else None
                        if is_paying_now or (mins_since is not None and mins_since <= 60.0):
                            p_n = getattr(payer_inf, "first_name", "Сим")
                            o_n = getattr(other_inf, "first_name", "Сим")
                            spark = {
                                "trigger_type": "paid_bills",
                                "priority": 86,
                                "premise": (
                                    f"ФИНАНСЫ И СЧЕТА: {p_n} оплатил счета за дом и поднимает тему бюджета с {o_n}. "
                                    f"Тон разговора и реакция персонажей зависят от их благосостояния, черт характера (бережливость, расточительность, эгоизм) и отношений."
                                ),
                                "participants": [payer_inf, other_inf],
                                "consume_bills_tracker_sim_id": p_id,
                            }
                            return True, f"{p_n} оплатил счета за дом, {o_n} рядом", spark
                    if not last_fail_reason:
                        last_fail_reason = "Ни один из симов не оплачивал счета за последний час (окно 60 мин)"
                else:
                    if not last_fail_reason:
                        last_fail_reason = f"Оба сима должны быть от подростка и старше ({name_a}: {age_a}, {name_b}: {age_b})"

            # 14. AMBIENT_LIVING_ROOM
            elif trigger_id == "ambient_living_room":
                if co_present:
                    spark = {
                        "trigger_type": "ambient_living_room",
                        "priority": 70,
                        "premise": f"{name_a} и {name_b} находятся рядом в одном пространстве ({space_type}), занимаясь повседневными делами.",
                        "participants": [info_a, info_b]
                    }
                    return True, f"{name_a} и {name_b} рядом ({space_type}, {dist:.1f}м)", spark

        if active_sim is not None and (sim_a == active_sim or sim_b == active_sim):
            if last_fail_reason and (not active_sim_fail_reason or "не рядом" in active_sim_fail_reason):
                active_sim_fail_reason = last_fail_reason

    # Fallback reason
    final_fail = active_sim_fail_reason or last_fail_reason or "Условия не выполнены (нет подходящей пары или занятия)"
    return False, final_fail, None


def generate_forced_trigger_spark(trigger_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generates a forced spark for testing trigger_id immediately with Sims on lot,
    even if natural preconditions are not active right now.
    Returns: (is_success, details_string, spark_dict)
    """
    sims = get_household_sim_instances()
    if len(sims) < 2:
        return False, "На участке меньше двух симов из семьи для генерации сцены", None

    sim_a, sim_b = sims[0], sims[1]
    info_a, info_b = sim_a.sim_info, sim_b.sim_info
    name_a = getattr(info_a, "first_name", "Сим 1")
    name_b = getattr(info_b, "first_name", "Сим 2")
    sim_c = sims[2] if len(sims) > 2 else None
    info_c = getattr(sim_c, "sim_info", None) if sim_c else None
    name_c = getattr(info_c, "first_name", "Третий персонаж") if info_c else "тайный возлюбленный"

    tid = str(trigger_id).strip().lower()

    if tid == "witnessed_cheating":
        from ai_social_pc.autonomous_director import (
            find_sim_committed_partner, get_sim_kinship_or_role_label,
            get_sim_relationship_scores, get_sim_sentiments_summary
        )
        witness_inf = info_a
        cheater_inf = info_b
        partner_inf = find_sim_committed_partner(cheater_inf) or (info_c if info_c else info_a)
        third_party = info_c if info_c else info_a
        w_n = name_a
        c_n = name_b
        p_n = getattr(partner_inf, "first_name", "Партнёр")
        l_n = name_c

        w_role_cheater = get_sim_kinship_or_role_label(witness_inf, cheater_inf)
        w_role_partner = get_sim_kinship_or_role_label(witness_inf, partner_inf)
        w_role_desc = f"{w_role_cheater} персонажа {c_n}" if w_role_cheater else "свидетель"
        if w_role_partner and w_role_partner != "знакомый":
            w_role_desc += f" (также {w_role_partner} персонажа {p_n})"

        fw_c, rw_c = get_sim_relationship_scores(witness_inf, cheater_inf)
        fw_p, _ = get_sim_relationship_scores(witness_inf, partner_inf)
        fw_l, _ = get_sim_relationship_scores(witness_inf, third_party)
        sent_c = get_sim_sentiments_summary(witness_inf, cheater_inf)
        sent_p = get_sim_sentiments_summary(witness_inf, partner_inf)

        action_phrase = f"поцеловал {l_n}"
        spark = {
            "trigger_type": "witnessed_cheating",
            "priority": 92,
            "premise": f"{w_n} ({w_role_desc}) замечает, как {c_n} {action_phrase} втайне от своего партнёра ({p_n}).",
            "participants": [witness_inf, cheater_inf],
            "cheating_action_verb": "поцеловал",
            "cheater_name": c_n,
            "partner_name": p_n,
            "lover_name": l_n,
            "witness_name": w_n,
            "witness_role_desc": w_role_desc,
            "mins_ago": 0,
            "is_active": True,
            "witness_already_knows": False,
            "rel_context": {
                "fw_c": fw_c,
                "rw_c": rw_c,
                "fw_p": fw_p,
                "fw_l": fw_l,
                "sent_c": sent_c,
                "sent_p": sent_p,
                "role_cheater": w_role_cheater,
                "role_partner": w_role_partner,
            }
        }
        return True, f"Принудительный тест: {w_n} ({w_role_desc}) застает измену {c_n} с {l_n}", spark

    elif tid == "walk_in_intimacy":
        from ai_social_pc.autonomous_director import is_sim_in_romantic_relationship
        intruder_inf = info_a
        actor_inf = info_b
        i_n = name_a
        a_n = name_b
        scene_scale = "парная интимная сцена (вуху / пара)"
        loc_phrase = "в комнате"
        timing_desc = "прямо сейчас в процессе"
        betrayed = is_sim_in_romantic_relationship(intruder_inf, actor_inf)

        if betrayed:
            premise = f"{i_n} заходит в комнату и застаёт своего партнёра ({a_n}) во время уединения ({scene_scale})."
            prio = 94
        else:
            premise = f"{i_n} неожиданно заходит и застаёт {a_n} во время уединения ({scene_scale})."
            prio = 91

        spark = {
            "trigger_type": "walk_in_intimacy",
            "priority": prio,
            "premise": premise,
            "participants": [intruder_inf, actor_inf],
            "total_participants": 2,
            "scene_scale": scene_scale,
            "loc_phrase": loc_phrase,
            "betrayed_partner_name": a_n if betrayed else "",
            "is_betrayal": betrayed,
            "intruder_name": i_n,
            "actor_name": a_n,
            "is_active": True,
            "mins_ago": 0,
        }
        return True, f"Принудительный тест: {i_n} застает {a_n} ({scene_scale})", spark

    elif tid in ("relative_homework_together", "guest_homework_together", "homework_in_progress"):
        from ai_social_pc.autonomous_director import is_sim_doing_homework, is_sim_helping_with_homework
        from ai_thought_reader.context import get_current_activity
        hw_sims = [s for s in sims if is_sim_doing_homework(s, getattr(s, "sim_info", None), (get_current_activity(getattr(s, "sim_info", None)) or ""))]
        if len(hw_sims) >= 2:
            s_a, s_b = hw_sims[0], hw_sims[1]
        elif len(hw_sims) == 1 and len(sims) >= 2:
            s_a = hw_sims[0]
            other_sims = [s for s in sims if s != s_a]
            adults_or_young = [s for s in other_sims if get_sim_age_category(getattr(s, "sim_info", None)) in ("YOUNGADULT", "ADULT", "ELDER", "CHILD", "TEEN")]
            s_b = adults_or_young[0] if adults_or_young else other_sims[0]
        else:
            young_sims = [s for s in sims if get_sim_age_category(getattr(s, "sim_info", None)) in ("CHILD", "TEEN")]
            if len(young_sims) >= 2:
                s_a, s_b = young_sims[0], young_sims[1]
            elif len(young_sims) == 1 and len(sims) >= 2:
                s_a = young_sims[0]
                s_b = [s for s in sims if s != s_a][0]
            else:
                s_a, s_b = sim_a, sim_b
        inf_a, inf_b = s_a.sim_info, s_b.sim_info
        n_a = getattr(inf_a, "first_name", "Сим 1")
        n_b = getattr(inf_b, "first_name", "Сим 2")
        title = "Домашка в процессе" if tid == "homework_in_progress" else "Делать уроки вместе"
        prio = 78 if tid == "homework_in_progress" else 88
        spark = {
            "trigger_type": tid,
            "priority": prio,
            "premise": f"[ПРИНУДИТЕЛЬНЫЙ ТЕСТ] Персонажи {n_a} и {n_b}: совместное выполнение школьного домашнего задания.",
            "participants": [inf_a, inf_b]
        }
        return True, f"Принудительный запуск действия '{title}' между {n_a} и {n_b}", spark

    elif tid == "homework_done":
        from ai_social_pc.autonomous_director import is_sim_homework_completed
        young_sims = [s for s in sims if get_sim_age_category(getattr(s, "sim_info", None)) in ("CHILD", "TEEN")]
        done_young = [s for s in young_sims if is_sim_homework_completed(getattr(s, "sim_info", None), s)]
        c_sim = done_young[0] if done_young else (young_sims[0] if young_sims else sim_a)
        other_sims = [s for s in sims if s != c_sim]
        o_sim = other_sims[0] if other_sims else sim_b
        c_inf, o_inf = c_sim.sim_info, o_sim.sim_info
        c_n = getattr(c_inf, "first_name", "Школьник")
        o_n = getattr(o_inf, "first_name", "Сим")
        spark = {
            "trigger_type": "homework_done",
            "priority": 76,
            "premise": f"[ПРИНУДИТЕЛЬНЫЙ ТЕСТ] {c_n} сделал все школьные домашние задания, а {o_n} находится рядом в комнате.",
            "participants": [c_inf, o_inf]
        }
        return True, f"Принудительный запуск действия 'Домашка сделана' между {c_n} и {o_n}", spark

    elif tid == "homework_not_done":
        young_sims = [s for s in sims if get_sim_age_category(getattr(s, "sim_info", None)) in ("CHILD", "TEEN")]
        c_sim = young_sims[0] if young_sims else sim_b
        adult_sims = [s for s in sims if s != c_sim and get_sim_age_category(getattr(s, "sim_info", None)) in ("YOUNGADULT", "ADULT", "ELDER")]
        p_sim = adult_sims[0] if adult_sims else ([s for s in sims if s != c_sim][0] if len(sims) > 1 else sim_a)
        p_inf, c_inf = p_sim.sim_info, c_sim.sim_info
        p_n = getattr(p_inf, "first_name", "Родитель")
        c_n = getattr(c_inf, "first_name", "Школьник")
        spark = {
            "trigger_type": "homework_not_done",
            "priority": 80,
            "premise": f"[ПРИНУДИТЕЛЬНЫЙ ТЕСТ] {c_n} еще не сделал школьное домашнее задание, а {p_n} находится рядом в комнате.",
            "participants": [p_inf, c_inf]
        }
        return True, f"Принудительный запуск действия 'Домашка не сделана' между {p_n} и {c_n}", spark

    elif tid == "service_repairman_done":
        spark = {
            "trigger_type": "service_repairman_done",
            "priority": 88,
            "premise": f"Мастер по ремонту {name_a} сообщает {name_b} об успешной починке техники или сантехники. Услуга мастера уже полностью оплачена клиентом при вызове — никаких счетов, требований денег или выдуманных цен! Мастер лишь коротко отчитывается о сделанном, даёт бытовой совет по уходу за приборами или вежливо прощается.",
            "participants": [info_a, info_b]
        }
        return True, f"Принудительный запуск отчёта мастера {name_a} перед {name_b}", spark

    elif tid == "community_ambient_social":
        from ai_social_pc.autonomous_director import is_sim_active_guest, is_sim_available, get_current_venue_info
        npc_sims = []
        if services is not None and hasattr(services, "sim_info_manager"):
            sim_mgr = services.sim_info_manager()
            if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                for inst in sim_mgr.instanced_sims_gen():
                    s_inf = getattr(inst, "sim_info", None)
                    if s_inf and not getattr(s_inf, "is_pet", False) and not is_sim_active_guest(s_inf) and is_sim_available(inst):
                        npc_sims.append(inst)
        if len(npc_sims) >= 2:
            from ai_social_pc.autonomous_director import get_distance_between_sims
            best_pair = None
            best_dist = 999999.0
            for i in range(len(npc_sims)):
                for j in range(i + 1, len(npc_sims)):
                    d = get_distance_between_sims(npc_sims[i], npc_sims[j])
                    if d is not None and d < best_dist:
                        best_dist = d
                        best_pair = (npc_sims[i], npc_sims[j])
            if best_pair is not None:
                s_a, s_b = best_pair
            else:
                s_a, s_b = npc_sims[0], npc_sims[1]
            inf_a, inf_b = s_a.sim_info, s_b.sim_info
            n_a = getattr(inf_a, "first_name", "Посетитель 1")
            n_b = getattr(inf_b, "first_name", "Посетитель 2")
            v_info = get_current_venue_info()
            v_name = v_info.get("venue_name", "заведение")
            spark = {
                "trigger_type": "community_ambient_social",
                "priority": 40,
                "premise": f"[ТЕСТ] Посетители {n_a} и {n_b} находятся рядом в заведении ({v_name}). Разговор двух посетителей: впечатления от места, личные новости или сплетни.",
                "participants": [inf_a, inf_b]
            }
            return True, f"Принудительный запуск фоновой беседы NPC {n_a} и {n_b}", spark
        return False, f"На общественном участке найдено меньше двух доступных NPC (найдено: {len(npc_sims)})", None

    elif tid == "community_player_social":
        from ai_social_pc.autonomous_director import is_sim_active_guest, is_sim_available, get_current_venue_info, get_distance_between_sims
        client = services.client_manager().get_first_client() if hasattr(services, "client_manager") else None
        p_sim = getattr(client, "active_sim", None) if client else (sims[0] if sims else None)
        other_sim = None
        best_d = 999999.0
        if services is not None and hasattr(services, "sim_info_manager"):
            sim_mgr = services.sim_info_manager()
            if sim_mgr and hasattr(sim_mgr, "instanced_sims_gen"):
                for inst in sim_mgr.instanced_sims_gen():
                    if inst is not p_sim and is_sim_available(inst):
                        s_inf = getattr(inst, "sim_info", None)
                        if s_inf and not getattr(s_inf, "is_pet", False):
                            d = get_distance_between_sims(p_sim, inst) if p_sim else 0.0
                            if d is not None and d < best_d:
                                best_d = d
                                other_sim = inst
        if p_sim and other_sim:
            inf_a, inf_b = p_sim.sim_info, other_sim.sim_info
            n_a = getattr(inf_a, "first_name", "Игрок")
            n_b = getattr(inf_b, "first_name", "Собеседник")
            v_info = get_current_venue_info()
            v_name = v_info.get("venue_name", "заведение")
            spark = {
                "trigger_type": "community_player_social",
                "priority": 80,
                "premise": f"[ТЕСТ] {n_a} и {n_b} находятся рядом в заведении ({v_name}). Живой диалог: обсуждение атмосферы места, отдыха, напитков или событий вокруг.",
                "participants": [inf_a, inf_b]
            }
            return True, f"Принудительный запуск диалога игрока {n_a} с {n_b}", spark
        return False, "Не найден второй персонаж на участке для диалога с игроком", None

    # For any other trigger: try natural evaluation first, else make standard spark
    is_met, details, sp = evaluate_trigger_conditions(tid)
    if is_met and sp:
        return True, details, sp

    meta = TRIGGER_MAP.get(tid, {})
    title = meta.get("name_ru", tid)
    premise_def = meta.get("requirements_ru", f"Событие {title} между {name_a} и {name_b}")
    spark = {
        "trigger_type": tid,
        "priority": meta.get("prio", 85),
        "premise": f"[ТЕСТ] {name_a} и {name_b}: {premise_def}",
        "participants": [info_a, info_b]
    }
    try:
        from ai_social_pc.autonomous_director import find_nearby_joinable_sims
        nearby = find_nearby_joinable_sims(sim_a, sim_b, max_count=6)
        spark["nearby_sims"] = nearby
        spark["all_scene_sims"] = [info_a, info_b] + nearby
    except Exception:
        pass
    return True, f"Принудительный запуск действия '{title}' между {name_a} и {name_b}", spark


# =========================================================================
# GLOBAL SCANNER: SCAN ALL TRIGGERS AT ONCE
# =========================================================================

def scan_all_triggers_report() -> List[Dict[str, Any]]:
    """
    Scans every single trigger in DIRECTOR_TRIGGERS and evaluates its status.
    Returns list of dicts: {'id', 'name_ru', 'is_met', 'details'}
    """
    results = []
    for trig in DIRECTOR_TRIGGERS:
        tid = trig["id"]
        name = trig["name_ru"]
        try:
            is_met, details, _ = evaluate_trigger_conditions(tid)
            results.append({
                "id": tid,
                "name": name,
                "is_met": is_met,
                "details": details
            })
        except Exception as e:
            results.append({
                "id": tid,
                "name": name,
                "is_met": False,
                "details": f"Ошибка проверки: {e}"
            })
    return results


# =========================================================================
# IN-GAME UI MENU: TOGGLE TRIGGERS FOR ISOLATED TESTING
# =========================================================================

def show_director_test_menu(owner_sim_info=None, current_mode=None):
    """
    Renders an in-game UI ItemPicker menu to toggle Director actions for testing.
    Supports 3 modes:
    - MODE_HOME: Домашний участок (32 triggers)
    - MODE_VISITING_FRIENDS: В гостях у друзей (8 triggers)
    - MODE_VISITING_RELATIVES: В гостях у родственников (8 triggers)
    When current_mode is None, renders the root Mode Hub.
    When a mode is selected, renders that mode's trigger list with a back button.
    """
    try:
        from ai_thought_reader.ui_dialogs import show_picker_dialog
    except ImportError:
        log("[DIRECTOR TEST] show_picker_dialog is not available in this environment.", level="ERROR")
        return

    if owner_sim_info is None:
        if services is not None and hasattr(services, "active_sim_info"):
            try:
                owner_sim_info = services.active_sim_info()
            except Exception:
                owner_sim_info = None

    if owner_sim_info is None:
        sims = get_household_sim_instances()
        if sims:
            owner_sim_info = getattr(sims[0], "sim_info", None)

    if owner_sim_info is None:
        log("[DIRECTOR TEST] Cannot open menu: active SimInfo not found.", level="WARN")
        return

    # Normalization of current_mode
    if current_mode:
        cm_norm = str(current_mode).strip().upper()
        if cm_norm in (MODE_HOME, "HOME", "ДОМ", "ДОМАШНИЙ"):
            current_mode = MODE_HOME
        elif cm_norm in (MODE_NPC_HOME, "NPC_HOME", "NPC", "НПС", "ГОСТИ", "GUESTS", "GUEST"):
            current_mode = MODE_NPC_HOME
        elif cm_norm in (MODE_VISITING_FRIENDS, "FRIENDS", "ДРУЗЬЯ", "ДРУГ"):
            current_mode = MODE_VISITING_FRIENDS
        elif cm_norm in (MODE_VISITING_RELATIVES, "RELATIVES", "РОДНЯ", "РОДСТВЕННИКИ"):
            current_mode = MODE_VISITING_RELATIVES
        elif cm_norm in (MODE_COMMUNITY, "COMMUNITY", "ОБЩЕСТВЕННЫЙ", "ОБЩЕСТВЕННЫЕ", "ЗАВЕДЕНИЕ", "VENUE"):
            current_mode = MODE_COMMUNITY
        else:
            current_mode = None

    rows = []

    # SCREEN 1: ROOT MODE HUB
    if current_mode is None:
        home_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode", MODE_HOME) == MODE_HOME]
        npc_home_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode") == MODE_NPC_HOME]
        friends_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode") == MODE_VISITING_FRIENDS]
        rel_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode") == MODE_VISITING_RELATIVES]
        comm_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode") == MODE_COMMUNITY]

        home_on = sum(1 for t in home_triggers if TRIGGER_TOGGLES.get(t["id"], False))
        npc_home_on = sum(1 for t in npc_home_triggers if TRIGGER_TOGGLES.get(t["id"], False))
        friends_on = sum(1 for t in friends_triggers if TRIGGER_TOGGLES.get(t["id"], False))
        rel_on = sum(1 for t in rel_triggers if TRIGGER_TOGGLES.get(t["id"], False))
        comm_on = sum(1 for t in comm_triggers if TRIGGER_TOGGLES.get(t["id"], False))
        total_on = home_on + npc_home_on + friends_on + rel_on + comm_on
        total_all = len(DIRECTOR_TRIGGERS)

        rows.append((
            f"[РЕЖИМ: ДОМАШНИЙ УЧАСТОК (СЕМЬЯ)] ({home_on}/{len(home_triggers)} ВКЛ)",
            f"{len(home_triggers)} сценариев | Базовые ситуации для родного дома активной семьи",
            "__GOTO_HOME__",
            False
        ))
        rows.append((
            f"[РЕЖИМ: ГОСТИ И NPC НА УЧАСТКЕ] ({npc_home_on}/{len(npc_home_triggers)} ВКЛ)",
            f"{len(npc_home_triggers)} сценариев | Встреча гостей, соседи, услуги (няня, мастер, уборка), NPC-NPC",
            "__GOTO_NPC_HOME__",
            False
        ))
        rows.append((
            f"[РЕЖИМ: В ГОСТЯХ У ДРУЗЕЙ] ({friends_on}/{len(friends_triggers)} ВКЛ)",
            f"{len(friends_triggers)} сценариев | Поведение и диалоги в гостях у друзей и знакомых",
            "__GOTO_FRIENDS__",
            False
        ))
        rows.append((
            f"[РЕЖИМ: В ГОСТЯХ У РОДСТВЕННИКОВ] ({rel_on}/{len(rel_triggers)} ВКЛ)",
            f"{len(rel_triggers)} сценариев | Поведение и диалоги в гостях у родни и родственников",
            "__GOTO_RELATIVES__",
            False
        ))
        rows.append((
            f"[РЕЖИМ: ОБЩЕСТВЕННЫЕ УЧАСТКИ] ({comm_on}/{len(comm_triggers)} ВКЛ)",
            f"{len(comm_triggers)} сценариев | Бары, кафе, спортзал, ресторан, библиотека, фоновое общение",
            "__GOTO_COMMUNITY__",
            False
        ))
        rows.append((
            "[ВКЛ ВСЕ ВЕЗДЕ] Включить все действия",
            f"Включает абсолютно все {total_all} сценариев Режиссёра во всех режимах",
            "__ALL_ON__",
            False
        ))
        rows.append((
            "[ВЫКЛ ВСЕ ВЕЗДЕ] Отключить все (Режим теста)",
            "Отключает все действия во всех режимах. Включайте ровно 1 для чистого теста!",
            "__ALL_OFF__",
            False
        ))
        rows.append((
            "[СБРОС ТАЙМЕРОВ] Обнулить паузы и лимиты",
            "Сбрасывает паузы тишины дома, кулдауны пар и суточные ограничения (мгновенный старт)",
            "__RESET_COOLDOWNS__",
            False
        ))

        def _on_root_select(selected_tag):
            if not selected_tag:
                return
            if selected_tag == "__GOTO_HOME__":
                show_director_test_menu(owner_sim_info, current_mode=MODE_HOME)
            elif selected_tag == "__GOTO_NPC_HOME__":
                show_director_test_menu(owner_sim_info, current_mode=MODE_NPC_HOME)
            elif selected_tag == "__GOTO_FRIENDS__":
                show_director_test_menu(owner_sim_info, current_mode=MODE_VISITING_FRIENDS)
            elif selected_tag == "__GOTO_RELATIVES__":
                show_director_test_menu(owner_sim_info, current_mode=MODE_VISITING_RELATIVES)
            elif selected_tag == "__GOTO_COMMUNITY__":
                show_director_test_menu(owner_sim_info, current_mode=MODE_COMMUNITY)
            elif selected_tag == "__ALL_ON__":
                enable_all_triggers(True)
                log("[DIRECTOR TEST] All triggers everywhere ENABLED.")
                show_director_test_menu(owner_sim_info, current_mode=None)
            elif selected_tag == "__ALL_OFF__":
                enable_all_triggers(False)
                log("[DIRECTOR TEST] All triggers everywhere DISABLED (Test Mode).")
                show_director_test_menu(owner_sim_info, current_mode=None)
            elif selected_tag == "__RESET_COOLDOWNS__":
                try:
                    from ai_social_pc.autonomous_director import reset_all_cooldowns
                    reset_all_cooldowns()
                except Exception:
                    pass
                log("[DIRECTOR TEST] Cooldowns reset via root menu.")
                show_director_test_menu(owner_sim_info, current_mode=None)

        title = f"Режиссёр: Выбор режима ({total_on}/{total_all} ВКЛ)"
        desc = "Выберите режим локации для настройки и тестирования триггеров Режиссёра:"
        show_picker_dialog(owner_sim_info, title, desc, rows, _on_root_select)
        return

    # SCREEN 2: SUBMENU FOR SPECIFIC MODE
    mode_triggers = [t for t in DIRECTOR_TRIGGERS if t.get("mode", MODE_HOME) == current_mode]
    mode_active = sum(1 for t in mode_triggers if TRIGGER_TOGGLES.get(t["id"], False))
    total_in_mode = len(mode_triggers)

    if current_mode == MODE_HOME:
        mode_label = "Домашний участок (Семья)"
    elif current_mode == MODE_NPC_HOME:
        mode_label = "Гости и NPC на участке"
    elif current_mode == MODE_VISITING_FRIENDS:
        mode_label = "В гостях у друзей"
    elif current_mode == MODE_VISITING_RELATIVES:
        mode_label = "В гостях у родственников"
    elif current_mode == MODE_COMMUNITY:
        mode_label = "Общественные участки"
    else:
        mode_label = "Выбранный режим"

    rows.append((
        "[< НАЗАД] К выбору режимов",
        "Вернуться в главное меню выбора режимов Режиссёра",
        "__BACK__",
        False
    ))
    rows.append((
        f"[ВКЛ ВСЕ В РЕЖИМЕ] Включить все ({total_in_mode})",
        f"Включает все сценарии режима «{mode_label}»",
        "__MODE_ALL_ON__",
        False
    ))
    rows.append((
        f"[ВЫКЛ ВСЕ В РЕЖИМЕ] Отключить все ({total_in_mode})",
        f"Отключает все сценарии режима «{mode_label}» (Режим теста)",
        "__MODE_ALL_OFF__",
        False
    ))
    rows.append((
        "[СБРОС ТАЙМЕРОВ] Обнулить паузы и лимиты",
        "Сбрасывает паузы тишины дома, кулдауны пар и суточные ограничения (мгновенный старт)",
        "__RESET_COOLDOWNS__",
        False
    ))

    for trig in mode_triggers:
        tid = trig["id"]
        is_on = TRIGGER_TOGGLES.get(tid, False)
        status_tag = "[ВКЛ]" if is_on else "[ВЫКЛ]"
        prio_val = trig.get("prio", 70)
        row_title = f"{status_tag} {trig['name_ru']}"
        row_desc = f"ID: {tid} | {trig['category']} | Прио: {prio_val} | {trig.get('requirements_ru', '')}"
        rows.append((row_title, row_desc, tid, False))

    def _on_mode_select(selected_tag):
        if not selected_tag:
            return
        if selected_tag == "__BACK__":
            show_director_test_menu(owner_sim_info, current_mode=None)
        elif selected_tag == "__MODE_ALL_ON__":
            enable_triggers_by_mode(current_mode, True)
            log(f"[DIRECTOR TEST] Mode {current_mode} all triggers ENABLED.")
            show_director_test_menu(owner_sim_info, current_mode=current_mode)
        elif selected_tag == "__MODE_ALL_OFF__":
            enable_triggers_by_mode(current_mode, False)
            log(f"[DIRECTOR TEST] Mode {current_mode} all triggers DISABLED.")
            show_director_test_menu(owner_sim_info, current_mode=current_mode)
        elif selected_tag == "__RESET_COOLDOWNS__":
            try:
                from ai_social_pc.autonomous_director import reset_all_cooldowns
                reset_all_cooldowns()
            except Exception:
                pass
            log("[DIRECTOR TEST] Cooldowns reset via mode menu.")
            show_director_test_menu(owner_sim_info, current_mode=current_mode)
        elif selected_tag in TRIGGER_MAP:
            new_val = toggle_trigger(selected_tag)
            t_name = TRIGGER_MAP[selected_tag]["name_ru"]
            status_word = "ВКЛЮЧЕНО" if new_val else "ВЫКЛЮЧЕНО"
            log(f"[DIRECTOR TEST] {t_name} ({selected_tag}) -> {status_word}")
            show_director_test_menu(owner_sim_info, current_mode=current_mode)

    title = f"{mode_label} ({mode_active}/{total_in_mode} ВКЛ)"
    desc = f"Выберите действие для переключения [ВКЛ] / [ВЫКЛ]. Режим: {mode_label}."
    show_picker_dialog(owner_sim_info, title, desc, rows, _on_mode_select)

