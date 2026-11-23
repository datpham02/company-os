"""A2/A5 offline contract tests: no Agent or network required (stdlib only)."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/setup/preview-task-evidence.py"
SPEC = importlib.util.spec_from_file_location("capability_evidence", MODULE)
cap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cap)


def cell(value):
    return {"value": value, "source": "test fixture"}


def operation(id, *, registered="pixelfx: integrated", installed="verified version: fixture", kind="bash"):
    return {"operation": id, "kind": kind, "approved": cell("Board 2026-11-21: approved"),
            "permitted": cell("declared match (not runtime authorization)"),
            "registered": cell(registered), "installed": cell(installed),
            "runtime_verified": cell("no"), "production_validated": cell("no")}


class A2A5OfflineTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.repo = Path(self.dir.name)
        self.map = {"schema": "capability-routing.v1", "task_types": {
            "ui-review": {"role": "ui-designer", "operations": [], "restrictions": ["READ_ONLY_UX_REVIEW", "NO_SKILL_INSTALL"],
                          "knowledge": ["knowledge/company/standards/task-contract.md",
                                        "knowledge/departments/game/skills/studio-ui-ux-review/SKILL.md"]},
            "pixel-vfx": {"role": "game-artist", "operations": ["pixelfx-list", "pixelfx-render"], "restrictions": ["NO_RENDER_WITHOUT_TASK_AUTHORIZATION"],
                          "knowledge": ["knowledge/departments/game/workflows/asset-production.md"]},
            "godot-smoke": {"role": "qa-engineer", "operations": ["godot-smoke"], "restrictions": ["NO_COMMAND_EXECUTION_IN_PREVIEW"],
                            "knowledge": ["knowledge/company/standards/task-contract.md"]},
        }}
        self.cat = {"schema": "capability-catalog.v1", "source_commit": "test-source", "roles": {
            "ui-designer": {"status": "active", "department": "company", "operations": []},
            "game-artist": {"status": "active", "department": "game", "operations": [operation("pixelfx-list"), operation("pixelfx-render")]},
            "qa-engineer": {"status": "active", "department": "company", "operations": [operation("godot-smoke", registered="no registry entry", installed="yes")]},
        }}
        self._write(cap.ROUTING, self.map)
        self._write(cap.CATALOG, self.cat)
        self._write("config/paperclip/external-skill-candidates.json", {
            "schema": "external-skill-candidates.v1",
            "sources": [{"id": "ccgs", "repository": "Donchitos/Claude-Code-Game-Studios",
                         "commit": "abc0de79d6ceb0b5d7aa693945849b3937afbe6a",
                         "integration": "candidate", "mode": "harvest_reference_only", "license": "MIT"}],
            "skills": [{"id": "ccgs/ux-review", "source_id": "ccgs",
                        "path": ".claude/skills/ux-review/SKILL.md",
                        "role": "ui-designer", "task_types": ["ui-review"],
                        "review_state": "deferred", "proposal": "DEFER_NATIVE_STUDIO_SKILL_PREFERRED",
                        "value": "Read-only UX review method", "dependencies": [],
                        "blockers": ["native skill preferred"], "migration": "proposed native skill"}]
        })
        for path in self.map["task_types"]["ui-review"]["knowledge"]:
            self._raw(path, "# Example fixture (not a real Agent read)")
        self._raw("knowledge/departments/game/workflows/asset-production.md", "# Test")
        # In a complete company-os checkout the existing policy is present; tests copy it into temporary fixtures.
        policy = ROOT / "scripts/setup/preview-capability-routing.py"
        if policy.exists():
            self._raw("scripts/setup/preview-capability-routing.py", policy.read_text(encoding="utf-8"))

    def _raw(self, name, text):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def _write(self, name, payload):
        self._raw(name, json.dumps(payload))

    def task(self, kind="ui-review"):
        route = self.map["task_types"][kind]
        return {"schema": "task-capability-input.v1", "task_id": "TEST-101",
                "task_type": kind, "role": route["role"],
                "operations": [{"id": op, "required": i == 0} for i, op in enumerate(route["operations"])],
                "knowledge": [{"path": p, "required": True} for p in route["knowledge"]]}

    def test_native_skill_exists_but_agent_delivery_unverified(self):
        r = cap.resolve(self.repo, self.task())
        self.assertEqual(r["readiness"], "PREVIEW_ONLY")
        self.assertFalse(r["execution_authorized"])
        self.assertTrue(all(x["agent_delivery"] == "UNVERIFIED" for x in r["requirements"]))
        self.assertTrue(all(x["stages"]["ACCESSIBLE"]["status"] == "UNVERIFIED" for x in r["requirements"]))

    def test_required_vs_optional_blockers(self):
        t = self.task("pixel-vfx")
        self.cat["roles"]["game-artist"]["operations"][1]["installed"] = cell("no")
        self._write(cap.CATALOG, self.cat)
        r = cap.resolve(self.repo, t)
        self.assertEqual(r["readiness"], "PREVIEW_ONLY")  # optional rendered op is blocked
        self.assertEqual(r["requirements"][1]["catalog_status"], "BLOCKED")
        t["operations"][1]["required"] = True
        r = cap.resolve(self.repo, t)
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertIn("NOT_INSTALLED", r["required_blockers"][0])

    def test_godot_is_unregistered_even_when_installed(self):
        r = cap.resolve(self.repo, self.task("godot-smoke"))
        self.assertEqual(r["requirements"][0]["blocker"], "UNREGISTERED_DEPENDENCY")
        self.assertEqual(r["readiness"], "BLOCKED")

    def test_missing_required_source_blocks(self):
        t = self.task()
        p = self.repo / t["knowledge"][1]["path"]
        p.unlink()
        r = cap.resolve(self.repo, t)
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertEqual(r["requirements"][1]["blocker"], "SOURCE_MISSING")
        self.assertFalse(r["execution_authorized"])

    def test_optional_missing_knowledge_stays_unauthorized(self):
        t = self.task()
        t["knowledge"][1]["required"] = False
        (self.repo / t["knowledge"][1]["path"]).unlink()
        result = cap.resolve(self.repo, t)
        missing = result["requirements"][1]
        self.assertEqual(missing["blocker"], "SOURCE_MISSING")
        self.assertEqual(missing["catalog_status"], "BLOCKED")
        self.assertEqual(result["readiness"], "PREVIEW_ONLY")
        self.assertEqual(result["required_blockers"], [])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["agent_invocation_verified"])
        self.assertFalse(result["effectiveness_verified"])

    def test_role_mismatch_is_blocked(self):
        task = self.task()
        task["role"] = "qa-engineer"
        with self.assertRaisesRegex(ValueError, "role mismatch"):
            cap.resolve(self.repo, task)

    def test_omitted_mapped_requirement_is_rejected(self):
        t = self.task("pixel-vfx")
        t["operations"] = t["operations"][:1]
        with self.assertRaisesRegex(ValueError, "every mapped item"):
            cap.resolve(self.repo, t)

    def test_non_boolean_required_is_rejected(self):
        t = self.task()
        t["knowledge"][0]["required"] = "yes"
        with self.assertRaisesRegex(ValueError, "invalid knowledge"):
            cap.resolve(self.repo, t)

    def test_untrusted_evidence_is_not_access_or_invocation(self):
        t = self.task("pixel-vfx")
        name = "operation:pixelfx-list"
        proof = {"schema": "capability-evidence-reports.v1", "task_id": t["task_id"], "receipts": [
            {"item": name, "stage": "DISCOVERED", "evidence_ref": "example-log#1"},
            {"item": name, "stage": "ACCESSED", "evidence_ref": "example-log#2"},
            {"item": name, "stage": "INVOKED", "evidence_ref": "example-log#3"},
            {"item": name, "stage": "APPLIED", "evidence_ref": "example-review#1",
             "criterion": "material requirements", "artifact_ref": "example-output.md"},
            {"item": name, "stage": "REVIEWED", "evidence_ref": "example-review#2",
             "criterion": "test benchmark", "artifact_ref": "example-output.md"},
        ]}
        r = cap.resolve(self.repo, t, proof)
        item = r["requirements"][0]
        self.assertTrue(item["usage"]["receipt_chain_complete"])
        self.assertIn("UNVERIFIED", item["usage"]["report_verification"])
        self.assertEqual(item["usage"]["reported_stages"], ["DISCOVERED", "ACCESSED", "INVOKED", "APPLIED", "REVIEWED"])
        self.assertEqual(item["stages"]["ACCESSIBLE"]["status"], "UNVERIFIED")
        self.assertEqual(item["stages"]["INVOKED"]["status"], "UNVERIFIED")
        self.assertEqual(item["usage"]["effective_use"], "UNVERIFIED (requires independent outcome review)")
        self.assertFalse(r["agent_invocation_verified"])
        self.assertFalse(r["effectiveness_verified"])

    def test_incomplete_evidence_chain_is_marked_incomplete(self):
        t = self.task()
        ref = "knowledge:" + t["knowledge"][1]["path"]
        evidence = {"schema": "capability-evidence-reports.v1", "task_id": t["task_id"],
                    "receipts": [{"item": ref, "stage": "APPLIED", "evidence_ref": "untrusted-note",
                                  "artifact_ref": "demo.md", "criterion": "contrast"}]}
        r = cap.resolve(self.repo, t, evidence)
        self.assertIn("READ_OR_INVOKE_BEFORE_APPLIED", r["requirements"][1]["usage"]["missing_chain_stages"])
        self.assertFalse(r["requirements"][1]["usage"]["receipt_chain_complete"])

    def test_mismatched_task_evidence_rejected(self):
        t = self.task()
        evidence = {"schema": "capability-evidence-reports.v1", "task_id": "ANOTHER", "receipts": []}
        with self.assertRaisesRegex(ValueError, "task ID mismatch"):
            cap.resolve(self.repo, t, evidence)

    def test_read_must_not_be_used_for_tool(self):
        t = self.task("pixel-vfx")
        evidence = {"schema": "capability-evidence-reports.v1", "task_id": t["task_id"], "receipts": [
            {"item": "operation:pixelfx-list", "stage": "READ", "evidence_ref": "ref"}]}
        with self.assertRaisesRegex(ValueError, "READ is for knowledge"):
            cap.resolve(self.repo, t, evidence)

    def test_unknown_stage_rejected(self):
        t = self.task()
        evidence = {"schema": "capability-evidence-reports.v1", "task_id": t["task_id"], "receipts": [
            {"item": "knowledge:" + t["knowledge"][0]["path"], "stage": "MAGIC", "evidence_ref": "ref"}]}
        with self.assertRaisesRegex(ValueError, "unknown capability or event"):
            cap.resolve(self.repo, t, evidence)

    def test_fixture_root_cannot_supply_executable_policy(self):
        # A fixture-provided Python file must never run via --repo.
        malicious = self.repo / "scripts/setup/preview-capability-routing.py"
        malicious.write_text("raise RuntimeError('fixture policy was executed')", encoding="utf-8")
        try:
            result = cap.resolve(self.repo, self.task("godot-smoke"))
            self.assertEqual(result["requirements"][0]["blocker"], "UNREGISTERED_DEPENDENCY")
        finally:
            malicious.unlink()

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            cap.safe_path(self.repo, "../secrets")

    def test_markdown_is_advisory(self):
        report = cap.markdown(cap.resolve(self.repo, self.task()))
        self.assertIn("## Required capabilities", report)
        self.assertIn("delivery UNVERIFIED", report)
        self.assertIn("runtime still NOT authorized", report)

    def test_router_restrictions_and_external_candidates_copied_unchanged(self):
        task = self.task()
        expected = cap.canonical_router_policy().resolve(self.repo, task["task_type"])
        result = cap.resolve(self.repo, task)
        self.assertEqual(result["restrictions"], expected["restrictions"])
        self.assertEqual(result["external_skill_candidates"], expected["external_skill_candidates"])
        self.assertEqual(result["external_skill_candidates"][0]["status"], "DEFERRED_NOT_ACTIVE")
        self.assertFalse(result["external_skill_candidates"][0]["execution_authorized"])
        body = cap.markdown(result)
        self.assertIn("READ_ONLY_UX_REVIEW", body)
        self.assertIn("ccgs/ux-review", body)
        self.assertIn("DEFERRED_NOT_ACTIVE", body)
        self.assertIn("abc0de79d6", body)

    def test_every_stage_uses_identical_status_evidence_shape(self):
        for task_type in ("ui-review", "pixel-vfx", "godot-smoke"):
            with self.subTest(task_type=task_type):
                result = cap.resolve(self.repo, self.task(task_type))
                for requirement in result["requirements"]:
                    for name, info in requirement["stages"].items():
                        self.assertIsInstance(info, dict, name)
                        self.assertEqual(set(info), {"status", "evidence"}, name)
                        self.assertIsInstance(info["status"], str)
                        if name in ("DISCOVERABLE", "ACCESSIBLE", "EFFECTIVELY_USED"):
                            self.assertEqual(info["status"], "UNVERIFIED")

    def test_markdown_prints_each_stage_and_receipt_verification(self):
        task = self.task("pixel-vfx")
        evidence = {"schema": "capability-evidence-reports.v1", "task_id": task["task_id"], "receipts": [
            {"item": "operation:pixelfx-list", "stage": "INVOKED", "evidence_ref": "reported-only"}
        ]}
        result = cap.resolve(self.repo, task, evidence)
        body = cap.markdown(result)
        for requirement in result["requirements"]:
            for name, value in requirement["stages"].items():
                self.assertIn(name + ": status=", body)
                self.assertIn("evidence=", body)
        self.assertIn("receipt_chain_complete=false; report_verification=UNVERIFIED", body)
        self.assertNotIn("claim_complete", body)
        self.assertFalse(result["agent_invocation_verified"])

    def test_example_fixture_intentionally_missing_reviewed(self):
        fixture = ROOT / "tests/fixtures/capability-evidence/pixel-vfx-receipts.json"
        example = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertFalse(any(x["stage"] == "REVIEWED" for x in example["receipts"]))
        task = self.task("pixel-vfx")
        example["task_id"] = task["task_id"]
        result = cap.resolve(self.repo, task, example)
        usage = result["requirements"][0]["usage"]
        self.assertFalse(usage["receipt_chain_complete"])
        self.assertIn("REVIEWED", usage["missing_chain_stages"])
        self.assertIn("UNVERIFIED", usage["report_verification"])

    def test_a6_fixtures_resolve_against_real_catalog(self):
        catalog_path = ROOT / cap.CATALOG
        if not catalog_path.is_file() or not (ROOT / cap.ROUTING).is_file():
            self.fail("full Company OS catalog and routing map are required for A6 fixtures")
        expected = {
            "sealwarden-doc-review.json": "PREVIEW_ONLY",
            "ui-design.json": "PREVIEW_ONLY",
            "ui-review.json": "PREVIEW_ONLY",
            "godot-smoke.json": "BLOCKED",
            "web-qa-browser.json": "BLOCKED",
            "gameplay-reverse-engineering.json": "BLOCKED",
        }
        for name, readiness in expected.items():
            with self.subTest(fixture=name):
                task = json.loads((ROOT / "tests/fixtures/capability-evidence" / name).read_text(encoding="utf-8"))
                result = cap.resolve(ROOT, task)
                preview = cap.canonical_router_policy().resolve(ROOT, task["task_type"])
                self.assertEqual(result["readiness"], readiness)
                self.assertFalse(result["execution_authorized"])
                self.assertFalse(result["agent_invocation_verified"])
                self.assertFalse(result["effectiveness_verified"])
                self.assertEqual(result["department"], preview["department"])
                self.assertIn("department: `" + result["department"] + "`", cap.markdown(result))
                for item in result["requirements"]:
                    for stage_name in ("DISCOVERABLE", "ACCESSIBLE", "EFFECTIVELY_USED"):
                        self.assertEqual(item["stages"][stage_name]["status"], "UNVERIFIED")
                    if item["kind"] == "operation":
                        self.assertEqual(item["stages"]["INVOKED"]["status"], "UNVERIFIED")
                    else:
                        self.assertEqual(item["stages"]["READ"]["status"], "UNVERIFIED")
                        self.assertEqual(item["stages"]["INVOKED"]["status"], "NOT_APPLICABLE")
                self.assertEqual(result["restrictions"], preview["restrictions"])
                self.assertEqual(result["external_skill_candidates"], preview["external_skill_candidates"])
        godot = cap.resolve(ROOT, json.loads((ROOT / "tests/fixtures/capability-evidence/godot-smoke.json").read_text(encoding="utf-8")))
        self.assertEqual(godot["required_blockers"], [
            "operation:godot-version: UNREGISTERED_DEPENDENCY",
            "operation:godot-import: UNREGISTERED_DEPENDENCY",
            "operation:godot-smoke: UNREGISTERED_DEPENDENCY",
        ])
        browser = cap.resolve(ROOT, json.loads((ROOT / "tests/fixtures/capability-evidence/web-qa-browser.json").read_text(encoding="utf-8")))
        self.assertEqual(browser["requirements"][0]["blocker"], "DEPENDENCY_NOT_APPROVED")
        paused = cap.resolve(ROOT, json.loads((ROOT / "tests/fixtures/capability-evidence/gameplay-reverse-engineering.json").read_text(encoding="utf-8")))
        self.assertTrue(paused["requirements"][0]["blocker"].startswith("ROLE_NOT_ACTIVE"))

    def test_real_main_catalog_gates_when_available(self):
        # The full Company OS checkout includes the generated catalog; only that checkout
        # can claim this integration result. In a partial local copy this test is skipped.
        if not (ROOT / cap.CATALOG).is_file() or not (ROOT / cap.ROUTING).is_file():
            self.skipTest("full Company OS catalog and mapping not mounted")
        catalog = cap.load(ROOT, cap.CATALOG)
        routing = cap.load(ROOT, cap.ROUTING)
        gate = cap.canonical_router_policy().block_reason
        self.assertEqual(routing["schema"], "capability-routing.v1")
        role = catalog["roles"]["qa-engineer"]
        godot = next(x for x in role["operations"] if x["operation"] == "godot-smoke")
        self.assertEqual(gate(godot, role["status"]), "UNREGISTERED_DEPENDENCY")
        self.assertTrue((ROOT / "knowledge/departments/game/skills/studio-ui-ux-review/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()