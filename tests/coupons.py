#!/usr/bin/env python3
"""
PEGBOARDLAB test coupons - hole-fit and retention samples for Dhiya's
two boards, printed on the Bambu H2S in ABS-GF before the tool is built.

    python3 tests/coupons.py            -> samples/coupon_imperial.*, samples/coupon_metric.*

Each coupon is one print plate:

imperial_19 (Ø7.5 holes, 19 mm chipboard, 23.876 square)
    5 fit plugs     pegs Ø6.6 6.8 7.0 7.2 7.4 × 16, labelled, head on the bed
    hook STR        two straight pegs Ø7.0 × 16, one row apart, J-hook 25 mm
    hook TPR        two tapered pegs Ø7.4 at the root -> Ø6.8 at the tip
    (both hooks print on their side: layers run along the pegs)

metric_4 (Ø4.7 holes, 4 mm hardboard, 45° lattice)
    4 fit plugs     pegs Ø3.9 4.1 4.3 4.5 × 6, labelled
    row bar 26.4    two Ø4.2 pegs 26.44 apart along a row   } one of the two
    row bar 23.9    two Ø4.2 pegs 23.876 apart along a row  } settles the pitch
    hook J3.8       rolled J: Ø3.8 shaft, 90° bend R5 behind the board,
                    straight Ø4.0 stop peg two rows down (26.44)
    hook J4.2       the same with a Ø4.2 shaft (tight: sagitta + shaft = 4.62 of 4.7)

Coordinates while modelling: board face z = 0, +Y up, pegs into z < 0.
Each body is then laid on the bed for printing.
"""

import math
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cadquery as cq
from boards import BOARDS, hole_xy

