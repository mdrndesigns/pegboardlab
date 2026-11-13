"""
PEGBOARDLAB model: parameters, the family registry, the build pipeline.

    merge_params(raw) -> p        validate(p) -> [errors]
    build(p, export=False) -> (solid, spec, warnings)
    layout(solid, p, spec) -> print-oriented solid
    context(p, spec) -> board stub      derived(p, spec) -> readout dict
    schema() -> UI controls (global + every family's)

A family is a module in families/ exposing NAME, LABEL, ORDER, PARAMS,
SCHEMA, ORIENT and two functions:

    plan(p, ctx)  -> dict(w, h, brand, keepout, mount)
                     plate size wanted, branding rect, height of the feature
                     band above the plate bottom, and the mount suggestion
                     (mt_* values used wherever the user left Mount on auto:
                     the standard single column is mt_pattern grid 1 × 3,
                     a wide holder asks for mt_bars twin)
    build(p, ctx, plate, mp) -> solid    plate with the family's features

The pipeline sizes the plate, lets the mount layer pick the holes, calls
the family, adds studs / ears, then branding. ctx carries the board,
stud Ø, print orientation, teardrop direction (None when studs are
vertical in the print), the no-supports switch, warnings and the
derived readout. Families that need no plate (nut, shelf) say so with
PLATE = False; PLATE may be a function of p (the brand kits mix bases).
Twin bars (mounts.py): the plate becomes two bars + a strip and the
spine is one single-column part printed twice.
"""

import importlib
import math
import os
import pkgutil

import cadquery as cq

import boards as BD
import branding as B
import fasteners as F
import geometry as G
import dims as DM
from families._lib import parse_list
import mounts as MT

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- families

def _load_families():
    import families
    fams = {}
    for m in pkgutil.iter_modules(families.__path__):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"families.{m.name}")
        if hasattr(mod, "NAME") and hasattr(mod, "build"):
            fams[mod.NAME] = mod
    return dict(sorted(fams.items(), key=lambda kv: getattr(kv[1], "ORDER", 99)))


FAMILIES = _load_families()


# ---------------------------------------------------------------- parameters

DEFAULTS = {
    "board": "imperial_19",
    "hole_d": 7.6, "t": 19.0, "pitch_x": 23.876, "pitch_y": 23.876, "stagger": 0.0, "back": 12.0,
    "shrink": 0.2, "clear": 0.0, "stud_len": 18.0,
    "material": "absgf",
    "family": "hook",
    "plate_t": 4.0,
    "plate_r": 3.0,            # plate corner radius
    "plate_edge": 0.6,         # front edge chamfer, 0 = none
    "split": "two",            # one | two   (two: spine plate on the board + holder screwed to it) - the house rule
    "spine_t": 0.0,            # spine plate thickness, 0 = auto (5 on thick boards, pilot depth + 1 on thin)
    "screw_d": 3.5,            # drywall screw major Ø
    "screw_len": 15.0,         # overall screw length (head included)
    "screw_head": 8.0,         # bugle head Ø
    "screw_seat": "csk",       # csk (countersunk, drywall bugle head) | pan (counterbore for a pan / wafer head)
    "screw_head_h": 2.5,       # pan: head height = counterbore depth
    "pilot_d": 2.8,            # pilot hole in the spine / stud
    "screw_min": 2,            # screws per holder, minimum
    "screw_max": 4,            # screws per holder, maximum (corners first)
    "no_supports": True,
    "orient": "auto",          # auto | face | side | upright | back
    "render_thread": False,
    "print_view": False,
    "brand_src": "none", "brand_text": "PEGBOARDLAB", "brand_font": "sans", "brand_bold": True,
    "brand_size": 0.0, "brand_depth": 0.6, "brand_mode": "recess", "brand_rot": 0.0,
    "brand_x": 0.0, "brand_y": 0.0, "brand_line": 1.2, "brand_svg": "", "brand_dual": False,
}
DEFAULTS.update(MT.PARAMS)
for _f in FAMILIES.values():
    DEFAULTS.update(_f.PARAMS)
for _k, _v in BD.BOARDS[DEFAULTS["board"]].items():
    if _k in BD.GEOM_KEYS:
        DEFAULTS[_k] = _v

