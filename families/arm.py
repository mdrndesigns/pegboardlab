"""
ARM - the modular cantilever arm. One flange (one hole column wide,
three holes tall) with a deep arm leaving its bottom edge; arms only
vary in reach and tip, so any tool is held by a pair (or a row) of
them mapped onto the board.

    tip  lip     hook: a rounded lip rises at the end (tools, cases, bags)
         flat    no lip, the arm top is a shelf bearer
         cradle  concave seat + tall lip for a cylinder lying across two arms
                 (rotary tool, glue pen); the reach follows the Ø

The arm top carries pilot holes (Ø2.8) at 14 mm from the flange front and
every 30 mm after, inside the flat run: a SHELF plate screws onto any
pair of lip or flat arms with the same Ø3.5 × 15 countersunk screws.
Underside tapers from `ar_root` at the flange to `ar_tip_h` at the end.

Prints on its side: the whole profile lies on the bed, width = build
height, layers run along the arm (strongest way for a cantilever).
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog, cove

NAME = "arm"
LABEL = "Arm"
ORDER = 5
ORIENT = {"default": "side", "no_supports": "side"}

PILOT_FIRST = 14.0      # first shelf pilot, from the flange front
PILOT_STEP = 30.0       # then every 30 mm
PILOT_END = 8.0         # keep pilots this far inside the flat run


def pilot_positions(reach, tip, lip_t):
    """Shelf pilot distances from the flange front for an arm (shared with SHELF)."""
    if tip == "cradle":
        return []
    end = reach - (lip_t if tip == "lip" else 0.0) - PILOT_END
    out, z = [], PILOT_FIRST
    while z <= end + 1e-6:
        out.append(z)
        z += PILOT_STEP
    return out


PARAMS = {
    "ar_tip": "lip",        # lip | flat | cradle
    "ar_reach": 80.0,       # flange front to the arm end (cradle: from the Ø)
    "ar_w": 22.0,           # flange width
    "ar_aw": 0.0,           # arm width, 0 = the flange width; narrower arms sit flush with the +X side (the bed side)
    "ar_root": 20.0,        # arm height at the flange
    "ar_tip_h": 12.0,       # arm height at the end
    "ar_lip": 12.0,         # lip rise above the arm top
    "ar_lip_t": 6.0,        # lip thickness
    "ar_cove": 3.0,         # fillet between arm top and flange / lip
    "ar_cradle_d": 55.0,    # cradle: tool Ø
    "ar_pilots": True,      # shelf pilots in the arm top
    "ar_pilot_d": 2.8,
    "ar_pilot_depth": 11.0,
    "ar_ph": 40.0,          # flange height minimum (the mount pattern grows it)
}

SCHEMA = [
    seg("ar_tip", "Tip", [("lip", "Lip"), ("flat", "Flat"), ("cradle", "Cradle")], "Arm"),
    sl("ar_reach", "Reach", 25, 200, 1, "Arm", show={"key": "ar_tip", "not": ["cradle"]}),
    sl("ar_cradle_d", "Tool Ø", 15, 90, 0.5, "Arm", show={"key": "ar_tip", "in": ["cradle"]}),
    sl("ar_w", "Width", 14, 40, 0.5, "Arm"),
    sl("ar_aw", "Arm width (0 = flange)", 0, 40, 0.5, "Arm"),
    sl("ar_root", "Height at the flange", 12, 40, 0.5, "Arm"),
    sl("ar_tip_h", "Height at the end", 8, 40, 0.5, "Arm"),
    sl("ar_lip", "Lip rise", 4, 50, 0.5, "Arm", show={"key": "ar_tip", "in": ["lip", "cradle"]}),
    sl("ar_lip_t", "Lip thickness", 4, 14, 0.5, "Arm", show={"key": "ar_tip", "in": ["lip", "cradle"]}),
    sl("ar_cove", "Cove radius", 0, 8, 0.5, "Arm"),
    tog("ar_pilots", "Shelf pilots in the top", "Arm", show={"key": "ar_tip", "not": ["cradle"]}),
    sl("ar_pilot_d", "Pilot Ø", 2, 4, 0.1, "Arm", show={"key": "ar_pilots", "eq": True}),
    sl("ar_pilot_depth", "Pilot depth", 5, 20, 0.5, "Arm", show={"key": "ar_pilots", "eq": True}),
    sl("ar_ph", "Flange height (minimum)", 30, 160, 1, "Arm"),
]


def cradle_geom(p):
    """(radius with clearance, seat centre from the flange front, reach)."""
    rc = float(p["ar_cradle_d"]) / 2 + 1.0
    zc = 2.0 + rc                                  # 2 mm off the flange face
    reach = zc + rc + 1.0 + float(p["ar_lip_t"])
    return rc, zc, reach


def reach_of(p):
    return cradle_geom(p)[2] if p["ar_tip"] == "cradle" else float(p["ar_reach"])


def validate(p):
    errs = []
    if float(p["ar_tip_h"]) > float(p["ar_root"]):
        errs.append("Arm end taller than the root: the underside would slope down.")
    if p["ar_tip"] != "cradle" and float(p["ar_reach"]) < float(p["ar_lip_t"]) + 15:
        errs.append("Reach too short for the lip.")
    return errs


def plan(p, ctx):
    w = max(float(p["ar_w"]), ctx["stud_d"] + 2 * float(p["mt_margin"]))
    keep = float(p["ar_root"]) + float(p["ar_cove"]) + 1.0
    return dict(w=w, h=max(float(p["ar_ph"]), keep + 12), brand=None, keepout=keep,
                mount=dict(mt_pattern="grid", mt_cols=1, mt_rows=3))


def _y_hole(r, y0, y1, down, x, z):
    """Pilot along +Y (vertical on the wall). Teardrop section when the print lays it horizontal."""
    if down is None or abs(down[1]) > 0.5:
        return G.cyl(r, y0, y1).rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))
    # build along Z with the section tip toward (dx, -dz), then turn Z -> Y: (x, y, z) -> (x, z, -y)
    h = G.teardrop_hole(r, y0, y1, (down[0], -down[2]))
    return h.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    yb = -h / 2
    tip = p["ar_tip"]
    root, tip_h = float(p["ar_root"]), float(p["ar_tip_h"])
    lip, lip_t, cv = float(p["ar_lip"]), float(p["ar_lip_t"]), float(p["ar_cove"])
    reach = reach_of(p)
    aw = float(p["ar_aw"]) if 0.3 < float(p["ar_aw"]) < w else w
    xc = w / 2 - aw / 2                       # flush with the flange's +X side: the side that lies on the bed
    y_top = yb + root
    ze = t0 + reach
    # profile: flat top, underside rising toward the end
    prof = (cq.Workplane("YZ").polyline([(yb, t0 - 0.01), (y_top, t0 - 0.01), (y_top, ze), (y_top - tip_h, ze)])
            .close().extrude(aw / 2, both=True).translate((xc, 0, 0)))
    body = plate.union(prof)
    if cv > 0.3:
        body = body.union(cove(aw, cv, t0, y_top, xc))
    if tip in ("lip", "cradle"):
        rise = lip if tip == "lip" else max(lip, 0.55 * cradle_geom(p)[0])
        lb = G.box(xc - aw / 2, xc + aw / 2, y_top - 0.01, y_top + rise, ze - lip_t, ze)
        lb = G.try_fillet(lb, cq.selectors.NearestToPointSelector((xc, y_top + rise, ze - lip_t / 2)), lip_t / 2 - 0.15)
        body = body.union(lb)
        if cv > 0.3:
            # cove between the arm top and the lip's inner face (mirror of the root cove)
            blk = G.box(xc - aw / 2, xc + aw / 2, y_top, y_top + cv, ze - lip_t - cv, ze - lip_t + 0.01)
            cut = (cq.Workplane("YZ").center(y_top + cv, ze - lip_t - cv).circle(cv).extrude(w / 2 + 1, both=True))
            body = body.union(blk.cut(cut))
        if tip == "cradle":
            rc, zc, _ = cradle_geom(p)
            seat_h = 0.4 * rc
            z0 = t0 + zc
            blk = G.box(xc - aw / 2, xc + aw / 2, y_top - 0.01, y_top + seat_h, z0, ze - lip_t + 0.01)
            cyl = cq.Workplane("YZ").center(y_top + rc - 0.6, z0).circle(rc).extrude(w / 2 + 1, both=True)
            body = body.union(blk.cut(cyl)).cut(cyl)
            ctx["derived"]["cradle"] = f"seat R{rc:.1f} for a Ø{float(p['ar_cradle_d']):g} tool · lip {rise:.0f} above the arm"
    # shelf pilots
    pil = []
    if p["ar_pilots"] and tip != "cradle" and aw >= 14:
        down = G.down_vector(ctx["orient"]) if ctx["no_supports"] else None
        r = float(p["ar_pilot_d"]) / 2
        for zk in pilot_positions(reach, tip, lip_t):
            hz = root - (root - tip_h) * zk / reach
            depth = min(float(p["ar_pilot_depth"]), hz - 1.5)
            body = body.cut(_y_hole(r, y_top - depth, y_top + 1.0, down, xc, t0 + zk))
            pil.append(f"{zk:g}")
    # dimensions (holder frame)
    dd = ctx.setdefault("dims", [])
    xs_ = w / 2
    rise_ = (lip if tip == "lip" else max(lip, 0.55 * cradle_geom(p)[0])) if tip in ("lip", "cradle") else 0.0
    dd.append(D((xs_, y_top, t0), (xs_, y_top, ze), (0, rise_ + 8, 0), key="reach"))
    dd.append(D((xs_, yb, t0), (xs_, y_top, t0), (8, 0, 0), key="root"))
    dd.append(D((xs_, y_top - tip_h, ze), (xs_, y_top, ze), (8, 0, 0), key="tip_h"))
    if tip in ("lip", "cradle"):
        dd.append(D((xs_, y_top, ze), (xs_, y_top + rise_, ze), (8, 0, 0), key="lip"))
        dd.append(D((xs_, y_top + rise_, ze - lip_t), (xs_, y_top + rise_, ze), (0, 6, 0), key="lip_t"))
    if aw < w - 0.3:
        dd.append(D((xc - aw / 2, y_top, ze), (xc + aw / 2, y_top, ze), (0, rise_ + 4, 0), key="arm_w"))
    if tip == "cradle":
        rc_, zc_, _ = cradle_geom(p)
        yc_ = y_top + rc_ - 0.6
        dd.append(D((xs_, yc_, t0 + zc_ - rc_), (xs_, yc_, t0 + zc_ + rc_), (8, 0, 0), kind="dia", key="cradle"))
    pz = [float(v) for v in pil]
    if pz:
        dd.append(D((xc, y_top, t0), (xc, y_top, t0 + pz[0]), (0, 5, 0), key="pilot_1"))
        if len(pz) > 1:
            dd.append(D((xc, y_top, t0 + pz[0]), (xc, y_top, t0 + pz[1]), (0, 5, 0), key="pilot_pitch"))
        dd.append(D((xc - float(p["ar_pilot_d"]) / 2, y_top, t0 + pz[0]), (xc + float(p["ar_pilot_d"]) / 2, y_top, t0 + pz[0]), (0, 2, 0),
                    kind="dia", key="pilot_d"))
    ctx.setdefault("notes", {}).update({"ar_aw": f"arm {aw:g} wide", "ar_cradle_d": f"seat Ø{2 * cradle_geom(p)[0]:.1f} · reach {reach:.1f}"})
    ctx["derived"]["arm"] = f"{tip} · reach {reach:.1f} · {root:g} → {tip_h:g} tall · {aw:g} wide"
    if pil:
        ctx["derived"]["pilots"] = "shelf pilots at " + ", ".join(pil) + " from the flange front"
    ctx["brand"] = None
    return body
