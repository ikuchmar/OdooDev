# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — универсальный и простой скрипт озвучивания текста

v14:
  • Универсальные языки через конфиг: "languages" с (voice, alt_voices, strict, markers, suffix_filter, detect_prefixes).
  • enable_languages — список ключей из "languages", которые озвучивать по умолчанию.
  • Маркеры языка (в любом месте строки) имеют приоритет над авто-детектом; маркеры вырезаются из озвучки.
  • Жёсткие суффиксы: если включён и имя файла оканчивается на suffix — озвучиваем только этим языком.
  • Паузы:
      - between_phrases_ms — базовая между фразами.
      - space_pause.ms_per_space — пауза за каждый пробел подряд (N пробелов → N × ms).
      - newline_pause.ms_per_newline — пауза за каждый перенос (в т.ч. пустые строки).
      - start_of_line_extra_pause_ms — доп.пауза, если новая фраза началась после переноса.
  • Спецсимволы из strip_symbols удаляются перед TTS.
  • Fallback/strict для КАЖДОГО языка.
  • Рекурсивный сбор входных файлов.

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
# 0) Служебное: игнорируем "_" ключи (комментарии в JSON)
# =============================================================================

def strip_private_keys(obj):
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("_"):
                continue
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
        # Минимальный шаблон
        template = {
            "inputs": ["data/*.txt"],
            "recursive_inputs": True,
            "extensions": [".txt"],
            "enable_languages": ["en", "ru", "uk"],
            "languages": {
                "en": {
                    "voice": "en-GB-RyanNeural",
                    "alt_voices": ["en-GB-ThomasNeural", "en-US-RogerNeural"],
                    "strict_no_fallback": False,
                    "markers": ["[EN]", "_en_", "(en)", "en:", "english:"],
                    "suffix_filter": { "enabled": True, "suffix": "_en" },
                    "detect_prefixes": ["en"]
                },
                "ru": {
                    "voice": "ru-RU-DmitryNeural",
                    "alt_voices": ["ru-RU-SergeyNeural", "ru-RU-AndreiNeural"],
                    "strict_no_fallback": False,
                    "markers": ["[RU]", "[RUS]", "_ru_", "_рус_", "(ru)", "(рус)", "ru:", "рус:"],
                    "suffix_filter": { "enabled": False, "suffix": "_ru" },
                    "detect_prefixes": ["ru"]
                },
                "uk": {
                    "voice": "uk-UA-OstapNeural",
                    "alt_voices": ["uk-UA-PolinaNeural"],
                    "strict_no_fallback": False,
                    "markers": ["[UK]", "[UA]", "_uk_", "_ua_", "(uk)", "(ua)", "uk:", "ua:"],
                    "suffix_filter": { "enabled": False, "suffix": "_uk" },
                    "detect_prefixes": ["uk", "uk-UA"]
                }
            },
            "strip_symbols": ["(", ")", "[", "]", "{", "}", "_", "<", ">", "—"],
            "strip_emojis": True,
            "rate": -15,
            "pauses": {
                "between_phrases_ms": 600,
                "space_pause":   { "enabled": True, "ms_per_space": 0 },
                "newline_pause": { "enabled": True, "ms_per_newline": 400 },
                "start_of_line_extra_pause_ms": 200
            },
            "sentence_delimiters": [".", ";", "!", "?", "\n"]
        }
        cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Создан шаблон конфига: {cfg_path}\nОтредактируйте и запустите скрипт ещё раз.")
        sys.exit(0)

    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
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
# 2) Подготовка «языковой матрицы»: маркеры, суффиксы, detect-префиксы
# =============================================================================

def get_languages_cfg(cfg: Dict) -> Dict[str, Dict]:
    langs = cfg.get("languages", {})
    # нормализуем структуру и типы
    norm = {}
    for key, val in langs.items():
        if not isinstance(val, dict):
            continue
        d = {
            "voice":            val.get("voice", ""),
            "alt_voices":       val.get("alt_voices", []) if isinstance(val.get("alt_voices", []), list) else [],
            "strict_no_fallback": bool(val.get("strict_no_fallback", False)),
            "markers":          [str(x).lower() for x in val.get("markers", []) if str(x).strip()],
            "suffix_filter":    {"enabled": bool(val.get("suffix_filter", {}).get("enabled", False)),
                                 "suffix":  str(val.get("suffix_filter", {}).get("suffix", ""))},
            "detect_prefixes":  [str(x).lower() for x in val.get("detect_prefixes", []) if str(x).strip()]
        }
        norm[key] = d
    return norm

