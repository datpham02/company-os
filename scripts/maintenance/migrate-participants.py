"""Stage-participant migration for the authentication switch (D-AUTH-02; A4 VA-4 to VA-6).

    python -I scripts/maintenance/migrate-participants.py --company SOU                 # dry run (default)
    python -I scripts/maintenance/migrate-participants.py --company SOU --apply --backup <file.sql.gz>
    python -I scripts/maintenance/migrate-participants.py --company SOU --from <claimant id> --to local-board ...
                                                                                       # rollback (VA-6)

Finds every open issue (not done, not cancelled) whose execution policy names the user `--from` (default
`local-board`) as a stage participant, and plans the change to `--to` (default: the Board identity from
GET /cli-auth/me, i.e. the claimed user once Paperclip runs in authenticated mode).

Method, exactly as verified in A.4:
- `PATCH /issues/:id` with `executionPolicy` = the stored policy with only that participant's `userId` changed, and
  `expectedExecutionPolicy` = the stored policy (VA-4: 200, ids, order, state, status and assignee unchanged);
- a stale policy is refused by Paperclip with 409 (VA-4b); the script stops;
- **skip** when the target is already a participant of the same stage: Paperclip would silently drop one entry
  (VA-4c hazard);
- **skip** when `--from` is the current participant (any status): Paperclip refuses with 422 (VA-5, verified for
  `in_review`).
  Such an issue needs a Board decision while `local-board` can still act (D-AUTH-02 step 1, e.g. SOU-28);
- after each PATCH the issue is read again and compared: stage ids, participant ids, order, status, assignees and
  executionState must be unchanged. The first mismatch stops the run.

Never used: the Board override that clears a stage without a decision (A1 1.4). Done and cancelled issues are
never changed. `--apply` needs `--backup` naming an existing database backup file (paperclipai db:backup) and
a Board authorization for the live migration (Phase D); the dry run only reads.
Stdlib only; Paperclip at PAPERCLIP_URL (default http://127.0.0.1:3100/api), Board credential via board_auth.py.
"""
import argparse
import copy
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
API = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
CLOSED = {"done", "cancelled"}
KEPT = ("status", "assigneeAgentId", "assigneeUserId", "executionState")


