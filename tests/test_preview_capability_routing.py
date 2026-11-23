"""Focused offline safety/regression tests for Task capability routing (stdlib only)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("router", ROOT / "scripts/setup/preview-capability-routing.py")
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)


def row(operation, approved="Board decision 2026-11-22", permitted="declared match (not runtime authorization)",
        registered="pixelfx: integrated", kind="bash", installed="verified version: fixture"):
    cell = lambda value: {"value": value, "source": "fixture"}
    return {"operation": operation, "kind": kind, "sample": "node example.js",
            "approved": cell(approved), "permitted": cell(permitted), "registered": cell(registered),
            "installed": cell(installed), "runtime_verified": cell("unknown"), "production_validated": cell("unknown")}


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        def save(name, data):
            p = self.repo / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data), encoding="utf-8")
        self.save = save
        self.cat = {"schema": "capability-catalog.v1", "source_commit": "fixture-sha", "roles": {
            "game-artist": {"status": "active", "operations": [row("pixelfx-list"), row("playwright-mcp", registered="playwright-mcp: candidate", permitted="unknown", approved="no (candidate)")]},
            "gameplay-programmer": {"status": "paused — security gate", "operations": [row("rea-mcp")]},
        }}
        self.route = {"schema": "capability-routing.v1", "task_types": {
            "vfx": {"role": "game-artist", "operations": ["pixelfx-list"], "knowledge": ["knowledge/game/asset.md"]},
            "candidate": {"role": "game-artist", "operations": ["playwright-mcp"], "knowledge": []},
            "paused": {"role": "gameplay-programmer", "operations": ["rea-mcp"], "knowledge": []},
        }}
        self.save(router.ROUTING_PATH, self.route)
        self.save(router.CATALOG_PATH, self.cat)
        self.external = {
            "schema": "external-skill-candidates.v1",
            "sources": [{"id": "ccgs", "repository": "Donchitos/Claude-Code-Game-Studios",
                         "commit": "abc0de79d6ceb0b5d7aa693945849b3937afbe6a",
                         "integration": "candidate", "mode": "harvest_reference_only", "license": "MIT"}],
            "skills": [{"id": "ccgs/art-bible", "source_id": "ccgs",
                        "path": ".claude/skills/art-bible/SKILL.md", "role": "game-artist",
                        "task_types": ["vfx"], "review_state": "candidate",
                        "proposal": "EVALUATE_ADAPT_ONLY", "value": "Art reference checklist",
                        "dependencies": ["project.yaml"],
                        "blockers": ["requires review"], "migration": "adapt later"}]
        }
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)

    def test_declared_only_without_runtime_or_knowledge_delivery_claims(self):
        result = router.resolve(self.repo, "vfx")
        self.assertEqual(result["capabilities"][0]["status"], "DECLARED_ONLY")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["knowledge"][0]["source_present"])
        self.assertIn("UNVERIFIED", result["knowledge"][0]["agent_delivery"])
        self.assertIn("capability: pixelfx-list", router.task_block(result))

    def test_candidate_is_blocked(self):
        self.assertEqual(router.resolve(self.repo, "candidate")["capabilities"][0]["reason"], "DEPENDENCY_NOT_APPROVED")

    def test_paused_role_is_blocked(self):
        self.assertIn("ROLE_NOT_ACTIVE", router.resolve(self.repo, "paused")["capabilities"][0]["reason"])

    def test_no_allow_or_unapproved_are_blocked(self):
        self.cat["roles"]["game-artist"]["operations"][0] = row("pixelfx-list", permitted="no allow rule")
        self.save(router.CATALOG_PATH, self.cat)
        self.assertEqual(router.resolve(self.repo, "vfx")["capabilities"][0]["status"], "BLOCKED")
        self.cat["roles"]["game-artist"]["operations"][0] = row("pixelfx-list", approved="no (rejected)")
        self.save(router.CATALOG_PATH, self.cat)
        self.assertEqual(router.resolve(self.repo, "vfx")["capabilities"][0]["status"], "BLOCKED")

    def test_unknown_operation_fails_closed(self):
        self.route["task_types"]["vfx"]["operations"] = ["invented-tool"]
        self.save(router.ROUTING_PATH, self.route)
        self.assertEqual(router.resolve(self.repo, "vfx")["capabilities"][0]["reason"], "NOT_IN_ROLE_CATALOG")

    def test_path_traversal_rejected(self):
        self.route["task_types"]["vfx"]["knowledge"] = ["../secret.txt"]
        self.save(router.ROUTING_PATH, self.route)
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "vfx")

    def test_external_discovery_never_activates_skill(self):
        result = router.resolve(self.repo, "vfx")
        ext = result["external_skill_candidates"]
        self.assertEqual(len(ext), 1)
        self.assertEqual(ext[0]["status"], "CANDIDATE_NOT_ACTIVE")
        self.assertFalse(ext[0]["execution_authorized"])
        self.assertFalse(ext[0]["knowledge_delivered"])
        self.assertIn("abc0de79d6ce", ext[0]["source"])
        self.assertIn("external-skill: ccgs/art-bible", router.task_block(result))

    def test_deferred_external_skill_never_activates(self):
        self.external["skills"][0]["review_state"] = "deferred"
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)
        self.assertEqual(router.resolve(self.repo, "vfx")["external_skill_candidates"][0]["status"],
                         "DEFERRED_NOT_ACTIVE")

    def test_unpinned_upstream_rejected(self):
        self.external["sources"][0]["commit"] = "main"
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "vfx")

    def test_external_traversal_and_unapproved_promotion_rejected(self):
        self.external["skills"][0]["path"] = "../../danger/SKILL.md"
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "vfx")
        self.external["skills"][0]["path"] = ".claude/skills/art-bible/SKILL.md"
        self.external["skills"][0]["review_state"] = "integrated"
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "vfx")

    def test_ui_ux_review_is_advisory_only(self):
        self.cat["roles"]["ui-designer"] = {"status": "active", "operations": []}
        self.route["task_types"]["ui-review"] = {
            "role": "ui-designer", "operations": [], "knowledge": []
        }
        self.external["skills"].append({
            "id": "ccgs/ux-review", "source_id": "ccgs",
            "path": ".claude/skills/ux-review/SKILL.md",
            "role": "ui-designer", "task_types": ["ui-review"],
            "review_state": "deferred", "proposal": "DEFER_NATIVE_STUDIO_SKILL_PREFERRED",
            "value": "Read-only quality rubric", "dependencies": ["project.yaml"],
            "blockers": ["upstream config"], "migration": "adapt checklist"
        })
        self.save(router.CATALOG_PATH, self.cat)
        self.save(router.ROUTING_PATH, self.route)
        self.save(router.EXTERNAL_SKILLS_PATH, self.external)
        result = router.resolve(self.repo, "ui-review")
        self.assertEqual(result["capabilities"], [])
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["external_skill_candidates"][0]["id"], "ccgs/ux-review")
        self.assertEqual(result["external_skill_candidates"][0]["status"], "DEFERRED_NOT_ACTIVE")
        self.assertIn("external-skill: ccgs/ux-review", router.task_block(result))

    def test_real_godot_smoke_shaped_row_is_blocked_as_unregistered(self):
        operation = row(
            "godot-smoke", approved="Board decision 2026-11-21, OQ-048 / SOU-31",
            permitted="declared match (not runtime authorization)",
            registered="no registry entry", installed="yes", kind="bash",
        )
        self.assertEqual(
            router.block_reason(operation, "active"), "UNREGISTERED_DEPENDENCY"
        )

    def test_not_installed_operation_is_blocked_even_if_approved(self):
        operation = row("example", registered="example: approved", installed="no")
        self.assertTrue(router.block_reason(operation, "active").startswith("NOT_INSTALLED"))
        operation["installed"]["value"] = "not installed (planned)"
        self.assertTrue(router.block_reason(operation, "active").startswith("NOT_INSTALLED"))

    def test_live_committed_map_against_generated_catalog_all_original_tasks(self):
        # This is the real repository mapping + generated catalog, NOT temporary fixtures.
        root = ROOT
        routing = router.read_json(root, router.ROUTING_PATH)
        catalog = router.read_json(root, router.CATALOG_PATH)
        expected = {
            "sealwarden-doc-review": {},
            "pixel-vfx": {"pixelfx-list": "DECLARED_ONLY", "pixelfx-render": "DECLARED_ONLY"},
            "ui-design": {"uiux-search": "DECLARED_ONLY", "design-md": "DECLARED_ONLY"},
            "godot-smoke": {"godot-version": "BLOCKED", "godot-import": "BLOCKED",
                            "godot-smoke": "BLOCKED"},
            "web-qa-browser": {"playwright-mcp": "BLOCKED"},
            "gameplay-reverse-engineering": {"rea-mcp": "BLOCKED"},
        }
        self.assertEqual(set(routing["task_types"]), set(expected) | {"combat-design", "skill-quality-review", "ui-review"})
        self.assertEqual(catalog["schema"], "capability-catalog.v1")
        for task_type, expected_ops in expected.items():
            with self.subTest(task_type=task_type):
                result = router.resolve(root, task_type)
                statuses = {row["id"]: row["status"] for row in result["capabilities"]}
                self.assertEqual(statuses, expected_ops)
                self.assertFalse(result["execution_authorized"])
                if task_type == "godot-smoke":
                    self.assertTrue(all(x["reason"] == "UNREGISTERED_DEPENDENCY"
                                        for x in result["capabilities"]))

    def test_live_external_manifest_defers_upstream_ux_review(self):
        manifest = router.read_json(ROOT, router.EXTERNAL_SKILLS_PATH)
        matches = [s for s in manifest["skills"] if s["id"] == "ccgs/ux-review"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["review_state"], "deferred")
        self.assertEqual(matches[0]["proposal"], "DEFER_NATIVE_STUDIO_SKILL_PREFERRED")
        routes = router.read_json(ROOT, router.ROUTING_PATH)
        native = "knowledge/departments/game/skills/studio-ui-ux-review/SKILL.md"
        self.assertIn(native, routes["task_types"]["ui-review"]["knowledge"])
        result = router.resolve(ROOT, "ui-review")
        upstream = [s for s in result["external_skill_candidates"] if s["id"] == "ccgs/ux-review"]
        self.assertEqual(len(upstream), 1)
        self.assertEqual(upstream[0]["status"], "DEFERRED_NOT_ACTIVE")
        self.assertFalse(upstream[0]["execution_authorized"])
        self.assertFalse(upstream[0]["knowledge_delivered"])
        refs = [k for k in result["knowledge"] if k["path"] == native]
        self.assertEqual(len(refs), 1)
        self.assertIn("UNVERIFIED", refs[0]["agent_delivery"])

    def test_unknown_task_type_rejected(self):
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "anything")


if __name__ == "__main__":
    unittest.main()
