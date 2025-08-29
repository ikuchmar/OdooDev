# -*- coding: utf-8 -*-
"""
tts_batch_reader.py (v5: multi_en_outputs)

Функциональность:
- Читает конфиг tts_config.json рядом со скриптом.
- Пути/маски файлов в inputs трактуются относительно папки скрипта.
- Делит текст на предложения, группирует подряд идущие предложения по языку (EN/RU) в блоки.
- Паузы между предложениями реализованы через "запятые" (эмоциональная пауза ~300мс/запятая).
- Санитизация "проблемных" символов (эмодзи и т.п.) при strip_emojis=true.
- ОДИН файл (multi_en_outputs=false): EN=voice_en с ретраями по alt_voices_en; RU=voice_ru.
- НЕСКОЛЬКО файлов (multi_en_outputs=true): для каждого голоса из alt_voices_en делаем отдельный MP3:
  английские блоки — этим голосом, русские — voice_ru. Имя файла получает суффикс __<VOICE>.

Зависимости:
pip install edge-tts langdetect
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
# Вспомогательные утилиты
# -----------------------------

def script_dir() -> Path:
    """Папка, где лежит данный скрипт."""
    return Path(__file__).resolve().parent

def ensure_config_exists(cfg_path: Path) -> bool:
    """
    Если конфига нет — создаём шаблон и просим пользователя отредактировать.
    Возвращаем False (чтобы завершить текущий запуск).
    """
    if cfg_path.exists():
        return True
    template = {
        "inputs": [
            "data/lesson1.txt"
        ],
        "voice_en": "en-GB-RyanNeural",
        "alt_voices_en": [
            "en-GB-RyanNeural",
            "en-GB-ThomasNeural",
            "en-US-GuyNeural"
        ],
        "voice_ru": "ru-RU-DmitryNeural",
        "rate": -15,
        "pause": 600,
        "strip_emojis": True,
        "multi_en_outputs": False
    }
    cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Создан шаблон конфига: {cfg_path.name}\nОтредактируйте его и запустите скрипт ещё раз.")
    return False

def load_config(cfg_path: Path) -> Dict:
    """Загрузить конфиг JSON."""
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Ошибка чтения {cfg_path.name}: {e}")
        sys.exit(1)

def expand_inputs(patterns: List[str]) -> List[Path]:
    """
    Разворачиваем маски/пути в список реальных файлов.
    Относительные пути считаем ОТ ПАПКИ СКРИПТА.
    """
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

def read_text_file(path: Path) -> str:
    """Читаем файл UTF-8 с игнорированием ошибок."""
    return path.read_text(encoding="utf-8", errors="ignore")

# -----------------------------
# Разбиение на предложения и определение языка
# -----------------------------

def split_into_sentences(text: str) -> List[str]:
    """
    Очень простой токенайзер предложений:
    - переносы строк превращаем в ". "
    - режем по . ! ? с пробелами
    - возвращаем непустые куски
    """
    normalized = re.sub(r"\s*\n+\s*", ". ", text.strip())
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
    return [s for s in sentences if s and len(s) > 1]

def detect_lang_safe(text: str) -> str:
    """Возвращаем 'ru' или 'en'. Если не распознано — 'en'."""
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
# Санитизация "проблемных" символов
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
    """Удаляем эмодзи/нестандарт, сжимаем пробелы, убираем ведущую пунктуацию."""
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
    где lang ∈ {"en","ru"} и предложения идут подряд одним языком.
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
# Подготовка текста блока и паузы
# -----------------------------

def make_pause_commas(pause_ms: int) -> str:
    """Возвращаем строку из нескольких запятых для эмуляции паузы."""
    if pause_ms <= 0:
        return ""
    approx_per_comma = 300  # эмпирически ~300мс на одну запятую
    count = max(1, round(pause_ms / approx_per_comma))
    return " " + ("," * count) + " "

def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    """
    Склеиваем список предложений в один текст с "псевдопаузами" запятыми.
    Следим, чтобы каждое предложение заканчивалось . ! ? (если нет — добавим точку).
    """
    if not sentences:
        return ""
    sep = make_pause_commas(pause_ms)
    norm = [s if re.search(r"[.!?]$", s) else s + "." for s in sentences]
    return sep.join(norm)

def build_rate_str(rate_pct: int) -> str:
    """edge-tts любит явный знак у процента скорости."""
    if rate_pct > 0:
        return f"+{rate_pct}%"
    if rate_pct < 0:
        return f"{rate_pct}%"
    return "+0%"

# -----------------------------
# Низкоуровневый синтез
# -----------------------------

async def tts_stream_to_file(text: str, voice: str, rate_pct: int, out_path: Path):
    """
    Один вызов edge-tts для блока текста → дописать MP3.
    Бросаем RuntimeError("No audio was received"), если поток пуст.
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

