"""Rule registry and the one deterministic result mapping for the motion validators (Board KA-BD-5, approved with
amendment, 2026-11-23). Rule records live in motion_rules.json; this module only decides states and verdicts.

Result states: pass | fail | warn | unknown | not_applicable, each with a reason.
  1. scope does not match                                       -> not_applicable
  2. scope cannot be decided, or the quantity cannot be measured -> unknown (never pass); unknown_kind says why:
     invalid_input (an error naming the field), unsupported (outside the solver's declared supported scope) or
     unmeasurable (the data is valid but the quantity cannot be measured)
  3. measured inside the threshold                              -> pass
  4. measured outside the threshold -> fail only when the rule is enforcement-eligible, else warn
  5. artistic review items -> unknown until a bound review record AND a separate governed approval exist
Acceptance: any mandatory fail -> rejected; else any mandatory unknown -> blocked; else accepted. warn and advisory
unknown are reported and never block by themselves.

Ownership (Board code review of PR #110, 110-01): motion data, the approved validation profile, approved exceptions
and the implementation are separate. Roles come only from the registry's acceptance profile and the thresholds of
structural invariants only from the registry (threshold.owner "registry"). A motion can only tighten (promote a rule
to mandatory, set a stricter structural threshold). Demoting a mandatory rule needs an approved exception recorded in
the registry (approved_exceptions: scope, provenance, approval record) that the motion references by id; any other
loosening request is refused and reported (resolve_acceptance). Representations and categories are closed vocabularies: a value outside them is
unknown, never not_applicable (H1, M2). The registry itself is checked when it loads (validate_registry).
"""
import copy
import fnmatch
import json
import os

STATES = ("pass", "fail", "warn", "unknown", "not_applicable")
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "motion_rules.json")
_CACHE = {}


def validate_registry(reg):
    """Problems that make the registry itself unusable (a programming or governance error, not a data gap)."""
    probs = []
    vocab = reg.get("vocabularies", {})
    reps, cats = set(vocab.get("representations", {})), list(vocab.get("categories", {}))
    ids = {r["id"] for r in reg["rules"]}
    always = [r["id"] for r in reg["rules"] if r["class"] == "structural_invariant" or r.get("always_mandatory")]
    for r in reg["rules"]:
        sc = r.get("scope", {})
        for rep in sc.get("representations", ["*"]):
            if rep != "*" and rep not in reps:
                probs.append(f"{r['id']}: representation {rep!r} is not in vocabularies.representations")
        for a in sc.get("actions", ["*"]):
            if a != "*" and not any(fnmatch.fnmatchcase(c, a) for c in cats):
                probs.append(f"{r['id']}: action scope {a!r} matches no category in vocabularies.categories")
        if r["class"] == "structural_invariant":
            if sc.get("representations", ["*"]) != ["*"] and not sc.get("representation_exclusion_why"):
                probs.append(f"{r['id']}: a structural invariant applies to every representation unless "
                             "scope.representation_exclusion_why justifies the exclusion")
            th = r.get("threshold", {})
            if "acceptance_key" in th and th.get("owner") != "registry":
                probs.append(f"{r['id']}: a structural threshold must be registry-owned (threshold.owner 'registry')")
    profs = reg.get("acceptance_profiles", {})
    if "default" not in profs:
        probs.append("no 'default' acceptance profile")
    for e in reg.get("approved_exceptions", []):
        if e.get("rule") not in ids:
            probs.append(f"approved exception {e.get('id')!r} names unknown rule {e.get('rule')!r}")
    for name, prof in profs.items():
        miss = [x for x in always if x not in prof.get("mandatory", [])]
        if miss:
            probs.append(f"acceptance profile {name!r} does not list {miss} as mandatory")
        bad = [x for x in prof.get("mandatory", []) if x not in ids]
        if bad:
            probs.append(f"acceptance profile {name!r} lists unknown rules {bad}")
    return probs


def prepare_registry(reg):
    """Index and check a registry dict (also used by tests on an edited in-memory copy)."""
    reg = copy.deepcopy(reg)
    reg.pop("by_id", None)
    probs = validate_registry(reg)
    if probs:
        raise ValueError("invalid rule registry: " + "; ".join(probs))
    reg["by_id"] = {r["id"]: r for r in reg["rules"]}
    return reg


def load_registry(path=REGISTRY_PATH):
    if path not in _CACHE:
        with open(path) as fh:
            _CACHE[path] = prepare_registry(json.load(fh))
    return _CACHE[path]


def rule(rule_id, reg=None):
    reg = reg or load_registry()
    if rule_id not in reg["by_id"]:
        raise KeyError(f"rule {rule_id!r} is not in the registry")       # a programming error, not a data gap
    return reg["by_id"][rule_id]


