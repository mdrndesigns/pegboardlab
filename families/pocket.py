"""
POCKET - an individual holder: a block on the flange's bottom edge with
vertical cut-outs, one tool or one small group per holder, tools shown
face-out. Prints upright (block and flange bottom on the bed), so every
slot, hole and pocket is a vertical wall and the entry funnels open upward:
no supports.

Backing: one standard column (22 × 61.8, three studs) - a wider block
overhangs it and its wings reach back to the board - or, from 90 wide,
twin bars (Mount · Backing) with the strip between them.

Cut-outs (pk_cuts, list of dicts; x along the wall from the block centre,
z = distance of the centre from the flange front):

    slot   rectangle w (along the wall) × l (front-back), through or blind
    hole   round Ø w, through or blind
    open   U from the front edge, width w, round end centred at z;
           keep=True adds 3 mm lips on the top either side of the mouth, so
           the tool lifts over them before it comes forward (it cannot be
           knocked out, it still draws in one move)
    peg    square drive peg, w across the flats, l tall, on the top
           (1/4 in 6.25, 3/8 in 9.40: a little under nominal, chamfered)

    depth  0 = through, > 0 = blind pocket that deep (floor stays)
    funnel entry chamfer at the top, mm (slots / holes)
"""

import cadquery as cq

import geometry as G
from dims import D, group_cuts
from families._lib import sl, seg, tog, lst

NAME = "pocket"
LABEL = "Pocket"
ORDER = 7
ORIENT = {"default": "upright", "no_supports": "upright"}

PARAMS = {
    "pk_w": 40.0,          # block width along the wall
    "pk_d": 30.0,          # block depth out from the flange
    "pk_h": 24.0,          # block height
    "pk_r": 2.0,           # vertical corner radius at the front
    "pk_lip_h": 3.0,       # keep-lip height
    "pk_ph": 40.0,         # flange height minimum (the stud grid grows it)
    "pk_wings": True,      # block beyond the flange reaches back to the board face (bears on it, stops rocking)
    "pk_cuts": [],         # cut-outs as dicts (the kits fill this)
    "pk_spec": [],         # cut-outs typed in the GUI, one token per feature - see spec_cuts()
    "pk_gap": 8.0,         # wall between typed cut-outs
}

SCHEMA = [
    sl("pk_w", "Block width", 20, 300, 0.5, "Pocket"),
    sl("pk_d", "Block depth", 10, 120, 0.5, "Pocket"),
    sl("pk_h", "Block height", 8, 80, 0.5, "Pocket"),
    sl("pk_r", "Front corner radius", 0, 10, 0.5, "Pocket"),
    sl("pk_lip_h", "Keep-lip height", 0, 8, 0.5, "Pocket"),
    sl("pk_ph", "Flange height (minimum)", 30, 160, 1, "Pocket"),
    tog("pk_wings", "Wings bear on the board", "Pocket"),
    lst("pk_spec", "Cut-outs · one per feature", "Pocket",
        hint="slot 4.5x17 @9, hole 12 d20, open 11.8 keep, peg 6.25 h10"),
    sl("pk_gap", "Wall between cut-outs", 3, 30, 0.5, "Pocket"),
]


