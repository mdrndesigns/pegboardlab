"""
Kit families: a tab per brand (Bosch 12V, Wera, Irwin, Measure) whose
controls are the tool's own measurements - housing depth, grip width,
beam thickness, neck Ø - and whose geometry is one of the base families
(ARM, SHELF, POCKET) with its parameters derived from those measurements.
Everything the base family offers stays available underneath.

A tool entry:

    "gsr": dict(
        label="GSR 120-LI drill",
        base="arm",                      # arm | shelf | pocket
        pair=("between", "grip"),        # None, or how the two arms are spaced:
                                         #   ("between", dim) the tool hangs BETWEEN the arms, the
                                         #                    named dim must pass the gap
                                         #   ("across", dim)  the tool rests ACROSS the arms, the
                                         #                    named dim is its length along the wall
        dims=[("depth", "Housing depth", 30, 160, 1, 70), ...],   # key, label, min, max, step, default
                                         # a list default makes a list control (min = its hint text)
        fixed=dict(ar_tip="lip", ...),   # base parameters that do not depend on the dims
        derive=lambda d, span, ctx: dict(ar_reach=d["depth"] + 10),   # base parameters from the dims
        note="hangs by its housing on 2 arms",
        notes=lambda d, q, span, gap, ctx: {"depth": f"reach {q['ar_reach']:g}"},   # per-dim readouts (mm)
    )

install(globals(), NAME, LABEL, ORDER, PREFIX, TOOLS) defines PARAMS,
SCHEMA, PLATE, ORIENT, orient_for, validate, plan, build in the kit module.
"""

import importlib
import math

import boards as BD
from families._lib import sl, seg, lst, parse_list


def _base(name):
    return importlib.import_module(f"families.{name}")


def install(ns, name, label, order, prefix, tools, intro=""):
    first = next(iter(tools))
    tool_key = f"{prefix}tool"
    span_key = f"{prefix}span"
    params = {tool_key: first, span_key: 0}
    schema = [seg(tool_key, "Tool", [(k, t["label"]) for k, t in tools.items()], label, wrap=2)]
    pair_tools = [k for k, t in tools.items() if t.get("pair")]
    for k, t in tools.items():
        for dk, dl, lo, hi, st, dv in t.get("dims", []):
            key = f"{prefix}{k}_{dk}"
            params[key] = dv
            if isinstance(dv, list):                 # a list control: lo carries the hint text
                schema.append(lst(key, dl, label, show={"key": tool_key, "in": [k]}, hint=str(lo)))
            else:
                schema.append(sl(key, dl, lo, hi, st, label, show={"key": tool_key, "in": [k]}))
    if pair_tools:
        schema.append(sl(span_key, "Arms apart · pitches (0 = auto)", 0, 14, 1, label, show={"key": tool_key, "in": pair_tools}))

    def dims_of(p, k):
        out = {}
        for dk, _, _, _, _, dv in tools[k].get("dims", []):
            v = p[f"{prefix}{k}_{dk}"]
            out[dk] = parse_list(v) if isinstance(dv, list) else (bool(v) if isinstance(dv, bool) else float(v))
        return out

    def pair_of(p, ctx, k, d):
        """(span, gap, note) for a pair tool: the arms' spacing in hole pitches."""
        t = tools[k]
        if not t.get("pair"):
            return 0, 0.0, None
        mode, dk = t["pair"]
        b = ctx["b"]
        rs = BD.row_step(b)
        bw = BD.stud_d(b) + 2 * float(p["mt_margin"])
        v = float(d[dk])
        span = int(p[span_key])
        if span <= 0:
            if mode == "between":
                span = max(2, math.ceil((v + 2.0 + bw) / rs))
            else:
                span = max(2, int((v - bw - 8.0) // rs))
        gap = span * rs - bw
        if mode == "between":
            note = f"2 arms {span} pitches apart ({span * rs:.1f}): {gap:.1f} gap between them for the {v:g} wide {dk}"
            if gap < v + 1.0:
                ctx["warns"].append(f"The {dk} ({v:g}) does not pass between the arms ({gap:.1f}): more pitches.")
        else:
            note = f"2 arms {span} pitches apart ({span * rs:.1f}) under the {v:g} long tool"
            if span * rs + bw > v - 4.0:
                ctx["warns"].append(f"Arms ({span * rs + bw:.1f} outside to outside) wider than the tool ({v:g}): fewer pitches.")
        return span, gap, note

    def resolve(p, ctx):
        k = p[tool_key]
        t = tools[k]
        d = dims_of(p, k)
        span, gap, note = pair_of(p, ctx, k, d)
        q = dict(p)
        q.update(t.get("fixed", {}))
        q.update(t["derive"](d, span, ctx) if t.get("derive") else {})
        q["family"] = t["base"]
        return q, t, note

    def plate_fn(p):
        return getattr(_base(tools[p[tool_key]]["base"]), "PLATE", True)

    def orient_for(p):
        b = _base(tools[p[tool_key]]["base"])
        return b.ORIENT.get("no_supports" if p["no_supports"] else "default")

    def validate(p):
        q, t, _ = resolve(p, dict(b=BD.BOARDS[p["board"]], warns=[]))
        b = _base(t["base"])
        return b.validate(q) if hasattr(b, "validate") else []

    def kit_notes(p, ctx, q, t):
        k = p[tool_key]
        d = dims_of(p, k)
        span, gap, _ = pair_of(p, ctx, k, d)
        out = {}
        if t.get("pair"):
            rs = BD.row_step(ctx["b"])
            out[span_key] = f"{span} × {rs:g} = {span * rs:.1f} centres · {gap:.1f} between the arms"
        if t.get("notes"):
            try:
                for dk, text in t["notes"](d, q, span, gap, ctx).items():
                    out[f"{prefix}{k}_{dk}"] = text
            except Exception:
                pass
        ctx.setdefault("notes", {}).update(out)

    def plan(p, ctx):
        q, t, note = resolve(p, ctx)
        want = _base(t["base"]).plan(q, ctx)
        kit_notes(p, ctx, q, t)
        return want

    def build(p, ctx, plate, mp):
        q, t, note = resolve(p, ctx)
        if plate is None:
            kit_notes(p, ctx, q, t)
        body = _base(t["base"]).build(q, ctx, plate, mp)
        ctx["derived"]["tool"] = f"{label} · {t['label']} · {t['base']}"
        if note:
            ctx["derived"]["pair"] = note
        if t.get("note"):
            ctx["derived"]["use"] = t["note"]
        return body

    ns.update(NAME=name, LABEL=label, ORDER=order, PARAMS=params, SCHEMA=schema, TOOLS=tools, PREFIX=prefix,
              ORIENT={"default": "upright", "no_supports": "upright"}, PLATE=plate_fn, orient_for=orient_for,
              validate=validate, plan=plan, build=build, resolve=resolve, INTRO=intro)
