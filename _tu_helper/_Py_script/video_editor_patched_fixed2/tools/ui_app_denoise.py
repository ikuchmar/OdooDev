
# video_editor/tools/ui_app_denoise.py
# -*- coding: utf-8 -*-
"""
ui_app_denoise.py — вкладка "Шумоподавление".
"""
import tkinter as tk
from tkinter import ttk
import threading
from . import denoise, utils

class UITabDenoise:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Шумоподавление аудио").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Пресет:").grid(row=1, column=0, sticky="w")
        self.app.var_dn_preset = tk.StringVar(value="medium")
        ttk.Combobox(frm, textvariable=self.app.var_dn_preset, values=["light","medium","strong"], state="readonly", width=10).grid(row=1, column=1, sticky="w")
        ttk.Button(frm, text="Применить ко всему видео", command=self._denoise_all).grid(row=1, column=2, sticky="w", padx=8)
        ttk.Button(frm, text="Применить к выделенному фрагменту", command=self._denoise_fragment).grid(row=1, column=3, sticky="w")

    def _denoise_all(self):
        if not self.app.state["video_path"]:
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        preset = self.app.var_dn_preset.get()
        def worker():
            out = denoise.apply_denoise(ffmpeg, self.app.state["video_path"], outdir, preset=preset, scope="all")
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _denoise_fragment(self):
        if not self.app.state["video_path"]:
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        preset = self.app.var_dn_preset.get()
        start = utils.hhmmss_to_sec(self.app.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.app.var_frag_end.get())
        def worker():
            out = denoise.apply_denoise(ffmpeg, self.app.state["video_path"], outdir, preset=preset, scope="fragment", start=start, end=end)
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()
