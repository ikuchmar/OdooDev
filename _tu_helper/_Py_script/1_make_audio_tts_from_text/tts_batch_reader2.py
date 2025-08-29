# -*- coding: utf-8 -*-
"""
tts_batch_reader.py (v4)
- Читает конфиг tts_config.json рядом со скриптом.
- Ищет входные файлы по путям/маскам ОТ ПАПКИ СКРИПТА.
- Делит текст на предложения, группирует подряд идущие предложения по языку (EN/RU) в блоки.
- Синтезирует блоками (стабильнее для edge-tts), между предложениями в блоке вставляет "паузы" запятыми.
- Ретраи с альтернативными голосами, санация символов, корректный rate.
- Выходной MP3 создаётся рядом с исходником, с тем же именем (.mp3).

Зависимости: pip install edge-tts langdetect
"""

import asyncio
import json
import sys
import re
from pathlib import Path
from glob import glob
from typing import List, Dict, Tuple
from langdetect import detect
import edge_tts

CONFIG_NAME = "tts_config.json"

# -----------------------------
# Папка скрипта и конфиг
# -----------------------------

def script_dir() -> Path:
    return Path(__file__).resolve().parent

def ensure_config_exists(cfg_path: Path) -> bool:
    if cfg_path.exists():
        return True
    template = {
        "inputs": [
            "data/lesson1.txt",
            "data/lesson2.txt",
            "notes/*.md"
        ],
        "voice_en": "en-US-GuyNeural",
        "voice_ru": "ru-RU-DmitryNeural",
        "rate": -15,
        "pause": 600,
        "strip_emojis": True
    }
    cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Создан шаблон конфига: {cfg_path.name}\nОтредактируйте его и запустите скрипт ещё раз.")
    return False

def load_config(cfg_path: Path) -> Dict:
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Ошибка чтения {cfg_path.name}: {e}")
        sys.exit(1)

# -----------------------------
# Поиск файлов: относительные пути — от папки скрипта
# -----------------------------

def expand_inputs(patterns: List[str]) -> List[Path]:
    base = script_dir()
    seen = set()
    result = []
    for pat in patterns:
        p = Path(pat)
        if not p.is_absolute():
            p = (base / pat)
        matches = glob(str(p), recursive=True)
        if not matches and p.exists() and p.is_file():
            matches = [str(p)]
        for m in matches:
            fp = Path(m).resolve()
            if fp.is_file() and fp not in seen:
                seen.add(fp)
                result.append(fp)
    return result

# -----------------------------
# Текст → предложения → язык
# -----------------------------

def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def split_into_sentences(text: str) -> List[str]:
    # нормализуем переносы строк, чтобы не слипалось
    normalized = re.sub(r"\s*\n+\s*", ". ", text.strip())
    # грубое разбиение по ! ? . + пробелы
    parts = re.split(r"([.!?]+)\s+", normalized)
    sentences, buf = [], ""
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
    # уберём пустяки
    return [s for s in sentences if s and len(s) > 1]

def detect_lang_safe(text: str) -> str:
    try:
        lang = detect(text)
        if lang.startswith("ru"):
            return "ru"
        if lang.startswith("en"):
            return "en"
    except Exception:
        pass
    return "en"

# -----------------------------
# Санитизация проблемных символов
# -----------------------------

_EMOJI_RE = re.compile(
    "["                       # эмодзи и пиктограммы
    "\U0001F300-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE
)
_ALLOWED_RE = re.compile(r"[^A-Za-z\u00C0-\u024F\u0400-\u04FF0-9\s\.,!?\:\;\-\(\)\"'«»]+", re.UNICODE)

def sanitize_sentence(s: str) -> str:
    s = _EMOJI_RE.sub("", s)
    s = _ALLOWED_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[\.\,\!\?\:\;\-]+", "", s).strip()
    return s

def maybe_sanitize(s: str, enabled: bool) -> str:
    return sanitize_sentence(s) if enabled else s

# -----------------------------
# Группировка предложений по языку → блоки
# -----------------------------

def group_by_language_blocks(sentences: List[str], strip_emojis: bool) -> List[Tuple[str, List[str]]]:
    """
    Возвращает список блоков: [(lang, [sent1, sent2, ...]), ...]
    где lang ∈ {"en","ru"}.
    """
    blocks: List[Tuple[str, List[str]]] = []
    curr_lang = None
    curr_list: List[str] = []
    for s in sentences:
        s2 = maybe_sanitize(s, strip_emojis)
        if not s2:
            continue
        lang = detect_lang_safe(s2)
        if curr_lang is None:
            curr_lang, curr_list = lang, [s2]
        elif lang == curr_lang:
            curr_list.append(s2)
        else:
            blocks.append((curr_lang, curr_list))
            curr_lang, curr_list = lang, [s2]
    if curr_list:
        blocks.append((curr_lang, curr_list))
    return blocks

