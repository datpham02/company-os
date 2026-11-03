# Windows Setup

Prepares the studio machine ([ADR-013](../decisions/ADR-013-native-windows-studio-host.md)). Reference machine (audit 2026-11-03): **Windows 11 Pro** (10.0.26100), Node.js **24.22.1** via nvm-windows, Git for Windows **2.47.1**, GitHub CLI **2.97.0**, Claude Code **2.1.316**. Docker Desktop is installed but **not used** (ADR-013).

Commands below are for **Git Bash** unless marked PowerShell. In this documentation `~` means your Windows user profile (`%USERPROFILE%`).

## 1. Requirements

| Component | Minimum | Why | Source |
|---|---|---|---|
| Windows | 11 | Reference platform | ADR-013 |
| Node.js | 24.11 | Paperclip requirement; also satisfies OpenSpec (22.12+) | Paperclip installation docs; OpenSpec README |
| Git for Windows | 2.x with `worktree`, includes Git Bash | Task Workspaces; `sh` for shell commands | ADR-006, ADR-013 |
| GitHub CLI `gh` | 2.62 | PRs, auth | registry `github-cli` |
| Disk | Enough for one Primary Checkout per game plus one worktree per concurrent Task | Worktrees share objects but duplicate working files | — |

Paperclip's docs name no operating system. Whether it runs on native Windows is `UNVERIFIED` (OQ-031).

## 2. Node.js via nvm-windows

The machine already uses nvm-windows. Make sure Node 24 is active for the user that runs Paperclip and agents (PowerShell or Git Bash):

```bash
nvm install 24
nvm use 24
node --version    # expect v24.x (>= 24.11)
```

Install all global npm CLIs (Codex, OpenSpec; Paperclip runs through `npx`) under this Node version. Each nvm-windows version has its own global packages.

## 3. Git settings for worktrees

Long paths are common in game repositories and worktrees. Enable them for Git (standard Git for Windows setting):

```bash
git config --global core.longpaths true
```

Line endings: keep each game repository's own `.gitattributes` authoritative, so agents do not create whole-file line-ending diffs. Behavior of `core.autocrlf` inside Paperclip worktrees is `UNVERIFIED`. Check it in Phase 0 experiment 0.6.

## 4. Git identity for agents

Commits by agents should be distinguishable from the Board Operator's. Recommended (`PROPOSED`): configure identity per Task Workspace or via environment variables in the Agent Instance config:

```text
GIT_AUTHOR_NAME="Game Studio Agent (<agent-id>)"
GIT_AUTHOR_EMAIL=<a noreply address you control>
GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL  (same)
```

These are standard Git environment variables.

## 5. GitHub CLI authentication (Board Operator)

```bash
gh auth login        # interactive, for the Board Operator's own use
gh auth status
```

Agent credentials are separate fine-grained tokens ([security-operations.md](security-operations.md)).

## 6. Directories

Create the Runtime Data locations from ADR-010 (`PROPOSED` defaults, under your user profile):

```bash
mkdir -p ~/.config/game-studio ~/.local/state/game-studio ~/game-studio-workspace/repos
```

On Windows these folders are private to your user account by default. You need `~/game-studio-workspace/worktrees` only if the Runtime owns worktrees (Stage 2).

Keep game repositories on a short path (for example `C:\WorkSpace\...`) to stay clear of the Windows path length limit.

## Related documents
[installation.md](installation.md) · [configuration.md](configuration.md) · [security-operations.md](security-operations.md)
