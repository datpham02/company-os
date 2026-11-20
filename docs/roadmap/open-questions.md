# Open Questions and Conflicts

This register is the single home for **unverified assumptions** (`OQ-NNN`) and **documentation or architecture conflicts** (`C-NNN`). IDs are permanent. Resolved entries stay, with their resolution.

**Research basis (2026-11-03):** Paperclip repository docs at commit `7b8aa60`; npm registry (latest `paperclipai` 2026.1023.0, `@openai/codex` 0.166.0, `@anthropic-ai/claude-code` 2.1.317, `@fission-ai/openspec` 1.16.0, `@playwright/mcp` 0.0.84, `@hoppscotch/mcp-server` 1.0.2); `--help` output of the locally installed Claude Code 2.1.273, Codex 0.166.0-alpha.5.1, and OpenSpec 1.11.0. Docs at `docs.paperclip.ing` were not fetched separately; the repository's `docs/` directory was used as the source.

**Status values:** `Open` · `Partially verified` · `Resolved`.

## Summary

| ID | Question | Status | Blocks |
|---|---|---|---|
| OQ-001 | How should the Runtime communicate with Paperclip? | Partially verified | Runtime Stage 2 |
| OQ-002 | Who owns Task Workspace (worktree) creation, and where do Paperclip's live? | Partially verified | Stage 1 setup, ADR-006 |
| OQ-003 | Does a `process`-adapter agent receive the Task ID and resolved workspace? | Resolved (no) | Runtime Stage 2 |
| OQ-004 | Task key format and branch naming in Paperclip worktree mode | Partially verified | Branch conventions |
| OQ-005 | How is merge approval made enforceable and checkable? | Partially verified (Paperclip side works; GitHub link missing) | ADR-009 operation |
| OQ-006 | Can `director` be the Paperclip root (CEO) agent? | Partially verified | Studio setup |
| OQ-007 | Can `knowledge/company/` + `knowledge/company/agents/` be imported with `paperclipai company import`? | Resolved | — |
| OQ-008 | Which Paperclip version to pin, and how stable is its API? | Open | Installation |
| OQ-009 | How should Codex CLI be installed (not on PATH)? | Resolved | — |
| OQ-010 | How does Codex authenticate in headless runs on this machine? | Partially verified | Codex provider |
| OQ-011 | How well do headless permission modes confine agents? | Resolved (Claude); Cursor in OQ-033 | Security profiles |
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
| OQ-025 | Backup procedure for Paperclip data | Partially verified (backup creation works; restore untested) | Operations |
| OQ-026 | Is Hoppscotch MCP needed? | Open | Dependency evaluation |
| OQ-027 | Stronger filesystem isolation without Docker | Open | Security |
| OQ-028 | Framework Repository not yet under Git; GitHub account mapping | Resolved | — |
| OQ-029 | Overlap with "Paperclip Runner" | Open | ADR-011 |
| OQ-030 | Can one Paperclip agent run concurrent heartbeats for different Tasks? | Resolved (yes) | Parallel tasks |
| OQ-031 | Does Paperclip run on native Windows? | Partially verified (server, import, agent test pass; wizard sign-in fails) | Stage 1, ADR-013 |
| OQ-032 | How do Codex sandboxing and the `process` adapter's shell behave on native Windows? | Partially verified | Codex provider, Runtime Stage 2 |
| OQ-033 | How well do Cursor CLI headless runs confine agents, with and without Paperclip's automatic `--yolo`? | Partially verified | Cursor provider |
| OQ-034 | Paperclip started with `npx` leaks `npm_*` environment variables into agent runs | Resolved | — |
| OQ-035 | Reviewer not woken after an in-run hand-off to an execution stage | Worked around | Stage 1 review flow |
| OQ-036 | Supabase anonymous sign-in, account linking and free-tier limits for the website | Superseded (ADR-021: Laravel + MySQL) | — |
| OQ-037 | Hosting choice: preview deploys per branch, production only on Board action, free tier | Open | Website M6 (ADR-014) |
| OQ-038 | Ad-network approval, placement policy for game pages, and consent requirements | Open | Website ads milestone |
| OQ-039 | Vietnamese legal requirements for a free game website with ads (Decree 147/2024, Decree 13/2023) | Open | Website public launch |
| OQ-040 | How are existing Paperclip agents updated from Git, given that import into an existing company refuses `--collision replace`? | Open | Studio bootstrap, ADR-016 |
| OQ-041 | Does `maxConcurrentRuns: 1` enforce WIP 1 without delaying an agent's review wakes? | Answered from source (not run): wakes are queued, so a busy reviewer's review waits | Task contract, ADR-017 |
| OQ-042 | How can a reviewer be kept from writing to the author's Task Workspace and branch (G-13)? | Open | Security, ADR-006, task-contract §8 |
| OQ-043 | Can the studio run Paperclip in `authenticated` mode on Windows, so that no local process is the Board by default (G-14)? | Partially verified (sandbox, no agent runs): works on Windows and closes keyless Board access; migration and script auth needed | Security, Runtime prerequisites |

## Entries

### OQ-001 — Runtime ↔ Paperclip communication mechanism
- **Why it matters:** Defines the Runtime's entry point, auth, and reporting path (ADR-013).
- **Current assumption:** Paperclip's `process` adapter invokes the Runtime per heartbeat; the Runtime reports via REST API (ADR-011, accepted). Phase 0: the `process` adapter passes no Task ID or workspace, so the Runtime must look both up through the API (OQ-003).
- **Verified so far:** Paperclip documents adapters `process` (runs a command with `PAPERCLIP_*` env; exit code = success), `http` (webhook), external adapter plugins, and a REST API with run JWTs. No Paperclip feature *requires* an external runtime.
- **Verification method:** Install Paperclip; create a `process` agent running `env | grep PAPERCLIP_ | sed 's/=.*/=<set>/'`; assign a Task; inspect the run log.
- **Impact if incorrect:** Runtime entry point redesigned (plugin or HTTP).
- **Status:** Partially verified.

### OQ-002 — Worktree ownership and location
- **Why it matters:** ADR-006 requires exactly one owner; the brief assigns worktrees to the Runtime, Paperclip already provides them.
- **Current assumption:** Stage 1: Paperclip owns worktrees. Stage 2: decided per gap analysis.
- **Verification method:** In a test company, set a project's execution workspace mode to isolated `git_worktree`; run two Tasks; record paths, branch names, cleanup behaviour; read `server/src/services/workspace-runtime.ts`.
- **Impact if incorrect:** Duplicate worktrees, branch collisions, disk waste.
- **Result (experiment 0.6; Paperclip 2026.1023.0 on Windows 11, scratch company "Scratch Lab (Phase 0)", project `scratch-game` with a local Git repository as its primary workspace, 2026-11-03):**
  - Isolated workspaces are an **experimental instance setting**, `enableIsolatedWorkspaces`, off by default (Instance settings → Experimental; API `PATCH /api/instance/settings/experimental`). While it is off, a project's `executionWorkspacePolicy` is ignored and every Task runs in the project's primary checkout (`shared_workspace` / `project_primary`). It was turned on for this instance on 2026-11-03; `enableIsolatedWorkspacesByDefault` stays off.
  - With it on and the project policy `{enabled: true, defaultMode: isolated_workspace, workspaceStrategy: {type: git_worktree, baseRef: main}}`, Paperclip creates one worktree per Task at `<primary-checkout>/.paperclip/worktrees/<ISSUE-KEY>-<title-slug>` on a new branch with the same name, from `main`. Two Tasks started in the same second got two worktrees.
  - Worktrees live **inside** the primary checkout, so `git status` there shows `?? .paperclip/`. Game Repositories MUST ignore `.paperclip/` in `.gitignore`.
  - Cancelling a Task did not remove its worktree or branch. Cleanup behavior is still unknown.
  - `claude_local` runs in the Task's worktree; Paperclip posts a "Workspace Ready" comment with strategy, branch and cwd. `process` agents do not (OQ-003).
- **Result (2026-11-19, source audit of the installed 2026.1023.0; not run):** every run on an issue, including a review-stage participant's, reuses the issue's worktree (OQ-042). The terminal reaper treats `done` and `cancelled` alike and archives a worktree only when it is clean and its merge is verified (`merged_via_pr` / `merged_by_ancestry`), so an unmerged cancelled Task keeps its worktree and branch. Paperclip commits in a worktree only in one repair path (a dirty worktree on the wrong branch is committed to `paperclip/rescue/<issue>/<ts>`) and never pushes.
- **Status:** Partially verified. Stage 1 owner: Paperclip. See C-001.

