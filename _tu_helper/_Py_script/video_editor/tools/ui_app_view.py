# video_editor/tools/ui_app_view.py
# -*- coding: utf-8 -*-
"""
ui_app_view.py — вкладка "Просмотр/Лента": управление ffplay, лента миниатюр, скриншоты.

Что добавлено/исправлено:
- Лента строится по ФАКТИЧЕСКИ созданным PNG (glob thumb_*.png), а не по "ожидаемому" count.
- Построение ленты идёт чанками (по 200 элементов) через .after(), чтобы длинные ролики
  не обрывались и UI не зависал.
- Авто-fallback: если быстрый режим (fps=1/step) дал слишком мало кадров, автоматически
  запускаем надёжный режим (по одному кадру через -ss).
- Исправлен обработчик _on_timeline_configure (был AttributeError).
"""

import os
import time
import glob
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import PhotoImage

from . import utils, thumbs_timeline, player_control


class UITabView:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # Локальное состояние вкладки
        self._thumb_images = []          # держим ссылки на PhotoImage, иначе GC их удалит
        self.timeline_cache = None       # временная папка с PNG миниатюр
        self.selected_thumbs = set()     # отмеченные секунды для сохранения
        self._watch_stop = None          # Event для остановки наблюдателя
        self._expected_total = 0         # оценка миниатюр (по длительности и шагу)
        self._step_sec = 10              # шаг ленты (по умолчанию 10 сек)

        # Данные для порционного построения
        self._items = []                 # список (sec:int, path:str)
        self._build_chunk_size = 200     # сколько миниатюр добавлять за один проход

        self._build()

    # ---------------------------------------------------------------------
    # Построение UI
    # ---------------------------------------------------------------------
    def _build(self):
        top = ttk.Frame(self.parent, padding=10)
        top.pack(fill="both", expand=True)

        # Панель кнопок
        btns = ttk.Frame(top)
        btns.pack(fill="x", pady=(0, 8))

        ttk.Button(btns, text="Открыть плеер (ffplay)", command=self._open_player).pack(side="left")
        ttk.Button(btns, text="−10с", command=lambda: self._seek_rel(-10)).pack(side="left", padx=4)
        ttk.Button(btns, text="+10с", command=lambda: self._seek_rel(10)).pack(side="left", padx=4)

        ttk.Label(btns, text="Перейти к (мм:сс):").pack(side="left", padx=(10, 4))
        self.app.var_goto = tk.StringVar(value="00:00")
        ttk.Entry(btns, textvariable=self.app.var_goto, width=8).pack(side="left")
        ttk.Button(btns, text="Перейти", command=self._seek_abs).pack(side="left", padx=4)

        # Настройки ленты
        ttk.Label(btns, text="Шаг ленты (сек):").pack(side="left", padx=(16, 4))
        self.var_tl_step = tk.StringVar(value="10")
        ttk.Entry(btns, textvariable=self.var_tl_step, width=6).pack(side="left")

        self.var_safe_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(btns, text="Надёжный режим (кадр через -ss)", variable=self.var_safe_mode)\
            .pack(side="left", padx=(16, 4))

        ttk.Button(btns, text="Сгенерировать ленту", command=self._gen_timeline).pack(side="left", padx=10)

        # Прогресс (текст + progressbar)
        pr = ttk.Frame(top)
        pr.pack(fill="x", pady=(4, 8))
        self.var_tl_progress = tk.StringVar(value="Лента: 0/0")
        ttk.Label(pr, textvariable=self.var_tl_progress).pack(side="left")
        self.pb_tl = ttk.Progressbar(pr, orient="horizontal", mode="determinate",
                                     length=300, maximum=100, value=0)
        self.pb_tl.pack(side="left", padx=10)

        # Полоса ленты (Canvas + горизонтальный скролл)
        self.timeline_canvas = tk.Canvas(top, height=220, bg="#111")
        self.timeline_canvas.pack(fill="x", expand=False)
        self.timeline_scroll = ttk.Scrollbar(top, orient="horizontal",
                                             command=self.timeline_canvas.xview)
        self.timeline_scroll.pack(fill="x")
        self.timeline_canvas.configure(xscrollcommand=self.timeline_scroll.set)

        self.timeline_frame = ttk.Frame(self.timeline_canvas)
        self.timeline_window = self.timeline_canvas.create_window(
            (0, 0), window=self.timeline_frame, anchor="nw"
        )
        self.timeline_frame.bind("<Configure>", self._on_timeline_configure)

        # Блок сохранения выбранных кадров
        fr_ss = ttk.Frame(top)
        fr_ss.pack(fill="x", pady=(8, 0))
        ttk.Button(fr_ss, text="Сохранить выбранные кадры (PNG)", command=self._save_selected_screens)\
            .pack(side="left")
        ttk.Label(fr_ss, text="Каждая миниатюра = кадр по выбранному шагу. Отмечайте чекбокс под ним.")\
            .pack(side="left", padx=10)

    # ---------------------------------------------------------------------
    # Управление плеером
    # ---------------------------------------------------------------------
    def _open_player(self):
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return
        player_control.open_player(
            self.app.var_ffplay.get() or "ffplay",
            self.app.state["video_path"],
            start_sec=utils.hhmmss_to_sec(self.app.var_goto.get())
        )

    def _seek_rel(self, delta):
        cur = utils.hhmmss_to_sec(self.app.var_goto.get())
        cur = max(0.0, cur + delta)
        self.app.var_goto.set(utils.sec_to_mmss(cur))
        self._open_player()

    def _seek_abs(self):
        self._open_player()

    # ---------------------------------------------------------------------
    # Генерация ленты
    # ---------------------------------------------------------------------
    def _gen_timeline(self):
        if not self.app.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео")
            return

        # Парсим шаг
        try:
            step = int(float(self.var_tl_step.get()))
            if step < 1:
                raise ValueError
        except Exception:
            messagebox.showwarning("Шаг ленты", "Введите целое число секунд (>=1). Например: 10")
            return
        self._step_sec = step

        # Очистка предыдущего UI/прогресса
        self.clear_timeline()
        tmpdir = tempfile.mkdtemp(prefix="timeline_")
        self.timeline_cache = tmpdir

        # Ожидаемое число кадров (только для прогресса)
        duration = float(self.app.state["duration"] or 0.0)
        self._expected_total = max(1, int(duration // step) + 1)
        self._set_progress(0, self._expected_total)
        self.app.var_progress.set("Генерация ленты миниатюр...")

        safe_mode = bool(self.var_safe_mode.get())

        def worker_gen():
            ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"

            # 1) Пытаемся быстрым способом (если не попросили "надёжный")
            count = 0
            used_mode = "fast"
            if not safe_mode:
                count = thumbs_timeline.generate_thumbs_step(
                    ffmpeg, self.app.state["video_path"], tmpdir, duration, step
                )

            # 2) Авто-fallback: если быстрый дал подозрительно мало (менее 90% ожидаемого),
            #    пересоздаём кадры надёжным способом
            if safe_mode or (self._expected_total > 0 and count < max(5, int(self._expected_total * 0.9))):
                used_mode = "safe"
                count = thumbs_timeline.generate_thumbs_step_iter(
                    ffmpeg, self.app.state["video_path"], tmpdir, duration, step
                )
                # информируем пользователя (через строку статуса)
                self.app.msg_queue.put(("progress", "Авто-fallback на надёжный режим…"))

            # 3) Финальный подсчёт по фактическим файлам
            count_final = len(glob.glob(os.path.join(tmpdir, "thumb_*.png")))
            self.app.msg_queue.put(("timeline_ready", {
                "dir": tmpdir, "count": count_final, "step": step, "mode": used_mode
            }))

        # Наблюдатель прогресса: считает количество готовых PNG
        def worker_watch():
            self._watch_stop = threading.Event()
            while not self._watch_stop.is_set():
                done = len(glob.glob(os.path.join(tmpdir, "thumb_*.png")))
                self.app.msg_queue.put(("view_progress", {"done": done, "total": self._expected_total}))
                time.sleep(0.3)

        threading.Thread(target=worker_gen, daemon=True).start()
        threading.Thread(target=worker_watch, daemon=True).start()

    def on_progress(self, payload):
        done = int(payload.get("done", 0))
        total = int(payload.get("total", max(1, self._expected_total or 1)))
        self._set_progress(done, total)

    def _set_progress(self, done, total):
        done = max(0, min(done, total))
        self.var_tl_progress.set(f"Лента: {done}/{total}")
        pct = 0 if total <= 0 else int(round(done * 100.0 / total))
        self.pb_tl["value"] = pct

    def on_timeline_ready(self, payload):
        """Финал генерации: останавливаем наблюдателя, собираем фактические файлы и строим ленту чанками."""
        if self._watch_stop is not None:
            self._watch_stop.set()

        tmpdir = payload.get("dir")
        step = int(payload.get("step") or self._step_sec or 1)

        # Собираем фактические файлы и парсим секунды из имён
        files = sorted(glob.glob(os.path.join(tmpdir, "thumb_*.png")))
        self._items = []
        for p in files:
            # Имя вида thumb_000120.png -> берём число 000120 как секунду
            try:
                base = os.path.basename(p)
                sec = int(os.path.splitext(base)[0].split("_", 1)[1])
            except Exception:
                # если вдруг имя нестандартное — пропускаем
                continue
            self._items.append((sec, p))

        # Финализируем прогресс по факту
        self._set_progress(len(self._items), max(len(self._items), self._expected_total or 1))

        if not self._items:
            messagebox.showwarning("Лента", "Миниатюры не создались. Проверьте FFmpeg/FFprobe и длительность видео.")
            self.app.var_progress.set("Не удалось создать ленту")
            return

        # Строим ленту порциями, чтобы не было обрыва/фриза на больших списках
        self._thumb_images.clear()
        self.selected_thumbs.clear()
        self._step_sec = step  # запомним для чекбоксов/подписей
        self._build_timeline_chunk(0)

    # ---------------------------------------------------------------------
    # Порционное построение ленты
    # ---------------------------------------------------------------------
    def _build_timeline_chunk(self, start_index):
        """
        Добавляет на ленту миниатюры с индекса start_index по (start_index + chunk - 1).
        После — планирует следующий кусок через .after().
        """
        end_index = min(start_index + self._build_chunk_size, len(self._items))
        for i in range(start_index, end_index):
            sec_mark, img_path = self._items[i]

            fr = ttk.Frame(self.timeline_frame, padding=3)
            fr.grid(row=0, column=i, sticky="n")

            try:
                img = PhotoImage(file=img_path)
            except Exception:
                img = None

            if img:
                self._thumb_images.append(img)
                lbl = ttk.Label(fr, image=img)
            else:
                lbl = ttk.Label(fr, text=f"{sec_mark}s", background="#222", foreground="#fff", width=16)
            lbl.pack()

            var_chk = tk.BooleanVar(value=False)
            def make_cb_callback(s=sec_mark, v=var_chk):
                return lambda: self._on_thumb_check(s, v.get())
            cb = ttk.Checkbutton(fr, text=utils.sec_to_mmss(sec_mark),
                                 variable=var_chk, command=make_cb_callback())
            cb.pack()

        # Обновляем область прокрутки
        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))

        # Если ещё остались элементы — планируем следующий кусок
        if end_index < len(self._items):
            # маленькая пауза, чтобы дать UI отрисоваться
            self.parent.after(1, lambda: self._build_timeline_chunk(end_index))
        else:
            self.app.var_progress.set("Лента миниатюр готова")

    # ---------------------------------------------------------------------
    # Вспомогательные методы
    # ---------------------------------------------------------------------
    def clear_timeline(self):
        """Полностью очищает текущую ленту и сбрасывает прогресс."""
        for w in list(self.timeline_frame.children.values() if hasattr(self, "timeline_frame") else []):
            w.destroy()
        self._thumb_images.clear()
        self.selected_thumbs.clear()
        if hasattr(self, "timeline_canvas"):
            self.timeline_canvas.configure(scrollregion=(0, 0, 0, 0))
        self._set_progress(0, 1)
        self._items = []

    def _on_timeline_configure(self, event):
        """Подгоняет scrollregion под реальный размер содержимого при изменении макета."""
        try:
            self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))
        except Exception:
            pass

    def _on_thumb_check(self, sec, is_checked):
        """Добавляет/удаляет секунду кадра в множестве выбранных миниатюр."""
        if is_checked:
            self.selected_thumbs.add(sec)
        else:
            self.selected_thumbs.discard(sec)

    def _save_selected_screens(self):
        """Сохраняет все отмеченные миниатюры в PNG рядом с исходным видео."""
        if not self.selected_thumbs:
            messagebox.showinfo("Скриншоты", "Не выбраны кадры для сохранения")
            return
        outdir = self.app.state["output_dir"]
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        base = os.path.splitext(os.path.basename(self.app.state["video_path"]))[0]

        def worker():
            for sec in sorted(self.selected_thumbs):
                out = os.path.join(outdir, f"{base}_{utils.sec_to_hhmmss(sec).replace(':','-')}.png")
                thumbs_timeline.save_frame(ffmpeg, self.app.state["video_path"], sec, out)
            self.app.msg_queue.put(("info", "Скриншоты сохранены"))

        threading.Thread(target=worker, daemon=True).start()
