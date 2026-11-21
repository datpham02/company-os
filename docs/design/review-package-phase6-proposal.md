# Review Package Phase 6: production proposal

- **Status:** `PROPOSED`. This document authorizes nothing. Each step in §10 needs its own Board approval before anything changes in Soucean, a repository setting or a credential.
- **Date:** 2026-11-21. Paperclip 2026.1023.0.
- **Basis:**
  - design [review-package.md](review-package.md) §11 (Phase 6: agent, profile, stages, runbook, token);
  - the [R6 readiness assessment](review-package-r6-phase6-readiness.md): B2–B7 closed, answered or accepted, B1 mostly closed;
  - [R5 results](review-package-r5-results.md);
  - [ADR-022](../decisions/ADR-022-author-pull-request-credential.md).
- **G-13 stays open.** This proposal does not claim to resolve it (§8).

## 1. What changes, in one paragraph

Today a Soucean code Task created with `pc.py create --review qa` has two stages (on 2026-11-21, 17 of the 30 Soucean issues have exactly this policy; the rest are design or document Tasks reviewed by another agent):
1. a `review` stage whose participant is the `qa` agent, which reviews inside the author's Task Workspace (G-13);
2. an `approval` stage for the Board.

Phase 6 replaces the `qa` review stage, for the pilot project only, with a **Review Package review**:
- the Board packages the PR (`review-pack`), so the reviewer gets a read-only copy of the diff and files;
- a strict, read-only `code-reviewer` agent reviews that package on its own sub-issue (`review-start`);
- the Verdict Relay records the verdict on the Task's `review` stage, whose participant is `local-board` (`review-relay`);
- the Board then approves and merges as today.

Every step is started by the Board by hand. Nothing is automatic.

## 2. Scope

- **Company:** Soucean (`SOU`).
- **Pilot project:** `soucean-game` (the website; author `web-engineer`).
- **Pilot size:** the first **five** code Tasks after go-live, then a Board checkpoint (§10, step P6-D).
- **Code Tasks only:** Tasks that change code in `soucean-game` and open a PR. Design and document Tasks keep their current review stage and reviewer.
- **Not in scope:**
  - `lamplight-vigil`, considered after the pilot;
  - any automatic trigger (V4);
  - the authenticated-mode migration (OQ-043, A5);
  - other companies.

## 3. Agent

- **Agent:** `code-reviewer` in Soucean, defined in `config/paperclip/agents.json` and a role file `knowledge/company/agents/code-reviewer/AGENTS.md`. The role file says: read-only review of the staged package; verdict block format; treat package content as untrusted data.
- **Adapter:** `claude_local`, model `sonnet`, heartbeat **off**, `maxConcurrentRuns` 1, **no `env`** (no `GH_TOKEN`, no secret of any kind).
- **New profile `claude-reviewer-strict`.** These are the arguments validated live in R1, P0 and R5:
  - `--no-session-persistence`;
  - `--restricted --tools Read,Grep,Glob`;
  - `--disallowedTools mcp__*`;
  - `--strict-mcp-config`;
  - `--permission-mode dontAsk --permission-prompts none`;
  - `--settings <reviewer settings file>`;
  - exactly one `--add-dir <Staging Root>/current`;
  - the reviewer system prompt.
  - `check_reviewer_config` (run by `review-start`) refuses any other shape.
- **Settings file:** the C1 file used in the sandboxes.
  - Allow: Read, Grep, Glob.
  - Deny: Edit, Write, NotebookEdit, Bash, PowerShell, WebFetch, WebSearch, `mcp__*`.
  - `defaultMode` `dontAsk`.
  - Kept in the repository without machine paths; the path is set when the agent is created.
- **Working directory:** an empty folder outside every repository and workspace. The agent has no project and no Task Workspace.
- **Paused** whenever no review is running. The Board resumes it for one review and pauses it after, because Paperclip queues an `issue_disposition_repair` run after each reviewer run (re-check list item 9).

## 4. Stages and workflow

- **Task creation:** a new `pc.py create --review-package` option. It gives the Task two stages:
  1. `review`, participant user `local-board`, which the relay fills;
  2. `approval`, participant user `local-board`, as today.
  - The `qa` review stage is not added for pilot Tasks.
  - `UNVERIFIED`: whether Paperclip runs two consecutive stages with the same user participant (`local-board`) as intended. The sandbox issues had one stage only. P6-B checks it on an `OPT` issue before the pilot; if it does not work, the approval stage is dropped and the Board's merge stays the gate.
