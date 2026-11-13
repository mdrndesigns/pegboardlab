"""
STAND - a quick-draw comb for flat tools that stand edge-on: combination
spanners, flat files, rules. A shallow tray on the plate's bottom edge,
one channel per tool between a pair of thin fins, a low lip across the
front. The tool stands on its open end in its channel with the foot
against the lip and leans back on the board; nothing is threaded through
a slot, so it lifts straight out forward.

    Channels   "6, 6.5, 7.5" = channel widths (tool thickness + ~2)
               "6x19, 10x42" = width × foot length (how far the foot
               reaches front to back: the head width + ~3)

The front edge follows the foot lengths (short tools at one end, long at
the other), so every foot sits the same distance in front of its lip and
small tools do not lean further than large ones. Fins stop below the
lowest screw head unless set by hand. Prints upright: the floor on the
bed, every wall vertical.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, lst, web_cap, parse_list

NAME = "stand"
LABEL = "Stand"
ORDER = 21
ORIENT = {"default": "upright", "no_supports": "upright"}

# Wera Bicycle Set 12 (Joker 6003: 6-14, 15 pedal, 16, 17): channel width × foot length
WERA_BIKE_12 = [[6, 23], [6, 25], [6.5, 28], [6.5, 30], [7.5, 32], [7.5, 34],
                [8, 36], [8, 38], [8.5, 40], [7, 42], [9.5, 44], [10, 46]]

PARAMS = {
    "sd_slots": WERA_BIKE_12,   # per tool: width, or width × foot length
    "sd_len": 30.0,             # foot length for entries without one
    "sd_pitch": 18.0,           # channel centres
    "sd_fin_t": 2.4,
    "sd_fin_h": 0.0,            # fin height at the plate above the floor, 0 = auto (under the screws)
    "sd_lip": 12.0,             # front lip above the floor
    "sd_lip_t": 2.4,
    "sd_floor": 3.0,
    "sd_edge": 3.0,             # floor beyond the outer fins
    "sd_ph": 40.0,
}

SCHEMA = [
    lst("sd_slots", "Channels · width or width × foot length", "Stand", hint="e.g. 6x19, 7.5x28, 10x42"),
    sl("sd_len", "Foot length (entries without one)", 10, 80, 1, "Stand"),
    sl("sd_pitch", "Channel spacing", 10, 40, 0.5, "Stand"),
    sl("sd_fin_t", "Fin thickness", 1.6, 6, 0.2, "Stand"),
    sl("sd_fin_h", "Fin height at the plate (0 = auto, under the screws)", 0, 120, 1, "Stand"),
    sl("sd_lip", "Front lip height", 4, 40, 0.5, "Stand"),
    sl("sd_lip_t", "Lip thickness", 1.6, 6, 0.2, "Stand"),
    sl("sd_floor", "Floor thickness", 2, 8, 0.5, "Stand"),
    sl("sd_edge", "Floor beyond the outer fins", 0, 20, 0.5, "Stand"),
    sl("sd_ph", "Plate height (minimum)", 30, 160, 1, "Stand"),
]


def channels(p):
    """[(x, width, foot length)] centred on the plate."""
    out = []
    for v in parse_list(p.get("sd_slots")):
        if isinstance(v, (list, tuple)):
            out.append((float(v[0]), float(v[1])))
        else:
            out.append((float(v), float(p["sd_len"])))
    if not out:
        out = [(8.0, float(p["sd_len"]))]
    n, pitch = len(out), float(p["sd_pitch"])
    return [((i - (n - 1) / 2) * pitch, w, l) for i, (w, l) in enumerate(out)]


def field(p):
    ch = channels(p)
    ft = float(p["sd_fin_t"])
    x0 = ch[0][0] - ch[0][1] / 2 - ft - float(p["sd_edge"])
    x1 = ch[-1][0] + ch[-1][1] / 2 + ft + float(p["sd_edge"])
    return ch, 2 * max(-x0, x1)


def validate(p):
    errs = []
    ch = channels(p)
    worst = max(w for _, w, _ in ch) + 2 * float(p["sd_fin_t"])
    if worst > float(p["sd_pitch"]) + 1e-6:
        errs.append(f"Channel + fins ({worst:g}) wider than the spacing ({float(p['sd_pitch']):g}).")
    return errs


def plan(p, ctx):
    ch, fw = field(p)
    w = max(fw, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    return dict(w=w, h=float(p["sd_ph"]), brand=None, keepout=float(p["sd_floor"]) + 1.0,
                mount=dict(mt_bars="twin" if w >= 90 else "plate", mt_pattern="grid", mt_cols=1, mt_rows=3))


def _depth_at(x, pts):
    """Front line depth at x: linear between the channel centres, flat beyond the ends."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (xa, da), (xb, db) in zip(pts, pts[1:]):
        if x <= xb:
            return da + (db - da) * (x - xa) / (xb - xa)
    return pts[-1][1]


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    yb = -h / 2
    ch, _ = field(p)
    ft, lt = float(p["sd_fin_t"]), float(p["sd_lip_t"])
    fl, lip = float(p["sd_floor"]), float(p["sd_lip"])
    yf = yb + fl
    pts = [(x, l + lt + 1.0) for x, _, l in ch]              # tray depth at each channel: foot + 1 + lip
    dep = lambda x: _depth_at(x, pts)

    def outline(shift):
        mid = [(x, t0 + d - shift) for x, d in pts]
        return [(-w / 2, t0 - 0.01), (-w / 2, t0 + dep(-w / 2) - shift)] + mid + [(w / 2, t0 + dep(w / 2) - shift), (w / 2, t0 - 0.01)]

    def prism(shift, y0, y1):
        # XZ polygon extruded along Y (workplane XZ extrudes toward -Y)
        return cq.Workplane("XZ").polyline(outline(shift)).close().extrude(-(y1 - y0)).translate((0, y0, 0))

    tub = prism(0.0, yb, yf + lip).cut(prism(lt, yf, yf + lip + 1.0))
    body = plate.union(tub)

    # fins: auto height stops under the lowest screw head
    fh = float(p["sd_fin_h"])
    cap = web_cap(mp, p, yf)
    if fh <= 0:
        fh = max(lip, (cap - yf) if cap is not None else h - fl - 4.0)
    elif cap is not None and fh > cap - yf + 1e-6:
        ctx["warns"].append(f"Fins {fh:g} high cover a screw head: {cap - yf:.1f} is the most that clears it.")
    fh = min(fh, h - fl - 2.0)
    for x, cw, _ in ch:
        for s in (-1, 1):
            xf = x + s * (cw / 2 + ft / 2)
            zf = t0 + min(dep(xf - ft / 2), dep(xf + ft / 2)) - lt + 0.2
            prof = [(yf - 0.01, t0 - 0.01), (yf + fh, t0 - 0.01), (yf + fh, t0 + 3.0), (yf + lip, zf), (yf - 0.01, zf)]
            fin = cq.Workplane("YZ").polyline(prof).close().extrude(ft / 2, both=True).translate((xf, 0, 0))
            body = body.union(fin)

    # dimensions
    dd = ctx.setdefault("dims", [])
    xa, wa, la = ch[0]
    xz, wz, lz = ch[-1]
    ytop = yf + lip
    dd.append(D((xa - wa / 2, ytop, t0 + dep(xa)), (xa + wa / 2, ytop, t0 + dep(xa)), (0, 6, 0), key="slot_a"))
    dd.append(D((xz - wz / 2, ytop, t0 + dep(xz)), (xz + wz / 2, ytop, t0 + dep(xz)), (0, 6, 0), key="slot_z"))
    if len(ch) > 1:
        dd.append(D((ch[0][0], ytop, t0 + dep(ch[0][0])), (ch[1][0], ytop, t0 + dep(ch[1][0])), (0, 13, 0), key="pitch"))
    dd.append(D((-w / 2, yb, t0), (-w / 2, yb, t0 + dep(-w / 2)), (-8, 0, 0), key="depth_a"))
    dd.append(D((w / 2, yb, t0), (w / 2, yb, t0 + dep(w / 2)), (16, 0, 0), key="depth_z"))
    dd.append(D((-w / 2, yf, t0 + dep(-w / 2)), (-w / 2, ytop, t0 + dep(-w / 2)), (-8, 0, 0), key="lip"))
    dd.append(D((-w / 2, yf, t0), (-w / 2, yf + fh, t0), (-16, 0, 0), key="fin_h"))
    ctx.setdefault("notes", {}).update({
        "sd_slots": f"{len(ch)} channels · " + ", ".join(f"{cw:g}×{l:g}" for _, cw, l in ch),
        "sd_pitch": f"{len(ch)} × {float(p['sd_pitch']):g} = {len(ch) * float(p['sd_pitch']):g} · {float(p['sd_pitch']) - max(c[1] for c in ch) - 2 * ft:.1f} min between fins",
        "sd_fin_h": f"{fh:.1f} high" + ("" if float(p["sd_fin_h"]) else " (under the screw heads)"),
    })
    ctx["derived"]["stand"] = (f"{len(ch)} channels at {float(p['sd_pitch']):g} · tray {w:.0f} wide, {dep(-w / 2):.0f} → {dep(w / 2):.0f} deep · "
                               f"lip {lip:g} · fins {fh:.1f}")
    ctx["brand"] = None
    return body
