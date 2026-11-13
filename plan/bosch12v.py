#!/usr/bin/env python3
"""
BOSCH 12V KIT - imperial board A (19 mm chipboard, Ø7.6 holes, 23.876 pitch).

One modular part, the ARM, in four reaches and two cradles, plus SHELF
plates that screw onto pairs of arms. Every arm is two-part (spine with
three studs + arm on a flange, 2 × Ø3.5 × 15 countersunk drywall screws
into the studs). No text on any print.

    python3 plan/bosch12v.py        -> plan/bosch12v/  (3MF / STL per design,
                                       contact sheet, board map, inventory)

Tool sizes: maker specs where published (cited in the summary), else
measured off the 2026-11-05 photo against the hole pitch (±5 mm).
"""
import csv
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import cadquery as cq
import geometry as G
import model as M
import build_prints as BP

OUT = os.path.join(HERE, "bosch12v")
os.makedirs(OUT, exist_ok=True)
BP.OUT = OUT
A = "imperial_19"
PITCH = 23.876

ARM = dict(family="arm", split="two", brand_src="none", mt_pattern="grid", mt_cols=1, mt_rows=3, mt_margin=7.0,
           ar_w=22.0, ar_root=20.0, ar_tip_h=12.0, ar_lip=12.0, ar_lip_t=6.0, ar_cove=3.0)
SHELF = dict(family="shelf", brand_src="none", sh_aw=22.0, sh_gap=4.0, sh_t=5.0, sh_lip_t=6.0)


def D(id_, label, n, **kw):
    base = dict(ARM if kw.get("family", "arm") == "arm" else SHELF)
    base.update(kw)
    return dict(id=id_, item=label, n=n, board=A, params=base, brand="Bosch", zone=2)


DESIGNS = [
    D("A40", "Arm · lip · reach 40", 4, ar_tip="lip", ar_reach=40),
    D("A60", "Arm · lip · reach 60", 2, ar_tip="lip", ar_reach=60),
    D("A80", "Arm · lip · reach 80", 4, ar_tip="lip", ar_reach=80),
    D("F100", "Arm · flat · reach 100", 2, ar_tip="flat", ar_reach=100),
    D("C56", "Arm · cradle Ø56", 2, ar_tip="cradle", ar_cradle_d=56, ar_lip=12),
    D("C38", "Arm · cradle Ø38", 2, ar_tip="cradle", ar_cradle_d=38, ar_lip=12),
    D("S-SAW", "Shelf · saw · on 2 × F100, 5 pitches", 1, family="shelf", sh_arms=2, sh_span=5, sh_reach=100,
      sh_tip="flat", sh_over=6, sh_side_lip=0, sh_front_lip=0, sh_notch_l=92, sh_notch_d=30),
    D("S-60", "Shelf · optional · on 2 × A60, 6 pitches", 1, family="shelf", sh_arms=2, sh_span=6, sh_reach=60,
      sh_tip="lip", sh_over=10, sh_side_lip=8),
]

# where everything goes: arm column(s) and the row of the arm's lowest stud (col 0 = left hole
# column, row 0 = top hole row). Tool box drawn on the map: (width, height above the arm top,
# depth below the arm top) in mm.  src: spec = maker data, photo = measured off the photo.
TOOLS = [
    dict(tool="Soft tool bag", model="Bosch", arm="A40", cols=(5, 8), row=3, draw=("hang", 308, 277), src="photo",
         note="hangs by its two handle straps, one over each arm; arm inner reach 34"),
    dict(tool="Drill/driver", model="GSR 120-LI", arm="A80", cols=(2, 5), row=21, draw=("pistol", 181, 70, 125), src="spec L 181 · photo H",
         note="motor housing rests on the arms, the grip hangs between them (gap 49.8 between arms)"),
    dict(tool="Angle grinder", model="GWS 12V-76", arm="A80", cols=(9, 12), row=21, draw=("pistol", 100, 70, 140), src="photo",
         note="gear head rests on the arms, body + battery hang between them; grip must pass the 49.8 gap"),
    dict(tool="Circular saw", model="GKS 12V-26", arm="F100", cols=(2, 7), row=34, draw=("box", 156, 156), src="spec 156 × 156, 1.4 kg",
         note="sits on S-SAW; the lower blade guard (26.5 cut depth) drops through the 92 × 30 front notch", shelf="S-SAW"),
    dict(tool="Accessory case", model="Bosch blue case", arm="A60", cols=(10, 16), row=34, draw=("box", 216, 81), src="photo",
         note="stands on its long edge on the arms, leaning on the flanges; inner reach 54"),
    dict(tool="Rotary tool", model="GRO 12V-35", arm="C56", cols=(3, 9), row=40, draw=("cyl", 255, 55), src="spec 255 × 55",
         note="lies across both cradles, 143 apart"),
    dict(tool="Glue pen", model="GluePen", arm="C38", cols=(3, 7), row=45, draw=("cyl", 170, 38), src="photo",
         note="barrel lies across both cradles, 95.5 apart"),
    dict(tool="Drill-bit set box", model="Bosch", arm="A40", cols=(13, 17), row=40, draw=("box", 139, 58), src="photo",
         note="stands on its long edge; thickness must be under 34"),
    dict(tool="Small bit box", model="clear box", arm="A40", cols=(12, 15), row=45, draw=("box", 116, 50), src="photo",
         note="stands on its long edge; thickness must be under 34"),
]

