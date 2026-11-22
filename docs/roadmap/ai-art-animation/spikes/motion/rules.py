"""Rule registry and the one deterministic result mapping for the motion validators (Board KA-BD-5, approved with
amendment, 2026-11-23). Rule records live in motion_rules.json; this module only decides states and verdicts.

Result states: pass | fail | warn | unknown | not_applicable, each with a reason.
  1. scope does not match                          -> not_applicable
  2. scope matches, quantity cannot be measured    -> unknown (never pass)
  3. measured inside the threshold                 -> pass
  4. measured outside the threshold                -> fail only when the rule is enforcement-eligible, else warn
  5. artistic review items                         -> unknown until a valid review record exists
Acceptance: any mandatory fail -> rejected; else any mandatory unknown -> blocked; else accepted. warn and advisory
unknown are reported and never block by themselves.
"""
import fnmatch
import json
import os

STATES = ("pass", "fail", "warn", "unknown", "not_applicable")
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "motion_rules.json")
_CACHE = {}


def load_registry(path=REGISTRY_PATH):
    if path not in _CACHE:
        with open(path) as fh:
            reg = json.load(fh)
        reg["by_id"] = {r["id"]: r for r in reg["rules"]}
        _CACHE[path] = reg
    return _CACHE[path]


def rule(rule_id, reg=None):
    reg = reg or load_registry()
    if rule_id not in reg["by_id"]:
        raise KeyError(f"rule {rule_id!r} is not in the registry")       # a programming error, not a data gap
    return reg["by_id"][rule_id]


def _match(patterns, value):
    return any(p == "*" or fnmatch.fnmatchcase(value, p) for p in patterns)


def scope_check(r, ctx):
    """Return (applicable, reason). ctx: representation, category (str or None), entity_tags (set), phases (set),
    events (set). A missing category cannot decide an action scope: the caller gets ('unknown', reason)."""
    sc = r.get("scope", {})
    reps = sc.get("representations", ["*"])
    if not _match(reps, ctx["representation"]):
        return False, f"representation {ctx['representation']!r} not in rule scope {reps}"
    tags = sc.get("entity_tags", ["*"])
    if "*" not in tags and not set(tags) <= ctx["entity_tags"]:
        return False, f"entity lacks tags {sorted(set(tags) - ctx['entity_tags'])}"
    acts = sc.get("actions", ["*"])
    if "*" not in acts:
        if not ctx.get("category"):
            return "unknown", "motion declares no category, so the action scope cannot be decided"
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
            eligibility_reasons=None, provenance=None, role="advisory", note=None, reg=None):
    r = rule(rule_id, reg)
    assert state in STATES, state
    return {"id": rule_id if instance is None else f"{rule_id}:{instance}", "rule_id": rule_id, "state": state,
            "reason": reason, "value": value, "threshold": threshold, "units": r.get("quantity", {}).get("units"),
            "class": r["class"], "convention": r.get("quantity", {}).get("convention"),
            "confidence": r.get("confidence"), "role": role, "enforcement_eligible": eligible,
            "eligibility_reasons": eligibility_reasons, "provenance": provenance, "note": note or r.get("note")}


def classify(rule_id, ctx, *, measured=None, within=None, unknown_reason=None, value=None, threshold=None,
             provenance=None, instance=None, note=None, reg=None):
    """The single mapping from (scope, measurement, eligibility) to a state.
    measured: True when a value was measured; within: True/False for inside/outside the threshold."""
    r = rule(rule_id, reg)
    role = role_of(rule_id, ctx)
    app, why = scope_check(r, ctx)
    common = dict(value=value, threshold=threshold, provenance=provenance, role=role, note=note, reg=reg)
    if app is False:
        return finding(rule_id, instance, state="not_applicable", reason=why, **common)
    if app == "unknown":
        return finding(rule_id, instance, state="unknown", reason=why, **common)
    if r.get("evaluable_from") is not None and r["evaluable_from"].get(ctx["representation"]) is None:
        return finding(rule_id, instance, state="unknown",
                       reason=f"representation {ctx['representation']!r} cannot measure {r['quantity']['name']}", **common)
    if not measured or within is None:
        return finding(rule_id, instance, state="unknown", reason=unknown_reason or "not measured", **common)
    ok, reasons = eligibility(r, ctx["representation"], provenance)
    if within:
        return finding(rule_id, instance, state="pass", eligible=ok, eligibility_reasons=reasons, **common)
    return finding(rule_id, instance, state="fail" if ok else "warn",
                   reason="outside the threshold" + ("" if ok else "; not enforcement-eligible: " + "; ".join(reasons)),
                   eligible=ok, eligibility_reasons=reasons, **common)


def role_of(rule_id, ctx):
    roles = ctx.get("roles") or {}
    if rule_id in roles:
        return roles[rule_id]
    prof = load_registry()["acceptance_profiles"][ctx.get("acceptance_profile", "default")]
    return "mandatory" if rule_id in prof["mandatory"] else "advisory"


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
            "blocked_by": unknown, "warnings": [f["id"] for f in findings if f["state"] == "warn"],
            "undetectable_defect_classes": gaps}
