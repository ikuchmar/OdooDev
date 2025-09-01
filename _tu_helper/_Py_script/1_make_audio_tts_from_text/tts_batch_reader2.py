# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — универсальный и простой скрипт озвучивания текста

v15:
  • Всё из v14 (универсальные языки, паузы по пробелам/переносам, маркеры языков, суффиксы, fallback/strict).
  • Новое: голосовые маркеры в тексте — (v:алиас) / (voice:алиас) и сахар [EN:guy].
      - Маркер вырезается из озвучки.
      - Действует с позиции маркера до следующего маркера или конца фразы.
      - Выбор голоса:
          1) По voice_aliases языка.
          2) Если allow_partial_voice_match=true — по подстроке среди [voice] + alt_voices.
          3) Иначе — основной voice.
      - При ошибке TTS:
          • strict_no_fallback=true → не переключаемся (логируем ошибку).
          • strict_no_fallback=false → пробуем alt_voices по порядку (если выбранный явно голос тоже упал).
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
        print("Конфиг не найден. Положите рядом tts_config.json (см. пример).")
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
            "voice": val.get("voice", ""),
            "alt_voices": val.get("alt_voices", []) if isinstance(val.get("alt_voices", []), list) else [],
            "strict_no_fallback": bool(val.get("strict_no_fallback", False)),
            "markers": [str(x).lower() for x in val.get("markers", []) if str(x).strip()],
            "suffix_filter": {"enabled": bool(val.get("suffix_filter", {}).get("enabled", False)),
                              "suffix": str(val.get("suffix_filter", {}).get("suffix", ""))},
            "detect_prefixes": [str(x).lower() for x in val.get("detect_prefixes", []) if str(x).strip()],
            "voice_aliases": {str(k).lower(): str(v) for k, v in val.get("voice_aliases", {}).items()}
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
    return [s.lower() for s in vps if str(s).strip()]


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
    Также поддерживает сахарную форму '[EN:alias]' — как голос+язык вместе (обрабатывается в split_chunk_by_markers()).
    """
    # Голосовой маркер в круглых скобках
    pos = lower_text.find("(", start)
    best = None
    while pos != -1:
        # пример: (v:guy) или (voice:thomas)
        close = lower_text.find(")", pos + 1)
        if close == -1:
            break
        inside = lower_text[pos + 1:close].strip()  # например "v:guy"
        for pref in voice_prefixes:
            if inside.startswith(pref):
                alias = inside[len(pref):].strip()
                if alias:
                    best = (pos, alias.lower(), close + 1)
                    return best
        pos = lower_text.find("(", pos + 1)
    return None


def find_next_square_combo(lower_text: str, start: int) -> Optional[Tuple[int, str, Optional[str], int]]:
    """
    Ищем сахарную форму: [EN:guy], [RU:dmitry], [UK:polina]
    Возвращаем: (pos_open_bracket, lang_key_lower, alias_lower, end_index) или None.
    alias может быть None (если форма [EN] без двоеточия).
    """
    pos = lower_text.find("[", start)
    while pos != -1:
        close = lower_text.find("]", pos + 1)
        if close == -1:
            break
        inside = lower_text[pos + 1:close].strip()  # напр. "EN:guy"
        if inside:
            # Разделим по ':', левое как язык, правое как алиас голоса
            if ":" in inside:
                l, r = inside.split(":", 1)
                lang = l.strip().lower()
                alias = r.strip().lower()
                if lang:
                    return (pos, lang, alias if alias else None, close + 1)
            else:
                # просто [EN]
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
    Возвращаем список частей: (text_part, forced_lang_key, forced_voice_id_or_alias)
      - forced_lang_key: ключ языка ('en','ru','uk',...).
      - forced_voice_id_or_alias: строка-алиас/ID для выбора конкретного голоса (может быть None).
    Маркеры вырезаются из озвучки. При встрече нового маркера — предыдущий язык/голос заканчиваются.
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
            # съесть маркер языка
            j = pos + len(next_lang_mark)
            while j < len(s) and s[j] in " \t:—-–":
                j += 1
            curr_lang = next_lang_key
            curr_voice_alias = None  # при смене языка сбрасываем голос-алиас (если хочется сохранить — убери это)
            i = j
        elif typ == "voice":
            # съесть голосовой маркер
            _pos, alias_lower, j = vm
            curr_voice_alias = alias_lower
            i = j
            # язык не меняем
        else:  # typ == "sq"
            _pos, lang_lower, alias_lower, j = sq
            # язык из квадр. маркера — если он зарегистрирован
            # сопоставим lang_lower по detect_prefixes и ключам
            lang_key = None
            # точное совпадение по ключам
            if lang_lower in langs_cfg:
                lang_key = lang_lower
            else:
                # если пришло, например, 'en' — попробуем по detect_prefix
                for k, inf in langs_cfg.items():
                    for pref in inf.get("detect_prefixes", []):
                        if lang_lower == pref:
                            lang_key = k
                            break
                    if lang_key:
                        break
            if lang_key:
                curr_lang = lang_key
            # голос-алиас, если указан
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
    Возвращаем список фраз: (phrase_text, forced_lang_key, voice_alias_or_id, newline_count_after)
      - Режем по sentence_delimiters с подсчётом подряд идущих \n.
      - Внутри фрагмента делим по маркерам: языковым и голосовым.
      - Алиас/ID голоса сохраняем для каждой части.
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


def group_phrases_by_language(phrases: List[Tuple[str, Optional[str], Optional[str], int]], cfg: Dict) -> List[
    Tuple[str, List[Tuple[str, Optional[str], Optional[str], int]]]]:
    """
    Блоки: [(lang_key, [ (text, forced_lang, voice_alias, newline_count), ... ]), ...]
    Если forced_lang None — используем langdetect → detect_map.
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
# 7) Выбор голоса по алиасу/ID и fallback
# =============================================================================

