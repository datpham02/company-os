# Backup and Recovery

## 1. What to back up

| Data | Location | Backup method | Criticality |
|---|---|---|---|
| Framework Repository | GitHub `datpham02/company-os` (renamed from `game-studio`, ADR-018) | Git remote is the backup | High |
| Game Repositories | GitHub | Git remote; unpushed Task Branch work is at risk | High |
| Paperclip data (companies, agents, tasks, approvals, run history, secrets) | Paperclip instance directory / embedded PostgreSQL | Procedure `UNVERIFIED` (OQ-025). Read Paperclip's `docs/deploy/database.md` and `storage.md` before relying on any method | High |
| Paperclip company definition | Exportable package | `npx paperclipai company export <company-id> --out <dir>` (`VERIFIED` command) | Medium (configuration only, not task history) |
| Provider credentials | `~/.claude/`, `~/.codex/` | Do **not** back up into shared storage; re-login is the recovery path | — |
| Runtime config (`PLANNED`) | `~/.config/game-studio/` | Copy to private backup (no secrets file) | Low |
| Runtime run records (`PLANNED`) | `~/.local/state/game-studio/` | Optional | Low |
| Task Workspaces | `~/game-studio-workspace/` or Paperclip-managed | Push branches; workspaces themselves are disposable | Low after push |

## 2. Minimum routine (`PROPOSED`)

- Agents push Task Branches at the end of every Run ([development-cycle.md](../../workflows/development-cycle.md) step 8), so the remote holds nearly all work.
- Weekly: `npx paperclipai company export` into a private location outside all repositories.
- Before every Paperclip upgrade: export, and back up the Paperclip data directory once its location and safe-copy procedure are verified (OQ-025).

## 3. Recovery scenarios

| Scenario | Recovery |
|---|---|
| Machine reboot during Runs | Restart Paperclip. Interrupted runs are handled by Paperclip's recovery. Stage 2 Runtime runs its recovery sweep on next invocation. Uncommitted work in Task Workspaces remains on disk. |
| Lost Task Workspace | Recreate from the pushed Task Branch |
| Lost Paperclip data | Re-import the company package (structure only); tasks and history are lost unless the database was backed up |
| Corrupted Primary Checkout | Delete it after confirming no worktree has unpushed commits (`git worktree list`, `git log --branches --not --remotes`); re-clone |
| Lost machine | New machine: [windows-setup.md](windows-setup.md), [installation.md](installation.md), restore Paperclip data, re-login providers |

## Related documents
[runtime-management.md](runtime-management.md) · [../architecture/repository-architecture.md](../architecture/repository-architecture.md)
