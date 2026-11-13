# PEGBOARDLAB

Parametric, 3D-printable pegboard accessories for Dhiya's boards
(imperial 19 mm chipboard, metric 4 mm hardboard) and any other board
you can measure. Sliders in the browser, CadQuery on the server,
exports STEP + STL + 3MF (laid on the bed, one object per print) +
parameters + a standalone script. Sister of SLOTLAB / KNOBLAB / BOXLAB.

    cd ~/cad/pegboardlab
    python3 app.py            # http://localhost:8768   (--port 8769 if busy)

Dependencies: `pip install cadquery` (Python 3.10–3.13). Nothing else;
three.js is vendored, the UI works offline.

House rules (2026-11): no text on prints; every holder is TWO-PART
(spine with the studs + holder, Ø3.5 × 15 countersunk drywall screws);
the backing is the standard column of three studs (22 × 61.8 on the
imperial board) - one column under a narrow holder, one at each side of
a wide one (twin bars); printed on the H2S in ABS-GF with no supports.

## Files

    boards.py        board presets + lattice maths (hole_xy, stud_d)
    fasteners.py     ISO holes / nuts / inserts, magnets, Gridfinity constants
    geometry.py      primitives, teardrop studs, printed threads, STL/3MF,
                     print orientations, the overhang audit
    mounts.py        the mount layer: backing (plate / twin bars), hole
                     patterns, fixings, ears
    model.py         parameters, family registry, build pipeline, two-part split
    branding.py      text / SVG artwork (kept for other boards; off by default)
    families/        one module per family - add a file, get a tab
      _kit.py        the brand-kit mechanism (tool tables -> arm / shelf / pocket)
    app.py           local server, stdlib only      index.html   UI + three.js
    tests/           kits.py (every kit tool + twin bars, both boards),
                     batch.py (every family × board × fixing × pattern),
                     smoke.py, samples.py, coupons.py, render.py
    plan/            the studio builds: bosch12v.py, handtools.py, precision.py,
                     boardA.py (board A map), build_prints.py (3MF + checks)
    research.md      reference data + bibliography

## Boards

Every number is a slider; the preset is a starting point. The stud the
tool cuts is `hole − clearance + shrink`, where shrink is the diametral
loss measured on that board's coupon (ABS-GF on the H2S).

    imperial_19   Ø7.6 · 19 thick · 23.876 square · shrink 0.2 · clear 0.0
                  -> studs Ø7.8 × 18 · 31 columns × 50 rows (740 × 1194)
    metric_4      Ø4.9 · 4 thick · 45° lattice: 27.44 along a row, rows 13.72,
                  stagger 13.72 · shrink 0.1 · clear 0.2 -> studs Ø4.8 × 6.5
    + US 1 in (1/4 and 1/8), JP/CN 25 mm, SKÅDIS - reference values, unmeasured

Lattice: hole (ix, iy) at x = ix·pitch_x + (iy mod 2)·stagger, y = iy·pitch_y.

## Mount layer (every family)

