# Stage 1 Gap Analysis

**Status:** living document, started 2026-11-04. The MUST-by-MUST evaluation and the Task evidence ledger that Phase 1 item 5 and item 4 require were added on 2026-11-21 (sections at the end). ADR-011 Stage 1 runs the studio on Paperclip's own adapters. This file lists the requirements Paperclip did not meet in practice, and what Game Studio does about each one. Stage 2 Runtime code is written **only** for gaps listed here.

| # | Gap | Evidence | Response | Status |
|---|---|---|---|---|
| G-1 | The reviewer is not woken when an agent hands an issue to a review stage from inside its own run | OQ-035 (GAM-3, GAM-4) | [`runtime/tools/review-wake-watchdog.ts`](../../runtime/tools/review-wake-watchdog.ts) wakes the pending agent participant through the public API | `IMPLEMENTED` workaround; report upstream |
| G-2 | `claude_local` on the default ACP engine approves every tool request | OQ-011, C-002 | Configuration only: Claude CLI engine profile with allowlist and reporting rule ([security-architecture.md](security-architecture.md) §4) | Resolved by configuration |
| G-3 | Isolated per-task worktrees sit behind an experimental instance flag | OQ-002 | Configuration only: `enableIsolatedWorkspaces` on; re-check on every Paperclip upgrade | Resolved by configuration |
| G-4 | Paperclip approvals are not linked to GitHub PR review or merge | OQ-005 | Manual two-step approval (ADR-009) | Accepted for v1 |
| G-5 | Task branches are named `<ISSUE-KEY>-<slug>`, not `agent/<agent-id>/<task-key>` | OQ-004 | Accept Paperclip's naming; allowlists use `GAM-*` | Accepted |
| G-6 | Onboarding wizard sign-in needs Python's Unix-only `pty` on Windows | OQ-031 | Import the company instead of using the wizard | Worked around |
| G-7 | `npx`-started server leaks `npm_*` variables into agents | OQ-034 | Global install, `paperclipai run` | Resolved by operation |
| G-8 | Confined agents cannot read Paperclip data beyond their own issue: other issues, the agent list. The normal agent API read path requires `$PAPERCLIP_API_KEY`, which the permission layer refuses. A separate `local_trusted` path may bypass this requirement (G-14); agent-run accessibility is untested | GAM-5 (pillars drifted from GAM-1), GAM-7 (tasks created with the wrong assignee) | Keep source-of-truth documents in the Game Repository (`docs/concept.md`, `docs/vision.md`); the Board fixes assignments. Candidate: a read-only helper script for issue and agent lookups, allowlisted like `paperclip-issue-update.sh` | Open: cause verified (Step 2) |
| G-9 | `create_task` (Paperclip MCP) creates issues as `todo` even when `backlog` is requested, so an assigned task starts at once | GAM-7 (GAM-9 started a run) | Board returns such tasks to `backlog`; planning tasks should create issues unassigned | Open: cause verified, skill path mitigated (Step 2) |
| G-10 | Issues created inside another issue's run inherit that run's execution workspace, so several tasks share one worktree and branch. Created issues also get no execution policy, so they skip review and Board approval | GAM-8 and GAM-9 (created in GAM-7's run) both ran in the `GAM-7-…` worktree; GAM-8 committed there. Caught before GAM-9 changed anything | Set `executionWorkspaceId: null` and `executionWorkspacePreference: isolated_workspace` before release; the skill's `release` does this automatically. Add review and approval stages to agent-created tasks | Worked around |
| G-11 | Import into an existing company refuses `--collision replace`, so Git changes to existing agents cannot be re-imported; importing from the working repository also picks up gitignored worktree copies | OQ-040 (dry runs 2026-11-04) | Build the package in a clean folder; Board applies changes to existing agents from Git; `sync-agents` script `PLANNED` ([company-bootstrap.md](../operations/company-bootstrap.md)) | Partially Verified: role texts synced, import limit confirmed, config drift open (Step 2) |
| G-12 | No WIP limit (imported agents allow 20 concurrent runs) and no revisit of blocked or stale work (heartbeats off); cancelled blockers never resolve | GAM-25/GAM-45 on one agent; GAM-6; GAM-21 | Task contract and daily triage ([task-contract.md](../../knowledge/company/standards/task-contract.md)); `pc.py triage` and release checks; `maxConcurrentRuns: 1` after OQ-041 | Partially Verified: skill-path workaround, bypasses listed, native sweeps found (Step 2) |
| G-13 | A reviewer runs in the author's task worktree and can commit and push the author's branch. Cursor profiles have no allowlist and no appended rules, so role text is the only guard | SOU-2 (db51e6d), SOU-18 (e7e3f88), both `web-engineer` on Cursor | Rule in every role file and in the `git` rule for Claude profiles; review code with `qa-engineer`; a reviewer push is discarded and the Task sent back. **Re-audited 2026-11-19 from the installed source (P1.1): no supported fix in Paperclip 2026.1023.0.** The review stage only reassigns the issue, and every run on it reuses the issue's worktree, so the reviewer works on the author's branch; there is no per-stage or read-only workspace setting; `filesystemScope` needs Bubblewrap and fails on Windows; `cursor` has no allowlist or permission key; the `claude-workspace-write` push rule (`{PREFIX}-*`) matches every task branch, the author's included. Next step and required capability: OQ-042. **Experiment 2026-11-20 (outside Paperclip):** a Claude Code reviewer with only read tools could review and could not write. A reviewer allowed `git diff`/`log`/`show` wrote files inside and outside the repository through `--output`. Windows gives no OS-level boundary here | Open: role rules only; revalidated 2026-11-20, see G-14 |
| G-14 | In `local_trusted` mode Paperclip treats any request without `Authorization` as the Board (instance admin). Both Claude profiles (`claude-read-only` and `claude-workspace-write`, used by six agents) allow `Bash(curl *)`, so an agent may be able to act as the Board with a plain `curl http://127.0.0.1:3100/api/...` (approve its own work, change status, assignees or agents) if its runtime lets that command reach the local API. Cursor profiles have no allowlist at all | Source: `middleware/auth.js` 153-163 (default actor `local-board`, `isInstanceAdmin: true`, `source: local_implicit`), `board-mutation-guard.js` 78-84 (no Origin needed). Instance config: `deploymentMode: local_trusted`, `bind: loopback`, `port: 3100`. `agents.json` lines 24 and 49. Not exploited or tested live | **2026-11-20 (D-STEP2-01):** `Bash(curl *)` removed from both Claude profiles and the six live Claude agents ([execution record](../roadmap/step2-board-decisions.md#6a-execution-record-d-step2-01-2026-11-20)). Still open: Cursor agents have no allowlist; exploitability untested; `authenticated` mode (OQ-043). See Step 2 validation below | **Open (critical)**: source/config verified; exploitability unverified |

## Step 2 validation (2026-11-20)

**Method.**
- A source audit of the installed Paperclip 2026.1023.0 (`@paperclipai/server/dist`, shared validators, bundled agent skill), plus this repository's configuration and scripts.
- The instance's own `config.json` was read only for its mode, bind and port.
- **Paperclip was not started, and no live or sandbox experiment was run.**
- Each item below gives the facts (with source lines), what remains assumption, and a proposal.
- Nothing here changes code or configuration.

### G-8: agent access to Paperclip data

- **Verified (source):** Paperclip itself lets a standard-trust agent read any non-private issue and the agent list of its own company.
  - `GET /issues/:id` → `assertIssueReadAllowed` → `authorization.js` 1747-1760 "allow_company_agent". There is no assignee check.
  - The issue list and `GET /companies/:id/agents` are filtered by the same rule, and agent configs are redacted.
  - Private projects and private issues are denied.
- **The normal agent API path requires a credential.** However, G-14 identifies a separate `local_trusted` path that may bypass this requirement; its accessibility from agent runs has not been tested.
  - The bundled skill tells agents to send `Authorization: Bearer $PAPERCLIP_API_KEY`, and Claude Code refuses commands with shell variables.
  - The helper `paperclip-issue-update.sh` reads the key itself, but it only PATCHes.
  - The MCP server `Paperclip projects` offers `list_projects`, `list_project_repositories`, `create_project`, `create_task` and `set_task_title`. It has no read tool for issues or agents.
- **Reproducibility:** from source. A live check would need a run in a sandbox company.
- **Impact:**
  - planning agents work from stale or pasted context (GAM-5, GAM-7);
  - the Board stays the courier for cross-issue text.
- **Options:**
  1. Keep source-of-truth text in the project repository and paste it into issues (current; no new risk).
  2. A Company OS read-only helper script that reads the key from the environment, allowlisted by exact path (like `paperclip-issue-update.sh`). It needs G-14 fixed first, or it adds little.
  3. Wait for an upstream read tool in the Paperclip MCP server.
- **Recommendation:** keep option 1. Design option 2 after G-14 is closed. Option 2 is a new tool and needs Board approval.
- **Status: Open.** The cause is verified; no fix is chosen.

### G-9: task creation by agents

- **Verified (source):**
  - The Paperclip MCP tool `create_task` declares `status: backlog | todo` and says "backlog tasks never wake an agent" (`semantic-action-catalog.js` 420-440).
  - But `callProjectTool` ignores `args.status`. It always sends `status: todo`, or `blocked` when blockers are given (`services/project-tools.js` 35-45).
  - It sets `assigneeAgentId: args.assigneeActorId ?? input.agentId`, so the task is assigned to the calling agent by default, and `parentId` is the current issue.
  - The route `routes/project-tools.js` always includes `create_task` (`projectToolDefinitions(workMode, true)`). The claim `delegation:tasks:create` is not checked on that path.
  - Every Claude profile in `agents.json` allows the whole server (`mcp__Paperclip_projects`).
  - The REST create defaults to `todo` only when an assignee is given and the status is omitted (`resolveCreateIssueStatusDefault`). An explicit `backlog` is honoured there.
- **Reproducibility:** from source. Matches GAM-7 / GAM-9 (2026-11-04).
- **Impact:** an agent-created task starts at once, on the creator unless it names someone else. That skips release's Write Set and WIP checks and the review stages (G-10).
- **Mitigation in place:** the skill's own paths cannot start a task outside `release` (P0.3). Agents' MCP path is unchanged.
- **Options:**
  1. Report the `status` bug upstream (the declared schema and the implementation disagree).
  2. Narrow the Claude allowlists from `mcp__Paperclip_projects` to the read tools (`mcp__Paperclip_projects__list_projects`, `…__list_project_repositories`), so `create_task` is refused. Whether Claude Code's per-tool MCP rule works through the `claude_local` adapter is unverified.
  3. The planning agent (`project-manager`) writes proposed tasks into its issue or a plan document, and the Board creates them with `pc.py create`.
- **Recommendation:** options 1 and 2 together, with option 3 as the planning workflow. Option 2 is a live adapter-config change and needs Board approval and a sandbox check.
- **Status: Open.** The cause is verified; the skill path is mitigated.

### G-11: agent synchronization from Git

- **Verified (source, re-checked):** the safe import route still refuses `replace` (`routes/companies.js` 993 and 1009: "Safe import route does not allow replace collision strategy").
- **What syncs today:**
  - `scripts/setup/sync-instructions.py`: role texts, through the instructions-bundle API with `baseRevisionId`; used on all 8 Soucean agents on 2026-11-05;
  - `scripts/setup/post-import.py`: project workspace paths and secret bindings.
- **Not synced, applied by hand:** adapter config (CLI args, allowlists, appended rules), permissions, `runtimeConfig` (`maxConcurrentRuns`), names and reporting lines.
- **No drift report exists**, so whether live agents still match `agents.json` is unknown until someone looks.
- **Impact:** a security change to a profile (for example G-14's curl removal) has to be applied agent by agent in the UI, and nothing proves it was applied everywhere.
- **Options:**
  1. A read-only drift check: compare the adapter config, permissions and runtime config built from `agents.json` with the live agents, and report differences. This is a Phase 2 tooling candidate.
  2. An apply mode for that tool, one agent at a time with confirmation.
  3. A fresh company import (loses history; rejected).
- **Recommendation:** build option 1 first (no writes). Decide option 2 after seeing its report.
- **Status: Partially Verified.** Role texts are solved; import is a confirmed Paperclip limit; config drift is open.

### G-12: WIP enforcement and stale work

- **Verified (source):** `maxConcurrentRuns` is enforced only in `startNextQueuedRunForAgent` (`heartbeat/queue.js` 1267-1271). The default is 20, clamped to 1–50.
- **At the limit, new wakes are queued, not dropped** (`queue.js` 3135-3193). Only daily caps or `wakeOnDemand: false` drop a wake. **This answers OQ-041:** with `maxConcurrentRuns: 1`, a reviewer's review wake waits while its own task runs.
- **There is no per-company or per-project WIP limit.**
- **Concurrency is not WIP.** `maxConcurrentRuns` limits simultaneous runs, not the number of issues in `in_progress`. A separate WIP check is still required to enforce one active task per agent.

  | Mechanism | What it controls |
  |---|---|
  | `pc.py release` | The number of `in_progress` tasks per agent, for releases made through the skill |
  | `maxConcurrentRuns` (Paperclip) | The number of simultaneous runs of one agent |
  | `pc.py request-changes` | Returns a task to `in_progress` with no WIP check (a bypass, below) |
  | Paperclip scheduler | Reconciles stranded issues and silent or orphaned runs; no WIP rule |

- **Correction to the original row:** "nothing revisits stale work" is wrong. An instance-wide scheduler (default on, every 30 s, `config.js` 246-247; `index.js` 1278-1296 and 1481-1498) runs regardless of agent heartbeats:
  - `reconcileStrandedAssignedIssues`: `todo`, `in_progress` and `in_review` issues; re-dispatches, re-wakes reviewers, or escalates to the Board;
  - `reconcileResolvedDependencyWakes`;
  - `scanSilentActiveRuns`: runs with no output, at 5 and 15 minutes;
  - orphaned-run reaping;
  - due issue monitors.
- **It does not sweep `blocked` issues.** A cancelled blocker never resolves its dependents (`services/issues.js` 1414-1416); only removing or replacing the relation does.
- **Company OS enforcement today:**
  - `pc.py release` refuses a second `in_progress` task per agent, across projects (P0.2);
  - `pc.py triage` reports breaches and stale or blocked work.
- **Bypass paths:**

  | Path | Verified how |
  |---|---|
  | Paperclip UI | No hook (P0.3 audit) |
  | Agents' MCP `create_task` (always `todo`, G-9) | Source |
  | An agent setting its own status through `paperclip-issue-update.sh --status` | The helper PATCHes any status |
  | Any Board API call, including through G-14 | Source |
  | **`pc.py request-changes`** | It returns the task to the implementer as `in_progress` with no WIP check (`board_decision` in `pc.py`) |

- **Impact:** WIP 1 holds only for releases made through the skill. A bypass can leave one agent with two `in_progress` tasks. With the current configuration (`maxConcurrentRuns` at the default 20, never lowered), their runs can also execute at the same time. Even with `maxConcurrentRuns: 1`, both tasks would stay `in_progress`; only their runs would take turns.
- **Options:**
  1. `maxConcurrentRuns: 1` on agents that never review (`gameplay-programmer`, `ui-designer`, `game-designer`). Keep reviewers (`qa`, `web-engineer`, `director`) higher, so their review wakes are not delayed.
  2. A WIP check in `pc.py request-changes`.
  3. Remove the agents' `create_task` (G-9) and the curl path (G-14).
- **Recommendation:** options 1–3. Option 1 is a live change and needs Board approval, a sandbox check of the queueing, and G-11 tooling to apply it reliably. Option 2 is a small skill fix for a later implementation step.
- **Status: Partially Verified.** The workaround is in place; its bypasses are listed; OQ-041 is answered from source.

### G-13: reviewer isolation (revalidated)

- **Re-run needed: no.** Conditions are unchanged since the OQ-042 experiment (2026-11-20):
  - Paperclip install unchanged (2026.1023.0, installed 2026-11-04);
  - Claude Code 2.1.328, the version used in the experiment;
  - no change to `agents.json` or reviewer roles after commit `1e7f689` (2026-11-19).
- **Evidence stands:**
  - the reviewer runs in the author's worktree;
  - there is no per-stage or read-only workspace;
  - a strict Claude reviewer (Read/Grep/Glob) cannot write;
  - a git shell allowlist can (`--output`);
  - Cursor cannot be confined.
- **New interaction with G-14:** if an author's run can reach Board endpoints through `curl` (untested), it could approve its own work and skip review entirely. Until G-14 is closed or shown unexploitable, reviewer isolation alone does not protect the review gate.
- **Status: Open** (role rules only). The review package (OQ-042) is in progress; Phase 1 is merged and hardened (PR #30, open).

### G-14 (new): implicit Board access in `local_trusted` mode

- **Verified (source and config):**
  - `middleware/auth.js` 153-163: a request without a bearer gets the actor `local-board`, `isInstanceAdmin: true`.
  - `board-mutation-guard.js` lets `local_implicit` writes through without an Origin header.
  - The only guards are a loopback bind and a Host-header check.
  - The studio instance runs `local_trusted` on `127.0.0.1:3100`.
  - Both Claude profiles allow `Bash(curl *)`: `claude-read-only` (`director`, `producer`, `project-manager`) and `claude-workspace-write` (`game-designer`, `ui-designer`, `qa-engineer`), six agents in all. No role text or workflow uses `curl` (repository search). The rule is a leftover of the OQ-011 experiments.
  - Cursor agents have no allowlist.
- **Assumption, not tested:** that Claude Code's `Bash(curl *)` rule admits a literal `curl http://127.0.0.1:3100/api/...` in a `claude_local` run. The rule format says it would.
- **Impact (critical):** an agent may be able to act as the Board and instance admin if its runtime permits the configured `curl` command to reach the local Paperclip API. This exploitability has not been tested. If it can, it could approve or close issues, reassign work, change agents, adapters and permissions, or read every company. This undermines every Board gate: ADR-009, release, review stages and G-13.
- **Options:**
  1. **Remove `Bash(curl *)` from both Claude profiles.** Low cost; no known use. A live adapter-config change on the six agents that use the two profiles (G-11: by hand).
  2. Run Paperclip in `authenticated` mode, so the Board logs in and agents use only their keys. Large change; Windows sign-in history (OQ-031) and the skill's local Board calls need checking (OQ-043).
  3. Cursor agents: no allowlist exists. Options are `--trust` without `--auto-review` (refuses all shell; breaks builds), moving code roles to Claude, or accepting the risk until option 2.
  4. OS-level separation (a separate Windows account for agents, OQ-027). Loopback filtering by process is not available with the built-in firewall (assumption).
- **Recommendation:**
  - do option 1 now, as a Board-approved configuration change, and confirm it in a sandbox run;
  - put option 2 on the Runtime prerequisites list (OQ-043);
  - decide option 3 explicitly.
- **Status: Open (critical): source/config verified; exploitability unverified.** Not exploited and not tested live.
- **Sandbox 2026-11-20 (D-STEP2-02, no agent runs):** keyless Board and instance-admin access confirmed over HTTP in `local_trusted` (a foreign `Origin` is accepted; only a foreign `Host` is refused); `authenticated` mode closes it on Windows. Agent exploitability stays untested: the Board cancelled the sandbox agent runs on 2026-11-20. Details: [OQ-043](../roadmap/open-questions.md#oq-043--authenticated-mode-instead-of-local_trusted-g-14).

## Phase 1 item 5: MUST-by-MUST evaluation (2026-11-21, Stage A survey)

[phases.md](../roadmap/phases.md) Phase 1 item 5 asks for every requirement of ADR-006, ADR-009, the Studio Rules ([rules.md](../../knowledge/company/policies/rules.md)) and [runtime-architecture.md](runtime-architecture.md) to be checked against Stage 1. The gap table above lists only gaps met in practice; this section is the requirement-by-requirement matrix.

- **Method:** read-only survey of the repository on 2026-11-21 (`main` at `027825b`), plus read-only Paperclip and GitHub reads. Nothing was changed.
- **Status key:**
  - **PASS:** evidence shows the requirement holds.
  - **PARTIAL:** it holds on some paths, or only by rule, or has documented bypasses.
  - **GAP:** evidence shows it does not hold.
  - **NOT VERIFIED:** no evidence either way.
  - **STAGE 2:** it applies only to the planned Runtime (Phase 3), so it is not a Stage 1 deficiency.
- **Rules:** each numbered Studio Rule is treated as a MUST. runtime-architecture.md has one upper-case MUST NOT (line 117) and two lower-case "must" sentences. Its rule tables are listed as Stage 2 items.

### Cross-cutting findings

| ID | Finding | Evidence | Board position |
|---|---|---|---|
| X-1 | In `local_trusted` mode an agent process with a shell is the Board. A keyless `curl` from a sandbox agent read every company (V3) | [review-package-r6-phase6-readiness.md](../design/review-package-r6-phase6-readiness.md) B3; G-14 below | Accepted as a named risk (B4, 2026-11-21); fix is OQ-043 |
| X-2 | The owner's GitHub account bypasses branch protection on `main`; the agents' token belongs to that account (token-level bypass untested) | [review-package-r5-results.md](../design/review-package-r5-results.md) B5; [ADR-022](../decisions/ADR-022-author-pull-request-credential.md) | Accepted as a named risk (B5) |
| X-3 | Cursor agents (`gameplay-programmer`, `web-engineer`) have no allow or deny list and no appended rules; they rely on their role files | `config/paperclip/agents.json` profile `cursor-workspace-write`; [security-architecture.md](security-architecture.md) | No decision recorded |
| X-4 | The shared `GH_TOKEN` reaches *All repositories* of the Board's account, including this repository, whose `main` is not protected | ADR-022; contradicts [security-operations.md](../operations/security-operations.md) §2 ("only the studio's Game Repositories") | Accepted with ADR-022; security-operations.md §2 not yet updated |

### ADR-006 (Git worktrees)

| ID | Requirement (shortened) | Status | Evidence | Next action |
|---|---|---|---|---|
| ADR006-1 | Every code-changing Task MUST run on a dedicated Task Branch, never the Default Branch | PASS (configuration) | Isolated `git_worktree` policy with `allowIssueOverride: false` (`scripts/setup/build-package.py`); flag `enableIsolatedWorkspaces` on (G-3); `pc.py release` forces isolation; Task ledger below: every merged code PR came from a `<KEY>-<slug>` branch | Re-check the flag after every Paperclip upgrade (ADR-011) |
| ADR006-2 | Concurrent Tasks on one project MUST each run in their own worktree | PARTIAL | G-10 (GAM-8 and GAM-9 shared GAM-7's worktree); fixed on the `pc.py` path only; G-9 (agent `create_task`) | Decide G-9 (D-06) |
| ADR006-3 | Conflicting Tasks MUST NOT run concurrently in the same Task Workspace (SHOULD be serialized; if parallel, separate worktrees and review) | PARTIAL | Write Set conflict guard on `release` (SKILL.md); releases from the Paperclip UI and agent `create_task` are not checked (task-contract.md §4) | As ADR006-2 |
| ADR006-4 | Agents MUST NOT work directly in the Primary Checkout | PARTIAL | Holds by configuration (isolated mode). Worktrees sit inside the primary checkout (`.paperclip/worktrees/`); a shell agent is not prevented from leaving its cwd (X-3) | Covered by Phase 4 isolation (OQ-027) |
| ADR006-5 | The Task ↔ Task Branch ↔ Task Workspace mapping MUST be recorded and kept after the Run | PARTIAL | Paperclip execution-workspace metadata (`branchName`, `deliveryState`) and the Workspace Ready comment; survival after the reaper archives a worktree not verified (OQ-002) | Verify on an archived workspace (read-only) |
| ADR006-6 | Exactly one component MUST own worktree creation and cleanup | PASS | C-001 resolved: Paperclip owns them in Stage 1; no Company OS code creates worktrees (Review Package R5 test 9) | — |

### ADR-009 (approval before merge)

| ID | Requirement (shortened) | Status | Evidence | Next action |
|---|---|---|---|---|
| ADR009-1 | No agent or automated component may modify a Default Branch directly | PARTIAL | Claude profiles deny pushes to `main`, force-push and `gh pr merge`; Cursor agents unguarded (X-3); owner token bypass (X-2) | D-05 (Cursor), B5 accepted |
| ADR009-2 | Changes reach the Default Branch only through a PR from a Task Branch | PASS in practice / PARTIAL by enforcement | Task ledger: 49 merged PRs, all from Task Branches, all merged by the Board account; enforcement procedural for agent tokens (ADR-022) | — |
| ADR009-3 | No merge without Board approval recorded both in Paperclip and on the GitHub PR (approving review or human merge) | PARTIAL | Task ledger: 48 of 49 merged PRs have a Paperclip approval stage (47 with review and approval); the GitHub side is the human merge by the Board. GAM-20 and GAM-44 were merged before Paperclip recorded `done`; GAM-22 had no stages; GAM-7 had an approval stage only. The two records are not linked technically (G-4). X-1: an agent could fake the Paperclip side | Phase 4 merge-approval audit (P4-T03) |
| ADR009-4 | An agent review MUST NOT count as the merge approval | PARTIAL | `pc.py create` always adds a Board approval stage; no exclusive Board identity in `local_trusted` (X-1) | OQ-043 |
| ADR009-5 | Execution logs and the Task ↔ Branch ↔ PR mapping MUST be preserved | PASS for logs / PARTIAL for the mapping | Paperclip 2026.1023.0 has no run-log retention or pruning (`services/run-log-store.js` deletes only its own temporary files); run logs since the first runs in early November are still on disk (checked read-only 2026-11-21). They are kept indefinitely, which also keeps any secret printed into a log. The PR link is kept by comment rule and `deliveryState` | Keep; any log deletion is a Board decision (secret exposure, OQ-025 backups) |
| ADR009-6 | Branch protection SHOULD enforce this technically (SHOULD) | GAP | Protection configured on both project repositories (PR, 1 approval, no force-push, no deletion) but `enforce_admins` is off and the owner bypasses it (X-2) | Accepted (B5) |

### Studio Rules (rules.md)

| ID | Requirement (shortened) | Status | Evidence | Next action |
|---|---|---|---|---|
| R0 | The rules apply to every agent on every Run; role files cannot relax them | PARTIAL | Rules appended to Claude profiles only (X-3) | D-05 |
| R1.1 | Work only in the given Task Workspace and Task Branch | PARTIAL | As ADR006-4; G-13 (a reviewer committed in the author's worktree: SOU-2, SOU-18) | Review Package pilot (Phase 6, separate) |
| R1.2 | Never commit to, push to or merge into a Default Branch | PARTIAL | As ADR009-1 | D-05 |
| R1.3 | Never force-push, rewrite history, delete others' branches, tags or repositories | PARTIAL | Claude profiles deny force-push; the token has no delete or admin scope; Contents-write can still delete branches and tags; Cursor unguarded | D-05 |
| R1.4 | No project code in the framework repository and no framework copies in project repositories | PARTIAL (rule only) | No violation found; the token can write this repository (X-4) | Protect `main` of this repository (D-07) |
| R1.5 | Touch only your Task's project repository | PARTIAL (rule only) | X-4 | D-07 |
| R1.6 | Read the project repository's `AGENTS.md` first | NOT VERIFIED | Relies on the provider reading it from the cwd | Spot-check run logs (read-only) |
| R2.1 | Check out a Task first; on `409` stop | NOT VERIFIED | Atomic checkout is Paperclip's; agent behaviour on `409` not observed | Low priority |
| R2.2 | One Task, one Task Branch, no unrelated changes | PARTIAL | G-10 (two Tasks on one branch once) | As ADR006-2 |
| R2.3 | Post a Run summary comment before the Run ends | PARTIAL (rule only) | Reporting rule in Claude profiles; daily triage flags quiet Tasks | — |
| R2.4 | Move code changes to `in_review`, never directly to `done` | PARTIAL | Paperclip turns `done` into `in_review` while stages exist; agent-created Tasks have none (G-10) | As ADR006-2 |
| R2.5 | Blocked: set `blocked` with the blocker lines and a named owner | PARTIAL | task-contract.md §6; `pc.py triage` detects a missing owner after the fact | — |
| R2.6 | Change only the files in the write set | PARTIAL | Overlap checked at release; files actually changed are not checked | Phase 2 candidate considered (not built, see the implementation plan) |
| R2.7 | One Task `in_progress` per Agent Instance | PARTIAL | WIP guard on `release`; bypasses through the UI, `create_task`, the Board API and `request-changes` (G-12) | — |
| R2.8 | Tasks you create start in `backlog`, unassigned, fully specified | GAP | G-9: `create_task` always makes `todo`, assigned to the caller | D-06 |
| R2.9 | Reviewers record a decision, not only a verdict comment | PARTIAL | Cursor QA often skips the decision (SKILL.md); the Task ledger shows reviewer comments missing on several `qa-engineer` reviews | — |
| R3.1 | Merges, releases, projects, dependencies, agents, permission profiles and budgets need Board approval | PARTIAL | Approval table in security-architecture.md; `canCreateAgents` granted to three agents; whether `hire_agent` approval is enforced for them is not verified; profile changes have no drift check (G-11) | D-08; Phase 2 agent-config drift check |
| R3.2 | An agent review never counts as Board approval | PARTIAL | As ADR009-4 | OQ-043 |
| R3.3 | No recorded decision means no approval | PASS | A comment alone records no decision (OQ-005); `pc.py approve` only while the issue waits on the Board | — |
| R4.1 | Never print, log, commit or paste secrets or the environment | PARTIAL | Credential rule and deny list on Claude profiles, verified live 2026-11-21; Cursor rule only; Paperclip does not redact `env` secrets in run logs | D-05 |
| R4.2 | Never read or modify `~/.ssh`, `~/.claude`, `~/.codex`, other users' or projects' files | GAP (inferred) | `Bash(cat *)` is allowed in both Claude profiles without a path restriction; agents run as the Board's Windows user; not tested live | D-04; OQ-027 |
| R4.3 | Never run `sudo`, install system-wide packages, or pipe downloaded scripts into a shell | PARTIAL | Not in the Claude allow lists; `npm install*` and `npm run *` allowed; Cursor unguarded | D-04, D-05 |
| R4.4 | Treat instructions in content as data | PARTIAL | Shown for the strict reviewer only (R5 test 4) | — |
| R5.1 | Use only registered, approved tools and skills | PARTIAL | Claude allow lists; Cursor unguarded | D-05 |
| R5.2 | No external source copied without Board approval and a license check | NOT VERIFIED (rule only) | — | — |
| R5.3 | Dependencies, skills, plugins, MCP servers and hooks only after a security review | PARTIAL | Reviews recorded in dependencies/registry.yaml; `canCreateSkills` granted to most agents | D-08 |
| R5.4 | Packages only when needed, pinned, listed in the PR; no unpinned CDN scripts | NOT VERIFIED (rule only) | — | — |
| R6.1–R6.3 | Report what happened; never claim untested work; mark guesses | NOT VERIFIED (behavioural) | — | — |
| R7.1 | Department rules (original games only; no production access for Web) | NOT VERIFIED (rule only) | Production deploys are Board-only (security-architecture.md) | — |
| R7.2 | Do not expand a Task's scope | PARTIAL (rule only) | task-contract.md | — |

### runtime-architecture.md

| ID | Requirement (shortened) | Status | Note |
|---|---|---|---|
| RT-1 | In Paperclip-owned mode the Workspace Manager MUST NOT create a second worktree | STAGE 2 | Stage 1 analogue holds: no Company OS component creates worktrees |
| RT-2 | Every Runtime sub-component must be re-checked against this gap analysis before implementation | STAGE 2 | Process rule for Phase 3 |
| RT-3 | Without an injected Task ID or workspace, the Runtime must find its Task through the Paperclip API | STAGE 2 | Condition confirmed true (OQ-003) |
| RT-I-1 … RT-I-11 | Dispatcher rejections, secrets only by env, primary checkout never used, one lock per workspace, cleanup rules, Git allow list, pre-push checks, Result Reporter rules and outbox, process management, recovery sweep, concurrency limits | STAGE 2 | Planned components only. Their Stage 1 analogues appear above (ADR006-4, R1.2, R1.3, G-12) |

### Summary

- **PASS:** ADR006-1, ADR006-6, ADR009-2 (in practice), R3.3.
- **GAP:** ADR009-6 (accepted, B5), R2.8 (G-9), R4.2 (inferred).
- **PARTIAL:** everything else that applies to Stage 1. The two findings behind most of them are X-1 (G-14) and X-2 (B5). Both are accepted risks, not unknowns.
- **NOT VERIFIED:** R1.6, R2.1, R5.2, R5.4, R6.x, R7.1. These are behavioural or rule-only, without a technical check.
- **STAGE 2:** RT-1 to RT-3 and RT-I-1 to RT-I-11. They are not Stage 1 deficiencies.

## Phase 1 item 4: Task evidence ledger (2026-11-21, read-only)

The repository had no per-Task record of real Tasks going through `development-cycle` and `code-review-and-merge`. This ledger joins, read-only:
- Paperclip issues of `SOU` (live) and `GAM` (archived);
- their execution policies and comments;
- the merged PRs of `datpham02/lamplight-vigil` and `datpham02/soucean-game` whose branch starts with the issue key.

| Measure | Count |
|---|---|
| Issues (SOU 30, GAM 46) | 76 |
| Issues with a merged PR from their Task Branch | 49 |
| …of which: `done`, `review` and `approval` stages, at least one reviewer comment, at least one Board comment, merged by the Board account | **38** |
| …merged by an account other than the Board's | 0 |

- **Phase 1 item 4 ("5–10 real Tasks") is met:** 38 Tasks show the whole chain. Examples:
  - code Tasks: GAM-9, GAM-12, GAM-41, GAM-42, SOU-1, SOU-12, SOU-14, SOU-15, SOU-27;
  - design and document Tasks: GAM-5, GAM-23, SOU-3 to SOU-10.
- **Deviations to record (not re-run):**
  - **Merged before Paperclip recorded `done`:** GAM-20 (`soucean-game#1`) and GAM-44 (`lamplight-vigil#20`). This is the reverse of the ADR-009 order.
  - **Weaker evidence:**
    - GAM-22 had no stages;
    - GAM-7 had an approval stage only;
    - nine `qa-engineer` reviews show the review stage passed but no reviewer comment (GAM-10, GAM-11, GAM-18, GAM-20, GAM-38, GAM-39, GAM-44, GAM-45, GAM-46). This matches the "Cursor QA posts no decision" note in SKILL.md.
- **The GitHub side of ADR-009** is the Board's human merge. GitHub approvals are impossible, because every PR is opened by the Board's own account (ADR-022).
- **Limits:**
  - the ledger proves stage policies, comments and merges;
  - it does not replay each stage decision, because Paperclip 2026.1023.0 has no endpoint for the decision history;
  - re-run the read-only join to refresh it.

## Related documents
[../decisions/ADR-011-execution-path-selection.md](../decisions/ADR-011-execution-path-selection.md) · [open-questions.md](../roadmap/open-questions.md) · [runtime-architecture.md](runtime-architecture.md)
