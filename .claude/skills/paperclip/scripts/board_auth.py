"""Board credential for the Board scripts (authentication migration Phase B; D-AUTH-04, A2 §3.D).

    python -I .claude/skills/paperclip/scripts/board_auth.py status   # mode, credential source, identity
    python -I .claude/skills/paperclip/scripts/board_auth.py store    # save a Board key, typed without echo
    python -I .claude/skills/paperclip/scripts/board_auth.py forget   # delete the saved key

Used by pc.py, scripts/setup/post-import.py, sync-instructions.py, check-agent-drift.py and
scripts/maintenance/merge-audit.py. The rules (D-AUTH-04, approved):

- The deployment mode comes from `GET /api/health` (`deploymentMode`, readable without a credential).
- `local_trusted`: no credential is read and no header is sent, exactly as before the migration.
- `authenticated`: the Board key is sent as `Authorization: Bearer`. Sources, in order:
  1. `PAPERCLIP_BOARD_TOKEN`, an explicit per-session override;
  2. a Windows Credential Manager generic credential (target `PAPERCLIP_BOARD_CREDENTIAL`, default
     `company-os/paperclip-board`), protected by DPAPI under the user's logon.
  When neither exists the script stops (fail closed); it never falls back to a keyless request.
- `PAPERCLIP_API_KEY` is never read: Paperclip gives that variable to every agent run (A1 3.11).
- Inside an agent run (`PAPERCLIP_RUN_ID` set) no Board credential is loaded at all.
- The key never appears in arguments, output, logs or exceptions; `redact()` masks it in error text. It is only
  sent to a loopback PAPERCLIP_URL (127.0.0.1, localhost, ::1).
- 401 and 403 get separate messages; Paperclip's 401 for an expired Board key talks about agent tokens (A1 3.6).
- The Board identity is `GET /api/cli-auth/me` -> `userId` (`local-board` in `local_trusted`), never a constant.

Keys are issued by the Board Operator in their own terminal (`paperclipai auth login`), never by the assistant.
Residual risk accepted by the Board (D-AUTH-06): any process running as the same Windows user can use the key.
Stdlib only.
"""
import ctypes
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_TARGET = "company-os/paperclip-board"
LOGIN_HINT = ("run `paperclipai auth login` in your own terminal, then save the key with "
              "`python -I .claude/skills/paperclip/scripts/board_auth.py store` "
              "(or set PAPERCLIP_BOARD_TOKEN for this session)")
_MODE = {}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class AuthError(Exception):
    pass


# ---------- Windows Credential Manager (generic credential) ----------

class _CREDENTIAL(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_uint32), ("Type", ctypes.c_uint32), ("TargetName", ctypes.c_wchar_p),
                ("Comment", ctypes.c_wchar_p), ("LastWritten", ctypes.c_uint64),
                ("CredentialBlobSize", ctypes.c_uint32), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", ctypes.c_uint32), ("AttributeCount", ctypes.c_uint32), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", ctypes.c_wchar_p), ("UserName", ctypes.c_wchar_p)]


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


def _advapi():
    if os.name != "nt":
        return None
    return ctypes.WinDLL("advapi32", use_last_error=True)


def target():
    return os.environ.get("PAPERCLIP_BOARD_CREDENTIAL") or DEFAULT_TARGET


def read_credential(name=None):
    """The stored key, or None when there is none (or not on Windows)."""
    adv = _advapi()
    if adv is None:
        return None
    pcred = ctypes.POINTER(_CREDENTIAL)()
    if not adv.CredReadW(ctypes.c_wchar_p(name or target()), CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        err = ctypes.get_last_error()
        if err == ERROR_NOT_FOUND:
            return None
        raise AuthError(f"Credential Manager read failed (Windows error {err})")
    try:
        c = pcred.contents
        blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    finally:
        adv.CredFree(pcred)
    return blob.decode("utf-8").strip() or None


def write_credential(secret, name=None):
    adv = _advapi()
    if adv is None:
        raise AuthError("Credential Manager is only available on Windows; use PAPERCLIP_BOARD_TOKEN")
    data = secret.encode("utf-8")
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    c = _CREDENTIAL(Type=CRED_TYPE_GENERIC, TargetName=name or target(), CredentialBlobSize=len(data),
                    CredentialBlob=ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)),
                    Persist=CRED_PERSIST_LOCAL_MACHINE, UserName="paperclip-board")
    if not adv.CredWriteW(ctypes.byref(c), 0):
        raise AuthError(f"Credential Manager write failed (Windows error {ctypes.get_last_error()})")


def delete_credential(name=None):
    adv = _advapi()
    if adv is None:
        return False
    if adv.CredDeleteW(ctypes.c_wchar_p(name or target()), CRED_TYPE_GENERIC, 0):
        return True
    if ctypes.get_last_error() == ERROR_NOT_FOUND:
        return False
    raise AuthError(f"Credential Manager delete failed (Windows error {ctypes.get_last_error()})")


