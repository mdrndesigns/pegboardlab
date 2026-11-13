"""
MAGSTRIP - a magnetic bar: a plate with disc magnets in rows.

    embed     pocket closed on both sides; the print pauses at the pocket
              top so the magnets drop in. A thin front cover (0.4-0.8)
              keeps most of the pull. The readout gives the pause height.
    exposed   pocket open on the front face (+0.3 on Ø): press in or
              epoxy, flush with the face - full pull.
    rear      pocket open on the back face, press in from behind, the
              front stays clean (pull through the plate: weakest).

Prints face down. Optional raised ledge along the bottom so a tool
rests on it as well as sticking.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog, magnet_spec, MAGNET_OPTIONS

NAME = "magstrip"
LABEL = "Mag strip"
ORDER = 70
ORIENT = {"default": "face", "no_supports": "face"}

PARAMS = {
    "mg_w": 120.0,
    "mg_h": 30.0,
    "mg_mode": "embed",     # embed | exposed | rear
    "mg_n": 5,
    "mg_rows": 1,
    "mg_size": "10x3",
    "mg_d": 10.0,
    "mg_t": 3.0,
    "mg_clear": 0.3,
    "mg_cover": 0.6,
    "mg_ledge": 0.0,        # ledge out from the face along the bottom edge, 0 = none
    "mg_ledge_t": 4.0,
}

SCHEMA = [
    sl("mg_w", "Width", 20, 400, 1, "Mag strip"),
    sl("mg_h", "Height", 10, 150, 1, "Mag strip"),
    seg("mg_mode", "Pockets", [("embed", "Embed · pause"), ("exposed", "Exposed · front"), ("rear", "Rear")], "Mag strip"),
    sl("mg_n", "Magnets across", 1, 24, 1, "Mag strip"),
    sl("mg_rows", "Rows", 1, 6, 1, "Mag strip"),
    seg("mg_size", "Magnet", MAGNET_OPTIONS, "Mag strip", wrap=4),
    sl("mg_d", "Custom Ø", 3, 40, 0.5, "Mag strip", show={"key": "mg_size", "in": ["custom"]}),
    sl("mg_t", "Custom thickness", 1, 12, 0.5, "Mag strip", show={"key": "mg_size", "in": ["custom"]}),
    sl("mg_clear", "Pocket clearance (Ø)", 0, 0.8, 0.05, "Mag strip"),
    sl("mg_cover", "Front cover", 0.4, 2, 0.1, "Mag strip", show={"key": "mg_mode", "in": ["embed"]}),
    sl("mg_ledge", "Bottom ledge (0 = none)", 0, 40, 1, "Mag strip"),
    sl("mg_ledge_t", "Ledge thickness", 2, 10, 0.5, "Mag strip", show={"key": "mg_ledge", "gt": 0}),
]


def orient_for(p):
    return "upright" if float(p["mg_ledge"]) > 0.5 else None


def plan(p, ctx):
    d, t, pull = magnet_spec(p, "mg_")
    need = t + 0.2 + (float(p["mg_cover"]) + 1.2 if p["mg_mode"] == "embed" else 1.2)
    return dict(w=float(p["mg_w"]), h=float(p["mg_h"]), brand="auto", t_min=need)


def validate(p):
    return []


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    d, t, pull = magnet_spec(p, "mg_")
    n, rows = int(p["mg_n"]), int(p["mg_rows"])
    mode = p["mg_mode"]
    clear = float(p["mg_clear"])
    cover = float(p["mg_cover"])
    rr = (d + clear) / 2
    depth = t + 0.2
    body = plate
    pts = []
    px = w / n
    py = h / rows
    for r_ in range(rows):
        for i in range(n):
            pts.append((-w / 2 + (i + 0.5) * px, -h / 2 + (r_ + 0.5) * py))
    td = ctx["td"]
    cut = (lambda r, z0, z1, x, y: G.teardrop_hole(r, z0, z1, td, x, y)) if td else G.cyl
    for x, y in pts:
        if mode == "exposed":
            body = body.cut(cut(rr, t0 - depth, t0 + 1, x, y))
        elif mode == "rear":
            body = body.cut(cut(rr, -1, depth, x, y))
        else:
            body = body.cut(cut(rr, t0 - cover - depth, t0 - cover, x, y))
    # a stud behind a pocket is fine while the web between them is thick enough
    web = (t0 - cover - depth) if mode == "embed" else (t0 - depth if mode == "exposed" else 0.0)
    if mode != "rear" and web < 1.2:
        for sx, sy in mp["studs"]:
            if any((sx - x) ** 2 + (sy - y) ** 2 < (rr + ctx["stud_d"] / 2) ** 2 for x, y in pts):
                ctx["warns"].append(f"Only {web:.1f} mm of plate between a stud and a pocket: thicken the plate.")
                break
    ctx["blockers"] += [(x, y, rr + 1) for x, y in pts]
    if pts:
        dd = ctx.setdefault("dims", [])
        x0_, y0_ = pts[0]
        dd.append(D((x0_ - rr, y0_, t0), (x0_ + rr, y0_, t0), (0, 0, 6), kind="dia", key="pocket"))
        if len(pts) > 1:
            dd.append(D((x0_, y0_, t0), (pts[1][0], pts[1][1], t0), (0, 0, 12), key="pitch"))
        if mode == "embed":
            dd.append(D((w / 2, y0_, t0 - cover), (w / 2, y0_, t0), (8, 0, 0), key="cover"))
    ledge = float(p["mg_ledge"])
    if ledge > 0.5:
        lt = float(p["mg_ledge_t"])
        body = body.union(G.box(-w / 2, w / 2, -h / 2, -h / 2 + lt, t0 - 0.01, t0 + ledge))
        ctx["derived"]["ledge"] = f"{ledge:g} out, {lt:g} thick - printed upright on the ledge"
    ctx["derived"]["magnets"] = f"{len(pts)} × Ø{d:g}×{t:g}  pocket Ø{2 * rr:.2f} × {depth:.1f} · {mode}"
    if mode == "embed":
        ctx["derived"]["bridges_mm2"] = round(len(pts) * 3.1416 * rr * rr, 1)
        if ctx["orient"] == "face":
            ctx["derived"]["pause_at"] = f"{cover + depth:.2f} mm from the bed (face-down print): pocket top"
        else:
            ctx["derived"]["pause_at"] = f"{(pts[-1][1] + h / 2 + rr):.2f} mm: top of the highest pocket (upright print)"
        if pull:
            ctx["derived"]["pull_est"] = f"~{pull * len(pts) * (0.5 if cover >= 0.4 else 0.7):.1f} kg total through {cover:g} cover"
    elif pull:
        ctx["derived"]["pull_est"] = f"~{pull * len(pts) * (1.0 if mode == 'exposed' else 0.3):.1f} kg total"
    return body