async def tts_block_with_retries(text: str, voices: List[str], rate_pct: int, out_path: Path) -> str:
    """
    Синтез блока с последовательной попыткой нескольких голосов (возвращаем имя сработавшего голоса).
    Используется в "одиночном" режиме (multi_en_outputs=false).
    """
    last_err = None
    for v in voices:
        try:
            await tts_stream_to_file(text, v, rate_pct, out_path)
            return v
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("Unknown TTS error")

# -----------------------------
# Обработка одного файла — два режима
# -----------------------------

async def render_single_output(in_path: Path, blocks: List[Tuple[str, List[str]]], cfg: Dict):
    """
    Режим: один итоговый MP3.
    EN — сначала voice_en, при неудаче ретраи по alt_voices_en.
    RU — voice_ru.
    """
    voice_en = cfg.get("voice_en", "en-GB-RyanNeural")
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list):
        alt_en = []
    voices_en_pool = [voice_en] + [v for v in alt_en if v != voice_en]

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    out_path = in_path.with_suffix(".mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        pass

    total_blocks = len(blocks)
    for idx, (lang, sents) in enumerate(blocks, start=1):
        text_block = glue_block_text(sents, pause_ms=pause)
        if not text_block.strip():
            continue
        print(f"  [Блок {idx}/{total_blocks}] lang={lang.upper()}, предложений={len(sents)}, длина={len(text_block)}")
        try:
            if lang == "ru":
                await tts_stream_to_file(text_block, voice_ru, rate, out_path)
                print(f"    ✓ RU голос: {voice_ru}")
            else:
                used_voice = await tts_block_with_retries(text_block, voices_en_pool, rate, out_path)
                print(f"    ✓ EN голос: {used_voice}")
        except Exception as e:
            print(f"    ! Ошибка синтеза блока: {e}. Пропуск блока.")

    print(f"  Готово: {out_path}")

async def render_multi_outputs_en(in_path: Path, blocks: List[Tuple[str, List[str]]], cfg: Dict):
    """
    Режим: отдельный MP3 для каждого EN-голоса из alt_voices_en.
    В каждом файле: RU-блоки = voice_ru, EN-блоки = текущий en_voice.
    Имя файла: <basename>__<VOICE>.mp3
    """
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices_en пуст — нечего генерировать.")
        return

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    for en_voice in alt_en:
        # формируем имя файла с суффиксом голоса
        stem = in_path.stem
        safe_suffix = en_voice  # можно оставить как есть; при желании заменить ':'/пробелы и т.п.
        out_path = in_path.with_name(f"{stem}__{safe_suffix}.mp3")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            pass

        print(f"\n  → Генерация варианта EN голосом: {en_voice}")
        total_blocks = len(blocks)
        for idx, (lang, sents) in enumerate(blocks, start=1):
            text_block = glue_block_text(sents, pause_ms=pause)
            if not text_block.strip():
                continue
            print(f"    [Блок {idx}/{total_blocks}] lang={lang.upper()}, предложений={len(sents)}, длина={len(text_block)}")
            try:
                if lang == "ru":
                    await tts_stream_to_file(text_block, voice_ru, rate, out_path)
                    print(f"      ✓ RU голос: {voice_ru}")
                else:
                    # В МУЛЬТИ-режиме НЕ переключаемся на другие EN-голоса, иначе файл потеряет смысл.
                    await tts_stream_to_file(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN голос: {en_voice}")
            except Exception as e:
                print(f"      ! Ошибка синтеза блока: {e}. Этот блок пропущен в данном варианте.")

        print(f"  Готово: {out_path}")

# -----------------------------
# Основной поток обработки
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

    strip_emojis = bool(cfg.get("strip_emojis", True))
    blocks = group_by_language_blocks(sentences, strip_emojis)
    if not blocks:
        print("  Нет валидных предложений (всё отфильтровано) — пропуск.")
        return

    multi_en_outputs = bool(cfg.get("multi_en_outputs", False))
    if multi_en_outputs:
        await render_multi_outputs_en(in_path, blocks, cfg)
    else:
        await render_single_output(in_path, blocks, cfg)

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
