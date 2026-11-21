"""Paperclip control for the Game Studio Board Operator, through Paperclip's REST API.

Stdlib only. Run with: python -I .claude/skills/paperclip/scripts/pc.py <command> [args]
Requires Paperclip in local_trusted mode on loopback (Board context without login).

Environment: PAPERCLIP_URL (default http://127.0.0.1:3100/api), PAPERCLIP_COMPANY (name, prefix or id;
default: the only active company).
"""
import argparse
import datetime
import fnmatch
import json
import re
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# python -I leaves the script folder off sys.path; append it (after the standard library) for review_pack.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import review_pack  # noqa: E402  (OQ-042 Phase 1: local only, no git, GitHub or Paperclip)
import review_relay  # noqa: E402  (OQ-042 Phase 4a: Verdict Relay)

API =os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
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
    if len(active) > 1:
        # Several companies: prefer the one named in config/paperclip/agents.json (the live company).
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            conf = json.load(open(os.path.join(here, "..", "..", "..", "..", "config", "paperclip", "agents.json"), encoding="utf-8"))
            live = [c for c in active if c["name"].lower() == conf["company"]["name"].lower()]
            if len(live) == 1:
                return live[0]
        except (OSError, KeyError, ValueError):
            pass
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


ISSUE_PAGE_LIMIT = 1000  # Paperclip's ISSUE_LIST_MAX_LIMIT; the default page is 500


def list_issues(cid, status=None):
    """Every issue of a company (optionally of the given comma-separated statuses), all pages.

    The list endpoint is paginated (Paperclip 2026.1023.0: limit default 500, max 1000). Pages are read with its
    keyset cursor (sortField=id, sortDir=asc, afterId=<last id>), which needs no offset and does not skip rows
    when issues change between pages. Reading ends at the first empty page. Raises ApiError on any request failure or unexpected page, so a partial
    read is never returned as a complete list.
    """
    rows, after = [], None
    while True:
        q = {"limit": ISSUE_PAGE_LIMIT, "sortField": "id", "sortDir": "asc"}
        if status:
            q["status"] = status
        if after:
            q["afterId"] = after
        page = call("GET", f"/companies/{cid}/issues?" + urllib.parse.urlencode(q))
        if not isinstance(page, list):
            raise ApiError("the issue list came back in an unexpected shape")
        if any(not isinstance(r, dict) or not r.get("id") for r in page):
            raise ApiError("the issue list has a row without an id")
        if page and after is not None and page[0]["id"] <= after:
            raise ApiError("the issue list did not advance past the previous page")
        if not page:  # stop only on an empty page: a short page may be the server's cap or read filter
            return rows
        rows.extend(page)
        after = page[-1]["id"]


def agent_wip(rows, cid):
    """{agentId: [issue identifiers]} of the in_progress issues in rows, across all projects of company cid.

    WIP is task-contract.md §5 taken literally: issues whose status is `in_progress`. in_review, blocked, todo
    and the rest do not count. Issues without an agent assignee (the Board, a user) are skipped. A row missing
    a field needed to decide, or from another company, raises ApiError instead of being skipped.
    """
    wip = {}
    for r in rows:
        if not isinstance(r, dict) or not r.get("id") or any(k not in r for k in ("status", "companyId", "assigneeAgentId")):
            raise ApiError("an issue row lacks id, status, companyId or assigneeAgentId, so WIP cannot be verified")
        if r["companyId"] != cid:
            raise ApiError(f"the issue list for company {cid} returned an issue of another company")
        if r["status"] != "in_progress" or not r["assigneeAgentId"]:
            continue
        wip.setdefault(r["assigneeAgentId"], []).append(r.get("identifier") or r["id"][:8])
    for keys in wip.values():
        keys.sort()
    return wip


def company_wip(cid):
    """Current WIP of every agent of the company, from one complete in_progress listing."""
    return agent_wip(list_issues(cid, "in_progress"), cid)


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


WRITE_SET_HEADING = re.compile(r"^#+\s*(write set|files? owned|file ownership|affected (areas|files))", re.I | re.M)
UNBLOCK_OWNER = re.compile(r"^\W*unblock owner\W*:", re.I | re.M)