MEASURE = [
    "GKS 12V-26 base plate: length × width, and how far the blade plane sits in from the base's front edge (notch is 30 deep, 92 long, centred)",
    "GKS 12V-26 lower guard: length where it leaves the base (notch 92) - turn the saw so the blade faces out",
    "GSR 120-LI and GWS 12V-76: grip width just under the motor / gear head (must pass 49.8 between the arms) and housing depth (≤ 74 inside the A80 lip)",
    "GRO 12V-35 body Ø where it lies on the cradles (seat cut for Ø56, spec 55)",
    "GluePen barrel Ø (seat cut for Ø38, photo estimate)",
    "Blue accessory case thickness (≤ 54 on A60, else use A80) - drill-bit box and small box thickness (≤ 34 on A40)",
]


def assembly_shelf(shelf_id, arm_id, span, out_svg):
    """Two arms + their spines + the shelf on top, in place: line drawing for the sheet."""
    arm = next(d for d in DESIGNS if d["id"] == arm_id)
    sh = next(d for d in DESIGNS if d["id"] == shelf_id)
    p = M.merge_params({})
    M.apply_board(p, A)
    p.update(arm["params"])
    body, spec, _ = M.build(p)
    a = M.assembly(body, spec).val()
    yb = -spec["h"] / 2
    y_top = yb + float(p["ar_root"])
    zf = spec["spine_t"] + spec["t"]
    xs = [-span * PITCH / 2, span * PITCH / 2]
    parts = [a.translate(cq.Vector(x, 0, 0)) for x in xs]
    q = M.merge_params({})
    M.apply_board(q, A)
    q.update(sh["params"])
    sb, _, _ = M.build(q)
    s = sb.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 180)
    s = s.translate((0, y_top, zf + float(q["sh_gap"])))
    parts.append(s.val())
    comp = cq.Workplane("XY").newObject([cq.Compound.makeCompound(parts)])
    cq.exporters.export(comp, out_svg, opt={"projectionDir": (-1, 0.9, 1.4), "width": 720, "height": 480, "marginLeft": 30,
                                            "marginTop": 30, "showHidden": False, "strokeWidth": 0.5, "strokeColor": (0, 0, 0),
                                            "showAxes": False})
    import cairosvg
    png = out_svg[:-4] + ".png"
    cairosvg.svg2png(url=out_svg, write_to=png, output_width=720, background_color="white")
    with open(out_svg[:-4] + ".step", "w"):
        pass
    cq.exporters.export(comp, out_svg[:-4] + ".step")
    return png


# ------------------------------------------------------------------ board map (SVG, 1:4)

