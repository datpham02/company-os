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

Single-role pilot mode (ADR-024, PROPOSED; opt-in, off by default; the default run above is unchanged):

    python -I scripts/setup/sync-instructions.py --company Soucean --generated-package --role game-artist --confirm game-artist --dry-run
    python -I scripts/setup/sync-instructions.py --company Soucean --generated-package --role game-artist --confirm game-artist --backup-dir <dir>
    python -I scripts/setup/sync-instructions.py --company Soucean --restore-from <dir>/<snapshot>.json --role game-artist --confirm game-artist --backup-dir <dir>

It touches exactly one agent, refuses to run without --role and a matching --confirm, and pushes only the committed
package at HEAD (working-tree edits are refused). A backup snapshot records company id, agent id and a content hash.
Restore checks that hash and refuses a snapshot for another company or another agent, even with the same role slug.
The default run skips an agent whose installed text is a generated package instead of replacing it with the legacy role body.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request


def read_text(path, newline=None):
    with open(path, encoding="utf-8", newline=newline) as f:
        return f.read()


API = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_board_auth():
    """The shared Board-credential helper (D-AUTH-04), loaded by path: it lives next to pc.py."""
    import importlib.util
    path = os.path.join(REPO, ".claude", "skills", "paperclip", "scripts", "board_auth.py")
    spec = importlib.util.spec_from_file_location("board_auth", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


board_auth = _load_board_auth()


def call(method, path, body=None):
    try:
        hdrs = dict(board_auth.headers(API), **{"Content-Type": "application/json"})
    except board_auth.AuthError as e:
        raise SystemExit(board_auth.redact(e))
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(board_auth.http_error(method, path, e.code, e.read().decode("utf-8", "replace"), 300))


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
            with open(path, encoding="utf-8") as f:
                text = f.read().replace("\r\n", "\n")
            fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
            slug = re.search(r"^slug:\s*(\S+)", fm.group(1), re.M) if fm else None
            out[slug.group(1) if slug else d] = text[fm.end():].lstrip("\n") if fm else text
    return out


GENERATED_DIR = os.path.join(REPO, "config", "paperclip", "generated")
PILOT_FLAGS = ("generated_package", "restore_from", "role", "confirm", "backup_dir")


def _load_generator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_role_packages", os.path.join(os.path.dirname(__file__), "gen-role-packages.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_show(rel):
    """Bytes of `rel` at HEAD. Tests replace this. A missing path is a refusal, not a fallback to the working tree."""
    r = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{rel}"], capture_output=True)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace").strip()
        raise SystemExit(f"refusing: {rel} is not a committed artifact at HEAD ({err})")
    return r.stdout.decode("utf-8").replace("\r\n", "\n")


def outside_repository(path):
    backup = os.path.realpath(os.path.abspath(path))
    repo = os.path.realpath(REPO)
    try:
        return os.path.commonpath([backup, repo]) != repo
    except ValueError:
        return True


def load_reviewed_package(role):
    """The package HEAD committed, and only if the working tree matches it and package.json names the same hash."""
    md_rel = f"config/paperclip/generated/{role}/AGENTS.md"
    js_rel = f"config/paperclip/generated/{role}/package.json"
    work_path = os.path.join(GENERATED_DIR, role, "AGENTS.md")
    if not os.path.isfile(work_path):
        raise SystemExit(f"no generated package for {role}: {os.path.relpath(work_path, REPO)}")
    work = read_text(work_path).replace("\r\n", "\n")
    committed = git_show(md_rel)
    if work != committed:
        raise SystemExit(f"refusing: {md_rel} in the working tree is not the committed artifact at HEAD")
    pkg = json.loads(git_show(js_rel))
    head = _load_generator().parse_header(committed)
    if not head or not head["intact"] or head["role"] != role:
        raise SystemExit(f"refusing: committed {md_rel} has no intact generated header for {role}")
    if head["package_sha256"] != pkg.get("package_sha256") or pkg.get("role") != role:
        raise SystemExit("refusing: package identity does not match the committed package.json "
                         "(an intact self-declared hash is not enough)")
    manifest = json.loads(read_text(os.path.join(REPO, "config", "paperclip", "knowledge-manifest.json")))
    if role not in (manifest.get("roles") or {}):
        raise SystemExit(f"refusing: {role} is outside the pilot manifest; nothing was changed")
    return committed, head


