"""Tests for the Verdict Relay (review_relay.py, OQ-042 Phase 4a) with an in-memory fake Paperclip and a fake
PR head. No network, no Paperclip, no token. Run: python -I -W error test_review_relay.py
(also collected by test_pc.py)"""
import argparse
import contextlib
import hashlib
import datetime
import io
import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import review_pack as rp  # noqa: E402
import review_relay as rl  # noqa: E402
from test_review_pack import Env, NOW, REPO, SHA_HEAD, fadd, fmod, source  # noqa: E402

UTC = datetime.timezone.utc
KEY, ISSUE_ID, RUN, REVIEWER, OTHER_AGENT = "SOU-12", "uuid-12", "run-1", "agent-cr", "agent-web"
SUB_ID, SUB_KEY, COMPANY = "uuid-13", "SOU-13", "co-1"
REVIEW_ID, CHALLENGE = "11111111-2222-4333-8444-555555555555", "c0ffee" * 5 + "ab"
WAKE_REASON = f"review {REVIEW_ID} {KEY} {SHA_HEAD[:12]}"
BOARD_CTX = {"wakeReason": WAKE_REASON, "triggeredBy": "board", "actorId": "local-board"}
LATER = NOW + datetime.timedelta(minutes=5)
TOKEN = "github_pat_TESTTOKEN0123456789abcdefABCDEF_xyz"


class HttpError(Exception):
    """Shaped like pc.ApiError: 'METHOD path -> code: body'."""


def http(method, path, code, body="error"):
    return HttpError(f"{method} {path} -> {code}: {body}")


def verdict(verdict="approved", findings=None, issue=KEY, head=SHA_HEAD, **over):
    v = {"schema": rp.VERDICT_SCHEMA, "verdict": verdict, "issue": issue, "headSha": head,
         "reviewId": REVIEW_ID, "challenge": CHALLENGE,
         "findings": findings if findings is not None else [], "notReviewable": []}
    v.update(over)
    return v


def finding(path="src/Calculator.cs", line=2, side="head", severity="high", **over):
    f = {"path": path, "line": line, "side": side, "severity": severity, "title": "Operands swapped",
         "detail": "b-a instead of a-b", "fix": "return a-b"}
    f.update(over)
    return f


def message(v, prefix="Reviewed the package.\n\n", suffix=""):
    body = v if isinstance(v, str) else json.dumps(v)
    return f"{prefix}```json\n{body}\n```{suffix}"


STRICT_TOOLS = ["Glob", "Grep", "Read"]
PAPERCLIP_WRITE_TOOLS = ["mcp__Paperclip_projects__create_task", "mcp__Paperclip_projects__create_project",
                         "mcp__Paperclip_projects__set_task_title"]


def run_log(final, extra_events=(), tools=None, denials=None, init=True):
    """GET /heartbeat-runs/<id>/log: JSONL records whose chunks carry Claude Code's stream-json output."""
    events = ([{"type": "system", "subtype": "init", "tools": list(STRICT_TOOLS if tools is None else tools)}]
              if init else []) + list(extra_events)
    if final is not None:
        events.append({"type": "result", "subtype": "success", "result": final,
                       "permission_denials": list(denials or [])})
    stream = "".join(json.dumps(e) + "\n" for e in events)
    half = len(stream) // 2  # a record boundary inside a JSON line, as real chunking does
    recs = [{"ts": "t", "stream": "stdout", "chunk": stream[:half]}, {"ts": "t", "stream": "stdout", "chunk": stream[half:]}]
    return {"content": "".join(json.dumps(r) + "\n" for r in recs)}


class FakePaperclip:
    def __init__(self, final, status="in_review", participant=None, runs=None):
        self.issue = {"id": ISSUE_ID, "companyId": COMPANY, "identifier": KEY, "status": status,
                      "executionState": {"currentStageType": "review",
                                         "currentParticipant": participant or {"type": "user", "userId": rp.BOARD}}}
        self.comments = []
        self.runs = runs if runs is not None else [
            {"runId": RUN, "agentId": REVIEWER, "status": "succeeded", "createdAt": rp.iso(LATER)}]
        self.logs = {RUN: run_log(final)}
        self.details = {}  # run id -> GET /heartbeat-runs/<id> body overriding the default
        self.sub = {"id": SUB_ID, "identifier": SUB_KEY, "parentId": ISSUE_ID, "companyId": COMPANY,
                    "assigneeAgentId": REVIEWER, "status": "in_progress"}
        self.created = []  # bodies of POST /companies/<id>/issues
        self.wake = {"id": RUN, "status": "queued"}
        self.wakes = []  # bodies of POST /agents/<id>/wakeup
        self.ctx = {}  # run id -> contextSnapshot; default BOARD_CTX
        self.create_error = None  # (exception, created_anyway) for POST /companies/<id>/issues
        self.wake_error = None  # (exception, run_created_anyway) for POST /agents/<id>/wakeup
        self.agent = None  # GET /agents/<reviewer>: set by RelayEnv.pc()
        self.page_size = 1024 * 1024  # bytes per log page served
        self.log_meta = {}  # run id -> overrides of logSha256 / logBytes / logStore / logCompressed
        self.next_offset_override = None  # force a nextOffset value on every page
        self.calls = []
        self.fail = {}  # (method, path) -> list of exceptions raised by successive calls
        self.store_despite_error = False  # a POST that fails after the server stored the comment

    def writes(self):
        """Writes to the reviewed issue (and anything else), except closing the review sub-issue."""
        return [(m, p) for m, p, _ in self.calls if m in ("POST", "PATCH") and p != f"/issues/{SUB_ID}"]

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        queue = self.fail.get((method, path))
        if queue:
            err = queue.pop(0)
            if method == "POST" and self.store_despite_error:
                self.comments.insert(0, {"body": body["body"]})
            raise err
        if (method, path) == ("GET", f"/issues/{KEY}"):
            return json.loads(json.dumps(self.issue))
        if (method, path) == ("GET", f"/issues/{ISSUE_ID}/comments"):
            return list(self.comments)
        if (method, path) == ("GET", f"/issues/{ISSUE_ID}/runs"):
            return []  # the reviewer runs on its review sub-issue (Option B)
        if (method, path) == ("GET", f"/issues/{SUB_ID}") and self.sub is not None:
            return dict(self.sub)
        if (method, path) == ("GET", f"/issues/{SUB_ID}/runs") and self.sub is not None:
            return list(self.runs)
        if (method, path) == ("PATCH", f"/issues/{SUB_ID}") and self.sub is not None:
            self.sub["status"] = body["status"]
            return dict(self.sub)
        if method == "GET" and path.startswith("/heartbeat-runs/") and "/log" in path:
            rid = path.split("/")[2]
            if rid not in self.logs:
                raise http(method, path, 404, "Run log not found")
            q = dict(p.split("=") for p in path.split("?", 1)[1].split("&")) if "?" in path else {}
            off, lim = int(q.get("offset", 0)), min(int(q.get("limitBytes", 256000)), self.page_size)
            data = self.logs[rid]["content"].encode("utf-8")
            page = {"runId": rid, "store": "local_file", "content": data[off:off + lim].decode("utf-8", "replace")}
            if self.next_offset_override is not None:
                page["nextOffset"] = self.next_offset_override
            elif off + lim < len(data):
                page["nextOffset"] = off + lim
            return page
        if method == "GET" and path.startswith("/heartbeat-runs/"):
            rid = path.split("/")[2]
            if rid in self.details:
                return dict(self.details[rid])
            r = next((r for r in self.runs if r["runId"] == rid), None)
            if r:
                d = {"id": rid, "companyId": COMPANY, "issueId": r.get("issueId", SUB_ID), "scopeKind": "issue",
                     "agentId": r["agentId"], "status": r["status"], "createdAt": r["createdAt"],
                     "contextSnapshot": dict(self.ctx.get(rid, BOARD_CTX))}
                if rid in self.logs:
                    data = self.logs[rid]["content"].encode("utf-8")
                    d.update(logStore="local_file", logCompressed=False, logBytes=len(data),
                             logSha256=hashlib.sha256(data).hexdigest())
                d.update(self.log_meta.get(rid, {}))
                return d
        if (method, path) == ("GET", f"/agents/{REVIEWER}") and self.agent is not None:
            return json.loads(json.dumps(self.agent))
        if (method, path) == ("GET", f"/companies/{COMPANY}/issues?parentId={ISSUE_ID}&limit=200"):
            return [dict(self.sub)] if self.sub else []
        if (method, path) == ("POST", f"/companies/{COMPANY}/issues"):
            err, created = self.create_error or (None, False)
            self.create_error = None
            if err is None or created:
                self.created.append(body)
                self.sub = dict(body, id=SUB_ID, identifier=SUB_KEY, companyId=COMPANY)
            if err is not None:
                raise err
            return dict(self.sub)
        if (method, path) == ("POST", f"/agents/{REVIEWER}/wakeup?companyId={COMPANY}"):
            self.wakes.append(body)
            err, started = self.wake_error or (None, False)
            self.wake_error = None
            if (err is None and self.wake) or started:
                rid = (self.wake or {}).get("id", RUN)
                self.runs.append({"runId": rid, "agentId": REVIEWER, "status": "queued", "createdAt": rp.iso(LATER)})
                self.ctx[rid] = {"wakeReason": body["reason"], "triggeredBy": "board", "actorId": "local-board"}
            if err is not None:
                raise err
            return dict(self.wake) if self.wake else {"status": "skipped"}
        if (method, path) == ("POST", f"/issues/{ISSUE_ID}/comments"):
            self.comments.insert(0, {"body": body["body"]})
            return {"id": f"c{len(self.comments)}"}
        if (method, path) == ("PATCH", f"/issues/{ISSUE_ID}"):
            self.issue["status"] = body["status"]
            self.comments.insert(0, {"body": body["comment"]})
            return dict(self.issue)
        raise http(method, path, 404, "not found")


