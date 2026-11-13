"""
Board presets for PEGBOARDLAB. All values in millimetres.

Coordinates: the board face is the XY plane at z = 0, +Y is up the
wall, the accessory lives at z > 0 and its studs reach into z < 0.
Hole (ix, iy) sits at

    x = ix * pitch_x + (iy % 2) * stagger
    y = iy * pitch_y

A square grid has stagger = 0; a 45° lattice (every other row shifted
half a pitch) has stagger = pitch_x / 2.

Dhiya's two boards, from his 1:1 Illustrator drawings (vector centres)
and the first coupon prints of 2026-10-27:

imperial_19   portrait, 19 mm chipboard, square 23.876 grid (0.94 in).
              Holes measured 7.6 (drawn 7.5). A Ø7.0 CAD stud printed
              6.8 in ABS-GF -> shrink 0.2; wants the stud sized to the
              hole, so clearance 0 + shrink 0.2 = Ø7.8 CAD. Studs 18 long.
metric_4      landscape 2100 × 530, 4 mm hardboard in a frame, 45°
              lattice. Holes measured 4.8-5.0 (drawn 4.7); Ø4.2 CAD
              printed 4.1 -> shrink 0.1. The 26.44 pattern needed +1 mm,
              so the lattice is 27.44 along a row, rows 13.72 apart,
              stagger 13.72 (square lattice of side 19.40 turned 45°).
              Studs 6.5 long.

`back` is the free depth behind the board for hooks and bolts - still
unmeasured on both, defaults to the furring-strip figure. `shrink` is
the diametral loss between CAD and print measured on that board's
coupon; `clear` is the fit wanted on top of the measured hole. The
stud the tool cuts is  hole_d - clear + shrink.
"""

BOARDS = {
    "imperial_19": dict(
        label="Imperial · 19 mm chipboard · Ø7.6 · 23.876 square",
        hole_d=7.6, t=19.0, pitch_x=23.876, pitch_y=23.876, stagger=0.0,
        back=12.0, shrink=0.2, clear=0.0, stud_len=18.0,
        material="chipboard", verified="drawing + coupon 2026-10-27",
        note="0.94 in pitch. Coupon: Ø7.0 CAD printed 6.8 in Ø7.6 holes; pitch confirmed.",
    ),
    "metric_4": dict(
        label="Metric · 4 mm hardboard · Ø4.9 · 45° lattice (13.72 rows)",
        hole_d=4.9, t=4.0, pitch_x=27.44, pitch_y=13.72, stagger=13.72,
        back=12.0, shrink=0.1, clear=0.2, stud_len=6.5,
        material="hardboard", verified="drawing + coupon 2026-10-27",
        note="Holes 4.8-5.0. Ø4.2 CAD printed 4.1. 26.44 pattern needed +1 mm -> 27.44.",
    ),
    # reference presets from the research of 2026-10-27 (unmeasured)
    "us_1in_quarter": dict(
        label="US 1 in · 1/4 in hardboard · Ø7.14 (9/32)", hole_d=7.14, t=5.5,
        pitch_x=25.4, pitch_y=25.4, stagger=0.0, back=12.7, shrink=0.15, clear=0.3, stud_len=7.0,
        material="hardboard", verified="Panel Processing spec", note="Nominal 1/4 in stock punches at 5.5 mm.",
    ),
    "us_1in_eighth": dict(
        label="US 1 in · 1/8 in hardboard · Ø4.76 (3/16)", hole_d=4.76, t=3.2,
        pitch_x=25.4, pitch_y=25.4, stagger=0.0, back=12.7, shrink=0.1, clear=0.3, stud_len=5.0,
        material="hardboard", verified="Panel Processing spec", note="",
    ),
    "jp_25_5": dict(
        label="JP/CN 25 mm · Ø5 · 5.5 mm", hole_d=5.0, t=5.5,
        pitch_x=25.0, pitch_y=25.0, stagger=0.0, back=12.0, shrink=0.1, clear=0.3, stud_len=7.0,
        material="hardboard", verified="Kato Hide / Wakai", note="Also sold Ø6 and 30 mm pitch.",
    ),
    "skadis": dict(
        label="IKEA SKÅDIS · 5 × 15 slots · 40/20 stagger (studs only)", hole_d=5.0, t=5.0,
        pitch_x=40.0, pitch_y=20.0, stagger=20.0, back=15.0, shrink=0.1, clear=0.3, stud_len=7.0,
        material="fibreboard", verified="community-measured", note="Slot modelled as its 5 mm width; studs sit in the slot.",
    ),
}

ORDER = list(BOARDS)
GEOM_KEYS = ("hole_d", "t", "pitch_x", "pitch_y", "stagger", "back", "shrink", "clear", "stud_len")


def hole_xy(b, ix, iy):
    """Centre of hole (ix, iy) in board coordinates."""
    return (ix * float(b["pitch_x"]) + (iy % 2) * float(b["stagger"]), iy * float(b["pitch_y"]))


def is_lattice(b):
    return abs(float(b["stagger"])) > 1e-6


def col_step(b):
    """Vertical distance between two holes in the same column."""
    return float(b["pitch_y"]) * (2 if is_lattice(b) else 1)


def row_step(b):
    """Horizontal distance between two holes in the same row."""
    return float(b["pitch_x"])


def stud_d(b):
    """Stud diameter the tool cuts for this board: hole - clearance + print shrink."""
    return float(b["hole_d"]) - float(b["clear"]) + float(b["shrink"])


def holes_in(b, x0, x1, y0, y1, ax=0.0, ay=0.0):
    """Lattice holes inside the rectangle, for a lattice anchored with hole
    (0,0) at (ax, ay). Returns [(x, y)] in the rectangle's frame."""
    px, py = float(b["pitch_x"]), float(b["pitch_y"])
    out = []
    iy0 = int((y0 - ay) // py) - 2
    iy1 = int((y1 - ay) // py) + 2
    ix0 = int((x0 - ax) // px) - 2
    ix1 = int((x1 - ax) // px) + 2
    for iy in range(iy0, iy1 + 1):
        for ix in range(ix0, ix1 + 1):
            x, y = hole_xy(b, ix, iy)
            x, y = x + ax, y + ay
            if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
                out.append((round(x, 4), round(y, 4)))
    return out
