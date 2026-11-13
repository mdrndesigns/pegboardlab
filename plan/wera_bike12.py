#!/usr/bin/env python3
"""
WERA BICYCLE SET 12 (05004181001) - quick-draw stand for the twelve Joker 6003
spanners (6-14, 15 pedal, 16, 17) on the imperial board A. STAND family on twin
bars, two-part. Writes the printable 3MF, the STLs, the parameters and two
snapshots (with and without the spanners) to plan/wera_bike12/.
"""
import json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import cadquery as cq
import geometry as G
import model as M
from families import stand as SD

OUT = os.path.join(HERE, "wera_bike12")
NAME = "WERA-BIKE12"

# size, overall length (Wera data sheet); head / ring / thickness are estimates for the proxies only
SET = [(6, 105), (7, 110), (8, 115), (9, 120), (10, 125), (11, 135), (12, 148), (13, 160), (14, 167), (15, 174), (16, 182), (17, 190)]
PARAMS = dict(family="stand", split="two", brand_src="none", mt_bars="twin", mt_span=8, mt_fill="plate")


def tris_of(shape, tol=0.08, ang=0.3):
    data = G.stl_bytes(shape, tol, ang)[0]
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(float)


def spanner(size, length, x, foot_z, thick):
    """Proxy spanner standing edge-on at x: open end down at foot_z from the board, ring leaning on the board."""
    hw, ring, sw = 2.1 * size + 3.5, 1.45 * size + 2.0, 0.55 * size + 3.5
    hl = hw * 0.95
    prof = (cq.Workplane("XY").ellipse(hw / 2, hl / 2).extrude(thick / 2, both=True)
            .cut(cq.Workplane("XY").center(0, -hl / 2).rect(size, hl).extrude(thick, both=True)))
    shank = cq.Workplane("XY").center(0, (length - hl / 2 - ring / 2) / 2).rect(sw, length - hl / 2 - ring / 2).extrude(thick / 2 * 0.8, both=True)
    top = length - hl / 2 - ring / 2
    rg = (cq.Workplane("XY").center(0, top).circle(ring / 2).extrude(thick / 2, both=True)
          .cut(cq.Workplane("XY").center(0, top).polygon(12, size * 1.08).extrude(thick, both=True)))
    w = prof.union(shank).union(rg).translate((0, hl / 2, 0))        # foot at y = 0, plane XY, axis +Y
    w = w.rotate((0, 0, 0), (0, 1, 0), 90)                           # edge-on: plane YZ
    lean = math.degrees(math.asin(max(0.0, min(0.9, (foot_z - ring / 2) / (length - hl / 2 - ring / 2)))))
    w = w.rotate((0, 0, 0), (1, 0, 0), -lean)                        # top toward the board (-Z)
    return w.translate((x, 0, foot_z)), lean


