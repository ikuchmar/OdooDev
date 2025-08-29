# -*- coding: utf-8 -*-
"""
tools/ui_app_fragment.py — вкладка "Фрагменты" с редактируемой таблицей

Совместимость:
- Импорт: from .ui_app_fragment import UITabFragment
- Конструктор: UITabFragment(app, parent_frame)

Новое:
- Редактирование прямо в таблице (двойной клик по ячейке):
  * Начинается редактирование, появляется Entry над ячейкой.
  * Enter — сохранить, Esc — отмена, также сохраняем при потере фокуса.
  * Значения валидируются как числа (float >= 0). Для пары (start, end) обеспечиваем start <= end.
- Горячие клавиши: Insert — добавить строку; Delete — удалить выделенные.
- Кнопки: Добавить, Авто‑фрагменты (шаг сек), Экспорт всех фрагментов в файлы.
- Воспроизведение: Пуск / Стоп / Перейти.
- Позиционная шкала: авто‑длительность через ffprobe, перемотка, автообновление.

Интеграция:
- Путь к видео: state["video_path"] -> tabs["files"].var_path.get() -> var_video_path.get()
- Папка вывода: state["output_dir"] -> (var_output_dir/var_out_dir/var_output/var_outpath/var_outdir/var_save_dir)
  на вкладке "Файлы" -> app.var_output_dir
- Пути к ffmpeg/ffprobe/ffplay: app.var_ffmpeg/var_ffprobe/var_ffplay или "ffmpeg"/"ffprobe"/"ffplay" из PATH.
"""

import os
import json
import time
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


# ------------------------- Утилиты -------------------------

def _safe_get(obj, path, default=None):
    cur = obj
    for key in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key, None)
            continue
        if hasattr(cur, key):
            cur = getattr(cur, key)
            continue
        return default
    return cur if cur is not None else default


def _get_strvar_value(var_like):
    if var_like is not None and hasattr(var_like, "get"):
        try:
            return var_like.get() or ""
        except Exception:
            return ""
    return ""


def _get_video_path_from_app(app):
    st = getattr(app, "state", None)
    if isinstance(st, dict):
        p = st.get("video_path")
        if p:
            return p
    var_path = _safe_get(app, ["tabs", "files", "var_path"])
    p = _get_strvar_value(var_path)
    if p:
        return p
    var_video_path = getattr(app, "var_video_path", None)
    p = _get_strvar_value(var_video_path)
    if p:
        return p
    return ""


def _get_output_dir_from_app(app):
    st = getattr(app, "state", None)
    if isinstance(st, dict):
        outp = st.get("output_dir")
        if outp:
            return outp
    files_tab = _safe_get(app, ["tabs", "files"])
    candidate_names = ["var_output_dir", "var_out_dir", "var_output", "var_outpath", "var_outdir", "var_save_dir"]
    for name in candidate_names:
        var = getattr(files_tab, name, None) if files_tab else None
        val = _get_strvar_value(var)
        if val:
            return val
    var_output_dir = getattr(app, "var_output_dir", None)
    val = _get_strvar_value(var_output_dir)
    if val:
        return val
    return ""


def _get_ffprobe_cmd(app):
    val = _get_strvar_value(getattr(app, "var_ffprobe", None)).strip()
    return val or "ffprobe"


def _get_ffplay_cmd(app):
    val = _get_strvar_value(getattr(app, "var_ffplay", None)).strip()
    return val or "ffplay"


def _get_ffmpeg_cmd(app):
    val = _get_strvar_value(getattr(app, "var_ffmpeg", None)).strip()
    return val or "ffmpeg"


