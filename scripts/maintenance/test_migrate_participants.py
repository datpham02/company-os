"""Tests for migrate-participants.py (D-AUTH-02). Offline: Paperclip is a fake in memory.

    python -I -W error scripts/maintenance/test_migrate_participants.py
"""
import contextlib
import copy
import io
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("migrate_participants", os.path.join(HERE, "migrate-participants.py"))
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)

LB, NEW = "local-board", "u-claimed"


def stage(sid, typ, *users):
    return {"id": sid, "type": typ, "participants": [{"id": f"{sid}-p{n}", "type": "user", "userId": u}
                                                     for n, u in enumerate(users)]}


def issue(ident, status, *stages, current=None):
    return {"id": ident.lower(), "identifier": ident, "status": status, "assigneeAgentId": "a-1",
            "assigneeUserId": None, "executionPolicy": {"mode": "normal", "stages": list(stages)},
            "executionState": ({"currentParticipant": {"type": "user", "userId": current}} if current else None)}


class Fake:
    def __init__(self, issues, drift=False):
        self.issues = {i["id"]: i for i in issues}
        self.patches = []
        self.drift = drift

    def call(self, method, path, body=None):
        if method == "GET" and path == "/companies":
            return [{"id": "c1", "name": "Soucean", "issuePrefix": "SOU"}]
        if method == "GET" and path == "/cli-auth/me":
            return {"userId": NEW}
        if method == "GET" and path.startswith("/companies/c1/issues"):
            return [{"id": i["id"], "status": i["status"]} for i in self.issues.values()]
        iid = path.split("/")[2]
        if method == "GET":
            return copy.deepcopy(self.issues[iid])
        assert method == "PATCH"
        cur = self.issues[iid]
        if body["expectedExecutionPolicy"] != cur["executionPolicy"]:
            raise mp.Stop("409 execution_policy_changed")
        self.patches.append(iid)
        cur["executionPolicy"] = copy.deepcopy(body["executionPolicy"])
        if self.drift:
            cur["status"] = "blocked"
        return cur


def fixture():
    return [issue("SOU-17", "todo", stage("s1", "approval", LB)),                       # change
            issue("SOU-30", "in_progress", stage("s2", "review", "x"), stage("s3", "approval", LB)),  # change
            issue("SOU-28", "in_review", stage("s4", "approval", LB), current=LB),        # VA-5 skip
            issue("SOU-40", "todo", stage("s5", "approval", LB, NEW)),                   # VA-4c skip
            issue("SOU-9", "done", stage("s6", "approval", LB)),                         # closed, untouched
            issue("SOU-50", "todo", stage("s7", "review", "someone"))]                   # not affected


class Migrate(unittest.TestCase):
    def test_dry_run_plans_and_writes_nothing(self):
        f, lines = Fake(fixture()), []
        bad = mp.run("SOU", LB, "me", False, f.call, lines.append)
        text = "\n".join(lines)
        self.assertEqual(f.patches, [])
        self.assertEqual(bad, 2)
        self.assertIn("PLAN   SOU-17", text)
        self.assertIn("PLAN   SOU-30", text)
        self.assertIn("SKIP   SOU-28", text)
        self.assertIn("VA-5", text)
        self.assertIn("SKIP   SOU-40", text)
        self.assertIn("VA-4c", text)
        self.assertNotIn("SOU-9", text)
        self.assertNotIn("SOU-50", text)

    def test_apply_changes_only_the_user_id_and_keeps_ids(self):
        f = Fake(fixture())
        before = copy.deepcopy(f.issues["sou-30"])
        mp.run("SOU", LB, "me", True, f.call, lambda _: None)
        self.assertEqual(sorted(f.patches), ["sou-17", "sou-30"])
        after = f.issues["sou-30"]
        self.assertEqual(mp.shape(after["executionPolicy"]), mp.shape(before["executionPolicy"]))
        self.assertEqual(after["executionPolicy"]["stages"][1]["participants"][0]["userId"], NEW)
        self.assertEqual(after["executionPolicy"]["stages"][0], before["executionPolicy"]["stages"][0])

    def test_rollback_is_the_same_tool_reversed(self):
        f = Fake(fixture())
        mp.run("SOU", LB, "me", True, f.call, lambda _: None)
        mp.run("SOU", NEW, LB, True, f.call, lambda _: None)
        self.assertEqual(f.issues["sou-17"]["executionPolicy"], fixture()[0]["executionPolicy"])

    def test_verification_failure_stops(self):
        f = Fake([issue("SOU-17", "todo", stage("s1", "approval", LB)),
                  issue("SOU-18", "todo", stage("s2", "approval", LB))], drift=True)
        with self.assertRaisesRegex(mp.Stop, "verification failed.*status changed"):
            mp.run("SOU", LB, "me", True, f.call, lambda _: None)
        self.assertEqual(len(f.patches), 1)  # stopped after the first

    def test_current_participant_skipped_in_any_status(self):
        f, lines = Fake([issue("SOU-60", "blocked", stage("s1", "approval", LB), current=LB)]), []
        self.assertEqual(mp.run("SOU", LB, "me", True, f.call, lines.append), 1)
        self.assertEqual(f.patches, [])
        self.assertIn("SKIP   SOU-60", " ".join(lines))

    def test_same_identity_refused(self):
        with self.assertRaisesRegex(mp.Stop, "same as --from"):
            mp.run("SOU", LB, LB, False, Fake([]).call, lambda _: None)

    def test_apply_needs_an_existing_backup(self):
        f, out = Fake(fixture()), io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(mp.main(["--company", "SOU", "--apply"], call=f.call), 2)
            self.assertEqual(mp.main(["--company", "SOU", "--apply", "--backup", "no-such-file.sql.gz"], call=f.call), 2)
        self.assertEqual(f.patches, [])
        self.assertIn("needs --backup", out.getvalue())


if __name__ == "__main__":
    unittest.main()
