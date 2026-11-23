"""Tests for check-agent-drift.py (Phase 2, P2-T03). Offline: the live side is built from this repository and then
changed, so nothing reaches Paperclip.

    python -I -W error scripts/setup/test_check_agent_drift.py
"""
import contextlib
import copy
import importlib.util
import io
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


cad = load("check-agent-drift")
bp = load("build-package")
si = load("sync-instructions")
CONF = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
COMPANY = {"id": "c-1", "name": "Soucean", "issuePrefix": "SOU"}


def matching_live():
    """Live records exactly as this repository would configure them (the strict reviewer is absent)."""
    full, bodies = {}, si.role_bodies()
    for slug, spec in CONF["agents"].items():
        prof = CONF["profiles"][spec["profile"]]
        if bp.is_strict_reviewer(prof):
            continue
        cfg = bp.adapter_block(prof, spec, CONF["rules"], "SOU", "C:/ws", "agent")["config"]
        cfg["env"] = {s: {"type": "secret_ref", "secretId": "s-1"} for s in spec.get("secrets") or []}
        cfg["paperclipSkillSync"] = {"desiredSkills": []}
        full[slug] = {"adapterType": prof["adapter"], "adapterConfig": cfg,
                      "runtimeConfig": copy.deepcopy(spec.get("runtime") or CONF["runtime"]),
                      "permissions": {k: bool((spec.get("permissions") or {}).get(k, False))
                                      for k in ("canCreateAgents", "canCreateSkills")}}
    return full, {s: b for s, b in bodies.items() if s in full}


class Drift(unittest.TestCase):
    def run_drift(self, full, live_bodies):
        return cad.drift(CONF, COMPANY, full, si.role_bodies(), live_bodies, bp)

    def test_matching_company_has_no_drift(self):
        self.assertEqual(self.run_drift(*matching_live()), [])

    def test_each_drift_kind(self):
        def args_removed(full, _):
            full["qa-engineer"]["adapterConfig"]["extraArgs"] = [a for a in full["qa-engineer"]["adapterConfig"]["extraArgs"]
                                                                 if a != "Bash(printenv*)"]

        def args_added(full, _):
            full["director"]["adapterConfig"]["extraArgs"].append("Bash(curl *)")

        def heartbeat(full, _):
            full["producer"]["runtimeConfig"]["heartbeat"]["enabled"] = True

        def env(full, _):
            full["director"]["adapterConfig"]["env"] = {"GH_TOKEN": {"type": "secret_ref"}}

        def body(_, bodies):
            bodies["qa-engineer"] = bodies["qa-engineer"].replace("Credentials", "Creds")

        def adapter(full, _):
            full["web-engineer"]["adapterType"] = "claude_local"

        def model(full, _):
            full["gameplay-programmer"]["adapterConfig"]["model"] = "gpt-5.3-codex"

        def effort(full, _):
            full["director"]["adapterConfig"].pop("effort")

        def missing(full, _):
            full.pop("ui-designer")

        def unknown(full, _):
            full["intern"] = {"adapterType": "claude_local", "adapterConfig": {}}

        cases = ((args_removed, "qa-engineer: extraArgs differ (missing 1, extra 0)"),
                 (args_added, "director: extraArgs differ (missing 0, extra 1); first extra: 'Bash(curl *)'"),
                 (heartbeat, "producer: heartbeat.enabled is True, expected False"),
                 (env, "director: env bindings ['GH_TOKEN'], expected [] (names only)"),
                 (body, "qa-engineer: AGENTS.md differs"),
                 (adapter, "web-engineer: adapter 'claude_local', expected 'cursor'"),
                 (model, "gameplay-programmer: model is 'gpt-5.3-codex', expected 'gpt-5.3-codex-high'"),
                 (effort, "director: effort is None, expected 'high'"),
                 (missing, "ui-designer: declared in agents.json but not in the company"),
                 (unknown, "intern: in the company but not in agents.json"))
        for change, want in cases:
            with self.subTest(want=want):
                full, bodies = matching_live()
                change(full, bodies)
                findings = self.run_drift(full, bodies)
                self.assertTrue(any(f.startswith(want) for f in findings), findings)

    def test_env_values_are_never_printed(self):
        full, bodies = matching_live()
        full["director"]["adapterConfig"]["env"] = {"X": "super-secret-value"}
        self.assertFalse(any("super-secret-value" in f for f in self.run_drift(full, bodies)))

    def test_main_reads_only(self):
        full, bodies = matching_live()
        calls = []

        def get(path):
            calls.append(path)
            if path == "/companies":
                return [COMPANY]
            if path == "/companies/c-1/agents":
                return [{"id": s, "urlKey": s} for s in full]
            if path == "/companies/c-1":
                return {**COMPANY, "requireBoardApprovalForNewAgents": True}
            if path.startswith("/agents/") and "instructions-bundle" in path:
                return {"content": bodies[path.split("/")[2]]}
            return full[path.split("/")[2]]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cad.main(["--company", "SOU"], get=get)
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(all(isinstance(c, str) for c in calls))  # every call is a GET path (the getter takes no body)


    def test_missing_bundle_file_still_reads_as_empty(self):
        """A 404 on the instructions bundle is a drift, not a crash; only 401/403 stop the run."""
        import urllib.error
        from unittest import mock
        err = urllib.error.HTTPError("u", 404, "not found", {}, io.BytesIO(b"{}"))
        with mock.patch.object(cad.urllib.request, "urlopen", side_effect=err),                 mock.patch.object(cad.board_auth, "headers", return_value={}):
            with self.assertRaises(urllib.error.HTTPError):
                cad.http_get("/agents/x/instructions-bundle/file?path=AGENTS.md")
        err401 = urllib.error.HTTPError("u", 401, "unauthorized", {}, io.BytesIO(b"Agent token invalid"))
        with mock.patch.object(cad.urllib.request, "urlopen", side_effect=err401),                 mock.patch.object(cad.board_auth, "headers", return_value={}):
            with self.assertRaisesRegex(SystemExit, "paperclipai auth login"):
                cad.http_get("/companies")


