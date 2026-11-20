# Authentication migration, Phase A.2: readiness assessment

- **Status:** `PROPOSED`. A planning and audit document only. It does not authorize Phase B or any runtime action.
- **Date:** 2026-11-20. Paperclip 2026.1023.0.
- **Repository:** `datpham02/company-os`. `main` is at `78341b1`; the working tree is on `docs/sandbox-cancel-accuracy`, which has the same content.
- **Inputs:**
  - [auth-migration-phase-a1.md](auth-migration-phase-a1.md) (cited as "A1");
  - [auth-migration-board-decisions.md](../roadmap/auth-migration-board-decisions.md) (D-AUTH-01 to D-AUTH-05);
  - [step2-board-decisions.md](../roadmap/step2-board-decisions.md) §6a and §6b;
  - [open-questions.md](../roadmap/open-questions.md);
  - the Paperclip source.
- **Test cases:** [auth-migration-verification-plan.md](auth-migration-verification-plan.md).

**Evidence levels:**
- **Source:** read in the installed Paperclip source.
- **Sandbox runtime:** observed in the OQ-043 sandbox on 2026-11-20, with no agent runs.
- **Live read:** GET requests against the studio instance on 2026-11-20.
- **Proposed:** a design.
- **Not verified.**

Source paths are relative to `node_modules\@paperclipai\server\dist` (`S`) and `node_modules\@paperclipai\shared\dist` (`SH`) inside the global `paperclipai` install.

## 1. Overall readiness

**Not ready for Phase B.** Four direct blockers:
1. **D-AUTH-03 fails at source level.** Paperclip's scheduler never re-wakes a reviewer that has never had a run on the issue, which is exactly the OQ-035 case (§3.C). Under D-AUTH-03 the question goes back to the Board.
2. **None of the migration steps is runtime-verified:** board claim, participant update, CLI identity, and the rollback by mode switch.
3. **The credential storage design** (D-AUTH-04) needs a security decision. Paperclip offers only a plaintext store.
4. **Traceability gaps:** the Phase A.1 report and the decision record are not committed, and the Phase A audit exists only outside the repository.

## 2. Workstream A: evidence matrix

