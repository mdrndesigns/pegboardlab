"""
Geometry helpers for PEGBOARDLAB: primitives, teardrop studs, printed
threads, meshing (STL / 3MF), the overhang audit and the print layout.

Board coordinates everywhere: board face z = 0, +Y up the wall, part at
z > 0, studs at z < 0. Print coordinates: bed at z = 0, +Z up.
"""

import math
import struct

import cadquery as cq

import fasteners as F


# ---------------------------------------------------------------- primitives

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def rbox(x0, x1, y0, y1, z0, z1, r):
    """Box with rounded vertical (Z) edges."""
    b = box(x0, x1, y0, y1, z0, z1)
    if r > 0.05:
        try:
            b = b.edges("|Z").fillet(min(r, (x1 - x0) / 2 - 0.05, (y1 - y0) / 2 - 0.05))
        except Exception:
            pass
    return b


def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((x, y, z0))


def hex_prism(af, z0, z1, x=0.0, y=0.0, corner_r=0.3):
    d = F.across_corners(af)
    h = cq.Workplane("XY").polygon(6, d).extrude(z1 - z0).translate((x, y, z0))
    if corner_r > 0:
        try:
            h = h.edges("|Z").fillet(corner_r)
        except Exception:
            pass
    return h


def rotx(o, deg):
    return o.rotate((0, 0, 0), (1, 0, 0), deg)


def roty(o, deg):
    return o.rotate((0, 0, 0), (0, 1, 0), deg)


def rotz(o, deg):
    return o.rotate((0, 0, 0), (0, 0, 1), deg)


def union_all(objs):
    out = objs[0]
    for o in objs[1:]:
        out = out.union(o)
    return out


def cut_all(obj, cutters):
    for c in cutters:
        obj = obj.cut(c)
    return obj


def try_fillet(obj, selector, r):
    try:
        out = obj.edges(selector).fillet(r)
        v = out.val()
        if not v.isValid() or v.Volume() < 0.5 * obj.val().Volume():
            return obj
        return out
    except Exception:
        return obj


def try_chamfer(obj, selector, s):
    try:
        out = obj.edges(selector).chamfer(s)
        v = out.val()
        if not v.isValid() or v.Volume() < 0.5 * obj.val().Volume():
            return obj
        return out
    except Exception:
        return obj


def wedge(w, run, rise, x0=0.0, up=False):
    """
    Right-triangle gusset in the YZ plane with its right angle at the
    origin: one leg `run` out along +Z (the shelf), one leg `rise` along
    the plate face, down (-Y) for a gusset under a shelf or up (+Y) for a
    web above an arm. Extruded over the width w centred on x0.
    """
    sy = 1.0 if up else -1.0
    prof = cq.Workplane("YZ").polyline([(0, 0), (sy * rise, 0), (0, run)]).close().extrude(w / 2, both=True)
    return prof.translate((x0, 0, 0))


# ---------------------------------------------------------------- teardrop sections

def teardrop_wire(r, down, flat=0.0):
    """
    Teardrop profile of a Ø2r stud that prints support-free with its
    axis horizontal: the upper half stays round, the half facing `down`
    is a 45° V with the apex on the circle. `down` is the direction in
    the section plane (unit 2-vector). `flat` > 0 clips the apex to a
    flat of that width (bridges, keeps the tip from being sharp).
    Returned as a list of points in the section plane (x, y).
    """
    dx, dy = down
    # local frame: u = across, v = up (opposite of down)
    ux, uy = -dy, dx
    vx, vy = -dx, -dy
    pts = []
    n = 24
    for i in range(n + 1):                       # upper semicircle from (+u) over the top to (-u)
        a = math.pi * i / n
        px, py = math.cos(a), math.sin(a)
        pts.append((r * (px * ux + py * vx), r * (px * uy + py * vy)))
    # V down to the apex on the -v side
    apex = -r + flat * 0.5
    if flat > 0:
        pts.append((flat / 2 * -ux + apex * vx, flat / 2 * -uy + apex * vy))
        pts.append((flat / 2 * ux + apex * vx, flat / 2 * uy + apex * vy))
    else:
        pts.append((-r * vx, -r * vy))
    return pts


def stud_solid(d, length, x, y, tip=1.0, teardrop=None, taper_to=None):
    """
    Stud from the board face (z = 0) into the board (z < 0), chamfered
    tip. `teardrop` is a unit 2-vector (in the XY section plane) pointing
    bed-down for a support-free print, or None for a round stud.
    """
    r = d / 2
    if teardrop is None:
        if taper_to:
            s = cq.Workplane("XY").circle(r).workplane(offset=-length).circle(taper_to / 2).loft()
        else:
            s = cq.Workplane("XY").circle(r).extrude(-length)
    else:
        pts = teardrop_wire(r, teardrop, flat=min(0.5, 0.15 * r))
        s = cq.Workplane("XY").polyline(pts).close().extrude(-length)
    if tip > 0:
        s = try_chamfer(s, "<Z", min(tip, r * 0.5))
    return s.translate((x, y, 0))


