# -*- coding: utf-8 -*-
"""
02_autolayout / autolayout.py
Вариант B (фикс): гарантированный обход блоков.
"""
import tomllib, glob, os, fnmatch
from pathlib import Path

def _toml_quote(s: str) -> str:
    return '"' + s.replace('"', '\"') + '"'

def _fmt_float(x: float) -> str:
    return f"{x:.6g}"

def _fmt_value(v):
    if isinstance(v, bool):  return "true" if v else "false"
    if isinstance(v, int):   return str(v)
    if isinstance(v, float): return _fmt_float(v)
    if isinstance(v, str):   return _toml_quote(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt_value(i) for i in v) + "]"
    return _toml_quote(str(v))

def dump_graph_toml(graph):
    lines = []
    meta = graph.get("meta", {})
    blocks = graph.get("blocks", [])
    lines.append("[meta]")
    for k in ("title", "canvas_size", "prepare_notes"):
        if k in meta:
            lines.append(f"{k} = {_fmt_value(meta[k])}")
    lines.append("")
    for b in blocks:
        lines.append("[[blocks]]")
        for k in ("id", "title"):
            if k in b:
                lines.append(f"{k} = {_fmt_value(b[k])}")
        if "auto_pos" in b:
            lines.append(f"auto_pos = {_fmt_value(b['auto_pos'])}")
        for k in sorted(b.keys()):
            if k.startswith("auto_") and k not in ("auto_pos",) and not isinstance(b[k], (list, tuple, dict)):
                lines.append(f"{k} = {_fmt_value(b[k])}")
        if "properties" in b:
            lines.append(f"properties = {_fmt_value(b['properties'])}")
        for e in b.get("outs", []):
            lines.append("[[blocks.outs]]")
            for k in ("to", "label"):
                if k in e:
                    lines.append(f"{k} = {_fmt_value(e[k])}")
            for k in sorted(e.keys()):
                if k.startswith("auto_") and k not in ("auto_waypoints",) and not isinstance(e[k], (list, tuple, dict)):
                    lines.append(f"{k} = {_fmt_value(e[k])}")
            if "auto_waypoints" in e:
                pts = e["auto_waypoints"]
                inner = ", ".join(f"[{_fmt_value(px)}, {_fmt_value(py)}]" for px, py in pts)
                lines.append(f"auto_waypoints = [{inner}]")
            lines.append("")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

def rect_of_block(b, defaults):
    x, y = b.get("auto_pos", [0.5, 0.5])
    width = b.get("auto_width", defaults["block.width"])
    props = b.get("properties", [])
    h = b.get("auto_header_height", defaults["block.header_height"]) + len(props) * b.get("auto_prop_height", defaults["block.prop_height"])
    return x - width/2, y - h/2, x + width/2, y + h/2

