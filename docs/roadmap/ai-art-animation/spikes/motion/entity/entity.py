"""Entity Motion Profile tool (Board amendment 'Universal Motion & Animation Knowledge System', 2026-11-22).

    python -I -s entity.py plan <entity.json> [components.json]

Step 1-7 of the method-selection procedure, made checkable: structure analysis (components resolve in the registry,
attachments point at existing components/sockets), capabilities (locomotion modes vs components), method choice per
component (registry methods filtered by the entity's methods_allowed, first = default), constraints (hard/soft per
component), validators (implemented vs planned), fictional rules removing physical validators explicitly.
Prints a JSON plan; exit code 1 when the profile is structurally invalid.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def plan(entity_path, registry_path=None):
    ent = json.load(open(entity_path))
    reg = json.load(open(registry_path or os.path.join(HERE, "components.json")))["components"]
    errors, comps = [], []
    names = {c["name"] for c in ent.get("components", [])}
    allowed = ent.get("methods_allowed")
    overridden = set()
    for r in ent.get("fictional_rules", []):
        for tok in r.get("overrides", "").replace("->", ",").split(","):
            tok = tok.strip()
            if tok and tok != "not applied" and not tok.startswith("no physical"):
                overridden.add(tok.split()[0])
    for c in ent.get("components", []):
        spec = reg.get(c["type"])
        if not spec:
            errors.append(f"component type '{c['type']}' is not in the registry (add it to the registry, not to the core)")
            continue
        at = c.get("attach_to")
        if at and at.split(".")[0] not in names and at.split(".")[0] not in ("carrier", "scrivener"):
            errors.append(f"{c['name']}: attach_to '{at}' names no component of this entity")
        methods = [m for m in spec["methods"] if not allowed or m in allowed or m.split(" ")[0] in allowed]
        vals = [v for v in spec.get("validators", []) if v not in overridden]
        comps.append({"name": c["name"], "type": c["type"], "method": methods[0] if methods else None,
                      "alternatives": methods[1:], "hard": spec.get("hard", []), "soft": spec.get("soft", []),
                      "validators": vals, "validators_removed_by_fiction": [v for v in spec.get("validators", []) if v in overridden],
                      "implemented": spec.get("implemented"), "runtime": spec.get("runtime", "")})
        if not methods:
            errors.append(f"{c['name']}: no allowed method among {spec['methods']}")
    out = {"entity": ent["id"], "movement_identity": ent.get("identity", {}).get("movement_identity"),
           "locomotion_modes": ent.get("locomotion_modes", []), "components": comps,
           "fictional_rules": ent.get("fictional_rules", []),
           "artistic_review": ent.get("validation", {}).get("artistic", "director on real-time and slow previews"),
           "errors": errors}
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "plan":
        sys.exit(__doc__)
    p = plan(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(json.dumps(p, indent=1))
    sys.exit(1 if p["errors"] else 0)
