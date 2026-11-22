"""Read-only drift check: live Paperclip agents against what this repository would configure (Phase 2, P2-T03; G-11).

    python -I scripts/setup/check-agent-drift.py --company Soucean

For every agent in config/paperclip/agents.json it compares, without writing anything:
- adapter type;
- adapterConfig.extraArgs, as build-package.py builds them for the company's issue prefix;
- adapterConfig.model and adapterConfig.effort (the agent's own values, else the profile's);
- runtimeConfig.heartbeat (`enabled`, `maxConcurrentRuns`);
- the names of `env` bindings (never their values) against the declared secrets;
- the managed AGENTS.md against the role file (as sync-instructions.py --dry-run does).

The Review Package reviewer (profile kind strict-reviewer) is not built here: its paths are machine-specific. While it
is absent it is reported as such; when present, `review-start` checks it with check_reviewer_config.

Exit 1 when any drift is found. Stdlib only; Paperclip at PAPERCLIP_URL (default http://127.0.0.1:3100/api).
"""
import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def read_text(path, newline=None):
    with open(path, encoding="utf-8", newline=newline) as f:
        return f.read()


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def _load_board_auth():
    """The shared Board-credential helper (D-AUTH-04), loaded by path: it lives next to pc.py."""
    import importlib.util
    path = os.path.join(REPO, ".claude", "skills", "paperclip", "scripts", "board_auth.py")
    spec = importlib.util.spec_from_file_location("board_auth", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


board_auth = _load_board_auth()
API = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def http_get(path):
    try:
        req = urllib.request.Request(API + path, headers=board_auth.headers(API))
    except board_auth.AuthError as e:
        raise SystemExit(board_auth.redact(e))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):  # credential problems stop the run; other errors keep their old handling
            raise SystemExit(board_auth.http_error("GET", path, e.code, e.read().decode("utf-8", "replace")))
        raise
    return json.loads(raw) if raw else None


def drift(conf, company, agents_full, bodies, live_bodies, bp):
    """Pure comparison; returns a list of finding lines. `agents_full` maps urlKey -> GET /agents/<id> record."""
    out = []
    prefix = company.get("issuePrefix")
    for slug, spec in conf["agents"].items():
        prof = conf["profiles"][spec["profile"]]
        live = agents_full.get(slug)
        if bp.is_strict_reviewer(prof):
            continue  # absent until Review Package P6-B; when present, review-start's check_reviewer_config applies
        if live is None:
            out.append(f"{slug}: declared in agents.json but not in the company")
            continue
        if live.get("adapterType") != prof["adapter"]:
            out.append(f"{slug}: adapter {live.get('adapterType')!r}, expected {prof['adapter']!r}")
        want_args = bp.adapter_block(prof, spec, conf["rules"], prefix, "", "agent")["config"].get("extraArgs")
        got_args = (live.get("adapterConfig") or {}).get("extraArgs")
        if want_args is not None and got_args != want_args:
            missing = [a for a in want_args if a not in (got_args or [])]
            extra = [a for a in (got_args or []) if a not in want_args]
            out.append(f"{slug}: extraArgs differ (missing {len(missing)}, extra {len(extra)}"
                       f"{', order only' if not missing and not extra else ''})"
                       + (f"; first missing: {missing[0][:80]!r}" if missing else "")
                       + (f"; first extra: {extra[0][:80]!r}" if extra else ""))
        want_cfg = {**prof.get("config", {}), **bp.model_fields(prof, spec)}
        for key in ("model", "effort"):
            got = (live.get("adapterConfig") or {}).get(key)
            if want_cfg.get(key) != got:
                out.append(f"{slug}: {key} is {got!r}, expected {want_cfg.get(key)!r}")
        want_hb = (spec.get("runtime") or conf["runtime"]).get("heartbeat", {})
        got_hb = ((live.get("runtimeConfig") or {}).get("heartbeat")) or {}
        for key in ("enabled", "maxConcurrentRuns"):
            if key in want_hb and got_hb.get(key) != want_hb[key]:
                out.append(f"{slug}: heartbeat.{key} is {got_hb.get(key)!r}, expected {want_hb[key]!r}")
        want_env = set(spec.get("secrets") or [])
        got_env = set(((live.get("adapterConfig") or {}).get("env") or {}).keys())
        if want_env != got_env:
            out.append(f"{slug}: env bindings {sorted(got_env)}, expected {sorted(want_env)} (names only)")
        want_body = (bodies.get(slug) or "").replace("\r\n", "\n").strip()
        got_body = (live_bodies.get(slug) or "").replace("\r\n", "\n").strip()
        if want_body and got_body != want_body:
            pkg = _load("gen-role-packages").parse_header(live_bodies.get(slug) or "")
            if pkg and pkg["intact"] and pkg["role"] == slug:
                continue  # a generated package (ADR-024 pilot): compared with the committed package in instructions.deployment
            out.append(f"{slug}: AGENTS.md differs from the role file (run sync-instructions.py --dry-run)")
    known = set(conf["agents"])
    for slug in sorted(set(agents_full) - known):
        out.append(f"{slug}: in the company but not in agents.json")
    return out