def _match(patterns, value):
    return any(p == "*" or fnmatch.fnmatchcase(value, p) for p in patterns)


def category_problem(category, reg=None):
    """None when the category is declared and in the registry vocabulary, else the reason (unknown)."""
    reg = reg or load_registry()
    if not category:
        return "motion declares no category, so the action scope cannot be decided"
    vocab = reg["vocabularies"]["categories"]
    if category not in vocab:
        return (f"category {category!r} is not in the registry vocabulary {sorted(vocab)} (misspelt or not "
                "registered), so the action scope cannot be decided")
    return None


def scope_check(r, ctx, reg=None):
    """Return (applicable, reason): True, False (not_applicable) or 'unknown'. ctx: representation (the solver's),
    category (str or None), entity_tags (set), phases (set), events (set). A representation or category outside the
    registry vocabularies gives 'unknown', never not_applicable."""
    reg = reg or load_registry()
    sc = r.get("scope", {})
    if ctx["representation"] not in reg["vocabularies"]["representations"]:
        return "unknown", f"representation {ctx['representation']!r} is not in the registry vocabulary"
    reps = sc.get("representations", ["*"])
    if not _match(reps, ctx["representation"]):
        return False, f"representation {ctx['representation']!r} not in rule scope {reps}"
    tags = sc.get("entity_tags", ["*"])
    if "*" not in tags and not set(tags) <= ctx["entity_tags"]:
        return False, f"entity lacks tags {sorted(set(tags) - ctx['entity_tags'])}"
    acts = sc.get("actions", ["*"])
    if "*" not in acts:
        why = category_problem(ctx.get("category"), reg)
        if why:
            return "unknown", why
        if not _match(acts, ctx["category"]):
            return False, f"category {ctx['category']!r} not in rule scope {acts}"
    miss = [p for p in sc.get("phases", []) if p not in ctx["phases"]]
    if miss:
        return "unknown", f"missing phase(s) {miss} needed by an applicable rule"
    miss = [e for e in sc.get("events", []) if e not in ctx["events"]]
    if miss:
        return "unknown", f"missing event(s) {miss} needed by an applicable rule"
    return True, None


def eligibility(r, representation, provenance=None):
    """(eligible, reasons). Verified source data alone never makes a rule eligible."""
    cls = r["class"]
    enf = r.get("enforcement", {})
    if cls == "structural_invariant":
        if enf.get("rationale"):
            return True, [f"eligible by class (structural invariant): {enf['rationale']}"]
        return False, ["structural rule without a recorded rationale"]
    if cls == "artistic_review":
        return True, ["recorded reviewer decision"]
    if cls == "declaration":
        return False, ["a declaration can only pass or be unknown"]
    reasons = []
    if not enf.get("eligible"):
        reasons.append("no enforcement record (enforcement.eligible is false)")
    if not enf.get("rationale") or not enf.get("approved_by"):
        reasons.append("no recorded rationale and approver")
    measured = r.get("evaluable_from", {}).get(representation)
    wanted = r.get("quantity", {}).get("convention")
    if measured is None:
        reasons.append(f"representation {representation!r} cannot measure this quantity")
    elif measured == "screen_projected" and wanted not in ("screen_projected", "ratio"):
        reasons.append(f"screen-projected 2D proxy compared with a {wanted} reference (warn at most)")
    if cls in ("physical_approximation", "artistic_heuristic", "representation_constraint"):
        reasons.append(f"class {cls} can warn at most without an enforcement record")
    if r.get("confidence") in ("unverified", "experimental"):
        reasons.append(f"rule confidence {r['confidence']}")
    if provenance is not None and not provenance.get("gate_eligible"):
        reasons.append(f"value provenance not gate-eligible (kind={provenance.get('kind')}, "
                       f"confidence={provenance.get('confidence')}, origin={provenance.get('origin')})")
    return (not reasons), reasons


def finding(rule_id, instance=None, *, state, reason=None, value=None, threshold=None, eligible=None,
            eligibility_reasons=None, provenance=None, role="advisory", note=None, reg=None, unknown_kind=None):
    r = rule(rule_id, reg)
    assert state in STATES, state
    th = r.get("threshold", {})
    return {"id": rule_id if instance is None else f"{rule_id}:{instance}", "rule_id": rule_id, "state": state,
            "reason": reason, "value": value, "threshold": threshold, "units": r.get("quantity", {}).get("units"),
            "threshold_owner": th.get("owner") or ("motion" if "acceptance_key" in th else "registry literal"),
            "threshold_status": th.get("status"),
            "unknown_kind": (unknown_kind or "unmeasurable") if state == "unknown" else None,
            "class": r["class"], "convention": r.get("quantity", {}).get("convention"),
            "confidence": r.get("confidence"), "role": role, "enforcement_eligible": eligible,
            "eligibility_reasons": eligibility_reasons, "provenance": provenance, "note": note or r.get("note")}


