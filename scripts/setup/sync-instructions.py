"""Push role instructions from Git into a live Paperclip company (docs/operations/company-bootstrap.md §4, OQ-040).

Stdlib only. Run from the repository root:

    python -I scripts/setup/sync-instructions.py --company Soucean --dry-run
    python -I scripts/setup/sync-instructions.py --company Soucean

For every role file under knowledge/company/agents/ and knowledge/departments/*/agents/, compares the
role body (the file without its frontmatter) with the agent's managed AGENTS.md in Paperclip, and
replaces it when it differs. Agents are matched by slug (frontmatter `slug`, else the folder name).

It uses the route that the official CLI command `paperclipai agent instructions-file:put` calls,
PUT /api/agents/{id}/instructions-bundle/file. Paperclip 2026.1023.0 requires `baseRevisionId`
there, which the CLI does not send yet, so this script reads the current revision first.
Names, adapters and permissions are not touched.
"""
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
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


def role_bodies():
    roots = [os.path.join(REPO, "knowledge", "company", "agents")]
    dept = os.path.join(REPO, "knowledge", "departments")
    roots += [os.path.join(dept, d, "agents") for d in sorted(os.listdir(dept)) if os.path.isdir(os.path.join(dept, d, "agents"))]
    out = {}
    for root in roots:
        for d in sorted(os.listdir(root)):
            path = os.path.join(root, d, "AGENTS.md")
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
            fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
            slug = re.search(r"^slug:\s*(\S+)", fm.group(1), re.M) if fm else None
            out[slug.group(1) if slug else d] = text[fm.end():].lstrip("\n") if fm else text
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    company = next((c for c in call("GET", "/companies")
                    if a.company in (c["id"], c.get("issuePrefix")) or c["name"].lower() == a.company.lower()), None)
    if not company:
        raise SystemExit(f"no company matches {a.company!r}")
    live = {ag["urlKey"]: ag for ag in call("GET", f"/companies/{company['id']}/agents")}
    norm = lambda s: s.replace("\r\n", "\n").strip()
    for slug, body in role_bodies().items():
        ag = live.get(slug)
        if not ag:
            print(f"{slug:20} not in Paperclip (import it first)")
            continue
        q = urllib.parse.urlencode({"path": "AGENTS.md"})
        cur = call("GET", f"/agents/{ag['id']}/instructions-bundle/file?{q}")
        if norm(cur.get("content", "")) == norm(body):
            print(f"{slug:20} current")
            continue
        if a.dry_run:
            print(f"{slug:20} would update")
            continue
        call("PUT", f"/agents/{ag['id']}/instructions-bundle/file",
             {"path": "AGENTS.md", "content": body, "baseRevisionId": (cur.get("revision") or {}).get("id")})
        print(f"{slug:20} updated")


if __name__ == "__main__":
    main()