GLOBAL_SCHEMA = [
    {"key": "board", "label": "Board", "type": "select", "group": "Board",
     "options": [(k, v["label"]) for k, v in BD.BOARDS.items()]},
    {"key": "hole_d", "label": "Hole Ø", "type": "slider", "min": 3, "max": 14, "step": 0.05, "group": "Board"},
    {"key": "t", "label": "Thickness", "type": "slider", "min": 1, "max": 30, "step": 0.5, "group": "Board"},
    {"key": "pitch_x", "label": "Pitch along a row", "type": "slider", "min": 10, "max": 60, "step": 0.01, "group": "Board"},
    {"key": "pitch_y", "label": "Row pitch", "type": "slider", "min": 5, "max": 60, "step": 0.01, "group": "Board"},
    {"key": "stagger", "label": "Row stagger", "type": "slider", "min": 0, "max": 30, "step": 0.01, "group": "Board"},
    {"key": "back", "label": "Clearance behind", "type": "slider", "min": 0, "max": 60, "step": 0.5, "group": "Board"},
    {"key": "material", "label": "Material", "type": "seg", "group": "Fit",
     "options": [(k, v["label"]) for k, v in F.MATERIALS.items()], "wrap": 2},
    {"key": "shrink", "label": "Print shrink (Ø)", "type": "slider", "min": -0.3, "max": 0.6, "step": 0.05, "group": "Fit"},
    {"key": "clear", "label": "Stud clearance", "type": "slider", "min": -0.3, "max": 1.0, "step": 0.05, "group": "Fit"},
    {"key": "stud_len", "label": "Stud length · board default", "type": "slider", "min": 3, "max": 30, "step": 0.5, "group": "Fit"},
    {"key": "family", "label": "Family", "type": "seg", "group": "Family",
     "options": [(k, v.LABEL) for k, v in FAMILIES.items()], "wrap": 4},
    {"key": "plate_t", "label": "Plate thickness", "type": "slider", "min": 2, "max": 12, "step": 0.5, "group": "Plate"},
    {"key": "plate_r", "label": "Corner radius", "type": "slider", "min": 0, "max": 15, "step": 0.5, "group": "Plate"},
    {"key": "plate_edge", "label": "Edge chamfer", "type": "slider", "min": 0, "max": 2, "step": 0.1, "group": "Plate"},
    {"key": "brand_src", "label": "Branding", "type": "seg", "group": "Branding",
     "options": [("none", "None"), ("text", "Text"), ("svg", "SVG")]},
    {"key": "brand_text", "label": "Text", "type": "text", "group": "Branding", "show": {"key": "brand_src", "in": ["text"]}},
    {"key": "brand_font", "label": "Font", "type": "seg", "group": "Branding",
     "options": [("sans", "Sans"), ("serif", "Serif"), ("mono", "Mono")], "show": {"key": "brand_src", "in": ["text"]}},
    {"key": "brand_bold", "label": "Bold", "type": "toggle", "group": "Branding", "show": {"key": "brand_src", "in": ["text"]}},
    {"key": "brand_svg", "label": "SVG", "type": "svg", "group": "Branding", "show": {"key": "brand_src", "in": ["svg"]}},
    {"key": "brand_mode", "label": "Mode", "type": "seg", "group": "Branding",
     "options": [("recess", "Recess"), ("emboss", "Emboss"), ("through", "Through")], "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_size", "label": "Size (0 = fit)", "type": "slider", "min": 0, "max": 60, "step": 0.5, "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_depth", "label": "Depth", "type": "slider", "min": 0.2, "max": 3, "step": 0.1, "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_rot", "label": "Rotation", "type": "slider", "min": -90, "max": 90, "step": 1, "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_x", "label": "Offset X", "type": "slider", "min": -60, "max": 60, "step": 0.5, "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_y", "label": "Offset Y", "type": "slider", "min": -60, "max": 60, "step": 0.5, "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "brand_line", "label": "Line spacing", "type": "slider", "min": 0.8, "max": 2, "step": 0.05, "group": "Branding", "show": {"key": "brand_src", "in": ["text"]}},
    {"key": "brand_dual", "label": "Two filaments (3MF parts)", "type": "toggle", "group": "Branding", "show": {"key": "brand_src", "in": ["text", "svg"]}},
    {"key": "split", "label": "Construction", "type": "seg", "group": "Two-part",
     "options": [("one", "One piece"), ("two", "Spine + holder · screws")]},
    {"key": "spine_t", "label": "Spine thickness (0 = auto)", "type": "slider", "min": 0, "max": 16, "step": 0.5, "group": "Two-part",
     "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_d", "label": "Screw Ø", "type": "slider", "min": 2.5, "max": 5, "step": 0.1, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_len", "label": "Screw length (overall)", "type": "slider", "min": 8, "max": 30, "step": 0.5, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_head", "label": "Head Ø", "type": "slider", "min": 5, "max": 12, "step": 0.1, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_seat", "label": "Head seat", "type": "seg", "group": "Two-part", "options": [("csk", "Countersunk"), ("pan", "Counterbored")],
     "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_head_h", "label": "Head height (counterbore depth)", "type": "slider", "min": 1, "max": 6, "step": 0.1, "group": "Two-part",
     "show": {"key": "screw_seat", "in": ["pan"]}},
    {"key": "pilot_d", "label": "Pilot Ø", "type": "slider", "min": 2, "max": 4, "step": 0.1, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_min", "label": "Screws minimum", "type": "slider", "min": 1, "max": 6, "step": 1, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "screw_max", "label": "Screws maximum", "type": "slider", "min": 1, "max": 12, "step": 1, "group": "Two-part", "show": {"key": "split", "in": ["two"]}},
    {"key": "no_supports", "label": "Design for no supports", "type": "toggle", "group": "Print"},
    {"key": "orient", "label": "Orientation", "type": "seg", "group": "Print",
     "options": [("auto", "Auto"), ("face", "Face"), ("side", "Side"), ("upright", "Upright"), ("back", "Back")], "wrap": 3},
    {"key": "render_thread", "label": "Render threads in preview", "type": "toggle", "group": "Print"},
    {"key": "print_view", "label": "Show print orientation", "type": "toggle", "group": "Print"},
]


def schema():
    out = list(GLOBAL_SCHEMA)
    # family groups follow the Family picker, mount after them
    fam_items = []
    for k, f in FAMILIES.items():
        for it in f.SCHEMA:
            it = dict(it)
            it["family"] = k
            fam_items.append(it)
    out = out[:out.index(next(i for i in out if i["key"] == "family")) + 1] + fam_items + MT.SCHEMA + \
        out[out.index(next(i for i in out if i["key"] == "plate_t")):]
    return out


def merge_params(raw):
    p = dict(DEFAULTS)
    for k, v in raw.items():
        if k not in p:
            continue
        d = p[k]
        if isinstance(d, list):
            if k.endswith("_spec"):                       # free text tokens, one per feature
                p[k] = [str(t).strip() for t in (v if isinstance(v, list) else str(v).replace(";", ",").split(",")) if str(t).strip()]
            else:
                p[k] = parse_list(v) if not (isinstance(v, list) and v and isinstance(v[0], dict)) else v
        elif isinstance(d, bool):
            p[k] = str(v).lower() in ("1", "true", "on", "yes")
        elif isinstance(d, int):
            try:
                p[k] = int(float(v))
            except ValueError:
                pass
        elif isinstance(d, float):
            try:
                p[k] = float(v)
            except ValueError:
                pass
        else:
            p[k] = v
    return p


def apply_board(p, key):
    b = BD.BOARDS[key]
    p["board"] = key
    for k in BD.GEOM_KEYS:
        p[k] = b[k]
    return p


def board_of(p):
    """The board the sliders describe (preset overridden by sliders)."""
    b = dict(BD.BOARDS.get(p["board"], BD.BOARDS["imperial_19"]))
    for k in BD.GEOM_KEYS:
        b[k] = float(p[k])
    return b


# ---------------------------------------------------------------- validation

def validate(p):
    errs = []
    if p["family"] not in FAMILIES:
        errs.append(f"Unknown family {p['family']}.")
        return errs
    b = board_of(p)
    if BD.stud_d(b) < 2.0:
        errs.append("Stud under Ø2: check hole Ø, clearance and shrink.")
    if BD.stud_d(b) > b["hole_d"] + 0.6:
        errs.append("Stud more than 0.6 over the hole Ø: that will not go in.")
    if float(p["plate_t"]) < 2.0:
        errs.append("Plate under 2 mm.")
    if p["orient"] not in G.ORIENTS and p["orient"] != "auto":
        errs.append("Unknown orientation.")
    fam = FAMILIES[p["family"]]
    if hasattr(fam, "validate"):
        errs += fam.validate(p)
    return errs


# ---------------------------------------------------------------- pipeline

def resolve_orient(p, fam):
    o = p["orient"]
    if o == "auto":
        o = fam.ORIENT.get("no_supports" if p["no_supports"] else "default", "side")
        if hasattr(fam, "orient_for"):
            o = fam.orient_for(p) or o
    return o


def has_plate(fam, p):
    pl = getattr(fam, "PLATE", True)
    return bool(pl(p)) if callable(pl) else bool(pl)


def make_ctx(p, export):
    b = board_of(p)
    fam = FAMILIES[p["family"]]
    orient = resolve_orient(p, fam)
    td = G.teardrop_dir(orient) if (p["no_supports"] and orient != "back") else None
    return dict(b=b, p=p, fam=fam, orient=orient, no_supports=bool(p["no_supports"]), td=td,
                stud_d=BD.stud_d(b), t=float(p["plate_t"]), export=export,
                render_thread=bool(p["render_thread"]), warns=[], derived={}, blockers=[], dims=[], notes={},
                mat=F.MATERIALS[p["material"]])


def make_plate(w, h, p, t=None, r=None):
    t = float(p["plate_t"]) if t is None else float(t)
    r = float(p["plate_r"]) if r is None else float(r)
    plate = G.rbox(-w / 2, w / 2, -h / 2, h / 2, 0, t, min(r, w / 2 - 0.1, h / 2 - 0.1))
    e = float(p["plate_edge"])
    if e > 0.05:
        plate = G.try_chamfer(plate, ">Z", min(e, t / 2 - 0.1))
    return plate


def free_band(rect, blockers):
    """Largest horizontal band of rect (cx, cy, w, h) free of circular blockers."""
    if rect is None:
        return None
    cx, cy, w, h = rect
    y0, y1 = cy - h / 2, cy + h / 2
    cuts = sorted((by - r, by + r) for bx, by, r in blockers if abs(bx - cx) < w / 2 + r)
    bands, start = [], y0
    for a, b in cuts:
        if a > start:
            bands.append((start, min(a, y1)))
        start = max(start, b)
    if start < y1:
        bands.append((start, y1))
    bands = [(a, b) for a, b in bands if b - a > 3]
    if not bands:
        return None
    a, b = max(bands, key=lambda ab: ab[1] - ab[0])
    return (cx, (a + b) / 2, w, b - a)


def build(p, export=False):
    ctx = make_ctx(p, export)
    fam, b = ctx["fam"], ctx["b"]
    spec = {"orient": ctx["orient"], "brand_solid": None}
    if not has_plate(fam, p):
        body = fam.build(p, ctx, None, None)
        spec["plan"] = dict(w=0, h=0, studs=[], anchor=(0, 0))
        spec["derived"] = ctx["derived"]
        spec["dims"] = ctx.get("dims") or DM.bbox_dims(body.val().BoundingBox())
        spec["notes"] = ctx.get("notes", {})
        return body, spec, ctx["warns"]
    want = fam.plan(p, ctx)
    q = MT.resolve(p, want)                 # mount controls on auto take the family's suggestion
    if q["mt_fix"] == "screw" and q["split"] == "two":
        q["split"] = "one"                  # screws go straight into the board: nothing for a spine to do
        ctx["warns"].append("Screw fixing: built in one piece, screwed straight to the board.")
    ctx["mount"] = q
    tm = max(float(want.get("t_min", 0)), MT.t_min(q))
    if tm > ctx["t"]:
        ctx["warns"].append(f"Plate thickened to {tm:.1f} (family / fixing minimum).")
        ctx["t"] = tm
    mp = MT.plan(q, b, want)
    suggested = q["mt_pattern"] != p["mt_pattern"] or q["mt_bars"] != p["mt_bars"]
    ctx["warns"] += [x for x in mp["warns"] if not (suggested and "to cover the pattern" in x)]
    w, h = mp["w"], mp["h"]
    ctx["w"], ctx["h"] = w, h
    if mp.get("bars"):
        spine_t = (float(q["spine_t"]) or 5.0) if q["split"] == "two" else 0.0
        plate = MT.twin_plate(mp, q, ctx["t"], spine_t)
        ctx["derived"]["bars"] = (f"twin · {mp['span']} pitches apart ({mp['bars'][1] - mp['bars'][0]:.1f}) · "
                                  f"bar {mp['bar_w']:.1f} × {h:.1f} · strip {mp['strip']:.0f} high")
    else:
        plate = make_plate(w, h, p, ctx["t"])
    body = fam.build(q, ctx, plate, mp)     # q: p with the resolved mount / split
    if q["split"] == "two":
        body = two_part(body, mp, q, ctx, spec, want)
    else:
        body = MT.apply(body, mp, q, ctx)
    # branding on the plate front
    rect = ctx.get("brand", want.get("brand"))
    if rect == "auto":
        rect = (0.0, 0.0, w, h)
    rect = free_band(rect, ctx["blockers"]) if rect else None
    if p["brand_src"] != "none":
        if rect is None:
            ctx["warns"].append("No free face for branding.")
        else:
            cx, cy, bw, bh = rect
            mode = p["brand_mode"]
            if mode == "emboss" and ctx["no_supports"] and ctx["orient"] == "face":
                ctx["warns"].append("Embossed branding would lift the face-down print off the bed: recessed instead.")
                mode = "recess"
            t = ctx["t"]
            depth = float(p["brand_depth"])
            art, info, bw_ = B.artwork(p, bw, bh, mirror=False, height=B.art_height(mode, depth, t))
            ctx["warns"] += bw_
            if art is not None:
                art = art.translate(cq.Vector(cx, cy, 0))
                if p["brand_dual"]:
                    placed = B.place(art, t, 1, mode, depth, t)
                    if mode == "emboss":
                        spec["brand_solid"] = placed.intersect(G.box(cx - bw, cx + bw, cy - bh, cy + bh, t, t + depth + 0.01).val())
                    elif mode == "through":
                        body = body.cut(cq.Workplane("XY").add(placed))
                        spec["brand_solid"] = placed.intersect(G.box(cx - bw, cx + bw, cy - bh, cy + bh, 0, t).val())
                    else:
                        body = body.cut(cq.Workplane("XY").add(placed))
                        spec["brand_solid"] = placed.intersect(G.box(cx - bw, cx + bw, cy - bh, cy + bh, t - depth, t).val())
                else:
                    body = B.apply(body, art, t, 1, mode, depth, t)
                ctx["derived"]["brand"] = f"{info.get('w', 0)} × {info.get('h', 0)} {mode}"
    spec["plan"] = mp
    spec["derived"] = ctx["derived"]
    spec["w"], spec["h"], spec["t"] = w, h, ctx["t"]
    spec["dims"] = dimensions(q, spec, body, ctx, want, mp)
    spec["notes"] = notes(q, spec, ctx, mp)
    return body, spec, ctx["warns"]


def dimensions(p, spec, body, ctx, want, mp):
    """Dimension lines for the assembly view, board frame (holder shifted by the spine)."""
    st = float(spec["spine_t"]) if spec.get("spine") is not None else 0.0
    bb = body.val().BoundingBox()
    t = ctx["t"]
    xmin, xmax, ymin, ymax = bb.xmin, bb.xmax, bb.ymin, bb.ymax
    zmax = bb.zmax + st
    dd = [DM.D((xmin, ymin, zmax), (xmax, ymin, zmax), (0, -8, 0), key="width"),
          DM.D((xmax, ymin, 0), (xmax, ymax, 0), (8, 0, 0), key="height"),
          DM.D((xmax, ymin, 0), (xmax, ymin, zmax), (0, -8, 0), key="depth")]
    if st > 0:
        dd.append(DM.D((xmax, ymax, 0), (xmax, ymax, st), (0, 8, 0), key="spine_t"))
        dd.append(DM.D((xmax, ymax, st), (xmax, ymax, st + t), (0, 17, 0), key="plate_t"))
    else:
        dd.append(DM.D((xmax, ymax, 0), (xmax, ymax, t), (0, 8, 0), key="plate_t"))
    studs = mp.get("studs") or []
    fix = p["mt_fix"]
    if studs and fix in ("plain", "thread", "tube", "insert"):
        d = ctx["stud_d"]
        L = MT.stud_len(p, ctx["b"])
        x, y = max(studs, key=lambda s_: (s_[0], -s_[1]))          # outer right, lowest: dims sit clear of the part
        oy = (ymin - 6) - y                                          # Ø line below the plate's bottom edge
        dd.append(DM.D((x - d / 2, y, -L), (x + d / 2, y, -L), (0, oy, 0), kind="dia", key="stud_d"))
        ox = (xmax + 6) - (x + d / 2)                                # length line beyond the plate's right edge
        dd.append(DM.D((x + d / 2, y, -L), (x + d / 2, y, 0), (ox, 0, 0), key="stud_len"))
        same = sorted(yy for xx, yy in studs if abs(xx - x) < 1e-6 and yy > y + 1e-6)
        if same:
            dd.append(DM.D((x, y, -L), (x, same[0], -L), (ox + d / 2 + 8, 0, 0), key="stud_pitch"))
    if mp.get("bars"):
        bx0, bx1 = mp["bars"]
        bw = mp["bar_w"]
        ztop = st + t
        dd.append(DM.D((bx0 - bw / 2, ymax, ztop), (bx0 + bw / 2, ymax, ztop), (0, 8, 0), key="bar_w"))
        dd.append(DM.D((bx0, ymax, ztop), (bx1, ymax, ztop), (0, 16, 0), key="bar_span"))
        dd.append(DM.D((xmin, ymin, ztop), (xmin, ymin + mp["strip"], ztop), (-8, 0, 0), key="strip"))
    fam_dims = ctx.get("dims") or []
    if fam_dims:
        dd += DM.shift(fam_dims, dz=st)
    else:
        keep = float(want.get("keepout", 0.0))
        if keep > 1:
            dd.append(DM.D((xmin, ymin, zmax), (xmin, ymin + keep, zmax), (-8, 0, 0), key="feature"))
    return dd


def print_dims(parts):
    """Bed footprints of the laid-out parts (print view)."""
    dd = []
    for name, sh in parts:
        if name in ("brand", "spine2"):
            continue
        dd += DM.bed_dims(sh.BoundingBox(), prefix=name + "_")
    return dd


def notes(p, spec, ctx, mp):
    """Per-control readouts in millimetres for controls that are counts or ratios."""
    n = dict(ctx.get("notes", {}))
    b = ctx["b"]
    rs = BD.row_step(b)
    bw = MT.bar_w(p, b)
    n["mt_margin"] = f"bar {bw:g} wide"
    sd = f"stud Ø{ctx['stud_d']:.2f}"
    n["hole_d"] = n["shrink"] = n["clear"] = sd
    n["stud_len"] = f"{MT.stud_len(p, b):g} mm"
    if mp.get("bars"):
        c = mp["bars"][1] - mp["bars"][0]
        n["mt_span"] = f"{mp['span']} × {rs:g} = {c:.1f} centres · {c - bw:.1f} between the bars"
        n["mt_rows"] = f"bars {spec['h']:.1f} tall"
        n["mt_strip"] = f"{mp['strip']:g} mm"
        n["mt_fill"] = f"filled to {mp['strip']:g} high" if p.get("mt_fill") == "plate" else f"strip {mp['strip']:g} high"
        fr = float(p.get("mt_fill_r") or 0) or float(p["plate_r"])
        n["mt_fill_r"] = f"r {fr:g}" + ("" if float(p.get("mt_fill_r") or 0) else " (the plate corner radius)")
        ft = float(p.get("mt_fill_t") or 0) or float(ctx["t"])
        n["mt_fill_t"] = f"{ft:g} thick" + ("" if float(p.get("mt_fill_t") or 0) else " (the flange)")
    else:
        n["mt_rows"] = f"plate {spec['h']:.1f} tall"
    if p["mt_fix"] == "screw":
        t = float(ctx["t"])
        Ls = float(p["mt_screw_len"])
        sd = float(p["mt_screw_d"])
        n["mt_screw_len"] = f"{Ls - t:.0f} in the board ({float(b['t']):g} thick)"
        n["mt_screw_d"] = f"head Ø{sd * 2 + 0.6:.1f} · clearance Ø{F.WOOD_SCREW.get(sd, sd + 0.5):g}"
    if p["mt_fix"] == "bore":
        bolt = int(p["mt_bolt"])
        if p["mt_bolt_from"] == "front":
            n["mt_head"] = f"M{bolt} head Ø{F.BOLT_HEAD.get(bolt, bolt * 1.8):g}"
        else:
            n["mt_nut"] = f"M{bolt} nut {F.NUT[bolt][0]:g} AF"
    return n


def screw_sites(mp, p, ctx, want):
    """Stud positions clear of the family's feature band: where the screws go."""
    h = ctx["h"]
    ko = float(want.get("keepout", 0.0))
    r = float(p["screw_head"]) / 2 + 1.0
    sites = [(x, y) for x, y in mp["studs"] if y - r > -h / 2 + ko]
    return sites


def pick_sites(sites, n_max):
    """Keep at most n_max sites: the ones nearest the corners of their spread first, then the rest spread out."""
    if len(sites) <= n_max:
        return sites
    xs, ys = [x for x, _ in sites], [y for _, y in sites]
    corners = [(min(xs), min(ys)), (max(xs), min(ys)), (min(xs), max(ys)), (max(xs), max(ys))]
    out = []
    for cx, cy in corners:
        best = min(sites, key=lambda s: (s[0] - cx) ** 2 + (s[1] - cy) ** 2)
        if best not in out:
            out.append(best)
    rest = [s_ for s_ in sites if s_ not in out]
    while len(out) < n_max and rest:
        far = max(rest, key=lambda s_: min((s_[0] - o[0]) ** 2 + (s_[1] - o[1]) ** 2 for o in out))
        out.append(far)
        rest.remove(far)
    return sorted(out[:n_max])


def two_part(holder, mp, p, ctx, spec, want):
    """
    Split the accessory: the SPINE is a plate with the studs (prints face
    down, round studs) and the HOLDER is the family body on a flange of the
    same footprint, screwed to the spine with countersunk drywall screws.

    Thick board (studs ≥ 3.6 over the pilot, board ≥ 12): the screws sit
    on the stud axes and run through flange + spine and on into the studs,
    expanding each stud in its hole as they go. Spine 5 mm.
    Thin board: the screws sit between the lattice holes and run through
    flange + spine and into the panel itself (tip ~2 mm proud behind), so
    they also lock the J-hooks / studs against unhooking. Spine 5 mm.
    """
    b = ctx["b"]
    w, h, t = ctx["w"], ctx["h"], ctx["t"]
    screw_d, L, head, pilot = float(p["screw_d"]), float(p["screw_len"]), float(p["screw_head"]), float(p["pilot_d"])
    engage = L - t                       # shank below the flange (head flush with the flange front)
    stud_ok = ctx["stud_d"] - pilot >= 3.6 and float(b["t"]) >= 12 and p["mt_fix"] in ("plain", "thread")
    spine_t = float(p["spine_t"]) or 5.0
    pilot_depth = engage + 0.5
    sites = screw_sites(mp, p, ctx, want)
    if not stud_ok:
        # between the holes: half a pitch along the row toward the plate centre, or a row up when the plate is narrow
        dx, dy = float(b["pitch_x"]) / 2, float(b["pitch_y"])
        r = head / 2 + 1.0
        ko = float(want.get("keepout", 0.0))
        moved = []
        bars = mp.get("bars")
        for x, y in mp["studs"]:          # all studs: the keepout is applied after the move
            cands = ((x, y + dy), (x, y - dy)) if bars else ((x + dx, y), (x - dx, y), (x, y + dy), (x, y - dy))
            for cand in cands:            # twin bars: only along the bar
                if -w / 2 + r <= cand[0] <= w / 2 - r and -h / 2 + ko + r <= cand[1] <= h / 2 - r:
                    moved.append((round(cand[0], 3), round(cand[1], 3)))
                    break
        sites = sorted(set(moved))
    sites = pick_sites(sites, int(p["screw_max"]))
    need = int(p["screw_min"])
    if len(sites) < need:
        ctx["warns"].append(f"Only {len(sites)} screw site(s) clear of the feature (wanted {need}): raise the plate or change the pattern.")
    # --- spine (twin bars: one single-column spine, printed twice, placed at mp["bars"])
    twin = bool(mp.get("bars"))
    if twin:
        smp = MT.bar_plan(mp)
        spine = make_plate(mp["bar_w"], h, p, spine_t, r=float(p.get("mt_fill_r") or 0) or None)   # the spine bars follow the fill radius
        x0 = mp["bars"][0]
        spine_sites = [(0.0, y) for x, y in sites if abs(x - x0) < 1e-6]
        spec["spine_xs"] = list(mp["bars"])
    else:
        smp = mp
        spine = make_plate(w, h, p, spine_t)
        spine_sites = sites
        spec["spine_xs"] = [0.0]
    sctx = dict(ctx, t=spine_t, td=None, derived={}, warns=[], blockers=[])
    spine = MT.apply(spine, smp, p, sctx)
    ctx["warns"] += sctx["warns"]
    for x, y in spine_sites:
        if stud_ok:
            spine = spine.cut(G.cyl(pilot / 2, spine_t - pilot_depth, spine_t + 1, x, y))
        else:
            spine = spine.cut(G.cyl(pilot / 2, -1, spine_t + 1, x, y))
        spine = G.try_chamfer(spine, cq.selectors.NearestToPointSelector((x + pilot / 2, y, spine_t)), 0.4)
    if twin:
        per = [len([1 for x, _ in sites if abs(x - bx) < 1e-6]) for bx in mp["bars"]]
        if min(per) < 1:
            ctx["warns"].append("A bar has no screw clear of the feature: raise the bars (rows) or lower the feature.")
        elif per[0] != per[1]:
            ctx["warns"].append("Uneven screws on the two bars.")
    # --- holder flange: countersunk holes (teardrop through-hole when the flange prints vertical)
    td = ctx["td"]
    for x, y in sites:
        thru = screw_d + 0.5
        if td is not None:
            holder = holder.cut(G.teardrop_hole(thru / 2, -1, t + 1, td, x, y))
        else:
            holder = holder.cut(G.cyl(thru / 2, -1, t + 1, x, y))
        csk_d = head + 0.6
        if p["screw_seat"] == "pan":
            holder = holder.cut(G.cyl(csk_d / 2, t - float(p["screw_head_h"]), t + 1, x, y))
        else:
            depth = (csk_d - thru) / 2                    # 90° countersink
            cone = (cq.Workplane("XY").workplane(offset=t + 0.01).center(x, y).circle(csk_d / 2)
                    .workplane(offset=-depth - 0.01).circle(thru / 2).loft())
            holder = holder.cut(cone)
        ctx["blockers"].append((x, y, csk_d / 2 + 0.8))
    if sites:
        x, y = sites[0]
        dd_ = ctx.setdefault("dims", [])
        dd_.append(DM.D((x - (screw_d + 0.5) / 2, y, t), (x + (screw_d + 0.5) / 2, y, t), (0, 0, 6), kind="dia", key="screw_hole"))
        dd_.append(DM.D((x - (head + 0.6) / 2, y, t), (x + (head + 0.6) / 2, y, t), (0, 0, 12), kind="dia", key="screw_head"))
        if len(sites) > 1:
            x2, y2 = sites[1]
            dd_.append(DM.D((x, y, t), (x2, y2, t), (0, 0, 18), key="screw_pitch"))
    spec["spine"] = spine
    spec["spine_t"] = spine_t
    spec["screws"] = sites
    d = ctx["derived"]
    d["construction"] = "two-part · spine + holder"
    d["screws"] = (f"{len(sites)} × Ø{screw_d:g} × {L:g} {'csk' if p['screw_seat'] == 'csk' else 'pan, counterbored ' + format(float(p['screw_head_h']), 'g')}, head Ø{head:g}"
                   + (f" · {len(sites) // 2} per bar" if twin else ""))
    sw = mp["bar_w"] if twin else w
    if stud_ok:
        d["spine"] = (f"{sw:.0f} × {h:.0f} × {spine_t:g} · pilot Ø{pilot:g} × {pilot_depth:.1f}: {pilot_depth - spine_t:.1f} into the studs"
                      + (" · print 2 (same part)" if twin else ""))
    else:
        proud = engage - spine_t - float(b["t"])
        tip = f"tip {proud:.1f} proud behind" if proud > 0 else f"{engage - spine_t:.1f} into the board"
        d["spine"] = (f"{sw:.0f} × {h:.0f} × {spine_t:g} · pilot Ø{pilot:g} through; screws bite the board, {tip}"
                      + (" · print 2 (same part)" if twin else ""))
        if proud > 0.5:
            ctx["warns"].append(f"Screw tips stand {proud:.1f} mm proud behind the panel: needs that clearance in the frame.")
    d["studs"] = sctx["derived"].get("studs")
    d["stud_d"] = sctx["derived"].get("stud_d")
    d["stud_len"] = sctx["derived"].get("stud_len")
    for k in ("j_pass", "bore"):
        if k in sctx["derived"]:
            d[k] = sctx["derived"][k]
    return holder


def spine_parts(spec):
    """The spine(s) in board coordinates: one, or the same single-column part at each bar."""
    sp = spec.get("spine")
    if sp is None:
        return []
    return [sp.translate((x, 0, 0)).val() for x in spec.get("spine_xs", [0.0])]


def assembly(body, spec):
    """Body (+ branding part, + spine(s) behind it) as one compound in board coordinates (STEP)."""
    parts = []
    sp = spec.get("spine")
    if sp is not None:
        parts += spine_parts(spec)
        parts.append(body.translate((0, 0, spec["spine_t"])).val())
        if spec.get("brand_solid") is not None:
            parts.append(spec["brand_solid"].translate(cq.Vector(0, 0, spec["spine_t"])))
    else:
        parts.append(body.val())
        if spec.get("brand_solid") is not None:
            parts.append(spec["brand_solid"])
    if len(parts) == 1:
        return body
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound(parts)])