# ---------- write set conflict guard (task-contract.md §4.1) ----------
#
# Every `release` runs this guard; --force does not skip it. It compares the candidate's Write Set with the
# Write Set of every unmerged Task of the same project and refuses the release on any overlap.
#
# Write Set format (task-contract.md §2): list items under a `## Write set` heading (also accepted: the other
# WRITE_SET_HEADING forms). A path is the item's code span (`src/a.ts`), or its first word when it has none.
# Paths are relative to the project repository. Globs are allowed (*, ?, [...], **). One item `none` = no files.
#
# "Unmerged" (verified against Paperclip 2026.1023.0, services/execution-workspaces.js):
# - todo, in_progress, in_review, blocked, and any status this script does not know: compared;
# - backlog: compared only when it has its own execution workspace (work started, then parked);
# - done: compared unless its workspace shows the merge: deliveryState merged_via_pr / merged_by_ancestry, or the
#   workspace was archived by Paperclip's terminal reaper (cleanupReason "issue_terminal"), which archives only
#   after it has verified the merge. A done Task with no execution workspace has no branch Paperclip knows of
#   and is not compared;
# - cancelled: not compared.

GLOB_CHARS = "*?["
MERGED_DELIVERY_STATES = {"merged_via_pr", "merged_by_ancestry"}
REAPER_CLEANUP_REASON = "issue_terminal"
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.*\S)\s*$")
CODE_SPAN = re.compile(r"`([^`]+)`")
NO_FILES = {"none", "nothing", "n/a", "no files"}


class WriteSetError(Exception):
    """A Write Set that cannot be read, so overlap cannot be ruled out."""


def _looks_like_path(text):
    return bool(text) and not re.search(r"[\s()]", text) and bool(re.search(r"[/\\.*?\[]", text))


def normalize_path(raw):
    """Project-relative path -> tuple of segments. Rejects absolute paths and '..'."""
    p = raw.strip().replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        raise WriteSetError(f"absolute path {raw!r}; use a path relative to the project repository")
    segments = tuple(s for s in p.split("/") if s not in ("", "."))
    if ".." in segments:
        raise WriteSetError(f"path {raw!r} leaves the project ('..')")
    if not segments:
        raise WriteSetError(f"path {raw!r} names the whole repository; list the files or folders")
    return segments


def parse_write_set(description):
    """Paths of the Write Set as segment tuples. [] means the Task declares no files. Raises WriteSetError."""
    lines = (description or "").splitlines()
    start = next((n for n, ln in enumerate(lines) if WRITE_SET_HEADING.match(ln)), None)
    if start is None:
        raise WriteSetError("no '## Write set' section")
    items = []
    for ln in lines[start + 1:]:
        if re.match(r"^\s*#", ln):
            break
        m = LIST_ITEM.match(ln)
        if m:
            items.append(m.group(1))
    if not items:
        raise WriteSetError("the '## Write set' section lists no paths")
    if len(items) == 1 and items[0].strip("`. ").lower() in NO_FILES:
        return []
    paths = []
    for item in items:
        if item.count("`") % 2:
            raise WriteSetError(f"item {item!r} has an unclosed backtick")
        spans = CODE_SPAN.findall(item)
        if spans:
            if not _looks_like_path(spans[0].strip()):
                raise WriteSetError(f"item {item!r} does not start with a path")
            raw = [s.strip() for s in spans if _looks_like_path(s.strip())]
        else:
            first = item.split()[0].rstrip(",;:")
            if not _looks_like_path(first):
                raise WriteSetError(f"item {item!r} is not a path; write paths in backticks")
            raw = [first]
        paths.extend((r, normalize_path(r)) for r in raw)
    return paths


def _literal_ends(seg):
    cut = [seg.find(c) for c in GLOB_CHARS if c in seg]
    first, last = min(cut), max(seg.rfind(c) for c in "*?]")
    return seg[:first], seg[last + 1:]