def _load_board_auth():
    import importlib.util
    path = os.path.join(REPO, ".claude", "skills", "paperclip", "scripts", "board_auth.py")
    spec = importlib.util.spec_from_file_location("board_auth", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


board_auth = _load_board_auth()


class Stop(Exception):
    pass


def http(method, path, body=None):
    try:
        hdrs = dict(board_auth.headers(API), **{"Content-Type": "application/json"})
    except board_auth.AuthError as e:
        raise Stop(board_auth.redact(e))
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise Stop(board_auth.http_error(method, path, e.code, e.read().decode("utf-8", "replace")))


def plan(issue, src, dst):
    """(action, detail, new_policy). action: 'change', 'skip' or None (issue not affected)."""
    pol = issue.get("executionPolicy") or {}
    stages = pol.get("stages") or []
    hits = [(si, pi) for si, s in enumerate(stages) for pi, p in enumerate(s.get("participants") or [])
            if p.get("type") == "user" and p.get("userId") == src]
    if not hits or issue.get("status") in CLOSED:
        return None, "", None
    state = issue.get("executionState") or {}
    cur = state.get("currentParticipant") or {}
    if cur.get("type") == "user" and cur.get("userId") == src:
        return "skip", (f"{src} is the current participant: Paperclip refuses this update (VA-5, seen for "
                        "in_review); the Board decides it before the switch (D-AUTH-02 step 1)"), None
    new = copy.deepcopy(pol)
    for si, pi in hits:
        stage = new["stages"][si]
        if any(p.get("type") == "user" and p.get("userId") == dst for p in stage["participants"]):
            return "skip", (f"{dst} is already a participant of stage {stage.get('id') or si}: the update would "
                            "silently drop a participant (VA-4c)"), None
        stage["participants"][pi]["userId"] = dst
    stage_list = ", ".join(f"{new['stages'][si].get('type')} stage {new['stages'][si].get('id', si)}"
                           for si, _ in hits)
    return "change", f"{src} -> {dst} on {stage_list}", new


def shape(pol):
    """Ids and order of stages and participants: must survive the update unchanged."""
    return [(s.get("id"), s.get("type"), [(p.get("id"), p.get("type")) for p in s.get("participants") or []])
            for s in (pol or {}).get("stages") or []]


def verify(before, after, new_policy):
    problems = []
    if shape(after.get("executionPolicy")) != shape(before.get("executionPolicy")):
        problems.append("stage or participant ids/order changed")
    if shape(after.get("executionPolicy")) != shape(new_policy) or \
            json.dumps((after.get("executionPolicy") or {}).get("stages"), sort_keys=True) != \
            json.dumps(new_policy.get("stages"), sort_keys=True):
        problems.append("stored policy differs from the requested one")
    for k in KEPT:
        if after.get(k) != before.get(k):
            problems.append(f"{k} changed")
    return problems


def list_issues(cid, get):
    after, rows = None, []
    while True:
        page = get(f"/companies/{cid}/issues?limit=500&sortField=id&sortDir=asc" + (f"&afterId={after}" if after else ""))
        page = page or []
        rows += page
        if len(page) < 500:
            return rows
        after = page[-1]["id"]


def run(company, src, dst, apply, call=http, out=print):
    """Returns the number of issues that were skipped or failed (0 = clean)."""
    get = lambda p: call("GET", p)  # noqa: E731
    comp = next((c for c in get("/companies") if company in (c["id"], c.get("issuePrefix"))
                 or c["name"].lower() == company.lower()), None)
    if not comp:
        raise Stop(f"no company matches {company!r}")
    if dst in (None, "me"):
        dst = board_auth.board_user_id(call)
    if dst == src:
        raise Stop(f"--to resolves to {dst!r}, the same as --from; nothing to migrate (still local_trusted?)")
    out(f"{comp['name']} ({comp.get('issuePrefix')}): {src} -> {dst}, {'APPLY' if apply else 'dry run'}")
    bad = changes = 0
    for row in list_issues(comp["id"], get):
        if row.get("status") in CLOSED:
            continue
        issue = get(f"/issues/{row['id']}")
        action, detail, new = plan(issue, src, dst)
        if action is None:
            continue
        ident = issue.get("identifier") or issue["id"]
        if action == "skip":
            bad += 1
            out(f"  SKIP   {ident} ({issue.get('status')}): {detail}")
            continue
        changes += 1
        out(f"  {'CHANGE' if apply else 'PLAN  '} {ident} ({issue.get('status')}): {detail}")
        if not apply:
            continue
        call("PATCH", f"/issues/{issue['id']}",
             {"executionPolicy": new, "expectedExecutionPolicy": issue.get("executionPolicy")})
        after = get(f"/issues/{issue['id']}")
        problems = verify(issue, after, new)
        if problems:
            raise Stop(f"{ident}: verification failed after the update ({'; '.join(problems)}); stopping. "
                       "Roll back with --from/--to swapped, or restore the backup")
        out(f"         verified: ids, order, status, assignees and state unchanged")
    out(f"{changes} issue(s) {'changed' if apply else 'to change'}, {bad} skipped")
    return bad


def main(argv=None, call=http):
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True, help="company name, prefix or id")
    p.add_argument("--from", dest="src", default="local-board", help="participant user id to replace")
    p.add_argument("--to", dest="dst", default="me", help="new user id (default: the Board, GET /cli-auth/me)")
    p.add_argument("--apply", action="store_true", help="write the changes (Phase D, Board-authorized only)")
    p.add_argument("--backup", help="the database backup taken just before --apply (must exist)")
    a = p.parse_args(argv)
    try:
        if a.apply and not (a.backup and os.path.isfile(a.backup)):
            raise Stop("--apply needs --backup naming an existing database backup file (paperclipai db:backup)")
        return 1 if run(a.company, a.src, a.dst, a.apply, call) else 0
    except (Stop, board_auth.AuthError) as e:
        print(f"STOP: {board_auth.redact(e)}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
