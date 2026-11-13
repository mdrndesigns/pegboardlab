"""
IRWIN - screwdrivers (with the chisel, awl and marking knife beside them),
pliers and cutters straddling fingers, Quick-Grip spring clamps biting a
rail on two arms, and the combination square: POCKET holders face-out,
lift up and out, twin bars from 90 wide.
"""
from families._kit import install


def driver_cuts(d, s, c):
    shafts = [float(v) for v in d.get("sizes", []) if not isinstance(v, list)] or [d["shaft"]] * int(d["count"])
    n = len(shafts)
    cuts = [dict(kind="open", x=round((i - (n - 1) / 2) * d["pitch"], 3), z=d["depth"] - 10.0, w=sh + 1.5, keep=bool(d["keep"]))
            for i, sh in enumerate(shafts)]
    return dict(pk_w=n * d["pitch"] + 14.0, pk_d=d["depth"], pk_h=d["height"], pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


def plier_cuts(d, s, c):
    n = int(d["count"])
    pitch = d["gap"] + d["finger"]
    cuts = [dict(kind="open", x=round((i - (n - 1) / 2) * pitch, 3), z=12.0, w=d["gap"], keep=False) for i in range(n)]
    return dict(pk_w=n * d["gap"] + (n - 1) * d["finger"] + 20.0, pk_d=d["depth"], pk_h=d["height"], pk_cuts=cuts,
                pk_r=2.0, pk_lip_h=3.0)


def square_cuts(d, s, c):
    return dict(pk_w=d["blade_w"] + 12.0, pk_d=20.0, pk_h=24.0, pk_r=2.0, pk_lip_h=3.0,
                pk_cuts=[dict(kind="slot", x=0.0, z=10.0, w=d["blade_w"] + 1.6, l=d["blade_t"] + 0.6, depth=0.0, funnel=1.0)])


TOOLS = {
    "drivers": dict(label="Screwdrivers · chisel · awl · knife", base="pocket",
                    dims=[("count", "Tools", 1, 12, 1, 7),
                          ("shaft", "Shaft Ø at the handle (all)", 3, 14, 0.1, 9),
                          ("sizes", "Shaft Ø per tool", "e.g. 6, 6, 9, 9, 5, 4, 3 · blank = the slider", 0, 0, []),
                          ("pitch", "Spacing (handles clear)", 20, 60, 1, 38),
                          ("depth", "Block depth", 20, 80, 1, 30),
                          ("height", "Block height", 12, 24, 0.5, 24),
                          ("keep", "Keep lips (1 = yes)", 0, 1, 1, 1)],
                    derive=driver_cuts,
                    note="shafts drop into front U's (Ø + 1.5), handles rest on top: one lift to draw"),
    "pliers": dict(label="Pliers · cutters · crimpers", base="pocket",
                   dims=[("count", "Tools", 1, 10, 1, 6),
                         ("gap", "Gap for one handle pair", 14, 40, 0.5, 26),
                         ("finger", "Finger between them", 6, 20, 0.5, 10),
                         ("depth", "Block depth", 30, 90, 1, 48),
                         ("height", "Block height", 12, 24, 0.5, 24)],
                   derive=plier_cuts,
                   note="each tool straddles a finger, one handle in the gap on either side, jaws up"),
    "clamp_rail": dict(label="Quick-Grip clamps · rail", base="shelf", pair=("across", "length"),
                       dims=[("count", "Clamps", 1, 10, 1, 4),
                             ("width", "Clamp width (handles)", 15, 80, 1, 30),
                             ("length", "Rail length", 60, 400, 1, 150),
                             ("reach", "Arm reach", 25, 120, 1, 40)],
                       fixed=dict(sh_arms=2, sh_tip="lip", sh_lip_t=6.0, sh_aw=22.0, sh_gap=4.0, sh_t=5.0, sh_side_lip=0.0,
                                  sh_front_lip=0.0, sh_back_lip=0.0, sh_notch_l=0.0, sh_r=3.0, sh_cuts=[]),
                       derive=lambda d, s, c: dict(sh_span=s, sh_reach=d["reach"],
                                                   sh_over=max(0.0, (d["length"] - (s * c["b"]["pitch_x"] + 22.0)) / 2)),
                       note="the clamps bite the rail's front edge; length ≥ clamps × width + 20"),
    "clamp_arm": dict(label="Quick-Grip clamps · lip arm", base="arm", pair=("across", "length"),
                      dims=[("length", "Rail length", 60, 400, 1, 150),
                            ("reach", "Reach", 25, 120, 1, 40)],
                      fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0, ar_pilots=True),
                      derive=lambda d, s, c: dict(ar_reach=d["reach"]),
                      note="the two arms under the clamp rail; the rail screws into their pilots"),
    "square": dict(label="Combination square", base="pocket",
                   dims=[("blade_w", "Blade width", 15, 50, 0.1, 25.4),
                         ("blade_t", "Blade thickness", 1, 5, 0.1, 2.4)],
                   derive=square_cuts,
                   note="the blade hangs face-out through a slot, the head rests on the block"),
}

def _blk(q):
    return f"block {q['pk_w']:g} × {q['pk_d']:g} × {q['pk_h']:g}"


NOTES = {
    "drivers": lambda d, q, s, g, c: {"count": _blk(q), "shaft": f"U {q['pk_cuts'][0]['w']:g} wide", "pitch": f"{len(q['pk_cuts'])} × {d['pitch']:g}",
                                      "sizes": f"{len(q['pk_cuts'])} U's: " + ", ".join(f"{x['w']:g}" for x in q["pk_cuts"])},
    "pliers": lambda d, q, s, g, c: {"count": _blk(q), "gap": f"pitch {d['gap'] + d['finger']:g}"},
    "clamp_rail": lambda d, q, s, g, c: {"count": f"needs {d['count'] * d['width'] + 20:g} of rail", "length": f"arms {s * c['b']['pitch_x']:.1f} apart",
                                        "reach": f"rail {d['reach'] - q['sh_gap'] - q['sh_lip_t'] - 0.5:g} deep"},
    "clamp_arm": lambda d, q, s, g, c: {"length": f"arms {s * c['b']['pitch_x']:.1f} apart"},
    "square": lambda d, q, s, g, c: {"blade_w": f"slot {q['pk_cuts'][0]['w']:g} × {q['pk_cuts'][0]['l']:g} · {_blk(q)}"},
}
for _k, _f in NOTES.items():
    TOOLS[_k]["notes"] = _f

install(globals(), "irwin", "Irwin", 3, "ir_", TOOLS, __doc__)
