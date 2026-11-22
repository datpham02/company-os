"""Action-aware pose and motion validation (Board amendment "Functional Anatomy & Biomechanics", 2026-11-22;
validator semantics KA-BD-5 and anatomy provenance KA-BD-6, 2026-11-23).

    python -I -s posecheck.py <structure.json> <motion.json> [out.json] [--review review.json]

Everything comes from an anatomy profile (with inheritance and per-tier provenance), the structure's anatomy map,
the motion's category/phases/acceptance and the rule registry (motion_rules.json). rules.py holds the one mapping
from (scope, measurement, eligibility) to a state:

  pass | fail | warn | unknown | not_applicable      (every non-pass state carries a reason)

- Scope mismatch (action category, entity tags, representation) -> not_applicable. A missing category, phase,
  event, joint mapping, range or acceptance value -> unknown. unknown is never a pass.
- fail only for enforcement-eligible rules: structural invariants (hierarchy, bone length, attachment, grip,
  rigidity, reachability, declared contacts, weapon vs ground) by class; anything else needs an enforcement record.
  Anatomical ranges on a planar rig are screen-projected proxies of 3D tables: warn at most.
- Artistic items stay unknown until a valid review record (reviewer, date, evidence files with matching sha256)
  judges them.
- Verdict: any mandatory fail -> rejected; else any mandatory unknown -> blocked; else accepted. The summary counts
  all five states and lists the defect classes the rule set cannot detect.

Facing: every directional measurement is taken in the character frame. Structure map `sign`/`zero` are stated for a
character facing +x; a structure facing -x is mirrored by the code (anatomical = sign * (facing * rel2d - zero)).
"""
import copy
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as mo  # noqa: E402
import rules as ru  # noqa: E402

DEFAULT_TIERS = ("clinical", "functional", "stylized")
UNRECORDED = {"kind": "unrecorded", "source_ids": [], "confidence": None, "gate_eligible": False}
ART_ITEMS = ("art.intent_read", "art.phase_poses_read", "art.weight_personality", "art.natural_vs_stylised",
             "art.reference_comparison")


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def override_joint(base_joint, ov_joint, origin):
    """Merge a child-profile or structure override into a joint. A tier range set by the override gets the override's
    own provenance record (or a heuristic record with no confidence): it NEVER inherits the base tier's provenance,
    so an invented number cannot carry a verified citation (audit D-04)."""
    why = ov_joint.get("why")
    out = deep_merge(base_joint, {k: v for k, v in ov_joint.items() if k not in ("movements", "why")})
    if why:
        out.setdefault("override_why", {})[origin] = why
    mvs = out.setdefault("movements", {})
    for mv, spec in ov_joint.get("movements", {}).items():
        cur = copy.deepcopy(mvs.get(mv, {}))
        prov = cur.get("provenance", {})
        own = spec.get("provenance", {})
        for k, v in spec.items():
            if k == "provenance":
                continue
            cur[k] = copy.deepcopy(v)
            if isinstance(v, list):                                           # a tier range
                rec = copy.deepcopy(own.get(k) or {"kind": "heuristic", "source_ids": [], "confidence": None,
                                                   "gate_eligible": False})
                rec["origin"] = origin
                if why and "why" not in rec:
                    rec["why"] = why
                prov[k] = rec
        for legacy in ("sources", "status"):                                  # described the base values only
            cur.pop(legacy, None)
        cur["provenance"] = prov
        mvs[mv] = cur
    return out


def load_profile(path):
    with open(path) as fh:
        raw = json.load(fh)
    pid = raw.get("id", os.path.splitext(os.path.basename(path))[0])
    if raw.get("extends"):
        p = load_profile(os.path.join(os.path.dirname(path), raw["extends"] + ".json"))
        lineage = p.get("lineage", []) + [pid]
        p = deep_merge(p, {k: v for k, v in raw.items() if k not in ("overrides", "joints")})
        own_joints = dict(raw.get("joints", {}))
    else:
        p = copy.deepcopy(raw)
        lineage = [pid]
        own_joints = {}
        for j in p.get("joints", {}).values():
            for mvd in j.get("movements", {}).values():
                for rec in mvd.get("provenance", {}).values():
                    rec.setdefault("origin", pid)
    ov = raw.get("overrides", {})
    own_joints.update(ov.get("joints", {}))
    p.setdefault("joints", {})
    for jn, oj in own_joints.items():
        p["joints"][jn] = override_joint(p["joints"].get(jn, {}), oj, origin=pid)
    p = deep_merge(p, {k: v for k, v in ov.items() if k != "joints"})
    p["lineage"] = lineage
    return p


