"""Tests for the Phase 3 GitHub source (review_github.py) with an in-memory fake GitHub. No network, no token.
Run: python -I -W error test_review_github.py   (also collected by test_pc.py)"""
import argparse
import base64
import datetime
import json
import os
import sys
import tempfile
import unittest
import urllib.parse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import review_github as gh  # noqa: E402
import review_pack as rp  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 21, 12, 0, 0, tzinfo=UTC)
TOKEN = "github_pat_TESTTOKEN0123456789abcdefABCDEF_xyz"
REPO = "acme/demo"
BASE, HEAD, MB = "1" * 40, "2" * 40, "3" * 40


def bsha(text):
    return rp.git_blob_sha1(text.encode("utf-8"))


class FakeGitHub:
    """Serves the five endpoints of design §4 option A from a small model of trees and blobs."""

    def __init__(self, base_files, head_files, changes, page_size=100):
        self.blobs = {}
        self.trees = {MB: self._tree(base_files), HEAD: self._tree(head_files)}
        self.changes = changes  # list of GitHub file entries
        self.page_size = page_size
        self.head_reads = [HEAD]  # successive heads returned by GET pulls/{n}
        self.overrides = {}  # path -> (status, headers, body)
        self.seen_auth = set()
        self.calls = []
        self.headers = {}

    def _tree(self, files):
        entries = []
        for path, text in files.items():
            if text is None:  # submodule
                entries.append({"path": path, "mode": "160000", "type": "commit", "sha": "9" * 40})
                continue
            sha = bsha(text)
            self.blobs[sha] = text.encode("utf-8")
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
        return {"sha": "t" * 40, "tree": entries, "truncated": False}

    def __call__(self, method, url, headers):
        self.seen_auth.add(headers.get("Authorization"))
        u = urllib.parse.urlparse(url)
        path, q = u.path, dict(urllib.parse.parse_qsl(u.query))
        self.calls.append(path + ("?" + u.query if u.query else ""))
        if path in self.overrides:
            return self.overrides[path]
        ok = lambda obj: (200, dict(self.headers), json.dumps(obj).encode())  # noqa: E731
        if path == f"/repos/{REPO}/pulls/41":
            head = self.head_reads.pop(0) if len(self.head_reads) > 1 else self.head_reads[0]
            return ok({"state": "open", "html_url": "https://example.invalid/pr/41", "changed_files": len(self.changes),
                       "head": {"sha": head}, "base": {"sha": BASE}})
        if path == f"/repos/{REPO}/compare/{BASE}...{HEAD}":
            return ok({"merge_base_commit": {"sha": MB}})
        if path == f"/repos/{REPO}/pulls/41/files":
            page = int(q.get("page", "1"))
            size = int(q.get("per_page", "30"))
            assert size == 100
            chunk = self.changes[(page - 1) * self.page_size: page * self.page_size]
            return ok(chunk)
        for sha, tree in self.trees.items():
            if path == f"/repos/{REPO}/git/trees/{sha}":
                return ok(tree)
        if path.startswith(f"/repos/{REPO}/git/blobs/"):
            sha = path.rsplit("/", 1)[1]
            if sha not in self.blobs:
                return 404, {}, b'{"message":"Not Found"}'
            return ok({"sha": sha, "encoding": "base64", "content": base64.b64encode(self.blobs[sha]).decode()})
        return 404, {}, b'{"message":"Not Found"}'


BASE_FILES = {"src/Calc.cs": "int Sub(int a,int b)=>a-b;\n", "src/Old.cs": "class Old {}\n",
              "src/Gone.cs": "class Gone {}\n", "docs/notes.md": "notes\n"}
HEAD_FILES = {"src/Calc.cs": "int Sub(int a,int b)=>b-a;\n", "src/New.cs": "class New {}\n",
              "src/Renamed.cs": "class Old {}\n", "docs/notes.md": "notes\n"}


