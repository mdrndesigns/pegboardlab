"""Shared pieces for the family modules."""

import math

import cadquery as cq

import fasteners as F
import geometry as G


def sl(key, label, lo, hi, step, group, show=None, note=None):
    d = {"key": key, "label": label, "type": "slider", "min": lo, "max": hi, "step": step, "group": group}
    if show:
        d["show"] = show
    if note:
        d["note"] = note
    return d


def seg(key, label, options, group, show=None, wrap=None):
    d = {"key": key, "label": label, "type": "seg", "options": options, "group": group}
    if show:
        d["show"] = show
    if wrap:
        d["wrap"] = wrap
    return d


def parse_list(v):
    """A list control's value: numbers, or 'a x b' pairs, from a list or a comma-separated string.
    '4.5, 6, 3.6x11' -> [4.5, 6.0, [3.6, 11.0]]"""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        toks = []
        for x in v:
            if isinstance(x, (list, tuple)):
                toks.append([float(x[0]), float(x[1])])
            elif isinstance(x, dict):
                toks.append(x)
            elif isinstance(x, (int, float)):
                toks.append(float(x))
            else:
                toks += parse_list(str(x))
        return toks
    out = []
    for tok in str(v).replace(";", ",").split(","):
        tok = tok.strip().lower().replace("×", "x")
        if not tok:
            continue
        if "x" in tok:
            a, b = tok.split("x", 1)
            try:
                out.append([float(a), float(b)])
            except ValueError:
                continue
        else:
            try:
                out.append(float(tok))
            except ValueError:
                continue
    return out


def lst(key, label, group, show=None, hint=""):
    """A list control: comma-separated numbers (or a×b pairs); blank = use the slider."""
    d = {"key": key, "label": label, "type": "list", "group": group, "hint": hint}
    if show:
        d["show"] = show
    return d


def web_cap(mp, p, y_floor, head=None):
    """Highest point (plate Y) an end web may reach without covering a screw head: the lowest stud
    above y_floor keeps head Ø / 2 + 1.5 clear. None = no stud above (webs may rise freely)."""
    if not mp or not mp.get("studs"):
        return None
    hd = float(head if head is not None else p.get("screw_head", 8.0))
    ys = sorted(y for x, y in mp["studs"] if y - hd / 2 - 1.5 > y_floor + 3.0)
    return (ys[0] - hd / 2 - 1.5) if ys else None


def web_params(prefix, group):
    """PARAMS + SCHEMA for a family's end braces (webs): `<prefix>webs` toggle must exist already."""
    params = {f"{prefix}web_shape": "triangle", f"{prefix}web_t": 3.0, f"{prefix}web_h": 0.0, f"{prefix}web_run": 0.0}
    show = {"key": f"{prefix}webs", "eq": True}
    schema = [
        seg(f"{prefix}web_shape", "Brace shape", [("triangle", "Triangle"), ("wall", "Wall")], group, show=show),
        sl(f"{prefix}web_t", "Brace thickness", 1.5, 10, 0.5, group, show=show),
        sl(f"{prefix}web_h", "Brace height (0 = auto, under the screws)", 0, 150, 1, group, show=show),
        sl(f"{prefix}web_run", "Brace run out from the plate (0 = full)", 0, 200, 1, group, show=show),
    ]
    return params, schema


def end_webs(body, p, prefix, mp, w, y0, t0, depth, ph, ctx=None):
    """End braces on a shelf: at the very ends of the backing (x = ±w/2), rising from y0 (the shelf
    top) against the plate, running `run` out along the shelf. Height is capped under the lowest
    stud above the shelf (screw heads stay clear) unless set by hand. Returns (body, rise, run, wt)."""
    if not p.get(f"{prefix}webs") or depth <= 12:
        return body, 0.0, 0.0, 0.0
    wt = float(p.get(f"{prefix}web_t", 3.0))
    run = float(p.get(f"{prefix}web_run", 0.0)) or (depth - 2.0)
    run = min(run, depth - 0.5)
    rise = float(p.get(f"{prefix}web_h", 0.0))
    cap = web_cap(mp, p, y0)
    if rise <= 0:
        rise = min(ph - 4.0, run)
        if cap is not None:
            rise = min(rise, cap - y0)
    elif cap is not None and rise > cap - y0 + 1e-6 and ctx is not None:
        ctx["warns"].append(f"Brace {rise:g} high covers a screw head: {cap - y0:.1f} is the most that clears it.")
    if rise <= 3:
        if ctx is not None:
            ctx["warns"].append("End braces dropped: no room under the lowest screw.")
        return body, 0.0, 0.0, wt
    shape = p.get(f"{prefix}web_shape", "triangle")
    for x0 in (-w / 2 + wt / 2, w / 2 - wt / 2):
        if shape == "wall":
            blk = G.box(x0 - wt / 2, x0 + wt / 2, y0 - 0.01, y0 + rise, t0 - 0.01, t0 + run)
            body = body.union(G.try_chamfer(blk, ">Y", min(1.0, wt / 2 - 0.2)))
        else:
            body = body.union(G.wedge(wt, run, rise, x0=x0, up=True).translate((0, y0, t0 - 0.01)))
    return body, rise, run, wt


