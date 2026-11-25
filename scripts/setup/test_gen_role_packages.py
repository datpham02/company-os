"""Tests for gen-role-packages.py and the secret scan over every generated file (ADR-024). Offline: Git is read
locally; nothing reaches Paperclip.

    python -I -W error scripts/setup/test_gen_role_packages.py
"""
import copy
import importlib.util
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


grp = load("gen-role-packages")
ROLE = "game-artist"
PKG = f"{grp.OUT_DIR}/{ROLE}/AGENTS.md"
PKG_JSON = f"{grp.OUT_DIR}/{ROLE}/package.json"


def committed_commit():
    return grp.committed_commit(REPO, ROLE)


class RealPackage(unittest.TestCase):
    """The committed package, regenerated from the commit it records."""

    @classmethod
    def setUpClass(cls):
        cls.src = grp.Source(REPO, committed_commit())
        cls.manifest, cls.msha, cls.origin = grp.load_manifest(cls.src, REPO)
        cls.files = grp.generate(cls.src, cls.manifest, cls.msha, cls.origin)
        cls.doc = cls.files[PKG]
        cls.pkg = json.loads(cls.files[PKG_JSON])

    def test_determinism_byte_identical(self):
        again = grp.generate(grp.Source(REPO, self.src.commit), *grp.load_manifest(self.src, REPO))
        self.assertEqual(sorted(again), sorted(self.files))
        for k in self.files:
            self.assertEqual(again[k].encode("utf-8"), self.files[k].encode("utf-8"), k)

    def test_committed_output_is_current(self):
        for rel, text in self.files.items():
            with open(os.path.join(REPO, rel), encoding="utf-8", newline="") as f:
                self.assertEqual(f.read().replace("\r\n", "\n"), text, f"{rel} is stale: run gen-role-packages.py")

    def test_header_records_commit_and_package_hash(self):
        head = grp.parse_header(self.doc)
        self.assertTrue(head and head["intact"])
        self.assertEqual(head["source_commit"], self.src.commit)
        self.assertEqual(head["package_sha256"], self.pkg["package_sha256"])
        tampered = self.doc.replace("Never force-push", "Always force-push", 1)
        self.assertFalse(grp.parse_header(tampered)["intact"])

    def test_source_coverage_every_delivered_unit_has_its_marker(self):
        delivered = [u for u in self.manifest["roles"][ROLE]["units"] if u["delivery"] in grp.DELIVERED]
        for u in delivered:
            row = next(r for r in self.pkg["units"] if r["id"] == u["id"])
            m = re.search(rf"<!-- kd:unit {re.escape(u['id'])} src=(\S+) @([0-9a-f]{{12}}) sha256=([0-9a-f]{{16}}) "
                          r"status=(\S+) role=(\S+) dept=(\S+) auth=\"[^\"]+\" delivery=(\S+) -->", self.doc)
            self.assertIsNotNone(m, f"no marker for {u['id']}")
            self.assertTrue(m.group(1).startswith(u["source"] + "#"))
            self.assertEqual(m.group(2), self.src.commit[:12])
            self.assertEqual(m.group(3), row["source_sha256"][:16])
            self.assertEqual((m.group(4), m.group(5), m.group(6), m.group(7)),
                             (u["status"], ROLE, "game", u["delivery"]))
            # the marker's hash is the hash of the source text at the commit
            raw, _, _ = grp.extract_unit(self.src, u, {(s["source"], s["heading"]): s["before"]
                                                       for s in self.manifest["roles"][ROLE].get("block_splits", [])})
            self.assertEqual(grp.sha256(raw), row["source_sha256"])
        self.assertEqual(self.pkg["source_coverage"]["delivered_units_with_marker"], [u["id"] for u in delivered])

    def test_every_role_file_section_is_claimed(self):
        bad = copy.deepcopy(self.manifest)
        bad["roles"][ROLE]["units"] = [u for u in bad["roles"][ROLE]["units"] if u["id"] != "ga-role-io"]
        with self.assertRaisesRegex(grp.GenError, "source coverage: role-file blocks claimed by no unit"):
            grp.generate(self.src, bad, "x", "test")

    def test_budget_accounting(self):
        b = self.pkg["budget"]
        self.assertEqual(b["core_bytes"] + b["command_reference_bytes"], b["combined_bytes"])
        self.assertEqual(b["combined_bytes"], len(self.doc.encode("utf-8")))
        cmd_start = self.doc.index("\n\n## Command reference")
        self.assertEqual(b["command_reference_bytes"], len(self.doc[cmd_start:].encode("utf-8")))
        self.assertLessEqual(b["core_bytes"], b["core_max_bytes"])
        self.assertLessEqual(b["command_reference_bytes"], b["command_reference_max_bytes"])
        self.assertLessEqual(b["combined_bytes"], b["combined_max_bytes"])
        self.assertEqual(b["applies_to"], ["game-artist"])
        self.assertEqual(b["core_max_bytes"], 48000)
        self.assertEqual(b["command_reference_max_bytes"], 8000)
        self.assertEqual(b["combined_max_bytes"], 54000)
        self.assertIn("ESTIMATED", self.pkg["tokens_estimated"]["method"])

    def test_over_budget_fails_loudly_and_names_units(self):
        for key in ("core_max_bytes", "command_reference_max_bytes", "combined_max_bytes"):
            with self.subTest(key=key):
                small = copy.deepcopy(self.manifest)
                small["budget"][key] = 100
                with self.assertRaisesRegex(grp.GenError, r"(?s)over budget .*Nothing was dropped.*ga-role-visual"):
                    grp.generate(self.src, small, "x", "test")

    def test_exact_command_forms_stay_in_command_reference(self):
        cmd = self.doc[self.doc.index("\n## Command reference"):]
        for form in ("python -I ~/game-studio-workspace/tools/comfy-draft.py --asset <asset_id>",
                     "python -I ~/game-studio-workspace/tools/comfy-edit.py inpaint",
                     "godot --headless --path . --import", "node ~/tools/pixelfx/tools/list.mjs"):
            self.assertIn(form, cmd)

    def test_no_relative_link_survives(self):
        self.assertIsNone(grp.LINK_RE.search(grp.strip_external_links(self.doc)))
        self.assertIn("(on request)", self.doc)

    def test_mandatory_moves_are_all_covered(self):
        for g in self.pkg["mandatory_guard"]:
            self.assertTrue(g["result"].startswith(("verbatim", "covered by", "not applicable", "lexical lint")), g)

    def test_status_proposed_is_labelled_and_no_experimental_is_delivered(self):
        self.assertIn("kd:unit ga-role-visual", self.doc)
        self.assertRegex(self.doc, r"kd:unit ga-role-visual [^\n]*status=proposed")
        self.assertNotRegex(self.doc, r"status=(experimental|superseded)")

    def test_skill_files_and_procedure_commands(self):
        skill = self.manifest["skills"]["studio-art-identity-and-refinement"]
        md = self.files[f"{skill['dir']}/SKILL.md"]
        self.assertTrue(md.startswith("---\nname: studio-art-identity-and-refinement\n"))
        for heading in ("## Purpose", "## When to use it", "## Source knowledge", "## Operating procedure",
                        "## Approved dependencies", "## Known limitations"):
            self.assertIn(heading, md)
        self.assertIn(f"[{skill['reference_file']}]({skill['reference_file']})", md)
        self.assertIn(self.src.commit, md)
        mark = skill["retrieval_mark"]
        ref = self.files[f"{skill['dir']}/{skill['reference_file']}"]
        self.assertIn(mark, ref)
        self.assertNotIn(mark, self.doc)

    def test_restored_mandatory_sections_are_in_the_package(self):
        for heading in ("Ownership with Gameplay Programmer (interim)", "2. Task contract", "6. Blocker protocol",
                        "8. Reviews", "8. Approval boundaries", "6. Art assets and technical art"):
            self.assertIn(heading, self.doc, heading)
        self.assertNotIn("## Credentials", self.doc)

    def test_freshness_ignores_commit_id_and_unrelated_files(self):
        src, manifest = mini()
        pkg = json.loads(grp.generate(src, manifest, "m" * 64, "test")[f"{grp.OUT_DIR}/tester/package.json"])
        other = grp.DictSource(dict(src.files), "b" * 40)
        self.assertEqual(grp.freshness_findings(pkg, other), [])
        other.files["notes/unrelated.md"] = "not a knowledge source\n"
        self.assertEqual(grp.freshness_findings(pkg, other), [])
        changed = grp.DictSource(dict(src.files), src.commit)
        changed.files["knowledge/company/policies/rules.md"] = RULES_MD.replace("Never push to main.", "Never push to main now.")
        found = grp.freshness_findings(pkg, changed)
        self.assertEqual(found, ["r § R1. Repositories"])
        bad = copy.deepcopy(self.manifest)
        bad["skills"]["studio-art-identity-and-refinement"]["procedure"].append("Run `python -I ~/evil.py`.")
        with self.assertRaisesRegex(grp.GenError, "is not allowed for game-artist"):
            grp.generate(self.src, bad, "x", "test")
        bad = copy.deepcopy(self.manifest)
        bad["skills"]["studio-art-identity-and-refinement"]["dependencies"].append({"id": "toonout", "note": "x"})
        with self.assertRaisesRegex(grp.GenError, "toonout is evaluating"):
            grp.generate(self.src, bad, "x", "test")


