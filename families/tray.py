"""
TRAY - open tray, tall cup, bin with a lowered front, on the plate's
bottom edge. Dividers, a drain, floor magnets (embedded with a print
pause, or exposed for press / epoxy). Printed upright: floor on the bed.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog, cove, magnet_pockets, magnet_spec, MAGNET_OPTIONS

NAME = "tray"
LABEL = "Tray"
ORDER = 30
ORIENT = {"default": "upright", "no_supports": "upright"}

PARAMS = {
    "tr_type": "tray",      # tray | cup | bin
    "tr_w": 80.0,           # outer width
    "tr_depth": 50.0,       # out from the plate
    "tr_h": 30.0,           # wall height (cup: tall)
    "tr_wall": 2.4,
    "tr_floor": 3.0,
    "tr_front": 12.0,       # bin: front wall height
    "tr_r": 4.0,            # inner corner radius
    "tr_div": 0,            # dividers across the width
    "tr_drain": False,
    "tr_tilt": 0.0,         # cup: tilt the opening forward (deg); fills a wedge under
    "tr_mag": "none",       # none | embed | exposed
    "tr_mag_n": 2,
    "tr_mag_size": "10x3",
    "tr_mag_d": 10.0,
    "tr_mag_t": 3.0,
    "tr_mag_cover": 0.6,
    "tr_ph": 40.0,          # plate above the floor
}

SCHEMA = [
    seg("tr_type", "Type", [("tray", "Tray"), ("cup", "Cup"), ("bin", "Bin")], "Tray"),
    sl("tr_w", "Width", 20, 300, 1, "Tray"),
    sl("tr_depth", "Depth", 15, 200, 1, "Tray"),
    sl("tr_h", "Wall height", 5, 150, 1, "Tray"),
    sl("tr_front", "Front wall height", 2, 100, 1, "Tray", show={"key": "tr_type", "in": ["bin"]}),
    sl("tr_wall", "Wall", 1.2, 6, 0.2, "Tray"),
    sl("tr_floor", "Floor", 1.6, 8, 0.2, "Tray"),
    sl("tr_r", "Inner corner radius", 0, 20, 0.5, "Tray"),
    sl("tr_div", "Dividers", 0, 8, 1, "Tray"),
    sl("tr_tilt", "Tilt forward", 0, 30, 1, "Tray", show={"key": "tr_type", "in": ["cup"]}),
    tog("tr_drain", "Drain hole", "Tray"),
    seg("tr_mag", "Floor magnets", [("none", "None"), ("embed", "Embed"), ("exposed", "Exposed")], "Tray"),
    sl("tr_mag_n", "Magnets", 1, 12, 1, "Tray", show={"key": "tr_mag", "not": ["none"]}),
    seg("tr_mag_size", "Magnet", MAGNET_OPTIONS, "Tray", show={"key": "tr_mag", "not": ["none"]}, wrap=4),
    sl("tr_mag_d", "Custom Ø", 3, 30, 0.5, "Tray", show={"key": "tr_mag_size", "in": ["custom"]}),
    sl("tr_mag_t", "Custom thickness", 1, 10, 0.5, "Tray", show={"key": "tr_mag_size", "in": ["custom"]}),
    sl("tr_mag_cover", "Cover over the magnet", 0.4, 2, 0.1, "Tray", show={"key": "tr_mag", "in": ["embed"]}),
    sl("tr_ph", "Plate above the floor", 10, 150, 1, "Tray"),
]


def plan(p, ctx):
    w = max(float(p["tr_w"]), ctx["stud_d"] + 2 * float(p["mt_margin"]))
    h = float(p["tr_ph"]) + float(p["tr_floor"])
    return dict(w=w, h=h, brand="auto", keepout=float(p["tr_floor"]) + 1)


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    k = p["tr_type"]
    tw, depth, th = float(p["tr_w"]), float(p["tr_depth"]), float(p["tr_h"])
    wall, floor, r = float(p["tr_wall"]), float(p["tr_floor"]), float(p["tr_r"])
    yb = -h / 2
    outer = G.box(-tw / 2, tw / 2, yb, yb + floor + th, t0 - 0.01, t0 + depth)
    outer = G.try_fillet(outer, "|Y", min(r + wall, tw / 2 - 0.1, depth / 2 - 0.1))
    inner = G.box(-tw / 2 + wall, tw / 2 - wall, yb + floor, yb + floor + th + 1, t0 + wall, t0 + depth - wall)
    inner = G.try_fillet(inner, "|Y", min(r, tw / 2 - wall - 0.1, (depth - 2 * wall) / 2 - 0.1))
    tray = outer.cut(inner)
    if k == "bin":
        fh = min(float(p["tr_front"]), th)
        tray = tray.cut(G.box(-tw / 2 + wall + r, tw / 2 - wall - r, yb + floor + fh, yb + floor + th + 1,
                              t0 + depth - wall - 1, t0 + depth + 1))
    nd = int(p["tr_div"])
    for i in range(1, nd + 1):
        x = -tw / 2 + i * tw / (nd + 1)
        tray = tray.union(G.box(x - wall / 2, x + wall / 2, yb, yb + floor + th, t0, t0 + depth - wall / 2))
    body = plate.union(tray)
    if k == "cup" and float(p["tr_tilt"]) > 0.5:
        ctx["warns"].append("Tilted cups are not built yet: the wedge fill is on the list; printed as a straight cup.")
    if p["tr_drain"]:
        for i in range(nd + 1):
            cx = -tw / 2 + (i + 0.5) * tw / (nd + 1)
            body = body.cut(cq.Workplane("XZ").center(cx, t0 + depth / 2).circle(2.0).extrude(-(floor + 2))
                            .translate((0, yb - 1, 0)))
    # magnets in the floor
    mm = p["tr_mag"]
    if mm != "none":
        d, t, pull = magnet_spec(p, "tr_mag_")
        n = int(p["tr_mag_n"])
        inner_w = tw - 2 * wall
        pitch = inner_w / n
        pts = [((i + 0.5) * pitch - inner_w / 2, t0 + depth / 2) for i in range(n)]
        cover = float(p["tr_mag_cover"])
        need = t + 0.2 + (cover if mm == "embed" else 0) + 0.6
        if floor < need:
            ctx["warns"].append(f"Floor {floor:g} is too thin for Ø{d:g}×{t:g} magnets ({need:.1f} needed).")
        # floor lies in the XZ plane: cut along Y. Build pockets as XY-plane cylinders then rotate.
        rr = (d + 0.3) / 2
        for x, z in pts:
            if mm == "exposed":
                cutter = cq.Workplane("XZ").center(x, z).circle(rr).extrude(-(t + 0.3)).translate((0, yb + floor - t - 0.2, 0))
            else:
                cutter = cq.Workplane("XZ").center(x, z).circle(rr).extrude(-(t + 0.2)).translate((0, yb + floor - cover - t - 0.2, 0))
            body = body.cut(cutter)
        ctx["derived"]["magnets"] = f"{n} × Ø{d:g}×{t:g}  pocket Ø{2 * rr:.1f}"
        if mm == "embed":
            ctx["derived"]["bridges_mm2"] = round(n * 3.1416 * rr * rr, 1)
            ctx["derived"]["pause_at"] = f"{(floor - cover):.2f} mm (pocket top, upright print)"
            if pull:
                ctx["derived"]["pull_est"] = f"~{pull * (0.5 if cover >= 0.4 else 0.7) * n:.1f} kg through the cover"
        elif pull:
            ctx["derived"]["pull_est"] = f"~{pull * n:.1f} kg exposed"
    cv = 3.0
    body = body.union(cove(tw - 0.02, cv, t0, yb + floor + th)) if th < 4 else body
    ctx["brand"] = (0.0, (h / 2 + yb + floor + th) / 2, w, max(0.0, h / 2 - (yb + floor + th)))
    dd = ctx.setdefault("dims", [])
    ytop = yb + floor + th
    zf = t0 + depth
    dd.append(D((tw / 2, ytop, t0), (tw / 2, ytop, zf), (8, 0, 0), key="depth"))
    dd.append(D((tw / 2, yb + floor, zf), (tw / 2, ytop, zf), (8, 0, 0), key="wall_h"))
    dd.append(D((tw / 2, yb, zf), (tw / 2, yb + floor, zf), (8, 0, 0), key="floor"))
    dd.append(D((tw / 2 - wall, ytop, zf), (tw / 2, ytop, zf), (0, 6, 0), key="wall"))
    dd.append(D((-tw / 2 + wall, ytop, zf - wall), (tw / 2 - wall, ytop, zf - wall), (0, 6, 0), key="inner_w"))
    if k == "bin":
        dd.append(D((-tw / 2, yb + floor, zf), (-tw / 2, yb + floor + min(float(p["tr_front"]), th), zf), (-8, 0, 0), key="front"))
    if nd:
        dd.append(D((-tw / 2, ytop, t0 + depth / 2), (-tw / 2 + tw / (nd + 1), ytop, t0 + depth / 2), (0, 12, 0), key="div_pitch"))
    if mm != "none":
        dd.append(D((pts[0][0] - rr, yb + floor, pts[0][1]), (pts[0][0] + rr, yb + floor, pts[0][1]), (0, 6, 0), kind="dia", key="magnet"))
        if len(pts) > 1:
            dd.append(D((pts[0][0], yb + floor, pts[0][1]), (pts[1][0], yb + floor, pts[1][1]), (0, 12, 0), key="mag_pitch"))
    ctx["derived"]["tray"] = f"{k} {tw:g} × {depth:g} × {th:g}, wall {wall:g}"
    return body
