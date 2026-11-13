# PEGBOARDLAB research notes — 2026-10-27

Reference data behind the presets, clearances and the Gridfinity /
magnet / thread families. **[P]** primary (manufacturer page, standard,
source constants read directly) · **[S]** secondary (community-measured,
retailer, blog) · **[U]** unverified — measure before hard-coding.

## 1 Imperial pegboard (1 in pitch)

| Board | Thickness (ANSI A135.4) | Hole | mm | Source |
|---|---|---|---|---|
| 1/8 in | 2.92–3.94 | 3/16 in | 4.76 | [P] Panel Processing https://www.panel.com/products/pegboard/ ; ANSI/CPA A135.4-2012 https://law.resource.org/pub/us/cfr/ibr/inc/ansi/ansi.cpa.a135.4.2012.pdf |
| 3/16 in (sold as 0.155 actual) | 3.94 | 1/4 in | 6.35 | [S] Home Depot 202189722 |
| 1/4 in (5.5 mm stock) | 5.33–6.73 | 9/32 in | 7.14 | [P] Panel Processing |
| Steel (Wall Control, 20 ga) | 0.9 | 1/4 in + slots | 6.35 | [P] https://wallcontrol.com/pages/pegboard-how-to |
| McMaster range | 0.03–1/4 in | 1/8–9/32 in | 3.18–7.14 | [P] https://www.mcmaster.com/workbench-pegboards |

Standoff: ≥ 1/2 in (furring strips) [S] Wayfair guide; Wall Control
3/4 in flange [P]. Design rear projection ≤ 12 mm for unknown boards.

