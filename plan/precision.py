#!/usr/bin/env python3
"""
PRECISION BATCH - individual POCKET holders for board A (imperial), face-out,
two-part (spine with studs + holder, Ø3.5 × 15 csk drywall screws), no text,
upright on the H2S bed in ABS-GF, no supports.

    python3 plan/precision.py   -> plan/precision/  (3MF / STL per design, sheet, inventory, fit table)

Measured by Dhiya 2026-11-06: digital caliper beam 4.5 × ~16, metal caliper
3.5 × ~16; micrometer Ø19 at the widest of the handle; wrenches 2-2.5 (thinnest)
to 5.6-6 (small adjustable); Wera ratchet neck 10.5-11; Stanley ratchet and
extension 12.5-13.
"""
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bosch12v as B
import build_prints as BP

OUT = os.path.join(HERE, "precision")
A = "imperial_19"


def P(id_, item, n, W, D, H, cuts, twin=0, **kw):
    # every holder: standard columns of three studs (22 × 61.8 spine), 2 screws on the upper two stud
    # axes per column; twin = the two bars' spacing in pitches (0 = one column under the block)
    assert H <= 24.0, "block over 24 tall would push the middle screw off its stud"
    params = dict(family="pocket", split="two", brand_src="none", mt_margin=7.0, mt_rows=3, pk_wings=True,
                  mt_bars="twin" if twin else "plate", mt_span=twin, mt_pattern="twin" if twin else "grid", mt_cols=1, pk_w=W, pk_d=D, pk_h=H, pk_r=2.0, pk_lip_h=3.0, pk_cuts=cuts)
    params.update(kw)
    return dict(id=id_, item=item, n=n, board=A, params=params, brand="", zone=2, twin=twin)



def S(x, z, w, l, depth=0.0, funnel=0.8):
    return dict(kind="slot", x=x, z=z, w=w, l=l, depth=depth, funnel=funnel)


def O(x, z, w, keep=True):
    return dict(kind="open", x=x, z=z, w=w, keep=keep)


def Hh(x, z, d, depth=0.0, funnel=0.8):
    return dict(kind="hole", x=x, z=z, w=d, depth=depth, funnel=funnel)


def PEG(x, z, af, tall):
    return dict(kind="peg", x=x, z=z, w=af, l=tall)


# ---- calipers: beam 16 wide (17 slot, 0.5 a side), thickness + 0.6 --------------------------------
#  F = face-out (beam flat to the wall, the face and brand show; slot 17 along the wall)
#  E = edge-on  (jaws point out from the wall; slot 17 front-back; 16 behind the beam for the
#      display housing / thumb wheel; takes one hole column of width)
# wrenches: edge-on (the wrench's plane square to the wall), handle down through a slot, the head
# (wider in its own plane than the handle) rests across the slot. Slot = head-end thickness + clearance
# along the wall × handle width + clearance front-back; all centred 22 out so a 40 head clears the flange.
#   6-9      3.6 × 11   (2-3 thick, handles ≤ 9)       ×4
#   10       5.0 × 14   (4-4.5 thick, handles ≤ 12)    ×3
#   11-14    6.0 × 17   (5-5.5 thick, handles ≤ 15)    ×4
#   adjust.  6.8 × 21   (5.6-6 thick, handle ≤ 19)     ×1
WR = [(3.6, 11.0)] * 4 + [(5.0, 14.0)] * 3 + [(6.0, 17.0)] * 4 + [(6.8, 21.0)]
WR_PITCH = 11.0

DESIGNS = [
    P("CAL-DF", "Digital caliper · face-out · beam 4.5", 1, 34, 28, 24, [S(0, 9.0, 17.0, 5.1, funnel=1.2)]),
    P("CAL-MF", "Metal caliper · face-out · beam 3.5", 1, 34, 24, 24, [S(0, 8.5, 17.0, 4.1, funnel=1.2)]),
    # ---- micrometer: thimble Ø19 drops through a 20 U, the frame rests on top behind keep lips -------
    P("MIC", "Micrometer · Ø19 handle · U 20 + keep lips", 1, 50, 34, 20, [O(0, 16.0, 20.0)]),
    # ---- rules: 4 steel rules stacked face-out (blind 28 × 1.8 pockets), protractor arm through a
    #      30 × 3.6 slot at the front (head rests on top, face unobstructed), compasses / dividers /
    #      pencils in blind holes behind the protractor head
    P("RULE", "Rules ×4 · protractor · compasses · 2 bars", 1, 154, 46, 24,
      [S(-55, z, 28.0, 1.8, depth=20.0, funnel=0.6) for z in (8.0, 14.0, 20.0, 26.0)]
      + [S(15, 38.0, 30.0, 3.6, funnel=1.0)]
      + [Hh(x, 13.0, d, depth=20.0) for x, d in ((-5, 10.0), (17, 12.0), (41, 14.0), (65, 10.0))]
      + [Hh(x, 27.0, d, depth=20.0) for x, d in ((6, 8.0), (29, 12.0), (53, 12.0))], twin=5),
    # ---- wrenches: edge-on, held by the head, 12 slots 11 apart, small to large left to right --------
    P("WRENCH", "Spanners 6-14 · adjustable · edge-on · 2 bars", 1, len(WR) * WR_PITCH + 14, 38, 24,
      [S(round((i - (len(WR) - 1) / 2) * WR_PITCH, 2), 22.0, w, l, funnel=0.8) for i, (w, l) in enumerate(WR)], twin=5),
    # ---- socket drivers: ratchet necks through U slots, heads up behind keep lips; socket pegs -------
    #      Wera 8000 A neck 10.5-11 -> U 11.8 · Stanley ratchet 12.5-13 -> U 13.8 · extension -> U 13.8
    #      pegs 1/4 in (6.25 □, 10 tall) ×3 back row, 3/8 in (9.40 □, 13 tall) ×3 front row
    P("SOCKET", "Ratchets · extension · sockets · 2 bars", 1, 206, 44, 22,
      [O(-85, 17.0, 11.8), O(-39, 17.0, 13.8), O(7, 17.0, 13.8)]
      + [PEG(x, 12.0, 6.25, 10.0) for x in (50, 74, 98)] + [PEG(x, 33.0, 9.40, 13.0) for x in (50, 74, 98)], twin=7),
]

