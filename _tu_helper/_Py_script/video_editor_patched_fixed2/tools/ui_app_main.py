# video_editor/tools/ui_app_main.py
# -*- coding: utf-8 -*-
"""
ui_app_main.py — корневой класс App_UI (Tk) + сборка вкладок.
Вся логика каждой вкладки вынесена в отдельные файлы: tools/ui_app_*.py
"""
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox

# Импорт табов
from .ui_app_files import UITabFiles
from .ui_app_view import UITabView
from .ui_app_fragment import UITabFragment
#from .ui_app_fragment import UITabFragments as UITabFragment
from .ui_app_audio import UITabAudio
from .ui_app_denoise import UITabDenoise
from .ui_app_speed import UITabSpeed
from .ui_app_logo import UITabLogo
from .ui_app_convert import UITabConvert
from .ui_app_automontage import UITabAutomontage
from .ui_app_queue import UITabQueue

from . import config

class App_UI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("video_editor — GUI на Tkinter для FFmpeg")
        self.geometry("1200x800")

        self.state = {
            "video_path": None,
            "output_dir": os.path.join(os.path.expanduser("~"), "Videos"),
            "ffmpeg": config.get_ffmpeg_path(),
            "ffprobe": config.get_ffprobe_path(),
            "ffplay": config.get_ffplay_path(),
            "duration": 0.0,
        }

        self.msg_queue = queue.Queue()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.frames = {name: ttk.Frame(nb) for name in [
            "files","view","fragment","audio","denoise","speed","logo","convert","automontage","queue"
        ]}
        nb.add(self.frames["files"], text="Файлы")
        nb.add(self.frames["view"], text="Видео")
        nb.add(self.frames["fragment"], text="Фрагмент")
        nb.add(self.frames["audio"], text="Аудио")
        nb.add(self.frames["denoise"], text="Шумоподавление")
        nb.add(self.frames["speed"], text="Скорость")
        nb.add(self.frames["logo"], text="Логотип")
        nb.add(self.frames["convert"], text="Конвертация")
        nb.add(self.frames["automontage"], text="Автомонтаж")
        nb.add(self.frames["queue"], text="Очередь/Статус")

        self.tabs = {}
        self.tabs["files"] = UITabFiles(self, self.frames["files"])
        self.tabs["view"] = UITabView(self, self.frames["view"])
        self.tabs["fragment"] = UITabFragment(self, self.frames["fragment"])
        self.tabs["audio"] = UITabAudio(self, self.frames["audio"])
        self.tabs["denoise"] = UITabDenoise(self, self.frames["denoise"])
        self.tabs["speed"] = UITabSpeed(self, self.frames["speed"])
        self.tabs["logo"] = UITabLogo(self, self.frames["logo"])
        self.tabs["convert"] = UITabConvert(self, self.frames["convert"])
        self.tabs["automontage"] = UITabAutomontage(self, self.frames["automontage"])
        self.tabs["queue"] = UITabQueue(self, self.frames["queue"])

        # Общая строка статуса (видна на вкладке «Очередь/Статус»)
        self.var_progress = tk.StringVar(value="Готово")
        ttk.Label(self.frames["queue"], textvariable=self.var_progress).pack(anchor="w")

        self.after(150, self._poll_msgs)

    def _poll_msgs(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "timeline_ready":
                    self.tabs["view"].on_timeline_ready(payload)
                elif kind == "view_progress":
                    # Прогресс генерации ленты (N из M)
                    self.tabs["view"].on_progress(payload)
                elif kind == "am_segments":
                    self.tabs["automontage"].on_segments(payload)
                elif kind == "info":
                    messagebox.showinfo("Инфо", str(payload))
                elif kind == "progress":
                    # Общий статус (оставил на всякий случай)
                    self.var_progress.set(str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_msgs)


def run_app():
    app = App_UI()
    app.mainloop()
