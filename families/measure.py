"""
MEASURE - the precision set: calipers, micrometer, steel rules with the
protractor and compasses, loose spanners edge-on. POCKET holders, face-out,
one tool or one group each; wide ones on twin bars. Measured 2026-11-06/07.
"""
from families._kit import install


def caliper_cuts(d, s, c):
    return dict(pk_w=d["beam_w"] + 18.0, pk_d=d["beam_t"] + 24.0, pk_h=d["height"], pk_r=2.0, pk_lip_h=3.0,
                pk_cuts=[dict(kind="slot", x=0.0, z=9.0 + d["beam_t"] / 2, w=d["beam_w"] + 1.0, l=d["beam_t"] + 0.6,
                              depth=0.0, funnel=1.2)])


def micrometer_cuts(d, s, c):
    u = d["dia"] + 1.0
    return dict(pk_w=u + 30.0, pk_d=d["depth"], pk_h=d["height"], pk_r=2.0, pk_lip_h=3.0,
                pk_cuts=[dict(kind="open", x=0.0, z=d["depth"] / 2 - 1.0, w=u, keep=True)])


def rule_cuts(d, s, c):
    """Left to right from the block's left edge: the rule pockets (9 in), then the protractor slot
    (30 along the wall, at the front) with the compass holes behind it in a row 20 apart."""
    n, nh = int(d["rules"]), int(d["holes"])
    rw, rt, hd = d["rule_w"], d["rule_t"], d["hole_d"]
    D = 46.0
    xr = 9.0 + rw / 2                               # rule centre
    x0 = 18.0 + rw                                  # right-hand region starts here
    cuts = [dict(kind="slot", x=xr, z=8.0 + i * 6.0, w=rw + 2.0, l=rt + 0.6, depth=20.0, funnel=0.6) for i in range(n)]
    W = x0 + 8.0
    if d["protractor"] > 0.5:
        cuts.append(dict(kind="slot", x=x0 + 15.0, z=D - 8.0, w=30.0, l=3.6, depth=0.0, funnel=1.0))
        W = max(W, x0 + 30.0 + 8.0)
    hds = [float(v) for v in d.get("hole_sizes", []) if not isinstance(v, list)] or [hd] * nh
    nh = len(hds)
    hx = x0 + 2.0
    for i, hdi in enumerate(hds):
        hx += hdi / 2
        cuts.append(dict(kind="hole", x=hx, z=14.0, w=hdi, depth=20.0, funnel=0.8))
        hx += hdi / 2 + 8.0
    if nh:
        W = max(W, hx - 8.0 + 8.0)
    for cu in cuts:
        cu["x"] = round(cu["x"] - W / 2, 3)
    return dict(pk_w=W, pk_d=D, pk_h=24.0, pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


WRENCH_CLASSES = [("n_small", 3.6, 11.0), ("n_10", 5.0, 14.0), ("n_large", 6.0, 17.0), ("n_adj", 6.8, 21.0)]


def wrench_cuts(d, s, c):
    slots = [(float(v[0]), float(v[1])) for v in d.get("slots", []) if isinstance(v, list)]
    if not slots:
        for key, w, l in WRENCH_CLASSES:
            slots += [(w, l)] * int(d[key])
    n = len(slots)
    pitch = d["pitch"]
    cuts = [dict(kind="slot", x=round((i - (n - 1) / 2) * pitch, 3), z=22.0, w=w, l=l, depth=0.0, funnel=0.8)
            for i, (w, l) in enumerate(slots)]
    return dict(pk_w=max(40.0, n * pitch + 14.0), pk_d=38.0, pk_h=24.0, pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


TOOLS = {
    "caliper": dict(label="Caliper · face-out", base="pocket",
                    dims=[("beam_t", "Beam thickness", 2, 8, 0.1, 4.5),
                          ("beam_w", "Beam width", 10, 30, 0.5, 16),
                          ("height", "Slot depth (block height)", 12, 24, 0.5, 24)],
                    derive=caliper_cuts,
                    note="beam drops into a slot (+0.6 / +1.0), the head rests on top with the face out; metal caliper: 3.5"),
    "micrometer": dict(label="Micrometer", base="pocket",
                       dims=[("dia", "Handle Ø at the widest", 10, 40, 0.5, 19),
                             ("depth", "Block depth", 20, 80, 1, 34),
                             ("height", "Block height", 12, 24, 0.5, 20)],
                       derive=micrometer_cuts,
                       note="handle through a front U (Ø + 1), the frame rests on top behind the keep lips"),
    "rules": dict(label="Steel rules · protractor · compasses", base="pocket",
                  dims=[("rules", "Rules (stacked 6 apart)", 1, 8, 1, 4),
                        ("rule_w", "Rule width", 10, 40, 0.5, 26),
                        ("rule_t", "Rule thickness", 0.5, 3, 0.1, 1.2),
                        ("protractor", "Protractor slot 30 × 3.6 (1 = yes)", 0, 1, 1, 1),
                        ("holes", "Compass / pencil holes", 0, 10, 1, 4),
                        ("hole_d", "Hole Ø (all)", 6, 20, 0.5, 12),
                        ("hole_sizes", "Hole Ø per item", "e.g. 8, 10, 12, 14 · blank = the slider", 0, 0, [])],
                  derive=rule_cuts,
                  note="rules face-out in blind pockets, protractor arm through the front slot, holes 20 deep"),
    "wrenches": dict(label="Spanners · edge-on", base="pocket",
                     dims=[("n_small", "6-9 (slot 3.6 × 11)", 0, 10, 1, 4),
                           ("n_10", "10 (slot 5.0 × 14)", 0, 10, 1, 3),
                           ("n_large", "11-14 (slot 6.0 × 17)", 0, 10, 1, 4),
                           ("n_adj", "Small adjustable (slot 6.8 × 21)", 0, 4, 1, 1),
                           ("pitch", "Slot spacing", 8, 20, 0.5, 11),
                           ("slots", "Slots w × l per spanner", "e.g. 3.6x11, 5x14, 6.8x21 · blank = the classes", 0, 0, [])],
                     derive=wrench_cuts,
                     note="handle down through the slot, the head rests across it; small to large left to right"),
}

def _blk(q):
    return f"block {q['pk_w']:g} × {q['pk_d']:g} × {q['pk_h']:g}"


NOTES = {
    "caliper": lambda d, q, s, g, c: {"beam_t": f"slot {q['pk_cuts'][0]['w']:g} × {q['pk_cuts'][0]['l']:g}", "beam_w": _blk(q)},
    "micrometer": lambda d, q, s, g, c: {"dia": f"U {q['pk_cuts'][0]['w']:g} wide · {_blk(q)}"},
    "rules": lambda d, q, s, g, c: {"rules": _blk(q), "rule_w": f"pockets {q['pk_cuts'][0]['w']:g} × {q['pk_cuts'][0]['l']:g} · 20 deep"},
    "wrenches": lambda d, q, s, g, c: {"n_small": f"{len(q['pk_cuts'])} slots · {_blk(q)}", "pitch": f"{len(q['pk_cuts'])} × {d['pitch']:g} = {len(q['pk_cuts']) * d['pitch']:g}",
                                       "slots": ", ".join(f"{x['w']:g}×{x['l']:g}" for x in q["pk_cuts"])},
}
for _k, _f in NOTES.items():
    TOOLS[_k]["notes"] = _f

install(globals(), "measure", "Measure", 4, "me_", TOOLS, __doc__)