Backing (`Mount · Backing`):

    Auto       the family's suggestion: the standard column (pattern Grid
               1 × 3) under arms and narrow pockets; twin bars under a wide
               pocket (≥ 90); the auto hole fill for the older families
    Plate      one plate the size of the feature, studs in the Pattern
    Twin bars  two vertical bars, one each side, `Bars apart` hole pitches
               apart (0 = as far apart as the feature allows), `Rows` studs
               each. `Between the bars`: a low STRIP joins them behind the
               feature, or a FILLED PLATE closes the gap to the bars' full
               height. `Fill corner radius` (0 = the plate corner radius; the
               bars' corners follow it) and `Fill thickness` (0 = the flange)
               shape the strip / fill. Two-part: ONE single-column spine behind each bar - the
               same part printed twice - and the strip / fill reaches back to
               0.3 off the board between the spines, so the holder bears on the
               board and cannot rock. The backing is always as wide as the
               bars' outer edges, so shelves and webs run flush with the ends.

Pattern: `Auto` fills every hole under the plate, `Row` / `Col` /
`Corners` thin that out, `1 2V 2H 4 ◇ Grid` are explicit and grow the
plate to fit, `None` for ears or bolts only.

Fixing:

    Stud      the printed peg (teardrop section when the print lays it horizontal)
    Thread    printed external thread + the NUT family
    Tube      printed internal thread, bolt from the back
    Insert    heat-set insert in the stud
    Bolt      a through bolt. `Bolt from` BACK: head behind the board, nut on
              the front - `Nut` CAPTIVE (hex pocket in the face, the plate is
              thickened to hold it) or LOOSE (plain hole, the nut sits on the
              face). FRONT: head on the face - `Head seat` CSK (cone, ISO
              head Ø), PAN (counterbore) or NONE (head on the face) - nut
              behind the board.
    Screw     drywall screws straight into the board (`Screw Ø`, `Screw
              length`; readout: engagement in the board). The plate sits half
              a pitch over so the screws land BETWEEN the holes; `Head seat`
              CSK / PAN / NONE as above. One-piece only (there are no studs
              for a spine) - holes behind the feature are skipped.
    J-hook    thin boards

Ears: D-tabs on any edge.

## Two-part construction (default)

The SPINE is a plate (or bar) with the studs; it prints face down. The
HOLDER is the family body on a flange of the same footprint; it prints
in the family's orientation. Drywall screws (Ø3.5 × 15, head Ø8, pilot
Ø2.8) run through the flange into the spine; `Head seat` CSK (cone) or
PAN (counterbore `Head height` deep, for pan / wafer heads):

    thick board (A)   the screws sit on the stud axes - the upper two studs
                      of each column - and run 6.5 mm on into the Ø7.8 studs,
                      expanding them in the Ø7.6 holes
    thin board (B, C) the screws sit between the holes along the bar and bite
                      the panel itself (tip ~2 mm proud behind)

Export gives one 3MF with the holder upright and the spine(s) face down
beside it, an STL per part, and the STEP assembly in place.

## Families

Brand kits - the controls are the tool's measurements, the geometry is an
ARM, SHELF or POCKET underneath (all of whose controls still apply):

    bosch 12V   GSR 120-LI, GWS 12V-76 (lip-arm pairs: housing depth, grip
                width -> reach, arms apart), GKS 12V-26 saw shelf + flat arm
                (base, reach, blade-guard notch), blue case, GRO 12V-35 and
                GluePen (cradle pairs: Ø, body length), bit boxes, soft bag
    wera        Tool-Check PLUS (arm pair), Hex-Plus 950/9 L-keys, Kraftform
                screwdrivers, Zyklop 8000 A ratchet, loose sockets (pegs)
    irwin       screwdrivers + chisel / awl / knife, pliers and cutters
                straddling fingers, Quick-Grip clamp rail + its lip arm,
                combination square
    measure     calipers face-out (beam thickness / width), micrometer,
                steel rules + protractor + compasses, spanners edge-on by size

Every pair tool reports `pair: 2 arms N pitches apart` in the readout
(auto from the grip width or the tool length; `Arms apart` overrides) and
warns when the tool would not pass or the arms would stick out. Print 2.

Modular parts:

    arm         the cantilever: standard column flange, arm 20 -> 12 tall,
                reach 25-200; tip lip / flat / cradle (Ø); shelf pilots Ø2.8
                at 14 + 30k mm; `Arm width` < flange = narrow hook (N30)
    shelf       plate on 2-6 arms n pitches apart (pilots match), side /
                front / back lips, front-open notch, rack cut-outs
                (open / slot / hole)
    pocket      individual face-out holder: block on the flange bottom with
                vertical slots / holes / blind pockets / front U's (+ keep
                lips) / square socket pegs; one column with wings, or twin bars

    rack        shelf with holes / slots / pockets: `Sizes` lists a width or Ø
                per feature ("4.5, 4.5, 6, 8, 10") and overrides the single
                slider; auto pitch packs mixed sizes with the margin between
                them. The shelf spans the whole backing; the END BRACES sit
                flush with the ends: `Brace shape` TRIANGLE (gusset) or WALL
                (full-height side), `Brace thickness`, `Brace height` (0 =
                auto: as tall as fits under the lowest screw head; a hand
                value that covers a screw is warned) and `Brace run` out from
                the plate (0 = the shelf depth).

    stand       quick-draw comb for flat tools standing edge-on (spanners,
                files): a tray on the plate's bottom edge, one channel per
                tool between a pair of fins, a low front lip. The tool stands
                on its open end against the lip and leans back on the board;
                it lifts straight out forward. `Channels` = width, or width ×
                foot length per tool; the front edge follows the foot lengths.
                Default list: Wera Bicycle Set 12 (plan/wera_bike12.py).

