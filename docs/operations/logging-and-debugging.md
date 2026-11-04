# Logging and Debugging

## 1. Where logs are

| Source | Location | Notes |
|---|---|---|
| Paperclip run transcripts | Paperclip UI (run viewer); stored by Paperclip | Adapters stream stdout to the run log (`VERIFIED`) |
| Paperclip activity log | Paperclip UI | Every mutation is logged (`VERIFIED`) |
| Paperclip server output | Terminal running `paperclipai run` | [runtime-management.md](runtime-management.md) |
| Claude Code debug | `claude --debug-file <path>` (`VERIFIED` flag) | Only when debugging; may contain sensitive data |
| Codex logs | `~/.codex/` (contains `logs_2.sqlite` on this machine) or the Paperclip-managed `CODEX_HOME` per agent | Format internal to Codex |
| Runtime run records (`PLANNED`) | `~/.local/state/game-studio/runs/<run-id>/` (`run.json`, `stdout.log`, `stderr.log`, `prompt.txt`) | Secrets redacted |
| Git state | `git -C <task-workspace> log/status/diff` | Ground truth for what an agent changed |

## 2. Debugging a failed Task, step by step

1. Open the Task in Paperclip. Read the last comments and the run record (exit, error code, cost).
2. Open the run transcript. Find the first error, not the last one.
3. Classify it with [../architecture/runtime-architecture.md §10](../architecture/runtime-architecture.md#10-error-handling).
4. Inspect the Task Workspace with `git status`, `git log --oneline origin/<default>..HEAD`, `git diff`.
5. Reproduce provider problems outside Paperclip in a scratch directory:
   ```bash
   claude -p "Respond with hello." --output-format stream-json --verbose
   echo "Respond with hello." | codex exec --json -
   ```
   (Both are the same probes Paperclip's environment tests use, `VERIFIED`.)
6. Record the cause in the Task ([task-failure-handling.md](../../knowledge/company/workflows/task-failure-handling.md) step 5).

## 3. Logging rules

- Logs MUST NOT contain secrets. Do not enable shell tracing (`set -x`) in agent environments that hold tokens.
- Keep Runtime logs for 30 days (`PROPOSED`), then delete. Paperclip retention follows Paperclip.
- Run IDs, not paths, are what go into Paperclip comments.

## Related documents
[troubleshooting.md](troubleshooting.md) · [runtime-management.md](runtime-management.md)
