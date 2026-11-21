# Task Contract, WIP Limit and Blocker Protocol

- **Status:** `PROPOSED` ([ADR-017](../../../docs/decisions/ADR-017-task-contract-and-liveness.md))
- **Applies to:** every Task in every project, created by the Board or by an agent.
- **Enforced by:** the planning workflows, the Paperclip skill's `release` and `triage` commands, and each role's instructions. Paperclip itself does not check these fields.

## 1. Why

The first two days of Stage 1 (2026-11-03/04) showed these failures:

| # | What happened | Root cause |
|---|---|---|
| E1 | GAM-44 and GAM-45 both changed `src/scenes/VigilScene.ts`. GAM-44 merged first, so GAM-45's PR conflicted | The overlap check looked only at `in_progress` Tasks. GAM-44 was in review, not yet merged, and still conflicted |
| E2 | `ui-designer` had GAM-25 and GAM-45 `in_progress` at once, in two projects | Imported agents allow 20 concurrent runs; the WIP limit of 1 existed only in a workflow |
| E3 | `project-manager` planned 12 M1 Tasks; all landed on itself (read-only), 11 went `blocked`; the planning issue GAM-21 then waited on the Board for hours | Agent-created Tasks land on the creator (G-9, G-10); the PM cannot reassign; nobody reminds the Board |
| E4 | GAM-6 was parked for source text the agent could not read. Two agent comments, no human reply; later cancelled as obsolete | G-8, and a blocked Task with no named unblocker |
| E5 | The Cursor QA review ended without a recorded decision; Paperclip moved GAM-45 to `blocked` | Reviewer tooling |
| E6 | Nothing revisits a blocked Task unless someone comments | All agents have heartbeats disabled; wakes are event-driven only |
| E7 | GAM-40 and GAM-46 sat ready in `backlog` with nobody scheduled to release them | No owner for "ready but not released" |
| E8 | 9 of the 12 M1 Tasks form one chain on `ui-designer` | The breakdown followed the role, not the dependency graph |

Paperclip 2026.1023.0 behaviour read from its installed code (`services/issues.js`, `services/issue-dependency-wakeups.js`): a dependent issue is woken (`issue_blockers_resolved`) only when **all** of its blockers are `done`. A **cancelled** blocker stays unresolved until an operator changes the relation, so its dependents never wake.

## 2. Task contract

A Task MUST NOT be released (moved out of `backlog`) unless it has every field below. Paperclip has native fields for some of them; the rest go in the description under these headings.

| Field | Where | Content |
|---|---|---|
| Goal | Title + first line | One outcome |
| Acceptance criteria | Description `## Acceptance criteria` | Checkable statements |
| **Write set** | Description `## Write set` (also accepted: `## Files owned …`) | Files or folders the Task may change (globs allowed) |
| Read set | Description `## Read set` | Documents to read. Text the agent cannot reach (other issues, G-8) is pasted or committed to the project repository first |
| Blocked by | Paperclip blocker relations | Not only prose |
| Assignee | Paperclip assignee | An agent whose role and permission profile can do the work |
| Reviewer | Execution policy `review` stage | A non-author agent, on a different provider where possible ([provider-allocation.md](../policies/provider-allocation.md)) |
| Approval | Execution policy `approval` stage | Board Operator, for anything that changes code or a governed artefact |
| Size | — | Fits one PR and one working session. Default limit: about 10 files or 400 changed lines; the project may set its own |

Agent-created Tasks are created in `backlog`, **unassigned**, with the intended assignee written in the description (G-9). The Board, or an agent granted `tasks:assign`, assigns them and adds the review and approval stages and the blockers before release (G-10).