def src_two_files():
    return source(files=[
        fmod("src/Calculator.cs", "class C {\n int Sub(int a,int b)=>a-b;\n}\n", "class C {\n int Sub(int a,int b)=>b-a;\n}\n"),
        fadd("src/New.cs", "// one line\n")])


class RelayEnv(Env):
    def setUp(self):
        super().setUp()
        pkg, _ = rp.build(self.rr, self.sr, src_two_files(), KEY, {"issues": {KEY: {"status": "in_review",
                          "project": "proj-1", "closedAt": None}}, "runs": []}, [REPO], NOW)
        rp.stage(self.rr, self.sr, KEY, SHA_HEAD, pkg, NOW)
        self.pin_review(started=True)
        self.head = SHA_HEAD
        self.sleeps = []
        self.settings_path = os.path.join(self.base, "reviewer-settings.json")
        self.write_settings()

    def write_settings(self, **over):
        perms = {"allow": ["Read", "Grep", "Glob"], "defaultMode": "dontAsk",
                 "deny": ["Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch", "mcp__*"]}
        perms.update(over)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump({"permissions": perms}, f)

    def reviewer_agent(self, extra=None, drop=(), **ac_over):
        """The strict reviewer profile that check_reviewer_config requires."""
        args = ["--no-session-persistence", "--restricted", "--tools", "Read,Grep,Glob", "--disallowedTools", "mcp__*",
                "--strict-mcp-config", "--permission-mode", "dontAsk", "--permission-prompts", "none",
                "--settings", self.settings_path, "--add-dir", os.path.join(self.sr, "current"),
                "--append-system-prompt", "You are code-reviewer. Use --tools carefully."]
        for flag in drop:
            i = args.index(flag)
            del args[i:i + (1 if flag == "--restricted" else 2)]
        args += list(extra or [])
        ac = {"cwd": self.base, "engine": "cli", "model": "sonnet", "dangerouslySkipPermissions": False, "extraArgs": args}
        ac.update(ac_over)
        return {"id": REVIEWER, "adapterType": "claude_local", "adapterConfig": ac}

    def pin_review(self, started):
        """Fix the staging's reviewId and challenge (the real ones are random), rewrite REVIEW-ID.txt to match,
        and, when started, record the review sub-issue and run as review-start would."""
        lock = rp.update_lock(self.sr, reviewId=REVIEW_ID, challenge=CHALLENGE,
                              reviewIssueId=SUB_ID if started else None,
                              reviewIssueKey=SUB_KEY if started else None, runId=RUN if started else None)
        data = rp.review_id_text(lock)
        with open(os.path.join(self.sr, "current", rp.REVIEW_ID_FILE), "wb") as f:
            f.write(data)
        rp.update_lock(self.sr, challengeSha256=rp.sha256_bytes(data))

    def pc(self, v=None, **kw):
        final = message(v if v is not None else verdict()) if not isinstance(v, str) else v
        api = FakePaperclip(final, **kw)
        api.agent = self.reviewer_agent()
        return api

    def relay(self, api, run_id=RUN, identity=rp.BOARD):
        return rl.relay(self.rr, self.sr, KEY, run_id, api, lambda: self.head, identity, REVIEWER, LATER,
                        self.sleeps.append)

    def refused_nothing_written(self, fragment, api, **kw):
        with self.assertRaises(rp.ReviewPackError) as cm:
            self.relay(api, **kw)
        self.assertIn(fragment, str(cm.exception))
        self.assertEqual(api.writes(), [])
        self.assertNotIn("relay", self.events())
        return cm.exception


# ---------- happy paths and §3.5 order ----------

class Relays(RelayEnv):
    def test_approved_comment_then_done(self):
        api = self.pc(verdict("approved"))
        out = self.relay(api)
        self.assertIn("relayed approved", out)
        self.assertEqual(api.writes(), [("POST", f"/issues/{ISSUE_ID}/comments"), ("PATCH", f"/issues/{ISSUE_ID}")])
        self.assertEqual(api.issue["status"], "done")
        self.assertIn(rl.receipt(RUN, SHA_HEAD), api.comments[1]["body"])
        e = rp.read_audit(self.rr)[-1]
        self.assertEqual((e["event"], e["issue"], e["headSha"], e["runId"], e["reason"]),
                         ("relay", KEY, SHA_HEAD, RUN, "approved"))
        self.assertTrue(rp.relayed(self.rr, rp.read_lock(self.sr)))  # so review-pack --unstage works

    def test_changes_requested_goes_back_to_in_progress_with_findings(self):
        api = self.pc(verdict("changes_requested", [finding(), finding("src/New.cs", 1, severity="low")]))
        self.relay(api)
        self.assertEqual(api.issue["status"], "in_progress")
        body = api.comments[1]["body"]
        self.assertIn("[high] `src/Calculator.cs:2` (head): Operands swapped", body)
        self.assertIn("Fix: return a-b", body)
        self.assertIn("`src/New.cs:1`", body)
        patch = [b for m, _, b in api.calls if m == "PATCH"][0]
        self.assertTrue(patch["comment"].strip())

    def test_base_side_finding_accepted(self):
        self.relay(self.pc(verdict("changes_requested", [finding(line=3, side="base")])))

    def test_not_reviewable_listed(self):
        api = self.pc(verdict(notReviewable=[{"path": "a.png", "reason": "binary"}]))
        self.relay(api)
        self.assertIn("`a.png` (binary)", api.comments[1]["body"])

    def test_last_result_event_wins_and_text_before_block_is_fine(self):
        api = self.pc(verdict())
        api.logs[RUN] = run_log(message(verdict()), [{"type": "assistant", "message": {"content": "thinking"}}])
        self.relay(api)


# ---------- §3.4 checks: each one refuses with nothing recorded ----------

class Check1IssueAndParticipant(RelayEnv):
    def test_not_in_review(self):
        self.refused_nothing_written("not in_review", self.pc(status="in_progress"))

    def test_agent_participant(self):
        self.refused_nothing_written("not the relay identity", self.pc(participant={"type": "agent", "agentId": REVIEWER}))

    def test_other_user_participant(self):
        self.refused_nothing_written("not the relay identity", self.pc(participant={"type": "user", "userId": "someone"}))

    def test_identity_is_configurable(self):
        api = self.pc(participant={"type": "user", "userId": "relay-user"})
        self.refused_nothing_written("not the relay identity", api)
        self.relay(api, identity="relay-user")


class Check2Run(RelayEnv):
    def run_with(self, **over):
        r = {"runId": RUN, "agentId": REVIEWER, "status": "succeeded", "createdAt": rp.iso(LATER)}
        r.update(over)
        return self.pc(runs=[r])

    def test_run_not_on_issue(self):
        self.refused_nothing_written("is not a run of", self.pc(runs=[]))

    def test_wrong_agent(self):
        self.refused_nothing_written("is not a code-reviewer run", self.run_with(agentId=OTHER_AGENT))

    def test_unfinished_or_failed(self):
        for status in ("running", "failed", "timed_out", "cancelled", "queued"):
            self.refused_nothing_written("not succeeded", self.run_with(status=status))

    def test_started_before_staging(self):
        self.refused_nothing_written("before the package was staged",
                                     self.run_with(createdAt=rp.iso(NOW - datetime.timedelta(seconds=1))))

    def test_lock_names_another_run(self):
        lock = rp.read_lock(self.sr)
        lock["runId"] = "run-other"
        with open(rp.lock_path(self.sr), "w", encoding="utf-8") as f:
            json.dump(lock, f)
        self.refused_nothing_written("names run run-other", self.pc())


