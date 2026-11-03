# Claude Code Integration

**Provider ID:** `claude_local` · **Verified against:** locally installed Claude Code **2.1.273** (`claude --help`, 2026-11-03). Latest npm release at that date: `@anthropic-ai/claude-code` 2.1.317. Flags marked `VERIFIED` appear in the installed CLI's help. Behaviour beyond the help text is `UNVERIFIED` unless stated.

## 1. Role in the studio
Claude Code is one of two v1 AI Execution Providers (ADR-008). In Stage 1 Paperclip's `claude_local` adapter launches it. In Stage 2 the Runtime's Claude Provider Adapter may launch it ([runtime-architecture.md §5](../architecture/runtime-architecture.md#5-agent-launcher-and-provider-abstraction)).

## 2. CLI execution

Non-interactive mode is `-p` / `--print` (`VERIFIED`: "Print response and exit"). Relevant flags (all `VERIFIED`):

| Flag | Use in the studio |
|---|---|
| `-p, --print` | Required for headless Runs |
| `--output-format text\|json\|stream-json` | `stream-json` for live parsing; `json` for a single result |
| `--verbose` | Paperclip's environment probe uses it together with `stream-json` |
| `--input-format text\|stream-json` | Prompt on stdin as text (default) |
| `--model <model>` | Per-instance model override |
| `--permission-mode <mode>` | `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan` |
| `--allowedTools` / `--disallowedTools` | Allow/deny lists, e.g. `"Bash(git *)" Edit` |
| `--tools <tools...>` | Restrict the built-in tool set |
| `--restricted` | Removes command-running tools and WebFetch; confines file tools to working dirs |
| `--dangerously-skip-permissions` | Bypass all permission checks (`bypass` profile only) |
| `--add-dir <dirs...>` | Extra readable/writable directories (Paperclip uses it for skills) |
| `--append-system-prompt <prompt>` | Append role instructions to the default system prompt |
| `--system-prompt` | Replace the system prompt (not recommended; loses defaults) |
| `--mcp-config <configs...>`, `--strict-mcp-config` | Per-Run MCP servers; ignore others |
| `--settings` | Load a settings file/JSON for the Run |
| `--max-budget-usd <amount>` | Spending cap for API-key users |
| `--json-schema <schema>` | Structured final output |
| `--session-id`, `-r/--resume`, `--no-session-persistence` | Session control |
| `--bare` | Minimal mode: skips hooks, plugins, auto-memory, CLAUDE.md discovery; auth strictly `ANTHROPIC_API_KEY` |

### Recommended invocation (Stage 2, `PROPOSED`)

```bash
# cwd = Task Workspace; prompt on stdin; no secrets in argv
claude -p \
  --output-format stream-json --verbose \
  --permission-mode acceptEdits \
  --allowedTools "Bash(git status*)" "Bash(git diff*)" "Bash(git add*)" "Bash(git commit*)" "Bash(git push origin agent/*)" \
  --disallowedTools "Bash(git push --force*)" "Bash(sudo *)" \
  --append-system-prompt "$(cat <role-instructions-file>)" \
  < prompt.txt
```

Whether `acceptEdits` plus allowlists lets a headless run finish without blocking on an unanswered permission prompt is `UNVERIFIED` (OQ-011). Allowlist patterns must be adjusted per project's build/test commands.

## 3. Authentication assumptions
- Supported by the CLI: subscription login stored under `~/.claude/`, `ANTHROPIC_API_KEY`, or `CLAUDE_CODE_OAUTH_TOKEN` (the last two `VERIFIED` via Paperclip `claude_local` docs).
- The studio machine has `~/.claude/` (audit 2026-11-03); login state was not inspected.
- Using a subscription login for automated Runs: terms and quotas to be confirmed (OQ-012).
- `--bare` mode ignores OAuth/keychain and requires `ANTHROPIC_API_KEY`.

## 4. Process lifecycle
1. Spawn `claude -p …` with cwd = Task Workspace, prompt on stdin.
2. Stream stdout (JSON lines with `stream-json`) to the run log; parse events.
3. Process exits when the agent finishes or hits a limit. Paperclip uses `maxTurnsPerRun` (default 300) as its own limit; the installed CLI's help does not list a max-turns flag.
4. Timeout → SIGTERM to the process group → grace period → SIGKILL ([runtime-architecture.md §9](../architecture/runtime-architecture.md#9-process-management)).

## 5. Working directory
- cwd MUST be the Task Workspace. Claude Code auto-discovers `CLAUDE.md` from cwd upward (not in `--bare` mode), so each Game Repository's `CLAUDE.md` → `AGENTS.md` is loaded.
- Do not `--add-dir` the home directory or other Game Repositories.

## 6. Prompt delivery
- Task content and run constraints: stdin.
- Role instructions: `--append-system-prompt` (Stage 2) or Paperclip `promptTemplate`/instructions (Stage 1, OQ-023).
- Skills: Claude Code skills/plugins installed per dependency registry; Paperclip adds its own skills via `--add-dir`.

## 7. Output collection
- `--output-format stream-json`: one JSON object per line, ending with a result object containing the final text and usage. The exact event schema is not documented in `--help`; parse defensively and keep raw logs (`UNVERIFIED` schema details).
- `--json-schema` MAY be used to get a machine-readable final report (`status`, `summary`, `branch`, `prUrl`).

## 8. Permission handling
Mapping of studio permission profiles to flags: [security-architecture.md §4](../architecture/security-architecture.md#4-agent-permissions-provider-level). Paperclip's default for `claude_local` is `dangerouslySkipPermissions: true`, which conflicts with the studio default (C-002).

## 9. Failure handling

| Symptom | Class | Action |
|---|---|---|
| `claude` not found | `unavailable` | Fail fast; operator installs ([installation.md](../operations/installation.md)) |
| Auth error / not logged in | `auth_error` | Fail fast; operator runs `claude` interactively to log in |
| Usage/quota limit message | `quota_or_rate_limit` | No retry this Run; Paperclip's adapter has quota-wait logic for ACP runs (`VERIFIED`) |
| Session resume fails | — | Start fresh session (Paperclip does this automatically, `VERIFIED`) |
| Non-zero exit, otherwise | `provider_crash` / `task_failure` | Preserve logs and workspace; report |

## Related documents
- [codex-integration.md](codex-integration.md) · [paperclip-integration.md](paperclip-integration.md) · [../decisions/ADR-008-provider-abstraction.md](../decisions/ADR-008-provider-abstraction.md)
