# -*- coding: utf-8 -*-
"""
tts_batch_reader.py — простой многокомментированный скрипт озвучивания текста (RU/EN/UA)
v9: логика "жёсткого суффикса" — если включён и совпал, озвучиваем только этим языком,
    иначе озвучиваем всеми из enable_languages.

Что умеет:
- Читает tts_config.json (создаёт шаблон при первом запуске).
- Собирает входные файлы из "inputs":
    • маски с ** работают как есть (glob recursive)
    • маски вида "data/*.txt" — при recursive_inputs=true дополнительно расширяются до "data/**/*.txt"
    • если указана папка — берём все файлы с расширениями из "extensions" рекурсивно
- Делит текст на предложения, определяет язык (en/ru/uk), опционально чистит эмодзи/экзотику.
- Склеивает подряд идущие предложения одного языка в блоки и озвучивает блоками (стабильнее).
- Пауза между предложениями — "запятыми" (~300 мс на запятую).
- Два режима:
    • single (multi_en_outputs=false): один MP3 (EN=voice_en с ретраями из alt_voices_en; RU/UK — свои)
    • multi (multi_en_outputs=true): отдельный MP3 на каждый EN-голос из alt_voices_en (RU/UK не меняются)
- Суффикс-фильтры:
    • Если для языка filter.enabled=true и имя файла оканчивается на filter.suffix (без расширения),
      то активным становится ТОЛЬКО этот язык.
    • Если ни один включённый суффикс не совпал — активные языки = enable_languages.
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


# -----------------------------------------------------------------------------
# 1) Конфиг и сбор входных файлов
# -----------------------------------------------------------------------------

def script_dir() -> Path:
    """Папка, где лежит этот скрипт."""
    return Path(__file__).resolve().parent


def load_or_create_config(cfg_path: Path) -> Dict:
    """
    Загружаем конфиг. Если его нет — создаём шаблон и выходим (чтобы пользователь заполнил пути).
    """
    if not cfg_path.exists():
        template = {
            "inputs": ["data/*.txt"],

            "recursive_inputs": True,
            "extensions": [".txt"],

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
    """Нормализуем список расширений: приводим к виду '.txt', '.md'."""
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
    """Рекурсивно собираем файлы из папки по списку расширений."""
    results: List[Path] = []
    for p in dir_path.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            results.append(p.resolve())
    return results


def expand_inputs(patterns: List[str], recursive_inputs: bool, exts: List[str]) -> List[Path]:
    """
    Превращаем "inputs" (маски/пути/папки) в список реальных файлов.
      - относительные пути считаем от папки скрипта
      - папка → рекурсивно файлы по extensions
      - маска с ** → используем как есть (glob recursive)
      - маска без ** и recursive_inputs=true → добавляем поиск по data/**/*.ext
    """
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
            name = pp.name  # например "*.txt"
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


# -----------------------------------------------------------------------------
# 2) Текст → предложения → язык → очистка
# -----------------------------------------------------------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def split_into_sentences(text: str) -> List[str]:
    """Простое разбиение на предложения."""
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
    """Возвращаем 'en', 'ru' или 'uk' (по умолчанию 'en')."""
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
    if not enabled:
        return s.strip()
    s = _EMOJI_RE.sub("", s)
    s = _ALLOWED_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[\.\,\!\?\:\;\-]+", "", s).strip()
    return s


# -----------------------------------------------------------------------------
# 3) Блоки по языку и паузы
# -----------------------------------------------------------------------------

def group_by_language(sentences: List[str], strip_emojis: bool) -> List[Tuple[str, List[str]]]:
    """Склеиваем подряд идущие предложения одного языка в блоки."""
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
    """Строка из запятых как «псевдопауза» (~300 мс на запятую)."""
    if ms <= 0:
        return ""
    n = max(1, round(ms / 300))
    return " " + ("," * n) + " "


def glue_block_text(sentences: List[str], pause_ms: int) -> str:
    """Склеиваем предложения блока, добавляя точку в конце при необходимости и запятые как паузы."""
    sep = make_pause_commas(pause_ms)
    fixed = [(s if re.search(r"[.!?]$", s) else s + ".") for s in sentences]
    return sep.join(fixed)


def rate_to_str(rate: int) -> str:
    if rate > 0:
        return f"+{rate}%"
    if rate < 0:
        return f"{rate}%"
    return "+0%"


# -----------------------------------------------------------------------------
# 4) Низкоуровневый синтез (edge-tts)
# -----------------------------------------------------------------------------

async def tts_append_block(text: str, voice: str, rate: int, out_path: Path) -> None:
    """Озвучиваем один текстовый блок, дозаписываем MP3 в конец файла."""
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
    """Пробуем несколько голосов по очереди. Возвращаем первый успешный."""
    last_err = None
    for v in voices:
        try:
            await tts_append_block(text, v, rate, out_path)
            return v
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("Unknown TTS error")


# -----------------------------------------------------------------------------
# 5) Суффикс-фильтры и выбор АКТИВНЫХ языков для файла (НОВАЯ ЛОГИКА)
# -----------------------------------------------------------------------------

def get_suffix_filters(cfg: Dict) -> Dict[str, Dict[str, object]]:
    """Возвращаем структуру с настройками суффиксов для en/ru/uk."""
    sf = cfg.get("suffix_filters", {})
    def one(lang, default_suffix):
        settings = sf.get(lang, {})
        return {
            "enabled": bool(settings.get("enabled", False)),
            "suffix":  str(settings.get("suffix", default_suffix))
        }
    return {
        "en": one("en", "_en"),
        "ru": one("ru", "_ru"),
        "uk": one("uk", "_uk"),
    }


def pick_active_languages_for_file(stem: str,
                                   enable_languages: List[str],
                                   suffix_filters: Dict[str, Dict[str, object]]) -> Set[str]:
    """
    Правило:
      1) Если ВКЛЮЧЁННЫЙ суффикс совпал с именем файла (stem.endswith(suffix)):
         активные языки = только этот язык.
         (Берём ПЕРВЫЙ совпавший по порядку ['en','ru','uk'], чтобы не плодить неоднозначности.)
      2) Иначе активные языки = enable_languages.
    """
    order = ["en", "ru", "uk"]
    for lang in order:
        rule = suffix_filters.get(lang, {"enabled": False, "suffix": ""})
        if rule.get("enabled") and stem.endswith(str(rule.get("suffix", ""))):
            return {lang}
    # ни один включённый суффикс не совпал — берём enable_languages
    return set(enable_languages)


# -----------------------------------------------------------------------------
# 6) Рендеринг (один файл / несколько EN-файлов)
# -----------------------------------------------------------------------------

async def render_single_output(in_path: Path,
                               blocks: List[Tuple[str, List[str]]],
                               cfg: Dict,
                               active_langs: Set[str]) -> None:
    """Один итоговый MP3. Озвучиваем только языки из active_langs."""
    voice_en = cfg.get("voice_en", "en-GB-RyanNeural")
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list):
        alt_en = []
    voices_en_try = [voice_en] + [v for v in alt_en if v != voice_en]

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")

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


async def render_multi_en_outputs(in_path: Path,
                                  blocks: List[Tuple[str, List[str]]],
                                  cfg: Dict,
                                  active_langs: Set[str]) -> None:
    """
    Несколько MP3: для каждого EN-голоса из alt_voices_en отдельный файл.
    Создаём ТОЛЬКО если 'en' среди active_langs и в тексте есть EN-блоки.
    Внутри каждого файла:
      - EN — текущим голосом (без ретраев),
      - RU — voice_ru (если 'ru' в active_langs),
      - UK — voice_uk (если 'uk' в active_langs).
    """
    alt_en = cfg.get("alt_voices_en", [])
    if not isinstance(alt_en, list) or not alt_en:
        print("  multi_en_outputs=true, но alt_voices_en пуст — нечего генерировать.")
        return

    if "en" not in active_langs:
        print("  Active языки не содержат EN — EN-варианты не создаются.")
        return

    # Проверим, что вообще есть английские блоки
    if "en" not in languages_present(blocks):
        print("  В файле нет английских блоков — EN-варианты не создаются.")
        return

    voice_ru = cfg.get("voice_ru", "ru-RU-DmitryNeural")
    voice_uk = cfg.get("voice_uk", "uk-UA-OstapNeural")
    rate = int(cfg.get("rate", -10))
    pause = int(cfg.get("pause", 500))

    # Оставим только блоки языков из active_langs
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
                    await tts_append_block(text_block, voice_ru, rate, out_path)
                    print(f"      ✓ RU: {voice_ru}")
                elif lang == "uk":
                    await tts_append_block(text_block, voice_uk, rate, out_path)
                    print(f"      ✓ UA: {voice_uk}")
                else:
                    await tts_append_block(text_block, en_voice, rate, out_path)
                    print(f"      ✓ EN: {en_voice}")
            except Exception as e:
                print(f"      ! Ошибка блока: {e} — пропуск этого блока.")

        print(f"  Готово: {out_path}")


# -----------------------------------------------------------------------------
# 7) Основной цикл по файлам
# -----------------------------------------------------------------------------

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

    # 1) Базовый список разрешённых языков (enable_languages)
    enable_languages = cfg.get("enable_languages", ["en", "ru"])
    if not isinstance(enable_languages, list) or not enable_languages:
        enable_languages = ["en", "ru"]

    # 2) Суффикс-фильтры и окончательный выбор АКТИВНЫХ языков для файла
    suffix_filters = get_suffix_filters(cfg)
    stem = path.stem
    active_langs = pick_active_languages_for_file(stem, enable_languages, suffix_filters)

    # 3) Если среди активных языков нет ни одного, который реально присутствует в тексте — завершаем
    present = languages_present(blocks)
    if not (active_langs & present):
        print(f"  В тексте нет блоков для активных языков {sorted(active_langs)} — пропуск.")
        return

    # 4) Выбор режима вывода
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
