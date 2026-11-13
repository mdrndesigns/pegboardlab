"""
HOOK - J-hooks, double prongs, pegs, loops and ramps on a plate.

The arm leaves the plate at its bottom edge, so printed upright the arm's
underside sits on the bed and nothing overhangs; printed on its side the
whole profile lies flat (single-width hooks only).
"""

import math

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog, arm_j

NAME = "hook"
LABEL = "Hook"
ORDER = 10
ORIENT = {"default": "side", "no_supports": "upright"}

PARAMS = {
    "hk_type": "j",         # j | double | peg | loop | ramp
    "hk_reach": 30.0,
    "hk_w": 20.0,           # hook width (j, peg, loop, ramp)
    "hk_t": 6.0,            # arm thickness
    "hk_tip": 12.0,         # lip rise
    "hk_bend": 4.0,         # inner cove radius
    "hk_gap": 30.0,         # double: clear gap between the prongs
    "hk_prong": 8.0,        # double: prong width
    "hk_loop_h": 20.0,      # loop: inner height
    "hk_angle": 20.0,       # ramp: rise angle
    "hk_rib": 10.0,         # web above the arm, 0 = none
    "hk_rib_t": 3.0,
    "hk_pw": 0.0,           # plate width, 0 = auto
    "hk_ph": 44.0,          # plate height
}

SCHEMA = [
    seg("hk_type", "Type", [("j", "J"), ("double", "Double"), ("peg", "Peg"), ("loop", "Loop"), ("ramp", "Ramp")], "Hook"),
    sl("hk_reach", "Reach", 10, 120, 1, "Hook"),
    sl("hk_w", "Width", 6, 80, 1, "Hook", show={"key": "hk_type", "not": ["double"]}),
    sl("hk_t", "Arm thickness", 3, 14, 0.5, "Hook"),
    sl("hk_tip", "Lip rise", 0, 40, 1, "Hook", show={"key": "hk_type", "in": ["j", "double", "peg"]}),
    sl("hk_bend", "Inner radius", 0, 15, 0.5, "Hook"),
    sl("hk_gap", "Prong gap", 5, 120, 1, "Hook", show={"key": "hk_type", "in": ["double"]}),
    sl("hk_prong", "Prong width", 4, 30, 0.5, "Hook", show={"key": "hk_type", "in": ["double"]}),
    sl("hk_loop_h", "Loop inner height", 6, 80, 1, "Hook", show={"key": "hk_type", "in": ["loop"]}),
    sl("hk_angle", "Ramp angle", 5, 45, 1, "Hook", show={"key": "hk_type", "in": ["ramp"]}),
    sl("hk_rib", "Web height (0 = none)", 0, 40, 1, "Hook"),
    sl("hk_rib_t", "Web thickness", 2, 8, 0.5, "Hook", show={"key": "hk_rib", "gt": 0}),
    sl("hk_pw", "Plate width (0 = auto)", 0, 160, 1, "Hook"),
    sl("hk_ph", "Plate height", 20, 160, 1, "Hook"),
]


def orient_for(p):
    if p["hk_type"] in ("double", "loop") or float(p["hk_w"]) > 40:
        return "upright"
    if p["mt_fix"] == "jhook":
        return "side"          # the J bend lies flat
    return None


def width(p, ctx):
    if p["hk_type"] == "double":
        return float(p["hk_gap"]) + 2 * float(p["hk_prong"])
    return float(p["hk_w"])


