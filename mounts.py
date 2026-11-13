"""
Mount layer for PEGBOARDLAB: how a plate meets the board.

    plan(p, b, want)      -> which holes the plate uses, final plate size
    apply(body, mp, p, ctx) -> studs, bores, nut pockets, J-hooks, ears cut
                              into / added onto the family's body

Every family builds on a plate centred on the origin (x in ±w/2, y in
±h/2, z in [0, t]); the mount layer never cares what is in front of it.

Patterns (mt_pattern):
    auto      every hole under the plate (inset by the margin)
    row       the top row of those             col   the centre column
    corners   the four extreme holes
    1 2V 2H 4 one hole, two in a column, two in a row, a 2 × 2
    diamond   lattice boards: a hole, its two diagonal neighbours above, and
              the hole above those (a 45° square)
    grid      mt_cols × mt_rows consecutive holes
    none      no studs (ears or bolts only)

Bars (mt_bars): what the backing is.
    plate     one plate the size of the family's feature, studs in the pattern
    twin      two vertical BARS, one each side of a wide holder, mt_span hole
              pitches apart; each bar is one column of mt_rows studs (the
              standard 22 × 61.8 bar on the imperial board) and a low back
              STRIP joins them behind the feature - or, mt_fill = plate, the
              space between the bars is filled to their full height. Two-part: one standard
              single-column spine behind each bar - the same part twice - and
              the strip reaches back to 0.3 off the board between the spines
              (wings), so the holder bears on the board and cannot rock.
    auto      the family's suggestion (twin for wide pockets, plate otherwise)

Fixings (mt_fix): what each stud is.
    plain     stud; teardrop section when the print needs it
    thread    printed external thread on the stud (NUT family makes the nut)
    tube      hollow stud with a printed internal thread for a bolt from the back
    insert    heat-set insert in the stud tip, bolt from the back
    bore      no stud (or a short locator): through hole + captive hex nut
              on the front, bolt from the back - the strong option for thin boards
    jhook     rolled J on the top row (thin boards), straight stops below
"""

import math

import cadquery as cq

import boards as BD
import fasteners as F
import geometry as G
import dims as DM

PARAMS = {
    "mt_bars": "auto",      # auto | plate | twin
    "mt_span": 0,           # twin: hole pitches between the bars, 0 = auto from the feature width
    "mt_rows": 3,           # twin: studs per bar · grid: rows
    "mt_fill": "strip",     # twin: strip (a low strip joins the bars) | plate (filled to the bars' full height)
    "mt_fill_r": 0.0,       # twin: corner radius of the strip / filled plate, 0 = the plate corner radius
    "mt_fill_t": 0.0,       # twin: thickness of the fill, 0 = the flange thickness
    "mt_strip": 0.0,        # twin: back strip height, 0 = auto (feature band + 6)
    "mt_wings": True,       # twin, two-part: strip reaches back to the board between the spines
    "mt_pattern": "auto",   # auto | row | col | corners | 1 | 2V | 2H | 4 | diamond | grid | none
    "mt_cols": 2,
    "mt_margin": 7.0,       # plate beyond the outer studs, per side
    "mt_fix": "plain",      # plain | thread | tube | insert | bore (bolt) | screw | jhook
    "mt_bolt": 5,           # M size for tube / insert / bore
    "mt_bolt_from": "back", # bore: back (head behind the board, nut on the front) | front (head on the front, nut behind)
    "mt_nut": "captive",    # bore from the back: captive (hex pocket in the front) | loose (nut sits on the face)
    "mt_head": "csk",       # bore from the front · screw: csk | pan (counterbore) | none (head on the face)
    "mt_screw_d": 3.5,      # screw: drywall / wood screw Ø, straight into the board between its holes
    "mt_screw_len": 32.0,   # screw: length (for the readout: engagement in the board)
    "mt_len": 0.0,          # stud length, 0 = board preset
    "mt_tip": 1.0,          # tip chamfer
    "mt_thread_pitch": 0.0, # external thread pitch, 0 = auto from the stud Ø
    "mt_j_bend": 5.0,       # jhook bend radius
    "mt_j_shaft": 0.0,      # jhook shaft Ø, 0 = stud - 0.5
    "mt_ears": "none",      # none | sides | top | bottom | topbottom | all
    "mt_ear_screw": 4.0,    # screw Ø
    "mt_ear_csk": True,
    "mt_ear_n": 1,          # ears per edge
    "mt_ear_wall": 3.0,
}