def build_marker_map(langs_cfg: Dict[str, Dict]) -> Dict[str, str]:
    """
    Плоская карта: маркер (в нижнем регистре) -> языковой ключ (en/ru/uk/...)
    При коллизиях приоритет у тех языков, что идут первыми в словаре (JSON сохраняет порядок).
    """
    m: Dict[str, str] = {}
    for lang_key, info in langs_cfg.items():
        # короткие маркеры ставим раньше длинных — меньше ложных срабатываний
        for marker in sorted(info.get("markers", []), key=len):
            if marker and marker not in m:
                m[marker] = lang_key
    return m

def build_detect_map(langs_cfg: Dict[str, Dict]) -> Dict[str, str]:
    """
    detect_prefix -> lang_key. Если prefix= 'en', то любой код langdetect,
    который .startswith('en'), будет считаться этим языком.
    """
    dmap: Dict[str, str] = {}
    for lang_key, info in langs_cfg.items():
        for pref in info.get("detect_prefixes", []):
            if pref and pref not in dmap:
                dmap[pref] = lang_key
    return dmap

def map_detect_to_lang(lang_code: str, detect_map: Dict[str, str], default_lang: str="en") -> str:
    lc = (lang_code or "").lower()
    for pref, key in detect_map.items():
        if lc.startswith(pref):
            return key
    return default_lang


# =============================================================================
# 3) Разбиение текста на фрагменты и инлайновые маркеры
# =============================================================================

def build_end_delims(cfg: Dict) -> List[str]:
    dl = cfg.get("sentence_delimiters", [".", ";", "!", "?", "\n"])
    if not isinstance(dl, list):
        return [".", ";", "!", "?", "\n"]
    return [("\n" if s == "\\n" else str(s)) for s in dl if str(s)]

def split_by_delimiters_with_counts(text: str, delims: List[str]) -> List[Tuple[str, Optional[str], int]]:
    """
    Делим текст на фрагменты по делимитерам и считаем КОЛИЧЕСТВО подряд идущих '\n'.
    Возвращаем [(chunk_text, delim_used (символ или None), newline_count_after_delim)]
    Пример: 'foo\\n\\nbar.' даст:
      ('foo', '\\n', 2) + ('bar', '.', 0)
    """
    dset = set([d if len(d) == 1 else d[0] for d in delims])
    chunks: List[Tuple[str, Optional[str], int]] = []

    buf = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in dset:
            # закрываем текущий буфер как фрагмент
            chunk = "".join(buf)
            buf = []

            # если это \n — считаем пачку подряд идущих \n
            newline_count = 0
            delim_used = ch
            if ch == "\n":
                newline_count = 1
                j = i + 1
                while j < n and text[j] == "\n":
                    newline_count += 1
                    j += 1
                i = j
            else:
                i += 1

            chunks.append((chunk, delim_used, newline_count))
        else:
            buf.append(ch)
            i += 1

    if buf:
        chunks.append(("".join(buf), None, 0))
    return chunks

def split_chunk_by_inline_markers(chunk_text: str,
                                  markers_map: Dict[str, str]) -> List[Tuple[str, Optional[str]]]:
    """
    Делим фрагмент по ИНЛАЙНОВЫМ маркерам (где угодно в строке).
    Возвращаем [(text_part, forced_lang or None)].
    Сам маркер из озвучки исключается.
    """
    if not chunk_text or not chunk_text.strip() or not markers_map:
        return [(chunk_text, None)]

    s = chunk_text
    res: List[Tuple[str, Optional[str]]] = []
    curr_lang: Optional[str] = None
    i = 0
    lower = s.lower()

    while i < len(s):
        next_pos = None
        next_mark = None
        next_lang = None
        for mark, lang_key in markers_map.items():
            pos = lower.find(mark, i)
            if pos != -1 and (next_pos is None or pos < next_pos):
                next_pos, next_mark, next_lang = pos, mark, lang_key

        if next_pos is None:
            tail = s[i:]
            if tail:
                res.append((tail, curr_lang))
            break

        if next_pos > i:
            res.append((s[i:next_pos], curr_lang))

        j = next_pos + len(next_mark)
        # проглатываем типичные разделители после маркера
        while j < len(s) and s[j] in " \t:—-–":
            j += 1

        curr_lang = next_lang
        i = j

    return res


