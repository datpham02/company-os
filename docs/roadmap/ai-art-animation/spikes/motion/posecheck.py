"""Action-aware pose and motion validation (Board amendment "Functional Anatomy & Biomechanics", 2026-11-22;
validator semantics KA-BD-5 and anatomy provenance KA-BD-6, 2026-11-23).

    python -I -s posecheck.py <structure.json> <motion.json> [out.json] [--review review.json] [--approval approval.json]

Everything comes from an anatomy profile (with inheritance and per-tier provenance), the structure's anatomy map,
the motion's category/phases/acceptance and the rule registry (motion_rules.json). rules.py holds the one mapping
from (scope, measurement, eligibility) to a state:

  pass | fail | warn | unknown | not_applicable      (every non-pass state carries a reason)

- Scope mismatch (action category, entity tags, representation) -> not_applicable. A missing category, phase,
  event, joint mapping, range or acceptance value -> unknown. unknown is never a pass.
- fail only for enforcement-eligible rules: structural invariants (hierarchy, bone length, attachment, grip,
  rigidity, reachability, declared contacts, weapon vs ground) by class; anything else needs an enforcement record.
  Anatomical ranges on a planar rig are screen-projected proxies of 3D tables: warn at most.
- Before anything is solved: the representation (only planar_2d has a solver), the solver's supported scope (the
  heavy-hammer benchmark humanoid; unsupported structures are named, never solved) and the input (every malformed
  field is named) are validated. unknown_kind tells invalid_input, unsupported and unmeasurable apart. There is no
  blanket exception handler: a programming error raises.
- Roles and structural thresholds come from the registry; a motion can only tighten them, and a mandatory rule
  becomes advisory only through an approved registry exception (rules.resolve_acceptance).
- Artistic items stay unknown until a review record bound to the exact revision (motion, structure, validation
  profile and artwork hashes, evidence sha256, reviewer, date) AND a separate governed approval record exist.
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


def _split_joints(joints, notes):
    """Joint records are dicts; a profile may also carry free-text notes under 'joints' (flying_creature 'legs').
    Notes move to notes{} so no loop meets a string (review of PR #110, 8a)."""
    out = {}
    for k, v in (joints or {}).items():
        if isinstance(v, dict):
            out[k] = v
        else:
            notes[k] = v
    return out


def load_profile(path):
    with open(path) as fh:
        raw = json.load(fh)
    pid = raw.get("id", os.path.splitext(os.path.basename(path))[0])
    notes = {}
    if raw.get("extends"):
        p = load_profile(os.path.join(os.path.dirname(path), raw["extends"] + ".json"))
        notes.update(p.get("joint_notes", {}))
        lineage = p.get("lineage", []) + [pid]
        p = deep_merge(p, {k: v for k, v in raw.items() if k not in ("overrides", "joints")})
        own_joints = _split_joints(raw.get("joints", {}), notes)
    else:
        p = copy.deepcopy(raw)
        p["joints"] = _split_joints(p.get("joints", {}), notes)
        lineage = [pid]
        own_joints = {}
        for j in p["joints"].values():
            for mvd in j.get("movements", {}).values():
                for rec in mvd.get("provenance", {}).values():
                    rec.setdefault("origin", pid)
    ov = raw.get("overrides", {})
    own_joints.update(_split_joints(ov.get("joints", {}), notes))
    p.setdefault("joints", {})
    for jn, oj in own_joints.items():
        p["joints"][jn] = override_joint(p["joints"].get(jn, {}), oj, origin=pid)
    p = deep_merge(p, {k: v for k, v in ov.items() if k != "joints"})
    p["lineage"] = lineage
    if notes:
        p["joint_notes"] = notes
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
    bend side: d['abs'] is True and only the magnitude is known (it does not depend on the facing). A signed channel,
    the signed shoulder angle and the knee side need anatomy.facing: without it they are reported missing (unknown),
    never measured as if the structure faced +x (M1)."""
    anat = s.get("anatomy") or {}
    amap = anat.get("map", {})
    face = mo.facing_sign(s)
    no_face = mo.facing_problem(s)
    out = {}
    rel0 = frames[0]["rel"] if frames else {}
    for ch, spec in amap.items():
        if ch not in rel0:
            out[ch] = {"spec": spec, "missing": f"channel {ch!r} is not a rig channel"}
            continue
        sign = spec.get("sign")
        if sign == "abs":
            raw = np.array([(face or 1) * mo.wrap(fr["rel"][ch]) for fr in frames])
            out[ch] = {"spec": spec, "raw": raw, "anat": np.abs(raw), "abs": True}
        elif isinstance(sign, (int, float)):
            if face is None:
                out[ch] = {"spec": spec, "missing": no_face}
                continue
            raw = np.array([face * mo.wrap(fr["rel"][ch]) for fr in frames])
            out[ch] = {"spec": spec, "raw": raw, "anat": sign * (raw - spec.get("zero", 0)), "abs": False}
        else:
            out[ch] = {"spec": spec, "missing": f"channel {ch!r} has no usable sign ({sign!r})"}
    J0 = frames[0]["J"] if frames else {}
    for name, spec in anat.get("derived", {}).items():
        J = spec["from"]
        if any(j not in J0 for j in J):
            out[name] = {"spec": spec, "missing": f"derived {name!r} needs joints {J}"}
            continue
        vals, side = [], []
        for fr in frames:
            if spec["movement"] == "flex" and spec["joint"] == "shoulder":
                trunk_down = fr["J"][J[1]] - fr["J"][J[0]]        # chest -> pelvis
                arm = fr["J"][J[3]] - fr["J"][J[2]]
                vals.append(angle_between(trunk_down, arm) * -(face or 1))  # + = forward (facing side), - = behind
            else:
                a, b, c = (fr["J"][j] for j in J)
                interior = abs(angle_between(a - b, c - b))
                vals.append(180 - interior)
                line = c - a                                       # which side of the hip-ankle line is the knee
                cross = line[0] * (b - a)[1] - line[1] * (b - a)[0]
                side.append(np.sign(-cross * face) if face is not None else 0.0)
        if spec["joint"] == "shoulder":
            # 2D elevation: 0 = hanging, 180 = overhead; front/back is ambiguous near overhead in a side view
            sg = np.array(vals)
            out[name] = {"spec": dict(spec, movement="elevation"), "anat": np.abs(sg),
                         "signed": sg if face is not None else None, "signed_missing": no_face, "side": None, "abs": False}
            continue
        out[name] = {"spec": spec, "anat": np.array(vals), "side": np.array(side) if (side and face is not None) else None,
                     "side_missing": no_face, "abs": False}
    return out


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def content_sha256(obj):
    """sha256 of canonical JSON (sorted keys, no whitespace): the content revision of a motion, structure or profile."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def review_binding(s, m, base_dir, reg=None, profile=None):
    """The revision a review record must be bound to (Board code review of PR #110, 110-03): motion, structure and
    validation profile content hashes, and the artwork file hash when the artwork is available."""
    reg = reg or ru.load_registry()
    profile = profile or ru.resolve_acceptance(m.get("acceptance"), m.get("category"), reg, m.get("id"))["profile"]
    rules_only = {k: v for k, v in reg.items() if k != "by_id"}
    art = s.get("artwork")
    ap = os.path.join(base_dir, art) if art else None
    return {"motion_sha256": content_sha256(m), "structure_sha256": content_sha256(s),
            "validation_profile_sha256": content_sha256({"profile": profile, "registry": rules_only}),
            "artwork_sha256": _sha256(ap) if ap and os.path.isfile(ap) else None}


def load_review(review, motion_id, binding=None):
    """(record or None, problem). A record counts only with reviewer, date, the motion id, at least one evidence file
    whose sha256 matches the file on disk (paths relative to the review file) and, when binding is given, the exact
    motion/structure/validation-profile/artwork revision it reviewed (a stale record is invalid)."""
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
    for k, want in (binding or {}).items():
        got = (rec.get("binding") or {}).get(k)
        if got != want:
            what = k.replace("_sha256", "").replace("_", " ")
            probs.append(f"stale review: it is bound to {what} {str(got)[:12]!r}, the validated {what} is {str(want)[:12]!r}")
    return (None, "; ".join(probs)) if probs else (rec, None)


def check_approval(approval, rec):
    """(ok, problem). A recorded visual review is not governed approval: the artistic items take the recorded decision
    only with a separate approval record naming the review (review_sha256), a reference, an approver who is not the
    reviewer, the approver's role (board or qa) and a date."""
    if approval is None:
        return False, "no governed approval record (a reviewer field is not independent QA or Board approval)"
    if isinstance(approval, str):
        with open(approval) as fh:
            approval = json.load(fh)
    probs = [f"approval has no {k}" for k in ("ref", "approved_by", "role", "date") if not approval.get(k)]
    if approval.get("role") and approval["role"] not in ("board", "qa"):
        probs.append(f"approval role {approval['role']!r} is not 'board' or 'qa'")
    if approval.get("approved_by") and approval.get("approved_by") == rec.get("reviewer"):
        probs.append("the approver is the reviewer (not independent)")
    if approval.get("review_sha256") != content_sha256({k: v for k, v in rec.items() if k != "_base"}):
        probs.append("approval is not bound to this review record (review_sha256)")
    return (not probs), "; ".join(probs)


def entity_tags(s, prof):
    tags = set(s.get("entity_tags", []))
    if "humanoid_base" in prof.get("lineage", []):
        tags.add("humanoid")
    return tags


def validate(sp, mp, review=None, approval=None):
    with open(sp) as a, open(mp) as b:
        s, m = json.load(a), json.load(b)
    return validate_data(s, m, os.path.dirname(os.path.abspath(sp)), review, approval=approval)


def validate_data(s, m, base_dir, review=None, reg=None, approval=None):
    reg = reg or ru.load_registry()
    find = []
    acc = ru.resolve_acceptance(m.get("acceptance"), m.get("category"), reg, motion_id=m.get("id"))
    anat = s.get("anatomy") or {}
    prof, prof_err = None, None
    ppath = anat.get("profile")
    if not ppath:
        prof_err = "structure.anatomy.profile: missing"
    elif not os.path.isfile(os.path.join(base_dir, ppath)):
        prof_err = f"structure.anatomy.profile: file {ppath!r} not found"
    else:
        try:
            prof = load_profile(os.path.join(base_dir, ppath))
        except json.JSONDecodeError as e:                               # malformed data file, named
            prof_err = f"structure.anatomy.profile: {ppath!r} is not valid JSON ({e})"
    if prof is not None:
        for jn, ov in anat.get("overrides", {}).items():           # character overrides (each must state why)
            prof["joints"][jn] = override_joint(prof["joints"].get(jn, {}), ov, origin=f"structure:{s.get('id')}")
    prof = prof or {"id": None, "joints": {}, "lineage": []}
    tier = anat.get("limit_tier", prof.get("limit_tier_default", "clinical"))
    # the measured representation is the solver's, never the structure's self-declaration
    ctx = {"representation": mo.REPRESENTATION, "category": m.get("category"),
           "entity_tags": entity_tags(s, prof), "phases": {p.get("name") for p in m.get("phases", [])},
           "events": {e.get("name") for e in m.get("events", [])}, "acceptance_profile": acc["profile"],
           "promoted": acc["promoted"], "excepted": acc["excepted"]}

    def C(rule_id, **kw):
        find.append(ru.classify(rule_id, ctx, reg=reg, **kw))

    def from_check(rule_id, chk, instance=None, **kw):
        C(rule_id, instance=instance, measured=chk["ok"] is not None, within=chk["ok"], unknown_reason=chk.get("reason"),
          value=chk.get("value"), threshold=chk.get("threshold"), **kw)

    def report():
        summ = ru.acceptance(find, reg)
        summ["exceptions_requested"] = acc["exceptions"]
        summ["acceptance_overrides"] = {"applied": acc["applied"], "refused": acc["refused"]}
        return {"motion": m.get("id"), "category": m.get("category"), "profile": prof.get("id"),
                "profile_lineage": prof.get("lineage"), "limit_tier": tier, "representation": ctx["representation"],
                "representation_declared": s.get("representation"), "acceptance_profile": acc["profile"],
                "ground_reference": mo.ground_reference(s)[1], "verdict": summ["verdict"], "summary": summ,
                "findings": find}

    def art_items():
        rec, prob = load_review(review, m.get("id"), review_binding(s, m, base_dir, reg, acc["profile"]))
        ok, aprob = check_approval(approval, rec) if rec is not None else (False, None)
        for rid in ART_ITEMS:
            item = (rec or {}).get("items", {}).get(rid)
            if rec is not None and ok and item in ("pass", "fail"):
                C(rid, measured=True, within=item == "pass",
                  value={"reviewer": rec["reviewer"], "date": rec["date"], "approval": approval_ref(approval)})
            elif rec is not None and item in ("pass", "fail"):
                C(rid, measured=False, unknown_reason=f"recorded visual review ({rec['reviewer']}, {rec['date']}: {item}) "
                                                      f"awaiting governed approval: {aprob}")
            else:
                C(rid, measured=False, unknown_reason="awaiting review: " + (prob or "item not judged in the review record"))

    # ---------------- declarations, validated before anything is solved
    schema_err = None if m.get("schema") == "motion.v2" else f"schema {m.get('schema')!r}: this validator solves motion.v2 only"
    C("meta.motion_schema", measured=schema_err is None, within=True if schema_err is None else None,
      unknown_reason=schema_err, value=m.get("schema"), unknown_kind="unsupported")
    cat = m.get("category")
    cat_why = ru.category_problem(cat, reg)
    C("meta.category_declared", measured=cat_why is None, within=True if cat_why is None else None, value=cat,
      unknown_reason=cat_why, unknown_kind="invalid_input")
    decl = s.get("representation")
    vocab = reg["vocabularies"]["representations"]
    rep_kind = "invalid_input"
    if decl is None:
        rep_why = "structure.representation: missing"
    elif decl not in vocab:
        rep_why = f"structure.representation: {decl!r} is not in the registry vocabulary {sorted(vocab)}"
    elif decl != mo.REPRESENTATION:
        rep_why, rep_kind = (f"representation {decl!r} has no solver here (only {mo.REPRESENTATION!r}); it is not solved "
                             "with the planar solver"), "unsupported"
    else:
        rep_why = None
    C("meta.representation", measured=rep_why is None, within=True if rep_why is None else None,
      value={"declared": decl, "solver": mo.REPRESENTATION}, unknown_reason=rep_why, unknown_kind=rep_kind)
    C("meta.acceptance_profile", measured=acc["profile_problem"] is None,
      within=True if acc["profile_problem"] is None else None, unknown_reason=acc["profile_problem"],
      value={"requested": acc["profile_requested"], "used": acc["profile"]}, unknown_kind="invalid_input")
    C("meta.acceptance_overrides", measured=True, within=not acc["refused"],
      value={"applied": acc["applied"], "refused": acc["refused"]})
    scope = [x for x in mo.scope_problems(s) if not x.startswith("representation")]
    if prof.get("id") is not None and "humanoid_base" not in prof.get("lineage", []):
        scope.append(f"anatomy profile {prof.get('id')!r} does not extend humanoid_base (quadruped, flying and "
                     "multi-limbed bodies are not supported by this solver)")
    C("meta.solver_scope", measured=not scope, within=True if not scope else None, value=scope,
      unknown_reason="unsupported structure: " + "; ".join(scope) if scope else None, unknown_kind="unsupported")
    if scope or schema_err:
        C("meta.input_valid", measured=False, unknown_kind="unsupported",
          unknown_reason="not checked: the structure or motion schema is outside the supported scope")
        inp = []
    else:
        inp = mo.input_problems(s, m) + ([prof_err] if prof_err else [])
        C("meta.input_valid", measured=not inp, within=True if not inp else None, value=inp,
          unknown_reason="invalid input: " + "; ".join(inp) if inp else None, unknown_kind="invalid_input")
    if schema_err or rep_why or scope or inp:
        kind = "unsupported" if (scope or schema_err or rep_kind == "unsupported") else "invalid_input"
        prof_rules = reg["acceptance_profiles"].get(acc["profile"], reg["acceptance_profiles"]["default"])["mandatory"]
        for rid in prof_rules:                       # nothing is solved: every mandatory measurement is unknown, named
            if not (rid.startswith("meta.") or rid in ART_ITEMS):
                C(rid, measured=False, unknown_kind=kind,
                  unknown_reason="not measured: the solver was not run (see meta.* findings)")
        art_items()
        return report()
    sol = mo.Solver(s, m)                            # no exception handler: input was validated, errors are bugs
    frames = [sol.solve(f) for f in range(sol.n)]
    _measure(s, m, sol, frames, prof, tier, acc, C, from_check, ctx, reg, find)
    art_items()
    return report()


def approval_ref(approval):
    if isinstance(approval, dict):
        return approval.get("ref")
    return approval


def _measure(s, m, sol, frames, prof, tier, acc, C, from_check, ctx, reg, find):
    checks, com, hang, table = mo.run_checks(sol, frames, acc["thresholds"])

    # ---------------- structural invariants
    missing_parents = [j for j, v in s["joints"].items() if v.get("parent") is not None and v["parent"] not in s["joints"]]
    C("structure.hierarchy", measured=True, within=not missing_parents, value=missing_parents, threshold=0)
    from_check("structure.bone_length_constant", checks["bone_length_dev_px"])
    from_check("structure.attachment", checks["attachment"])
    from_check("structure.grip", checks["grip_error_px"])
    from_check("structure.weapon_rigid", checks["weapon_rigid_dev_px"])
    from_check("structure.reachability", checks["solver_flags"])
    fs = checks["foot_slide_px"]
    if fs["declared_contacts"] == 0 and m.get("contacts") == "none":
        # explicit, recorded opt-out by the motion (no planted contact); never inferred from a missing declaration
        find.append(ru.finding("contact.foot_slide", state="not_applicable", reg=reg,
                               reason="the motion declares \"contacts\": \"none\" (no planted contact); recorded",
                               role=ru.role_of("contact.foot_slide", ctx, reg)))
    elif fs["declared_contacts"] == 0:
        C("contact.foot_slide", measured=False, threshold=fs.get("threshold"),
          unknown_reason="the motion declares no contact constraint (declare the planted spans, or \"contacts\": "
                         "\"none\" for a motion with no planted contact)")
    else:
        from_check("contact.foot_slide", fs)
    from_check("environment.weapon_ground_penetration", checks["weapon_ground_penetration_px"])

    # ---------------- anatomical references (profile tier, per-tier provenance)
    tiers = tuple(prof.get("tiers", {}) or DEFAULT_TIERS)
    ser = anatomical_series(sol, frames, s)
    covered = set()
    for name, d in ser.items():
        jn, mv = d["spec"].get("joint"), d["spec"].get("movement")
        covered.add((jn, mv))
        if "missing" in d:
            C("anat.range", instance=name, measured=False, unknown_reason=f"structure.anatomy.map.{name}: {d['missing']}")
            continue
        if tier not in tiers:
            C("anat.range", instance=name, measured=False,
              unknown_reason=f"structure.anatomy.limit_tier: {tier!r} is not a tier of profile {prof.get('id')} {list(tiers)}")
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
            if d["signed"] is None:
                C("anat.shoulder_extension_behind", instance=name, measured=False, unknown_reason=d["signed_missing"])
            elif frng is None:
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
        if d["spec"].get("bend") == "forward_of_line":
            if d.get("side") is None:
                C("rep.knee_bend_side_2d", instance=name, measured=False,
                  unknown_reason=d.get("side_missing") or "bend side not measured")
            else:
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

    # ---------------- physical approximations, action-specific and heuristic rules (advisory by default)
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
    rv, ap = None, None
    if "--review" in args:
        i = args.index("--review")
        rv = args[i + 1]
        del args[i:i + 2]
    if "--approval" in args:
        i = args.index("--approval")
        ap = args[i + 1]
        del args[i:i + 2]
    rep = validate(args[0], args[1], rv, ap)
    if len(args) > 2:
        with open(args[2], "w") as fh:
            json.dump(rep, fh, indent=1, default=str)
    _print(rep)
