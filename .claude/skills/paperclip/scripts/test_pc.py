"""Tests for the Write Set conflict guard in pc.py. Stdlib only, no Paperclip needed.

Run from the repository root: python -I .claude/skills/paperclip/scripts/test_pc.py
"""
import argparse
import contextlib
import io
import os
import sys
import unittest
import urllib.parse
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
    """Minimal stand-in for pc.call / pc.issue that records writes.

    The issue list behaves like Paperclip 2026.1023.0's: comma-separated `status`, keyset pages with
    sortField=id, sortDir=asc, afterId, and `limit` (page_limit stands in for the server cap).
    fail_list: True fails every list call; "in_progress" only the WIP listing; "unfiltered" only the full one.
    """

    def __init__(self, issues, fail_list=False, page_limit=None, fail_writes=False):
        self.issues = {i["id"]: i for i in issues}
        self.by_key = {i["identifier"]: i for i in issues}
        self.fail_list = fail_list
        self.fail_writes = fail_writes
        self.page_limit = page_limit
        self.writes = []
        self.list_calls = []

    def issue(self, ref):
        i = self.by_key.get(ref) or self.issues.get(ref)
        if i is None:
            raise pc.ApiError(f"GET /issues/{ref} -> 404")
        return dict(i)

    def list_page(self, query):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}
        self.list_calls.append(q)
        if (self.fail_list is True or (self.fail_list == "unfiltered" and "status" not in q)
                or (self.fail_list and q.get("status") == self.fail_list)):
            raise pc.ApiError("Paperclip is not reachable")
        assert q.get("sortField") == "id" and q.get("sortDir") == "asc", q
        statuses = set(q["status"].split(",")) if "status" in q else None
        rows = sorted(self.issues.values(), key=lambda i: i["id"])
        rows = [i for i in rows if (statuses is None or i["status"] in statuses)
                and ("afterId" not in q or i["id"] > q["afterId"])]
        limit = min(int(q["limit"]), self.page_limit or int(q["limit"]))
        # The list endpoint omits the execution workspace.
        return [{k: v for k, v in i.items() if k != "currentExecutionWorkspace"} for i in rows[:limit]]

    AGENTS = [{"id": "ag-1", "name": "web-engineer", "urlKey": "web-engineer"},
              {"id": "ag-2", "name": "qa-engineer", "urlKey": "qa-engineer"}]

    def call(self, method, path, body=None):
        if method == "GET" and path.startswith(f"/companies/{CID}/issues?"):
            return self.list_page(path.split("?", 1)[1])
        if method == "GET" and path.endswith(("/comments", "/runs")):
            return []
        if method == "GET" and path == "/companies":
            return [{"id": CID, "name": "Soucean", "issuePrefix": "SOU", "status": "active"}]
        if method == "GET" and path == f"/companies/{CID}/agents":
            return self.AGENTS
        if method == "POST":
            self.writes.append((method, path, body))
            if self.fail_writes:
                raise pc.ApiError(f"POST {path} -> 500")
            if path == f"/companies/{CID}/issues":
                return {"identifier": "SOU-99", **body}
            return {"id": "run-1", "status": "queued"}
        if method == "PATCH" and self.fail_writes:
            self.writes.append((method, path, body))
            raise pc.ApiError(f"PATCH {path} -> 500")
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
        fake = FakePaperclip([cand], fail_list="unfiltered")
        out = release(fake, "SOU-40", force=True)
        self.assertIn("Write Set conflict check could not read Paperclip", out)
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


# ---------- P0.2: WIP limit ----------

def row(n, status="in_progress", agent="ag-1", project=PA, company=CID, user=None):
    return {"id": f"id-{n}", "identifier": f"SOU-{n}", "status": status, "companyId": company,
            "projectId": project, "assigneeAgentId": agent, "assigneeUserId": user}


