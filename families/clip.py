"""
CLIP - wire and cable keepers on a block: snap-in C channels, closed
loops, or an open comb. Wires run along X. Prints on its side so each
channel is a vertical hole with its mouth facing out.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog

NAME = "clip"
LABEL = "Clip"
ORDER = 50
ORIENT = {"default": "side", "no_supports": "side"}

PARAMS = {
    "cl_type": "snap",      # snap | loop | comb
    "cl_wire": "round",     # round | flat
    "cl_d": 5.0,            # wire Ø / flat cable thickness
    "cl_w": 12.0,           # flat cable width
    "cl_n": 3,
    "cl_wall": 2.0,
    "cl_snap": 0.6,         # snap lip per side at the mouth
    "cl_len": 16.0,         # block length along the wire (X)
    "cl_ph": 0.0,           # plate height, 0 = auto
}

SCHEMA = [
    seg("cl_type", "Type", [("snap", "Snap"), ("loop", "Loop"), ("comb", "Comb")], "Clip"),
    seg("cl_wire", "Wire", [("round", "Round"), ("flat", "Flat")], "Clip"),
    sl("cl_d", "Wire Ø / cable thickness", 1, 30, 0.5, "Clip"),
    sl("cl_w", "Flat cable width", 3, 60, 0.5, "Clip", show={"key": "cl_wire", "in": ["flat"]}),
    sl("cl_n", "Count", 1, 10, 1, "Clip"),
    sl("cl_wall", "Wall", 1.2, 5, 0.2, "Clip"),
    sl("cl_snap", "Snap lip per side", 0, 2, 0.1, "Clip", show={"key": "cl_type", "in": ["snap"]}),
    sl("cl_len", "Block length", 6, 60, 1, "Clip"),
    sl("cl_ph", "Plate height (0 = auto)", 0, 200, 1, "Clip"),
]


def pitch(p):
    d = float(p["cl_d"]) if p["cl_wire"] == "round" else float(p["cl_d"])
    return d + 2 * float(p["cl_wall"])


def plan(p, ctx):
    n = int(p["cl_n"])
    hh = n * pitch(p) + 2 * float(p["cl_wall"])
    w = max(float(p["cl_len"]), ctx["stud_d"] + 2 * float(p["mt_margin"]))
    h = float(p["cl_ph"]) or max(hh + 10, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    return dict(w=w, h=h, brand=None, keepout=hh + 2 * float(p["cl_wall"]) + 1)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    k, wire = p["cl_type"], p["cl_wire"]
    d, cw, wall, n = float(p["cl_d"]), float(p["cl_w"]), float(p["cl_wall"]), int(p["cl_n"])
    L = w                      # the block spans the plate so nothing overhangs on its side
    snap = float(p["cl_snap"]) if k == "snap" else 0.0
    pt = pitch(p)
    depth = (d if wire == "round" else cw) + wall + (snap + wall if k != "comb" else 0)
    hh = n * pt + wall
    yb = -h / 2
    block = G.box(-L / 2, L / 2, yb, yb + hh + wall, t0 - 0.01, t0 + depth)
    body = plate.union(block)
    clear = ctx["mat"]["snap"]
    for i in range(n):
        yc = yb + wall + (i + 0.5) * pt
        if wire == "round":
            zc = t0 + wall + d / 2
            body = body.cut(cq.Workplane("YZ").center(yc, zc).circle(d / 2 + clear / 2).extrude(L + 2, both=True))
            if k == "comb":
                body = body.cut(G.box(-L - 1, L + 1, yc - d / 2 - clear / 2, yc + d / 2 + clear / 2, zc, t0 + depth + 1))
            elif k == "snap":
                body = body.cut(G.box(-L - 1, L + 1, yc - d / 2 + snap, yc + d / 2 - snap, zc, t0 + depth + 1))
                body = G.try_chamfer(body, cq.selectors.BoxSelector((-L - 2, yc - d / 2 - 1, t0 + depth - 0.5), (L + 2, yc + d / 2 + 1, t0 + depth + 0.5)), min(0.6, snap))
        else:
            zc = t0 + wall + cw / 2
            body = body.cut(G.box(-L - 1, L + 1, yc - d / 2 - clear / 2, yc + d / 2 + clear / 2, zc - cw / 2 - clear / 2, zc + cw / 2 + clear / 2))
            if k == "comb":
                body = body.cut(G.box(-L - 1, L + 1, yc - d / 2 - clear / 2, yc + d / 2 + clear / 2, zc, t0 + depth + 1))
            elif k == "snap":
                body = body.cut(G.box(-L - 1, L + 1, yc - d / 2 + snap, yc + d / 2 - snap, zc, t0 + depth + 1))
    dd = ctx.setdefault("dims", [])
    yc0 = yb + wall + 0.5 * pt
    zc0 = t0 + wall + (d / 2 if wire == "round" else cw / 2)
    dd.append(D((L / 2, yc0 - d / 2, zc0), (L / 2, yc0 + d / 2, zc0), (8, 0, 0), kind="dia" if wire == "round" else None, key="wire"))
    if wire == "flat":
        dd.append(D((L / 2, yc0, zc0 - cw / 2), (L / 2, yc0, zc0 + cw / 2), (8, 0, 0), key="cable_w"))
    if n > 1:
        dd.append(D((L / 2, yc0, zc0), (L / 2, yc0 + pt, zc0), (16, 0, 0), key="pitch"))
    dd.append(D((L / 2, yb + hh + wall, t0), (L / 2, yb + hh + wall, t0 + depth), (0, 6, 0), key="depth"))
    if snap > 0.05:
        dd.append(D((L / 2, yc0 - d / 2, t0 + depth), (L / 2, yc0 - d / 2 + snap, t0 + depth), (0, 0, 6), key="snap"))
    ctx["derived"]["clip"] = f"{k} · {n} × {wire} {d:g}" + (f" × {cw:g}" if wire == "flat" else "")
    ctx["brand"] = (0.0, (h / 2 + yb + hh + wall) / 2, w, max(0.0, h / 2 - (yb + hh + wall)))
    return body
