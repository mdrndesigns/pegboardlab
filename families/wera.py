"""
WERA - Tool-Check PLUS on a pair of lip ARMs; Hex-Plus L-keys, Kraftform
screwdrivers, the Zyklop 8000 A ratchet and loose sockets in POCKET
holders (face-out, lift up and out). Pockets wider than 90 sit on twin bars.
"""
from families._kit import install

HEX_AF = [1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]          # 950/9 Hex-Plus Multicolour


def hex_cuts(d, s, c):
    n = len(HEX_AF)
    pitch, l = d["pitch"], d["slot_l"]
    cuts = [dict(kind="slot", x=round((i - (n - 1) / 2) * pitch, 3), z=d["depth"] / 2,
                 w=round(max(2.6, 1.155 * af + 0.6), 2), l=l, depth=0.0, funnel=0.8) for i, af in enumerate(HEX_AF)]
    return dict(pk_w=n * pitch + 14.0, pk_d=d["depth"], pk_h=d["height"], pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


def kraftform_cuts(d, s, c):
    dias = [float(v) for v in d.get("sizes", []) if not isinstance(v, list)] or [d["dia"]] * int(d["count"])
    n = len(dias)
    cuts = [dict(kind="hole", x=round((i - (n - 1) / 2) * d["pitch"], 3), z=d["depth"] / 2, w=dia + 1.0, depth=0.0, funnel=1.0)
            for i, dia in enumerate(dias)]
    return dict(pk_w=n * d["pitch"] + 14.0, pk_d=d["depth"], pk_h=d["height"], pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


def ratchet_cuts(d, s, c):
    u = d["neck"] + 0.8
    return dict(pk_w=u + 30.0, pk_d=d["depth"], pk_h=d["height"], pk_r=2.0, pk_lip_h=3.0,
                pk_cuts=[dict(kind="open", x=0.0, z=d["depth"] / 2, w=u, keep=True)])


def socket_cuts(d, s, c):
    n1, n2 = int(d["n14"]), int(d["n38"])
    pitch = d["pitch"]
    n = max(n1, n2)
    cuts = [dict(kind="peg", x=round((i - (n1 - 1) / 2) * pitch, 3), z=12.0, w=6.25, l=10.0) for i in range(n1)]
    cuts += [dict(kind="peg", x=round((i - (n2 - 1) / 2) * pitch, 3), z=12.0 + pitch, w=9.40, l=13.0) for i in range(n2)]
    return dict(pk_w=n * pitch + 14.0, pk_d=12.0 + pitch + 12.0, pk_h=d["height"], pk_cuts=cuts, pk_r=2.0, pk_lip_h=3.0)


TOOLS = {
    "toolcheck": dict(label="Tool-Check PLUS", base="arm", pair=("across", "length"),
                      dims=[("thick", "Case thickness (standing on its edge)", 15, 120, 1, 35),
                            ("length", "Case length along the wall", 60, 400, 1, 190)],
                      fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                      derive=lambda d, s, c: dict(ar_reach=d["thick"] + 10.0),
                      note="spec 190 × 100 × 35, 514 g; stands on its long edge on the arms"),
    "hexkeys": dict(label="Hex-Plus 950/9 L-keys", base="pocket",
                    dims=[("pitch", "Key spacing", 10, 30, 0.5, 16),
                          ("slot_l", "Slot length (front-back)", 8, 30, 0.5, 14),
                          ("depth", "Block depth", 16, 80, 1, 30),
                          ("height", "Block height", 12, 24, 0.5, 24)],
                    derive=hex_cuts,
                    note="1.5-10: long legs hang down through slots = 1.155 × AF + 0.6, short legs rest on top"),
    "kraftform": dict(label="Kraftform screwdrivers", base="pocket",
                      dims=[("count", "Drivers", 1, 12, 1, 6),
                            ("dia", "Shaft / blade Ø at the handle (all)", 3, 14, 0.1, 9.5),
                            ("sizes", "Blade Ø per driver", "e.g. 6, 6, 8, 9.5, 9.5, 5 · blank = the slider", 0, 0, []),
                            ("pitch", "Spacing (handles clear)", 20, 60, 1, 40),
                            ("depth", "Block depth", 16, 80, 1, 30),
                            ("height", "Block height", 12, 24, 0.5, 24)],
                      derive=kraftform_cuts,
                      note="blades drop through round holes, the handles rest on the block"),
    "ratchet": dict(label="Zyklop 8000 A ratchet", base="pocket",
                    dims=[("neck", "Neck Ø below the head", 6, 20, 0.1, 11),
                          ("depth", "Block depth", 20, 80, 1, 34),
                          ("height", "Block height", 12, 24, 0.5, 22)],
                    derive=ratchet_cuts,
                    note="neck through a front U (Ø + 0.8), head rests on top behind the keep lips"),
    "sockets": dict(label="Sockets · square pegs", base="pocket",
                    dims=[("n14", "1/4 in sockets", 0, 12, 1, 3),
                          ("n38", "3/8 in sockets", 0, 12, 1, 3),
                          ("pitch", "Peg spacing", 16, 40, 1, 24),
                          ("height", "Block height", 12, 24, 0.5, 22)],
                    derive=socket_cuts,
                    note="pegs 6.25 □ (1/4 in, back row) and 9.40 □ (3/8 in, front row), chamfered"),
}

def _blk(q):
    return f"block {q['pk_w']:g} × {q['pk_d']:g} × {q['pk_h']:g}"


NOTES = {
    "toolcheck": lambda d, q, s, g, c: {"thick": f"reach {q['ar_reach']:g}", "length": f"arms {s * c['b']['pitch_x']:.1f} apart"},
    "hexkeys": lambda d, q, s, g, c: {"pitch": _blk(q), "slot_l": "slots " + " · ".join(f"{x['w']:g}" for x in q["pk_cuts"])},
    "kraftform": lambda d, q, s, g, c: {"count": _blk(q), "dia": f"holes Ø{q['pk_cuts'][0]['w']:g}", "pitch": f"{len(q['pk_cuts'])} × {d['pitch']:g}",
                                        "sizes": "holes " + ", ".join(f"Ø{x['w']:g}" for x in q["pk_cuts"])},
    "ratchet": lambda d, q, s, g, c: {"neck": f"U {q['pk_cuts'][0]['w']:g} wide · {_blk(q)}"},
    "sockets": lambda d, q, s, g, c: {"n14": _blk(q), "pitch": f"pegs {max(d['n14'], d['n38']):g} × {d['pitch']:g}"},
}
for _k, _f in NOTES.items():
    TOOLS[_k]["notes"] = _f

install(globals(), "wera", "Wera", 2, "we_", TOOLS, __doc__)
