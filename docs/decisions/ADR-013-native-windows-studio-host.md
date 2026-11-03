# ADR-013: Native Windows Studio Host

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Supersedes:** [ADR-003](ADR-003-native-ubuntu-agent-runtime.md)
- **Related:** ADR-004, ADR-010, ADR-011, [runtime-architecture.md](../architecture/runtime-architecture.md), OQ-011, OQ-027, OQ-031, OQ-032

## Context
ADR-003 placed the studio on the Board Operator's Ubuntu 24.04 machine. That machine was a temporary work machine and is no longer used. The studio machine is now the Board Operator's personal computer, which runs **Windows 11 Pro** (verified 2026-11-03).

The Board Operator considered WSL2 Ubuntu on the same computer and chose to run natively on Windows instead.

Facts checked on 2026-11-03:
- Paperclip's installation and five-minute-path docs state only "Node.js 24+" (minimum 24.11.0) and name no operating system. Windows support is neither confirmed nor excluded (OQ-031).
- Node.js 24.22.1 (nvm-windows), Git for Windows 2.47.1, GitHub CLI 2.97.0, and Claude Code 2.1.316 are installed on the machine. Codex CLI and Paperclip are not.
- Git for Windows provides Git Bash (`sh`), which the documented shell examples rely on.

## Decision
- The studio machine is the Board Operator's Windows 11 computer. Paperclip, the Provider CLIs, and (later) the Agent Runtime MUST run natively on Windows, as the Board Operator's own user account.
- Docker and WSL MUST NOT be required in v1.
- Everything else ADR-003 decided still applies:
  - The Agent Runtime lives in this repository under `runtime/`.
  - Its responsibilities are unchanged: receive Tasks, resolve the project, prepare workspaces, launch and supervise Providers, manage Task Branches and worktrees, collect results, report to Paperclip, and recover after a restart.
  - The Paperclip ↔ Runtime mechanism MUST be verified before implementation (OQ-001, ADR-011).
- Paths written as `~/...` in this documentation mean the Windows user profile (`%USERPROFILE%`, for example `C:\Users\<user>`). Runtime Data stays outside the repository, as ADR-010 requires.
- Shell commands in documentation and agent configuration SHOULD work in Git Bash. Commands that need PowerShell MUST say so.
- Any behavior whose Windows support is unverified MUST be marked `UNVERIFIED` and tested in Phase 0 before Stage 1 relies on it. This covers Paperclip itself, the `process` adapter's shell, and Codex sandboxing.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Keep ADR-003 and use WSL2 Ubuntu on the same computer | Matches the existing docs, but adds a second filesystem and environment to manage. The Board Operator chose native Windows. |
| Keep ADR-003 and a separate Ubuntu machine | The only Ubuntu machine was temporary and is no longer available. |
| Docker containers | Already rejected for v1 by ADR-003. |

## Consequences
- Isolation relies on Git worktrees, NTFS permissions of the user account, and each Provider's own permission or sandbox controls. Unix permissions and `systemd` features no longer apply (OQ-027).
- Agent processes can read anything the user account can read. This v1 risk is unchanged from ADR-003.
- Codex's sandbox behaves differently on Windows than on Linux, which is `UNVERIFIED` (OQ-032). Phase 0 experiment 0.7 MUST run on this machine.
- Facts audited on the retired Ubuntu machine (paths, versions) are stale. They MUST be re-verified on the Windows machine before they are recorded as current.
- Machine preparation moves from `ubuntu-setup.md` to [windows-setup.md](../operations/windows-setup.md).
- If Paperclip turns out not to work on native Windows (OQ-031), the Board Operator should reconsider WSL2 through a new ADR.

## Reconsider when
- Paperclip, Claude Code, or Codex cannot run reliably on native Windows, or
- agents need stronger isolation than Windows user permissions and Provider sandboxes give, or
- the studio moves to a different machine or a server.
