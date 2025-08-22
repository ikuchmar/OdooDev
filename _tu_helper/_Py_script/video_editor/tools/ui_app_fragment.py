# video_editor/tools/ui_app_fragment.py
# -*- coding: utf-8 -*-
"""
ui_app_fragment.py — вкладка "Фрагмент" (таблица интервалов + предпросмотр строки + контроллер).

Что есть:
- Таблица интервалов (Treeview) с колонками "Начало" и "Конец" (HH:MM:SS).
- Управление списком: добавить, обновить, удалить, очистить, нормализовать (сортировка+склейка).
- Операции:
    * "Удалить фрагменты — оставить остальное (в один файл)"
    * "Сохранить только указанные фрагменты (склейка в один файл)"
- Быстрый предпросмотр выделенной строки:
    * "▶ Просмотреть (с начала фрагмента)" — старт с начала интервала, дальше без ограничений.
    * "▶ Просмотреть только фрагмент" — проигрывает ровно интервал (-ss + -t), затем закрывается.
- Контроллер предпросмотра (Toplevel):
    * Кнопки ▶ Пуск, ⏹ Стоп, ⏩ Перейти
    * Слайдер-позиция (линейка времени) для всего видео или только выделенного фрагмента.
    * Перемотка реализована перезапуском ffplay с нужной позицией (без внешних зависимостей).

Ограничения:
- Мы не можем "встроить" кнопки прямо в окно ffplay, поэтому делаем отдельное контролирующее окно на Tk.
- Пауза/резюмирование эмулируются как Стоп+Пуск на нужной позиции (индикатор позиции ведётся по таймеру).
"""

import os
import time
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

from . import utils, fragment_ops