def tier_range(prof, joint, movement, tier):
    """(range, provenance, reason). reason is set when there is no range: the caller reports unknown."""
    j = prof.get("joints", {}).get(joint)
    if j is None:
        return None, None, f"joint {joint!r} is not in profile {prof.get('id')}"
    mv = j.get("movements", {}).get(movement)
    if mv is None:
        return None, None, f"movement {joint}.{movement} is not in profile {prof.get('id')}"
    rng = mv.get(tier)
    if not (isinstance(rng, list) and len(rng) == 2):
        return None, None, f"no {tier!r} range for {joint}.{movement}"
    return rng, copy.deepcopy(mv.get("provenance", {}).get(tier) or UNRECORDED), None


def angle_between(v, w):
    import math
    return math.degrees(math.atan2(v[0] * w[1] - v[1] * w[0], v[0] * w[0] + v[1] * w[1]))


def anatomical_series(sol, frames, s):
    """Anatomical angle series per mapped channel + derived joints, in the character frame. rel2d is wrapped to
    (-180, 180] first (an unwrapped 308.6 is not an angle a hinge can have). A channel mapped with sign 'abs' has no
    bend side: d['abs'] is True and only the magnitude is known."""
    amap = s["anatomy"]["map"]
    face = mo.facing_sign(s)
    out = {}
    rel0 = frames[0]["rel"] if frames else {}
    for ch, spec in amap.items():
        if ch not in rel0:
            out[ch] = {"spec": spec, "missing": f"channel {ch!r} is not a rig channel"}
            continue
        raw = np.array([face * mo.wrap(fr["rel"][ch]) for fr in frames])
        sign = spec.get("sign")
        if sign == "abs":
            out[ch] = {"spec": spec, "raw": raw, "anat": np.abs(raw), "abs": True}
        elif isinstance(sign, (int, float)):
            out[ch] = {"spec": spec, "raw": raw, "anat": sign * (raw - spec.get("zero", 0)), "abs": False}
        else:
            out[ch] = {"spec": spec, "missing": f"channel {ch!r} has no usable sign ({sign!r})"}
    J0 = frames[0]["J"] if frames else {}
    for name, spec in s["anatomy"].get("derived", {}).items():
        J = spec["from"]
        if any(j not in J0 for j in J):
            out[name] = {"spec": spec, "missing": f"derived {name!r} needs joints {J}"}
            continue
        vals, side = [], []
        for fr in frames:
            if spec["movement"] == "flex" and spec["joint"] == "shoulder":
                trunk_down = fr["J"][J[1]] - fr["J"][J[0]]        # chest -> pelvis
                arm = fr["J"][J[3]] - fr["J"][J[2]]
                vals.append(angle_between(trunk_down, arm) * -face)  # + = forward (facing side), - = behind
            else:
                a, b, c = (fr["J"][j] for j in J)
                interior = abs(angle_between(a - b, c - b))
                vals.append(180 - interior)
                line = c - a                                       # which side of the hip-ankle line is the knee
                cross = line[0] * (b - a)[1] - line[1] * (b - a)[0]
                side.append(np.sign(-cross * face))
        if spec["joint"] == "shoulder":
            # 2D elevation: 0 = hanging, 180 = overhead; front/back is ambiguous near overhead in a side view
            sg = np.array(vals)
            out[name] = {"spec": dict(spec, movement="elevation"), "anat": np.abs(sg), "signed": sg, "side": None, "abs": False}
            continue
        out[name] = {"spec": spec, "anat": np.array(vals), "side": np.array(side) if side else None, "abs": False}
    return out


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_review(review, motion_id):
    """(record or None, problem). A record counts only with reviewer, date, the motion id and at least one evidence
    file whose sha256 matches the file on disk (paths relative to the review file)."""
    if review is None:
        return None, "no review record"
    if isinstance(review, str):
        base = os.path.dirname(os.path.abspath(review))
        with open(review) as fh:
            rec = json.load(fh)
    else:
        rec, base = review, review.get("_base", os.getcwd())
    probs = []
    if rec.get("motion") != motion_id:
        probs.append(f"review is for motion {rec.get('motion')!r}, not {motion_id!r}")
    for k in ("reviewer", "date"):
        if not rec.get(k):
            probs.append(f"review has no {k}")
    ev = rec.get("evidence") or []
    if not ev:
        probs.append("review lists no evidence files")
    for e in ev:
        fp = os.path.join(base, e.get("path", ""))
        if not os.path.isfile(fp):
            probs.append(f"evidence {e.get('path')!r} not found")
        elif _sha256(fp) != e.get("sha256"):
            probs.append(f"evidence {e.get('path')!r} sha256 does not match")
    return (None, "; ".join(probs)) if probs else (rec, None)


