# video_editor/tools/ui_app_automontage.py
# -*- coding: utf-8 -*-
"""
ui_app_automontage.py — вкладка "Автомонтаж".
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from . import automontage, utils

class UITabAutomontage:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Авто-вырезка пауз/статичных моментов").grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(frm, text="Режим:").grid(row=1, column=0, sticky="w")
        self.app.var_am_mode = tk.StringVar(value="both")
        ttk.Combobox(frm, textvariable=self.app.var_am_mode, values=["audio","video","both"], state="readonly", width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Порог тишины (дБ, напр. -35):").grid(row=2, column=0, sticky="w")
        self.app.var_am_db = tk.StringVar(value="-35")
        ttk.Entry(frm, textvariable=self.app.var_am_db, width=8).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Порог застывшего кадра (freezedetect, t):").grid(row=3, column=0, sticky="w")
        self.app.var_am_freeze_t = tk.StringVar(value="2.0")
        ttk.Entry(frm, textvariable=self.app.var_am_freeze_t, width=8).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Мин. длительность паузы (сек):").grid(row=4, column=0, sticky="w")
        self.app.var_am_minlen = tk.StringVar(value="1.0")
        ttk.Entry(frm, textvariable=self.app.var_am_minlen, width=8).grid(row=4, column=1, sticky="w")

        ttk.Label(frm, text="Запас до/после (сек):").grid(row=5, column=0, sticky="w")
        self.app.var_am_pad = tk.StringVar(value="0.2")
        ttk.Entry(frm, textvariable=self.app.var_am_pad, width=8).grid(row=5, column=1, sticky="w")

        ttk.Button(frm, text="Проанализировать", command=self._analyze_automontage).grid(row=6, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Вырезать найденные паузы", command=lambda: self._apply_automontage(mode="cut")).grid(row=6, column=1, sticky="w", pady=6)
        ttk.Button(frm, text="Сжать паузы (ускорить)", command=lambda: self._apply_automontage(mode="compress")).grid(row=6, column=2, sticky="w", pady=6)

        self.txt_segments = tk.Text(frm, height=10, width=100)
        self.txt_segments.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=6)
        frm.rowconfigure(7, weight=1)
        frm.columnconfigure(3, weight=1)

    def _analyze_automontage(self):
        if not self.app.state["video_path"]:
            return
        mode = self.app.var_am_mode.get()
        silence_db = float(self.app.var_am_db.get() or -35)
        freeze_t = float(self.app.var_am_freeze_t.get() or 2.0)
        minlen = float(self.app.var_am_minlen.get() or 1.0)
        pad = float(self.app.var_am_pad.get() or 0.2)
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        def worker():
            segs = automontage.analyze(ffmpeg, self.app.state["video_path"], mode=mode, silence_db=silence_db, freeze_t=freeze_t, minlen=minlen, pad=pad)
            self.app.msg_queue.put(("am_segments", segs))
        threading.Thread(target=worker, daemon=True).start()

    def on_segments(self, segs):
        self.txt_segments.delete("1.0", "end")
        for a,b in segs:
            self.txt_segments.insert("end", f"{utils.sec_to_hhmmss(a)} - {utils.sec_to_hhmmss(b)}\n")
        messagebox.showinfo("Анализ", f"Найдено сегментов: {len(segs)}")

    def _apply_automontage(self, mode="cut"):
        if not self.app.state["video_path"]:
            return
        ffmpeg = self.app.var_ffmpeg.get() or "ffmpeg"
        outdir = self.app.state["output_dir"]
        text = self.txt_segments.get("1.0", "end").strip()
        segs = automontage.parse_segments_text(text)
        if not segs:
            messagebox.showwarning("Нет сегментов", "Сначала выполните анализ и убедитесь, что список сегментов непустой.")
            return
        def worker():
            out = automontage.apply(ffmpeg, self.app.state["video_path"], segs, outdir, mode=mode)
            self.app.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()
