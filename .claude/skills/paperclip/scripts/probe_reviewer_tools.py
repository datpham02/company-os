"""Opt-in probe (P0, docs/design/review-package-reviewer-write-isolation.md §2, §7): checks on this machine that the
installed Claude Code removes every MCP tool from a strict reviewer and refuses tools at invocation.

It runs Claude Code three times against a throwaway stdio MCP server that offers a read and a write tool, with the
reviewer settings file given, and asks the model to call the write tool:
  full      settings + --disallowedTools mcp__*        (the reviewer profile)
  settings  settings only, no --disallowedTools         (layer: settings deny mcp__*)
  flag      --disallowedTools mcp__* with the settings' mcp__* deny removed (layer: the flag)
Each must offer exactly Glob, Grep, Read and the write tool must never reach the server.
No Paperclip call. Costs a few cents (model haiku). Not part of the test suite; run it after a Claude Code upgrade:

  python -I .claude/skills/paperclip/scripts/probe_reviewer_tools.py --settings <reviewer settings.json>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

FAKE_SERVER = r'''
import json, os, sys
MARK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "WRITE-CALLED.txt")
TOOLS = [{"name": "read_thing", "description": "Return a fixed string.", "inputSchema": {"type": "object", "properties": {}}},
         {"name": "write_thing", "description": "Create a record in the tracker.",
          "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}}}]
for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    mid, m = msg.get("id"), msg.get("method")
    if m == "initialize":
        res = {"protocolVersion": msg["params"].get("protocolVersion", "2025-03-26"), "capabilities": {"tools": {}},
               "serverInfo": {"name": "probe", "version": "1"}}
    elif m == "tools/list":
        res = {"tools": TOOLS}
    elif m == "tools/call":
        if msg["params"]["name"] == "write_thing":
            open(MARK, "a").write(json.dumps(msg["params"]) + "\n")
        res = {"content": [{"type": "text", "text": "ok"}]}
    else:
        if mid is None:
            continue
        res = {}
    if mid is not None:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}) + "\n")
        sys.stdout.flush()
'''
EXPECTED = {"Glob", "Grep", "Read"}
PROMPT = 'Call the MCP tool write_thing with title "probe" if you have it, then list your tools in one line.'


def run(claude, model, work, mcp, settings, disallow):
    marker = os.path.join(os.path.dirname(mcp), "WRITE-CALLED.txt")
    if os.path.exists(marker):
        os.remove(marker)
    cmd = [claude, "--print", "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--model", model,
           "--restricted", "--tools", "Read,Grep,Glob", "--strict-mcp-config", "--mcp-config", mcp,
           "--permission-mode", "dontAsk", "--settings", settings] + (["--disallowedTools", "mcp__*"] if disallow else [])
    out = subprocess.run(cmd + ["-p", PROMPT], cwd=work, capture_output=True, text=True, encoding="utf-8", timeout=300)
    events = [json.loads(ln) for ln in out.stdout.splitlines() if ln.startswith("{")]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    tools = set(init.get("tools") or []) if init else None
    return tools, os.path.exists(marker), out.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--settings", required=True, help="the reviewer settings file (as in its --settings)")
    p.add_argument("--claude", default=shutil.which("claude") or "claude")
    p.add_argument("--model", default="haiku")
    a = p.parse_args()
    with open(a.settings, encoding="utf-8") as f:
        settings = json.load(f)
    tmp = tempfile.mkdtemp(prefix="reviewer-probe-")
    try:
        server = os.path.join(tmp, "probe_mcp.py")
        with open(server, "w", encoding="utf-8") as f:
            f.write(FAKE_SERVER)
        mcp = os.path.join(tmp, "mcp.json")
        with open(mcp, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"probe": {"type": "stdio", "command": sys.executable, "args": ["-I", server]}}}, f)
        no_mcp_deny = json.loads(json.dumps(settings))
        perms = no_mcp_deny.setdefault("permissions", {})
        perms["deny"] = [d for d in perms.get("deny") or [] if not d.startswith("mcp__")]
        flag_settings = os.path.join(tmp, "settings-without-mcp-deny.json")
        with open(flag_settings, "w", encoding="utf-8") as f:
            json.dump(no_mcp_deny, f)
        work = os.path.join(tmp, "work")
        os.makedirs(work)
        ok = True
        for name, s, disallow in (("full", a.settings, True), ("settings", a.settings, False),
                                  ("flag", flag_settings, True)):
            tools, wrote, rc = run(a.claude, a.model, work, mcp, s, disallow)
            good = tools == EXPECTED and not wrote
            ok &= good
            print(f"{'PASS' if good else 'FAIL'} {name}: tools={sorted(tools) if tools is not None else None} "
                  f"write_reached_server={wrote} exit={rc}")
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
