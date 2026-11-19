"""Tests for the Write Set conflict guard in pc.py. Stdlib only, no Paperclip needed.

Run from the repository root: python -I .claude/skills/paperclip/scripts/test_pc.py
"""
import argparse
import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves the script folder off sys.path
import pc  # noqa: E402

CID, PA, PB = "co-1", "proj-a", "proj-b"


def ws_desc(*paths):
    return "Goal.\n\n## Write set\n" + "".join(f"- `{p}`\n" for p in paths) + "\n## Acceptance criteria\n- [ ] works\n"


def make(n, status="in_progress", paths=("src/other.ts",), project=PA, ws=None, desc=None, assignee="ag-1"):
    return {
        "id": f"id-{n}", "identifier": f"SOU-{n}", "issueNumber": n, "title": f"Task {n}", "status": status,
        "companyId": CID, "projectId": project, "assigneeAgentId": assignee,
        "description": desc if desc is not None else ws_desc(*paths),
        "executionPolicy": {"stages": [{"type": "review"}]}, "blockedBy": [],
        "currentExecutionWorkspace": ws,
    }


def P(path):
    return pc.normalize_path(path)


class PathOverlap(unittest.TestCase):
    def test_same_file(self):
        self.assertTrue(pc.paths_overlap(P("src/a.ts"), P("src/a.ts")))

    def test_different_files(self):
        self.assertFalse(pc.paths_overlap(P("src/a.ts"), P("src/b.ts")))

    def test_directory_contains_file_both_directions(self):
        self.assertTrue(pc.paths_overlap(P("src/scenes/"), P("src/scenes/VigilScene.ts")))
        self.assertTrue(pc.paths_overlap(P("src/scenes/VigilScene.ts"), P("src/scenes/")))

    def test_sibling_directories(self):
        self.assertFalse(pc.paths_overlap(P("src/scenes/"), P("src/ui/")))

    def test_no_substring_match(self):
        self.assertFalse(pc.paths_overlap(P("src/app"), P("src/application")))
        self.assertFalse(pc.paths_overlap(P("src/app/x.ts"), P("src/application/x.ts")))

    def test_normalization(self):
        self.assertEqual(P("./src//scenes/./A.ts"), ("src", "scenes", "A.ts"))
        self.assertEqual(P("src\\scenes\\A.ts"), ("src", "scenes", "A.ts"))
        self.assertTrue(pc.paths_overlap(P("./src/a.ts"), P("src\\a.ts")))

    def test_parent_traversal_rejected(self):
        for bad in ("../secrets.txt", "src/../../x", "/etc/passwd", "C:\\x\\y", "./"):
            with self.assertRaises(pc.WriteSetError, msg=bad):
                P(bad)

    def test_case_insensitive(self):
        # Documented convention: the studio runs on Windows, where these are one file.
        self.assertTrue(pc.paths_overlap(P("src/Scene.ts"), P("src/scene.ts")))

    def test_globs(self):
        self.assertTrue(pc.paths_overlap(P("src/*.ts"), P("src/a.ts")))
        self.assertFalse(pc.paths_overlap(P("src/*.ts"), P("src/a.css")))
        self.assertTrue(pc.paths_overlap(P("src/**"), P("src/scenes/deep/A.ts")))
        self.assertTrue(pc.paths_overlap(P("src/**/*.ts"), P("src/x/y.css")))  # ** is conservative
        self.assertFalse(pc.paths_overlap(P("src/**"), P("docs/a.md")))
        self.assertTrue(pc.paths_overlap(P("src/scene?.ts"), P("src/scene1.ts")))
        self.assertTrue(pc.paths_overlap(P("src/*"), P("src/scenes/A.ts")))  # src/* covers the folder src/scenes
        self.assertTrue(pc.paths_overlap(P("src/*.ts"), P("src/a*.ts")))
        self.assertFalse(pc.paths_overlap(P("src/*.ts"), P("src/*.css")))
        self.assertFalse(pc.paths_overlap(P("src/a*.ts"), P("src/b*.ts")))


class ParseWriteSet(unittest.TestCase):
    def raws(self, desc):
        return [r for r, _ in pc.parse_write_set(desc)]

    def test_backticked_items_and_section_end(self):
        desc = ws_desc("src/a.ts", "docs/") + "- `not/in/write/set.ts`\n"
        self.assertEqual(self.raws(desc), ["src/a.ts", "docs/"])

    def test_archived_heading_form_and_trailing_prose(self):
        desc = ("## Files owned by this Task (no other M1 Task may touch them)\n"
                "- `docs/design/DESIGN.md`\n- `src/beam/index.ts` (reads `TuningConfig`)\n"
                "- src/plain.ts — no backticks\n* [ ] `a.ts`, `b/c.ts`\n")
        self.assertEqual(self.raws(desc), ["docs/design/DESIGN.md", "src/beam/index.ts", "src/plain.ts", "a.ts", "b/c.ts"])

    def test_none(self):
        self.assertEqual(pc.parse_write_set("## Write set\n- none\n"), [])

    def test_missing_or_malformed(self):
        for desc in (None, "", "no heading here", "## Write set\nJust prose, no list.\n",
                     "## Write set\n- the beam module\n", "## Write set\n- `../outside.ts`\n",
                     "## Write set\n- `TuningConfig` in src\n",
                     "## Write set\n- `docs/design/a\n"):  # cut off mid-path (seen in the GAM export)
            with self.assertRaises(pc.WriteSetError, msg=repr(desc)):
                pc.parse_write_set(desc)


