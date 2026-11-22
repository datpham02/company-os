"""Spike S2 (Board R&D, 2026-11-22): engine-neutral rig + clip JSON from part PNGs.

Run with ComfyUI's embedded Python (NumPy, Pillow):  python -I -s make_rig.py
Parts are full-canvas RGBA PNGs (832x1216, the master's frame) in art/parts/.
Mesh: a grid over each part's alpha (cells with any opaque pixel), triangulated; this is the
simplest mesh, not the CDT mesh of spike S10. Weights: rigid parts 1.0 to one bone; the cloak
blends root -> torso by height (smoothstep), so a torso turn bends the cloak.
Writes rig.json and clip_sway.json, then checks every triangle at every clip frame with a CPU
linear-blend-skinning reference: a triangle whose signed area changes sign is a flip.
"""
import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 24

BONES = [  # name, parent, pivot (image px), length
    ("Root", None, (380, 1180), 400),
    ("Torso", "Root", (380, 760), 360),
    ("Head", "Torso", (410, 300), 200),
    ("ArmFront", "Torso", (360, 430), 180),
]
PARTS = [  # name, png, bone weighting
    ("cloak", "art_src/parts/cloak_full.png", "cloak"),
    ("arm_front", "art_src/parts/arm_front_full.png", "ArmFront"),
    ("head", "art_src/parts/head_full.png", "Head"),
]
DRAW_ORDER = ["cloak", "head", "arm_front"]


def grid_mesh(alpha):
    h, w = alpha.shape
    ys, xs = np.nonzero(alpha > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    nx, ny = math.ceil((x1 - x0) / CELL), math.ceil((y1 - y0) / CELL)
    vid, verts, tris = {}, [], []

    def v(i, j):
        if (i, j) not in vid:
            vid[(i, j)] = len(verts)
            verts.append((float(min(x0 + i * CELL, w)), float(min(y0 + j * CELL, h))))
        return vid[(i, j)]

    for j in range(ny):
        for i in range(nx):
            cx0, cy0 = x0 + i * CELL, y0 + j * CELL
            if (alpha[cy0:cy0 + CELL, cx0:cx0 + CELL] > 8).any():
                a, b, c, d = v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)
                tris += [(a, b, c), (a, c, d)]
    return verts, tris


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def weights_for(kind, verts):
    names = [b[0] for b in BONES]
    W = np.zeros((len(verts), len(names)))
    for k, (x, y) in enumerate(verts):
        if kind == "cloak":
            t = smoothstep(1180, 700, y)        # 0 at the hem, 1 at the waist and above
            W[k, names.index("Root")] = 1 - t
            W[k, names.index("Torso")] = t
        else:
            W[k, names.index(kind)] = 1.0
    return W


def build():
    rig = {"schema": "rig.v0", "canvas": [832, 1216], "bones": [], "parts": [], "draw_order": DRAW_ORDER}
    for name, parent, pivot, length in BONES:
        rig["bones"].append({"name": name, "parent": parent, "pivot": list(pivot), "length": length})
    for name, png, kind in PARTS:
        alpha = np.asarray(Image.open(os.path.join(HERE, png)).convert("RGBA"))[..., 3]
        verts, tris = grid_mesh(alpha)
        W = weights_for(kind, verts)
        rig["parts"].append({"name": name, "texture": png, "vertices": [list(p) for p in verts],
                             "triangles": [list(t) for t in tris],
                             "weights": {b[0]: W[:, i].round(4).tolist() for i, b in enumerate(BONES) if W[:, i].any()}})
    # clip: 2.0 s loop at 30 fps; rotation keys in radians, eased (sine) - a v0 stand-in for presets (S4)
    fps, frames = 30, 60
    clip = {"schema": "clip.v0", "name": "sway", "fps": fps, "length": frames / fps, "loop": True, "tracks": {}}
    for bone, amp, phase in (("Torso", 0.08, 0.0), ("Head", 0.10, 0.6), ("ArmFront", 0.25, 1.2)):
        clip["tracks"][bone] = [[round(f / fps, 4), round(amp * math.sin(2 * math.pi * f / frames + phase), 5)]
                                for f in range(0, frames + 1, 5)]
    json.dump(rig, open(os.path.join(HERE, "rig.json"), "w"), indent=0)
    json.dump(clip, open(os.path.join(HERE, "clip_sway.json"), "w"), indent=1)
    return rig, clip


def rot_about(p, angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, p[0] - c * p[0] + s * p[1]], [s, c, p[1] - s * p[0] - c * p[1]], [0, 0, 1]])


def flip_check(rig, clip):
    parent = {b["name"]: b["parent"] for b in rig["bones"]}
    pivot = {b["name"]: b["pivot"] for b in rig["bones"]}

    def sample(track, t):
        ks = clip["tracks"].get(track)
        if not ks:
            return 0.0
        for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return ks[-1][1]

    worst = {}
    for f in range(int(clip["length"] * clip["fps"]) + 1):
        t = f / clip["fps"]
        G = {}
        for b in rig["bones"]:  # parents come first in the list
            M = rot_about(pivot[b["name"]], sample(b["name"], t))
            G[b["name"]] = (G[parent[b["name"]]] @ M) if parent[b["name"]] else M
        for part in rig["parts"]:
            V = np.c_[np.array(part["vertices"]), np.ones(len(part["vertices"]))]
            out = np.zeros((len(V), 2))
            for bone, w in part["weights"].items():
                out += np.array(w)[:, None] * (V @ G[bone].T)[:, :2]
            T = np.array(part["triangles"])
            def area(P):
                a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
                return (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            r = area(out) / area(V[:, :2])
            worst[part["name"]] = min(worst.get(part["name"], 9), float(r.min()))
    return worst


if __name__ == "__main__":
    rig, clip = build()
    for p in rig["parts"]:
        print(p["name"], "vertices", len(p["vertices"]), "triangles", len(p["triangles"]), "bones", list(p["weights"]))
    w = flip_check(rig, clip)
    print("min triangle area ratio over the clip (<=0 means a flip):", {k: round(v, 3) for k, v in w.items()})
