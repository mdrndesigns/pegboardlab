"""
RACK - a shelf on the plate's bottom edge with holes, slots or pockets.

    drivers   round through-holes (screwdrivers, markers, files)
    pens      smaller round through-holes in two staggered rows
    hexkeys   one hole per key, 1.5 to 10 mm, ascending
    drills    graduated holes for a drill set, ascending
    bits      blind 1/4 in hex pockets, grid (driver bits)
    wrenches  open slots from the front edge, handles drop in
    chisels   through slots across the shelf (blades hang)
    pliers    one long window, handles through, jaws on the rails
    sockets   round blind pockets for socket squares (posts option off)

Printed upright: the shelf's underside is on the bed, every hole is
vertical. A cove at the plate joint stiffens it without overhangs.

The shelf spans the whole backing (plate or twin bars) so the end webs
sit flush with the ends; the webs stop below the lowest stud above the
shelf, clear of the screw heads. `Sizes` lists a width / Ø per feature
(e.g. "4.5, 4.5, 6, 8, 10") and overrides the single slider; with
`Pitch` on auto the features are packed with the edge margin between
them, so mixed sizes stay evenly spaced.
"""

import math

import cadquery as cq

import fasteners as F
import geometry as G
from dims import D, group_cuts
from families._lib import sl, seg, tog, lst, cove, web_cap, parse_list, web_params, end_webs

NAME = "rack"
LABEL = "Rack"
ORDER = 20
ORIENT = {"default": "upright", "no_supports": "upright"}

PARAMS = {
    "rk_type": "drivers",
    "rk_n": 5,
    "rk_pitch": 0.0,        # 0 = auto from the feature size
    "rk_d": 9.0,            # hole Ø / slot width / pocket size
    "rk_sizes": [],         # per-feature width / Ø, overrides rk_d (and the count)
    "rk_depth": 30.0,       # shelf depth out from the plate
    "rk_t": 8.0,            # shelf thickness
    "rk_margin": 6.0,       # shelf material around the features
    "rk_rows": 1,           # bits / pens: rows
    "rk_pocket": 10.0,      # blind pocket depth (bits, sockets)
    "rk_slot_len": 0.0,     # wrenches / pliers slot length, 0 = auto
    "rk_slot_t": 8.0,       # chisels: slot thickness (blade + clearance), the slot is d wide across
    "rk_cove": 4.0,
    "rk_lip": 0.0,          # front lip rise (keeps things from rolling off), 0 = none
    "rk_ph": 40.0,          # plate height above the shelf
    "rk_webs": True,        # end braces above the shelf, flush with the ends
}
_wp, _ws = web_params("rk_", "Rack")
PARAMS.update(_wp)

SCHEMA = [
    seg("rk_type", "Type", [("drivers", "Drivers"), ("pens", "Pens"), ("hexkeys", "Hex keys"), ("drills", "Drills"),
                            ("bits", "Bits"), ("wrenches", "Wrenches"), ("chisels", "Chisels"), ("pliers", "Pliers"),
                            ("sockets", "Sockets")], "Rack", wrap=3),
    sl("rk_n", "Count", 1, 24, 1, "Rack", show={"key": "rk_type", "not": ["hexkeys", "drills", "pliers"]}),
    sl("rk_rows", "Rows", 1, 4, 1, "Rack", show={"key": "rk_type", "in": ["bits", "pens", "sockets"]}),
    sl("rk_d", "Hole Ø / slot width (all)", 3, 40, 0.5, "Rack", show={"key": "rk_type", "not": ["hexkeys", "drills", "bits"]}),
    lst("rk_sizes", "Sizes · one per feature", "Rack", show={"key": "rk_type", "not": ["bits", "pliers"]},
        hint="e.g. 4.5, 4.5, 6, 8, 10 · blank = the slider"),
    sl("rk_pitch", "Pitch (0 = auto)", 0, 60, 0.5, "Rack"),
    sl("rk_depth", "Shelf depth", 10, 120, 1, "Rack"),
    sl("rk_t", "Shelf thickness", 3, 30, 0.5, "Rack"),
    sl("rk_pocket", "Pocket depth", 3, 30, 0.5, "Rack", show={"key": "rk_type", "in": ["bits", "sockets"]}),
    sl("rk_slot_len", "Slot length (0 = auto)", 0, 100, 1, "Rack", show={"key": "rk_type", "in": ["wrenches", "pliers"]}),
    sl("rk_slot_t", "Blade slot thickness", 3, 30, 0.5, "Rack", show={"key": "rk_type", "in": ["chisels"]}),
    sl("rk_margin", "Edge margin", 2, 20, 0.5, "Rack"),
    sl("rk_lip", "Front lip (0 = none)", 0, 20, 0.5, "Rack"),
    sl("rk_cove", "Cove at the plate", 0, 15, 0.5, "Rack"),
    tog("rk_webs", "End braces", "Rack"),
] + _ws + [
    sl("rk_ph", "Plate height above shelf", 15, 150, 1, "Rack"),
]


