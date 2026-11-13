#!/usr/bin/env python3
"""
Kit + twin-bar verification: every tool of every kit family (Bosch 12V, Wera,
Irwin, Measure) on both measured boards, two-part, plus twin bars on every
plate family. Each case: valid solids, watertight meshes, nothing inside the
board (printed stud size), screws per bar. Report -> samples/kits_report.txt

    python3 tests/kits.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cadquery as cq
import geometry as G
import model as M

BOARDS = ("imperial_19", "metric_4")


def check(p):
    body, spec, warns = M.build(p, export=True)
    parts, laid = M.parts_for_export(body, spec)
    d = M.derived(p, spec, laid)
    valid = all(sh.isValid() for _, sh in parts)
    opens = sum(G.mesh_closed(G.stl_bytes(sh, 0.01, 0.1)[0]) for _, sh in parts)
    inter = 0.0
    stub = M.context(p, spec, hole_pad=float(p["shrink"]) + 0.02)
    if stub is not None:
        for sp in M.spine_parts(spec):
            ix = cq.Workplane("XY").add(sp).intersect(stub)
            inter += ix.val().Volume() if ix.solids().size() else 0.0
        ix = body.translate((0, 0, spec.get("spine_t", 0.0))).intersect(stub)
        inter += ix.val().Volume() if ix.solids().size() else 0.0
    nd = len(spec.get("dims", []))
    bad_dim = [x for x in spec.get("dims", []) if any(v != v for v in x["a"] + x["b"] + x["o"])]      # NaN guard
    ok = valid and opens == 0 and inter < 0.5 and nd >= 3 and not bad_dim
    return ok, dict(valid=valid, opens=opens, inter=round(inter, 2), parts=len(parts), dims=nd, screws=d.get("screws"), bars=d.get("bars"),
                    pair=d.get("pair"), size=d.get("print_size"), unsupported=d.get("overhang_mm2"), warns=warns)


def main():
    rows, bad = [], 0
    t0 = time.time()
    for board in BOARDS:
        for fam in ("bosch", "wera", "irwin", "measure"):
            mod = M.FAMILIES[fam]
            for tool in mod.TOOLS:
                p = M.merge_params({})
                M.apply_board(p, board)
                p.update(dict(family=fam, split="two", brand_src="none"))
                p[mod.PREFIX + "tool"] = tool
                errs = M.validate(p)
                if errs:
                    rows.append(f"REFUSED {board:12s} {fam:8s} {tool:11s} {errs}")
                    continue
                try:
                    ok, r = check(p)
                except Exception as e:
                    ok, r = False, dict(error=f"{type(e).__name__}: {e}")
                bad += not ok
                rows.append(f"{'ok ' if ok else 'BAD'} {board:12s} {fam:8s} {tool:11s} {r}")
                print(rows[-1][:150], flush=True)
        for fam in ("pocket", "arm", "rack", "tray", "holster", "hook", "plate", "magstrip", "gridfinity", "clip"):
            for split in ("two", "one"):
                p = M.merge_params({})
                M.apply_board(p, board)
                p.update(dict(family=fam, split=split, brand_src="none", mt_bars="twin", mt_span=4))
                if fam == "pocket":
                    p.update(pk_w=130, pk_cuts=[dict(kind="slot", x=x, z=20, w=5, l=14) for x in range(-44, 45, 11)])
                errs = M.validate(p)
                if errs:
                    rows.append(f"REFUSED {board:12s} twin {fam:8s} {split} {errs}")
                    continue
                try:
                    ok, r = check(p)
                except Exception as e:
                    ok, r = False, dict(error=f"{type(e).__name__}: {e}")
                bad += not ok
                rows.append(f"{'ok ' if ok else 'BAD'} {board:12s} twin {fam:10s} {split:3s} {r}")
                print(rows[-1][:150], flush=True)
    # per-feature size lists, typed pocket cut-outs, filled twin bars
    extra = [
        dict(family="rack", rk_type="wrenches", rk_sizes="4.5, 4.5, 6, 8, 10", mt_bars="twin", mt_span=2, mt_fill="plate"),
        dict(family="rack", rk_type="drivers", rk_sizes="6, 8, 10, 12", rk_rows=1),
        dict(family="rack", rk_type="chisels", rk_sizes="20, 26, 32"),
        dict(family="rack", rk_type="sockets", rk_rows=2, mt_bars="twin"),
        dict(family="pocket", pk_spec="slot 4.5x17 @9, slot 3.5x17 @9, hole 12 d20, open 11.8 keep, peg 6.25 h10, 20x3"),
        dict(family="irwin", ir_tool="drivers", ir_drivers_sizes="6, 6, 9, 9, 5, 4, 3"),
        dict(family="wera", we_tool="kraftform", we_kraftform_sizes="6, 6, 8, 9.5"),
        dict(family="measure", me_tool="wrenches", me_wrenches_slots="3.6x11, 3.6x11, 5x14, 6.8x21"),
        dict(family="measure", me_tool="rules", me_rules_hole_sizes="8, 10, 12, 14"),
        dict(family="gridfinity", mt_bars="twin", mt_fill="plate"),
        # v3.3: fill controls, braces, bolt and screw fixings, head seats
        dict(family="rack", rk_type="wrenches", mt_bars="twin", mt_fill="plate", mt_fill_r=8, mt_fill_t=6),
        dict(family="pocket", pk_w=146, mt_bars="twin", mt_fill="strip", mt_fill_r=0.5, mt_fill_t=3),
        dict(family="rack", rk_web_shape="wall", rk_web_t=4, rk_web_run=20, rk_web_h=12),
        dict(family="rack", rk_web_t=5, rk_web_h=40, mt_bars="twin", mt_fill="plate"),
        dict(family="gridfinity", gf_web_shape="wall", gf_web_t=4, gf_web_run=25),
        dict(family="rack", mt_fix="bore", mt_bolt_from="back", mt_nut="captive"),
        dict(family="rack", mt_fix="bore", mt_bolt_from="back", mt_nut="loose"),
        dict(family="rack", mt_fix="bore", mt_bolt_from="front", mt_head="csk"),
        dict(family="arm", mt_fix="bore", mt_bolt_from="front", mt_head="pan", split="one"),
        dict(family="arm", mt_fix="bore", mt_bolt_from="front", mt_head="none", split="one"),
        dict(family="rack", mt_fix="screw", mt_head="csk"),
        dict(family="pocket", pk_w=146, mt_bars="twin", mt_fix="screw", mt_head="pan"),
        dict(family="arm", mt_fix="screw", mt_head="none", mt_screw_d=4),
        dict(family="measure", me_tool="wrenches", mt_fix="screw"),
        dict(family="rack", screw_seat="pan", screw_head_h=3),
        dict(family="arm", screw_seat="pan"),
    ]
    for c in extra:
        p = M.merge_params(dict(split="two", brand_src="none") | c)
        M.apply_board(p, "imperial_19")
        try:
            ok, r = check(p)
        except Exception as e:
            ok, r = False, dict(error=f"{type(e).__name__}: {e}")
        bad += not ok
        rows.append(f"{'ok ' if ok else 'BAD'} imperial_19  lists {c['family']:10s} {r}")
        print(rows[-1][:150], flush=True)
    os.makedirs(os.path.join(ROOT, "samples"), exist_ok=True)
    with open(os.path.join(ROOT, "samples", "kits_report.txt"), "w") as fh:
        fh.write(f"PEGBOARDLAB kit + twin-bar verification · {time.strftime('%Y-%m-%d %H:%M')} · {len(rows)} cases · {bad} bad · {time.time() - t0:.0f} s\n\n")
        fh.write("\n".join(rows) + "\n")
    print(f"{len(rows)} cases, {bad} bad, {time.time() - t0:.0f} s")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
