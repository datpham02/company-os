"""Tests for build-package.py's Review Package reviewer (Phase 6 W2). Stdlib only; builds into temporary folders.

    python -I scripts/setup/test_build_package.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(HERE, "build-package.py")


def build(*extra):
    out = tempfile.mkdtemp()
    shutil.rmtree(out)
    p = subprocess.run([sys.executable, "-I", SCRIPT, "--prefix", "SOU", "--out", out, *extra], cwd=REPO,
                       capture_output=True, text=True)
    return p, out


def agent_block(yaml_text, slug):
    m = re.search(rf"^  {re.escape(slug)}:\n(.*?)(?=^  [a-z-]+:\n|^[a-z]+:)", yaml_text, re.S | re.M)
    return m.group(1) if m else None


class ReviewerPackage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.staging = os.path.join(self.tmp, "staging")
        self.cwd = os.path.join(self.tmp, "cwd")
        os.makedirs(self.staging)
        os.makedirs(self.cwd)
        self.outs = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for o in self.outs:
            shutil.rmtree(o, ignore_errors=True)

    def run_build(self, *extra):
        p, out = build(*extra)
        self.outs.append(out)
        return p, out

    def test_reviewer_left_out_by_default(self):
        p, out = self.run_build()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, "agents", "code-reviewer")))
        with open(os.path.join(out, ".paperclip.yaml"), encoding="utf-8") as f:
            self.assertIsNone(agent_block(f.read(), "code-reviewer"))

    def test_reviewer_built_strict_and_checked(self):
        p, out = self.run_build("--with-reviewer", "--staging-root", self.staging, "--reviewer-cwd", self.cwd)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(os.path.join(out, ".paperclip.yaml"), encoding="utf-8") as f:
            block = agent_block(f.read(), "code-reviewer")
        self.assertIsNotNone(block)
        for needle in ('"--restricted"', '"Read,Grep,Glob"', '"--strict-mcp-config"', '"--no-session-persistence"',
                       '"dontAsk"', '"mcp__*"', "enabled: false", "maxConcurrentRuns: 1"):
            self.assertIn(needle, block)
        self.assertEqual(block.count('"--add-dir"'), 1)
        self.assertNotIn("env:", block)
        self.assertNotIn("inputs:", block)
        self.assertNotIn("--allowedTools", block)

    def test_reviewer_needs_both_paths(self):
        p, _ = self.run_build("--with-reviewer", "--staging-root", self.staging)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("needs --staging-root and --reviewer-cwd", p.stderr)

    def test_reviewer_paths_outside_repository_and_each_other(self):
        cases = ((["--staging-root", os.path.join(REPO, "x"), "--reviewer-cwd", self.cwd], "outside this repository"),
                 (["--staging-root", self.staging, "--reviewer-cwd", os.path.join(self.staging, "cwd")],
                  "must not contain each other"),
                 (["--staging-root", "relative/staging", "--reviewer-cwd", self.cwd], "absolute path"))
        for args, want in cases:
            with self.subTest(want=want):
                p, _ = self.run_build("--with-reviewer", *args)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(want, p.stderr)

    def test_unsafe_built_configuration_is_refused_not_corrected(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_package", SCRIPT)
        bp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bp)
        conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
        prof = conf["profiles"]["claude-reviewer-strict"]
        good = {"adapter": bp.adapter_block(prof, {}, {}, "SOU", self.tmp, None, self.staging, self.cwd),
                "runtime": {"heartbeat": {"enabled": False, "maxConcurrentRuns": 1}}}
        bp.check_reviewer_block(good, self.staging)  # passes
        bad_args = dict(good, adapter=dict(good["adapter"], config=dict(
            good["adapter"]["config"], extraArgs=good["adapter"]["config"]["extraArgs"] + ["--allowedTools", "Bash"])))
        bad_runtime = dict(good, runtime={"heartbeat": {"enabled": True, "maxConcurrentRuns": 1}})
        bad_env = dict(good, adapter=dict(good["adapter"], config=dict(good["adapter"]["config"], env={"X": "1"})))
        for block in (bad_args, bad_runtime, bad_env):
            with self.subTest(block=str(block)[-80:]):
                with self.assertRaises(SystemExit) as cm:
                    bp.check_reviewer_block(block, self.staging)
                self.assertIn("refused", str(cm.exception))
        self.assertNotIn("--allowedTools", good["adapter"]["config"]["extraArgs"])  # nothing was rewritten

    def test_agent_model_and_effort_reach_the_adapter_config(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_package", SCRIPT)
        bp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bp)
        conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
        profiles, agents = conf["profiles"], conf["agents"]
        director = bp.adapter_block(profiles["claude-read-only"], agents["director"], conf["rules"], "SOU", "C:/ws",
                                    "agent")["config"]
        self.assertEqual((director["model"], director["effort"]), ("claude-fable-5-1", "high"))
        gp = bp.adapter_block(profiles["claude-workspace-write"], agents["gameplay-programmer"], conf["rules"], "SOU",
                              "C:/ws", "agent")["config"]
        self.assertEqual((gp["model"], gp["effort"]), ("claude-fable-5-1", "high"))
        we = bp.adapter_block(profiles["cursor-workspace-write"], agents["web-engineer"], conf["rules"], "SOU",
                              "C:/ws", "agent")["config"]
        self.assertEqual(we["model"], "gpt-5.3-codex-high")
        self.assertNotIn("effort", we)
        with self.assertRaises(SystemExit) as cm:
            bp.model_fields(profiles["cursor-workspace-write"], {"model": "composer-2.5", "effort": "medium"})
        self.assertIn("only supported for claude_local", str(cm.exception))

    def test_outward_tools_denied_for_every_claude_agent(self):
        """T-1 (Issue #113): account, desktop and scheduling tools are denied by bare name in the built arguments."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_package", SCRIPT)
        bp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bp)
        conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
        outward = {"Artifact", "ArtifactComments", "ArtifactData", "CronCreate", "CronDelete", "CronList",
                   "DesignSync", "EnterWorktree", "ExitWorktree", "ListAgents", "PublishPlugin", "PushNotification",
                   "RemoteTrigger", "ScheduleWakeup", "SendMessage", "ShareOnboardingGuide", "Workflow"}
        checked = 0
        for slug, ag in conf["agents"].items():
            prof = conf["profiles"][ag["profile"]]
            if prof["adapter"] != "claude_local" or bp.is_strict_reviewer(prof):
                continue
            args = bp.adapter_block(prof, ag, conf["rules"], "SOU", "C:/ws", "agent")["config"]["extraArgs"]
            allow = args[args.index("--allowedTools") + 1:args.index("--disallowedTools")]
            deny = args[args.index("--disallowedTools") + 1:args.index("--append-system-prompt")]
            with self.subTest(agent=slug):
                self.assertEqual(outward - set(deny), set())
                self.assertEqual(outward & set(allow), set())
            checked += 1
        self.assertGreaterEqual(checked, 7)

    def test_settings_file_is_the_strict_one(self):
        with open(os.path.join(REPO, "config", "paperclip", "reviewer-settings.json"), encoding="utf-8") as f:
            perms = json.load(f)["permissions"]
        self.assertEqual(sorted(perms["allow"]), ["Glob", "Grep", "Read"])
        self.assertTrue({"Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch",
                         "mcp__*"} <= set(perms["deny"]))
        self.assertEqual(perms["defaultMode"], "dontAsk")


if __name__ == "__main__":
    unittest.main()
