"""Tests for the S-1 reporting wrappers and their installer (Issue #113, option R-B). Offline: the wrappers are rendered
against stub Paperclip scripts in a temporary folder; nothing reaches Paperclip.

    python -I -W error scripts/setup/test_report_wrappers.py
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


inst = load("install-report-wrappers")
bp = load("build-package")


def find_bash():
    """Git Bash or a POSIX bash; never the WSL launcher in System32."""
    for cand in (os.environ.get("GIT_BASH"), r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash")):
        if cand and os.path.isfile(cand) and "system32" not in cand.lower():
            return cand
    return None


BASH = find_bash()
STUB = """#!/usr/bin/env bash
out="$STUB_OUT"
{ printf 'ARGS'; for a in "$@"; do printf ' [%s]' "$a"; done; printf '\\n'; } >>"$out"
if [[ ! -t 0 ]]; then printf 'STDIN[%s]\\n' "$(cat)" >>"$out"; fi
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.scripts = os.path.join(self.tmp, "pc-scripts")
        self.bin = os.path.join(self.tmp, "report-bin")
        self.ws = os.path.join(self.tmp, "workspace")
        self.home = os.path.join(self.tmp, "home")
        for d in (self.scripts, self.ws, self.home):
            os.makedirs(d)
        for name in ("paperclip-issue-update.sh", "paperclip-upload-artifact.sh"):
            with open(os.path.join(self.scripts, name), "w", newline="\n") as f:
                f.write(STUB)
        self.out = os.path.join(self.tmp, "stub-out.txt")

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for n in files:
                try:
                    os.chmod(os.path.join(root, n), 0o666)
                except OSError:
                    pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = inst.main(["--paperclip-scripts-dir", self.scripts, "--bin", self.bin, "--workspace", self.ws,
                              *extra])
        return code, out.getvalue()


class Installer(Base):
    def test_render_pins_dir_and_hash(self):
        code, _ = self.install()
        self.assertEqual(code, 0)
        text = open(os.path.join(self.bin, "pc-issue-update"), encoding="utf-8").read()
        self.assertIsNone(re.search(r"@@[A-Z0-9_]+@@", text))
        sha = hashlib.sha256(open(os.path.join(self.scripts, "paperclip-issue-update.sh"), "rb").read()).hexdigest()
        self.assertIn(f"TRUSTED_SHA256='{sha}'", text)
        self.assertIn(f"TRUSTED_DIR='{self.scripts.replace(chr(92), '/')}'", text)
        self.assertEqual(self.install("--check")[0], 0)

    def test_check_detects_changed_wrapper_and_changed_target(self):
        self.install()
        path = os.path.join(self.bin, "pc-issue-update")
        os.chmod(path, 0o666)
        with open(path, "a", newline="\n") as f:
            f.write("# tampered\n")
        code, out = self.install("--check")
        self.assertEqual(code, 1)
        self.assertIn("differs from a fresh render", out)
        self.install()
        with open(os.path.join(self.scripts, "paperclip-upload-artifact.sh"), "a", newline="\n") as f:
            f.write("# upgraded\n")
        self.assertEqual(self.install("--check")[0], 1)

    def test_refuses_unsafe_locations(self):
        for bin_dir, msg in ((os.path.join(self.ws, "bin"), "outside the agents' workspace"),
                             (os.path.join(REPO, "tmp-bin"), "outside this repository"),
                             (os.path.join(self.tmp, "claude-prompt-cache", "k"), "prompt cache"),
                             ("relative-bin", "absolute")):
            with self.subTest(bin=bin_dir), self.assertRaises(SystemExit) as cm:
                inst.main(["--paperclip-scripts-dir", self.scripts, "--bin", bin_dir, "--workspace", self.ws])
            self.assertIn(msg, str(cm.exception))
        with self.assertRaises(SystemExit):
            inst.main(["--paperclip-scripts-dir", os.path.join(self.ws, "s"), "--bin", self.bin, "--workspace", self.ws])

    def test_templates_are_not_runnable_as_committed(self):
        for name in ("pc-issue-update", "pc-upload-artifact"):
            text = open(os.path.join(REPO, "scripts", "report-wrappers", name), encoding="utf-8").read()
            self.assertIn("@@PAPERCLIP_SCRIPTS_DIR@@", text)
            self.assertIn("not installed (template placeholders present)", text)
            for bad in (r"\beval\b", r"\bsh -c\b", r"bash -c\b", r"source\s", r"\$\(\s*\$"):
                self.assertIsNone(re.search(bad, text), (name, bad))