class Check2ReviewSubIssue(RelayEnv):
    """Option B: only the run of this staging's review sub-issue, named in the lock, is accepted."""

    def test_happy_path_closes_the_sub_issue(self):
        api = self.pc()
        out = self.relay(api)
        self.assertIn("relayed approved", out)
        self.assertIn("review sub-issue closed", out)
        self.assertEqual(api.sub["status"], "done")
        e = rp.read_audit(self.rr)[-1]
        self.assertEqual((e["event"], e["reviewId"], e["reviewIssueId"]), ("relay", REVIEW_ID, SUB_ID))
        self.assertIn(REVIEW_ID, api.comments[1]["body"])

    def test_sub_issue_close_failure_does_not_undo_the_decision(self):
        api = self.pc()
        api.fail[("PATCH", f"/issues/{SUB_ID}")] = [http("PATCH", "p", 422, "no")]
        out = self.relay(api)
        self.assertIn("close it by hand", out)
        self.assertEqual(api.issue["status"], "done")

    def test_staging_without_review_start_refused(self):
        self.pin_review(started=False)
        self.refused_nothing_written("start the review with pc.py review-start", self.pc())

    def test_pre_option_b_lock_refused(self):
        lock = rp.read_lock(self.sr)
        for k in ("reviewId", "challenge", "challengeSha256", "reviewIssueId", "reviewIssueKey"):
            lock.pop(k, None)
        with open(rp.lock_path(self.sr), "w", encoding="utf-8") as f:
            json.dump(lock, f)
        os.remove(os.path.join(self.sr, "current", rp.REVIEW_ID_FILE))
        self.refused_nothing_written("start the review with pc.py review-start", self.pc())

    def test_run_not_named_in_lock_refused(self):
        rp.update_lock(self.sr, runId="run-other")
        self.refused_nothing_written("names run run-other", self.pc())

    def test_sub_issue_missing_refused(self):
        api = self.pc()
        api.sub = None
        self.refused_nothing_written("was not found", api)

    def test_sub_issue_of_another_parent_refused(self):
        api = self.pc()
        api.sub["parentId"] = "uuid-99"
        self.refused_nothing_written("is not a child of", api)

    def test_sub_issue_of_another_company_refused(self):
        api = self.pc()
        api.sub["companyId"] = "co-2"
        self.refused_nothing_written("another company", api)

    def test_sub_issue_not_assigned_to_reviewer_refused(self):
        api = self.pc()
        api.sub["assigneeAgentId"] = OTHER_AGENT
        self.refused_nothing_written("not assigned to code-reviewer", api)

    def test_run_not_on_sub_issue_refused(self):
        self.refused_nothing_written("not a run of the review sub-issue", self.pc(runs=[]))

    def test_run_record_scoped_elsewhere_refused(self):
        for over in ({"issueId": None}, {"issueId": ISSUE_ID}, {"issueId": "uuid-99"}, {"id": "run-x"}):
            with self.subTest(over=over):
                api = self.pc()
                d = {"id": RUN, "companyId": COMPANY, "issueId": SUB_ID, "agentId": REVIEWER, "status": "succeeded",
                     "createdAt": rp.iso(LATER)}
                d.update(over)
                api.details[RUN] = d
                self.refused_nothing_written("not scoped to the review sub-issue", api)

    def test_company_scoped_run_no_longer_accepted(self):
        """The Phase 4b company-scoped path is gone: a run without the sub-issue binding is refused."""
        api = self.pc(runs=[])
        api.details[RUN] = {"id": RUN, "companyId": COMPANY, "issueId": None, "agentId": REVIEWER,
                            "status": "succeeded", "createdAt": rp.iso(LATER)}
        self.refused_nothing_written("not a run of the review sub-issue", api)

    def test_verdict_review_id_and_challenge_must_match(self):
        for over, fragment in (({"reviewId": "other"}, "reviewId does not match"),
                               ({"reviewId": None}, "reviewId does not match"),
                               ({"challenge": "0" * 32}, "challenge does not match"),
                               ({"challenge": None}, "challenge does not match"),
                               ({"challenge": ["x"]}, "challenge does not match")):
            with self.subTest(over=over):
                v = verdict()
                v.update(over)
                self.refused_nothing_written(fragment, self.pc(v))

    def test_verdict_without_the_new_fields_refused(self):
        v = verdict()
        del v["reviewId"], v["challenge"]
        self.refused_nothing_written("reviewId does not match", self.pc(v))

    def test_tampered_review_id_file_refused(self):
        with open(os.path.join(self.sr, "current", rp.REVIEW_ID_FILE), "ab") as f:
            f.write(b"x")
        self.refused_nothing_written("REVIEW-ID.txt fails", self.pc())