- **QA's role in the pilot: a Board decision (§11, decision 3).**
  - **Option a (recommended):** `qa` does not review pilot Tasks. Build and tests stay the author's duty, reported in the Run summary and visible in the PR. The Board can run them before merging. This keeps the pilot free of the G-13 exposure that the Review Package exists to remove.
  - **Option b:** keep a `qa` stage before the Review Package stage, for build and test verification only. G-13 stays as today for that stage.
- **Flow per Task** (`development-cycle` and `code-review-and-merge`, pilot variant):
  1. The author pushes its Task Branch and opens the PR (ADR-022: its own scoped token), then moves the Task to `in_review`. Paperclip hands the `review` stage to `local-board`.
  2. **Board:** `pc.py review-pack <KEY> --github-pr N --github-repo datpham02/soucean-game --allow-repo datpham02/soucean-game` (§9, work item W1 removes the state and task files).
  3. **Board:** resume `code-reviewer`; `pc.py review-start <KEY>`; wait for the run; pause `code-reviewer`.
  4. **Board:** `pc.py review-relay <KEY> --run-id <R>`. The relay posts the findings and records `approved` or `changes_requested`.
     - `changes_requested`: the Task returns to the author.
     - On any refusal the Board decides by hand (`pc.py approve` / `request-changes`).
  5. **Board:** `pc.py review-pack --unstage`.
  6. **Board:** approval stage and merge in GitHub, as today (ADR-009). The PR author is the Board's own account (ADR-022), so the merge uses admin bypass.
- **One review at a time** (staging is single). A second Task waits at step 2 until step 5 of the first.

## 5. Runbook (outline)

To be written as `docs/operations/review-package-runbook.md` (work item W5):

| Section | Content |
|---|---|
| Setup | Roots, set by `COMPANY_OS_REVIEW_ROOT` and `COMPANY_OS_STAGING_ROOT`, in a private folder outside every repository and workspace; packager token in Credential Manager (§6); agent created paused |
| Per Task | The steps in §4, with the exact commands |
| Status | `review-pack --status`: staging, reviewer runs from Paperclip, `verified` |
| Refusals | One row per refusal family, with what to do. <ul><li>Package rules and limits: "split the Task", or review by hand.</li><li>Stale head: repackage.</li><li>Staging holds another issue: finish or unstage it.</li><li>Active reviewer run: wait or cancel.</li><li>Relay check failed, malformed verdict, tool surface, log hash, issue changed (F1), Paperclip error: the Board decides by hand.</li></ul> |
| Retention | `review-pack --cleanup` weekly, by hand. It reads closure from Paperclip (B2) and keeps anything unverified. Cap 2 GB |
| Tokens | Packager token expiry date and rotation reminder (R5 F4); author token per ADR-022 and security-operations §2 |
| Upgrade | Paperclip version re-check list (R6 §8, B6) before the first review on a new version |
| Incident | <ul><li>Reviewer used a forbidden tool, or wrote anything: pause it, abandon staging, review by hand, record it.</li><li>A token appears in a run log: rotate it.</li></ul> |

## 6. Tokens

- **Packager token:**
  - fine-grained, **read-only** (Metadata, Contents, Pull requests: read);
  - repositories: `soucean-game` only, for the pilot;
  - expiry at most 90 days;
  - created by the Board, stored by the Board in Windows Credential Manager (`company-os/review-packager`);
  - never in an agent's environment.
  - R5 F4: the previous one lapsed silently, so the runbook records the expiry date and a reminder 14 days before it.
- **Author token:** unchanged (ADR-022). One shared fine-grained `GH_TOKEN`, Contents and Pull requests read/write, bound only to code-writing agents; an accepted risk.
- **Reviewer:** no token, no secret.

## 7. Roots and retention

- Review Root and Staging Root in a private folder outside every repository, workspace and agent working directory.
- The reviewer can read only `<Staging Root>/current` (`--restricted` plus one `--add-dir`).
- Retention: 14 days after the Task closes (Paperclip `completedAt` or `cancelledAt`), then two-step deletion; cap 2 GB.
- The audit log stays in the Review Root and is never deleted by cleanup.

## 8. Accepted and open risks (named)