# ---------- mode, token, headers ----------

def _health(api):
    with urllib.request.urlopen(api + "/health", timeout=30) as r:
        return json.loads(r.read() or b"{}")


def deployment_mode(api, health=_health):
    """`local_trusted` or `authenticated`, read once per process and API base."""
    if api not in _MODE:
        try:
            _MODE[api] = (health(api) or {}).get("deploymentMode")
        except (urllib.error.URLError, OSError) as e:
            raise AuthError(f"Paperclip is not reachable at {api} ({getattr(e, 'reason', e)}). "
                            "Start it with runtime/tools/start-studio.cmd.")
        except ValueError:
            raise AuthError(f"{api}/health did not return JSON; refusing to guess the deployment mode")
    return _MODE[api]


def board_token(env=None, read=read_credential):
    """(token, source) or (None, None). Never reads PAPERCLIP_API_KEY."""
    env = os.environ if env is None else env
    if env.get("PAPERCLIP_RUN_ID"):
        raise AuthError("this process is inside a Paperclip agent run (PAPERCLIP_RUN_ID is set); "
                        "the Board credential is never loaded there")
    if env.get("PAPERCLIP_BOARD_TOKEN", "").strip():
        return env["PAPERCLIP_BOARD_TOKEN"].strip(), "PAPERCLIP_BOARD_TOKEN"
    tok = read()
    return (tok, f"Credential Manager ({target()})") if tok else (None, None)


def headers(api, env=None, health=_health, read=read_credential):
    """Extra request headers for the Board. {} in local_trusted; fails closed in authenticated without a key."""
    mode = deployment_mode(api, health)
    if mode == "local_trusted":
        return {}
    if mode != "authenticated":
        raise AuthError(f"unknown Paperclip deploymentMode {mode!r}; refusing to guess how to authenticate")
    host = urllib.parse.urlsplit(api).hostname
    if host not in LOOPBACK:
        raise AuthError(f"PAPERCLIP_URL points at {host!r}; the Board key is only ever sent to a loopback address")
    tok, _ = board_token(env, read)
    if not tok:
        raise AuthError(f"Paperclip runs in authenticated mode and no Board credential is set: {LOGIN_HINT}")
    return {"Authorization": f"Bearer {tok}"}


def redact(text, tok=None):
    """Mask the Board key, and anything shaped like a Board key or a bearer header, in error text."""
    out = str(text)
    if tok:
        out = out.replace(tok, "[REDACTED]")
    out = re.sub(r"pcp_board_[A-Za-z0-9_\-]+", "[REDACTED]", out)
    return re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+", r"\1[REDACTED]", out)


def http_error(method, path, code, body, limit=400):
    """One-line message for an HTTP error; 401 and 403 are told apart (A1 §5.3)."""
    body = redact(body)[:limit]
    if code == 401:
        return (f"{method} {path} -> 401: the Board credential is missing, expired or revoked "
                f"(Paperclip may word this as an agent-token error): {LOGIN_HINT}. Server said: {body}")
    if code == 403:
        return f"{method} {path} -> 403: the Board user lacks the right for this action. Server said: {body}"
    return f"{method} {path} -> {code}: {body}"


def board_user_id(call):
    """The Board identity from GET /cli-auth/me (`local-board` in local_trusted)."""
    me = call("GET", "/cli-auth/me") or {}
    if not me.get("userId"):
        raise AuthError("GET /cli-auth/me returned no userId")
    return me["userId"]


# ---------- CLI ----------

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    api = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100/api").rstrip("/")
    cmd = argv[0] if argv else "status"
    try:
        if cmd == "store":
            secret = getpass.getpass("Board key (input hidden): ").strip()
            if not secret:
                print("nothing stored")
                return 1
            write_credential(secret)
            print(f"stored in Credential Manager as {target()}")
            return 0
        if cmd == "forget":
            print(f"deleted {target()}" if delete_credential() else f"no credential named {target()}")
            return 0
        if cmd == "status":
            mode = deployment_mode(api)
            _, source = board_token()
            print(f"deploymentMode: {mode}")
            print(f"Board credential: {source or 'none'}" + (" (not used in local_trusted)"
                                                              if mode == "local_trusted" and source else ""))
            h = headers(api)
            req = urllib.request.Request(api + "/cli-auth/me", headers=h)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    me = json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                print(http_error("GET", "/cli-auth/me", e.code, e.read().decode("utf-8", "replace")))
                return 1
            print(f"identity: {me.get('userId')} (source {me.get('source')}, "
                  f"instance admin {me.get('isInstanceAdmin')})")
            return 0
        print(__doc__)
        return 2
    except AuthError as e:
        print(redact(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