def sizes_of(p):
    """Per-feature sizes along the shelf: the Sizes list if given, else the type's table or the slider."""
    k = p["rk_type"]
    lst_ = [float(v) if not isinstance(v, (list, tuple)) else float(v[0]) for v in parse_list(p.get("rk_sizes"))]
    if lst_ and k not in ("bits", "pliers"):
        return lst_
    n = int(p["rk_n"])
    d = float(p["rk_d"])
    if k == "hexkeys":
        return [s * 1.155 + 1.2 for s in F.HEX_KEYS]
    if k == "drills":
        return [s + 0.6 for s in F.DRILL_SET]
    return [d] * n


def spread(sizes, pitch, gap):
    """Centres along X: a fixed pitch, or packed with `gap` between neighbouring features, centred."""
    if not sizes:
        return []
    if pitch > 0:
        n = len(sizes)
        return [(i - (n - 1) / 2) * pitch for i in range(n)]
    xs, x = [], 0.0
    for i, s in enumerate(sizes):
        if i:
            x += sizes[i - 1] / 2 + gap + s / 2
        xs.append(x)
    c = (xs[0] + xs[-1]) / 2
    return [v - c for v in xs]


def features(p):
    """[(dx, dz, kind, size)] relative to the shelf centre, kind: hole | hex | slot | slot_open | window."""
    k = p["rk_type"]
    n = int(p["rk_n"])
    d = float(p["rk_d"])
    pitch = float(p["rk_pitch"])
    rows = int(p["rk_rows"])
    m = float(p["rk_margin"])
    sizes = sizes_of(p)
    out = []
    if k in ("drivers", "pens", "sockets"):
        rows = rows if k in ("pens", "sockets") else 1
        gap = 6.0 if k == "drivers" else 4.0
        xs = spread(sizes, pitch, gap)
        pt = pitch or (max(sizes) + gap)
        rp = pt * (0.87 if k == "pens" else 1.0)
        for r in range(rows):
            off = (pt / 2 if (k == "pens" and r % 2) else 0.0)
            for x, s in zip(xs, sizes):
                out.append((x + off, (r - (rows - 1) / 2) * rp, "hole", s))
    elif k in ("hexkeys", "drills"):
        xs = spread(sizes, pitch, 14.0 - max(sizes) if k == "hexkeys" and not pitch and len(sizes) == len(F.HEX_KEYS) else m)
        if k == "hexkeys" and not pitch and len(sizes) == len(F.HEX_KEYS):
            xs = [(i - (len(sizes) - 1) / 2) * 14.0 for i in range(len(sizes))]
        if k == "drills" and not pitch and len(sizes) == len(F.DRILL_SET):
            xs = [(i - (len(sizes) - 1) / 2) * 11.0 for i in range(len(sizes))]
        for x, s in zip(xs, sizes):
            out.append((x, 0.0, "hole", s))
    elif k == "bits":
        pt = pitch or 11.0
        for r in range(rows):
            for i in range(n):
                out.append(((i - (n - 1) / 2) * pt, (r - (rows - 1) / 2) * pt, "hex", F.BIT_HEX))
    elif k == "wrenches":
        xs = spread(sizes, pitch, m)
        for x, s in zip(xs, sizes):
            out.append((x, 0.0, "slot_open", s))
    elif k == "chisels":
        tt = float(p["rk_slot_t"])
        xs = spread(sizes, pitch, tt + 8.0)
        for x, s in zip(xs, sizes):
            out.append((x, 0.0, "slot", s))
    elif k == "pliers":
        out.append((0.0, 0.0, "window", d))
    return out


