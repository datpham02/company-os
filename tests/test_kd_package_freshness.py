"""Regression gate: committed Knowledge Delivery packages must be fresh against HEAD (ADR-024).

A package goes stale when a source section it delivers (for example rules.md R2 or
task-contract §2) changes after the pinned source commit. That happened between
616f6d1 and 1b28789 (Issue #113, Phase C C0) and was caught only by
scripts/setup/test_check_agent_drift.py, which is outside this suite.

This test uses --freshness, which compares each unit's recorded section hash with
the git blob at HEAD. It does not depend on working-tree line endings, so it also
passes on a Windows checkout with core.autocrlf=true (where --check reports false
"stale" results). Stdlib only; needs git and the pinned commit in the local clone.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts/setup/gen-role-packages.py"
MANIFEST = ROOT / "config/paperclip/knowledge-manifest.json"


def run(*args):
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(GEN), "--repo", str(ROOT), *args],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)


class KnowledgePackageFreshness(unittest.TestCase):
    def roles(self):
        return sorted(json.loads(MANIFEST.read_text(encoding="utf-8"))["roles"])

    def pinned(self, role):
        pkg = ROOT / "config/paperclip/generated" / role / "package.json"
        self.assertTrue(pkg.is_file(), f"{role}: no committed package.json")
        return json.loads(pkg.read_text(encoding="utf-8"))["source_commit"]

    def test_pinned_commit_is_available(self):
        for role in self.roles():
            commit = self.pinned(role)
            r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0,
                             f"{role}: pinned source commit {commit} is not in this clone; "
                             "a squash or rebase merge of the generating PR orphans it")

    def test_packages_are_fresh_against_head(self):
        for role in self.roles():
            commit = self.pinned(role)
            r = run("--freshness", "--commit", commit, "--against", "HEAD", "--role", role)
            self.assertEqual(r.returncode, 0,
                             f"{role}: committed package is stale against HEAD. Regenerate with "
                             f"gen-role-packages.py --commit <commit> in an LF checkout.\n{r.stdout}\n{r.stderr}")
            self.assertIn("fresh:", r.stdout)


if __name__ == "__main__":
    unittest.main()