| Item | Evidence level | Evidence location | Result | Limitation | Next action |
|---|---|---|---|---|---|
| `authenticated` mode starts on Windows | Sandbox runtime | step2-board-decisions §6b; commit `c126202` (PR #38) | Instance started and answered health | One isolated instance, no agents, one session | Re-confirm in the verification environment (VA-1) |
| Keyless Board access rejected | Sandbox runtime + Source | §6b (403 / 401 for every keyless request); `S\middleware\auth.js` 153-163 | Keyless requests are refused in `authenticated` | No live check; no agent-originated request | VA-1 |
| Board claim flow | Source only | `S\board-claim.js` 31-103; `S\routes\access.js` 2096-2125; `S\index.js` 547, 1620-1629 | Claim moves instance admin from `local-board` to the claimer and makes it owner of every company | **Not run.** The sandbox used a manual promotion instead | VA-2 |
| Board identity via `/api/cli-auth/me` | Sandbox runtime (one call) + Source | §6b (T2.6 answered 200); `S\routes\access.js` `/cli-auth/me` | Returns the token's user | Not checked after a claim; the response fields were not recorded | VA-3 |
| Board token authentication | Sandbox runtime + Source | §6b (CLI login token used for T2/T3); `S\middleware\auth.js` 240-256 | Board key acts with the owner's live access | Expiry, revocation and 401 text not exercised | VA-3, VA-7 |
| Agent API authentication | Sandbox runtime (agent key, no runs) + Source | §6b T1.11-T1.15, T3.5-T3.9 | Agent keys keep same-company reads, refuse admin reads and cross-issue writes without a run | **No agent run**, so per-run keys, helper scripts and MCP are not verified | VR-8 (needs agent-run approval) |
| CLI credential storage and expiry | Source | A1 3.1-3.10; `S\services\board-auth.js` 5, 115-123, 159-180; CLI `dist\index.js` 25158-25284 | Plaintext `auth.json`; 30-day keys; no refresh; no lock; non-atomic write | Not observed on the studio host; no `auth.json` exists there (live read of the folder only) | Security decision (§3.D) |
| Issue participant migration | Source | §3.B below | Works for issues without an active stage; refused (422) for an active `in_review` stage under the guard | **Not run** | VA-4, VA-5 |
| `executionPolicy` update and concurrency guard | Source | `S\services\issues.js` 7444-7456, 7793-7795; `S\routes\issues.js` 9660-9662, 10009-10012 | `expectedExecutionPolicy` is a compare-and-set under a row lock (409 on mismatch) | Only the policy column is guarded; not run | VA-4 |
| Scheduler vs watchdog | Source | §3.C below; `S\services\recovery\service.js` 2938-2944, 3412-3440 | The sweeper **skips** a reviewer with no run on the issue, so OQ-035 is not recovered | Which branch dropped the original wake in OQ-035 is unknown | Board decision (§6); VR-1 if agent runs are approved |
| Sandbox cleanup | Live read (2026-11-20, A.2) + records | step2-board-decisions §6b; commits `42ca684`, `5eb1078` | `C:\OQ-043-Sandbox`, the `paperclip-sandbox` user and profile, and the folder deny rule are gone; ports 3200 and 54339 are closed | `C:\OQ-042-Sandbox` (an older experiment, OQ-042) **still exists** | Track separately (§4) |

## 3. Workstream findings

### 3.A Evidence reconciliation

- The Step 2 sandbox proved only two things: basic `authenticated` behaviour on Windows, and that keyless Board access is refused (§6b).
- It did **not** exercise:
  - the board claim (a manual promotion was used instead);
  - script authentication (`pc.py` simply received a 403);
  - agent runs;
  - any migration step.
- **Traceability gaps:**
  - `auth-migration-phase-a1.md` and `auth-migration-board-decisions.md` exist only in the working tree; they are not committed.
  - The Phase A audit (`phase-a-auth-migration-audit.md`) was delivered outside the repository and is not tracked. *(Later resolved by D-AUTH-08: added as [auth-migration-phase-a-audit.md](auth-migration-phase-a-audit.md).)* `docs/architecture/auth-migration-audit.md` does not exist.

### 3.B D-AUTH-02: participant migration (Source)

**Data model:**
- Each participant is `{id, type, userId | agentId}`.
- Ids are kept when supplied: `S\services\issue-execution-policy.js` 253 for participants, 271 for stages.
- **Participants are deduplicated by principal, not by id** (262-266). If the new user is already a participant of the same stage, the edited entry is silently dropped.
- Empty participants are filtered out (258), and a stage left with no participants is dropped (268-269).

**The guard:**
- `expectedExecutionPolicy` needs a policy-only body (`S\routes\issues.js` 9660-9662).
- It is compared with `isDeepStrictEqual` against the raw stored policy, under a `SELECT … FOR UPDATE` row lock (`S\services\issues.js` 7444-7456). A mismatch returns 409 `execution_policy_changed`.
- With the guard present, any change to status or assignee returns 422 (`S\routes\issues.js` 10009-10012).

**Case (a): no active stage.** This covers `backlog` issues such as SOU-17 and SOU-30 at the last read.
- Only `executionPolicy` changes; `executionState`, status and assignee are unchanged.
- No decision row is written.
- Activity log: `issue.updated` and `issue.approvers_updated`, which records the change as a removal plus an addition.

**Case (b): active `in_review` stage held by `local-board`.** This covers SOU-28 at the last read.
- The guarded body is **rejected with 422 and nothing is written**, because the transition would move the assignee to the new user.
- Without the guard, the stage is kept, the participant and assignee become the new user, and no decision row is written. The membership check `assertAssignableUser` (`S\services\issues.js` 4661-4669) requires the new user to be an active company member.
- The unguarded form loses the concurrency protection.

**Transactions:**
- The issue update is atomic (`S\services\issues.js` 7793-7795).
- Validation errors occur before the write.
- Activity rows are written after commit, outside the transaction.
- A user participant triggers no wake.

**Board override:**
- It does not fire on a policy-only body, because it needs a status or assignee change (`issue-execution-policy.js` 715-720).
- A policy-only update can still clear the stage, by changing a stage id or by deduplicating a stage's participants away.

**Mandatory invariants** for any participant update:
1. The stage set and every stage and participant id are unchanged.
2. Decision history (`issue_execution_decisions`) is untouched.
3. No unintended change to `executionState`, status or assignee.
4. No Board override is used to get past an unresolved decision.

**Safe sequence** (proposed; replaces nothing in D-AUTH-02):
1. **Before the switch, in `local_trusted`:** decide SOU-28 as `local-board` with `pc.py approve` or `request-changes`. This writes a real decision row and avoids case (b).
2. **Freeze new Board stages.** From the re-read (step 3) until the claim, do not create issues with `pc.py create`, because each one adds a `local-board` approver.
3. **Re-read immediately before the switch,** with GET only, for every company issue that is not `done` or `cancelled`:
   - the raw `executionPolicy` and `executionState`;
   - status, `assigneeUserId` and `assigneeAgentId`;
   - active runs.

   Any issue whose `executionState.currentParticipant` is `local-board` must be decided first, as in step 1.
4. After the switch and claim (D-AUTH-01), check that the new user is an active member (an owner, through the claim).
5. **For each issue in case (a):** a guarded policy-only PATCH that changes only `userId`. Check beforehand that the new user is not already a participant of that stage. Re-read afterwards and compare: same stage and participant ids, same order, no state change, `issue.approvers_updated` logged.
6. **On a 409:** re-read and retry once. On a 422: stop, because the issue has left case (a).

**Rollback:**
- For case (a), the reverse guarded PATCH. It has no membership check.
- Case (b) never happens in this sequence.

### 3.C D-AUTH-03: scheduler and watchdog (Source)

**How the review wake is created and lost:**
- On a stage hand-off the server cancels the author's running run and enqueues one fire-and-forget wake, `execution_review_requested` (`S\routes\issues.js` 1667-1712, 10167-10188, 11358-11393).
- That wake can be dropped in several ways, all without a retry:
  - **skipped:** for example `wakeOnDemand` off, a pause hold, a daily cap, unresolved dependencies;
  - **thrown:** budget, agent not invokable; these leave only the log line "failed to wake agent on issue update";
  - **deferred** behind another active run.
- Which of these happened in OQ-035 cannot be told from source. The evidence would be in `agent_wakeup_requests`.

**Why the scheduler does not recover it:**
- `reconcileStrandedAssignedIssues` selects `in_review` issues with no user assignee (`S\services\recovery\service.js` 2938-2944).
- But when the participant has **no run** on the issue, or its latest run is not terminal, it counts the issue as `skipped`. It escalates only if the agent is not invokable (3412-3440).
- So the OQ-035 case is skipped on every 30-second tick and at startup, indefinitely.
- The sweeper does re-dispatch a reviewer whose **previous** run on the issue is terminal (reason `execution_review_participant_recovery`).

**Other sweeps:**
- `scanSilentActiveRuns` only reports on running runs.
- `blocked` issues are swept only when their blockers resolve.

**Duplicates and multiple reviewers:**
- The server does not enforce the watchdog's `idempotencyKey`. A Board manual wake is not coalesced, so de-duplication stays on the client side.
- Only the first eligible participant of a stage is woken.

**Consequence for D-AUTH-03:**
- The approved condition ("retire if the scheduler reliably recovers reviewer wakeups") is not met at source level.
- D-AUTH-03 says that in that case work stops and the Board decides again.
- The live watchdog is unchanged.
- After a switch to `authenticated` without a Board credential, the watchdog would stop working, so **the manual Board sweep becomes the only approved option**.

**Recommendation:** use the **manual Board sweep** after the switch: a `pc.py` command that runs the watchdog's logic as the Board, run by hand. Keep the watchdog unchanged until the switch. A runtime check (VR-1) would only confirm the source finding; it is optional.

### 3.D D-AUTH-04: credential security (Source and Proposed)

**Findings, all Source:**
- **Plaintext store:** `%USERPROFILE%\.paperclip\auth.json` holds the key in clear text (A1 3.3).
- **Windows ACLs:** the file's `0o600` mode is meaningless on Windows. The protection is the folder ACL, which grants SYSTEM, Administrators and the user (live read).
- **Expiry:** keys last 30 days with no renewal. Any valid key can mint a successor (A1 3.2).
- **Writes:** not atomic, not locked (A1 3.3).
- **401 text:** an expired or revoked key gets an agent-token message (A1 3.6).
- **Leaks through output:** `token board create`, `connect` and `auth challenge create` print tokens (A1 3.10).
- **Shared variable:** `PAPERCLIP_API_KEY` is also every agent run's variable (A1 3.11).

**New point:** `pc.py` is run by Claude Code on the Board's behalf. Any Board credential `pc.py` can read is readable by that assistant session too. This is not a Paperclip agent, but it is an automated process with the Board's rights.

**Storage options:**

| Option | Protection | Rotation | Issuance without printing | Complexity |
|---|---|---|---|---|
| CLI store `auth.json`, read by a helper | Folder ACL only; plaintext; internal format may change | `paperclipai auth login` every 30 days | Yes (login never prints the key) | Low |
| `PAPERCLIP_BOARD_TOKEN` set per session | Process memory; any same-user process can read the environment | Manual | Depends on how it is set | Low; easy to leak into shell history |
| Windows Credential Manager (generic credential), read through `ctypes` | DPAPI under the user's logon; not plaintext on disk | Re-issue, overwrite, revoke the old key id | Needs a small issuance script that stores the key without echoing it | Medium |
| DPAPI-encrypted file (`CryptProtectData` through `ctypes`) | Same as Credential Manager | Same | Same | Medium |

**Recommendation (Proposed):**
- Store the key in **Windows Credential Manager**, read by one shared helper through `ctypes`, with `PAPERCLIP_BOARD_TOKEN` as an explicit per-session override. Issue keys with `paperclipai auth login`, by the Board Operator, in their own terminal, never through the assistant.
- Do not depend on the CLI store's internal format.
- **Rules for the helper:**
  - the identity comes from `GET /api/cli-auth/me`;
  - when the credential is missing or invalid, stop with a "log in again" message;
  - a 403 names the missing right;
  - the token is redacted from every error;
  - the helper never reads `PAPERCLIP_API_KEY`.
- **Residual risk:** any process running as ADMIN, including the assistant session, can use the stored key. That needs explicit Board acceptance.

## 4. Workstream E: risk classification

| Risk | Classification | Evidence | Note |
|---|---|---|---|
| D-AUTH-03 premise false (OQ-035 not recovered) | **Direct migration blocker** | §3.C (Source) | Back to the Board |
| Board claim not runtime-verified | **Direct migration blocker** | §2 | VA-2 |
| Participant update not runtime-verified; SOU-28 needs a decision before the switch | **Direct migration blocker** | §3.B | VA-4, VA-5; operational step |
| Credential storage undecided | **Direct migration blocker** | §3.D | Board decision |
| Scripts send no `Authorization` header | **Direct migration blocker** (Phase B work) | Phase A §3 | Phase B |
| No tested backup restore (OQ-025) | **Direct migration blocker** (for rollback) | OQ-025; manual backup worked (step2 §6a) | VA-9 |
| R8: workspace folder grants Modify to all Authenticated Users | **Security risk requiring separate acceptance** | Live read 2026-11-20 (A.2) | Unrelated to the mode switch |
| G-14 exploitability from an agent run | **Security risk requiring separate acceptance** | §6b; `Bash(curl *)` removed (§6a) | Agent runs cancelled. Cursor agents have no allowlist |
| Assistant session holds the Board credential | **Security risk requiring separate acceptance** | §3.D | New |
| Phase A audit not in the repository; A.1 and the decision record uncommitted | **Out of scope but must remain tracked** (traceability) | §3.A | Commit or archive by Board choice |
| `C:\OQ-042-Sandbox` still exists | **Out of scope but must remain tracked** | Live read | Belongs to OQ-042 |
| Agents in `authenticated` mode (helpers, MCP) | **Out of scope but must remain tracked**; it becomes a blocker if agent runs are required before the switch | §2 | Needs agent-run approval |
| OQ-024 (deployment mode) still says `local_trusted` for v1 | **Out of scope but must remain tracked** | open-questions OQ-024 | Updated only when the mode actually changes |
| OQ-031 wizard sign-in failure | **No longer applicable to Board sign-in** | §6b: browser sign-in worked | Still applies to model "Connect" in the UI |
| OQ-043 sandbox artifacts | **No longer applicable** | §2 sandbox cleanup row | Cleanup verified |

No risk is closed by this document.

## 5. Workstream F: Phase B entry criteria

| # | Criterion | Required evidence | Acceptance condition | Decision-maker | Separate Board approval |
|---|---|---|---|---|---|
| E1 | Readiness package reviewed | This document and the verification plan | Board review recorded | Board Operator | Yes |
| E2 | Watchdog decision re-taken | §3.C | New decision: manual sweep, credentialed watchdog or other | Board Operator | **Yes** (D-AUTH-03 return) |
| E3 | Credential storage decided | §3.D | An option chosen and the residual risk accepted in writing | Board Operator | **Yes** |
| E4 | Verification environment authorized | Verification plan §2 | Board approves environment creation (D-AUTH-05 covers planning only) | Board Operator | **Yes** |
| E5 | Claim verified | VA-2 result record | Claim works; `local-board` admin removed; owner memberships created | Board Operator reviews | No (part of E4) |
| E6 | Participant update verified | VA-4 and VA-5 results | Case (a) keeps ids and state; case (b) refused as predicted; rollback works | Board Operator reviews | No |
| E7 | Identity and token handling verified | VA-3 and VA-7 results | `/cli-auth/me` gives the claimed user; 401 and 403 behave as documented | Board Operator reviews | No |
| E8 | Backup restore verified | VA-9 result | A restore into the test environment succeeds | Board Operator reviews | No |
| E9 | Mode rollback verified | VA-8 result | Returning to `local_trusted` restores Board access, and data is intact | Board Operator reviews | No |
| E10 | Traceability | Git | The Phase A audit, A.1, the decision record and this package are committed or explicitly archived | Board Operator | Yes (commit) |
| E11 | Agent behaviour in `authenticated` | VR-8, or explicit acceptance | Verified, or the Board accepts migrating without agent verification | Board Operator | **Yes** |
| E12 | Separate security risks | §4 | R8, G-14 and the assistant-credential risk are accepted or scheduled | Board Operator | **Yes** |

Phase B stays **blocked** until E1-E10 are met and E11-E12 are met or explicitly accepted.

## 6. Decisions that must return to the Board

1. **D-AUTH-03:** the premise fails at source level. Choose one:
   - (a) a manual Board sweep after the switch (recommended);
   - (b) a credentialed watchdog, which reverses D-AUTH-03's "no Board credential" condition and needs the risk in A1 §3 accepted;
   - (c) investigate a plugin or built-in alternative first.
2. **Credential storage** (§3.D), including acceptance that the assistant session can use the Board key.
3. **Verification environment** (verification plan): creation, and whether the agent-run cases are included.
4. **Traceability:** whether to commit the Phase A audit, A.1, the decision record and this package.
5. **Freeze on new Board stages** between the final re-read and the claim (§3.B step 2).
