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

### 1.0 ComfyUI draft script and art-ops (D1, 2026-11-22)

`runtime/tools/comfy-draft.py` generates concept drafts with the local ComfyUI (`~/game-studio-workspace/tools/ComfyUI_windows_portable`, cu126 build for driver 572.83). `game-artist` runs the installed copy, so after changing the script run `Copy-Item runtime/tools/comfy-draft.py "$HOME/game-studio-workspace/tools/comfy-draft.py"`. Output goes to `~/game-studio-workspace/staging/art/<asset_id>/`. `runtime/tools/art-ops.py` (crop, resize, colour-key, trim, canvas, sprite sheet, grade, contact sheet) is copied the same way to `$HOME/game-studio-workspace/tools/art-ops.py`; it uses ComfyUI's embedded Python (Pillow, NumPy). Test: `python -I runtime/tools/comfy-draft.py --asset smoke_test --model flux --prompt "..." --seed 7` (about 30 s on the RTX 3060).

**Release gates for the Art Production v2 pilot (Board, after merging a change to these tools, `agents.json` or the art role files).** These are gates, not suggestions: **no pilot Task is released (`pc.py release`, or an `Auto-release` line) until G1–G6 and G7(a) have passed in order; then exactly one pilot Task is released for G7(b), and the rest only after G7(b) passes**, and their output is recorded in one Board comment on the pilot planning issue. A failed gate stops the sequence; fix it and restart from that gate.

