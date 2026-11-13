#!/usr/bin/env python3
"""
Build every holder in plan/holders.py with PEGBOARDLAB, verify it, export
it and total the filament.

    python3 plan/build_prints.py            # all
    python3 plan/build_prints.py A2-07 A6-01  # a few

Writes plan/prints/<id>.3mf (holder + spine as separate objects, laid on
the bed), <id>_holder.stl, <id>_spine.stl, <id>_params.json, a thumbnail,
plan/prints_inventory.csv and plan/prints_summary.txt.

Filament: ABS-GF 1.08 g/cm³ (Bambu TDS). Printed mass = solid volume ×
density × fill factor; fill = 1.0 for walls under 3.4 mm (4 walls of
0.42), else a 4-wall / 3-top-bottom / 25 % infill estimate per part.
"""
import csv
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import cadquery as cq
import geometry as G
import model as M
from holders import HOLDERS

OUT = os.path.join(HERE, "prints")
os.makedirs(OUT, exist_ok=True)
DENSITY = 1.08          # g/cm³ ABS-GF
WALL = 4 * 0.42         # four perimeters
INFILL = 0.25


def fill_factor(shape):
    """Rough printed-fraction of a solid: shell is dense, core is 25 % infill."""
    v = shape.Volume()
    a = sum(f.Area() for f in shape.Faces())
    shell = min(v, a * WALL * 0.5)          # each face grows a wall inward; halve for double counting at edges
    core = max(0.0, v - shell)
    return (shell + core * INFILL) / v if v > 0 else 1.0


def build_one(hd):
    p = M.merge_params({})
    M.apply_board(p, hd["board"])
    p.update(hd["params"])
    errs = M.validate(p)
    if errs:
        return dict(status="refused", reason="; ".join(errs))
    t0 = time.time()
    body, spec, warns = M.build(p, export=True)
    parts, laid = M.parts_for_export(body, spec)
    # H2S bed 340 × 320: a part longer than 320 goes on the diagonal (35°) so it fits whatever way the slicer loads it
    fixed = []
    for n, sh in parts:
        bb = sh.BoundingBox()
        if max(bb.xlen, bb.ylen) > 320:
            c = bb.center
            sh = sh.rotate(cq.Vector(c.x, c.y, 0), cq.Vector(c.x, c.y, 1), 35)
        fixed.append((n, sh))
    parts = fixed
    der = M.derived(p, spec, laid)
    # verification
    valid = all(sh.isValid() for _, sh in parts)
    opens = [G.mesh_closed(G.stl_bytes(sh, 0.01, 0.1)[0]) for _, sh in parts]
    stub = M.context(p, spec, hole_pad=float(p["shrink"]) + 0.02)
    inter = 0.0
    if stub is not None and spec.get("spine") is not None:
        for sp in M.spine_parts(spec):
            ix = cq.Workplane("XY").add(sp).intersect(stub)
            inter += ix.val().Volume() if ix.solids().size() else 0.0
    # export
    name = hd["id"]
    with open(os.path.join(OUT, f"{name}.3mf"), "wb") as fh:
        fh.write(G.write_3mf([(f"{name}_{n}", sh) for n, sh in parts], name, one_object=False))
    vols = {}
    masses = {}
    for n, sh in parts:
        if n != "spine2":                       # twin bars: spine1 == spine2, one STL named spine
            with open(os.path.join(OUT, f"{name}_{'spine' if n == 'spine1' else n}.stl"), "wb") as fh:
                fh.write(G.stl_bytes(sh, 0.005, 0.05)[0])
        vols[n] = sh.Volume() / 1000.0
        masses[n] = vols[n] * DENSITY * fill_factor(sh)
    if "spine1" in masses:                      # twin bars: the two spines are one part, printed twice
        vols["spine"] = vols.pop("spine1") + vols.pop("spine2")
        masses["spine"] = masses.pop("spine1") + masses.pop("spine2")
    with open(os.path.join(OUT, f"{name}_params.json"), "w") as fh:
        json.dump(p, fh, indent=1)
    # thumbnail: line drawing of the assembly, front-left above, Y up
    comp = M.assembly(body, spec)
    svg = os.path.join(OUT, f"{name}.svg")
    for pd in ((-1, 0.9, 1.4), (-1.02, 0.91, 1.41), (-1, 1.0, 1.3)):      # OCC's hidden-line removal can trip on one view
        try:
            cq.exporters.export(comp, svg, opt={"projectionDir": pd, "width": 480, "height": 400, "marginLeft": 30,
                                                "marginTop": 30, "showHidden": False, "strokeWidth": 0.55, "strokeColor": (0, 0, 0),
                                                "showAxes": False})
            break
        except Exception:
            continue
    try:
        import cairosvg
        cairosvg.svg2png(url=svg, write_to=os.path.join(OUT, f"{name}.png"), output_width=480, background_color="white")
    except Exception:
        pass
    bb_h = parts[0][1].BoundingBox()
    bb_s = parts[-1][1].BoundingBox()
    return dict(status="ok" if (valid and not any(opens) and inter < 0.5) else "bad", valid=valid, open_edges=sum(opens),
                interference=round(inter, 2), secs=round(time.time() - t0, 1),
                holder_cm3=round(vols.get("holder", vols.get("base", 0)), 1), spine_cm3=round(vols.get("spine", 0), 1),
                holder_g=round(masses.get("holder", masses.get("base", 0)), 1), spine_g=round(masses.get("spine", 0), 1),
                holder_bed=f"{bb_h.xlen:.0f} × {bb_h.ylen:.0f} × {bb_h.zlen:.0f}",
                spine_bed=("2 × " if len(parts) > 2 else "") + f"{bb_s.xlen:.0f} × {bb_s.ylen:.0f} × {bb_s.zlen:.0f}",
                plate=der.get("plate"), screws=der.get("screws"), studs=der.get("studs"), spine=der.get("spine"),
                orient=der.get("orient"), unsupported=der.get("overhang_mm2"), warnings="; ".join(w for w in warns if "proud" not in w))