@unittest.skipUnless(BASH, "bash not available")
class Wrappers(Base):
    def setUp(self):
        super().setUp()
        self.install()
        open(os.path.join(self.ws, "probe.png"), "wb").write(b"x")

    def run_w(self, name, args, stdin=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PAPERCLIP_", "CLAUDE"))}
        env.update({"STUB_OUT": self.out.replace("\\", "/"), "HOME": self.home.replace("\\", "/")})
        p = subprocess.run([BASH, os.path.join(self.bin, name).replace("\\", "/"), *args], cwd=self.ws, env=env,
                           input=stdin, capture_output=True, text=True, timeout=60)
        called = open(self.out).read() if os.path.exists(self.out) else ""
        if os.path.exists(self.out):
            os.remove(self.out)
        return p.returncode, p.stderr, called

    def test_issue_update_valid_forms_pass_through(self):
        rc, err, called = self.run_w("pc-issue-update", ["--issue-id", "SOU-12", "--status", "done"], "line 1\n\nline 3\n")
        self.assertEqual(rc, 0, err)
        self.assertIn("ARGS [--issue-id] [SOU-12] [--status] [done]", called)
        self.assertIn("STDIN[line 1\n\nline 3]", called)
        rc, err, called = self.run_w("pc-issue-update", ["--issue-id", "0f8fad5b-d9cb-469f-a165-70867728950e", "--dry-run"], "")
        self.assertEqual(rc, 0, err)
        self.assertIn("[--dry-run]", called)
        rc, _, called = self.run_w("pc-issue-update", ["--help"])
        self.assertEqual((rc, called), (0, ""))
        audit = open(os.path.join(self.home, ".company-os", "report-audit", os.listdir(
            os.path.join(self.home, ".company-os", "report-audit"))[0])).read()
        self.assertIn("pc-issue-update\texit:0\tSOU-12\tdone\t", audit)
        self.assertNotIn("line 1", audit)  # never the comment text

    def test_issue_update_refusals_never_reach_the_target(self):
        cases = (
            ["--issue-id", "../agents/x"], ["--issue-id", "SOU-12/../../agents"], ["--issue-id", "sou-12"],
            ["--issue-id", "SOU-12; curl x"], ["--issue-id", "$(id)"], ["--issue-id", "SOU-1", "--status", "weird"],
            ["--issue-id", "SOU-1", "--comment", "hi"], ["--issue-id", "SOU-1", "--issue-id", "SOU-2"],
            ["--issue-id", "SOU-1", "extra"], ["--issue-id"], ["--status", "done"], ["--issue-id", "SOU-1", "--help"],
            ["-c", "echo pwned"], ["--issue-id", "SOU-1", "--status"],
        )
        for args in cases:
            with self.subTest(args=args):
                rc, err, called = self.run_w("pc-issue-update", args, "x")
                self.assertEqual(rc, 64, err)
                self.assertIn("refused", err)
                self.assertEqual(called, "")

    def test_changed_target_is_refused(self):
        with open(os.path.join(self.scripts, "paperclip-issue-update.sh"), "a", newline="\n") as f:
            f.write("echo injected\n")
        rc, err, called = self.run_w("pc-issue-update", ["--issue-id", "SOU-1"], "x")
        self.assertEqual((rc, called), (70, ""))
        self.assertIn("trusted script changed since install", err)

    def test_upload_valid_and_refused(self):
        rc, err, called = self.run_w("pc-upload-artifact", ["probe.png", "--issue-id", "SOU-3", "--title", "Probe",
                                                            "--content-type", "image/png", "--dry-run"])
        self.assertEqual(rc, 0, err)
        self.assertIn("ARGS [probe.png] [--issue-id] [SOU-3] [--title] [Probe] [--content-type] [image/png] [--dry-run]",
                      called)
        outside = os.path.join(self.tmp, "secret.txt")
        open(outside, "w").write("s")
        os.makedirs(os.path.join(self.ws, "sub"))
        cases = (
            [outside.replace("\\", "/"), "--issue-id", "SOU-3"], ["../secret.txt", "--issue-id", "SOU-3"],
            ["sub/../../secret.txt", "--issue-id", "SOU-3"], ["C:/x.png", "--issue-id", "SOU-3"],
            ["-x", "--issue-id", "SOU-3"], ["missing.png", "--issue-id", "SOU-3"], ["sub", "--issue-id", "SOU-3"],
            ["probe.png"], ["probe.png", "--issue-id", "SOU-3", "--company-id", "c"],
            ["probe.png", "--issue-id", "SOU-3", "--chat-comment", "hi"],
            ["probe.png", "--issue-id", "SOU-3", "--retry-unknown-upload"],
            ["probe.png", "--issue-id", "SOU-3", "--status", "approved"],
            ["probe.png", "--issue-id", "SOU-3", "--content-type", "text/html; x"],
            ["probe.png", "--issue-id", "SOU-3", "--output", "yaml"],
            ["probe.png", "--issue-id", "SOU-3", "--title", "--dry-run"],
            ["probe.png", "--issue-id", "../x"],
        )
        for args in cases:
            with self.subTest(args=args):
                rc, err, called = self.run_w("pc-upload-artifact", args)
                self.assertEqual(rc, 64, (args, err))
                self.assertEqual(called, "")

    def test_upload_refuses_a_link_out_of_the_workspace(self):
        link = os.path.join(self.ws, "link.png")
        try:
            os.symlink(os.path.join(self.tmp, "home"), link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted for this user")
        rc, _, called = self.run_w("pc-upload-artifact", ["link.png", "--issue-id", "SOU-3"])
        self.assertEqual((rc, called), (64, ""))


class BuiltRules(unittest.TestCase):
    def built(self, report_bin):
        conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
        out = {}
        for slug, ag in conf["agents"].items():
            prof = conf["profiles"][ag["profile"]]
            if prof["adapter"] == "claude_local" and not bp.is_strict_reviewer(prof):
                out[slug] = bp.adapter_block(prof, ag, conf["rules"], "SOU", "C:/ws", "agent",
                                             report_bin=report_bin)["config"]["extraArgs"]
        return out

    def test_wildcards_replaced_by_wrapper_rules(self):
        built = self.built("C:/Users/u/.company-os/report-bin")
        self.assertGreaterEqual(len(built), 7)
        for slug, args in built.items():
            allow = args[args.index("--allowedTools") + 1:args.index("--disallowedTools")]
            with self.subTest(agent=slug):
                self.assertFalse(any("*paperclip-" in a for a in allow), allow)
                self.assertIn('Bash(bash "C:/Users/u/.company-os/report-bin/pc-issue-update" --issue-id *)', allow)
                self.assertIn('Bash(bash "C:\\Users\\u\\.company-os\\report-bin\\pc-issue-update" --issue-id *)', allow)
                self.assertIn('Bash(bash "C:/Users/u/.company-os/report-bin/pc-upload-artifact" *)', allow)
                self.assertFalse(any("\\*" in a for a in allow), "a backslash before * escapes the wildcard")
                self.assertFalse(any("{REPORT_BIN}" in a for a in args))
                prompt = args[args.index("--append-system-prompt") + 1]
                self.assertIn('bash "C:/Users/u/.company-os/report-bin/pc-issue-update" --issue-id', prompt)
                self.assertIn("Do not call paperclip-issue-update.sh", prompt)

    def test_report_bin_is_a_build_input(self):
        self.assertNotEqual(self.built("C:/a/report-bin"), self.built("C:/b/report-bin"))
        self.assertEqual(bp.default_report_bin(), os.path.join(os.path.expanduser("~"), ".company-os", "report-bin"))


if __name__ == "__main__":
    unittest.main()
