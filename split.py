"""
Split layer for PEGBOARDLAB: one accessory, two prints.

Every family with a plate splits: the right-angle ones (rack, tray,
holster, gridfinity, hook, clip) because one piece cannot print
support-free with round studs, the flat ones (plate, mag strip) so a
front can be swapped or printed in another colour on a stock stud plate,
and magnets can drop in at the joint with no print pause. A family opts
in by existing; there is no switch (the loader refuses a SPLIT flag).
Split cuts the finished part on a plane through the plate thickness,
sp_t from the back:

    stud plate   back of the plate + studs. Prints mating face down,
                 studs straight up: round studs, no teardrop flats,
                 clean printed threads / insert holes.
    body         front of the plate ("slab") + the feature. Prints in the
                 family's own orientation, now without studs.

Both faces at the cut are plain planar sections of one outline: no
chamfer, no radius, so the seam closes and the assembly reads as one
part. The joint is holes only, fasteners from the back of the stud
plate (heads recessed flush, hidden against the board):

    screw   self-tapping / drywall / wood screw through a clearance hole
            in the stud plate into a pilot hole in the slab
    nut     bolt into a hex nut captive in the slab's mating face: the
            pocket opens on the face, the nut is trapped once the parts meet
    thread  bolt into a printed thread in the slab (M5+ at 0.12 layers)
    insert  bolt into a heat-set insert in the slab

Hole positions: auto (lattice cell centres, then corners, 2 across, 2 up,
then a free scan of the plate, whichever first fits), corners, 2 across,
2 up, grid, cells, free, or manual X-Y per hole; inset from the edge and an X-Y shift on top. Every hole is
checked against the studs, the mount layer's own pockets and the plate
edge; a hole that would hit a stud is skipped with a warning.

Printability in the body: the joint holes lie horizontal in an upright
or side print, so round holes become teardrops and the hex pocket is
turned flat-side-up (a short bridge rather than a 30° roof). In a
face-down print (plate, mag strip) every joint hole is vertical and the
pockets open upward: nothing to bridge at all.

What a family has to do: nothing. Keep the feature in front of the plate,
register anything cut into the plate thickness in ctx["blockers"] as
(x, y, r) so the joint holes avoid it, cut body features with
ctx["td_body"] (the body print's teardrop direction) and, for a pocket
that must open on the body's mating face, append the cutter to
ctx["body_cuts"] instead of cutting it yourself: it is applied to the
body after the split. Every hole is volume-checked after cutting: one
that breaks into a channel, pocket or hole is reported.
"""

import math

import cadquery as cq

import boards as BD
import fasteners as F
import geometry as G

FLOOR = 1.2          # material left in front of a blind joint hole
HEAD_FLOOR = 0.6     # stud plate left under a head recess

PARAMS = {
    "sp_on": False,
    "sp_view": "assembly",   # assembly | explode | plate | body
    "sp_plate_orient": "face",   # face (round studs, root on a layer line) | upright | side (studs along the layers)
    "sp_gap": 25.0,          # explode distance
    "sp_t": 3.0,             # stud plate thickness (the cut, from the back)
    "sp_join": "nut",        # screw | nut | thread | insert
    "sp_bolt": 4,            # M size for nut / thread / insert
    "sp_screw": 3.5,         # screw Ø for screw
    "sp_head": "csk",        # csk | socket  (screws are always csk)
    "sp_fit": "medium",      # close | medium | free   (bolt clearance, ISO 273)
    "sp_d": 0.0,             # hole Ø override: bolt clearance / screw pilot, 0 = table
    "sp_depth": 8.0,         # blind hole depth into the slab (engagement)
    "sp_pattern": "auto",    # auto | cells | corners | 2H | 2V | grid | free | manual
    "sp_cols": 2,
    "sp_rows": 2,
    "sp_inset": 0.0,         # hole centre from the plate edge, 0 = auto (head + 2.5)
    "sp_dx": 0.0,
    "sp_dy": 0.0,
    "sp_n": 4,               # manual: holes used
    "sp_x1": -12.0, "sp_y1": -12.0, "sp_x2": 12.0, "sp_y2": -12.0,
    "sp_x3": -12.0, "sp_y3": 12.0, "sp_x4": 12.0, "sp_y4": 12.0,
}

