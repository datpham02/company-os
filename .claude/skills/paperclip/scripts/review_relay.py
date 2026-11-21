"""OQ-042 Review Package Phase 4a: the Verdict Relay (docs/design/review-package.md §3).

Reads a finished code-reviewer run, checks it against the staged package and the live state (§3.4, fail closed),
then posts the findings as a comment with a relay receipt and records the decision (§3.5). Every Paperclip and
GitHub call goes through injected functions, so the whole flow is tested offline; no call is made at import.

Authority (§3.3): the relay acts as the identity that the CLI uses for Paperclip. It records a decision only
while that identity is the issue's active stage participant. Otherwise Paperclip refuses, and the Board decides
by hand (fallback).

Run binding (Option B, docs/design/review-package-post-phase5-assessment.md §3.5): `review-start` creates one
review sub-issue per staging (child of the reviewed issue, assigned to code-reviewer, no project) and wakes the
reviewer for it. The relay accepts only that sub-issue's run, named in the staging lock, and a verdict that
echoes the staging's reviewId and challenge (REVIEW-ID.txt, present only in the staged copy). This binds the
run to the staging and shows the verdict carries a value only the staged package held. It does not prove the
reviewer read or understood the package, and a same-user process could still tamper with staging (G-13, G-14).
"""
import hashlib
import hmac
import json
import os
import re
import time

import review_pack as rp

VERDICTS = {"approved", "changes_requested"}
SEVERITIES = {"critical", "high", "medium", "low"}
SIDES = {"head", "base"}
RUN_OK = "succeeded"
# P0 (docs/design/review-package-reviewer-write-isolation.md): the only tools a reviewer run may be offered.
REVIEWER_TOOLS = frozenset({"Glob", "Grep", "Read"})
REQUIRED_DENY = {"mcp__*", "Bash", "PowerShell", "WebFetch", "WebSearch", "Edit", "Write", "NotebookEdit"}
FORBIDDEN_FLAGS = {"--allowedTools", "--allowed-tools", "--dangerously-skip-permissions",
                   "--allow-dangerously-skip-permissions", "--mcp-config", "--permission-prompt-tool", "--tools-file"}
