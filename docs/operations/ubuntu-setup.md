# Ubuntu Setup

Prepares the studio machine. Reference machine (audit 2026-11-03): **Ubuntu 24.04.5 LTS**, Node.js **24.20.0** via nvm (also 16.20.2 and 22.23.2 installed), Git **2.43.0**, GitHub CLI **2.62.0**, Docker 29.9.1 installed but **not used** (ADR-003).

## 1. Requirements

| Component | Minimum | Why | Source |
|---|---|---|---|
| Ubuntu | 24.04 LTS | Reference platform | ADR-003 |
| Node.js | 24.11 | Paperclip requirement; also satisfies OpenSpec (22.12+) | Paperclip `docs/start/architecture.md`; OpenSpec README |
| Git | 2.x with `worktree` | Task Workspaces | ADR-006 |
| GitHub CLI `gh` | 2.62 | PRs, auth | registry `github-cli` |
| Disk | Enough for one Primary Checkout per game plus one worktree per concurrent Task | Worktrees share objects but duplicate working files | — |

## 2. Base packages

Standard Ubuntu packages (skip what is installed):

```bash
sudo apt update
sudo apt install -y git curl ca-certificates build-essential
```

## 3. Node.js via nvm

The machine already uses nvm. Ensure Node 24 is the default for the user that runs Paperclip and agents:

```bash
nvm install 24
nvm alias default 24
node --version    # expect v24.x (>= 24.11)
```

All global npm CLIs (Paperclip via `npx`, OpenSpec, Codex) must be installed under this Node version. Each nvm version has its own global packages. The audit found `openspec` only under v24.20.0.

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

Create the Runtime Data locations from ADR-010 (`PROPOSED` defaults):

```bash
mkdir -p ~/.config/game-studio ~/.local/state/game-studio ~/game-studio-workspace/repos
chmod 700 ~/.config/game-studio ~/.local/state/game-studio
```

`~/game-studio-workspace/worktrees` is needed only if the Runtime owns worktrees (Stage 2).

## 7. Framework Repository under Git

The framework directory is not yet a Git repository (OQ-028). When the Board Operator decides:

```bash
cd ~/game-studio
git init -b main
git remote add origin https://github.com/datpham02/game-studio.git   # after creating it on GitHub
```

This documentation deliberately does not run these commands.

## Related documents
[installation.md](installation.md) · [configuration.md](configuration.md) · [security-operations.md](security-operations.md)
