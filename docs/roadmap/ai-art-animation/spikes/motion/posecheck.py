"""Action-aware pose and motion validation in three tiers (Board amendment "Functional Anatomy & Biomechanics",
2026-11-22). Character-agnostic: everything comes from an anatomy profile (with inheritance), the structure's
anatomy map and the motion's phases/acceptance.

    python -I -s posecheck.py <structure.json> <motion.json> [out.json]

Tier A  anatomical validity     hierarchy, bone lengths, joint ranges (tier chosen by the structure: clinical /
                                functional / stylized), bend directions, 2D flips only through neutral,
                                reachability (solver flags)
Tier B  biomechanical plausibility   balance per phase, contacts, weight transfer, proximal-to-distal sequencing,
                                grip, self-collision (face zone), scapulohumeral coupling, contact speed
Tier C  action and artistic plausibility   intent checks for the action category (extension at impact, wind-up
                                flexion, anticipation, follow-through, silhouette change) + an explicit list of
                                items that need a human/director judgement on the real-time and slow previews.
Every finding is classed hard / soft / artistic.
"""
import copy
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as mo  # noqa: E402


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_profile(path):
    p = json.load(open(path))
    if p.get("extends"):
        base = load_profile(os.path.join(os.path.dirname(path), p["extends"] + ".json"))
        p = deep_merge(base, {k: v for k, v in p.items() if k not in ("overrides",)})
        p = deep_merge(p, p.get("overrides", {}) if "overrides" not in base else {})
        raw = json.load(open(path))
        if "overrides" in raw:
            p = deep_merge(p, raw["overrides"])
    return p


def angle_between(v, w):
    return math.degrees(math.atan2(v[0] * w[1] - v[1] * w[0], v[0] * w[0] + v[1] * w[1]))


def anatomical_series(sol, frames, s):
    """Anatomical angle series per mapped channel + derived joints."""
    amap = s["anatomy"]["map"]
    out = {}
    for ch, spec in amap.items():
        raw = np.array([fr["rel"][ch] for fr in frames])
        if spec["sign"] == "abs":
            v = np.abs(raw)
        else:
            v = spec["sign"] * (raw - spec.get("zero", 0))
        out[ch] = {"spec": spec, "raw": raw, "anat": v}
    face = 1 if s["anatomy"].get("facing", "+x") == "+x" else -1
    for name, spec in s["anatomy"].get("derived", {}).items():
        J = spec["from"]
        vals, side = [], []
        for fr in frames:
            if spec["movement"] == "flex" and spec["joint"] == "shoulder":
                trunk_down = fr["J"][J[1]] - fr["J"][J[0]]        # chest -> pelvis
                arm = fr["J"][J[3]] - fr["J"][J[2]]
                sgn = angle_between(trunk_down, arm) * -face       # + = forward (facing side), - = behind
                vals.append(sgn)
            else:
                a, b, c = (fr["J"][j] for j in J)
                u, w = a - b, c - b
                interior = abs(angle_between(u, w))
                vals.append(180 - interior)
                # which side of the hip-ankle line is the knee? (+1 = forward, the facing side)
                line = c - a
                cross = line[0] * (b - a)[1] - line[1] * (b - a)[0]
                side.append(np.sign(-cross * face))
        if spec["joint"] == "shoulder":
            # 2D elevation: 0 = hanging, 180 = overhead; front/back is ambiguous near overhead in a side view
            sg = np.array(vals)
            out[name] = {"spec": dict(spec, movement="elevation"), "anat": np.abs(sg), "signed": sg, "side": None}
            continue
        out[name] = {"spec": spec, "anat": np.array(vals), "side": np.array(side) if side else None}
    return out


