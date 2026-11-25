"""Install the S-1 reporting wrappers (pc-issue-update, pc-upload-artifact) into a bin folder outside every agent
workspace, pinned to the trusted Paperclip skill scripts by sha256 (Issue #113, S-1 option R-B).

    python -I scripts/setup/install-report-wrappers.py [--paperclip-scripts-dir DIR] [--bin DIR] [--workspace DIR]
    python -I scripts/setup/install-report-wrappers.py --check      # installed files equal a fresh render; no writes

The wrappers are the only reporting commands the agents' allow rules accept: Bash(bash "{REPORT_BIN}/pc-issue-update"
--issue-id *) and Bash(bash "{REPORT_BIN}/pc-upload-artifact" *). build-package.py and check-agent-drift.py expand
{REPORT_BIN} to the same default folder (<HOME>/.company-os/report-bin) or to --report-bin. Machine paths are never
committed (ADR-010).

Trust boundary (see docs/architecture/security-architecture.md): the agent runs as the same Windows user that owns
these files, so file permissions alone do not make them immutable. The enforcement boundary is the Claude Code
permission layer (no Write/Edit/Bash rule reaches the bin folder) plus the sha256 pin and --check.
"""
import argparse
import hashlib
import os
import re
import shutil
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TEMPLATES = os.path.join(REPO, "scripts", "report-wrappers")
HOME = os.path.expanduser("~")
WRAPPERS = {
    "pc-issue-update": ("paperclip-issue-update.sh", "@@ISSUE_UPDATE_SHA256@@"),
    "pc-upload-artifact": ("paperclip-upload-artifact.sh", "@@UPLOAD_ARTIFACT_SHA256@@"),
}
DIR_PLACEHOLDER = "@@PAPERCLIP_SCRIPTS_DIR@@"


def default_bin():
    return os.path.join(HOME, ".company-os", "report-bin")


def detect_scripts_dir():
    """The skill scripts of the globally installed paperclipai package (the server copy Paperclip symlinks into every
    prompt bundle). Never a workspace or prompt-cache path."""
    exe = shutil.which("paperclipai")
    if not exe:
        return None
    base = os.path.dirname(os.path.realpath(exe))
    for root in (base, os.path.join(base, "..", "lib")):
        cand = os.path.join(root, "node_modules", "paperclipai", "node_modules", "@paperclipai", "server", "skills",
                            "paperclip", "scripts")
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return None


def norm(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def inside(child, parent):
    c, p = norm(child), norm(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def bash_path(p):
    return os.path.abspath(p).replace("\\", "/")


def render(scripts_dir):
    """{wrapper name: rendered text}. Refuses a scripts dir whose path could break the single-quoted assignment."""
    if "'" in scripts_dir or "\n" in scripts_dir:
        sys.exit("refused: the scripts folder path contains a quote or newline")
    out = {}
    for name, (target, sha_ph) in WRAPPERS.items():
        tpath = os.path.join(scripts_dir, target)
        if not os.path.isfile(tpath) or os.path.islink(tpath):
            sys.exit(f"refused: {target} is missing or a link in {scripts_dir}")
        text = open(os.path.join(TEMPLATES, name), encoding="utf-8", newline="").read().replace("\r\n", "\n")
        for ph in (DIR_PLACEHOLDER, sha_ph):
            if text.count(ph) != 1:
                sys.exit(f"template {name}: placeholder {ph} must occur exactly once")
        text = text.replace(DIR_PLACEHOLDER, bash_path(scripts_dir)).replace(sha_ph, sha256_file(tpath))
        if re.search(r"@@[A-Z0-9_]+@@", text):
            sys.exit(f"template {name}: unresolved placeholder")
        out[name] = text
    return out


def check_locations(bin_dir, scripts_dir, workspace):
    if not os.path.isabs(bin_dir):
        sys.exit("refused: --bin must be an absolute path")
    for label, path in (("--bin", bin_dir), ("the Paperclip scripts folder", scripts_dir)):
        for other, what in ((workspace, "the agents' workspace"), (REPO, "this repository")):
            if inside(path, other) or inside(other, path):
                sys.exit(f"refused: {label} must be outside {what}")
        if "claude-prompt-cache" in norm(path):
            sys.exit(f"refused: {label} must not be inside a Paperclip prompt cache (agent --add-dir)")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--paperclip-scripts-dir", help="trusted Paperclip skill scripts folder (default: detected from "
                                                   "the paperclipai command)")
    p.add_argument("--bin", default=default_bin(), help="install folder (default: <HOME>/.company-os/report-bin)")
    p.add_argument("--workspace", default=os.path.join(HOME, "game-studio-workspace"),
                   help="agents' workspace; the bin folder must be outside it")
    p.add_argument("--check", action="store_true", help="compare installed wrappers with a fresh render; no writes")
    a = p.parse_args(argv)

    scripts_dir = a.paperclip_scripts_dir or detect_scripts_dir()
    if not scripts_dir:
        sys.exit("Paperclip scripts folder not found; pass --paperclip-scripts-dir")
    scripts_dir = os.path.abspath(scripts_dir)
    check_locations(a.bin, scripts_dir, a.workspace)
    rendered = render(scripts_dir)

    if a.check:
        bad = []
        for name, text in rendered.items():
            path = os.path.join(a.bin, name)
            if os.path.islink(path) or not os.path.isfile(path):
                bad.append(f"{name}: missing or a link")
            elif open(path, encoding="utf-8", newline="").read() != text:
                bad.append(f"{name}: differs from a fresh render (changed, or the Paperclip scripts changed)")
        for line in bad:
            print(line)
        print("report wrappers: " + ("OK" if not bad else f"{len(bad)} problem(s)"))
        return 1 if bad else 0

    os.makedirs(a.bin, exist_ok=True)
    if os.path.islink(a.bin):
        sys.exit("refused: --bin is a link")
    for name, text in rendered.items():
        path = os.path.join(a.bin, name)
        if os.path.islink(path):
            sys.exit(f"refused: {path} is a link")
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
        os.chmod(path, stat.S_IREAD | stat.S_IXUSR)
        print(f"installed {name}: sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]}...")
    for name, (target, _) in WRAPPERS.items():
        print(f"pinned {target}: {sha256_file(os.path.join(scripts_dir, target))[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
