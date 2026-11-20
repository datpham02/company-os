"""OQ-042 Review Package Phase 3: GitHub API source (docs/design/review-package.md §4 option A, §6).

Reads a pull request over the GitHub REST API with the packager's dedicated read-only token and turns it into
the same source shape as the Phase 1 fixture (review_pack.SOURCE_SCHEMA), so review_pack.plan_package applies
every §5.2 limit and §5.3 rule unchanged, including the blob-SHA check and the head-moved check.

No git process, no local repository, no Paperclip. The token is read from Windows Credential Manager, sent only
in the Authorization header, and never written to output, logs or exceptions.
"""
import base64
import ctypes
import datetime
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
CREDENTIAL_TARGET = "company-os/review-packager"
PAGE_SIZE = 100
MAX_PAGES = 30  # 3,000 files; far beyond the 50-file package limit, so a runaway list is refused
EXPIRY_WARN_DAYS = 14
TIMEOUT = 30
STATUS_MAP = {"added": "A", "modified": "M", "removed": "D", "renamed": "R", "copied": "C", "changed": "T"}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_TOKEN_RE = re.compile(r"(github_pat_|ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]+")


class GitHubSourceError(Exception):
    """A refusal; the message never contains the token."""


def redact(text, token=None):
    text = str(text)
    if token:
        text = text.replace(token, "<token>")
    return _TOKEN_RE.sub("<token>", text)


# ---------- credential ----------

class _CREDENTIAL(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_uint32), ("Type", ctypes.c_uint32), ("TargetName", ctypes.c_wchar_p),
                ("Comment", ctypes.c_wchar_p), ("LastWritten", ctypes.c_uint64),
                ("CredentialBlobSize", ctypes.c_uint32), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", ctypes.c_uint32), ("AttributeCount", ctypes.c_uint32), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", ctypes.c_wchar_p), ("UserName", ctypes.c_wchar_p)]


