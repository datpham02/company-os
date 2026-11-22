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
| G3 Runtime installation | `Copy-Item runtime/tools/art-ops.py "$HOME/game-studio-workspace/tools/art-ops.py"` and the same for `comfy-draft.py` and `comfy-edit.py` (2026-11-22; it imports the `art-ops.py` next to it); then stop a running ComfyUI server (the Board, from Task Manager or its console) so the next `comfy-draft.py` run starts it with the current flags | Copies in place; no ComfyUI process left from before the copy |
| G4 Installed-tool and model integrity | `Get-FileHash` (SHA256) of each repository wrapper and its installed copy; `git -C <ComfyUI> rev-parse HEAD` and `git -C <ComfyUI> status --short`; `Get-FileHash` of both checkpoints; the embedded CPython, Pillow and NumPy versions; the custom-node inventory (`ComfyUI/custom_nodes` listing, `git status --ignored custom_nodes`, and no `extra_model_paths.yaml` adding node paths) | Wrappers identical; ComfyUI at the registry commit with a clean status; checkpoint hashes, CPython, Pillow and NumPy versions equal to their registry entries; `custom_nodes` holds only the upstream-tracked `example_node.py.example` and `websocket_image_save.py`. The nodes ComfyUI actually loads are confirmed from its startup log in G7(a). `check-dependencies.py` skips these entries (no version command), so this gate is their integrity check. All values recorded in the gate comment |
| G5 Permissions | `python -I scripts/setup/check-agent-drift.py --company Soucean` | No `adapterConfig` drift for `game-artist`, `ui-designer`, `gameplay-programmer`, `qa-engineer`. Drift is fixed by the Board to match `agents.json` exactly (UI or `paperclipai agent update`, [company-bootstrap.md](company-bootstrap.md) §5); never widened beyond it |
| G6 Instructions and read-back | `sync-instructions.py --company Soucean --dry-run` (only the PR's role files `would update`), then without `--dry-run`, then `--dry-run` again, then `check-agent-drift.py` | Read-back: every role `current`; drift check reports none |
| G7(d) comfy-edit matte (2026-11-22) | Board installs `birefnet.safetensors` into `ComfyUI/models/background_removal/` (copied from `rnd/models/background_removal/`, SHA256 checked against the `birefnet` registry pin). `python_embeded/python.exe -I -s runtime/tools/test_comfy_edit.py` (20 tests). From a scratch folder with `.git` and the 11 SOU-81 house-style images in `art_src/`: `matte` on each; one run with `--max-leftover 0`; a review sheet of the cut-outs on `#1B2026` | 2026-11-22, repository copy against the running production ComfyUI: tests OK; 11/11 passed, leftover backdrop 0.003–0.137% (spike S7: BiRefNet worst 0.14%), soft edge 2.4–7.6%; the `--max-leftover 0` run exits 1 and writes only `_rejected.png`; `ComfyUI/input/edit/` and `ComfyUI/output/matte_*` empty after each run; sheet clean (no halo, no foot shadow, lantern rings open). **Still to do after merge:** the installed copy and the permission-layer check (`claude -p` with the live `extraArgs`) |
| G7(c) comfy-edit (2026-11-22) | `python_embeded/python.exe -I -s runtime/tools/test_comfy_edit.py` (12 tests). Installed copy from a scratch folder with `.git` and a 16-multiple PNG in `art_src/`: one `img2img` per model (`sdxl`, `flux`), one `inpaint --model sdxl` with an `art-ops mask`; refusals: `inpaint --model flux`, an input outside the roots, an input in `docs/`, a non-multiple-of-16 size, an all-zero mask, a mask of another size, denoise out of range; the same through the agent's permission layer (`claude -p` with the live `extraArgs`) | Tests OK. Each run writes a PNG, a workflow and a provenance JSON with `input_sha256` (and for inpaint `mask_sha256` and `outside_mask_changed: 0`); `ComfyUI/input/edit/` and `ComfyUI/output/edit_*` are empty after each run; every refusal exits non-zero; `/system_stats` still shows `--offline` |
| G7 Live pilot validation | **(a) Runtime smoke tests of the installed copies.** art-ops, from a scratch folder with `.git`: `info`, `resize --filter nearest` into `art_src/`, `contact --bg …`, and refusals (`..` path, a junction, `.git`). Generation: one `comfy-draft.py` run per approved checkpoint (`--model sdxl`, `--model flux`, fixed seed, small size, asset id `g7_smoke`), with ComfyUI started by the wrapper after G3. Rejected invalid arguments: an unknown model, `--count 9`, a size outside the wrapper's limits, an asset id with a path separator. **(b)** The first pilot Task (L0 or L1, written by the Board from the template) runs end to end | (a) art-ops outputs as expected and every refusal exits non-zero without writing. Each generation writes a valid PNG (PNG signature; `art-ops.py info` gives the requested size and an RGB(A) mode; opened with Read), the workflow JSON and a provenance JSON naming the checkpoint file, seed and prompt. **Runtime configuration:** the running ComfyUI's arguments (`/system_stats` `argv`, or the process command line) include `--listen 127.0.0.1` and `--offline`; its startup log lists no custom-node imports beyond `websocket_image_save.py`. Every invalid argument is rejected before ComfyUI is called. **Agent-level permission smoke (added 2026-11-22 after SOU-66):** in a scratch folder with `.git`, run Claude Code headless with the agent's **live** `--allowedTools` and `--disallowedTools` read back from Paperclip (G5) and its permission mode, and ask it to run each allowed art command exactly as the role file spells it (`python -I ~/game-studio-workspace/tools/comfy-draft.py …`, `python -I ~/game-studio-workspace/tools/art-ops.py …`, `node ~/tools/pixelfx/tools/list.mjs …`): each runs; a different script under the same folder is refused. Cover all five rules with each agent's own live args: `game-artist` (`comfy-draft.py`, `art-ops.py`, PixelFX `list.mjs` and `render.mjs` with `--out` inside the evidence folder) and `ui-designer` (`python ~/.claude/skills/ui-ux-pro-max/scripts/search.py …`); negatives: the quoted `$HOME` form, a `..` path, the script without `-I`, another script in the same folder, a chained non-read-only command, and the other role's tool. The PixelFX output boundary is policy only (security-architecture §4) and is recorded, not passed Running the tools from the Board's shell does not exercise the permission layer and does not count (b) The plan comment names a lane; evidence is where the Task's evidence rule says; `qa` opens it and records a verdict with the rubric; the Board can read every evidence path. Only then are further pilot Tasks released |

**Fixed 2026-11-22 (2A prerequisite 1):** `comfy-draft.py` and `comfy-edit.py` now refuse a running server whose `/system_stats` `argv` lacks `--listen 127.0.0.1` or `--offline` (`comfy-edit.py` also checks the version). The earlier limitation, kept for the record: **accepted for the controlled pilot only (review of PR #88):** `comfy-draft.py` reused a ComfyUI server that is already listening on 127.0.0.1:8188 without checking how it was started, so a server started by hand without `--offline` would be used as is. During the pilot the Board checks the running server's arguments at G7(a) and before releasing each pilot Task (process command line or `/system_stats`), and only the wrapper starts ComfyUI. It must be fixed in the wrapper (refuse or restart a server whose `argv` lacks the approved flags) before any Phase 2 permission expansion ([OQ-049](../roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling) item 8).

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
