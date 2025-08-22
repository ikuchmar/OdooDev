# video_editor/tools/ui_app_files.py
# -*- coding: utf-8 -*-
"""
ui_app_files.py — вкладка "Файлы": выбор ролика/аудио, длительность, папка вывода.
Дополнения:
- Поля для путей к утилитам: ffmpeg / ffprobe / ffplay (+ обзор и сохранение в app.conf).
- Безопасная инициализация self.app.var_ffmpeg/var_ffprobe/var_ffplay из app.conf (если их нет).
- Автозагрузка [app] last_video (с обрезкой кавычек) и установка папки вывода, длительности.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import ffprobe_info, utils
from . import config_store as cfg


class UITabFiles:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # завести безопасно переменные путей в главном app, если нет
        self._ensure_tool_vars_from_conf()

        # локальные переменные UI
        self.var_path = tk.StringVar(value="")
        self.var_outdir = tk.StringVar(value="")
        self.var_duration = tk.StringVar(value="длительность: —")

        self._build()
        self._load_last_video_from_conf()

    # ---------------- вспомогательные ----------------
    def _status(self, msg: str):
        vp = getattr(self.app, "var_progress", None)
        try:
            if vp is not None:
                vp.set(str(msg))
        except Exception:
            pass

    def _ensure_tool_vars_from_conf(self):
        """Создаёт в self.app StringVar для ffmpeg/ffprobe/ffplay из app.conf, если их нет."""
        if not hasattr(self.app, "var_ffmpeg"):
            self.app.var_ffmpeg = tk.StringVar(value=cfg.get("tools", "ffmpeg", "ffmpeg"))
        if not hasattr(self.app, "var_ffprobe"):
            self.app.var_ffprobe = tk.StringVar(value=cfg.get("tools", "ffprobe", "ffprobe"))
        if not hasattr(self.app, "var_ffplay"):
            self.app.var_ffplay = tk.StringVar(value=cfg.get("tools", "ffplay", "ffplay"))

    def _ffprobe_cmd(self) -> str:
        var = getattr(self.app, "var_ffprobe", None)
        try:
            return (var.get() or "ffprobe") if var is not None else "ffprobe"
        except Exception:
            return "ffprobe"

    # ---------------- UI ----------------
    def _build(self):
        root = ttk.Frame(self.parent, padding=10)
        root.pack(fill="both", expand=True)

        # Источник
        fr_sel = ttk.LabelFrame(root, text="Источник", padding=8)
        fr_sel.pack(fill="x")
        ttk.Label(fr_sel, text="Файл:").grid(row=0, column=0, sticky="w")
        ttk.Entry(fr_sel, textvariable=self.var_path, width=70, state="readonly").grid(row=0, column=1, sticky="we", padx=6)
        ttk.Button(fr_sel, text="Выбрать…", command=self._choose_file).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(fr_sel, text="Пересчитать длительность", command=self._recalc_duration).grid(row=0, column=3)
        ttk.Label(fr_sel, textvariable=self.var_duration).grid(row=1, column=1, sticky="w", pady=(6, 0))
        fr_sel.columnconfigure(1, weight=1)

        # Папка вывода
        fr_out = ttk.LabelFrame(root, text="Папка вывода", padding=8)
        fr_out.pack(fill="x", pady=(10, 0))
        ttk.Entry(fr_out, textvariable=self.var_outdir, width=70, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(fr_out, text="Открыть…", command=self._open_outdir).pack(side="left", padx=6)

        # Пути к утилитам
        fr_tools = ttk.LabelFrame(root, text="Пути к утилитам (FFmpeg)", padding=8)
        fr_tools.pack(fill="x", pady=(10, 0))

        # ffmpeg
        ttk.Label(fr_tools, text="ffmpeg:").grid(row=0, column=0, sticky="w")
        ttk.Entry(fr_tools, textvariable=self.app.var_ffmpeg, width=70).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Button(fr_tools, text="Обзор…", command=lambda: self._choose_tool("ffmpeg")).grid(row=0, column=2)

        # ffprobe
        ttk.Label(fr_tools, text="ffprobe:").grid(row=1, column=0, sticky="w")
        ttk.Entry(fr_tools, textvariable=self.app.var_ffprobe, width=70).grid(row=1, column=1, sticky="we", padx=6)
        ttk.Button(fr_tools, text="Обзор…", command=lambda: self._choose_tool("ffprobe")).grid(row=1, column=2)

        # ffplay
        ttk.Label(fr_tools, text="ffplay:").grid(row=2, column=0, sticky="w")
        ttk.Entry(fr_tools, textvariable=self.app.var_ffplay, width=70).grid(row=2, column=1, sticky="we", padx=6)
        ttk.Button(fr_tools, text="Обзор…", command=lambda: self._choose_tool("ffplay")).grid(row=2, column=2)

        ttk.Button(fr_tools, text="Сохранить пути", command=self._save_tools_to_conf).grid(row=3, column=1, sticky="e", pady=(8, 0))

        fr_tools.columnconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

    # --------- действия ----------
    def _choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите видео/аудио",
            filetypes=[("Медиа файлы", "*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.m4a *.aac *.flac *.webm"),
                       ("Все файлы", "*.*")]
        )
        if not path:
            return
        self._set_video_path(path, save_conf=True)

    def _recalc_duration(self):
        if not self.app.state.get("video_path"):
            messagebox.showinfo("Файл", "Сначала выберите видео/аудио.")
            return
        self._update_duration(self.app.state["video_path"])

    def _open_outdir(self):
        outdir = self.app.state.get("output_dir") or ""
        if not outdir or not os.path.isdir(outdir):
            messagebox.showinfo("Папка вывода", "Папка вывода не установлена.")
            return
        try:
            if os.name == "nt":
                os.startfile(outdir)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess; subprocess.Popen(["open", outdir])
            else:
                import subprocess; subprocess.Popen(["xdg-open", outdir])
        except Exception as e:
            messagebox.showwarning("Открыть папку", f"Не удалось открыть папку:\n{e}")

    def _choose_tool(self, which):
        """Выбор исполняемого файла для ffmpeg/ffprobe/ffplay."""
        path = filedialog.askopenfilename(
            title=f"Укажите {which}",
            filetypes=[("Исполняемые файлы", "*.exe *.bat *.cmd *.sh *.bin"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        if which == "ffmpeg":
            self.app.var_ffmpeg.set(path)
        elif which == "ffprobe":
            self.app.var_ffprobe.set(path)
        elif which == "ffplay":
            self.app.var_ffplay.set(path)

    def _save_tools_to_conf(self):
        """Сохраняет текущие пути в app.conf [tools]."""
        try:
            cfg.set("tools", "ffmpeg", self.app.var_ffmpeg.get())
            cfg.set("tools", "ffprobe", self.app.var_ffprobe.get())
            cfg.set("tools", "ffplay", self.app.var_ffplay.get())
            self._status("Пути к утилитам сохранены в app.conf")
        except Exception:
            self._status("Не удалось сохранить пути в app.conf")

    # --------- внутренняя логика ----------
    def _load_last_video_from_conf(self):
        raw = (cfg.get("app", "last_video", "") or "").strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1].strip()
        path = os.path.normpath(os.path.expanduser(os.path.expandvars(raw)))
        if path and os.path.isfile(path):
            self._set_video_path(path, save_conf=False)
        elif raw:
            self.var_path.set(raw)

    def _set_video_path(self, path, save_conf=True):
        apath = os.path.abspath(path)
        self.app.state["video_path"] = apath
        outdir = os.path.dirname(apath) or os.getcwd()
        self.app.state["output_dir"] = outdir

        self.var_path.set(apath)
        self.var_outdir.set(outdir)

        if save_conf:
            try:
                cfg.set("app", "last_video", apath)
            except Exception:
                pass

        self._update_duration(apath)
        self._status("Файл выбран. Папка вывода установлена в каталог файла.")

    def _update_duration(self, path):
        ffprobe = self._ffprobe_cmd()
        dur = ffprobe_info.get_duration(ffprobe, path) or 0.0
        self.app.state["duration"] = float(dur)
        self.var_duration.set(f"длительность: {utils.sec_to_hhmmss(int(dur))} ({int(dur)} с)")