# =============================================================================
# 4) Очистка и паузы внутри фразы (пробелы/переносы)
# =============================================================================

def make_pause_commas(ms: int) -> str:
    if ms <= 0:
        return ""
    n = max(1, round(ms / 300))
    return "," * n

def sanitize_strip_symbols(s: str, symbols: List[str]) -> str:
    if not symbols:
        return s
    table = {ord(c): None for c in symbols if isinstance(c, str) and len(c) == 1}
    return s.translate(table)

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

def sanitize_base(s: str, strip_emojis: bool) -> str:
    if strip_emojis:
        s = _EMOJI_RE.sub("", s)
        s = _ALLOWED_RE.sub("", s)
    # Не схлопываем пробелы! Они управляют паузой. Уберём только крайние.
    return s.strip()

def inject_space_pauses(s: str, enabled: bool, ms_per_space: int) -> str:
    """
    Вставляем «запятые-паузы» за КАЖДЫЙ пробел.
    Пример: "слово␠␠слово" -> "слово , , слово" (если 1 запятая == ms_per_space)
    Реализация: заменяем последовательности пробелов на " " + пауза + " ".
    """
    if not enabled or ms_per_space <= 0 or " " not in s:
        return s

    def repl(match):
        count = len(match.group(0))
        pause = make_pause_commas(count * ms_per_space)
        # чтобы не терять разделение слов — ставим одиночный пробел по краям
        return " " + pause + " "

    # последовательности >=1 пробелов
    return re.sub(r" +", repl, s)

def finalize_phrase_text(text: str) -> str:
    """Если в конце нет знака препинания — добавим точку."""
    return text if re.search(r"[.!?;]$", text) else (text + ".")


# =============================================================================
# 5) Построение фраз с учётом маркеров и последующая группировка по языку
# =============================================================================

def build_phrases_with_lang(text: str, cfg: Dict) -> List[Tuple[str, Optional[str], int]]:
    """
    Возвращаем список фраз в виде (phrase_text, forced_lang, newline_count_after_delim)
      - Разрезаем по sentence_delimiters, считая количество подряд идущих \\n (пустые строки = больше пауза).
      - Внутри фрагмента делим по ИНЛАЙНОВЫМ маркерам, вырезаем маркеры.
      - Удаляем strip_symbols.
      - Вставляем паузы по пробелам (если включено).
      - Базовую очистку (эмодзи и пр.) делаем без схлопывания пробелов.
    """
    langs_cfg = get_languages_cfg(cfg)
    markers_map = build_marker_map(langs_cfg)
    delims = build_end_delims(cfg)

    strip_symbols_list = cfg.get("strip_symbols", [])
    strip_emojis = bool(cfg.get("strip_emojis", True))

    pauses = cfg.get("pauses", {})
    space_enabled = bool(pauses.get("space_pause", {}).get("enabled", False))
    ms_per_space = int(pauses.get("space_pause", {}).get("ms_per_space", 0))

    chunks = split_by_delimiters_with_counts(text, delims)
    phrases: List[Tuple[str, Optional[str], int]] = []

    for chunk_text, delim_used, newline_count in chunks:
        parts = split_chunk_by_inline_markers(chunk_text, markers_map)  # [(text_part, forced_lang)]

        for idx, (part_text, forced_lang) in enumerate(parts):
            # 1) убрать спецсимволы
            cleaned = sanitize_strip_symbols(part_text, strip_symbols_list)
            # 2) паузы по пробелам (до базовой очистки)
            cleaned = inject_space_pauses(cleaned, space_enabled, ms_per_space)
            # 3) базовая очистка (без схлопывания пробелов)
            cleaned = sanitize_base(cleaned, strip_emojis)
            if not cleaned:
                continue

            # Только последняя часть фрагмента будет знать, сколько \n было после (для паузы)
            nl_count = newline_count if idx == len(parts) - 1 else 0

            phrases.append((finalize_phrase_text(cleaned), forced_lang, nl_count))

    return phrases

