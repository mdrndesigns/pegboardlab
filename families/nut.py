"""
NUT - the printed nut for a threaded stud (Mount fixing "Thread"): hex
or knurled round, with the matching internal thread. Also a plain
washer. No plate; prints flat.
"""

import math

import cadquery as cq

import boards as BD
import fasteners as F
import geometry as G
from dims import D
import mounts as MT
from families._lib import sl, seg, tog

NAME = "nut"
LABEL = "Nut"
ORDER = 90
PLATE = False
ORIENT = {"default": "back", "no_supports": "back"}

PARAMS = {
    "nt_type": "hex",       # hex | knurl | wing | washer
    "nt_af": 0.0,           # across flats / outer Ø, 0 = auto (2.2 × stud)
    "nt_h": 0.0,            # height, 0 = auto (0.9 × stud)
    "nt_knurls": 12,
    "nt_wing": 24.0,        # wing span
    "nt_clear": 0.0,        # extra radial clearance on top of the material preset
}

SCHEMA = [
    seg("nt_type", "Type", [("hex", "Hex"), ("knurl", "Knurl"), ("wing", "Wing"), ("washer", "Washer")], "Nut"),
    sl("nt_af", "Across flats / Ø (0 = auto)", 0, 60, 0.5, "Nut"),
    sl("nt_h", "Height (0 = auto)", 0, 30, 0.5, "Nut"),
    sl("nt_knurls", "Knurls", 6, 36, 1, "Nut", show={"key": "nt_type", "in": ["knurl"]}),
    sl("nt_wing", "Wing span", 10, 60, 1, "Nut", show={"key": "nt_type", "in": ["wing"]}),
    sl("nt_clear", "Extra clearance", 0, 0.6, 0.05, "Nut"),
]


def build(p, ctx, plate, mp):
    b = ctx["b"]
    d = ctx["stud_d"]
    pitch = MT.ext_thread_pitch(p, d)
    clear = ctx["mat"]["thread"] + float(p["nt_clear"])
    k = p["nt_type"]
    af = float(p["nt_af"]) or round(d * 2.2 + 2, 1)
    hgt = float(p["nt_h"]) or round(d * 0.9 + 1, 1)
    if k == "washer":
        hgt = float(p["nt_h"]) or 2.0
        body = G.cyl(af / 2, 0, hgt).cut(G.cyl(d / 2 + clear + 0.2, -1, hgt + 1))
        ctx["derived"]["nut"] = f"washer Ø{af:g} × {hgt:g}, bore {d + 2 * clear + 0.4:.1f}"
        return body
    if k == "hex":
        body = G.hex_prism(af, 0, hgt, corner_r=0.0)
        body = G.try_chamfer(body, ">Z or <Z", min(1.0, hgt / 4))
    elif k == "knurl":
        n = int(p["nt_knurls"])
        body = G.cyl(af / 2, 0, hgt)
        rr = max(1.2, af * 0.07)
        for i in range(n):
            a = 2 * math.pi * i / n
            body = body.cut(G.cyl(rr, -1, hgt + 1, (af / 2) * math.cos(a), (af / 2) * math.sin(a)))
    else:
        span = float(p["nt_wing"])
        body = G.cyl(af / 2, 0, hgt)
        wing = G.box(-span / 2, span / 2, -hgt * 0.25, hgt * 0.25, 0, hgt)
        wing = G.try_fillet(wing, "|Y", hgt * 0.2)
        body = body.union(wing)
    # internal thread matching the stud
    if ctx["export"] or ctx["render_thread"]:
        groove, r_minor = G.thread_groove(d, pitch, hgt, clear)
        body = body.cut(groove)
    else:
        r_minor = F.minor_d(d, pitch) / 2 + clear + 0.02
    body = body.cut(G.cyl(r_minor, -1, hgt + 1))
    body = G.try_chamfer(body, cq.selectors.BoxSelector((-r_minor - 0.5, -r_minor - 0.5, -0.5), (r_minor + 0.5, r_minor + 0.5, 0.5)), min(0.8, pitch * 0.8))
    dd = ctx.setdefault("dims", [])
    dd.append(D((-af / 2, 0, hgt), (af / 2, 0, hgt), (0, -af / 2 - 6, 0), label=(f"{af:g} AF" if k == "hex" else f"Ø{af:g}"), key="af"))
    dd.append(D((af / 2, 0, 0), (af / 2, 0, hgt), (6, 0, 0), key="height"))
    dd.append(D((-r_minor, 0, hgt), (r_minor, 0, hgt), (0, 6, 0), kind="dia", key="bore"))
    if k == "wing":
        dd.append(D((-span / 2, 0, hgt), (span / 2, 0, hgt), (0, hgt * 0.25 + 6, 0), key="wing"))
    ctx["derived"]["nut"] = f"{k} for Ø{d:.2f} × {pitch:.2f} thread · {af:g} AF · {hgt:g} high"
    if d < 6:
        ctx["warns"].append("Printed threads under Ø6 strip easily; this nut suits the 19 mm board's studs, not the 4 mm one.")
    return body
