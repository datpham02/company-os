"""Tests for yaml_subset.py, validate-registries.py and check-dependencies.py (Phase 2). Stdlib only, offline.

    python -I -W error scripts/maintenance/test_registry_tools.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yaml_subset  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


vr = load_script("validate-registries")
cd = load_script("check-dependencies")


class YamlSubset(unittest.TestCase):
    def test_supported_shapes(self):
        text = ("# comment\nname: \"A # not a comment\"\ncount: 3\nflag: true\nnothing: ~\nlist: [a, \"b c\", 1]\n"
                "map: { k: v, n: 2 }\nitems:\n  - id: one\n    tags: []\n  - id: two\n    nested:\n      deep: 'x''y'\n"
                "seq:\n- plain\n- 7\npattern: \"^a\\\\.b$\"\n")
        d = yaml_subset.loads(text)
        self.assertEqual(d["name"], "A # not a comment")
        self.assertEqual((d["count"], d["flag"], d["nothing"]), (3, True, None))
        self.assertEqual(d["list"], ["a", "b c", 1])
        self.assertEqual(d["map"], {"k": "v", "n": 2})
        self.assertEqual(d["items"], [{"id": "one", "tags": []}, {"id": "two", "nested": {"deep": "x'y"}}])
        self.assertEqual(d["seq"], ["plain", 7])
        self.assertEqual(d["pattern"], "^a\\.b$")

    def test_refuses_unsupported_or_malformed(self):
        cases = {"block scalar": "a: |\n  text\n", "tab": "a:\n\tb: 1\n", "documents": "a: 1\n---\nb: 2\n",
                 "duplicate key": "a: 1\na: 2\n", "bad indent": "a: 1\n   b: 2\n", "anchor": "a: &x 1\n",
                 "unterminated": "a: \"open\n", "flow": "a: [1, 2\n"}
        for name, text in cases.items():
            with self.subTest(name):
                with self.assertRaises(yaml_subset.YamlError):
                    yaml_subset.loads(text)

    def test_reads_the_real_registries(self):
        for rel in ("knowledge/projects/registry.yaml", "knowledge/projects/project-config.schema.yaml",
                    "dependencies/registry.yaml"):
            with self.subTest(rel):
                self.assertIsInstance(yaml_subset.load(os.path.join(REPO, rel)), dict)


class ValidateRegistries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for rel in ("knowledge/projects/registry.yaml", "knowledge/projects/project-config.schema.yaml",
                    "dependencies/registry.yaml", "config/paperclip/agents.json"):
            os.makedirs(os.path.dirname(os.path.join(self.tmp, rel)), exist_ok=True)
            shutil.copy(os.path.join(REPO, rel), os.path.join(self.tmp, rel))
        for role in ("director", "producer", "project-manager", "qa", "ui-designer"):
            self._role(f"knowledge/company/agents/{role}")
        for role in ("game-designer", "gameplay-programmer"):
            self._role(f"knowledge/departments/game/agents/{role}")
        self._role("knowledge/departments/web/agents/web-engineer")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _role(self, rel):
        os.makedirs(os.path.join(self.tmp, rel), exist_ok=True)
        open(os.path.join(self.tmp, rel, "AGENTS.md"), "w").write("---\n---\n")

    def edit(self, rel, old, new):
        p = os.path.join(self.tmp, rel)
        s = open(p, encoding="utf-8").read()
        self.assertIn(old, s)
        open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))

    def test_real_registries_have_no_findings(self):
        self.assertEqual(vr.check(REPO), [])

    def test_each_error_kind_is_reported(self):
        reg = "knowledge/projects/registry.yaml"
        cases = [
            (reg, "    department: web\n", "    department: marketing\n", "is not one of"),
            (reg, "    frameworkVersion: 0.1.0\n\n  - id: soucean-game", "    frameworkVersion: 0.1.0\n    color: blue\n\n  - id: soucean-game", "unknown property 'color'"),
            (reg, "ui-designer, qa]\n    frameworkVersion: 0.1.0\n", "ui-designer, qa-engineer]\n    frameworkVersion: 0.1.0\n", "agent 'qa-engineer' is not a role Agent ID"),
            (reg, "  - id: soucean-game\n    name: Soucean Game\n", "  - id: soucean-game\n    name: Soucean Game\n    dependencies: [left-pad]\n", "dependency 'left-pad'"),
            (reg, "url: https://github.com/datpham02/soucean-game.git", "url: https://github.com/datpham02/other.git", "differs from agents.json"),
            (reg, "    status: active                # Board", "    status: shipped                # Board", "'shipped' is not one of"),
            ("dependencies/registry.yaml", "usedBy: [ui-designer]\n", "usedBy: [ui-designer, intern]\n", "usedBy 'intern'"),
            ("dependencies/registry.yaml", "  - id: codex\n", "  - id: paperclip\n", "duplicate ids"),
        ]
        for rel, old, new, want in cases:
            with self.subTest(want=want):
                self.tearDown()
                self.setUp()
                self.edit(rel, old, new)
                findings = vr.check(self.tmp)
                self.assertTrue(any(want in f for f in findings), findings)

    def test_missing_required_field(self):
        self.edit("knowledge/projects/registry.yaml", "    frameworkVersion: 0.1.0\n\n  - id: soucean-game",
                  "\n  - id: soucean-game")
        self.assertTrue(any("missing required 'frameworkVersion'" in f for f in vr.check(self.tmp)))

    def test_unreadable_registry_is_a_finding(self):
        os.remove(os.path.join(self.tmp, "dependencies", "registry.yaml"))
        self.assertTrue(vr.check(self.tmp)[0].startswith("cannot read a registry"))


class CheckDependencies(unittest.TestCase):
    DEPS = [{"id": "paperclip", "verifiedVersion": "2026.1023.0 (npx …)"},
            {"id": "claude-code", "verifiedVersion": "2.1.329 (claude --version)"},
            {"id": "codex", "verifiedVersion": "0.166.0"},
            {"id": "github-cli", "verifiedVersion": "not recorded"},
            {"id": "openspec", "verifiedVersion": "1.0.0"}]

    def test_statuses(self):
        outputs = {"paperclipai": "2026.1023.0\n", "claude": "2.1.330 (Claude Code)\n", "codex": None,
                   "gh": "gh version 2.97.0 (2026-01-01)\n"}
        rows = {r[0]: r for r in cd.check(self.DEPS, lambda argv: outputs.get(argv[0]))}
        self.assertEqual(rows["paperclip"][1], "ok")
        self.assertEqual(rows["claude-code"][1:], ("DRIFT", "2.1.329", "2.1.330"))
        self.assertEqual(rows["codex"][1], "not installed")
        self.assertEqual(rows["github-cli"][1], "no version in registry")
        self.assertEqual(rows["openspec"][1], "skipped")

    def test_exit_code(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cd.main(runner=lambda argv: None), 0)  # nothing installed: no drift
            self.assertEqual(cd.main(runner=lambda argv: "99.99.99"), 1)

    def test_runner_never_installs(self):
        self.assertTrue(all(argv[-1] == "--version" for argv in cd.COMMANDS.values()))


if __name__ == "__main__":
    unittest.main()
