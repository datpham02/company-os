"""Tests for post-import.py (Phase 6 W2): --resume never resumes the Review Package reviewer. Offline: call() is
replaced by a fake, so nothing reaches Paperclip.

    python -I scripts/setup/test_post_import.py
"""
import contextlib
import importlib.util
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    spec = importlib.util.spec_from_file_location("post_import", os.path.join(HERE, "post-import.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Resume(unittest.TestCase):
    def test_resume_leaves_the_reviewer_paused(self):
        m = load()
        keys = {"a1": "code-reviewer", "a2": "director"}
        posts = []

        def call(method, path, body=None):
            if method == "POST":
                posts.append(path)
                return {}
            if path == "/companies":
                return [{"id": "c1", "name": "Soucean", "issuePrefix": "SOU", "status": "active"}]
            if path == "/companies/c1/agents":
                return [{"id": i, "urlKey": k} for i, k in keys.items()]
            if path.startswith("/agents/"):
                i = path.split("/")[2]
                return {"id": i, "urlKey": keys[i], "status": "paused", "adapterType": "claude_local",
                        "adapterConfig": {}}
            return []
        m.call = call
        argv, sys.argv = sys.argv, ["post-import.py", "--company", "SOU", "--resume"]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                m.main()
        finally:
            sys.argv = argv
        self.assertEqual(posts, ["/agents/a2/resume"])
        self.assertIn("code-reviewer: left paused", out.getvalue())


if __name__ == "__main__":
    unittest.main()
