#!/usr/bin/env python3
"""
BOARD A - the whole imperial board: Bosch 12V + hand tools + Wera, placed
on the real hole grid (31 columns × 50 rows, pitch 23.876) by a small packer.

Each item is drawn as rectangles relative to its anchor (centre between its
arms, arm top), plus its flanges (22 × 61.8 per arm, on three holes of one
column). Items are placed in priority order (measuring and pliers nearest
the bench, drivers and Wera next, Bosch above); for each item every legal
(column, row) is tried and the cheapest position that keeps a clearance to
everything already placed and stays on the board wins. Whatever cannot be
placed is reported, never forced.

    python3 plan/boardA.py   -> plan/boardA/boardA_map.{svg,pdf,png}, placement.csv
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "boardA")
P = 23.876
NC, NR = 31, 50                 # hole columns / rows (board A, 740 × 1194)
EDGE = 12.0                     # board edge beyond the outer holes
CLEAR = 6.0                     # clearance kept between items
FL_W, FL_UP, FL_DN = 22.0, 2 * P + 7.0, 7.0      # flange: above / below the lowest stud
ARM_TOP = 13.0                  # arm top sits 13 above the lowest stud


def pair(W, up, down=0.0):            # tool resting on / hanging from two arms
    return [(-W / 2, W / 2, -up, down)]


def pistol(W, up, gw, down):          # drill / grinder: housing above the arms, grip between them
    return [(-W / 2, W / 2, -up, 0.0), (-gw / 2, gw / 2, 0.0, down)]


def rack(Wp, Wt, up, down):           # rack plate (6 + 12 back wall) + tools hanging through it
    return [(-Wp / 2, Wp / 2, -18.0, 0.0), (-Wt / 2, Wt / 2, -up, down)]


def single(W, down):                  # one narrow hook, tool hanging below it
    return [(-W / 2, W / 2, -12.0, down)]


def tools(*rs):
    return list(rs)


# id, tool, parts, span (pitches between the two arms; 0 = single hook), col (left arm), row (lowest stud),
# rects relative to (centre between the arms, arm top): x0, x1, y0 (up = negative), y1
ITEMS = [
    # ---------------------------------------------------------------- LEFT · Bosch 12V, top to bottom
    dict(id="B-GSR", tool="GSR 120-LI drill", parts="2 × A80", span=3, col=2, row=3, rects=pistol(181, 70, 46, 125)),
    dict(id="B-GWS", tool="GWS 12V-76 grinder", parts="2 × A80", span=3, col=9, row=3, rects=pistol(100, 70, 55, 140)),
    dict(id="B-SMALL", tool="Small bit box", parts="2 × A40", span=3, col=9, row=12, rects=pair(116, 50)),
    dict(id="B-GKS", tool="GKS 12V-26 saw", parts="2 × F100 + S-SAW", span=5, col=1, row=16,
         rects=[(-78, 78, -166, 0), (-76.5, 76.5, -5, 20)]),
    dict(id="B-BITS", tool="Drill-bit box", parts="2 × A40", span=4, col=8, row=16, rects=pair(139, 58)),
    dict(id="B-CASE", tool="Bosch blue case", parts="2 × A60", span=6, col=3, row=21, rects=pair(216, 81)),
    dict(id="B-GRO", tool="GRO 12V-35", parts="2 × C56", span=6, col=2, row=25, rects=pair(255, 58)),
    dict(id="B-GLUE", tool="GluePen", parts="2 × C38", span=4, col=2, row=28, rects=pair(170, 40)),
    # ---------------------------------------------------------------- LEFT · hooks + measuring, nearest the bench
    dict(id="SCISS", tool="Scissors", parts="N30", span=0, col=4, row=30, rects=single(90, 200)),
    dict(id="MICRO", tool="Micrometer 0-25", parts="N30", span=0, col=8, row=31, rects=single(80, 140)),
    dict(id="PROTR", tool="Protractor + rule", parts="N30", span=0, col=12, row=29, rects=single(80, 220)),
    dict(id="R-MEAS", tool="Caliper · tape · markers · scriber", parts="2 × F60 + R-MEAS", span=10, col=1, row=41,
         rects=[(-138.5, 138.5, -18, 0), (-104, -40, -12, 85), (-34, 6, -45, 195), (20, 100, -25, 125)]),
    # ---------------------------------------------------------------- RIGHT · Wera, drivers, pliers
    dict(id="TOOLCHK", tool="Wera Tool-Check PLUS", parts="2 × A60", span=6, col=20, row=5, rects=pair(190, 100)),
    dict(id="R-HEX", tool="Wera Hex-Plus L-keys ×9", parts="2 × F60 + R-HEX", span=8, col=20, row=8,
         rects=[(-114.5, 114.5, -18, 0), (-70, 70, -15, 224)]),
    dict(id="WRENCH", tool="Adjustable wrench 200", parts="N30", span=0, col=15, row=8, rects=single(60, 210)),
    dict(id="SPAN", tool="Spanner", parts="N30", span=0, col=18, row=8, rects=single(36, 160)),
    dict(id="R-DRV", tool="Drivers: Irwin · chisel · awl · knife + Wera ×6", parts="2 × F60 + R-DRV", span=14, col=14, row=23,
         rects=[(-186.2, 186.2, -18, 0), (-152, 152, -110, 150)]),
    dict(id="R-PLI-2", tool="Cutters / crimpers ×4 · snips · nipper", parts="2 × F60 + R-PLI", span=12, col=16, row=33,
         rects=[(-162.3, 162.3, -18, 0), (-121, 121, -60, 190)]),
    dict(id="R-PLI-1", tool="Pliers ×4 · 1 cutter · spare", parts="2 × F60 + R-PLI", span=12, col=16, row=44,
         rects=[(-162.3, 162.3, -18, 0), (-121, 121, -50, 140)]),
]

# not on board A: big / rarely used - they go to the metric boards next (same arms, metric spines)
DEFERRED = ["Bosch soft tool bag (2 × A40)", "Irwin spring clamps L ×2 + S ×2", "Japanese pull saw", "Irwin combination square 300",
            "Ratchet strap", "Acrylic rule 450", "Green cross-line laser level", "Work-light tube", "Cables / test leads"]


def absolute(it, col, row):
    """All rectangles of an item at (left arm column, lowest stud row), in board mm (x right, y down)."""
    cols = (col, col + it["span"]) if it["span"] else (col,)
    cx = (cols[0] + cols[-1]) * P / 2
    at = row * P - ARM_TOP
    rs = [(cx + a, cx + b, at + c, at + d) for a, b, c, d in it["rects"]]
    rs += [(c * P - FL_W / 2, c * P + FL_W / 2, row * P - FL_UP, row * P + FL_DN) for c in cols]
    return rs, cols, cx, at


def overlap(a, b, cl=CLEAR):
    return a[0] < b[1] + cl and b[0] < a[1] + cl and a[2] < b[3] + cl and b[2] < a[3] + cl


def inside(r):
    return r[0] >= -EDGE and r[1] <= (NC - 1) * P + EDGE and r[2] >= -EDGE and r[3] <= (NR - 1) * P + EDGE


def pack():
    """Fixed positions; every pair of items checked for clearance and every rectangle for the board edge."""
    placed, problems = [], []
    for it in ITEMS:
        rs, cols, cx, at = absolute(it, it["col"], it["row"])
        for r in rs:
            if not inside(r):
                problems.append(f"{it['id']} off the board: {tuple(round(v) for v in r)}")
        for p in placed:
            for r in rs:
                for q in p["rs"]:
                    if overlap(r, q):
                        gap = max(q[0] - r[1], r[0] - q[1], q[2] - r[3], r[2] - q[3])
                        problems.append(f"{it['id']} × {p['id']}: gap {gap:.1f}")
        placed.append(dict(it, rs=rs, cols=cols, cx=cx, at=at))
    return placed, sorted(set(problems))


def draw(placed, failed, path):
    S, MM = 1 / 4.0, 3.7795
    k = S * MM
    ox, oy = 18, 34
    W, H = 420, 297 * 2 ** 0.5           # A3 portrait would squeeze the legend; use 420 × 420 square-ish A2 strip
    W, H = 297, 420
    X = lambda x: (ox + (x + EDGE) * S) * MM
    Y = lambda y: (oy + (y + EDGE) * S) * MM
    bw, bh = (NC - 1) * P + 2 * EDGE, (NR - 1) * P + 2 * EDGE
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W * MM:.1f} {H * MM:.1f}">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<style>text{font-family:"IBM Plex Sans",Helvetica,Arial,sans-serif;fill:#000}.b{font-weight:700}'
         '.m{font-family:"IBM Plex Mono",monospace}</style>',
         f'<rect x="{X(-EDGE):.1f}" y="{Y(-EDGE):.1f}" width="{bw * k:.1f}" height="{bh * k:.1f}" fill="none" stroke="#000" stroke-width="1"/>']
    for c in range(NC):
        for r in range(NR):
            o.append(f'<circle cx="{X(c * P):.1f}" cy="{Y(r * P):.1f}" r="{3.8 * k:.2f}" fill="#000" opacity="0.16"/>')
    for c in range(0, NC, 5):
        o.append(f'<text x="{X(c * P):.1f}" y="{(oy - 2) * MM:.1f}" font-size="7" text-anchor="middle" class="m">{c}</text>')
    for r in range(0, NR, 5):
        o.append(f'<text x="{(ox - 2) * MM:.1f}" y="{Y(r * P) + 2.5:.1f}" font-size="7" text-anchor="end" class="m">{r}</text>')
    for n, p in enumerate(placed, 1):
        nr = len(p["rects"])
        for i, r in enumerate(p["rs"]):
            if i < nr:
                o.append(f'<rect x="{X(r[0]):.1f}" y="{Y(r[2]):.1f}" width="{(r[1] - r[0]) * k:.1f}" height="{(r[3] - r[2]) * k:.1f}" '
                         f'fill="none" stroke="#000" stroke-width="0.8"/>')
            else:
                o.append(f'<rect x="{X(r[0]):.1f}" y="{Y(r[2]):.1f}" width="{(r[1] - r[0]) * k:.1f}" height="{(r[3] - r[2]) * k:.1f}" fill="#00f"/>')
        if p["id"].startswith("R-") or "+ S-" in p["parts"]:      # plate on the arms
            r = p["rs"][0]
            o.append(f'<rect x="{X(r[0]):.1f}" y="{Y(p["at"] - 6):.1f}" width="{(r[1] - r[0]) * k:.1f}" height="{6 * k:.1f}" fill="#00f"/>')
        r0 = p["rs"][0]
        tx, ty = X(p["cx"]), Y((r0[2] + r0[3]) / 2)
        o.append(f'<rect x="{tx - 7:.1f}" y="{ty - 7:.1f}" width="14" height="14" fill="#000"/>'
                 f'<text x="{tx:.1f}" y="{ty + 3.4:.1f}" font-size="9" text-anchor="middle" class="b" style="fill:#fff">{n}</text>')
    o.append(f'<text x="{ox * MM:.1f}" y="{16 * MM:.1f}" font-size="18" class="b">BOARD A · IMPERIAL · BOSCH 12V + HAND TOOLS + WERA</text>')
    o.append(f'<text x="{ox * MM:.1f}" y="{23 * MM:.1f}" font-size="8">1:4 · Ø7.6 holes, pitch 23.876 · col from the left hole column, row = the arm\'s lowest stud from the top · '
             f'blue = flanges / plates · black = tool envelopes · bench below row 49</text>')
    lx, ly = X((NC - 1) * P + EDGE) + 10 * MM * 0.0 + 6, Y(-EDGE) + 4
    lx = (ox + bw * S + 4) * MM
    o.append(f'<text x="{lx:.1f}" y="{ly + 6:.1f}" font-size="9" class="b">PLACEMENT</text>')
    ly += 18
    for n, p in enumerate(placed, 1):
        cs = " + ".join(str(c) for c in p["cols"])
        o.append(f'<rect x="{lx:.1f}" y="{ly - 8:.1f}" width="10" height="10" fill="#000"/>'
                 f'<text x="{lx + 5:.1f}" y="{ly:.1f}" font-size="7.5" text-anchor="middle" class="b" style="fill:#fff">{n}</text>'
                 f'<text x="{lx + 14:.1f}" y="{ly:.1f}" font-size="7.5" class="b">{p["tool"]}</text>'
                 f'<text x="{lx + 14:.1f}" y="{ly + 9:.1f}" font-size="6.8" class="m" style="fill:#00f">{p["parts"]} · col {cs} · row {p["row"]}</text>')
        ly += 22
    ly += 8
    o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" class="b">NOT ON BOARD A</text>')
    ly += 13
    for t in DEFERRED:
        o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="7">{t}</text>')
        ly += 10
    o.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(o))


def main():
    os.makedirs(OUT, exist_ok=True)
    placed, failed = pack()
    print("\n".join(failed) or "clearances ok")
    with open(os.path.join(OUT, "placement.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "id", "tool", "parts", "columns", "row"])
        for n, p in enumerate(placed, 1):
            w.writerow([n, p["id"], p["tool"], p["parts"], " + ".join(map(str, p["cols"])), p["row"]])
    svg = os.path.join(OUT, "boardA_map.svg")
    draw(placed, failed, svg)
    import cairosvg
    cairosvg.svg2pdf(url=svg, write_to=svg[:-4] + ".pdf")
    cairosvg.svg2png(url=svg, write_to=svg[:-4] + ".png", output_width=1600, background_color="white")
    for n, p in enumerate(placed, 1):
        print(f"{n:2d} {p['id']:8s} cols {' + '.join(map(str, p['cols'])):9s} row {p['row']:2d}  {p['tool']}")



if __name__ == "__main__":
    main()
