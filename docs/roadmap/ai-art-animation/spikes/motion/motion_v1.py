"""Deterministic motion solver, checks and QA renderer (Board R&D, 2026-11-22; methodology 04-animation-methodology.md).

    python -I -s motion.py <structure.json> <motion.json> <out_dir>

Engine-neutral. Reads a structure.v1 (skeleton with locked bone lengths, contacts, rigid attachments) and a motion.v1
(phases, key poses, easing, constraints, events, acceptance), solves every frame, checks the acceptance criteria and
writes the QA evidence: frames, real-time and slow-motion GIFs, a sequential contact sheet, trajectories, a timing
graph, silhouettes, and checks.json. The render is a blocking proxy (capsules + the rigid hammer shape): it judges
MOTION, not artwork.

Solving:
  spine/neck/head and the free arm: forward kinematics (angle offsets from rest, chest frame for the arms)
  hammer arm: two-bone IK to a hand target given in polar form around the shoulder (reach, dir) in the chest frame;
              interpolating (reach, dir, hammer angle) produces arcs, not straight lines
  hammer: rigid master asset placed on the hand by transform only (grip at the hand joint)
  legs: two-bone IK to the foot targets (planted = rest ankle + step dx; a step between keys lifts on a sin arc),
        knees bend forward (+x)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

EASE = {"lin": lambda u: u, "in": lambda u: u ** 3, "out": lambda u: 1 - (1 - u) ** 3,
        "inout": lambda u: u * u * (3 - 2 * u)}
PHASE_COL = {"idle": (120, 130, 140), "anticipation": (90, 160, 220), "windup": (70, 110, 230), "swing": (240, 170, 60),
             "impact": (235, 70, 60), "follow_through": (230, 120, 170), "recovery": (110, 200, 120),
             "return_to_idle": (170, 170, 120)}


def rot(deg):
    r = math.radians(deg)
    return np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])


def polar(r, deg):
    a = math.radians(deg)
    return np.array([r * math.cos(a), r * math.sin(a)])


def ik2(root, target, l1, l2, side):
    """Two-bone IK; side = +1/-1 picks the bend. Returns (mid joint, clamped?)."""
    d = target - root
    dist = float(np.linalg.norm(d))
    clamped = False
    lo, hi = abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3
    if dist > hi or dist < lo:
        clamped = True
        dist = min(max(dist, lo), hi)
    u = d / (np.linalg.norm(d) + 1e-9)
    a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    a = math.acos(max(-1.0, min(1.0, a)))
    mid = root + rot(math.degrees(a) * side) @ u * l1
    return mid, clamped


class Solver:
    def __init__(self, structure, motion):
        self.s, self.m = structure, motion
        self.R = {j: np.array(v["rest"], float) for j, v in structure["joints"].items()}
        self.L = {b: float(np.linalg.norm(self.R[v["to"]] - self.R[v["from"]])) for b, v in structure["bones"].items()}
        self.keys = sorted(motion["keys"], key=lambda k: k["frame"])
        self.n = self.keys[-1]["frame"] + 1
        h = structure["objects"][structure["attachments"]["hammer"]["asset"]]
        self.hammer = h
        # bend sides from the rest pose
        def side(a, b, c):
            v1, v2 = self.R[b] - self.R[a], self.R[c] - self.R[a]
            return 1 if (v1[0] * v2[1] - v1[1] * v2[0]) < 0 else -1
        self.side_arm = side("shoulder_f", "hand_f", "elbow_f")
        self.side_k = side("hip_k", "ankle_k", "knee_k")
        self.side_f = side("hip_f", "ankle_f", "knee_f")
        self.flags = []

    def channel(self, f):
        """Interpolated pose dict and step progress for frame f."""
        ks = self.keys
        if f >= ks[-1]["frame"]:
            return ks[-1]["pose"], {}
        i = max(j for j in range(len(ks)) if ks[j]["frame"] <= f)
        a, b = ks[i], ks[i + 1]
        u = (f - a["frame"]) / (b["frame"] - a["frame"])
        e = EASE[a["ease"]](u)

        def mix(x, y):
            if isinstance(x, dict):
                return {k: mix(x[k], y[k]) for k in x}
            if isinstance(x, list):
                return [mix(p, q) for p, q in zip(x, y)]
            return x + (y - x) * e
        pose = mix(a["pose"], b["pose"])
        steps = {c: u for c in a["pose"]["feet"] if a["pose"]["feet"][c][0] != b["pose"]["feet"][c][0]}
        return pose, steps

    def solve(self, f):
        p, steps = self.channel(f)
        R = self.R
        J = {}
        J["pelvis"] = R["pelvis"] + np.array(p["pelvis"], float)
        sp = p["spine"]
        J["chest"] = J["pelvis"] + rot(sp) @ (R["chest"] - R["pelvis"])
        J["neck"] = J["chest"] + rot(sp + p["neck"]) @ (R["neck"] - R["chest"])
        J["head"] = J["neck"] + rot(sp + p["neck"] + p["head"]) @ (R["head"] - R["neck"])
        for s in ("shoulder_f", "shoulder_b"):
            J[s] = J["chest"] + rot(sp) @ (R[s] - R["chest"])
        # hammer arm (IK) + rigid hammer
        af = p["arm_f"]
        hand_t = J["shoulder_f"] + rot(sp) @ polar(af["reach"], af["dir"])
        elbow, cl = ik2(J["shoulder_f"], hand_t, self.L["upperarm_f"], self.L["forearm_f"], self.side_arm)
        if cl:
            self.flags.append((f, "arm_f reach clamped"))
        J["elbow_f"] = elbow
        J["hand_f"] = elbow + (hand_t - elbow) / np.linalg.norm(hand_t - elbow) * self.L["forearm_f"]
        ham_angle = sp + af["hammer"]
        Rh = rot(ham_angle)
        H = {k: J["hand_f"] + Rh @ np.array(v, float) for k, v in self.hammer["points"].items()}
        H["grip"] = J["hand_f"] + Rh @ np.array(self.hammer["grip_point"], float)
        shape = {k: np.array([J["hand_f"] + Rh @ np.array(q, float) for q in v]) for k, v in self.hammer["shape"].items()}
        # free arm (FK)
        ab = p["arm_b"]
        J["elbow_b"] = J["shoulder_b"] + rot(sp + ab["shoulder"]) @ (R["elbow_b"] - R["shoulder_b"])
        J["hand_b"] = J["elbow_b"] + rot(sp + ab["shoulder"] + ab["elbow"]) @ (R["hand_b"] - R["elbow_b"])
        # legs (IK to planted / stepping feet)
        lift_px = self.m.get("step", {}).get("lift_px", 12)
        for leg, foot, side in (("k", "foot_k", self.side_k), ("f", "foot_f", self.side_f)):
            hip = J["pelvis"] + (R["hip_" + leg] - R["pelvis"])
            dx = p["feet"][foot][0]
            lift = lift_px * math.sin(math.pi * steps[foot]) if foot in steps else 0.0
            ank_t = R["ankle_" + leg] + np.array([dx, -lift])
            knee, cl = ik2(hip, ank_t, self.L["thigh_" + leg], self.L["shin_" + leg], side)
            if cl:
                self.flags.append((f, f"leg {leg} overextended"))
            J["hip_" + leg] = hip
            J["knee_" + leg] = knee
            J["ankle_" + leg] = knee + (ank_t - knee) / np.linalg.norm(ank_t - knee) * self.L["shin_" + leg]
        return {"J": J, "H": H, "shape": shape, "ham_angle": ham_angle, "pose": p}

    def com(self, fr):
        J, H = fr["J"], fr["H"]
        tot, acc = 0.0, np.zeros(2)
        for b, v in self.s["bones"].items():
            w = self.s["masses"].get(b, 0.0)
            acc += w * (J[v["from"]] + J[v["to"]]) / 2
            tot += w
        w = self.s["masses"].get("hammer", 0.0)
        acc += w * (H["grip"] + H["head"]) / 2
        tot += w
        return acc / tot


def phase_of(motion, f):
    for ph in motion["phases"]:
        if ph["start"] <= f < ph["end"]:
            return ph["name"]
    return motion["phases"][-1]["name"]


# ------------------------------------------------------------------ checks

def run_checks(sol, frames):
    s, m = sol.s, sol.m
    acc = m["acceptance"]
    res = {}
    # bone lengths
    dev = 0.0
    for fr in frames:
        for b, v in s["bones"].items():
            dev = max(dev, abs(float(np.linalg.norm(fr["J"][v["to"]] - fr["J"][v["from"]])) - sol.L[b]))
    res["bone_length_dev_px"] = (round(dev, 4), dev <= acc["bone_length_dev_px"])
    # grip
    g = max(float(np.linalg.norm(fr["H"]["grip"] - fr["J"]["hand_f"])) for fr in frames)
    res["grip_error_px"] = (round(g, 4), g <= acc["grip_error_px"])
    # rigid hammer: head-butt distance constant, one instance
    lens = [float(np.linalg.norm(fr["H"]["head"] - fr["H"]["butt"])) for fr in frames]
    res["hammer_rigid_dev_px"] = (round(max(lens) - min(lens), 4), max(lens) - min(lens) < 0.01)
    res["hammer_instances"] = (1, s["attachments"]["hammer"]["count"] == 1)
    # foot slide while planted
    worst = 0.0
    for c in m["constraints"]:
        if c["type"] != "contact":
            continue
        joint = s["contacts"][c["contact"]]["joint"]
        spans = c["frames"] if isinstance(c["frames"][0], list) else [c["frames"]]
        for a, b in spans:
            pts = np.array([frames[f]["J"][joint] for f in range(a, min(b, len(frames)))])
            if len(pts):
                worst = max(worst, float(np.abs(pts - pts[0]).max()))
    res["foot_slide_px"] = (round(worst, 3), worst <= acc["foot_slide_px"])
    # centre of mass: weight transfer
    com = np.array([sol.com(fr) for fr in frames])
    ph = {p["name"]: p for p in m["phases"]}
    idle_x = com[0, 0]
    wind_min = com[ph["windup"]["start"]:ph["windup"]["end"], 0].min()
    imp = [e for e in m["events"] if e["name"] == "impact"][0]["frame"]
    res["com_back_in_windup_px"] = (round(float(idle_x - wind_min), 1), idle_x - wind_min >= acc["com_back_in_windup_px"])
    res["com_forward_at_impact_px"] = (round(float(com[imp, 0] - idle_x), 1), com[imp, 0] - idle_x >= acc["com_forward_at_impact_px"])
    # support polygon (between the two feet's toe and heel x), report frames outside
    out = []
    for f, fr in enumerate(frames):
        xs = []
        for c, spec in s["contacts"].items():
            a = fr["J"][spec["joint"]]
            xs += [a[0] + spec["toe"][0], a[0] + spec["heel"][0]]
        if not (min(xs) - 4 <= com[f, 0] <= max(xs) + 4):
            out.append(f)
    res["com_outside_support_frames"] = (out, True)
    # swing monotonic, anticipation opposite, follow-through overshoot
    ang = np.array([fr["ham_angle"] for fr in frames])
    sw = ang[ph["swing"]["start"]:ph["swing"]["end"] + 1]
    res["swing_hammer_angle_monotonic"] = (bool(np.all(np.diff(sw) >= -1e-6)), bool(np.all(np.diff(sw) >= -1e-6)))
    wu = ang[ph["windup"]["start"]:ph["windup"]["end"] + 1]
    res["anticipation_opposite"] = (round(float(wu[-1] - wu[0]), 1), (wu[-1] - wu[0]) < 0 and (sw[-1] - sw[0]) > 0)
    ft = ang[ph["follow_through"]["start"]:ph["follow_through"]["end"] + 1]
    over = float(ft.max() - ang[imp])
    res["follow_through_overshoot_deg"] = (round(over, 1), over >= acc["follow_through_overshoot_deg"])
    res["solver_flags"] = (sorted(set(x[1] for x in sol.flags)), len(sol.flags) == 0)
    return res, com, ang


# ------------------------------------------------------------------ render

BG = (27, 32, 38)
INK = (26, 20, 38)


def draw_pose(d, fr, s, k, off, col_body=(150, 156, 160), col_arm=(178, 184, 188), col_ham=(120, 78, 44), fill=True):
    J = fr["J"]
    T = lambda p: (float(p[0] * k + off[0]), float(p[1] * k + off[1]))

    def capsule(a, b, w, col):
        d.line([T(a), T(b)], fill=INK, width=max(1, int((w + 8) * k)))
        for p in (a, b):
            r = (w + 8) * k / 2
            d.ellipse([T(p)[0] - r, T(p)[1] - r, T(p)[0] + r, T(p)[1] + r], fill=INK)
        if fill:
            d.line([T(a), T(b)], fill=col, width=max(1, int(w * k)))
            for p in (a, b):
                r = w * k / 2
                d.ellipse([T(p)[0] - r, T(p)[1] - r, T(p)[0] + r, T(p)[1] + r], fill=col)
    order = ["upperarm_b", "forearm_b", "thigh_k", "shin_k", "thigh_f", "shin_f", "spine", "neck", "head"]
    for b in order:
        v = s["bones"][b]
        capsule(J[v["from"]], J[v["to"]], v["width"], col_body if b not in ("upperarm_b", "forearm_b") else (120, 126, 130))
    # torso mass
    tor = [J["shoulder_f"], J["shoulder_b"], J["hip_f"], J["hip_k"]]
    d.polygon([T(p) for p in tor], fill=col_body, outline=INK)
    hr = 50 * k
    hx, hy = T(J["head"])
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=col_body, outline=INK, width=max(1, int(4 * k)))
    # feet
    for c, spec in s["contacts"].items():
        a = J[spec["joint"]]
        pts = [a + np.array([spec["heel"][0], -10]), a + np.array([spec["toe"][0], -6]),
               a + np.array([spec["toe"][0], spec["toe"][1]]), a + np.array([spec["heel"][0], spec["heel"][1]])]
        d.polygon([T(p) for p in pts], fill=col_body, outline=INK)
    # hammer (rigid master shape) then the hammer arm on top
    for part in ("handle", "head"):
        d.polygon([T(p) for p in fr["shape"][part]], fill=col_ham, outline=INK)
    capsule(J["shoulder_f"], J["elbow_f"], s["bones"]["upperarm_f"]["width"], col_arm)
    capsule(J["elbow_f"], J["hand_f"], s["bones"]["forearm_f"]["width"], col_arm)


def render_all(sol, frames, com, out):
    s, m = sol.s, sol.m
    k, off = 0.5, (60, 30)
    W, Hh = 560, 620
    imgs = []
    for f, fr in enumerate(frames):
        im = Image.new("RGB", (W, Hh), BG)
        d = ImageDraw.Draw(im)
        gy = 972 * k + off[1] + 9
        d.line([(0, gy), (W, gy)], fill=(60, 66, 74), width=2)
        draw_pose(d, fr, s, k, off)
        c = com[f] * k + np.array(off)
        d.line([(c[0] - 6, c[1]), (c[0] + 6, c[1])], fill=(255, 220, 80), width=2)
        d.line([(c[0], c[1] - 6), (c[0], c[1] + 6)], fill=(255, 220, 80), width=2)
        ph = phase_of(m, f)
        d.rectangle([0, 0, W, 22], fill=PHASE_COL[ph])
        d.text((6, 5), f"f{f:03d}  {ph}", fill=(0, 0, 0))
        for e in m["events"]:
            if e["name"] == "impact" and e["frame"] <= f < e["frame"] + e.get("hitstop_frames", 0):
                d.text((W - 70, 5), "IMPACT", fill=(0, 0, 0))
        imgs.append(im)
    return imgs, k, off


def save_evidence(sol, frames, com, ang, imgs, k, off, out):
    s, m = sol.s, sol.m
    name = m["id"]
    os.makedirs(out, exist_ok=True)
    # GIFs: real time (30 fps from 60) and quarter speed
    imgs[0].save(os.path.join(out, f"{name}.gif"), save_all=True, append_images=imgs[2::2], duration=33, loop=0)
    imgs[0].save(os.path.join(out, f"{name}_slow.gif"), save_all=True, append_images=imgs[1:], duration=66, loop=0)
    # sequential contact sheet: every 2nd frame, in order
    th = [im.resize((im.width * 2 // 5, im.height * 2 // 5)) for im in imgs[::2]]
    cols = 10
    rows = (len(th) + cols - 1) // cols
    S = Image.new("RGB", (cols * th[0].width, rows * th[0].height), (10, 10, 10))
    for i, t in enumerate(th):
        S.paste(t, ((i % cols) * t.width, (i // cols) * t.height))
    S.save(os.path.join(out, f"{name}_sheet.png"))
    # trajectories with onion-skinned key poses
    T = Image.new("RGB", (560, 620), BG)
    d = ImageDraw.Draw(T)
    gy = 972 * k + off[1] + 9
    d.line([(0, gy), (560, gy)], fill=(60, 66, 74), width=2)
    for key in m["keys"]:
        f = key["frame"]
        layer = Image.new("RGB", T.size, BG)
        dl = ImageDraw.Draw(layer)
        draw_pose(dl, frames[f], s, k, off)
        T = Image.blend(T, layer, 0.18)
    d = ImageDraw.Draw(T)
    paths = {"hammer head": ([fr["H"]["head"] for fr in frames], None),
             "hand": ([fr["J"]["hand_f"] for fr in frames], (230, 230, 230)),
             "COM": (list(com), (255, 220, 80))}
    for label, (pts, colr) in paths.items():
        P = [(float(p[0] * k + off[0]), float(p[1] * k + off[1])) for p in pts]
        for i in range(len(P) - 1):
            c = PHASE_COL[phase_of(m, i)] if colr is None else colr
            d.line([P[i], P[i + 1]], fill=c, width=3 if colr is None else 2)
        for i in range(0, len(P), 2):
            c = PHASE_COL[phase_of(m, i)] if colr is None else colr
            d.ellipse([P[i][0] - 2, P[i][1] - 2, P[i][0] + 2, P[i][1] + 2], fill=c)
    imp = [e for e in m["events"] if e["name"] == "impact"][0]["frame"]
    hp = frames[imp]["H"]["head"] * k + np.array(off)
    d.ellipse([hp[0] - 9, hp[1] - 9, hp[0] + 9, hp[1] + 9], outline=(235, 70, 60), width=3)
    y = 6
    for ph, c in PHASE_COL.items():
        d.rectangle([6, y, 16, y + 10], fill=c)
        d.text((20, y - 1), ph, fill=(220, 220, 220))
        y += 14
    d.text((330, 6), "white: hand   yellow: COM", fill=(220, 220, 220))
    d.text((330, 20), "phase colours: hammer head", fill=(220, 220, 220))
    T.save(os.path.join(out, f"{name}_trajectories.png"))
    # timing graph
    G = Image.new("RGB", (900, 420), (245, 245, 245))
    d = ImageDraw.Draw(G)
    x0, x1, n = 50, 880, len(frames)
    X = lambda f: x0 + (x1 - x0) * f / (n - 1)
    for ph in m["phases"]:
        c = PHASE_COL[ph["name"]]
        d.rectangle([X(ph["start"]), 20, X(min(ph["end"], n - 1)), 400], fill=tuple(int(v * 0.25 + 245 * 0.75) for v in c))
        d.text((X(ph["start"]) + 2, 4), ph["name"][:10], fill=(60, 60, 60))
    series = {"hammer angle (deg, /2)": ([a / 2 for a in ang], (150, 90, 40)),
              "spine (deg)": ([fr["pose"]["spine"] for fr in frames], (60, 90, 200)),
              "pelvis dx (px, /2)": ([fr["pose"]["pelvis"][0] / 2 for fr in frames], (40, 160, 80)),
              "pelvis dy (px)": ([fr["pose"]["pelvis"][1] for fr in frames], (200, 60, 160)),
              "COM x - idle (px, /2)": ([(c[0] - com[0, 0]) / 2 for c in com], (220, 160, 0))}
    Y = lambda v: 210 - v * 2
    d.line([(x0, Y(0)), (x1, Y(0))], fill=(150, 150, 150))
    ly = 30
    for label, (vals, c) in series.items():
        d.line([(X(f), Y(v)) for f, v in enumerate(vals)], fill=c, width=2)
        d.text((x1 - 190, ly), label, fill=c)
        ly += 13
    d.line([(X(imp), 20), (X(imp), 400)], fill=(235, 70, 60), width=2)
    d.text((X(imp) + 3, 385), "impact", fill=(235, 70, 60))
    G.save(os.path.join(out, f"{name}_timing.png"))
    # silhouettes: idle vs each key, IoU
    def sil(fr):
        im = Image.new("RGB", (560, 620), (0, 0, 0))
        draw_pose(ImageDraw.Draw(im), fr, s, k, off)
        return np.asarray(im).max(-1) > 0
    base = sil(frames[0])
    rows = []
    tiles = []
    for key in m["keys"]:
        f = key["frame"]
        sm = sil(frames[f])
        iou = float((base & sm).sum() / max(1, (base | sm).sum()))
        rows.append((f, phase_of(m, f), round(iou, 3)))
        t = np.zeros((620, 560, 3), np.uint8)
        t[base] = (60, 110, 200)
        t[sm] = (230, 150, 60)
        t[base & sm] = (200, 200, 200)
        tile = Image.fromarray(t).resize((208, 224))
        ImageDraw.Draw(tile).text((4, 4), f"f{f} {phase_of(m, f)} IoU {iou:.2f}", fill=(255, 255, 255))
        tiles.append(tile)
    S = Image.new("RGB", (6 * 208, ((len(tiles) + 5) // 6) * 224))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % 6) * 208, (i // 6) * 224))
    S.save(os.path.join(out, f"{name}_silhouettes.png"))
    # impact thumbnail at 270 px high (the game's enemy display height)
    im = imgs[imp].copy()
    im.resize((int(im.width * 270 / im.height), 270)).save(os.path.join(out, f"{name}_impact_270.png"))
    return rows


def main(structure_path, motion_path, out):
    s = json.load(open(structure_path))
    m = json.load(open(motion_path))
    sol = Solver(s, m)
    frames = [sol.solve(f) for f in range(sol.n)]
    res, com, ang = run_checks(sol, frames)
    imgs, k, off = render_all(sol, frames, com, out)
    sil = save_evidence(sol, frames, com, ang, imgs, k, off, out)
    imp = [e for e in m["events"] if e["name"] == "impact"][0]["frame"]
    iou_imp = [r for r in sil if r[0] == imp][0][2]
    res["impact_silhouette_iou"] = (iou_imp, iou_imp <= m["acceptance"]["impact_silhouette_iou_max"])
    phases = [(p["name"], p["start"], p["end"], p["end"] - p["start"]) for p in m["phases"]]
    report = {"motion": m["id"], "frames": sol.n, "fps": m["fps"], "phases": phases,
              "checks": {k2: {"value": v[0], "pass": bool(v[1])} for k2, v in res.items()},
              "silhouette_iou_vs_idle": sil}
    json.dump(report, open(os.path.join(out, f"{m['id']}_checks.json"), "w"), indent=1, default=str)
    for k2, v in report["checks"].items():
        print(f"{'PASS' if v['pass'] else 'FAIL'}  {k2}: {v['value']}")
    print("silhouette IoU vs idle:", sil)


if __name__ == "__main__":
    main(*sys.argv[1:4])