| Gate | Command or action | Pass condition |
|---|---|---|
| G1 Tests | `& "$HOME/game-studio-workspace/tools/ComfyUI_windows_portable/python_embeded/python.exe" -I -s runtime/tools/test_art_ops.py` in the merged checkout | `OK`, no failures (skips listed) |
| G2 Dependency registration | Entries in [dependencies/registry.yaml](../../dependencies/registry.yaml) for every external tool the pilot uses, through [add-external-dependency.md](../../knowledge/company/workflows/add-external-dependency.md): ComfyUI (portable build), its embedded Python with Pillow and NumPy, the checkpoints `sd_xl_base_1.0` and `flux1-schnell-fp8`, PixelFX (exists). Versions and licences read from the installed copies, not guessed. Then `python -I scripts/maintenance/validate-registries.py` and `check-dependencies.py` | Every tool has an entry with status `approved` or `integrated`; 0 registry findings. **Open today** (OQ-049) |
| G3 Runtime installation | `Copy-Item runtime/tools/art-ops.py "$HOME/game-studio-workspace/tools/art-ops.py"` and the same for `comfy-draft.py`; then stop a running ComfyUI server (the Board, from Task Manager or its console) so the next `comfy-draft.py` run starts it with the current flags | Copies in place; no ComfyUI process left from before the copy |
| G4 Installed-tool and model integrity | `Get-FileHash` (SHA256) of each repository wrapper and its installed copy; `git -C <ComfyUI> rev-parse HEAD` and `git -C <ComfyUI> status --short`; `Get-FileHash` of both checkpoints; the embedded Python's Pillow and NumPy versions | Wrappers identical; ComfyUI at the registry commit with a clean status; checkpoint hashes and package versions equal to their registry entries. `check-dependencies.py` skips these entries (no version command), so this gate is their integrity check. All values recorded in the gate comment |
| G5 Permissions | `python -I scripts/setup/check-agent-drift.py --company Soucean` | No `adapterConfig` drift for `game-artist`, `ui-designer`, `gameplay-programmer`, `qa-engineer`. Drift is fixed by the Board to match `agents.json` exactly (UI or `paperclipai agent update`, [company-bootstrap.md](company-bootstrap.md) §5); never widened beyond it |
| G6 Instructions and read-back | `sync-instructions.py --company Soucean --dry-run` (only the PR's role files `would update`), then without `--dry-run`, then `--dry-run` again, then `check-agent-drift.py` | Read-back: every role `current`; drift check reports none |
| G7 Live pilot validation | (a) Smoke run of the installed copy from a scratch folder with `.git`: `info`, `resize --filter nearest` into `art_src/`, `contact --bg …`, one refused path (`..\x.png`); outputs opened with Read. (b) The first pilot Task (L0 or L1, written by the Board from the template) runs end to end | (a) as expected. (b) The plan comment names a lane; evidence is where the Task's evidence rule says; `qa` opens it and records a verdict with the rubric; the Board can read every evidence path. Only then are further pilot Tasks released |

### 1.1 Review-wake watchdog (`IMPLEMENTED`, 2026-11-04)

Paperclip 2026.1023.0 does not wake the next review participant when an agent hands an issue to review from inside its own run (OQ-035). [`runtime/tools/review-wake-watchdog.ts`](../../runtime/tools/review-wake-watchdog.ts) fills that gap:
- Every 60 s it lists `in_review` issues. If the current execution stage waits on an agent that has had no run since the stage started (90 s grace), it wakes that agent with `POST /api/agents/{id}/wakeup`.
- One wake per stage entry, through an idempotency key. It never changes issue state.
- Run it with `node runtime/tools/review-wake-watchdog.ts`; `--once` does a single sweep. It needs Node 24+ for native TypeScript, and Paperclip in `local_trusted` mode on loopback.

### 1.2 Stuck-issue alerts (`IMPLEMENTED`, 2026-11-21; OQ-048)

Paperclip hands a stuck issue to the Board without telling anyone: its liveness recovery can end with "Recovery owner: board", and a reviewer that cannot act leaves the issue `blocked`. Company heartbeats are off and agents cannot read other issues (G-8), so no role notices. The same watchdog process now also sweeps every open issue (`todo`, `in_progress`, `in_review`, `blocked`) of each active company, using the rules in [`runtime/tools/stuck-rules.ts`](../../runtime/tools/stuck-rules.ts):

| Finding | Condition | Action |
|---|---|---|
| `board_recovery` | The issue's active recovery action has `ownerType` `board` | Notify the Board |
| `retry_loop` | The assignee's last 3 runs all `failed`, `timed_out`, `error` or `scheduled_retry` | Notify the Board |
| `blocked` | `blocked`, no open blocker issue, no active run, quiet for 10 min | Notify the Board |
| `idle` | `todo`/`in_progress`, assigned to an agent that is not paused or busy, no active run or scheduled retry, quiet for 15 min | Wake the assignee once; if it is idle again 15 min after that wake, notify the Board. At most one wake per issue per 6 h |
| `dead_run` | A run Paperclip shows as `starting`/`running` whose `processPid` no longer exists on this machine (2 min grace), or with no output (`lastOutputAt`, last confirmed activity, start) for 20 min. Checked first: a dead run counts as active for every other rule | Notify the Board once per run, with the `pc.py cancel-run` command. The watchdog does not cancel it |

- **Board queue (ADR-023):** an issue whose current review or approval stage waits on a user gets a `BOARD` console line and one toast per waiting episode. `--no-board-queue` turns it off.
- **Auto-release (ADR-023):** a `backlog` Task whose description starts with `Auto-release: approved by the Board <date>` is released through `pc.py release <KEY>` (needs `python` on `PATH`, or `--python <exe>`) once all its blockers are `done`. All release guards apply, and a refusal (WIP, Write Set waiting for a merge) is logged once and retried each sweep. A release shows a toast. `--no-auto-release` turns it off. Test with `--once --dry-run`.
- A notice is a console line starting with `ATTENTION` in the watchdog window and a Windows toast. Each stuck episode is notified once; what was done is kept in memory, so restarting the watchdog may notify again.
- It reads issues and runs and calls `POST /api/agents/{id}/wakeup` only. It never changes issue state, reassigns or comments: deciding is the Board's job (`pc.py triage`, which also lists Board-owned recoveries under "Needs the Board").
- Options: `--idle`, `--blocked-grace`, `--retry-loop`, `--wake-cooldown`, `--dead-silence` (seconds or count; `--dead-silence 0` turns the dead-run rule off), `--no-stuck` (review wakes only), `--no-toast`, `--dry-run` (log what it would do).
- Dead runs (SOU-34, 2026-11-21): the agent's process died while Paperclip kept the run `running` and renewed its controller lease, so the issue looked busy and nothing fired. The PID check works only because the watchdog runs on the same machine as Paperclip; a reused PID would hide it until the silence limit.
- `UNVERIFIED`: the full list of run statuses (the retry-loop set is a best guess), whether a legitimately busy run can stay silent for 20 min (raise `--dead-silence` if one is reported falsely), and whether a plain wake helps after a Board-owned recovery (the watchdog only notifies there).

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