def _segment_overlap(a, b):
    a, b = a.casefold(), b.casefold()
    ga, gb = any(c in a for c in GLOB_CHARS), any(c in b for c in GLOB_CHARS)
    if not ga and not gb:
        return a == b
    if ga and not gb:
        return fnmatch.fnmatchcase(b, a)
    if gb and not ga:
        return fnmatch.fnmatchcase(a, b)
    # Two patterns: overlap is possible when their literal prefixes and suffixes agree (conservative).
    (pa, sa), (pb, sb) = _literal_ends(a), _literal_ends(b)
    return (pa.startswith(pb) or pb.startswith(pa)) and (sa.endswith(sb) or sb.endswith(sa))


def paths_overlap(left, right):
    """True when two Write Set entries can name the same file.

    An entry covers itself and everything below it, so a folder overlaps every path inside it. Comparison is
    case-insensitive: the studio runs on Windows, where `Scene.ts` and `scene.ts` are one file. `**` matches any
    depth, so the paths overlap once the segments before it match.
    """
    for x, y in zip(left, right):
        if "**" in x or "**" in y:
            return True
        if not _segment_overlap(x, y):
            return False
    return True


def comparison_reason(i):
    """Why issue i counts as unmerged work (its status label), or None when it is not compared."""
    status = i.get("status")
    ws = i.get("currentExecutionWorkspace") or {}
    if status == "cancelled":
        return None
    if status == "backlog":
        return "backlog, work started" if ws and ws.get("sourceIssueId") == i.get("id") else None
    if status == "done":
        if not ws:
            return None
        if ws.get("deliveryState") in MERGED_DELIVERY_STATES:
            return None
        if ws.get("status") in ("archived", "cleanup_failed") and (ws.get("cleanupReason") or "").startswith(REAPER_CLEANUP_REASON):
            return None
        return f"done, not merged (delivery {ws.get('deliveryState') or 'unknown'})"
    return status or "unknown status"


def find_write_set_conflicts(candidate_paths, others):
    """others: [(issue, reason)]. Returns (conflicts, unreadable), both in issue-number order.

    conflicts: [(issue, reason, [(candidate raw path, other raw path)])]; unreadable: [(issue, reason, error)].
    """
    conflicts, unreadable = [], []
    for o, reason in sorted(others, key=lambda x: (x[0].get("issueNumber") or 0, x[0].get("identifier") or "")):
        try:
            other_paths = parse_write_set(o.get("description"))
        except WriteSetError as e:
            unreadable.append((o, reason, str(e)))
            continue
        pairs = sorted({(cr, orr) for cr, cs in candidate_paths for orr, os_ in other_paths if paths_overlap(cs, os_)})
        if pairs:
            conflicts.append((o, reason, pairs))
    return conflicts, unreadable


def unmerged_project_issues(cand, cache):
    """Unmerged issues of the candidate's project, except the candidate: [(full issue, reason)].

    Raises WriteSetError when the candidate has no project, ApiError when Paperclip cannot be read.
    """
    pid, cid = cand.get("projectId"), cand.get("companyId")
    if not pid:
        raise WriteSetError("it has no project, so it cannot be compared with its project's other Tasks; set a project first")
    listing = list_issues(cid)
    out = []
    for s in listing:
        if s.get("id") == cand["id"] or s.get("status") == "cancelled":
            continue
        if "projectId" in s and s["projectId"] != pid:
            continue
        full = cache.get(s["id"])
        if full is None:
            full = cache[s["id"]] = issue(s["id"])  # the list omits the execution workspace
        if full.get("companyId") != cid or full.get("projectId") != pid:
            continue
        reason = comparison_reason(full)
        if reason:
            out.append((full, reason))
    return out