class ComparisonReason(unittest.TestCase):
    def test_active_statuses_compared(self):
        for s in ("todo", "in_progress", "in_review", "blocked", "some_new_status"):
            self.assertTrue(pc.comparison_reason(make(1, status=s)), s)

    def test_cancelled_ignored(self):
        self.assertIsNone(pc.comparison_reason(make(1, status="cancelled")))

    def test_backlog(self):
        self.assertIsNone(pc.comparison_reason(make(1, status="backlog")))
        inherited = make(1, status="backlog", ws={"sourceIssueId": "id-9"})
        self.assertIsNone(pc.comparison_reason(inherited))
        started = make(1, status="backlog", ws={"sourceIssueId": "id-1"})
        self.assertTrue(pc.comparison_reason(started))

    def test_done_approved_but_not_merged_is_compared(self):
        for state in ("unmerged", "unknown", None):
            i = make(1, status="done", ws={"sourceIssueId": "id-1", "status": "active", "deliveryState": state})
            self.assertTrue(pc.comparison_reason(i), state)

    def test_done_and_merged_ignored(self):
        for state in ("merged_via_pr", "merged_by_ancestry"):
            i = make(1, status="done", ws={"status": "active", "deliveryState": state})
            self.assertIsNone(pc.comparison_reason(i), state)
        reaped = make(1, status="done", ws={"status": "archived", "deliveryState": "unknown", "cleanupReason": "issue_terminal"})
        self.assertIsNone(pc.comparison_reason(reaped))
        failed = make(1, status="done", ws={"status": "cleanup_failed", "deliveryState": "unknown",
                                            "cleanupReason": "issue_terminal | git error"})
        self.assertIsNone(pc.comparison_reason(failed))

    def test_done_archived_by_hand_still_compared(self):
        i = make(1, status="done", ws={"status": "archived", "deliveryState": "unknown", "cleanupReason": "manual"})
        self.assertTrue(pc.comparison_reason(i))

    def test_done_without_workspace_ignored(self):
        self.assertIsNone(pc.comparison_reason(make(1, status="done", ws=None)))


class FakePaperclip:
    """Minimal stand-in for pc.call / pc.issue that records writes."""

    def __init__(self, issues, fail_list=False):
        self.issues = {i["id"]: i for i in issues}
        self.by_key = {i["identifier"]: i for i in issues}
        self.fail_list = fail_list
        self.writes = []

    def issue(self, ref):
        i = self.by_key.get(ref) or self.issues.get(ref)
        if i is None:
            raise pc.ApiError(f"GET /issues/{ref} -> 404")
        return dict(i)

    def call(self, method, path, body=None):
        if method == "GET" and path == f"/companies/{CID}/issues":
            if self.fail_list:
                raise pc.ApiError("Paperclip is not reachable")
            # The list endpoint omits the execution workspace.
            return [{k: v for k, v in i.items() if k != "currentExecutionWorkspace"} for i in self.issues.values()]
        if method == "GET" and path.startswith(f"/companies/{CID}/issues?status="):
            s = path.split("=", 1)[1]
            return [i for i in self.issues.values() if i["status"] == s]
        if method == "PATCH":
            self.writes.append((path, body))
            iid = path.rsplit("/", 1)[1]
            self.issues[iid].update(body)
            return dict(self.issues[iid])
        raise AssertionError(f"unexpected call {method} {path}")


def release(fake, *keys, force=False):
    out = io.StringIO()
    with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "issue", fake.issue), \
            contextlib.redirect_stdout(out):
        pc.cmd_release(argparse.Namespace(keys=list(keys), force=force))
    return out.getvalue()