SCHEMA = [
    {"key": "mt_bars", "label": "Backing", "type": "seg", "group": "Mount",
     "options": [("auto", "Auto"), ("plate", "Plate"), ("twin", "Twin bars")]},
    {"key": "mt_span", "label": "Bars apart · pitches (0 = auto)", "type": "slider", "min": 0, "max": 14, "step": 1, "group": "Mount",
     "show": {"key": "mt_bars", "not": ["plate"]}},
    {"key": "mt_fill", "label": "Between the bars", "type": "seg", "group": "Mount",
     "options": [("strip", "Strip"), ("plate", "Filled plate")], "show": {"key": "mt_bars", "not": ["plate"]}},
    {"key": "mt_strip", "label": "Strip height (0 = auto)", "type": "slider", "min": 0, "max": 120, "step": 1, "group": "Mount",
     "show": {"key": "mt_fill", "in": ["strip"]}},
    {"key": "mt_fill_r", "label": "Fill corner radius (0 = plate radius)", "type": "slider", "min": 0, "max": 20, "step": 0.5, "group": "Mount",
     "show": {"key": "mt_bars", "not": ["plate"]}},
    {"key": "mt_fill_t", "label": "Fill thickness (0 = flange)", "type": "slider", "min": 0, "max": 12, "step": 0.5, "group": "Mount",
     "show": {"key": "mt_bars", "not": ["plate"]}},
    {"key": "mt_wings", "label": "Strip bears on the board", "type": "toggle", "group": "Mount",
     "show": {"key": "mt_bars", "not": ["plate"]}},
    {"key": "mt_pattern", "label": "Pattern", "type": "seg", "group": "Mount",
     "options": [("auto", "Auto"), ("row", "Row"), ("col", "Col"), ("corners", "Corners"), ("1", "1"), ("2V", "2V"),
                 ("2H", "2H"), ("4", "4"), ("diamond", "◇"), ("grid", "Grid"), ("none", "None")], "wrap": 4},
    {"key": "mt_cols", "label": "Columns", "type": "slider", "min": 1, "max": 8, "step": 1, "group": "Mount",
     "show": {"key": "mt_pattern", "in": ["grid"]}},
    {"key": "mt_rows", "label": "Rows (grid · studs per bar)", "type": "slider", "min": 1, "max": 8, "step": 1, "group": "Mount"},
    {"key": "mt_margin", "label": "Plate margin", "type": "slider", "min": 4, "max": 30, "step": 0.5, "group": "Mount"},
    {"key": "mt_fix", "label": "Fixing", "type": "seg", "group": "Mount",
     "options": [("plain", "Stud"), ("thread", "Thread"), ("tube", "Tube"), ("insert", "Insert"), ("bore", "Bolt"), ("screw", "Screw"),
                 ("jhook", "J-hook")], "wrap": 4,
     "show": {"key": "mt_pattern", "not": ["none"]}},
    {"key": "mt_bolt", "label": "Bolt", "type": "seg", "group": "Mount",
     "options": [(3, "M3"), (4, "M4"), (5, "M5"), (6, "M6")],
     "show": {"key": "mt_fix", "in": ["tube", "insert", "bore"]}},
    {"key": "mt_bolt_from", "label": "Bolt from", "type": "seg", "group": "Mount",
     "options": [("back", "The back · nut on the front"), ("front", "The front · nut behind")],
     "show": {"key": "mt_fix", "in": ["bore"]}},
    {"key": "mt_nut", "label": "Nut", "type": "seg", "group": "Mount",
     "options": [("captive", "Captive hex pocket"), ("loose", "Loose on the face")],
     "show": {"key": "mt_bolt_from", "in": ["back"]}},
    {"key": "mt_head", "label": "Head seat", "type": "seg", "group": "Mount",
     "options": [("csk", "Countersunk"), ("pan", "Counterbored"), ("none", "On the face")],
     "show": {"key": "mt_fix", "in": ["bore", "screw"]}},
    {"key": "mt_screw_d", "label": "Screw Ø", "type": "seg", "group": "Mount",
     "options": [(3.0, "3"), (3.5, "3.5"), (4.0, "4"), (4.5, "4.5"), (5.0, "5")],
     "show": {"key": "mt_fix", "in": ["screw"]}},
    {"key": "mt_screw_len", "label": "Screw length", "type": "slider", "min": 12, "max": 60, "step": 1, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["screw"]}},
    {"key": "mt_len", "label": "Stud length (0 = board)", "type": "slider", "min": 0, "max": 30, "step": 0.5, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["plain", "thread", "tube", "insert"]}},
    {"key": "mt_tip", "label": "Tip chamfer", "type": "slider", "min": 0, "max": 2, "step": 0.1, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["plain", "thread", "tube", "insert", "bore"]}},
    {"key": "mt_thread_pitch", "label": "Thread pitch (0 = auto)", "type": "slider", "min": 0, "max": 2.5, "step": 0.05, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["thread"]}},
    {"key": "mt_j_bend", "label": "J bend radius", "type": "slider", "min": 3, "max": 10, "step": 0.5, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["jhook"]}},
    {"key": "mt_j_shaft", "label": "J shaft Ø (0 = auto)", "type": "slider", "min": 0, "max": 8, "step": 0.1, "group": "Mount",
     "show": {"key": "mt_fix", "in": ["jhook"]}},
    {"key": "mt_ears", "label": "Screw ears", "type": "seg", "group": "Mount",
     "options": [("none", "None"), ("sides", "Sides"), ("top", "Top"), ("bottom", "Bottom"), ("topbottom", "Top+Bot"), ("all", "All")], "wrap": 3},
    {"key": "mt_ear_screw", "label": "Screw Ø", "type": "seg", "group": "Mount",
     "options": [(3.0, "3"), (3.5, "3.5"), (4.0, "4"), (4.5, "4.5"), (5.0, "5")],
     "show": {"key": "mt_ears", "not": ["none"]}},
    {"key": "mt_ear_n", "label": "Ears per edge", "type": "slider", "min": 1, "max": 3, "step": 1, "group": "Mount",
     "show": {"key": "mt_ears", "not": ["none"]}},
    {"key": "mt_ear_wall", "label": "Ear wall", "type": "slider", "min": 2, "max": 6, "step": 0.5, "group": "Mount",
     "show": {"key": "mt_ears", "not": ["none"]}},
    {"key": "mt_ear_csk", "label": "Countersink", "type": "toggle", "group": "Mount",
     "show": {"key": "mt_ears", "not": ["none"]}},
]


