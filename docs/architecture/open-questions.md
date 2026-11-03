# Open Questions and Conflicts

This register is the single home for **unverified assumptions** (`OQ-NNN`) and **documentation or architecture conflicts** (`C-NNN`). IDs are permanent. Resolved entries stay, with their resolution.

**Research basis (2026-11-03):** Paperclip repository docs at commit `7b8aa60`; npm registry (latest `paperclipai` 2026.1023.0, `@openai/codex` 0.166.0, `@anthropic-ai/claude-code` 2.1.317, `@fission-ai/openspec` 1.16.0, `@playwright/mcp` 0.0.84, `@hoppscotch/mcp-server` 1.0.2); `--help` output of the locally installed Claude Code 2.1.273, Codex 0.166.0-alpha.5.1, and OpenSpec 1.11.0. Docs at `docs.paperclip.ing` were not fetched separately; the repository's `docs/` directory was used as the source.

**Status values:** `Open` · `Partially verified` · `Resolved`.

## Summary

| ID | Question | Status | Blocks |
|---|---|---|---|
| OQ-001 | How should the Runtime communicate with Paperclip? | Partially verified | Runtime Stage 2 |
| OQ-002 | Who owns Task Workspace (worktree) creation, and where do Paperclip's live? | Open | Stage 1 setup, ADR-006 |
| OQ-003 | Does a `process`-adapter agent receive the Task ID and resolved workspace? | Open | Runtime Stage 2 |
| OQ-004 | Task key format and branch naming in Paperclip worktree mode | Open | Branch conventions |
| OQ-005 | How is merge approval made enforceable and checkable? | Partially verified | ADR-009 operation |
| OQ-006 | Can `game-director` be the Paperclip root (CEO) agent? | Partially verified | Studio setup |
| OQ-007 | Can `company/` + `agents/` be imported with `paperclipai company import`? | Open | ADR-012 |
| OQ-008 | Which Paperclip version to pin, and how stable is its API? | Open | Installation |
| OQ-009 | How should Codex CLI be installed (not on PATH)? | Open | Codex provider |
| OQ-010 | How does Codex authenticate in headless runs on this machine? | Partially verified | Codex provider |
| OQ-011 | How well do headless permission modes confine agents? | Open | Security profiles |
| OQ-012 | Are subscription logins acceptable for automated runs (terms, quotas)? | Open | Provider auth |
| OQ-013 | Runtime implementation language | Open (TypeScript proposed) | Runtime Stage 2 |
| OQ-014 | Runtime state store | Open | Runtime Stage 2 |
| OQ-015 | Concurrency and resource limits on this machine | Open | Parallel tasks |
| OQ-016 | Who presses "merge"? | Open (human in GitHub until resolved) | ADR-009 |
| OQ-017 | GitHub credential model for agents | Open | First game project |
| OQ-018 | Who creates new Game Repositories? | Open (Board Operator until resolved) | project-initialization |
| OQ-019 | License of the Framework Repository | Open | Publishing |
| OQ-020 | Where do OpenSpec specs live, and which OpenSpec version? | Open | OpenSpec integration |
| OQ-021 | How to use Claude Code Game Studios without copying it | Open | Dependency evaluation |
| OQ-022 | Engine choice and worktree compatibility | Open | Per project |
| OQ-023 | How do role instructions reach the CLI under Paperclip adapters? | Partially verified | Stage 1 setup |
| OQ-024 | Paperclip deployment mode and installation on this machine | Open | Stage 1 |
| OQ-025 | Backup procedure for Paperclip data | Open | Operations |
| OQ-026 | Is Hoppscotch MCP needed? | Open | Dependency evaluation |
| OQ-027 | Stronger filesystem isolation without Docker | Open | Security |
| OQ-028 | Framework Repository not yet under Git; GitHub account mapping | Open | Everything that needs Git |
| OQ-029 | Overlap with "Paperclip Runner" | Open | ADR-011 |
| OQ-030 | Can one Paperclip agent run concurrent heartbeats for different Tasks? | Open | Parallel tasks |

## Entries

### OQ-001 — Runtime ↔ Paperclip communication mechanism
- **Why it matters:** Defines the Runtime's entry point, auth, and reporting path (ADR-003).
- **Current assumption:** Paperclip's `process` adapter invokes the Runtime per heartbeat; the Runtime reports via REST API (ADR-011 `PROPOSED`).
- **Verified so far:** Paperclip documents adapters `process` (runs a command with `PAPERCLIP_*` env; exit code = success), `http` (webhook), external adapter plugins, and a REST API with run JWTs. No Paperclip feature *requires* an external runtime.
- **Verification method:** Install Paperclip; create a `process` agent running `env | grep PAPERCLIP_ | sed 's/=.*/=<set>/'`; assign a Task; inspect the run log.
- **Impact if incorrect:** Runtime entry point redesigned (plugin or HTTP).
- **Status:** Partially verified.