class WipCalculation(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(pc.agent_wip([], CID), {})

    def test_one(self):
        self.assertEqual(pc.agent_wip([row(1)], CID), {"ag-1": ["SOU-1"]})

    def test_two_in_different_projects(self):
        self.assertEqual(pc.agent_wip([row(1, project=PA), row(2, project=PB)], CID), {"ag-1": ["SOU-1", "SOU-2"]})

    def test_agents_are_separate(self):
        self.assertEqual(pc.agent_wip([row(1, agent="ag-1"), row(2, agent="ag-2")], CID),
                         {"ag-1": ["SOU-1"], "ag-2": ["SOU-2"]})

    def test_board_and_user_issues_do_not_count(self):
        self.assertEqual(pc.agent_wip([row(1, agent=None, user="local-board")], CID), {})

    def test_other_statuses_do_not_count(self):
        rows = [row(n, status=s) for n, s in enumerate(
            ("in_review", "blocked", "todo", "backlog", "done", "cancelled"), start=1)]
        self.assertEqual(pc.agent_wip(rows, CID), {})

    def test_malformed_fails_closed(self):
        missing_agent = row(1)
        del missing_agent["assigneeAgentId"]
        missing_status = row(2)
        del missing_status["status"]
        for bad in ([missing_agent], [missing_status], [{"status": "in_progress"}], ["SOU-1"],
                    [row(3, company="co-other")]):
            with self.assertRaises(pc.ApiError, msg=repr(bad)):
                pc.agent_wip(bad, CID)


class IssueListing(unittest.TestCase):
    def listing(self, fake, status=None):
        with mock.patch.object(pc, "call", fake.call):
            return pc.list_issues(CID, status)

    def test_reads_every_page(self):
        fake = FakePaperclip([make(n) for n in range(10, 17)], page_limit=3)
        with mock.patch.object(pc, "ISSUE_PAGE_LIMIT", 3):
            rows = self.listing(fake)
        self.assertEqual(len(rows), 7)
        self.assertEqual([c.get("afterId") for c in fake.list_calls], [None, "id-12", "id-15", "id-16"])

    def test_wip_found_on_a_later_page(self):
        issues = [make(n, status="in_review", assignee=f"ag-{n}") for n in range(10, 16)]
        issues.append(make(19, status="in_progress", assignee="ag-1"))
        fake = FakePaperclip(issues, page_limit=2)
        with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "ISSUE_PAGE_LIMIT", 2):
            self.assertEqual(pc.company_wip(CID), {"ag-1": ["SOU-19"]})

    def test_short_server_page_is_not_mistaken_for_the_end(self):
        # The server caps a page below what was asked: pc.py must not stop early or skip rows silently.
        fake = FakePaperclip([make(n) for n in range(10, 16)], page_limit=2)
        rows = self.listing(fake)  # asks for 1000, gets 2 per page
        self.assertEqual([r["id"] for r in rows], [f"id-{n}" for n in range(10, 16)])

    def test_unexpected_shapes_fail(self):
        for page in ({"items": []}, None, [{"identifier": "SOU-1"}]):
            with mock.patch.object(pc, "call", return_value=page):
                with self.assertRaises(pc.ApiError, msg=repr(page)):
                    pc.list_issues(CID)

    def test_cursor_that_does_not_advance_fails(self):
        same = [{"id": "id-1"}, {"id": "id-2"}]
        with mock.patch.object(pc, "call", return_value=same):
            with self.assertRaises(pc.ApiError):
                pc.list_issues(CID)