class UITabFragment:
    def __init__(self, app, parent):
        """
        app    — экземпляр App_UI (главное окно)
        parent — фрейм вкладки
        """
        self.app = app
        self.parent = parent

        # Переменные для окна-контроллера предпросмотра
        self._pv_win = None            # Toplevel окна контроллера (если открыто)
        self._pv_proc = None           # subprocess.Popen(ffplay) текущего предпросмотра
        self._pv_timer = None          # поток-таймер, обновляющий позицию
        self._pv_stop_evt = None       # Event для остановки таймера
        self._pv_scope = "video"       # "video" (всё видео) или "frag" (текущий интервал)
        self._pv_start = 0.0           # стартовая позиция текущего запуска, сек
        self._pv_length = 0.0          # длина "диапазона" для проигрывания (видео или фрагмент), сек
        self._pv_started_at = 0.0      # time.monotonic() момента старта (для расчёта текущей позиции)

        self._build()

    # ----------------------------------------------------------------------
    # Построение интерфейса вкладки
    # ----------------------------------------------------------------------
    def _build(self):
        root = ttk.Frame(self.parent, padding=10)
        root.pack(fill="both", expand=True)

        # --- Панель ввода одного интервала (для добавления/редактирования) ---
        frm_in = ttk.LabelFrame(root, text="Интервал", padding=8)
        frm_in.pack(fill="x")

        ttk.Label(frm_in, text="Начало (чч:мм:сс):").grid(row=0, column=0, sticky="w")
        ttk.Label(frm_in, text="Конец (чч:мм:сс):").grid(row=0, column=2, sticky="w")

        self.var_start = tk.StringVar(value="00:00:05")
        self.var_end   = tk.StringVar(value="00:00:10")

        ttk.Entry(frm_in, textvariable=self.var_start, width=12).grid(row=0, column=1, padx=(4, 16), sticky="w")
        ttk.Entry(frm_in, textvariable=self.var_end,   width=12).grid(row=0, column=3, padx=(4, 16), sticky="w")

        ttk.Button(frm_in, text="Добавить", command=self._add_interval).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(frm_in, text="Обновить выделенный", command=self._update_selected).grid(row=0, column=5, padx=(0, 6))

        # --- Таблица интервалов ---
        frm_tbl = ttk.LabelFrame(root, text="Список интервалов (вырезать или сохранить)", padding=8)
        frm_tbl.pack(fill="both", expand=True, pady=(10, 8))

        self.tree = ttk.Treeview(frm_tbl, columns=("start", "end"), show="headings", height=10)
        self.tree.heading("start", text="Начало")
        self.tree.heading("end",   text="Конец")
        self.tree.column("start", width=120, anchor="center")
        self.tree.column("end",   width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm_tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_tree_dblclick)

        # --- Кнопки управления таблицей и предпросмотром ---
        frm_tbl_btns = ttk.Frame(root)
        frm_tbl_btns.pack(fill="x", pady=(0, 10))
        ttk.Button(frm_tbl_btns, text="Удалить выделенные строки", command=self._remove_selected).pack(side="left")
        ttk.Button(frm_tbl_btns, text="Очистить список", command=self._clear_all).pack(side="left", padx=6)
        ttk.Button(frm_tbl_btns, text="Отсортировать и склеить пересекающиеся", command=self._normalize_rows).pack(side="left", padx=6)

        # Быстрые действия предпросмотра по выделенной строке
        ttk.Button(frm_tbl_btns, text="▶ Просмотреть (с начала фрагмента)", command=self._preview_from_start).pack(side="right")
        ttk.Button(frm_tbl_btns, text="▶ Просмотреть только фрагмент", command=self._preview_fragment_only).pack(side="right", padx=(0, 8))

        # --- Контроллер предпросмотра (отдельное окно) ---
        frm_ctrl = ttk.Frame(root)
        frm_ctrl.pack(fill="x", pady=(0, 10))
        ttk.Button(frm_ctrl, text="Открыть контроллер предпросмотра", command=self._open_preview_controller).pack(side="left")

        # --- Операции с интервалами ---
        frm_ops = ttk.LabelFrame(root, text="Операции с интервалами", padding=8)
        frm_ops.pack(fill="x")

        ttk.Button(frm_ops,
                   text="Удалить фрагменты — оставить остальное (в один файл)",
                   command=self._apply_delete_list).pack(side="left", padx=(0, 8))

        ttk.Button(frm_ops,
                   text="Сохранить только указанные фрагменты (склейка в один файл)",
                   command=self._apply_keep_list).pack(side="left", padx=(0, 8))

        root.columnconfigure(0, weight=1)

    # ----------------------------------------------------------------------
    # Табличные операции
    # ----------------------------------------------------------------------
    def _add_interval(self):
        """Добавляет интервал из полей ввода в таблицу (с валидацией)."""
        try:
            s = utils.hhmmss_to_sec(self.var_start.get())
            e = utils.hhmmss_to_sec(self.var_end.get())
        except Exception:
            messagebox.showwarning("Ошибка", "Неверный формат времени. Пример: 00:01:23")
            return
        if e <= s:
            messagebox.showwarning("Ошибка", "Конец должен быть больше начала")
            return
        self.tree.insert("", "end", values=(utils.sec_to_hhmmss(int(s)), utils.sec_to_hhmmss(int(e))))

    def _on_tree_dblclick(self, event):
        """Подставляет выбранную строку в поля 'Начало'/'Конец' для правки."""
        item = self.tree.focus()
        if not item:
            return
        start_str, end_str = self.tree.item(item, "values")
        self.var_start.set(start_str)
        self.var_end.set(end_str)

    def _update_selected(self):
        """Обновляет выделенную строку значениями из полей."""
        item = self.tree.focus()
        if not item:
            messagebox.showinfo("Правка", "Сначала выделите строку двойным кликом в таблице")
            return
        try:
            s = utils.hhmmss_to_sec(self.var_start.get())
            e = utils.hhmmss_to_sec(self.var_end.get())
        except Exception:
            messagebox.showwarning("Ошибка", "Неверный формат времени. Пример: 00:01:23")
            return
        if e <= s:
            messagebox.showwarning("Ошибка", "Конец должен быть больше начала")
            return
        self.tree.item(item, values=(utils.sec_to_hhmmss(int(s)), utils.sec_to_hhmmss(int(e))))

    def _remove_selected(self):
        """Удаляет выделенные строки из таблицы."""
        for iid in self.tree.selection():
            self.tree.delete(iid)

    def _clear_all(self):
        """Полностью очищает таблицу."""
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def _normalize_rows(self):
        """Сортирует интервалы, склеивает пересечения/соприкосновения и перерисовывает таблицу."""
        segs = self._collect_segments()
        if not segs:
            return
        segs_norm = fragment_ops.normalize_intervals(segs, duration=self.app.state.get("duration", 0.0) or 0.0)
        self._fill_table_from_segments(segs_norm)
        messagebox.showinfo("Нормализация", f"Интервалы отсортированы и объединены.\nИтого: {len(segs_norm)}")

    def _collect_segments(self):
        """Собирает интервалы из таблицы в список [(start_sec, end_sec), ...] с сортировкой по началу."""
        rows = []
        for iid in self.tree.get_children():
            start_str, end_str = self.tree.item(iid, "values")
            try:
                s = utils.hhmmss_to_sec(start_str)
                e = utils.hhmmss_to_sec(end_str)
            except Exception:
                continue
            if e > s:
                rows.append((s, e))
        rows.sort(key=lambda x: x[0])
        return rows

    def _fill_table_from_segments(self, segs):
        """Перерисовывает таблицу списком интервалов segs (секунды -> HH:MM:SS)."""
        self._clear_all()
        for s, e in segs:
            self.tree.insert("", "end", values=(utils.sec_to_hhmmss(int(s)), utils.sec_to_hhmmss(int(e))))

    # ----------------------------------------------------------------------
    # Быстрый предпросмотр выделенного интервала (отдельные кнопки)
    # ----------------------------------------------------------------------
    def _get_current_interval(self):
        """Возвращает (start_sec, end_sec) текущей выделенной строки таблицы или None."""
        item = self.tree.focus()
        if not item:
            return None
        vals = self.tree.item(item, "values")
        if not vals or len(vals) < 2:
            return None
        try:
            s = utils.hhmmss_to_sec(vals[0])
            e = utils.hhmmss_to_sec(vals[1])
        except Exception:
            return None
        if e <= s:
            return None
        return (s, e)

    def _preview_from_start(self):
        """Открыть ffplay, перемотав на начало выбранного интервала (играет дальше)."""
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return
        cur = self._get_current_interval()
        if not cur:
            messagebox.showinfo("Просмотр", "Выделите строку с интервалом в таблице.")
            return
        start, _end = cur
        self._spawn_ffplay(start_sec=start, duration_sec=None)

    def _preview_fragment_only(self):
        """Открыть ffplay и проиграть ровно выбранный фрагмент (-ss + -t)."""
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return
        cur = self._get_current_interval()
        if not cur:
            messagebox.showinfo("Просмотр", "Выделите строку с интервалом в таблице.")
            return
        start, end = cur
        dur = max(0.1, float(end - start))
        self._spawn_ffplay(start_sec=start, duration_sec=dur)

    # Неблокирующий запуск ffplay
    def _spawn_ffplay(self, start_sec=0.0, duration_sec=None, window_title=None):
        ffplay = self.app.var_ffplay.get() or "ffplay"
        src = self.app.state["video_path"]

        def worker():
            cmd = [ffplay, "-hide_banner", "-loglevel", "error"]
            # без -autoexit в "открытом" просмотре, но с -autoexit для точного фрагмента
            if duration_sec and duration_sec > 0:
                cmd += ["-autoexit", "-t", str(float(duration_sec))]
            if start_sec and start_sec > 0:
                cmd += ["-ss", str(float(start_sec))]
            if window_title:
                cmd += ["-window_title", window_title]
            cmd += [src]
            try:
                subprocess.Popen(cmd)  # не ждём
            except Exception as e:
                messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    # ----------------------------------------------------------------------
    # Контроллер предпросмотра (отдельное Toplevel окно)
    # ----------------------------------------------------------------------
    def _open_preview_controller(self):
        """Создаёт окно-контроллер предпросмотра (если уже есть — выводит его на передний план)."""
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return

        # Если окно уже открыто — просто фокусируем
        if self._pv_win and tk.Toplevel.winfo_exists(self._pv_win):
            try:
                self._pv_win.lift()
                self._pv_win.focus_force()
            except Exception:
                pass
            return

        # Создаём новое окно
        self._pv_win = tk.Toplevel(self.parent)
        self._pv_win.title("Предпросмотр — контроллер")
        self._pv_win.geometry("640x160")
        self._pv_win.protocol("WM_DELETE_WINDOW", self._pv_on_close)

        # Верхняя панель: область/режим
        frm_top = ttk.Frame(self._pv_win, padding=8)
        frm_top.pack(fill="x")

        ttk.Label(frm_top, text="Режим:").pack(side="left")
        self._pv_mode = tk.StringVar(value="video")
        ttk.Radiobutton(frm_top, text="Всё видео", variable=self._pv_mode, value="video",
                        command=self._pv_on_mode_change).pack(side="left", padx=6)
        ttk.Radiobutton(frm_top, text="Текущий фрагмент", variable=self._pv_mode, value="frag",
                        command=self._pv_on_mode_change).pack(side="left")

        # Средняя панель: линейка времени
        frm_mid = ttk.Frame(self._pv_win, padding=8)
        frm_mid.pack(fill="x")

        self._pv_pos = tk.DoubleVar(value=0.0)    # текущая позиция в "диапазоне"
        self._pv_max = tk.DoubleVar(value=max(1.0, float(self.app.state.get("duration") or 1.0)))
        self._pv_lbl = ttk.Label(frm_mid, text="00:00 / 00:00")
        self._pv_lbl.pack(side="right")

        self._pv_scale = ttk.Scale(frm_mid, from_=0.0, to=self._pv_max.get(),
                                   orient="horizontal", variable=self._pv_pos,
                                   command=self._pv_on_slider_drag)
        self._pv_scale.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Нижняя панель: кнопки управления
        frm_bot = ttk.Frame(self._pv_win, padding=8)
        frm_bot.pack(fill="x")

        ttk.Button(frm_bot, text="▶ Пуск", command=self._pv_play).pack(side="left")
        ttk.Button(frm_bot, text="⏹ Стоп", command=self._pv_stop).pack(side="left", padx=6)
        ttk.Button(frm_bot, text="⏩ Перейти", command=self._pv_seek).pack(side="left")

        # Инициализация параметров диапазона (по умолчанию: всё видео)
        self._pv_apply_scope(init=True)
        self._pv_update_label()

    # --- обработчики окна контроллера ---
    def _pv_on_close(self):
        """Закрытие окна-контроллера: останавливаем таймер и ffplay."""
        self._pv_stop()
        try:
            self._pv_win.destroy()
        except Exception:
            pass
        self._pv_win = None

    def _pv_on_mode_change(self):
        """Переключение 'всё видео' / 'текущий фрагмент'."""
        self._pv_apply_scope()
        self._pv_update_label()

    def _pv_on_slider_drag(self, _val):
        """Обновление подписи позиции при перемещении ползунка."""
        self._pv_update_label()

    # --- логика контроллера ---
    def _pv_apply_scope(self, init=False):
        """
        Настраивает диапазон воспроизведения в зависимости от режима:
        - video: [0 .. duration]
        - frag:  [start .. end] из выделенной строки таблицы
        """
        mode = self._pv_mode.get()
        self._pv_scope = mode

        if mode == "frag":
            cur = self._get_current_interval()
            if not cur:
                if not init:
                    messagebox.showinfo("Фрагмент", "Выделите строку в таблице интервалов.")
                # откатываемся в режим видео
                self._pv_mode.set("video")
                self._pv_apply_scope(init=True)
                return
            s, e = cur
            self._pv_start = float(s)
            self._pv_length = max(0.1, float(e - s))
        else:
            # Весь ролик
            self._pv_start = 0.0
            self._pv_length = float(self.app.state.get("duration") or 0.0)

        # Обновляем слайдер: 0.._pv_length
        maxv = max(1.0, self._pv_length)
        self._pv_max.set(maxv)
        try:
            self._pv_scale.configure(to=maxv)
        except Exception:
            pass

        # Сбрасываем позицию в 0 в текущем диапазоне
        self._pv_pos.set(0.0)
        self._pv_update_label()

    def _pv_play(self):
        """
        Пуск: стартуем ffplay с начала диапазона + позиция ползунка.
        Если уже играет — перезапускаем с новой позиции.
        """
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return

        # Позиция в пределах текущего диапазона
        rel = float(self._pv_pos.get() or 0.0)
        abs_pos = self._pv_start + rel
        dur_left = max(0.0, self._pv_length - rel)

        # Перезапускаем ffplay
        self._pv_stop(kill_only=True)
        self._pv_proc = self._spawn_ffplay_managed(start_sec=abs_pos, duration_sec=dur_left)

        # Запускаем таймер обновления индикатора позиции
        self._pv_started_at = time.monotonic()
        self._pv_start_rel = rel
        self._start_timer()

    def _pv_seek(self):
        """
        Перейти: как Play, но без автозапуска? В нашей реализации — просто как Play (запускаем).
        """
        self._pv_play()

    def _pv_stop(self, kill_only=False):
        """
        Стоп: останавливаем таймер и процесс ffplay.
        kill_only=True — не трогать слайдер/позицию, просто убить процесс.
        """
        # Остановка таймера
        if self._pv_stop_evt is not None:
            self._pv_stop_evt.set()
        self._pv_stop_evt = None

        # Завершаем ffplay (если есть)
        if self._pv_proc and self._pv_proc.poll() is None:
            try:
                self._pv_proc.terminate()
            except Exception:
                pass
            # чуть подождём и добьём при необходимости
            try:
                self._pv_proc.wait(timeout=0.5)
            except Exception:
                try:
                    self._pv_proc.kill()
                except Exception:
                    pass
        self._pv_proc = None

        if not kill_only:
            # Сбрасывать позицию не будем: пусть остаётся на текущем значении слайдера
            self._pv_update_label()

    # --- внутренние помощники контроллера ---
    def _spawn_ffplay_managed(self, start_sec=0.0, duration_sec=None):
        """
        Запускает ffplay и возвращает Popen. Без блокировки.
        - Если duration_sec задана — ставим -autoexit, чтобы окно закрылось по окончанию кусочка.
        """
        ffplay = self.app.var_ffplay.get() or "ffplay"
        src = self.app.state["video_path"]

        cmd = [ffplay, "-hide_banner", "-loglevel", "error"]
        if duration_sec and duration_sec > 0:
            cmd += ["-autoexit", "-t", str(float(duration_sec))]
        if start_sec and start_sec > 0:
            cmd += ["-ss", str(float(start_sec))]

        title = f"Preview: {os.path.basename(src)} @ {utils.sec_to_hhmmss(int(start_sec))}"
        try:
            cmd += ["-window_title", title]
        except Exception:
            pass
        cmd += [src]

        try:
            return subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")
            return None

    def _start_timer(self):
        """Запускает фоновый поток, который раз в 0.1с обновляет позицию слайдера во время воспроизведения."""
        self._pv_stop_evt = threading.Event()

        def run():
            # Пока процесс жив и не попросили остановиться — считаем прошедшее время и обновляем слайдер
            while not self._pv_stop_evt.is_set():
                if self._pv_proc is None or self._pv_proc.poll() is not None:
                    break
                elapsed = time.monotonic() - self._pv_started_at
                rel = self._pv_start_rel + elapsed
                # если дошли до конца диапазона — выходим
                if rel >= self._pv_length:
                    break
                # обновляем позицию в UI из главного потока
                try:
                    self._pv_win.after(0, lambda v=rel: self._pv_pos.set(v))
                    self._pv_win.after(0, self._pv_update_label)
                except Exception:
                    pass
                time.sleep(0.1)

            # Доигралось / остановлено — корректный финиш
            try:
                self._pv_win.after(0, self._pv_update_label)
            except Exception:
                pass

        self._pv_timer = threading.Thread(target=run, daemon=True)
        self._pv_timer.start()

    def _pv_update_label(self):
        """Обновляет текст под линейкой: ТекущееВремя / КонецДиапазона."""
        rel = float(self._pv_pos.get() or 0.0)
        cur_abs = self._pv_start + rel
        total_abs = self._pv_start + self._pv_length
        self._pv_lbl.config(text=f"{utils.sec_to_hhmmss(int(cur_abs))} / {utils.sec_to_hhmmss(int(total_abs))}")

    # ----------------------------------------------------------------------
    # Операции вырезать/оставить
    # ----------------------------------------------------------------------
    def _apply_delete_list(self):
        """Удалить все указанные интервалы, остальное склеить в один файл (1 прогон через filter_complex)."""
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return

        segs = self._collect_segments()
        if not segs:
            messagebox.showinfo("Интервалы", "Список пуст — удалять нечего.")
            return

        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        ffprobe = self.app.var_ffprobe.get() or "ffprobe"
        src = self.app.state["video_path"]
        outdir = self.app.state["output_dir"]
        duration = float(self.app.state.get("duration") or 0.0)

        def worker():
            try:
                out = fragment_ops.cut_out_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=duration)
                self.app.msg_queue.put(("info", f"Готово: {out}"))
            except Exception as e:
                self.app.msg_queue.put(("info", f"Ошибка: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_keep_list(self):
        """Сохранить только указанные интервалы (склейка в один файл, 1 прогон через filter_complex)."""
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return

        segs = self._collect_segments()
        if not segs:
            messagebox.showinfo("Интервалы", "Список пуст — сохранять нечего.")
            return

        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        ffprobe = self.app.var_ffprobe.get() or "ffprobe"
        src = self.app.state["video_path"]
        outdir = self.app.state["output_dir"]
        duration = float(self.app.state.get("duration") or 0.0)

        def worker():
            try:
                out = fragment_ops.keep_only_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=duration)
                self.app.msg_queue.put(("info", f"Готово: {out}"))
            except Exception as e:
                self.app.msg_queue.put(("info", f"Ошибка: {e}"))

        threading.Thread(target=worker, daemon=True).start()