**Creating or assigning a Task does not start it; only release does.** In the Paperclip skill, `create` always makes a `backlog` Task, `assign` keeps a `backlog` Task in `backlog` and refuses to hand over a started Task unless it is parked in `backlog` first, and `comment` and `wake --issue` refuse an unreleased Task, because Paperclip wakes the assignee on each of these. `release` is the Board Operator's only start gate and runs the WIP and Write Set checks first ([the skill](../../../.claude/skills/paperclip/SKILL.md#start-gate-only-release-starts-a-task)). Not covered, because they bypass the skill: the Paperclip UI, the agents' MCP `create_task` (always `todo` or `blocked` and assigned, G-9, inheriting the run's workspace, G-10), `paperclip-issue-update.sh --status`, and direct API calls. The rules above stay the agents' own duty for those paths.

## 3. Splitting work

1. **Split by write set, not by role.** Tasks that may run at the same time MUST have disjoint write sets.
2. **Vertical slices over layers.** A feature that crosses UI, logic and data is one slice owned end to end, so fewer Tasks touch shared files.
3. **Hotspot files** are changed by one Task at a time. Each project lists its hotspots in its own `AGENTS.md` (for a Phaser game: the main scene, game config, `package.json`; for a website: the router, global styles, schema and migrations). Several features that need the same hotspot are chained (`blocked by`), or one small integration Task owns the hotspot and lands first.
4. **Fix and follow-up Tasks** that touch their parent's files are blocked by the parent's merge (for example GAM-46 after GAM-44).
5. **Short, wide chains.** If most Tasks of a milestone form one chain on one role (E8), look for work that can start earlier (contracts, fixtures, docs), or ask the Board for a second instance of that role.
6. **Cross-department work** is split at a written contract (for example [game-platform-contract.md](../shared/game-platform-contract.md)). Each side owns its own write set; the contract has one owner.

## 4. Conflict prevention

1. Before release, compare the Task's write set with every Task of the same project that is **not merged yet**: `in_progress`, `in_review`, `blocked`, and approved but not merged (E1). Overlap: add a blocker relation and do not release. The Paperclip skill's `release` command enforces this check on every release and `--force` does not skip it; its exact rules (path format, which statuses count as unmerged, how a merge is detected) are in [the skill](../../../.claude/skills/paperclip/SKILL.md#write-set-conflict-guard-release). A release made in the Paperclip UI is not checked.
2. A Task that finds it must change a file outside its write set stops and comments. The `project-manager` re-checks overlap before it continues. Unrelated fixes become follow-up Tasks (R7.2).
3. After each merge, the `project-manager` comments on every open PR of that project whose write set overlaps the merged change: `git fetch origin`, then `git merge origin/main` as separate commands, resolve, re-run tests, push. Never rebase or force-push ([security-architecture.md §4](../../../docs/architecture/security-architecture.md#4-agent-permissions-provider-level)).
4. The Board merges PRs one at a time, in dependency order.
5. A project whose tools cannot handle two worktrees at once sets `workflows.parallel-tasks.maxConcurrent: 1` in the registry.

## 5. WIP and capacity

1. **One `in_progress` Task per Agent Instance** (E2), counted across every project of the company. The `project-manager` does not release a second Task to a busy agent. The Paperclip skill's `release` refuses one and `--force` does not skip it; `triage` lists any agent over the limit ([the skill](../../../.claude/skills/paperclip/SKILL.md#wip-limit-release-triage)). Only `in_progress` counts: `in_review`, `blocked` and `todo` are not implementation WIP under this rule. A release made in the Paperclip UI or by an agent is not checked. The runtime enforcement planned for later is `maxConcurrentRuns: 1` on implementer agents (`UNVERIFIED`: a reviewer agent must still receive its review wakes while it has a Task of its own; test before applying).
2. A role that serves several projects has **one queue**, ordered by the `producer`'s cross-project priorities.
3. If one role's queue is longer than the milestone allows, the `producer` asks the Board for a second instance ([agent-onboarding.md](../workflows/agent-onboarding.md) case B).

## 6. Blocker protocol

An agent that sets a Task to `blocked` MUST post this comment:

```text
Blocked: <one line>
Type: dependency | decision | context | environment | review-tooling | permission
Unblock owner: <agent id | Board>
Ask: <the exact thing that owner must do or answer>
Check again: <after GAM-NN is done | within 4h | …>
```

Then, by type:

| Type | Action |
|---|---|
| `dependency` | The blocker must be a Paperclip blocker relation, so the Task wakes when it is `done`. An agent that cannot set relations asks the `project-manager` or the Board in `Ask` |
| `decision` | @-mention the owning role (`game-designer` for design, `producer` for scope) or ask the Board |
| `context` | Ask for the text to be pasted into the Task or committed to the project repository (G-8). "See GAM-1" is not usable context |
| `environment` / `permission` | The `project-manager` opens a Board Task with the exact fix; no retries meanwhile ([task-failure-handling.md](../workflows/task-failure-handling.md) step 2) |
| `review-tooling` | The reviewer ended without a decision (E5). Wake the reviewer once; if it fails again, the Board records a manual resolution or reassigns the review |

A `blocked` Task without an unblock owner is a process defect; the daily triage lists it.

**Cancelling a Task:** first list the Tasks it blocks, and either point their blocker relation at the replacement Task or cancel them too (cancelled blockers never resolve).

## 7. Liveness: nothing is forgotten

Event-driven wakes are not enough (E6). The [daily-triage](../workflows/daily-triage.md) workflow sweeps every active project. Time limits (`PROPOSED` defaults):

| Situation | After | Action |
|---|---|---|
| Blocked on an agent | 4 h | Wake that agent with the `Ask` |
| Blocked on an agent | 1 working day | Escalate to its manager |
| Waiting on the Board | 1 working day | Top of the Board summary (`pc.py triage`) |
| `in_review` with no reviewer run | 90 s | The review-wake watchdog wakes the reviewer (exists) |
| `in_progress` with no new comment or commit | 1 working day | Execution failure ([task-failure-handling.md](../workflows/task-failure-handling.md) step 4) |
| Ready in `backlog` (all blockers done) | 1 working day | `project-manager` proposes release to the Board |

## 8. Reviews

1. Reviewer ≠ author, on a different provider where possible.
2. The reviewer records a decision (approve / request changes) in Paperclip; a verdict comment alone is not a decision.
3. A reviewer never edits, rebases or pushes the author's branch. Paperclip runs the review in the author's own Task Workspace, so this rule is enforced by role text and Board checks only, not technically (G-13, OQ-042). The reviewer does not switch branches there and commits nothing; a reviewer commit is discarded and the Task sent back.
4. "Changes requested" goes back to the author on the same branch, with the review stages kept.
5. The author's next run makes the fix. When Paperclip wakes the author with a recovery contract instead (reason `issue_disposition_repair`: "recover this task, not do the work"), the author is the original owner and the fix is the live disposition it asks for; a run that only changes status, or reads Paperclip's files to repair its bookkeeping, counts as an unsuccessful Run ([task-failure-handling.md](../workflows/task-failure-handling.md) step 4). An author who cannot make the fix, or disagrees with it, sets the Task `blocked` instead (SOU-31, OQ-048).

## Related documents
[../policies/rules.md](../policies/rules.md) · [../workflows/parallel-tasks.md](../workflows/parallel-tasks.md) · [../workflows/task-delegation.md](../workflows/task-delegation.md) · [../workflows/daily-triage.md](../workflows/daily-triage.md) · [../../../docs/architecture/stage1-gap-analysis.md](../../../docs/architecture/stage1-gap-analysis.md)