def shelf_size(p, ctx, feats):
    m = float(p["rk_margin"])
    k = p["rk_type"]
    if feats:
        if k == "pliers":
            w = float(p["rk_slot_len"]) or 60.0
            w += 2 * m
        else:
            w = max(f[0] + f[3] / 2 for f in feats) - min(f[0] - f[3] / 2 for f in feats) + 2 * m
    else:
        w = 40.0
    return max(w, 20.0), float(p["rk_depth"])


def plan(p, ctx):
    feats = features(p)
    w, depth = shelf_size(p, ctx, feats)
    w = max(w, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    h = float(p["rk_ph"]) + float(p["rk_t"])
    return dict(w=w, h=h, brand="auto", keepout=float(p["rk_t"]) + float(p["rk_cove"]) + 1)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    k = p["rk_type"]
    feats = features(p)
    _, depth = shelf_size(p, ctx, feats)
    sw = w                               # the shelf spans the whole backing: webs flush with the ends
    st = float(p["rk_t"])
    yb = -h / 2
    ns = ctx["no_supports"]
    mat = ctx["mat"]
    shelf = G.box(-sw / 2, sw / 2, yb, yb + st, t0 - 0.01, t0 + depth)
    shelf = G.try_fillet(shelf, "|Y", min(3.0, st / 2))
    body = plate.union(shelf)
    lip = float(p["rk_lip"])
    if lip > 0.05:
        body = body.union(G.box(-sw / 2, sw / 2, yb, yb + st + lip, t0 + depth - 2.0, t0 + depth))
    cv = float(p["rk_cove"])
    if cv > 0.3:
        body = body.union(cove(sw - 0.02, min(cv, depth / 2), t0, yb + st))
    body, web_rise, web_run, web_t = end_webs(body, p, "rk_", mp, sw, yb + st, t0, depth, float(p["rk_ph"]), ctx)
    # features: cut vertically (along Y) through / into the shelf
    zc = t0 + depth / 2 + (2.0 if k in ("wrenches",) else 0.0)
    pocket = float(p["rk_pocket"])
    hole_clear = mat["hole"]
    for dx, dz, kind, size in feats:
        x, z = dx, zc + dz
        if kind == "hole":
            r = size / 2 + hole_clear
            if k == "sockets":      # blind pocket open at the shelf top
                body = body.cut(cq.Workplane("XZ").center(x, z).circle(r).extrude(-(pocket + 1))
                                .translate((0, yb + st - pocket, 0)))
            else:                   # through
                body = body.cut(cq.Workplane("XZ").center(x, z).circle(r).extrude(-(st + 2)).translate((0, yb - 1, 0)))
        elif kind == "hex":
            hx = (cq.Workplane("XZ").center(x, z).polygon(6, F.across_corners(size + mat["hex"]))
                  .extrude(-(pocket + 1)).translate((0, yb + st - pocket, 0)))
            body = body.cut(hx)
        elif kind == "slot":          # chisel blade: `size` wide across X, rk_slot_t thick along Z
            tt = float(p["rk_slot_t"]) + hole_clear
            body = body.cut(cq.Workplane("XZ").center(x, z).slot2D(size + hole_clear + tt, tt, 0)
                            .extrude(-(st + 2)).translate((0, yb - 1, 0)))
        elif kind == "slot_open":
            L = float(p["rk_slot_len"]) or depth * 0.6
            body = body.cut(cq.Workplane("XZ").center(x, t0 + depth - L / 2 + size / 2)
                            .slot2D(L + size, size + hole_clear, 90).extrude(-(st + 2)).translate((0, yb - 1, 0)))
        elif kind == "window":
            L = float(p["rk_slot_len"]) or 60.0
            body = body.cut(cq.Workplane("XZ").center(0, t0 + depth / 2).slot2D(L, size + hole_clear, 0)
                            .extrude(-(st + 2)).translate((0, yb - 1, 0)))
    # dimensions
    dd = ctx.setdefault("dims", [])
    ytop = yb + st
    zf = t0 + depth
    dd.append(D((sw / 2, ytop, t0), (sw / 2, ytop, zf), (8, 0, 0), key="shelf_d"))
    dd.append(D((sw / 2, yb, zf), (sw / 2, ytop, zf), (8, 0, 0), key="shelf_t"))
    if web_rise:
        dd.append(D((-sw / 2, ytop, t0), (-sw / 2, ytop + web_rise, t0), (-8, 0, 0), key="web"))
        dd.append(D((-sw / 2, ytop, t0), (-sw / 2, ytop, t0 + web_run), (-8, -6, 0), key="web_run"))
        dd.append(D((-sw / 2, ytop, t0 + web_run), (-sw / 2 + web_t, ytop, t0 + web_run), (0, 0, 6), key="web_t"))
    if lip > 0.05:
        dd.append(D((-sw / 2, ytop, zf), (-sw / 2, ytop + lip, zf), (-8, 0, 0), key="lip"))
    L_open = float(p["rk_slot_len"]) or depth * 0.6
    firsts, pitches = group_cuts([dict(kind=kd, x=dx, z=zc + dz, w=sz) for dx, dz, kd, sz in feats],
                                 lambda c: (c["kind"], round(c["w"], 2)))
    for c in firsts:
        x, z, sz, kd = c["x"], c["z"], c["w"], c["kind"]
        if kd == "hole":
            dd.append(D((x - sz / 2, ytop, z), (x + sz / 2, ytop, z), (0, 6, 0), kind="dia", key="hole"))
            if k == "sockets":
                dd.append(D((x + sz / 2, ytop - pocket, z), (x + sz / 2, ytop, z), (0, 0, sz / 2 + 4), key="pocket"))
        elif kd == "hex":
            dd.append(D((x - sz / 2, ytop, z), (x + sz / 2, ytop, z), (0, 6, 0), label=f"⬡{sz:g}", key="hex"))
            dd.append(D((x + sz / 2, ytop - pocket, z), (x + sz / 2, ytop, z), (0, 0, sz / 2 + 4), key="pocket"))
        elif kd == "slot":
            tt = float(p["rk_slot_t"])
            dd.append(D((x - sz / 2 - tt / 2, ytop, z), (x + sz / 2 + tt / 2, ytop, z), (0, 6, 0), key="slot_w"))
            dd.append(D((x, ytop, z - tt / 2), (x, ytop, z + tt / 2), (-(sz / 2 + tt / 2 + 4), 4, 0), key="slot_t"))
        elif kd == "slot_open":
            dd.append(D((x - sz / 2, ytop, zf), (x + sz / 2, ytop, zf), (0, 6, 0), key="slot_w"))
            dd.append(D((x + sz / 2, ytop, zf - L_open), (x + sz / 2, ytop, zf), (4, 4, 0), key="slot_l"))
        elif kd == "window":
            Lw = float(p["rk_slot_len"]) or 60.0
            dd.append(D((x - Lw / 2, ytop, z), (x + Lw / 2, ytop, z), (0, 6, 0), key="window_l"))
            dd.append(D((x + Lw / 2, ytop, z - sz / 2), (x + Lw / 2, ytop, z + sz / 2), (4, 4, 0), key="window_w"))
    for c0, c1 in pitches:
        zz = zf if c0["kind"] == "slot_open" else c0["z"]
        dd.append(D((c0["x"], ytop, zz), (c1["x"], ytop, zz), (0, 12, 0), key="pitch"))
    ctx.setdefault("notes", {}).update({"rk_n": f"shelf {sw:.1f} wide", "rk_sizes": f"{len(feats)} features" + ("" if not p.get("rk_sizes") else " from the list"),
                                        "rk_pitch": "packed, margin between" if not float(p["rk_pitch"]) else f"{float(p['rk_pitch']):g} centres"})
    ctx["derived"]["rack"] = f"{k} · {len(feats)} features · shelf {sw:.0f} × {depth:g} × {st:g}"
    ctx["brand"] = (0.0, (h / 2 + yb + st + (cv if cv > 0.3 else 0)) / 2, w, h / 2 - (yb + st + (cv if cv > 0.3 else 0)))
    return body
