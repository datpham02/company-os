# Review Package R2: Paperclip-backed `--unstage` (R2-A design)

- **Status:** IMPLEMENTED (2026-11-21).
  - The design (R2-A) was written as code reading only, with no code or Paperclip change.
  - The Board Operator approved it with the proposed decisions (§5), and it was implemented in PR #53 (R2-B to R2-D), checked live on the `OPT` sandbox (R2-E), and corrected after a self-review in PR #54 (§3.1).
  - Results and live evidence: [review-package-r2-results.md](review-package-r2-results.md).
  - The rest of this document keeps the R2-A analysis as written; §1 describes the code *before* R2.
- **Code read:** `main` at `3a5ba8b` (PR #51 merged):
  - `.claude/skills/paperclip/scripts/review_pack.py`: `unstage`, `staging_status`, `lock_runs`, `relayed`, `stage`, `update_lock`, CLI;
  - `review_relay.py`: `review_start`, `_op_lock`, `_matching_runs`;
  - `pc.py`.
- **Paperclip sources read (2026.1023.0):** `shared/dist/constants.js` (`HEARTBEAT_RUN_STATUSES`); server `routes/agents.js` (5454, 5598); `services/heartbeat/run-state.js` (1186 ff.).
- **Out of scope:** reviewer profile and Paperclip configuration; relay verdict rules; OS isolation and G-14; Author Task workflow; Soucean; cleanup of REV/RPR/OPT; Phase 6; V3.

## 1. Current behaviour (code, `main` 3a5ba8b)

`review_pack.unstage(rr, sr, state, abandon, now)`:
1. Refuses if `staging.op` exists. It only *checks* the file; it does not take it.
2. No lock: nothing staged, or orphaned files that only `--abandon` clears.
3. **Active runs come from the state file:** `lock_runs(state, lock)` filters `state["runs"]` by `issue == lock.issue`, agent name `code-reviewer`, `lock.runId` if set, and `createdAt >= stagedAt`. The statuses in `ACTIVE_RUN` (`queued`, `starting`, `running`, `scheduled_retry`) refuse.
4. Not relayed (no `relay` audit entry for this issue and head since `stagedAt`) refuses unless `--abandon`.
5. Clears `current/`, the lock and leftovers; audits `unstage` or `abandon`.

**Why that is not enough:**
- The state file is a Phase 1 stand-in that nothing keeps current.
- Under Option B the reviewer runs on the review **sub-issue**, so `issue == lock.issue` never matches a real reviewer run, even with a current state file.
- Any run of the reviewer agent can read `current/`, because the agent's `--add-dir` is fixed to it. That includes Paperclip's `issue_disposition_repair` follow-up, a retry after `interrupted`, and a stray company-scoped wake. The lock's own run is not the only one that matters.
- `staging_status` (`--status`) uses the same state file for "active" and "stale".

**`review-pack` itself must stay network-free.** `test_review_pack.py` `NoForbiddenCapabilities` forbids `urllib`, `socket`, `subprocess`, `import pc` and others in `review_pack.py`. Paperclip calls therefore belong in `review_relay.py` / `pc.py` and are injected.

## 2. Facts from Paperclip and the lock

**Run statuses** (`HEARTBEAT_RUN_STATUSES`): `queued`, `scheduled_retry`, `running`, `succeeded`, `interrupted`, `failed`, `cancelled`, `timed_out`. There is **no `starting`** (it is in `review_pack.ACTIVE_RUN` and `pc.ACTIVE_RUN`; harmless, kept for compatibility).

**APIs:**

| Call | Use | Source |
|---|---|---|
| `GET /api/heartbeat-runs/<runId>` | One run: `id`, `companyId`, `agentId`, `issueId`, `status`, `createdAt` (observed live in Phases 4b, 5 and the Option B check) | `routes/agents.js` 5598 |
| `GET /api/companies/<id>/heartbeat-runs?agentId=<id>` | **Every** run of that agent in the company, newest first. Without `limit` there is no limit; with `limit` it is capped at 1000 | `routes/agents.js` 5454; `run-state.js` `listRuns` 1186–1212 |

**Lock schema after Option B and R1** (`review_pack.stage`, `review_relay.review_start`):
- `issue`, `headSha`, `packagePath`, `manifestSha256`, `stagedAt`, `stagedBy`;
- `runId`, null until a review run is recorded;
- `reviewId`, `challenge`, `challengeSha256`;
- `reviewIssueId`, `reviewIssueKey`;
- `reviewStart`: `null` / `creating` / `create-refused` / `sub-issue-created` / `waking` / `wake-refused` / `started`.

A lock written before Option B has none of the last four groups.

## 3. Design

### 3.1 What decides "a reviewer run may still be using staging"

**The reviewer agent, not one run.** Unstage asks Paperclip for **all runs of the `code-reviewer` agent** of the reviewed issue's company:
- `GET /companies/<company>/heartbeat-runs?agentId=<reviewer>`, without `limit`;
- refuse if **any** run has an **active** status, whenever it was created. A run that started before this staging still has the agent's fixed `--add-dir` and can read it;
- for `interrupted` and unknown statuses, only runs created at or after `stagedAt` count.

*Corrected after the R2 self-review (2026-11-21).* The first version of this design, and the code merged in PR #53, kept only runs created at or after `stagedAt`, so a still-active older run was ignored. Fixed in the follow-up PR, with a regression test.

This covers:
- the lock's run;
- retries;
- `issue_disposition_repair`;
- any stray wake.

They all share the agent's fixed `--add-dir`.

**Status policy:**

| Status | Unstage |
|---|---|
| `queued`, `scheduled_retry`, `running` | **Refuse**, even with `--abandon`. Cancel the run first (`pc.py cancel-run <id>`) |
| `interrupted` | **Refuse unless `--abandon`**. Paperclip may still recover or retry the work |
| `succeeded`, `failed`, `cancelled`, `timed_out` | Allowed (then the relayed/abandon rule applies) |
| Any other value | Refuse unless `--abandon` (unknown schema) |

**When the lock names a run** (`runId`), it is also read by id and must be:
- that run (`id`);
- of the reviewer agent;
- in the parent's company;
- scoped to `reviewIssueId`.

A mismatch, or a run that does not exist, refuses unless `--abandon`. A **confirmed active run is never overridden**.

### 3.2 Identity of company and reviewer

- **Company:** `GET /issues/<lock.issue>` → `companyId`.
- **Reviewer:** the company's `code-reviewer` by name (as `review-start` and `review-relay` do).

To bind this to the staging, `review-start` would additionally record `companyId` and `reviewerAgentId` in the lock when it creates the sub-issue. Unstage then prefers the lock's values and refuses if the name lookup disagrees. Locks without them (pre-start, or older) use the lookup.

### 3.3 Fail closed, and what `--abandon` may override

| Situation | Without `--abandon` | With `--abandon` |
|---|---|---|
| Paperclip unreachable, error, timeout, malformed list or record | Refuse | Allowed, audited as `abandon` with the reason "reviewer state unverified: …" |
| Lock missing required fields, or `runId` record missing/mismatched | Refuse | Allowed, audited |
| Any reviewer run `interrupted` or unknown status | Refuse | Allowed, audited |
| Any reviewer run `queued` / `scheduled_retry` / `running` | Refuse | **Refuse** (cancel the run first) |
| Review not relayed | Refuse | Allowed, audited (unchanged) |
| `reviewStart` is `creating` or `waking` (a start may be in flight) | Refuse | Allowed only if the agent-wide check shows no active run; audited |

**`--abandon` is a deliberate escape, not evidence.** The audit line records that the reviewer's state was not verified, and why.

### 3.4 Race handling (`staging.op`)

`unstage` takes `staging.op` itself, with the same exclusive create (`O_EXCL`) as `review-start`, and releases it in `finally`. Sequence:
1. take `staging.op` (refuse if it exists: another `review-start` or `unstage` is running, or a crash left it; never taken over);
2. read the lock;
3. **check 1:** the Paperclip agent-wide check, plus the `runId` check if present;
4. write `unstaging: <iso time>` into the lock (`update_lock`, atomic replace);
5. **check 2:** repeat the Paperclip check, to catch a run that a wake outside this tool started in between;
6. clear `current/`, then the lock (the lock last, so a crash leaves a lock that still says `unstaging`);
7. audit; release `staging.op`.

**`review-start` refuses a lock with `unstaging` set** ("an unstage was interrupted; finish it with --unstage"). A later `unstage` of such a lock resumes from step 3.

**Remaining window:** a run started by something other than `review-start` (for example a manual `pc.py wake code-reviewer`) between check 2 and the delete is not prevented. Paperclip state cannot be locked from outside. The window is milliseconds; a run in it fails to read a vanished package, and the relay would refuse its verdict.

### 3.5 Code placement

- **`review_pack.unstage(rr, sr, state, abandon, now, reviewer_runs=None)`:**
  - `reviewer_runs` is an injected callable `(lock) -> classification` that does the Paperclip check;
  - when it is `None` (no Paperclip available) the result is "unverified": refuse unless `--abandon`;
  - `review_pack` stays network-free; the state file is no longer consulted by `unstage`;
  - `--state-file` stays accepted for compatibility and for `--cleanup`.
- **`review_relay.reviewer_run_state(api, lock, sleep)`:** the Paperclip queries and the classification (`active`, `clear`, `unverified` with reasons, `mismatch`).
- **`pc.py`:** wires `review-pack --unstage` through a wrapper that passes the classifier bound to `pc.call`.
- **`staging.op`:** the helper moves to `review_pack` (file-only) and is shared by both commands.
- **`staging_status` (`--status`):** *done after R2 in a follow-up PR:* through `pc.py` it reports the same Paperclip classification and hides the challenge; outside `pc.py` it falls back to the state file. Originally: a follow-up option is to report the same Paperclip classification. It is not required for R2 acceptance; it stays on the state file until then.

### 3.6 Audit

- `unstage` / `abandon` lines gain `reviewerRuns`: ids and statuses checked, and the agent id; and `verified: true|false` with the reason.
- A refusal writes `refuse` with `unstage: <reason>`, naming the blocking run.

## 4. Tests (R2-D, after approval)

**Offline, with a fake Paperclip:**
- run `running`, `queued`, `scheduled_retry`: refuse, also with `--abandon`;
- `interrupted` or unknown status: refuse, allowed with `--abandon` (audited);
- `succeeded`, `failed`, `cancelled`, `timed_out`: allowed if relayed or `--abandon`;
- an active `issue_disposition_repair` or company-scoped run of the reviewer after `stagedAt`: refuse;
- a run of another agent, or one created before `stagedAt`: ignored;
- Paperclip unreachable, 5xx, malformed list or record: refuse; `--abandon` allowed and audited "unverified";
- `runId` record missing, other id, agent, company or issue: refuse unless `--abandon`;
- lock without `runId` before a start: agent-wide check decides;
- `reviewStart` `creating` / `waking`: refuse unless `--abandon` with no active run;
- `staging.op` present: refuse; `unstage` takes and always releases it;
- `review-start` during `unstage` (threads): exactly one proceeds;
- crash after `unstaging` was written: `review-start` refuses, `unstage` resumes;
- check 2 sees a run that started after check 1: refuse, staging intact;
- no `reviewer_runs` provided: refuse unless `--abandon`;
- every existing unstage, staging and cleanup test still passes.

**Live (R2-E, sandbox OPT only, needs approval):**
1. stage `OPT-3`;
2. `review-start` (resumes the reviewer for one run);
3. while the run is `running`, `--unstage` and `--unstage --abandon` both refuse; lock and staging unchanged;
4. after the run ends: pause the reviewer, relay, then `--unstage` succeeds;
5. record audit lines, issue and run counts, agent states.

Expected cost: one reviewer run (about US$0.05).

## 5. Board decisions (taken 2026-11-21)

All proposed options were approved ("Duyệt, làm R2-B–D", then "Duyệt R2-E"):
1. **Confirmed-active runs** refuse even with `--abandon`. Implemented.
2. **`interrupted`** refuses unless `--abandon`. Implemented.
3. `review-start` records `companyId` and `reviewerAgentId` in the lock. Implemented.
4. **`--status`** stays a follow-up: it still reads the state file.
5. R2-B to R2-D were approved and implemented (PR #53); R2-E was approved separately and run on `OPT`.

## 6. Risks kept

- `staging.op` coordinates only processes that use it; a same-user process can still call Paperclip or edit the files (G-14).
- The window between check 2 and the delete cannot be closed from outside Paperclip.
- `--abandon` is a deliberate escape, not proof that the reviewer stopped.
- R2 does not address G-13 (whether the reviewer understood the package) or G-14.