def classify(rule_id, ctx, *, measured=None, within=None, unknown_reason=None, value=None, threshold=None,
             provenance=None, instance=None, note=None, reg=None, unknown_kind=None):
    """The single mapping from (scope, measurement, eligibility) to a state.
    measured: True when a value was measured; within: True/False for inside/outside the threshold."""
    r = rule(rule_id, reg)
    role = role_of(rule_id, ctx, reg)
    app, why = scope_check(r, ctx, reg)
    common = dict(value=value, threshold=threshold, provenance=provenance, role=role, note=note, reg=reg)
    if app is False:
        return finding(rule_id, instance, state="not_applicable", reason=why, **common)
    if app == "unknown":
        kind = "invalid_input" if ("vocabulary" in why or "no category" in why) else "unmeasurable"
        return finding(rule_id, instance, state="unknown", reason=why, unknown_kind=kind, **common)
    if r.get("evaluable_from") is not None and r["evaluable_from"].get(ctx["representation"]) is None:
        return finding(rule_id, instance, state="unknown",
                       reason=f"representation {ctx['representation']!r} cannot measure {r['quantity']['name']}", **common)
    if not measured or within is None:
        return finding(rule_id, instance, state="unknown", reason=unknown_reason or "not measured",
                       unknown_kind=unknown_kind, **common)
    ok, reasons = eligibility(r, ctx["representation"], provenance)
    if within:
        return finding(rule_id, instance, state="pass", eligible=ok, eligibility_reasons=reasons, **common)
    return finding(rule_id, instance, state="fail" if ok else "warn",
                   reason="outside the threshold" + ("" if ok else "; not enforcement-eligible: " + "; ".join(reasons)),
                   eligible=ok, eligibility_reasons=reasons, **common)


def role_of(rule_id, ctx, reg=None):
    """mandatory | advisory, from the registry's acceptance profile (ctx['acceptance_profile'], resolved by
    resolve_acceptance; an unknown name falls back to 'default'). A motion can only promote (ctx['promoted']); a
    mandatory rule becomes advisory only through an approved registry exception (ctx['excepted'])."""
    reg = reg or load_registry()
    profs = reg["acceptance_profiles"]
    prof = profs.get(ctx.get("acceptance_profile", "default")) or profs["default"]
    if rule_id in (ctx.get("excepted") or ()):
        return "advisory"
    promoted = ctx.get("promoted") or ()
    if rule_id in promoted:
        return "mandatory"
    return "mandatory" if rule_id in prof["mandatory"] else "advisory"


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def exception_problem(e, rule_id, motion_id, category):
    """None when the approved registry exception e covers rule_id for this motion, else why not."""
    if e.get("rule") != rule_id:
        return f"approved exception {e.get('id')!r} is for rule {e.get('rule')!r}, not {rule_id!r}"
    sc = e.get("scope") or {}
    if not sc.get("motion_ids") and not sc.get("categories"):
        return f"approved exception {e.get('id')!r} has no scope (motion_ids or categories)"
    if sc.get("motion_ids") and motion_id not in sc["motion_ids"]:
        return f"approved exception {e.get('id')!r} does not cover motion {motion_id!r}"
    if sc.get("categories") and not (category and _match(sc["categories"], category)):
        return f"approved exception {e.get('id')!r} does not cover category {category!r}"
    if not e.get("provenance"):
        return f"approved exception {e.get('id')!r} has no provenance"
    ap = e.get("approval") or {}
    miss = [k for k in ("approved_by", "date", "ref") if not ap.get(k)]
    if miss:
        return f"approved exception {e.get('id')!r} has no approval record ({', '.join(miss)} missing)"
    return None


