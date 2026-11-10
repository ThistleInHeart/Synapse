import os
import json
import threading
from urllib.parse import quote, unquote
from typing import Dict, Any, Optional
from ai_thought_reader.logger import log, log_exception

try:
    from ai_thought_reader.lore_manager import get_current_save_id
except ImportError:
    def get_current_save_id() -> str:
        return "slot_default"

WORLD_LORE_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_world_lore.json")

_WORKING_WORLD_CACHE: Optional[Dict[str, Dict[str, str]]] = None
_ACTIVE_WORLD_SAVE_ID: Optional[str] = None
_WORLD_LOCK = threading.RLock()

DEFAULT_WORLD_DESCRIPTIONS: Dict[str, str] = {
    "Виллоу Крик": "уютный цветущий пригород: тенистые аллеи, плакучие ивы, парки, магнолии и традиционные жилые кварталы с красивыми особняками",
    "Оазис Спрингс": "солнечный пустынный оазис в стиле юго-запада США: пальмы, кактусы, каньоны из красного песчаника, ретро-модерн застройка середины века (Mid-century modern) и сухой знойный климат",
    "Ньюкрест": "просторный тихий пригород с аккуратными лужайками, городским парком и видом на современный скайлайн вдалеке",
    "Магнолия Променейд": "оживленная торговая набережная у залива: бутики, магазины, кирпичные мостовые и уютные прибрежные скверы",
    "Винденбург": "старинный европейский город: фахверковые дома в стиле Тюдоров, булыжные мостовые, древние руины на утесах, ветряные мельницы, живописные фьорды и бурная клубная жизнь",
    "Сан Мишуно": "шумный интернациональный мегаполис: высотные небоскребы, пентхаусы, тесные квартиры, блошиные рынки, уличная еда со всего мира, фестивали и яркие граффити",
    "Форготн Холлоу": "мрачный готический туманный анклав: вечные сумерки, старинные склепы, викторианские поместья, сухие корявые деревья, чеснок и древние вампиры",
    "Бриндлтон Бэй": "уютный прибрежный портовый городок Новой Англии: маяк, деревянные коттеджи у моря, песчаные пляжи, туманы, соленый морской бриз и культ домашних питомцев (кошек и собак)",
    "Сельвадорада": "латиноамериканский тропический край: густые непроходимые джунгли, древние храмы и руины цивилизации омисканцев, бурные реки, водопады и колоритный рынок с местной культурой",
    "Дель-Соль-Вэлли": "гламурный аналог Лос-Анджелеса и Голливуда: пальмовые бульвары, аллея славы, киностудии, роскошные особняки знаменитостей на холмах Пиннаклс и палящее калифорнийское солнце",
    "Стрейнджервиль": "загадочный военный городок в каньонах пустыни: секретная лаборатория, бункеры, параноидальные заговоры, причудливая флора и аномальная атмосфера тайн в стиле Зоны 51",
    "Сулани": "райский тропический полинезийский архипелаг: бирюзовые лагуны с кораллами, действующий вулкан, песчаные пляжи, бунгало на сваях, культура кавы и духи предков",
    "Глиммербрук": "уединенный сказочный лесной поселок: густые сосны, бурлящий водопад, каменистая река, деревянные шале и скрытый таинственный портал в Волшебный мир",
    "Волшебный мир": "парящие в космической пустоте магические острова: сиренево-звездное небо, Аллея Заклинателей, древний замок магии, парящие скалы и чистая колдовская энергия",
    "Волшебный мир / Глиммербрук": "парящие в космической пустоте магические острова: сиренево-звездное небо, Аллея Заклинателей, древний замок магии, парящие скалы и чистая колдовская энергия",
    "Бритчестер": "величественный английский университетский городок: старинный неоготический Университет Бритчестера, ультрасовременный Институт Фоксбери, каналы, пабы и студенческая академическая жизнь",
    "Эвергрин-Харбор": "бывший промышленный тихоокеанский порт: переоборудованные фабрики, контейнерное жилье, экологические проекты, смоговые дымки или кристально чистая зеленая гавань",
    "Гора Комореби": "живописный японский горный курорт: заснеженные вершины для лыж и сноуборда, горячие источники (онсэны), бамбуковые рощи, синтоистские святилища и цветущая сакура",
    "Хэнфорд-он-Бэгли": "пасторальная английская сельская глубинка: каменные коттеджи с соломенными крышами, зеленые холмы, пастбища коров и лам, дикие лисы, птицы, кролики и уютная деревенская ярмарка",
    "Тартоза": "романтическое средиземноморское побережье: водопады любви, оливковые и цитрусовые рощи, бирюзовые морские бухты, итальянская архитектура и идеальная атмосфера для свадеб",
    "Мунвуд Милл": "заброшенный лесопильный поселок в темных хвойных лесах: ржавые станки, индустриальные руины, полнолуние над озером Лунвуд, подземные тоннели и логова стай оборотней",
    "Коппердейл": "уютный шахтерский городок у озера в духе американского Северо-Запада: старшая школа, парк аттракционов с колесом обозрения на пирсе, чайный магазин боба и подростковая драма",
    "Сан-Секвойя": "спокойный калифорнийский залив в стиле залива Сан-Франциско: грандиозный мост, набережные, пригородные семейные дома, парки у воды и общественный центр",
    "Честнат-Ридж": "просторные прерии американского Дикого Запада: каньоны, ранчо, поля для верховой езды, загоны для лошадей, нектарные погреба и ковбойский колорит",
    "Томаранг": "колоритный край Юго-Восточной Азии: густые тропики, ночной рынок с запахами специй, арендные жилые комплексы, ботанический заповедник и старинные буддийские храмы",
    "Сьюдад-Энаморада": "страстный южноамериканский романтический мегаполис: архитектура в стиле Мехико, роскошные зеленые парки свиданий, мотели на час, бары на крышах и стена влюбленных",
    "Вранбург": "мистический викторианский край потустороннего мира: склепы, старинные кладбища, блуждающие призраки, вороны, колокольня Смерти и мрачный загробный колорит",
    "Батуу": "далекая застава на краю Галактики 'Звёздных Войн': каменные шпили аванпоста Черный Шпиль, дроиды, кантина Оги, космические корабли, Сопротивление и Первый Орден",
    "Гранит Фоллз": "дремучий хвойный национальный заповедник: вековые сосны, скалы, палаточные кемпинги, костры, сбор трав и скрытое жилище лесного отшельника",
    "Сиксим": "чужеродная внеземная планета: светящиеся неоновые кристаллы, инопланетные растения, низкая гравитация, парящие споры и странные атмосферные явления",
    "Лесная поляна": "тайная сказочная поляна: волшебное дерево, розово-голубое свечение, мерцающие водопады, светлячки и редкие цветы",
    "Забытый грот": "скрытая глубокая пещера в каньоне: сталактиты, кристаллы, светящиеся пещерные мхи, подземное озеро и редкие ископаемые",
    "Глухой лес": "глухая непроходимая чаща заповедника: вековые деревья, заросшие тропы, дикая природа и бревенчатая хижина отшельника",
}

