# video_editor/tools/ui_app_view.py
# -*- coding: utf-8 -*-
"""
Вкладка «Видео»
- ОДНА кнопка «Сгенерировать (лента+миниатюры)»
- Миниатюры раскладываются ПО ВРЕМЕНИ (x = t / sec_per_px)
- ЛКМ по ленте/миниатюре/шкале — переход к времени + предпросмотр (force)
- Подсветка ближайшей миниатюры + автопрокрутка корректна
- Всегда видна временная шкала (сек/мин) под миниатюрами
"""

import os, json, time, math, threading, tempfile, subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import utils
from . import config_store as cfg


class UITabView:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # размеры/ограничения ленты
        self._timeline_height = 130    # компактная лента
        self._MAX_WIDTH = 12000
        self._total_width = 0
        self._sec_per_px = 1.0

        # длительность/позиция
        self._duration_cache = 0.0
        self.var_pos = tk.DoubleVar(value=0.0)

        # проигрывание
        self._play_proc = None
        self._play_started_at = 0.0
        self._play_start_sec = 0.0
        self._play_stop_evt = None

        # прогресс
        self.var_progress = tk.StringVar(value="Лента: 0/0")

        # миниатюры
        self.var_thumb_step = tk.StringVar(value=str(cfg.get_int("view","thumb_step",5)))
        self.var_thumb_h    = tk.StringVar(value=str(cfg.get_int("view","thumb_h",90)))
        self.var_thumb_w    = tk.StringVar(value=str(cfg.get_int("view","thumb_w",140)))
        self._thumb_tempdir = os.path.join(tempfile.gettempdir(),"video_editor_thumbs")
        self._thumb_items   = []     # id canvas-элементов (png/рамки/делители)
        self._thumb_images  = []     # ссылки на PhotoImage
        self._thumb_paths   = []     # пути временных png
        self._thumb_meta    = []     # [{sec,x_left,w,h,rect_id,img_id}]
        self._sel_thumb_box_id = None

        # предпросмотр (отдельное поле)
        self._last_preview_ts  = 0.0
        self._last_preview_sec = -1.0
        self._preview_img   = None
        self._preview_item  = None
        self._preview_bg    = None

        # ui refs
        self.timeline_canvas = None
        self.timeline_scroll = None
        self._cursor_id = None
        self.preview_canvas = None
        self.scale = None
        self.lbl_pos = None
        self.pb = None

        self._build_ui()

    # ---- внешние утилиты
    def _ffplay_cmd(self):  v=getattr(self.app,"var_ffplay",None);  return (v.get() or "ffplay")  if v else "ffplay"
    def _ffprobe_cmd(self): v=getattr(self.app,"var_ffprobe",None); return (v.get() or "ffprobe") if v else "ffprobe"
    def _ffmpeg_cmd(self):  v=getattr(self.app,"var_ffmpeg",None);  return (v.get() or "ffmpeg")  if v else "ffmpeg"

    # ---- UI
    def _build_ui(self):
        root = ttk.Frame(self.parent, padding=10); root.pack(fill="both", expand=True)

        top = ttk.LabelFrame(root, text="Лента по видео", padding=8); top.pack(fill="x")
        ttk.Button(top, text="Сгенерировать (лента+миниатюры)", command=self._gen_all).pack(side="left")
        ttk.Label(top, textvariable=self.var_progress).pack(side="left", padx=(10,6))
        self.pb = ttk.Progressbar(top, orient="horizontal", mode="determinate", length=240, maximum=100, value=0); self.pb.pack(side="left")

        ttk.Label(top, text="  Шаг (сек):").pack(side="left", padx=(12,2))
        ttk.Entry(top, textvariable=self.var_thumb_step, width=4).pack(side="left")
        ttk.Label(top, text="Высота:").pack(side="left", padx=(10,2))
        ttk.Entry(top, textvariable=self.var_thumb_h, width=4).pack(side="left")
        ttk.Label(top, text="Ширина:").pack(side="left", padx=(10,2))
        ttk.Entry(top, textvariable=self.var_thumb_w, width=5).pack(side="left")

        # лента
        mid = ttk.Frame(root); mid.pack(fill="x", expand=False, pady=(8,6))
        self.timeline_canvas = tk.Canvas(mid, height=self._timeline_height, bg="#202020", highlightthickness=0)
        self.timeline_canvas.pack(side="top", fill="x", expand=False)
        self.timeline_scroll = ttk.Scrollbar(mid, orient="horizontal", command=self.timeline_canvas.xview); self.timeline_scroll.pack(fill="x", side="bottom")
        self.timeline_canvas.configure(xscrollcommand=self.timeline_scroll.set)
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.timeline_canvas.tag_bind("thumb", "<Button-1>", self._on_thumb_left)
        self.timeline_canvas.tag_bind("thumb", "<Button-3>", self._on_thumb_right)

        # предпросмотр
        prev = ttk.LabelFrame(root, text="Предпросмотр кадра (на всю ширину)", padding=6); prev.pack(fill="both", expand=True, pady=(4,8))
        self.preview_canvas = tk.Canvas(prev, height=320, bg="#101010", highlightthickness=0); self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self._render_preview_current(force=True))

        # нижняя панель
        bot = ttk.Frame(root); bot.pack(fill="x")
        ttk.Label(bot, text="Позиция:").pack(side="left")
        self.scale = ttk.Scale(bot, from_=0.0, to=1.0, orient="horizontal", variable=self.var_pos, command=self._on_scale_drag)
        self.scale.pack(side="left", fill="x", expand=True, padx=8)
        self.scale.bind("<Button-1>", self._on_scale_click)
        self.lbl_pos = ttk.Label(bot, text="00:00:00 / 00:00:00"); self.lbl_pos.pack(side="left")
        ttk.Button(bot, text="Сохранить кадр (PNG)", command=self._save_current_frame).pack(side="left", padx=(10,4))
        ttk.Button(bot, text="▶ Пуск", command=self._play).pack(side="left", padx=4)
        ttk.Button(bot, text="⏹ Стоп", command=self._stop).pack(side="left", padx=4)
        ttk.Button(bot, text="⏩ Перейти", command=self._seek).pack(side="left", padx=4)

        root.columnconfigure(0, weight=1)
        self._ensure_duration()
        self._update_pos_label(0.0, self._duration_cache)

    # ---- длительность файла
    def _ensure_duration(self):
        dur = float(self.app.state.get("duration") or 0.0)
        src = self.app.state.get("video_path") or ""
        if dur<=0.0 and src and os.path.isfile(src):
            try:
                out = subprocess.check_output([self._ffprobe_cmd(), "-v","error","-show_format","-of","json", src], stderr=subprocess.STDOUT)
                dur = float((json.loads(out.decode("utf-8","ignore")).get("format") or {}).get("duration", 0.0) or 0.0)
            except Exception:
                dur = 0.0
        self._duration_cache = max(0.0, dur)
        self.scale.configure(from_=0.0, to=self._duration_cache)

    # ---- прогресс/сервис
    def _set_progress(self, done, total):
        total=max(1,int(total)); done=int(done)
        self.var_progress.set(f"Лента/миниатюры: {done}/{total}")
        self.pb["value"]=int(round(done*100.0/total))

    def _clear_timeline(self):
        try: self.timeline_canvas.delete("all")
        except Exception: pass
        self._cursor_id=None
        self._total_width=0
        self._sec_per_px=1.0
        self.timeline_canvas.configure(scrollregion=(0,0,0,self._timeline_height))
        self._clear_thumbs(delete_files=True)
        self._thumb_meta.clear()
        if self._sel_thumb_box_id:
            try: self.timeline_canvas.delete(self._sel_thumb_box_id)
            except Exception: pass
            self._sel_thumb_box_id=None

    # ---- сетка времени
    def _draw_time_grid(self, W:int, H:int):
        # фон
        self.timeline_canvas.create_rectangle(0,0,W,H, fill="#101010", outline="")
        # деления секунд (низ)
        step_sec = max(1, int(round(1.0 / self._sec_per_px)))
        y0, y1 = H-18, H-2
        for s in range(0, int(self._duration_cache)+1, step_sec):
            x = int(round(s / self._sec_per_px))
            self.timeline_canvas.create_line(x, y0, x, y1, fill="#222222")
        # минуты — по всей высоте + подпись
        for m in range(0, int(self._duration_cache//60)+1):
            s = m*60
            x = int(round(s / self._sec_per_px))
            self.timeline_canvas.create_line(x, 0, x, H, fill="#303030")
            self.timeline_canvas.create_text(x+3, 4, anchor="nw", fill="#888",
                                             text=utils.sec_to_hhmmss(s), font=("TkDefaultFont",8))

    # ---- генерация
    def _gen_timeline(self):
        self._ensure_duration()
        if self._duration_cache<=0.0: return
        pps = max(1, cfg.get_int("view","px_per_sec",6))
        width = int(round(self._duration_cache*pps))
        if width>self._MAX_WIDTH:
            width=self._MAX_WIDTH
            pps=max(1, int(round(width/max(1.0,self._duration_cache))))
        self._total_width=max(1,width)
        self._sec_per_px=self._duration_cache/float(self._total_width)

        self.timeline_canvas.configure(scrollregion=(0,0,self._total_width,self._timeline_height))
        self._draw_time_grid(self._total_width, self._timeline_height)

    def _clear_thumbs(self, delete_files=False):
        for it in self._thumb_items:
            try: self.timeline_canvas.delete(it)
            except Exception: pass
        self._thumb_items.clear()
        self._thumb_images.clear()
        if delete_files:
            for p in self._thumb_paths:
                try:
                    if os.path.isfile(p): os.remove(p)
                except Exception: pass
            self._thumb_paths.clear()

    def _gen_thumbs(self):
        src = self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла", "Сначала выберите видео."); return
        if self._total_width<=0:
            self._gen_timeline()
        self._ensure_duration()
        if self._duration_cache<=0.0:
            messagebox.showwarning("Длительность","Неизвестна длительность файла."); return

        try: step=max(1,int(float(self.var_thumb_step.get())))
        except Exception: step=5
        try: th=max(30,min(320,int(float(self.var_thumb_h.get()))))
        except Exception: th=90
        try:
            tw=max(40,min(480,int(float(self.var_thumb_w.get()))))
            if tw%2==1: tw+=1
        except Exception: tw=140

        cfg.set("view","thumb_step",step); cfg.set("view","thumb_h",th); cfg.set("view","thumb_w",tw)

        # высоту ленты под высоту превью
        self._timeline_height = th + 16
        self.timeline_canvas.config(height=self._timeline_height)

        # ограничим количество
        n_est = max(1, int(self._duration_cache//step)+1)
        if n_est>500:
            step=max(step, int(math.ceil(self._duration_cache/500.0)))
            n_est=max(1, int(self._duration_cache//step)+1)

        self._clear_thumbs(delete_files=True)
        self._thumb_meta.clear()
        try: os.makedirs(self._thumb_tempdir, exist_ok=True)
        except Exception: pass

        ffmpeg=self._ffmpeg_cmd()
        self._set_progress(0,n_est)

        def worker():
            done=0; paths=[]
            for i,sec in enumerate(range(0, int(self._duration_cache)+1, step)):
                outp=os.path.join(self._thumb_tempdir, f"thumb_{i:05d}.png")
                cmd=[ffmpeg,"-hide_banner","-loglevel","error","-y",
                     "-ss",str(sec), "-i", src,
                     "-frames:v","1",
                     "-vf", f"scale={tw}:{th}:force_original_aspect_ratio=decrease,"
                            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black",
                     outp]
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    if os.path.isfile(outp): paths.append((float(sec), outp))
                except Exception:
                    pass
                done+=1
                try: self.timeline_canvas.after(0, self._set_progress, done, n_est)
                except Exception: pass

            def on_done():
                # рисуем по ВРЕМЕНИ
                for sec, path in paths:
                    try: img=tk.PhotoImage(file=path)
                    except Exception: continue
                    x_center = int(round(sec / self._sec_per_px))
                    x_left   = max(2, min(x_center - img.width()//2, self._total_width - img.width() - 2))
                    y = 4
                    rect = self.timeline_canvas.create_rectangle(x_left-1, y-1, x_left+img.width()+1, y+img.height()+1,
                                                                 outline="#333", fill="#000",
                                                                 tags=("thumb", f"t={sec}"))
                    it   = self.timeline_canvas.create_image(x_left, y, anchor="nw",
                                                             image=img, tags=("thumb", f"t={sec}"))
                    self._thumb_items.extend([rect,it]); self._thumb_images.append(img); self._thumb_paths.append(path)
                    self._thumb_meta.append({"sec":sec,"x_left":x_left,"w":img.width(),"h":img.height(),
                                             "rect_id":rect,"img_id":it})
                # сетку перерисуем поверх фона, но под миниатюрами — НЕ надо. Мы рисовали ДО миниатюр.
                # курсор и подсветку — сверху
                self._highlight_nearest_thumb(float(self.var_pos.get() or 0.0))
                self._raise_foreground_layers()
                self._set_progress(n_est,n_est)

            try: self.timeline_canvas.after(0, on_done)
            except Exception: pass

        threading.Thread(target=worker, daemon=True).start()

    def _gen_all(self):
        self._clear_timeline()
        if not self.app.state.get("video_path"):
            messagebox.showwarning("Нет файла","Сначала выберите видео."); return
        self._ensure_duration()
        if self._duration_cache<=0.0:
            messagebox.showwarning("Длительность","Неизвестна длительность файла."); return
        self._gen_timeline()
        self._gen_thumbs()

    # ---- подсветка/курсор/переход
    def _raise_foreground_layers(self):
        # курсор и жёлтая рамка должны быть поверх
        if self._cursor_id: self.timeline_canvas.tag_raise(self._cursor_id)
        if self._sel_thumb_box_id: self.timeline_canvas.tag_raise(self._sel_thumb_box_id)

    def _highlight_nearest_thumb(self, sec: float, autoscroll: bool=True):
        if not self._thumb_meta:
            if self._sel_thumb_box_id:
                try: self.timeline_canvas.delete(self._sel_thumb_box_id)
                except Exception: pass
                self._sel_thumb_box_id=None
            return None
        nearest = min(self._thumb_meta, key=lambda m: abs(m["sec"]-sec))
        x, w, h = nearest["x_left"], nearest["w"], nearest["h"]
        y = 4
        if self._sel_thumb_box_id is None:
            self._sel_thumb_box_id = self.timeline_canvas.create_rectangle(x-3,y-3,x+w+3,y+h+3, outline="#ffcc00", width=2)
        else:
            self.timeline_canvas.coords(self._sel_thumb_box_id, x-3,y-3,x+w+3,y+h+3)
        if autoscroll:
            try:
                cw = int(self.timeline_canvas.winfo_width())
                cx = x + w//2
                new_left = max(0, min(cx - cw//2, self._total_width - cw))
                self.timeline_canvas.xview_moveto(new_left/float(max(1,self._total_width)))
            except Exception: pass
        self._raise_foreground_layers()
        return nearest

    def _time_to_x(self, sec: float) -> int:
        if self._total_width<=0: return 0
        return int(round(float(sec)/self._sec_per_px))

    def _x_to_time(self, x: int) -> float:
        if self._total_width<=0: return 0.0
        return max(0.0, min((float(x)+0.5)*self._sec_per_px, self._duration_cache))

    def _draw_cursor(self, x:int):
        x=max(0, min(x, max(0,self._total_width-1)))
        if self._cursor_id is None:
            self._cursor_id = self.timeline_canvas.create_line(x,0,x,self._timeline_height, fill="red", width=2)
        else:
            self.timeline_canvas.coords(self._cursor_id, x,0,x,self._timeline_height)
        self._raise_foreground_layers()

    def _goto_time(self, sec: float, snap: bool=True, force_preview: bool=True):
        if snap and self._thumb_meta:
            near=self._highlight_nearest_thumb(sec, autoscroll=True)
            if near: sec=near["sec"]
        self.var_pos.set(sec)
        self._update_pos_label(sec, self._duration_cache)
        self._draw_cursor(self._time_to_x(sec))
        self._render_preview_at_sec(sec, force=force_preview)

    # ---- клики
    def _on_timeline_click(self, e):
        if self._total_width<=0: return
        x=int(self.timeline_canvas.canvasx(e.x))
        self._goto_time(self._x_to_time(x), snap=True, force_preview=True)

    def _on_thumb_left(self, _e):
        cur=self.timeline_canvas.find_withtag("current")
        if not cur: return
        sec=None
        for t in self.timeline_canvas.gettags(cur[0]) or ():
            if t.startswith("t="):
                try: sec=float(t.split("=",1)[1])
                except Exception: pass
        if sec is None: return
        self._goto_time(sec, snap=False, force_preview=True)

    def _on_thumb_right(self, _e):
        cur=self.timeline_canvas.find_withtag("current")
        if not cur: return
        sec=None
        for t in self.timeline_canvas.gettags(cur[0]) or ():
            if t.startswith("t="):
                try: sec=float(t.split("=",1)[1])
                except Exception: pass
        if sec is None: return
        self._save_frame_at_sec(sec)

    # ---- позиционная шкала
    def _on_scale_click(self, e):
        try:
            w=e.widget.winfo_width()
            a=float(self.scale.cget("from")); b=float(self.scale.cget("to"))
            frac=max(0.0, min(1.0, e.x/max(1,w)))
            val=a+frac*(b-a)
        except Exception:
            return
        self._goto_time(val, snap=True, force_preview=True)

    def _on_scale_drag(self, _val):
        sec=float(self.var_pos.get() or 0.0)
        self._highlight_nearest_thumb(sec, autoscroll=False)
        self._draw_cursor(self._time_to_x(sec))
        self._update_pos_label(sec, self._duration_cache)
        self._render_preview_at_sec(sec, force=False)

    def _update_pos_label(self, cur, total):
        try: total=float(total)
        except Exception: total=0.0
        self.lbl_pos.config(text=f"{utils.sec_to_hhmmss(int(cur))} / {utils.sec_to_hhmmss(int(total))}")

    # ---- предпросмотр
    def _render_preview_current(self, force=False):
        self._render_preview_at_sec(float(self.var_pos.get() or 0.0), force=force)

    def _render_preview_at_sec(self, sec: float, force: bool=False):
        now=time.monotonic()
        if not force:
            if now-self._last_preview_ts<0.2: return
            if abs(sec-self._last_preview_sec)<0.05: return
        self._last_preview_ts=now; self._last_preview_sec=sec

        src=self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src): return

        try:
            self.preview_canvas.update_idletasks()
            W=max(200, int(self.preview_canvas.winfo_width()))
            H=max(120, int(self.preview_canvas.winfo_height()))
        except Exception:
            W,H=800,320

        tmp=os.path.join(tempfile.gettempdir(), f"video_editor_preview_{os.getpid()}.png")
        cmd=[self._ffmpeg_cmd(),"-hide_banner","-loglevel","error","-y",
             "-i",src,"-ss",str(max(0.0,float(sec))),"-frames:v","1",
             "-vf", f"scale={W}:-2:force_original_aspect_ratio=decrease,"
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
             tmp]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            img=tk.PhotoImage(file=tmp)
        except Exception:
            return

        if self._preview_bg is None:
            self._preview_bg=self.preview_canvas.create_rectangle(0,0,W,H, fill="#101010", outline="")
        else:
            self.preview_canvas.coords(self._preview_bg,0,0,W,H)

        if self._preview_item is None:
            self._preview_item=self.preview_canvas.create_image(W//2,H//2, anchor="center", image=img)
        else:
            self.preview_canvas.itemconfigure(self._preview_item, image=img)
            self.preview_canvas.coords(self._preview_item, W//2, H//2)
        self._preview_img=img

    # ---- сохранение кадров
    def _default_frames_dir(self):
        src=self.app.state.get("video_path") or ""
        return os.path.dirname(os.path.abspath(src)) if src else os.getcwd()

    def _save_frame_at_sec(self, sec: float, out_path: str=None):
        src=self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла","Сначала выберите видео."); return
        if out_path is None:
            ts=utils.sec_to_hhmmss(int(sec)).replace(":","-")
            out_path=filedialog.asksaveasfilename(title="Сохранить кадр…", defaultextension=".png",
                                                  filetypes=[("PNG","*.png")],
                                                  initialfile=f"frame_{ts}.png",
                                                  initialdir=self._default_frames_dir())
            if not out_path: return
        cmd=[self._ffmpeg_cmd(),"-hide_banner","-loglevel","error","-y",
             "-i",src,"-ss",str(max(0.0,float(sec))),"-frames:v","1", out_path]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            messagebox.showinfo("Готово", f"Кадр сохранён:\n{out_path}")
        except Exception as e:
            messagebox.showwarning("FFmpeg", f"Не удалось сохранить кадр:\n{e}")

    def _save_current_frame(self):
        self._save_frame_at_sec(float(self.var_pos.get() or 0.0))

    # ---- воспроизведение
    def _play(self):
        src=self.app.state.get("video_path") or ""
        if not src or not os.path.isfile(src):
            messagebox.showwarning("Нет файла","Сначала выберите видео."); return
        self._ensure_duration()
        start=float(self.var_pos.get() or 0.0)
        left=max(0.0, self._duration_cache-start)
        self._stop(kill_only=True)
        cmd=[self._ffplay_cmd(),"-hide_banner","-loglevel","error","-i",src]
        if start>0: cmd+=["-ss",str(start)]
        if left>0:  cmd+=["-t",str(left),"-autoexit"]
        try:
            self._play_proc=subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}")
            self._play_proc=None; return
        self._play_started_at=time.monotonic(); self._play_start_sec=start
        self._start_play_timer()

    def _seek(self): self._play()

    def _stop(self, kill_only=False):
        if self._play_stop_evt is not None: self._play_stop_evt.set()
        self._play_stop_evt=None
        if self._play_proc and self._play_proc.poll() is None:
            try: self._play_proc.terminate()
            except Exception: pass
            try: self._play_proc.wait(timeout=0.5)
            except Exception:
                try: self._play_proc.kill()
                except Exception: pass
        self._play_proc=None
        if not kill_only: self._update_pos_label(float(self.var_pos.get() or 0.0), self._duration_cache)

    def _start_play_timer(self):
        self._play_stop_evt=threading.Event()
        def run():
            while not self._play_stop_evt.is_set():
                if self._play_proc is None or self._play_proc.poll() is not None: break
                elapsed=time.monotonic()-self._play_started_at
                cur=min(self._duration_cache, self._play_start_sec+elapsed)
                try:
                    self.timeline_canvas.after(0, self.var_pos.set, cur)
                    self.timeline_canvas.after(0, self._on_scale_drag, None)
                except Exception: pass
                time.sleep(0.15)
            try:
                self.timeline_canvas.after(0, self._update_pos_label, float(self.var_pos.get() or 0.0), self._duration_cache)
            except Exception: pass
        threading.Thread(target=run, daemon=True).start()
