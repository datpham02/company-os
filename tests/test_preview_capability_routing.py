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
        registered="pixelfx: integrated", kind="bash"):
    cell = lambda value: {"value": value, "source": "fixture"}
    return {"operation": operation, "kind": kind, "sample": "node example.js",
            "approved": cell(approved), "permitted": cell(permitted), "registered": cell(registered),
            "runtime_verified": cell("unknown"), "production_validated": cell("unknown")}


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

    def test_unknown_task_type_rejected(self):
        with self.assertRaises(ValueError):
            router.resolve(self.repo, "anything")


if __name__ == "__main__":
    unittest.main()
