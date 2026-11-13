#!/usr/bin/env python3
"""
PEGBOARDLAB studio layout plan v1 - 2D zoning of Dhiya's three boards.

    python3 plan/layout.py   -> plan/layout_v1.svg, .pdf, inventory_v1.csv

Boards are drawn on their real hole lattices at 1:10 on A3 landscape.
Every item is a rectangle snapped to the grid with the PEGBOARDLAB
family that will hold it. Numbers marked ? are to be measured.
"""
import csv
import os
import math

HERE = os.path.dirname(os.path.abspath(__file__))
S = 0.1                           # default 1:10 (board B); A and C at 1:7.5

# ---------------------------------------------------------------- boards (mm)
BOARDS = {
    "A": dict(name="A · IMPERIAL · chipboard 19 · 1:7.5", w=781, h=1215, px=23.876, py=23.876, st=0.0,
              ox=32.4, oy=22.5, hole=7.6, page=(14, 30), s=1 / 7.5,
              note="31 × 50 · Ø7.6 · 23.876 square · studs Ø7.8 × 18"),
    "C": dict(name="C · METRIC · portrait ? · 1:7.5", w=450, h=1850, px=27.44, py=13.72, st=13.72,
              ox=18, oy=16, hole=4.9, page=(128, 30), s=1 / 7.5,
              note="450 × 1850 ? · Ø4.9 · 27.44 / 13.72 · confirm"),
    "B": dict(name="B · METRIC · landscape 4 mm · 1:10", w=2100, h=530, px=27.44, py=13.72, st=13.72,
              ox=20, oy=20, hole=4.9, page=(200, 30), s=0.1,
              note="2100 × 530 · Ø4.9 · 27.44 / 13.72 lattice · right 700 kept for the filament boxes ?"),
}

# ---------------------------------------------------------------- accessory legend (PEGBOARDLAB families)
ACC = {
    "HS": ("Holster · saddle", "holster · hs_type=saddle"),
    "HR": ("Holster · ring", "holster · hs_type=ring"),
    "HJ": ("Hook · J", "hook · hk_type=j"),
    "HD": ("Hook · double prong", "hook · hk_type=double"),
    "HL": ("Hook · loop", "hook · hk_type=loop"),
    "HP": ("Hook · peg (rolls)", "hook · hk_type=peg"),
    "RK": ("Rack · holes / slots", "rack · rk_type=…"),
    "TR": ("Tray / bin", "tray · tr_type=…"),
    "MG": ("Magnet strip", "magstrip · mg_mode=embed"),
    "CL": ("Clip · cables", "clip · cl_type=snap"),
    "GF": ("Gridfinity shelf", "gridfinity · gf_nx × gf_ny"),
    "PL": ("Label plate", "plate · pl_w × pl_h"),
}

# ---------------------------------------------------------------- zones  (board, label, x, y, w, h in mm)
ZONES = [
    ("A", "1  CLAMPS · SQUARE · BAG", 0, 0, 680, 240),
    ("A", "2  BOSCH 12V SYSTEM", 0, 240, 290, 620),
    ("A", "3  IRWIN HAND TOOLS", 290, 240, 190, 330),
    ("A", "4  WERA · DRIVE · LEVEL", 480, 240, 200, 330),
    ("A", "6  CUT · GRIP · POWER", 290, 570, 390, 290),
    ("A", "5  MEASURE · MARK  (nearest the bench)", 0, 860, 680, 230),
    ("A", "7  BENCH BINS (existing)", 0, 1090, 680, 125),
    ("A", "CLEAR", 680, 0, 101, 1215),
    ("C", "8  KREG · GUIDES", 0, 0, 450, 420),
    ("C", "9  RULES · LAYOUT", 0, 420, 450, 420),
    ("C", "10 TAPE · ADHESIVE", 0, 840, 450, 360),
    ("C", "11 BINS (existing)", 0, 1200, 450, 300),
    ("C", "12 GRIDFINITY · SMALL PARTS", 0, 1500, 450, 350),
    ("B", "13 LONG TOOLS · SAWS · CLAMPS", 0, 0, 1400, 300),
    ("B", "14 GRIDFINITY SHELF ROW · hardware", 0, 300, 1400, 230),
    ("B", "FILAMENT BOXES (bench) ?", 1400, 0, 700, 530),
]