Steel hooks: "1/8 in" hooks 0.148 in (3.76) wire [S] Azar; "1/4 in"
hooks 0.186 in (4.72) wire [P] Kinter https://products.kinter.com/item/metal-display-hooks/single-prong-all-wire-pegboard-hook/160570 .
Lock principle (US10827853 [P] https://patents.google.com/patent/US10827853 ):
hook tilted so the bent ends pass through, levelled; the front bend bears
on the face, the bent ends behind block withdrawal unless re-tilted.
Peg locks: flanged plastic caps into the adjacent holes [S] kk.org/cooltools ;
Triton DuraHook rear tab + front screw [S] toolguyd ; Wall Control slotted
hooks "up-down-up-down" tang [P] https://www.wallcontrol.com/content/PegboardHookEngagement.PDF .
Wall Control slot size **[U]**.

## 2 Metric boards

IKEA SKÅDIS [S, consistent across ≥5 sources]: slot 5 × 15 (R2.5), 40 mm
in-row, rows 20 mm with 20 mm stagger, panel ≈ 5 mm.
https://pegboardly.com/skadis/skadis-sizes-and-dimensions ·
https://github.com/soloh4cker/skadis_pegboard_studio ·
https://www.printables.com/model/667614 . IKEA publishes no drawing.

Europe retail steel: Ø4.5 / 30 mm / 1 mm (Hornbach 3401205) [S]; 10×10 sq /
38 mm (Element System, Kappes RasterPlan) [S]; Bauhaus HDF Ø5 / 15 mm / 3 mm [S].
Japan 有孔ボード: 25 mm pitch Ø5 (also 6, 8), 4–5.5 mm, 5.5 most common
[P] Kato Hide https://pr.www.ipros.com/en/katohide/product/detail/2000293199 ;
[S] Wakai https://store.wakaisangyo.co.jp/en/blogs/diyhajimemashita/240509 ;
30 mm / Ø6 variant. China: Ø5/8/12, 25/30/75 pitch, Ø5 × 25 most common
[S] https://post.smzdm.com/p/a34vx987/ .
Printed ecosystems: Multiboard 25 mm MU, 0.25 design tolerance [P]
https://docs.multibuild.io/beginner-section/printing-guidelines ; openGrid 28 mm,
6.8 / 3.4 thick [S]; Honeycomb Storage Wall hex **[U]**.

## 3 Printed hook / peg practice

- Hole-to-peg: 0.42 clearance + 0.1 anti-play (Printables 168516) [S];
  +0.2 on printed-board holes (MakerWorld 651869) [S]; advertised 5 mm
  holes measured 4.4 (Printables 282565) — always enter the measured Ø.
- Two-point lock: upper peg + lower snap clip (EZPZ hook, Make Anything) [S];
  lever lock compressing the mount (SYS PegLock, Printables 249871) [S];
  flared snap peg (Snapmaker blog) [S].
- Orientation: hooks flat on their side, 5–8 walls, 0 % infill
  (Printables 672229, 309753, 360037) [S].
- Fit bands on Bambu (UAL CCI wiki, per side): press 0–0.05, snug 0.1–0.15,
  sliding 0.15–0.2, loose ≥ 0.2 [S]
  https://wiki.cci.arts.ac.uk/books/digital-fabrication-lab/page/design-the-clearance-and-tolerance
- Bambu X-Y hole compensation starting points: PLA 0.05, ABS/PETG 0.10,
  nylon 0.15 [P] https://wiki.bambulab.com/en/knowledge-sharing/3d-prints-shrinkage
- Bambu ABS-GF TDS [P]: tensile 36 XY / 29 Z MPa, bending 68 / 46, HDT 88 °C,
  nozzle 240–280, bed 80–100, hardened 0.6 recommended
  https://www.lesimprimantes3d.fr/dl/Bambu_ABS-GF_Technical_Data_Sheet.pdf
- Peg in a real hardboard hole, GF filament: hole − 0.3…0.5 **[derived]**;
  the coupons measure it.

## 4 Gridfinity (de-facto constants, kennetek/gridfinity-rebuilt-openscad standard.scad [P])

    grid 42 · bin footprint 41.5 (0.25 gap/side) · unit height 7
    bin base profile 0.8 ch + 1.8 vert + 2.15 ch = 4.75; bridge 2.25
    baseplate socket 0.7 + 1.8 + 2.15 = 4.65 (plate thickness is a choice; 5 common)
    radii: bin top R3.75, base bottom R0.8, baseplate R4.0
    stacking lip 0.7 / 1.8 / 1.9 = 4.4, 2.6 deep, tip fillet 0.6
    magnet pocket Ø6.5 × 2.4 for 6×2; refined press-fit Ø5.86 × 1.9
    magnet / screw centres 8 from each side (26 c-c), 4.8 from the bottom edge
    screw Ø3 (M3), min wall 0.95, divider 1.2
    https://raw.githubusercontent.com/kennetek/gridfinity-rebuilt-openscad/main/src/core/standard.scad
    https://github.com/gridfinity-unofficial/specification · https://gridfinity.xyz/specification/

## 5 Magnets

supermagnete, on 20 mm steel, zero gap [P] (0.5 mm gap ≈ −50 %):
6×2 N45 0.74 kg · 8×2 ~1.1 · 8×3 N45 1.5 · 10×2 N42 1.3 · 10×3 N42 1.8 ·
12×3 N45 2.4 · 15×3 N45 3.2 · 20×2 ~2.9 · 20×3 N45 4.3 kg; ±0.1 mm, 80 °C.
https://www.supermagnete.de/eng/disc-magnets-neodymium/
K&J, Case 1 [P]: D41 1/4×1/16 0.54 kg · D42 1/4×1/8 1.04 · D62 3/8×1/8 2.0 ·
D63 3/8×3/16 2.64 · D82 1/2×1/8 2.92 kg. https://www.kjmagnetics.com/
N52 vs N42 ≈ +25 % (Br², derived).
Pockets: Gridfinity +0.5 Ø / +0.4 depth, open [P]; Pantheon +0.25, ≥0.5 mm
retaining nubs, magnet ≥5 mm above the bed [S]; Bambu forum glue-in +0.3 /
+0.4, 0.4 seal; flush press +0.2 [S] https://forum.bambulab.com/t/perfect-flush-magnet-fit/205491 .
Tool defaults: Ø +0.3 press / +0.5 drop-in; depth = t + 0.2…0.4 rounded to
the layer; cover 0.4–0.6 when enclosed; report pull ≈ rated × 0.5 for a
0.4 mm cover (estimate). Prefer exposed / 0.2 bridge when the magnet is
the retainer.

## 6 Printed threads and nuts

Printed thread floor M6 (JLC3DP, Sovol) [S]; M5 only on tuned machines;
radial clearance 0.10–0.20, fibre filaments at the low end (Bambu forum
145508) [S]; trapezoid / rounded roots, 45° lead chamfer, engagement
2–2.5 × Ø [S]; Multiboard bolts 0.125 clearance [S]. ABS-GF studs lose
~20 % in Z tension: print studs lying down.
ISO 4032 (AF / m / pitch) [P] wermac.org: M3 5.5/2.4/0.5 · M4 7/3.2/0.7 ·
M5 8/4.7/0.8 · M6 10/5.2/1.0 · M8 13/6.8/1.25 · M10 16/8.4/1.5 (DIN 934 M10 = 17).

## Flagged
Wall Control slot geometry · SKÅDIS thickness (community only) · "Ø5/25 EU
HDF" as a standard · Multiboard hole Ø / HSW hex / openGrid opening ·
Taobao 4 mm ABS tiles · Gridfinity "5 mm plate" (socket is 4.65) ·
ABS-GF peg clearance (derived) · N52 +25 % (derived) · Packout plates.
