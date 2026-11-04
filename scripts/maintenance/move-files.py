"""Move files with `git mv` and rewrite every relative Markdown link that pointed at them.

Stdlib only. Run from anywhere:

    python -I scripts/maintenance/move-files.py scripts/maintenance/m1-moves.json --dry-run
    python -I scripts/maintenance/move-files.py scripts/maintenance/m1-moves.json

The mapping file is JSON: {"files": {"old/path.md": "new/path.md", ...}, "dirs": {"old/dir/": "new/dir/", ...},
"keepText": ["paths whose prose must not change, e.g. docs/decisions/"]}.

Pass 1 rewrites Markdown links `[text](relative/path#anchor)` in every tracked .md file, resolving each
link against the file's OLD location and writing it relative to its NEW location.
Pass 2 rewrites repository paths written in backticks (`company/RULES.md`) in current documents,
except files under `keepText` (decision records, changelog, the migration map), which are history.
"""
import json
import os
import posixpath
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LINK = re.compile(r"(\]\()([^)\s]+)(\))")
TICK = re.compile(r"`([A-Za-z0-9_.\-/<>]+)`")


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=True).stdout


def main():
    mapping = json.load(open(sys.argv[1], encoding="utf-8"))
    dry = "--dry-run" in sys.argv
    files, dirs = mapping["files"], mapping.get("dirs", {})
    keep = tuple(mapping.get("keepText", []))

    def new_path(old):
        """Map an old repository path (file or directory) to its new path."""
        if old in files:
            return files[old]
        probe = old if old.endswith("/") else old + "/"
        for o, n in sorted(dirs.items(), key=lambda kv: -len(kv[0])):
            if probe.startswith(o):
                return (n + probe[len(o):]).rstrip("/") + ("/" if old.endswith("/") else "")
        return old

    tracked = git("ls-files").split()
    where = {p: files.get(p, p) for p in tracked}          # old path -> new path, for every tracked file
    for old, new in files.items():
        if old not in tracked:
            sys.exit(f"not tracked: {old}")

    if not dry:
        for old, new in files.items():
            os.makedirs(os.path.join(REPO, os.path.dirname(new)), exist_ok=True)
            git("mv", old, new)

    changed = 0
    for old_file, new_file in where.items():
        if not new_file.endswith(".md"):
            continue
        path = os.path.join(REPO, new_file if not dry else old_file)
        text = open(path, encoding="utf-8").read()
        old_dir, new_dir = posixpath.dirname(old_file), posixpath.dirname(new_file)

        def fix_link(m):
            target = m.group(2)
            if target.startswith(("http:", "https:", "mailto:", "#", "/")):
                return m.group(0)
            ref, hashpart = (target.split("#", 1) + [""])[:2]
            if not ref:
                return m.group(0)
            trailing = ref.endswith("/")
            old_abs = posixpath.normpath(posixpath.join(old_dir, ref)) + ("/" if trailing else "")
            new_abs = new_path(old_abs)
            rel = posixpath.relpath(new_abs.rstrip("/") or ".", new_dir or ".") + ("/" if trailing else "")
            out = rel + ("#" + hashpart if hashpart else "")
            return m.group(1) + out + m.group(3)

        new_text = LINK.sub(fix_link, text)

        if not old_file.startswith(keep) and old_file not in keep:
            def fix_tick(m):
                p = m.group(1)
                if p in files:
                    return "`" + files[p] + "`"
                mapped = new_path(p)
                return "`" + mapped + "`" if mapped != p and "/" in p else m.group(0)
            new_text = TICK.sub(fix_tick, new_text)

        if new_text != text:
            changed += 1
            if dry:
                print(f"would rewrite {old_file} -> {new_file}")
            else:
                open(path, "w", encoding="utf-8", newline="\n").write(new_text)
    print(f"{'planned' if dry else 'moved'} {len(files)} files; {'would rewrite' if dry else 'rewrote'} {changed} documents")


if __name__ == "__main__":
    main()
