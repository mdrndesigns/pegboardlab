"""
Branding for PEGBOARDLAB (shared with SLOTLAB): text in a bundled font, or an uploaded SVG, made
into a flat solid that a part recesses, embosses or cuts through.

    artwork(p, avail_w, avail_h, mirror)  -> (compound | None, info, warnings)
    apply(body, art, z_face, outward, mode, depth)

Fonts live in ./fonts (IBM Plex, SIL Open Font License). SVG files are
parsed here with the standard library only: <path>, <rect>, <circle>,
<ellipse>, <polygon>, <polyline>, groups and transforms. Curves are
flattened; fills follow the even-odd rule (a shape inside a shape is a
hole). Strokes, text and images in the SVG are ignored - convert them to
outlines in the drawing program first.
"""

import hashlib
import math
import os
import re
import xml.etree.ElementTree as ET

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
FONTS = {
    "sans":  {"label": "Sans · IBM Plex Sans",   "regular": "IBMPlexSans-Regular.ttf",  "bold": "IBMPlexSans-Bold.ttf"},
    "serif": {"label": "Serif · IBM Plex Serif", "regular": "IBMPlexSerif-Regular.ttf", "bold": "IBMPlexSerif-Bold.ttf"},
    "mono":  {"label": "Mono · IBM Plex Mono",   "regular": "IBMPlexMono-Regular.ttf",  "bold": "IBMPlexMono-Bold.ttf"},
}
SVG_STORE = {}          # key -> svg text (uploads; exports carry the file beside the script)
SVG_MAX = 2_000_000     # bytes


# ---------------------------------------------------------------------
# fonts
# ---------------------------------------------------------------------

def font_path(key, bold=False):
    f = FONTS.get(key) or FONTS["sans"]
    name = f["bold"] if bold else f["regular"]
    path = os.path.join(FONT_DIR, name)
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, f["regular"])
    return path if os.path.exists(path) else None


def available_fonts():
    return {k: v["label"] for k, v in FONTS.items() if os.path.exists(os.path.join(FONT_DIR, v["regular"]))}


# ---------------------------------------------------------------------
# svg -> polygons (svg user units, y down)
# ---------------------------------------------------------------------

_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_TOK = re.compile(r"[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _mat_mul(a, b):
    """2D affine (a b c d e f) composition: a then b applied as a∘b (b after a)."""
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (a0 * b0 + a2 * b1, a1 * b0 + a3 * b1,
            a0 * b2 + a2 * b3, a1 * b2 + a3 * b3,
            a0 * b4 + a2 * b5 + a4, a1 * b4 + a3 * b5 + a5)


def _apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _parse_transform(s):
    m = (1, 0, 0, 1, 0, 0)
    if not s:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s):
        v = [float(x) for x in _NUM.findall(args)]
        if name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            r = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) > 2:
                t = _mat_mul(_mat_mul((1, 0, 0, 1, -v[1], -v[2]), r), (1, 0, 0, 1, v[1], v[2]))
            else:
                t = r
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = _mat_mul(t, m)
    return m


