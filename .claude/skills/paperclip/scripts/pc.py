"""Paperclip control for the Game Studio Board Operator, through Paperclip's REST API.

Stdlib only. Run with: python -I .claude/skills/paperclip/scripts/pc.py <command> [args]
Requires Paperclip in local_trusted mode on loopback (Board context without login).

Environment: PAPERCLIP_URL (default http://127.0.0.1:3100/api), PAPERCLIP_COMPANY (name, prefix or id;
default: the only active company).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
BOARD_USER = "local-board"
ACTIVE_RUN = {"queued", "starting", "running"}
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class ApiError(Exception):
    pass


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise ApiError(f"{method} {path} -> {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    except urllib.error.URLError as e:
        raise ApiError(f"Paperclip is not reachable at {API} ({e.reason}). Start it with runtime/tools/start-studio.cmd.")


# ---------- lookups ----------

def company(ref=None):
    ref = ref or os.environ.get("PAPERCLIP_COMPANY")
    active = [c for c in call("GET", "/companies") if c.get("status") == "active"]
    if ref:
        for c in active:
            if ref in (c["id"], c.get("issuePrefix")) or c["name"].lower() == ref.lower():
                return c
        raise ApiError(f"no active company matches {ref!r}")
    if len(active) != 1:
        raise ApiError("several active companies; pass --company or set PAPERCLIP_COMPANY: "
                       + ", ".join(f"{c['name']} ({c.get('issuePrefix')})" for c in active))
    return active[0]


def agents(cid):
    return call("GET", f"/companies/{cid}/agents")


def agent(cid, ref):
    ref_l = ref.lower()
    for a in agents(cid):
        if ref_l in (a["id"], (a.get("urlKey") or "").lower(), a["name"].lower()) or a["id"].startswith(ref_l):
            return a
    raise ApiError(f"no agent matches {ref!r}")


def project(cid, ref):
    for p in call("GET", f"/companies/{cid}/projects"):
        if ref in (p["id"],) or p["name"].lower() == ref.lower():
            return p
    raise ApiError(f"no project matches {ref!r}")


def issue(key):
    return call("GET", f"/issues/{urllib.parse.quote(key)}")


def names(cid):
    return {a["id"]: a["name"] for a in agents(cid)}


def who(i, agent_names):
    if i.get("assigneeAgentId"):
        return agent_names.get(i["assigneeAgentId"], i["assigneeAgentId"][:8])
    if i.get("assigneeUserId"):
        return "Board" if i["assigneeUserId"] == BOARD_USER else i["assigneeUserId"]
    return "-"


def stage(i):
    s = i.get("executionState") or {}
    if not s.get("currentStageType"):
        return ""
    return f"{s['currentStageType']} ({s.get('status')})"


def runs(issue_id):
    return call("GET", f"/issues/{issue_id}/runs") or []


# ---------- commands ----------

def cmd_health(a):
    h = call("GET", "/health")
    print(f"Paperclip {h.get('version')} {h.get('status')} | mode {h.get('deploymentMode')} | {API}")


def cmd_overview(a):
    c = company(a.company)
    n = names(c["id"])
    print(f"Company: {c['name']} (prefix {c.get('issuePrefix')})")
    print("\nProjects:")
    for p in call("GET", f"/companies/{c['id']}/projects"):
        print(f"  - {p['name']}")
    print("\nAgents:")
    for ag in agents(c["id"]):
        print(f"  - {ag['name']:20} {ag['adapterType']:13} {ag['status']}")
    print("\nOpen issues:")
    open_issues = [i for i in call("GET", f"/companies/{c['id']}/issues") if i["status"] not in ("done", "cancelled")]
    order = {"in_review": 0, "in_progress": 1, "blocked": 2, "todo": 3, "backlog": 4}
    for i in sorted(open_issues, key=lambda x: (order.get(x["status"], 9), x.get("issueNumber") or 0)):
        # The list endpoint omits blockers, so read them per issue.
        blockers = [b.get("identifier") for b in (issue(i["id"]).get("blockedBy") or [])
                    if isinstance(b, dict) and b.get("status") not in ("done", "cancelled")]
        after = f"  [after {', '.join(blockers)}]" if blockers else ("  [ready]" if i["status"] == "backlog" else "")
        print(f"  {i['identifier']:7} {i['status']:11} {who(i, n):20} {i['title'][:70]}{after}")
    if not open_issues:
        print("  (none)")


def cmd_show(a):
    i = issue(a.key)
    n = names(i["companyId"])
    print(f"{i['identifier']}: {i['title']}")
    print(f"status: {i['status']} | assignee: {who(i, n)} | stage: {stage(i) or '-'}")
    blocked = [b.get("identifier") or b.get("id", "")[:8] for b in (i.get("blockedBy") or []) if isinstance(b, dict)]
    if blocked:
        print("blocked by:", ", ".join(blocked))
    ws = i.get("currentExecutionWorkspace") or {}
    # Backlog issues created inside another issue's run inherit that run's workspace; it is not theirs.
    if ws.get("branchName") and i["status"] not in ("backlog", "todo"):
        print("branch:", ws["branchName"])
    if a.description and i.get("description"):
        print("\n--- description ---\n" + i["description"])
    comments = call("GET", f"/issues/{i['id']}/comments") or []
    print(f"\n--- last {min(a.comments, len(comments))} of {len(comments)} comments (newest first) ---")
    for c in comments[: a.comments]:
        author = n.get(c.get("authorAgentId")) or ("Board" if c.get("authorUserId") else "system")
        body = (c.get("body") or "").strip()
        print(f"\n[{c.get('createdAt', '')[:16]}] {author}:\n{body[: a.chars]}{' …' if len(body) > a.chars else ''}")
    print("\n--- runs (newest first) ---")
    for r in runs(i["id"])[:8]:
        print(f"  {r['runId']}  {n.get(r['agentId'], r['agentId'][:8]):20} {r['status']:15} {r.get('createdAt', '')[:16]}  {r.get('livenessReason') or ''}")


def cmd_log(a):
    log = call("GET", f"/heartbeat-runs/{a.run_id}/log") or {}
    parts = []
    for line in str(log.get("content", "")).splitlines():
        if not line.startswith("{"):
            continue
        try:
            parts.append(json.loads(line).get("chunk", ""))
        except json.JSONDecodeError:  # the log endpoint can cut the last line mid-record
            parts.append(line)
    text = "".join(parts)
    print(text[-a.tail:] if a.tail else text)


def cmd_release(a):
    for key in a.keys:
        i = issue(key)
        if i["status"] != "backlog":
            print(f"{key}: not in backlog (status {i['status']}); left unchanged")
            continue
        if not i.get("assigneeAgentId"):
            print(f"{key}: has no agent assignee; assign it first")
            continue
        ws = i.get("currentExecutionWorkspace") or {}
        if ws.get("sourceIssueId") and ws["sourceIssueId"] != i["id"]:
            # Issues created inside another issue's run inherit that run's worktree (gap G-10).
            call("PATCH", f"/issues/{i['id']}", {"executionWorkspaceId": None, "executionWorkspacePreference": "isolated_workspace"})
            print(f"{key}: detached from inherited workspace {ws.get('name')}; it gets its own worktree")
        res = call("PATCH", f"/issues/{i['id']}", {"status": "todo"})
        print(f"{key}: released -> {res['status']} (the assignee is woken now)")


def board_decision(a, status, label):
    i = issue(a.key)
    s = i.get("executionState") or {}
    participant = s.get("currentParticipant") or {}
    if i["status"] != "in_review" or participant.get("userId") != BOARD_USER:
        raise ApiError(f"{a.key} is not waiting on the Board (status {i['status']}, stage {stage(i) or '-'})")
    if not a.comment.strip():
        raise ApiError("a Board decision needs a comment")
    res = call("PATCH", f"/issues/{i['id']}", {"status": status, "comment": a.comment})
    rs = res.get("executionState") or {}
    print(f"{a.key}: {label} -> status {res['status']}, decision {rs.get('lastDecisionOutcome')}")


def cmd_approve(a):
    board_decision(a, "done", "approved")


def cmd_request_changes(a):
    board_decision(a, "in_progress", "changes requested")


def cmd_cancel(a):
    i = issue(a.key)
    if i["status"] in ("done", "cancelled"):
        raise ApiError(f"{a.key} is already {i['status']}")
    for r in runs(i["id"]):
        if r["status"] in ACTIVE_RUN | {"scheduled_retry"}:
            call("POST", f"/heartbeat-runs/{r['runId']}/cancel", {})
    res = call("PATCH", f"/issues/{i['id']}", {"status": "cancelled", "comment": a.comment})
    print(f"{a.key}: cancelled (was {i['status']}) -> {res['status']}")


def cmd_comment(a):
    i = issue(a.key)
    call("POST", f"/issues/{i['id']}/comments", {"body": a.text})
    print(f"{a.key}: comment posted")


def cmd_assign(a):
    i = issue(a.key)
    ag = agent(i["companyId"], a.agent)
    body = {"assigneeAgentId": ag["id"]}
    if a.status:
        body["status"] = a.status
    res = call("PATCH", f"/issues/{i['id']}", body)
    print(f"{a.key}: assigned to {ag['name']} | status {res['status']}")


def cmd_create(a):
    c = company(a.company)
    desc = open(a.desc_file, encoding="utf-8").read() if a.desc_file else (a.desc or "")
    ag = agent(c["id"], a.assignee)
    stages = [{"type": "review", "participants": [{"type": "agent", "agentId": agent(c["id"], r)["id"]}]} for r in a.review]
    if not a.no_approval:
        stages.append({"type": "approval", "participants": [{"type": "user", "userId": BOARD_USER}]})
    body = {"title": a.title, "description": desc, "assigneeAgentId": ag["id"], "status": a.status}
    if a.project:
        body["projectId"] = project(c["id"], a.project)["id"]
    if stages:
        body["executionPolicy"] = {"stages": stages}
    i = call("POST", f"/companies/{c['id']}/issues", body)
    print(f"created {i['identifier']} | {ag['name']} | status {i['status']} | stages: "
          + (" -> ".join(s["type"] for s in stages) or "none"))


def cmd_wake(a):
    c = company(a.company)
    ag = agent(c["id"], a.agent)
    payload = {"issueId": issue(a.issue)["id"]} if a.issue else {}
    r = call("POST", f"/agents/{ag['id']}/wakeup?companyId={c['id']}",
             {"source": "on_demand", "triggerDetail": "manual", "reason": a.reason, "payload": payload})
    print(f"woke {ag['name']}: run {r.get('id')} {r.get('status')}")


def cmd_cancel_run(a):
    call("POST", f"/heartbeat-runs/{a.run_id}/cancel", {})
    print(f"run {a.run_id} cancelled")


def main():
    p = argparse.ArgumentParser(prog="pc.py", description="Paperclip control for the Game Studio Board Operator")
    p.add_argument("--company", help="company name, issue prefix or id (default: the only active company)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="is Paperclip up").set_defaults(fn=cmd_health)
    sub.add_parser("overview", help="projects, agents and open issues").set_defaults(fn=cmd_overview)
    s = sub.add_parser("show", help="one issue: status, stage, comments, runs")
    s.add_argument("key")
    s.add_argument("--comments", type=int, default=3)
    s.add_argument("--chars", type=int, default=1500)
    s.add_argument("--description", action="store_true")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("log", help="text output of a run")
    s.add_argument("run_id")
    s.add_argument("--tail", type=int, default=4000, help="last N characters (0 = all)")
    s.set_defaults(fn=cmd_log)
    s = sub.add_parser("release", help="backlog -> todo; wakes the assignee")
    s.add_argument("keys", nargs="+")
    s.set_defaults(fn=cmd_release)
    for name, fn, helptext in (("approve", cmd_approve, "Board approves: status done + comment"),
                               ("request-changes", cmd_request_changes, "Board requests changes: back to the implementer")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("key")
        s.add_argument("comment")
        s.set_defaults(fn=fn)
    s = sub.add_parser("cancel", help="cancel an issue with a reason; stops its pending runs")
    s.add_argument("key")
    s.add_argument("comment")
    s.set_defaults(fn=cmd_cancel)
    s = sub.add_parser("comment", help="post a Board comment")
    s.add_argument("key")
    s.add_argument("text")
    s.set_defaults(fn=cmd_comment)
    s = sub.add_parser("assign", help="assign an issue to an agent")
    s.add_argument("key")
    s.add_argument("agent")
    s.add_argument("--status", choices=["backlog", "todo"])
    s.set_defaults(fn=cmd_assign)
    s = sub.add_parser("create", help="create an issue (default: backlog, Board approval stage)")
    s.add_argument("--title", required=True)
    s.add_argument("--assignee", required=True)
    s.add_argument("--project")
    s.add_argument("--desc")
    s.add_argument("--desc-file")
    s.add_argument("--review", action="append", default=[], help="reviewer agent (repeatable, in order)")
    s.add_argument("--no-approval", action="store_true", help="skip the Board approval stage")
    s.add_argument("--status", choices=["backlog", "todo"], default="backlog")
    s.set_defaults(fn=cmd_create)
    s = sub.add_parser("wake", help="wake an agent now")
    s.add_argument("agent")
    s.add_argument("--issue")
    s.add_argument("--reason", default="Woken by the Board Operator")
    s.set_defaults(fn=cmd_wake)
    s = sub.add_parser("cancel-run", help="cancel a queued or running run")
    s.add_argument("run_id")
    s.set_defaults(fn=cmd_cancel_run)
    a = p.parse_args()
    try:
        a.fn(a)
    except ApiError as e:
        print("error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