def layout(obj, spec):
    return G.lay_out(obj, spec["orient"])


def context(p, spec, hole_pad=0.0):
    b = board_of(p)
    mp = spec["plan"]
    if not mp["studs"] and p["mt_ears"] == "none" and p["mt_pattern"] == "none":
        return None
    return MT.context_board(mp, b, spec.get("w", 40), spec.get("h", 40), hole_pad)


def context_key(p, spec):
    b = board_of(p)
    mp = spec["plan"]
    return "|".join(str(round(float(b[k]), 3)) for k in ("hole_d", "t", "pitch_x", "pitch_y", "stagger")) + \
        f"|{spec.get('w', 0):.1f}|{spec.get('h', 0):.1f}|{mp['anchor']}|{len(mp['studs'])}"


def derived(p, spec, laid=None):
    d = dict(spec.get("derived", {}))
    b = board_of(p)
    d["board"] = f"Ø{b['hole_d']:.2f} · {b['t']:.1f} thick · {b['pitch_x']:.2f} / {b['pitch_y']:.2f}"
    d["orient"] = G.ORIENTS[spec["orient"]][0] if spec.get("w") else "Flat · bottom face on the bed"
    d["plate"] = f"{spec.get('w', 0):.1f} × {spec.get('h', 0):.1f} × {spec.get('t', p['plate_t']):.1f}"
    if laid is not None:
        area, worst, low = G.overhang_audit(laid.val())
        d["overhang_mm2"] = area
        d["overhang_worst"] = worst
        net = area - float(d.get("bridges_mm2", 0))
        d["overhang_note"] = ("clean" if net < 60 else
                              "stud flats and small bridges" if net < 250 else
                              "check the print view: something faces down")
        if d.get("bridges_mm2"):
            d["overhang_note"] += f" · {d['bridges_mm2']} mm² of it is designed bridging (pocket / loop ceilings)"
        bb = laid.val().BoundingBox()
        d["print_size"] = f"{bb.xlen:.1f} × {bb.ylen:.1f} × {bb.zlen:.1f}"
        if spec.get("spine") is not None:
            sb = spec["spine"].val().BoundingBox()
            n = len(spec.get("spine_xs", [0.0]))
            d["print_size"] += f" + {n} × spine {sb.xlen:.1f} × {sb.ylen:.1f} × {sb.zlen:.1f}" if n > 1 else \
                f" + spine {sb.xlen:.1f} × {sb.ylen:.1f} × {sb.zlen:.1f}"
            d["volume_cm3"] = round((laid.val().Volume() + n * spec["spine"].val().Volume()) / 1000, 1)
        else:
            d["volume_cm3"] = round(laid.val().Volume() / 1000, 1)
    return d


