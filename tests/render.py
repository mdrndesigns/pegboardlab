#!/usr/bin/env python3
"""Preview PNGs of the coupons (matplotlib, black / white / #0000FF)."""
import os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "samples")


def read_stl(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(float), arr["n"].astype(float)


def render(path, png, elev=28, azim=-55, title=""):
    tris, norms = read_stl(path)
    # shade by normal, pure blue family
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    sh = np.clip(norms @ light, 0, 1) * 0.6 + 0.4
    cols = np.stack([np.zeros_like(sh), np.zeros_like(sh), np.ones_like(sh) * 0.55 + 0.45 * sh], 1)
    fig = plt.figure(figsize=(14, 6), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    pc = Poly3DCollection(tris, facecolors=cols, edgecolors="none")
    ax.add_collection3d(pc)
    lo, hi = tris.min(axis=(0, 1)), tris.max(axis=(0, 1))
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(hi - lo))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.patch.set_facecolor("white")
    ax.text2D(0.02, 0.95, title, transform=ax.transAxes, family="monospace", fontsize=11, color="black")
    fig.savefig(png, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    for tag, t in (("imperial", "COUPON IMPERIAL  Ø7.5 · 19 mm · 23.876 square"),
                   ("metric", "COUPON METRIC  Ø4.7 · 4 mm · 45° lattice")):
        render(os.path.join(OUT, f"coupon_{tag}.stl"), os.path.join(OUT, f"coupon_{tag}_preview.png"), title=t)
    print("rendered")