ROLE_MD = """---
slug: tester
---

# Tester

## Identity
You test. See [rules](../../../../company/policies/rules.md#r1-repositories) and [rule two](../../../../company/policies/rules.md#r2-other).

## Tools
**Reviewing:** read the PR with `gh pr view 1`. Exact form: `git status --short` only.

## Extra
Background only.
"""
RULES_MD = """# Rules

## R1. Repositories
1. Never push to main.
2. Work in the Task Workspace.

## R2. Other
1. You MUST post a comment.
"""


def mini(files=None, units=None, **role):
    srcfiles = {"knowledge/departments/qa/agents/tester/AGENTS.md": ROLE_MD,
                "knowledge/company/policies/rules.md": RULES_MD,
                "dependencies/registry.yaml": "dependencies:\n",
                "config/paperclip/agents.json": json.dumps({
                    "rules": {"git": "Git rule: never force-push."},
                    "profiles": {"p": {"adapter": "claude_local", "allowedTools": ["Bash(git status*)"],
                                       "disallowedTools": [], "rules": ["git"]}},
                    "agents": {"tester": {"department": "qa", "profile": "p"}}})}
    srcfiles.update(files or {})
    rf = "knowledge/departments/qa/agents/tester/AGENTS.md"
    manifest = {
        "schema": grp.MANIFEST_SCHEMA,
        "budget": {"core_max_bytes": 32000, "command_reference_max_bytes": 6000, "combined_max_bytes": 38000},
        "package_intro": "# Role {role}", "command_reference_intro": "## Command reference",
        "company_rules_heading": "## Company rules", "on_request_note": "On request:",
        "roles": {"tester": {"department": "qa", "role_file": rf, "units": units or [
            {"id": "t-id", "source": rf, "headings": ["(preamble)", "Identity", "Tools"], "status": "approved",
             "authority": "role",              "delivery": "always_loaded"},
            {"id": "t-extra", "source": rf, "headings": ["Extra"], "status": "approved", "authority": "role",
             "delivery": "on_request"},
            {"id": "r", "source": "knowledge/company/policies/rules.md", "headings": ["R1. Repositories"],
             "status": "approved", "authority": "rules", "delivery": "always_loaded"}], "coverage": [], **role}},
    }
    return grp.DictSource(srcfiles, "a" * 40), manifest


