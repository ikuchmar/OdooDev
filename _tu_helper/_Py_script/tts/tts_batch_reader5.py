# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — простой многокомментированный скрипт озвучивания текста (RU/EN/UA)
v7: добавлены опциональные фильтры по суффиксам имени файла для каждого языка (en/ru/uk)

Идея работы:
1) Читаем конфиг tts_config.json (создаём шаблон, если его нет).
2) Собираем входные файлы (относительные пути считаем от папки скрипта).
3) Для каждого файла:
   - читаем текст, режем на предложения, определяем язык каждого предложения (en/ru/uk);
   - очищаем эмодзи/экзотику при необходимости;
   - объединяем подряд идущие предложения одного языка в блоки (стабильнее и качественнее);
   - применяем правила:
        a) enable_languages — какие языки вообще озвучивать;
        b) suffix_filters — если для языка правило включено, озвучиваем блоки этого языка
           только если ИМЯ ФАЙЛА (stem) оканчивается на заданный суффикс (например "_en").
   - режимы вывода:
        - single (multi_en_outputs=false): один mp3 с EN=voice_en (+ ретраи из alt_voices_en),
          RU=voice_ru, UA=voice_uk;
        - multi_en_outputs=true: набор файлов для каждого EN-голоса из alt_voices_en.
          Если включен suffix-фильтр для EN и файл не соответствует суффиксу — EN-варианты не делаем.

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


# -----------------------------------------------------------------------------
# 1) Работа с конфигом и входными файлами
# -----------------------------------------------------------------------------

def script_dir() -> Path:
    """Папка, где лежит этот скрипт."""
    return Path(__file__).resolve().parent


