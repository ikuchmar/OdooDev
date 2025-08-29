# video_editor/tools/ui_app_fragments.py
# -*- coding: utf-8 -*-
"""
Вкладка «Фрагмент»

Что здесь есть (и сильно прокомментировано по-русски):
1) Таблица интервалов (начало/конец/длительность) + базовые операции:
   - Добавить строку, Удалить выбранные, Очистить список,
   - Отсортировать и склеить пересекающиеся (нормализация списка).
2) Автозаполнение интервалов:
   - Поле «Разбивать на интервалы, сек» + кнопка «Разбить»;
   - Флажок «привязывать к паузам речи» (FFmpeg silencedetect) и настройки
     Порог дБ / Мин. пауза мс / Окно поиска ± мс.
3) Просмотр:
   - Кнопка «Посмотреть фрагмент» — быстро запустить ffplay на выбранном интервале;
   - «Открыть контролер предпросмотра» — отдельное окошко с Пуск/Стоп/Перейти и ползунком
     по текущему фрагменту (играем через ffplay, seek перезапуском процесса).
4) Экспорт:
   - «Сохранить все фрагменты в файлы» — каждый интервал в отдельный mp4;
   - «Сохранить только указанные фрагменты (склейка в один файл)» — конкатенация выбранных;
   - «Удалить фрагменты — оставить остальное (в один файл)» — берём дополнение к объединённым
     интервалам и склеиваем в один файл.
   Для сборок используется concat demuxer: порежем во временные файлы (-c copy) и склеим.

Зависимости: стандартная библиотека + внешние ffmpeg/ffprobe/ffplay (пути берём из главного окна).
"""

import os
import json
import math
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# Если в проекте уже есть utils с форматированием времени — используем его.
from . import utils

# ----------------------- УТИЛИТЫ ВРЕМЕНИ -----------------------

def _sec_to_hhmmss(sec: float) -> str:
    """Перевод секунд в строку чч:мм:сс (для отображения в таблице)."""
    try:
        return utils.sec_to_hhmmss(int(max(0, round(sec))))
    except Exception:
        s = max(0, int(round(sec)))
        h = s // 3600
        m = (s % 3600) // 60
        s2 = s % 60
        return f"{h:02d}:{m:02d}:{s2:02d}"

def _parse_time_to_sec(text: str) -> float:
    """Парсим либо число секунд, либо 'чч:мм:сс(.ms)' в float секунд."""
    t = (text or "").strip().replace(",", ".")
    if not t:
        return 0.0
    if ":" not in t:
        try:
            return float(t)
        except ValueError:
            return 0.0
    parts = t.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return 0.0
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts[-3], parts[-2], parts[-1]
    return max(0.0, h * 3600.0 + m * 60.0 + s)

# ----------------------- КЛАСС ВКЛАДКИ -----------------------

