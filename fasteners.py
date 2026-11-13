"""
Fastener, magnet and Gridfinity tables for PEGBOARDLAB. Millimetres.

Sources (research.md, 2026-10-27): ISO 261/273/4032/4762/10642; heat-set
inserts as sold for FDM (CNC Kitchen hole sizes); supermagnete and K&J
pull tables (direct contact on thick steel - a 0.5 mm gap halves it);
kennetek/gridfinity-rebuilt-openscad constants; Bambu ABS-GF TDS.
"""

import math

SIZES = [3, 4, 5, 6, 8]
PITCH = {3: 0.5, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25, 10: 1.5}
CLEARANCE = {3: 3.4, 4: 4.5, 5: 5.5, 6: 6.6, 8: 9.0, 10: 11.0}       # ISO 273 medium
NUT = {3: (5.5, 2.4), 4: (7.0, 3.2), 5: (8.0, 4.7), 6: (10.0, 5.2), 8: (13.0, 6.8)}   # ISO 4032 s, m
SHCS = {3: (5.5, 3.0), 4: (7.0, 4.0), 5: (8.5, 5.0), 6: (10.0, 6.0), 8: (13.0, 8.0)}  # dk, k
CSK = {3: 6.72, 4: 8.96, 5: 11.2, 6: 13.44, 8: 17.92}                                   # ISO 10642 dk, 90°
INSERTS = {3: (4.6, 5.7, 4.2), 4: (5.6, 6.4, 5.3), 5: (6.4, 8.0, 6.1), 6: (8.0, 10.0, 7.6)}  # OD, length, hole
WOOD_SCREW = {3.0: 3.4, 3.5: 3.9, 4.0: 4.5, 4.5: 5.0, 5.0: 5.5}     # screw Ø -> clearance

HEX_KEYS = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
DRILL_SET = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]
BIT_HEX = 6.35          # 1/4 in hex driver bits, across flats

MATERIALS = {
    "absgf": {"label": "ABS-GF (Bambu)", "hex": 0.25, "depth": 0.30, "hole": 0.20, "thread": 0.25, "snap": 0.20},
    "abs":   {"label": "ABS / ASA",      "hex": 0.25, "depth": 0.30, "hole": 0.20, "thread": 0.30, "snap": 0.20},
    "petg":  {"label": "PETG",           "hex": 0.30, "depth": 0.30, "hole": 0.20, "thread": 0.25, "snap": 0.25},
    "pla":   {"label": "PLA",            "hex": 0.20, "depth": 0.25, "hole": 0.15, "thread": 0.30, "snap": 0.15},
}

# neodymium discs: (Ø, t, pull kg on thick steel, grade) - supermagnete / K&J
MAGNETS = {
    "6x2":    (6.0, 2.0, 0.74, "N45"),
    "6x3":    (6.0, 3.0, 1.00, "N42"),
    "8x3":    (8.0, 3.0, 1.50, "N45"),
    "10x2":   (10.0, 2.0, 1.30, "N42"),
    "10x3":   (10.0, 3.0, 1.80, "N42"),
    "12x3":   (12.0, 3.0, 2.40, "N45"),
    "15x3":   (15.0, 3.0, 3.20, "N45"),
    "20x3":   (20.0, 3.0, 4.30, "N45"),
    "1/4x1/16": (6.35, 1.59, 0.54, "N42"),
    "1/4x1/8":  (6.35, 3.17, 1.04, "N42"),
    "3/8x1/8":  (9.52, 3.17, 2.00, "N42"),
    "1/2x1/8":  (12.7, 3.17, 2.92, "N42"),
    "custom": (None, None, None, ""),
}
MAGNET_ORDER = list(MAGNETS)

GRIDFINITY = dict(
    grid=42.0, bin=41.5, unit_h=7.0,
    socket=[(0.7, 0.7), (0.0, 1.8), (2.15, 2.15)],   # (radial, vertical) steps, bottom up: 4.65 deep
    socket_depth=4.65, corner_r=4.0, bin_corner_r=3.75,
    magnet_d=6.5, magnet_t=2.4, magnet_inset=8.0, screw_d=3.0, min_wall=0.95,
)


def across_corners(s):
    return s / math.cos(math.radians(30))


def minor_d(major, pitch):
    return major - 1.0825 * pitch


def thread_status(major, pitch):
    """Printed internal thread: 'ok' | 'warn' | 'no'."""
    if major < 4.5 or pitch < 0.7:
        return "no"
    if major < 6:
        return "warn"
    return "ok"


# socket / pan head Ø and height by M size (ISO 7380 button head, close to ISO 7045 pan): head seats
BOLT_HEAD = {3: 5.7, 4: 7.6, 5: 9.5, 6: 10.5, 8: 14.0}
BOLT_HEAD_H = {3: 1.65, 4: 2.2, 5: 2.75, 6: 3.3, 8: 4.4}
