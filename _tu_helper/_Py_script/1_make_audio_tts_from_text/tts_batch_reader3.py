# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — универсальный и простой скрипт озвучивания текста

v15.1:
  • Универсальные языки и настройка через tts_config.json (voices, alt_voices, strict, markers, suffix_filter, detect_prefixes, voice_aliases).
  • Маркеры языка в любом месте строки (преимущество над авто-детектом).
  • Голосовые маркеры: (v:алиас)/(voice:алиас) и «сахар» [EN:guy] (язык+голос).
  • Паузы: между фразами, за каждый пробел подряд, за каждый перенос строки, доп. в начале строки.
  • Рекурсивный сбор входных файлов, жёсткие суффиксы по имени файла.
  • Fallback/strict для каждого языка.
  • Исправление «голых пауз»: паузы всегда «пришиваются» к следующему тексту (не посылаются в TTS отдельно).
  • Запись таймингов для каждого синтезированного КУСКА в <СТЕМ>.slides.txt (по одному рядом с MP3, и для каждого варианта в multi-EN).

Зависимости:
    pip install edge-tts langdetect mutagen
"""

import asyncio
import json
import re
import sys
from glob import glob
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional

import edge_tts
from langdetect import detect

try:
    from mutagen.mp3 import MP3  # для измерения длительности mp3-байтов
except Exception:
    MP3 = None


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
        print("Конфиг не найден. Положите рядом tts_config.json (см. пример из README).")
        sys.exit(1)
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
# 2) Подготовка языков, маркеров, алиасов
# =============================================================================

def get_languages_cfg(cfg: Dict) -> Dict[str, Dict]:
    langs = cfg.get("languages", {})
    norm = {}
    for key, val in langs.items():
        if not isinstance(val, dict):
            continue
        d = {
            "voice":             val.get("voice", ""),
            "alt_voices":        val.get("alt_voices", []) if isinstance(val.get("alt_voices", []), list) else [],
            "strict_no_fallback": bool(val.get("strict_no_fallback", False)),
            "markers":           [str(x).lower() for x in val.get("markers", []) if str(x).strip()],
            "suffix_filter":     {"enabled": bool(val.get("suffix_filter", {}).get("enabled", False)),
                                  "suffix":  str(val.get("suffix_filter", {}).get("suffix", ""))},
            "detect_prefixes":   [str(x).lower() for x in val.get("detect_prefixes", []) if str(x).strip()],
            "voice_aliases":     {str(k).lower(): str(v) for k, v in val.get("voice_aliases", {}).items()}
        }
        norm[key] = d
    return norm

def build_marker_map(langs_cfg: Dict[str, Dict]) -> Dict[str, str]:
    # язык → маркеры → плоская карта "маркер -> язык"
    m: Dict[str, str] = {}
    for lang_key, info in langs_cfg.items():
        for marker in sorted(info.get("markers", []), key=len):
            if marker and marker not in m:
                m[marker] = lang_key
    return m

def build_detect_map(langs_cfg: Dict[str, Dict]) -> Dict[str, str]:
    dmap: Dict[str, str] = {}
    for lang_key, info in langs_cfg.items():
        for pref in info.get("detect_prefixes", []):
            if pref and pref not in dmap:
                dmap[pref] = lang_key
    return dmap

def map_detect_to_lang(lang_code: str, detect_map: Dict[str, str], default_lang: str) -> str:
    lc = (lang_code or "").lower()
    for pref, key in detect_map.items():
        if lc.startswith(pref):
            return key
    return default_lang

def get_voice_marker_prefixes(cfg: Dict) -> List[str]:
    vps = cfg.get("voice_marker_prefixes", ["v:", "voice:"])
    if not isinstance(vps, list):
        vps = ["v:", "voice:"]
    return [str(s).lower() for s in vps if str(s).strip()]

def build_end_delims(cfg: Dict) -> List[str]:
    dl = cfg.get("sentence_delimiters", [".", ";", "!", "?", "\n"])
    if not isinstance(dl, list):
        return [".", ";", "!", "?", "\n"]
    return [("\n" if s == "\\n" else str(s)) for s in dl if str(s)]


# =============================================================================
# 3) Разбиение по делимитерам с подсчётом переносов
# =============================================================================

def split_by_delimiters_with_counts(text: str, delims: List[str]) -> List[Tuple[str, Optional[str], int]]:
    dset = set([d if len(d) == 1 else d[0] for d in delims])
    chunks: List[Tuple[str, Optional[str], int]] = []

    buf = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in dset:
            chunk = "".join(buf)
            buf = []

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


# =============================================================================
# 4) Инлайновые маркеры: язык и голос
# =============================================================================

def find_next_voice_marker(lower_text: str, start: int, voice_prefixes: List[str]) -> Optional[Tuple[int, str, int]]:
    """
    Ищем ближайший голосовой маркер вида '(v:alias)' или '(voice:alias)'.
    Возвращает: (pos_open_paren, alias_lower, end_index_after_marker) или None.
    """
    pos = lower_text.find("(", start)
    while pos != -1:
        close = lower_text.find(")", pos + 1)
        if close == -1:
            break
        inside = lower_text[pos+1:close].strip()
        for pref in voice_prefixes:
            if inside.startswith(pref):
                alias = inside[len(pref):].strip()
                if alias:
                    return (pos, alias.lower(), close + 1)
        pos = lower_text.find("(", pos + 1)
    return None

def find_next_square_combo(lower_text: str, start: int) -> Optional[Tuple[int, str, Optional[str], int]]:
    """
    Ищем сахарную форму: [EN:guy], [RU:dmitry], [UK:polina] или просто [EN]
    Возвращаем: (pos_open_bracket, lang_key_lower_or_pref, alias_lower_or_None, end_index)
    """
    pos = lower_text.find("[", start)
    while pos != -1:
        close = lower_text.find("]", pos + 1)
        if close == -1:
            break
        inside = lower_text[pos+1:close].strip()
        if inside:
            if ":" in inside:
                l, r = inside.split(":", 1)
                lang = l.strip().lower()
                alias = r.strip().lower()
                if lang:
                    return (pos, lang, alias if alias else None, close + 1)
            else:
                lang = inside.strip().lower()
                if lang:
                    return (pos, lang, None, close + 1)
        pos = lower_text.find("[", pos + 1)
    return None

def split_chunk_by_markers(chunk_text: str,
                           lang_marker_map: Dict[str, str],
                           langs_cfg: Dict[str, Dict],
                           voice_prefixes: List[str]) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """
    Делим фрагмент по ИНЛАЙНОВЫМ маркерам (языковым и голосовым).
    Возвращаем части: (text_part, forced_lang_key, forced_voice_alias_or_id)
    """
    if not chunk_text or not chunk_text.strip():
        return [(chunk_text, None, None)]

    s = chunk_text
    res: List[Tuple[str, Optional[str], Optional[str]]] = []
    curr_lang: Optional[str] = None
    curr_voice_alias: Optional[str] = None
    i = 0
    lower = s.lower()

    while i < len(s):
        # ближайший языковой маркер
        next_lang_pos, next_lang_mark, next_lang_key = None, None, None
        for mark, lang_key in lang_marker_map.items():
            pos = lower.find(mark, i)
            if pos != -1 and (next_lang_pos is None or pos < next_lang_pos):
                next_lang_pos, next_lang_mark, next_lang_key = pos, mark, lang_key

        # ближайший голосовой маркер
        vm = find_next_voice_marker(lower, i, voice_prefixes)
        next_voice_pos = vm[0] if vm else None

        # сахарная форма [EN:alias] / [EN]
        sq = find_next_square_combo(lower, i)
        next_sq_pos = sq[0] if sq else None

        # выбираем ближайшее событие
        candidates = [(next_lang_pos, "lang"), (next_voice_pos, "voice"), (next_sq_pos, "sq")]
        candidates = [(p, t) for (p, t) in candidates if p is not None]
        if not candidates:
            tail = s[i:]
            if tail:
                res.append((tail, curr_lang, curr_voice_alias))
            break

        pos, typ = min(candidates, key=lambda x: x[0])

        if pos > i:
            res.append((s[i:pos], curr_lang, curr_voice_alias))

        if typ == "lang":
            j = pos + len(next_lang_mark)
            while j < len(s) and s[j] in " \t:—-–":
                j += 1
            curr_lang = next_lang_key
            curr_voice_alias = None  # сбрасываем алиас при смене языка
            i = j
        elif typ == "voice":
            _pos, alias_lower, j = vm
            curr_voice_alias = alias_lower
            i = j
        else:  # "sq"
            _pos, lang_lower, alias_lower, j = sq
            # сопоставим язык
            if lang_lower in langs_cfg:
                curr_lang = lang_lower
            else:
                for k, inf in langs_cfg.items():
                    for pref in inf.get("detect_prefixes", []):
                        if lang_lower == pref:
                            curr_lang = k
                            break
                    if curr_lang == k:
                        break
            curr_voice_alias = alias_lower if alias_lower else None
            i = j

        lower = s.lower()

    return res


# =============================================================================
# 5) Очистка и паузы внутри фразы
# =============================================================================

_ALLOWED_RE = re.compile(r"[^A-Za-z\u00C0-\u024F\u0400-\u04FF0-9\s\.,!?\:\;\-\(\)\[\]\"'«»]+", re.UNICODE)
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

def sanitize_base(s: str, strip_emojis: bool) -> str:
    if strip_emojis:
        s = _EMOJI_RE.sub("", s)
        s = _ALLOWED_RE.sub("", s)
    return s.strip()

def inject_space_pauses(s: str, enabled: bool, ms_per_space: int) -> str:
    if not enabled or ms_per_space <= 0 or " " not in s:
        return s
    def repl(match):
        count = len(match.group(0))
        pause = make_pause_commas(count * ms_per_space)
        return " " + pause + " "
    return re.sub(r" +", repl, s)

def finalize_phrase_text(text: str) -> str:
    return text if re.search(r"[.!?;]$", text) else (text + ".")


# =============================================================================
# 6) Построение фраз и группировка по языку
# =============================================================================

def build_phrases_with_lang_and_voice(text: str, cfg: Dict) -> List[Tuple[str, Optional[str], Optional[str], int]]:
    """
    Возвращаем фразы: (phrase_text, forced_lang_key, voice_alias_or_id, newline_count_after)
    """
    langs_cfg = get_languages_cfg(cfg)
    lang_marker_map = build_marker_map(langs_cfg)
    delims = build_end_delims(cfg)
    strip_symbols_list = cfg.get("strip_symbols", [])
    strip_emojis = bool(cfg.get("strip_emojis", True))

    pauses = cfg.get("pauses", {})
    space_enabled = bool(pauses.get("space_pause", {}).get("enabled", False))
    ms_per_space = int(pauses.get("space_pause", {}).get("ms_per_space", 0))

    voice_prefixes = get_voice_marker_prefixes(cfg)

    chunks = split_by_delimiters_with_counts(text, delims)
    phrases: List[Tuple[str, Optional[str], Optional[str], int]] = []

    for chunk_text, delim_used, newline_count in chunks:
        parts = split_chunk_by_markers(chunk_text, lang_marker_map, langs_cfg, voice_prefixes)
        if not parts:
            continue

        for idx, (part_text, forced_lang, voice_alias) in enumerate(parts):
            cleaned = sanitize_strip_symbols(part_text, strip_symbols_list)
            cleaned = inject_space_pauses(cleaned, space_enabled, ms_per_space)
            cleaned = sanitize_base(cleaned, strip_emojis)
            if not cleaned:
                continue

            nl_count = newline_count if idx == len(parts) - 1 else 0
            phrases.append((finalize_phrase_text(cleaned), forced_lang, voice_alias, nl_count))

    return phrases

def group_phrases_by_language(phrases: List[Tuple[str, Optional[str], Optional[str], int]], cfg: Dict) -> List[Tuple[str, List[Tuple[str, Optional[str], Optional[str], int]]]]:
    """
    Блоки: [(lang_key, [ (text, forced_lang, voice_alias, newline_count), ... ]), ...]
    """
    langs_cfg = get_languages_cfg(cfg)
    detect_map = build_detect_map(langs_cfg)
    default_lang = next(iter(langs_cfg.keys()), "en")

    blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str], int]]]] = []
    curr_lang_key: Optional[str] = None
    curr_list: List[Tuple[str, Optional[str], Optional[str], int]] = []

    for text, forced_lang, voice_alias, nlcount in phrases:
        if not text:
            continue
        if forced_lang:
            lang_key = forced_lang
        else:
            try:
                code = detect(text)
            except Exception:
                code = "en"
            lang_key = map_detect_to_lang(code, detect_map, default_lang)

        if curr_lang_key is None:
            curr_lang_key, curr_list = lang_key, [(text, forced_lang, voice_alias, nlcount)]
            continue

        if lang_key == curr_lang_key:
            curr_list.append((text, forced_lang, voice_alias, nlcount))
        else:
            blocks.append((curr_lang_key, curr_list))
            curr_lang_key, curr_list = lang_key, [(text, forced_lang, voice_alias, nlcount)]

    if curr_list:
        blocks.append((curr_lang_key, curr_list))

    return blocks

def languages_present(blocks) -> Set[str]:
    return {lang for lang, frs in blocks if frs}


# =============================================================================
# 7) Выбор голоса по алиасу/ID и TTS с измерением длительности
# =============================================================================

def choose_voice_for_part(lang_key: str,
                          voice_alias_or_id: Optional[str],
                          cfg: Dict) -> Tuple[str, List[str], bool]:
    """
    Возвращает (primary_voice, alt_voices, strict_flag) для части.
    """
    langs_cfg = get_languages_cfg(cfg)
    info = langs_cfg.get(lang_key, {})
    primary = info.get("voice", "")
    alts = info.get("alt_voices", []) if isinstance(info.get("alt_voices", []), list) else []
    strict = bool(info.get("strict_no_fallback", False))

    if not voice_alias_or_id:
        return primary, alts, strict

    alias = voice_alias_or_id.lower()
    aliases_map = {str(k).lower(): str(v) for k, v in info.get("voice_aliases", {}).items()}
    if alias in aliases_map:
        return aliases_map[alias], alts, strict

    if bool(cfg.get("allow_partial_voice_match", True)):
        candidates = [primary] + alts
        for vid in candidates:
            if alias in vid.lower():
                return vid, alts, strict

    return primary, alts, strict

def rate_to_str(rate: int) -> str:
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"

async def tts_render_bytes(text: str, voice: str, rate: int) -> bytes:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_to_str(rate))
    buf = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    if not buf:
        raise RuntimeError("No audio was received")
    return bytes(buf)

def mp3_duration_from_bytes(mp3_bytes: bytes) -> float:
    if MP3 is None or not mp3_bytes:
        return 0.0
    try:
        bio = BytesIO(mp3_bytes)
        audio = MP3(bio)
        return float(audio.info.length or 0.0)
    except Exception:
        return 0.0

async def tts_render_with_fallback_to_bytes(text: str,
                                            chosen_voice: str,
                                            alts: List[str],
                                            strict: bool,
                                            rate: int) -> Tuple[str, bytes]:
    try:
        b = await tts_render_bytes(text, chosen_voice, rate)
        return chosen_voice, b
    except Exception as first_err:
        if strict:
            raise first_err
        last_err = first_err
        tried = {chosen_voice.lower()}
        for v in alts:
            if v.lower() in tried:
                continue
            try:
                b = await tts_render_bytes(text, v, rate)
                return v, b
            except Exception as e:
                last_err = e
        raise last_err


# =============================================================================
# 8) Склейка (теперь паузы пришиваются к следующему тексту)
# =============================================================================

def glue_block_text(frs: List[Tuple[str, Optional[str], Optional[str], int]], cfg: Dict) -> List[Tuple[str, Optional[str]]]:
    """
    Возвращаем список (text_piece, voice_alias_or_id), но:
      - паузы НЕ отправляются отдельными кусками в TTS;
      - все паузы «пришиваются» в начало следующего текстового фрагмента.
    """
    pauses = cfg.get("pauses", {})
    base_ms = int(pauses.get("between_phrases_ms", 600))
    np_enabled = bool(pauses.get("newline_pause", {}).get("enabled", True))
    np_ms = int(pauses.get("newline_pause", {}).get("ms_per_newline", 400))
    start_line_ms = int(pauses.get("start_of_line_extra_pause_ms", 0))

    out: List[Tuple[str, Optional[str]]] = []
    first = True
    pending_prefix = ""  # сюда накапливаем «запятые-паузы»

    for text, _forced_lang, voice_alias, nlcount in frs:
        if not text:
            continue

        if first:
            out.append((text, voice_alias))
            first = False
            continue

        if base_ms > 0:
            pending_prefix += " " + make_pause_commas(base_ms) + " "
        if np_enabled and nlcount > 0 and np_ms > 0:
            pending_prefix += " " + make_pause_commas(nlcount * np_ms) + " "
        if nlcount > 0 and start_line_ms > 0:
            pending_prefix += " " + make_pause_commas(start_line_ms) + " "

        if pending_prefix:
            text = pending_prefix + text
            pending_prefix = ""

        out.append((text, voice_alias))

    # Гарантируем точку в конце последнего текстового фрагмента
    if out:
        last_text, last_voice = out[-1]
        if last_text and not re.search(r"[.!?;]\s*$", last_text):
            out[-1] = (finalize_phrase_text(last_text), last_voice)

    return out


# =============================================================================
# 9) Рендеринг (single / multi-EN) + запись .slides.txt
# =============================================================================

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str], int]]]],
                               cfg: Dict,
                               active_langs: Set[str]) -> None:
    langs_cfg = get_languages_cfg(cfg)
    rate = int(cfg.get("rate", -10))

    # только активные языки
    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После выбора активных языков блоков не осталось — пропуск.")
        return

    out_path = in_path.with_suffix(".mp3")
    slides_path = in_path.with_suffix(".slides.txt")
    out_path.write_bytes(b"")
    slides: List[float] = []

    with out_path.open("ab") as f:
        for i, (lang_key, frs) in enumerate(blocks, start=1):
            text_pieces = glue_block_text(frs, cfg)  # [(text_part, voice_alias_or_id)]
            if not text_pieces:
                continue

            print(f"  [Блок {i}/{len(blocks)}] lang={lang_key}, частей={len(text_pieces)}")
            for idx, (piece, voice_alias) in enumerate(text_pieces, start=1):
                if not piece.strip():
                    continue
                # защита: пропускаем «голые паузы», если вдруг образуются
                if len(piece.strip().replace(",", "")) == 0:
                    continue

                chosen_voice, alts, strict = choose_voice_for_part(lang_key, voice_alias, cfg)
                try:
                    used, mp3_bytes = await tts_render_with_fallback_to_bytes(
                        piece, chosen_voice, alts, strict, rate
                    )
                    f.write(mp3_bytes)
                    slides.append(mp3_duration_from_bytes(mp3_bytes))
                except Exception as e:
                    print(f"    ! Ошибка части ({lang_key} #{idx}): {e} — пропуск части.")

    if slides:
        slides_path.write_text("\n".join(f"{d:.3f}" for d in slides), encoding="utf-8")
        print(f"  Тайминги: {slides_path}")

    print(f"  Готово: {out_path}")

async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[Tuple[str, Optional[str], Optional[str], int]]]],
                                  cfg: Dict,
                                  active_langs: Set[str]) -> None:
    langs_cfg = get_languages_cfg(cfg)
    rate = int(cfg.get("rate", -10))

    if "en" not in langs_cfg:
        print("  multi_en_outputs=true, но язык 'en' не найден — пропуск.")
        return

    en_info = langs_cfg["en"]
    alt_en = en_info.get("alt_voices", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices у 'en' пуст — пропуск.")
        return

    if "en" not in active_langs:
        print("  Активные языки не содержат 'en' — пропуск.")
        return
    if not any(lang == "en" for lang, _ in blocks):
        print("  В тексте нет EN-блоков — пропуск.")
        return

    blocks = [(lang, frs) for (lang, frs) in blocks if lang in active_langs]
    if not blocks:
        print("  После отбора блоков не осталось — пропуск.")
        return

    stem = in_path.stem
    for en_voice in alt_en:
        out_path = in_path.with_name(f"{stem}__{en_voice}.mp3")
        slides_path = in_path.with_name(f"{stem}__{en_voice}.slides.txt")
        out_path.write_bytes(b"")
        slides: List[float] = []
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        with out_path.open("ab") as f:
            for i, (lang_key, frs) in enumerate(blocks, start=1):
                text_pieces = glue_block_text(frs, cfg)
                if not text_pieces:
                    continue
                print(f"    [Блок {i}/{len(blocks)}] lang={lang_key}, частей={len(text_pieces)}")
                for idx, (piece, voice_alias) in enumerate(text_pieces, start=1):
                    if not piece.strip():
                        continue
                    if len(piece.strip().replace(",", "")) == 0:
                        continue

                    try:
                        if lang_key == "en":
                            mp3_bytes = await tts_render_bytes(piece, en_voice, rate)
                            f.write(mp3_bytes)
                            slides.append(mp3_duration_from_bytes(mp3_bytes))
                        else:
                            chosen_voice, alts, strict = choose_voice_for_part(lang_key, voice_alias, cfg)
                            used, mp3_bytes = await tts_render_with_fallback_to_bytes(
                                piece, chosen_voice, alts, strict, rate
                            )
                            f.write(mp3_bytes)
                            slides.append(mp3_duration_from_bytes(mp3_bytes))
                    except Exception as e:
                        print(f"      ! Ошибка части ({lang_key} #{idx}): {e} — пропуск.")

        if slides:
            slides_path.write_text("\n".join(f"{d:.3f}" for d in slides), encoding="utf-8")
            print(f"  Тайминги: {slides_path}")

        print(f"  Готово: {out_path}")


# =============================================================================
# 10) Жёсткие суффиксы и активные языки
# =============================================================================

def pick_active_languages_for_file(stem: str, cfg: Dict) -> Set[str]:
    langs_cfg = get_languages_cfg(cfg)
    # приоритет — первый совпавший язык в порядке объявления
    for lang_key, info in langs_cfg.items():
        filt = info.get("suffix_filter", {"enabled": False, "suffix": ""})
        if filt.get("enabled") and stem.endswith(str(filt.get("suffix", ""))):
            return {lang_key}

    enable = cfg.get("enable_languages", [])
    if not isinstance(enable, list) or not enable:
        enable = list(langs_cfg.keys())
    return set(enable)


# =============================================================================
# 11) Основной цикл
# =============================================================================

async def process_one_file(path: Path, cfg: Dict) -> None:
    print(f"\n=== Файл: {path}")

    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        print("  Пустой файл — пропуск.")
        return

    phrases = build_phrases_with_lang_and_voice(raw_text, cfg)
    if not phrases:
        print("  После разметки не осталось фраз — пропуск.")
        return

    blocks = group_phrases_by_language(phrases, cfg)
    if not blocks:
        print("  Нет блоков для озвучивания — пропуск.")
        return

    stem = path.stem
    active_langs = pick_active_languages_for_file(stem, cfg)

    present = languages_present(blocks)
    if not (active_langs & present):
        print(f"  В тексте нет фраз для активных языков {sorted(active_langs)} — пропуск.")
        return

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
