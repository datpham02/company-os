"""Tests for merge-audit.py (Phase 4, P4-T03). Offline: Paperclip and gh are fakes.

    python -I -W error scripts/maintenance/test_merge_audit.py
"""
import contextlib
import importlib.util
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("merge_audit", os.path.join(HERE, "merge-audit.py"))
ma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ma)

OK = {"status": "done", "stages": ["review", "approval"], "completedAt": "2026-11-05T10:00:00.500Z"}


def pr(n, branch, merged="2026-11-05T10:00:01Z", by="board"):
    return {"repo": "o/r", "number": n, "branch": branch, "mergedAt": merged, "mergedBy": by}


class Audit(unittest.TestCase):
    def test_clean_history_has_no_findings(self):
        self.assertEqual(ma.audit({"SOU-1": OK}, [pr(1, "SOU-1-thing")], "board"), [])

    def test_each_finding(self):
        issues = {"SOU-1": OK,
                  "SOU-2": dict(OK, stages=["review"]),
                  "SOU-3": dict(OK, status="in_review"),
                  "SOU-4": dict(OK, completedAt="2026-11-05T10:00:02Z")}
        prs = [pr(1, "release/v1"), pr(2, "SOU-99-x"), pr(3, "SOU-2-a"), pr(4, "SOU-3-b"), pr(5, "SOU-4-c"),
               pr(6, "SOU-1-d", by="someone")]
        findings = "\n".join(ma.audit(issues, prs, "board"))
        for want in ("o/r#1: unlinked", "o/r#2: unknown Task SOU-99", "o/r#3 (SOU-2): no approval stage",
                     "o/r#4 (SOU-3): Task is in_review, not done", "o/r#5 (SOU-4): merged before approval",
                     "o/r#6 (SOU-1): merged by another account (someone)"):
            self.assertIn(want, findings)

    def test_times_are_compared_as_times(self):
        """Same second: 46Z is earlier than 46.5Z; a string comparison would get this wrong."""
        issues = {"SOU-1": dict(OK, completedAt="2026-11-04T08:59:46Z")}
        self.assertEqual(ma.audit(issues, [pr(1, "SOU-1-a", merged="2026-11-04T08:59:46.500Z")], "board"), [])
        issues = {"SOU-1": dict(OK, completedAt="2026-11-04T08:59:46.500Z")}
        self.assertIn("merged before approval",
                      ma.audit(issues, [pr(1, "SOU-1-a", merged="2026-11-04T08:59:46Z")], "board")[0])

    def test_main_reads_only(self):
        gets, ghs = [], []

        def get(path):
            gets.append(path)
            if path == "/companies":
                return [{"id": "c1", "name": "Soucean", "issuePrefix": "SOU"}]
            if path.startswith("/companies/c1/issues"):
                return [{"id": "i1"}]
            return {"identifier": "SOU-1", "status": "done", "completedAt": OK["completedAt"],
                    "executionPolicy": {"stages": [{"type": "review"}, {"type": "approval"}]}}

        def gh(args):
            ghs.append(args)
            if args[:2] == ["api", "user"]:
                return json.dumps({"login": "board"})
            return json.dumps([{"number": 1, "headRefName": "SOU-1-a", "mergedAt": "2026-11-05T10:00:01Z",
                                "mergedBy": {"login": "board"}}])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ma.main(["--company", "SOU"], get=get, gh=gh)
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(all(a[0] in ("pr", "api") and a[1] in ("list", "user") for a in ghs))  # reads only


if __name__ == "__main__":
    unittest.main()
