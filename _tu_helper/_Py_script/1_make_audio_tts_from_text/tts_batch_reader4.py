# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — простой и многокомментированный скрипт озвучивания текста.

Идея:
1) Берём конфиг tts_config.json (создаём шаблон, если его нет).
2) Ищем входные файлы (относительные пути считаем от папки, где лежит скрипт).
3) Для каждого файла:
   - читаем текст;
   - режем на предложения;
   - определяем язык предложений (en/ru/uk);
   - опционально чистим эмодзи и экзотические символы;
   - объединяем подряд идущие предложения одного языка в БЛОКИ;
   - озвучиваем по блокам (так надёжнее и звучит ровнее);
   - вставляем "паузы" между предложениями как несколько запятых (примерно 300мс на запятую).
4) Два режима вывода:
   - single: один MP3 (EN=voice_en (+ ретраи из alt_voices_en), RU=voice_ru, UA=voice_uk)
   - multi_en_outputs: много MP3 — для каждого голоса из alt_voices_en свой файл, RU/UA те же.

Зависимости: pip install edge-tts langdetect
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
# 1. БАЗОВЫЕ ВСПОМОГАТЕЛИ
# -----------------------------

def script_dir() -> Path:
    """Возвращает папку, где лежит этот скрипт."""
    return Path(__file__).resolve().parent


def load_or_create_config(cfg_path: Path) -> Dict:
    """
    Загружает tts_config.json.
    Если файла нет — создаёт шаблон и просит запустить ещё раз.
    """
    if not cfg_path.exists():
        template = {
            "inputs": ["data/lesson1.txt"],

            "enable_languages": ["en", "ru"],

            "voice_en": "en-GB-RyanNeural",
            "alt_voices_en": ["en-GB-RyanNeural", "en-GB-ThomasNeural", "en-US-RogerNeural"],

            "voice_ru": "ru-RU-DmitryNeural",

            "voice_uk": "uk-UA-OstapNeural",
            "alt_voices_uk": ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"],

            "rate": -15,
            "pause": 600,
            "strip_emojis": True,

            "multi_en_outputs": False
        }
        cfg_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Создан шаблон конфига: {cfg_path}\nОтредактируйте его и запустите скрипт ещё раз.")
        sys.exit(0)

    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Ошибка чтения {cfg_path.name}: {e}")
        sys.exit(1)


def expand_inputs(patterns: List[str]) -> List[Path]:
    """
    Превращает список путей/масок в список реальных файлов.
    Важно: относительные пути считаем от папки скрипта.
    """
    base = script_dir()
    files: List[Path] = []
    seen = set()

    for pat in patterns:
        p = Path(pat)
        if not p.is_absolute():
            p = base / pat

        matches = glob(str(p), recursive=True)
        if not matches and p.exists() and p.is_file():
            matches = [str(p)]

        for m in matches:
            f = Path(m).resolve()
            if f.is_file() and f not in seen:
                seen.add(f)
                files.append(f)

    return files


# -----------------------------
# 2. ПОДГОТОВКА ТЕКСТА
# -----------------------------

def read_text(path: Path) -> str:
    """Чтение файла в UTF-8 с игнорированием ошибок."""
    return path.read_text(encoding="utf-8", errors="ignore")


def split_into_sentences(text: str) -> List[str]:
    """
    Очень простой разрез текста на предложения.
    Подходит для учебных материалов: не идеален, но надёжен и без зависимостей.
    """
    # Переносы строк превращаем в ". " — так не слипнется
    text = re.sub(r"\s*\n+\s*", ". ", text.strip())

    # Режем по . ! ? + пробелы
    parts = re.split(r"([.!?]+)\s+", text)

    sentences: List[str] = []
    buf = ""
    for i, chunk in enumerate(parts):
        if i % 2 == 0:
            # текст до знака
            buf = chunk.strip()
        else:
            # сам знак
            buf += chunk
            if buf:
                sentences.append(buf.strip())
            buf = ""

    if buf:
        sentences.append(buf.strip())

    # Убираем мусорные коротыши
    sentences = [s for s in sentences if len(s) > 1]
    return sentences


def detect_lang_simple(s: str) -> str:
    """
    Определяем язык предложения: 'en', 'ru' или 'uk'.
    Если не удалось — считаем английским.
    """
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


# -----------------------------
# 3. ОЧИСТКА «ПРОБЛЕМНЫХ» СИМВОЛОВ
# -----------------------------