def main():
    only = set(sys.argv[1:])
    rows = []
    for hd in HOLDERS:
        if only and hd["id"] not in only:
            continue
        try:
            r = build_one(hd)
        except Exception as e:
            r = dict(status="fail", reason=f"{type(e).__name__}: {e}")
        r = dict(id=hd["id"], board=hd["board"], zone=hd["zone"], item=hd["item"], brand=hd["brand"], n=hd["n"],
                 family=hd["params"]["family"], **r)
        rows.append(r)
        print(f"{r['status']:7s} {r['id']:7s} ×{r['n']} {r['item'][:34]:34s} {r.get('holder_g', 0):6.1f} + {r.get('spine_g', 0):5.1f} g "
              f"{r.get('screws', r.get('reason', ''))}  {r.get('warnings', '')}", flush=True)
    keys = sorted(set(k for r in rows for k in r), key=lambda k: (k not in ("id", "board", "zone", "item", "brand", "n", "family", "status"), k))
    with open(os.path.join(HERE, "prints_inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r["status"] == "ok"]
    prints = sum(r["n"] for r in ok)
    g_holder = sum(r["holder_g"] * r["n"] for r in ok)
    g_spine = sum(r["spine_g"] * r["n"] for r in ok)
    cm3 = sum((r["holder_cm3"] + r["spine_cm3"]) * r["n"] for r in ok)
    screws = sum(int(str(r["screws"]).split(" ×")[0]) * r["n"] for r in ok if r.get("screws"))
    lines = [f"PEGBOARDLAB studio prints  {time.strftime('%Y-%m-%d %H:%M')}",
             f"holder designs {len(rows)}  ok {len(ok)}  not ok {len(rows) - len(ok)}",
             f"parts to print {prints} holders + {prints} spines = {2 * prints}",
             f"solid volume {cm3:.0f} cm³  ·  printed mass ≈ {g_holder + g_spine:.0f} g (holders {g_holder:.0f} + spines {g_spine:.0f})",
             f"ABS-GF at 1.08 g/cm³, 4 walls / 25 % infill; add ~12 % for purge, brims and failures → {1.12 * (g_holder + g_spine):.0f} g",
             f"rolls of 1 kg: {(1.12 * (g_holder + g_spine)) / 1000:.2f}",
             f"drywall screws Ø3.5 × 15 csk: {screws}", ""]
    for b in ("imperial_19", "metric_4"):
        rb = [r for r in ok if r["board"] == b]
        lines.append(f"{b}: {sum(r['n'] for r in rb)} holders, {sum((r['holder_g'] + r['spine_g']) * r['n'] for r in rb):.0f} g")
    lines.append("")
    for r in rows:
        if r["status"] != "ok":
            lines.append(f"{r['status']} {r['id']} {r.get('reason', '')} valid={r.get('valid')} open={r.get('open_edges')} int={r.get('interference')}")
    with open(os.path.join(HERE, "prints_summary.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
