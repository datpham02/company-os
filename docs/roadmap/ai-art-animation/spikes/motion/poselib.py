"""Validated pose library builder (Board amendment, 2026-11-22).

    python -I -s poselib.py <structure.json> <poses_spec.json> <out_dir>

A pose = joint transforms (motion.v2 pose: root, chain offsets, shift, feet) for one structure, with action context,
contact requirements, reference, anatomy profile and validation results. Static validation covers tier A
(ranges for the structure's limit tier, bend directions, reachability, bone lengths) and the static part of tier B
(balance over the support, required contacts). It is NOT proof of animation quality (stated in every entry).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as mo  # noqa: E402
import posecheck as pc  # noqa: E402


def static_motion(pose):
    return {"schema": "motion.v2", "id": "pose", "fps": 60, "interpolation": "eased",
            "keys": [{"frame": 0, "ease": "lin", "pose": pose}, {"frame": 1, "ease": "lin", "pose": json.loads(json.dumps(pose))}],
            "phases": [], "events": [], "constraints": [], "acceptance": {}}


def validate_pose(s, prof, tier, pose, needs):
    m = static_motion(pose)
    sol = mo.Solver(s, m)
    fr = sol.solve(0)
    res = []
    lens_ok = all(abs(float(np.linalg.norm(fr["J"][v["to"]] - fr["J"][v["from"]])) - sol.L[b]) < 1e-6 for b, v in s["bones"].items())
    res.append(("A", "hard", "bone_lengths", lens_ok, None))
    ser = pc.anatomical_series(sol, [fr], s)
    for name, d in ser.items():
        jn, mv = d["spec"]["joint"], d["spec"]["movement"]
        rng = prof["joints"].get(jn, {}).get("movements", {}).get(mv, {}).get(tier)
        if rng:
            v = float(d["anat"][0])
            res.append(("A", "hard", f"range:{name}", rng[0] - 1e-6 <= v <= rng[1] + 1e-6, round(v, 1)))
        if d.get("side") is not None and d["spec"].get("bend") == "forward_of_line":
            res.append(("A", "hard", f"bend:{name}", not (d["side"][0] < 0 and d["anat"][0] > 5), int(d["side"][0])))
        if "signed" in d:
            ext = prof["joints"][jn]["movements"]["flex"][tier][0]
            res.append(("A", "soft", f"shoulder_behind:{name}", not (d["signed"][0] < ext and d["anat"][0] < 150), round(float(d["signed"][0]), 1)))
    res.append(("A", "hard", "reachability", not sol.flags, [f[1] for f in sol.flags]))
    com = sol.com(fr)
    xs = []
    for c, spec in s["contacts"].items():
        a = fr["J"][spec["joint"]]
        xs += [a[0] + spec["toe"][0], a[0] + spec["heel"][0]]
    inside = min(xs) - 4 <= com[0] <= max(xs) + 4
    res.append(("B", "hard" if needs.get("balanced", True) else "soft", "balance_static", inside or not needs.get("balanced", True), round(float(com[0]), 1)))
    return [{"tier": t, "class": c, "id": i, "pass": bool(p), "value": v} for t, c, i, p, v in res], fr


def main(sp, specp, out):
    s = json.load(open(sp))
    spec = json.load(open(specp))
    prof = pc.load_profile(os.path.join(os.path.dirname(os.path.abspath(sp)), s["anatomy"]["profile"]))
    for jn, ov in s["anatomy"].get("overrides", {}).items():
        prof["joints"][jn] = pc.deep_merge(prof["joints"].get(jn, {}), {k: v for k, v in ov.items() if k != "why"})
    tier = s["anatomy"].get("limit_tier", "clinical")
    os.makedirs(out, exist_ok=True)
    src = {}
    if spec.get("from_motion"):
        mm = json.load(open(os.path.join(os.path.dirname(os.path.abspath(specp)), spec["from_motion"])))
        src = {k["frame"]: k["pose"] for k in mm["keys"]}
    index = []
    from PIL import Image, ImageDraw
    tiles = []
    for p in spec["poses"]:
        pose = src[p["from_key"]] if "from_key" in p else p["pose"]
        if "patch" in p:
            pose = pc.deep_merge(pose, p["patch"])
        checks, fr = validate_pose(s, prof, tier, pose, p.get("needs", {}))
        ok = all(c["pass"] for c in checks if c["class"] == "hard")
        entry = {"schema": "pose-library-entry.v1", "id": p["id"], "structure": s["id"], "anatomy_profile": s["anatomy"]["profile"],
                 "limit_tier": tier, "action_context": p["context"], "reference": p.get("reference", ""),
                 "contacts_required": p.get("needs", {}).get("contacts", ["foot_k", "foot_f"]),
                 "joint_transforms": pose, "validation": {"static_hard_pass": ok, "checks": checks},
                 "known_limitations": p.get("limitations", []) + ["static validation is not proof of animation quality"]}
        json.dump(entry, open(os.path.join(out, f"{p['id']}.json"), "w"), indent=1)
        index.append({"id": p["id"], "context": p["context"], "static_hard_pass": ok,
                      "soft_fail": [c["id"] for c in checks if c["class"] == "soft" and not c["pass"]]})
        im = Image.new("RGB", (560, 620), mo.BG)
        d = ImageDraw.Draw(im)
        mo.draw_pose(d, fr, s, 0.5, (60, 30))
        d.rectangle([0, 0, 560, 22], fill=(70, 150, 90) if ok else (200, 70, 60))
        d.text((6, 5), f"{p['id']}  {'PASS' if ok else 'FAIL'}", fill=(0, 0, 0))
        tiles.append(im.resize((280, 310)))
    S = Image.new("RGB", (5 * 280, ((len(tiles) + 4) // 5) * 310), (10, 10, 10))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % 5) * 280, (i // 5) * 310))
    S.save(os.path.join(out, "_sheet.png"))
    json.dump(index, open(os.path.join(out, "_index.json"), "w"), indent=1)
    for e in index:
        print(("PASS " if e["static_hard_pass"] else "FAIL ") + e["id"], "soft:", e["soft_fail"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