def write_set_guard(cand, cache):
    """Report lines when the release must stop, [] when the Write Set is clear. May raise ApiError."""
    title = f"{cand.get('identifier')} — {cand.get('title')}"
    try:
        candidate_paths = parse_write_set(cand.get("description"))
        others = unmerged_project_issues(cand, cache)
    except WriteSetError as e:
        return [f"Release blocked: the Write Set cannot be checked: {e}.", f"Candidate: {title}"]
    conflicts, unreadable = find_write_set_conflicts(candidate_paths, others)
    if not conflicts and not unreadable:
        return []
    out = ["Release blocked: Write Set conflicts detected." if conflicts else
           "Release blocked: other unmerged Tasks have a Write Set that cannot be checked.", "", f"Candidate: {title}"]
    for o, reason, pairs in conflicts:
        out.append(f"Conflicts with: {o.get('identifier')} — {o.get('title')} ({reason})")
        out += [f"  - {c}" if c == p else f"  - {c}  (overlaps {p})" for c, p in pairs]
    for o, reason, err in unreadable:
        out.append(f"Cannot check: {o.get('identifier')} — {o.get('title')} ({reason}): {err}")
    out.append("")
    if conflicts:
        out.append("Resolve the overlapping Write Set before releasing this task: narrow it, or add a blocker "
                   "relation and release after the other Task is merged.")
    if unreadable:
        out.append("Fix the Write Set of the Task(s) above so overlap can be checked.")
    if any(r.startswith("done") for _, r, _ in conflicts) or any(r.startswith("done") for _, r, _ in unreadable):
        out.append("A done Task counts until Paperclip sees its merge; after merging, update the project "
                   "repository's local main (git pull --ff-only origin main).")
    out.append("--force does not override this check.")
    return out


def wip_guard(i, reserved):
    """Report line when the assignee already holds its WIP slot (task-contract.md §5), else None.

    Hard check: --force does not skip it. Counts the company's in_progress issues in every project, plus
    `reserved` ({agentId: key}): issues released earlier in the same command, which are `todo` and not yet
    `in_progress`. May raise ApiError, which the caller treats as "WIP not verified" and refuses.
    """
    aid = i["assigneeAgentId"]
    held = [k for k in company_wip(i["companyId"]).get(aid, []) if k != i.get("identifier")]
    if aid in reserved and reserved[aid] not in held:  # its run may already have moved it to in_progress
        held.append(f"{reserved[aid]} (released earlier in this command)")
    if held:
        return f"assignee already has {', '.join(held)} in progress (WIP limit 1, all projects); --force does not override this check"
    return None


def release_problems(i):
    """Forceable task-contract checks (task-contract.md §2) before an issue may start. --force skips these only."""
    problems = []
    if not WRITE_SET_HEADING.search(i.get("description") or ""):
        problems.append("no '## Write set' in the description")
    if not ((i.get("executionPolicy") or {}).get("stages")):
        problems.append("no review or approval stage (agent-created tasks get none, G-10)")
    open_blockers = [b.get("identifier") for b in (i.get("blockedBy") or [])
                     if isinstance(b, dict) and b.get("status") != "done"]
    if open_blockers:
        problems.append("blockers not done: " + ", ".join(open_blockers))
    return problems


def cmd_release(a):
    # Hard guards (WIP, Write Set) run on every release before anything changes; --force skips neither.
    # Not atomic: two release commands run at the same moment can both pass the WIP check.
    reserved = {}  # agentId -> key released earlier in this command (now todo, not yet in_progress)
    cache = {}  # full issues fetched by the Write Set guard, reused across the keys of one release
    for key in a.keys:
        i = issue(key)
        if i["status"] != "backlog":
            print(f"{key}: not in backlog (status {i['status']}); left unchanged")
            continue
        if not i.get("assigneeAgentId"):
            print(f"{key}: has no agent assignee; assign it first")
            continue
        try:
            busy = wip_guard(i, reserved)
        except ApiError as e:
            print(f"{key}: not released: WIP could not be verified ({e}). Nothing was changed.")
            continue
        if busy:
            print(f"{key}: not released: {busy}. Nothing was changed.")
            continue
        try:
            report = write_set_guard(i, cache)
        except ApiError as e:
            print(f"{key}: not released: the Write Set conflict check could not read Paperclip ({e}). Nothing was changed.")
            continue
        if report:
            print(f"{key}: not released.\n" + "\n".join(report))
            continue
        problems = release_problems(i)
        if problems and not a.force:
            print(f"{key}: not released: " + "; ".join(problems) + ". Fix it, or pass --force if the Board accepts it.")
            continue
        ws = i.get("currentExecutionWorkspace") or {}
        if ws.get("sourceIssueId") and ws["sourceIssueId"] != i["id"]:
            # Issues created inside another issue's run inherit that run's worktree (gap G-10).
            call("PATCH", f"/issues/{i['id']}", {"executionWorkspaceId": None, "executionWorkspacePreference": "isolated_workspace"})
            print(f"{key}: detached from inherited workspace {ws.get('name')}; it gets its own worktree")
        res = call("PATCH", f"/issues/{i['id']}", {"status": "todo"})
        cache[i["id"]] = {**i, "status": res.get("status", "todo")}  # later keys compare against it
        reserved[i["assigneeAgentId"]] = key  # later keys of this command see the occupied slot
        print(f"{key}: released -> {res['status']} (the assignee is woken now)"
              + (f"; accepted with: {'; '.join(problems)}" if problems else ""))


