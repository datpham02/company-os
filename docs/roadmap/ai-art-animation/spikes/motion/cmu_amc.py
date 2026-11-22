"""ASF/AMC reader + 3D forward kinematics (studio code, no new dependency; Board decision K1, 2026-11-22).

Data: CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu) - free for all uses, the data itself may not be
resold even in converted form. Files are read as plain text only.

Math (the ASF/AMC convention): each bone has an axis C (Euler XYZ, degrees) and per-frame rotations M (the bone's
dof values); its global rotation G = G_parent @ C @ M @ C^-1, its end point = start + length * G @ direction.
Euler 'XYZ' here means R = Rz @ Ry @ Rx (static axes), as in the CMU tools.
"""
import math

import numpy as np


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler(xyz_deg):
    x, y, z = np.radians(xyz_deg)
    return rz(z) @ ry(y) @ rx(x)


def read_asf(path):
    lines = [l.strip() for l in open(path, encoding="ascii", errors="replace")]
    bones, hierarchy = {}, {}
    root = {"name": "root", "direction": np.zeros(3), "length": 0.0, "axis": np.zeros(3), "dof": []}
    i = 0
    section = None
    cur = None
    while i < len(lines):
        l = lines[i]
        if l.startswith(":"):
            section = l.split()[0]
            if section == ":root":
                i += 1
                while i < len(lines) and not lines[i].startswith(":"):
                    t = lines[i].split()
                    if t and t[0] == "orientation":
                        root["axis"] = np.array([float(v) for v in t[1:4]])
                    if t and t[0] == "order":
                        root["order"] = t[1:]
                    i += 1
                continue
        elif section == ":bonedata":
            t = l.split()
            if t and t[0] == "begin":
                cur = {"dof": []}
            elif t and t[0] == "end" and cur is not None:
                bones[cur["name"]] = cur
                cur = None
            elif cur is not None and t:
                if t[0] == "name":
                    cur["name"] = t[1]
                elif t[0] == "direction":
                    cur["direction"] = np.array([float(v) for v in t[1:4]])
                elif t[0] == "length":
                    cur["length"] = float(t[1])
                elif t[0] == "axis":
                    cur["axis"] = np.array([float(v) for v in t[1:4]])
                elif t[0] == "dof":
                    cur["dof"] = t[1:]
        elif section == ":hierarchy":
            t = l.split()
            if t and t[0] not in ("begin", "end"):
                for c in t[1:]:
                    hierarchy[c] = t[0]
        i += 1
    bones["root"] = root
    for b in bones.values():
        b["C"] = euler(b["axis"])
        b["Cinv"] = np.linalg.inv(b["C"])
    return bones, hierarchy


def read_amc(path):
    frames, cur = [], None
    for l in open(path, encoding="ascii", errors="replace"):
        t = l.split()
        if not t or l.startswith("#") or l.startswith(":"):
            continue
        if len(t) == 1 and t[0].isdigit():
            cur = {}
            frames.append(cur)
        elif cur is not None:
            cur[t[0]] = [float(v) for v in t[1:]]
    return frames


def fk(bones, hierarchy, frame):
    """Returns {bone: (start, end)} positions for one AMC frame (ASF length units, Y up)."""
    order = ["root"]
    children = {}
    for c, p in hierarchy.items():
        children.setdefault(p, []).append(c)
    q = ["root"]
    while q:
        n = q.pop(0)
        for c in children.get(n, []):
            order.append(c)
            q.append(c)
    G, P = {}, {}
    r = frame["root"]
    root = bones["root"]
    P["root"] = np.array(r[:3])
    G["root"] = root["C"] @ euler(r[3:6]) @ root["Cinv"]
    out = {"root": (P["root"], P["root"])}
    for n in order[1:]:
        b = bones[n]
        p = hierarchy[n]
        rot = np.zeros(3)
        vals = frame.get(n, [])
        for k, d in enumerate(b["dof"]):
            if k < len(vals):
                rot["xyz".index(d[1])] = vals[k]
        G[n] = G[p] @ b["C"] @ euler(rot) @ b["Cinv"]
        start = P[p]
        P[n] = start + b["length"] * (G[n] @ b["direction"])
        out[n] = (start, P[n])
    return out