def spec_cuts(p):
    """Cut-outs from the typed list, packed left to right with pk_gap between them, centred.
    Token grammar (space-separated fields):  kind size [@z] [dN] [keep] [hN]
        kind   slot | hole | open | peg   (a token starting with a number is a slot)
        size   w  or  w x l   (slot: w along the wall × l front-back; hole: Ø; open: U width; peg: □)
        @z     centre distance from the flange front (default: half the block depth; open: 10 in from the front)
        dN     blind, N deep (slot / hole); hN peg height; keep = keep lips (open)"""
    toks = [str(t) for t in (p.get("pk_spec") or [])]
    if not toks:
        return None
    Dp = float(p["pk_d"])
    gap = float(p["pk_gap"])
    cuts, widths = [], []
    for tok in toks:
        parts = tok.replace("×", "x").lower().split()
        if not parts:
            continue
        kind = parts[0] if parts[0] in ("slot", "hole", "open", "peg") else "slot"
        fields = parts[1:] if parts[0] == kind else parts
        size = fields[0] if fields else "10"
        w, l = (size.split("x", 1) + [None])[:2] if "x" in size else (size, None)
        try:
            w = float(w)
            l = float(l) if l is not None else None
        except ValueError:
            continue
        c = dict(kind=kind, x=0.0, w=w, z=Dp / 2 if kind != "open" else max(Dp - 10.0, w / 2 + 2.0), depth=0.0, funnel=0.8)
        if kind == "slot":
            c["l"] = l if l is not None else max(3.0, w * 0.3)
        if kind == "peg":
            c["l"] = 12.0
        for f in fields[1:]:
            try:
                if f.startswith("@"):
                    c["z"] = float(f[1:])
                elif f.startswith("d") and kind in ("slot", "hole"):
                    c["depth"] = float(f[1:])
                elif f.startswith("h") and kind == "peg":
                    c["l"] = float(f[1:])
                elif f == "keep" and kind == "open":
                    c["keep"] = True
            except ValueError:
                pass
        cuts.append(c)
        widths.append(w + (0.0 if kind != "open" or not c.get("keep") else 14.0))
    if not cuts:
        return None
    xs, x = [], 0.0
    for i, wd in enumerate(widths):
        if i:
            x += widths[i - 1] / 2 + gap + wd / 2
        xs.append(x)
    mid = (xs[0] + xs[-1]) / 2
    for c, xx in zip(cuts, xs):
        c["x"] = round(xx - mid, 3)
    W = max(float(p["pk_w"]), (xs[-1] - xs[0]) + widths[0] / 2 + widths[-1] / 2 + 2 * gap)
    return cuts, W


TWIN_FROM = 90.0        # blocks this wide and over ask for twin bars


def effective(p):
    """p with typed cut-outs (pk_spec) turned into pk_cuts and the block widened to hold them."""
    sc = spec_cuts(p)
    if sc is None:
        return p
    cuts, W = sc
    return dict(p, pk_cuts=cuts, pk_w=W)


def plan(p, ctx):
    """One standard column (the block may be wider and overhang it), or twin bars under a wide
    block. The mount suggestion is only used where the Mount controls are on auto."""
    p = effective(p)
    W = float(p["pk_w"])
    keep = float(p["pk_h"]) + 1.0
    mount = dict(mt_pattern="grid", mt_cols=1, mt_rows=3)
    twin = p["mt_bars"] == "twin" or (p["mt_bars"] == "auto" and W >= TWIN_FROM)
    if twin:
        mount["mt_bars"] = "twin"
        w = W
    else:
        w = ctx["stud_d"] + 2 * float(p["mt_margin"])
    return dict(w=w, h=max(float(p["pk_ph"]), keep + 14), brand=None, keepout=keep, mount=mount)


# local frame: X along the wall, Y = -(distance out from the board), Z = up. One rotation at the end.
def _rect(x, zc, w, l, z0, z1):
    return G.box(x - w / 2, x + w / 2, -zc - l / 2, -zc + l / 2, z0, z1)


def _frustum_rect(x, zc, w, l, top, c):
    return (cq.Workplane("XY").workplane(offset=top + 0.01).center(x, -zc).rect(w + 2 * c, l + 2 * c)
            .workplane(offset=-c - 0.01).rect(w, l).loft())


def _frustum_circ(x, zc, d, top, c):
    return (cq.Workplane("XY").workplane(offset=top + 0.01).center(x, -zc).circle(d / 2 + c)
            .workplane(offset=-c - 0.01).circle(d / 2).loft())