def plan(p, ctx):
    w = float(p["hk_pw"]) or max(width(p, ctx) + 2.0, ctx["stud_d"] + 2 * float(p["mt_margin"]))
    h = float(p["hk_ph"])
    rib = float(p["hk_rib"]) if p["hk_type"] != "loop" else 0.0
    feat = float(p["hk_t"]) + (float(p["hk_loop_h"]) + float(p["hk_t"]) if p["hk_type"] == "loop" else 0.0)
    if p["hk_type"] == "ramp":
        feat += float(p["hk_reach"]) * math.tan(math.radians(float(p["hk_angle"])))
    return dict(w=w, h=h, brand="auto", keepout=feat + (rib if rib > 0.5 else 0) + 1)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    kind = p["hk_type"]
    reach, at, tip, bend = float(p["hk_reach"]), float(p["hk_t"]), float(p["hk_tip"]), float(p["hk_bend"])
    ns = ctx["no_supports"]
    yb = -h / 2
    body = plate
    arms = []
    if kind == "j":
        arms = [(0.0, float(p["hk_w"]), tip)]
    elif kind == "peg":
        arms = [(0.0, float(p["hk_w"]), min(tip, at))]
    elif kind == "double":
        g, pw = float(p["hk_gap"]), float(p["hk_prong"])
        arms = [(-(g + pw) / 2, pw, tip), ((g + pw) / 2, pw, tip)]
    elif kind == "loop":
        lw = float(p["hk_w"])
        lh = float(p["hk_loop_h"])
        arms = [(0.0, lw, lh + at)]
        # top bar back to the plate closes the loop
        body = body.union(G.box(-lw / 2, lw / 2, yb + at + lh, yb + 2 * at + lh, t0 - 0.01, t0 + reach))
        ctx["derived"]["bridges_mm2"] = round(lw * reach, 1)
        if ns and reach > 40:
            ctx["warns"].append(f"Loop top bar bridges {reach:.0f} mm; over 40 it sags without supports.")
    elif kind == "ramp":
        lw = float(p["hk_w"])
        ang = math.radians(float(p["hk_angle"]))
        rise = reach * math.tan(ang)
        prof = (cq.Workplane("YZ").polyline([(yb, t0 - 0.01), (yb, t0 + reach), (yb + at + rise, t0 + reach),
                                             (yb + at, t0 - 0.01)]).close().extrude(lw / 2, both=True))
        prof = G.try_fillet(prof, cq.selectors.NearestToPointSelector((0, yb + at + rise, t0 + reach)), at / 2 - 0.2)
        body = body.union(prof)
    for x0, aw, atip in arms:
        body = body.union(arm_j(aw, reach, at, atip, bend, t0, yb, ns, x0=x0))
    # web above the arm
    rib = float(p["hk_rib"])
    if rib > 0.5 and kind != "loop":
        rt = float(p["hk_rib_t"])
        run = min(reach - at - 1.0, 60.0) if kind != "ramp" else reach - 1.0
        if run > 2:
            xs = [x0 for x0, _, _ in arms] or [0.0]
            for x0 in xs:
                wr = G.wedge(rt, run, rib, x0=x0, up=True)      # right angle at the plate / arm-top corner
                body = body.union(wr.translate((0, yb + at, t0 - 0.01)))
    ctx["brand"] = (0.0, (h / 2 + yb + at + (rib if rib > 0.5 else 0)) / 2, w,
                    h / 2 - (yb + at + (rib if rib > 0.5 else 0)))
    dd = ctx.setdefault("dims", [])
    xr = (arms[-1][0] + arms[-1][1] / 2) if arms else float(p["hk_w"]) / 2
    dd.append(D((xr, yb + at, t0), (xr, yb + at, t0 + reach), (0, (arms[-1][2] if arms else 0) + 8, 0), key="reach"))
    dd.append(D((xr, yb, t0 + reach), (xr, yb + at, t0 + reach), (8, 0, 0), key="arm_t"))
    if arms and arms[-1][2] > 0.3:
        dd.append(D((xr, yb + at, t0 + reach), (xr, yb + at + arms[-1][2], t0 + reach), (8, 0, 0), key="tip"))
    if kind == "double":
        g, pw = float(p["hk_gap"]), float(p["hk_prong"])
        dd.append(D((-g / 2, yb + at, t0 + reach), (g / 2, yb + at, t0 + reach), (0, tip + 6, 0), key="gap"))
        dd.append(D((g / 2, yb + at, t0 + reach), (g / 2 + pw, yb + at, t0 + reach), (0, tip + 12, 0), key="prong"))
    elif kind == "loop":
        dd.append(D((xr, yb + at, t0 + reach), (xr, yb + at + float(p["hk_loop_h"]), t0 + reach), (8, 0, 0), key="loop_h"))
    elif kind == "ramp":
        dd.append(D((xr, yb + at, t0 + reach), (xr, yb + at + reach * math.tan(math.radians(float(p["hk_angle"]))), t0 + reach), (8, 0, 0), key="rise"))
    if arms:
        dd.append(D((arms[0][0] - arms[0][1] / 2, yb, t0 + reach), (arms[0][0] + arms[0][1] / 2, yb, t0 + reach), (0, -8, 0), key="arm_w"))
    if rib > 0.5 and kind != "loop":
        dd.append(D((-w / 2, yb + at, t0), (-w / 2, yb + at + rib, t0), (-8, 0, 0), key="rib"))
    ctx["derived"]["hook"] = f"{kind} · reach {reach:g} · {len(arms) or 1} arm(s)"
    return body