def board_map(path):
    S = 1 / 4.0                   # drawing scale, mm on paper per mm on the wall
    MM = 3.7795                   # px per mm in the SVG (96 dpi)
    ncols, nrows = 21, 50
    ox, oy = 18, 34               # board origin on the sheet, mm
    W, H = 297, 420
    k = S * MM

    def X(c):
        return (ox + (c * PITCH + 12) * S) * MM

    def Y(r):
        return (oy + (r * PITCH + 12) * S) * MM

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W * MM:.1f} {H * MM:.1f}">',
           '<rect width="100%" height="100%" fill="#fff"/>',
           '<style>text{font-family:"IBM Plex Sans",Helvetica,Arial,sans-serif;fill:#000}'
           '.b{font-weight:700}.m{font-family:"IBM Plex Mono",monospace}</style>']
    bw, bh = (ncols - 1) * PITCH + 24, (nrows - 1) * PITCH + 24
    out.append(f'<rect x="{ox * MM:.1f}" y="{oy * MM:.1f}" width="{bw * k:.1f}" height="{bh * k:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
    for c in range(ncols):
        for r in range(nrows):
            out.append(f'<circle cx="{X(c):.1f}" cy="{Y(r):.1f}" r="{3.8 * k:.2f}" fill="#000" opacity="0.18"/>')
    for c in range(0, ncols, 5):
        out.append(f'<text x="{X(c):.1f}" y="{(oy - 2) * MM:.1f}" font-size="8" text-anchor="middle" class="m">{c}</text>')
    for r in range(0, nrows, 5):
        out.append(f'<text x="{(ox - 2) * MM:.1f}" y="{Y(r) + 3:.1f}" font-size="8" text-anchor="end" class="m">{r}</text>')
    tag = 1
    legend = []
    for tl in TOOLS:
        c0, c1 = tl["cols"]
        r = tl["row"]
        arm_top = Y(r) + (7 - 20) * k          # flange bottom is 7 below the lowest stud; arm top 20 above that
        cx = (X(c0) + X(c1)) / 2
        # flanges (3 studs) + arms seen from the front
        for c in (c0, c1):
            out.append(f'<rect x="{X(c) - 11 * k:.1f}" y="{Y(r - 2) - 7 * k:.1f}" width="{22 * k:.1f}" height="{(2 * PITCH + 14) * k:.1f}" '
                       f'fill="#00f"/>')
        sh_t = 5 * k if tl.get("shelf") else 0
        if tl.get("shelf"):
            span = (c1 - c0) * PITCH
            out.append(f'<rect x="{cx - (span / 2 + 21) * k:.1f}" y="{arm_top - sh_t:.1f}" width="{(span + 42) * k:.1f}" height="{sh_t:.1f}" fill="#00f"/>')
        kind = tl["draw"][0]
        wdt = tl["draw"][1] * k
        if kind == "hang":
            top = arm_top + 30 * k
            ht = tl["draw"][2] * k
            out.append(f'<rect x="{cx - wdt / 2:.1f}" y="{top:.1f}" width="{wdt:.1f}" height="{ht:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
            for c in (c0, c1):
                out.append(f'<line x1="{X(c):.1f}" y1="{arm_top:.1f}" x2="{X(c):.1f}" y2="{top:.1f}" stroke="#000" stroke-width="1"/>')
            ty = top + ht / 2
        elif kind == "pistol":
            up, down = tl["draw"][2] * k, tl["draw"][3] * k
            out.append(f'<rect x="{cx - wdt / 2:.1f}" y="{arm_top - up:.1f}" width="{wdt:.1f}" height="{up:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
            gw = 46 * k
            out.append(f'<rect x="{cx - gw / 2:.1f}" y="{arm_top:.1f}" width="{gw:.1f}" height="{down:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
            ty = arm_top - up / 2
        elif kind == "cyl":
            dd = tl["draw"][2] * k
            out.append(f'<rect x="{cx - wdt / 2:.1f}" y="{arm_top - dd:.1f}" width="{wdt:.1f}" height="{dd:.1f}" rx="{dd / 2:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
            ty = arm_top - dd / 2
        else:
            ht = tl["draw"][2] * k
            out.append(f'<rect x="{cx - wdt / 2:.1f}" y="{arm_top - sh_t - ht:.1f}" width="{wdt:.1f}" height="{ht:.1f}" fill="none" stroke="#000" stroke-width="1"/>')
            ty = arm_top - sh_t - ht / 2
        out.append(f'<rect x="{cx - 7:.1f}" y="{ty - 7:.1f}" width="14" height="14" fill="#000"/>'
                   f'<text x="{cx:.1f}" y="{ty + 3.6:.1f}" font-size="10" text-anchor="middle" class="b" style="fill:#fff">{tag}</text>')
        legend.append((tag, tl))
        tag += 1
    # title + legend
    out.append(f'<text x="{ox * MM:.1f}" y="{16 * MM:.1f}" font-size="20" class="b">BOSCH 12V · BOARD A · IMPERIAL</text>')
    out.append(f'<text x="{ox * MM:.1f}" y="{24 * MM:.1f}" font-size="9">1:4 · holes Ø7.6 · pitch 23.876 (0.94 in) · columns from the left hole column, rows from the top hole row · blue = arms, flanges, shelf</text>')
    lx = (ox + bw * S + 10) * MM
    ly = oy * MM
    out.append(f'<text x="{lx:.1f}" y="{ly + 8:.1f}" font-size="11" class="b">PLACEMENT</text>')
    ly += 22
    for tg, tl in legend:
        out.append(f'<rect x="{lx:.1f}" y="{ly - 9:.1f}" width="12" height="12" fill="#000"/>'
                   f'<text x="{lx + 6:.1f}" y="{ly + 0.5:.1f}" font-size="9" text-anchor="middle" class="b" style="fill:#fff">{tg}</text>')
        out.append(f'<text x="{lx + 18:.1f}" y="{ly:.1f}" font-size="9.5" class="b">{tl["tool"]} · {tl["model"]}</text>')
        sh = f' + {tl["shelf"]}' if tl.get("shelf") else ""
        out.append(f'<text x="{lx + 18:.1f}" y="{ly + 12:.1f}" font-size="8.5" class="m" style="fill:#00f">2 × {tl["arm"]}{sh} · cols {tl["cols"][0]} + {tl["cols"][1]} · row {tl["row"]}</text>')
        ly += 34
    ly += 8
    out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" class="b">ARMS</text>')
    ly += 16
    for d in DESIGNS:
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="8.5" class="m">{d["id"]:6s} ×{d["n"]}  {d["item"].split(" · ", 1)[1]}</text>')
        ly += 12
    ly += 10
    for line in ("Row = the lowest of the arm's three studs.",
                 "Studs go in the three holes of one column;",
                 "the arm leaves the flange bottom, so its top",
                 "sits 13 mm above that stud's centre.",
                 "Free for later: columns 19-30."):
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="8.5">{line}</text>')
        ly += 11
    out.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(out))


def contact_sheet(rows, extra, path_pdf, title="BOSCH 12V KIT · ARMS + SHELVES · imperial board A", sub=None):
    from PIL import Image, ImageDraw, ImageFont
    Wp, Hp = 4961, 3508
    M_ = 120
    BLUE = (0, 0, 255)

    def font(sz, bold=False):
        f = os.path.join(ROOT, "fonts", f"IBMPlexSans-{'Bold' if bold else 'Regular'}.ttf")
        return ImageFont.truetype(f, sz)

    page = Image.new("RGB", (Wp, Hp), "white")
    d = ImageDraw.Draw(page)
    d.text((M_, M_ - 20), title, font=font(64, True), fill="black")
    d.text((M_, M_ + 60), sub or ("two-part: arm on flange (prints on its side) + spine with 3 studs (face down) · 2 × Ø3.5 × 15 csk drywall screws into the studs · "
           "shelves: Ø3.5 × 15 csk into the arm tops · ABS-GF, 0.4 TC nozzle, no supports, no text"), font=font(34), fill="black")
    d.line((M_, M_ + 120, Wp - M_, M_ + 120), fill="black", width=3)
    cols, cw = 4, (Wp - 2 * M_) // 4
    ch = 1050 if len(rows) <= 12 else 780
    for k, r in enumerate(rows):
        cx = M_ + (k % cols) * cw
        cy = M_ + 160 + (k // cols) * ch
        d.rectangle((cx, cy, cx + cw - 20, cy + ch - 20), outline="black", width=2)
        png = os.path.join(OUT, f"{r['id']}.png")
        if os.path.exists(png):
            im = Image.open(png).convert("RGB")
            tw = cw - 200
            im = im.resize((tw, int(im.height * tw / im.width)))
            page.paste(im, (cx + 90, cy + 90))
        d.rectangle((cx, cy, cx + 230, cy + 64), fill=BLUE)
        d.text((cx + 14, cy + 8), r["id"], font=font(44, True), fill="white")
        d.text((cx + 250, cy + 14), f"×{r['n']}  {r['item']}", font=font(32, True), fill="black")
        g = f"{r['holder_g']} + {r['spine_g']} g" if r.get("spine_g") else f"{r['holder_g']} g"
        d.text((cx + 20, cy + ch - 130), f"{g} · {r.get('screws') or ''}", font=font(28), fill="black")
        d.text((cx + 20, cy + ch - 90), f"bed {r['holder_bed']}" + (f" + spine {r['spine_bed']}" if r.get("spine_g") else ""), font=font(26), fill=BLUE)
    pages = [page]
    if extra:
        pg = Image.new("RGB", (Wp, Hp), "white")
        d = ImageDraw.Draw(pg)
        d.text((M_, M_ - 20), "SHELVES IN PLACE · arms + spines + plate", font=font(64, True), fill="black")
        d.line((M_, M_ + 70, Wp - M_, M_ + 70), fill="black", width=3)
        for i, (png, cap) in enumerate(extra):
            im = Image.open(png).convert("RGB")
            tw = (Wp - 3 * M_) // 2
            im = im.resize((tw, int(im.height * tw / im.width)))
            x = M_ + i * (tw + M_)
            pg.paste(im, (x, M_ + 200))
            d.text((x, M_ + 140), cap, font=font(40, True), fill="black")
        pages.append(pg)
    pages[0].save(path_pdf, save_all=True, append_images=pages[1:], resolution=300)
    for i, pg in enumerate(pages):
        pg.resize((Wp // 3, Hp // 3)).save(path_pdf[:-4] + f"_{i + 1}.png")


def main():
    rows = []
    for hd in DESIGNS:
        r = BP.build_one(hd)
        r = dict(id=hd["id"], item=hd["item"], n=hd["n"], family=hd["params"]["family"], **r)
        rows.append(r)
        print(f"{r['status']:5s} {r['id']:6s} ×{r['n']} {r['item']:40s} {r.get('holder_g', 0):6.1f} + {r.get('spine_g', 0):5.1f} g  "
              f"unsupported {r.get('unsupported')}  {r.get('warnings', '')}", flush=True)
    keys = ["id", "item", "n", "family", "status", "holder_g", "spine_g", "holder_cm3", "spine_cm3", "holder_bed", "spine_bed",
            "screws", "studs", "plate", "orient", "unsupported", "valid", "open_edges", "interference", "warnings"]
    with open(os.path.join(OUT, "inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    extra = [(assembly_shelf("S-SAW", "F100", 5, os.path.join(OUT, "S-SAW_assembly.svg")), "S-SAW on 2 × F100 · 5 pitches (119.4) · circular saw"),
             (assembly_shelf("S-60", "A60", 6, os.path.join(OUT, "S-60_assembly.svg")), "S-60 on 2 × A60 · 6 pitches (143.3) · lips = front stop")]
    contact_sheet(rows, extra, os.path.join(OUT, "bosch12v_sheet.pdf"))
    ok = [r for r in rows if r["status"] == "ok"]
    arms = sum(r["n"] for r in ok if r["family"] == "arm")
    g = sum((r["holder_g"] + r.get("spine_g", 0)) * r["n"] for r in ok)
    screws = 2 * arms + sum(int(str(r["screws"]).split(" ×")[0]) * r["n"] for r in ok if r["family"] == "shelf")
    L = [f"BOSCH 12V KIT · imperial board A · {time.strftime('%Y-%m-%d %H:%M')}",
         f"designs {len(rows)} · ok {len(ok)}",
         f"prints: {arms} arms + {arms} spines + {sum(r['n'] for r in ok if r['family'] == 'shelf')} shelves",
         f"ABS-GF ≈ {g:.0f} g (+12 % purge / brims → {1.12 * g:.0f} g)",
         f"Ø3.5 × 15 csk drywall screws: {screws}", "",
         "placement: plan/boardA (board A packed with the hand tools + Wera, 2026-11-06)"]
    L += ["", "measure before printing the pairs that depend on it:"] + [f"  - {m}" for m in MEASURE]
    L += ["", "not ok:"] + [f"  {r['id']} {r.get('reason', '')} valid={r.get('valid')} open={r.get('open_edges')}" for r in rows if r["status"] != "ok"]
    with open(os.path.join(OUT, "summary.txt"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