class Synthetic(unittest.TestCase):
    def gen(self, src, manifest):
        return grp.generate(src, manifest, "m" * 64, "test")

    def test_minimal_package_rewrites_links(self):
        out = self.gen(*mini())
        doc = out[f"{grp.OUT_DIR}/tester/AGENTS.md"]
        self.assertIn("rules (in this file)", doc)
        self.assertIn("rule two (on request)", doc)
        self.assertIn("- knowledge/company/policies/rules.md", doc)
        self.assertNotIn("](", doc)

    def test_missing_heading_fails(self):
        src, m = mini()
        m["roles"]["tester"]["units"][2]["headings"] = ["R9. Missing"]
        with self.assertRaisesRegex(grp.GenError, "missing heading 'R9. Missing'"):
            self.gen(src, m)

    def test_missing_reference_target_fails(self):
        src, m = mini({"knowledge/departments/qa/agents/tester/AGENTS.md":
                       ROLE_MD.replace("../../../../company/policies/rules.md#r2-other", "../../../../company/nope.md")})
        with self.assertRaisesRegex(grp.GenError, "missing reference: link in .* -> knowledge/company/nope.md does not exist"):
            self.gen(src, m)

    def test_missing_anchor_fails(self):
        src, m = mini({"knowledge/departments/qa/agents/tester/AGENTS.md":
                       ROLE_MD.replace("#r2-other", "#r7-gone")})
        with self.assertRaisesRegex(grp.GenError, "anchor #r7-gone not found"):
            self.gen(src, m)

    def test_link_outside_company_os_fails(self):
        src, m = mini({"knowledge/departments/qa/agents/tester/AGENTS.md":
                       ROLE_MD.replace("../../../../company/policies/rules.md#r2-other", "../../../../../../outside.md")})
        with self.assertRaisesRegex(grp.GenError, "points outside Company OS"):
            self.gen(src, m)

    def test_unavailable_channel_survivor_fails(self):
        src, m = mini()
        orig = grp.rewrite_links
        try:
            grp.rewrite_links = lambda text, *a, **k: text  # a broken rewriter must be caught by the final scan
            with self.assertRaisesRegex(grp.GenError, "unavailable channel: a relative link survived"):
                self.gen(src, m)
        finally:
            grp.rewrite_links = orig

    def test_mandatory_sentence_cannot_leave_verified_channel(self):
        src, m = mini()
        m["roles"]["tester"]["units"].append({"id": "r2", "source": "knowledge/company/policies/rules.md",
                                              "headings": ["R2. Other"], "status": "approved", "authority": "rules",
                                              "delivery": "skill_assigned"})
        with self.assertRaisesRegex(grp.GenError, "(?s)mandatory content would leave the verified channels.*MUST post"):
            self.gen(src, m)
        m["roles"]["tester"]["coverage"] = [{"unit": "r2", "match": "MUST post", "covered_by": ["Never push to main."]}]
        self.gen(src, m)
        m["roles"]["tester"]["coverage"] = [{"unit": "r2", "match": "MUST post", "covered_by": ["not in the package"]}]
        with self.assertRaisesRegex(grp.GenError, "names phrases not in the delivered text"):
            self.gen(src, m)

    def test_exact_allowed_command_form_cannot_leave_verified_channel(self):
        src, m = mini({"knowledge/departments/qa/agents/tester/AGENTS.md":
                       ROLE_MD.replace("Background only.", "Run `git status --porcelain` here.")})
        with self.assertRaisesRegex(grp.GenError, "exact allowed command form `git status --porcelain`"):
            self.gen(src, m)

    def test_experimental_or_superseded_never_delivered(self):
        for st in ("experimental", "superseded"):
            src, m = mini()
            m["roles"]["tester"]["units"][2]["status"] = st
            with self.assertRaisesRegex(grp.GenError, f"is {st} and may not be delivered"):
                self.gen(src, m)

    def test_approved_unit_with_proposed_label_fails(self):
        src, m = mini({"knowledge/company/policies/rules.md":
                       RULES_MD.replace("1. Never push to main.", "`PROPOSED` draft.\n1. Never push to main.")})
        with self.assertRaisesRegex(grp.GenError, "declared approved but its source says `PROPOSED`"):
            self.gen(src, m)

    def test_command_reference_block_is_counted_separately(self):
        rf = "knowledge/departments/qa/agents/tester/AGENTS.md"
        src, m = mini(units=[
            {"id": "a", "source": rf, "headings": ["(preamble)", "Identity"], "status": "approved", "authority": "r",
             "delivery": "always_loaded"},
            {"id": "c", "source": rf, "headings": ["Tools"], "status": "approved", "authority": "r",
             "delivery": "command_reference"},
            {"id": "e", "source": rf, "headings": ["Extra"], "status": "approved", "authority": "r",
             "delivery": "on_request"},
            {"id": "r", "source": "knowledge/company/policies/rules.md", "headings": ["R1. Repositories"],
             "status": "approved", "authority": "rules", "delivery": "always_loaded"}])
        out = self.gen(src, m)
        pkg = json.loads(out[f"{grp.OUT_DIR}/tester/package.json"])
        doc = out[f"{grp.OUT_DIR}/tester/AGENTS.md"]
        self.assertGreater(pkg["budget"]["command_reference_bytes"], 0)
        self.assertEqual(pkg["budget"]["combined_bytes"], len(doc.encode("utf-8")))
        m["budget"]["command_reference_max_bytes"] = 50
        with self.assertRaisesRegex(grp.GenError, "command_reference_bytes=\\d+ > 50"):
            self.gen(src, m)


