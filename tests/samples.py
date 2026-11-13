#!/usr/bin/env python3
"""Showcase exports: one STL (print orientation) + preview PNG per sample."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import geometry as G
import model as M
from render import render

OUT = os.path.join(ROOT, "samples")
os.makedirs(OUT, exist_ok=True)

MET = dict(board="metric_4")

SAMPLES = {
    "hook_j_imperial":        dict(family="hook", hk_type="j", brand_src="text", brand_text="CHISELS"),
    "hook_double_imperial":   dict(family="hook", hk_type="double", hk_gap=40, hk_reach=45),
    "hook_loop_imperial":     dict(family="hook", hk_type="loop", hk_w=30, hk_loop_h=24),
    "rack_drivers_imperial":  dict(family="rack", rk_type="drivers", rk_n=6),
    "rack_bits_imperial":     dict(family="rack", rk_type="bits", rk_n=8, rk_rows=2),
    "rack_wrenches_imperial": dict(family="rack", rk_type="wrenches", rk_n=5, rk_d=10),
    "tray_bin_magnets":       dict(family="tray", tr_type="bin", tr_div=1, tr_mag="embed", tr_floor=5, tr_mag_n=3),
    "holster_drill_imperial": dict(family="holster", hs_type="saddle", hs_inner_w=40, hs_inner_d=45),
    "clip_snap_imperial":     dict(family="clip", cl_type="snap", cl_n=3, cl_d=5),
    "plate_label_imperial":   dict(family="plate", pl_w=96, pl_h=36, pl_lip="raised", brand_src="text", brand_text="HEX KEYS", brand_size=12),
    "magstrip_embed":         dict(family="magstrip", mg_mode="embed", plate_t=6, mg_n=5, mg_size="10x3"),
    "gridfinity_2x1_tilt":    dict(family="gridfinity", gf_nx=2, gf_ny=1, gf_tilt=12, gf_lip=4, gf_magnets=True, gf_t=9),
    "nut_knurl_imperial":     dict(family="nut", nt_type="knurl", mt_fix="thread"),
    "hook_j_metric_jhook":    dict(family="hook", hk_type="j", mt_fix="jhook", mt_pattern="2V", **MET),
    "rack_pens_metric_bore":  dict(family="rack", rk_type="pens", rk_n=5, rk_rows=2, rk_d=12, mt_fix="bore", mt_bolt=4, **MET),
    "tray_cup_metric":        dict(family="tray", tr_type="cup", tr_w=60, tr_depth=60, tr_h=70, **MET),
}


def main():
    only = sys.argv[1:]
    index = {}
    for name, over in SAMPLES.items():
        if only and name not in only:
            continue
        p = M.merge_params({})
        M.apply_board(p, over.get("board", "imperial_19"))
        p.update({k: v for k, v in over.items() if k != "board"})
        errs = M.validate(p)
        if errs:
            print(name, "REFUSED", errs)
            continue
        body, spec, warns = M.build(p, export=True)
        parts, laid = M.parts_for_export(body, spec)
        der = M.derived(p, spec, laid)
        stl = os.path.join(OUT, f"{name}.stl")
        data, _ = G.stl_bytes(parts[0][1], 0.005, 0.05)
        if len(parts) > 1:
            data = G.stl_merge(data, G.stl_bytes(parts[1][1], 0.005, 0.05)[0])
        open(stl, "wb").write(data)
        open(os.path.join(OUT, f"{name}_parameters.json"), "w").write(json.dumps(p, indent=1))
        render(stl, os.path.join(OUT, f"{name}_preview.png"), title=f"{name}  ·  {der['orient']}")
        index[name] = {"derived": der, "warnings": warns}
        print(f"{name:26s} {der['print_size']:20s} unsupported {der['overhang_mm2']} mm²  {'; '.join(warns)}")
    open(os.path.join(OUT, "samples_index.json"), "w").write(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
