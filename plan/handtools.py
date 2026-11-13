#!/usr/bin/env python3
"""
HAND TOOLS + WERA KIT - imperial board A. Same system as the Bosch 12V kit:
ARMs on a two-part spine (2 × Ø3.5 × 15 csk drywall screws into the studs)
and SHELF plates screwed onto pairs of arms. Hand tools hang from RACK
plates (shelf plates with cut-outs) on pairs of flat 60 arms, or from
narrow N hooks. No text on any print. ABS-GF on the H2S, no supports.

    python3 plan/handtools.py   -> plan/handtools/  (3MF / STL per design, sheet, inventory)
    python3 plan/boardA.py      -> plan/boardA/     (the whole board: Bosch + hand tools + Wera)

Rack cut-outs (x along the wall from the plate centre, w along the wall, l front-back):
    open   from the front edge: quick-draw, lift up and out
    slot   closed stadium (the tool hangs by a shoulder)
    hole   round
Pliers / cutters straddle 10 mm fingers between 26 mm open gaps; drivers and
chisels drop into 9.5-10 mm open slots; L-keys into slots sized to their hex
across the corners (+0.6); the caliper beam into a closed slot.
"""
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bosch12v as B          # shares ARM / SHELF defaults, the contact sheet and the shelf assembly drawing
import build_prints as BP

OUT = os.path.join(HERE, "handtools")
PITCH = B.PITCH
RACK = dict(sh_tip="flat", sh_reach=60, sh_t=6.0, sh_gap=4.0, sh_over=8.0, sh_side_lip=0.0, sh_back_lip=12.0, sh_r=3.0)
D60 = 60 - 4                  # rack plate depth on F60 arms
NARROW = dict(ar_aw=9.0, ar_root=11.0, ar_tip_h=8.0, ar_lip_t=5.0, ar_cove=1.5, ar_pilots=False)


def row(kind, n, pitch, w, l=0.0, y=0.0, x0=0.0):
    return [dict(kind=kind, x=round(x0 + (i - (n - 1) / 2) * pitch, 3), w=w, l=l, y=y) for i in range(n)]