class Conflicts(unittest.TestCase):
    def test_must_versus_must_not(self):
        found = grp.find_conflicts([("a", "You MUST push the Task Branch before review."),
                                    ("b", "Agents MUST NOT push the Task Branch before review.")])
        self.assertEqual(len(found), 1)
        self.assertIn("contradictory obligation on 'push task branch before review'", found[0])

    def test_never_counts_as_must_not(self):
        found = grp.find_conflicts([("a", "You MUST merge the pull request."), ("b", "Never merge the pull request.")])
        self.assertTrue(found and "merge pull request" in found[0])

    def test_same_rule_id_two_texts(self):
        a = "## R2. Tasks\n1. Check out a Task first.\n"
        b = "## R2. Tasks\n1. Never check out a Task.\n"
        found = grp.find_conflicts([("x", a), ("y", b)])
        self.assertTrue(any("rule id R2.1 has two texts" in f for f in found), found)
        self.assertEqual(grp.find_conflicts([("x", a), ("y", a)]), [])

    def test_explicit_ids(self):
        found = grp.find_conflicts([("x", "- **K-002** Keep the silhouette."), ("y", "- **K-002** Drop the silhouette.")])
        self.assertTrue(any("K-002" in f for f in found))

    def test_unrelated_obligations_do_not_conflict(self):
        self.assertEqual(grp.find_conflicts([("a", "You MUST post a plan."), ("b", "You MUST NOT push to main.")]), [])

    def test_real_package_has_no_conflict(self):
        pkg = json.loads(grp.read_text(os.path.join(REPO, PKG_JSON)))
        self.assertEqual(pkg["conflicts"], [])

    def test_conflict_stops_generation(self):
        src, m = mini({"knowledge/company/policies/rules.md":
                       RULES_MD.replace("2. Work in the Task Workspace.", "2. You MUST push to main.")})
        with self.assertRaisesRegex(grp.GenError, "conflicting mandatory policies"):
            grp.generate(src, m, "m" * 64, "test")


