#!/usr/bin/env python3
"""
PEGBOARDLAB - local parametric front end for pegboard accessories.

    python3 app.py            -> http://localhost:8768

Sliders in the browser, CadQuery on the server; the browser only shows
the mesh the server built, so what you see is what exports. Sister of
SLOTLAB, KNOBLAB and BOXLAB.
"""

import argparse
import io
import json
import os
import tempfile
import threading
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import cadquery as cq

import boards as BD
import branding as B
import fasteners as F
import geometry as G
import model as M

HERE = os.path.dirname(os.path.abspath(__file__))
KERNEL_LOCK = threading.Lock()
CONTEXT_CACHE = {}
EMPTY_STL = bytes(84)


def export_bytes(obj, ext, **kw):
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as fh:
        path = fh.name
    try:
        cq.exporters.export(obj, path, **kw)
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        os.unlink(path)


def stats_for(shape):
    bb = shape.BoundingBox()
    return {"bbox": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
            "volume": round(shape.Volume() / 1000.0, 2), "valid": bool(shape.isValid())}


def catalog():
    return {
        "boards": {k: {**v} for k, v in BD.BOARDS.items()},
        "board_order": BD.ORDER,
        "geom_keys": list(BD.GEOM_KEYS),
        "materials": F.MATERIALS,
        "families": {k: {"label": v.LABEL, "orient": v.ORIENT, "plate": M.has_plate(v, M.DEFAULTS),
                         "kit": getattr(v, "INTRO", "") if hasattr(v, "TOOLS") else ""} for k, v in M.FAMILIES.items()},
        "orients": {k: v[0] for k, v in G.ORIENTS.items()},
        "fonts": B.available_fonts(),
        "magnets": {k: list(v) for k, v in F.MAGNETS.items()},
        "schema": M.schema(),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _params(self, qs):
        return M.merge_params({k: v[0] for k, v in qs.items()})

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)

        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")

        if u.path.startswith("/vendor/") and ".." not in u.path:
            fp = os.path.join(HERE, u.path.lstrip("/"))
            if os.path.isfile(fp):
                with open(fp, "rb") as fh:
                    return self._send(200, fh.read(), "text/javascript; charset=utf-8")
            return self._send(404, "not found", "text/plain")

        if u.path == "/defaults":
            return self._send(200, json.dumps({"defaults": M.DEFAULTS, "catalog": catalog()}), "application/json")

        if u.path == "/preview.stl":
            p = self._params(qs)
            errs = M.validate(p)
            if errs:
                return self._send(400, json.dumps({"errors": errs}), "application/json")
            try:
                with KERNEL_LOCK:
                    body, spec, warnings = M.build(p)
                    laid = M.layout(body, spec)
                    if p["print_view"]:
                        parts, _ = M.parts_for_export(body, spec)
                        shown_shape = cq.Compound.makeCompound([sh for n, sh in parts if n != "brand"])
                    elif spec.get("spine") is not None:
                        shown_shape = cq.Compound.makeCompound(M.spine_parts(spec) + [body.translate((0, 0, spec["spine_t"])).val()])
                    else:
                        shown_shape = body.val()
                    data, _ = G.stl_bytes(shown_shape, 0.03, 0.2)
                    brand_tris = 0
                    bs = spec.get("brand_solid")
                    if bs is not None and spec.get("spine") is not None and not p["print_view"]:
                        bs = bs.translate(cq.Vector(0, 0, spec["spine_t"]))
                    if bs is not None:
                        bshape = bs if not p["print_view"] else G.lay_out(cq.Workplane("XY").add(bs), spec["orient"]).val()
                        bdata, brand_tris = G.stl_bytes(bshape, 0.03, 0.2)
                        data = G.stl_merge(data, bdata)
                    stats = {"part": stats_for(body.val()), "derived": M.derived(p, spec, laid),
                             "warnings": warnings, "context_key": "" if p["print_view"] else M.context_key(p, spec),
                             "brand_tris": brand_tris, "print_view": bool(p["print_view"]),
                             "dims": M.print_dims(parts) if p["print_view"] else spec.get("dims", []),
                             "notes": spec.get("notes", {})}
            except Exception as e:
                return self._send(400, json.dumps({"errors": [f"Build failed: {e}"]}), "application/json")
            return self._send(200, data, "model/stl", {"X-Stats": json.dumps(stats)})

        if u.path == "/context.stl":
            p = self._params(qs)
            errs = M.validate(p)
            if errs:
                return self._send(400, json.dumps({"errors": errs}), "application/json")
            try:
                with KERNEL_LOCK:
                    body, spec, _ = M.build(p)
                    key = M.context_key(p, spec)
                    if key in CONTEXT_CACHE:
                        return self._send(200, CONTEXT_CACHE[key], "model/stl")
                    ctx = M.context(p, spec)
                    data = EMPTY_STL if ctx is None else G.stl_bytes(ctx.val(), 0.08, 0.4)[0]
            except Exception as e:
                return self._send(400, json.dumps({"errors": [f"Context failed: {e}"]}), "application/json")
            if len(CONTEXT_CACHE) > 40:
                CONTEXT_CACHE.clear()
            CONTEXT_CACHE[key] = data
            return self._send(200, data, "model/stl")

        if u.path == "/export":
            p = self._params(qs)
            errs = M.validate(p)
            if errs:
                return self._send(400, json.dumps({"errors": errs}), "application/json")
            name = qs.get("name", ["part"])[0].strip() or "part"
            name = "".join(c for c in name if c.isalnum() or c in "-_")
            with KERNEL_LOCK:
                body, spec, warnings = M.build(p, export=True)
                parts, laid = M.parts_for_export(body, spec)
                whole = M.assembly(body, spec)
                der = M.derived(p, spec, laid)
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    z.writestr(f"{name}.step", export_bytes(whole, "step"))
                    if len(parts) == 1:
                        z.writestr(f"{name}.stl", G.stl_bytes(parts[0][1], 0.005, 0.05)[0])
                        z.writestr(f"{name}.3mf", G.write_3mf([(name, parts[0][1])], name))
                    elif spec.get("spine") is not None and spec.get("brand_solid") is None:
                        # two prints on one plate: separate objects
                        z.writestr(f"{name}.3mf", G.write_3mf([(f"{name}_{n}", sh) for n, sh in parts], name, one_object=False))
                        for n, sh in parts:
                            z.writestr(f"{name}_{n}.stl", G.stl_bytes(sh, 0.005, 0.05)[0])
                    else:
                        base_stl, _ = G.stl_bytes(parts[0][1], 0.005, 0.05)
                        brand_stl, _ = G.stl_bytes(parts[1][1], 0.005, 0.05)
                        z.writestr(f"{name}.3mf", G.write_3mf([(f"{name}_base", parts[0][1]), (f"{name}_brand", parts[1][1])], name))
                        z.writestr(f"{name}_base.stl", base_stl)
                        z.writestr(f"{name}_brand.stl", brand_stl)
                        z.writestr(f"{name}.stl", G.stl_merge(base_stl, brand_stl))
                        z.writestr(f"{name}_TWO_FILAMENTS.txt", DUAL_NOTE.format(name=name))
                    svg_name = None
                    if p["brand_src"] == "svg" and p["brand_svg"] in B.SVG_STORE:
                        svg_name = f"{name}_brand.svg"
                        z.writestr(svg_name, B.SVG_STORE[p["brand_svg"]])
                    z.writestr(f"{name}_parameters.json", json.dumps(p, indent=2))
                    z.writestr(f"{name}_spec.json", json.dumps({"derived": der, "warnings": warnings,
                                                                 "part": stats_for(body.val())}, indent=2))
                    z.writestr(f"{name}_PRINT.txt", print_note(name, p, der, warnings))
                    z.writestr(f"{name}_model.py", script_for(p, svg_name))
            return self._send(200, buf.getvalue(), "application/zip",
                              {"Content-Disposition": f'attachment; filename="{name}.zip"'})

        return self._send(404, "not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/svg":
            return self._send(404, "not found", "text/plain")
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n <= 0 or n > B.SVG_MAX:
            return self._send(400, json.dumps({"errors": ["SVG missing or over 2 MB."]}), "application/json")
        text = self.rfile.read(n).decode("utf-8", "replace")
        try:
            key, info = B.store_svg(text)
        except Exception as e:
            return self._send(400, json.dumps({"errors": [f"SVG rejected: {e}"]}), "application/json")
        return self._send(200, json.dumps({"key": key, **info}), "application/json")


DUAL_NOTE = """{name}: two-filament branding
=================================

{name}.3mf is one object with two parts: "{name}_base" and "{name}_brand".

Bambu Studio: import the 3MF (answer Yes to "load as a single object with
multiple parts"), expand the object, right-click "{name}_brand" > Change
filament. Fallback: import {name}_base.stl and {name}_brand.stl together.
Same material family for both filaments so they bond; prime tower on.
"""


def print_note(name, p, der, warnings):
    lines = [f"{name}: print notes", "=" * (len(name) + 13), "",
             f"Orientation : {der.get('orient')}  (the STL / 3MF are already laid on the bed)",
             f"Print size  : {der.get('print_size')} mm",
             f"Board       : {der.get('board')}",
             f"Studs       : {der.get('studs')} × Ø{der.get('stud_d')} × {der.get('stud_len')}",
             f"Unsupported : {der.get('overhang_mm2')} mm² ({der.get('overhang_note')})", ""]
    if "pause_at" in der:
        lines += [f"MAGNETS     : pause at Z = {der['pause_at']}  (Bambu Studio: right-click the layer > Add pause)",
                  f"              {der.get('magnets')}", ""]
    if "thread" in der:
        lines += [f"Thread      : {der['thread']} - make the NUT family on the same board preset", ""]
    if "bore" in der:
        lines += [f"Bolts       : {der['bore']}", ""]
    lines += ["ABS-GF on the H2S: hardened nozzle, 4+ walls, 0.2 layers (0.12 for printed threads),",
              "X-Y hole compensation 0.10, elephant foot 0.15. Hooks and racks print upright with",
              "teardrop studs; plates and magnet strips print face down.", ""]
    if warnings:
        lines += ["Warnings:"] + [f"  - {w}" for w in warnings]
    return "\n".join(lines) + "\n"


def script_for(p, svg_name=None):
    lines = [
        "# Generated by PEGBOARDLAB. Standalone - edit and re-run with:",
        "#   python3 this_file.py   (needs the pegboardlab folder beside it: model.py, families/, fonts/ ...)",
        "import sys, os",
        "HERE = os.path.dirname(os.path.abspath(__file__))",
        "sys.path.insert(0, HERE)",
        "import cadquery as cq",
        "import geometry as G",
        "import model as M",
        "",
        "PARAMS = {",
    ]
    for k, v in p.items():
        lines.append(f"    {k!r}: {v!r},")
    lines += ["}", ""]
    if svg_name:
        lines += ["import branding as B",
                  f"with open(os.path.join(HERE, {svg_name!r}), encoding='utf-8') as fh:",
                  "    B.SVG_STORE[PARAMS['brand_svg']] = fh.read()", ""]
    lines += [
        "errs = M.validate(PARAMS)",
        "if errs:",
        "    raise SystemExit('\\n'.join(errs))",
        "body, spec, warnings = M.build(PARAMS, export=True)",
        "parts, laid = M.parts_for_export(body, spec)",
        "cq.exporters.export(M.assembly(body, spec), 'part.step')",
        "open('part.stl', 'wb').write(G.stl_bytes(parts[0][1], 0.005, 0.05)[0])",
        "open('part.3mf', 'wb').write(G.write_3mf([(n, s) for n, s in parts], 'part'))",
        "print('exported', M.derived(PARAMS, spec, laid), warnings)",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8768)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError as e:
        print(f"Cannot bind port {a.port}: {e}")
        print(f"Something is already using it. Try:  python3 app.py --port {a.port + 1}")
        raise SystemExit(1)
    url = f"http://localhost:{a.port}"
    print(f"PEGBOARDLAB running at {url}   (ctrl-C to stop)")
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