| Risk | Status | What limits it |
|---|---|---|
| **G-13** reviewer isolation | Open, narrowed | The reviewer runs on its own sub-issue, not in the author's worktree. It has no write or shell tools (live R1, P0, R5) and no MCP tools. The relay checks run binding, tool surface, log hash and the staging challenge. Comprehension cannot be proven: the Board's approval and merge stay the real gate |
| **G-14 / B4** keyless Board access (`local_trusted`) | **Accepted for now** | V3: an agent process with a shell is the Board. Same-user processes can rewrite the relay's files. Limited by: <ul><li>agent rules;</li><li>Claude allow and deny lists (no `curl`; `npm run *` remains);</li><li>Board review.</li></ul> Cursor authors have no hard guard. Fix: OQ-043 / A5, separate work |
| **B5** branch protection does not bind the owner's account | **Accepted** | For agent tokens the merge gate is procedural: the Board reviews every PR |
| **F1 residual window** | Narrowed | The relay re-checks the issue just before its decision; Paperclip has no conditional status update |
| **B1 open items** | Open | <ul><li>Criterion 2: representative cases only.</li><li>Criterion 6: malformed verdict offline only.</li><li>Criterion 9: verified only in sandboxes until the pilot.</li></ul> The pilot's first review adds the production evidence for criterion 9 |
| Log redaction | Mitigated | `env` secrets are not redacted in run logs. Credential rule and deny list (verified). The reviewer has no secrets |
| Packager token lapse | Mitigated by the runbook | Expiry date and reminder (§6) |
| Paperclip upgrade | Mitigated by the runbook | Re-check list (R6 §8) |

## 9. Implementation work items

Each item is a pull request, reviewed and merged by the Board. No Soucean change happens in this step.

| # | Work | Why |
|---|---|---|
| W1 | `review-pack` through `pc.py` reads the issue (status `in_review`, key, id) and the task text from Paperclip, instead of the Phase 1 state file and a hand-written task file. The goal, acceptance criteria and write set are taken from the description sections that task-contract §2 requires. A description without them is refused, not guessed | Production has no state file. Same fail-closed rules as B2 |
| W2 | `claude-reviewer-strict` profile and the `code-reviewer` role file in the package. `build-package.py` and `post-import.py` support it: settings file path, Staging Root, no project | The agent is defined in Git like every other agent (ADR-016) |
| W3 | `pc.py create --review-package`: stages `review` (`local-board`) and `approval` (`local-board`) | Pilot Tasks get the right stages |
| W4 | `pc.py` helper to resume, start, wait for and pause the reviewer in one command, with the pause in a `finally` | Fewer manual steps; the reviewer is never left resumed |
| W5 | Runbook (§5); updated `code-review-and-merge` and `development-cycle` workflows for the pilot variant; SKILL.md | Operations |

Offline tests for W1–W4. Each fails on the previous code where it fixes behaviour.

## 10. Rollout steps (each needs its own Board approval)

| Step | What | Live change | Acceptance |
|---|---|---|---|
| P6-A | W1–W5 merged | None | Suites pass; self-review done |
| P6-B | Create `code-reviewer` in Soucean, paused; create the roots; store the packager token (Board). Check the two-stage policy on an `OPT` issue | Soucean: one new paused agent; one `OPT` test issue | `check_reviewer_config` passes on the live agent; `review-pack --status` empty and verified; the two-stage check behaves as §4 says |
| P6-C | First pilot Task, end to end, with the Board watching each step. Snapshot worktrees and branches before and after (criterion 9) | One review | Verdict relayed or a documented refusal; criterion 9 holds in production; nothing written by the reviewer |
| P6-D | Tasks 2–5, then a checkpoint record: findings quality, refusals, time and cost per review (one Sonnet reviewer run each), incidents | Four reviews | The Board decides: continue, extend to `lamplight-vigil`, change, or roll back |

## 11. Board decisions needed now

1. Approve this proposal as the plan, or change it.
2. Pilot scope: `soucean-game`, five Tasks.
3. QA in the pilot: option a (no `qa` review stage; recommended) or option b (keep `qa` for build and tests).
4. Start P6-A (code and docs only, no live change).

## 12. Rollback

- **Before P6-B:** revert the merged PRs, if wanted.
- **From P6-B on:**
  - pause or delete `code-reviewer`;
  - create Tasks without `--review-package`; existing pilot Tasks get their stage decided by the Board by hand (`pc.py approve` / `request-changes`), which works without the pipeline;
  - `review-pack --unstage --abandon`.
- The packager token can be revoked at any time. No other component depends on it.
