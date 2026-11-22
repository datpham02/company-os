"""Generate the Agent Capability Catalog and its role views from Company OS at one Git commit (ADR-024, PROPOSED).

Stdlib only. Writes local files only; never calls Paperclip. Run from the repository root:

    python -I scripts/setup/gen-capability-catalog.py              # at main
    python -I scripts/setup/gen-capability-catalog.py --check      # exit 1 if the committed catalog is stale

Inputs, all read with `git show <commit>:<path>` except capability-sources.json (read from the commit when it is
there, else from the working tree; its sha256 is recorded):
- config/paperclip/agents.json: the allow and deny rules build-package.py builds for each role;
- dependencies/registry.yaml: registration and installed version;
- the role files: whether a role is instructed about an operation;
- config/paperclip/capability-sources.json: operations, sample commands and citations.

Columns (every cell names its source, or says "unknown"):
- Registered / Installed: the registry entries the operation names (integrationStatus, verifiedVersion), else a citation.
- Approved: cited decision text, verified verbatim at the commit; else the cited "no"; else "unknown".
- Permitted: the exact allow rule that matches the operation's sample command (Claude Code `Bash(...)` glob, deny rules
  first), with its source in agents.json. Cursor roles: "not enforced (Cursor sandbox disabled)". Never inferred from the
  registry or any declaration. A catalog entry is not a permission grant.
- Instructed: the role-file heading whose text contains one of the operation's keywords.
- Runtime verified / Production validated: cited evidence only, else the operation's default ("no" / "unknown").
A `file` citation whose quote is not in the file at the commit stops the run. `external` citations (Board R&D evidence
outside this repository) are shown as external and are not verified here.

Outputs: config/paperclip/generated/catalog/capability-catalog.md, capability-catalog.json and views/<role>.md.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys


def read_text(path, newline=None):
    with open(path, encoding="utf-8", newline=newline) as f:
        return f.read()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCES = "config/paperclip/capability-sources.json"
OUT = "config/paperclip/generated/catalog"
GENERATOR = "scripts/setup/gen-capability-catalog.py"
VERSION = "1"
COLUMNS = ("registered", "installed", "approved", "permitted", "instructed", "runtime_verified", "production_validated")
CURSOR_PERMITTED = "not enforced (Cursor sandbox disabled)"


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


grp = _load("gen-role-packages")
GenError = grp.GenError
fail = grp.fail


def sha256(s):
    return hashlib.sha256(s.encode("utf-8") if isinstance(s, str) else s).hexdigest()


class Evidence:
    """Resolves and verifies citations: `file` quotes against the source commit, `external` ones only labelled."""

    def __init__(self, src, cites):
        self.src, self.cites = src, cites
        self.used = {}

    def resolve(self, cite):
        c = self.cites[cite] if isinstance(cite, str) else cite
        if c is None:
            return None
        if "file" in c:
            text = self.src.read(c["file"])
            if c["quote"] not in text:
                fail(f"citation not verified: {c['quote']!r} is not in {c['file']} at {self.src.commit[:12]}")
            label = f"{c['file']}"
        elif "external" in c:
            label = f"external: {c['external']} (not verified from this repository)"
        else:
            fail(f"citation without file or external: {c}")
        key = sha256(json.dumps(c, sort_keys=True))[:10]
        self.used[key] = {**c, "verified": "file" in c}
        return f"{label} [{key}]"


def per_role(value, role):
    if isinstance(value, dict):
        return value.get(role, value.get("*"))
    return value


def instructed(body, keywords, role_file):
    hs = grp.headings(body)
    lines = body.split("\n")
    for i, (start, _, h) in enumerate(hs):
        end = hs[i + 1][0] if i + 1 < len(hs) else len(lines)
        text = "\n".join(lines[start:end])
        if any(k in text for k in keywords):
            return {"value": "yes", "source": f"{role_file}#{grp.anchor(h)}"}
    return {"value": "no", "source": f"{role_file} (no heading mentions it)"}


def evidence_cell(op, key, role, ev):
    entries = per_role(op.get(key) or {}, role)
    if entries:
        vals, srcs = [], []
        for e in entries:
            vals.append(f"{e.get('verdict', 'yes')}: {e['text']}")
            srcs.append(ev.resolve(e["cite"]))
        return {"value": "; ".join(vals), "source": "; ".join(srcs)}
    return {"value": op.get(key + "_default", "unknown"), "source": "no cited evidence"}


def cell_permitted(op, role, agents, profile_kind, notes):
    if profile_kind == "cursor":
        return {"value": CURSOR_PERMITTED, "rule": None,
                "source": "Cursor CLI ignores --allowedTools; sandbox disabled (security gate KD-BD-4)"}
    if op["kind"] == "bash":
        allow, deny = grp.role_rules(agents, role)
        spec = agents["agents"][role]
        d = next((r for r in deny if grp.bash_match(r, op["sample"])), None)
        if d:
            return {"value": "denied", "rule": d, "source": f"config/paperclip/agents.json profile {spec['profile']} disallowedTools"}
        a = next((r for r in allow if grp.bash_match(r, op["sample"])), None)
        if a:
            where = "extraAllowedTools" if a in [x.replace("{PREFIX}", "SOU") for x in spec.get("extraAllowedTools", [])] \
                else f"profile {spec['profile']} allowedTools"
            out = {"value": "allowed by exact rule", "rule": a, "source": f"config/paperclip/agents.json {where}"}
            if op.get("note"):
                out["note"] = op["note"]
            return out
        return {"value": "no allow rule", "rule": None, "source": "config/paperclip/agents.json (no matching rule)"}
    if op["kind"] == "paperclip-permission":
        perms = agents["agents"][role].get("permissions", {})
        return {"value": "declared " + (", ".join(f"{k}={json.dumps(v)}" for k, v in sorted(perms.items())) or "nothing"),
                "rule": None, "source": "config/paperclip/agents.json permissions (declaration, not enforcement; "
                                         "live values: check-agent-drift.py)"}
    return {"value": op.get("permitted_text", "unknown"), "rule": None,
            "source": notes.resolve(op["permitted_cite"]) if op.get("permitted_cite") else "no cited source"}


def build(src, sources, sources_sha, sources_origin):
    agents = json.loads(src.read("config/paperclip/agents.json"))
    registry = grp.parse_registry(src.read("dependencies/registry.yaml"))
    ev = Evidence(src, sources["cites"])
    role_files = {}
    for p in sorted(x for x in src.paths if x.endswith("/AGENTS.md") and (
            x.startswith("knowledge/company/agents/") or re.match(r"knowledge/departments/[^/]+/agents/", x))):
        fm = grp.split_frontmatter(src.read(p))[0]
        m = re.search(r"^slug:\s*(\S+)", fm, re.M)
        role_files[m.group(1) if m else p.split("/")[-2]] = p
    roles = [r for r in agents["agents"]]
    rows = {r: [] for r in roles}
    for op in sources["operations"]:
        for role in op["roles"]:
            if role not in agents["agents"]:
                fail(f"operation {op['id']}: unknown role {role}")
            prof = agents["profiles"][agents["agents"][role]["profile"]]
            kind = "cursor" if prof["adapter"] == "cursor" else prof.get("kind", "claude")
            reg_ids = op.get("registry", [])
            if reg_ids:
                missing = [i for i in reg_ids if i not in registry]
                if missing:
                    fail(f"operation {op['id']}: registry ids not in dependencies/registry.yaml: {missing}")
                registered = {"value": ", ".join(f"{i}: {registry[i].get('integrationStatus')}" for i in reg_ids),
                              "source": "dependencies/registry.yaml " + ", ".join(f"line {registry[i]['line']}" for i in reg_ids)}
                vv = [f"{i} {re.split(r' \(|, ', registry[i].get('verifiedVersion'))[0]}" for i in reg_ids
                      if registry[i].get("verifiedVersion")]
                installed = {"value": "verified version: " + "; ".join(vv) if vv else "unknown (no verifiedVersion)",
                             "source": "dependencies/registry.yaml verifiedVersion (first clause)"}
            elif op.get("registry_absent"):
                token = op["registry_absent"]
                if any(token in i for i in registry):
                    fail(f"operation {op['id']}: registry now has an entry containing {token!r}; update the sources")
                registered = {"value": "no registry entry",
                              "source": f"dependencies/registry.yaml (no id contains {token!r})"}
                installed = {"value": op.get("installed_text", "yes" if op.get("installed_cite") else "unknown"),
                             "source": ev.resolve(op["installed_cite"]) if op.get("installed_cite") else "no cited source"}
            else:
                registered = {"value": "no registry entry" if op.get("registered_cite") else "n/a (not a dependency)",
                              "source": ev.resolve(op["registered_cite"]) if op.get("registered_cite") else "dependencies/registry.yaml"}
                installed = {"value": op.get("installed_text", "yes" if op.get("installed_cite") else "unknown"),
                             "source": ev.resolve(op["installed_cite"]) if op.get("installed_cite") else "no cited source"}
            if op.get("installed_cite") and reg_ids:
                installed = {"value": op.get("installed_text", installed["value"]), "source": ev.resolve(op["installed_cite"])}
            appr = per_role(op.get("approved") or [], role)
            if appr:
                approved = {"value": "; ".join(a["text"] for a in appr), "source": "; ".join(ev.resolve(a["cite"]) for a in appr)}
            elif op.get("approved_text"):
                approved = {"value": op["approved_text"],
                            "source": ev.resolve(op["approved_cite"]) if op.get("approved_cite") else "no cited source"}
            else:
                approved = {"value": "unknown", "source": "no cited decision"}
            body = grp.split_frontmatter(src.read(role_files[role]))[1] if role in role_files else ""
            row = {"operation": op["id"], "label": op["label"], "group": op["group"], "plain": op["plain"],
                   "kind": op["kind"], "sample": op.get("sample"), "expect": op.get("expect"),
                   "registered": registered, "installed": installed, "approved": approved,
                   "permitted": cell_permitted(op, role, agents, kind, ev),
                   "instructed": instructed(body, op.get("instructed", []), role_files.get(role, "?")),
                   "runtime_verified": evidence_cell(op, "runtime", role, ev),
                   "production_validated": evidence_cell(op, "production", role, ev)}
            rows[role].append(row)
    status = {}
    for role in roles:
        prof = agents["profiles"][agents["agents"][role]["profile"]]
        st = sources["role_status"].get(role)
        status[role] = {"status": st["status"] if st else "active",
                        "source": "; ".join(ev.resolve(c) for c in st["cites"]) if st else "no pause recorded",
                        "adapter": prof["adapter"], "profile": agents["agents"][role]["profile"],
                        "department": agents["agents"][role]["department"]}
    rnd = []
    allow_all = {r: grp.role_rules(agents, r)[0] for r in roles}
    for item in sources["rnd_only"]["items"]:
        hits = [f"{r}: {a}" for r, rules in sorted(allow_all.items()) for a in rules
                if any(t.lower() in a.lower() for t in item["tokens"])]
        if hits:
            fail(f"R&D-only item {item['label']} is reachable through allow rules: {hits}")
        reg = registry.get(item["registry"]) if item.get("registry") else None
        rnd.append({"label": item["label"], "availability": "not available",
                    "registry": f"{item['registry']}: {reg.get('integrationStatus')}" if reg else "no registry entry",
                    "facts": [{"text": f["text"], "source": ev.resolve(f["cite"])} for f in item["facts"]],
                    "allow_rules": "none (searched every role's allow rules for: " + ", ".join(item["tokens"]) + ")"})
    for rid, reg in sorted(registry.items()):
        if reg.get("integrationStatus") == "evaluating" and not any(i.get("registry") == rid for i in sources["rnd_only"]["items"]):
            rnd.append({"label": reg.get("name") or rid, "availability": "not available",
                        "registry": f"{rid}: evaluating", "facts": [], "allow_rules": "none"})
    notes = {k: [{"text": n["text"], "source": ev.resolve(n["cite"])} for n in v] for k, v in sources["task_notes"].items()}
    return {
        "schema": "capability-catalog.v1",
        "generated_note": "Generated file. Do not edit by hand.",
        "generator": {"path": GENERATOR, "version": VERSION},
        "source_commit": src.commit,
        "sources": {"path": SOURCES, "sha256": sources_sha, "origin": sources_origin},
        "not_a_grant": sources["not_a_grant"],
        "roles": {r: {**status[r], "operations": rows[r]} for r in roles},
        "rnd_only": rnd,
        "task_notes": notes,
        "views": sources["views"],
        "citations": dict(sorted(ev.used.items())),
    }


# ---------- rendering ----------

def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def cell_md(c):
    v = c["value"]
    if c.get("rule"):
        v += f" `{c['rule']}`"
    if c.get("note"):
        v += f" ({c['note']})"
    return esc(v)


def header(cat, title):
    return [f"<!-- GENERATED by {GENERATOR} v{VERSION}. Do not edit by hand. source-commit={cat['source_commit']} -->",
            f"# {title}", "",
            f"Generated from Company OS commit `{cat['source_commit']}` and `{SOURCES}` (sha256 `{cat['sources']['sha256'][:16]}`).", "",
            f"**{cat['not_a_grant']}**", ""]


def ops_table(rows, full=True):
    cols = ["Operation", "Registered", "Installed", "Approved", "Permitted", "Instructed", "Runtime verified",
            "Production validated"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        exp = " (expected: refused)" if r.get("expect") == "refused" else ""
        out.append("| " + " | ".join([esc(r["label"] + exp)] + [cell_md(r[c]) for c in COLUMNS]) + " |")
    if full:
        out += ["", "Sources per cell:", ""]
        for r in rows:
            out.append(f"- `{r['operation']}`: " + "; ".join(f"{c}: {esc(r[c]['source'])}" for c in COLUMNS))
    return out


def rnd_section(cat):
    out = ["## Not available: R&D-only tools", "",
           "Listed only so that nobody assumes them. No role has an allow rule for them; they are not approved for production.", "",
           "| Tool | Availability | Registry | Facts |", "|---|---|---|---|"]
    for i in cat["rnd_only"]:
        facts = "; ".join(f"{f['text']} ({f['source']})" for f in i["facts"]) or "—"
        out.append(f"| {esc(i['label'])} | {i['availability']} | {esc(i['registry'])} | {esc(facts)} |")
    return out


def citations_section(cat):
    out = ["## Citations", "", "| Key | Source | Quote | Verified at commit |", "|---|---|---|---|"]
    for k, c in cat["citations"].items():
        out.append(f"| {k} | {esc(c.get('file') or 'external: ' + c.get('external', ''))} | {esc(c['quote'])} | "
                   f"{'yes' if c['verified'] else 'no (external)'} |")
    return out


def role_block(cat, role, full=True, level="##"):
    r = cat["roles"][role]
    out = [f"{level} `{role}`", "",
           f"Status: **{r['status']}** ({esc(r['source'])}). Adapter `{r['adapter']}`, profile `{r['profile']}`, "
           f"department {r['department']}.", ""]
    if r["adapter"] == "cursor":
        out += [f"Every allow rule for this role is **{CURSOR_PERMITTED}**; nothing in this table is enforced.", ""]
    notes = cat["task_notes"].get(role, []) + cat["task_notes"].get("*", [])
    if notes and full:
        out += ["Task notes:", *[f"- {n['text']} ({esc(n['source'])})" for n in notes], ""]
    if r["operations"]:
        out += ops_table(r["operations"], full)
    else:
        out += ["No cataloged operations."]
    return out + [""]


def render_catalog(cat):
    out = header(cat, "Agent Capability Catalog")
    out += ["Columns: Registered and Installed from `dependencies/registry.yaml`; Approved from a cited decision; "
            "Permitted is the exact allow rule built from `config/paperclip/agents.json` (deny rules first) and is never "
            "inferred from a registry entry or a role text; Instructed from the role file; Runtime verified and "
            "Production validated from cited evidence only. `unknown` means no cited source.", ""]
    for role in cat["roles"]:
        out += role_block(cat, role)
    out += rnd_section(cat) + [""] + citations_section(cat)
    return "\n".join(out) + "\n"


def render_view(cat, role):
    v = cat["views"][role]
    out = header(cat, f"Capability view for `{role}`")
    if v["kind"] == "management":
        out += [f"Management view ({role}): every role, compact. Use it to route Tasks only to a role whose operation is "
                "permitted by an exact rule, approved, and not paused.", ""]
        for r in cat["roles"]:
            out += role_block(cat, r, full=False, level="##")
    else:
        out += role_block(cat, role, full=True)
        for r in v["coordinated"]:
            out += [f"Coordinated role (compact):", ""] + role_block(cat, r, full=False, level="###")
    out += rnd_section(cat)
    return "\n".join(out) + "\n"


def generate(src, sources, sources_sha, origin):
    cat = build(src, sources, sources_sha, origin)
    files = {f"{OUT}/capability-catalog.json": json.dumps(cat, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
             f"{OUT}/capability-catalog.md": render_catalog(cat)}
    for role in cat["views"]:
        files[f"{OUT}/views/{role}.md"] = render_view(cat, role)
    leaks = {p: f for p, t in files.items() for f in [grp.secret_findings(t)] if f}
    if leaks:
        fail(f"secret scan: generated catalog would contain credential, secret or machine-specific material: {leaks}")
    return files


def load_sources(src, repo):
    if SOURCES in src.paths:
        raw, origin = grp.git(repo, "show", f"{src.commit}:{SOURCES}"), f"commit {src.commit}"
    else:
        raw, origin = read_bytes(os.path.join(repo, SOURCES)), "working tree (not in the source commit yet)"
    return json.loads(raw.decode("utf-8")), sha256(raw.replace(b"\r\n", b"\n")), origin


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--repo", default=REPO)
    p.add_argument("--commit", help="source commit (default: main; with --check, the commit the committed catalog records)")
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    commit = a.commit
    if not commit and a.check:
        path = os.path.join(a.repo, OUT, "capability-catalog.json")
        commit = json.loads(read_text(path))["source_commit"] if os.path.isfile(path) else "main"
    try:
        src = grp.Source(a.repo, commit or "main")
        sources, ssha, origin = load_sources(src, a.repo)
        files = generate(src, sources, ssha, origin)
    except GenError as e:
        print(f"gen-capability-catalog: FAILED: {e}", file=sys.stderr)
        return 1
    if a.check:
        stale = [r for r, t in sorted(files.items())
                 if not os.path.isfile(os.path.join(a.repo, r))
                 or read_text(os.path.join(a.repo, r), newline="") != t]
        for r in stale:
            print(f"stale: {r}")
        print(f"{len(files) - len(stale)} of {len(files)} catalog file(s) current at {src.commit[:12]}")
        return 1 if stale else 0
    for rel, text in sorted(files.items()):
        path = os.path.join(a.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"wrote {rel} ({len(text.encode('utf-8'))} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