def group_phrases_by_language(phrases: List[Tuple[str, Optional[str], int]], cfg: Dict) -> List[Tuple[str, List[Tuple[str, Optional[str], int]]]]:
    """
    Возвращаем блоки: [(lang_key, [ (text, forced_lang, newline_count), ... ]), ...]
    Язык определяется: forced_lang (если есть) иначе langdetect → map_detect_to_lang.
    """
    langs_cfg = get_languages_cfg(cfg)
    # Соберём detect_map
    detect_map = build_detect_map(langs_cfg)
    default_lang = next(iter(langs_cfg.keys()), "en")

    blocks: List[Tuple[str, List[Tuple[str, Optional[str], int]]]] = []
    curr_lang_key: Optional[str] = None
    curr_list: List[Tuple[str, Optional[str], int]] = []

    for text, forced, nlcount in phrases:
        if not text:
            continue
        if forced:
            lang_key = forced
        else:
            # авто-детект и маппинг в ключ языка
            try:
                code = detect(text)
            except Exception:
                code = "en"
            lang_key = map_detect_to_lang(code, detect_map, default_lang)

        if curr_lang_key is None:
            curr_lang_key, curr_list = lang_key, [(text, forced, nlcount)]
            continue

        if lang_key == curr_lang_key:
            curr_list.append((text, forced, nlcount))
        else:
            blocks.append((curr_lang_key, curr_list))
            curr_lang_key, curr_list = lang_key, [(text, forced, nlcount)]

    if curr_list:
        blocks.append((curr_lang_key, curr_list))

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
# 7) Суффиксы (жёсткий режим) и выбор активных языков
# =============================================================================

def pick_active_languages_for_file(stem: str, cfg: Dict) -> Set[str]:
    """
    Если включённый суффикс где-то совпал — активен только этот язык.
    Если совпало несколько — берем ПЕРВЫЙ по порядку объявления в конфиге "languages".
    Иначе — enable_languages.
    """
    langs_cfg = get_languages_cfg(cfg)
    for lang_key, info in langs_cfg.items():
        filt = info.get("suffix_filter", {"enabled": False, "suffix": ""})
        if filt.get("enabled") and stem.endswith(str(filt.get("suffix", ""))):
            return {lang_key}

    enable = cfg.get("enable_languages", [])
    if not isinstance(enable, list) or not enable:
        enable = list(langs_cfg.keys())
    return set(enable)


# =============================================================================
# 8) Склейка фраз в блок с паузами между фразами и по переносам
# =============================================================================

def glue_block_text(frs: List[Tuple[str, Optional[str], int]], cfg: Dict) -> str:
    """
    Склеиваем фразы одного языка:
      - базовая пауза между фразами: pauses.between_phrases_ms
      - за переносы (в т.ч. пустые строки): pauses.newline_pause.ms_per_newline × count
      - доп. пауза, если новая фраза началась с новой строки: pauses.start_of_line_extra_pause_ms
    """
    pauses = cfg.get("pauses", {})
    base_ms = int(pauses.get("between_phrases_ms", 600))
    np_enabled = bool(pauses.get("newline_pause", {}).get("enabled", True))
    np_ms = int(pauses.get("newline_pause", {}).get("ms_per_newline", 400))
    start_line_ms = int(pauses.get("start_of_line_extra_pause_ms", 0))

    parts = []
    first = True
    for text, _forced, nlcount in frs:
        if not text:
            continue

        if first:
            parts.append(text)
            first = False
            continue

        # Базовая пауза между фразами
        if base_ms > 0:
            parts.append(" " + make_pause_commas(base_ms) + " ")

        # Пауза за переносы (включая пустые строки)
        if np_enabled and nlcount > 0 and np_ms > 0:
            parts.append(" " + make_pause_commas(nlcount * np_ms) + " ")

        # Доп. пауза если новая фраза начиналась с новой строки
        if nlcount > 0 and start_line_ms > 0:
            parts.append(" " + make_pause_commas(start_line_ms) + " ")

        parts.append(text)

    # Гарантируем финальную точку у последней фразы
    if parts and not re.search(r"[.!?;]\s*$", parts[-1]):
        parts[-1] = finalize_phrase_text(parts[-1])

    return "".join(parts).strip()