def raster(layers, png, size=(2000, 1300), elev=20, azim=-32):
    """Orthographic z-buffer render. layers = [(tris, rgb)], black silhouette lines from depth steps."""
    from PIL import Image
    a, e = math.radians(azim), math.radians(elev)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    R = Rx @ Ry
    allp = np.concatenate([t.reshape(-1, 3) for t, _ in layers]) @ R.T
    lo, hi = allp.min(0), allp.max(0)
    W, H = size
    s = min((W - 120) / (hi[0] - lo[0]), (H - 120) / (hi[1] - lo[1]))
    ox, oy = (W - s * (hi[0] - lo[0])) / 2, (H - s * (hi[1] - lo[1])) / 2
    zbuf = np.full((H, W), -1e9)
    img = np.ones((H, W, 3))
    ident = np.zeros((H, W), dtype=int)
    light = np.array([-0.35, 0.55, 0.75]); light /= np.linalg.norm(light)
    for li, (tris, rgb) in enumerate(layers, 1):
        P = tris @ R.T
        nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(nrm, axis=1); ln[ln == 0] = 1
        shade = 0.42 + 0.58 * np.abs((nrm / ln[:, None]) @ light)
        X = (P[:, :, 0] - lo[0]) * s + ox
        Y = H - ((P[:, :, 1] - lo[1]) * s + oy)
        Z = P[:, :, 2]
        for k in range(len(P)):
            x, y, z = X[k], Y[k], Z[k]
            x0, x1 = max(int(x.min()), 0), min(int(x.max()) + 1, W - 1)
            y0, y1 = max(int(y.min()), 0), min(int(y.max()) + 1, H - 1)
            if x1 < x0 or y1 < y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            l2 = 1 - l0 - l1
            zz = l0 * z[0] + l1 * z[1] + l2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            m = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4) & (zz > sub)
            sub[m] = zz[m]
            img[y0:y1 + 1, x0:x1 + 1][m] = np.asarray(rgb) * shade[k] + (1 - shade[k]) * np.asarray(rgb) * 0.25
            ident[y0:y1 + 1, x0:x1 + 1][m] = li
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        dz = np.abs(zbuf - np.roll(zbuf, 1, axis=0 if dy else 1))
        edge |= (dz > 2.5 / 1.0) & (ident > 1) | ((ident != np.roll(ident, 1, axis=0 if dy else 1)) & ((ident > 1) | (np.roll(ident, 1, axis=0 if dy else 1) > 1)))
    img[edge] = 0
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((W // 2, H // 2), Image.LANCZOS).save(png)


def board_layer(xr, yr, pitch, hole_d, x_off):
    """Board face (z = 0) as two triangles and its holes as dark discs just in front."""
    x0, x1, y0, y1 = xr[0], xr[1], yr[0], yr[1]
    face = np.array([[[x0, y0, 0], [x1, y0, 0], [x1, y1, 0]], [[x0, y0, 0], [x1, y1, 0], [x0, y1, 0]]], float)
    discs = []
    i0, i1 = math.ceil((x0 + 8 - x_off) / pitch), math.floor((x1 - 8 - x_off) / pitch)
    j0, j1 = math.ceil((y0 + 8) / pitch), math.floor((y1 - 8) / pitch)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cx, cy = x_off + i * pitch, j * pitch
            for k in range(24):
                a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
                discs.append([[cx, cy, 0.05], [cx + hole_d / 2 * math.cos(a0), cy + hole_d / 2 * math.sin(a0), 0.05],
                              [cx + hole_d / 2 * math.cos(a1), cy + hole_d / 2 * math.sin(a1), 0.05]])
    return face, np.array(discs, float)


def main():
    os.makedirs(OUT, exist_ok=True)
    p = M.merge_params(PARAMS)
    M.apply_board(p, "imperial_19")
    errs = M.validate(p)
    assert not errs, errs
    body, spec, warns = M.build(p, export=True)
    parts, laid = M.parts_for_export(body, spec)
    report = []
    for n, sh in parts:
        stl, _ = G.stl_bytes(sh, 0.01, 0.1)
        ok = sh.isValid() and G.mesh_closed(stl) == 0
        bb = sh.BoundingBox()
        report.append(f"{n:8s} {'ok ' if ok else 'BAD'} {bb.xlen:6.1f} × {bb.ylen:5.1f} × {bb.zlen:5.1f}  {sh.Volume() / 1000:6.1f} cm³")
        assert ok, n
        if n in ("holder", "spine1"):
            open(os.path.join(OUT, f"{NAME}_{'spine' if n == 'spine1' else n}.stl"), "wb").write(stl)
    open(os.path.join(OUT, f"{NAME}.3mf"), "wb").write(G.write_3mf([(f"{NAME}_{n}", sh) for n, sh in parts], NAME, one_object=False))
    asm = M.assembly(body, spec)
    cq.exporters.export(asm, os.path.join(OUT, f"{NAME}_assembly.step"))
    json.dump(p, open(os.path.join(OUT, f"{NAME}_params.json"), "w"), indent=1, default=str)

    # --- snapshots
    b = M.board_of(p)
    pitch = float(b["pitch_x"])
    bar_x = spec["plan"]["bars"][0]
    face, holes = board_layer((-150, 150), (-55, 215), pitch, float(b["hole_d"]), bar_x)
    holder = tris_of(asm.val())
    t_front = spec["spine_t"] + spec["t"]
    ch = SD.channels(p)
    yf = -spec["h"] / 2 + float(p["sd_floor"])
    sp_tris, leans = [], []
    for (size, length), (x, cw, fl) in zip(SET, ch):
        hw = 2.1 * size + 3.5
        foot_z = t_front + fl + 1.0 - 1.0 - hw * 0.95 / 2 - 0.5
        thick = max(3.0, cw - 2.0)
        w, lean = spanner(size, length, x, foot_z, thick)
        sp_tris.append(tris_of(w.translate((0, yf, 0)).val(), 0.1, 0.4))
        leans.append(lean)
    base = [(face, (0.95, 0.95, 0.95)), (holes, (0.72, 0.72, 0.72)), (holder, (0.0, 0.0, 1.0))]
    raster(base, os.path.join(OUT, f"{NAME}_empty.png"))
    raster(base + [(np.concatenate(sp_tris), (0.82, 0.82, 0.82))], os.path.join(OUT, f"{NAME}_loaded.png"))
    raster(base + [(np.concatenate(sp_tris), (0.82, 0.82, 0.82))], os.path.join(OUT, f"{NAME}_side.png"), elev=6, azim=-78)

    lines = [f"{NAME} · Wera Bicycle Set 12 · imperial board A", *report, "",
             *[f"{k}: {v}" for k, v in spec["derived"].items()], "",
             "channel (width × foot length) per spanner, lean on the board:",
             *[f"  {s:2d} × {L}   {cw:g} × {fl:g}   lean {ln:4.1f}°" for (s, L), (_, cw, fl), ln in zip(SET, ch, leans)],
             "", "warnings: " + ("; ".join(warns) or "none")]
    open(os.path.join(OUT, "summary.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