FONT = next((p for p in (
    os.path.join(ROOT, "fonts", "IBMPlexSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
) if os.path.exists(p)), None)

OUT = os.path.join(ROOT, "samples")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- primitives

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def peg(d, length, x, y, tip_ch=0.8, taper_to=None):
    """Peg from the board face (z=0) into the board (z<0), tip chamfered."""
    if taper_to is None:
        s = cq.Workplane("XY").circle(d / 2).extrude(-length)
        if tip_ch > 0:
            s = s.faces("<Z").chamfer(tip_ch)
    else:
        # cone: root d at z=0, taper_to at the tip
        s = (cq.Workplane("XY").circle(d / 2)
             .workplane(offset=-length).circle(taper_to / 2).loft())
        if tip_ch > 0:
            s = s.faces("<Z").chamfer(tip_ch)
    return s.translate((x, y, 0))


def label(solid, text, size, face_z, x, y, depth=0.4, bold=True):
    """Recess text into the face at z = face_z (text reads from +Z)."""
    kw = {"fontPath": FONT} if FONT else {}
    t = (cq.Workplane("XY").workplane(offset=face_z - depth)
         .center(x, y).text(text, size, depth, combine=False, halign="center", valign="center",
                            kind="bold" if bold else "regular", **kw))
    return solid.cut(t)


def rolled_j(d, y, shaft, bend_r, tip):
    """
    Upper hook for a thin board: straight shaft of Ø d from z=0 to z=-shaft,
    quarter bend (torus section) of centreline radius bend_r rising in +Y,
    then `tip` mm straight up with a rounded end. Built from revolve /
    extrude primitives (a sphere cap tessellates with open pole edges).
    """
    z1 = -shaft
    shaft_c = cq.Workplane("XY").center(0, y).circle(d / 2).extrude(z1)
    bend = (cq.Workplane("XY").workplane(offset=z1).center(0, y).circle(d / 2)
            .revolve(90, (0, bend_r, 0), (1, bend_r, 0)))
    ey, ez = y + bend_r, z1 - bend_r                 # end of the bend, tangent +Y
    tip_c = (cq.Workplane("XZ").workplane(offset=-ey).center(0, ez).circle(d / 2)
             .extrude(-tip))                          # XZ normal is -Y: extrude(-tip) runs +Y
    tip_c = tip_c.faces(">Y").fillet(min(d / 2 - 0.5, tip - 0.5))
    return shaft_c.union(bend).union(tip_c).clean()


def j_hook_arm(w, reach, t, tip, bend_r, plate_t, y_bottom):
    """
    J arm leaving the plate front (z = plate_t) at the bottom edge: horizontal
    shelf `reach` long, `t` thick, tip rising `tip`, inner bend radius bend_r.
    Profile drawn in the YZ plane, extruded over the width.
    """
    y0, z0 = y_bottom, plate_t
    shelf = box(-w / 2, w / 2, y0, y0 + t, z0 - 0.01, z0 + reach)          # out from the plate
    lip = box(-w / 2, w / 2, y0, y0 + t + tip, z0 + reach - t, z0 + reach)  # rising tip
    arm = shelf.union(lip)
    # inner corner (shelf top meets lip) and outer corner (shelf bottom / lip outside)
    arm = arm.edges(cq.selectors.NearestToPointSelector((0, y0 + t, z0 + reach - t))).fillet(bend_r)
    arm = arm.edges(cq.selectors.NearestToPointSelector((0, y0, z0 + reach))).fillet(bend_r + t - 0.01)
    # soften the tip
    arm = arm.edges(cq.selectors.NearestToPointSelector((0, y0 + t + tip, z0 + reach))).fillet(t / 2 - 0.1)
    return arm


# ---------------------------------------------------------------- bodies (board coords)

def fit_plug(d, length, head_d, head_t, text, text_size):
    head = cq.Workplane("XY").circle(head_d / 2).extrude(head_t).edges(">Z").chamfer(0.6)
    s = head.union(peg(d, length, 0, 0, tip_ch=min(0.8, d * 0.12)))
    return label(s, text, text_size, head_t, 0, 0)


def row_bar(b, pitch, d, length, text):
    w, h, t = pitch + 14, 10.0, 3.0
    xc = pitch / 2                                   # pegs on hole (0,0) and pitch along the row
    bar = box(xc - w / 2, xc + w / 2, -h / 2, h / 2, 0, t).edges("|Z").fillet(2.0)
    for x in (0.0, pitch):
        bar = bar.union(peg(d, length, x, 0, tip_ch=0.6))
    return label(bar, text, 4.0, t, xc, 0)


def hook_imperial(b, mode):
    """Two pegs one row apart (23.876), J-hook arm. mode: 'str' | 'tpr'."""
    pw, ph, pt = 20.0, 44.0, 4.0
    y_lo, y_hi = hole_xy(b, 0, 0)[1], hole_xy(b, 0, 1)[1]      # holes (0,0) and (0,1)
    yc = (y_lo + y_hi) / 2
    plate = box(-pw / 2, pw / 2, yc - ph / 2, yc + ph / 2, 0, pt).edges("|Z").fillet(3.0)
    L = 16.0
    for y in (y_hi, y_lo):
        if mode == "str":
            plate = plate.union(peg(7.0, L, 0, y, tip_ch=1.0))
        else:
            plate = plate.union(peg(7.4, L, 0, y, tip_ch=1.0, taper_to=6.8))
    arm = j_hook_arm(pw, reach=25.0, t=6.0, tip=12.0, bend_r=4.0, plate_t=pt, y_bottom=yc - ph / 2)
    s = plate.union(arm)
    s = label(s, "STR" if mode == "str" else "TPR", 5.0, pt, 0, yc + 10.0)
    return s


def hook_metric(b, shaft_d):
    """Rolled J one row up (y=+13.22), straight stop peg two rows down (26.44 lower)."""
    pw, ph, pt = 16.0, 40.0, 4.0
    y_lo, y_hi = hole_xy(b, 0, 0)[1], hole_xy(b, 0, 2)[1]      # same column, two rows apart (26.44)
    yc = (y_lo + y_hi) / 2
    plate = box(-pw / 2, pw / 2, yc - ph / 2, yc + ph / 2, 0, pt).edges("|Z").fillet(3.0)
    hook = rolled_j(shaft_d, y_hi, shaft=b["t"] + 1.5, bend_r=5.0, tip=2.5)
    stop = peg(4.0, b["t"] + 1.0, 0, y_lo, tip_ch=0.8)
    arm = j_hook_arm(pw, reach=20.0, t=5.0, tip=10.0, bend_r=3.0, plate_t=pt, y_bottom=yc - ph / 2)
    s = plate.union(hook).union(stop).union(arm)
    return label(s, f"J{shaft_d:.1f}", 4.0, pt, 0, yc + 6.0)


def mount(b, holes, peg_d, peg_len, text, margin=8.0, t=4.0, grip=True):
    """
    Flat plate with one straight peg per listed hole (ix, iy). Prints face
    down, pegs up. A finger slot through the plate (or a notch on a bar)
    gives something to pull on. Label recessed in the front face.
    """
    pts = [hole_xy(b, ix, iy) for ix, iy in holes]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin
    plate = box(x0, x1, y0, y1, 0, t).edges("|Z").fillet(3.0)
    for x, y in pts:
        plate = plate.union(peg(peg_d, peg_len, x, y, tip_ch=min(1.0, peg_d * 0.12)))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    if grip and len(pts) == 4:                      # finger slot in the middle of the 2x2
        slot = cq.Workplane("XY").slot2D(14.0, 7.0).extrude(t + 1).translate((cx, cy, -0.5))
        plate = plate.cut(slot)
        plate = label(plate, text, 5.0, t, cx, cy + 9.0)
    elif grip:                                      # 2-hole: notch at each end of the long axis
        if w >= h:
            for sx in (-1, 1):
                plate = plate.cut(cq.Workplane("XY").circle(3.0).extrude(t + 1).translate((cx + sx * (w / 2), cy, -0.5)))
            plate = label(plate, text, 4.0, t, cx, cy + 0.0 if h > 18 else cy)
        else:
            for sy in (-1, 1):
                plate = plate.cut(cq.Workplane("XY").circle(3.0).extrude(t + 1).translate((cx, cy + sy * (h / 2), -0.5)))
            plate = label(plate, text, 4.0, t, cx, cy)
    return plate


# ---------------------------------------------------------------- board stub for interference checks

def board_stub(b, nx=3, ny=5):
    w = (nx + 1) * b["pitch_x"]
    h = (ny + 1) * b["pitch_y"]
    stub = box(-w / 2, w / 2, -h / 2 - b["pitch_y"], h / 2 + b["pitch_y"], -b["t"], 0)
    for iy in range(-ny, ny + 1):
        for ix in range(-nx, nx + 1):
            x, y = hole_xy(b, ix, iy)
            if abs(x) < w / 2 and abs(y) < h / 2 + b["pitch_y"]:
                stub = stub.cut(cq.Workplane("XY").circle(b["hole_d"] / 2).extrude(-b["t"] - 1).translate((x, y, 0.5)))
    return stub


# ---------------------------------------------------------------- bed layout

def lay(obj, orient):
    """Rotate a board-coordinate body onto the bed (z >= 0). orient: 'face' | 'side'."""
    if orient == "face":        # front face down, pegs up
        o = obj.rotate((0, 0, 0), (1, 0, 0), 180)
    else:                       # on its side: X becomes Z
        o = obj.rotate((0, 0, 0), (0, 1, 0), 90)
    bb = o.val().BoundingBox()
    return o.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def place(bodies, gap=8.0):
    """Row-pack bodies left to right; returns [(name, solid)] in bed coordinates."""
    out, x = [], 0.0
    for name, s in bodies:
        bb = s.val().BoundingBox()
        out.append((name, s.translate((x, 0, 0))))
        x += bb.xlen + gap
    return out


# ---------------------------------------------------------------- 3MF with one object per body

def write_3mf(parts, title):
    """Minimal 3MF: each (name, cq solid) becomes its own object, so the
    slicer lists them separately (Bambu Studio: one object each)."""
    objs, items = [], []
    for i, (name, s) in enumerate(parts, 1):
        verts, tris = s.val().tessellate(0.005, 0.05)
        vs = "".join(f'<vertex x="{v.x:.4f}" y="{v.y:.4f}" z="{v.z:.4f}"/>' for v in verts)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        objs.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
                    f'<triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><resources>{"".join(objs)}</resources>'
             f'<build>{"".join(items)}</build></model>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return buf.getvalue()


def stl_stats(path):
    """Triangle count and a closed-mesh check (every edge used exactly twice)."""
    with open(path, "rb") as fh:
        data = fh.read()
    n = struct.unpack("<I", data[80:84])[0]
    edges = {}
    off = 84
    for _ in range(n):
        tri = struct.unpack("<12fH", data[off:off + 50])
        off += 50
        v = [tuple(round(c, 4) for c in tri[3 + 3 * k:6 + 3 * k]) for k in range(3)]
        for a, b in ((v[0], v[1]), (v[1], v[2]), (v[2], v[0])):
            k = (a, b) if a < b else (b, a)
            edges[k] = edges.get(k, 0) + 1
    bad = sum(1 for c in edges.values() if c != 2)
    return n, bad


# ---------------------------------------------------------------- main

def build_imperial():
    b = BOARDS["imperial_19"]
    d, L = 7.0, 16.0
    bodies_board = [
        ("mount_2V", mount(b, [(0, 0), (0, 1)], d, L, "2V")),
        ("mount_2H", mount(b, [(0, 0), (1, 0)], d, L, "2H")),
        ("mount_4",  mount(b, [(0, 0), (1, 0), (0, 1), (1, 1)], d, L, "4")),
    ] + [(f"plug_{dd:.1f}", fit_plug(dd, 16.0, 16.0, 3.0, f"{dd:.1f}", 5.0))
         for dd in (6.6, 6.8, 7.0, 7.2, 7.4)]
    bed = [(n, lay(s, "face")) for n, s in bodies_board]
    return b, bodies_board, place(bed)


def build_metric():
    b = BOARDS["metric_4"]
    d, L = 4.2, 5.0
    # same-column holes are two rows apart (26.44); in-row neighbours 26.44 apart
    bodies_board = [
        ("mount_2V", mount(b, [(0, 0), (0, 2)], d, L, "2V", margin=7.0)),
        ("mount_2H", mount(b, [(0, 0), (1, 0)], d, L, "2H", margin=7.0)),
        ("mount_4",  mount(b, [(0, 0), (1, 0), (0, 2), (1, 2)], d, L, "4", margin=7.0)),
        ("rowbar_23.9", row_bar(b, 23.876, d, L, "23.9")),      # fits only if the in-row pitch is 23.876
        ("hook_J3.8", hook_metric(b, 3.8)),
    ] + [(f"plug_{dd:.1f}", fit_plug(dd, 6.0, 12.0, 3.0, f"{dd:.1f}", 4.0))
         for dd in (3.9, 4.1, 4.3, 4.5)]
    bed = [(n, lay(s, "side" if n.startswith("hook") else "face")) for n, s in bodies_board]
    return b, bodies_board, place(bed)


def check(b, bodies_board):
    """Validity, volume, and interference with the board stub at nominal hole size."""
    stub = board_stub(b)
    rows = []
    for name, s in bodies_board:
        shape = s.val()
        inter = s.intersect(stub)
        iv = inter.val().Volume() if inter.solids().size() else 0.0
        rows.append((name, shape.isValid(), round(shape.Volume() / 1000, 2), round(iv, 3)))
    return rows


def export(tag, b, bodies_board, bed):
    names = []
    comp = cq.Workplane("XY").newObject([cq.Compound.makeCompound([s.val() for _, s in bed])])
    stl = os.path.join(OUT, f"coupon_{tag}.stl")
    cq.exporters.export(comp, stl, tolerance=0.005, angularTolerance=0.05)
    cq.exporters.export(comp, os.path.join(OUT, f"coupon_{tag}.step"))
    with open(os.path.join(OUT, f"coupon_{tag}.3mf"), "wb") as fh:
        fh.write(write_3mf(bed, f"PEGBOARDLAB coupon {tag}"))
    for n, s in bed:
        p = os.path.join(OUT, f"coupon_{tag}_{n}.stl")
        cq.exporters.export(s, p, tolerance=0.005, angularTolerance=0.05)
        names.append(p)
    bb = comp.val().BoundingBox()
    return stl, (round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)), names


if __name__ == "__main__":
    report = []
    for tag, fn in (("imperial", build_imperial), ("metric", build_metric)):
        b, bodies_board, bed = fn()
        rows = check(b, bodies_board)
        stl, size, names = export(tag, b, bodies_board, bed)
        n, bad = stl_stats(stl)
        report.append(f"== {tag}: {b['label']}\n   plate {size[0]} x {size[1]} x {size[2]} mm, "
                      f"{n} triangles, {bad} open edges")
        for name, ok, vol, iv in rows:
            flag = "" if (ok and iv < 1e-3) else "   <-- CHECK"
            report.append(f"   {name:20s} valid={ok} vol={vol:6.2f} cm3 interference={iv:.3f} mm3{flag}")
    print("\n".join(report))
    with open(os.path.join(OUT, "coupons_report.txt"), "w") as fh:
        fh.write("\n".join(report) + "\n")
