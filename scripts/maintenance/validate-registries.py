"""Validate the project and dependency registries (Phase 2, P2-T01). Stdlib only, read-only.

    python -I scripts/maintenance/validate-registries.py

Checks:
1. knowledge/projects/registry.yaml against knowledge/projects/project-config.schema.yaml (the JSON Schema subset
   that file uses: type, required, additionalProperties, properties, enum, const, pattern, minLength, maxLength,
   items, uniqueItems, propertyNames, $ref).
2. Cross-references:
   - each project's `agents` are role Agent IDs (the role folders under knowledge/);
   - its `dependencies` exist in dependencies/registry.yaml;
   - its repository matches config/paperclip/agents.json `projects` (the same id) when listed there.
3. dependencies/registry.yaml: unique kebab-case ids, and `usedBy` names a role Agent ID (or `studio`).

Prints one line per finding and exits 1 if there is any; exit 0 means "no finding", not "everything is right".
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yaml_subset  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}


def validate(value, schema, root, path, out):
    """A small JSON Schema subset; appends findings to `out`."""
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            out.append(f"{path}: unsupported $ref {ref}")
            return
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        return validate(value, target, root, path, out)
    t = schema.get("type")
    if t and not (isinstance(value, TYPES[t]) and not (t == "integer" and isinstance(value, bool))):
        out.append(f"{path}: expected {t}, got {type(value).__name__}")
        return
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            out.append(f"{path}: items are not unique")
        for i, item in enumerate(value):
            if "items" in schema:
                validate(item, schema["items"], root, f"{path}[{i}]", out)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}: missing required '{key}'")
        for key, v in value.items():
            if "propertyNames" in schema:
                validate(key, schema["propertyNames"], root, f"{path}.<key {key}>", out)
            if key in props:
                validate(v, props[key], root, f"{path}.{key}", out)
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}: unknown property '{key}'")


def role_ids(repo):
    """Agent IDs: the role folders under knowledge/company/agents and knowledge/departments/*/agents."""
    ids = set()
    roots = [os.path.join(repo, "knowledge", "company", "agents")]
    dept = os.path.join(repo, "knowledge", "departments")
    if os.path.isdir(dept):
        roots += [os.path.join(dept, d, "agents") for d in os.listdir(dept)]
    for root in roots:
        if os.path.isdir(root):
            ids |= {d for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "AGENTS.md"))}
    return ids


def check(repo):
    out = []
    try:
        reg = yaml_subset.load(os.path.join(repo, "knowledge", "projects", "registry.yaml"))
        schema = yaml_subset.load(os.path.join(repo, "knowledge", "projects", "project-config.schema.yaml"))
        deps = yaml_subset.load(os.path.join(repo, "dependencies", "registry.yaml"))
    except (OSError, yaml_subset.YamlError) as e:
        return [f"cannot read a registry: {e}"]
    validate(reg, schema, schema, "projects-registry", out)
    roles = role_ids(repo)
    dep_list = (deps or {}).get("dependencies") or []
    dep_ids = [d.get("id") for d in dep_list if isinstance(d, dict)]
    if len(set(dep_ids)) != len(dep_ids):
        out.append("dependencies-registry: duplicate ids")
    for i, d in enumerate(dep_list):
        if not isinstance(d, dict) or not isinstance(d.get("id"), str) or not KEBAB.match(d["id"]):
            out.append(f"dependencies-registry[{i}]: missing or non-kebab id")
            continue
        for user in d.get("usedBy") or []:
            if user != "studio" and user not in roles:
                out.append(f"dependencies-registry {d['id']}: usedBy '{user}' is not a role Agent ID")
    try:
        conf = json.load(open(os.path.join(repo, "config", "paperclip", "agents.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        out.append(f"cannot read config/paperclip/agents.json: {e}")
        conf = {}
    conf_projects = conf.get("projects", {})
    for p in (reg or {}).get("projects") or []:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        for a in p.get("agents") or []:
            if a not in roles:
                out.append(f"project {pid}: agent '{a}' is not a role Agent ID")
        for dep in p.get("dependencies") or []:
            if dep not in dep_ids:
                out.append(f"project {pid}: dependency '{dep}' is not in dependencies/registry.yaml")
        if pid in conf_projects:
            want = conf_projects[pid].get("repo")
            url = ((p.get("repository") or {}).get("url") or "")
            got = re.sub(r"^https://github\.com/|\.git$", "", url)
            if want and got.lower() != want.lower():
                out.append(f"project {pid}: repository {got!r} differs from agents.json {want!r}")
    return out


def main(argv=None):
    findings = check(REPO)
    for f in findings:
        print(f)
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
