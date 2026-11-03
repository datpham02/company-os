# Cursor CLI Integration

**Provider ID:** `cursor` (Paperclip adapter type; package `@paperclipai/adapter-cursor-local`) · **Verified against:** `agent --help` of Cursor CLI **2026.10.22-27dcf5f**, installed on the Windows studio machine on 2026-11-03 with the official installer (`irm 'https://cursor.com/install?win32=true' | iex`, from https://cursor.com/docs/cli/installation). Paperclip adapter behavior was read from the installed `@paperclipai/adapter-cursor-local` 2026.1023.0 package and checked with Test Environment; no Task has run through it yet. Labels follow [../conventions.md](../conventions.md).

## 1. Role in the studio
Third AI Execution Provider, added on 2026-11-03 through [add-execution-provider.md](../../workflows/add-execution-provider.md). It is registered as an additional provider. It does not replace Codex (ADR-008).

Main reason to use it: Cursor can run non-Claude models. That gives `qa` a different model from most implementers without needing an OpenAI account. Stage 1: Paperclip's `cursor` adapter. Stage 2: a Runtime Cursor Provider Adapter (`PLANNED`).

## 2. Installation (Windows)

The installer puts the CLI in `%LOCALAPPDATA%\cursor-agent` and adds that folder to the user `PATH`. It installs two equivalent commands, `agent` and `cursor-agent`. Open a new terminal after installing so the new `PATH` applies. The CLI updates itself by default; `agent update` updates manually. The installer notes that Git for Windows (Git Bash) is required for some features.

```powershell
agent --version
agent login            # interactive browser login, done by the Board Operator
```

`--api-key` or the `CURSOR_API_KEY` environment variable authenticate without a browser (`VERIFIED` in `--help`). Store such a key only as a Paperclip secret, never in this repository.

## 3. CLI execution

Non-interactive mode: `agent -p` (`--print`). The help text says it "Has access to all tools, including write and shell" (`VERIFIED`).

| Flag | Use in the studio |
|---|---|
| `-p, --print` | Non-interactive run |
| `--output-format text\|json\|stream-json` | Output format (with `--print`) |
| `--workspace <path>` | Working root = Task Workspace |
| `--model <model>`, `--list-models` | Model choice |
| `--mode plan\|ask`, `--plan` | Read-only modes (no edits) |
| `-f, --force` / `--yolo` | Allow commands unless explicitly denied (`bypass`-like) |
| `--auto-review` | A server-side classifier auto-runs safe tool calls and prompts for the rest |
| `--sandbox enabled\|disabled` | Sandbox mode override |
| `--trust` | Trust the workspace without prompting |
| `--approve-mcps` | Auto-approve MCP servers |
| `--add-dir <path>` | Extra workspace root |
| `-w, --worktree [name]`, `--worktree-base <ref>` | Cursor-managed worktree under `~/.cursor/worktrees/` (not used; Paperclip owns worktrees, ADR-006) |
| `--resume [chatId]`, `--continue` | Resume a session |

## 4. Paperclip `cursor` adapter

The adapter type is `cursor`. The API rejects `cursor_local` with "Unknown adapter type" (`VERIFIED` 2026-11-03). Read from the installed adapter code:
- It runs `agent -p --output-format stream-json --workspace <cwd>`, plus `--resume`, `--model` and `--mode` when set. The prompt goes through stdin.
- Config fields read: `command` (default `agent`; `cursor-agent` also recognized), `cwd`, `model`, `mode`, `extraArgs`/`args`, `instructionsFilePath`, `promptTemplate`, `bootstrapPromptTemplate`, `timeoutSec`, `graceSec`.
- **It adds `--yolo` automatically unless `extraArgs` already contains `--trust`, `--yolo`, `-f` or `--trust=…`.** By default a Paperclip Cursor agent therefore runs every command. To avoid that, put `--trust` in `extraArgs`. How a non-interactive run then handles commands that need approval is `UNVERIFIED` (OQ-033).

## 5. Permission mapping (`PROPOSED`, OQ-033)

| Studio profile | Cursor CLI | Tested headless on Windows (OQ-033) |
|---|---|---|
| `read-only` | `--trust --mode plan` | Reads only; edits and shell refused |
| `workspace-write` | `--trust --auto-review` | Edits allowed; Cursor's server-side classifier decides shell commands (it allowed `git commit`) |
| `workspace-write`, stricter | `--trust` alone | Edits allowed; every shell command refused |
| `bypass` | `--yolo` (the adapter's default) | Everything allowed |

`--sandbox enabled` does not work on Windows: the CLI exits with "Sandbox mode is enabled but not available on this system. Sandbox requires macOS or Linux."

Current Stage 1 setting for `qa`: `extraArgs: ["--trust", "--auto-review"]`, model `gpt-5.3-codex`.

## 6. Failure modes

| Signal | Handling |
|---|---|
| Not logged in | Run `agent login` on the host; Test Environment should report it |
| Model unavailable on the plan | Pick a model from `agent --list-models` |
| Command not found under Paperclip | Paperclip must see `%LOCALAPPDATA%\cursor-agent` on `PATH`; restart Paperclip from a new terminal after installing |

## Related documents
[paperclip-integration.md](paperclip-integration.md) · [claude-code-integration.md](claude-code-integration.md) · [codex-integration.md](codex-integration.md) · [../architecture/security-architecture.md](../architecture/security-architecture.md)