### OQ-003 — Context passed to `process` adapters
- **Why it matters:** Without the Task ID and resolved workspace, the Runtime must re-discover them.
- **Current assumption:** Env vars listed in Paperclip's `how-agents-work.md` (`PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_RUN_ID`, `PAPERCLIP_TASK_ID`, `PAPERCLIP_WAKE_REASON`, `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, …) are injected for all adapters. Whether `cwd` is the resolved execution workspace for `process` agents is unknown.
- **Verification method:** Same as OQ-001, plus print `pwd` and `git rev-parse --abbrev-ref HEAD`.
- **Impact if incorrect:** Extra API calls; Runtime must own workspaces.
- **Result (experiment 0.5; Paperclip 2026.1023.0 on Windows 11, scratch company "Scratch Lab (Phase 0)", project `scratch-game` with a local Git repository as its primary workspace, 2026-11-03):** A `process` agent ran Git Bash with a script that printed `PAPERCLIP_*` variable names (values hidden), `pwd` and the branch.
  - Injected: `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_RUN_ID`, `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, agent key-pair variables, `PAPERCLIP_RUNTIME_*` tool variables, and scratch/temp directories (`PAPERCLIP_RUN_SCRATCH_DIR`, `PAPERCLIP_TASK_SCRATCH_DIR`, `PAPERCLIP_TMPDIR`). Secret values are redacted in the run log.
  - **Not injected:** `PAPERCLIP_TASK_ID`, `PAPERCLIP_WAKE_REASON`, or any workspace path. The Task must be looked up through the API, for example `GET /api/heartbeat-runs/{runId}/issues`.
  - **cwd is the directory the Paperclip server was started from, even when Paperclip had created an isolated worktree for the Task.** The adapter only uses `adapterConfig.cwd`.
  - A `process` run that does not update its Task is retried automatically (liveness "needs_followup", retry reason `issue_disposition_repair`), so a Runtime behind `process` MUST update the Task through the API.
- **Status:** Resolved. A Stage 2 Runtime behind `process` would have to resolve the Task and its workspace itself (ADR-011).

### OQ-004 — Task key and branch naming
- **Why it matters:** Branch names must be unique, traceable, and human-readable.
- **Current assumption:** Paperclip issues have a human-readable identifier usable as Task Key; the Runtime naming rule is `agent/<agent-id>/<task-key>`.
- **Verification method:** Inspect an issue via `GET /api/issues/{id}`; inspect branch names created by Paperclip worktree mode and whether they are configurable.
- **Impact if incorrect:** Naming convention changes; documentation update only.
- **Result (experiment 0.6, 2026-11-03):** Issues get identifiers `<company prefix>-<n>` (for example `SCR-4`). Paperclip names worktree branches `<ISSUE-KEY>-<title-slug>` (for example `SCR-4-0-6-worktree-probe-c`), not `agent/<agent-id>/<task-key>`. The project policy schema has `workspaceStrategy.branchTemplate`; whether it can produce the ADR-006 convention is untested.
- **Status:** Partially verified.

### OQ-005 — Enforceable merge approval
- **Why it matters:** ADR-009 requires approval in Paperclip **and** on GitHub.
- **Verified so far:** Paperclip issue execution policies support `review` and `approval` stages with agent or user participants and an audit trail (`docs/guides/execution-policy.md`). GitHub branch protection can require approving reviews.
- **Open:** Whether Paperclip can block `done` until the PR is merged; whether a GitHub merge can be linked automatically to the Paperclip approval.
- **Verification method:** Configure an issue with an approval stage whose participant is the board user; walk through it; check `executionState`.
- **Impact if incorrect:** Approval stays a manual two-step process (acceptable for v1).
- **Result (experiment 0.8, 2026-11-03, scratch company):** An issue was created with `executionPolicy: {stages: [{type: review, participants: [{type: agent, agentId: <reviewer>}]}, {type: approval, participants: [{type: user, userId: "local-board"}]}]}` (`local-board` is the Board user in `local_trusted` mode).
  - The implementer committed on its worktree branch and set the issue to `done`. Paperclip then moved it to `in_review`, assigned the reviewer agent and recorded `returnAssignee` = implementer.
  - The reviewer approved with a comment. Paperclip completed the review stage and moved to the approval stage, assigning the issue to the Board user; the UI showed "Approval pending with You". The whole sequence took about one minute.
  - `executionState` tracks `currentStageType`, `completedStageIds`, `lastDecisionId` and `returnAssignee`.
  - Nothing in Paperclip links this approval to a GitHub PR or merge. ADR-009's GitHub side stays manual.
  - First attempt: the implementer ran with the confined Claude CLI profile and could not set the issue to `done` (OQ-011), so the review stage never started. The second attempt used unrestricted ACP agents, in the scratch company only.
  - **Board decision:** A Board comment alone ("Approved") does **not** record a decision; the issue stayed `in_review`. Per Paperclip's `issue-execution-policy` service, the current participant approves by setting the status to `done` **with a comment**; any other status with a comment records `changes_requested` and returns the issue to `returnAssignee`. Setting `done` with a comment completed the approval stage: `status: done`, `executionState.status: completed`, 2 completed stages, `lastDecisionOutcome: approved`. The worktree branch was left unmerged and unpushed; merging stays a separate step (ADR-009).
- **Status:** Resolved for the Paperclip side (review and Board approval work end to end). Still open: no link to GitHub PR review or merge.

### OQ-006 — `director` as Paperclip root agent
- **Why it matters:** Paperclip agents form "a strict tree hierarchy … every agent reports to exactly one manager (except the CEO)" (`VERIFIED`). The CEO also produces strategy needing board approval.
- **Current assumption:** `director` maps to the root (CEO) position, `reportsTo: null`.
- **Verification method:** Create the company; create `director` as CEO; confirm role names are free-form.
- **Impact if incorrect:** An extra "CEO" agent is added above `director`; ORGANIZATION.md updated.
- **Status:** Partially verified.

### OQ-007 — Importing the studio into Paperclip
- **Why it matters:** Avoids manual re-entry of agents (ADR-012).
- **Verified so far:** `paperclipai company export/import` exist (`docs/cli/control-plane-commands.md`); Agent Companies format uses `COMPANY.md` at the package root and `knowledge/company/agents/<slug>/AGENTS.md`.
- **Open:** This repository keeps `COMPANY.md` in `knowledge/company/`, not at root. Import may need a generated package (`PLANNED` script) or a dry-run may accept it.
- **Verification method:** Run the documented import preview (no writes) against this repository and a generated package.
- **Impact if incorrect:** Agents created manually in the UI.
- **Result (2026-11-03, Paperclip 2026.1023.0, Windows):** `npx paperclipai@2026.1023.0 company import . --target new --dry-run` accepts this repository as-is. No generated package is needed. The preview found the company at `knowledge/company/COMPANY.md` and created reporting lines from each agent's `reportsTo` frontmatter (`director` has none, so it is the root). It reported no warnings or errors. Findings:
  - The repository-root `AGENTS.md` (instructions for coding agents working on this repository) is also picked up as an agent with slug `agent`. Imports MUST pass `--agents` with the seven role slugs to exclude it.
  - Agents without an explicit adapter are created with `claude_local`. Codex roles must be switched after import.
  - Imported agents have budget `0` and empty adapter config. `cwd`, permissions (`dangerouslySkipPermissions`, C-002), and budgets must be set after import.
  - The package bundles all 76 repository files, not only company and agent files.
- **Result (2026-11-03, real import):** `company import . --target existing -C <company-id> --agents director,producer,project-manager,game-designer,gameplay-programmer,ui-designer,qa --yes` created the 7 agents in the existing company and left the company unchanged. This also bypasses the onboarding wizard's sign-in step, which fails on Windows (OQ-031). Reporting lines match [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md); `director` has no manager. Each agent got `adapterType: claude_local`, an `instructionsFilePath` pointing at a copy of its `AGENTS.md` inside Paperclip's data directory, heartbeat disabled, `maxConcurrentRuns: 20`, budget `0`, and permissions `canCreateAgents: true` and `canCreateSkills: true`.
  - Instructions are copied, not linked. Edits to `agents/*/AGENTS.md` in Git need a re-import (`--collision replace`) to reach Paperclip.
- **Status:** Resolved (import works; keeping instructions in sync is tracked in OQ-023).

### OQ-008 — Paperclip version and API stability
- **Why it matters:** Integration depends on documented endpoints and adapters.
- **Current assumption:** Pin the npm `paperclipai` version used at install time; record it in the dependency registry.
- **Verification method:** Check Paperclip release notes (`releases/` directory in its repo) for API changes before each upgrade.
- **Impact if incorrect:** Broken integration after upgrades.
- **Status:** Open.

### OQ-009 — Codex installation
- **Why it matters:** Codex is a v1 Provider.
- **Found:** On the retired Ubuntu machine, no `codex` was on PATH; only app-bundled binaries existed. On the Windows studio machine (2026-11-03), `codex` is not installed at all. The npm package `@openai/codex` (0.166.0) exists.
- **Current assumption:** Install the standalone CLI from the official source and do not rely on app-bundled binaries.
- **Verification method:** Follow the official Codex install instructions; confirm `codex --version` and `codex exec --help`.
- **Impact if incorrect:** Runs break when the desktop app updates.
- **Result (2026-11-03):** `npm install -g @openai/codex` on the Windows studio machine installed `codex-cli 0.166.0` on PATH (npm global folder). Login is still pending (OQ-010).
- **Status:** Resolved.

### OQ-010 — Codex headless authentication
- **Verified so far:** Paperclip docs state Codex reads credentials from `$CODEX_HOME/auth.json`; `~/.codex/` exists on this machine. `codex login` exists.
- **Verification method:** `codex login status` (check availability in `codex login --help`), then a test `codex exec` in a scratch repository.
- **Result (2026-11-03, Windows):** `codex login --with-api-key` (key read from stdin) stores the key; `codex login status` reports "API key configured" and notes that authentication is checked only on the first request. A test `codex exec --sandbox read-only` in a scratch repository reached the OpenAI API and failed with "Quota exceeded. Check your plan and billing details." The API account has no usable credit yet. ChatGPT sign-in (`codex login`) asked for phone verification and was rate-limited.
- **Status:** Partially verified.

### OQ-011 — Headless permission confinement
- **Why it matters:** Security profiles in [security-architecture.md §4](../architecture/security-architecture.md#4-agent-permissions-provider-level).
- **Verified so far:** Flags exist: Claude Code `--permission-mode` (`acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`), `--allowedTools`, `--disallowedTools`, `--restricted`, `--dangerously-skip-permissions`; Codex `--sandbox` (`read-only`, `workspace-write`, `danger-full-access`), `--dangerously-bypass-approvals-and-sandbox`. Paperclip's `claude_local` defaults `dangerouslySkipPermissions: true`.
- **Open:** Whether a non-bypass Claude Code headless run blocks on permission prompts or fails; what Codex's `workspace-write` sandbox permits on Windows (network, paths; see OQ-032).
- **Verification method:** Scripted experiments in a scratch repository per profile, recording what is blocked.
- **Result, Claude Code CLI (Phase 0 experiment 0.7, 2026-11-03, Claude Code 2.1.316, Windows 11):** `claude -p` in a scratch Git repository. The task was to read a file, edit it, then run a shell command (once `git status --short`, once `git commit`). Each case had a 150 s timeout.
  | Flags | Read | Edit | Read-only shell (`git status`) | Writing shell (`git commit`) |
  |---|---|---|---|---|
  | none (default) | allowed | denied | allowed | — |
  | `--permission-mode plan` | allowed | denied | allowed | — |
  | `--permission-mode acceptEdits` | allowed | allowed | allowed | denied |
  | `--permission-mode acceptEdits --allowedTools "Bash(git -c *)"` | allowed | allowed | allowed | allowed |
  | `--permission-mode dontAsk --allowedTools Read Edit` | allowed | allowed | — | denied |
  - **No run hung.** A denied action is skipped, the agent says so in its answer, and the process exits `0`. The exit code therefore does not show that something was denied.
  - Read-only shell commands such as `git status` run even without an allowlist entry.
  - Plan mode writes a plan file under `~/.claude/plans/`, outside the repository.
  - On Windows, Claude Code's PowerShell tool failed every time with "The command line is too long". The agent then ran the same command through Bash (Git Bash). Allowlists must use `Bash(...)` patterns.
- **Result, Paperclip `claude_local` (read from installed Paperclip 2026.1023.0 code, not yet exercised in a run):** The default execution engine is ACP. Under ACP, tool permissions come from `adapterConfig.permissionMode` (default `approve-all`) and `adapterConfig.nonInteractivePermissions` (default `deny`). Supported modes in the bundled runner are `approve-all`, `approve-reads` (reads approved; other requests follow `nonInteractivePermissions`), and `deny-all`. The "Skip permissions" switch (`dangerouslySkipPermissions`) only affects the Claude CLI engine (`--dangerously-skip-permissions`) and the login probe. **So with the default ACP engine, turning "Skip permissions" off does not restrict the agent: every permission request is approved.** Restricting an agent needs either `permissionMode: approve-reads` / `deny-all` under ACP, or the Claude CLI engine plus `extraArgs` such as `--permission-mode acceptEdits --allowedTools ...`. Both still need a test run through Paperclip.
- **Result, Paperclip run with `permissionMode: approve-reads` (experiment 0.7b, 2026-11-03):** A `claude_local` agent (ACP engine, `nonInteractivePermissions: deny`) got a Task to read `game.py`, edit it, commit, then comment and close the Task.
  - Read: allowed. `git status`: allowed. **Edit: refused** ("User refused permission to run tool"); the file was unchanged.
  - **Every write to the Paperclip API was refused too** (comment, interaction, status update), because they go through the shell. The agent could not report or close its Task. Paperclip still posted the agent's final message as a comment, then scheduled retries (`issue_disposition_repair`) that had to be cancelled by hand.
  - The run created an untracked `.claude/` directory in the worktree.
  - Conclusion: `approve-reads` confines file edits, but it is unusable for any agent that must report through Paperclip, including the planning roles. A usable profile must allow the agent's Paperclip API calls while still limiting edits and other commands. Candidate: Claude CLI engine with `--permission-mode acceptEdits` and an `--allowedTools` list, still to be tested through Paperclip.
- **Result, Paperclip run on the Claude CLI engine (experiments 0.7c and 0.7d, 2026-11-03):** `adapterConfig: {engine: "cli", dangerouslySkipPermissions: false, extraArgs: [...]}`, same Task plus a `git push` step that should be refused.
  - **0.7c**, `--permission-mode acceptEdits --allowedTools "Bash(curl *)" "Bash(cat *)" "Bash(git status*)" "Bash(git diff*)" "Bash(git log*)" "Bash(git add*)" "Bash(git commit*)" --disallowedTools "Bash(git push*)"`:
    - Edit, `git status` and commit: allowed. `git push`: denied by the rule.
    - Reporting to Paperclip still failed. Claude Code rejects any command that contains a shell variable ("A variable in this command can't be checked before it runs"), so `curl` with `$PAPERCLIP_API_URL` / `$PAPERCLIP_API_KEY` cannot run even though `curl` is allowed. The Paperclip skill's helper `scripts/paperclip-issue-update.sh` "requires approval". The Paperclip MCP tools were "not granted". Paperclip then scheduled retries.
  - **0.7d**, the same flags plus `"Bash(*paperclip-issue-update.sh*)" "Bash(*paperclip-upload-artifact.sh*)" "mcp__Paperclip_projects"` in `--allowedTools`: **everything worked as intended.**
    - Edit, `git status` and commit: allowed. `git push`: denied.
    - The agent posted its results through `paperclip-issue-update.sh` and set the Task to `done`, so no retry was scheduled. Its first helper call, with `$PAPERCLIP_TASK_ID`, hit the variable check; it then passed the literal issue ID.
    - The Paperclip skill also requires a `Co-Authored-By: Paperclip <noreply@paperclip.ing>` trailer, so the agent amended its commit.
  - **Repeat (experiment 0.8, first attempt):** With the same profile, the agent edited and committed, but did not call the helper script directly. It wrote its own wrapper script (`bash .pc-finish.sh`), which "requires approval", and its `curl` calls hit the variable check. It never reported, and the issue ended `blocked`. **So the profile works only when the agent happens to call the helper directly: 1 of 2 runs.** It is not reliable yet. Options still to test: tell the agent in its instructions to call `paperclip-issue-update.sh` directly with literal IDs; or find a Paperclip MCP tool for issue updates that can be allowlisted.
  - **Fix (2026-11-03): reporting rule.** The profile now adds `--append-system-prompt` with a rule: call `paperclip-issue-update.sh` directly as one standalone command, with literal IDs, no shell variables, no wrapper scripts and no chaining. Retested in the scratch company:
    - `workspace-write`: 3 Tasks in parallel (each edits `README.md` and commits). **3/3 closed themselves `done` in a single run each.**
    - `read-only`: 2 Tasks (each reads a file and tries an edit). **2/2: edit refused, file unchanged, results reported, issue `done` in a single run.**
  - The profile (security-architecture.md §4, `PROPOSED`) is applied to the six `claude_local` agents of the studio company. For `read-only` roles, the candidate is the same allowlist without `--permission-mode acceptEdits` and without the `git add` / `git commit` entries. That variant is untested.
- **Status:** Resolved for `claude_local` on Windows: reporting rule + CLI profile, 5/5 runs after the fix. Cursor: OQ-033. See C-002.

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
- **Result (2026-11-03):** A fine-grained token limited to `datpham02/lamplight-vigil` (Contents and Pull requests read/write, 90-day expiry) is stored as the Paperclip company secret `GH_TOKEN` (provider `local_encrypted`). It is bound as `env.GH_TOKEN` (`secret_ref`, version `latest`) to `game-designer`, `gameplay-programmer` and `ui-designer`. `qa` is not bound yet; that needs a Board decision. The game repository's local clone uses `credential.helper = !gh auth git-credential`, so `git push` and `gh` both use `GH_TOKEN` when it is set.
- **Result (GAM-2, 2026-11-04):** `gameplay-programmer` pushed its task branch with the bound token. `gh pr create` first failed with "Resource not accessible by personal access token": the token had been created without Pull requests permission. After the Board added **Pull requests: Read and write** (editing a fine-grained token keeps its value, so the Paperclip secret did not change), the agent opened PR datpham02/lamplight-vigil#1. Branch protection then requires one approval, and the PR author is the account itself, so merging needs the owner's admin bypass in the GitHub UI.
- **Status:** Resolved for the first Game Repository.

### OQ-018 — Creating Game Repositories
- **Current assumption:** The Board Operator creates the repository (GitHub UI or `gh repo create`) after the approval step in [project-initialization.md](../../knowledge/company/workflows/project-initialization.md).
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
- **Found (2026-11-03):** Imported `claude_local` agents get `instructionsFilePath`, so the equivalent exists. It points at a copy inside Paperclip's data directory (OQ-007).
- **Open:** Best way to keep instructions in sync with Git.
- **Status:** Partially verified.

### OQ-024 — Paperclip deployment on this machine
- **Found:** Paperclip not installed. Documented install: `npx paperclipai onboard --yes`; modes `local_trusted` (loopback, no login) and `authenticated` (private/public).
- **Current assumption:** `local_trusted` on loopback for v1.
- **Status:** Open.

### OQ-025 — Paperclip backup
- **Found:** Paperclip uses embedded PostgreSQL by default; `docs/deploy/database.md` exists in the Paperclip repo but was not reviewed for backup commands.
- **Verification method:** Read Paperclip's database and storage deployment docs; test a restore.
- **Backup observed (2026-11-20, D-STEP2-01):** `POST /api/instance/database-backups` (instance admin) created a gzip SQL dump in the instance's `data/backups` folder, verified with `gzip -t`; the same call pruned 35 older files under the retention policy (7 daily, 4 weekly, 1 monthly). See [step2-board-decisions.md](step2-board-decisions.md) §6a. **No restore has been tested** (verification case VA-9 in [auth-migration-verification-plan.md](../architecture/auth-migration-verification-plan.md)).
- **Phase A.4 (2026-11-20):** a manual backup also works with automatic backups disabled. Paperclip 2026.1023.0 has **no user-facing restore command**: its restore routine is used only inside `worktree init`, which snapshots a running instance. A restore of a backup file is therefore not a supported procedure; see [auth-migration-phase-a4-verification.md](../architecture/auth-migration-phase-a4-verification.md) VA-9. Backup creation alone is not proof of recoverability.
- **Board decision D-AUTH-10 (2026-11-20):** a backup does not establish recoverability; E8 stays unmet until a restore is verified; no improvised restore against the live instance. Restore planning is workstream WS-1 of [auth-migration-phase-a5-plan.md](../architecture/auth-migration-phase-a5-plan.md); nothing executed.
- **WS-1.1 research (2026-11-20, source, docs and issues; nothing executed):** see [auth-migration-ws1-restore-research.md](../architecture/auth-migration-ws1-restore-research.md).
  - No Paperclip version up to v2026.1117.0, nor `master`, has a supported database restore. Paperclip's documentation names what disaster recovery needs (the database, the secrets master key and the object store) but gives no procedure.
  - On this machine every backup uses the JavaScript engine, because no `pg_dump` or `psql` is installed. Open upstream issue #17854 reports that restoring such a backup drops all CHECK constraints.
  - Candidates for an isolated test, both unsupported: a cold copy of the stopped instance folder (recommended first), or a dump made with `pg_dump` 18 and then restored.
  - Still open; E8 is not met.
- **Status:** Partially verified (backup creation only).

### OQ-026 — Hoppscotch MCP
- **Found:** Official package `@hoppscotch/mcp-server` (1.0.2); configured locally. Useful only for games with HTTP backends.
- **Status:** Open. Registry status `candidate`.

### OQ-027 — Filesystem isolation without Docker
- **Options (Windows, ADR-013):** a dedicated local Windows user for agents with NTFS access only to the Workspace Root; Codex sandbox; Claude Code `--restricted`. Feasibility with Paperclip, which launches agents as its own user, is `UNVERIFIED`.
- **Related (2026-11-20):** risk R8, the workspace folder that grants Modify to all Authenticated Users, is to get a remediation plan under D-AUTH-15 (workstream WS-6 of [auth-migration-phase-a5-plan.md](../architecture/auth-migration-phase-a5-plan.md)). No ACL was changed.
- **Status:** Open.

### OQ-028 — Framework Repository Git state
- **Found (2026-11-03):** The repository is under Git with remote `git@github.com:datpham02/game-studio.git`; documentation v1.0 is pushed as commit `9d8ebb6`.
- **Status:** Resolved.

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
- **Result (experiment 0.6, 2026-11-03):** Yes. One `process` agent ran two Tasks in parallel (runs started in the same second). Agents default to `runtimeConfig.heartbeat.maxConcurrentRuns: 20`. Extra Agent Instances are not needed for parallelism; a lower limit may be needed for cost or machine load (OQ-015).
- **Status:** Resolved.

### OQ-031 — Paperclip on native Windows
- **Why it matters:** ADR-013 runs the studio natively on Windows 11.
- **Found:** Paperclip's installation and five-minute-path docs require Node.js 24.11+ and name no operating system. The managed install uses `~/.paperclip` and `~/.local/bin`.
- **Verification method:** Phase 0 C2: `npx paperclipai onboard --yes`, `npx paperclipai run`, open the UI, then run one `claude_local` heartbeat.
- **Impact if incorrect:** Reconsider WSL2 through a new ADR (see ADR-013, "Reconsider when").
- **Result (2026-11-03):** `npx paperclipai@2026.1023.0 onboard --yes --bind loopback --no-install-service` on Windows 11 passed its doctor checks (11 passed, 1 warning: no LLM provider configured, which is optional). It created `~/.paperclip/instances/default`, started embedded PostgreSQL on port 54329, applied migrations, and served the UI on `127.0.0.1:3100` in `local_trusted` mode. The doctor reports "Service management is not supported on win32. Use paperclipai run instead." An agent heartbeat on Windows is not yet tested.
- **Result (2026-11-03, onboarding wizard):** The "Connect a model" step (Claude subscription, browser sign-in) fails on Windows with "Browser sign-in requires Python 3 and a working local terminal." Cause, read from Paperclip's installed code (`@paperclipai/server` `local-ai-browser-login.js`): it spawns `python3` and uses Python's `pty` module to drive the provider CLI login. There is no `python3` command on this machine, and `pty.fork` is not available on Windows anyway, so this sign-in path cannot work on native Windows. The host's Claude Code is already logged in (`claude auth status`: `claude.ai`). Agents created by `company import` skip the wizard (OQ-007).
- **Result (2026-11-03, Test Environment, `director`):** "Connection successful". The agent page reports "Existing authentication — not managed by Connections", so the agent uses the host's Claude login. Test details: execution engine ACP (`claude-agent-acp` from the npx cache; `engine=cli` selects the Claude Code CLI lane), Node 24.22.1 accepted, `ANTHROPIC_API_KEY` not set, "Claude login probe succeeded". The working directory defaulted to the directory Paperclip was started from, which here was this framework repository. Agents MUST get a game repository or project workspace as `cwd` before they receive Tasks.
- **Result (2026-11-03, all 7 agents):** "Skip permissions" is off for all seven. "Can create new agents" and "Can assign tasks" are off for the leaf roles (`game-designer`, `gameplay-programmer`, `ui-designer`, `qa`). They stay on for `director`, `producer` and `project-manager`, which must assign Tasks; hiring is gated by "Require board approval for new hires". Test Environment passed for all seven. The changes were made through the same API the UI uses: `PATCH /api/agents/{id}` merges `adapterConfig` unless `replaceAdapterConfig` is set, and permissions go through `PATCH /api/agents/{id}/permissions`.
- **Other settings seen in the UI:** a per-agent "Skip permissions" switch (on by default after import; turned off for `director`), "Extra args", "Max turns per run" (default 1000), "Heartbeat on interval" (off). In company settings: "Require board approval for new hires" (turned on 2026-11-03) and automatic hourly database backups with configurable retention (relevant to OQ-025). In agent permissions: "Can create new agents", which also grants task assignment authority; "Can assign tasks" is enabled automatically while it is on.
- **Status:** Partially verified.

### OQ-032 — Codex sandbox and `process` shell on Windows
- **Why it matters:** Security profiles (OQ-011) and the Stage 2 entry point (ADR-011) assume Linux behavior.
- **Open:** What Codex `--sandbox workspace-write` enforces on Windows; which shell Paperclip's `process` adapter uses on Windows, and whether `sh -c` (Git Bash) works there.
- **Verification method:** Phase 0 experiments 0.5 and 0.7 on the Windows studio machine.
- **Result (experiment 0.5, 2026-11-03):** The `process` adapter starts `command` directly with `args`, not through a shell. On this machine `bash` resolves to `C:\WINDOWS\system32\bash.exe` (the WSL launcher), not Git Bash. A `process` agent must therefore use the full Git Bash path (`C:\Program Files\Git\bin\bash.exe`) as `command`, with `["-c", "..."]` as `args`. That worked (bash 5.2.37). Codex sandbox behavior is still untested.
- **Status:** Partially verified.

### OQ-033 — Cursor CLI permission confinement
- **Why it matters:** Cursor CLI was added as a third provider on 2026-11-03 ([cursor-integration.md](../integrations/cursor-integration.md)). Paperclip's `cursor` adapter adds `--yolo` unless `extraArgs` contains `--trust`, `--yolo` or `-f`.
- **Open:** In `agent -p` runs on Windows, what is allowed and denied with `--trust` alone, `--mode plan`, `--sandbox enabled` and `--auto-review`; whether a run hangs on an approval; and whether `--trust` in `extraArgs` reaches the CLI through Paperclip.
- **Verification method:** Repeat experiment 0.7 with the Cursor CLI in a scratch repository, then one Test Environment and one run through Paperclip.
- **Result (2026-11-03, Cursor CLI 2026.10.22-27dcf5f, Windows, model `gpt-5.3-codex-low`):** `agent -p` in a scratch repository with the same task as experiment 0.7 (read, edit, `git commit`), 180 s timeout:
  | Flags | Read | Edit | `git commit` | Notes |
  |---|---|---|---|---|
  | `--trust` | allowed | allowed | refused | 78 s; the agent retried the command before giving up |
  | `--trust --mode plan` | allowed | refused | refused | |
  | `--trust --sandbox enabled` | — | — | — | Exit 1: "Sandbox mode is enabled but not available on this system. Sandbox requires macOS or Linux." |
  | `--trust --auto-review` | allowed | allowed | allowed | Cursor's server-side classifier decided |
  | `--yolo` | allowed | allowed | allowed | Paperclip's default |
  | `--trust` + `.cursor/cli.json` `{"permissions":{"allow":["Shell(git)"]}}` | allowed | allowed | refused | The project allowlist had no effect in this form |
  - No run hung. Refusals are reported in the answer and the process exits `0`.
  - Paperclip: switching `qa` to adapter type `cursor` with `extraArgs: ["--trust", "--auto-review"]` passed Test Environment ("Cursor is authenticated via `agent login`"). The hello probe was skipped because `command` is a full path rather than `agent`. Not yet run on a Task.
- **Result, first real task (GAM-2 review, 2026-11-04):** `qa` on adapter `cursor` (`gpt-5.3-codex`, `--trust --auto-review`) reviewed the seeding task three times.
  - **It was never woken automatically** when the review stage assigned the issue to it. Every QA run had to be started with `POST /api/agents/{id}/wakeup`. Claude agents in the same flow were woken normally.
  - Once, QA posted its findings as a comment without recording a stage decision. Paperclip then retried the reviewer and moved the issue to `blocked` ("no completed decision or live reviewer run"); the Board had to hand it back. The two other runs recorded decisions correctly: `changes_requested`, then `approved`.
  - Without `GH_TOKEN`, `gh` is unauthenticated, so QA could not see the PR by itself.
  - It found that inherited `npm_*` variables from the Paperclip process (started with `npx`) pointed npm at another directory, and worked around it by sanitizing the environment (see OQ-034).
- **Update (2026-11-04):** The missing wake is not specific to `cursor`; it is OQ-035. With the watchdog, `qa` reviewed GAM-3 and recorded its decision.
- **Adapter source (2026-11-19, installed 2026.1023.0):** the `cursor` adapter accepts `cwd`, `instructionsFilePath`, `promptTemplate`, `model`, `mode` (`plan` or `ask` only), `command`, `extraArgs`, `env`, `timeoutSec`, `graceSec`. It has no allowlist, sandbox or permission key. `--auto-review` is not referenced by the adapter; it is passed to the CLI unchanged.
- **Open:** A working shell allowlist format for Cursor CLI; whether `--auto-review` is acceptable as the `workspace-write` control.
- **Status:** Partially verified.

### OQ-034 — `npm_*` variables leak into agent runs
- **Found (GAM-2, 2026-11-04):** Paperclip was started with `npx paperclipai@… run`. npm sets `npm_config_*` / `npm_*` variables for that process, and agents inherit them. In the game repository, `npm run typecheck` then failed (`typescript/bin/tsc` missing) until the agent cleared those variables.
- **Fix (2026-11-04):** `npm install -g paperclipai@2026.1023.0`, then `paperclipai run` from `~/game-studio-workspace`. The server process is now `node.exe …/paperclipai/dist/index.js run`, started directly by the package shim with no npm wrapper, from a shell with no `npm_*` variables. Data in `~/.paperclip` carried over unchanged. Starting from `~/game-studio-workspace` also stops agents and `process` runs from defaulting to the framework repository as cwd.
- **Status:** Resolved. The next agent `npm` run in a Game Repository is the final confirmation.

### OQ-035 — Reviewer not woken after an in-run hand-off
- **Found (2026-11-04):** In the studio company, when an agent sets its issue to `done` from inside its own run and the policy moves the issue to a review stage, the reviewer agent gets **no run**. This happens whatever the reviewer's adapter: reproduced with `qa` on `cursor` (GAM-3) and `producer` on `claude_local` (GAM-4), with no run after more than 3 minutes. The hand-off cancels the implementer's own run with `issue_reassigned`, and the server log shows no wake failure. Paperclip's stalled-review recovery did not fire within 8 minutes either. In code, the stage wakeup carries `interruptedRunId` into the heartbeat queue's hand-off path (`services/heartbeat/queue.js`); the exact cause is not confirmed. Experiment 0.8 (scratch company) did wake its reviewer, so the trigger is not fully understood.
- **Workaround (`IMPLEMENTED`):** [`runtime/tools/review-wake-watchdog.ts`](../../runtime/tools/review-wake-watchdog.ts) wakes the pending agent participant through the public API after 90 s. Verified: it woke the reviewers of GAM-3 and GAM-4, both completed their reviews, and a second sweep made no duplicate wakes.
- **Next:** report upstream to Paperclip with the reproduction; remove the watchdog once fixed.
- **Auth migration (2026-11-20):** D-AUTH-03 ([auth-migration-board-decisions.md](auth-migration-board-decisions.md)) retires the watchdog only if Paperclip's built-in scheduler is verified, in an isolated environment, to recover these reviewer wakeups; the manual Board sweep is the fallback, and the watchdog gets no Board credential. Note: this question was observed on 2026-11-04 with the same Paperclip version and its scheduler running, so the verification must reproduce this exact scenario. The live watchdog stays as it is until then.
- **Source finding (2026-11-20, Phase A.2):** Paperclip's sweeper does **not** recover this case. `reconcileStrandedAssignedIssues` skips an `in_review` issue whose reviewer has no run on it, or a non-terminal one (`services/recovery/service.js` 3412-3440); it re-dispatches only a reviewer whose previous run is terminal. The original wake is fire-and-forget and can be skipped, deferred or dropped without retry (`routes/issues.js` 11358-11393). Which branch dropped it in 2026-11-04 is not known. So the D-AUTH-03 condition is not met at source level; not runtime-verified. See [auth-migration-phase-a2-readiness.md](../architecture/auth-migration-phase-a2-readiness.md) §3.C.
- **Status:** Worked around.

### OQ-036 — Supabase identity and free tier for the website
- **Superseded 2026-11-05 by [ADR-021](../decisions/ADR-021-laravel-mysql-backend.md):** the Board chose Laravel + MySQL and no Supabase. Anonymous identity becomes a Laravel-issued token; account linking is Laravel code.
- **Assumption (`UNVERIFIED`):** Supabase Auth supports anonymous sign-in, and an anonymous user can later link Google or an email address while keeping the same user id, so their scores stay theirs. The free tier allows a separate dev project and a prod project. Inactive free projects may be paused.
- **Verify:** read the current Supabase docs for anonymous sign-ins, identity linking, free-tier project limits and pausing, and check whether the anonymous sign-in rate limits and CAPTCHA options are enough for a public site.
- **Status:** Open.

### OQ-037 — Website hosting
- **Constraint (ADR-021):** a VPS or cloud server that runs PHP-FPM, Laravel Reverb (long-lived WebSocket process), later a game server, and MySQL behind HTTPS. Shared hosting does not qualify.
- **Board direction (2026-11-05):** Vietnamese provider; **candidate Vietnix NVMe VPS** (at least 2 vCPU / 4 GB, Ubuntu LTS, root). AWS was considered and set aside for now (cost, USD billing and egress, managed MySQL not listed for the Hanoi Local Zone). Everything runs locally until the Board decides.
- **Ask Vietnix before buying:** managed MySQL or not; snapshots and backups on the NVMe line; datacenter location; Anti-DDoS add-on and its filtering capacity; IPv4 and reverse DNS; upgrade path without reinstall.
- **Also verify with a lawyer (OQ-039):** whether a G1 licence applies and what player data must be stored in Vietnam (Decree 147/2024, Art. 39).
- **Status:** Open (candidate chosen; not purchased).

### OQ-038 — Ad network and consent
- **Assumption (`UNVERIFIED`):** Google AdSense needs an owned domain, original content, enough real traffic and a privacy policy. Pages with embedded games may face extra placement rules, and ads near interactive content need a clear margin. Serving ads to EEA/UK visitors needs a certified consent tool.
- **Verify:** read the current AdSense program and placement policies, ads.txt requirements, and alternatives. Check consent-tool requirements for the expected audience (Vietnam first; EU only if expected).
- **Status:** Open.

### OQ-039 — Legal requirements for the website in Vietnam
- **Question:** Does a free browser-game website with ads and no payments need registration or a licence under Decree 147/2024/ND-CP (online games) or other rules? What does Decree 13/2023/ND-CP on personal data require for anonymous ids and optional email linking? Payments would add a licence, a payment provider, refunds and tax.
- **Owner:** the Board Operator, with a lawyer. Agents MUST NOT treat any answer as settled without the Board's confirmation.
- **Status:** Open.

### OQ-040 — Updating existing agents from Git
- **Found (2026-11-04, Paperclip 2026.1023.0):** `company import --target existing` goes through the "safe" route `/api/companies/{id}/imports/{preview,apply}`, which returns `403 Safe import route does not allow replace collision strategy`. Only `rename` and `skip` work. The re-import with `--collision replace` described in ADR-012, OQ-007 and OQ-023 therefore cannot update existing agents.
- **Also found:** importing from the working repository picks up gitignored copies under `.claude/worktrees/`. A package built in a clean folder with only `knowledge/company/` and `knowledge/company/agents/` matches all 8 live agents (after `knowledge/company/agents/qa` declared `slug: qa-engineer`).
- **Options:** the Board edits agents in the UI from Git (current); a sync script using the agent API (`PATCH /api/agents/{id}` and the instructions-bundle routes seen in the installed code, not in the public docs); a fresh company import (loses issue history).
- **Resolved for role texts (2026-11-05):** the official CLI has `paperclipai agent instructions-file:get|put` (route `/api/agents/{id}/instructions-bundle/file`). Paperclip 2026.1023.0 rejects the CLI's `put` with `422 INSTRUCTION_BASE_REQUIRED` because it omits `baseRevisionId`; `scripts/setup/sync-instructions.py` sends it. Used to apply the M1 role texts to all 8 Soucean agents. Renames go through `paperclipai agent update`.
- **Status:** Partly resolved. Adapter config and allowlists are still applied by hand.

### OQ-041 — WIP limit through `maxConcurrentRuns`
- **Question:** If an implementer agent has `runtimeConfig.heartbeat.maxConcurrentRuns: 1`, are review or comment wakes for its other Tasks queued, dropped, or delayed until its current run ends?
- **Why it matters:** Two Tasks ran on one agent at once (GAM-25 and GAM-45). The limit would stop that, but must not stall reviews.
- **Verification method:** scratch company; one agent with limit 1; start a long Task, then send a review hand-off to the same agent; record what happens.
- **Answered from source (2026-11-20, Paperclip 2026.1023.0; not run):**
  - the limit is enforced only in `startNextQueuedRunForAgent` (`heartbeat/queue.js` 1267-1271);
  - `enqueueWakeup` always queues the wake and creates a `queued` run (3135-3193). Wakes for the same task scope coalesce; only daily caps or `wakeOnDemand: false` drop one;
  - queued runs are ordered with dependency-ready `in_progress` work first.
  So with limit 1, a reviewer that has its own task running gets its review **delayed until a slot frees, not dropped**. Recommended use: limit 1 only on agents that never review (Stage 1 gap analysis, G-12).
- **Status:** Answered from source; the scratch-company check is still useful before applying it.

### OQ-042 — Reviewer isolation (G-13)
- **Why it matters:** `web-engineer` (Cursor) committed to the author's branch while reviewing SOU-2 and SOU-18. Role text is the only guard.
- **Found (2026-11-19, source audit of Paperclip 2026.1023.0 and its adapters; nothing was run):**
  - The review stage only reassigns the issue (`issue-execution-policy.js` `buildPendingStagePatch`: status `in_review` plus the participant as assignee). A run's workspace comes from the issue's `executionWorkspaceId` with preference `reuse_existing` (`heartbeat/environment-selection.js`, `heartbeat/workspace-preparation.js`), so **the reviewer runs in the author's worktree, on the author's branch**, with the same write access. "Changes requested" returns the issue to the author in the same worktree.
  - No supported setting gives a review participant its own or a read-only workspace: stage participants carry only `type/agentId/userId`; the workspace strategy has no read-only or mount field. Workspace hooks (`provisionCommand` on every realization, teardown and cleanup on archive) all target the same worktree; a reviewer checkout built in a hook would be a second worktree owner (ADR-006). The `low_trust_review` trust preset only upgrades `shared_workspace` to `isolated_workspace`; it does not separate a reviewer from an issue's existing worktree.
  - Providers: `claude_local` (engine `cli`) passes our `--allowedTools`/`--disallowedTools` through `extraArgs`, so edits and git writes can be refused per agent. `filesystemScope` needs Bubblewrap and throws on Windows. `codex_local` defaults to `--dangerously-bypass-approvals-and-sandbox` unless `extraArgs` sets a sandbox (no Codex agent is used). `cursor` accepts only `mode` (`plan`/`ask`) and `extraArgs`; it has no allowlist, sandbox or permission key, and adds `--yolo` unless `--trust` is given.
  - Our reviewers also implement (`qa` reviews code and writes tests; `web-engineer` reviews `ui-designer`), and permission profiles are per agent, not per stage. A read-only profile on them would stop their implementation work.
  - A reviewer that runs tests executes the author's own build scripts (`npm test`, `npm run …`), which can run any command, so allowing tests is not a write boundary.
- **Options left:** (1) a separate review-only Agent Instance on `claude_local` with no edit tools, no `git add/commit/push` and no build commands (reads, diffs, `gh pr view` only; tests left to CI or the author's evidence), which needs Board approval for the new agent and a live test; (2) an upstream Paperclip feature: a per-stage workspace (detached read-only checkout of the PR head) or a read-only flag for review participants; (3) branch protection on task branches so only the author's token can push, which needs one GitHub token per agent.
- **Verification method for option 1:** scratch company and repository; a review-only `claude_local` agent; ask it to edit a tracked file, `git add`, `git commit` and `git push`; record that each is refused and the author's branch is unchanged.
- **Experiment, option 1 (2026-11-20, Windows 11 native, Claude Code 2.1.328, model `sonnet`):**
  - **Setup.** A throwaway Git repository outside every project: two commits, a task branch with four planted defects, no remote. The reviewer ran as `claude --print --output-format stream-json --verbose`, the base flags of Paperclip's `claude_local` adapter, plus:
    - `--restricted --tools <list> --strict-mcp-config --permission-mode dontAsk --permission-prompts none --settings <reviewer settings file> --no-session-persistence`;
    - its cwd was the repository on the task branch, which is where a Paperclip review run lands.
  - **What was not done.** It was **not run through Paperclip**: Paperclip was off, and starting it would also start the production company, so no sandbox company was created. User and global settings were untouched (`--restricted` ignores them; settings were passed per run).
  - **Three reviewer configurations:**
    - *strict*: tools Read, Grep and Glob only. Deny rules `Edit`, `Write`, `NotebookEdit`, `Bash`, `PowerShell`, `WebFetch`, `WebSearch`. The diff is written by the harness to a separate folder passed with `--add-dir`.
    - *allowonly*: tools Read, Grep, Glob, Edit, Write, Bash and PowerShell. Only Read, Grep and Glob are allowed, with no deny rules, so `dontAsk` refuses the rest.
    - *gitread*: tools Read, Grep, Glob and Bash. Allow `git diff`, `git log`, `git show` and `git status`; deny git write commands, `git -c` and `git config`.

  | Test | Config | Result |
  |---|---|---|
  | Review the task branch (find the four planted defects, with file and line, and give a verdict) | strict | **PASS**: all four found, plus edge cases; `changes_requested` |
  | Edit, Write (in and outside the repo), delete, Bash, PowerShell | strict | **PASS**: the tools are not in the session. A bare deny rule removes a tool even when `--tools` names it |
  | Same operations, tools present | allowonly | **PASS**: every call refused at call time ("don't ask mode"); files unchanged |
  | `git add`, `commit`, `push`, `checkout`, `switch`, `branch`, `reset --hard`, `stash`, `config`, `git -c …` | gitread | **PASS**: each refused |
  | `&&`, `;`, `$(…)`, `>`, `\| tee`, `GIT_EXTERNAL_DIFF=… git diff`, `powershell.exe …`, `cmd.exe /c …` | gitread | **PASS**: each refused, because the full command does not match an allow rule |
  | `git diff --output=<file>`, `git log --output=<file>`, `git show --output=<file>` | gitread | **FAIL**: two untracked files written in the repository, and a file **outside** it overwritten. `--restricted` confines Claude's file tools, not processes run by allowed commands |

  - **Deny patterns cannot close the `--output` hole.** Run by the harness in a copy: `--output <file>` and `--out""put=<file>` also write, so a pattern like `*--output=*` is evaded. Abbreviations (`--outp=`) are rejected by `git diff` and `git log`.
  - **Integrity after all runs.** Branch, HEAD, refs, commit history and reflog unchanged. No remote; no push possible. The only changes were the three `--output` writes, kept as evidence.

  **Answers to the seven questions:**
  1. Useful review: yes, with read-only file tools and a diff supplied from outside.
  2. Claude permission rules block direct Write and Edit: yes, both by removing the tool and by refusing the call.
  3. PowerShell bypass: blocked in every tested configuration; the tool was absent or refused, and `powershell.exe` through Bash was refused.
  4. Git writes: refused when named. But any allowed git read command can still write files through `--output`. With a shell, git writes are **not** reliably blocked.
  5. Windows filesystem isolation: **none in this setup.** The boundary is Claude Code's permission check. A process it lets run has the full rights of the user account (OQ-027).
  6. Enough for G-13: **no, not yet.** The strict form blocks reviewer writes within the tested boundary, but:
     - it was not run through Paperclip;
     - in Paperclip the reviewer still sits in the author's worktree;
     - something must supply the diff without a shell. Paperclip has no such step, and a hook that writes into the worktree would itself change the author's workspace.
  7. Stronger isolation would need one of:
     - a separate OS account with NTFS rights limited to read (OQ-027);
     - a container or VM;
     - an upstream Paperclip per-stage read-only checkout of the PR head.
- **Recommendation:** option 1 is viable only in the *strict* form: no shell, read-only file tools, deny rules for every write tool, diff delivered from outside. A shell allowlist for git, even "read-only", must not be used. Next steps before any production use:
  - a Board decision on how the diff reaches the reviewer;
  - a Paperclip run in a sandbox company, started only with the Board's approval because it shares the instance with the production company.
- **Diff handoff design (2026-11-20, `PROPOSED`, not implemented):** [review-package.md](../design/review-package.md).
- **Board decisions (2026-11-20), now in the design:**
  - **U1:** the reviewer returns a JSON verdict. A Board-side Verdict Relay validates the run, issue, reviewer, head SHA and verdict schema.
    - The relay records the decision **only when its identity is the active review-stage participant**. The proposal makes the Board Operator user (or a dedicated relay user, if Paperclip supports one) the stage participant; `code-reviewer` only gives advice and is woken by hand.
    - If that arrangement is unavailable, or Paperclip refuses the relay, the relay posts the findings only and the Board Operator records the decision manually (`pc.py approve` / `pc.py request-changes`).
    - V1–V3 are unverified sandbox questions.
  - **U2:** manual trigger only (`pc.py review-pack`); no `provisionCommand`, watchdog or automatic lifecycle.
  - **U4:** 50 files, 1 MB patch, 256 KB per file, 10 context files, 2 GB Review Root, 14 days after closure. Over a limit, the package is refused with "split the Task".
  - **U5:** GitHub API first (object-only repository as fallback); never a working repository.
  - **U6:** a dedicated fine-grained read-only token (Metadata, Contents and Pull requests: read; selected repositories), packager only.
  - **U7:** immutable per-issue, per-head storage, and one serialized `current` staging folder, the only one given to the reviewer.
- **Found while designing U1:** Paperclip 2026.1023.0 lets only the current stage participant record a stage decision ("Only the active reviewer or approver can advance the current execution stage"). The relay can therefore decide only if its own user identity is the stage participant, with `code-reviewer` advisory and woken by hand.
- **Still to validate in a sandbox:** V1 (a user as stage participant), V2 (a run for a non-assignee agent), V3 (whether agents reach Board endpoints in `local_trusted` mode), V5 (retention from closure or merge), V6 (fork PRs). V4 (automatic trigger) is for a later phase.
- **Nothing was implemented at design time.** Since then:
  - the Phase 1 packager has been merged (PR #29, audited in PR #30);
  - the relay, token, agent and Paperclip changes are still not done.
- **Review Package Phase 2 (2026-11-20, outside Paperclip, Claude Code 2.1.329, model `sonnet`):** a strict reviewer on a staged fixture package found all three planted defects at the right `files/head` lines with a valid verdict block. Every read, glob or grep outside its cwd and `current/` was refused (store, another issue's package, the staging lock, the audit log, an outside canary), and no file changed. The read boundary comes from Claude Code's `--restricted` flag (together with `--add-dir current`), not from the settings' `allow` rules, so the reviewer profile must always carry it. See [review-package-phase2-results.md](../design/review-package-phase2-results.md). Not verified inside Paperclip.
- **Review Package Phase 3 (2026-11-20, code and offline tests only):** the GitHub API source (design §4 option A) is implemented in `review_github.py`. It reads every page, checks the trees at head and at the merge base, recomputes blob SHAs and detects a moved head. The token comes from Windows Credential Manager and is redacted everywhere. 25 tests run against a fake GitHub. **First live run (2026-11-20):** `datpham02/soucean-game` PR #27, read-only, with the Board's fine-grained token. 7/7 blob SHAs matched GitHub, and the token appeared nowhere. Several pages, a moved head, modified/renamed/deleted files and the 401/403 path are still covered offline only ([review-package-phase3-github.md](../design/review-package-phase3-github.md) §4).
- **Review Package Phase 4a (2026-11-21, code and offline tests only):** `pc.py review-relay` (`review_relay.py`) implements the relay checks (design §3.4) and the receipt, order, retry and refusal rules (§3.5). 55 tests run against a fake Paperclip. It has not run against any Paperclip instance; V1–V3 still need the sandbox (Phase 4b, Board approval). See [review-package-phase4a-relay.md](../design/review-package-phase4a-relay.md).
- **Status:** Open. Option 1 is partly verified outside Paperclip (strict form only); its diff handoff is designed, with decisions U1, U2 and U4–U7 approved, but not built. G-13 stays unresolved.

### OQ-043 — Authenticated mode instead of `local_trusted` (G-14)
- **Why it matters:** in `local_trusted` mode a request without `Authorization` is the Board and instance admin (`middleware/auth.js` 153-163). Any agent able to reach `127.0.0.1:3100` could act as the Board. The Claude profiles allowed `Bash(curl *)` until D-STEP2-01 removed it on 2026-11-20; Cursor agents still have no allowlist. Whether an agent run can actually reach it has not been tested.
- **Questions:**
  - Does `authenticated` mode work on native Windows for the Board's sign-in (the onboarding sign-in failed, OQ-031)?
  - Do agents keep working with only their keys?
  - How do `pc.py`, `post-import.py`, `sync-instructions.py` and the review-wake watchdog authenticate (board API key)?
- **Verification method:** a separate Paperclip instance with its own data folder and port, never the studio instance; switch the mode; run one agent task and each script.
- **Sandbox results (2026-11-20, D-STEP2-02 part (c), no agent runs):** a separate instance (own home folder, instance `sandbox`, port 3200, Postgres 54339, fresh secrets, telemetry and backups off), with the studio instance stopped and port 3100 checked free. Evidence: [step2-board-decisions.md §6b](step2-board-decisions.md#6b-execution-record-d-step2-02-part-c-2026-11-20).
  - **Windows sign-in works.** `authenticated` mode starts on native Windows 11. `paperclipai auth bootstrap-ceo --force` issued an invite; the Board Operator created an account and signed in in a browser. `paperclipai auth login` (a CLI challenge approved in that browser) returned a board token. OQ-031's wizard problem does not apply to this path.
  - **Keyless Board access is closed.** Every keyless request is refused (`403 Board access required`; admin routes `401`).
  - **Migration is not automatic.** The implicit `local-board` user keeps `instance_admin` and owns the existing companies. A user who signs up after the switch is a Board user with no company access and cannot claim admin (`/bootstrap/claim` refuses once an admin exists). Working path, verified: sign up in `authenticated` mode; switch back to `local_trusted` briefly; promote that user (`POST /api/admin/users/:id/promote-instance-admin`) and grant company access (`PUT /api/admin/users/:id/company-access`) keyless; switch to `authenticated`. After that the board token saw both companies and could act as admin.
  - **Agent keys** in `authenticated` mode: same-company reads work (issues not assigned to the agent, the agent list); instance-admin reads are refused (`401`); a cross-issue write without a run is refused (`403`, needs `X-Paperclip-Run-Id`); creating an issue without a run is **allowed** (`201`).
  - **Scripts:** `pc.py`, `post-import.py`, `sync-instructions.py` and `review-wake-watchdog.ts` send no `Authorization` header; `pc.py overview` against the sandbox fails with `403`. Each needs board-token support before the studio switches.
  - **Not tested, and cancelled:** agent runs in `authenticated` mode and G-14 exploitability from an agent run. The Board cancelled the sandbox agent runs on 2026-11-20, and the sandbox was removed.
- **Board decisions (2026-11-20):** the migration design of [auth-migration-phase-a1.md](../architecture/auth-migration-phase-a1.md) was approved as D-AUTH-01 to D-AUTH-05 in [auth-migration-board-decisions.md](auth-migration-board-decisions.md): board claim for the Board identity, a participant migration for SOU-17, SOU-28 and SOU-30, conditional watchdog retirement, separate Board credentials (`PAPERCLIP_BOARD_TOKEN`), and verification in an isolated environment (agent runs need a separate approval). None of this is runtime-verified yet; Phase B is not authorized.
- **Phase A.2 (2026-11-20, source):** a guarded participant update works only for issues without an active stage; an active `in_review` stage held by `local-board` must be decided before the switch, because the guarded update is refused (422). Readiness and test cases: [auth-migration-phase-a2-readiness.md](../architecture/auth-migration-phase-a2-readiness.md), [auth-migration-verification-plan.md](../architecture/auth-migration-verification-plan.md).
- **Phase A.4 (2026-11-20, isolated runtime, no agents):** board claim, `/api/cli-auth/me`, the guarded participant update (case (a) 200, stale guard 409, case (b) 422, reverse 200), revoked-key 401 and viewer-write 403, and the rollback to `local_trusted` all behaved as predicted from source. The duplicate-participant drop was reproduced. See [auth-migration-phase-a4-verification.md](../architecture/auth-migration-phase-a4-verification.md). Still unverified: agent runs in `authenticated` mode; no supported restore exists.
- **Phase A.5 decisions (2026-11-20, approved; implementation Pending):** D-AUTH-10 (E8 stays unmet until a restore is verified), D-AUTH-11 (two instance admins not accepted; demotion plan required), D-AUTH-12 (agent verification planning only; agent and VR tests not authorized), D-AUTH-13 (claim URLs in logs are sensitive; handling procedure required), D-AUTH-14 (explicit roles; no reliance on the `operator` default), D-AUTH-15 (R8 remediation plan; G-14 stays open until mitigated with evidence; D-AUTH-06's credential-risk acceptance does not accept G-14). See [auth-migration-phase-a5-board-decisions.md](auth-migration-phase-a5-board-decisions.md) and [auth-migration-phase-a5-plan.md](../architecture/auth-migration-phase-a5-plan.md). E8, E11 and E12 remain unmet.
- **Status:** Partially verified. Remaining before any switch of the studio instance: script board-token support, a migration runbook, a Board decision, and a check that agents still work in `authenticated` mode (no sandbox remains for it).

## Conflicts

### C-001 — Runtime scope vs. Paperclip built-in execution
- **Documents:** The v1 brief (§2.3: Runtime launches CLIs, manages branches/worktrees; §2.6) vs. ADR-002 ("do not duplicate functionality Paperclip provides") and verified Paperclip features (`claude_local`, `codex_local`, `git_worktree` execution workspaces).
- **Interim rule:** ADR-013 (which superseded ADR-003) and ADR-006 remain Accepted. ADR-011 stages the work so that nothing is duplicated before a gap is shown.
- **Resolution:** ADR-011 accepted on 2026-11-03 after Phase 0. Stage 1: Paperclip owns execution and worktrees; a Runtime is built only for gaps found while operating Stage 1.
- **Status:** Resolved.

### C-002 — Paperclip's default permission bypass vs. security architecture
- **Documents:** Paperclip `claude_local` default `dangerouslySkipPermissions: true` vs. [security-architecture.md §4](../architecture/security-architecture.md#4-agent-permissions-provider-level).
- **Interim rule:** Bypass only with per-instance Board approval and protected branches.
- **Update (2026-11-03):** Under Paperclip's default ACP engine the effective default is `permissionMode: approve-all`, which is equivalent to bypass even with "Skip permissions" off (OQ-011). All seven agents are currently in this state, so none may receive Tasks on a real Game Repository until their permission mode is set.
- **Update (2026-11-03, later):** The six `claude_local` agents of the studio company now use the Claude CLI engine with the tested profile from security-architecture.md §4. `director`, `producer` and `project-manager` got the `read-only` variant; `game-designer`, `gameplay-programmer` and `ui-designer` got `workspace-write`. Instructions settings were kept, and Test Environment passed for all six. `qa` stays on Cursor with `--trust --auto-review` (OQ-033). Later the same day, a reporting rule was added (OQ-011) and both variants passed real runs (5/5). Still to add: each game's build/test commands to the allowlist.
- **Needs:** OQ-011 results.
- **Status:** Open.

### C-003 — Schema location
- **Documents:** The brief's target structure has both `knowledge/projects/project-config.schema.yaml` and a `schemas/` directory.
- **Interim rule:** Project schema stays in `knowledge/projects/` as specified; other schemas go to `schemas/`.
- **Needs:** Board Operator confirmation.
- **Status:** Open.

### C-004 — "Workflow Engine" component
- **Documents:** The brief lists "Workflow Engine or workflow orchestration" as a component; ADR-002 assigns orchestration to Paperclip.
- **Resolution:** No Game Studio workflow engine in v1. Workflows are definitions executed through Paperclip tasks and execution policies ([system-components.md §4](../architecture/system-components.md#4-workflow-definitions-workflow-orchestration)).
- **Status:** Resolved (documentation), revisit only by ADR.

### C-005 — Number of workflow files
- **Documents:** The brief's target tree lists 4 workflow files; §4.4 requires 12 workflows.
- **Resolution:** The 4 names are kept for their matching workflows; 8 more files are added ([../../knowledge/company/workflows/README.md](../../knowledge/company/workflows/README.md)).
- **Status:** Resolved.

## Related documents
- [../conventions.md](../conventions.md) · [../decisions/README.md](../decisions/README.md) · [phases.md](phases.md)