class GuardFiltering(unittest.TestCase):
    def test_same_project_conflict_and_other_project_ignored(self):
        cand = make(10, status="backlog", paths=("src/a.ts",))
        same = make(11, status="in_review", paths=("src/a.ts",), assignee="ag-2")
        other_project = make(12, status="in_progress", paths=("src/a.ts",), project=PB, assignee="ag-3")
        fake = FakePaperclip([cand, same, other_project])
        with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "issue", fake.issue):
            report = pc.write_set_guard(fake.issue("SOU-10"), {})
        text = "\n".join(report)
        self.assertIn("SOU-11", text)
        self.assertNotIn("SOU-12", text)
        self.assertNotIn("Conflicts with: SOU-10", text)  # never compared with itself

    def test_candidate_without_project_blocks(self):
        cand = make(10, status="backlog", project=None)
        fake = FakePaperclip([cand])
        with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "issue", fake.issue):
            report = pc.write_set_guard(fake.issue("SOU-10"), {})
        self.assertIn("no project", "\n".join(report))

    def test_other_task_with_unreadable_write_set_blocks(self):
        cand = make(10, status="backlog", paths=("src/a.ts",))
        vague = make(11, status="in_progress", desc="## Write set\n- the scene code\n", assignee="ag-2")
        fake = FakePaperclip([cand, vague])
        out = release(fake, "SOU-10")
        self.assertIn("Cannot check: SOU-11", out)
        self.assertEqual(fake.writes, [])

    def test_all_conflicts_listed_in_order(self):
        cand = make(10, status="backlog", paths=("src/scenes/", "package.json"))
        c13 = make(13, status="blocked", paths=("package.json",), assignee="ag-3")
        c11 = make(11, status="in_progress", paths=("src/scenes/VigilScene.ts", "src/scenes/Menu.ts"), assignee="ag-2")
        fine = make(12, status="todo", paths=("docs/readme.md",), assignee="ag-4")
        fake = FakePaperclip([cand, c13, c11, fine])
        out = release(fake, "SOU-10")
        self.assertLess(out.index("Conflicts with: SOU-11"), out.index("Conflicts with: SOU-13"))
        self.assertIn("src/scenes/  (overlaps src/scenes/Menu.ts)", out)
        self.assertIn("src/scenes/  (overlaps src/scenes/VigilScene.ts)", out)
        self.assertIn("  - package.json", out)
        self.assertNotIn("SOU-12", out)


class ReleaseIntegration(unittest.TestCase):
    def test_conflict_blocks_without_side_effects_even_with_force(self):
        cand = make(45, status="backlog", paths=("src/scenes/VigilScene.ts",))
        merged_later = make(44, status="done", paths=("src/scenes/VigilScene.ts",), assignee="ag-2",
                            ws={"sourceIssueId": "id-44", "status": "active", "deliveryState": "unmerged"})
        fake = FakePaperclip([cand, merged_later])
        for force in (False, True):
            out = release(fake, "SOU-45", force=force)
            self.assertIn("Release blocked: Write Set conflicts detected.", out)
            self.assertIn("Conflicts with: SOU-44", out)
            self.assertIn("--force does not override", out)
            self.assertEqual(fake.writes, [])
            self.assertEqual(fake.issues["id-45"]["status"], "backlog")

    def test_merged_task_does_not_block(self):
        cand = make(45, status="backlog", paths=("src/scenes/VigilScene.ts",))
        merged = make(44, status="done", paths=("src/scenes/VigilScene.ts",), assignee="ag-2",
                      ws={"sourceIssueId": "id-44", "status": "active", "deliveryState": "merged_via_pr"})
        fake = FakePaperclip([cand, merged])
        out = release(fake, "SOU-45")
        self.assertIn("released -> todo", out)
        self.assertEqual(fake.writes, [("/issues/id-45", {"status": "todo"})])

    def test_no_conflict_keeps_existing_release_path(self):
        cand = make(20, status="backlog", paths=("src/a.ts",))
        other = make(21, status="in_progress", paths=("src/b.ts",), assignee="ag-2")
        fake = FakePaperclip([cand, other])
        out = release(fake, "SOU-20")
        self.assertIn("SOU-20: released -> todo", out)
        self.assertEqual(fake.writes, [("/issues/id-20", {"status": "todo"})])

    def test_second_key_compared_with_first_released(self):
        first = make(30, status="backlog", paths=("src/a.ts",), assignee="ag-1")
        second = make(31, status="backlog", paths=("src/a.ts",), assignee="ag-2")
        fake = FakePaperclip([first, second])
        out = release(fake, "SOU-30", "SOU-31")
        self.assertIn("SOU-30: released", out)
        self.assertIn("SOU-31: not released", out)
        self.assertIn("Conflicts with: SOU-30", out)
        self.assertEqual(fake.writes, [("/issues/id-30", {"status": "todo"})])

    def test_api_failure_is_not_an_empty_list(self):
        cand = make(40, status="backlog", paths=("src/a.ts",))
        fake = FakePaperclip([cand], fail_list=True)
        out = release(fake, "SOU-40", force=True)
        self.assertIn("could not read Paperclip", out)
        self.assertEqual(fake.writes, [])

    def test_missing_candidate_write_set_blocks_even_with_force(self):
        cand = make(41, status="backlog", desc="Goal only, no write set.")
        fake = FakePaperclip([cand])
        out = release(fake, "SOU-41", force=True)
        self.assertIn("no '## Write set' section", out)
        self.assertEqual(fake.writes, [])

    def test_force_still_skips_other_checks(self):
        cand = make(42, status="backlog", paths=("src/a.ts",))
        cand["executionPolicy"] = {}
        fake = FakePaperclip([cand])
        self.assertIn("not released", release(fake, "SOU-42"))
        out = release(fake, "SOU-42", force=True)
        self.assertIn("released -> todo", out)


if __name__ == "__main__":
    unittest.main()