class UITabFragment:
    """
    Вкладка «Фрагмент». Здесь только UI и вызовы утилит ffmpeg/ffplay.
    """

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # Кэш длительности ролика, чтобы валидировать границы
        self._duration_cache = 0.0

        # Переменные авторазбиения
        self.var_chunk_sec   = tk.StringVar(value="10")   # разбивать на N сек
        self.var_snap        = tk.BooleanVar(value=True)  # привязывать к паузам
        self.var_silence_db  = tk.StringVar(value="-30")  # порог дБ
        self.var_silence_ms  = tk.StringVar(value="300")  # мин. пауза мс
        self.var_window_ms   = tk.StringVar(value="700")  # окно поиска ± мс

        # Прогресс и статус
        self.var_progress = tk.StringVar(value="Фрагменты: 0/0")
        self.pb = None

        # Дерево (таблица) интервалов
        self.tree = None

        # Контролер предпросмотра (дочернее окно)
        self._ctrl_win = None
        self._ctrl_pos_var = tk.DoubleVar(value=0.0)  # сек внутри фрагмента
        self._ctrl_proc = None  # процесс ffplay для предпросмотра

        self._build_ui()
        self._ensure_duration()

    # ---------------------- Внешние утилиты ----------------------

    def _ffmpeg_cmd(self) -> str:
        var = getattr(self.app, "var_ffmpeg", None)
        try:
            return (var.get() or "ffmpeg") if var is not None else "ffmpeg"
        except Exception:
            return "ffmpeg"

    def _ffprobe_cmd(self) -> str:
        var = getattr(self.app, "var_ffprobe", None)
        try:
            return (var.get() or "ffprobe") if var is not None else "ffprobe"
        except Exception:
            return "ffprobe"

    def _ffplay_cmd(self) -> str:
        var = getattr(self.app, "var_ffplay", None)
        try:
            return (var.get() or "ffplay") if var is not None else "ffplay"
        except Exception:
            return "ffplay"

    # -------------------------- UI --------------------------

    def _build_ui(self):
        root = ttk.Frame(self.parent, padding=10)
        root.pack(fill="both", expand=True)

        # Блок авторазбиения
        top = ttk.LabelFrame(root, text="Авторазбиение", padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Разбивать на интервалы, сек:").pack(side="left")
        ttk.Entry(top, textvariable=self.var_chunk_sec, width=6).pack(side="left", padx=(4, 10))

        ttk.Checkbutton(top, text="привязывать к паузам речи", variable=self.var_snap)\
            .pack(side="left", padx=(0, 10))
        ttk.Label(top, text="Порог, дБ:").pack(side="left")
        ttk.Entry(top, textvariable=self.var_silence_db, width=6).pack(side="left")
        ttk.Label(top, text="Мин. пауза, мс:").pack(side="left", padx=(8, 2))
        ttk.Entry(top, textvariable=self.var_silence_ms, width=6).pack(side="left")
        ttk.Label(top, text="Окно ±, мс:").pack(side="left", padx=(8, 2))
        ttk.Entry(top, textvariable=self.var_window_ms, width=6).pack(side="left")

        ttk.Button(top, text="Разбить", command=self._auto_split).pack(side="left", padx=(12, 4))

        # Таблица интервалов
        mid = ttk.LabelFrame(root, text="Интервалы (фрагменты)", padding=8)
        mid.pack(fill="both", expand=True, pady=(10, 8))

        cols = ("idx", "start", "end", "dur")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=12, selectmode="extended")
        self.tree.heading("idx",   text="#")
        self.tree.heading("start", text="Начало (сек или чч:мм:сс)")
        self.tree.heading("end",   text="Конец (сек или чч:мм:сс)")
        self.tree.heading("dur",   text="Длительность")

        self.tree.column("idx",   width=48,  anchor="e")
        self.tree.column("start", width=180, anchor="center")
        self.tree.column("end",   width=180, anchor="center")
        self.tree.column("dur",   width=120, anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview).pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=lambda a, b: None)

        # Панель действий
        bot = ttk.Frame(root)
        bot.pack(fill="x", pady=(4, 0))

        # слева — редактирование списка
        ttk.Button(bot, text="Добавить строку", command=self._add_empty_row).pack(side="left")
        ttk.Button(bot, text="Удалить выбранные", command=self._remove_selected).pack(side="left", padx=6)
        ttk.Button(bot, text="Очистить список", command=self._clear_all).pack(side="left", padx=6)
        ttk.Button(bot, text="Отсортировать и склеить пересекающиеся", command=self._sort_and_merge)\
            .pack(side="left", padx=6)

        # центр — прогресс
        ttk.Label(bot, textvariable=self.var_progress).pack(side="left", padx=(16, 6))
        self.pb = ttk.Progressbar(bot, orient="horizontal", mode="determinate", length=260, maximum=100, value=0)
        self.pb.pack(side="left")

        # справа — просмотр и экспорт
        ttk.Button(bot, text="Открыть контролер предпросмотра", command=self._open_preview_controller)\
            .pack(side="right")
        ttk.Button(bot, text="Посмотреть фрагмент", command=self._preview_selected)\
            .pack(side="right", padx=(6, 6))

        # след. строка — операции склейки
        bot2 = ttk.Frame(root); bot2.pack(fill="x", pady=(8, 0))
        ttk.Button(bot2, text="Удалить фрагменты — оставить остальное (в 1 файл)", command=self._save_complement_one)\
            .pack(side="left")
        ttk.Button(bot2, text="Сохранить только указанные фрагменты (склейка в 1 файл)", command=self._save_selected_one)\
            .pack(side="left", padx=6)
        ttk.Button(bot2, text="Сохранить все фрагменты в файлы", command=self._export_all)\
            .pack(side="right")

        root.columnconfigure(0, weight=1)

    # ------------------- Длительность текущего видео -------------------

    def _ensure_duration(self):
        """Узнаём длительность текущего видео (из app.state или через ffprobe)."""
        dur = float(self.app.state.get("duration") or 0.0)
        src = self.app.state.get("video_path") or ""
        if dur <= 0.0 and src and os.path.isfile(src):
            try:
                out = subprocess.check_output(
                    [self._ffprobe_cmd(), "-v", "error", "-show_format", "-of", "json", src],
                    stderr=subprocess.STDOUT
                )
                fmt = (json.loads(out.decode("utf-8", "ignore")).get("format") or {})
                dur = float(fmt.get("duration", 0.0) or 0.0)
            except Exception:
                dur = 0.0
        self._duration_cache = max(0.0, dur)

    # ----------------------- Работа с таблицей -----------------------

    def _add_row(self, a: float, b: float):
        """Добавить строку интервала (секунды -> строки + авторасчёт длительности)."""
        a = max(0.0, float(a)); b = max(a, float(b))
        dur = max(0.0, b - a)
        i = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", values=(i, _sec_to_hhmmss(a), _sec_to_hhmmss(b), _sec_to_hhmmss(dur)))

    def _add_empty_row(self):
        """Пустая строка под ручной ввод (по умолчанию 00:00:00)."""
        i = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", values=(i, "00:00:00", "00:00:00", "00:00:00"))

    def _remove_selected(self):
        """Удаляем выделенные строки и пере-нумеровываем индексы."""
        for iid in self.tree.selection():
            self.tree.delete(iid)
        self._reindex_and_fix_durations()

    def _clear_all(self):
        """Полностью очищаем таблицу."""
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.var_progress.set("Фрагменты: 0/0")
        self.pb["value"] = 0

    def _reindex_and_fix_durations(self):
        """Проходим по строкам сверху вниз: выставляем индексы и пересчитываем длительность."""
        for i, iid in enumerate(self.tree.get_children(), start=1):
            vals = list(self.tree.item(iid, "values"))
            vals[0] = i
            a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
            vals[3] = _sec_to_hhmmss(max(0.0, b - a))
            self.tree.item(iid, values=vals)

    def _get_intervals_from_table(self):
        """Собираем интервалы из таблицы в список [(a,b), ...] в секундах."""
        res = []
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
            if b > a + 0.01:
                res.append((a, b))
        return res

    def _set_intervals_to_table(self, intervals):
        """Заменяем содержимое таблицы заданным списком интервалов."""
        self._clear_all()
        for a, b in intervals:
            self._add_row(a, b)
        self._reindex_and_fix_durations()

    # ----------------------- Сортировка и склейка -----------------------

    @staticmethod
    def _merge_overlaps(intervals, eps=0.05):
        """
        Принимаем список [(a,b), ...], сортируем и склеиваем пересекающиеся/соприкасающиеся интервалы.
        eps — допуск в секундах (на всякий случай).
        """
        if not intervals:
            return []
        ints = sorted([(min(a, b), max(a, b)) for a, b in intervals], key=lambda x: x[0])
        merged = [ints[0]]
        for a, b in ints[1:]:
            la, lb = merged[-1]
            if a <= lb + eps:  # пересекаются или соприкасаются
                merged[-1] = (la, max(lb, b))
            else:
                merged.append((a, b))
        return merged

    def _sort_and_merge(self):
        """Кнопка «Отсортировать и склеить пересекающиеся»."""
        merged = self._merge_overlaps(self._get_intervals_from_table())
        self._set_intervals_to_table(merged)

    # ----------------------- Авторазбиение (silencedetect) -----------------------

    def _detect_silences(self, noise_db: float, min_sil_ms: int):
        """
        FFmpeg silencedetect: возвращаем список тишин [(start, end), ...] в секундах.
        """
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            return []
        cmd = [
            self._ffmpeg_cmd(), "-hide_banner", "-nostats",
            "-i", src,
            "-af", f"silencedetect=noise={noise_db}dB:d={max(0.05, min_sil_ms/1000.0)}",
            "-f", "null", "-"
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = proc.communicate()
            text = err.decode("utf-8", "ignore")
        except Exception:
            return []
        silences = []
        cur = None
        for line in text.splitlines():
            s = line.strip().lower()
            if "silence_start" in s:
                try:
                    cur = float(s.split("silence_start:")[1].strip())
                except Exception:
                    cur = None
            elif "silence_end" in s and cur is not None:
                try:
                    val = float(s.split("silence_end:")[1].split("|")[0].strip())
                    silences.append((cur, val)); cur = None
                except Exception:
                    cur = None
        return silences

    @staticmethod
    def _snap_to_nearest_silence(t: float, silences, window_ms: int) -> float:
        """Смещаем точку t к ближайшей середине паузы в окне ±window_ms; иначе оставляем как есть."""
        if not silences:
            return t
        win = max(0.05, window_ms / 1000.0)
        best = None; best_d = 10**9
        for s0, s1 in silences:
            mid = 0.5 * (s0 + s1)
            d = abs(mid - t)
            if d <= win and d < best_d:
                best_d = d; best = mid
        return best if best is not None else t

    def _auto_split(self):
        """Кнопка «Разбить»: заполняем таблицу равными кусками с необязательной привязкой к паузам."""
        self._ensure_duration()
        if self._duration_cache <= 0:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке «Файлы».")
            return

        try: chunk = max(1, int(float(self.var_chunk_sec.get())))
        except Exception: chunk = 10
        use_snap = bool(self.var_snap.get())
        try: noise_db = float(self.var_silence_db.get())
        except Exception: noise_db = -30.0
        try: min_sil_ms = int(self.var_silence_ms.get())
        except Exception: min_sil_ms = 300
        try: window_ms = int(self.var_window_ms.get())
        except Exception: window_ms = 700

        # Равномерные границы
        bounds = [0.0]; t = float(chunk)
        while t < self._duration_cache - 0.001:
            bounds.append(t); t += chunk
        bounds.append(self._duration_cache)

        # Привязка к паузам — двигаем внутренние границы
        if use_snap:
            sil = self._detect_silences(noise_db, min_sil_ms)
            for i in range(1, len(bounds)-1):
                bounds[i] = self._snap_to_nearest_silence(bounds[i], sil, window_ms)

        # В таблицу
        self._clear_all()
        for i in range(len(bounds)-1):
            a, b = bounds[i], bounds[i+1]
            if b - a >= 0.2:
                self._add_row(a, b)
        self._reindex_and_fix_durations()
        total = len(self.tree.get_children())
        self.var_progress.set(f"Фрагменты: {total}/{total}")
        self.pb["value"] = 100 if total else 0

    # ----------------------- Просмотр (ffplay) -----------------------

    def _preview_selected(self):
        """Быстрый просмотр выделенного фрагмента (через ffplay)."""
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла", "Сначала выберите видео."); return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Не выбрано", "Выберите строку в таблице."); return
        vals = self.tree.item(sel[0], "values")
        a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
        d = max(0.0, b - a)
        if d <= 0.05:
            messagebox.showinfo("Мелкий фрагмент", "Длительность слишком мала."); return
        cmd = [self._ffplay_cmd(), "-hide_banner", "-loglevel", "error", "-i", src, "-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-autoexit"]
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")

    # ---- контролер предпросмотра (отдельное окно)

    def _open_preview_controller(self):
        """Окно с кнопками Пуск/Стоп/Перейти и ползунком по текущему выделенному интервалу."""
        if self._ctrl_win and tk.Toplevel.winfo_exists(self._ctrl_win):
            try:
                self._ctrl_win.lift()
                self._sync_ctrl_from_selection()
                return
            except Exception:
                pass

        win = tk.Toplevel(self.parent)
        win.title("Контролер предпросмотра (ffplay)")
        win.geometry("520x140")
        self._ctrl_win = win

        # Верхняя строка — выбор фрагмента
        top = ttk.Frame(win, padding=8); top.pack(fill="x")
        ttk.Button(top, text="Синхронизировать с выделенной строкой", command=self._sync_ctrl_from_selection)\
            .pack(side="left")
        self._ctrl_info = ttk.Label(top, text="— нет фрагмента —"); self._ctrl_info.pack(side="left", padx=8)

        # Ползунок позиции
        mid = ttk.Frame(win, padding=(8, 0)); mid.pack(fill="x")
        ttk.Label(mid, text="Позиция в фрагменте (сек):").pack(side="left")
        self._ctrl_scale = ttk.Scale(mid, from_=0.0, to=1.0, orient="horizontal",
                                     variable=self._ctrl_pos_var, command=lambda _v: None)
        self._ctrl_scale.pack(side="left", fill="x", expand=True, padx=8)

        # Кнопки управления
        bot = ttk.Frame(win, padding=8); bot.pack(fill="x")
        ttk.Button(bot, text="▶ Пуск",  command=self._ctrl_play).pack(side="left")
        ttk.Button(bot, text="⏩ Перейти", command=self._ctrl_seek).pack(side="left", padx=6)
        ttk.Button(bot, text="⏹ Стоп",  command=self._ctrl_stop).pack(side="left")

        # Изначально — подтягиваем выделение
        self._sync_ctrl_from_selection()

        # Закрытие окна — убьём ffplay
        def _on_close():
            self._ctrl_stop()
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

    def _current_selected_interval(self):
        """Возвращает (a,b) по текущей выделенной строке таблицы или None."""
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
        if b <= a + 0.05:
            return None
        return (a, b)

    def _sync_ctrl_from_selection(self):
        """Читает выделенную строку и подготавливает контролер."""
        ab = self._current_selected_interval()
        if not ab:
            self._ctrl_info.config(text="— нет корректного фрагмента —")
            self._ctrl_scale.configure(from_=0.0, to=1.0)
            self._ctrl_pos_var.set(0.0)
            return
        a, b = ab
        dur = b - a
        self._ctrl_info.config(text=f"{_sec_to_hhmmss(a)} — {_sec_to_hhmmss(b)}  (длительность: {dur:.2f}с)")
        self._ctrl_scale.configure(from_=0.0, to=dur)
        self._ctrl_pos_var.set(0.0)

    def _ctrl_play(self):
        """Пуск с начала выделенного фрагмента."""
        ab = self._current_selected_interval()
        if not ab: return
        self._ctrl_seek(start_from_slider=False)

    def _ctrl_seek(self):
        """Перейти к позиции ползунка внутри выбранного фрагмента (запуск ffplay)."""
        ab = self._current_selected_interval()
        if not ab: return
        a, b = ab
        pos = float(self._ctrl_pos_var.get() or 0.0)
        start = a + max(0.0, min(pos, b - a))
        self._ctrl_stop(kill_only=True)
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src): return
        left = max(0.0, b - start)
        cmd = [self._ffplay_cmd(), "-hide_banner", "-loglevel", "error", "-i", src, "-ss", f"{start:.3f}", "-t", f"{left:.3f}", "-autoexit"]
        try:
            self._ctrl_proc = subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")
            self._ctrl_proc = None

    def _ctrl_stop(self, kill_only: bool = False):
        """Останавливаем текущий процесс ffplay контролера."""
        if self._ctrl_proc and self._ctrl_proc.poll() is None:
            try: self._ctrl_proc.terminate()
            except Exception: pass
            try: self._ctrl_proc.wait(timeout=0.5)
            except Exception:
                try: self._ctrl_proc.kill()
                except Exception: pass
        self._ctrl_proc = None

    # ----------------------- Экспорт / склейка -----------------------

    def _default_output_dir(self):
        """Папка вывода по умолчанию = каталог текущего видео."""
        src = self.app.state.get("video_path") or ""
        return os.path.dirname(os.path.abspath(src)) if src else os.getcwd()

    def _ffmpeg_cut(self, src: str, start: float, duration: float, out_path: str) -> bool:
        """
        Быстрый рез: -i src, затем -ss/-t и -c copy.
        Возвращает True/False по результату. В случае ошибки вернём False (вызов выше решит, что делать).
        """
        cmd = [self._ffmpeg_cmd(), "-hide_banner", "-loglevel", "error", "-y",
               "-i", src, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-c", "copy", out_path]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            return True
        except Exception:
            # запасной вариант — -ss до -i (ещё быстрее, но менее точен), всё равно -c copy
            cmd2 = [self._ffmpeg_cmd(), "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{start:.3f}", "-i", src, "-t", f"{duration:.3f}", "-c", "copy", out_path]
            try:
                subprocess.check_call(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                return True
            except Exception:
                return False

    def _concat_files(self, parts_paths, out_path) -> bool:
        """
        Склейка через concat demuxer:
        - на каждый файл пишем строку вида: file '/abs/posix/path.mp4'
        - пути нормализуем в POSIX (слэши /), экранируем одинарные кавычки.
        """
        if not parts_paths:
            return False

        list_txt = os.path.join(tempfile.gettempdir(), f"concat_{os.getpid()}.txt")
        try:
            # важно: newline="\n", чтобы ffmpeg не спотыкался на \r\n
            with open(list_txt, "w", encoding="utf-8", newline="\n") as f:
                for p in parts_paths:
                    # абсолютный путь и POSIX-слэши (ffmpeg на Windows это понимает)
                    path = os.path.abspath(p).replace("\\", "/")
                    # экранируем одинарные кавычки по правилу demuxer'а: ' -> '\''
                    path = path.replace("'", "'\\''")
                    # без f-строк — чтобы не ловить проблемы с экранированием в Python-литералах
                    f.write("file '" + path + "'\n")

            cmd = [
                self._ffmpeg_cmd(), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", out_path
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            return True
        except Exception:
            return False
        finally:
            try:
                os.remove(list_txt)
            except Exception:
                pass

    # -- Экспорт: каждый фрагмент в отдельный файл
    def _export_all(self):
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла", "Сначала выберите видео."); return
        rows = self.tree.get_children()
        if not rows:
            messagebox.showinfo("Пусто", "Список интервалов пуст."); return

        out_dir = self._default_output_dir()
        base = os.path.splitext(os.path.basename(src))[0]

        total = len(rows); done = 0
        self.pb["value"] = 0; self.var_progress.set(f"Фрагменты: 0/{total}")

        for idx, iid in enumerate(rows, start=1):
            vals = self.tree.item(iid, "values")
            a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
            d = max(0.0, b - a)
            if d <= 0.05:
                continue
            out_name = f"{base}_part{idx:03d}_{_sec_to_hhmmss(a).replace(':','-')}-{_sec_to_hhmmss(b).replace(':','-')}.mp4"
            out_path = os.path.join(out_dir, out_name)
            ok = self._ffmpeg_cut(src, a, d, out_path)
            if not ok:
                messagebox.showwarning("FFmpeg", f"Не удалось сохранить фрагмент #{idx}. Пропущен.")
            done += 1
            self.pb["value"] = int(round(done * 100.0 / total))
            self.var_progress.set(f"Фрагменты: {done}/{total}")
            self.pb.update_idletasks()

        messagebox.showinfo("Готово", f"Сохранено: {done} из {total}\nПапка: {out_dir}")

    # -- Сохранить только указанные (склейка в один файл)
    def _save_selected_one(self):
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла", "Сначала выберите видео."); return

        # Берём ВЫДЕЛЕННЫЕ строки; если ничего не выделено — берём все
        sel = self.tree.selection()
        rows = sel if sel else self.tree.get_children()
        if not rows:
            messagebox.showinfo("Пусто", "Нет интервалов для склейки."); return

        intervals = []
        for iid in rows:
            vals = self.tree.item(iid, "values")
            a = _parse_time_to_sec(vals[1]); b = _parse_time_to_sec(vals[2])
            if b > a + 0.05:
                intervals.append((a, b))
        if not intervals:
            messagebox.showinfo("Пусто", "Нет валидных интервалов."); return

        # Склеим пересечения
        merged = self._merge_overlaps(intervals)

        # Режем во временные файлы
        tmp_dir = tempfile.mkdtemp(prefix="video_editor_parts_")
        parts = []
        for i, (a, b) in enumerate(merged, start=1):
            d = b - a
            part = os.path.join(tmp_dir, f"part_{i:03d}.mp4")
            if self._ffmpeg_cut(src, a, d, part):
                parts.append(part)

        if not parts:
            messagebox.showwarning("FFmpeg", "Не удалось подготовить части для склейки."); return

        out_dir = self._default_output_dir()
        base = os.path.splitext(os.path.basename(src))[0]
        out_path = os.path.join(out_dir, f"{base}__selected_concat.mp4")

        ok = self._concat_files(parts, out_path)
        # Чистим временные
        for p in parts:
            try: os.remove(p)
            except Exception: pass
        try: os.rmdir(tmp_dir)
        except Exception: pass

        if ok:
            messagebox.showinfo("Готово", f"Сохранён файл:\n{out_path}")
        else:
            messagebox.showwarning("FFmpeg", "Склейка не удалась.")

    # -- Удалить фрагменты — оставить остальное (в 1 файл)
    def _save_complement_one(self):
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла", "Сначала выберите видео."); return

        intervals = self._merge_overlaps(self._get_intervals_from_table())
        if not intervals:
            messagebox.showinfo("Пусто", "Список интервалов пуст."); return

        self._ensure_duration()
        T = self._duration_cache
        if T <= 0:
            messagebox.showwarning("Нет длительности", "Не удалось узнать длительность файла."); return

        # Дополнение: сегменты «вне» объединённых интервалов
        complement = []
        cur = 0.0
        for a, b in intervals:
            if a > cur + 0.05:
                complement.append((cur, a))
            cur = max(cur, b)
        if cur < T - 0.05:
            complement.append((cur, T))

        if not complement:
            messagebox.showinfo("Пусто", "После вычитания ничего не осталось."); return

        # Режем и склеиваем
        tmp_dir = tempfile.mkdtemp(prefix="video_editor_keep_")
        parts = []
        for i, (a, b) in enumerate(complement, start=1):
            d = b - a
            part = os.path.join(tmp_dir, f"keep_{i:03d}.mp4")
            if self._ffmpeg_cut(src, a, d, part):
                parts.append(part)

        if not parts:
            messagebox.showwarning("FFmpeg", "Не удалось подготовить части для склейки."); return

        out_dir = self._default_output_dir()
        base = os.path.splitext(os.path.basename(src))[0]
        out_path = os.path.join(out_dir, f"{base}__removed_fragments.mp4")

        ok = self._concat_files(parts, out_path)

        for p in parts:
            try: os.remove(p)
            except Exception: pass
        try: os.rmdir(tmp_dir)
        except Exception: pass

        if ok:
            messagebox.showinfo("Готово", f"Сохранён файл:\n{out_path}")
        else:
            messagebox.showwarning("FFmpeg", "Склейка не удалась.")