def parts_for_export(body, spec):
    """[(name, shape)] in print orientation, branding second if present."""
    laid = layout(body, spec)
    out = [("base", laid.val())]
    bs = spec.get("brand_solid")
    if bs is not None:
        bl = G.lay_out(cq.Workplane("XY").add(bs), spec["orient"])
        # the brand part must share the base's translation: re-lay both from a common bbox
        comp = cq.Workplane("XY").newObject([cq.Compound.makeCompound([body.val(), bs])])
        both = G.lay_out(comp, spec["orient"])
        solids = both.solids().vals()
        # the base is the big one
        solids.sort(key=lambda s: -s.Volume())
        out = [("base", solids[0]), ("brand", cq.Compound.makeCompound(solids[1:]) if len(solids) > 2 else solids[1])]
    sp = spec.get("spine")
    if sp is not None:
        sl = G.lay_out(sp, "face")
        bb = laid.val().BoundingBox()
        sb = sl.val().BoundingBox()
        n = len(spec.get("spine_xs", [0.0]))
        out = [("holder" if nm == "base" else nm, sh) for nm, sh in out]
        for i in range(n):                                    # beside the holder on the bed, same part n times
            out.append(("spine" if n == 1 else f"spine{i + 1}", sl.translate((bb.xmax + 10.0 + i * (sb.xlen + 8.0), 0, 0)).val()))
    return out, laid
