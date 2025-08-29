# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — простой многокомментированный скрипт озвучивания текста (RU/EN/UA)

v12:
  • Игнорируем в конфиге любые ключи, начинающиеся с "_" (можно писать комментарии).
  • Явные маркеры языка с приоритетом над авто-детектом (настраиваются в конфиге):
        explicit_language_markers.en / .ru / .uk
     Маркер действует ДО ближайшего разделителя из marker_end_delimiters (по умолчанию: . ; ! ? \n).
     Сам маркер НЕ озвучивается.
  • Спец-символы, перечисленные в strip_symbols, удаляются из текста перед TTS.
  • Доп.паузы:
        - двойной пробел внутри предложения → добавляем паузу (если enabled), длительность в ms;
        - новая строка → добавляем паузу (если enabled), длительность в ms.
     Паузы реализованы «запятыми» (~300 мс/запятая).
  • Остальное — как в v11:
        - рекурсивный сбор входных;
        - суффикс-фильтры по имени файла: «жёсткий» режим (если включённый суффикс совпал — озвучиваем только этим языком);
        - два режима вывода (single и multi_en_outputs);
        - fallback-голоса и флаги строгого режима для EN/RU/UK.

Зависимости:
    pip install edge-tts langdetect
"""

import asyncio
import json
import re
import sys
from glob import glob
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional

import edge_tts
from langdetect import detect


# =============================================================================
# 0) УТИЛИТЫ: игнорируем "_" ключи в конфиге (комментарии)
# =============================================================================

def strip_private_keys(obj):
    """
    РЕКУРСИВНО удаляет из словаря все пары, ключ которых начинается с "_".
    Для списков — применяет к каждому элементу.
    Для остальных типов — возвращает как есть.
    """
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("_"):
                continue  # игнорируем "комментарии"
            clean[k] = strip_private_keys(v)
        return clean
    if isinstance(obj, list):
        return [strip_private_keys(x) for x in obj]
    return obj


# =============================================================================
# 1) Конфиг и сбор входных файлов
# =============================================================================

def script_dir() -> Path:
    return Path(__file__).resolve().parent

def load_or_create_config(cfg_path: Path) -> Dict:
    if not cfg_path.exists():
        template = {
            "inputs": ["data/*.txt"],

            "recursive_inputs": True,
            "extensions": [".txt"],

            "enable_languages": ["en", "ru", "uk"],

            "voice_en": "en-GB-RyanNeural",
            "alt_voices_en": ["en-GB-ThomasNeural", "en-US-RogerNeural"],
            "en_strict_no_fallback": False,

            "voice_ru": "ru-RU-DmitryNeural",
            "alt_voices_ru": ["ru-RU-SergeyNeural", "ru-RU-AndreiNeural"],
            "ru_strict_no_fallback": False,

            "voice_uk": "uk-UA-OstapNeural",
            "alt_voices_uk": ["uk-UA-PolinaNeural"],
            "uk_strict_no_fallback": False,

            "rate": -15,
            "pause": 600,
            "strip_emojis": True,

            "multi_en_outputs": False,

            "suffix_filters": {
                "en": { "enabled": True,  "suffix": "_en" },
                "ru": { "enabled": False, "suffix": "_ru" },
                "uk": { "enabled": False, "suffix": "_uk" }
            },

            "_comment": "Ниже — новые настройки маркеров/пауз/символов",

            "explicit_language_markers": {
                "en": ["[EN]", "_en_", "(en)", "en:", "english:"],
                "ru": ["[RU]", "[RUS]", "_ru_", "_рус_", "(ru)", "(рус)", "ru:", "рус:", "russian:"],
                "uk": ["[UK]", "[UA]", "_uk_", "_ua_", "(uk)", "(ua)", "uk:", "ua:", "ukrainian:"]
            },

            "marker_end_delimiters": [".", ";", "!", "?", "\n"],

            "strip_symbols": ["(", ")", "[", "]", "{", "}", "_", "<", ">", "—"],

            "extra_pause_on_double_space": {"enabled": True, "ms": 200},
            "extra_pause_on_newline": {"enabled": True, "ms": 500}
        }
        cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Создан шаблон конфига: {cfg_path}\nОтредактируйте его и запустите скрипт ещё раз.")
        sys.exit(0)

    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        # ВАЖНО: удалим из конфига все ключи-комментарии, начинающиеся с "_"
        cfg = strip_private_keys(raw)
        return cfg
    except Exception as e:
        print(f"Ошибка чтения {cfg_path.name}: {e}")
        sys.exit(1)

def normalize_ext_list(ext_list) -> List[str]:
    if not isinstance(ext_list, list):
        return [".txt"]
    out = []
    for e in ext_list:
        s = str(e).strip()
        if not s:
            continue
        if not s.startswith("."):
            s = "." + s
        out.append(s.lower())
    return out or [".txt"]

def rglob_dir_for_exts(dir_path: Path, exts: List[str]) -> List[Path]:
    results: List[Path] = []
    for p in dir_path.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            results.append(p.resolve())
    return results

def expand_inputs(patterns: List[str], recursive_inputs: bool, exts: List[str]) -> List[Path]:
    base = script_dir()
    files: List[Path] = []
    seen = set()

    for raw in patterns:
        p = Path(raw)
        if not p.is_absolute():
            p = base / raw

        if p.exists() and p.is_dir():
            found = rglob_dir_for_exts(p, exts)
            for f in found:
                if f not in seen:
                    seen.add(f)
                    files.append(f)
            continue

        pattern = str(p)
        matches = glob(pattern, recursive=True)
        if recursive_inputs and "**" not in pattern and ("*" in pattern or "?" in pattern):
            pp = Path(pattern)
            parent = str(pp.parent)
            name = pp.name
            recursive_pattern = str(Path(parent) / ("**/" + name))
            matches = list(set(matches) | set(glob(recursive_pattern, recursive=True)))

        if not matches and p.exists() and p.is_file():
            matches = [str(p)]

        for m in matches:
            f = Path(m).resolve()
            if f.is_file() and f not in seen:
                if exts and f.suffix.lower() not in exts:
                    continue
                seen.add(f)
                files.append(f)

    return files


# =============================================================================
# 2) Маркеры языка и разбиение по разделителям
# =============================================================================

def build_marker_index(cfg: Dict) -> Dict[str, List[str]]:
    """
    Подготавливаем маркеры для en/ru/uk:
      - приводим к нижнему регистру,
      - оставляем порядок (важно, если есть похожие маркеры).
    """
    out = {"en": [], "ru": [], "uk": []}
    em = cfg.get("explicit_language_markers", {})
    for lang in out.keys():
        raw = em.get(lang, [])
        if isinstance(raw, list):
            out[lang] = [str(x).lower() for x in raw if str(x).strip()]
    return out

def build_end_delims(cfg: Dict) -> List[str]:
    """
    Разделители окончания действия маркера.
    Пример: [".", ";", "!", "?", "\n"]
    """
    dl = cfg.get("marker_end_delimiters", [".", ";", "!", "?", "\n"])
    if not isinstance(dl, list):
        return [".", ";", "!", "?", "\n"]
    return [("\n" if s == "\\n" else str(s)) for s in dl if str(s)]

def split_by_delimiters(text: str, delims: List[str]) -> List[Tuple[str, Optional[str]]]:
    """
    Делим текст на «фразы» по разделителям из delims.
    Возвращаем список (chunk_text, delim_used), где delim_used — сам разделитель (или None для хвоста).
    Delims — односимвольные (в т.ч. '\n').
    """
    # Гарантируем, что все делимитеры — один символ
    dset = set([d if len(d) == 1 else d[0] for d in delims])
    chunks: List[Tuple[str, Optional[str]]] = []

    buf = []
    for ch in text:
        if ch in dset:
            # закрываем фрагмент до разделителя
            chunk = "".join(buf)
            chunks.append((chunk, ch))   # разделитель сохраняем отдельно
            buf = []
        else:
            buf.append(ch)
    # остаток
    if buf:
        chunks.append(("".join(buf), None))
    return chunks

def detect_marker_and_strip(s: str, markers_idx: Dict[str, List[str]]) -> Tuple[Optional[str], str]:
    """
    Ищем в начале строки маркер языка (с учётом ведущих пробелов).
    Возвращаем (forced_lang or None, text_without_marker).
    Поиск регистронезависимый.
    """
    s_orig = s
    s = s.lstrip()  # маркер можно ставить после отступов
    lower = s.lower()

    for lang in ["en", "ru", "uk"]:
        for m in markers_idx.get(lang, []):
            if m and lower.startswith(m):
                # срезаем маркер и последующие пробелы
                rest = s[len(m):].lstrip()
                # восстановим левую часть, которую срезали lstrip() (чтобы не потерять внутренние отступы)
                left_trim = len(s_orig) - len(s_orig.lstrip())
                return lang, (" " * left_trim) + rest
    return None, s_orig


# =============================================================================
# 3) Очистка текста, паузы и язык фразы
# =============================================================================

def make_pause_commas(ms: int) -> str:
    """~300 мс на запятую."""
    if ms <= 0:
        return ""
    n = max(1, round(ms / 300))
    return "," * n  # без пробелов — добавим их вокруг при вставке

def apply_double_space_pauses(s: str, enabled: bool, ms: int) -> str:
    """Заменяем двойной пробел на однократный + запятые-паузы + однократный."""
    if not enabled or "  " not in s:
        return s
    pause = " " + make_pause_commas(ms) + " "
    # заменим повторяющимися попытками
    while "  " in s:
        s = s.replace("  ", pause)
    return s

def sanitize_strip_symbols(s: str, symbols: List[str]) -> str:
    """Удаляем указанные спецсимволы (точное совпадение символа)."""
    if not symbols:
        return s
    table = {ord(c): None for c in symbols if isinstance(c, str) and len(c) == 1}
    return s.translate(table)

# (из прошлых версий)
_EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+", flags=re.UNICODE
)
_ALLOWED_RE = re.compile(r"[^A-Za-z\u00C0-\u024F\u0400-\u04FF0-9\s\.,!?\:\;\-\(\)\"'«»]+", re.UNICODE)

def sanitize_sentence_core(s: str, strip_emojis: bool) -> str:
    """Базовая очистка от эмодзи/экзотики + нормализация пробелов."""
    if strip_emojis:
        s = _EMOJI_RE.sub("", s)
        s = _ALLOWED_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[\.\,\!\?\:\;\-]+", "", s).strip()
    return s

def detect_lang_simple(s: str) -> str:
    try:
        lang = detect(s)
        if lang.startswith("ru"):
            return "ru"
        if lang.startswith("uk"):
            return "uk"
        if lang.startswith("en"):
            return "en"
    except Exception:
        pass
    return "en"


# =============================================================================
# 4) Построение «фраз» с учётом маркеров, делимитеров и пауз
# =============================================================================

def build_phrases_with_lang(text: str,
                            cfg: Dict) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """
    Разбиваем текст на фразы по marker_end_delimiters.
    Для каждой фразы:
      - пытаемся найти явный маркер языка в начале (forced_lang),
      - вырезаем маркер,
      - удаляем спецсимволы из strip_symbols,
      - вставляем доп.паузы за двойной пробел,
      - возвращаем кортеж (phrase_text_with_delim, forced_lang, delim_used).
    ВНИМАНИЕ: delim_used нужен для новых пауз на перевод строки.
    """
    markers_idx = build_marker_index(cfg)
    delims = build_end_delims(cfg)

    extra_double = cfg.get("extra_pause_on_double_space", {"enabled": False, "ms": 200})
    ds_enabled = bool(extra_double.get("enabled", False))
    ds_ms = int(extra_double.get("ms", 200))

    strip_symbols_list = cfg.get("strip_symbols", [])

    chunks = split_by_delimiters(text, delims)
    phrases: List[Tuple[str, Optional[str], Optional[str]]] = []

    for chunk_text, delim in chunks:
        # 1) явный маркер?
        forced_lang, without_marker = detect_marker_and_strip(chunk_text, markers_idx)

        # 2) спецсимволы не озвучиваем
        cleaned = sanitize_strip_symbols(without_marker, strip_symbols_list)

        # 3) доп.пауза за двойной пробел (до базовой очистки, чтобы не потерять)
        cleaned = apply_double_space_pauses(cleaned, ds_enabled, ds_ms)

        # 4) базовая очистка
        cleaned = sanitize_sentence_core(cleaned, bool(cfg.get("strip_emojis", True)))

        # 5) вернём фразу (вместе с исходным разделителем, чтобы позже его учесть)
        #    Замечание: сам разделитель (точка/;/?/!/перенос строки) хранится отдельно в 'delim'
        phrase_text = cleaned
        if delim and delim != "\n":
            # оставим знаки препинания (нужны для интонации TTS)
            # если их уже нет в cleaned — добавим
            if not re.search(r"[.!?;]$", phrase_text):
                phrase_text += delim

        phrases.append((phrase_text, forced_lang, delim))

    return phrases


# =============================================================================
# 5) Группировка по языкам (с приоритетом forced_lang) и «склейка» с паузами
# =============================================================================

def make_pause_commas_token(ms: int) -> str:
    token = make_pause_commas(ms)
    return " " + token + " " if token else ""

def glue_block_text(phrases: List[Tuple[str, Optional[str], Optional[str]]],
                    pause_ms_default: int,
                    cfg: Dict) -> str:
    """
    Склеиваем список фраз в один блок (одного языка), вставляя:
      - базовую паузу между фразами (pause_ms_default),
      - дополнительную паузу, если фраза отделена переносом строки (настраивается).
    """
    add_newline = cfg.get("extra_pause_on_newline", {"enabled": False, "ms": 500})
    nl_enabled = bool(add_newline.get("enabled", False))
    nl_ms = int(add_newline.get("ms", 500))

    parts = []
    first = True
    for text, _forced, delim in phrases:
        if not text:
            continue
        if first:
            parts.append(text if re.search(r"[.!?;]$", text) else (text + "."))
            first = False
            continue

        # базовая пауза
        parts.append(make_pause_commas_token(pause_ms_default))

        # доп.пауза, если до этой фразы был перенос строки
        if nl_enabled and delim == "\n":
            parts.append(make_pause_commas_token(nl_ms))

        parts.append(text if re.search(r"[.!?;]$", text) else (text + "."))

    return "".join(parts).strip()

def group_phrases_by_language(phrases: List[Tuple[str, Optional[str], Optional[str]]]) -> List[Tuple[str, List[Tuple[str, Optional[str], Optional[str]]]]]:
    """
    С учётом forced_lang: строим последовательность блоков [(lang, [фразы...]), ...]
    где lang ∈ {"en","ru","uk"} (auto или из маркера).
    """
    blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str]]]]] = []
    curr_lang = None
    curr_list: List[Tuple[str, Optional[str], Optional[str]]] = []

    for text, forced, delim in phrases:
        if not text:
            continue
        lang = forced if forced else detect_lang_simple(text)
        if curr_lang is None:
            curr_lang, curr_list = lang, [(text, forced, delim)]
            continue
        if lang == curr_lang:
            curr_list.append((text, forced, delim))
        else:
            blocks.append((curr_lang, curr_list))
            curr_lang, curr_list = lang, [(text, forced, delim)]

    if curr_list:
        blocks.append((curr_lang, curr_list))
    return blocks

def languages_present(blocks) -> Set[str]:
    return {lang for lang, frs in blocks if frs}


# =============================================================================
# 6) Низкоуровневый TTS и fallback
# =============================================================================

def rate_to_str(rate: int) -> str:
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"

async def tts_append_block(text: str, voice: str, rate: int, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_to_str(rate))
    empty = True
    with out_path.open("ab") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                empty = False
                f.write(chunk["data"])
    if empty:
        raise RuntimeError("No audio was received")

async def tts_try_primary_then_alts(text: str,
                                    primary: str,
                                    alts: List[str],
                                    allow_fallback: bool,
                                    rate: int,
                                    out_path: Path) -> str:
    try:
        await tts_append_block(text, primary, rate, out_path)
        return primary
    except Exception as first_err:
        if not allow_fallback or not alts:
            raise first_err
        last_err = first_err
        for v in alts:
            try:
                await tts_append_block(text, v, rate, out_path)
                return v
            except Exception as e:
                last_err = e
        raise last_err


# =============================================================================
# 7) Суффикс-фильтры (жёсткий режим) и выбор активных языков
# =============================================================================

def get_suffix_filters(cfg: Dict) -> Dict[str, Dict[str, object]]:
    sf = cfg.get("suffix_filters", {})
    def one(lang, default_suffix):
        s = sf.get(lang, {})
        return {"enabled": bool(s.get("enabled", False)), "suffix": str(s.get("suffix", default_suffix))}
    return {
        "en": one("en", "_en"),
        "ru": one("ru", "_ru"),
        "uk": one("uk", "_uk"),
    }

def pick_active_languages_for_file(stem: str, enable_languages: List[str], suffix_filters: Dict[str, Dict[str, object]]) -> Set[str]:
    # Жёсткий суффикс: если включён и совпал — активен только этот язык (первый из ['en','ru','uk'])
    for lang in ["en", "ru", "uk"]:
        rule = suffix_filters.get(lang, {"enabled": False, "suffix": ""})
        if rule.get("enabled") and stem.endswith(str(rule.get("suffix", ""))):
            return {lang}
    return set(enable_languages)


# =============================================================================
# 8) Рендеринг (single / multi)
# =============================================================================

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str]]]]],
                               cfg: Dict,
                               active_langs: Set[str]) -> None:
    # Основные голоса
    voice_en = cfg.get("voice_en", "en-GB-RyanNeural")
    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")

    # Альтернативы
    alt_en = cfg.get("alt_voices_en", [])
    alt_ru = cfg.get("alt_voices_ru", [])
    alt_uk = cfg.get("alt_voices_uk", [])
    if not isinstance(alt_en, list): alt_en = []
    if not isinstance(alt_ru, list): alt_ru = []
    if not isinstance(alt_uk, list): alt_uk = []

    # Флаги строгого режима
    en_strict = bool(cfg.get("en_strict_no_fallback", False))
    ru_strict = bool(cfg.get("ru_strict_no_fallback", False))
    uk_strict = bool(cfg.get("uk_strict_no_fallback", False))

    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    # Отфильтруем блоки по активным языкам
    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После выбора активных языков блоков не осталось — пропуск.")
        return

    out_path = in_path.with_suffix(".mp3")
    out_path.write_bytes(b"")

    total = len(blocks)
    for i, (lang, frs) in enumerate(blocks, start=1):
        text_block = glue_block_text(frs, pause, cfg)
        if not text_block.strip():
            continue
        print(f"  [Блок {i}/{total}] lang={lang}, фраз={len(frs)}, длина={len(text_block)}")
        try:
            if lang == "ru":
                used = await tts_try_primary_then_alts(text_block, voice_ru, alt_ru, not ru_strict, rate, out_path)
                print(f"    ✓ RU голос: {used}")
            elif lang == "uk":
                used = await tts_try_primary_then_alts(text_block, voice_uk, alt_uk, not uk_strict, rate, out_path)
                print(f"    ✓ UA голос: {used}")
            else:
                used = await tts_try_primary_then_alts(text_block, voice_en, alt_en, not en_strict, rate, out_path)
                print(f"    ✓ EN голос: {used}")
        except Exception as e:
            print(f"    ! Ошибка блока: {e} — пропуск.")

    print(f"  Готово: {out_path}")

async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str]]]]],
                                  cfg: Dict,
                                  active_langs: Set[str]) -> None:
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices_en пуст — нечего генерировать.")
        return
    if "en" not in active_langs:
        print("  Active языки не содержат EN — EN-варианты не создаются.")
        return
    if "en" not in languages_present(blocks):
        print("  В файле нет английских блоков — EN-варианты не создаются.")
        return

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    alt_ru = cfg.get("alt_voices_ru", [])
    if not isinstance(alt_ru, list): alt_ru = []
    ru_strict = bool(cfg.get("ru_strict_no_fallback", False))

    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")
    alt_uk = cfg.get("alt_voices_uk", [])
    if not isinstance(alt_uk, list): alt_uk = []
    uk_strict = bool(cfg.get("uk_strict_no_fallback", False))

    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После выбора активных языков блоков не осталось — пропуск EN-вариантов.")
        return

    stem = in_path.stem
    for en_voice in alt_en:
        out_path = in_path.with_name(f"{stem}__{en_voice}.mp3")
        out_path.write_bytes(b"")
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        total = len(blocks)
        for i, (lang, frs) in enumerate(blocks, start=1):
            text_block = glue_block_text(frs, pause, cfg)
            if not text_block.strip():
                continue
            print(f"    [Блок {i}/{total}] lang={lang}, фраз={len(frs)}, длина={len(text_block)}")
            try:
                if lang == "ru":
                    used = await tts_try_primary_then_alts(text_block, voice_ru, alt_ru, not ru_strict, rate, out_path)
                    print(f"      ✓ RU: {used}")
                elif lang == "uk":
                    used = await tts_try_primary_then_alts(text_block, voice_uk, alt_uk, not uk_strict, rate, out_path)
                    print(f"      ✓ UA: {used}")
                else:
                    # EN в мульти-режиме — строго текущим голосом без fallback
                    await tts_append_block(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN: {en_voice}")
            except Exception as e:
                print(f"      ! Ошибка блока: {e} — пропуск этого блока.")

        print(f"  Готово: {out_path}")


# =============================================================================
# 9) Основной цикл по файлам
# =============================================================================

def get_suffix_filters(cfg: Dict) -> Dict[str, Dict[str, object]]:
    sf = cfg.get("suffix_filters", {})
    def one(lang, default_suffix):
        s = sf.get(lang, {})
        return {"enabled": bool(s.get("enabled", False)), "suffix": str(s.get("suffix", default_suffix))}
    return {
        "en": one("en", "_en"),
        "ru": one("ru", "_ru"),
        "uk": one("uk", "_uk"),
    }

def pick_active_languages_for_file(stem: str, enable_languages: List[str], suffix_filters: Dict[str, Dict[str, object]]) -> Set[str]:
    for lang in ["en", "ru", "uk"]:
        rule = suffix_filters.get(lang, {"enabled": False, "suffix": ""})
        if rule.get("enabled") and stem.endswith(str(rule.get("suffix", ""))):
            return {lang}
    return set(enable_languages)

async def process_one_file(path: Path, cfg: Dict) -> None:
    print(f"\n=== Файл: {path}")

    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        print("  Пустой файл — пропуск.")
        return

    # 1) Разбиваем на фразы с учётом маркеров/делимитеров/символов/двойных пробелов
    phrases = build_phrases_with_lang(raw_text, cfg)
    if not phrases:
        print("  После разметки не осталось фраз — пропуск.")
        return

    # 2) Группируем в блоки по языку (forced_lang приоритетнее)
    blocks = group_phrases_by_language(phrases)
    if not blocks:
        print("  Нет блоков для озвучивания — пропуск.")
        return

    # 3) Активные языки по суффиксам/enable
    enable_languages = cfg.get("enable_languages", ["en", "ru"])
    if not isinstance(enable_languages, list) or not enable_languages:
        enable_languages = ["en", "ru"]
    suffix_filters = get_suffix_filters(cfg)
    stem = path.stem
    active_langs = pick_active_languages_for_file(stem, enable_languages, suffix_filters)

    present = languages_present(blocks)
    if not (active_langs & present):
        print(f"  В тексте нет фраз для активных языков {sorted(active_langs)} — пропуск.")
        return

    # 4) Режим вывода
    if bool(cfg.get("multi_en_outputs", False)):
        await render_multi_en_outputs(path, blocks, cfg, active_langs)
    else:
        await render_single_output(path, blocks, cfg, active_langs)

def main():
    cfg_path = script_dir() / "tts_config.json"
    cfg = load_or_create_config(cfg_path)

    patterns = cfg.get("inputs", [])
    if not isinstance(patterns, list) or not patterns:
        print("В 'inputs' должен быть непустой список путей/масок (строк).")
        sys.exit(1)

    recursive_inputs = bool(cfg.get("recursive_inputs", True))
    extensions = normalize_ext_list(cfg.get("extensions", [".txt"]))

    files = expand_inputs(patterns, recursive_inputs=recursive_inputs, exts=extensions)
    if not files:
        print("Файлы не найдены (проверьте 'inputs', 'recursive_inputs' и 'extensions').")
        sys.exit(1)

    for p in files:
        try:
            asyncio.run(process_one_file(p, cfg))
        except Exception as e:
            print(f"  Ошибка при обработке {p.name}: {e}")

if __name__ == "__main__":
    main()