def hours_since(ts):
    if not ts:
        return 0.0
    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600


def cmd_triage(a):
    """Read-only sweep for knowledge/company/workflows/daily-triage.md. Changes nothing."""
    c = company(a.company)
    n = names(c["id"])
    summaries = [i for i in list_issues(c["id"]) if i["status"] not in ("done", "cancelled")]
    full = [issue(s["id"]) for s in summaries]  # the list endpoint omits blockers and execution state
    sections = {k: [] for k in ("Needs the Board", "Blocked", "Review stalled", "Quiet", "Ready to release", "WIP")}
    for i in full:
        key, status, age = i["identifier"], i["status"], hours_since(i.get("updatedAt"))
        title = i["title"][:60]
        part = ((i.get("executionState") or {}).get("currentParticipant") or {})
        blockers = [b for b in (i.get("blockedBy") or []) if isinstance(b, dict)]
        cancelled = [b.get("identifier") for b in blockers if b.get("status") == "cancelled"]
        open_blockers = [b.get("identifier") for b in blockers if b.get("status") != "done"]
        if cancelled:
            sections["Blocked"].append((age, f"{key} {status}: blocker(s) {', '.join(cancelled)} cancelled; they never resolve. Re-point or remove the relation | {title}"))
        if i.get("assigneeUserId") or part.get("type") == "user":
            why = "pending Board approval" if part.get("type") == "user" else "assigned to the Board"
            sections["Needs the Board"].append((age, f"{key} {status}, {why}, {age:.0f}h | {title}"))
        elif status == "blocked":
            since = hours_since(i.get("blockedTransitionAt") or i.get("updatedAt"))
            comments = call("GET", f"/issues/{i['id']}/comments") or []
            owner = next((ln.split(":", 1)[1].strip() for ln in (comments[0].get("body") or "").splitlines()
                          if UNBLOCK_OWNER.match(ln)), None) if comments else None
            note = f"owner {owner}" if owner else "NO unblock owner in the last comment"
            if blockers and not open_blockers:
                note += "; all blockers are done, so it should move"
            sections["Blocked"].append((since, f"{key} on {who(i, n)}, {since:.0f}h, {note} | {title}"))
        elif status == "in_review" and part.get("type") == "agent":
            started = i.get("updatedAt") or ""
            if not any(r.get("agentId") == part.get("agentId") and (r.get("createdAt") or "") >= started for r in runs(i["id"])) and age > 0.05:
                sections["Review stalled"].append((age, f"{key} waiting on {n.get(part.get('agentId'), '?')} with no run, {age:.1f}h | {title}"))
        elif status == "in_progress":
            if age >= a.quiet_hours:
                sections["Quiet"].append((age, f"{key} on {who(i, n)}, no update for {age:.0f}h | {title}"))
        elif status == "backlog" and not open_blockers:
            sections["Ready to release"].append((age, f"{key} on {who(i, n)}, waiting {age:.0f}h | {title}"))
    # Same calculation as the release gate, across every project of the company.
    try:
        wip = company_wip(c["id"])
    except ApiError as e:
        wip = None
        sections["WIP"].append((0, f"COULD NOT CHECK WIP: {e}. WIP is unknown, not clear"))
    for agent_id, keys in sorted((wip or {}).items(), key=lambda kv: n.get(kv[0], kv[0])):
        if len(keys) > 1:
            sections["WIP"].append((0, f"{n.get(agent_id, agent_id[:8])} has {len(keys)} in progress (limit 1): {', '.join(keys)}"))
    print(f"Triage for {c['name']} ({len(full)} open issues)")
    for title, rows in sections.items():
        print(f"\n{title}:")
        for _, line in sorted(rows, key=lambda r: -r[0]):
            print("  " + line)
        if not rows:
            print("  (none)")


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


