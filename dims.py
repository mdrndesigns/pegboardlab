"""
Dimension lines for the viewer. A dimension is the segment a-b, drawn
offset by the vector o (extension lines from a and b to the dimension
line), with a label - the length by default, "Ø" or "□" where asked.

    D(a, b, o, label=None, key=None)  -> dict(a, b, o, t, k)

Families append dimensions to ctx["dims"] in their own (holder) frame:
x along the wall, y up, z out of the board, flange back at z = 0. The
model adds the generic set (overall size, spine, studs, bars) in the
board frame and shifts the family's by the spine thickness for the
assembly view; print view gets each laid part's bed footprint instead.
"""


def num(v):
    v = float(v)
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def D(a, b, o, label=None, key=None, kind=None):
    a = [float(x) for x in a]
    b = [float(x) for x in b]
    L = sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5
    if label is None:
        label = num(L)
        if kind == "dia":
            label = "Ø" + label
        elif kind == "sq":
            label = "□" + label
    return dict(a=a, b=b, o=[float(x) for x in o], t=str(label), k=key or "")


def shift(dims, dx=0.0, dy=0.0, dz=0.0):
    out = []
    for d in dims:
        e = dict(d)
        e["a"] = [d["a"][0] + dx, d["a"][1] + dy, d["a"][2] + dz]
        e["b"] = [d["b"][0] + dx, d["b"][1] + dy, d["b"][2] + dz]
        out.append(e)
    return out


def bbox_dims(bb, prefix="", gap=8.0):
    """Width (bottom front), height (right, back plane), depth (bottom right) of a bounding box."""
    return [
        D((bb.xmin, bb.ymin, bb.zmax), (bb.xmax, bb.ymin, bb.zmax), (0, -gap, 0), key=prefix + "width"),
        D((bb.xmax, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmin), (gap, 0, 0), key=prefix + "height"),
        D((bb.xmax, bb.ymin, bb.zmin), (bb.xmax, bb.ymin, bb.zmax), (0, -gap, 0), key=prefix + "depth"),
    ]


def bed_dims(bb, prefix="", gap=8.0):
    """Footprint of a part laid on the bed (Z up): x along the front edge, y along the right edge,
    height at the front-right corner."""
    return [
        D((bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymin, bb.zmin), (0, -gap, 0), key=prefix + "x"),
        D((bb.xmax, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmin), (gap, 0, 0), key=prefix + "y"),
        D((bb.xmax, bb.ymin, bb.zmin), (bb.xmax, bb.ymin, bb.zmax), (gap, -gap, 0), key=prefix + "z"),
    ]


def group_cuts(cuts, sig):
    """First occurrence of each distinct cut (by sig) and, for repeated ones, the pitch to the next."""
    firsts, pitches, seen = [], [], {}
    for c in cuts:
        s = sig(c)
        if s not in seen:
            seen[s] = c
            firsts.append(c)
        elif s not in {k for k, _ in pitches}:
            pitches.append((s, (seen[s], c)))
    return firsts, [pair for _, pair in pitches]