def resolve_acceptance(acc, category, reg=None, motion_id=None):
    """Resolve a motion's acceptance block against the registry (H2). Returns a dict:
      profile / profile_problem: the acceptance profile used ('default' when the requested one is unknown or does not
        cover the category; meta.acceptance_profile is then unknown).
      thresholds: the effective values. A registry-owned key (structural invariant) takes the registry value; the
        motion may only make it stricter (kind max: smaller, kind min: larger). A registry-owned key without a registry
        value is left out, so its rule is unknown (no default). Other keys come from the motion as before.
      promoted: rules the motion makes mandatory (allowed, stricter). A demotion through acceptance.roles is refused.
      excepted: mandatory rules made advisory for this motion by an approved registry exception the motion references
        (acceptance.exceptions [{id, rule, why}]); the registry record needs scope, provenance and an approval record.
        A request without a valid approved record is refused (the rule stays mandatory) and reported.
      applied / refused: what was applied, and every loosening or invalid request refused (meta.acceptance_overrides)."""
    reg = reg or load_registry()
    acc = acc if isinstance(acc, dict) else {}
    out = {k: v for k, v in acc.items() if k not in ("roles", "profile", "exceptions")}
    applied, refused = [], []
    profs = reg["acceptance_profiles"]
    name = acc.get("profile", "default")
    problem = None
    if not isinstance(name, str) or name not in profs:
        problem = f"acceptance profile {name!r} is not in the registry {sorted(profs)}"
    else:
        cats = profs[name].get("categories", ["*"])
        if "*" not in cats and not (category and _match(cats, category)):
            problem = f"acceptance profile {name!r} applies to categories {cats}, not {category!r}"
    used = name if problem is None else "default"
    for r in reg["rules"]:
        th = r.get("threshold", {})
        if th.get("owner") != "registry":
            continue
        key, kind, rv = th["acceptance_key"], th.get("kind", "max"), th.get("value")
        req = acc.get(key)
        out.pop(key, None)
        if not _num(rv):
            continue                                                     # no registry value: unknown, no default
        out[key] = rv
        if req is None or req == rv:
            continue
        if _num(req) and (req < rv if kind == "max" else req > rv):
            out[key] = req
            applied.append({"key": key, "requested": req, "registry": rv, "effect": "stricter threshold applied"})
        else:
            refused.append({"key": key, "requested": req, "registry": rv,
                            "why": "a motion may only tighten a registry-owned structural threshold"})
    mandatory = profs[used]["mandatory"]
    promoted = set()
    for rid, role in (acc.get("roles") or {}).items():
        if rid not in reg["by_id"]:
            refused.append({"role": rid, "requested": role, "why": "not a rule of the registry"})
        elif role == "mandatory":
            promoted.add(rid)
            applied.append({"role": rid, "requested": role, "effect": "promoted to mandatory"})
        elif role == "advisory" and rid in mandatory:
            refused.append({"role": rid, "requested": role,
                            "why": f"a motion cannot demote a rule the acceptance profile {used!r} makes mandatory"})
        elif role != "advisory":
            refused.append({"role": rid, "requested": role, "why": "role must be 'mandatory' or 'advisory'"})
    approved = {e.get("id"): e for e in reg.get("approved_exceptions", [])}
    excepted, exceptions = set(), []
    for req in (acc.get("exceptions") or []):
        req = dict(req) if isinstance(req, dict) else {"request": req}
        e = approved.get(req.get("id"))
        why = (f"no approved exception {req.get('id')!r} in the registry (approved_exceptions)" if e is None
               else exception_problem(e, req.get("rule"), motion_id, category))
        if why:
            refused.append({"exception": dict(req), "why": why})
            req["status"] = "refused: " + why
        else:
            excepted.add(e["rule"])
            applied.append({"exception": req.get("id"), "rule": e["rule"], "effect": "advisory for this motion",
                            "approval": e["approval"]})
            req["status"] = "applied (approved registry exception)"
        exceptions.append(req)
    return {"profile": used, "profile_requested": name, "profile_problem": problem, "promoted": promoted,
            "excepted": excepted, "thresholds": out, "applied": applied, "refused": refused, "exceptions": exceptions}


def acceptance(findings, reg=None):
    """Verdict + counts of all five states + blocking items + defect classes the set cannot detect."""
    reg = reg or load_registry()
    counts = {s: sum(1 for f in findings if f["state"] == s) for s in STATES}
    mand = [f for f in findings if f["role"] == "mandatory"]
    m_counts = {s: sum(1 for f in mand if f["state"] == s) for s in STATES}
    fails = [f["id"] for f in mand if f["state"] == "fail"]
    unknown = [f"{f['id']} ({f['reason']})" for f in mand if f["state"] == "unknown"]
    verdict = "rejected" if fails else ("blocked" if unknown else "accepted")
    gaps = list(reg["coverage_gaps"])
    gaps += sorted({f"{f['id']}: {f['reason']}" for f in findings
                    if f["state"] == "unknown" and f["role"] == "advisory"})
    return {"verdict": verdict, "counts": counts, "mandatory_counts": m_counts, "rejected_by": fails,
            "blocked_by": unknown,
            "input_errors": [f"{f['id']}: {f['reason']}" for f in findings if f.get("unknown_kind") == "invalid_input"],
            "unsupported": [f"{f['id']}: {f['reason']}" for f in findings if f.get("unknown_kind") == "unsupported"],
            "warnings": [f["id"] for f in findings if f["state"] == "warn"],
            "awaiting_board_confirmation": sorted({f"{f['rule_id']}: {f['threshold_status']}" for f in findings
                                                   if f.get("threshold_status") and f["state"] != "not_applicable"}),
            "undetectable_defect_classes": gaps}