def generated_files():
    roots = [os.path.join(REPO, grp.OUT_DIR), os.path.join(REPO, "config", "paperclip", "agent-settings"),
             os.path.join(REPO, "knowledge", "departments", "game", "skills")]
    for root in roots:
        for d, _, fs in os.walk(root):
            for f in fs:
                yield os.path.join(d, f)


class SecretScan(unittest.TestCase):
    def test_no_secret_in_any_generated_file(self):
        files = list(generated_files())
        self.assertGreater(len(files), 10)
        for path in files:
            with open(path, encoding="utf-8") as f:
                self.assertEqual(grp.secret_findings(f.read()), [], path)

    def test_scanner_catches_planted_material(self):
        planted = ["GH_TOKEN=" + "ghp_" + "a1" * 18, "token github_pat_" + "B2" * 15, "x-api sk-ant-" + "api03-abcdefghij",
                   "-----BEGIN OPENSSH " + "PRIVATE KEY-----", "Authorization: Bearer " + "abc.def-ghi_" * 3,
                   '{"secretId": "s-1"}', "C:" + "\\Users\\someone\\x", "~/.claude/.credentials" + ".json"]
        for p in planted:
            with self.subTest(p=p[:10]):
                self.assertTrue(grp.secret_findings(p), p)

    def test_generation_refuses_a_leak(self):
        src, m = mini({"knowledge/company/policies/rules.md":
                       RULES_MD.replace("Work in the Task Workspace.", "Use token " + "ghp_" + "z9" * 18 + ".")})
        with self.assertRaisesRegex(grp.GenError, "secret scan"):
            grp.generate(src, m, "m" * 64, "test")


if __name__ == "__main__":
    unittest.main()
