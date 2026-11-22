"""Deterministic motion solver, checks and QA renderer, v2 (Board R&D, 2026-11-22; 04-animation-methodology.md).

    python -I -s motion.py <structure.json> <motion.json> <out_dir>

Engine-neutral and character-agnostic: everything about the character (joints, chains, limits, legs, masses,
contacts, attachments, proxy drawing) comes from a structure.v2 file; everything about the movement from a
motion.v2 file. v2 changes after the Board review of v1 (forearm across the face):
  - arms are FK chains (shoulder, elbow, wrist rotate independently; channels are offsets from the rest pose), with
    a shoulder shift (protraction/elevation) channel; no arm IK, no fixed elbow bend side
  - joint limits are configured per joint and checked every frame
  - the rigid weapon hangs on the hand bone by its rest axis (grip = the hand joint)
  - legs stay two-bone IK to their ground contacts (planted feet), knees bend the rest-pose way
Evidence: real-time and slow GIFs, sequential contact sheet, key pose sheet, weapon/joint trajectories, joint-angle
graph with limit bands, bone-length table, skeleton overlay on the artwork, silhouettes, checks.json.
The v1 solver (arm IK) is kept as motion_v1.py: it is method A of the comparison spike.

Supported scope (Board code review of PR #110, 110-04): this solver is validated on ONE structure, the heavy-hammer
benchmark humanoid (data/structure_brute_hammer.json). It assumes a 'trunk' chain (pelvis, chest, ...), legs hanging
off 'pelvis' planted on contacts, and exactly one rigid attachment named 'hammer'. scope_problems() names every
assumption a structure breaks (unsupported: unarmed, sword, quadruped, hovering, flying, depth_3d) and
input_problems() names every malformed field (invalid input); posecheck runs neither the solver nor any structural
rule on such data, so nothing outside the scope can pass by accident. It is not a universal entity solver.
Conventions used by the checks:
  - contacts.<c>.ground_y is the contact joint's height when planted; toe/heel are the contact points relative to
    that joint. The floor is ground_y + the contact points' y (the drawn sole line), not ground_y itself; a structure
    may state ground.line_y instead. The finding names the ground reference used.
  - anatomy.facing ("+x" or "-x") is required for every directional measurement (no silent +x default).
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
BG, INK = (27, 32, 38), (26, 20, 38)
REPRESENTATION = "planar_2d"            # what this solver measures (motion_rules.json vocabularies.representations)


def rot(deg):
    r = math.radians(deg)
    return np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])


def ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def unwrap_series(vals):
    out = [vals[0]]
    for v in vals[1:]:
        out.append(out[-1] + wrap(v - out[-1]))
    return out


def ik2(root, target, l1, l2, side):
    d = target - root
    dist = float(np.linalg.norm(d))
    clamped = False
    lo, hi = abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3
    if dist > hi or dist < lo:
        clamped = True
        dist = min(max(dist, lo), hi)
    u = d / (np.linalg.norm(d) + 1e-9)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))))
    return root + rot(math.degrees(a) * side) @ u * l1, clamped


class Solver:
    def __init__(self, s, m):
        self.s, self.m = s, m
        self.R = {j: np.array(v["rest"], float) for j, v in s["joints"].items()}
        self.L = {b: float(np.linalg.norm(self.R[v["to"]] - self.R[v["from"]])) for b, v in s["bones"].items()}
        self.keys = sorted(m["keys"], key=lambda k: k["frame"])
        self.n = self.keys[-1]["frame"] + 1
        self.chain_rest = {}
        for cname, c in s["chains"].items():
            js = c["joints"]
            dirs = [ang(self.R[js[i + 1]] - self.R[js[i]]) for i in range(len(js) - 1)]
            rel = [None] + [wrap(dirs[i] - dirs[i - 1]) for i in range(1, len(dirs))]
            lens = [float(np.linalg.norm(self.R[js[i + 1]] - self.R[js[i]])) for i in range(len(js) - 1)]
            self.chain_rest[cname] = {"dirs": dirs, "rel": rel, "lens": lens}
        self.leg_side = {}
        for lname, l in s["legs"].items():
            a, b, c = (self.R[j] for j in l["joints"])
            v1, v2 = c - a, b - a
            self.leg_side[lname] = 1 if (v1[0] * v2[1] - v1[1] * v2[0]) > 0 else -1   # rot(+a) turns u toward +cross
        att = s["attachments"]["hammer"]
        self.att = att
        self.obj = s["objects"][att["asset"]]
        hb = s["bones"][att["parent_bone"]]
        self.weapon_offset = att["rest_axis_deg"] - ang(self.R[hb["to"]] - self.R[hb["from"]])
        self.flags = []

    def _flat(self, pose):
        out = []
        def walk(x):
            if isinstance(x, dict):
                for k in sorted(x):
                    walk(x[k])
            elif isinstance(x, list):
                for q in x:
                    walk(q)
            else:
                out.append(float(x))
        walk(pose)
        return out

    def _unflat(self, tmpl, vals):
        it = iter(vals)
        def build(x):
            if isinstance(x, dict):
                return {k: build(x[k]) for k in sorted(x)}
            if isinstance(x, list):
                return [build(q) for q in x]
            return next(it)
        return build(tmpl)

    def _pchip(self):
        """Piecewise PCHIP. A key with "break": true splits the curve (a broken tangent, as at a physical impact):
        the segment before keeps its speed into the key, the segment after starts fresh."""
        if not hasattr(self, "_pc"):
            from scipy.interpolate import PchipInterpolator
            cuts = [0] + [i for i, k in enumerate(self.keys) if k.get("break") and 0 < i < len(self.keys) - 1] + [len(self.keys) - 1]
            segs = []
            for a, b in zip(cuts, cuts[1:]):
                ks = self.keys[a:b + 1]
                fr = np.array([k["frame"] for k in ks], float)
                M = np.array([self._flat(k["pose"]) for k in ks])
                segs.append((fr[0], fr[-1], PchipInterpolator(fr, M, axis=0) if len(ks) > 2 else
                             (lambda x, fr=fr, M=M: M[0] + (M[1] - M[0]) * (x - fr[0]) / (fr[1] - fr[0]))))
            def ev(x):
                for lo, hi, f in segs:
                    if lo <= x <= hi:
                        return f(x)
                return segs[-1][2](segs[-1][1])
            self._pc = ev
        return self._pc

    def channel(self, f):
        if self.m.get("interpolation", "eased") == "pchip":
            ks = self.keys
            pose = self._unflat(ks[0]["pose"], self._pchip()(min(f, ks[-1]["frame"])))
            steps = {}
            if f < ks[-1]["frame"]:
                i = max(j for j in range(len(ks)) if ks[j]["frame"] <= f)
                a, b = ks[i], ks[i + 1]
                u = (f - a["frame"]) / (b["frame"] - a["frame"])
                steps = {c: u for c in a["pose"]["feet"] if a["pose"]["feet"][c][0] != b["pose"]["feet"][c][0]}
            return pose, steps
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
        steps = {c: u for c in a["pose"]["feet"] if a["pose"]["feet"][c][0] != b["pose"]["feet"][c][0]}
        return mix(a["pose"], b["pose"]), steps

    def solve(self, f):
        p, steps = self.channel(f)
        s, R = self.s, self.R
        J, rel, frame_rot = {}, {}, {}
        for cname in ["trunk"] + [c for c in s["chains"] if c != "trunk"]:
            c = s["chains"][cname]
            cr = self.chain_rest[cname]
            offs = p["chains"][cname]
            js = c["joints"]
            if c["base"] == "root":
                J[js[0]] = R[js[0]] + np.array(p["root"], float)
                base_rot = 0.0
            else:
                base_rot = frame_rot[c["base"]]
                shift = np.array(p.get("shift", {}).get(cname, [0, 0]), float) if c.get("shift") else np.zeros(2)
                J[js[0]] = J[c["base"]] + rot(base_rot) @ (R[js[0]] - R[c["base"]] + shift)
            frame_rot[js[0]] = base_rot
            for i in range(len(js) - 1):
                cum = sum(offs[:i + 1])
                d_i = cr["dirs"][i] + base_rot + cum
                J[js[i + 1]] = J[js[i]] + rot(d_i) @ np.array([cr["lens"][i], 0.0])
                frame_rot[js[i + 1]] = base_rot + cum
                rel[f"{cname}.{c['channels'][i]}"] = (cr["rel"][i] + offs[i]) if i > 0 else offs[0]
            if cname == "trunk":
                frame_rot["chest"] = offs[0]
        lift_px = self.m.get("step", {}).get("lift_px", 12)
        for lname, l in s["legs"].items():
            hip_j, knee_j, ank_j = l["joints"]
            hip = J["pelvis"] + (R[hip_j] - R["pelvis"])
            dx = p["feet"][l["contact"]][0]
            lift = lift_px * math.sin(math.pi * steps[l["contact"]]) if l["contact"] in steps else 0.0
            tgt = R[ank_j] + np.array([dx, -lift])
            l1 = float(np.linalg.norm(R[knee_j] - R[hip_j]))
            l2 = float(np.linalg.norm(R[ank_j] - R[knee_j]))
            side = self.leg_side[lname]
            if l.get("bend") in ("+x", "-x"):
                # anatomical preferred bend (knee toward the facing side) wins over a near-straight rest triangle
                want = 1.0 if l["bend"] == "+x" else -1.0
                u = tgt - hip
                for sd in (1, -1):
                    kk, _ = ik2(hip, tgt, l1, l2, sd)
                    cross = u[0] * (kk - hip)[1] - u[1] * (kk - hip)[0]
                    if np.sign(-cross) == want or abs(cross) < 1e-9:
                        side = sd
                        break
            knee, cl = ik2(hip, tgt, l1, l2, side)
            if cl:
                self.flags.append((f, f"{lname} overextended"))
            J[hip_j], J[knee_j] = hip, knee
            J[ank_j] = knee + (tgt - knee) / np.linalg.norm(tgt - knee) * l2
        hb = s["bones"][self.att["parent_bone"]]
        h_ang = ang(J[hb["to"]] - J[hb["from"]]) + self.weapon_offset
        grip = J[self.att["grip_joint"]]
        Rh = rot(h_ang)
        H = {k: grip + Rh @ np.array(v, float) for k, v in self.obj["points"].items()}
        H["grip"] = grip + Rh @ np.array(self.obj["grip_point"], float)
        shape = {k: np.array([grip + Rh @ np.array(q, float) for q in v]) for k, v in self.obj["shape"].items()}
        return {"J": J, "H": H, "shape": shape, "ham_angle": h_ang, "pose": p, "rel": rel}

    def com(self, fr):
        J, H = fr["J"], fr["H"]
        tot, acc = 0.0, np.zeros(2)
        for b, v in self.s["bones"].items():
            w = self.s["masses"].get(b, 0.0)
            acc += w * (J[v["from"]] + J[v["to"]]) / 2
            tot += w
        w = self.s["masses"].get("hammer", 0.0)
        return (acc + w * (H["grip"] + H["head"]) / 2) / (tot + w)


def phase_of(m, f):
    for ph in m["phases"]:
        if ph["start"] <= f < ph["end"]:
            return ph["name"]
    return m["phases"][-1]["name"]


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, float((p - a) @ ab / (ab @ ab))))
    return float(np.linalg.norm(p - (a + t * ab)))


def facing_problem(s):
    """None when anatomy.facing is '+x' or '-x', else why the directional measurements are unknown."""
    f = (s.get("anatomy") or {}).get("facing")
    if f is None:
        return "anatomy.facing is not declared, so a direction in the character frame cannot be measured"
    if f not in ("+x", "-x"):
        return f"anatomy.facing must be '+x' or '-x', got {f!r}"
    return None


def facing_sign(s):
    """+1 when the structure faces +x, -1 when it faces -x (anatomy.facing), None when facing is missing or invalid
    (never a silent +x default). Every directional measurement is taken in the character frame (multiplied by this
    sign), so a mirrored clip gives identical outcomes."""
    if facing_problem(s):
        return None
    f = s["anatomy"]["facing"]
    return 1 if f == "+x" else -1


def ground_reference(s):
    """(line_y or None, info). The floor the structure stands on: structure.ground.line_y when declared, else the
    declared contact points (max over contacts of ground_y + toe/heel y). None (info['reason']) when the floor cannot
    be located: the ground rule is then unknown (unmeasurable), never measured against a guessed line."""
    g = s.get("ground")
    if isinstance(g, dict) and _finite(g.get("line_y")):
        return float(g["line_y"]), {"source": "structure.ground.line_y", "line_y": float(g["line_y"])}
    per = {}
    for name, c in (s.get("contacts") or {}).items():
        pts = [c[k] for k in ("toe", "heel") if isinstance(c.get(k), list) and len(c[k]) == 2]
        if not _finite(c.get("ground_y")) or not pts:
            return None, {"reason": f"contacts.{name} declares no ground_y or no toe/heel points, so the floor cannot "
                                    "be located (or declare ground.line_y)"}
        per[name] = float(c["ground_y"]) + max(float(q[1]) for q in pts)
    if not per:
        return None, {"reason": "the structure declares no contacts and no ground.line_y"}
    return max(per.values()), {"source": "contact points (contacts.<c>.ground_y + toe/heel y)",
                               "line_y": max(per.values()), "per_contact": per}


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def scope_problems(s):
    """Assumptions of this solver the structure breaks (unsupported, not invalid). Empty list = inside the validated
    scope (the heavy-hammer benchmark humanoid). The anatomy-profile requirement (extends humanoid_base) is checked
    by posecheck, which loads the profile."""
    probs = []
    rep = s.get("representation")
    if rep is not None and rep != REPRESENTATION:
        probs.append(f"representation {rep!r}: only {REPRESENTATION!r} has a solver")
    chains = s.get("chains") if isinstance(s.get("chains"), dict) else {}
    tr = chains.get("trunk") or {}
    if tr.get("base") != "root" or list(tr.get("joints", []))[:2] != ["pelvis", "chest"]:
        probs.append("no humanoid trunk: the solver needs chain 'trunk' with base 'root' and joints pelvis, chest, ...")
    if not s.get("legs") or not s.get("contacts"):
        probs.append("no legs or contacts: hovering, flying or legless entities are not supported (biped planted on contacts only)")
    atts = s.get("attachments") or {}
    if list(atts) != ["hammer"]:
        probs.append(f"attachments {sorted(atts)}: the solver supports exactly one rigid attachment named 'hammer' "
                     "(unarmed, other weapons and several attachments are not supported)")
    return probs


def input_problems(s, m):
    """Malformed fields of an in-scope structure and its motion, each named (invalid input). Checked before solving,
    so the solver only ever sees well-formed data; there is no blanket exception handler around it."""
    probs = []

    def bad(field, why):
        probs.append(f"{field}: {why}")

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, float) and not math.isfinite(x):
            bad(path, f"non-finite number {x}")
    walk(s, "structure")
    walk(m, "motion")
    J, B = s.get("joints") or {}, s.get("bones") or {}
    for j, v in J.items():
        r = v.get("rest") if isinstance(v, dict) else None
        if not (isinstance(r, list) and len(r) == 2 and all(_finite(q) for q in r)):
            bad(f"structure.joints.{j}.rest", "must be two finite numbers")
    for b, v in B.items():
        for e in ("from", "to"):
            if v.get(e) not in J:
                bad(f"structure.bones.{b}.{e}", f"joint {v.get(e)!r} does not exist")
    for c, v in (s.get("chains") or {}).items():
        js = v.get("joints", [])
        miss = [j for j in js if j not in J]
        if miss or len(js) < 2:
            bad(f"structure.chains.{c}.joints", f"needs two or more existing joints (missing {miss})")
        if len(v.get("channels", [])) != max(0, len(js) - 1):
            bad(f"structure.chains.{c}.channels", "needs one channel per bone of the chain")
        if v.get("base") != "root" and v.get("base") not in J:
            bad(f"structure.chains.{c}.base", f"joint {v.get('base')!r} does not exist")
    for name, c in (s.get("contacts") or {}).items():
        if c.get("joint") not in J:
            bad(f"structure.contacts.{name}.joint", f"joint {c.get('joint')!r} does not exist")
        for k in ("toe", "heel"):
            if not (isinstance(c.get(k), list) and len(c[k]) == 2 and all(_finite(q) for q in c[k])):
                bad(f"structure.contacts.{name}.{k}", "must be two finite numbers (contact point relative to the joint)")
    for name, l in (s.get("legs") or {}).items():
        if len(l.get("joints", [])) != 3 or any(j not in J for j in l.get("joints", [])):
            bad(f"structure.legs.{name}.joints", "needs three existing joints (hip, knee, ankle)")
        if l.get("contact") not in (s.get("contacts") or {}):
            bad(f"structure.legs.{name}.contact", f"contact {l.get('contact')!r} does not exist")
        face = (s.get("anatomy") or {}).get("facing")
        if face in ("+x", "-x") and l.get("bend") in ("+x", "-x") and l["bend"] != face:
            bad(f"structure.legs.{name}.bend", f"{l['bend']!r} contradicts anatomy.facing {face!r} (a humanoid knee "
                                               "bends toward the facing side)")
    att = (s.get("attachments") or {}).get("hammer")
    if att is not None:
        obj = (s.get("objects") or {}).get(att.get("asset"))
        if obj is None:
            bad("structure.attachments.hammer.asset", f"object {att.get('asset')!r} does not exist")
        else:
            pts = obj.get("points") or {}
            for k in ("head", "butt"):
                if k not in pts:
                    bad(f"structure.objects.{att.get('asset')}.points.{k}", "missing (the checks measure the weapon head and butt)")
            if not obj.get("shape"):
                bad(f"structure.objects.{att.get('asset')}.shape", "missing")
        if att.get("parent_bone") not in B:
            bad("structure.attachments.hammer.parent_bone", f"bone {att.get('parent_bone')!r} does not exist")
        if att.get("grip_joint") not in J:
            bad("structure.attachments.hammer.grip_joint", f"joint {att.get('grip_joint')!r} does not exist")
        if not _finite(att.get("rest_axis_deg")):
            bad("structure.attachments.hammer.rest_axis_deg", "must be a finite number")
    keys = m.get("keys")
    if not isinstance(keys, list) or len(keys) < 2:
        bad("motion.keys", "needs two or more keys")
        return probs
    frames = [k.get("frame") for k in keys]
    if not all(isinstance(f, int) and not isinstance(f, bool) and f >= 0 for f in frames) or len(set(frames)) != len(frames):
        bad("motion.keys[].frame", "frames must be distinct non-negative integers")
        return probs
    n = max(frames) + 1
    interp = m.get("interpolation", "eased")
    if interp not in ("eased", "pchip"):
        bad("motion.interpolation", f"{interp!r} is not 'eased' or 'pchip'")
    last = max(frames)
    for i, k in enumerate(keys):
        p = k.get("pose") or {}
        if not (isinstance(p.get("root"), list) and len(p["root"]) == 2):
            bad(f"motion.keys[{i}].pose.root", "must be [dx, dy]")
        for c, v in (s.get("chains") or {}).items():
            vals = (p.get("chains") or {}).get(c)
            if not (isinstance(vals, list) and len(vals) == len(v.get("channels", []))):
                bad(f"motion.keys[{i}].pose.chains.{c}", f"needs {len(v.get('channels', []))} channel values")
        for l in (s.get("legs") or {}).values():
            f = (p.get("feet") or {}).get(l.get("contact"))
            if not (isinstance(f, list) and len(f) == 2):
                bad(f"motion.keys[{i}].pose.feet.{l.get('contact')}", "must be [dx, dy]")
        if interp == "eased" and k.get("frame") != last and k.get("ease") not in EASE:
            bad(f"motion.keys[{i}].ease", f"{k.get('ease')!r} is not one of {sorted(EASE)}")
    for i, ph in enumerate(m.get("phases", [])):
        a, b = ph.get("start"), ph.get("end")
        # Empty phases (start == end) are rejected: no schema field declares a phase optional and the measurements
        # (e.g. min() over the windup interval in run_checks) need at least one frame (Board review 2026-11-23).
        if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= n):
            bad(f"motion.phases[{i}] ({ph.get('name')})",
                f"range [{a}, {b}) must satisfy 0 <= start < end <= {n} (empty phases are not supported)")
    for i, e in enumerate(m.get("events", [])):
        f = e.get("frame")
        if not (isinstance(f, int) and 0 <= f < n):
            bad(f"motion.events[{i}].frame ({e.get('name')})", f"{f!r} is outside the clip [0, {n - 1}]")
    for i, c in enumerate(m.get("constraints", [])):
        if c.get("type") != "contact":
            continue
        if c.get("contact") not in (s.get("contacts") or {}):
            bad(f"motion.constraints[{i}].contact", f"contact {c.get('contact')!r} does not exist in the structure")
        fr = c.get("frames")
        spans = fr if isinstance(fr, list) and fr and isinstance(fr[0], list) else [fr]
        for sp in spans:
            if not (isinstance(sp, list) and len(sp) == 2 and all(isinstance(q, int) for q in sp) and 0 <= sp[0] < sp[1] <= n):
                bad(f"motion.constraints[{i}].frames", f"span {sp!r} must be [start, end) inside the clip (0..{n})")
    return probs


def run_checks(sol, frames, thresholds=None):
    """Raw measurements, keyed by quantity. Each entry: value, ok (True/False, or None when the measurement or its
    threshold is missing), reason (why ok is None), threshold. No threshold has a default: a missing value gives
    ok=None (unknown), never a heavy-hammer number. thresholds: the effective values from rules.resolve_acceptance
    (registry-owned for structural invariants; the motion can only tighten them); resolved here when None.
    Classification (pass/fail/warn/unknown/not_applicable) happens in posecheck through rules.py."""
    s, m = sol.s, sol.m
    if thresholds is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import rules
        thresholds = rules.resolve_acceptance(m.get("acceptance"), m.get("category"), motion_id=m.get("id"))["thresholds"]
    acc = thresholds
    face = facing_sign(s)
    no_face = facing_problem(s)
    res = {}

    def put(name, value, ok, reason=None, threshold=None):
        res[name] = {"value": value, "ok": None if ok is None else bool(ok), "reason": reason, "threshold": threshold}

    def thr(key):
        return acc.get(key)

    def missing(key):
        return f"threshold {key} missing (no default)"

    ph = {p["name"]: p for p in m.get("phases", [])}
    ev = {e["name"]: e["frame"] for e in m.get("events", [])}
    imp = ev.get("impact")
    n = len(frames)
    lens = {b: [float(np.linalg.norm(fr["J"][v["to"]] - fr["J"][v["from"]])) for fr in frames] for b, v in s["bones"].items()}
    table = {b: {"rest": round(sol.L[b], 2), "min": round(min(v), 2), "max": round(max(v), 2)} for b, v in lens.items()}
    dev = max(max(abs(x - sol.L[b]) for x in v) for b, v in lens.items())
    t = thr("bone_length_dev_px")
    put("bone_length_dev_px", round(dev, 4), None if t is None else dev <= t, None if t is not None else missing("bone_length_dev_px"), t)
    g = max(float(np.linalg.norm(fr["H"]["grip"] - fr["J"][sol.att["grip_joint"]])) for fr in frames)
    t = thr("grip_error_px")
    put("grip_error_px", round(g, 4), None if t is None else g <= t, None if t is not None else missing("grip_error_px"), t)
    hl = [float(np.linalg.norm(fr["H"]["head"] - fr["H"]["butt"])) for fr in frames]
    t = thr("weapon_rigid_dev_px")
    put("weapon_rigid_dev_px", round(max(hl) - min(hl), 4), None if t is None else max(hl) - min(hl) <= t,
        None if t is not None else missing("weapon_rigid_dev_px"), t)
    att = s.get("attachments", {}).get("hammer", {})
    probs = [p for p, bad in (("asset missing", att.get("asset") not in s.get("objects", {})),
                              ("parent bone missing", att.get("parent_bone") not in s["bones"]),
                              ("grip joint missing", att.get("grip_joint") not in s["joints"]),
                              (f"declared count {att.get('count')} != 1", att.get("count") != 1)) if bad]
    put("attachment", {"count": att.get("count"), "problems": probs}, not probs, threshold="count == 1, parts exist")
    # 2D rig limits declared by the structure (rel2d wrapped to (-180, 180], character frame); channels without a
    # limit are reported, not free
    lim2d = {k: v for k, v in s.get("joint_limits", {}).items() if k != "note"}
    per = {}
    for ch in (frames[0]["rel"] if frames else {}):
        if face is None:
            per[ch] = {"ok": None, "reason": no_face, "value": None}
            continue
        vals = [face * wrap(frames[f]["rel"][ch]) for f in range(n)]
        if ch not in lim2d:
            per[ch] = {"ok": None, "reason": "no 2D joint limit declared for this channel", "value": [round(float(min(vals)), 1), round(float(max(vals)), 1)]}
            continue
        lo, hi = lim2d[ch]
        bad = [f for f, v in enumerate(vals) if not lo <= v <= hi]
        per[ch] = {"ok": not bad, "value": [round(float(min(vals)), 1), round(float(max(vals)), 1)], "frames": bad[:6], "threshold": [lo, hi]}
    put("joint_limits_2d", per, all(v["ok"] for v in per.values()) if per and all(v["ok"] is not None for v in per.values()) else None,
        None if per and all(v["ok"] is not None for v in per.values()) else "some channels have no declared 2D limit")
    el = [fr["rel"]["arm_f.elbow"] for fr in frames] if frames and "arm_f.elbow" in frames[0]["rel"] else None
    t = thr("elbow_range_min_deg")
    if el is None:
        put("elbow_range_deg", None, None, "no channel arm_f.elbow")
    else:
        put("elbow_range_deg", [round(float(min(el)), 1), round(float(max(el)), 1)], None if t is None else max(el) - min(el) >= t,
            None if t is not None else missing("elbow_range_min_deg"), t)
    # KB hammer rule 3: the elbow is most bent at the top of the wind-up (window: last 8 frames of the wind-up)
    t = thr("windup_elbow_flex_deg")
    if "windup" not in ph or el is None:
        put("windup_elbow_flex_deg", None, None, "missing phase 'windup' or channel arm_f.elbow")
    else:
        lo_f, hi_f = max(0, ph["windup"]["end"] - 8), min(n - 1, ph["windup"]["end"])
        wtop = max(abs(wrap(frames[f]["rel"]["arm_f.elbow"])) for f in range(lo_f, hi_f + 1))
        put("windup_elbow_flex_deg", round(wtop, 1), None if t is None else t[0] <= wtop <= t[1],
            None if t is not None else missing("windup_elbow_flex_deg"), t)
    t = thr("impact_elbow_interior_min_deg")
    if imp is None or el is None:
        put("impact_elbow_interior_deg", None, None, "missing event 'impact' or channel arm_f.elbow")
    else:
        interior = 180 - abs(wrap(frames[imp]["rel"]["arm_f.elbow"]))
        put("impact_elbow_interior_deg", round(interior, 1), None if t is None else interior >= t,
            None if t is not None else missing("impact_elbow_interior_min_deg"), t)
    worst, spans_seen = 0.0, 0
    for c in m.get("constraints", []):
        if c["type"] != "contact":
            continue
        joint = s["contacts"][c["contact"]]["joint"]
        spans = c["frames"] if isinstance(c["frames"][0], list) else [c["frames"]]
        for a, b in spans:
            pts = np.array([frames[f]["J"][joint] for f in range(a, min(b, n))])
            if len(pts):
                spans_seen += 1
                worst = max(worst, float(np.abs(pts - pts[0]).max()))
    t = thr("foot_slide_px")
    if not spans_seen:
        put("foot_slide_px", None, None, "no contact constraint declared", t)
    else:
        put("foot_slide_px", round(worst, 3), None if t is None else worst <= t, None if t is not None else missing("foot_slide_px"), t)
    res["foot_slide_px"]["declared_contacts"] = spans_seen
    # weapon vs ground (ported from the R&D copy via review, KA-BD-11): lowest point of the rigid weapon shape vs the
    # floor the structure declares (its contact points, or ground.line_y; ground_y alone is the ankle height, review
    # of PR #110 H3). Planar model: all parts lie in one plane, so this is exact in that model.
    gy, g_info = ground_reference(s)
    t = thr("ground_penetration_tol_px")
    if gy is None:
        put("weapon_ground_penetration_px", {"ground_reference": g_info}, None, g_info["reason"])
    else:
        low = [max(float(p[1]) for poly in fr["shape"].values() for p in poly) - gy for fr in frames]
        if t is None:
            put("weapon_ground_penetration_px", {"max_below_ground": round(max(low), 1), "ground_reference": g_info},
                None, missing("ground_penetration_tol_px"))
        else:
            pen = [f for f, v in enumerate(low) if v > t]
            put("weapon_ground_penetration_px", {"max_below_ground": round(max(low), 1), "first_frames": pen[:6],
                                                 "frame_count": len(pen), "frame_span": [pen[0], pen[-1]] if pen else None,
                                                 "ground_reference": g_info},
                not pen, threshold=t)
    com = np.array([sol.com(fr) for fr in frames])
    # COM along the facing (character frame): positive = forward
    fwd = face * com[:, 0] if face is not None else None
    t = thr("com_back_in_windup_px")
    if "windup" not in ph:
        put("com_back_in_windup_px", None, None, "missing phase 'windup'")
    elif fwd is None:
        put("com_back_in_windup_px", None, None, no_face)
    else:
        back = float(fwd[0] - fwd[ph["windup"]["start"]:ph["windup"]["end"]].min())
        put("com_back_in_windup_px", round(back, 1), None if t is None else back >= t, None if t is not None else missing("com_back_in_windup_px"), t)
    t = thr("com_forward_at_impact_px")
    if imp is None:
        put("com_forward_at_impact_px", None, None, "missing event 'impact'")
    elif fwd is None:
        put("com_forward_at_impact_px", None, None, no_face)
    else:
        f_imp = float(fwd[imp] - fwd[0])
        put("com_forward_at_impact_px", round(f_imp, 1), None if t is None else f_imp >= t, None if t is not None else missing("com_forward_at_impact_px"), t)
    out = []
    for f, fr in enumerate(frames):
        xs = []
        for c, spec in s["contacts"].items():
            a = fr["J"][spec["joint"]]
            xs += [a[0] + spec["toe"][0], a[0] + spec["heel"][0]]
        if not (min(xs) - 4 <= com[f, 0] <= max(xs) + 4):
            out.append(f)
    put("com_outside_support_frames", out, len(out) == 0, threshold="x-span of contacts +-4 px")
    # weapon angle in the character frame (facing * unwrapped screen angle): positive = turning with the strike
    hang = np.array(unwrap_series([fr["ham_angle"] for fr in frames]))
    hc_ang = face * hang if face is not None else None
    if "swing" not in ph:
        put("swing_weapon_angle_monotonic", None, None, "missing phase 'swing'")
    elif hc_ang is None:
        put("swing_weapon_angle_monotonic", None, None, no_face)
    else:
        sw = hc_ang[ph["swing"]["start"]:ph["swing"]["end"] + 1]
        mono = bool(np.all(np.diff(sw) >= -1e-6))
        put("swing_weapon_angle_monotonic", mono, mono, threshold="non-decreasing along the facing")
    if "windup" not in ph or "swing" not in ph:
        put("windup_opposite_to_swing", None, None, "missing phase 'windup' or 'swing'")
    elif hc_ang is None:
        put("windup_opposite_to_swing", None, None, no_face)
    else:
        wu = hc_ang[ph["windup"]["start"]:ph["windup"]["end"] + 1]
        sw = hc_ang[ph["swing"]["start"]:ph["swing"]["end"] + 1]
        put("windup_opposite_to_swing", round(float(wu[-1] - wu[0]), 1), (wu[-1] - wu[0]) < 0 < (sw[-1] - sw[0]),
            threshold="windup turn < 0 < swing turn")
    t = thr("follow_through_overshoot_deg")
    if "follow_through" not in ph or imp is None:
        put("follow_through_overshoot_deg", None, None, "missing phase 'follow_through' or event 'impact'")
    elif hc_ang is None:
        put("follow_through_overshoot_deg", None, None, no_face)
    else:
        ft = hc_ang[ph["follow_through"]["start"]:ph["follow_through"]["end"] + 1]
        over = float(ft.max() - hc_ang[imp])
        put("follow_through_overshoot_deg", round(over, 1), None if t is None else over >= t,
            None if t is not None else missing("follow_through_overshoot_deg"), t)
    hc = s.get("proxy", {}).get("head_circle")
    # face zone = the lower half of the head circle (eyes to chin), a 2D screen-overlap proxy (no depth)
    def face_hit(fr):
        c = fr["J"][hc["joint"]]
        a, b = fr["J"]["elbow_f"], fr["J"]["wrist_f"]
        for t_ in np.linspace(0, 1, 21):
            q = a + t_ * (b - a)
            if np.linalg.norm(q - c) < hc["r"] * 0.9 and q[1] > c[1] - 0.1 * hc["r"]:
                return True
        return False
    if not hc or "impact" not in ph or "recovery" not in ph or "elbow_f" not in s["joints"] or "wrist_f" not in s["joints"]:
        put("forearm_crosses_face_zone_frames", None, None, "missing head circle, joints elbow_f/wrist_f, or phases impact/recovery")
    else:
        cross = [f for f, fr in enumerate(frames) if ph["impact"]["start"] <= f < ph["recovery"]["end"] and face_hit(fr)]
        put("forearm_crosses_face_zone_frames", cross[:8], len(cross) == 0, threshold="none in impact.start..recovery.end")
    hp = np.array([fr["H"]["head"] for fr in frames])
    v = np.linalg.norm(np.diff(hp, axis=0), axis=1)
    # weapon still fast at contact (KB hammer rule 8: tip speed at contact >= 80% of the swing's peak)
    t = thr("contact_speed_ratio_min")
    if "swing" not in ph or imp is None or imp <= ph["swing"]["start"]:
        put("contact_speed_ratio", None, None, "missing phase 'swing' or event 'impact' after it")
    else:
        peak = float(v[ph["swing"]["start"]:imp].max())
        ratio = float(v[imp - 1]) / peak if peak else 0.0
        put("contact_speed_ratio", round(ratio, 2), None if t is None else ratio >= t, None if t is not None else missing("contact_speed_ratio_min"), t)
    # a pop = one frame much faster than BOTH neighbours (a spike), above an imperceptibility floor
    fl, pr = thr("velocity_floor_px"), thr("pop_ratio")
    if fl is None or pr is None:
        put("weapon_velocity_pops", None, None, missing("velocity_floor_px / pop_ratio"))
    else:
        jumps = [(i, round(float(v[i]), 1)) for i in range(1, len(v) - 1) if v[i] > fl and v[i] > pr * max(v[i - 1], v[i + 1])]
        put("weapon_velocity_pops", jumps[:6], len(jumps) == 0, threshold=[fl, pr])
    put("solver_flags", sorted(set(x[1] for x in sol.flags)), len(sol.flags) == 0, threshold="no flags")
    return res, com, hang, table


def draw_pose(d, fr, s, k, off, colors=None):
    J = fr["J"]
    T = lambda q: (float(q[0] * k + off[0]), float(q[1] * k + off[1]))
    c = colors or {"body": (150, 156, 160), "back": (118, 124, 128), "front": (182, 188, 192), "ham": (120, 78, 44)}

    def capsule(a, b, w, col):
        for width, cc in (((w + 8) * k, INK), (w * k, col)):
            d.line([T(a), T(b)], fill=cc, width=max(1, int(width)))
            for q in (a, b):
                r = width / 2
                d.ellipse([T(q)[0] - r, T(q)[1] - r, T(q)[0] + r, T(q)[1] + r], fill=cc)
    pr = s["proxy"]
    for b in pr["back"]:
        v = s["bones"][b]; capsule(J[v["from"]], J[v["to"]], v["width"], c["back"])
    for b in pr["body"]:
        v = s["bones"][b]; capsule(J[v["from"]], J[v["to"]], v["width"], c["body"])
    d.polygon([T(J[j]) for j in pr["torso"]], fill=c["body"], outline=INK)
    hc = pr["head_circle"]
    hx, hy = T(J[hc["joint"]]); hr = hc["r"] * k
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=c["body"], outline=INK, width=max(1, int(4 * k)))
    for cn, spec in s["contacts"].items():
        a = J[spec["joint"]]
        pts = [a + np.array([spec["heel"][0], -10]), a + np.array([spec["toe"][0], -6]),
               a + np.array([spec["toe"][0], spec["toe"][1]]), a + np.array([spec["heel"][0], spec["heel"][1]])]
        d.polygon([T(q) for q in pts], fill=c["body"], outline=INK)
    for part in ("handle", "head"):
        d.polygon([T(q) for q in fr["shape"][part]], fill=c["ham"], outline=INK)
    for b in pr["front"]:
        v = s["bones"][b]; capsule(J[v["from"]], J[v["to"]], v["width"], c["front"])


def save_all(sol, frames, com, hang, table, res, out, art_base):
    s, m = sol.s, sol.m
    name = m["id"]
    os.makedirs(out, exist_ok=True)
    k, off, W, Hh = 0.5, (60, 30), 560, 620
    imp = [e for e in m["events"] if e["name"] == "impact"][0]["frame"]      # this renderer draws strike evidence
    ground_y, _ = ground_reference(s)                    # the floor line the ground check uses (None: not drawn)
    imgs = []
    for f, fr in enumerate(frames):
        im = Image.new("RGB", (W, Hh), BG)
        d = ImageDraw.Draw(im)
        if ground_y is not None:
            gy = ground_y * k + off[1]
            d.line([(0, gy), (W, gy)], fill=(60, 66, 74), width=2)
        draw_pose(d, fr, s, k, off)
        for j in s["chains"]["arm_f"]["joints"]:
            x, y = fr["J"][j] * k + np.array(off)
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 90, 90))
        cx, cy = com[f] * k + np.array(off)
        d.line([(cx - 6, cy), (cx + 6, cy)], fill=(255, 220, 80), width=2)
        d.line([(cx, cy - 6), (cx, cy + 6)], fill=(255, 220, 80), width=2)
        ph = phase_of(m, f)
        d.rectangle([0, 0, W, 22], fill=PHASE_COL[ph])
        d.text((6, 5), f"f{f:03d} {ph}  elbow {fr['rel']['arm_f.elbow']:+.0f}  wrist {fr['rel']['arm_f.wrist']:+.0f}  spine {fr['rel']['trunk.spine']:+.0f}", fill=(0, 0, 0))
        imgs.append(im)
    imgs[0].save(os.path.join(out, f"{name}.gif"), save_all=True, append_images=imgs[2::2], duration=33, loop=0)
    imgs[0].save(os.path.join(out, f"{name}_slow.gif"), save_all=True, append_images=imgs[1:], duration=66, loop=0)
    th = [im.resize((im.width * 2 // 5, im.height * 2 // 5)) for im in imgs[::2]]
    cols = 10
    S = Image.new("RGB", (cols * th[0].width, ((len(th) + cols - 1) // cols) * th[0].height), (10, 10, 10))
    for i, t in enumerate(th):
        S.paste(t, ((i % cols) * t.width, (i // cols) * t.height))
    S.save(os.path.join(out, f"{name}_sheet.png"))
    keys = [kk["frame"] for kk in m["keys"]]
    tiles = [imgs[f].resize((280, 310)) for f in keys]
    KS = Image.new("RGB", (6 * 280, ((len(tiles) + 5) // 6) * 310), (10, 10, 10))
    for i, t in enumerate(tiles):
        KS.paste(t, ((i % 6) * 280, (i // 6) * 310))
    KS.save(os.path.join(out, f"{name}_keys.png"))
    T = Image.new("RGB", (W, Hh), BG)
    for kf in keys:
        layer = Image.new("RGB", (W, Hh), BG)
        draw_pose(ImageDraw.Draw(layer), frames[kf], s, k, off)
        T = Image.blend(T, layer, 0.18)
    d = ImageDraw.Draw(T)
    if ground_y is not None:
        gy = ground_y * k + off[1]
        d.line([(0, gy), (W, gy)], fill=(60, 66, 74), width=2)
    paths = {"head": ([fr["H"]["head"] for fr in frames], None), "hand": ([fr["J"]["hand_f"] for fr in frames], (230, 230, 230)),
             "elbow": ([fr["J"]["elbow_f"] for fr in frames], (120, 200, 255)), "com": (list(com), (255, 220, 80))}
    for label, (pts, colr) in paths.items():
        P = [(float(q[0] * k + off[0]), float(q[1] * k + off[1])) for q in pts]
        for i in range(len(P) - 1):
            cc = PHASE_COL[phase_of(m, i)] if colr is None else colr
            d.line([P[i], P[i + 1]], fill=cc, width=3 if colr is None else 2)
        for i in range(0, len(P), 2):
            cc = PHASE_COL[phase_of(m, i)] if colr is None else colr
            d.ellipse([P[i][0] - 2, P[i][1] - 2, P[i][0] + 2, P[i][1] + 2], fill=cc)
    hp = frames[imp]["H"]["head"] * k + np.array(off)
    d.ellipse([hp[0] - 9, hp[1] - 9, hp[0] + 9, hp[1] + 9], outline=(235, 70, 60), width=3)
    y = 6
    for phn, cc in PHASE_COL.items():
        d.rectangle([6, y, 16, y + 10], fill=cc); d.text((20, y - 1), phn, fill=(220, 220, 220)); y += 14
    d.text((330, 6), "weapon head: phase colours", fill=(220, 220, 220))
    d.text((330, 20), "white hand, blue elbow, yellow COM", fill=(220, 220, 220))
    T.save(os.path.join(out, f"{name}_trajectories.png"))
    G = Image.new("RGB", (960, 640), (245, 245, 245))
    d = ImageDraw.Draw(G)
    x0, x1, n = 70, 940, len(frames)
    X = lambda f: x0 + (x1 - x0) * f / (n - 1)
    for phs in m["phases"]:
        cc = PHASE_COL[phs["name"]]
        d.rectangle([X(phs["start"]), 20, X(min(phs["end"], n - 1)), 630], fill=tuple(int(v * 0.22 + 245 * 0.78) for v in cc))
        d.text((X(phs["start"]) + 2, 4), phs["name"][:12], fill=(60, 60, 60))
    lanes = {"arm_f.elbow": ((40, 320), (200, 60, 60)), "arm_f.wrist": ((340, 470), (60, 140, 60)),
             "trunk.spine": ((490, 620), (60, 90, 200))}
    for jn, ((top, bot), cc) in lanes.items():
        lim = s["joint_limits"][jn]
        lo, hi = lim[0] - 20, lim[1] + 20
        Y = lambda v, lo=lo, hi=hi, top=top, bot=bot: bot - (v - lo) / (hi - lo) * (bot - top)
        d.rectangle([x0, Y(lim[1]), x1, Y(lim[0])], outline=(150, 150, 150))
        d.line([(x0, Y(0)), (x1, Y(0))], fill=(190, 190, 190))
        d.line([(X(f), Y(fr["rel"][jn])) for f, fr in enumerate(frames)], fill=cc, width=3)
        d.text((4, top), jn, fill=cc)
        d.text((x0 - 32, Y(lim[1]) - 6), f"{lim[1]}", fill=(120, 120, 120))
        d.text((x0 - 32, Y(lim[0]) - 6), f"{lim[0]}", fill=(120, 120, 120))
    d.line([(X(imp), 20), (X(imp), 630)], fill=(235, 70, 60), width=2)
    d.text((X(imp) + 3, 22), "impact", fill=(235, 70, 60))
    G.save(os.path.join(out, f"{name}_joint_angles.png"))
    art = s.get("artwork")
    if art:
        ap = os.path.join(art_base, art)
        if os.path.isfile(ap):
            a = Image.open(ap).convert("RGBA")
            bgi = Image.new("RGBA", a.size, BG + (255,)); bgi.alpha_composite(a)
            d = ImageDraw.Draw(bgi)
            fr0 = frames[0]
            for b, v in s["bones"].items():
                d.line([tuple(fr0["J"][v["from"]]), tuple(fr0["J"][v["to"]])], fill=(255, 80, 80, 255), width=4)
            for j, q in fr0["J"].items():
                d.ellipse([q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7], fill=(255, 230, 0, 255))
            d.line([tuple(fr0["H"]["butt"]), tuple(fr0["H"]["head"])], fill=(80, 200, 255, 255), width=4)
            g0 = fr0["H"]["grip"]
            d.ellipse([g0[0] - 9, g0[1] - 9, g0[0] + 9, g0[1] + 9], outline=(80, 200, 255, 255), width=3)
            bgi.convert("RGB").resize((416, 608)).save(os.path.join(out, f"{name}_skeleton_overlay.png"))

    def sil(fr):
        im = Image.new("RGB", (W, Hh), (0, 0, 0)); draw_pose(ImageDraw.Draw(im), fr, s, k, off)
        return np.asarray(im).max(-1) > 0
    base = sil(frames[0]); rows = []
    for kf in keys:
        sm = sil(frames[kf]); rows.append((kf, phase_of(m, kf), round(float((base & sm).sum() / max(1, (base | sm).sum())), 3)))
    report = {"motion": m["id"], "frames": sol.n, "fps": m["fps"],
              "phases": [(p["name"], p["start"], p["end"]) for p in m["phases"]],
              "checks": res,
              "note": "raw measurements: ok is None when the value or its acceptance threshold is missing (unknown, never "
                      "a pass). Classification and the verdict come from posecheck.py (rules.py).",
              "bone_lengths": table, "silhouette_iou_vs_idle": rows}
    iou_imp = [r for r in rows if r[0] == imp][0][2]
    t = m.get("acceptance", {}).get("impact_silhouette_iou_max")
    report["checks"]["impact_silhouette_iou"] = {"value": iou_imp, "ok": None if t is None else iou_imp <= t,
                                                 "reason": None if t is not None else "acceptance.impact_silhouette_iou_max missing (no default)",
                                                 "threshold": t}
    json.dump(report, open(os.path.join(out, f"{name}_checks.json"), "w"), indent=1, default=str)
    return report


def main(sp, mp, out):
    s, m = json.load(open(sp)), json.load(open(mp))
    sol = Solver(s, m)
    frames = [sol.solve(f) for f in range(sol.n)]
    res, com, hang, table = run_checks(sol, frames)
    rep = save_all(sol, frames, com, hang, table, res, out, os.path.dirname(os.path.abspath(sp)))
    for kk, v in rep["checks"].items():
        tag = {True: "OK  ", False: "OUT ", None: "UNKN"}[v["ok"]]
        print(f"{tag}  {kk}: {v['value']}" + (f"  ({v['reason']})" if v.get("reason") else ""))
    print("bone lengths:", {b: (t["min"], t["max"]) for b, t in rep["bone_lengths"].items()})


if __name__ == "__main__":
    main(*sys.argv[1:4])