# Ordered list of all primary worlds for UI listing
ORDERED_WORLD_LIST = [
    "Виллоу Крик", "Оазис Спрингс", "Ньюкрест", "Гранит Фоллз", "Магнолия Променейд",
    "Винденбург", "Сан Мишуно", "Форготн Холлоу", "Бриндлтон Бэй", "Сельвадорада",
    "Дель-Соль-Вэлли", "Стрейнджервиль", "Сулани", "Глиммербрук", "Волшебный мир",
    "Бритчестер", "Эвергрин-Харбор", "Гора Комореби", "Хэнфорд-он-Бэгли", "Тартоза",
    "Мунвуд Милл", "Коппердейл", "Сан-Секвойя", "Честнат-Ридж", "Томаранг",
    "Сьюдад-Энаморада", "Вранбург", "Батуу", "Сиксим", "Лесная поляна",
    "Забытый грот", "Глухой лес"
]


def _read_disk_file() -> Dict[str, Any]:
    if os.path.exists(WORLD_LORE_FILE_PATH):
        try:
            with open(WORLD_LORE_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "saves" not in data or not isinstance(data["saves"], dict):
                        data["saves"] = {}
                    return data
        except Exception as e:
            log_exception("Failed to read ai_world_lore.json from disk", e)
    return {"saves": {}}


def _write_disk_file(data: Dict[str, Any]) -> bool:
    try:
        tmp_path = WORLD_LORE_FILE_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(WORLD_LORE_FILE_PATH):
            os.replace(tmp_path, WORLD_LORE_FILE_PATH)
        else:
            os.rename(tmp_path, WORLD_LORE_FILE_PATH)
        return True
    except Exception as e:
        log_exception("Failed to write ai_world_lore.json", e)
        return False


def load_world_data() -> Dict[str, Dict[str, str]]:
    global _WORKING_WORLD_CACHE, _ACTIVE_WORLD_SAVE_ID
    with _WORLD_LOCK:
        current_save = get_current_save_id()
        if _WORKING_WORLD_CACHE is not None and _ACTIVE_WORLD_SAVE_ID == current_save:
            return _WORKING_WORLD_CACHE

        _ACTIVE_WORLD_SAVE_ID = current_save
        disk_data = _read_disk_file()
        save_entry = disk_data.get("saves", {}).get(current_save, {})
        if isinstance(save_entry, dict):
            _WORKING_WORLD_CACHE = {}
            for k, v in save_entry.items():
                if isinstance(v, dict):
                    _WORKING_WORLD_CACHE[str(k)] = {
                        "desc": str(v.get("desc", "")).strip(),
                        "name": str(v.get("name", "")).strip()
                    }
                elif isinstance(v, str):
                    _WORKING_WORLD_CACHE[str(k)] = {"desc": v.strip(), "name": ""}
        else:
            _WORKING_WORLD_CACHE = {}

        log(f"[WORLD_LORE] Loaded {len(_WORKING_WORLD_CACHE)} custom world(s) for save '{current_save}'")
        return _WORKING_WORLD_CACHE


def get_custom_world_data(world_key: str, save_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    if not world_key:
        return None
    with _WORLD_LOCK:
        if save_id is None:
            cache = load_world_data()
            return cache.get(world_key)
        else:
            disk_data = _read_disk_file()
            entry = disk_data.get("saves", {}).get(save_id, {}).get(world_key)
            if isinstance(entry, dict):
                return {"desc": str(entry.get("desc", "")), "name": str(entry.get("name", ""))}
            elif isinstance(entry, str):
                return {"desc": entry, "name": ""}
            return None


def set_custom_world_data(world_key: str, desc: str, custom_name: str = "", save_id: Optional[str] = None) -> bool:
    if not world_key:
        return False
    with _WORLD_LOCK:
        current_save = save_id or get_current_save_id()
        clean_desc = desc.strip() if desc else ""
        clean_name = custom_name.strip() if custom_name else ""

        # Update in-memory cache if active save matches
        if _ACTIVE_WORLD_SAVE_ID == current_save and _WORKING_WORLD_CACHE is not None:
            if clean_desc or clean_name:
                _WORKING_WORLD_CACHE[world_key] = {"desc": clean_desc, "name": clean_name}
            else:
                _WORKING_WORLD_CACHE.pop(world_key, None)

        # Write to disk
        disk_data = _read_disk_file()
        if current_save not in disk_data["saves"]:
            disk_data["saves"][current_save] = {}

        if clean_desc or clean_name:
            disk_data["saves"][current_save][world_key] = {"desc": clean_desc, "name": clean_name}
        else:
            disk_data["saves"][current_save].pop(world_key, None)

        success = _write_disk_file(disk_data)
        log(f"[WORLD_LORE] Saved custom lore for world '{world_key}' in save '{current_save}': ok={success}")
        return success


def delete_custom_world_data(world_key: str, save_id: Optional[str] = None) -> bool:
    return set_custom_world_data(world_key, "", "", save_id=save_id)


def get_all_custom_worlds(save_id: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    with _WORLD_LOCK:
        if save_id is None:
            return dict(load_world_data())
        disk_data = _read_disk_file()
        save_entry = disk_data.get("saves", {}).get(save_id, {})
        res = {}
        if isinstance(save_entry, dict):
            for k, v in save_entry.items():
                if isinstance(v, dict):
                    res[k] = {"desc": str(v.get("desc", "")), "name": str(v.get("name", ""))}
                elif isinstance(v, str):
                    res[k] = {"desc": v, "name": ""}
        return res


def get_effective_world_desc(world_key: str) -> str:
    """Returns custom description for world_key if defined in this save, else default description."""
    if not world_key:
        return ""
    data = get_custom_world_data(world_key)
    if data and data.get("desc"):
        return data["desc"]
    return DEFAULT_WORLD_DESCRIPTIONS.get(world_key, "")


def get_effective_world_name(world_key: str) -> str:
    """Returns custom world name if defined in this save, else default world_key."""
    if not world_key:
        return ""
    data = get_custom_world_data(world_key)
    if data and data.get("name"):
        return data["name"]
    return world_key


def get_packed_world_lore_payload() -> str:
    """
    Packs world lore info for UI command dispatch:
    Format:
    curr_world_enc|num_custom|key_enc:name_enc:desc_enc|...
    """
    try:
        from ai_thought_reader.context import get_current_world_name
        curr_world = get_current_world_name() or "Виллоу Крик"
    except Exception:
        curr_world = "Виллоу Крик"

    curr_enc = quote(curr_world, safe="")
    custom_map = get_all_custom_worlds()
    items = []
    for k, v in custom_map.items():
        d = v.get("desc", "").strip()
        n = v.get("name", "").strip()
        if d or n:
            items.append(f"{quote(k, safe='')}:{quote(n, safe='')}:{quote(d, safe='')}")

    if not items:
        return f"{curr_enc}|0"
    return f"{curr_enc}|{len(items)}|" + "|".join(items)