def load_or_create_config(cfg_path: Path) -> Dict:
    """
    Загружаем конфиг. Если отсутствует — создаём шаблон и выходим, чтобы пользователь отредактировал.
    """
    if not cfg_path.exists():
        template = {
            "inputs": ["data/lesson1_en.txt"],

            "enable_languages": ["en", "ru", "uk"],

            "voice_en": "en-GB-RyanNeural",
            "alt_voices_en": ["en-GB-RyanNeural", "en-GB-ThomasNeural", "en-US-RogerNeural"],

            "voice_ru": "ru-RU-DmitryNeural",

            "voice_uk": "uk-UA-OstapNeural",
            "alt_voices_uk": ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"],

            "rate": -15,
            "pause": 600,
            "strip_emojis": True,

            "multi_en_outputs": False,

            "suffix_filters": {
                "en": {"enabled": True, "suffix": "_en"},
                "ru": {"enabled": False, "suffix": "_ru"},
                "uk": {"enabled": False, "suffix": "_uk"}
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


def expand_inputs(patterns: List[str]) -> List[Path]:
    """
    Превращаем список путей/масок в список реальных файлов.
    Относительные пути интерпретируем ОТ ПАПКИ СКРИПТА — так надёжнее.
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


# -----------------------------------------------------------------------------
# 2) Подготовка текста: чтение, разбиение на предложения, детекция языка, очистка
# -----------------------------------------------------------------------------

def read_text(path: Path) -> str:
    """Читаем файл в UTF-8 (игнорируя ошибки)."""
    return path.read_text(encoding="utf-8", errors="ignore")


def split_into_sentences(text: str) -> List[str]:
    """
    Очень простой, но рабочий разбор текста на предложения:
    - переносы строк -> ". "
    - режем по . ! ? + пробелы
    """
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

    # убираем мусорные коротыши
    return [s for s in sentences if len(s) > 1]


def detect_lang_simple(s: str) -> str:
    """
    Определяем язык предложения: 'en', 'ru', 'uk'.
    Если не распознали — считаем 'en'.
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


# Очистка от эмодзи и «экзотики», чтобы TTS не «молчал».
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


# -----------------------------------------------------------------------------
# 3) Блоки по языку + паузы
# -----------------------------------------------------------------------------

def group_by_language(sentences: List[str], strip_emojis: bool) -> List[Tuple[str, List[str]]]:
    """
    Объединяем подряд идущие предложения одного языка в блоки.
    Пример: [('en',[...]), ('ru',[...]), ('en',[...])]
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
    """Какие языки реально есть в тексте (по блокам)."""
    return {lang for lang, sents in blocks if sents}


def make_pause_commas(ms: int) -> str:
    """
    Возвращает строку из запятых для имитации паузы.
    Примерно ~300 мс на одну запятую (эмпирически).
    """
    if ms <= 0:
        return ""
    per = 300
    n = max(1, round(ms / per))
    return " " + ("," * n) + " "


def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    """
    Склеиваем предложения блока в один текст.
    Если в конце предложения нет . ! ? — добавляем точку.
    Между предложениями вставляем "псевдопаузу" запятыми.
    """
    sep = make_pause_commas(pause_ms)
    fixed = [(s if re.search(r"[.!?]$", s) else s + ".") for s in sentences]
    return sep.join(fixed)


def rate_to_str(rate: int) -> str:
    """edge-tts ожидает '+10%' или '-15%'; для нуля — '+0%'."""
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"


# -----------------------------------------------------------------------------
# 4) Низкоуровневый синтез (edge-tts)
# -----------------------------------------------------------------------------

async def tts_append_block(text: str, voice: str, rate: int, out_path: Path) -> None:
    """
    Озвучиваем один текстовый блок, дозаписываем MP3 в конец файла.
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
    Пробуем несколько голосов по очереди. Возвращаем первый успешный.
    """
    last_err = None
    for v in voices:
        try:
            await tts_append_block(text, v, rate, out_path)
            return v
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("Unknown TTS error")


# -----------------------------------------------------------------------------
# 5) Фильтр по суффиксам имени файла (новое в v7)
# -----------------------------------------------------------------------------

def get_suffix_filters(cfg: Dict) -> Dict[str, Dict[str, object]]:
    """
    Возвращает структуру вида:
        {
          "en": {"enabled": True/False, "suffix": "_en"},
          "ru": {"enabled": True/False, "suffix": "_ru"},
          "uk": {"enabled": True/False, "suffix": "_uk"}
        }
    Если чего-то нет — подставляем разумные дефолты.
    """
    sf = cfg.get("suffix_filters", {})

    def one(lang, default_suffix):
        settings = sf.get(lang, {})
        return {
            "enabled": bool(settings.get("enabled", False)),
            "suffix": str(settings.get("suffix", default_suffix))
        }

    return {
        "en": one("en", "_en"),
        "ru": one("ru", "_ru"),
        "uk": one("uk", "_uk"),
    }


def lang_allowed_for_file(lang: str, file_stem: str, suffix_filters: Dict[str, Dict[str, object]]) -> bool:
    """
    Проверяем суффикс-правило для конкретного языка и файла.
    Если для языка правило выключено — разрешаем.
    Если включено — разрешаем только если имя файла (stem) оканчивается на указанный суффикс.
    """
    rule = suffix_filters.get(lang, {"enabled": False, "suffix": ""})
    if not rule["enabled"]:
        return True
    suffix = str(rule["suffix"])
    return file_stem.endswith(suffix)


# -----------------------------------------------------------------------------
# 6) Рендеринг (один файл / несколько EN-файлов)
# -----------------------------------------------------------------------------

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[str]]],
                               cfg: Dict,
                               enabled: Set[str],
                               suffix_filters: Dict[str, Dict[str, object]]) -> None:
    """
    Один итоговый MP3:
      - EN: основной voice_en с ретраями по alt_voices_en
      - RU: voice_ru
      - UK: voice_uk
    При этом для каждого языка дополнительно проверяем суффикс-правило.
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

    # Имя файла без расширения — пригодится для проверки суффиксов
    stem = in_path.stem

    # Фильтруем блоки:
    # 1) язык должен быть включён в enable_languages
    # 2) файл должен соответствовать суффиксу для этого языка, если правило включено
    filtered = []
    for (lang, sents) in blocks:
        if lang not in enabled:
            continue
        if not lang_allowed_for_file(lang, stem, suffix_filters):
            continue
        filtered.append((lang, sents))

    if not filtered:
        print("  После фильтра по enable_languages и суффиксам блоков не осталось — пропуск.")
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
                await tts_append_block(text_block, voice_ru, rate, out_path)
                print(f"    ✓ RU голос: {voice_ru}")
            elif lang == "uk":
                await tts_append_block(text_block, voice_uk, rate, out_path)
                print(f"    ✓ UA голос: {voice_uk}")
            else:  # en
                used = await tts_with_fallbacks(text_block, voices_en_try, rate, out_path)
                print(f"    ✓ EN голос: {used}")
        except Exception as e:
            print(f"    ! Ошибка блока: {e} — пропуск.")

    print(f"  Готово: {out_path}")


async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[str]]],
                                  cfg: Dict,
                                  enabled: Set[str],
                                  suffix_filters: Dict[str, Dict[str, object]]) -> None:
    """
    Несколько MP3: для каждого EN-голоса из alt_voices_en отдельный файл.
    В каждом файле:
      - EN — текущим голосом (без ретраев, чтобы вариант был «чистым»),
      - RU — voice_ru,
      - UK — voice_uk.
    ВНИМАНИЕ к суффиксам:
      - если для EN включён суффикс-фильтр и файл НЕ оканчивается нужным суффиксом,
        то EN-варианты НЕ создаём (смысла нет).
      - для RU/UK внутри каждого файла суффикс-фильтры также учитываются.
    """
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices_en пуст — нечего генерировать.")
        return

    # Если en не включён — EN-варианты не делаем
    if "en" not in enabled:
        print("  multi_en_outputs=true, но 'en' отключён в enable_languages — пропуск EN-вариантов.")
        return

    # Суффикс-проверка только для EN: если включено — имя файла должно соответствовать
    stem = in_path.stem
    if not lang_allowed_for_file("en", stem, suffix_filters):
        print("  EN суффикс-фильтр активен, но файл не соответствует — EN-варианты не создаются.")
        return

    # Проверим, что в тексте вообще есть английские блоки (иначе тоже не создаём)
    langs_in_text = languages_present(blocks)
    if "en" not in langs_in_text:
        print("  В файле нет английских блоков — EN-варианты не создаются.")
        return

    # Остальные голоса/настройки
    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")
    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    # На каждый EN-голос — отдельный mp3
    for en_voice in alt_en:
        out_path = in_path.with_name(f"{stem}__{en_voice}.mp3")
        out_path.write_bytes(b"")
        print(f"\n  → Генерация EN-варианта голосом: {en_voice}")

        # Внутри файла тоже фильтруем блоки:
        # - язык должен быть в enable_languages,
        # - файл должен соответствовать суффиксу языка (если включён).
        filtered = []
        for (lang, sents) in blocks:
            if lang not in enabled:
                continue
            if not lang_allowed_for_file(lang, stem, suffix_filters):
                continue
            filtered.append((lang, sents))

        if not filtered:
            print("    Нет блоков после фильтра по enable_languages и суффиксам — пропуск этого EN-варианта.")
            continue

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
                    await tts_append_block(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN: {en_voice}")
            except Exception as e:
                print(f"      ! Ошибка блока: {e} — пропуск блока в этом EN-варианте.")

        print(f"  Готово: {out_path}")


# -----------------------------------------------------------------------------
# 7) Основной цикл по файлам
# -----------------------------------------------------------------------------

async def process_one_file(path: Path, cfg: Dict) -> None:
    """Озвучивание одного файла по настройкам."""
    print(f"\n=== Файл: {path}")

    text = read_text(path)
    if not text.strip():
        print("  Пустой файл — пропуск.")
        return

    sentences = split_into_sentences(text)
    if not sentences:
        print("  Не удалось разбить текст на предложения — пропуск.")
        return

    # Формируем блоки
    strip_emojis = bool(cfg.get("strip_emojis", True))
    blocks = group_by_language(sentences, strip_emojis)
    if not blocks:
        print("  После очистки не осталось текста — пропуск.")
        return

    # Какие языки пользователь разрешил
    enabled_list = cfg.get("enable_languages", ["en", "ru"])
    if not isinstance(enabled_list, list) or not enabled_list:
        enabled_list = ["en", "ru"]
    enabled = set(enabled_list)

    # Фильтры по суффиксам для каждого языка
    suffix_filters = get_suffix_filters(cfg)

    # Если после применения обоих условий (enable + suffix) не останется блоков — просто завершим.
    stem = path.stem
    any_ok = False
    for (lang, _sents) in blocks:
        if lang in enabled and lang_allowed_for_file(lang, stem, suffix_filters):
            any_ok = True
            break
    if not any_ok:
        print("  Ни один язык файла не прошёл фильтры enable_languages/суффиксов — пропуск.")
        return

    # Выбор режима
    if bool(cfg.get("multi_en_outputs", False)):
        await render_multi_en_outputs(path, blocks, cfg, enabled, suffix_filters)
    else:
        await render_single_output(path, blocks, cfg, enabled, suffix_filters)


def main():
    cfg_path = script_dir() / "tts_config.json"
    cfg = load_or_create_config(cfg_path)

    patterns = cfg.get("inputs", [])
    if not isinstance(patterns, list) or not patterns:
        print("В конфиге 'inputs' должен быть непустой список путей/масок.")
        sys.exit(1)

    files = expand_inputs(patterns)
    if not files:
        print("По 'inputs' не найдено ни одного файла.")
        sys.exit(1)

    for p in files:
        try:
            asyncio.run(process_one_file(p, cfg))
        except Exception as e:
            print(f"  Ошибка при обработке {p.name}: {e}")


if __name__ == "__main__":
    main()