# ---------- extended checks (ADR-024, PROPOSED): knowledge delivery, skills, adapter, memory ----------

# Board decision 2026-11-23 (SEC-02 immediate mitigation): new agents need Board approval. Not declared in agents.json.
EXPECTED_COMPANY = {"requireBoardApprovalForNewAgents": True}
UNVERIFIED_RUNTIME = [
    "which skills the Claude CLI actually lists at run start (init.skills in the run log); the API shows only "
    "desiredSkills and Paperclip's skill entries",
    "whether --settings enabledPlugins entries override ~/.claude/settings.json per plugin (merge semantics)",
    "whether disableBundledSkills removes every bundled skill, and whether ~/.claude/skills user skills still load",
    "whether autoMemoryEnabled=false stops auto-memory reads as well as writes",
    "whether a changed instructions bundle starts a fresh session on the next run (instruction hash change)",
    "Cursor agents: ~/.cursor/cli-config.json sandbox and permissions (not read by this check)",
]


def _norm_body(s):
    return (s or "").replace("\r\n", "\n").strip()


def extended(conf, manifest, company_full, agents_full, live_bodies, bodies, live_skills, read_local, bp, grp):
    """Pure comparison. Returns rows {category, role, status, detail}; status is ok, drift, info or unverified.
    `live_skills` maps slug -> {"desired": [...], "files": {repo path: sha256 or None}} (None: could not be read).
    `read_local(path)` returns a local file's text or None."""
    rows = []
    add = lambda cat, role, st, detail: rows.append({"category": cat, "role": role, "status": st, "detail": detail})  # noqa: E731
    for key, want in EXPECTED_COMPANY.items():
        got = (company_full or {}).get(key)
        add("adapter.company", "*", "ok" if got == want else "drift",
            f"{key} is {json.dumps(got)}, expected {json.dumps(want)} (Board decision 2026-11-23, SEC-02)")
    for slug, spec in conf["agents"].items():
        prof = conf["profiles"][spec["profile"]]
        live = agents_full.get(slug)
        if bp.is_strict_reviewer(prof) and live is None:
            add("adapter.config", slug, "info", "absent from the company: strict reviewer, created only in Review Package "
                "P6-B (KD-BD-7 open)")
            continue
        if bp.is_strict_reviewer(prof) or live is None:
            continue
        cfg = live.get("adapterConfig") or {}
        if prof["adapter"] == "cursor":
            add("adapter.config", slug, "info",
                f"Cursor agent, status {live.get('status')!r}"
                + (f" (paused {live.get('pausedAt')}, reason {live.get('pauseReason')!r})" if live.get("pausedAt") else "")
                + "; allow rules not enforced (Cursor sandbox disabled)")
        pilot = (manifest.get("roles") or {}).get(slug)
        # 1-2. Deployment kind, source commit and package hash.
        body = live_bodies.get(slug) or ""
        head = grp.parse_header(body) if body else None
        pkg_path = os.path.join(REPO, grp.OUT_DIR, slug, "AGENTS.md")
        if head:
            committed = read_text(pkg_path) if os.path.isfile(pkg_path) else None
            same = committed is not None and _norm_body(committed) == _norm_body(body)
            add("instructions.deployment", slug, "ok" if same and head["intact"] else "drift",
                "generated-package" + ("" if head["intact"] else " (header hash does not match the content)")
                + ("; equals the committed package" if same else "; differs from the committed package"))
            add("instructions.source", slug, "info",
                f"source commit {head['source_commit']}, package sha256 {head['package_sha256']}")
        else:
            want = _norm_body(bodies.get(slug))
            add("instructions.deployment", slug, "ok" if want and _norm_body(body) == want else "drift",
                "legacy-role-body; " + ("equals the role file" if want and _norm_body(body) == want
                                        else "differs from the role file (sync-instructions.py --dry-run)"))
            add("instructions.source", slug, "info", "legacy role body: no source commit or package hash")
        # 3. Assigned skills and their revision.
        desired = list(((cfg.get("paperclipSkillSync") or {}).get("desiredSkills")) or [])
        repo_skills = {s["name"] for s in (pilot or {}).get("skills", [])}
        if not desired:
            add("skills.assigned", slug, "ok", "desiredSkills [] (baseline; Paperclip adds its own system skills per run)")
        for d in desired:
            name = d.split("/")[-1]
            if name in repo_skills:
                files = (live_skills.get(slug) or {}).get("files", {})
                skill = manifest["skills"][name]
                want_files = {p: grp.sha256(read_text(os.path.join(REPO, p)).replace("\r\n", "\n"))
                              for p in sorted(os.path.join(skill["dir"], f).replace("\\", "/")
                                              for f in ("SKILL.md", skill["reference_file"]))
                              if os.path.isfile(os.path.join(REPO, p))}
                if not files or any(v is None for v in files.values()):
                    add("skills.assigned", slug, "unverified", f"{d}: assigned; live content could not be read")
                else:
                    diff = [p for p in want_files if files.get(p) != want_files[p]]
                    add("skills.assigned", slug, "ok" if not diff else "drift",
                        f"{d}: assigned (pilot change C); content " + ("matches the repository" if not diff
                                                                      else "differs: " + ", ".join(diff)))
            else:
                add("skills.assigned", slug, "drift", f"{d}: assigned but not a repository Studio Skill for this role")
        # 4. Adapter configuration.
        args = cfg.get("extraArgs") or []
        settings_path = args[args.index("--settings") + 1] if "--settings" in args and args.index("--settings") + 1 < len(args) else None
        if prof["adapter"] == "claude_local":
            add("adapter.config", slug, "info" if settings_path is None else "ok",
                "no --settings in extraArgs (baseline)" if settings_path is None else f"--settings {settings_path}")
            want_dsp = (prof.get("config") or {}).get("dangerouslySkipPermissions")
            got_dsp = cfg.get("dangerouslySkipPermissions")
            add("adapter.config", slug, "ok" if got_dsp == want_dsp else "drift",
                f"dangerouslySkipPermissions is {json.dumps(got_dsp)}, expected {json.dumps(want_dsp)}")
        perms = live.get("permissions") or {}
        declared = spec.get("permissions") or {}
        for key in ("canCreateAgents", "canCreateSkills"):
            want = bool(declared.get(key, False))
            add("adapter.permissions", slug, "ok" if perms.get(key) == want else "drift",
                f"{key} is {json.dumps(perms.get(key))}, agents.json declares {json.dumps(want)}"
                + ("" if key in declared else " (absent = false)"))
        # 5. Memory policy.
        if prof["adapter"] != "claude_local":
            add("memory.policy", slug, "unverified", "Cursor agent: memory and skills folders are not read by this check")
        elif settings_path is None:
            add("memory.policy", slug, "info", "default: auto-memory on, inherited user skills and plugins (pilot change B not applied)")
        else:
            repo_file = (pilot or {}).get("settings_file")
            text = read_local(settings_path)
            if text is None:
                add("memory.policy", slug, "drift", f"--settings file {settings_path} is missing or unreadable")
            elif not repo_file:
                add("memory.policy", slug, "drift", "--settings is set but the manifest names no settings file for this role")
            else:
                want = json.loads(read_text(os.path.join(REPO, repo_file)))
                try:
                    got = json.loads(text)
                except ValueError:
                    got = None
                add("memory.policy", slug, "ok" if got == want else "drift",
                    f"{settings_path} " + ("equals " if got == want else "differs from ") + repo_file
                    + f"; autoMemoryEnabled={json.dumps((got or {}).get('autoMemoryEnabled'))}")
    for item in UNVERIFIED_RUNTIME:
        add("unverified.runtime", "*", "unverified", item)
    return rows