def choose_voice_for_part(lang_key: str,
                          voice_alias_or_id: Optional[str],
                          cfg: Dict) -> Tuple[str, List[str], bool]:
    """
    Возвращает (primary_voice, alt_voices, strict_flag) для данного языка и части.
      - Если voice_alias_or_id задан:
          1) если он присутствует как ключ в voice_aliases → его значение (ID).
          2) иначе, если allow_partial_voice_match=true → ищем по подстроке в [voice]+alt_voices.
          3) иначе → основной voice.
      - alt_voices и strict берём из конфигурации языка (не от алиаса).
    """
    langs_cfg = get_languages_cfg(cfg)
    info = langs_cfg.get(lang_key, {})
    primary = info.get("voice", "")
    alts = info.get("alt_voices", []) if isinstance(info.get("alt_voices", []), list) else []
    strict = bool(info.get("strict_no_fallback", False))

    if not voice_alias_or_id:
        return primary, alts, strict

    alias = voice_alias_or_id.lower()
    # 1) По словарю алиасов
    aliases_map = {str(k).lower(): str(v) for k, v in info.get("voice_aliases", {}).items()}
    if alias in aliases_map:
        return aliases_map[alias], alts, strict

    # 2) По подстроке (если включено)
    if bool(cfg.get("allow_partial_voice_match", True)):
        candidates = [primary] + alts
        for vid in candidates:
            if alias in vid.lower():
                return vid, alts, strict

    # 3) По умолчанию
    return primary, alts, strict


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


async def tts_try_with_fallbacks(text: str,
                                 chosen_voice: str,
                                 alts: List[str],
                                 strict: bool,
                                 rate: int,
                                 out_path: Path) -> str:
    try:
        await tts_append_block(text, chosen_voice, rate, out_path)
        return chosen_voice
    except Exception as first_err:
        if strict:
            raise first_err
        # попробуем альтернативы (исключая тот же, если он уже в списке)
        last_err = first_err
        tried = set([chosen_voice.lower()])
        for v in alts:
            if v.lower() in tried:
                continue
            try:
                await tts_append_block(text, v, rate, out_path)
                return v
            except Exception as e:
                last_err = e
        raise last_err


