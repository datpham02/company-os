"""Tests for gen-capability-catalog.py (ADR-024). Offline.

    python -I -W error scripts/setup/test_gen_capability_catalog.py
"""
import copy
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


gcc = load("gen-capability-catalog")
grp = gcc.grp
CAT_JSON = f"{gcc.OUT}/capability-catalog.json"


class Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        commit = json.loads(grp.read_text(os.path.join(REPO, CAT_JSON)))["source_commit"]
        cls.src = grp.Source(REPO, commit)
        cls.sources, cls.ssha, cls.origin = gcc.load_sources(cls.src, REPO)
        cls.files = gcc.generate(cls.src, cls.sources, cls.ssha, cls.origin)
        cls.cat = json.loads(cls.files[CAT_JSON])
        cls.agents = json.loads(cls.src.read("config/paperclip/agents.json"))

    def test_deterministic_and_committed(self):
        again = gcc.generate(grp.Source(REPO, self.src.commit), self.sources, self.ssha, self.origin)
        self.assertEqual(again, self.files)
        for rel, text in self.files.items():
            self.assertEqual(grp.read_text(os.path.join(REPO, rel), newline="").replace("\r\n", "\n"), text,
                             f"{rel} is stale: run gen-capability-catalog.py")

    def test_catalog_never_grants_permission(self):
        """'allowed' only with an exact allow rule that build-package.py really builds for that role; never from a
        registry entry or a declaration."""
        n = 0
        for role, r in self.cat["roles"].items():
            allow, deny = grp.role_rules(self.agents, role)
            for row in r["operations"]:
                p = row["permitted"]
                if p["value"].startswith("declared match"):
                    n += 1
                    self.assertTrue(p.get("rule"), (role, row["operation"]))
                    self.assertIn(p["rule"], allow, (role, row["operation"]))
                    self.assertTrue(grp.bash_match(p["rule"], row["sample"]))
                    self.assertFalse(any(grp.bash_match(d, row["sample"]) for d in deny))
                    self.assertIn("config/paperclip/agents.json", p["source"])
                else:
                    self.assertNotIn("allowed", p["value"].replace("not allowed", ""), (role, row["operation"]))
        self.assertGreater(n, 20)

    def test_not_a_grant_statement_everywhere(self):
        for rel, text in self.files.items():
            if rel.endswith(".md"):
                self.assertIn("A catalog entry is not a permission grant", text, rel)
        self.assertIn("not a permission grant", self.cat["not_a_grant"])

    def test_cursor_roles_paused_and_not_enforced(self):
        for role in ("gameplay-programmer", "web-engineer"):
            r = self.cat["roles"][role]
            self.assertTrue(r["status"].startswith("paused"), r["status"])
            self.assertIn("security gate", r["status"])
            for row in r["operations"]:
                self.assertEqual(row["permitted"]["value"], "not enforced (Cursor sandbox disabled)")
                self.assertIsNone(row["permitted"]["rule"])

    def test_sec01_cat_note_is_corrected(self):
        for role in ("director", "producer", "project-manager"):
            row = next(x for x in self.cat["roles"][role]["operations"] if x["operation"] == "write-file-via-shell")
            self.assertEqual(row["permitted"]["note"],
                             "SEC-01: redirect writes are expected to be denied in -p default mode; untested")
        self.assertNotIn("qa-engineer run wrote a file", self.files[f"{gcc.OUT}/capability-catalog.md"])

    def test_rnd_only_tools_listed_only_as_not_available(self):
        labels = {i["label"]: i for i in self.cat["rnd_only"]}
        for name in ("SAM 3.1 (segmentation)", "ViTPose base (pose)", "Krita (paint-over)"):
            self.assertEqual(labels[name]["availability"], "not available")
        ops = {o["id"] for o in self.sources["operations"]}
        self.assertFalse(ops & {"sam3", "vitpose", "krita", "toonout"})

    def test_rnd_tool_reachable_by_allow_rule_fails(self):
        agents = copy.deepcopy(self.agents)
        agents["agents"]["game-artist"]["extraAllowedTools"].append("Bash(python ~/tools/vitpose_infer.py *)")
        src = grp.DictSource({**{p: self.src.read(p) for p in ("dependencies/registry.yaml",)},
                              "config/paperclip/agents.json": json.dumps(agents)}, self.src.commit)
        src.paths |= self.src.paths
        orig_read = src.read
        src.read = lambda p: orig_read(p) if p in src.files else self.src.read(p)
        with self.assertRaisesRegex(gcc.GenError, "R&D-only item ViTPose base \\(pose\\) is reachable"):
            gcc.build(src, self.sources, self.ssha, self.origin)

    def test_unverified_citation_fails(self):
        bad = copy.deepcopy(self.sources)
        bad["cites"]["merge_board"] = {"file": "docs/architecture/security-architecture.md", "quote": "no such words here"}
        with self.assertRaisesRegex(gcc.GenError, "citation not verified"):
            gcc.build(self.src, bad, self.ssha, self.origin)

    def test_every_cell_names_a_source(self):
        for role, r in self.cat["roles"].items():
            for row in r["operations"]:
                for col in gcc.COLUMNS:
                    self.assertTrue(row[col].get("source"), (role, row["operation"], col))
                    self.assertTrue(row[col].get("value"), (role, row["operation"], col))

    def test_views_exist_for_required_roles(self):
        for role in ("director", "producer", "project-manager", "game-designer", "game-artist", "ui-designer",
                     "gameplay-programmer", "web-engineer", "qa-engineer"):
            self.assertIn(f"{gcc.OUT}/views/{role}.md", self.files)
        self.assertIn("Management view", self.files[f"{gcc.OUT}/views/project-manager.md"])


if __name__ == "__main__":
    unittest.main()
