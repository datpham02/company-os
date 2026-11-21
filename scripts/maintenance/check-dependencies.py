"""Compare locally installed tool versions with dependencies/registry.yaml (Phase 2, P2-T02). Stdlib only.

    python -I scripts/maintenance/check-dependencies.py

For each dependency with a known version command, runs `<command> --version` (read-only, no network, nothing is
installed or changed) and compares the first version-looking token with the first one in `verifiedVersion`.

Prints one line per dependency:
- `ok`: the versions match;
- `DRIFT`: installed differs from registry;
- `not installed`;
- `no version in registry`;
- `skipped` (no command known).

Exits 1 when any DRIFT is found. ADR-007: drift must be checked against the registry.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yaml_subset  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
# dependency id -> version command (argv). Only tools the studio machine runs directly.
COMMANDS = {
    "paperclip": ["paperclipai", "--version"],
    "claude-code": ["claude", "--version"],
    "codex": ["codex", "--version"],
    "cursor-cli": ["agent", "--version"],
    "github-cli": ["gh", "--version"],
    "docker-desktop": ["docker", "--version"],
}
VERSION = re.compile(r"\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.\-]+)?")


def first_version(text):
    m = VERSION.search(text or "")
    return m.group(0) if m else None


def default_runner(argv):
    exe = shutil.which(argv[0])
    if not exe:
        return None
    try:
        p = subprocess.run([exe] + argv[1:], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (p.stdout or "") + (p.stderr or "")


def check(deps, runner=default_runner):
    rows = []
    for d in deps:
        did = d.get("id")
        if did not in COMMANDS:
            rows.append((did, "skipped", None, None))
            continue
        want = first_version(str(d.get("verifiedVersion") or ""))
        out = runner(COMMANDS[did])
        if out is None:
            rows.append((did, "not installed", want, None))
            continue
        got = first_version(out)
        if not want:
            rows.append((did, "no version in registry", None, got))
        elif got != want:
            rows.append((did, "DRIFT", want, got))
        else:
            rows.append((did, "ok", want, got))
    return rows


def main(argv=None, runner=default_runner):
    deps = (yaml_subset.load(os.path.join(REPO, "dependencies", "registry.yaml")) or {}).get("dependencies") or []
    rows = check(deps, runner)
    for did, status, want, got in rows:
        if status != "skipped":
            print(f"{did:16} {status:22} registry={want or '-'} installed={got or '-'}")
    drift = [r for r in rows if r[1] == "DRIFT"]
    print(f"{len(drift)} drift(s); {sum(1 for r in rows if r[1] == 'skipped')} dependencies have no version command")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
