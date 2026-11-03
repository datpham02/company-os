# Troubleshooting

Each entry gives symptom → likely cause → fix. Paperclip error semantics are `VERIFIED` from its API docs.

## Providers

| Symptom | Cause | Fix |
|---|---|---|
| `codex: command not found` | Standalone Codex not installed; only app-bundled binaries exist on this machine | Install per [installation.md §2](installation.md#2-codex-cli) |
| Codex run fails with `401 Missing bearer` / `adapter_failed … no Codex credentials provisioned` | Managed `CODEX_HOME` has no `auth.json` | `codex login` on the host so Paperclip can link `auth.json`, or set a per-agent `OPENAI_API_KEY` in the adapter env |
| `claude` works in a terminal but not under Paperclip | Different `PATH`/Node version in the service environment | Use absolute paths; set `PATH` in the service; check `which claude` |
| Claude run aborts asking for permissions / hangs | Non-bypass permission mode in headless run (OQ-011) | Adjust `--allowedTools`; do not switch to bypass without Board approval (C-002) |
| Claude resume error `previous_message_id` 400 | Poisoned session transcript | Paperclip auto-rotates the session (`VERIFIED`); if it loops, see Paperclip's `claude-local` doc |
| Quota / usage-limit messages | Subscription or API limits | Wait for reset; lower concurrency; consider API keys (OQ-012) |

## Paperclip

| Symptom | Cause | Fix |
|---|---|---|
| `409 Conflict` on checkout | Another agent owns the Task | Expected; **do not retry**. Check for duplicate assignment |
| `422` on status update | Invalid transition (e.g. backlog → done) | Follow the lifecycle `backlog → todo → in_progress → in_review → done` |
| `403` | Cross-company access or missing permission | Check the agent's company and key |
| `401` | Missing/expired token | Agents must use `PAPERCLIP_API_KEY` from the current heartbeat |
| UI not reachable | Server not running, or wrong bind | `paperclipai run` from `~/game-studio-workspace`; default `http://localhost:3100` |
| Agent's `npm` commands fail oddly (missing `tsc`, wrong prefix) | Paperclip started through `npx`, so `npm_*` variables leaked into the agent (OQ-034) | Restart with the global `paperclipai run` |
| Issue sits in `in_review` and the reviewer agent never runs | Reviewer not woken after an in-run hand-off (OQ-035) | Keep `runtime/tools/review-wake-watchdog.ts` running |
| Node version error at start | Node < 24.11 | `nvm use 24` |

## Git and workspaces

| Symptom | Cause | Fix |
|---|---|---|
| `fatal: '<branch>' is already checked out at …` | Same branch in two worktrees | Each Task needs a unique Task Branch; reuse the existing worktree for continuation |
| Push rejected to `main` | Branch protection (working as intended) | Push the Task Branch and open a PR |
| Push rejected (non-fast-forward) on Task Branch | Someone else pushed to it | Fetch and merge; never force-push |
| Private repo clone fails in Paperclip | No GitHub token for server-side clone | Add company secret `GITHUB_TOKEN`/`GH_TOKEN`/`PAPERCLIP_GITHUB_TOKEN` (`VERIFIED`) |
| Disk filling up | Many worktrees / engine caches | Close finished execution workspaces; `git worktree prune` after removal |

## Studio-level

| Symptom | Cause | Fix |
|---|---|---|
| Agent edits the wrong repository | Task's project not mapped, or cwd wrong | Verify registry `paperclip.projectId` and the project workspace |
| Agents ignore role instructions | Instructions not delivered to the Provider (OQ-023) | Check `instructionsFilePath`/`promptTemplate`/import |
| Review pile-up | Board approval bottleneck | Expected (ADR-009); `project-manager` limits `in_review` WIP |

## Related documents
[logging-and-debugging.md](logging-and-debugging.md) · [../architecture/open-questions.md](../architecture/open-questions.md)
