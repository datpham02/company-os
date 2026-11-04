"""Build a clean Paperclip company package from this repository (docs/operations/studio-bootstrap.md).

Stdlib only. Writes nothing to Paperclip. Usage (from the repository root):

    python -I scripts/setup/build-package.py --prefix SOU
    python -I scripts/setup/build-package.py --prefix SOU --out <dir> --workspace <dir>

Sources: company/COMPANY.md, agents/*/AGENTS.md, config/paperclip/agents.json.
The built package is local to this machine: it contains this machine's workspace path and
Cursor CLI path, so it is written outside the repository and never committed.
The generated .paperclip.yaml is block YAML in the shape of Paperclip's own export.
"""
import argparse
import json
import os
import re
import shutil
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOME = os.path.expanduser("~")


def frontmatter_slug(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = m.group(1) if m else ""
    s = re.search(r"^slug:\s*(\S+)", fm, re.M)
    return s.group(1) if s else os.path.basename(os.path.dirname(path))


def to_yaml(value, indent=0):
    """Block YAML in the shape Paperclip's own export writes (its parser does not read JSON)."""
    pad = " " * indent
    scalar = lambda v: json.dumps(v, ensure_ascii=False) if not isinstance(v, bool) else ("true" if v else "false")
    lines = []
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                if not v:
                    continue
                lines.append(f"{pad}{k}:")
                lines += to_yaml(v, indent + 2)
            elif v is not None:
                lines.append(f"{pad}{k}: {scalar(v)}")
    else:
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines += to_yaml(item, indent + 2)
            else:
                lines.append(f"{pad}- {scalar(item)}")
    return lines


def adapter_block(profile, agent, rules, prefix, workspace, cursor_cmd):
    sub = lambda xs: [x.replace("{PREFIX}", prefix) for x in xs]
    cfg = dict(profile.get("config", {}))
    cfg["cwd"] = workspace
    if profile["adapter"] == "claude_local":
        args = []
        if profile.get("permissionMode"):
            args += ["--permission-mode", profile["permissionMode"]]
        args += ["--allowedTools"] + sub(profile["allowedTools"] + agent.get("extraAllowedTools", []))
        args += ["--disallowedTools"] + sub(profile["disallowedTools"])
        args += ["--append-system-prompt", " ".join(rules[r] for r in profile["rules"])]
        cfg["extraArgs"] = args
    elif profile["adapter"] == "cursor":
        if not cursor_cmd:
            sys.exit("Cursor CLI not found; pass --cursor-command")
        cfg["command"] = cursor_cmd
    return {"type": profile["adapter"], "config": cfg}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True, help="issue prefix the new company will get (first 3 letters of its name)")
    p.add_argument("--out", default=os.path.join(HOME, "game-studio-workspace", "package"))
    p.add_argument("--workspace", default=os.path.join(HOME, "game-studio-workspace"), help="agents' cwd and parent of repos/")
    p.add_argument("--cursor-command", default=os.path.join(os.environ.get("LOCALAPPDATA", ""), "cursor-agent", "agent.cmd"))
    a = p.parse_args()

    conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
    cursor_cmd = a.cursor_command if os.path.exists(a.cursor_command) else None
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    shutil.copytree(os.path.join(REPO, "company"), os.path.join(a.out, "company"),
                    ignore=shutil.ignore_patterns("ORGANIZATION.md", "RULES.md", "OPERATING_MODEL.md"))

    agents_dir = os.path.join(REPO, "agents")
    found = {}
    for d in sorted(os.listdir(agents_dir)):
        src = os.path.join(agents_dir, d, "AGENTS.md")
        if os.path.isfile(src):
            found[frontmatter_slug(src)] = src
    missing = set(conf["agents"]) ^ set(found)
    if missing:
        sys.exit(f"agents.json and agents/ disagree on: {sorted(missing)}")

    ext = {"schema": "paperclip/v1", "schemaVersion": 7, "agents": {}, "projects": {}}
    for slug, src in found.items():
        dst = os.path.join(a.out, "agents", slug)
        os.makedirs(dst)
        shutil.copy(src, os.path.join(dst, "AGENTS.md"))
        agent = conf["agents"][slug]
        block = {
            "adapter": adapter_block(conf["profiles"][agent["profile"]], agent, conf["rules"], a.prefix, a.workspace, cursor_cmd),
            "runtime": conf["runtime"],
            "permissions": agent.get("permissions", {}),
        }
        if agent.get("secrets"):
            block["inputs"] = {"env": {s: {"description": f"{s} for {slug}", "kind": "secret", "requirement": "optional", "default": ""}
                                       for s in agent["secrets"]}}
        ext["agents"][slug] = block

    for slug, pr in conf["projects"].items():
        dst = os.path.join(a.out, "projects", slug)
        os.makedirs(dst)
        with open(os.path.join(dst, "PROJECT.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"---\nname: {json.dumps(pr['name'])}\ndescription: {json.dumps(pr['description'])}\nowner: {json.dumps(pr['lead'])}\n---\n\n{pr['description']}\n")
        ext["projects"][slug] = {
            "leadAgentSlug": pr["lead"],
            "executionWorkspacePolicy": {"enabled": True, "defaultMode": "isolated_workspace", "allowIssueOverride": False,
                                         "workspaceStrategy": {"type": "git_worktree", "baseRef": "main"}},
            "workspaces": {slug: {"name": slug, "sourceType": "local_path", "repoUrl": f"https://github.com/{pr['repo']}.git",
                                  "repoRef": "main", "defaultRef": "main", "isPrimary": True, "visibility": "default"}},
        }
    with open(os.path.join(a.out, ".paperclip.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(to_yaml(ext)) + "\n")
    print(f"package: {a.out}")
    for slug, b in ext["agents"].items():
        print(f"  {slug:20} {b['adapter']['type']:13} secrets={','.join((b.get('inputs') or {}).get('env', {}).keys()) or '-'}")
    print(f"  projects: {', '.join(ext['projects'])}")


if __name__ == "__main__":
    main()