Typed cut-outs (POCKET · `Cut-outs`, one token per feature, comma-separated,
packed left to right with `Wall between` them):

    slot 4.5x17 @9     slot 4.5 along the wall × 17 front-back, centred 9 from the flange
    hole 12 d20        Ø12, blind 20 deep           open 11.8 keep   front U + keep lips
    peg 6.25 h10       square socket peg 10 tall    20x3             a slot (kind optional)

The Irwin drivers, Wera Kraftform, Measure spanners and rules tools take
the same per-item lists (shaft Ø per tool, blade Ø per driver, slot w × l
per spanner, hole Ø per compass).

Older families: hook, tray, holster, clip, plate, magstrip, gridfinity,
nut (see their module docstrings). Gridfinity's end braces take the same
controls as the rack's.

## Printing without supports

`Design for no supports` picks the orientation and the geometry:

    arm              on its side: the profile on the bed, layers along the arm
    pocket           upright: block and flange bottom on the bed, every cut-out
                     a vertical wall, entries funnelled
    shelf / spine    flat / face down
    hook rack tray holster gridfinity   upright; clip on its side; plate,
                     magstrip face down; nut flat

The readout's `unsupported` figure is the area of faces steeper than
45° above the first layer (stud flats and small bridges are normal).
Parts longer than 320 are laid on the bed diagonal by plan/build_prints.

## Dimensions in the viewer

Every build returns its dimension lines and the viewer draws them
(black lines, 45° ticks, white labels; `Dimensions` button to hide):
overall width / height / depth, spine and flange thickness, stud Ø,
length and pitch, bar width, bar spacing and strip height for twin bars,
then the family's own - reach, root and tip heights, lip, cradle Ø and
pilot positions on an arm; block depth and height, every distinct
cut-out (slot w × l, hole Ø, U width and depth, keep lip, peg □ and
height) and the pitch of repeated ones on a pocket; plate, arm spacing,
lips, notch, pilots and cut-outs on a shelf; shelf depth and thickness, web height,
every distinct hole Ø / slot width and length / hex pocket and the pitch, brace height, run and
thickness on a rack; bolt hole, nut pocket AF or head Ø, screw hole and head
Ø for the fixing; reach, arm, tip, gap and prong on a hook; depth, wall, floor,
front, dividers and magnets on a tray; opening or ring on a holster;
unit, pitch, socket depth on a Gridfinity shelf; wire, pitch and snap on a
clip; holes, lip, magnet pockets, nut AF / bore / wing on the rest. The
print view shows each part's bed footprint instead.

Controls that are counts or ratios carry their millimetre result under
the slider (blue): bars apart → centres and the gap between the bars,
rows → bar height, hole Ø / shrink / clearance → the stud Ø, arms apart
→ centres and the gap, a tool's measurement → the reach, cradle Ø, slot
or block it produces, fill radius / thickness → the value they inherit,
screw length → engagement in the board, bolt → nut AF or head Ø.

## Verification

`tests/kits.py` builds every tool of every kit on both boards, twin bars
on every plate family, the per-item size lists / typed cut-outs /
filled twin bars, and the fill, brace, bolt and screw options (114 cases: valid solid, watertight mesh, no
interference with the board at the printed stud size, screws per bar) ->
samples/kits_report.txt. `tests/batch.py` is the full family × board ×
fixing × pattern sweep; `tests/smoke.py` the quick one.

## Print settings (H2S, ABS-GF, 0.4 TC nozzle)

4+ walls, 0.2 layers (0.12 for printed threads), X-Y hole compensation
0.10, elephant-foot 0.15. Studs are sized to the hole: dry-fit one spine
before printing a batch.