class WipReleaseGate(unittest.TestCase):
    def test_free_agent_released(self):
        fake = FakePaperclip([make(50, status="backlog", paths=("a.ts",)),
                              make(51, status="in_review", paths=("b.ts",))])  # in_review does not count
        self.assertIn("SOU-50: released -> todo", release(fake, "SOU-50"))

    def test_busy_agent_blocked_with_active_task_named(self):
        fake = FakePaperclip([make(50, status="backlog", paths=("a.ts",)),
                              make(12, status="in_progress", paths=("b.ts",))])
        out = release(fake, "SOU-50")
        self.assertIn("SOU-50: not released: assignee already has SOU-12 in progress (WIP limit 1", out)
        self.assertEqual(fake.writes, [])

    def test_active_task_in_another_project_blocks(self):
        fake = FakePaperclip([make(50, status="backlog", paths=("a.ts",), project=PA),
                              make(12, status="in_progress", paths=("a.ts",), project=PB)])
        self.assertIn("already has SOU-12 in progress", release(fake, "SOU-50"))
        self.assertEqual(fake.writes, [])

    def test_force_cannot_bypass(self):
        fake = FakePaperclip([make(50, status="backlog", paths=("a.ts",)),
                              make(12, status="in_progress", paths=("b.ts",))])
        out = release(fake, "SOU-50", force=True)
        self.assertIn("--force does not override", out)
        self.assertEqual(fake.writes, [])

    def test_api_failure_is_not_zero_wip(self):
        fake = FakePaperclip([make(50, status="backlog", paths=("a.ts",))], fail_list="in_progress")
        out = release(fake, "SOU-50", force=True)
        self.assertIn("WIP could not be verified", out)
        self.assertEqual(fake.writes, [])

    def test_no_workspace_mutation_when_wip_blocks(self):
        cand = make(50, status="backlog", paths=("a.ts",), ws={"sourceIssueId": "id-9", "name": "SOU-9-x"})
        fake = FakePaperclip([cand, make(12, status="in_progress", paths=("b.ts",))])
        out = release(fake, "SOU-50", force=True)
        self.assertNotIn("detached", out)
        self.assertEqual(fake.writes, [])

    def test_batch_releases_at_most_one_per_agent(self):
        fake = FakePaperclip([make(60, status="backlog", paths=("a.ts",)),
                              make(61, status="backlog", paths=("b.ts",))])
        out = release(fake, "SOU-60", "SOU-61")
        self.assertIn("SOU-60: released", out)
        self.assertIn("SOU-61: not released: assignee already has SOU-60 (released earlier in this command)", out)
        self.assertEqual(fake.writes, [("/issues/id-60", {"status": "todo"})])

    def test_rejected_task_does_not_reserve_the_slot(self):
        clash = make(59, status="in_review", paths=("a.ts",), assignee="ag-9")
        first = make(60, status="backlog", paths=("a.ts",))  # Write Set conflict with SOU-59
        second = make(61, status="backlog", paths=("b.ts",))
        fake = FakePaperclip([clash, first, second])
        out = release(fake, "SOU-60", "SOU-61")
        self.assertIn("SOU-60: not released.", out)
        self.assertIn("SOU-61: released -> todo", out)
        self.assertEqual(fake.writes, [("/issues/id-61", {"status": "todo"})])

    def test_forced_release_reserves_the_slot(self):
        first = make(60, status="backlog", paths=("a.ts",))
        first["executionPolicy"] = {}  # forceable problem
        fake = FakePaperclip([first, make(61, status="backlog", paths=("b.ts",))])
        out = release(fake, "SOU-60", "SOU-61", force=True)
        self.assertIn("SOU-60: released -> todo", out)
        self.assertIn("SOU-61: not released: assignee already has SOU-60", out)

    def test_other_agent_released_in_same_batch(self):
        fake = FakePaperclip([make(60, status="backlog", paths=("a.ts",), assignee="ag-1"),
                              make(61, status="backlog", paths=("b.ts",), assignee="ag-1"),
                              make(62, status="backlog", paths=("c.ts",), assignee="ag-2")])
        out = release(fake, "SOU-60", "SOU-61", "SOU-62")
        self.assertIn("SOU-62: released", out)
        self.assertEqual([w[0] for w in fake.writes], ["/issues/id-60", "/issues/id-62"])

    def test_reserved_task_already_running_is_named_once(self):
        fake = FakePaperclip([make(60, status="backlog", paths=("a.ts",)),
                              make(61, status="backlog", paths=("b.ts",))])
        real_patch = fake.call

        def run_starts_at_once(method, path, body=None):
            res = real_patch(method, path, body)
            if method == "PATCH" and body == {"status": "todo"}:
                fake.issues[path.rsplit("/", 1)[1]]["status"] = "in_progress"
            return res
        fake.call = run_starts_at_once
        out = release(fake, "SOU-60", "SOU-61")
        self.assertIn("SOU-61: not released: assignee already has SOU-60 in progress", out)
        self.assertNotIn("released earlier", out)


class TriageWip(unittest.TestCase):
    def triage(self, fake):
        out = io.StringIO()
        with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "issue", fake.issue), \
                mock.patch.object(pc, "company", return_value={"id": CID, "name": "Soucean"}), \
                mock.patch.object(pc, "names", return_value={"ag-1": "web-engineer", "ag-2": "qa"}), \
                contextlib.redirect_stdout(out):
            pc.cmd_triage(argparse.Namespace(company=None, quiet_hours=1e9))
        text = out.getvalue()
        return text[text.index("\nWIP:"):]

    def test_breach_lists_both_across_projects(self):
        fake = FakePaperclip([make(1, project=PA), make(2, project=PB), make(3, assignee="ag-2")])
        wip = self.triage(fake)
        self.assertIn("web-engineer has 2 in progress (limit 1): SOU-1, SOU-2", wip)
        self.assertNotIn("qa", wip)
        self.assertEqual(wip.count("in progress"), 1)

    def test_single_active_task_is_no_breach(self):
        fake = FakePaperclip([make(1), make(2, status="in_review")])
        self.assertIn("(none)", self.triage(fake))

    def test_failure_is_visible_not_none(self):
        fake = FakePaperclip([make(1), make(2)], fail_list="in_progress")
        wip = self.triage(fake)
        self.assertIn("COULD NOT CHECK WIP", wip)
        self.assertNotIn("(none)", wip)


# ---------- P0.3: only `release` starts a task ----------