ON = {"key": "sp_on", "eq": True}
BOLTS = {"key": "sp_join", "in": ["nut", "thread", "insert"]}


def _sl(key, label, lo, hi, step, group, *show, note=None):
    d = {"key": key, "label": label, "type": "slider", "min": lo, "max": hi, "step": step, "group": group, "show": list(show)}
    if note:
        d["note"] = note
    return d


def _seg(key, label, options, group, *show, wrap=None):
    d = {"key": key, "label": label, "type": "seg", "options": options, "group": group, "show": list(show)}
    if wrap:
        d["wrap"] = wrap
    return d


SCHEMA = [
    {"key": "sp_on", "label": "Split: stud plate + body (two prints)", "type": "toggle", "group": "Print", "show": []},
    _seg("sp_view", "Show", [("assembly", "Assembled"), ("explode", "Exploded"), ("plate", "Stud plate"), ("body", "Body")], "Print", ON, wrap=2),
    _sl("sp_gap", "Explode gap", 5, 80, 1, "Print", ON, {"key": "sp_view", "in": ["explode"]}),
    _seg("sp_plate_orient", "Stud plate print", [("face", "Face down · round studs"), ("upright", "Upright · studs along the layers"),
                                                 ("side", "On its side · studs along the layers")], "Print", ON, wrap=1),
    _seg("sp_join", "Joint", [("screw", "Screw"), ("nut", "Bolt + nut"), ("thread", "Bolt + thread"), ("insert", "Bolt + insert")], "Joint", ON, wrap=2),
    _seg("sp_bolt", "Bolt", [(3, "M3"), (4, "M4"), (5, "M5"), (6, "M6")], "Joint", ON, BOLTS),
    _seg("sp_screw", "Screw Ø", [(3.0, "3"), (3.5, "3.5"), (4.0, "4"), (4.5, "4.5"), (5.0, "5")], "Joint", ON, {"key": "sp_join", "in": ["screw"]}),
    _seg("sp_head", "Head", [("csk", "Countersunk"), ("socket", "Socket cap")], "Joint", ON, BOLTS),
    _seg("sp_fit", "Bolt fit", [("close", "Close"), ("medium", "Medium"), ("free", "Free")], "Joint", ON, BOLTS),
    _sl("sp_d", "Hole Ø override (0 = table)", 0, 12, 0.05, "Joint", ON),
    _sl("sp_t", "Stud plate thickness", 2, 8, 0.5, "Joint", ON),
    _sl("sp_depth", "Hole depth into the body", 3, 30, 0.5, "Joint", ON),
    _seg("sp_pattern", "Pattern", [("auto", "Auto"), ("cells", "Cells"), ("corners", "Corners"), ("2H", "2 across"),
                                   ("2V", "2 up"), ("grid", "Grid"), ("free", "Free"), ("manual", "Manual")], "Joint", ON, wrap=4),
    _sl("sp_cols", "Columns", 1, 6, 1, "Joint", ON, {"key": "sp_pattern", "in": ["grid"]}),
    _sl("sp_rows", "Rows", 1, 6, 1, "Joint", ON, {"key": "sp_pattern", "in": ["grid"]}),
    _sl("sp_inset", "Inset from the edge (0 = auto)", 0, 40, 0.5, "Joint", ON, {"key": "sp_pattern", "not": ["manual"]}),
    _sl("sp_dx", "Shift X", -40, 40, 0.5, "Joint", ON, {"key": "sp_pattern", "not": ["manual"]}),
    _sl("sp_dy", "Shift Y", -40, 40, 0.5, "Joint", ON, {"key": "sp_pattern", "not": ["manual"]}),
    _sl("sp_n", "Holes", 1, 4, 1, "Joint", ON, {"key": "sp_pattern", "in": ["manual"]}),
] + [
    _sl(f"sp_{a}{i}", f"Hole {i} {a.upper()}", -150, 150, 0.5, "Joint", ON, {"key": "sp_pattern", "in": ["manual"]})
    for i in (1, 2, 3, 4) for a in ("x", "y")
]

