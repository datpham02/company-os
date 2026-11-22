"""Validated pose library builder (Board amendment, 2026-11-22; validator semantics KA-BD-5, 2026-11-23).

    python -I -s poselib.py <structure.json> <poses_spec.json> <out_dir>

A pose = joint transforms (motion.v2 pose: root, chain offsets, shift, feet) for one structure, with action context,
contact requirements, reference, anatomy profile and validation results. A pose is validated by the same rule engine
as a motion (posecheck.validate_data, rules.py) as a two-frame static clip of category "pose.static": structural
invariants (bone lengths, attachment, grip, reachability, weapon vs ground), anatomical references (warn at most on a
planar rig), the static balance approximation (warn at most; not_applicable when needs.balanced is false). Action
rules are not_applicable. Thresholds come from the acceptance block of the spec's from_motion (or the spec's own
"acceptance"); a missing threshold is unknown, never a default. Artistic review items are advisory for poses.
It is NOT proof of animation quality (stated in every entry).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as mo  # noqa: E402
import posecheck as pc  # noqa: E402
import rules as ru  # noqa: E402


def static_motion(pose, acceptance):
    acc = dict(acceptance)
    acc["roles"] = dict(acc.get("roles", {}), **{rid: "advisory" for rid in pc.ART_ITEMS})
    return {"schema": "motion.v2", "id": "pose", "category": "pose.static", "fps": 60, "interpolation": "eased",
            "keys": [{"frame": 0, "ease": "lin", "pose": pose}, {"frame": 1, "ease": "lin", "pose": json.loads(json.dumps(pose))}],
            "phases": [], "events": [], "constraints": [], "acceptance": acc}


def validate_pose(s, base_dir, pose, needs, acceptance):
    rep = pc.validate_data(s, static_motion(pose, acceptance), base_dir)
    if not needs.get("balanced", True):
        for i, f in enumerate(rep["findings"]):
            if f["rule_id"] == "phys.com_inside_support":
                rep["findings"][i] = ru.finding(f["rule_id"], state="not_applicable", reason="pose spec: needs.balanced is false",
                                                value=f["value"], role=f["role"])
        rep["summary"] = ru.acceptance(rep["findings"])
        rep["verdict"] = rep["summary"]["verdict"]
    sol = mo.Solver(s, static_motion(pose, acceptance))
    return rep, sol.solve(0)


def main(sp, specp, out):
    s = json.load(open(sp))
    spec = json.load(open(specp))
    base_dir = os.path.dirname(os.path.abspath(sp))
    os.makedirs(out, exist_ok=True)
    src, acceptance = {}, dict(spec.get("acceptance", {}))
    if spec.get("from_motion"):
        mm = json.load(open(os.path.join(os.path.dirname(os.path.abspath(specp)), spec["from_motion"])))
        src = {k["frame"]: k["pose"] for k in mm["keys"]}
        acceptance = dict(mm.get("acceptance", {}), **acceptance)
    index = []
    from PIL import Image, ImageDraw
    tiles = []
    for p in spec["poses"]:
        pose = src[p["from_key"]] if "from_key" in p else p["pose"]
        if "patch" in p:
            pose = pc.deep_merge(pose, p["patch"])
        rep, fr = validate_pose(s, base_dir, pose, p.get("needs", {}), acceptance)
        verdict = rep["verdict"]
        entry = {"schema": "pose-library-entry.v2", "id": p["id"], "structure": s["id"], "anatomy_profile": s["anatomy"]["profile"],
                 "limit_tier": rep["limit_tier"], "action_context": p["context"], "reference": p.get("reference", ""),
                 "contacts_required": p.get("needs", {}).get("contacts", ["foot_k", "foot_f"]),
                 "joint_transforms": pose,
                 "validation": {"verdict": verdict, "counts": rep["summary"]["counts"], "blocked_by": rep["summary"]["blocked_by"],
                                "rejected_by": rep["summary"]["rejected_by"], "findings": rep["findings"]},
                 "known_limitations": p.get("limitations", []) + ["static validation is not proof of animation quality"]}
        json.dump(entry, open(os.path.join(out, f"{p['id']}.json"), "w"), indent=1, default=str)
        index.append({"id": p["id"], "context": p["context"], "verdict": verdict, "warnings": rep["summary"]["warnings"]})
        im = Image.new("RGB", (560, 620), mo.BG)
        d = ImageDraw.Draw(im)
        mo.draw_pose(d, fr, s, 0.5, (60, 30))
        col = {"accepted": (70, 150, 90), "blocked": (200, 170, 60), "rejected": (200, 70, 60)}[verdict]
        d.rectangle([0, 0, 560, 22], fill=col)
        d.text((6, 5), f"{p['id']}  {verdict.upper()}", fill=(0, 0, 0))
        tiles.append(im.resize((280, 310)))
    S = Image.new("RGB", (5 * 280, ((len(tiles) + 4) // 5) * 310), (10, 10, 10))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % 5) * 280, (i // 5) * 310))
    S.save(os.path.join(out, "_sheet.png"))
    json.dump(index, open(os.path.join(out, "_index.json"), "w"), indent=1)
    for e in index:
        print(e["verdict"].upper().ljust(9), e["id"], "warn:", e["warnings"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
