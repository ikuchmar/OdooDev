# video_editor/tools/ui_app_convert.py
# -*- coding: utf-8 -*-
"""
ui_app_convert.py — вкладка "Конвертация".
"""
import tkinter as tk
from tkinter import ttk
import threading
from . import convert_ops

class UITabConvert:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Формат вывода:").grid(row=0, column=0, sticky="w")
        self.app.var_fmt = tk.StringVar(value="mp4")
        ttk.Combobox(frm, textvariable=self.app.var_fmt, values=["mp4","mkv","mov","webm","avi"], state="readonly", width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Профиль качества:").grid(row=1, column=0, sticky="w")
        self.app.var_quality = tk.StringVar(value="medium")
        ttk.Combobox(frm, textvariable=self.app.var_quality, values=["original","large","medium","small"], state="readonly", width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Разрешение:").grid(row=2, column=0, sticky="w")
        self.app.var_scale = tk.StringVar(value="keep")
        ttk.Combobox(frm, textvariable=self.app.var_scale, values=["keep","2160p","1440p","1080p","720p","480p"], state="readonly", width=10).grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Конвертировать", command=self._convert_now).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Ремакс (без перекодирования)", command=self._remux_now).grid(row=3, column=1, sticky="w", pady=6)

    def _convert_now(self):
        if not self.app.state["video_path"]:
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        def worker():
            out = convert_ops.convert_video(ffmpeg, self.app.state["video_path"], outdir, fmt=self.app.var_fmt.get(), quality=self.app.var_quality.get(), scale=self.app.var_scale.get())
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _remux_now(self):
        if not self.app.state["video_path"]:
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        def worker():
            out = convert_ops.remux_video(ffmpeg, self.app.state["video_path"], outdir, fmt=self.app.var_fmt.get())
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()