CLEAR = {"close": F.CLEARANCE_FINE, "medium": F.CLEARANCE, "free": F.CLEARANCE_COARSE}


def active(p, fam):
    """Split is on for every family that has a plate (the nut has none)."""
    return bool(p["sp_on"]) and bool(getattr(fam, "PLATE", True))


def min_side(J):
    """Plate width / height that fits two joint holes edge to edge."""
    return 4 * J["rh"] + 2.6


# ---------------------------------------------------------------- the joint

def joint(p, mat):
    """
    Numbers for the joint, from the fastener tables and the material preset.
    Returns dict(join, size, thru, head, head_d, head_depth, zs, dep, t_min,
    rh (collision radius), body (what is cut into the slab), warns, fastener).
    """
    join = p["sp_join"]
    over = float(p["sp_d"])
    hole_c = mat["hole"]
    warns = []
    J = dict(join=join, warns=warns)
    if join == "screw":
        d = float(p["sp_screw"])
        thru = F.WOOD_SCREW.get(d, d + 0.5) + hole_c
        pilot = over if over > 0.5 else round(0.8 * d, 2)
        dk = 2.2 * d
        J.update(size=d, thru=thru, head="csk", head_d=dk, head_depth=(dk - thru) / 2, pilot=pilot)
        J["body"] = ("pilot", pilot)
        dep = float(p["sp_depth"])
        rh_face = pilot / 2
        J["label"] = f"Ø{d:g} self-tapping screw"
    else:
        m = int(p["sp_bolt"])
        thru = (over if over > 0.5 else CLEAR[p["sp_fit"]][m]) + (0 if over > 0.5 else hole_c)
        if p["sp_head"] == "socket":
            dk, k = F.SHCS[m]
            J.update(head="socket", head_d=dk + 0.6, head_depth=k + 0.3)
        else:
            dk = F.CSK[m] + 0.4
            J.update(head="csk", head_d=dk, head_depth=(dk - thru) / 2)
        J.update(size=m, thru=thru)
        dep = float(p["sp_depth"])
        if join == "nut":
            af, nm = F.NUT[m]
            pocket_af = af + mat["hex"]
            pocket_h = nm + mat["depth"]
            J.update(pocket_af=pocket_af, pocket_h=pocket_h)
            J["body"] = ("nut", pocket_af, pocket_h)
            dep = max(dep, pocket_h + 2.0)
            rh_face = F.across_corners(pocket_af) / 2
            J["label"] = f"M{m} {'countersunk' if J['head'] == 'csk' else 'socket cap'} bolt + M{m} hex nut ({af:g} AF)"
        elif join == "thread":
            pitch = F.PITCH[m]
            st = F.thread_status(m, pitch)
            if st == "no":
                warns.append(f"Printed M{m} thread is below the floor for a 0.4 nozzle: use a captive nut or insert.")
            elif st == "warn":
                warns.append(f"Printed M{m} thread: print the body at 0.12 mm layers.")
            dep = max(dep, 1.5 * m)
            J.update(pitch=pitch, r_minor=F.minor_d(m, pitch) / 2 + mat["thread"])
            J["body"] = ("thread", m, pitch)
            rh_face = m / 2 + mat["thread"]
            J["label"] = f"M{m} {'countersunk' if J['head'] == 'csk' else 'socket cap'} bolt into a printed thread"
        else:
            od, length, hole = F.INSERTS.get(m, F.INSERTS[5])
            dep = max(dep, length + 1.0)
            J.update(ins_hole=hole, ins_len=length)
            J["body"] = ("insert", hole)
            rh_face = max(hole, thru) / 2
            J["label"] = f"M{m} {'countersunk' if J['head'] == 'csk' else 'socket cap'} bolt into an M{m} heat-set insert"
    zs = float(p["sp_t"])
    need = J["head_depth"] + HEAD_FLOOR
    if zs < need - 1e-6:
        zs = math.ceil(need * 2) / 2
        warns.append(f"Stud plate thickened to {zs:g} for the {J['head']} head recess.")
    J["zs"] = zs
    J["dep"] = dep
    J["t_min"] = zs + dep + FLOOR
    J["rh"] = max(J["head_d"] / 2, rh_face)
    return J