# ---------------------------------------------------------------- items  (board, label, brand, acc, x, y, w, h, settings, qty)
ITEMS = [
    # A · zone 1
    ("A", "Tool bag", "Bosch", "HL", 10, 10, 220, 220, "loop 30 wide, reach 40", 1),
    ("A", "End nippers", "—", "HD", 240, 10, 60, 190, "double, gap 20", 1),
    ("A", "Spring clamp L ×2", "Irwin", "HD", 310, 10, 120, 150, "double, gap 60, reach 50", 2),
    ("A", "Spring clamp S ×2", "Irwin", "HD", 440, 10, 90, 120, "double, gap 40", 2),
    ("A", "Combination square", "Irwin", "HJ", 540, 10, 80, 230, "J 25 wide, lip 10", 1),
    # zone 2 Bosch
    ("A", "GWS 12V grinder", "Bosch", "HS", 10, 250, 140, 140, "saddle 44 × 50, h 30", 1),
    ("A", "Drill bit case", "Bosch", "TR", 160, 250, 120, 140, "tray 120 × 40, h 25", 1),
    ("A", "GKS 12V circular saw", "Bosch", "HS", 10, 400, 190, 170, "saddle 50 × 60, h 35", 1),
    ("A", "Bits · small parts", "Bosch", "TR", 210, 400, 70, 170, "tray 60 × 60", 1),
    ("A", "Accessory box", "Bosch", "TR", 10, 580, 200, 110, "tray 200 × 60 lip 15", 1),
    ("A", "Glue pen", "Bosch", "HD", 220, 580, 60, 110, "double, gap 24", 1),
    ("A", "GSR 12V drill", "Bosch", "HS", 10, 700, 150, 150, "saddle 44 × 60, h 30", 1),
    ("A", "GRO 12V rotary", "Bosch", "HS", 170, 700, 110, 150, "saddle 40 × 45, h 25", 1),
    # zone 3 Irwin
    ("A", "Chisels ×3 + gouge", "Irwin", "RK", 300, 250, 110, 300, "rack chisels n=4 d=12 depth 40", 4),
    ("A", "Screwdrivers ×2", "Irwin", "RK", 420, 250, 50, 230, "rack drivers n=2 d=10", 2),
    ("A", "Marking knife", "—", "HJ", 420, 490, 50, 70, "J 20, lip 8", 1),
    # zone 4 Wera
    ("A", "Tool-Check Plus", "Wera", "TR", 490, 250, 180, 60, "tray 200 × 48 × 18", 1),
    ("A", "Ratchet", "Wera", "HJ", 490, 320, 55, 120, "J 16, lip 10", 1),
    ("A", "Hex keys ×9", "Wera", "RK", 555, 320, 115, 120, "rack hexkeys", 9),
    ("A", "Laser level", "—", "TR", 490, 450, 100, 110, "tray 112 × 112", 1),
    ("A", "Future Wera ×6", "Wera", "RK", 600, 450, 75, 110, "rack drivers n=6 d=10", 1),
    # zone 6 cut/grip (rows 24-36)
    ("A", "Pliers ×6 + crimper slot", "—", "RK", 300, 580, 260, 130, "rack chisels n=7 28 × 14", 7),
    ("A", "Work light tube", "—", "HD", 300, 720, 290, 60, "double, gap 236, reach 55", 1),
    ("A", "Aviation snips", "—", "HJ", 570, 580, 50, 130, "J 25, lip 12", 1),
    ("A", "Scissors", "—", "HJ", 630, 580, 45, 130, "J 20", 1),
    ("A", "Wrenches ×2 + spare", "—", "RK", 300, 790, 110, 60, "rack wrenches n=3 d=14", 3),
    ("A", "Multitool", "—", "TR", 420, 790, 50, 60, "cup 42 × 24 × 50", 1),
    ("A", "Spare J ×2 (knife · cutter)", "—", "HJ", 480, 790, 110, 60, "J 20 ×2", 2),
    ("A", "Spare J ×2 (quick-draw)", "—", "HJ", 600, 720, 75, 130, "J 20 ×2", 2),
    # zone 5 measure (rows 36-45, nearest the bench)
    ("A", "Rules 150 · 300", "—", "MG", 10, 870, 40, 160, "magstrip 40 × 160, 4 × Ø10×3", 2),
    ("A", "Digital caliper", "—", "HS", 60, 870, 45, 200, "saddle 18 × 26", 1),
    ("A", "Micrometer", "—", "HJ", 115, 870, 60, 90, "J 20, lip 10", 1),
    ("A", "Protractor", "—", "HJ", 185, 870, 90, 90, "J 20, lip 10", 1),
    ("A", "Scriber · feelers", "—", "RK", 115, 970, 110, 110, "rack drivers n=4 d=8", 4),
    ("A", "Tape measure", "Stanley", "HS", 285, 870, 70, 90, "saddle 46 × 78", 1),
    ("A", "Pens · markers ×8", "—", "RK", 365, 870, 110, 110, "sockets n=4 rows 2 d=18", 1),
    ("A", "Test leads · cable", "—", "CL", 485, 870, 60, 110, "clip snap n=3 d=5", 1),
    ("A", "Zone labels ×6", "mdrn", "PL", 555, 870, 120, 110, "plate 120 × 28 each", 6),
    ("A", "Spare (future measure)", "—", "HJ", 235, 970, 120, 110, "J 20 ×2", 2),
    # board C
    ("C", "Rip-Cut guide · J ×2", "Kreg", "HJ", 20, 15, 400, 50, "J 30 ×2, 400 apart", 2),
    ("C", "Pocket-hole jig", "Kreg", "TR", 25, 80, 170, 320, "bin 142 × 72 × 40", 1),
    ("C", "Clamp triangle", "Kreg", "HJ", 215, 80, 110, 110, "J 20", 1),
    ("C", "Vernier caliper", "—", "HS", 215, 200, 50, 200, "saddle 24 × 20", 1),
    ("C", "Rule 600", "—", "MG", 340, 80, 40, 330, "magstrip 30 × 300", 1),
    ("C", "Rule 1000 (alu) · J ×2", "—", "HJ", 395, 80, 40, 330, "J 35 ×2", 2),
    ("C", "Dividers", "—", "HD", 25, 440, 70, 230, "double, gap 24", 1),
    ("C", "Rule 300", "—", "MG", 120, 440, 40, 330, "magstrip 30 × 300", 1),
    ("C", "Compass · scribe", "—", "RK", 190, 440, 90, 150, "rack drivers n=3", 1),
    ("C", "Utility blades ×2", "Sky", "HJ", 300, 440, 60, 130, "J 20 (pack hole)", 2),
    ("C", "Scraper", "—", "HJ", 370, 440, 60, 130, "J 20", 1),
    ("C", "Label plates ×5", "mdrn", "PL", 190, 700, 240, 110, "plate 90 × 24", 5),
    ("C", "Masking tape ×3", "—", "HP", 25, 860, 150, 180, "peg Ø22 × 140, lip", 3),
    ("C", "Double-sided tape ×2", "—", "HP", 190, 860, 110, 110, "peg Ø22 × 90", 2),
    ("C", "Glue dots · stickers", "Bostik", "HJ", 310, 860, 60, 140, "J 20", 2),
    ("C", "Brush 100", "—", "HJ", 380, 860, 55, 200, "J 25, lip 14", 1),
    ("C", "Sanding block", "—", "TR", 190, 990, 110, 110, "tray 100 × 60", 1),
    ("C", "Blue bins ×6 (existing)", "—", "—", 25, 1215, 400, 270, "keep · or GF 2×1 ×3", 6),
    ("C", "Gridfinity 2×1", "—", "GF", 25, 1520, 200, 100, "gf 2×1 tilt 10 lip 4", 1),
    ("C", "Gridfinity 2×1", "—", "GF", 235, 1520, 200, 100, "gf 2×1 tilt 10 lip 4", 1),
    ("C", "Gridfinity 2×1", "—", "GF", 25, 1640, 200, 100, "gf 2×1 tilt 10 lip 4", 1),
    ("C", "Gridfinity 2×1", "—", "GF", 235, 1640, 200, 100, "gf 2×1 tilt 10 lip 4", 1),
    # board B
    ("B", "F-clamps ×4", "—", "HJ", 20, 20, 500, 260, "J 30 lip 20 ×4", 4),
    ("B", "Straightedge 1000", "—", "HJ", 560, 20, 1020, 60, "J 35 ×2", 2),
    ("B", "Pull saw · hand saws", "—", "HJ", 560, 100, 400, 180, "J 30 ×2, lip 14", 2),
    ("B", "Extension cord", "—", "HR", 1000, 100, 180, 180, "ring Ø140", 1),
    ("B", "Label plates ×3", "mdrn", "PL", 1220, 100, 160, 60, "plate 150 × 40", 3),
] + [("B", "Gridfinity 4×1", "—", "GF", 20 + i * 200, 320, 176, 100, "gf 4×1 magnets", 1) for i in range(7)]