def _bezier(p0, p1, p2, p3, n):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def _quad(p0, p1, p2, n):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def _arc(p0, rx, ry, phi, large, sweep, p1, n):
    """SVG elliptical arc, endpoint parameterisation -> points (excluding p0)."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    phi = math.radians(phi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1 = cp * dx + sp * dy
    y1 = -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = (x1 / rx) ** 2 + (y1 / ry) ** 2
    if lam > 1:
        rx *= math.sqrt(lam)
        ry *= math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        k = -k
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx = cp * cx1 - sp * cy1 + (p0[0] + p1[0]) / 2
    cy = sp * cx1 + cp * cy1 + (p0[1] + p1[1]) / 2

    def ang(ux, uy, vx, vy):
        d = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return d
    t0 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    out = []
    for i in range(1, n + 1):
        t = t0 + dt * i / n
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        out.append((cp * ex - sp * ey + cx, sp * ex + cp * ey + cy))
    return out


def _path_polys(d, m, seg_n=12):
    toks = _TOK.findall(d)
    polys, cur = [], []
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    last_c = last_q = None

    def flush():
        nonlocal cur
        if len(cur) >= 3:
            polys.append(cur)
        cur = []

    def nums(k):
        nonlocal i
        v = [float(t) for t in toks[i:i + k]]
        i += k
        return v

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                flush()
                x, y = sx, sy
                cur = []
                continue
        if cmd is None:
            i += 1
            continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            px, py = nums(2)
            if rel:
                px, py = x + px, y + py
            flush()
            x, y = px, py
            sx, sy = x, y
            cur = [_apply(m, x, y)]
            cmd = "l" if rel else "L"
            last_c = last_q = None
        elif c == "L":
            px, py = nums(2)
            if rel:
                px, py = x + px, y + py
            x, y = px, py
            cur.append(_apply(m, x, y))
            last_c = last_q = None
        elif c == "H":
            (px,) = nums(1)
            x = x + px if rel else px
            cur.append(_apply(m, x, y))
            last_c = last_q = None
        elif c == "V":
            (py,) = nums(1)
            y = y + py if rel else py
            cur.append(_apply(m, x, y))
            last_c = last_q = None
        elif c in "CS":
            if c == "C":
                x1, y1, x2, y2, px, py = nums(6)
                if rel:
                    x1, y1, x2, y2, px, py = x + x1, y + y1, x + x2, y + y2, x + px, y + py
            else:
                x2, y2, px, py = nums(4)
                if rel:
                    x2, y2, px, py = x + x2, y + y2, x + px, y + py
                x1, y1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
            pts = _bezier((x, y), (x1, y1), (x2, y2), (px, py), seg_n)
            cur += [_apply(m, *q) for q in pts]
            last_c = (x2, y2)
            last_q = None
            x, y = px, py
        elif c in "QT":
            if c == "Q":
                x1, y1, px, py = nums(4)
                if rel:
                    x1, y1, px, py = x + x1, y + y1, x + px, y + py
            else:
                px, py = nums(2)
                if rel:
                    px, py = x + px, y + py
                x1, y1 = (2 * x - last_q[0], 2 * y - last_q[1]) if last_q else (x, y)
            pts = _quad((x, y), (x1, y1), (px, py), seg_n)
            cur += [_apply(m, *q) for q in pts]
            last_q = (x1, y1)
            last_c = None
            x, y = px, py
        elif c == "A":
            rx, ry, phi, large, sweep, px, py = nums(7)
            if rel:
                px, py = x + px, y + py
            pts = _arc((x, y), rx, ry, phi, bool(large), bool(sweep), (px, py), seg_n * 2)
            cur += [_apply(m, *q) for q in pts]
            last_c = last_q = None
            x, y = px, py
        else:
            i += 1
    flush()
    return polys


def _shape_polys(el, m):
    tag = el.tag.split("}")[-1]
    g = lambda k, d=0.0: float(el.get(k, d) or d)
    if tag == "path":
        return _path_polys(el.get("d", ""), m)
    if tag == "rect":
        x, y, w, h = g("x"), g("y"), g("width"), g("height")
        rx, ry = g("rx"), g("ry")
        if rx and not ry:
            ry = rx
        if ry and not rx:
            rx = ry
        if rx > 0:
            rx, ry = min(rx, w / 2), min(ry, h / 2)
            d = (f"M{x + rx},{y} H{x + w - rx} A{rx},{ry} 0 0 1 {x + w},{y + ry} V{y + h - ry} "
                 f"A{rx},{ry} 0 0 1 {x + w - rx},{y + h} H{x + rx} A{rx},{ry} 0 0 1 {x},{y + h - ry} "
                 f"V{y + ry} A{rx},{ry} 0 0 1 {x + rx},{y} Z")
            return _path_polys(d, m)
        return [[_apply(m, *q) for q in [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]]
    if tag in ("circle", "ellipse"):
        cx, cy = g("cx"), g("cy")
        rx = g("r") if tag == "circle" else g("rx")
        ry = g("r") if tag == "circle" else g("ry")
        n = 48
        return [[_apply(m, cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                 for i in range(n)]]
    if tag in ("polygon", "polyline"):
        v = [float(t) for t in _NUM.findall(el.get("points", ""))]
        pts = [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
        return [[_apply(m, *q) for q in pts]] if len(pts) >= 3 else []
    return []


WHITE = {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgb(255, 255, 255)"}


def parse_svg(text):
    """Filled shapes of an SVG as [(polygons, knockout)], one entry per
    element, polygons as lists of (x, y) in user units, y down. A white
    fill is a knockout (it removes what lies under it); every other fill
    adds. Even-odd applies inside one element."""
    root = ET.fromstring(text)
    polys = []

    def walk(el, m):
        tag = el.tag.split("}")[-1]
        if tag in ("defs", "clipPath", "mask", "symbol", "metadata", "style", "title", "desc"):
            return
        if el.get("display", "") == "none" or "display:none" in el.get("style", "").replace(" ", ""):
            return
        mm = _mat_mul(_parse_transform(el.get("transform")), m)
        if tag == "svg":
            vb = el.get("viewBox")
            w, h = el.get("width"), el.get("height")
            if vb and w and h:
                try:
                    vx, vy, vw, vh = [float(t) for t in _NUM.findall(vb)[:4]]
                    pw, ph = float(_NUM.findall(w)[0]), float(_NUM.findall(h)[0])
                    if vw > 0 and vh > 0:
                        sc = min(pw / vw, ph / vh)
                        mm = _mat_mul((sc, 0, 0, sc, -vx * sc, -vy * sc), mm)
                except (ValueError, IndexError):
                    pass
        fill = (el.get("fill") or "").strip().lower()
        style = el.get("style", "").replace(" ", "").lower()
        mf = re.search(r"fill:([^;]+)", style)
        if mf:
            fill = mf.group(1)
        if fill != "none":
            shp = [q for q in (_clean(poly) for poly in _shape_polys(el, mm)) if q is not None]
            if shp:
                polys.append((shp, fill in WHITE))
        for ch in el:
            walk(ch, mm)
    walk(root, (1, 0, 0, 1, 0, 0))
    return polys


def flat_polys(elements):
    return [q for shp, _ in elements for q in shp]


def _clean(poly, eps=1e-6):
    out = []
    for q in poly:
        if not out or abs(q[0] - out[-1][0]) > eps or abs(q[1] - out[-1][1]) > eps:
            out.append(q)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) <= eps and abs(out[0][1] - out[-1][1]) <= eps:
        out.pop()
    if len(out) < 3 or abs(_area(out)) < 1e-9:
        return None
    return out


def _area(poly):
    a = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        a += x0 * y1 - x1 * y0
    return a / 2


def _inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if xi > x:
                c = not c
    return c


def _nest(polys):
    """Even-odd nesting: returns [(outer, [holes])]. Each polygon's depth is
    the number of other polygons containing it; even depth = solid."""
    n = len(polys)
    depth = [0] * n
    parent = [None] * n
    areas = [abs(_area(p)) for p in polys]
    for i in range(n):
        best = None
        for j in range(n):
            if i == j or areas[j] <= areas[i]:
                continue
            if _inside(polys[i][0], polys[j]):
                depth[i] += 1
                if best is None or areas[j] < areas[best]:
                    best = j
        parent[i] = best
    out = []
    idx = {}
    for i in range(n):
        if depth[i] % 2 == 0:
            idx[i] = len(out)
            out.append((polys[i], []))
    for i in range(n):
        if depth[i] % 2 == 1 and parent[i] is not None and parent[i] in idx:
            out[idx[parent[i]]][1].append(polys[i])
    return out


try:
    from shapely.geometry import Polygon as _SPoly, MultiPolygon as _SMulti
    HAVE_SHAPELY = True
except Exception:                      # shapely is optional: it repairs messy outlines
    HAVE_SHAPELY = False


def _groups(elements):
    """[(outer, [holes])]. With shapely: each element is the even-odd
    combination of its outlines, elements then add (or knock out when
    white), and the result is cleaned of slivers. Without it: nesting by
    containment over all outlines."""
    if HAVE_SHAPELY:
        acc = None
        for shp, knock in elements:
            region = None
            for q in shp:
                try:
                    sp = _SPoly(q).buffer(0)
                except Exception:
                    continue
                if sp.is_empty:
                    continue
                region = sp if region is None else region.symmetric_difference(sp)
            if region is None or region.is_empty:
                continue
            if acc is None:
                acc = region if not knock else None
            else:
                acc = acc.difference(region) if knock else acc.union(region)
        if acc is None or acc.is_empty:
            return []
        acc = acc.buffer(0).simplify(0.01)
        parts = list(acc.geoms) if isinstance(acc, _SMulti) else [acc]
        out = []
        for part in parts:
            if part.is_empty or part.area < 0.2:
                continue
            outer = list(part.exterior.coords)[:-1]
            holes = [list(r.coords)[:-1] for r in part.interiors if abs(_area(list(r.coords)[:-1])) > 0.2]
            if len(outer) >= 3:
                out.append((outer, [h for h in holes if len(h) >= 3]))
        return out
    return _nest(flat_polys(elements))


def svg_solid(elements, height):
    """Extrude the shapes (already in mm, y up) into one compound, z in [0, height]."""
    solids = []
    for outer, holes in _groups(elements):
        try:
            ow = cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in outer], close=True)
            hw = [cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in h], close=True) for h in holes]
            face = cq.Face.makeFromWires(ow, hw)
            sol = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, height))
            if sol.isValid():
                solids.append(sol)
        except Exception:
            continue
    if not solids:
        return None
    return cq.Compound.makeCompound(solids)


def svg_key(text):
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:12]


def store_svg(text):
    """Parse, validate and keep an uploaded SVG. Returns (key, info)."""
    if len(text) > SVG_MAX:
        raise ValueError("SVG over 2 MB.")
    elements = parse_svg(text)
    polys = flat_polys(elements)
    if not polys:
        raise ValueError("No filled outlines found in the SVG (convert strokes and text to paths).")
    key = svg_key(text)
    SVG_STORE[key] = text
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return key, {"paths": len(polys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)}


def _svg_text(key):
    if key in SVG_STORE:
        return SVG_STORE[key]
    if key and os.path.exists(key):
        with open(key, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return None


# ---------------------------------------------------------------------
# artwork
# ---------------------------------------------------------------------

def _bbox(shape):
    bb = shape.BoundingBox()
    return bb.xmin, bb.xmax, bb.ymin, bb.ymax


def _font_cmap(fp):
    """Code points the font can draw, or None when fontTools is not installed."""
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return None
    if fp not in _CMAP:
        try:
            _CMAP[fp] = set(TTFont(fp).getBestCmap().keys())
        except Exception:
            _CMAP[fp] = None
    return _CMAP[fp]


_CMAP = {}
DROPPED = []    # characters the last text_solid call could not draw (for warnings)


def text_solid(txt, size, height, font="sans", bold=False, line=1.2):
    fp = font_path(font, bold)
    if fp is None:
        raise ValueError("Font files missing from ./fonts.")
    DROPPED.clear()
    cmap = _font_cmap(fp)
    if cmap is not None:
        # a character the font lacks would come out as an empty box: drop it and say so
        keep = []
        for c in txt:
            if c in "\n\r" or c.isspace() or ord(c) in cmap:
                keep.append(c)
            elif c not in DROPPED:
                DROPPED.append(c)
        txt = "".join(keep)
    lines = [ln for ln in txt.replace("\r", "").split("\n")]
    lines = [ln if ln.strip() else " " for ln in lines]
    if not any(ln.strip() for ln in lines):
        return None
    lh = size * line
    solids = []
    n = len(lines)
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        y = ((n - 1) / 2 - i) * lh
        w = cq.Workplane("XY").text(ln, size, height, fontPath=fp, halign="center", valign="center")
        solids += [s.translate(cq.Vector(0, y, 0)) for s in w.solids().vals()]
    if not solids:
        return None
    return cq.Compound.makeCompound(solids)


def art_height(mode, depth, thick):
    """Solid height to build for a mode: the cut/emboss depth plus overlap."""
    if mode == "through":
        return thick + 1.3
    if mode == "emboss":
        return depth + 0.5
    return depth + 1.0


def artwork(p, avail_w, avail_h, mirror=False, prefix="brand_", height=None):
    """
    Flat artwork compound lying in z [0, height], centred on the origin and
    reading correctly from +Z (mirror=True flips it for a face seen from
    -Z). Returns (compound | None, info, warnings).
    """
    g = lambda k: p[prefix + k]
    src = g("src")
    warns = []
    info = {"src": src}
    if src not in ("text", "svg"):
        return None, info, warns
    depth = max(0.1, float(g("depth"))) if height is None else height
    size = float(g("size"))
    margin = 0.08
    max_w, max_h = avail_w * (1 - 2 * margin), avail_h * (1 - 2 * margin)
    if max_w < 2 or max_h < 2:
        warns.append("No room for branding on this face.")
        return None, info, warns
    if src == "text":
        txt = str(g("text")).strip("\n")
        if not txt.strip():
            warns.append("Branding text is empty.")
            return None, info, warns
        base = size if size > 0 else 10.0
        art = text_solid(txt, base, depth, g("font"), bool(g("bold")), float(g("line")))
        if DROPPED:
            warns.append("Not in this font, dropped: " + " ".join(DROPPED) + ". Use an SVG for symbols and emoji.")
        if art is None:
            warns.append("Nothing left to render after dropping unsupported characters.")
            return None, info, warns
    else:
        svg = _svg_text(str(g("svg")))
        if not svg:
            warns.append("No SVG loaded: upload one in the Branding group.")
            return None, info, warns
        elements = parse_svg(svg)
        polys = flat_polys(elements)
        if not polys:
            warns.append("The SVG has no filled outlines.")
            return None, info, warns
        xs = [x for q in polys for x, _ in q]
        ys = [y for q in polys for _, y in q]
        w0, h0 = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        target = size if size > 0 else max(max_w, max_h)
        sc = target / max(w0, h0, 1e-9)
        elements = [([[((x - cx) * sc, -(y - cy) * sc) for x, y in q] for q in shp], knock)
                    for shp, knock in elements]                                      # y up, centred, mm
        art = svg_solid(elements, depth)
        if art is None:
            warns.append("The SVG outlines could not be made into faces.")
            return None, info, warns
        info["paths"] = len(polys)
    # rotate, then fit into the available rectangle (auto size, or clip an explicit one)
    rot = float(g("rot"))
    if abs(rot) > 1e-6:
        art = art.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
    x0, x1, y0, y1 = _bbox(art)
    art = art.translate(cq.Vector(-(x0 + x1) / 2, -(y0 + y1) / 2, 0))
    w, h = x1 - x0, y1 - y0
    f = min(max_w / max(w, 1e-9), max_h / max(h, 1e-9))
    if size <= 0 or f < 1:
        if size > 0 and f < 1:
            warns.append(f"Branding scaled to {f * 100:.0f}% to fit the face.")
        # uniform XY scale only: keep the solid height
        art = art.transformGeometry(cq.Matrix([[f, 0, 0, 0], [0, f, 0, 0], [0, 0, 1, 0]]))
        w, h = w * f, h * f
    if mirror:
        art = art.mirror("YZ")
    art = art.translate(cq.Vector(float(g("x")), float(g("y")), 0))
    info.update(w=round(w, 1), h=round(h, 1))
    return art, info, warns


def place(art, z_face, outward, mode, depth, thick):
    """The artwork (built with art_height) moved onto the face plane z = z_face
    whose outward normal is +Z (outward = 1) or -Z (outward = -1)."""
    if mode == "emboss":
        z0 = z_face - 0.5 if outward > 0 else z_face - depth
    else:
        pad_in = 0.3 if mode == "through" else 0.0
        d = thick if mode == "through" else depth
        z0 = z_face - d - pad_in if outward > 0 else z_face - 1.0
    return art.translate(cq.Vector(0, 0, z0))


def apply(body, art, z_face, outward, mode, depth, thick):
    """Recess / emboss / cut the artwork into `body` on the face z = z_face.
    mode: recess | emboss | through."""
    if art is None:
        return body
    placed = cq.Workplane("XY").add(place(art, z_face, outward, mode, depth, thick))
    if mode == "emboss":
        return body.union(placed)
    return body.cut(placed)
