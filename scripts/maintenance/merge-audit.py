"""Read-only audit of the ADR-009 merge gate (Phase 4, P4-T03): merged PRs against their Paperclip Tasks.

    python -I scripts/maintenance/merge-audit.py --company Soucean [--company GAM] [--board-login <login>]

For every merged PR of the project repositories in config/paperclip/agents.json it finds the Task by the branch
prefix `<KEY>-` and reports:
- **unlinked:** a merged PR whose branch names no Task;
- **unknown Task:** a branch key matching no issue of the given companies;
- **no approval stage:** the Task's execution policy has no `approval` stage;
- **not done:** the Task is not `done` although its PR is merged;
- **merged before approval:** the PR was merged before Paperclip recorded the Task `done` (completedAt), the reverse
  of the ADR-009 order;
- **merged by another account:** someone other than the Board account merged.

**Limits:** Paperclip 2026.1023.0 has no endpoint for the stage-decision history. "Approved" is therefore read as
"done, with an approval stage, at or before the merge"; a fake approval through the `local_trusted` Board path (G-14)
cannot be told apart.

Reads only: Paperclip GETs (PAPERCLIP_URL, default http://127.0.0.1:3100/api) and `gh pr list` / `gh api user`.
Exit 1 when there is any finding.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
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
KEY = re.compile(r"^([A-Z]+-\d+)-")


def _ts(text):
    """ISO 8601 with or without fractions and with a trailing Z; compared as times, never as strings."""
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def audit(issues, prs, board_login):
    """Pure check. issues: key -> {status, stages, completedAt}; prs: [{repo, number, branch, mergedAt, mergedBy}]."""
    out = []
    for p in sorted(prs, key=lambda p: (p["repo"], p["number"])):
        ref = f"{p['repo']}#{p['number']}"
        m = KEY.match(p.get("branch") or "")
        if not m:
            out.append(f"{ref}: unlinked: branch {p.get('branch')!r} names no Task")
            continue
        key = m.group(1)
        i = issues.get(key)
        if i is None:
            out.append(f"{ref}: unknown Task {key}")
            continue
        if board_login and p.get("mergedBy") and p["mergedBy"] != board_login:
            out.append(f"{ref} ({key}): merged by another account ({p['mergedBy']})")
        if "approval" not in (i.get("stages") or []):
            out.append(f"{ref} ({key}): no approval stage on the Task")
        if i.get("status") != "done":
            out.append(f"{ref} ({key}): Task is {i.get('status')}, not done, although the PR is merged")
        elif i.get("completedAt") and p.get("mergedAt") and _ts(i["completedAt"]) > _ts(p["mergedAt"]):
            out.append(f"{ref} ({key}): merged before approval (merged {p['mergedAt']}, done {i['completedAt']})")
    return out


def _get(path):
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


def _gh(args):
    p = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {p.stderr.strip()[:200]}")
    return p.stdout


def collect_issues(companies, get=_get):
    issues = {}
    for c in get("/companies"):
        if not any(ref in (c["id"], c.get("issuePrefix")) or c["name"].lower() == ref.lower() for ref in companies):
            continue
        after, rows = None, []
        while True:  # keyset pages, as pc.py list_issues does
            q = f"/companies/{c['id']}/issues?limit=500&sortField=id&sortDir=asc" + (f"&afterId={after}" if after else "")
            page = get(q) or []
            rows += page
            if len(page) < 500:
                break
            after = page[-1]["id"]
        for row in rows:
            full = get(f"/issues/{row['id']}")
            issues[full["identifier"]] = {"status": full.get("status"), "completedAt": full.get("completedAt"),
                                          "stages": [s.get("type") for s in
                                                     (full.get("executionPolicy") or {}).get("stages", [])]}
    return issues


def collect_prs(repos, gh=_gh):
    prs = []
    for repo in repos:
        rows = json.loads(gh(["pr", "list", "-R", repo, "--state", "merged", "--limit", "500", "--json",
                              "number,headRefName,mergedAt,mergedBy"]))
        prs += [{"repo": repo, "number": r["number"], "branch": r["headRefName"], "mergedAt": r["mergedAt"],
                 "mergedBy": (r.get("mergedBy") or {}).get("login")} for r in rows]
    return prs


def main(argv=None, get=_get, gh=_gh):
    p = argparse.ArgumentParser()
    p.add_argument("--company", action="append", required=True, help="company name, prefix or id (repeatable)")
    p.add_argument("--board-login", help="the GitHub account allowed to merge (default: the gh login)")
    a = p.parse_args(argv)
    conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
    repos = sorted({pr["repo"] for pr in conf.get("projects", {}).values() if pr.get("repo")})
    board = a.board_login or json.loads(gh(["api", "user"])).get("login")
    findings = audit(collect_issues(a.company, get), collect_prs(repos, gh), board)
    for f in findings:
        print(f)
    print(f"{len(findings)} finding(s) across {', '.join(repos)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