# ---------- start gate: only `release` starts a task (task-contract.md §2, P0.3) ----------
#
# Wake rules read from Paperclip 2026.1023.0 (routes/issues.js, services/issue-assignment-wakeup.js,
# services/issue-comment-wakeup.js):
# - creating or reassigning an issue wakes its agent assignee unless the issue is `backlog` (or closed);
# - moving an issue out of `backlog` wakes its agent assignee;
# - a comment by anyone but the assignee wakes the assignee unless the issue is done or cancelled, backlog
#   included; the comment API has no option to post without waking.
# So create, assign and comment refuse anything that would start an unreleased issue, and only `release`
# (with its WIP and Write Set guards) moves an issue out of backlog. --force does not apply to these refusals.

START_ONLY_BY_RELEASE = "only `release` starts a task, after its WIP and Write Set checks"


class GateError(ApiError):
    """A command refused because it would start a task outside `release`."""


def cmd_comment(a):
    i = issue(a.key)
    if i.get("status") == "backlog" and i.get("assigneeAgentId"):
        raise GateError(f"{a.key} is backlog and assigned to an agent; a Board comment wakes that agent and it starts "
                        f"the task ({START_ONLY_BY_RELEASE}). Release it first, or put the note in its description.")
    call("POST", f"/issues/{i['id']}/comments", {"body": a.text})
    print(f"{a.key}: comment posted")


def cmd_assign(a):
    if a.status == "todo":
        raise GateError(f"assign --status todo is not allowed: {START_ONLY_BY_RELEASE}. "
                        f"Assign it in backlog, then run: release {a.key}")
    i = issue(a.key)
    status = i.get("status")
    if status not in ("backlog", "done", "cancelled") and a.status != "backlog":
        raise GateError(f"{a.key} is {status}; Paperclip wakes a new agent assignee at once unless the issue is backlog, "
                        f"which would skip release's checks. Park and hand it over with: assign {a.key} {a.agent} "
                        f"--status backlog, then: release {a.key}")
    ag = agent(i["companyId"], a.agent)
    # Clear a user assignee (e.g. the Board after a stuck review): Paperclip allows only one assignee.
    body = {"assigneeAgentId": ag["id"], "assigneeUserId": None}
    if a.status and a.status != status:
        body["status"] = a.status
    res = call("PATCH", f"/issues/{i['id']}", body)
    print(f"{a.key}: assigned to {ag['name']} | status {res['status']}"
          + (f" (not started; run: release {a.key})" if res["status"] == "backlog" else ""))


def cmd_create(a):
    if a.status == "todo":
        raise GateError(f"create --status todo is not allowed: {START_ONLY_BY_RELEASE}. "
                        "Create it in backlog, then release it")
    c = company(a.company)
    desc = open(a.desc_file, encoding="utf-8").read() if a.desc_file else (a.desc or "")
    ag = agent(c["id"], a.assignee)
    stages = [{"type": "review", "participants": [{"type": "agent", "agentId": agent(c["id"], r)["id"]}]} for r in a.review]
    if not a.no_approval:
        stages.append({"type": "approval", "participants": [{"type": "user", "userId": BOARD_USER}]})
    # Always backlog: an assigned backlog issue wakes nobody. The Board is not inside a run, so Paperclip does
    # not make it inherit a run's workspace; no parentId or workspace field is sent.
    body = {"title": a.title, "description": desc, "assigneeAgentId": ag["id"], "status": "backlog"}
    if a.project:
        body["projectId"] = project(c["id"], a.project)["id"]
    if stages:
        body["executionPolicy"] = {"stages": stages}
    i = call("POST", f"/companies/{c['id']}/issues", body)
    print(f"created {i['identifier']} | {ag['name']} | status {i['status']} | stages: "
          + (" -> ".join(s["type"] for s in stages) or "none")
          + f" | not started; run: release {i['identifier']}")