class ReviewStart(RelayEnv):
    """review-start lock states and recovery (no Paperclip call is repeated when it may have taken effect)."""

    def setUp(self):
        super().setUp()
        self.pin_review(started=False)

    def api(self, **kw):
        api = self.pc(**kw)
        api.sub, api.runs = None, []
        return api

    def start(self, api, identity=rp.BOARD):
        return rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, identity, NOW, self.sleeps.append)

    def refuse(self, api, fragment):
        with self.assertRaises(rp.ReviewPackError) as cm:
            self.start(api)
        self.assertIn(fragment, str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(self.sr, rp.OP_LOCK_FILE)))  # op lock always released
        return cm.exception

    def lock(self):
        return rp.read_lock(self.sr)

    # 1
    def test_first_start_creates_one_sub_issue_and_one_run(self):
        api = self.api()
        out = self.start(api)
        self.assertIn(f"review sub-issue {SUB_KEY} created, reviewer run {RUN}", out)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))
        body = api.created[0]
        self.assertEqual((body["status"], body["parentId"], body["assigneeAgentId"]), ("backlog", ISSUE_ID, REVIEWER))
        self.assertNotIn("projectId", body)
        self.assertNotIn("executionPolicy", body)
        wake = api.wakes[0]
        self.assertEqual((wake["payload"], wake["source"], wake["triggerDetail"], wake["reason"]),
                         ({"issueId": SUB_ID}, "on_demand", "manual", WAKE_REASON))
        self.assertNotEqual(wake["reason"], "issue_assigned")  # no missing-comment re-wake for a tool-less reviewer
        lock = self.lock()
        self.assertEqual((lock["reviewIssueId"], lock["reviewIssueKey"], lock["runId"], lock["reviewStart"]),
                         (SUB_ID, SUB_KEY, RUN, "started"))
        self.assertIn("review-start", self.events())

    def test_challenge_never_leaves_staging(self):
        api = self.api()
        self.start(api)
        self.assertNotIn(CHALLENGE, json.dumps(api.calls))
        self.assertNotIn(CHALLENGE, json.dumps(rp.read_audit(self.rr)))

    def test_start_then_relay(self):
        api = self.api()
        self.start(api)
        api.runs[0]["status"] = "succeeded"
        api.sub["status"] = "in_progress"
        self.assertIn("relayed approved", self.relay(api))

    # 2
    def test_wake_refused_then_retry_wakes_without_second_sub_issue(self):
        api = self.api()
        api.wake_error = (http("POST", "wakeup", 409, "agent paused"), False)
        self.refuse(api, "refused the reviewer wake")
        self.assertEqual((self.lock()["reviewStart"], self.lock()["runId"]), ("wake-refused", None))
        self.start(api)
        self.assertEqual((len(api.created), len(api.wakes), len(api.runs)), (1, 2, 1))
        self.assertEqual(self.lock()["runId"], RUN)

    def test_wake_skipped_without_run_id_then_retry(self):
        api = self.api()
        api.wake = None
        self.refuse(api, "did not start a run")
        self.assertEqual(self.lock()["reviewStart"], "wake-refused")
        api.wake = {"id": RUN, "status": "queued"}
        self.start(api)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 2))

    def test_wake_unknown_outcome_without_run_fails_closed(self):
        api = self.api()
        api.wake_error = (HttpError("Paperclip is not reachable (timed out)"), False)
        self.refuse(api, "gave no answer")
        self.assertEqual(self.lock()["reviewStart"], "waking")
        # 5: no run listed -> stop, no second wake
        e = self.refuse(api, "may have reached Paperclip")
        self.assertIn(SUB_ID, str(e))
        self.assertIn("do not wake the reviewer by hand", str(e))
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))

    def test_wake_5xx_is_treated_as_unknown(self):
        api = self.api()
        api.wake_error = (http("POST", "wakeup", 502, "bad gateway"), False)
        self.refuse(api, "gave no answer")
        self.assertEqual(self.lock()["reviewStart"], "waking")

    # 3
    def test_lost_wake_response_is_recovered_without_waking_again(self):
        api = self.api()
        api.wake_error = (HttpError("Paperclip is not reachable (timed out)"), True)
        self.refuse(api, "gave no answer")
        out = self.start(api)
        self.assertIn(f"recovered the reviewer run {RUN}", out)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))
        self.assertEqual((self.lock()["runId"], self.lock()["reviewStart"]), (RUN, "started"))

    # 11
    def test_lock_write_failure_after_wake_is_recovered(self):
        api = self.api()
        real = rp.update_lock

        def failing(sr, **fields):
            if "runId" in fields:
                raise OSError("disk full")
            return real(sr, **fields)
        rp.update_lock = failing
        try:
            with self.assertRaises(OSError):
                self.start(api)
        finally:
            rp.update_lock = real
        self.assertFalse(os.path.exists(os.path.join(self.sr, rp.OP_LOCK_FILE)))
        self.assertEqual((self.lock()["reviewStart"], self.lock()["runId"]), ("waking", None))
        self.assertIn("recovered the reviewer run", self.start(api))
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))

    # 4
    def test_already_started_verifies_and_never_wakes(self):
        api = self.api()
        self.start(api)
        out = self.start(api)
        self.assertIn("review already started", out)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))

    def test_already_started_with_foreign_recorded_run_fails_closed(self):
        api = self.api()
        self.start(api)
        rp.update_lock(self.sr, runId="run-other")
        self.refuse(api, "is not this review's run")
        self.assertEqual(len(api.wakes), 1)

    # 6
    def test_sub_issue_gone_fails_closed_and_is_not_recreated(self):
        api = self.api()
        api.wake_error = (HttpError("timed out"), False)
        self.refuse(api, "gave no answer")
        api.sub = None
        self.refuse(api, "was not found in Paperclip; it is not recreated")
        self.assertEqual(len(api.created), 1)

    # 7
    def test_sub_issue_wrong_parent_company_or_assignee_fails_closed(self):
        for field, value, fragment in (("parentId", "uuid-99", "is not a child of"),
                                       ("companyId", "co-2", "another company"),
                                       ("assigneeAgentId", OTHER_AGENT, "is not assigned to code-reviewer")):
            with self.subTest(field=field):
                api = self.api()
                api.wake_error = (HttpError("timed out"), False)
                rp.update_lock(self.sr, reviewIssueId=None, reviewIssueKey=None, runId=None, reviewStart=None)
                self.refuse(api, "gave no answer")
                api.sub[field] = value
                self.refuse(api, fragment)
                self.assertEqual(len(api.wakes), 1)

    # 8
    def test_run_of_another_issue_or_review_is_not_adopted(self):
        for over, ctx in (({"issueId": "uuid-99"}, None),
                          ({}, dict(BOARD_CTX, wakeReason="review other-review SOU-12 x")),
                          ({}, dict(BOARD_CTX, triggeredBy="agent")),
                          ({}, dict(BOARD_CTX, actorId="someone")),
                          ({"agentId": OTHER_AGENT}, None)):
            with self.subTest(over=over, ctx=ctx):
                api = self.api()
                api.wake_error = (HttpError("timed out"), False)
                rp.update_lock(self.sr, reviewIssueId=None, reviewIssueKey=None, runId=None, reviewStart=None)
                self.refuse(api, "gave no answer")
                api.runs.append(dict({"runId": "run-x", "agentId": REVIEWER, "status": "running",
                                      "createdAt": rp.iso(LATER)}, **over))
                if ctx:
                    api.ctx["run-x"] = ctx
                self.refuse(api, "cannot be chosen safely")
                self.assertIsNone(self.lock()["runId"])
                self.assertEqual(len(api.wakes), 1)

    def test_run_created_before_staging_is_not_adopted(self):
        api = self.api()
        api.wake_error = (HttpError("timed out"), False)
        self.refuse(api, "gave no answer")
        api.runs.append({"runId": "run-old", "agentId": REVIEWER, "status": "succeeded",
                         "createdAt": rp.iso(NOW - datetime.timedelta(minutes=1))})
        self.refuse(api, "cannot be chosen safely")

    # 9
    def test_several_matching_runs_fail_closed(self):
        api = self.api()
        api.wake_error = (HttpError("timed out"), True)
        self.refuse(api, "gave no answer")
        api.runs.append({"runId": "run-2", "agentId": REVIEWER, "status": "queued", "createdAt": rp.iso(LATER)})
        api.ctx["run-2"] = dict(BOARD_CTX)
        self.refuse(api, "2 run(s) of this review")
        self.assertIsNone(self.lock()["runId"])

    def test_existing_unrelated_run_blocks_a_first_wake(self):
        """Even before any wake was sent, a run already on the sub-issue stops review-start instead of adding one."""
        api = self.api()
        api.wake_error = (http("POST", "wakeup", 422, "no"), False)
        self.refuse(api, "refused the reviewer wake")
        api.runs.append({"runId": "run-x", "agentId": REVIEWER, "status": "running", "createdAt": rp.iso(LATER)})
        api.ctx["run-x"] = dict(BOARD_CTX, wakeReason="something else")
        self.refuse(api, "cannot be chosen safely")
        self.assertEqual(len(api.wakes), 1)

    # sub-issue creation outcomes
    def test_create_refused_allows_retry(self):
        api = self.api()
        api.create_error = (http("POST", "issues", 422, "bad"), False)
        self.refuse(api, "refused to create the review sub-issue")
        self.assertEqual(self.lock()["reviewStart"], "create-refused")
        self.start(api)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))

    def test_lost_create_response_adopts_the_sub_issue(self):
        api = self.api()
        api.create_error = (HttpError("timed out"), True)
        self.refuse(api, "creating the review sub-issue gave no answer")
        self.assertEqual(self.lock()["reviewStart"], "creating")
        self.start(api)
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))
        self.assertEqual(self.lock()["reviewIssueId"], SUB_ID)

    def test_unknown_create_without_sub_issue_fails_closed(self):
        api = self.api()
        api.create_error = (HttpError("timed out"), False)
        self.refuse(api, "gave no answer")
        e = self.refuse(api, "0 child issue(s)")
        self.assertIn(REVIEW_ID, str(e))
        self.assertEqual(api.created, [])

    # 10
    def test_concurrent_start_is_refused_while_one_runs(self):
        import threading
        api = self.api()
        entered, release, results = threading.Event(), threading.Event(), []
        inner = api.__call__

        def slow(method, path, body=None):
            if method == "POST" and path.endswith("/issues"):
                entered.set()
                release.wait(5)
            return inner(method, path, body)

        def first():
            try:
                results.append(rl.review_start(self.rr, self.sr, KEY, slow, COMPANY, REVIEWER, rp.BOARD, NOW))
            except Exception as e:  # pragma: no cover - surfaced below
                results.append(e)
        t = threading.Thread(target=first)
        t.start()
        self.assertTrue(entered.wait(5))
        try:
            with self.assertRaises(rp.ReviewPackError) as cm:
                rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW)
            self.assertIn("another staging operation is in progress", str(cm.exception))
            with self.assertRaises(rp.ReviewPackError):
                rp.unstage(self.rr, self.sr, {"issues": {}, "runs": []}, True, NOW)
        finally:
            release.set()
            t.join(5)
        self.assertIn("created", results[0])
        self.assertEqual((len(api.created), len(api.wakes)), (1, 1))

    def test_leftover_op_lock_is_not_taken_over(self):
        with open(os.path.join(self.sr, rp.OP_LOCK_FILE), "w") as f:
            f.write("{}")
        api = self.api()
        with self.assertRaises(rp.ReviewPackError) as cm:
            self.start(api)
        self.assertIn("delete that file by hand", str(cm.exception))
        self.assertTrue(os.path.exists(os.path.join(self.sr, rp.OP_LOCK_FILE)))
        self.assertEqual(api.calls, [])

    # refusals before anything is created
    def test_refusals_create_nothing(self):
        for kw in (dict(status="in_progress"), dict(participant={"type": "agent", "agentId": REVIEWER}),
                   dict(participant={"type": "user", "userId": "someone"})):
            with self.subTest(kw=kw):
                api = self.api(**kw)
                self.refuse(api, "not waiting on user:local-board")
                self.assertEqual((api.created, api.wakes), ([], []))
                self.assertIsNone(self.lock()["reviewIssueId"])

    def test_tampered_staging_refused(self):
        with open(os.path.join(self.sr, "current", rp.REVIEW_ID_FILE), "ab") as f:
            f.write(b"x")
        api = self.api()
        self.refuse(api, "REVIEW-ID.txt fails")
        self.assertEqual(api.created, [])

    def test_unknown_state_refused(self):
        rp.update_lock(self.sr, reviewStart="weird")
        self.refuse(self.api(), "unknown reviewStart state")

    def test_other_issue_staged_or_nothing_staged(self):
        api = self.api()
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.review_start(self.rr, self.sr, "SOU-99", api, COMPANY, REVIEWER, rp.BOARD, NOW)
        self.assertIn("staging holds SOU-12", str(cm.exception))
        rp.unstage(self.rr, self.sr, {"issues": {}, "runs": []}, True, NOW)
        self.refuse(api, "nothing is staged")

    def test_cli_refusal_is_audited(self):
        api = self.api(status="todo")
        a = argparse.Namespace(key=KEY, identity=rp.BOARD, review_root=self.rr, staging_root=self.sr)
        with self.assertRaises(rp.ReviewPackError):
            rl.cmd_review_start(a, api, lambda: COMPANY, lambda: REVIEWER, now=NOW, sleep=self.sleeps.append)
        e = rp.read_audit(self.rr)[-1]
        self.assertEqual(e["event"], "refuse")
        self.assertTrue(e["reason"].startswith("review-start: "))

    def test_parser_wired_into_pc(self):
        import pc
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        rl.add_start_parser(sub, pc.cmd_review_start)
        a = p.parse_args(["review-start", KEY])
        self.assertEqual((a.key, a.identity, a.fn), (KEY, rp.BOARD, pc.cmd_review_start))


