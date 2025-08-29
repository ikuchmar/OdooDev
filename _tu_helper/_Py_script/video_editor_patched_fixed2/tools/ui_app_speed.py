# video_editor/tools/ui_app_speed.py
# -*- coding: utf-8 -*-
"""
ui_app_speed.py — вкладка "Скорость".
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from . import utils, speed_ops

class UITabSpeed:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Изменение скорости видео/аудио").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Коэффициент (например 0.5, 1.25, 2):").grid(row=1, column=0, sticky="w")
        self.app.var_speed = tk.StringVar(value="1.5")
        ttk.Entry(frm, textvariable=self.app.var_speed, width=10).grid(row=1, column=1, sticky="w", padx=(0,10))

        self.app.var_pitch = tk.StringVar(value="preserve")
        ttk.Radiobutton(frm, text="Сохранить высоту голоса", variable=self.app.var_pitch, value="preserve").grid(row=2, column=0, sticky="w")
        ttk.Radiobutton(frm, text="Менять высоту вместе со скоростью", variable=self.app.var_pitch, value="change").grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Применить ко всему видео", command=lambda: self._apply_speed(scope="all")).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Применить к выделенному фрагменту", command=lambda: self._apply_speed(scope="fragment")).grid(row=3, column=1, sticky="w", pady=6)

    def _apply_speed(self, scope="all"):
        if not self.app.state["video_path"]:
            return
        try:
            factor = float(self.app.var_speed.get())
            if factor <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Ошибка", "Введите корректный коэффициент скорости (>0)")
            return
        pitch = self.app.var_pitch.get()
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        start = utils.hhmmss_to_sec(self.app.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.app.var_frag_end.get())
        def worker():
            out = speed_ops.apply_speed(ffmpeg, self.app.state["video_path"], outdir, factor=factor, pitch_mode=pitch, scope=scope, start=start, end=end)
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()
