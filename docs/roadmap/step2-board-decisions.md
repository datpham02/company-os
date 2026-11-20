# Board Decision Record — Step 2 Stage 1 Validation

**Date:** 2026-11-20  
**Status:** Approved — all six decisions, as recommended (Board Operator, in chat, 2026-11-20)  
**Scope:** G-8, G-9, G-11, G-12, G-13, G-14; OQ-041, OQ-043  
**Related PRs:** #32, #33  
**Authority:** Board Operator

Evidence: [stage1-gap-analysis.md, Step 2 validation](../architecture/stage1-gap-analysis.md#step-2-validation-2026-11-20), [open-questions.md](open-questions.md) (OQ-041, OQ-043), [autonomous-execution-log.md](autonomous-execution-log.md) (Step 2).

## 1. Purpose

Record the decisions required after Step 2 — Stage 1 Validation.

This document separates:
- Verified findings from the Paperclip source/configuration audit.
- Proposed operational and configuration changes.
- Experiments requiring a separate sandbox instance.
- Work that must remain blocked until explicit approval.

This record does not authorize production changes or Phase 2 implementation by itself.

## 2. Decisions requested

### D-STEP2-01 — G-14: Remove unrestricted curl access

**Finding:** Both Claude profiles (`claude-read-only` and `claude-workspace-write`), used by six agents, allow `Bash(curl *)`. In `local_trusted` mode, a keyless loopback request may be treated as the Board and instance admin.

**Proposal:**
- Remove `Bash(curl *)` from both Claude profiles.
- Review the Cursor agents (`gameplay-programmer`, `web-engineer`) separately because they currently have no allowlist.
- Do not add alternative network permissions without an explicit security review.

**Recommended decision:** Approve removal from both Claude profiles. Defer Cursor policy until its execution and permission model is reviewed.

**Approval:** Approved 2026-11-20, as the recommended decision above.

### D-STEP2-02 — OQ-043: Authorize an isolated Paperclip sandbox

**Purpose:** Verify whether `authenticated` mode works on native Windows and whether agent runs can access the local-trusted Board API.

**Proposal:**
- Use a separate Paperclip instance.
- Use a separate data directory and port.
- Do not connect it to the live Soucean company or reuse production data.
- Test authentication, agent API access and required setup scripts.
- Record results without changing production configuration.

**Recommended decision:** Approve a disposable, isolated sandbox experiment.

**Approval:** Approved 2026-11-20, as the recommended decision above.

### D-STEP2-03 — G-12: Agent concurrency

**Finding:** `maxConcurrentRuns` limits simultaneous runs, not the number of issues in `in_progress`. The skill's WIP check can be bypassed through other paths.

**Proposal:**
- Test `maxConcurrentRuns: 1` for non-reviewing agents.
- Keep reviewers at a higher limit so review wakes are not unnecessarily delayed.
- Add a WIP check to `pc.py request-changes` in a separately approved implementation.
- Do not treat concurrency limits as a replacement for WIP enforcement.

**Recommended decision:** Approve sandbox validation first. Do not change live values yet.

**Approval:** Approved 2026-11-20, as the recommended decision above.

### D-STEP2-04 — G-9: Restrict MCP task creation

**Finding:** Paperclip MCP `create_task` ignores its declared `status` argument and creates tasks as `todo` (or `blocked` when blockers are provided). It also assigns the task to the calling agent by default.

**Proposal:**
- Report the status mismatch upstream.
- Evaluate narrowing Claude MCP permissions to `list_projects` and `list_project_repositories`.
- Use `project-manager` to propose tasks in a plan or issue; the Board creates actual tasks through `pc.py create`.
- Verify per-tool MCP restrictions through the Claude local adapter in the sandbox.

**Recommended decision:** Approve the planning workflow and sandbox validation. Defer live adapter changes until verified.

**Approval:** Approved 2026-11-20, as the recommended decision above.

### D-STEP2-05 — G-11: Read-only configuration drift checker

**Finding:** Role instructions can be synchronized, but adapter configuration, permissions and runtime configuration do not have a reliable synchronization or drift report.

**Proposal:**
- Build a read-only checker comparing `agents.json` with live Paperclip agent configuration.
- Report missing agents, mismatched profiles, permissions and runtime settings.
- Do not implement automatic apply mode in this step.
- Consider apply mode only after the read-only report has been reviewed.

**Recommended decision:** Approve design and implementation planning for a read-only checker as a Phase 2 candidate. Actual implementation requires separate Phase 2 authorization.

**Approval:** Approved 2026-11-20, as the recommended decision above.

### D-STEP2-06 — G-13: Reviewer isolation

**Finding:** The reviewer still shares the author's task worktree. Role restrictions are not an OS-level security boundary. The review package work remains separate from this validation.

**Proposal:**
- Keep G-13 open.
- Continue the approved review-package work according to `docs/design/review-package.md`.
- Do not claim reviewer isolation is resolved by role instructions alone.

**Recommended decision:** Retain the current mitigation and keep G-13 unresolved until the review-package workflow has been validated.

**Approval:** Approved 2026-11-20, as the recommended decision above.

## 3. Sandbox execution boundaries

If D-STEP2-02 is approved, the sandbox experiment must follow these boundaries:

1. Use a separate Paperclip instance, data folder and port.
2. Do not import or modify the live Soucean company.
3. Do not reuse production credentials or secrets.
4. Do not modify production agent profiles, permissions or runtime configuration.
5. Record Paperclip version, configuration, test steps, observed results and failures.
6. Stop if the experiment requires access to production data or credentials.
7. Report findings to the Board before proposing production changes.

### 3.1 Additional sandbox safety requirements

#### Loopback isolation

The live Paperclip instance currently listens on `127.0.0.1:3100` and accepts local trusted requests without an API key.

Because the sandbox and live instance share the host loopback interface, a sandbox agent may reach the live instance if it targets the live port.

Mandatory controls:

1. Stop the live Paperclip instance before running any sandbox experiment involving local HTTP requests or G-14 validation.
2. Verify that port `3100` has no listening process before starting the sandbox.
3. Run the sandbox on a separate port and data directory.
4. Verify the target URL and port before each experiment.
5. Stop all sandbox processes and agents before restarting the live instance.
6. Abort if the live instance is detected or the request target cannot be verified.

#### Credential and identity isolation

The sandbox must not receive or reuse production Paperclip secrets or GitHub credentials.

Mandatory controls:

- Do not attach or expose `GH_TOKEN` to sandbox agents or processes.
- Do not copy production Paperclip API keys, secrets or secret bindings into the sandbox.
- Use sandbox-specific Paperclip credentials only.
- Prefer a separate Windows user profile with its own Claude Code authentication.
- If the existing Windows user's Claude Code session must be reused, explicitly record this as a Board-approved exception. The experiment must not be described as fully isolated at the identity level.
- Do not grant sandbox agents access to production repositories or other production credentials.

The sandbox experiment must stop if any of these boundaries cannot be maintained.

## 4. Execution order

| Order | Work | Prerequisite |
|---|---|---|
| 1 | Approve decisions D-STEP2-01 to D-STEP2-06 | Board review |
| 2 | Remove curl permission from Claude profiles | D-STEP2-01 approval; controlled configuration change |
| 3 | Prepare isolated Paperclip sandbox | D-STEP2-02 approval |
| 4 | Validate G-14, OQ-043, G-9 and G-12 | Sandbox ready |
| 5 | Update gap analysis and open questions | Evidence collected |
| 6 | Submit Phase 2 scope and implementation plan | Board review of sandbox results |

## 5. Explicitly not authorized

This record does not authorize:

- Changes to the live Paperclip deployment mode.
- Changes to live Cursor permissions.
- Changes to live `maxConcurrentRuns` values.
- Automatic synchronization or application of agent configuration.
- Production changes to MCP permissions.
- Building the Runtime or starting Phase 2.
- Automatic task execution, approval or merge.
- Any change to production data or credentials.

Each item requires the relevant approval and execution scope.

## 6. Board approval record

| Decision | Board outcome | Notes |
|---|---|---|
| D-STEP2-01 — Remove Claude curl access | Approved | Approves removing `Bash(curl *)` from both Claude profiles as a controlled configuration change. Cursor policy deferred |
| D-STEP2-02 — Isolated sandbox | Approved | Approves a disposable sandbox under §3 and §3.1. Reusing this Windows user's Claude Code session is **not** approved by this record; it needs its own Board-approved exception. **Part (c) done (§6b); agent-run part cancelled by the Board 2026-11-20** |
| D-STEP2-03 — Concurrency validation | Approved | Sandbox validation only; live `maxConcurrentRuns` unchanged. The `request-changes` WIP check needs a separate implementation approval |
| D-STEP2-04 — MCP task creation | Approved | Planning workflow and sandbox validation; live adapter changes deferred until verified |
| D-STEP2-05 — Drift checker candidate | Approved | Design and implementation planning only; implementation needs Phase 2 authorization |
| D-STEP2-06 — Reviewer isolation | Approved | G-13 stays open; review-package work continues |

**Board Operator:** approved in chat  
**Approval date:** 2026-11-20

Approval covers the recommended decisions only. §5 still applies: each production change needs its own approval and execution scope.

## 6a. Execution record: D-STEP2-01 (2026-11-20)

**Authorization:** Board Operator in chat: apply D-STEP2-01 to the six live Claude agents in Soucean, after a fresh database backup; remove only the exact `Bash(curl *)` entry; change nothing else.

**Preparation.**
- Paperclip 2026.1023.0 was not running. It was started for this change. `start-studio.cmd` could not start it, because the active Node is now v22.22.1 and `paperclipai` is installed under nvm v24.22.1; it was started with Node v24 on the PATH of its own window only (`nvm use` unchanged). Health: `ok`, `local_trusted`, `127.0.0.1:3100`.
- **Backup:** `POST /api/instance/database-backups` created `paperclip-20261120-140321.sql.gz` (13,359,264 bytes, 4.7 s; `gzip -t` OK). The previous backup was from 2026-11-06. Paperclip's retention policy (7 daily, 4 weekly, 1 monthly) pruned 35 older backup files during this backup.
- **Dry run:** 8 agents; the six `claude_local` agents each had exactly one `Bash(curl *)`; the two `cursor` agents had none; all idle.

**Change.** `PATCH /api/agents/:id` with only `adapterConfig.extraArgs` (Paperclip merges `adapterConfig` shallowly), the list minus the exact element. The script re-read every agent first and would have stopped on any difference from the dry run.

**Verification** (all eight agents read back; `adapterConfig` compared in full, other agent fields compared except timestamps and status):

| Agent | Adapter | Result | `extraArgs` | New config revision | Rollback target (pre-change revision) |
|---|---|---|---|---|---|
| Director | claude_local | OK, curl removed, nothing else changed | 14 → 13 | `78906eaa-a26d-4003-a6b3-3d334bee4820` | `e2f177de-26c8-4826-8761-b4f86c7d1043` |
| Producer | claude_local | OK, curl removed, nothing else changed | 14 → 13 | `30a23a25-8a19-4f97-be51-f72556a384bb` | none (first revision); restore from its `beforeConfig` |
| Project Manager | claude_local | OK, curl removed, nothing else changed | 14 → 13 | `18bb7a33-7ac3-41a5-a886-4df529d8ee49` | none (first revision); restore from its `beforeConfig` |
| Game Designer | claude_local | OK, curl removed, nothing else changed | 38 → 37 | `2b1564a6-5382-4e91-8af2-1998d59e00e1` | `41cd2bef-70cc-408c-aa0f-bac323271595` |
| QA Engineer | claude_local | OK, curl removed, nothing else changed | 39 → 38 | `f3b56974-5da9-4a18-9aa0-1d9e86329fb2` | `079991a1-5640-4bb1-b68c-1cea7a0e5a94` |
| UI Designer | claude_local | OK, curl removed, nothing else changed | 40 → 39 | `c696494c-57a7-4ee7-92d1-2487a6dcd518` | `3b0f6f62-8c0d-48b6-8722-a2fde5ea3675` |
| Gameplay Programmer | cursor | Unchanged | — | none (latest 2026-11-04) | — |
| Web Engineer | cursor | Unchanged | — | none (latest 2026-11-04) | — |

Each new revision's `beforeConfig` contains `Bash(curl *)` and its `afterConfig` does not; the only removed element is `Bash(curl *)`.

**Rollback.** `POST /api/agents/:id/config-revisions/<rollback target>/rollback` restores that revision's whole configuration. The narrowest rollback is a `PATCH` that puts `Bash(curl *)` back into `extraArgs` at its old position, taken from the new revision's `beforeConfig`. Database backup: `paperclip-20261120-140321.sql.gz`.

**Not done (out of scope):** Cursor agents (policy deferred); G-14 exploitability (needs the D-STEP2-02 sandbox); `authenticated` mode; the Node/PATH issue in `start-studio.cmd`. **G-14 stays open.**

## 6b. Execution record: D-STEP2-02 part (c) (2026-11-20)

**Authorization:** D-STEP2-02 (approved); the Board Operator chose part (c): no agent runs first. The sandbox Claude Code identity question (§3.1) stays open, so no agent ran.

**Loopback isolation (§3.1).**
- Before stopping: all eight live agents idle, no run in progress.
- Live watchdog and Paperclip stopped; ports 3100 and 54329 had no listener; the live database folder's timestamp did not change while the sandbox ran.
- The live Postgres exited with its Paperclip process before `pg_ctl stop` could run (unclean shutdown). On restart Paperclip ran startup recovery and reached `ready`; agents, open issues and the D-STEP2-01 change were unchanged.
- Sandbox: own home folder outside `~/.paperclip`, instance `sandbox`, port 3200, Postgres 54339, fresh `.env` secrets; telemetry, update checks and backups off. Test scripts were fixed to `127.0.0.1:3200`; the mode-switch script refused to start if anything listened on 3100.
- After the tests every sandbox process was stopped and no sandbox port was listening; only then was the studio started again (with the fixed `start-studio.cmd`: Paperclip and the watchdog both on Node 24).

**Credential isolation.** No `GH_TOKEN`, production API key, secret or secret binding was used. The only credentials were sandbox ones: the Board Operator's sandbox account, a CLI board token stored in the sandbox folder, and agent keys of a sandbox agent. The sandbox test agent used the `process` adapter, was paused, had every wake disabled and recorded 0 runs.

**Results.**

| Test | Mode | Result |
|---|---|---|
| Keyless read, write, instance-admin read | `local_trusted` | 200 / 201 / 200: keyless is the Board and instance admin |
| Keyless write with a foreign `Origin` | `local_trusted` | 201: accepted |
| Keyless request with a foreign `Host` | `local_trusted` | 403 |
| Agent key: read an issue not assigned to it; list agents | both | 200 (G-8 server side confirmed) |
| Agent key: instance-admin read; close another issue | both | 401; 403 |
| Agent key: create an issue without a run | `authenticated` | 201 |
| Keyless read, write, admin read, agent-key creation | `authenticated` | 403 / 403 / 401 / 403 |
| Board sign-in on Windows (browser) and CLI board token | `authenticated` | Works |
| New user after the switch: company access, admin | `authenticated` | None; cannot claim admin |
| Promote and grant access in `local_trusted`, then switch | both | Works; the board token then sees the companies and is admin |
| `pc.py overview` | `authenticated` | 403: no `Authorization` header |

The evidence files (JSON, tokens redacted) are deleted with the sandbox (Board decision, 2026-11-20); this record is the remaining evidence.

**Agent runs cancelled (Board decision, 2026-11-20).** The Board started preparing a separate Windows user for sandbox agent runs (§3.1), then decided the agent-run tests are not needed and ordered the sandbox removed: instance, evidence files and scripts, plus the sandbox Windows user and its folder rule (Board Operator steps). One finding from that preparation stands on its own: the studio machine's workspace folder, which holds `company-os` and the other repositories, grants **Modify to all Authenticated Users**, so any other local Windows account can read and change the production repositories. The Board Operator's profile (Paperclip data, Claude Code login, Node) is private.

**Not done, and not planned after the cancellation:** G-14 exploitability from an agent run; OQ-041 queueing (D-STEP2-03); G-9 option 2, the per-tool MCP restriction (D-STEP2-04). These stay unverified, so any live change that depends on them needs another basis or a new Board decision. **Still open:** board-token support in the scripts; any change to the studio instance's mode.

## 7. Exit criteria

Step 2 follow-up is complete when:

- All six decisions have an explicit outcome.
- Approved sandbox experiments have evidence and reproducible results.
- G-8 through G-14 statuses are updated based on evidence, not assumptions.
- OQ-043 is resolved or has a documented remaining blocker.
- Production changes have separate approval records.
- A Phase 2 proposal is submitted for Board authorization.

**Current status:** Phase 2 remains not started.