# Регулярки для удаления эмодзи и экзотических символов.
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
    """Если enabled=True — чистим эмодзи, экзотику, лишние пробелы и лидирующую пунктуацию."""
    if not enabled:
        return s.strip()

    s = _EMOJI_RE.sub("", s)
    s = _ALLOWED_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[\.\,\!\?\:\;\-]+", "", s).strip()
    return s


# -----------------------------
# 4. БЛОКИ ПО ЯЗЫКУ + ПАУЗЫ
# -----------------------------

def group_by_language(sentences: List[str], strip_emojis: bool) -> List[Tuple[str, List[str]]]:
    """
    Склеиваем подряд идущие предложения одного языка в блоки.
    Пример результата: [('en', [.., ..]), ('ru', [..]), ('en', [...])]
    """
    blocks: List[Tuple[str, List[str]]] = []

    current_lang = None
    current_list: List[str] = []

    for raw in sentences:
        s = sanitize_sentence(raw, strip_emojis)
        if not s:
            continue

        lang = detect_lang_simple(s)

        if current_lang is None:
            current_lang = lang
            current_list = [s]
            continue

        if lang == current_lang:
            current_list.append(s)
        else:
            blocks.append((current_lang, current_list))
            current_lang = lang
            current_list = [s]

    if current_list:
        blocks.append((current_lang, current_list))

    return blocks


def languages_present(blocks: List[Tuple[str, List[str]]]) -> Set[str]:
    """Какие языки вообще встретились в тексте файлов."""
    return {lang for lang, sents in blocks if sents}


def make_pause_commas(ms: int) -> str:
    """
    Возвращает строку из запятых для паузы.
    Примерно 300 мс на одну запятую (эмпирически).
    """
    if ms <= 0:
        return ""
    per = 300
    n = max(1, round(ms / per))
    return " " + ("," * n) + " "


def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    """
    Склеиваем предложения блока в одну строку с "псевдопаузами" (запятые).
    Гарантируем, что каждое предложение заканчивается ., ! или ?.
    """
    sep = make_pause_commas(pause_ms)
    fixed = []
    for s in sentences:
        if re.search(r"[.!?]$", s):
            fixed.append(s)
        else:
            fixed.append(s + ".")
    return sep.join(fixed)


def rate_to_str(rate: int) -> str:
    """edge-tts ожидает '+10%' или '-15%'. Для нуля — '+0%'."""
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"


# -----------------------------
# 5. НИЗКОУРОВНЕВЫЙ СИНТЕЗ
# -----------------------------

async def tts_append_block(text: str, voice: str, rate: int, out_path: Path) -> None:
    """
    Озвучивает один блок и ДОПИСЫВАЕТ результат в конец MP3-файла.
    Если TTS вернул пусто — бросаем исключение.
    """
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_to_str(rate))
    empty = True

    with out_path.open("ab") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                empty = False
                f.write(chunk["data"])

    if empty:
        raise RuntimeError("No audio was received")


async def tts_with_fallbacks(text: str, voices: List[str], rate: int, out_path: Path) -> str:
    """
    Пробуем озвучить текст несколькими голосами по очереди.
    Возвращаем имя первого сработавшего голоса.
    """
    last_err = None
    for v in voices:
        try:
            await tts_append_block(text, v, rate, out_path)
            return v
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("Unknown TTS error")


# -----------------------------
# 6. РЕНДЕРИНГ (2 РЕЖИМА)
# -----------------------------

async def render_single_output(in_path: Path, blocks: List[Tuple[str, List[str]]], cfg: Dict, enabled: Set[str]) -> None:
    """
    Режим одного выхода (один MP3).
    EN — voice_en, при неудаче ретраи по alt_voices_en.
    RU — voice_ru. UA — voice_uk.
    """
    voice_en = cfg.get("voice_en", "en-GB-RyanNeural")
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list):
        alt_en = []
    voices_en_try = [voice_en] + [v for v in alt_en if v != voice_en]

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")

    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    out_path = in_path.with_suffix(".mp3")
    out_path.write_bytes(b"")  # очищаем файл

    # Оставляем только те блоки, языки которых пользователь включил
    filtered = [(lang, sents) for (lang, sents) in blocks if lang in enabled]
    if not filtered:
        print("  Нет блоков после фильтра по enable_languages — пропуск.")
        return

    total = len(filtered)
    for i, (lang, sents) in enumerate(filtered, start=1):
        text_block = glue_block_text(sents, pause)
        if not text_block.strip():
            continue

        print(f"  [Блок {i}/{total}] lang={lang}, предложений={len(sents)}, длина={len(text_block)}")
        try:
            if lang == "ru":
                await tts_append_block(text_block, voice_ru, rate, out_path)
                print(f"    ✓ RU голос: {voice_ru}")
            elif lang == "uk":
                await tts_append_block(text_block, voice_uk, rate, out_path)
                print(f"    ✓ UA голос: {voice_uk}")
            else:
                used = await tts_with_fallbacks(text_block, voices_en_try, rate, out_path)
                print(f"    ✓ EN голос: {used}")
        except Exception as e:
            print(f"    ! Ошибка блока: {e} — пропуск.")

    print(f"  Готово: {out_path}")


