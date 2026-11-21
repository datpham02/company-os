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
            out.append(f"{slug}: AGENTS.md differs from the role file (run sync-instructions.py --dry-run)")
    known = set(conf["agents"])
    for slug in sorted(set(agents_full) - known):
        out.append(f"{slug}: in the company but not in agents.json")
    return out


def main(argv=None, get=http_get):
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    a = p.parse_args(argv)
    bp = _load("build-package")
    si = _load("sync-instructions")
    conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
    company = next((c for c in get("/companies")
                    if a.company in (c["id"], c.get("issuePrefix")) or c["name"].lower() == a.company.lower()), None)
    if not company:
        print(f"no company matches {a.company!r}")
        return 2
    agents_full, live_bodies = {}, {}
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
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