def lengths(J):
    """(min, max) fastener length for the joint. Reach is measured from the
    stud plate's back face; countersunk bolts and screws are specified over
    the head, socket caps under it (the head sits in its counterbore)."""
    zs, dep = J["zs"], J["dep"]
    if J["join"] == "screw":
        lo, hi = zs + 0.6 * dep, zs + dep
    elif J["join"] == "nut":
        lo, hi = zs + J["pocket_h"] + 1.0, zs + dep - 0.5
    elif J["join"] == "thread":
        lo, hi = zs + 1.2 * J["size"], zs + dep - 0.5
    else:
        lo, hi = zs + 0.8 * J["ins_len"], zs + dep - 0.5
    seat = J["head_depth"] - 0.3 if J["head"] == "socket" else 0.0
    return lo - seat, hi - seat


def fastener_text(J, n):
    lo, hi = lengths(J)
    table = F.SCREW_LENGTHS if J["join"] == "screw" else F.BOLT_LENGTHS
    std = [L for L in table if lo - 1e-6 <= L <= hi + 1e-6]
    pick = (f"stock {' / '.join(f'{L:g}' for L in std)}" if std else "no stock length fits: change the hole depth")
    return f"{n} × {J['label']}, length {lo:.0f}–{hi:.0f} mm ({pick})"


# ---------------------------------------------------------------- hole positions

def _clear(pt, studs, stud_r, blockers, rh):
    x, y = pt
    for sx, sy in studs:
        if math.hypot(x - sx, y - sy) < rh + stud_r + 0.8:
            return False
    for bx, by, br in blockers:
        if math.hypot(x - bx, y - by) < rh + br + 0.8:
            return False
    return True


def _pick(good, spacing):
    """Up to four of `good`: one per quadrant, the one furthest out toward
    its corner, then the ones furthest from those already chosen; every
    pair at least `spacing` apart."""
    out = []
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        q = [c for c in good if sx * c[0] >= -1e-6 and sy * c[1] >= -1e-6]
        if not q:
            continue
        c = max(q, key=lambda c: (round(sx * c[0] + sy * c[1], 3), min(abs(c[0]), abs(c[1]))))
        if c not in out and all(math.hypot(c[0] - x, c[1] - y) >= spacing for x, y in out):
            out.append(c)
    rest = [c for c in good if c not in out]
    while len(out) < 4 and rest:
        c = max(rest, key=lambda c: min(math.hypot(c[0] - x, c[1] - y) for x, y in out) if out else 0.0)
        rest.remove(c)
        if all(math.hypot(c[0] - x, c[1] - y) >= spacing for x, y in out):
            out.append(c)
    return out


def _cells(b, mp, x_in, y_in, need, spacing, ok=lambda c: True):
    """Lattice-aligned positions inside the inset rectangle that clear every
    board hole by `need` and pass `ok` (studs, pockets): cell centres and
    edge midpoints of the lattice, spread by _pick."""
    ax, ay = mp["anchor"]
    px, py = float(b["pitch_x"]), float(b["pitch_y"])
    lattice = BD.holes_in(b, -x_in - 2 * px, x_in + 2 * px, -y_in - 2 * py, y_in + 2 * py, ax, ay)
    if not lattice:
        return []
    cands = set()
    for x, y in lattice:
        for cx, cy in ((x + px / 2, y + py / 2), (x + px / 2, y), (x, y + py / 2)):
            if abs(cx) <= x_in + 1e-6 and abs(cy) <= y_in + 1e-6:
                cands.add((round(cx, 3), round(cy, 3)))
    good = [c for c in cands if min(math.hypot(c[0] - x, c[1] - y) for x, y in lattice) >= need and ok(c)]
    return _pick(good, spacing)


