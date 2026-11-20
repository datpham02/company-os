# Board Decision Record — Paperclip Authentication Migration

**Date:** 2026-11-20
**Status:** Approved: five decisions (Board Operator, in chat, 2026-11-20). Approval of a decision is **not** authorization to implement it.
**Scope:** migration of the studio Paperclip instance from `local_trusted` to `authenticated`. Related: G-14, OQ-035, OQ-043.
**Authority:** Board Operator

**Evidence:**
- [auth-migration-phase-a1.md](../architecture/auth-migration-phase-a1.md): Phase A.1, the authoritative design input. Sections are cited below as "A1 §…", findings as "A1 n.n".
- [auth-migration-phase-a-audit.md](../architecture/auth-migration-phase-a-audit.md): the Phase A audit (2026-11-20), an API caller inventory. Added to the repository under D-AUTH-08.
- [step2-board-decisions.md](step2-board-decisions.md) §6b: sandbox results.
- [open-questions.md](open-questions.md): OQ-035, OQ-043.

**Evidence labels** (as in A1):
- **[source]:** read in the Paperclip 2026.1023.0 source.
- **[sandbox]:** observed in the OQ-043 sandbox on 2026-11-20, which ran no agents.
- **[live-read]:** GET requests only against the studio instance.
- **[design]:** proposed, not verified at runtime.

## 1. Purpose

Record the Board's five decisions that follow Phase A and Phase A.1:
- what each decision approves;
- what it does not approve;
- what each depends on;
- what must be verified before it can be acted on.

## 2. Decisions

### D-AUTH-01 — Board identity: use Paperclip board claim

**Decision:** APPROVED.

When the instance moves to `authenticated` mode, the Board identity is established with Paperclip's built-in board claim:
1. Start Paperclip in `authenticated` mode.
2. Use the claim link that Paperclip generates.
3. The signed-in user who claims becomes instance admin and owner of every company.
4. `local-board` loses instance admin. It stays only as a historical identity in existing records.

**Rationale:**
- This is the supported path (A1 1.9).
- It avoids the manual workaround used in the sandbox (§6b): promoting a new user while briefly in `local_trusted`. That workaround leaves `local-board` as a second instance admin.

**Boundaries:**
- No claim is performed, and the live authentication mode is not changed.
- The claim link is created only at server startup, kept in memory, and valid for 24 hours (A1 §1, 1.9).

**Dependencies:**
- `local-board` must be the only instance admin at the time of the switch (A1 1.9). [source]
- A browser session of the claiming user is required (A1 1.9). [source]

**Runtime verification:** **not runtime-tested.** Inspected in source only (A1 1.9). Risk R1 in A1 §6.

**Related:** A1 1.9, 1.10, §2.2; G-14; OQ-043.

### D-AUTH-02 — Stage participant migration

**Decision:** APPROVED.

Order:
1. Resolve the pending Board approval of **SOU-28** while the `local-board` participant can still act, that is, in `local_trusted` mode, before the switch.
2. After the Board identity has been established through D-AUTH-01, update the stage participants of **SOU-17** and **SOU-30** from `local-board` to the new Board user.
3. Keep the existing stage ids and participant ids wherever the supported API allows. `PATCH /issues/:id` with `executionPolicy`, guarded by `expectedExecutionPolicy` (A1 1.5, §2.2).
4. Keep decision history and the existing execution state. Done and cancelled issues are not changed.

**Rationale:**
- A stage decision is accepted only from the exact `userId` of the active participant. Board, owner or admin status does not count (A1 1.2, 1.3). [source]
- After the switch nobody can act as `local-board`, and Paperclip's recovery does not escalate such issues (A1 1.8). [source]

**Boundaries:**
- No real issue or stage is modified by this record.
- The Board override that clears a stage without a decision row (A1 1.4) is **not** part of the approved method.

**Dependencies:** D-AUTH-01 completed; D-AUTH-04 (the `pc.py` identity change) deployed; a verified participant update (R2).

**Runtime verification:** **not verified.** How the participant update behaves at runtime is unknown. The affected-issue inventory is [live-read] on 2026-11-20 (A1 1.13) and must be read again just before the migration, because issues change.

**Related:** A1 1.1-1.8, 1.12, 1.13, §2.2; risk R2.

### D-AUTH-03 — Watchdog strategy


**Decision:** APPROVED.

- Retire the custom review-wake watchdog (`runtime/tools/review-wake-watchdog.ts`) **if** Paperclip's built-in scheduler reliably recovers reviewer wakeups.
- A manual Board sweep is the fallback.

**Conditions:**
- The watchdog is never given a Board credential.
- No automation user is created.
- The live watchdog is not deleted or disabled yet.
- The scheduler's behaviour must first be verified in an isolated environment (D-AUTH-05).
- If the scheduler cannot do the job, work stops and the Board takes a new decision.

**Rationale:**
- No least-privilege identity can wake agents. The narrowest one, an `operator` member with grants cleared, still holds `secrets:read`, issue mutation and runtime control (A1 2.1-2.9, §3.2). [source]
- A Board key cannot be scoped (A1 2.7). [source]