async def render_multi_en_outputs(in_path: Path, blocks: List[Tuple[str, List[str]]], cfg: Dict, enabled: Set[str]) -> None:
    """
    Режим "по файлу на каждый EN-голос" из alt_voices_en.
    В каждом файле: RU — voice_ru, UA — voice_uk, EN — текущий голос из списка (без ретраев).
    Если EN в тексте отсутствует — файлы не создаём.
    """
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices_en пуст — нечего генерировать.")
        return

    # Если en выключен в enable_languages — смысла нет
    if "en" not in enabled:
        print("  multi_en_outputs=true, но 'en' отключён в enable_languages — пропуск EN-вариантов.")
        return

    # Если в тексте нет английских блоков — тоже пропускаем
    langs_here = languages_present(blocks)
    if "en" not in langs_here:
        print("  В файле нет английских блоков — EN-варианты не создаются.")
        return

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")
    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    # Отфильтруем блоки по enabled языкам (EN останется, так как выше проверили)
    filtered = [(lang, sents) for (lang, sents) in blocks if lang in enabled]

    for en_voice in alt_en:
        # В имени файла добавим суффикс с названием голоса
        stem = in_path.stem
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
                    await tts_append_block(text_block, voice_ru, rate, out_path)
                    print(f"      ✓ RU: {voice_ru}")
                elif lang == "uk":
                    await tts_append_block(text_block, voice_uk, rate, out_path)
                    print(f"      ✓ UA: {voice_uk}")
                else:
                    # В мульти-режиме EN — строго текущим голосом, без ретраев, чтобы файл был «чистым» под голос
                    await tts_append_block(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN: {en_voice}")
            except Exception as e:
                print(f"      ! Ошибка блока: {e} — пропуск блока в этом EN-варианте.")

        print(f"  Готово: {out_path}")


# -----------------------------
# 7. ОСНОВНОЙ ЦИКЛ ПО ФАЙЛАМ
# -----------------------------

async def process_one_file(path: Path, cfg: Dict) -> None:
    """Озвучивает один файл по настройкам из cfg."""
    print(f"\n=== Файл: {path}")

    text = read_text(path)
    if not text.strip():
        print("  Пустой файл — пропуск.")
        return

    # Разбиваем на предложения
    sentences = split_into_sentences(text)
    if not sentences:
        print("  Не удалось разбить текст на предложения — пропуск.")
        return

    # Формируем блоки по языкам
    strip_emojis = bool(cfg.get("strip_emojis", True))
    blocks = group_by_language(sentences, strip_emojis)
    if not blocks:
        print("  После очистки не осталось текста — пропуск.")
        return

    # Какие языки пользователь хочет озвучивать
    enabled_list = cfg.get("enable_languages", ["en", "ru"])
    if not isinstance(enabled_list, list) or not enabled_list:
        enabled_list = ["en", "ru"]
    enabled = set(enabled_list)

    # Если в файле нет ни одного блока из включённых языков — ничего не делаем
    if not any(lang in enabled for lang, _ in blocks):
        print("  Языки файла не входят в enable_languages — пропуск.")
        return

    # Режим: одиночный файл или много EN-вариантов
    if bool(cfg.get("multi_en_outputs", False)):
        await render_multi_en_outputs(path, blocks, cfg, enabled)
    else:
        await render_single_output(path, blocks, cfg, enabled)


def main():
    cfg_path = script_dir() / "tts_config.json"
    cfg = load_or_create_config(cfg_path)

    # Собираем список входных файлов
    patterns = cfg.get("inputs", [])
    if not isinstance(patterns, list) or not patterns:
        print("В конфиге 'inputs' должен быть непустым списком путей/масок.")
        sys.exit(1)
    files = expand_inputs(patterns)
    if not files:
        print("По 'inputs' не найдено ни одного файла.")
        sys.exit(1)

    # Идём по всем файлам последовательно
    for p in files:
        try:
            asyncio.run(process_one_file(p, cfg))
        except Exception as e:
            print(f"  Ошибка при обработке {p.name}: {e}")


if __name__ == "__main__":
    main()