def _free(x_in, y_in, spacing, ok, step=2.0):
    """Any position on a 2 mm scan of the inset rectangle that clears
    everything: the last resort when nothing lattice-aligned fits."""
    def axis(lim):
        n = max(1, int(round(2 * lim / step)) + 1)
        return [0.0] if n == 1 else [round(-lim + 2 * lim * i / (n - 1), 2) for i in range(n)]
    good = [(x, y) for x in axis(x_in) for y in axis(y_in) if ok((x, y))]
    return _pick(good, spacing)


def holes(p, b, mp, J, blockers, stud_d):
    """[(x, y)] joint holes in plate coordinates, plus warnings."""
    w, h = mp["w"], mp["h"]
    rh = J["rh"]
    warns = []
    lim_x, lim_y = w / 2 - rh - 0.8, h / 2 - rh - 0.8
    inset = float(p["sp_inset"]) or (rh + 2.5)
    x_in, y_in = max(0.0, min(w / 2 - inset, lim_x)), max(0.0, min(h / 2 - inset, lim_y))
    studs, stud_r = mp["studs"], stud_d / 2
    pat = p["sp_pattern"]

    def corners():
        return [(-x_in, -y_in), (x_in, -y_in), (-x_in, y_in), (x_in, y_in)]

    def two_h():                       # the inset is a wish, the spacing a rule: spread to the edge limit if needed
        xx = min(lim_x, max(x_in, rh + 0.5))
        return [(-xx, 0.0), (xx, 0.0)]

    def two_v():
        yy = min(lim_y, max(y_in, rh + 0.5))
        return [(0.0, -yy), (0.0, yy)]

    def grid():
        nc, nr = int(p["sp_cols"]), int(p["sp_rows"])
        xs = [0.0] if nc == 1 else [-x_in + i * 2 * x_in / (nc - 1) for i in range(nc)]
        ys = [0.0] if nr == 1 else [-y_in + j * 2 * y_in / (nr - 1) for j in range(nr)]
        return [(x, y) for y in ys for x in xs]

    def ok(c):
        return _clear(c, studs, stud_r, blockers, rh)

    def cells():
        return _cells(b, mp, x_in, y_in, rh + stud_r + 0.8, 2 * rh + 1.0, ok)

    def free():
        return _free(x_in, y_in, 2 * rh + 1.0, ok)

    def manual():
        n = int(p["sp_n"])
        return [(float(p[f"sp_x{i}"]), float(p[f"sp_y{i}"])) for i in range(1, n + 1)]

    pats = {"corners": corners, "2H": two_h, "2V": two_v, "grid": grid, "cells": cells, "free": free, "manual": manual}
    dx, dy = float(p["sp_dx"]), float(p["sp_dy"])

    def place(fn):
        pts = [(x + dx, y + dy) for x, y in fn()]
        clamped = False
        out = []
        for x, y in pts:
            cx, cy = max(-lim_x, min(lim_x, x)), max(-lim_y, min(lim_y, y))
            clamped |= abs(cx - x) > 1e-6 or abs(cy - y) > 1e-6
            out.append((round(cx, 3), round(cy, 3)))
        out = list(dict.fromkeys(out))
        kept = []
        for pt in out:
            if _clear(pt, studs, stud_r, blockers, rh) and all(math.hypot(pt[0] - kx, pt[1] - ky) >= 2 * rh + 1.0 - 1e-6 for kx, ky in kept):
                kept.append(pt)
        return out, kept, clamped

    def auto():
        tried, chosen = [], None
        for name in ("cells", "corners", "2H", "2V", "free"):
            pts, kept, clamped = place(pats[name])
            tried.append((name, pts, kept, clamped))
            if len(kept) >= 2 and len(kept) == len(pts):
                chosen = tried[-1]
                break
        return chosen or max(tried, key=lambda t: len(t[2]))

    partial = False
    if pat == "auto":
        used, pts, kept, clamped = auto()
        if 2 <= len(kept) < len(pts):          # best available: say so, it is not a fault
            warns.append(f"auto: {len(kept)} of {len(pts)} {used} positions clear the studs and pockets.")
            pts, partial = kept, True
    else:
        pts, kept, clamped = place(pats[pat])
        used = pat
        if len(kept) < 2 and not (pat == "manual" and len(kept) == int(p["sp_n"])):
            name, apts, akept, aclamped = auto()
            if len(akept) > len(kept):
                warns.append(f"{pat}: only {len(kept)} hole(s) clear the studs; auto pattern ({name}) used instead.")
                used, pts, kept, clamped = f"auto:{name}", apts, akept, aclamped
    if clamped:
        warns.append("Joint hole(s) pulled inside the plate edge.")
    if len(kept) < len(pts) and not partial:
        warns.append(f"{len(pts) - len(kept)} joint hole(s) would hit a stud, a pocket or each other: skipped. Try Cells, a shift, or Manual.")
    if not kept:
        warns.append("No joint hole fits: the parts have nothing to bolt with. Smaller fastener, wider plate, or Manual.")
    elif len(kept) == 1:
        warns.append("Only one joint hole fits: the body can pivot on it. Try M3, a wider plate, or Manual positions.")
    return kept, used, warns