def fixture_getter(path):
    """Offline mode: a JSON file {"get": {api path: response}, "files": {local path: text}}; nothing reaches Paperclip."""
    fx = json.loads(read_text(path))

    def get(p):
        if p not in fx["get"]:
            raise urllib.error.HTTPError(p, 404, "not in fixture", {}, None)
        return fx["get"][p]
    return get, (lambda f: fx.get("files", {}).get(f))


def read_local_file(path):
    try:
        return read_text(os.path.expanduser(path))
    except OSError:
        return None


def main(argv=None, get=http_get, read_local=read_local_file):
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    p.add_argument("--fixtures", help="offline: read every API response from this JSON fixture file (tests)")
    a = p.parse_args(argv)
    if a.fixtures:
        get, read_local = fixture_getter(a.fixtures)
    bp = _load("build-package")
    si = _load("sync-instructions")
    grp = _load("gen-role-packages")
    conf = json.loads(read_text(os.path.join(REPO, "config", "paperclip", "agents.json")))
    mpath = os.path.join(REPO, "config", "paperclip", "knowledge-manifest.json")
    manifest = json.loads(read_text(mpath)) if os.path.isfile(mpath) else {}
    company = next((c for c in get("/companies")
                    if a.company in (c["id"], c.get("issuePrefix")) or c["name"].lower() == a.company.lower()), None)
    if not company:
        print(f"no company matches {a.company!r}")
        return 2
    agents_full, live_bodies, live_skills = {}, {}, {}
    for ag in get(f"/companies/{company['id']}/agents"):
        agents_full[ag["urlKey"]] = get(f"/agents/{ag['id']}")
        q = urllib.parse.urlencode({"path": "AGENTS.md"})
        try:
            live_bodies[ag["urlKey"]] = (get(f"/agents/{ag['id']}/instructions-bundle/file?{q}") or {}).get("content", "")
        except urllib.error.URLError:
            live_bodies[ag["urlKey"]] = ""
    findings = drift(conf, company, agents_full, si.role_bodies(), live_bodies, bp)
    for f in findings:
        print(f)
    print(f"{len(findings)} drift finding(s) for {company['name']} ({company.get('issuePrefix')})")

    # Extended checks: GET only, plus a local read of a --settings file named in extraArgs.
    try:
        company_full = get(f"/companies/{company['id']}")
    except urllib.error.URLError:
        company_full = {}
    skills_index = None
    for slug, live in agents_full.items():
        desired = (((live.get("adapterConfig") or {}).get("paperclipSkillSync") or {}).get("desiredSkills")) or []
        role_skills = {s["name"] for s in ((manifest.get("roles") or {}).get(slug) or {}).get("skills", [])}
        for d in desired:
            name = d.split("/")[-1]
            if name not in role_skills:
                continue
            if skills_index is None:
                try:
                    skills_index = get(f"/companies/{company['id']}/skills") or []
                except urllib.error.URLError:
                    skills_index = []
            items = skills_index.get("items", []) if isinstance(skills_index, dict) else skills_index
            sk = next((s for s in items if s.get("slug") == name or s.get("key") == d), None)
            sk_def = manifest["skills"][name]
            files = {}
            for rel in ("SKILL.md", sk_def["reference_file"]):
                repo_path = f"{sk_def['dir']}/{rel}"
                content = None
                if sk:
                    try:
                        content = (get(f"/companies/{company['id']}/skills/{sk['id']}/files?"
                                       + urllib.parse.urlencode({"path": rel})) or {}).get("content")
                    except urllib.error.URLError:
                        content = None
                files[repo_path] = grp.sha256(content.replace("\r\n", "\n")) if content is not None else None
            live_skills[slug] = {"desired": desired, "files": files}
    rows = extended(conf, manifest, company_full, agents_full, live_bodies, si.role_bodies(), live_skills,
                    read_local, bp, grp)
    print("")
    print("Extended checks (read-only: GET /companies/{id}, GET /agents/{id} adapterConfig and permissions, "
          "GET instructions-bundle AGENTS.md, GET company skills only for an assigned repository skill, local read of a "
          "--settings file named in extraArgs):")
    for r in rows:
        print(f"  [{r['status']:10}] {r['category']:24} {r['role']:20} {r['detail']}")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("ok", "drift", "info", "unverified")}
    print(f"Extended: {counts['drift']} drift, {counts['ok']} ok, {counts['info']} info, {counts['unverified']} unverified "
          f"(categories: instructions.deployment, instructions.source, skills.assigned, adapter.config, "
          f"adapter.permissions, adapter.company, memory.policy, unverified.runtime)")
    return 1 if findings or counts["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