def entity_tags(s, prof):
    tags = set(s.get("entity_tags", []))
    if "humanoid_base" in prof.get("lineage", []):
        tags.add("humanoid")
    return tags


def validate(sp, mp, review=None):
    with open(sp) as a, open(mp) as b:
        s, m = json.load(a), json.load(b)
    return validate_data(s, m, os.path.dirname(os.path.abspath(sp)), review)


def validate_data(s, m, base_dir, review=None):
    reg = ru.load_registry()
    find = []
    prof = load_profile(os.path.join(base_dir, s["anatomy"]["profile"]))
    for jn, ov in s["anatomy"].get("overrides", {}).items():          # character overrides (each must state why)
        prof["joints"][jn] = override_joint(prof["joints"].get(jn, {}), ov, origin=f"structure:{s.get('id')}")
    tier = s["anatomy"].get("limit_tier", prof.get("limit_tier_default", "clinical"))
    ctx = {"representation": s.get("representation", "planar_2d"), "category": m.get("category"),
           "entity_tags": entity_tags(s, prof), "phases": {p["name"] for p in m.get("phases", [])},
           "events": {e["name"] for e in m.get("events", [])}, "roles": m.get("acceptance", {}).get("roles"),
           "acceptance_profile": m.get("acceptance", {}).get("profile", "default")}

    def C(rule_id, **kw):
        find.append(ru.classify(rule_id, ctx, **kw))

    def from_check(rule_id, chk, instance=None, **kw):
        C(rule_id, instance=instance, measured=chk["ok"] is not None, within=chk["ok"], unknown_reason=chk.get("reason"),
          value=chk.get("value"), threshold=chk.get("threshold"), **kw)

    def report():
        summ = ru.acceptance(find, reg)
        return {"motion": m.get("id"), "category": m.get("category"), "profile": prof.get("id"),
                "profile_lineage": prof.get("lineage"), "limit_tier": tier, "representation": ctx["representation"],
                "verdict": summ["verdict"], "summary": summ, "findings": find}

    def art_items():
        rec, prob = load_review(review, m.get("id"))
        for rid in ART_ITEMS:
            item = (rec or {}).get("items", {}).get(rid)
            if rec is not None and item in ("pass", "fail"):
                C(rid, measured=True, within=item == "pass", value={"reviewer": rec["reviewer"], "date": rec["date"]})
            else:
                C(rid, measured=False, unknown_reason="awaiting review: " + (prob or "item not judged in the review record"))

    # ---------------- declarations
    sol, frames, err = None, None, None
    if m.get("schema") != "motion.v2":
        err = f"schema {m.get('schema')!r}: this validator solves motion.v2 only"
    else:
        try:
            sol = mo.Solver(s, m)
            frames = [sol.solve(f) for f in range(sol.n)]
        except Exception as e:                                           # data the solver cannot read: unknown
            err = f"solver could not read the motion: {type(e).__name__}: {e}"
    C("meta.motion_schema", measured=err is None, within=True if err is None else None, unknown_reason=err,
      value=m.get("schema"))
    cat = m.get("category")
    C("meta.category_declared", measured=bool(cat), within=True if cat else None, value=cat,
      unknown_reason="the motion has no 'category' (required; scopes the action-specific rules)")
    if err is not None:
        art_items()
        return report()
    checks, com, hang, table = mo.run_checks(sol, frames)

    # ---------------- structural invariants
    missing_parents = [j for j, v in s["joints"].items() if v.get("parent") is not None and v["parent"] not in s["joints"]]
    C("structure.hierarchy", measured=True, within=not missing_parents, value=missing_parents, threshold=0)
    from_check("structure.bone_length_constant", checks["bone_length_dev_px"])
    from_check("structure.attachment", checks["attachment"])
    from_check("structure.grip", checks["grip_error_px"])
    from_check("structure.weapon_rigid", checks["weapon_rigid_dev_px"])
    from_check("structure.reachability", checks["solver_flags"])
    if checks["foot_slide_px"]["declared_contacts"] == 0:
        find.append(ru.finding("contact.foot_slide", state="not_applicable", reason="the motion declares no contact constraint",
                               role=ru.role_of("contact.foot_slide", ctx)))
    else:
        from_check("contact.foot_slide", checks["foot_slide_px"])
    from_check("environment.weapon_ground_penetration", checks["weapon_ground_penetration_px"])

    # ---------------- anatomical references (profile tier, per-tier provenance)
    tiers = tuple(prof.get("tiers", {}) or DEFAULT_TIERS)
    ser = anatomical_series(sol, frames, s)
    covered = set()
    for name, d in ser.items():
        jn, mv = d["spec"].get("joint"), d["spec"].get("movement")
        covered.add((jn, mv))
        if "missing" in d:
            C("anat.range", instance=name, measured=False, unknown_reason=d["missing"])
            continue
        if tier not in tiers:
            C("anat.range", instance=name, measured=False, unknown_reason=f"limit tier {tier!r} is not a tier of profile {prof.get('id')} {list(tiers)}")
            continue
        rng, prov, why = tier_range(prof, jn, mv, tier)
        a = d["anat"]
        if rng is None:
            C("anat.range", instance=f"{name}->{jn}.{mv}[{tier}]", measured=False, unknown_reason=why,
              value=[round(float(a.min()), 1), round(float(a.max()), 1)])
        else:
            lo, hi = rng
            out_mask = (a > hi + 1e-6) if d["abs"] else ((a < lo - 1e-6) | (a > hi + 1e-6))
            bad = [int(f) for f in np.nonzero(out_mask)[0]]
            note = f"frames {bad[:5]}"
            if d["abs"]:
                note += "; upper bound only: a sign 'abs' mapping cannot measure the lower bound (hyperextension)"
            C("anat.range", instance=f"{name}->{jn}.{mv}[{tier}]", measured=True, within=not bad,
              value=[round(float(a.min()), 1), round(float(a.max()), 1)], threshold=rng, provenance=prov, note=note)
        if d["abs"]:
            C("anat.bend_side", instance=name, measured=False,
              unknown_reason="channel mapped with sign 'abs': bend side and hyperextension are not measurable on this mapping")
        if "signed" in d:
            frng, fprov, fwhy = tier_range(prof, jn, "flex", tier)
            if frng is None:
                C("anat.shoulder_extension_behind", instance=name, measured=False, unknown_reason=fwhy)
            else:
                back = [int(i) for i in range(len(d["signed"])) if d["signed"][i] < frng[0] and d["anat"][i] < 150]
                C("anat.shoulder_extension_behind", instance=name, measured=True, within=not back, value=back[:5],
                  threshold=[frng[0], 150], provenance=fprov)
        if d["spec"].get("flip_policy") == "through_neutral":
            raw = d["raw"]
            flips = [int(i) for i in range(1, len(raw)) if np.sign(raw[i]) != np.sign(raw[i - 1]) and
                     min(abs(raw[i]), abs(raw[i - 1])) > 25]
            C("rep.no_flip_through_fold", instance=name, measured=True, within=not flips, value=flips[:5], threshold=25)
        if d.get("side") is not None and d["spec"].get("bend") == "forward_of_line":
            wrong = [int(i) for i in np.nonzero(d["side"] < 0)[0] if d["anat"][i] > 5]
            C("rep.knee_bend_side_2d", instance=name, measured=True, within=not wrong, value=wrong[:5], threshold=5)
    for jn, j in prof.get("joints", {}).items():
        for mv, spec in j.get("movements", {}).items():
            if (jn, mv) not in covered and any(isinstance(spec.get(t), list) for t in tiers):
                C("anat.profile_coverage", instance=f"{jn}.{mv}", measured=False,
                  unknown_reason="the profile declares this movement but no channel of the structure measures it")
    for ch, v in checks["joint_limits_2d"]["value"].items():
        C("rep.joint_limits_2d", instance=ch, measured=v["ok"] is not None, within=v["ok"], unknown_reason=v.get("reason"),
          value=v["value"], threshold=v.get("threshold"))

    # ---------------- physical approximations, action-specific and heuristic rules
    from_check("phys.com_inside_support", checks["com_outside_support_frames"])
    from_check("strike.weight_back_in_windup", checks["com_back_in_windup_px"])
    from_check("strike.weight_forward_at_impact", checks["com_forward_at_impact_px"])
    from_check("rep.face_zone_overlap", checks["forearm_crosses_face_zone_frames"])
    from_check("strike.contact_speed", checks["contact_speed_ratio"])
    from_check("strike.extension_at_impact", checks["impact_elbow_interior_deg"])
    from_check("strike.windup_elbow_flexion", checks["windup_elbow_flex_deg"])
    from_check("strike.elbow_range", checks["elbow_range_deg"])
    from_check("strike.anticipation_opposite", checks["windup_opposite_to_swing"])
    from_check("strike.follow_through", checks["follow_through_overshoot_deg"])
    from_check("strike.continuous_swing_arc", checks["swing_weapon_angle_monotonic"])
    from_check("continuity.weapon_velocity_pops", checks["weapon_velocity_pops"])
    # proximal-to-distal: frame of peak speed in the swing for pelvis, chest, elbow, weapon head
    ph = {p["name"]: p for p in m.get("phases", [])}
    imp = {e["name"]: e["frame"] for e in m.get("events", [])}.get("impact")
    rel0, J0 = frames[0]["rel"], frames[0]["J"]
    if "swing" in ph and imp is not None and "pelvis" in J0 and "trunk.spine" in rel0 and "arm_f.elbow" in rel0:
        lo, hi = ph["swing"]["start"], imp + 1

        def peak(series):
            v = np.abs(np.diff(series))
            return int(lo + np.argmax(v[lo:hi])) if hi > lo else lo
        order = {"pelvis": peak(np.array([fr["J"]["pelvis"][0] for fr in frames])),
                 "spine": peak(np.array([fr["rel"]["trunk.spine"] for fr in frames])),
                 "elbow": peak(np.array([fr["rel"]["arm_f.elbow"] for fr in frames])),
                 "weapon": peak(np.array(mo.unwrap_series([fr["ham_angle"] for fr in frames])))}
        seq = list(order.values())
        C("strike.proximal_to_distal", measured=True, within=all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1)),
          value=order, threshold="non-decreasing")
    else:
        C("strike.proximal_to_distal", measured=False,
          unknown_reason="needs phase 'swing', event 'impact', joint pelvis and channels trunk.spine, arm_f.elbow")
    # scapulohumeral coupling: arm above shoulder height -> shoulder raised
    sh = ser.get("shoulder_f")
    if sh is not None and "anat" in sh and s["chains"].get("arm_f", {}).get("shift"):
        shift_y = [sol.channel(k)[0].get("shift", {}).get("arm_f", [0, 0])[1] for k in range(len(frames))]
        viol = [k for k in range(len(frames)) if sh["anat"][k] > 120 and shift_y[k] > -2]
        C("coupling.scapulohumeral", measured=True, within=len(viol) <= 2, value=viol[:6], threshold="120 deg, -2 px, 2 frames")
    else:
        C("coupling.scapulohumeral", measured=False, unknown_reason="needs derived shoulder_f and a shift channel on arm_f")
    art_items()
    return report()


def _print(rep):
    sm = rep["summary"]
    print(json.dumps({"verdict": rep["verdict"], "counts": sm["counts"], "mandatory": sm["mandatory_counts"]}))
    for f in rep["findings"]:
        if f["state"] == "fail" or (f["state"] == "unknown" and f["role"] == "mandatory"):
            print(f"{f['state'].upper():7s} [{f['role']}/{f['class']}] {f['id']}: {f['value']}  {f['reason'] or ''}")
    for f in rep["findings"]:
        if f["state"] == "warn":
            print(f"WARN    [{f['role']}/{f['class']}] {f['id']}: {f['value']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    rv = None
    if "--review" in args:
        i = args.index("--review")
        rv = args[i + 1]
        del args[i:i + 2]
    rep = validate(args[0], args[1], rv)
    if len(args) > 2:
        with open(args[2], "w") as fh:
            json.dump(rep, fh, indent=1, default=str)
    _print(rep)
