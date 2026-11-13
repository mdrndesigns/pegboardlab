#!/usr/bin/env python3
"""Quick build of every family on both boards with default settings."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import cadquery as cq
import model as M
import geometry as G

boards = sys.argv[1:] or ["imperial_19", "metric_4"]
fails = 0
for board in boards:
    for fam in M.FAMILIES:
        p = M.merge_params({})
        M.apply_board(p, board)
        p["family"] = fam
        if board == "metric_4" and fam != "nut":
            p["mt_fix"] = "plain"
        errs = M.validate(p)
        if errs:
            print(f"{board:12s} {fam:10s} REFUSED {errs}")
            continue
        t = time.time()
        try:
            body, spec, warns = M.build(p)
            laid = M.layout(body, spec)
            d = M.derived(p, spec, laid)
            v = body.val()
            ok = v.isValid()
            print(f"{board:12s} {fam:10s} {'ok ' if ok else 'BAD'} {time.time() - t:4.1f}s vol={v.Volume() / 1000:6.2f} "
                  f"orient={spec['orient']:8s} overhang={d.get('overhang_mm2')}mm² worst={d.get('overhang_worst')}° "
                  f"studs={d.get('studs')} {('WARN: ' + '; '.join(warns)) if warns else ''}")
            if not ok:
                fails += 1
        except Exception as e:
            fails += 1
            print(f"{board:12s} {fam:10s} FAIL {e}")
print("failures:", fails)
