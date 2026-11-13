"""
GRIDFINITY - a shelf with Gridfinity baseplate sockets so any bin from
MakerWorld / Printables sits on the pegboard. nx × ny units of 42 mm,
socket profile 2.15 / 1.8 / 0.7 (4.65 deep), corner R4, magnet pockets
Ø6.5 × 2.4 at 8 mm from the socket sides, M3 screw holes. Tilt leans
the bins back against the plate (a wedge fills under the shelf so it
still prints upright without supports). A front lip keeps them in.
"""

import math

import cadquery as cq

import fasteners as F
import geometry as G
from dims import D
from families._lib import sl, seg, tog, cove, web_cap, web_params, end_webs

NAME = "gridfinity"
LABEL = "Gridfinity"
ORDER = 80
ORIENT = {"default": "upright", "no_supports": "upright"}
GF = F.GRIDFINITY

PARAMS = {
    "gf_nx": 2,             # units along the plate
    "gf_ny": 1,             # units out from the plate
    "gf_rim": 2.0,          # shelf beyond the grid, per side
    "gf_t": 6.5,            # shelf thickness (sockets 4.65 + floor)
    "gf_tilt": 0.0,
    "gf_lip": 0.0,          # front lip height above the shelf, 0 = none
    "gf_magnets": False,
    "gf_screws": False,
    "gf_webs": True,
    "gf_ph": 50.0,          # plate above the shelf
}
_wp, _ws = web_params("gf_", "Gridfinity")
PARAMS.update(_wp)

SCHEMA = [
    sl("gf_nx", "Units along", 1, 8, 1, "Gridfinity"),
    sl("gf_ny", "Units out", 1, 4, 1, "Gridfinity"),
    sl("gf_rim", "Rim", 0, 10, 0.5, "Gridfinity"),
    sl("gf_t", "Shelf thickness", 5.5, 14, 0.5, "Gridfinity"),
    sl("gf_tilt", "Tilt back", 0, 30, 1, "Gridfinity"),
    sl("gf_lip", "Front lip (0 = none)", 0, 15, 0.5, "Gridfinity"),
    tog("gf_magnets", "Magnet pockets 6 × 2", "Gridfinity"),
    tog("gf_screws", "M3 screw holes", "Gridfinity"),
    tog("gf_webs", "End braces", "Gridfinity"),
] + _ws + [
    sl("gf_ph", "Plate above the shelf", 15, 200, 1, "Gridfinity"),
]


def _rsq(a, r):
    return cq.Sketch().rect(a, a).vertices().fillet(r)


def socket(x, y, z_top):
    """Baseplate socket solid to cut, top face at z_top, centred on (x, y) in the XY plane."""
    g = GF["grid"]
    a1 = g - 2 * 2.15
    a2 = a1 - 2 * 0.7
    top, mid, bot = _rsq(g, GF["corner_r"]), _rsq(a1, GF["corner_r"] - 2.15), _rsq(a2, GF["corner_r"] - 2.85)
    f1 = cq.Workplane("XY").placeSketch(top, mid.moved(cq.Location(cq.Vector(0, 0, -2.15)))).loft(ruled=True)
    f2 = cq.Workplane("XY").workplane(offset=-2.15).placeSketch(mid).extrude(-1.8)
    f3 = cq.Workplane("XY").workplane(offset=-3.95).placeSketch(mid, bot.moved(cq.Location(cq.Vector(0, 0, -0.7)))).loft(ruled=True)
    cap = cq.Workplane("XY").placeSketch(top).extrude(1.0)     # clears the top face
    return f1.union(f2).union(f3).union(cap).translate((x, y, z_top))


def validate(p):
    errs = []
    if p["gf_magnets"] and float(p["gf_t"]) < GF["socket_depth"] + GF["magnet_t"] + 1.0:
        errs.append(f"Shelf must be ≥ {GF['socket_depth'] + GF['magnet_t'] + 1.0:.1f} for magnet pockets under the sockets.")
    if float(p["gf_t"]) < GF["socket_depth"] + 0.8:
        errs.append("Shelf thinner than the socket depth + 0.8 floor.")
    return errs