def _probe_duration_seconds(ffprobe_cmd, path):
    if not path or not os.path.exists(path):
        return 0.0
    try:
        cmd = [ffprobe_cmd, "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return 0.0
        data = json.loads(proc.stdout or "{}")
        dur = float(data.get("format", {}).get("duration", 0.0) or 0.0)
        return max(0.0, dur)
    except Exception:
        return 0.0


def _fmt_time(sec):
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ---------------------- Класс вкладки ----------------------

class UITabFragment(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent)
        self.app = app

        # Состояние проигрывания
        self._ffplay_proc = None
        self._playing = False
        self._duration = 0.0
        self._position = 0.0
        self._tick_period = 0.2
        self._scale_dragging = False

        # ==== Таблица интервалов ====
        self.tree = ttk.Treeview(self, columns=("start", "end"), show="headings", height=12)
        self.tree.heading("start", text="Начало (сек)")
        self.tree.heading("end", text="Конец (сек)")
        self.tree.column("start", width=120, anchor="center")
        self.tree.column("end", width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        # Редактирование в таблице (Entry поверх ячейки)
        self._editor = None   # tk.Entry
        self._edit_item = ""  # id строки
        self._edit_col = ""   # "#1" или "#2"

        # Биндинги для редактирования
        self.tree.bind("<Double-1>", self._on_tree_dblclick)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")  # убрать редактор при клике вне
        self.tree.bind("<Key-Insert>", lambda e: self._act_add_row())
        self.tree.bind("<Delete>", lambda e: self._act_delete_selected())

        # ==== Кнопки действий со списком ====
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(bar, text="Добавить", command=self._act_add_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Авто‑фрагменты (шаг сек)", command=self._act_autosplit).pack(side=tk.LEFT, padx=2)

        ttk.Button(bar, text="Удалить выделенные", command=self._act_delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Очистить список", command=self._act_clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Склеить пересекающиеся", command=self._act_merge_overlaps).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Посмотреть фрагмент", command=self._act_preview_fragment).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Удалить фрагменты - оставить остальное", command=self._act_cut_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Сохранить только фрагменты (склейка)", command=self._act_save_only_fragments).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Сохранить фрагменты в файлы", command=self._act_export_all_fragments).pack(side=tk.LEFT, padx=2)

        # ==== Панель управления воспроизведением ====
        play = ttk.Frame(self)
        play.pack(fill=tk.X)

        self.lbl_time = ttk.Label(play, text="00:00 / 00:00")
        self.lbl_time.pack(side=tk.RIGHT, padx=(8, 0))

        self.scale_var = tk.DoubleVar(value=0.0)
        self.scale = ttk.Scale(play, from_=0.0, to=100.0, orient="horizontal",
                               variable=self.scale_var, command=self._on_scale_move)
        self.scale.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(4, 8))

        ttk.Button(play, text="Пуск", command=self._act_play).pack(side=tk.LEFT, padx=2)
        ttk.Button(play, text="Стоп", command=self._act_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(play, text="Перейти", command=self._act_goto_fragment).pack(side=tk.LEFT, padx=2)

        # События шкалы
        self.scale.bind("<Button-1>", self._on_scale_press, add="+")
        self.scale.bind("<ButtonRelease-1>", self._on_scale_release, add="+")

        # Инициализация длительности по текущему файлу
        self._refresh_duration()

        # Отрисовать фрейм вкладки
        self.pack(fill=tk.BOTH, expand=True)

    # ------ Получение путей/длительности ------
    def _get_video_path(self):
        return _get_video_path_from_app(self.app)

    def _get_output_dir(self):
        return _get_output_dir_from_app(self.app)

    def _ffprobe_cmd(self):
        return _get_ffprobe_cmd(self.app)

    def _ffplay_cmd(self):
        return _get_ffplay_cmd(self.app)

    def _ffmpeg_cmd(self):
        return _get_ffmpeg_cmd(self.app)

    def _refresh_duration(self):
        path = self._get_video_path()
        dur = _probe_duration_seconds(self._ffprobe_cmd(), path)
        self._duration = float(dur) if dur > 0 else 0.0
        if self._duration > 0:
            self.scale.configure(from_=0.0, to=self._duration)
            if self._position > self._duration:
                self._position = self._duration
            self.scale_var.set(self._position)
            self.lbl_time.configure(text=f"{_fmt_time(self._position)} / {_fmt_time(self._duration)}")
        else:
            self.scale.configure(from_=0.0, to=100.0)
            self._position = 0.0
            self.scale_var.set(0.0)
            self.lbl_time.configure(text="00:00 / 00:00")

    # ------ Редактирование в таблице ------
    def _close_editor(self, save=False):
        """Закрыть редактор; если save=True — записать значение в ячейку."""
        if not self._editor:
            return
        entry = self._editor
        item = self._edit_item
        col = self._edit_col
        self._editor = None
        self._edit_item = ""
        self._edit_col = ""

        if save and item and col:
            new_text = entry.get().strip()
            # Валидация float >= 0
            try:
                val = float(new_text.replace(",", "."))
                if val < 0:
                    raise ValueError
            except Exception:
                messagebox.showwarning("Ошибка ввода", "Нужно указать неотрицательное число (секунды).")
                entry.destroy()
                return

            # Получаем текущее значение пары (start, end)
            vals = list(self.tree.item(item, "values"))
            idx = 0 if col in ("#1", "start") else 1
            vals[idx] = val

            # Нормализация пары: start <= end
            try:
                st = float(vals[0])
                en = float(vals[1])
                if en < st:
                    st, en = en, st
                    vals[0], vals[1] = st, en
            except Exception:
                pass

            self.tree.item(item, values=(float(vals[0]), float(vals[1])))

        entry.destroy()

    def _start_cell_edit(self, item, col):
        """Начать редактирование указанной ячейки (item, col="#1"|"#2")."""
        # Закрываем предыдущий редактор, если есть
        self._close_editor(save=True)

        # Геометрия ячейки
        bbox = self.tree.bbox(item, col)
        if not bbox:
            return
        x, y, w, h = bbox

        # Текущее значение
        cur_vals = self.tree.item(item, "values")
        cur_text = str(cur_vals[0 if col == "#1" else 1])

        # Создаем Entry поверх нужной области
        editor = tk.Entry(self.tree)
        editor.insert(0, cur_text)
        editor.select_range(0, tk.END)
        editor.focus_set()
        editor.place(x=x, y=y, width=w, height=h)

        # Сохраняем ссылки
        self._editor = editor
        self._edit_item = item
        self._edit_col = col

        # Биндинги редактора
        editor.bind("<Return>", lambda e: self._close_editor(save=True))
        editor.bind("<Escape>", lambda e: self._close_editor(save=False))
        editor.bind("<FocusOut>", lambda e: self._close_editor(save=True))

    def _on_tree_dblclick(self, event):
        """Двойной клик — начать редактирование ячейки."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)  # "#1", "#2", ...
        if not item or col not in ("#1", "#2"):
            return
        self._start_cell_edit(item, col)

    def _on_tree_click(self, _event):
        """Клик вне — закрыть редактор (с сохранением)."""
        if self._editor:
            self._close_editor(save=True)

    # ------ Операции со списком ------
    def _act_add_row(self):
        """Быстро добавить строку и сразу открыть редактирование начала."""
        st = 0.0
        en = min(1.0, self._duration) if self._duration > 0 else 1.0
        item = self.tree.insert("", tk.END, values=(st, en))
        # Встать в редактирование start
        self.tree.see(item)
        self.tree.selection_set(item)
        self.after(50, lambda: self._start_cell_edit(item, "#1"))

    def _act_autosplit(self):
        """Автозаполнение фрагментов по всему видео с заданным шагом (сек)."""
        if self._duration <= 0:
            self._refresh_duration()
        if self._duration <= 0:
            messagebox.showwarning("Ошибка", "Не удалось определить длительность видео.")
            return
        step = simpledialog.askfloat("Авто‑фрагменты", "Шаг (сек):", minvalue=0.1, initialvalue=5.0)
        if step is None:
            return
        if step <= 0:
            messagebox.showwarning("Ошибка", "Шаг должен быть больше 0.")
            return

        t = 0.0
        added = 0
        while t < self._duration:
            start = t
            end = min(t + step, self._duration)
            self.tree.insert("", tk.END, values=(round(start, 3), round(end, 3)))
            added += 1
            t += step

        messagebox.showinfo("Готово", f"Добавлено фрагментов: {added}")

    def _act_delete_selected(self):
        if self._editor:
            self._close_editor(save=True)
        for item in self.tree.selection():
            self.tree.delete(item)

    def _act_clear_all(self):
        if self._editor:
            self._close_editor(save=True)
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _act_merge_overlaps(self):
        """Сортировка и склейка пересекающихся интервалов."""
        if self._editor:
            self._close_editor(save=True)
        intervals = []
        for row in self.tree.get_children():
            start = float(self.tree.item(row, "values")[0])
            end = float(self.tree.item(row, "values")[1])
            if end < start:
                start, end = end, start
            intervals.append((start, end))

        intervals.sort(key=lambda x: x[0])
        merged = []
        for st, en in intervals:
            if not merged or merged[-1][1] < st:
                merged.append([st, en])
            else:
                merged[-1][1] = max(merged[-1][1], en)

        self._act_clear_all()
        for st, en in merged:
            self.tree.insert("", tk.END, values=(st, en))

    def _act_preview_fragment(self):
        path = self._get_video_path()
        if not path:
            messagebox.showwarning("Ошибка", "Сначала выберите видеофайл.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Ошибка", "Не выбран фрагмент.")
            return
        start, end = self.tree.item(sel[0], "values")
        start = float(start)
        dur = max(0.0, float(end) - start)
        if dur <= 0:
            messagebox.showwarning("Внимание", "Длительность фрагмента равна 0.")
            return
        self._play_with_ffplay(start=start, duration=dur)

    def _act_cut_out(self):
        messagebox.showinfo("Инфо", "Заглушка: вырезать указанные фрагменты (оставить остальное).")

    def _act_save_only_fragments(self):
        messagebox.showinfo("Инфо", "Заглушка: сохранить только указанные фрагменты (склейка).")

    def _act_export_all_fragments(self):
        """
        Сохранить каждый фрагмент в отдельный файл:
        ffmpeg -y -ss START -i INPUT -t DURATION -c copy OUTPUT
        """
        if self._editor:
            self._close_editor(save=True)

        input_path = self._get_video_path()
        if not input_path:
            messagebox.showwarning("Ошибка", "Сначала выберите видеофайл.")
            return
        if not os.path.exists(input_path):
            messagebox.showwarning("Ошибка", "Файл видео не найден.")
            return

        out_dir = self._get_output_dir()
        if not out_dir:
            messagebox.showwarning("Ошибка", "Не задана папка вывода (см. вкладку «Файлы»).")
            return
        os.makedirs(out_dir, exist_ok=True)

        rows = self.tree.get_children()
        if not rows:
            messagebox.showwarning("Внимание", "Список фрагментов пуст.")
            return

        ffmpeg_cmd = self._ffmpeg_cmd()
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        src_ext = os.path.splitext(input_path)[1] or ".mp4"

        exported, errors = 0, []
        for idx, row in enumerate(rows, start=1):
            start, end = self.tree.item(row, "values")
            try:
                start = float(start)
                end = float(end)
            except Exception:
                errors.append(f"#{idx}: некорректные значения (не числа)")
                continue
            if end < start:
                start, end = end, start
            duration = max(0.0, end - start)
            if duration <= 0:
                errors.append(f"#{idx}: нулевая длительность")
                continue

            out_name = f"{base_name}_part{idx:03d}_{int(round(start))}-{int(round(end))}{src_ext}"
            out_path = os.path.join(out_dir, out_name)

            cmd = [
                ffmpeg_cmd,
                "-y",
                "-hide_banner", "-loglevel", "error",
                "-ss", f"{start}",
                "-i", input_path,
                "-t", f"{duration}",
                "-c", "copy",
                out_path,
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode != 0:
                    errors.append(f"#{idx}: {proc.stderr.strip() or 'ffmpeg error'}")
                else:
                    exported += 1
            except FileNotFoundError:
                messagebox.showerror(
                    "Ошибка",
                    "Не найден ffmpeg.\nУстановите FFmpeg и добавьте в PATH\nили укажите путь в настройках."
                )
                return
            except Exception as e:
                errors.append(f"#{idx}: {e}")

        if errors:
            messagebox.showwarning("Готово с ошибками",
                                   f"Экспортировано: {exported}\nОшибки:\n" + "\n".join(errors[:10]))
        else:
            messagebox.showinfo("Готово", f"Экспортировано файлов: {exported}\nПапка: {out_dir}")

    # ------ Воспроизведение ------
    def _act_play(self):
        path = self._get_video_path()
        if not path:
            messagebox.showwarning("Ошибка", "Сначала выберите видеофайл.")
            return
        start = float(self.scale_var.get()) if self._duration > 0 else 0.0
        self._play_with_ffplay(start=start)

    def _act_stop(self):
        self._stop_ffplay()

    def _act_goto_fragment(self):
        path = self._get_video_path()
        if not path:
            messagebox.showwarning("Ошибка", "Сначала выберите видеофайл.")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Ошибка", "Не выбран фрагмент.")
            return
        start, _end = self.tree.item(sel[0], "values")
        try:
            start = float(start)
        except Exception:
            messagebox.showwarning("Ошибка", "Неверное значение начала фрагмента.")
            return
        self._play_with_ffplay(start=start)

    def _play_with_ffplay(self, start=0.0, duration=None):
        self._stop_ffplay()
        cmd = [self._ffplay_cmd(), "-autoexit", "-ss", str(max(0.0, float(start)))]
        if duration is not None and duration > 0:
            cmd += ["-t", str(float(duration))]
        cmd.append(self._get_video_path())
        try:
            self._ffplay_proc = subprocess.Popen(cmd)
        except FileNotFoundError:
            messagebox.showerror(
                "Ошибка",
                "Не найден ffplay.\nУстановите FFmpeg и добавьте в PATH\nили укажите путь в настройках."
            )
            self._ffplay_proc = None
            return
        self._playing = True
        self._position = max(0.0, float(start))
        self._refresh_duration()
        threading.Thread(target=self._tick_worker, daemon=True).start()

    def _stop_ffplay(self):
        self._playing = False
        if self._ffplay_proc and self._ffplay_proc.poll() is None:
            try:
                self._ffplay_proc.terminate()
            except Exception:
                pass
        self._ffplay_proc = None

    # ------ Позиционная шкала ------
    def _tick_worker(self):
        last = time.time()
        while self._playing and self._ffplay_proc and self._ffplay_proc.poll() is None:
            time.sleep(self._tick_period)
            now = time.time()
            dt = now - last
            last = now
            if not self._scale_dragging:
                self._position += dt
                if self._duration > 0 and self._position > self._duration:
                    self._position = self._duration
                self.after(0, self._sync_scale_and_label)
        self.after(0, self._sync_scale_and_label)

    def _sync_scale_and_label(self):
        try:
            self.scale_var.set(self._position)
        except tk.TclError:
            pass
        total = self._duration if self._duration > 0 else 0.0
        self.lbl_time.configure(text=f"{_fmt_time(self._position)} / {_fmt_time(total)}")

    def _on_scale_press(self, _event):
        self._scale_dragging = True

    def _on_scale_release(self, _event):
        self._scale_dragging = False
        new_pos = float(self.scale_var.get())
        if self._playing:
            self._play_with_ffplay(start=new_pos)
        else:
            self._position = new_pos
            self._sync_scale_and_label()

    def _on_scale_move(self, _value):
        if self._scale_dragging:
            self._position = float(self.scale_var.get())
            self._sync_scale_and_label()