def snapshot_content(snap, role, company, agent):
    """Restore payload after identity checks. Same role slug on another agent is a refusal."""
    if snap.get("role") != role:
        raise SystemExit(f"snapshot is a snapshot of {snap.get('role')!r}, not {role!r}; refusing")
    if snap.get("schema") != "knowledge-delivery-snapshot.v1":
        raise SystemExit("refusing: snapshot schema is not knowledge-delivery-snapshot.v1")
    if snap.get("companyId") != company["id"]:
        raise SystemExit("refusing: snapshot companyId does not match this company")
    if snap.get("agentId") != agent["id"] or snap.get("urlKey") != agent.get("urlKey"):
        raise SystemExit("refusing: snapshot agentId does not match this agent (the role slug is not an identity)")
    content = (snap.get("instructions") or {}).get("content")
    if not isinstance(content, str):
        raise SystemExit("refusing: snapshot has no instructions content")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if digest != (snap.get("instructions") or {}).get("sha256"):
        raise SystemExit("refusing: snapshot content hash does not match its bytes")
    return content


def check_pilot_args(a):
    """Refuse before any network call unless exactly one role is named and confirmed."""
    if not a.role or not a.confirm:
        raise SystemExit("pilot mode needs --role <slug> and --confirm <slug>; nothing was changed")
    if a.confirm != a.role:
        raise SystemExit(f"--confirm {a.confirm!r} does not match --role {a.role!r}; nothing was changed")
    if a.generated_package and a.restore_from:
        raise SystemExit("use either --generated-package or --restore-from, not both; nothing was changed")
    if not a.dry_run and not a.backup_dir:
        raise SystemExit("pilot mode needs --backup-dir <folder outside the repository> unless --dry-run; nothing was changed")
    if a.backup_dir and not outside_repository(a.backup_dir):
        raise SystemExit("--backup-dir must be outside the repository; nothing was changed")