def run_cmd(fake, fn, **kw):
    """Run a pc.py command; returns (stdout, GateError/ApiError or None)."""
    out = io.StringIO()
    err = None
    with mock.patch.object(pc, "call", fake.call), mock.patch.object(pc, "issue", fake.issue), \
            contextlib.redirect_stdout(out):
        try:
            fn(argparse.Namespace(company=None, **kw))
        except pc.ApiError as e:
            err = e
    return out.getvalue(), err


def create_args(**kw):
    base = dict(title="New task", assignee="web-engineer", project=None, desc=ws_desc("src/a.ts"), desc_file=None,
                review=["qa-engineer"], no_approval=False, status="backlog")
    base.update(kw)
    return base


class CreateGate(unittest.TestCase):
    def test_payload_is_backlog_and_never_requests_a_workspace(self):
        fake = FakePaperclip([])
        out, err = run_cmd(fake, pc.cmd_create, **create_args())
        self.assertIsNone(err)
        (method, path, body), = fake.writes
        self.assertEqual((method, path), ("POST", f"/companies/{CID}/issues"))
        self.assertEqual(body["status"], "backlog")
        for field in ("parentId", "executionWorkspaceId", "inheritExecutionWorkspaceFromIssueId",
                      "executionWorkspacePreference", "projectWorkspaceId"):
            self.assertNotIn(field, body)
        self.assertIn("not started; run: release SOU-99", out)

    def test_status_todo_refused_before_any_call(self):
        fake = FakePaperclip([])
        _, err = run_cmd(fake, pc.cmd_create, **create_args(status="todo"))
        self.assertIsInstance(err, pc.GateError)
        self.assertIn("release", str(err))
        self.assertEqual(fake.writes, [])

    def test_failed_create_does_nothing_else(self):
        fake = FakePaperclip([], fail_writes=True)
        _, err = run_cmd(fake, pc.cmd_create, **create_args())
        self.assertIsNotNone(err)
        self.assertEqual([w[1] for w in fake.writes], [f"/companies/{CID}/issues"])  # no assign, status or wake


class AssignGate(unittest.TestCase):
    def test_backlog_stays_backlog_without_status_change(self):
        fake = FakePaperclip([make(70, status="backlog", assignee=None)])
        out, err = run_cmd(fake, pc.cmd_assign, key="SOU-70", agent="web-engineer", status=None)
        self.assertIsNone(err)
        self.assertEqual(fake.writes, [("/issues/id-70", {"assigneeAgentId": "ag-1", "assigneeUserId": None})])
        self.assertEqual(fake.issues["id-70"]["status"], "backlog")
        self.assertIn("not started; run: release SOU-70", out)

    def test_status_todo_refused(self):
        fake = FakePaperclip([make(70, status="backlog")])
        _, err = run_cmd(fake, pc.cmd_assign, key="SOU-70", agent="web-engineer", status="todo")
        self.assertIsInstance(err, pc.GateError)
        self.assertIn("release SOU-70", str(err))
        self.assertEqual(fake.writes, [])

    def test_started_issue_refused_without_parking(self):
        for status in ("todo", "in_progress", "in_review", "blocked"):
            fake = FakePaperclip([make(71, status=status, assignee=None)])
            _, err = run_cmd(fake, pc.cmd_assign, key="SOU-71", agent="web-engineer", status=None)
            self.assertIsInstance(err, pc.GateError, status)
            self.assertIn("--status backlog", str(err))
            self.assertEqual(fake.writes, [], status)

    def test_started_issue_parked_to_backlog_then_needs_release(self):
        board_parked = make(72, status="in_review", assignee=None)
        board_parked["assigneeUserId"] = "local-board"
        fake = FakePaperclip([board_parked])
        _, err = run_cmd(fake, pc.cmd_assign, key="SOU-72", agent="web-engineer", status="backlog")
        self.assertIsNone(err)
        self.assertEqual(fake.writes, [("/issues/id-72", {"assigneeAgentId": "ag-1", "assigneeUserId": None,
                                                          "status": "backlog"})])

    def test_closed_issue_assignable(self):
        fake = FakePaperclip([make(73, status="done", assignee=None)])
        _, err = run_cmd(fake, pc.cmd_assign, key="SOU-73", agent="web-engineer", status=None)
        self.assertIsNone(err)
        self.assertNotIn("status", fake.writes[0][1])

    def test_assign_never_releases_or_wakes(self):
        fake = FakePaperclip([make(70, status="backlog", assignee=None)])
        with mock.patch.object(pc, "cmd_release") as rel, mock.patch.object(pc, "wip_guard") as wip:
            run_cmd(fake, pc.cmd_assign, key="SOU-70", agent="web-engineer", status=None)
        rel.assert_not_called()
        wip.assert_not_called()
        self.assertFalse(any("wakeup" in str(w) or w[1].get("status") == "todo" for w in fake.writes))

    def test_api_failure_reported_without_status_change(self):
        fake = FakePaperclip([make(70, status="backlog", assignee=None)], fail_writes=True)
        _, err = run_cmd(fake, pc.cmd_assign, key="SOU-70", agent="web-engineer", status=None)
        self.assertIsNotNone(err)
        self.assertEqual(len(fake.writes), 1)
        self.assertNotIn("status", fake.writes[0][2])
        self.assertEqual(fake.issues["id-70"]["status"], "backlog")