grp = load("gen-role-packages")
MANIFEST = json.loads(grp.read_text(os.path.join(REPO, "config", "paperclip", "knowledge-manifest.json")))
SETTINGS_REPO = os.path.join(REPO, "config", "paperclip", "agent-settings", "game-artist.settings.json")
PACKAGE = grp.read_text(os.path.join(REPO, grp.OUT_DIR, "game-artist", "AGENTS.md"))
SKILL = MANIFEST["skills"]["studio-art-identity-and-refinement"]


def skill_hashes():
    return {f"{SKILL['dir']}/{f}": grp.sha256(grp.read_text(os.path.join(REPO, SKILL["dir"], f)).replace("\r\n", "\n"))
            for f in ("SKILL.md", SKILL["reference_file"])}


class Extended(unittest.TestCase):
    """The knowledge-delivery categories (ADR-024) on fixtures; nothing reaches Paperclip."""

    def rows(self, full=None, bodies=None, company=None, skills=None, files=None, state=None):
        f, b = matching_live()
        full = full or f
        bodies = bodies or b
        return cad.extended(CONF, MANIFEST, company or {"requireBoardApprovalForNewAgents": True}, full, bodies,
                            si.role_bodies(), skills or {}, lambda p: (files or {}).get(p), bp, grp,
                            deployment_state=state)

    def pick(self, rows, cat, role):
        return [r for r in rows if r["category"] == cat and r["role"] == role]

    def test_baseline_has_no_extended_drift(self):
        rows = self.rows()
        self.assertEqual([r for r in rows if r["status"] == "drift"], [])
        dep = self.pick(rows, "instructions.deployment", "game-artist")[0]
        self.assertTrue(dep["detail"].startswith("legacy-role-body; equals the role file"))
        self.assertIn("state pilot_prepared", dep["detail"])
        skill = self.pick(rows, "skills.assigned", "game-artist")[0]
        self.assertEqual(skill["status"], "info")
        self.assertIn("not delivery of a required skill", skill["detail"])
        self.assertTrue(any(r["category"] == "unverified.runtime" for r in rows))
        self.assertTrue(any(r["role"] == "code-reviewer" and "absent" in r["detail"] for r in rows))

    def test_legacy_drift_still_reported(self):
        full, bodies = matching_live()
        bodies["game-artist"] = "older role text"
        dep = self.pick(self.rows(full, bodies), "instructions.deployment", "game-artist")[0]
        self.assertEqual(dep["status"], "drift")
        self.assertIn("legacy-role-body; differs from the role file", dep["detail"])

    def test_generated_package_detected_by_header(self):
        full, bodies = matching_live()
        bodies["game-artist"] = PACKAGE
        active = {"roles": {"game-artist": {"state": "pilot_active", "required_skills": []}}}
        rows = self.rows(full, bodies, state=active)
        dep = self.pick(rows, "instructions.deployment", "game-artist")[0]
        self.assertEqual(dep["status"], "ok", dep)
        self.assertTrue(dep["detail"].startswith("generated-package; equals the committed package"))
        self.assertIn("state pilot_active", dep["detail"])
        head = grp.parse_header(PACKAGE)
        src = self.pick(rows, "instructions.source", "game-artist")[0]["detail"]
        self.assertIn(head["source_commit"], src)
        self.assertIn(head["package_sha256"], src)
        bodies["game-artist"] = PACKAGE.replace("Never force-push", "Force-push", 1)
        dep = self.pick(self.rows(full, bodies, state=active), "instructions.deployment", "game-artist")[0]
        self.assertEqual(dep["status"], "drift")
        self.assertIn("header hash does not match", dep["detail"])

    def test_settings_file_memory_policy(self):
        full, bodies = matching_live()
        full["game-artist"]["adapterConfig"]["extraArgs"] += ["--settings", "X:/ws/agent-settings/game-artist.settings.json"]
        good = grp.read_text(SETTINGS_REPO)
        rows = self.rows(full, bodies, files={"X:/ws/agent-settings/game-artist.settings.json": good})
        mem = self.pick(rows, "memory.policy", "game-artist")[0]
        self.assertEqual(mem["status"], "ok")
        self.assertIn("autoMemoryEnabled=false", mem["detail"])
        self.assertIn("--settings X:/ws/agent-settings/game-artist.settings.json",
                      self.pick(rows, "adapter.config", "game-artist")[0]["detail"])
        changed = json.dumps({**json.loads(good), "autoMemoryEnabled": True})
        mem = self.pick(self.rows(full, bodies, files={"X:/ws/agent-settings/game-artist.settings.json": changed}),
                        "memory.policy", "game-artist")[0]
        self.assertEqual((mem["status"], "differs from" in mem["detail"]), ("drift", True))
        mem = self.pick(self.rows(full, bodies, files={}), "memory.policy", "game-artist")[0]
        self.assertEqual((mem["status"], "missing" in mem["detail"]), ("drift", True))

    def test_assigned_skill_revision(self):
        full, bodies = matching_live()
        full["game-artist"]["adapterConfig"]["paperclipSkillSync"] = {"desiredSkills": ["company/studio-art-identity-and-refinement"]}
        ok = self.pick(self.rows(full, bodies, skills={"game-artist": {"files": skill_hashes()}}),
                       "skills.assigned", "game-artist")[0]
        self.assertEqual(ok["status"], "ok", ok)
        changed = {k: "0" * 64 for k in skill_hashes()}
        bad = self.pick(self.rows(full, bodies, skills={"game-artist": {"files": changed}}), "skills.assigned", "game-artist")[0]
        self.assertEqual(bad["status"], "drift")
        unread = self.pick(self.rows(full, bodies, skills={}), "skills.assigned", "game-artist")[0]
        self.assertEqual(unread["status"], "unverified")
        full["director"]["adapterConfig"]["paperclipSkillSync"] = {"desiredSkills": ["company/studio-art-identity-and-refinement"]}
        other = self.pick(self.rows(full, bodies), "skills.assigned", "director")[0]
        self.assertEqual(other["status"], "drift")

    def test_adapter_permissions_and_company(self):
        full, bodies = matching_live()
        full["game-artist"]["permissions"]["canCreateSkills"] = True
        full["director"]["adapterConfig"]["dangerouslySkipPermissions"] = True
        rows = self.rows(full, bodies, company={"requireBoardApprovalForNewAgents": False})
        drifts = {(r["category"], r["role"]) for r in rows if r["status"] == "drift"}
        self.assertEqual(drifts, {("adapter.permissions", "game-artist"), ("adapter.config", "director"),
                                  ("adapter.company", "*")})

    def test_offline_fixture_mode_in_main(self):
        import tempfile
        full, bodies = matching_live()
        bodies["game-artist"] = PACKAGE
        q = "?path=AGENTS.md"
        fx = {"get": {"/companies": [COMPANY], "/companies/c-1": {**COMPANY, "requireBoardApprovalForNewAgents": True},
                      "/companies/c-1/agents": [{"id": s, "urlKey": s} for s in full]}, "files": {}}
        for s in full:
            fx["get"][f"/agents/{s}"] = full[s]
            fx["get"][f"/agents/{s}/instructions-bundle/file{q}"] = {"content": bodies[s]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fx.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(fx, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cad.main(["--company", "SOU", "--fixtures", path], get=None)
        text = out.getvalue()
        self.assertNotIn("game-artist: AGENTS.md differs", text)  # an intact package is judged by instructions.deployment
        self.assertIn("state pilot_prepared", text)
        self.assertIn("live package while state expects the legacy role body", text)
        self.assertNotEqual(code, 0, text)

    def test_active_pilot_rejects_empty_skills_and_legacy_text(self):
        full, bodies = matching_live()
        active = {"roles": {"game-artist": {"state": "pilot_active",
                                            "required_skills": ["studio-art-identity-and-refinement"]}}}
        rows = self.rows(full, bodies, state=active)
        dep = self.pick(rows, "instructions.deployment", "game-artist")[0]
        skill = self.pick(rows, "skills.assigned", "game-artist")[0]
        mem = self.pick(rows, "memory.policy", "game-artist")[0]
        self.assertEqual(dep["status"], "drift")
        self.assertIn("active pilot requires the generated package", dep["detail"])
        self.assertEqual(skill["status"], "drift")
        self.assertIn("empty desiredSkills is not OK", skill["detail"])
        self.assertEqual(mem["status"], "drift")


if __name__ == "__main__":
    unittest.main()
