"""OQ-042 Review Package Phase 4a: the Verdict Relay (docs/design/review-package.md §3).

Reads a finished code-reviewer run, checks it against the staged package and the live state (§3.4, fail closed),
then posts the findings as a comment with a relay receipt and records the decision (§3.5). Every Paperclip and
GitHub call goes through injected functions, so the whole flow is tested offline; no call is made at import.

Authority (§3.3): the relay acts as the identity that the CLI uses for Paperclip. It records a decision only
while that identity is the issue's active stage participant. Otherwise Paperclip refuses, and the Board decides
by hand (fallback). Whether this works on a real instance is Phase 4b (V1-V3), not tested here.
"""
import json
import os
import re
import time

import review_pack as rp

VERDICTS = {"approved", "changes_requested"}
SEVERITIES = {"critical", "high", "medium", "low"}
SIDES = {"head", "base"}
RUN_OK = "succeeded"
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

def final_message(log):
    """The reviewer's final message from GET /heartbeat-runs/<id>/log: the `result` of the stream-json output."""
    text = "".join(_chunks(log))
    result = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict) and ev.get("type") == "result" and isinstance(ev.get("result"), str):
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
    lines = [f"**Code review relayed: {v['verdict']}** (reviewer run `{run_id}`, head `{head[:12]}`)", ""]
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


def _company_run(api, run_id, issue, key, sleep):
    """Check 2 for a run that is not in the issue's runs: the reviewer woken without an issue (Phase 4b, V2).

    Establishes, from GET /heartbeat-runs/<id> (Board API):
    - the run exists and is the run named by --run-id (`id`);
    - it belongs to the issue's company (`companyId`), so a run of another company cannot be relayed;
    - it is not scoped to another issue (`issueId` empty or this issue's id).
    The caller then requires, as for an issue-scoped run: `agentId` is code-reviewer, `status` is succeeded,
    `createdAt` is at or after the staging lock's `stagedAt`, and the lock's `runId`, if set, matches.
    Checks 3 and 5 add: the staged package is the locked one, and the verdict names the locked issue and head
    and cites only files and lines of the staged manifest.

    Does NOT establish:
    - that the run was started for this review. Paperclip links a company-scoped run to no issue; the wake
      reason naming the issue is free text, not checked here. Any succeeded code-reviewer run of the company
      started after staging passes this check;
    - that the run read the staged package. A verdict with the right issue, head and valid lines passes
      check 5 whether it came from reading `current/` or from anything else the reviewer saw or guessed.
    The binding to the review therefore rests on the Board starting exactly one reviewer run per staging
    (design §7, serialization) and on the relay receipt refusing a second run for the same head.
    Any read failure other than a transient one is a refusal (fail closed)."""
    try:
        r = _with_retry(lambda: api("GET", f"/heartbeat-runs/{run_id}"), sleep)
    except Transient:
        raise
    except Exception:
        r = None
    if not isinstance(r, dict) or r.get("id") != run_id:
        raise rp.ReviewPackError(f"run {run_id} is not a run of {key}")
    if issue.get("companyId") is None or r.get("companyId") != issue.get("companyId"):
        raise rp.ReviewPackError(f"run {run_id} belongs to another company than {key}")
    if r.get("issueId") not in (None, issue["id"]):
        raise rp.ReviewPackError(f"run {run_id} was scoped to another issue")
    return {"runId": r["id"], "agentId": r.get("agentId"), "status": r.get("status"), "createdAt": r.get("createdAt")}


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
    manifest, _ = rp.verify_package(pkg, True, lock["manifestSha256"])
    rp.verify_package(lock["packagePath"], True, lock["manifestSha256"])
    if manifest["headSha"] != lock["headSha"]:
        raise rp.ReviewPackError("the staged manifest head differs from the staging lock")

    if lock.get("runId") not in (None, run_id):
        raise rp.ReviewPackError(f"the staging lock names run {lock['runId']}, not {run_id}")

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
    # Check 2: the run
    runs = _with_retry(lambda: api("GET", f"/issues/{issue['id']}/runs"), sleep) or []
    run = next((r for r in runs if r.get("runId") == run_id), None)
    if run is None:
        # Phase 4b (V2): Paperclip 2026.1023.0 cancels an issue-scoped run of an agent that is neither the
        # assignee nor the agent participant of the current stage, so the reviewer is woken without an issue.
        # Such a run is accepted only if it belongs to the issue's company and is not scoped to another issue;
        # the staging lock and the verdict's issue and headSha bind it to this review.
        run = _company_run(api, run_id, issue, key, sleep)
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
    log = _with_retry(lambda: api("GET", f"/heartbeat-runs/{run_id}/log"), sleep) or {}
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
    rp.audit(rr, "relay", now, issue=key, head=lock["headSha"], run_id=run_id, reason=v["verdict"])
    return f"{key}: relayed {v['verdict']} from run {run_id} ({len(v['findings'])} findings)"


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
            manifest, _ = rp.verify_package(os.path.join(sr, "current"), True, lock["manifestSha256"])
            head_now = github_head(manifest)
        print(relay(rr, sr, key, a.run_id, api, head_now, a.identity, reviewer_agent_id(), now, sleep))
        return 0
    except RelayRefused:
        raise
    except (rp.ReviewPackError, OSError) as e:
        reason = str(e) if isinstance(e, rp.ReviewPackError) else f"filesystem error: {e}"
        try:
            rp.audit(rr, "refuse", now, issue=key, run_id=a.run_id, reason=f"relay: {reason}")
        except OSError:
            pass
        raise rp.ReviewPackError(f"{reason}. Nothing was recorded; the Board decides by hand "
                                 f"(pc.py approve / request-changes)") from None