def validate(sp, mp):
    s, m = json.load(open(sp)), json.load(open(mp))
    prof = load_profile(os.path.join(os.path.dirname(os.path.abspath(sp)), s["anatomy"]["profile"]))
    # character-specific overrides (each must state why)
    for jn, ov in s["anatomy"].get("overrides", {}).items():
        prof["joints"][jn] = deep_merge(prof["joints"].get(jn, {}), {k: v for k, v in ov.items() if k != "why"})
    tier_lim = s["anatomy"].get("limit_tier", prof.get("limit_tier_default", "clinical"))
    sol = mo.Solver(s, m)
    frames = [sol.solve(f) for f in range(sol.n)]
    checks, com, hang, table = mo.run_checks(sol, frames)
    ph = {p["name"]: p for p in m["phases"]}
    imp = [e for e in m["events"] if e["name"] == "impact"][0]["frame"]
    find = []

    def add(tier, cls, cid, ok, value, note=""):
        find.append({"tier": tier, "class": cls, "id": cid, "pass": None if ok is None else bool(ok), "value": value, "note": note})
    # ---------------- Tier A
    parents_ok = all((v["parent"] is None) or (v["parent"] in s["joints"]) for v in s["joints"].values())
    add("A", "hard", "hierarchy", parents_ok, None)
    add("A", "hard", "bone_lengths_constant", checks["bone_length_dev_px"][1], checks["bone_length_dev_px"][0])
    ser = anatomical_series(sol, frames, s)
    for name, d in ser.items():
        jn, mv = d["spec"]["joint"], d["spec"]["movement"]
        rng = prof["joints"].get(jn, {}).get("movements", {}).get(mv, {}).get(tier_lim)
        if rng:
            lo, hi = rng
            bad = [int(f) for f in np.nonzero((d["anat"] < lo - 1e-6) | (d["anat"] > hi + 1e-6))[0]]
            add("A", "hard", f"range:{name}->{jn}.{mv}[{tier_lim}]", not bad,
                [round(float(d["anat"].min()), 1), round(float(d["anat"].max()), 1)], f"allowed {rng}; frames {bad[:5]}")
        if "signed" in d:
            ext_lim = prof["joints"][jn]["movements"]["flex"][tier_lim][0]          # e.g. -75 stylized
            back = [int(i) for i in range(len(d["signed"])) if d["signed"][i] < ext_lim and d["anat"][i] < 150]
            add("A", "soft", f"shoulder_extension_behind:{name}", not back, back[:5],
                f"arm behind the trunk beyond {ext_lim} deg below 150 deg of elevation (above that, front/back is a projection ambiguity)")
        if d["spec"].get("flip_policy") == "through_neutral":
            raw = np.array([mo.wrap(v) for v in d["raw"]])          # a fold flip shows as a jump across +-180
            flips = [int(i) for i in range(1, len(raw)) if np.sign(raw[i]) != np.sign(raw[i - 1]) and
                     min(abs(raw[i]), abs(raw[i - 1])) > 25]
            add("A", "hard", f"no_flip_through_fold:{name}", not flips, flips[:5],
                "a 2D bend may change sign only near straight (axial arm rotation), never by snapping through a fold")
        if d.get("side") is not None and d["spec"].get("bend") == "forward_of_line":
            wrong = [int(i) for i in np.nonzero(d["side"] < 0)[0] if d["anat"][i] > 5]
            add("A", "hard", f"bend_direction:{name}", not wrong, wrong[:5], "knee must stay forward of the hip-ankle line")
    add("A", "hard", "reachability (no clamped IK)", checks["solver_flags"][1], checks["solver_flags"][0])
    # ---------------- Tier B
    add("B", "hard", "ground_contact (foot slide)", checks["foot_slide_px"][1], checks["foot_slide_px"][0])
    add("B", "hard", "grip (weapon on the hand)", checks["grip_error_px"][1] and checks["weapon_rigid_dev_px"][1],
        [checks["grip_error_px"][0], checks["weapon_rigid_dev_px"][0]])
    add("B", "soft", "balance (COM inside support)", checks["com_outside_support_frames"][1], checks["com_outside_support_frames"][0])
    add("B", "soft", "weight_transfer_back_in_windup", checks["com_back_in_windup_px"][1], checks["com_back_in_windup_px"][0])
    add("B", "soft", "weight_transfer_forward_at_impact", checks["com_forward_at_impact_px"][1], checks["com_forward_at_impact_px"][0])
    add("B", "soft", "self_collision_face_zone_held_poses", checks["forearm_crosses_face_zone_frames"][1], checks["forearm_crosses_face_zone_frames"][0])
    add("B", "soft", "contact_speed (no braking before contact)", checks["contact_speed_ratio"][1], checks["contact_speed_ratio"][0])
    # proximal-to-distal: frame of peak angular/linear speed in the swing for pelvis, chest, elbow, weapon head
    lo, hi = ph["swing"]["start"], imp + 1
    def peak(series):
        v = np.abs(np.diff(series))
        return int(lo + np.argmax(v[lo:hi])) if hi > lo else lo
    pel = np.array([fr["J"]["pelvis"][0] for fr in frames])
    spn = np.array([fr["rel"]["trunk.spine"] for fr in frames])
    elb = np.array([fr["rel"]["arm_f.elbow"] for fr in frames])
    hed = np.array([mo.unwrap_series([fr["ham_angle"] for fr in frames])]).ravel()
    order = {"pelvis": peak(pel), "spine": peak(spn), "elbow": peak(elb), "weapon": peak(hed)}
    seq = list(order.values())
    add("B", "soft", "proximal_to_distal_sequence", all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1)), order,
        "peak speed frame must not decrease from pelvis to weapon")
    # scapulohumeral coupling: arm above shoulder height -> shoulder raised
    sh = ser.get("shoulder_f")
    if sh is not None:
        shift_y = []
        for k, fr in enumerate(frames):
            p, _ = sol.channel(k)
            shift_y.append(p.get("shift", {}).get("arm_f", [0, 0])[1])
        viol = [k for k in range(len(frames)) if sh["anat"][k] > 120 and shift_y[k] > -2]
        add("B", "soft", "scapulohumeral_coupling", len(viol) <= 2, viol[:6],
            "upper arm above ~120 deg of flexion needs the shoulder (scapula) raised")
    # ---------------- Tier C
    cat = m.get("category", "heavy_strike")
    add("C", "soft", f"{cat}:extension_at_impact", checks["impact_elbow_interior_deg"][1], checks["impact_elbow_interior_deg"][0])
    if "windup_elbow_flex_deg" in checks:
        add("C", "soft", f"{cat}:windup_elbow_flexion", checks["windup_elbow_flex_deg"][1], checks["windup_elbow_flex_deg"][0])
    add("C", "soft", f"{cat}:anticipation_opposite_to_action", checks["windup_opposite_to_swing"][1], checks["windup_opposite_to_swing"][0])
    add("C", "soft", f"{cat}:follow_through", checks["follow_through_overshoot_deg"][1], checks["follow_through_overshoot_deg"][0])
    add("C", "soft", f"{cat}:continuous_swing_arc", checks["swing_weapon_angle_monotonic"][1], checks["swing_weapon_angle_monotonic"][0])
    for item in ("intent read at 270 px", "phase poses read (anticipation, impact)", "personality and weight of the character",
                 "natural vs intentionally stylised posture", "comparison with the motion reference"):
        add("C", "artistic", item, None, None, "director, on the real-time and slow previews (never stills alone)")
    summary = {c: {"pass": sum(1 for f in find if f["class"] == c and f["pass"] is True),
                   "fail": sum(1 for f in find if f["class"] == c and f["pass"] is False),
                   "review": sum(1 for f in find if f["class"] == c and f["pass"] is None)} for c in ("hard", "soft", "artistic")}
    return {"motion": m["id"], "profile": prof["id"], "limit_tier": tier_lim, "summary": summary, "findings": find}


if __name__ == "__main__":
    rep = validate(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        json.dump(rep, open(sys.argv[3], "w"), indent=1, default=str)
    print(json.dumps(rep["summary"]))
    for f in rep["findings"]:
        if f["pass"] is False:
            print(f"FAIL [{f['tier']}/{f['class']}] {f['id']}: {f['value']}  {f['note']}")