**Runtime verification:** **not verified** (A1 2.11, risk R3). See §6 below for an inconsistency in the premise.

**Related:** A1 §3; OQ-035; risks R3, R5, R6.

### D-AUTH-04 — Board credential design

**Decision:** APPROVED.

**Board and agent credentials are kept separate:**
- Board scripts (`pc.py`, `post-import.py`, `sync-instructions.py`) read `PAPERCLIP_BOARD_TOKEN`.
- Agent processes keep `PAPERCLIP_API_KEY`.
- The agent variable is never used for Board authentication: Paperclip gives every agent run that variable (A1 3.11).

**Handling rules:**
- No credential in command-line arguments, logs or exceptions.
- Fail closed when the Board credential is missing; never fall back to a keyless request.
- Handle 401 and 403 separately. A 401 for an expired Board key carries an agent-token message (A1 3.6).

**Board identity:** resolved at runtime through `GET /api/cli-auth/me`, not hardcoded as `local-board` (A1 1.12).

**Still subject to security review:** the storage implementation. These Phase A.1 findings stand:
- the CLI store `auth.json` is plaintext, not atomic, and not locked (A1 3.3);
- Windows applies `0o600` only as a read-only attribute, so the folder ACL is the real control (A1 3.3, 3.4);
- keys expire after 30 days with no automatic refresh (A1 3.2);
- there is no OS key store support (A1 3.9);
- some CLI commands print tokens (A1 3.10).

**Boundaries:** no credential is created, issued, stored, revoked or rotated.

**Runtime verification:** the flow of a CLI login is [sandbox]. Everything else is [source] or [design].

**Related:** A1 §4, §5.3; risk R7.

### D-AUTH-05 — Verification authorization

**Decision:** APPROVED.

Verification may be planned and carried out in an **isolated** Paperclip test environment. It must not reuse or modify the live instance's data, credentials or workspace. The boundaries of [step2-board-decisions.md](step2-board-decisions.md) §3 and §3.1 (loopback and credential isolation) apply.

**This approval does not authorize:**
- creating or rebuilding a sandbox right away; the verification plan comes first (§4);
- running or waking agents (agent-run verification needs a separate, explicit Board approval);
- changing live Paperclip authentication settings;
- changing live users, roles, permissions, keys or issue stages;
- the migration itself.

**What it covers:**
- Without agents: R1 (claim) and R2 (participant update) from A1 §6.
- Only after the separate approval above: R3 (scheduler wakes reviewers) and R4 (agents in `authenticated` mode).

**Related:** A1 §6, §7 item 5; D-STEP2-02 (whose agent-run part was cancelled on 2026-11-20).

## 3. Approval record

| Decision | Board outcome | Runtime-verified | Notes |
|---|---|---|---|
| D-AUTH-01 — Board claim | Approved | No | Source only |
| D-AUTH-02 — Stage participants | Approved | No | Inventory [live-read] 2026-11-20 |
| D-AUTH-03 — Watchdog | Approved (conditional) | No | Retire only after verification |
| D-AUTH-04 — Credentials | Approved | Partly (CLI login [sandbox]) | Storage still under security review |
| D-AUTH-05 — Verification | Approved | n/a | Agent runs need a separate approval |

**Board Operator:** approved in chat.
**Approval date:** 2026-11-20.

## 4. Phase B readiness

Approving D-AUTH-01 to D-AUTH-05 does **not** authorize Phase B (authentication contract and implementation). Phase B stays blocked until:
1. this record has been reviewed;
2. the isolated verification plan (D-AUTH-05) is prepared;
3. the runtime verification results (at least R1 and R2; R3 and R4 if agent runs are approved) are reviewed by the Board;
4. the remaining security and migration blockers are resolved or explicitly accepted. That includes the credential storage review (D-AUTH-04) and the D-AUTH-03 premise (§6).

## 5. Explicitly not authorized

- A live mode switch or any change to the live Paperclip configuration.
- A board claim on the live instance.
- Changes to live issues, stages, users, roles, permissions or keys.
- Creating, storing, rotating or revoking any credential.
- Creating an automation user, or giving the watchdog any credential.
- Deleting or disabling the live watchdog.
- Running, waking or cancelling agents.
- Code changes for Phase B.

## 6. Open points recorded with the decisions

1. **The D-AUTH-03 premise is in doubt.** OQ-035 records that reviewers were **not** woken after an in-run hand-off on 2026-11-04. That was on the same Paperclip 2026.1023.0, whose scheduler was already running (A1 2.11). The scheduler may therefore not cover this case. Verification R3 must reproduce the OQ-035 scenario specifically.
2. **The Phase A audit file was not in the repository** (resolved by D-AUTH-08: now [auth-migration-phase-a-audit.md](../architecture/auth-migration-phase-a-audit.md)). A1 refers to `phase-a-auth-migration-audit.md`, which was delivered outside the repository. If it is to be kept, it needs to be added separately.
3. **Phase A was corrected by Phase A.1** on `local-board`'s admin role: it is removed by a claim, not kept (A1 1.9).
4. **The workspace-folder ACL risk** (all local users can modify the repositories) stays open and is outside these decisions (A1 R8).
