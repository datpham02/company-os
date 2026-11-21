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
        full[slug] = {"adapterType": prof["adapter"], "adapterConfig": cfg,
                      "runtimeConfig": copy.deepcopy(spec.get("runtime") or CONF["runtime"])}
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


if __name__ == "__main__":
    unittest.main()