def teardrop_hole(r, z0, z1, down, x=0.0, y=0.0):
    """Hole cutter with a teardrop section (axis along Z), point toward `down`."""
    pts = teardrop_wire(r, down)
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((x, y, z0))


# ---------------------------------------------------------------- printed threads

def thread_groove(major, pitch, height, clear, overlap=0.15):
    """
    Helical groove for an INTERNAL 60° thread along Z (cut it before the
    minor bore). Groove 0.75 p wide at the minor Ø, root flat 0.125 p at
    the major; `clear` radial oversize for the print.
    Returns (groove solid from z=-p to height+p, minor radius).
    """
    r_minor = F.minor_d(major, pitch) / 2 + clear
    r_major = major / 2 + clear
    w_in, w_out = 0.7 * pitch, 0.125 * pitch
    r_in = r_minor - overlap
    pts = [(r_in, -w_in / 2), (r_minor, -w_in / 2), (r_major, -w_out / 2),
           (r_major, w_out / 2), (r_minor, w_in / 2), (r_in, w_in / 2)]
    helix = cq.Wire.makeHelix(pitch=pitch, height=height + 2 * pitch, radius=r_minor)
    groove = cq.Workplane("XZ").polyline(pts).close().sweep(cq.Workplane().add(helix), isFrenet=True)
    groove = _positive(groove, pts, helix)
    # bore radius a hair over the groove's inner vertex: a bore exactly at r_minor
    # shares a face with the groove and OpenCascade silently drops the cut
    return groove.translate((0, 0, -pitch)), r_minor + 0.02


def _positive(groove, pts, helix):
    """A swept groove can come out inside-out (negative volume) depending on
    the profile winding; rebuild it the other way round when it does."""
    if groove.val().Volume() < 0:
        groove = cq.Workplane("XZ").polyline(list(reversed(pts))).close().sweep(cq.Workplane().add(helix), isFrenet=True)
    return groove


def external_thread_groove(major, pitch, height, clear, overlap=0.25):
    """
    Helical groove for an EXTERNAL thread: cut it from a cylinder of
    Ø major. The ridge left is 0.125 p wide at the crest; `clear` shrinks
    the thread radially so it runs in a printed or steel nut.
    Returns (groove from z=-p to height+p, crest radius).
    """
    r_major = major / 2 - clear
    r_minor = F.minor_d(major, pitch) / 2 - clear
    w_out, w_in = 0.875 * pitch, 0.25 * pitch     # wide at the crest, narrow at the root
    r_out = r_major + overlap
    pts = [(r_minor, -w_in / 2), (r_major, -w_out / 2), (r_out, -w_out / 2),
           (r_out, w_out / 2), (r_major, w_out / 2), (r_minor, w_in / 2)]
    helix = cq.Wire.makeHelix(pitch=pitch, height=height + 2 * pitch, radius=r_minor)
    groove = cq.Workplane("XZ").polyline(pts).close().sweep(cq.Workplane().add(helix), isFrenet=True)
    groove = _positive(groove, pts, helix)
    return groove.translate((0, 0, -pitch)), r_major


# ---------------------------------------------------------------- meshing

def tessellate(shape, tolerance=0.01, angular=0.1):
    verts, tris = shape.tessellate(tolerance, angular)
    return [(v.x, v.y, v.z) for v in verts], [tuple(t) for t in tris]


def stl_bytes(shape, tolerance=0.01, angular=0.1):
    verts, tris = tessellate(shape, tolerance, angular)
    out = bytearray(b"PEGBOARDLAB".ljust(80, b" "))
    out += struct.pack("<I", len(tris))
    for a, b, c in tris:
        p0, p1, p2 = verts[a], verts[b], verts[c]
        u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
        out += struct.pack("<12fH", n[0] / ln, n[1] / ln, n[2] / ln, *p0, *p1, *p2, 0)
    return bytes(out), len(tris)


def stl_merge(a, b):
    na = struct.unpack("<I", a[80:84])[0]
    nb = struct.unpack("<I", b[80:84])[0]
    return a[:80] + struct.pack("<I", na + nb) + a[84:84 + 50 * na] + b[84:84 + 50 * nb]


