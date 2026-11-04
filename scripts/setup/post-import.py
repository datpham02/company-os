"""Post-import step for a company built with scripts/setup/build-package.py (docs/operations/company-bootstrap.md).

Stdlib only. Uses documented Paperclip API routes (agents.md, goals-and-projects.md, secrets.md).
Idempotent: safe to run again. Never reads or prints secret values.

    python -I scripts/setup/post-import.py --company Soucean            # report + project paths + secret bindings
    python -I scripts/setup/post-import.py --company Soucean --resume   # also resume paused agents

What it does:
1. Points each project's primary workspace at <workspace>/repos/<project-slug> when that checkout exists.
2. Binds each agent's declared secrets (config/paperclip/agents.json "secrets") to the company secret
   of the same name, if the Board has created it. Missing secrets are reported, not created.
3. Checks that allowlists use the company's issue prefix.
4. Optionally resumes paused agents (a Board decision: only with --resume).
5. Prints a verification table.
"""
import argparse
import json
import os
import urllib.error
import urllib.request

API = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def call(method, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    p.add_argument("--workspace", default=os.path.join(os.path.expanduser("~"), "game-studio-workspace"))
    p.add_argument("--resume", action="store_true", help="resume paused agents")
    a = p.parse_args()

    conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
    company = next((c for c in call("GET", "/companies")
                    if a.company in (c["id"], c.get("issuePrefix")) or c["name"].lower() == a.company.lower()), None)
    if not company:
        raise SystemExit(f"no company matches {a.company!r}")
    cid, prefix = company["id"], company.get("issuePrefix")
    print(f"Company {company['name']} ({prefix}) {cid}")

    # 1. project workspaces
    for proj in call("GET", f"/companies/{cid}/projects"):
        slug = proj.get("urlKey")
        path = os.path.join(a.workspace, "repos", slug or "")
        for ws in proj.get("workspaces") or []:
            if not ws.get("isPrimary"):
                continue
            if ws.get("cwd") == path:
                print(f"  project {slug}: workspace already at {path}")
            elif os.path.isdir(os.path.join(path, ".git")):
                call("PATCH", f"/projects/{proj['id']}/workspaces/{ws['id']}", {"cwd": path})
                print(f"  project {slug}: workspace set to {path}")
            else:
                print(f"  project {slug}: no checkout at {path}; clone it there, then rerun")

    # 2. secrets
    secrets = {s["name"]: s["id"] for s in call("GET", f"/companies/{cid}/secrets") or []}
    agents = {}
    for s in call("GET", f"/companies/{cid}/agents"):
        agents[s["urlKey"]] = call("GET", f"/agents/{s['id']}")
    missing = set()
    for slug, spec in conf["agents"].items():
        ag = agents.get(slug)
        if not ag:
            print(f"  agent {slug}: not in this company")
            continue
        cfg = dict(ag.get("adapterConfig") or {})
        env = dict(cfg.get("env") or {})
        changed = False
        for name in spec.get("secrets", []):
            if name not in secrets:
                missing.add(name)
                continue
            if (env.get(name) or {}).get("secretId") != secrets[name]:
                env[name] = {"type": "secret_ref", "secretId": secrets[name], "version": "latest"}
                changed = True
        if changed:
            cfg["env"] = env
            call("PATCH", f"/agents/{ag['id']}", {"adapterConfig": cfg})
            agents[slug] = call("GET", f"/agents/{ag['id']}")
            print(f"  agent {slug}: secrets bound")
    if missing:
        print(f"  MISSING company secrets: {', '.join(sorted(missing))}. Create them in Paperclip (Company > Secrets), then rerun.")

    # 3. prefix check
    for slug, ag in agents.items():
        args = " ".join((ag.get("adapterConfig") or {}).get("extraArgs") or [])
        if "git push" in args and f"origin {prefix}-*" not in args and ag["adapterType"] == "claude_local" and "acceptEdits" in args:
            print(f"  WARNING {slug}: allowlist does not use prefix {prefix}; rebuild the package with --prefix {prefix}")

    # 4. resume
    if a.resume:
        for slug, ag in agents.items():
            if ag["status"] == "paused":
                call("POST", f"/agents/{ag['id']}/resume", {})
                agents[slug] = call("GET", f"/agents/{ag['id']}")
                print(f"  agent {slug}: resumed")

    # 5. table
    print(f"\n{'agent':20} {'adapter':13} {'status':8} {'skipPerms':9} {'allowlist':9} secrets")
    for slug, ag in sorted(agents.items()):
        cfg = ag.get("adapterConfig") or {}
        print(f"{slug:20} {ag['adapterType']:13} {ag['status']:8} {str(cfg.get('dangerouslySkipPermissions', '-')):9} "
              f"{len(cfg.get('extraArgs') or []):<9} {','.join(sorted((cfg.get('env') or {}).keys())) or '-'}")


if __name__ == "__main__":
    main()
