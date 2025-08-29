# -*- coding: utf-8 -*-
"""
presets.py — сохранение/загрузка пресетов настроек (JSON) и применение к UI.
"""
import json

def collect(app):
    """Собираем основные настройки из UI в словарь."""
    return {
        "video_path": app.state.get("video_path"),
        "output_dir": app.state.get("output_dir"),
        "goto": app.var_goto.get(),
        "frag_start": app.var_frag_start.get(),
        "frag_end": app.var_frag_end.get(),
        "cut_mode": app.var_cut_mode.get(),
        "fmt": app.var_fmt.get(),
        "quality": app.var_quality.get(),
        "scale": app.var_scale.get(),
        "am_mode": app.var_am_mode.get(),
        "am_db": app.var_am_db.get(),
        "am_freeze_t": app.var_am_freeze_t.get(),
        "am_minlen": app.var_am_minlen.get(),
        "am_pad": app.var_am_pad.get(),
        "logo_path": app.var_logo_path.get(),
        "logo_pos": app.var_logo_pos.get(),
        "logo_scale": app.var_logo_scale.get(),
        "speed": app.var_speed.get(),
        "pitch": app.var_pitch.get(),
    }

def apply_to_ui(app, cfg):
    """Применяем словарь настроек к элементам UI."""
    if not cfg: return
    app.state["video_path"] = cfg.get("video_path") or app.state["video_path"]
    app.var_video.set(app.state["video_path"] or "(файл не выбран)")
    app.state["output_dir"] = cfg.get("output_dir") or app.state["output_dir"]
    app.var_outdir.set(app.state["output_dir"])
    app.var_goto.set(cfg.get("goto","00:00"))
    app.var_frag_start.set(cfg.get("frag_start","00:00"))
    app.var_frag_end.set(cfg.get("frag_end","00:05"))
    app.var_cut_mode.set(cfg.get("cut_mode","fast"))
    app.var_fmt.set(cfg.get("fmt","mp4"))
    app.var_quality.set(cfg.get("quality","medium"))
    app.var_scale.set(cfg.get("scale","keep"))
    app.var_am_mode.set(cfg.get("am_mode","both"))
    app.var_am_db.set(cfg.get("am_db","-35"))
    app.var_am_freeze_t.set(cfg.get("am_freeze_t","2.0"))
    app.var_am_minlen.set(cfg.get("am_minlen","1.0"))
    app.var_am_pad.set(cfg.get("am_pad","0.2"))
    app.var_logo_path.set(cfg.get("logo_path",""))
    app.var_logo_pos.set(cfg.get("logo_pos","top-right"))
    app.var_logo_scale.set(cfg.get("logo_scale","10"))
    app.var_speed.set(cfg.get("speed","1.5"))
    app.var_pitch.set(cfg.get("pitch","preserve"))

def save(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