def block(p, t0, yb, fw, bar_xs=(0.0,)):
    """The pocket block in holder coordinates (flange front at z = t0, bottom at y = yb), plus notes.
    bar_xs: centres of the flange bars (each fw wide, a spine behind each); the wings fill the
    space beside / between them back to 0.3 off the board face."""
    W, D, H = float(p["pk_w"]), float(p["pk_d"]), float(p["pk_h"])
    top = yb + H
    blk = G.box(-W / 2, W / 2, -(t0 + D), -t0 + 0.01, yb, top)
    r = float(p["pk_r"])
    if r > 0.3:
        try:
            blk = blk.edges("|Z").edges(cq.selectors.BoxSelector((-W, -(t0 + D) - 0.5, yb - 1), (W, -(t0 + D) + 0.5, top + 1))).fillet(r)
        except Exception:
            pass
    lip_h = float(p["pk_lip_h"])
    adds, cuts, notes = [], [], []
    if p.get("pk_wings", True) and W > fw + 3:
        back = -(float(p.get("spine_t") or 0) or 5.0) + 0.3 if p.get("split") == "two" else 0.3
        gaps = sorted((xb - fw / 2 - 0.6, xb + fw / 2 + 0.6) for xb in bar_xs)
        edges, x = [], -W / 2
        for g0, g1 in gaps:
            if g0 - x > 1.0:
                edges.append((x, g0))
            x = max(x, g1)
        if W / 2 - x > 1.0:
            edges.append((x, W / 2))
        for x0, x1 in edges:
            adds.append(G.box(x0, x1, -t0, -back, yb, top))      # local Y = -(out): from the flange front back to the board
        notes.append("wings to the board")
    for c in p.get("pk_cuts") or []:
        k = c["kind"]
        x, w = float(c["x"]), float(c["w"])
        zc = t0 + float(c.get("z", D / 2))
        l = float(c.get("l", w))
        depth = float(c.get("depth", 0.0))
        z0 = top - depth if depth > 0 else yb - 1
        fun = float(c.get("funnel", 0.8))
        if k == "slot":
            cuts.append(_rect(x, zc, w, l, z0, top + 1))
            if fun > 0:
                cuts.append(_frustum_rect(x, zc, w, l, top, fun))
            notes.append(f"slot {w:g}×{l:g}" + (f" blind {depth:g}" if depth > 0 else ""))
        elif k == "hole":
            cuts.append(G.cyl(w / 2, z0, top + 1, x, -zc))
            if fun > 0:
                cuts.append(_frustum_circ(x, zc, w, top, fun))
            notes.append(f"Ø{w:g}" + (f" blind {depth:g}" if depth > 0 else ""))
        elif k == "open":
            zf = t0 + D
            cuts.append(G.box(x - w / 2, x + w / 2, -zf - 1, -zc, z0, top + lip_h + 1))
            cuts.append(G.cyl(w / 2, z0, top + lip_h + 1, x, -zc))
            if c.get("keep") and lip_h > 0.3:
                lw = float(c.get("lip_w", 7.0))
                for s in (-1, 1):
                    xa = x + s * (w / 2 + lw / 2)
                    lip = G.box(xa - lw / 2, xa + lw / 2, -zf, -zf + 4.0, top - 0.01, top + lip_h)
                    adds.append(G.try_chamfer(lip, ">Z", 1.0))
            notes.append(f"U {w:g}" + (" + keep lips" if c.get("keep") else ""))
        elif k == "peg":
            ph = l if "l" in c else 12.0
            peg = G.box(x - w / 2, x + w / 2, -zc - w / 2, -zc + w / 2, top - 0.01, top + ph)
            peg = G.try_chamfer(peg, ">Z", min(1.0, w / 4))
            adds.append(peg)
            notes.append(f"peg □{w:g}×{ph:g}")
    for a_ in adds:
        blk = blk.union(a_)
    for c in cuts:
        blk = blk.cut(c)
    blk = blk.rotate((0, 0, 0), (1, 0, 0), -90)        # local Z (up) -> board +Y, local -Y (out) -> board +Z
    return blk, notes