BLUE = "#0000FF"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def holes_svg(b, X, Y):
    out = []
    S = b["s"]
    px, py, st = b["px"], b["py"], b["st"]
    r = b["hole"] / 2 * S
    ncols = int((b["w"] - 2 * b["ox"]) // px) + 1
    nrows = int((b["h"] - 2 * b["oy"]) // py) + 1
    for j in range(nrows):
        shift = st if (j % 2) else 0.0
        for i in range(ncols):
            x = b["ox"] + i * px + shift
            if x > b["w"] - b["ox"] + 1e-6:
                continue
            y = b["oy"] + j * py
            out.append(f'<circle cx="{X + x * S:.2f}" cy="{Y + y * S:.2f}" r="{r:.2f}"/>')
    return "\n".join(out), ncols, nrows


def snap(b, v, pitch, origin):
    return origin + round((v - origin) / pitch) * pitch


def main():
    W, H = 420, 297
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
           f'font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    # title block
    svg.append('<text x="14" y="12" font-size="5.2" font-weight="700" letter-spacing="0.8">PEGBOARDLAB · STUDIO LAYOUT PLAN v2</text>')
    svg.append('<text x="14" y="17.5" font-size="2.6" letter-spacing="0.3">Three boards on their real hole lattices · A and C at 1:7.5, B at 1:10 · A3 · 2026-11-05 · '
               'zones in blue · two-part holders (spine + holder, Ø3.5 × 15 csk drywall screws) · code = PEGBOARDLAB family · ? = to confirm</text>')
    svg.append(f'<line x1="14" y1="20" x2="{W - 14}" y2="20" stroke="#000" stroke-width="0.3"/>')
    svg.append(f'<line x1="200" y1="92" x2="{W - 14}" y2="92" stroke="#000" stroke-width="0.3"/>')

    rows = []
    # overlap check
    for key in BOARDS:
        its = [it for it in ITEMS if it[0] == key]
        for i in range(len(its)):
            for j in range(i + 1, len(its)):
                a, c = its[i], its[j]
                if a[4] < c[4] + c[6] and c[4] < a[4] + a[6] and a[5] < c[5] + c[7] and c[5] < a[5] + a[7]:
                    print("OVERLAP", key, a[1], "/", c[1])
    for key, b in BOARDS.items():
        S = b["s"]
        X, Y = b["page"]
        hs, nc, nr = holes_svg(b, X, Y)
        svg.append(f'<g id="board-{key}">')
        svg.append(f'<rect x="{X}" y="{Y}" width="{b["w"] * S:.2f}" height="{b["h"] * S:.2f}" fill="none" stroke="#000" stroke-width="0.4"/>')
        svg.append(f'<g fill="none" stroke="#000" stroke-width="0.08">{hs}</g>')
        svg.append(f'<text x="{X}" y="{Y - 6.6}" font-size="3" font-weight="700" letter-spacing="0.4">{esc(b["name"])}</text>')
        svg.append(f'<text x="{X}" y="{Y - 3.6}" font-size="1.9">{esc(b["note"])} · {nc} × {nr} holes</text>')
        # zones (outlines first; labels after the items so they float on top)
        for zb, zl, zx, zy, zw, zh in ZONES:
            if zb != key:
                continue
            clear = zl.startswith("CLEAR") or zl.startswith("FILAMENT")
            svg.append(f'<rect x="{X + zx * S:.2f}" y="{Y + zy * S:.2f}" width="{zw * S:.2f}" height="{zh * S:.2f}" fill="none" '
                       f'stroke="{BLUE}" stroke-width="{0.25 if clear else 0.5}" {"stroke-dasharray=\"1 0.8\"" if clear else ""}/>')
        # items
        for ib, lab, brand, acc, ix, iy, iw, ih, sett, qty in ITEMS:
            if ib != key:
                continue
            x0, y0 = ix, iy
            px_, py_ = X + x0 * S, Y + y0 * S
            w_, h_ = iw * S, ih * S
            existing = acc == "—"
            svg.append(f'<rect x="{px_:.2f}" y="{py_:.2f}" width="{w_:.2f}" height="{h_:.2f}" fill="#fff" fill-opacity="0.85" stroke="#000" '
                       f'stroke-width="{0.2 if existing else 0.3}" {"stroke-dasharray=\"0.8 0.6\"" if existing else ""}/>')
            # label (wrap to the box width: ~1.05 mm per char at 1.75 font)
            cpl = max(4, int(w_ / 1.05))
            words, lines, cur = lab.split(), [], ""
            for wd in words:
                if len(cur) + len(wd) + 1 > cpl and cur:
                    lines.append(cur); cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            lines.append(cur)
            ty = py_ + 2.3
            for ln in lines[:4]:
                svg.append(f'<text x="{px_ + 0.7:.2f}" y="{ty:.2f}" font-size="1.75" font-weight="700">{esc(ln)}</text>')
                ty += 2.0
            if not existing:
                svg.append(f'<text x="{px_ + w_ - 0.7:.2f}" y="{py_ + h_ - 0.8:.2f}" font-size="1.7" font-weight="700" fill="{BLUE}" text-anchor="end">{acc}</text>')
            rows.append(dict(board=key, zone=next(z[1] for z in ZONES if z[0] == key and z[2] <= ix < z[2] + z[4] and z[3] <= iy < z[3] + z[5]),
                             item=lab, brand=brand, qty=qty, accessory=ACC.get(acc, ("existing / keep", ""))[0],
                             pegboardlab=ACC.get(acc, ("", "—"))[1], settings=sett,
                             x_mm=int(x0), y_mm=int(y0), w_mm=iw, h_mm=ih,
                             holes_wide=round(iw / b["px"] + 0.5), holes_high=round(ih / b["py"] + 0.5)))
        for zb, zl, zx, zy, zw, zh in ZONES:
            if zb != key:
                continue
            tw = len(zl) * 1.25 + 2
            lx, ly = X + zx * S, Y + zy * S
            svg.append(f'<rect x="{lx:.2f}" y="{ly - 1.6:.2f}" width="{tw:.2f}" height="3.2" fill="{BLUE}"/>')
            svg.append(f'<text x="{lx + 1:.2f}" y="{ly + 0.75:.2f}" font-size="1.8" font-weight="700" fill="#fff" letter-spacing="0.25">{esc(zl)}</text>')
        svg.append('</g>')

    # legend
    LX, LY = 200, 100
    svg.append(f'<text x="{LX}" y="{LY}" font-size="3" font-weight="700" letter-spacing="0.4">ACCESSORY CODES</text>')
    y = LY + 5
    for i, (code, (lab, fam)) in enumerate(ACC.items()):
        col = i % 2
        xx = LX + col * 102
        if col == 0 and i:
            y += 4.2
        svg.append(f'<rect x="{xx}" y="{y - 2.6}" width="8" height="3.4" fill="none" stroke="#000" stroke-width="0.3"/>')
        svg.append(f'<text x="{xx + 7.3}" y="{y}" font-size="1.9" font-weight="700" fill="{BLUE}" text-anchor="end">{code}</text>')
        svg.append(f'<text x="{xx + 10}" y="{y}" font-size="1.9" font-weight="700">{esc(lab)}</text>')
        svg.append(f'<text x="{xx + 44}" y="{y}" font-size="1.7">{esc(fam)}</text>')
    # principles
    PY = y + 10
    svg.append(f'<text x="{LX}" y="{PY}" font-size="3" font-weight="700" letter-spacing="0.4">PLACEMENT RULES</text>')
    rules = [
        "Brand clusters: Bosch 12V left column of A (holsters, one grab, no tilt) · Irwin centre · Wera right · Kreg on C.",
        "Reach: measuring nearest the bench (A rows 36–45), then pliers · cutters · drivers · knives above (rows 24–36); clamps and the bag up top.",
        "Stability: two-part holders - a spine with ≥2 sized studs (Ø7.8 on A) or a J-hook + stop (C / B), the holder screwed to it with",
        "Ø3.5 × 15 countersunk drywall screws; on A the screws run on into the studs and expand them in their holes. No steel hooks remain.",
        "Quick draw: holsters and J-hooks lift straight up; racks open to the front; nothing is stacked behind anything else.",
        "Put-back: every holder carries its label plate (item name, brand) so an empty slot says what is missing.",
        "Board B: long tools and a Gridfinity shelf row for small parts; right 700 mm stays bench space while the filament lives there.",
        "To measure before printing: board C size and lattice, bench height under A (reach), fan / power-strip keep-out on A.",
    ]
    yy = PY + 4.5
    for r in rules:
        svg.append(f'<text x="{LX}" y="{yy}" font-size="1.9">{esc(r)}</text>')
        yy += 3.3
    # counts
    from collections import Counter
    cnt = Counter(r["accessory"] for r in rows)
    yy += 3
    svg.append(f'<text x="{LX}" y="{yy}" font-size="3" font-weight="700" letter-spacing="0.4">PRINT COUNT (holders)</text>')
    yy += 4.5
    for acc, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        svg.append(f'<text x="{LX}" y="{yy}" font-size="2.0"><tspan font-weight="700" fill="{BLUE}">{n:2d}</tspan>  {esc(acc)}</text>')
        yy += 3.2
    svg.append(f'<text x="{W - 14}" y="{H - 8}" font-size="2" text-anchor="end" letter-spacing="0.3">mdrndesigns · PEGBOARDLAB · plan/layout.py regenerates this sheet</text>')
    svg.append('</svg>')

    out_svg = os.path.join(HERE, "layout_v2.svg")
    open(out_svg, "w").write("\n".join(svg))
    with open(os.path.join(HERE, "inventory_v2.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    try:
        import cairosvg
        cairosvg.svg2pdf(url=out_svg, write_to=os.path.join(HERE, "layout_v2.pdf"))
        cairosvg.svg2png(url=out_svg, write_to=os.path.join(HERE, "layout_v2.png"), output_width=2800, background_color="white")
    except Exception as e:
        print("pdf/png skipped:", e)
    print(len(rows), "items,", len(ZONES), "zones")


if __name__ == "__main__":
    main()