def cmd_wake(a):
    target = issue(a.issue) if a.issue else None
    if target and target.get("status") == "backlog":
        raise GateError(f"{a.issue} is backlog; waking an agent on it starts unreleased work ({START_ONLY_BY_RELEASE}). "
                        f"Run: release {a.issue}")
    c = company(a.company)
    ag = agent(c["id"], a.agent)
    payload = {"issueId": target["id"]} if target else {}
    r = call("POST", f"/agents/{ag['id']}/wakeup?companyId={c['id']}",
             {"source": "on_demand", "triggerDetail": "manual", "reason": a.reason, "payload": payload})
    print(f"woke {ag['name']}: run {r.get('id')} {r.get('status')}")


def cmd_cancel_run(a):
    call("POST", f"/heartbeat-runs/{a.run_id}/cancel", {})
    print(f"run {a.run_id} cancelled")


def cmd_review_relay(a):
    review_relay.cmd_review_relay(a, call, lambda: agent(company(a.company)["id"], review_pack.REVIEWER_AGENT)["id"])


def cmd_review_start(a):
    review_relay.cmd_review_start(a, call, lambda: company(a.company)["id"],
                                  lambda: agent(company(a.company)["id"], review_pack.REVIEWER_AGENT)["id"])


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
    s = sub.add_parser("release", help="backlog -> todo; wakes the assignee (task-contract checks first)")
    s.add_argument("keys", nargs="+")
    s.add_argument("--force", action="store_true", help="release despite failed task-contract checks (Board decision); never skips the Write Set conflict guard")
    s.set_defaults(fn=cmd_release)
    s = sub.add_parser("triage", help="read-only sweep: Board queue, blocked, stalled, quiet, ready, WIP")
    s.add_argument("--quiet-hours", type=float, default=24, help="in_progress with no update for this long is 'quiet'")
    s.set_defaults(fn=cmd_triage)
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
    s = sub.add_parser("comment", help="post a Board comment (refused on an agent-assigned backlog issue: it would wake the agent)")
    s.add_argument("key")
    s.add_argument("text")
    s.set_defaults(fn=cmd_comment)
    s = sub.add_parser("assign", help="assign an issue to an agent; never starts it (use release)")
    s.add_argument("key")
    s.add_argument("agent")
    s.add_argument("--status", choices=["backlog", "todo"],
                   help="backlog: park a started issue while handing it over; todo is refused (use release)")
    s.set_defaults(fn=cmd_assign)
    s = sub.add_parser("create", help="create an issue in backlog with a Board approval stage; start it with release")
    s.add_argument("--title", required=True)
    s.add_argument("--assignee", required=True)
    s.add_argument("--project")
    s.add_argument("--desc")
    s.add_argument("--desc-file")
    s.add_argument("--review", action="append", default=[], help="reviewer agent (repeatable, in order)")
    s.add_argument("--no-approval", action="store_true", help="skip the Board approval stage")
    s.add_argument("--status", choices=["backlog", "todo"], default="backlog", help="todo is refused (use release)")
    s.set_defaults(fn=cmd_create)
    s = sub.add_parser("wake", help="wake an agent now (refused with --issue on a backlog issue)")
    s.add_argument("agent")
    s.add_argument("--issue")
    s.add_argument("--reason", default="Woken by the Board Operator")
    s.set_defaults(fn=cmd_wake)
    s = sub.add_parser("cancel-run", help="cancel a queued or running run")
    s.add_argument("run_id")
    s.set_defaults(fn=cmd_cancel_run)
    review_pack.add_parser(sub)
    review_relay.add_parser(sub, cmd_review_relay)
    review_relay.add_start_parser(sub, cmd_review_start)
    a = p.parse_args()
    try:
        a.fn(a)
    except (ApiError, review_pack.ReviewPackError) as e:
        print("error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
