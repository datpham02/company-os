"""Tests for sync-instructions.py: the default run is unchanged, and the single-role pilot mode (ADR-024) refuses
without --role and a matching --confirm. Offline: the HTTP call is stubbed, nothing reaches Paperclip.

    python -I -W error scripts/setup/test_sync_instructions.py
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


si = load("sync-instructions")
COMPANY = {"id": "c-1", "name": "Soucean", "issuePrefix": "SOU"}


class Stub:
    """Stands in for sync-instructions.call. Live bodies: every role current except the ones in `stale`."""

    def __init__(self, stale=(), absent=("code-reviewer",)):
        self.calls = []
        self.bodies = {s: b for s, b in si.role_bodies().items() if s not in absent}
        for s in stale:
            self.bodies[s] = "old text"

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == "/companies":
            return [COMPANY]
        if path == "/companies/c-1/agents":
            return [{"id": f"id-{s}", "urlKey": s} for s in self.bodies]
        if "/instructions-bundle/file" in path and method == "GET":
            slug = path.split("/")[2][3:]
            return {"content": self.bodies[slug], "revision": {"id": f"rev-{slug}"}}
        if method == "GET" and path.startswith("/agents/"):
            return {"id": path.split("/")[2], "adapterConfig": {"model": "x", "env": {"GH_TOKEN": {"type": "secret_ref"}}}}
        if method == "PUT":
            return {}
        raise AssertionError(f"unexpected call {method} {path}")


def run(argv, stub):
    out = io.StringIO()
    orig = si.call
    si.call = stub
    try:
        with contextlib.redirect_stdout(out):
            code = si.main(argv)
    finally:
        si.call = orig
    return code, out.getvalue()


class DefaultUnchanged(unittest.TestCase):
    def test_dry_run_lists_every_role(self):
        stub = Stub(stale=("game-artist", "gameplay-programmer"))
        _, out = run(["--company", "Soucean", "--dry-run"], stub)
        want = []
        for slug in si.role_bodies():
            if slug == "code-reviewer":
                want.append(f"{slug:20} not in Paperclip (import it first)")
            elif slug in ("game-artist", "gameplay-programmer"):
                want.append(f"{slug:20} would update")
            else:
                want.append(f"{slug:20} current")
        self.assertEqual(out.splitlines(), want)
        self.assertFalse([c for c in stub.calls if c[0] != "GET"])

    def test_default_run_updates_every_stale_role_with_the_role_body(self):
        stub = Stub(stale=("game-artist", "gameplay-programmer"))
        run(["--company", "Soucean"], stub)
        puts = [(p, b) for m, p, b in stub.calls if m == "PUT"]
        self.assertEqual(sorted(p for p, _ in puts), ["/agents/id-game-artist/instructions-bundle/file",
                                                       "/agents/id-gameplay-programmer/instructions-bundle/file"])
        for p, b in puts:
            slug = p.split("/")[2][3:]
            self.assertEqual(b, {"path": "AGENTS.md", "content": si.role_bodies()[slug], "baseRevisionId": f"rev-{slug}"})


class PilotMode(unittest.TestCase):
    def refused(self, argv, msg):
        stub = Stub(stale=("game-artist",))
        with self.assertRaisesRegex(SystemExit, msg):
            run(argv, stub)
        self.assertEqual(stub.calls, [], "pilot refusals happen before any call")

    def test_refuses_without_role_or_confirm(self):
        self.refused(["--company", "Soucean", "--generated-package"], "needs --role <slug> and --confirm <slug>")
        self.refused(["--company", "Soucean", "--generated-package", "--role", "game-artist"], "needs --role")
        self.refused(["--company", "Soucean", "--generated-package", "--confirm", "game-artist"], "needs --role")

    def test_refuses_mismatched_confirm(self):
        self.refused(["--company", "Soucean", "--generated-package", "--role", "game-artist", "--confirm", "director"],
                     "does not match --role")

    def test_pilot_flags_alone_do_not_change_the_default_run(self):
        self.refused(["--company", "Soucean", "--role", "game-artist", "--confirm", "game-artist"],
                     "belong to pilot mode")

    def test_live_change_needs_a_backup_dir(self):
        self.refused(["--company", "Soucean", "--generated-package", "--role", "game-artist", "--confirm", "game-artist"],
                     "needs --backup-dir")

    def test_dry_run_touches_one_role_with_gets_only(self):
        stub = Stub(stale=("game-artist", "gameplay-programmer"))
        _, out = run(["--company", "Soucean", "--generated-package", "--role", "game-artist", "--confirm", "game-artist",
                      "--dry-run"], stub)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertRegex(out, r"game-artist +would update to generated package [0-9a-f]{16} \(source [0-9a-f]{12}\)")
        self.assertTrue(all(m == "GET" for m, _, _ in stub.calls))
        self.assertFalse([p for _, p, _ in stub.calls if "gameplay-programmer" in p])

    def test_live_run_writes_backup_then_puts_only_the_package(self):
        stub = Stub(stale=("game-artist", "gameplay-programmer"))
        with tempfile.TemporaryDirectory() as tmp:
            _, out = run(["--company", "Soucean", "--generated-package", "--role", "game-artist", "--confirm",
                          "game-artist", "--backup-dir", tmp], stub)
            backups = os.listdir(tmp)
            self.assertEqual(len(backups), 1)
            with open(os.path.join(tmp, backups[0]), encoding="utf-8") as f:
                snap = json.load(f)
            self.assertEqual(snap["role"], "game-artist")
            self.assertEqual(snap["instructions"]["content"], "old text")
            self.assertNotIn("GH_TOKEN", json.dumps(snap["adapterConfig_keys"]))
            puts = [(p, b) for m, p, b in stub.calls if m == "PUT"]
            self.assertEqual(len(puts), 1)
            self.assertEqual(puts[0][0], "/agents/id-game-artist/instructions-bundle/file")
            with open(os.path.join(si.GENERATED_DIR, "game-artist", "AGENTS.md"), encoding="utf-8") as f:
                self.assertEqual(puts[0][1]["content"], f.read().replace("\r\n", "\n"))
            self.assertEqual(puts[0][1]["baseRevisionId"], "rev-game-artist")
            # rollback: the snapshot goes back, for that one role only
            stub2 = Stub(stale=("game-artist",))
            stub2.bodies["game-artist"] = puts[0][1]["content"]
            run(["--company", "Soucean", "--restore-from", os.path.join(tmp, backups[0]), "--role", "game-artist",
                 "--confirm", "game-artist", "--backup-dir", tmp], stub2)
            puts2 = [b for m, _, b in stub2.calls if m == "PUT"]
            self.assertEqual([b["content"] for b in puts2], ["old text"])

    def test_restore_refuses_another_roles_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"role": "director", "instructions": {"content": "x"}}, f)
            stub = Stub()
            with self.assertRaisesRegex(SystemExit, "is a snapshot of 'director', not 'game-artist'"):
                run(["--company", "Soucean", "--restore-from", path, "--role", "game-artist", "--confirm", "game-artist",
                     "--dry-run"], stub)
            self.assertFalse([c for c in stub.calls if c[0] == "PUT"])


if __name__ == "__main__":
    unittest.main()