def write_3mf(parts, title="part", tolerance=0.005, angular=0.05, one_object=True):
    """
    3MF bytes. one_object=True: one build item with one component per
    (name, shape) - Bambu Studio opens it as one object with parts, each
    assignable to its own filament. one_object=False: one object per part.
    """
    import io
    import zipfile
    from xml.sax.saxutils import escape
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           f'<metadata name="Title">{escape(title)}</metadata>',
           '<metadata name="Application">PEGBOARDLAB</metadata>', '<resources>']
    ids = []
    for i, (name, shape) in enumerate(parts, start=1):
        verts, tris = tessellate(shape, tolerance, angular)
        xml.append(f'<object id="{i}" name="{escape(name)}" type="model"><mesh><vertices>')
        xml += [f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in verts]
        xml.append('</vertices><triangles>')
        xml += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris]
        xml.append('</triangles></mesh></object>')
        ids.append(i)
    if one_object and len(parts) > 1:
        root = len(parts) + 1
        xml.append(f'<object id="{root}" name="{escape(title)}" type="model"><components>')
        xml += [f'<component objectid="{i}"/>' for i in ids]
        xml.append('</components></object></resources>')
        xml.append(f'<build><item objectid="{root}"/></build></model>')
    else:
        xml.append('</resources><build>')
        xml += [f'<item objectid="{i}"/>' for i in ids]
        xml.append('</build></model>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                   '</Relationships>')
        z.writestr("3D/3dmodel.model", "".join(xml))
    return buf.getvalue()


def mesh_closed(stl):
    """Open-edge count of a binary STL (0 = watertight), from the bytes."""
    n = struct.unpack("<I", stl[80:84])[0]
    edges = {}
    off = 84
    for _ in range(n):
        tri = struct.unpack("<12fH", stl[off:off + 50])
        off += 50
        v = [tuple(round(c, 4) for c in tri[3 + 3 * k:6 + 3 * k]) for k in range(3)]
        for a, b in ((v[0], v[1]), (v[1], v[2]), (v[2], v[0])):
            k = (a, b) if a < b else (b, a)
            edges[k] = edges.get(k, 0) + 1
    return sum(1 for c in edges.values() if c != 2)


# ---------------------------------------------------------------- print layout and audit

ORIENTS = {
    # name: (label, rotation board -> print coords)
    "face":    ("Face down · studs up", lambda o: rotx(o, 180)),
    "side":    ("On its side", lambda o: roty(o, 90)),
    "upright": ("Upright · standing on the bottom edge", lambda o: rotx(o, 90)),
    "back":    ("Back down · studs down (needs supports)", lambda o: o),
}


def _down_vectors():
    """Board-coordinate direction that ends up pointing at the bed, per orientation,
    found by rotating the axes the same way the parts are."""
    out = {}
    for k, (_, fn) in ORIENTS.items():
        best = None
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            v = fn(cq.Workplane("XY").add(cq.Vertex.makeVertex(*d))).val().toTuple()
            if v[2] < -0.9:
                best = d
        out[k] = best
    return out


DOWN = _down_vectors()


def lay_out(obj, orient):
    """Board-coordinate part -> print coordinates, resting on z = 0 at the origin corner."""
    label, fn = ORIENTS[orient]
    o = fn(obj)
    bb = o.val().BoundingBox()
    return o.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def down_vector(orient):
    """Direction in board coordinates that points at the bed for this orientation."""
    return DOWN[orient]


def teardrop_dir(orient):
    """Section-plane (XY) unit vector a horizontal stud's teardrop should point
    at, or None when the stud axis is vertical in the print."""
    d = down_vector(orient)
    if abs(d[2]) > 0.5:
        return None
    return (d[0], d[1])


def overhang_audit(shape, max_angle=45.0, tolerance=0.05, angular=0.3, first_layer=1.2):
    """
    Area (mm²) of downward faces steeper than `max_angle` from vertical,
    excluding the first layer and bridges are NOT detected (a flat ceiling
    counts as overhang). Returns (area, worst_angle_deg, lowest_z).
    """
    verts, tris = tessellate(shape, tolerance, angular)
    cos_lim = math.cos(math.radians(90 - max_angle))   # normal·(-Z) beyond this = overhang
    area = 0.0
    worst = 0.0
    low = None
    for a, b, c in tris:
        p0, p1, p2 = verts[a], verts[b], verts[c]
        if min(p0[2], p1[2], p2[2]) < first_layer:
            continue
        u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if ln < 1e-9:
            continue
        down = -n[2] / ln
        if down > cos_lim + 1e-3:
            area += ln / 2
            ang = math.degrees(math.asin(min(1.0, down)))      # 90 = flat ceiling
            worst = max(worst, ang)
            z = min(p0[2], p1[2], p2[2])
            low = z if low is None else min(low, z)
    return round(area, 1), round(worst, 1), (round(low, 2) if low is not None else None)
