"""Build a clean Paperclip company package from this repository (docs/operations/company-bootstrap.md).

Stdlib only. Writes nothing to Paperclip. Usage (from the repository root):

    python -I scripts/setup/build-package.py --prefix SOU
    python -I scripts/setup/build-package.py --prefix SOU --out <dir> --workspace <dir>

Sources: knowledge/company/COMPANY.md, knowledge/company/agents/*/AGENTS.md,
knowledge/departments/*/agents/*/AGENTS.md, config/paperclip/agents.json (ADR-019).
The built package is local to this machine: it contains this machine's workspace path and
Cursor CLI path, so it is written outside the repository and never committed.
The generated .paperclip.yaml is block YAML in the shape of Paperclip's own export.

The Review Package reviewer (profile kind "strict-reviewer", Phase 6 W2) is left out unless --with-reviewer is
given, together with --staging-root and --reviewer-cwd. Its built configuration must pass the same
check_reviewer_config that review-start runs; a failure stops the build (nothing is corrected silently).
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


def reviewer_args(profile, staging_root):
    """The strict reviewer's CLI arguments, in the shape validated live in R1, P0 and R5."""
    return ["--no-session-persistence", "--restricted", "--tools", "Read,Grep,Glob", "--strict-mcp-config",
            "--permission-mode", "dontAsk", "--permission-prompts", "none",
            "--settings", os.path.normpath(os.path.join(REPO, profile["settingsFile"])),
            "--add-dir", os.path.normpath(os.path.join(staging_root, "current")),
            "--append-system-prompt", profile["systemPrompt"], "--disallowedTools", "mcp__*"]


def is_strict_reviewer(profile):
    return profile.get("kind") == "strict-reviewer"


def check_reviewer_block(block, staging_root):
    """Run review-start's own check on the built reviewer configuration; refuse, never correct."""
    sys.path.insert(0, os.path.join(REPO, ".claude", "skills", "paperclip", "scripts"))
    import review_pack
    import review_relay
    agent = {"adapterType": block["adapter"]["type"], "adapterConfig": block["adapter"]["config"],
             "runtimeConfig": block["runtime"]}
    try:
        review_relay.check_reviewer_config(agent, staging_root)
    except review_pack.ReviewPackError as e:
        sys.exit(f"the built code-reviewer configuration is refused: {e}")


def adapter_block(profile, agent, rules, prefix, workspace, cursor_cmd, staging_root=None, reviewer_cwd=None):
    sub = lambda xs: [x.replace("{PREFIX}", prefix) for x in xs]
    cfg = dict(profile.get("config", {}))
    cfg["cwd"] = workspace
    if is_strict_reviewer(profile):
        cfg["cwd"] = os.path.normpath(reviewer_cwd)
        cfg["extraArgs"] = reviewer_args(profile, staging_root)
        return {"type": profile["adapter"], "config": cfg}
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


def check_reviewer_paths(a):
    """The reviewer's Staging Root and working folder: given, absolute, outside this repository and the agents'
    workspace, and not inside each other."""
    if not a.staging_root or not a.reviewer_cwd:
        sys.exit("--with-reviewer needs --staging-root and --reviewer-cwd")
    norm = lambda p: os.path.normcase(os.path.abspath(p))  # noqa: E731
    inside = lambda child, parent: norm(child) == norm(parent) or norm(child).startswith(norm(parent) + os.sep)  # noqa: E731
    for name, path in (("--staging-root", a.staging_root), ("--reviewer-cwd", a.reviewer_cwd)):
        if not os.path.isabs(path):
            sys.exit(f"{name} must be an absolute path")
        for other, label in ((REPO, "this repository"), (a.workspace, "the agents' workspace")):
            if inside(path, other) or inside(other, path):
                sys.exit(f"{name} must be outside {label}")
    if inside(a.reviewer_cwd, a.staging_root) or inside(a.staging_root, a.reviewer_cwd):
        sys.exit("--reviewer-cwd and --staging-root must not contain each other")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True, help="issue prefix the new company will get (first 3 letters of its name)")
    p.add_argument("--out", default=os.path.join(HOME, "game-studio-workspace", "package"))
    p.add_argument("--workspace", default=os.path.join(HOME, "game-studio-workspace"), help="agents' cwd and parent of repos/")
    # Paperclip only runs its Cursor hello probe (and so only lets the agent resume) when the command is
    # the default entrypoint `agent` or `cursor-agent`, resolved from PATH (verified 2026-11-05).
    p.add_argument("--cursor-command", default="agent")
    p.add_argument("--with-reviewer", action="store_true", help="include the Review Package code-reviewer (Phase 6)")
    p.add_argument("--staging-root", help="with --with-reviewer: the Review Package Staging Root")
    p.add_argument("--reviewer-cwd", help="with --with-reviewer: an empty folder for the reviewer's working directory")
    a = p.parse_args()

    conf = json.load(open(os.path.join(REPO, "config", "paperclip", "agents.json"), encoding="utf-8"))
    reviewers = {s for s, ag in conf["agents"].items() if is_strict_reviewer(conf["profiles"][ag["profile"]])}
    if a.with_reviewer:
        check_reviewer_paths(a)
    cursor_cmd = a.cursor_command if (shutil.which(a.cursor_command) or os.path.exists(a.cursor_command)) else None
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    os.makedirs(os.path.join(a.out, "company"))
    shutil.copy(os.path.join(REPO, "knowledge", "company", "COMPANY.md"), os.path.join(a.out, "company", "COMPANY.md"))

    role_roots = [os.path.join(REPO, "knowledge", "company", "agents")]
    dept_root = os.path.join(REPO, "knowledge", "departments")
    role_roots += [os.path.join(dept_root, d, "agents") for d in sorted(os.listdir(dept_root))
                   if os.path.isdir(os.path.join(dept_root, d, "agents"))]
    found = {}
    for root in role_roots:
        for d in sorted(os.listdir(root)):
            src = os.path.join(root, d, "AGENTS.md")
            if not os.path.isfile(src):
                continue
            slug = frontmatter_slug(src)
            if slug in found:
                sys.exit(f"duplicate agent slug {slug}: {found[slug]} and {src}")
            found[slug] = src
    missing = set(conf["agents"]) ^ set(found)
    if missing:
        sys.exit(f"agents.json and agents/ disagree on: {sorted(missing)}")
    if not a.with_reviewer:
        for slug in reviewers:  # the reviewer is created only on purpose (Phase 6, step P6-B)
            found.pop(slug)

    ext = {"schema": "paperclip/v1", "schemaVersion": 7, "agents": {}, "projects": {}}
    for slug, src in found.items():
        dst = os.path.join(a.out, "agents", slug)
        os.makedirs(dst)
        shutil.copy(src, os.path.join(dst, "AGENTS.md"))
        agent = conf["agents"][slug]
        block = {
            "adapter": adapter_block(conf["profiles"][agent["profile"]], agent, conf["rules"], a.prefix, a.workspace,
                                     cursor_cmd, a.staging_root, a.reviewer_cwd),
            "runtime": agent.get("runtime", conf["runtime"]),
            "permissions": agent.get("permissions", {}),
        }
        if slug in reviewers:
            if agent.get("secrets"):
                sys.exit(f"{slug} must have no secrets")
            check_reviewer_block(block, a.staging_root)
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
