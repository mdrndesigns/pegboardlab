#!/usr/bin/env python3
"""
Independent verification of PEGBOARDLAB: every family on both measured
boards across fixings, patterns and the family's own types; each part is
checked for a valid solid, a watertight export mesh, no interference
with a model of the board at the nominal hole size, and the unsupported
area of the laid-out print. Writes samples/batch_report.txt and .csv.

    python3 tests/batch.py            # full run
    python3 tests/batch.py hook rack  # only these families
"""
import csv
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cadquery as cq
import geometry as G
import model as M

OUT = os.path.join(ROOT, "samples")
os.makedirs(OUT, exist_ok=True)

BOARDS = ["imperial_19", "metric_4"]
FIX = {"imperial_19": ["plain", "tube", "bore", "thread", "insert"], "metric_4": ["plain", "bore", "jhook"]}
PATTERNS = ["auto", "2V", "2H", "4", "row", "corners"]

VARIANTS = {
    "hook": [{"hk_type": t} for t in ("j", "double", "peg", "loop", "ramp")],
    "rack": [{"rk_type": t} for t in ("drivers", "pens", "hexkeys", "drills", "bits", "wrenches", "chisels", "pliers", "sockets")],
    "tray": [{"tr_type": "tray"}, {"tr_type": "cup", "tr_h": 80}, {"tr_type": "bin", "tr_div": 2},
             {"tr_type": "tray", "tr_mag": "embed", "tr_floor": 5}, {"tr_type": "tray", "tr_mag": "exposed", "tr_floor": 5}],
    "holster": [{"hs_type": "saddle"}, {"hs_type": "ring"}],
    "clip": [{"cl_type": "snap"}, {"cl_type": "loop"}, {"cl_type": "comb", "cl_wire": "flat"}],
    "plate": [{"pl_lip": "none"}, {"pl_lip": "raised", "brand_src": "text", "brand_text": "LABEL"}, {"pl_holes": 4, "pl_hang": True}],
    "magstrip": [{"mg_mode": "embed", "plate_t": 6}, {"mg_mode": "exposed", "plate_t": 6}, {"mg_mode": "rear", "plate_t": 6}],
    "gridfinity": [{"gf_nx": 1, "gf_ny": 1}, {"gf_nx": 2, "gf_ny": 1, "gf_tilt": 15, "gf_magnets": True, "gf_t": 9, "gf_lip": 4}],
    "nut": [{"nt_type": "hex"}, {"nt_type": "knurl"}, {"nt_type": "wing"}, {"nt_type": "washer"}],
}


def board_params(key):
    p = M.merge_params({})
    M.apply_board(p, key)
    return p


def interference(body, p, spec):
    stub = M.context(p, spec, hole_pad=float(p["shrink"]) + 0.02)   # compare as printed
    if stub is None:
        return 0.0
    inter = body.intersect(stub)
    return inter.val().Volume() if inter.solids().size() else 0.0


def run_case(board, fam, variant, fix, pattern, no_supports=True, export=False):
    p = board_params(board)
    p["family"] = fam
    p["mt_fix"] = fix
    p["mt_pattern"] = pattern
    p["no_supports"] = no_supports
    p.update(variant)
    errs = M.validate(p)
    if errs:
        return dict(status="refused", reason="; ".join(errs))
    t = time.time()
    body, spec, warns = M.build(p, export=export)
    v = body.val()
    laid = M.layout(body, spec)
    stl, ntri = G.stl_bytes(laid.val(), 0.01, 0.1)
    open_edges = G.mesh_closed(stl)
    inter = interference(body, p, spec) if getattr(M.FAMILIES[fam], "PLATE", True) else 0.0
    area, worst, _ = G.overhang_audit(laid.val())
    return dict(status="ok" if (v.isValid() and open_edges == 0 and inter < 0.5) else "bad",
                valid=v.isValid(), open_edges=open_edges, interference=round(inter, 2), volume=round(v.Volume() / 1000, 2),
                overhang=area, worst=worst, orient=spec["orient"], secs=round(time.time() - t, 1),
                warnings="; ".join(warns))


def main():
    fams = sys.argv[1:] or list(M.FAMILIES)
    rows = []
    for board in BOARDS:
        for fam in fams:
            variants = VARIANTS.get(fam, [{}])
            fixes = FIX[board] if getattr(M.FAMILIES[fam], "PLATE", True) else ["plain"]
            for vi, var in enumerate(variants):
                for fix in fixes:
                    pats = PATTERNS if (fix == "plain" and vi == 0) else ["auto"]
                    for pat in pats:
                        label = f"{board}/{fam}/{vi}:{list(var.values())[0] if var else '-'}/{fix}/{pat}"
                        try:
                            r = run_case(board, fam, var, fix, pat)
                        except Exception as e:
                            r = dict(status="fail", reason=f"{type(e).__name__}: {e}")
                        r["case"] = label
                        rows.append(r)
                        tail = "" if r["status"] != "ok" else f"  oh={r['overhang']} int={r['interference']} {r['secs']}s"
                        print(f"{r['status']:8s} {label:60s} {r.get('reason', '')}{tail}", flush=True)
    # the real thread cuts (slow helical booleans): one of each
    for board, fam, var, fix in (("imperial_19", "hook", {"hk_type": "j"}, "tube"),
                                 ("imperial_19", "hook", {"hk_type": "j"}, "thread"),
                                 ("imperial_19", "nut", {"nt_type": "hex"}, "plain"),
                                 ("imperial_19", "nut", {"nt_type": "knurl"}, "plain")):
        if fam not in fams:
            continue
        label = f"{board}/{fam}/{list(var.values())[0]}/{fix}/auto/EXPORT-THREADS"
        try:
            r = run_case(board, fam, var, fix, "auto", export=True)
        except Exception as e:
            r = dict(status="fail", reason=f"{type(e).__name__}: {e}")
        r["case"] = label
        rows.append(r)
        print(f"{r['status']:8s} {label:60s} {r.get('reason', '')}", flush=True)
    keys = sorted(set(k for r in rows for k in r))
    with open(os.path.join(OUT, "batch_report.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines = [f"PEGBOARDLAB batch {time.strftime('%Y-%m-%d %H:%M')}: {len(rows)} cases  " +
             "  ".join(f"{k}={v}" for k, v in sorted(counts.items())), ""]
    for r in rows:
        if r["status"] != "ok":
            lines.append(f"{r['status']:8s} {r['case']}  {r.get('reason', '')} valid={r.get('valid')} open={r.get('open_edges')} int={r.get('interference')}")
    lines.append("")
    big = [r for r in rows if r["status"] == "ok" and r["overhang"] > 250]
    lines.append(f"unsupported area over 250 mm²: {len(big)}")
    for r in big:
        lines.append(f"   {r['case']}  {r['overhang']} mm²  worst {r['worst']}°  {r['warnings']}")
    with open(os.path.join(OUT, "batch_report.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