class CommentAndWakeGate(unittest.TestCase):
    def test_comment_refused_on_agent_assigned_backlog(self):
        fake = FakePaperclip([make(80, status="backlog")])
        _, err = run_cmd(fake, pc.cmd_comment, key="SOU-80", text="note")
        self.assertIsInstance(err, pc.GateError)
        self.assertEqual(fake.writes, [])

    def test_comment_allowed_elsewhere(self):
        for issue_ in (make(81, status="backlog", assignee=None), make(82, status="in_progress"),
                       make(83, status="in_review")):
            fake = FakePaperclip([issue_])
            _, err = run_cmd(fake, pc.cmd_comment, key=issue_["identifier"], text="note")
            self.assertIsNone(err, issue_["status"])
            self.assertEqual(fake.writes[0][:2], ("POST", f"/issues/{issue_['id']}/comments"))

    def test_wake_on_backlog_issue_refused(self):
        fake = FakePaperclip([make(84, status="backlog")])
        _, err = run_cmd(fake, pc.cmd_wake, agent="web-engineer", issue="SOU-84", reason="r")
        self.assertIsInstance(err, pc.GateError)
        self.assertEqual(fake.writes, [])

    def test_wake_on_released_issue_allowed(self):
        fake = FakePaperclip([make(85, status="in_review", assignee="ag-2")])
        _, err = run_cmd(fake, pc.cmd_wake, agent="qa-engineer", issue="SOU-85", reason="r")
        self.assertIsNone(err)
        self.assertEqual(fake.writes[0][1], "/agents/ag-2/wakeup?companyId=co-1")


class OnlyReleaseStarts(unittest.TestCase):
    """Every local command that writes, run against a backlog issue: only release moves it out of backlog."""

    def test_no_other_command_moves_backlog_out(self):
        attempts = [
            (pc.cmd_assign, dict(key="SOU-90", agent="web-engineer", status=None)),
            (pc.cmd_assign, dict(key="SOU-90", agent="web-engineer", status="todo")),
            (pc.cmd_assign, dict(key="SOU-90", agent="web-engineer", status="backlog")),
            (pc.cmd_comment, dict(key="SOU-90", text="go")),
            (pc.cmd_wake, dict(agent="web-engineer", issue="SOU-90", reason="r")),
            (pc.cmd_approve, dict(key="SOU-90", comment="ok")),
            (pc.cmd_request_changes, dict(key="SOU-90", comment="fix")),
        ]
        for fn, kw in attempts:
            fake = FakePaperclip([make(90, status="backlog", paths=("a.ts",))])
            run_cmd(fake, fn, **kw)
            self.assertEqual(fake.issues["id-90"]["status"], "backlog", fn.__name__)
            self.assertFalse(any("wakeup" in str(w) or "/comments" in str(w) for w in fake.writes), fn.__name__)
        fake = FakePaperclip([make(90, status="backlog", paths=("a.ts",))])
        self.assertIn("released -> todo", release(fake, "SOU-90"))

    def test_release_still_runs_both_hard_guards(self):
        fake = FakePaperclip([make(91, status="backlog", paths=("a.ts",))])
        with mock.patch.object(pc, "wip_guard", wraps=pc.wip_guard) as wip, \
                mock.patch.object(pc, "write_set_guard", wraps=pc.write_set_guard) as ws:
            release(fake, "SOU-91", force=True)
        wip.assert_called_once()
        ws.assert_called_once()


# ---------- OQ-042 Phase 1: review packager (tests live in test_review_pack.py) ----------
import test_review_pack as _review_pack_tests  # noqa: E402

for _name, _obj in vars(_review_pack_tests).items():
    if isinstance(_obj, type) and issubclass(_obj, unittest.TestCase) and _obj.__module__ == _review_pack_tests.__name__:
        globals()["ReviewPack" + _name] = _obj  # prefixed, so no helper or class here is shadowed
del _name, _obj  # otherwise unittest also collects the last class through _obj


if __name__ == "__main__":
    unittest.main()
