"""
SHELF - a plate that screws onto the tops of two or more ARMs and turns
them into a shelf. The arms sit `sh_span` hole pitches apart; the plate's
countersunk holes land on the arms' shelf pilots (14 mm from the flange
front, then every 30 mm) and take the same Ø3.5 × 15 drywall screws.

On flat arms the plate runs to the arm ends; on lip arms it stops in
front of the lips, which then act as the front stop. Side and front lips
are optional, and a front-open notch lets a part hang through the plate
(the lower blade guard of a circular saw). No text. Prints flat, bottom
face on the bed: nothing overhangs.
"""

import cadquery as cq

import geometry as G
from dims import D as DIM, group_cuts
from families._lib import sl, seg, tog
from families.arm import pilot_positions

NAME = "shelf"
LABEL = "Shelf"
ORDER = 6
PLATE = False
ORIENT = {"default": "back", "no_supports": "back"}

PARAMS = {
    "sh_arms": 2,            # arms under the plate
    "sh_span": 4,            # hole pitches between neighbouring arms
    "sh_reach": 100.0,       # the arms' reach
    "sh_tip": "flat",        # the arms' tip: flat | lip
    "sh_lip_t": 6.0,         # the arms' lip thickness
    "sh_aw": 22.0,           # the arms' width
    "sh_gap": 4.0,           # back edge off the flange front (clears the arm cove)
    "sh_over": 10.0,         # plate beyond the outer arms, per side
    "sh_t": 5.0,
    "sh_side_lip": 8.0,      # side lips above the plate, 0 = none
    "sh_front_lip": 0.0,     # front lip above the plate, 0 = none
    "sh_lip_w": 3.0,         # lip wall
    "sh_notch_l": 0.0,       # front notch length (along the wall), 0 = none
    "sh_notch_d": 30.0,      # front notch depth (from the front edge)
    "sh_notch_x": 0.0,       # notch centre offset
    "sh_r": 3.0,             # outer corner radius
    "sh_back_lip": 0.0,      # back wall above the plate (stiffens long racks), 0 = none
    "sh_cuts": [],           # rack cut-outs: dicts kind=open|slot|hole, x, w, l, y (see cut())
}

SCHEMA = [
    sl("sh_arms", "Arms", 2, 6, 1, "Shelf"),
    sl("sh_span", "Pitches between arms", 1, 12, 1, "Shelf"),
    sl("sh_reach", "Arm reach", 25, 200, 1, "Shelf"),
    seg("sh_tip", "Arm tip", [("flat", "Flat"), ("lip", "Lip")], "Shelf"),
    sl("sh_lip_t", "Arm lip thickness", 4, 14, 0.5, "Shelf", show={"key": "sh_tip", "in": ["lip"]}),
    sl("sh_aw", "Arm width", 14, 40, 0.5, "Shelf"),
    sl("sh_gap", "Gap to the flange", 0, 10, 0.5, "Shelf"),
    sl("sh_over", "Overhang past the arms", 0, 80, 1, "Shelf"),
    sl("sh_t", "Thickness", 3, 10, 0.5, "Shelf"),
    sl("sh_side_lip", "Side lips (0 = none)", 0, 40, 0.5, "Shelf"),
    sl("sh_front_lip", "Front lip (0 = none)", 0, 40, 0.5, "Shelf"),
    sl("sh_lip_w", "Lip wall", 2, 6, 0.5, "Shelf"),
    sl("sh_notch_l", "Front notch length (0 = none)", 0, 200, 1, "Shelf"),
    sl("sh_notch_d", "Front notch depth", 5, 120, 1, "Shelf", show={"key": "sh_notch_l", "gt": 0}),
    sl("sh_notch_x", "Front notch offset", -100, 100, 0.5, "Shelf", show={"key": "sh_notch_l", "gt": 0}),
    sl("sh_r", "Corner radius", 0, 10, 0.5, "Shelf"),
    sl("sh_back_lip", "Back wall (0 = none)", 0, 40, 0.5, "Shelf"),
]


def cut(c, D, t):
    """One rack cut-out through the plate. x = centre along the wall, w = width along the wall,
    l = length front-back. open: runs in from the front edge (quick-draw), round inner end;
    slot: closed stadium centred at depth y; hole: round, Ø w, at depth y."""
    k, x, w = c["kind"], float(c["x"]), float(c["w"])
    z0, z1 = -1.0, t + 60.0
    if k == "hole":
        return G.cyl(w / 2, z0, z1, x, float(c["y"]))
    l = float(c["l"])
    if k == "open":
        y0 = D - l
        if l <= w / 2:
            return G.box(x - w / 2, x + w / 2, y0, D + 1, z0, z1)
        return G.box(x - w / 2, x + w / 2, y0 + w / 2, D + 1, z0, z1).union(G.cyl(w / 2, z0, z1, x, y0 + w / 2))
    y = float(c["y"])
    if l >= w:
        r = w / 2
        return (G.box(x - r, x + r, y - l / 2 + r, y + l / 2 - r, z0, z1)
                .union(G.cyl(r, z0, z1, x, y - l / 2 + r)).union(G.cyl(r, z0, z1, x, y + l / 2 - r)))
    r = l / 2
    return (G.box(x - w / 2 + r, x + w / 2 - r, y - r, y + r, z0, z1)
            .union(G.cyl(r, z0, z1, x - w / 2 + r, y)).union(G.cyl(r, z0, z1, x + w / 2 - r, y)))


