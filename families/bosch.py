"""
BOSCH 12V - the power-tool kit for the imperial board: each tool is held by a
PAIR of ARMs (one hole column each, three studs, two-part) spaced a whole
number of pitches apart, or by a SHELF on a pair of flat arms. The controls
are the tool's measurements; the arm reach and cradle follow from them.
Print 2 of every arm. Maker data where published, else measured off the
board photo (±5): measure before printing a pair.
"""
from families._kit import install

TOOLS = {
    "gsr": dict(label="GSR 120-LI drill", base="arm", pair=("between", "grip"),
                dims=[("depth", "Housing depth (wall to front)", 30, 160, 1, 70),
                      ("grip", "Grip width under the housing", 20, 120, 1, 46)],
                fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                derive=lambda d, s, c: dict(ar_reach=d["depth"] + 10.0),
                note="the housing rests on the two arms, the grip hangs between them; spec L 181"),
    "gws": dict(label="GWS 12V-76 grinder", base="arm", pair=("between", "grip"),
                dims=[("depth", "Head depth (wall to front)", 30, 160, 1, 70),
                      ("grip", "Body width under the head", 20, 120, 1, 55)],
                fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                derive=lambda d, s, c: dict(ar_reach=d["depth"] + 10.0),
                note="the gear head rests on the arms, body and battery hang between them"),
    "gks_shelf": dict(label="GKS 12V-26 saw · shelf", base="shelf", pair=("across", "base_w"),
                      dims=[("base_w", "Base plate along the wall", 80, 300, 1, 156),
                            ("reach", "Arm reach (flat arms under it)", 40, 200, 1, 100),
                            ("guard_l", "Blade-guard notch length", 0, 200, 1, 92),
                            ("guard_d", "Blade-guard notch depth", 5, 120, 1, 30)],
                      fixed=dict(sh_arms=2, sh_tip="flat", sh_aw=22.0, sh_gap=4.0, sh_t=5.0, sh_side_lip=0.0, sh_front_lip=0.0,
                                 sh_back_lip=0.0, sh_notch_x=0.0, sh_r=3.0, sh_cuts=[]),
                      derive=lambda d, s, c: dict(sh_span=s, sh_reach=d["reach"],
                                                  sh_over=max(0.0, (d["base_w"] - 2.0 - (s * c["b"]["pitch_x"] + 22.0)) / 2),
                                                  sh_notch_l=d["guard_l"], sh_notch_d=d["guard_d"]),
                      note="spec 156 × 156, 1.4 kg; the lower blade guard drops through the front notch - measure the blade's inset"),
    "gks_arm": dict(label="GKS 12V-26 saw · flat arm", base="arm", pair=("across", "base_w"),
                    dims=[("base_w", "Base plate along the wall", 80, 300, 1, 156),
                          ("reach", "Reach", 40, 200, 1, 100)],
                    fixed=dict(ar_tip="flat", ar_w=22.0, ar_pilots=True),
                    derive=lambda d, s, c: dict(ar_reach=d["reach"]),
                    note="the flat arms under the saw shelf; shelf pilots on top"),
    "case": dict(label="Blue accessory case", base="arm", pair=("across", "length"),
                 dims=[("thick", "Case thickness (standing on its edge)", 15, 120, 1, 54),
                       ("length", "Case length along the wall", 60, 400, 1, 216)],
                 fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                 derive=lambda d, s, c: dict(ar_reach=d["thick"] + 6.0),
                 note="stands on its long edge on the arms, leaning on the bars"),
    "gro": dict(label="GRO 12V-35 rotary tool", base="arm", pair=("across", "body_l"),
                dims=[("dia", "Body Ø where it lies", 15, 90, 0.5, 55),
                      ("body_l", "Length of that body section", 40, 300, 1, 150)],
                fixed=dict(ar_tip="cradle", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                derive=lambda d, s, c: dict(ar_cradle_d=d["dia"] + 1.0),
                note="lies across two cradles; spec 255 × 55 overall"),
    "gluepen": dict(label="GluePen", base="arm", pair=("across", "body_l"),
                    dims=[("dia", "Barrel Ø", 15, 90, 0.5, 37),
                          ("body_l", "Barrel length", 40, 300, 1, 120)],
                    fixed=dict(ar_tip="cradle", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                    derive=lambda d, s, c: dict(ar_cradle_d=d["dia"] + 1.0),
                    note="lies across two cradles; Ø and length off the photo - measure"),
    "bitbox": dict(label="Drill-bit set box", base="arm", pair=("across", "length"),
                   dims=[("thick", "Box thickness (standing on its edge)", 10, 100, 1, 30),
                         ("length", "Box length along the wall", 40, 300, 1, 139)],
                   fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                   derive=lambda d, s, c: dict(ar_reach=d["thick"] + 10.0),
                   note="stands on its long edge between the lips and the bars"),
    "smallbox": dict(label="Small bit box", base="arm", pair=("across", "length"),
                     dims=[("thick", "Box thickness", 10, 100, 1, 30),
                           ("length", "Box length along the wall", 40, 300, 1, 116)],
                     fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                     derive=lambda d, s, c: dict(ar_reach=d["thick"] + 10.0),
                     note="stands on its long edge between the lips and the bars"),
    "bag": dict(label="Soft tool bag", base="arm", pair=("across", "straps"),
                dims=[("reach", "Arm reach", 25, 120, 1, 40),
                      ("straps", "Handle-strap spacing", 40, 400, 1, 95)],
                fixed=dict(ar_tip="lip", ar_w=22.0, ar_lip=12.0, ar_lip_t=6.0),
                derive=lambda d, s, c: dict(ar_reach=d["reach"]),
                note="hangs by its two handle straps, one over each arm"),
}

NOTES = {
    "gsr": lambda d, q, s, g, c: {"depth": f"reach {q['ar_reach']:g}", "grip": f"{g:.1f} between the arms"},
    "gws": lambda d, q, s, g, c: {"depth": f"reach {q['ar_reach']:g}", "grip": f"{g:.1f} between the arms"},
    "gks_shelf": lambda d, q, s, g, c: {"base_w": f"shelf {s * c['b']['pitch_x'] + 22 + 2 * q['sh_over']:.1f} wide",
                                       "reach": f"shelf {d['reach'] - q['sh_gap']:g} deep", "guard_l": f"notch {d['guard_l']:g} × {d['guard_d']:g}"},
    "gks_arm": lambda d, q, s, g, c: {"reach": f"arm {q['ar_reach']:g} long"},
    "case": lambda d, q, s, g, c: {"thick": f"reach {q['ar_reach']:g}", "length": f"arms {s * c['b']['pitch_x']:.1f} apart"},
    "gro": lambda d, q, s, g, c: {"dia": f"cradle Ø{q['ar_cradle_d']:g}", "body_l": f"cradles {s * c['b']['pitch_x']:.1f} apart"},
    "gluepen": lambda d, q, s, g, c: {"dia": f"cradle Ø{q['ar_cradle_d']:g}", "body_l": f"cradles {s * c['b']['pitch_x']:.1f} apart"},
    "bitbox": lambda d, q, s, g, c: {"thick": f"reach {q['ar_reach']:g}", "length": f"arms {s * c['b']['pitch_x']:.1f} apart"},
    "smallbox": lambda d, q, s, g, c: {"thick": f"reach {q['ar_reach']:g}", "length": f"arms {s * c['b']['pitch_x']:.1f} apart"},
    "bag": lambda d, q, s, g, c: {"straps": f"arms {s * c['b']['pitch_x']:.1f} apart"},
}
for _k, _f in NOTES.items():
    TOOLS[_k]["notes"] = _f

install(globals(), "bosch", "Bosch 12V", 1, "bo_", TOOLS, __doc__)
