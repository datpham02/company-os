"""Tests for the Verdict Relay (review_relay.py, OQ-042 Phase 4a) with an in-memory fake Paperclip and a fake
PR head. No network, no Paperclip, no token. Run: python -I -W error test_review_relay.py
(also collected by test_pc.py)"""
import argparse
import contextlib
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
LATER = NOW + datetime.timedelta(minutes=5)
TOKEN = "github_pat_TESTTOKEN0123456789abcdefABCDEF_xyz"


class HttpError(Exception):
    """Shaped like pc.ApiError: 'METHOD path -> code: body'."""


def http(method, path, code, body="error"):
    return HttpError(f"{method} {path} -> {code}: {body}")


def verdict(verdict="approved", findings=None, issue=KEY, head=SHA_HEAD, **over):
    v = {"schema": rp.VERDICT_SCHEMA, "verdict": verdict, "issue": issue, "headSha": head,
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


def run_log(final, extra_events=()):
    """GET /heartbeat-runs/<id>/log: JSONL records whose chunks carry Claude Code's stream-json output."""
    events = [{"type": "system", "subtype": "init"}] + list(extra_events)
    if final is not None:
        events.append({"type": "result", "subtype": "success", "result": final})
    stream = "".join(json.dumps(e) + "\n" for e in events)
    half = len(stream) // 2  # a record boundary inside a JSON line, as real chunking does
    recs = [{"ts": "t", "stream": "stdout", "chunk": stream[:half]}, {"ts": "t", "stream": "stdout", "chunk": stream[half:]}]
    return {"content": "".join(json.dumps(r) + "\n" for r in recs)}


class FakePaperclip:
    def __init__(self, final, status="in_review", participant=None, runs=None):
        self.issue = {"id": ISSUE_ID, "companyId": "co-1", "identifier": KEY, "status": status,
                      "executionState": {"currentStageType": "review",
                                         "currentParticipant": participant or {"type": "user", "userId": rp.BOARD}}}
        self.comments = []
        self.runs = runs if runs is not None else [
            {"runId": RUN, "agentId": REVIEWER, "status": "succeeded", "createdAt": rp.iso(LATER)}]
        self.logs = {RUN: run_log(final)}
        self.details = {}  # run id -> GET /heartbeat-runs/<id> body (company-scoped runs)
        self.calls = []
        self.fail = {}  # (method, path) -> list of exceptions raised by successive calls
        self.store_despite_error = False  # a POST that fails after the server stored the comment

    def writes(self):
        return [(m, p) for m, p, _ in self.calls if m in ("POST", "PATCH")]

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
            return list(self.runs)
        if method == "GET" and path.startswith("/heartbeat-runs/") and path.endswith("/log"):
            return self.logs.get(path.split("/")[2], {"content": ""})
        if method == "GET" and path.startswith("/heartbeat-runs/") and path.split("/")[2] in self.details:
            return dict(self.details[path.split("/")[2]])
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
        self.head = SHA_HEAD
        self.sleeps = []

    def pc(self, v=None, **kw):
        final = message(v if v is not None else verdict()) if not isinstance(v, str) else v
        return FakePaperclip(final, **kw)

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


class Check2CompanyScopedRun(RelayEnv):
    """Phase 4b finding (V2): the reviewer is woken without an issue, so its run is not in the issue's runs."""

    def api(self, **over):
        api = self.pc(runs=[])
        d = {"id": RUN, "companyId": "co-1", "agentId": REVIEWER, "issueId": None, "scopeKind": "company",
             "status": "succeeded", "createdAt": rp.iso(LATER)}
        d.update(over)
        api.details[RUN] = d
        return api

    def test_company_scoped_run_accepted(self):
        api = self.api()
        self.assertIn("relayed approved", self.relay(api))

    def test_run_of_another_company_refused(self):
        self.refused_nothing_written("another company", self.api(companyId="co-2"))

    def test_run_scoped_to_another_issue_refused(self):
        self.refused_nothing_written("scoped to another issue", self.api(issueId="uuid-99"))

    def test_run_scoped_to_this_issue_accepted(self):
        self.assertIn("relayed approved", self.relay(self.api(issueId=ISSUE_ID)))

    def test_unknown_run_refused(self):
        api = self.pc(runs=[])  # GET /heartbeat-runs/<id> answers 404
        self.refused_nothing_written("is not a run of", api)

    def test_run_id_mismatch_in_detail_refused(self):
        self.refused_nothing_written("is not a run of", self.api(id="run-other"))

    def test_issue_without_company_refused(self):
        api = self.api()
        del api.issue["companyId"]
        self.refused_nothing_written("another company", api)

    def test_documented_limit_any_company_reviewer_run_after_staging_passes_check_2(self):
        """Documents what check 2 does NOT establish (_company_run docstring): nothing ties a company-scoped
        run to this review. A run whose wake had nothing to do with the issue still passes check 2; only the
        verdict (check 5) and the receipt bind it."""
        api = self.api(scopeKind="company", contextSnapshot={"wakeReason": "unrelated chore"})
        self.assertIn("relayed approved", self.relay(api))

    def test_company_run_still_bound_by_the_verdict(self):
        api = self.api(contextSnapshot={"wakeReason": "unrelated chore"})
        api.logs[RUN] = run_log(message(verdict(issue="SOU-99")))
        self.refused_nothing_written("does not match the staging lock", api)

    def test_company_run_still_checked_for_agent_status_and_time(self):
        self.refused_nothing_written("is not a code-reviewer run", self.api(agentId=OTHER_AGENT))
        self.refused_nothing_written("not succeeded", self.api(status="failed"))
        self.refused_nothing_written("before the package was staged",
                                     self.api(createdAt=rp.iso(NOW - datetime.timedelta(seconds=1))))


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