# ---------------------------------------------------------------- cutting

def _csk(dk, d, x, y):
    depth = (dk - d) / 2
    cone = (cq.Workplane("XY").workplane(offset=-0.02).circle(dk / 2 + 0.02)
            .workplane(offset=depth + 0.04).circle(d / 2).loft())
    return cone.translate((x, y, 0))


def _hole(r, z0, z1, x, y, td):
    if td is None:
        return G.cyl(r, z0, z1, x, y)
    return G.teardrop_hole(r, z0, z1, td, x, y)


def plate_orient(p):
    """How the stud plate prints. Face down: round studs, but the stud root is
    a layer line (the weak way for a bending load). Upright / side: studs lie
    along the layers (2-3x stronger at the root in FDM) with teardrop flats.
    A J-hook fixing always lies on its side."""
    if p["mt_fix"] == "jhook" and p["mt_pattern"] != "none":
        return "side"
    return p.get("sp_plate_orient", "face") if p.get("sp_plate_orient") in ("face", "upright", "side") else "face"


def nominal_volume(J):
    """Material one joint hole removes from the body when it meets solid all the way."""
    kind = J["body"][0]
    dep = J["dep"]
    if kind == "pilot":
        return math.pi * (J["pilot"] / 2) ** 2 * dep
    if kind == "nut":
        return (math.sqrt(3) / 2) * J["pocket_af"] ** 2 * J["pocket_h"] + math.pi * (J["thru"] / 2) ** 2 * (dep - J["pocket_h"])
    if kind == "thread":
        return math.pi * J["r_minor"] ** 2 * dep
    return math.pi * (J["ins_hole"] / 2) ** 2 * dep


