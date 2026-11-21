# Review Package: post-Phase 5 technical assessment and remediation plan

- **Status:** PROPOSED; read-only assessment, 2026-11-21. **Update (same day):** the Board Operator chose **Option B** ("làm phương án B"). It is implemented with offline tests on branch `feat/review-package-option-b` (§3.5): review sub-issue, staging challenge (Option A's challenge included), `review-start` with recovery of interrupted starts, relay checks; the company-scoped path is removed. Not yet run live. Everything else here is still a proposal.
- **Inputs:**
  - [review-package.md](review-package.md) (design);
  - Phase 4a, 4b and 5 records: [4a](review-package-phase4a-relay.md), [4b](review-package-phase4b-live.md), and `review-package-phase5-sandbox.md`. The Phase 5 record is in documentation PR #49, not yet merged; this assessment uses its content as written there;
  - code at `main` `6642f18`: `.claude/skills/paperclip/scripts/review_pack.py`, `review_github.py`, `review_relay.py`, `pc.py`;
  - Paperclip 2026.1023.0 sources, read-only. Server paths below are relative to the installed `@paperclipai/server/dist`; adapter paths to `@paperclipai/adapter-claude-local/dist`.
- **Read-only checks made for this assessment:** one `GET /api/heartbeat-runs/<id>` on the Phase 5 run `1de50989`. No Paperclip writes, no test runs.
- **Standing status:** Phase 5 Partially Accepted; **G-13 OPEN**; V3 not tested; Phase 6 not authorized.

## 1. Executive summary

- **G-13 is the main gap.** The relay can show that a reviewer run belongs to the issue's company, was started after staging by the `code-reviewer` agent, and returned a well-formed verdict for the locked issue and head. It cannot show that the run was started **for this review**, or that the reviewer **read** the staged package.
  - The lock field meant to bind the run (`runId`) is never set.
  - Paperclip keeps the wake reason and the waking actor on the run (`contextSnapshot`). Nothing reads them yet.
- **Two options for G-13:**
  - **A (minimal):** a `review-wake` step records the run id, a per-review id and a package challenge in the lock. The relay requires all of them. This binds the run to the staging, and the verdict to content that is only in the staged package.
  - **B (stronger, workflow change):** one review sub-issue per review, assigned to `code-reviewer`. The run becomes issue-scoped in Paperclip's own records, plus A's checks.
  - **Neither proves comprehension.** At best they prove the run was started for this package, received it, and returned a value that only the package contained. That is evidence of access, not of review.
- **Phase 5 findings:**
  - **`--unstage`** reads runs from a local state file, so a live reviewer run cannot block it. A Paperclip-backed check is needed. Even the state-file rule can no longer match a company-scoped run.
  - **`cancelled` runs** come from Paperclip stopping the run that reassigns its own issue. The run record says so explicitly (`issue_reassigned`, `reassignmentStopConfirmed`). It is a lifecycle state, not a failure. It does not touch reviewer runs today.
  - **Author PR credential:** a decision between giving authors a scoped write credential, and having a Board-side step open PRs.
- **§12:** 1 criterion fully live-verified, 1 holds by definition, 8 partly verified. Each has a proposed test (§5).
- **Roadmap (§6):** six stages, G-13 first. Each needs its own Board approval. Phase 6 should wait at least for R1 and R2.

## 2. Current architecture and trust boundaries

| Component | Trust | Identity and access | Evidence |
|---|---|---|---|
| Review Packager | Trusted, Board side | Packager token, read-only, from Credential Manager; writes only the two roots | `review_github.py` `read_token`; `review_pack.py` has no `subprocess`, network or `ctypes` import (imports at lines 15–25); `test_review_pack.py` `NoForbiddenCapabilities` |
| Staging lock | Trusted file, same-user writable | `{issue, headSha, packagePath, manifestSha256, stagedAt, stagedBy, runId}`; `runId` is always `null` | `review_pack.py` `stage()` line 822 |
| `code-reviewer` run | Untrusted output | `claude_local`, `--restricted --tools Read,Grep,Glob`, `--add-dir <Staging Root>/current`; company-scoped wake (V2) | Phase 4b and 5 run init events |
| Paperclip run record | Paperclip-owned | `companyId`, `agentId`, `issueId` (null for company scope), `status`, `createdAt`, `contextSnapshot` (`wakeReason`, `actorId`, `triggeredBy`), `wakeupRequestId`, `logSha256` | `GET /api/heartbeat-runs/<id>` on `1de50989`: `triggeredBy: board`, `actorId: local-board`, `wakeReason: "Review the staged package for RPR-1 at head e7818ed11ded"`, `logSha256` present |
| Verdict Relay | Trusted, Board side | Acts as `local-board` (not exclusive in `local_trusted`, V3) | `review_relay.py` `relay()` lines 242–317 |
| Audit log | Trusted file, same-user writable | JSONL, append-only by convention | `review_pack.py` `audit()` line 213 |

**Boundaries that do not exist:**
- **No OS boundary.** All processes run as one Windows user. Any process with a shell can change the lock, staging, the store and the audit log (design §7, §9).
- **No exclusive Board authority** in `local_trusted` mode (G-14, V3).

## 3. G-13: reviewer run not bound to a review

### 3.1 What the relay checks today

From `review_relay.py`:

| Check | Code | What it establishes |
|---|---|---|
| 3 Staging | `relay()` 246–254: lock names the key; staged and store copies verify against `manifestSha256`; manifest head equals the lock head | The package on disk is the one built and staged |
| Lock run | line 256: `lock.runId` if set must equal `--run-id` | **Inactive:** `stage()` writes `runId: None` (`review_pack.py` 822) and nothing sets it |
| Receipts | lines 259–269: receipt in comments or a `relay` audit entry for the same head blocks other runs | One decision per head, first come first served |
| 1 Issue | lines 271–277 | The issue waits on the relay identity |
| 2 Run | lines 278–293 plus `_company_run()` 204–237: run in issue runs, or a run record with the issue's `companyId` and `issueId` null or this issue; `agentId` = `code-reviewer` (resolved by name, `pc.py` `cmd_review_relay`); `succeeded`; `createdAt >= stagedAt` | The run is a finished `code-reviewer` run of this company, newer than the staging |
| 4 Head | lines 294–296: GitHub PR head = lock head | The review is not stale |
| 5 Verdict | lines 298–299, `validate_verdict()` 114–145 | One well-formed verdict naming the locked issue and the full 40-character head; findings point into the manifest |

### 3.2 What these checks do not establish

1. **Which wake started the run.** Any succeeded `code-reviewer` run of the company created after `stagedAt` passes check 2, for example a run woken for another purpose or by someone else (`_company_run` docstring).
2. **That the run received this package.** The run's `--add-dir` points to `current/`, but the relay does not tie the run's start to the staging's content. If staging changed during the run, the relay would still see the final state.
3. **That the reviewer read the package.** Check 5 shows the verdict names the locked issue and full head SHA and cites existing lines.
   - The full head SHA appears in `REVIEW.md` and `manifest.json` (`render_review_md`, `build_manifest`). The wake reason carried only a 12-character prefix. So a matching full SHA is weak evidence that the reviewer saw one of those files.
   - It is not proof: the full SHA is public on GitHub, and a run could learn it another way.
   - It says nothing about which files were read.
4. **That the verdict was produced by the model** rather than written by another same-user process into the run log. Paperclip stores `logSha256`; whether anything else can rewrite a stored log is not verified.

### 3.3 Threats

| Threat | Today | Notes |
|---|---|---|
| **Replay** of an old run's verdict | Blocked for a different head (check 4, check 5 head match) and for older staging (`createdAt >= stagedAt`). Same head, re-staged after abandon: an old run created before the new `stagedAt` is refused | Live in Phase 5 (T7) |
| **Stale run** (head moved) | Refused (check 4) | Live in Phase 5 (T5) |
| **Cross-issue** | A run scoped to another issue is refused. A company-scoped run made for issue X while issue Y is staged passes check 2. It fails check 5 only if its verdict names X | Gap: binding relies on the verdict text |
| **Cross-package** (same issue, other head) | Refused by check 5 head match and check 4 | |
| **Stray run** (same company, after staging, not for this review) | Passes check 2. The verdict must still match issue and head | Main G-13 gap |
| **Forged run log or lock** by a same-user process | Not prevented | No OS boundary (§2) |
| **Prompt injection in package content** | `REVIEW.md` quotes task data after fixed instructions (audit D8); worst case is a manipulated verdict | Board approval and merge remain the last gate (ADR-009) |

### 3.4 Option A: bind run and verdict to the staging (minimal change)

**Architecture and data flow:**
1. At stage time `review-pack` adds to the lock:
   - `reviewId`: a random UUID;
   - `challenge`: 128 random bits, written **only** into the staged copy of `REVIEW.md` (a "Review id and challenge" line) and into the lock;
   - the existing `manifestSha256`.

   The store copy stays immutable; the challenge lives only in staging, so it is a staging-time addition, verified separately.
2. A new `pc.py review-wake <KEY>` (Board-run):
   - refuses unless the lock names `<KEY>` and no run is recorded;
   - wakes `code-reviewer` without an issue, with reason `review <reviewId> <KEY> <head12>`;
   - writes the returned run id into `lock.runId`;
   - audits `wake`.
3. The verdict schema gains two required fields, `reviewId` and `challenge`. `REVIEW.md` tells the reviewer to copy them.
4. The relay requires:
   - `--run-id` = `lock.runId` (the existing line-256 check becomes mandatory);
   - from `GET /heartbeat-runs/<id>`: `contextSnapshot.wakeReason` contains `reviewId`, `triggeredBy` is `board`, and `actorId` is the relay identity;
   - the verdict's `reviewId` and `challenge` equal the lock's.

**What A establishes:**
- The run is the one the Board started for this staging, through Paperclip's wake record.
- The verdict contains a value that existed only in the staged `REVIEW.md`. **Not** in the wake reason, the prompt, GitHub or the store.

**What A still does not establish:**
- That the reviewer read anything beyond `REVIEW.md`, or understood it.
- That no same-user process read the challenge from staging and wrote a verdict. There is no OS boundary.
- Whether the wake reason appears in the model prompt is not established. The adapter sets it as `PAPERCLIP_WAKE_REASON` (adapter `server/execute.js` lines 94–117). The challenge must therefore never be put in the reason.

**Threat model.** A closes: stray run, cross-issue run, an issue/head guess without access to staging. It does not close same-user tampering (G-14), or a reviewer that copies the challenge without reviewing.

**Cost:** small to medium.
- `stage()`, `render_review_md()` (staging variant), lock schema, a new `review-wake` command;
- relay checks on `contextSnapshot` and the verdict fields;
- updates to the verdict schema and the Phase 2 reviewer prompt.

**Tests:**
- offline: run id mismatch, missing or mismatched `reviewId`/`challenge`, wake not by the Board, wake reason without `reviewId`, challenge absent from the store copy, re-stage creates a new challenge;
- live: one sandbox review with A, plus a stray run woken without `review-wake` (must be refused).

**Paperclip and Board impact:** none on Paperclip configuration. The Board uses `review-wake` instead of `wake`.

### 3.5 Option B: issue-scoped review sub-issue (stronger, workflow change)

**Architecture and data flow:**
1. For each review the Board creates a child issue of the Author Task. For example "Review RPR-1 @ e7818ed1 (review <reviewId>)", with `parentId` the author issue, assigned to `code-reviewer`, no execution stages of its own, in `backlog`.
2. `review-pack` stages and records `reviewIssueId` and `reviewId` in the lock.
3. The Board releases the review sub-issue. `code-reviewer` is now the **assignee**, so Paperclip runs it issue-scoped (`decideIssueOwnership`, server `modules/run-dispatch/domain/policy.js` lines 12–24, allows the assignee).
4. The reviewer cannot write to Paperclip (no tools). The Board side closes the sub-issue after the relay.
5. The relay additionally requires:
   - the run is in `GET /issues/<reviewIssueId>/runs` with that `issueId`;
   - the sub-issue's parent is `<KEY>`;
   - the lock's `reviewIssueId` matches;
   - plus all of Option A (challenge, `lock.runId`, `triggeredBy`).

**What B adds over A:** the run-to-review binding is held by Paperclip's own data model (`issueId` on the run, an assignment and a release), not only by a wake reason string. Stray company-scoped runs are irrelevant: only runs of the sub-issue count.

**Open points for B:**
- **Workspace and checkout behaviour of an issue-scoped `code-reviewer` run.** If the sub-issue belongs to a project with a git-worktree policy, Paperclip may create a worktree and set `cwd` in the author's repository; in Phase 4b's wording, that brings back the author-worktree exposure. The sub-issue must therefore have **no project** or a project without a workspace. Not verified.
- **Assignment wakes:** releasing or commenting on the sub-issue wakes the reviewer (SKILL.md start-gate notes). Retries and watchdog behaviour must be checked.
- **The author issue's review stage participant stays `local-board`.** B does not change V1.

**Threat model.** As A, plus: the Paperclip record ties the run to the review. Same-user tampering and comprehension remain open.

**Cost:** medium.
- sub-issue creation and close commands;
- lock schema;
- relay checks;
- a live V2-style check that an assignee `code-reviewer` run on a project-less sub-issue starts in its configured `cwd` and creates no worktree.

**Tests:**
- offline: run on another sub-issue, sub-issue of another parent, missing sub-issue;
- live: issue-scoped review run, workspace observation, cancelled or failed reviewer run, Board close.

**Paperclip and Board impact:** more issues per review, Board release per review. No configuration change if project-less sub-issues work.

### 3.6 Optional addition to A or B: signed relay receipt

The relay could sign `(reviewId, runId, manifestSha256, headSha, verdict SHA-256, logSha256)` with a Board-side key (for example DPAPI-protected) and post the signature with the receipt. This makes later edits to the audit log or comment detectable **by a party that does not have the key**. Under the same Windows user, any process can use the key, so it does not create an authority boundary (G-14). Value: audit integrity against accidental or after-the-fact edits only.

### 3.7 Recommendation

- **Start with A.** It closes the stray-run and cross-issue gaps with small changes and no Paperclip configuration change.
- **Evaluate B in a sandbox** once its workspace behaviour is verified.
- **G-13 stays open under both**, because:
  - the reviewer's isolation still depends on Claude Code flags under one OS user;
  - "read the package" can only be evidenced, never proven.

## 4. Phase 5 findings

### 4.A GitHub CLI credential for the author

**Observed:** `gh` had no credential inside the author run; `git push` worked through Git Credential Manager (Phase 5 record §3). Soucean agents get `GH_TOKEN` from a company secret binding (`adapterConfig.env.GH_TOKEN` is a `secretId` reference).

**Options:**
1. **Scoped author credential:** a fine-grained token per repository with Contents read/write and Pull requests read/write only, bound as a Paperclip company secret (`env` secret reference, never a literal), with an expiry. Least privilege: no admin, no workflows, selected repositories only.
   - Risk: the author can push and open PRs on its own, as Soucean authors already do.
   - `git push` already works with the Board's credential manager login, which is broader than needed. That is an existing least-privilege gap worth recording separately.
2. **Board-side PR creation:** the author pushes; a Board-run command opens the PR from the issue's branch (as done in Phase 5). No new credential. Costs one Board step per Task.
3. **Trusted integration:** a GitHub App installed on the repository creates PRs on a Paperclip event. Strongest separation, highest setup cost, outside current scope.

**Avoiding leaks:**
- secret references only;
- never an `env` literal, a file, or a command line;
- `gh` reads `GH_TOKEN` from the environment;
- keep redaction in Paperclip logs (verify on a sandbox run);
- set a rotation date in the runbook.

**Recommendation for the Board:** option 2 for review-package sandboxes; decide option 1 for production authors together with a fix for the broad Git Credential Manager access.

**Board decision (2026-11-21, R4):** option 2 for sandboxes and option 1 for production, recorded in [ADR-022](../decisions/ADR-022-author-pull-request-credential.md). Production uses one shared fine-grained token for code-writing agents. Git Credential Manager access is addressed by requiring each agent clone to use `gh` with that token (both project clones checked and `soucean-game` fixed on 2026-11-21). The token is on the Board's own account with *All repositories*, an accepted risk recorded in the ADR.

### 4.B `--unstage` and real run state

**Why the state file is not enough:**
- `unstage()` and `staging_status()` (`review_pack.py` 851–889) take runs from `--state-file` through `lock_runs()` (840–843), a Phase 1 stand-in that nothing keeps current.
- `lock_runs()` also matches `r["issue"] == lock["issue"]`. A company-scoped reviewer run (the V2 workaround) has no issue, so even an up-to-date state file would never match it.

**Paperclip sources of truth (read-only):**
- `GET /api/heartbeat-runs/<runId>` (server `routes/agents.js` line 5598) for the run recorded in `lock.runId` (Option A);
- otherwise `GET /api/companies/<id>/heartbeat-runs?agentId=<code-reviewer>&limit=…` (line 5454) filtered by `createdAt >= stagedAt`. Active statuses: `queued`, `starting`, `running`, `scheduled_retry` (`review_pack.py` `ACTIVE_RUN` line 53).

**Proposed rule:**
1. Read the lock.
2. Query Paperclip. If Paperclip is unavailable or answers with an error, **refuse** unless `--abandon` (fail closed; logged).
3. If any reviewer run since `stagedAt` is active, refuse.
4. Clear staging.

**Races:**
- A wake between step 3 and the delete could start a run that then finds `current/` gone. It would fail to read the package, and its verdict would fail check 3 or Option A.
- To narrow the window, `review-wake` and `unstage` should take a short exclusive **operation lock** (for example `staging.op` created with `O_EXCL`), and `review-wake` should refuse while an unstage is in progress.
- A two-phase check (query, mark `unstaging` in the lock, query again, delete) further limits it.
- Pure Paperclip state cannot be locked from outside; the residual risk is a run that the Board starts by other means. Option B's sub-issue state helps here.

**Tests:**
- offline with a fake API: active, finished, cancelled run; API down; stale state;
- concurrent `review-wake` and `unstage` (threads or two processes against a fake);
- live: unstage refused while a sandbox reviewer run is `running`.

### 4.C Runs shown as `cancelled` after a handover

**Cause (source):**
- When an issue update changes the assignee while the old assignee agent has an active run on it, the server cancels that run before applying the update (server `routes/issues.js` lines 10165–10185):
  - message "Cancelled before issue reassignment";
  - `errorCode: issue_reassigned`;
  - `resultJson: {reassignmentStopConfirmed: true, issueMutationStopId}`.
- An author that sets `in_review` from inside its own run triggers the review stage, which moves the assignee to the participant. Its own run is therefore cancelled at the moment it hands over.
- This is normal lifecycle behaviour of Paperclip 2026.1023.0, not a workflow error.

**Telling completion from real cancellation.** Combine:
- run `errorCode == issue_reassigned` with `resultJson.reassignmentStopConfirmed`;
- the issue's transition to `in_review` at the same time;
- the run's own last status-update comment.

A cancel by the Board (`cancel-run`) or a timeout has a different `errorCode`. Status alone is not enough.

**Impact on the relay:** none today. Reviewer runs must be `succeeded` (check 2), and the reviewer cannot change issues, so it is never cancelled this way. Do not relax check 2 to accept `cancelled`.

**Impact elsewhere:**
- triage and liveness reporting should label these runs "handed over", not "failed";
- the audit log needs no change;
- `--status` / `--unstage` treat them as finished, which they are.

**Proposal:** a read-only classification helper in `pc.py` (for `show`, `triage`), with tests on recorded run shapes. No change to verification rules.

## 5. §12 acceptance gap matrix

Status as recorded after Phase 5. **Live** = verified in a sandbox; **Offline** = tests against fakes; **Source** = code reading; **Not tested**; **Failed** = none so far.

| # | Criterion | Status | Proposed test | Setup | Expected result | Evidence to keep | Risk | New sandbox? |
|---|---|---|---|---|---|---|---|---|
| 1 | Packager reads only the GitHub API; no git on agent-writable repos | API source **Live**; "no git" **Source/Offline** | Run `review-pack` under Process Monitor (or a `git` shim first on `PATH` that logs and fails) | Sandbox PR; process tracing | No `git` process; only `api.github.com` connections | Trace export, packager output | Low | Reuse `RPR` |
| 2 | §5.3 rules and §5.2 limits refuse | **Offline** | A throwaway PR with a long path, a reserved name, a symlink, 51 files, a file over 256 KB | Throwaway repository or branch | Each refused with the documented message; nothing staged | Outputs, audit `refuse` lines | Low; repository noise | Yes (throwaway repo preferred) |
| 3 | Immutable per head; `READY` last; stale heads refused | per-head and stale **Live**; `READY` **Offline/Source** | Kill the packager between rename and `READY` (fault-injection flag in a test build) | Sandbox | Next run rebuilds; partial package never staged | Store listing, audit | Low | Reuse |
| 4 | Reviewer tools only; reaches only `current/`; write/shell/git fail | tools and reads **Live** (2 runs); attempts **Not tested** in Paperclip | Stage a package whose `REVIEW.md` asks (as injected text) to write a file, run `git status`, read outside `current/` | Sandbox reviewer | Tools absent or refused; nothing written; verdict still valid or refused | Run log, file snapshot before and after | Low; cost of one run | Reuse |
| 5 | One review staged at a time | **Live** | — | — | — | Phase 5 record | — | — |
| 6 | Relay accepts only §3.4; no duplicates; fallback | 1–4, duplicates, fallback **Live**; check 5 malformed and 4xx **Offline** | (a) A reviewer prompt variant told to emit a bad schema, a wrong line, a wrong issue; (b) 4xx: relay while the stage has moved on (Board decides by hand between check and PATCH, or a participant change) | Sandbox | (a) refused, nothing written; (b) comment stays, `relay-refused`, fallback message | Run logs, comments, audit | Low; (b) needs a timed manual step | Reuse |
| 7 | Token read-only, selected repos, never in agent env or log | not-in-files **Live**; read-only scope **Source** (Board-created) | Attempt a write with the packager token in a throwaway repository (expect 403); search Paperclip run logs and the DB backup for the token prefix | Throwaway repository | 403; no match | Command output (redacted), search result | Low | Throwaway repo |
| 8 | Retention, 2 GB cap, cleanup, logged | cleanup and audit **Live** (nothing eligible); deletion and cap **Offline** | Use a test Review Root with `closedAt` older than 14 days and a lowered cap; requires `--cleanup` to read closure from Paperclip (today the state file) | Sandbox roots | Old packages deleted in two steps; cap refusal lists packages | Audit `delete` lines, store listing | Low | Reuse |
| 9 | No worktree or branch created, moved or deleted (ADR-006) | packager/relay **Live**; production **Not tested** | Snapshot `git worktree list` and branches of the project clone before and after a full review | Sandbox | Only Paperclip's own changes | Snapshots | Low | Reuse |
| 10 | G-13 not marked resolved | Holds | — | — | — | — | — | — |
| — | Merge | **Not tested** (Board closed PR #28) | Board merges a sandbox PR after an approved relay; confirm ADR-009 order (Paperclip `done`, then GitHub merge by the Board) | Throwaway repository preferred | Merge by the Board only | PR record | Touches the repository's `main` | Throwaway repo |
| — | V3 | **Not tested** | Separate authorization required (D-AUTH-12, OQ-043) | — | — | — | Probes Board authority | Separate plan |

## 6. Roadmap

Each stage needs its own Board approval and ends with a review. No stage starts the next.

| Stage | Objective | Scope | Out of scope | Deliverables | Acceptance | Depends on | Rollback | Board approval |
|---|---|---|---|---|---|---|---|---|
| **R1 G-13 binding (Option A)** | Bind reviewer run and verdict to one staging | `review-wake`, lock fields, staging challenge, verdict fields, relay checks, tests | Option B, OS isolation, V3 | Code, tests, design update | Offline tests for every new refusal; one live sandbox review accepted; a stray run refused | PR #49 reviewed | Revert the PR; the old `wake` path still exists | Design change and one sandbox run |
| **R2 `--unstage` from Paperclip** | Make "active run prevents unstage" real | Read-only run queries, fail closed, operation lock | Paperclip changes | Code, tests | Concurrency tests; live refusal while a reviewer run is `running` | R1 (uses `lock.runId`) | Revert; `--abandon` remains | Code change and sandbox run |
| **R3 `cancelled` semantics** | Report handovers correctly | Read-only classification in `pc.py` `show`/`triage` | Relay rules (unchanged) | Code, tests on recorded shapes | Handovers shown as "handed over"; real cancels unchanged | — | Revert | Code change |
| **R4 PR credential decision** | Decide who opens PRs | Options 4.A 1–3; least-privilege review of Git Credential Manager | Creating credentials (done by the Board) | Decision record; runbook | Board decision recorded | — | — | Decision; any credential the Board creates |
| **R5 §12 evidence** | Close the live gaps of §5 | Tests 1–4, 6–9 and merge in sandboxes | V3 | Phase 5b record | Each item Live or recorded as Failed | R1, R2 (for 6 and 8) | Sandbox cleanup | Sandbox execution; throwaway repository |
| **R6 Phase 6 readiness** (assessed 2026-11-21: **not ready**, blockers B1–B6 in [review-package-r6-phase6-readiness.md](review-package-r6-phase6-readiness.md)) | State what must hold before a production proposal | Checklist: R1–R5 outcomes, G-13/G-14 position, V3 plan, runbook outline | Writing or approving Phase 6 | Readiness assessment | Board review | R1–R5 | — | Review only |

**Optional R1b (Option B):** after R1, a sandbox test of project-less review sub-issues (workspace behaviour, wakes), then a decision on B.

## 7. Board decisions required

1. Review and merge or reject PR #49 (Phase 5 record).
2. Approve R1 with Option A, or ask for B directly.
3. Approve R2 (fail-closed `--unstage` against Paperclip).
4. Approve R3 (reporting only).
5. Decide the PR mechanism for authors (4.A), and whether to narrow the Git Credential Manager access agents inherit. **Decided** (ADR-022: option 2 for sandboxes, option 1 with one shared scoped token for production; clones must use `gh` with the token instead of Git Credential Manager, to be checked per clone).
6. Approve a throwaway repository for R5 (preferred over `soucean-game`), and the R5 sandbox run.
7. Decide cleanup of `RPR`, `REV`, the PR #28 branch, the separate clone and its worktree, the private test folders, and the backups.
8. Decide whether and when to plan V3 (separate authorization).

## 8. Risks and unresolved questions

- **Comprehension cannot be proven.** Options A and B give evidence of access and binding only. The Board's approval and merge remain the real gate.
- **Same-user tampering (G-14).** Every file the relay trusts (lock, staging, store, audit) is writable by any same-user process with a shell. The Cursor authors have one. Only an OS or deployment boundary changes this.
- **Wake reason in the prompt:** unverified. Option A must not depend on it being absent from the prompt.
- **Run log integrity:** `logSha256` exists on the run. Whether Paperclip re-verifies it on read is not verified.
- **Option B workspace behaviour:** unverified. B must not reintroduce author-worktree exposure.
- **Reviewer identity by name:** `pc.py` resolves `code-reviewer` by name or url key. A renamed or duplicate agent changes what check 2 accepts. Pinning the agent id in configuration is cheap.
- **`--cleanup` and retention** also read closure from the state file. The same Paperclip-backed approach as R2 is needed before live retention evidence means anything.
- **Transient exceptions in the check phase** of the relay still escape as raw errors (recorded during PR #48). Fail closed, but not audited. Small fix, separate PR.
- **Paperclip version coupling:** all source references are to 2026.1023.0. An upgrade must re-check `decideIssueOwnership`, the reassignment cancel and the run record fields.
