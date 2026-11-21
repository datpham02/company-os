"""Tests for board_auth.py (authentication migration Phase B, D-AUTH-04). Offline: health and the credential store
are fakes, so nothing reaches Paperclip or Credential Manager.

    python -I -W error .claude/skills/paperclip/scripts/test_board_auth.py

Set BOARD_AUTH_CREDMAN_TEST=1 to also round-trip a throwaway Credential Manager entry (Windows; it is deleted again).
"""
import os
import sys
import unittest
import uuid
from unittest import mock

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import board_auth as ba  # noqa: E402
import pc  # noqa: E402

TOKEN = "pcp_board_" + "x" * 24  # a fake value with the real key's shape


def health(mode):
    return lambda api: {"deploymentMode": mode}


def never(*_a, **_k):
    raise AssertionError("the credential store must not be read")


class Headers(unittest.TestCase):
    def setUp(self):
        ba._MODE.clear()

    def test_local_trusted_reads_nothing_and_sends_nothing(self):
        self.assertEqual(ba.headers("http://a", env={"PAPERCLIP_BOARD_TOKEN": TOKEN}, health=health("local_trusted"),
                                    read=never), {})

    def test_authenticated_uses_the_override_first(self):
        h = ba.headers("http://127.0.0.1:1/api", env={"PAPERCLIP_BOARD_TOKEN": TOKEN}, health=health("authenticated"),
                       read=never)
        self.assertEqual(h, {"Authorization": f"Bearer {TOKEN}"})

    def test_authenticated_falls_back_to_credential_manager(self):
        h = ba.headers("http://127.0.0.1:1/api", env={}, health=health("authenticated"), read=lambda: TOKEN)
        self.assertEqual(h, {"Authorization": f"Bearer {TOKEN}"})

    def test_fails_closed_without_a_key_and_ignores_the_agent_variable(self):
        with self.assertRaisesRegex(ba.AuthError, "paperclipai auth login"):
            ba.headers("http://127.0.0.1:1/api", env={"PAPERCLIP_API_KEY": TOKEN}, health=health("authenticated"),
                       read=lambda: None)

    def test_no_board_credential_inside_an_agent_run(self):
        with self.assertRaisesRegex(ba.AuthError, "agent run"):
            ba.headers("http://127.0.0.1:1/api", env={"PAPERCLIP_RUN_ID": "r-1", "PAPERCLIP_BOARD_TOKEN": TOKEN},
                       health=health("authenticated"), read=never)

    def test_key_never_sent_off_loopback(self):
        with self.assertRaisesRegex(ba.AuthError, "loopback"):
            ba.headers("http://evil.example/api", env={"PAPERCLIP_BOARD_TOKEN": TOKEN},
                       health=health("authenticated"), read=never)
        for api in ("http://127.0.0.1:3100/api", "http://localhost:3100/api", "http://[::1]:3100/api"):
            self.assertIn("Authorization", ba.headers(api, env={"PAPERCLIP_BOARD_TOKEN": TOKEN},
                                                      health=health("authenticated"), read=never))

    def test_unknown_mode_is_refused(self):
        with self.assertRaisesRegex(ba.AuthError, "unknown Paperclip deploymentMode"):
            ba.headers("http://a", env={}, health=health(None), read=never)

    def test_mode_is_read_once_per_api(self):
        calls = []

        def h(api):
            calls.append(api)
            return {"deploymentMode": "local_trusted"}
        for _ in range(3):
            ba.headers("http://a", env={}, health=h, read=never)
        self.assertEqual(calls, ["http://a"])


class Messages(unittest.TestCase):
    def test_401_and_403_differ(self):
        m401 = ba.http_error("GET", "/x", 401, "Agent token invalid")
        m403 = ba.http_error("PATCH", "/y", 403, "forbidden")
        self.assertIn("missing, expired or revoked", m401)
        self.assertIn("paperclipai auth login", m401)
        self.assertIn("lacks the right", m403)
        self.assertNotIn("auth login", m403)

    def test_redaction(self):
        text = f"echo {TOKEN} and Authorization: Bearer abc.def-123 and secret-xyz"
        out = ba.redact(text, "secret-xyz")
        for leaked in (TOKEN, "abc.def-123", "secret-xyz"):
            self.assertNotIn(leaked, out)
        self.assertNotIn(TOKEN, ba.http_error("GET", "/x", 500, f"boom {TOKEN}"))

    def test_identity_comes_from_cli_auth_me(self):
        self.assertEqual(ba.board_user_id(lambda m, p: {"userId": "u-7"} if p == "/cli-auth/me" else None), "u-7")
        with self.assertRaises(ba.AuthError):
            ba.board_user_id(lambda m, p: {})


class PcWiring(unittest.TestCase):
    def test_auth_error_becomes_api_error_without_the_key(self):
        with mock.patch.object(pc.board_auth, "headers", side_effect=ba.AuthError(f"bad {TOKEN}")):
            with self.assertRaises(pc.ApiError) as cm:
                pc.call("GET", "/companies")
        self.assertNotIn(TOKEN, str(cm.exception))

    def test_board_user_is_resolved_once(self):
        saved = dict(pc._BOARD)
        pc._BOARD.clear()
        try:
            with mock.patch.object(pc, "call", return_value={"userId": "u-9"}) as c:
                self.assertEqual((pc.board_user(), pc.board_user()), ("u-9", "u-9"))
            c.assert_called_once_with("GET", "/cli-auth/me")
            self.assertEqual(pc.who({"assigneeUserId": "u-9"}, {}), "Board")
            self.assertEqual(pc.who({"assigneeUserId": "local-board"}, {}), "Board (legacy)")
        finally:
            pc._BOARD.clear()
            pc._BOARD.update(saved)


@unittest.skipUnless(os.name == "nt" and os.environ.get("BOARD_AUTH_CREDMAN_TEST") == "1", "opt-in, Windows only")
class CredentialManagerRoundTrip(unittest.TestCase):
    def test_write_read_delete(self):
        name = f"company-os/test-{uuid.uuid4().hex}"
        try:
            ba.write_credential(TOKEN, name)
            self.assertEqual(ba.read_credential(name), TOKEN)
        finally:
            self.assertTrue(ba.delete_credential(name))
        self.assertIsNone(ba.read_credential(name))
        self.assertFalse(ba.delete_credential(name))


if __name__ == "__main__":
    unittest.main()
