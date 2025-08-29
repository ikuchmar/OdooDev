# video_editor/tools/ui_app_audio.py
# -*- coding: utf-8 -*-
"""
Аудио → Аудиограмма по PCM без дрейфа + режимы отрисовки (столбики/линия/заливка).

Главное:
- PCM вытягиваем через ffmpeg+atrim (точно по времени), дрейфа нет.
- Метрика peak/rms, сглаживание (скользящее среднее).
- Режимы отрисовки: bars | line | area (выбирается в UI).
"""

import os, json, math, time, threading, subprocess
from array import array
import tkinter as tk
from tkinter import ttk, messagebox

from . import utils
from . import config_store as cfg


class UITabAudio:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent

        # параметры отображения/генерации
        self._VIEW_H = max(80, min(1000, cfg.get_int("audio", "view_height", 220)))
        self._zoom = max(0.25, min(8.0, cfg.get_float("audio", "zoom", 1.0)))
        self._px_per_sec_default = max(1, cfg.get_int("audio", "px_per_sec", 6))
        self._show_video_default = cfg.get_bool("audio", "show_video", True)
        self._saved_stream_global = cfg.get_int("audio", "stream_global", -1)
        self._metric = cfg.get("audio", "metric", "rms").lower()          # 'peak'|'rms'
        self._smooth = max(0, min(12, cfg.get_int("audio", "smooth", 1))) # радиус сглаживания
        self._draw_mode = cfg.get("audio", "draw", "area").lower()        # 'bars'|'line'|'area'

        # состояние ленты
        self._sec_per_px = 1.0
        self._total_width = 0
        self._chunk_w_target = 800
        self._wave_items = []
        self._bins_acc = None  # сюда собираем все бины для «line/area»

        # курсор/проигрывание
        self._cursor_x = 0
        self._cursor_id = None
        self._play_proc = None
        self._play_started_at = 0.0
        self._play_start_sec = 0.0
        self._play_stop_evt = None

        # лимиты ширины ленты (чтобы Canvas жил)
        self._MAX_WIDTH = 12000

        # UI refs/vars
        self.var_stream_global = tk.StringVar(value=str(self._saved_stream_global) if self._saved_stream_global>=0 else "")
        self.var_px_per_sec = tk.StringVar(value=str(self._px_per_sec_default))
        self.var_metric = tk.StringVar(value=self._metric)
        self.var_smooth = tk.IntVar(value=self._smooth)
        self.var_smooth_disp = tk.StringVar(value=str(self._smooth))
        self.var_draw = tk.StringVar(value=self._draw_mode)

        self._use_map_global = True  # фолбэк для -map
        self._build()

    # --- ff* helpers
    def _ffplay_cmd(self):  return (getattr(self.app,"var_ffplay",None).get() or "ffplay")  if hasattr(self.app,"var_ffplay") else "ffplay"
    def _ffprobe_cmd(self): return (getattr(self.app,"var_ffprobe",None).get() or "ffprobe") if hasattr(self.app,"var_ffprobe") else "ffprobe"
    def _ffmpeg_cmd(self):  return (getattr(self.app,"var_ffmpeg",None).get() or "ffmpeg")  if hasattr(self.app,"var_ffmpeg") else "ffmpeg"

    # --- UI
    def _build(self):
        root = ttk.Frame(self.parent, padding=10); root.pack(fill="both", expand=True)

        top = ttk.LabelFrame(root, text="Аудиограмма (waveform)", padding=8); top.pack(fill="x")
        ttk.Label(top, text="Аудио-дорожка:").pack(side="left")
        self.cb_stream = ttk.Combobox(top, textvariable=self.var_stream_global, width=26, state="readonly"); self.cb_stream.pack(side="left", padx=(4,8))
        ttk.Button(top, text="Обновить список", command=self._scan_audio_streams).pack(side="left", padx=(0,10))

        ttk.Label(top, text="Пикс/сек:").pack(side="left")
        ttk.Entry(top, textvariable=self.var_px_per_sec, width=6).pack(side="left", padx=(4,8))

        ttk.Label(top, text="Масштаб:").pack(side="left", padx=(8,4))
        self.var_zoom_value = tk.StringVar(value=f"{self._zoom:.2f}×")
        ttk.Button(top, text="−", width=3, command=lambda: self._zoom_change(0.5)).pack(side="left")
        ttk.Button(top, text="1×", width=3, command=lambda: self._zoom_set(1.0)).pack(side="left", padx=2)
        ttk.Button(top, text="+", width=3, command=lambda: self._zoom_change(2.0)).pack(side="left", padx=(0,6))
        ttk.Label(top, textvariable=self.var_zoom_value).pack(side="left")
        ttk.Label(top, text="(зум применится после «Сгенерировать»)", foreground="#666").pack(side="left", padx=(8,8))

        ttk.Label(top, text="Метрика:").pack(side="left", padx=(10,2))
        ttk.Combobox(top, textvariable=self.var_metric, values=["peak","rms"], width=6, state="readonly").pack(side="left")

        ttk.Label(top, text="Сглаживание:").pack(side="left", padx=(10,2))
        ttk.Button(top, text="−", width=2, command=lambda: self._change_smooth(-1)).pack(side="left")
        ttk.Label(top, textvariable=self.var_smooth_disp, width=3, anchor="center").pack(side="left")
        ttk.Button(top, text="+", width=2, command=lambda: self._change_smooth(+1)).pack(side="left")

        ttk.Label(top, text="Режим:").pack(side="left", padx=(10,2))
        ttk.Combobox(top, textvariable=self.var_draw, values=["bars","line","area"], width=6, state="readonly").pack(side="left")

        pr = ttk.Frame(root); pr.pack(fill="x", padx=10, pady=(6,0))
        self.var_wave_progress = tk.StringVar(value="Аудиограмма: 0/0"); ttk.Label(pr, textvariable=self.var_wave_progress).pack(side="left")
        self.pb_wave = ttk.Progressbar(pr, orient="horizontal", mode="determinate", length=260, maximum=100, value=0); self.pb_wave.pack(side="left", padx=8)
        ttk.Button(pr, text="Сгенерировать аудиограмму", command=self._gen_waveform).pack(side="left", padx=(10,8))
        self.var_show_video = tk.BooleanVar(value=self._show_video_default)
        ttk.Checkbutton(pr, text="Показывать видео (ffplay)", variable=self.var_show_video).pack(side="left", padx=(8,0))

        self.var_wave_hint = tk.StringVar(value=""); ttk.Label(root, textvariable=self.var_wave_hint, foreground="#555").pack(fill="x", padx=10, pady=(4,0))

        mid = ttk.Frame(root); mid.pack(fill="both", expand=True, pady=(8,8))
        self.canvas = tk.Canvas(mid, height=self._VIEW_H, bg="#111"); self.canvas.pack(fill="both", expand=True, side="top")
        self.hbar = ttk.Scrollbar(mid, orient="horizontal", command=self.canvas.xview); self.hbar.pack(fill="x", side="bottom")
        self.canvas.configure(xscrollcommand=self.hbar.set)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        bot = ttk.Frame(root); bot.pack(fill="x")
        ttk.Label(bot, text="Позиция:").pack(side="left")
        self.var_pos = tk.DoubleVar(value=0.0)
        self.scale = ttk.Scale(bot, from_=0.0, to=1.0, orient="horizontal", variable=self.var_pos, command=self._on_scale_drag)
        self.scale.pack(side="left", fill="x", expand=True, padx=8)
        self.lbl_pos = ttk.Label(bot, text="00:00:00 / 00:00:00"); self.lbl_pos.pack(side="left")
        ttk.Button(bot, text="▶ Пуск", command=self._play).pack(side="left", padx=(10,4))
        ttk.Button(bot, text="⏹ Стоп", command=self._stop).pack(side="left", padx=4)
        ttk.Button(bot, text="⏩ Перейти", command=self._seek).pack(side="left", padx=4)

        root.columnconfigure(0, weight=1)
        self._scan_audio_streams()

    # --- streams
    def _scan_audio_streams(self):
        src = self.app.state.get("video_path") or cfg.get("app","last_video","") or ""
        src = os.path.normpath(os.path.expanduser(os.path.expandvars(src)))
        if not src or not os.path.isfile(src):
            self.cb_stream["values"] = []; self.var_stream_global.set(""); return
        cmd = [self._ffprobe_cmd(), "-v","error","-show_streams","-select_streams","a","-of","json", src]
        try:
            data = json.loads(subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8","ignore"))
        except Exception:
            data = {}
        streams = []; aord=0
        for st in (data.get("streams") or []):
            gidx=int(st.get("index",-1))
            disp = st.get("disposition") or {}
            is_def = (disp.get("default",0)==1)
            streams.append({
                "global": gidx, "aord": aord,
                "codec": (st.get("codec_name") or ""), "channels": int(st.get("channels",0) or 0),
                "layout": (st.get("channel_layout") or ""), "lang": (st.get("tags",{}).get("language") or ""),
                "title": (st.get("tags",{}).get("title") or ""), "default": is_def,
                "duration": float(st.get("duration") or 0.0)
            }); aord+=1
        streams.sort(key=lambda s:(0 if s["default"] else 1, s["aord"]))
        vals=[]; def_global=None
        for s in streams:
            d=f"  dur~{int(s['duration'])}s" if s["duration"] else ""
            label=f"a:{s['aord']}  [#{s['global']}]  {s['codec']}  {s['channels']}ch {s['layout']}{d}"
            if s["lang"]: label+=f"  [{s['lang']}]"
            if s["title"]: label+=f"  {s['title']}"
            if s["default"]: label+="  (default)"; def_global=str(s["global"])
            vals.append(label)
        self.audio_streams = streams
        self.cb_stream["values"]=vals
        all_globals=[str(s["global"]) for s in streams]
        target=self.var_stream_global.get().strip()
        if target not in all_globals:
            target = def_global or (all_globals[0] if all_globals else "")
        self.var_stream_global.set(target)
        if target!="": cfg.set("audio","stream_global", int(target))

    def _selected_stream_global(self):
        try: return int(self.var_stream_global.get().strip() or -1)
        except Exception: return -1

    # --- small utils
    def _set_controls_enabled(self, enabled: bool):
        state="normal" if enabled else "disabled"
        for w in (self.cb_stream,):
            try: w.configure(state=state)
            except Exception: pass

    def _set_progress(self, done, total):
        pct = 0 if total<=0 else int(round(done*100.0/total))
        self.var_wave_progress.set(f"Аудиограмма: {done}/{max(1,total)}")
        self.pb_wave["value"]=pct

    def _clear_wave_canvas(self):
        for it in self._wave_items:
            try: self.canvas.delete(it)
            except Exception: pass
        self._wave_items=[]
        if self._cursor_id is not None:
            try: self.canvas.delete(self._cursor_id)
            except Exception: pass
            self._cursor_id=None

    def _effective_px_per_sec(self, duration):
        try: base = max(1, int(float(self.var_px_per_sec.get())))
        except Exception: base = self._px_per_sec_default
        desired = max(1, int(round(base * self._zoom)))
        width = int(round(duration * desired))
        if width <= self._MAX_WIDTH: return desired, width
        limited = max(1, int(self._MAX_WIDTH/max(1.0,duration)))
        return limited, int(round(duration*limited))

    def _change_smooth(self, d):
        v=max(0, min(12, int(self.var_smooth.get())+int(d)))
        self.var_smooth.set(v); self.var_smooth_disp.set(str(v))

    # --- PCM core
    def _decode_pcm_bytes(self, src, start_sec, dur_sec, sel_global):
        """Достаём PCM точно по времени (atrim). Форматы: s16le → f32le → u8."""
        ffmpeg = self._ffmpeg_cmd()
        sr = 16000
        attempts=[("s16le",2),("f32le",4),("u8",1)]
        last_err=""
        for fmt,_bps in attempts:
            atrim=f"atrim=start={max(0.0,start_sec)}:end={max(0.0,start_sec+max(0.001,dur_sec))}"
            cmd=[ffmpeg,"-hide_banner","-nostats","-loglevel","error","-i",src,"-vn"]
            if self._use_map_global and sel_global>=0: cmd+=["-map",f"0:{sel_global}"]
            cmd+=["-af",atrim,"-ac","1","-ar",str(sr),"-f",fmt,"pipe:1"]
            try:
                p=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                raw,err=p.communicate(); rc=p.returncode; err=(err.decode("utf-8","ignore") if err else "")
            except Exception as e:
                raw=b""; rc=1; err=str(e)
            if rc!=0 and (("matches no streams" in err) or ("stream specifier" in err.lower())) and self._use_map_global:
                self._use_map_global=False
                try:
                    cmd2=[ffmpeg,"-hide_banner","-nostats","-loglevel","error","-i",src,"-vn","-af",atrim,"-ac","1","-ar",str(sr),"-f",fmt,"pipe:1"]
                    p2=subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    raw,err=p2.communicate(); rc=p2.returncode; err=(err.decode("utf-8","ignore") if err else "")
                except Exception as e2:
                    raw=b""; rc=1; err=str(e2)
            last_err = err or f"ffmpeg rc={rc}"
            if rc==0 and raw: return True, fmt, sr, raw
        return False, f"ERROR: {last_err}", sr, b""

    # --- амплитуда
    @staticmethod
    def _peak_from_block(fmt, block):
        if not block: return 0.0
        try:
            if fmt=="s16le":
                arr=array("h"); arr.frombytes(block); return min(1.0, max((abs(x) for x in arr), default=0)/32767.0)
            if fmt=="f32le":
                arr=array("f"); arr.frombytes(block); return max(0.0, min(1.0, float(max((abs(x) for x in arr), default=0.0))))
            arr=array("B"); arr.frombytes(block);  return min(1.0, max((abs(int(x)-128) for x in arr), default=0)/127.0)
        except Exception: return 0.0

    @staticmethod
    def _rms_from_block(fmt, block):
        if not block: return 0.0
        try:
            if fmt=="s16le":
                arr=array("h"); arr.frombytes(block); n=len(arr);
                if n==0: return 0.0
                s=0.0
                for v in arr: s+=float(v)*float(v)
                return min(1.0, math.sqrt(s/n)/32767.0)
            if fmt=="f32le":
                arr=array("f"); arr.frombytes(block); n=len(arr)
                if n==0: return 0.0
                s=0.0
                for v in arr: s+=float(v)*float(v)
                return max(0.0, min(1.0, math.sqrt(s/n)))
            arr=array("B"); arr.frombytes(block); n=len(arr)
            if n==0: return 0.0
            s=0.0
            for v in arr:
                vv=float(int(v)-128); s+=vv*vv
            return min(1.0, math.sqrt(s/n)/127.0)
        except Exception: return 0.0

    @staticmethod
    def _smooth_bins(bins, radius):
        r=int(max(0, radius))
        if r==0 or not bins: return bins
        n=len(bins); out=[0.0]*n
        for i in range(n):
            a=max(0, i-r); b=min(n-1, i+r)
            s=0.0; cnt=0
            for k in range(a,b+1): s+=bins[k]; cnt+=1
            out[i]=s/cnt if cnt else 0.0
        return out

    # --- координаты/курсор
    def _time_to_x(self, sec):
        return 0 if self._total_width<=0 else int(round(float(sec)/self._sec_per_px))
    def _x_to_time(self, x):
        if self._total_width<=0: return 0.0
        duration=float(self.scale.cget("to") or 0.0)
        sec=(float(x)+0.5)*self._sec_per_px
        return max(0.0, min(sec, duration))

    def _draw_cursor(self, x):
        x=max(0, min(int(x), max(0, self._total_width-1))); self._cursor_x=x
        h=self._VIEW_H
        if self._cursor_id is None:
            self._cursor_id=self.canvas.create_line(x,0,x,h,fill="red",width=2)
        else:
            self.canvas.coords(self._cursor_id, x,0,x,h)
        try:
            cw=int(self.canvas.winfo_width()); left=int(self.canvas.canvasx(0)); right=left+cw
            if x<left+40 or x>right-40:
                new_left=max(0, x-cw//2); self.canvas.xview_moveto(new_left/float(max(1,self._total_width)))
        except Exception: pass

    def _on_canvas_click(self, e):
        if self._total_width<=0: return
        x=int(self.canvas.canvasx(e.x)); x=max(0, min(x, self._total_width-1))
        sec=self._x_to_time(x); self.var_pos.set(sec); self._draw_cursor(self._time_to_x(sec)); self._update_pos_label(sec, self.scale.cget("to"))

    def _on_scale_drag(self, _):
        duration=float(self.scale.cget("to") or 0.0); sec=float(self.var_pos.get() or 0.0)
        self._draw_cursor(self._time_to_x(sec)); self._update_pos_label(sec, duration)

    def _update_pos_label(self, cur, total):
        try: total=float(total)
        except Exception: total=0.0
        self.lbl_pos.config(text=f"{utils.sec_to_hhmmss(int(cur))} / {utils.sec_to_hhmmss(int(total))}")

    # --- генерация
    def _gen_waveform(self):
        if not self.app.state.get("video_path"):
            messagebox.showwarning("Нет файла", "Сначала выберите видео/аудио"); return
        cfg.set("app", "last_video", self.app.state["video_path"])

        self._scan_audio_streams()
        sel_global=self._selected_stream_global()
        if sel_global>=0: cfg.set("audio","stream_global", sel_global)

        # стартовая длительность по метаданным (для ширины), потом уточним по PCM
        meta_duration = next((s["duration"] for s in self.audio_streams if str(s["global"])==self.var_stream_global.get().strip()), 0.0)
        if meta_duration<=0.0: meta_duration=float(self.app.state.get("duration") or 0.0)
        if meta_duration<=0.0:
            messagebox.showwarning("Длительность", "Неизвестна длительность файла."); return

        pps, total_w = self._effective_px_per_sec(meta_duration)
        self._total_width = total_w
        self._sec_per_px = meta_duration / float(max(1,total_w))
        self._bins_acc = [0.0]*total_w  # накапливаем здесь

        H=self._VIEW_H; self._clear_wave_canvas()
        self.canvas.config(scrollregion=(0,0,total_w,H))
        self._set_progress(0,1)
        self.var_wave_hint.set("Генерация аудиограммы (PCM, сглаживание, режим отрисовки)…")
        self._use_map_global = (sel_global>=0)
        metric = (self.var_metric.get() or "rms").lower()
        smooth_r = int(self.var_smooth.get())
        draw_mode = (self.var_draw.get() or "area").lower()

        # фактическая длительность по PCM
        pcm_total_seconds = 0.0
        bytes_per_sample_map={"s16le":2,"f32le":4,"u8":1}
        t_cursor=0.0

        n_chunks = int(math.ceil(total_w / float(self._chunk_w_target))); n_chunks=max(1,n_chunks)
        self._set_progress(0, n_chunks)

        def worker():
            nonlocal t_cursor, pcm_total_seconds
            first_err=[None]; offset_x=0; fmt_used=None; sr_used=None

            for i in range(n_chunks):
                width_i = self._chunk_w_target if (offset_x+self._chunk_w_target)<=total_w else (total_w-offset_x)
                width_i=int(max(1,width_i))
                planned_dur = width_i * self._sec_per_px
                start_sec = t_cursor

                ok, fmt, sr, raw = self._decode_pcm_bytes(self.app.state["video_path"], start_sec, planned_dur, sel_global)
                if ok and fmt_used is None: fmt_used=fmt; sr_used=sr

                bins=[0.0]*width_i
                if ok and raw:
                    bps = bytes_per_sample_map.get(fmt,2)
                    chunk_seconds = len(raw)/float(max(1,sr*bps))
                    pcm_total_seconds += chunk_seconds
                    t_cursor += chunk_seconds

                    total=len(raw); step = total/float(width_i); pos=0
                    block2amp = (self._peak_from_block if metric=="peak" else self._rms_from_block)
                    for x in range(width_i):
                        pos_end = int(round((x+1)*step))
                        if pos_end>total: pos_end=total
                        bins[x]= block2amp(fmt, raw[pos:pos_end])
                        pos=pos_end
                        if pos>=total and x<width_i-1:
                            # остаток — нули
                            for k in range(x+1, width_i): bins[k]=0.0
                            break
                    if smooth_r>0:
                        bins = self._smooth_bins(bins, smooth_r)
                else:
                    if i==0 and first_err[0] is None: first_err[0]=fmt  # здесь fmt содержит текст ошибки

                # накапливаем бины в общий массив (рисовать будем после сборки всех чанков)
                self._bins_acc[offset_x:offset_x+width_i] = bins

                # прогресс
                try: self.canvas.after(0, self._set_progress, min(i+1,n_chunks), n_chunks)
                except Exception: pass

                offset_x += width_i

            def on_done():
                self._set_controls_enabled(True)
                if first_err[0]:
                    messagebox.showwarning("FFmpeg", f"Не удалось построить аудиограмму:\n{first_err[0]}")
                    self.var_wave_hint.set("Ошибка построения аудиограммы (см. сообщение)."); return

                # финально подгоняем шкалу времени под фактическую длительность по PCM
                eff_dur = max(0.0, pcm_total_seconds)
                if eff_dur>0.0:
                    self._sec_per_px = eff_dur / float(max(1, self._total_width))
                    self.scale.configure(from_=0.0, to=eff_dur)

                # рендерим выбранным режимом
                self._render_bins(self._bins_acc, draw_mode)

                # подпись
                s = next((s for s in self.audio_streams if str(s["global"])==self.var_stream_global.get().strip()), None)
                info = ""
                if s:
                    ch=f"{s['channels']}ch {s['layout'] or ''}".strip()
                    lang=f"[{s['lang']}] " if s['lang'] else ""
                    ttl=s['title'] or ""
                    info=f" | a:{s['aord']} [#{s['global']}] {s['codec'] or ''} {ch} {lang}{ttl}".strip()
                extra = (f" • PCM: {fmt_used}@{sr_used}Hz" if fmt_used else "") + (f" • сглаживание r={smooth_r}" if smooth_r>0 else "") + f" • метрика={metric.upper()}"
                self.var_wave_hint.set(f"Готово: ширина {self._total_width}px × высота {self._VIEW_H}px (~{self._total_width/max(1,eff_dur):.1f} px/сек, zoom={self._zoom:.2f}×){info}{extra}" + (f" • достигнут предел {self._MAX_WIDTH}px" if self._total_width>=self._MAX_WIDTH else ""))

                # курсор/подпись
                cur=float(self.var_pos.get() or 0.0); self.var_pos.set(max(0.0, min(cur, eff_dur)))
                self._update_pos_label(self.var_pos.get(), eff_dur); self._draw_cursor(self._time_to_x(self.var_pos.get()))

                # сохранить настройки
                cfg.set("audio","px_per_sec", int(self.var_px_per_sec.get() or self._px_per_sec_default))
                cfg.set("audio","zoom", self._zoom)
                cfg.set("audio","view_height", self._VIEW_H)
                if self.var_stream_global.get().strip()!="": cfg.set("audio","stream_global", int(self.var_stream_global.get().strip()))
                cfg.set("audio","show_video", "true" if self.var_show_video.get() else "false")
                cfg.set("audio","metric", metric); cfg.set("audio","smooth", str(smooth_r)); cfg.set("audio","draw", draw_mode)

            try: self.canvas.after(0, on_done)
            except Exception: pass

        self._set_controls_enabled(False)
        threading.Thread(target=worker, daemon=True).start()

    # --- рендер целой ленты из bins (0..1)
    def _render_bins(self, bins, mode):
        """Рисуем готовую ленту одним приёмом — чтобы картинка была ровной."""
        self._clear_wave_canvas()
        if not bins: return
        H=self._VIEW_H; mid=H//2; amp_scale=(H*0.9)/2.0
        W=len(bins)

        if mode=="bars":
            # вертикальные штрихи (как было)
            items=[]
            for x,amp in enumerate(bins):
                if amp<=0.0: continue
                h=max(1, int(amp*amp_scale))
                it=self.canvas.create_line(x, mid-h, x, mid+h, fill="white")
                items.append(it)
            self._wave_items.extend(items)
        elif mode in ("line","area"):
            # формируем верхнюю/нижнюю огибающую
            # чтобы Canvas не задохнулся — ограничим количество точек ~6k
            step=max(1, int(W/6000))
            xs=list(range(0, W, step))
            if xs[-1]!=W-1: xs.append(W-1)

            top=[]; bot=[]
            for x in xs:
                y_up = mid - max(1, int(bins[x]*amp_scale))
                y_dn = mid + max(1, int(bins[x]*amp_scale))
                top.append((x, y_up)); bot.append((x, y_dn))

            if mode=="line":
                # рисуем две линии (верх/низ)
                coords_top=[]; coords_bot=[]
                for x,y in top: coords_top.extend([x,y])
                for x,y in bot: coords_bot.extend([x,y])
                self._wave_items.append(self.canvas.create_line(*coords_top, fill="white", smooth=True))
                self._wave_items.append(self.canvas.create_line(*coords_bot, fill="white", smooth=True))
            else:
                # заливка: полигон по верхней линии + обратная нижняя
                coords=[]
                for x,y in top: coords.extend([x,y])
                for x,y in reversed(bot): coords.extend([x,y])
                self._wave_items.append(self.canvas.create_polygon(*coords, fill="white", outline=""))
        else:
            # на всякий случай — bars
            return self._render_bins(bins, "bars")

        self.canvas.config(scrollregion=(0,0, W, H))

    # --- zoom/seek/playback
    def _zoom_set(self, z: float):
        self._zoom = max(0.25, min(8.0, float(z)))
        self.var_zoom_value.set(f"{self._zoom:.2f}×")

    def _zoom_change(self, factor: float):
        self._zoom_set(self._zoom*float(factor))

    def _play(self):
        if not self.app.state.get("video_path"):
            messagebox.showwarning("Нет файла","Сначала выберите видео/аудио"); return
        start=float(self.var_pos.get() or 0.0)
        cmd=[self._ffplay_cmd(),"-hide_banner","-loglevel","error","-i",self.app.state["video_path"]]
        if start>0: cmd+=["-ss",str(start)]
        if not self.var_show_video.get(): cmd+=["-nodisp"]
        try: self._play_proc=subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showwarning("ffplay", f"Не удалось запустить ffplay:\n{e}"); self._play_proc=None; return
        cfg.set("audio","show_video","true" if self.var_show_video.get() else "false")
        self._play_started_at=time.monotonic(); self._play_start_sec=start; self._start_play_timer()

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
        if not kill_only: self._update_pos_label(self.var_pos.get() or 0.0, self.scale.cget("to"))

    def _start_play_timer(self):
        self._play_stop_evt=threading.Event()
        def run():
            duration=float(self.scale.cget("to") or 0.0)
            while not self._play_stop_evt.is_set():
                if self._play_proc is None or self._play_proc.poll() is not None: break
                elapsed=time.monotonic()-self._play_started_at
                cur=min(duration, self._play_start_sec+elapsed)
                try:
                    self.canvas.after(0, self.var_pos.set, cur); self.canvas.after(0, self._on_scale_drag, None)
                except Exception: pass
                time.sleep(0.1)
            try: self.canvas.after(0, self._update_pos_label, float(self.var_pos.get() or 0.0), duration)
            except Exception: pass
        threading.Thread(target=run, daemon=True).start()