def split(body, p, ctx, J, pts):
    """One-piece body -> (stud plate, body) with the joint holes cut."""
    zs = J["zs"]
    bb = body.val().BoundingBox()

    def slab(z0, z1):
        return G.box(bb.xmin - 2, bb.xmax + 2, bb.ymin - 2, bb.ymax + 2, z0, z1)
    plate = body.intersect(slab(bb.zmin - 2, zs))
    feat = body.intersect(slab(zs, bb.zmax + 2))
    for cutter in ctx.get("body_cuts", []):          # pockets that open on the mating face
        feat = feat.cut(cutter)
    for cutter in ctx.get("plate_cuts", []):
        plate = plate.cut(cutter)
    body_orient = ctx["orient"]
    ns = ctx["no_supports"]
    td = G.teardrop_dir(body_orient) if (ns and body_orient != "back") else None
    td_p = G.teardrop_dir(plate_orient(p)) if ns else None      # the stud plate's own print
    up = G.down_vector(body_orient)
    hex_rot = 30.0 if abs(up[0]) > 0.5 else 0.0     # flat side up in the print
    dep = J["dep"]
    kind = J["body"][0]
    threaded = ctx["export"] or ctx["render_thread"]
    z0 = zs - 0.5
    nominal = nominal_volume(J)
    broken = []
    removed_total = 0.0
    for x, y in pts:
        v_before = feat.val().Volume()
        plate = plate.cut(_hole(J["thru"] / 2, -1, zs + 1, x, y, td_p))
        if J["head"] == "csk":
            plate = plate.cut(_csk(J["head_d"], J["thru"], x, y))
        else:
            plate = plate.cut(_hole(J["head_d"] / 2, -1, J["head_depth"], x, y, td_p))
        if kind == "pilot":
            feat = feat.cut(_hole(J["pilot"] / 2, z0, zs + dep, x, y, td))
        elif kind == "nut":
            feat = feat.cut(G.hex_prism(J["pocket_af"], z0, zs + J["pocket_h"], x, y, rot=hex_rot))
            feat = feat.cut(_hole(J["thru"] / 2, z0, zs + dep, x, y, td))
        elif kind == "thread":
            m, pitch = J["body"][1], J["body"][2]
            if threaded:
                groove, r_bore = G.thread_groove(m, pitch, dep - 1.5 * pitch, ctx["mat"]["thread"])
                cut = feat.cut(groove.translate((x, y, zs))).cut(G.cyl(r_bore, z0, zs + dep, x, y))
                if cut.solids().size() and cut.val().isValid():
                    feat = cut
                else:
                    ctx["warns"].append("Printed joint thread failed to build; plain bore instead.")
                    feat = feat.cut(G.cyl(J["r_minor"], z0, zs + dep, x, y))
            else:
                feat = feat.cut(G.cyl(J["r_minor"], z0, zs + dep, x, y))
        else:
            feat = feat.cut(G.cyl(J["ins_hole"] / 2, z0, zs + dep, x, y))
        removed = v_before - feat.val().Volume()
        removed_total += removed
        if removed < 0.96 * nominal:
            broken.append(f"({x:g}, {y:g}) {removed / nominal:.0%}")
    if broken:
        ctx["warns"].append("Joint hole breaks into a feature (solid met: " + ", ".join(broken)
                            + "): move it (Manual / shift) or reduce the hole depth.")
    if td is not None and kind == "thread":
        ctx["warns"].append("Joint threads lie horizontal in the body print: a captive nut or insert prints cleaner.")
    ctx["derived"]["joint_removed_mm3"] = round(removed_total, 1)
    return plate, feat


def apply(body, p, ctx, mp, J, placed=None):
    """Run the joint on a finished one-piece body. Fills ctx['derived'] and warns.
    `placed` is an earlier holes() result (so branding could avoid the holes).
    Returns dict(plate, body, holes, pattern, orients) or None when no hole fits."""
    pts, used, warns = placed or holes(p, ctx["b"], mp, J, ctx.get("blockers", []), ctx["stud_d"])
    ctx["warns"] += warns
    der = ctx["derived"]
    zs, t = J["zs"], ctx["t"]
    der["split"] = f"stud plate {zs:g} + body slab {t - zs:g} = {t:g}"
    der["joint"] = f"{len(pts)} × {J['label']} · {used}"
    der["joint_holes"] = "  ".join(f"({x:g}, {y:g})" for x, y in pts)
    der["joint_hole"] = (f"Ø{J['thru']:.2f} through the stud plate, {J['head']} Ø{J['head_d']:.1f} × {J['head_depth']:.1f} deep · "
                         + {"pilot": f"pilot Ø{J.get('pilot', 0):.2f} × {J['dep']:g}",
                            "nut": f"nut pocket {J.get('pocket_af', 0):.2f} AF × {J.get('pocket_h', 0):.2f}, bore to {J['dep']:g}",
                            "thread": f"M{J['size']} thread × {J['dep']:g}",
                            "insert": f"insert hole Ø{J.get('ins_hole', 0):g} × {J['dep']:g}"}[J["body"][0]])
    der["fasteners"] = fastener_text(J, len(pts))
    if not pts:
        return None
    if J["body"][0] == "nut" and G.teardrop_dir(ctx["orient"]) is not None:   # horizontal hex pockets: flat roofs are designed bridges
        der["bridges_mm2"] = round(float(der.get("bridges_mm2", 0)) + len(pts) * J["pocket_af"] / math.sqrt(3) * J["pocket_h"], 1)
    plate, feat = split(body, p, ctx, J, pts)
    return dict(plate=plate, body=feat, holes=pts, pattern=used, zs=zs, removed=ctx["derived"].pop("joint_removed_mm3"),
                orients={"plate": plate_orient(p), "body": ctx["orient"]})