# -----------------------------
# TTS helpers
# -----------------------------

def build_rate_str(rate_pct: int) -> str:
    if rate_pct > 0:
        return f"+{rate_pct}%"
    if rate_pct < 0:
        return f"{rate_pct}%"
    return "+0%"

def make_pause_commas(pause_ms: int) -> str:
    if pause_ms <= 0:
        return ""
    approx_per_comma = 300  # эмпирически
    count = max(1, round(pause_ms / approx_per_comma))
    # пробелы вокруг — чтобы пауза отделялась от слов
    return " " + ("," * count) + " "

def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    """
    Склеиваем список предложений в один текст с "псевдопаузами" запятыми.
    """
    if not sentences:
        return ""
    sep = make_pause_commas(pause_ms)
    # гарантируем точку в конце каждого предложения (если пользователь не поставил)
    norm = [s if re.search(r"[.!?]$", s) else s + "." for s in sentences]
    return sep.join(norm)

async def tts_stream_to_file(text: str, voice: str, rate_pct: int, out_path: Path):
    """
    Один вызов edge-tts для блока текста → дописать MP3.
    """
    rate_str = build_rate_str(rate_pct)
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
    empty = True
    with out_path.open("ab") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                empty = False
                f.write(chunk["data"])
    if empty:
        raise RuntimeError("No audio was received")

async def tts_block_with_retries(text: str, lang: str, voices: List[str], rate_pct: int, out_path: Path):
    """
    Пытаемся синтезировать блок несколькими голосами по очереди.
    """
    last_err = None
    for v in voices:
        try:
            await tts_stream_to_file(text, v, rate_pct, out_path)
            return v  # успех — вернём голос, которым получилось
        except Exception as e:
            last_err = e
    # если ничего не вышло — пробросим последнюю ошибку
    raise last_err if last_err else RuntimeError("Unknown TTS error")

# -----------------------------
# Обработка одного файла
# -----------------------------

async def process_file(in_path: Path, cfg: Dict):
    print(f"\n=== Файл: {in_path}")
    text = read_text_file(in_path)
    if not text.strip():
        print("  Пустой файл — пропуск.")
        return

    sentences = split_into_sentences(text)
    if not sentences:
        print("  Не удалось разбить на предложения — пропуск.")
        return

    voice_en_primary = cfg.get("voice_en", "en-US-GuyNeural")
    voice_ru_primary = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    # Пулы альтернатив (можете подредактировать под свой вкус)
    voices_en = [voice_en_primary, "en-US-ChristopherNeural", "en-US-DavisNeural"]
    voices_ru = [voice_ru_primary, "ru-RU-SergeyNeural", "ru-RU-AndreiNeural"]

    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))
    strip_emojis = bool(cfg.get("strip_emojis", True))

    blocks = group_by_language_blocks(sentences, strip_emojis)
    if not blocks:
        print("  Нет валидных предложений (всё отфильтровано) — пропуск.")
        return

    out_path = in_path.with_suffix(".mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # обнулим/создадим
    with out_path.open("wb") as f:
        pass

    total_blocks = len(blocks)
    for idx, (lang, sents) in enumerate(blocks, start=1):
        text_block = glue_block_text(sents, pause_ms=pause)
        if not text_block.strip():
            continue
        # выберем пул голосов
        voices_pool = voices_ru if lang == "ru" else voices_en
        print(f"  [Блок {idx}/{total_blocks}] lang={lang.upper()}, предложений={len(sents)}, длина={len(text_block)}")

        try:
            used_voice = await tts_block_with_retries(text_block, lang, voices_pool, rate, out_path)
            print(f"    ✓ OK голос: {used_voice}")
        except Exception as e:
            print(f"    ! Ошибка синтеза блока: {e}. Пропуск блока.")

    print(f"  Готово: {out_path}")

# -----------------------------
# main
# -----------------------------

def main():
    cfg_path = script_dir() / CONFIG_NAME
    if not ensure_config_exists(cfg_path):
        return
    cfg = load_config(cfg_path)

    patterns = cfg.get("inputs", [])
    if not patterns or not isinstance(patterns, list):
        print("В конфиге 'inputs' должен быть списком путей/масок.")
        return

    files = expand_inputs(patterns)
    if not files:
        print("По маскам/путям из 'inputs' не найдено ни одного файла.")
        return

    for p in files:
        try:
            asyncio.run(process_file(p, cfg))
        except Exception as e:
            print(f"  Ошибка при обработке {p.name}: {e}")

if __name__ == "__main__":
    main()
