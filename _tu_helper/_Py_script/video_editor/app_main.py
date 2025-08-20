# -*- coding: utf-8 -*-
"""
app_main.py — точка входа GUI-приложения "video_editor".
Приложение: простой настольный интерфейс на Tkinter для работы с видео через FFmpeg/FFprobe.

ВНИМАНИЕ:
- Нужны установленные FFmpeg и FFprobe (в PATH) или укажите путь в Настройках.
- Код максимально простой и снабжен русскими комментариями "что и зачем делаем".
- Все операции выполняются в отдельных потоках, чтобы не блокировать UI.
- Просмотр видео реализован через отдельное окно ffplay (самый надежный способ без внешних библиотек).
"""

import os
import sys
import threading
import queue
import tempfile
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import PhotoImage

# Локальные модули проекта
from tools import config, utils, ffprobe_info, thumbs_timeline, player_control
from tools import fragment_ops, audio_ops, denoise, speed_ops, logo_overlay, convert_ops
from tools import automontage, queue_runner, presets

# ------------------------ Класс интерфейса приложения ------------------------
class App_UI(tk.Tk):
    """
    Класс App_UI содержит только логику интерфейса
    и вызовы вспомогательных функций из папки tools/.
    """

    def __init__(self):
        super().__init__()
        self.title("video_editor — простой GUI на Tkinter для FFmpeg")
        self.geometry("1200x800")

        # Храним состояние
        self.state = {
            "video_path": None,     # путь к текущему видео
            "output_dir": os.path.join(os.path.expanduser("~"), "Videos"),
            "ffmpeg": config.get_ffmpeg_path(),
            "ffprobe": config.get_ffprobe_path(),
            "ffplay": config.get_ffplay_path(),
            "duration": 0.0,
            "timeline_cache": None, # временная папка для миниатюр
            "selected_thumbs": set(), # выбранные секунды для скриншотов
        }

        # Очередь сообщений от фоновых потоков (для прогресса/логов)
        self.msg_queue = queue.Queue()

        # Создаём вкладки
        self._build_tabs()

        # Таймер для обработки очереди сообщений
        self.after(100, self._poll_msgs)

    # -------------------- Построение вкладок --------------------
    def _build_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Вкладки
        self.tab_files = ttk.Frame(notebook)
        self.tab_view = ttk.Frame(notebook)
        self.tab_fragment = ttk.Frame(notebook)
        self.tab_audio = ttk.Frame(notebook)
        self.tab_denoise = ttk.Frame(notebook)
        self.tab_speed = ttk.Frame(notebook)
        self.tab_logo = ttk.Frame(notebook)
        self.tab_convert = ttk.Frame(notebook)
        self.tab_automontage = ttk.Frame(notebook)
        self.tab_queue = ttk.Frame(notebook)

        notebook.add(self.tab_files, text="Файлы")
        notebook.add(self.tab_view, text="Просмотр/Лента")
        notebook.add(self.tab_fragment, text="Фрагмент")
        notebook.add(self.tab_audio, text="Аудио")
        notebook.add(self.tab_denoise, text="Шумоподавление")
        notebook.add(self.tab_speed, text="Скорость")
        notebook.add(self.tab_logo, text="Логотип")
        notebook.add(self.tab_convert, text="Конвертация")
        notebook.add(self.tab_automontage, text="Автомонтаж")
        notebook.add(self.tab_queue, text="Очередь/Статус")

        self._build_tab_files(self.tab_files)
        self._build_tab_view(self.tab_view)
        self._build_tab_fragment(self.tab_fragment)
        self._build_tab_audio(self.tab_audio)
        self._build_tab_denoise(self.tab_denoise)
        self._build_tab_speed(self.tab_speed)
        self._build_tab_logo(self.tab_logo)
        self._build_tab_convert(self.tab_convert)
        self._build_tab_automontage(self.tab_automontage)
        self._build_tab_queue(self.tab_queue)

    # -------------------- Вкладка "Файлы" --------------------
    def _build_tab_files(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        # Выбор видео
        ttk.Label(frm, text="Текущее видео:").grid(row=0, column=0, sticky="w")
        self.var_video = tk.StringVar(value="(файл не выбран)")
        ttk.Label(frm, textvariable=self.var_video).grid(row=0, column=1, sticky="w")
        ttk.Button(frm, text="Открыть видео...", command=self._choose_video).grid(row=0, column=2, padx=8)

        # Папка вывода
        ttk.Label(frm, text="Папка вывода:").grid(row=1, column=0, sticky="w", pady=(10,0))
        self.var_outdir = tk.StringVar(value=self.state["output_dir"])
        ttk.Entry(frm, textvariable=self.var_outdir, width=60).grid(row=1, column=1, sticky="we", pady=(10,0))
        ttk.Button(frm, text="Выбрать...", command=self._choose_outdir).grid(row=1, column=2, padx=8, pady=(10,0))

        # Пути к ffmpeg/ffprobe/ffplay
        ttk.Label(frm, text="Путь к FFmpeg:").grid(row=2, column=0, sticky="w", pady=(10,0))
        self.var_ffmpeg = tk.StringVar(value=self.state["ffmpeg"] or "")
        ttk.Entry(frm, textvariable=self.var_ffmpeg, width=60).grid(row=2, column=1, sticky="we", pady=(10,0))
        ttk.Button(frm, text="Найти", command=lambda: self._auto_find_bin("ffmpeg")).grid(row=2, column=2, padx=8, pady=(10,0))

        ttk.Label(frm, text="Путь к FFprobe:").grid(row=3, column=0, sticky="w")
        self.var_ffprobe = tk.StringVar(value=self.state["ffprobe"] or "")
        ttk.Entry(frm, textvariable=self.var_ffprobe, width=60).grid(row=3, column=1, sticky="we")
        ttk.Button(frm, text="Найти", command=lambda: self._auto_find_bin("ffprobe")).grid(row=3, column=2, padx=8)

        ttk.Label(frm, text="Путь к FFplay:").grid(row=4, column=0, sticky="w")
        self.var_ffplay = tk.StringVar(value=self.state["ffplay"] or "")
        ttk.Entry(frm, textvariable=self.var_ffplay, width=60).grid(row=4, column=1, sticky="we")
        ttk.Button(frm, text="Найти", command=lambda: self._auto_find_bin("ffplay")).grid(row=4, column=2, padx=8)

        # Кнопка проверить
        ttk.Button(frm, text="Проверить FFmpeg/FFprobe/FFplay", command=self._check_bins).grid(row=5, column=0, columnspan=3, pady=10, sticky="w")

        # Растяжение
        frm.columnconfigure(1, weight=1)

    # -------------------- Вкладка "Просмотр/Лента" --------------------
    def _build_tab_view(self, parent):
        top = ttk.Frame(parent, padding=10)
        top.pack(fill="both", expand=True)

        # Кнопки управления плеером
        btns = ttk.Frame(top)
        btns.pack(fill="x", pady=(0,8))
        ttk.Button(btns, text="Открыть плеер (ffplay)", command=self._open_player).pack(side="left")
        ttk.Button(btns, text="−10с", command=lambda: self._seek_rel(-10)).pack(side="left", padx=4)
        ttk.Button(btns, text="+10с", command=lambda: self._seek_rel(10)).pack(side="left", padx=4)
        ttk.Label(btns, text="Перейти к (мм:сс):").pack(side="left", padx=(10,4))
        self.var_goto = tk.StringVar(value="00:00")
        ttk.Entry(btns, textvariable=self.var_goto, width=8).pack(side="left")
        ttk.Button(btns, text="Перейти", command=self._seek_abs).pack(side="left", padx=4)
        ttk.Button(btns, text="Сгенерировать ленту по секундам", command=self._gen_timeline).pack(side="left", padx=10)

        # Прокручиваемая область миниатюр с чекбоксами
        self.timeline_canvas = tk.Canvas(top, height=220, bg="#111")
        self.timeline_canvas.pack(fill="x", expand=False)
        self.timeline_scroll = ttk.Scrollbar(top, orient="horizontal", command=self.timeline_canvas.xview)
        self.timeline_scroll.pack(fill="x")
        self.timeline_canvas.configure(xscrollcommand=self.timeline_scroll.set)

        self.timeline_frame = ttk.Frame(self.timeline_canvas)
        self.timeline_window = self.timeline_canvas.create_window((0,0), window=self.timeline_frame, anchor="nw")

        self.timeline_frame.bind("<Configure>", self._on_timeline_configure)

        # Кнопки скриншотов
        fr_ss = ttk.Frame(top)
        fr_ss.pack(fill="x", pady=(8,0))
        ttk.Button(fr_ss, text="Сохранить выбранные кадры (PNG)", command=self._save_selected_screens).pack(side="left")
        ttk.Label(fr_ss, text="Каждая миниатюра = 1 секунда. Кликните чекбокс под ней, чтобы сохранить кадр.").pack(side="left", padx=10)

        # Хранилище PhotoImage, чтобы картинки не "собирал мусор"
        self._thumb_images = []

    def _on_timeline_configure(self, event):
        # Обновляем область прокрутки при изменении размеров внутреннего фрейма
        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))

    # -------------------- Вкладка "Фрагмент" --------------------
    def _build_tab_fragment(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Начало (мм:сс)").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Конец (мм:сс)").grid(row=0, column=1, sticky="w")
        self.var_frag_start = tk.StringVar(value="00:00")
        self.var_frag_end = tk.StringVar(value="00:05")
        ttk.Entry(frm, textvariable=self.var_frag_start, width=10).grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_frag_end, width=10).grid(row=1, column=1, sticky="w")

        self.var_cut_mode = tk.StringVar(value="fast")
        ttk.Radiobutton(frm, text="Быстро (без перекодирования)", variable=self.var_cut_mode, value="fast").grid(row=2, column=0, sticky="w", pady=(8,0))
        ttk.Radiobutton(frm, text="Точно (с перекодированием)", variable=self.var_cut_mode, value="precise").grid(row=2, column=1, sticky="w", pady=(8,0))

        ttk.Button(frm, text="Удалить выделенное", command=self._delete_fragment).grid(row=3, column=0, pady=10, sticky="w")
        ttk.Button(frm, text="Сохранить выделенное в новый файл", command=self._save_fragment).grid(row=3, column=1, pady=10, sticky="w")

        frm.columnconfigure(2, weight=1)

    # -------------------- Вкладка "Аудио" --------------------
    def _build_tab_audio(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Операции со звуком").grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Button(frm, text="Удалить звук у всего видео", command=self._remove_audio_all).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Button(frm, text="Сделать тишину в выделенном фрагменте", command=self._mute_audio_fragment).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Separator(frm, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="we", pady=(8,8))

        ttk.Button(frm, text="Заменить звук — из файла (на всё видео)", command=self._replace_audio_from_file).grid(row=3, column=0, sticky="w", pady=4)
        ttk.Button(frm, text="Записать с микрофона и заменить (на всё видео)", command=self._replace_audio_from_mic).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Button(frm, text="Смешать поверх оригинала (из файла)", command=self._mix_audio_from_file).grid(row=3, column=2, sticky="w", pady=4)

        ttk.Separator(frm, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="we", pady=(8,8))

        ttk.Button(frm, text="Нормализация (быстрая)", command=lambda: self._normalize_audio(mode="fast")).grid(row=5, column=0, sticky="w", pady=4)
        ttk.Button(frm, text="Нормализация (EBU R128, 2 прохода)", command=lambda: self._normalize_audio(mode="ebu")).grid(row=5, column=1, sticky="w", pady=4)

        frm.columnconfigure(3, weight=1)

    # -------------------- Вкладка "Шумоподавление" --------------------
    def _build_tab_denoise(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Шумоподавление аудио").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Пресет:").grid(row=1, column=0, sticky="w")
        self.var_dn_preset = tk.StringVar(value="medium")
        ttk.Combobox(frm, textvariable=self.var_dn_preset, values=["light", "medium", "strong"], state="readonly", width=10).grid(row=1, column=1, sticky="w")
        ttk.Button(frm, text="Применить ко всему видео", command=self._denoise_all).grid(row=1, column=2, sticky="w", padx=8)
        ttk.Button(frm, text="Применить к выделенному фрагменту", command=self._denoise_fragment).grid(row=1, column=3, sticky="w")

    # -------------------- Вкладка "Скорость" --------------------
    def _build_tab_speed(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Изменение скорости видео/аудио").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Коэффициент (например 0.5, 1.25, 2):").grid(row=1, column=0, sticky="w")
        self.var_speed = tk.StringVar(value="1.5")
        ttk.Entry(frm, textvariable=self.var_speed, width=10).grid(row=1, column=1, sticky="w", padx=(0,10))

        self.var_pitch = tk.StringVar(value="preserve")
        ttk.Radiobutton(frm, text="Сохранить высоту голоса", variable=self.var_pitch, value="preserve").grid(row=2, column=0, sticky="w")
        ttk.Radiobutton(frm, text="Менять высоту вместе со скоростью", variable=self.var_pitch, value="change").grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Применить ко всему видео", command=lambda: self._apply_speed(scope="all")).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Применить к выделенному фрагменту", command=lambda: self._apply_speed(scope="fragment")).grid(row=3, column=1, sticky="w", pady=6)

    # -------------------- Вкладка "Логотип" --------------------
    def _build_tab_logo(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="PNG логотип:").grid(row=0, column=0, sticky="w")
        self.var_logo_path = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.var_logo_path, width=50).grid(row=0, column=1, sticky="we")
        ttk.Button(frm, text="Выбрать...", command=self._choose_logo).grid(row=0, column=2, padx=6)

        ttk.Label(frm, text="Позиция:").grid(row=1, column=0, sticky="w")
        self.var_logo_pos = tk.StringVar(value="top-right")
        ttk.Combobox(frm, textvariable=self.var_logo_pos, values=["top-left","top-right","bottom-left","bottom-right"], state="readonly", width=15).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Масштаб (% ширины):").grid(row=2, column=0, sticky="w")
        self.var_logo_scale = tk.StringVar(value="10")
        ttk.Entry(frm, textvariable=self.var_logo_scale, width=10).grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Применить (ко всему видео)", command=self._apply_logo_all).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Применить (к фрагменту)", command=self._apply_logo_fragment).grid(row=3, column=1, sticky="w", pady=6)

        frm.columnconfigure(1, weight=1)

    # -------------------- Вкладка "Конвертация" --------------------
    def _build_tab_convert(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Формат вывода:").grid(row=0, column=0, sticky="w")
        self.var_fmt = tk.StringVar(value="mp4")
        ttk.Combobox(frm, textvariable=self.var_fmt, values=["mp4","mkv","mov","webm","avi"], state="readonly", width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Профиль качества:").grid(row=1, column=0, sticky="w")
        self.var_quality = tk.StringVar(value="medium")
        ttk.Combobox(frm, textvariable=self.var_quality, values=["original","large","medium","small"], state="readonly", width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Разрешение:").grid(row=2, column=0, sticky="w")
        self.var_scale = tk.StringVar(value="keep")
        ttk.Combobox(frm, textvariable=self.var_scale, values=["keep","2160p","1440p","1080p","720p","480p"], state="readonly", width=10).grid(row=2, column=1, sticky="w")

        ttk.Button(frm, text="Конвертировать", command=self._convert_now).grid(row=3, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Ремакс (без перекодирования)", command=self._remux_now).grid(row=3, column=1, sticky="w", pady=6)

    # -------------------- Вкладка "Автомонтаж" --------------------
    def _build_tab_automontage(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Авто-вырезка пауз/статичных моментов").grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(frm, text="Режим:").grid(row=1, column=0, sticky="w")
        self.var_am_mode = tk.StringVar(value="both")
        ttk.Combobox(frm, textvariable=self.var_am_mode, values=["audio","video","both"], state="readonly", width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Порог тишины (дБ, напр. -35):").grid(row=2, column=0, sticky="w")
        self.var_am_db = tk.StringVar(value="-35")
        ttk.Entry(frm, textvariable=self.var_am_db, width=8).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Порог застывшего кадра (freezedetect, t):").grid(row=3, column=0, sticky="w")
        self.var_am_freeze_t = tk.StringVar(value="2.0")
        ttk.Entry(frm, textvariable=self.var_am_freeze_t, width=8).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Мин. длительность паузы (сек):").grid(row=4, column=0, sticky="w")
        self.var_am_minlen = tk.StringVar(value="1.0")
        ttk.Entry(frm, textvariable=self.var_am_minlen, width=8).grid(row=4, column=1, sticky="w")

        ttk.Label(frm, text="Запас до/после (сек):").grid(row=5, column=0, sticky="w")
        self.var_am_pad = tk.StringVar(value="0.2")
        ttk.Entry(frm, textvariable=self.var_am_pad, width=8).grid(row=5, column=1, sticky="w")

        ttk.Button(frm, text="Проанализировать", command=self._analyze_automontage).grid(row=6, column=0, sticky="w", pady=6)
        ttk.Button(frm, text="Вырезать найденные паузы", command=lambda: self._apply_automontage(mode="cut")).grid(row=6, column=1, sticky="w", pady=6)
        ttk.Button(frm, text="Сжать paузы (ускорить)", command=lambda: self._apply_automontage(mode="compress")).grid(row=6, column=2, sticky="w", pady=6)

        # Список сегментов (предпросмотр)
        self.txt_segments = tk.Text(frm, height=10, width=100)
        self.txt_segments.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=6)
        frm.rowconfigure(7, weight=1)
        frm.columnconfigure(3, weight=1)

    # -------------------- Вкладка "Очередь/Статус" --------------------
    def _build_tab_queue(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Очередь задач (выполняются по очереди)").pack(anchor="w")
        self.lst_queue = tk.Listbox(frm, height=10)
        self.lst_queue.pack(fill="both", expand=True, pady=4)

        self.var_progress = tk.StringVar(value="Готово")
        ttk.Label(frm, textvariable=self.var_progress).pack(anchor="w")

        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="Запустить очередь", command=self._run_queue).pack(side="left")
        ttk.Button(btns, text="Открыть папку вывода", command=self._open_outdir).pack(side="left", padx=6)
        ttk.Button(btns, text="Сохранить пресет настроек...", command=self._save_preset).pack(side="left", padx=6)
        ttk.Button(btns, text="Загрузить пресет...", command=self._load_preset).pack(side="left", padx=6)

    # -------------------- Обработчики --------------------
    def _choose_video(self):
        path = filedialog.askopenfilename(title="Выберите видео", filetypes=[("Видео", "*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.mpg *.mpeg *.ts *.mts *.m2ts"), ("Все файлы","*.*")])
        if not path:
            return
        self.state["video_path"] = path
        self.var_video.set(path)
        # Узнаем длительность через ffprobe
        dur = ffprobe_info.get_duration(self.var_ffprobe.get() or "ffprobe", path)
        self.state["duration"] = dur or 0.0
        messagebox.showinfo("Видео выбрано", f"Файл: {path}\nДлительность: {utils.sec_to_hhmmss(self.state['duration'])}")
        # Очистим ленту, если была
        self._clear_timeline()

    def _choose_outdir(self):
        d = filedialog.askdirectory(title="Выберите папку вывода", initialdir=self.state["output_dir"])
        if d:
            self.state["output_dir"] = d
            self.var_outdir.set(d)

    def _choose_logo(self):
        p = filedialog.askopenfilename(title="Выберите PNG логотип", filetypes=[("PNG изображения","*.png")])
        if p:
            self.var_logo_path.set(p)

    def _open_outdir(self):
        utils.open_folder(self.state["output_dir"])

    def _auto_find_bin(self, name):
        p = utils.which(name)
        if p:
            if name == "ffmpeg": self.var_ffmpeg.set(p)
            if name == "ffprobe": self.var_ffprobe.set(p)
            if name == "ffplay": self.var_ffplay.set(p)
            messagebox.showinfo("Найдено", f"{name}: {p}")
        else:
            messagebox.showwarning("Не найдено", f"{name} не найден в PATH")

    def _check_bins(self):
        ffmpeg_ok = utils.check_bin(self.var_ffmpeg.get() or "ffmpeg", "-version")
        ffprobe_ok = utils.check_bin(self.var_ffprobe.get() or "ffprobe", "-version")
        ffplay_ok = utils.check_bin(self.var_ffplay.get() or "ffplay", "-version")
        messagebox.showinfo("Проверка", f"ffmpeg: {'OK' if ffmpeg_ok else 'нет'}\nffprobe: {'OK' if ffprobe_ok else 'нет'}\nffplay: {'OK' if ffplay_ok else 'нет'}")

    def _open_player(self):
        if not self.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео на вкладке 'Файлы'")
            return
        player_control.open_player(self.var_ffplay.get() or "ffplay", self.state["video_path"], start_sec=utils.hhmmss_to_sec(self.var_goto.get()))

    def _seek_rel(self, delta):
        # Реализуем как "переоткрыть плеер со смещением"
        cur = utils.hhmmss_to_sec(self.var_goto.get())
        cur = max(0.0, cur + delta)
        self.var_goto.set(utils.sec_to_mmss(cur))
        self._open_player()

    def _seek_abs(self):
        self._open_player()

    def _gen_timeline(self):
        if not self.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео")
            return
        # Очистим предыдущую ленту
        self._clear_timeline()
        # Создадим временную папку под превьюшки
        tmpdir = tempfile.mkdtemp(prefix="timeline_")
        self.state["timeline_cache"] = tmpdir

        # Генерация миниатюр в фоне
        def worker():
            ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
            count = thumbs_timeline.generate_thumbs_per_second(ffmpeg, self.state["video_path"], tmpdir, self.state["duration"])
            self.msg_queue.put(("timeline_ready", {"dir": tmpdir, "count": count}))

        threading.Thread(target=worker, daemon=True).start()
        self.var_progress.set("Генерация ленты миниатюр...")

    def _clear_timeline(self):
        # Удаляем все виджеты из timeline_frame
        for w in list(self.timeline_frame.children.values()):
            w.destroy()
        self._thumb_images.clear()
        self.state["selected_thumbs"].clear()
        self.timeline_canvas.configure(scrollregion=(0,0,0,0))

    def _build_timeline_ui(self, tmpdir, count):
        # На каждую секунду создаем маленький фрейм с картинкой и чекбоксом
        for sec in range(int(count)):
            fr = ttk.Frame(self.timeline_frame, padding=3)
            fr.grid(row=0, column=sec, sticky="n")
            img_path = os.path.join(tmpdir, f"thumb_{sec:06d}.png")
            try:
                img = PhotoImage(file=img_path)  # PNG поддерживается в Tk 8.6+
            except Exception:
                img = None
            if img:
                self._thumb_images.append(img)  # храним ссылку, чтобы не собрал GC
                lbl = ttk.Label(fr, image=img)
            else:
                lbl = ttk.Label(fr, text=f"{sec}s", background="#222", foreground="#fff", width=16)
            lbl.pack()
            var_chk = tk.BooleanVar(value=False)
            def make_cb_callback(s=sec, v=var_chk):
                return lambda: self._on_thumb_check(s, v.get())
            cb = ttk.Checkbutton(fr, text=utils.sec_to_mmss(sec), variable=var_chk, command=make_cb_callback())
            cb.pack()

        # Обновляем область прокрутки
        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))
        self.var_progress.set("Лента миниатюр готова")

    def _on_thumb_check(self, sec, is_checked):
        if is_checked:
            self.state["selected_thumbs"].add(sec)
        else:
            self.state["selected_thumbs"].discard(sec)

    def _save_selected_screens(self):
        if not self.state["selected_thumbs"]:
            messagebox.showinfo("Скриншоты", "Не выбраны кадры для сохранения")
            return
        outdir = self.state["output_dir"]
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        base = os.path.splitext(os.path.basename(self.state["video_path"]))[0]
        # Сохраняем каждый выбранный кадр
        def worker():
            for sec in sorted(self.state["selected_thumbs"]):
                out = os.path.join(outdir, f"{base}_{utils.sec_to_hhmmss(sec).replace(':','-')}.png")
                thumbs_timeline.save_frame(ffmpeg, self.state["video_path"], sec, out)
            self.msg_queue.put(("info", "Скриншоты сохранены"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Фрагменты --------------------
    def _delete_fragment(self):
        self._fragment_action(action="delete")

    def _save_fragment(self):
        self._fragment_action(action="extract")

    def _fragment_action(self, action):
        if not self.state["video_path"]:
            messagebox.showwarning("Нет видео", "Сначала выберите видео")
            return
        start = utils.hhmmss_to_sec(self.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.var_frag_end.get())
        if end <= start:
            messagebox.showwarning("Ошибка", "Конец должен быть больше начала")
            return
        fast = (self.var_cut_mode.get() == "fast")
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            if action == "delete":
                out = fragment_ops.delete_fragment(ffmpeg, self.state["video_path"], start, end, outdir, fast=fast)
            else:
                out = fragment_ops.extract_fragment(ffmpeg, self.state["video_path"], start, end, outdir, fast=fast)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Аудио --------------------
    def _remove_audio_all(self):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.remove_audio_all(ffmpeg, self.state["video_path"], outdir)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _mute_audio_fragment(self):
        if not self.state["video_path"]:
            return
        start = utils.hhmmss_to_sec(self.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.var_frag_end.get())
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.mute_audio_fragment(ffmpeg, self.state["video_path"], start, end, outdir)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _replace_audio_from_file(self):
        if not self.state["video_path"]:
            return
        aud = filedialog.askopenfilename(title="Выберите аудиофайл", filetypes=[("Аудио","*.wav *.mp3 *.aac *.m4a *.flac *.ogg"), ("Все файлы","*.*")])
        if not aud:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.replace_audio_full(ffmpeg, self.state["video_path"], aud, outdir)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _replace_audio_from_mic(self):
        if not self.state["video_path"]:
            return
        # Простая запись: спросим длительность записи = длительности видео
        dur = max(1, int(self.state["duration"] or 5))
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.replace_audio_from_mic(ffmpeg, self.state["video_path"], outdir, dur_sec=dur)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _mix_audio_from_file(self):
        if not self.state["video_path"]:
            return
        aud = filedialog.askopenfilename(title="Выберите аудиофайл (оверлей)", filetypes=[("Аудио","*.wav *.mp3 *.aac *.m4a *.flac *.ogg"), ("Все файлы","*.*")])
        if not aud:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.mix_audio_overlay(ffmpeg, self.state["video_path"], aud, outdir)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _normalize_audio(self, mode="fast"):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = audio_ops.normalize_audio(ffmpeg, self.state["video_path"], outdir, mode=mode)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Шумоподавление --------------------
    def _denoise_all(self):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        preset = self.var_dn_preset.get()
        def worker():
            out = denoise.apply_denoise(ffmpeg, self.state["video_path"], outdir, preset=preset, scope="all")
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _denoise_fragment(self):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        preset = self.var_dn_preset.get()
        start = utils.hhmmss_to_sec(self.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.var_frag_end.get())
        def worker():
            out = denoise.apply_denoise(ffmpeg, self.state["video_path"], outdir, preset=preset, scope="fragment", start=start, end=end)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Скорость --------------------
    def _apply_speed(self, scope="all"):
        if not self.state["video_path"]:
            return
        try:
            factor = float(self.var_speed.get())
            if factor <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Ошибка", "Введите корректный коэффициент скорости (>0)")
            return
        pitch = self.var_pitch.get()  # 'preserve' or 'change'
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        start = utils.hhmmss_to_sec(self.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.var_frag_end.get())
        def worker():
            out = speed_ops.apply_speed(ffmpeg, self.state["video_path"], outdir, factor=factor, pitch_mode=pitch, scope=scope, start=start, end=end)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Логотип --------------------
    def _apply_logo_all(self):
        if not self.state["video_path"] or not self.var_logo_path.get():
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = logo_overlay.apply_logo(ffmpeg, self.state["video_path"], outdir, self.var_logo_path.get(), self.var_logo_pos.get(), int(self.var_logo_scale.get() or "10"), scope="all")
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_logo_fragment(self):
        if not self.state["video_path"] or not self.var_logo_path.get():
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        start = utils.hhmmss_to_sec(self.var_frag_start.get())
        end = utils.hhmmss_to_sec(self.var_frag_end.get())
        def worker():
            out = logo_overlay.apply_logo(ffmpeg, self.state["video_path"], outdir, self.var_logo_path.get(), self.var_logo_pos.get(), int(self.var_logo_scale.get() or "10"), scope="fragment", start=start, end=end)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Конвертация --------------------
    def _convert_now(self):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = convert_ops.convert_video(ffmpeg, self.state["video_path"], outdir, fmt=self.var_fmt.get(), quality=self.var_quality.get(), scale=self.var_scale.get())
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    def _remux_now(self):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        def worker():
            out = convert_ops.remux_video(ffmpeg, self.state["video_path"], outdir, fmt=self.var_fmt.get())
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Автомонтаж --------------------
    def _analyze_automontage(self):
        if not self.state["video_path"]:
            return
        mode = self.var_am_mode.get()
        silence_db = float(self.var_am_db.get() or -35)
        freeze_t = float(self.var_am_freeze_t.get() or 2.0)
        minlen = float(self.var_am_minlen.get() or 1.0)
        pad = float(self.var_am_pad.get() or 0.2)
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"

        def worker():
            segs = automontage.analyze(ffmpeg, self.state["video_path"], mode=mode, silence_db=silence_db, freeze_t=freeze_t, minlen=minlen, pad=pad)
            self.msg_queue.put(("am_segments", segs))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_automontage(self, mode="cut"):
        if not self.state["video_path"]:
            return
        ffmpeg = self.var_ffmpeg.get() or "ffmpeg"
        outdir = self.state["output_dir"]
        text = self.txt_segments.get("1.0", "end").strip()
        segs = automontage.parse_segments_text(text)
        if not segs:
            messagebox.showwarning("Нет сегментов", "Сначала выполните анализ и убедитесь, что список сегментов непустой.")
            return

        def worker():
            out = automontage.apply(ffmpeg, self.state["video_path"], segs, outdir, mode=mode)
            self.msg_queue.put(("info", f"Готово: {out}"))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------- Очередь и пресеты --------------------
    def _run_queue(self):
        # Пример базового запуска задачи: можно расширить под реальную очередь
        messagebox.showinfo("Очередь", "Демонстрационная очередь: текущие кнопки запускают задачи сразу. Расширим при необходимости.")

    def _save_preset(self):
        cfg = presets.collect(self)
        path = filedialog.asksaveasfilename(title="Сохранить пресет", defaultextension=".json", filetypes=[("JSON","*.json")])
        if path:
            presets.save(cfg, path)
            messagebox.showinfo("Пресет", f"Сохранено: {path}")

    def _load_preset(self):
        path = filedialog.askopenfilename(title="Загрузить пресет", filetypes=[("JSON","*.json")])
        if path:
            cfg = presets.load(path)
            presets.apply_to_ui(self, cfg)

    # -------------------- Сообщения от фоновых потоков --------------------
    def _poll_msgs(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "timeline_ready":
                    self._build_timeline_ui(payload["dir"], payload["count"])
                elif kind == "info":
                    messagebox.showinfo("Инфо", str(payload))
                elif kind == "am_segments":
                    # Выведем сегменты в текстовое поле
                    self.txt_segments.delete("1.0", "end")
                    for a,b in payload:
                        self.txt_segments.insert("end", f"{utils.sec_to_hhmmss(a)} - {utils.sec_to_hhmmss(b)}\n")
                    messagebox.showinfo("Анализ", f"Найдено сегментов: {len(payload)}")
        except queue.Empty:
            pass
        self.after(150, self._poll_msgs)


def main():
    app = App_UI()
    app.mainloop()


if __name__ == "__main__":
    main()