FIT = [
    ("CAL-DF", "digital caliper beam", "4.5 × 16", "slot 5.1 × 17", "+0.6 / +1.0, 24 deep, 1.2 funnel"),
    ("CAL-MF", "metal caliper beam", "3.5 × 16", "slot 4.1 × 17", "+0.6 / +1.0, 24 deep, 1.2 funnel"),
    ("MIC", "micrometer handle", "Ø19", "U 20", "+1.0, frame rests on top, 3 mm keep lips"),
    ("RULE", "steel rules", "≤ 1.2 × ≤ 26", "pocket 1.8 × 28, 20 deep", "4 stacked 6 apart"),
    ("RULE", "protractor arm", "≤ 2.5 × ≤ 28", "slot 3.6 × 30", "through, head rests on top"),
    ("RULE", "compasses / dividers / pencils", "", "Ø8 · Ø10 ×2 · Ø12 ×3 · Ø14", "20 deep, floor 4"),
    ("WRENCH", "spanners 6-9 (edge-on)", "2-3 thick", "slot 3.6 × 11 ×4", "head rests across the slot"),
    ("WRENCH", "spanners 10", "4-4.5 thick", "slot 5.0 × 14 ×3", "head rests across the slot"),
    ("WRENCH", "spanners 11-14", "5-5.5 thick", "slot 6.0 × 17 ×4", "head rests across the slot"),
    ("WRENCH", "small adjustable", "5.6-6 thick", "slot 6.8 × 21", "head rests across the slot"),
    ("SOCKET", "Wera 8000 A neck", "Ø10.5-11", "U 11.8", "+0.8, keep lips"),
    ("SOCKET", "Stanley ratchet neck / extension", "Ø12.5-13", "U 13.8", "+0.8, keep lips"),
    ("SOCKET", "1/4 in sockets", "6.35 □", "peg 6.25 □ × 10", "-0.10, chamfered"),
    ("SOCKET", "3/8 in sockets", "9.53 □", "peg 9.40 □ × 13", "-0.13, chamfered"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    BP.OUT = OUT
    B.OUT = OUT
    rows = []
    for hd in DESIGNS:
        r = BP.build_one(hd)
        r = dict(id=hd["id"], item=hd["item"], n=hd["n"], family="pocket", **r)
        rows.append(r)
        print(f"{r['status']:5s} {r['id']:7s} ×{r['n']} {r['item']:52s} {r.get('holder_g', 0):6.1f} + {r.get('spine_g', 0):5.1f} g  "
              f"unsupported {r.get('unsupported')}  bed {r.get('holder_bed')}  {r.get('screws')}", flush=True)
    keys = ["id", "item", "n", "status", "holder_g", "spine_g", "holder_bed", "spine_bed", "screws", "unsupported",
            "valid", "open_edges", "interference"]
    with open(os.path.join(OUT, "inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT, "fit_table.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["holder", "tool", "measured", "cut", "note"])
        w.writerows(FIT)
    B.contact_sheet(rows, [], os.path.join(OUT, "precision_sheet.pdf"),
                    title="PRECISION BATCH · calipers · micrometer · rules · wrenches · sockets · board A",
                    sub="two-part: pocket holder on a 22 wide flange (prints upright, block on the bed; wings bear on the board) + spine 22 × 61.8 with 3 studs (face down) · Ø3.5 × 15 csk drywall "
                        "screws into the studs · all cut-outs vertical · ABS-GF, 0.4 TC nozzle, no supports, no text")
    ok = [r for r in rows if r["status"] == "ok"]
    printed = [r for r in ok if r["n"] > 0]
    g = sum((float(r["holder_g"]) + float(r["spine_g"])) * r["n"] for r in printed)
    screws = sum(int(str(r["screws"]).split(" ×")[0]) * r["n"] for r in printed)
    L = [f"PRECISION BATCH · imperial board A · {time.strftime('%Y-%m-%d %H:%M')}",
         f"designs {len(rows)} · ok {len(ok)} · {sum(r['n'] for r in printed)} holders + {sum(r['n'] * (2 if d.get('twin') else 1) for r, d in zip(rows, DESIGNS) if r['status'] == 'ok')} spines (all the same part: 22 × 61.8, 3 studs)",
         f"ABS-GF ≈ {g:.0f} g (+12 % → {1.12 * g:.0f} g) · Ø3.5 × 15 csk drywall screws: {screws}",
         "screws: 2 per bar, on the upper two stud axes, 6.5 mm on into the Ø7.8 studs",
         "RULE / WRENCH / SOCKET: two bars (one each side, 5 / 5 / 7 pitches apart), one standard spine behind each", "",
         "fit (measured → cut):"] + [f"  {a:7s} {b:32s} {c:14s} {d:28s} {e}" for a, b, c, d, e in FIT]
    L += ["", "not ok:"] + [f"  {r['id']} {r.get('reason', '')}" for r in rows if r["status"] != "ok"]
    with open(os.path.join(OUT, "summary.txt"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