def cut_dims(p, t0, yb, dd):
    """Dimensions of the block and its cut-outs in the holder frame (y up, z out of the board)."""
    W, Dp, H = float(p["pk_w"]), float(p["pk_d"]), float(p["pk_h"])
    top, zf = yb + H, t0 + Dp
    dd.append(D((W / 2, top, t0), (W / 2, top, zf), (8, 0, 0), key="block_d"))
    dd.append(D((W / 2, yb, zf), (W / 2, top, zf), (8, 0, 0), key="block_h"))
    cuts = list(p.get("pk_cuts") or [])

    def sig(c):
        return (c["kind"], round(float(c["w"]), 2), round(float(c.get("l", c["w"])), 2), round(float(c.get("depth", 0)), 1),
                round(float(c.get("z", Dp / 2)), 2))

    firsts, pitches = group_cuts(cuts, sig)
    for c in firsts:
        k, x, w = c["kind"], float(c["x"]), float(c["w"])
        z = t0 + float(c.get("z", Dp / 2))
        l = float(c.get("l", w))
        dep = float(c.get("depth", 0.0))
        if k == "slot":
            dd.append(D((x - w / 2, top, z), (x + w / 2, top, z), (0, 6, 0), key="cut_w"))
            dd.append(D((x, top, z - l / 2), (x, top, z + l / 2), (-(w / 2 + 4), 4, 0), key="cut_l"))
        elif k == "hole":
            dd.append(D((x - w / 2, top, z), (x + w / 2, top, z), (0, 6, 0), kind="dia", key="cut_d"))
        elif k == "open":
            dd.append(D((x - w / 2, top, z), (x + w / 2, top, z), (0, 6, 0), key="u_w"))
            dd.append(D((x, top, z), (x, top, zf), (w / 2 + 4, 4, 0), key="u_in"))
            if c.get("keep"):
                dd.append(D((x + w / 2, top, zf - 4), (x + w / 2, top + float(p["pk_lip_h"]), zf - 4), (6, 0, 0), key="keep_lip"))
        elif k == "peg":
            ph = l if "l" in c else 12.0
            dd.append(D((x - w / 2, top + ph, z), (x + w / 2, top + ph, z), (0, 4, 0), kind="sq", key="peg"))
            dd.append(D((x + w / 2, top, z), (x + w / 2, top + ph, z), (5, 0, 0), key="peg_h"))
        if dep > 0 and k in ("slot", "hole"):
            dd.append(D((x + w / 2, top - dep, z), (x + w / 2, top, z), (0, 0, l / 2 + 5), key="blind"))
    for c0, c1 in pitches:
        z = t0 + float(c0.get("z", Dp / 2))
        y = top + (float(c0.get("l", 12.0)) if c0["kind"] == "peg" else 0.0)
        dd.append(D((float(c0["x"]), y, z), (float(c1["x"]), y, z), (0, 12, 0), key="pitch"))


def build(p, ctx, plate, mp):
    p = effective(p)
    if p.get("pk_spec"):
        ctx.setdefault("notes", {})["pk_spec"] = f"{len(p['pk_cuts'])} cut-outs · block {float(p['pk_w']):g} wide"
    cut_dims(p, ctx["t"], -ctx["h"] / 2, ctx.setdefault("dims", []))
    if mp.get("bars"):
        # twin bars: the mount layer's strip + wings already bear on the board
        blk, notes = block(dict(p, pk_wings=False), ctx["t"], -ctx["h"] / 2, ctx["w"])
    else:
        blk, notes = block(p, ctx["t"], -ctx["h"] / 2, ctx["w"])
    body = plate.union(blk)
    counted, seen = [], {}
    for n_ in notes:                                  # "slot 3.6×11 ×4" rather than four entries
        seen[n_] = seen.get(n_, 0) + 1
        if seen[n_] == 1:
            counted.append(n_)
    notes = [n_ + (f" ×{seen[n_]}" if seen[n_] > 1 else "") for n_ in counted]
    ctx["derived"]["pocket"] = f"block {float(p['pk_w']):g} × {float(p['pk_d']):g} × {float(p['pk_h']):g} · " + " · ".join(notes)
    ctx["brand"] = None
    return body