def layout(parts, spec, gap=12.0):
    """Both parts in print coordinates side by side: [(name, shape)]."""
    o = spec["split"]["orients"]
    plate = G.lay_out(parts["plate"], o["plate"])
    extras = [parts["body"]] + ([spec["brand_solid"]] if spec.get("brand_solid") is not None else [])
    laid = G.lay_out_group([cq.Workplane("XY").add(s) if not isinstance(s, cq.Workplane) else s for s in extras], o["body"])
    dx = plate.val().BoundingBox().xlen + gap
    out = [("plate", plate.val()), ("body", laid[0].translate((dx, 0, 0)).val())]
    if len(laid) > 1:
        out.append(("brand", laid[1].translate((dx, 0, 0)).val()))
    return out


def assembly_note(name, p, J, parts, der):
    o = parts["orients"]
    lines = [f"{name}: two-part print and assembly", "=" * (len(name) + 32), "",
             f"Stud plate  : prints {G.ORIENTS[o['plate']][0].lower()}; the flat mating face is on the bed,",
             f"              studs straight up. Size {der.get('print_size_plate')} mm, unsupported {der.get('unsupported_plate')}.",
             f"Body        : prints {G.ORIENTS[o['body']][0].lower()}. Size {der.get('print_size_body')} mm,",
             f"              unsupported {der.get('unsupported_body')}.",
             f"Cut         : {der.get('split')} mm. Both mating faces are plain planes of the same outline.",
             f"Studs       : Ø{der.get('stud_d')} × {der.get('stud_len')}" + (f" · root {der['stud_root']}" if der.get('stud_root') else "")
             + (f" · taper {der['stud_taper']}" if der.get('stud_taper') else ""),
             "", f"Joint       : {der.get('joint')}", f"Holes       : {der.get('joint_hole')}",
             f"Positions   : {der.get('joint_holes')}  (x, y from the plate centre)",
             f"Fasteners   : {der.get('fasteners')}", ""]
    j = J["join"]
    steps = ["1. Print both parts. Elephant-foot compensation on (the mating faces touch the bed),",
             "   no brim on the stud plate's mating face, or trim it."]
    if j == "nut":
        steps += ["2. Drop a nut into each hex pocket on the body's mating face (press flat; the pocket is",
                  "   0.3 deeper than the nut so it does not hold the faces apart).",
                  "3. Offer the stud plate up, heads from the back, and tighten in a cross pattern.",
                  "   The nuts are trapped between the parts and cannot turn or drop out."]
    elif j == "thread":
        steps += ["2. Chase each printed thread once with a bolt (no nut) to clear strings.",
                  "3. Offer the stud plate up, heads from the back, tighten gently: a printed thread",
                  "   strips if you crank it."]
    elif j == "insert":
        steps += ["2. Heat-set an insert into each hole on the body's mating face, flush or 0.2 below.",
                  "3. Offer the stud plate up, heads from the back, tighten in a cross pattern."]
    else:
        steps += ["2. Offer the stud plate up and drive each screw from the back through the clearance",
                  "   hole into the pilot hole; stop when the head seats, do not strip the pilot."]
    steps += ["4. Hang it: the heads sit flush in the stud plate's back, nothing shows from the front."]
    return "\n".join(lines + steps) + "\n"