class ToolSurface(RelayEnv):
    """P0 layer 3: the relay accepts only a run that was offered exactly Read, Grep and Glob and used nothing else."""

    def with_log(self, **kw):
        api = self.pc()
        api.logs[RUN] = run_log(message(verdict()), **kw)
        return api

    def test_strict_run_accepted(self):
        self.assertIn("relayed approved", self.relay(self.with_log()))

    def test_each_paperclip_write_tool_refused(self):
        for tool in PAPERCLIP_WRITE_TOOLS + ["mcp__Paperclip_connections__connection_request"]:
            with self.subTest(tool=tool):
                self.refused_nothing_written("offered tools other than Read, Grep and Glob",
                                             self.with_log(tools=STRICT_TOOLS + [tool]))

    def test_unknown_future_tool_refused(self):
        """An allow list catches tools that do not exist yet, read or write."""
        for tool in ("mcp__Paperclip_newserver__delete_everything", "mcp__other__list", "Bash", "WebFetch", "Task"):
            with self.subTest(tool=tool):
                self.refused_nothing_written("offered tools other than Read, Grep and Glob",
                                             self.with_log(tools=STRICT_TOOLS + [tool]))

    def test_missing_or_partial_tool_list_refused(self):
        for tools in ([], ["Read"], ["Read", "Grep", "Glob", "Read"], None):
            with self.subTest(tools=tools):
                api = self.pc()
                ev = {"type": "system", "subtype": "init"}
                if tools is not None:
                    ev["tools"] = tools
                api.logs[RUN] = run_log(message(verdict()), init=False, extra_events=[ev])
                self.refused_nothing_written("offered tools other than Read, Grep and Glob", api)

    def test_no_init_event_refused(self):
        self.refused_nothing_written("no init event", self.with_log(init=False))

    def test_any_init_event_with_extra_tools_refused(self):
        api = self.pc()
        api.logs[RUN] = run_log(message(verdict()), extra_events=[
            {"type": "system", "subtype": "init", "tools": STRICT_TOOLS + PAPERCLIP_WRITE_TOOLS[:1]}])
        self.refused_nothing_written("offered tools other than Read, Grep and Glob", api)

    def test_use_of_another_tool_refused(self):
        use = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "mcp__Paperclip_projects__create_task", "input": {"title": "x"}}]}}
        self.refused_nothing_written("used tools other than Read, Grep and Glob", self.with_log(extra_events=[use]))

    def test_permission_denial_refused(self):
        self.refused_nothing_written("attempted refused tools", self.with_log(
            denials=[{"tool_name": "mcp__Paperclip_projects__set_task_title", "tool_input": {}}]))


