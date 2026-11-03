# Codex Integration

**Provider ID:** `codex_local` · **Verified against:** `codex exec --help` of the Codex binary **0.166.0-alpha.5.1** found on the retired Ubuntu machine (bundled with the ChatGPT desktop app), 2026-11-03. **Codex is not installed on the Windows studio machine**; install the standalone CLI (OQ-009). Latest npm release: `@openai/codex` 0.166.0. Flags may differ slightly between the alpha binary and the stable release; re-verify after installation.

## 1. Role in the studio
Second v1 AI Execution Provider (ADR-008). Stage 1: Paperclip's `codex_local` adapter. Stage 2: Runtime Codex Provider Adapter.

## 2. CLI execution

Non-interactive mode: `codex exec [OPTIONS] [PROMPT]` (`VERIFIED`). If no prompt argument is given, or `-` is used, the prompt is read from stdin (`VERIFIED`).

| Flag | Use in the studio |
|---|---|
| `-C, --cd <DIR>` | Working root = Task Workspace |
| `-s, --sandbox read-only\|workspace-write\|danger-full-access` | Permission profile |
| `--dangerously-bypass-approvals-and-sandbox` | `bypass` profile only |
| `--approve-for-me` | Routes approval requests through automatic review in the `workspace-write` sandbox |
| `-m, --model <MODEL>` | Model override |
| `--json` | JSON event output to stdout |
| `-o, --output-last-message <FILE>` | Write the final message to a file |
| `--output-schema <FILE>` | Structured final output |
| `--add-dir <DIR>` | Extra writable directory |
| `--skip-git-repo-check` | Allow running outside a Git repo (not needed for Task Workspaces) |
| `--ephemeral` | Do not persist the session |
| `--ignore-user-config`, `--ignore-rules` | Isolation from user-level config/rules |
| `-c key=value`, `-p/--profile` | Config overrides / profiles from `~/.codex/` |
| `codex exec resume` | Resume a previous session |

### Recommended invocation (Stage 2, `PROPOSED`)

```bash
codex exec \
  --cd "<task-workspace>" \
  --sandbox workspace-write \
  --json \
  --output-last-message "<run-dir>/last-message.txt" \
  - < prompt.txt
```

What the `workspace-write` sandbox permits on Windows (OQ-032) (network, paths outside the workspace, `.git` writes in a worktree whose Git directory lives in the Primary Checkout) is `UNVERIFIED` (OQ-011). Worktree Git metadata lives outside the worktree directory. Commits may therefore need `--add-dir <primary-checkout>/.git`; verify this before relying on it.

## 3. Authentication assumptions
- Codex reads credentials from `$CODEX_HOME/auth.json` (default `~/.codex/`), not directly from `OPENAI_API_KEY` in the environment (`VERIFIED` via Paperclip `codex_local` docs).
- `codex login` (ChatGPT login), `codex login --with-api-key` (key on stdin), and `codex login status` exist (`VERIFIED`).
- `~/.codex/` exists on the studio machine; login state not inspected (OQ-010).

## 4. Process lifecycle
Same as Claude Code: spawn with cwd/`--cd`, prompt on stdin, stream `--json` output, exit at completion; timeout and grace kill from [runtime-architecture.md §9](../architecture/runtime-architecture.md#9-process-management).

## 5. Working directory
- `--cd` MUST be the Task Workspace.
- Codex loads `AGENTS.md` files from the repository root to cwd, so each Game Repository's `AGENTS.md` is loaded. Paperclip notes that its own instructions file is added on top of repo-local `AGENTS.md` (`VERIFIED`).

## 6. Prompt delivery
- Stdin prompt = role instructions + Task + run constraints (Codex has no `--append-system-prompt` equivalent in `exec --help`). Paperclip's `instructionsFilePath` prepends a file to the stdin prompt (`VERIFIED`).

## 7. Output collection
- `--json`: event stream to stdout (schema `UNVERIFIED`; keep raw logs, parse defensively).
- `-o` gives the final message reliably in a file; `--output-schema` gives structured output.

## 8. Permission handling
Profiles → `--sandbox` mode per [security-architecture.md §4](../architecture/security-architecture.md#4-agent-permissions-provider-level). Paperclip's `dangerouslyBypassApprovalsAndSandbox` is documented as "dev only".

## 9. Failure handling

| Symptom | Class | Action |
|---|---|---|
| `codex` not found | `unavailable` | Install standalone CLI (OQ-009) |
| `401` / missing credentials | `auth_error` | `codex login`; Paperclip fails fast with `adapter_failed` for managed homes without credentials (`VERIFIED`) |
| Rate/usage limit | `quota_or_rate_limit` | Retry on later heartbeat |
| Sandbox denial | `task_failure` | Agent reports; adjust profile only with Board approval |

## Related documents
- [claude-code-integration.md](claude-code-integration.md) · [paperclip-integration.md](paperclip-integration.md) · [../decisions/ADR-008-provider-abstraction.md](../decisions/ADR-008-provider-abstraction.md)