def changes():
    return [
        {"filename": "src/Calc.cs", "status": "modified", "sha": bsha(HEAD_FILES["src/Calc.cs"])},
        {"filename": "src/New.cs", "status": "added", "sha": bsha(HEAD_FILES["src/New.cs"])},
        {"filename": "src/Renamed.cs", "status": "renamed", "previous_filename": "src/Old.cs",
         "sha": bsha(HEAD_FILES["src/Renamed.cs"])},
        {"filename": "src/Gone.cs", "status": "removed", "sha": "0" * 40},
    ]


ISSUE = {"key": "SOU-41", "id": "uuid-41", "project": "proj-1"}
TASK = {"goal": "Fix subtraction", "acceptanceCriteria": ["Sub(5,3)==2"], "writeSet": ["src/Calc.cs"],
        "readSet": ["docs/notes.md"]}


def fetch(fake, task=None):
    client = gh.GitHubClient(TOKEN, transport=fake, now=NOW)
    return client, gh.fetch_source(client, REPO, 41, ISSUE, task or TASK, rp.SOURCE_SCHEMA)


class Source(unittest.TestCase):
    def test_builds_fixture_shaped_source(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        _, src = fetch(fake)
        self.assertEqual(src["source"], "github-api")
        self.assertEqual((src["baseSha"], src["headSha"], src["mergeBaseSha"], src["headShaAfterBuild"]),
                         (BASE, HEAD, MB, HEAD))
        by = {f["path"]: f for f in src["files"]}
        self.assertEqual(by["src/Calc.cs"]["status"], "M")
        self.assertEqual(base64.b64decode(by["src/Calc.cs"]["base"]["contentBase64"]), b"int Sub(int a,int b)=>a-b;\n")
        self.assertEqual(by["src/Renamed.cs"]["oldPath"], "src/Old.cs")
        self.assertNotIn("head", by["src/Gone.cs"])
        self.assertNotIn("base", by["src/New.cs"])
        self.assertEqual([c["path"] for c in src["context"]], ["docs/notes.md"])
        self.assertEqual(fake.seen_auth, {f"Bearer {TOKEN}"})

    def test_base_content_comes_from_the_merge_base_not_the_base_tip(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fetch(fake)
        self.assertIn(f"/repos/{REPO}/git/trees/{MB}?recursive=1", fake.calls)
        self.assertNotIn(f"/repos/{REPO}/git/trees/{BASE}?recursive=1", fake.calls)

    def test_reads_every_page_until_empty(self):
        many_head = {f"src/F{i}.cs": f"class F{i} {{}}\n" for i in range(5)}
        ch = [{"filename": p, "status": "added", "sha": bsha(t)} for p, t in many_head.items()]
        fake = FakeGitHub({}, many_head, ch, page_size=2)  # pages of 2, 2, 1, then empty
        _, src = fetch(fake, dict(TASK, readSet=[]))
        self.assertEqual(len(src["files"]), 5)
        pages = [c for c in fake.calls if "/pulls/41/files" in c]
        self.assertEqual(len(pages), 4)

    def test_incomplete_file_list_refused(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        orig = fake.__call__

        def short(method, url, headers):
            status, h, body = orig(method, url, headers)
            if "/pulls/41" in url and "/files" not in url:
                d = json.loads(body); d["changed_files"] = 5; body = json.dumps(d).encode()
            return status, h, body
        with self.assertRaisesRegex(gh.GitHubSourceError, "reports 5 changed files but 4"):
            gh.fetch_source(gh.GitHubClient(TOKEN, transport=short), REPO, 41, ISSUE, TASK, rp.SOURCE_SCHEMA)

    def test_head_moved_is_recorded_and_refused_by_the_packager(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.head_reads = [HEAD, "4" * 40]
        _, src = fetch(fake)
        self.assertEqual(src["headShaAfterBuild"], "4" * 40)
        with tempfile.TemporaryDirectory() as d:
            rr, sr = rp.resolve_roots(os.path.join(d, "r"), os.path.join(d, "s"))
            st = {"issues": {"SOU-41": {"status": "in_review", "project": "proj-1", "closedAt": None}}, "runs": []}
            with self.assertRaisesRegex(rp.ReviewPackError, "moved"):
                rp.build(rr, sr, src, "SOU-41", st, [REPO], NOW)

    def test_file_list_sha_differing_from_head_tree_refused(self):
        ch = changes(); ch[0]["sha"] = "5" * 40
        with self.assertRaisesRegex(gh.GitHubSourceError, "differs from the head tree"):
            fetch(FakeGitHub(BASE_FILES, HEAD_FILES, ch))

    def test_missing_blob_content_refused(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        sha = bsha(HEAD_FILES["src/Calc.cs"])
        fake.overrides[f"/repos/{REPO}/git/blobs/{sha}"] = (200, {}, json.dumps(
            {"sha": sha, "encoding": "none", "content": ""}).encode())
        with self.assertRaisesRegex(gh.GitHubSourceError, "did not return the blob content"):
            fetch(fake)

    def test_tampered_blob_refused_by_the_packager_sha_check(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        sha = bsha(HEAD_FILES["src/Calc.cs"])
        fake.blobs[sha] = b"tampered\n"
        _, src = fetch(fake)
        with tempfile.TemporaryDirectory() as d:
            rr, sr = rp.resolve_roots(os.path.join(d, "r"), os.path.join(d, "s"))
            st = {"issues": {"SOU-41": {"status": "in_review", "project": "proj-1", "closedAt": None}}, "runs": []}
            with self.assertRaisesRegex(rp.ReviewPackError, "does not match its blob sha"):
                rp.build(rr, sr, src, "SOU-41", st, [REPO], NOW)

    def test_truncated_tree_refused(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.trees[HEAD]["truncated"] = True
        with self.assertRaisesRegex(gh.GitHubSourceError, "truncated"):
            fetch(fake)

    def test_submodule_refused(self):
        head = dict(HEAD_FILES, **{"lib/sub": None})
        ch = changes() + [{"filename": "lib/sub", "status": "added", "sha": "9" * 40}]
        with self.assertRaisesRegex(gh.GitHubSourceError, "submodule"):
            fetch(FakeGitHub(BASE_FILES, head, ch))

    def test_unknown_status_refused(self):
        ch = changes(); ch[0]["status"] = "unchanged"
        with self.assertRaisesRegex(gh.GitHubSourceError, "not supported"):
            fetch(FakeGitHub(BASE_FILES, HEAD_FILES, ch))

    def test_read_set_file_missing_refused(self):
        with self.assertRaisesRegex(gh.GitHubSourceError, "read-set file"):
            fetch(FakeGitHub(BASE_FILES, HEAD_FILES, changes()), dict(TASK, readSet=["nope.txt"]))

    def test_too_many_pages_refused(self):
        many = {f"f{i}.txt": f"{i}\n" for i in range(4)}
        ch = [{"filename": p, "status": "added", "sha": bsha(t)} for p, t in many.items()]
        fake = FakeGitHub({}, many, ch, page_size=1)
        old = gh.MAX_PAGES
        gh.MAX_PAGES = 2
        try:
            with self.assertRaisesRegex(gh.GitHubSourceError, "more than 2 pages"):
                fetch(fake, dict(TASK, readSet=[]))
        finally:
            gh.MAX_PAGES = old


class TokenHandling(unittest.TestCase):
    def test_401_and_403_refuse_without_fallback(self):
        for code in (401, 403):
            fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
            fake.overrides[f"/repos/{REPO}/pulls/41"] = (code, {}, b'{"message":"Bad credentials"}')
            with self.assertRaisesRegex(gh.GitHubSourceError, "token invalid, revoked"):
                fetch(fake)
            self.assertEqual(len(fake.calls), 1)

    def test_rate_limit_has_its_own_message(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.overrides[f"/repos/{REPO}/pulls/41"] = (403, {"x-ratelimit-remaining": "0"}, b"{}")
        with self.assertRaisesRegex(gh.GitHubSourceError, "rate limit"):
            fetch(fake)

    def test_token_never_appears_in_errors(self):
        def leaky(method, url, headers):
            raise OSError(f"connection reset while sending {headers['Authorization']}")
        with self.assertRaises(gh.GitHubSourceError) as cm:
            gh.GitHubClient(TOKEN, transport=leaky).get("/x")
        self.assertNotIn(TOKEN, str(cm.exception))
        self.assertIn("<token>", str(cm.exception))

    def test_redact_catches_token_shapes(self):
        self.assertEqual(gh.redact("a ghp_abcDEF123 b github_pat_X_y1 c"), "a <token> b <token> c")

    def test_expiry_warning_under_14_days(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.headers = {"github-authentication-token-expiration": "2026-11-30 00:00:00 UTC"}
        client, _ = fetch(fake)
        self.assertEqual(len(client.warnings), 1)
        self.assertIn("expires in 8 days", client.warnings[0])  # 8.5 days from NOW, shown whole
        self.assertNotIn(TOKEN, client.warnings[0])

    def test_no_warning_when_far_from_expiry(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.headers = {"github-authentication-token-expiration": "2027-02-01 00:00:00 UTC"}
        client, _ = fetch(fake)
        self.assertEqual(client.warnings, [])

    def test_empty_token_refused(self):
        with self.assertRaises(gh.GitHubSourceError):
            gh.GitHubClient("")


class PackagerIntegration(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        d = self._tmp.name
        self.rr, self.sr = rp.resolve_roots(os.path.join(d, "r"), os.path.join(d, "s"))
        self.task_file = os.path.join(d, "task.json")
        with open(self.task_file, "w") as f:
            json.dump({"schema": rp.TASK_SCHEMA, "issue": ISSUE, "task": TASK}, f)
        self.state = {"issues": {"SOU-41": {"status": "in_review", "project": "proj-1", "closedAt": None}}, "runs": []}

    def tearDown(self):
        self._tmp.cleanup()

    def args(self, **kw):
        base = dict(github_pr=41, github_repo=REPO, task_file=self.task_file, allow_repo=[REPO], source_fixture=None)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_end_to_end_package_records_github_source(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        src = rp.load_github_source(self.args(), "SOU-41", token=TOKEN, transport=fake, now=NOW)
        pkg, how = rp.build(self.rr, self.sr, src, "SOU-41", self.state, [REPO], NOW)
        self.assertEqual(how, "built")
        with open(os.path.join(pkg, "manifest.json"), encoding="utf-8") as f:
            man = json.load(f)
        self.assertEqual(man["source"], "github-api")
        self.assertEqual(man["headSha"], HEAD)
        with open(os.path.join(pkg, "files", "head", "src", "Calc.cs"), encoding="utf-8") as f:
            self.assertEqual(f.read(), HEAD_FILES["src/Calc.cs"])
        with open(os.path.join(pkg, "REVIEW.md"), encoding="utf-8") as f:
            blob = json.dumps(man) + f.read()
        self.assertNotIn(TOKEN, blob)

    def test_repo_must_be_allowed(self):
        with self.assertRaisesRegex(rp.ReviewPackError, "not in the allowed list"):
            rp.load_github_source(self.args(allow_repo=["other/repo"]), "SOU-41", token=TOKEN,
                                  transport=FakeGitHub(BASE_FILES, HEAD_FILES, changes()))

    def test_task_file_must_match_the_key(self):
        with self.assertRaisesRegex(rp.ReviewPackError, "task file is for"):
            rp.load_github_source(self.args(), "SOU-99", token=TOKEN,
                                  transport=FakeGitHub(BASE_FILES, HEAD_FILES, changes()))

    def test_github_errors_become_redacted_refusals(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        fake.overrides[f"/repos/{REPO}/pulls/41"] = (401, {}, b"{}")
        with self.assertRaises(rp.ReviewPackError) as cm:
            rp.load_github_source(self.args(), "SOU-41", token=TOKEN, transport=fake)
        self.assertNotIn(TOKEN, str(cm.exception))

    def test_unknown_source_kind_refused(self):
        fake = FakeGitHub(BASE_FILES, HEAD_FILES, changes())
        src = rp.load_github_source(self.args(), "SOU-41", token=TOKEN, transport=fake, now=NOW)
        src["source"] = "worktree"
        with self.assertRaisesRegex(rp.ReviewPackError, "is not one of"):
            rp.build(self.rr, self.sr, src, "SOU-41", self.state, [REPO], NOW)


if __name__ == "__main__":
    unittest.main()