# =============================================================================
# 8) Паузы между фразами и склейка
# =============================================================================

def glue_block_text(frs: List[Tuple[str, Optional[str], Optional[str], int]], cfg: Dict) -> List[
    Tuple[str, Optional[str]]]:
    """
    Возвращаем список (text_piece, voice_alias_or_id), но теперь:
      - паузы НЕ идут отдельными кусками;
      - все паузы «пришиваются» к следующему текстовому фрагменту.
    """
    pauses = cfg.get("pauses", {})
    base_ms = int(pauses.get("between_phrases_ms", 600))
    np_enabled = bool(pauses.get("newline_pause", {}).get("enabled", True))
    np_ms = int(pauses.get("newline_pause", {}).get("ms_per_newline", 400))
    start_line_ms = int(pauses.get("start_of_line_extra_pause_ms", 0))

    out: List[Tuple[str, Optional[str]]] = []
    first = True
    pending_prefix = ""  # сюда копим «запятые-паузы», чтоб потом добавить к следующему тексту

    for text, _forced_lang, voice_alias, nlcount in frs:
        if not text:
            continue

        if first:
            # первая фраза — без базовой паузы
            out.append((text, voice_alias))
            first = False
            continue

        # базовая пауза между фразами
        if base_ms > 0:
            pending_prefix += " " + make_pause_commas(base_ms) + " "

        # пауза за переносы (в т.ч. пустые строки)
        if np_enabled and nlcount > 0 and np_ms > 0:
            pending_prefix += " " + make_pause_commas(nlcount * np_ms) + " "

        # доп. пауза в начале строки
        if nlcount > 0 and start_line_ms > 0:
            pending_prefix += " " + make_pause_commas(start_line_ms) + " "

        # добавляем накопленные паузы в начало текущего текста
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
# 9) Рендеринг (single / multi-EN)
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
    out_path.write_bytes(b"")

    for i, (lang_key, frs) in enumerate(blocks, start=1):
        text_pieces = glue_block_text(frs, cfg)  # → [(text_part, voice_alias_or_id), ...]
        if not text_pieces:
            continue

        print(f"  [Блок {i}/{len(blocks)}] lang={lang_key}, частей={len(text_pieces)}")
        for idx, (piece, voice_alias) in enumerate(text_pieces, start=1):
            if not piece.strip():
                continue

                # если кусок состоит только из запятых/пробелов — пропустить
            if len(piece.strip().replace(",", "")) == 0:
                continue
            # выбрать голос для этой части
            chosen_voice, alts, strict = choose_voice_for_part(lang_key, voice_alias, cfg)
            try:
                used = await tts_try_with_fallbacks(piece, chosen_voice, alts, strict, rate, out_path)
                # можно логировать только смены/ошибки:
                # print(f"    [{lang_key} #{idx}] ✓ {used}")
            except Exception as e:
                print(f"    ! Ошибка части ({lang_key} #{idx}): {e} — пропуск части.")

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
        out_path.write_bytes(b"")
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        for i, (lang_key, frs) in enumerate(blocks, start=1):
            text_pieces = glue_block_text(frs, cfg)
            if not text_pieces:
                continue
            print(f"    [Блок {i}/{len(blocks)}] lang={lang_key}, частей={len(text_pieces)}")
            for idx, (piece, voice_alias) in enumerate(text_pieces, start=1):
                if not piece.strip():
                    continue
                if lang_key == "en":
                    # В мульти-режиме EN читаем строго заданным en_voice (без fallback)
                    try:
                        await tts_append_block(piece, en_voice, rate, out_path)
                    except Exception as e:
                        print(f"      ! Ошибка EN-части #{idx}: {e}")
                else:
                    # другие языки как обычно
                    chosen_voice, alts, strict = choose_voice_for_part(lang_key, voice_alias, cfg)
                    try:
                        used = await tts_try_with_fallbacks(piece, chosen_voice, alts, strict, rate, out_path)
                    except Exception as e:
                        print(f"      ! Ошибка части ({lang_key} #{idx}): {e} — пропуск.")

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