def plan(p, ctx):
    g = GF["grid"]
    rim = float(p["gf_rim"])
    w = int(p["gf_nx"]) * g + 2 * rim
    w = max(w, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    return dict(w=w, h=float(p["gf_ph"]) + float(p["gf_t"]), brand="auto", keepout=float(p["gf_t"]) + 2)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    g = GF["grid"]
    nx, ny = int(p["gf_nx"]), int(p["gf_ny"])
    rim, st = float(p["gf_rim"]), float(p["gf_t"])
    tilt = float(p["gf_tilt"])
    yb = -h / 2
    sw = nx * g + 2 * rim
    depth = ny * g + 2 * rim
    # shelf built flat in a local frame: shelf top at y = yb + st, from z = t0 to t0 + depth
    # make it in the XY plane (sockets along -Z) then stand it up (Y up -> top face at +Y)
    flat = G.box(-sw / 2, sw / 2, -depth, 0, 0, st)        # XY plane: x across, y out (negative), z up = thickness
    flat = G.try_fillet(flat, "|Z", min(GF["corner_r"] + rim, sw / 2 - 0.1))
    for i in range(nx):
        for j in range(ny):
            x = -sw / 2 + rim + (i + 0.5) * g
            y = -(rim + (j + 0.5) * g)
            flat = flat.cut(socket(x, y, st))
            if p["gf_magnets"] or p["gf_screws"]:
                ins = GF["magnet_inset"]
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        mx, my = x + sx * (g / 2 - ins), y + sy * (g / 2 - ins)
                        if p["gf_magnets"]:
                            flat = flat.cut(G.cyl(GF["magnet_d"] / 2, st - GF["socket_depth"] - GF["magnet_t"], st - GF["socket_depth"] + 1, mx, my))
                        if p["gf_screws"]:
                            flat = flat.cut(G.cyl(GF["screw_d"] / 2 + 0.1, -1, st + 1, mx, my))
    lip = float(p["gf_lip"])
    if lip > 0.3:
        rc = min(GF["corner_r"] + rim, sw / 2 - 0.1)
        flat = flat.union(G.box(-sw / 2 + rc, sw / 2 - rc, -depth, -depth + 2.0, 0, st + lip))   # inside the corner radii
    # stand it up: local z (thickness) -> board Y, local -y (out) -> board +Z
    shelf = flat.rotate((0, 0, 0), (1, 0, 0), -90)          # (x, y, z) -> (x, z, -y)
    shelf = shelf.translate((0, yb, t0 - 0.01))
    body = plate
    if tilt > 0.3:
        shelf = shelf.rotate((0, yb, t0), (1, yb, t0), -tilt)   # front rises
        rise = depth * math.tan(math.radians(tilt))
        wedge = (cq.Workplane("YZ").polyline([(yb, t0 - 0.01), (yb, t0 + depth * math.cos(math.radians(tilt))),
                                              (yb + depth * math.sin(math.radians(tilt)), t0 + depth * math.cos(math.radians(tilt)))])
                 .close().extrude(sw / 2, both=True))
        body = body.union(wedge)
        ctx["derived"]["tilt"] = f"{tilt:g}° · front rises {rise:.1f}"
    body = body.union(shelf)
    body, web_rise, web_run, web_t = end_webs(body, p, "gf_", mp, w, yb + st, t0, depth, float(p["gf_ph"]), ctx)
    dd = ctx.setdefault("dims", [])
    dd.append(D((sw / 2, yb + st, t0), (sw / 2, yb + st, t0 + depth), (8, 0, 0), key="shelf_d"))
    dd.append(D((sw / 2, yb, t0 + depth), (sw / 2, yb + st, t0 + depth), (8, 0, 0), key="shelf_t"))
    dd.append(D((-sw / 2 + rim, yb + st, t0 + rim + g / 2), (-sw / 2 + rim + g, yb + st, t0 + rim + g / 2), (0, 6, 0), key="unit"))
    if nx > 1:
        dd.append(D((-sw / 2 + rim + g / 2, yb + st, t0 + rim + g / 2), (-sw / 2 + rim + 1.5 * g, yb + st, t0 + rim + g / 2), (0, 12, 0), key="pitch"))
    dd.append(D((-sw / 2 + rim + g / 2, yb + st - GF["socket_depth"], t0 + rim + g), (-sw / 2 + rim + g / 2, yb + st, t0 + rim + g), (0, 0, 6), key="socket"))
    if lip > 0.3:
        dd.append(D((-sw / 2, yb + st, t0 + depth), (-sw / 2, yb + st + lip, t0 + depth), (-8, 0, 0), key="lip"))
    if web_rise:
        dd.append(D((-w / 2, yb + st, t0), (-w / 2, yb + st + web_rise, t0), (-8, 0, 0), key="web"))
    ctx["derived"]["gridfinity"] = f"{nx} × {ny} units · shelf {sw:g} × {depth:g} × {st:g}"
    ctx.setdefault("notes", {}).update({"gf_nx": f"shelf {sw:g} wide", "gf_ny": f"shelf {depth:g} deep"})
    ctx["brand"] = (0.0, (h / 2 + yb + st + 8) / 2, w, max(0.0, h / 2 - (yb + st + 8)))
    return body