# ---------------------------------------------------------------- suggestions

def resolve(p, want):
    """A copy of p with the family's mount suggestion (want["mount"]) filled in wherever the
    user left the control on auto: mt_bars = auto, mt_pattern = auto, mt_span = 0."""
    q = dict(p)
    sug = dict(want.get("mount") or {})
    if q["mt_bars"] == "auto":
        q["mt_bars"] = sug.get("mt_bars", "plate")
    if q["mt_pattern"] == "auto" and "mt_pattern" in sug:
        q["mt_pattern"] = sug["mt_pattern"]
        for k in ("mt_cols", "mt_rows"):
            if k in sug:
                q[k] = sug[k]
    if q["mt_bars"] == "twin":
        q["mt_pattern"] = "twin"
        if int(q["mt_span"]) <= 0:
            q["mt_span"] = int(sug.get("mt_span", 0))
    elif q["mt_pattern"] == "twin":
        q["mt_pattern"] = "auto"
    return q


def bar_w(p, b):
    """Width of one bar / the standard single-column plate: stud Ø + 2 margins, rounded up to 0.5
    (22 on the imperial board, 19 on the metric)."""
    return math.ceil((BD.stud_d(b) + 2 * float(p["mt_margin"])) * 2) / 2


def auto_span(p, b, feature_w):
    """Bars as far apart as the feature allows: the bars stay 3 mm inside its ends."""
    rs = BD.row_step(b)
    return max(2, int((feature_w - bar_w(p, b) - 6.0) // rs))


# ---------------------------------------------------------------- patterns

def _named(p, b):
    """Explicit patterns as offsets from the first hole; None for auto-type patterns."""
    pat = p["mt_pattern"]
    cs, rs = BD.col_step(b), BD.row_step(b)
    py, st = float(b["pitch_y"]), float(b["stagger"])
    if pat == "1":
        return [(0, 0)]
    if pat == "2V":
        return [(0, 0), (0, cs)]
    if pat == "2H":
        return [(0, 0), (rs, 0)]
    if pat == "4":
        return [(0, 0), (rs, 0), (0, cs), (rs, cs)]
    if pat == "diamond":
        if BD.is_lattice(b):
            return [(0, 0), (st, py), (-st, py), (0, 2 * py)]
        return [(0, 0), (rs, 0), (0, cs), (rs, cs)]
    if pat == "grid":
        nc, nr = int(p["mt_cols"]), int(p["mt_rows"])
        return [(i * rs, j * cs) for j in range(nr) for i in range(nc)]
    if pat == "twin":
        nr = max(1, int(p["mt_rows"]))
        span = max(1, int(p["mt_span"]))
        return [(i * span * rs, j * cs) for j in range(nr) for i in (0, 1)]
    return None


def _best_anchor(b, w, h, margin):
    """Lattice shift that puts the most holes under the plate, centred."""
    px, py = float(b["pitch_x"]), float(b["pitch_y"])
    x0, x1, y0, y1 = -w / 2 + margin, w / 2 - margin, -h / 2 + margin, h / 2 - margin
    best = None
    for i in range(8):
        for j in range(8):
            ax, ay = i * px / 8, j * py / 4
            holes = BD.holes_in(b, x0, x1, y0, y1, ax, ay)
            if not holes:
                continue
            cx = sum(x for x, _ in holes) / len(holes)
            cy = sum(y for _, y in holes) / len(holes)
            score = (len(holes), -round(abs(cx) + abs(cy), 3))
            if best is None or score > best[0]:
                best = (score, (ax, ay), holes)
    return best


def _keepout(p, holes, h, want):
    """Bore fixings need the front of the plate: drop holes behind the family's
    feature band at the bottom of the plate."""
    ko = float(want.get("keepout", 0.0))
    fix = p["mt_fix"]
    if fix not in ("bore", "screw") or ko <= 0:
        return holes, None
    if fix == "screw":
        r = float(p["mt_screw_d"]) + 0.3 + 1.0                 # head Ø / 2 + clearance
        name = "Screw"
    else:
        bolt = int(p["mt_bolt"])
        r = F.across_corners(F.NUT[bolt][0]) / 2 + 1.0
        name = "Bore"
    kept = [(x, y) for x, y in holes if y - r > -h / 2 + ko]
    if not kept:
        return holes, f"No hole clears the feature in front of the plate for a {name} fixing; raise the plate or use studs."
    if len(kept) < len(holes):
        return kept, f"{len(holes) - len(kept)} hole(s) behind the feature skipped ({name} needs the front)."
    return kept, None


def plan(p, b, want):
    """
    want: dict(w, h, keepout) the family asks for (plate size). Returns a plan:
        w, h           final plate size (grown to cover the pattern)
        studs          [(x, y)] in plate coords (plate centre = origin)
        anchor         (ax, ay) position of board hole (0, 0) in plate coords
        notes, warns
    """
    margin = float(p["mt_margin"])
    pat = p["mt_pattern"]
    w, h = float(want["w"]), float(want["h"])
    warns = []
    if pat == "none":
        return dict(w=w, h=h, studs=[], anchor=(0.0, 0.0), warns=warns)
    if pat == "twin" and int(p["mt_span"]) <= 0:
        p = dict(p, mt_span=auto_span(p, b, w))
    named = _named(p, b)
    if named is not None:
        xs = [x for x, _ in named]
        ys = [y for _, y in named]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        studs = [(round(x - cx, 4), round(y - cy, 4)) for x, y in named]
        need_w = max(xs) - min(xs) + 2 * margin
        if pat == "twin":
            need_w = max(xs) - min(xs) + bar_w(p, b)          # the bars' outer edges
        need_h = max(ys) - min(ys) + 2 * margin
        if need_w > w + 1e-6:
            warns.append(f"Plate widened to {need_w:.1f} to cover the pattern.")
            w = need_w
        if need_h > h + 1e-6:
            warns.append(f"Plate heightened to {need_h:.1f} to cover the pattern.")
            h = need_h
        anchor = (round(-cx, 4), round(-cy, 4))
        studs, note = _keepout(p, studs, h, want)
        if note:
            warns.append(note)
        if p["mt_fix"] == "screw":
            anchor = screw_anchor(b, anchor)
        out = dict(w=w, h=h, studs=studs, anchor=anchor, warns=warns)
        if pat == "twin":
            span = int(p["mt_span"])
            bx = span * BD.row_step(b) / 2
            out["bars"] = [-bx, bx]
            out["bar_w"] = bar_w(p, b)
            out["span"] = span
            ko = float(want.get("keepout", 0.0))
            strip = h if p.get("mt_fill") == "plate" else (float(p["mt_strip"]) or max(14.0, ko + 6.0))
            out["strip"] = min(strip, h)
        return out
    # auto family
    best = _best_anchor(b, w, h, margin)
    if best is None:
        # plate too small: use one hole in the centre and grow the plate around it
        d = float(b["hole_d"]) + 2 * margin
        w, h = max(w, d), max(h, d)
        warns.append("Plate too small for a hole under the margin: one stud at the centre.")
        return dict(w=w, h=h, studs=[(0.0, 0.0)], anchor=(0.0, 0.0), warns=warns)
    _, anchor, holes = best
    if p["mt_fix"] == "screw":
        anchor = screw_anchor(b, anchor)
    if pat == "row":
        top = max(y for _, y in holes)
        holes = [(x, y) for x, y in holes if abs(y - top) < 1e-6]
    elif pat == "col":
        xs = sorted(set(x for x, _ in holes), key=lambda x: abs(x))
        holes = [(x, y) for x, y in holes if abs(x - xs[0]) < 1e-6]
    elif pat == "corners":
        xs, ys = [x for x, _ in holes], [y for _, y in holes]
        lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
        holes = [(x, y) for x, y in holes if (abs(x - lo_x) < 1e-6 or abs(x - hi_x) < 1e-6)
                 and (abs(y - lo_y) < 1e-6 or abs(y - hi_y) < 1e-6)]
    holes, note = _keepout(p, holes, h, want)
    if note:
        warns.append(note)
    return dict(w=w, h=h, studs=holes, anchor=anchor, warns=warns)


def screw_anchor(b, anchor):
    """Screw fixing: shift the plate half a pitch on the board so its screw points land on board
    material between the holes (square boards: half a pitch each way; lattices: one row down,
    which is between the column's holes and half a step from the staggered neighbours)."""
    ax, ay = anchor
    if BD.is_lattice(b):
        return (ax, round(ay + float(b["pitch_y"]), 4))
    return (round(ax + BD.row_step(b) / 2, 4), round(ay + BD.col_step(b) / 2, 4))


def head_seat(body, p, x, y, t, thru, head_d, head_h, td=None):
    """Head seat on the front face at (x, y): countersunk cone, counterbore, or nothing."""
    kind = p["mt_head"]
    if kind == "csk":
        depth = (head_d - thru) / 2                   # 90° countersink
        cone = (cq.Workplane("XY").workplane(offset=t + 0.01).center(x, y).circle(head_d / 2)
                .workplane(offset=-depth - 0.01).circle(thru / 2).loft())
        return body.cut(cone), head_d / 2 + 0.8
    if kind == "pan":
        return body.cut(G.cyl(head_d / 2, t - head_h, t + 1, x, y)), head_d / 2 + 0.8
    return body, head_d / 2 + 0.8


# ---------------------------------------------------------------- twin bars

def twin_plate(mp, p, t, spine_t=0.0):
    """Backing for a twin-bar holder in plate coordinates: two bars (bar_w × h × t) at mp["bars"],
    a strip (w × strip × t) along the bottom, and - two-part, wings on - the strip extended back to
    0.3 off the board face beside and between the bars (the spines sit behind the bars)."""
    w, h, bw = mp["w"], mp["h"], mp["bar_w"]
    r = float(p["plate_r"])
    e = float(p["plate_edge"])
    sh = mp["strip"]
    fr = float(p.get("mt_fill_r") or 0) or r                   # follows the plate corner radius by default
    ft = float(p.get("mt_fill_t") or 0) or t
    body = None
    for x in mp["bars"]:
        bar = G.rbox(x - bw / 2, x + bw / 2, -h / 2, h / 2, 0, t, min(fr, bw / 2 - 0.1))   # bars share the fill's radius
        if e > 0.05:
            bar = G.try_chamfer(bar, ">Z", min(e, t / 2 - 0.1))
        body = bar if body is None else body.union(bar)
    strip = G.rbox(-w / 2, w / 2, -h / 2, -h / 2 + sh, 0, ft, min(fr, sh / 2 - 0.1, w / 2 - 0.1))
    if e > 0.05:
        strip = G.try_chamfer(strip, ">Z", min(e, ft / 2 - 0.1))
    body = body.union(strip)
    if spine_t > 0 and p["mt_wings"]:
        z0 = -(spine_t - 0.3)
        gaps = sorted((x - bw / 2 - 0.6, x + bw / 2 + 0.6) for x in mp["bars"])
        x = -w / 2
        for g0, g1 in gaps:
            if g0 - x > 1.0:
                body = body.union(G.box(x, g0, -h / 2, -h / 2 + sh, z0, 0.01))
            x = max(x, g1)
        if w / 2 - x > 1.0:
            body = body.union(G.box(x, w / 2, -h / 2, -h / 2 + sh, z0, 0.01))
    return body


def bar_plan(mp):
    """The plan of one bar on its own (for the single-column spine): studs at x = 0."""
    x0 = mp["bars"][0]
    studs = [(0.0, y) for x, y in mp["studs"] if abs(x - x0) < 1e-6]
    return dict(mp, w=mp["bar_w"], studs=studs, bars=None)


# ---------------------------------------------------------------- building

def t_min(p):
    """Plate thickness a fixing needs."""
    if p["mt_fix"] == "bore":
        af, m = F.NUT[int(p["mt_bolt"])]
        return m + F.MATERIALS[p["material"]]["depth"] + 1.5
    return 0.0


def stud_len(p, b):
    v = float(p["mt_len"])
    return v if v > 0 else float(b["stud_len"])


def ext_thread_pitch(p, d):
    v = float(p["mt_thread_pitch"])
    if v > 0:
        return v
    return 1.25 if d >= 7 else (1.0 if d >= 5.5 else 0.8)


def _rolled_j(d, x, y, shaft, bend_r, tip):
    z1 = -shaft
    shaft_c = cq.Workplane("XY").center(x, y).circle(d / 2).extrude(z1)
    bend = (cq.Workplane("XY").workplane(offset=z1).center(x, y).circle(d / 2)
            .revolve(90, (0, bend_r, 0), (1, bend_r, 0)))
    ey, ez = y + bend_r, z1 - bend_r
    tip_c = cq.Workplane("XZ").workplane(offset=-ey).center(x, ez).circle(d / 2).extrude(-tip)
    tip_c = G.try_fillet(tip_c, ">Y", min(d / 2 - 0.5, tip - 0.5))
    return shaft_c.union(bend).union(tip_c).clean()


def _hole(r, z0, z1, x, y, td):
    """Round hole, or a teardrop when its axis lies horizontal in the print."""
    if td is None:
        return G.cyl(r, z0, z1, x, y)
    return G.teardrop_hole(r, z0, z1, td, x, y)


def apply(body, mp, p, ctx):
    """Add the studs / ears to the plate body. ctx: dict(b, stud_d, td, orient,
    no_supports, export, render_thread, warns, derived, t)."""
    b, d, td = ctx["b"], ctx["stud_d"], ctx["td"]
    t = ctx["t"]
    fix = p["mt_fix"] if mp["studs"] else "none"
    L = stud_len(p, b)
    tip = float(p["mt_tip"])
    warns, der = ctx["warns"], ctx["derived"]
    mat = F.MATERIALS[p["material"]]
    bolt = int(p["mt_bolt"])
    studs = mp["studs"]
    blockers = ctx.setdefault("blockers", [])   # (x, y, r) things on the front face
    der["studs"] = len(studs)
    der["stud_d"] = round(d, 2)
    der["stud_len"] = round(L, 1)
    if L > float(b["t"]) + float(b["back"]) and fix in ("plain", "thread", "tube", "insert"):
        warns.append(f"Studs {L:.1f} long run past the board ({b['t']}) and its back clearance ({b['back']}).")

    if fix == "plain":
        for x, y in studs:
            body = body.union(G.stud_solid(d, L, x, y, tip=tip, teardrop=td))
    elif fix == "thread":
        pitch = ext_thread_pitch(p, d)
        der["thread"] = f"Ø{d:.2f} × {pitch:.2f} external"
        if d < 6:
            warns.append("Printed external thread under Ø6 will not hold; use Tube/Bore or a plain stud.")
        if td is not None:
            warns.append("Threaded studs are round: their underside overhangs in this orientation.")
        for x, y in studs:
            s = G.stud_solid(d, L, x, y, tip=tip)
            if ctx["export"] or ctx["render_thread"]:
                groove, _ = G.external_thread_groove(d, pitch, L, mat["thread"] * 0.5)
                s = s.cut(groove.translate((x, y, -L)))
            body = body.union(s)
    elif fix == "tube":
        pitch = F.PITCH[bolt]
        clear = mat["thread"]
        r_minor = F.minor_d(bolt, pitch) / 2 + clear
        wall = d / 2 - (bolt / 2 + clear)
        der["tube_wall"] = round(wall, 2)
        st = F.thread_status(bolt, pitch)
        if st == "no":
            warns.append(f"Printed M{bolt} internal thread is below the floor: M5+ with a 0.4 nozzle.")
        elif st == "warn":
            warns.append(f"Printed M{bolt} thread: print at 0.12 mm layers.")
        if wall < 1.2:
            warns.append(f"Tube wall {wall:.2f} under the M{bolt} thread is thin (< 1.2).")
        if td is not None:
            warns.append("Threaded tubes are round studs: their underside overhangs in this orientation.")
        # the thread lives in a plain cylinder built on its own, then joined: keeps the helix boolean simple
        threaded = ctx["export"] or ctx["render_thread"]
        tube0 = cq.Workplane("XY").circle(d / 2).extrude(-L)
        tube0 = G.try_chamfer(tube0, "<Z", min(tip, 1.0))
        if threaded:
            groove, r_bore = G.thread_groove(bolt, pitch, L, clear)
            tube = tube0.cut(groove.translate((0, 0, -L))).cut(G.cyl(r_bore, -L - 1, 1))
            if not tube.solids().size() or not tube.val().isValid():
                warns.append("Printed thread failed to build in this tube; exported with a plain bore.")
                tube = tube0.cut(G.cyl(r_minor, -L - 1, 1))
        else:
            tube = tube0.cut(G.cyl(r_minor, -L - 1, 1))
        for x, y in studs:
            body = body.union(tube.translate((x, y, 0)))
            body = body.cut(G.cyl(r_minor, -1, t + 1, x, y))        # bolt passes the plate too
    elif fix == "insert":
        od, length, hole = F.INSERTS.get(bolt, F.INSERTS[5])
        wall = (d - hole) / 2
        der["insert_wall"] = round(wall, 2)
        if wall < 1.0:
            warns.append(f"Stud wall {wall:.2f} around an M{bolt} insert is thin; use a smaller insert.")
        if length + 1 > L:
            warns.append(f"M{bolt} insert ({length} long) is longer than the stud; it will reach the plate.")
        for x, y in studs:
            body = body.union(G.stud_solid(d, L, x, y, tip=tip, teardrop=td))
            body = body.cut(_hole(hole / 2, -L - 1, -L + length + 1, x, y, td))
    elif fix == "bore":
        clear_d = F.CLEARANCE[bolt] + mat["hole"]
        af, m = F.NUT[bolt]
        pocket_af = af + mat["hex"]
        pocket_h = m + mat["depth"]
        loc = min(3.0, L)
        head_d = F.BOLT_HEAD.get(bolt, bolt * 2.0) + 0.6
        head_h = F.BOLT_HEAD_H.get(bolt, bolt * 0.7)
        if p["mt_bolt_from"] == "back":
            if p["mt_nut"] == "captive":
                if pocket_h > t - 1.0:
                    warns.append(f"Nut pocket {pocket_h:.1f} deep leaves under 1 mm of plate behind it; thicken the plate.")
                der["bolt"] = f"M{bolt} from the back · captive nut {af:g} AF in a {pocket_af:.1f} pocket, {pocket_h:.1f} deep"
            else:
                der["bolt"] = f"M{bolt} from the back · loose nut on the face"
        else:
            der["bolt"] = f"M{bolt} from the front · {dict(csk='countersunk', pan='counterbored', none='head on the face')[p['mt_head']]} Ø{head_d:.1f} · nut behind the board"
            if p["mt_head"] == "csk" and (head_d - clear_d) / 2 > t - 1.0:
                warns.append("Countersink deeper than the plate: counterbore or thicken the plate.")
        for x, y in studs:
            if loc > 0 and float(b["t"]) >= 6:
                body = body.union(G.stud_solid(d, loc, x, y, tip=min(tip, 0.6), teardrop=td))
            body = body.cut(_hole(clear_d / 2, -L - 2, t + 1, x, y, td))
            if p["mt_bolt_from"] == "back" and p["mt_nut"] == "captive":
                body = body.cut(G.hex_prism(pocket_af, t - pocket_h, t + 80, x, y))   # through anything in front
                blockers.append((x, y, F.across_corners(pocket_af) / 2))
            elif p["mt_bolt_from"] == "back":
                blockers.append((x, y, F.across_corners(pocket_af) / 2 + 1))
            else:
                body, br = head_seat(body, p, x, y, t, clear_d, head_d, head_h)
                blockers.append((x, y, br))
        x, y = studs[0]
        ctx.setdefault("dims", []).append(DM.D((x - clear_d / 2, y, t), (x + clear_d / 2, y, t), (0, 0, 6), kind="dia", key="bolt_hole"))
        if p["mt_bolt_from"] == "back" and p["mt_nut"] == "captive":
            ctx["dims"].append(DM.D((x - pocket_af / 2, y, t), (x + pocket_af / 2, y, t), (0, 0, 12), label=f"{pocket_af:.1f} AF", key="nut_pocket"))
        elif p["mt_bolt_from"] == "front" and p["mt_head"] != "none":
            ctx["dims"].append(DM.D((x - head_d / 2, y, t), (x + head_d / 2, y, t), (0, 0, 12), kind="dia", key="head"))
    elif fix == "screw":
        sd = float(p["mt_screw_d"])
        thru = F.WOOD_SCREW.get(sd, sd + 0.5) + mat["hole"]
        head_d = sd * 2.0 + 0.6
        head_h = sd * 0.6
        Ls = float(p["mt_screw_len"])
        der["screw"] = (f"{len(studs)} × Ø{sd:g} × {Ls:g} {dict(csk='countersunk', pan='counterbored', none='head on the face')[p['mt_head']]} "
                        f"straight into the board between its holes · {Ls - t:.0f} in the board")
        if Ls - t > float(b["t"]) + float(b["back"]):
            warns.append(f"Screws run {Ls - t - float(b['t']):.0f} mm out of the back of the board.")
        if Ls - t < 10:
            warns.append("Under 10 mm of screw in the board: longer screws.")
        for x, y in studs:
            body = body.cut(_hole(thru / 2, -1, t + 1, x, y, td))
            body, br = head_seat(body, p, x, y, t, thru, head_d, head_h)
            blockers.append((x, y, br))
        x, y = studs[0]
        ctx.setdefault("dims", []).append(DM.D((x - thru / 2, y, t), (x + thru / 2, y, t), (0, 0, 6), kind="dia", key="screw_hole"))
        if p["mt_head"] != "none":
            ctx["dims"].append(DM.D((x - head_d / 2, y, t), (x + head_d / 2, y, t), (0, 0, 12), kind="dia", key="head"))
    elif fix == "jhook":
        if float(b["t"]) > 8:
            warns.append("J-hooks are for thin boards (≤ 8 mm); on this board they cannot roll through.")
        shaft = float(p["mt_j_shaft"]) or max(2.5, d - 0.5)
        bend_r = float(p["mt_j_bend"])
        hole = float(b["hole_d"])
        sag = bend_r - math.sqrt(max(0.0, bend_r ** 2 - (float(b["t"]) / 2) ** 2))
        der["j_pass"] = f"shaft {shaft:.1f} + bend {sag:.2f} = {shaft + sag:.2f} in Ø{hole:.1f}"
        if shaft + sag > hole - 0.1:
            warns.append("J-hook will not roll through: thin the shaft or enlarge the bend radius.")
        top = max(y for _, y in studs)
        for x, y in studs:
            if abs(y - top) < 1e-6:
                body = body.union(_rolled_j(shaft, x, y, float(b["t"]) + 1.5, bend_r, 2.5))
            else:
                body = body.union(G.stud_solid(d - 0.2, float(b["t"]) + 1.0, x, y, tip=0.8, teardrop=td))
        if td is not None and abs(td[1]) > 0.5:
            warns.append("J-hooks print best on their side; upright the bend underside overhangs.")
        if float(b["back"]) < bend_r + shaft:
            warns.append(f"J needs ~{bend_r + shaft:.0f} mm behind the board; preset says {b['back']}.")

    # ears
    ears = p["mt_ears"]
    if ears != "none":
        body = _ears(body, mp, p, ctx)
    return body


def _ears(body, mp, p, ctx):
    t = ctx["t"]
    w, h = mp["w"], mp["h"]
    screw = float(p["mt_ear_screw"])
    clear = F.WOOD_SCREW.get(screw, screw + 0.5) + F.MATERIALS[p["material"]]["hole"]
    wall = float(p["mt_ear_wall"])
    r = clear / 2 + wall
    n = int(p["mt_ear_n"])
    csk = bool(p["mt_ear_csk"])
    which = p["mt_ears"]
    edges = []
    if which in ("sides", "all"):
        edges += ["left", "right"]
    if which in ("top", "topbottom", "all"):
        edges += ["top"]
    if which in ("bottom", "topbottom", "all"):
        edges += ["bottom"]
    ctx["derived"]["ears"] = f"{len(edges) * n} × Ø{clear:.1f}" + (" csk" if csk else "")
    for e in edges:
        for i in range(n):
            f = (i + 1) / (n + 1)
            if e == "left":
                cx, cy = -w / 2 - r + 0.5, -h / 2 + f * h
            elif e == "right":
                cx, cy = w / 2 + r - 0.5, -h / 2 + f * h
            elif e == "top":
                cx, cy = -w / 2 + f * w, h / 2 + r - 0.5
            else:
                cx, cy = -w / 2 + f * w, -h / 2 - r + 0.5
            ear = G.cyl(r, 0, t, cx, cy)
            # web joining the ear to the plate edge
            if e in ("left", "right"):
                web = G.box(min(cx, 0) - (0 if cx < 0 else 0), max(cx, 0), cy - r, cy + r, 0, t)
            else:
                web = G.box(cx - r, cx + r, min(cy, 0), max(cy, 0), 0, t)
            body = body.union(ear).union(web)
            body = body.cut(G.cyl(clear / 2, -1, t + 1, cx, cy))
            if csk:
                dk = max(clear + 2, screw * 2.0)
                cone = (cq.Workplane("XY").workplane(offset=t + 0.01).center(cx, cy).circle(dk / 2)
                        .workplane(offset=-dk / 2).circle(0.1).loft())
                body = body.cut(cone)
    return body


def context_board(mp, b, w, h, hole_pad=0.0):
    """Board stub behind the plate, holes on the lattice the plate uses.
    hole_pad enlarges the holes (the batch test uses the print shrink so
    the deliberately oversize CAD studs are compared as printed)."""
    ax, ay = mp["anchor"]
    pad = max(float(b["pitch_x"]), float(b["pitch_y"])) * 1.2 + 10
    x0, x1, y0, y1 = -w / 2 - pad, w / 2 + pad, -h / 2 - pad, h / 2 + pad
    stub = G.box(x0, x1, y0, y1, -float(b["t"]), 0)
    r = (float(b["hole_d"]) + hole_pad) / 2
    for x, y in BD.holes_in(b, x0 + r, x1 - r, y0 + r, y1 - r, ax, ay):
        stub = stub.cut(G.cyl(r, -float(b["t"]) - 1, 1, x, y))
    return stub
