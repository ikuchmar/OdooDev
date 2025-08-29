# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — простой многокомментированный скрипт озвучивания текста (RU/EN/UA)
v11:
  - Fallback-логика есть для EN, RU, UK.
  - Добавлены флаги строгого режима: en_strict_no_fallback, ru_strict_no_fallback, uk_strict_no_fallback.
  - Остальное как прежде: рекурсивный сбор входных, суффикс-фильтры, «паузы» запятыми, 2 режима вывода.

Зависимости:
    pip install edge-tts langdetect
"""

import asyncio
import json
import re
import sys
from glob import glob
from pathlib import Path
from typing import List, Tuple, Dict, Set

import edge_tts
from langdetect import detect


# -----------------------------
# 1) Конфиг и сбор входных файлов
# -----------------------------

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
            }
        }
        cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Создан шаблон конфига: {cfg_path}\nОтредактируйте его и запустите скрипт ещё раз.")
        sys.exit(0)

    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
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


# -----------------------------
# 2) Текст → предложения → язык → очистка
# -----------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def split_into_sentences(text: str) -> List[str]:
    text = re.sub(r"\s*\n+\s*", ". ", text.strip())
    parts = re.split(r"([.!?]+)\s+", text)
    sentences: List[str] = []
    buf = ""
    for i, chunk in enumerate(parts):
        if i % 2 == 0:
            buf = chunk.strip()
        else:
            buf += chunk
            if buf:
                sentences.append(buf.strip())
            buf = ""
    if buf:
        sentences.append(buf.strip())
    return [s for s in sentences if len(s) > 1]

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

def sanitize_sentence(s: str, enabled: bool) -> str:
    if not enabled:
        return s.strip()
    s = _EMOJI_RE.sub("", s)
    s = _ALLOWED_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[\.\,\!\?\:\;\-]+", "", s).strip()
    return s


# -----------------------------
# 3) Блоки по языку и паузы
# -----------------------------

def group_by_language(sentences: List[str], strip_emojis: bool) -> List[Tuple[str, List[str]]]:
    blocks: List[Tuple[str, List[str]]] = []
    current_lang = None
    current_list: List[str] = []
    for raw in sentences:
        s = sanitize_sentence(raw, strip_emojis)
        if not s:
            continue
        lang = detect_lang_simple(s)
        if current_lang is None:
            current_lang, current_list = lang, [s]
            continue
        if lang == current_lang:
            current_list.append(s)
        else:
            blocks.append((current_lang, current_list))
            current_lang, current_list = lang, [s]
    if current_list:
        blocks.append((current_lang, current_list))
    return blocks

def languages_present(blocks: List[Tuple[str, List[str]]]) -> Set[str]:
    return {lang for lang, sents in blocks if sents}

def make_pause_commas(ms: int) -> str:
    if ms <= 0:
        return ""
    n = max(1, round(ms / 300))
    return " " + ("," * n) + " "

def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    sep = make_pause_commas(pause_ms)
    fixed = [(s if re.search(r"[.!?]$", s) else s + ".") for s in sentences]
    return sep.join(fixed)

def rate_to_str(rate: int) -> str:
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"


# -----------------------------
# 4) Низкоуровневый синтез и универсальный fallback
# -----------------------------

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
    """
    Сначала пробуем primary; если allow_fallback=True и ошибка/пусто — пробуем alt-голоса по очереди.
    Возвращаем имя голоса, которым получилось озвучить.
    """
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


# -----------------------------
# 5) Суффикс-фильтры и выбор активных языков
# -----------------------------

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


# -----------------------------
# 6) Рендеринг
# -----------------------------

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[str]]],
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

    # Фильтруем блоки по активным языкам
    filtered = [(lang, sents) for (lang, sents) in blocks if lang in active_langs]
    if not filtered:
        print("  После выбора активных языков блоков не осталось — пропуск.")
        return

    out_path = in_path.with_suffix(".mp3")
    out_path.write_bytes(b"")

    total = len(filtered)
    for i, (lang, sents) in enumerate(filtered, start=1):
        text_block = glue_block_text(sents, pause)
        if not text_block.strip():
            continue
        print(f"  [Блок {i}/{total}] lang={lang}, предложений={len(sents)}, длина={len(text_block)}")
        try:
            if lang == "ru":
                used = await tts_try_primary_then_alts(text_block, voice_ru, alt_ru, not ru_strict, rate, out_path)
                print(f"    ✓ RU голос: {used}")
            elif lang == "uk":
                used = await tts_try_primary_then_alts(text_block, voice_uk, alt_uk, not uk_strict, rate, out_path)
                print(f"    ✓ UA голос: {used}")
            else:  # en
                used = await tts_try_primary_then_alts(text_block, voice_en, alt_en, not en_strict, rate, out_path)
                print(f"    ✓ EN голос: {used}")
        except Exception as e:
            print(f"    ! Ошибка блока: {e} — пропуск.")

    print(f"  Готово: {out_path}")

async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[str]]],
                                  cfg: Dict,
                                  active_langs: Set[str]) -> None:
    # EN-варианты создаём только если EN активен и есть EN-блоки
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

    # RU/UK их строгие флаги и альтернативы
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

    # Блоки только активных языков
    filtered = [(lang, sents) for (lang, sents) in blocks if lang in active_langs]
    if not filtered:
        print("  После выбора активных языков блоков не осталось — пропуск EN-вариантов.")
        return

    stem = in_path.stem
    for en_voice in alt_en:
        out_path = in_path.with_name(f"{stem}__{en_voice}.mp3")
        out_path.write_bytes(b"")
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        total = len(filtered)
        for i, (lang, sents) in enumerate(filtered, start=1):
            text_block = glue_block_text(sents, pause)
            if not text_block.strip():
                continue
            print(f"    [Блок {i}/{total}] lang={lang}, предложений={len(sents)}, длина={len(text_block)}")
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


# -----------------------------
# 7) Основной цикл по файлам
# -----------------------------

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

    text = read_text(path)
    if not text.strip():
        print("  Пустой файл — пропуск.")
        return

    sentences = split_into_sentences(text)
    if not sentences:
        print("  Не удалось разбить текст на предложения — пропуск.")
        return

    strip_emojis = bool(cfg.get("strip_emojis", True))
    blocks = group_by_language(sentences, strip_emojis)
    if not blocks:
        print("  После очистки не осталось текста — пропуск.")
        return

    enable_languages = cfg.get("enable_languages", ["en", "ru"])
    if not isinstance(enable_languages, list) or not enable_languages:
        enable_languages = ["en", "ru"]

    suffix_filters = get_suffix_filters(cfg)
    stem = path.stem
    active_langs = pick_active_languages_for_file(stem, enable_languages, suffix_filters)

    present = languages_present(blocks)
    if not (active_langs & present):
        print(f"  В тексте нет блоков для активных языков {sorted(active_langs)} — пропуск.")
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