def segment_intersects_rect(p1, p2, rect):
    (x1,y1), (x2,y2) = p1, p2
    xmin,ymin,xmax,ymax = rect
    def inside(x,y): return xmin <= x <= xmax and ymin <= y <= ymax
    if inside(x1,y1) or inside(x2,y2): return True
    def inter(a,b,c,d):
        def orient(p,q,r): return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
        o1 = orient(a,b,c); o2 = orient(a,b,d); o3 = orient(c,d,a); o4 = orient(c,d,b)
        if o1 == 0 and min(a[0],b[0]) <= c[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= c[1] <= max(a[1],b[1]): return True
        if o2 == 0 and min(a[0],b[0]) <= d[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= d[1] <= max(a[1],b[1]): return True
        if o3 == 0 and min(c[0],d[0]) <= a[0] <= max(c[0],d[0]) and min(c[1],d[1]) <= a[1] <= max(c[1],d[1]): return True
        if o4 == 0 and min(c[0],d[0]) <= b[0] <= max(c[0],d[0]) and min(c[1],d[1]) <= b[1] <= max(c[1],d[1]): return True
        return (o1>0) != (o2>0) and (o3>0) != (o4>0)
    A,B=(x1,y1),(x2,y2)
    edges=[((xmin,ymin),(xmax,ymin)),((xmax,ymin),(xmax,ymax)),((xmax,ymax),(xmin,ymax)),((xmin,ymax),(xmin,ymin))]
    return any(inter(A,B,C,D) for C,D in edges)

def poly_intersects_any(points, rects):
    if not points or len(points)<2: return False
    for i in range(len(points)-1):
        if any(segment_intersects_rect(points[i], points[i+1], R) for R in rects):
            return True
    return False

def connector_point(b, side, defaults):
    xmin,ymin,xmax,ymax = rect_of_block(b, defaults)
    if side == "left":   return (xmin, (ymin+ymax)/2)
    if side == "right":  return (xmax, (ymin+ymax)/2)
    if side == "top":    return ((xmin+xmax)/2, ymin)
    if side == "bottom": return ((xmin+xmax)/2, ymax)
    return ((xmin+xmax)/2, (ymin+ymax)/2)

def choose_ports_auto(src_pos, dst_pos, direction):
    sx, sy = src_pos; dx, dy = dst_pos
    if direction in ("LR","RL"):
        from_side = "right" if dx >= sx else "left"
        to_side   = "left"  if dx >= sx else "right"
        if abs(dx-sx) < 0.08:
            from_side = "bottom" if dy >= sy else "top"
            to_side   = "top"    if dy >= sy else "bottom"
    else:
        from_side = "bottom" if dy >= sy else "top"
        to_side   = "top"    if dy >= sy else "bottom"
        if abs(dy-sy) < 0.08:
            from_side = "right" if dx >= sx else "left"
            to_side   = "left"  if dx >= sx else "right"
    return from_side, to_side

def route_edge_variantB(src, dst, defaults, rects, cfg_edges, direction):
    p_from = connector_point(src, cfg_edges["port_from_default"], defaults)
    p_to   = connector_point(dst, cfg_edges["port_to_default"], defaults)
    if not any(segment_intersects_rect(p_from, p_to, R) for R in rects):
        return {"curve":"straight","waypoints":[],"from":cfg_edges["port_from_default"],"to":cfg_edges["port_to_default"]}

    sx, sy = src.get("auto_pos",[0.5,0.5]); dx, dy = dst.get("auto_pos",[0.5,0.5])
    cand_ports = [choose_ports_auto((sx,sy),(dx,dy), direction)]
    extra = [("right","left"),("left","right"),("bottom","top"),("top","bottom"),
             ("right","top"),("right","bottom"),("left","top"),("left","bottom")]
    for comb in extra:
        if comb not in cand_ports:
            cand_ports.append(comb)
        if len(cand_ports) >= 8: break

    for pf, pt in cand_ports:
        pf_pt = connector_point(src, pf, defaults)
        pt_pt = connector_point(dst, pt, defaults)
        dog1 = [pf_pt, (pf_pt[0], pt_pt[1]), pt_pt]
        dog2 = [pf_pt, (pt_pt[0], pf_pt[1]), pt_pt]
        if not poly_intersects_any(dog1, rects):
            return {"curve":"orthogonal","waypoints":[dog1[1]],"from":pf,"to":pt}
        if not poly_intersects_any(dog2, rects):
            return {"curve":"orthogonal","waypoints":[dog2[1]],"from":pf,"to":pt}

    padding = float(cfg_edges["avoid_padding"])
    detour_pref = cfg_edges["avoid_direction"]
    min_y = min(r[1] for r in rects); max_y = max(r[3] for r in rects)
    corridor_pad = padding*1.2
    if detour_pref == "above":
        y_detour = min_y - corridor_pad
    elif detour_pref == "below":
        y_detour = max_y + corridor_pad
    else:
        center_y = 0.5; y_above = min_y - corridor_pad; y_below = max_y + corridor_pad
        y_detour = y_above if abs(center_y - y_above) < abs(center_y - y_below) else y_below

    def shift_x(pt, side, pad):
        x,y = pt
        if side=="right":  return (x+pad, y)
        if side=="left":   return (x-pad, y)
        return (x, y)

    pf_auto, pt_auto = choose_ports_auto((sx,sy),(dx,dy), direction)
    pfa = connector_point(src, pf_auto, defaults); pta = connector_point(dst, pt_auto, defaults)
    pfa2 = shift_x(pfa, pf_auto, padding); pta2 = shift_x(pta, pt_auto, padding)
    waypoints = [ (pfa2[0], y_detour), (pta2[0], y_detour) ]
    return {"curve":"orthogonal","waypoints":waypoints,"from":pf_auto,"to":pt_auto}

def try_toposort(ids, edges):
    from collections import defaultdict, deque
    indeg = {u:0 for u in ids}; adj = defaultdict(list)
    for u,v in edges:
        if u in indeg and v in indeg:
            adj[u].append(v); indeg[v]+=1
    dq = deque([u for u in ids if indeg[u]==0]); order = []
    while dq:
        u = dq.popleft(); order.append(u)
        for w in adj[u]:
            indeg[w]-=1
            if indeg[w]==0: dq.append(w)
    return order if len(order)==len(ids) else None

def layered_order(ids, edges):
    from collections import defaultdict, deque
    adj = defaultdict(list); rev = defaultdict(list)
    for u,v in edges:
        adj[u].append(v); rev[v].append(u)
    starts = [u for u in ids if not rev[u]] or [ids[0]]
    rank = {u:0 for u in ids}; dq = deque(starts); seen=set(starts)
    while dq:
        u = dq.popleft()
        for w in adj[u]:
            rank[w] = max(rank[w], rank[u]+1)
            if w not in seen: seen.add(w); dq.append(w)
    return sorted(ids, key=lambda x: (rank.get(x,0), ids.index(x)))

def order_blocks(blocks, direction, cfg_order):
    mode = cfg_order.get("mode","auto")
    ids = [b["id"] for b in blocks if "id" in b]
    edges = [(b["id"], e["to"]) for b in blocks for e in b.get("outs",[]) if e.get("to")]
    if mode=="input":
        ordered = blocks
    else:
        topo = try_toposort(ids, edges) if mode in ("auto","topological") else None
        if topo:
            id2b = {b["id"]: b for b in blocks}; ordered = [id2b[i] for i in topo if i in id2b]
        else:
            order_ids = layered_order(ids, edges); id2b = {b["id"]: b for b in blocks}
            ordered = [id2b[i] for i in order_ids if i in id2b]
    if direction in ("RL","BT"): ordered = list(reversed(ordered))
    return ordered

def layout_blocks(blocks, cfg):
    direction = cfg["layout"]["direction"]
    blocks[:] = order_blocks(blocks, direction, cfg.get("order", {}))
    n = len(blocks)
    if n==0: return
    if direction in ("LR","RL"):
        xs = [0.1+i*(0.8/max(1,n-1)) for i in range(n)]
        if direction=="RL": xs.reverse()
        for i,b in enumerate(blocks): b["auto_pos"]= [xs[i],0.5]
    else:
        ys = [0.1+i*(0.8/max(1,n-1)) for i in range(n)]
        if direction=="BT": ys.reverse()
        for i,b in enumerate(blocks): b["auto_pos"]= [0.5,ys[i]]

def apply_defaults(blocks,cfg):
    d=cfg["defaults"]
    for b in blocks:
        b.setdefault("auto_width",d.get("block.width",0.1))
        b.setdefault("auto_header_height",d.get("block.header_height",0.1))
        b.setdefault("auto_prop_height",d.get("block.prop_height",0.06))

def build_edges(blocks,cfg):
    defaults = cfg["defaults"]; direction = cfg["layout"]["direction"]
    edcfg = cfg.get("edges", {})
    dir_to_ports={"LR":("right","left"),"RL":("left","right"),"TB":("bottom","top"),"BT":("top","bottom")}
    cf_def,ct_def=dir_to_ports.get(direction,("right","left"))
    cfg_edges = {
        "curve_pref": edcfg.get("curve","auto"),
        "avoid_nodes": bool(edcfg.get("avoid_nodes",True)),
        "avoid_padding": float(edcfg.get("avoid_padding",0.08)),
        "avoid_direction": edcfg.get("avoid_direction","auto"),
        "port_from_default": edcfg.get("connector_from",cf_def),
        "port_to_default":   edcfg.get("connector_to",ct_def),
    }
    rects = [rect_of_block(b, defaults) for b in blocks]
    id2b = {b["id"]: b for b in blocks if "id" in b}
    for b in blocks:
        for e in b.get("outs", []):
            to_id = e.get("to")
            if not to_id or to_id not in id2b: continue
            src, dst = b, id2b[to_id]
            res = route_edge_variantB(src, dst, defaults, rects, cfg_edges, direction)
            e["auto_curve"] = res["curve"]
            e["auto_connector_from"] = res["from"]
            e["auto_connector_to"] = res["to"]
            if res["waypoints"]: e["auto_waypoints"] = res["waypoints"]
            e.setdefault("auto_label_offset", cfg["defaults"].get("style.label_offset", 0.5))

def read_toml_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def load_config(cfg_path: Path) -> dict:
    raw = read_toml_text(cfg_path)
    return tomllib.loads(raw)

def process_file(path_in,cfg,out_suffix):
    with open(path_in,"rb") as f: data=tomllib.load(f)
    meta=data.get("meta",{}); blocks=data.get("blocks",[])
    layout_blocks(blocks,cfg); apply_defaults(blocks,cfg); build_edges(blocks,cfg)
    graph_out={"meta":{"title":meta.get("title",""),"canvas_size":meta.get("canvas_size",[1200,800]),"prepare_notes":meta.get("prepare_notes",[])},
               "blocks":blocks}
    out_text=dump_graph_toml(graph_out); base,_=os.path.splitext(path_in); out_path=f"{base}{out_suffix}.toml"
    with open(out_path,"w",encoding="utf-8") as f:f.write(out_text); return path_in,out_path

def main():
    root=Path(__file__).parent; cfg_path=root/"config_autolayout.toml"; cfg=load_config(cfg_path)
    cfg.setdefault("layout",{}); cfg["layout"].setdefault("direction","LR")
    cfg.setdefault("order",{});  cfg.setdefault("edges",{}); cfg["edges"].setdefault("curve","auto")
    cfg["edges"].setdefault("avoid_nodes",True); cfg["edges"].setdefault("avoid_padding",0.08); cfg["edges"].setdefault("avoid_direction","auto")
    cfg["edges"].setdefault("connector_from","right"); cfg["edges"].setdefault("connector_to","left")
    cfg.setdefault("defaults",{}); cfg["defaults"].setdefault("block.width",0.1); cfg["defaults"].setdefault("block.header_height",0.1)
    cfg["defaults"].setdefault("block.prop_height",0.06); cfg["defaults"].setdefault("style.label_offset",0.5)
    io=cfg.get("io",{}); input_dirs=io.get("input_dirs",["."]); recursive=bool(io.get("recursive",True))
    include_extensions=io.get("include_extensions",["toml"]); exclude_patterns=io.get("exclude_patterns",["*_02.toml","*_03.toml"])
    input_suffix=io.get("input_suffix","_01.toml"); out_suffix=io.get("output_suffix","_02")
    files_in=[]; 
    for ddir in input_dirs:
        pattern="**/*" if recursive else "*"
        for ext in include_extensions: files_in+=glob.glob(os.path.join(ddir,f"{pattern}"),recursive=recursive)
    files_in=[p for p in files_in if p.endswith(input_suffix)]
    def is_excluded(p): 
        return any(fnmatch.fnmatch(os.path.basename(p),pat) for pat in exclude_patterns)
    files_in=[p for p in files_in if not is_excluded(p)]
    print(f"Found {len(files_in)} file(s)." )
    for path_in in files_in:
        try:
            src,outp=process_file(path_in,cfg,out_suffix)
            print(f"OK: {src} -> {outp}")
        except Exception as e:
            print(f"ERR processing {path_in} -> {e}")
            if io.get("stop_on_error",True): raise

if __name__=="__main__": 
    main()