class LogIntegrity(RelayEnv):
    """The relay parses only the whole log Paperclip finalized for the lock's run (size and SHA-256 verified)."""

    def test_verified_log_accepted_across_pages(self):
        api = self.pc()
        api.page_size = 97  # many pages, boundaries inside JSON lines
        self.assertIn("relayed approved", self.relay(api))
        log_reads = [p for m, p, _ in api.calls if p.startswith(f"/heartbeat-runs/{RUN}/log")]
        self.assertGreater(len(log_reads), 3)

    def test_tool_use_on_a_later_page_is_seen(self):
        """Regression: the relay used to read only the first page (256 KB default), so later events were invisible."""
        api = self.pc()
        filler = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "x" * 400}]}}] * 3
        use = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "mcp__Paperclip_projects__create_task", "input": {}}]}}
        api.logs[RUN] = run_log(message(verdict()), extra_events=filler + [use])
        api.page_size = 500
        self.refused_nothing_written("used tools other than Read, Grep and Glob", api)

    def test_log_changed_after_finalize_refused(self):
        api = self.pc()
        good = api.logs[RUN]["content"]
        api.log_meta[RUN] = {"logSha256": hashlib.sha256(good.encode()).hexdigest(), "logBytes": len(good.encode())}
        api.logs[RUN] = {"content": good.replace("Reviewed the package.", "Reviewed the PACKAGE.")}
        self.refused_nothing_written("does not match its recorded SHA-256", api)

    def test_size_mismatch_refused(self):
        api = self.pc()
        data = api.logs[RUN]["content"].encode()
        api.log_meta[RUN] = {"logBytes": len(data) + 1}
        self.refused_nothing_written("the run record says", api)

    def test_missing_or_malformed_hash_refused(self):
        for value in (None, "", "abc", "G" * 64, 123):
            with self.subTest(value=value):
                api = self.pc()
                api.log_meta[RUN] = {"logSha256": value}
                self.refused_nothing_written("no finalized log hash", api)

    def test_missing_size_refused(self):
        for value in (None, "10", -1, True):
            with self.subTest(value=value):
                api = self.pc()
                api.log_meta[RUN] = {"logBytes": value}
                self.refused_nothing_written("no finalized log size", api)

    def test_compressed_remote_or_unstated_log_refused(self):
        """Only an explicit local, uncompressed log is accepted; missing fields fail closed (schema change)."""
        for over in ({"logCompressed": True}, {"logStore": "s3"}, {"logStore": None}, {"logCompressed": None},
                     {"logCompressed": 0}, {"logCompressed": "false"}):
            with self.subTest(over=over):
                api = self.pc()
                api.log_meta[RUN] = over
                self.refused_nothing_written("only plain local logs", api)

    def test_missing_log_refused(self):
        api = self.pc()
        del api.logs[RUN]
        api.log_meta[RUN] = {"logSha256": "0" * 64, "logBytes": 10, "logStore": "local_file", "logCompressed": False}
        self.refused_nothing_written("could not be read", api)
        api.log_meta[RUN] = {"logSha256": "0" * 64, "logBytes": 10}  # no store fields at all: refused earlier
        self.refused_nothing_written("only plain local logs", api)

    def test_pages_that_do_not_advance_refused(self):
        api = self.pc()
        api.next_offset_override = 0
        self.refused_nothing_written("do not advance", api)

    def test_metadata_for_another_run_refused(self):
        api = self.pc()
        api.log_meta[RUN] = {"id": "run-other"}
        self.refused_nothing_written("", api)

    def test_hash_checked_before_parsing(self):
        """A log that would fail parsing is refused on its hash first when it was altered."""
        api = self.pc()
        good = api.logs[RUN]["content"]
        api.log_meta[RUN] = {"logSha256": hashlib.sha256(good.encode()).hexdigest(), "logBytes": len(good.encode())}
        api.logs[RUN] = {"content": good[: len(good) // 2]}
        api.next_offset_override = None
        e = self.refused_nothing_written("", api)
        self.assertIn("bytes, the run record says", str(e))


class ReviewerRunState(RelayEnv):
    """R2: review_relay.reviewer_run_state reads the reviewer agent's runs from Paperclip (read-only)."""

    def api(self, rows=None, detail=None, company=COMPANY):
        calls = []
        since = NOW + datetime.timedelta(minutes=1)

        def api(method, path, body=None):
            calls.append((method, path))
            assert method == "GET", "reviewer_run_state must only read"
            if path == f"/issues/{KEY}":
                return {"id": ISSUE_ID, "companyId": company}
            if path == f"/companies/{company}/heartbeat-runs?agentId={REVIEWER}":
                return rows if rows is not None else [{"id": RUN, "status": "succeeded", "createdAt": rp.iso(since)}]
            if path == f"/heartbeat-runs/{RUN}":
                d = {"id": RUN, "agentId": REVIEWER, "companyId": company, "issueId": SUB_ID, "status": "succeeded"}
                d.update(detail or {})
                return d
            raise http(method, path, 404, "not found")
        api.calls = calls
        return api

    def state(self, api, **lock_over):
        lock = rp.read_lock(self.sr)
        lock.update(lock_over)
        return rl.reviewer_run_state(api, lock, lambda cid: REVIEWER if cid == COMPANY else None, self.sleeps.append)

    def row(self, status, minutes=2, **over):
        return dict({"id": f"r-{status}", "status": status, "createdAt": rp.iso(NOW + datetime.timedelta(minutes=minutes))}, **over)

    def test_clear_when_every_run_since_staging_is_terminal(self):
        rows = [self.row(s) for s in ("succeeded", "failed", "cancelled", "timed_out")]
        res = self.state(self.api(rows))
        self.assertEqual((res["state"], res["agentId"], res["companyId"]), ("clear", REVIEWER, COMPANY))

    def test_active_statuses(self):
        for s in ("queued", "scheduled_retry", "running"):
            with self.subTest(s=s):
                res = self.state(self.api([self.row("succeeded"), self.row(s)]))
                self.assertEqual((res["state"], res["runs"][0]["status"]), ("active", s))

    def test_any_reviewer_run_counts_not_only_the_lock_run(self):
        """A disposition-repair or stray run of the reviewer agent also reads staging."""
        res = self.state(self.api([self.row("running", id="r-repair")]), runId=RUN)
        self.assertEqual((res["state"], res["runs"][0]["id"]), ("active", "r-repair"))

    def test_interrupted_or_unknown_status_is_unverified(self):
        for s in ("interrupted", "starting", "paused", ""):
            with self.subTest(s=s):
                self.assertEqual(self.state(self.api([self.row(s)]))["state"], "unverified")

    def test_active_run_from_before_staging_still_blocks(self):
        """Regression (R2 self-review): a reviewer run that started before this staging and is still active can
        read staging through the agent's fixed --add-dir, so it blocks unstage like any other active run."""
        for s in ("queued", "scheduled_retry", "running"):
            with self.subTest(s=s):
                res = self.state(self.api([self.row(s, minutes=-60)]))
                self.assertEqual((res["state"], res["runs"][0]["status"]), ("active", s))

    def test_finished_or_interrupted_runs_before_staging_ignored(self):
        for s in ("succeeded", "failed", "cancelled", "timed_out", "interrupted", "unknown-status"):
            with self.subTest(s=s):
                self.assertEqual(self.state(self.api([self.row(s, minutes=-5)]))["state"], "clear")

    def test_malformed_or_foreign_rows_unverified(self):
        for rows in ({"runs": []}, [None], [{"id": "x", "status": "running"}], [self.row("succeeded", agentId="other")]):
            with self.subTest(rows=rows):
                self.assertEqual(self.state(self.api(rows))["state"], "unverified")

    def test_company_and_reviewer_must_agree_with_the_lock(self):
        self.assertEqual(self.state(self.api(), companyId="co-other")["state"], "unverified")
        self.assertEqual(self.state(self.api(), reviewerAgentId="agent-other")["state"], "unverified")
        self.assertEqual(self.state(self.api(company="co-2"))["state"], "unverified")  # no reviewer resolved

    def test_recorded_run_must_be_the_sub_issue_run(self):
        for over in ({"id": "other"}, {"agentId": "a"}, {"companyId": "c"}, {"issueId": ISSUE_ID}):
            with self.subTest(over=over):
                self.assertEqual(self.state(self.api(detail=over), runId=RUN)["state"], "unverified")
        self.assertEqual(self.state(self.api(detail={"status": "running"}), runId=RUN)["state"], "active")
        self.assertEqual(self.state(self.api(detail={"status": "interrupted"}), runId=RUN)["state"], "unverified")
        self.assertEqual(self.state(self.api(), runId=RUN)["state"], "clear")

    def test_read_failures_raise_for_review_pack_to_treat_as_unverified(self):
        def down(method, path, body=None):
            raise HttpError("Paperclip is not reachable (timed out)")
        with self.assertRaises(Exception):
            self.state(down)
        lock = rp.read_lock(self.sr)
        self.assertIn("could not be verified", str(self.assert_unstage_refused(down)))
        self.assertEqual(rp.read_lock(self.sr), lock)

    def assert_unstage_refused(self, api):
        with self.assertRaises(rp.ReviewPackError) as cm:
            rp.unstage(self.rr, self.sr, {"issues": {}, "runs": []}, False, NOW,
                       lambda lock: rl.reviewer_run_state(api, lock, lambda cid: REVIEWER, self.sleeps.append))
        return cm.exception

    def test_only_reads(self):
        api = self.api()
        self.state(api, runId=RUN)
        self.assertTrue(all(m == "GET" for m, _ in api.calls))

    def test_review_start_records_company_and_reviewer_and_respects_unstaging(self):
        self.pin_review(started=False)
        api = self.pc()
        api.sub, api.runs = None, []
        rp.update_lock(self.sr, unstaging=rp.iso(NOW))
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW, self.sleeps.append)
        self.assertIn("unstage of SOU-12 was interrupted", str(cm.exception))
        self.assertEqual(api.created, [])
        rp.update_lock(self.sr, unstaging=None)
        rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW, self.sleeps.append)
        lock = rp.read_lock(self.sr)
        self.assertEqual((lock["companyId"], lock["reviewerAgentId"]), (COMPANY, REVIEWER))

    def test_unstage_holding_the_op_lock_blocks_review_start(self):
        import threading
        self.pin_review(started=False)
        entered, release, out = threading.Event(), threading.Event(), []

        def slow_check(lock):
            entered.set()
            release.wait(5)
            return {"state": "clear", "runs": []}
        t = threading.Thread(target=lambda: out.append(
            rp.unstage(self.rr, self.sr, {"issues": {}, "runs": []}, True, NOW, slow_check)))
        t.start()
        self.assertTrue(entered.wait(5))
        try:
            api = self.pc()
            api.sub, api.runs = None, []
            with self.assertRaises(rp.ReviewPackError) as cm:
                rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW, self.sleeps.append)
            self.assertIn("another staging operation is in progress", str(cm.exception))
            self.assertEqual((api.created, api.wakes), ([], []))
        finally:
            release.set()
            t.join(5)
        self.assertIn("abandon", out[0])

    def test_pc_wires_review_pack_through_paperclip(self):
        import pc
        import argparse as ap
        p = ap.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        rp.add_parser(sub).set_defaults(fn=pc.cmd_review_pack)
        a = p.parse_args(["review-pack", "--unstage", "--state-file", "s.json"])
        self.assertIs(a.fn, pc.cmd_review_pack)