RECEIPT_RE = re.compile(r"relay-receipt: (\S+) ([0-9a-f]{40})")
FENCE_RE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n```", re.S)
STATUS_RE = re.compile(r"-> (\d{3})\b")
ATTEMPTS = 3


class Transient(Exception):
    pass


class RelayRefused(rp.ReviewPackError):
    """Every check passed, but recording failed or was refused; already audited as `relay-refused`."""


def _http_status(err):
    m = STATUS_RE.search(str(err))
    return int(m.group(1)) if m else None


def _with_retry(fn, sleep):
    """Network errors and 5xx: up to ATTEMPTS tries with backoff (§3.5). 4xx: no retry (re-raised)."""
    last = None
    for attempt in range(ATTEMPTS):
        try:
            return fn()
        except Exception as e:  # pc.ApiError, or anything the injected API raises
            code = _http_status(e)
            if code is not None and code < 500:
                raise
            last = e
            if attempt + 1 < ATTEMPTS:
                sleep(2 ** attempt)
    raise Transient(f"gave up after {ATTEMPTS} attempts: {last}")


# ---------- verdict parsing (§3.1) ----------

def _events(log):
    """The stream-json events of a run log (GET /heartbeat-runs/<id>/log), in order."""
    for line in "".join(_chunks(log)).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            yield ev


LOG_PAGE_BYTES = 1024 * 1024  # Paperclip's maximum page (server routes/agents.js RUN_LOG_MAX_LIMIT_BYTES)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fetch_verified_log(api, run_id, sleep):
    """Read the whole run log and prove it is the log Paperclip finalized for this run, before anything parses it.

    Paperclip 2026.1023.0 stores the log as one NDJSON file and, at finalize, records its size (`logBytes`) and
    SHA-256 (`logSha256`) on the run (server services/run-log-store.js sha256File/finalize). GET
    /heartbeat-runs/<id>/log serves that file in pages (`offset`, `limitBytes`, `nextOffset`). Every page is read,
    the UTF-8 text is joined and re-encoded, and its size and SHA-256 must equal the run record's. Fails closed on
    a missing or malformed hash, a compressed or non-local log, a page loop that does not advance, a size or hash
    mismatch, or any read failure. A page boundary inside a multi-byte character would also fail (refusal, not
    acceptance). Returns {"content": text} in the shape the parsers expect."""
    def get(path):
        try:
            return _with_retry(lambda: api("GET", path), sleep)
        except Transient:
            raise
        except Exception as e:
            raise rp.ReviewPackError(f"run {run_id}: {path} could not be read ({str(e)[:160]})") from None
    meta = get(f"/heartbeat-runs/{run_id}")
    if not isinstance(meta, dict) or meta.get("id") != run_id:
        raise rp.ReviewPackError(f"the run record returned for {run_id} is not that run")
    want, size = meta.get("logSha256"), meta.get("logBytes")
    if not isinstance(want, str) or not SHA256_RE.match(want):
        raise rp.ReviewPackError(f"run {run_id} has no finalized log hash (logSha256); its log cannot be verified")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise rp.ReviewPackError(f"run {run_id} has no finalized log size (logBytes)")
    if meta.get("logStore") != "local_file" or meta.get("logCompressed") is not False:
        raise rp.ReviewPackError(f"run {run_id}'s log is stored as {meta.get('logStore')} "
                                 f"(compressed: {meta.get('logCompressed')}); only plain local logs can be verified")
    parts, offset = [], 0
    while True:
        page = get(f"/heartbeat-runs/{run_id}/log?offset={offset}&limitBytes={LOG_PAGE_BYTES}")
        if not isinstance(page, dict) or not isinstance(page.get("content"), str):
            raise rp.ReviewPackError(f"run {run_id}: the log page at offset {offset} is malformed")
        parts.append(page["content"])
        nxt = page.get("nextOffset")
        if nxt is None:
            break
        # offsets strictly increase and never pass the recorded size, so the loop always ends
        if not isinstance(nxt, int) or isinstance(nxt, bool) or nxt <= offset or nxt > size:
            raise rp.ReviewPackError(f"run {run_id}: the log pages do not advance (offset {offset} -> {nxt})")
        offset = nxt
    text = "".join(parts)
    data = text.encode("utf-8")
    if len(data) != size:
        raise rp.ReviewPackError(f"run {run_id}: the log read has {len(data)} bytes, the run record says {size}")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), want):
        raise rp.ReviewPackError(f"run {run_id}: the log read does not match its recorded SHA-256; it is not accepted")
    return {"content": text}


def check_tool_surface(log):
    """Fail closed unless the run was offered exactly Read, Grep and Glob and used nothing else (P0 layer 3).

    An allow list, not a deny list: any other tool in an `init` event, including an MCP tool a future Paperclip
    version adds under a new name, refuses the verdict; so does a tool_use of another tool, or any permission
    denial (an attempt counts as tampering, even though it was refused)."""
    inits, uses, denials = [], [], []
    for ev in _events(log):
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            inits.append(ev)
        elif ev.get("type") == "assistant":
            for c in ((ev.get("message") or {}).get("content") or []):
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    uses.append(c.get("name"))
        elif ev.get("type") == "result":
            denials += [d.get("tool_name") if isinstance(d, dict) else d for d in (ev.get("permission_denials") or [])]
    if not inits:
        raise rp.ReviewPackError("the run log has no init event, so the reviewer's tools cannot be checked")
    for ev in inits:
        tools = ev.get("tools")
        if not isinstance(tools, list) or set(tools) != REVIEWER_TOOLS or len(tools) != len(REVIEWER_TOOLS):
            extra = sorted(set(map(str, tools or [])) - REVIEWER_TOOLS)
            missing = sorted(REVIEWER_TOOLS - set(map(str, tools or [])))
            raise rp.ReviewPackError(f"the reviewer run was offered tools other than Read, Grep and Glob "
                                     f"(extra {extra}, missing {missing}); its verdict is not accepted")
    other = sorted({str(u) for u in uses} - REVIEWER_TOOLS)
    if other:
        raise rp.ReviewPackError(f"the reviewer run used tools other than Read, Grep and Glob ({other})")
    if denials:
        raise rp.ReviewPackError(f"the reviewer run attempted refused tools ({sorted(map(str, denials))}); "
                                 "its verdict is not accepted")


def final_message(log):
    """The reviewer's final message from GET /heartbeat-runs/<id>/log: the `result` of the stream-json output."""
    result = None
    for ev in _events(log):
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            result = ev["result"]
    if result is None:
        raise rp.ReviewPackError("the run log has no final message (no result event)")
    return result


def _chunks(log):
    content = log.get("content", "") if isinstance(log, dict) else ""
    for line in str(content).splitlines():
        if not line.startswith("{"):
            continue
        try:
            yield json.loads(line).get("chunk", "")
        except ValueError:
            yield line


def parse_verdict(message):
    blocks = FENCE_RE.findall(message)
    if len(blocks) != 1:
        raise rp.ReviewPackError(f"the final message has {len(blocks)} json blocks; exactly one is required")
    if message[FENCE_RE.search(message).end():].strip():
        raise rp.ReviewPackError("the verdict block must end the final message")
    try:
        v = json.loads(blocks[0])
    except ValueError as e:
        raise rp.ReviewPackError(f"the verdict block is not valid JSON ({e})")
    if not isinstance(v, dict):
        raise rp.ReviewPackError("the verdict block is not a JSON object")
    return v


def _line_count(pkg, side, path, old):
    rel = ["files", side] + (old if side == "base" and old else path).split("/")
    p = os.path.join(pkg, *rel)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        data = f.read()
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def validate_verdict(v, lock, manifest, pkg):
    if v.get("schema") != rp.VERDICT_SCHEMA:
        raise rp.ReviewPackError(f"verdict schema is not {rp.VERDICT_SCHEMA}")
    if not isinstance(v.get("verdict"), str) or v.get("verdict") not in VERDICTS:
        raise rp.ReviewPackError(f"verdict {v.get('verdict')!r} is not one of {sorted(VERDICTS)}")
    if v.get("issue") != lock["issue"] or v.get("headSha") != lock["headSha"]:
        raise rp.ReviewPackError("the verdict's issue or headSha does not match the staging lock")
    if lock.get("challenge"):
        rid, ch = v.get("reviewId"), v.get("challenge")
        if not isinstance(rid, str) or rid != lock["reviewId"]:
            raise rp.ReviewPackError("the verdict's reviewId does not match this staging")
        if not isinstance(ch, str) or not hmac.compare_digest(ch.encode("utf-8"), lock["challenge"].encode("utf-8")):
            raise rp.ReviewPackError(f"the verdict's challenge does not match {rp.REVIEW_ID_FILE} of this staging")
    findings = v.get("findings")
    if not isinstance(findings, list):
        raise rp.ReviewPackError("verdict findings must be a list")
    if v["verdict"] == "changes_requested" and not findings:
        raise rp.ReviewPackError("changes_requested needs at least one finding")
    files = {f["path"]: f for f in manifest["files"]}
    for i, f in enumerate(findings):
        what = f"finding #{i + 1}"
        if not isinstance(f, dict):
            raise rp.ReviewPackError(f"{what} is not an object")
        path, side, line = f.get("path"), f.get("side"), f.get("line")
        if not isinstance(path, str) or path not in files:
            raise rp.ReviewPackError(f"{what}: path {path!r} is not a file of the package")
        if not isinstance(side, str) or side not in SIDES:
            raise rp.ReviewPackError(f"{what}: side {side!r} is not head or base")
        if not isinstance(f.get("severity"), str) or f.get("severity") not in SEVERITIES:
            raise rp.ReviewPackError(f"{what}: severity {f.get('severity')!r} is not one of {sorted(SEVERITIES)}")
        if not isinstance(f.get("title"), str) or not f["title"].strip():
            raise rp.ReviewPackError(f"{what}: title is missing")
        n = _line_count(pkg, side, path, files[path].get("oldPath"))
        if n is None:
            raise rp.ReviewPackError(f"{what}: {path} has no {side} side in the package")
        if not isinstance(line, int) or isinstance(line, bool) or not 1 <= line <= n:
            raise rp.ReviewPackError(f"{what}: line {line!r} is outside {path} ({side}, {n} lines)")
    return v


# ---------- comment and decision ----------

def receipt(run_id, head):
    return f"relay-receipt: {run_id} {head}"


def render_comment(v, run_id):
    head = v["headSha"]
    rid = f", review `{v['reviewId']}`" if isinstance(v.get("reviewId"), str) else ""
    lines = [f"**Code review relayed: {v['verdict']}** (reviewer run `{run_id}`, head `{head[:12]}`{rid})", ""]
    if v["findings"]:
        lines.append("Findings:")
        for i, f in enumerate(v["findings"], 1):
            lines.append(f"{i}. [{f['severity']}] `{f['path']}:{f['line']}` ({f['side']}): {f['title']}")
            if isinstance(f.get("detail"), str) and f["detail"].strip():
                lines.append(f"   {f['detail'].strip()}")
            if isinstance(f.get("fix"), str) and f["fix"].strip():
                lines.append(f"   Fix: {f['fix'].strip()}")
    else:
        lines.append("No findings.")
    nr = v.get("notReviewable") or v.get("notReviewed") or []
    if isinstance(nr, list) and nr:
        lines += ["", "Not reviewable: " + ", ".join(f"`{x.get('path')}` ({x.get('reason')})" for x in nr
                                                     if isinstance(x, dict))]
    lines += ["", receipt(run_id, head)]
    return "\n".join(lines)


def decision_body(v, run_id):
    if v["verdict"] == "approved":
        return {"status": "done", "comment": f"Approved by the Verdict Relay (review run {run_id})."}
    return {"status": "in_progress",
            "comment": f"Changes requested by the Verdict Relay (review run {run_id}); see the findings comment."}


def _receipts(comments):
    return {m.groups() for c in comments or [] for m in RECEIPT_RE.finditer(str(c.get("body") or ""))}


def _post_comment(api, issue_id, body, run_id, head, sleep):
    """POST the findings comment. After a transient failure the comments are read again before any retry:
    the server may have stored the comment although the reply was lost, and it must not appear twice."""
    for attempt in range(ATTEMPTS):
        try:
            return api("POST", f"/issues/{issue_id}/comments", {"body": body})
        except Exception as e:
            code = _http_status(e)
            if code is not None and code < 500:
                raise
            last = e
        if attempt + 1 < ATTEMPTS:
            sleep(2 ** attempt)
        if (run_id, head) in _receipts(_with_retry(lambda: api("GET", f"/issues/{issue_id}/comments"), sleep)):
            return None
    raise Transient(f"gave up after {ATTEMPTS} attempts: {last}")


def _review_run(api, run_id, issue, lock, reviewer_agent_id, sleep):
    """Check 2 (Option B): the run belongs to this staging's review sub-issue.

    Establishes, from Paperclip's records:
    - the lock names a review sub-issue and the run (`review-start` wrote both), and --run-id is that run;
    - the sub-issue is a child of the reviewed issue, in the same company, assigned to code-reviewer;
    - the run is in the sub-issue's runs, and the run record's `issueId` is the sub-issue (issue-scoped).
    The caller then checks agent, `succeeded` and `createdAt >= stagedAt`, and check 5 the reviewId and challenge.

    Does NOT establish that the reviewer read or understood the package: only that Paperclip ran it for this
    sub-issue and that its verdict carries the staging's challenge. Any read failure other than a transient one
    is a refusal (fail closed)."""
    sub_id = lock.get("reviewIssueId")
    if not lock.get("reviewId") or not sub_id:
        raise rp.ReviewPackError(f"this staging has no review sub-issue; start the review with "
                                 f"pc.py review-start {lock['issue']} (Option B)")
    if lock.get("runId") != run_id:
        raise rp.ReviewPackError(f"the staging lock names run {lock.get('runId')}, not {run_id}")

    def get(path):
        try:
            return _with_retry(lambda: api("GET", path), sleep)
        except Transient:
            raise
        except Exception:
            return None
    sub = get(f"/issues/{sub_id}")
    if not isinstance(sub, dict) or sub.get("id") != sub_id:
        raise rp.ReviewPackError(f"review sub-issue {sub_id} was not found")
    if sub.get("parentId") != issue["id"]:
        raise rp.ReviewPackError(f"review sub-issue {sub.get('identifier') or sub_id} is not a child of {lock['issue']}")
    if issue.get("companyId") is None or sub.get("companyId") != issue.get("companyId"):
        raise rp.ReviewPackError("the review sub-issue belongs to another company")
    if sub.get("assigneeAgentId") != reviewer_agent_id:
        raise rp.ReviewPackError(f"review sub-issue {sub.get('identifier') or sub_id} is not assigned to "
                                 f"{rp.REVIEWER_AGENT}")
    runs = get(f"/issues/{sub_id}/runs") or []
    run = next((r for r in runs if isinstance(r, dict) and r.get("runId") == run_id), None)
    if run is None:
        raise rp.ReviewPackError(f"run {run_id} is not a run of the review sub-issue")
    detail = get(f"/heartbeat-runs/{run_id}")
    if not isinstance(detail, dict) or detail.get("id") != run_id or detail.get("issueId") != sub_id:
        raise rp.ReviewPackError(f"run {run_id} is not scoped to the review sub-issue")
    return run


# ---------- the relay ----------

def relay(rr, sr, key, run_id, api, head_now, identity, reviewer_agent_id, now, sleep=time.sleep):
    """Returns a one-line result. Raises ReviewPackError on any failed check (nothing recorded) or refusal."""
    lock = rp.read_lock(sr)
    if lock is None:
        raise rp.ReviewPackError("nothing is staged; the relay needs the staged package of the review")
    # Check 3: staging lock and staged copy
    if lock["issue"] != key:
        raise rp.ReviewPackError(f"staging holds {lock['issue']}, not {key}")
    pkg = os.path.join(sr, "current")
    manifest, _ = rp.verify_package(pkg, True, lock["manifestSha256"], rp.staged_extra(lock))
    rp.verify_package(lock["packagePath"], True, lock["manifestSha256"])
    if manifest["headSha"] != lock["headSha"]:
        raise rp.ReviewPackError("the staged manifest head differs from the staging lock")
    if not lock.get("reviewId") or not lock.get("reviewIssueId"):
        raise rp.ReviewPackError(f"this staging has no review sub-issue; start the review with "
                                 f"pc.py review-start {key} (Option B)")

    issue = _with_retry(lambda: api("GET", f"/issues/{key}"), sleep)
    receipts = _receipts(_with_retry(lambda: api("GET", f"/issues/{issue['id']}/comments"), sleep))
    mine = (run_id, lock["headSha"]) in receipts
    logged = {(e.get("runId"), e.get("headSha")) for e in rp.read_audit(rr)
              if e["event"] == "relay" and e.get("issue") == key}
    others = sorted(r for r, h in receipts | logged if r and h == lock["headSha"] and r != run_id)
    if others:
        raise rp.ReviewPackError(f"a verdict for head {lock['headSha'][:12]} was already relayed (run {others[0]}); "
                                 "the Board decides which review stands")
    if (mine or (run_id, lock["headSha"]) in logged) and issue.get("status") != "in_review":
        return f"{key}: already relayed (run {run_id}); nothing to do"

    # Check 1: in_review, and the relay identity is the active participant
    part = (issue.get("executionState") or {}).get("currentParticipant") or {}
    if issue.get("status") != "in_review":
        raise rp.ReviewPackError(f"{key} is {issue.get('status')}, not in_review")
    if part.get("type") != "user" or part.get("userId") != identity:
        raise rp.ReviewPackError(f"{key}'s active participant is {part.get('type')}:{part.get('userId') or part.get('agentId')}, "
                                 f"not the relay identity user:{identity}; the Board decides by hand")
    # Check 2: the run is the review sub-issue's run named in the lock (Option B)
    run = _review_run(api, run_id, issue, lock, reviewer_agent_id, sleep)
    if run.get("agentId") != reviewer_agent_id:
        raise rp.ReviewPackError(f"run {run_id} is not a {rp.REVIEWER_AGENT} run")
    if run.get("status") != RUN_OK:
        raise rp.ReviewPackError(f"run {run_id} is {run.get('status')}, not {RUN_OK}")
    created = rp.parse_iso(run.get("createdAt") or "", f"run {run_id} createdAt")
    if created < rp.parse_iso(lock["stagedAt"], "staging.lock stagedAt"):
        raise rp.ReviewPackError(f"run {run_id} started before the package was staged; it reviewed something else")
    # Check 4: PR head unchanged
    current = head_now()
    if current != lock["headSha"]:
        raise rp.ReviewPackError(f"the PR head moved to {str(current)[:12]}; the review is stale")
    # Check 5: exactly one valid verdict
    log = fetch_verified_log(api, run_id, sleep)  # the lock's run (check 2), whole log, size and SHA-256 verified
    check_tool_surface(log)
    v = validate_verdict(parse_verdict(final_message(log)), lock, manifest, pkg)

    # §3.5: comment first (skipped if its receipt exists), then the decision
    try:
        if not mine:
            _post_comment(api, issue["id"], render_comment(v, run_id), run_id, lock["headSha"], sleep)
        _with_retry(lambda: api("PATCH", f"/issues/{issue['id']}", decision_body(v, run_id)), sleep)
    except Transient as e:
        rp.audit(rr, "relay-refused", now, issue=key, head=lock["headSha"], run_id=run_id, reason=f"transient: {e}")
        raise RelayRefused(f"{e}; re-run review-relay later (the receipt makes it safe), or the Board decides by "
                           f"hand: pc.py approve {key} or pc.py request-changes {key}")
    except Exception as e:
        rp.audit(rr, "relay-refused", now, issue=key, head=lock["headSha"], run_id=run_id, reason=str(e)[:300])
        raise RelayRefused(f"Paperclip refused the relay ({str(e)[:200]}). The findings comment stays; "
                                 f"the Board decides by hand: pc.py approve {key} or pc.py request-changes {key}")
    try:
        rp.audit(rr, "relay", now, issue=key, head=lock["headSha"], run_id=run_id, reason=v["verdict"],
                 reviewId=lock["reviewId"], reviewIssueId=lock["reviewIssueId"])
        audit_note = ""
    except OSError as e:  # the decision is recorded in Paperclip; only the local audit line is missing
        audit_note = (f"; WARNING: the decision is recorded in Paperclip but the audit log could not be written "
                      f"({e}); review-pack --unstage will need --abandon")
    note = _close_review_issue(api, lock["reviewIssueId"], sleep) + audit_note
    return f"{key}: relayed {v['verdict']} from run {run_id} ({len(v['findings'])} findings){note}"


def _close_review_issue(api, sub_id, sleep):
    """After a recorded decision the review sub-issue has served its purpose. Closing it is best effort: the
    decision stands either way, and a failure is reported for the Board to close it by hand."""
    try:
        _with_retry(lambda: api("PATCH", f"/issues/{sub_id}", {"status": "done"}), sleep)
        return "; review sub-issue closed"
    except Exception as e:
        return f"; the review sub-issue could not be closed ({str(e)[:120]}), close it by hand"


# ---------- review-start (Option B) ----------

START_STATES = (None, "creating", "create-refused", "sub-issue-created", "waking", "wake-refused", "started")
OP_LOCK = rp.OP_LOCK_FILE


_op_lock = rp.op_lock  # shared with review_pack.unstage (R2)


def reviewer_run_state(api, lock, resolve_reviewer, sleep=time.sleep):
    """R2: may any run of the code-reviewer agent still use staging? Read-only Paperclip calls.

    Returns {"state": "active" | "clear" | "unverified", "reason", "runs", "agentId", "companyId"}:
    - company: the lock's companyId (recorded by review-start) or the reviewed issue's; they must agree;
    - reviewer: resolve_reviewer(companyId) (the company's code-reviewer by name); it must agree with the lock's
      reviewerAgentId when recorded;
    - every run of that agent in the company (GET /companies/<id>/heartbeat-runs?agentId=, no limit: all rows):
      queued / scheduled_retry / running -> active, **whenever it was created** (a run that started before this
      staging still has the agent's fixed --add-dir and can read it); among runs created at or after stagedAt,
      interrupted or an unknown status -> unverified; succeeded / failed / cancelled / timed_out -> fine;
    - the lock's runId, when set, read by id: same id, agent, company and review sub-issue, else unverified.
    Any read failure raises; review_pack turns that into "unverified"."""
    issue = _with_retry(lambda: api("GET", f"/issues/{lock['issue']}"), sleep)
    cid = (issue or {}).get("companyId")
    if not cid:
        return {"state": "unverified", "reason": f"{lock['issue']} has no company in Paperclip"}
    if lock.get("companyId") and lock["companyId"] != cid:
        return {"state": "unverified", "reason": "the staging lock names another company than the issue's"}
    aid = resolve_reviewer(cid)
    if not aid:
        return {"state": "unverified", "reason": f"no {rp.REVIEWER_AGENT} agent found", "companyId": cid}
    if lock.get("reviewerAgentId") and lock["reviewerAgentId"] != aid:
        return {"state": "unverified", "reason": f"the {rp.REVIEWER_AGENT} agent differs from the one recorded in "
                                                 "the staging lock", "companyId": cid, "agentId": aid}
    rows = _with_retry(lambda: api("GET", f"/companies/{cid}/heartbeat-runs?agentId={aid}"), sleep)
    if not isinstance(rows, list):
        return {"state": "unverified", "reason": "the run list is not a list", "companyId": cid, "agentId": aid}
    since = rp.parse_iso(lock["stagedAt"], "staging.lock stagedAt")
    runs, active = [], []
    for r in rows:
        if not isinstance(r, dict) or not all(isinstance(r.get(k), str) for k in ("id", "status", "createdAt")):
            return {"state": "unverified", "reason": "a run in the list is malformed", "companyId": cid, "agentId": aid}
        if r.get("agentId") not in (None, aid):
            return {"state": "unverified", "reason": "the run list contains another agent's run",
                    "companyId": cid, "agentId": aid}
        if r["status"] in rp.REVIEWER_ACTIVE:  # active at any age: it can still read staging
            active.append({"id": r["id"], "status": r["status"]})
        if rp.parse_iso(r["createdAt"], f"run {r['id']} createdAt") < since:
            continue
        runs.append({"id": r["id"], "status": r["status"]})
    base = {"companyId": cid, "agentId": aid}
    if active:
        return dict(base, state="active", reason="a reviewer run is active", runs=active)
    odd = [r for r in runs if r["status"] not in rp.REVIEWER_TERMINAL]
    if odd:
        return dict(base, state="unverified", runs=odd,
                    reason=f"reviewer run {odd[0]['id']} is {odd[0]['status']} (may still be recovered)")
    if lock.get("runId"):
        d = _with_retry(lambda: api("GET", f"/heartbeat-runs/{lock['runId']}"), sleep)
        if not isinstance(d, dict) or d.get("id") != lock["runId"]:
            return dict(base, state="unverified", runs=runs, reason=f"run {lock['runId']} was not returned")
        if d.get("agentId") != aid or d.get("companyId") != cid or d.get("issueId") != lock.get("reviewIssueId"):
            return dict(base, state="unverified", runs=runs,
                        reason=f"run {lock['runId']} is not the reviewer's run of the review sub-issue")
        if d.get("status") in rp.REVIEWER_ACTIVE:
            return dict(base, state="active", reason="the recorded run is active",
                        runs=[{"id": d["id"], "status": d["status"]}])
        if d.get("status") not in rp.REVIEWER_TERMINAL:
            return dict(base, state="unverified", runs=runs,
                        reason=f"the recorded run is {d.get('status')}")
    return dict(base, state="clear", reason="no active reviewer run; none interrupted since staging", runs=runs)


def _is_refusal(err):
    """A 4xx answer means Paperclip refused the request, so it had no effect. Anything else (network error,
    timeout, 5xx) leaves it unknown whether the request took effect."""
    code = _http_status(err)
    return code is not None and 400 <= code < 500


def _flag_value(args, flag):
    """The single value after `flag` in an argument list; refuses a missing, repeated or valueless flag."""
    idx = [i for i, a in enumerate(args) if a == flag]
    if len(idx) != 1 or idx[0] + 1 >= len(args):
        raise rp.ReviewPackError(f"the reviewer's extraArgs must contain {flag} exactly once, with a value")
    return args[idx[0] + 1]


def check_reviewer_config(agent, sr):
    """Fail closed unless the code-reviewer agent has the strict, write-free profile (P0 layers 1 and 2):
    built-in tools Read, Grep, Glob only; every MCP tool removed (--disallowedTools mcp__* and a settings deny
    rule); dontAsk with an allow list of exactly Read, Grep, Glob; --restricted to one --add-dir, the staging
    folder; no environment variables (no credential); no flag that adds tools, MCP servers or bypasses checks."""
    if not isinstance(agent, dict) or agent.get("adapterType") != "claude_local":
        raise rp.ReviewPackError(f"{rp.REVIEWER_AGENT} is not a claude_local agent")
    ac = agent.get("adapterConfig") or {}
    if ac.get("env"):
        raise rp.ReviewPackError(f"{rp.REVIEWER_AGENT} has environment variables configured; it must have none")
    if ac.get("dangerouslySkipPermissions"):
        raise rp.ReviewPackError(f"{rp.REVIEWER_AGENT} skips permission checks")
    args = ac.get("extraArgs")
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise rp.ReviewPackError(f"{rp.REVIEWER_AGENT} has no extraArgs list")
    bad = sorted(FORBIDDEN_FLAGS & set(args))
    if bad:
        raise rp.ReviewPackError(f"the reviewer's extraArgs contain forbidden flags {bad}")
    if "--restricted" not in args:
        raise rp.ReviewPackError("the reviewer's extraArgs lack --restricted")
    if set(_flag_value(args, "--tools").split(",")) != REVIEWER_TOOLS:
        raise rp.ReviewPackError("the reviewer's --tools must be exactly Read,Grep,Glob")
    if "mcp__*" not in [x.strip() for x in _flag_value(args, "--disallowedTools").replace(" ", ",").split(",")]:
        raise rp.ReviewPackError("the reviewer's extraArgs must remove every MCP tool: --disallowedTools mcp__*")
    if _flag_value(args, "--permission-mode") != "dontAsk":
        raise rp.ReviewPackError("the reviewer's --permission-mode must be dontAsk")
    add_dir = _flag_value(args, "--add-dir")
    norm = lambda p: os.path.normcase(os.path.abspath(p))  # noqa: E731
    if norm(add_dir) != norm(os.path.join(sr, "current")):
        raise rp.ReviewPackError("the reviewer's --add-dir must be the staging folder <Staging Root>/current")
    settings_path = _flag_value(args, "--settings")
    try:
        with open(settings_path, encoding="utf-8") as f:
            perms = (json.load(f) or {}).get("permissions") or {}
    except (OSError, ValueError, AttributeError) as e:
        raise rp.ReviewPackError(f"the reviewer's settings file cannot be read ({e})")
    if sorted(perms.get("allow") or []) != sorted(REVIEWER_TOOLS):
        raise rp.ReviewPackError("the reviewer settings must allow exactly Read, Grep and Glob")
    missing = sorted(REQUIRED_DENY - set(perms.get("deny") or []))
    if missing:
        raise rp.ReviewPackError(f"the reviewer settings must deny {missing}")
    if perms.get("defaultMode") != "dontAsk" or perms.get("ask") or perms.get("additionalDirectories"):
        raise rp.ReviewPackError("the reviewer settings must use defaultMode dontAsk with no ask rules or "
                                 "additional directories")


def _get_sub(api, sub_id, sleep):
    """GET a review sub-issue; a refusal (for example 404) reads as missing, a transient error propagates."""
    try:
        return _with_retry(lambda: api("GET", f"/issues/{sub_id}"), sleep)
    except Transient:
        raise
    except Exception:
        return None


def _wake_reason(lock):
    return f"review {lock['reviewId']} {lock['issue']} {lock['headSha'][:12]}"


def _sub_title(lock):
    return f"Review {lock['issue']} @ {lock['headSha'][:12]} (review {lock['reviewId'][:8]})"


def _check_sub(sub, sub_id, issue, reviewer_agent_id):
    if not isinstance(sub, dict) or sub.get("id") != sub_id:
        raise rp.ReviewPackError(f"review sub-issue {sub_id} was not found in Paperclip; it is not recreated "
                                 "automatically. Unstage with --abandon and stage again for a new review")
    label = sub.get("identifier") or sub_id
    if sub.get("parentId") != issue["id"]:
        raise rp.ReviewPackError(f"review sub-issue {label} is not a child of {issue.get('identifier')}")
    if issue.get("companyId") is None or sub.get("companyId") != issue.get("companyId"):
        raise rp.ReviewPackError(f"review sub-issue {label} belongs to another company")
    if sub.get("assigneeAgentId") != reviewer_agent_id:
        raise rp.ReviewPackError(f"review sub-issue {label} is not assigned to {rp.REVIEWER_AGENT}")


def _matching_runs(api, lock, sub_id, reviewer_agent_id, identity, sleep):
    """Runs of the sub-issue that this review-start's wake created: same agent, scoped to the sub-issue (run
    record), started by the Board identity with this review's exact wake reason, not older than the staging.
    Returns (matches, other_runs)."""
    try:
        runs = _with_retry(lambda: api("GET", f"/issues/{sub_id}/runs"), sleep) or []
    except Transient:
        raise
    except Exception as e:
        raise rp.ReviewPackError(f"the runs of review sub-issue {sub_id} could not be read ({str(e)[:160]}); "
                                 "nothing was woken") from None
    since = rp.parse_iso(lock["stagedAt"], "staging.lock stagedAt")
    matches, others = [], []
    for r in runs:
        rid = r.get("runId") if isinstance(r, dict) else None
        if not rid:
            continue
        try:
            d = _with_retry(lambda: api("GET", f"/heartbeat-runs/{rid}"), sleep)
        except Transient:
            raise
        except Exception:
            d = None  # unreadable run record: counted as another run, so nothing is woken
        ctx = (d or {}).get("contextSnapshot") or {}
        ok = (isinstance(d, dict) and d.get("id") == rid and d.get("issueId") == sub_id
              and d.get("agentId") == reviewer_agent_id and ctx.get("wakeReason") == _wake_reason(lock)
              and ctx.get("triggeredBy") == "board" and ctx.get("actorId") == identity
              and rp.parse_iso(d.get("createdAt") or "", f"run {rid} createdAt") >= since)
        (matches if ok else others).append(rid)
    return matches, others


def review_start(rr, sr, key, api, company_id, reviewer_agent_id, identity, now, sleep=time.sleep):
    """Create the review sub-issue for the staged review and wake code-reviewer for it, or recover a start that
    was interrupted. Returns a summary. Fails closed whenever it cannot tell what an earlier attempt did.

    Lock field `reviewStart` records progress, so an interrupted run never repeats a step that may have
    taken effect:
      None / create-refused   -> create the sub-issue (state "creating" is written first)
      creating                -> the create may have happened: look for the sub-issue among the issue's
                                 children (by review id); exactly one -> adopt it; otherwise stop
      sub-issue-created / wake-refused -> no wake took effect: wake (state "waking" is written first)
      waking                  -> the wake may have happened: look for this review's run on the sub-issue;
                                 exactly one -> record it; none or several -> stop, no new wake
      started (runId set)     -> verify sub-issue and run; never wake again
    POSTs that create or wake are sent once, without automatic retry. Paperclip's wakeup idempotencyKey is not
    used: in 2026.1023.0 it deduplicates only execution-recovery wakes (server services/heartbeat/queue.js).
    The sub-issue is created in backlog (no assignment wake) without a project (no worktree); the wake reason
    does not make Paperclip require an issue comment (queue.js shouldRequireIssueCommentForWake). Whether
    Paperclip runs an on-demand wake for a backlog issue as issue-scoped, in the agent's cwd, is to be verified
    in a sandbox."""
    op = _op_lock(sr, "review-start", now)
    try:
        return _review_start(rr, sr, key, api, company_id, reviewer_agent_id, identity, now, sleep)
    finally:
        os.remove(op)


def _review_start(rr, sr, key, api, company_id, reviewer_agent_id, identity, now, sleep):
    lock = rp.read_lock(sr)
    if lock is None:
        raise rp.ReviewPackError("nothing is staged; run review-pack first")
    if lock["issue"] != key:
        raise rp.ReviewPackError(f"staging holds {lock['issue']}, not {key}")
    if not lock.get("reviewId"):
        raise rp.ReviewPackError("this staging predates Option B (no reviewId); unstage and stage it again")
    if lock.get("unstaging"):
        raise rp.ReviewPackError(f"an unstage of {key} was interrupted (unstaging since {lock['unstaging']}); finish "
                                 "it with review-pack --unstage before starting a review")
    state = lock.get("reviewStart")
    if state not in START_STATES:
        raise rp.ReviewPackError(f"staging.lock has an unknown reviewStart state {state!r}; inspect it")
    rp.verify_package(os.path.join(sr, "current"), True, lock["manifestSha256"], rp.staged_extra(lock))
    issue = _with_retry(lambda: api("GET", f"/issues/{key}"), sleep)
    head12, rid8 = lock["headSha"][:12], lock["reviewId"][:8]

    # Started: verify, never wake again
    if lock.get("runId"):
        if not lock.get("reviewIssueId"):
            raise rp.ReviewPackError("staging.lock names a run but no review sub-issue; inspect it")
        sub = _get_sub(api, lock["reviewIssueId"], sleep)
        _check_sub(sub, lock["reviewIssueId"], issue, reviewer_agent_id)
        matches, _ = _matching_runs(api, lock, lock["reviewIssueId"], reviewer_agent_id, identity, sleep)
        if lock["runId"] not in matches:
            raise rp.ReviewPackError(f"the recorded run {lock['runId']} is not this review's run on "
                                     f"{sub.get('identifier')}; inspect it before relaying")
        return (f"{key}: review already started (sub-issue {sub.get('identifier')}, run {lock['runId']}); "
                f"nothing woken. When it has succeeded: pc.py review-relay {key} --run-id {lock['runId']}")

    part = (issue.get("executionState") or {}).get("currentParticipant") or {}
    if issue.get("status") != "in_review" or part.get("type") != "user" or part.get("userId") != identity:
        raise rp.ReviewPackError(f"{key} is not waiting on user:{identity} in review "
                                 f"(status {issue.get('status')}); the relay could not record the decision")
    try:
        agent = _with_retry(lambda: api("GET", f"/agents/{reviewer_agent_id}"), sleep)
    except Transient:
        raise
    except Exception as e:
        raise rp.ReviewPackError(f"the {rp.REVIEWER_AGENT} configuration could not be read ({str(e)[:160]})") from None
    check_reviewer_config(agent, sr)

    # Step 1: the sub-issue
    if not lock.get("reviewIssueId"):
        if state == "creating":
            found = _with_retry(lambda: api("GET", f"/companies/{company_id}/issues?parentId={issue['id']}"
                                                   f"&limit=200"), sleep) or []
            mine = [c for c in found if isinstance(c, dict) and f"(review {lock['reviewId']})" in
                    str(c.get("description") or "") and c.get("parentId") == issue["id"]]
            if len(mine) != 1:
                raise rp.ReviewPackError(
                    f"an earlier review-start may have created the review sub-issue and was interrupted; "
                    f"{len(mine)} child issue(s) of {key} carry review {lock['reviewId']}. Nothing was created now. "
                    f"Look for \"{_sub_title(lock)}\" among {key}'s sub-issues: if exactly one exists it will be "
                    "adopted on the next review-start once Paperclip lists it; if none exists after a few "
                    "minutes, or several do, cancel them (pc.py cancel) and unstage with --abandon, then stage again")
            sub = mine[0]
            _check_sub(sub, sub["id"], issue, reviewer_agent_id)
        else:
            rp.update_lock(sr, reviewStart="creating")
            desc = (f"Review sub-issue for {key} at head {lock['headSha']} (review {lock['reviewId']}).\n\n"
                    "You are code-reviewer. Read REVIEW.md and REVIEW-ID.txt in the staged package folder given "
                    "to you with --add-dir, review the package as REVIEW.md says, and end your final message with "
                    "exactly one fenced json verdict block. Do not try to change anything.")
            try:
                sub = api("POST", f"/companies/{company_id}/issues", {
                    "title": _sub_title(lock), "description": desc, "assigneeAgentId": reviewer_agent_id,
                    "status": "backlog", "parentId": issue["id"]})
            except Exception as e:
                if _is_refusal(e):
                    rp.update_lock(sr, reviewStart="create-refused")
                    raise rp.ReviewPackError(f"Paperclip refused to create the review sub-issue ({str(e)[:200]}); "
                                             "nothing was created, review-start can be run again") from None
                raise rp.ReviewPackError(
                    f"creating the review sub-issue gave no answer ({str(e)[:200]}); it may exist. Run "
                    "review-start again: it looks for it and does not create a second one") from None
            _check_sub(sub, (sub or {}).get("id"), issue, reviewer_agent_id)
        lock = rp.update_lock(sr, reviewIssueId=sub["id"], reviewIssueKey=sub.get("identifier"),
                              reviewStart="sub-issue-created", companyId=company_id, reviewerAgentId=reviewer_agent_id)
        rp.audit(rr, "review-start", now, issue=key, head=lock["headSha"], reason=f"sub-issue {sub.get('identifier')}",
                 reviewId=lock["reviewId"], reviewIssueId=sub["id"])
    sub_id = lock["reviewIssueId"]
    sub = _get_sub(api, sub_id, sleep)
    _check_sub(sub, sub_id, issue, reviewer_agent_id)
    label = sub.get("identifier") or sub_id

    # Step 2: the run. Any existing run of the sub-issue blocks a new wake.
    matches, others = _matching_runs(api, lock, sub_id, reviewer_agent_id, identity, sleep)
    if len(matches) == 1:
        rp.update_lock(sr, runId=matches[0], reviewStart="started")
        return (f"{key}: recovered the reviewer run {matches[0]} of sub-issue {label}; nothing new woken. "
                f"When it has succeeded: pc.py review-relay {key} --run-id {matches[0]}")
    if matches or others:
        raise rp.ReviewPackError(
            f"sub-issue {label} has {len(matches)} run(s) of this review and {len(others)} other run(s); the run "
            "cannot be chosen safely and nothing was woken. Inspect them in Paperclip; to start over, cancel the "
            "sub-issue (pc.py cancel) and unstage with --abandon, then stage again")
    if lock.get("reviewStart") == "waking":
        raise rp.ReviewPackError(
            f"an earlier wake for sub-issue {label} ({sub_id}) may have reached Paperclip, but no run of it is "
            "listed yet. Nothing was woken now. Run review-start again in a few minutes: it records the run once "
            f"Paperclip lists it. If none appears, cancel {label} (pc.py cancel) and unstage with --abandon, then "
            "stage again; do not wake the reviewer by hand")
    rp.update_lock(sr, reviewStart="waking")
    try:
        run = api("POST", f"/agents/{reviewer_agent_id}/wakeup?companyId={company_id}", {
            "source": "on_demand", "triggerDetail": "manual", "reason": _wake_reason(lock),
            "payload": {"issueId": sub_id}})
    except Exception as e:
        if _is_refusal(e):
            rp.update_lock(sr, reviewStart="wake-refused")
            raise rp.ReviewPackError(f"Paperclip refused the reviewer wake ({str(e)[:200]}); no run was started. "
                                     f"Fix the cause, then run review-start again (sub-issue {label} is kept)") from None
        raise rp.ReviewPackError(
            f"the reviewer wake for sub-issue {label} gave no answer ({str(e)[:200]}); a run may exist. Run "
            "review-start again: it looks for the run and does not wake twice") from None
    run_id = (run or {}).get("id")
    if not run_id:
        rp.update_lock(sr, reviewStart="wake-refused")
        raise rp.ReviewPackError(f"Paperclip did not start a run for the reviewer wake (status "
                                 f"{(run or {}).get('status')}; for example the agent is paused). Sub-issue {label} "
                                 "is kept; fix the cause, then run review-start again")
    rp.update_lock(sr, runId=run_id, reviewStart="started")
    return (f"{key}: review sub-issue {label} created, reviewer run {run_id} {(run or {}).get('status')}. "
            f"When it has succeeded: pc.py review-relay {key} --run-id {run_id}")


def add_start_parser(sub, fn):
    s = sub.add_parser("review-start", help="OQ-042 Option B: create the review sub-issue for the staged review "
                                            "and wake code-reviewer for it")
    s.add_argument("key", help="issue key of the staged review, e.g. SOU-12")
    s.add_argument("--identity", default=rp.BOARD, help="the Paperclip user who must be the review participant")
    s.add_argument("--review-root", default=os.environ.get("COMPANY_OS_REVIEW_ROOT"))
    s.add_argument("--staging-root", default=os.environ.get("COMPANY_OS_STAGING_ROOT"))
    s.set_defaults(fn=fn)
    return s


def cmd_review_start(a, api, company_id, reviewer_agent_id, now=None, sleep=time.sleep):
    now = now or rp.utcnow()
    try:
        rr, sr = rp.resolve_roots(a.review_root, a.staging_root)
    except OSError as e:
        raise rp.ReviewPackError(f"cannot prepare the roots: {e}")
    key = a.key if rp.KEY_RE.match(a.key or "") else None
    try:
        if key is None:
            raise rp.ReviewPackError(f"{a.key!r} is not an issue key")
        print(review_start(rr, sr, key, api, company_id(), reviewer_agent_id(), a.identity, now, sleep))
        return 0
    except Exception as e:  # review_start fails closed; every failure becomes an audited refusal
        reason = _refusal_reason(e)
        try:
            rp.audit(rr, "refuse", now, issue=key, reason=f"review-start: {reason}")
        except OSError:
            pass
        raise rp.ReviewPackError(reason) from None


# ---------- CLI (wired into pc.py as `review-relay`) ----------

def add_parser(sub, fn):
    s = sub.add_parser("review-relay", help="OQ-042 Phase 4a: check a finished code-reviewer run against the "
                                            "staged package and relay its verdict (Board fallback on refusal)")
    s.add_argument("key", help="issue key of the staged review, e.g. SOU-12")
    s.add_argument("--run-id", required=True, help="the code-reviewer run whose final message holds the verdict")
    s.add_argument("--identity", default=rp.BOARD, help="the Paperclip user the relay acts as (default: the "
                                                         "Board Operator, design §3.3)")
    s.add_argument("--review-root", default=os.environ.get("COMPANY_OS_REVIEW_ROOT"))
    s.add_argument("--staging-root", default=os.environ.get("COMPANY_OS_STAGING_ROOT"))
    s.set_defaults(fn=fn)
    return s


def github_head(manifest, token=None, transport=None):
    """Check 4 source: a function returning the PR's current head over the GitHub API (packager token).
    A fixture package has no live PR to compare with, so it cannot be relayed."""
    import review_github as gh
    if manifest.get("source") != "github-api":
        raise rp.ReviewPackError("the staged package was built from a fixture; its PR head cannot be checked, "
                                 "so it cannot be relayed (the Board decides by hand)")
    repo, number = manifest["repository"], (manifest.get("pullRequest") or {}).get("number")

    def head_now():
        tok = None
        try:
            tok = token if token is not None else gh.read_token()
            client = gh.GitHubClient(tok, **({"transport": transport} if transport else {}))
            return gh._pr(client, repo, number)["head"]["sha"]
        except gh.GitHubSourceError as e:
            raise rp.ReviewPackError(gh.redact(e, tok)) from None
    return head_now


def _refusal_reason(e):
    """A one-line reason for an audited refusal. Before A3, a Paperclip failure in the check phase (network or 5xx
    after the retries, or a 4xx such as an unknown issue) escaped as a raw exception with no audit line."""
    if isinstance(e, rp.ReviewPackError):
        return str(e)
    if isinstance(e, OSError):
        return f"filesystem error: {e}"
    if isinstance(e, Transient):
        return f"Paperclip did not answer ({str(e)[:200]})"
    return f"Paperclip refused or failed ({type(e).__name__}: {str(e)[:200]})"


def cmd_review_relay(a, api, reviewer_agent_id, head_now=None, now=None, sleep=time.sleep):
    """CLI entry. A failed check is audited as `refuse` (nothing recorded in Paperclip); a refused or failed
    recording is audited by relay() as `relay-refused`."""
    now = now or rp.utcnow()
    try:
        rr, sr = rp.resolve_roots(a.review_root, a.staging_root)
    except OSError as e:
        raise rp.ReviewPackError(f"cannot prepare the roots: {e}")
    key = a.key if rp.KEY_RE.match(a.key or "") else None
    try:
        if key is None:
            raise rp.ReviewPackError(f"{a.key!r} is not an issue key")
        if head_now is None:
            lock = rp.read_lock(sr)
            if lock is None:
                raise rp.ReviewPackError("nothing is staged; the relay needs the staged package of the review")
            manifest, _ = rp.verify_package(os.path.join(sr, "current"), True, lock["manifestSha256"],
                                            rp.staged_extra(lock))
            head_now = github_head(manifest)
        print(relay(rr, sr, key, a.run_id, api, head_now, a.identity, reviewer_agent_id(), now, sleep))
        return 0
    except RelayRefused:
        raise
    except Exception as e:  # every other failure happened before anything was recorded: an audited refusal
        reason = _refusal_reason(e)
        try:
            rp.audit(rr, "refuse", now, issue=key, run_id=a.run_id, reason=f"relay: {reason}")
        except OSError:
            pass
        raise rp.ReviewPackError(f"{reason}. Nothing was recorded; the Board decides by hand "
                                 f"(pc.py approve / request-changes)") from None
