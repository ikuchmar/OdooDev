# video_editor/tools/ui_app_logo.py
# -*- coding: utf-8 -*-
"""
ui_app_logo.py — вкладка "Логотип".
"""
import tkinter as tk
from tkinter import ttk, filedialog
import threading
from . import logo_overlay, utils

class UITabLogo:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="PNG логотип:").grid(row=0, column=0, sticky="w")
        self.app.var_logo_path = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.app.var_logo_path, width=50).grid(row=0, column=1, sticky="we")
        ttk.Button(frm, text="Выбрать...", command=self._choose_logo).grid(row=0, column=2, padx=6)

        ttk.Label(frm, text="Позиция:").grid(row=1, column=0, sticky="w")
        self.app.var_logo_pos = tk.StringVar(value="top-right")
        ttk.Combobox(frm, textvariable=self.app.var_logo_pos, values=["top-left","top-right","bottom-left","bottom-right"], state="readonly", width=15).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Масштаб (% ширины):").grid(row=2, column=0, sticky="w")
        self.app.var_logo_scale = tk.StringVar(value="10")
        ttk.Entry(frm, textvariable=self.app.var_logo_scale, width=10).grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Применить (ко всему видео)", command=self._apply_logo_all).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Применить (к фрагменту)", command=self._apply_logo_fragment).grid(row=3, column=1, sticky="w", pady=6)

        frm.columnconfigure(1, weight=1)

    def _choose_logo(self):
        p = filedialog.askopenfilename(title="Выберите PNG логотип", filetypes=[("PNG изображения","*.png")])
        if p:
            self.app.var_logo_path.set(p)

    def _apply_logo_all(self):
        if not self.app.state["video_path"] or not self.app.var_logo_path.get():
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        def worker():
            out = logo_overlay.apply_logo(ffmpeg, self.app.state["video_path"], outdir, self.app.var_logo_path.get(), self.app.var_logo_pos.get(), int(self.app.var_logo_scale.get() or "10"), scope="all")
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_logo_fragment(self):
        if not self.app.state["video_path"] or not self.app.var_logo_path.get():
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        start = utils.hhmmss_to_sec(self.app.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.app.var_frag_end.get())
        def worker():
            out = logo_overlay.apply_logo(ffmpeg, self.app.state["video_path"], outdir, self.app.var_logo_path.get(), self.app.var_logo_pos.get(), int(self.app.var_logo_scale.get() or "10"), scope="fragment", start=start, end=end)
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()