def arm_xs(p, ctx):
    n, s = int(p["sh_arms"]), int(p["sh_span"]) * float(ctx["b"]["pitch_x"])
    return [(i - (n - 1) / 2) * s for i in range(n)]


def dims(p, ctx):
    xs = arm_xs(p, ctx)
    W = xs[-1] - xs[0] + float(p["sh_aw"]) + 2 * float(p["sh_over"])
    stop = (float(p["sh_lip_t"]) + 0.5) if p["sh_tip"] == "lip" else 0.0
    D = float(p["sh_reach"]) - float(p["sh_gap"]) - stop
    return W, D


def validate(p):
    errs = []
    if int(p["sh_span"]) * 23.0 < float(p["sh_aw"]) + 2:
        errs.append("Arms closer than their width.")
    return errs


def build(p, ctx, plate, mp):
    W, D = dims(p, ctx)
    t = float(p["sh_t"])
    gap = float(p["sh_gap"])
    xs = arm_xs(p, ctx)
    # local frame: x along the wall, y = depth from the back edge (0) to the front (D), z up
    body = G.rbox(-W / 2, W / 2, 0, D, 0, t, float(p["sh_r"]))
    lw = float(p["sh_lip_w"])
    sl_h, fl_h = float(p["sh_side_lip"]), float(p["sh_front_lip"])
    if sl_h > 0.3:
        for sx in (-1, 1):
            x0, x1 = (W / 2 - lw, W / 2) if sx > 0 else (-W / 2, -W / 2 + lw)
            lip = G.box(x0, x1, 0, D, t - 0.01, t + sl_h)
            lip = G.try_chamfer(lip, ">Z", min(1.0, lw / 2 - 0.2))
            body = body.union(lip)
    nl = float(p["sh_notch_l"])
    nx, nd = float(p["sh_notch_x"]), float(p["sh_notch_d"])
    if fl_h > 0.3:
        fl = G.box(-W / 2, W / 2, D - lw, D, t - 0.01, t + fl_h)
        fl = G.try_chamfer(fl, ">Z", min(1.0, lw / 2 - 0.2))
        body = body.union(fl)
    bl = float(p.get("sh_back_lip", 0.0))
    if bl > 0.3:
        bw = G.box(-W / 2, W / 2, 0, lw, t - 0.01, t + bl)
        bw = G.try_chamfer(bw, ">Z", min(1.0, lw / 2 - 0.2))
        body = body.union(bw)
    cuts = list(p.get("sh_cuts") or [])
    aw = float(p["sh_aw"])
    for c in cuts:
        body = body.cut(cut(c, D, t))
        x, w = float(c["x"]), float(c["w"])
        for xa in xs:
            if abs(x - xa) < w / 2 + aw / 2:
                ctx["warns"].append(f"Cut-out at x = {x:.0f} sits over the arm at x = {xa:.0f}.")
    if cuts:
        ctx["derived"]["rack"] = f"{len(cuts)} cut-outs: " + ", ".join(sorted({c['kind'] for c in cuts}))
    if nl > 0.5:
        rr, zt = min(4.0, nd / 2 - 0.1, nl / 2 - 0.1), t + max(sl_h, fl_h, bl) + 1
        notch = (G.box(nx - nl / 2 + rr, nx + nl / 2 - rr, D - nd, D + 1, -1, zt)
                 .union(G.box(nx - nl / 2, nx + nl / 2, D - nd + rr, D + 1, -1, zt))
                 .union(G.cyl(rr, -1, zt, nx - nl / 2 + rr, D - nd + rr))
                 .union(G.cyl(rr, -1, zt, nx + nl / 2 - rr, D - nd + rr)))      # rounded inner corners, no fillet op
        body = body.cut(notch)
        aw = float(p["sh_aw"])
        for x in xs:
            if abs(x - nx) < nl / 2 + aw / 2:
                ctx["warns"].append(f"Notch over the arm at x = {x:.0f}: whatever hangs through would hit it.")
    # countersunk holes over the arms' pilots
    sd, head = float(p["screw_d"]), float(p["screw_head"])
    thru, csk = sd + 0.5, head + 0.6
    zs = pilot_positions(float(p["sh_reach"]), p["sh_tip"], float(p["sh_lip_t"]))
    n = 0
    for x in xs:
        for zk in zs:
            y = zk - gap
            if y < csk / 2 or y > D - csk / 2:
                continue
            if nl > 0.5 and abs(x - nx) < nl / 2 + csk / 2 and y > D - nd - csk / 2:
                continue
            body = body.cut(G.cyl(thru / 2, -1, t + 1, x, y))
            cone = (cq.Workplane("XY").workplane(offset=t + 0.01).center(x, y).circle(csk / 2)
                    .workplane(offset=-(csk - thru) / 2 - 0.01).circle(thru / 2).loft())
            body = body.cut(cone)
            n += 1
    ctx.setdefault("notes", {}).update({"sh_span": f"{int(p['sh_span']) * float(ctx['b']['pitch_x']):.1f} centres",
                                        "sh_arms": f"plate {W:.1f} wide", "sh_reach": f"plate {D:.1f} deep"})
    dd = ctx.setdefault("dims", [])
    dd.append(DIM((-W / 2, 0, t), (W / 2, 0, t), (0, -8, 0), key="width"))
    dd.append(DIM((W / 2, 0, t), (W / 2, D, t), (8, 0, 0), key="depth"))
    dd.append(DIM((W / 2, D, 0), (W / 2, D, t), (8, 0, 0), key="t"))
    if len(xs) > 1:
        dd.append(DIM((xs[0], D, t), (xs[1], D, t), (0, 8, 0), key="arm_span"))
    dd.append(DIM((xs[0] - float(p["sh_aw"]) / 2, D, t), (xs[0] + float(p["sh_aw"]) / 2, D, t), (0, 16, 0), key="arm_w"))
    if sl_h > 0.3:
        dd.append(DIM((W / 2, D, t), (W / 2, D, t + sl_h), (8, 0, 0), key="side_lip"))
    if fl_h > 0.3:
        dd.append(DIM((-W / 2, D, t), (-W / 2, D, t + fl_h), (-8, 0, 0), key="front_lip"))
    if bl > 0.3:
        dd.append(DIM((-W / 2, 0, t), (-W / 2, 0, t + bl), (-8, 0, 0), key="back_wall"))
    if nl > 0.5:
        dd.append(DIM((nx - nl / 2, D, t), (nx + nl / 2, D, t), (0, 24, 0), key="notch_l"))
        dd.append(DIM((nx + nl / 2, D - nd, t), (nx + nl / 2, D, t), (6, 0, 0), key="notch_d"))
    pil_y = [zk - gap for zk in zs if csk / 2 <= zk - gap <= D - csk / 2]
    if pil_y:
        dd.append(DIM((xs[0], 0, t), (xs[0], pil_y[0], t), (0, 0, 6), key="pilot_1"))
        if len(pil_y) > 1:
            dd.append(DIM((xs[0], pil_y[0], t), (xs[0], pil_y[1], t), (0, 0, 6), key="pilot_pitch"))
        dd.append(DIM((xs[0] - csk / 2, pil_y[0], t), (xs[0] + csk / 2, pil_y[0], t), (0, 0, 3), kind="dia", key="csk"))
    firsts, pitches = group_cuts(cuts, lambda c: (c["kind"], round(float(c["w"]), 2), round(float(c.get("l", 0)), 2)))
    for c in firsts:
        x, w = float(c["x"]), float(c["w"])
        if c["kind"] == "hole":
            y = float(c["y"])
            dd.append(DIM((x - w / 2, y, t), (x + w / 2, y, t), (0, 0, 6), kind="dia", key="cut_d"))
        elif c["kind"] == "open":
            l = float(c["l"])
            dd.append(DIM((x - w / 2, D, t), (x + w / 2, D, t), (0, 0, 6), key="cut_w"))
            dd.append(DIM((x + w / 2, D - l, t), (x + w / 2, D, t), (4, 0, 6), key="cut_l"))
        else:
            l, y = float(c["l"]), float(c["y"])
            dd.append(DIM((x - w / 2, y, t), (x + w / 2, y, t), (0, 0, 6), key="cut_w"))
            dd.append(DIM((x + w / 2, y - l / 2, t), (x + w / 2, y + l / 2, t), (4, 0, 6), key="cut_l"))
    for c0, c1 in pitches:
        y = D if c0["kind"] == "open" else float(c0["y"])
        dd.append(DIM((float(c0["x"]), y, t), (float(c1["x"]), y, t), (0, 0, 12), key="pitch"))
    ctx["derived"]["shelf"] = (f"{W:.1f} × {D:.1f} × {t:g} on {len(xs)} arms {int(p['sh_span'])} pitches apart "
                               f"({int(p['sh_span']) * float(ctx['b']['pitch_x']):.1f}) · {p['sh_tip']} arms reach {float(p['sh_reach']):g}")
    ctx["derived"]["screws"] = f"{n} × Ø{sd:g} csk into the arm tops"
    if n < len(xs):
        ctx["warns"].append("Some arm gets no screw: check reach, gap and notch.")
    return body
