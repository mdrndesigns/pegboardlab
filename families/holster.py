"""
HOLSTER - a U-saddle for a drill, driver or glue gun: two arms out from
the plate with a front bar, the tool's neck drops in from above. Also a
ring (closed loop) for spray cans, bottles and tape. Printed upright:
arms and bar sit on the bed.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog, cove

NAME = "holster"
LABEL = "Holster"
ORDER = 40
ORIENT = {"default": "upright", "no_supports": "upright"}

PARAMS = {
    "hs_type": "saddle",    # saddle | ring
    "hs_inner_w": 36.0,     # opening width (tool neck)
    "hs_inner_d": 40.0,     # opening depth out from the plate
    "hs_arm": 8.0,          # arm width (X) / bar thickness (Z)
    "hs_h": 25.0,           # arm height (Y)
    "hs_r": 6.0,            # inner corner radius
    "hs_flare": 3.0,        # entry chamfer at the top of the opening
    "hs_ring_d": 66.0,      # ring: inner Ø
    "hs_ph": 50.0,
}

SCHEMA = [
    seg("hs_type", "Type", [("saddle", "Saddle"), ("ring", "Ring")], "Holster"),
    sl("hs_inner_w", "Opening width", 10, 120, 1, "Holster", show={"key": "hs_type", "in": ["saddle"]}),
    sl("hs_inner_d", "Opening depth", 10, 120, 1, "Holster", show={"key": "hs_type", "in": ["saddle"]}),
    sl("hs_ring_d", "Ring inner Ø", 20, 150, 1, "Holster", show={"key": "hs_type", "in": ["ring"]}),
    sl("hs_arm", "Arm / bar width", 4, 20, 0.5, "Holster"),
    sl("hs_h", "Height", 6, 80, 1, "Holster"),
    sl("hs_r", "Inner corner radius", 0, 30, 0.5, "Holster", show={"key": "hs_type", "in": ["saddle"]}),
    sl("hs_flare", "Entry chamfer", 0, 8, 0.5, "Holster"),
    sl("hs_ph", "Plate height", 20, 160, 1, "Holster"),
]


def plan(p, ctx):
    a = float(p["hs_arm"])
    if p["hs_type"] == "ring":
        ow = float(p["hs_ring_d"]) + 2 * a
    else:
        ow = float(p["hs_inner_w"]) + 2 * a
    w = max(ow, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    return dict(w=w, h=float(p["hs_ph"]), brand="auto", keepout=float(p["hs_h"]) + 1)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    a, hh = float(p["hs_arm"]), float(p["hs_h"])
    yb = -h / 2
    fl = float(p["hs_flare"])
    if p["hs_type"] == "ring":
        ri = float(p["hs_ring_d"]) / 2
        ro = ri + a
        ring = G.cyl(ro, 0, hh).cut(G.cyl(ri, -1, hh + 1))            # axis Z
        ring = ring.rotate((0, 0, 0), (1, 0, 0), -90)                  # axis -> +Y, spans y in [0, hh]
        bb = ring.val().BoundingBox()
        ring = ring.translate((0, yb - bb.ymin, t0 + ro - 1.0))        # sunk 1 mm into the plate so it fuses
        neck = G.box(-ro * 0.6, ro * 0.6, yb, yb + hh, t0 - 0.01, t0 + ro)
        bore = G.cyl(ri, -1, hh + 2).rotate((0, 0, 0), (1, 0, 0), -90)
        bb2 = bore.val().BoundingBox()
        neck = neck.cut(bore.translate((0, yb - 1 - bb2.ymin, t0 + ro - 1.0)))
        body = plate.union(neck).union(ring)
        if fl > 0.3:
            body = G.try_chamfer(body, cq.selectors.NearestToPointSelector((0, yb + hh, t0 + ro - ri)), min(fl, a - 0.5))
        dd = ctx.setdefault("dims", [])
        zc_ = t0 + ro - 1.0
        dd.append(D((-ri, yb + hh, zc_), (ri, yb + hh, zc_), (0, 6, 0), kind="dia", key="ring_id"))
        dd.append(D((ri, yb + hh, zc_), (ro, yb + hh, zc_), (0, 6, 0), key="wall"))
        dd.append(D((ro, yb, zc_), (ro, yb + hh, zc_), (8, 0, 0), key="height"))
        ctx["derived"]["holster"] = f"ring Ø{2 * ri:g} inner, {a:g} wall, {hh:g} tall"
        ctx["brand"] = (0.0, (h / 2 + yb + hh) / 2, w, max(0.0, h / 2 - (yb + hh)))
        return body
    iw, idp, r = float(p["hs_inner_w"]), float(p["hs_inner_d"]), float(p["hs_r"])
    ow, od = iw + 2 * a, idp + a
    outer = G.box(-ow / 2, ow / 2, yb, yb + hh, t0 - 0.01, t0 + od)
    outer = G.try_fillet(outer, "|Y", min(r + a, ow / 2 - 0.1, od / 2 - 0.1))
    opening = G.box(-iw / 2, iw / 2, yb - 1, yb + hh + 1, t0 - 1, t0 + idp)
    opening = G.try_fillet(opening, cq.selectors.BoxSelector((-iw, yb - 2, t0 + idp - 1), (iw, yb + hh + 2, t0 + idp + 1)), min(r, iw / 2 - 0.1, idp - 0.1)) if r > 0.3 else opening
    saddle = outer.cut(opening)
    if fl > 0.3:
        # entry chamfer along the top inner edges
        saddle = G.try_chamfer(saddle, cq.selectors.BoxSelector((-iw / 2 - 0.5, yb + hh - 0.5, t0 - 0.5), (iw / 2 + 0.5, yb + hh + 0.5, t0 + idp + 0.5)), fl)
    body = plate.union(saddle)
    dd = ctx.setdefault("dims", [])
    dd.append(D((-iw / 2, yb + hh, t0 + od), (iw / 2, yb + hh, t0 + od), (0, 6, 0), key="opening_w"))
    dd.append(D((iw / 2, yb + hh, t0), (iw / 2, yb + hh, t0 + idp), (4, 6, 0), key="opening_d"))
    dd.append(D((iw / 2, yb + hh, t0 + od), (ow / 2, yb + hh, t0 + od), (0, 12, 0), key="arm"))
    dd.append(D((ow / 2, yb, t0 + od), (ow / 2, yb + hh, t0 + od), (8, 0, 0), key="height"))
    ctx["derived"]["holster"] = f"saddle {iw:g} × {idp:g} opening, arms {a:g}, {hh:g} tall"
    ctx["brand"] = (0.0, (h / 2 + yb + hh) / 2, w, max(0.0, h / 2 - (yb + hh)))
    return body