### OQ-002 — Worktree ownership and location
- **Why it matters:** ADR-006 requires exactly one owner; the brief assigns worktrees to the Runtime, Paperclip already provides them.
- **Current assumption:** Stage 1: Paperclip owns worktrees. Stage 2: decided per gap analysis.
- **Verification method:** In a test company, set a project's execution workspace mode to isolated `git_worktree`; run two Tasks; record paths, branch names, cleanup behaviour; read `server/src/services/workspace-runtime.ts`.
- **Impact if incorrect:** Duplicate worktrees, branch collisions, disk waste.
- **Status:** Open. See C-001.

### OQ-003 — Context passed to `process` adapters
- **Why it matters:** Without the Task ID and resolved workspace, the Runtime must re-discover them.
- **Current assumption:** Env vars listed in Paperclip's `how-agents-work.md` (`PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_RUN_ID`, `PAPERCLIP_TASK_ID`, `PAPERCLIP_WAKE_REASON`, `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, …) are injected for all adapters. Whether `cwd` is the resolved execution workspace for `process` agents is unknown.
- **Verification method:** Same as OQ-001, plus print `pwd` and `git rev-parse --abbrev-ref HEAD`.
- **Impact if incorrect:** Extra API calls; Runtime must own workspaces.
- **Status:** Open.

### OQ-004 — Task key and branch naming
- **Why it matters:** Branch names must be unique, traceable, and human-readable.
- **Current assumption:** Paperclip issues have a human-readable identifier usable as Task Key; the Runtime naming rule is `agent/<agent-id>/<task-key>`.
- **Verification method:** Inspect an issue via `GET /api/issues/{id}`; inspect branch names created by Paperclip worktree mode and whether they are configurable.
- **Impact if incorrect:** Naming convention changes; documentation update only.
- **Status:** Open.

### OQ-005 — Enforceable merge approval
- **Why it matters:** ADR-009 requires approval in Paperclip **and** on GitHub.
- **Verified so far:** Paperclip issue execution policies support `review` and `approval` stages with agent or user participants and an audit trail (`docs/guides/execution-policy.md`). GitHub branch protection can require approving reviews.
- **Open:** Whether Paperclip can block `done` until the PR is merged; whether a GitHub merge can be linked automatically to the Paperclip approval.
- **Verification method:** Configure an issue with an approval stage whose participant is the board user; walk through it; check `executionState`.
- **Impact if incorrect:** Approval stays a manual two-step process (acceptable for v1).
- **Status:** Partially verified.

### OQ-006 — `game-director` as Paperclip root agent
- **Why it matters:** Paperclip agents form "a strict tree hierarchy … every agent reports to exactly one manager (except the CEO)" (`VERIFIED`). The CEO also produces strategy needing board approval.
- **Current assumption:** `game-director` maps to the root (CEO) position, `reportsTo: null`.
- **Verification method:** Create the company; create `game-director` as CEO; confirm role names are free-form.
- **Impact if incorrect:** An extra "CEO" agent is added above `game-director`; ORGANIZATION.md updated.
- **Status:** Partially verified.

### OQ-007 — Importing the studio into Paperclip
- **Why it matters:** Avoids manual re-entry of agents (ADR-012).
- **Verified so far:** `paperclipai company export/import` exist (`docs/cli/control-plane-commands.md`); Agent Companies format uses `COMPANY.md` at the package root and `agents/<slug>/AGENTS.md`.
- **Open:** This repository keeps `COMPANY.md` in `company/`, not at root. Import may need a generated package (`PLANNED` script) or a dry-run may accept it.
- **Verification method:** Run the documented import preview (no writes) against this repository and a generated package.
- **Impact if incorrect:** Agents created manually in the UI.
- **Status:** Open.

### OQ-008 — Paperclip version and API stability
- **Why it matters:** Integration depends on documented endpoints and adapters.
- **Current assumption:** Pin the npm `paperclipai` version used at install time; record it in the dependency registry.
- **Verification method:** Check Paperclip release notes (`releases/` directory in its repo) for API changes before each upgrade.
- **Impact if incorrect:** Broken integration after upgrades.
- **Status:** Open.

### OQ-009 — Codex installation
- **Why it matters:** Codex is a v1 Provider.
- **Found:** No `codex` on PATH. A Codex binary bundled with the ChatGPT desktop app exists at `/usr/lib/chatgpt/resources/codex` (0.166.0-alpha.5.1), and one inside a Cursor extension. The npm package `@openai/codex` (0.166.0) exists.
- **Current assumption:** Install the standalone CLI from the official source and do not rely on app-bundled binaries.
- **Verification method:** Follow the official Codex install instructions; confirm `codex --version` and `codex exec --help`.
- **Impact if incorrect:** Runs break when the desktop app updates.
- **Status:** Open.

