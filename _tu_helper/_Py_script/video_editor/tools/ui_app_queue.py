# video_editor/tools/ui_app_queue.py
# -*- coding: utf-8 -*-
"""
ui_app_queue.py — вкладка "Очередь/Статус". Пока демонстрационная.
"""
import tkinter as tk
from tkinter import ttk, messagebox

class UITabQueue:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        frm = ttk.Frame(self.parent, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Очередь задач (выполняются по очереди)").pack(anchor="w")
        self.lst_queue = tk.Listbox(frm, height=10)
        self.lst_queue.pack(fill="both", expand=True, pady=4)

        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="Запустить очередь", command=self._run_queue).pack(side="left")
        ttk.Button(btns, text="Открыть папку вывода", command=self._open_outdir).pack(side="left", padx=6)

    def _run_queue(self):
        messagebox.showinfo("Очередь", "Демонстрационная очередь: текущие кнопки запускают задачи сразу. Расширим при необходимости.")

    def _open_outdir(self):
        from . import utils
        utils.open_folder(self.app.state["output_dir"])
