#!/usr/bin/env python3
"""Contact sheet of every holder: thumbnail + id + item + mass + screws. A3 landscape pages → PDF."""
import csv
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.join(HERE, "prints")
rows = list(csv.DictReader(open(os.path.join(HERE, "prints_inventory.csv"))))
rows = [r for r in rows if r["status"] == "ok"]

W, H = 4961, 3508            # A3 landscape at 300 dpi
COLS, ROWS = 6, 4
M = 120
cw = (W - 2 * M) // COLS
ch = (H - 2 * M - 160) // ROWS
BLUE = (0, 0, 255)


def font(sz, bold=False):
    for cand in (f"/home/claude/pegboardlab/fonts/IBMPlexSans-{'Bold' if bold else 'Regular'}.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(cand):
            return ImageFont.truetype(cand, sz)
    return ImageFont.load_default()


pages = []
per = COLS * ROWS
for pi in range(0, len(rows), per):
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    d.text((M, M - 20), "PEGBOARDLAB · STUDIO HOLDERS · print inventory", font=font(64, True), fill="black")
    d.text((M, M + 60), f"sheet {pi // per + 1} of {(len(rows) + per - 1) // per} · two-part: holder (upright) + spine (face down) · Ø3.5 × 15 csk drywall screws · ABS-GF blue, 0.4 TC nozzle, 4 walls, no supports",
           font=font(34), fill="black")
    d.line((M, M + 120, W - M, M + 120), fill="black", width=3)
    for k, r in enumerate(rows[pi:pi + per]):
        cx = M + (k % COLS) * cw
        cy = M + 160 + (k // COLS) * ch
        d.rectangle((cx, cy, cx + cw - 20, cy + ch - 20), outline="black", width=2)
        png = os.path.join(PR, f"{r['id']}.png")
        if os.path.exists(png):
            im = Image.open(png).convert("RGB")
            tw = cw - 60
            im = im.resize((tw, int(im.height * tw / im.width)))
            page.paste(im, (cx + 20, cy + 70))
        d.rectangle((cx, cy, cx + 150, cy + 56), fill=BLUE)
        d.text((cx + 12, cy + 8), r["id"], font=font(36, True), fill="white")
        d.text((cx + 170, cy + 12), f"×{r['n']}  {r['item'][:30]}", font=font(32, True), fill="black")
        info = f"{r['family']} · {r['holder_g']} + {r['spine_g']} g · {r['screws'].split(' csk')[0]}"
        d.text((cx + 20, cy + ch - 100), info, font=font(28), fill="black")
        d.text((cx + 20, cy + ch - 62), f"bed {r['holder_bed']} + spine {r['spine_bed']}", font=font(26), fill=BLUE)
    pages.append(page)

pages[0].save(os.path.join(HERE, "prints_contact_sheet.pdf"), save_all=True, append_images=pages[1:], resolution=300)
for i, pg in enumerate(pages):
    pg.resize((W // 3, H // 3)).save(os.path.join(HERE, f"prints_contact_sheet_{i + 1}.png"))
print(len(rows), "holders on", len(pages), "pages")