### OQ-010 — Codex headless authentication
- **Verified so far:** Paperclip docs state Codex reads credentials from `$CODEX_HOME/auth.json`; `~/.codex/` exists on this machine. `codex login` exists.
- **Verification method:** `codex login status` (check availability in `codex login --help`), then a test `codex exec` in a scratch repository.
- **Status:** Partially verified.

### OQ-011 — Headless permission confinement
- **Why it matters:** Security profiles in [security-architecture.md §4](security-architecture.md#4-agent-permissions-provider-level).
- **Verified so far:** Flags exist: Claude Code `--permission-mode` (`acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`), `--allowedTools`, `--disallowedTools`, `--restricted`, `--dangerously-skip-permissions`; Codex `--sandbox` (`read-only`, `workspace-write`, `danger-full-access`), `--dangerously-bypass-approvals-and-sandbox`. Paperclip's `claude_local` defaults `dangerouslySkipPermissions: true`.
- **Open:** Whether a non-bypass Claude Code headless run blocks on permission prompts or fails; what Codex's `workspace-write` sandbox permits on Linux (network, paths).
- **Verification method:** Scripted experiments in a scratch repository per profile, recording what is blocked.
- **Status:** Open. See C-002.

### OQ-012 — Subscription use in automation
- **Why it matters:** Cost model and compliance.
- **Verification method:** Read current Anthropic and OpenAI terms for the plans in use; decide between subscription login and API keys per Agent Instance.
- **Status:** Open.

### OQ-013 — Runtime language
- **Current assumption:** TypeScript/Node.js (matches Paperclip, its adapter utilities, and installed Node 24).
- **Impact if incorrect:** None until code is written.
- **Status:** Open.

### OQ-014 — Runtime state store
- **Current assumption:** One JSON file per run plus an index file; SQLite if querying becomes necessary.
- **Status:** Open.

### OQ-015 — Concurrency and resources
- **Current assumption:** Max 2 concurrent Runs. Game engines (editor builds, tests) may need much more memory than code-only tasks.
- **Verification method:** Measure memory/CPU of one Run per engine; set limits.
- **Status:** Open.

### OQ-016 — Who merges
- **Current assumption:** The Board Operator merges in the GitHub UI after approving. A Runtime-performed merge after recorded approval is a possible future option needing an ADR.
- **Status:** Open.

### OQ-017 — GitHub credentials for agents
- **Current assumption:** Fine-grained personal access token per studio (or per project), scoped to Game Repositories with Contents and Pull requests read/write; delivered as `GH_TOKEN` via a Paperclip secret binding.
- **Verification method:** Create the token; verify an agent can push a Task Branch and open a PR, and cannot push to a protected Default Branch.
- **Status:** Open.

### OQ-018 — Creating Game Repositories
- **Current assumption:** The Board Operator creates the repository (GitHub UI or `gh repo create`) after the approval step in [project-initialization.md](../../workflows/project-initialization.md).
- **Status:** Open.

### OQ-019 — Framework license
- **Status:** Open. Board Operator decision.

### OQ-020 — OpenSpec placement and version
- **Found:** OpenSpec 1.11.0 installed globally; latest 1.16.0. OpenSpec initializes an `openspec/` directory in a project (`openspec init`).
- **Current assumption:** Each Game Repository has its own `openspec/`. The Framework Repository MAY use OpenSpec for Runtime development.
- **Status:** Open.

### OQ-021 — Claude Code Game Studios
- **Found:** `Donchitos/Claude-Code-Game-Studios` (MIT) is a template meant to be cloned as a project root, providing `.claude/` agents, skills, hooks, and rules for Claude Code.
- **Open:** Using it means copying its `.claude/` content into a *Game Repository* (not this repository), which conflicts with nothing in ADR-007 but overlaps with Game Studio's own role system. Options: reference only; adopt selected skills per game; or not use it.
- **Status:** Open. Registry status `candidate`.

### OQ-022 — Engines and worktrees
- **Why it matters:** Some engines keep large per-checkout caches (e.g. Unity `Library/`) or editor lock files that make many worktrees costly or unsafe.
- **Verification method:** Per engine, create two worktrees and run a headless build in each.
- **Status:** Open.

### OQ-023 — Delivering role instructions under Paperclip adapters
- **Verified so far:** `claude_local` supports `promptTemplate` with `{{agent.name}}`-style variables and injects Paperclip skills via `--add-dir`; `codex_local` supports `instructionsFilePath` (prepended to the prompt). Agent Companies import sets agent instructions from the `AGENTS.md` body.
- **Open:** Whether `claude_local` has an equivalent of `instructionsFilePath`; best way to keep instructions in sync with Git.
- **Status:** Partially verified.

### OQ-024 — Paperclip deployment on this machine
- **Found:** Paperclip not installed. Documented install: `npx paperclipai onboard --yes`; modes `local_trusted` (loopback, no login) and `authenticated` (private/public).
- **Current assumption:** `local_trusted` on loopback for v1.
- **Status:** Open.

### OQ-025 — Paperclip backup
- **Found:** Paperclip uses embedded PostgreSQL by default; `docs/deploy/database.md` exists in the Paperclip repo but was not reviewed for backup commands.
- **Verification method:** Read Paperclip's database and storage deployment docs; test a restore.
- **Status:** Open.

### OQ-026 — Hoppscotch MCP
- **Found:** Official package `@hoppscotch/mcp-server` (1.0.2); configured locally. Useful only for games with HTTP backends.
- **Status:** Open. Registry status `candidate`.

### OQ-027 — Filesystem isolation without Docker
- **Options:** dedicated Unix user; Codex sandbox; Claude Code `--restricted`; `systemd-run --user` with `ProtectHome=` style properties (feasibility for user units `UNVERIFIED`).
- **Status:** Open.

### OQ-028 — Framework Repository Git state
- **Found:** `/home/datpt/game-studio` is not a Git repository and has no remote. The intended remote is `datpham02/game-studio`; the local Unix user is `datpt`. Whether the GitHub repository already exists was not checked (no network calls to GitHub were made).
- **Action:** The Board Operator initializes Git and connects the remote. This documentation work did not do so (constraint: no new repositories, no commits).
- **Status:** Open.

### OQ-029 — "Paperclip Runner"
- **Found:** Paperclip docs mention a "Paperclip Runner" offering native Codex (app server), Claude via ACPX, and OpenCode, selectable per agent instead of the "Legacy runner".
- **Open:** How it differs from `claude_local`/`codex_local` for local execution, and whether it changes ADR-011.
- **Verification method:** Read `docs/specs/agent-config-ui.md` and the Runner sections of Paperclip's docs; inspect the agent configuration UI.
- **Status:** Open.

### OQ-030 — Concurrent heartbeats per agent
- **Why it matters:** Decides whether parallel Tasks for one role need multiple Agent Instances.
- **Current assumption:** One Run per Agent Instance at a time; register extra instances (e.g. `gameplay-programmer-2`) for parallelism.
- **Verification method:** Assign two Tasks to one agent and invoke heartbeats; observe whether runs overlap (Phase 0.6).
- **Impact if incorrect:** Fewer instances needed; org chart simplified.
- **Status:** Open.

## Conflicts

### C-001 — Runtime scope vs. Paperclip built-in execution
- **Documents:** The v1 brief (§2.3: Runtime launches CLIs, manages branches/worktrees; §2.6) vs. ADR-002 ("do not duplicate functionality Paperclip provides") and verified Paperclip features (`claude_local`, `codex_local`, `git_worktree` execution workspaces).
- **Interim rule:** ADR-003 and ADR-006 remain Accepted. ADR-011 (`Proposed`) stages the work so that nothing is duplicated before a gap is shown.
- **Needs:** Board Operator decision on ADR-011.
- **Status:** Open.

### C-002 — Paperclip's default permission bypass vs. security architecture
- **Documents:** Paperclip `claude_local` default `dangerouslySkipPermissions: true` vs. [security-architecture.md §4](security-architecture.md#4-agent-permissions-provider-level).
- **Interim rule:** Bypass only with per-instance Board approval and protected branches.
- **Needs:** OQ-011 results.
- **Status:** Open.

### C-003 — Schema location
- **Documents:** The brief's target structure has both `projects/project-config.schema.yaml` and a `schemas/` directory.
- **Interim rule:** Project schema stays in `projects/` as specified; other schemas go to `schemas/`.
- **Needs:** Board Operator confirmation.
- **Status:** Open.

### C-004 — "Workflow Engine" component
- **Documents:** The brief lists "Workflow Engine or workflow orchestration" as a component; ADR-002 assigns orchestration to Paperclip.
- **Resolution:** No Game Studio workflow engine in v1. Workflows are definitions executed through Paperclip tasks and execution policies ([system-components.md §4](system-components.md#4-workflow-definitions-workflow-orchestration)).
- **Status:** Resolved (documentation), revisit only by ADR.

### C-005 — Number of workflow files
- **Documents:** The brief's target tree lists 4 workflow files; §4.4 requires 12 workflows.
- **Resolution:** The 4 names are kept for their matching workflows; 8 more files are added ([workflows/README.md](../../workflows/README.md)).
- **Status:** Resolved.

## Related documents
- [../conventions.md](../conventions.md) · [../decisions/README.md](../decisions/README.md) · [../guides/implementation-roadmap.md](../guides/implementation-roadmap.md)