# Wera 950/9 Hex-Plus Multicolour: 1.5 2 2.5 3 4 5 6 8 10 (long legs 90 ... ~224)
HEX_AF = [1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
hex_cuts = [dict(kind="open", x=round((i - 4) * 16.0, 3), w=round(max(2.6, 1.155 * af + 0.6), 2), l=14) for i, af in enumerate(HEX_AF)]

# measuring rack (10 pitches, arms at ±119.4, inner edges ±108.4):
#   x -104 ... -40  front edge left clear: the tape's belt clip hooks over it (plate 6 thick)
#   caliper beam slot 20 × 6 (closed) · 4 marker holes Ø13 · scriber / awl hole Ø10
meas_cuts = ([dict(kind="slot", x=-14.0, w=20.0, l=6.0, y=28.0)]
             + row("hole", 4, 19.0, 13.0, y=28.0, x0=37.5)
             + [dict(kind="hole", x=92.0, w=10.0, y=28.0)])

# drivers: front row 7 open slots (Irwin, chisel, awl, knife - quick-draw), back row 6 closed slots
# half a pitch over (Wera Kraftform); shaft centres 33 apart front-back, 21 along the wall -> 39 between
# shafts, so Ø36 handles clear each other
drv_cuts = row("open", 7, 42.0, 10.0, l=18) + row("slot", 6, 42.0, 10.0, l=12, y=10.0)

DESIGNS = [
    # arms (the Bosch kit's standard set plus the two new ones)
    B.D("F60", "Arm · flat · reach 60 (rack bearer)", 10, ar_tip="flat", ar_reach=60),
    B.D("A60", "Arm · lip · reach 60", 2, ar_tip="lip", ar_reach=60),
    B.D("N30", "Hook · narrow · reach 30", 5, ar_tip="lip", ar_reach=30, ar_lip=8, **NARROW),
    # racks: shelf plates with cut-outs on pairs of F60
    B.D("R-PLI", "Rack · pliers + cutters ×6 · 12 pitches", 2, family="shelf", sh_arms=2, sh_span=12,
        sh_cuts=row("open", 7, 36.0, 26.0, l=D60 - 18), **RACK),
    B.D("R-DRV", "Rack · drivers ×13, two staggered rows · 14 pitches", 1, family="shelf", sh_arms=2, sh_span=14,
        sh_cuts=drv_cuts, **RACK),
    B.D("R-HEX", "Rack · Wera Hex-Plus L-keys ×9 · 8 pitches", 1, family="shelf", sh_arms=2, sh_span=8,
        sh_cuts=hex_cuts, **RACK),
    B.D("R-MEAS", "Rack · caliper · markers · scriber · tape · 10 pitches", 1, family="shelf", sh_arms=2, sh_span=10,
        sh_cuts=meas_cuts, **RACK),
]

TOOLS = {
    "R-PLI": "pliers ×4 (red/black), cutters / crimpers ×5, aviation snips, end nipper, 1 spare (two racks)",
    "R-DRV": "front: Irwin long ×2 + stubby ×2, chisel, awl, marking knife · back: Wera Kraftform ×6 (one now, room for five more)",
    "R-HEX": "Wera 950/9 Hex-Plus Multicolour 1.5-10, long legs down, short legs resting on the plate",
    "R-MEAS": "digital caliper (beam down, jaws up), Stanley 8 m tape (clip over the left front edge), markers ×4, scriber",
    "A60": "Wera Tool-Check PLUS (190 × 100 × 35) standing on its long edge on a pair",
    "N30": "scissors, adjustable wrench, spanner, micrometer 0-25, protractor - one each",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    BP.OUT = OUT
    B.OUT = OUT
    rows = []
    for hd in DESIGNS:
        r = BP.build_one(hd)
        r = dict(id=hd["id"], item=hd["item"], n=hd["n"], family=hd["params"]["family"], **r)
        rows.append(r)
        print(f"{r['status']:5s} {r['id']:7s} ×{r['n']} {r['item']:55s} {r.get('holder_g', 0):6.1f} + {r.get('spine_g', 0):5.1f} g  "
              f"unsupported {r.get('unsupported')}  {r.get('warnings', '')}", flush=True)
    keys = ["id", "item", "n", "family", "status", "holder_g", "spine_g", "holder_bed", "spine_bed", "screws", "unsupported",
            "valid", "open_edges", "interference", "warnings"]
    with open(os.path.join(OUT, "inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    B.DESIGNS[:] = B.DESIGNS + [d for d in DESIGNS if d["id"] not in {x["id"] for x in B.DESIGNS}]
    extra = [(B.assembly_shelf("R-PLI", "F60", 12, os.path.join(OUT, "R-PLI_assembly.svg")), "R-PLI on 2 × F60 · 12 pitches · pliers straddle the fingers"),
             (B.assembly_shelf("R-DRV", "F60", 14, os.path.join(OUT, "R-DRV_assembly.svg")), "R-DRV on 2 × F60 · 14 pitches · two staggered rows")]
    B.contact_sheet(rows, extra, os.path.join(OUT, "handtools_sheet.pdf"),
                    title="HAND TOOLS + WERA · ARMS + RACKS · imperial board A")
    ok = [r for r in rows if r["status"] == "ok"]
    arms = sum(r["n"] for r in ok if r["family"] == "arm")
    g = sum((r["holder_g"] + r.get("spine_g", 0)) * r["n"] for r in ok)
    screws = 2 * arms + sum(int(str(r["screws"]).split(" ×")[0]) * r["n"] for r in ok if r["family"] == "shelf")
    L = [f"HAND TOOLS + WERA · imperial board A · {time.strftime('%Y-%m-%d %H:%M')}",
         f"designs {len(rows)} · ok {len(ok)}",
         f"prints: {arms} arms + {arms} spines + {sum(r['n'] for r in ok if r['family'] == 'shelf')} rack plates",
         f"ABS-GF ≈ {g:.0f} g (+12 % → {1.12 * g:.0f} g)", f"Ø3.5 × 15 csk drywall screws: {screws}", ""]
    L += [f"  {k:7s} {v}" for k, v in TOOLS.items()]
    L += ["", "not ok:"] + [f"  {r['id']} {r.get('reason', '')}" for r in rows if r["status"] != "ok"]
    with open(os.path.join(OUT, "summary.txt"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
