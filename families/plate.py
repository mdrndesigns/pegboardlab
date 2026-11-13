"""
PLATE - a label plate or a blank panel of any size: branding on the
front, studs on the back, optional border lip and a grid of through
holes (hang small things off it, or screw into it). Prints face down.
"""

import cadquery as cq

import geometry as G
from dims import D
from families._lib import sl, seg, tog

NAME = "plate"
LABEL = "Plate"
ORDER = 60
ORIENT = {"default": "face", "no_supports": "face"}

PARAMS = {
    "pl_w": 90.0,
    "pl_h": 40.0,
    "pl_lip": "none",       # none | raised | groove
    "pl_lip_h": 1.0,
    "pl_lip_w": 2.0,
    "pl_lip_inset": 2.0,
    "pl_holes": 0,          # through holes across (0 = none)
    "pl_holes_d": 5.0,
    "pl_holes_rows": 1,
    "pl_hang": False,       # keyhole slot at the top for a nail / screw head
}

SCHEMA = [
    sl("pl_w", "Width", 20, 400, 1, "Plate"),
    sl("pl_h", "Height", 10, 400, 1, "Plate"),
    seg("pl_lip", "Border", [("none", "None"), ("raised", "Raised"), ("groove", "Groove")], "Plate"),
    sl("pl_lip_h", "Border height / depth", 0.4, 3, 0.1, "Plate", show={"key": "pl_lip", "not": ["none"]}),
    sl("pl_lip_w", "Border width", 0.8, 6, 0.2, "Plate", show={"key": "pl_lip", "not": ["none"]}),
    sl("pl_lip_inset", "Border inset", 0, 15, 0.5, "Plate", show={"key": "pl_lip", "not": ["none"]}),
    sl("pl_holes", "Through holes across (0 = none)", 0, 20, 1, "Plate"),
    sl("pl_holes_rows", "Hole rows", 1, 10, 1, "Plate", show={"key": "pl_holes", "gt": 0}),
    sl("pl_holes_d", "Hole Ø", 2, 20, 0.5, "Plate", show={"key": "pl_holes", "gt": 0}),
    tog("pl_hang", "Keyhole at the top", "Plate"),
]


def plan(p, ctx):
    return dict(w=float(p["pl_w"]), h=float(p["pl_h"]), brand="auto")


def build(p, ctx, plate, mp):
    t0 = ctx["t"]
    w, h = ctx["w"], ctx["h"]
    body = plate
    lip = p["pl_lip"]
    if lip == "raised" and ctx["no_supports"] and ctx["orient"] == "face":
        ctx["warns"].append("Raised border would lift the face-down print off the bed: cut as a groove instead (or allow supports).")
        lip = "groove"
    if lip != "none":
        lh, lw, ins = float(p["pl_lip_h"]), float(p["pl_lip_w"]), float(p["pl_lip_inset"])
        r = max(0.0, float(p["plate_r"]) - ins)
        outer = G.rbox(-w / 2 + ins, w / 2 - ins, -h / 2 + ins, h / 2 - ins, t0 - 0.01 if lip == "raised" else t0 - lh, t0 + (lh if lip == "raised" else 0.01), r)
        inner = G.rbox(-w / 2 + ins + lw, w / 2 - ins - lw, -h / 2 + ins + lw, h / 2 - ins - lw, t0 - lh - 1, t0 + lh + 1, max(0.0, r - lw))
        frame = outer.cut(inner)
        body = body.union(frame) if lip == "raised" else body.cut(frame)
        ctx["brand"] = (0.0, 0.0, w - 2 * (ins + lw) - 2, h - 2 * (ins + lw) - 2)
    n = int(p["pl_holes"])
    if n > 0:
        rows = int(p["pl_holes_rows"])
        d = float(p["pl_holes_d"]) + ctx["mat"]["hole"]
        px = (w - 2 * 6) / n
        py = (h - 2 * 6) / rows
        for r_ in range(rows):
            for i in range(n):
                x = -w / 2 + 6 + (i + 0.5) * px
                y = -h / 2 + 6 + (r_ + 0.5) * py
                body = body.cut(G.cyl(d / 2, -1, t0 + 1, x, y))
                ctx["blockers"].append((x, y, d / 2 + 1))
        ctx["derived"]["holes"] = f"{n * rows} × Ø{d - ctx['mat']['hole']:g}"
        x0_, y0_ = -w / 2 + 6 + 0.5 * px, -h / 2 + 6 + 0.5 * py
        dd = ctx.setdefault("dims", [])
        dd.append(D((x0_ - d / 2, y0_, t0), (x0_ + d / 2, y0_, t0), (0, 0, 6), kind="dia", key="hole"))
        if n > 1:
            dd.append(D((x0_, y0_, t0), (x0_ + px, y0_, t0), (0, 0, 12), key="pitch"))
        if rows > 1:
            dd.append(D((x0_, y0_, t0), (x0_, y0_ + py, t0), (0, 0, 12), key="row_pitch"))
    if lip != "none":
        ctx.setdefault("dims", []).append(D((w / 2 - ins - lw, h / 2 - ins, t0), (w / 2 - ins, h / 2 - ins, t0), (0, 0, 6), key="lip_w"))
        ctx["dims"].append(D((w / 2, h / 2 - ins, t0), (w / 2, h / 2, t0), (0, 0, 6), key="lip_inset"))
    if p["pl_hang"]:
        y = h / 2 - 8
        body = body.cut(G.cyl(4.5, -1, t0 + 1, 0, y)).cut(cq.Workplane("XY").center(0, y - 4).slot2D(8, 4.2, 90).extrude(t0 + 2).translate((0, 0, -1)))
        ctx["blockers"].append((0, y - 2, 6))
    return body