class ReviewerConfig(RelayEnv):
    """P0 layers 1 and 2, checked by review-start before anything is created or woken."""

    def setUp(self):
        super().setUp()
        self.pin_review(started=False)

    def start_refused(self, agent, fragment):
        api = self.pc()
        api.sub, api.runs, api.agent = None, [], agent
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW, self.sleeps.append)
        self.assertIn(fragment, str(cm.exception))
        self.assertEqual((api.created, api.wakes), ([], []))
        return cm.exception

    def test_strict_profile_accepted(self):
        api = self.pc()
        api.sub, api.runs = None, []
        self.assertIn("created", rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW))

    def test_mcp_not_removed_refused(self):
        self.start_refused(self.reviewer_agent(drop=["--disallowedTools"]), "--disallowedTools")
        a = self.reviewer_agent(drop=["--disallowedTools"], extra=["--disallowedTools", "mcp__Paperclip_projects"])
        self.start_refused(a, "--disallowedTools mcp__*")

    def test_settings_without_mcp_deny_refused(self):
        self.write_settings(deny=["Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch"])
        self.start_refused(self.reviewer_agent(), "must deny ['mcp__*']")

    def test_settings_allowing_more_refused(self):
        for allow in (["Read", "Grep", "Glob", "mcp__Paperclip_projects__create_task"], ["Read", "Grep", "Glob", "Bash"],
                      ["Read"]):
            with self.subTest(allow=allow):
                self.write_settings(allow=allow)
                self.start_refused(self.reviewer_agent(), "allow exactly Read, Grep and Glob")

    def test_settings_mode_ask_or_extra_dirs_refused(self):
        for over in ({"defaultMode": "default"}, {"ask": ["Bash"]}, {"additionalDirectories": ["C:/"]}):
            with self.subTest(over=over):
                self.write_settings(**over)
                self.start_refused(self.reviewer_agent(), "defaultMode dontAsk")

    def test_unreadable_settings_refused(self):
        os.remove(self.settings_path)
        self.start_refused(self.reviewer_agent(), "settings file cannot be read")

    def test_wrong_tools_mode_restricted_or_add_dir_refused(self):
        cases = ((self.reviewer_agent(drop=["--tools"], extra=["--tools", "Read,Grep,Glob,Bash"]), "--tools must be exactly"),
                 (self.reviewer_agent(drop=["--tools"]), "--tools exactly once"),
                 (self.reviewer_agent(drop=["--permission-mode"], extra=["--permission-mode", "acceptEdits"]), "dontAsk"),
                 (self.reviewer_agent(drop=["--restricted"]), "lack --restricted"),
                 (self.reviewer_agent(drop=["--add-dir"], extra=["--add-dir", self.base]), "--add-dir must be"),
                 (self.reviewer_agent(extra=["--add-dir", self.base]), "--add-dir exactly once"))
        for agent, fragment in cases:
            with self.subTest(fragment=fragment):
                self.start_refused(agent, fragment)

    def test_forbidden_flags_refused(self):
        for flag in ("--allowedTools", "--dangerously-skip-permissions", "--mcp-config", "--permission-prompt-tool"):
            with self.subTest(flag=flag):
                self.start_refused(self.reviewer_agent(extra=[flag, "x"]), "forbidden flags")

    def test_env_or_skip_permissions_or_other_adapter_refused(self):
        self.start_refused(self.reviewer_agent(env={"GH_TOKEN": {"type": "secret_ref"}}), "environment variables")
        self.start_refused(self.reviewer_agent(dangerouslySkipPermissions=True), "skips permission checks")
        a = self.reviewer_agent()
        a["adapterType"] = "cursor"
        self.start_refused(a, "not a claude_local agent")

    def test_unreadable_agent_refused(self):
        api = self.pc()
        api.sub, api.runs, api.agent = None, [], None
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.review_start(self.rr, self.sr, KEY, api, COMPANY, REVIEWER, rp.BOARD, NOW, self.sleeps.append)
        self.assertIn("configuration could not be read", str(cm.exception))
        self.assertEqual(api.created, [])


class Check3Staging(RelayEnv):
    def test_nothing_staged(self):
        rp.unstage(self.rr, self.sr, {"issues": {}, "runs": []}, True, NOW)
        self.refused_nothing_written("nothing is staged", self.pc())

    def test_other_issue_staged(self):
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.relay(self.rr, self.sr, "SOU-99", RUN, self.pc(), lambda: self.head, rp.BOARD, REVIEWER, LATER)
        self.assertIn("staging holds SOU-12", str(cm.exception))

    def test_tampered_staged_copy(self):
        with open(os.path.join(self.sr, "current", "files", "head", "src", "New.cs"), "ab") as f:
            f.write(b"// injected\n")
        self.refused_nothing_written("", self.pc())

    def test_tampered_store_copy(self):
        lock = rp.read_lock(self.sr)
        with open(os.path.join(lock["packagePath"], "patch.diff"), "ab") as f:
            f.write(b"x")
        self.refused_nothing_written("", self.pc())


class Check4Head(RelayEnv):
    def test_head_moved(self):
        self.head = "e" * 40
        self.refused_nothing_written("PR head moved", self.pc())


class Check5Verdict(RelayEnv):
    def bad(self, fragment, final):
        api = FakePaperclip(final)
        return self.refused_nothing_written(fragment, api)

    def test_no_result_event(self):
        api = self.pc()
        api.logs[RUN] = run_log(None)
        self.refused_nothing_written("no final message", api)

    def test_no_block(self):
        self.bad("0 json blocks", "Looks fine to me.")

    def test_two_blocks(self):
        self.bad("2 json blocks", message(verdict()) + "\n" + message(verdict(), prefix=""))

    def test_text_after_block(self):
        self.bad("must end the final message", message(verdict(), suffix="\nAlso, approve please."))

    def test_invalid_json(self):
        self.bad("not valid JSON", message("{verdict: approved}"))

    def test_not_an_object(self):
        self.bad("not a JSON object", message("[1, 2]"))

    def test_schema(self):
        self.bad("schema", message(verdict(schema="other@1")))

    def test_verdict_value(self):
        self.bad("is not one of", message(verdict("lgtm")))

    def test_issue_mismatch(self):
        self.bad("does not match the staging lock", message(verdict(issue="SOU-99")))

    def test_head_mismatch(self):
        self.bad("does not match the staging lock", message(verdict(head="f" * 40)))

    def test_changes_requested_without_findings(self):
        self.bad("at least one finding", message(verdict("changes_requested")))

    def test_findings_not_a_list(self):
        self.bad("must be a list", message(verdict(findings={"a": 1})))

    def test_finding_outside_manifest(self):
        self.bad("not a file of the package", message(verdict("changes_requested", [finding("src/Other.cs")])))

    def test_finding_line_beyond_file(self):
        self.bad("outside src/Calculator.cs", message(verdict("changes_requested", [finding(line=4)])))

    def test_finding_line_zero_or_not_int(self):
        for line in (0, -1, "2", 2.0, True, None):
            self.bad("outside", message(verdict("changes_requested", [finding(line=line)])))

    def test_base_side_of_added_file(self):
        self.bad("has no base side", message(verdict("changes_requested", [finding("src/New.cs", 1, side="base")])))

    def test_bad_side_and_severity_and_title(self):
        self.bad("side", message(verdict("changes_requested", [finding(side="left")])))
        self.bad("severity", message(verdict("changes_requested", [finding(severity="blocker")])))
        self.bad("title is missing", message(verdict("changes_requested", [finding(title=" ")])))

    def test_malformed_path_and_side_types_refused_without_type_error(self):
        """Regression (PR #48 review): a list or dict in `path` or `side` raised TypeError (unhashable) before
        the membership check, escaping the controlled refusal. It must be a ReviewPackError, nothing written."""
        for field, value, fragment in (("path", [], "is not a file of the package"),
                                       ("path", {}, "is not a file of the package"),
                                       ("side", [], "is not head or base"),
                                       ("side", {}, "is not head or base")):
            with self.subTest(field=field, value=value):
                e = self.bad(fragment, message(verdict("changes_requested", [finding(**{field: value})])))
                self.assertNotIsInstance(e, TypeError)

    def test_malformed_severity_and_verdict_types_refused_without_type_error(self):
        for value in ([], {}):
            with self.subTest(value=value):
                self.bad("severity", message(verdict("changes_requested", [finding(severity=value)])))
                self.bad("is not one of", message(verdict(value)))


# ---------- §3.5 duplicates, retries and refusals ----------

class Duplicates(RelayEnv):
    def test_rerun_after_success_does_nothing(self):
        api = self.pc()
        self.relay(api)
        n = len(api.writes())
        self.assertIn("already relayed", self.relay(api))
        self.assertEqual(len(api.writes()), n)

    def test_second_run_for_same_head_refused(self):
        api = self.pc()
        self.relay(api)
        api.issue["status"] = "in_review"  # say the Board reopened it; a new review run comes in
        api.runs.append({"runId": "run-2", "agentId": REVIEWER, "status": "succeeded", "createdAt": rp.iso(LATER)})
        api.logs["run-2"] = run_log(message(verdict()))
        n = len(api.writes())
        with self.assertRaises(rp.ReviewPackError) as cm:
            self.relay(api, run_id="run-2")
        self.assertIn("already relayed (run run-1)", str(cm.exception))
        self.assertEqual(len(api.writes()), n)

    def test_receipt_in_audit_log_only_still_refuses_another_run(self):
        rp.audit(self.rr, "relay", LATER, issue=KEY, head=SHA_HEAD, run_id="run-0", reason="approved")
        api = self.pc()
        with self.assertRaises(rp.ReviewPackError) as cm:
            self.relay(api)
        self.assertIn("already relayed (run run-0)", str(cm.exception))
        self.assertEqual(api.writes(), [])
        self.assertEqual(self.events().count("relay"), 1)

    def test_decision_failed_earlier_retries_only_the_decision(self):
        api = self.pc()
        api.fail[("PATCH", f"/issues/{ISSUE_ID}")] = [http("PATCH", "/issues/x", 422, "Only the active reviewer")]
        with self.assertRaises(rl.RelayRefused):
            self.relay(api)
        self.assertEqual(len([c for c in api.comments if rl.receipt(RUN, SHA_HEAD) in c["body"]]), 1)
        self.relay(api)  # the Board fixed the stage; re-run
        self.assertEqual(len([c for c in api.comments if rl.receipt(RUN, SHA_HEAD) in c["body"]]), 1)
        self.assertEqual(api.issue["status"], "done")
        self.assertEqual([m for m, _ in api.writes()], ["POST", "PATCH", "PATCH"])


