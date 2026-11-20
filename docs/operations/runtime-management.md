# Runtime Management

How to operate execution day to day. In **Stage 1** "the runtime" is Paperclip plus its adapters. The Game Studio Runtime (Stage 2) is `PLANNED`.

## 1. Stage 1: operating through Paperclip (`VERIFIED` features)

| Task | How |
|---|---|
| Operate Paperclip from Claude Code | Open a Claude Code session in this repository and ask in plain language. The project skill [`.claude/skills/paperclip`](../../.claude/skills/paperclip/SKILL.md) wraps the REST API: `overview`, `show`, `release`, `approve`, `request-changes`, `create`, `assign`, `wake`, `log` |
| Start everything | Double-click `runtime/tools/start-studio.cmd` (or a Desktop shortcut to it). It starts Paperclip and the watchdog in their own windows if they are not already running, then opens the UI. It finds `paperclipai` even when `nvm use` switched to another Node: `PAPERCLIP_NODE_DIR` if set, else `PATH`, else the newest nvm Node folder that has `paperclipai.cmd`; that folder goes first on `PATH` for both windows, so the watchdog also gets Node 24 |
| Start Paperclip | `paperclipai run` from `~/game-studio-workspace` (global install pinned to the registry version; not `npx`, OQ-034) |
| Start the review-wake watchdog | `node runtime/tools/review-wake-watchdog.ts` from the framework repository, while Paperclip runs (OQ-035) |
| Stop Paperclip | Stop the process (Ctrl+C in its terminal, or stop the service if you created one; see §3) |
| See running/finished runs | Paperclip UI: agent run history and live transcript |
| Wake an agent now | UI "Invoke", or `POST /api/agents/{agentId}/heartbeat/invoke` |
| Pause / resume / terminate an agent | UI, or `POST /api/agents/{agentId}/pause` · `/resume` · `/terminate` |
| Clear an agent's error state | `POST /api/agents/{agentId}/clear-error` |
| Inspect execution workspaces | Project / execution-workspace pages in the UI; archive or close when done |

Execution workspaces persist "until a human closes them" (`VERIFIED`). Close a workspace only after its Task is `done`/`cancelled` and its branch is merged or abandoned.

### 1.1 Review-wake watchdog (`IMPLEMENTED`, 2026-11-04)

Paperclip 2026.1023.0 does not wake the next review participant when an agent hands an issue to review from inside its own run (OQ-035). [`runtime/tools/review-wake-watchdog.ts`](../../runtime/tools/review-wake-watchdog.ts) fills that gap:
- Every 60 s it lists `in_review` issues. If the current execution stage waits on an agent that has had no run since the stage started (90 s grace), it wakes that agent with `POST /api/agents/{id}/wakeup`.
- One wake per stage entry, through an idempotency key. It never changes issue state.
- Run it with `node runtime/tools/review-wake-watchdog.ts`; `--once` does a single sweep. It needs Node 24+ for native TypeScript, and Paperclip in `local_trusted` mode on loopback.

## 2. Stage 2: Game Studio Runtime (`PLANNED`)

No command below exists. They describe the intended interface for implementers.

| Intended command | Purpose |
|---|---|
| `game-studio-runtime run` | Entry point invoked by Paperclip's `process` adapter |
| `game-studio-runtime doctor` | Check providers, auth, config, paths, Paperclip reachability |
| `game-studio-runtime recover` | Recovery sweep ([runtime-architecture.md §11](../architecture/runtime-architecture.md#11-restart-and-recovery)) |
| `game-studio-runtime runs list` / `runs show <run-id>` | Inspect Runtime run records |
| `game-studio-runtime workspaces gc` | Clean up worktrees of finished Tasks (never dirty ones) |

## 3. Starting Paperclip automatically (`PROPOSED`)

To start Paperclip when you sign in to Windows, you can use a Task Scheduler task with a logon trigger. This is a standard Windows mechanism, not a Paperclip-documented procedure. Paperclip's own `--install-service` does not work here: its doctor reports "Service management is not supported on win32" (2026-11-03). Test it before relying on it (PowerShell):

```powershell
# Use the full path from: (Get-Command paperclipai).Source
$action  = New-ScheduledTaskAction -Execute "<path-to-paperclipai.cmd>" -Argument "run" -WorkingDirectory "$env:USERPROFILE\game-studio-workspace"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask -TaskName "Paperclip" -Action $action -Trigger $trigger
```

Provider CLIs launched by Paperclip inherit the task's environment. Make sure `PATH` includes `claude` and `codex`. nvm-windows switches Node by changing a symlink, so after `nvm use` the task picks up the new version.

## 4. Capacity

- Keep concurrent Runs ≤ 2 until measured (OQ-015).
- Watch memory with Task Manager (or `Get-Process` in PowerShell) during engine builds.

## Related documents
[logging-and-debugging.md](logging-and-debugging.md) · [troubleshooting.md](troubleshooting.md) · [../architecture/runtime-architecture.md](../architecture/runtime-architecture.md)