def pilot(a, company):
    """Opt-in single-role mode (ADR-024, pilot change A; PROPOSED). Pushes ONE role's committed generated package, or
    restores ONE role's instructions from a backup snapshot this mode wrote. Refuses without --role and a matching
    --confirm. Before any PUT it writes a backup snapshot. A revision that moves between the read and the write aborts.
    After the PUT the script reads the file back and refuses a mismatch."""
    import time
    if a.generated_package:
        content, head = load_reviewed_package(a.role)
        what = f"committed package {head['package_sha256'][:16]} (pinned source {head['source_commit'][:12]})"
        snap = None
    else:
        snap = json.loads(read_text(a.restore_from))
        if snap.get("role") != a.role:
            raise SystemExit(f"{a.restore_from} is a snapshot of {snap.get('role')!r}, not {a.role!r}; refusing")
        content, what = None, None
    agent = next((ag for ag in call("GET", f"/companies/{company['id']}/agents") if ag["urlKey"] == a.role), None)
    if not agent:
        raise SystemExit(f"{a.role} is not in Paperclip; nothing was changed")
    if snap is not None:
        content = snapshot_content(snap, a.role, company, agent)
        what = f"snapshot {os.path.basename(a.restore_from)} (revision {snap['instructions'].get('revision_id')})"
    q = urllib.parse.urlencode({"path": "AGENTS.md"})
    bundle = f"/agents/{agent['id']}/instructions-bundle/file"
    cur = call("GET", f"{bundle}?{q}") or {}
    norm = lambda s: s.replace("\r\n", "\n").strip()  # noqa: E731
    if norm(cur.get("content", "")) == norm(content):
        print(f"{a.role:20} current ({what})")
        return
    if a.dry_run:
        print(f"{a.role:20} would update to {what}")
        return
    again = call("GET", f"{bundle}?{q}") or {}
    rev = (cur.get("revision") or {}).get("id")
    if (again.get("revision") or {}).get("id") != rev or norm(again.get("content", "")) != norm(cur.get("content", "")):
        raise SystemExit(f"{a.role}: revision changed before PUT; aborting, nothing was written")
    record = call("GET", f"/agents/{agent['id']}") or {}
    os.makedirs(a.backup_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    previous = cur.get("content", "")
    backup = os.path.join(a.backup_dir, f"{a.role}-instructions-{stamp}.json")
    with open(backup, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "knowledge-delivery-snapshot.v1", "role": a.role, "taken": stamp,
                   "companyId": company["id"], "companyName": company.get("name"),
                   "agentId": agent["id"], "urlKey": agent.get("urlKey"),
                   "adapterConfig_keys": sorted((record.get("adapterConfig") or {}).keys()),
                   "instructions": {"path": "AGENTS.md", "content": previous, "revision_id": rev,
                                    "sha256": hashlib.sha256(previous.encode("utf-8")).hexdigest()}},
                  f, indent=2, ensure_ascii=False)
    print(f"{a.role:20} backup written: {backup}")
    call("PUT", bundle, {"path": "AGENTS.md", "content": content, "baseRevisionId": rev})
    back = call("GET", f"{bundle}?{q}") or {}
    if norm(back.get("content", "")) != norm(content):
        raise SystemExit(f"{a.role}: read-back does not match the deployed text; the backup is {backup}")
    print(f"{a.role:20} updated to {what}; read-back matches")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    p.add_argument("--dry-run", action="store_true")
    g = p.add_argument_group("single-role pilot mode (opt-in; ADR-024 PROPOSED; default behaviour is unchanged)")
    g.add_argument("--generated-package", action="store_true",
                   help="push the committed generated package of --role instead of its role body")
    g.add_argument("--restore-from", help="push the instructions saved in this backup snapshot (rollback of --generated-package)")
    g.add_argument("--role", help="the one role to change (pilot mode only)")
    g.add_argument("--confirm", help="repeat the role slug to confirm (pilot mode only)")
    g.add_argument("--backup-dir", help="folder for the backup snapshot written before the change (pilot mode only)")
    a = p.parse_args(argv)
    if not (a.generated_package or a.restore_from) and any(getattr(a, k) for k in PILOT_FLAGS):
        raise SystemExit("--role, --confirm and --backup-dir belong to pilot mode (--generated-package or --restore-from); "
                         "nothing was changed")
    if a.generated_package or a.restore_from:
        check_pilot_args(a)
    company = next((c for c in call("GET", "/companies")
                    if a.company in (c["id"], c.get("issuePrefix")) or c["name"].lower() == a.company.lower()), None)
    if not company:
        raise SystemExit(f"no company matches {a.company!r}")
    if a.generated_package or a.restore_from:
        return pilot(a, company)
    live = {ag["urlKey"]: ag for ag in call("GET", f"/companies/{company['id']}/agents")}
    norm = lambda s: s.replace("\r\n", "\n").strip()
    gen = _load_generator()
    for slug, body in role_bodies().items():
        ag = live.get(slug)
        if not ag:
            print(f"{slug:20} not in Paperclip (import it first)")
            continue
        q = urllib.parse.urlencode({"path": "AGENTS.md"})
        cur = call("GET", f"/agents/{ag['id']}/instructions-bundle/file?{q}")
        installed = cur.get("content", "")
        head = gen.parse_header(installed)
        if head:
            print(f"{slug:20} skipped: installed text is a generated package for {head['role']}; "
                  f"legacy sync does not replace it (use --generated-package or --restore-from)")
            continue
        if "GENERATED by scripts/setup/gen-role-packages.py" in installed:
            print(f"{slug:20} skipped: generated-package marker is present but the header is not intact; "
                  f"refusing to replace it with the legacy role body")
            continue
        if norm(installed) == norm(body):
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
