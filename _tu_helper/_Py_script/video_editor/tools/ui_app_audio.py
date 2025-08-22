# video_editor/tools/ui_app_audio.py
# -*- coding: utf-8 -*-
"""
ui_app_audio.py — вкладка "Аудио": лента-аудиограмма с крупной вертикальной детализацией,
компактной областью просмотра, зумом (перестраивается ТОЛЬКО по кнопке),
курсор/скролл и управление ffplay (с видео или без).

Новое:
- Добавлено поле "Текущий зум" (read-only), которое сразу обновляется при нажатии − / 1× / +.
- Кнопки масштаба по-прежнему НЕ перестраивают PNG сразу; применится после "Сгенерировать аудиограмму".
"""

import os
import time
import tempfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import PhotoImage

from . import utils
from . import config_store as cfg


class UITabAudio:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # --- конфигурация из app.conf ---
        self._BASE_H = max(50, min(2000, cfg.get_int("audio", "base_height", 500)))
        self._VIEW_H = max(80, min(1000, cfg.get_int("audio", "view_height", 220)))
        self._zoom = max(0.25, min(8.0, cfg.get_float("audio", "zoom", 1.0)))
        self._px_per_sec_default = max(1, cfg.get_int("audio", "px_per_sec", 10))
        self._show_video_default = cfg.get_bool("audio", "show_video", True)

        # --- внутреннее состояние ---
        self._wave_tmp = None
        self._wave_img = None
        self._wave_w = 0
        self._wave_h = 0
        self._sec_per_px = 1.0
        self._cursor_x = 0
        self._cursor_id = None

        # воспроизведение
        self._play_proc = None
        self._play_started_at = 0.0
        self._play_start_sec = 0.0
        self._play_stop_evt = None

        # лимит ширины PNG
        self._MAX_WIDTH = 12000

        self._build()

    # ---------------- безопасные геттеры внешних утилит ----------------
    def _ffplay_cmd(self) -> str:
        var = getattr(self.app, "var_ffplay", None)
        try:
            return (var.get() or "ffplay") if var is not None else "ffplay"
        except Exception:
            return "ffplay"

    def _ffprobe_cmd(self) -> str:
        var = getattr(self.app, "var_ffprobe", None)
        try:
            return (var.get() or "ffprobe") if var is not None else "ffprobe"
        except Exception:
            return "ffprobe"

    # ---------------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------------
    def _build(self):
        root = ttk.Frame(self.parent, padding=10)
        root.pack(fill="both", expand=True)

        # Панель генерации аудиограммы
        top = ttk.LabelFrame(root, text="Аудиограмма (waveform)", padding=8)
        top.pack(fill="x")

        # Базовая плотность
        ttk.Label(top, text="Базовая плотность, пикс/сек:").pack(side="left")
        self.var_px_per_sec = tk.StringVar(value=str(self._px_per_sec_default))
        ttk.Entry(top, textvariable=self.var_px_per_sec, width=6).pack(side="left", padx=(4, 8))

        # Кнопки зума
        ttk.Label(top, text="Масштаб:").pack(side="left", padx=(8, 4))
        self.var_zoom_disp = tk.StringVar(value=f"{self._zoom:.2f}×")
        ttk.Button(top, text="−", width=3, command=lambda: self._zoom_change(0.5)).pack(side="left")
        ttk.Button(top, text="1×", width=3, command=lambda: self._zoom_set(1.0)).pack(side="left", padx=2)
        ttk.Button(top, text="+", width=3, command=lambda: self._zoom_change(2.0)).pack(side="left", padx=(0, 6))
        ttk.Label(top, text="(зум применится после «Сгенерировать»)", foreground="#666").pack(side="left", padx=(0, 8))

        # ПОЛЕ-индикатор текущего зума (наглядно видно, что кнопки сработали)
        ttk.Label(top, text="Текущий зум:").pack(side="left", padx=(8, 4))
        self.var_zoom_value = tk.StringVar(value=f"{self._zoom:.2f}×")
        e_zoom = ttk.Entry(top, textvariable=self.var_zoom_value, width=7, state="readonly", justify="center")
        e_zoom.pack(side="left")

        ttk.Button(top, text="Сгенерировать аудиограмму", command=self._gen_waveform)\
            .pack(side="left", padx=(10, 8))

        # Флаг показа видео
        self.var_show_video = tk.BooleanVar(value=self._show_video_default)
        ttk.Checkbutton(top, text="Показывать видео (ffplay)", variable=self.var_show_video)\
            .pack(side="left", padx=(8, 0))

        self.var_wave_hint = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.var_wave_hint, foreground="#555").pack(side="left", padx=(10, 0))

        # Полоса аудиограммы (Canvas) + скроллбар
        mid = ttk.Frame(root)
        mid.pack(fill="both", expand=True, pady=(8, 8))

        # Высота канваса — компактная; PNG может быть куда выше (base_height)
        self.canvas = tk.Canvas(mid, height=self._VIEW_H, bg="#111")
        self.canvas.pack(fill="both", expand=True, side="top")
        self.hbar = ttk.Scrollbar(mid, orient="horizontal", command=self.canvas.xview)
        self.hbar.pack(fill="x", side="bottom")
        self.canvas.configure(xscrollcommand=self.hbar.set)

        # Слой изображения
        self._img_item = self.canvas.create_image(0, 0, anchor="nw")

        # Клик по ленте — перемещает курсор/позицию
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Ползунок времени + кнопки управления
        bot = ttk.Frame(root)
        bot.pack(fill="x")

        ttk.Label(bot, text="Позиция:").pack(side="left")
        self.var_pos = tk.DoubleVar(value=0.0)
        self.scale = ttk.Scale(bot, from_=0.0, to=1.0, orient="horizontal", variable=self.var_pos,
                               command=self._on_scale_drag)
        self.scale.pack(side="left", fill="x", expand=True, padx=8)

        self.lbl_pos = ttk.Label(bot, text="00:00:00 / 00:00:00")
        self.lbl_pos.pack(side="left")

        ttk.Button(bot, text="▶ Пуск", command=self._play).pack(side="left", padx=(10, 4))
        ttk.Button(bot, text="⏹ Стоп", command=self._stop).pack(side="left", padx=4)
        ttk.Button(bot, text="⏩ Перейти", command=self._seek).pack(side="left", padx=4)

        root.columnconfigure(0, weight=1)

    # ---------------------------------------------------------------------
    # Генерация аудиограммы через ffmpeg
    # ---------------------------------------------------------------------
    def _run(self, args):
        try:
            cp = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, encoding="utf-8", errors="ignore")
            return cp.returncode, cp.stdout, cp.stderr
        except Exception as e:
            return 1, "", str(e)

    def _has_audio(self, path):
        rc, out, _ = self._run([
            self._ffprobe_cmd(), "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            path
        ])
        return (rc == 0) and (out.strip() != "")

    def _effective_px_per_sec(self, duration):
        """Возвращает (px_per_sec, width) с учётом зума и лимита ширины."""
        try:
            base_pps = max(1, int(float(self.var_px_per_sec.get())))
        except Exception:
            base_pps = self._px_per_sec_default
        desired = max(1, int(round(base_pps * float(self._zoom or 1.0))))
        width = int(duration * desired)
        if width <= self._MAX_WIDTH:
            return desired, width
        limited = max(1, int(self._MAX_WIDTH / max(1.0, duration)))
        return limited, int(duration * limited)

    def _gen_waveform(self):
        """Строит PNG аудиограммы (с учётом текущего зума) и загружает в Canvas."""
        if not self.app.state.get("video_path"):
            messagebox.showwarning("Нет файла", "Сначала выберите видео/аудио")
            return

        # сохраняем последний путь в конфиг
        try:
            cfg.set("app", "last_video", self.app.state["video_path"])
        except Exception:
            pass

        src = self.app.state["video_path"]
        duration = float(self.app.state.get("duration") or 0.0)

        if duration <= 0:
            messagebox.showwarning("Длительность", "Неизвестна длительность файла.")
            return

        if not self._has_audio(src):
            messagebox.showwarning("Аудио", "В файле не найден аудиопоток.")
            return

        px_per_sec, target_w = self._effective_px_per_sec(duration)
        H = self._BASE_H  # PNG высокий, Canvas ниже — просто «обрезает» по окну

        tmpdir = tempfile.mkdtemp(prefix="wave_")
        out_png = os.path.join(tmpdir, "wave.png")

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-y",
            "-i", src,
            "-filter_complex", f"aformat=channel_layouts=mono,showwavespic=s={target_w}x{H}:colors=white",
            "-frames:v", "1",
            out_png
        ]
        rc, _o, err = self._run(cmd)
        if rc != 0 or not os.path.exists(out_png):
            messagebox.showwarning("FFmpeg", f"Не удалось построить аудиограмму.\n{err.strip() or rc}")
            return

        try:
            self._wave_img = PhotoImage(file=out_png)
        except Exception as e:
            messagebox.showwarning("Tk", f"Не удалось загрузить аудиограмму: {e}")
            return

        self._wave_w = self._wave_img.width()
        self._wave_h = self._wave_img.height()
        self._sec_per_px = max(0.001, duration / float(self._wave_w))

        self.canvas.itemconfigure(self._img_item, image=self._wave_img)
        self.canvas.config(scrollregion=(0, 0, self._wave_w, self._wave_h))

        # восстановим/ограничим текущую позицию
        cur_sec = float(self.var_pos.get() or 0.0)
        self.scale.configure(from_=0.0, to=duration)
        self.var_pos.set(max(0.0, min(cur_sec, duration)))
        self._update_pos_label(self.var_pos.get(), duration)

        # курсор в нужном месте
        self._draw_cursor(self._time_to_x(self.var_pos.get()))

        # подпись
        note = f"PNG: {self._wave_w}×{self._wave_h}px  (~{px_per_sec} px/сек, zoom={self._zoom:.2f}×)"
        if self._wave_w >= self._MAX_WIDTH:
            note += f" • достигнут предел {self._MAX_WIDTH}px"
        self.var_wave_hint.set(note)

        # сохраним актуальные настройки в конфиг
        cfg.set("audio", "px_per_sec", px_per_sec)
        cfg.set("audio", "zoom", self._zoom)
        cfg.set("audio", "base_height", self._BASE_H)
        cfg.set("audio", "view_height", self._VIEW_H)
        cfg.set("audio", "show_video", "true" if self.var_show_video.get() else "false")

    # ---------------------------------------------------------------------
    # Зум (НЕ перестраивает PNG немедленно)
    # ---------------------------------------------------------------------
    def _zoom_set(self, z: float):
        """Установить значение зума и обновить индикаторы (без генерации PNG)."""
        z = max(0.25, min(8.0, float(z)))
        self._zoom = z
        # Обновляем оба индикатора: компактная метка и read-only поле
        self.var_zoom_disp.set(f"{self._zoom:.2f}×")
        self.var_zoom_value.set(f"{self._zoom:.2f}×")
        # Генерация произойдет только по кнопке "Сгенерировать аудиограмму"

    def _zoom_change(self, factor: float):
        """Изменить масштаб умножением (0.5 — меньше, 2.0 — больше)."""
        self._zoom_set(self._zoom * float(factor))

    # ---------------------------------------------------------------------
    # Преобразование время <-> пиксель (центр бина)
    # ---------------------------------------------------------------------
    def _time_to_x(self, sec):
        if self._wave_w <= 0:
            return 0
        return int(round(float(sec) / self._sec_per_px))

    def _x_to_time(self, x):
        if self._wave_w <= 0:
            return 0.0
        duration = float(self.scale.cget("to") or self.app.state.get("duration") or 0.0)
        sec = (float(x) + 0.5) * self._sec_per_px
        return max(0.0, min(sec, duration))

    # ---------------------------------------------------------------------
    # Курсор/скролл
    # ---------------------------------------------------------------------
    def _draw_cursor(self, x):
        x = max(0, min(int(x), max(0, self._wave_w - 1)))
        self._cursor_x = x
        if self._cursor_id is None:
            self._cursor_id = self.canvas.create_line(x, 0, x, self._wave_h, fill="red", width=2)
        else:
            self.canvas.coords(self._cursor_id, x, 0, x, self._wave_h)
        self._ensure_cursor_visible()

    def _ensure_cursor_visible(self):
        try:
            cw = int(self.canvas.winfo_width())
            if cw <= 0 or self._wave_w <= 0:
                return
            left_px = int(self.canvas.canvasx(0))
            right_px = left_px + cw
            x = int(self._cursor_x)
            if x < left_px + 40 or x > right_px - 40:
                new_left = max(0, x - cw // 2)
                frac = new_left / float(max(1, self._wave_w))
                self.canvas.xview_moveto(frac)
        except Exception:
            pass

    def _on_canvas_click(self, event):
        if self._wave_w <= 0:
            return
        x_abs = int(self.canvas.canvasx(event.x))
        x_abs = max(0, min(x_abs, self._wave_w - 1))
        sec = self._x_to_time(x_abs)
        self.var_pos.set(sec)
        self._draw_cursor(self._time_to_x(sec))
        self._update_pos_label(sec, self.scale.cget("to"))

    def _on_scale_drag(self, _val):
        duration = float(self.scale.cget("to") or 0.0)
        sec = float(self.var_pos.get() or 0.0)
        self._draw_cursor(self._time_to_x(sec))
        self._update_pos_label(sec, duration)

    def _update_pos_label(self, cur_sec, total_sec):
        try:
            total_sec = float(total_sec)
        except Exception:
            total_sec = float(self.app.state.get("duration") or 0.0)
        self.lbl_pos.config(text=f"{utils.sec_to_hhmmss(int(cur_sec))} / {utils.sec_to_hhmmss(int(total_sec))}")

    # ---------------------------------------------------------------------
    # Воспроизведение (ffplay), опционально с видео
    # ---------------------------------------------------------------------
    def _play(self):
        if not self.app.state.get("video_path"):
            messagebox.showwarning("Нет файла", "Сначала выберите видео/аудио")
            return

        start_sec = float(self.var_pos.get() or 0.0)
        duration = float(self.app.state.get("duration") or 0.0)
        left = max(0.0, duration - start_sec)

        self._stop(kill_only=True)

        cmd = [self._ffplay_cmd(), "-hide_banner", "-loglevel", "error"]
        if not self.var_show_video.get():
            cmd += ["-nodisp"]
        if start_sec > 0:
            cmd += ["-ss", str(start_sec)]
        if left > 0:
            cmd += ["-t", str(left), "-autoexit"]
        cmd += [self.app.state["video_path"]]

        try:
            self._play_proc = subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")
            self._play_proc = None
            return

        cfg.set("audio", "show_video", "true" if self.var_show_video.get() else "false")
        self._play_started_at = time.monotonic()
        self._play_start_sec = start_sec
        self._start_play_timer()

    def _seek(self):
        self._play()

    def _stop(self, kill_only=False):
        if self._play_stop_evt is not None:
            self._play_stop_evt.set()
        self._play_stop_evt = None

        if self._play_proc and self._play_proc.poll() is None:
            try:
                self._play_proc.terminate()
            except Exception:
                pass
            try:
                self._play_proc.wait(timeout=0.5)
            except Exception:
                try:
                    self._play_proc.kill()
                except Exception:
                    pass
        self._play_proc = None

        if not kill_only:
            self._update_pos_label(self.var_pos.get() or 0.0, self.scale.cget("to"))

    def _start_play_timer(self):
        self._play_stop_evt = threading.Event()

        def run():
            duration = float(self.app.state.get("duration") or 0.0)
            while not self._play_stop_evt.is_set():
                if self._play_proc is None or self._play_proc.poll() is not None:
                    break
                elapsed = time.monotonic() - self._play_started_at
                cur = min(duration, self._play_start_sec + elapsed)
                try:
                    self.canvas.after(0, self.var_pos.set, cur)
                    self.canvas.after(0, self._on_scale_drag, None)
                except Exception:
                    pass
                time.sleep(0.1)
            try:
                self.canvas.after(0, self._update_pos_label, float(self.var_pos.get() or 0.0), duration)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()