class RetriesAndRefusals(RelayEnv):
    def test_5xx_retried_with_backoff(self):
        api = self.pc()
        api.fail[("PATCH", f"/issues/{ISSUE_ID}")] = [http("PATCH", "p", 502), http("PATCH", "p", 503)]
        self.relay(api)
        self.assertEqual(self.sleeps, [1, 2])
        self.assertEqual(api.issue["status"], "done")

    def test_network_error_retried(self):
        api = self.pc()
        api.fail[("GET", f"/issues/{KEY}")] = [HttpError("Paperclip is not reachable at http://127.0.0.1:3100/api")]
        self.relay(api)
        self.assertEqual(self.sleeps, [1])

    def test_three_transient_failures_stop_and_audit(self):
        api = self.pc()
        api.fail[("PATCH", f"/issues/{ISSUE_ID}")] = [http("PATCH", "p", 500)] * 3
        with self.assertRaises(rl.RelayRefused) as cm:
            self.relay(api)
        self.assertIn("gave up after 3 attempts", str(cm.exception))
        self.assertIn("pc.py approve SOU-12", str(cm.exception))
        self.assertEqual(self.events()[-1], "relay-refused")
        self.assertEqual(api.issue["status"], "in_review")
        self.assertEqual(len(api.comments), 1)  # the findings comment stays

    def test_4xx_not_retried_comment_stays_fallback_named(self):
        api = self.pc()
        api.fail[("PATCH", f"/issues/{ISSUE_ID}")] = [
            http("PATCH", "p", 422, "Only the active reviewer or approver can advance the current execution stage")]
        with self.assertRaises(rl.RelayRefused) as cm:
            self.relay(api)
        msg = str(cm.exception)
        self.assertIn("Only the active reviewer", msg)
        self.assertIn("pc.py approve SOU-12 or pc.py request-changes SOU-12", msg)
        self.assertEqual(self.sleeps, [])
        self.assertEqual(len([m for m, _, _ in api.calls if m == "PATCH"]), 1)
        self.assertEqual(self.events()[-1], "relay-refused")
        self.assertIn(rl.receipt(RUN, SHA_HEAD), api.comments[0]["body"])

    def test_comment_4xx_refused_without_decision(self):
        api = self.pc()
        api.fail[("POST", f"/issues/{ISSUE_ID}/comments")] = [http("POST", "p", 403, "forbidden")]
        with self.assertRaises(rl.RelayRefused):
            self.relay(api)
        self.assertEqual([m for m, _ in api.writes()], ["POST"])
        self.assertEqual(api.issue["status"], "in_review")

    def test_comment_stored_despite_5xx_is_not_posted_twice(self):
        api = self.pc()
        api.store_despite_error = True
        api.fail[("POST", f"/issues/{ISSUE_ID}/comments")] = [http("POST", "p", 504)]
        self.relay(api)
        self.assertEqual(len([c for c in api.comments if rl.receipt(RUN, SHA_HEAD) in c["body"]]), 1)
        self.assertEqual(api.issue["status"], "done")


# ---------- CLI ----------

class Cli(RelayEnv):
    def args(self, key=KEY):
        return argparse.Namespace(key=key, run_id=RUN, identity=rp.BOARD, review_root=self.rr, staging_root=self.sr)

    def test_parser_wired_into_pc(self):
        import pc
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        rl.add_parser(sub, pc.cmd_review_relay)
        a = p.parse_args(["review-relay", KEY, "--run-id", RUN])
        self.assertEqual((a.key, a.run_id, a.identity, a.fn), (KEY, RUN, rp.BOARD, pc.cmd_review_relay))

    def test_cli_relays_with_injected_head(self):
        api = self.pc()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rl.cmd_review_relay(self.args(), api, lambda: REVIEWER, head_now=lambda: SHA_HEAD, now=LATER,
                                sleep=self.sleeps.append)
        self.assertIn("relayed approved", out.getvalue())

    def test_fixture_package_cannot_be_relayed(self):
        api = self.pc()
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.cmd_review_relay(self.args(), api, lambda: REVIEWER, now=LATER)
        self.assertIn("built from a fixture", str(cm.exception))
        self.assertIn("Nothing was recorded", str(cm.exception))
        self.assertEqual(api.calls, [])
        e = rp.read_audit(self.rr)[-1]
        self.assertEqual((e["event"], e["runId"]), ("refuse", RUN))
        self.assertTrue(e["reason"].startswith("relay: "))

    def test_failed_check_audited_as_refuse(self):
        with self.assertRaises(rp.ReviewPackError):
            rl.cmd_review_relay(self.args(), self.pc(status="todo"), lambda: REVIEWER, head_now=lambda: SHA_HEAD,
                                now=LATER)
        self.assertEqual(self.events()[-1], "refuse")

    def test_malformed_finding_refused_and_audited_through_the_cli(self):
        """A malformed verdict goes through the CLI's controlled refusal: ReviewPackError, a `refuse` audit line,
        nothing written to Paperclip (no TypeError escapes cmd_review_relay)."""
        for field, value in (("path", []), ("side", {})):
            with self.subTest(field=field):
                api = self.pc(verdict("changes_requested", [finding(**{field: value})]))
                with self.assertRaises(rp.ReviewPackError) as cm:
                    rl.cmd_review_relay(self.args(), api, lambda: REVIEWER, head_now=lambda: SHA_HEAD, now=LATER,
                                        sleep=self.sleeps.append)
                self.assertIn("Nothing was recorded", str(cm.exception))
                self.assertEqual(api.writes(), [])
                e = rp.read_audit(self.rr)[-1]
                self.assertEqual((e["event"], e["runId"]), ("refuse", RUN))
                self.assertIn(f"finding #1: {field}", e["reason"])

    def test_bad_key(self):
        with self.assertRaises(rp.ReviewPackError) as cm:
            rl.cmd_review_relay(self.args("sou-12; rm"), self.pc(), lambda: REVIEWER, head_now=lambda: SHA_HEAD,
                                now=LATER)
        self.assertIn("is not an issue key", str(cm.exception))


class GitHubHead(unittest.TestCase):
    MANIFEST = {"source": "github-api", "repository": "acme/demo", "pullRequest": {"number": 7}}

    def transport(self, status, body, seen):
        def t(method, url, headers):
            seen.append((method, url, headers.get("Authorization")))
            return status, {}, json.dumps(body).encode()
        return t

    def test_reads_pr_head_with_token_in_header_only(self):
        seen = []
        head = rl.github_head(self.MANIFEST, TOKEN, self.transport(200, {"head": {"sha": "a" * 40},
                                                                          "base": {"sha": "b" * 40}}, seen))()
        self.assertEqual(head, "a" * 40)
        self.assertEqual(seen[0][0], "GET")
        self.assertTrue(seen[0][1].endswith("/repos/acme/demo/pulls/7"))
        self.assertNotIn(TOKEN, seen[0][1])
        self.assertEqual(seen[0][2], f"Bearer {TOKEN}")

    def test_401_refused_and_redacted(self):
        f = rl.github_head(self.MANIFEST, TOKEN, self.transport(401, {"message": f"Bad credentials {TOKEN}"}, []))
        with self.assertRaises(rp.ReviewPackError) as cm:
            f()
        self.assertNotIn(TOKEN, str(cm.exception))

    def test_fixture_manifest_refused(self):
        with self.assertRaises(rp.ReviewPackError):
            rl.github_head({"source": "fixture"})


class NoWritesOutsideRelay(unittest.TestCase):
    def test_module_imports_no_network_code_at_import(self):
        with open(rl.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("urllib", src)
        self.assertNotIn("subprocess", src)


if __name__ == "__main__":
    unittest.main()