def tog(key, label, group, show=None):
    d = {"key": key, "label": label, "type": "toggle", "group": group}
    if show:
        d["show"] = show
    return d


def arm_j(w, reach, t, tip, bend_r, z0, y_bottom, no_supports, x0=0.0):
    """
    J arm leaving the plate front (z = z0) with its underside at y_bottom:
    shelf `reach` out, `t` thick, lip rising `tip`. Inner cove radius
    bend_r. With no_supports the outer corner is a 45° chamfer (prints
    upright on the bed); otherwise a fillet.
    """
    shelf = G.box(x0 - w / 2, x0 + w / 2, y_bottom, y_bottom + t, z0 - 0.01, z0 + reach)
    arm = shelf
    if tip > 0.05:
        lip = G.box(x0 - w / 2, x0 + w / 2, y_bottom, y_bottom + t + tip, z0 + reach - t, z0 + reach)
        arm = arm.union(lip)
        inner = cq.selectors.NearestToPointSelector((x0, y_bottom + t, z0 + reach - t))
        try:
            arm = arm.edges(inner).fillet(min(bend_r, reach - t - 0.2, tip - 0.2))
        except Exception:
            pass
        outer = cq.selectors.NearestToPointSelector((x0, y_bottom, z0 + reach))
        if no_supports:
            try:
                arm = arm.edges(outer).chamfer(min(t - 0.2, bend_r))
            except Exception:
                pass
        else:
            try:
                arm = arm.edges(outer).fillet(min(bend_r + t - 0.1, t - 0.2 + bend_r))
            except Exception:
                pass
        top = cq.selectors.NearestToPointSelector((x0, y_bottom + t + tip, z0 + reach - t / 2))
        try:
            arm = arm.edges(top).fillet(t / 2 - 0.15)
        except Exception:
            pass
    return arm


def cove(w, r, z0, y_top, x0=0.0):
    """Concave fillet block in the corner between the plate front (z = z0)
    and the top face of a shelf at y = y_top: a quarter-round of material."""
    blk = G.box(x0 - w / 2, x0 + w / 2, y_top, y_top + r, z0, z0 + r)
    cutter = cq.Workplane("XY").circle(r).extrude(w + 2).translate((0, 0, 0))
    cutter = (cq.Workplane("YZ").center(y_top + r, z0 + r).circle(r).extrude(w / 2 + 1, both=True)
              .translate((x0, 0, 0)))
    return blk.cut(cutter)


def magnet_pockets(body, pts, d, t, clear_d, z_open, from_top, cover, no_supports, derived, warns, axis_down=None):
    """
    Magnet pockets at (x, y) in a slab lying in the XY plane whose face at
    z = z_open is where the magnet goes in (from_top = the pocket opens on
    that face) or where it is covered by `cover` mm of material (embedded,
    print pauses). Pocket Ø = d + clear_d, depth t + 0.2.
    """
    r = (d + clear_d) / 2
    depth = t + 0.2
    for x, y in pts:
        if from_top:
            body = body.cut(G.cyl(r, z_open - depth, z_open + 1, x, y))
        else:
            body = body.cut(G.cyl(r, z_open - cover - depth, z_open - cover, x, y))
    derived["magnets"] = f"{len(pts)} × Ø{d:g} × {t:g}  pocket Ø{2 * r:.2f} × {depth:.2f}"
    return body


def magnet_spec(p, prefix="mg_"):
    key = p[prefix + "size"]
    if key == "custom" or key not in F.MAGNETS:
        return float(p[prefix + "d"]), float(p[prefix + "t"]), None
    d, t, pull, grade = F.MAGNETS[key]
    return d, t, pull


MAGNET_OPTIONS = [(k, k) for k in F.MAGNET_ORDER]