# =============================================================================
# 9) Рендеринг (single / multi-EN)
# =============================================================================

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[Tuple[str, Optional[str], int]]]],
                               cfg: Dict,
                               active_langs: Set[str]) -> None:
    langs_cfg = get_languages_cfg(cfg)
    rate = int(cfg.get("rate", -10))

    # Оставим блоки только по активным языкам
    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После выбора активных языков блоков не осталось — пропуск.")
        return

    out_path = in_path.with_suffix(".mp3")
    out_path.write_bytes(b"")

    for i, (lang_key, frs) in enumerate(blocks, start=1):
        text_block = glue_block_text(frs, cfg)
        if not text_block.strip():
            continue

        info = langs_cfg.get(lang_key, {})
        voice = info.get("voice", "")
        alts = info.get("alt_voices", [])
        strict = bool(info.get("strict_no_fallback", False))

        print(f"  [Блок {i}/{len(blocks)}] lang={lang_key}, фраз={len(frs)}, длина={len(text_block)}")
        try:
            used = await tts_try_primary_then_alts(text_block, voice, alts, not strict, rate, out_path)
            print(f"    ✓ {lang_key} голос: {used}")
        except Exception as e:
            print(f"    ! Ошибка блока ({lang_key}): {e} — пропуск.")

    print(f"  Готово: {out_path}")

async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[Tuple[str, Optional[str], int]]]],
                                  cfg: Dict,
                                  active_langs: Set[str]) -> None:
    """
    По аналогии со старыми версиями: multi-режим сделан для EN (исторически).
    Если хочешь — легко расширяется для любого языка: просто продублировать цикл по alt_voices языка X.
    """
    langs_cfg = get_languages_cfg(cfg)
    rate = int(cfg.get("rate", -10))

    # Берём «en», если он существует в конфиге
    if "en" not in langs_cfg:
        print("  multi_en_outputs=true, но язык 'en' не найден в конфиге — пропуск.")
        return

    en_info = langs_cfg["en"]
    alt_en = en_info.get("alt_voices", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices у 'en' пуст — нечего генерировать.")
        return

    # Есть ли EN-блоки и активен ли EN?
    if "en" not in active_langs:
        print("  Активные языки не содержат 'en' — пропуск EN-вариантов.")
        return
    if not any(lang == "en" for lang, _ in blocks):
        print("  В тексте нет EN-блоков — пропуск EN-вариантов.")
        return

    # Оставим только активные языки
    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После выбора активных языков блоков не осталось — пропуск EN-вариантов.")
        return

    stem = in_path.stem
    for en_voice in alt_en:
        out_path = in_path.with_name(f"{stem}__{en_voice}.mp3")
        out_path.write_bytes(b"")
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        for i, (lang_key, frs) in enumerate(blocks, start=1):
            text_block = glue_block_text(frs, cfg)
            if not text_block.strip():
                continue

            info = langs_cfg.get(lang_key, {})
            base_voice = info.get("voice", "")
            alts = info.get("alt_voices", [])
            strict = bool(info.get("strict_no_fallback", False))

            print(f"    [Блок {i}/{len(blocks)}] lang={lang_key}, фраз={len(frs)}, длина={len(text_block)}")
            try:
                if lang_key == "en":
                    # EN в мульти-режиме — строго текущим en_voice (без fallback)
                    await tts_append_block(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN: {en_voice}")
                else:
                    used = await tts_try_primary_then_alts(text_block, base_voice, alts, not strict, rate, out_path)
                    print(f"      ✓ {lang_key}: {used}")
            except Exception as e:
                print(f"      ! Ошибка блока ({lang_key}): {e} — пропуск блока.")

        print(f"  Готово: {out_path}")


# =============================================================================
# 10) Основной цикл
# =============================================================================

async def process_one_file(path: Path, cfg: Dict) -> None:
    print(f"\n=== Файл: {path}")

    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        print("  Пустой файл — пропуск.")
        return

    phrases = build_phrases_with_lang(raw_text, cfg)
    if not phrases:
        print("  После разметки не осталось фраз — пропуск.")
        return

    blocks = group_phrases_by_language(phrases, cfg)
    if not blocks:
        print("  Нет блоков для озвучивания — пропуск.")
        return

    # Выбор активных языков
    stem = path.stem
    active_langs = pick_active_languages_for_file(stem, cfg)

    present = languages_present(blocks)
    if not (active_langs & present):
        print(f"  В тексте нет фраз для активных языков {sorted(active_langs)} — пропуск.")
        return

    # Режим вывода
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