def read_token(target=CREDENTIAL_TARGET):
    """Read a generic credential from Windows Credential Manager. Refuses when it is missing or not Windows."""
    if sys.platform != "win32":
        raise GitHubSourceError("the packager token is read from Windows Credential Manager; not available here")
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    pcred = ctypes.POINTER(_CREDENTIAL)()
    CRED_TYPE_GENERIC = 1
    if not advapi.CredReadW(ctypes.c_wchar_p(target), CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        raise GitHubSourceError(f"no packager token in Windows Credential Manager under {target!r} "
                                "(generic credential); the Board stores it there (review-package.md §6)")
    try:
        c = pcred.contents
        raw = bytes(bytearray(c.CredentialBlob[i] for i in range(c.CredentialBlobSize)))
    finally:
        advapi.CredFree(pcred)
    for enc in ("utf-16-le", "utf-8"):
        try:
            token = raw.decode(enc).strip("\x00").strip()
        except UnicodeDecodeError:
            continue
        if token and token.isascii() and " " not in token:
            return token
    raise GitHubSourceError(f"the credential {target!r} does not hold a usable token")


# ---------- HTTP ----------

def urllib_transport(method, url, headers):
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, {k.lower(): v for k, v in res.headers.items()}, res.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read()


class GitHubClient:
    def __init__(self, token, transport=urllib_transport, api=API, now=None):
        if not token:
            raise GitHubSourceError("no packager token")
        self._token = token
        self._transport = transport
        self.api = api.rstrip("/")
        self.now = now or datetime.datetime.now(datetime.timezone.utc)
        self.warnings = []
        self.calls = 0

    def get(self, path, query=None):
        url = self.api + path + ("?" + urllib.parse.urlencode(query) if query else "")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "company-os-review-packager", "Authorization": f"Bearer {self._token}"}
        self.calls += 1
        try:
            status, h, body = self._transport("GET", url, headers)
        except Exception as e:  # network errors may echo the request; never leak the token
            raise GitHubSourceError(f"GitHub request failed: {redact(e, self._token)}") from None
        self._check_expiry(h)
        if status in (401, 403):
            if status == 403 and h.get("x-ratelimit-remaining") == "0":
                raise GitHubSourceError("GitHub rate limit reached; try again after the reset time")
            raise GitHubSourceError(f"GitHub answered {status} for {path}: token invalid, revoked or lacking "
                                    "read access; no other credential is tried")
        if status == 404:
            raise GitHubSourceError(f"GitHub answered 404 for {path}: not found, or the token cannot read it")
        if status != 200:
            raise GitHubSourceError(f"GitHub answered {status} for {path}")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise GitHubSourceError(f"GitHub returned a body that is not JSON for {path}")

    def _check_expiry(self, headers):
        value = headers.get("github-authentication-token-expiration")
        if not value or any("expires" in w for w in self.warnings):
            return
        try:
            exp = datetime.datetime.strptime(value.replace(" UTC", " +0000"), "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return
        days = (exp - self.now).total_seconds() / 86400
        if days < EXPIRY_WARN_DAYS:
            self.warnings.append(f"the packager token expires in {max(days, 0):.0f} days ({value}); rotate it "
                                 "(review-package.md §6)")


# ---------- source building ----------

def _tree(client, repo, sha):
    t = client.get(f"/repos/{repo}/git/trees/{sha}", {"recursive": "1"})
    if t.get("truncated"):
        raise GitHubSourceError(f"the tree of {sha[:12]} is truncated by GitHub; the package would be incomplete")
    return {e["path"]: e for e in t.get("tree", []) if e.get("type") in ("blob", "commit")}


def _blob(client, repo, sha, what):
    if not isinstance(sha, str) or not SHA1_RE.match(sha):
        raise GitHubSourceError(f"{what}: no valid blob sha")
    b = client.get(f"/repos/{repo}/git/blobs/{sha}")
    if b.get("encoding") != "base64" or not isinstance(b.get("content"), str):
        raise GitHubSourceError(f"{what}: GitHub did not return the blob content (encoding "
                                f"{b.get('encoding')!r}); it may be too large for the API")
    data = base64.b64decode(b["content"].replace("\n", ""))
    return {"sha": sha, "contentBase64": base64.b64encode(data).decode("ascii")}


def _pr(client, repo, number):
    pr = client.get(f"/repos/{repo}/pulls/{number}")
    head, base = pr.get("head") or {}, pr.get("base") or {}
    for name, val in (("head.sha", head.get("sha")), ("base.sha", base.get("sha"))):
        if not isinstance(val, str) or not SHA1_RE.match(val):
            raise GitHubSourceError(f"pull request #{number}: {name} is missing")
    return pr


def fetch_source(client, repo, number, issue, task, schema):
    """Build a source dict (design §4 option A, steps 1–7). The packager's plan step validates it further."""
    if not REPO_RE.match(repo or ""):
        raise GitHubSourceError(f"repository {repo!r} is not owner/name")
    if not isinstance(number, int) or number < 1:
        raise GitHubSourceError("the pull request number must be a positive integer")
    # 1. PR metadata
    pr = _pr(client, repo, number)
    head_sha, base_sha = pr["head"]["sha"], pr["base"]["sha"]
    changed = pr.get("changed_files")
    if not isinstance(changed, int):
        raise GitHubSourceError(f"pull request #{number} does not report changed_files")
    # 2. merge base
    cmp_ = client.get(f"/repos/{repo}/compare/{base_sha}...{head_sha}")
    mb = (cmp_.get("merge_base_commit") or {}).get("sha")
    if not isinstance(mb, str) or not SHA1_RE.match(mb):
        raise GitHubSourceError("the compare response has no merge base commit")
    # 3. every page of the file list
    gh_files, page = [], 1
    while True:
        if page > MAX_PAGES:
            raise GitHubSourceError(f"the file list has more than {MAX_PAGES} pages; refusing")
        chunk = client.get(f"/repos/{repo}/pulls/{number}/files", {"per_page": PAGE_SIZE, "page": page})
        if not isinstance(chunk, list):
            raise GitHubSourceError("the file list page is not a list")
        if not chunk:
            break
        gh_files.extend(chunk)
        page += 1
    # (the count against changed_files is checked by plan_package; checked here too for a clear message)
    if len(gh_files) != changed:
        raise GitHubSourceError(f"the PR reports {changed} changed files but {len(gh_files)} were listed; "
                                "the file list is incomplete")
    # 4. blobs, verified against the trees at head and at the merge base
    head_tree, base_tree = _tree(client, repo, head_sha), _tree(client, repo, mb)
    files = []
    for f in gh_files:
        path, gh_status = f.get("filename"), f.get("status")
        status = STATUS_MAP.get(gh_status)
        if not isinstance(path, str) or status is None:
            raise GitHubSourceError(f"file {path!r}: GitHub status {gh_status!r} is not supported")
        old = f.get("previous_filename") if status in ("R", "C") else None
        entry = {"path": path, "status": status}
        if old is not None:
            entry["oldPath"] = old
        if status != "D":
            t = head_tree.get(path)
            if t is None:
                raise GitHubSourceError(f"file {path!r} is missing from the tree at head {head_sha[:12]}")
            if f.get("sha") and f["sha"] != t["sha"]:
                raise GitHubSourceError(f"file {path!r}: the file list sha differs from the head tree; the head "
                                        "may have moved during the read")
            if t.get("type") == "commit":
                raise GitHubSourceError(f"file {path!r} is a submodule change; the GitHub source does not "
                                        "package submodules (no blob to verify)")
            entry["mode"] = t.get("mode")
            entry["head"] = _blob(client, repo, t["sha"], f"file {path!r} at head")
        if status != "A":
            bpath = old if old is not None else path
            t = base_tree.get(bpath)
            if t is None:
                raise GitHubSourceError(f"file {bpath!r} is missing from the tree at the merge base {mb[:12]}")
            if t.get("type") == "commit":
                raise GitHubSourceError(f"file {bpath!r} is a submodule at the merge base; not packaged")
            entry.setdefault("mode", t.get("mode"))
            entry["base"] = _blob(client, repo, t["sha"], f"file {bpath!r} at the merge base")
        files.append(entry)
    # 7. context files (the Task's Read set) at head
    context = []
    for p in task.get("readSet") or []:
        t = head_tree.get(p)
        if t is None or t.get("type") != "blob":
            raise GitHubSourceError(f"read-set file {p!r} is not a file at head {head_sha[:12]}")
        context.append(dict({"path": p}, **_blob(client, repo, t["sha"], f"context {p!r}")))
    # 6. head moved?
    after = _pr(client, repo, number)["head"]["sha"]
    return {
        "schema": schema, "source": "github-api", "issue": issue, "repository": repo,
        "pullRequest": {"number": number, "url": pr.get("html_url"), "state": pr.get("state"),
                        "changedFiles": changed},
        "baseSha": base_sha, "headSha": head_sha, "mergeBaseSha": mb, "headShaAfterBuild": after,
        "files": files, "context": context, "task": task,
    }
